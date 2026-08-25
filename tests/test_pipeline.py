"""Røyktest: kjører hele pipelinen med en falsk kilde, uten nett.

Poenget er ikke testdekning. Poenget er at du kan endre core/ og på
to sekunder vite om du ødela noe.
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from core import changelog, diff, feltnormal, health, runner, signals, snapshot
from core import utvalg
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
        # Datoen diffen sammenlignet mot. `krev_dato_etter_forrige` leser
        # den; uten den kan ingen regel skille "ny i registeret" fra "ny
        # i utvalget vårt".
        "forrige_observed_at": "2026-01-01",
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
        "krev_uendret", "krev_dato_etter_forrige",
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
    etiketten "Ny lokalitet i registeret".

    Selskapet må være FAKTISK nyregistrert for at regelen skal treffe i
    det hele tatt — derfor følger registreringsdatoen med som søskenrad.
    Se test_nytt_selskap_krever_registrering_etter_forrige_snapshot.
    """
    selskap = _signalrad("navn", None, "Nylaks AS",
                         change_type="ny", source="enhetsregisteret",
                         entity_type="selskap")
    registrert = _signalrad("registreringsdato", None, "2026-01-05",
                            change_type="ny", source="enhetsregisteret",
                            entity_type="selskap")
    lokalitet = _signalrad("navn", None, "TUHOLMANE Ø",
                           change_type="ny", source="akvakultur",
                           entity_type="lokalitet")

    scoret = signals.score(pl.DataFrame([selskap, registrert, lokalitet]))
    # Slår opp på (kilde, felt): begge navn-radene er "ny", og det er
    # nettopp dem regelparet skal skille.
    per_navnrad = {
        (k, f): sig for k, f, sig in
        scoret.select(["source", "field", "signal"]).iter_rows()
    }

    assert per_navnrad[("enhetsregisteret", "navn")] == "Nytt selskap i bransjen"
    assert per_navnrad[("akvakultur", "navn")] == "Ny lokalitet i registeret"


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

    filer = sorted(str(p.relative_to(tmp_path / "changelog"))
                   for p in (tmp_path / "changelog").glob("*/*.parquet"))
    assert filer == ["falsk/2026-01-08.parquet", "falsk/2026-01-15.parquet"]

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


def _endring_fra(kilde, dato, ny_verdi, eid="1"):
    return pl.DataFrame([{
        "entity_id": eid, "entity_type": "selskap", "entity_name": "Testlaks AS",
        "field": "antall_ansatte", "old_value": "10", "new_value": ny_verdi,
        "change_type": "endret", "source": kilde, "observed_at": dato,
    }])


def test_to_kilder_samme_dato_overlever_hverandre(tmp_path, monkeypatch):
    """F11: lusetall og sjotemperatur har samme etterslep og deler dato.

    Før 25.08.2026 var datoen alene filnavnet, og den andre skrivingen
    slettet den førstes rader. Det traff 238 datoer i 2012-2016.
    """
    from core import changelog

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    changelog.skriv(_endring_fra("lusetall", "2026-07-27", "20"), "2026-07-27")
    changelog.skriv(_endring_fra("sjotemperatur", "2026-07-27", "9.4"), "2026-07-27")

    alt = changelog.les_alt()
    assert sorted(alt["source"].to_list()) == ["lusetall", "sjotemperatur"]
    assert alt.height == 2, "den andre skrivingen skal ikke ha slettet den første"

    filer = sorted(str(f.relative_to(tmp_path / "changelog"))
                   for f in (tmp_path / "changelog").glob("*/*.parquet"))
    assert filer == ["lusetall/2026-07-27.parquet",
                     "sjotemperatur/2026-07-27.parquet"]


def test_rekjoring_av_samme_kilde_dobbeltforer_fortsatt_ikke(tmp_path, monkeypatch):
    """Skillet som gjør (kilde, dato) riktig: din egen fil overskrives,
    naboens finnes ikke for deg."""
    from core import changelog

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    changelog.skriv(_endring_fra("lusetall", "2026-07-27", "20"), "2026-07-27")
    changelog.skriv(_endring_fra("sjotemperatur", "2026-07-27", "9.4"), "2026-07-27")
    changelog.skriv(_endring_fra("lusetall", "2026-07-27", "20"), "2026-07-27")

    alt = changelog.les_alt()
    assert alt.height == 2
    assert sorted(alt["source"].to_list()) == ["lusetall", "sjotemperatur"]


def test_skriv_krever_en_kilde_per_fil(tmp_path, monkeypatch):
    """Filnavnet bærer kilden, så innholdet må være enig med seg selv."""
    from core import changelog

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")

    blandet = pl.concat([_endring_fra("lusetall", "2026-07-27", "20"),
                         _endring_fra("sjotemperatur", "2026-07-27", "9.4")])
    with pytest.raises(ValueError, match="skriv_per_dato"):
        changelog.skriv(blandet, "2026-07-27")


def test_skriv_per_dato_deler_paa_kilde_og_dato(tmp_path, monkeypatch):
    """Én kjøring, to kilder, to datoer -> fire filer, ingen overskriving."""
    from core import changelog

    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    alle = pl.concat([
        _endring_fra("lusetall", "2026-07-27", "20"),
        _endring_fra("sjotemperatur", "2026-07-27", "9.4"),
        _endring_fra("enhetsregisteret", "2026-08-24", "31"),
    ])
    skrevet = changelog.skriv_per_dato(alle)

    assert len(skrevet) == 3
    assert sorted(str(f.relative_to(tmp_path / "changelog")) for f in skrevet) == [
        "enhetsregisteret/2026-08-24.parquet",
        "lusetall/2026-07-27.parquet",
        "sjotemperatur/2026-07-27.parquet",
    ]
    assert changelog.les_alt().height == 3


def test_gammel_flat_fil_med_samme_kilde_avvises(tmp_path, monkeypatch):
    """Det ene tvetydige tilfellet i migreringen: avvis, ikke gjett.

    Den flate fila fra før omleggingen bærer allerede kilden. Skrives
    <kilde>/<dato>.parquet ved siden av, teller les_alt() radene to ganger.
    """
    from core import changelog

    kat = tmp_path / "changelog"
    kat.mkdir()
    monkeypatch.setattr(changelog, "CHANGELOG_DIR", kat)
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    _endring_fra("lusetall", "2026-07-27", "20").write_parquet(
        kat / "2026-07-27.parquet")

    with pytest.raises(changelog.Kildekollisjon, match="2026-07-27.parquet"):
        changelog.skriv(_endring_fra("lusetall", "2026-07-27", "21"), "2026-07-27")


def test_gammel_flat_fil_med_annen_kilde_er_ingen_kollisjon(tmp_path, monkeypatch):
    """Det VANLIGE tilfellet: lusetall ligger flatt i 2012-2016, og
    sjotemperatur backfilles inn ved siden av. De bærer hver sine rader."""
    from core import changelog

    kat = tmp_path / "changelog"
    kat.mkdir()
    monkeypatch.setattr(changelog, "CHANGELOG_DIR", kat)
    monkeypatch.setattr(changelog, "GAMMEL_FIL", tmp_path / "finnes-ikke.parquet")

    _endring_fra("lusetall", "2014-06-02", "20").write_parquet(
        kat / "2014-06-02.parquet")

    changelog.skriv(_endring_fra("sjotemperatur", "2014-06-02", "9.4"),
                    "2014-06-02")

    alt = changelog.les_alt()
    assert alt.height == 2
    assert sorted(alt["source"].to_list()) == ["lusetall", "sjotemperatur"]


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


