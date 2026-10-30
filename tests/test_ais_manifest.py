"""ais_manifest.py: manifester skrives én gang, status overskrives."""
import io
import json
import sys

import pytest

import ais_manifest

S = "b" * 64


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(ais_manifest, "MANIFEST_DIR", tmp_path / "arkiv/ais-manifest")
    monkeypatch.setattr(ais_manifest, "STATUS", tmp_path / "ais/status.json")
    monkeypatch.setattr(ais_manifest, "DATA_DIR", tmp_path)
    return tmp_path


def kjør(monkeypatch, manifester, skrevet="2026-10-30T08:30:00Z"):
    inn = {"skrevet": skrevet, "disk": {}, "manifester": manifester}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(inn)))
    ais_manifest.main()


def test_skrives_en_gang_og_endring_faar_lopenummer(data, monkeypatch):
    m = {"kilde": "bw", "dato": "2026-10-29", "innhold": f"{S}  2026-10-29T00Z.txt.zst\n"}
    kjør(monkeypatch, [m])
    kjør(monkeypatch, [m], skrevet="2026-10-31T08:30:00Z")
    mappe = data / "arkiv/ais-manifest/bw"
    assert [p.name for p in mappe.iterdir()] == ["2026-10-29.SHA256SUMS"]
    assert json.loads((data / "ais/status.json").read_text())["skrevet"] == "2026-10-31T08:30:00Z"
    assert "manifester" not in json.loads((data / "ais/status.json").read_text())

    m2 = dict(m, innhold=m["innhold"] + f"{S}  2026-10-29T23Z.avbrutt.txt.zst\n")
    kjør(monkeypatch, [m2])
    assert sorted(p.name for p in mappe.iterdir()) == ["2026-10-29.2.SHA256SUMS", "2026-10-29.SHA256SUMS"]
    assert (mappe / "2026-10-29.SHA256SUMS").read_text() == m["innhold"]


@pytest.mark.parametrize("kilde,dato,innhold", [
    ("../x", "2026-10-29", ""),
    ("bw", "2026-10-29/../..", ""),
    ("bw", "2026-10-29", "ikke en sum\n"),
    ("bw", "2026-10-29", f"{S}  ../../ut\n"),
])
def test_avviser_det_som_ikke_er_et_manifest(data, kilde, dato, innhold):
    with pytest.raises(ValueError):
        ais_manifest.skriv_manifest(kilde, dato, innhold)
