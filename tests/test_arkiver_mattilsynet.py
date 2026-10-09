"""arkiver_mattilsynet.py liste: kildens eget svar, arkivert under
kildens navn — ingen kobling skrives om her.

Ingen nettverk: `Unntaksvekst.fetch` byttes ut.
"""

import gzip
import json

import pytest

import arkiver_mattilsynet as ark
from core import raw as raw_arkiv
from sources.unntaksvekst import Unntaksvekst

SVAR = {"url": "https://mattilsynet.no/x", "status": 200, "sha256": "cd" * 32,
        "bytes": 10, "headere": {"age": "5"},
        "rader": [{"lokalitet": "A", "po": "3", "resultat": "Godkjent",
                   "saksnumre": ["1"], "kobling": "entydig",
                   "lokalitet_nr": "100", "kandidater": ["100"]},
                  {"lokalitet": "B", "po": "3", "resultat": "Avslag",
                   "saksnumre": ["2"], "kobling": "usikker",
                   "lokalitet_nr": "200", "kandidater": ["200"]}]}


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(Unntaksvekst, "fetch", lambda self, d: SVAR)
    return tmp_path / "arkiv"


def test_lista_arkiveres_under_kildens_navn_og_dato(arkiv):
    assert ark.main(["liste", "--dato", "2026-10-09"]) == 0
    [fil] = (arkiv / "unntaksvekst").glob("*.gz")
    assert fil.name == "2026-10-09.json.gz"
    assert json.loads(gzip.open(fil).read()) == SVAR, "kildens svar, uendret"
    [post] = json.loads((arkiv / "mattilsynet" / "2026-10-09.logg.json")
                        .read_text())
    assert post["koblet"] == 1 and post["rader"] == 2
    assert post["kropp_sha256"] == "cd" * 32
    assert post["published_at"] == "", "siden har ingen Last-Modified"
    assert post["kode_commit"] == "0" * 40


def test_samme_svar_to_ganger_arkiveres_en_gang(arkiv):
    ark.main(["liste", "--dato", "2026-10-09"])
    ark.main(["liste", "--dato", "2026-10-09"])
    assert len(list((arkiv / "unntaksvekst").glob("*.gz"))) == 1
    assert (arkiv / "mattilsynet" / "2026-10-09.2.logg.json").exists()


def test_torrkjoring_skriver_ingenting(arkiv):
    assert ark.main(["liste", "--torrkjor"]) == 0
    assert not arkiv.exists()


def test_kode_som_ikke_kan_spores_henter_ingenting(arkiv, monkeypatch, capsys):
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("urent")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)
    monkeypatch.setattr(Unntaksvekst, "fetch",
                        lambda self, d: pytest.fail("skulle ikke hentet"))
    assert ark.main(["liste", "--dato", "2026-10-09"]) == 1
    assert "::error::Mattilsynet-arkiveringen startet ikke" in capsys.readouterr().out
