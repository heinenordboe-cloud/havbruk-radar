"""Reguleringsområder (Havforskningsinstituttet) — 28 forslåtte områder.

Verifisert mot levende tjenester 09.09.2026. Alt i denne docstringen er
MÅLT mot de nedlastede kroppene, ikke lest ut av dokumentasjon.

HI har foreslått å dele de 13 produksjonsområdene i 28
reguleringsområder for utslipp av lakselus. Forslaget er et RÅD til
Nærings- og fiskeridepartementet, avgitt 29.06.2026. Det er ikke
forskrift, og ingen vet hvilken form det som eventuelt vedtas får.

To endepunkt, og kilden henter BEGGE:

    geojson   https://ftp.nmdc.no/nmdc/IMR/Smittepress/regomr.geojson
    rapport   https://www.hi.no/hi/nettrapporter/
                  rapport-fra-havforskningen-2026-28

DOI for datasettet: https://doi.org/10.21335/NMDC-1923112433

## Hvorfor begge, og hva sammenligningen viste

Rapportens appendiks 7.1 bærer de samme 28 polygonene som WKT.
Geojson-fila og appendikset er to uavhengige framstillinger av samme
grense, utgitt samme dag av samme miljø, og de kan sjekkes mot
hverandre uten å spørre noen.

Målt 09.09.2026, alle 28 områder:

  - Navnene er identiske i de to: 1A, 1B, 2A, 3A, 3B, 4A-4D, 5A, 5B,
    6A, 6B, 7A, 7B, 8A, 8B, 9A, 10A, 10B, 11A, 11B, 12A-12D, 13A, 13B.
  - Punktene er identiske, hjørne for hjørne, i ALLE 28, når to
    forskjeller i FORMAT er regnet inn:

        WKT er avrundet til 5 desimaler; geojson har full flyttalls-
        presisjon. `round(4.372435319571625, 5) == 4.37244`.

        WKT gjentar sluttpunktet én gang for mye. Ringen er lukket
        (siste punkt == første) OG har så en ekstra kopi av det
        punktet på slutten. Det gjelder 28 av 28, altså formatet og
        ikke en feil i noen av dem.

    Etter avrunding og fjerning av det duplikatet: null avvik.

Det er derfor GEOJSON-fila som lagres — den har presisjonen — og
appendikset som brukes som kontroll. `geometri_bekreftet` bærer
resultatet av kontrollen på hver rad, slik at en senere leser ser om
den ble gjort og hva den sa.

WKT-en i appendikset er ikke standard WKT: den skriver
`POLYGON((x, y), (x, y), ...)` med hvert punkt i egen parentes og komma
mellom x og y, der standarden er `POLYGON((x y, x y, ...))`. Parseren
her er tolerant med vilje — den leter etter talpar, ikke etter syntaks.

## Koordinatrekkefølgen er VERIFISERT, ikke antatt

Geojson-standarden sier lengdegrad først, men en fil kan bryte den, og
en snudd rekkefølge ville gitt en punkt-i-polygon-analyse som feiler
stille for alle punkter i stedet for åpenbart for ett.

To uavhengige prøver, begge kjørt 09.09.2026:

  1. Verdiområdet. Første koordinat spenner 4,362-31,218, den andre
     57,942-71,202. Norge ligger på 4-31 °Ø og 58-71 °N. Andre
     koordinat KAN ikke være en norsk lengdegrad — 71 °Ø er Vest-Sibir.
  2. Kjent posisjon. Ålesund havn (62,4722 °N / 6,1495 °Ø) faller i
     reguleringsområde 5A, som ligger inni produksjonsområde 5 (Stadt
     til Hustadvika) — der Ålesund faktisk er. Med snudd rekkefølge
     (62,47 °Ø / 6,15 °N) faller punktet utenfor alle 28: det ligger
     i Indiahavet.

Og den tredje, som er Del C sin egen: 969 av akvakulturregisterets
lokaliteter har produksjonsområdekode fra Fiskeridirektoratet. Faller
de i et reguleringsområde med SAMME tall, er begge sider bekreftet på
én gang. Se docs/ANALYSE-REGULERINGSOMRAADER.md.

## `status = "forslag"` — en 1b-3-verdi

Feltet avgjør hva radene BETYR. En grense som er et råd og en grense
som er forskrift ser identiske ut som polygoner, og et snapshot som
ikke bærer forskjellen kan ikke svare på hvilken av dem det beskriver.
Regel 1b-3: en verdi som avgjør hva dataene betyr, lagres SAMMEN med
dem — ikke i config, ikke i git, ikke i en README.

Blir forslaget vedtatt, endres verdien, og da ligger BEGGE tilstandene
i historikken med hver sin `observed_at`. Det er hele grunnen til at
dette er en kilde og ikke en engangsfil.

## `published_at` LESES fra rapporten, ikke fra en header

Regel 1b-7 punkt 2. Rapportsiden sier «Publisert: 29.06.2026» i sin
egen metadatablokk, og det er kildens eget utsagn om når den utga
dette. Alle tre rapportene (2026-28, -36 og -37) sier samme dato.

**hi.no sender ingen `Last-Modified` i det hele tatt** for disse
sidene — målt på alle tre 09.09.2026. Det er ikke et problem her,
siden datoen står i kroppen.

**NMDC-verten er målt for første gang.** `ftp.nmdc.no` er
`Apache/2.4.6 (CentOS)` og svarer:

    Last-Modified: Fri, 28 Aug 2026 05:00:09 GMT

Det er TO MÅNEDER etter at rapporten ble utgitt. Headeren er altså
ikke utgivelsestidspunktet for grensene; den sier når fila sist ble
skrevet på den serveren. Den brukes derfor IKKE som `published_at` —
den er notert her, og i beslutningsnotatet, som en måling av verten.
Om de to månedene er en re-opplasting av samme innhold eller en stille
revisjon, er IKKE fastslått. Det skal ikke gjettes.

## To rapporter som ARKIVERES og aldri parses

2026-36 «Råd om akseptabelt utslippsnivå av lakselus» og 2026-37
«Akseptabelt utslipp av lakselus innenfor miljømål» hentes med, ligger i
den samme arkivfila, og blir ALDRI til en observasjon. Se
`GRENSETALLRAPPORTER` for hvorfor de hentes her og hvorfor de ikke blir
en kilde.

Det de inneholder, målt 09.09.2026:

    2026-36   fem tabeller: akseptabelt lusenivå (millioner voksne
              hunnlus) som gir 10 % dødelighet på utvandrende laksesmolt
              og 10 % fitness-reduksjon for sjøørret, per
              produksjonsområde og per reguleringsområde, med høyeste og
              laveste verdi over 2022-2025 og med median og 25/75-
              persentil fra en modellsammenstilling.
    2026-37   tre tabeller: utvandringsperioder og antall anlegg med
              produksjon per REGULERINGSOMRÅDE, en beskrivelse av tre
              beregningsmetoder, og antall voksne hunnlus (millioner)
              beregnet med metode 1-3 for ROC og VPS, både per PO og per
              RO.

Grensetallene er altså et INTERVALL fra TRE metoder, ikke ett tall. Det
er den viktigste grunnen til at de ikke er en kilde: en kilde måtte valgt
metode og punktestimat på HIs vegne, og det valget er departementets.

## Kadens: statisk, som biomasse

Kilden endrer seg bare hvis HI publiserer en ny versjon av datasettet,
eller hvis forslaget behandles. `min_dager_mellom = 7` er ikke en
påstand om hvor ofte det skjer — det er hvor ofte kjøringen får lov å
spørre `finnes_allerede()` om 2026-06-29 allerede ligger skrevet. Så
lenge den gjør det, hentes ingenting. Samme mekanikk og samme
begrunnelse som `trafikklysvedtak`.

`observed_at` er 29.06.2026 og ikke kjøredatoen: `observed_at` handler
om verden, kjøredatoen om oss. De spriker med over to måneder i dag,
og det er riktig.

## Hva som får parse() til å nekte

`gjelder_for()` VELGER datoen; kroppen BEKREFTER den. Samme rekkefølge
som i `biomasse.parse()` og `trafikklysvedtak.parse()`. Nekter den:

  - rapporten oppgir en annen utgivelsesdato enn `UTGITT`. Da er dette
    en NY utgave, og å skrive den under 2026-06-29 ville påstått at
    2026-06-29-grensen så slik ut. Kroppen er arkivert av kjernen før
    parse() kalles, så ingenting går tapt — det er en re-parse etter at
    `UTGITT` er oppdatert.
  - geojson-fila oppgir et annet lagnavn enn `regomr_v3`. Fila bærer
    sin egen versjon i `name`, og det er det eneste stedet en stille
    revisjon ville vist seg.
  - antallet områder eller navnene avviker fra de 28 kjente.
  - tallet i et områdenavn er uenig med `prodomr`-egenskapen i samme
    feature.

Den siste er en gratis kryssjekk: oppgaven sier at tallet i navnet ER
produksjonsområdet, og fila bærer det ALLEREDE som et eget felt. To
uavhengige utsagn om samme ting skal stemme, og gjør de ikke det, er
det ikke vår jobb å velge hvilket som gjelder. Målt 09.09.2026: alle
28 er enige.
"""

