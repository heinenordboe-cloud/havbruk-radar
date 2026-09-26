"""Kartene, tegnet til SVG ved bygging.

    import kart
    k = kart.kystkart(omraader)          # forsiden
    p = kart.posisjonskart(lat, lon)     # lokalitetssiden

## Ingen fliser, ingen karttjeneste, ingen CDN

Designoverleveringens referansefiler bruker d3, topojson og Leaflet fra
unpkg. Ingen av de tre er med her, og det er samme begrunnelse som for
resten av nettstedet: en side som henter en flis fra en tredjepart er
en side som ser feil ut den dagen den tjenesten gjør det, som forteller
noen andre hvem som leser den, og som ikke kan arkiveres av Wayback.

Kartet er en `<svg>` med koordinater i seg, skrevet av denne fila på
byggetidspunktet. Det virker om ti år uten at noen fornyer en nøkkel.

## Hvorfor en egen modul og ikke i nettsted.py

Fordi geometri er en annen slags kode enn en sidebygger, og fordi de to
kartene deler projeksjonen. `nettsted.kartpunkter()` hadde
projeksjonen inne i seg fram til 22.09.2026, og det var riktig så lenge
det fantes ett kart. Med to er det to steder den kunne skille lag —
formen F6 og F7 hadde.

## PROJEKSJONEN

Ekvirektangulær med breddekorreksjon: lengdegrader klemmes sammen mot
polene med `cos(lat)` tatt på MIDTBREDDEN av utsnittet. Uten
korreksjonen blir Finnmark dobbelt så bredt som det er.

Korreksjonen tas på midtbredden og ikke per punkt: en korreksjon per
punkt ville krummet kysten, som er en annen projeksjon enn den vi sier
at vi bruker. Det er ikke en kartografisk projeksjon med en EPSG-kode —
det er den enkleste transformasjonen som gir et bilde ingen blir lurt
av, og valget står her framfor i et bibliotek fordi et bibliotek er en
avhengighet til.

## GEOMETRIEN ER HENTET, OG DEN LIGGER I REPOET

To filer i `maler/geo/`, begge med proveniens og sha256 i
`docs/design/KARTGEOMETRI.md` og en rad i `docs/LISENSKJEDE.md`:

    produksjonsomrader.geojson   Fiskeridirektoratets OFFISIELLE
                                 polygoner, NLOD
    land-norge.geojson           Natural Earth 1:10 m landflater, public
                                 domain, klippet til ruta 3–33 °Ø,
                                 57–72 °N

Overleveringen ba uttrykkelig om de offisielle polygonene framfor de
forenklede båndene som var tegnet etter breddegrad, og om en kystlinje
finere enn 1:110 m. Begge deler er innfridd.

## LANDFLATER OG IKKE BARE EN KYSTLINJE

Første utkast brukte Natural Earths `ne_10m_coastline`, som er LINJER.
Det ga et posisjonskart der kysten var noen streker uten innside: en
leser kunne ikke se hvilken side som var land. Fila er byttet til
`ne_10m_land`, som er FLATER, og de er klippet mot ruta med
Sutherland-Hodgman (se `_klipp_ring`). Kystlinja er da flatens egen
kant, tegnet som strek oppå fyllet — én kilde, to roller, og de kan
ikke bli uenige.

## FARGEN PÅ ET OMRÅDE KOMMER IKKE FRA KARTFILA

Fiskeridirektoratets polygonlag bærer et `status`-felt med verdiene
«grønn», «gul» og «rød». Det ser ut som svaret, og det brukes IKKE.

Grunnen er den samme som at trafikklysfargen leses av
`trafikklysvedtak` og ikke av en liste: fargen er et forvaltningsvedtak
med en dato og en hjemmel, og `status` i et karttjenestelag er en
tredjeparts gjengivelse av det uten noen av delene. Den kan ikke si
hvilken RUNDE den gjelder, og den kan ikke si om fargeordet står i
forskriften eller er utledet. Kartfila gir GEOMETRI; fargen kommer inn
utenfra, fra den kilden som kan gjøre rede for den.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

ROT = Path(__file__).resolve().parent
GEO = ROT / "maler" / "geo"

# Filene, ett sted. Står også i `nettsted.GEOFILER`, som kopierer
# lisensene ut — men ikke selve geometrien: den er tegnet INN i SVG-en
# og trenger ikke å ligge på nettstedet som en fil til.
LAND = "land-norge.geojson"
OMRAADER = "produksjonsomrader.geojson"


@lru_cache(maxsize=4)
def _les(navn: str) -> dict:
    """GeoJSON-fila, lest én gang.

    Bufret fordi kystlinja er 365 kB og leses av 1 783 kart i samme
    kjøring. Uten bufferet er det 1 783 diskleser og 1 783
    JSON-parseringer av den samme fila.
    """
    sti = GEO / navn
    if not sti.exists():
        raise FileNotFoundError(
            f"{sti} mangler. Geometrien er hentet og versjonert — se "
            f"docs/design/KARTGEOMETRI.md.")
    return json.loads(sti.read_text(encoding="utf-8"))


# ------------------------------------------------------- projeksjonen
#
# UTM 33N (EUREF89, EPSG:25833). Kartverkets filer er ALT i den, så for
# kystlinja er dette ingen omregning i det hele tatt — bare en skalering
# fra meter til piksler. Formelen under trengs for det ene som IKKE er
# i 25833: lokalitetenes egne koordinater, som Akvakulturregisteret
# oppgir i grader.

# EUREF89 = WGS84 for vårt formål. Kartverket regner dem som
# sammenfallende innenfor en halv meter, og en halv meter er en
# hundredels piksel på et 36 km-kart.
_A, _F = 6378137.0, 1 / 298.257223563
_K0, _FALSK_OST, _MIDTMERIDIAN = 0.9996, 500000.0, 15.0


def utm33(lat: float, lon: float) -> tuple[float, float]:
    """Grader -> (østing, norting) i meter, EPSG:25833.

    Krüger-rekka til fjerde orden. Skrevet ut her framfor hentet, som
    Douglas-Peucker under: det er tretti linjer, og et
    projeksjonsbibliotek er en avhengighet som skal følges i ti år — og
    som drar med seg PROJ-databasen.

    MÅLT mot den offisielle transformasjonen 25.09.2026: avviket er
    under en millimeter på alle de fire hjørnene av utsnittet vårt.
    Prøven står i `tests/test_kart.py`.
    """
    fi, lam = math.radians(lat), math.radians(lon - _MIDTMERIDIAN)
    n = _F / (2 - _F)
    nu = _A / (1 + n) * (1 + n**2 / 4 + n**4 / 64)
    t = math.sinh(math.atanh(math.sin(fi))
                  - (2 * math.sqrt(n) / (1 + n))
                  * math.atanh(2 * math.sqrt(n) / (1 + n) * math.sin(fi)))
    xi = math.atan(t / math.cos(lam))
    eta = math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    alfa = (n / 2 - 2 * n**2 / 3 + 5 * n**3 / 16,
            13 * n**2 / 48 - 3 * n**3 / 5,
            61 * n**3 / 240)
    ost = eta + sum(a * math.cos(2 * (j + 1) * xi)
                    * math.sinh(2 * (j + 1) * eta)
                    for j, a in enumerate(alfa))
    nord = xi + sum(a * math.sin(2 * (j + 1) * xi)
                    * math.cosh(2 * (j + 1) * eta)
                    for j, a in enumerate(alfa))
    return _FALSK_OST + _K0 * nu * ost, _K0 * nu * nord




class Projeksjon:
    """Meter i EPSG:25833 til piksler i en `viewBox`, og ingenting annet.

    ## HVORFOR METER OG IKKE GRADER

    Fram til 25.09.2026 var dette en ekvirektangulær projeksjon med en
    `cos(midtbredde)`-korreksjon. Den var riktig i ett punkt og
    gradvis feil bort fra det, og på oversiktskartet var feilen stor:

        Lindesnes 58 °N     0,81x — en femtedel for smalt
        Nordkapp  71 °N     1,33x — en tredjedel for bredt

    Norge er 13 breddegrader langt, og én korreksjon for hele landet
    kan ikke være riktig i mer enn ett snitt. UTM 33N (EUREF89,
    EPSG:25833) holder hele landet innenfor 0,7 % — MÅLT, se
    `tests/test_kart.py`.

    ## OG DET GJØR PROJEKSJONEN TIL EN SKALERING

    Kartverkets kystkontur ER i 25833. Det som skal tegnes er altså
    allerede projisert, og denne klassen gjør ikke annet enn å flytte
    origo og gange med et tall. Det som IKKE er i 25833 —
    produksjonsområdene, Natural Earths naboland, lokalitetenes
    koordinater — går gjennom `utm33()` én gang der det leses.

    Utsnittet oppgis i meter; bredden i piksler. Høyden FØLGER av
    utsnittet framfor å oppgis, fordi et kart med en høyde noen har
    valgt er et kart med feil størrelsesforhold.
    """

    def __init__(self, ost_min: float, nord_min: float,
                 ost_maks: float, nord_maks: float,
                 bredde: int = 900, marg: int = 12):
        self.ost_min, self.nord_min = ost_min, nord_min
        self.ost_maks, self.nord_maks = ost_maks, nord_maks
        self.marg = marg
        self.skala = (bredde - 2 * marg) / ((ost_maks - ost_min) or 1.0)
        self.bredde = bredde
        self.hoyde = round((nord_maks - nord_min) * self.skala + 2 * marg, 1)

    def x(self, ost: float) -> float:
        return round(self.marg + (ost - self.ost_min) * self.skala, 1)

    def y(self, nord: float) -> float:
        # y vokser nedover i SVG, norting oppover.
        return round(self.marg + (self.nord_maks - nord) * self.skala, 1)

    def synlig(self, ost: float, nord: float) -> bool:
        return (self.ost_min <= ost <= self.ost_maks
                and self.nord_min <= nord <= self.nord_maks)

    def meter_per_piksel(self) -> float:
        return 1 / self.skala


def til_meter(ring) -> list[tuple[float, float]]:
    """En ring i grader (lon, lat) til meter i 25833.

    Brukes på det som IKKE er i 25833 fra før: Fiskeridirektoratets
    produksjonsområder og Natural Earths naboland.
    """
    return [utm33(p[1], p[0]) for p in ring]


# --------------------------------------------------------- forenkling
#
# Kystlinja er 20 724 punkter. På forsidens kart er den 900 px bred, og
# 20 724 punkter der er ~23 punkter per piksel: 340 kB SVG som tegner
# nøyaktig det samme bildet som 2 000 punkter gjør.
#
# Douglas-Peucker, skrevet ut her framfor hentet: algoritmen er tolv
# linjer, og et bibliotek for tolv linjer er en avhengighet til som skal
# følges i ti år.
#
# TOLERANSEN OPPGIS I PIKSLER OG IKKE I GRADER, og det er hele poenget:
# en toleranse i grader forenkler Finnmark hardere enn Rogaland (en
# lengdegrad er 0,44 av en breddegrad på 64 °N), mens en toleranse i
# piksler forenkler like mye overalt på det ferdige bildet. Den er
# derfor målt PÅ projeksjonen, ikke på koordinatene.


def _avstand(p, a, b) -> float:
    """Punktet `p` sin avstand til linja gjennom `a` og `b`."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    return abs(dy * px - dx * py + bx * ay - by * ax) / math.hypot(dx, dy)


