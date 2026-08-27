"""Ekspertgruppen for vurdering av lusepåvirkning — kategori per PO per år.

Verifisert mot fem nedlastede rapporter 26.-27.08.2026, se
docs/KILDE-EKSPERTGRUPPEN.md. Alt i denne docstringen er MÅLT på de
arkiverte kroppene, ikke lest ut av en nettside.

Dette er fasiten trafikklyssystemet faktisk styres etter: ekspertgruppen
plasserer hvert av de tretten produksjonsområdene i lav (< 10 %),
moderat (10-30 %) eller høy (> 30 %) lakselusindusert villfiskdødelighet
på utvandrende villakssmolt, og departementet fargelegger deretter.

Fram til 26.08.2026 lå tallene i `analyse/fasit/ekspertgruppen-po-kategori.csv`
— skrevet for hånd, uten proveniens, uten rå-arkiv, uten `source_version`.
Det er regel 1b-3 i måltallet: en verdi utenfor dataene avgjorde hva de
betyr, uten spor av hvor den kom fra.

## Kildens form: N KROPPER som hver dekker M ÅR

Ulikt alle andre kilder i repoet. Biomasse er ÉN kropp som bærer alle
periodene; lusetall er én kropp per periode. Denne er seks kropper som
OVERLAPPER: 2018-rapporten gjentar 2016 og 2017, 2021-rapporten gjentar
2020 med en oppdatert tabell.

Det er ikke en konstruksjon vi påfører kilden. Ekspertgruppen skriver
selv «For 2017 konkluderte ekspertgruppen med ...» i 2018-rapportens
kapittel 4, og 2021-rapporten har en egen Tabell 2 for 2020 med teksten
«Vurderingene for 2020 er oppdatert etter møte i september».

Derfor: **én observasjon om hvert år rapporten dekker, med rapportens
`published_at`.** To rapporter som er uenige om 2020 er ikke en feil —
det er to påstander om samme tidspunkt, gjort på hver sin dato, og begge
er sanne. Se CLAUDE.md 1b-5 og `diff.revisjon()`.

## `published_at` LESES av PDF-ens `/CreationDate` — ikke av HTTP

Dette er kildens viktigste avvik fra `sources/biomasse.py`, og det er
målt, ikke antatt.

Biomasse tar `published_at` fra `Last-Modified`, som Fiskeridirektoratet
setter presist. Her er den samme headeren en CMS-MIGRERINGSDATO. Målt
26.08.2026 på to uavhengige verter:

    hi.no/resources/rapport-2020_ekspertgruppen_final.pdf
        Last-Modified: Fri, 05 Aug 2022 12:39:43 GMT   (rapport fra nov. 2020)
    trafikklyssystemet.no/.../W Rapport ekspertgruppe 2017.pdf
        Last-Modified: Thu, 10 Mar 2022 11:20:43 GMT   (rapport fra okt. 2017)
    trafikklyssystemet.no/.../Rapport2018_final.pdf
        Last-Modified: Thu, 10 Mar 2022 11:40:00 GMT   (rapport fra nov. 2018)

To verter, tre kropper, samme svar: headeren sier når fila ble flyttet
inn i dagens publiseringsløsning. Brukt som `published_at` ville den
datert 2017-rapporten til 2022 og lest revisjonsaksen baklengs for hele
serien.

Det som finnes er PDF-ens egen `/CreationDate`, satt av verktøyet som
laget dokumentet. Målt på de fem kroppene:

    2016+2017   D:20171006061014Z      Word / Quartz PDFContext
    2018        D:20181120124257+00    Microsoft Word
    2020        D:20201123130644+01    Microsoft Word 2016
    2021        D:20211111154825+01    Microsoft Word 2016
    2022        D:20221201103434+01    Microsoft Word 2016

Alle fem faller i vurderingsårets oktober-desember, som er når
ekspertgruppen leverer. Den er LEST fra dokumentet, ikke utledet av en
publiseringsplan — se CLAUDE.md 1b-7 punkt 2.

**Og den er vaktet.** `/CreationDate` er eksporttidspunktet, ikke
nødvendigvis utgivelsen: 2016/2017-kroppen er kjørt gjennom «Mac OS X
Quartz PDFContext», altså re-eksportert. Faller datoen utenfor
[nyeste vurderingsår, nyeste vurderingsår + 1], er den en re-eksport og
ikke en utgivelse, og da settes `published_at` TOM med en advarsel. Se
`_utgitt()`. Alle fem kroppene passerer i dag; vakten finnes for den
sjette.

## Wayback gir TILGANG, ikke proveniens

2021- og 2022-rapportene ligger på regjeringen.no, som svarer 403 på
både artikkelsider og direkte PDF-er for oss. Kroppene hentes derfor via
Internet Archive.

Merk hva som IKKE endrer seg av det: `X-Archive-Orig-Last-Modified`
bevarer opphavets `Last-Modified` — og opphavets `Last-Modified` er
migreringsdatoen målt over. Wayback flytter ikke problemet, den bevarer
det. `/CreationDate` leses av kroppen og er den samme uansett hvilken
adresse kroppen kom fra.

## Én uttrekksfunksjon per rapportår

Den viktigste designbeslutningen, og den er tatt fordi rapportene MÅLT
er forskjellige dokumenter:

    kropp        sider   Tabell med metodekolonner   Vindu per PO
    2016+2017      64    nei (kategori i prosa)      nei — standardisert 40 dager
    2018           27    ja, UTEN usikkerhet         nei
    2020          107    ja, med usikkerhet + pil    JA, som datoer
    2021          109    ja x2 (2020 og 2021)        nei
    2022          130    nei — SHELF, kategori+usikkerhet i prosa

2022 byttet metode helt: ekspertgruppen gikk over til SHELF-elisitering
med sannsynlighetsfordeling per kategori, og metodetabellen finnes ikke
lenger. 2018-tabellen koder usikkerhet som CELLEFARGE («Farger på rutene
markerer liten, middels og stor usikkerhet»), som ikke finnes i teksten
i det hele tatt.

En generisk parser over den spredningen ville gitt riktig FORM og feil
TALL — prosjektets egen feilklasse, se CLAUDE.md 1b-2. Derfor er
`RAPPORTER` en tabell av kropper med hver sin uttrekksfunksjon, og
`parse()` NEKTER å emittere for et år ingen funksjon dekker.

## Tabellene leses med `extraction_mode="layout"`

Uten den kollapser kolonnene til en tokenstrøm, og en rad med TOMME
celler kan ikke tilordnes metode: PO1 i 2020 har ingen trål, ingen bur
og ingen SINTEF, så de åtte kolonnene kommer ut som fem tokens. Med
layout beholdes x-posisjonene, og hver celle havner i sin kolonne.

To feller i de faktiske kroppene, begge håndtert i `_tabellrader()`:

* **Superskript på egen linje.** PO12 i 2020 og PO4/PO12 i 2021 får
  usikkerhetssuffikset på linja OVER grunnlinja. Uten sammenslåing blir
  «Lav» stående uten usikkerhet, og «lit» forsvinner.
* **Celler med mellomrom.** «Høy mid» (PO3 Bur, 2020) er én celle. Den
  slås sammen fordi begge tokenene faller i samme kolonne.

## Hva som IKKE trekkes ut, med vilje

* **Usikkerhet fra 2018-tabellen.** Den er cellefarge. Usikkerheten for
  hovedkonklusjonen leses i stedet av prosalinja «Usikkerhet: ...» under
  hvert PO; per metode finnes den ikke i tekst.
* **VIs scenariomarkører `*` og `**` i 2018.** Fotnoten definerer dem som
  spriket mellom forventet og verste scenario. Det er en annen skala enn
  liten/middels/stor, og å presse den inn i samme felt ville gjort to
  ulike ting like. Markørene strippes fra kategorien.
* **Sammensatte celler beholdes sammensatt.** «Mod/Lav» i 2018 er
  kildens egen tvetydighet, og lagres som `moderat/lav`. En analyse som
  slår opp i en kategoriordbok får KeyError, som er meningen — samme
  prinsipp som at `float("<1")` skal kaste.

## Ulikheter lagres ORDRETT

«< 1 %» og «under 1 %» er kildens faktiske utsagn, ikke tall den
avrundet. PO1 i 2020: «Modellert område med forhøyet påvirkning utgjør
< 1 % av det kystnære arealet», og «både uvektet og vektet var under
1 % samtlige år».

`value` blir da `"<1"`. Å skrive `0.5` ville vært oppdiktet presisjon og
`1` ville vært feil vei. En analyse som møter en ulikhet skal STOPPE og
ta stilling — `analyse/ekspertgruppen_celler.tolk()` returnerer
`(relasjon, tall)` og tvinger kalleren til det.

## Sikkerhet per celle

Hver verdi får et søsterfelt `<felt>__sikkerhet` med kildens lesemåte:

    tabell           lest fra en tabellcelle, maskinelt
    lopende_tekst    lest fra et avsnitt, maskinelt

Den tredje graden — verifisert av et menneske — ligger IKKE her. Den kan
ikke: snapshots er append-only, og et menneske som leser rapporten i
morgen kan ikke skrive om en fil fra i dag. Verifikasjonen føres i
`analyse/fasit/ekspertgruppen-verifisert.csv` og legges på ved LESING,
mot verdien og kroppens sha256 — så en re-parse som flytter verdien
opphever verifikasjonen i stedet for å arve den. Se
`analyse/ekspertgruppen_celler.py`.

**Kjent følge for feltvakten:** `__sikkerhet`-feltene er konstante
innenfor ett snapshot, så `minoritet` er 0 og `health._vurder_innhold()`
teller nullstrekk. Med én kjøring i året treffer standardgrensen på 13
tidligst i 2039. Det er ikke dempet med en høyere terskel, fordi
alarmen da ville vært SANN: den ville betydd at ingen har verifisert en
eneste celle på tretten år. Se docs/KILDE-EKSPERTGRUPPEN.md punkt 7.

## `min_dager_mellom = 7` for en årlig kilde

Samme resonnement som biomasse, og av samme grunn: sju betyr ikke «det
kommer en rapport hver uke», det betyr «tilby kilden til kjøringen hver
uke og la `finnes_allerede()` avgjøre».

Her er begrunnelsen sterkere enn for biomasse, fordi
publiseringsmåneden IKKE er fast. Målt på de fem kroppene: oktober
(2017), november (2018, 2020, 2021) og desember (2022) — og
departementet la ut 2024-vurderingen i juni 2025 og 2025-vurderingen i
desember 2025. Et etterslep i dager ville måttet gjette hvilken måned,
og gjettet ville vært feil annethvert år.

Steg 2b i `run.py` hopper over kilden uten å hente så lenge året ligger
skrevet, så kostnaden er null nedlastinger mellom rapportene.
"""