from __future__ import annotations

import html as htmllib
import re
from typing import Iterable, NamedTuple

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

GEOJSON_URL = "https://ftp.nmdc.no/nmdc/IMR/Smittepress/regomr.geojson"
RAPPORT_URL = (
    "https://www.hi.no/hi/nettrapporter/rapport-fra-havforskningen-2026-28"
)
DOI = "https://doi.org/10.21335/NMDC-1923112433"

# Rapportene som bærer GRENSETALLENE — akseptabelt utslippsnivå per
# område, i millioner voksne hunnlus. De arkiveres og PARSES ALDRI.
#
# Hvorfor de likevel hentes her: de er samme bestilling, samme dato
# (29.06.2026) og samme forfattermiljø som 2026-28, og 2026-37s tabell 1
# og 3 er oppgitt PER REGULERINGSOMRÅDE. De er den samme leveransen, og
# regel 1b-5 punkt 2 sier at `fetch()` skal returnere det kilden faktisk
# sendte — hele svaret, ikke skiva vi skriver. Med dem i råsvaret får de
# `raw_hash` og `published_at` gjennom den vanlige maskineriet, uten en
# eneste linje ny kode i `core/`.
#
# Hvorfor de ikke blir en kilde: grensetallene er et RÅD med intervaller
# og tre ulike beregningsmetoder, ikke en vedtatt grense. Ingen vet
# hvilken form det som eventuelt vedtas får, og en kilde bygget på
# rådets form ville måttet rives den dagen forskriften kom. Å arkivere
# kroppen nå koster ingenting og bevarer utgangspunktet.
GRENSETALLRAPPORTER: tuple[tuple[str, str], ...] = (
    ("2026-36", "https://www.hi.no/hi/nettrapporter/"
                "rapport-fra-havforskningen-2026-36"),
    ("2026-37", "https://www.hi.no/hi/nettrapporter/"
                "rapport-fra-havforskningen-2026-37"),
)

