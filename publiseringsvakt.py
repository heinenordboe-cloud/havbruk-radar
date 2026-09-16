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
"""

from __future__ import annotations

import hashlib
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
    utdrag: str
    antall: int = 1

    def __str__(self) -> str:
        return f"{self.fil}: {self.slag} — {self.utdrag} (x{self.antall})"


# --------------------------------------------------- hvitelista

def _snapshotrammer() -> Iterable[pl.DataFrame]:
    """Nyeste snapshot per kilde, LEST GJENNOM `snapshot._les()`.

    Veien er ikke likegyldig. `_les()` er den ene døra, og den kjører
    `persondata.fjern_personformer()`. Bygges hvitelista med
    `pl.read_parquet()` i stedet, inneholder den nøyaktig de orgnumrene
    og navnene vakten finnes for å stoppe — og vakten ville godkjent dem.
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

    Tar NYESTE snapshot per kilde og ikke hele historikken. Det er en
    bevisst innstramming: en generator som viser et selskap som forsvant
    ut av registeret for et år siden, henter fra et sted vakten ikke
    kjenner, og det skal rapporteres framfor godkjennes. Trenger en
    visning eldre data, er utvidelsen her og skal begrunnes.
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


def gransk_tekst(tekst: str, orgnr_ok: set[str], navn_ok: set[str],
                 fil: str = "", tvetydige: Iterable[str] = ()) -> list[Funn]:
    """De tre prøvene på én filkropp. Returnerer funnene, tom = rent.

    `tvetydige` er kodene som også betyr noe annet i dataene — de søkes
    bare i en organisasjonsform-sammenheng. Standarden er tom, altså den
    strengeste lesningen: en kaller som ikke har målt noe, får alle
    kodene prøvd som hele ord.
    """
    funn: list[Funn] = []

    ukjente: dict[str, int] = {}
    for treff in NI_SIFFER.findall(tekst):
        if treff not in orgnr_ok:
            ukjente[treff] = ukjente.get(treff, 0) + 1
    for nr, antall in sorted(ukjente.items()):
        # Bare de fire siste sifrene i rapporten. Et funn skal kunne
        # finnes igjen i fila uten at rapporten selv blir en lekkasje.
        funn.append(Funn(fil, "ukjent_orgnr", f"…{nr[-4:]}", antall))

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

    if treff_form:
        funn.append(Funn(fil, "personform",
                         f"{sorted(set(treff_form))}", len(treff_form)))

    for navn in navn_i(tekst):
        if navn not in navn_ok:
            funn.append(Funn(fil, "ukjent_navn", _anonymiser(navn)))

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
    return [m.group(1).strip() for m in NAVNEMERKE.finditer(tekst)
            if m.group(1).strip()]


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

def gransk(mappe: Path) -> list[Funn]:
    """Alle filer under `mappe`. Tom liste = ingenting å innvende."""
    orgnr_ok, navn_ok = hviteliste()
    tvetydige = tvetydige_koder(_snapshotrammer())
    funn: list[Funn] = []
    for sti in sorted(p for p in mappe.rglob("*") if p.is_file()):
        rel = str(sti.relative_to(mappe))
        tekst = _tekst(sti)
        if tekst is None:
            # Ikke antatt trygg. En .parquet eller .xlsx ved siden av
            # sida er like publisert som HTML-en, og vakten sier at den
            # ikke har lest den framfor å tie.
            funn.append(Funn(rel, "ugranska", sti.suffix or "(uten endelse)"))
            continue
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