from __future__ import annotations

import datetime as dt
import io
import logging
import re
from typing import Callable, Iterable, NamedTuple

import httpx
import pypdf

from core.config import get
from core.contract import Observation, Source
from sources import _http

# pypdf logger på WARNING om deler av dokumentet den ikke tolker fullt ut
# («Rotated text discovered», «Ignoring wrong pointing object»). Begge
# gjelder objekter og roterte figurtekster vi ikke leser — tabellene og
# avsnittene kommer ut hele.
#
# Den påstanden er ikke tatt på tro. `_kryssjekk()` leser hovedkonklusjonen
# TO ganger av hver kropp — én gang fra tabellen og én gang fra avsnittet
# under hvert produksjonsområde — og krever at de stemmer for alle tretten
# områdene. Skulle en advarsel bety at noe faktisk manglet, ville de to
# lesingene sprikt, og uttrekket felt seg selv.
#
# Meldingene dempes fordi en backfill over fem kropper ellers drukner i
# ~200 linjer som ikke gjelder noe vi bruker. Se
# docs/KILDE-EKSPERTGRUPPEN.md punkt 4.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# ------------------------------------------------------------- konstanter

ANTALL_PO = 13

# Kildens tre kategorier, normalisert. Terskler oppgitt av rapporten selv
# (2020, kap. 5): lav < 10 %, moderat 10-30 %, høy > 30 %.
LAV, MODERAT, HOY = "lav", "moderat", "hoy"

# Ordformer vi har SETT i de fem kroppene. Lista er lukket med vilje: en
# form vi ikke kjenner skal felle uttrekket, ikke gjettes inn i en av de
# tre. «Mod» og «Moderat» opptrer i hver sin rapport, «Høy» og «Hoy»
# etter hvordan PDF-en koder ø.
KATEGORIORD = {
    "lav": LAV,
    "mod": MODERAT, "moderat": MODERAT,
    "høy": HOY, "hoy": HOY,
}

# Samme, for usikkerhet. «lit» og «liten» er samme ord forkortet ulikt i
# 2020- og 2021-tabellen; «mid» og «middels» likeså.
USIKKERHETSORD = {
    "lit": "liten", "liten": "liten",
    "mid": "middels", "middels": "middels",
    "stor": "stor",
}

# Pilene i tabellen sier hvilken vei usikkerheten for «moderat» peker.
# 2021 innførte ↕ («over, under eller begge»).
RETNINGER = {"↑": "opp", "↓": "ned", "↕": "begge"}

# Metodene ekspertgruppen vurderer hvert PO med. Nøkkelen er feltnavnet
# vårt, verdien er kolonneetiketten slik den står i tabellen — og den er
# ikke lik mellom rapportene, så hver kropp oppgir sine egne.
METODE_TRAAL = "traal"
METODE_RUSE = "ruse_garn"
METODE_BUR = "bur"
METODE_HI_SMITTE = "hi_smittepress"
METODE_HI_VS = "hi_virtuell_smolt"
METODE_VI_VS = "vi_virtuell_smolt"
METODE_SINTEF_VS = "sintef_virtuell_smolt"

# Feltnavn. Rekkefølgen her er rekkefølgen observasjonene kommer ut i, og
# den er stabil mellom kjøringer med vilje: en parquet-fil skal ikke få
# nytt innhold i git bare fordi en dict ble iterert annerledes.
F_KATEGORI = "kategori"
F_USIKKERHET = "kategori_usikkerhet"
F_RETNING = "kategori_retning"

F_VINDU_START = "utvandring_start"
F_VINDU_SLUTT = "utvandring_slutt"
F_VINDU_MEDIAN = "utvandring_median"
F_VINDU_MEDIAN_UKE = "utvandring_median_uke"

F_HI_VS_VEKTET = "hi_virtuell_smolt_vektet"
F_HI_VS_UVEKTET = "hi_virtuell_smolt_uvektet"
F_AREALANDEL = "hi_smittepress_arealandel"
F_ROC = "hi_smittepress_roc_indeks"

# Lesemåten, lagret SAMMEN med verdien. Se modulens docstring.
SIKKERHET_SUFFIKS = "__sikkerhet"
FRA_TABELL = "tabell"
FRA_TEKST = "lopende_tekst"


class Rapportfeil(RuntimeError):
    """Kroppen kom, men ikke i den formen uttrekket kjenner.

    Egen type fordi den betyr noe annet enn et nettverksavbrudd: den sier
    at PDF-en ikke er den vi trodde, eller at uttrekket må skrives om.
    Kroppen er arkivert, så det er en re-parse og ikke tapt historikk.
    """


class Aarmangler(RuntimeError):
    """Året finnes ikke i denne kroppen.

    Kastes framfor å skrive et tomt snapshot. Et tomt snapshot ville sett
    vellykket ut, låst året mot senere skriving via `finnes_allerede()`,
    og gjort hullet permanent i en append-only-serie.
    """


# ------------------------------------------------------------- kalender

def siste_dag(aar: int) -> str:
    """ISO-datoen et snapshot for dette vurderingsåret BÆRER.

    Årets siste dag, av samme grunn som biomasse bruker månedens siste:
    `observed_at` er slutten av perioden raden beskriver. Vurderingen
    gjelder utvandringssesongen, men den er en uttalelse om ÅRET, og det
    er året rapporten selv navngir i tittelen.

    Bieffekt som er verdt å ha: datoen er også en gyldig månedsslutt, så
    de samme filnavnene sorterer riktig sammen med resten av repoet.
    """
    return f"{aar}-12-31"


def aar_av(observed_at: str) -> int:
    """Vurderingsåret for en gyldighetsdato. Kaster på alt annet enn
    årets siste dag.

    Kontrollen er ikke pedanteri. Ett snapshot er ett tidspunkt, og
    filnavnet er det eneste alt nedstrøms leser datoen fra (F6). Et
    snapshot som het 2020-06-15 ville påstått at ekspertgruppen uttalte
    seg om midten av juni.
    """
    d = dt.date.fromisoformat(observed_at)
    if (d.month, d.day) != (12, 31):
        raise ValueError(
            f"observed_at {observed_at} er ikke årets siste dag. "
            f"Ekspertgruppen vurderer et ÅR, og et snapshot som bærer en "
            f"annen dato lyver om hvilken periode det gjelder. Mente du "
            f"{siste_dag(d.year)}?"
        )
    return d.year


# ------------------------------------------------------------- PDF-lesing

def _sider(rå: bytes, layout: bool) -> list[str]:
    """PDF-bytes til én tekststreng per side.

    `layout=True` beholder x-posisjonene og er det tabellene leses med;
    `layout=False` gir løpende tekst med bevarte ordmellomrom, som er det
    avsnittene leses med. Begge trengs, og de brukes til hver sitt.
    """
    try:
        leser = pypdf.PdfReader(io.BytesIO(rå))
        modus = "layout" if layout else "plain"
        return [side.extract_text(extraction_mode=modus) or ""
                for side in leser.pages]
    except Exception as e:                       # pypdf kaster mange typer
        raise Rapportfeil(
            f"Klarte ikke lese PDF-en ({type(e).__name__}: {e}). Kroppen er "
            f"arkivert, så dette er en re-parse og ikke tapt historikk."
        ) from e


def _flat(sider: list[str]) -> str:
    """Alle sider som én streng med normaliserte mellomrom.

    PDF-ene bryter setninger over linjer og limer inn harde bindestreker
    og doble mellomrom fra ordelingen. Et regex som skal treffe «HI
    virtuell smolt: Den gjennomsnittlige ...» må se teksten uten dem.
    """
    return " ".join(" ".join(sider).split())


def _utgitt(rå: bytes, nyeste_aar: int,
            advarsler: list[str] | None = None) -> str:
    """`published_at` lest av PDF-ens `/CreationDate`, normalisert til UTC.

    Returnerer ISO-8601 i UTC, eller TOM STRENG. Tom er «vet ikke», og
    den er det ærlige svaret — ikke hentetidspunktet, og ikke
    vurderingsåret. Se Observation.published_at.

    ## Hvorfor grunnen kommer ut gjennom `advarsler` og ikke som returverdi

    Fordi `test_ingen_kilde_setter_published_at_uten_a_normalisere`
    leser koden STATISK: den krever at `self.published_at = ...` er et
    direkte kall til en funksjon som er registrert og oppførselstestet
    som UTC-normaliserer. En tuppel som pakkes ut i to variabler først
    ser ut som en tilordning fra et navn, og vakten kan ikke se hva
    navnet inneholder.

    Første utkast gjorde nettopp det, og vakten felte det — med rette.
    Formen på tilordningen ER egenskapen som kan etterprøves, og en
    bekvemmelighet som ødelegger den er ikke en bekvemmelighet.

    ## Vakten

    `/CreationDate` er eksporttidspunktet. For fire av fem kropper er det
    også utgivelsen, men 2016/2017-kroppen har `/Producer: Mac OS X
    Quartz PDFContext` — den er kjørt gjennom en re-eksport, og en
    re-eksport kan skje når som helst.

    Derfor kreves datoen å ligge i [nyeste vurderingsår, +1]. Nedre
    grense fordi en rapport ikke kan skrives før året den vurderer er
    omme; øvre fordi ekspertgruppen leverer på høsten samme år eller
    tidlig året etter. Faller den utenfor, er verdien en re-eksport og
    ikke en utgivelse, og da SKRIVES INGENTING framfor å gjette.

    Målt: alle fem kroppene ligger i oktober-desember i vurderingsåret,
    altså godt innenfor. Vakten finnes for den sjette.
    """
    try:
        meta = pypdf.PdfReader(io.BytesIO(rå)).metadata or {}
        rå_dato = meta.get("/CreationDate")
        # Metadataene kan være indirekte objekter (2016/2017-kroppen er).
        if hasattr(rå_dato, "get_object"):
            rå_dato = rå_dato.get_object()
    except Exception as e:
        return _si_fra(advarsler,
                       f"ekspertgruppen: klarte ikke lese PDF-metadata "
                       f"({type(e).__name__}: {e}). published_at settes tom.")

    if not rå_dato:
        return _si_fra(advarsler,
                       "ekspertgruppen: kroppen har ingen `/CreationDate`. "
                       "Da vet vi ikke når kilden utga den, og published_at "
                       "settes tom — en gjettet dato er verre enn ingen.")

    naar = _les_pdf_dato(str(rå_dato))
    if naar is None:
        return _si_fra(advarsler,
                       f"ekspertgruppen: `/CreationDate` {rå_dato!r} lot seg "
                       f"ikke tolke (måned og dag kreves — se "
                       f"`_les_pdf_dato`). published_at settes tom.")

    if not (nyeste_aar <= naar.year <= nyeste_aar + 1):
        return _si_fra(
            advarsler,
            f"ekspertgruppen: `/CreationDate` er {naar.date().isoformat()}, "
            f"utenfor [{nyeste_aar}, {nyeste_aar + 1}] for en rapport som "
            f"vurderer {nyeste_aar}. Det er et RE-EKSPORTTIDSPUNKT, ikke en "
            f"utgivelse — published_at settes tom framfor å datere kildens "
            f"utgivelse etter når noen åpnet fila i en annen PDF-motor."
        )

    # DEN ENE normaliseringen. Alt annet i denne funksjonen er vakthold.
    # DEN ENE normaliseringen. Alt annet i funksjonen er vakthold, og
    # hvert avslag går gjennom `_si_fra` slik at returtypen forblir én
    # streng — se docstringen om hvorfor formen på tilordningen betyr
    # noe for `test_ingen_kilde_setter_published_at_uten_a_normalisere`.
    return naar.astimezone(dt.timezone.utc).isoformat()