# Datoen rapporten selv oppgir. `gjelder_for()` velger den, `parse()`
# krever at kroppen sier det samme. Endres den her uten at en ny kropp
# faktisk sier det, feiler parse() — som den skal.
UTGITT = "2026-06-29"

# Lagnavnet geojson-fila bærer i `name`. Fila er selve versjonsmerket:
# en revidert utgave vil hete `regomr_v4`, og da skal kilden stoppe og
# ikke skrive den nye grensen under den gamle datoen.
VENTET_VERSJON = "regomr_v3"

# Et RÅD, ikke en forskrift. Se modulens docstring om 1b-3.
STATUS = "forslag"

# De 28 navnene, i rapportens egen rekkefølge. Listen er en kontrakt mot
# historikken på samme måte som feltnavn er det: et område som dukker
# opp eller forsvinner skal felle kilden, ikke bli en stille endringsrad.
OMRAADER: tuple[str, ...] = (
    "1A", "1B", "2A", "3A", "3B", "4A", "4B", "4C", "4D", "5A", "5B",
    "6A", "6B", "7A", "7B", "8A", "8B", "9A", "10A", "10B", "11A", "11B",
    "12A", "12B", "12C", "12D", "13A", "13B",
)

# Desimaler i den lagrede WKT-en. Seks er ~11 cm i lengdegrad ved
# ekvator og langt under enhver grense noen har tegnet. Tallet er en
# KONTRAKT mot historikken, ikke en preferanse: endrer du det, leser
# diffen hver eneste grense som endret. Full presisjon ligger uansett i
# rå-arkivet, som er der den hører hjemme.
DESIMALER = 6