def _kjort(tmp_path, monkeypatch, **sist_ok):
    """Skriv en health.json der hver kilde sist LYKTES på gitt dato.

    Frekvensvakten leser siste vellykkede innsamling herfra — ikke
    datoen på nyeste snapshotfil (F4), og ikke siste forsøk (F8).
    Verdien None gir en post uten `sist_ok`: kilden finnes, den ble
    forsøkt i dag, men den har aldri levert. Det er nøyaktig posten
    lusetall hadde i produksjon 24.08.
    """
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    health.skriv({
        kilde: ({"sist_ok": dato, "sist_forsok": dato, "feil_paa_rad": 0}
                if dato else
                {"sist_ok": None, "sist_forsok": "2026-01-08",
                 "feil_paa_rad": 3})
        for kilde, dato in sist_ok.items()
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


def test_kilde_som_aldri_har_lykkes_er_forfalt(tmp_path, monkeypatch):
    """F8: posten finnes og sist_forsok er I DAG, men sist_ok er null.

    Dette er lusetall 24.08: tre forsøk samme dag, alle invalid_client,
    `feil_paa_rad=3`, ikke én rad hentet. Vakten leste `sist_forsok`,
    så «hentet i dag», og satte kilden i syv dagers karantene. Uke 31
    måtte hentes med --tving.

    Halvveis kjennskap er ikke kjennskap: et forsøk sier ingenting om
    hva vi har.
    """
    health = _kjort(tmp_path, monkeypatch, falsk=None)

    assert health.les()["falsk"]["sist_forsok"] == "2026-01-08"   # forsøkt i dag
    assert health.les()["falsk"]["sist_ok"] is None               # aldri hentet
    assert health.dager_siden_ok("falsk", "2026-01-08") is None

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-08")
    assert [k.name for k in forfalt] == ["falsk"]
    assert venter == []


def _health(tmp_path, monkeypatch, poster):
    """Skriv health.json rått, slik at sist_ok og sist_forsok kan skille lag.

    `_kjort` holder de to i takt, som de er når alt går bra. Testene
    under F8 handler nettopp om uka der de IKKE er i takt.
    """
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    health.skriv(poster)
    return health


def test_kilde_som_feilet_i_gaar_velges_i_dag(tmp_path, monkeypatch):
    """Kravet fra F8: en feilet kilde forsøkes igjen ved NESTE kjøring.

    Mandag 05.01 lyktes. Mandag 12.01 kjørte cron og feilet. Tirsdag
    13.01 prøvde vi igjen, og det feilet også. Onsdag 14.01 kjører vi.

    Målt mot forsøket var kilden «hentet i går» — seks dager igjen av
    karantenen, og da er uka forbi før den slipper ut. Målt mot siste
    suksess er den ni dager gammel: forfalt, og uka kan fortsatt reddes.
    """
    _health(tmp_path, monkeypatch, {
        "falsk": {"sist_ok": "2026-01-05", "sist_forsok": "2026-01-13",
                  "feil_paa_rad": 2},
    })

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-14")
    assert [k.name for k in forfalt] == ["falsk"]
    assert venter == []


def test_kilde_som_lyktes_i_gaar_velges_ikke(tmp_path, monkeypatch):
    """Motsatt vei: vakten skal fortsatt holde igjen.

    Fiksen får ikke bli «kjør alltid». Lyktes kilden i går, ligger
    gårsdagens data på disk, og en henting til er en .2-fil uten nytt
    innhold.
    """
    _kjort(tmp_path, monkeypatch, falsk="2026-01-13")

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-14")
    assert forfalt == []
    assert [(k.name, d) for k, d in venter] == [("falsk", 1)]


def test_feilet_i_dag_med_gammel_suksess_velges(tmp_path, monkeypatch):
    """Selve F8-tilfellet, med begge felt satt og uenige.

    `sist_forsok` er i dag — kilden ble forsøkt for en time siden og
    feilet. `sist_ok` er åtte dager gammel. Leser vakten forsøket, er
    svaret «hentet i dag, går hver 7. dag», og perioden som mangler blir
    aldri hentet. Leser den suksessen, er svaret 8 >= 7: forfalt.
    """
    health = _health(tmp_path, monkeypatch, {
        "falsk": {"sist_ok": "2026-01-06", "sist_forsok": "2026-01-14",
                  "feil_paa_rad": 1},
    })

    assert health.dager_siden_ok("falsk", "2026-01-14") == 8

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-14")
    assert [k.name for k in forfalt] == ["falsk"]
    assert venter == []


def test_feilet_forsok_forkorter_ikke_karantenen(tmp_path, monkeypatch):
    """Et forsøk skal verken forlenge eller forkorte noe.

    Feiler kilden i dag etter en fersk suksess i går, er ingenting i
    fare: gårsdagens data ligger der. Vakten teller fortsatt fra
    suksessen, og kilden venter — dette er den bevisste følgen av å måle
    det vi HAR i stedet for det vi PRØVDE.
    """
    _health(tmp_path, monkeypatch, {
        "falsk": {"sist_ok": "2026-01-13", "sist_forsok": "2026-01-14",
                  "feil_paa_rad": 1},
    })

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-14")
    assert forfalt == []
    assert [(k.name, d) for k, d in venter] == [("falsk", 1)]


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


# ------------------------------------------------- personformer (ENK)
#
# Revisjonen 22.08.2026 fant 34 enkeltpersonforetak i hvert eneste
# enhetsregister-snapshot. Et ENK er ikke et eget rettssubjekt — foretaket
# ER innehaveren — så navn, kommune, postnummer og konkursflagg er
# opplysninger om en identifiserbar fysisk person. Testene under låser
# begge halvdelene: filteret i kilden, og vakten som fanger at filteret
# svikter.


def _enhet(orgnr: str, form: str, navn: str = "Testlaks",
           gate: str = "Fjordveien 1") -> dict:
    return {
        "organisasjonsnummer": orgnr,
        "navn": navn,
        "organisasjonsform": {"kode": form, "beskrivelse": form},
        "forretningsadresse": {"kommune": "BODØ", "postnummer": "8000",
                               "adresse": [gate]},
        "antallAnsatte": 3,
    }


def test_enk_gir_ingen_observasjoner():
    """Filteret er i kilden, ikke i en vask etterpå."""
    from sources.enhetsregisteret import Enhetsregisteret

    obs = list(Enhetsregisteret().parse(
        [_enhet("111111111", "ENK"), _enhet("222222222", "AS")], "2026-08-24"
    ))

    assert {o.entity_id for o in obs} == {"222222222"}


def test_da_og_ans_beholdes():
    """Et bevisst valg, ikke en forglemmelse: DA og ANS er egne
    rettssubjekter, og deltakerne står bare i rolleregisteret vi aldri
    spør etter. Se core/persondata.py. Faller denne, er valget endret —
    og da skal beslutningen endres med den."""
    from sources.enhetsregisteret import Enhetsregisteret

    obs = list(Enhetsregisteret().parse(
        [_enhet("333333333", "DA"), _enhet("444444444", "ANS")], "2026-08-24"
    ))

    assert {o.entity_id for o in obs} == {"333333333", "444444444"}


def test_gammelt_arkiv_med_enk_reparses_uten_enk():
    """Arkivfilene fra før 22.08.2026 inneholder ENK. En re-parse skal
    ikke føre dem inn igjen — derfor filtrerer parse() også, ikke bare
    fetch()."""
    from sources.enhetsregisteret import Enhetsregisteret

    flatt_gammelt_arkiv = [_enhet("111111111", "ENK"), _enhet("222222222", "AS")]
    obs = list(Enhetsregisteret().parse(flatt_gammelt_arkiv, "2026-08-17"))

    assert all(o.entity_id != "111111111" for o in obs)


def test_fetch_arkiverer_ikke_personformer(monkeypatch, capsys):
    """Rå-arkivet lagrer hele API-svaret, inkludert gateadressen som
    FELTER holder utenfor snapshotet. Filtrerer vi først i parse(), ligger
    hjemmeadressen til hvert ENK i arkivet uansett."""
    from sources import _http
    from sources import enhetsregisteret as er
    from sources.enhetsregisteret import Enhetsregisteret

    # `from core.config import get` binder navnet i kildemodulen.
    monkeypatch.setattr(er, "get", lambda nokkel, standard=None: {
        "kilder.enhetsregisteret.naeringskoder": ["03.211"],
        "kilder.enhetsregisteret.sidestorrelse": 100,
        "kilder.enhetsregisteret.tillat_tomt": [],
    }.get(nokkel, standard))

    class FalsktSvar:
        def json(self):
            return {
                "_embedded": {"enheter": [
                    _enhet("111111111", "ENK", gate="Hjemmeveien 7"),
                    _enhet("222222222", "AS")]},
                "page": {"totalPages": 1},
            }

    monkeypatch.setattr(_http, "get", lambda *a, **kw: FalsktSvar())

    sider = Enhetsregisteret().fetch("2026-08-24")
    arkivert = json.dumps(sider, ensure_ascii=False)

    assert "111111111" not in arkivert      # ENK er ute av arkivet
    assert "Hjemmeveien" not in arkivert    # og hjemmeadressen med den
    assert "222222222" in arkivert          # selskapet står igjen

    # Konvolutten er urørt: en avkortet paginering skal fortsatt kunne
    # oppdages ved re-parse.
    assert sider[0]["svar"]["page"]["totalPages"] == 1
    assert sider[0]["naeringskode"] == "03.211"

    # Antallet skrives til kjøringsloggen, slik at et hopp er synlig.
    assert "1 foretak filtrert bort som fysisk person (ENK 1)" in capsys.readouterr().out


def test_side_med_bare_personformer_stopper_ikke_pagineringen(monkeypatch):
    """Pagineringen styres av svaret fra Brreg, ikke av hva som ble igjen
    etter filteret. Telles den etter, bryter løkka på en side der alle
    treffene var ENK — og mister sidene bak."""
    from sources import _http
    from sources import enhetsregisteret as er
    from sources.enhetsregisteret import Enhetsregisteret

    # `from core.config import get` binder navnet i kildemodulen.
    monkeypatch.setattr(er, "get", lambda nokkel, standard=None: {
        "kilder.enhetsregisteret.naeringskoder": ["03.211"],
        "kilder.enhetsregisteret.sidestorrelse": 100,
        "kilder.enhetsregisteret.tillat_tomt": [],
    }.get(nokkel, standard))

    sider_ut = [
        {"_embedded": {"enheter": [_enhet("111111111", "ENK")]},
         "page": {"totalPages": 2}},
        {"_embedded": {"enheter": [_enhet("222222222", "AS")]},
         "page": {"totalPages": 2}},
    ]

    class FalsktSvar:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    kalt = []

    def falsk_get(*a, **kw):
        kalt.append(kw.get("params", {}).get("page"))
        return FalsktSvar(sider_ut[len(kalt) - 1])

    monkeypatch.setattr(_http, "get", falsk_get)

    sider = Enhetsregisteret().fetch("2026-08-24")

    assert kalt == [0, 1]                      # side 2 ble faktisk hentet
    assert "222222222" in json.dumps(sider)
    assert "111111111" not in json.dumps(sider)


def test_tomt_sok_varsler_ikke_naar_treffene_var_personformer(monkeypatch):
    """Varselet om tomme næringskodesøk spør «svarte Brreg med noe».
    Telles treffene etter filteret, ser en kode som legitimt bare
    inneholder ENK ut som en utgått kode."""
    from sources import _http
    from sources import enhetsregisteret as er
    from sources.enhetsregisteret import Enhetsregisteret

    # `from core.config import get` binder navnet i kildemodulen.
    monkeypatch.setattr(er, "get", lambda nokkel, standard=None: {
        "kilder.enhetsregisteret.naeringskoder": ["03.211"],
        "kilder.enhetsregisteret.sidestorrelse": 100,
        "kilder.enhetsregisteret.tillat_tomt": [],
    }.get(nokkel, standard))

    class FalsktSvar:
        def json(self):
            return {"_embedded": {"enheter": [_enhet("111111111", "ENK")]},
                    "page": {"totalPages": 1}}

    monkeypatch.setattr(_http, "get", lambda *a, **kw: FalsktSvar())

    kilde = Enhetsregisteret()
    kilde.fetch("2026-08-24")

    assert kilde.advarsler == []


def _obs_form(orgnr: str, form: str, observed_at: str = "2026-08-24") -> Observation:
    return Observation(
        entity_id=orgnr,
        entity_type="selskap",
        entity_name="Testlaks",
        field="organisasjonsform",
        value=form,
        source="enhetsregisteret",
        observed_at=observed_at,
    )


def test_vakten_nekter_snapshot_med_personform(tmp_path, monkeypatch):
    """Et filter noen glemmer å oppdatere er ikke en garanti. Vakten
    ligger i trakta alt skrives gjennom, som datokontrollen."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    with pytest.raises(ValueError, match="ENK"):
        snapshot.write([_obs_form("111111111", "ENK")], "2026-08-24")

    assert list(tmp_path.rglob("*.parquet")) == []   # ingenting ble skrevet


def test_vakten_slipper_gjennom_selskapsformer(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    filer = snapshot.write(
        [_obs_form("222222222", "AS"), _obs_form("333333333", "DA")],
        "2026-08-24",
    )

    assert len(filer) == 1
    assert pl.read_parquet(filer[0]).height == 2


def test_vakten_lar_seg_ikke_lure_av_store_og_smaa_bokstaver(tmp_path, monkeypatch):
    """Verdien er tekst fra et API. En kilde som skriver 'enk' skal ikke
    slippe forbi en vakt som bare kjenner 'ENK'."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    with pytest.raises(ValueError):
        snapshot.write([_obs_form("111111111", " enk ")], "2026-08-24")


def test_vakten_faller_ikke_paa_kilder_uten_organisasjonsform(tmp_path, monkeypatch):
    """Akvakulturregisteret oppgir ingen organisasjonsform. Vakten skal
    være stille der, ikke kaste på et felt som ikke finnes."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    lokalitet = Observation(
        entity_id="10029", entity_type="lokalitet", entity_name="TUHOLMANE",
        field="kapasitet", value="2340.0", source="akvakultur",
        observed_at="2026-08-24",
    )

    assert len(snapshot.write([lokalitet], "2026-08-24")) == 1


def test_samme_enk_fra_to_naeringskoder_telles_en_gang(monkeypatch, capsys):
    """Kilden søker på ni koder, og samme foretak kan komme i retur fra
    flere. Teller loggen forekomster i stedet for foretak, hopper tallet
    av at en næringskode ble lagt til — ikke av at flere personer kom inn
    i utvalget."""
    from sources import _http
    from sources import enhetsregisteret as er
    from sources.enhetsregisteret import Enhetsregisteret

    monkeypatch.setattr(er, "get", lambda nokkel, standard=None: {
        "kilder.enhetsregisteret.naeringskoder": ["03.211", "03.300"],
        "kilder.enhetsregisteret.sidestorrelse": 100,
        "kilder.enhetsregisteret.tillat_tomt": [],
    }.get(nokkel, standard))

    class FalsktSvar:
        def json(self):
            return {"_embedded": {"enheter": [_enhet("111111111", "ENK"),
                                              _enhet("222222222", "AS")]},
                    "page": {"totalPages": 1}}

    monkeypatch.setattr(_http, "get", lambda *a, **kw: FalsktSvar())

    Enhetsregisteret().fetch("2026-08-24")

    assert "1 foretak filtrert bort" in capsys.readouterr().out


# -------------------------------------------------- leseveien er én dør
#
# Snapshotene fra 16.-17.08.2026 inneholder 34 ENK hver, og de filene er
# append-only. Filteret er derfor ikke en opprydding som blir ferdig, men
# en betingelse hver eneste lesing må oppfylle. Testene under håndhever
# begge halvdelene: at filteret virker, og at ingen ny lesevei kan gå
# utenom det uten å felle suiten.


def _snapshot_med_enk(observed_at: str = "2026-08-17") -> list[Observation]:
    """Et snapshot slik de gamle filene ser ut: ENK og AS side om side,
    med alle feltene utfylt for begge."""
    rader = []
    for orgnr, form, navn in [("111111111", "ENK", "Kari Nordmann"),
                              ("222222222", "AS", "Testlaks AS")]:
        for felt, verdi in [("organisasjonsform", form), ("navn", navn),
                            ("kommune", "BODØ"), ("postnummer", "8000"),
                            ("konkurs", "false")]:
            rader.append(Observation(
                entity_id=orgnr, entity_type="selskap", entity_name=navn,
                field=felt, value=verdi, source="enhetsregisteret",
                observed_at=observed_at,
            ))
    return rader


def _skriv_gammelt_snapshot(rader, observed_at="2026-08-17"):
    """Skriver forbi snapshot.write(), som med rette nekter ENK.

    De gamle filene ble skrevet før vakten fantes, og en test som ikke kan
    lage dem kan ikke bevise at leseveien håndterer dem."""
    mappe = snapshot.RAW_DIR / "enhetsregisteret"
    mappe.mkdir(parents=True, exist_ok=True)
    ramme = pl.DataFrame([o.as_dict() for o in rader]).select(snapshot.SCHEMA)
    ramme.write_parquet(mappe / f"{observed_at}.parquet")


def test_previous_filtrerer_enk_ut_av_gammelt_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)
    _skriv_gammelt_snapshot(_snapshot_med_enk())

    gammelt = snapshot.previous("enhetsregisteret", before="2026-08-24")

    assert gammelt is not None
    assert gammelt["entity_id"].unique().to_list() == ["222222222"]


def test_les_mellom_filtrerer_enk(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)
    _skriv_gammelt_snapshot(_snapshot_med_enk())

    [(_, ramme)] = snapshot.les_mellom("enhetsregisteret", "2026-08-01", "2026-08-31")

    assert "111111111" not in ramme["entity_id"].to_list()


def test_hele_entiteten_fjernes_ikke_bare_formraden(tmp_path, monkeypatch):
    """Fjernes bare raden som sier ENK, står navnet, kommunen og
    konkursflagget igjen — persondataene uten etiketten som gjorde dem
    gjenkjennelige. Det er verre enn ingen filtrering, fordi neste
    revisjon ikke ville funnet dem."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)
    _skriv_gammelt_snapshot(_snapshot_med_enk())

    ramme = snapshot.previous("enhetsregisteret", before="2026-08-24")

    assert "Kari Nordmann" not in ramme["value"].to_list()
    assert "Kari Nordmann" not in ramme["entity_name"].to_list()
    assert ramme.height == 5              # kun AS-ets fem felter står igjen


def test_enk_som_forsvinner_blir_ikke_en_endring(tmp_path, monkeypatch):
    """Den konkrete konsekvensen av at leseveien filtrerer.

    Uten filteret ser diffen ENK i forrige snapshot og ikke i dette, og
    fører hver av dem inn i changeloggen som change_type «borte» — med
    navn. Filteret i kilden ville da ha FLYTTET persondataene fra
    snapshotene til endringsloggen, ikke fjernet dem."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)
    _skriv_gammelt_snapshot(_snapshot_med_enk("2026-08-17"))

    # Denne uka: kilden filtrerer, så bare AS-et kommer inn.
    naa = snapshot.to_frame([o for o in _snapshot_med_enk("2026-08-24")
                             if o.entity_id == "222222222"])
    endringer = diff.compare(naa, "2026-08-24")

    assert endringer.height == 0
    assert "111111111" not in endringer["entity_id"].to_list()


def test_akvakultur_gaar_urort_gjennom_filteret(tmp_path, monkeypatch):
    """En kilde uten organisasjonsformer skal ikke tape rader."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    lokalitet = [Observation(
        entity_id="10029", entity_type="lokalitet", entity_name="TUHOLMANE",
        field=f, value="x", source="akvakultur", observed_at="2026-08-17",
    ) for f in ["kapasitet", "kommune", "prodomraade_status"]]
    snapshot.write(lokalitet, "2026-08-17")

    assert snapshot.previous("akvakultur", before="2026-08-24").height == 3