def _si_fra(advarsler: list[str] | None, grunn: str) -> str:
    """Legger grunnen i lista og returnerer tom `published_at`.

    Finnes for at `_utgitt` skal kunne ha ÉN returtype. Se der for
    hvorfor formen på tilordningen er en egenskap som må bevares.
    """
    if advarsler is not None:
        advarsler.append(grunn)
    return ""


_PDF_DATO = re.compile(
    r"D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?"
    r"(?:(Z|[+-])(\d{2})'?(\d{2})?)?"
)


def _les_pdf_dato(tekst: str) -> dt.datetime | None:
    """`D:20201123130644+01'00'` -> tidssone-bevisst datetime.

    Egen leser fordi formatet er PDF-spesifikt (ISO 32000, 7.9.4) og
    hverken `datetime.fromisoformat` eller `email.utils` tar det.

    ## Måned og dag KREVES, selv om standarden gjør dem valgfrie

    ISO 32000 tillater `D:2020` — alt etter årstallet kan utelates. Vi
    NEKTER den formen likevel, og det er et valg, ikke en forglemmelse.

    To grunner. Ingen av de fem kroppene har en slik dato; å støtte et
    format vi ikke har sett er å anta noe om det (CLAUDE.md regel 4). Og
    tolkningen ville uansett vært et gjett: `D:2020` som 2020-01-01
    daterer en rapport utgitt i november til 1. januar, ti måneder for
    tidlig. `published_at` sammenlignes LEKSIKOGRAFISK i
    `snapshot.publisert()` og `diff.revisjon()`, så en oppdiktet
    januardato kan sortere foran en ekte påstand fra året før.

    `None` gir tom `published_at` med advarsel, som er det ærlige svaret.
    """
    m = _PDF_DATO.match(tekst.strip())
    if not m:
        return None
    aar, mnd, dag = int(m.group(1)), int(m.group(2)), int(m.group(3))
    t, mi, s = (int(m.group(i) or 0) for i in (4, 5, 6))
    tegn, tt, tm = m.group(7), int(m.group(8) or 0), int(m.group(9) or 0)

    if tegn in (None, "Z"):
        sone = dt.timezone.utc
    else:
        forskyv = dt.timedelta(hours=tt, minutes=tm)
        sone = dt.timezone(-forskyv if tegn == "-" else forskyv)
    try:
        return dt.datetime(aar, mnd, dag, t, mi, s, tzinfo=sone)
    except ValueError:
        return None


# ------------------------------------------------------------- tabeller

def _overlegg(a: str, b: str) -> str:
    """To linjer lagt oppå hverandre, tegn for tegn.

    Brukes bare på tabellhoder som er brutt over flere linjer. Poenget er
    at x-POSISJONENE må overleve: kolonnetilordningen i `_tabellrader`
    måler avstand til overskriftens senter, så en sammenslåing som endret
    lengden ville flyttet hver eneste kolonne.
    """
    bredde = max(len(a), len(b))
    a, b = a.ljust(bredde), b.ljust(bredde)
    return "".join(x if x != " " else y for x, y in zip(a, b))


def _tabellrader(side: str, aarmerke: str,
                 etiketter: list[str]) -> dict[str, list[str]]:
    """Rå celletekst per PO fra en tabell i en layout-ekstrahert side.

    `etiketter` er kolonneoverskriftene ORDRETT slik de står i kroppen,
    inkludert den første (som er årstallet eller «Prod.»). Rekkefølgen er
    kolonnerekkefølgen, og den er kildens — ikke vår.

    ## Hvorfor tilordning etter SENTER og ikke etter kolonnegrense

    Cellene er sentrert under overskriftene, ikke venstrestilte, og
    kolonnebreddene varierer med den bredeste cellen. En grense midt
    mellom to overskrifter treffer derfor feil for smale celler i brede
    kolonner. Nærmeste overskriftssenter er stabilt for alle fem
    kroppene: verifisert celle for celle mot 2020- og 2021-tabellene.

    ## De to fellene i de faktiske kroppene

    **Superskript på egen linje.** PDF-en legger usikkerhetssuffikset på
    en egen linje OVER grunnlinja når raden er høy nok — PO12 i 2020,
    PO4 og PO12 i 2021. En slik linje har ingen kategoriord i seg, bare
    `lit`/`mid`/`stor` og piler. Den bufres og limes på NESTE PO-rad, i
    riktig kolonne.

    **Celler med mellomrom.** «Høy mid» (PO3 Bur, 2020) og «Lav stor»
    (PO6 Trål, 2021) er én celle brutt av ordelingen. To tokens som
    havner i samme kolonne limes sammen.
    """
    linjer = side.split("\n")

    hode = None
    for i, linje in enumerate(linjer):
        if linje.lstrip().startswith(aarmerke) and "Hovedk" in linje:
            hode = i
            break
        if linje.lstrip().startswith(aarmerke) and "Konklusj" in linje:
            hode = i
            break
    if hode is None:
        raise Rapportfeil(
            f"Fant ingen tabellhode som begynner med {aarmerke!r} og "
            f"inneholder «Hovedk» eller «Konklusj» på siden. Formatet er "
            f"endret — kroppen er arkivert, så dette er en re-parse."
        )

    # 2018-hodet går over TO linjer: «Vaktbur» og «Smitte-press» står på
    # den andre, «Trål-» og «Sjøørret» på den første. Linjene legges
    # oppå hverandre tegn for tegn, slik at x-posisjonene beholdes og
    # alle etikettene finnes i én streng. Bare linjer som IKKE begynner
    # med et PO-nummer slås inn — ellers ville første datarad blitt del
    # av hodet.
    hodetekst = linjer[hode]
    for ekstra in linjer[hode + 1:hode + 3]:
        forste = ekstra.split()[0] if ekstra.split() else ""
        if re.fullmatch(r"\d{1,2}", forste):
            break
        hodetekst = _overlegg(hodetekst, ekstra)

    sentre: list[float] = []
    i = 0
    for etikett in etiketter:
        j = hodetekst.find(etikett, i)
        if j < 0:
            raise Rapportfeil(
                f"Kolonneoverskriften {etikett!r} står ikke i tabellhodet "
                f"{hodetekst.strip()!r}. Formatet er endret."
            )
        sentre.append(j + len(etikett) / 2)
        i = j + len(etikett)

    rader: dict[str, list[str]] = {}
    ventende: list[str] | None = None

    for linje in linjer[hode + 1:]:
        if not linje.strip():
            continue
        tokens = [(m.start(), m.end(), m.group(0))
                  for m in re.finditer(r"\S+", linje)]
        if not tokens:
            continue

        def kolonne(start: int, slutt: int) -> int:
            midt = (start + slutt) / 2
            # Kolonne 0 er PO-nummeret og er aldri et celleinnhold.
            return min(range(1, len(sentre)),
                       key=lambda n: abs(midt - sentre[n]))

        forste = tokens[0][2]
        if re.fullmatch(r"\d{1,2}", forste) and 1 <= int(forste) <= ANTALL_PO:
            celler = [""] * len(etiketter)
            for start, slutt, tekst in tokens[1:]:
                k = kolonne(start, slutt)
                celler[k] = (celler[k] + tekst) if celler[k] else tekst
            if ventende is not None:
                for k, bit in enumerate(ventende):
                    if bit:
                        celler[k] += bit
                ventende = None
            rader[forste] = celler
            if len(rader) == ANTALL_PO:
                break
            continue

        # Ren superskriptlinje: bare usikkerhetsformer og piler.
        if all(re.fullmatch(r"[↑↓↕]*(lit|liten|mid|middels|stor)[↑↓↕]*",
                            tekst, re.I)
               for _, _, tekst in tokens):
            ventende = [""] * len(etiketter)
            for start, slutt, tekst in tokens:
                ventende[kolonne(start, slutt)] = tekst

    if len(rader) != ANTALL_PO:
        raise Rapportfeil(
            f"Leste {len(rader)} av {ANTALL_PO} produksjonsområder fra "
            f"tabellen (fant {sorted(rader, key=int)}). Formatet er endret "
            f"— kroppen er arkivert, så dette er en re-parse."
        )
    return rader


_CELLE = re.compile(
    r"^(lav|moderat|mod|høy|hoy)([↑↓↕]?)(lit|liten|mid|middels|stor)?([↑↓↕]?)$",
    re.I,
)


