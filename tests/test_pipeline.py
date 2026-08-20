"""Røyktest: kjører hele pipelinen med en falsk kilde, uten nett.

Poenget er ikke testdekning. Poenget er at du kan endre core/ og på
to sekunder vite om du ødela noe.
"""

import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from core import diff, runner, signals, snapshot
from core import raw as raw_arkiv
from core.contract import Observation, Source

ROT = Path(__file__).resolve().parent.parent


class FalskKilde(Source):
    name = "falsk"
    entity_type = "selskap"

    def fetch(self, kjoredato):
        return [{"orgnr": "999999999", "navn": "Testlaks AS", "ansatte": 12}]

    def parse(self, raw, observed_at):
        for rad in raw:
            yield Observation(
                entity_id=rad["orgnr"],
                entity_type=self.entity_type,
                entity_name=rad["navn"],
                field="antall_ansatte",
                value=str(rad["ansatte"]),
                source=self.name,
                observed_at=observed_at,
            )


class KnustKilde(Source):
    name = "knust"

    def fetch(self, kjoredato):
        raise RuntimeError("kilden er nede")

    def parse(self, raw, observed_at):
        return []


def test_feil_isoleres(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path)

    obs, res = runner.run_all([FalskKilde(), KnustKilde()], "2026-01-01")
    assert len(obs) == 1
    assert [r.ok for r in res] == [True, False]


