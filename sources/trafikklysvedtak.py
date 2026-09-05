"""Departementets FARGE per produksjonsområde per tildelingsrunde, lest av
kapasitetsjusteringsforskriftene på lovdata.no.

Verifisert mot fire nedlastede forskriftskropper 05.09.2026, se
docs/KILDE-TRAFIKKLYSVEDTAK.md. Alt i denne docstringen er MÅLT på de
arkiverte kroppene, ikke lest ut av en oppsummering.

`sources/ekspertgruppen.py` har den ene siden av trafikklyssystemet:
RÅDET, altså hvilken risikokategori ekspertgruppen setter på hvert
produksjonsområde. Denne kilden har den andre: VEDTAKET, altså hvilken
farge Nærings- og fiskeridepartementet faktisk ga området da runden ble
avgjort.

De to er ikke samme skala, og de er ikke koblet av noe regelverk. Det er
kildens viktigste funn, og det står i sin helhet under «Koblingen
mellom råd og vedtak er ikke definert».

## Fire runder, ikke fem

Trafikklyset er fargelagt i tildelingsrundene 2018, 2020, 2022, 2024 og
2026. Bare de FIRE første har en fastsatt forskrift.

Målt 05.09.2026 mot Lovdatas register over Norsk Lovtidend avdeling I
(`/register/lovtidend?avdeling=LTI&year=YYYY&search=…`), som søker i
tittelfeltet:

    runde   forskrift                 kunngjort
    2018    FOR-2017-12-20-2397       03.01.2018
    2020    FOR-2020-02-04-105        05.02.2020
    2022    FOR-2022-06-07-972        07.06.2022
    2024    FOR-2024-03-22-515        26.03.2024
    2026    finnes ikke

Søk på «matfisk», «kapasitet», «akvakultur», «produksjonsomr»,
«regnbue» og «tillatelser» for 2026 gir ingen kapasitetsjusterings-
forskrift. Departementet sendte utkastet på høring 19.06.2026 med frist
31.07.2026; fargeleggingen for 2026 er kunngjort i en pressemelding, men
VEDTAKET i forskrifts form fantes ikke da kilden ble skrevet.

Derfor står 2026 ikke i `FORSKRIFTER`. En kilde skal ikke emittere for
en runde den ikke har en lest kropp for — fravær framfor gjetning, samme
regel som ekspertgruppens manglende årganger.

## Kildens form: N KROPPER som hver dekker M RUNDER

Samme form som ekspertgruppen, og av samme grunn: forskriftene uttaler
seg om hverandres runder. § 4-tabellen i 2024-forskriften skriver
«Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022, rødt lys i
2024)» — én rad, tre påstander, om tre ulike runder.

    kropp   uttaler seg om
    2018    2018
    2020    2020
    2022    2020, 2022
    2024    2020, 2022, 2024

To forskrifter som er uenige om 2020 ville ikke vært en feil, men to
påstander om samme tidspunkt gjort på hver sin dato. De er MÅLT enige:
2022- og 2024-kroppen sier begge PO3 gult, PO4 rødt og PO5 rødt i 2020.
Se CLAUDE.md 1b-5 og `diff.revisjon()`.

## KJENT AVVIK: revisjonsaksens entitetssemantikk passer ikke her

`diff.revisjon_mellom()` sier det uttrykkelig: skjemafilteret går på
FELTNAVN og ikke på entiteter, fordi «en entitet som dukker opp eller
forsvinner mellom to versjoner av samme måned ER en revisjon». Det er
riktig for biomasse, der en lokalitet faktisk flyttes inn i eller ut av
en måned.

Det er FEIL for denne kilden. 2022-forskriften uttaler seg bare om PO3,
PO4 og PO5 for runde 2020. At den ikke gjentar PO1, betyr ikke at
departementet trakk tilbake det grønne lyset — det betyr at
§ 4-tabellen bare har tre rader.

Målt på backfillen 05.09.2026, 38 revisjonsrader i alt:

    34   new_value er null — området er BARE IKKE GJENTATT
     2   old_value er null — PO3 2020, som 2020-kroppen ikke bærer
     2   ekte verdiendring — PO4 og PO5 2020, der lesemåten går fra
         `kapitteloverskrift` til `ordrett`
     0   motstrid om FARGE mellom to kropper

De 34 er en usann påstand i changeloggen. De er ikke datatap:
changeloggen er avledet og kan regnes ut på nytt fra snapshotene (regel
2), begge snapshots står, og `diff.bevegelse()` filtrerer `revidert`
bort fra ukas endringstall uansett.

Rettelsen hører hjemme i `core/diff.py` — et valg mellom entitets- og
feltsemantikk som kilden ikke kan ta selv — og CLAUDE.md regel 1 sier
at en kilde IKKE skal be om en endring i `core/` på egen hånd. Derfor
står avviket her, målt, og ikke omgått.

**Leseregelen som gjelder inntil videre:** gjeldende farge for (runde,
PO) er den SIST UTGITTE raden SOM FINNES for den cellen — ikke det siste
snapshotet. Det er nøyaktig regelen
`analyse/ekspertgruppen_celler.les()` følger for felter, anvendt på
entiteter, og den er implementert i `analyse/vedtak_mot_rad.les_vedtak()`.

## `published_at` er IKRAFTTREDELSEN, og HTTP har ingen dato å tilby

Biomasse tar `published_at` fra `Last-Modified`. Det er ikke et valg
her: målt 05.09.2026 sender lovdata.no **ingen `Last-Modified`-header i
det hele tatt** på disse fire dokumentene — bare `date:` (nå) og
`cache-control: max-age=7200`. Headeren finnes ikke å ta feil av.

Det som finnes er dokumentets eget metadatafelt:

    FOR-2017-12-20-2397   Ikrafttredelse 20.12.2017
    FOR-2020-02-04-105    Ikrafttredelse 04.02.2020
    FOR-2022-06-07-972    Ikrafttredelse 07.06.2022
    FOR-2024-03-22-515    Ikrafttredelse 22.03.2024

Ikrafttredelsen er valgt framfor kunngjøringsdatoen fordi den er det
tidspunktet vedtaket VIRKER fra. For alle fire faller den sammen med
fastsettelsesdatoen i FOR-nummeret; kunngjøringen ligger 0–14 dager
etter. `_utgitt()` KREVER at de to faller sammen og setter
`published_at` tom med en advarsel hvis de ikke gjør det — en
ikrafttredelse som ligger langt fra fastsettelsen ville betydd en
utsatt eller tilbakevirkende virkning, og da er «da kilden utga dette»
et annet spørsmål enn feltet svarer på.

Den er LEST av dokumentet, ikke utledet av FOR-nummeret. Se CLAUDE.md
1b-7 punkt 2.

## LTI-versjonen, ikke SF-versjonen

Lovdata har hvert dokument i to former: `LTI` er teksten slik den ble
kunngjort, `SF` er den konsoliderte som oppdateres når forskriften
endres. 2022-forskriften er endret tre ganger (FOR-2022-06-16-1058,
-09-28-1671, -10-06-1721).

Kilden leser LTI. Et VEDTAK er en handling på et tidspunkt, og
`published_at` skal peke på det tidspunktet. En konsolidert tekst er en
påstand om hva som gjelder NÅ, og den ville gjort hver kropp til en
bevegelig referanse — CLAUDE.md 1b-4 sier at en referanse ikke skal
flytte seg selv.

## Én uttrekksfunksjon per forskriftsår

Den viktigste designbeslutningen, og den er tatt fordi kroppene MÅLT er
forskjellige dokumenter — ikke fordi det er pent:

    kropp   fargeord i teksten   § 3-form                    § 4-tabell
    2018    INGEN                «Kapittel 2 om økt …»       nei
    2020    «røde» (kap.hode)    tre kapittelledd            nei
    2022    «(grønne)», «lys i»  to kapittelledd             ja, 2 år/rad
    2024    «(grønne)», «lys i»  to kapittelledd             ja, 3 år/rad

2018-kroppen inneholder ikke ett eneste fargeord. 2020-kroppen har
«røde» bare i overskriften til kapittel 4. En generisk parser over den
spredningen ville gitt riktig FORM og feil TALL — prosjektets egen
feilklasse (CLAUDE.md 1b-2), og nøyaktig den som felte ROC-uttrekket
fire ganger. Derfor er `FORSKRIFTER` en tabell av kropper med hver sin
uttrekksfunksjon, og `parse()` NEKTER å emittere for en runde ingen
funksjon dekker.

## TRE lesemåter, lagret SAMMEN med fargen

Hver farge får et søsterfelt `farge__lesemaate` med hvor sterkt kilden
faktisk sier den. De er ordinale, sterkest først:

    ordrett              fargeordet står i samme setning eller
                         tabellrad som områdenummeret
                         («(grønne) produksjonsområder: … Område 1: …»,
                          «Produksjonsområde 3 (gult lys i 2020, …)»)

    kapitteloverskrift   § 3 plasserer området i et kapittel, og
                         KAPITTELETS EGEN OVERSKRIFT bærer fargeordet
                         («Kapittel 4. Nedjustering av tillatelses-
                          kapasitet i røde produksjonsområder»)

    kapittelhjemmel      § 3 plasserer området i kapittelet som
                         gjennomfører produksjonsområdeforskriften § 11
                         «Tilbud om kapasitetsøkning (akseptabel
                         miljøpåvirkning)», og ingen fargeord finnes.
                         Grønn er da UTLEDET av hjemmelen, ikke lest.

Skillet er ikke pynt. `kapittelhjemmel` er det eneste leddet der vi selv
tar et steg kilden ikke tar, og en analyse skal kunne se hvilke celler
det gjelder. Regel 1b-3: verdien som avgjør hva dataene BETYR lagres
sammen med dem.

**Og utledningen er etterprøvd.** Den samme strukturelle plassen —
kapittelet som gir tilbud om økt kapasitet etter § 11 — er merket
«(grønne)» ORDRETT i både 2022- og 2024-kroppen. For rødt gjelder det
motsatt vei: 2020-kroppens `kapitteloverskrift`-lesning av PO4 og PO5
bekreftes ordrett av «rødt lys i 2020» i både 2022- og 2024-kroppen. To
av to røde og to av to tilgjengelige kontroller stemmer.

## Hva som IKKE emitteres, med vilje

**Farge ved utelukkelse.** I 2022-kroppen står PO2 og PO7 verken i
den grønne lista eller i § 4-tabellen; i 2024-kroppen gjelder det PO2,
PO6, PO7 og PO8. Systemet har tre farger, så «verken grønn eller rød»
peker mot gul — og «Tillatelser hjemmehørende i øvrige
produksjonsområder kan utnyttes 100 prosent» er forenlig med det.

Det emitteres likevel ikke. Slutningen krever at forskriften er
UTTØMMENDE om farge, og 2018-kroppen beviser at den ikke trenger å
være det: der er fem områder unevnt, og minst ett av dem var rødt.
En regel som er riktig i akkurat de kroppene der den lar seg sjekke, og
stille feil i den ene der den ikke gjør det, er mønsteret fra 1b-2.

**Kapasitetstallene i § 4-tabellen.** «Ned 6 pst.», «94 pst.»,
«88,36 pst.» er stated og lesbare, men de er en annen størrelse enn
fargen og hører til et annet spørsmål. Kroppen er arkivert; det er en
re-parse den dagen noen vil ha dem.

## Koblingen mellom råd og vedtak er ikke definert

Dette er funnet kilden ble bygget for å svare på, og svaret er negativt.

`analyse/fasit/…` og `sources/ekspertgruppen.py` gir RISIKONIVÅ for
lakselusindusert villfiskdødelighet: lav (< 10 %), moderat (10–30 %),
høy (> 30 %). Forskriften gir FARGE. Spørsmålet var om
produksjonsområdeforskriften definerer oversettelsen.

Målt på både den opprinnelig kunngjorte og den gjeldende teksten av
FOR-2017-01-16-61 (05.09.2026): ordene «dødelighet», «grønn», «rød»,
«trafikklys», «risiko» og «ekspertgruppe» forekommer **null ganger**,
og det finnes ingen prosentterskler.

Det forskriften har er § 8 annet ledd: «Departementet vurderer om
miljøpåvirkningen i et produksjonsområde er akseptabel, moderat eller
uakseptabel», med §§ 9, 10 og 11 som knytter konsekvens til hver av de
tre. Farge-til-miljøstatus står bare UTENFOR forskriften, og der er den
entydig — departementets eget høringsnotat 19.06.2026: «Er
miljøpåvirkningen akseptabel (grønn) kan næringen tilbys vekst. Er
miljøpåvirkningen moderat (gul) kan kapasiteten bli stående uendret, og
er miljøpåvirkningen uakseptabel (rød) kan kapasiteten senkes.»

Leddet som mangler er risikonivå-til-miljøstatus. Det nærmeste som
finnes er trafikklysmeldingen (Meld. St. 16 (2014–2015)) kap. 8.3,
sitert av departementet i samme høringsnotat: «Dersom resultatet er
sammenfallende begge årene vil utfallet være forutsigbart og det legges
ikke opp til noen vurdering, men dersom overvåkingen viser en endring i
påvirkning de to årene vil myndighetene måtte gjøre grundigere
vurderinger ut ifra den samlede miljøtilstanden.»

Tre grunner til at det ikke er en definisjon:

1. En stortingsmelding er ikke et regelverk, og setningen sier
   «forutsigbart», ikke hvilken farge som følger av hvilken kategori.
2. Vedtaket hviler på TO vurderingsår, ikke ett. Runde 2026 bygger på
   ekspertgruppens rapporter for 2024 og 2025 (høringsnotatet
   19.06.2026); runde 2024 på 2022 og 2023. En celle (PO, runde) har
   altså to råd, ikke ett.
3. Departementet forbeholder seg uttrykkelig en helhetsvurdering:
   «I en helhetsvurdering kan det også ses hen til samfunnsøkonomiske
   konsekvenser av ulike valg. Styringsgruppen foretar ingen slik
   helhetsvurdering når den gir råd til departementet, den gir kun et
   faglig råd om miljøtilstanden.»

Konsekvensen for analysen står i `analyse/vedtak_mot_rad.py` og
`analyse/FORBEHOLD-vedtak-mot-rad.md`: sammenstillingen teller dekning
og viser samforekomst, men beregner INGEN treffrate og INGEN
avviksretning, fordi det ikke finnes en skala å måle avvik mot.

## `min_dager_mellom = 7` for en toårig kilde

Samme resonnement som ekspertgruppen: sju betyr ikke «det kommer en
forskrift hver uke», det betyr «tilby kilden til kjøringen hver uke og
la `finnes_allerede()` avgjøre». Fastsettelsesmåneden er MÅLT til å
variere mellom desember, februar, mars og juni; et etterslep i dager
måtte gjettet hvilken.
"""

