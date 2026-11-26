"""Standardens punkt 1: kilde, dato og bevis, per sidetype.

MÅLT 25.11.2026 på bygget av 32cfa52 (sluttkontrollen 15b, 4.1, målt på
nytt i økt R1a):

  - «Tiltaksgrense 0,5 og 0,2» sto med `data-kilde` og uten
    `data-gjelder` på 992 lokalitetssider, og uten kilde og dato i
    teksten.
  - Bevisblokka (dato, sha256, stempel per kilde) sto på 1 786
    lokalitetssider og 144 kommunesider, og på 0 av 485 selskapssider,
    0 av 14 områdesider og 0 av 168 ukesider.
  - Hver ukeside siterte NYESTE akvakultursnapshot: uke 35 og uke 48
    oppga den samme summen.

Blokka kommer nå fra én makro (`maler/bevis.html.j2`) og én funksjon
(`nettsted.bevis()`), med sidens egne kilder. Ukesidens bevis er ukas
egne snapshots, og siteringens sum er akvakulturraden i det.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import datetime as dt
import os
import re
from pathlib import Path

import pytest

import nettsted
import visningsord
from tests.test_nettsted import _side, _uker, datamappe  # noqa: F401


# ------------------------------------------------------------- bevis()

def test_uten_uke_er_beviset_det_nyeste(datamappe):  # noqa: F811
    assert [b["dato"] for b in nettsted.bevis(("akvakultur",))] == ["2026-09-14"]


def test_med_uke_er_beviset_ukas_eget(datamappe):  # noqa: F811
    # 2026-09-14 er mandag i uke 38. Onsdag samme uke finner det; uka
    # etter har ikke noe, og da står kilden ikke.
    assert [b["dato"] for b in nettsted.bevis(("akvakultur",), uke="2026-09-16")] \
        == ["2026-09-14"]
    assert nettsted.bevis(("akvakultur",), uke="2026-09-22") == []


def test_kilder_uten_en_kropp_staar_ikke(datamappe):  # noqa: F811
    assert [b["kilde"] for b in nettsted.bevis(("eierskap_historikk", "akvakultur"))] \
        == ["akvakultur"]


RAD_EKS = {"kilde": "eierskap", "navn": "Tillatelsesregisteret",
           "kort": "Fiskeridir.", "dato": "2026-09-14", "uke": False,
           "hentet": "2026-09-14", "sha256": "ab" * 32,
           "sha256_vist": nettsted._hash_vist("ab" * 32),
           "stempel": "komplett", "manifest": "2026-09-15"}


@pytest.mark.parametrize("lag", ["_selskap", "_po"])
def test_malen_viser_beviset_fra_samme_makro(lag):
    import tests.test_nettsted as tn
    side = getattr(tn, lag)(bevis=[RAD_EKS])
    blokk = BLOKK.search(side)
    assert blokk, "ingen bevisblokk"
    tekst = " ".join(re.sub(r"<[^>]+>", " ", blokk.group(1)).split())
    assert "Tillatelsesregisteret Fiskeridir. hentet 14.09.2026" in tekst
    assert "sha256 abababab" in tekst and "stemplet med OpenTimestamps 15.09.2026" in tekst
    assert 'data-kilde="eierskap" data-gjelder="2026-09-14"' in blokk.group(1)


def test_hver_kilde_et_bevis_kan_vise_har_et_navn():
    """Til 4b sto «enhetsregisteret» og «trafikklysvedtak» som navn i
    blokka på selskaps- og områdesidene: kilde-id-en, et internt ord."""
    kilder = (set(nettsted.BEVISKILDER) | set(nettsted.SELSKAPSKILDER)
              | set(nettsted.PO_KILDER) | set(nettsted.ENDRINGSKILDER)) \
        - nettsted.UTEN_EN_KROPP
    for k in sorted(kilder):
        assert visningsord.datasett(k) != k, k


def test_selskapenes_kilder_er_de_siden_oppgir():
    assert set(nettsted.SELSKAPSKILDER) - nettsted.UTEN_EN_KROPP == \
        {"akvakultur", "eierskap", "enhetsregisteret"}


# -------------------------------------------------------- tiltaksgrensen

def test_grensa_har_kilde_og_gjelder_dato_fra_siste_uke_med_grense():
    serie = _uker(0.1, 0.2, 0.3, grense=("0.5", "0.2", ""))
    h = nettsted.lusegraf(serie)["grense"]["herkomst"]
    assert h["kilde"] == "sjotemperatur" and h["kort"] == "BarentsWatch"
    assert h["gjelder"] == serie[1]["dato"], "siste uke MED grense"
    assert h["vist"] == "uke 3, 2020"   # 2020-01-13


def test_grensas_herkomst_rorer_ikke_grafens_tellinger():
    """Første utkast kalte grenseteksten `verdier`, navnet på ukenes
    lusetall i `lusegraf()`: «528 av 774 uker med tall» ble «774 av 774»
    på delbygget. Fanget av sammenligningen før commit."""
    serie = _uker(0.1, None, 0.0, 0.3, grense=("0.5",) * 4)
    g = nettsted.lusegraf(serie)
    assert (g["uker_med_tall"], g["uten_tall"], g["nuller"]) == (3, 1, 1)
    assert g["grense"]["verdier"] == "0,5"


def test_siden_merker_grensa_og_viser_kilde_og_dato():
    serie = _uker(0.1, 0.2, grense=("0.5", "0.2"))
    side = _side(lus_serie=serie, lusegraf=nettsted.lusegraf(serie))
    rad = re.search(r"<div([^>]*)><dt>Tiltaksgrense</dt><dd>(.*?)</dd></div>", side, re.S)
    assert rad, "fant ikke tiltaksgrensa"
    assert f'data-kilde="sjotemperatur" data-gjelder="{serie[1]["dato"]}"' in rad.group(1)
    tekst = " ".join(re.sub(r"<[^>]+>", " ", rad.group(2)).split())
    assert tekst == "0,5 og 0,2 BarentsWatch · uke 3, 2020"


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted")

BLOKK = re.compile(r'<details class="tallboks bevis" id="bevis">(.*?)</details>', re.S)
RAD = re.compile(r'<div data-kilde="([a-z_]+)" data-gjelder="([\d-]+)"[^>]*>(.*?)</div>', re.S)


def _rader(side: str) -> list[tuple[str, str, str]]:
    m = BLOKK.search(side)
    if not m:
        return []
    return [(k, d, " ".join(re.sub(r"<[^>]+>", " ", r).split()))
            for k, d, r in RAD.findall(m.group(1))]


def _sider(mappe: str, dybde: int = 1) -> list[Path]:
    rot = NETTSTED / mappe
    return sorted(rot.glob("/".join(["*"] * dybde) + "/index.html")) if rot.is_dir() else []


@trenger_bygg
def test_hver_tiltaksgrense_har_kilde_og_dato():
    sider, feil = 0, []
    for fil in _sider("lokalitet"):
        side = fil.read_text(encoding="utf-8")
        for attr, dd in re.findall(r"<div([^>]*)><dt>Tiltaksgrense</dt><dd>(.*?)</dd>", side, re.S):
            if "ikke oppgitt" in dd:
                continue
            sider += 1
            if 'data-kilde="sjotemperatur"' not in attr or "data-gjelder=" not in attr \
                    or 'class="herkomst">BarentsWatch' not in dd:
                feil.append(fil.parent.name)
    if not sider:
        pytest.skip("bygget har ingen lokalitetsside med tiltaksgrense")
    assert not feil, f"{len(feil)} av {sider}: {feil[:8]}"


@pytest.mark.parametrize("mappe", ["lokalitet", "selskap", "produksjonsomrade"])
@trenger_bygg
def test_sidetypen_har_bevis_med_sum(mappe):
    sider = _sider(mappe)
    if not sider:
        pytest.skip(f"bygget har ingen {mappe}-sider")
    uten = [f.parent.name for f in sider
            if not any("sha256" in r for _, _, r in _rader(f.read_text(encoding="utf-8")))]
    assert not uten, f"{len(uten)} av {len(sider)} uten bevis: {uten[:8]}"


@trenger_bygg
def test_bevisblokka_har_ingen_kilde_id():
    from core import registry
    idene = {k.name for k in registry.discover()}
    funn = []
    for fil in _sider("selskap") + _sider("produksjonsomrade") + _sider("lokalitet"):
        m = BLOKK.search(fil.read_text(encoding="utf-8"))
        for dt_ in re.findall(r"<dt>(.*?) <span", m.group(1) if m else "", re.S):
            if dt_.strip() in idene:
                funn.append((fil.relative_to(NETTSTED).as_posix(), dt_.strip()))
    assert not funn, f"{len(funn)}: {funn[:6]}"


@trenger_bygg
def test_ukesidene_har_ukas_eget_bevis_og_siterer_det():
    sider = [f for f in _sider("endringer") + _sider("endringer", 2)
             if re.fullmatch(r"\d{4}-\d{2}", f.relative_to(NETTSTED / "endringer").parts[0])]
    if not sider:
        pytest.skip("bygget har ingen ukesider")
    feil = []
    for fil in sider:
        side = fil.read_text(encoding="utf-8")
        aar, uke = map(int, fil.relative_to(NETTSTED / "endringer").parts[0].split("-"))
        mandag, sondag = dt.date.fromisocalendar(aar, uke, 1), dt.date.fromisocalendar(aar, uke, 7)
        rader = _rader(side)
        if not rader:
            feil.append((fil.relative_to(NETTSTED).as_posix(), "ingen bevis"))
            continue
        for kilde, dato, _ in rader:
            if not mandag <= dt.date.fromisoformat(dato) <= sondag:
                feil.append((fil.relative_to(NETTSTED).as_posix(), f"{kilde} {dato}"))
        akva = next((r for k, _, r in rader if k == "akvakultur"), "")
        sitert = re.search(r"sjekksum ([0-9a-f]{8})…([0-9a-f]{4})", side)
        summen = "".join(re.findall(r"[0-9a-f]{8}", akva.split("sha256", 1)[-1]))
        if not sitert or not summen.startswith(sitert.group(1)) \
                or not summen.endswith(sitert.group(2)):
            feil.append((fil.relative_to(NETTSTED).as_posix(), "siteringen er ikke ukas sum"))
    assert not feil, f"{len(feil)}: {feil[:6]}"
