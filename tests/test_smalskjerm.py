"""Det som bare kan måles på en RENDRET side, i en ekte nettleser.

390 piksler: ingen vannrett rulling i body, og ingen celle kuttet.
Brikkene: minst 44 piksler høye, i begge bredder.

## Hvorfor denne prøven ikke går i den vanlige runden

Den trenger et FERDIG BYGGET nettsted og en nettleser. Bygget tar ~45
sekunder og Chromium starter i ett til; den vanlige runden er på sju.
En prøve som gjorde hver kjøring et minutt lengre, er en prøve noen
slår av.

Den kjøres derfor mot en bygd mappe, oppgitt i miljøet:

    python nettsted.py --alle --ut /tmp/ut
    HAVBRUK_NETTSTED=/tmp/ut python -m pytest tests/test_smalskjerm.py

Uten variabelen hoppes den over, og den sier hvorfor.

## Hva som måles, og hva som ikke kan måles her

MÅLT PÅ RENDRET SIDE, ikke i CSS-en. Om en tabell «blir et kort» er et
resultat av `data-label`, `display: block`, målebånd, ordbrytning og
skriftmetrikk sammen — og hvert av de fem leddene kan være riktig mens
resultatet er en celle som er bredere enn skjermen. Det samme
argumentet som kontrastprøven bruker for å regne framfor å lese.

To ting måles:

  1. `documentElement.scrollWidth` mot vindusbredden. Ruller siden
     vannrett på en telefon, er noe bredere enn skjermen — og det er den
     feilen kortene finnes for å fjerne.
  2. Hver celle i en korttabell: `scrollWidth` mot `clientWidth`. En
     celle som er bredere enn sin egen boks har innhold utenfor kanten,
     også når siden ikke ruller.

Tabellen som IKKE blir kort — krysstabellen på /endringer/ — står i sin
egen `overflow-x: auto`-ramme, og at den ruller er meningen. Prøven
måler derfor sida og kortcellene, ikke rammene.
"""

import os
import socketserver
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest

BREDDE = 390

# Én side per sidetype. Lokalitetssiden har den bredeste tabellen på
# nettstedet (ni kolonner lusetall), og /endringer/ har unntaket.
SIDER = (
    "/",
    "/lokalitet/",
    "/lokalitet/31397/",
    "/produksjonsomrade/4/",
    "/selskap/",
    "/endringer/",
    "/endringer/2026-39/",
    "/om/",
    "/sok/",
)

ROT = os.environ.get("HAVBRUK_NETTSTED", "")

pytestmark = pytest.mark.skipif(
    not ROT,
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted — "
           "bygg med `python nettsted.py --alle --ut <mappe>` først")


