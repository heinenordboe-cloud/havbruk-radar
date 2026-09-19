"""Bygger den publiserte nettsiden fra snapshotene.

    python nettsted.py                     # bygger, gransker, exit 1 ved funn
    python nettsted.py --lokalitet 31397   # bare den ene siden
    python nettsted.py --uten-vakt         # bygg uten porten (utvikling)

Statisk HTML, Jinja2, ingen JavaScript. Tallene står i kildekoden.

## Hvorfor ikke Hugo, ikke Node, ikke en klientside-app

Samme argument som pinningen av `requirements.txt`: dette skal kjøre
uten tilsyn i to år. Et andre språk og en andre pakkebrønn er et andre
sted ting kan råtne, og en side som tegnes av JavaScript kan ikke
siteres, ikke arkiveres av Wayback, og ikke leses av noen som har slått
det av.

Målt før valget: Jinja2 rendrer 2000 sider à 200 tabellrader på 0,04
sekunder. Byggetid er ikke en begrensning, og det er derfor det enkleste
alternativet får vinne.

## Hvor siden skrives

`HAVBRUK_DATA_DIR/nettsted/`, ikke i kodrepoet. Samme begrunnelse som
`vis.py` og `analyse/ut/`: en generert fil som skrives om hver uke får
git til å vokse kvadratisk, og siden er en ren funksjon av snapshots som
alle er append-only. Den kan alltid regenereres.

## URL-ene er låst

`/lokalitet/<lokalitetsnummer>/`, registerets ID som slug, avsluttende
skråstrek, og tabellankere på formen `<kilde>-<hva>`. Begrunnelsen for
hvert ledd står i
`docs/beslutninger/2026-09-16-url-struktur.md`, og den er skrevet FØR
denne fila fantes — en URL er det eneste her som ikke kan gjøres om.

## Leseveien er `snapshot`, og det er en personvernsak

Alt leses gjennom `core/snapshot.py`, som kjører
`persondata.fjern_personformer()`. Følgen er at et foretak i SSB-sektor
8200 eller 2300 aldri får en side — ikke fordi generatoren husker å
hoppe over det, men fordi entiteten ikke finnes i ramma den leser fra.
Et URL-rom er en liste over hvem som finnes, selv om hver side er tom.

## Merkekonvensjonen er en avtale med publiseringsvakten

`publiseringsvakt.py` sin `ukjent_navn`-prøve ser bare navn en generator
har MERKET som navn — `data-navn` eller `class="navn|eier"`. Det står
som et åpent punkt i beslutningen 15.09: konvensjonen måtte bestemmes
før generatoren ble skrevet, «etterpå er det en omskriving».

Den er bestemt her, og den er brukt: lokalitetsnavnet er `data-navn`,
alle selskapsnavn er `class="eier"`. Skriver en framtidig mal et
selskapsnavn uten merket, er vakten blind for akkurat det navnet — og
det er en grense vakten selv dokumenterer, ikke en feil som oppstår
stille.

### Og for en FELT-VERDI-tabell er merkingen feltnavnet

De to merkingene over duger der kolonnen er kjent på forhånd. I
registertabellen og i endringstabellen er den ikke det: samme `<td>`
bærer `siste_rapport` i én rad og `eier_navn` i neste. En statisk klasse
ville merket alt som navn eller ingenting.

Fra 18.09.2026 bærer verdicellene i de to tabellene derfor
`data-felt="<feltnavn>"`, og `publiseringsvakt.felt_verdier()` leser
merkingen mot `NAVNEFELT` og mot personvernfeltene. Det er SAMME regel
`gransk_csv` har for en CSV — kolonneoverskriften er merkingen — og
feltnavnet er kildens eget, ikke en presentasjonsklasse vi har funnet
opp.

Endringstabellen var den som trengte det: cellene bærer changeloggens
`old_value`/`new_value`, altså verdier fra ELDRE snapshots enn dem
hvitelista bygges av. MÅLT 18.09.2026 sto 24 navneverdier der uten at
`ukjent_navn` kunne se én av dem. Se
`docs/beslutninger/2026-09-18-changeloggens-persondata-ligger-stille.md`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import publiseringsvakt                                    # noqa: E402
from core import changelog, diff, snapshot                 # noqa: E402
from core.contract import attribusjon_per_kilde            # noqa: E402
from core.paths import DATA_DIR                            # noqa: E402

MALER = ROOT / "maler"
UT = DATA_DIR / "nettsted"

# Hvor mange uker av lusetallserien som vises. Serien for OTERNESET er
# 764 uker; hele den er ikke en avgjørelse om URL-er eller markup, men om
# design, og design er utsatt. Ett år er nok til å svare på «hva har
# lusetallene vært» uten å ta et designvalg på forskudd.
#
# At resten IKKE er på siden står i tabellens caption sammen med hele
# seriens spenn. En side som viser et utsnitt uten å si at det er et
# utsnitt, lyver ved utelatelse.
LUSEUKER = 52

# Kildene en lokalitetsside bygger på. Rekkefølgen er lesningens.
SIDENS_KILDER = ("akvakultur", "eierskap", "eierskap_historikk", "lusetall")

# ---------------------------------------------------------------------
# VILKÅRENE
#
# Tabellen som sto her fram til 16.09.2026 er flyttet til
# `Source.attribusjon` i core/contract.py. Grunnen står i
# docs/beslutninger/2026-09-16-attribusjon-folger-kilden.md: vilkåret er
# en egenskap ved KILDEN, og en liste hos publiseringsleddet kunne bli
# stående uendret når en ny kilde kom til. Den manglende setningen ville
# vist seg først den dagen noen publiserte.
#
# Det som er igjen her er POLITIKKEN, og den hører hjemme her: en
# UBELAGT kilde kan brukes i analyse og dokumentasjon, men skal ikke
# bære en publisert visning. Kjernen sier hva som er erklært; hva det
# får lov til å bety er publiseringsleddets sak.


def kildevilkaar() -> dict[str, tuple[str, ...] | None]:
    """{kildenavn: setninger eller None} for alle kilder repoet har.

    Bygget av `registry.discover()` ved hvert kall og ikke bufret: en
    buffer ville vært et andre sted sannheten kan bli stående gammel, og
    det er nøyaktig feilen flyttingen retter.
    """
    from core import registry
    return attribusjon_per_kilde(registry.discover())


# Lisens-URL per kilde, for JSON-LD. Bare der versjonen er BELAGT i
# lisenskjeden. Fiskeridirektoratets side sier «NLOD» uten versjon, og en
# URL til 2.0 ville påstått en versjon ingen har gått god for.
LISENS_URL = {
    "eierskap": "https://data.norge.no/nlod/no/2.0",
    "eierskap_historikk": "https://data.norge.no/nlod/no/2.0",
    "enhetsregisteret": "https://data.norge.no/nlod/no/2.0",
}

UTGIVER = {
    "akvakultur": "Fiskeridirektoratet",
    "eierskap": "Fiskeridirektoratet",
    "eierskap_historikk": "Fiskeridirektoratet",
    "lusetall": "BarentsWatch",
    "sjotemperatur": "BarentsWatch",
    "enhetsregisteret": "Brønnøysundregistrene",
}


class UbelagtKilde(Exception):
    """En side bruker en kilde uten dokumentert attribusjonsvilkår.

    Kastes FØR rendering, ikke etter. En side som er skrevet til disk er
    en side noen kan komme til å publisere, og det er lettere å la være å
    skrive den enn å huske å slette den.
    """


def attribusjon(kilder, vilkaar=None) -> list[str]:
    """Setningene som må stå synlig, for de kildene siden faktisk bruker.

    Deduplisert med rekkefølgen intakt: `eierskap` og
    `eierskap_historikk` krever de samme to setningene, og den som leser
    bunnteksten skal ikke lure på hvorfor det står to like.

    Kaster på UBELAGT — og på et kildenavn ingen kilde skriver under.
    De to er samme sak: i begge tilfeller er det ingen som har sagt hva
    vilkåret er.

    `vilkaar` kan sendes inn av en test. Standarden er registeret.
    """
    indeks = kildevilkaar() if vilkaar is None else vilkaar
    ut: list[str] = []
    for kilde in kilder:
        if kilde not in indeks:
            raise UbelagtKilde(
                f"{kilde} er ikke et kildenavn noen Source skriver under. "
                f"Attribusjonen bor på kilden (Source.attribusjon); et navn "
                f"uten kilde har ingen som har gått god for vilkåret. "
                f"Skriver kilden under flere navn, se Source.skriver_ogsaa.")
        if indeks[kilde] is None:
            raise UbelagtKilde(
                f"{kilde} er UBELAGT: vilkåret er lett etter og ikke funnet "
                f"(se docs/LISENSKJEDE.md). Siden bygges ikke. Lukk luken "
                f"med et spørsmål til utgiveren, ikke med mer kode.")
        for setning in indeks[kilde]:
            if setning not in ut:
                ut.append(setning)
    return ut


# --------------------------------------------------------- lesing


def _pivot(ramme: pl.DataFrame) -> dict[str, dict[str, str]]:
    """{entity_id: {felt: verdi}} for én snapshotramme.

    Snapshotformatet er langt — én rad per (entitet, felt) — og en
    HTML-mal vil ha det bredt. Pivoteringen skjer her og ikke i malen:
    en mal som regner er en mal ingen kan teste.
    """
    ut: dict[str, dict[str, str]] = defaultdict(dict)
    for eid, felt, verdi in ramme.select(["entity_id", "field", "value"]).iter_rows():
        ut[str(eid)][str(felt)] = verdi
    return ut


def _siste(kilde: str) -> tuple[str, dict[str, dict[str, str]]]:
    """Nyeste snapshot for kilden, pivotert. Går via `snapshot.versjoner()`
    fordi den kjenner regelen om at `.10` sorterer etter `.2`."""
    dato = snapshot.siste_dato(kilde)
    if dato is None:
        raise SystemExit(f"{kilde}: ingen snapshots i {DATA_DIR}")
    versjonene = snapshot.versjoner(kilde, dato)
    return dato, _pivot(versjonene[-1][1])


def _overforinger() -> dict[str, dict[str, str]]:
    """Hele overføringshistorikken, slått sammen over ALLE versjoner.

    Dette er den ene lesemåten som er riktig for `eierskap_historikk`, og
    den er ikke åpenbar: `<år>-12-31.parquet` (v1) er KJENT
    underfiltrert og mangler 677 av 2611 overføringer — fortrinnsvis de
    OPPKJØPTE selskapene, altså nøyaktig hendelsene serien finnes for.

    En leser som tar «siste fil» får riktig svar her, men bare
    tilfeldigvis: v2 er en ekte overmengde av v1. Den dagen en versjon
    restaterer bare en DEL, gir «siste fil» feil svar igjen. Se
    docs/KILDE-EIERSKAP.md punkt 1.
    """
    ut: dict[str, dict[str, str]] = defaultdict(dict)
    for dato in snapshot.datoer("eierskap_historikk"):
        for _nr, ramme in snapshot.versjoner("eierskap_historikk", dato):
            for eid, felt, verdi in ramme.select(
                    ["entity_id", "field", "value"]).iter_rows():
                ut[str(eid)][str(felt)] = verdi
    return ut


# ------------------------------------------------------- FELLESLESINGEN
#
# `bygg_lokalitet()` er skrevet for ÉN side, og den leser da alt den
# trenger selv. Det er riktig for én side og umulig for 1782: målt
# 17.09.2026 koster den 9,06 s, hvorav 6,37 s er hele changeloggen og
# 2,59 s er alle 764 lusetallsnapshots — to lesinger som ikke avhenger
# av hvilken lokalitet det spørres om. Naivt over 1782 sider er det
# **4,5 timer**.
#
# `Felles` er de lesingene gjort ÉN gang. Det er ikke en optimalisering
# av den trege delen — den trege delen er like treg, og står uendret i
# `bygg_lokalitet()` når den kalles alene. Det er forskjellen på en
# byggejobb som kan kjøre og en som ikke kan.
#
# Én side alene koster fortsatt 9 s. Det er MENINGEN at det synes.


@dataclass(frozen=True)
class Felles:
    """Alt som er likt for hver side, lest én gang.

    Indeksene er dicts og ikke polars-filtre med vilje: et filter over en
    ramme med 985 031 rader er billig én gang og dyrt 1782 ganger, og
    det var nettopp den formen som ga 4,5 timer.
    """

    akva_dato: str
    akva: dict[str, dict[str, str]]
    eierskap_dato: str
    eierskap: dict[str, dict[str, str]]
    tillatelser_per_lokalitet: dict[str, set[str]]
    overforinger_per_tillatelse: dict[str, list[dict]]
    lusserier: dict[str, list[dict]]
    lusetall_snapshots: list[str]
    registerendringer: dict[str, list[dict]]
    maaleserierader: dict[str, int]
    dekning_fra: list[dict]
    vilkaar: dict


def les_felles() -> Felles:
    """Leser snapshots og changelog én gang. Tar ~14 s.

    Rekkefølgen er lesningens og ikke tilfeldig: lusetallindeksen er den
    som koster minne (målt 1,1 GB for 1 322 004 ukerader over 2705
    lokaliteter), og den bygges sist så resten er ferdig hvis den feller
    maskinen.
    """
    akva_dato, akva = _siste("akvakultur")
    eierskap_dato, eierskap = _siste("eierskap")

    till_per_lok: dict[str, set[str]] = defaultdict(set)
    for nr, d in eierskap.items():
        for lok in (d.get("lokaliteter") or "").split(";"):
            if lok.strip():
                till_per_lok[lok.strip()].add(nr)

    ovf_per_till: dict[str, list[dict]] = defaultdict(list)
    for o in _overforinger().values():
        ovf_per_till[o.get("tillatelse_nr", "")].append(o)

    # Changeloggen én gang. `bevegelse()` har alt filtrert bort
    # utvalgsutvidelse og revisjon — se docs/ARKITEKTUR.md.
    alle = changelog.merk_utvalgsutvidelse(changelog.les_alt())
    beveg = diff.bevegelse(alle)
    maaleserie = sorted(MAALESERIER)

    register: dict[str, list[dict]] = defaultdict(list)
    for r in (beveg.filter(~pl.col("source").is_in(maaleserie))
              .sort("observed_at", descending=True).iter_rows(named=True)):
        register[str(r["entity_id"])].append(r)

    maalt: dict[str, int] = defaultdict(int)
    for eid in beveg.filter(pl.col("source").is_in(maaleserie))["entity_id"]:
        maalt[str(eid)] += 1

    serier: dict[str, list[dict]] = defaultdict(list)
    lusedatoer = snapshot.datoer("lusetall")
    for dato in lusedatoer:
        aar, ukenr = _isouke(dato)
        for _nr, ramme in snapshot.versjoner("lusetall", dato):
            per_lok: dict[str, dict[str, str]] = defaultdict(dict)
            for eid, felt, verdi in ramme.select(
                    ["entity_id", "field", "value"]).iter_rows():
                per_lok[str(eid)][str(felt)] = verdi
            for eid, raa in per_lok.items():
                uke = {felt: (raa.get(felt) or "") for felt in LUSEFELT}
                uke["dato"] = dato
                uke["iso_aar"] = str(aar)
                uke["iso_uke"] = f"{ukenr:02d}"
                serier[eid].append(uke)

    return Felles(
        akva_dato=akva_dato, akva=akva,
        eierskap_dato=eierskap_dato, eierskap=eierskap,
        tillatelser_per_lokalitet=dict(till_per_lok),
        overforinger_per_tillatelse=dict(ovf_per_till),
        lusserier=dict(serier),
        lusetall_snapshots=lusedatoer,
        registerendringer=dict(register),
        maaleserierader=dict(maalt),
        dekning_fra=_dekning_fra(),
        vilkaar=kildevilkaar(),
    )


def _isouke(dato: str) -> tuple[int, int]:
    """(ISO-år, ISO-uke) av en dato.

    Lusetall daterer hver uke til MANDAGEN i ISO-uka
    (docs/KILDE-LUSETALL.md), så ukenummeret er en annen skriving av den
    samme datoen og ikke et nytt tall.

    ISO-året, ikke kalenderåret: 2019-12-30 er mandag i uke 1 av 2020, og
    et kalenderår i den kolonnen ville gitt «2019 uke 01» ved siden av
    «2019 uke 52» — to uker som ligger ett år fra hverandre.
    """
    aar, uke, _ = dt.date.fromisoformat(dato).isocalendar()
    return aar, uke


# Feltene lusetabellen viser, i kolonnerekkefølge. Eksplisitt liste og
# ikke «alt kilden har»: en kilde som legger til et felt skal ikke endre
# en publisert tabell uten at noen har bestemt det.
LUSEFELT = ("voksne_hunnlus", "lus_er_rapportert", "har_laksefisk",
            "brakklagt", "har_medikamentell_behandling",
            "har_mekanisk_fjerning", "har_rensefisk")

# Det som står i cellen når kilden ikke har noen verdi. Ikke «0», og
# ikke blankt.
#
# MÅLT 16.09.2026 på OTERNESET: 207 av 764 uker har ingen
# `voksne_hunnlus`-rad, og i alle 207 er `lus_er_rapportert` False —
# lokaliteten var brakklagt. Null uker har et tall uten å være
# rapportert. Feltet er altså FRAVÆRENDE, ikke null, og det er nøyaktig
# skillet `lus_er_rapportert` finnes for: «gikk til null» og «sluttet å
# rapportere» betyr helt forskjellige ting (se F10 og
# docs/KILDE-ENHETSREGISTERET.md om `ansatte_er_registrert`).
#
# En tom celle ville latt leseren gjette. En 0 ville vært en påstand
# kilden ikke har gjort.
INGEN_VERDI = "–"

# Kildens boolske verdier, slik de skal leses av et menneske.
#
# Kartet er EKSAKT og ikke en sannhetsprøve: en verdi som ikke står her
# går gjennom uendret. En kilde som en dag sender «true» i små
# bokstaver, eller «1», skal vises som det den er, ikke oversettes av et
# `if verdi` som gjør «0» og «» og «nei» til det samme.
#
# «nei» og «–» er IKKE det samme, og det er hele grunnen til at kartet
# ikke har en standardverdi: «nei» er kilden som sier nei, «–» er kilden
# som ikke sier noe.
JANEI = {"True": "ja", "False": "nei"}


def _lusserie(loknr: str) -> list[dict]:
    """Hele lusetallserien for én lokalitet, eldst først.

    Leser hvert ukesnapshot og plukker den ene lokaliteten. Det er
    dyrere enn å lese én bred fil, men det finnes ingen bred fil — og
    det er den samme døra alt annet går gjennom.

    Hver uke får ALLE feltene i `LUSEFELT`, med tom streng der kilden
    tidde. Utfyllingen skjer her og ikke i malen: `StrictUndefined` gjør
    en manglende nøkkel til en feil i stedet for en tom celle, og det er
    riktig — men da må den som leser dataene bestemme hva fraværet BETYR,
    og det kan ikke en HTML-mal.

    KILDENS EGNE VERDIER, uoversatt. `True`/`False` blir ikke til
    `ja`/`nei` her, og fravær blir ikke til «–». Det er `til_visning()`
    som gjør det, og skillet er ikke pedanteri: CSV-en skal bære det
    kilden sa, og HTML-en skal bære det et menneske kan lese. Skjedde
    oversettelsen her, ville CSV-en vært en gjengivelse av VÅR lesning
    — og BarentsWatch-vilkåret sier uttrykkelig at datainnholdet ikke
    skal endres.
    """
    rader = []
    for dato in snapshot.datoer("lusetall"):
        for _nr, ramme in snapshot.versjoner("lusetall", dato):
            sub = ramme.filter(pl.col("entity_id") == loknr)
            if sub.is_empty():
                continue
            raa = {str(f): v for f, v in
                   sub.select(["field", "value"]).iter_rows()}
            uke = {felt: (raa.get(felt) or "") for felt in LUSEFELT}
            aar, ukenr = _isouke(dato)
            uke["dato"] = dato
            uke["iso_aar"] = str(aar)
            uke["iso_uke"] = f"{ukenr:02d}"
            rader.append(uke)
    return rader


def til_visning(rader: list[dict]) -> list[dict]:
    """Kildens verdier til noe et menneske leser. Rører ikke `rader`.

    To oversettelser, og begge er presentasjon og ikke data:

      * `True`/`False` -> `ja`/`nei`, fordi siden er på norsk.
      * tom -> «–», fordi en tom celle i en HTML-tabell ikke kan skilles
        fra en feil i malen.

    `INGEN_VERDI` er ikke «0» og ikke blankt. Målt 16.09.2026 på
    OTERNESET: 207 av 764 uker har ingen `voksne_hunnlus`-rad, og i alle
    207 er `lus_er_rapportert` False — lokaliteten var brakklagt. Feltet
    er FRAVÆRENDE, ikke null, og det er nøyaktig skillet
    `lus_er_rapportert` finnes for.
    """
    ut = []
    for rad in rader:
        vist = dict(rad)
        for felt in LUSEFELT:
            verdi = rad.get(felt, "")
            vist[felt] = INGEN_VERDI if verdi == "" else JANEI.get(verdi, verdi)
        vist["uke"] = f"{rad['iso_aar']} uke {rad['iso_uke']}"
        ut.append(vist)
    return ut


# ------------------------------------------------- hva er en endring
#
# Changeloggen er prosjektets unike bidrag, og nettopp derfor må det stå
# hva den betyr HER. På en lokalitetsside er ikke alt som ligger i
# changeloggen en «endring» i den forstand en leser mener.
#
# REGISTERKILDER er kilder der en rad betyr at noen har fattet en
# beslutning eller rettet en oppføring: en tillatelse trukket, en
# artsbegrensning endret, en eier byttet. Det er hendelser.
#
# MÅLESERIER er kilder som leverer et nytt tall hver uke. Hvert nye tall
# er en changelog-rad hos oss, men ingen har bestemt noe — det er bare
# neste måling. For OTERNESET er det 1284 slike rader mot 6
# registerendringer. Tas de med, drukner hendelsen i serien.
#
# Skillet er en LISTE og ikke en heuristikk, av samme grunn som
# `changelog.TAUSHETSKILDER` er det: en kilde som ikke står her behandles
# som en registerkilde, altså vises, og usikkerhet ser ut som usikkerhet
# framfor å forsvinne.
MAALESERIER = frozenset({"lusetall", "sjotemperatur"})

# Kildene hvis changelog-rader kan vises via en TILLATELSE på
# lokaliteten. Endringen gjelder tillatelsen og ikke lokaliteten, og
# koblingen er `entity_id` == tillatelsesnummeret.
ENDRINGER_VIA_TILLATELSE = frozenset({"eierskap"})

# `eierskap_historikk` står UTTRYKKELIG IKKE over, og utelatelsen er en
# BESLUTNING — ikke en forglemmelse og ikke noe som skal rettes av den
# neste som leser filteret.
#
# Fram til 18.09.2026 sto kilden i lista, og den var DØD KODE. MÅLT over
# hele changeloggen: `eierskap_historikk` har `entity_id` på formen
# `F-A-0034|2007000034` — tillatelse|journalnr, fordi en overføring er én
# entitet og en tillatelse har mange. **30 104 av 30 104 rader har
# rørtegnet**, så `entity_id in tillatelser` kunne treffe 0. Klausulen
# navnga en kilde den ikke kunne matche.
#
# Å «rette» den er ikke en opprydding — det er en publiseringsbeslutning
# med et målt innhold: 30 104 rader ville begynt å nå sidene, og to av
# dem bærer navnet på et DA (sektor 2300 etter dagens grense) hentet inn
# 02.09, før grensa flyttet seg. De kan ikke fjernes av lesedøra, som
# leser `organisasjonsform` og `institusjonell_sektorkode` — en
# overføringsrad har `mottaker_type` i pub-aquas vokabular og ingen av
# de to.
#
# Tre ting måtte vært på plass før kilden kan vises:
#
#   1. En uttrykkelig kobling. Tillatelsesdelen av den sammensatte
#      id-en må splittes ut med vilje, ikke matche ved et sammentreff.
#   2. Merkingen fra publiseringsvakten. PÅ PLASS fra 18.09.2026:
#      endringstabellens celler bærer `data-felt`, og `ukjent_navn` ser
#      dem. Uten den var en visning usynlig for porten.
#   3. En avklaring av de to DA-navnene — de er en åpen beslutning, se
#      notatet under.
#
# docs/beslutninger/2026-09-18-changeloggens-persondata-ligger-stille.md
ENDRINGER_UTELATT = frozenset({"eierskap_historikk"})


def _endringer(loknr: str, tillatelser: list[str]) -> tuple[list[dict], int]:
    """(registerendringer nyest først, antall måleserierader).

    Tar med endringer som gjelder lokaliteten SELV og endringer som
    gjelder en TILLATELSE på den. Det andre er en indirekte kobling, og
    den er med fordi et eierskifte er noe av det viktigste som kan skje
    med en lokalitet — men raden gjelder tillatelsen, og det står i
    kolonnen «Gjelder» framfor å pusses bort.

    `diff.bevegelse()` er allerede kjørt: `utvalgsutvidelse` og
    `revidert` er ikke bevegelse. Se docs/ARKITEKTUR.md.

    Hvilke kilder som kan komme inn via en tillatelse står i
    `ENDRINGER_VIA_TILLATELSE`, og hvilken som uttrykkelig ikke kan, i
    `ENDRINGER_UTELATT`. Lista står der og ikke her fordi
    `_endringer_av_indeks()` skal svare det samme.
    """
    alle = changelog.merk_utvalgsutvidelse(changelog.les_alt())
    beveg = diff.bevegelse(alle)

    mine = beveg.filter(
        (pl.col("entity_id") == loknr)
        | ((pl.col("source").is_in(sorted(ENDRINGER_VIA_TILLATELSE)))
           & pl.col("entity_id").is_in(tillatelser))
    )

    maaleserie = mine.filter(pl.col("source").is_in(sorted(MAALESERIER))).height

    register = mine.filter(~pl.col("source").is_in(sorted(MAALESERIER)))
    rader = [_endringsrad(r, loknr) for r in
             register.sort("observed_at", descending=True).iter_rows(named=True)]
    return rader, maaleserie


def _endringsrad(r: dict, loknr: str) -> dict:
    """Én changelog-rad til én tabellrad. Ett sted, to kallere.

    `gjelder` skiller endringer om LOKALITETEN fra endringer om en
    TILLATELSE på den. Det andre er en indirekte kobling, og den står i
    en kolonne framfor å pusses bort — et eierskifte er noe av det
    viktigste som kan skje med en lokalitet, men raden gjelder
    tillatelsen.
    """
    return {
        "dato": str(r["observed_at"]),
        "gjelder": ("lokaliteten" if str(r["entity_id"]) == loknr
                    else f"tillatelse {r['entity_id']}"),
        "kilde": str(r["source"]),
        "felt": str(r["field"]),
        "fra": r["old_value"] if r["old_value"] is not None else "",
        "til": r["new_value"] if r["new_value"] is not None else "",
    }


# --------------------------------------------------------- sida


def _endringer_av_indeks(loknr: str, tillatelser: list[str],
                         felles: Felles) -> tuple[list[dict], int]:
    """Samme svar som `_endringer()`, men av en ferdig indeks.

    To funksjoner som skal si det samme er formen F6 og F7 hadde, og
    derfor deler de radformen: `_endringsrad()` er den ene stedet en
    changelog-rad blir til en tabellrad. Av samme grunn leser de
    kildelista fra `ENDRINGER_VIA_TILLATELSE` framfor å ha den hver for
    seg — den utelatte kilden skal ikke kunne bli utelatt i bare én av
    de to.
    """
    rader = list(felles.registerendringer.get(loknr, ()))
    for nr in tillatelser:
        rader += [r for r in felles.registerendringer.get(nr, ())
                  if r["source"] in ENDRINGER_VIA_TILLATELSE]
    rader.sort(key=lambda r: str(r["observed_at"]), reverse=True)
    return ([_endringsrad(r, loknr) for r in rader],
            felles.maaleserierader.get(loknr, 0))


def _dekning_fra() -> list[dict]:
    """Fra når changeloggen faktisk dekker hver registerkilde.

    ÉN dato for hele tabellen ville vært feil, og feil på den stille
    måten. Registerkildene startet ikke samtidig: `akvakultur` har
    snapshots fra 17.08.2026, `eierskap` fra 02.09.2026. Et eierskifte i
    mellomtiden finnes ikke i loggen vår, og en overskrift som sa «6
    endringer siden 17.08» ville latt leseren tro at det gjorde det.

    `eierskap_historikk` står ikke her: den er datert etter ÅRET
    overføringen ble journalført (2006-12-31 og utover), ikke etter når
    vi hentet den, så «fra 2006» ville vært en påstand om vår egen
    dekning som ikke stemmer. Overføringstabellen bærer sin egen
    tidsakse.
    """
    ut = []
    for kilde in ("akvakultur", "eierskap"):
        datoer = snapshot.datoer(kilde)
        if datoer:
            ut.append({"kilde": kilde, "fra": min(datoer)})
    return ut


def bygg_lokalitet(loknr: str, felles: Felles | None = None) -> dict:
    """Alle dataene én lokalitetsside trenger. Ingen HTML her.

    `felles` er de delte lesingene gjort på forhånd — se `les_felles()`.
    Uten den leser funksjonen alt selv, og da koster ett kall 9 s. Det er
    riktig for én side og umulig for 1782, og forskjellen skal være
    synlig i kallet framfor gjemt i en buffer.

    Resultatet er det SAMME uansett vei. `test_batch_gir_samme_side_som_enkelt`
    håndhever det: to veier til samme side som kan svare ulikt, er formen
    F6 og F7 hadde.
    """
    if felles is None:
        akva_dato, akva = _siste("akvakultur")
    else:
        akva_dato, akva = felles.akva_dato, felles.akva
    if loknr not in akva:
        raise SystemExit(f"lokalitet {loknr} finnes ikke i "
                         f"akvakultur-snapshotet {akva_dato}")
    a = akva[loknr]

    if felles is None:
        eierskap_dato, eierskap = _siste("eierskap")
        mine_till = {
            nr: d for nr, d in eierskap.items()
            if loknr in [x.strip() for x in (d.get("lokaliteter") or "").split(";")]
        }
        ovf = list(_overforinger().values())
        serie = _lusserie(loknr)
        endringer, maaleserie_rader = _endringer(loknr, sorted(mine_till))
    else:
        eierskap_dato, eierskap = felles.eierskap_dato, felles.eierskap
        mine_till = {nr: eierskap[nr] for nr in
                     felles.tillatelser_per_lokalitet.get(loknr, ())}
        ovf = [o for nr in mine_till
               for o in felles.overforinger_per_tillatelse.get(nr, ())]
        serie = felles.lusserier.get(loknr, [])
        endringer, maaleserie_rader = _endringer_av_indeks(
            loknr, sorted(mine_till), felles)

    overforinger = sorted(
        (o for o in ovf if o.get("tillatelse_nr") in mine_till),
        key=lambda o: (o.get("journal_dato", ""), o.get("tillatelse_nr", "")),
    )

    return {
        "loknr": loknr,
        "navn": a.get("navn", ""),
        "kommune": a.get("kommune", ""),
        "fylke": a.get("fylke", ""),
        "po_kode": a.get("prodomraade_kode", ""),
        "po_navn": a.get("prodomraade_navn", ""),
        "breddegrad": a.get("breddegrad", ""),
        "lengdegrad": a.get("lengdegrad", ""),
        "akva_dato": akva_dato,
        "eierskap_dato": eierskap_dato,
        # Sortert alfabetisk og ikke i kildens rekkefølge: kildens
        # rekkefølge er en tilfeldighet i et JSON-svar, og en tabell som
        # stokker om på seg selv mellom to kjøringer er en tabell ingen
        # kan diffe.
        "register": sorted(a.items()),
        "tillatelser": [
            {
                "nr": nr,
                "eier_navn": d.get("eier_navn", ""),
                "eier_orgnr": d.get("eier_orgnr", ""),
                "type": d.get("tillatelse_type", ""),
                "kapasitet": d.get("kapasitet", ""),
                "kapasitet_enhet": d.get("kapasitet_enhet", ""),
                "tildelt_dato": (d.get("tildelt_tid") or "")[:10],
                "tildelt_navn": d.get("tildelt_navn", ""),
            }
            for nr, d in sorted(mine_till.items())
        ],
        "overforinger": [
            {
                "dato": o.get("journal_dato", ""),
                "tillatelse": o.get("tillatelse_nr", ""),
                "mottaker_navn": o.get("mottaker_navn", ""),
                "mottaker_orgnr": o.get("mottaker_orgnr", ""),
                "rekkefolge": o.get("rekkefolge", ""),
            }
            for o in overforinger
        ],
        "lus": til_visning(list(reversed(serie[-LUSEUKER:]))),
        "lus_fra": serie[0]["dato"] if serie else "",
        "lus_til": serie[-1]["dato"] if serie else "",
        "lus_uker": len(serie),
        # Hvor mange ukesnapshots vi HAR. Uten det kan en side med null
        # uker ikke skille «vi har ikke sett etter» fra «vi har sett i
        # 764 uker og ikke funnet den».
        "lusetall_snapshots": (len(felles.lusetall_snapshots) if felles
                               else len(snapshot.datoer("lusetall"))),
        # Telles her og skrives ikke inn i malen for hånd. Et tall i en
        # mal er et tall som ikke oppdateres når dataene gjør det, og da
        # er siden usann neste uke uten at noen rørte den.
        "lus_uten_tall": sum(1 for u in serie if u["voksne_hunnlus"] == ""),
        # Hele serien, urørt. CSV-en skrives av den; tabellen viser
        # slutten av den. At de to kommer fra SAMME liste er det som
        # gjør at de ikke kan bli uenige.
        "lus_serie": serie,
        "csv_filnavn": CSV_FILNAVN,
        "endringer": endringer,
        "maaleserie_rader": maaleserie_rader,
        "dekning_fra": (felles.dekning_fra if felles else _dekning_fra()),
    }


# ---------------------------------------------------- den siterbare CSV-en
#
# Tabellen på siden viser 52 uker. Serien er 764. Hele den skal kunne
# siteres, og da må den ligge på en adresse noen kan lenke til — ikke
# bare i et snapshot i et privat repo.
#
# Filnavnet er `<kilde>.csv` i lokalitetens egen mappe. Begrunnelsen for
# akkurat den adressen står i
# docs/beslutninger/2026-09-16-url-struktur.md punkt 8.

# Filnavnet, ett sted. Det står i tre: på disk, i lenka fra sida, og i
# `contentUrl` i JSON-LD-en. Tre strenger som skal si det samme er
# formen F6 og F7 hadde.
CSV_FILNAVN = "lusetall.csv"

CSV_KOLONNER = ("lokalitetsnummer", "dato", "iso_aar", "iso_uke") + LUSEFELT


def csv_kommentar(lok: dict, setninger: list[str], bygget: str) -> list[str]:
    """Hodet som gjør CSV-en selvstendig. Uten `#`-prefiks — det settes på.

    ## Hvorfor i FILA og ikke i en sidecar

    Alternativet var en `lusetall.csv.txt` ved siden av, og det ble
    forkastet: en sidecar er borte i det øyeblikket noen laster ned CSV-en
    alene, som er nøyaktig det man gjør med en CSV. Et vilkår som bare er
    oppfylt så lenge to filer holder sammen, er et vilkår som svikter
    stille — og BarentsWatch krever synlighet for SLUTTBRUKER, ikke for
    den som fant begge filene.

    Prisen er reell og skal ikke pusses bort: RFC 4180 kjenner ingen
    kommentarsyntaks. En leser som ikke hopper over `#`-linjene får dem
    som datarader, og den aller første blir lest som kolonneoverskrifter.
    Derfor sier siste kommentarlinje hvordan fila skal leses, og derfor
    står den der og ikke bare i et notat.

    Byttehandelen er: en leser som ikke leser hodet får en synlig feil
    med én gang, mens en sidecar som blir borte gir en usynlig mangel som
    varer. Den første feilen er den billigste.

    Attribusjonen HENTES fra kilden, ikke skrives her. Samme indeks som
    bunnteksten på siden bruker, så de to kan ikke bli uenige.
    """
    linjer = [
        f"Voksne hunnlus per fisk for akvakulturlokalitet "
        f"{lok['loknr']} {lok['navn']}, {lok['kommune']}.",
    ]
    # MÅLT 17.09.2026: 4 av 1782 lokaliteter har ingen uker. Første
    # utgave skrev «Ukentlig serie  til , 0 uker» — to tomme spenn og en
    # påstand om en serie som ikke finnes.
    if lok["lus_uker"]:
        linjer += [
            f"Ukentlig serie {lok['lus_fra']} til {lok['lus_til']}, "
            f"{lok['lus_uker']} uker. Datoen er MANDAG i ISO-uka.",
            "",
        ]
    else:
        linjer += [
            f"INGEN UKER. Lokaliteten finnes ikke i noen av de "
            f"{lok['lusetall_snapshots']} ukesnapshotene vi har.",
            "Fila har hode og null rader med vilje: det er et svar, og "
            "404 er det ikke.",
            "",
        ]
    linjer += setninger
    linjer += [""]
    if lok["lus_uker"]:
        linjer += [
            "Tom voksne_hunnlus betyr at kilden ikke oppgir noe tall - ikke "
            "at tallet var null.",
            "Se lus_er_rapportert paa samme rad. "
            f"{lok['lus_uten_tall']} av {lok['lus_uker']} uker er slik.",
            "",
        ]
    linjer += [
        f"Bygget {bygget} av havbruk-radar fra snapshots. Tallene er "
        f"gjengitt uendret fra kilden.",
        "Kommentarlinjer starter med #. Les f.eks. med "
        "polars.read_csv(..., comment_prefix=\"#\").",
    ]
    return linjer


def csv_tekst(lok: dict, setninger: list[str], bygget: str) -> str:
    """Hele CSV-en som tekst: kommentarhode, overskriftsrad, 764 rader.

    `\r\n` og `QUOTE_MINIMAL` er `csv`-modulens standard og RFC 4180s
    form. Den beholdes framfor å pyntes til `\n`: en fil som skal
    siteres bør være den formen flest verktøy forventer, og vår
    lesbarhet i en terminal er ikke et argument mot det.
    """
    ut = io.StringIO()
    for linje in csv_kommentar(lok, setninger, bygget):
        ut.write(f"# {linje}\n" if linje else "#\n")

    skriver = csv.writer(ut)
    skriver.writerow(CSV_KOLONNER)
    for rad in lok["lus_serie"]:
        skriver.writerow([lok["loknr"]] + [rad.get(k, "")
                                           for k in CSV_KOLONNER[1:]])
    return ut.getvalue()


def jsonld(lok: dict) -> str:
    """schema.org/Dataset for lokalitetssiden.

    Tre valg som er verdt å begrunne:

    **Ingen `url`.** Domenet finnes ikke ennå, og en absolutt URL med et
    påfunnet vertsnavn ville vært en påstand om noe som ikke er avgjort.
    `identifier` bærer den ekte identiteten i stedet — `siteNr`, med
    `propertyID` som sier hvilket register nummeret tilhører.

    **`isBasedOn` per kilde, ikke én `license` for hele siden.** Kildene
    har hver sin lisensgiver og hver sin attribusjonsplikt, og en enkelt
    `license`-URL på toppnivå ville skjult at de er tre. Bare kilder der
    lisensVERSJONEN er belagt får en URL — Fiskeridirektoratets side sier
    «NLOD» uten versjon, og en lenke til 2.0 ville påstått en versjon
    ingen har gått god for.

    **`temporalCoverage` er MÅLT**, ikke satt til «siden 2012»: det er
    spennet i lusetallserien for akkurat denne lokaliteten.
    """
    indeks = kildevilkaar()
    kilder = []
    for kilde in SIDENS_KILDER:
        node = {
            "@type": "Dataset",
            "name": kilde,
            "creditText": (indeks.get(kilde) or ("",))[0],
        }
        if kilde in UTGIVER:
            node["provider"] = {"@type": "Organization", "name": UTGIVER[kilde]}
        if kilde in LISENS_URL:
            node["license"] = LISENS_URL[kilde]
        kilder.append(node)

    data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"Lokalitet {lok['loknr']} {lok['navn']} — "
                f"registerdata, eierskap og lusetall",
        "description": (
            f"Sammenstilte offentlige registerdata om akvakulturlokalitet "
            f"{lok['loknr']} {lok['navn']} i {lok['kommune']}: "
            f"registeropplysninger, hvem som eier tillatelsene og siden når, "
            f"ukentlige lusetall, og hva som har endret seg i registrene."),
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "Fiskeridirektoratets lokalitetsnummer (siteNr)",
            "value": lok["loknr"],
        },
        "inLanguage": "nb",
        "dateModified": lok["akva_dato"],
        "isBasedOn": kilder,
        "creator": {"@type": "Organization", "name": "havbruk-radar"},
    }
    if lok["lus_fra"]:
        data["temporalCoverage"] = f"{lok['lus_fra']}/{lok['lus_til']}"
    if lok["breddegrad"] and lok["lengdegrad"]:
        data["spatialCoverage"] = {
            "@type": "Place",
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": lok["breddegrad"],
                "longitude": lok["lengdegrad"],
            },
        }
    if lok["lus_serie"]:
        # DataDownload for hele serien, ikke for de 52 ukene tabellen
        # viser. Det er den fila som er ment å siteres.
        #
        # `contentUrl` er RELATIV, og det er ikke slurv. JSON-LD løser
        # relative IRI-er mot dokumentets egen adresse, så «lusetall.csv»
        # peker riktig uansett hvilket vertsnavn siden havner på. Et
        # påfunnet domene ville vært en påstand om noe som ikke er
        # avgjort — samme grunn som at `url` ikke står her i det hele
        # tatt.
        data["distribution"] = [{
            "@type": "DataDownload",
            "name": f"Lusetall for lokalitet {lok['loknr']}, hele serien",
            "description": (
                f"{lok['lus_uker']} uker, {lok['lus_fra']} til "
                f"{lok['lus_til']}. CSV med kommentarhode."),
            "contentUrl": CSV_FILNAVN,
            "encodingFormat": "text/csv",
            "creditText": (indeks.get("lusetall") or ("",))[0],
        }]
        data["variableMeasured"] = [{
            "@type": "PropertyValue",
            "name": "voksne_hunnlus",
            "description": "Gjennomsnittlig antall voksne hunnlus per fisk, "
                           "rapportert per uke.",
            "measurementTechnique": "Oppdretters ukentlige telling, "
                                    "rapportert til Mattilsynet",
        }]
    return _script_trygg(data)


def _script_trygg(data: dict) -> Markup:
    """JSON som kan stå inne i en `<script>` uten å bli HTML-escapet.

    ## Feilen dette er rettingen av, målt 16.09.2026

    Første utkast skrev `{{ jsonld }}` i malen med `autoescape=True` på.
    Jinja escapet da hvert anførselstegn til `&#34;`, og resultatet var:

        <script type="application/ld+json">{
          &#34;@context&#34;: &#34;https://schema.org&#34;,

    Innholdet i en `<script>` er RAW TEXT i HTML — entiteter dekodes
    ikke der. `&#34;` blir altså stående som seks tegn, og JSON-LD-en er
    ugyldig for enhver parser. Siden så riktig ut i nettleseren, fordi
    ingenting av dette vises. Det er den stille varianten.

    ## Hvorfor ikke bare `|safe`

    Fordi `autoescape` var der av en grunn: strengene kommer fra
    registre vi ikke kontrollerer. Et lokalitetsnavn som inneholder
    `</script>` ville avsluttet taggen og gjort resten av JSON-en til
    HTML — og `json.dumps` escaper ikke `<`.

    Løsningen er å escape på JSONs premisser i stedet for HTMLs:
    `\u003c` er gyldig JSON og betyr fortsatt `<`, men nettleserens
    HTML-parser ser ingen tagg. `&` tas med for å lukke
    `&lt;/script&gt;`-varianten. Det er den samme øvelsen som i vakten:
    still spørsmålet i det vokabularet mottakeren faktisk leser.
    """
    raa = json.dumps(data, ensure_ascii=False, indent=2)
    trygg = (raa.replace("<", "\\u003c")
                .replace(">", "\\u003e")
                .replace("&", "\\u0026"))
    return Markup(trygg)


def _miljo() -> Environment:
    """Jinja2 med autoescaping PÅ og udefinerte variabler som FEIL.

    `autoescape=True` fordi hver streng på siden kommer fra et register
    vi ikke kontrollerer. `StrictUndefined` fordi en skrivefeil i et
    variabelnavn ellers rendrer som tom streng — en side med et manglende
    tall ser riktig ut, og det er den feilen som er dyrest å oppdage
    sent.
    """
    return Environment(
        loader=FileSystemLoader(MALER),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def skriv_lokalitet(loknr: str, rot: Path = UT,
                    felles: Felles | None = None,
                    mal=None) -> list[Path]:
    """Rendrer og skriver lokalitetssiden OG dens CSV. Returnerer stiene.

    Begge filene i samme mappe, som er hva en avsluttende skråstrek
    betyr. Mappa er dermed selvstendig: kopierer noen
    `/lokalitet/31397/`, følger både siden og tallene med.

    `felles` og `mal` er gjenbruk for en batch — se `skriv_alle()`. Uten
    dem gjør funksjonen nøyaktig det den gjorde før: leser alt selv og
    kompilerer malen på nytt.
    """
    lok = bygg_lokalitet(loknr, felles)
    vilkaar = felles.vilkaar if felles else None
    setninger = attribusjon(SIDENS_KILDER, vilkaar)  # kaster på UBELAGT
    mal = mal or _miljo().get_template("lokalitet.html.j2")

    html = mal.render(
        lok=lok,
        tittel=f"Lokalitet {lok['loknr']} {lok['navn']} — havbruk-radar",
        beskrivelse=(
            f"Registerdata, eierskap og ukentlige lusetall for "
            f"akvakulturlokalitet {lok['loknr']} {lok['navn']} i "
            f"{lok['kommune']}, med endringslogg."),
        jsonld=jsonld(lok),
        attribusjon=setninger,
        bygget=dt.date.today().isoformat(),
    )

    # Mappe + index.html, som er hva en avsluttende skråstrek BETYR.
    mappe = rot / "lokalitet" / loknr
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / "index.html"
    sti.write_text(html, encoding="utf-8")

    # CSV-en bærer BARE lusetall, og derfor bare lusetallkildens
    # attribusjon. Å legge alle fire kildenes setninger i et hode over en
    # fil som ikke inneholder dem, ville vært en påstand om at
    # Fiskeridirektoratet har levert noe her.
    #
    # SKRIVES OGSÅ NÅR SERIEN ER TOM. Målt 17.09.2026: 4 av 1782
    # lokaliteter finnes ikke i noe lusetallsnapshot. En CSV med hode og
    # null rader sier «vi har sett etter og ikke funnet noe»; en
    # manglende fil sier ingenting, og 404 er ikke et svar. Lenka fra
    # sida er den samme uansett, og kommentarhodet oppgir 0 uker.
    csv_sti = mappe / CSV_FILNAVN
    csv_sti.write_text(
        csv_tekst(lok, attribusjon(["lusetall"], vilkaar),
                  dt.date.today().isoformat()),
        encoding="utf-8")
    return [sti, csv_sti]


# ------------------------------------------------------------- batchen


@dataclass
class Byggelogg:
    """Hva som ikke gikk rent. Tellere, ikke lister med identiteter.

    Et bygg over 1782 sider som bare sier «ferdig» skjuler nøyaktig det
    man trenger å vite. Hver kategori her er noe som ble HÅNDTERT — og
    håndteringen står i koden ved siden av telleren, ikke i en
    fallback-verdi ingen ser.
    """

    sider: int = 0
    uten_eier: list[str] = None
    uten_tillatelser: list[str] = None
    uten_koordinater: list[str] = None
    uten_lusetall: list[str] = None
    uten_prodomraade: list[str] = None
    uten_endringer: list[str] = None
    feilet: list[tuple[str, str]] = None

    def __post_init__(self):
        for felt in ("uten_eier", "uten_tillatelser", "uten_koordinater",
                     "uten_lusetall", "uten_prodomraade", "uten_endringer",
                     "feilet"):
            if getattr(self, felt) is None:
                setattr(self, felt, [])


def skriv_alle(rot: Path = UT, grense: int | None = None
               ) -> tuple[Byggelogg, dict[str, float]]:
    """Alle lokaliteter i nyeste akvakultur-snapshot. (logg, tider).

    Feiler ÉN side, feller den ikke de andre. Samme regel som
    `runner.run_all()` og av samme grunn: én knekt ting skal koste én
    ting, ikke alt. Feilen føres med lokalitetsnummer og melding, og
    byggingen ender rødt.
    """
    tider: dict[str, float] = {}
    t0 = time.perf_counter()
    felles = les_felles()
    tider["felleslesing"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    mal = _miljo().get_template("lokalitet.html.j2")
    tider["malkompilering"] = time.perf_counter() - t0

    logg = Byggelogg()
    ider = sorted(felles.akva, key=lambda e: int(e) if e.isdigit() else 0)
    if grense:
        ider = ider[:grense]

    t0 = time.perf_counter()
    for loknr in ider:
        a = felles.akva[loknr]
        try:
            skriv_lokalitet(loknr, rot, felles, mal)
        except Exception as feil:                    # noqa: BLE001
            logg.feilet.append((loknr, f"{type(feil).__name__}: {feil}"))
            continue

        logg.sider += 1
        if not felles.tillatelser_per_lokalitet.get(loknr):
            logg.uten_eier.append(loknr)
        if not (a.get("tillatelser") or "").strip():
            logg.uten_tillatelser.append(loknr)
        if not (a.get("breddegrad") or "").strip() or \
                not (a.get("lengdegrad") or "").strip():
            logg.uten_koordinater.append(loknr)
        if not felles.lusserier.get(loknr):
            logg.uten_lusetall.append(loknr)
        if not (a.get("prodomraade_kode") or "").strip():
            logg.uten_prodomraade.append(loknr)
        if not felles.registerendringer.get(loknr):
            logg.uten_endringer.append(loknr)
    tider["rendring_og_skriving"] = time.perf_counter() - t0
    return logg, tider


# --------------------------------------------------------- porten


def gransk_og_meld(rot: Path) -> int:
    """Publiseringsvakten på det som nettopp ble bygget. 0 = rent.

    Porten er BLOKKERENDE, og den ligger her og ikke i testsuiten: en
    test kjører med `HAVBRUK_DATA_DIR` pekt til en engangsmappe, så
    hvitelista ville vært tom og vakten blind framfor streng. Se
    `docs/beslutninger/2026-09-15-publiseringsvakten.md`.

    Den kjøres på UTPUTTET og ikke på dataene, fordi det er generatoren
    den skal fange: et filtrert snapshot kan settes sammen til en side
    som bærer persondata uten at noen av datafiltrene ser det.
    """
    funn = publiseringsvakt.gransk(rot)
    publiseringsvakt._rapport()
    if not funn:
        print(f"\n{rot}: ingenting å innvende.")
        return 0
    print(f"\n{len(funn)} funn:")
    for f in funn:
        print(f"  {f}")
    print("\nPUBLISERING STOPPET.")
    return 1


def _meld_bygg(logg: Byggelogg, tider: dict[str, float], rot: Path) -> None:
    """Byggerapporten. Tallene, ikke inntrykket.

    Kategoriene skrives ALLTID, også når de er null. Et tall man bare
    ser når det er galt, er et tall ingen kjenner normalverdien til —
    samme begrunnelse som at `--rapport` teller de filtrerte hver gang.
    """
    total = sum(tider.values())
    bytes_ = sum(f.stat().st_size for f in rot.rglob("*") if f.is_file())
    print(f"\n{logg.sider} sider skrevet til {rot}")
    print(f"  byggetid      {total:8.1f} s")
    for merke, t in tider.items():
        print(f"    {merke:22} {t:7.1f} s  ({t / total * 100:4.1f} %)")
    print(f"  på disk       {bytes_ / 1e6:8.1f} MB"
          f"  ({bytes_ / max(logg.sider, 1) / 1024:.0f} kB per side)")

    print("\n  ikke rent:")
    for merke, liste in (
            ("uten eier (ingen tillatelse i eierskap)", logg.uten_eier),
            ("uten tillatelser i akvakultur", logg.uten_tillatelser),
            ("uten koordinater", logg.uten_koordinater),
            ("uten lusetall noen gang", logg.uten_lusetall),
            ("uten produksjonsområde", logg.uten_prodomraade),
            ("uten registerendringer", logg.uten_endringer),
            ("FEILET", logg.feilet)):
        print(f"    {merke:38} {len(liste):>5}")
    for loknr, feil in logg.feilet[:20]:
        print(f"      {loknr}: {feil}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lokalitet", default="31397",
                    help="lokalitetsnummer å bygge (standard: 31397)")
    ap.add_argument("--alle", action="store_true",
                    help="bygg hver lokalitet i nyeste akvakultur-snapshot")
    ap.add_argument("--grense", type=int, default=None,
                    help="med --alle: bygg bare de N første (for en prøve)")
    ap.add_argument("--ut", default=str(UT), help="målmappe")
    ap.add_argument("--uten-vakt", action="store_true",
                    help="hopp over publiseringsvakten (bare utvikling)")
    args = ap.parse_args()

    rot = Path(args.ut)
    if args.alle:
        logg, tider = skriv_alle(rot, args.grense)
        _meld_bygg(logg, tider, rot)
        if logg.feilet:
            return 1
    else:
        filer = skriv_lokalitet(args.lokalitet, rot)
        for f in filer:
            print(f"{f}  ({f.stat().st_size / 1024:.0f} kB)")
        print(f"  URL: /lokalitet/{args.lokalitet}/")
        print(f"  CSV: /lokalitet/{args.lokalitet}/{CSV_FILNAVN}")

    if args.uten_vakt:
        print("\nVAKTEN ER HOPPET OVER. Siden skal ikke publiseres.")
        return 0
    return gransk_og_meld(rot)


if __name__ == "__main__":
    raise SystemExit(main())