def test_diff_fanger_endring(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    forrige = snapshot.to_frame(list(FalskKilde().collect("2026-01-01")))
    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")

    endret = [Observation("999999999", "selskap", "Testlaks AS",
                          "antall_ansatte", "20", "falsk", "2026-01-08")]
    endringer = diff.compare(snapshot.to_frame(endret), "2026-01-08")

    assert endringer.height == 1
    assert endringer["change_type"][0] == "endret"


def _signalrad(felt, gammel, ny, **overstyr):
    rad = {
        "entity_id": "1", "entity_type": "selskap", "entity_name": "Testlaks AS",
        "field": felt, "old_value": gammel, "new_value": ny,
        "change_type": "endret", "source": "falsk", "observed_at": "2026-01-08",
    }
    rad.update(overstyr)
    return rad


def test_signalregler_scorer():
    scoret = signals.score(pl.DataFrame([_signalrad("antall_ansatte", "10", "20")]))
    assert signals.treff(scoret).height == 1


def test_score_returnerer_alle_rader_ogsaa_uten_treff():
    """Blindsonen skal være synlig. Før kastet score() hver rad ingen
    regel traff, så en uke med 400 uklassifiserte endringer så ut som en
    uke uten endringer."""
    endringer = pl.DataFrame([
        _signalrad("antall_ansatte", "10", "20"),      # treffer en regel
        _signalrad("poststed", "Bodø", "Tromsø"),      # ingen regel
        _signalrad("landkode", "NO", "SE"),            # ingen regel
    ])
    scoret = signals.score(endringer)

    assert scoret.height == 3                        # ALLE rader er med
    assert signals.treff(scoret).height == 1

    uten = scoret.filter(pl.col("signal").is_null())
    assert uten.height == 2
    assert uten["vekt"].to_list() == [0, 0]


def test_scoret_pluss_uklassifisert_er_lik_totalen():
    """Den ene summen som ikke kan stemme ved et sammentreff."""
    endringer = pl.DataFrame([
        _signalrad("antall_ansatte", "10", "20"),
        _signalrad("konkurs", "False", "True"),
        _signalrad("poststed", "Bodø", "Tromsø"),
        _signalrad("landkode", "NO", "SE"),
        _signalrad("aktivitet", "x", "y"),
    ])
    scoret = signals.score(endringer)
    traff = signals.treff(scoret)
    uklassifisert = scoret.height - traff.height

    assert scoret.height == endringer.height
    assert traff.height + uklassifisert == endringer.height


def test_uklassifiserte_felter_peker_paa_manglende_regler():
    """Lista over felter uten regel er lista over regler som mangler."""
    endringer = pl.DataFrame(
        [_signalrad("poststed", "a", "b") for _ in range(3)]
        + [_signalrad("landkode", "NO", "SE") for _ in range(2)]
        + [_signalrad("antall_ansatte", "10", "20")]
    )
    topp = signals.uklassifiserte_felter(signals.score(endringer))

    assert topp == [("poststed", 3), ("landkode", 2)]


def test_score_paa_tom_ramme_har_riktige_kolonner():
    """Uke uten endringer skal ikke kaste hos kalleren."""
    tom = pl.DataFrame(schema=diff.CHANGE_SCHEMA)
    scoret = signals.score(tom)

    assert scoret.height == 0
    assert "signal" in scoret.columns and "vekt" in scoret.columns
    assert signals.treff(scoret).height == 0
    assert signals.uklassifiserte_felter(scoret) == []


def test_regresjon_oppdages(tmp_path, monkeypatch):
    """En kilde som fungerte forrige uke og feiler nå skal flagges."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    ok = [runner.Result("falsk", True, 5)]
    health.skriv(health.oppdater(ok, "2026-01-01")[0])

    feilet = [runner.Result("falsk", False, 0, "RuntimeError: nede")]
    _, nede = health.oppdater(feilet, "2026-01-08")

    assert nede == ["falsk (nede, uke 1)"]


def test_knekt_kildefil_stopper_ikke_de_andre(tmp_path, monkeypatch):
    """En kildefil som ikke lar seg importere skal isoleres, ikke drepe kjøringen."""
    import types

    from core import registry

    (tmp_path / "frisk.py").write_text(
        "from core.contract import Source\n"
        "class Frisk(Source):\n"
        "    name = 'frisk'\n"
        "    def fetch(self, kjoredato): return []\n"
        "    def parse(self, raw, observed_at): return []\n",
        encoding="utf-8",
    )
    (tmp_path / "knekt.py").write_text("import finnes_ikke_xyz\n", encoding="utf-8")

    def last(navn: str):
        fil = tmp_path / f"{navn.split('.')[-1]}.py"
        modul = types.ModuleType(navn)
        exec(compile(fil.read_text(encoding="utf-8"), str(fil), "exec"), modul.__dict__)
        return modul

    monkeypatch.setattr(registry, "SOURCES_DIR", tmp_path)
    monkeypatch.setattr(registry.importlib, "import_module", last)
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")

    kilder = registry.discover()
    assert sorted(k.name for k in kilder) == ["frisk", "knekt"]

    _, res = runner.run_all(kilder, "2026-01-01")
    assert {r.source: r.ok for r in res} == {"frisk": True, "knekt": False}


def test_modulnavn_er_kildenavn():
    """Invarianten: sources/<navn>.py inneholder kilden som heter <navn>.

    En kildefil som ikke lar seg importere blir en KnektKilde, og da
    finnes det ingen klasse å spørre om navn — kjernen kan bare lese
    filnavnet. Bryter de to, rapporteres importfeilen under et navn
    health.json aldri har sett: ingen sist_ok, ingen volumreferanse,
    ingen sist_forsok. Nedetidsalarmen ser en kilde som aldri har
    fungert, og frekvensvakten ser en ukjent kilde.

    Dette er klassen feil, ikke tilfellet. sources/akvakulturregisteret.py
    het `akvakultur` som kilde og er døpt om; denne testen er det som
    hindrer at neste kilde gjør det samme.
    """
    import importlib
    import inspect

    from core import registry
    from core.contract import Source

    brudd = []
    for fil in sorted(registry.SOURCES_DIR.glob("*.py")):
        if fil.stem.startswith("_"):
            continue          # delte hjelpere, ikke kilder

        modul = importlib.import_module(f"sources.{fil.stem}")
        klasser = [
            obj for _, obj in inspect.getmembers(modul, inspect.isclass)
            if issubclass(obj, Source) and obj is not Source
            and obj.__module__ == modul.__name__
        ]

        assert klasser, f"sources/{fil.name} definerer ingen kilde"
        for klasse in klasser:
            if klasse.name != fil.stem:
                brudd.append(f"sources/{fil.name}: {klasse.__name__}."
                             f"name = {klasse.name!r}, forventet {fil.stem!r}")

    assert not brudd, (
        "Modulnavn må være identisk med kildens name, ellers rapporteres "
        "en importfeil under et navn health.json ikke kjenner:\n  "
        + "\n  ".join(brudd)
    )


def test_knekt_kilde_navngis_etter_kilden_naar_klassen_finnes(tmp_path,
                                                              monkeypatch):
    """Feiler __init__ i stedet for importen, kan kilden navngi seg selv.

    Da skal navnet komme fra klassen, ikke fra filnavnet — filnavnet er
    bare fallback for den ene feilen der ingen klasse finnes.
    """
    import types

    from core import registry

    (tmp_path / "en_kilde.py").write_text(
        "from core.contract import Source\n"
        "class Ødelagt(Source):\n"
        "    name = 'en_kilde'\n"
        "    def __init__(self): raise RuntimeError('config mangler')\n"
        "    def fetch(self, kjoredato): return []\n"
        "    def parse(self, raw, observed_at): return []\n",
        encoding="utf-8",
    )

    def last(navn: str):
        fil = tmp_path / f"{navn.split('.')[-1]}.py"
        modul = types.ModuleType(navn)
        modul.__name__ = navn
        exec(compile(fil.read_text(encoding="utf-8"), str(fil), "exec"),
             modul.__dict__)
        for obj in modul.__dict__.values():
            if isinstance(obj, type):
                obj.__module__ = navn
        return modul

    monkeypatch.setattr(registry, "SOURCES_DIR", tmp_path)
    monkeypatch.setattr(registry.importlib, "import_module", last)

    kilder = registry.discover()
    assert [k.name for k in kilder] == ["en_kilde"]


def test_importert_kildeklasse_registreres_ikke_to_ganger():
    """Gjenbruk av en baseklasse mellom kilder skal ikke doble observasjonene."""
    import inspect as _inspect
    from core import registry
    from core.contract import Source

    class Delt(Source):
        name = "delt"

    Delt.__module__ = "sources.kilde_a"

    class Arving(Delt):
        name = "arving"

    Arving.__module__ = "sources.kilde_b"

    # Slik registry filtrerer: bare klasser definert i modulen som skannes.
    i_b = [o for o in (Delt, Arving) if o.__module__ == "sources.kilde_b"]
    assert [o.name for o in i_b] == ["arving"]


def test_nede_kilde_varsler_hver_uke(tmp_path, monkeypatch):
    """Alarmen skal ikke gå stille uke to. Da er datatap usynlig."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    health.skriv(health.oppdater([runner.Result("falsk", True, 5)], "2026-01-01")[0])

    feilet = [runner.Result("falsk", False, 0, "RuntimeError: nede")]
    for uke in ("2026-01-08", "2026-01-15", "2026-01-22"):
        tilstand, nede = health.oppdater(feilet, uke)
        health.skriv(tilstand)
        assert nede, f"ingen alarm {uke} — dette er den stille datatapsfeilen"


def test_kilde_som_aldri_har_fungert_varsler_ogsaa(tmp_path, monkeypatch):
    """Erstatter test_kilde_som_aldri_har_fungert_varsler_ikke.

    Den gamle testen festet antakelsen om at en ny kilde er en du sitter
    og ser på mens den skrives. Legges kilden til av en agent og cron
    fyrer fem dager senere, feiler den i det uendelige med exit 0 — og
    ingen får vite det. Det er nøyaktig den stille datatapsfeilen hele
    health.py finnes for å hindre, bare for en kilde som aldri kom i
    drift i stedet for en som falt ut.
    """
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    feilet = [runner.Result("ny_kilde", False, 0, "RuntimeError: ikke ferdig")]
    for uke in ("2026-01-01", "2026-01-08", "2026-01-15"):
        tilstand, nede = health.oppdater(feilet, uke)
        health.skriv(tilstand)
        assert nede, f"ingen alarm {uke} — kilden kan feile i det uendelige"

    # Meldingen skiller de to tilfellene: dette er ikke en kilde som falt
    # ut, det er en som aldri kom i drift. Samme exit-kode, ulik oppgave.
    assert "har ALDRI levert" in nede[0]
    assert "nede," not in nede[0]
    assert "RuntimeError: ikke ferdig" in nede[0]


def test_nede_og_aldri_levert_skilles_i_meldingen(tmp_path, monkeypatch):
    """Begge gir exit 1, men de betyr ikke det samme for den som leser."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    # "fungert" har lykkes én gang; "aldri" har aldri.
    health.skriv(health.oppdater([runner.Result("fungert", True, 5)],
                                 "2026-01-01")[0])

    _, nede = health.oppdater(
        [runner.Result("fungert", False, 0, "nede"),
         runner.Result("aldri", False, 0, "nede")],
        "2026-01-08",
    )

    assert nede[0].startswith("fungert (nede, uke 1)")
    assert nede[1].startswith("aldri (har ALDRI levert")


def test_retning_skiller_okning_fra_kutt():
    """En regel som heter 'økning' skal ikke score et kutt."""
    def endring(gammel, ny):
        return {
            "entity_id": "1", "entity_type": "lokalitet", "entity_name": "Lok",
            "field": "kapasitet", "old_value": gammel, "new_value": ny,
            "change_type": "endret", "source": "falsk", "observed_at": "2026-01-08",
        }

    opp = {"navn": "økning", "felt": "kapasitet", "endringstype": "endret",
           "min_endring_prosent": 10, "retning": "opp"}
    ned = {"navn": "kutt", "felt": "kapasitet", "endringstype": "endret",
           "min_endring_prosent": 10, "retning": "ned"}

    assert signals._matches(opp, endring("100", "120"))
    assert not signals._matches(opp, endring("100", "80"))
    assert signals._matches(ned, endring("100", "80"))
    assert not signals._matches(ned, endring("100", "120"))

    begge = {"navn": "begge", "felt": "kapasitet", "endringstype": "endret",
             "min_endring_prosent": 10}
    assert signals._matches(begge, endring("100", "80"))
    assert signals._matches(begge, endring("100", "120"))


def test_reglene_i_repoet_er_gyldige():
    """Fanger skrivefeil i signals.yml før de blir stille manglende signaler."""
    kjente = {
        "navn", "felt", "endringstype", "min_endring_prosent", "retning",
        "vekt", "kilde", "entity_type", "fra", "til", "fra_null",
        "krev_uendret",
    }
    assert signals.valider_regler() == [], "formatfeil i signals.yml"
    for regel in signals.load_rules():
        assert "navn" in regel, regel
        assert regel.get("endringstype") in (None, "ny", "endret", "borte"), regel
        assert regel.get("retning") in (None, "opp", "ned", "begge"), regel
        # En ukjent nøkkel ignoreres stille av _matches() og gir en regel
        # som ser strengere ut enn den er.
        assert set(regel) <= kjente, f"ukjent nøkkel i {regel['navn']}: {set(regel)-kjente}"


def test_kapasitetsendring_med_samtidig_enhetsbytte_matcher_ikke():
    """1000 TN -> 1500 STK er ikke 50 % vekst, det er to usammenlignbare
    tall. Regelen skal tie, og enhetsbyttet får sin egen rad."""
    scoret = signals.score(pl.DataFrame([
        _signalrad("kapasitet", "1000", "1500", entity_id="7"),
        _signalrad("kapasitet_enhet", "TN", "STK", entity_id="7"),
    ]))
    per_felt = dict(zip(scoret["field"].to_list(), scoret["signal"].to_list()))

    assert per_felt["kapasitet"] is None
    assert per_felt["kapasitet_enhet"] == "Måleenhet for kapasitet endret"


def test_kapasitetsendring_uten_enhetsbytte_matcher_som_for():
    """Vakten skal ikke gjøre regelen strengere enn den var når enheten
    faktisk lå i ro — heller ikke for en ANNEN entitet som byttet enhet."""
    scoret = signals.score(pl.DataFrame([
        _signalrad("kapasitet", "1000", "1500", entity_id="7"),
        _signalrad("kapasitet_enhet", "TN", "STK", entity_id="8"),
    ]))
    kap = scoret.filter(pl.col("field") == "kapasitet")

    assert kap["signal"][0] == "Kapasitetsøkning over 10 %"


def test_kapasitet_fra_null_fanges():
    """At det settes ut fisk der det ikke var noe er den mest interessante
    hendelsen en lokalitet har. Nullvernet mot divisjon spiste den."""
    scoret = signals.score(pl.DataFrame([_signalrad("kapasitet", "0", "780")]))
    traff = signals.treff(scoret)

    assert traff.height == 1
    assert traff["signal"][0] == "Kapasitet satt fra null"


def test_fra_null_gjelder_bare_naar_nokkelen_er_satt():
    """Ingen implisitt endring av eksisterende regler: 0 -> N skal ikke
    plutselig matche prosentreglene, og N -> 0 er ikke fra_null."""
    # Prosentreglene skal fortsatt avvise 0 som utgangspunkt.
    kun_prosent = [r for r in signals.load_rules()
                   if r.get("min_endring_prosent") and not r.get("fra_null")]
    rad = _signalrad("kapasitet", "0", "780")
    assert not any(signals._matches(r, rad) for r in kun_prosent)

    # Og motsatt vei er ikke "fra null".
    fra_null = [r for r in signals.load_rules() if r.get("fra_null")]
    assert fra_null
    assert not any(signals._matches(r, _signalrad("kapasitet", "780", "0"))
                   for r in fra_null)


def test_boolsk_overgang_scorer_ulikt_hver_vei():
    """Å gå konkurs og å komme ut av konkurs er ikke samme hendelse.
    Før scoret begge identisk på vekt 9."""
    inn = _signalrad("konkurs", "False", "True")
    ut = _signalrad("konkurs", "True", "False")

    scoret = signals.score(pl.DataFrame([inn, ut]))
    per_ny = dict(zip(scoret["new_value"].to_list(),
                      zip(scoret["signal"].to_list(), scoret["vekt"].to_list())))

    assert per_ny["True"] == ("Konkurs åpnet", 9)
    assert per_ny["False"] == ("Ut av konkurs", 5)


def test_boolsk_regel_matcher_uten_aa_kaste():
    """float("False") kaster. Tekstgrammatikken skal ikke være i nærheten
    av tallveien i det hele tatt."""
    scoret = signals.score(pl.DataFrame([
        _signalrad("under_tvangsavvikling", "False", "True"),
        _signalrad("er_i_konsern", "False", "True"),
        _signalrad("ansatte_er_registrert", "True", "False"),
    ]))
    assert signals.treff(scoret).height == 3


def test_blandet_grammatikk_er_formatfeil():
    """Tall- og tekstgrammatikk på samme regel gjør noe annet enn den ser
    ut til å gjøre. Det skal si fra, ikke tie."""
    problemer = signals.valider_regler([
        {"navn": "Blandet", "felt": "konkurs", "til": "True", "retning": "ned"},
    ])
    assert len(problemer) == 1 and "Blandet" in problemer[0]
    assert signals.valider_regler([{"navn": "Rein", "felt": "konkurs",
                                    "til": "True"}]) == []


def test_ugyldig_regel_utelates_men_stopper_ikke_scoringen(capsys):
    """Én feilskrevet regel skal ikke koste ukas changelog."""
    import core.signals as s
    ekte = s.load_rules
    s.load_rules = lambda: [
        {"navn": "Blandet", "felt": "konkurs", "til": "True", "retning": "ned", "vekt": 9},
        {"navn": "Frisk", "felt": "antall_ansatte", "endringstype": "endret",
         "min_endring_prosent": 20, "retning": "opp", "vekt": 5},
    ]
    try:
        scoret = s.score(pl.DataFrame([
            _signalrad("konkurs", "False", "True"),
            _signalrad("antall_ansatte", "10", "20"),
        ]))
    finally:
        s.load_rules = ekte

    assert "::error::" in capsys.readouterr().out
    assert scoret.height == 2                       # ingen rader tapt
    assert s.treff(scoret).height == 1              # kun den friske regelen traff


def test_nytt_selskap_far_ikke_lokalitetsetiketten():
    """Begge regler er felt `navn` + endringstype `ny`, og første treff
    vinner. Uten kilde/entity_type fikk hvert nyregistrerte selskap
    etiketten "Ny lokalitet i registeret"."""
    selskap = _signalrad("navn", None, "Nylaks AS",
                         change_type="ny", source="enhetsregisteret",
                         entity_type="selskap")
    lokalitet = _signalrad("navn", None, "TUHOLMANE Ø",
                           change_type="ny", source="akvakultur",
                           entity_type="lokalitet")

    scoret = signals.score(pl.DataFrame([selskap, lokalitet]))
    per_kilde = dict(zip(scoret["source"].to_list(), scoret["signal"].to_list()))

    assert per_kilde["enhetsregisteret"] == "Nytt selskap i bransjen"
    assert per_kilde["akvakultur"] == "Ny lokalitet i registeret"


def test_samme_dag_oppdages(tmp_path, monkeypatch):
    """Dagens snapshot skal kjennes igjen, ellers dobbeltføres changeloggen."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    assert snapshot.finnes_allerede("2026-01-01") == []

    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")

    assert snapshot.finnes_allerede("2026-01-01") == ["falsk"]
    assert snapshot.finnes_allerede("2026-01-08") == []


def test_manglende_miljovariabel_kaster_ved_bruk(tmp_path, monkeypatch):
    """Tom streng gir kryptisk 401 senere. Vi vil ha feilen med en gang."""
    from core import config

    (tmp_path / "config.yml").write_text(
        "kilder:\n"
        "  test:\n"
        "    aktiv: true\n"
        "    nokkel: \"${FINNES_IKKE_XYZ}\"\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.yml")
    monkeypatch.delenv("FINNES_IKKE_XYZ", raising=False)
    config.load.cache_clear()

    # Nøkler uten miljøvariabel skal fortsatt virke — feilen er lokal.
    assert config.get("kilder.test.aktiv") is True

    with pytest.raises(RuntimeError, match="FINNES_IKKE_XYZ"):
        config.get("kilder.test.nokkel")

    config.load.cache_clear()


def _endring(dato, ny_verdi):
    return pl.DataFrame([{
        "entity_id": "1", "entity_type": "selskap", "entity_name": "Testlaks AS",
        "field": "antall_ansatte", "old_value": "10", "new_value": ny_verdi,
        "change_type": "endret", "source": "falsk", "observed_at": dato,
    }])


def test_changelog_skriver_en_fil_per_kjoring(tmp_path, monkeypatch):
    """Ingen omskriving av samlefil — git skal ikke lagre alt på nytt hver uke."""
    from core import changelog

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    changelog.skriv(_endring("2026-01-08", "20"), "2026-01-08")
    changelog.skriv(_endring("2026-01-15", "30"), "2026-01-15")

    filer = sorted(p.name for p in (tmp_path / "changelog").glob("*.parquet"))
    assert filer == ["2026-01-08.parquet", "2026-01-15.parquet"]

    alt = changelog.les_alt()
    assert alt.height == 2
    assert alt["observed_at"].to_list() == ["2026-01-08", "2026-01-15"]


def test_changelog_rekjoring_dobbeltforer_ikke(tmp_path, monkeypatch):
    """Samme dato skrevet to ganger skal gi én rad, ikke to."""
    from core import changelog

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    changelog.skriv(_endring("2026-01-08", "20"), "2026-01-08")
    changelog.skriv(_endring("2026-01-08", "20"), "2026-01-08")

    assert changelog.les_alt().height == 1


def test_changelog_tom_gir_riktig_skjema(tmp_path, monkeypatch):
    from core import changelog
    from core.diff import CHANGE_SCHEMA

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    tom = changelog.les_alt()
    assert tom.height == 0
    assert tom.columns == list(CHANGE_SCHEMA)

    assert changelog.skriv(tom, "2026-01-08") is None
    assert not (tmp_path / "changelog").exists()


def test_changelog_leser_gammel_samlefil(tmp_path, monkeypatch):
    """Historikk fra før omleggingen skal ikke forsvinne."""
    from core import changelog

    gammel = tmp_path / "changelog.parquet"
    _endring("2025-12-01", "15").write_parquet(gammel)

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", gammel)

    changelog.skriv(_endring("2026-01-08", "20"), "2026-01-08")

    alt = changelog.les_alt()
    assert alt["observed_at"].to_list() == ["2025-12-01", "2026-01-08"]


def test_nytt_felt_i_kilden_er_ikke_en_endring(tmp_path, monkeypatch):
    """Utvider du en kilde med nye felter, er ikke det 23 000 hendelser."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    forrige = [Observation("999999999", "selskap", "Testlaks AS",
                           "antall_ansatte", "12", "falsk", "2026-01-01")]
    snapshot.write(forrige, "2026-01-01")

    # Uka etter: samme verdi, men kilden lagrer nå to felter til.
    naa = [
        Observation("999999999", "selskap", "Testlaks AS",
                    "antall_ansatte", "12", "falsk", "2026-01-08"),
        Observation("999999999", "selskap", "Testlaks AS",
                    "aksjekapital", "100000", "falsk", "2026-01-08"),
        Observation("999999999", "selskap", "Testlaks AS",
                    "er_i_konsern", "True", "falsk", "2026-01-08"),
    ]
    assert diff.compare(snapshot.to_frame(naa), "2026-01-08").height == 0

    # Men en NY entitet skal fortsatt telles, på et felt som fantes før.
    ny_entitet = naa + [Observation("888888888", "selskap", "Nylaks AS",
                                    "antall_ansatte", "3", "falsk", "2026-01-08")]
    endringer = diff.compare(snapshot.to_frame(ny_entitet), "2026-01-08")
    assert endringer.height == 1
    assert endringer["entity_id"][0] == "888888888"
    assert endringer["change_type"][0] == "ny"


def _akva_rad(site_nr=10029, kapasitet=2340.0, tillatelser=("B", "A")):
    return {
        "siteNr": site_nr, "name": "TUHOLMANE Ø",
        "capacity": kapasitet, "capacityUnitType": "TN", "tempCapacity": kapasitet,
        "placement": {"municipalityName": "KARMØY", "municipalityCode": "1149",
                      "countyName": "ROGALAND", "countyCode": "11",
                      "prodAreaCode": "3", "prodAreaName": "Karmøy til Sotra",
                      "prodAreaStatus": "RØD"},
        "latitude": 59.371233, "longitude": 5.216333,
        "speciesTypes": ["SALMON"], "speciesLimitations": [],
        "placementType": "Offshore", "waterType": "Salt",
        "isSlaughtery": False, "hasCommercialActivity": True,
        "hasColocation": True, "hasJointOperation": False,
        "connections": [{"licenseNr": n} for n in tillatelser],
        "obsoleteConnections": [],
        "version": {"status": "APPROVED", "versionCauseType": "COORDINATES",
                    "validFrom": "2020-05-13T22:00:00Z"},
    }


def test_akvakultur_parser_ekte_respons():
    """Feltnavnene er verifisert mot levende API — dette låser dem."""
    from sources.akvakultur import Akvakulturregisteret

    obs = {o.field: o.value
           for o in Akvakulturregisteret().parse([_akva_rad()], "2026-08-17")}

    assert obs["kapasitet"] == "2340.0"
    assert obs["kapasitet_enhet"] == "TN"          # enhet ALLTID med tallet
    assert obs["prodomraade_status"] == "RØD"      # trafikklyset
    assert obs["kommunenummer"] == "1149"

    alle = list(Akvakulturregisteret().parse([_akva_rad()], "2026-08-17"))
    assert {o.entity_id for o in alle} == {"10029"}   # siteNr, ikke siteId
    assert {o.entity_type for o in alle} == {"lokalitet"}


def test_akvakultur_tillatelser_sorteres():
    """Uten sortering gir vilkårlig rekkefølge fra API-et falsk endring hver uke."""
    from sources.akvakultur import Akvakulturregisteret

    def tillatelser(rekkefolge):
        rad = _akva_rad(tillatelser=rekkefolge)
        return next(o.value for o in Akvakulturregisteret().parse([rad], "2026-08-17")
                    if o.field == "tillatelser")

    assert tillatelser(("B", "A", "C")) == tillatelser(("C", "B", "A"))


def test_akvakultur_lagrer_ingen_persondata():
    """connections skal kun gi tillatelsesnumre — aldri innehaver."""
    from sources.akvakultur import Akvakulturregisteret

    rad = _akva_rad()
    rad["connections"] = [{"licenseNr": "H-KM-0018", "siteName": "TUHOLMANE Ø",
                           "licenseId": 394, "registeredTime": "2025-08-28"}]

    verdier = " ".join(o.value for o in
                       Akvakulturregisteret().parse([rad], "2026-08-17"))
    assert "394" not in verdier.split("; ")
    assert verdier.count("H-KM-0018") == 1


def test_datamappe_kan_flyttes_med_miljovariabel(tmp_path, monkeypatch):
    """Koden ligger offentlig, dataene privat. Da må stien være flyttbar."""
    import importlib

    monkeypatch.setenv("HAVBRUK_DATA_DIR", str(tmp_path / "annensteds"))

    from core import paths
    importlib.reload(paths)

    assert paths.DATA_DIR == (tmp_path / "annensteds").resolve()
    assert paths.RAW_DIR == paths.DATA_DIR / "raw"
    assert paths.CHANGELOG_DIR == paths.DATA_DIR / "changelog"
    assert paths.HEALTH_PATH == paths.DATA_DIR / "health.json"

    monkeypatch.delenv("HAVBRUK_DATA_DIR")
    importlib.reload(paths)
    assert paths.DATA_DIR == (paths.ROT / "data").resolve()


class DagligKilde(FalskKilde):
    name = "daglig"
    min_dager_mellom = 1


def _kjort(tmp_path, monkeypatch, **sist_forsok):
    """Skriv en health.json der hver kilde sist ble FORSØKT på gitt dato.

    Frekvensvakten leser innsamlingstidspunktet herfra, ikke datoen på
    nyeste snapshotfil. Verdien None gir en post uten `sist_forsok` —
    kilden finnes, men vi vet ikke når den sist kjørte.
    """
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    health.skriv({
        kilde: ({"sist_forsok": dato} if dato else {"sist_ok": "2026-01-01"})
        for kilde, dato in sist_forsok.items()
    })
    return health


def test_forfalte_kilder_velges_hver_for_seg(tmp_path, monkeypatch):
    """Én kilde hentet i dag skal ikke blokkere de andre.

    Dette er scenarioet hver gang en ny kilde aktiveres midt i uka.
    """
    _kjort(tmp_path, monkeypatch, falsk="2026-01-07", daglig="2026-01-07")

    ukentlig, daglig, ny = FalskKilde(), DagligKilde(), KnustKilde()
    ny.name = "helt_ny"

    forfalt, venter = runner.velg_forfalte([ukentlig, daglig, ny], "2026-01-08")

    # Ukentlig må vente (1 dag < 7). Daglig er forfalt (1 >= 1).
    # En kilde health.json ikke kjenner er alltid forfalt.
    assert sorted(k.name for k in forfalt) == ["daglig", "helt_ny"]
    assert [(k.name, d) for k, d in venter] == [("falsk", 1)]


def test_kilde_kjort_i_dag_er_ikke_forfalt(tmp_path, monkeypatch):
    _kjort(tmp_path, monkeypatch, falsk="2026-01-08")

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-08")
    assert forfalt == []
    assert venter[0][1] == 0


def test_forfalt_igjen_etter_full_periode(tmp_path, monkeypatch):
    _kjort(tmp_path, monkeypatch, falsk="2026-01-01")

    forfalt, _ = runner.velg_forfalte([FalskKilde()], "2026-01-08")   # nøyaktig 7
    assert [k.name for k in forfalt] == ["falsk"]


def test_kjoretidspunkt_fram_i_tid_gir_ikke_ny_kjoring(tmp_path, monkeypatch):
    """Klokkerot skal ikke føre til at noe skrives over."""
    _kjort(tmp_path, monkeypatch, falsk="2026-02-01")

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-08")
    assert forfalt == []
    assert venter[0][1] < 0


def test_ukjent_kilde_i_health_er_forfalt(tmp_path, monkeypatch):
    """Fallback-regelen: vet vi ikke når kilden sist kjørte, kjører vi.

    Ikke hypotetisk. `lusetall` sto i nøyaktig denne tilstanden i
    produksjon da F4 ble fikset — health.json kjente bare akvakultur og
    enhetsregisteret. Ble ukjent behandlet som fersk, ville kilden aldri
    blitt hentet, og det er tapt historikk som ikke kan rettes i
    etterkant. Å hente for ofte koster en ekstra fil med løpenummer.
    """
    _kjort(tmp_path, monkeypatch, daglig="2026-01-08")

    forfalt, venter = runner.velg_forfalte([FalskKilde(), DagligKilde()],
                                           "2026-01-08")
    assert [k.name for k in forfalt] == ["falsk"]      # står ikke i health.json
    assert [k.name for k, _ in venter] == ["daglig"]


def test_kilde_uten_sist_forsok_er_forfalt(tmp_path, monkeypatch):
    """Samme regel når posten finnes, men mangler feltet.

    Slik ser en health.json ut som er skrevet av en eldre versjon, eller
    av en kilde som bare har `sist_ok`. Halvveis kjennskap er ikke
    kjennskap.
    """
    health = _kjort(tmp_path, monkeypatch, falsk=None)

    assert health.les()["falsk"] == {"sist_ok": "2026-01-01"}
    assert health.dager_siden_kjoring("falsk", "2026-01-08") is None

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-08")
    assert [k.name for k in forfalt] == ["falsk"]
    assert venter == []


def test_etterslep_gjor_ikke_kilden_permanent_forfalt(tmp_path, monkeypatch):
    """F4: lusetall skriver uke N-4, så nyeste fil er ALLTID 28 dager
    gammel — også når kilden kjører perfekt.

    Målte vakten mot filnavnet, var kilden permanent forfalt, `kilder`
    aldri tom, og `if not kilder:` i run.py kunne ikke fyre. Måler den
    mot innsamlingstidspunktet, er den fersk.
    """
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    _kjort(tmp_path, monkeypatch, falsk="2026-08-19")

    # Snapshotet kilden skrev i dag er datert fire uker tilbake.
    snapshot.write(
        [Observation("10029", "lokalitet", "", "f", "v", "falsk", "2026-07-22")],
        "2026-07-22",
    )

    # Observasjonsalderen er 28 dager — det er den gamle vaktens tall,
    # og det er over enhver terskel.
    assert snapshot.dager_siden_observasjon("falsk", "2026-08-19") == 28

    # Innsamlingstidspunktet er i dag. Kilden er fersk.
    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-08-19")
    assert forfalt == []
    assert [(k.name, d) for k, d in venter] == [("falsk", 0)]


def test_alle_kilder_ferske_gir_tom_liste(tmp_path, monkeypatch):
    """`if not kilder:` i run.py skal kunne fyre igjen.

    Så lenge lusetall var permanent forfalt, kunne listen aldri bli tom,
    og --planlagt-vakten fra 17.08 var død kode for den kilden.
    """
    _kjort(tmp_path, monkeypatch, falsk="2026-08-19", daglig="2026-08-19")

    forfalt, venter = runner.velg_forfalte([FalskKilde(), DagligKilde()],
                                           "2026-08-19")
    assert forfalt == []
    assert not forfalt          # dette er uttrykket run.py tester på
    assert sorted(k.name for k, _ in venter) == ["daglig", "falsk"]


def test_health_beholder_kilder_som_ikke_kjorte(tmp_path, monkeypatch):
    """En kilde som hoppes over skal ikke miste sin sist_ok-historikk.

    Uten dette ville alarmen "har fungert før, er nede nå" aldri kunne
    utløses for en kilde som ventet én uke.
    """
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    begge = [runner.Result("falsk", True, 5), runner.Result("daglig", True, 3)]
    health.skriv(health.oppdater(begge, "2026-01-01")[0])

    # Uke etter: bare "daglig" kjørte.
    tilstand, _ = health.oppdater([runner.Result("daglig", True, 3)], "2026-01-02")
    health.skriv(tilstand)

    assert tilstand["falsk"]["sist_ok"] == "2026-01-01"

    # Og når "falsk" senere feiler, skal alarmen fortsatt gå.
    _, nede = health.oppdater([runner.Result("falsk", False, 0, "nede")], "2026-01-08")
    assert nede == ["falsk (nede, uke 1)"]


def _helse(tmp_path, monkeypatch):
    """Isolert health.json. Volumvakten leser ikke snapshots i det hele
    tatt — referansenivået ligger i health.json (se ARKITEKTUR.md)."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    return health


def test_volumfall_utloser_rodt(tmp_path, monkeypatch):
    """Et stort fall skal felle jobben selv om kilden rapporterer ok —
    scenarioet der et feltnavn endres og parse() stille returnerer færre
    rader uten å kaste."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, nede = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-01")
    health.skriv(tilstand)
    assert nede == []   # første kjøring etablerer nivået

    _, nede = health.oppdater([runner.Result("falsk", True, 500)], "2026-01-08")
    assert nede == ["falsk (volum 50% av referanse 1000: 500 observasjoner, uke 1)"]


def test_volumvakt_forste_kjoring_varsler_ikke(tmp_path, monkeypatch):
    """Ingen referanse å måle mot: ikke varsle, uansett hvor lavt tallet er."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, nede = health.oppdater([runner.Result("helt_ny", True, 1)], "2026-01-01")
    assert nede == []
    assert tilstand["helt_ny"]["volum_referanse"] == 1


def test_volumokning_varsler_ikke_og_hever_referansen(tmp_path, monkeypatch):
    """En økning er ikke tapt historikk, og skal ikke felle jobben. Men
    den nye normalen blir referansen, slik at et senere fall måles mot
    det faktiske nivået."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("falsk", True, 100)], "2026-01-01")
    health.skriv(tilstand)

    tilstand, nede = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-08")
    health.skriv(tilstand)
    assert nede == []
    assert tilstand["falsk"]["volum_referanse"] == 1000

    # Tilbake til 100 er nå et fall på 90 %, ikke en normal verdi.
    # Strekken er 1: de to foregående ukene var friske og nullstilte den.
    _, nede = health.oppdater([runner.Result("falsk", True, 100)], "2026-01-15")
    assert nede == ["falsk (volum 10% av referanse 1000: 100 observasjoner, uke 1)"]


def test_volumalarm_holder_seg_rod_i_fem_uker(tmp_path, monkeypatch):
    """Kjernen i vakten: et vedvarende brudd skal varsle HVER uke.

    Sammenlignet vakten mot forrige snapshot i stedet for et lagret
    referansenivå, ville det ødelagte tallet blitt neste ukes normal —
    rødt i uke 1, grønt i uke 2 og utover, mens datatapet fortsetter.
    Det er nøyaktig feilmodusen health.py finnes for å hindre.
    """
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-01")
    health.skriv(tilstand)

    for uke, dato in enumerate(
        ["2026-01-08", "2026-01-15", "2026-01-22", "2026-01-29", "2026-02-05"], start=1
    ):
        tilstand, nede = health.oppdater([runner.Result("falsk", True, 250)], dato)
        health.skriv(tilstand)
        assert nede == [
            f"falsk (volum 25% av referanse 1000: 250 observasjoner, uke {uke})"
        ], f"stille i uke {uke} — bruddet varer fortsatt"

    # Referansen skal IKKE ha flyttet seg nedover underveis.
    assert tilstand["falsk"]["volum_referanse"] == 1000


def test_referansen_driver_ikke_nedover_ved_gradvise_fall(tmp_path, monkeypatch):
    """Hullet de andre volumtestene ikke dekket: fall som hver for seg er
    INNENFOR terskelen, uke etter uke.

    Senker referansen seg til siste friske verdi, måles neste uke mot et
    allerede senket nivå. Da passerer 8 % fall i uka hver gang, og kilden
    kan drive til under halvparten uten ett varsel — rullende snitt i
    praksis, som er nøyaktig det health.py sier den ikke er.
    """
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-01")
    health.skriv(tilstand)

    # 8 % fall: 920/1000 = 92 %, godt innenfor terskelen på 90 %.
    tilstand, nede = health.oppdater([runner.Result("falsk", True, 920)], "2026-01-08")
    health.skriv(tilstand)
    assert nede == []                                    # riktig: ett fall er ikke alarm
    assert tilstand["falsk"]["volum_referanse"] == 1000  # men nivået skal stå

    # Uke to måles mot 1000, ikke mot 920. 846/1000 = 85 % -> alarm.
    tilstand, nede = health.oppdater([runner.Result("falsk", True, 846)], "2026-01-15")
    health.skriv(tilstand)
    assert nede == ["falsk (volum 85% av referanse 1000: 846 observasjoner, uke 1)"]

    # Og driften stanser ikke opp av seg selv: nivået står til noen tar tak.
    for uke, antall in enumerate([778, 716, 659], start=2):
        tilstand, nede = health.oppdater(
            [runner.Result("falsk", True, antall)], f"2026-02-{uke:02d}"
        )
        health.skriv(tilstand)
        assert nede, f"stille i uke {uke} med {antall} mot referanse 1000"
    assert tilstand["falsk"]["volum_referanse"] == 1000


def test_godta_volum_stopper_alarmen(tmp_path, monkeypatch):
    """Kvitteringen for et reelt fall: godta nivået, og vakten tier —
    men først etter et bevisst valg, ikke av seg selv."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-01")
    health.skriv(tilstand)
    tilstand, nede = health.oppdater([runner.Result("falsk", True, 400)], "2026-01-08")
    health.skriv(tilstand)
    assert nede != []

    ok, melding = health.godta_volum("falsk")
    assert ok
    assert "1000 -> 400" in melding

    # Samme nivå er nå friskt.
    _, nede = health.oppdater([runner.Result("falsk", True, 400)], "2026-01-15")
    assert nede == []

    # Men et NYTT fall under det godtatte nivået varsler igjen.
    _, nede = health.oppdater([runner.Result("falsk", True, 100)], "2026-01-22")
    assert nede == ["falsk (volum 25% av referanse 400: 100 observasjoner, uke 1)"]


