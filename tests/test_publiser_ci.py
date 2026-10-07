"""Publiseringen fra GitHub Actions — det som kan prøves uten å laste opp.

`publiser_ci.py` kaller stegene i `publiser.py`. Prøvene her gjelder det
som er NYTT: summen over byggemappa, sperren for nøklene som mangler, og
bokføringen som prøver pushen på nytt når origin har flyttet seg.
"""

import json
import subprocess
from pathlib import Path

import pytest

import publiser
import publiser_ci
from tests.test_publiser import _datarepo, _pa_origin


# ---- summen over byggemappa ------------------------------------------

def _mappe(rot: Path) -> Path:
    (rot / "lokalitet" / "1").mkdir(parents=True)
    (rot / "index.html").write_text("<p>forside</p>", encoding="utf-8")
    (rot / "lokalitet" / "1" / "index.html").write_text("<p>1</p>",
                                                         encoding="utf-8")
    (rot / "_headers").write_text("/*\n  X: y\n", encoding="utf-8")
    return rot


def test_summen_er_den_samme_for_de_samme_filene(tmp_path):
    """To kopier av samme mappe, skrevet i ulik rekkefølge og til ulik
    tid, er de samme filene. Summen skal ikke vite forskjell."""
    a = _mappe(tmp_path / "a")
    b = tmp_path / "b"
    (b / "lokalitet" / "1").mkdir(parents=True)
    for rel in ("_headers", "lokalitet/1/index.html", "index.html"):
        (b / rel).write_bytes((a / rel).read_bytes())
    assert publiser.mappesum(a) == publiser.mappesum(b)
    assert publiser.mappesum(a)[1:] == (3, sum(
        p.stat().st_size for p in a.rglob("*") if p.is_file()))


@pytest.mark.parametrize("endring", ["innhold", "navn", "ny fil", "borte"])
def test_summen_endres_av_hver_slags_endring(tmp_path, endring):
    """Innhold, navn, en fil til og en fil mindre. En sum over bare
    innholdet ville ikke sett at en fil flyttet seg."""
    m = _mappe(tmp_path / "m")
    for_ = publiser.mappesum(m)[0]
    if endring == "innhold":
        (m / "index.html").write_text("<p>forside!</p>", encoding="utf-8")
    elif endring == "navn":
        (m / "lokalitet" / "1").rename(m / "lokalitet" / "2")
    elif endring == "ny fil":
        (m / "robots.txt").write_text("", encoding="utf-8")
    else:
        (m / "_headers").unlink()
    assert publiser.mappesum(m)[0] != for_


# ---- nøklene -----------------------------------------------------------

