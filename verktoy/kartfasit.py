#!/usr/bin/env python3
"""Måler lokalitetskartet mot N500 Arealdekke: hvor mange piksler er
malt feil?

## Hva fasiten er

Kartet vårt tegner to ting: hav og land. Fasiten må svare på det samme
spørsmålet for hvert punkt, og svaret finnes i den SAMME kilden vi
allerede bruker — N500 Arealdekke — bare i den andre halvdelen av den.
`Havflate` er sjøen; alt det andre som er en FLATE er land:
`ÅpentOmråde`, `Skog`, `Myr`, `SnøIsbre`, `Tettbebyggelse`, `Innsjø`,
`Elv`, `Industriområde`, `Golfbane`, `Lufthavn`, `Steinbrudd`.

Innsjøer og elver regnes som land her. Det er ikke slurv: spørsmålet
kartet svarer på er «er dette sjø», og et vann på et fjell er ikke sjø.
Kartet maler dem i landfargen, og fasiten må stille det samme
spørsmålet — ellers måler vi noe annet enn det vi vil vite (CLAUDE.md
regel 1b-2).

## Hva som sammenlignes

Vår side rasteriseres i en nettleser, ikke gjenskapes i Python. En
Python-modell av malerekkefølgen ville målt modellen, ikke sida.
Lagene som ikke er flater — gradnett, områdegrense, naboer, markør,
målestokk og kystkonturstreken — strippes før rasteriseringen, så det
som måles er nettopp fyllet: hav mot land.

KYSTKONTURSTREKEN ER TATT UT MED VILJE. Den er en strek på halvannen
piksel oppå grensa mellom to flater, og med den inne ville hver
kystlinje i utsnittet talt som en stripe feilmalte piksler i en måling
som handler om noe helt annet.

## Bruk

    python3 verktoy/kartfasit.py <nettstedmappe> [loknr ...]

GML-fila lastes ned for hånd fra Geonorge og ligger aldri i repoet —
samme regel som `verktoy/kystlinje.py`. Stien settes med
`N500_AREALDEKKE`.
"""

from __future__ import annotations

import os
import pathlib
import re
import struct
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import kart                                                 # noqa: E402
from core import snapshot                                   # noqa: E402

GML = pathlib.Path(os.environ.get(
    "N500_AREALDEKKE",
    "/tmp/kystloggen-kart/Basisdata_0000_Norge_25833_N500Arealdekke_GML.gml"))

# FLATETYPENE SOM ER LAND. Lista er lest ut av fila selv, ikke gjettet:
# `grep -o "<app:\w* " | sort | uniq -c` gir 22 typer, og de elleve her
# er de som er flater og ikke er `Havflate`. De ti andre er linjer
# (grenser, kanter, sperrer) og har ingen innside.
LANDFLATER = ("ÅpentOmråde", "Skog", "Myr", "SnøIsbre", "Tettbebyggelse",
              "Innsjø", "Elv", "Industriområde", "Golfbane", "Lufthavn",
              "Steinbrudd")

NI = ("11899", "11851", "45275",        # utenfor kystbeltet (punkt 1)
      "13509", "11682", "15657", "36197", "10505", "10837")   # de seks

START = re.compile(r"<app:(\w+)[ >]")
POSLIST = re.compile(r"<gml:posList[^>]*>([^<]*)</gml:posList>")


# --------------------------------------------------------- fasiten

def _rammer(loknr: list[str]) -> dict:
    """{loknr: (projeksjon, lat, lon)} — samme utsnitt som sida har."""
    df = snapshot.versjoner("akvakultur", snapshot.siste_dato("akvakultur"))[-1][1]
    pos: dict[str, dict] = {}
    for eid, felt, verdi in df.select(["entity_id", "field", "value"]).iter_rows():
        if eid in set(loknr) and felt in ("breddegrad", "lengdegrad"):
            pos.setdefault(eid, {})[felt] = verdi
    ut = {}
    for nr in loknr:
        d = pos.get(nr)
        if not d:
            print(f"  {nr}: ingen koordinater i snapshotet")
            continue
        lat, lon = float(d["breddegrad"]), float(d["lengdegrad"])
        ost, nord = kart.utm33(lat, lon)
        halv = kart.POSISJON_KM * 1000 / 2
        ut[nr] = (kart.Projeksjon(ost - halv, nord - halv,
                                  ost + halv, nord + halv,
                                  bredde=kart.POSISJON_BREDDE, marg=0),
                  lat, lon)
    return ut


def _fyll(rute: bytearray, bredde: int, hoyde: int, ringer: list) -> None:
    """Skanlinjefyll med PARTALLSREGEL over alle ringene i én flate.

    Ytterring og hull i samme omgang: et punkt som ligger innenfor et
    like antall ringer er utenfor flata. Det er den samme regelen som
    `fill-rule="evenodd"` i SVG-en, og det er meningen — fasiten og
    kartet skal svare på spørsmålet på samme måte.
    """
    kanter = []
    ymin, ymaks = 1e18, -1e18
    for ring in ringer:
        for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
            if y0 != y1:
                kanter.append((y0, y1, x0, x1))
            ymin = min(ymin, y0, y1)
            ymaks = max(ymaks, y0, y1)
    if not kanter:
        return
    for py in range(max(0, int(ymin)), min(hoyde, int(ymaks) + 2)):
        y = py + 0.5
        xs = []
        for y0, y1, x0, x1 in kanter:
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        if not xs:
            continue
        xs.sort()
        rad = py * bredde
        for i in range(0, len(xs) - 1, 2):
            a = max(0, int(xs[i] + 0.5))
            b = min(bredde, int(xs[i + 1] + 0.5))
            for px in range(a, b):
                rute[rad + px] = 1


