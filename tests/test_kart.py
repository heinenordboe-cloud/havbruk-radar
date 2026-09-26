"""Projeksjonen og det avledede kystutdraget.

`kart.py` har ingen avhengigheter utover standardbiblioteket, og det er
et valg: et projeksjonsbibliotek drar med seg PROJ-databasen, og et
geometribibliotek er en avhengighet som skal følges i ti år. Prisen er
at formlene står her og må PRØVES her.
"""

import gzip
import json
import math
from pathlib import Path

import pytest

import kart

ROT = Path(__file__).resolve().parent.parent


# ---- UTM 33N ----------------------------------------------------------
#
# FASITEN ER REGNET, IKKE SKREVET AV. Hvert punkt under er kontrollert
# mot Kartverkets egen transformasjonstjeneste 25.09.2026
# (ws.geonorge.no/transformering/v1/transformer, fra 4258 til 25833), og
# tallene er svaret DEN ga. En prøve mot en tabell vi hadde regnet ut
# selv med den samme formelen, ville bare målt at formelen er seg selv
# lik.

FASIT = [
    # (lat, lon, østing, norting, hva) — tjenestens egne svar, ordrett.
    (58.0, 7.0, 27803.17296465335, 6456737.786457714, "Lindesnes, vest"),
    (60.4, 5.3, -33183.54326988198, 6735342.844288771, "Bergen"),
    (64.0, 15.0, 500000.00000000076, 7097014.16246643, "sentralmeridianen"),
    (68.9288, 16.5108, 560613.4601717583, 7647168.81350194,
     "Oterneset, lokalitet 31397"),
    (70.4, 31.1, 1096588.060198751, 7890085.812393519, "Vardø, langt øst"),
]


@pytest.mark.parametrize("lat,lon,ost,nord,hva", FASIT)
def test_utm33_treffer_fasiten(lat, lon, ost, nord, hva):
    """MÅLT avvik 25.09.2026: under en MILLIMETER på alle fem, også på
    Vardø som ligger 16 grader fra sentralmeridianen — langt utenfor
    sonens nominelle bredde. Terskelen står på en centimeter så prøven
    ikke faller på siste bit i en flyttallsrepresentasjon."""
    e, n = kart.utm33(lat, lon)
    assert abs(e - ost) < 0.01, f"{hva}: østing {e:.4f} mot {ost}"
    assert abs(n - nord) < 0.01, f"{hva}: norting {n:.4f} mot {nord}"


def _maalestokk(lat: float, lon: float, d: float = 0.01) -> float:
    """Målt målestokksfaktor: projisert lengde delt på sann lengde.

    Regnet av projeksjonen selv, ikke av en formel for målestokk — det
    er den projiserte lengden som havner på skjermen, og det er den som
    skal være riktig.
    """
    e1, n1 = kart.utm33(lat, lon)
    e2, n2 = kart.utm33(lat, lon + d)
    projisert = math.hypot(e2 - e1, n2 - n1)
    sant = d * 111320 * math.cos(math.radians(lat))
    return projisert / sant


@pytest.mark.parametrize("hva,lat,lon", [
    ("Lindesnes", 58.0, 7.0),
    ("Vardø", 70.4, 31.1),
    ("Bremanger", 61.8, 5.1),
    ("Nordkapp", 71.2, 25.8),
])
def test_maalestokken_holder_seg_under_en_prosent(hva, lat, lon):
    """Hele grunnen til at projeksjonen ble byttet 25.09.2026.

    Den gamle var ekvirektangulær med `cos(midtbredde)`, og på
    oversiktskartet ga den −19 % ved Lindesnes og +33 % ved Nordkapp:
    Finnmark var en tredjedel for bredt og Sørlandet en femtedel for
    smalt. UTM 33N holder hele landet innenfor én prosent.
    """
    k = _maalestokk(lat, lon)
    assert abs(k - 1) < 0.01, f"{hva}: målestokksfaktor {k:.5f}"


# ---- det avledede utdraget --------------------------------------------

UTDRAG = ROT / "maler" / "geo" / "kystlinje.json.gz"


@pytest.fixture(scope="module")
def utdrag():
    return json.loads(gzip.open(UTDRAG, "rt", encoding="utf-8").read())


def test_utdraget_er_under_taket():
    """Over tre megabyte skal det stoppe og rapporteres, ikke commites.

    Fila ligger i git, og git glemmer ingenting: hver ny utgave legger
    seg OPPÅ den forrige i historikken. Taket er derfor ikke en
    ytelsesgrense, det er en grense for hvor fort repoet vokser."""
    assert UTDRAG.exists(), "kystutdraget mangler — se verktoy/kystlinje.py"
    assert UTDRAG.stat().st_size <= 3_000_000


