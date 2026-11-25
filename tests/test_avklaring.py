"""Felt under avklaring med kilden: linja, feeden og ukas tall.

SD2, 25.11.2026. 44 lokaliteter mistet `har_samdrift` mellom
døgnhentingene 16.11 og 17.11.2026, uten ny versjon i registeret, og 29
av dem fikk `har_samlokalisering` i samme steg. Lista står i config.yml
(`nettsted.under_avklaring`), regelen i `vesentlighet`. Her prøves det
nettstedet gjør med den: linja på sidene, feeden uten radene, og — mot
portens bygg — uke 48 slik den faktisk ble.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import nettsted
import vesentlighet

AVKLARING = ({"kilde": "akvakultur", "felt": "har_samdrift",
              "fra": "2026-11-17", "til": None, "nr": 0,
              "skiftet_mellom": ["2026-11-16T13:50:01+00:00",
                                 "2026-11-17T14:41:49+00:00"]},
             {"kilde": "akvakultur", "felt": "har_samlokalisering",
              "fra": "2026-11-17", "til": None, "nr": 1})

I_RADEN = ("Kilden endret dette feltet for 44 lokaliteter i samme uke, "
           "uten ny versjon i registeret.")
LINJE = "Samdrift: " + I_RADEN
SPURT = "Vi har spurt Fiskeridirektoratet."


@pytest.fixture
def liste(monkeypatch):
    monkeypatch.setattr(vesentlighet, "avklaringer", lambda: AVKLARING)
    monkeypatch.setattr(nettsted, "_avklaringstall",
                        lambda: {(0, "2026-48"): 44, (1, "2026-48"): 29,
                                 (0, "2026-49"): 3})


def post(felt, dato="2026-11-23", kilde="akvakultur"):
    return {"kilde": kilde, "kildefelt": felt, "dato": dato}


def test_linja_er_heines_ord_med_feltet_foran(liste):
    assert nettsted.avklaringslinjer([post("har_samdrift")]) == [[LINJE, SPURT]]


def test_hvert_avsnitt_er_under_avsnittsgrensa(liste):
    for linje in nettsted.avklaringslinjer([post("har_samdrift"),
                                            post("har_samlokalisering")]):
        for avsnitt in linje:
            assert len(avsnitt) <= 110, avsnitt


def test_en_linje_per_felt_og_uke_i_listas_rekkefolge(liste):
    rader = [post("har_samlokalisering"), post("har_samdrift"),
             post("har_samdrift"), post("kapasitet"),
             post("har_samdrift", dato="2026-11-30")]
    alle = nettsted.avklaringslinjer(rader)
    # «Vi har spurt» står én gang, etter den siste.
    assert [len(l) for l in alle] == [1, 1, 2] and alle[-1][-1] == SPURT
    linjer = [l[0] for l in alle]
    assert linjer == [
        LINJE,
        "Samdrift: Kilden endret dette feltet for 3 lokaliteter i samme "
        "uke, uten ny versjon i registeret.",
        "Samlokalisering: Kilden endret dette feltet for 29 lokaliteter i "
        "samme uke, uten ny versjon i registeret."]


def test_i_raden_staar_linja_uten_feltnavn_og_med_spurt_rett_etter(liste):
    poster = nettsted._med_avklaring([post("har_samdrift"), post("kapasitet"),
                                      post("har_samlokalisering")])
    assert [p["avklaring"] for p in poster] == [
        [I_RADEN, SPURT], [],
        ["Kilden endret dette feltet for 29 lokaliteter i samme uke, uten ny "
         "versjon i registeret.", SPURT]]


def test_samtidig_bare_naar_skiftet_er_maalt_innen_ett_dogn(liste, monkeypatch):
    kort = (dict(AVKLARING[0], skiftet_mellom=["2026-11-16T13:50:01+00:00",
                                               "2026-11-17T12:00:00+00:00"]),)
    monkeypatch.setattr(vesentlighet, "avklaringer", lambda: kort)
    [[linje, _]] = nettsted.avklaringslinjer([post("har_samdrift")])
    assert "44 lokaliteter samtidig, uten ny versjon" in linje


def test_ingen_linje_utenfor_lista_eller_tidsrommet(liste):
    assert nettsted.avklaringslinjer([post("kapasitet"),
                                      post("har_samdrift", dato="2026-11-16"),
                                      post("har_samdrift", kilde="eierskap")]
                                     ) == []


def _hendelse(felt, eid, dato="2026-11-23"):
    return {"dato": dato, "kilde": "akvakultur", "kildefelt": felt,
            "felt": felt, "identitet": eid, "entity_id": eid,
            "etikett": felt, "fra": "ja", "til": "nei", "kommune": "",
            "po": "4", "gjelder": eid, "gjelder_url": f"/lokalitet/{eid}/",
            "gjelder_slag": "lokalitet"}


def test_feedene_har_ikke_radene_under_avklaring(liste, tmp_path):
    uker = [{"hendelser": [_hendelse("har_samdrift", "10303"),
                           _hendelse("kapasitet", "10303"),
                           _hendelse("har_samdrift", "10303",
                                     dato="2026-11-16")]}]
    felles = SimpleNamespace(akva={"10303": {"navn": "NAPPEHOLMANE"}},
                             po_navn={"4": "Nordhordland til Stadt"},
                             tillatelser_per_eier={})
    nettsted.skriv_feeder(tmp_path, felles, uker)
    for sti in ("endringer/feed.xml", "lokalitet/10303/feed.xml",
                "produksjonsomrade/4/feed.xml"):
        ider = re.findall(r"<id>[^<]*#([^<]*)</id>",
                          (tmp_path / sti).read_text(encoding="utf-8"))
        assert ider == ["2026-11-23/akvakultur/10303/kapasitet",
                        "2026-11-16/akvakultur/10303/har_samdrift"], sti


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "endringer" / "2026-48").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygg med uke 48")

# Fire av de 44, de samme som står som eksempler i e-posten til
# Fiskeridirektoratet (ukesvakta 24.11.2026, punkt 4.2).
BERORT = ("10303", "39657", "18936", "29376")
# 11665 fikk ny registerversjon i uke 48 (koordinater), og er ikke blant
# de 44 (ukesvakta 24.11.2026, punkt 3).
UTENFOR = "11665"


def _tekst(html: str) -> str:
    """Teksten slik avsnittsvakten leser den: tagger bort, mellomrom
    slått sammen."""
    return " ".join(re.sub(r"<[^>]+>", "", html).split())


def _les(*deler: str) -> str:
    return (NETTSTED.joinpath(*deler)).read_text(encoding="utf-8")


def _rader(html: str, tabell: str) -> list[str]:
    m = re.search(rf'<table id="{tabell}".*?</table>', html, re.S)
    return re.findall(r"<tr[^>]*>.*?</tr>", m.group(0), re.S) if m else []


def _felt_i(rader: list[str], felt: str) -> int:
    return sum(1 for r in rader if f'data-felt="{felt}"' in r)


@trenger_bygg
def test_uke_48_teller_ikke_skiftet_men_viser_det_blant_de_tekniske():
    side = _les("endringer", "2026-48", "index.html")
    hoved = _rader(side, "endringer-uke")
    tekniske = _rader(side, "endringer-uke-tekniske")
    assert hoved, "fant ikke hovedtabellen for uke 48"
    assert _felt_i(hoved, "har_samdrift") == 0
    assert _felt_i(hoved, "har_samlokalisering") == 0
    assert _felt_i(tekniske, "har_samdrift") == 44
    assert _felt_i(tekniske, "har_samlokalisering") == 29
    tekst = _tekst(side)
    assert LINJE in tekst and tekst.count(SPURT) == 1
    # I «Observert …»-linjas størrelse, ikke ingressens (Heine, SD2).
    for avsnitt in (LINJE, SPURT):
        assert re.search(rf'<p class="lok-undertittel">{re.escape(avsnitt)}</p>',
                         side), avsnitt
    assert "Samlokalisering: Kilden endret dette feltet for 29 lokaliteter" in tekst
    # OVERSKRIFTSTALLET ER RADENE I HOVEDTABELLEN, og de 73 er ikke blant
    # dem. Tallet leses av siden, ikke skrives inn her.
    m = re.search(r"(\d+) endringer? i uke 48, 2026\.", tekst)
    assert m, "fant ikke ukas tall på ukesiden"
    assert int(m.group(1)) < 73


@trenger_bygg
def test_forsiden_har_samme_tall_for_uke_48_som_ukesiden():
    uke = re.search(r"(\d+) endringer? i uke 48, 2026\.",
                    _tekst(_les("endringer", "2026-48", "index.html")))
    forside = _tekst(_les("index.html"))
    assert uke and f"{uke.group(1)} endringer observert i uke 48, 2026." in forside


@trenger_bygg
def test_ingen_feed_har_skiftet_fra_uke_48():
    feeder = list(NETTSTED.rglob("feed.xml"))
    assert len(feeder) > 1000, "fant ikke feedene"
    funn = [f for f in feeder
            if re.search(r"#2026-11-23/akvakultur/[^<]*/har_sam(drift|lokalisering)</id>",
                         f.read_text(encoding="utf-8"))]
    assert not funn, f"{len(funn)} feeder, f.eks. {funn[:3]}"


@trenger_bygg
@pytest.mark.parametrize("loknr", BERORT)
def test_en_berort_lokalitetsside_har_linja_og_kildens_verdi(loknr):
    side = _les("lokalitet", loknr, "index.html")
    # LINJA STÅR I RADEN DEN GJELDER, blant de tekniske, med «Vi har
    # spurt» rett etter — ikke over tidslinja (Heine, SD2).
    tidslinjer = "".join(re.findall(
        r'<ol class="tidsakse tidsakse--observert[^"]*">.*?</ol>', side, re.S))
    poster = re.findall(r"<li[^>]*>.*?</li>", tidslinjer, re.S)
    samdrift = [p for p in poster if 'data-felt="har_samdrift"' in p]
    assert len(samdrift) == 1, "fant ikke samdriftsraden"
    assert re.search(
        rf'<p class="tidsakse-avklaring">{re.escape(I_RADEN)}</p>\s*'
        rf'<p class="tidsakse-avklaring">{re.escape(SPURT)}</p>', samdrift[0])
    for p in poster:
        if p is not samdrift[0] and "har_samlokalisering" not in p:
            assert "tidsakse-avklaring" not in p, "linja står i en annen rad"
    # VERDIEN KILDEN OPPGIR, vises som før.
    assert re.search(r'<td data-felt="har_samdrift"[^>]*>\s*nei\s*<', side), \
        "faktaboksen viser ikke kildens verdi"
    # Endringen står blant de tekniske, ikke i den åpne tidslinja.
    apen = side.split('<ol class="tidsakse tidsakse--observert">', 1)[1]
    apen, tekniske = apen.split('class="tallboks tekniske-endringer"', 1)
    assert 'data-felt="har_samdrift"' not in apen
    assert 'data-felt="har_samdrift"' in tekniske


@trenger_bygg
def test_linja_staar_paa_de_44_og_ingen_andre_lokalitetssider():
    med = {f.parent.name for f in (NETTSTED / "lokalitet").glob("*/index.html")
           if "Kilden endret dette feltet" in f.read_text(encoding="utf-8")}
    assert len(med) == 44 and set(BERORT) <= med and UTENFOR not in med


@trenger_bygg
def test_en_lokalitet_utenfor_lista_er_uendret():
    """11665 fikk ny versjon i uke 48. Siden har ingen linje, og endringen
    er der den var: lista rører ikke en lokalitet som ikke står på den."""
    side = _les("lokalitet", UTENFOR, "index.html")
    assert "tidsakse-avklaring" not in side
    assert "Kilden endret dette feltet" not in _tekst(side)
    assert 'data-gjelder="2026-11-23"' in side
