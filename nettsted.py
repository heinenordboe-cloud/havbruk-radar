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
import math
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
import visningsord                                         # noqa: E402
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


def ubelagte(vilkaar: dict[str, tuple[str, ...] | None]) -> frozenset[str]:
    """Kildene uten dokumentert attribusjonsvilkår — UBELAGT.

    UTLEDET av `Source.attribusjon`, aldri listet. En liste her ville
    vært et andre sted sannheten kan bli stående gammel, og
    `test_bare_ekspertgruppen_er_ubelagt` ville ikke sett at de to ble
    uenige. I dag er svaret `{"ekspertgruppen"}`.

    Brukes til å holde UBELAGTE kilder ute av publiserte visninger. En
    UBELAGT kilde kan brukes i analyse; den skal ikke bære en publisert
    side. Se docs/LISENSKJEDE.md.
    """
    return frozenset(k for k, v in vilkaar.items() if v is None)


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

    ## Kilden spørres i tillegg til døra, og det er ikke valgfritt

    `snapshot.versjoner()` kjører `persondata.fjern_personformer()`. Den
    fjerner MÅLT 0 av 36 360 rader her, fordi kilden skriver 0 rader
    `organisasjonsform` og 0 `institusjonell_sektorkode` — formen står i
    `mottaker_type`, i pub-aquas vokabular.
    `Source.fjern_egne_personer()` er tillegget for nettopp det.

    Uten kallet ville fire overføringer til en personform stått på
    sidene, og `publiseringsvakt.hviteliste()` — som leser de samme
    årgangene gjennom det samme tillegget — ville meldt dem som
    `ukjent_navn` og blokkert publiseringen. Generatoren og porten må
    lese LIKT; to lesemåter av samme kilde som kan svare ulikt er formen
    F6 og F7 hadde.
    """
    from core import registry
    from core.contract import kilder_per_navn

    kilde = kilder_per_navn(registry.discover()).get("eierskap_historikk")
    ut: dict[str, dict[str, str]] = defaultdict(dict)
    for dato in snapshot.datoer("eierskap_historikk"):
        for _nr, ramme in snapshot.versjoner("eierskap_historikk", dato):
            if kilde is not None:
                ramme = kilde.fjern_egne_personer(ramme)
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
    # Produksjonsområdene: navn fra akvakultur, farger fra
    # trafikklysvedtak, og lokalitetene som ligger i hvert.
    po_navn: dict[str, str]
    lokaliteter_per_po: dict[str, list[str]]
    po_farger: dict[str, dict[str, dict[str, str]]]
    runder: list[str]
    # Selskapene: eier_orgnr -> tillatelsesnumre, og registerdata der vi
    # har det. 482 eiere, 360 med registerdata (målt 20.09.2026).
    tillatelser_per_eier: dict[str, list[str]]
    enhet: dict[str, dict[str, str]]
    enhet_dato: str


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

    # PRODUKSJONSOMRÅDENE. Navnet står på hver lokalitet i akvakultur og
    # ikke i en egen kilde; vi leser det derfra framfor å skrive en liste
    # over tretten navn som kan bli uenig med dataene.
    po_navn: dict[str, str] = {}
    lok_per_po: dict[str, list[str]] = defaultdict(list)
    for loknr, a in akva.items():
        kode = (a.get("prodomraade_kode") or "").strip()
        if not kode:
            continue
        lok_per_po[kode].append(loknr)
        navn = (a.get("prodomraade_navn") or "").strip()
        if navn:
            po_navn.setdefault(kode, navn)
    for kode in lok_per_po:
        lok_per_po[kode].sort(key=lambda e: int(e) if e.isdigit() else 0)

    # SELSKAPENE. Nøkkelen er organisasjonsnummeret, som er det URL-en
    # bruker — se docs/beslutninger/2026-09-16-url-struktur.md.
    till_per_eier: dict[str, list[str]] = defaultdict(list)
    for nr, d in eierskap.items():
        orgnr = (d.get("eier_orgnr") or "").strip()
        if orgnr:
            till_per_eier[orgnr].append(nr)
    for orgnr in till_per_eier:
        till_per_eier[orgnr].sort()

    enhet_dato, enhet = _siste("enhetsregisteret")

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
        po_navn=po_navn,
        lokaliteter_per_po=dict(lok_per_po),
        po_farger=_po_farger(),
        runder=snapshot.datoer("trafikklysvedtak"),
        tillatelser_per_eier=dict(till_per_eier),
        enhet=enhet,
        enhet_dato=enhet_dato,
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
MAALESERIER = frozenset({"lusetall", "sjotemperatur", "biomasse"})
#
# `biomasse` kom inn 20.09.2026, da produksjonsområdesidene ble bygget.
# Den er månedlige beholdningstall per produksjonsområde — samme klasse
# som lusetall, og MÅLT 10 990 changelog-rader mot trafikklysvedtakets
# 47. Tas de med som registerendringer, drukner vedtaket i serien.
#
# Den endrer ingenting for lokalitetssidene: biomasse har 14 entity_id-er
# i changeloggen (1-13 og `uten_po`), og ingen av dem er et
# lokalitetsnummer. Verifisert før tillegget.

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
        # `felt` er kildens navn og blir i `data-felt`. `etikett` er det
        # som står i Felt-kolonnen, og `fra`/`til` er oversatt: cellene
        # bærer changeloggens `old_value`/`new_value`, og de er like rå
        # som alt annet fra kilden.
        "etikett": visningsord.felt(str(r["field"])),
        "fra": visningsord.verdi(str(r["field"]),
                                 r["old_value"] if r["old_value"] is not None else ""),
        "til": visningsord.verdi(str(r["field"]),
                                 r["new_value"] if r["new_value"] is not None else ""),
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


# ------------------------------------------- produksjonsområdene
#
# Trettten områder, fastsatt i forskrift. Fargen per runde leses av
# `trafikklysvedtak`, og den er IKKE komplett: MÅLT 20.09.2026 kan 19 av
# 65 celler ikke leses av forskriftsteksten. En slik celle sier det.
#
# To grader av belegg, og skillet er alt et felt i dataene
# (`farge__lesemaate`):
#
#     ordrett           fargeordet står i bestemmelsen. 29 celler.
#     kapittelhjemmel   fargen er UTLEDET av hvilket kapittel området er
#                       plassert i. 17 celler.
#
# De to er ikke like sterke, og en side som viste dem likt ville påstått
# et belegg den ikke har.

# Fargeordet slik forskriften skriver det. Parseren normaliserer til
# ascii; her settes ordet tilbake. Kartet er vårt, ikke kildens — og det
# er derfor det ikke står i kilden.
#
# Fra 20.09.2026 ligger det i `visningsord.FARGE` sammen med resten av
# kildens koder. Grunnen er at det ikke var det eneste stedet «rod» nådde
# en leser: changeloggens `old_value`/`new_value` bar det uoversatt i
# endringstabellen, og MÅLT sto «rod» i 5 celler og «gronn» i 20 på de
# publiserte sidene mens fargetabellen ved siden av sa «rød». To steder
# som skal si det samme er formen F6 og F7 hadde.
FARGEORD = visningsord.FARGE

# Hva lesemåten BETYR, i klartekst på siden. Nøkkelen er kildens verdi.
LESEMAATE = {
    "ordrett": "fargeordet står ordrett i bestemmelsen",
    "kapitteloverskrift": "fargeordet står i kapitteloverskriften området "
                          "er plassert under",
    "kapittelhjemmel": "utledet av hvilket kapittel området er plassert i",
}

# Teksten når forskriften ikke oppgir farge for et område i en runde.
# Ikke tom celle — samme regel som `EIER_UKJENT`, og av samme grunn:
# fravær er et svar, og en tom celle lar leseren gjette.
#
# KORT, og i samme form som «rød», «gul», «grønn». Fram til 20.09.2026
# sto hele setningen «forskriften oppgir ikke farge for dette området i
# denne runden» i cellen, og den satte bredden på hele kolonnen: 62 tegn
# der de fem andre cellene har tre til fem. MÅLT i nettleser ble
# Fargekolonnen 11em bred og 2018-raden dobbelt så høy som de andre,
# og CSS-en måtte holdes oppe av et `min-width`-gulv og et
# `max-width`-tak for å se halvveis ut.
#
# En lang forklaringstekst bestemmer layouten rundt seg. Setningen står
# nå i noten under tabellen, der den forklarer alle radene én gang
# framfor å stå i hver celle den gjelder.
FARGE_MANGLER = "ikke oppgitt"
FARGE_MANGLER_FELT = "farge_mangler"

# EN PRESENTASJONSKROK, og bare det. CSS kan ikke velge på celletekst,
# så «hvilken av de tre» må stå som en klasse for at ruta foran ordet
# skal kunne få farge. Verdien er kildens normaliserte fargeord, ikke
# et nytt vokabular — `rod`, `gul`, `gronn`.
#
# ORDET ER FORTSATT BÆREREN. Klassen styrer en `::before`-rute som bare
# finnes i CSS-en; slås stilarket av, står ordet igjen alene og cellen
# er like sann. Se avsnitt 5 i maler/stil.css.
#
# Den heter ikke noe med `navn` eller `eier` i seg, og det er ikke
# tilfeldig: publiseringsvaktens `NAVNEMERKE` leser
# `class="[^"]*\b(navn|eier)\b[^"]*"` som «her står et navn», og en
# klasse som het `po-navn` ville meldt hvert områdenavn som et ukjent
# personnavn.
FARGE_KLASSE = {"gronn": "lys-gronn", "gul": "lys-gul", "rod": "lys-rod"}


def _po_farger() -> dict[str, dict[str, dict[str, str]]]:
    """{po: {år: {farge, farge__lesemaate}}} for hver fastsatte runde.

    Leses av alle snapshotene til `trafikklysvedtak`, som er partisjonert
    på VEDTAKSÅRET — se `Source.partisjonering`. Nyeste fil alene ville
    gitt 2026 og ikke de fire rundene før den.
    """
    ut: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for dato in snapshot.datoer("trafikklysvedtak"):
        for _versjon, ramme in snapshot.versjoner("trafikklysvedtak", dato):
            for eid, felt, verdi in ramme.select(
                    ["entity_id", "field", "value"]).iter_rows():
                ut[str(eid)].setdefault(dato[:4], {})[str(felt)] = verdi
    return {po: dict(runder) for po, runder in ut.items()}


def _fargerader(po: str, felles: Felles) -> list[dict]:
    """Én rad per runde. Aldri en tom celle.

    Rekkefølgen er rundenes, eldst først: en fargehistorikk leses
    kronologisk, og den som vil se dagens farge finner den nederst eller i
    registertabellen.
    """
    rader = []
    for dato in felles.runder:
        aar = dato[:4]
        d = (felles.po_farger.get(po) or {}).get(aar)
        if d and (d.get("farge") or "").strip():
            raa = d["farge"].strip()
            maate = (d.get("farge__lesemaate") or "").strip()
            rader.append({
                "aar": aar,
                "farge": visningsord.verdi("farge", raa),
                "farge_felt": "farge",
                "farge_klasse": FARGE_KLASSE.get(raa, ""),
                "lesemaate": maate,
                "lesemaate_tekst": LESEMAATE.get(maate, maate or "ukjent"),
            })
        else:
            rader.append({
                "aar": aar,
                "farge": FARGE_MANGLER,
                "farge_felt": FARGE_MANGLER_FELT,
                "farge_klasse": "",
                "lesemaate": "",
                "lesemaate_tekst": "ingen bestemmelse å lese",
            })
    return rader


def bygg_produksjonsomrade(po: str, felles: Felles) -> dict:
    """Alt én produksjonsområdeside trenger.

    Tar `felles` som krav og ikke som valgfritt: tretten sider leser de
    samme snapshotene, og en variant som leste selv ville vært en andre
    vei til samme side — formen F6 og F7 hadde.
    """
    lokaliteter = [
        {
            "loknr": loknr,
            "navn": felles.akva[loknr].get("navn", ""),
            "kommune": felles.akva[loknr].get("kommune", ""),
            "kapasitet": visningsord.maalt(
                felles.akva[loknr].get("kapasitet", ""),
                felles.akva[loknr].get("kapasitet_enhet", "")),
            "arter": visningsord.verdi("arter",
                                       felles.akva[loknr].get("arter", "")),
        }
        for loknr in felles.lokaliteter_per_po.get(po, ())
    ]

    # Endringene for OMRÅDET. Måleseriene telles og vises ikke — samme
    # regel som på lokalitetssiden, og for biomasse er forholdet 10 990
    # mot 47. `ekspertgruppen` holdes helt utenfor: kilden er UBELAGT, og
    # antallet oppgis framfor å forsvinne stille.
    rader = felles.registerendringer.get(po, ())
    ubelagt = ubelagte(felles.vilkaar)
    register = [_endringsrad(r, po) for r in rader
                if r["source"] not in MAALESERIER
                and r["source"] not in ubelagt]
    register.sort(key=lambda r: r["dato"], reverse=True)

    return {
        "nr": po,
        "navn": felles.po_navn.get(po, ""),
        "status": (felles.akva[lokaliteter[0]["loknr"]].get("prodomraade_status", "")
                   if lokaliteter else ""),
        "akva_dato": felles.akva_dato,
        "runder": _fargerader(po, felles),
        "lokaliteter": lokaliteter,
        "lokaliteter_antall": len(lokaliteter),
        "endringer": register,
        # FRA MÅLESERIEINDEKSEN, ikke fra `registerendringer` — den
        # inneholder per konstruksjon ingen måleserierader, så en telling
        # der ville alltid gitt 0. Første utkast gjorde nettopp det, og
        # sida ville påstått «0 biomasserader» der det er 840.
        "maaleserie_rader": felles.maaleserierader.get(po, 0),
        "ubelagte_rader": sum(1 for r in rader if r["source"] in ubelagt),
        "ubelagte_kilder": sorted(ubelagt),
    }


# --------------------------------------------- når kildene er uenige
#
# `akvakultur` oppgir hvilke tillatelser som ligger på en lokalitet.
# `eierskap` oppgir hvem som eier en tillatelse. MÅLT 19.09.2026 er de to
# uenige om 84 tillatelsesnumre på 65 lokaliteter — 62 der INGEN av
# tillatelsene finnes i eierskap.
#
# Uenigheten er ikke en datafeil, og den er ikke kildens: alle 84 finnes
# hos Fiskeridirektoratet med 200 OK, og for TRETTØY er alle 14 AKTIVE.
# Det som mangler er EIEREN — 55 fordi kilden ikke oppgir
# organisasjonsnummer for eiere som er privatpersoner, 29 fordi eieren
# ikke finnes i `/entities` og typen dermed er ukjent. Begge stoppes av
# vårt eget personvernfilter, og det skal de.
#
# REGELEN: en lokalitet der vi ikke vet hvem som eier tillatelsene sier
# DET. Den viser ikke en tom tabell, og den utelater ikke raden. Se
# docs/REGEL-UENIGE-KILDER.md.

# Verdien i eiercellen når vi ikke kan gjøre rede for eieren. Ikke tom
# streng: en tom celle lar leseren gjette, og «vi vet ikke» er et svar.
EIER_UKJENT = "ikke oppgitt av kilden"

# Feltnavnet den cellen merkes med. IKKE `eier_navn` — verdien er VÅR
# setning om fravær, ikke et navn fra kilden, og porten skal ikke lete
# etter den i hvitelista over navn. Se docs/REGEL-UENIGE-KILDER.md.
EIER_UKJENT_FELT = "eier_ukjent"


def _liste(verdi: str | None) -> list[str]:
    """Semikolonlista `akvakultur.tillatelser` bærer, som numre.

    Kilden skriver «H-SO-0318; H-SO-0329», og separatoren er kildens.
    Ett sted, fordi to varianter av samme split er to steder å glemme
    `strip()`.
    """
    return [x.strip() for x in (verdi or "").split(";") if x.strip()]


def _uten_eier(oppgitt: list[str], eierskap: dict) -> list[str]:
    """Tillatelsene akvakultur oppgir som eierskap ikke kan gjøre rede for.

    Ett sted, kalt fra begge veiene inn i `bygg_lokalitet()`. To steder
    som skal si det samme om hva vi ikke vet, er formen F6 og F7 hadde.
    """
    return [nr for nr in oppgitt if nr not in eierskap]


def _tillatelsesrader(mine_till: dict, uten_eier: list[str]) -> list[dict]:
    """Radene i eierskapstabellen — kjente OG ugjorte rede for.

    Samme radform for begge, med `eier_felt` som skiller dem. En egen
    tabell for de ukjente ville gjort fraværet til noe man kan overse;
    en utelatt rad ville gjort det usynlig.
    """
    rader = [
        {
            "nr": nr,
            "eier_navn": d.get("eier_navn", ""),
            "eier_felt": "eier_navn",
            "eier_orgnr": d.get("eier_orgnr", ""),
            "type": d.get("tillatelse_type", ""),
            "kapasitet": visningsord.maalt(d.get("kapasitet", ""),
                                           d.get("kapasitet_enhet", "")),
            "tildelt_dato": (d.get("tildelt_tid") or "")[:10],
            "tildelt_navn": d.get("tildelt_navn", ""),
        }
        for nr, d in mine_till.items()
    ] + [
        {
            "nr": nr,
            "eier_navn": EIER_UKJENT,
            "eier_felt": EIER_UKJENT_FELT,
            "eier_orgnr": "",
            "type": "",
            "kapasitet": "",
            "tildelt_dato": "",
            "tildelt_navn": "",
        }
        for nr in uten_eier
    ]
    return sorted(rader, key=lambda r: r["nr"])


# --------------------------------------------------------- lusegrafen
#
# ## Hvorfor en graf når tallene allerede står der
#
# Lokalitetssiden har 764 uker lusetall. Tabellen viser de siste 26 av
# dem, og hele serien ligger i CSV-en ved siden av. Det er riktig for
# den som vil ETTERPRØVE et tall, og ubrukelig for den som vil se om
# lusa har økt siden 2012 — 764 rader er ikke en form et menneske kan
# lese en kurve ut av.
#
# Grafen legger ikke til én verdi. Den er den samme lista, tegnet.
#
# ## Hullene er ikke null, og de tegnes ikke som null
#
# 207 av 764 uker på OTERNESET har ingen verdi. En kurve som gikk
# gjennom dem i null ville påstått at det ble talt null lus, og det er
# den ene feilen denne grafen ikke får gjøre — hele tabellen under står
# og roper at «–» betyr at kilden ikke oppgir noe tall.
#
# Linja BRYTES derfor ved hvert hull. Segmentene er egne `<polyline>`
# og ikke én path med hopp i: et hopp i en path er en usynlig strek som
# noen CSS-regel kan komme til å fylle.
#
# ## Brakklegging forklarer hullene — men ikke alle
#
# MÅLT på OTERNESET: alle 167 brakklagte uker mangler tall, og 40 uker
# mangler tall UTEN å være brakklagt. Båndene forklarer altså 167 av
# 207 hull, og de siste 40 er ikke forklart av noe vi har. Tallene
# regnes per lokalitet og står i bildeteksten, framfor at grafen lar
# båndene se ut som om de dekker alt.
#
# ## Ingen JavaScript, altså ingen tooltip
#
# En SVG-graf på nettet får normalt et fadekors og en tooltip. Denne
# får det ikke, og det er samme valg som resten av nettstedet: tallene
# skal stå i kildekoden. Det leseren mister — verdien for en bestemt
# uke — står i tabellen under og i CSV-en, som er en bedre kilde enn en
# tooltip uansett: den kan siteres.

GRAF_BREDDE = 900
GRAF_HOYDE = 220
GRAF_MARG = {"v": 48, "h": 12, "o": 14, "u": 28}   # venstre/høyre/over/under

# Trinnene en y-akse får lov å bruke. Et «pent» tall er ikke en estetisk
# sak: 0,4 og 0,8 leses som fjerdedeler, 0,37 leses ikke som noe.
GRAF_TRINN = (0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0)


def _grafskala(maks: float) -> tuple[float, float]:
    """(tak, trinn) for y-aksen. 3-5 linjer, alltid med 0 og taket."""
    if maks <= 0:
        return 1.0, 0.5
    for trinn in GRAF_TRINN:
        if maks / trinn <= 4:
            return math.ceil(maks / trinn) * trinn, trinn
    return maks, maks / 4


def lusegraf(serie: list[dict]) -> dict | None:
    """Geometrien til lusegrafen, eller None når det ikke er noe å tegne.

    None og ikke en tom graf: en akse uten en eneste verdi er en ramme
    som later som om den har et innhold. Malen viser da ingenting, og
    tabellen sier fra i klartekst — den sier det allerede.
    """
    if not serie:
        return None
    verdier: list[float | None] = []
    for u in serie:
        rå = (u.get("voksne_hunnlus") or "").strip()
        try:
            verdier.append(float(rå))
        except ValueError:
            verdier.append(None)
    if not any(v is not None for v in verdier):
        return None

    maks = max(v for v in verdier if v is not None)
    tak, trinn = _grafskala(maks)
    n = len(serie)
    v, h, o, u_ = (GRAF_MARG["v"], GRAF_MARG["h"],
                   GRAF_MARG["o"], GRAF_MARG["u"])
    plott_b = GRAF_BREDDE - v - h
    plott_h = GRAF_HOYDE - o - u_

    def x(i: int) -> float:
        return round(v + (plott_b * i / (n - 1) if n > 1 else plott_b / 2), 1)

    def y(verdi: float) -> float:
        return round(o + plott_h * (1 - verdi / tak), 1)

    # Segmentene. Et nytt segment begynner etter hvert hull.
    segmenter, naa = [], []
    for i, verdi in enumerate(verdier):
        if verdi is None:
            if len(naa) > 1:
                segmenter.append(" ".join(naa))
            naa = []
        else:
            naa.append(f"{x(i)},{y(verdi)}")
    if len(naa) > 1:
        segmenter.append(" ".join(naa))

    # ENSLIGE punkter. En uke med tall mellom to hull blir et segment på
    # ett punkt, og en `<polyline>` med ett punkt tegner ingenting. Uten
    # dette forsvinner en målt verdi fra grafen i stillhet.
    alene = [{"x": x(i), "y": y(verdier[i])}
             for i in range(n) if verdier[i] is not None
             and (i == 0 or verdier[i - 1] is None)
             and (i == n - 1 or verdier[i + 1] is None)]

    # Brakkleggingsbåndene, slått sammen til sammenhengende strekk.
    baand, start = [], None
    for i, rad in enumerate(serie + [{}]):
        er_brakk = str(rad.get("brakklagt")) == "True"
        if er_brakk and start is None:
            start = i
        elif not er_brakk and start is not None:
            baand.append({"x": x(start) if start else v,
                          "bredde": round(max(x(i - 1) - x(start), 1.5), 1)})
            start = None

    linjer = []
    steg = trinn
    verdi = 0.0
    while verdi <= tak + 1e-9:
        linjer.append({"y": y(verdi), "verdi": verdi,
                       "etikett": f"{verdi:.2f}".rstrip("0").rstrip(".")
                                  .replace(".", ",") or "0"})
        verdi += steg

    # Årstallene. Ett merke per årsskifte, og bare annethvert når serien
    # er lang nok til at de ellers ville stått oppå hverandre.
    aar = []
    for i, rad in enumerate(serie):
        if i and rad.get("iso_aar") != serie[i - 1].get("iso_aar"):
            aar.append({"x": x(i), "etikett": rad.get("iso_aar", "")})
    if len(aar) > 8:
        aar = aar[1::2]

    uten_tall = sum(1 for v in verdier if v is None)
    brakk = sum(1 for rad in serie if str(rad.get("brakklagt")) == "True")
    brakk_uten_tall = sum(1 for rad, v in zip(serie, verdier)
                          if v is None and str(rad.get("brakklagt")) == "True")
    return {
        "bredde": GRAF_BREDDE, "hoyde": GRAF_HOYDE,
        "plott_x": v, "plott_y": o,
        "plott_bredde": plott_b, "plott_hoyde": plott_h,
        "bunn": round(o + plott_h, 1),
        "segmenter": segmenter,
        "alene": alene,
        "baand": baand,
        "linjer": linjer,
        "aar": aar,
        "tak": tak,
        # Formateres HER og ikke i malen. `1.54` med punktum er engelsk,
        # og `visningsord.tall()` er det ene stedet nettstedet bestemmer
        # hvordan et tall ser ut på norsk. En graf som skrev det selv
        # ville vært et andre sted.
        "maks": visningsord.tall(maks),
        "uker": n,
        "uker_med_tall": n - uten_tall,
        "uten_tall": uten_tall,
        "brakklagt": brakk,
        "hull_forklart": brakk_uten_tall,
        "hull_uforklart": uten_tall - brakk_uten_tall,
    }


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
        oppgitt = _liste(a.get("tillatelser"))
        uten_eier = _uten_eier(oppgitt, eierskap)
    else:
        eierskap_dato, eierskap = felles.eierskap_dato, felles.eierskap
        mine_till = {nr: eierskap[nr] for nr in
                     felles.tillatelser_per_lokalitet.get(loknr, ())}
        ovf = [o for nr in mine_till
               for o in felles.overforinger_per_tillatelse.get(nr, ())]
        serie = felles.lusserier.get(loknr, [])
        endringer, maaleserie_rader = _endringer_av_indeks(
            loknr, sorted(mine_till), felles)
        oppgitt = _liste(a.get("tillatelser"))
        uten_eier = _uten_eier(oppgitt, eierskap)

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
        # TRE ledd per rad, ikke to: kildens feltnavn, etiketten et
        # menneske leser, og verdien oversatt. Feltnavnet MÅ bli med —
        # det er `data-felt`, altså markupkontrakten, og det er det
        # publiseringsvakten leser. Etiketten er bare for øyet.
        "register": [(f, visningsord.felt(f), visningsord.verdi(f, v))
                     for f, v in sorted(a.items())],
        # KJENTE og UGJORTE REDE FOR i SAMME tabell, i nummerrekkefølge.
        # Regelen og målingen står i docs/REGEL-UENIGE-KILDER.md: en
        # lokalitet der vi ikke vet hvem som eier tillatelsene skal si
        # det, ikke vise en tom tabell.
        "tillatelser": _tillatelsesrader(mine_till, uten_eier),
        "tillatelser_oppgitt": len(oppgitt),
        "tillatelser_uten_eier": len(uten_eier),
        # Teksten sendes INN og står ikke i malen: to steder som skal si
        # det samme om hva vi ikke vet, er formen F6 og F7 hadde.
        "eier_ukjent": EIER_UKJENT,
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
        "lusegraf": lusegraf(serie),
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


# Stien fra en side til stilarket. RELATIV, ikke absolutt.
#
# `/stil.css` er riktig når siden SERVERES fra et domenerot, og bare da.
# Åpnes fila rett fra disk, løser nettleseren `/stil.css` til
# `file:///stil.css` — filsystemets rot — og siden rendrer uten stilark.
# MÅLT 20.09.2026: nettopp det skjedde, og symptomet var vanskelig å
# lese som «stilarket mangler»: nettleseren faller tilbake på sin egen
# tabellstil, og en granskende leser ser en side som ser ut som et
# designvalg framfor en fil som ikke kom fram.
#
# Relativ sti virker begge veier, og i tillegg om nettstedet en dag
# skulle ligge i en undermappe. URL-beslutningen 2026-09-16 gjelder
# SIDENES adresser — de er fortsatt absolutte. Stilarket er ingen
# adresse noen lenker til.
STILARK = "stil.css"


def stilsti(sti: Path, rot: Path) -> str:
    """Relativ sti fra `sti` sin mappe til stilarket i `rot`.

    Regnes av den faktiske filstien framfor av et tall per sidetype:
    et tall ville vært en andre påstand om hvor sida ligger, ved siden
    av den ekte — og de to kan svare ulikt. Samme grunn som at
    kjøredatoen slås opp ett sted.
    """
    dybde = len(sti.relative_to(rot).parts) - 1
    return "../" * dybde + STILARK


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
    sti = rot / "lokalitet" / loknr / "index.html"
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
        stilark=stilsti(sti, rot),
        bygget=dt.date.today().isoformat(),
    )

    # Mappe + index.html, som er hva en avsluttende skråstrek BETYR.
    mappe = sti.parent
    mappe.mkdir(parents=True, exist_ok=True)
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


# -------------------------------------------------------- stilarket
#
# ## Én fil, lenket — ikke innebygd i hver side
#
# Innebygd i `<style>` ville stilarket kostet ~12 kB per side. Over
# 2 279 sider er det 27 MB, altså 18 % på et utputt som er 155 MB, og
# hver leser ville lastet det på nytt for hver side. Lenket er det én
# fil og én forespørsel, og nettleseren hentet den sist på forsiden.
#
# ## Hvorfor to filer på disk, men én på nettet
#
# `maler/tokens.css` er HENTET — Digdirs verdier ordrett, med tagg,
# sha256 og lisens. `maler/stil.css` er SKREVET. Grensa er hele grunnen
# til at de ligger hver for seg: en oppgradering av tokens skal kunne
# byttes ut som en blokk, uten at noen må skille våre verdier fra
# deres. Sammensetningen her er tekstsammenslåing og ikke et byggesteg
# — ingen preprosessor, ingen minifisering, ingen kildekart.
#
# ## Stien er absolutt, som hver annen URL på nettstedet
#
# `/stil.css`, ikke `../../stil.css`. Sidene lenker alt absolutt (se
# 2026-09-16-url-struktur.md), så det er ingen ny begrensning — men det
# betyr at siden må SERVERES for å se riktig ut. Åpnet rett fra disk
# med `file://` finner nettleseren verken stilarket eller nabosidene.
#     python -m http.server --directory <ut-mappa>

STILFILER = ("tokens.css", "stil.css")


def stilark() -> str:
    """Tokens + vår CSS, i den rekkefølgen. Rekkefølgen er ikke fri:
    `stil.css` leser `--ds-*` som `tokens.css` definerer."""
    biter = []
    for navn in STILFILER:
        sti = MALER / navn
        biter.append(f"/* ==== {navn} ==== */\n{sti.read_text(encoding='utf-8')}")
    return "\n".join(biter)


def skriv_stil(rot: Path) -> Path:
    """Skriver `/stil.css`. Returnerer stien."""
    rot.mkdir(parents=True, exist_ok=True)
    ut = rot / "stil.css"
    ut.write_text(stilark(), encoding="utf-8")
    return ut


# -------------------------------------------------------- fonten
#
# ## Én fil, hostet av oss
#
# `maler/stil.css` viser til `url("newsreader.woff2")` RELATIVT til
# stilarket, og stilarket ligger i rota. Fonten må derfor ligge samme
# sted. Ingen CDN: en side som henter en fil fra fonts.gstatic.com er
# en side som ser feil ut den dagen den tjenesten gjør det, og som
# forteller Google hvem som leser den. Samme argument som pinningen av
# `requirements.txt`.
#
# ## Lisensen er en FIL, ikke en kommentar
#
# SIL OFL 1.1 krever at lisensteksten distribueres med fonten. En
# kommentar i CSS-en er ikke det, og en lenke til Google er det heller
# ikke. `newsreader-OFL.txt` kopieres derfor ved siden av woff2-fila og
# er tilgjengelig på /newsreader-OFL.txt for enhver som ser etter.
#
# ## Hvorfor kopiering og ikke innbaking i CSS-en
#
# En woff2 som base64 i stilarket ville lagt 47 kB på en fil hver leser
# henter, og gjort at stilarket ikke kan mellomlagres uavhengig av
# fonten. To filer, to forespørsler, begge cachbare.

FONTFILER = ("newsreader.woff2", "newsreader-OFL.txt")


def skriv_fonter(rot: Path) -> list[Path]:
    """Kopierer fonten og lisensen til nettstedets rot.

    Kaster om en av dem mangler. En side som rendrer uten fonten ser ut
    som et designvalg (se `font-display: swap`), og en font uten lisens
    ved siden av er et lisensbrudd som ingen ser — begge er feil som er
    stille, og derfor skal byggingen stoppe framfor å hoppe over."""
    rot.mkdir(parents=True, exist_ok=True)
    skrevet = []
    for navn in FONTFILER:
        kilde = MALER / navn
        if not kilde.exists():
            raise FileNotFoundError(
                f"{kilde} mangler. Stilarket viser til /{navn}; "
                f"uten fila er @font-face en død lenke.")
        ut = rot / navn
        ut.write_bytes(kilde.read_bytes())
        skrevet.append(ut)
    return skrevet


# ------------------------------------------- sitemap, robots, llms
#
# ## Domenet finnes ikke, og det skal ikke finnes på
#
# `sitemap.xml` krever ABSOLUTTE URL-er etter spesifikasjonen. Vi har
# ikke noe vertsnavn — se docs/beslutninger/2026-09-16-url-struktur.md,
# som lar være å oppgi `url` i JSON-LD-en av nøyaktig samme grunn: et
# påfunnet domene er en påstand om noe som ikke er avgjort.
#
# Løsningen er ikke å finne på ett, og ikke å la fila være:
# `HAVBRUK_BASEURL` leses ved bygging. Er den satt, blir URL-ene
# absolutte og fila er spec-gyldig. Er den ikke satt, skrives stiene
# relative OG fila sier i en kommentar at den må bygges på nytt med
# variabelen satt før den duger for en søkemotor. Da er mangelen synlig
# i fila selv, ikke bare i hodet på den som bygde.

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _basisurl() -> str:
    """Vertsnavnet sidene skal ligge på, eller tom streng.

    Leses ved KALL og ikke ved import, så en test kan sette den uten å
    laste modulen på nytt — samme grunn som `_http.brukeragent()`.
    """
    import os
    return (os.environ.get("HAVBRUK_BASEURL") or "").strip().rstrip("/")


def _urler(felles: Felles) -> list[str]:
    """Hver publiserte side, som sti. Rekkefølgen er lesningens.

    Lusetall-CSV-ene står ikke her: en sitemap er sider, ikke
    nedlastinger, og hver CSV er lenket fra sin egen lokalitetsside.
    """
    stier = ["/", "/om/", "/lokalitet/", "/produksjonsomrade/", "/selskap/"]
    stier += [f"/lokalitet/{loknr}/" for loknr in
              sorted(felles.akva, key=lambda e: int(e) if e.isdigit() else 0)]
    stier += [f"/produksjonsomrade/{po}/" for po in
              sorted(felles.po_navn, key=lambda k: int(k) if k.isdigit() else 0)]
    stier += [f"/selskap/{orgnr}/" for orgnr in
              sorted(felles.tillatelser_per_eier)
              if not personeier(orgnr, felles)]
    return stier


def skriv_sitemap(rot: Path, felles: Felles) -> Path:
    """sitemap.xml over alle sidene."""
    from xml.sax.saxutils import escape

    basis = _basisurl()
    dato = dt.date.today().isoformat()
    linjer = ['<?xml version="1.0" encoding="UTF-8"?>']
    if not basis:
        linjer.append(
            "<!-- HAVBRUK_BASEURL er ikke satt, så <loc> er RELATIVE "
            "stier. Sitemap-spesifikasjonen krever absolutte URL-er: "
            "bygg på nytt med variabelen satt før fila leveres til en "
            "søkemotor. Et påfunnet domene ville vært en påstand om noe "
            "som ikke er avgjort. -->")
    linjer.append(f'<urlset xmlns="{SITEMAP_NS}">')
    for sti in _urler(felles):
        linjer.append("  <url>")
        linjer.append(f"    <loc>{escape(basis + sti)}</loc>")
        linjer.append(f"    <lastmod>{dato}</lastmod>")
        linjer.append("  </url>")
    linjer.append("</urlset>")
    ut = rot / "sitemap.xml"
    ut.write_text("\n".join(linjer) + "\n", encoding="utf-8")
    return ut


def skriv_robots(rot: Path) -> Path:
    """robots.txt. Alt er åpent; det er poenget med å publisere det."""
    basis = _basisurl()
    linjer = [
        "# havbruk-radar — offentlige registerdata, fritt tilgjengelige.",
        "# Sidene er statiske og tåler å bli indeksert i sin helhet.",
        "User-agent: *",
        "Allow: /",
        "",
    ]
    if basis:
        linjer.append(f"Sitemap: {basis}/sitemap.xml")
    else:
        linjer += [
            "# Sitemap-linja krever en absolutt URL, og domenet er ikke",
            "# avgjort. Bygg på nytt med HAVBRUK_BASEURL satt.",
            "# Sitemap: https://<domene>/sitemap.xml",
        ]
    ut = rot / "robots.txt"
    ut.write_text("\n".join(linjer) + "\n", encoding="utf-8")
    return ut


def skriv_llms(rot: Path, felles: Felles) -> Path:
    """llms.txt — hva dette er, og hvor de fullstendige listene er.

    Peker på INDEKSENE og /om/, ikke på 1782 enkeltsider. En modell som
    følger fila skal finne alt på tre hopp, og en fil med 1782 lenker
    ville vært den samme lista som sitemap.xml, bare dårligere.
    """
    om = bygg_om(felles)
    basis = _basisurl()
    u = (lambda sti: basis + sti) if basis else (lambda sti: sti)
    tekst = f"""# havbruk-radar

