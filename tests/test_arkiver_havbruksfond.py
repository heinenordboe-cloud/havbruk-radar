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
    # Ingen nettverk: NTB-strømmen er tom og Wayback har ingen treff,
    # med mindre testen sier noe annet (se `_daglig`).
    monkeypatch.setattr(ark._http, "get", lambda klient, url, hva="": _Svar(
        content=b"<rss><channel></channel></rss>", text=""))
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


# ── --daglig (A6) ───────────────────────────────────────────────────

RSS = ("<rss><channel>"
       "<item><title>Presseinvitasjon: London</title>"
       "<link>https://kommunikasjon.ntb.no/pressemelding/1/london</link>"
       "<description>Næringsministeren</description></item>"
       "<item><title>Milliardutbetaling fra Havbruksfondet</title>"
       "<link>https://kommunikasjon.ntb.no/pressemelding/2/hf</link>"
       "<description>Kommunene får</description></item>"
       "<item><title>Utbetaling</title>"
       "<link>https://kommunikasjon.ntb.no/pressemelding/3/x</link>"
       "<description>gjennom havbruksfondet</description></item>"
       "</channel></rss>").encode()
NTB_KROPP = (b"<html><body><h1>Milliardutbetaling</h1>"
             b"<p>12.11.2026 10:00:00 CET | N\xc3\xa6rings- og "
             b"fiskeridepartementet | Pressemelding</p></body></html>")


class _Svar:
    def __init__(self, content=b"", text=""):
        self.content, self.text = content, text


def test_ntb_saker_velger_bare_saker_om_fondet():
    assert ark.ntb_saker(RSS) == [
        "https://kommunikasjon.ntb.no/pressemelding/2/hf",
        "https://kommunikasjon.ntb.no/pressemelding/3/x"]


def test_pressedato_leser_ntb_formatet():
    assert ark.pressedato(NTB_KROPP) == "2026-11-12"


def _daglig(monkeypatch, cdx="", rss=RSS, rss_feiler=False):
    def get(klient, url, hva=""):
        if url == ark.NTB_RSS:
            if rss_feiler:
                raise RuntimeError("503")
            return _Svar(content=rss)
        if "cdx" in url:
            return _Svar(text=cdx)
        raise AssertionError(url)
    monkeypatch.setattr(ark._http, "get", get)

    def hent(klient, url):
        if url == ark.SIDE:
            return SIDE, ""
        if "kommunikasjon.ntb.no" in url:
            return NTB_KROPP + url.encode(), ""
        if "regjeringen.no" in url:
            return PM + url.encode(), ""
        return b"%PDF-1.7 " + url.encode(), ""
    monkeypatch.setattr(ark, "_hent", hent)


def test_daglig_henter_ikke_de_faste_kroppene_og_arkiverer_ntb_under_sin_dato(
        arkiv, monkeypatch):
    _daglig(monkeypatch)
    assert ark.main(["--daglig", "--dato", "2026-11-12"]) == 0
    hf = list((arkiv / "havbruksfondet").glob("*.gz"))
    assert len(hf) == 1 + 2, "siden og vedleggene, ingen instrukser"
    ntb = sorted(p.name for p in (arkiv / "ntb-pressemeldinger").glob("*.gz"))
    assert ntb == ["2026-11-12.2.bin.gz", "2026-11-12.bin.gz"]
    assert not (arkiv / "regjeringen-pressemeldinger").exists()


def test_daglig_tar_wayback_treff_inn_under_meldingens_dato(arkiv, monkeypatch):
    cdx = ("20261112180000 https://www.regjeringen.no/no/aktuelt/"
           "havbruksfondet-2026/id1/\n")
    _daglig(monkeypatch, cdx=cdx)
    ark.main(["--daglig", "--dato", "2026-11-13"])
    [pm] = (arkiv / "regjeringen-pressemeldinger").glob("*.gz")
    assert pm.name == "2025-11-10.bin.gz", "datoen i kroppen, ikke kjøredagen"


def test_daglig_ntb_som_feiler_er_en_advarsel_ikke_en_stille_null(
        arkiv, monkeypatch):
    _daglig(monkeypatch, rss_feiler=True)
    assert ark.main(["--daglig", "--dato", "2026-11-12"]) == 0
    logg = json.loads((arkiv / "havbruksfondet" / "2026-11-12.logg.json")
                      .read_text())
    assert any(r.get("advarsel") == "ntb_feilet" for r in logg)


def test_daglig_er_rod_bare_naar_alt_feilet(arkiv, monkeypatch):
    _daglig(monkeypatch)

    def feil(klient, url):
        raise RuntimeError("nede")
    monkeypatch.setattr(ark, "_hent", feil)
    assert ark.main(["--daglig", "--dato", "2026-11-12"]) == 1


def test_daglig_uten_noe_nytt_skriver_ingen_ny_logg(arkiv, monkeypatch):
    """Tre kjøringer i døgnet mot en uendret side skal gi én fil, ikke tre."""
    _daglig(monkeypatch, rss=b"<rss><channel></channel></rss>")
    ark.main(["--daglig", "--dato", "2026-11-12"])
    ark.main(["--daglig", "--dato", "2026-11-12"])
    ark.main(["--daglig", "--dato", "2026-11-12"])
    assert [p.name for p in (arkiv / "havbruksfondet").glob("*.logg.json")] \
        == ["2026-11-12.logg.json"]
