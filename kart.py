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


class Projeksjon:
    """Grader til piksler i en `viewBox`, og ingenting annet.

    Utsnittet oppgis i grader; bredden i piksler. Høyden FØLGER av
    utsnittet framfor å oppgis, fordi et kart med en høyde noen har
    valgt er et kart med feil størrelsesforhold.
    """

    def __init__(self, lon_min: float, lat_min: float,
                 lon_maks: float, lat_maks: float,
                 bredde: int = 900, marg: int = 12):
        self.lon_min, self.lat_min = lon_min, lat_min
        self.lon_maks, self.lat_maks = lon_maks, lat_maks
        self.marg = marg
        self.k = math.cos(math.radians((lat_min + lat_maks) / 2))
        grader_b = (lon_maks - lon_min) * self.k or 1.0
        grader_h = (lat_maks - lat_min) or 1.0
        self.skala = (bredde - 2 * marg) / grader_b
        self.bredde = bredde
        self.hoyde = round(grader_h * self.skala + 2 * marg, 1)

    def x(self, lon: float) -> float:
        return round(self.marg + (lon - self.lon_min) * self.k * self.skala, 1)

    def y(self, lat: float) -> float:
        # y vokser nedover i SVG, breddegrad oppover.
        return round(self.marg + (self.lat_maks - lat) * self.skala, 1)

    def synlig(self, lon: float, lat: float) -> bool:
        return (self.lon_min <= lon <= self.lon_maks
                and self.lat_min <= lat <= self.lat_maks)


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
    """Punktlista som en SVG-`d`. Tom streng når det ikke er noe å tegne."""
    if len(punkter) < 2:
        return ""
    ledd = [f"M{punkter[0][0]} {punkter[0][1]}"]
    ledd += [f"L{x} {y}" for x, y in punkter[1:]]
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
    kanter = (("v", proj.lon_min - monn), ("h", proj.lon_maks + monn),
              ("n", proj.lat_min - monn), ("o", proj.lat_maks + monn))
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
    """Grader til `d`-strenger, klippet til utsnittet og forenklet.

    FORENKLINGEN SKJER I PIKSELROMMET og ikke i grader: en toleranse i
    grader forenkler Finnmark hardere enn Rogaland, mens en toleranse i
    piksler forenkler like mye overalt på det ferdige bildet.

    ALT SOM TEGNES HER ER RINGER — landflater og produksjonsområder —
    og de klippes med Sutherland-Hodgman, ikke med en linjedeler. Se
    `_flatekant()`.

    `klipp=False` når utsnittet uansett dekker hele geometrien: på
    oversiktskartet er rammen områdenes egen utstrekning, og en
    klipping der er arbeid uten virkning.
    """
    monn = (proj.lon_maks - proj.lon_min) * 0.05
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


def gradnett(proj: Projeksjon, steg_lat: int = 5, steg_lon: int = 5,
             etikett: bool = True) -> dict:
    """Linjene og etikettene. Tegnes bare der det faktisk er kart."""
    def trinn(fra: float, til: float, steg: int) -> list[int]:
        forste = int(math.ceil(fra / steg) * steg)
        return list(range(forste, int(til) + 1, steg))

    bredde = [{"y": proj.y(g), "grad": g, "etikett": f"{g}°N",
               "etikett_x": proj.bredde - 6,
               "etikett_y": round(proj.y(g) - 5, 1)}
              for g in trinn(proj.lat_min, proj.lat_maks, steg_lat)]
    lengde = []
    for g in trinn(proj.lon_min, proj.lon_maks, steg_lon):
        x = proj.x(g)
        sist = x > proj.bredde - 60
        lengde.append({"x": x, "grad": g, "etikett": f"{g}°Ø",
                       "etikett_x": round(x - 6 if sist else x + 6, 1),
                       "etikett_anker": "end" if sist else "start"})
    return {"bredde": bredde, "lengde": lengde,
            "etikett_y_bunn": round(proj.hoyde - 8, 1),
            "etiketter": etikett}


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
    lon_min = lat_min = 1e9
    lon_maks = lat_maks = -1e9
    for f in po["features"]:
        nr = str(f["properties"]["id"])
        per_nr[nr] = f
        for ring in _linjer(f["geometry"]):
            for x, y in ring:
                lon_min, lon_maks = min(lon_min, x), max(lon_maks, x)
                lat_min, lat_maks = min(lat_min, y), max(lat_maks, y)

    proj = Projeksjon(lon_min, lat_min, lon_maks, lat_maks, bredde=bredde)

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
            "baner": _tegn(_linjer(f["geometry"]), proj,
                           KYSTKART_TOLERANSE, lukket=True,
                           klipp=False),
        })

    # Landflatene dekker hele rammen her — rammen ER områdenes
    # utstrekning — så klippingen er arbeid uten virkning.
    land = _tegn(_linjer(_les(LAND)["features"][0]["geometry"]),
                 proj, KYSTKART_TOLERANSE, lukket=True, klipp=False)

    return {
        "bredde": proj.bredde,
        "hoyde": proj.hoyde,
        "omraader": flater,
        "mangler_geometri": [r["nr"] for r in omraader
                             if str(r["nr"]) not in per_nr],
        "land": land,
        "gitter": gradnett(proj),
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
POSISJON_TOLERANSE = 0.35   # piksler — finere enn oversikten, av samme
                            # grunn som at utsnittet er mindre
KM_PER_BREDDEGRAD = 111.32


def posisjonskart(breddegrad: object, lengdegrad: object,
                  bredde: int = POSISJON_BREDDE,
                  km: float = POSISJON_KM) -> dict | None:
    """Kartutsnittet rundt ett punkt, eller None uten koordinater.

    None og ikke et tomt kart: en ramme uten et punkt i er en ramme som
    later som om den har et innhold. Malen viser da ingenting, og siden
    sier i klartekst at koordinatene mangler — samme regel som
    `nettsted.lusegraf()`.
    """
    try:
        lat = float(str(breddegrad).strip())
        lon = float(str(lengdegrad).strip())
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    halv_lat = (km / 2) / KM_PER_BREDDEGRAD
    k = math.cos(math.radians(lat)) or 1e-6
    halv_lon = halv_lat / k
    proj = Projeksjon(lon - halv_lon, lat - halv_lat,
                      lon + halv_lon, lat + halv_lat,
                      bredde=bredde, marg=0)

    land = _tegn(_linjer(_les(LAND)["features"][0]["geometry"]),
                 proj, POSISJON_TOLERANSE, lukket=True)

    return {
        "bredde": proj.bredde,
        "hoyde": proj.hoyde,
        "land": land,
        # Gradnettet er FINERE her, og etikettene er av: et utsnitt på
        # 36 km rommer en tredjedels breddegrad, og «69°N» tvers over
        # bildet ville vært den eneste linja og dessuten i veien.
        "gitter": gradnett(proj, steg_lat=1, steg_lon=1, etikett=False),
        "x": proj.x(lon),
        "y": proj.y(lat),
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