class Formatfeil(RuntimeError):
    """Kroppen kom, men ikke i formen vi leser.

    Egen type fordi den betyr noe annet enn et nettverksavbrudd: den sier
    at framstillingen er endret og at rå-kroppen må re-parses etterpå.
    Den er arkivert, så det er en re-parse og ikke tapt historikk.
    """


class Nyutgivelse(RuntimeError):
    """Kroppen er en ANNEN utgave enn den `UTGITT` navngir.

    Skilt fra Formatfeil med vilje. En formatfeil betyr at vi ikke klarte
    å lese; denne betyr at vi leste helt fint, og at det vi leste er noe
    annet enn det snapshotet skulle hete. Å skrive den under gammel dato
    ville vært en påstand om hvordan grensen SÅ UT den dagen.
    """


class Omraade(NamedTuple):
    """Ett reguleringsområde slik geojson-fila framstiller det."""

    navn: str                       # "4A"
    produksjonsomraade: str         # "4", utledet av navnet
    nummer: str                     # `numregomr`, f.eks. "41"
    punkter: list[tuple[float, float]]   # (lengdegrad, breddegrad)


# ------------------------------------------------------------ utledning

def produksjonsomraade(navn: str) -> str:
    """Tallet i områdenavnet, som ER produksjonsområdet det ligger inni.

    Utledet av NAVNET og ikke av `prodomr`-egenskapen, fordi oppgaven
    definerer det slik og fordi navnet er det eneste begge
    framstillingene har. `_krev_enig_med_fila()` holder resultatet mot
    `prodomr` etterpå — to utsagn om samme ting, sjekket mot hverandre.
    """
    m = re.fullmatch(r"(\d{1,2})([A-Z])", navn)
    if not m:
        raise Formatfeil(
            f"Områdenavnet {navn!r} har ikke formen <tall><bokstav>. "
            f"Da kan produksjonsområdet ikke utledes av navnet."
        )
    return m.group(1)


def wkt_av(punkter: list[tuple[float, float]]) -> str:
    """Punktene som ETT polygon i standard WKT.

    Standard form, ikke rapportens: `POLYGON((x y, x y, ...))`. Vi lagrer
    noe andre verktøy kan lese, ikke en gjengivelse av appendikset.
    """
    ledd = ", ".join(
        f"{x:.{DESIMALER}f} {y:.{DESIMALER}f}" for x, y in punkter
    )
    return f"POLYGON(({ledd}))"


def bbox_av(punkter: list[tuple[float, float]]) -> str:
    """Omsluttende rektangel som «vest,sør,øst,nord»."""
    xs = [x for x, _ in punkter]
    ys = [y for _, y in punkter]
    return ",".join(
        f"{v:.{DESIMALER}f}" for v in (min(xs), min(ys), max(xs), max(ys))
    )


def inneholder(punkter: list[tuple[float, float]],
               lengdegrad: float, breddegrad: float) -> bool:
    """Punkt-i-polygon, stråleskyting i planet.

    Ligger her og ikke i analysen fordi det er GEOMETRIEN som svarer, og
    geometrien er kildens. Analysen skal kunne spørre «hvilket område er
    dette punktet i» uten å kjenne polygonformatet — samme prinsipp som
    `biomasse.maaneder()` og `trafikklysvedtak.aar_i()`.

    Planet og ikke kula: områdene er noen få grader store og grensene er
    tegnet i lengde/bredde, så en storsirkel mellom to nabohjørner ville
    vært en annen strek enn den HI faktisk tegnet. Det er den TEGNEDE
    grensen som gjelder.
    """
    inne = False
    n = len(punkter)
    for i in range(n):
        x1, y1 = punkter[i]
        x2, y2 = punkter[(i + 1) % n]
        if (y1 > breddegrad) != (y2 > breddegrad):
            # Der kanten krysser breddegraden: er krysningen øst for oss?
            x = x1 + (breddegrad - y1) * (x2 - x1) / (y2 - y1)
            if x > lengdegrad:
                inne = not inne
    return inne


# ------------------------------------------------------------- lesing

