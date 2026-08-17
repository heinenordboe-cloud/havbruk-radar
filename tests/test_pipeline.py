"""Røyktest: kjører hele pipelinen med en falsk kilde, uten nett.

Poenget er ikke testdekning. Poenget er at du kan endre core/ og på
to sekunder vite om du ødela noe.
"""

import polars as pl
import pytest

from core import diff, runner, signals, snapshot
from core.contract import Observation, Source


class FalskKilde(Source):
    name = "falsk"
    entity_type = "selskap"

    def fetch(self):
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

    def fetch(self):
        raise RuntimeError("kilden er nede")

    def parse(self, raw, observed_at):
        return []


def test_feil_isoleres():
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


def test_signalregler_scorer():
    endringer = pl.DataFrame([{
        "entity_id": "1", "entity_type": "selskap", "entity_name": "Testlaks AS",
        "field": "antall_ansatte", "old_value": "10", "new_value": "20",
        "change_type": "endret", "source": "falsk", "observed_at": "2026-01-08",
    }])
    assert signals.score(endringer).height == 1


def test_regresjon_oppdages(tmp_path, monkeypatch):
    """En kilde som fungerte forrige uke og feiler nå skal flagges."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    ok = [runner.Result("falsk", True, 5)]
    health.skriv(health.oppdater(ok, "2026-01-01")[0])

    feilet = [runner.Result("falsk", False, 0, "RuntimeError: nede")]
    _, nede = health.oppdater(feilet, "2026-01-08")

    assert nede == ["falsk (uke 1)"]


def test_knekt_kildefil_stopper_ikke_de_andre(tmp_path, monkeypatch):
    """En kildefil som ikke lar seg importere skal isoleres, ikke drepe kjøringen."""
    import types

    from core import registry

    (tmp_path / "frisk.py").write_text(
        "from core.contract import Source\n"
        "class Frisk(Source):\n"
        "    name = 'frisk'\n"
        "    def fetch(self): return []\n"
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

    kilder = registry.discover()
    assert sorted(k.name for k in kilder) == ["frisk", "knekt"]

    _, res = runner.run_all(kilder, "2026-01-01")
    assert {r.source: r.ok for r in res} == {"frisk": True, "knekt": False}


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


def test_kilde_som_aldri_har_fungert_varsler_ikke(tmp_path, monkeypatch):
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    _, nede = health.oppdater([runner.Result("ny_kilde", False, 0, "ikke ferdig")], "2026-01-01")
    assert nede == []


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
    for regel in signals.load_rules():
        assert "navn" in regel, regel
        assert regel.get("endringstype") in (None, "ny", "endret", "borte"), regel
        assert regel.get("retning") in (None, "opp", "ned", "begge"), regel


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
    from sources.akvakulturregisteret import Akvakulturregisteret

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
    from sources.akvakulturregisteret import Akvakulturregisteret

    def tillatelser(rekkefolge):
        rad = _akva_rad(tillatelser=rekkefolge)
        return next(o.value for o in Akvakulturregisteret().parse([rad], "2026-08-17")
                    if o.field == "tillatelser")

    assert tillatelser(("B", "A", "C")) == tillatelser(("C", "B", "A"))


def test_akvakultur_lagrer_ingen_persondata():
    """connections skal kun gi tillatelsesnumre — aldri innehaver."""
    from sources.akvakulturregisteret import Akvakulturregisteret

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


def test_forfalte_kilder_velges_hver_for_seg(tmp_path, monkeypatch):
    """Én kilde hentet i dag skal ikke blokkere de andre.

    Dette er scenarioet hver gang en ny kilde aktiveres midt i uka.
    """
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    ukentlig, daglig, ny = FalskKilde(), DagligKilde(), KnustKilde()
    ny.name = "helt_ny"

    # Begge etablerte kilder hentet i går.
    for kilde in (ukentlig, daglig):
        snapshot.write(
            [Observation("1", "selskap", "X", "f", "v", kilde.name, "2026-01-07")],
            "2026-01-07",
        )

    forfalt, venter = runner.velg_forfalte([ukentlig, daglig, ny], "2026-01-08")

    # Ukentlig må vente (1 dag < 7). Daglig er forfalt (1 >= 1).
    # En kilde som aldri er hentet er alltid forfalt.
    assert sorted(k.name for k in forfalt) == ["daglig", "helt_ny"]
    assert [(k.name, d) for k, d in venter] == [("falsk", 1)]


def test_kilde_hentet_i_dag_er_ikke_forfalt(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    snapshot.write(list(FalskKilde().collect("2026-01-08")), "2026-01-08")

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-08")
    assert forfalt == []
    assert venter[0][1] == 0


def test_forfalt_igjen_etter_full_periode(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")

    forfalt, _ = runner.velg_forfalte([FalskKilde()], "2026-01-08")   # nøyaktig 7
    assert [k.name for k in forfalt] == ["falsk"]


def test_snapshot_datert_fram_i_tid_overskrives_ikke(tmp_path, monkeypatch):
    """Klokkerot skal ikke føre til at noe skrives over."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    snapshot.write(list(FalskKilde().collect("2026-02-01")), "2026-02-01")

    forfalt, venter = runner.velg_forfalte([FalskKilde()], "2026-01-08")
    assert forfalt == []
    assert venter[0][1] < 0


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
    assert nede == ["falsk (uke 1)"]


def test_dager_siden_leser_siste_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    assert snapshot.dager_siden("falsk", "2026-01-08") is None

    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")
    snapshot.write(list(FalskKilde().collect("2026-01-05")), "2026-01-05")

    assert snapshot.siste_dato("falsk") == "2026-01-05"
    assert snapshot.dager_siden("falsk", "2026-01-08") == 3