def _les_celle(tekst: str) -> tuple[str, str, str] | None:
    """Celletekst -> (kategori, usikkerhet, retning). None for tom celle.

    Usikkerhet og retning er tomme strenger der cellen ikke bærer dem —
    2018-tabellen har ingen usikkerhet i det hele tatt (den er
    cellefarge), og bare «moderat» får pil.

    ## Sammensatte celler

    «Mod/Lav» og «Mod/Høy» i 2018 er kildens egen tvetydighet: to
    kategorier i én celle. De normaliseres hver for seg og settes sammen
    igjen med skråstrek — `moderat/lav`. Verdien er da ikke slåbar opp i
    en kategoriordbok, og det er meningen: en analyse skal stoppe på den
    og ta stilling, ikke velge den første halvdelen stilltiende.

    ## En ukjent form KASTER

    Ikke «ukjent kategori» og ikke tom. Et fjortende ord vi ikke kjenner
    ville lagt seg ved siden av de tre og telt med i enhver fordeling
    uten at noen så det — samme begrunnelse som `biomasse._po()` har for
    å kaste på en ukjent PO-kode.
    """
    t = "".join(tekst.split())
    # VIs scenariomarkører i 2018-tabellen. Fotnoten definerer dem som
    # spriket mellom forventet og verste scenario — en annen skala enn
    # liten/middels/stor, og den bæres ikke videre. Se modulens docstring.
    t = t.rstrip("*")
    if not t:
        return None

    if "/" in t:
        deler = [_les_celle(d) for d in t.split("/")]
        if any(d is None for d in deler):
            raise Rapportfeil(f"Sammensatt celle {tekst!r} har en tom del.")
        return ("/".join(d[0] for d in deler),  # type: ignore[index]
                "", "")

    m = _CELLE.match(t)
    if not m:
        raise Rapportfeil(
            f"Celleteksten {tekst!r} er ikke en form vi kjenner. Kjente "
            f"former er kategori (Lav/Mod/Moderat/Høy) med valgfri "
            f"usikkerhet (lit/liten/mid/middels/stor) og valgfri pil "
            f"(↑↓↕). Formatet er endret — kroppen er arkivert."
        )
    kategori = KATEGORIORD[m.group(1).lower()]
    usikkerhet = USIKKERHETSORD[m.group(3).lower()] if m.group(3) else ""
    retning = RETNINGER.get(m.group(2) or m.group(4) or "", "")
    return kategori, usikkerhet, retning


# --------------------------------------------------------- tekstuttrekk

# Navnet på hvert produksjonsområde, lest av seksjonsoverskriften. Alle
# fem kroppene skriver «Produksjonsområde 4: Nordhordland til Stadt».
_PO_OVERSKRIFT = re.compile(
    r"Produksjonsområde\s+(\d{1,2})\s*:\s*([^\n]{3,60}?)\s*(?=\n|$)")


def _po_navn(sider: list[str]) -> dict[str, str]:
    """Områdenavn fra rapportens egne seksjonsoverskrifter.

    Leses av kroppen framfor å hardkodes. Navnene er ikke helt stabile
    mellom rapportene («Nordmøre og Sør-Trøndelag» / «Nordmøre til
    Sør-Trøndelag»), og en hardkodet liste ville stille overskrevet
    kildens egen skrivemåte.
    """
    navn: dict[str, str] = {}
    for side in sider:
        for m in _PO_OVERSKRIFT.finditer(side):
            po = str(int(m.group(1)))
            if 1 <= int(po) <= ANTALL_PO:
                # Sidetallet limer seg på slutten av overskriften i den
                # flate ekstraksjonen («Nordhordland til Stadt 35»).
                rent = re.sub(r"\s+\d+$", "", " ".join(m.group(2).split()))
                # SISTE forekomst vinner, ikke første: innholdsfortegnelsen
                # står foran i dokumentet og har samme ordlyd som den ekte
                # overskriften. Se `_seksjoner` for hele begrunnelsen.
                navn[po] = rent
    return navn


def _seksjoner(flat: str) -> dict[str, str]:
    """Teksten som hører til hvert PO, fra overskrift til neste overskrift.

    Trengs fordi avsnittene («HI virtuell smolt: ...») ikke navngir
    området selv — de står under en overskrift. Uten oppdelingen ville et
    regex over hele dokumentet gitt PO1s tall til PO2.

    ## SISTE forekomst vinner

    Innholdsfortegnelsen har nøyaktig samme ordlyd som de ekte
    overskriftene, og den står FØRST i dokumentet. Den ekte seksjonen er
    derfor alltid den siste av de to.

    Det var ikke åpenbart hvorfor «lengste vinner» ikke duger, og feilen
    er verdt å skrive ned: for det SISTE produksjonsområdet ligger
    innholdsfortegnelsens oppføring rett foran hele brødteksten, så dens
    utsnitt strekker seg fra innholdsfortegnelsen til første ekte
    overskrift — 119 532 tegn i 2022-kroppen, mot ~5 000 for den ekte
    seksjonen. Lengden pekte altså konsekvent på feil utsnitt for PO13,
    og bare for PO13. Rekkefølgen peker riktig for alle tretten.
    """
    treff = list(re.finditer(r"Produksjonsområde\s+(\d{1,2})\s*:", flat))
    ut: dict[str, str] = {}
    for i, m in enumerate(treff):
        po = str(int(m.group(1)))
        if not 1 <= int(po) <= ANTALL_PO:
            continue
        slutt = treff[i + 1].start() if i + 1 < len(treff) else len(flat)
        ut[po] = flat[m.start():slutt]
    return ut


# «< 1», «under 1», «34», «2 og 32». Tallet beholdes ORDRETT med
# relasjonen foran der kilden oppgir en ulikhet. Se modulens docstring.
_ULIKHET = re.compile(r"(<|>|under|over)?\s*(\d{1,3}(?:[.,]\d+)?)\s*%")


def _prosent(tekst: str) -> str | None:
    """Første prosentverdi i teksten, med relasjon der den finnes.

    «34 %» -> `"34"`.  «< 1 %» -> `"<1"`.  «under 1 %» -> `"<1"`.

    Ordformene «under» og «over» oversettes til `<` og `>` fordi de er
    det samme utsagnet — men TALLET røres ikke, og ingen ulikhet gjøres
    om til et punktestimat.
    """
    m = _ULIKHET.search(tekst)
    if not m:
        return None
    rel = (m.group(1) or "").lower()
    tegn = {"<": "<", "under": "<", ">": ">", "over": ">"}.get(rel, "")
    return f"{tegn}{m.group(2).replace(',', '.')}"


MAANEDER = {
    "januar": 1, "februar": 2, "mars": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11,
    "desember": 12,
}

# «24. april – 5. juni, med 50 % utvandring satt til 17. mai (uke 20)»
# Bindestreken varierer mellom -, – og —; «med/mens/med dato for» varierer.
_VINDU = re.compile(
    r"Antatt tidspunkt for utvandring:\s*"
    r"(\d{1,2})\.\s*(" + "|".join(MAANEDER) + r")\s*[-–—]\s*"
    r"(\d{1,2})\.\s*(" + "|".join(MAANEDER) + r")\s*,\s*"
    r"[^.]*?(\d{1,2})\.\s*(" + "|".join(MAANEDER) + r")\s*"
    r"\(uke\s*(\d{1,2})\)",
    re.I,
)


def _vindu(seksjon: str, aar: int) -> dict[str, str] | None:
    """Utvandringsvinduet for ett PO, som DATOER.

    Kilden oppgir datoer — «24. april – 5. juni» — og et uketall bare for
    medianen. Uketallet for start og slutt er derfor VÅR avledning, og
    den er årsavhengig: samme dato faller i ulik ISO-uke fra år til år.
    Den gjøres ikke her. Analyselaget regner den om når det trenger uker,
    og står da for regnestykket selv.

    Året kommer fra rapportens eget vurderingsår. Det er ikke et gjett:
    vinduet står i seksjonen for det året rapporten vurderer.
    """
    m = _VINDU.search(seksjon)
    if not m:
        return None

    def dato(dag: str, maaned: str) -> str:
        return dt.date(aar, MAANEDER[maaned.lower()], int(dag)).isoformat()

    return {
        F_VINDU_START: dato(m.group(1), m.group(2)),
        F_VINDU_SLUTT: dato(m.group(3), m.group(4)),
        F_VINDU_MEDIAN: dato(m.group(5), m.group(6)),
        F_VINDU_MEDIAN_UKE: str(int(m.group(7))),
    }


# ------------------------------------------------------- celler og prosa

class Celle(NamedTuple):
    """Én uttrukket verdi, med lesemåten sin.

    Uttrekksfunksjonene returnerer disse; `Ekspertgruppen.parse()` gjør
    dem om til `Observation`-par (verdien og `<felt>__sikkerhet`). Skillet
    finnes for at en uttrekksfunksjon skal kunne skrives uten å kjenne
    observasjonsformatet — den vet hva den leste og hvor, ikke hvordan
    kjernen lagrer det.
    """
    po: str
    felt: str
    verdi: str
    sikkerhet: str


# «Konklusjon: Høy lakselusindusert villfiskdødelighet i 2020» (2020, 2021)
# «Konklusjon: Moderat risiko for lakselusindusert villfiskdødelighet i 2018»
_KONKLUSJON_ETT_AAR = re.compile(
    r"Konklusjon\s*:\s*(Lav|Moderat|Høy|Hoy)\b[^.]{0,80}?\b(\d{4})\b", re.I)

# «Konklusjon: Lav risiko ... både i 2016 og 2017» (2016/2017-rapporten)
_KONKLUSJON_BEGGE = re.compile(
    r"Konklusjon\s*:\s*(Lav|Moderat|Høy|Hoy)\s+risiko[^.]{0,90}?"
    r"både i\s*(\d{4})\s*og\s*(\d{4})", re.I)

# «Konklusjon: Moderat risiko i 2016 og lav risiko i 2017 for ...»
_KONKLUSJON_HVERT = re.compile(
    r"Konklusjon\s*:\s*(Lav|Moderat|Høy|Hoy)\s+risiko\s+i\s*(\d{4})\s*og\s+"
    r"(lav|moderat|høy|hoy)\s+risiko\s+i\s*(\d{4})", re.I)

# «Kategori med høyest sannsynlighet: Moderat lakselusindusert ... i 2022»
_KATEGORI_SHELF = re.compile(
    r"Kategori med høyest sannsynlighet\s*:\s*(Lav|Moderat|Høy|Hoy)\b"
    r"[^.]{0,80}?\b(\d{4})\b", re.I)

# «Usikkerhet: Middels usikkerhet for området i sin helhet» (2016-2018)
# «Usikkerhet: Konklusjonen vurderes (til)? å ha stor usikkerhet» (2020, 2021)
# «... vurderes å ha liten usikkerhet etter tidligere års ...»  (2022)
_USIKKERHET_LINJE = re.compile(
    r"Usikkerhet\s*:\s*(Liten|Middels|Stor)\s+usikkerhet\b", re.I)