def fasit(rammer: dict) -> dict:
    """{loknr: bytearray} med 1 = land, lest av N500 Arealdekke.

    Fila strømmes ÉN gang for alle utsnittene samtidig: den er 162 MB,
    og ni gjennomlesninger er ni ganger så lang tid for det samme
    svaret.
    """
    if not GML.exists():
        raise SystemExit(
            f"{GML} finnes ikke. Last ned N500 Arealdekke GML fra "
            f"nedlasting.geonorge.no og sett N500_AREALDEKKE.")
    ruter = {nr: bytearray(p.bredde * int(p.hoyde))
             for nr, (p, _lat, _lon) in rammer.items()}
    bokser = {nr: (p.ost_min, p.nord_min, p.ost_maks, p.nord_maks)
              for nr, (p, _lat, _lon) in rammer.items()}

    type_ = None
    ringer: list = []
    n = truffet = 0
    with GML.open(encoding="utf-8", errors="replace") as f:
        for linje in f:
            if type_ is None:
                m = START.search(linje)
                if not (m and m.group(1) in LANDFLATER):
                    continue
                type_, ringer = m.group(1), []
            p = POSLIST.search(linje)
            if p:
                tall = [float(v) for v in p.group(1).split()]
                ringer.append(list(zip(tall[0::2], tall[1::2])))
            if f"</app:{type_}>" not in linje:
                continue
            n += 1
            if ringer:
                xs = [x for r in ringer for x, _ in r]
                ys = [y for r in ringer for _, y in r]
                bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
                for nr, (o0, n0, o1, n1) in bokser.items():
                    if bx1 < o0 or bx0 > o1 or by1 < n0 or by0 > n1:
                        continue
                    truffet += 1
                    proj = rammer[nr][0]
                    _fyll(ruter[nr], proj.bredde, int(proj.hoyde),
                          [[(proj.x(x), proj.y(y)) for x, y in r]
                           for r in ringer])
            type_, ringer = None, []
    print(f"  {n} landflater lest, {truffet} traff et utsnitt")
    return ruter


# ------------------------------------------------------ vår egen side