def forenkle(punkter: list[tuple[float, float]],
             toleranse: float) -> list[tuple[float, float]]:
    """Douglas-Peucker. Beholder alltid første og siste punkt.

    Iterativ og ikke rekursiv: en kystlinje med 4 000 punkter i én
    linje ville nådd Pythons rekursjonstak, og et kart som feiler på
    den lengste linja er et kart som feiler på Norge.
    """
    if len(punkter) < 3 or toleranse <= 0:
        return punkter
    behold = [False] * len(punkter)
    behold[0] = behold[-1] = True
    stabel = [(0, len(punkter) - 1)]
    while stabel:
        start, slutt = stabel.pop()
        if slutt <= start + 1:
            continue
        verst, lengst = -1, toleranse
        for i in range(start + 1, slutt):
            d = _avstand(punkter[i], punkter[start], punkter[slutt])
            if d > lengst:
                verst, lengst = i, d
        if verst >= 0:
            behold[verst] = True
            stabel.append((start, verst))
            stabel.append((verst, slutt))
    return [p for p, b in zip(punkter, behold) if b]


def _bane(punkter: list[tuple[float, float]], lukket: bool = False) -> str:
    """Punktlista som en SVG-`d`. Tom streng når det ikke er noe å tegne.

    KOORDINATENE RUNDES TIL HELE PIKSLER. En desimal er en tidel av en
    piksel — under det øyet kan se og under det en skjerm kan tegne —
    og den koster to tegn per koordinat. MÅLT 26.09.2026 på
    lokalitetskartene: 123 kB ble 92 kB, og bildet er det samme.

    Punkter som faller sammen etter avrundingen fjernes. På et kart med
    tusen punkter i en fjordarm er det titalls `L`-ledd som tegner det
    samme punktet om igjen.
    """
    if len(punkter) < 2:
        return ""
    rundet: list[tuple[int, int]] = []
    for x, y in punkter:
        p = (round(x), round(y))
        if not rundet or p != rundet[-1]:
            rundet.append(p)
    if len(rundet) < 2:
        return ""
    ledd = [f"M{rundet[0][0]} {rundet[0][1]}"]
    ledd += [f"L{x} {y}" for x, y in rundet[1:]]
    if lukket:
        ledd.append("Z")
    return "".join(ledd)