_USIKKERHET_VURDERES = re.compile(
    r"vurderes\s+(?:til\s+)?å\s+ha\s+(liten|middels|stor)\s+usikkerhet", re.I)


def _kategori_i_prosa(seksjon: str, aar: int) -> str | None:
    """Hovedkonklusjonens kategori for ett PO og ett år, fra avsnittstekst.

    Tre setningsformer, én per rapportgenerasjon. Alle tre navngir ÅRET
    eksplisitt, og det er derfor de kan brukes på 2016/2017-rapporten som
    bærer to år i samme setning: «Moderat risiko i 2016 og lav risiko i
    2017» gir ulikt svar for de to årene, og det er kilden som sier det —
    ikke vi som fordeler.
    """
    m = _KONKLUSJON_HVERT.search(seksjon)
    if m:
        for kat, kat_aar in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
            if int(kat_aar) == aar:
                return KATEGORIORD[kat.lower()]
        return None

    m = _KONKLUSJON_BEGGE.search(seksjon)
    if m and aar in (int(m.group(2)), int(m.group(3))):
        return KATEGORIORD[m.group(1).lower()]

    for mønster in (_KONKLUSJON_ETT_AAR, _KATEGORI_SHELF):
        m = mønster.search(seksjon)
        if m and int(m.group(2)) == aar:
            return KATEGORIORD[m.group(1).lower()]
    return None


def _usikkerhet_i_prosa(seksjon: str) -> str | None:
    """Usikkerheten for hovedkonklusjonen, fra avsnittstekst.

    Merk at den IKKE er årsbestemt. For rapportene som dekker ett år er
    det uproblematisk. For 2016/2017-rapporten er den én linje for to år,
    og da emitteres den ikke i det hele tatt — se `_uttrekk_2017`.
    """
    for mønster in (_USIKKERHET_LINJE, _USIKKERHET_VURDERES):
        m = mønster.search(seksjon)
        if m:
            return m.group(1).lower().replace("liten", "liten")
    return None


def _slakk(ord_: str) -> str:
    """Regexbit som tåler ORDDELINGSMELLOMROM inne i et ord.

    PDF-ene setter av og til et mellomrom midt i et ord når linja er
    justert: 2018-rapportens kapittel 4 skriver «hø y risiko for
    lakselusindusert dødel ighet i to områder (3, 4)». Uten slakk fant
    `_kategorilister` bare 11 av 13 produksjonsområder for 2017, og de
    to som falt ut var nettopp de to i høy-kategorien.

    Slakken gjelder BARE kategoriordene, og bare i denne ene lesingen.
    Å normalisere bort alle enkeltmellomrom i hele dokumentet ville
    slått sammen ord som skal stå fra hverandre.
    """
    return r"\s?".join(re.escape(bokstav) for bokstav in ord_)


# HI smittekart oppgir SAMME indeks i to formuleringer, og rapportene
# bytter mellom dem uten å bruke begge for samme produksjonsområde:
#
#   2020, alle 13 PO   «Modellert område med forhøyet påvirkning utgjør
#                       34 % av det kystnære arealet»
#   2021/2022, PO2-13  «Indeksen for risiko for høy påvirkning er 27 %»
#   2021/2022, PO1     tilbake til 2020-formen
#
# At det er én størrelse er lest i rapportene, ikke sluttet av navnene —
# se docs/KILDE-EKSPERTGRUPPEN.md punkt 5b. De lagres likevel som TO
# felter, fordi ordlyden er kildens og en sammenslåing er analysens valg,
# ikke innsamlingens.
#
# Begge mønstrene tåler orddelingsmellomrom («påv irkning», «ris iko»):
# PDF-en deler ord i justerte linjer, og uten slakk falt PO7 ut av begge
# årene — 11 % i 2021 og 25 % i 2022, begge moderate verdier midt i
# fordelingen.
_AREALANDEL = re.compile(
    r"forh[øo]yet\s+" + _slakk("påvirkning") + r"\s+utgj[øo]r\s*"
    r"([^.]{0,30}?%)\s*av\s+det\s+kystn[æa]re\s+arealet", re.I)

# «er 27 %», «er moderat (33 %)», «er moderat i 2022 (15 %)» og
# «for hele produksjonsområdet er moderat (25 %)» — innskuddet mellom
# størrelsen og verbet er valgfritt og kan være flere ord.
_ROC = re.compile(
    r"Indeksen\s+for\s+" + _slakk("risiko") + r"\s+for\s+"
    + _slakk("høy") + r"\s+" + _slakk("påvirkning")
    + r"[^.%]{0,45}?\s+er\s+(?:[^\W\d_]+\s*)*\(?\s*([^.)]{0,20}?%)", re.I)

# «Gjennomsnittet vektet (22 %) ... uvektede snittet (32 %)»
_VS_VEKTET_FORST = re.compile(
    r"vektet\s*\(\s*([^)]{1,14}%)\s*\)[^.]{0,120}?uvektede?\s+snittet\s*"
    r"\(\s*([^)]{1,14}%)\s*\)", re.I)

# «ingen forskjell på uvektet (27 %) og vektet (27 %)»
_VS_UVEKTET_FORST = re.compile(
    r"uvektet\s*\(\s*([^)]{1,14}%)\s*\)\s*og\s+vektet\s*\(\s*([^)]{1,14}%)\s*\)",
    re.I)

# «både uvektet og vektet ... var under 1 % samtlige år»
_VS_BEGGE_UNDER = re.compile(
    r"b[åa]de\s+uvekt\s?et\s+og\s+vektet[^.]{0,90}?var\s+"
    r"(under|over)\s+(\d{1,3})\s*%\s*samtlige\s+[åa]r", re.I)


def _hi_avsnitt(seksjon: str, etiketter: tuple[str, ...]) -> str:
    """Teksten etter en avsnittsetikett, fram til neste etikett.

    Etikettene varierer mellom rapportene og til og med innenfor én:
    2020 skriver «Smittepress HI:» for PO1 og «HI smittepress:» for
    resten. Begge former oppgis av kalleren; her velges den som finnes.
    """
    for etikett in etiketter:
        m = re.search(re.escape(etikett) + r"\s*:", seksjon, re.I)
        if m:
            return seksjon[m.end():m.end() + 700]
    return ""


def _hi_virtuell_smolt(seksjon: str) -> list[tuple[str, str]]:
    """(felt, verdi) for HI virtuell smolt, vektet og uvektet.

    TOM LISTE er det vanlige svaret, og det er riktig. Målt på
    2020-rapporten: bare 4 av 13 produksjonsområder oppgir årets vektede
    og uvektede snitt i det hele tatt. De øvrige ni oppgir SERIENS spenn
    («varierte mellom 5 og 20 % i perioden 2012–2020») og elvenes spenn
    innen året — to andre størrelser, om andre tidsrom.

    Å lese seriens spenn som årets verdi ville vært å hente riktig FORM
    og feil TALL. Feltet er da fraværende, ikke null. Se
    docs/KILDE-EKSPERTGRUPPEN.md punkt 5 for hva det betyr for et
    kontinuerlig måltall.
    """
    tekst = _hi_avsnitt(seksjon, ("HI virtuell smolt", "HI Virtuell smolt"))
    if not tekst:
        return []

    m = _VS_VEKTET_FORST.search(tekst)
    if m:
        return [(F_HI_VS_VEKTET, _prosent(m.group(1)) or ""),
                (F_HI_VS_UVEKTET, _prosent(m.group(2)) or "")]

    m = _VS_UVEKTET_FORST.search(tekst)
    if m:
        return [(F_HI_VS_UVEKTET, _prosent(m.group(1)) or ""),
                (F_HI_VS_VEKTET, _prosent(m.group(2)) or "")]

    m = _VS_BEGGE_UNDER.search(tekst)
    if m:
        tegn = "<" if m.group(1).lower() == "under" else ">"
        verdi = f"{tegn}{m.group(2)}"
        return [(F_HI_VS_UVEKTET, verdi), (F_HI_VS_VEKTET, verdi)]

    return []


def _hi_smittepress(seksjon: str) -> list[tuple[str, str]]:
    """(felt, verdi) for HI smittekart.

    TO FELTER, ikke ett, og det er med vilje. 2020 oppgir «Modellert
    område med forhøyet påvirkning utgjør 34 % av det kystnære arealet»
    — en arealandel. 2021 og 2022 oppgir «Indeksen for risiko for høy
    påvirkning er 27 %» — en ROC-indeks.

    De KAN være samme størrelse uttrykt ulikt, og de kan la være. Vi har
    ikke sett dem defineres mot hverandre noe sted, og CLAUDE.md regel 4
    sier at det som ikke er bekreftet ikke skal antas. Å slå dem sammen
    til ett felt ville skjult et metodeskifte midt i serien og gjort en
    definisjonsendring til en verdiendring i changeloggen.
    """
    tekst = _hi_avsnitt(seksjon, ("HI smittepress", "Smittepress HI"))
    if not tekst:
        return []

    ut = []
    m = _AREALANDEL.search(tekst)
    if m:
        verdi = _prosent(m.group(1))
        if verdi:
            ut.append((F_AREALANDEL, verdi))
    m = _ROC.search(tekst)
    if m:
        verdi = _prosent(m.group(1))
        if verdi:
            ut.append((F_ROC, verdi))
    return ut


# «lav risiko for lakselusindusert dødelighet i syv produksjonsområder
#  (1, 8, 9, 10, 11, 12, 13)» — 2018-rapportens kapittel 4.
_KATEGORILISTE = re.compile(
    r"(" + "|".join(_slakk(o) for o in ("lav", "moderat", "høy", "hoy"))
    + r")\s*risiko[^.(]{0,110}?\(([^)]{1,80})\)", re.I)


def _kategorilister(avsnitt: str) -> dict[str, str]:
    """{po: kategori} fra en oppsummerende setning med PO-lister.

    2018-rapporten gjentar 2016 og 2017 slik, og det er den ENESTE
    formen de to årene finnes i der. Listene er alltid i parentes for de
    to gjentatte årene; setningen om rapportens EGET år har en variant
    uten parentes («i produksjonsområde 2, 4, 5 og 7»), og den leses
    derfor fra tabellen i stedet.
    """
    ut: dict[str, str] = {}
    for m in _KATEGORILISTE.finditer(avsnitt):
        kategori = KATEGORIORD["".join(m.group(1).lower().split())]
        for tall in re.findall(r"\d{1,2}", m.group(2)):
            if 1 <= int(tall) <= ANTALL_PO:
                ut[str(int(tall))] = kategori
    return ut


