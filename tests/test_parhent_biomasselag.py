"""parhent_biomasselag.py: begge endepunkter i samme kjøring, mot mock.

Ingen test går mot nettet. Tre tilstander fra oppgaven 05.10.2026 —
begge oppe, primær nede, begge nede — og to til som følger av dem:
reserven alene nede, og tørrkjøring.
"""

import gzip
import hashlib
import json
import time

import httpx
import pytest

import parhent_biomasselag as ph
from core import raw
from sources import biomasselag as bl

PRIMAER = bl.STANDARD_BASE
RESERVE = bl.RESERVE_BASE
FEIL_500 = {"error": {"code": 500, "message": "Error performing query operation",
                      "details": []}}
AUG, JUL = 1756598400000, 1753920000000      # 2025-08-31 / 2025-07-31 UTC


def _rad(loknr, rapport=AUG, har_fisk="Ja", art="Laks", objectid=None):
    return {"objectid": objectid or loknr, "loknr": loknr, "navn": f"L{loknr}",
            "status_lokalitet": "AKTIV", "siste_rapport": rapport,
            "har_fisk": har_fisk, "art": art}


class Lag:
    """Ett ArcGIS-lag. `feilsvar`: 200 OK med error-objekt på /query.
    `status`: HTTP-status på alt."""

    def __init__(self, rader, *, feilsvar=False, status=200, felter=None):
        self.rader, self.feilsvar, self.status = rader, feilsvar, status
        self.felter = felter or (bl.FELTER + bl.KJENTE_UTELATTE)

    def __call__(self, req):
        if self.status != 200:
            return httpx.Response(self.status)
        if not req.url.path.endswith("/query"):
            return httpx.Response(200, json={"fields": [{"name": f} for f in self.felter]})
        if self.feilsvar:
            return httpx.Response(200, json=FEIL_500)
        q = dict(req.url.params)
        if q.get("returnCountOnly") == "true":
            return httpx.Response(200, json={"count": len(self.rader)})
        fra, n = int(q["resultOffset"]), int(q["resultRecordCount"])
        return httpx.Response(200, json={
            "features": [{"attributes": r} for r in self.rader[fra:fra + n]]})


@pytest.fixture
def nett(monkeypatch, tmp_path):
    lag: dict = {}

    def ruter(req):
        url = str(req.url).split("?")[0]
        for base, h in lag.items():
            if url == base or url.startswith(base + "/"):
                return h(req)
        return httpx.Response(404)

    ekte = httpx.Client
    monkeypatch.setattr(ph.httpx, "Client",
                        lambda **kw: ekte(transport=httpx.MockTransport(ruter), **kw))
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(raw, "ARKIV_DIR", tmp_path / "arkiv")
    return lag


def _par(tmp_path):
    return tmp_path / "arkiv" / ph.MAPPE


def _filer(tmp_path):
    rot = _par(tmp_path)
    return sorted(str(p.relative_to(rot)) for p in rot.rglob("*") if p.is_file()) \
        if rot.exists() else []


RESERVE_FELTER = bl.FELTER + bl.KJENTE_UTELATTE_RESERVE


# --------------------------------------------------------------- begge oppe

def test_begge_oppe_arkiverer_begge_og_sammenligner(nett, tmp_path, capsys):
    nett[PRIMAER] = Lag([_rad(1), _rad(2), _rad(3, rapport=AUG), _rad(4)])
    nett[RESERVE] = Lag([_rad(1, objectid=99), _rad(2, har_fisk="Nei", art=None),
                         _rad(3, rapport=JUL), _rad(5)],
                        felter=RESERVE_FELTER)

    assert ph.kjor("2026-10-11") == 0

    assert _filer(tmp_path) == ["primaer/2026-10-11.json.gz",
                                "reserve/2026-10-11.json.gz",
                                "sammenligning/2026-10-11.json"]
    s = json.loads((_par(tmp_path) / "sammenligning" / "2026-10-11.json").read_text())

    # Hashen i sammenligningen er hashen av kroppen som ligger på disk.
    for side in ("primaer", "reserve"):
        kropp = gzip.open(_par(tmp_path) / side / "2026-10-11.json.gz").read()
        assert s["endepunkter"][side]["sha256"] == hashlib.sha256(kropp).hexdigest()
        assert s["endepunkter"][side]["svarer"] is True
    assert s["endepunkter"]["primaer"]["url"] == PRIMAER
    assert s["endepunkter"]["reserve"]["url"] == RESERVE

    assert s["lokaliteter"] == {"primaer": 4, "reserve": 4, "felles": 3,
                                "bare_primaer": ["4"], "bare_reserve": ["5"]}
    avvik = {f: v["antall"] for f, v in s["felt_som_avviker"].items()}
    assert avvik == {"navn": 0, "status_lokalitet": 0, "har_fisk": 1,
                     "arter": 1, "siste_rapport": 1}, "objectid teller ikke"
    assert s["siste_rapport"]["reserve_eldre"] == 1
    assert s["siste_rapport"]["forskjeller"] == [
        {"loknr": "3", "primaer": "2025-08-31", "reserve": "2025-07-31",
         "retning": "reserve eldre"}]

    ut = capsys.readouterr().out
    assert "bare primær 1" in ut and "sha256" in ut