def les_geojson(rå: str) -> tuple[str, list[Omraade]]:
    """(lagnavn, områder) ut av geojson-kroppen.

    Lagnavnet returneres og kastes ikke bort: det er filas eget
    versjonsmerke, og det eneste stedet en stille revisjon ville vist seg.
    """
    import json

    try:
        d = json.loads(rå)
    except ValueError as e:
        raise Formatfeil(f"geojson lot seg ikke tolke som JSON: {e}") from e

    if d.get("type") != "FeatureCollection":
        raise Formatfeil(
            f"Ventet FeatureCollection, fikk {d.get('type')!r}."
        )

    ut: list[Omraade] = []
    for f in d.get("features", []):
        p = f.get("properties") or {}
        navn = str(p.get("regomr", "")).strip()
        if not navn:
            raise Formatfeil("En feature mangler `regomr`.")

        geom = f.get("geometry") or {}
        punkter = _ytre_ring(navn, geom)
        ut.append(Omraade(
            navn=navn,
            produksjonsomraade=produksjonsomraade(navn),
            nummer=str(p.get("numregomr", "")),
            punkter=punkter,
        ))

    _krev_enig_med_fila(d, ut)
    return str(d.get("name", "")), ut


def _ytre_ring(navn: str, geom: dict) -> list[tuple[float, float]]:
    """Den ene ytre ringen i et område.

    Fila bruker MultiPolygon med ett polygon og én ring per område, målt
    på alle 28. Kravet håndheves i stedet for å antas: et område som får
    en øy eller et hull i en senere utgave ville ellers blitt lagret som
    om hullet ikke fantes, og punkt-i-polygon ville sagt at et anlegg
    inne i hullet ligger i området.
    """
    t = geom.get("type")
    c = geom.get("coordinates") or []

    if t == "MultiPolygon":
        if len(c) != 1:
            raise Formatfeil(
                f"{navn}: MultiPolygon med {len(c)} polygoner. Kilden "
                f"lagrer én ytre ring per område og kan ikke uttrykke dette."
            )
        ringer = c[0]
    elif t == "Polygon":
        ringer = c
    else:
        raise Formatfeil(f"{navn}: ukjent geometritype {t!r}.")

    if len(ringer) != 1:
        raise Formatfeil(
            f"{navn}: polygonet har {len(ringer)} ringer. Hull kan ikke "
            f"uttrykkes av `geometri`-feltet slik det er nå."
        )
    return [(float(x), float(y)) for x, y in ringer[0]]


def _krev_enig_med_fila(d: dict, omraader: list[Omraade]) -> None:
    """Navnene mot de 28 kjente, og navnets tall mot `prodomr`."""
    navn = [o.navn for o in omraader]
    if sorted(navn) != sorted(OMRAADER):
        mangler = sorted(set(OMRAADER) - set(navn))
        nye = sorted(set(navn) - set(OMRAADER))
        raise Nyutgivelse(
            f"geojson har {len(navn)} områder, ikke de {len(OMRAADER)} "
            f"kjente. Mangler: {mangler or 'ingen'}. Nye: {nye or 'ingen'}."
        )

    fra_fila = {
        str((f.get("properties") or {}).get("regomr", "")).strip():
            (f.get("properties") or {}).get("prodomr")
        for f in d.get("features", [])
    }
    for o in omraader:
        oppgitt = fra_fila.get(o.navn)
        if oppgitt is None:
            continue
        if str(oppgitt) != o.produksjonsomraade:
            raise Formatfeil(
                f"{o.navn}: navnet sier produksjonsområde "
                f"{o.produksjonsomraade}, fila sier {oppgitt}. To utsagn "
                f"om samme ting som ikke stemmer — kilden velger ikke."
            )


def les_wkt(rå_html: str) -> dict[str, list[tuple[float, float]]]:
    """Appendiks 7.1s polygoner, som {navn: punkter}.

    Tolerant med vilje: rapportens WKT er ikke standard WKT (se modulens
    docstring), så parseren leter etter talpar i parentes og ikke etter
    syntaks. Det er riktig avveining for en KONTROLL — den skal svare på
    om tallene er de samme, ikke om HI skriver korrekt WKT.
    """
    t = htmllib.unescape(rå_html)
    start = t.find("sec-7-1")
    if start < 0:
        raise Formatfeil(
            "Fant ikke appendiks 7.1 (`sec-7-1`) i rapportkroppen."
        )

    ut: dict[str, list[tuple[float, float]]] = {}
    deler = re.split(r"Reguleringsområde\s+(\d{1,2}[A-Z]):", t[start:])
    for i in range(1, len(deler) - 1, 2):
        navn = deler[i]
        kropp = deler[i + 1]
        slutt = kropp.find("</p>")
        if slutt >= 0:
            kropp = kropp[:slutt]
        ut[navn] = [
            (float(a), float(b))
            for a, b in re.findall(
                r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)", kropp
            )
        ]
    return ut