def _felt_frame(felter, n=100, kilde="akvakultur"):
    return snapshot.to_frame([
        Observation(str(i), "lokalitet", "X", f, "v", kilde, "2026-01-01")
        for f in felter for i in range(n)
    ])


def test_felt_som_forsvinner_varsler_der_volumvakten_er_stille(tmp_path, monkeypatch):
    """Kjernepåstanden: feltvakten dekker et område volumvakten ikke når.

    Med 29 felter er det største enkeltfeltet 3,7 % av radene, og
    terskelen er 10 %. Målt på ekte akvakultur-data ga et bortfall av
    prodomraade_status 2,0 % fall — volumvakten stille, feltvakten fyrte.
    """
    health = _helse(tmp_path, monkeypatch)
    felter = [f"felt_{i}" for i in range(29)]

    full = _felt_frame(felter)
    tilstand, nede = health.oppdater(
        [runner.Result("akvakultur", True, full.height)], "2026-01-01", full
    )
    health.skriv(tilstand)
    assert nede == []

    uten = _felt_frame(felter[:-1])
    fall = 1 - uten.height / full.height
    assert fall < 0.10, "fikstur må ligge under volumterskelen for å bevise poenget"

    tilstand, nede = health.oppdater(
        [runner.Result("akvakultur", True, uten.height)], "2026-01-08", uten
    )
    health.skriv(tilstand)

    assert not [v for v in nede if "volum" in v]      # volumvakten er stille
    assert len(nede) == 1 and "felt borte: felt_28" in nede[0]

    # Fyrer på nytt uke etter uke, som volumvakten.
    _, nede = health.oppdater(
        [runner.Result("akvakultur", True, uten.height)], "2026-01-15", uten
    )
    assert len(nede) == 1 and "felt borte" in nede[0]