def test_utdraget_bærer_sin_egen_proveniens(utdrag):
    """Fila skal kunne leses av noen som ikke har lest dokumentasjonen.

    Lisensen, opphavet og enheten står I fila — ikke bare i
    KARTGEOMETRI.md. En binærfil som er skilt fra provenienssen sin, er
    en fil ingen kan gå god for.
    """
    assert utdrag["epsg"] == 25833
    assert utdrag["rute_m"] == 10
    assert "Kartverket" in utdrag["om"]
    assert "CC BY 4.0" in utdrag["om"]


def test_begge_opplosningene_er_med(utdrag):
    """`n500` til lokalitetskartet, `n2000` til oversikten. To
    oppløsninger fordi de svarer på hver sin ting."""
    for serie in ("n500", "n2000"):
        assert utdrag[serie]["hav"], serie
        assert utdrag[serie]["kyst"], serie


def test_koordinatene_er_hele_ti_meter(utdrag):
    """Avrundingen er en del av formatet, ikke en tilfeldighet ved
    skrivingen. Ett piksel er 64 m på lokalitetskartet."""
    for serie in ("n500", "n2000"):
        for flate in utdrag[serie]["hav"][:20]:
            for ring in flate:
                for x, y in ring[:50]:
                    assert x % 10 == 0 and y % 10 == 0, (serie, x, y)


def test_hver_havflate_er_en_gruppe_ringer(utdrag):
    """Øyer er INTERIØRRINGER i havflata. Skilles de fra hverandre,
    fylles de som hav i stedet for å bli hull — og et hull er det som
    viser land."""
    for serie in ("n500", "n2000"):
        for flate in utdrag[serie]["hav"][:50]:
            assert isinstance(flate, list) and flate
            for ring in flate:
                assert len(ring) >= 3
                assert isinstance(ring[0], list) and len(ring[0]) == 2


# ---- kartene i det bygde nettstedet ------------------------------------
#
# Krever et ferdig bygg, som `tests/test_smalskjerm.py`. Uten
# `HAVBRUK_NETTSTED` hoppes de over og sier hvorfor.

import os                                                  # noqa: E402
import pathlib                                             # noqa: E402

NETTSTED = os.environ.get("HAVBRUK_NETTSTED", "")

bygget = pytest.mark.skipif(
    not NETTSTED,
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted — "
           "bygg med `python nettsted.py --alle --ut <mappe>` først")

KART_TAK = 60_000


def _kart_i(html: str) -> str:
    """SVG-en, fra `<svg … data-kart` til `</svg>`. Tom uten kart."""
    i = html.find("data-kart")
    if i < 0:
        return ""
    start = html.rindex("<svg", 0, i)
    return html[start:html.index("</svg>", start) + 6]


@bygget
def test_ingen_lokalitetsside_har_et_kart_over_60_kb():
    """Kartet er tegnet INN i sida, så hver byte er en byte leseren
    laster. 1 782 sider ganger et kart som er dobbelt så stort som det
    trenger, er en side som er treg uten at noe på den er blitt bedre.

    Toleransen i `kart.POSISJON_TOLERANSE` er knappen som styrer det.
    """
    sider = sorted(pathlib.Path(NETTSTED, "lokalitet").glob("*/index.html"))
    assert len(sider) > 1000, f"fant bare {len(sider)} lokalitetssider"
    verst = []
    for sti in sider:
        kart_ = _kart_i(sti.read_text(encoding="utf-8"))
        if len(kart_.encode()) > KART_TAK:
            verst.append((len(kart_.encode()), sti.parent.name))
    verst.sort(reverse=True)
    assert not verst, f"kart over {KART_TAK} byte: {verst[:5]}"


OMRAADE_TAK = 150_000


@bygget
def test_heroens_bildemaal_er_kartets_egne():
    """`<img width height>` skal være SVG-ens `viewBox`.

    To tall skrevet to steder driver fra hverandre — og et bilde som
    oppgir feil mål, hopper i sida når fila lander. Her leses begge
    fra det bygde nettstedet, så prøven fanger både en endret ramme og
    en mal som fortsatt skriver de gamle tallene.
    """
    import re
    svg = pathlib.Path(NETTSTED, "kart", "norge.svg").read_text(encoding="utf-8")
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    assert vb, "norge.svg har ingen viewBox"
    html = pathlib.Path(NETTSTED, "index.html").read_text(encoding="utf-8")
    img = re.search(r'<img class="hero-kart"[^>]*>', html)
    assert img, "forsiden har ikke heroens kart"
    assert f'width="{_tall(vb.group(1))}"' in img.group(0), img.group(0)
    assert f'height="{_tall(vb.group(2))}"' in img.group(0), img.group(0)


