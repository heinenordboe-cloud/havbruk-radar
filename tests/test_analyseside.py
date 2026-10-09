"""Analysesiden /analyse/unntaksvekst/, bygget av et lite arkiv.

Arkivet er laget her, i den formen kroppene er MÅLT å ha (se
tests/test_unntaksanalyse.py). Suiten leser aldri datarepoet.
"""

import datetime as dt
import gzip
import json
import re
from types import SimpleNamespace

import pytest

import nettsted
import unntaksanalyse as u
from core import paths
from core import snapshot as snap
from core.contract import Observation
from tests.test_unntaksanalyse import PARAGRAF_12, _dokument


def _legg(arkiv, mappe, navn, data: bytes):
    (arkiv / mappe).mkdir(parents=True, exist_ok=True)
    with gzip.open(arkiv / mappe / navn, "wb") as f:
        f.write(data)


def _rapp(aar, uke, lus, med=()):
    levert = dt.date.fromisocalendar(aar, uke, 5).isoformat()
    return {"år": aar, "uke": uke, "rapporteringstidspunkt": f"{levert}T08:00:00Z",
            "organisasjonsnummer": "", "organisasjonsnavn": "",
            "lusetelling": {"voksneHunnlus": lus},
            "medikamentelleBehandlinger": list(med),
            "ikkeMedikamentelleBehandlinger": [], "kombinasjonsbehandlinger": []}


RADER = [
    {"lokalitet": "Testholmen", "po": "3", "resultat": "Godkjent",
     "saksnumre": ["2025/205518"], "kobling": "entydig",
     "lokalitet_nr": "10001", "kandidater": ["10001"],
     "soker": "Testlaks", "soker_orgnr": "912345678",
     "organisasjonsform": "AS", "soker_registernavn": "TESTLAKS AS"},
    {"lokalitet": "Tomholmen", "po": "3", "resultat": "Avslag",
     "saksnumre": ["2025/209376"], "kobling": "entydig",
     "lokalitet_nr": "10002", "kandidater": ["10002"]},
    {"lokalitet": "Kanskjeholmen", "po": "3", "resultat": "Godkjent",
     "saksnumre": ["2025/209407"], "kobling": "usikker",
     "lokalitet_nr": "10003", "kandidater": ["10003"]},
    {"lokalitet": "Ingenholmen", "po": "4", "resultat": "Avslag",
     "saksnumre": ["2025/209429"], "kobling": "flertydig",
     "lokalitet_nr": "", "kandidater": ["10004", "10005"]},
]


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    arkiv = tmp_path / "arkiv"
    monkeypatch.setattr(paths, "ARKIV_DIR", arkiv)
    monkeypatch.setattr(snap, "RAW_DIR", tmp_path / "raw")

    _legg(arkiv, "unntaksvekst", "2026-10-09.json.gz", json.dumps({
        "url": "https://mattilsynet.no/liste", "sha256": "ab" * 32,
        "bytes": 10, "headere": {}, "rader": RADER}).encode())
    sf = _dokument({"12": PARAGRAF_12, "12a": [(0, "", "Søknad innen 1. september.")]},
                   fotnote="Endret ved forskrifter 28 sep 2023 nr. 1520.")
    _legg(arkiv, "lovdata-produksjonsomradeforskriften", "2026-10-09.bin.gz", sf)
    _legg(arkiv, "lovdata-produksjonsomradeforskriften-endring-2023",
          "2026-10-09.bin.gz", _dokument({"12": PARAGRAF_12}))
    _legg(arkiv, "lovdata-lakselusforskriften", "2026-10-09.bin.gz",
          _dokument({"8": [(0, "", "færre enn 0,5")]}))
    _legg(arkiv, "trafikklysvedtak", "2026-12-31.bin.gz", b"<p>kap. 4</p>")
    for dato, kap in (("2026-09-28", 1068.0), ("2026-10-05", 1079.0)):
        _legg(arkiv, "eierskap", f"{dato}.json.gz", json.dumps({
            "personer_fjernet": 0, "enheter": [],
            "tillatelser": [{"licenseNr": "N-T-0001", "openLegalEntityNr": "912345678",
                             "capacity": {"current": kap, "unit": "TN"},
                             "connections": [{"active": True, "siteNr": "10001"}]}]
        }).encode())
    for nr, rapporter in (("10001", [_rapp(2024, 20, 0.12), _rapp(2025, 41, 0.05)]),
                          ("10002", [_rapp(2024, 20, 0.02)]),
                          ("10003", [_rapp(2024, 20, 0.30)])):
        _legg(arkiv, f"mattilsynet-lakselus/{nr}", "2026-10-09.json.gz",
              json.dumps({"rapporter": rapporter}).encode())

    def obs(kilde, felt, verdi, dato, eid):
        return Observation(entity_id=eid, entity_type="lokalitet",
                           entity_name="X", field=felt, value=verdi,
                           source=kilde, observed_at=dato)
    for aar, uke in ((2024, 20), (2025, 41)):
        dato = dt.date.fromisocalendar(aar, uke, 1).isoformat()
        snap.write([obs("lusetall", "brakklagt", "False", dato, e)
                    for e in ("10001", "10002", "10003")], dato)
        snap.write([obs("sjotemperatur", "lusegrense", "0.5", dato, e)
                    for e in ("10001", "10002", "10003")], dato)
    return arkiv