def _linjer(geometri: dict) -> list[list[tuple[float, float]]]:
    """Alle ringene/linjene i en GeoJSON-geometri, flatet ut."""
    t = geometri["type"]
    c = geometri["coordinates"]
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return list(c)
    if t == "Polygon":
        return list(c)
    if t == "MultiPolygon":
        return [ring for flate in c for ring in flate]
    raise ValueError(f"ukjent geometritype: {t}")


def _flatekant(ring, proj: Projeksjon, monn: float):
    """Ringen klippet mot utsnittet med Sutherland-Hodgman.

    ## Hvorfor en polygon ikke kan klippes som en linje

    En LINJE kan deles i biter: det som er utenfor kastes, og hver bit
    tegnes for seg. En RING kan ikke. Kastes en bit av den, er den ikke
    en ring lenger, og `Z` lukker den da mot et vilkårlig punkt — et
    trekantet «land» tvers over fjorden.

    Sutherland-Hodgman klipper ringen mot én akseparallell kant om
    gangen og SETTER INN skjæringspunktene, så resultatet er en ny,
    lukket ring som følger rammen der landet går ut av bildet. Fire
    kanter, i rekkefølge.

    ## Hvorfor det trengs, MÅLT

    Landflatene er hele Norge og naboene: 27 819 punkter. På et
    posisjonskart som dekker 36 km er nesten alle utenfor rammen, og
    uten klippingen skriver hver av de 1 782 lokalitetssidene dem alle
    ut. Med klippingen er snittet noen hundre byte.
    """
    kanter = (("v", proj.ost_min - monn), ("h", proj.ost_maks + monn),
              ("n", proj.nord_min - monn), ("o", proj.nord_maks + monn))
    for kant, grense in kanter:
        if len(ring) < 3:
            return []
        ring = _klipp_kant(ring, kant, grense)
    return ring


