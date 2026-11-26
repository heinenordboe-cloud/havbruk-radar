"""Uker over tiltaksgrensen per produksjonsperiode: hva tallet teller.

«0 av 28 uker med lusetall» ble lest som at lusetallene manglet
(sluttkontrollen 15b, funn C). MÅLT 25.11.2026 på bygget av 32cfa52: det
første tallet er uker OVER grensa, det andre uker med et lusetall i
perioden, og det andre er aldri 0. 600 sider hadde en inneværende periode
(kontrollens 588 talte ikke «1 uke») og 989 en forrige. Etiketten sier nå
«0 av 28 målte uker over grensa».

Skal anlegget ikke rapportere, står tellingen ikke: en periode telles
bare når BarentsWatch teller lus i minst én av ukene
(`nettsted.i_luseunivers()`, samme regel som tilstanden). 12 sider
mistet tellingen, alle med en forrige periode på én til fem uker helt
utenfor tellingen; 988 fikk bare den nye ordlyden.

Den siste prøven trenger et bygget nettsted (`HAVBRUK_NETTSTED`).
"""
import os
import re
from pathlib import Path

import pytest

import nettsted
from tests.test_nettsted import _side, _uker

LAND = {"er_landbasert": "True"}


def _pp(serie):
    return nettsted.produksjonsperioder(serie, serie[-1]["dato"])


def test_etiketten_sier_at_tallet_er_uker_over_grensa():
    serie = _uker(0.1, 0.2, 0.6, grense=("0.5",) * 3)
    tekst = " ".join(_side(lus_serie=serie, lusegraf=nettsted.lusegraf(serie)).split())
    assert "1 av 3 målte uker over grensa" in tekst
    assert "med lusetall" not in tekst.split("Uker over tiltaksgrensen", 1)[1][:400]


def test_entall():
    serie = _uker(0.1, grense=("0.5",))
    tekst = " ".join(_side(lus_serie=serie, lusegraf=nettsted.lusegraf(serie)).split())
    assert "0 av 1 målt uke over grensa" in tekst


def test_en_periode_utenfor_tellingen_telles_ikke():
    """Et anlegg på land med tall i noen uker: BarentsWatch teller ikke lus
    der, og siden teller ikke uker over grensa der."""
    serie = _uker(0.1, 0.7, 0.2, grense=("0.5",) * 3)
    for u in serie:
        u.update(LAND)
    assert _pp(serie) == {"innevaerende": None, "forrige": None}
    tekst = " ".join(_side(lus_serie=serie, lusegraf=nettsted.lusegraf(serie)).split())
    assert "Uker over tiltaksgrensen" not in tekst


def test_en_periode_i_sjo_for_anlegget_kom_paa_land_telles():
    serie = _uker(0.6, 0.1, None, None, brakk={2, 3}, grense=("0.5",) * 4)
    serie[3].update(LAND)
    pp = _pp(serie)
    assert pp["innevaerende"] is None
    assert pp["forrige"]["uker"] == 2 and pp["forrige"]["over"] == 1


def test_en_blandet_periode_telles_helt():
    """Som 45018: 83 uker i sjø, én av dem uten laksefisk."""
    serie = _uker(0.6, 0.1, 0.2, grense=("0.5",) * 3)
    serie[1]["har_laksefisk"] = "False"
    pp = _pp(serie)
    assert pp["innevaerende"]["uker"] == 3 and pp["innevaerende"]["med_tall"] == 3


def test_en_periode_utenfor_tar_ikke_plassen_som_forrige():
    """Sjø, brakk, én uke på land med tall, brakk, sjø nå: forrige
    produksjonsperiode er den i sjø, ikke uka på land."""
    serie = _uker(0.6, None, 0.9, None, 0.1, brakk={1, 3},
                  grense=("0.5",) * 5)
    serie[2].update(LAND)
    pp = _pp(serie)
    assert pp["innevaerende"]["fra"] == serie[4]["dato"]
    assert pp["forrige"]["fra"] == serie[0]["dato"]
    assert pp["forrige"]["over"] == 1


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file() or not (NETTSTED / "lokalitet").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygg med lokalitetssider")

PERIODE = re.compile(r"<dt>(?:Inneværende|Forrige) produksjonsperiode</dt>\s*<dd>(.*?)</dd>", re.S)


@trenger_bygg
def test_hver_telling_sier_at_den_teller_uker_over_grensa():
    tellinger, feil = 0, []
    for fil in sorted((NETTSTED / "lokalitet").glob("*/index.html")):
        for dd in PERIODE.findall(fil.read_text(encoding="utf-8")):
            tekst = " ".join(re.sub(r"<[^>]+>", " ", dd).split())
            if tekst.startswith("ingen:"):
                continue
            tellinger += 1
            if not re.match(r"\d+ av \d+ målte? uker? over grensa", tekst) \
                    or "med lusetall" in tekst:
                feil.append((fil.parent.name, tekst[:60]))
    assert tellinger, "fant ingen periodetelling"
    assert not feil, f"{len(feil)} tellinger: {feil[:6]}"
