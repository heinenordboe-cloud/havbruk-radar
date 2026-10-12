"""arkiver_havbruksfond.py: kroppene lagres uendret og én gang, vedleggene
leses av siden, og pressemeldingene arkiveres under sin egen dato.

Ingen nettverk: `_hent` byttes ut.
"""

import gzip
import json

import pytest

import arkiver_havbruksfond as ark
from core import kodeproveniens
from core import raw as raw_arkiv

V1 = ("/akvakultur/havbruksfondet/_/attachment/download/aa:bb/"
      "Beregning%20utbetaling%202025.xlsx")
V2 = ("/akvakultur/havbruksfondet/_/attachment/inline/cc:dd/"
      "Orientering%202025.pdf")
SIDE = (f'<html><body><a href="{V1}">2025</a><a href="{V2}">brev</a>'
        f'<a href="{V1}">igjen</a><a href="/annet">x</a></body></html>').encode()
PM = (b"<html><body><p>Pressemelding | Dato: 10.11.2025 | "
      b"N\xc3\xa6rings- og fiskeridepartementet</p></body></html>")


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar",
                        lambda: ("a" * 40, kodeproveniens.RENT))
    return tmp_path / "arkiv"


def _svar(monkeypatch, side=SIDE, utgitt=""):
    def hent(klient, url):
        if url == ark.SIDE:
            return side, ""
        if "regjeringen.no" in url:
            return PM + url.encode(), utgitt
        return b"%PDF-1.7 " + url.encode(), utgitt
    monkeypatch.setattr(ark, "_hent", hent)


def test_vedleggene_leses_av_siden_unike_og_absolutte():
    assert ark.vedlegg(SIDE) == sorted(["https://www.fiskeridir.no" + V1,
                                        "https://www.fiskeridir.no" + V2])


def test_hver_kropp_lagres_uendret_og_pressemeldingen_under_sin_dato(
        arkiv, monkeypatch):
    _svar(monkeypatch)
    assert ark.main(["--dato", "2026-10-12"]) == 0

    hf = sorted(p.name for p in (arkiv / "havbruksfondet").glob("*.gz"))
    # Siden, to vedlegg og tre instrukser.
    assert len(hf) == 1 + 2 + len(ark.INSTRUKSER)
    assert all(n.startswith("2026-10-12") for n in hf)

    pm = sorted((arkiv / "regjeringen-pressemeldinger").glob("*.gz"))
    assert len(pm) == len(ark.PRESSEMELDINGER)
    assert all(p.name.startswith("2025-11-10") for p in pm), \
        "pressemeldingens egen «Dato:», ikke kjøredagen"
    assert gzip.open(pm[0]).read().startswith(PM)

    logg = json.loads((arkiv / "havbruksfondet" / "2026-10-12.logg.json")
                      .read_text())
    assert all(r["kode_commit"] == "a" * 40 for r in logg if "sha256" in r)


def test_andre_kjoring_skriver_ingen_ny_kropp(arkiv, monkeypatch):
    _svar(monkeypatch)
    ark.main(["--dato", "2026-10-12"])
    for_ = sorted(p.name for p in arkiv.rglob("*.gz"))
    ark.main(["--dato", "2026-10-13"])
    assert sorted(p.name for p in arkiv.rglob("*.gz")) == for_
    logg = json.loads((arkiv / "havbruksfondet" / "2026-10-13.logg.json")
                      .read_text())
    assert not any(r.get("ny") for r in logg)


def test_published_at_er_tom_uten_header_aldri_hentetidspunktet(
        arkiv, monkeypatch):
    _svar(monkeypatch, utgitt="")
    ark.main(["--dato", "2026-10-12"])
    logg = json.loads((arkiv / "havbruksfondet" / "2026-10-12.logg.json")
                      .read_text())
    assert all(r["published_at"] == "" for r in logg if "sha256" in r)


def test_side_uten_vedlegg_gir_advarsel_i_loggen(arkiv, monkeypatch):
    _svar(monkeypatch, side=b"<html>ingen lenker</html>")
    ark.main(["--dato", "2026-10-12"])
    logg = json.loads((arkiv / "havbruksfondet" / "2026-10-12.logg.json")
                      .read_text())
    assert any(r.get("advarsel") == "ingen_vedlegg" for r in logg)


def test_pressedato_tom_naar_den_mangler():
    assert ark.pressedato(b"<p>ingen dato her</p>") == ""
    assert ark.pressedato(PM) == "2025-11-10"