def test_samme_dato_to_ganger_overskriver_ikke(nett, tmp_path):
    nett[PRIMAER] = Lag([_rad(1)])
    nett[RESERVE] = Lag([_rad(1)], felter=RESERVE_FELTER)

    assert ph.kjor("2026-10-11") == 0
    assert ph.kjor("2026-10-11") == 0

    assert _filer(tmp_path) == [
        "primaer/2026-10-11.2.json.gz", "primaer/2026-10-11.json.gz",
        "reserve/2026-10-11.2.json.gz", "reserve/2026-10-11.json.gz",
        "sammenligning/2026-10-11.2.json", "sammenligning/2026-10-11.json"]


def test_torrkjoring_skriver_ingenting(nett, tmp_path):
    nett[PRIMAER] = Lag([_rad(1)])
    nett[RESERVE] = Lag([_rad(1)], felter=RESERVE_FELTER)

    assert ph.kjor("2026-10-11", torrkjor=True) == 0
    assert _filer(tmp_path) == []


# --------------------------------------------------------------- primær nede

def test_primaer_200_med_error_objekt_svarer_ikke_og_ingenting_skrives(
        nett, tmp_path, capsys):
    """Formen målt 02.10 og 04.10.2026."""
    nett[PRIMAER] = Lag([], feilsvar=True)
    nett[RESERVE] = Lag([_rad(1)], felter=RESERVE_FELTER)

    assert ph.kjor("2026-10-11") == 2
    assert _filer(tmp_path) == [], "verken feilkroppen eller reserven alene"
    ut = capsys.readouterr().out
    assert "primaer: SVARER IKKE (code 500)" in ut
    assert "Primæren svarer ikke" in ut


def test_primaer_http_feil_svarer_ikke(nett, tmp_path):
    nett[PRIMAER] = Lag([], status=503)
    nett[RESERVE] = Lag([_rad(1)], felter=RESERVE_FELTER)

    assert ph.kjor("2026-10-11") == 2
    assert _filer(tmp_path) == []


def test_fullstendighetsfeil_er_ikke_svarer_ikke(nett, tmp_path):
    """Primæren svarte, men `count` stemmer ikke. Det er ikke «nede», og
    det skal ikke se ut som det — samme skille som i kilden."""
    lag = Lag([_rad(1), _rad(2)])

    def feil_telling(req):
        if dict(req.url.params).get("returnCountOnly") == "true":
            return httpx.Response(200, json={"count": 3})
        return lag(req)

    nett[PRIMAER] = feil_telling
    nett[RESERVE] = Lag([_rad(1)], felter=RESERVE_FELTER)
    with pytest.raises(RuntimeError, match="sa 3 rader"):
        ph.kjor("2026-10-11")
    assert _filer(tmp_path) == []


# --------------------------------------------------------------- begge nede

def test_begge_nede(nett, tmp_path, capsys):
    nett[PRIMAER] = Lag([], feilsvar=True)
    nett[RESERVE] = Lag([], status=503)

    assert ph.kjor("2026-10-11") == 3
    assert _filer(tmp_path) == []
    ut = capsys.readouterr().out
    assert "primaer: SVARER IKKE (code 500)" in ut
    assert "reserve: SVARER IKKE (HTTP 503)" in ut


def test_bare_reserven_nede(nett, tmp_path):
    nett[PRIMAER] = Lag([_rad(1)])
    nett[RESERVE] = Lag([], feilsvar=True)

    assert ph.kjor("2026-10-11") == 4
    assert _filer(tmp_path) == []


# --------------------------------------------------------------- main()

def test_main_gir_exit_1_paa_annen_feil(nett, monkeypatch):
    nett[PRIMAER] = lambda req: httpx.Response(200, json={"count": "x"}) \
        if "/query" in str(req.url) else httpx.Response(200, json={"fields": []})
    nett[RESERVE] = Lag([_rad(1)], felter=RESERVE_FELTER)
    monkeypatch.setattr("sys.argv", ["parhent_biomasselag.py", "--dato", "2026-10-11"])
    assert ph.main() == 1