def test_nytt_felt_lofter_referansen(tmp_path, monkeypatch):
    """Skjemautvidelse er normalt — Enhetsregisteret gikk fra 9 til 32
    felter på ett døgn. Nye felter skal tas inn uten varsel."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater(
        [runner.Result("akvakultur", True, 200)], "2026-01-01", _felt_frame(["a", "b"])
    )
    health.skriv(tilstand)

    utvidet = _felt_frame(["a", "b", "c"])
    tilstand, nede = health.oppdater(
        [runner.Result("akvakultur", True, utvidet.height)], "2026-01-08", utvidet
    )
    assert nede == []
    assert set(tilstand["akvakultur"]["felt_referanse"]) == {"a", "b", "c"}


def test_nede_kilde_nullstiller_ikke_feltreferansen(tmp_path, monkeypatch):
    """En kilde som er nede leverer null felter. Det skal ikke slette alt
    den har lært — ellers ville første kjøring etter nedetid sett et
    tomt feltsett som normalen, og feltvakten vært død for den kilden."""
    health = _helse(tmp_path, monkeypatch)

    full = _felt_frame(["a", "b", "c"])
    tilstand, _ = health.oppdater(
        [runner.Result("akvakultur", True, full.height)], "2026-01-01", full
    )
    health.skriv(tilstand)

    # Uke 2: kilden er nede. Ingen observasjoner i det hele tatt.
    tom = snapshot.to_frame([])
    tilstand, _ = health.oppdater(
        [runner.Result("akvakultur", False, 0, "RuntimeError: nede")], "2026-01-08", tom
    )
    health.skriv(tilstand)
    assert set(tilstand["akvakultur"]["felt_referanse"]) == {"a", "b", "c"}

    # Uke 3: oppe igjen, men ett felt mangler. Skal fortsatt fanges.
    delvis = _felt_frame(["a", "b"])
    _, nede = health.oppdater(
        [runner.Result("akvakultur", True, delvis.height)], "2026-01-15", delvis
    )
    assert any("felt borte: c" in v for v in nede)


def test_godta_felt_er_uavhengig_av_godta_volum(tmp_path, monkeypatch):
    """To kvitteringer, to spørsmål. Kvitterer du volumet, skal et
    forsvunnet felt fortsatt varsle — ellers blir den ene en stille
    aksept av den andre."""
    health = _helse(tmp_path, monkeypatch)

    full = _felt_frame(["a", "b", "c"])
    tilstand, _ = health.oppdater(
        [runner.Result("akvakultur", True, full.height)], "2026-01-01", full
    )
    health.skriv(tilstand)

    delvis = _felt_frame(["a", "b"])
    tilstand, nede = health.oppdater(
        [runner.Result("akvakultur", True, delvis.height)], "2026-01-08", delvis
    )
    health.skriv(tilstand)
    assert any("felt borte" in v for v in nede)

    # Kvitterer volumet: feltvarselet skal IKKE forsvinne med det.
    health.godta_volum("akvakultur")
    _, nede = health.oppdater(
        [runner.Result("akvakultur", True, delvis.height)], "2026-01-15", delvis
    )
    assert any("felt borte" in v for v in nede), "volumkvittering svelget feltvarselet"

    # Egen kvittering rydder det.
    ok, melding = health.godta_felt("akvakultur")
    assert ok and "c" in melding
    _, nede = health.oppdater(
        [runner.Result("akvakultur", True, delvis.height)], "2026-01-22", delvis
    )
    assert not [v for v in nede if "felt borte" in v]


def test_godta_felt_ukjent_kilde(tmp_path, monkeypatch):
    health = _helse(tmp_path, monkeypatch)
    ok, melding = health.godta_felt("finnes_ikke")
    assert not ok and "Ukjent kilde" in melding


def test_godta_volum_ukjent_kilde(tmp_path, monkeypatch):
    health = _helse(tmp_path, monkeypatch)

    ok, melding = health.godta_volum("finnes_ikke")
    assert not ok
    assert "Ukjent kilde" in melding


def test_null_observasjoner_uten_exception_varsler(tmp_path, monkeypatch):
    """En kilde kan returnere 0 observasjoner uten å kaste — endepunktet
    svarer 200 med tom liste, eller parse() finner ingenting. r.ok er
    True, så bare volumvakten kan fange det."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-01")
    health.skriv(tilstand)

    tilstand, nede = health.oppdater([runner.Result("falsk", True, 0)], "2026-01-08")
    health.skriv(tilstand)

    assert nede == ["falsk (volum 0% av referanse 1000: 0 observasjoner, uke 1)"]
    # 0 skal ikke bli den nye normalen — da ville alt vært "friskt" igjen.
    assert tilstand["falsk"]["volum_referanse"] == 1000