def _aarsavsnitt(flat: str, aar: int) -> str:
    """Den oppsummerende setningen om ETT år, klippet før den neste.

    Rapportene skriver årene etter hverandre i samme avsnitt:

        «... har for 2016 konkludert med lav risiko ... (1, 8, 9, ...),
        moderat ... (2, 4, 5, 6, 7) og høy ... (3). For 2017 konkluderte
        ekspertgruppen med lav risiko ... (1, 2, 6, 7, ...)»

    Et vindu på faste tegn renner over i neste år og blander to
    kategorilister. Det gjorde det: PO2 fikk «lav» fra 2017-setningen
    inn i 2016-lesingen, og kryssjekken felte uttrekket — riktig, men av
    feil grunn. Klippet går ved neste «(For|for) <årstall> konkl».
    """
    m = re.search(rf"(?:F|f)or\s+{aar}\s+konkl", flat)
    if not m:
        return ""
    rest = flat[m.start():m.start() + 900]
    neste = re.search(r"(?:F|f)or\s+\d{4}\s+konkl", rest[10:])
    return rest[:neste.start() + 10] if neste else rest


def _kryssjekk(fra_tabell: dict[str, str], fra_prosa: dict[str, str],
               hva: str) -> None:
    """Kaster hvis to uavhengige lesinger av samme kropp er uenige.

    Rapportene sier det samme to ganger: én gang i oppsummeringstabellen
    og én gang i avsnittet under hvert produksjonsområde. At de stemmer
    er ikke gitt — det er nettopp den slags stille avvik en tabellparser
    med feil kolonnetilordning ville produsert.

    Sjekken er billig og den er den eneste som kan felle et uttrekk som
    er syntaktisk vellykket og semantisk feil. Bare PO-er som finnes i
    BEGGE sjekkes; et avsnitt uten konklusjonssetning er et fravær, ikke
    et sprik.
    """
    avvik = {po: (fra_tabell[po], fra_prosa[po])
             for po in sorted(fra_tabell.keys() & fra_prosa.keys(), key=int)
             if fra_tabell[po] != fra_prosa[po]}
    if avvik:
        raise Rapportfeil(
            f"{hva}: tabellen og den løpende teksten er uenige om "
            f"{len(avvik)} produksjonsområde(r): "
            + ", ".join(f"PO{po} tabell={t!r} tekst={p!r}"
                        for po, (t, p) in avvik.items())
            + ". Uttrekket leser feil kolonne, eller kroppen er ikke den vi "
              "tror. Ingenting skrives."
        )


# ------------------------------------------------------ uttrekk per kropp
#
# Én funksjon per KROPP, ikke per år. Signaturen er
# `(sider_layout, flat, aar) -> Iterable[Celle]`, og hver av dem kjenner
# nøyaktig det ene dokumentet den er skrevet mot. Se modulens docstring
# for hvorfor det ikke er én generisk parser.


def _felles_prosa(flat: str, aar: int, med_usikkerhet: bool
                  ) -> tuple[dict[str, str], list[Celle]]:
    """Kategori (og evt. usikkerhet) per PO fra avsnittene.

    Returnerer både ordboka — som `_kryssjekk` trenger — og de ferdige
    cellene, slik at de to aldri kan komme i utakt.
    """
    kategorier: dict[str, str] = {}
    celler: list[Celle] = []

    for po, seksjon in sorted(_seksjoner(flat).items(), key=lambda p: int(p[0])):
        kategori = _kategori_i_prosa(seksjon, aar)
        if kategori is None:
            continue
        kategorier[po] = kategori
        celler.append(Celle(po, F_KATEGORI, kategori, FRA_TEKST))

        if med_usikkerhet:
            usikkerhet = _usikkerhet_i_prosa(seksjon)
            if usikkerhet:
                celler.append(Celle(po, F_USIKKERHET, usikkerhet, FRA_TEKST))

    return kategorier, celler


def _tallceller(flat: str) -> Iterable[Celle]:
    """De kontinuerlige estimatene, der rapporten oppgir dem.

    Felles for 2020, 2021 og 2022 fordi avsnittsetikettene er de samme i
    de tre. Hva som faktisk finnes varierer sterkt — se
    `_hi_virtuell_smolt` og `_hi_smittepress`.
    """
    for po, seksjon in sorted(_seksjoner(flat).items(), key=lambda p: int(p[0])):
        for felt, verdi in _hi_virtuell_smolt(seksjon):
            yield Celle(po, felt, verdi, FRA_TEKST)
        for felt, verdi in _hi_smittepress(seksjon):
            yield Celle(po, felt, verdi, FRA_TEKST)


def _metodeceller(rader: dict[str, list[str]], metoder: list[str]
                  ) -> tuple[dict[str, str], list[Celle]]:
    """Tabellrader -> metodeceller + hovedkonklusjonen per PO.

    `metoder` er feltnavnene i KOLONNEREKKEFØLGE, uten den første
    (PO-nummeret) og uten den siste (hovedkonklusjonen). Rekkefølgen er
    kildens, og den er ikke lik mellom rapportene — 2018 har ingen
    SINTEF-kolonne.
    """
    hoved: dict[str, str] = {}
    celler: list[Celle] = []

    for po in sorted(rader, key=int):
        celle_tekst = rader[po]
        for i, metode in enumerate(metoder, start=1):
            lest = _les_celle(celle_tekst[i])
            if lest is None:
                continue                       # metoden dekker ikke dette PO
            kategori, usikkerhet, retning = lest
            celler.append(Celle(po, f"metode_{metode}_kategori",
                                kategori, FRA_TABELL))
            if usikkerhet:
                celler.append(Celle(po, f"metode_{metode}_usikkerhet",
                                    usikkerhet, FRA_TABELL))
            if retning:
                celler.append(Celle(po, f"metode_{metode}_retning",
                                    retning, FRA_TABELL))

        lest = _les_celle(celle_tekst[-1])
        if lest is None:
            raise Rapportfeil(
                f"PO{po} har tom hovedkonklusjon i tabellen. Alle tretten "
                f"områder skal ha en — formatet er endret."
            )
        kategori, usikkerhet, retning = lest
        hoved[po] = kategori
        celler.append(Celle(po, F_KATEGORI, kategori, FRA_TABELL))
        if usikkerhet:
            celler.append(Celle(po, F_USIKKERHET, usikkerhet, FRA_TABELL))
        if retning:
            celler.append(Celle(po, F_RETNING, retning, FRA_TABELL))

    return hoved, celler


def _finn_tabellside(sider: list[str], aarmerke: str,
                     etiketter: list[str], hva: str) -> dict[str, list[str]]:
    """Leter gjennom sidene til én av dem gir en fullstendig tabell.

    Sidetallet slås ikke opp som en konstant. Det ville vært et tall som
    er riktig for akkurat den kroppen og stille feil for en re-eksport
    med annen paginering — og kroppene ER re-eksportert (se `_utgitt`).
    Markøren og kolonneoverskriftene er derimot kildens egen tekst.
    """
    siste_feil = ""
    for side in sider:
        if aarmerke not in side:
            continue
        try:
            return _tabellrader(side, aarmerke, etiketter)
        except Rapportfeil as e:
            siste_feil = str(e)
    raise Rapportfeil(
        f"{hva}: fant ingen fullstendig tabell i kroppen. Siste forsøk: "
        f"{siste_feil or 'ingen side inneholdt markøren ' + aarmerke!r}"
    )


def _uttrekk_2017(sider: list[str], flat: str, aar: int) -> Iterable[Celle]:
    """2016+2017-rapporten (Nilsen mfl. 2017), 64 sider.

    Ingen metodetabell: kategorien står bare i avsnittet under hvert
    produksjonsområde, i to setningsformer som begge navngir årene
    («både i 2016 og 2017» / «Moderat risiko i 2016 og lav risiko i
    2017»).

    **Usikkerhet emitteres IKKE.** Rapporten har én «Usikkerhet:»-linje
    per produksjonsområde, og den dekker begge årene under ett — også der
    kategorien er ulik mellom dem (PO2, PO4, PO6, PO7). Å feste den til
    begge årene ville påstått at ekspertgruppen sa noe den ikke sa, og å
    feste den til ett av dem ville vært et valg uten grunnlag. Kapittel 6
    oppgir usikkerhet for 2017 alene, men ikke for 2016; å ta med det ene
    og ikke det andre ville gitt et felt som ser komplett ut og er halvt.

    Kryssjekkes mot kapittel 6, som gjentar begge årene som PO-lister.
    """
    kategorier, celler = _felles_prosa(flat, aar, med_usikkerhet=False)

    # Kapittel 6 sier det samme en gang til. To lesinger av samme kropp
    # som må stemme — se `_kryssjekk`.
    avsnitt = _aarsavsnitt(flat, aar)
    if avsnitt:
        _kryssjekk(_kategorilister(avsnitt), kategorier,
                   f"ekspertgruppen {aar} (2016/2017-rapporten)")

    yield from celler


def _uttrekk_2018(sider: list[str], flat: str, aar: int) -> Iterable[Celle]:
    """2018-rapporten (Nilsen mfl. 2018), 27 sider. Dekker 2016-2018.

    To helt ulike veier inn, fordi rapporten selv behandler årene ulikt:

    * **2018** står i Tabell 2, med seks metodekolonner og ingen
      usikkerhet (den er cellefarge). Hovedkonklusjonen kryssjekkes mot
      «Konklusjon: ...»-linja under hvert PO, og usikkerheten leses av
      «Usikkerhet: ...»-linja.
    * **2016 og 2017** står bare som PO-lister i kapittel 4 («For 2017
      konkluderte ekspertgruppen med lav risiko ... i ti
      produksjonsområder (1, 2, 6, ...)»). Ingen metoder, ingen
      usikkerhet — bare kategorien.

    Det er andre gang begge de to årene uttales om, og dermed det første
    stedet revisjonsaksen har noe å måle.
    """
    if aar == 2018:
        rader = _finn_tabellside(
            sider, "Prod.",
            ["Prod.", "Trål-", "Sjøørret", "Vaktbur", "HI", "HI", "VI",
             "Konklusj"],
            "ekspertgruppen 2018")
        hoved, celler = _metodeceller(
            rader, [METODE_TRAAL, METODE_RUSE, METODE_BUR,
                    METODE_HI_SMITTE, METODE_HI_VS, METODE_VI_VS])

        kategorier, prosaceller = _felles_prosa(flat, aar, med_usikkerhet=True)
        _kryssjekk(hoved, kategorier, "ekspertgruppen 2018")

        yield from celler
        # Bare usikkerheten fra prosaen — kategorien er alt lest av
        # tabellen, og to celler for samme felt ville kollidert i
        # `snapshot.NOKKEL`.
        yield from (c for c in prosaceller if c.felt != F_KATEGORI)
        return

    # 2016 og 2017: gjentatt som PO-lister i kapittel 4.
    avsnitt = _aarsavsnitt(flat, aar)
    if not avsnitt:
        raise Aarmangler(
            f"2018-rapporten har ingen oppsummerende setning for {aar}. "
            f"Årene den gjentar er 2016 og 2017."
        )
    lister = _kategorilister(avsnitt)
    if len(lister) != ANTALL_PO:
        raise Rapportfeil(
            f"Den oppsummerende setningen for {aar} nevner "
            f"{len(lister)} av {ANTALL_PO} produksjonsområder "
            f"({sorted(lister, key=int)}). En delvis liste ville gitt et "
            f"år som ser skrevet ut og mangler områder — ingenting skrives."
        )
    for po, kategori in sorted(lister.items(), key=lambda p: int(p[0])):
        yield Celle(po, F_KATEGORI, kategori, FRA_TEKST)