def _png(data: bytes):
    """(bredde, høyde, rader med (r,g,b)). Samme leser som i prøvene."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
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
    assert dybde == 8 and farge in (2, 6)
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


STRIPP = ("kart-gitter", "kart-grense", "kart-naboer", "kart-markor",
          "kart-malestokk", "kart-kyst")


def _bare_flatene(svg: str) -> str:
    """SVG-en med alt som ikke er et FYLL tatt ut."""
    for klasse in STRIPP:
        while True:
            i = svg.find(f'<g class="{klasse}"')
            if i < 0:
                break
            svg = svg[:i] + svg[svg.index("</g>", i) + 4:]
    return svg


def rasteriser(nettsted: pathlib.Path, loknr: list[str], stil: str) -> dict:
    """{loknr: (bredde, høyde, rader)} — sidens eget kart, i piksler."""
    from playwright.sync_api import sync_playwright
    ut = {}
    with sync_playwright() as pw:
        nb = pw.chromium.launch()
        side = nb.new_page(viewport={"width": 900, "height": 900})
        for nr in loknr:
            html = (nettsted / "lokalitet" / nr / "index.html").read_text(
                encoding="utf-8")
            i = html.find("data-kart")
            if i < 0:
                ut[nr] = None
                continue
            s = html.rindex("<svg", 0, i)
            svg = _bare_flatene(html[s:html.index("</svg>", s) + 6])
            fil = pathlib.Path("/tmp") / f"kartfasit-{nr}.html"
            # NATURLIG STØRRELSE, 1:1 MOT FASITEN. Stilarket gjør
            # kartet flytende (`inline-size: 100%`), og i en tom side
            # blir det da 700 x 448 med `preserveAspectRatio`-striper
            # på sidene — en raster som ikke lar seg legge oppå
            # fasiten. Her tvinges SVG-en til sine egne viewBox-mål,
            # så piksel 0,0 i bildet er piksel 0,0 i utsnittet.
            fil.write_text(
                f"<!doctype html><style>*{{margin:0;padding:0}}{stil}\n"
                f"svg{{inline-size:{kart.POSISJON_BREDDE}px!important;"
                f"block-size:{kart.POSISJON_BREDDE}px!important;"
                f"max-inline-size:none!important;"
                f"max-block-size:none!important;display:block}}"
                # `.lok-tilstand` MÅ VÆRE MED. Kartet står i
                # tilstandsspalta på sida, og den spalta setter både
                # bakgrunnen og taket på høyden. Uten wrapperen måler
                # vi et kart som ikke finnes noe sted.
                f"</style><div class=\"lok-tilstand\">{svg}</div>",
                encoding="utf-8")
            side.goto(fil.as_uri())
            side.wait_for_timeout(120)
            ut[nr] = _png(side.locator("svg").first.screenshot())
        nb.close()
    return ut


def _stil(nettsted: pathlib.Path) -> str:
    """Sidens eget stilark, så fargene er de ekte."""
    return (nettsted / "stil.css").read_text(encoding="utf-8")


def _navn(rgb, palett):
    r, g, b = rgb
    return min(palett, key=lambda k: (r - palett[k][0]) ** 2
               + (g - palett[k][1]) ** 2 + (b - palett[k][2]) ** 2)


# TRE FARGER, TO BETYDNINGER. `--kart-hav` er sjø. Land males med to
# ulike farger i dag: `--papir2` er bakgrunnen kartet står på i
# tilstandsspalta, og `--kart-land` er fyllet i kartlagene. Begge
# BETYR land, og en prøve som bare kjente den ene ville talt sidens
# egen bakgrunn som feilmalt sjø — målt, og det var nettopp det som
# skjedde i første kjøring.
LANDFARGER = ("land", "papir")


def _palett(nettsted: pathlib.Path) -> dict:
    """{navn: rgb} fra stilarkets egne tokens, lysmodus."""
    css = _stil(nettsted)
    ut = {}
    for felt, navn in (("--kart-hav", "hav"), ("--kart-land", "land"),
                       ("--papir2", "papir")):
        m = re.search(rf"{felt}:\s*#([0-9a-fA-F]{{6}})", css)
        if not m:
            raise SystemExit(f"fant ikke {felt} i stil.css")
        h = m.group(1)
        ut[navn] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return ut


def _grensesone(rute: bytearray, bredde: int, hoyde: int,
                radius: int = 2) -> bytearray:
    """1 der fasiten skifter fra land til sjø innenfor `radius` piksler.

    HVOR FEILEN LIGGER er et annet spørsmål enn hvor mye det er av den.
    En kystlinje er lang, og et kart som treffer den på halvannen
    piksel har en feilstripe langs hele den — det er oppløsning, ikke
    en påstand om verden. En feil MIDT i en flate er det motsatte:
    der har kartet sagt sjø om land, eller land om sjø, uten at noen
    grense er i nærheten.
    """
    kant = bytearray(bredde * hoyde)
    for y in range(hoyde):
        rad = y * bredde
        for x in range(bredde):
            v = rute[rad + x]
            if (x and rute[rad + x - 1] != v) or (y and rute[rad - bredde + x] != v):
                kant[rad + x] = 1
    ut = bytearray(bredde * hoyde)
    for y in range(hoyde):
        for x in range(bredde):
            if not kant[y * bredde + x]:
                continue
            for dy in range(-radius, radius + 1):
                yy = y + dy
                if not (0 <= yy < hoyde):
                    continue
                for dx in range(-radius, radius + 1):
                    xx = x + dx
                    if 0 <= xx < bredde:
                        ut[yy * bredde + xx] = 1
    return ut


def main() -> int:
    nettsted = pathlib.Path(sys.argv[1])
    loknr = sys.argv[2:] or list(NI)
    print(f"Fasit mot {GML.name}")
    rammer = _rammer(loknr)
    sann = fasit(rammer)
    palett = _palett(nettsted)
    bilder = rasteriser(nettsted, list(rammer), _stil(nettsted))

    print(f"\n{'lokalitet':>10}  {'feilmalt':>9}  {'ved kysten':>11}  "
          f"{'inne i flata':>13}   {'som er land':>11}")
    verst = verst_inne = 0.0
    for nr, (proj, _lat, _lon) in rammer.items():
        bilde = bilder.get(nr)
        if bilde is None:
            print(f"{nr:>10}  {'(intet kart på sida)':>30}")
            continue
        bredde, hoyde, rader = bilde
        rute = sann[nr]
        b0, h0 = proj.bredde, int(proj.hoyde)
        sone = _grensesone(rute, b0, h0)
        feil = feil_inne = talt = land = 0
        for py in range(hoyde):
            rad = rader[py]
            ry = min(h0 - 1, py * h0 // hoyde)
            for px in range(bredde):
                rx = min(b0 - 1, px * b0 // bredde)
                i = ry * b0 + rx
                er_land = rute[i] == 1
                malt = _navn(rad[px], palett)
                talt += 1
                land += er_land
                if er_land != (malt in LANDFARGER):
                    feil += 1
                    if not sone[i]:
                        feil_inne += 1
        andel = 100 * feil / talt
        inne = 100 * feil_inne / talt
        verst = max(verst, andel)
        verst_inne = max(verst_inne, inne)
        print(f"{nr:>10}  {andel:8.2f} %  {andel-inne:10.2f} %  "
              f"{inne:12.2f} %   {100*land/talt:10.1f} %")
    print(f"\nverst: {verst:.2f} % totalt, {verst_inne:.2f} % inne i flata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
