"""Endepunktet følger med inn i endringsloggen — merket, ikke filtrert.

Variant A i docs/FORSLAG-endepunkt-i-endringsloggen.md, godkjent
04.10.2026. Hver rad bærer `endepunkt` og `forrige_endepunkt`. Rader der
de to er KJENTE og ulike er et `diff.endepunktbytte()`, rader der bare
den ene er kjent er `diff.endepunkt_uavklart()`. Ingen av dem fjernes
fra `diff.bevegelse()`.
"""

import polars as pl
import pytest

from core import diff, signals, snapshot
from core.contract import Observation
import run

PRIMAER = ("https://gis.fiskeridir.no/server/rest/services/"
           "Yggdrasil/Biomasse/MapServer/0")
RESERVE = ("https://gis.fiskeridir.no/server/rest/services/"
           "fiskeridirWMS_akva/MapServer/6")


@pytest.fixture
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    return tmp_path / "raw"


def _obs(dato, endepunkt, verdier):
    return [Observation(entity_id=loknr, entity_type="lokalitet",
                        entity_name=f"L{loknr}", field="siste_rapport",
                        value=v, source="biomasselag", observed_at=dato,
                        endepunkt=endepunkt)
            for loknr, v in verdier.items()]


def _skriv(dato, endepunkt, verdier):
    snapshot.write(_obs(dato, endepunkt, verdier), dato)


def _skriv_uten_kolonnen(raw, dato, verdier):
    """Et snapshot fra før 02.10.2026: kolonnen `endepunkt` finnes ikke.
    Skrevet forbi `write()`, som ellers ville lagt den til tom."""
    mappe = raw / "biomasselag"
    mappe.mkdir(parents=True, exist_ok=True)
    kolonner = [k for k in snapshot.SCHEMA
                if k not in snapshot.KJORINGSFELT and k != "endepunkt"]
    pl.DataFrame([o.as_dict() for o in _obs(dato, "", verdier)]) \
        .select(kolonner).write_parquet(mappe / f"{dato}.parquet")


def _diff(dato):
    """Som run.py: ukas snapshot mot forrige, via `compare()`."""
    naa = snapshot._les(snapshot.RAW_DIR / "biomasselag" / f"{dato}.parquet")
    return diff.compare(naa, dato)


# ------------------------------------------------------------ skjemaet

def test_kolonnene_staar_i_skjemaet():
    assert "endepunkt" in diff.CHANGE_SCHEMA
    assert "forrige_endepunkt" in diff.CHANGE_SCHEMA


# ------------------------------------------------- primær → reserve → primær

def test_primaer_reserve_primaer_merkes_begge_veier(raw):
    _skriv("2026-09-22", PRIMAER, {"10726": "2026-08-31", "1": "2026-07-31"})
    _skriv("2026-10-04", RESERVE, {"10726": "2026-07-31", "1": "2026-08-31"})

    fram = _diff("2026-10-04")
    assert fram.height == 2
    assert set(fram["forrige_endepunkt"]) == {PRIMAER}
    assert set(fram["endepunkt"]) == {RESERVE}
    assert diff.endepunktbytte(fram).height == 2
    assert diff.endepunkt_uavklart(fram).height == 0

    _skriv("2026-10-11", PRIMAER, {"10726": "2026-08-31", "1": "2026-08-31"})
    tilbake = _diff("2026-10-11")
    assert tilbake.height == 1
    assert tilbake.row(0, named=True)["forrige_endepunkt"] == RESERVE
    assert tilbake.row(0, named=True)["endepunkt"] == PRIMAER
    assert diff.endepunktbytte(tilbake).height == 1


def test_bytte_er_merket_men_ikke_filtrert(raw):
    """Antallet i «X endringer» er det samme med og uten byttet."""
    _skriv("2026-09-22", PRIMAER, {"1": "a", "2": "a", "3": "a"})
    _skriv("2026-10-04", RESERVE, {"1": "b", "2": "b", "3": "a"})

    endringer = _diff("2026-10-04")
    assert endringer.height == 2
    assert diff.bevegelse(endringer).height == 2
    assert set(endringer["change_type"]) == {"endret"}


# --------------------------------------------------------- reserve → reserve

def test_reserve_mot_reserve_er_ikke_et_bytte(raw):
    _skriv("2026-10-04", RESERVE, {"1": "a"})
    _skriv("2026-10-11", RESERVE, {"1": "b"})

    endringer = _diff("2026-10-11")
    assert endringer.height == 1
    rad = endringer.row(0, named=True)
    assert rad["endepunkt"] == rad["forrige_endepunkt"] == RESERVE
    assert diff.endepunktbytte(endringer).height == 0
    assert diff.endepunkt_uavklart(endringer).height == 0
    assert run.endepunktlinjer(endringer) == []