def _uttrekk_2020(sider: list[str], flat: str, aar: int) -> Iterable[Celle]:
    """2020-rapporten (Vollset mfl. 2020), 107 sider.

    Den rikeste kroppen i serien, og den eneste som oppgir
    UTVANDRINGSVINDU per produksjonsområde. Vinduet står som DATOER
    («24. april – 5. juni, med 50 % utvandring satt til 17. mai (uke
    20)») — se `_vindu` for hvorfor uketallet ikke avledes her.
    """
    rader = _finn_tabellside(
        sider, "2020",
        ["2020", "Trål", "Ruse/garn", "Bur", "HI smitte", "HI VS", "VI VS",
         "SINTEF VS", "Hovedk."],
        "ekspertgruppen 2020")
    hoved, celler = _metodeceller(
        rader, [METODE_TRAAL, METODE_RUSE, METODE_BUR, METODE_HI_SMITTE,
                METODE_HI_VS, METODE_VI_VS, METODE_SINTEF_VS])

    kategorier, _ = _felles_prosa(flat, aar, med_usikkerhet=False)
    _kryssjekk(hoved, kategorier, "ekspertgruppen 2020")

    yield from celler
    yield from _tallceller(flat)

    for po, seksjon in sorted(_seksjoner(flat).items(), key=lambda p: int(p[0])):
        vindu = _vindu(seksjon, aar)
        if vindu:
            for felt, verdi in vindu.items():
                yield Celle(po, felt, verdi, FRA_TEKST)


def _uttrekk_2021(sider: list[str], flat: str, aar: int) -> Iterable[Celle]:
    """2021-rapporten (Vollset mfl. 2021), 109 sider. Dekker 2020 og 2021.

    Rapporten bærer TO metodetabeller: Tabell 2 for 2020 og Tabell 3 for
    2021. Den første er en OPPDATERING av 2020-rapportens egen tabell, og
    rapporten sier det selv: «Vurderingene for 2020 er oppdatert etter
    møte i september i ekspertgruppen ... Ingen hovedkonklusjoner er
    endret.»

    Det er revisjonsaksens hovedeksempel i denne kilden, og teksten over
    er fasiten uttrekket ble verifisert mot: hver enkelt endring den
    beskriver gjenfinnes i diffen mellom de to tabellene, og ingenting
    annet beveger seg.

    Kolonnene er de samme som i 2020, men overskriftene er brutt over to
    linjer («HI\\nsmittepress»), så etikettene er kortere her.
    """
    aarmerke = str(aar)
    rader = _finn_tabellside(
        sider, aarmerke,
        [aarmerke, "Trål", "Ruse/garn", "Bur", "HI", "HI virtuell",
         "VI virtuell", "SINTEF", "Hovedk."],
        f"ekspertgruppen {aar} (2021-rapporten)")
    hoved, celler = _metodeceller(
        rader, [METODE_TRAAL, METODE_RUSE, METODE_BUR, METODE_HI_SMITTE,
                METODE_HI_VS, METODE_VI_VS, METODE_SINTEF_VS])
    yield from celler

    # Avsnittene under hvert PO gjelder rapportens EGET år. For 2020 er
    # det bare tabellen som er oppdatert, og en kryssjekk mot 2021-teksten
    # ville sammenlignet to ulike år.
    if aar == 2021:
        kategorier, _ = _felles_prosa(flat, aar, med_usikkerhet=False)
        _kryssjekk(hoved, kategorier, "ekspertgruppen 2021")
        yield from _tallceller(flat)


def _uttrekk_2022(sider: list[str], flat: str, aar: int) -> Iterable[Celle]:
    """2022-rapporten (Vollset mfl. 2022), 130 sider.

    Metodeskifte: ekspertgruppen gikk over til SHELF-elisitering, og
    metodetabellen finnes ikke lenger. Tabell 3 oppgir i stedet en
    sannsynlighetsfordeling over de tre kategoriene, med en kolonne
    «Konklusjon uttrykt som i tidligere rapporter».

    Uttrekket leser den løpende teksten og ikke den tabellen, av to
    grunner: setningene «Kategori med høyest sannsynlighet: ...» og
    «vurderes å ha stor usikkerhet» er entydige per PO, mens tabellens
    sannsynlighetsord («Mer sannsynlig enn ikke») er en fjerde skala som
    ikke lar seg legge oppå de tre kategoriene uten å finne på noe.

    Sannsynlighetsfordelingen SELV er ikke trukket ut. Den er ekte
    informasjon og den er rikere enn kategorien — men den er en ny
    størrelse som bare finnes fra 2022, og å legge den inn nå ville gitt
    et felt med ett års historikk. Kroppen er arkivert; det er en
    re-parse den dagen noen vil ha den.
    """
    _, celler = _felles_prosa(flat, aar, med_usikkerhet=True)
    yield from celler
    yield from _tallceller(flat)


# ------------------------------------------------------------- utgivelser

class Utgivelse(NamedTuple):
    """Én rapport: hva den heter, hvilke år den uttaler seg om, hvor den
    ligger, og hvem som leser den."""

    # Ordrett fra kroppens forside. Dette er hvordan `parse()` VET hvilken
    # rapport den har fått — den gjetter ikke ut fra filnavn, URL eller
    # rekkefølge. Verifisert på alle fem kroppene.
    tittel: str
    # Årene rapporten uttaler seg om, ELDST FØRST.
    aar: tuple[int, ...]
    url: str
    uttrekk: Callable[[list[str], str, int], Iterable[Celle]]
    # Hvor kroppen faktisk ble hentet fra, når det ikke er `url` selv.
    # Tom streng betyr «url svarer for oss».
    merknad: str = ""


# Rapportene vi HAR LEST og skrevet et uttrekk for, ELDST UTGITT FØRST.
#
# Rekkefølgen er utgivelsesrekkefølge, og den er ikke kosmetisk:
# `backfill.py --rapporter` går gjennom dem i denne rekkefølgen, slik at
# hvert år først skrives av den eldste rapporten som dekker det og
# deretter revideres av de nyere. Går den motsatt vei, ville hver eldre
# rapport blitt en `Feilrekkefolge` mot en nyere påstand som alt lå der.
#
# 2019, 2023, 2024 og 2025 står IKKE her, og det er ikke en forglemmelse:
#
#   2019   trafikklyssystemet.no har en årstallsoverskrift med TOMT
#          innhold. Vi vet ikke om rapporten finnes. Ubesvart spørsmål,
#          ikke bekreftet fravær — se docs/KILDE-EKSPERTGRUPPEN.md.
#   2023   hovedrapporten er ikke lokalisert på noen åpen adresse. Bare
#   2024   vedleggene ligger ute. Departementet publiserte dem, og
#   2025   regjeringen.no svarer 403 på både artikkelsider og PDF-er.
#
# En kilde skal ikke emittere for et år den ikke har en lest kropp og en
# skrevet uttrekksfunksjon for. Fravær framfor gjetning.
RAPPORTER: tuple[Utgivelse, ...] = (
    Utgivelse(
        tittel=("Vurdering av lakselusindusert villfiskdødelighet per "
                "produksjonsområde i 2016 og 2017"),
        aar=(2016, 2017),
        url=("https://trafikklyssystemet.no/Portals/3/Publikasjoner/"
             "W%20Rapport%20ekspertgruppe%202017.pdf"
             "?ver=cOolnJjoR3UGHiZxVUrvbg%3d%3d"),
        uttrekk=_uttrekk_2017,
    ),
    Utgivelse(
        tittel=("Vurdering av lakselusindusert villfiskdødelighet per "
                "produksjonsområde i 2018"),
        aar=(2016, 2017, 2018),
        url=("https://trafikklyssystemet.no/Portals/3/Publikasjoner/"
             "Rapport2018_final.pdf?ver=gRVDfOyx5IgtOrSTD8-6cA%3d%3d"),
        uttrekk=_uttrekk_2018,
    ),
    Utgivelse(
        tittel=("Vurdering av lakselusindusert villfiskdødelighet per "
                "produksjonsområde i 2020"),
        aar=(2020,),
        url="https://www.hi.no/resources/rapport-2020_ekspertgruppen_final.pdf",
        uttrekk=_uttrekk_2020,
    ),
    Utgivelse(
        tittel=("Vurdering av lakselusindusert villfiskdødelighet per "
                "produksjonsområde i 2021"),
        aar=(2020, 2021),
        url=("http://web.archive.org/web/20251202085454id_/"
             "https://www.regjeringen.no/contentassets/"
             "e2ce5edb567341eb8ac15fd46714417f/ekspertgrupperapport-2021.pdf"),
        uttrekk=_uttrekk_2021,
        merknad=("regjeringen.no svarer 403 for oss, både på artikkelsiden "
                 "og på PDF-en. Kroppen hentes via Internet Archive. Det gir "
                 "TILGANG, ikke proveniens — published_at leses av "
                 "/CreationDate uansett hvilken adresse kroppen kom fra."),
    ),
    Utgivelse(
        tittel=("Produksjonsområdebasert vurdering av lakselusindusert "
                "villfiskdødelighet i 2022"),
        aar=(2022,),
        url=("http://web.archive.org/web/20260124115838id_/"
             "https://www.regjeringen.no/contentassets/"
             "b6f5e7d38fe04234b32156131a1eec14/ekspertrapport-tls-2022-1.pdf"),
        uttrekk=_uttrekk_2022,
        merknad="Som 2021: hentes via Internet Archive, se over.",
    ),
)