def publisert_i(rå_html: str) -> str:
    """Utgivelsesdatoen rapporten selv oppgir, som ISO-dato.

    LEST, ikke utledet — regel 1b-7 punkt 2. Finner vi den ikke, blir det
    tom streng, som leses «vet ikke». Å falle tilbake på kjøredatoen ville
    vært å datere HIs publisering etter når VI ringte.
    """
    t = htmllib.unescape(rå_html)
    m = re.search(r"Publisert:\s*(?:<[^>]+>\s*)*(\d{2})\.(\d{2})\.(\d{4})", t)
    if not m:
        return ""
    dag, maaned, aar = m.groups()
    return f"{aar}-{maaned}-{dag}"


def _bevaringen_sier(raw: dict[str, str], observed_at: str) -> list[str]:
    """Hva som skjedde med de to grensetallrapportene. Aldri en exception.

    `published_at` på radene er LEST av 2026-28 alene, og de tre kroppene
    ligger i samme arkivfil under den ene datoen. Den påstanden er bare
    sann så lenge alle tre faktisk oppgir den — og det er billig å spørre
    dem, siden kroppene er her. Målt 09.09.2026: alle tre sier 29.06.2026.

    Advarsel og ikke exception, fordi kroppene bare skal BEVARES.
    Grensetallene brukes ikke til noe, så en uenighet om dato er noe
    noen skal se på — ikke noe som skal koste oss de 28 grensene.
    """
    ut: list[str] = []
    for navn, _ in GRENSETALLRAPPORTER:
        kropp = raw.get(f"grensetall_{navn}", "")
        if not kropp:
            ut.append(f"grensetall {navn}: ikke i råsvaret.")
        elif kropp.startswith("__IKKE_HENTET__"):
            ut.append(f"grensetall {navn} ble ikke hentet: "
                      f"{kropp[len('__IKKE_HENTET__'):].strip()}")
        else:
            utgitt = publisert_i(kropp)
            if utgitt and utgitt != observed_at:
                ut.append(
                    f"grensetall {navn} oppgir utgivelsesdato {utgitt}, "
                    f"ikke {observed_at}. Kroppene ligger i samme arkivfil "
                    f"under den ene datoen — se på om det stemmer."
                )
    return ut


# -------------------------------------------------------- kontrollen

def sammenlign(omraader: list[Omraade],
               wkt: dict[str, list[tuple[float, float]]]) -> dict[str, str]:
    """Geojson mot appendiks, per område. {navn: "wkt+geojson" | grunn}.

    UTLIGNER INGENTING. To framstillinger som er uenige er et funn, ikke
    et problem å glatte over — og fordi geojson er den som lagres, ville
    en stille utligning her betydd at vi lagret noe rapporten ikke sier.

    De to formatforskjellene som er MÅLT på alle 28 (avrunding til fem
    desimaler, og et duplisert sluttpunkt i WKT-en) regnes inn. Det er
    ikke en utligning: det er å sammenligne tall med tall i stedet for
    tekst med tekst.
    """
    ut: dict[str, str] = {}
    for o in omraader:
        w = wkt.get(o.navn)
        if w is None:
            ut[o.navn] = "mangler i appendiks"
            continue
        if len(w) > 1 and w[-1] == w[-2]:
            w = w[:-1]
        rundet = [(round(x, 5), round(y, 5)) for x, y in o.punkter]
        if len(w) != len(rundet):
            ut[o.navn] = f"sprik: {len(w)} punkter i WKT, {len(rundet)} i geojson"
        elif w != rundet:
            n = sum(1 for a, b in zip(w, rundet) if a != b)
            ut[o.navn] = f"sprik: {n} av {len(w)} punkter ulike"
        else:
            ut[o.navn] = "wkt+geojson"
    return ut


# ---------------------------------------------------------------- kilden

