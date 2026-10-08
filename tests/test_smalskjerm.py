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
import re
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


@pytest.mark.parametrize("bredde", (1000, 1200, 1440))
@pytest.mark.parametrize("sti", SIDER)
def test_ingen_vannrett_rulling_paa_bred_skjerm(side, tjener, sti, bredde):
    """Over 62rem slutter `.tabellramme` å rulle, med vilje — og da kan en
    tabell som er bredere enn spalten dra SIDEN ut i stedet.

    MÅLT 06.10.2026: /om/ var 1 477 px bred på 1440 og 1 403 på 1000.
    Kildetabellen hadde 1 033 px innhold i en spalte på 760. Prøven over
    målte bare 390, der ramma ruller, og så det derfor ikke.
    """
    side.set_viewport_size({"width": bredde, "height": 900})
    try:
        side.goto(tjener + sti, wait_until="load")
        dokument, vindu = side.evaluate(
            "() => [document.documentElement.scrollWidth, window.innerWidth]")
    finally:
        side.set_viewport_size({"width": BREDDE, "height": 844})
    assert dokument <= vindu, (
        f"{sti} @ {bredde}: dokumentet er {dokument}px bredt i et "
        f"{vindu}px vindu")


def _ledetall(tekst: str) -> int:
    """Første tall i en tekst, med tusenskille av mellomrom eller nbsp."""
    m = re.search(r"\d[\d\u00a0\u202f ]*", tekst)
    assert m, f"ingen tall i: {tekst[:120]}"
    return int(re.sub(r"\D", "", m.group()))


def test_metabeskrivelsen_har_samme_tall_som_overskriften():
    """Hver ukeside og hver typeside, lest som fil — ingen nettleser.

    Metabeskrivelsen sa radene i FILA, og uke 41 sto i søkeresultatet som
    «158 endringer» over en side som sa «90 endringer». MÅLT 06.10.2026.
    Prøven går gjennom ALLE sidene i bygget, ikke ett eksempel: tallet
    skal være likt på hver eneste én.
    """
    import html as _html

    sider = sorted(Path(ROT, "endringer").glob("*/**/index.html"))
    assert sider, "fant ingen ukesider i bygget"
    avvik = []
    for f in sider:
        kilde = f.read_text(encoding="utf-8")
        meta = re.search(r'<meta name="description" content="([^"]*)"', kilde)
        sammendrag = re.search(
            r'class="uke-sammendrag[^"]*">\s*<p>(.*?)</p>', kilde, re.S)
        if not (meta and sammendrag):
            avvik.append(f"{f}: mangler meta eller sammendrag")
            continue
        overskrift = re.sub(r"<[^>]+>", "", sammendrag.group(1))
        a = _ledetall(_html.unescape(meta.group(1)))
        b = _ledetall(_html.unescape(overskrift))
        if a != b:
            avvik.append(f"{f.relative_to(ROT)}: meta {a}, overskrift {b}")
    assert not avvik, "\n".join(avvik[:20])


def test_uke_35_sier_hva_trinnet_i_artsbegrensningene_var():
    """Tallene fra målingen 25.09.2026 (KILDE-AKVAKULTUR.md 4.5), regnet
    av radene i bygget — og bare på uke 35."""
    import html as _html
    def tekst(uke):
        f = Path(ROT, "endringer", uke, "index.html")
        return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ",
                                              f.read_text(encoding="utf-8"))).split())
    t = tekst("2026-35")
    assert ("hadde Fiskeridirektoratet endret artsbegrensningene for "
            "118 lokaliteter: 76 mistet alle, og 42 fikk sine første.") in t
    assert "endret artsbegrensningene for" not in tekst("2026-38")
    # RETT UNDER OVERSKRIFTEN, ikke i den lukkede delen med de tekniske.
    rå = Path(ROT, "endringer", "2026-35", "index.html").read_text(encoding="utf-8")
    assert re.search(r'</h1>\s*<p class="uke-ingress">\s*I øyeblikksbildet', rå)
    detaljer = rå.split('<details class="tallboks tekniske-endringer">', 1)[1]
    assert "endret artsbegrensningene" not in detaljer.split("</details>", 1)[0]


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