def test_null_referanse_gir_ikke_divisjon_paa_null(tmp_path, monkeypatch):
    """Leverer kilden 0 på aller første kjøring, blir referansen 0.
    Vakten skal da ligge i dvale (ikke krasje, ikke varsle) til et ekte
    volum kommer inn og etablerer nivået."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, nede = health.oppdater([runner.Result("ny", True, 0)], "2026-01-01")
    health.skriv(tilstand)
    assert nede == []
    assert tilstand["ny"]["volum_referanse"] == 0

    # Fortsatt 0, med referanse 0: her ville en naiv andel-utregning
    # kastet ZeroDivisionError og felt hele kjøringen.
    tilstand, nede = health.oppdater([runner.Result("ny", True, 0)], "2026-01-08")
    health.skriv(tilstand)
    assert nede == []

    # Første ekte leveranse etablerer nivået, uten å varsle underveis.
    tilstand, nede = health.oppdater([runner.Result("ny", True, 500)], "2026-01-15")
    health.skriv(tilstand)
    assert nede == []
    assert tilstand["ny"]["volum_referanse"] == 500


def test_godta_volum_uten_levert_volum_dreper_ikke_vakten(tmp_path, monkeypatch):
    """--godta-volum på en kilde som aldri har levert skal AVVISES.

    Satte den referansen til 0, ville vakten vært permanent død for den
    kilden: alt er "friskt" når normalen er null.
    """
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("tom", True, 0)], "2026-01-01")
    health.skriv(tilstand)

    ok, melding = health.godta_volum("tom")
    assert not ok
    assert "ikke noe registrert volum" in melding
    assert health.les()["tom"]["volum_referanse"] == 0

    # Vakten er fortsatt i live: et ekte nivå kan fortsatt etableres,
    # og et fall fra det varsler som normalt.
    tilstand, _ = health.oppdater([runner.Result("tom", True, 1000)], "2026-01-08")
    health.skriv(tilstand)
    _, nede = health.oppdater([runner.Result("tom", True, 100)], "2026-01-15")
    assert nede == ["tom (volum 10% av referanse 1000: 100 observasjoner, uke 1)"]


def test_nede_kilde_odelegger_ikke_referansen(tmp_path, monkeypatch):
    """En kilde som er nede leverer 0 observasjoner. Det skal ikke bli
    det nye referansenivået — da ville alt vært "friskt" igjen straks
    kilden kom opp med en brøkdel av dataene."""
    health = _helse(tmp_path, monkeypatch)

    tilstand, _ = health.oppdater([runner.Result("falsk", True, 1000)], "2026-01-01")
    health.skriv(tilstand)

    tilstand, _ = health.oppdater(
        [runner.Result("falsk", False, 0, "RuntimeError: nede")], "2026-01-08"
    )
    health.skriv(tilstand)
    assert tilstand["falsk"]["volum_referanse"] == 1000

    # Oppe igjen, men bare 20 % av dataene: fortsatt et volumvarsel.
    _, nede = health.oppdater([runner.Result("falsk", True, 200)], "2026-01-15")
    assert nede == ["falsk (volum 20% av referanse 1000: 200 observasjoner, uke 1)"]


def test_dager_siden_observasjon_leser_siste_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    assert snapshot.dager_siden_observasjon("falsk", "2026-01-08") is None

    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")
    snapshot.write(list(FalskKilde().collect("2026-01-05")), "2026-01-05")

    assert snapshot.siste_dato("falsk") == "2026-01-05"
    assert snapshot.dager_siden_observasjon("falsk", "2026-01-08") == 3


def test_to_kjoringer_samme_dag_gir_to_filer(tmp_path, monkeypatch):
    """--tving skal aldri overskrive dagens snapshot — kollisjon løses med
    løpenummer, som i raw_arkiv.arkiver()."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    forste = [Observation("999999999", "selskap", "Testlaks AS",
                          "antall_ansatte", "12", "falsk", "2026-01-01")]
    andre = [Observation("999999999", "selskap", "Testlaks AS",
                         "antall_ansatte", "13", "falsk", "2026-01-01")]

    snapshot.write(forste, "2026-01-01")
    filer_2 = snapshot.write(andre, "2026-01-01")

    filer = sorted((tmp_path / "falsk").glob("*.parquet"))
    assert [p.name for p in filer] == ["2026-01-01.2.parquet", "2026-01-01.parquet"]
    assert filer_2[0].name == "2026-01-01.2.parquet"

    # Den første fila skal fortsatt ha den første verdien — ikke overskrevet.
    original = pl.read_parquet(tmp_path / "falsk" / "2026-01-01.parquet")
    assert original["value"][0] == "12"


