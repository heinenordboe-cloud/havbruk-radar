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
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polars as pl

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import persondata, snapshot                      # noqa: E402
from core.paths import RAW_DIR                              # noqa: E402

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

# Felter der en verdi er et NAVN. Brukes til å bygge hvitelista.
NAVNEFELT = ("navn", "entity_name", "eier_navn", "tildelt_navn",
             "mottaker_navn", "lokalitet_navn", "prodomraade_navn")

# Felter der en verdi er et ORGNUMMER.
ORGNRFELT = ("eier_orgnr", "tildelt_orgnr", "mottaker_orgnr",
             "openLegalEntityNr", "legalEntityNrId")


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
    utdrag: str
    antall: int = 1

    def __str__(self) -> str:
        return f"{self.fil}: {self.slag} — {self.utdrag} (x{self.antall})"


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
    if sti.suffix.lower() not in TEKSTTYPER:
        return None
    try:
        return sti.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


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
                 fil: str = "", tvetydige: Iterable[str] = ()) -> list[Funn]:
    """De tre prøvene på én filkropp. Returnerer funnene, tom = rent.

    `tvetydige` er kodene som også betyr noe annet i dataene — de søkes
    bare i en organisasjonsform-sammenheng. Standarden er tom, altså den
    strengeste lesningen: en kaller som ikke har målt noe, får alle
    kodene prøvd som hele ord.
    """
    funn = _ukjente_orgnr(tekst, orgnr_ok, fil)

    tvetydige = {k.strip().upper() for k in tvetydige}
    treff_form: list[str] = []

    # De ENTYDIGE kodene: hele ordet, hvor som helst i fila.
    entydig = _personformmonster(persondata.PERSONFORMER - tvetydige)
    if entydig:
        treff_form += entydig.findall(tekst)

    # De TVETYDIGE: bare der feltnavnet står like foran.
    tvetydig = _personformmonster(tvetydige)
    if tvetydig:
        for m in re.finditer("organisasjonsform", tekst, re.I):
            vindu = tekst[m.end():m.end() + KONTEKSTVINDU]
            treff_form += tvetydig.findall(vindu)

    # De FELTMERKEDE cellene: samme regel som `gransk_csv` stiller på en
    # kolonne. En `organisasjonsform`-celle med `DA` er delt ansvar, og
    # den trenger ikke tekstvinduet over — merkingen SIER hva feltet er.
    ukjente_navn: dict[str, int] = {}
    for felt, verdi in felt_verdier(tekst):
        if felt in NAVNEFELT:
            if verdi not in navn_ok:
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

    # De gamle merkingene først, så kan den feltmerkede prøven la et navn
    # som alt er meldt være. Meldes det to ganger, er det fordi cellen
    # har to merkinger — og to funnrader om samme navn i samme fil er
    # støy, ikke informasjon.
    meldt: set[str] = set()
    for navn in navn_i(tekst):
        if navn not in navn_ok:
            funn.append(Funn(fil, "ukjent_navn", _anonymiser(navn)))
            meldt.add(navn)

    for navn, antall in sorted(ukjente_navn.items()):
        if navn not in meldt:
            funn.append(Funn(fil, "ukjent_navn", _anonymiser(navn), antall))

    return funn


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
                elif kolonne in NAVNEFELT and verdi not in navn_ok:
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


def gransk(mappe: Path) -> list[Funn]:
    """Alle filer under `mappe`, OG grunnlaget hvitelista bygges på.

    Grunnlagsfunnene er med i samme liste fordi de har samme følge: en
    hviteliste bygget på en feil erklæring er en hviteliste som gjør rede
    for noe den ikke har sett, og et grønt bygg på den er verre enn et
    rødt. Porten skiller dem ikke, og exit-koden dekker begge.
    """
    funn: list[Funn] = list(grunnlagsfunn())
    orgnr_ok, navn_ok = hviteliste()
    tvetydige = tvetydige_koder(_snapshotrammer())
    for sti in sorted(p for p in mappe.rglob("*") if p.is_file()):
        rel = str(sti.relative_to(mappe))
        tekst = _tekst(sti)
        if tekst is None:
            # Ikke antatt trygg. En .parquet eller .xlsx ved siden av
            # sida er like publisert som HTML-en, og vakten sier at den
            # ikke har lest den framfor å tie.
            funn.append(Funn(rel, "ugranska", sti.suffix or "(uten endelse)"))
            continue
        if sti.suffix.lower() in KOLONNETYPER:
            funn.extend(gransk_csv(tekst, orgnr_ok, navn_ok, fil=rel,
                                   avgrenser=KOLONNETYPER[sti.suffix.lower()]))
        else:
            funn.extend(gransk_tekst(tekst, orgnr_ok, navn_ok, fil=rel,
                                     tvetydige=tvetydige))
    return funn


def _rapport() -> None:
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
        _rapport()

    if not funn:
        print(f"\n{mappe}: ingenting å innvende.")
        return 0

    print(f"\n{len(funn)} funn:")
    for f in funn:
        print(f"  {f}")
    print("\nPUBLISERING STOPPET.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