def _kildefiler() -> list[Path]:
    """Alle .py-filer i repoet som ikke er tester eller virtualenv."""
    return [p for p in ROT.rglob("*.py")
            if ".venv" not in p.parts and "tests" not in p.parts
            and "__pycache__" not in p.parts]


def test_ingen_leser_snapshots_utenom_les():
    """Beviser at det ikke finnes en vei rundt filteret.

    To krav, og begge må holde:

    1. core/snapshot.py leser parquet nøyaktig ETT sted — `_les()`. En ny
       funksjon der som kaller read_parquet direkte feller denne testen.
    2. Ingen annen modul kombinerer kjennskap til RAW_DIR med en
       parquet-lesing. En ny lesevei må gå gjennom previous() eller
       les_mellom(), som begge går gjennom `_les()`.

    Faller denne, ikke demp den: enten skal den nye veien gå gjennom
    `_les()`, eller så er filteret ikke lenger en garanti.
    """
    def lesekall(fil: Path) -> list[str]:
        """Faktiske parquet-lesekall, funnet i syntakstreet.

        AST og ikke tekstsøk: docstringene i snapshot.py OMTALER
        read_parquet for å forklare regelen, og en test som teller
        forekomster i tekst ville talt forklaringen som et brudd."""
        treff = []
        for node in ast.walk(ast.parse(fil.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("read_parquet", "scan_parquet"):
                    treff.append(f"{node.func.attr} linje {node.lineno}")
        return treff

    i_snapshot = lesekall(ROT / "core" / "snapshot.py")
    assert len(i_snapshot) == 1, (
        f"core/snapshot.py leser parquet {len(i_snapshot)} steder, ikke ett: "
        f"{i_snapshot}. Persondatafilteret ligger i _les() — gå gjennom den."
    )

    for fil in _kildefiler():
        if fil == ROT / "core" / "snapshot.py":
            continue
        if "RAW_DIR" not in fil.read_text(encoding="utf-8"):
            continue
        assert not lesekall(fil), (
            f"{fil.relative_to(ROT)} kjenner både RAW_DIR og "
            f"{lesekall(fil)} — det er en lesevei utenom snapshot._les(), "
            f"og da filtreres ikke enkeltpersonforetakene bort."
        )


def test_changelog_og_predictions_leser_ikke_raadata():
    """De to andre modulene som leser parquet leser sine EGNE filer —
    changelog/ og predictions/ — ikke raw/. Denne testen fanger at en av
    dem begynner å lese snapshots direkte."""
    for modul in ["changelog.py", "predictions.py"]:
        tekst = (ROT / "core" / modul).read_text(encoding="utf-8")
        assert "RAW_DIR" not in tekst, (
            f"core/{modul} kjenner RAW_DIR. Leser den snapshots, må den gå "
            f"gjennom snapshot.les_mellom() — se test_ingen_leser_snapshots_utenom_les."
        )


# ==================================================== utvalgsutvidelse
#
# F9: diff.compare() undertrykte nye FELTNAVN, men gjorde ingenting med
# nye ENTITETER som kom inn fordi utvalget ble utvidet. 24.08.2026 var
# 25804 av 26673 endringer (96,7 %) av det slaget.


def _obs(eid, felt, verdi, dato, kilde="falsk", navn="Testlaks AS",
         utvalg_json=""):
    return Observation(
        entity_id=eid, entity_type="selskap", entity_name=navn,
        field=felt, value=verdi, source=kilde, observed_at=dato,
        utvalg=utvalg_json,
    )


def _skriv(monkeypatch, tmp_path, dato, rader, koder):
    """Snapshot med et oppgitt utvalg, skrevet gjennom den ekte veien."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    merket = utvalg.serialiser({"naeringskoder": koder})
    obs = [_obs(eid, felt, verdi, dato, utvalg_json=merket)
           for eid, felt, verdi in rader]
    snapshot.write(obs, dato)
    return obs


def test_utvalg_folger_snapshotet_og_kan_leses_tilbake(tmp_path, monkeypatch):
    """Rotårsaken til F9: søket lå bare i config.yml og i git."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "A")], ["03.211", "03.212"])

    lest = snapshot.previous("falsk", before="2026-01-08")
    assert snapshot.utvalg_i(lest) == {"naeringskoder": ["03.211", "03.212"]}


def test_gammelt_snapshot_uten_utvalg_leses_som_vet_ikke(tmp_path, monkeypatch):
    """Filene fra før 24.08.2026 har ingen utvalgskolonne, og de er
    append-only. De skal kunne leses, og de skal lese som «vet ikke» —
    ikke som «ingen filtrering»."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    katalog = tmp_path / "raw" / "falsk"
    katalog.mkdir(parents=True)
    pl.DataFrame({
        "entity_id": ["1"], "entity_type": ["selskap"], "entity_name": ["A"],
        "field": ["navn"], "value": ["A"], "source": ["falsk"],
        "observed_at": ["2026-01-01"],
    }).write_parquet(katalog / "2026-01-01.parquet")

    lest = snapshot.previous("falsk", before="2026-01-08")
    assert "utvalg" in lest.columns, "kolonnen legges til av _les()"
    assert snapshot.utvalg_i(lest) is None, "tom streng betyr vet ikke"


def test_ny_entitet_ved_utvidet_utvalg_merkes(tmp_path, monkeypatch):
    """Selve F9, i miniatyr: kode 03.300 legges til, og selskapet som
    kommer inn med den er ikke en hendelse i verden."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "Gammel AS"), ("1", "kommune", "Bodø")],
           ["03.211"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08",
                 [("1", "navn", "Gammel AS"), ("1", "kommune", "Bodø"),
                  ("2", "navn", "Nykommer AS"), ("2", "kommune", "Tromsø")],
                 ["03.211", "03.300"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")

    typer = dict(endringer.group_by("change_type").len().iter_rows())
    assert typer == {diff.UTVALGSUTVIDELSE: 2}, typer
    assert set(endringer["entity_id"].to_list()) == {"2"}
    assert diff.bevegelse(endringer).height == 0, "ingen bevegelse denne uka"


def test_ekte_nyregistrering_overlever_en_utvidelsesuke(tmp_path, monkeypatch):
    """Unntaket fra merkingen, og grunnen til at Source.startdatofelt finnes.

    To selskaper kommer inn samme uke som utvalget utvides. Det ene ble
    registrert i 1998 og har alltid vært der; det andre ble registrert
    etter forrige snapshot. Merkes begge, forsvinner en ekte hendelse i
    støyen fra utvidelsen — samme tap som utvidelsen selv skaper, bare
    med motsatt fortegn.
    """
    # `registreringsdato` må finnes i FORRIGE snapshot også. Er feltnavnet
    # nytt, filtrerer skjemautvidelsesregelen det bort før noen rekker å
    # lese datoen — og da har utvidelsesuka ingen fødselsdato å skille på.
    # Verdt å vite hvis en kilde legger til startdatofeltet sitt samtidig
    # som utvalget vokser.
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "Gammel AS"), ("1", "registreringsdato", "2001-03-04")],
           ["03.211"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08", [
        ("1", "navn", "Gammel AS"), ("1", "registreringsdato", "2001-03-04"),
        ("2", "navn", "Innhentet AS"), ("2", "registreringsdato", "1998-04-01"),
        ("3", "navn", "Helt Fersk AS"), ("3", "registreringsdato", "2026-01-05"),
    ], ["03.211", "03.300"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08",
                             startdatofelt="registreringsdato")

    per_entitet = {
        e: t for e, f, t in
        endringer.select(["entity_id", "field", "change_type"]).iter_rows()
        if f == "navn"
    }
    assert per_entitet == {"2": diff.UTVALGSUTVIDELSE, "3": "ny"}

    # Og hele veien ut: signalregelen skal se den ene, ikke den andre.
    traff = signals.treff(signals.score(
        endringer.with_columns(pl.lit("enhetsregisteret").alias("source"))
    ))
    assert [(r["entity_id"], r["signal"]) for r in traff.iter_rows(named=True)] \
        == [("3", "Nytt selskap i bransjen")]


def test_uten_startdatofelt_merkes_alle_nye(tmp_path, monkeypatch):
    """En kilde som ikke kan etterprøves får ingen tvil til gode. Det er
    den strenge siden, og den er riktig her: uten en startdato finnes det
    ingen grunn til å påstå at entiteten er ny i verden."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "Gammel AS"), ("1", "registreringsdato", "2001-03-04")],
           ["03.211"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08",
                 [("1", "navn", "Gammel AS"),
                  ("1", "registreringsdato", "2001-03-04"),
                  ("3", "navn", "Fersk AS"),
                  ("3", "registreringsdato", "2026-01-05")],
                 ["03.211", "03.300"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")  # ingen felt
    assert set(endringer["change_type"].to_list()) == {diff.UTVALGSUTVIDELSE}


def test_ny_entitet_uten_utvidelse_er_fortsatt_ny(tmp_path, monkeypatch):
    """Motprøven. Står utvalget stille, er en ny entitet en hendelse —
    fiksen får ikke bli «alt nytt er støy»."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "Gammel AS")], ["03.211"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08",
                 [("1", "navn", "Gammel AS"), ("2", "navn", "Nykommer AS")],
                 ["03.211"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")
    assert dict(endringer.group_by("change_type").len().iter_rows()) == {"ny": 1}
    assert diff.bevegelse(endringer).height == 1


def test_endring_paa_eksisterende_entitet_merkes_aldri(tmp_path, monkeypatch):
    """Utvidelsen gjelder entiteter som kom INN. En verdi som beveget seg
    på et selskap vi allerede fulgte er bevegelse, uansett hva som skjedde
    med næringskodelista samme uke."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "kommune", "Bodø")], ["03.211"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08",
                 [("1", "kommune", "Tromsø"), ("2", "kommune", "Alta")],
                 ["03.211", "03.300"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")
    per_entitet = dict(zip(endringer["entity_id"].to_list(),
                           endringer["change_type"].to_list()))
    assert per_entitet == {"1": "endret", "2": diff.UTVALGSUTVIDELSE}


def test_ukjent_utvalg_undertrykker_ingenting(tmp_path, monkeypatch):
    """Fallbacken går motsatt vei av frekvensvaktens, og med vilje: en
    undertrykt rad er en hendelse ingen får se."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    snapshot.write([_obs("1", "navn", "Gammel AS", "2026-01-01")], "2026-01-01")
    naa = [_obs("1", "navn", "Gammel AS", "2026-01-08"),
           _obs("2", "navn", "Nykommer AS", "2026-01-08")]
    snapshot.write(naa, "2026-01-08")

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")
    assert dict(endringer.group_by("change_type").len().iter_rows()) == {"ny": 1}


def test_innsnevring_og_utvidelse_samtidig_er_ikke_utvidelse(tmp_path, monkeypatch):
    """17.08.2026 gikk 10.209 UT mens 03.222 og 10.203 kom inn. Da kan en
    ny entitet skyldes begge deler, og radene skal bli SETT."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "Gammel AS")], ["03.211", "10.209"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08",
                 [("1", "navn", "Gammel AS"), ("2", "navn", "Nykommer AS")],
                 ["03.211", "10.203", "03.222"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")
    assert dict(endringer.group_by("change_type").len().iter_rows()) == {"ny": 1}


def test_er_utvidet_grammatikken():
    """Definisjonen for seg, uten filer rundt."""
    smal = {"naeringskoder": ["03.211"]}
    bred = {"naeringskoder": ["03.211", "03.300"]}

    assert utvalg.er_utvidet(smal, bred)
    assert not utvalg.er_utvidet(bred, smal)          # innsnevring
    assert not utvalg.er_utvidet(smal, smal)          # uendret
    assert not utvalg.er_utvidet(None, bred)          # vet ikke
    assert not utvalg.er_utvidet(smal, None)
    # Ny NØKKEL er et kriterium vi ikke søkte på før.
    assert utvalg.er_utvidet(smal, {**smal, "fylker": ["18"]})
    # Rekkefølge skal ikke telle som endring — ellers ny fil i git hver uke.
    assert utvalg.serialiser({"naeringskoder": ["b", "a"]}) == \
        utvalg.serialiser({"naeringskoder": ["a", "b"]})


def test_tre_tilstander_overlever_diskturen():
    """Kjent utvalg, kjent ingen filtrering, og ukjent — alle tre.

    Fram til 25.08.2026 fantes bare to: `{}` serialiserte til tom streng
    og kunne ikke skilles fra «kilden sa ingenting». For lusetall var det
    direkte galt — endepunktet tar ingen utvalgsparametre, så «alt» er
    kunnskap og ikke fravær av den.
    """
    kjent = {"naeringskoder": ["03.211"]}

    assert utvalg.serialiser(kjent) == '{"naeringskoder":["03.211"]}'
    assert utvalg.serialiser({}) == "{}"
    assert utvalg.serialiser(None) == ""

    assert utvalg.les('{"naeringskoder":["03.211"]}') == kjent
    assert utvalg.les("{}") == {}
    assert utvalg.les("") is None

    # Og de tre skal kunne SKILLES av en leser, ikke bare lagres ulikt.
    assert not utvalg.er_ukjent(utvalg.les("{}"))
    assert utvalg.henter_alt(utvalg.les("{}"))

    assert utvalg.er_ukjent(utvalg.les(""))
    assert not utvalg.henter_alt(utvalg.les(""))

    assert not utvalg.er_ukjent(kjent)
    assert not utvalg.henter_alt(kjent)


def test_ingen_filtrering_er_ikke_ukjent_i_utvidelsesregelen():
    """De to ytterpunktene, som den generelle regelen ikke dekker."""
    filter_ = {"naeringskoder": ["03.211"]}

    # Bredere enn alt finnes ikke.
    assert not utvalg.er_utvidet({}, filter_)
    assert not utvalg.er_utvidet({}, {})

    # Fra et filter til alt er den størst mulige utvidelsen.
    assert utvalg.er_utvidet(filter_, {})

    # Ukjent smitter fortsatt: ingen kan påstå noe da.
    assert not utvalg.er_utvidet(None, {})
    assert not utvalg.er_utvidet({}, None)


def test_kilde_som_ikke_sier_noe_paastaar_ikke_at_den_henter_alt():
    """Standarden på Source er None, ikke {}.

    Sto den som {}, ville enhver kilde som aldri har tenkt på spørsmålet
    automatisk påstått at den ikke filtrerer — en påstand ingen har gått
    god for.
    """
    from core.contract import Source

    class Taus(Source):
        name = "taus"
        entity_type = "selskap"

        def fetch(self, kjoredato):
            return {}

        def parse(self, raw, observed_at):
            return []

    assert Taus().utvalg is None
    assert utvalg.serialiser(Taus().utvalg) == ""
    assert utvalg.er_ukjent(utvalg.les(utvalg.serialiser(Taus().utvalg)))


def test_lusetall_deklarerer_ingen_filtrering(monkeypatch):
    """2b: endepunktet tar ingen utvalgsparametre, og det skal STÅ."""
    from sources.lusetall import Lusetall

    kilde = Lusetall()
    assert kilde.utvalg is None, "ingenting påstås før noe er hentet"

    monkeypatch.setattr(kilde, "_klient", lambda: _FalskKlient())
    kilde.hent_uke(2026, 30)

    assert kilde.utvalg == {}
    assert utvalg.serialiser(kilde.utvalg) == "{}"
    assert utvalg.henter_alt(utvalg.les(utvalg.serialiser(kilde.utvalg)))


class _FalskKlient:
    def get(self, url, **kw):
        import httpx
        return httpx.Response(200, request=httpx.Request("GET", url),
                              json={"year": 2026, "week": 30, "localities": []})

    def close(self):
        pass


def test_skalar_i_utvalget_avvises():
    """`sidestorrelse` endrer ikke HVILKE entiteter vi får, og et felt som
    ikke endrer utvalget skal ikke kunne utløse en utvalgsutvidelse."""
    with pytest.raises(ValueError, match="ikke en liste"):
        utvalg.serialiser({"sidestorrelse": 100})


def test_utvalgsutvidelse_utloser_ingen_signalregel():
    """Kravet, sagt rett ut. `endringstype` i signals.yml er ny/endret/
    borte — en fjerde verdi kan ikke matche noen av dem."""
    rad = _signalrad("navn", None, "Nykommer AS",
                     change_type=diff.UTVALGSUTVIDELSE,
                     source="enhetsregisteret", entity_type="selskap")
    reg = _signalrad("registreringsdato", None, "2026-01-05",
                     change_type=diff.UTVALGSUTVIDELSE,
                     source="enhetsregisteret", entity_type="selskap")

    scoret = signals.score(pl.DataFrame([rad, reg]))
    assert scoret.height == 2, "radene beholdes"
    assert signals.treff(scoret).height == 0, "men scorer ikke"


def test_nytt_selskap_krever_registrering_etter_forrige_snapshot():
    """Regelen fyrte 908 ganger 24.08 og hadde rett null ganger.

    Alle 908 var registrert FØR forrige snapshot — nyeste 04.08, eldste
    1995-02-19. «Ny for oss» er ikke «ny i verden».
    """
    def selskap(orgnr, registrert):
        return [
            _signalrad("navn", None, f"Selskap {orgnr}", entity_id=orgnr,
                       change_type="ny", source="enhetsregisteret",
                       entity_type="selskap",
                       forrige_observed_at="2026-01-01"),
            _signalrad("registreringsdato", None, registrert, entity_id=orgnr,
                       change_type="ny", source="enhetsregisteret",
                       entity_type="selskap",
                       forrige_observed_at="2026-01-01"),
        ]

    scoret = signals.score(pl.DataFrame(
        selskap("gammel", "1995-02-19")     # fantes lenge, ny for OSS
        + selskap("fersk", "2026-01-05")    # registrert etter forrige snapshot
    ))
    traff = signals.treff(scoret)
    assert [r["entity_id"] for r in traff.iter_rows(named=True)] == ["fersk"]
    assert traff["signal"].to_list() == ["Nytt selskap i bransjen"]


def test_nytt_selskap_uten_baseline_scorer_ikke():
    """Rader skrevet før 24.08.2026 mangler `forrige_observed_at`. Å anta
    «da er den vel ny» ville gjenskapt feilen regelen finnes for."""
    rader = [
        _signalrad("navn", None, "Ukjent AS", change_type="ny",
                   source="enhetsregisteret", entity_type="selskap",
                   forrige_observed_at=None),
        _signalrad("registreringsdato", None, "2026-01-05", change_type="ny",
                   source="enhetsregisteret", entity_type="selskap",
                   forrige_observed_at=None),
    ]
    assert signals.treff(signals.score(pl.DataFrame(rader))).height == 0


def test_forrige_observed_at_stemples_paa_hver_endring(tmp_path, monkeypatch):
    """Uten den kan ingen lese hvor langt en changelog-rad spenner."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "kommune", "Bodø")], ["03.211"])
    naa = _skriv(monkeypatch, tmp_path, "2026-01-08",
                 [("1", "kommune", "Tromsø")], ["03.211"])

    endringer = diff.compare(snapshot.to_frame(naa), "2026-01-08")
    assert endringer["forrige_observed_at"].to_list() == ["2026-01-01"]


def test_historiske_rader_merkes_ved_lesing(tmp_path, monkeypatch):
    """Punkt 4: changeloggen fra 24.08 kan ikke skrives om, men den kan
    leses riktig. Testen er den samme som signalregelen bruker."""
    _skriv(monkeypatch, tmp_path, "2026-01-01",
           [("1", "navn", "Gammel AS")], ["03.211"])
    _skriv(monkeypatch, tmp_path, "2026-01-08",
           [("1", "navn", "Gammel AS"), ("2", "navn", "Nykommer AS")],
           ["03.211"])

    # Slik en rad så ut FØR fiksen: ingen forrige_observed_at, ingen
    # utvalgskolonne å slå opp i.
    gammel_logg = pl.DataFrame([
        {"entity_id": "2", "entity_type": "selskap", "entity_name": "Nykommer AS",
         "field": "navn", "old_value": None, "new_value": "Nykommer AS",
         "change_type": "ny", "source": "enhetsregisteret",
         "observed_at": "2026-01-08"},
        {"entity_id": "2", "entity_type": "selskap", "entity_name": "Nykommer AS",
         "field": "registreringsdato", "old_value": None,
         "new_value": "1998-04-01",          # fantes lenge før vi så etter
         "change_type": "ny", "source": "enhetsregisteret",
         "observed_at": "2026-01-08"},
        {"entity_id": "3", "entity_type": "selskap", "entity_name": "Fersk AS",
         "field": "navn", "old_value": None, "new_value": "Fersk AS",
         "change_type": "ny", "source": "enhetsregisteret",
         "observed_at": "2026-01-08"},
        {"entity_id": "3", "entity_type": "selskap", "entity_name": "Fersk AS",
         "field": "registreringsdato", "old_value": None,
         "new_value": "2026-01-05",          # registrert etter forrige snapshot
         "change_type": "ny", "source": "enhetsregisteret",
         "observed_at": "2026-01-08"},
    ])

    # Baselinen finnes ikke i raden, men snapshotene ligger der.
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    (tmp_path / "raw" / "enhetsregisteret").mkdir(parents=True)
    for dato in ["2026-01-01", "2026-01-08"]:
        for fil in (tmp_path / "raw" / "falsk").glob(f"{dato}.parquet"):
            pl.read_parquet(fil).with_columns(
                pl.lit("enhetsregisteret").alias("source")
            ).write_parquet(tmp_path / "raw" / "enhetsregisteret" / fil.name)

    merket = changelog.merk_utvalgsutvidelse(gammel_logg)

    assert merket.height == gammel_logg.height, "ingen rad forsvinner"
    per_entitet = {
        e: t for e, f, t in
        merket.select(["entity_id", "field", "change_type"]).iter_rows()
        if f == "navn"
    }
    assert per_entitet == {"2": diff.UTVALGSUTVIDELSE, "3": "ny"}


def test_merking_rorer_ikke_kilder_uten_startdatofelt():
    """Lusetall har ingen registreringsdato. Uten et felt å etterprøve
    mot skal raden stå som «ny» — usikkerhet skal se ut som usikkerhet."""
    logg = pl.DataFrame([
        {"entity_id": "10029", "entity_type": "lokalitet", "entity_name": "Ø",
         "field": "voksne_hunnlus", "old_value": None, "new_value": "0.2",
         "change_type": "ny", "source": "lusetall",
         "observed_at": "2026-01-08", "forrige_observed_at": "2026-01-01"},
    ])
    assert changelog.merk_utvalgsutvidelse(logg)["change_type"].to_list() == ["ny"]


# ============================================== innholdsvakten (F10)
#
# Feltvakten teller RADER. har_rensefisk leverte 1777 rader hver uke fra
# 2023-04-24 og var False i hver eneste én — 171 uker uten et pip.


def _obs_felt(dato, felt, verdier, kilde="falsk"):
    """Én observasjon per verdi, alle på samme felt."""
    return [
        Observation(str(i), "lokalitet", f"L{i}", felt, str(v), kilde, dato)
        for i, v in enumerate(verdier)
    ]


def _ramme(dato, felt, verdier, kilde="falsk"):
    return snapshot.to_frame(_obs_felt(dato, felt, verdier, kilde))


def test_maal_ser_innhold_ikke_bare_rader():
    """Målet er minoriteten — rader som ikke har den vanligste verdien."""
    dodt = feltnormal.mål(pl.Series("value", ["False"] * 1777))
    levende = feltnormal.mål(pl.Series("value", ["True"] * 1360 + ["False"] * 417))

    assert dodt["rader"] == 1777 and dodt["minoritet"] == 0
    assert levende["rader"] == 1777 and levende["minoritet"] == 417
    # Radetellingen ser to like fulle kolonner. Det var hele feilen.
    assert dodt["rader"] == levende["rader"]


def test_boolsk_felt_som_fryser_til_true_fanges_ogsaa():
    """Derfor minoritet og ikke «antall True».

    har_laksefisk er True for 1360 av 1777. Fryser feltet til bare True,
    STIGER antall True — en vakt som teller sanne verdier ser vekst i det
    øyeblikket feltet slutter å skille noe fra noe.
    """
    for _ in range(1):
        levende = feltnormal.mål(pl.Series("value", ["True"] * 1360 + ["False"] * 417))
        frosset = feltnormal.mål(pl.Series("value", ["True"] * 1777))

    assert frosset["sanne"] > levende["sanne"], "antall True STEG"
    assert frosset["minoritet"] == 0 < levende["minoritet"], "minoriteten falt"


def test_maal_skiller_typene():
    b = feltnormal.mål(pl.Series("value", ["True", "False", "True"]))
    n = feltnormal.mål(pl.Series("value", ["0.0", "0.2", "1.5", "0.0"]))
    k = feltnormal.mål(pl.Series("value", ["TN", "TN", "STK"]))

    assert b["type"] == "boolsk" and b["sanne"] == 2
    assert n["type"] == "numerisk" and n["ikke_null"] == 2 and n["median"] == 0.1
    assert k["type"] == "kategorisk"


def test_bygg_finner_dodt_felt_og_normalt_strekk():
    """Speiler har_rensefisk: levende, så tomt i det uendelige."""
    historikk = (
        [(f"2026-01-{d:02d}", _ramme(f"2026-01-{d:02d}", "flagg",
                                     ["True"] * 5 + ["False"] * 95))
         for d in range(1, 10)]
        + [(f"2026-02-{d:02d}", _ramme(f"2026-02-{d:02d}", "flagg", ["False"] * 100))
           for d in range(1, 21)]
    )
    n = feltnormal.bygg(historikk)["flagg"]

    assert n["gulv"] == 0, "feltet HAR vært tomt, så gulvet er null"
    assert n["dodt_naa"] == 20, "det pågående strekket telles"
    assert n["normalt_nullstrekk"] == 0, (
        "det pågående strekket skal IKKE bli normalen — det er nettopp "
        "det som skal etterforskes")


def test_normalen_skrives_append_only(tmp_path, monkeypatch):
    """En fil per gang normalen etableres. Aldri omskrevet.

    Grunnen står i core/feltnormal.py: en referanse som skrives om kan
    ikke svare på «hva var normalen i uke X», og det var en referanse som
    oppdaterte seg selv som festet dødsleiet til har_rensefisk.
    """
    monkeypatch.setattr(feltnormal, "FELTNORMAL_DIR", tmp_path / "feltnormal")

    a = feltnormal.skriv({"falsk": {"flagg": {"gulv": 5}}}, "2026-08-25", "første")
    b = feltnormal.skriv({"falsk": {"flagg": {"gulv": 9}}}, "2026-08-25", "andre")

    assert a.name == "2026-08-25.json"
    assert b.name == "2026-08-25.2.json", "kollisjon gir løpenummer"
    assert json.loads(a.read_text())["kilder"]["falsk"]["flagg"]["gulv"] == 5, \
        "den første fila er urørt"
    assert feltnormal.les()["kilder"]["falsk"]["flagg"]["gulv"] == 9, "nyeste gjelder"


def _vakt(tmp_path, monkeypatch, normal, tilstand=None):
    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    monkeypatch.setattr(feltnormal, "FELTNORMAL_DIR", tmp_path / "feltnormal")
    if normal is not None:
        feltnormal.skriv(normal, "2026-01-01", "test")
    health.skriv(tilstand or {})


def test_tomt_felt_varsler_selv_naar_radene_kommer(tmp_path, monkeypatch):
    """Selve F10. Fullt levert, helt tomt."""
    # gulv 0: feltet HAR vært tomt før, så gulvprøven kan ikke fyre.
    # Det er strekket alene som skal fange dette — som med har_rensefisk.
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 0, "median": 40, "uker": 500,
                               "normalt_nullstrekk": 3, "dodt_naa": 0}}},
          {"falsk": {"innhold_nullstrekk": {"flagg": 12}}})

    naa = _ramme("2026-01-08", "flagg", ["False"] * 1777)
    _, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)

    assert len(tilsyn) == 1, tilsyn
    assert "tomt 13 kjøringer på rad" in tilsyn[0]
    assert "1777 rader leveres fortsatt" in tilsyn[0]