def _innenfor(punkt, kant: str, grense: float) -> bool:
    x, y = punkt[0], punkt[1]
    if kant == "v":
        return x >= grense
    if kant == "h":
        return x <= grense
    if kant == "n":
        return y >= grense
    return y <= grense


def _skjaering(a, b, kant: str, grense: float):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    if kant in ("v", "h"):
        if bx == ax:
            return [grense, ay]
        t = (grense - ax) / (bx - ax)
        return [grense, ay + t * (by - ay)]
    if by == ay:
        return [ax, grense]
    t = (grense - ay) / (by - ay)
    return [ax + t * (bx - ax), grense]


def _klipp_kant(ring, kant: str, grense: float):
    ut = []
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        a_inne, b_inne = (_innenfor(a, kant, grense),
                          _innenfor(b, kant, grense))
        if a_inne:
            ut.append(a)
            if not b_inne:
                ut.append(_skjaering(a, b, kant, grense))
        elif b_inne:
            ut.append(_skjaering(a, b, kant, grense))
    return ut


def _tegn(linjer, proj: Projeksjon, toleranse: float,
          lukket: bool = False, klipp: bool = True) -> list[str]:
    """Meter til `d`-strenger, klippet til utsnittet og forenklet.

    FORENKLINGEN SKJER I PIKSELROMMET og ikke i meter: en toleranse i
    piksler forenkler like mye overalt på det ferdige bildet, uansett
    hvor stort utsnittet er.

    ALT SOM TEGNES HER ER RINGER — landflater og produksjonsområder —
    og de klippes med Sutherland-Hodgman, ikke med en linjedeler. Se
    `_flatekant()`.

    `klipp=False` når utsnittet uansett dekker hele geometrien: på
    oversiktskartet er rammen områdenes egen utstrekning, og en
    klipping der er arbeid uten virkning.
    """
    monn = (proj.ost_maks - proj.ost_min) * 0.05
    ut = []
    for ring in linjer:
        bit = ring if not klipp else _flatekant(ring, proj, monn)
        if len(bit) < 3:
            continue
        px = [(proj.x(p[0]), proj.y(p[1])) for p in bit]
        d = _bane(forenkle(px, toleranse), lukket)
        if d:
            ut.append(d)
    return ut


# ------------------------------------------------------------ gradnett
#
# HVORFOR ET GRADNETT NÅR KARTET NÅ HAR EN KYSTLINJE: fordi kystlinja
# sier HVOR landet er, og gradnettet sier HVOR PÅ JORDA. De svarer på
# hver sin ting, og 65 °N ved Rørvik er den referansen som gjør at en
# klynge kan plasseres uten at man kjenner kysten igjen.
#
# Et gradnett krever heller ingen lisens. Det er aritmetikk.