def _felles(**k):
    grunn = dict(
        akva={"10001": {"navn": "TESTHOLMEN"}, "10002": {"navn": "TOMHOLMEN"},
              "10003": {"navn": "KANSKJEHOLMEN I"}},
        tillatelser_per_eier={"912345678": ["N-T-0001"]},
        eierskap={"N-T-0001": {"eier_type": "LimitedLiabilityCompany"}},
        enhet={}, former={}, vilkaar=nettsted.kildevilkaar(),
        akva_dato="2026-10-05", akva_hentet="", kontakt="",
        unntak=nettsted.unntak_per_lokalitet())
    grunn.update(k)
    return SimpleNamespace(**grunn)


def test_siden_bygges_av_arkivet_og_bare_sikre_rader_telles(arkiv, tmp_path):
    a = nettsted.bygg_unntaksvekst(_felles())
    assert a["n_lok"] == 2 and (a["godkjent"], a["avslag"]) == (1, 1)
    assert [r["lok"]["nr"] for r in a["rader"]] == ["10001", "10002"]
    assert [r["kandidat"]["nr"] for r in a["usikre"]] == ["10003"]
    assert len(a["uloste"]) == 1
    assert a["rader"][0]["kapasitet"] == "+11 t på 1 tillatelse, alle nøyaktig 1 %"
    assert a["rader"][0]["kv"]["b1"] == "1 av 1"


def test_soekeren_staar_bare_med_orgnr_og_registerets_navn(arkiv):
    a = nettsted.bygg_unntaksvekst(_felles())
    test, tom = a["rader"]
    assert test["soker"]["navn"] == "Testlaks AS"
    assert test["soker"]["url"] == "/selskap/912345678/"
    assert tom["soker"]["navn"] == ""


def test_siden_skrives_med_nedlasting_og_uten_dom(arkiv, tmp_path):
    rot = tmp_path / "ut"
    filer = nettsted.skriv_unntaksvekst(rot, _felles())
    assert {f.name for f in filer} == {"index.html",
                                       "unntaksvekst-2025-2026.xlsx",
                                       "unntaksvekst-2025-2026.zip"}
    html = (rot / "analyse" / "unntaksvekst" / "index.html").read_text()
    celler = " ".join(re.findall(r"<td\b[^>]*>(.*?)</td>", html, re.S))
    assert "Kanskjeholmen" not in re.search(
        r'<table id="unntak-lokaliteter".*?</table>', html, re.S).group(0), \
        "en usikker kobling står ikke i hovedtabellen"
    # INGEN CELLE FELLER EN DOM. Forbeholdet sier ordene, cellene gjør ikke.
    for ord_ in ("oppfylt", "brutt", "brudd", "ja", "nei"):
        assert not re.search(rf"\b{ord_}\b", celler, re.I), ord_
    assert nettsted.MATTILSYNET_API in html
    assert "Kilde: Mattilsynet" in html
    assert "Periodegrensa er BarentsWatchs vurdering" in html


def test_ingen_hash_paa_siden_har_ni_siffer_paa_rad(arkiv, tmp_path):
    """En hel sha256 har ni siffer på rad i 11,7 % av tilfellene, og
    porten leser det som et organisasjonsnummer."""
    rot = tmp_path / "ut"
    nettsted.skriv_unntaksvekst(rot, _felles())
    html = (rot / "analyse" / "unntaksvekst" / "index.html").read_text()
    for kode in re.findall(r"<code>([0-9a-f ]{71})</code>", html):
        assert all(len(g) == 8 for g in kode.split())


def test_uten_arkivert_liste_bygges_ingen_side(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ARKIV_DIR", tmp_path / "tomt")
    assert nettsted.unntak_per_lokalitet() == {}
    assert nettsted.bygg_unntaksvekst(_felles(unntak={})) is None
    assert nettsted.skriv_unntaksvekst(tmp_path / "ut", _felles(unntak={})) == []


def test_lokaliteten_faar_linja_bare_med_sikker_kobling(arkiv):
    per = nettsted.unntak_per_lokalitet()
    assert set(per) == {"10001", "10002"}, "10003 er usikker"
    linje = nettsted.unntak_for_lokalitet(per["10001"])
    assert linje == {"resultat": "godkjent", "soknader": 1,
                     "url": "/analyse/unntaksvekst/"}
    assert nettsted.unntak_for_lokalitet([]) is None


def test_sitemap_har_analysesiden_bare_naar_den_bygges():
    felles = SimpleNamespace(
        akva={}, po_navn={}, tillatelser_per_eier={}, unntak={"1": [{}]})
    assert "/analyse/unntaksvekst/" in nettsted._urler(felles)
    felles.unntak = {}
    assert "/analyse/unntaksvekst/" not in nettsted._urler(felles)


def test_forsiden_lenker_til_analysen_med_tall_fra_lista():
    felles = SimpleNamespace(unntak={
        "1": [{"resultat": "Godkjent"}, {"resultat": "Godkjent"}],
        "2": [{"resultat": "Avslag"}]})
    assert nettsted._forside_unntak(felles) == {
        "url": "/analyse/unntaksvekst/", "lokaliteter": 2,
        "godkjent": 1, "avslag": 1}
    assert nettsted._forside_unntak(SimpleNamespace(unntak={})) is None


def test_analysesidens_kilder_er_belagt_og_vist():
    assert set(nettsted.ANALYSE_KILDER) <= nettsted.viste_kilder()
    assert set(nettsted.ANALYSE_KILDER).isdisjoint(
        nettsted.ubelagte(nettsted.kildevilkaar()))
    assert nettsted.ANSVARLIG_FOR[nettsted.MATTILSYNET_API] == ("Mattilsynet",)