def test_en_enkelt_tom_uke_varsler_ikke(tmp_path, monkeypatch):
    """Null er en HELT normal uke for et lite felt. har_ila har 22
    nulluker i historikken, har_pd 33 — en vakt som fyrte på hver av dem
    ville vært støy, og støy får folk til å slutte å lese alarmer."""
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 0, "median": 8, "uker": 500,
                               "normalt_nullstrekk": 22, "dodt_naa": 0}}})

    naa = _ramme("2026-01-08", "flagg", ["False"] * 1777)
    _, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)
    assert tilsyn == []


def test_innhold_under_gulvet_varsler_straks(tmp_path, monkeypatch):
    """Den andre prøven. Gulvet er et LAVVANNSMERKE — det laveste feltet
    har vært på 574 uker. Under det er per definisjon uten sidestykke.

    Dette er prøven som fanget har_medikamentell_behandling i replayen:
    gulvet var 1, og uka det falt til 0 fyrte den samme uke.
    """
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 1, "median": 24, "uker": 574,
                               "normalt_nullstrekk": 0, "dodt_naa": 0}}})

    naa = _ramme("2026-01-08", "flagg", ["False"] * 1745)
    _, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)

    assert len(tilsyn) == 1, tilsyn
    assert "under gulvet 1" in tilsyn[0] and "574 uker" in tilsyn[0]