# Nyeste år noen kropp i `RAPPORTER` uttaler seg om. Regnes ut av tabellen
# framfor å stå som en konstant — to tall for samme sak er formen F6 og F7
# hadde, og dette ville vært et som må huskes oppdatert.
NYESTE_AAR = max(aar for r in RAPPORTER for aar in r.aar)


def gjenkjenn(flat_forside: str) -> Utgivelse:
    """Hvilken rapport denne kroppen ER, lest av forsiden.

    Ikke av filnavnet, ikke av URL-en, ikke av rekkefølgen den ble hentet
    i. Alle tre kan være feil for en kropp som er lastet ned for hånd
    eller spilt av på nytt fra arkivet — og en kropp som blir tolket som
    feil rapport ville fått riktig form og feil år.

    Titlene er verifisert ordrett på alle fem kroppene, og de skiller seg
    fra hverandre: 2022 begynner til og med med et annet ord.
    """
    normalisert = " ".join(flat_forside.split())
    for utgivelse in RAPPORTER:
        if utgivelse.tittel in normalisert:
            return utgivelse
    raise Rapportfeil(
        f"Forsiden matcher ingen kjent rapport. Første 160 tegn: "
        f"{normalisert[:160]!r}. Kjente titler: "
        + "; ".join(r.tittel for r in RAPPORTER)
        + ". Er dette en ny årgang, må den få en egen uttrekksfunksjon — "
          "se modulens docstring om hvorfor det ikke finnes en generisk."
    )


# ---------------------------------------------------------------- kilden

class Ekspertgruppen(Source):
    name = "ekspertgruppen"

    # Bumpet fra "1" 27.08.2026: `_AREALANDEL` og `_ROC` fikk slakk for
    # orddelingsmellomrom («påv irkning») og for innskutte ord mellom
    # størrelsen og verbet («... for hele produksjonsområdet er ...»).
    # Uten dem falt PO7 ut av både 2021 og 2022 — 11 % og 25 %, midt i
    # fordelingen.
    #
    # Snapshotene på disk er skrevet av versjon 1 og har 37 av 39
    # HI smittekart-celler. De skrives IKKE om: dataene er pushet, og en
    # parserendring etter det er en ny versjon ved siden av, ikke en
    # re-derivering. `diff.revisjon()` vil kaste `Grunnlagssprik` mellom
    # versjonene, som er riktig — en forskjell kan da like gjerne være
    # vår parser som kildens revisjon.
    version = "2"
    # Samme entitetstype som biomasse, med vilje: en analyse skal kunne
    # joine kategori mot beholdning på `entity_id` uten en oversettelse.
    entity_type = "produksjonsomraade"

    # Sju for en ÅRLIG kilde. Se modulens docstring — dette er ikke en
    # påstand om publiseringstakt, men om hvor ofte kjøringen skal få
    # spørre `finnes_allerede()`. Publiseringsmåneden er målt til å
    # variere mellom oktober og desember, og for de departementsleverte
    # årgangene også juni; et etterslep i dager måtte gjettet den.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.ekspertgruppen.aktiv", False))

    # ---- henting -------------------------------------------------------

    def utgivelser(self) -> tuple[Utgivelse, ...]:
        """Rapportene kilden kan lese, ELDST UTGITT FØRST.

        `backfill.py` dispatcher på at denne finnes — samme
        egenskapsbaserte utvelgelse som `hent_uke()` og `hent_alt()`, og
        av samme grunn: kilden vet hvilken form den har, og et flagg
        brukeren kan sette feil er et sted til å være uenig.
        """
        return RAPPORTER

    def hent_rapport(self, utgivelse: Utgivelse,
                     client: httpx.Client | None = None,
                     url: str | None = None) -> bytes:
        """Én rapportkropp som rå PDF-bytes.

        Returnerer BYTES og ikke uttrukket tekst, fordi kjernen arkiverer
        det `fetch()` returnerer og det som arkiveres skal være det
        tjenesten faktisk sendte. `core/raw.py` lagrer bytes som
        `.bin.gz`. En parser som forbedres senere kjører da på nytt uten
        å hente igjen — hele begrunnelsen for rå-arkivet.

        `published_at` settes HER, av kroppens `/CreationDate`, og ikke
        av noen HTTP-header. Se modulens docstring for målingen som
        avgjorde det.

        `utvalg` settes HER av samme grunn som i `biomasse.hent_alt()`:
        dette er det ene stedet begge veier inn i kilden går gjennom.
        `{}` er riktig og ikke et gjett — vi ber om hele rapporten og får
        hele rapporten. At ekspertgruppen selv bare vurderer laksesmolt i
        tretten produksjonsområder er deres avgrensning, ikke vår.
        """
        self.utvalg = {}

        egen = client is None
        c = client or httpx.Client(timeout=120.0, follow_redirects=True)
        try:
            svar = _http.get(c, url or utgivelse.url,
                             hva=f"ekspertgruppen {utgivelse.aar[-1]}")
            rå = svar.content
        finally:
            if egen:
                c.close()

        # SETT, ikke append: `advarsler` er en liste på KLASSEN, som
        # deles av alle instanser og aldri tømmes. Se Source.advarsler.
        advarsler: list[str] = []
        # Direkte kall, ikke en utpakket tuppel. Se `_utgitt`.
        self.published_at = _utgitt(rå, utgivelse.aar[-1], advarsler)
        self.advarsler = advarsler
        return rå

    def aar_i(self, rå: bytes) -> list[str]:
        """Gyldighetsdatoene en kropp bærer, eldst først.

        Kroppen svarer selv: forsiden sier hvilken rapport den er, og
        `RAPPORTER` sier hvilke år den rapporten uttaler seg om. Samme
        rolle som `biomasse.maaneder()` — kalleren skal slippe å kjenne
        PDF-formatet for å vite hvilke perioder den har fått.
        """
        utgivelse = gjenkjenn(_sider(rå, layout=False)[0])
        return [siste_dag(aar) for aar in utgivelse.aar]

    def _nyeste_uskrevne(self, kjoredato: str) -> int:
        """Nyeste vurderingsår vi har en lest kropp for.

        Kjøredatoen tas inn og brukes IKKE til å slå opp klokka — den er
        med fordi kontrakten sier at `fetch()` og `gjelder_for()` skal få
        tiden inn, og fordi en framtidig årgang skal kunne begrenses av
        den uten at signaturen endres. I dag er svaret konstant:
        `RAPPORTER` er en skrevet liste, ikke noe vi utleder av dagens
        dato.
        """
        return NYESTE_AAR

    def gjelder_for(self, kjoredato: str) -> str:
        """Siste dag i nyeste vurderingsår vi kan lese — ikke kjøreåret.

        For denne kilden spriker de to med fire år i dag (2022 mot 2026),
        og det er riktig: `observed_at` handler om verden, kjøredatoen om
        oss. Så lenge 2022 ligger skrevet, hopper steg 2b i `run.py` over
        kilden uten å hente.
        """
        return siste_dag(self._nyeste_uskrevne(kjoredato))

    def fetch(self, kjoredato: str) -> bytes:
        """Nyeste rapportkropp vi har et uttrekk for.

        Den løpende jobben henter ÉN rapport — den nyeste — og skriver
        ett år av den. Historikken og de eldre kroppene går gjennom
        `backfill.py --rapporter`, som er det ene stedet
        utgivelsesrekkefølgen håndheves.
        """
        aar = self._nyeste_uskrevne(kjoredato)
        for utgivelse in reversed(RAPPORTER):
            if aar in utgivelse.aar:
                return self.hent_rapport(utgivelse)
        raise Rapportfeil(
            f"Ingen rapport i RAPPORTER dekker {aar}. Tabellen og "
            f"NYESTE_AAR er ute av takt."
        )

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: bytes, observed_at: str) -> Iterable[Observation]:
        """Ett vurderingsår ut av en kropp som kan bære flere.

        `observed_at` VELGER året, kroppen BEKREFTER det. Samme rekkefølge
        og samme begrunnelse som `biomasse.parse()`: én kropp bærer flere
        perioder, så det finnes ikke noe i dataene å utlede datoen fra, og
        det eneste forsvaret mot at kjernen og kroppen er uenige er å
        sjekke at året faktisk er der.

        Kaster `Aarmangler` hvis det ikke er det. Alternativet — å skrive
        et tomt snapshot — ville sett vellykket ut, låst året mot senere
        skriving via `finnes_allerede()`, og gjort hullet permanent.
        """
        aar = aar_av(observed_at)

        flate = _sider(raw, layout=False)
        utgivelse = gjenkjenn(flate[0])
        if aar not in utgivelse.aar:
            raise Aarmangler(
                f"«{utgivelse.tittel}» uttaler seg om "
                f"{', '.join(str(a) for a in utgivelse.aar)}, ikke om {aar}. "
                f"Ingenting skrives — et tomt snapshot ville låst året."
            )

        layout = _sider(raw, layout=True)
        flat = _flat(flate)
        navn = _po_navn(flate)

        celler = list(utgivelse.uttrekk(layout, flat, aar))
        if not celler:
            raise Rapportfeil(
                f"Uttrekket for {aar} fant ingenting i «{utgivelse.tittel}». "
                f"Formatet er endret — kroppen er arkivert, så dette er en "
                f"re-parse og ikke tapt historikk."
            )

        sett: set[tuple[str, str]] = set()
        for celle in celler:
            if (celle.po, celle.felt) in sett:
                raise Rapportfeil(
                    f"Uttrekket ga to verdier for PO{celle.po} "
                    f"{celle.felt!r} i {aar}. `snapshot.NOKKEL` ville "
                    f"beholdt den første stilltiende."
                )
            sett.add((celle.po, celle.felt))

            felles = dict(entity_id=celle.po, entity_type=self.entity_type,
                          entity_name=navn.get(celle.po, ""),
                          source=self.name, observed_at=observed_at)
            yield Observation(field=celle.felt, value=celle.verdi, **felles)
            # Lesemåten lagres SAMMEN med verdien, ikke ved siden av den.
            # Se CLAUDE.md 1b-3 og modulens docstring om feltvakten.
            yield Observation(field=celle.felt + SIKKERHET_SUFFIKS,
                              value=celle.sikkerhet, **felles)