@pytest.mark.parametrize("miljo,mangler", [
    ({}, ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"]),
    ({"CLOUDFLARE_API_TOKEN": "t"}, ["CLOUDFLARE_ACCOUNT_ID"]),
    ({"CLOUDFLARE_API_TOKEN": "  ", "CLOUDFLARE_ACCOUNT_ID": "a"},
     ["CLOUDFLARE_API_TOKEN"]),
])
def test_en_manglende_noekkel_navngis(miljo, mangler):
    """`${{ secrets.X }}` på en secret som ikke finnes blir TOM STRENG.
    Wrangler svarer da med en feil som ikke sier hvilken som mangler."""
    with pytest.raises(publiser.Stopp) as e:
        publiser_ci.krev_cloudflare(miljo)
    for navn in mangler:
        assert navn in str(e.value)
    for navn in set(publiser_ci.CLOUDFLARE) - set(mangler):
        assert navn not in str(e.value)


def test_begge_noekler_slipper_gjennom():
    publiser_ci.krev_cloudflare({"CLOUDFLARE_API_TOKEN": "t",
                                 "CLOUDFLARE_ACCOUNT_ID": "a"})


def test_ingen_opplasting_uten_noekler(tmp_path, monkeypatch):
    """Sperren står FØR wrangler kalles, ikke i feilmeldingen etterpå."""
    for n in publiser_ci.CLOUDFLARE:
        monkeypatch.delenv(n, raising=False)
    kalt = []
    monkeypatch.setattr(publiser, "kjor", lambda *a, **k: kalt.append(a))
    with pytest.raises(publiser.Stopp):
        publiser_ci.last_opp(tmp_path, "produksjon")
    assert kalt == []


def test_opplastingen_er_publisers_kommando(tmp_path, monkeypatch):
    """Versjonen og grenen sies ett sted. Se `publiser.WRANGLER`."""
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
    kalt = []
    monkeypatch.setattr(publiser, "kjor", lambda *a, **k: kalt.append(a))
    publiser_ci.last_opp(tmp_path, "forhandsvisning")
    publiser_ci.last_opp(tmp_path, "produksjon")
    assert kalt == [tuple(publiser.wranglerkommando(tmp_path, False)),
                    tuple(publiser.wranglerkommando(tmp_path, True))]
    assert kalt[0][-1] == publiser.FORHANDSGREN
    assert kalt[1][-1] == publiser.PRODUKSJONSGREN


def test_miljoet_maa_vaere_et_av_de_to():
    with pytest.raises(SystemExit):
        publiser_ci.main(["last-opp", ".", "--miljo", "prod"])


# ---- kvitteringen ------------------------------------------------------

def test_kvittering_uten_sum_stopper(tmp_path):
    k = tmp_path / "k.json"
    k.write_text(json.dumps({"kode_commit": "a", "data_commit": "b",
                             "uke": "2026-41", "sha256": ""}),
                 encoding="utf-8")
    with pytest.raises(publiser.Stopp, match="sha256"):
        publiser_ci.les_kvittering(k)


def test_oppsummeringen_baerer_summen_og_ukas_tall():
    k = {"kode_commit": "a" * 40, "data_commit": "b" * 40,
         "uke": "2026-41", "sha256": "c" * 64, "filer": 3, "byte": 1e6}
    tekst = publiser_ci.oppsummering(k, ["  uke 41, 2026", "  12 endringer"])
    assert "c" * 64 in tekst
    assert "  12 endringer" in tekst
    assert "a" * 40 in tekst and "b" * 40 in tekst


def test_byggkommandoen_navngir_ci_skriptet():
    kommando = publiser.byggkommando(av="publiser_ci.py bygg, steg 3")
    assert kommando[-2:] == ["--vakt-kjores-av",
                             "publiser_ci.py bygg, steg 3"]


# ---- bokføringen -------------------------------------------------------

@pytest.fixture
def datarepo(tmp_path, monkeypatch):
    arbeid = _datarepo(tmp_path)
    monkeypatch.setattr(publiser, "DATAREPO", arbeid)
    monkeypatch.setattr(publiser, "LOGG",
                        arbeid / "docs" / "publiseringslogg.tsv")
    return arbeid


def _kom_forst(datarepo: Path) -> None:
    """En annen workflow pusher til datarepoet mens vi bygger."""
    fremmed = datarepo.parent / "fremmed"
    subprocess.run(["git", "clone", str(datarepo.parent / "origin.git"),
                    str(fremmed)], check=True, capture_output=True)
    for n, v in (("user.email", "x@example.invalid"), ("user.name", "X")):
        subprocess.run(["git", "-C", str(fremmed), "config", n, v],
                       check=True, capture_output=True)
    (fremmed / "annet.txt").write_text("i veien\n", encoding="utf-8")
    for args in (["add", "-A"], ["commit", "-m", "kom først"],
                 ["push", "origin", "main"]):
        subprocess.run(["git", "-C", str(fremmed), *args],
                       check=True, capture_output=True)


K = {"kode_commit": "a" * 40, "data_commit": "b" * 40, "uke": "2026-41",
     "sha256": "c" * 64}


def test_avvist_push_proves_igjen_og_linja_havner_paa_origin(datarepo):
    """`publiser.bokfor()` gir opp her, fordi et menneske kan gjøre
    resten. I Actions gjør ingen det."""
    _kom_forst(datarepo)
    assert publiser_ci.logg(K, "forhandsvisning") == ""
    linjer = _pa_origin(datarepo).splitlines()
    assert len(linjer) == 2                    # overskrift + ÉN linje
    assert linjer[1].split("\t")[1:] == ["forhandsvisning", "a" * 40,
                                         "b" * 40, "2026-41"]


def test_ny_push_skriver_ikke_linja_to_ganger(datarepo):
    publiser_ci.logg(K, "produksjon")
    assert len(_pa_origin(datarepo).splitlines()) == 2
