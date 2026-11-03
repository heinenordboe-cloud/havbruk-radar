"""arkiver_flater.py: flatelaget hver dag, kroppen bare når den er ny.

Ingen nettverk: `hent_fn` gir svaret, som den falske kilden i
test_arkiver_luseinnkomst.py.
"""

import gzip
import json

import pytest

import arkiver_flater as ark
from core import raw as raw_arkiv


def svar(n=3):
    return {"displayFieldName": "loknr", "features": [
        {"attributes": {"loknr": 10000 + i, "navn": f"L{i}", "areal_m2": 1.5},
         "geometry": {"rings": [[[5.0, 60.0], [5.1, 60.0], [5.0, 60.1], [5.0, 60.0]]]}}
        for i in range(n)]}


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv" / ark.MAPPE


def kjor(rå, dato="2026-11-03"):
    return ark.main(["--dato", dato], hent_fn=lambda: rå)


@pytest.fixture(autouse=True)
def sporbar(monkeypatch):
    monkeypatch.setattr(ark.kodeproveniens, "krev_sporbar", lambda: ("a" * 40, "rent"))


def kropper(arkiv):
    return sorted(p.name for p in arkiv.glob("*.gz"))


def logger(arkiv):
    return {p.name: json.loads(p.read_text()) for p in arkiv.glob("*.logg.json")}


def test_forste_kropp_skrives_med_samme_bytes_som_raw(arkiv):
    assert kjor(svar()) == 0
    assert kropper(arkiv) == ["2026-11-03.json.gz"]
    b = gzip.decompress((arkiv / "2026-11-03.json.gz").read_bytes())
    assert b == raw_arkiv._serialiser(svar())[0]
    logg = logger(arkiv)["2026-11-03.fangst.logg.json"]
    assert logg["flater"]["status"] == "ny" and logg["flater"]["flater"] == 3
    assert logg["flater"]["published_at"] == ""
    assert logg["kode_commit"] == "a" * 40


def test_uendret_gir_bare_logg(arkiv):
    kjor(svar())
    assert kjor(svar(), "2026-11-04") == 0
    assert kropper(arkiv) == ["2026-11-03.json.gz"]
    assert logger(arkiv)["2026-11-04.fangst.logg.json"]["flater"]["status"] == "uendret"


def test_endret_flate_gir_ny_kropp(arkiv):
    kjor(svar())
    endret = svar()
    endret["features"][0]["attributes"]["areal_m2"] = 2.0
    kjor(endret, "2026-11-04")
    assert kropper(arkiv) == ["2026-11-03.json.gz", "2026-11-04.json.gz"]


def test_feilside_med_200_gaar_i_karantene_og_er_tatt_vare_paa(arkiv):
    side = b"<html><body>Proxy Error</body></html>"
    assert kjor(side) == 1
    assert kropper(arkiv) == []
    [kropp] = (arkiv / "karantene").glob("*.gz")
    assert gzip.decompress(kropp.read_bytes()) == side
    post = json.loads(kropp.with_name(kropp.name + ".json").read_text())
    assert post["status"] == "karantene" and "ikke JSON" in post["grunn"][0]


def test_tom_liste_gaar_i_karantene(arkiv):
    assert kjor({"features": []}) == 1
    assert kropper(arkiv) == []
    [post] = [json.loads(p.read_text()) for p in (arkiv / "karantene").glob("*.gz.json")]
    assert post["grunn"] == ["svaret har ingen flater"]


def test_error_objekt_med_200_gaar_i_karantene(arkiv):
    assert kjor({"error": {"code": 500, "message": "Error performing query operation"}}) == 1
    assert kropper(arkiv) == []


def test_avkortet_svar_gaar_i_karantene(arkiv):
    rå = dict(svar(), exceededTransferLimit=True)
    assert kjor(rå) == 1
    assert kropper(arkiv) == []


def test_under_halvparten_av_forrige_gaar_i_karantene(arkiv):
    kjor(svar(10))
    assert kjor(svar(4), "2026-11-04") == 1
    assert kropper(arkiv) == ["2026-11-03.json.gz"]
    assert kjor(svar(5), "2026-11-05") == 0


def test_torrkjoring_skriver_ingenting(arkiv):
    assert ark.main(["--dato", "2026-11-03", "--torrkjor"], hent_fn=lambda: svar()) == 0
    assert not arkiv.exists()


def test_nettfeil_gir_logg_og_exit_1(arkiv):
    def feil():
        raise RuntimeError("nede")
    assert ark.main(["--dato", "2026-11-03"], hent_fn=feil) == 1
    assert logger(arkiv)["2026-11-03.fangst.logg.json"]["flater"]["status"] == "feil"
