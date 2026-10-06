"""arkiver_auksjon.py: de tre stille tilfellene sier fra.

Tom indeks, feil i Wayback-oppslaget, og feil sammen med nye kropper sto
bare som en `print` fram til 06.10.2026. Jobben var grønn, og loggfila
sa ingenting. Nå gir de `::warning::` og en post i loggfila.

Ingen nettverk: `_hent` og `_http.get` byttes ut.
"""

import json
import sys

import pytest

import arkiver_auksjon as ark
from core import raw as raw_arkiv

INDEKS_MED_BARN = (b'<a href="/akvakultur/auksjon-av-produksjonskapasitet/'
                   b'auksjon-2022">2022</a>')


@pytest.fixture
def kjor(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")

    def kjor(hent, cdx):
        monkeypatch.setattr(ark, "_hent", lambda klient, url: hent(url))
        monkeypatch.setattr(ark._http, "get",
                            lambda klient, url, hva=None: cdx(url))
        monkeypatch.setattr(sys, "argv", ["arkiver_auksjon.py",
                                          "--dato", "2026-10-06"])
        kode = ark.main()
        logg = json.loads((tmp_path / "arkiv" / ark.KILDE
                           / "2026-10-06.logg.json").read_text())
        return kode, logg
    return kjor


class Svar:
    def __init__(self, tekst):
        self.text = tekst


def _advarsler(logg):
    return [r["advarsel"] for r in logg if "advarsel" in r]


def test_wayback_som_feiler_er_en_advarsel_og_ikke_null_avtrykk(kjor, capsys):
    def cdx(url):
        raise RuntimeError("504 Gateway Time-out")

    kode, logg = kjor(lambda url: (INDEKS_MED_BARN, ""), cdx)

    assert kode == 0, "indeksen kom inn som ny; dagen er ikke tom"
    assert _advarsler(logg) == ["wayback_feilet"]
    ut = capsys.readouterr().out
    assert "::warning::Auksjonsarkivering: Wayback-oppslaget (CDX) feilet: " \
           "504 Gateway Time-out" in ut


def test_tom_indeks_er_en_advarsel(kjor, capsys):
    kode, logg = kjor(lambda url: (b"<html>ingen lenker</html>", ""),
                      lambda url: Svar(""))

    assert _advarsler(logg) == ["tom_indeks"]
    assert "lenket ingen auksjonsrunder" in capsys.readouterr().out
    assert kode == 0


def test_indeks_som_ikke_kan_leses_er_feil_og_advarsel(kjor):
    def hent(url):
        raise RuntimeError("tilkobling nektet")

    kode, logg = kjor(hent, lambda url: Svar(""))

    assert [r for r in logg if "feil" in r], "selve indeksen er en feil"
    assert _advarsler(logg) == ["tom_indeks"]
    assert kode == 1, "feil og ingenting nytt: rød, som før"


def test_feil_sammen_med_nye_kropper_er_en_advarsel(kjor, capsys):
    def hent(url):
        if url.endswith("auksjon-2022"):
            raise RuntimeError("500")
        return INDEKS_MED_BARN, ""

    kode, logg = kjor(hent, lambda url: Svar(""))

    assert kode == 0, "noe nytt kom inn; grønn, som før"
    assert _advarsler(logg) == ["feil_med_nye"]
    assert "1 adresse(r) feilet samme dag som 1 ny(e)" in capsys.readouterr().out


def test_en_vanlig_dag_har_ingen_advarsler(kjor, capsys):
    kode, logg = kjor(lambda url: (INDEKS_MED_BARN, ""), lambda url: Svar(""))

    assert kode == 0
    assert _advarsler(logg) == []
    assert "::warning::" not in capsys.readouterr().out
