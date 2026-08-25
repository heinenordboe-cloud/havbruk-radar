"""Biomasse (Fiskeridirektoratet) — beholdning per produksjonsområde per måned.

Verifisert mot levende tjeneste 25.08.2026, se docs/KILDE-BIOMASSE.md.
Alt i denne docstringen er MÅLT mot den nedlastede fila, ikke lest ut av
dokumentasjonen.

Endepunkt — én statisk fil, ikke et API:

    https://register.fiskeridir.no/biomassestatistikk/
        BIOSTAT-LAKS-OMR/biostat-total-omr.csv

Fila bærer HELE serien i hver nedlasting: 2017-10 til 2026-07, 106
måneder uten hull, 5199 rader, 650 kB. Det finnes ingen spørrestreng,
ingen paginering og ingen måte å be om én måned.

Lisens: NLOD. Attribusjon «Kilde: Fiskeridirektoratet» kreves av enhver
sammenstilling som bruker disse tallene. Ingen nøkkel, ingen
registrering, ingen avtale.

## Hvorfor kilden finnes: antall fisk

`BEHFISK_STK` er ANTALL FISK, ikke tonnasje. Tjenestens egen
`Forklaring`-blokk (i fylkesvarianten, se under om metadatafeilen):

    BEHFISK_STK   «Beholdning av fisk ved månedslutt, målt i antall stk.»
    BIOMASSE_KG   «Biomasse ved månedslutt. Biomasse er definert som
                   antall fisk multiplisert med gjennomsnittlig vekt.»

Kausaliteten går altså motsatt vei av det man skulle tro: antallet er
det innrapporterte, biomassen er det avledede. Stien mfl. 2005 sitt
`N_fisk` kan leses direkte. Ingen omregning med snittvekt, ingen
tilnærming å dokumentere.

## Om etterslepet — det er MÅNEDER, og det er ikke lusetalls N-4

Innrapporteringsfristen er den 7. i påfølgende måned
(akvakulturdriftsforskriften § 44, via Altinn). Fila publiseres på nytt
den 20. hver måned. Måned M er altså først synlig ~50 dager etter at M
begynte.

Det er den ene halvdelen. Den andre er at fila REVIDERES bakover, og at
revisjonen har en målbar avklingingskurve. Målt ved å krysse en
Wayback-kopi hentet 07.08.2024 mot dagens fil, 3973 felles rader:

    alder ved 2024-hentingen     andel rader som SENERE ble revidert
    0 mnd (ferskeste måned)                  28,8 %
    1 mnd                                    19,2 %
    2 mnd                                    11,3 %
    3 mnd                                    10,4 %
    4-80 mnd                            ~8-15 %, flatt

Kurven flater ut ved to måneders alder. Resten — omtrent 11 % — er ikke
etterslep som setter seg; det er permanent omklassifisering som ingen
ventetid fjerner (se neste avsnitt). Å vente lenger enn til alder 2
kjøper altså ingenting.

`maaneder_etterslep = 4` er valgt for å GARANTERE alder >= 2 uansett
hvilken dag i måneden jobben kjører:

  - kjører vi den 20. eller senere, er ferskeste publiserte måned
    kjøremåneden minus 1, og måneden vi skriver har alder 3
  - kjører vi før den 20., er ferskeste publiserte måned kjøremåneden
    minus 2, og måneden vi skriver har alder 2

Tre ville gitt alder 1 (19,2 %) halvparten av dagene. Grensen skal ikke
avhenge av hvilken ukedag cron traff.

`parse()` kontrollerer at måneden faktisk ligger i fila og kaster hvis
den ikke gjør det. Regnestykket over er vårt; fila vet selv hvilke
måneder den bærer, og når motparten kan svare er svaret dens bedre enn
vårt (F13). Regnestykket velger måneden, fila bekrefter den.

## Om REVISJON — fortiden ligger ikke fast her

Dette er en kilde av et slag repoet ikke har hatt før. Registrene vi
ellers henter fra sier hva som gjelder NÅ; denne sier hva
Fiskeridirektoratet i dag MENER gjaldt i 2017, og den meningen endrer
seg. Målt mellom 2024-kopien og dagens fil: 490 av 3973 felles rader
(12,3 %) er endret, fordelt over hvert eneste år tilbake til 2017.

Mekanismen er ikke nye innrapporteringer. Summen av `BEHFISK_STK` over
alle felles rader endret seg 0,006 %, mens 12,3 % av radene beveget seg.
De største utslagene kommer i SPEILPAR: PO 5 / REGNBUEØRRET /
utsettsår 2017 for oktober 2017 gikk fra 2 553 307 til 1 130 530 fisk,
mens `(null)` for samme celle gikk fra 310 173 til 1 732 950 — nøyaktig
1 422 777 fisk flyttet begge veier. Lokaliteter blir omklassifisert
mellom produksjonsområder i ettertid.

Aggregert til PO-år, som er nivået analysen bruker: 15 av 78 celler for
2018-2023 er endret, 9 av dem mer enn 1 %, største utslag PO 5 i 2018
(256,5 -> 246,5 mill. fisk, et fall på 3,90 %).

Konsekvensen for innsamlingen, og den er hele grunnen til at kilden er
bygget slik den er:

  - Ett snapshot per måned, `observed_at` = siste dag i måneden. Det er
    ikke en dato vi har valgt for pynt: `BEHFISK_STK` er beholdning ved
    MÅNEDSLUTT, og strømmene (fôr, uttak, dødfisk) er summert over
    måneden og dermed også ferdige da.
  - `fetched_at` settes av kjernen til kjøredatoen. To snapshots som er
    uenige om 2018 er ikke en feil — de sier hva kilden sa på hver sin
    dato, og begge er sanne utsagn.
  - INGEN rad skrives om. Fila for en måned skrives én gang.

Og det viktigste: `fetch()` returnerer HELE fila, ikke måneden vi skal
skrive. Kjernen arkiverer det `fetch()` returnerer (`runner.run_all`:
fetch, arkiver, parse), så hver kjøring legger igjen en komplett kopi av
serien slik den så ut den dagen, i `data/arkiv/biomasse/`. Det er den
eneste stedet historikken over hva Fiskeridirektoratet SA om fortiden
finnes — hos dem forsvinner forrige versjon den 20. hver måned.

At arkivet får nøyaktig én kopi per publisering følger av `min_dager_mellom`
under.

## Om `min_dager_mellom = 7` for en månedlig kilde

Dette ser feil ut og er det ikke. Sju betyr ikke «kilden endrer seg hver
uke» — den endrer seg den 20. hver måned. Sju betyr «tilby kilden til
kjøringen hver uke, og la `finnes_allerede()` avgjøre».

Grunnen er at `min_dager_mellom` teller DAGER SIDEN SIST, mens målet vårt
er en KALENDERMÅNED. De to glir fra hverandre, og glidningen lager hull:
med 28 dager og en ukentlig cron kan et vellykket treff sent i mars gjøre
kilden forfalt 28. april, som en cron på mandager kan bomme på — og da
hopper `gjelder_for()` fra én måned til den neste uten at måneden
imellom noen gang blir skrevet. Med 31 dager er hullet enda lettere å
treffe.

Med sju er kilden forfalt hver uke, `gjelder_for()` peker på samme
måned i tre-fire uker på rad, og steg 2b i run.py hopper over den med
`[har] biomasse ...`. Det koster ingenting: 2b kjører FØR hentingen, så
en måned som ligger skrevet kaster ikke bort et nedlastingskall.

Bieffekten er ønsket: den ene kjøringen per måned som faktisk henter,
skjer i løpet av månedens første sju dager, altså alltid før den 20.
Hver publisering blir derfor arkivert nøyaktig én gang — ingen
publisering hoppes over, ingen arkiveres to ganger.

## Om `(null)` — den lagres, den filtreres ikke bort

0,96-4,57 % av all fisk ligger på rader der `PO_KODE` er `(null)`. Den
opplagte forklaringen — settefisk og landanlegg — holder ikke: snittvekten
i `(null)`-radene er 2,02 kg mot 1,86 kg i PO-radene. Det er voksen
matfisk uten produksjonsområde. ÅRSAKEN ER UKJENT, og skal stå som ukjent
til noen har spurt Fiskeridirektoratet.

Radene lagres som entiteten `uten_po`. De filtreres ikke bort, fordi en
nevner som forsvinner stille er verre enn en nevner som er rar: en
analyse som summerer PO 1-13 og kaller det «Norge» tar systematisk feil
med opptil 4,6 %, og ville ikke merket det.

`andel_av_beholdning` emitteres derfor for HVER entitet — også for de
tretten ekte produksjonsområdene. Feltet er AVLEDET (entitetens
`beholdning_antall` delt på summen over alle fjorten), og det er med
vilje lagret i stedet for regnet ut senere: det er nevneren, og en
konsument som har droppet `uten_po` får da et tall som ikke stemmer med
vårt, i stedet for et tall som ser riktig ut. Samme begrunnelse som
CLAUDE.md 1b-3 — verdien som avgjør hva dataene BETYR, lagres sammen med
dem.

At feltet emitteres for alle fjorten og ikke bare for `uten_po` er ikke
kosmetikk heller. Et felt med ÉN rad har per konstruksjon null minoritet,
og `health._vurder_innhold()` ville lest det som et dødt felt og fyrt hver
måned i det uendelige. Fjorten rader med fjorten ulike andeler gir
minoritet 13.

## Hva kilden emitter, og hva den lar være

Ni målte felter per produksjonsområde, pluss den avledede andelen:

    beholdning_antall              BEHFISK_STK, summert over art og utsettsår
    beholdning_antall_laks         samme, bare LAKS
    beholdning_antall_regnbueorret samme, bare REGNBUEØRRET
    biomasse_kg                    BIOMASSE_KG
    utsett_smolt_antall            UTSETT_SMOLT_STK
    uttak_antall                   UTTAK_STK
    dodfisk_antall                 DØDFISK_STK
    romming_antall                 RØMMING_STK
    forforbruk_kg                  FORFORBRUK_KG
    andel_av_beholdning            avledet, se over

Utsettsår summeres bort. Fila har `UTSETTSÅR` som egen akse, og den er
ekte informasjon (fiskens generasjon), men den ville ganget feltantallet
med fem-seks og gitt kohorter som oppstår og forsvinner — altså
«ny»/«borte» i changeloggen hver gang en generasjon slaktes ut. Skal den
inn senere, er det en RE-PARSE av arkivet og ikke tapt historikk: hele
fila ligger arkivert for hver kjøring.

De øvrige kolonnene (`UTTAK_KG`, `UTTAK_SLØYD_KG`, `UTTAK_HODEKAPPET_KG`,
`UTTAK_RUNDVEKT_KG`, `UTKAST_STK`, `ANDRE_STK`, `ANDRE_NY_STK`,
`TELLEFEIL_STK`, `UTSETT_SMOLT_STK_MINDRE_ENN_500G`) leses ikke. Samme
begrunnelse, og de sjekkes derfor heller ikke i `PAAKREVDE`: en kolonne
vi ikke leser skal ikke kunne felle en måned.

## Om en art som mangler

903 av 1484 PO-måneder har bare LAKS. Da emitteres
`beholdning_antall_regnbueorret = 0`, ikke ingenting.

Det er en TOLKNING, og den er begrunnet i en måling: fila inneholder 250
rader med `BEHFISK_STK = 0` — eksplisitte nuller for kohorter som er
slaktet helt ut i løpet av måneden (2017-10, PO 12, LAKS 2015: null
beholdning, 336 597 uttak). Registeret skriver altså nullen når kohorten
finnes. En kohort som ikke finnes i det hele tatt har ingen fisk, og
null er det riktige svaret — ikke «vet ikke».

Motsatt valg ville gitt et felt som forsvinner og kommer tilbake alt
etter hvilke arter som står i sjøen, og feltvakten i `health.py` er
bygget for å reagere på nettopp det.

## Om parsing

  - UTF-8 med BOM (`utf-8-sig`), `;`-separert, norske kolonnenavn.
  - `PO_KODE` har byttet format: `01` i 2024-kopien, `1` i dag. Den
    normaliseres til usignert heltall som tekst, og en kode som verken
    er et tall eller `(null)` KASTER. Vår egen `prodomraade_kode` fra
    akvakultur er `'1'`..`'13'`, verifisert mot siste snapshot, så
    koblingen er direkte når normaliseringen er gjort.
  - Skjemaet vokste fra 21 til 23 kolonner i 2024 (`ANDRE_NY_STK`,
    `TELLEFEIL_STK`, begge udokumenterte i tjenestens `Forklaring`).
    Vi leser ingen av dem, og en ny kolonne til skal ikke felle noe.
  - JSON-varianten har FEIL metadata: `Metadata.Tittel` sier «Utsett av
    rensefisk pr. lokalitet (fylke)» og `Forklaring` beskriver felter
    som ikke finnes i `Data`. Dataene er riktige, metadatablokken er
    kopiert fra feil fil. Derfor CSV.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from typing import Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

STANDARD_URL = (
    "https://register.fiskeridir.no/biomassestatistikk/"
    "BIOSTAT-LAKS-OMR/biostat-total-omr.csv"
)

# Første måned i serien. Produksjonsområdene ble innført 15.10.2017 med
# trafikklyssystemet, så det finnes ikke eldre PO-tall å hente — verken
# her eller andre steder. Fylkesvarianten går til 2005, men fylke er ikke
# produksjonsområde. Se docs/KILDE-BIOMASSE.md.
TIDLIGSTE = (2017, 10)

# Antall produksjonsområder. Målt: alle tretten er til stede i hver
# eneste av de 106 månedene, og `(null)` likeså.
ANTALL_PO = 13

# Entiteten radene uten produksjonsområde samles under. Ikke `(null)`,
# som er tjenestens måte å skrive «tomt» på og ville sett ut som en
# manglende verdi i enhver senere lesing.
UTEN_PO = "uten_po"
UTEN_PO_NAVN = "Uten produksjonsområde"

# Kolonnenavnene, verifisert 25.08.2026. Norske, med BOM, laget for et
# regneark. De er en kontrakt vi ikke eier — derfor står de her som
# navngitte konstanter og sjekkes eksplisitt, i stedet for å leses med
# .get() som gir None og en stille tom måned.
KOL_AAR = "ÅR"
KOL_MND = "MÅNED_KODE"
KOL_PO = "PO_KODE"
KOL_PO_NAVN = "PO_NAVN"
KOL_ART = "ARTSID"

ART_LAKS = "LAKS"
ART_REGNBUE = "REGNBUEØRRET"

# felt -> kolonne. Rekkefølgen her er rekkefølgen observasjonene kommer
# ut i, og den er stabil mellom kjøringer med vilje: parquet-fila skal
# ikke få et nytt innhold i git bare fordi en dict ble iterert annerledes.
SUMFELT: dict[str, str] = {
    "beholdning_antall": "BEHFISK_STK",
    "biomasse_kg": "BIOMASSE_KG",
    "utsett_smolt_antall": "UTSETT_SMOLT_STK",
    "uttak_antall": "UTTAK_STK",
    "dodfisk_antall": "DØDFISK_STK",
    "romming_antall": "RØMMING_STK",
    "forforbruk_kg": "FORFORBRUK_KG",
}

FELT_LAKS = "beholdning_antall_laks"
FELT_REGNBUE = "beholdning_antall_regnbueorret"
FELT_ANDEL = "andel_av_beholdning"

# Bare kolonnene vi FAKTISK leser. En kolonne vi ignorerer skal ikke
# kunne felle en måned — se docstringen om skjemaveksten i 2024.
PAAKREVDE = (KOL_AAR, KOL_MND, KOL_PO, KOL_PO_NAVN, KOL_ART,
             *SUMFELT.values())

# Antall desimaler `BIOMASSE_KG` summeres til. Målt: kolonnen har maks
# tre desimaler i kilden. Uten avrunding gir flyttallsummen
# 3615930.4530000002 den ene kjøringen og 3615930.453 den neste, og
# diffen rapporterer en endring som ikke har skjedd.
DESIMALER_KG = 3

# Andelen lagres som brøk, ikke prosent, med seks desimaler. Seks fordi
# den minste ekte andelen vi har målt er 0,0096 og skal kunne bevege seg
# meningsfullt; brøk fordi `value` er tekst og typingen skjer i analysen.
DESIMALER_ANDEL = 6


class Kolonnefeil(RuntimeError):
    """Fila kom, men ikke med kolonnene vi leser.

    Egen type fordi den betyr noe annet enn et nettverksavbrudd: den sier
    at formatet er endret, og at rå-CSV-en må re-parses etterpå. Den er
    arkivert, så det er en re-parse og ikke tapt historikk.
    """


class Maanedmangler(RuntimeError):
    """Måneden vi skulle skrive ligger ikke i fila.

    Etterslepsregnestykket er VÅRT; fila vet selv hvilke måneder den
    bærer. Spriker de to, er publiseringen forsinket eller formatet
    endret — og begge deler skal felle måneden høylytt framfor å skrive
    et tomt snapshot som ser vellykket ut.
    """


# ---------------------------------------------------------------- kalender

def maaned_med_etterslep(dato: dt.date, maaneder: int) -> tuple[int, int]:
    """Måneden vi henter når vi kjører `dato`. Ingen klokkeoppslag her.

    Regner i måneder siden år 0 for å slippe grensetilfellene rundt
    årsskiftet: `dato.month - 4` er -1 i januar.
    """
    n = dato.year * 12 + (dato.month - 1) - maaneder
    return n // 12, n % 12 + 1


def siste_dag(aar: int, maaned: int) -> str:
    """ISO-dato for siste dag i måneden.

    Det er datoen et snapshot for denne måneden BÆRER, fordi
    `BEHFISK_STK` er beholdning ved månedslutt. Se modulens docstring.
    """
    neste = (dt.date(aar + 1, 1, 1) if maaned == 12
             else dt.date(aar, maaned + 1, 1))
    return (neste - dt.timedelta(days=1)).isoformat()


def maaned_av(observed_at: str) -> tuple[int, int]:
    """(år, måned) for en gyldighetsdato. Kaster hvis den ikke er
    månedens siste dag.

    Kontrollen er ikke pedanteri. Ett snapshot er ett tidspunkt, og
    filnavnet er det eneste alt nedstrøms leser datoen fra (F6). Et
    snapshot som het 2018-03-15 ville påstått at beholdningen ble målt
    midt i mars, og det gjør den ikke.
    """
    d = dt.date.fromisoformat(observed_at)
    if siste_dag(d.year, d.month) != observed_at:
        raise ValueError(
            f"observed_at {observed_at} er ikke siste dag i måneden. "
            f"Biomassen er beholdning ved månedslutt, og et snapshot som "
            f"bærer en annen dato lyver om når den ble målt. Mente du "
            f"{siste_dag(d.year, d.month)}?"
        )
    return d.year, d.month


# ---------------------------------------------------------------- parsing

def _les_csv(tekst: str) -> list[dict[str, str]]:
    """CSV-tekst til rader. Kaster hvis en kolonne vi leser mangler.

    BOM-en fjernes HER og ikke bare ved nedlasting, av samme grunn som i
    `sjotemperatur`: `parse()` kalles like gjerne på tekst fra en
    re-parse av rå-arkivet eller fra en fil noen har lastet ned for hånd,
    og da har ingen `hent_alt()` vært innom. Overlever BOM-en, heter den
    første kolonnen '\\ufeffÅR' — og fordi det er kolonnen som bærer
    ÅRET, ville hver eneste måned blitt udaterbar mens de 22 andre
    kolonnene så helt friske ut.
    """
    leser = csv.DictReader(io.StringIO(tekst.lstrip("﻿")), delimiter=";")
    rader = list(leser)
    if not rader:
        return []

    mangler = [k for k in PAAKREVDE if k not in rader[0]]
    if mangler:
        raise Kolonnefeil(
            f"Fila mangler kolonnen(e) {', '.join(mangler)}. Fikk: "
            f"{', '.join(rader[0])}. Formatet er endret — rå-CSV-en er "
            f"arkivert, så dette er en re-parse og ikke tapt historikk."
        )
    return rader


def _po(rad: dict[str, str]) -> str:
    """`PO_KODE` til entity_id. Kaster på et format vi ikke kjenner.

    Koden var nullpadet (`01`) i 2024-kopien og er det ikke i dag (`1`).
    Normaliseringen gjør de to like, slik at en backfill mot et gammelt
    arkiv gir samme entity_id som en fersk henting — ellers ville PO 1
    vært to entiteter, og hver av dem sett ut som «ny» den dagen
    formatet snudde.

    En ukjent verdi KASTER framfor å bli sin egen entitet. Et stille
    fjortende produksjonsområde ville lagt seg ved siden av de tretten
    og telt med i nevneren uten at noen så det.
    """
    rå = (rad.get(KOL_PO) or "").strip()
    if rå == "(null)":
        return UTEN_PO
    if rå.isdigit():
        return str(int(rå))
    raise Kolonnefeil(
        f"Ukjent PO_KODE {rå!r}. Kjente former er et tall (med eller uten "
        f"innledende null) og '(null)'. Formatet er endret — rå-CSV-en er "
        f"arkivert, så dette er en re-parse."
    )


def _tall(tekst: str | None) -> float:
    """Celle til tall. En tom eller ulesbar celle KASTER.

    Motsatt av `sjotemperatur._tall()`, som gir None og lar raden bære et
    «ikke rapportert»-flagg. Her finnes ikke det valget: verdiene
    SUMMERES over art og utsettsår, og en celle som stilltiende ble null
    ville gitt et produksjonsområde som ser ut til å ha færre fisk enn det
    har. Målt over alle 5199 rader: null tomme celler, null desimalkomma,
    null negative verdier i kolonnene vi leser.
    """
    if tekst is None or not tekst.strip():
        raise Kolonnefeil(
            "Tom celle i en kolonne som summeres. Kilden har aldri hatt "
            "tomme celler i disse kolonnene — formatet er endret."
        )
    return float(tekst.strip())


def maaneder_i(rader: list[dict[str, str]]) -> list[tuple[int, int]]:
    """Månedene fila bærer, eldst først. Fila svarer selv."""
    return sorted({(int(r[KOL_AAR]), int(r[KOL_MND])) for r in rader})


def _formater(felt: str, verdi: float) -> str:
    """Sum til tekst. Heltall som heltall, kilo med tre desimaler.

    Formatet er en kontrakt mot historikken like mye som feltnavnet er
    det: skriver vi `750` den ene måneden og `750.0` den neste, leser
    diffen det som en endring.
    """
    if felt.endswith("_kg"):
        return f"{round(verdi, DESIMALER_KG):.{DESIMALER_KG}f}"
    return str(int(round(verdi)))


# ---------------------------------------------------------------- kilden

class Biomasse(Source):
    name = "biomasse"
    entity_type = "produksjonsomraade"

    # Sju for en månedlig kilde. Se modulens docstring — dette er ikke en
    # påstand om hvor ofte fila endrer seg, men om hvor ofte kjøringen
    # skal få lov til å spørre `finnes_allerede()` om måneden er skrevet.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.biomasse.aktiv", False))

    # ---- henting -------------------------------------------------------

    def url(self) -> str:
        return str(get("kilder.biomasse.url", STANDARD_URL))

    def hent_alt(self, client: httpx.Client | None = None) -> str:
        """Rå CSV-tekst for HELE serien. Det er den eneste formen som finnes.

        Returnerer TEKST og ikke ferdig tolkede rader, fordi kjernen
        arkiverer det `fetch()` returnerer og det som arkiveres skal være
        det tjenesten faktisk sendte. `core/raw.py` lagrer en str som
        `.txt.gz`.

        Og fordi det er hele fila som arkiveres, er hver kjøring en
        komplett kopi av serien slik Fiskeridirektoratet framstilte den
        den dagen. Det er den eneste stedet revisjonshistorikken finnes.

        `utvalg` settes HER og ikke i `fetch()`, fordi dette er det ene
        stedet begge veier inn i kilden går gjennom: månedsjobben via
        `fetch()`, historikken via `backfill.py`. Sto det i `fetch()`,
        fikk backfillede rader tomt utvalg — som leses «vet ikke», ikke
        «ingen filtrering». Samme felle som kostet sjotemperatur 389 206
        rader 24.08.2026.

        `{}` er riktig her og ikke et gjett: fila har ingen
        spørrestreng. Vi ber om alt som finnes, og får alt som finnes.
        At Fiskeridirektoratet selv har avgrenset den til matfisk av laks
        og regnbueørret i sjø er deres utvalg, ikke vårt.
        """
        self.utvalg = {}

        egen = client is None
        c = client or httpx.Client(timeout=60.0, follow_redirects=True)
        try:
            svar = _http.get(c, self.url(), hva="biomasse (hele serien)")
            # Eksplisitt dekoding, ikke svar.text: httpx gjetter tegnsett
            # fra headeren, og denne svarer `text/csv` uten charset. Da
            # ville «MÅNED_KODE» blitt «MÃ…NED_KODE» og kolonnesjekken
            # felt måneden.
            return svar.content.decode("utf-8-sig")
        finally:
            if egen:
                c.close()

    def _maaned_naa(self, kjoredato: str) -> tuple[int, int]:
        """Måneden kilden henter når vi kjører `kjoredato`. Ett sted, ikke to.

        Både `fetch()` og `gjelder_for()` må svare på det samme
        spørsmålet, og begge får datoen inn. Ingen klokkeoppslag her —
        se Source.fetch og F7.
        """
        maaneder = int(get("kilder.biomasse.maaneder_etterslep", 4))
        return maaned_med_etterslep(dt.date.fromisoformat(kjoredato), maaneder)

    def gjelder_for(self, kjoredato: str) -> str:
        """Siste dag i måneden vi henter — ikke dagen vi henter den."""
        return siste_dag(*self._maaned_naa(kjoredato))

    def fetch(self, kjoredato: str) -> str:
        aar, mnd = self._maaned_naa(kjoredato)
        rå = self.hent_alt()

        # Vurderingen får ALDRI felle fetch(). Kjernen arkiverer det
        # fetch() RETURNERER (runner.run_all: fetch, arkiver, parse), så
        # en exception her betyr at rå-CSV-en aldri når disk — og da er
        # en omdøpt kolonne oppdaget om et halvt år permanent datatap i
        # stedet for en re-parse. Feilen forsvinner ikke: parse() leser
        # den samme fila på nytt og kaster der, etter arkiveringen.
        try:
            self.advarsler = self._vurder(_les_csv(rå), aar, mnd)
        except (Kolonnefeil, ValueError) as e:
            self.advarsler = [
                f"biomasse {aar}-{mnd:02d}: klarte ikke vurdere fila. {e}"
            ]
        return rå

    def _vurder(self, rader: list[dict[str, str]],
                aar: int, mnd: int) -> list[str]:
        """Advarsler om fila. Ikke exceptions — snapshotet skal skrives.

        To prøver, og de spør om hver sin ting:

        * Ligger måneden vi skal skrive i fila? Nei her betyr at
          publiseringen er forsinket. Det felles i `parse()`, men
          advarselen sier det med tall og navn.
        * Er alle tretten produksjonsområdene til stede? Målt: de er det
          i hver eneste av 106 måneder. Er de plutselig ikke det, er
          enten fila avkortet eller et område lagt ned, og begge deler
          endrer nevneren i enhver senere aggregering.
        """
        varsler: list[str] = []
        if not rader:
            return ["biomasse: fila er tom."]

        finnes = maaneder_i(rader)
        if (aar, mnd) not in finnes:
            varsler.append(
                f"biomasse {aar}-{mnd:02d}: måneden ligger ikke i fila. "
                f"Den bærer {finnes[0][0]}-{finnes[0][1]:02d} til "
                f"{finnes[-1][0]}-{finnes[-1][1]:02d}. Publiseringen er "
                f"trolig forsinket — måneden skrives ikke."
            )
            return varsler

        i_maaneden = [r for r in rader
                      if (int(r[KOL_AAR]), int(r[KOL_MND])) == (aar, mnd)]
        koder = {_po(r) for r in i_maaneden} - {UTEN_PO}
        if len(koder) != ANTALL_PO:
            varsler.append(
                f"biomasse {aar}-{mnd:02d}: {len(koder)} produksjonsområder "
                f"i fila, ventet {ANTALL_PO}. Fikk "
                f"{sorted(koder, key=int)}. Nevneren i enhver aggregering "
                f"over PO er endret — undersøk før tallene brukes."
            )
        return varsler

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: str, observed_at: str) -> Iterable[Observation]:
        """Én måned ut av en fil som bærer alle.

        `observed_at` VELGER måneden, og fila BEKREFTER den. Det er ikke
        den samme rekkefølgen som i `lusetall` og `sjotemperatur`, der
        datoen utledes av dataene — men der bærer ett svar én uke, og her
        bærer ett svar 106 måneder. Da finnes det ikke noe i dataene å
        utlede datoen fra, og det eneste forsvaret mot at kjernen og fila
        er uenige er å sjekke at måneden faktisk er der.

        Kaster hvis den ikke er det. Alternativet — å skrive et tomt
        snapshot — ville sett vellykket ut, låst måneden mot senere
        henting via `finnes_allerede()`, og gjort hullet permanent i en
        append-only-serie.
        """
        aar, mnd = maaned_av(observed_at)
        rader = _les_csv(raw)
        if not rader:
            raise Maanedmangler(
                f"Fila er tom, så {aar}-{mnd:02d} kan ikke skrives.")

        i_maaneden = [r for r in rader
                      if (int(r[KOL_AAR]), int(r[KOL_MND])) == (aar, mnd)]
        if not i_maaneden:
            finnes = maaneder_i(rader)
            raise Maanedmangler(
                f"{aar}-{mnd:02d} ligger ikke i fila, som bærer "
                f"{finnes[0][0]}-{finnes[0][1]:02d} til "
                f"{finnes[-1][0]}-{finnes[-1][1]:02d}. Etterslepsregningen "
                f"vår og publiseringen er uenige — skriv ingenting framfor "
                f"å låse måneden med et tomt snapshot."
            )

        navn: dict[str, str] = {UTEN_PO: UTEN_PO_NAVN}
        sum_felt: dict[str, dict[str, float]] = {}
        per_art: dict[str, dict[str, float]] = {}

        for rad in i_maaneden:
            po = _po(rad)
            if po != UTEN_PO:
                navn.setdefault(po, (rad.get(KOL_PO_NAVN) or "").strip())
            felter = sum_felt.setdefault(po, {f: 0.0 for f in SUMFELT})
            for felt, kol in SUMFELT.items():
                felter[felt] += _tall(rad.get(kol))
            arter = per_art.setdefault(po, {ART_LAKS: 0.0, ART_REGNBUE: 0.0})
            art = (rad.get(KOL_ART) or "").strip()
            if art in arter:
                arter[art] += _tall(rad.get(SUMFELT["beholdning_antall"]))

        # Nevneren for `andel_av_beholdning`. Summert over ALLE fjorten
        # entitetene, `uten_po` inkludert — det er hele poenget med
        # feltet. Se modulens docstring.
        landet = sum(f["beholdning_antall"] for f in sum_felt.values())

        # Sortert, og `uten_po` sist. Rekkefølgen er stabil mellom
        # kjøringer med vilje: `to_frame()` beholder rekkefølgen, og en
        # parquet-fil som endrer seg uten at innholdet gjør det er en ny
        # fil i git hver måned.
        for po in sorted(sum_felt, key=lambda p: (p == UTEN_PO,
                                                  int(p) if p.isdigit() else 0)):
            felles = dict(entity_id=po, entity_type=self.entity_type,
                          entity_name=navn.get(po, ""), source=self.name,
                          observed_at=observed_at)

            for felt in SUMFELT:
                yield Observation(field=felt,
                                  value=_formater(felt, sum_felt[po][felt]),
                                  **felles)

            # Null og ikke ingenting når arten mangler. Se docstringen om
            # de 250 eksplisitte nullene i kilden.
            for felt, art in ((FELT_LAKS, ART_LAKS),
                              (FELT_REGNBUE, ART_REGNBUE)):
                yield Observation(field=felt,
                                  value=str(int(round(per_art[po][art]))),
                                  **felles)

            andel = (sum_felt[po]["beholdning_antall"] / landet) if landet else 0.0
            yield Observation(
                field=FELT_ANDEL,
                value=f"{round(andel, DESIMALER_ANDEL):.{DESIMALER_ANDEL}f}",
                **felles)
