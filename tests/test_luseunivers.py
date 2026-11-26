"""Lakselus i «Tilstanden nå» bare der BarentsWatch teller lus.

BarentsWatch teller lakselus på laksefisk i sjø. For et anlegg på land
eller en slaktemerd er «brakklagt» deres slutning om et anlegg som ikke
skal rapportere lus, ikke en påstand om fisken der (MALING-FUNN-OKTOBER
F4.2, «UNIVERS»). Regelen sto i `fisk_mot_lus()`, og tilstanden spurte
bare om `har_laksefisk`. Nå er den ÉN funksjon, `nettsted.i_luseunivers()`.

MÅLT 25.11.2026 på bygget av 32cfa52 (sluttkontrollen 15b, funn B):
295 lokaliteter som registeret sier ligger på land, viste «Lakselus:
brakklagt». Alle 295 var `er_landbasert` og uten lusrapport i uke 44
hos BarentsWatch, og 287 hadde aldri rapportert lus i 774 uker. Samme
regel tar 40 slaktemerder i sjø. Ingen lokalitet utenfor tellingen viste
et lusetall eller «ikke rapportert», så ingen tall forsvinner.

Nedlastingene bærer kildens verdi, urørt.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import csv
import io
import os
import re
from pathlib import Path

import pytest

import nettsted
from tests.test_nettsted import _uke_raa

LAND = {"er_landbasert": "True", "brakklagt": "True",
        "lus_er_rapportert": "False", "voksne_hunnlus": ""}
SLAKT = {"er_slaktemerd": "True", "brakklagt": "True",
         "lus_er_rapportert": "False", "voksne_hunnlus": ""}


def _lok(uke: dict) -> dict:
    """Det `lokalitetspaastander()` leser, og ikke mer."""
    return {"loknr": "10131", "navn": "DIRDAL", "kommune": "GJESDAL",
            "akva_dato": "2026-11-23", "eierskap_dato": "2026-11-23",
            "lus_serie": [uke], "lus_uker": 1, "lus_fra": uke["dato"],
            "lus_til": uke["dato"], "lus_uten_tall": 1,
            "lus_mangler_tekst": "", "lusetall_snapshots": 1,
            "biolag": {}, "selskap": {}, "tillatelser": [],
            "fisk_mot_lus": []}


@pytest.mark.parametrize("laksefisk, land, slakt, innenfor", [
    ("True", "False", "False", True),
    ("False", "False", "False", False),
    ("True", "True", "False", False),
    ("True", "False", "True", False),
    ("True", "", "False", False),       # et tomt flagg er ikke et nei
])
def test_regelen_er_kildens_tre_flagg(laksefisk, land, slakt, innenfor):
    uke = {"har_laksefisk": laksefisk, "er_landbasert": land,
           "er_slaktemerd": slakt}
    assert nettsted.i_luseunivers(uke) is innenfor


@pytest.mark.parametrize("utenfor", [LAND, SLAKT], ids=["land", "slaktemerd"])
def test_tilstanden_har_ingen_lakselus_utenfor_tellingen(utenfor):
    uke = _uke_raa(dato="2026-10-26", **utenfor)
    assert nettsted.lokalitetspaastander(_lok(uke))["lus"] is None


def test_brakklagt_i_sjo_star_som_for():
    uke = _uke_raa(dato="2026-10-26", brakklagt="True",
                   lus_er_rapportert="False", voksne_hunnlus="")
    lus = nettsted.lokalitetspaastander(_lok(uke))["lus"]
    assert lus["vist"] == "brakklagt" and lus["nivaa"] == "vurdert"


def test_tilstanden_og_samme_uke_spor_den_samme_regelen(monkeypatch):
    """Ett sted å endre: byttes regelen, følger begge leserne med."""
    uke = _uke_raa(dato="2026-10-26", **LAND)
    monkeypatch.setattr(nettsted, "i_luseunivers", lambda u: True)
    assert nettsted.lokalitetspaastander(_lok(uke))["lus"]["vist"] == "brakklagt"

    lok = dict(_lok(uke), biolag={"maaneder": [
        {"dato": "2026-10-31", "har_fisk": "Ja", "arter": "Laks"}]})
    lok["lus_serie"] = [dict(uke, dato="2026-10-26")]
    assert nettsted.fisk_mot_lus(lok)[0]["konflikt"] is True
    monkeypatch.setattr(nettsted, "i_luseunivers", lambda u: False)
    assert nettsted.fisk_mot_lus(lok)[0]["konflikt"] is False


def test_nedlastingen_har_kildens_brakklagt():
    uke = _uke_raa(dato="2026-10-26", **LAND)
    tekst = nettsted.csv_tekst(_lok(uke), ["Data levert av BarentsWatch"],
                               "2026-11-26")
    data = [l for l in tekst.splitlines() if not l.startswith("#")]
    rad = next(csv.DictReader(io.StringIO("\n".join(data))))
    assert rad["brakklagt"] == "True"


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file() or not (NETTSTED / "lokalitet").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygg med lokalitetssider")


@trenger_bygg
def test_ingen_lokalitet_paa_land_har_lakselus_i_tilstanden():
    """Registerets «på land» i undertittelen, og ingen lakselusrad.

    Målt mot registeret og ikke mot BarentsWatchs flagg, som ikke står på
    siden. MÅLT 25.11.2026 i uke 44: alle 399 lokaliteter på land som står
    hos BarentsWatch, var landbaserte der også. Sier de to kildene noe
    annet en dag, skal noen se på det.
    """
    funn = []
    sider = 0
    for fil in sorted((NETTSTED / "lokalitet").glob("*/index.html")):
        side = fil.read_text(encoding="utf-8")
        hode = side.split('id="tilstand-tittel"', 1)
        if len(hode) < 2 or not re.search(r"·\s*på land\s*·", hode[0]):
            continue
        sider += 1
        tilstand = hode[1].split("</section>", 1)[0]
        if "<dt>Lakselus</dt>" in tilstand:
            funn.append(fil.parent.name)
    assert sider, "fant ingen lokalitet på land"
    assert not funn, f"{len(funn)} på land med lakselus i tilstanden: {funn[:8]}"