> Offentlige registerdata om norsk akvakultur, hentet ukentlig og lagret
> som daterte snapshots. {om['lokaliteter']} lokaliteter, 13
> produksjonsområder og {len(_urler(felles)) - 5 - om['lokaliteter'] - 13}
> selskaper. Registrene viser nåtilstanden og skriver over; her står
> tidsaksen — hva registeret sa forrige uke, og hva som har endret seg.

Data fra Fiskeridirektoratet, Brønnøysundregistrene, BarentsWatch og
Lovdata, gjengitt uendret. Sammenstillingen er {om['forfatter']} sin.
Hver side oppgir datoen dataene gjelder for, og sier hva den ikke vet:
der en eier ikke er oppgitt av kilden, eller en forskrift ikke oppgir
farge, står det i klartekst framfor en tom celle.

Nyeste snapshots: akvakultur {om['akva_dato']}, eierskap
{om['eierskap_dato']}, enhetsregisteret {om['enhet_dato']}, lusetall
{om['lus_til']} ({om['lusetall_uker']} uker tilbake til {om['lus_fra']}).

Dekning: {om['med_eier']} av {om['lokaliteter']} lokaliteter
({om['dekning']} %) har minst én tillatelse knyttet til et navngitt
selskap. Foretak i SSB-sektor 8200 og 2300 er bevisst utelatt av
personvernhensyn, og de som forsvinner er små, personeide anlegg.

