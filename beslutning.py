"""Departementets FARGELEGGING, lest av pressemeldingen som kunngjorde den.

`sources/trafikklysvedtak.py` leser kapasitetsjusteringsforskriftene, og
de svarer bare halvveis: MÅLT 20.09.2026 kunne 19 av 65 celler ikke
leses av forskriftsteksten i det hele tatt.

Grunnen er ikke at forskriftene er ufullstendige. Den er at
trafikklyset besluttes i TO TRINN:

    1. Departementet fargelegger alle 13 produksjonsområdene.
    2. Det fastsettes forskrift for det som må reguleres — vekst i
       grønne områder og nedtrekk i røde.

**Et gult område krever ingen forskrift.** «Her opprettholdes dagens
produksjonskapasitet», som pressemeldingen 19.06.2026 skriver det, og
en bestemmelse som ikke endrer noe blir ikke skrevet. Fargen finnes;
den står bare ikke i Lovtidend.

Derfor denne modulen, som gir en TREDJE beleggsgrad ved siden av
`ordrett` og `kapittelhjemmel`:

    ordrett            fargeordet står i FORSKRIFTENS bestemmelse
    kapittelhjemmel    fargen er utledet av hvilket kapittel i
                       FORSKRIFTEN området er plassert i
    beslutning         fargeordet står i departementets kunngjøring av
                       fargeleggingen, ikke i forskriften

## Den leser ARKIVET, ikke nettet

regjeringen.no svarer 403 for oss på alle fem meldingene. Kroppene er
hentet via Internet Archive 09.09.2026, lagret rått, og verifisert
setning for setning i `docs/VERIFISERING-PRESSEMELDINGER.md`. Modulen
leser de arkiverte kroppene og ingenting annet: ingen nettverkskall ved
bygging, og samme svar hver gang.

`KROPPER` pinner sha256 av hver kropp. Endrer en fil seg, faller
`hent()` — den skal ikke stille lese en annen tekst enn den som er
verifisert.

## Den er IKKE en kilde

Ingen `Observation`, ingen `data/raw/`. Beslutningen fra 2018 kan ikke
hentes på nytt i 2027, og en «kilde» som bare kan lese fem arkiverte
filer er ikke en kilde — den er dokumentasjonsgrunnlag, samme status
som `docs/VERIFISERING-PRESSEMELDINGER.md`. Se
`docs/beslutninger/2026-09-05-vedtakskilden.md`, som valgte vekk
pressemeldinger som kilde og fortsatt gjelder.

## GODKJENT er en menneskelig kvittering, ikke en teknisk grense

Parseren leser alle fem rundene. Bare rundene i `GODKJENT` når
nettstedet. Grunnen står i
`docs/beslutninger/2026-09-23-fargeleggingen-er-et-eget-belegg.md`:
avsnittene skal leses av et menneske mot kroppen før de publiseres, og
en runde legges til her når de er lest.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import re
from functools import lru_cache

from core.paths import DATA_DIR

ARKIV = DATA_DIR / "arkiv" / "regjeringen-pressemeldinger"

# Tildelingsrunde -> (pressemeldingens dato, sha256 av kroppen).
#
# Summene er de samme som står i docs/VERIFISERING-PRESSEMELDINGER.md,
# og de er der av samme grunn som fontene er pinnet: en kropp som
# endrer seg skal stoppe, ikke bli lest.
KROPPER = {
    "2018": ("2017-10-30",
             "896b9570c2d91346f06513fddba7bd7c45b1a5235950fb83f0410210b54eadda"),
    "2020": ("2020-02-04",
             "f02cd9a1494e908b6dc145b0551795c69b8f75425983b44dae1386e275ed9c6b"),
    "2022": ("2022-06-07",
             "637168e536c51114259825401ff0396425f75944b54f1b95af4b03ab0c5501c9"),
    "2024": ("2024-03-06",
             "c5681d286a37cf49304349c076b5e58af99ffbfc129ff0db0be261e670ef9c22"),
    "2026": ("2026-06-19",
             "b804dafd845a9908e14601e9dc855180c2115edaa4771402212496d610bdc194"),
}

# Rundene som er LEST av et menneske mot kroppen, og som derfor vises.
#
# 2026 er godkjent 23.09.2026: avsnittene navngir alle tretten områdene
# med nummer og farge, i tre setninger som begynner med «Tre
# produksjonsområder (PO) fargelegges grønt», «Ni produksjonsområder
# fargelegges gult» og «Ett produksjonsområde fargelegges rødt».
#
# De fire andre er parset og lagt fram, men ikke godkjent. En tom
# celle er et ærligere svar enn en celle ingen har sett på.
GODKJENT = frozenset({"2026"})


class Kroppsprik(RuntimeError):
    """Den arkiverte kroppen er ikke den som er verifisert."""


# Hvordan de fem meldingene skriver fargen. To former, begge ordrett.
FARGEORD = (
    (re.compile(r"fargelegges\s+grønt|får\s+grønt\s+lys|settes\s+til\s+grønt"), "gronn"),
    (re.compile(r"fargelegges\s+gult|får\s+gult\s+lys|settes\s+til\s+gult"), "gul"),
    (re.compile(r"fargelegges\s+rødt|får\s+rødt\s+lys|settes\s+til\s+rødt"), "rod"),
)

# «(PO4)», «(4)», «(produksjonsområdene 1 og 7-13)».
NUMMER = re.compile(r"\(([^)]*\d[^)]*)\)")

# Kanonisk adresse, LEST AV KROPPEN og ikke skrevet av her. Meldingen
# bærer sin egen `og:url`, og en URL vi skrev selv ville vært et gjett
# på regjeringen.nos vegne. MÅLT: ingen av de fem kroppene har
# `rel="canonical"`; alle fem har `og:url`.
KANONISK = re.compile(r'property="og:url"[^>]*content="([^"]+)"')

# Avsnittet der departementet forklarer at det gikk UTENOM den
# automatiske regelen for et område. 2026-meldingen: «I områder der
# ekspertgruppens vurderinger er ulik de to årene gjør departementet en
# mer helhetlig vurdering av miljøtilstanden.»
SAERSKILT = re.compile(
    r"særskilt vurdering|grundigere vurdering|mer helhetlig vurdering")
SPENN = re.compile(r"(\d+)\s*[-–]\s*(\d+)")

# Et produksjonsområde har nummer 1-13. Grensa er ikke pedanteri: den
# er det som skiller «(PO4)» fra «Meld. St. 16 (2014-2015)», og
# 2014-2015 står i et avsnitt i hver eneste av de fem meldingene.
OMRAADER = frozenset(str(n) for n in range(1, 14))


def _tekst(rå: bytes) -> list[str]:
    """Kroppens avsnitt som ren tekst, i dokumentrekkefølge."""
    s = rå.decode("utf-8", "replace")
    s = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", "\n", s)
    s = html.unescape(s)
    return [ln.strip() for ln in s.split("\n") if ln.strip()]


def _numre(bit: str) -> list[str]:
    """Områdenumrene i én parentes. «7-13» er en OPPREGNING.

    En tallrekke er ikke en utledning: «produksjonsområdene 1 og 7-13»
    navngir åtte områder, komprimert. Det som IKKE gjøres, er å slutte
    fra «de øvrige ble gule» — se modulens docstring og punkt 3 i
    oppdraget.
    """
    ut: list[str] = []
    rest = bit
    for spenn in SPENN.finditer(bit):
        ut += [str(n) for n in range(int(spenn.group(1)),
                                     int(spenn.group(2)) + 1)]
        rest = rest.replace(spenn.group(0), " ")
    ut += re.findall(r"\d+", rest)
    return [n for n in ut if n in OMRAADER]


# HVA FARGEN BETØR I DENNE RUNDEN, lest av kunngjøringen.
#
# ## Hvorfor dette ikke er én fast tegnforklaring
#
# «rød = ned 6 %, grønn = opp 6 %» er sant for fire av fem runder og
# USANT for den første. Kunngjøringen 30.10.2017 skriver:
#
#   «Det er tidligere besluttet at kapasiteten i de røde områdene ikke
#    skal reduseres i denne runden. Nedtrekk vil først skje i de
#    områdene som blir røde i neste runde i 2019.»
#
# PO3 og PO4 var røde i 2018 og ble IKKE trukket ned. En felles
# tegnforklaring ville sagt at de ble det, og det er en påstand om et
# forvaltningsvedtak — ikke en forenkling.
#
# Grønt i 2018 er også annerledes: «tilbud om økt produksjonskapasitet»
# uten oppgitt prosent.
#
# Mønstrene leses derfor per runde, av kroppen. Finner de ingenting for
# en farge, står tegnforklaringen tom — se `gul` i 2018, der
# kunngjøringen ikke sier hva gult betyr.
FOLGER = (
    # rødt
    (re.compile(r"ikke skal reduseres i denne runden"), "rod",
     "ingen reduksjon i denne runden"),
    (re.compile(r"redusere[rs]? produksjonskapasiteten med (\d+) prosent"),
     "rod", "{} prosent nedtrekk"),
    # grønt
    (re.compile(r"øke produksjonskapasiteten med inntil (\d+) prosent"),
     "gronn", "tilbud om inntil {} prosent vekst"),
    (re.compile(r"økt produksjonskapasitet med inntil (\d+) prosent"),
     "gronn", "tilbud om inntil {} prosent vekst"),
    (re.compile(r"tilbud om økt produksjonskapasitet i de områdene som "
                r"settes til grønt"), "gronn",
     "tilbud om økt produksjonskapasitet, uten oppgitt prosent"),
    # gult
    (re.compile(r"ingen endringer i produksjonskapasiteten"), "gul",
     "ingen endring i kapasiteten"),
    (re.compile(r"opprettholdes dagens produksjonskapasitet"), "gul",
     "dagens kapasitet opprettholdes"),
)

# Sidens egen dokumenttype, lest av kroppen. regjeringen.no merker hver
# side som «Pressemelding», «Nyhet» eller noe annet, og de to første er
# ikke det samme: en nyhet er ikke et kunngjort vedtak. MÅLT 23.09.2026:
# 2020 og 2024 er Nyhet, de tre andre Pressemelding.
#
# `og:type` er «website» på alle fem og sier ingenting. Merkelappen står
# i sidens egen typeblokk, etterfulgt av en loddrett strek.
DOKUMENTTYPE = re.compile(
    r'<[^>]*class="[^"]*(?:article-type|documenttype|type)[^"]*"[^>]*>'
    r'\s*([^<|]{3,40}?)\s*\|')


@lru_cache(maxsize=8)
def _kropp(runde: str) -> bytes:
    """Den arkiverte kroppen, verifisert mot sha256.

    `Kroppsprik` når fila er der, men ikke er den som er gått god for i
    `docs/VERIFISERING-PRESSEMELDINGER.md`. En kropp som har endret seg
    skal stoppe, ikke leses stille.
    """
    par = KROPPER.get(runde)
    if par is None:
        return b""
    dato, sum_ = par
    sti = ARKIV / f"{dato}.bin.gz"
    if not sti.exists():
        return b""
    rå = gzip.decompress(sti.read_bytes())
    faktisk = hashlib.sha256(rå).hexdigest()
    if faktisk != sum_:
        raise Kroppsprik(
            f"{sti.name}: sha256 {faktisk[:16]}… der {sum_[:16]}… er "
            f"verifisert i docs/VERIFISERING-PRESSEMELDINGER.md")
    return rå


@lru_cache(maxsize=8)
def folge(runde: str) -> dict[str, dict[str, str]]:
    """{farge: {"tekst": …, "sitat": …}} — hva fargen BETØR i runden.

    Tegnforklaringen er ikke felles for de fem rundene, og det er ikke
    en detalj: i 2018 ble de røde områdene IKKE trukket ned. Se
    `FOLGER`.

    En farge kunngjøringen ikke sier noe om, står ikke i svaret. Gult i
    2018 er et slikt tilfelle.
    """
    rå = _kropp(runde)
    if not rå:
        return {}
    ut: dict[str, dict[str, str]] = {}
    for avsnitt in _tekst(rå):
        for mønster, farge, mal in FOLGER:
            if farge in ut:
                continue
            m = mønster.search(avsnitt)
            if not m:
                continue
            tekst = mal.format(*m.groups()) if m.groups() else mal
            ut[farge] = {"tekst": tekst, "sitat": avsnitt}
    return ut


@lru_cache(maxsize=8)
def dokumenttype(runde: str) -> str:
    """«Pressemelding» eller «Nyhet», lest av sidens egen merkelapp.

    De to er ikke det samme, og forskjellen er departementets egen: en
    nyhet er ikke merket som et kunngjort vedtak. MÅLT 23.09.2026: 2020
    og 2024 er Nyhet, de tre andre Pressemelding.

    `og:type` duger ikke — den er «website» på alle fem.
    """
    rå = _kropp(runde)
    if not rå:
        return ""
    m = DOKUMENTTYPE.search(rå.decode("utf-8", "replace"))
    return " ".join(m.group(1).split()) if m else ""


def url(runde: str) -> str:
    """Meldingens egen kanoniske adresse, lest av kroppen."""
    rå = _kropp(runde)
    if not rå:
        return ""
    m = KANONISK.search(rå.decode("utf-8", "replace"))
    return m.group(1) if m else ""


@lru_cache(maxsize=8)
def saerskilt(runde: str) -> dict[str, dict[str, str]]:
    """{po: {"sitat": …, "dato": …}} der departementet sier at det gjorde
    en egen vurdering av området.

    Fargeleggingen følger ekspertgruppens vurdering når de to
    grunnlagsårene er enige. Er de ikke det, sier meldingen at
    departementet vurderte området særskilt — og NAVNGIR områdene. Det
    er en opplysning om hvordan fargen ble til, og den står på
    områdesiden ordrett, uten tolkning.

    MÅLT 23.09.2026: 2026-meldingen navngir ett område (PO9), 2022
    navngir tre (PO2, PO4, PO5).
    """
    par = KROPPER.get(runde)
    if par is None:
        return {}
    rå = _kropp(runde)
    if not rå:
        return {}
    dato = par[0]

    ut: dict[str, dict[str, str]] = {}
    for avsnitt in _tekst(rå):
        if not SAERSKILT.search(avsnitt):
            continue
        numre = [n for m in NUMMER.finditer(avsnitt)
                 for n in _numre(m.group(1))]
        for po in numre:
            ut.setdefault(po, {"sitat": avsnitt, "dato": dato})
    return ut


def saerskilt_for_runde(runde: str) -> dict[str, dict[str, str]]:
    """Som `saerskilt()`, men tom for en runde som ikke er godkjent."""
    return saerskilt(runde) if runde in GODKJENT else {}


@lru_cache(maxsize=8)
def hent(runde: str) -> dict[str, dict[str, str]]:
    """{po: {"farge": …, "sitat": …, "dato": …}} for én runde.

    Tom dict når runden ikke har en kropp. `Kroppsprik` når kroppen er
    der, men ikke er den verifiserte.
    """
    par = KROPPER.get(runde)
    if par is None:
        return {}
    rå = _kropp(runde)
    if not rå:
        return {}
    dato = par[0]

    ut: dict[str, dict[str, str]] = {}
    for avsnitt in _tekst(rå):
        # HVER PARENTES HØRER TIL FARGEORDET FORAN SEG, ikke til
        # avsnittet.
        #
        # 2017-meldingen skriver alle tre fargene i ÉN setning:
        # «8 produksjonsområder settes til grønt (produksjonsområdene 1
        # og 7-13), tre produksjonsområder settes til gult (2, 5 og 6)
        # og to produksjonsområder settes til rødt (3 og 4)». Et
        # avsnittsvis oppslag ga 2, 3, 4, 5 og 6 fargen GRØNN — og de
        # skal være gul, rød, rød, gul, gul.
        #
        # Det er formen fra CLAUDE.md 1b-2: en prøve som er riktig
        # nettopp i de tilfellene der de to tingene faller sammen — ett
        # fargeord per avsnitt — og stille feil ellers.
        farger = [(m.start(), farge) for mønster, farge in FARGEORD
                  for m in mønster.finditer(avsnitt)]
        if not farger:
            continue
        farger.sort()
        for paren in NUMMER.finditer(avsnitt):
            foran = [f for pos, f in farger if pos < paren.start()]
            if not foran:
                continue
            farge = foran[-1]
            for po in _numre(paren.group(1)):
                # FØRSTE FOREKOMST VINNER. De fem meldingene gjentar
                # fargene lenger nede i brødteksten, og en gjentakelse
                # skal ikke kunne overskrive oppregningen.
                ut.setdefault(po, {"farge": farge, "sitat": avsnitt,
                                   "dato": dato})
    return ut


def tabell() -> dict[tuple[str, str], dict[str, str]]:
    """{(runde, po): …} for alle rundene, godkjente som ugodkjente.

    For rapporten og for testene. Nettstedet spør `for_runde()`.
    """
    return {(r, po): d for r in KROPPER for po, d in hent(r).items()}


def for_runde(runde: str) -> dict[str, dict[str, str]]:
    """Som `hent()`, men tom for en runde som ikke er godkjent ennå."""
    return hent(runde) if runde in GODKJENT else {}
