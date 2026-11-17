"""Skåreren for maskinanslagene: skaar_anslag.py (økt 8, to steder fra økt 14a).

Utfallet, fasiten.json og trefflista. Snapshotene, ukefilene og stempelet
er de samme falske som i test_anslag.py: ingenting rører ekte data eller
nettet. Siste prøve leser de ekte mappene, når datarepoet står ved siden
av.
"""
import datetime as dt
import hashlib
import json
import shutil

import pytest

import anslag
import skaar_anslag
from tests.test_anslag import (NAA, OTS_HODE, T, _flytt_til_kodrepoet,  # noqa: F401
                               _grunnlag, _logg, _uke, ekte, isolert)

U45 = T - dt.timedelta(weeks=1)


def _fasit_i_tmp(monkeypatch) -> None:
    monkeypatch.setattr(skaar_anslag, "FASIT", anslag.MASKIN_DIR / "fasiten.json")
    monkeypatch.setattr(skaar_anslag, "TREFFLISTE", anslag.MASKIN_DIR / "treffliste.md")


@pytest.fixture
def skaarer(isolert, monkeypatch):  # noqa: F811
    _fasit_i_tmp(monkeypatch)
    _grunnlag()
    assert anslag.main(["--forsegl"], naa=NAA) == 0
    return isolert


@pytest.fixture
def to_steder(isolert, monkeypatch):  # noqa: F811
    """Uke 45 forseglet i kodrepoets mappe og uke 46 i datarepoets, slik
    uke 46–47 og uke 48 ligger i de ekte repoene."""
    _fasit_i_tmp(monkeypatch)
    _grunnlag()
    monkeypatch.setattr(anslag, "FORSTE_I_DATAREPOET", U45)
    assert anslag.main(["--forsegl"], naa=NAA - dt.timedelta(weeks=1)) == 0
    _flytt_til_kodrepoet("2026-45.yml")
    monkeypatch.setattr(anslag, "FORSTE_I_DATAREPOET", T)
    monkeypatch.setattr(anslag, "KODE_UKER", ("2026-45.yml",))
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
    assert (rad["repo"], rad["fil"]) == ("havbruk-radar-data", "predictions/maskin/2026-46.yml")
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
    assert f["ikke_tellende"] == [{"uke": "2026-W47", "repo": "havbruk-radar-data",
                                   "fil": "predictions/maskin/2026-47.yml",
                                   "grunn": "ikke stemplet: ingen .ots"}]
    sti.write_text(sti.read_text(encoding="utf-8") + "# endret\n", encoding="utf-8")
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert f["anslag"] == []
    assert any("summen i 2026-46.yml.ots" in x["grunn"] for x in f["ikke_tellende"])


def test_et_stempel_etter_fristen_teller_ikke(skaarer):
    tsv = _logg()
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


# ------------------------------------------------------ to steder, én fasit

def _ukene(f: dict) -> dict[str, set[str]]:
    """{uke: repoene radene oppgir}."""
    ut: dict[str, set[str]] = {}
    for r in f["anslag"]:
        ut.setdefault(r["uke"], set()).add(r["repo"])
    return ut


def test_fasiten_dekker_ukene_begge_steder(to_steder):
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert len(f["anslag"]) == 52 and not f["ikke_tellende"]
    assert _ukene(f) == {"2026-W45": {"havbruk-radar"}, "2026-W46": {"havbruk-radar-data"}}
    assert f["treffliste"]["K2"]["forseglede_uker"] == 2
    tekst = skaar_anslag.TREFFLISTE.read_text(encoding="utf-8")
    assert "| 2026-W45 |" in tekst and "| 2026-W46 |" in tekst
    # Ett sted: fasiten og trefflista ligger i datarepoets mappe, ikke i kodrepoets.
    assert sorted(p.name for p in anslag.KODE_MASKIN.iterdir()) == [
        "2026-45.yml", "2026-45.yml.ots", "forseglinger.tsv"]


def _stoppet(capsys, ord: str) -> None:
    """Skåreren nekter, sier hvorfor, og rører ikke fasiten."""
    for_ = skaar_anslag.FASIT.read_bytes() if skaar_anslag.FASIT.exists() else None
    assert skaar_anslag.main([]) == 2
    ut = capsys.readouterr().out
    assert ord in ut and "ikke skrevet" in ut, ut
    assert (skaar_anslag.FASIT.read_bytes() if skaar_anslag.FASIT.exists() else None) == for_


def test_en_uke_begge_steder_stopper_skaareren(to_steder, capsys):
    for n in ("2026-46.yml", "2026-46.yml.ots"):
        shutil.copy(anslag.MASKIN_DIR / n, anslag.KODE_MASKIN / n)
    _stoppet(capsys, "predictions/maskin/2026-46.yml finnes begge steder")


def test_en_uke_i_feil_repo_stopper_skaareren(to_steder, capsys):
    for n in ("2026-46.yml", "2026-46.yml.ots"):
        (anslag.MASKIN_DIR / n).rename(anslag.KODE_MASKIN / n)
    _stoppet(capsys, "2026-W46 hører hjemme i havbruk-radar-data")