## Fullstendige lister

- [Alle lokaliteter]({u('/lokalitet/')}): flat, upaginert liste over alle
  {om['lokaliteter']} lokalitetene, med nummer, navn, kommune og
  produksjonsområde.
- [Alle produksjonsområder]({u('/produksjonsomrade/')}): de 13 områdene
  med nyeste trafikklysfarge.
- [Alle selskaper]({u('/selskap/')}): selskapene som eier minst én
  akvakulturtillatelse.

## Om kilder, metode og sitering

- [Om havbruk-radar]({u('/om/')}): kildene med lisens og ordrett
  attribusjon, hvor ofte det samles inn, hva dekningen er, hva som
  bevisst ikke hentes, og en ferdig formatert referanse.
- [Kildekode og beslutningslogg]({om['repo']}): hver beslutning er
  skrevet ned med hva som ville snudd den, og hver terskel er målt.

## Sitering

{om['forfatter']} ({om['bygget'][:4]}). havbruk-radar: sammenstilte
registerdata om norsk akvakultur. Bygget {om['bygget']}. {om['repo']}

Kildenes egen attribusjon må følge med og står i bunnteksten på hver
side. Den erstattes ikke av en referanse til dette nettstedet.
"""
    ut = rot / "llms.txt"
    ut.write_text(tekst, encoding="utf-8")
    return ut


# ---------------------------------------------------------- om-siden
#
# Den ENESTE siden som skrives for et menneske som lurer på om det kan
# stole på dette. Den skal svare på det med tall og datoer, ikke med
# forsikringer.
#
# Kildetabellen bygges av `Source.attribusjon` og `docs/LISENSKJEDE.md`,
# og lisensraden er ikke hardkodet her: en fjerde kopi av lisenskjeden
# ville blitt stående uendret den dagen et vilkår endres.

# Lisensnavn og hjemmel per kilde, ordrett fra docs/LISENSKJEDE.md med
# datoen vilkåret ble lest. Attribusjonssetningene hentes fra kilden
# selv — dette er bare det LISENSKJEDEN sier utover setningen.
LISENSRAD = {
    "akvakultur": ("NLOD", "fiskeridir.no", "25.08.2026"),
    "biomasse": ("NLOD", "fiskeridir.no", "25.08.2026"),
    "biomasselag": ("NLOD", "fiskeridir.no", "25.08.2026"),
    "romming": ("NLOD", "fiskeridir.no", "25.08.2026"),
    "eierskap": ("NLOD + NLOD 2.0", "fiskeridir.no + brreg.no",
                 "25.08. / 14.09.2026"),
    "eierskap_historikk": ("NLOD + NLOD 2.0", "fiskeridir.no + brreg.no",
                           "25.08. / 14.09.2026"),
    "enhetsregisteret": ("NLOD 2.0 (frie nivået)", "brreg.no", "14.09.2026"),
    "lusetall": ("NLOD", "barentswatch.no/artikler/api-vilkar", "12.09.2026"),
    "sjotemperatur": ("NLOD", "barentswatch.no/artikler/api-vilkar",
                      "12.09.2026"),
    "trafikklysvedtak": ("NLOD 2.0 via Lovdatas punkt 2.3",
                         "lovdata.no/info/brukeravtale", "12.09.2026"),
    "reguleringsomraader": ("CC BY 4.0", "doi.org/10.21335/NMDC-1923112433",
                            "14.09.2026"),
    "ekspertgruppen": ("UBELAGT", "ingen funnet", "14.09.2026 (søkt)"),
}

OM_KILDER = ("akvakultur", "eierskap", "eierskap_historikk",
             "enhetsregisteret", "lusetall", "trafikklysvedtak")


def bygg_om(felles: Felles) -> dict:
    """Tallene om-siden står for. Alle målt i denne kjøringen."""
    med_eier = sum(1 for loknr in felles.akva
                   if felles.tillatelser_per_lokalitet.get(loknr))
    total = len(felles.akva)
    uten = [loknr for loknr in felles.akva
            if not felles.tillatelser_per_lokalitet.get(loknr)]
    oppgitt_likevel = [loknr for loknr in uten
                       if _liste(felles.akva[loknr].get("tillatelser"))]

    vilkaar = felles.vilkaar
    kilder = []
    for navn in sorted(LISENSRAD):
        lisens, hjemmel, lest = LISENSRAD[navn]
        setninger = vilkaar.get(navn)
        kilder.append({
            "navn": navn,
            "lisens": lisens,
            "hjemmel": hjemmel,
            "lest": lest,
            "attribusjon": list(setninger) if setninger else [],
            "ubelagt": setninger is None,
            "publiseres": navn in OM_KILDER,
        })

    import os
    kontakt = (os.environ.get("HAVBRUK_KONTAKT") or "").strip()

    return {
        "lokaliteter": total,
        "med_eier": med_eier,
        "dekning": round(med_eier / total * 100, 2) if total else 0.0,
        "uten_eier": len(uten),
        "uten_eier_med_tillatelse": len(oppgitt_likevel),
        "uten_tillatelse_noe_sted": len(uten) - len(oppgitt_likevel),
        "kilder": kilder,
        "ubelagte": [k["navn"] for k in kilder if k["ubelagt"]],
        "akva_dato": felles.akva_dato,
        "eierskap_dato": felles.eierskap_dato,
        "enhet_dato": felles.enhet_dato,
        "lusetall_uker": len(felles.lusetall_snapshots),
        "lus_fra": (felles.lusetall_snapshots[0]
                    if felles.lusetall_snapshots else ""),
        "lus_til": (felles.lusetall_snapshots[-1]
                    if felles.lusetall_snapshots else ""),
        "kontakt": kontakt,
        "repo": "https://github.com/heinenordboe-cloud/havbruk-radar",
        "forfatter": "Heine Valø Nordbøe",
        "bygget": dt.date.today().isoformat(),
    }


def skriv_om(rot: Path, felles: Felles) -> Path:
    """Rendrer og skriver /om/."""
    om = bygg_om(felles)
    mal = _miljo().get_template("om.html.j2")
    html = mal.render(
        om=om,
        tittel="Om havbruk-radar — kilder, metode, dekning og sitering",
        beskrivelse=(
            "Hva havbruk-radar er, hvilke offentlige kilder det bygger "
            "på med lisens og attribusjon, hvor ofte det samles inn, hva "
            "dekningen er, hvem som står bak, og hvordan du siterer det."),
        jsonld=_script_trygg({
            "@context": "https://schema.org",
            "@type": "AboutPage",
            "name": "Om havbruk-radar",
            "inLanguage": "nb",
            "author": {"@type": "Person", "name": om["forfatter"]},
            "codeRepository": om["repo"],
        }),
        attribusjon=attribusjon(OM_KILDER, felles.vilkaar),
        stilark=stilsti(rot / "om" / "index.html", rot),
        bygget=om["bygget"],
    )
    mappe = rot / "om"
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / "index.html"
    sti.write_text(html, encoding="utf-8")
    return sti


# ------------------------------------------------------ indeksene
#
# Flate lister, ingen paginering. Dette er sidene en crawler og en
# språkmodell følger for å finne alt annet, og en paginert liste er en
# liste der side 14 aldri blir lest. MÅLT: 1782 + 13 + 481 rader.
#
# Hver indeks er sin egen mal, ikke én generisk: kolonnene er ulike, og
# en generisk tabell ville enten vist minste felles nevner eller fått en
# `if` per sidetype. Malene er korte nok til at tre av dem er billigere
# enn én med forgreninger.


def bygg_lokalitetsindeks(felles: Felles) -> dict:
    """Alle lokaliteter, sortert på nummer."""
    rader = [{
        "loknr": loknr,
        "navn": a.get("navn", ""),
        "kommune": a.get("kommune", ""),
        "fylke": a.get("fylke", ""),
        "po_kode": a.get("prodomraade_kode", ""),
        "arter": visningsord.verdi("arter", a.get("arter", "")),
    } for loknr, a in felles.akva.items()]
    rader.sort(key=lambda r: int(r["loknr"]) if r["loknr"].isdigit() else 0)
    return {"rader": rader, "antall": len(rader),
            "akva_dato": felles.akva_dato,
            "uten_po": sum(1 for r in rader if not r["po_kode"])}


def bygg_poindeks(felles: Felles) -> dict:
    """De tretten produksjonsområdene, med nyeste farge."""
    rader = []
    for po in sorted(felles.po_navn, key=lambda k: int(k) if k.isdigit() else 0):
        runder = _fargerader(po, felles)
        siste = runder[-1] if runder else None
        rader.append({
            "nr": po,
            "navn": felles.po_navn[po],
            "lokaliteter": len(felles.lokaliteter_per_po.get(po, ())),
            "siste_runde": siste["aar"] if siste else "",
            "farge": siste["farge"] if siste else "",
            "farge_felt": siste["farge_felt"] if siste else "farge",
            "farge_klasse": siste["farge_klasse"] if siste else "",
            "lesemaate": siste["lesemaate"] if siste else "",
        })
    return {"rader": rader, "antall": len(rader),
            "akva_dato": felles.akva_dato,
            "uten_po": sum(1 for a in felles.akva.values()
                           if not (a.get("prodomraade_kode") or "").strip())}


def bygg_selskapsindeks(felles: Felles) -> dict:
    """Selskapene med minst én tillatelse, sortert på navn.

    Eiere kilden klassifiserer som person står IKKE her og har ingen
    side — men antallet gjør, slik at utelatelsen ikke er stille. Se
    `personeier()`.
    """
    rader, personer = [], 0
    for orgnr in sorted(felles.tillatelser_per_eier):
        if personeier(orgnr, felles):
            personer += 1
            continue
        tillatelser = felles.tillatelser_per_eier[orgnr]
        navn = ""
        for nr in tillatelser:
            navn = (felles.eierskap[nr].get("eier_navn") or "").strip() or navn
            if navn:
                break
        lok = {l for nr in tillatelser
               for l in _liste(felles.eierskap[nr].get("lokaliteter"))}
        rader.append({
            "orgnr": orgnr,
            "navn": navn,
            "tillatelser": len(tillatelser),
            "lokaliteter": len(lok),
            "har_registerdata": orgnr in felles.enhet,
        })
    rader.sort(key=lambda r: (r["navn"] or "ÅÅÅ", r["orgnr"]))
    return {"rader": rader, "antall": len(rader),
            "eierskap_dato": felles.eierskap_dato,
            "uten_registerdata": sum(1 for r in rader
                                     if not r["har_registerdata"]),
            "personeiere": personer}


def _skriv_indeks(rot: Path, sti: str, mal_navn: str, data: dict,
                  tittel: str, beskrivelse: str, kilder: tuple,
                  felles: Felles) -> Path:
    """Én indeksside. Samme form for alle tre."""
    mal = _miljo().get_template(mal_navn)
    html = mal.render(
        d=data, tittel=tittel, beskrivelse=beskrivelse,
        jsonld=_script_trygg({
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": tittel,
            "description": beskrivelse,
            "inLanguage": "nb",
        }),
        attribusjon=attribusjon(kilder, felles.vilkaar),
        stilark=stilsti(rot / sti / "index.html", rot),
        bygget=dt.date.today().isoformat(),
    )
    mappe = rot / sti
    mappe.mkdir(parents=True, exist_ok=True)
    ut_sti = mappe / "index.html"
    ut_sti.write_text(html, encoding="utf-8")
    return ut_sti


def skriv_indekser(rot: Path, felles: Felles) -> list[Path]:
    """De tre indekssidene."""
    return [
        _skriv_indeks(
            rot, "lokalitet", "indeks-lokalitet.html.j2",
            bygg_lokalitetsindeks(felles),
            "Alle akvakulturlokaliteter — havbruk-radar",
            "Flat liste over alle norske akvakulturlokaliteter med "
            "nummer, navn, kommune og produksjonsområde.",
            ("akvakultur",), felles),
        _skriv_indeks(
            rot, "produksjonsomrade", "indeks-produksjonsomrade.html.j2",
            bygg_poindeks(felles),
            "Alle produksjonsområder — havbruk-radar",
            "De tretten produksjonsområdene med nyeste trafikklysfarge "
            "og antall lokaliteter.",
            ("akvakultur", "trafikklysvedtak"), felles),
        _skriv_indeks(
            rot, "selskap", "indeks-selskap.html.j2",
            bygg_selskapsindeks(felles),
            "Alle selskaper med akvakulturtillatelse — havbruk-radar",
            "Flat liste over selskaper som eier minst én "
            "akvakulturtillatelse, med antall tillatelser og lokaliteter.",
            ("eierskap", "enhetsregisteret"), felles),
    ]


# ---------------------------------------------------------- kartet
#
# Statisk SVG, generert ved bygging. Ingen karttjeneste, ingen
# JavaScript, ingen flis hentet i runtime — kartet skal virke om ti år
# uten at noen fornyer en nøkkel. Samme begrunnelse som at siden ikke
# tegnes av JS: se modulens docstring.
#
# PROJEKSJONEN er ekvirektangulær med breddekorreksjon: lengdegrader
# klemmes sammen mot polene, og uten `cos(lat)` blir Finnmark dobbelt så
# bredt som det er. Det er ikke en kartografisk projeksjon med et navn og
# en EPSG-kode — det er den enkleste transformasjonen som gir et bilde
# ingen blir lurt av, og valget står her framfor i et bibliotek fordi et
# bibliotek er en avhengighet til.
#
# MÅLT 20.09.2026: 1782 lokaliteter, lat 58,021-71,017, lon 4,633-31,027.

KART_BREDDE = 900          # px i viewBox. Høyden følger av utstrekningen.
KART_MARG = 12
KART_PUNKT = 2.0           # radius. MÅLT 20.09.2026: ved 1.7 er et punkt
                           # 3,4px i diameter på full bredde og 2,1px når
                           # kartet er skalert til gulvet på telefon (30rem
                           # i sin egen scrollramme — se `.kart` i
                           # stil.css). Fyllet er halvgjennomsiktig, og en
                           # blek 2-pikselprikk forsvinner. 2.0 kjøper
                           # tilbake den pikselen. Overlappet stiger fra
                           # 78,3 % til 84,2 % av punktene, og det er
                           # prisen: tettheten leses av fyllet, ikke av
                           # at prikkene er atskilte.


# GRADNETTET. Trinnene er ulike fordi gradene er det: på 64 grader nord
# er en lengdegrad 0,44 av en breddegrad i bredde, og et nett med samme
# trinn på begge akser ville gitt tre vannrette linjer og tjueseks
# loddrette. Trinnene under gir 3 og 6 på dagens utstrekning.
#
# HVORFOR ET GRADNETT I DET HELE TATT: kartet har ingen kystlinje, og det
# er et bevisst valg — vi har ingen kystlinje vi har lisens til å tegne
# (se docs/LISENSKJEDE.md). Følgen fram til 21.09.2026 var at kartet var
# 1782 prikker uten en eneste referanse: en leser kunne se at det er tett
# på midten, men ikke om den tettheten ligger i Trøndelag eller i Troms.
#
# Et gradnett krever ingen lisens. Det er aritmetikk, ikke en gjengivelse
# av noens datasett, og det er den ENESTE referansen vi kan tegne uten å
# låne noe. 65 grader nord deler landet omtrent ved Rørvik; 70 ligger
# like nord for Tromsø. Det er nok til å plassere en klynge.
GITTER_LAT = 5             # grader mellom vannrette linjer
GITTER_LON = 5             # grader mellom loddrette linjer


def kartpunkter(akva: dict[str, dict[str, str]]) -> tuple[list[dict], list[str], float, dict]:
    """(punkter, lokaliteter uten koordinater, høyde på viewBox, gradnett).

    Punktene er avrundet til én desimal. Full flyttallspresisjon i en
    SVG er 1782 tall med femten siffer som ingen ser forskjell på, og
    fila blir dobbelt så stor.

    Lokaliteter uten koordinater UTELATES fra kartet og returneres for
    seg. Et punkt som mangler skal ikke bare forsvinne — se
    docs/REGEL-UENIGE-KILDER.md, som er den samme regelen i et annet
    format.
    """
    med, uten = [], []
    for loknr, a in akva.items():
        bredde = (a.get("breddegrad") or "").strip()
        lengde = (a.get("lengdegrad") or "").strip()
        try:
            med.append((loknr, float(bredde), float(lengde)))
        except ValueError:
            uten.append(loknr)

    if not med:
        return ([], sorted(uten, key=lambda e: int(e) if e.isdigit() else 0),
                0.0, {"bredde": [], "lengde": []})

    lat_min = min(p[1] for p in med)
    lat_maks = max(p[1] for p in med)
    lon_min = min(p[2] for p in med)
    lon_maks = max(p[2] for p in med)
    # Breddekorreksjonen tas på MIDTBREDDEN og ikke per punkt: en
    # korreksjon per punkt ville krummet kysten, som er en annen
    # projeksjon enn den vi sier at vi bruker.
    k = math.cos(math.radians((lat_min + lat_maks) / 2))

    bredde_grader = (lon_maks - lon_min) * k or 1.0
    hoyde_grader = (lat_maks - lat_min) or 1.0
    skala = (KART_BREDDE - 2 * KART_MARG) / bredde_grader
    hoyde = hoyde_grader * skala + 2 * KART_MARG

    punkter = [{
        "loknr": loknr,
        "x": round(KART_MARG + (lon - lon_min) * k * skala, 1),
        # y vokser nedover i SVG, breddegrad oppover.
        "y": round(KART_MARG + (lat_maks - lat) * skala, 1),
    } for loknr, lat, lon in med]
    punkter.sort(key=lambda p: (p["y"], p["x"]))

    # Linjene tegnes bare der det faktisk er kart. En linje på 55 grader
    # ville stått utenfor utstrekningen og sagt at nettet dekker noe
    # dataene ikke gjør.
    def _trinn(fra: float, til: float, steg: int) -> list[int]:
        forste = int(math.ceil(fra / steg) * steg)
        return [g for g in range(forste, int(til) + 1, steg)]

    # Etikettposisjonene regnes HER og ikke i malen. `{{ h - 8 }}` i
    # Jinja ga `1018.5999999999999` i utputtet: flyttallsstøy i en
    # koordinat ingen ser, i en fil som skal være lesbar.
    #
    # Den siste lengdegradsetiketten flyttes til VENSTRE for linja si.
    # 30°Ø ligger 40px fra kanten, og en etikett til høyre ville blitt
    # klippet av viewBox-en.
    #
    # BREDDEGRADENE STÅR TIL HØYRE, og det er ikke en smakssak.
    # Førsteutkastet satte dem ved venstre kant, der de er vant til å
    # stå — og der ligger kysten. «60°N» lå midt oppi klyngen i
    # Rogaland og Hordaland og var uleselig. Høyre halvdel av kartet er
    # Finnmarksvidda og åpent hav: tom.
    lengde = []
    for i, g in enumerate(_trinn(lon_min, lon_maks, GITTER_LON)):
        x = round(KART_MARG + (g - lon_min) * k * skala, 1)
        sist = x > KART_BREDDE - 60
        lengde.append({"x": x, "grad": g, "etikett": f"{g}°Ø",
                       "etikett_x": round(x - 6 if sist else x + 6, 1),
                       "etikett_anker": "end" if sist else "start"})
    gitter = {
        "bredde": [{"y": round(KART_MARG + (lat_maks - g) * skala, 1),
                    "grad": g, "etikett": f"{g}°N",
                    "etikett_x": KART_BREDDE - 6,
                    "etikett_y": round(KART_MARG + (lat_maks - g) * skala - 5, 1)}
                   for g in _trinn(lat_min, lat_maks, GITTER_LAT)],
        "lengde": lengde,
        "bredde_px": KART_BREDDE,
        "hoyde_px": round(hoyde, 1),
        "etikett_y_bunn": round(hoyde - 8, 1),
    }
    return (punkter,
            sorted(uten, key=lambda e: int(e) if e.isdigit() else 0),
            round(hoyde, 1), gitter)


FORSIDEKILDER = ("akvakultur", "eierskap", "lusetall")


def bygg_forside(felles: Felles) -> dict:
    """Tallene og kartet forsiden viser.

    Forsiden skal svare en fremmed på tre ting: hva er dette, hvem lagde
    det, hva kan jeg gjøre her. Tallene er det første svaret — en
    påstand om omfang som kan etterprøves ved å klikke.
    """
    punkter, uten_koordinater, hoyde, gitter = kartpunkter(felles.akva)
    uten = [{"loknr": loknr, "navn": felles.akva[loknr].get("navn", ""),
             "kommune": felles.akva[loknr].get("kommune", "")}
            for loknr in uten_koordinater]
    uker = len(felles.lusetall_snapshots)
    return {
        "lokaliteter": len(felles.akva),
        "produksjonsomraader": len(felles.po_navn),
        "selskaper": sum(1 for o in felles.tillatelser_per_eier
                         if not personeier(o, felles)),
        "tillatelser": len(felles.eierskap),
        "luke_uker": uker,
        "lus_fra": felles.lusetall_snapshots[0] if uker else "",
        "lus_til": felles.lusetall_snapshots[-1] if uker else "",
        "akva_dato": felles.akva_dato,
        "eierskap_dato": felles.eierskap_dato,
        "punkter": punkter,
        "punkter_antall": len(punkter),
        "kart_bredde": KART_BREDDE,
        "kart_hoyde": hoyde,
        "kart_punkt": KART_PUNKT,
        "gitter": gitter,
        "uten_koordinater": uten,
        "uten_koordinater_antall": len(uten),
    }


def skriv_forside(rot: Path, felles: Felles, mal=None) -> Path:
    """Rendrer og skriver forsiden."""
    f = bygg_forside(felles)
    mal = mal or _miljo().get_template("forside.html.j2")
    html = mal.render(
        f=f,
        tittel="havbruk-radar — norske akvakulturlokaliteter, uke for uke",
        beskrivelse=(
            f"Offentlige registerdata om {f['lokaliteter']} norske "
            f"akvakulturlokaliteter, sammenstilt og datert: eierskap, "
            f"trafikklysfarge, lusetall og hva som har endret seg."),
        jsonld=jsonld_forside(f, felles.vilkaar),
        attribusjon=attribusjon(FORSIDEKILDER, felles.vilkaar),
        stilark=stilsti(rot / "index.html", rot),
        bygget=dt.date.today().isoformat(),
    )
    sti = rot / "index.html"
    rot.mkdir(parents=True, exist_ok=True)
    sti.write_text(html, encoding="utf-8")
    return sti


def jsonld_forside(f: dict, vilkaar: dict) -> Markup:
    """schema.org/Dataset for hele samlingen."""
    kilder = []
    for kilde in FORSIDEKILDER:
        node = {"@type": "Dataset", "name": kilde,
                "creditText": (vilkaar.get(kilde) or ("",))[0]}
        if kilde in UTGIVER:
            node["provider"] = {"@type": "Organization", "name": UTGIVER[kilde]}
        if kilde in LISENS_URL:
            node["license"] = LISENS_URL[kilde]
        kilder.append(node)
    data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "havbruk-radar — norske akvakulturlokaliteter uke for uke",
        "description": (
            f"Sammenstilte offentlige registerdata om {f['lokaliteter']} "
            f"norske akvakulturlokaliteter: hvem som eier tillatelsene, "
            f"trafikklysfargen i produksjonsområdet, ukentlige lusetall og "
            f"hva som har endret seg i registrene."),
        "inLanguage": "nb",
        "dateModified": f["akva_dato"],
        "isBasedOn": kilder,
        "creator": {"@type": "Person", "name": "Heine Valø Nordbøe"},
        "spatialCoverage": {"@type": "Place", "name": "Norge"},
    }
    if f["luke_uker"]:
        data["temporalCoverage"] = f"{f['lus_fra']}/{f['lus_til']}"
    return _script_trygg(data)


# ------------------------------------------------------ selskapene
#
# Én side per organisasjonsnummer som eier minst én tillatelse i nyeste
# eierskap-snapshot. MÅLT 20.09.2026: 482 eiere, hvorav 360 finnes i
# enhetsregisteret og 122 ikke gjør det.
#
# HVEM SOM IKKE FÅR SIDE, og hvorfor det ikke er en mangel:
#
#   1383 selskaper i enhetsregisteret uten tillatelse. De er i utvalget
#        vårt på næringskode, men eier ingen akvakulturtillatelse.
#     84 tillatelser med en eier vi ikke kan navngi — 55 privatpersoner
#        (kilden oppgir ikke nummeret) og 29 med ukjent type. De har
#        ingen eier å lage en side for, og regel 3 forbyr å lage en.
#
# Den andre gruppa er hele grunnen til uenighetsregelen: en lokalitet
# der eieren ikke er oppgitt skal IKKE kunne dukke opp under et selskap
# som ikke eier den. Her følger det av konstruksjonen — sidens
# tillatelser er de som har DETTE organisasjonsnummeret i `eier_orgnr`,
# og en tillatelse uten eier har ingen — men det er en invariant verdt en
# test, ikke en tilfeldighet. Se docs/REGEL-UENIGE-KILDER.md.

# Feltene fra enhetsregisteret som vises, i rekkefølge. En liste og ikke
# «alt vi har»: registeret bærer felter vi henter for analyse og ikke for
# visning, og en side som dumpet alt ville vokst av seg selv neste gang
# kilden utvides.
SELSKAPSFELT = (
    "navn", "organisasjonsform", "kommune", "postnummer", "poststed",
    "naeringskode", "registreringsdato", "stiftelsesdato",
    "antall_ansatte", "aksjekapital", "konkurs", "under_avvikling",
    "under_tvangsavvikling", "registrert_i_foretaksregisteret",
    "siste_innsendte_aarsregnskap", "er_i_konsern",
)

# Teksten når vi ikke har registerdata for eieren i det hele tatt.
# 122 av 482. Ikke en tom tabell — samme regel som `EIER_UKJENT`.
UTEN_REGISTERDATA = ("selskapet står ikke i vårt enhetsregister-uttrekk")

SELSKAPSKILDER = ("akvakultur", "eierskap", "eierskap_historikk",
                  "enhetsregisteret")


def personeier(orgnr: str, felles: Felles) -> bool:
    """Klassifiserer KILDEN denne eieren som en person?

    Lesedøra fjerner entiteter med `organisasjonsform` i en personsektor.
    Den er blind for eiere der snapshotet bare bærer pub-aquas eget ord:
    H-FJ-0018 har `eier_type = JointlyOwnedShippingCompany` og ingen
    oversatt form i snapshotene fra 02.09 og 14.09, fordi `FORM_KART`
    ikke kjente typen da de ble skrevet. Se sektornotatets punkt 7.2.

    På en lokalitetsside er følgen én rad. På en SELSKAPSSIDE er følgen
    en hel side om et partrederi — altså om navngitte mennesker — og et
    URL-rom er en liste over hvem som finnes selv om siden er tom. MÅLT
    20.09.2026 fanget porten den: tre funn på
    `/selskap/954744469/index.html`.

    Spørsmålet stilles til KILDEN og ikke til `core/`: oversettelsen
    mellom pub-aquas ord og Brregs koder bor i
    `sources/eierskap.FORM_KART`, og kjernen skal ikke lære den. Samme
    delegering som `Source.fjern_egne_personer()`.

    Dette er IKKE B1 fra 18.09 gjenåpnet. B1 var å la lesedøra fjerne
    raden for alle lesere; dette er publiseringsleddet som lar være å
    lage en SIDE. Raden står som før på lokalitetssiden, og forsvinner
    derfra ved neste eierskap-kjøring.
    """
    from sources.eierskap import er_person

    for nr in felles.tillatelser_per_eier.get(orgnr, ()):
        if er_person((felles.eierskap.get(nr) or {}).get("eier_type")):
            return True
    return False


def bygg_selskap(orgnr: str, felles: Felles) -> dict:
    """Alt én selskapsside trenger.

    Tillatelsene bygges av `_tillatelsesrader()`, den samme funksjonen
    lokalitetssiden bruker. To veier til den samme raden er formen F6 og
    F7 hadde — og her er det ekstra viktig, for raden bærer hvem som eier
    hva.
    """
    tillatelser = sorted(felles.tillatelser_per_eier.get(orgnr, ()))
    mine = {nr: felles.eierskap[nr] for nr in tillatelser}

    # Navnet tas fra EIERSKAP og ikke fra enhetsregisteret: det er der
    # koblingen til tillatelsen står, og for de 122 uten registerdata er
    # det det eneste navnet vi har.
    navn = ""
    for d in mine.values():
        navn = (d.get("eier_navn") or "").strip() or navn
        if navn:
            break

    reg = felles.enhet.get(orgnr) or {}
    # Samme tre ledd som lokalitetssidens registertabell: kildens
    # feltnavn til `data-felt`, etiketten til øyet, verdien oversatt.
    register = [(f, visningsord.felt(f), visningsord.verdi(f, reg[f]))
                for f in SELSKAPSFELT if reg.get(f)]

    # Lokalitetene tillatelsene ligger på. En tillatelse kan ligge på
    # flere, og flere tillatelser kan ligge på samme — derfor et sett,
    # sortert som tall.
    lokaliteter: dict[str, dict] = {}
    for nr in tillatelser:
        for loknr in _liste(mine[nr].get("lokaliteter")):
            a = felles.akva.get(loknr)
            if a is None:
                continue
            lokaliteter.setdefault(loknr, {
                "loknr": loknr,
                "navn": a.get("navn", ""),
                "kommune": a.get("kommune", ""),
                "po_kode": a.get("prodomraade_kode", ""),
                "po_navn": a.get("prodomraade_navn", ""),
            })

    # SIDEN NÅR: overføringene TIL dette selskapet, eldst først.
    # `journal_dato` er «senest da» og ikke «akkurat da» — forbeholdet
    # står på hver rad i dataene og i tabellens caption.
    overforinger = sorted(
        ({"dato": o.get("journal_dato", ""),
          "tillatelse": o.get("tillatelse_nr", ""),
          "rekkefolge": o.get("rekkefolge", "")}
         for nr in tillatelser
         for o in felles.overforinger_per_tillatelse.get(nr, ())
         if (o.get("mottaker_orgnr") or "").strip() == orgnr),
        key=lambda o: (o["dato"], o["tillatelse"]))

    return {
        "orgnr": orgnr,
        "navn": navn,
        "har_registerdata": bool(register),
        "register": register,
        "uten_registerdata_tekst": UTEN_REGISTERDATA,
        "enhet_dato": felles.enhet_dato,
        "eierskap_dato": felles.eierskap_dato,
        "akva_dato": felles.akva_dato,
        "tillatelser": _tillatelsesrader(mine, []),
        "tillatelser_antall": len(tillatelser),
        "lokaliteter": [lokaliteter[k] for k in
                        sorted(lokaliteter, key=lambda e: int(e) if e.isdigit() else 0)],
        "lokaliteter_antall": len(lokaliteter),
        "overforinger": overforinger,
    }


def jsonld_selskap(sel: dict, vilkaar: dict) -> Markup:
    """schema.org/Dataset for selskapssiden.

    `identifier` er organisasjonsnummeret med `propertyID` som sier hvem
    som har tildelt det. Ingen `url`, av samme grunn som ellers.
    """
    kilder = []
    for kilde in SELSKAPSKILDER:
        node = {"@type": "Dataset", "name": kilde,
                "creditText": (vilkaar.get(kilde) or ("",))[0]}
        if kilde in UTGIVER:
            node["provider"] = {"@type": "Organization", "name": UTGIVER[kilde]}
        if kilde in LISENS_URL:
            node["license"] = LISENS_URL[kilde]
        kilder.append(node)
    return _script_trygg({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{sel['navn'] or sel['orgnr']} — akvakulturtillatelser "
                f"og lokaliteter",
        "description": (
            f"Hvilke akvakulturtillatelser organisasjonsnummer "
            f"{sel['orgnr']} eier, hvilke {sel['lokaliteter_antall']} "
            f"lokaliteter de ligger på, og når tillatelsene ble overført "
            f"til selskapet."),
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "Organisasjonsnummer (Brønnøysundregistrene)",
            "value": sel["orgnr"],
        },
        "inLanguage": "nb",
        "dateModified": sel["eierskap_dato"],
        "isBasedOn": kilder,
        "creator": {"@type": "Organization", "name": "havbruk-radar"},
    })


def skriv_selskap(orgnr: str, rot: Path, felles: Felles, mal=None) -> Path:
    """Rendrer og skriver én selskapsside."""
    sel = bygg_selskap(orgnr, felles)
    setninger = attribusjon(SELSKAPSKILDER, felles.vilkaar)
    mal = mal or _miljo().get_template("selskap.html.j2")
    html = mal.render(
        sel=sel,
        tittel=f"{sel['navn'] or sel['orgnr']} — havbruk-radar",
        beskrivelse=(
            f"Akvakulturtillatelser, lokaliteter og overføringer for "
            f"organisasjonsnummer {sel['orgnr']}"
            f"{' (' + sel['navn'] + ')' if sel['navn'] else ''}."),
        jsonld=jsonld_selskap(sel, felles.vilkaar),
        attribusjon=setninger,
        stilark=stilsti(rot / "selskap" / orgnr / "index.html", rot),
        bygget=dt.date.today().isoformat(),
    )
    mappe = rot / "selskap" / orgnr
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / "index.html"
    sti.write_text(html, encoding="utf-8")
    return sti


# Kildene en produksjonsområdeside bygger på. `ekspertgruppen` står
# IKKE her: kilden er UBELAGT, og en side som oppgav den i bunnteksten
# ville påstått et vilkår ingen har gått god for.
PO_KILDER = ("akvakultur", "trafikklysvedtak")


def jsonld_po(po: dict, vilkaar: dict) -> Markup:
    """schema.org/Dataset for produksjonsområdesiden.

    Ingen `url`, som på lokalitetssiden: domenet finnes ikke ennå, og en
    absolutt URL med et påfunnet vertsnavn ville vært en påstand om noe
    som ikke er avgjort. `identifier` bærer PO-nummeret med `propertyID`
    som sier hvem som har fastsatt det.
    """
    kilder = []
    for kilde in PO_KILDER:
        node = {"@type": "Dataset", "name": kilde,
                "creditText": (vilkaar.get(kilde) or ("",))[0]}
        if kilde in UTGIVER:
            node["provider"] = {"@type": "Organization", "name": UTGIVER[kilde]}
        if kilde in LISENS_URL:
            node["license"] = LISENS_URL[kilde]
        kilder.append(node)
    data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"Produksjonsområde {po['nr']} {po['navn']} — "
                f"trafikklysfarge per runde og lokaliteter",
        "description": (
            f"Trafikklysfargen for produksjonsområde {po['nr']} "
            f"{po['navn']} i hver fastsatt runde, med lesemåte, og de "
            f"{po['lokaliteter_antall']} akvakulturlokalitetene i området."),
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "Produksjonsområdenummer fastsatt i forskrift "
                          "(Nærings- og fiskeridepartementet)",
            "value": po["nr"],
        },
        "inLanguage": "nb",
        "dateModified": po["akva_dato"],
        "isBasedOn": kilder,
        "creator": {"@type": "Organization", "name": "havbruk-radar"},
    }
    if po["runder"]:
        data["temporalCoverage"] = (f"{po['runder'][0]['aar']}/"
                                    f"{po['runder'][-1]['aar']}")
    return _script_trygg(data)


def skriv_produksjonsomrade(po: str, rot: Path, felles: Felles,
                            mal=None) -> Path:
    """Rendrer og skriver én produksjonsområdeside."""
    d = bygg_produksjonsomrade(po, felles)
    setninger = attribusjon(PO_KILDER, felles.vilkaar)   # kaster på UBELAGT
    mal = mal or _miljo().get_template("produksjonsomrade.html.j2")
    html = mal.render(
        po=d,
        tittel=f"Produksjonsområde {d['nr']} {d['navn']} — havbruk-radar",
        beskrivelse=(
            f"Trafikklysfarge per runde for produksjonsområde {d['nr']} "
            f"{d['navn']}, med lesemåte, og de {d['lokaliteter_antall']} "
            f"lokalitetene i området."),
        jsonld=jsonld_po(d, felles.vilkaar),
        attribusjon=setninger,
        stilark=stilsti(rot / "produksjonsomrade" / po / "index.html", rot),
        bygget=dt.date.today().isoformat(),
    )
    mappe = rot / "produksjonsomrade" / po
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / "index.html"
    sti.write_text(html, encoding="utf-8")
    return sti


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
    po_sider: int = 0
    selskapssider: int = 0
    indekssider: int = 0
    selskap_uten_registerdata: list[str] = None
    selskap_person: list[str] = None
    uten_eier: list[str] = None
    uten_tillatelser: list[str] = None
    uten_koordinater: list[str] = None
    uten_lusetall: list[str] = None
    uten_prodomraade: list[str] = None
    uten_endringer: list[str] = None
    feilet: list[tuple[str, str]] = None

    def __post_init__(self):
        for felt in ("selskap_uten_registerdata", "selskap_person",
                     "uten_eier", "uten_tillatelser", "uten_koordinater",
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

    # PRODUKSJONSOMRÅDENE. Samme `felles`, egen mal, egen fase i
    # tidsmålingen — en fase som ikke måles er en fase ingen ser vokse.
    t0 = time.perf_counter()
    po_mal = _miljo().get_template("produksjonsomrade.html.j2")
    for po in sorted(felles.po_navn, key=lambda k: int(k) if k.isdigit() else 0):
        try:
            skriv_produksjonsomrade(po, rot, felles, po_mal)
        except Exception as feil:                    # noqa: BLE001
            logg.feilet.append((f"po/{po}", f"{type(feil).__name__}: {feil}"))
            continue
        logg.po_sider += 1
    tider["produksjonsomraader"] = time.perf_counter() - t0

    # SELSKAPENE. Én side per organisasjonsnummer som eier minst én
    # tillatelse. De 122 uten registerdata får side de også — siden sier
    # at vi ikke har dataene, framfor å ikke finnes.
    t0 = time.perf_counter()
    sel_mal = _miljo().get_template("selskap.html.j2")
    for orgnr in sorted(felles.tillatelser_per_eier):
        if personeier(orgnr, felles):
            # Ingen side, og ingen stillhet: tallet står i byggeloggen og
            # på indekssiden. Se `personeier()`.
            logg.selskap_person.append(orgnr)
            continue
        try:
            skriv_selskap(orgnr, rot, felles, sel_mal)
        except Exception as feil:                    # noqa: BLE001
            logg.feilet.append((f"selskap/{orgnr}",
                                f"{type(feil).__name__}: {feil}"))
            continue
        logg.selskapssider += 1
        if orgnr not in felles.enhet:
            logg.selskap_uten_registerdata.append(orgnr)
    tider["selskaper"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        skriv_forside(rot, felles)
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("forside", f"{type(feil).__name__}: {feil}"))
    tider["forside"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        logg.indekssider = len(skriv_indekser(rot, felles))
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("indekser", f"{type(feil).__name__}: {feil}"))
    try:
        skriv_om(rot, felles)
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("om", f"{type(feil).__name__}: {feil}"))
    tider["indekser"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    for skriv in (lambda: skriv_stil(rot),
                  lambda: skriv_fonter(rot),
                  lambda: skriv_sitemap(rot, felles),
                  lambda: skriv_robots(rot),
                  lambda: skriv_llms(rot, felles)):
        try:
            skriv()
        except Exception as feil:                    # noqa: BLE001
            logg.feilet.append(("maskinfiler", f"{type(feil).__name__}: {feil}"))
    tider["maskinfiler"] = time.perf_counter() - t0

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
    publiseringsvakt._rapport(funn)

    # Kvitterte funn STÅR, og de skrives alltid. Exit 0 med kvitterte
    # funn skal aldri kunne leses som «ingen funn» — det er hele skillet
    # mellom en kvittering og en bryter. `ukvittert()` er det ene stedet
    # som avgjør hva som feller publiseringen; to steder som skulle svart
    # det samme er formen F6 og F7 hadde.
    kvitterte = [f for f in funn if f.kvittert]
    if kvitterte:
        print(f"\n{len(kvitterte)} funn er KVITTERT UT:")
        for f in kvitterte:
            print(f"  {f}")

    igjen = publiseringsvakt.ukvittert(funn)
    if not igjen:
        print(f"\n{rot}: ingen ukvitterte funn"
              f"{f' — de {len(kvitterte)} over står' if kvitterte else ''}.")
        return 0
    print(f"\n{len(igjen)} ukvitterte funn:")
    for f in igjen:
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
    print(f"\n{logg.sider} lokalitetssider + {logg.po_sider} "
          f"produksjonsområdesider + {logg.selskapssider} selskapssider "
          f"+ {logg.indekssider} indekssider skrevet til {rot}")
    print(f"  byggetid      {total:8.1f} s")
    for merke, t in tider.items():
        print(f"    {merke:22} {t:7.1f} s  ({t / total * 100:4.1f} %)")
    print(f"  på disk       {bytes_ / 1e6:8.1f} MB"
          f"  ({bytes_ / max(logg.sider, 1) / 1024:.0f} kB per side)")

    print("\n  ikke rent:")
    for merke, liste in (
            ("selskaper uten registerdata hos oss",
             logg.selskap_uten_registerdata),
            ("eiere kilden klassifiserer som person (ingen side)",
             logg.selskap_person),
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

    # KODER SOM FALT UT AV OVERSETTELSESTABELLEN. Skrives ALLTID, også
    # når den er tom — et tall man bare ser når det er galt, er et tall
    # ingen kjenner normalverdien til. En kode som ikke står i
    # `visningsord` vises ordrett, og det er riktig; det som ikke er
    # riktig er at «SALMON» står på siden igjen om et halvår uten at
    # noen la merke til det.
    ukjente = visningsord.ukjente_rapport()
    print(f"\n  koder uten norsk oversettelse            {len(ukjente):>5}")
    for linje in ukjente[:20]:
        print(f"      {linje}")


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
        filer = (skriv_lokalitet(args.lokalitet, rot)
                 + [skriv_stil(rot)] + skriv_fonter(rot))
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
