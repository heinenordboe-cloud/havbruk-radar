"""«Lokaliteter med tillatelse», delt i bare egne og delt med andre.

Til 23.11.2026 sto «lokaliteter nå» på selskapssiden og «Lokaliteter» i
selskapsindeksen om hver lokalitet med en aktiv kobling til en av
selskapets tillatelser, også der andre innehavere har resten.

MÅLT 23.11.2026 (eierskap og akvakultur 16.11.2026): 173 av 480 selskaper
har minst én lokalitet der et annet organisasjonsnummer også har
tillatelse. Hos dem gjelder det 1 307 av 2 000 lokaliteter (65,3 %); over
alle 480 er det 1 307 av 2 560 (51,1 %). Tre lokaliteter har en tillatelse
uten oppgitt innehaver, og er verken «bare egne» eller «delt med andre».

Tallet og ordene står ett sted, `nettsted.selskapets_lokaliteter()`,
`LOKALITETER_ORD` og `DELING_ORD`, og selskapssiden, indeksen,
JSON-LD-beskrivelsen, søket og margen med kartet leser dem derfra.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import html
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import nettsted
from tests.test_nettsted import _grunn, _selskap

A, B = "912345678", "923456789"


def _felles(**overstyr):
    """Selskap A med fire lokaliteter: én alene, én delt med B, én med en
    tillatelse registeret oppgir uten innehaver, og én som ikke står i
    Akvakulturregisteret."""
    eierskap = {
        "A-1": {"eier_orgnr": A, "eier_navn": "TESTLAKS AS",
                "eier_type": "LimitedLiabilityCompany",
                "lokaliteter": "10001; 10002; 10003; 99999"},
        "A-2": {"eier_orgnr": A, "eier_navn": "TESTLAKS AS",
                "eier_type": "LimitedLiabilityCompany", "lokaliteter": "10002"},
        "B-1": {"eier_orgnr": B, "eier_navn": "ANDRE AS",
                "eier_type": "LimitedLiabilityCompany", "lokaliteter": "10002"},
        "B-2": {"eier_orgnr": B, "eier_navn": "ANDRE AS",
                "eier_type": "LimitedLiabilityCompany", "lokaliteter": "10002"},
        "B-3": {"eier_orgnr": B, "eier_navn": "ANDRE AS",
                "eier_type": "LimitedLiabilityCompany", "lokaliteter": "10004"},
    }
    akva = {"10001": {"navn": "ALENE", "tillatelser": "A-1"},
            "10002": {"navn": "DELT", "tillatelser": "A-1; A-2; B-1; B-2"},
            "10003": {"navn": "UAVKLART", "tillatelser": "A-1; X-9"},
            "10004": {"navn": "BARE B", "tillatelser": "B-3"}}
    felt = dict(
        eierskap=eierskap, akva=akva,
        tillatelser_per_eier={A: ["A-1", "A-2"], B: ["B-1", "B-2", "B-3"]},
        enhet={A: {}}, eierskap_dato="2026-11-16", akva_dato="2026-11-16",
        dekning_fra=[], registerendringer={})
    felt.update(overstyr)
    return SimpleNamespace(**felt)


# ------------------------------------------------------------ funksjonen

def test_lokalitetene_deles_i_tre_og_summerer_til_tallet():
    d = nettsted.selskapets_lokaliteter(A, _felles())
    assert (d["antall"], d["egne"], d["delt"], d["uavklart"]) == (3, 1, 1, 1)
    assert d["egne"] + d["delt"] + d["uavklart"] == d["antall"] == len(d["per"])
    assert list(d["per"]) == ["10001", "10002", "10003"]
    assert {k: v["slag"] for k, v in d["per"].items()} == {
        "10001": "egne", "10002": "delt", "10003": "uavklart"}


def test_hver_lokalitet_sier_hvor_mange_av_tillatelsene_som_er_selskapets():
    per = nettsted.selskapets_lokaliteter(A, _felles())["per"]
    assert (per["10002"]["egne"], per["10002"]["andre"], per["10002"]["alle"]) == (2, 2, 4)
    assert (per["10001"]["egne"], per["10001"]["alle"]) == (1, 1)
    # Tillatelsen registeret oppgir uten innehaver, telles med i «alle».
    assert (per["10003"]["egne"], per["10003"]["uten"], per["10003"]["alle"]) == (1, 1, 2)


def test_den_andre_innehaveren_ser_den_samme_lokaliteten_som_delt():
    d = nettsted.selskapets_lokaliteter(B, _felles())
    assert (d["antall"], d["egne"], d["delt"], d["uavklart"]) == (2, 1, 1, 0)
    assert d["per"]["10002"]["slag"] == "delt"


def test_en_lokalitet_utenfor_registeret_telles_ikke():
    """Lokalitetslista kan ikke vise en lokalitet Akvakulturregisteret ikke
    har, og tallet teller det lista viser."""
    assert "99999" not in nettsted.selskapets_lokaliteter(A, _felles())["per"]


def test_et_selskap_uten_tillatelser_har_ingen_lokaliteter():
    d = nettsted.selskapets_lokaliteter("999999999", _felles())
    assert (d["antall"], d["egne"], d["delt"], d["uavklart"], d["per"]) == (0, 0, 0, 0, {})


def test_delingen_staar_med_null_men_uavklart_bare_naar_den_finnes():
    assert nettsted.deling_vist({"egne": 2, "delt": 18, "uavklart": 0}) == \
        "2 bare egne · 18 delt med andre"
    assert nettsted.deling_vist({"egne": 5, "delt": 0, "uavklart": 0}) == \
        "5 bare egne · 0 delt med andre"
    assert nettsted.deling_vist({"egne": 0, "delt": 1, "uavklart": 3}) == \
        "0 bare egne · 1 delt med andre · 3 med tillatelse uten oppgitt innehaver"
    assert nettsted.deling_vist({"egne": 2, "delt": 18, "uavklart": 0},
                                skille=", ") == "2 bare egne, 18 delt med andre"
    assert nettsted.deling_vist({"egne": 2, "delt": 18, "uavklart": 0},
                                lange=True) == \
        "2 med bare egne tillatelser · 18 delt med andre innehavere"


# ---------------------------------------------- de fire stedene, samme tall

def test_indeksen_og_selskapssiden_teller_med_samme_funksjon():
    felles = _felles()
    rader = {r["orgnr"]: r for r in nettsted.bygg_selskapsindeks(felles)["rader"]}
    for orgnr in (A, B):
        d = nettsted.selskapets_lokaliteter(orgnr, felles)
        r = rader[orgnr]
        assert (r["lokaliteter"], r["egne"], r["delt"], r["uavklart"]) == (
            d["antall"], d["egne"], d["delt"], d["uavklart"])


def _avsnitt(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", markup)).split())


def test_indeksen_har_kolonnene_med_selskapssidens_ord():
    d = nettsted.bygg_selskapsindeks(_felles())
    side = nettsted._miljo().get_template("indeks-selskap.html.j2").render(
        d=d, **_grunn("lokalitet"))
    hode = re.findall(r'<th scope="col">(.*?)</th>', side, re.S)
    assert hode == ["Organisasjonsnummer", "Navn", "Tillatelser",
                    "Lokaliteter med tillatelse", "Bare egne", "Delt med andre",
                    "Registerdata"]
    rad = re.search(rf'<a href="/selskap/{A}/">.*?</tr>', side, re.S).group(0)
    celler = dict(re.findall(r'data-felt="(lokaliteter_\w+)">([^<]*)<', rad))
    assert celler == {"lokaliteter_antall": "3", "lokaliteter_egne": "1",
                      "lokaliteter_delt": "1"}
    flat = _avsnitt(side)
    assert "Der de to ikke summerer til tallet foran" in flat
    assert "Flest lokaliteter med tillatelse" in flat
    assert '<th scope="col">Lokaliteter</th>' not in side


def test_noten_om_summen_staar_bare_der_den_trengs():
    felles = _felles()
    felles.akva["10003"]["tillatelser"] = "A-1"
    side = nettsted._miljo().get_template("indeks-selskap.html.j2").render(
        d=nettsted.bygg_selskapsindeks(felles), **_grunn("lokalitet"))
    assert "Der de to ikke summerer" not in _avsnitt(side)


def _nokkeltall(side: str) -> dict:
    rute = re.search(r'<div class="nokkeltall-lokaliteter">(.*?)</div>', side, re.S).group(1)
    return {"tall": re.search(r'data-felt="lokaliteter_antall">([^<]*)<', rute).group(1),
            "etikett": _avsnitt(re.search(r"<dt>(.*?)</dt>", rute, re.S).group(1)),
            "deling": _avsnitt(re.search(
                r'class="nokkeltall-del"[^>]*>(.*?)</dd>', rute, re.S).group(1))}


def test_selskapssiden_sier_hva_tallet_er_og_deler_det():
    side = _selskap(lokaliteter_antall=20,
                    lokaliteter_deling={"egne": 2, "delt": 18, "uavklart": 0})
    assert _nokkeltall(side) == {
        "tall": "20", "etikett": "lokaliteter med tillatelse nå",
        "deling": "2 bare egne · 18 delt med andre"}
    assert "lokaliteter nå" not in _avsnitt(side)
    # Entall, og den tredje gruppa bare når den finnes.
    en = _nokkeltall(_selskap())
    assert (en["tall"], en["etikett"]) == ("1", "lokalitet med tillatelse nå")
    tre = _selskap(lokaliteter_antall=4,
                   lokaliteter_deling={"egne": 0, "delt": 1, "uavklart": 3})
    assert _nokkeltall(tre)["deling"].endswith(
        "3 med tillatelse uten oppgitt innehaver")


def test_margen_og_lista_paa_selskapssiden_har_samme_tall_og_ord():
    side = _selskap(lokaliteter_antall=20,
                    lokaliteter_deling={"egne": 2, "delt": 18, "uavklart": 0})
    delinger = [_avsnitt(m) for m in re.findall(
        r'data-felt="lokaliteter_deling">(.*?)</(?:dd|p)>', side, re.S)]
    # Nøkkeltallene, margen med kartet og lokalitetslista.
    assert delinger == ["2 bare egne · 18 delt med andre"] * 3
    assert "av 20 lokaliteter med tillatelse er tegnet" in _avsnitt(side)


def test_lokalitetslista_sier_egne_tillatelser_av_alle():
    rad = {"loknr": "10002", "navn": "Delt", "original": "DELT",
           "kommune": "BODØ", "po_kode": "8", "po_navn": "Helgeland til Bodø",
           "status": "gul", "status_klasse": "lys-gul", "kapasitet": "780 tonn",
           "siden": "", "tillatelser": ["A-1"], "egne_tillatelser": 1,
           "alle_tillatelser": 5, "delt_slag": "delt"}
    side = _selskap(lokaliteter=[rad])
    assert '<tr data-deling="delt">' in side
    assert re.search(r'<td data-felt="egne_tillatelser">1 av 5</td>', side)
    assert '<th scope="col">Egne tillatelser</th>' in side


def test_jsonld_beskrivelsen_har_tallet_og_delingen():
    sel = {"orgnr": A, "navn": "TESTLAKS AS", "eierskap_dato": "2026-11-16",
           "lokaliteter_antall": 20,
           "lokaliteter_deling": {"egne": 2, "delt": 18, "uavklart": 0}}
    data = json.loads(str(nettsted.jsonld_selskap(sel, nettsted.kildevilkaar())))
    assert data["description"].endswith(
        "20 lokaliteter med tillatelse: 2 bare egne, 18 delt med andre.")
    assert "hvilke 20 lokaliteter de ligger på" not in data["description"]


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "selskap").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted med /selskap/")

DELING = re.compile(r"^(\d[\d\s]*) bare egne · (\d[\d\s]*) delt med andre"
                    r"(?: · (\d[\d\s]*) med tillatelse uten oppgitt innehaver)?$")


def _heltall(tekst: str) -> int:
    return int("".join(tekst.split()))


def _indeksrader() -> dict[str, dict[str, int]]:
    rader: dict[str, dict[str, int]] = {}
    sider = [NETTSTED / "selskap" / "index.html",
             *sorted((NETTSTED / "selskap" / "side").glob("*/index.html"))]
    for fil in sider:
        side = fil.read_text(encoding="utf-8")
        assert "Lokaliteter med tillatelse</th>" in side, fil
        for orgnr, rad in re.findall(
                r'<th scope="row"><a href="/selskap/(\d{9})/">.*?</th>(.*?)</tr>',
                side, re.S):
            rader[orgnr] = {k: _heltall(html.unescape(v)) for k, v in re.findall(
                r'data-felt="(lokaliteter_\w+)"[^>]*>([^<]*)<', rad)}
    return rader


@trenger_bygg
def test_hver_selskapsside_har_samme_tall_og_ord_som_indeksen_jsonld_og_margen():
    """Fire steder, ett tall: nøkkeltallene, raden i selskapsindeksen,
    JSON-LD-beskrivelsen og margen med kartet. Og tallet er antall rader i
    lokalitetslista, delt slik radene selv er merket."""
    indeks = _indeksrader()
    sider = sorted(p for p in (NETTSTED / "selskap").glob("*/index.html")
                   if p.parent.name.isdigit())
    assert len(sider) > 400 and len(indeks) == len(sider)
    feil, med_delt, delt_i_alt, lok_i_alt = [], 0, 0, 0
    for fil in sider:
        orgnr = fil.parent.name
        side = fil.read_text(encoding="utf-8")
        tekst = _avsnitt(side)
        n = _nokkeltall(side)
        tall = _heltall(n["tall"])
        m = DELING.match(n["deling"])
        if not m:
            feil.append((orgnr, "nøkkeltallene", n["deling"]))
            continue
        egne, delt, uavklart = (_heltall(x) if x else 0 for x in m.groups())
        ord_ = "lokalitet med tillatelse" if tall == 1 else "lokaliteter med tillatelse"
        if n["etikett"] != f"{ord_} nå" or egne + delt + uavklart != tall:
            feil.append((orgnr, "etikett eller sum", n))
        # Indeksen.
        if indeks.get(orgnr) != {"lokaliteter_antall": tall,
                                 "lokaliteter_egne": egne,
                                 "lokaliteter_delt": delt}:
            feil.append((orgnr, "indeksen", indeks.get(orgnr), n))
        # JSON-LD.
        data = json.loads(re.search(
            r'<script type="application/ld\+json">(.*?)</script>', side, re.S).group(1))
        ventet = (f"{n['tall']} {ord_}: " + n["deling"].replace(" · ", ", ") + ".")
        if not html.unescape(data["description"]).replace("\xa0", " ").endswith(
                ventet.replace("\xa0", " ")):
            feil.append((orgnr, "JSON-LD", data["description"][-90:]))
        # Margen med kartet, og lista.
        delinger = [_avsnitt(x) for x in re.findall(
            r'data-felt="lokaliteter_deling">(.*?)</(?:dd|p)>', side, re.S)]
        if delinger != [n["deling"]] * 3:
            feil.append((orgnr, "margen eller lista", delinger))
        if f"av {n['tall']} {ord_} er tegnet" not in tekst:
            feil.append((orgnr, "kartteksten"))
        # Radene i lokalitetslista, slik de selv er merket.
        tabell = side[side.index('id="akvakultur-lokaliteter"'):]
        tabell = tabell[:tabell.index("</table>")]
        slag = re.findall(r'<tr data-deling="(\w+)">', tabell)
        if (slag.count("egne"), slag.count("delt"), slag.count("uavklart")) != (
                egne, delt, uavklart):
            feil.append((orgnr, "radene", len(slag), n))
        for rad_slag, a, b in re.findall(
                r'<tr data-deling="(\w+)">.*?data-felt="egne_tillatelser"[^>]*>'
                r'(\d+) av (\d+)<', tabell, re.S):
            if (rad_slag == "egne") != (a == b):
                feil.append((orgnr, "egne av alle", rad_slag, a, b))
        if "lokaliteter nå" in tekst.replace("med tillatelse nå", ""):
            feil.append((orgnr, "gammel etikett"))
        med_delt += delt > 0
        delt_i_alt += delt
        lok_i_alt += tall
    assert not feil, f"{len(feil)} avvik, f.eks. {feil[:5]}"
    # Prøven har sett ekte data: delingen finnes, og den er ikke alt.
    assert med_delt > 100 and 0 < delt_i_alt < lok_i_alt


@trenger_bygg
def test_sokets_undertittel_bruker_samme_ord():
    fil = next(p for p in sorted((NETTSTED / "selskap").glob("*/index.html"))
               if p.parent.name.isdigit())
    side = fil.read_text(encoding="utf-8")
    under = html.unescape(re.search(
        r'data-pagefind-meta="undertittel\[data-verdi\]" data-verdi="([^"]*)"',
        side).group(1))
    assert re.fullmatch(rf"{fil.parent.name} · \d[\d\s]* lokalitet(er)? med tillatelse",
                        under), under


@trenger_bygg
def test_om_siden_forklarer_delingen_med_de_samme_ordene():
    om = (NETTSTED / "om" / "index.html").read_text(encoding="utf-8")
    bit = om[om.index('id="lesing-selskap-lokaliteter"'):][:700]
    tekst = _avsnitt(bit[bit.index(">") + 1:])
    assert tekst.startswith("«Lokaliteter med tillatelse» teller hver lokalitet")
    assert "«Delt med andre»: et annet organisasjonsnummer har også tillatelse der." in tekst
    assert "«Bare egne»: ingen andre har det." in tekst
