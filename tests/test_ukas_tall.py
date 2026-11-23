"""Tallene øverst på forsiden og ukessidene sier hva de teller.

Til 23.11.2026 sto «Fisk til stede 77» i typestolpene like ved setningen
«Fisk til stede: 36 lokaliteter gikk fra nei til ja, 39 fra ja til nei»
(75). 77 er endringer, 75 er lokaliteter, og typen «Fisk til stede» er
hele biomasselaget: også artene.

MÅLT 23.11.2026 over de 13 ukene med endringer: i 4 av dem (uke 40, 41,
43 og 47) er typebrikken større enn de to tallene i setningen, og resten
er hver gang `arter_tilstede` og `antall_arter` på lokaliteter der fisken
sto hele tida. Setningen gjør nå rede for resten, så de tre tallene
summerer til brikka, og stolpene heter «Endringer etter type».

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import html
import os
import re
from pathlib import Path

import pytest

import nettsted

ALLE = frozenset({"eierskap", "biomasselag", "akvakultur"})


def _h(felt, eid, til=""):
    return {"type": "biomasse", "kildefelt": felt, "entity_id": eid, "til": til}


def _fisk(ledet) -> str:
    return next(s for s in nettsted._ukefakta(ledet, ALLE) if "isk til stede" in s)


# --------------------------------------------------------------- setningen

def test_setningen_gjoer_rede_for_resten_av_typen():
    """Én lokalitet fikk en art til uten at fisken kom eller gikk: to
    rader i samme type. 1 + 2 + 2 er de fem endringene brikka teller."""
    ledet = [_h("har_fisk", "1", "Ja"), _h("har_fisk", "2", "Nei"),
             _h("har_fisk", "3", "Nei"),
             _h("arter_tilstede", "4", "Laks;Regnbueørret"),
             _h("antall_arter", "4", "2")]
    assert _fisk(ledet) == ("Fisk til stede: 1 lokalitet gikk fra nei til ja, "
                            "2 fra ja til nei. 2 endringer til gjaldt arter.")


def test_uten_rest_er_setningen_som_foer():
    ledet = [_h("har_fisk", "1", "Ja"), _h("har_fisk", "2", "Nei")]
    assert _fisk(ledet) == ("Fisk til stede: 1 lokalitet gikk fra nei til ja, "
                            "1 fra ja til nei.")


def test_bare_artsendringer_staar_uten_til():
    ledet = [_h("arter_tilstede", "4", "Laks")]
    assert _fisk(ledet) == ("Ingen lokaliteter endret status for fisk til stede. "
                            "1 endring gjaldt arter.")


def test_et_annet_felt_i_typen_kalles_ikke_arter():
    ledet = [_h("har_fisk", "1", "Ja"), _h("lokalitet_status", "5", "AKTIV")]
    assert _fisk(ledet).endswith("1 endring til gjaldt annet.")


@pytest.mark.parametrize("ledet", [
    [_h("har_fisk", str(i), "Ja") for i in range(36)]
    + [_h("har_fisk", str(100 + i), "Nei") for i in range(39)]
    + [_h("arter_tilstede", "999", "Laks"), _h("antall_arter", "999", "2")],
    [_h("har_fisk", "1", "Ja"), _h("har_fisk", "1", "Nei"), _h("har_fisk", "1", "Ja")],
    [_h("arter_tilstede", "4", "Laks")],
    [],
])
def test_tallene_i_setningen_summerer_til_typens_rader(ledet):
    """Også når samme lokalitet gikk samme vei to ganger i uka: den telles
    én gang som lokalitet, og den andre raden står i resten."""
    assert sum(_tall_i_setningen(_fisk(ledet))) == len(ledet)


def test_setningen_er_under_avsnittsgrensa_med_store_tall():
    ledet = ([_h("har_fisk", str(i), "Ja") for i in range(1234)]
             + [_h("har_fisk", str(5000 + i), "Nei") for i in range(1234)]
             + [_h("lokalitet_status", str(9000 + i), "X") for i in range(123)])
    import publiseringsvakt
    assert len(_fisk(ledet)) <= publiseringsvakt.AVSNITTSGRENSE, _fisk(ledet)


def test_typen_sier_at_den_ogsaa_teller_artene():
    hva = {k["id"]: k["hva"] for k in nettsted.ENDRINGSTYPER}["biomasse"]
    assert hva == "om det står fisk på lokaliteten, og hvilke arter"


def test_forsidens_stolper_heter_endringer_etter_type():
    mal = (Path(nettsted.__file__).parent / "maler" / "forside.html.j2").read_text(
        encoding="utf-8")
    assert '<figcaption class="etikett">Endringer etter type</figcaption>' in mal
    assert ">Etter type<" not in mal


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "endringer").is_dir() or not (NETTSTED / "index.html").is_file(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted med forside og /endringer/")

SETNING = re.compile(
    r"^(?:Fisk til stede: (\d[\d\s]*) lokalitet(?:er)? gikk fra nei til ja, "
    r"(\d[\d\s]*) fra ja til nei\.|Ingen lokaliteter endret status for fisk til stede\.)"
    r"(?: (\d[\d\s]*) endring(?:er)?(?: til)? gjaldt (?:arter|annet)\.)?$")


def _tall_i_setningen(setning: str) -> list[int]:
    m = SETNING.match(" ".join(html.unescape(setning).split()))
    assert m, setning
    return [int("".join(x.split())) for x in m.groups() if x]


def _avsnitt(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", markup)).split())


def _fakta(side: str) -> list[str]:
    liste = re.search(r'<ul class="uke-fakta">(.*?)</ul>', side, re.S)
    return [_avsnitt(x) for x in re.findall(r"<li>(.*?)</li>", liste.group(1), re.S)] \
        if liste else []


def _ukesider() -> list[Path]:
    return sorted(p for p in (NETTSTED / "endringer").glob("*/index.html")
                  if re.fullmatch(r"\d{4}-\d{2}", p.parent.name))


@trenger_bygg
def test_brikka_og_setningen_summerer_paa_hver_ukeside():
    """«Fisk til stede N» på brikka er N endringer, og tallene i
    faktasetningen under summerer til N. Uker uten setning (kilden ble
    ikke sammenlignet) har null på brikka."""
    sider = _ukesider()
    assert len(sider) >= 10, "fant ikke ukesidene"
    feil, med_rest = [], 0
    for fil in sider:
        side = fil.read_text(encoding="utf-8")
        brikke = re.search(
            r'Fisk til stede <span class="typemerke-tall">([^<]*)</span>', side)
        assert brikke, f"{fil}: fant ikke brikka"
        n = int("".join(html.unescape(brikke.group(1)).split()))
        setning = [s for s in _fakta(side) if "isk til stede" in s]
        if not setning:
            if n:
                feil.append((fil.parent.name, n, "ingen setning"))
            continue
        tall = _tall_i_setningen(setning[0])
        if sum(tall) != n:
            feil.append((fil.parent.name, n, setning[0]))
        med_rest += len(tall) == 3
        if "Alle <span" not in side or "endringer" not in _avsnitt(
                re.search(r'<ul class="typemerker".*?</li>', side, re.S).group(0)):
            feil.append((fil.parent.name, "den første brikka sier ikke «endringer»"))
    assert not feil, feil[:5]
    assert med_rest >= 1, "ingen uke i bygget har en rest; prøven har ikke sett tilfellet"


@trenger_bygg
def test_forsiden_merker_stolpene_som_endringer_og_summerer_likt():
    side = (NETTSTED / "index.html").read_text(encoding="utf-8")
    stolper = re.search(r'<figure class="typestolper">(.*?)</figure>', side, re.S)
    assert stolper, "forsiden har ingen typestolper"
    assert "Endringer etter type" in _avsnitt(stolper.group(1))
    par = dict(re.findall(
        r'<span class="typestolpe-type">([^<]*)</span>\s*'
        r'<span class="typestolpe-tall">([^<]*)</span>', stolper.group(1)))
    setning = [s for s in _fakta(side) if "isk til stede" in s]
    if "Fisk til stede" in par and setning:
        n = int("".join(html.unescape(par["Fisk til stede"]).split()))
        assert sum(_tall_i_setningen(setning[0])) == n, (n, setning[0])
    # Samme setninger som øverst på den nyeste ukessiden, uten «Ingen …»
    # (16b): en slik linje står aldri først og vises bare på ukessiden.
    uka = _fakta(_ukesider()[-1].read_text(encoding="utf-8"))
    assert _fakta(side) == [s for s in uka if not s.startswith("Ingen")]
    assert not [s for s in _fakta(side) if s.startswith("Ingen")]