def test_en_uke_som_mangler_i_kodrepoet_stopper_skaareren(to_steder, capsys):
    """Mappa som ikke ble lest: kodrepoets uker er faste, og en fasit uten
    dem er en fasit som stille ble kortere."""
    assert skaar_anslag.main([]) == 0
    (anslag.KODE_MASKIN / "2026-45.yml").unlink()
    _stoppet(capsys, "predictions/maskin/2026-45.yml mangler i havbruk-radar")


def test_en_uke_som_forsvinner_stopper_skaareren(to_steder, capsys):
    """En uke som sto i fasiten, står der neste gang også."""
    assert skaar_anslag.main([]) == 0
    for n in ("2026-46.yml", "2026-46.yml.ots"):
        (anslag.MASKIN_DIR / n).unlink()
    capsys.readouterr()
    _stoppet(capsys, "2026-W46 står i fasiten.json fra før")


def test_en_uke_som_slutter_aa_telle_forsvinner_ikke(to_steder):
    """Den flytter seg til ikke_tellende, og det er ikke å mangle."""
    assert skaar_anslag.main([]) == 0
    (anslag.MASKIN_DIR / "2026-46.yml.ots").unlink()
    assert skaar_anslag.main([]) == 0
    f = _fasit()
    assert set(_ukene(f)) == {"2026-W45"}
    assert [x["uke"] for x in f["ikke_tellende"]] == ["2026-W46"]


def _komplett(sti, sum_hex: str, attestasjon: bytes) -> None:
    (sti.parent / f"{sti.name}.komplett.ots").write_bytes(
        OTS_HODE + b"\x01\x08" + bytes.fromhex(sum_hex) + attestasjon)


# En attestasjon er 0x00, åtte byte merke, lengde og innhold. Bitcoin bærer
# blokkhøyden (975346 som varuint); en kalender som venter, bærer adressen sin.
BITCOIN = b"\x00" + bytes.fromhex("0588960d73d71901") + b"\x03\xf2\xc3\x3b"
VENTER = b"\x00" + bytes.fromhex("83dfe30d2ef90c8e") + b"\x04\x03abc"


def test_komplett_krever_riktig_sum_og_en_blokk(skaarer, capsys):
    """Fram til økt 14a var det nok at en fil het .komplett.ots."""
    sti = anslag.MASKIN_DIR / "2026-46.yml"
    sha = anslag.sha256(sti)

    def komplett() -> bool:
        assert skaar_anslag.main([]) == 0
        return _fasit()["anslag"][0]["stempel_komplett"]

    assert komplett() is False
    _komplett(sti, hashlib.sha256(b"en annen fil").hexdigest(), BITCOIN)
    assert komplett() is False
    assert "er stemplet for en annen sum" in capsys.readouterr().out
    _komplett(sti, sha, VENTER)
    assert komplett() is False
    assert "bærer ingen Bitcoin-blokk" in capsys.readouterr().out
    _komplett(sti, sha, BITCOIN)
    assert komplett() is True
    assert "::warning::" not in capsys.readouterr().out


def test_oppgraderingen_skriver_bare_i_datarepoets_mappe(to_steder, monkeypatch):
    """Jobben kan ikke committe i kodrepoet, så en .komplett.ots skrevet
    der ville blitt borte med runneren, og forsøkt på nytt hver uke."""
    sett = []
    monkeypatch.setattr(skaar_anslag.stempel, "oppgrader",
                        lambda ots: sett.append(ots) or False)
    assert skaar_anslag.main(["--oppgrader"]) == 0
    assert sett == [anslag.MASKIN_DIR / "2026-46.yml.ots"]


def test_fasiten_i_datarepoet_har_hver_uke_fra_begge_repoene(ekte):  # noqa: F811
    """Mot de ekte mappene. Fasiten i datarepoet skal føre hver uke som
    har en ukefil, de to i kodrepoet medregnet, og hver rad skal peke på en
    fil som finnes i repoet den oppgir. Uten datarepoet ved siden av
    (kodrepoets Actions) er det ingenting å holde den mot."""
    if not ekte:
        pytest.skip("datarepoet står ikke ved siden av kodrepoet")
    fasit = anslag.MASKIN_DIR / "fasiten.json"
    assert fasit.exists(), f"{fasit} mangler: kjør skaar_anslag.py og commit den i datarepoet"
    f = json.loads(fasit.read_text(encoding="utf-8"))
    uker = {anslag.isouke(U) for U, _ in skaar_anslag.ukefiler()}
    assert {"2026-W46", "2026-W47"} <= uker
    assert skaar_anslag.uker_i(f) == uker
    mappe = {anslag.KODEREPO: anslag.KODE_MASKIN, anslag.DATAREPO: anslag.MASKIN_DIR}
    for rad in f["anslag"] + f["ikke_tellende"]:
        navn = rad["fil"].removeprefix(f"{anslag.STI}/")
        assert (mappe[rad["repo"]] / navn).exists(), (rad["repo"], rad["fil"])
        assert anslag.mappe(anslag.uke_fra_filnavn(navn)) == mappe[rad["repo"]]
