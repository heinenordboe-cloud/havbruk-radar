"""arkiver_vilkar.py: kroppen lagres uendret og én gang, med hash.

Ingen nettverk: `_hent` byttes ut.
"""

import gzip
import hashlib
import json

import pytest

import arkiver_vilkar as ark
from core import raw as raw_arkiv


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


def _sider(monkeypatch, svar):
    monkeypatch.setattr(ark, "_hent", lambda klient, url: svar(url))


def test_hver_side_lagres_uendret_med_hash(arkiv, monkeypatch):
    kropp = b"<html><script>x=1</script><p>Du har lov</p></html>"
    _sider(monkeypatch, lambda url: (kropp, "Thu, 02 Nov 2023 10:00:00 GMT"))

    assert ark.main(["--dato", "2026-10-06"]) == 0

    for part in ark.SIDER:
        [fil] = (arkiv / f"vilkar-{part}").glob("*.gz")
        assert fil.name == "2026-10-06.bin.gz"
        assert gzip.open(fil).read() == kropp, "kroppen slik den kom"
    logg = json.loads((arkiv / "vilkar" / "2026-10-06.logg.json").read_text())
    assert {r["part"] for r in logg} == set(ark.SIDER)
    assert all(r["sha256"] == hashlib.sha256(kropp).hexdigest() for r in logg)
    assert all(r["published_at"] == "Thu, 02 Nov 2023 10:00:00 GMT" for r in logg)
    assert all(r["tekst_sha256"] == hashlib.sha256(b"Du har lov").hexdigest()
               for r in logg), "teksthashen ser bort fra skript og tagger"


def test_samme_kropp_neste_maaned_skrives_ikke_igjen(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (b"<p>uendret</p>", ""))
    ark.main(["--dato", "2026-10-06"])
    ark.main(["--dato", "2026-11-02"])

    for part in ark.SIDER:
        assert len(list((arkiv / f"vilkar-{part}").glob("*.gz"))) == 1
    logg = json.loads((arkiv / "vilkar" / "2026-11-02.logg.json").read_text())
    assert not any(r["ny"] for r in logg)


def test_uten_last_modified_er_published_at_tom(arkiv, monkeypatch):
    """Aldri hentetidspunktet (CLAUDE.md 1b-7)."""
    _sider(monkeypatch, lambda url: (b"x", ""))
    ark.main(["--dato", "2026-10-06"])
    logg = json.loads((arkiv / "vilkar" / "2026-10-06.logg.json").read_text())
    assert all(r["published_at"] == "" for r in logg)


def test_en_side_som_feiler_gir_rod_men_de_andre_arkiveres(arkiv, monkeypatch, capsys):
    def svar(url):
        if "lovdata" in url:
            raise RuntimeError("403")
        return b"<p>ok</p>", ""
    _sider(monkeypatch, svar)

    assert ark.main(["--dato", "2026-10-06"]) == 1
    assert "::error::Vilkårsarkivering: https://lovdata.no/info/brukeravtale" \
           in capsys.readouterr().out
    assert not (arkiv / "vilkar-lovdata").exists()
    assert len(list((arkiv / "vilkar-barentswatch").glob("*.gz"))) == 1