def test_friskt_felt_varsler_ikke(tmp_path, monkeypatch):
    """Fiksen får ikke bli «alt varsler»."""
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 300, "median": 400, "uker": 574,
                               "normalt_nullstrekk": 0, "dodt_naa": 0}}})

    naa = _ramme("2026-01-08", "flagg", ["True"] * 380 + ["False"] * 1397)
    _, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)
    assert tilsyn == []


def test_uten_normal_varsler_ingenting(tmp_path, monkeypatch):
    """Ingen etablert normal = ingen påstand. En alarm på et grunnlag vi
    ikke har er støy."""
    _vakt(tmp_path, monkeypatch, None)

    naa = _ramme("2026-01-08", "flagg", ["False"] * 1777)
    tilstand, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)

    assert tilsyn == []
    assert tilstand["falsk"]["innhold_nullstrekk"] == {"flagg": 1}, \
        "strekket telles likevel, så tallet er klart den dagen normalen bygges"


def test_strekket_arves_fra_normalens_dodt_naa(tmp_path, monkeypatch):
    """Et felt som har vært tomt i 171 uker skal ikke begynne på null.

    Uten arven ville vakten trengt 13 NYE uker på å si fra om noe som har
    vart i tre år.
    """
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 0, "median": 12, "uker": 761,
                               "normalt_nullstrekk": 3, "dodt_naa": 171}}})

    naa = _ramme("2026-01-08", "flagg", ["False"] * 1777)
    tilstand, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)

    assert tilstand["falsk"]["innhold_nullstrekk"]["flagg"] == 172
    assert len(tilsyn) == 1 and "tomt 172 kjøringer" in tilsyn[0]