# ---- heroen over fotografiet ------------------------------------------
#
# FLATA UNDER TEKSTEN ER ET FOTO, ikke en farge, og et foto kan ikke
# leses av stilarket. `tests/test_kontrast.py` måler gulvet i CSS-en —
# at toningen er sterk nok mot HVITT, altså mot det verst tenkelige
# bildet. DETTE måler det som faktisk havner på skjermen: bildets egne
# piksler under hver tekstblokk, med toningen oppå.
#
# METODEN: skjul teksten, fotografer nøyaktig det rektangelet teksten
# sto i, og finn den LYSESTE pikselen der. Kontrasten mot elementets
# egen tekstfarge regnes med WCAG-formelen. Lyseste og ikke
# gjennomsnittet: en tekst er uleselig der den er uleselig, ikke i
# snitt.

# `PAPIR = (0xE7, 0xDB, 0xD0)` STO HER som heroens tekstfarge. Den er
# borte: fargen leses nå av den rendrede sida, fordi konstanten var
# usann i mørk modus og prøven ikke kunne se det. Se
# `test_heroteksten_har_nok_kontrast`.
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
    (".hero-bildetekst", AA_TEKST, "bildeteksten"),
    (".hovedmeny a", AA_TEKST, "menyen, alle fem lenkene"),
])
@pytest.mark.parametrize("modus", ("light", "dark"))
@pytest.mark.parametrize("bredde", (390, 1440))
def test_heroteksten_har_nok_kontrast(side, tjener, velger, terskel, hva,
                                      bredde, modus):
    """Kontrasten måles på den RENDREDE sida, ikke på tokener.

    Heroen har vært et foto, et kart og et foto igjen på fem dager.
    Denne prøven er den eneste som kan si om toningen er sterk nok der
    teksten FAKTISK står, over de pikslene som FAKTISK ligger der.

    ## TO TING BLE LAGT TIL 27.09.2026, og begge fordi prøven bommet

    **MODUS.** Prøven kjørte bare i lys. Heroteksten sto i
    `var(--papir)`, som snur til #121a1d i mørk modus, og h1 målte
    **1,34:1** der — i alle tre breddene. Prøven var grønn hele tiden,
    fordi den aldri spurte. Feilen var eldre enn fotografiet.

    **TEKSTFARGEN LESES, den antas ikke.** Fram til da var den hardkodet
    til papirfargen. Det er stedfortrederen fra CLAUDE.md 1b-2: konstanten
    var lik den ekte fargen helt til den ikke var det, og da målte
    prøven kontrasten til en farge som ikke sto på sida. Nå leses
    `getComputedStyle(el).color` — det ØYET ser, som resten av prøven.

    Teksten skjules, rektangelet den sto i fotograferes, og den LYSESTE
    pikselen der måles mot elementets egen farge.
    """
    side.emulate_media(color_scheme=modus)
    side.set_viewport_size({"width": bredde, "height": 900})
    side.goto(tjener + "/", wait_until="load")
    side.wait_for_timeout(250)

    # ALLE ELEMENTENE VELGEREN TREFFER, ikke det første.
    #
    # `querySelector(".hovedmeny a")` gir «Lokaliteter» alene. Da
    # menyen brøt til to linjer på 390, lå den andre — «Endringer»,
    # «Om», «Følg med» — lenger ned, over en lysere del av himmelen, og
    # ble aldri målt: 1,60:1. Menyen står på ÉN linje fra 27.09.2026,
    # men unionen blir stående. Den er det som gjør prøven riktig
    # uansett hvor mange linjer menyen tar, og hvor mange punkter den
    # har.
    boks = side.evaluate(r"""(v) => {
      const alle = [...document.querySelectorAll(v)];
      if (!alle.length) return null;
      const r = alle.map(e => e.getBoundingClientRect());
      const x = Math.min(...r.map(q => q.left));
      const y = Math.min(...r.map(q => q.top));
      const c = getComputedStyle(alle[0]).color
          .replace(/^rgba?\(/, "").replace(/\)$/, "").split(",");
      return {x, y, antall: alle.length,
              width: Math.max(...r.map(q => q.right)) - x,
              height: Math.max(...r.map(q => q.bottom)) - y,
              farge: [+c[0], +c[1], +c[2]]};
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
    klipp = {"x": max(boks["x"], 0), "y": max(boks["y"], 0),
             "width": boks["width"], "height": boks["height"]}
    bilde = side.screenshot(clip=klipp)
    # SIDA ER MODULSCOPET. Både bredden og modusen settes tilbake, ellers
    # arver neste prøve i fila en mørk 1440-skjerm uten å be om den.
    side.set_viewport_size({"width": BREDDE, "height": 844})
    side.emulate_media(color_scheme="light")

    _b, _h, rader = _png_piksler(bilde)
    lysest = max((p for rad in rader for p in rad), key=_lum)
    k = _kontrast(tuple(boks["farge"]), lysest)
    assert k >= terskel, (
        f"{hva} @ {bredde}px, {modus} ({boks['antall']} element): "
        f"{k:.2f}:1 — teksten er "
        f"{tuple(boks['farge'])}, lyseste piksel under den {lysest}, "
        f"terskelen {terskel}")


@pytest.mark.parametrize("bredde", (360, 390, 1440))
def test_menyflata_naar_heroens_kant(side, tjener, bredde):
    """Båndet bak menyen skal nå skjermkanten i alle bredder.

    Under 48rem har `.hero` sin egen `padding-inline` — luft fra den
    gang heroen var et bånd med en kant — og et barn av den arver
    innrykket. MÅLT 27.09.2026 på 390: flata sto x=16 med bredde 358,
    altså et mørkt rektangel med fotografi rundt tre av fire sider.

    Prøven måler flata mot HEROEN og ikke mot vindusbredden: det er
    heroens kant båndet skal nå, og de to er ikke alltid det samme.
    """
    side.set_viewport_size({"width": bredde, "height": 844})
    side.goto(tjener + "/", wait_until="load")
    side.wait_for_timeout(150)
    maal = side.evaluate("""() => {
      const f = document.querySelector('.hero-menyflate').getBoundingClientRect();
      const h = document.querySelector('.hero').getBoundingClientRect();
      return {fx: f.x, fh: f.right, fy: f.y,
              hx: h.x, hh: h.right, hy: h.y};
    }""")
    side.set_viewport_size({"width": BREDDE, "height": 844})
    assert abs(maal["fx"] - maal["hx"]) < 1, f"venstre kant: {maal}"
    assert abs(maal["fh"] - maal["hh"]) < 1, f"høyre kant: {maal}"
    assert abs(maal["fy"] - maal["hy"]) < 1, f"overkant: {maal}"


# ---- hovedmenyen ------------------------------------------------------


MENYSIDER = ("/", "/lokalitet/31397/", "/sok/")


@pytest.mark.parametrize("sti", MENYSIDER)
@pytest.mark.parametrize("bredde", (360, 390, 639, 640, 1440))
def test_menypunktene_star_paa_en_linje(side, tjener, sti, bredde):
    """Fem punkter, én linje, i hver bredde — og ordmerket over eller
    ved siden av.

    Fram til 27.09.2026 brøt menyen til to linjer under 640 px. Den
    andre linja havnet over en lysere del av herofotografiet, og det
    var der `test_heroteksten_har_nok_kontrast` fant 1,60:1.

    LØSNINGEN ER IKKE EN HAMBURGER. Får punktene ikke plass, ruller
    lista vannrett inne i seg selv — se `test_menyen_ruller_framfor_aa_bryte`.
    Alle fem er der, i samme rekkefølge, for øyet og for tabulatoren.
    """
    side.set_viewport_size({"width": bredde, "height": 844})
    side.goto(tjener + sti, wait_until="load")
    side.wait_for_timeout(120)
    m = side.evaluate("""() => {
      const nav = document.querySelector('.hovedmeny');
      const punkter = [...nav.querySelectorAll('ul a')];
      const merke = nav.querySelector('.merke').getBoundingClientRect();
      return {
        antall: punkter.length,
        topper: [...new Set(punkter.map(
            e => Math.round(e.getBoundingClientRect().top)))],
        merkeTopp: Math.round(merke.top),
        punktTopp: Math.round(punkter[0].getBoundingClientRect().top),
      };
    }""")
    side.set_viewport_size({"width": BREDDE, "height": 844})
    assert m["antall"] == 5, f"{sti}: {m['antall']} punkter"
    assert len(m["topper"]) == 1, (
        f"{sti} @ {bredde}: punktene står på {len(m['topper'])} linjer "
        f"({m['topper']})")
    if bredde >= 640:
        assert m["merkeTopp"] == m["punktTopp"], "ordmerket skal stå på linja"
    else:
        assert m["merkeTopp"] < m["punktTopp"], "ordmerket skal stå over"


@pytest.mark.parametrize("bredde", (360, 390))
def test_menyen_ruller_framfor_aa_bryte(side, tjener, bredde):
    """Når fem punkter ikke får plass, skal lista RULLE — ikke bryte,
    ikke krympe teksten, ikke gjemme noe bak en knapp.

    Prøven krever ikke at den RULLER ved en gitt bredde; den krever at
    lista er en rulleboks, og at ingenting er klippet bort: siste punkt
    skal være nåbart. Om 341 piksler med lenker får plass i 318 eller
    350 avhenger av fonten, og det er ikke det prøven handler om.
    """
    side.set_viewport_size({"width": bredde, "height": 844})
    side.goto(tjener + "/", wait_until="load")
    side.wait_for_timeout(120)
    m = side.evaluate("""() => {
      const ul = document.querySelector('.hovedmeny ul');
      const cs = getComputedStyle(ul);
      const siste = ul.querySelector('li:last-child a');
      ul.scrollLeft = ul.scrollWidth;
      const r = siste.getBoundingClientRect();
      const u = ul.getBoundingClientRect();
      return {wrap: cs.flexWrap, overflow: cs.overflowX,
              sisteSynlig: r.right <= u.right + 1 && r.left >= u.left - 1,
              sideRuller: document.documentElement.scrollWidth
                          > window.innerWidth};
    }""")
    side.set_viewport_size({"width": BREDDE, "height": 844})
    assert m["wrap"] == "nowrap", "lista bryter"
    assert m["overflow"] == "auto", "lista er ingen rulleboks"
    assert m["sisteSynlig"], "siste punkt er ikke nåbart ved å rulle"
    assert not m["sideRuller"], "menyen dro SIDA ut i bredden"


@pytest.mark.parametrize("bredde", (360, 390))
def test_forsidens_meny_har_samme_kanter_som_resten(side, tjener, bredde):
    """Forsiden fikk 16 px ekstra sideluft fra `.hero`, oppå `.ark`s egen.

    MÅLT 06.10.2026 på 390: menylista sto x=32–350 på forsiden og
    x=16–366 på undersidene. Den fikk 318 px til 341 px innhold, og
    «Søk» ble kappet til «S» — nåbart ved å rulle, men ikke synlig.
    """
    side.set_viewport_size({"width": bredde, "height": 844})
    kanter = {}
    try:
        for sti in ("/", "/lokalitet/31397/"):
            side.goto(tjener + sti, wait_until="load")
            kanter[sti] = side.evaluate("""() => {
              const ul = document.querySelector('.hovedmeny ul');
              const r = ul.getBoundingClientRect();
              const m = document.querySelector('.hovedmeny .merke')
                                .getBoundingClientRect();
              return {ul: [Math.round(r.left), Math.round(r.right)],
                      merke: Math.round(m.left),
                      ruller: ul.scrollWidth > ul.clientWidth};
            }""")
    finally:
        side.set_viewport_size({"width": BREDDE, "height": 844})
    forside, underside = kanter["/"], kanter["/lokalitet/31397/"]
    assert forside["ul"] == underside["ul"], kanter
    assert forside["merke"] == underside["merke"], kanter
    if bredde == 390:
        assert not forside["ruller"], "alle fem punktene skal synes på 390"


LOKALITETER = ("/lokalitet/45140/", "/lokalitet/12325/", "/lokalitet/31397/")


@pytest.mark.parametrize("bredde", (1440, 390))
@pytest.mark.parametrize("sti", LOKALITETER)
def test_lokalitetssiden_har_ingen_egen_loddrett_rulling(side, tjener, sti, bredde):
    """Ingen element har `overflow-y` `auto` eller `scroll`, bortsett fra
    tabellrammene som ruller vannrett på telefon.

    Til 06.10.2026 hadde høyrespalta et høydetak og egen rulling, for at
    fisk til stede og siteringen nederst i den skulle nås. Det var en
    rullboks inni en rullende side. Unntaket måles på `overflow-x`: en
    ramme som ruller vannrett får `overflow-y: auto` beregnet av
    nettleseren, og det er den ene formen som er meningen.
    """
    side.set_viewport_size({"width": bredde, "height": 900})
    try:
        side.goto(tjener + sti, wait_until="load")
        ruller = side.evaluate("""() => [...document.querySelectorAll("*")]
          .filter(e => {
            const s = getComputedStyle(e);
            if (!["auto", "scroll"].includes(s.overflowY)) return false;
            return !(e.classList.contains("tabellramme")
                     && ["auto", "scroll"].includes(s.overflowX));
          })
          .map(e => e.tagName.toLowerCase() + "." + e.className)""")
    finally:
        side.set_viewport_size({"width": BREDDE, "height": 844})
    assert not ruller, f"{sti} på {bredde}: {ruller}"


@pytest.mark.parametrize("sti", LOKALITETER)
def test_hoyrespalta_har_bare_tilstanden_og_kartet(side, tjener, sti):
    """Fisk til stede og siteringen står i hovedflyten under tidslinja,
    over hele bredden — ikke i høyrespalta."""
    side.set_viewport_size({"width": 1440, "height": 900})
    try:
        side.goto(tjener + sti, wait_until="load")
        m = side.evaluate("""() => {
          const t = document.querySelector(".lok-tilstand");
          const l = document.querySelector(".lok-tidslinje");
          const fisk = document.querySelector("#fisk-tittel").closest("section");
          const siter = document.querySelector("#siter");
          const etter = (a, b) => !!(a.compareDocumentPosition(b)
                                     & Node.DOCUMENT_POSITION_FOLLOWING);
          return {
            i_spalta: [...t.querySelectorAll("h2")].map(h => h.id),
            kart: !!t.querySelector(".posisjonskart, .posisjon-mangler"),
            fisk_etter: etter(l, fisk), siter_etter: etter(l, siter),
            fisk_bredde: fisk.getBoundingClientRect().width,
            siter_bredde: siter.getBoundingClientRect().width,
            // FULL BREDDE er lakselusblokka sin, som står over hele siden.
            full: document.querySelector("#lus-tittel").closest("section")
                          .getBoundingClientRect().width,
            hoyde: t.getBoundingClientRect().height,
            vindu: window.innerHeight};
        }""")
    finally:
        side.set_viewport_size({"width": BREDDE, "height": 844})
    assert m["i_spalta"] == ["tilstand-tittel"], m
    assert m["kart"], m
    assert m["fisk_etter"] and m["siter_etter"], m
    assert abs(m["fisk_bredde"] - m["full"]) <= 1, m
    assert abs(m["siter_bredde"] - m["full"]) <= 1, m
    # Uten tak må innholdet få plass, ellers henger bunnen av den
    # klebrige spalta under skjermkanten.
    assert m["hoyde"] <= m["vindu"], m


# ---- brikka «Alle N endringer» ----------------------------------------


@pytest.mark.parametrize("uke", ("2026-36", "2026-37", "2026-39", "2026-41"))
def test_alle_brikka_teller_det_samme_som_overskriften(side, tjener, uke):
    """«Alle N endringer» er overskriftens N, uten selskapsdata.

    Til 25.09.2026 telte brikka changelogg-radene, og fram til 06.10
    radene på siden — med selskapsdataene, som har sin egen del og sin
    egen brikke. Uke 41 sa «Alle 134 rader» under «75 endringer».
    """
    side.goto(f"{tjener}/endringer/{uke}/", wait_until="load")
    tall = side.evaluate(r"""() => {
      const brikke = document.querySelector(".typemerke--valgt .typemerke-tall");
      const p = document.querySelector(".uke-sammendrag p");
      return {brikke: brikke ? brikke.textContent.replace(/\D/g, "") : null,
              overskrift: p ? p.textContent.trim().split(" ")[0].replace(/\D/g, "") : null};
    }""")
    assert tall["brikke"] is not None, "fant ikke den valgte brikka"
    assert tall["brikke"] == tall["overskrift"], (
        f"uke {uke}: brikka sier {tall['brikke']}, overskriften {tall['overskrift']}")


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


# ---- ukesidenes hentetidspunkt -----------------------------------------

def _proveniens(uke: str) -> str:
    import html as _html
    raa = Path(ROT, "endringer", uke, "index.html").read_text(encoding="utf-8")
    m = re.search(r'<div class="ark bunn-proveniens">\s*<p>(.*?)</p>', raa, re.S)
    assert m, f"ingen proveniens på {uke}"
    return " ".join(_html.unescape(m.group(1)).split())


def test_uke_35_og_uke_41_oppgir_hver_sin_henting():
    """MÅLT 07.10.2026: begge sa «hentet 5. oktober 2026 kl. 12.07 UTC»,
    det nyeste snapshotets tidspunkt. Uke 35 ble hentet 24. august.

    Tidspunktene er datarepoets (fetched_at i snapshotene for 2026-08-24
    og 2026-10-05), lest 08.10.2026."""
    u35, u41 = _proveniens("2026-35"), _proveniens("2026-41")
    assert "hentet 24. august 2026 kl. 19.48 UTC" in u35, u35
    assert "hentet 5. oktober 2026 kl. 12.07 UTC" in u41, u41
    hentet = lambda t: t.split("hentet ", 1)[1].split(".", 1)[0]
    assert hentet(u35) != hentet(u41)


def test_ingen_ukeside_er_hentet_foer_sin_egen_uke():
    """For hver ukeside i bygget: hentingen er ikke eldre enn uka den
    sier den er bygget fra. Fanger at en uke låner et annet snapshots
    tidspunkt i begge retninger, så langt dato-delen kan si det."""
    import datetime as dt
    maaneder = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
                "august", "september", "oktober", "november", "desember"]
    tider = {}
    for mappe in sorted(Path(ROT, "endringer").glob("20??-??")):
        t = _proveniens(mappe.name)
        m = re.search(r"hentet (\d+)\. (\w+) (\d{4})", t)
        assert m, t
        d = dt.date(int(m[3]), maaneder.index(m[2]) + 1, int(m[1]))
        aar, uke, _ = d.isocalendar()
        assert (aar, uke) >= tuple(int(x) for x in mappe.name.split("-")), t
        tider[mappe.name] = d
    assert len(set(tider.values())) == len(tider), tider


def test_moerk_modus_i_systemet_gir_den_samme_lyse_siden(side, tjener):
    """Bare lys modus — docs/design/BRIEF.md. En leser med mørk modus i
    systemet skal få nøyaktig den samme paletten, ikke en halvveis
    oversatt side."""
    farger = {}
    for modus in ("light", "dark"):
        side.emulate_media(color_scheme=modus)
        side.goto(tjener + "/lokalitet/31397/", wait_until="load")
        farger[modus] = side.evaluate(
            "[getComputedStyle(document.body).backgroundColor,"
            " getComputedStyle(document.body).color]")
    side.emulate_media(color_scheme="light")
    assert farger["dark"] == farger["light"]