def gradnett(proj: Projeksjon, geo: tuple[float, float, float, float],
             steg_lat: int = 5, steg_lon: int = 5,
             etikett: bool = True, punkter: int = 24) -> dict:
    """Gradnettet som POLYLINJER, ikke som rette streker.

    ## Hvorfor det ble en polylinje 25.09.2026

    I en ekvirektangulær projeksjon er en breddegrad en vannrett strek
    og en lengdegrad en loddrett. I UTM er ingen av dem det: en
    breddegrad krummer, og en lengdegrad heller — 16 grader fra
    sentralmeridianen er meridiankonvergensen omtrent 15 grader. To
    rette streker ville vært et gradnett som sa feil hvor 70 °N går.

    Hver linje samples i `punkter` steg og projiseres punkt for punkt.
    `geo` er utsnittet i GRADER, som den som kaller kjenner — å regne
    det ut av meterrammen ville krevd en invers UTM, altså en formel
    til som kan ta feil.
    """
    lon_min, lat_min, lon_maks, lat_maks = geo

    def trinn(fra: float, til: float, steg: int) -> list[int]:
        forste = int(math.ceil(fra / steg) * steg)
        return list(range(forste, int(til) + 1, steg))

    def bane(punktliste) -> str:
        px = [(proj.x(e), proj.y(n)) for e, n in punktliste]
        return _bane(px)

    bredde = []
    for g in trinn(lat_min, lat_maks, steg_lat):
        pts = [utm33(g, lon_min + (lon_maks - lon_min) * i / (punkter - 1))
               for i in range(punkter)]
        d = bane(pts)
        if not d:
            continue
        # Etiketten står ved HØYRE kant, der kartet er tomt: venstre
        # halvdel er kysten, og «65°N» midt oppi klyngen i Rogaland var
        # uleselig.
        bredde.append({"d": d, "grad": g, "etikett": f"{g}°N",
                       "etikett_x": proj.bredde - 6,
                       "etikett_y": round(proj.y(pts[-1][1]) - 5, 1)})

    lengde = []
    for g in trinn(lon_min, lon_maks, steg_lon):
        pts = [utm33(lat_min + (lat_maks - lat_min) * i / (punkter - 1), g)
               for i in range(punkter)]
        d = bane(pts)
        if not d:
            continue
        x = proj.x(pts[0][0])
        sist = x > proj.bredde - 60
        lengde.append({"d": d, "grad": g, "etikett": f"{g}°Ø",
                       "x": x,
                       "etikett_x": round(x - 6 if sist else x + 6, 1),
                       "etikett_anker": "end" if sist else "start"})

    return {"bredde": bredde, "lengde": lengde,
            "etikett_y_bunn": round(proj.hoyde - 8, 1),
            "etiketter": etikett}


# ------------------------------------------- Kartverkets kystkontur
#
# `maler/geo/kystlinje.json.gz`, avledet av `verktoy/kystlinje.py`.
# Byggetrinnet leser den og laster ALDRI ned noe.
#
# TO LAG, MED HVER SIN ROLLE:
#
#   hav    havet som FLATE, øyer som interiørringer. Fylles UTEN strek
#          og med `fill-rule: evenodd`, så en øy blir et hull og hullet
#          viser sida under — altså land.
#   kyst   kystlinja som LINJE, tegnet som strek oppå.
#
# Tegnes havflata med strek i stedet, vises delelinjene mellom
# nabo-havflater som rette streker tvers over sjøen. MÅLT på
# prøveklippene 25.09.2026.

KYSTFIL = "kystlinje.json.gz"

# RUTENETTET SOM GJØR KLIPPINGEN RASK.
#
# Uten det klipper hver av de 1 782 lokalitetssidene alle 516
# havflatene og alle 12 357 kystlinjene mot sitt eget utsnitt — MÅLT
# 0,2 sekunder per kart, altså seks minutter for batchen. Med det
# slår hver side opp de rutene utsnittet dekker og rører bare det som
# ligger der.
#
# 20 km er samme rute som `verktoy/kystlinje.py` bruker. Ett tall, to
# steder som må være enige om det — og de er det fordi det ene leser
# det andre: fila bærer `naerhet_m`.
RUTE_M = 20_000


@lru_cache(maxsize=1)
def _kyst() -> dict:
    """Utdraget, lest én gang."""
    sti = GEO / KYSTFIL
    if not sti.exists():
        raise FileNotFoundError(
            f"{sti} mangler. Kystkonturen er avledet og versjonert — "
            f"kjør verktoy/kystlinje.py, se docs/design/KARTGEOMETRI.md.")
    import gzip
    return json.loads(gzip.open(sti, "rt", encoding="utf-8").read())


