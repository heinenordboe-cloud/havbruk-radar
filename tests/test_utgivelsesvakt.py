"""utgivelsesvakt.py: kroppen bare når den er ny, og `endret=` til jobben.

Ingen nettverk: `hent_fn` gir (kropp, Last-Modified) per URL.
"""

import gzip
import json

import pytest

import utgivelsesvakt as vakt
from core import raw as raw_arkiv

GEO = json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature"}]}).encode()
LM = "Fri, 28 Aug 2026 05:00:09 GMT"


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(vakt.kodeproveniens, "krev_sporbar", lambda: ("b" * 40, "rent"))
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    return tmp_path / "arkiv"


def kjor(kropp, dato="2026-11-09", output=None, monkeypatch=None):
    return vakt.main(["--dato", dato], hent_fn=lambda url: (kropp, LM))


def kropper(arkiv):
    return sorted(p.name for p in (arkiv / "utgivelse-regomr").glob("*.gz"))


def test_forste_kropp_er_bytene_slik_de_kom(arkiv):
    assert kjor(GEO) == 0
    assert kropper(arkiv) == ["2026-11-09.bin.gz"]
    assert gzip.decompress((arkiv / "utgivelse-regomr" / "2026-11-09.bin.gz").read_bytes()) == GEO
    logg = json.loads((arkiv / "utgivelsesvakt" / "2026-11-09.logg.json").read_text())
    [s] = logg["sider"]
    assert s["status"] == "ny" and s["published_at"] == "" and s["last_modified"] == LM


def test_uendret_gir_ingen_kropp_og_tom_endret(arkiv, tmp_path, monkeypatch):
    kjor(GEO)
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert kjor(GEO, "2026-11-16") == 0
    assert kropper(arkiv) == ["2026-11-09.bin.gz"]
    assert out.read_text() == "endret=\n"


def test_ny_utgave_gir_kropp_og_endret(arkiv, tmp_path, monkeypatch):
    kjor(GEO)
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    ny = GEO.replace(b"Feature\"}", b"Feature\", \"id\": 2}")
    assert kjor(ny, "2026-11-16") == 0
    assert kropper(arkiv) == ["2026-11-09.bin.gz", "2026-11-16.bin.gz"]
    assert out.read_text() == "endret=regomr\n"


def test_feilside_med_200_gaar_i_karantene(arkiv):
    side = b"<!DOCTYPE html><html><body>Maintenance</body></html>"
    assert kjor(side) == 1
    assert kropper(arkiv) == []
    [kropp] = (arkiv / "utgivelse-regomr" / "karantene").glob("*.gz")
    assert gzip.decompress(kropp.read_bytes()) == side
    post = json.loads(kropp.with_name(kropp.name + ".json").read_text())
    assert post["grunn"] == ["kroppen er en HTML-side, ikke GeoJSON"]


def test_tom_liste_gaar_i_karantene(arkiv):
    assert kjor(json.dumps({"type": "FeatureCollection", "features": []}).encode()) == 1
    assert kropper(arkiv) == []
    [post] = [json.loads(p.read_text())
              for p in (arkiv / "utgivelse-regomr" / "karantene").glob("*.gz.json")]
    assert post["grunn"] == ["GeoJSON uten features"]


def test_tom_kropp_gaar_i_karantene(arkiv):
    assert kjor(b"") == 1
    assert kropper(arkiv) == []


def test_torrkjoring_skriver_ingenting(arkiv):
    assert vakt.main(["--dato", "2026-11-09", "--torrkjor"],
                     hent_fn=lambda url: (GEO, LM)) == 0
    assert not arkiv.exists()