def test_innhold_som_kommer_tilbake_nullstiller_strekket(tmp_path, monkeypatch):
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 0, "median": 12, "uker": 761,
                               "normalt_nullstrekk": 3, "dodt_naa": 0}}},
          {"falsk": {"innhold_nullstrekk": {"flagg": 40}}})

    naa = _ramme("2026-01-08", "flagg", ["True"] * 6 + ["False"] * 1771)
    tilstand, tilsyn = health.oppdater(
        [runner.Result("falsk", True, naa.height)], "2026-01-08", naa)

    assert tilstand["falsk"]["innhold_nullstrekk"] == {}
    assert tilsyn == []


def test_nede_kilde_forlenger_ikke_strekket(tmp_path, monkeypatch):
    """Et felt som ikke ble hentet har ikke vært tomt — det har ikke
    vært spurt."""
    _vakt(tmp_path, monkeypatch,
          {"falsk": {"flagg": {"gulv": 0, "median": 12, "uker": 761,
                               "normalt_nullstrekk": 3, "dodt_naa": 0}}},
          {"falsk": {"sist_ok": "2026-01-01",
                     "innhold_nullstrekk": {"flagg": 12}}})

    tilstand, tilsyn = health.oppdater(
        [runner.Result("falsk", False, 0, error="nede")], "2026-01-08", None)

    assert tilstand["falsk"]["innhold_nullstrekk"] == {"flagg": 12}, "står stille"
    assert not any("flagg" in t for t in tilsyn)


def test_godta_felt_kvitterer_ogsaa_innholdsalarmen(tmp_path, monkeypatch):
    """«Feltet er borte» og «feltet er tomt» er samme sak fra to sider.
    En kvittering som bare tok den ene ville latt jobben stå rød på den
    andre uten at noe mer kunne gjøres herfra."""
    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    health.skriv({"falsk": {"felt_sist": {"flagg": 100},
                            "felt_referanse": {"flagg": 100},
                            "innhold_nullstrekk": {"flagg": 40}}})

    ok, melding = health.godta_felt("falsk")

    assert ok and "nullstilte innholdsstrekket for flagg" in melding
    assert health.les()["falsk"]["innhold_nullstrekk"] == {}