@pytest.fixture(scope="module")
def tjener():
    """Sidene bruker ABSOLUTTE adresser og må serveres, ikke åpnes.

    `file://` ville gitt brutte bilder, brutt navigasjon og — verst for
    denne prøven — et stilark som ikke kom fram, altså en side uten
    kortlayout som prøven ville målt som om den var siden vår.
    """
    class Tyst(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    class Gjenbruk(socketserver.TCPServer):
        allow_reuse_address = True

    t = Gjenbruk(("127.0.0.1", 0), partial(Tyst, directory=str(Path(ROT))))
    threading.Thread(target=t.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{t.server_address[1]}"
    t.shutdown()


@pytest.fixture(scope="module")
def side(tjener):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        nettleser = p.chromium.launch()
        s = nettleser.new_page(viewport={"width": BREDDE, "height": 844})
        yield s
        nettleser.close()


@pytest.mark.parametrize("sti", SIDER)
def test_ingen_vannrett_rulling_paa_390(side, tjener, sti):
    side.goto(tjener + sti, wait_until="load")
    bredde = side.evaluate(
        "() => [document.documentElement.scrollWidth, window.innerWidth]")
    dokument, vindu = bredde
    assert dokument <= vindu, (
        f"{sti}: dokumentet er {dokument}px bredt i et {vindu}px vindu")


# ---- brikkene ---------------------------------------------------------
#
# 44 PIKSLER. WCAG 2.2 AA 2.5.8 setter 24x24 som minstemål; 44 er det
# som gjør en brikke til et treffsikkert mål med en tommel. Brikkene
# står side om side med 10 piksler mellom seg, så et lite mål her er et
# feilklikk, ikke bare en unøyaktighet.
#
# MÅLT I BEGGE BREDDER: høyden kommer av `min-block-size` og av hvor
# mange linjer teksten brekker til, og et navn som brekker på 390 og
# ikke på 1440 gir to ulike høyder.

MINSTE_TREFF = 44


@pytest.mark.parametrize("bredde", (390, 1440))
@pytest.mark.parametrize("sti", ("/", "/endringer/2026-39/"))
def test_brikkene_er_minst_44_piksler_hoye(side, tjener, sti, bredde):
    side.set_viewport_size({"width": bredde, "height": 844})
    side.goto(tjener + sti, wait_until="load")
    smaa = side.evaluate("""(minste) => {
      const ut = [];
      for (const b of document.querySelectorAll(".typemerke")) {
        const h = b.getBoundingClientRect().height;
        if (h < minste) {
          ut.push(b.textContent.trim().slice(0, 30) + " (" + Math.round(h) + "px)");
        }
      }
      return ut.slice(0, 5);
    }""", MINSTE_TREFF)
    side.set_viewport_size({"width": BREDDE, "height": 844})
    assert not smaa, f"{sti} @ {bredde}: brikker under {MINSTE_TREFF}px: {smaa}"


@pytest.mark.parametrize("sti", ("/", "/endringer/2026-39/"))
def test_en_brikke_med_null_er_ikke_klikkbar(side, tjener, sti):
    """Den fører til en side som viser null rader.

    Formen sier det — ingen ramme, ingen bakgrunn, dempet tekst — og
    `aria-disabled` sier det samme til den som ikke ser formen. Prøven
    måler begge deler på rendret side: at ingen null-brikke er et `<a>`,
    og at ingen av dem har en synlig ramme.
    """
    side.goto(tjener + sti, wait_until="load")
    feil = side.evaluate("""() => {
      const ut = [];
      for (const b of document.querySelectorAll(".typemerke--tom")) {
        const stil = getComputedStyle(b);
        if (b.tagName === "A") { ut.push("lenke: " + b.textContent.trim()); }
        if (b.getAttribute("aria-disabled") !== "true") {
          ut.push("uten aria-disabled: " + b.textContent.trim());
        }
        if (stil.boxShadow !== "none") {
          ut.push("med ramme: " + b.textContent.trim());
        }
      }
      return ut.slice(0, 5);
    }""")
    assert not feil, f"{sti}: {feil}"


# ---- heroen over kartet -----------------------------------------------
#
# FLATA UNDER TEKSTEN ER ET KART, ikke en farge, og et kart kan ikke
# leses av stilarket. `tests/test_kontrast.py` måler gulvet i CSS-en —
# at toningen er sterk nok mot hvitt. DETTE måler det som faktisk
# havner på skjermen: kartets egne piksler under hver tekstblokk, med
# toningen oppå.
#
# METODEN: skjul teksten, fotografer nøyaktig det rektangelet teksten
# sto i, og finn den LYSESTE pikselen der. Kontrasten mot `--papir`
# regnes med WCAG-formelen. Lyseste og ikke gjennomsnittet: en tekst er
# uleselig der den er uleselig, ikke i snitt.

PAPIR = (0xE7, 0xDB, 0xD0)      # --papir, heroens tekstfarge
AA_TEKST = 4.5
AA_STOR = 3.0                   # >= 24 px, WCAG 1.4.3


def _png_piksler(data: bytes):
    """(bredde, høyde, rader med (r,g,b)) fra en PNG.

    Bare det Chromium skriver: 8 bit per kanal, RGB eller RGBA, ingen
    interlacing. Hvilken av de to den velger avhenger av om utsnittet
    har gjennomsiktige piksler, og den velger begge — derfor leses
    kanaltallet av `IHDR` og ikke antas.

    Skrevet ut her framfor hentet. Et bildebibliotek for å lese fem
    skjermbilder er en avhengighet til i en prøve som allerede krever
    en nettleser.
    """
    import struct
    import zlib

    assert data[:8] == b"\x89PNG\r\n\x1a\n", "ikke en PNG"
    i, idat, bredde, hoyde, dybde, farge = 8, b"", 0, 0, 0, 0
    while i < len(data):
        lengde, merke = struct.unpack(">I4s", data[i:i + 8])
        kropp = data[i + 8:i + 8 + lengde]
        if merke == b"IHDR":
            bredde, hoyde, dybde, farge = struct.unpack(">IIBB", kropp[:10])
        elif merke == b"IDAT":
            idat += kropp
        elif merke == b"IEND":
            break
        i += 12 + lengde
    assert dybde == 8 and farge in (2, 6), \
        f"uventet PNG: dybde {dybde}, fargetype {farge}"

    raa = zlib.decompress(idat)
    kanaler = 3 if farge == 2 else 4
    linje = bredde * kanaler
    ut, forrige = [], bytearray(linje)
    p = 0
    for _ in range(hoyde):
        filter_ = raa[p]
        rad = bytearray(raa[p + 1:p + 1 + linje])
        p += 1 + linje
        for x in range(linje):
            a = rad[x - kanaler] if x >= kanaler else 0
            b = forrige[x]
            c = forrige[x - kanaler] if x >= kanaler else 0
            if filter_ == 1:
                rad[x] = (rad[x] + a) & 0xFF
            elif filter_ == 2:
                rad[x] = (rad[x] + b) & 0xFF
            elif filter_ == 3:
                rad[x] = (rad[x] + (a + b) // 2) & 0xFF
            elif filter_ == 4:
                p_ = a + b - c
                pa, pb, pc = abs(p_ - a), abs(p_ - b), abs(p_ - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                rad[x] = (rad[x] + pred) & 0xFF
        ut.append([(rad[x], rad[x + 1], rad[x + 2])
                   for x in range(0, linje, kanaler)])
        forrige = rad
    return bredde, hoyde, ut


def _lum(farge) -> float:
    def kanal(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (kanal(x) for x in farge)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _kontrast(a, b) -> float:
    la, lb = _lum(a), _lum(b)
    lys, morkt = max(la, lb), min(la, lb)
    return (lys + 0.05) / (morkt + 0.05)


@pytest.mark.parametrize("velger,terskel,hva", [
    (".hero-losen", AA_STOR, "mottoet, 32-62 px"),
    (".hero-tagline", AA_TEKST, "beskrivelsen"),
    (".hero-kreditt", AA_TEKST, "Kartverket-krediteringen"),
    (".hovedmeny a", AA_TEKST, "menyen"),
])
@pytest.mark.parametrize("bredde", (390, 1440))
def test_heroteksten_har_nok_kontrast(side, tjener, velger, terskel, hva,
                                      bredde):
    """Teksten i heroen står over KARTET, og kartet er ikke én farge.

    Målt på rendret side: teksten skjules, rektangelet den sto i
    fotograferes, og den LYSESTE pikselen der måles mot `--papir`.
    """
    side.set_viewport_size({"width": bredde, "height": 900})
    side.goto(tjener + "/", wait_until="load")
    side.wait_for_timeout(250)

    boks = side.evaluate("""(v) => {
      const el = document.querySelector(v);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {x: r.x, y: r.y, width: r.width, height: r.height};
    }""", velger)
    assert boks and boks["width"] > 4 and boks["height"] > 4, \
        f"{hva}: fant ikke {velger}"

    # ALL TEKST I HEROEN BORT, ikke bare den vi måler.
    #
    # Første utkast skjulte bare velgerens egne elementer, og da var den
    # lyseste pikselen i taglinens rektangel nøyaktig `--papir`: H1-ens
    # underlengder henger ned i boksen under, og søkefeltet er en
    # papirflate. Målingen leste altså tekst som bakgrunn.
    side.evaluate("""() => {
      const hero = document.querySelector(".hero");
      for (const el of hero.querySelectorAll(
              "h1, p, a, form, label, input, button, .merke")) {
        el.style.visibility = "hidden";
      }
    }""")
    side.wait_for_timeout(80)
    bilde = side.screenshot(clip=boks)
    side.set_viewport_size({"width": BREDDE, "height": 844})

    _b, _h, rader = _png_piksler(bilde)
    lysest = max((p for rad in rader for p in rad), key=_lum)
    k = _kontrast(PAPIR, lysest)
    assert k >= terskel, (
        f"{hva} @ {bredde}px: {k:.2f}:1 mot lyseste piksel "
        f"{lysest} — terskelen er {terskel}")


# ---- brikka «Alle N rader» --------------------------------------------


@pytest.mark.parametrize("uke", ("2026-36", "2026-37", "2026-39"))
def test_brikka_teller_radene_siden_faktisk_viser(side, tjener, uke):
    """«Alle N rader» skal være radene på SIDEN, ikke i changeloggen.

    `tillatelser` og `tillatelser_trukket` er to halvdeler av én
    hendelse og vises som én rad. Fram til 25.09.2026 telte brikka
    changelogg-radene, og uke 36 sa «Alle 61 rader» over en side som
    viste 54.

    Målt på rendret side og ikke i ramma: tallet er én ting, radene i
    to tabeller er noe annet, og bare nettleseren kan telle det siste.
    """
    side.goto(f"{tjener}/endringer/{uke}/", wait_until="load")
    tall = side.evaluate(r"""() => {
      const brikke = document.querySelector(".typemerke--valgt .typemerke-tall");
      const rader = document.querySelectorAll(
          "#endringer-uke tbody tr:not([data-tom]), "
          + "#endringer-selskapsdata tbody tr").length;
      return {brikke: brikke ? brikke.textContent.replace(/\D/g, "") : null,
              rader};
    }""")
    assert tall["brikke"] is not None, "fant ikke den valgte brikka"
    assert int(tall["brikke"]) == tall["rader"], (
        f"uke {uke}: brikka sier {tall['brikke']}, siden viser {tall['rader']}")


# ---- søket -----------------------------------------------------------
#
# MÅLT MOT DEN EKTE INDEKSEN. Pagefind bygges av en binær over den
# ferdige HTML-en, og rangeringen er dens — ikke vår. Om vekting,
# `data-pagefind-ignore` og metafeltene virker sammen kan bare avgjøres
# ved å spørre indeksen.


def _sok(side, tjener, q, filter_=None):
    side.goto(tjener + "/sok/", wait_until="load")
    return side.evaluate("""async ({q, f}) => {
      const pf = await import("/pagefind/pagefind.js");
      await pf.init();
      const r = await pf.search(q, f ? {filters: {type: f}} : undefined);
      const d = await Promise.all(r.results.slice(0, 10).map(x => x.data()));
      return d.map(x => ({url: x.url, meta: x.meta}));
    }""", {"q": q, "f": filter_})


def test_et_kommunenavn_gir_lokalitetene_i_kommunen_forst(side, tjener):
    """«Bremanger» er en kommune med lokaliteter, og et ord som står i
    en kolonne på mange andre sider.

    Vektingen av tittel og kommune er det som avgjør: uten den vant
    sider som bare NEVNER Bremanger i en tabellrad.
    """
    treff = _sok(side, tjener, "Bremanger")
    assert treff, "ingen treff på Bremanger"
    forste = treff[0]
    assert forste["meta"]["sidetype"] == "Lokalitet", forste["url"]
    assert "BREMANGER" in forste["meta"]["undertittel"].upper()
    # De fem øverste er alle lokaliteter i kommunen.
    for t in treff[:5]:
        assert t["meta"]["sidetype"] == "Lokalitet", t["url"]
        assert "BREMANGER" in t["meta"]["undertittel"].upper(), t["url"]


def test_et_lokalitetsnavn_gir_lokaliteten_forst(side, tjener):
    treff = _sok(side, tjener, "Oterneset")
    assert treff, "ingen treff på Oterneset"
    assert treff[0]["url"] == "/lokalitet/31397/", treff[0]["url"]


def test_hver_side_bærer_sidetype_undertittel_og_beskrivelse(side, tjener):
    """Metafeltene er det trefflista viser. Mangler ett av dem, faller
    lista tilbake på en URL og et klipp fra et vilkårlig sted på sida.
    """
    for q, ventet in (("Oterneset", "Lokalitet"),
                      ("Nordhordland til Stadt", "Produksjonsområde")):
        [forste, *_] = _sok(side, tjener, q)
        for felt in ("sidetype", "undertittel", "beskrivelse"):
            assert forste["meta"].get(felt), f"{q}: {felt} mangler"
        assert forste["meta"]["sidetype"] == ventet, q


def test_filteret_begrenser_til_en_sidetype(side, tjener):
    treff = _sok(side, tjener, "Bremanger", "Selskap")
    assert treff, "ingen selskaper med Bremanger"
    for t in treff:
        assert t["meta"]["sidetype"] == "Selskap", t["url"]


# ---- lokalitetssidens to spalter --------------------------------------


def test_tilstanden_staar_foer_tidslinja_i_markupen(side, tjener):
    """Rekkefølgen i DOM-en er den en telefon og en skjermleser får.

    Under 1024px er det én spalte, og da skal «hva er dette stedet nå»
    komme før «hva har skjedd her». På brede skjermer bytter `order`
    dem om — men markupen er det som gjelder når CSS-en ikke gjør det.
    """
    side.goto(tjener + "/lokalitet/31397/", wait_until="load")
    rekkefolge = side.evaluate("""() => {
      const t = document.querySelector(".lok-tilstand");
      const l = document.querySelector(".lok-tidslinje");
      if (!t || !l) return "mangler";
      return (t.compareDocumentPosition(l) & Node.DOCUMENT_POSITION_FOLLOWING)
             ? "tilstand først" : "tidslinje først";
    }""")
    assert rekkefolge == "tilstand først"


@pytest.mark.parametrize("bredde,ventet", ((390, "under"), (1440, "ved siden")))
def test_spaltene_faller_sammen_under_1024(side, tjener, bredde, ventet):
    """Over 1024: tidslinja til VENSTRE, tilstanden til høyre. Under:
    én spalte.

    Målt på plasseringen, ikke på mediespørringen: `order`, `grid` og
    målebåndet virker sammen, og hver av dem kan være riktig mens
    resultatet er to spalter på en telefon.
    """
    side.set_viewport_size({"width": bredde, "height": 900})
    side.goto(tjener + "/lokalitet/31397/", wait_until="load")
    boks = side.evaluate("""() => {
      const r = (s) => document.querySelector(s).getBoundingClientRect();
      const t = r(".lok-tilstand"), l = r(".lok-tidslinje");
      return {tv: t.left, tb: t.bottom, lv: l.left, lt: l.top,
              klebrig: getComputedStyle(document.querySelector(".lok-tilstand"))
                         .position};
    }""")
    side.set_viewport_size({"width": BREDDE, "height": 844})
    if ventet == "under":
        assert boks["tb"] <= boks["lt"] + 1, "tilstanden ligger ikke over"
        assert boks["tv"] == boks["lv"], "spaltene er ikke sammenfalt"
    else:
        assert boks["lv"] < boks["tv"], "tidslinja står ikke til venstre"
        assert boks["klebrig"] == "sticky", "høyrespalta er ikke klebrig"


@pytest.mark.parametrize("sti", SIDER)
def test_ingen_celle_er_kuttet_paa_390(side, tjener, sti):
    side.goto(tjener + sti, wait_until="load")
    kuttet = side.evaluate("""() => {
      const ut = [];
      /* BARE `<tbody>`. Hoderadene er visuelt skjult (1px) og dermed
         «kuttet» per definisjon — de er ikke noe en leser ser. */
      for (const c of document.querySelectorAll(".tabell--kort tbody td, "
                                                + ".tabell--kort tbody th")) {
        if (c.scrollWidth > c.clientWidth + 1) {
          ut.push((c.dataset.label || c.textContent).trim().slice(0, 40)
                  + " (" + c.scrollWidth + " > " + c.clientWidth + ")");
        }
      }
      return ut.slice(0, 5);
    }""")
    assert not kuttet, f"{sti}: celler utenfor egen kant: {kuttet}"