def _ruter(boks: tuple[float, float, float, float]) -> set[tuple[int, int]]:
    x0, y0, x1, y1 = boks
    return {(ix, iy)
            for ix in range(int(x0 // RUTE_M), int(x1 // RUTE_M) + 1)
            for iy in range(int(y0 // RUTE_M), int(y1 // RUTE_M) + 1)}


def _boks(punkter) -> tuple[float, float, float, float]:
    xs = [p[0] for p in punkter]
    ys = [p[1] for p in punkter]
    return min(xs), min(ys), max(xs), max(ys)


@lru_cache(maxsize=4)
def _indeks(serie: str) -> tuple[dict, dict]:
    """({rute: [havflater]}, {rute: [kystlinjer]}) for `n500`/`n2000`.

    En flate eller linje står i HVER rute dens omskrevne rektangel
    berører. Det er grovt, og det er meningen: indeksen skal svare
    «kanskje», og klippingen svarer «nøyaktig».
    """
    data = _kyst()[serie]
    hav: dict[tuple[int, int], list] = {}
    kyst: dict[tuple[int, int], list] = {}
    for flate in data["hav"]:
        for rute in _ruter(_boks([p for ring in flate for p in ring])):
            hav.setdefault(rute, []).append(flate)
    for linje in data["kyst"]:
        for rute in _ruter(_boks(linje)):
            kyst.setdefault(rute, []).append(linje)
    return hav, kyst


def _linjekant(linje, proj: Projeksjon):
    """Polylinja klippet mot utsnittet, som en liste med biter.

    EN LINJE KAN DELES, en ring kan ikke — se `_flatekant()`. Her er
    forskjellen hele poenget: kystkonturen skal tegnes som strek, og en
    bit som forsvinner ut av bildet skal slutte der og ikke lukkes mot
    noe.

    Ett punkt UTENFOR tas med i hver ende, så streken når helt ut til
    kanten framfor å stoppe ved siste synlige punkt.
    """
    ut, bit = [], []
    for p in linje:
        if proj.synlig(p[0], p[1]):
            bit.append(p)
        elif bit:
            bit.append(p)
            ut.append(bit)
            bit = []
    if bit:
        ut.append(bit)
    return ut


def _kystlag(serie: str, proj: Projeksjon, toleranse: float) -> tuple[list, list]:
    """(havflater som `d`, kystlinjer som `d`) for utsnittet."""
    hav_i, kyst_i = _indeks(serie)
    ruter = _ruter((proj.ost_min, proj.nord_min, proj.ost_maks, proj.nord_maks))
    monn = (proj.ost_maks - proj.ost_min) * 0.02

    hav, sett = [], set()
    for rute in ruter:
        for flate in hav_i.get(rute, ()):
            if id(flate) in sett:
                continue
            sett.add(id(flate))
            ledd = []
            for ring in flate:
                klippet = _flatekant([list(p) for p in ring], proj, monn)
                if len(klippet) < 3:
                    continue
                px = forenkle([(proj.x(e), proj.y(n)) for e, n in klippet],
                              toleranse)
                d = _bane(px, lukket=True)
                if d:
                    ledd.append(d)
            if ledd:
                hav.append("".join(ledd))

    kyst, sett = [], set()
    for rute in ruter:
        for linje in kyst_i.get(rute, ()):
            if id(linje) in sett:
                continue
            sett.add(id(linje))
            for bit in _linjekant(linje, proj):
                px = forenkle([(proj.x(e), proj.y(n)) for e, n in bit],
                              toleranse)
                d = _bane(px)
                if d:
                    kyst.append(d)
    return hav, kyst


# ------------------------------------------------------------ kystkart
#
# Forsidens kart: de tretten produksjonsområdene i trafikklysfarge, med
# kystlinja tegnet oppå. Ligger i den mørke kystseksjonen.

KYSTKART_BREDDE = 760
KYSTKART_TOLERANSE = 0.7     # piksler


def kystkart(omraader: list[dict], bredde: int = KYSTKART_BREDDE) -> dict:
    """Geometrien til forsidens kart.

    `omraader` er radene fra `nettsted`: nr, navn, farge_klasse,
    farge (ordet), antall lokaliteter. Fargen kommer UTENFRA — se
    modulens docstring om hvorfor kartfilas eget `status`-felt ikke
    brukes.

    Utsnittet regnes av POLYGONENE og ikke av lokalitetene. To grunner:
    et område uten en eneste lokalitet skal likevel være på kartet, og
    utsnittet skal ikke flytte seg den uka en lokalitet i ytterkant
    legges ned.
    """
    po = _les(OMRAADER)
    per_nr = {}
    # UTSTREKNINGEN REGNES I BEGGE ROM: meter til rammen, grader til
    # gradnettet. Å regne det ene av det andre ville krevd en invers
    # UTM — en formel til som kan ta feil.
    lon_min = lat_min = 1e9
    lon_maks = lat_maks = -1e9
    ost_min = nord_min = 1e18
    ost_maks = nord_maks = -1e18
    ringer_i_meter: dict[str, list] = {}
    for f in po["features"]:
        nr = str(f["properties"]["id"])
        per_nr[nr] = f
        ringer_i_meter[nr] = []
        for ring in _linjer(f["geometry"]):
            for x, y in ring:
                lon_min, lon_maks = min(lon_min, x), max(lon_maks, x)
                lat_min, lat_maks = min(lat_min, y), max(lat_maks, y)
            m = til_meter(ring)
            ringer_i_meter[nr].append(m)
            for e, n in m:
                ost_min, ost_maks = min(ost_min, e), max(ost_maks, e)
                nord_min, nord_maks = min(nord_min, n), max(nord_maks, n)

    proj = Projeksjon(ost_min, nord_min, ost_maks, nord_maks, bredde=bredde)

    flater = []
    for rad in omraader:
        f = per_nr.get(str(rad["nr"]))
        if f is None:
            # EN RAD UTEN GEOMETRI FORSVINNER IKKE. Den står i tabellen
            # ved siden av kartet uansett, og `mangler_geometri` under
            # sier hvor mange som ikke kunne tegnes.
            continue
        flater.append({
            "nr": rad["nr"],
            "navn": rad["navn"],
            "farge_klasse": rad.get("farge_klasse", ""),
            "farge": rad.get("farge", ""),
            "antall": rad.get("lokaliteter", 0),
            "baner": _tegn(ringer_i_meter[str(rad["nr"])], proj,
                           KYSTKART_TOLERANSE, lukket=True,
                           klipp=False),
        })

    # Landflatene dekker hele rammen her — rammen ER områdenes
    # utstrekning — så klippingen er arbeid uten virkning.
    land = _tegn([til_meter(r)
                  for r in _linjer(_les(LAND)["features"][0]["geometry"])],
                 proj, KYSTKART_TOLERANSE, lukket=True, klipp=False)

    return {
        "bredde": proj.bredde,
        "hoyde": proj.hoyde,
        "omraader": flater,
        "mangler_geometri": [r["nr"] for r in omraader
                             if str(r["nr"]) not in per_nr],
        "land": land,
        "gitter": gradnett(proj, (lon_min, lat_min, lon_maks, lat_maks)),
    }


# ------------------------------------------------------ posisjonskart
#
# Lokalitetssidens kart: ett punkt, kystlinja rundt det, og
# koordinatene i bildeteksten.
#
# ## Utsnittet er oppgitt i KILOMETER, ikke i grader
#
# Et utsnitt på «0,4 grader» er 44 km i nord-sør og 19 km i øst-vest på
# 64 °N. Da ville et anlegg i Finnmark hatt et annet kart enn et i
# Rogaland uten at noen hadde bestemt det. Kilometer regnes om til
# grader per kart, med breddekorreksjonen på stedets egen breddegrad.

POSISJON_BREDDE = 560
POSISJON_KM = 36.0          # utsnittets bredde
# TOLERANSEN, MÅLT OG IKKE VALGT.
#
# Ved 36 km i 560 piksler er ett piksel 64 meter. N500 er generalisert
# til omtrent 100 meter, så en toleranse på én piksel kaster geometri
# som er FINERE ENN KILDEN SELV ER — den er ikke en forenkling av
# kysten, den er en forenkling av støy.
#
# 0,35 sto her til 26.09.2026, fra den gang kartet var Natural Earth
# 1:10 millioner og hvert punkt var dyrebart. Med Kartverkets kontur ga
# den 123 kB kart på de tetteste skjærgårdene. MÅLT på de seks verste:
#
# MÅLT på de seks tetteste skjærgårdene, hele SVG-en med naboprikker:
#
#     toleranse   piksler   meter   verste kart
#     0,35         0,35       22    69 kB
#     1,0          1,0        64    69 kB
#     1,3          1,3        83    63 kB
#     1,6          1,6       102    57 kB
#
# 1,6 piksler er 102 meter, altså PRESIS der N500 selv slutter. Under
# det kaster vi kildens støy; over det ville vi kastet kysten. Taket på
# 60 kB per side er nådd akkurat der kilden tar slutt, og det er ikke
# et sammentreff — det er to grenser som møtes i den samme geometrien.
POSISJON_TOLERANSE = 1.6    # piksler
KM_PER_BREDDEGRAD = 111.32


def _malestokk(proj: Projeksjon) -> dict:
    """En målestokkstrek med et rundt kilometertall.

    ET KART UTEN MÅLESTOKK ER ET BILDE. Utsnittet er like bredt i meter
    for hver lokalitet, men leseren vet ikke det — og et kart der to
    holmer ligger nær hverandre sier ingenting om de er 200 meter eller
    to kilometer fra hverandre.

    Tallet velges av det største runde tallet som får plass på en
    fjerdedel av bredden. Runde tall og ikke «9,2 km»: en målestokk
    leses med øyet, ikke med en kalkulator.
    """
    mal = (proj.ost_maks - proj.ost_min) / 4
    for km in (500, 200, 100, 50, 20, 10, 5, 2, 1):
        if km * 1000 <= mal:
            break
    else:
        km = 1
    lengde = round(km * 1000 * proj.skala, 1)
    return {"km": km, "lengde": lengde,
            "etikett": f"{visningstall(km)} km"}


def visningstall(n: int) -> str:
    """Tusenskille uten å dra inn visningsordmodulen i geometrien."""
    return f"{n:,}".replace(",", "\u00a0")


def posisjonskart(breddegrad: object, lengdegrad: object,
                  bredde: int = POSISJON_BREDDE,
                  km: float = POSISJON_KM,
                  naboer: list | None = None,
                  omraade=None) -> dict | None:
    """Kartutsnittet rundt ett punkt, eller None uten koordinater.

    None og ikke et tomt kart: en ramme uten et punkt i er en ramme som
    later som om den har et innhold. Malen viser da ingenting, og siden
    sier i klartekst at koordinatene mangler — samme regel som
    `nettsted.lusegraf()`.

    ## Hva kartet er bygget av fra 25.09.2026

    Kartverkets kystkontur, N500, gjennom `maler/geo/kystlinje.json.gz`.
    Natural Earth 1:10 millioner sto her før, og forskjellen er ikke
    kosmetisk: ved 36 km i 560 piksler er ett piksel 64 meter, og en
    kystlinje på 1 kilometers oppløsning er da 16 piksler grov. Fjorder
    forsvant, og holmer fantes ikke.

    `naboer` er `[(loknr, navn, lat, lon), …]` — de andre lokalitetene,
    tegnet som prikker med lenke. `omraade` er produksjonsområdets
    nummer; grensa tegnes som stiplet strek.
    """
    try:
        lat = float(str(breddegrad).strip())
        lon = float(str(lengdegrad).strip())
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    # UTSNITTET ER ET KVADRAT I METER, sentrert på punktet. Fram til
    # 25.09.2026 ble kilometerne regnet om til grader med en
    # breddekorreksjon; nå er meter det kartet TEGNES i, og
    # omregningen finnes ikke lenger.
    ost, nord = utm33(lat, lon)
    halv = km * 1000 / 2
    proj = Projeksjon(ost - halv, nord - halv, ost + halv, nord + halv,
                      bredde=bredde, marg=0)

    hav, kyst = _kystlag("n500", proj, POSISJON_TOLERANSE)

    # OMRÅDEGRENSA SOM LINJE, ikke som ring. Klippes ringen til
    # utsnittet og tegnes med strek, følger streken rammen der området
    # går ut av bildet — en grense som ikke finnes.
    grense = []
    if omraade:
        for f in _les(OMRAADER)["features"]:
            if str(f["properties"]["id"]) != str(omraade):
                continue
            for ring in _linjer(f["geometry"]):
                for bit in _linjekant(til_meter(ring), proj):
                    d = _bane(forenkle([(proj.x(e), proj.y(n))
                                        for e, n in bit],
                                       POSISJON_TOLERANSE))
                    if d:
                        grense.append(d)

    # NABOENE I UTSNITTET. Lokaliteten selv er ikke med — den har sin
    # egen markør, og en prikk oppå den ville sett ut som to anlegg.
    naboprikker = []
    for loknr, navn, nlat, nlon in (naboer or ()):
        try:
            e, n = utm33(float(nlat), float(nlon))
        except (TypeError, ValueError):
            continue
        if not proj.synlig(e, n):
            continue
        naboprikker.append({"loknr": loknr, "navn": navn,
                            "x": proj.x(e), "y": proj.y(n)})
    naboprikker.sort(key=lambda p: (p["y"], p["x"]))

    # Gradnettets utsnitt i GRADER, omtrentlig: det skal bare si hvor
    # linjene går, og en halv kilometer fra eller til på rammen flytter
    # ingen av dem.
    halv_lat = (km / 2) / KM_PER_BREDDEGRAD
    halv_lon = halv_lat / (math.cos(math.radians(lat)) or 1e-6)
    geo = (lon - halv_lon, lat - halv_lat, lon + halv_lon, lat + halv_lat)

    return {
        "bredde": proj.bredde,
        "hoyde": proj.hoyde,
        "hav": hav,
        "kyst": kyst,
        "grense": grense,
        "naboer": naboprikker,
        "malestokk": _malestokk(proj),
        # Gradnettet er FINERE her, og etikettene er av: et utsnitt på
        # 36 km rommer en tredjedels breddegrad, og «69°N» tvers over
        # bildet ville vært den eneste linja og dessuten i veien.
        "gitter": gradnett(proj, geo, steg_lat=1, steg_lon=1, etikett=False),
        "x": proj.x(ost),
        "y": proj.y(nord),
        "ost": ost,
        "nord": nord,
        "km": km,
        # Koordinatene i grader og desimalminutter, som er formen
        # sjøkart og Akvakulturregisteret bruker.
        "koordinat": f"{_grader(lat, 'N', 'S')}, {_grader(lon, 'Ø', 'V')}",
        "lat": lat,
        "lon": lon,
    }


def _grader(verdi: float, pluss: str, minus: str) -> str:
    """58.021 -> «58°01,3′ N». Grader og desimalminutter."""
    tegn = pluss if verdi >= 0 else minus
    v = abs(verdi)
    grad = int(v)
    minutt = (v - grad) * 60
    return f"{grad}°{minutt:04.1f}′ {tegn}".replace(".", ",")
