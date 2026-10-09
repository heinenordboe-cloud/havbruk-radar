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


# ---------------------------------------------------------------- lakselus

class _Svar:
    def __init__(self, data, url="https://api/x", status=200, headers=None):
        self._data = data
        self.content = json.dumps(data).encode()
        self.url = url
        self.status_code = status
        self.headers = headers or {"date": "Fri, 09 Oct 2026 08:00:00 GMT"}

    def json(self):
        return self._data


def _rapport(lok, org, navn="NOE AS", uke=40):
    return {"id": f"{lok}-{uke}", "lokalitetsnummer": int(lok),
            "organisasjonsnummer": org, "organisasjonsnavn": navn,
            "år": 2025, "uke": uke, "lusetelling": {"voksneHunnlus": 0.05},
            "medikamentelleBehandlinger": []}


@pytest.fixture
def lusarkiv(arkiv, monkeypatch):
    """Lista med 100 (entydig) og 200 (usikker), og en eierskapskropp
    der 921668236 er et AS."""
    raw_arkiv.arkiver("unntaksvekst", "2026-10-09", SVAR)
    raw_arkiv.arkiver("eierskap", "2026-10-05", {
        "enheter": [{"openNr": "921668236",
                     "typeValue": "LimitedLiabilityCompany"}],
        "tillatelser": [], "personer_fjernet": 0})
    monkeypatch.setattr(ark, "PAUSE_S", 0)
    kall = []

    def hent(klient, url, params=None):
        kall.append((url, params))
        if url == ark.OPENAPI:
            return _Svar({"info": {"version": "ed7f9fe",
                                   "license": {"name": "NLOD"}}})
        nr = params["lokalitetsnummer"]
        return _Svar([_rapport(nr, "921668236"),
                      _rapport(nr, "999999999", navn="OLA NORDMANN", uke=41)],
                     url=f"{url}?lokalitetsnummer={nr}")
    monkeypatch.setattr(ark, "_hent", hent)
    return kall


def test_sikre_og_usikre_lokaliteter_hentes_hver_for_seg(arkiv, lusarkiv):
    assert ark.main(["lakselus", "--dato", "2026-10-09"]) == 0
    assert [p["lokalitetsnummer"] for _u, p in lusarkiv if p] == ["100", "200"]
    for nr in ("100", "200"):
        [fil] = (arkiv / "mattilsynet-lakselus" / nr).glob("*.gz")
        assert fil.name == "2026-10-09.json.gz"
    assert len(list((arkiv / "mattilsynet-openapi").glob("*.gz"))) == 1


def test_en_rapportor_som_ikke_er_et_kjent_selskap_blankes_for_arkivering(
        arkiv, lusarkiv):
    """«Vet ikke» er nei — og navnet skal ikke inn i et append-only arkiv."""
    ark.main(["lakselus", "--dato", "2026-10-09"])
    data = gzip.open(arkiv / "mattilsynet-lakselus" / "100" /
                     "2026-10-09.json.gz").read()
    assert b"OLA NORDMANN" not in data and b"999999999" not in data
    post = json.loads(data)
    assert post["rapportor_blanket"] == 1
    [ok, blank] = post["rapporter"]
    assert ok["organisasjonsnavn"] == "NOE AS"
    assert (blank["organisasjonsnummer"], blank["organisasjonsnavn"]) == ("", "")
    assert blank["lusetelling"] == {"voksneHunnlus": 0.05}, \
        "lusetallet er lokalitetsdata og beholdes"
    assert len(post["sha256"]) == 64, "hashen av kroppen slik den kom"


def test_et_svar_med_rapporter_for_en_annen_lokalitet_er_en_feil(
        arkiv, lusarkiv, monkeypatch, capsys):
    monkeypatch.setattr(ark, "_hent", lambda k, url, params=None: (
        _Svar({"info": {}}) if url == ark.OPENAPI
        else _Svar([_rapport("999", "921668236")])))
    assert ark.main(["lakselus", "--dato", "2026-10-09"]) == 1
    assert "svaret har rapporter for ['999']" in capsys.readouterr().out
    assert not (arkiv / "mattilsynet-lakselus").exists()


def test_publisert_er_tom_uten_last_modified(arkiv, lusarkiv):
    ark.main(["lakselus", "--dato", "2026-10-09"])
    logg = json.loads((arkiv / "mattilsynet" / "2026-10-09.logg.json").read_text())
    assert all(p["published_at"] == "" for p in logg)
    assert {p["hva"] for p in logg} == {"openapi", "lakselus"}