# ------------------------------------------------- tomt endepunkt mot ny verdi

def test_snapshot_uten_kolonnen_mot_reserve_er_uavklart(raw):
    """Formen 2026-09-22 → 2026-10-04. Det eldre snapshotet vet ikke
    hvilket endepunkt det kom fra, og `forrige_endepunkt` fylles ikke
    inn — selv om vi «vet» det var primæren (regel 2, 1b-7)."""
    _skriv_uten_kolonnen(raw, "2026-09-22", {"1": "a", "2": "a"})
    _skriv("2026-10-04", RESERVE, {"1": "b", "2": "a"})

    endringer = _diff("2026-10-04")
    assert endringer.height == 1
    rad = endringer.row(0, named=True)
    assert rad["forrige_endepunkt"] == ""
    assert rad["endepunkt"] == RESERVE
    assert diff.endepunktbytte(endringer).height == 0, \
        "tomt er «vet ikke», ikke «annerledes»"
    assert diff.endepunkt_uavklart(endringer).height == 1
    assert diff.bevegelse(endringer).height == 1


def test_tomt_endepunkt_paa_begge_sider_er_taust(raw):
    """Alle andre kilder: ingen påstand, ingen linje."""
    _skriv("2026-10-04", "", {"1": "a"})
    _skriv("2026-10-11", "", {"1": "b"})

    endringer = _diff("2026-10-11")
    assert endringer.height == 1
    assert diff.endepunktbytte(endringer).height == 0
    assert diff.endepunkt_uavklart(endringer).height == 0
    assert run.endepunktlinjer(endringer) == []


def test_kjent_mot_tomt_er_ogsaa_uavklart(raw):
    """Motsatt vei: en backfillet rad uten endepunkt etter en kjent."""
    _skriv("2026-10-04", RESERVE, {"1": "a"})
    _skriv("2026-10-11", "", {"1": "b"})

    endringer = _diff("2026-10-11")
    assert diff.endepunkt_uavklart(endringer).height == 1
    assert diff.endepunktbytte(endringer).height == 0


# ------------------------------------------------------------- gamle filer

def test_changelog_fra_foer_kolonnene_gir_ingen_merking():
    gammel = pl.DataFrame({"entity_id": ["1"], "change_type": ["endret"],
                           "source": ["biomasselag"]})
    assert diff.endepunktbytte(gammel).height == 0
    assert diff.endepunkt_uavklart(gammel).height == 0


def test_null_fra_diagonal_concat_leses_som_ukjent():
    """`les_alt()` konkatenerer gamle og nye filer diagonalt; de gamle får
    null i kolonnene, og null er «vet ikke» som tom streng."""
    ramme = pl.DataFrame({"entity_id": ["1", "2"],
                          "source": ["biomasselag"] * 2,
                          "endepunkt": [None, RESERVE],
                          "forrige_endepunkt": [None, None]},
                         schema={"entity_id": pl.Utf8, "source": pl.Utf8,
                                 "endepunkt": pl.Utf8,
                                 "forrige_endepunkt": pl.Utf8})
    assert diff.endepunktbytte(ramme).height == 0
    assert diff.endepunkt_uavklart(ramme)["entity_id"].to_list() == ["2"]


# ------------------------------------------------------------- utdata

def test_commitmeldingen_sier_det(raw):
    _skriv("2026-09-22", PRIMAER, {"1": "a", "2": "a"})
    _skriv("2026-10-04", RESERVE, {"1": "b", "2": "b"})
    endringer = _diff("2026-10-04")

    assert run.endepunktlinjer(endringer) == [
        "biomasselag: 2 endringer på 2 entiteter over endepunktbytte "
        "(Biomasse/0 → fiskeridirWMS_akva/6). Talt med, ikke filtrert."]

    melding = run.bygg_commitmelding("2026-10-04", [], endringer,
                                     signals.score(endringer))
    assert "over endepunktbytte" in melding
    assert "Snapshot 2026-10-04 — 2 endringer" in melding


def test_uavklart_linje_navngir_ukjent(raw):
    _skriv_uten_kolonnen(raw, "2026-09-22", {"1": "a"})
    _skriv("2026-10-04", RESERVE, {"1": "b"})
    assert run.endepunktlinjer(_diff("2026-10-04")) == [
        "biomasselag: 1 endringer på 1 entiteter over endepunkt ukjent på "
        "den ene siden (ukjent → fiskeridirWMS_akva/6). Talt med, ikke "
        "filtrert."]