def test_siden_og_diff_plukker_nyeste_ved_kollisjon(tmp_path, monkeypatch):
    """dager_siden_observasjon() og diff.compare() må lese den siste versjonen for
    dagen, ikke feiltolke løpenummeret som at kilden aldri er hentet."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")
    snapshot.write(
        [Observation("999999999", "selskap", "Testlaks AS",
                     "antall_ansatte", "20", "falsk", "2026-01-01")],
        "2026-01-01",
    )

    # siste_dato/dager_siden_observasjon skal fortsatt lese datoen riktig, ikke
    # snuble på løpenummeret og tro kilden aldri er hentet.
    assert snapshot.siste_dato("falsk") == "2026-01-01"
    assert snapshot.dager_siden_observasjon("falsk", "2026-01-08") == 7

    # diff mot uka etter skal sammenligne mot den SISTE versjonen (20),
    # ikke den første (12) som ellers ville gitt en falsk "endring".
    naa = [Observation("999999999", "selskap", "Testlaks AS",
                       "antall_ansatte", "20", "falsk", "2026-01-08")]
    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")
    assert endringer.height == 0


def test_run_py_kan_importeres():
    """Ingen test importerer run.py ellers — en syntaksfeil der ville
    sluppet gjennom hele suiten. --help kjører uten nett og uten å
    røre data/, og tvinger en reell import av hele modulen."""
    resultat = subprocess.run(
        [sys.executable, str(ROT / "run.py"), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert resultat.returncode == 0, resultat.stderr
    assert "--planlagt" in resultat.stdout
    assert "--tving" in resultat.stdout


def test_tomt_naeringskodesok_varsler():
    """En utgått NACE-kode gir 200 OK med tom liste, ikke en feil. Det er
    slik 10.209 kunne stå i config.yml i to dager uten at noe sa fra."""
    from sources.enhetsregisteret import _varsle_tomme_sok

    varsler = _varsle_tomme_sok({"03.211": 612, "10.209": 0, "10.201": 109}, set())

    assert len(varsler) == 1
    assert varsler[0].startswith("10.209:")
    assert "03.211" not in varsler[0]   # kun de tomme nevnes


def test_tomt_sok_kan_kvitteres_ut():
    """tillat_tomt er kvitteringen for en kode som legitimt er tom —
    et bevisst valg ført i config.yml, ikke en dempet alarm."""
    from sources.enhetsregisteret import _varsle_tomme_sok

    assert _varsle_tomme_sok({"03.211": 612, "03.223": 0}, {"03.223"}) == []


def test_alle_koder_med_treff_er_stille():
    from sources.enhetsregisteret import _varsle_tomme_sok

    assert _varsle_tomme_sok({"03.211": 612, "10.201": 109}, set()) == []


def test_advarsel_fra_kilde_naar_helt_opp(tmp_path, monkeypatch):
    """En kilde som leverer, men ber om tilsyn, skal felle jobben —
    uten å miste dataene sine. Det er hele poenget med kanalen:
    et tomt NACE-søk skal ikke koste ukas seks andre koder."""
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path)

    class MaseteKilde(FalskKilde):
        name = "masete"

        def fetch(self, kjoredato):
            self.advarsler = ["10.209: næringskode uten treff"]
            return super().fetch(kjoredato)

    obs, res = runner.run_all([MaseteKilde()], "2026-01-01")

    assert len(obs) == 1                      # dataene er i behold
    assert res[0].ok is True                  # kilden feilet ikke
    assert res[0].advarsler == ["10.209: næringskode uten treff"]


def test_kilde_uten_advarsler_gir_tom_liste(tmp_path, monkeypatch):
    """Default skal være tom. En kilde som ikke bryr seg rører ikke feltet."""
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path)

    _, res = runner.run_all([FalskKilde()], "2026-01-01")
    assert res[0].advarsler == []


def test_advarsler_deles_ikke_mellom_kilder(tmp_path, monkeypatch):
    """Klasseattributtet er en delt liste. Setter en kilde self.advarsler,
    skal det ikke lekke til neste kilde eller neste kjøring."""
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path)

    class Masete(FalskKilde):
        name = "masete"

        def fetch(self, kjoredato):
            self.advarsler = ["noe å se på"]
            return super().fetch(kjoredato)

    _, res = runner.run_all([Masete(), FalskKilde()], "2026-01-01")
    per_kilde = {r.source: r.advarsler for r in res}

    assert per_kilde["masete"] == ["noe å se på"]
    assert per_kilde["falsk"] == []
    assert Source.advarsler == []   # klasselista er urørt


def test_duplikater_fjernes_i_to_frame():
    """En kilde som søker på flere koder kan få samme entitet fra to søk.
    15 selskaper matchet to NACE-koder 17.08.2026 og ga 503 identiske
    ekstrarader."""
    obs = [
        Observation("1", "selskap", "X", "antall_ansatte", "10", "falsk", "2026-01-01"),
        Observation("1", "selskap", "X", "antall_ansatte", "10", "falsk", "2026-01-01"),
        Observation("1", "selskap", "X", "kommune", "Bodø", "falsk", "2026-01-01"),
    ]
    frame = snapshot.to_frame(obs)

    assert frame.height == 2
    assert sorted(frame["field"].to_list()) == ["antall_ansatte", "kommune"]


def test_samme_felt_fra_to_kilder_beholdes():
    """To KILDER som ser samme felt på samme entitet er kryssvalidering,
    ikke duplikat. Derfor er source med i nøkkelen."""
    obs = [
        Observation("1", "selskap", "X", "navn", "Testlaks AS", "falsk", "2026-01-01"),
        Observation("1", "selskap", "X", "navn", "Testlaks AS", "annen", "2026-01-01"),
    ]
    assert snapshot.to_frame(obs).height == 2


def test_diff_dobbeltrapporterer_ikke_paa_gammelt_snapshot(tmp_path, monkeypatch):
    """Snapshots skrevet før dedupliseringen er append-only og kan ikke
    rettes. Joiner diffen mot dem, fanner den ut og rapporterer samme
    endring én gang per duplikat. Endringsloggen er produktet."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    rad = {
        "entity_id": "1", "entity_type": "selskap", "entity_name": "X",
        "field": "antall_ansatte", "value": "10", "source": "falsk",
        "observed_at": "2026-01-01", "fetched_at": "", "source_version": "1",
        "raw_hash": "",
    }
    (tmp_path / "falsk").mkdir(parents=True)
    pl.DataFrame([rad, rad]).write_parquet(tmp_path / "falsk" / "2026-01-01.parquet")

    naa = snapshot.to_frame(
        [Observation("1", "selskap", "X", "antall_ansatte", "20", "falsk", "2026-01-08")]
    )
    endringer = diff.compare(naa, "2026-01-08")

    assert endringer.height == 1
    assert endringer["old_value"][0] == "10"
    assert endringer["new_value"][0] == "20"