from __future__ import annotations

import datetime as dt
import html
import re
from typing import Callable, Iterable, NamedTuple

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http


# ------------------------------------------------------------- konstanter

ANTALL_PO = 13

# Fargene, normalisert til ASCII slik ekspertgruppen normaliserer «høy»
# til `hoy`. Verdiene er det analysene slår opp på, og en æøå i en
# nøkkelverdi har en tendens til å bli to ulike strenger.
GRONN, GUL, ROD = "gronn", "gul", "rod"

# Ordformene vi har SETT i de fire kroppene. Lista er lukket med vilje:
# en form vi ikke kjenner skal felle uttrekket, ikke gjettes inn i en av
# de tre. Kildene skriver intetkjønn («rødt lys») i tabellen og flertall
# («røde produksjonsområder», «(grønne)») i overskrifter og ledd.
FARGEORD = {
    "grønt": GRONN, "grønne": GRONN, "grønn": GRONN,
    "gult": GUL, "gule": GUL, "gul": GUL,
    "rødt": ROD, "røde": ROD, "rød": ROD,
}

# Feltnavn. Rekkefølgen her er rekkefølgen observasjonene kommer ut i, og
# den er stabil mellom kjøringer med vilje: en parquet-fil skal ikke få
# nytt innhold i git bare fordi en dict ble iterert annerledes.
F_FARGE = "farge"

