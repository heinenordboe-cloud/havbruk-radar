"""Siste port før noe forlater maskinen: gransker GENERERT output.

    python publiseringsvakt.py <mappe>          # granskning, exit 1 ved funn
    python publiseringsvakt.py <mappe> --rapport

`core/persondata.py` beskytter to steder: `fetch()` holder personformene
ute av rå-arkivet, og `snapshot._les()` holder dem ute av alt som leses.
Begge virker på DATAENE.

Ingen av dem beskytter en GENERATOR. En funksjon som leser et snapshot og
skriver HTML kan sette sammen felter på en måte ingen av de to filtrene
ser: en tabell over «største eiere», en tooltip med orgnummer, en
CSV-eksport ved siden av sida. Filteret har gjort jobben sin, og
persondataene er der likevel — satt sammen av biter som hver for seg var
greie.

Derfor granskes utputtet, ikke inputtet. Denne vakten leser ferdige filer
og spør: står det noe her som ikke kan gjøres rede for?

## Prøven er en HVITELISTE, ikke et mønsterforbud

Oppgaven ba om «ingen fil skal inneholde `\\b\\d{9}\\b`». Den prøven er
MÅLT ugjennomførbar 15.09.2026:

    enhetsregisteret   1807 entity_id som ER ni-sifrede orgnumre
    eierskap           2953 eier_orgnr + 2939 tildelt_orgnr
    eierskap_historikk   91 mottaker_orgnr
    enhetsregisteret     32 aksjekapital og 26 antall_aksjer som
                            tilfeldigvis har ni siffer og ikke er
                            orgnumre i det hele tatt

En side som viser ett eneste selskap ville feilt. Og et forbud som må
slås av for å publisere, blir slått av.

Prøven er derfor snudd: **hvert ni-sifret tall i utputtet skal finnes
igjen blant orgnumrene i de FILTRERTE snapshotene.** Da er det ikke
mønsteret som avgjør, men proveniensen — og et orgnummer som har kommet
inn en annen vei enn gjennom `snapshot._les()` har ingen steder å gjemme
seg. Det er samme inversjon som gjør `test_ingen_leser_snapshots_utenom_les`
mulig: én dør, og alt som ikke kom gjennom den er et funn.

Den fanger nøyaktig det ni-siffer-prøven fra 16.08 ikke kunne fange. Den
prøven sa «alle entity_id er ni siffer, altså selskapsdata» — syntaktisk
der spørsmålet var semantisk, og et ENK har ni siffer akkurat som et AS.
Denne spør om noe annet: kom dette tallet fra en kilde vi har filtrert?

## Tre prøver, og hva hver av dem IKKE dekker

  1. `ukjent_orgnr`   ni-sifret tall som ikke finnes i de filtrerte
                      snapshotene. Dekker ikke et orgnummer som er
                      filtrert bort OG som tilfeldigvis også står i en
                      annen kildes data.
  2. `personform`     ordet ENK (eller en annen kode i PERSONFORMER) i
                      en sammenheng som ser ut som en organisasjonsform.
                      Dekker ikke et snapshot som bærer persondataene
                      uten etiketten — derfor fjerner
                      `fjern_personformer()` HELE entiteten.
  3. `ukjent_navn`    en navnestreng i utputtet som ikke finnes igjen i
                      navnefeltene i de filtrerte snapshotene. Dekker
                      ikke et navn som ER i snapshotet og likevel er en
                      person — se `personformet_navn()` og
                      docs/MALING-PERSONEKSPONERING.md.

Ingen av de tre later som om de er uttømmende. Det er med vilje: en vakt
som lover mer enn den kan holde, er verre enn ingen vakt, fordi den blir
trodd.

## Merkingen prøve 2 og 3 leser: FELTVOKABULARET, ikke en attributtliste

En prøve på HTML kan bare se det generatoren MERKER. Fram til 18.09.2026
var merkingen en liste attributtnavn — `data-navn`, `class="navn|eier"`
— og den holdt for de tabellene der kolonnen er kjent på forhånd: et
eiernavn står alltid i eierkolonnen.

Den duger ikke for en FELT-VERDI-tabell. I endringstabellen og i
registertabellen bærer samme `<td>` `siste_rapport` i én rad og
`eier_navn` i neste; en statisk klasse ville enten merket alt som navn
eller ingenting. Merkingen må da utledes av RADEN, og feltnavnet er det
generatoren allerede har.

`data-felt="<feltnavn>"` er derfor konvensjonen, og `felt_verdier()`
leser den mot `NAVNEFELT`, `persondata.FORM_FELT` og
`persondata.SEKTOR_FELT` — ikke mot en liste attributtnavn. Det er
SAMME regel `gransk_csv` har hatt siden 16.09: kolonneoverskriften er
merkingen, og den kommer fra generatorens eget feltvokabular. To
formater, én regel.

Hva den ikke dekker: en celle uten `data-felt`. Den er usynlig for prøve
3 med mindre den også har en av de gamle merkingene — og en umerket
celle er nøyaktig hullet som ble målt 18.09.2026, da 24 navneverdier fra
changeloggen sto i endringstabellen uten at `ukjent_navn` kunne se dem.
Se docs/beslutninger/2026-09-18-changeloggens-persondata-ligger-stille.md.

## Og ett hull som er MÅLT og står åpent

`ukjent_orgnr` leter i to ledd: først finner den kandidattall i teksten,
så spør den om de er gjort rede for. Andre ledd er sterkt — det er
proveniens og ikke mønster. Første ledd er en TOKENISERING, og den er
format-avhengig.

Målt 17.09.2026, samme nisifrede tall i ti innpakninger:

    <td>999888777</td>            finnes
    {"orgnr": "999888777"}        finnes
    {"orgnr": 999888777}          finnes
    orgnr;999888777               finnes
    | 999888777 | (markdown)      finnes
    999888777,Kari  (rå CSV)      USYNLIG — kommaet er avgrenseren
    [999888777, 123]  (JSON)      USYNLIG — samme komma

CSV-en er lukket: `.csv` og `.tsv` parses nå per kolonne, og
avgrenseren er borte før prøven stilles. **JSON er ikke lukket.** Et
nisifret tall i en JSON-LISTE er usynlig for vakten i dag.

Det biter ingen generator vi har — `.json` skrives ikke, og JSON-LD-en i
`nettsted.py` bærer ingen organisasjonsnumre — men det er en påstand om
i dag og ikke om i morgen. Vurderingen av hvorfor prøven har feilet tre
ganger, og hva som eventuelt bør gjøres med den, står i
`docs/VURDERING-NI-SIFFER-PROVEN.md`.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polars as pl

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import kodeproveniens, persondata, snapshot       # noqa: E402
from core.paths import KVITTERING_DIR, RAW_DIR              # noqa: E402

# Ni siffer, men som et HELT TALL og ikke som en sifferstreng inni et
# lengre tall. Oppgaven ba om `\b\d{9}\b`; den varianten er MÅLT for
# grov mot ekte utputt 15.09.2026.
#
# `oversikt.html` inneholder «96697320.109» og «123456789.289» —
# biomasse i kilo. `\b` står mellom siffer og punktum, så `\d{9}\b`
# traff heltallsdelen av et desimaltall og meldte et orgnummer som ikke
# fantes. Ett funn i den eneste genererte fila vi har, og det var falskt.
#
# En vakt som fyrer på hver biomasseverdi blir slått av. Derfor matches
# tallet som TOKEN: ingen siffer, punktum eller komma på noen av sidene.
#
# HULLET det åpner, sagt rett ut: et orgnummer formatert som desimaltall
# — «912345678.0» ut av en pandas-runde — blir ikke sett. Det er en
# formateringsfeil ingen generator her gjør i dag, og prisen for at
# vakten kan stå på. Se `test_orgnummer_som_desimaltall_er_et_kjent_hull`.
NI_SIFFER = re.compile(r"(?<![\d.,])\d{9}(?![\d.,])")

# Filtypene som faktisk går ut. En `.parquet` ved siden av sida er like
# publisert som HTML-en, og en `.csv` er verre: den er laget for å lastes
# ned. Lista er en hviteliste over hva vakten VET hvordan den skal lese
# som tekst — alt annet rapporteres som `ugranska` framfor å bli antatt
# trygt.
TEKSTTYPER = {".html", ".htm", ".css", ".js", ".json", ".csv", ".tsv",
              ".md", ".txt", ".svg", ".xml"}

# Tekstfiler UTEN endelse, som vi skriver selv.
#
# `_headers` og `_redirects` er Cloudflare Pages' eget format — se
# `nettsted.skriv_vertsfiler()`. De er like publiserte som alt annet,
# og de bærer URL-er. Porten meldte dem som `ugranska` første gang de
# ble skrevet, og det er slik den skal virke: en fil den ikke kan lese,
# sier den at den ikke har lest.
#
# En LUKKET liste og ikke «alt uten endelse er tekst»: en binærfil uten
# endelse skal fortsatt falle til `ugranska`.
TEKSTFILER = {"_headers", "_redirects"}

# BINÆRFILENE VI SENDER UT MED VILJE, med sha256 pinnet.
#
# Fra 21.09.2026 hoster nettstedet én font, og den er ikke tekst. Tre
# måter å håndtere det på, og bare den tredje duger:
#
#   1. Legge `.woff2` i TEKSTTYPER. Løgn: vakten kan ikke lese woff2 som
#      tekst, og ville rapportert grønt om en granskning som ikke skjedde.
#   2. Hoppe over ukjente binærfiler. Da er `ugranska` død som prøve, og
#      en `.parquet` som lekker et personregister går ut i stillhet.
#   3. Pinne den ENE fila vi faktisk har sett i, på innhold.
#
# Nøkkelen er sha256 og ikke filnavnet, og det er hele poenget: et navn
# kan gjenbrukes av en annen fil. Endres fonten — nytt subsett, ny
# versjon, en annen font med samme navn — treffer ikke summen lenger, og
# porten faller til `ugranska` slik den skal. Kvitteringen gjelder
# innholdet som ble inspisert, ikke plassen det lå på.
#
# Det er samme form som kvitteringene i `data/kvitteringer/`: en påstand
# om en KONKRET verdi, ikke en bryter som slår av et helt slag.
#
# Hva som er inspisert i fonten, og hvordan, står i
# docs/design/NEWSREADER.md. Kort: `name`-tabellen er lest ut i sin
# helhet, den inneholder opphavsrett og stilnavn, og ingenting fra våre
# kilder.
BINAERFILER = {
    "14209ccee1fac927285fbf69eab415c27815d6b90c249ed07b807cf37f75faa9":
        "newsreader.woff2 — Newsreader, OFL 1.1. name-tabellen inspisert "
        "22.09.2026, se docs/design/NEWSREADER.md",
    # De to Plex-fontene kom 22.09.2026 med designoverleveringen.
    # Brødteksten er ikke lenger systemets sans, og tallkolonnene er
    # ikke lenger systemets mono. Begge name-tabellene er lest ut i sin
    # helhet og gjengitt i docs/design/IBM-PLEX.md.
    "0e98868216b2ed175098bedc3ece2273382dc9b1f23bdd911bb12ebedfaa6344":
        "ibmplexsans.woff2 — IBM Plex Sans, OFL 1.1. name-tabellen "
        "inspisert 22.09.2026, se docs/design/IBM-PLEX.md",
    "6e32afc77a2d702137db7bd95f8dd435db6861ae1ae8a56b001ac8a8e851edca":
        "ibmplexmono.woff2 — IBM Plex Mono, OFL 1.1. name-tabellen "
        "inspisert 22.09.2026, se docs/design/IBM-PLEX.md",
    # Ikonene. Rastret av `maler/favicon.svg`, som vakten leser som
    # tekst (`.svg` står i TEKSTTYPER) og granskes som alt annet. PNG-ene
    # kan derfor ikke inneholde noe SVG-en ikke inneholder — men de er
    # binære, og en binærfil vakten ikke har sett i, skal ikke gå ut.
    "36477d774220c1f8880dbb73a9eb1be5f70d69eff50d0e070bc34ad702a5293e":
        "favicon-32.png — «K» i Newsreader 600 på havblått, rastret av "
        "maler/favicon.svg 21.09.2026",
    "20b6fc8bf832023ffd1d09df2220fb66eaa6189f34e3ede5e5f6154e66be3365":
        "apple-touch-icon.png — samme ikon, 180x180",
    # HEROFOTOGRAFIET, tre bredder av det samme motivet. Segmentene er
    # lest ut én gang: JFIF (APP0) og en sRGB-ICC-profil (APP2), og
    # INGEN APP1 — altså ingen EXIF, ingen GPS, intet kameraserienummer
    # og ingen navn. Se docs/design/HEROFOTO.md.
    #
    # At de tre er skalerte utgaver av det samme motivet gjør dem ikke
    # til én fil: sha256 pinner INNHOLD, og tre filer er tre innhold.
    #
    # De gikk ut umerket ved første bygg 22.09.2026, og porten stoppet
    # publiseringen med «ugranska — .jpg». Det er slik den skal virke.
    "4aececeb4f01f8b9cfc445d3dc687c9f6fd8415c788615e5ffc4af9035b0ccbd":
        "bilde/hero-800.jpg — herofoto, Unsplash-lisens. Segmentene "
        "inspisert 22.09.2026: ingen EXIF, se docs/design/HEROFOTO.md",
    "3c8c0e7f92dbcc8e63791f96886f7faeef079b60834f3ad716c8433f7a7ac1e8":
        "bilde/hero-1600.jpg — samme motiv, 1600 px bred",
    "1233af0d2cb4ced13f084ca41aaae198d6cea6a172585ddb1af085e6a244c781":
        "bilde/hero-2400.jpg — samme motiv, 2400 px bred",
}

# BINÆRFILER ET VERKTØY LEGGER IGJEN, ikke filer vi sender fra `maler/`.
#
# Skillet er ikke kosmetisk: `test_hver_pinnet_sum_finnes_som_fil_i_maler`
# er en driftvakt som feller en pinning uten fil — en kvittering for noe
# som ikke finnes er støy som skjuler at den ekte fila er ukvittert. Den
# prøven kan ikke se disse, fordi de først oppstår når bygget kjører.
#
# Proveniensen er derfor VERKTØYET, og den står her.
BINAERFILER_VERKTOY = {
    # SØKEMOTORENS WEBASSEMBLY. To filer, begge lagt der av
    # pagefind-binæren og ingen av dem bygget av oss.
    #
    # INNHOLDET ER SØKEMOTOREN, IKKE DATAENE VÅRE. Det er
    # `.pf_fragment`- og `.pf_index`-filene som bærer sidenes tekst;
    # disse to er koden som leser dem. Utpakket (gzip, `pagefind`-hale)
    # er de 116 631 og 112 482 byte Rust-kompilert wasm.
    #
    # Proveniensen er binæren de kom fra:
    #
    #   pagefind-v1.4.0-aarch64-apple-darwin.tar.gz
    #   sha256 647fa1da25fefeb24348ed09cccfcbcdd1dcab75c83e146c9f50336a78efb290
    #   github.com/CloudCannon/pagefind, MIT, hentet 22.09.2026
    #
    # En annen versjon av Pagefind gir andre summer, og porten faller
    # til `ugranska` slik den skal. Se docs/design/PAGEFIND.md.
    "2feab03d140476c959ca2b69830b84c8292403085d8280a381b140632e8a7274":
        "pagefind/wasm.nb.pagefind — søkemotoren, norsk stemming. "
        "Pagefind 1.4.0, se docs/design/PAGEFIND.md",
    "c9f966c91edb839e017a11c745e63b0c828b55cd02abcd16a8a4fd5ff7c28172":
        "pagefind/wasm.unknown.pagefind — samme motor, uten stemming",
}

# Oppslaget porten gjør. To tabeller, ett spørsmål: «har vi sett i
# denne fila?»
BINAERFILER_ALLE = {**BINAERFILER, **BINAERFILER_VERKTOY}

# Filtypene der KOLONNEOVERSKRIFTEN er merkingen, og der prøvene derfor
# stilles per kolonne framfor på teksten. Se `gransk_csv`.
#
# Avgrenseren står SAMMEN med typen og gjettes ikke. Første utkast hadde
# `{".csv", ".tsv"}` som et sett og lot `csv.reader` bruke standarden —
# altså komma — for begge. Målt 17.09.2026 på en konstruert TSV: hele
# overskriftsrada ble ÉN kolonne som het `navn\tkommune`, som ikke står i
# NAVNEFELT, og et navn i navnekolonnen var usynlig.
#
# Formen på feilen er kjent: vakten sa at den dekket `.tsv`, og gjorde det
# ikke. En vakt som lover mer enn den holder, er verre enn ingen vakt.
KOLONNETYPER = {".csv": ",", ".tsv": "\t"}

# FILTYPENE SOM ER PAKKET TEKST. Pagefinds tekstutdrag: gzip rundt
# `pagefind_dcd` + JSON. De pakkes ut og granskes som alt annet — se
# `_pakket_tekst()` for hvorfor de verken kan pinnes på sha256 eller
# legges i `TEKSTTYPER`.
PAKKEDE_TYPER = {".pf_fragment"}

# FILTYPENE SOM ER AVLEDET AV NOE VAKTEN HAR LEST, og som derfor står
# som gjort rede for uten å bli gransket hver for seg.
#
# `.pf_index` og `.pf_meta` er Pagefinds ordtabeller: CBOR, ikke tekst.
# Tre veier ble prøvd, og bare den tredje duger:
#
#   1. La dem stå som `ugranska`. Da faller porten hver uke på 2 558
#      filer, og en port som alltid faller blir slått av.
#   2. Pakke dem ut og granske dem som tekst. MÅLT 22.09.2026:
#      **2 418 funn, alle falske.** CBOR-rammen limer sammen
#      nabotokener, og «20260126» + en lengdebyte «2» blir «202601262»
#      — ni siffer på rad som `NI_SIFFER` leser som et
#      organisasjonsnummer. Ingen av dem er et tall; alle 2 418 er
#      rammestøy. En vakt som feiler feil blir slått av.
#   3. Erklære dem AVLEDET av tekstutdragene, som ER gransket.
#
# DERIVASJONSARGUMENTET, sagt rett ut: Pagefind trekker ut teksten fra
# en side én gang og skriver den til BÅDE `.pf_fragment` og
# ordtabellene. Er utdragene rene, er tabellene bygget av rene ord.
#
# Argumentet hviler på at det finnes et utdrag per indeksert side.
# Holder ikke det, er ordtabellen bygget av noe vakten ikke har sett.
# `test_hvert_indeksert_sideutdrag_granskes` er prøven som håndhever
# det, og den er grunnen til at dette ikke bare er en påstand.
#
# Samme form som ikonene: PNG-ene er rastret av `favicon.svg`, som
# vakten leser som tekst, og kan derfor ikke inneholde noe SVG-en ikke
# inneholder.
#
# `.pf_filter` kom 25.09.2026, med `data-pagefind-filter` på hver side.
# Den er den SAMME konstruksjonen: en CBOR-tabell over hvilke sider som
# har hvilken filterverdi, bygget av den samme utlesningen som skriver
# `.pf_fragment`. Verdiene den inneholder er sidetypene våre —
# «Lokalitet», «Selskap», «Liste» — og de står i utdragene vakten
# leser. Derivasjonsargumentet og prøven over dekker den uten endring.
AVLEDEDE_TYPER = {".pf_index", ".pf_meta", ".pf_filter"}

# Felter der en verdi er et NAVN. Brukes til å bygge hvitelista.
NAVNEFELT = ("navn", "entity_name", "eier_navn", "tildelt_navn",
             "mottaker_navn", "lokalitet_navn", "prodomraade_navn")

# Felter der en verdi er et ORGNUMMER.
ORGNRFELT = ("eier_orgnr", "tildelt_orgnr", "mottaker_orgnr",
             "openLegalEntityNr", "legalEntityNrId")


def navnenoekkel(navn: str) -> str:
    """Navnet i det ALFABETET hvitelista sammenlignes i.

    ## Hvorfor dette finnes, og hvorfor det ikke er en oppmykning

    Hvitelista er navnene slik de står i snapshotene, og de står i
    VERSALER: Akvakulturregisteret skriver «OTERNESET». Fra 22.09.2026
    står lokalitetsnavnet i tittelform i H1 — «Oterneset» — fordi
    versaler i en 88-piksels overskrift er en egenskap ved registerets
    inntastingsfelt og ikke en opplysning om navnet. Originalen står
    fortsatt i registerfelt-tabellen på samme side.

    Sammenlignet ordrett ville hver eneste av de 1 782 lokalitets-
    sidene meldt sitt eget lokalitetsnavn som `ukjent_navn`. En vakt
    som feiler 1 782 ganger på noe som er gjort rede for, blir slått av
    — det er nøyaktig begrunnelsen `_celleverdi()` har for å avkode
    HTML-entiteter: «MÅLT 18.09.2026 meldte `ukjent_navn` 54 funn på
    ett eneste navn (…) Alle 54 var falske, og en vakt som feiler feil
    blir slått av.»

    Store og små bokstaver er den samme slags forskjell som `&amp;` mot
    `&`: to skrivemåter av den samme strengen. Prøven spør «er dette
    navnet gjort rede for i dataene», og det spørsmålet har samme svar
    uansett hvilken kasse det står i.

    HULLET DETTE IKKE ÅPNER: et navn som ikke finnes i dataene, finnes
    ikke i noen kasse heller. `casefold()` kan bare få to strenger til å
    møtes; det kan ikke føre en ny streng inn i hvitelista. Se
    `test_kassen_gjor_ikke_et_ukjent_navn_kjent`.
    """
    return html.unescape(navn).strip().casefold()


def _noekler(navn_ok: Iterable[str]) -> set[str]:
    """Hvitelista oversatt til nøkkelalfabetet, én gang per fil.

    NORMALISERINGEN SKJER HER OG IKKE I `hviteliste()`, og det er et
    valg med en målt pris: 10 476 navn omskrevet 2 279 ganger koster
    2,1 sekunder av en granskning som tar ~30.

    Prisen er verdt det fordi grensa da ligger i FUNKSJONEN og ikke i
    kallet. `gransk_tekst()` og `gransk_csv()` kan kalles med hvilken
    som helst mengde navn — en prøve, et skript, en framtidig kaller —
    og svaret er det samme. Lå normaliseringen i `hviteliste()`, ville
    en kaller som bygget sitt eget sett fått en vakt som stille
    sammenlignet to alfabeter, og det er nøyaktig feilen `navnenoekkel`
    finnes for.
    """
    return {navnenoekkel(n) for n in navn_ok}


def _er_ni_siffer(s: str) -> bool:
    """Nøyaktig ni siffer og ingenting annet.

    Egen funksjon fordi `NI_SIFFER` har negative lookarounds og derfor
    ikke kan brukes med `fullmatch()` på en verdi som ER hele strengen.
    """
    return len(s) == 9 and s.isdigit()


@dataclass(frozen=True)
class Funn:
    """Ett treff. `utdrag` er forkortet med vilje — en rapport om
    persondata skal ikke selv bli et sted persondata står."""

    fil: str
    slag: str        # ukjent_orgnr | personform | ukjent_navn | ugranska
                     # | ukjent_partisjon | feilerklaert_partisjon
                     # | uferdig | raatt_tidsstempel | reposti
                     # | uten_kontakt
    utdrag: str
    antall: int = 1

    # Kvitteringen som dekker funnet, eller tom streng. Et kvittert funn
    # STÅR I RAPPORTEN og teller ikke i exit-koden — det er forskjellen
    # på en påstand om at funnet er forstått og en bryter som gjør
    # vakten stille. Se `kvitteringer()`.
    kvittert: str = ""

    # Nøkkelen en kvittering slås opp på: `(felt, signatur)` som streng,
    # eller tom for et funn som ikke kan kvitteres. Den står HER og
    # utledes ikke av `utdrag` — rapporten er en tekst for mennesker, og
    # en teller som parset den ville vært en teller som måler
    # formateringen. Første utgave gjorde nettopp det og meldte «2
    # kvitteringer traff ingen funn» mens alle tre traff.
    noekkel: str = ""

    def __str__(self) -> str:
        hale = f"  [KVITTERT {self.kvittert}]" if self.kvittert else ""
        return (f"{self.fil}: {self.slag} — {self.utdrag} "
                f"(x{self.antall}){hale}")


# --------------------------------------------------- kvitteringene


def _signatur(verdi: str) -> str:
    """Nøkkelen en kvittering slår opp på. Ikke verdien selv.

    Samme hash som `_anonymiser()` bruker, men lengre: 16 tegn framfor 6.
    Seks er nok til å kjenne igjen et navn i en rapport man leser ved
    siden av fila; en NØKKEL skal ikke kunne kollidere med et annet navn
    i det hele tatt.
    """
    return hashlib.sha256(verdi.encode("utf-8")).hexdigest()[:16]


def kvitteringer() -> dict[tuple[str, str], dict]:
    """{(felt, navnesignatur): kvitteringen} — hva som er FORSTÅTT.

    ## En kvittering er en påstand, ikke en bryter

    Samme form som `health.godta_volum()`: kvitteringen er ikke et flagg
    som slår av vakten, men en verdi skrevet til en fil som committes.
    Git-loggen sier når, fila sier hvorfor og av hvem, og funnet BLIR
    STÅENDE I RAPPORTEN — `--rapport` teller kvitterte funn hver kjøring,
    slik at «porten er grønn» aldri kan bety «ingen funn».

    ## Den kvitterer ut ET FUNN, aldri et SLAG

    Nøkkelen er `(felt, signaturen til den enkelte verdien)`. Det er et
    bevisst valg framfor `slag = "personform"`:

        kvittert: personform            hele prøven er død. Et femte navn
                                        passerer i stillhet.
        kvittert: (tildelt_navn, #ab..) nøyaktig denne verdien i nøyaktig
                                        dette feltet. Et femte navn har
                                        ingen kvittering og feller porten.

    Det er samme skille som `godta_felt()` mot `godta_volum()`: to
    kvitteringer for to spørsmål, framfor én som svelger begge.

    ## Formatet

    `data/kvitteringer/<dato>.json`, append-only som `data/feltnormal/`:

        {"dato": "2026-09-19",
         "kvittert_av": "Heine Nordboe",
         "begrunnelse": "...hele resonnementet, ikke en stikktittel...",
         "saker": [{"felt": "tildelt_navn",
                    "navn": "<verdien ordrett>",
                    "navn_signatur": "<sha256[:16] av navnet>",
                    "orgnr": "<organisasjonsnummer>",
                    "entiteter": ["H-AV-0006"],
                    "status": "kvittert"}]}

    `navn` står ordrett i fila, og det er grunnen til at fila ligger i
    DATAREPOET — se `core.paths.KVITTERING_DIR`. Porten trenger den ikke:
    den slår opp på signaturen, som den regner ut av det den finner i
    utputtet. Navnet er der for mennesket som skal etterprøve
    kvitteringen.

    Signaturen KONTROLLERES mot navnet. En kvittering som oppgir et navn
    og en signatur som ikke hører sammen, er en kvittering for noe annet
    enn den ser ut som — og den ville kvittert ut et funn ingen har lest.

    `status = "trukket"` trekker en tidligere kvittering. Filene leses i
    datorekkefølge, og den siste som nevner en sak avgjør. Å slette en
    fil er ikke veien: de er append-only, og en trukket kvittering skal
    kunne leses i ettertid.
    """
    if not KVITTERING_DIR.exists():
        return {}

    ut: dict[tuple[str, str], dict] = {}
    for sti in sorted(KVITTERING_DIR.glob("*.json"),
                      key=lambda p: _dato_og_nummer(p.stem)):
        data = json.loads(sti.read_text(encoding="utf-8"))
        dato = str(data.get("dato") or sti.stem)
        av = str(data.get("kvittert_av") or "").strip()
        grunn = str(data.get("begrunnelse") or "").strip()
        if not av or not grunn:
            raise ValueError(
                f"{sti.name}: en kvittering uten `kvittert_av` og "
                f"`begrunnelse` er et flagg, ikke en kvittering.")

        for sak in data.get("saker") or []:
            felt = str(sak.get("felt") or "").strip()
            sig = str(sak.get("navn_signatur") or "").strip()
            if not felt or not sig:
                raise ValueError(
                    f"{sti.name}: en sak mangler `felt` eller "
                    f"`navn_signatur`, og kan ikke slås opp.")
            navn = sak.get("navn")
            if navn and _signatur(str(navn)) != sig:
                raise ValueError(
                    f"{sti.name}: `navn_signatur` {sig} hører ikke til "
                    f"navnet i samme sak. Kvitteringen gjelder da noe annet "
                    f"enn den ser ut som.")
            nøkkel = (felt, sig)
            if str(sak.get("status") or "kvittert") == "trukket":
                ut.pop(nøkkel, None)
                continue
            ut[nøkkel] = {"dato": dato, "kvittert_av": av,
                          "begrunnelse": grunn, "fil": sti.name,
                          "orgnr": sak.get("orgnr"),
                          "entiteter": sak.get("entiteter") or []}
    return ut


def _dato_og_nummer(stem: str) -> tuple[str, int]:
    """`2026-09-19.2` -> `("2026-09-19", 2)`. Som snapshot-løpenumrene."""
    dato, _, n = stem.partition(".")
    return dato, int(n) if n.isdigit() else 1


# --------------------------------------------------- hvitelista
#
# HVILKE DATOER som leses er en egenskap ved KILDEN, ikke ved vakten:
#
#   "verden"    ALLE datoer. Snapshotene er ulike tidsrom som gjelder
#               samtidig, og en visning av serien er en visning av dem
#               alle — lokalitetssiden viser 764 uker lusetall og 21
#               årganger overføringer.
#   "henting"   NYESTE dato. Et navn fra forrige ukes uttrekk er et navn
#               som ikke gjelder lenger, og en visning skal ikke hente
#               fra det.
#   ""          NYESTE, altså den strengeste lesningen — og et funn. Se
#               `grunnlagsfunn()`.
#
# Erklæringen ligger på kilden (`Source.partisjonering`), og
# klassifiseringen er målt i docs/MALING-PARTISJONERING.md. Fram til
# 19.09.2026 leste denne fila NYESTE for alle, og det ga **961 av 1030
# portfunn**: generatoren leser alle 21 årgangene av
# `eierskap_historikk`, hvitelista bare 2026-fila.
#
# Målt kostnad for regelen: 7,17-7,54 s mot 0,07-0,08 s for nyeste alene,
# og lusetall er 5 av de 7 sekundene. Det den kjøper er 13 navn og 5
# orgnumre som IKKE hvitelistes — de eldre partisjonene til
# henting-kildene. Lite, men det er innstrammingen `hviteliste()` finnes
# for å ha.


def _erklaeringene() -> tuple[dict[str, str], dict]:
    """({kildenavn: partisjonering}, {kildenavn: kilden}).

    Bygget av `registry.discover()` ved hvert kall og ikke bufret, som
    `nettsted.kildevilkaar()`: en port som leser en gammel erklæring er
    en port som svarer på gårsdagens kode.
    """
    from core import registry
    from core.contract import kilder_per_navn, partisjonering_per_kilde

    kilder = registry.discover()
    return partisjonering_per_kilde(kilder), kilder_per_navn(kilder)


def _datoene(kilde: str, partisjonering: str) -> list[str]:
    """Datoene hvitelista skal lese for kilden. Regelen, ett sted."""
    if partisjonering == "verden":
        return snapshot.datoer(kilde)
    siste = snapshot.siste_dato(kilde)
    return [siste] if siste else []


def _snapshotrammer() -> Iterable[pl.DataFrame]:
    """Rammene hvitelista bygges av, LEST GJENNOM `snapshot._les()`.

    Veien er ikke likegyldig. `_les()` er den ene døra, og den kjører
    `persondata.fjern_personformer()`. Bygges hvitelista med
    `pl.read_parquet()` i stedet, inneholder den nøyaktig de orgnumrene
    og navnene vakten finnes for å stoppe — og vakten ville godkjent dem.

    Døra er likevel ikke nok for enhver kilde, og det er MÅLT:
    `eierskap_historikk` har 36 360 rader over 21 årganger og 0 med
    `organisasjonsform` eller `institusjonell_sektorkode` — døra fjerner
    0. Derfor spørres KILDEN i tillegg (`fjern_egne_personer()`), ellers
    ville regelen over hvitelistet de fire personformede mottakerne i
    stedet for å filtrere dem. Stillhet kjøpt for sikkerhet.
    """
    if not RAW_DIR.exists():
        return
    partisjonering, kilder = _erklaeringene()
    for kdir in sorted(RAW_DIR.iterdir()):
        if not kdir.is_dir():
            continue
        for ramme in _rammene_for(kdir.name, partisjonering, kilder):
            yield ramme


def _rammene_for(kilde: str, partisjonering: dict[str, str],
                 kilder: dict) -> Iterable[pl.DataFrame]:
    """Rammene for én kilde, etter regelen og med kildens eget tillegg."""
    for dato in _datoene(kilde, partisjonering.get(kilde, "")):
        for _versjon, ramme in snapshot.versjoner(kilde, dato):
            eier = kilder.get(kilde)
            if eier is None:
                yield ramme
                continue
            etter = eier.fjern_egne_personer(ramme)
            if etter.height > ramme.height:
                # Hooken er et TILLEGG til døra og kan bare fjerne. En
                # kilde som leverer flere rader tilbake har ikke
                # filtrert, og en hviteliste bygget av det er større enn
                # dataene den skal gjøre rede for.
                raise ValueError(
                    f"{kilde}.fjern_egne_personer() ga {etter.height} rader "
                    f"tilbake av {ramme.height} for {dato}. Hooken skal "
                    f"filtrere, ikke legge til — se Source.fjern_egne_personer.")
            yield etter


def _gamle_snapshotrammer() -> Iterable[pl.DataFrame]:
    """Nyeste snapshot per kilde, uten regelen. Bare for målinger.

    Beholdt fordi tallene i docs/MALING-PARTISJONERING.md er målt mot
    den, og et tall uten en kjørbar kilde er et tall ingen kan etterprøve.
    """
    if not RAW_DIR.exists():
        return
    for kdir in sorted(RAW_DIR.iterdir()):
        if not kdir.is_dir():
            continue
        dato = snapshot.siste_dato(kdir.name)
        if not dato:
            continue
        for _versjon, ramme in snapshot.versjoner(kdir.name, dato):
            yield ramme


def hviteliste() -> tuple[set[str], set[str]]:
    """(orgnumre, navn) som ER gjort rede for. Begge lest gjennom døra.

    Hvilke datoer som leses er KILDENS erklæring og ikke vaktens valg —
    alle for «verden», nyeste for «henting». Se kommentaren over
    `_snapshotrammer()`.

    Innstrammingen som sto her fram til 19.09.2026 — nyeste dato for ALLE
    kilder — er ikke gitt opp, den er gjort presis. Den var riktig om
    `enhetsregisteret`, der forrige ukes navn ikke gjelder lenger, og feil
    om `eierskap_historikk`, der 2009-årgangen er et annet tidsrom og ikke
    en utdatert versjon av 2026. Målt: den beholder 13 navn og 5 orgnumre
    utenfor hvitelista som «alle datoer for alt» ville sluppet inn.
    """
    orgnr: set[str] = set()
    navn: set[str] = set()
    for ramme in _snapshotrammer():
        kolonner = set(ramme.columns)
        if {"entity_id", "field", "value"} - kolonner:
            continue
        orgnr |= {e for e in ramme["entity_id"].to_list()
                  if _er_ni_siffer(str(e))}
        for felt, verdi in ramme.select(["field", "value"]).iter_rows():
            if verdi is None:
                continue
            if felt in ORGNRFELT and _er_ni_siffer(str(verdi)):
                orgnr.add(str(verdi))
            elif felt in NAVNEFELT:
                navn.add(str(verdi).strip())
        if "entity_name" in kolonner:
            navn |= {str(n).strip()
                     for n in ramme["entity_name"].to_list() if n}
    return orgnr, navn


# --------------------------------------------------- prøvene

def _tekst(sti: Path) -> str | None:
    if sti.suffix.lower() in PAKKEDE_TYPER:
        return _pakket_tekst(sti)
    if sti.suffix.lower() not in TEKSTTYPER and sti.name not in TEKSTFILER:
        return None
    try:
        return sti.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _pakket_tekst(sti: Path) -> str | None:
    """Innholdet i en gzip-pakket søkeindeksfil, som tekst.

    ## Hvorfor dette finnes, og hvorfor det ikke er en oppmykning

    Pagefind skriver 2 558 filer under `/pagefind/`, og fragmentene
    inneholder TEKSTEN FRA SIDENE — navn, kommuner, orgnumre, alt.
    De er like publiserte som HTML-en, og de er laget for å lastes ned
    av nettleseren.

    De er gzip-pakket med en 12-byte hale-header (`pagefind_dcd`) foran
    en CBOR-kropp. Vakten kan ikke lese dem som tekst uten å pakke dem
    ut, og en fil den ikke kan lese skal rapporteres som `ugranska` —
    ikke antas trygg. MÅLT 22.09.2026 gjorde den nettopp det: 2 558
    funn, og publiseringen ble stoppet.

    Å pinne dem på sha256 som fontene, går ikke: summen endres hver uke
    fordi innholdet er sidene. Å legge dem i `TEKSTTYPER` ville vært en
    løgn: de ER ikke tekst.

    Den tredje veien er å PAKKE DEM UT og granske innholdet. Da leser
    vakten det som faktisk går ut, med de samme tre prøvene som for
    HTML. CBOR-rammen blir med som støy i strengen; det gjør prøvene
    litt bråkete, ikke blinde, og det er riktig vei å ta feil.

    Returnerer None om fila ikke lar seg pakke ut — da står den som
    `ugranska`, som den skal.
    """
    import gzip
    try:
        raa = gzip.decompress(sti.read_bytes())
    except (OSError, gzip.BadGzipFile, EOFError):
        return None
    return raa.decode("utf-8", errors="replace")


def _personformmonster(koder: Iterable[str]) -> re.Pattern | None:
    """Kodene som HELT ORD — ikke som del av et ord. None hvis lista er tom.

    Lista leses fra `core/persondata.py` og skrives ikke av her. To lister
    over hvem vi nekter å publisere om ville vært to steder å glemme det
    ene, og det er formen F6 og F7 hadde.
    """
    koder = sorted(set(koder))
    if not koder:
        return None
    m = "|".join(re.escape(k) for k in koder)
    return re.compile(rf"(?<![A-Za-zÆØÅæøå])({m})(?![A-Za-zÆØÅæøå])")


# Personformkoden i en sammenheng der noen har SAGT at det er en
# organisasjonsform. Vinduet er slakt med vilje: `oversikt.html` skriver
# «"felt": "organisasjonsform", ..., "eksempler": ["AS", "DA", "KBO"]»,
# altså med feltnavnet et stykke foran verdien.
FORMKONTEKST = re.compile(r"organisasjonsform.{0,200}?", re.I | re.S)

# Hvor langt etter feltnavnet en kode fortsatt regnes som samme
# sammenheng. Målt mot den ene ekte genererte fila vi har: 62 tegn er
# avstanden der, og taket er satt med margin.
KONTEKSTVINDU = 200


def tvetydige_koder(rammer: Iterable[pl.DataFrame]) -> set[str]:
    """Personformkoder som også er en LOVLIG verdi et annet sted i dataene.

    MÅLT, ikke listet. 16.09.2026 over nyeste snapshot per kilde:

        DA    kapasitet_enhet    748 rader    dekar, ikke «delt ansvar»

    Dette er grunnen til at den brede prøven ikke overlevde at grensa
    flyttet seg. Fram til 16.09 var `PERSONFORMER` lik `{"ENK"}`, og
    «ENK» betyr ikke noe annet noe sted — et helt ord var derfor en god
    nok stedfortreder for «dette er en organisasjonsform». Da `DA` kom
    inn i lista, sluttet den å være det: kjørt mot den ene ekte
    genererte fila vi har, meldte prøven fire funn, og alle fire var
    arealenheten eller en feltoppsummering.

    Det er regel 1b-2 en gang til. En kontroll som måler noe som LIGNER
    det den skal måle, er riktig akkurat så lenge de to faller sammen.
    En blokkerende vakt som fyrer på hver arealangivelse blir slått av,
    og da har den gjort skade i stedet for nytte.

    For de tvetydige kodene kreves derfor at feltnavnet står i nærheten
    — se `FORMKONTEKST`. For de entydige holder ordet alene.
    """
    ut: set[str] = set()
    for ramme in rammer:
        if {"field", "value"} - set(ramme.columns):
            continue
        for felt, verdi in ramme.select(["field", "value"]).iter_rows():
            if felt == persondata.FORM_FELT or verdi is None:
                continue
            kode = str(verdi).strip().upper()
            if kode in persondata.PERSONFORMER:
                ut.add(kode)
    return ut


def _ukjente_orgnr(tekst: str, orgnr_ok: set[str], fil: str) -> list[Funn]:
    """Ni-sifrede tall som ikke er gjort rede for. Én rad per NUMMER.

    Egen funksjon fordi den gjelder uansett filformat: et orgnummer i en
    CSV-celle er like publisert som ett i en tabellcelle, og prøven er
    den samme — finnes tallet igjen blant orgnumrene i de filtrerte
    snapshotene?

    Teller forekomster framfor å melde hver enkelt. En CSV med 764 rader
    kan bære samme nummer 764 ganger, og 764 like funn er en rapport
    ingen leser.
    """
    ukjente: dict[str, int] = {}
    for treff in NI_SIFFER.findall(tekst):
        if treff not in orgnr_ok:
            ukjente[treff] = ukjente.get(treff, 0) + 1
    # Bare de fire siste sifrene i rapporten. Et funn skal kunne finnes
    # igjen i fila uten at rapporten selv blir en lekkasje.
    return [Funn(fil, "ukjent_orgnr", f"…{nr[-4:]}", antall)
            for nr, antall in sorted(ukjente.items())]


def gransk_tekst(tekst: str, orgnr_ok: set[str], navn_ok: set[str],
                 fil: str = "", tvetydige: Iterable[str] = (),
                 kvittert: dict | None = None) -> list[Funn]:
    """De tre prøvene på én filkropp. Returnerer funnene, tom = rent.

    `tvetydige` er kodene som også betyr noe annet i dataene — de søkes
    bare i en organisasjonsform-sammenheng. Standarden er tom, altså den
    strengeste lesningen: en kaller som ikke har målt noe, får alle
    kodene prøvd som hele ord.

    `kvittert` er `kvitteringer()` — {(felt, signatur): kvitteringen}.
    Standarden er ingen: en kaller som ikke har lest kvitteringene skal
    ikke få dem gratis. Et kvittert funn RETURNERES som funn, med
    `Funn.kvittert` satt; det er kalleren (`main()`) som lar det stå
    utenfor exit-koden.
    """
    funn = _ukjente_orgnr(tekst, orgnr_ok, fil)
    kvittert = kvittert or {}
    navn_ok = _noekler(navn_ok)

    tvetydige = {k.strip().upper() for k in tvetydige}
    treff_form: list[str] = []

    # EN PERSONFORMKODE INNE I EN FELTMERKET NAVNEVERDI er attribuerbar,
    # og det er forskjellen på et funn som kan kvitteres ut og et som
    # ikke kan. «hele fila inneholder ordet ANS» kan bare kvitteres som
    # et SLAG; «tildelt_navn på denne siden er en verdi med signatur
    # #ab…» kan kvitteres som ETT FUNN, og et femte navn har da ingen
    # kvittering.
    #
    # Her brukes ALLE kodene, også de tvetydige. `DA` i en
    # `kapasitet_enhet`-celle er dekar, men `DA` som siste ord i et
    # NAVNEFELT er en personform — merkingen sier hvilket av de to det er,
    # og det er den samme skjerpingen `gransk_csv` fikk av
    # kolonneoverskriften 16.09.
    alle_koder = _personformmonster(persondata.PERSONFORMER)
    attribuert: dict[tuple[str, str], int] = {}
    navnespenn: list[tuple[int, int]] = []
    for m in FELTMERKE.finditer(tekst):
        felt, verdi = m.group(1), _celleverdi(m.group(2))
        if felt not in NAVNEFELT or not verdi:
            continue
        n = len(alle_koder.findall(verdi)) if alle_koder else 0
        if n:
            nøkkel = (felt, verdi)
            attribuert[nøkkel] = attribuert.get(nøkkel, 0) + n
            navnespenn.append((m.start(2), m.end(2)))

    # Resten av teksten er det som IKKE kunne attribueres. Navneverdiene
    # maskeres framfor å trekkes fra, så posisjonene står — tekstvinduet
    # under er posisjonsavhengig, og et fratrekk kunne blitt negativt.
    if navnespenn:
        biter = list(tekst)
        for start, slutt in navnespenn:
            biter[start:slutt] = " " * (slutt - start)
        resten = "".join(biter)
    else:
        resten = tekst

    # De ENTYDIGE kodene: hele ordet, hvor som helst i fila.
    entydig = _personformmonster(persondata.PERSONFORMER - tvetydige)
    if entydig:
        treff_form += entydig.findall(resten)

    # De TVETYDIGE: bare der feltnavnet står like foran.
    tvetydig = _personformmonster(tvetydige)
    if tvetydig:
        for m in re.finditer("organisasjonsform", resten, re.I):
            vindu = resten[m.end():m.end() + KONTEKSTVINDU]
            treff_form += tvetydig.findall(vindu)

    # De FELTMERKEDE cellene: samme regel som `gransk_csv` stiller på en
    # kolonne. En `organisasjonsform`-celle med `DA` er delt ansvar, og
    # den trenger ikke tekstvinduet over — merkingen SIER hva feltet er.
    ukjente_navn: dict[str, int] = {}
    for felt, verdi in felt_verdier(tekst):
        if felt in NAVNEFELT:
            if navnenoekkel(verdi) not in navn_ok:
                ukjente_navn[verdi] = ukjente_navn.get(verdi, 0) + 1
        elif felt == persondata.FORM_FELT:
            if persondata.er_personform(verdi):
                treff_form.append(verdi.upper())
        elif felt == persondata.SEKTOR_FELT:
            if persondata.er_personsektor(verdi):
                treff_form.append(verdi)

    if treff_form:
        funn.append(Funn(fil, "personform",
                         f"{sorted(set(treff_form))}", len(treff_form)))

    # De attribuerte, én funnrad per (felt, verdi) — og hver av dem slås
    # opp mot kvitteringene. Rapporten bærer signaturen og ikke navnet:
    # en kvittering skal kunne etterprøves fra loggen, og loggen skal
    # ikke være stedet navnet står.
    for (felt, verdi), antall in sorted(attribuert.items()):
        sig = _signatur(verdi)
        k = kvittert.get((felt, sig))
        funn.append(Funn(
            fil, "personform",
            f"{felt} {_anonymiser(verdi)} sig={sig[:8]}", antall,
            kvittert=(f"{k['dato']} {k['kvittert_av']}" if k else ""),
            noekkel=f"{felt}/{sig}"))

    # De gamle merkingene først, så kan den feltmerkede prøven la et navn
    # som alt er meldt være. Meldes det to ganger, er det fordi cellen
    # har to merkinger — og to funnrader om samme navn i samme fil er
    # støy, ikke informasjon.
    meldt: set[str] = set()
    for navn in navn_i(tekst):
        if navnenoekkel(navn) not in navn_ok:
            funn.append(Funn(fil, "ukjent_navn", _anonymiser(navn)))
            meldt.add(navn)

    for navn, antall in sorted(ukjente_navn.items()):
        if navn not in meldt:
            funn.append(Funn(fil, "ukjent_navn", _anonymiser(navn), antall))

    return funn


# --------------------------------------------------- uferdig tekst
#
# MARKØRENE FOR TEKST SOM IKKE ER SKREVET FERDIG. Én liste, fordi de er
# ett spørsmål: står det noe i utputtet som var ment for oss og ikke for
# leseren?
#
# Grunnen til at dette er portens sak og ikke korrekturens: en uvedtatt
# setning på nettstedet er en PÅSTAND vi ikke har gått god for, og
# /om/-seksjonen som ble tatt ut 24.09.2026 var nettopp det — «Utkast.
# [Heine skriver endelig tekst.]» sto synlig over en skisse av hva andre
# har lov til med dataene. Merket gjorde den ærlig og ikke mindre
# publisert. Det er samme klasse som `ugranska`: ikke et personvernbrudd,
# men noe som forlot maskinen uten at noen tok stilling til det.
#
# Markørene er repoets egne konvensjoner, ikke gjetninger:
#
#   [Heine          plassholderen i beslutningsnotatene og i malene —
#                   «[Heine]», «[Heine skriver endelig tekst.]»
#   [fylles inn]    frontmatterens plassholder for en commit-sha
#   Utkast.         merket `.utkast-merke` skriver, og overskriften
#                   «**UTKAST.**» i notatene
#   TODO / FIXME    de vanlige, som ingen skriver med vilje i prosa
#   Lorem ipsum     fyllteksten fra en designfil
#
# HAKEPARENTES-NAVNET er med vilje bare «[Heine»: en generisk prøve på
# «[ord]» ville truffet legitim tekst — kildehenvisninger og
# tegnforklaringer bruker hakeparentes — og en prøve som feller det ekte
# blir en prøve noen slår av.
#
# «Utkast.» søkes VERSALFØLSOMT, og det er målt hvorfor. Ordet står i
# utputtet to steder: i `om/index.html`, som er funnet vi vil ha, og i
# `stil.css` — stilarket bærer kommentarene sine ut, og en av dem sier
# «ET UTKAST SKAL SE UT SOM ET UTKAST.» En versalblind prøve ville felt
# porten på vår egen forklaring av mekanismen, hver kjøring.
#
# Formen som prøves er derfor badgens egen: `<strong>Utkast.</strong>`.
# Ordgrensa foran gjør at «forskriftsutkast.» ikke treffer. Prisen er at
# en plassholder skrevet «UTKAST.» i en HTML-side slipper gjennom; den
# formen finnes i beslutningsnotatene, som ikke bygges, og et notat som
# en dag legges ut er en ny prøve verdt — ikke en grunn til å felle
# stilarket i dag.
UFERDIGMARKORER = (
    "[Heine",
    "[fylles inn]",
    "Utkast.",
    "TODO",
    "FIXME",
    "Lorem ipsum",
)

# «Utkast.» skal ikke treffe inni et sammensatt ord. De andre er
# entydige nok til å søkes som de står.
_ORDGRENSE = ("Utkast.",)


def uferdig_tekst(tekst: str, fil: str = "") -> list[Funn]:
    """Markører for tekst som ikke er skrevet ferdig. Tom liste = rent.

    Ett funn per markør, med antallet — ikke ett per treff. En side som
    sier «TODO» fire ganger har ett problem, ikke fire.

    Prøven kjøres på ALLE tekstfiler, også `.csv` og `.json`: en
    plassholder i en nedlastbar fil er verre enn i HTML-en, fordi den
    lever videre et annet sted. Samme begrunnelse som `gransk_csv`.

    Funnet kan IKKE kvitteres ut. Det er et valg: en kvittering sier «vi
    har sett dette og det er riktig», og en markør for uferdig tekst kan
    ikke være riktig — enten er teksten skrevet, eller så skal den ut.
    Se `maler/om.html.j2`.
    """
    funn: list[Funn] = []
    for markor in UFERDIGMARKORER:
        if markor in _ORDGRENSE:
            antall = len(re.findall(rf"\b{re.escape(markor)}", tekst))
        else:
            antall = tekst.count(markor)
        if antall:
            funn.append(Funn(fil, "uferdig", f"«{markor}»", antall))
    return funn


# ------------------------------------------- repo-stier i utputtet
#
# EN LESER KAN IKKE ÅPNE EN FIL I REPOET.
#
# `Se docs/APNE-SPORSMAL.md` sto som `<code>` på hver av 1 782
# lokalitetssider. Stien peker på noe bare vi har, og den som følger den
# får ingenting. Det er samme klasse som et rått tidsstempel: kildens
# eller vårt eget arbeidsformat, sluppet ut i teksten.
#
# Prøven leser SYNLIG tekst, som `raa_tidsstempler()`, så en `href` til
# en ekte adresse ikke felles. Mønstrene er de to som faktisk lekker:
# en sti under `docs/`, og et filnavn som slutter på `.md`.
REPOSTI = re.compile(r"\bdocs/[\w./-]+|\b[\w./-]+\.md\b")


# SKRIPT OG STILARK BÆRER SINE EGNE KOMMENTARER UT, og en kommentar er
# ikke noe en leser ser. `kystloggen.js` forklarer en avgjørelse med
# «se docs/VISNING.md», og det er riktig sted for den forklaringen.
#
# At kommentarene i det hele tatt sendes med er et annet spørsmål — det
# handler om filstørrelse og om hva vi utleverer, ikke om hva leseren
# møter. Det er ikke avgjort her.
UTEN_REPOSTIPROVE = {".js", ".css", ".map"}


def repostier(tekst: str, fil: str = "") -> list[Funn]:
    """Stier inn i repoet, i synlig tekst. Tom liste = rent."""
    if any(fil.lower().endswith(e) for e in UTEN_REPOSTIPROVE):
        return []
    synlig = TAGG.sub(" ", MASKINELEMENTER.sub(" ", tekst))
    treff = REPOSTI.findall(synlig)
    if not treff:
        return []
    return [Funn(fil, "reposti",
                 f"«{treff[0]}»" + (f" og {len(treff) - 1} til"
                                    if len(treff) > 1 else ""),
                 len(treff))]


# ------------------------------------------- kart uten attribusjon
#
# KYSTLINJA ER KARTVERKETS, OG CC BY 4.0 KREVER NAVNET DER PRODUKTET
# BRUKES. Vilkårssiden, ordrett: «Kartverkets namn skal visast i alle
# samanhengar der produkta eller uttrekk av produkta blir brukt … på
# følgjande måte: © Kartverket.» Se docs/LISENSKJEDE.md merknad J.
#
# Det er ikke en kolofon. Et kart uten navnet er et lisensbrudd, og
# forskjellen på det og de andre funnene i denne fila er at dette er en
# tredjeparts RETTIGHET og ikke vår egen hygiene.
#
# MERKET ER `data-kart` PÅ SVG-EN, satt av malen. En prøve på
# `<svg class="kystkart"` ville måttet kjenne hver klasse hvert kart
# har, og et nytt kart med en ny klasse ville sluppet gjennom stille.
KARTMERKE = re.compile(r"<svg\b[^>]*\bdata-kart\b", re.I)
KARTNAVN = "© Kartverket"


def kart_uten_attribusjon(tekst: str, fil: str = "") -> list[Funn]:
    """En side med kart som ikke navngir Kartverket. Tom liste = rent.

    Funnet kan IKKE kvitteres ut, av samme grunn som `uferdig_tekst`:
    en kvittering sier «vi har sett dette og det er riktig», og et kart
    uten attribusjonen kan ikke være riktig.
    """
    if not KARTMERKE.search(tekst) or KARTNAVN in tekst:
        return []
    return [Funn(fil, "kart_uten_attribusjon",
                 f"kart uten «{KARTNAVN}»", len(KARTMERKE.findall(tekst)))]


# ------------------------------------------- rå tidsstempler
#
# KILDENS TIDSSTEMPEL ER IKKE EN DATO EN LESER SKAL SE.
#
# Akvakulturregisteret og pub-aqua lagrer datoer som `2010-11-10T23:00:00Z`
# — midnatt 11. november norsk tid. MÅLT 24.09.2026 sto 3 396 slike
# stempler i det bygde nettstedet, på sider, i CSV og i feed-titler, og
# 94 % av dem oppgir dessuten en dag FOR TIDLIG når datodelen leses som
# den står. Se `visningsord.oslodato()`.
#
# ## Hva som IKKE er et funn
#
# Atom-feeden SKAL ha maskinlesbare tidspunkt i `<updated>` og
# `<published>`, og et `datetime`-attributt er maskinlesbart av natur.
# Prøven leser derfor bare det SYNLIGE: elementteksten i de
# maskinelementene fjernes, og deretter fjernes alle tagger med
# attributtene sine. Det som står igjen er det et menneske ser.
#
# Grensa er ikke «T22 eller T23». Den formen ville vært riktig for
# dagens to kilder og stille for den tredje som skriver T12:34:56Z —
# nøyaktig mønsteret CLAUDE.md 1b-2 handler om.
MASKINELEMENTER = re.compile(
    r"<(updated|published|lastBuildDate|pubDate)>[^<]*</\1>", re.I)
TAGG = re.compile(r"<[^>]*>")
RAATT_TIDSSTEMPEL = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def raa_tidsstempler(tekst: str, fil: str = "") -> list[Funn]:
    """Tidsstempler i SYNLIG tekst. Tom liste = rent.

    Ett funn per fil med antallet, ikke ett per stempel: en side med 40
    rå stempler har én feil i én mal, ikke førti.
    """
    synlig = TAGG.sub(" ", MASKINELEMENTER.sub(" ", tekst))
    treff = RAATT_TIDSSTEMPEL.findall(synlig)
    if not treff:
        return []
    return [Funn(fil, "raatt_tidsstempel",
                 f"«{treff[0]}»" + (f" og {len(treff) - 1} til"
                                    if len(treff) > 1 else ""),
                 len(treff))]


# --------------------------------------------------- CSV
#
# En `.csv` ved siden av sida er ikke mindre publisert enn HTML-en — den
# er verre, fordi den er laget for å lastes ned og leve videre et annet
# sted. Fra 16.09.2026 legger `/lokalitet/<nr>/lusetall.csv` hele
# lusetallserien ut som siterbar fil, og da må vakten se INN i den.
#
# Den kunne ikke det. Målt 16.09.2026 på en konstruert CSV med en
# `navn`-kolonne: `ukjent_navn` fant ingenting. Prøven leter etter en
# HTML-merking (`data-navn`, `class="eier"`), og en CSV har ingen.
#
# I en CSV er det KOLONNEOVERSKRIFTEN som er merkingen. Den er
# generatorens egen, akkurat som HTML-attributtet, og den kommer fra det
# samme feltvokabularet. Det er den samme regelen i et annet format, ikke
# en ny og løsere regel.

# Kommentarlinjer i en CSV. Vår egen bærer attribusjonen; en annen
# generators kan bære hva som helst, og linjene granskes derfor som
# vanlig tekst.
CSV_KOMMENTAR = "#"


def _csv_rader(tekst: str, avgrenser: str = ","):
    """(overskrifter, rader) fra en CSV med `#`-kommentarer. Tåler rot.

    Returnerer `(None, [])` for noe som ikke lar seg lese som CSV. Det er
    IKKE «rent»: kallerne kjører tekstprøvene uansett, og en fil vakten
    ikke forstår strukturen i får dermed den svakere granskningen framfor
    ingen. At den er svakere står i `gransk_csv`.
    """
    linjer = [l for l in tekst.splitlines()
              if not l.lstrip().startswith(CSV_KOMMENTAR)]
    if not linjer:
        return None, []
    try:
        rader = list(csv.reader(linjer, delimiter=avgrenser))
    except csv.Error:
        return None, []
    if not rader:
        return None, []
    return [h.strip() for h in rader[0]], rader[1:]


def gransk_csv(tekst: str, orgnr_ok: set[str], navn_ok: set[str],
               fil: str = "", avgrenser: str = ",") -> list[Funn]:
    """Prøvene på en CSV-kropp, med KOLONNEOVERSKRIFTEN som merking.

    Tre prøver, som i HTML, men to av dem stilt på en annen måte:

      1. `ukjent_orgnr` — uendret. Et ni-sifret tall er et ni-sifret tall
         uansett hvilken kolonne det står i.
      2. `personform` — leses av KOLONNEN og ikke av teksten. En
         `organisasjonsform`-kolonne med `ENK` er et funn; en
         `kapasitet_enhet`-kolonne med `DA` er dekar og er det ikke.
         Tekstvinduet HTML-prøven bruker duger ikke her: i en CSV ligger
         overskriften og verdien en hel rad fra hverandre, og
         nabokolonnen ligger ett tegn unna.
      3. `ukjent_navn` — verdiene i kolonner som HETER noe i `NAVNEFELT`.

    Kommentarlinjene granskes som vanlig tekst med de ENTYDIGE kodene.
    Vår egen CSV har attribusjonen der; en annens kan ha hva som helst.

    Hva den IKKE dekker, sagt rett ut: en kolonne med et navn i, som
    heter noe annet enn feltene i `NAVNEFELT`. Det er den samme grensen
    som i HTML — vakten ser det generatoren merker — og den er billigere
    å leve med enn en prøve som gjetter på hva som er et navn og fyrer
    på hvert stedsnavn i datasettet.
    """
    navn_ok = _noekler(navn_ok)
    overskrifter, rader = _csv_rader(tekst, avgrenser)
    kommentarer = "\n".join(l for l in tekst.splitlines()
                             if l.lstrip().startswith(CSV_KOMMENTAR))

    # ORGNUMRENE LESES PER CELLE, ikke av råteksten, og det er en MÅLT
    # retting fra 16.09.2026.
    #
    # `NI_SIFFER` krever at tallet ikke har siffer, punktum eller komma
    # på noen av sidene. Regelen ble satt for HTML, der «96697320.109» er
    # biomasse i kilo og ikke et orgnummer. I en CSV er kommaet
    # DELIMITEREN: `999888777,Kari` gir et komma rett etter tallet, og
    # prøven fant ingenting. Et orgnummer i en CSV-kolonne var altså
    # usynlig for vakten — i nøyaktig den filtypen som er laget for å
    # lastes ned.
    #
    # Cellene skilles med linjeskift i stedet. Da er delimiteren borte,
    # mens desimaltallet INNE i en celle fortsatt er beskyttet av samme
    # regel.
    celler = "\n".join(v for rad in ([overskrifter or []] + rader)
                        for v in rad)
    funn = _ukjente_orgnr(celler + "\n" + kommentarer, orgnr_ok, fil)
    former: list[str] = []
    entydig = _personformmonster(persondata.PERSONFORMER)
    if entydig and kommentarer:
        former += entydig.findall(kommentarer)

    ukjente_navn: dict[str, int] = {}
    if overskrifter:
        for rad in rader:
            for kolonne, verdi in zip(overskrifter, rad):
                verdi = (verdi or "").strip()
                if not verdi:
                    continue
                if kolonne == persondata.FORM_FELT:
                    if persondata.er_personform(verdi):
                        former.append(verdi.upper())
                elif kolonne == persondata.SEKTOR_FELT:
                    if persondata.er_personsektor(verdi):
                        former.append(verdi)
                elif (kolonne in NAVNEFELT
                      and navnenoekkel(verdi) not in navn_ok):
                    ukjente_navn[verdi] = ukjente_navn.get(verdi, 0) + 1

    if former:
        funn.append(Funn(fil, "personform", f"{sorted(set(former))}",
                         len(former)))
    for navn, antall in sorted(ukjente_navn.items()):
        funn.append(Funn(fil, "ukjent_navn", _anonymiser(navn), antall))
    return funn


# Navn slik en generator plausibelt skriver dem: i et element merket som
# eier- eller navnefelt. Mønsteret er bevisst SMALT — det leter etter en
# merking generatoren selv må sette, ikke etter «ord som ligner et navn».
#
# En bred navnegjenkjenner over all HTML ville gitt hundrevis av treff på
# stedsnavn og overskrifter, og en vakt som alltid fyrer blir slått av.
NAVNEMERKE = re.compile(
    r"""(?:data-(?:navn|eier|entity-name)"""
    r"""|class="[^"]*\b(?:navn|eier)\b[^"]*")"""
    r"""[^>]*>\s*([^<>\n]{2,120}?)\s*<""",
    re.I | re.X)


def navn_i(tekst: str) -> list[str]:
    """Navnestrengene et generert dokument MERKER som navn.

    Vakten kan bare se det generatoren merker. Det er en reell grense, og
    den står i modulens docstring: skriver generatoren et eiernavn som
    løpende tekst uten merking, finner ikke denne prøven det.

    Den grensa er billigere å leve med enn alternativet. En prøve som
    gjettet på hva som er et navn ville fyrt på hvert stedsnavn i
    datasettet, og en vakt som alltid fyrer blir slått av — som er
    nøyaktig hvordan `\\b\\d{9}\\b`-forbudet ville endt.
    """
    return [v for v in (_celleverdi(m.group(1))
                        for m in NAVNEMERKE.finditer(tekst)) if v]


# Merkingen på en FELT-VERDI-celle: feltnavnet ordrett, slik generatoren
# selv kjenner det. `<td data-felt="eier_navn">…</td>`.
#
# Verdien fanges i sin helhet og ikke med et lengdevindu som NAVNEMERKE:
# der er mønsteret en gjetning på hvor navnet slutter, her SIER merkingen
# at hele cellen er verdien av det feltet. Taket på 500 tegn er en sperre
# mot en regex som løper, ikke en påstand om feltlengder.
FELTMERKE = re.compile(
    r'data-felt="([A-Za-z0-9_.\-]{1,60})"[^>]*>\s*([^<>\n]{0,500}?)\s*<')


def felt_verdier(tekst: str) -> list[tuple[str, str]]:
    """(feltnavn, verdi) for hver celle generatoren har feltmerket.

    Dette er prøve 2 og 3 lest av FELTVOKABULARET framfor av en liste
    attributtnavn — se modulens docstring. Kalleren spør `NAVNEFELT`,
    `persondata.FORM_FELT` og `persondata.SEKTOR_FELT`, og ikke denne
    funksjonen, om hva et felt BETYR: to steder som skulle svart det
    samme om det, er formen F6 og F7 hadde.

    Tomme celler faller bort. En `<td data-felt="kapasitet"></td>` er
    ikke en verdi, og et funn på den ville vært et funn på fravær.
    """
    ut: list[tuple[str, str]] = []
    for m in FELTMERKE.finditer(tekst):
        verdi = _celleverdi(m.group(2))
        if verdi:
            ut.append((m.group(1), verdi))
    return ut


def _celleverdi(raa: str) -> str:
    """Celleteksten som en VERDI — avkodet, slik hvitelista har den.

    HTML-en er escapet og snapshotene er ikke. Sammenlignes de to
    direkte, sammenligner vi to alfabeter: MÅLT 18.09.2026 på
    `data/nettsted` meldte `ukjent_navn` **54 funn** på ett eneste navn —
    `EGIL KRISTOFFERSEN &amp; SØNNER AS`, et AS som ligger i hvitelista
    med `&`. Alle 54 var falske, og en vakt som feiler feil blir slått
    av.

    Avkodingen skjer per VERDI og ikke på filkroppen. Prøvd på kroppen
    ville den også endret inputtet til `ukjent_orgnr`, og den prøven er
    en tokenisering der ett tegn til eller fra avgjør — se `NI_SIFFER`.
    """
    return html.unescape(raa).strip()


def _anonymiser(navn: str) -> str:
    """Nok til å finne navnet igjen i fila, ikke nok til å VÆRE det.

    Dette er ikke pedanteri. Vakten kjører i en byggejobb, og
    byggelogger i et offentlig repo er offentlige. En vakt som skriver
    det lekkede navnet til loggen har FLYTTET lekkasjen, ikke stoppet
    den — samme feil som changeloggen gjorde da kildefilteret kom uten
    lesefilteret, og 699 rader med navn havnet i
    `data/changelog/2026-08-24.parquet`.

    Rapporten gir formen, lengden og en kort signatur. Den som gransker
    har fila og kan søke; den som leser loggen får ingenting.
    """
    form = " ".join("W" if o.lower() != "og" else "og" for o in navn.split())
    sign = hashlib.sha256(navn.encode("utf-8")).hexdigest()[:6]
    return f"«{form}» {len(navn)} tegn #{sign}"


# --------------------------------------------------- personformet navn

FORM_SUFFIKS = re.compile(
    r"\s+(AS|ASA|DA|ANS|SA|BA|NUF|KS|IKS|FKF|SF|STI|FLI|PRE|AL|KBO|SÆR)\.?$",
    re.I)


# Organisasjonsformene SSB plasserer i sektor 2300, «personlige
# foretak». Fra 16.09.2026 er de PERSONFORMER — grensa ble flyttet dit,
# se docs/beslutninger/2026-09-16-grensa-gaar-ved-sektor-2300.md.
#
# Lista leses derfor ikke lenger av her. Den ER
# `core/persondata.PERSONFORMER` minus ENK, og en egen kopi ville blitt
# stående uendret den dagen grensa flyttes igjen.
SEKTOR_2300 = frozenset(persondata.PERSONFORMER - {"ENK"})


def personeksponert(navn: str, organisasjonsform: str) -> bool:
    """Er denne entiteten en navngitt fysisk person, så langt dataene når?

    Feller ingenting. Den er en TELLER for rapporten — og fra 16.09.2026
    er den først og fremst en KONTROLL AV DØRA.

    ## Hva tallet betyr nå

    Fram til 16.09 var svaret 46 av 64, og de 46 ble publisert: DA, ANS
    og partrederi passerte filteret, og telleren fantes for å vise hva
    det åpne spørsmålet fra 22.08 kostet. Spørsmålet er avgjort, formene
    filtreres, og telleren skal derfor lese **0**.

    Det gjør den ikke til pynt. `hviteliste()` bygges gjennom
    `snapshot._les()`, og et tall over 0 betyr at noe kom inn UTENOM den
    døra — en hviteliste bygget med `pl.read_parquet`, et snapshot
    skrevet forbi vakten i `snapshot.write()`, eller en femte personform
    ingen har ført opp. Telleren måler altså ikke lenger en kjent
    kostnad; den måler at filteret virker, hver gang rapporten kjøres.

    ## Hvorfor formen må være med, og navnet ikke holder alene

    Målt 15.09.2026 på enhetsregisteret-snapshotet: en navneprøve alene
    — to eller tre ord, ingen bedriftsord — treffer **1278 av 1807**
    entiteter, hvorav **1196 er AS**. Brreg skriver navn i VERSALER (1795
    av 1807), så «NORDLAKS OPPDRETT AS» og «HANSEN OG OLSEN DA» har
    nøyaktig samme form.

    Det er grunnen til at grensa ikke ble flyttet til «DA med personnavn»
    men til hele sektoren: en regel som avhenger av hvordan et navn ser
    ut, er ikke en regel. Navneleddet står igjen HER, i telleren, fordi
    en teller ikke felles av å ta feil — og fordi det er det som gjør et
    tall over 0 lesbart: «noe med personform OG personnavn passerte».
    """
    if organisasjonsform.strip().upper() not in SEKTOR_2300:
        return False
    kjerne = FORM_SUFFIKS.sub("", navn).strip()
    ord_ = kjerne.split()
    if not 2 <= len(ord_) <= 3:
        return False
    return all(re.fullmatch(r"[A-ZÆØÅa-zæøå'\-]{2,}", o) or o.lower() == "og"
               for o in ord_)


def personeksponerte() -> dict[str, int]:
    """{organisasjonsform: antall} for hele hvitelista. For rapporten."""
    from collections import Counter
    ut: Counter = Counter()
    for ramme in _snapshotrammer():
        if {"entity_id", "field", "value"} - set(ramme.columns):
            continue
        navn, form = {}, {}
        kolonner = ["entity_id", "field", "value"]
        for e, f, v in ramme.select(kolonner).iter_rows():
            if f == "navn":
                navn[e] = v
            elif f == persondata.FORM_FELT:
                form[e] = v
        for e, n in navn.items():
            if n and personeksponert(n, form.get(e, "") or ""):
                ut[form[e]] += 1
    return dict(ut)


def filtrert_bort() -> dict[str, int]:
    """{organisasjonsform: antall} som lesedøra HOLDT UTE, per kilde-dato.

    Motstykket til `personeksponerte()`: den teller dem som slapp
    gjennom, denne teller dem som ikke gjorde det. Rapporten trenger
    begge, og den trenger dem HVER GANG.

    Grunnen står i beslutningen 15.09: en blokkerende vakt kan gi en
    falsk trygghet som er dyrere enn en varslende — «bygget er grønt,
    altså er det ingen persondata der» er nøyaktig setningen fra 16.08.
    Et grønt bygg sier bare at de tre prøvene ikke fant noe i utputtet.
    At 64 personer ble holdt ute av lesedøra, er et annet faktum, og det
    skal stå ved siden av det grønne.

    Nyeste dato per kilde, altså samme utvalg som hvitelista.
    """
    ut: dict[str, int] = {}
    if not RAW_DIR.exists():
        return ut
    for kdir in sorted(RAW_DIR.iterdir()):
        if not kdir.is_dir():
            continue
        dato = snapshot.siste_dato(kdir.name)
        if not dato:
            continue
        for form, antall in snapshot.filtrert_bort(kdir.name, dato).items():
            ut[form] = ut.get(form, 0) + antall
    return dict(sorted(ut.items()))


# --------------------------------------------------- inngangen

# --------------------------------------------------- grunnlaget
#
# De tre prøvene gransker UTPUTTET. Denne granskes GRUNNLAGET: stemmer
# erklæringen hvitelista bygges etter med dataene den bygges av?
#
# Spørsmålet finnes fordi de to feilretningene ikke er like:
#
#   «verden» erklært som «henting»   hvitelista blir for LITEN. Hvert navn
#                                    i historikken meldes som ukjent_navn.
#                                    Høyt, irriterende, ufarlig.
#   «henting» erklært som «verden»   hvitelista blir for STOR. Et navn som
#                                    forsvant ut av registeret for et år
#                                    siden er plutselig gjort rede for, og
#                                    en visning som viser det PASSERER.
#                                    Stille.
#
# Den andre er grunnen til at denne prøven finnes. En vakt som bare kan
# felle den støyende retningen er ikke en vakt mot den stille.

# Hvor mange snapshots som må til før «verden» kan motbevises. Med ett
# snapshot er 0 dagers avvik uinformativt: en kilde som ble hentet samme
# dag som tidsrommet den gjelder for ser ut som en henting-kilde, og det
# er ikke en feil — det er fravær av grunnlag. Med to er et sammenfall i
# BEGGE en påstand dataene ikke bærer.
MINST_FOR_AA_MOTBEVISE_VERDEN = 2


def _avvik(kilde: str, dato: str) -> int | None:
    """Dager mellom `observed_at` og datoen i `fetched_at`. None = ukjent.

    Snapshots skrevet før `fetched_at` fantes kan ikke måles, og de skal
    ikke felle noe: fravær av et tidsstempel er ikke en feil erklæring.
    """
    for _versjon, ramme in snapshot.versjoner(kilde, dato):
        hentet = snapshot.fetched_at_i(ramme)
        if not hentet:
            continue
        try:
            return (dt.date.fromisoformat(dato)
                    - dt.date.fromisoformat(hentet[:10])).days
        except ValueError:
            return None
    return None


# Filtaket hos verten.
#
# Cloudflare Pages tar 20 000 filer per utrulling på gratisplanen.
# Grensa her er 15 000, og avstanden er med vilje: en port som fyrer
# ved 19 999 gir én ukes varsel, og den uka går med til å finne ut hva
# som skal kuttes. MÅLT 23.09.2026: 9 005 filer, og veksten er 0–15
# filer i uka. Det gir år, ikke uker — men tallet skal ses, ikke
# oppdages.
FILTAK = 15_000


def filtallsfunn(mappe: Path) -> list[Funn]:
    """Nærmer publiseringsmappa seg vertens filtak?

    Ikke et personvernfunn, og det er grunnen til at den står for seg:
    porten er stedet som ser på det ferdige utputtet, og et nettsted som
    ikke lar seg rulle ut er like upublisert som et med persondata i.
    """
    antall = sum(1 for p in mappe.rglob("*") if p.is_file())
    if antall < FILTAK:
        return []
    return [Funn(str(mappe), "filtak",
                 f"{antall} filer — taket hos Cloudflare Pages er 20 000, "
                 f"og porten varsler fra {FILTAK}")]


def kodeproveniensfunn() -> list[Funn]:
    """Snapshots som ikke kan spores tilbake til kode som er PUSHET.

    F15 to ganger — se `core/kodeproveniens.py`. Prøven stiller
    spørsmålet den faktisk vil ha svar på: ikke «finnes koden», men
    «finnes den der alle kan se den».

    ## Tre utfall, og bare to av dem er funn

      * **Fila har ikke feltet.** Skrevet før 23.09.2026. Rapporteres som
        `kodeproveniens_ukjent` og er IKKE et funn: de 1 833 filene er
        append-only, og å felle porten på dem ville felt den for alltid.
        En port som alltid faller blir slått av.
      * **Feltet er der og tomt, eller treet var urent.** Funn. Da har
        koden som stempler kjørt, og likevel visste den ikke — eller
        visste at den ikke kunne gjøre rede for seg.
      * **Hashen finnes ikke på `origin/main`.** Funn. Det er F15 i sin
        rene form.

    Skillet mellom de to første krever at man vet om KOLONNEN fantes, og
    ikke bare om den er tom. `snapshot.kodeproveniens_per_fil()` svarer
    på det; lesingen bor der fordi ingen annen modul får kombinere
    `RAW_DIR` med en parquet-lesing.

    ## Hvorfor «på origin/main» spørres på nytt hver gang

    Om en commit er pushet kan endre seg ETTER at fila ble skrevet. Det
    er en opplysning om verden nå, ikke om raden, og den lagres derfor
    ikke i fila — CLAUDE.md 1b-7.
    """
    funn: list[Funn] = []
    for post in snapshot.kodeproveniens_per_fil():
        rel = f"data/raw/{post['kilde']}/{post['fil']}"
        if not post["har_felt"]:
            continue       # grensa i historikken, se `kodeproveniens_ukjente()`
        if not post["commit"]:
            funn.append(Funn(rel, "kodeproveniens",
                             "feltet finnes, men er tomt"))
            continue
        for sha in post["commit"]:
            if post["rent"] != [kodeproveniens.RENT]:
                funn.append(Funn(
                    rel, "kodeproveniens",
                    f"{sha[:12]} — arbeidstreet var ikke rent "
                    f"({', '.join(post['rent']) or 'uoppgitt'})"))
            pushet, hvordan = kodeproveniens.paa_origin_main(sha)
            if not pushet:
                funn.append(Funn(
                    rel, "kodeproveniens",
                    f"{sha[:12]} finnes ikke på origin/main ({hvordan})"))

    return funn


def kodeproveniens_ukjente() -> list[Funn]:
    """Filene som ble skrevet FØR regelen fantes, talt per kilde.

    Ikke med i `gransk()`, og det er et valg: `gransk()` returnerer det
    porten FALLER PÅ, og disse filene kan ikke rettes. De er
    append-only, og et stempel satt i ettertid ville påstått at fila ble
    skrevet av kode som ikke fantes da.

    Men de skrives HVER kjøring, av samme grunn som `filtrert_bort()`:
    et aggregat ingen ser er det samme som ingen kontroll. Grensa i
    historikken skal være synlig, ikke glemt — og tallet skal synke.
    """
    ukjente: dict[str, int] = {}
    for post in snapshot.kodeproveniens_per_fil():
        if not post["har_felt"]:
            ukjente[post["kilde"]] = ukjente.get(post["kilde"], 0) + 1
    return [Funn(f"data/raw/{kilde}", "kodeproveniens_ukjent",
                 f"{antall} filer skrevet før 23.09.2026")
            for kilde, antall in sorted(ukjente.items())]


def grunnlagsfunn() -> list[Funn]:
    """Erklæringer som ikke kan gjøres rede for mot dataene.

    To slag:

      * `ukjent_partisjon` — kilden har ikke erklært seg. Hvitelista leser
        da nyeste dato alene, som er den strengeste lesningen, men
        stillhet skal ikke belønnes: en ny kilde som glemmer erklæringen
        skal stoppe publiseringen, akkurat som en UBELAGT attribusjon
        gjør det.
      * `feilerklaert_partisjon` — dataene motsier erklæringen.

    Prøven er MÅLT mulig, og det er hele grunnen til at den kan stå:
    19.09.2026 har de fire henting-kildene 0 dagers avvik i HVERT enkelt
    snapshot — min og maks, ikke bare median — og de åtte verden-kildene
    median mellom −77 og −3532. Skillet er ikke gradvist. Se
    docs/MALING-PARTISJONERING.md punkt 1.
    """
    if not RAW_DIR.exists():
        return []
    partisjonering, _kilder = _erklaeringene()
    funn: list[Funn] = []

    for kdir in sorted(RAW_DIR.iterdir()):
        if not kdir.is_dir():
            continue
        kilde = kdir.name
        datoer = snapshot.datoer(kilde)
        if not datoer:
            continue
        erklaert = partisjonering.get(kilde)

        if erklaert is None:
            funn.append(Funn(f"data/raw/{kilde}", "ukjent_partisjon",
                             "ingen kilde skriver under navnet"))
            continue
        if not erklaert:
            funn.append(Funn(f"data/raw/{kilde}", "ukjent_partisjon",
                             "Source.partisjonering er ikke satt"))
            continue

        avvik = [(d, _avvik(kilde, d)) for d in datoer]
        maalte = [(d, a) for d, a in avvik if a is not None]
        if not maalte:
            continue                      # ingen fetched_at å måle mot

        if erklaert == "henting":
            # Ett eneste snapshot som gjelder for et annet tidsrom enn
            # dagen det ble hentet, motsier «henting». Her trengs ingen
            # terskel: påstanden er at de ALLTID faller sammen.
            uenige = [(d, a) for d, a in maalte if a != 0]
            if uenige:
                d, a = uenige[0]
                funn.append(Funn(
                    f"data/raw/{kilde}", "feilerklaert_partisjon",
                    f"erklært «henting», men {len(uenige)} av {len(maalte)} "
                    f"snapshots gjelder for et annet tidsrom enn hentingen "
                    f"({d}: {a} dager). Er kilden «verden», leser hvitelista "
                    f"bare nyeste dato av den"))
        elif erklaert == "verden":
            if (len(maalte) >= MINST_FOR_AA_MOTBEVISE_VERDEN
                    and all(a == 0 for _d, a in maalte)):
                funn.append(Funn(
                    f"data/raw/{kilde}", "feilerklaert_partisjon",
                    f"erklært «verden», men alle {len(maalte)} snapshots er "
                    f"datert dagen de ble hentet. Er kilden «henting», "
                    f"hvitelister vi navn som ikke gjelder lenger"))
    return funn


def utdrag_dekker_indeksen(katalog: Path) -> tuple[int, int]:
    """(sider Pagefind sier den indekserte, tekstutdrag på disk).

    DERIVASJONSARGUMENTET, gjort målbart. `.pf_index` og `.pf_meta`
    står som AVLEDET av tekstutdragene fordi Pagefind trekker ut
    teksten fra en side ÉN gang og skriver den til begge. Argumentet
    hviler på at det finnes ett utdrag per indeksert side.

    Er de to tallene ulike, er ordtabellen bygget av noe vakten ikke
    har sett, og unntaket i `AVLEDEDE_TYPER` er en blindsone framfor en
    avledning. `gransk()` melder det da som et funn.

    (0, 0) for en katalog uten `pagefind-entry.json` — altså der
    søkeindeksen ikke er bygget i det hele tatt. Det er ikke en feil;
    byggerapporten sier fra om det for seg.
    """
    entry = katalog / "pagefind-entry.json"
    if not entry.exists():
        return 0, 0
    try:
        data = json.loads(entry.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return -1, 0
    sider = sum(int((s or {}).get("page_count") or 0)
                for s in (data.get("languages") or {}).values())
    utdrag = len(list(katalog.rglob("*.pf_fragment")))
    return sider, utdrag


# SETNINGEN BUNNTEKSTEN SKRIVER NÅR `HAVBRUK_KONTAKT` IKKE ER SATT.
#
# En påfunnet adresse ville vært verre enn ingen, så bygget sier det
# heller høyt — og på en forhåndsvisning er det riktig. I PRODUKSJON er
# det ikke: da står det på hver av 2 348 sider at det ikke finnes en vei
# inn, og «feil i dataene? skriv» rett under. En side som ber om
# rettelser uten å oppgi hvor, er verre enn en som ikke ber.
#
# Prøven leser setningen fra malen og ikke en egen kopi: to steder som
# skal si det samme er formen F6 og F7 hadde.
UTEN_KONTAKT = "Ingen kontaktadresse er satt i denne"


def gransk(mappe: Path, produksjon: bool = False) -> list[Funn]:
    """Alle filer under `mappe`, OG grunnlaget hvitelista bygges på.

    Grunnlagsfunnene er med i samme liste fordi de har samme følge: en
    hviteliste bygget på en feil erklæring er en hviteliste som gjør rede
    for noe den ikke har sett, og et grønt bygg på den er verre enn et
    rødt. Porten skiller dem ikke, og exit-koden dekker begge.
    """
    funn: list[Funn] = (list(grunnlagsfunn()) + list(kodeproveniensfunn())
                        + list(filtallsfunn(mappe)))

    # SØKEINDEKSENS DERIVASJON, sjekket før filene leses. Se
    # `utdrag_dekker_indeksen()`.
    sider, utdrag = utdrag_dekker_indeksen(mappe / "pagefind")
    if sider != utdrag:
        funn.append(Funn(
            "pagefind/pagefind-entry.json", "ugranska",
            f"søkeindeksen oppgir {sider} sider, men det finnes "
            f"{utdrag} tekstutdrag — ordtabellene kan da være bygget av "
            f"noe som ikke er gransket"))

    # KONTAKTADRESSEN, bare for et produksjonsbygg. Se `UTEN_KONTAKT`.
    if produksjon:
        forside = mappe / "index.html"
        tekst = _tekst(forside) if forside.exists() else None
        if tekst is None:
            funn.append(Funn("index.html", "uten_kontakt",
                             "forsiden kan ikke leses"))
        elif UTEN_KONTAKT in tekst:
            funn.append(Funn(
                "index.html", "uten_kontakt",
                "bygget oppgir ingen kontaktadresse, og ber samtidig om "
                "rettelser. Sett HAVBRUK_KONTAKT"))

    orgnr_ok, navn_ok = hviteliste()
    tvetydige = tvetydige_koder(_snapshotrammer())
    kvittert = kvitteringer()
    for sti in sorted(p for p in mappe.rglob("*") if p.is_file()):
        rel = str(sti.relative_to(mappe))
        tekst = _tekst(sti)
        if tekst is None:
            # Ikke antatt trygg. En .parquet eller .xlsx ved siden av
            # sida er like publisert som HTML-en, og vakten sier at den
            # ikke har lest den framfor å tie.
            #
            # Unntaket er de binærfilene vi HAR sett i, og de kjennes på
            # innholdet: summen av fila mot `BINAERFILER`. Treffer den,
            # er dette fila som ble inspisert og ingen annen.
            sum_ = hashlib.sha256(sti.read_bytes()).hexdigest()
            if sum_ in BINAERFILER_ALLE:
                continue
            # AVLEDET AV NOE SOM ER GRANSKET. Se `AVLEDEDE_TYPER` for
            # hele argumentet og for hvorfor de to andre veiene ikke
            # duger. Prøven som holder argumentet sant er
            # `test_hvert_indeksert_sideutdrag_granskes`.
            if sti.suffix.lower() in AVLEDEDE_TYPER:
                continue
            funn.append(Funn(rel, "ugranska", sti.suffix or "(uten endelse)"))
            continue
        # UFERDIG TEKST, på hver tekstfil uansett type. Se
        # `UFERDIGMARKORER`.
        funn.extend(uferdig_tekst(tekst, fil=rel))
        # RÅ TIDSSTEMPLER i synlig tekst. Se `raa_tidsstempler()`.
        funn.extend(raa_tidsstempler(tekst, fil=rel))
        # REPO-STIER i synlig tekst. Se `repostier()`.
        funn.extend(repostier(tekst, fil=rel))
        # KART UTEN KARTVERKETS NAVN. Et lisensvilkår, ikke hygiene.
        funn.extend(kart_uten_attribusjon(tekst, fil=rel))
        if sti.suffix.lower() in KOLONNETYPER:
            funn.extend(gransk_csv(tekst, orgnr_ok, navn_ok, fil=rel,
                                   avgrenser=KOLONNETYPER[sti.suffix.lower()]))
        else:
            funn.extend(gransk_tekst(tekst, orgnr_ok, navn_ok, fil=rel,
                                     tvetydige=tvetydige, kvittert=kvittert))
    return funn


def ukvittert(funn: Iterable[Funn]) -> list[Funn]:
    """Funnene som IKKE er gjort rede for. Det er disse porten faller på.

    Egen funksjon, og ikke en `if` i `main()`: `nettsted.gransk_og_meld()`
    er den andre kalleren, og to steder som skal si det samme om hva som
    feller publiseringen er formen F6 og F7 hadde.
    """
    return [f for f in funn if not f.kvittert]


def _kvitterte_funn(funn: Iterable[Funn]) -> None:
    """Hva som er kvittert ut, HVER kjøring.

    Dette er hele grunnen til at kvitteringen ikke er en bryter. Et funn
    som er forstått, skal fortsatt telles og navngis — ellers betyr «0
    funn» to helt ulike ting («ingen fant noe» og «noen har sagt at det er
    greit»), og den som leser kan ikke se hvilket.

    Samme begrunnelse som `filtrert_bort()` under: et tall som bare vises
    når noe er galt, er et tall ingen kjenner normalverdien til.
    """
    kvitterte = [f for f in funn if f.kvittert]
    alle = kvitteringer()
    print(f"\nKvitterte funn i denne kjøringen: {len(kvitterte)}"
          f"   ({len(alle)} kvitteringer finnes i {KVITTERING_DIR})")
    per_sak: dict[str, int] = {}
    for f in kvitterte:
        per_sak[f"{f.utdrag}  [{f.kvittert}]"] = (
            per_sak.get(f"{f.utdrag}  [{f.kvittert}]", 0) + f.antall)
    for sak, antall in sorted(per_sak.items()):
        print(f"    {antall:>4}x  {sak}")

    # Kvitteringer som ikke traff noe. En kvittering for et funn som ikke
    # finnes lenger er ikke farlig, men den er RØTE: den ser ut som en
    # levende påstand og dekker ingenting. Tallet gjør den synlig, og
    # veien ut er `status: "trukket"`.
    truffet = {f.noekkel for f in kvitterte if f.noekkel}
    ubrukte = sorted(f"{felt}/{sig}" for felt, sig in alle
                     if f"{felt}/{sig}" not in truffet)
    if ubrukte:
        print(f"    {len(ubrukte)} kvittering(er) traff ingen funn i denne")
        print("    kjøringen — funnet kan være borte fra utputtet:")
        for n in ubrukte:
            felt, _, sig = n.partition("/")
            print(f"      {felt} sig={sig[:8]}")

    print("  En kvittering er en påstand om at funnet er FORSTÅTT, ikke at")
    print("  det er borte. Den dekker ÉN verdi i ÉTT felt; en ny verdi har")
    print("  ingen kvittering og feller porten. Se kvitteringer().")


def _rapport(funn: Iterable[Funn] = ()) -> None:
    """Hvem grensa holder ute, og hvem den slipper gjennom. Begge tall.

    Skrives HVER gang `--rapport` er med, uavhengig av om granskningen
    fant noe. Et tall som bare vises når noe er galt, er et tall ingen
    kjenner normalverdien til.
    """
    print(f"\nGrensa: SSB-sektor {', '.join(sorted(persondata.PERSONSEKTORER))}"
          f" — {', '.join(sorted(persondata.PERSONFORMER))}")

    holdt_ute = filtrert_bort()
    print(f"Filtrert bort i lesedøra: {sum(holdt_ute.values())}")
    for f_, n_ in holdt_ute.items():
        print(f"    {f_:12} {n_:>4}")
    if not holdt_ute:
        print("    ingen — og et filter som aldri tar noe er et filter")
        print("    ingen har prøvd mot virkeligheten. Undersøk.")

    eksp = personeksponerte()
    print(f"\nPersoneksponerte som PASSERER filteret: {sum(eksp.values())}")
    for f_, n_ in sorted(eksp.items()):
        print(f"    {f_:12} {n_:>4}")
    if eksp:
        print("  Over 0 betyr at noe kom inn utenom snapshot._les().")
        print("  Se personeksponert() — dette skal være 0 fra 16.09.2026.")

    _kvitterte_funn(funn)

    print("\nIngen av tallene sier at utputtet er trygt. De tre prøvene")
    print("ser bare det som kom UTENOM døra — se modulens docstring.")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("\n  python publiseringsvakt.py <mappe> [--rapport]")
        return 2
    mappe = Path(sys.argv[1])
    if not mappe.is_dir():
        print(f"{mappe} er ikke en mappe.")
        return 2

    orgnr_ok, navn_ok = hviteliste()
    print(f"Hviteliste fra {RAW_DIR}: {len(orgnr_ok)} orgnumre, "
          f"{len(navn_ok)} navn — lest gjennom snapshot._les()")

    funn = gransk(mappe)
    if "--rapport" in sys.argv:
        _rapport(funn)

    igjen = ukvittert(funn)
    kvitterte = [f for f in funn if f.kvittert]

    # GRENSA I HISTORIKKEN, skrevet hver kjøring. Se
    # `kodeproveniens_ukjente()`.
    uten_proveniens = kodeproveniens_ukjente()
    if uten_proveniens:
        print(f"\n{len(uten_proveniens)} kilder har snapshots uten "
              f"kodeproveniens (blokkerer ikke):")
        for f in uten_proveniens:
            print(f"  {f}")

    if kvitterte:
        # Skrives ALLTID, ikke bare med --rapport. Exit 0 med kvitterte
        # funn skal aldri kunne leses som «ingen funn».
        print(f"\n{len(kvitterte)} funn er KVITTERT UT:")
        for f in kvitterte:
            print(f"  {f}")

    if not igjen:
        if kvitterte:
            print(f"\n{mappe}: ingen ukvitterte funn. De {len(kvitterte)} "
                  f"over står, og de er forstått — se {KVITTERING_DIR}.")
        else:
            print(f"\n{mappe}: ingenting å innvende.")
        return 0

    print(f"\n{len(igjen)} ukvitterte funn:")
    for f in igjen:
        print(f"  {f}")
    print("\nPUBLISERING STOPPET.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