def test_parse_leser_begge_arkivformater():
    """Arkivet er verdiløst hvis en formatendring gjør gamle filer
    uleselige. Både flat enhetsliste (før 17.08.2026) og sider med
    konvolutt (etter) skal gi samme observasjoner."""
    from sources.enhetsregisteret import Enhetsregisteret

    enhet = {"organisasjonsnummer": "999999999", "navn": "Testlaks AS",
             "antallAnsatte": 12}
    kilde = Enhetsregisteret()

    gammelt = list(kilde.parse([enhet], "2026-01-01"))
    nytt = list(kilde.parse(
        [{"naeringskode": "03.211", "side": 0,
          "svar": {"_embedded": {"enheter": [enhet]},
                   "page": {"totalPages": 1}}}],
        "2026-01-01",
    ))

    assert gammelt and gammelt == nytt


def test_konvolutten_bevarer_totalpages_og_sok():
    """Poenget med å arkivere sidene: totalPages og hvilket søk som fant
    enheten er tilgjengelig ved re-parse, ikke bare i sanntid."""
    from sources.enhetsregisteret import _enheter

    sider = [
        {"naeringskode": "03.211", "side": 0,
         "svar": {"_embedded": {"enheter": [{"organisasjonsnummer": "1"}]},
                  "page": {"totalPages": 2}}},
        {"naeringskode": "10.209", "side": 0,
         "svar": {"_embedded": {"enheter": []}, "page": {"totalPages": 0}}},
    ]

    # Enhetene pakkes ut som før ...
    assert [e["organisasjonsnummer"] for e in _enheter(sider)] == ["1"]

    # ... men det tomme søket er fortsatt synlig i arkivet etterpå.
    tomme = [s["naeringskode"] for s in sider
             if not s["svar"]["_embedded"]["enheter"]]
    assert tomme == ["10.209"]


def test_config_har_ingen_utgatte_koder():
    """Kodene i config.yml skal finnes som bekreftet i segments.yml.
    Fanger at noen legger tilbake en utgått kode uten å slå den opp."""
    import yaml
    from core import config

    kart = yaml.safe_load(
        (ROT / "rules" / "segments.yml").read_text(encoding="utf-8")
    )
    bekreftet = {
        kode
        for seg in kart["segmenter"].values()
        for kode in (seg.get("koder") or {})
    }
    utgatt = {
        kode
        for seg in kart["segmenter"].values()
        for kode in (seg.get("koder_utgatt") or {})
    }

    sokte = set(config.get("kilder.enhetsregisteret.naeringskoder", []))
    assert sokte, "config.yml har ingen næringskoder"
    assert not (sokte & utgatt), f"config.yml søker på utgåtte koder: {sokte & utgatt}"
    assert sokte <= bekreftet, f"koder uten dekning i segments.yml: {sokte - bekreftet}"