# Lesemåten, lagret SAMMEN med verdien. Se modulens docstring.
LESEMAATE_SUFFIKS = "__lesemaate"
ORDRETT = "ordrett"
KAPITTELOVERSKRIFT = "kapitteloverskrift"
KAPITTELHJEMMEL = "kapittelhjemmel"


class Forskriftsfeil(RuntimeError):
    """Kroppen kom, men ikke i den formen uttrekket kjenner.

    Kroppen er arkivert, så det er en re-parse og ikke tapt historikk.
    """


class Rundemangler(RuntimeError):
    """Kroppen uttaler seg ikke om tildelingsrunden vi ba om.

    Egen klasse fordi den betyr noe annet enn `Forskriftsfeil`: formen er
    i orden, det er koblingen mellom `FORSKRIFTER` og `observed_at` som
    ikke stemmer.
    """


# ------------------------------------------------------------- kalender

def siste_dag(runde: int) -> str:
    """ISO-datoen et snapshot for denne tildelingsrunden BÆRER.

    Årets siste dag, nøyaktig som `ekspertgruppen.siste_dag()`. Det er
    ikke tilfeldig at de er like: en analyse skal kunne joine råd mot
    vedtak på (entity_id, observed_at) uten en oversettelse i midten.

    Merk at datoen er en ETIKETT på runden, ikke tidspunktet vedtaket ble
    fattet. Det siste er `published_at`, og for runde 2018 ligger det i
    desember 2017 — før `observed_at`. Det er riktig: `observed_at`
    handler om hvilken runde raden gjelder, `published_at` om når
    departementet avgjorde den.
    """
    return f"{runde}-12-31"


def runde_av(observed_at: str) -> int:
    """Tildelingsrunden for en gyldighetsdato. Kaster på alt annet enn
    årets siste dag.

    Samme kontroll og samme begrunnelse som `ekspertgruppen.aar_av()`:
    ett snapshot er ett tidspunkt, og filnavnet er det eneste alt
    nedstrøms leser datoen fra (F6).
    """
    d = dt.date.fromisoformat(observed_at)
    if (d.month, d.day) != (12, 31):
        raise ValueError(
            f"observed_at {observed_at} er ikke årets siste dag. En "
            f"tildelingsrunde etiketteres med årets siste dag, og et "
            f"snapshot som bærer en annen dato lyver om hvilken runde det "
            f"gjelder. Mente du {siste_dag(d.year)}?"
        )
    return d.year


# ---------------------------------------------------------- HTML-lesing

