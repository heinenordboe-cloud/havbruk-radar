"""arkiver_lovdata.py: forskriftskroppen lagres uendret og én gang, med
hash, og Lovdatas egne metadatafelt leses — aldri hentetidspunktet.

Fra 04.11.2026 henter skriptet ikke selv: kroppen er en fil Heine har
lagret i nettleseren, og `--hentet` er når han gjorde det.
"""

import gzip
import hashlib
import json

import pytest

import arkiver_lovdata as ark
from core import raw as raw_arkiv

HODE = (b"<html><body><ul><li>\xc2\xa7 17. Ikrafttredelse</li><li>Vedlegg</li></ul>"
        b"<dl><dt>Dato</dt><dd>FOR-2017-01-16-61</dd>"
        b"<dt>Ikrafttredelse</dt><dd>16.01.2017</dd>"
        b"<dt>Sist endret</dt><dd>FOR-2026-04-26-689</dd>"
        b"<dt>Kunngjort</dt><dd>25.01.2017 kl. 14.05</dd></dl>"
        b"<p>\xc2\xa7 12. Tilbud</p></body></html>")


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


HENTET = "2026-10-09T09:15:00+02:00"


def _args(tmp_path, kropp=HODE, dokumenter=None, hentet=HENTET):
    args = ["--dato", "2026-10-09", "--hentet", hentet]
    for dok in dokumenter or ark.DOKUMENTER:
        fil = tmp_path / f"{dok}.html"
        fil.write_bytes(kropp)
        args += ["--fil", f"{dok}={fil}"]
    return args


def test_uten_fil_henter_skriptet_ingenting_og_feiler(arkiv, capsys):
    """Lovdata-hentingene er stoppet: ingen standardoppførsel som går ut."""
    assert ark.main(["--dato", "2026-10-09"]) == 1
    assert "stoppet fra 04.11.2026" in capsys.readouterr().out
    assert not arkiv.exists()
    assert not hasattr(ark, "httpx") and not hasattr(ark, "_http")


def test_hentet_uten_sone_eller_ukjent_dokument_avvises(arkiv, tmp_path):
    assert ark.main(_args(tmp_path, hentet="2026-10-09T09:15:00")) == 1
    fil = tmp_path / "x.html"
    fil.write_bytes(HODE)
    assert ark.main(["--hentet", HENTET, "--fil", f"trafikklys={fil}"]) == 1
    assert not arkiv.exists()


def test_hvert_dokument_lagres_uendret_med_hash(arkiv, tmp_path):
    assert ark.main(_args(tmp_path)) == 0

    for dok in ark.DOKUMENTER:
        [fil] = (arkiv / f"lovdata-{dok}").glob("*.gz")
        assert fil.name == "2026-10-09.bin.gz"
        assert gzip.open(fil).read() == HODE, "kroppen slik den kom"
    logg = json.loads((arkiv / "lovdata" / "2026-10-09.logg.json").read_text())
    assert {r["dokument"] for r in logg} == set(ark.DOKUMENTER)
    assert all(r["sha256"] == hashlib.sha256(HODE).hexdigest() for r in logg)
    assert all(r["hentet_for_hand"] for r in logg)


def test_metadata_leses_av_dokumenthodet_ikke_av_innholdsfortegnelsen():
    """«Ikrafttredelse» er også en paragraftittel i innholdsfortegnelsen,
    som står FØR hodet. Navnet alene ga «Vedlegg» (MÅLT 09.10.2026)."""
    assert ark.metadata(HODE) == {
        "Dato": "FOR-2017-01-16-61", "Sist endret": "FOR-2026-04-26-689",
        "Ikrafttredelse": "16.01.2017", "Kunngjort": "25.01.2017 kl. 14.05"}


def test_en_lov_har_lovens_nummer_og_kunngjoring_uten_klokkeslett():
    """Åndsverkloven, MÅLT 09.10.2026: «Dato LOV-2018-06-15-40» og
    «Kunngjort 15.06.2018 Rettet …». Mønstrene på bare `FOR-` og på
    «kl.» ga to tomme felt."""
    hode = (b"<dl><dt>Dato</dt><dd>LOV-2018-06-15-40</dd>"
            b"<dt>Sist endret</dt><dd>LOV-2024-12-13-76</dd>"
            b"<dt>Kunngjort</dt><dd>15.06.2018</dd>"
            b"<dt>Rettet</dt><dd>28.11.2025</dd></dl>")
    m = ark.metadata(hode)
    assert m["Dato"] == "LOV-2018-06-15-40"
    assert m["Sist endret"] == "LOV-2024-12-13-76"
    assert m["Kunngjort"] == "15.06.2018"


def test_et_felt_som_mangler_er_tomt_ikke_gjettet():
    assert ark.metadata(b"<p>Dato FOR-2023-09-28-1520</p>")["Sist endret"] == ""


def test_published_at_er_tom_og_fetched_at_er_den_oppgitte(arkiv, tmp_path):
    """Aldri hentetidspunktet, og aldri dokumentets egne datoer
    (CLAUDE.md 1b-7). De står i `lovdata`, merket som Lovdatas.
    `fetched_at` er når Heine lagret fila, ikke når skriptet kjørte."""
    ark.main(_args(tmp_path))
    logg = json.loads((arkiv / "lovdata" / "2026-10-09.logg.json").read_text())
    assert all(r["published_at"] == "" for r in logg)
    assert all(r["lovdata"]["Ikrafttredelse"] == "16.01.2017" for r in logg)
    for r in logg:
        assert r["kode_commit"] == "0" * 40      # conftest låser den
        assert r["fetched_at"] == "2026-10-09T07:15:00+00:00"


def test_samme_kropp_to_ganger_skrives_en_gang_men_loggen_to(arkiv, tmp_path):
    ark.main(_args(tmp_path))
    ark.main(_args(tmp_path))
    for dok in ark.DOKUMENTER:
        assert len(list((arkiv / f"lovdata-{dok}").glob("*.gz"))) == 1
    assert (arkiv / "lovdata" / "2026-10-09.2.logg.json").exists(), \
        "en logg skrives aldri over"


def test_kode_som_ikke_kan_spores_arkiverer_ingenting(arkiv, tmp_path, monkeypatch,
                                                     capsys):
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("HEAD finnes ikke på origin/main")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)

    assert ark.main(_args(tmp_path)) == 1
    assert "::error::Lovdataarkiveringen startet ikke" in capsys.readouterr().out
    assert not arkiv.exists()


def test_en_fil_som_mangler_gir_rod_men_de_andre_arkiveres(arkiv, tmp_path):
    args = _args(tmp_path, dokumenter=["produksjonsomradeforskriften"])
    args += ["--fil", f"lakselusforskriften={tmp_path / 'finnes-ikke.html'}"]

    assert ark.main(args) == 1
    assert not (arkiv / "lovdata-lakselusforskriften").exists()
    assert (arkiv / "lovdata-produksjonsomradeforskriften").exists()
