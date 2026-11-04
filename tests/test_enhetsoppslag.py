"""Enhetsregisterets svar for orgnumre tillatelsesregisteret nevner.

Rødt lag F4 (04.11.2026): «(i dag: Landøy Fiskeoppdrett AS)» sto om en
enhet slettet 18.05.2019. Oppslaget er det som lar siden si «slettet i
Enhetsregisteret <dato>» — og det er en vei inn i et append-only arkiv,
så personvernet prøves først.
"""

import gzip
import hashlib
import json

import httpx
import pytest

import backfill
from core import raw as raw_arkiv, snapshot
from core.contract import Observation
from sources.enhetsregisteret import OPPSLAG_KILDE, Enhetsregisteret


AKTIV = {"organisasjonsnummer": "928957489", "navn": "SALMAR OPPDRETT AS",
         "organisasjonsform": {"kode": "AS"},
         "forretningsadresse": {"adresse": ["Industriveien 51"]},
         "telefon": "72 44 79 00"}
SLETTET = {"organisasjonsnummer": "931967061", "navn": "LANDØY FISKEOPPDRETT AS",
           "organisasjonsform": {"kode": "AS"}, "slettedato": "2019-05-18",
           "respons_klasse": "SlettetEnhet"}
ENK = {"organisasjonsnummer": "985937028", "navn": "OLA NORDMANN",
       "organisasjonsform": {"kode": "ENK"},
       "forretningsadresse": {"adresse": ["Hjemmeveien 1"]}, "mobil": "999"}


def _klient(svar: dict[str, tuple[int, dict]]):
    def handler(req: httpx.Request) -> httpx.Response:
        orgnr = req.url.path.rsplit("/", 1)[-1]
        kode, kropp = svar.get(orgnr, (404, {}))
        return httpx.Response(kode, json=kropp)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_oppslaget_reduseres_til_fire_felt():
    c = _klient({"928957489": (200, AKTIV), "931967061": (200, SLETTET)})
    aktiv = Enhetsregisteret().oppslag("928957489", c)
    slettet = Enhetsregisteret().oppslag("931967061", c)
    assert aktiv == {"organisasjonsnummer": "928957489", "status": "finnes",
                     "organisasjonsform": "AS", "slettedato": ""}
    assert slettet["status"] == "slettet"
    assert slettet["slettedato"] == "2019-05-18"
    assert "navn" not in aktiv and "forretningsadresse" not in aktiv


def test_personform_gir_bare_status():
    """«Dette nummeret er et ENK» er en opplysning om et menneske."""
    d = Enhetsregisteret().oppslag("985937028", _klient({"985937028": (200, ENK)}))
    assert d == {"organisasjonsnummer": "985937028", "status": "personform"}


@pytest.mark.parametrize("kode, status", [(404, "ikke_funnet"), (410, "fjernet")])
def test_404_og_410_er_status_ikke_feil(kode, status):
    d = Enhetsregisteret().oppslag("911111111", _klient({"911111111": (kode, {})}))
    assert d == {"organisasjonsnummer": "911111111", "status": status}


def test_parse_slipper_ingen_personform_gjennom():
    kropp = {"enheter": [
        {"organisasjonsnummer": "931967061", "status": "slettet",
         "organisasjonsform": "AS", "slettedato": "2019-05-18"},
        {"organisasjonsnummer": "985937028", "status": "personform"},
        {"organisasjonsnummer": "985937029", "status": "finnes",
         "organisasjonsform": "ENK"}]}
    obs = list(Enhetsregisteret().parse_oppslag(kropp, "2026-11-04"))
    assert {o.entity_id for o in obs} == {"931967061"}
    assert {o.source for o in obs} == {OPPSLAG_KILDE}
    assert {(o.field, o.value) for o in obs} == {
        ("status", "slettet"), ("organisasjonsform", "AS"),
        ("slettedato", "2019-05-18")}


class FalskEnhetsregisteret(Enhetsregisteret):
    def __init__(self, svar):
        self.svar = svar
        self.spurt = []

    def oppslag(self, orgnr, c):
        self.spurt.append(orgnr)
        return self.svar[orgnr]


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(backfill.snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(backfill.changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(backfill.time, "sleep", lambda s: None)
    return tmp_path


def _obs(eid, felt, verdi, kilde, dato, etype="tillatelse"):
    return Observation(entity_id=eid, entity_type=etype, entity_name="",
                       field=felt, value=verdi, source=kilde, observed_at=dato)


def test_backfill_slaar_opp_bare_dem_utenfor_utvalget(isolert, monkeypatch):
    snapshot.write([_obs("T-D-0009", "tildelt_orgnr", "931967061", "eierskap", "2026-11-02"),
                    _obs("T-D-0009", "eier_orgnr", "928957489", "eierskap", "2026-11-02"),
                    _obs("T-D-0010", "tildelt_orgnr", "985937028", "eierskap", "2026-11-02")],
                   "2026-11-02")
    snapshot.write([_obs("928957489", "navn", "SALMAR OPPDRETT AS",
                         "enhetsregisteret", "2026-11-02", "selskap")], "2026-11-02")
    kilde = FalskEnhetsregisteret({
        "931967061": {"organisasjonsnummer": "931967061", "status": "slettet",
                      "organisasjonsform": "AS", "slettedato": "2019-05-18"},
        "985937028": {"organisasjonsnummer": "985937028", "status": "personform"}})
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "enhetsregisteret",
                                     "--oppslag", "--pause", "0"])

    assert backfill.main() == 0

    assert sorted(kilde.spurt) == ["931967061", "985937028"], \
        "928957489 står i utvalget, og registeret har svart for den"
    dato = snapshot.siste_dato(OPPSLAG_KILDE)
    ramme = snapshot.versjoner(OPPSLAG_KILDE, dato)[-1][1]
    assert set(ramme["entity_id"]) == {"931967061"}
    [arkivfil] = list((isolert / "arkiv" / OPPSLAG_KILDE).glob("*.json.gz"))
    data = gzip.open(arkivfil).read()
    assert set(ramme["raw_hash"]) == {hashlib.sha256(data).hexdigest()}
    kropp = json.loads(data)
    assert kropp["personform_utelatt"] == 1
    assert "985937028" not in data.decode("utf-8")
    assert kropp["grunnlag"] == {"eierskap": "2026-11-02",
                                 "enhetsregisteret": "2026-11-02"}
    assert not (isolert / "changelog").exists() or \
        not list((isolert / "changelog").glob("*.parquet"))