class Reguleringsomraader(Source):
    name = "reguleringsomraader"

    version = "1"

    # Egen entitetstype. IKKE `produksjonsomraade`, selv om `4A` ligger
    # inni PO 4: en analyse som joiner på `entity_id` skal ikke kunne
    # forveksle «4» med «4A». `produksjonsomraade` bæres som felt i
    # stedet, slik at serien kan aggregeres tilbake til PO-nivå der det
    # er det man vil.
    entity_type = "reguleringsomraade"

    # Sju for en STATISK kilde. Se modulens docstring — dette er ikke en
    # påstand om hvor ofte HI reviderer, men om hvor ofte kjøringen skal
    # få spørre `finnes_allerede()` om 2026-06-29 er skrevet.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.reguleringsomraader.aktiv", False))

    # ---- henting -------------------------------------------------------

    def geojson_url(self) -> str:
        return str(get("kilder.reguleringsomraader.geojson_url", GEOJSON_URL))

    def rapport_url(self) -> str:
        return str(get("kilder.reguleringsomraader.rapport_url", RAPPORT_URL))

    def hent_begge(self, client: httpx.Client | None = None) -> dict[str, str]:
        """Begge kroppene, rått, i én dict.

        Returnerer TEKST og ikke ferdig tolkede polygoner, fordi kjernen
        arkiverer det `fetch()` returnerer og det som arkiveres skal være
        det tjenestene faktisk sendte. Begge ligger i samme arkivfil, og
        det er med vilje: kontrollen i `sammenlign()` gir bare mening om
        begge halvdelene finnes, og to filer som må finnes sammen er to
        filer som kan komme fra hverandre.

        `utvalg` og `published_at` settes HER og ikke i `fetch()`, fordi
        dette er det ene stedet alle veier inn i kilden går gjennom.
        Samme begrunnelse som `biomasse.hent_alt()`.

        `{}` er riktig utvalg og ikke et gjett: ingen av de to adressene
        tar en spørrestreng. Vi ber om hele fila og får hele fila. At HI
        har avgrenset forslaget til 28 områder er DERES utvalg, ikke vårt.
        """
        self.utvalg = {}

        egen = client is None
        c = client or httpx.Client(timeout=60.0, follow_redirects=True)
        try:
            geo = _http.get(c, self.geojson_url(),
                            hva="reguleringsområder (geojson)")
            rap = _http.get(c, self.rapport_url(),
                            hva="reguleringsområder (rapport 2026-28)")
            kropper = {
                "geojson": geo.content.decode("utf-8-sig"),
                "rapport": rap.content.decode("utf-8", errors="replace"),
                # Vertens egen header, BEVART og ikke brukt. Se modulens
                # docstring: den er to måneder etter utgivelsen, så den
                # sier noe om serveren og ikke om grensene. Den ligger i
                # arkivet fordi den er en måling av en vert vi ikke har
                # målt før, og fordi den ikke kan hentes igjen i morgen.
                "geojson_last_modified": geo.headers.get("Last-Modified", ""),
            }
            for navn, url in GRENSETALLRAPPORTER:
                kropper[f"grensetall_{navn}"] = self._hent_bevaring(c, url)
        finally:
            if egen:
                c.close()

        self.published_at = publisert_i(kropper["rapport"])
        return kropper

    @staticmethod
    def _hent_bevaring(c: httpx.Client, url: str) -> str:
        """En kropp som skal BEVARES, ikke leses.

        Feiler den, feiler ikke kilden. Det er ikke slapphet — det er
        rangeringen mellom de to tingene kallet gjør: 2026-28 bærer
        radene som skrives, mens disse to bare skal ikke gå tapt. En
        hi.no-side som er nede skal ikke koste oss de 28 grensene.

        Feilteksten lagres i stedet for kroppen, og går i arkivet med
        den. Da sier arkivet «vi prøvde, dette svarte den» i stedet for
        å tie — samme skille som `lus_er_rapportert` gjør mellom
        rapportert null og ikke rapportert.
        """
        try:
            return _http.get(c, url, hva=f"grensetall {url}").content.decode(
                "utf-8", errors="replace")
        except Exception as e:              # noqa: BLE001 — bevaring, ikke lesing
            return f"__IKKE_HENTET__ {type(e).__name__}: {e}"

    def gjelder_for(self, kjoredato: str) -> str:
        """Datoen rådet ble avgitt — ikke dagen vi henter det.

        De to spriker med over to måneder i dag, og det er riktig:
        `observed_at` handler om verden, kjøredatoen om oss. Så lenge
        2026-06-29 ligger skrevet, hopper steg 2b i `run.py` over kilden
        uten å hente.

        Kjøredatoen tas inn og brukes IKKE til å slå opp klokka — den er
        med fordi kontrakten sier at `fetch()` og `gjelder_for()` skal få
        tiden inn, og fordi en framtidig utgave skal kunne begrenses av
        den uten at signaturen endres.
        """
        return UTGITT

    def fetch(self, kjoredato: str) -> dict[str, str]:
        return self.hent_begge()

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: dict[str, str],
              observed_at: str) -> Iterable[Observation]:
        """28 områder ut av geojson, med appendikset som kontroll.

        `observed_at` VELGER utgaven, kroppen BEKREFTER den. Samme
        rekkefølge og samme begrunnelse som `biomasse.parse()`: et
        etterslepsregnestykke eller en konstant er OSS, og kroppen er
        VERDEN. Er de uenige, er det kroppen som har rett, og da skal
        ingenting skrives.
        """
        if not isinstance(raw, dict) or "geojson" not in raw:
            raise Formatfeil(
                "Råsvaret er ikke {'geojson': ..., 'rapport': ...}. "
                "En eldre arkivkropp kan ha en annen form."
            )

        utgitt = publisert_i(raw.get("rapport", ""))
        if utgitt and utgitt != observed_at:
            raise Nyutgivelse(
                f"Rapporten oppgir utgivelsesdato {utgitt}, snapshotet "
                f"skulle hete {observed_at}. Dette er en annen utgave. "
                f"Kroppen er arkivert — oppdater UTGITT og re-parse."
            )

        versjon, omraader = les_geojson(raw["geojson"])
        if versjon != VENTET_VERSJON:
            raise Nyutgivelse(
                f"geojson-lagets navn er {versjon!r}, ventet "
                f"{VENTET_VERSJON!r}. HI har publisert en ny versjon av "
                f"datasettet. Kroppen er arkivert — se på den før du "
                f"skriver den under {observed_at}."
            )

        wkt = les_wkt(raw.get("rapport", "")) if raw.get("rapport") else {}
        dom = sammenlign(omraader, wkt) if wkt else {}

        # SETT, ikke append: `advarsler` er en liste på KLASSEN, som deles
        # av alle instanser og aldri tømmes. Se Source.advarsler.
        avvik = [
            f"reguleringsområde {navn}: {grunn}"
            for navn, grunn in sorted(dom.items())
            if grunn != "wkt+geojson"
        ]
        if not wkt:
            avvik.append(
                "reguleringsområder: appendiks 7.1 ble ikke lest, så "
                "geojson står ukontrollert."
            )
        avvik += _bevaringen_sier(raw, observed_at)
        self.advarsler = avvik

        for o in omraader:
            felles = dict(
                entity_id=o.navn,
                entity_type=self.entity_type,
                entity_name=f"Reguleringsområde {o.navn}",
                source=self.name,
                observed_at=observed_at,
            )

            # `status` FØRST, med vilje. Den avgjør hva alt det andre
            # betyr — en grense som er et råd er ikke en grense som er
            # forskrift. Se modulens docstring om 1b-3.
            yield Observation(field="status", value=STATUS, **felles)
            yield Observation(field="produksjonsomraade",
                              value=o.produksjonsomraade, **felles)
            yield Observation(field="omraadenummer", value=o.nummer, **felles)
            yield Observation(field="geometri",
                              value=wkt_av(o.punkter), **felles)
            yield Observation(field="punkter",
                              value=str(len(o.punkter)), **felles)
            yield Observation(field="bbox",
                              value=bbox_av(o.punkter), **felles)
            # Bæres på HVER rad og ikke bare i advarslene: en leser om to
            # år skal kunne se av snapshotet alene om appendikset bekreftet
            # denne grensen. Regel 1b-3 — en advarsel er en logglinje, og
            # logglinjer følger ikke med dataene.
            yield Observation(field="geometri_bekreftet",
                              value=dom.get(o.navn, "ukontrollert"), **felles)
            yield Observation(field="datasett_versjon",
                              value=versjon, **felles)