def _tekst(rå: bytes) -> str:
    """Lovdata-siden som én flat tekstlinje.

    Taggene erstattes med MELLOMROM og ikke med tom streng. Det er ikke
    kosmetikk: § 4-tabellen er et `<table>`, og uten mellomrommet limes
    «Produksjonsområde 3 (…)» sammen med «Ned 6 pst.» fra nabocellen.
    """
    t = rå.decode("utf-8", "replace")
    t = re.sub(r"(?s)<script.*?</script>", " ", t)
    t = re.sub(r"(?s)<style.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


_HJEMMEL_START = "Hjemmel: Fastsatt av"


def _forskriftstekst(flat: str) -> str:
    """Selve forskriften, uten Lovdatas meny og innholdsfortegnelse.

    Kuttet er ikke sparsommelighet. Lovdatas sider gjentar hver
    paragrafoverskrift i en innholdsfortegnelse FØR brødteksten, og et
    `§ 3.…(?=§ 4.)`-snitt over hele siden ville truffet de to
    innholdslinjene og gitt en tom seksjon — riktig form, ingen data.
    Samme feilklasse som 1b-2, og den fanges ikke av noen vakt fordi
    resultatet ser ut som en forskrift uten områdeliste.
    """
    i = flat.find(_HJEMMEL_START)
    if i < 0:
        raise Forskriftsfeil(
            f"Fant ikke «{_HJEMMEL_START}» i kroppen. Uten den kan ikke "
            f"brødteksten skilles fra Lovdatas innholdsfortegnelse, og et "
            f"uttrekk over hele siden leser overskriftene i stedet for "
            f"paragrafene. Kroppen er arkivert — dette er en re-parse."
        )
    return flat[i:]


_FOR_ID = re.compile(r"Dato\s+(FOR-(\d{4})-(\d{2})-(\d{2})-\d+)")
_IKRAFT = re.compile(r"Ikrafttredelse\s+(\d{2})\.(\d{2})\.(\d{4})")


def _forskrift_id(flat: str) -> str:
    """FOR-nummeret, lest av dokumentets metadatablokk.

    Leses av HELE siden og ikke av `_forskriftstekst()`: metadatablokken
    står FØR «Hjemmel: Fastsatt av».
    """
    m = _FOR_ID.search(flat)
    if not m:
        raise Forskriftsfeil(
            "Fant ingen «Dato FOR-…» i kroppen. Uten den vet vi ikke "
            "hvilken forskrift dette er, og et uttrekk mot feil tabellrad "
            "ville gitt riktig form og feil runde."
        )
    return m.group(1)


def _si_fra(advarsler: list[str] | None, grunn: str) -> str:
    """Legg til en advarsel og returner tom streng.

    Samme form som `ekspertgruppen._si_fra()`: en utgivelsesdato vi ikke
    stoler på skal bli TOM, ikke gjettet. Tom streng leses «vet ikke».
    """
    if advarsler is not None:
        advarsler.append(grunn)
    return ""


def _utgitt(flat: str, advarsler: list[str] | None = None) -> str:
    """`published_at` for en forskriftskropp: IKRAFTTREDELSEN.

    Lovdata sender ingen `Last-Modified` for disse dokumentene — målt
    05.09.2026 på alle fire — så det finnes ikke noe HTTP-alternativ å
    velge feil. Det som finnes er dokumentets eget metadatafelt.

    ## Vakten

    Ikrafttredelsen KREVES å falle sammen med fastsettelsesdatoen i
    FOR-nummeret. For alle fire kroppene gjør den det:

        FOR-2017-12-20-2397   Ikrafttredelse 20.12.2017
        FOR-2020-02-04-105    Ikrafttredelse 04.02.2020
        FOR-2022-06-07-972    Ikrafttredelse 07.06.2022
        FOR-2024-03-22-515    Ikrafttredelse 22.03.2024

    Skiller de seg, er vedtaket enten utsatt eller gitt tilbakevirkende
    kraft, og da er «da kilden utga dette svaret» et annet spørsmål enn
    ikrafttredelsen svarer på. Feltet settes tomt med en advarsel framfor
    å bære en dato ingen har gått god for — samme valg som
    `ekspertgruppen._utgitt()` gjør for en re-eksportert PDF. Vakten
    finnes for den femte kroppen, ikke for de fire.
    """
    m_id = _FOR_ID.search(flat)
    m_kraft = _IKRAFT.search(flat)
    if not m_id:
        return _si_fra(advarsler, "Kroppen har ingen «Dato FOR-…».")
    if not m_kraft:
        return _si_fra(
            advarsler,
            f"{m_id.group(1)} har intet «Ikrafttredelse»-felt. "
            f"published_at settes tom.")

    fastsatt = dt.date(int(m_id.group(2)), int(m_id.group(3)),
                       int(m_id.group(4)))
    kraft = dt.date(int(m_kraft.group(3)), int(m_kraft.group(2)),
                    int(m_kraft.group(1)))
    if kraft != fastsatt:
        return _si_fra(
            advarsler,
            f"{m_id.group(1)}: ikrafttredelse {kraft.isoformat()} er ikke "
            f"fastsettelsesdatoen {fastsatt.isoformat()}. Vedtaket er "
            f"utsatt eller gitt tilbakevirkende kraft, og da svarer "
            f"ikrafttredelsen på et annet spørsmål enn published_at "
            f"stiller. Feltet settes tomt.")
    # Midt på dagen UTC. Datoen er det Lovdata oppgir; et klokkeslett vi
    # ikke har ville vært oppdiktet presisjon uansett hvilket vi valgte,
    # og 12:00 er det som ikke flytter datoen i noen tidssone.
    return dt.datetime(kraft.year, kraft.month, kraft.day, 12, 0,
                       tzinfo=dt.timezone.utc).isoformat()


# ------------------------------------------------------- paragrafer og ledd

def _paragraf(kropp: str, nr: str, neste: str) -> str:
    """Teksten i én paragraf, fra overskriften til neste paragraf.

    Kaster hvis paragrafen ikke finnes. Et tomt uttrekk ville sett
    vellykket ut og gitt null farger uten å si fra.
    """
    m = re.search(rf"§\s*{nr}\s*\..*?(?=§\s*{neste}\s*\.)", kropp, re.S)
    if not m:
        raise Forskriftsfeil(
            f"Fant ikke § {nr} (avgrenset av § {neste}) i kroppen. "
            f"Paragrafnummereringen er endret — kroppen er arkivert, så "
            f"dette er en re-parse. Årgangen skal ha sitt eget uttrekk "
            f"framfor at et eksisterende mykes opp."
        )
    return m.group(0)


# «Kapittel 2 …», «Kapittel 3 …», «Kapitlene 1, 2, 4 og 5 …». Delingen av
# § 3 i ledd, ett per kapittelhenvisning. Formen varierer mellom
# kroppene — 2018 skyter inn «om økt kapasitet på eksisterende
# tillatelser» mellom nummeret og «gjelder» — så leddet klippes på
# HENVISNINGEN og ikke på et verb.
_KAPITTELLEDD = re.compile(
    r"Kapit(?:tel|lene)\s+(\d{1,2}(?:\s*,\s*\d{1,2})*(?:\s+og\s+\d{1,2})?)"
    r"(.*?)(?=Kapit(?:tel|lene)\s+\d|$)", re.S)


def _ledd(seksjon: str) -> list[tuple[str, str]]:
    """§ 3 delt i (kapittelhenvisning, tekst).

    Henvisningen beholdes ORDRETT («1, 2, 4 og 5»), fordi den er kildens
    egen og fordi hvert uttrekk selv skal si hvilket kapittel det leter
    etter.
    """
    return [(" ".join(m.group(1).split()), m.group(2))
            for m in _KAPITTELLEDD.finditer(seksjon)]


def _ledd_for(seksjon: str, kapittel: int) -> str:
    """Leddet som handler om NØYAKTIG dette ene kapittelet.

    En henvisning til flere kapitler («Kapitlene 1, 2, 4 og 5 gjelder
    tillatelser hjemmehørende i alle produksjonsområder») sier ingenting
    om farge, og skal ikke kunne forveksles med det enkeltleddet som
    lister områder.
    """
    for henvisning, tekst in _ledd(seksjon):
        if henvisning == str(kapittel):
            return tekst
    raise Forskriftsfeil(
        f"§ 3 har intet ledd som gjelder kapittel {kapittel} alene. "
        f"Ledd funnet: {[h for h, _ in _ledd(seksjon)]}. Strukturen er "
        f"endret — kroppen er arkivert, dette er en re-parse."
    )


# «a. Område 1: Svenskegrensen til Jæren», «a) Område 1: …». Navnet
# stoppes av neste punktmarkør, av et punktum, av neste kapittelhenvisning
# eller av Lovdatas delelenke — 2018-kroppen har INGEN punktum etter det
# siste områdenavnet, så «Øst-Finnmark Kapittel 3 gjelder i alle …» ville
# blitt navnet uten stoppet på «Kapit».
_OMRAADE = re.compile(
    r"Område\s+(\d{1,2})\s*:\s*(.{2,60}?)\s*"
    r"(?=[a-z][.)]\s+Område|\.\s|\s+Kapit|\s*🔗|$)")

# Vakten. Nevner leddet et områdenummer, SKAL en farge komme ut av det.
#
# Den trenger ikke vite hvor mange områder som forventes, og det er med
# vilje — samme grunn som `ekspertgruppen._ROC_KANDIDAT`: antallet
# varierer legitimt mellom rundene (åtte grønne i 2022, seks i 2024), og
# en terskel på tretten ville fyrt hver eneste kropp. Spørsmålet vakten
# stiller har et svar for HVERT ENKELT område: nevnte forskriften det, og
# leste vi det?
#
# Ankeret er «Område N:» med kolon, ikke ordet «produksjonsområde». Det
# siste står 20–40 ganger i hver kropp, om virkeområde, om flytting og om
# vederlag, og en vakt på det ordet ville fyrt på hver eneste paragraf.
_OMRAADE_KANDIDAT = re.compile(r"Område\s+(\d{1,2})\s*:")


def _omraader(ledd: str) -> list[tuple[str, str]]:
    """[(po, navn)] fra en områdeliste i § 3."""
    ut = []
    for m in _OMRAADE.finditer(ledd):
        po = str(int(m.group(1)))
        if not 1 <= int(po) <= ANTALL_PO:
            raise Forskriftsfeil(
                f"§ 3 lister «Område {m.group(1)}», som ikke er ett av de "
                f"{ANTALL_PO} produksjonsområdene. Et fjortende område "
                f"ville lagt seg ved siden av de tretten og talt med i "
                f"nevneren uten at noen så det."
            )
        ut.append((po, " ".join(m.group(2).split())))
    return ut


# ---------------------------------------------------------- § 4-tabellen

# «a. Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022) Ned 6 pst. …»
#
# STOR forbokstav, og det er målt: § 4 i 2024-kroppen omtaler også
# «Tillatelser i produksjonsområde 3 og 4 …» og «… i produksjonsområde 5
# …» i løpende tekst med LITEN p. Med stor P treffer mønsteret nøyaktig
# de tre tabellradene i begge kroppene og ingenting annet.
_TABELLRAD = re.compile(r"Produksjonsområde\s+(\d{1,2})\s*\(([^)]*)\)")

# Vakten for tabellen: en rad UTEN parentes ville ikke matchet mønsteret
# over i det hele tatt, og raden ville forsvunnet stille.
_TABELLRAD_KANDIDAT = re.compile(r"Produksjonsområde\s+(\d{1,2})\b")

# «gult lys i 2020», «rødt lys i 2022»
_LYS = re.compile(r"(grønt|gult|rødt)\s+lys\s+i\s+(\d{4})")


class Celle(NamedTuple):
    """Én farge for ett produksjonsområde i én tildelingsrunde."""

    runde: int
    po: str
    navn: str
    farge: str
    lesemaate: str


def _tabellceller(seksjon4: str) -> list[Celle]:
    """Alle «X lys i ÅÅÅÅ» i § 4-tabellen, som celler.

    Radene bærer flere runder hver, og det er hele grunnen til at
    forskriftene overlapper: 2024-kroppen restaterer 2020 og 2022 her.
    """
    ut: list[Celle] = []
    for m in _TABELLRAD.finditer(seksjon4):
        po = str(int(m.group(1)))
        for ord_, aar in _LYS.findall(m.group(2)):
            ut.append(Celle(int(aar), po, "", FARGEORD[ord_], ORDRETT))
    return ut


# ------------------------------------------------------------- vaktene

def _krev_alle_omraader(ledd: str, celler: list[Celle], hvor: str) -> None:
    """Nevner leddet et område, skal en farge ha kommet ut.

    Prosauttrekk fra offentlige dokumenter har feilet STILLE i dette
    repoet før, hver gang med riktig form og feil tall. En områdelinje
    som er der og ikke blir lest, gir et hull som ser ut som en ekte
    utelatelse fra forskriften — og for denne kilden er hull nettopp det
    interessante funnet, så et falskt hull er verre enn ellers.
    """
    nevnt = {str(int(m.group(1))) for m in _OMRAADE_KANDIDAT.finditer(ledd)}
    fikk = {c.po for c in celler}
    mangler = sorted(nevnt - fikk, key=int)
    if not mangler:
        return
    raise Forskriftsfeil(
        f"{hvor} nevner produksjonsområde "
        f"{', '.join(mangler)} uten at uttrekket fikk en farge ut. "
        f"Ordrett: …{' '.join(ledd.split())[:400]}… "
        f"Kroppen er arkivert — dette er en re-parse, ikke tapt "
        f"historikk. Er formen endret, skal årgangen ha sitt eget "
        f"mønster framfor at et eksisterende mykes opp."
    )


def _krev_alle_tabellrader(seksjon4: str, celler: list[Celle]) -> None:
    """Hver «Produksjonsområde N» i § 4 skal ha gitt minst én farge, og
    hver «X lys i ÅÅÅÅ» sin egen celle.

    To ledd, fordi de svikter på hver sin måte: en rad uten parentes
    forsvinner helt, og en parentes med tre årstall der uttrekket leser to
    mister den eldste runden uten å endre antall rader.
    """
    fikk_po = {c.po for c in celler}
    for m in _TABELLRAD_KANDIDAT.finditer(seksjon4):
        po = str(int(m.group(1)))
        if po not in fikk_po:
            raise Forskriftsfeil(
                f"§ 4-tabellen har en rad for produksjonsområde {po} uten "
                f"at uttrekket fikk en farge ut. Ordrett: "
                f"…{' '.join(seksjon4[m.start():m.start() + 220].split())}… "
                f"Kroppen er arkivert — dette er en re-parse."
            )

    fikk = {(c.runde, c.po) for c in celler}
    for m in _TABELLRAD.finditer(seksjon4):
        po = str(int(m.group(1)))
        paren = m.group(2)
        lys = _LYS.findall(paren)
        if not lys:
            raise Forskriftsfeil(
                f"Parentesen etter «Produksjonsområde {po}» inneholder "
                f"ingen «farge lys i ÅÅÅÅ»: {paren!r}. Formen er ny, og "
                f"mønsteret skal utvides mot kroppen — ikke mykes opp på "
                f"gjetning."
            )
        for _, aar in lys:
            if (int(aar), po) not in fikk:
                raise Forskriftsfeil(
                    f"«{paren}» nevner {aar} for produksjonsområde {po}, "
                    f"men ingen celle kom ut for den runden."
                )


def _krev_ordlyd(tekst: str, ordlyd: str, hva: str) -> None:
    """Kroppen skal si det vi påstår at den sier.

    Brukes av uttrekkene til å binde en PÅSTAND OM LESEMÅTE til teksten:
    sier uttrekket at grønn står `ordrett`, må «(grønne)» faktisk stå der.
    Uten dette ville lesemåtefeltet vært vår egen hukommelse om
    dokumentet, og en kropp som byttet ordlyd ville fått en for sterk
    lesemåte påstemplet uten at noe sa fra.
    """
    if ordlyd.casefold() not in tekst.casefold():
        raise Forskriftsfeil(
            f"{hva}: forventet ordlyden «{ordlyd}» i kroppen, men den står "
            f"der ikke. Lesemåten som er skrevet inn i uttrekket stemmer "
            f"ikke lenger med teksten. Ordrett: "
            f"…{' '.join(tekst.split())[:300]}…"
        )


_KAPITTELHODE = re.compile(
    r"Kapit(?:tel|el)\s+(\d{1,2})\s*[.:]\s*([^§]{3,240}?)\s*(?=§\s*\d)")


def _kapitteloverskrift(kropp: str, nr: int) -> str:
    """Overskriften til ett kapittel, ordrett.

    Leses av kroppen framfor å hardkodes, fordi det er overskriften som
    BÆRER fargeordet i 2020-kroppen («Nedjustering av tillatelseskapasitet
    i røde produksjonsområder»). En hardkodet streng ville gjort
    lesemåten `kapitteloverskrift` til en påstand om noe vi ikke leste.
    """
    for funnet, hode in _KAPITTELHODE.findall(kropp):
        if int(funnet) == nr:
            return " ".join(hode.split())
    raise Forskriftsfeil(
        f"Fant ingen overskrift for kapittel {nr}. Kapittelinndelingen er "
        f"endret — kroppen er arkivert, dette er en re-parse."
    )


# Hjemmelen som gjør et kapittel til et GRØNT kapittel: produksjons-
# områdeforskriften § 11 «Tilbud om kapasitetsøkning (akseptabel
# miljøpåvirkning)». Alle fire kroppene siterer den i hjemmelslinja.
_HJEMMEL_11 = re.compile(r"produksjonsområdeforskriften\)\s*§\s*11")


def _krev_vekst_hjemmel(kropp: str, kapitteloverskrift: str) -> None:
    """Utledningen «dette kapittelet er det grønne» skal hvile på
    kroppens egen hjemmelslinje, ikke på vår hukommelse.

    To krav, og begge leses av kroppen:

      1. forskriften er hjemlet i produksjonsområdeforskriften § 11, som
         er paragrafen om AKSEPTABEL miljøpåvirkning, og
      2. kapittelet handler om ØKT kapasitet.

    Det er så nær en avledet grønnfarge kan komme uten å bli lest, og
    lesemåten `kapittelhjemmel` sier at det er nettopp det den er.
    """
    if not _HJEMMEL_11.search(kropp):
        raise Forskriftsfeil(
            "Forskriften er ikke hjemlet i produksjonsområdeforskriften "
            "§ 11. Uten den hjemmelen er «kapittelet for økt kapasitet» "
            "ikke lenger kapittelet for akseptabel miljøpåvirkning, og "
            "grønnfargen kan ikke utledes av strukturen."
        )
    lav = kapitteloverskrift.casefold()
    if "økt" not in lav or "kapasitet" not in lav:
        raise Forskriftsfeil(
            f"Kapitteloverskriften «{kapitteloverskrift}» handler ikke om "
            f"økt kapasitet. Da er den ikke § 11-kapittelet, og grønn kan "
            f"ikke utledes av at et område står oppført under det."
        )


# --------------------------------------------------------- uttrekkene

def _uttrekk_2018(kropp: str) -> list[Celle]:
    """FOR-2017-12-20-2397, tildelingsrunde 2018.

    ## Kroppen inneholder ikke ett eneste fargeord

    Verifisert 05.09.2026: hverken «grønn», «gul» eller «rød» i noen
    bøyning står i dokumentet. Det er ikke en mangel ved uttrekket — det
    er formen på den første trafikklysforskriften.

    Det som finnes er § 3 første ledd: «Kapittel 2 om økt kapasitet på
    eksisterende tillatelser gjelder tillatelse hjemmehørende i følgende
    produksjonsområder», og åtte områder. Kapittel 2 er
    § 11-kapittelet — akseptabel miljøpåvirkning — så de åtte er grønne,
    UTLEDET. Lesemåten sier `kapittelhjemmel`.

    ## De fem øvrige områdene emitteres ikke

    PO 2, 3, 4, 5 og 6 står ingen steder i kroppen. Forskriften har intet
    kapittel om nedjustering: i denne runden ble ingen kapasitet
    nedjustert, og et rødt område ser i dette dokumentet nøyaktig ut som
    et gult. Å utlede gult av at området ikke fikk vekst ville vært å
    påstå fravær av rødt fra en kropp som ikke uttaler seg om rødt.

    ## Merk ordlyden i § 3

    2018-kroppen skyter inn «om økt kapasitet på eksisterende
    tillatelser» mellom kapittelnummeret og «gjelder». `_KAPITTELLEDD`
    klipper derfor på HENVISNINGEN og ikke på verbet — et mønster som
    krevde «Kapittel 2 gjelder» ville lest null ledd her og gitt null
    celler.
    """
    seksjon3 = _paragraf(kropp, "3", "4")
    ledd = _ledd_for(seksjon3, 2)
    hode = _kapitteloverskrift(kropp, 2)
    _krev_vekst_hjemmel(kropp, hode)

    celler = [Celle(2018, po, navn, GRONN, KAPITTELHJEMMEL)
              for po, navn in _omraader(ledd)]
    _krev_alle_omraader(ledd, celler, "§ 3 første ledd (kapittel 2)")
    return celler


def _uttrekk_2020(kropp: str) -> list[Celle]:
    """FOR-2020-02-04-105, tildelingsrunde 2020.

    ## To ledd med områder, og ETT fargeord

    § 3 har tre ledd. Kapittel 2 (ni områder) er § 11-kapittelet — grønn,
    `kapittelhjemmel`, som i 2018. Kapittel 4 (to områder) har en
    overskrift som selv sier fargen:

        «Kapittel 4. Nedjustering av tillatelseskapasitet i RØDE
         produksjonsområder»

    Derfor `kapitteloverskrift` og ikke `kapittelhjemmel` for PO 4 og
    PO 5. Skillet er lite, men det er skillet mellom å lese og å utlede,
    og det er nettopp det lesemåtefeltet finnes for.

    Det tredje leddet («Kapittel 3 gjelder tillatelser hjemmehørende i
    alle produksjonsområder») lister ingen områder — kapittel 3 er
    vekst UAVHENGIG av miljøstatus, som per definisjon ikke sier noe om
    farge.

    ## PO 3 og PO 10 emitteres ikke

    Ingen av dem står i § 3. PO 3 får sin farge for 2020 av
    2022-kroppen, som skriver «gult lys i 2020» ordrett. PO 10 for 2020
    står ingen steder i noen av de fire kroppene, og blir stående som et
    hull.
    """
    seksjon3 = _paragraf(kropp, "3", "4")
    hode2 = _kapitteloverskrift(kropp, 2)
    _krev_vekst_hjemmel(kropp, hode2)

    ledd2 = _ledd_for(seksjon3, 2)
    gronne = [Celle(2020, po, navn, GRONN, KAPITTELHJEMMEL)
              for po, navn in _omraader(ledd2)]
    _krev_alle_omraader(ledd2, gronne, "§ 3 første ledd (kapittel 2)")

    hode4 = _kapitteloverskrift(kropp, 4)
    _krev_ordlyd(hode4, "røde", "kapittel 4 skal si «røde» i overskriften")

    ledd4 = _ledd_for(seksjon3, 4)
    rode = [Celle(2020, po, navn, ROD, KAPITTELOVERSKRIFT)
            for po, navn in _omraader(ledd4)]
    _krev_alle_omraader(ledd4, rode, "§ 3 tredje ledd (kapittel 4)")

    return gronne + rode


def _uttrekk_2022(kropp: str) -> list[Celle]:
    """FOR-2022-06-07-972, tildelingsrundene 2020 og 2022.

    ## Første kropp med fargeord i selve bestemmelsene

    § 3: «Kapittel 3 gjelder for følgende (grønne) produksjonsområder»,
    åtte områder. Fargen står i samme setning som lista — `ordrett`, ikke
    `kapittelhjemmel`.

    Det er også kontrollen av utledningen i 2018 og 2020: den samme
    strukturelle plassen, § 11-kapittelet for økt kapasitet, er her
    merket grønn av kilden selv.

    ## § 4-tabellen bærer TO runder per rad

        Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022)
        Produksjonsområde 4 (rødt lys i 2020, rødt lys i 2022)
        Produksjonsområde 5 (rødt lys i 2020, gult lys i 2022)

    2020-halvdelen er en påstand om en runde som allerede er skrevet av
    2020-kroppen, og den er derfor en revisjonsrad i `diff.revisjon()`
    forstand. PO 4 og PO 5 stemmer med 2020-kroppens egen
    `kapitteloverskrift`-lesning; PO 3 er NY informasjon, som 2020-kroppen
    ikke bærer i det hele tatt.

    ## Årstallene i tabellen kontrolleres mot `FORSKRIFTER`

    Settet av runder tabellen nevner skal være nøyaktig de rundene
    tabellen i `FORSKRIFTER` sier kroppen uttaler seg om. Uten den
    kontrollen kunne uttrekket lese to av tre parenteser og fortsatt gi
    tre rader — riktig form, tapt runde.

    ## PO 2 og PO 7 emitteres ikke

    De står verken i den grønne lista eller i tabellen. Se modulens
    docstring om hvorfor «verken grønn eller rød» ikke skrives som gul.
    """
    seksjon3 = _paragraf(kropp, "3", "4")
    ledd3 = _ledd_for(seksjon3, 3)
    _krev_ordlyd(ledd3, "(grønne)",
                 "§ 3 skal merke kapittel 3-lista «(grønne)»")

    gronne = [Celle(2022, po, navn, GRONN, ORDRETT)
              for po, navn in _omraader(ledd3)]
    _krev_alle_omraader(ledd3, gronne, "§ 3 annet ledd (kapittel 3)")

    seksjon4 = _paragraf(kropp, "4", "5")
    tabell = _tabellceller(seksjon4)
    _krev_alle_tabellrader(seksjon4, tabell)
    _krev_runder(tabell, (2020, 2022), "FOR-2022-06-07-972")

    return gronne + tabell


def _uttrekk_2024(kropp: str) -> list[Celle]:
    """FOR-2024-03-22-515, tildelingsrundene 2020, 2022 og 2024.

    Samme to former som 2022-kroppen — «(grønne)» i § 3 og
    «farge lys i ÅÅÅÅ» i § 4-tabellen — men den er IKKE samme dokument,
    og uttrekket er derfor sitt eget:

      * den grønne lista er seks områder, ikke åtte,
      * hver tabellrad bærer TRE runder, ikke to, og
      * § 4 har i tillegg løpende tekst som omtaler «produksjonsområde 3
        og 4» og «produksjonsområde 5» med LITEN forbokstav. Tabellvakten
        krever stor P nettopp for å ikke lese de tre prosaomtalene som
        tabellrader og deretter kreve farger av dem.

    Å kalle `_uttrekk_2022` her ville vært riktig i dag og stille feil
    den dagen en av de tre forskjellene betydde noe. Se CLAUDE.md 1b-2.

    ## PO 2, 6, 7 og 8 emitteres ikke

    Fire områder står verken i den grønne lista eller i tabellen — flere
    enn i noen annen kropp, fordi den grønne lista krympet fra åtte til
    seks uten at tabellen vokste.
    """
    seksjon3 = _paragraf(kropp, "3", "4")
    ledd3 = _ledd_for(seksjon3, 3)
    _krev_ordlyd(ledd3, "(grønne)",
                 "§ 3 skal merke kapittel 3-lista «(grønne)»")

    gronne = [Celle(2024, po, navn, GRONN, ORDRETT)
              for po, navn in _omraader(ledd3)]
    _krev_alle_omraader(ledd3, gronne, "§ 3 annet ledd (kapittel 3)")

    seksjon4 = _paragraf(kropp, "4", "5")
    tabell = _tabellceller(seksjon4)
    _krev_alle_tabellrader(seksjon4, tabell)
    _krev_runder(tabell, (2020, 2022, 2024), "FOR-2024-03-22-515")

    return gronne + tabell


def _krev_runder(celler: list[Celle], ventet: tuple[int, ...],
                 hvem: str) -> None:
    """Rundene tabellen NEVNER skal være nøyaktig de vi har skrevet opp.

    Kontrollen går begge veier med vilje. Færre runder enn ventet betyr
    at uttrekket mistet en parentes; flere betyr at kroppen har begynt å
    uttale seg om en runde `FORSKRIFTER` ikke vet om, og da er
    `Forskrift.aar` — som styrer hvilke snapshots backfillen skriver —
    ute av takt med dokumentet.
    """
    funnet = tuple(sorted({c.runde for c in celler}))
    if funnet != tuple(sorted(ventet)):
        raise Forskriftsfeil(
            f"{hvem}: § 4-tabellen uttaler seg om rundene {funnet}, men "
            f"FORSKRIFTER sier {tuple(sorted(ventet))}. Enten leste "
            f"uttrekket for få parenteser, eller så dekker kroppen en "
            f"runde tabellen ikke kjenner. Begge deler skal rettes mot "
            f"kroppen, ikke rundes av."
        )


# ------------------------------------------------------------ forskriftene

class Forskrift(NamedTuple):
    """Én kapasitetsjusteringsforskrift: hva den heter, hvilke runder den
    uttaler seg om, hvor den ligger, og hvem som leser den."""

    # Ordrett fra dokumentets overskrift på lovdata.no. Sammen med
    # FOR-nummeret er dette hvordan `parse()` VET hvilken forskrift den
    # har fått — den gjetter ikke ut fra filnavn, URL eller rekkefølge.
    tittel: str
    # FOR-nummeret. Den EKSAKTE identiteten; tittelen er kontrollen.
    forskrift_id: str
    # Tildelingsrundene forskriften uttaler seg om, ELDST FØRST.
    #
    # Feltet heter `aar` og ikke `runder` fordi `backfill.py --rapporter`
    # leser NAVNET på tvers av kilder (`utgivelse.aar`), og kjernen skal
    # ikke endres for å legge til en kilde (CLAUDE.md regel 1). For denne
    # kilden er et «år» en tildelingsrunde.
    aar: tuple[int, ...]
    url: str
    uttrekk: Callable[[str], list[Celle]]
    merknad: str = ""


# Forskriftene vi HAR LEST og skrevet et uttrekk for, ELDST FASTSATT FØRST.
#
# Rekkefølgen er utgivelsesrekkefølge, og den er ikke kosmetisk:
# `backfill.py --rapporter` går gjennom dem i denne rekkefølgen, slik at
# hver runde først skrives av den eldste forskriften som dekker den og
# deretter revideres av de nyere. Går den motsatt vei, ville hver eldre
# forskrift blitt en `Feilrekkefolge` mot en nyere påstand som alt lå der.
#
# Runde 2026 står IKKE her, og det er ikke en forglemmelse: den er målt
# fraværende i Norsk Lovtidend avdeling I 05.09.2026. Se modulens
# docstring.
#
# URL-ene peker på LTI-versjonen (teksten slik den ble kunngjort), ikke
# på SF (den konsoliderte). Se modulens docstring om hvorfor.
FORSKRIFTER: tuple[Forskrift, ...] = (
    Forskrift(
        tittel=("Forskrift om kapasitetsøkning for tillatelser til "
                "akvakultur med matfisk i sjø av laks, ørret og "
                "regnbueørret i 2017-2018"),
        forskrift_id="FOR-2017-12-20-2397",
        aar=(2018,),
        url="https://lovdata.no/dokument/LTI/forskrift/2017-12-20-2397",
        uttrekk=_uttrekk_2018,
        merknad=("Første trafikklysrunde. Kroppen inneholder INGEN "
                 "fargeord — åtte grønne områder utledes av at kapittel 2 "
                 "er § 11-kapittelet, og de fem øvrige emitteres ikke."),
    ),
    Forskrift(
        tittel=("Forskrift om kapasitetsjusteringer for tillatelser til "
                "akvakultur med matfisk i sjø av laks, ørret og "
                "regnbueørret i 2020"),
        forskrift_id="FOR-2020-02-04-105",
        aar=(2020,),
        url="https://lovdata.no/dokument/LTI/forskrift/2020-02-04-105",
        uttrekk=_uttrekk_2020,
        merknad=("Eneste kropp der fargeordet står i en KAPITTELOVERSKRIFT "
                 "og ikke i en bestemmelse: «Kapittel 4. Nedjustering av "
                 "tillatelseskapasitet i røde produksjonsområder»."),
    ),
    Forskrift(
        tittel=("Forskrift om kapasitetsjusteringer for tillatelser til "
                "akvakultur med matfisk i sjø av laks, ørret og "
                "regnbueørret i 2022"),
        forskrift_id="FOR-2022-06-07-972",
        aar=(2020, 2022),
        url="https://lovdata.no/dokument/LTI/forskrift/2022-06-07-972",
        uttrekk=_uttrekk_2022,
        merknad=("Endret tre ganger etter kunngjøring (FOR-2022-06-16-1058, "
                 "FOR-2022-09-28-1671, FOR-2022-10-06-1721). Vi leser "
                 "LTI-versjonen, som ikke endrer seg."),
    ),
    Forskrift(
        tittel=("Forskrift om kapasitetsjusteringer for tillatelser til "
                "akvakultur med matfisk i sjø av laks, ørret og "
                "regnbueørret i 2024"),
        forskrift_id="FOR-2024-03-22-515",
        aar=(2020, 2022, 2024),
        url="https://lovdata.no/dokument/LTI/forskrift/2024-03-22-515",
        uttrekk=_uttrekk_2024,
        merknad="Nyeste FASTSATTE runde. 2026 er på høring, ikke vedtatt.",
    ),
)

# Nyeste runde noen forskrift i `FORSKRIFTER` uttaler seg om. Regnes ut av
# tabellen framfor å stå som en konstant — to tall for samme sak er formen
# F6 og F7 hadde, og dette ville vært et som må huskes oppdatert.
NYESTE_RUNDE = max(runde for f in FORSKRIFTER for runde in f.aar)


def gjenkjenn(flat: str) -> Forskrift:
    """Hvilken forskrift denne kroppen ER, lest av dokumentet.

    Ikke av filnavnet, ikke av URL-en, ikke av rekkefølgen den ble hentet
    i. Alle tre kan være feil for en kropp som er lastet ned for hånd
    eller spilt av på nytt fra arkivet — og en kropp som blir tolket som
    feil forskrift ville fått riktig form og feil runde.

    TO uavhengige lesninger må stemme: FOR-nummeret i metadatablokken og
    tittelen i overskriften. FOR-nummeret alene ville holdt, men da ville
    en Lovdata-side som byttet metadataformat kunnet gi et treff på et
    tall fra en helt annen del av siden.
    """
    forskrift_id = _forskrift_id(flat)
    normalisert = " ".join(flat.split())
    for forskrift in FORSKRIFTER:
        if forskrift.forskrift_id != forskrift_id:
            continue
        if forskrift.tittel not in normalisert:
            raise Forskriftsfeil(
                f"Kroppen oppgir {forskrift_id}, men tittelen "
                f"«{forskrift.tittel}» står ikke i den. De to lesningene "
                f"er uenige, og da er det ikke avgjort hvilken forskrift "
                f"dette er."
            )
        return forskrift
    raise Forskriftsfeil(
        f"Kroppen er {forskrift_id}, som ikke står i FORSKRIFTER. Kjente: "
        + ", ".join(f.forskrift_id for f in FORSKRIFTER)
        + ". Er dette en ny runde, må den få en egen uttrekksfunksjon — se "
          "modulens docstring om hvorfor det ikke finnes en generisk."
    )


# ---------------------------------------------------------------- kilden

class Trafikklysvedtak(Source):
    name = "trafikklysvedtak"

    version = "1"

    # Samme entitetstype som ekspertgruppen og biomasse, med vilje: en
    # analyse skal kunne joine vedtak mot råd og mot beholdning på
    # `entity_id` uten en oversettelse.
    entity_type = "produksjonsomraade"

    # Sju for en TOÅRIG kilde. Se modulens docstring — dette er ikke en
    # påstand om vedtakstakt, men om hvor ofte kjøringen skal få spørre
    # `finnes_allerede()`.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.trafikklysvedtak.aktiv", False))

    # ---- henting -------------------------------------------------------

    def utgivelser(self) -> tuple[Forskrift, ...]:
        """Forskriftene kilden kan lese, ELDST FASTSATT FØRST.

        `backfill.py` dispatcher på at denne finnes — samme
        egenskapsbaserte utvelgelse som `hent_uke()` og `hent_alt()`, og
        av samme grunn: kilden vet hvilken form den har, og et flagg
        brukeren kan sette feil er et sted til å være uenig.
        """
        return FORSKRIFTER

    def hent_rapport(self, utgivelse: Forskrift,
                     client: httpx.Client | None = None,
                     url: str | None = None) -> bytes:
        """Én forskriftskropp som rå HTML-bytes.

        Returnerer BYTES og ikke uttrukket tekst, fordi kjernen arkiverer
        det `fetch()` returnerer og det som arkiveres skal være det
        tjenesten faktisk sendte. En parser som forbedres senere kjører da
        på nytt uten å hente igjen — hele begrunnelsen for rå-arkivet.

        Metodenavnet er `hent_rapport` og ikke `hent_forskrift` fordi
        `backfill.py --rapporter` kaller det navnet på tvers av kilder, og
        kjernen skal ikke endres for å legge til en kilde.

        `published_at` settes HER, av dokumentets ikrafttredelsesfelt, og
        ikke av noen HTTP-header. Lovdata sender ingen `Last-Modified` for
        disse dokumentene — se modulens docstring.

        `utvalg` settes HER av samme grunn som i `biomasse.hent_alt()`:
        dette er det ene stedet begge veier inn i kilden går gjennom.
        `{}` er riktig og ikke et gjett — vi ber om hele forskriften og
        får hele forskriften.
        """
        self.utvalg = {}

        egen = client is None
        c = client or httpx.Client(timeout=60.0, follow_redirects=True)
        try:
            svar = _http.get(c, url or utgivelse.url,
                             hva=f"trafikklysvedtak {utgivelse.forskrift_id}")
            rå = svar.content
        finally:
            if egen:
                c.close()

        # SETT, ikke append: `advarsler` er en liste på KLASSEN, som
        # deles av alle instanser og aldri tømmes. Se Source.advarsler.
        advarsler: list[str] = []
        self.published_at = _utgitt(_tekst(rå), advarsler)
        self.advarsler = advarsler
        return rå

    def arkivdato(self, utgivelse: Forskrift) -> str:
        """Under hvilken dato en forskrifts kropp er arkivert.

        `_backfill_rapporter` arkiverer under `aar_i(rå)[-1]`, altså siste
        runde kroppen dekker. Regelen står HER og ikke i backfillen, av
        samme grunn som `aar_i` gjør det: kalleren skal slippe å kjenne
        dokumentformatet for å finne igjen en kropp den selv har lagt vekk.
        """
        return siste_dag(utgivelse.aar[-1])

    def gjenkjenn_kropp(self, rå: bytes) -> Forskrift:
        """Hvilken forskrift en arkivert kropp ER, lest av dokumentet.

        Samme svar som `gjenkjenn()`, men uten at kalleren må vite at
        identiteten står i en metadatablokk i HTML-en.
        """
        return gjenkjenn(_tekst(rå))

    def utgitt_av(self, rå: bytes, utgivelse: Forskrift) -> str:
        """`published_at` for en kropp som kommer fra ARKIVET, ikke nettet.

        `hent_rapport()` setter feltet som en sidevirkning av hentingen.
        En re-parse henter ikke, og skal likevel ende med det SAMME
        utgivelsestidspunktet — det leses av kroppens eget
        ikrafttredelsesfelt, og kroppen er byte for byte den samme.

        Uten dette måtte `backfill.py --reparse` enten gjettet datoen
        eller falt tilbake på hentetidspunktet, som er I DAG. Da ville den
        ELDSTE forskriften fått det NYESTE tidspunktet, og revisjonsaksen
        lest baklengs — nøyaktig feilen 1b-7 finnes for.
        """
        advarsler: list[str] = []
        self.published_at = _utgitt(_tekst(rå), advarsler)
        self.advarsler = advarsler
        self.utvalg = {}
        return self.published_at

    def aar_i(self, rå: bytes) -> list[str]:
        """Gyldighetsdatoene en kropp bærer, eldst først.

        Kroppen svarer selv: metadatablokken sier hvilken forskrift den
        er, og `FORSKRIFTER` sier hvilke runder den forskriften uttaler
        seg om. Samme rolle som `biomasse.maaneder()`.
        """
        return [siste_dag(runde) for runde in gjenkjenn(_tekst(rå)).aar]

    def gjelder_for(self, kjoredato: str) -> str:
        """Siste dag i nyeste FASTSATTE runde — ikke kjøreåret.

        For denne kilden spriker de to med to år i dag (2024 mot 2026), og
        det er riktig: `observed_at` handler om verden, kjøredatoen om
        oss. Så lenge 2024 ligger skrevet, hopper steg 2b i `run.py` over
        kilden uten å hente.

        Kjøredatoen tas inn og brukes IKKE til å slå opp klokka — den er
        med fordi kontrakten sier at `fetch()` og `gjelder_for()` skal få
        tiden inn, og fordi en framtidig runde skal kunne begrenses av den
        uten at signaturen endres.
        """
        return siste_dag(NYESTE_RUNDE)

    def fetch(self, kjoredato: str) -> bytes:
        """Nyeste forskriftskropp vi har et uttrekk for.

        Den løpende jobben henter ÉN forskrift — den nyeste — og skriver
        én runde av den. Historikken og de eldre kroppene går gjennom
        `backfill.py --rapporter`, som er det ene stedet
        utgivelsesrekkefølgen håndheves.
        """
        for forskrift in reversed(FORSKRIFTER):
            if NYESTE_RUNDE in forskrift.aar:
                return self.hent_rapport(forskrift)
        raise Forskriftsfeil(
            f"Ingen forskrift i FORSKRIFTER dekker {NYESTE_RUNDE}. Tabellen "
            f"og NYESTE_RUNDE er ute av takt."
        )

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: bytes, observed_at: str) -> Iterable[Observation]:
        """Én tildelingsrunde ut av en kropp som kan bære flere.

        `observed_at` VELGER runden, kroppen BEKREFTER den. Samme
        rekkefølge og samme begrunnelse som `biomasse.parse()` og
        `ekspertgruppen.parse()`: én kropp bærer flere runder, så det
        finnes ikke noe i dataene å utlede datoen fra, og det eneste
        forsvaret mot at kjernen og kroppen er uenige er å sjekke at
        runden faktisk er der.

        Kaster `Rundemangler` hvis den ikke er det. Alternativet — å
        skrive et tomt snapshot — ville sett vellykket ut, låst runden mot
        senere skriving via `finnes_allerede()`, og gjort hullet permanent.

        ## Uttrekket kjøres for HELE kroppen, og filtreres etterpå

        Ikke fordi det er enklere, men fordi vaktene trenger det.
        § 4-tabellen bærer to eller tre runder i samme parentes, og en
        vakt som bare så runden vi ba om ville ikke merket at parentesens
        eldste årstall aldri ble lest. Kjøres uttrekket helt, feller
        `_krev_alle_tabellrader` og `_krev_runder` den feilen uansett
        hvilken runde snapshotet gjelder.
        """
        runde = runde_av(observed_at)
        flat = _tekst(raw)
        forskrift = gjenkjenn(flat)
        if runde not in forskrift.aar:
            raise Rundemangler(
                f"«{forskrift.tittel}» ({forskrift.forskrift_id}) uttaler "
                f"seg om rundene "
                f"{', '.join(str(a) for a in forskrift.aar)}, ikke om "
                f"{runde}. Ingenting skrives — et tomt snapshot ville låst "
                f"runden."
            )

        kropp = _forskriftstekst(flat)
        alle = forskrift.uttrekk(kropp)
        if not alle:
            raise Forskriftsfeil(
                f"Uttrekket for {forskrift.forskrift_id} fant ingenting. "
                f"Formatet er endret — kroppen er arkivert, så dette er en "
                f"re-parse og ikke tapt historikk."
            )

        celler = [c for c in alle if c.runde == runde]
        if not celler:
            raise Forskriftsfeil(
                f"{forskrift.forskrift_id} skal uttale seg om runde "
                f"{runde}, men uttrekket ga null celler for den. "
                f"FORSKRIFTER og uttrekket er uenige."
            )

        # Områdenavnet står bare i § 3-listene. En celle fra
        # § 4-tabellen har ingen, og arver den lista har for samme
        # område i den samme kroppen — ikke fra en annen kropp og ikke
        # fra produksjonsområdeforskriftens vedlegg, som ville vært en
        # andre kilde smuglet inn i den første.
        navn = {c.po: c.navn for c in alle if c.navn}

        sett: set[str] = set()
        for celle in sorted(celler, key=lambda c: int(c.po)):
            if celle.po in sett:
                raise Forskriftsfeil(
                    f"Uttrekket ga to farger for PO{celle.po} i runde "
                    f"{runde}. `snapshot.NOKKEL` ville beholdt den første "
                    f"stilltiende."
                )
            sett.add(celle.po)

            felles = dict(entity_id=celle.po, entity_type=self.entity_type,
                          entity_name=navn.get(celle.po, ""),
                          source=self.name, observed_at=observed_at)
            yield Observation(field=F_FARGE, value=celle.farge, **felles)
            # Lesemåten lagres SAMMEN med verdien, ikke ved siden av den.
            # Se CLAUDE.md 1b-3 og modulens docstring.
            yield Observation(field=F_FARGE + LESEMAATE_SUFFIKS,
                              value=celle.lesemaate, **felles)
