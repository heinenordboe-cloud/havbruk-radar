"""arkiver_daglig.py: kroppen skrives bare når den avviker fra siste lagrede.

Ingen nettverk: kildene er falske, og `registry.discover` byttes ut.
"""

import gzip
import hashlib
import json

import pytest

import arkiver_daglig as ark
from core import raw as raw_arkiv
from core import registry


class Falsk:
    """En kilde som svarer det `svar` sier, og kan feile."""

    version = "1"

    def __init__(self, name, svar):
        self.name, self.svar = name, svar
        self.utvalg = {"utelatt": ["PERSON"]}

    def fetch(self, kjoredato):
        verdi = self.svar[self.name]
        if isinstance(verdi, Exception):
            raise verdi
        return verdi


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


@pytest.fixture
def svar(monkeypatch):
    s = {"eierskap": {"tillatelser": [1]}, "biomasselag": [{"a": 1}]}
    monkeypatch.setattr(registry, "discover",
                        lambda: [Falsk(n, s) for n in ("eierskap", "biomasselag")])
    return s


def logger(arkiv, kilde):
    return [json.loads(p.read_text()) for p in sorted((arkiv / kilde).glob("*.logg.json"))]


def kropper(arkiv, kilde):
    return sorted(p.name for p in (arkiv / kilde).glob("*.gz"))


def test_forste_kjoring_skriver_kropp_og_logg(arkiv, svar):
    assert ark.main(["--dato", "2026-10-13"]) == 0
    assert kropper(arkiv, "eierskap") == ["2026-10-13.json.gz"]
    [logg] = logger(arkiv, "eierskap")
    assert logg["kjoring"] == "daglig" and logg["status"] == "ny"
    assert logg["fil"] == "2026-10-13.json.gz"
    assert logg["sammenlignet_med"] is None
    assert logg["kode_commit"] == "0" * 40          # conftest låser den
    assert logg["utvalg"] == {"utelatt": ["PERSON"]}


def test_kroppen_er_de_samme_bytene_som_innsamlingen_ville_skrevet(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    data, _ = raw_arkiv._serialiser(svar["eierskap"])
    lagret = gzip.open(arkiv / "eierskap" / "2026-10-13.json.gz", "rb").read()
    assert lagret == data
    assert logger(arkiv, "eierskap")[0]["sha256"] == hashlib.sha256(data).hexdigest()


def test_uendret_mot_ukentlig_kropp_gir_bare_logg(arkiv, svar):
    """Mandagens kropp fra innsamlingen har ingen logg: den er ukentlig."""
    raw_arkiv.arkiver("eierskap", "2026-10-12", svar["eierskap"])
    assert ark.main(["--dato", "2026-10-13"]) == 0
    assert kropper(arkiv, "eierskap") == ["2026-10-12.json.gz"]
    [logg] = logger(arkiv, "eierskap")
    assert logg["status"] == "uendret" and "fil" not in logg
    assert logg["sammenlignet_med"]["fil"] == "2026-10-12.json.gz"
    assert logg["sammenlignet_med"]["kjoring"] == "ukentlig"


def test_uendret_mot_daglig_kropp_sier_daglig(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    ark.main(["--dato", "2026-10-14"])
    assert kropper(arkiv, "eierskap") == ["2026-10-13.json.gz"]
    andre = logger(arkiv, "eierskap")[1]
    assert andre["status"] == "uendret"
    assert andre["sammenlignet_med"] == {
        "fil": "2026-10-13.json.gz", "kjoring": "daglig",
        "sha256": logger(arkiv, "eierskap")[0]["sha256"]}


def test_endret_kropp_skrives_med_lopenummer_samme_dag(arkiv, svar):
    raw_arkiv.arkiver("eierskap", "2026-10-13", svar["eierskap"])
    svar["eierskap"] = {"tillatelser": [1, 2]}
    ark.main(["--dato", "2026-10-13"])
    assert kropper(arkiv, "eierskap") == ["2026-10-13.2.json.gz", "2026-10-13.json.gz"]
    [logg] = logger(arkiv, "eierskap")
    assert logg["status"] == "ny" and logg["fil"] == "2026-10-13.2.json.gz"


def test_tilbake_til_en_gammel_kropp_er_en_endring(arkiv, svar):
    """A, B, A: den tredje avviker fra SISTE lagrede (B), og skrives — selv
    om de samme bytene ligger i arkivet fra før. Det er forskjellen fra
    `raw.arkiver_ny()`, og det er den som bevarer at registeret gikk tilbake."""
    a = svar["eierskap"]
    ark.main(["--dato", "2026-10-13"])
    svar["eierskap"] = {"tillatelser": [9]}
    ark.main(["--dato", "2026-10-14"])
    svar["eierskap"] = a
    ark.main(["--dato", "2026-10-15"])
    assert kropper(arkiv, "eierskap") == [
        "2026-10-13.json.gz", "2026-10-14.json.gz", "2026-10-15.json.gz"]


def test_to_kjoringer_samme_dag_gir_to_logger(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    ark.main(["--dato", "2026-10-13"])
    navn = sorted(p.name for p in (arkiv / "eierskap").glob("*.logg.json"))
    assert navn == ["2026-10-13.2.logg.json", "2026-10-13.logg.json"]


def test_en_kilde_som_feiler_koster_ikke_de_andre(arkiv, svar, capsys):
    svar["eierskap"] = RuntimeError("503")
    assert ark.main(["--dato", "2026-10-13"]) == 1
    assert "::error::Daglig arkiv: eierskap feilet: RuntimeError: 503" \
        in capsys.readouterr().out
    assert not (arkiv / "eierskap").exists()
    assert kropper(arkiv, "biomasselag") == ["2026-10-13.json.gz"]


def test_torrkjoring_skriver_ingenting(arkiv, svar, monkeypatch):
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("urent")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)
    assert ark.main(["--torrkjor", "--dato", "2026-10-13"]) == 0
    assert not arkiv.exists()


def test_kode_som_ikke_kan_spores_henter_ingenting(arkiv, svar, monkeypatch, capsys):
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("HEAD finnes ikke på origin/main")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)
    svar["eierskap"] = AssertionError("skulle ikke hentet noe")
    assert ark.main(["--dato", "2026-10-13"]) == 1
    assert "::error::Det daglige arkivet startet ikke" in capsys.readouterr().out
    assert not arkiv.exists()


def test_akvakultur_er_ikke_med_for_lagringsformen_er_valgt():
    """MÅLT 13.10.2026: kroppen er aldri byte-lik (rekkefølgen i
    speciesTypes). Se modulens docstring. Prøven står så kilden ikke
    legges til uten at noen har sett hvorfor den mangler."""
    assert "akvakultur" not in ark.KILDER
