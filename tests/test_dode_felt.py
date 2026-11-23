"""Et felt kilden sender, men ikke fyller, vises ikke som «nei».

`har_rensefisk` og `har_medikamentell_behandling` er døde hos
BarentsWatch fra datoene i `kilder.lusetall.dodt_fra` (config.yml,
docs/KILDE-LUSETALL.md «Datatap»). Regelen er ÉN, `paastand.dodt()`, og
den har to lesere: lusetabellen på lokalitetssidene
(`nettsted.til_visning()`) og tidsaksen (`tidsakse.levende_uker()`).

MÅLT 23.11.2026 på bygget av 2139c38, før regelen ble felles: 1 781
lokalitetssider viste «nei» i begge feltene, 91 702 celler for rensefisk
og 91 692 for medikamentell behandling, mens tidsaksen lot de samme ukene
stå tomme.

Nedlastingene bærer kildens verdi, urørt: BarentsWatch-vilkåret sier at
innholdet i data som leveres, ikke skal endres (docs/LISENSKJEDE.md).

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import csv
import html
import io
import os
import re
from pathlib import Path

import polars as pl
import pytest

import nettsted
import paastand
import tidsakse
from tests.test_nettsted import _side, _uke_raa

DODE = paastand.dodt_fra("lusetall")
MED, RENS = "har_medikamentell_behandling", "har_rensefisk"


def _uke(dato: str, **overstyr) -> dict:
    aar, uke, _ = __import__("datetime").date.fromisoformat(dato).isocalendar()
    return _uke_raa(dato=dato, iso_aar=str(aar), iso_uke=f"{uke:02d}", **overstyr)


def _dagen_for(dato: str) -> str:
    d = __import__("datetime").date.fromisoformat(dato)
    return (d - __import__("datetime").timedelta(days=7)).isoformat()


# ------------------------------------------------------------- regelen

def test_datoene_er_de_config_oppgir():
    """Prøvene under hviler på at begge feltene står i `dodt_fra`. Flyttes
    en dato, følger prøvene med; forsvinner et felt, sier denne fra."""
    assert set(DODE) == {MED, RENS}
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in DODE.values())


@pytest.mark.parametrize("felt", sorted(DODE))
def test_regelen_gjelder_fra_og_med_datoen(felt):
    fra = DODE[felt]
    assert paastand.dodt("lusetall", felt, fra)
    assert paastand.dodt("lusetall", felt, "2099-01-04")
    assert not paastand.dodt("lusetall", felt, _dagen_for(fra))
    # Et tidsstempel leses som datoen det bærer.
    assert paastand.dodt("lusetall", felt, fra + "T00:00:00+00:00")


def test_regelen_gjelder_bare_feltene_som_staar_der():
    assert not paastand.dodt("lusetall", "har_mekanisk_fjerning", "2099-01-04")
    assert not paastand.dodt("lusetall", "voksne_hunnlus", "2099-01-04")
    assert not paastand.dodt("sjotemperatur", RENS, "2099-01-04")


# ----------------------------------------------------------- lusetabellen

@pytest.mark.parametrize("felt", sorted(DODE))
@pytest.mark.parametrize("verdi", ["False", "True"])
def test_et_dodt_felt_er_strek_i_tabellen_uansett_verdi(felt, verdi):
    """Fra datoen står verken «ja» eller «nei». Den ene `True` i
    medikamentfeltet (2024-11-11) er et unntak, ikke liv (config.yml)."""
    vist = nettsted.til_visning([_uke(DODE[felt], **{felt: verdi})])[0]
    assert vist[felt] == nettsted.INGEN_VERDI


@pytest.mark.parametrize("felt", sorted(DODE))
def test_foer_datoen_staar_kildens_svar(felt):
    foer = _dagen_for(DODE[felt])
    assert nettsted.til_visning([_uke(foer, **{felt: "False"})])[0][felt] == "nei"
    assert nettsted.til_visning([_uke(foer, **{felt: "True"})])[0][felt] == "ja"


def test_de_levende_feltene_er_som_foer():
    vist = nettsted.til_visning([_uke("2026-08-10", har_mekanisk_fjerning="True")])[0]
    assert (vist["har_mekanisk_fjerning"], vist["har_laksefisk"],
            vist["brakklagt"], vist["lus_er_rapportert"]) == ("ja", "ja", "nei", "ja")


def test_visningen_roerer_ikke_raden():
    """CSV-en og nedlastingene skrives av den samme raden."""
    rad = _uke("2026-08-10")
    foer = dict(rad)
    nettsted.til_visning([rad])
    assert rad == foer and rad[RENS] == "False"


def test_noten_navngir_bare_kolonner_med_en_dod_rad():
    foer_begge = _uke(_dagen_for(min(DODE.values())))
    mellom = _uke(_dagen_for(max(DODE.values())))
    etter = _uke(max(DODE.values()))
    assert nettsted.dode_kolonner([foer_begge]) == []
    forst = min(DODE, key=DODE.get)
    assert [d["felt"] for d in nettsted.dode_kolonner([foer_begge, mellom])] == [forst]
    alle = nettsted.dode_kolonner([foer_begge, etter])
    # Tabellens rekkefølge, ikke datoenes.
    assert [d["felt"] for d in alle] == [f for f in nettsted.LUSEFELT if f in DODE]
    assert {d["felt"]: d["fra"] for d in alle} == DODE
    assert nettsted.dode_kolonner() == alle


def _avsnitt(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", markup)).split())


NOTE = re.compile(r"<p class=\"tabellnote\" data-dode-felt>(.*?)</p>", re.S)


def test_siden_sier_hvilke_kolonner_og_fra_naar():
    side = _side()
    note = NOTE.search(side)
    assert note, "tabellnoten om de døde feltene mangler"
    tekst = _avsnitt(note.group(1))
    for d in nettsted.dode_kolonner():
        assert f"{d['navn']} fra {d['fra']}" in tekst
        # Samme ord som kolonneoverskriften.
        assert f"<th scope=\"col\">{d['navn']}</th>" in side
        assert f'<time datetime="{d["fra"]}">' in note.group(1)
    assert "ikke fylt av kilden, vist som «–»" in tekst
    assert 'href="/om/#lesing-lus"' in note.group(1)
    assert len(tekst) <= 110, (len(tekst), tekst)


def test_cellene_paa_siden_er_strek():
    side = _side()
    for felt in DODE:
        celle = re.search(rf'<td data-felt="{felt}">(.*?)</td>', side, re.S)
        assert celle and celle.group(1).strip() == nettsted.INGEN_VERDI


def test_uten_dode_rader_staar_ingen_note():
    gammel = _uke(_dagen_for(min(DODE.values())))
    side = _side(lus_serie=[gammel], lus=nettsted.til_visning([gammel]),
                 lus_dode=nettsted.dode_kolonner([gammel]))
    assert not NOTE.search(side)
    for felt in DODE:
        assert re.search(rf'<td data-felt="{felt}">nei</td>', side)


# ---------------------------------------------------------- nedlastingene

def _lok(serie: list[dict]) -> dict:
    return {"loknr": "31397", "navn": "OTERNESET", "kommune": "HARSTAD",
            "lus_serie": serie, "lus_uker": len(serie),
            "lus_fra": serie[0]["dato"], "lus_til": serie[-1]["dato"],
            "lus_uten_tall": 0, "lus_mangler_tekst": "",
            "lusetall_snapshots": len(serie)}


def test_csv_en_baerer_kildens_verdi_og_sier_hva_den_ikke_betyr():
    serie = [_uke(_dagen_for(min(DODE.values()))), _uke("2026-08-10"),
             _uke("2026-08-17", **{MED: "True"})]
    tekst = nettsted.csv_tekst(_lok(serie), ["Data levert av BarentsWatch"],
                               "2026-11-23")
    data = [l for l in tekst.splitlines() if not l.startswith("#")]
    rader = list(csv.DictReader(io.StringIO("\n".join(data))))
    assert [r[RENS] for r in rader] == ["False", "False", "False"]
    assert [r[MED] for r in rader] == ["False", "False", "True"]
    hode = [l[2:] for l in tekst.splitlines() if l.startswith("# ")]
    linje = next(l for l in hode if "kilden fyller ikke feltet" in l)
    for felt, fra in DODE.items():
        assert f"{felt} fra {fra}" in linje
    assert any("Den står her som kilden sendte den." in l for l in hode)


def test_csv_en_uten_dode_uker_har_ingen_linje_om_dem():
    serie = [_uke(_dagen_for(min(DODE.values())))]
    tekst = nettsted.csv_tekst(_lok(serie), ["Data levert av BarentsWatch"],
                               "2026-11-23")
    assert "kilden fyller ikke feltet" not in tekst


def test_kolonnebeskrivelsene_har_datoen_fra_config_og_ingen_egen():
    """Til 23.11.2026 sto «siste uke kilden oppga sann», målt 01.09.2026:
    2024-11-11 for medikamentell behandling, der regelen er 2024-01-01."""
    per_navn = {k.navn: k for k in nettsted.LUSEKOLONNER}
    for felt, fra in DODE.items():
        tekst = per_navn[felt].forklaring
        assert f"Fra og med {fra} fyller ikke kilden feltet" in tekst
        assert "Den står her som kilden sendte den." in tekst
        assert re.findall(r"\d{4}-\d{2}-\d{2}", tekst) == [fra]
    assert "fyller ikke" not in per_navn["har_mekanisk_fjerning"].forklaring


def test_kildebeskrivelsen_i_jsonld_sier_det_samme():
    node = nettsted.kildenode("lusetall", nettsted.kildevilkaar())
    for felt, fra in DODE.items():
        assert f"{felt} (fra {fra})" in node["description"]
    andre = nettsted.kildenode("akvakultur", nettsted.kildevilkaar())
    assert "fyller ikke" not in andre["description"]


# ------------------------------------------------- de to veiene er én

def test_tidsaksen_og_tabellen_spoer_den_samme_regelen():
    """Samme uker, samme svar: ukene tidsaksen regner som døde, er ukene
    tabellen viser som strek. Fire uker rundt hver dato, med flagget
    `True` i alle, så R8s strekkregel ikke tar noen av dem."""
    dt = __import__("datetime")
    for felt, fra in DODE.items():
        d0 = dt.date.fromisoformat(fra)
        uker = [(d0 + dt.timedelta(days=7 * i)).isoformat() for i in range(-2, 2)]
        lus = pl.DataFrame({
            "mandag": uker, "entity_id": ["1"] * 4,
            "har_laksefisk": ["True"] * 4, "er_landbasert": ["False"] * 4,
            "er_slaktemerd": ["False"] * 4, felt: ["True"] * 4})
        lever = tidsakse.levende_uker(lus, felt, 13, DODE)
        vist = {u: nettsted.til_visning([_uke(u, **{felt: "True"})])[0][felt]
                for u in uker}
        assert lever == {u for u, v in vist.items() if v != nettsted.INGEN_VERDI}
        assert lever == set(uker[:2])


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "lokalitet").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted med /lokalitet/")

RAD = re.compile(r'<tr data-kilde="lusetall" data-gjelder="(\d{4}-\d{2}-\d{2})"'
                 r'[^>]*>(.*?)</tr>', re.S)


def _celle(rad: str, felt: str) -> str | None:
    m = re.search(rf'<td[^>]*data-felt="{felt}"[^>]*>(.*?)</td>', rad, re.S)
    return _avsnitt(m.group(1)) if m else None


@trenger_bygg
def test_ingen_bygget_side_viser_ja_eller_nei_i_et_dodt_felt():
    """Hver lokalitetsside, hver rad i lusetabellen: et felt i `dodt_fra`
    står ikke som «ja» eller «nei» fra datoen. Før datoen står kildens
    svar, og noten står når, og bare når, tabellen har en slik rad."""
    sider = sorted((NETTSTED / "lokalitet").glob("*/index.html"))
    assert len(sider) > 1000, "fant ikke lokalitetssidene"
    funn, rader_etter, note_feil = [], 0, []
    for fil in sider:
        side = fil.read_text(encoding="utf-8")
        dode_her = set()
        for dato, rad in RAD.findall(side):
            for felt in DODE:
                verdi = _celle(rad, felt)
                assert verdi is not None, f"{fil}: {felt} mangler i raden {dato}"
                if paastand.dodt("lusetall", felt, dato, DODE):
                    rader_etter += 1
                    dode_her.add(felt)
                    if verdi != nettsted.INGEN_VERDI:
                        funn.append((fil.parent.name, dato, felt, verdi))
        note = NOTE.search(side)
        nevnt = ({d["felt"] for d in nettsted.dode_kolonner()
                  if f"{d['navn']} fra {d['fra']}" in _avsnitt(note.group(1))}
                 if note else set())
        if nevnt != dode_her:
            note_feil.append((fil.parent.name, sorted(nevnt), sorted(dode_her)))
    assert rader_etter > 100_000, "fant ikke radene fra datoene"
    assert not funn, f"{len(funn)} celler, f.eks. {funn[:5]}"
    assert not note_feil, f"{len(note_feil)} sider, f.eks. {note_feil[:5]}"


@trenger_bygg
def test_om_siden_forklarer_de_dode_feltene_med_samme_datoer():
    om = (NETTSTED / "om" / "index.html").read_text(encoding="utf-8")
    bit = re.search(r'<p id="lesing-lus-dode">(.*?)</p>', om, re.S)
    assert bit, "/om/#lesing-lus sier ikke hvilke felt som er døde"
    tekst = _avsnitt(bit.group(1))
    for d in nettsted.dode_kolonner():
        assert f"{d['navn']} fra {d['fra']}" in tekst
    assert "Nedlastingene har verdien kilden sendte, uendret." in _avsnitt(om)


@trenger_bygg
def test_nedlastingene_i_bygget_har_kildens_verdi():
    """`lusetall.csv` på hver lokalitet har bare `True`, `False` eller tomt
    i de to kolonnene, aldri en strek, og minst én `False` fra datoen."""
    sett = {felt: set() for felt in DODE}
    usanne_etter = 0
    for fil in sorted((NETTSTED / "lokalitet").glob("*/lusetall.csv")):
        linjer = [l for l in fil.read_text(encoding="utf-8").splitlines()
                  if not l.startswith("#")]
        for r in csv.DictReader(io.StringIO("\n".join(linjer))):
            for felt in DODE:
                sett[felt].add(r[felt])
                usanne_etter += (r[felt] == "False"
                                 and paastand.dodt("lusetall", felt, r["dato"], DODE))
    for felt in DODE:
        assert sett[felt] <= {"True", "False", ""}, (felt, sett[felt])
    assert usanne_etter > 100_000