def _tall(s: str) -> str:
    """«1800.0» og «1800» er samme tall; malen skriver det korteste."""
    v = float(s)
    return str(int(v)) if v == int(v) else str(v)


@bygget
def test_ingen_omraadeside_har_et_kart_over_150_kb():
    """Taket i `kart.OMRAADE_TAK` er et LØFTE, og dette er prøven som
    holder det — på den ferdige sida, ikke på anslaget.

    `kart._svgbyte()` regner ut hva malen kommer til å skrive, og
    velger serie etter det. Et anslag kan bli feil: endrer malen
    markupen rundt en prikk, flytter tallet seg uten at noen rører
    `kart.py`. Da skal det si fra HER, og ikke i en nettleser.
    """
    sider = sorted(pathlib.Path(NETTSTED, "produksjonsomrade")
                   .glob("*/index.html"))
    assert len(sider) >= 13, f"fant bare {len(sider)} områdesider"
    verst = []
    for sti in sider:
        kart_ = _kart_i(sti.read_text(encoding="utf-8"))
        if len(kart_.encode()) > OMRAADE_TAK:
            verst.append((len(kart_.encode()), sti.parent.name))
    verst.sort(reverse=True)
    assert not verst, f"områdekart over {OMRAADE_TAK} byte: {verst[:5]}"


@bygget
def test_kartet_er_aldri_eneste_vei_til_opplysningen():
    """Punkt 7, andre ledd: alt kartet viser står også som tekst.

    Et kart er utilgjengelig for den som ikke ser det, og upålitelig
    for den som ikke kan peke. Prikkene på områdekartet er derfor en
    ANNEN vei til tabellen under — og prøven her går den veien motsatt:
    hver lokalitet kartet lenker til, skal stå i tabellen på samme
    side. Er den ikke det, er kartet den eneste veien dit.

    Lokalitetssidas eget kart prøves på samme måte i
    `test_posisjonen_star_ogsaa_som_tall`: punktet er tegnet, og
    koordinatene står i bildeteksten.
    """
    import re
    mangler = []
    for sti in sorted(pathlib.Path(NETTSTED, "produksjonsomrade")
                      .glob("*/index.html")):
        html = sti.read_text(encoding="utf-8")
        kart_ = _kart_i(html)
        tabell = html[html.index('id="akvakultur-lokaliteter"'):]
        for nr in set(re.findall(r'href="/lokalitet/(\d+)/"', kart_)):
            if f'href="/lokalitet/{nr}/"' not in tabell:
                mangler.append((sti.parent.name, nr))
    assert not mangler, f"kartprikker uten rad i tabellen: {mangler[:5]}"


@bygget
def test_posisjonen_star_ogsaa_som_tall():
    """Kartet viser HVOR; bildeteksten sier det samme i grader.

    Prøven leser sidene som HAR et kart, og krever at den samme sida
    oppgir koordinatene som tekst. Merkelappen er ordene «posisjon
    fra» i bildeteksten, som står rett etter gradtallene.
    """
    uten = []
    for sti in sorted(pathlib.Path(NETTSTED, "lokalitet")
                      .glob("*/index.html"))[:400]:
        html = sti.read_text(encoding="utf-8")
        if "data-kart" in html and "posisjon fra" not in html:
            uten.append(sti.parent.name)
    assert not uten, f"kart uten koordinater i tekst: {uten[:5]}"


@bygget
def test_hver_lokalitetsside_med_koordinater_har_et_kart():
    """Et kart som stille uteble ville sett ut som en lokalitet uten
    koordinater, og de to er ikke det samme — siden sier i klartekst
    hvilken av dem det er.

    Fra 26.09.2026 er det TRE tilstander, ikke to: kart, ingen
    koordinater, eller koordinater utenfor kystbeltet Kartverket
    dekker. Hver har sin egen setning.
    """
    uten = []
    for sti in sorted(pathlib.Path(NETTSTED, "lokalitet").glob("*/index.html")):
        html = sti.read_text(encoding="utf-8")
        if ("data-kart" not in html
                and "oppgir ikke koordinater" not in html
                and "utenfor kystbeltet" not in html):
            uten.append(sti.parent.name)
    assert not uten, f"sider uten kart og uten forklaring: {uten[:5]}"
