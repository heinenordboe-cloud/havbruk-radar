"""Skåreren for maskinanslagene: skaar_anslag.py (økt 8).

Utfallet, fasiten.json og trefflista. Snapshotene, ukefilene og stempelet
er de samme falske som i test_anslag.py: ingenting rører ekte data eller
nettet.
"""
import datetime as dt
import json

import pytest

import anslag
import skaar_anslag
from tests.test_anslag import NAA, T, _grunnlag, _uke, isolert  # noqa: F401 — fiksturen


@pytest.fixture
def skaarer(isolert, monkeypatch):  # noqa: F811
    monkeypatch.setattr(skaar_anslag, "FASIT", anslag.MASKIN_DIR / "fasiten.json")
    monkeypatch.setattr(skaar_anslag, "TREFFLISTE", anslag.MASKIN_DIR / "treffliste.md")
    _grunnlag()
    assert anslag.main(["--forsegl"], naa=NAA) == 0
    return isolert


def _utfallsukene(brakklegg_11_i_T1=True, n_k6=6):
    """Uke T−3 … T+4. Lokalitet 11 brakklegges i uke T+1. I måluka for K6
    rapporterer `n_k6` lokaliteter, med lus 0,3."""
    for k in range(-3, 4):
        d = T + dt.timedelta(weeks=k)
        brakk = {"11": "True"} if (brakklegg_11_i_T1 and k >= 1) else {}
        _uke(d, brakklagt=brakk)
    _uke(T + dt.timedelta(weeks=4), lus="0.3",
         lokaliteter=("11", "12", "13", "14", "15", "16")[:n_k6])


def _fasit() -> dict:
    return json.loads(skaar_anslag.FASIT.read_text(encoding="utf-8"))


def test_aapne_anslag_venter_paa_dataene(skaarer):
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert len(f["anslag"]) == 26
    rad = next(r for r in f["anslag"] if r["id"] == "2026-46-K2-PO2")
    assert rad["status"] == "åpen" and rad["utfall"] is None and rad["skaar"] is None
    assert rad["forseglet"] == "2026-11-10T20:00:00Z"
    assert rad["sha256"] == anslag.sha256(anslag.MASKIN_DIR / "2026-46.yml")
    assert rad["aapningsdato"] == "2026-12-28" and rad["po"] == "2"
    assert f["treffliste"]["K2"]["dom"].startswith("for tidlig")
    assert f["treffliste"]["K6"]["klasse"] == "PRØVETYPE"


def test_utfallet_fylles_inn_naar_dataene_er_kommet(skaarer):
    _utfallsukene()
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    k2 = next(r for r in f["anslag"] if r["id"] == "2026-46-K2-PO2")
    assert k2["status"] == "avgjort" and k2["utfall"] == 1
    assert k2["skaar"]["feil_a"] == abs(1 - k2["referanse_a"])
    k6 = next(r for r in f["anslag"] if r["id"] == "2026-46-K6-PO2")
    # Uten trening er det ingen sesongverdi: K6 har intet anslag og skåres ikke.
    assert k6["anslag"] is None and k6["status"] == "skåres ikke"
    t = f["treffliste"]["K2"]
    assert t["avgjorte_uker"] == 1 and t["avgjorte_rader"] == 13


def test_k6_med_faerre_enn_fem_lokaliteter_skaares_ikke(skaarer):
    _utfallsukene(n_k6=4)
    ut = skaar_anslag.utfallene(
        [(T, anslag.MASKIN_DIR / "2026-46.yml",
          {"po_kobling": "akvakultur 2026-11-02"})],
        anslag.kl.Kjoringslogg("prove", skaarer / "logg"))
    y, grunn = ut[(T, "K6", "2")]
    assert y is None and "færre enn 5" in grunn


def test_bare_forseglede_uker_teller(skaarer):
    sti = anslag.MASKIN_DIR / "2026-46.yml"
    # En ukefil uten stempel, og en som er endret etter stempelet.
    (anslag.MASKIN_DIR / "2026-47.yml").write_text(sti.read_text(encoding="utf-8"),
                                                    encoding="utf-8")
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert {r["uke"] for r in f["anslag"]} == {"2026-W46"}
    assert f["ikke_tellende"] == [{"fil": "predictions/maskin/2026-47.yml",
                                   "grunn": "ikke stemplet: ingen .ots"}]
    sti.write_text(sti.read_text(encoding="utf-8") + "# endret\n", encoding="utf-8")
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert f["anslag"] == []
    assert any("summen i 2026-46.yml.ots" in x["grunn"] for x in f["ikke_tellende"])


def test_et_stempel_etter_fristen_teller_ikke(skaarer):
    tsv = anslag.FORSEGLINGER
    tsv.write_text(tsv.read_text(encoding="utf-8").replace(
        "2026-11-10T20:00:00Z", "2026-11-16T00:00:00Z"), encoding="utf-8")
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert f["anslag"] == [] and "etter fristen" in f["ikke_tellende"][0]["grunn"]


def test_trefflista_merker_provetypen_og_holder_backtesten_adskilt(skaarer):
    assert skaar_anslag.main([]) == 0
    tekst = skaar_anslag.TREFFLISTE.read_text(encoding="utf-8")
    assert "## K6, snitt voksne hunnlus om fire uker — PRØVETYPE" in tekst
    forseglet, backtest = tekst.split("## BACKTEST")
    assert "Bare forseglede uker teller" in forseglet
    assert "1.3066" not in forseglet and "1.3066" in backtest
    assert _fasit()["backtest"]["merke"].startswith("BACKTEST")


def test_skaareren_gir_samme_filer_to_ganger(skaarer):
    _utfallsukene()
    assert skaar_anslag.main([]) == 0
    for_ = skaar_anslag.FASIT.read_bytes(), skaar_anslag.TREFFLISTE.read_bytes()
    assert skaar_anslag.main([]) == 0
    assert (skaar_anslag.FASIT.read_bytes(), skaar_anslag.TREFFLISTE.read_bytes()) == for_
