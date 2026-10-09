"""Bygger den publiserte nettsiden fra snapshotene.

    python nettsted.py                     # bygger, gransker, exit 1 ved funn
    python nettsted.py --lokalitet 31397   # bare den ene siden
    python nettsted.py --uten-vakt         # bygg uten porten (utvikling)
    python nettsted.py --vakt-kjores-av X  # porten kjøres av X, ikke her

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
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import lru_cache
from html import escape
from pathlib import Path

import polars as pl
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import beslutning                                          # noqa: E402
import kart                                                # noqa: E402
import nedlasting                                          # noqa: E402
import publiseringsvakt                                    # noqa: E402
import unntaksanalyse                                      # noqa: E402
import vesentlighet                                        # noqa: E402
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

# SKILLETEGNET I EN UNDERTITTEL. Samme tegn som undertitlene på sidene
# selv bruker — «Lokalitet 31397 · permanent klarering · i sjø» — så en
# trefflinje ser ut som linja den fører til.
SKILLE = " · "

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

# HVEM SOM STÅR BAK HVER ATTRIBUSJONSSETNING.
#
# Bunnteksten sa «verken Fiskeridirektoratet, Brønnøysundregistrene,
# BarentsWatch eller Mattilsynet går god for den» som fast tekst — fire
# navn skrevet inn for hånd. `trafikklysvedtak` siterer Lovdata, og
# produksjonsområdesiden siterer departementets egne ord fra
# regjeringen.no; ingen av dem var med, og ingenting sa fra.
#
# Nøkkelen er SETNINGEN og ikke kildenavnet, fordi setningen er det
# kilden faktisk har gått god for (`Source.attribusjon`). Kommer en ny
# setning til uten et navn her, kaster `fraskrivelse()` — en fraskrivelse
# som stilltiende utelater en rettighetshaver er verre enn ingen.
ANSVARLIG_FOR = {
    "Kilde: Fiskeridirektoratet": ("Fiskeridirektoratet",),
    "Inneholder data under Norsk lisens for offentlige data (NLOD) "
    "tilgjengeliggjort av Brønnøysundregistrene": ("Brønnøysundregistrene",),
    "Data levert av BarentsWatch": ("BarentsWatch",),
    "Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra "
    "Mattilsynet.": ("Mattilsynet",),
    "Kilde: Lovdata. Inneholder data under Norsk lisens for offentlige "
    "data (NLOD) 2.0": ("Lovdata",),
    # Søknadslista om unntaksvekst, fra mattilsynet.no — se
    # sources/unntaksvekst.py, `attribusjon`.
    "Kilde: Mattilsynet": ("Mattilsynet",),
    # Lakselusrapportene fra Mattilsynets åpne API — se `MATTILSYNET_API`.
    "Inneholder data under Norsk lisens for offentlige data (NLOD) "
    "tilgjengeliggjort av Mattilsynet": ("Mattilsynet",),
    # Ikke vist på noen side i dag — `reguleringsomraader` står i
    # lisenstabellen og ikke i `viste_kilder()`. Navnet står her likevel,
    # så den dagen et kart tar den i bruk, felles ikke bygget for en
    # setning ingen svarer for.
    "Havforskningsinstituttet, «Smittekontakt (lakselus) mellom "
    "oppdrettsanlegg og oppholdsområder for villfisk», CC BY 4.0":
        ("Havforskningsinstituttet",),
}


# ATTRIBUSJONSSETNINGER SOM SKAL VÆRE LENKER. BarentsWatchs vilkår
# (api-vilkar, sist oppdatert 02.11.2023, lest 06.10.2026): «All bruk av
# BarentsWatch API i applikasjoner skal derfor merkes med følgende tekst
# og lenkes til BarentsWatch om mulig». Setningen sto som ren tekst i
# bunnteksten fram til 06.10.2026. Nøkkelen er setningen, som i
# `ANSVARLIG_FOR`.
ATTRIBUSJONSLENKE = {
    "Data levert av BarentsWatch": "https://www.barentswatch.no/",
}


def fraskrivelse(kilder, vilkaar=None, i_tillegg=()) -> list[str]:
    """Organene en side skal si at IKKE går god for sammenstillingen.

    Utledet av `attribusjon()` — altså av setningene kildene selv krever
    — så fraskrivelsen og navngivingen ikke kan svare ulikt.

    `i_tillegg` er organ siden SITERER uten å ha en kilde for det.
    Produksjonsområdesiden gjengir departementets begrunnelse med lenke
    til regjeringen.no: det står i markupen, ikke i en
    `Source.attribusjon`, og en fraskrivelse som utelot det ville
    utelatt den ene parten hvis EGNE ORD står på siden.
    """
    ut: list[str] = []
    for setning in attribusjon(kilder, vilkaar):
        if setning not in ANSVARLIG_FOR:
            raise UbelagtKilde(
                f"ingen i ANSVARLIG_FOR svarer for attribusjonssetningen "
                f"{setning!r}. Bunntekstens fraskrivelse ville utelatt "
                f"rettighetshaveren i stillhet.")
        for organ in ANSVARLIG_FOR[setning]:
            if organ not in ut:
                ut.append(organ)
    for organ in i_tillegg:
        if organ not in ut:
            ut.append(organ)
    return ut


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


# ATTRIBUSJONEN FOR KARTGEOMETRIEN, som ikke kommer fra en `Source`.
#
# Kystlinja er Kartverkets, CC BY 4.0, og lisensen krever at navnet
# vises «i alle samanhengar der produkta eller uttrekk av produkta blir
# brukt … på følgjande måte: © Kartverket. Det skal også linkast til
# nettsidene våre der det er mogleg.» Ordrett fra vilkårssiden — se
# docs/LISENSKJEDE.md merknad J.
#
# Den bor HER og ikke på en kilde, fordi geometrien ikke er en kilde i
# `sources/`: den hentes for hånd, avledes av `verktoy/kystlinje.py` og
# tegnes inn i SVG-en ved bygging. `attribusjon()` kaster på et
# kildenavn ingen `Source` skriver under, og det skal den fortsette med.
#
# EN SIDE MED KART MÅ BÆRE DEN. Porten håndhever det — se
# `publiseringsvakt.kart_uten_attribusjon()`.
KARTVERKET = "© Kartverket"
KARTVERKET_URL = "https://www.kartverket.no"


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
                f"{kilde}: lisensvilkåret er lett etter og ikke funnet "
                f"(se docs/LISENSKJEDE.md). Siden bygges ikke. Lukk luken "
                f"med et spørsmål til utgiveren, ikke med mer kode.")
        for setning in indeks[kilde]:
            if setning not in ut:
                ut.append(setning)
    return ut


# ------------------------------------------------- DET HVER SIDE DELER
#
# Bunnteksten, menyen og proveniens­linja står på alle 2 279 sidene.
# Fram til 22.09.2026 sendte hver `skriv_*` inn sine egne fem
# nøkkelord, og `StrictUndefined` gjorde en glemt nøkkel til en
# byggefeil — men bare for den ene sidetypen. Med ni sidetyper er det
# ni steder å glemme den samme.
#
# `_grunnkontekst()` er det ene stedet. Den som legger til en ny
# sidetype får bunnteksten ved å kalle den, og en ny nøkkel i
# bunnteksten legges til her og virker overalt.

# Repoet, ett sted. Står i bunnteksten på hver side og på /om/.
REPO = "https://github.com/heinenordboe-cloud/havbruk-radar"


def _kontakt() -> str:
    """Adressen folk melder feil til, fra `nettsted.kontakt` i config.yml.

    Tom streng når den ikke står der, og bunnteksten SIER at den ikke er
    satt framfor å skrive en påfunnet adresse. Samme skille som
    `utvalg`: tom er fraværet av en verdi, ikke en verdi.

    IKKE fra miljøet. Fram til 07.10.2026 kom den fra `HAVBRUK_KONTAKT`,
    og da var adressen på siden en egenskap ved skallet som bygget — det
    samme bygget ga ulike sider på Heines maskin og i Actions. Variabelen
    brukes nå bare til User-Agent (`sources/_http.py`). Se config.yml.
    """
    from core import config

    return str(config.get("nettsted.kontakt", "") or "").strip()


def proveniens(observed_at: str, fetched_at: str, tillegg: str = "") -> str:
    """Setningen nederst på siden: hvilket øyeblikksbilde, og når hentet.

    TO TIDSPUNKTER, og skillet er CLAUDE.md 1b-7. `observed_at` er
    uka raden GJELDER FOR — verden. `fetched_at` er da VI spurte — oss.
    De faller nesten sammen når vi henter ferskt, og «nesten» er
    nøyaktig det som gjør at et repo klarer seg uten å skille dem helt
    til en kropp graves ut av et arkiv.

    Mangler hentetidspunktet, utelates leddet. Å skrive
    `observed_at` der ville vært å påstå at vi hentet på gyldighets-
    datoen, og det er den samme feilen `published_at`-regelen stengte.
    """
    uka = visningsord.uke(observed_at)
    linje = f"Bygget fra øyeblikksbildet for {uka}"
    hentet = visningsord.tidspunkt(fetched_at)
    if hentet:
        linje += f", hentet {hentet}"
    linje += "."
    if tillegg:
        linje += f" {tillegg}"
    return linje


def _grunnkontekst(felles: Felles | None, rot: Path, sti: Path, *,
                   tittel: str, beskrivelse: str, jsonld,
                   kilder, proveniens_tekst: str,
                   meny_aktiv: str = "", feed: str = "",
                   feed_tittel: str = "", main_klasse: str = "",
                   side_skript: str = "", siterte_organ=(),
                   sidetype: str = "", undertittel: str = "",
                   soketekst: str = "", kart: bool = False,
                   ekstra_attribusjon: tuple[str, ...] = ()) -> dict:
    """Nøklene `base.html.j2` krever, for hvilken som helst sidetype.

    `ekstra_attribusjon` er setninger for data som ikke kommer fra en
    `Source` — som `KARTVERKET` for kartet. Hver av dem må stå i
    `ANSVARLIG_FOR`, ellers kaster `fraskrivelse()`.
    """
    for setning in ekstra_attribusjon:
        if setning not in ANSVARLIG_FOR:
            raise UbelagtKilde(
                f"ingen i ANSVARLIG_FOR svarer for {setning!r}")
    siterte_organ = tuple(siterte_organ) + tuple(
        organ for s in ekstra_attribusjon for organ in ANSVARLIG_FOR[s])
    # DEN KANONISKE ADRESSEN, regnet ut av filstien og vertsnavnet.
    #
    # Ett sted. Fram til 23.09.2026 sto `https://kystloggen.no` som
    # bokstav fire steder i tillegg til `BASEURL` — tre `siter.url` og
    # én permalenke i en mal — og de gikk utenom `_basisurl()`. En
    # forhåndsvisning på pages.dev ville dermed fortalt leseren at den
    # var originalen, og bedt henne sitere en adresse som ikke serverte
    # innholdet.
    i_dag = dt.date.today().isoformat()
    return {
        "tittel": tittel,
        "beskrivelse": beskrivelse,
        # NETTSTEDETS EGEN ADRESSE, fra konfigurasjonen og ikke som
        # bokstav i en mal. Se `_basisurl()`.
        "basisurl": _basisurl(),
        # HVEM SOM IKKE GÅR GOD FOR DEN, utledet av kildenes egne
        # attribusjonssetninger. Se `fraskrivelse()`.
        "fraskrivelse": visningsord.liste(
            fraskrivelse(kilder, i_tillegg=siterte_organ), "eller"),
        "kanonisk": kanonisk_url(sti, rot),
        "jsonld": jsonld,
        # BUNNTEKSTENS SETNINGER, og Kartverkets i tillegg når siden
        # viser et kart. Lisensen krever navnet der produktet BRUKES,
        # og en side uten kart bruker det ikke.
        "attribusjon": (attribusjon(kilder,
                                    felles.vilkaar if felles else None)
                        + [s for s in ekstra_attribusjon]
                        + ([KARTVERKET] if kart else [])),
        "kartverket": KARTVERKET if kart else "",
        "kartverket_url": KARTVERKET_URL,
        "stilark": stilsti(sti, rot),
        "bygget": i_dag,
        "bygget_vist": visningsord.dato(i_dag),
        "proveniens": proveniens_tekst,
        "repo": REPO,
        "kontakt": felles.kontakt if felles else _kontakt(),
        "meny_aktiv": meny_aktiv,
        "feed": feed,
        "feed_tittel": feed_tittel,
        # Sidetypens eget skript, der den har ett. Bare `/sok/` i dag.
        "side_skript": side_skript,
        # `fullbredde` når sidetypen har seksjoner som går helt ut i
        # kanten og selv setter innholdsbredden med en indre `.ark`.
        # To lag sidemarg er dobbelt innrykk, og MÅLT ble forsidens
        # innhold stående 112 px inn der det skulle stått 56.
        "main_klasse": main_klasse,
        # ---- det søkeindeksen trenger, og bare det ----
        #
        # Pagefind leser HTML-en etter at hver side er skrevet, og har
        # ingen annen vei til å vite hva en side ER. `sidetype` blir et
        # filter og et felt i trefflista; `undertittel` er linja under
        # tittelen i trefflista, og `beskrivelse` er utdraget.
        #
        # ALLE TRE ER SIDENS EGNE, satt av sidetypen som bygger den. En
        # utledning av URL-en ville vært et andre sted sidetypen
        # bestemmes, og den ville tatt feil på /endringer/2026-39/ som er
        # en uke og ikke en endringstype.
        "sidetype": sidetype,
        "undertittel": undertittel,
        # ORD SOM SKAL VEIE TUNGT. Tittelen og kommunen — det en leser
        # skriver inn når hun leter etter et sted. De står allerede i
        # sidas tekst; her står de en gang til med vekt, og Pagefind
        # summerer vektene for det samme ordet.
        "soketekst": soketekst,
    }


# --------------------------------------------------------- lesing


def sidesti(sti: Path, rot: Path) -> str:
    """Filstien som URL-sti: `lokalitet/31397/index.html` -> `/lokalitet/31397/`.

    `index.html` faller bort, som i enhver statisk vert. Tom rot gir
    `/`.
    """
    rel = sti.relative_to(rot).as_posix()
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    return "/" + rel.lstrip("/")


def kanonisk_url(sti: Path, rot: Path) -> str:
    """Absolutt adresse for en side, eller den relative stien.

    Tom streng fra `_basisurl()` betyr «vi vet ikke hvor dette skal
    ligge», og da er en relativ sti det sanne svaret — ikke et påfunnet
    domene. Se kommentaren over `BASEURL`.
    """
    return _basisurl() + sidesti(sti, rot)


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
    fordi den kjenner regelen om at `.10` sorterer etter `.2`.

    ## KILDENS EGET TILLEGG kjøres her, ikke bare hos porten

    `snapshot.versjoner()` kjører lesedøra, og døra spør om
    `organisasjonsform` og `institusjonell_sektorkode`. For `eierskap`
    er begge `None` på en tillatelse der formen bare står i
    `eier_type` — CLAUDE.md regel 7 navngir nettopp den.

    `publiseringsvakt._rammene_for()` har kalt `fjern_egne_personer()`
    siden 19.09, og generatoren gjorde det ikke. To lesemåter av samme
    kilde som kan svare ulikt er formen F6 og F7 hadde, og her var
    retningen den farlige: porten så færre rader enn siden.
    """
    dato = snapshot.siste_dato(kilde)
    if dato is None:
        raise SystemExit(f"{kilde}: ingen snapshots i {DATA_DIR}")
    ramme = snapshot.versjoner(kilde, dato)[-1][1]
    return dato, _pivot(_uten_egne_personer(kilde, ramme))


def _uten_egne_personer(kilde: str, ramme):
    """Ramma etter kildens eget persontillegg. Urørt om kilden er ukjent.

    Samme kall og samme rekkefølgevern som
    `publiseringsvakt._rammene_for()`: en hook kan bare FJERNE.
    """
    from core import registry
    from core.contract import kilder_per_navn

    eier = kilder_per_navn(registry.discover()).get(kilde)
    if eier is None:
        return ramme
    etter = eier.fjern_egne_personer(ramme)
    if etter.height > ramme.height:
        raise ValueError(
            f"{kilde}.fjern_egne_personer() ga {etter.height} rader der "
            f"den fikk {ramme.height}. Hooken skal filtrere, ikke legge "
            f"til — se Source.fjern_egne_personer.")
    return etter


def _sjekksum(kilde: str) -> str:
    """`raw_hash` i nyeste snapshot av kilden. Tom når den mangler.

    ÉN verdi per snapshot: hashen er av KROPPEN kilden sendte, ikke av
    raden, så alle radene i en fil bærer den samme. Det er nettopp
    derfor den kan stå på forsiden som «sjekksum for dette
    øyeblikksbildet» — den identifiserer svaret vi fikk, og en
    etterprøving kan sammenligne mot arkivet i `data/arkiv/`.

    Skulle en fil bære flere, er den satt sammen av flere kropper, og da
    er det ingen ÉN sjekksum å oppgi. Tom streng er da svaret, ikke den
    første av dem.
    """
    dato = snapshot.siste_dato(kilde)
    if dato is None:
        return ""
    ramme = snapshot.versjoner(kilde, dato)[-1][1]
    if "raw_hash" not in ramme.columns:
        return ""
    verdier = [v for v in ramme["raw_hash"].unique().to_list() if v]
    return verdier[0] if len(verdier) == 1 else ""


def _hentet(kilde: str) -> str:
    """`fetched_at` i nyeste snapshot av kilden, eller tom streng.

    DETTE ER ET TIDSPUNKT OM OSS, ikke om verden. `observed_at` er
    datoen raden gjelder for, og den står i filnavnet; dette er da VI
    spurte. Proveniens­linja i bunnteksten oppgir begge, fordi en side
    som bare oppgir det ene lar leseren tro at de er det samme. Se
    CLAUDE.md 1b-7.

    Tom streng og ikke en gjetning når feltet mangler: et gammelt
    snapshot kan være skrevet før feltet fantes, og
    `visningsord.tidspunkt("")` gir tom streng videre.
    """
    dato = snapshot.siste_dato(kilde)
    if dato is None:
        return ""
    versjonene = snapshot.versjoner(kilde, dato)
    return snapshot.fetched_at_i(versjonene[-1][1]) or ""


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
    # NÅR VI HENTET, ikke hva raden gjelder for. Bunntekstens
    # proveniens­linje oppgir begge — se `_hentet()` og CLAUDE.md 1b-7.
    akva_hentet: str
    # Sjekksummen av nyeste akvakultur-snapshot. Står i arkivlinja på
    # forsiden og i siteringsboksen på hver lokalitetsside.
    sjekksum: str
    # Adressen folk melder feil til. Tom når `nettsted.kontakt` ikke står
    # i config.yml, og da SIER bunnteksten det framfor å finne på en.
    kontakt: str
    # HELE CHANGELOGGEN, filtrert av `diff.bevegelse()`. Ligger her og
    # ikke bak et nytt kall fordi lesingen koster 6 s, og fordi
    # `les_endringsuker()` og `registerendringer` ellers ville vært to
    # lesinger av det samme som kan svare ulikt — formen F6 og F7 hadde.
    bevegelse: pl.DataFrame
    # Trafikklysfargen slik AKVAKULTURREGISTERET oppgir den nå, per
    # produksjonsområde. En annen kilde enn `po_farger`, og den svarer
    # på et annet spørsmål — se `_po_naa()`.
    po_naa: dict[str, dict[str, str]]
    # {loknr: [uke]} — om det står fisk på lokaliteten, per uke VI har
    # observert. Se `_biomasselag()`.
    biomasselag: dict[str, list[dict]]
    biomasselag_uker: list[str]
    # {po: [måned]} — offentlige beholdningstall per produksjonsområde,
    # og {po: nyeste published_at}. Se `_biomasse()`.
    biomasse: dict[str, list[dict]]
    biomasse_utgitt: dict[str, str]
    # {(entity_id, felt): siste observed_at} — når vi sist SÅ feltet
    # endre seg. Brukes i «Sist endret»-kolonnen i registertabellene.
    sist_endret: dict[tuple[str, str], str]
    # {orgnr: formene kildene oppgir} — det `_navn_eller_skjult()` slår
    # opp i. Se `publiseringsvakt.formkart()`.
    former: dict[str, frozenset[str]] = field(default_factory=dict)
    # {loknr: [rad]} — Mattilsynets søknader om unntaksvekst med SIKKER
    # kobling til lokaliteten. Se `unntak_per_lokalitet()`.
    unntak: dict[str, list[dict]] = field(default_factory=dict)


@lru_cache(maxsize=1)
def _bokforingsfelt() -> frozenset[tuple[str, str]]:
    """{(kilde, felt)} kildene selv erklærer som bokføring.

    UTLEDET, aldri listet her. En liste i nettsted.py ville vært et andre
    sted sannheten kan bli stående gammel — samme grunn som
    `ukentlige_kilder()` og `kildevilkaar()` gir, og samme regel som
    CLAUDE.md 1: en ny kilde skal ikke kreve en endring her.
    """
    from core import registry
    from core.contract import erklaert_bokforing

    ut: set[tuple[str, str]] = set()
    for kilde in registry.discover():
        ut |= erklaert_bokforing(kilde)
    return frozenset(ut)


@lru_cache(maxsize=1)
def _avledede_felt() -> dict[tuple[str, str], str]:
    """{(kilde, avledet felt): grunnfelt}, kildenes egen erklæring."""
    from core import registry
    from core.contract import erklaert_avledning

    ut: dict[tuple[str, str], str] = {}
    for kilde in registry.discover():
        ut.update(erklaert_avledning(kilde))
    return ut


def uten_bokforing(beveg: pl.DataFrame) -> pl.DataFrame:
    """Radene om RAPPORTERINGEN ut av det nettstedet leser.

    En lesedør, ikke en opprydding: radene blir liggende i changeloggen,
    som `utvalgsutvidelse`-radene og persondataene gjør. Append-only
    gjelder, og en avledet logg kan regnes ut på nytt.

    Den står i `_les_beveg()` og ikke i `les_endringsuker()`, fordi
    changeloggen leses ÉTT sted for nettstedet. Lå filteret bare i
    ukesregnskapet, ville entitetens egen tidslinje fortsatt vist radene
    — og to lesemåter av samme logg som svarer ulikt er formen F6 og F7
    hadde.
    """
    felt = _bokforingsfelt()
    if beveg.is_empty() or not felt:
        return beveg
    behold = [(str(k), str(f)) not in felt
              for k, f in zip(beveg["source"].to_list(),
                              beveg["field"].to_list())]
    return beveg.filter(pl.Series(behold, dtype=pl.Boolean))


@lru_cache(maxsize=1)
def _les_beveg() -> pl.DataFrame:
    """Changeloggen slik NETTSTEDET skal lese den. Ett sted.

    Tre merkinger og to filtre, i den rekkefølgen:

        merk_utvalgsutvidelse   entiteten kom fordi VI begynte å spørre
        merk_feltbevegelse      det var et FELT som kom eller gikk, ikke
                                entiteten
        bevegelse()             fjerner det som ikke skjedde i verden
        uten_bokforing()        fjerner det som er om RAPPORTERINGEN og
                                ikke om entiteten — kildens egen
                                erklæring, se Source.bokforing

    ## Hvorfor det er én funksjon og ikke to like kall

    Fram til 23.09.2026 sto de samme to linjene i `les_felles()` og i
    `_endringer()`. De var like den dagen de ble skrevet, og en tredje
    merking måtte legges inn to steder for at forsiden og
    lokalitetssiden skulle si det samme om den samme raden. Det er
    formen F6 og F7 hadde: ett oppslag gjort på nytt et sted til.

    ## Hvorfor `merk_feltbevegelse` bare får de ukentlige kildene

    Oppslagskostnad, ikke definisjon. Se funksjonens egen docstring:
    1 528 av 1 569 (kilde, dato)-par er lusetall og sjøtemperatur, som
    ikke vises som ukesendringer i det hele tatt.
    """
    alle = changelog.merk_utvalgsutvidelse(changelog.les_alt())
    alle = changelog.merk_feltbevegelse(alle, kilder=ukentlige_kilder())
    return uten_bokforing(diff.bevegelse(alle))


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

    alle_ovf = list(_overforinger().values())
    ovf_per_till: dict[str, list[dict]] = defaultdict(list)
    for o in alle_ovf:
        ovf_per_till[o.get("tillatelse_nr", "")].append(o)

    # Changeloggen én gang, gjennom den ENE lesedøra — se `_les_beveg()`.
    beveg = _les_beveg()
    maaleserie = sorted(MAALESERIER)

    # SKILLET GÅR PÅ (kilde, felt) — se `er_maaleserie()`. Ramma
    # filtreres grovt på kildenavn først, fordi et Python-kall per rad
    # over 987 769 rader er dyrt; de to unntaksfeltene hentes inn igjen.
    register: dict[str, list[dict]] = defaultdict(list)
    hendelser_i_maaleserie = beveg.filter(
        pl.col("source").is_in(maaleserie)
        & pl.col("field").is_in(sorted(f for _k, f in MAALESERIE_HENDELSER)))
    for r in (pl.concat([beveg.filter(~pl.col("source").is_in(maaleserie)),
                         hendelser_i_maaleserie])
              .sort("observed_at", descending=True).iter_rows(named=True)):
        if not er_maaleserie(str(r["source"]), str(r["field"])):
            register[str(r["entity_id"])].append(r)

    maalt: dict[str, int] = defaultdict(int)
    for kilde_, felt_, eid in beveg.filter(
            pl.col("source").is_in(maaleserie)).select(
            ["source", "field", "entity_id"]).iter_rows():
        if er_maaleserie(str(kilde_), str(felt_)):
            maalt[str(eid)] += 1

    serier: dict[str, list[dict]] = defaultdict(list)
    lusedatoer = snapshot.datoer("lusetall")
    grenser = _lusegrenser()
    for dato in lusedatoer:
        aar, ukenr = _isouke(dato)
        # SISTE VERSJON AV UKA, ikke alle. Se `_lusserie()`.
        for _nr, ramme in snapshot.versjoner("lusetall", dato)[-1:]:
            hentet = snapshot.fetched_at_i(ramme) or ""
            per_lok: dict[str, dict[str, str]] = defaultdict(dict)
            for eid, felt, verdi in ramme.select(
                    ["entity_id", "field", "value"]).iter_rows():
                per_lok[str(eid)][str(felt)] = verdi
            for eid, raa in per_lok.items():
                uke = {felt: (raa.get(felt) or "") for felt in LUSEFELT}
                uke["dato"] = dato
                uke["iso_aar"] = str(aar)
                uke["iso_uke"] = f"{ukenr:02d}"
                uke["lusegrense"] = grenser.get(eid, {}).get(dato, "")
                uke["hentet"] = hentet
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
    biolag, biolag_uker = _biomasselag()
    bio_serier, bio_utgitt = _biomasse()

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
        akva_hentet=_hentet("akvakultur"),
        sjekksum=_sjekksum("akvakultur"),
        kontakt=_kontakt(),
        bevegelse=beveg,
        po_naa=_po_naa(akva),
        biomasselag=biolag,
        biomasselag_uker=biolag_uker,
        biomasse=bio_serier,
        biomasse_utgitt=bio_utgitt,
        sist_endret=sist_endret_av(beveg),
        former=publiseringsvakt.formkart(enhet, eierskap, alle_ovf),
        unntak=unntak_per_lokalitet(),
    )


def sist_endret_av(beveg: pl.DataFrame) -> dict[tuple[str, str], str]:
    """{(entitet, felt): siste `observed_at`} — da vi sist SÅ feltet
    endre seg.

    ETT STED, kalt fra begge veiene inn i `bygg_lokalitet()`. Fram til
    22.09.2026 bygde batchen den og enkeltsiden ikke, og følgen var at
    «Sist observert»-kolonnen var utfylt i en batch og tom i en
    enkeltkjøring — to veier til samme side som svarer ulikt, altså
    formen F6 og F7 hadde. `test_batch_gir_samme_side_som_enkelt`
    fanget det.

    `borte`-rader teller ikke: de sier at hele oppføringen forsvant,
    ikke at feltet fikk en ny verdi. En kolonne som sa «sist observert
    21.09» fordi entiteten var borte den uka, ville vært en påstand om
    en verdi som ikke finnes.
    """
    ut: dict[tuple[str, str], str] = {}
    for eid, felt, dato in (beveg.filter(pl.col("change_type") == "endret")
                            .select(["entity_id", "field", "observed_at"])
                            .iter_rows()):
        nøkkel = (str(eid), str(felt))
        if str(dato) > ut.get(nøkkel, ""):
            ut[nøkkel] = str(dato)
    return ut


def _po_naa(akva: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Trafikklysfargen slik REGISTERET oppgir den nå, per område.

    ## Hvorfor dette ikke er det samme som `_po_farger()`

    De to svarer på hver sin ting, og forskjellen er hele grunnen til at
    begge finnes:

        _po_farger()   HVA FORSKRIFTEN SA i hver runde, med belegg.
                       Leses av `trafikklysvedtak`. 19 av 65 celler er
                       tomme, fordi forskriften bare navngir områder
                       der noe endrer seg.
        _po_naa()      HVILKEN FARGE SOM GJELDER NÅ. Leses av
                       `akvakultur.prodomraade_status`, som
                       Fiskeridirektoratet setter på hver lokalitet.
                       Ingen tomme: alle 13 har en verdi.

    Å utlede «gjelder nå» av forskriftsrundene ville krevd at vi antok
    at en farge står til den endres. Det er sant, men det er VÅR
    slutning — og her finnes et register som sier det selv. Still
    spørsmålet til den som faktisk vet (CLAUDE.md 1b-1).

    ## Uenighet sies, den pusses ikke bort

    Fargen står på hver LOKALITET og ikke på området. Skulle to
    lokaliteter i samme område oppgi ulik farge, er det en uenighet i
    kilden, og raden sier det framfor at en av de to vinner ved et
    sammentreff i iterasjonsrekkefølgen. Se docs/REGEL-UENIGE-KILDER.md.
    """
    per_po: dict[str, Counter] = defaultdict(Counter)
    for a in akva.values():
        kode = (a.get("prodomraade_kode") or "").strip()
        farge = (a.get("prodomraade_status") or "").strip()
        if kode and farge:
            per_po[kode][farge] += 1

    ut: dict[str, dict[str, str]] = {}
    for kode, teller in per_po.items():
        if len(teller) == 1:
            raa = next(iter(teller))
            ut[kode] = {
                "farge": visningsord.verdi("prodomraade_status", raa),
                "klasse": FARGE_KLASSE.get(_fargekode(raa.lower()), ""),
                "uenig": "",
            }
        else:
            ut[kode] = {
                "farge": FARGE_MANGLER,
                "klasse": "",
                "uenig": "; ".join(f"{visningsord.verdi('prodomraade_status', f)}"
                                   f" på {n} lokaliteter"
                                   for f, n in teller.most_common()),
            }
    return ut


# Feltene biomasselaget faktisk bærer om fisken. `dato_forbehold` og
# `arts_forbehold` er IKKE med her: de er kildens egne
# forbeholdssetninger, ikke verdier per uke, og de står én gang på siden
# framfor på hver rad.
BIOLAGFELT = ("har_fisk", "arter_tilstede", "antall_arter",
              "siste_rapport", "lokalitet_status")


def _biomasselag() -> tuple[dict[str, list[dict]], list[str]]:
    """({loknr: [uke, ...]}, alle observasjonsdatoene).

    ## Hva denne serien ER, og hva den ikke er

    Biomasselaget sier OM det står fisk på en lokalitet — ja eller nei,
    og hvilken art. Det sier ikke hvor mye. Mengdetallene ligger i
    biomassedatabasen etter akvakulturdriftsforskriften § 44, som er
    børssensitiv og ikke offentlig (bekreftet av HI 09.09.2026). De
    offentlige mengdetallene finnes bare per PRODUKSJONSOMRÅDE, og de
    hører derfor hjemme på områdesiden og ikke her.

    ## `observed_at` ER HENTETIDSPUNKTET VÅRT

    Kilden sier det selv, i feltet `dato_forbehold`: laget bærer siste
    innsendte månedsrapport per lokalitet, og `siste_rapport` sier
    hvilken måned nettopp den påstanden gjelder for. De to kan ligge år
    fra hverandre — MÅLT 10.09.2026 spente `siste_rapport` fra
    2005-04-30 til 2026-08-31 over 112 distinkte verdier.

    Derfor bærer HVER RUTE i stripa sin egen `siste_rapport`, og ikke
    bare et ja eller nei. En stripe som viste «fisk» uke for uke uten
    det, ville påstått at vi vet noe om akkurat den uka. Det er samme
    skille som CLAUDE.md 1b-7 gjør mellom `observed_at` og
    `fetched_at`, og her er det kilden som insisterer på det.
    """
    serier: dict[str, list[dict]] = defaultdict(list)
    datoer = snapshot.datoer("biomasselag")
    for dato in datoer:
        for _nr, ramme in snapshot.versjoner("biomasselag", dato):
            per_lok: dict[str, dict[str, str]] = defaultdict(dict)
            for eid, felt, verdi in ramme.select(
                    ["entity_id", "field", "value"]).iter_rows():
                if str(felt) in BIOLAGFELT:
                    per_lok[str(eid)][str(felt)] = verdi
            for eid, raa in per_lok.items():
                uke = {f: (raa.get(f) or "") for f in BIOLAGFELT}
                uke["dato"] = dato
                serier[eid].append(uke)
    return dict(serier), datoer


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


def _lusegrenser(loknr: str | None = None) -> dict[str, dict[str, str]]:
    """{lokalitet: {dato: grense}} fra `sjotemperatur.lusegrense`.

    Siste versjon av hver uke, som `_lusserie()`. Grensa er BarentsWatchs
    «Lusegrense uke» for lokaliteten den uka — 0,5, og 0,2 i vårukene fra
    2017 — og ALDRI en konstant her. Mangler den, er svaret tom streng og
    linja får et brudd, på samme måte som en uke uten tall får et tomrom.

    `loknr` begrenser til én lokalitet, for siden som bygges alene.
    """
    ut: dict[str, dict[str, str]] = defaultdict(dict)
    for dato in snapshot.datoer("sjotemperatur"):
        for _nr, ramme in snapshot.versjoner("sjotemperatur", dato)[-1:]:
            sub = ramme.filter(pl.col("field") == "lusegrense")
            if loknr is not None:
                sub = sub.filter(pl.col("entity_id") == loknr)
            for eid, verdi in sub.select(["entity_id", "value"]).iter_rows():
                # sys.intern: 800 000 verdier, to ulike strenger.
                ut[str(eid)][dato] = sys.intern(str(verdi))
    return ut


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
    grenser = _lusegrenser(loknr).get(loknr, {})
    for dato in snapshot.datoer("lusetall"):
        # ÉN RAD PER UKE: bare den sist utgitte versjonen av uka. Med
        # alle versjoner ville en uke med `.2` gitt to rader, og «764
        # uker» i fila og på siden ville talt rader og ikke uker. MÅLT
        # 07.10.2026: ingen lusetallsuke har mer enn én versjon i dag
        # (767 filer, 767 datoer), så endringen flytter ingen tall —
        # den holder invarianten `test_antall_uker_i_teksten_er_antall_rader`
        # prøver. Samme valg som `_siste()`: nyeste påstand vinner.
        for _nr, ramme in snapshot.versjoner("lusetall", dato)[-1:]:
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
            # Ikke i LUSEFELT: grensa kommer fra en annen kilde og står
            # ikke i tabellen eller nedlastingene. Grafen tegner den.
            uke["lusegrense"] = grenser.get(dato, "")
            # NÅR VI HENTET UKA — `fetched_at`, oss. Står i nedlastingenes
            # «Om dataene», og er ikke en kolonne: den sier noe om
            # snapshotet, ikke om lokaliteten.
            uke["hentet"] = snapshot.fetched_at_i(ramme) or ""
            rader.append(uke)
    return rader


def manglende_uker(serie: list[dict], datoer: list[str]) -> list[str]:
    """Ukene MELLOM seriens første og siste rad som lokaliteten ikke
    står i. Ukene før første og etter siste rad regnes ikke: de er der
    lokaliteten ikke fantes ennå, eller ikke lenger.

    MÅLT 07.10.2026 over alle 767 ukesnapshots: 115 av 2 706 lokaliteter
    har slike hull, 4 369 (lokalitet, uke)-par i alt — og ALLE 4 369
    mangler også i BarentsWatch sitt rå-svar i `data/arkiv/lusetall/`.
    Hullene er kildens, ikke parserens. 20797 URDVIKA mangler
    2018-11-26, 2018-12-03 og 2018-12-10, og serien sa «764 uker for
    2012-01-02 til 2026-09-07» — 767 ISO-uker — uten å si hvilke.
    """
    if not serie:
        return []
    har = {u["dato"] for u in serie}
    fra, til = serie[0]["dato"], serie[-1]["dato"]
    return [d for d in datoer if fra < d < til and d not in har]


def manglende_tekst(mangler: list[str]) -> str:
    """Setningen som NAVNGIR de manglende ukene. Tom når ingen mangler.

    Sammenhengende uker står som ett strekk. Et strekk på tre uker eller
    færre navngis uke for uke; et lengre som «fra … til …, N uker» —
    MÅLT har ingen lokalitet mer enn to strekk, men det lengste er 243
    uker, og 243 datoer i en setning er ikke en opplysning noen leser.
    """
    if not mangler:
        return ""
    strekk: list[list[str]] = [[mangler[0]]]
    for d in mangler[1:]:
        forrige = dt.date.fromisoformat(strekk[-1][-1])
        if dt.date.fromisoformat(d) - forrige == dt.timedelta(days=7):
            strekk[-1].append(d)
        else:
            strekk.append([d])

    def vist(d: str) -> str:
        return f"{d} ({visningsord.uke(d)})"

    deler = [", ".join(vist(d) for d in s) if len(s) <= 3
             else f"fra {vist(s[0])} til {vist(s[-1])}, {len(s)} uker"
             for s in strekk]
    return (f"{visningsord.antall(len(mangler), 'uke', 'uker')} i perioden "
            f"mangler fordi lokaliteten ikke står i kildens svar for dem: "
            f"{'; '.join(deler)}. De har ingen rad.")


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

# TO FELTER I EN MÅLESERIE SOM LIKEVEL ER HENDELSER.
#
# `lusetall` leverer et nytt tall hver uke, og hvert tall er neste
# måling — derfor står kilden i `MAALESERIER`. Men to av feltene er
# ikke målinger: `har_ila` og `har_pd` er FLAGG som slås av og på, og et
# flagg som slås på er noe som har skjedd med anlegget.
#
# MÅLT 22.09.2026 over hele changeloggen: 3 323 `endret`-rader for de to
# feltene, fordelt på 723 uker og 2 074 lokaliteter. Til sammenligning
# har OTERNESET alene 1 284 måleserierader. Flaggene drukner altså ikke
# hendelsen — de ER hendelsen, og de er sjeldne.
#
# Unntaket er et PAR (kilde, felt) og ikke et kildenavn: resten av
# lusetall skal fortsatt holdes utenfor. En liste over kilder kunne
# ikke uttrykt det.
MAALESERIE_HENDELSER = frozenset({
    ("lusetall", "har_ila"),
    ("lusetall", "har_pd"),
})


def er_maaleserie(source: str, field: str) -> bool:
    """Er denne raden neste måling, eller er den en hendelse?

    ETT STED, kalt fra alle tre veiene inn i endringslistene — batchen,
    enkeltsiden og felleslesingen. Tre steder som skulle svart det samme
    om hva som er en hendelse, er formen F6 og F7 hadde.
    """
    return (source in MAALESERIER
            and (source, field) not in MAALESERIE_HENDELSER)
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


def _endringer(loknr: str, tillatelser: list[str]
               ) -> tuple[list[dict], int, dict[tuple[str, str], str]]:
    """(registerendringer nyest først, måleserierader, sist-observert).

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
    beveg = _les_beveg()

    mine = beveg.filter(
        (pl.col("entity_id") == loknr)
        | ((pl.col("source").is_in(sorted(ENDRINGER_VIA_TILLATELSE)))
           & pl.col("entity_id").is_in(tillatelser))
    )

    # SKILLET GÅR PÅ (kilde, felt), ikke på kildenavnet alene — se
    # `er_maaleserie()`. `har_ila` og `har_pd` er flagg og ikke
    # målinger, og de hører hjemme i tidslinja.
    rader_alle = list(mine.iter_rows(named=True))
    maaleserie = sum(1 for r in rader_alle
                     if er_maaleserie(str(r["source"]), str(r["field"])))
    register_rader = [r for r in rader_alle
                      if not er_maaleserie(str(r["source"]), str(r["field"]))]
    register_rader.sort(key=lambda r: str(r["observed_at"]), reverse=True)
    rader = _lokalitetsendringer(register_rader, loknr)
    # SAMME KART SOM BATCHEN BYGGER, av den samme ramma. Se
    # `sist_endret_av()` for hvorfor det ikke kan være to.
    return rader, maaleserie, sist_endret_av(beveg)


@lru_cache(maxsize=1)
def _partisjonering() -> dict[str, str]:
    """{kildenavn: «henting» eller «verden»}, kildenes egen erklæring.

    Bufret: den leses per changelog-rad, og `registry.discover()`
    importerer hver kilde. Samme utledning som `ukentlige_kilder()`
    gjør — og av samme grunn ligger den ikke som en liste her.
    """
    from core import registry
    from core.contract import erklaert_partisjonering

    ut: dict[str, str] = {}
    for kilde in registry.discover():
        ut.update(erklaert_partisjonering(kilde))
    return ut


def _lokalitetsendringer(raa: list[dict], loknr: str) -> list[dict]:
    """Changelog-radene for én lokalitet som tidslinjerader, med klasse.

    ETT STED, TO KALLERE: `_endringer()` og `_endringer_av_indeks()`
    skal svare det samme, og gjør det fordi begge går hit.

    Klassen settes av `vesentlighet.klassifiser()` på HELE lista før
    noe annet skjer: to av reglene ser på andre rader samme dag.
    """
    klasser = vesentlighet.klassifiser(raa)
    rader = [dict(_endringsrad(r, loknr), klasse=k.klasse, forklaring="",
                  endringstype=str(r["change_type"]), samlet=0)
             for r, k in zip(raa, klasser)]
    # REGISTERETS EGET ORD FOR «NY». Lest av den rå koden, ikke av den
    # oversatte teksten: `NEW_SITE` er det registeret sier.
    nye_lokaliteter = {(str(r["entity_id"]), str(r["observed_at"]))
                       for r in raa
                       if (str(r["source"]), str(r["field"])) == VERSJONSAARSAK
                       and str(r["new_value"]) == "NEW_SITE"}
    return _samle_oppforinger(_med_versjonsaarsak(rader), nye_lokaliteter)


# Kildene der `ny`/`borte` betyr at en OPPFØRING kom eller gikk: en
# lokalitet i Akvakulturregisteret, en tillatelse i eierskapsregisteret.
# `lusetall` og `biomasselag` står ikke her: der betyr `ny` at
# lokaliteten kom inn i en annen kilde, og radene er sykdomsflagg og
# fisk til stede som klassifiseres hver for seg.
OPPFORINGSKILDER = frozenset({"akvakultur", "eierskap"})


def _samle_oppforinger(rader: list[dict],
                       nye_lokaliteter: set[tuple[str, str]]) -> list[dict]:
    """En oppføring som kom eller gikk, er ÉN hendelse og ikke én rad per felt.

    MÅLT 06.10.2026: en ny lokalitet ga 25 rader i tidslinja, og 45307
    fikk i tillegg 85 for de fem tillatelsene som kom med den. Ukesiden
    har slått sammen per oppføring siden den ble bygget; dette er samme
    regel på lokalitetssiden.

    ORDET FØLGER BELEGGET. «Ny lokalitet registrert» står bare der
    registeret selv sier det, med `versjon_aarsak = NEW_SITE` samme dag
    (alle seks i dataene i dag). Ellers står ukesidens ord, «Ny i vårt
    utvalg» og «Ute av vårt utvalg»: vi vet at den er ny for OSS, ikke
    at den er ny i registeret.

    Forklaringen fra registeret blir med hendelsen hvis et av feltene
    hadde den — se `_med_versjonsaarsak()`.
    """
    grupper: dict[tuple, list[dict]] = {}
    ut: list[dict] = []
    for r in rader:
        if r["endringstype"] in ("ny", "borte") and r["kilde"] in OPPFORINGSKILDER:
            nokkel = (r["kilde"], r["entity_id"], r["dato"], r["endringstype"])
            if nokkel not in grupper:
                grupper[nokkel] = []
                ut.append(nokkel)
            grupper[nokkel].append(r)
        else:
            ut.append(r)
    resultat = []
    for post in ut:
        if isinstance(post, dict):
            resultat.append(post)
            continue
        kilde, eid, dato, slag = post
        felt = grupper[post]
        if kilde == "akvakultur" and slag == "ny" and (eid, dato) in nye_lokaliteter:
            etikett = "Ny lokalitet registrert"
        else:
            etikett = "Ny i vårt utvalg" if slag == "ny" else "Ute av vårt utvalg"
        resultat.append(dict(
            felt[0], etikett=etikett, felt="oppforing", kildefelt="oppforing",
            fra="", til="", differanse=[], samlet=len(felt),
            klasse=vesentlighet.VESENTLIG,
            forklaring=next((f["forklaring"] for f in felt if f["forklaring"]), "")))
    return resultat


# Registerets forklaring på en ny versjon av oppføringen. Den er ikke en
# hendelse, men et svar på hvorfor en annen rad samme dag finnes.
VERSJONSAARSAK = ("akvakultur", "versjon_aarsak")


def _med_versjonsaarsak(rader: list[dict]) -> list[dict]:
    """«Samdrift: ja → nei (registeret: samdrift avsluttet)».

    `versjon_aarsak` står ikke som egen rad. Verdien den fikk, settes som
    `forklaring` på de andre akvakultur-radene for samme lokalitet samme
    dag — de vesentlige hvis det finnes noen, ellers de tekniske.

    FINNES DET INGEN ANDRE RADER, BLIR DEN STÅENDE. En forklaring uten
    noe å forklare er fortsatt noe registeret sa, og en rad som forsvant
    fordi partneren manglet, ville vært en stille utelatelse — samme
    regel som `slaa_sammen_trukne()`.

    Bare en årsak som ENDRET seg har en rad. Er årsaken den samme som
    forrige versjons, står den ikke i loggen, og da forklares ingenting.
    Å lese den av snapshotet ville vært en annen påstand: at årsaken
    gjelder akkurat denne endringen.
    """
    aarsaker = [r for r in rader
                if (r["kilde"], r["kildefelt"]) == VERSJONSAARSAK and r["til"]]
    ut = [r for r in rader if not any(r is a for a in aarsaker)]
    for a in aarsaker:
        samme = [r for r in ut if r["kilde"] == VERSJONSAARSAK[0]
                 and r["entity_id"] == a["entity_id"] and r["dato"] == a["dato"]]
        maal = [r for r in samme if r["klasse"] == vesentlighet.VESENTLIG] or samme
        if not maal:
            ut.append(a)
            continue
        # HØYST ÉN GANG PER LOKALITET OG DAG. Fram til 06.10.2026 sto
        # forklaringen på hver rad den gjaldt, og 45302 viste «(registeret:
        # ny lokalitet)» 24 ganger. Den står nå på den første — den
        # nyeste vesentlige, i tidslinjas rekkefølge.
        maal[0]["forklaring"] = a["til"]
    return ut


def _endringsrad(r: dict, loknr: str) -> dict:
    """Én changelog-rad til én tabellrad. Ett sted, to kallere.

    `gjelder` skiller endringer om LOKALITETEN fra endringer om en
    TILLATELSE på den. Det andre er en indirekte kobling, og den står i
    en kolonne framfor å pusses bort — et eierskifte er noe av det
    viktigste som kan skje med en lokalitet, men raden gjelder
    tillatelsen.
    """
    # HVA DATOEN ER, lest av KILDENS egen erklæring og ikke av en liste
    # her. `Source.partisjonering` sier det:
    #
    #   henting   `observed_at` er dagen VI hentet. «Observert»
    #   verden    `observed_at` er perioden raden HANDLER OM. «Gjelder»
    #
    # Skillet ble synlig da sykdomsflaggene kom inn i tidslinja
    # 22.09.2026: `lusetall` er `verden`-partisjonert, så en
    # ILA-endring datert 2019-11-18 gjelder UKE 47 AV 2019 — den sier
    # ikke at vi så noe den dagen. Vi backfilte den i 2026. En tidslinje
    # som kalte begge «observert» ville vært nøyaktig forvekslingen
    # CLAUDE.md 1b handler om.
    kilde = str(r["source"])
    verden = _partisjonering().get(kilde) == "verden"
    return {
        "dato": str(r["observed_at"]),
        "datoslag": "verden" if verden else "henting",
        "datoord": "Gjelder" if verden else "Observert",
        "gjelder": ("lokaliteten" if str(r["entity_id"]) == loknr
                    else f"tillatelse {r['entity_id']}"),
        "kilde": kilde,
        # ENTITETEN OG PARET følger raden. De brukes ikke i visningen,
        # men `slaa_sammen_trukne()` nøkler på dem — og en nøkkel som må
        # bygges av noe annet på hver side, er to steder å ta feil.
        "entity_id": str(r["entity_id"]),
        "forrige_dato": str(r.get("forrige_observed_at") or ""),
        "kildefelt": str(r["field"]),
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
        "differanse": _differanse(str(r["field"]), r["old_value"], r["new_value"]),
    }


# --------------------------------------------------------- sida


def _endringer_av_indeks(loknr: str, tillatelser: list[str],
                         felles: Felles
                         ) -> tuple[list[dict], int, dict[tuple[str, str], str]]:
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
    return (_lokalitetsendringer(rader, loknr),
            felles.maaleserierader.get(loknr, 0),
            felles.sist_endret)


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


# ---------------------------------------------------- ENDRINGSUKENE
#
# «Denne uka i registrene» på forsiden, og siden `/endringer/<år>-<uke>/`.
# Det er nettstedets eneste side som er om TIDA framfor om en entitet,
# og den er hele produktet: registrene viser nå, og bevegelsen er det
# som ikke finnes noe annet sted.
#
# ## HVILKE KILDER SOM HAR EN UKE, og hvorfor det ikke er en liste her
#
# `observed_at` betyr ikke det samme i alle kilder, og kilden sier det
# selv: `Source.partisjonering` er enten «henting» eller «verden».
#
#     henting   observed_at ER innsamlingsdatoen. akvakultur,
#               biomasselag, eierskap, enhetsregisteret.
#     verden    observed_at er perioden raden HANDLER OM.
#               trafikklysvedtak dateres til vedtaksåret (2026-12-31),
#               eierskap_historikk til journalåret, biomasse til
#               månedsslutt.
#
# En «verden»-rad har ingen uke i denne forstand. MÅLT 22.09.2026:
# `trafikklysvedtak` og `eierskap_historikk` har 2026-12-31 som
# `observed_at`, altså uke 53 av 2026 — en uke som ikke har vært. Tatt
# med ville forsiden påstått at vi observerte noe i framtida.
#
# Lista utledes derfor av kildenes egen erklæring og står ikke her. Det
# er samme regel som `ubelagte()`: en liste hos publiseringsleddet kan
# bli stående uendret når en ny kilde kommer til, og den manglende
# uka ville vist seg først den dagen noen så etter.
#
# At radene er UTELATT står på siden med et tall, ikke i stillhet.


def ukentlige_kilder() -> frozenset[str]:
    """Kildene der `observed_at` ER innsamlingsdatoen.

    UTLEDET av `Source.partisjonering`, aldri listet. I dag er svaret
    `{akvakultur, biomasselag, eierskap, enhetsregisteret}`.
    """
    from core import registry
    from core.contract import erklaert_partisjonering

    ut: dict[str, str] = {}
    for kilde in registry.discover():
        ut.update(erklaert_partisjonering(kilde))
    return frozenset(n for n, v in ut.items() if v == "henting")


# ------------------------------------------------- HVA SLAGS ENDRING
#
# Overleveringen ber om seks etiketter: Trafikklys, Biomasse, Eierskap,
# Tillatelse, Ny lokalitet, Nedlagt lokalitet. Dataene har ÅTTE slag, og
# to av dem er store: 369 endringer i `antall_ansatte` og 362 i
# `prodomraade_status` i uke 39 alene.
#
# De to som mangler i overleveringens liste er
# SELSKAPSOPPLYSNING (enhetsregisteret) og LOKALITETSOPPLYSNING
# (akvakulturfelt som ikke er trafikklyset). Å presse dem inn i
# «Eierskap» eller å utelate dem ville vært å la designet bestemme hva
# dataene inneholder. README-en sier selv: «Datafeltene er foreslåtte
# navn; tilpass modellen.»
#
# ## TABELLEN ER EKSPLISITT, OG DET ER POENGET
#
# Ingen heuristikk, ingen «hvis feltnavnet inneholder eier». Et felt som
# ikke står her faller til `annet` og TELLES — samme regel som
# `visningsord`: en ukjent kode slipper igjennom uendret og blir talt,
# slik at den ikke står på siden igjen om et halvår uten at noen så det.

# (source, field) -> type. Feltet `*` betyr «alle andre felt i kilden».
ENDRINGSTYPE_REGLER = {
    # Trafikklysfargen slik REGISTERET oppgir den per lokalitet. Dette
    # er kilden til at fargen endrer seg i en bestemt UKE: forskriften
    # dateres til vedtaksåret, mens Akvakulturregisteret følger den opp
    # og vi ser det den mandagen det skjer.
    ("akvakultur", "prodomraade_status"): "trafikklys",
    ("trafikklysvedtak", "farge"): "trafikklys",
    ("trafikklysvedtak", "farge__lesemaate"): "trafikklys",

    # Hvem som eier tillatelsen.
    ("eierskap", "eier_navn"): "eierskap",
    ("eierskap", "eier_orgnr"): "eierskap",
    ("eierskap", "eier_type"): "eierskap",
    ("eierskap", "organisasjonsform"): "eierskap",

    # Selve tillatelsen: hva den gjelder, hvor stor den er, hvor den
    # ligger. Alt annet `eierskap` bærer.
    ("eierskap", "*"): "tillatelse",
    ("akvakultur", "tillatelser"): "tillatelse",
    ("akvakultur", "tillatelser_antall"): "tillatelse",
    ("akvakultur", "tillatelser_trukket"): "tillatelse",

    # Fisk til stede. `biomasselag` sier om det STÅR fisk på
    # lokaliteten, ikke hvor mye — mengden er per produksjonsområde og
    # hører hjemme på områdesiden. Se avviket i oppdraget, punkt 1.
    ("biomasselag", "*"): "biomasse",

    # SYKDOMSFLAGGENE. `har_ila` og `har_pd` er de to feltene i
    # `lusetall` som ikke er målinger — se `MAALESERIE_HENDELSER`.
    #
    # ORDLYDEN ER NØYTRAL, OG DET ER MÅLT. BarentsWatchs OpenAPI-
    # dokumentasjon (hentet 22.09.2026) sier om feltet bare: «Does the
    # site have ISA disease this week». Den skiller ikke MISTANKE fra
    # PÅVIST.
    #
    # At skillet FINNES hos kilden, er derimot dokumentert: `IlaPd`
    # bærer `ruling` med verdiene «Mistanke or Påvist», og `IlaPdCase`
    # har både `suspectedDate` og `confirmedDate` — og `disproved`.
    # Den ene boolske verdien vi får per uke kan altså dekke begge, og
    # hvilken av dem den dekker står ikke skrevet.
    #
    # Derfor sier siden «ILA-flagg satt i BarentsWatch» og ikke
    # «ILA påvist». Ordet «påvist» brukes ikke før det er målt. Se
    # docs/APNE-SPORSMAL.md.
    ("lusetall", "har_ila"): "sykdom",
    ("lusetall", "har_pd"): "sykdom",

    # Resten av akvakultur: navn, kommune, arter, kapasitet, koordinater.
    ("akvakultur", "*"): "lokalitet",

    # Enhetsregisteret om selskapet: ansatte, regnskap, konkurs, adresse.
    ("enhetsregisteret", "*"): "selskap",
}

# Rekkefølgen etikettene står i, og teksten på dem. Rekkefølgen er
# TEMATISK og ikke etter antall: etiketter som bytter plass fra uke til
# uke er etiketter ingen lærer seg.
ENDRINGSTYPER = (
    {"id": "trafikklys", "navn": "Trafikklys", "kort": "trafikklys",
     "hva": "produksjonsområdets farge, slik registeret oppgir den"},
    {"id": "eierskap", "navn": "Eierskap", "kort": "eierskap",
     "hva": "hvem som eier en tillatelse"},
    # `forklaring` er forsidens ord, etter «Flest endringer gjaldt
    # tillatelser (N):». `hva` står med typen som subjekt i ordlista og
    # på brikkene; de to setningene har ulik grammatikk. Uten
    # `forklaring` brukes `hva`.
    {"id": "tillatelse", "navn": "Tillatelse", "kort": "tillatelser",
     "hva": "tillatelsens formål, kapasitet eller lokaliteter",
     "forklaring": "kapasitet, formål eller hvilke lokaliteter de hører til"},
    # «I VÅRT UTVALG», IKKE «I REGISTERET». Skillet er målt, ikke
    # forsiktighet: 23.09.2026 slo vi opp alle de 29 selskapene uke 39
    # kalte «Ute av registeret» mot Brønnøysunds åpne API. 20 av dem
    # sto der fortsatt og hadde byttet næringskode ut av lista vår
    # (til 68.200 eiendom, 55.100 hotell, 10.410 fôr …), 2 var faktisk
    # slettet, og 7 hadde aldri forsvunnet — se `felt_borte`.
    #
    # Vår luke inn i Enhetsregisteret ER et næringskodesøk. En entitet
    # som går ut av lista går ut av SØKET, og fra to øyeblikksbilder
    # alene kan ingen se hvilket av de to som skjedde. Da er det
    # svakeste sanne utsagnet det eneste vi har lov til å trykke.
    {"id": "ny", "navn": "Ny i vårt utvalg", "kort": "nye oppføringer",
     "hva": "en lokalitet, tillatelse eller et selskap som ikke var med "
            "forrige uke. Utvalget vårt er et søk, så «ny for oss» er "
            "ikke det samme som «ny i registeret»"},
    {"id": "borte", "navn": "Ute av vårt utvalg",
     "kort": "oppføringer som gikk ut",
     "hva": "en oppføring som var med forrige uke og ikke er det nå. "
            "Den kan være slettet fra registeret, eller ha fått en "
            "næringskode utenfor søket vårt — vi kan ikke se hvilket"},

    # FELTET KOM ELLER GIKK, ikke entiteten. Telles ikke i ukas tall:
    # at et selskap begynner å oppgi antall ansatte er en opplysning om
    # rapporteringen, ikke en hendelse i havbruket. Raden STÅR likevel,
    # på entitetens egen tidslinje, fordi kilden selv skiller «gikk til
    # null» fra «sluttet å rapportere» og vi lagrer det skillet.
    {"id": "felt_ny", "navn": "Felt oppgitt første gang", "teller": False,
     "kort": "felt oppgitt første gang",
     "hva": "kilden oppgir et felt om denne oppføringen for første gang"},
    {"id": "felt_borte", "navn": "Felt ikke lenger oppgitt", "teller": False,
     "kort": "felt som ikke lenger oppgis",
     "hva": "kilden sluttet å oppgi et felt om denne oppføringen"},
    {"id": "lokalitet", "navn": "Lokalitetsopplysning", "kort": "lokalitetsopplysninger",
     "hva": "navn, kommune, arter, kapasitet eller posisjon"},
    {"id": "biomasse", "navn": "Fisk til stede", "kort": "fisk til stede",
     "hva": "om det står fisk på lokaliteten"},
    {"id": "sykdom", "navn": "Sykdom (ILA/PD)", "kort": "sykdomsflagg",
     "hva": "ILA- eller PD-flagget satt eller fjernet i BarentsWatch. "
            "Kilden sier ikke om flagget betyr mistanke eller påvist"},
    # SELSKAPSDATA STÅR FOR SEG, og telles ikke i ukas overskriftstall.
    #
    # MÅLT uke 39: 402 av 440 telte endringer var dette ene slaget, og
    # 369 av dem var `antall_ansatte` — A-ordningens månedlige
    # oppdatering, kontrollert rad for rad mot Brønnøysunds egne
    # kropper (docs/MALING-UKE-39.md). Radene er ekte. De er bare ikke
    # det noen kommer hit for.
    #
    # Et tall der 91 % er løpende registervedlikehold, svarer ikke på
    # «hva skjedde i havbruket denne uka» — det svarer på «hvor mange
    # felt endret seg i et register», og de to ser like ut helt til man
    # spør hva de betyr. Samme skille som `utvalgsutvidelse` og
    # `revidert` i CLAUDE.md 1b-6: radene beholdes, merkes og vises,
    # men summeres ikke som aktivitet.
    #
    # `egen_del` sier hvor de HØRER HJEMME: utenfor forsidens korte
    # tabell, og i sin egen sammenfoldede del på ukessiden. Uten
    # JavaScript står den åpen — en `<details open>` som skriptet
    # lukker, ikke en skjult del som skriptet åpner.
    {"id": "selskap", "navn": "Selskapsdata", "teller": False,
     "egen_del": True, "kort": "selskapsdata",
     "hva": "ansatte, næringskode, adresse, regnskap, konkurs eller "
            "kapital i Enhetsregisteret"},
    {"id": "annet", "navn": "Annet", "kort": "annet",
     "hva": "et felt som ikke er klassifisert ennå"},
)

# Kodene som falt ut av tabellen. Telles og skrives i byggerapporten, av
# samme grunn som `visningsord.UKJENTE`.
UKJENTE_ENDRINGER: defaultdict = defaultdict(int)

# Hvilke slag som telles i «X endringer denne uka». Utledet av
# `ENDRINGSTYPER`, aldri listet ved siden av — to lister som skal si det
# samme er to steder å glemme det.
TELLER = {k["id"]: k.get("teller", True) for k in ENDRINGSTYPER}

# Slagene som står for seg: utenfor forsidens korte tabell, og i sin
# egen sammenfoldede del på ukessiden. Se `selskap` i `ENDRINGSTYPER`.
EGEN_DEL = frozenset(k["id"] for k in ENDRINGSTYPER if k.get("egen_del"))

# Feltene der ÉN beslutning står skrevet på hver lokalitet i et
# produksjonsområde.
#
# ## MÅLT uke 39, og det er derfor regelen finnes
#
# `akvakultur.prodomraade_status` ga 362 rader den 21.09.2026. De er
# ikke 362 hendelser — de er FIRE:
#
#     PO  4   RØD   -> GUL   137 lokaliteter
#     PO  9   GRØNN -> GUL   109
#     PO 10   GRØNN -> GUL    72
#     PO 11   GRØNN -> GUL    44
#
# Hver lokalitet i området fikk samme nye verdi samme dag, fordi
# fargen ikke er en egenskap ved lokaliteten. Den er en egenskap ved
# OMRÅDET, ført på hver lokalitet av registeret.
#
# Det er nøyaktig samme form som `ny`/`borte`: én hendelse skrevet én
# gang per rad kilden har. Forskjellen er bare hva raden deles på —
# entiteten der, området her.
SAMLES_PER_OMRAADE = frozenset({("akvakultur", "prodomraade_status")})


# ------------------------------------------- LISTEFELT SOM FORSKJELL
#
# En lokalitet med fjorten tillatelser som mister én, viste fjorten
# numre, en pil og tretten numre. Leseren måtte lese to lister og finne
# det ene nummeret som ikke står i begge — og det er nøyaktig det
# en maskin skal gjøre framfor et menneske.
#
# Hva som ER en liste, spørres `visningsord.LISTEFELT` om. En liste her
# ville vært et andre sted å glemme et felt.

# {(kilde, felt): grunnfelt} — raden som SLÅS INN i grunnfeltets rad når
# begge gjelder samme entitet i samme par.
#
# ## Hva `tillatelser_trukket` ER, målt før ordet ble rørt
#
# Feltet er `obsoleteConnections` fra Akvakulturregisteret, lest som
# LISENSNUMRE og ikke som et antall (`_lisensnumre`, ikke `_antall` —
# docs/KILDE-AKVAKULTUR.md punkt 6, rettet 25.09.2026). Registeret
# flytter en oppføring fra `connections` til `obsoleteConnections` når
# tillatelsen trekkes fra lokaliteten, og MÅLT over hele changeloggen
# faller alle 13 radene i samme par som `tillatelser`: 13 av 13.
#
# De to radene sier hver sin halvdel av én hendelse. `tillatelser` sier
# AT nummeret forsvant; `tillatelser_trukket` sier at det forsvant fordi
# det ble trukket, og ikke fordi det ble flyttet til en annen lokalitet.
# Derfor slås de sammen til én rad der det ene ordet står ved det ene
# nummeret — ikke to rader der leseren må se at de handler om det samme.
#
# DETTE ER IKKE `Source.avledet_av`. Den erklæringen ville kastet
# `tillatelser_trukket` og beholdt grunnraden, og ordet «trukket» ville
# forsvunnet — se sources/akvakultur.py. Her blir ordet stående ved
# nummeret det gjelder.
#
# Ukas tall på SIDEN telles etter sammenslåingen, fordi de sier hvor
# mange rader som står der: én hendelse, én rad, én i tellingen. Fram
# til 06.10.2026 ble de telt før, og uke 41 hadde typebrikker som
# summerte til én mer enn «Alle». Filene (CSV, JSON, feed) har fortsatt
# hver rad kilden ga oss — se `antall_i_fila`.
SLAAS_INN_I = {("akvakultur", "tillatelser_trukket"): "tillatelser"}

# Radtypene der raden handler om ET FELT og ikke om oppføringen. De tre
# deler etikett og merking; `ny` og `borte` gjelder hele oppføringen.
ENDRET_ELLER_FELT = frozenset({"endret", "felt_ny", "felt_borte"})


def _differanse(felt: str, fra_raa: object, til_raa: object) -> list[dict]:
    """Forskjellen på to listeverdier, som ledd med fortegn.

    Tom liste for et felt som ikke er en liste — da står pil-formen, som
    før. Tom liste OGSÅ når listen ikke endret seg: da har raden
    ingenting å vise som en forskjell, og den faller tilbake på pila.
    """
    endring = visningsord.listeendring(felt, fra_raa, til_raa)
    if not endring:
        return []
    ut = []
    for retning, tegn, ord_ in (("lagt_til", "+", "lagt til"),
                                ("fjernet", "−", "borte")):
        if endring[retning]:
            ut.append({
                "retning": retning.replace("_", "-"),
                "tegn": tegn,
                "ord": ord_,
                # ETT MERKET LEDD PER VERDI, ikke én merket streng.
                # «T-T-0040, T-T-0041» merket `tillatelser` er to verdier
                # bak én merking, og en merking skal peke på ÉN verdi fra
                # kilden — samme regel som endringscellen ellers følger.
                "ledd": [{"verdi": v, "felt": felt, "note": ""}
                         for v in endring[retning]],
            })
    return ut


def slaa_sammen_trukne(rader: list[dict]) -> list[dict]:
    """Radene der ett felt sier HVORFOR et annet flyttet seg, som én rad.

    Nøkkelen er (kilde, entitet, par) — `forrige_observed_at ->
    observed_at`, ikke datoen alene. To uker der først den ene og så den
    andre flyttet seg, er to ting som skjedde.

    Finnes grunnraden ikke i samme par, blir tilleggsraden STÅENDE som
    sin egen. Den sier fortsatt noe sant, og en rad som forsvant fordi
    partneren manglet ville vært en stille utelatelse.

    Den som kaller teller ETTER, ikke før: tallene på siden sier hvor
    mange rader som står der. Se `SLAAS_INN_I`.
    """
    if not any((r.get("kilde"), r.get("kildefelt")) in SLAAS_INN_I
               for r in rader):
        return rader

    def nokkel(r: dict) -> tuple:
        return (str(r.get("kilde", "")), str(r.get("entity_id", "")),
                str(r.get("dato", "")), str(r.get("forrige_dato", "")))

    grunnrad: dict[tuple, dict] = {}
    for r in rader:
        par = (str(r.get("kilde", "")), str(r.get("kildefelt", "")))
        if par in SLAAS_INN_I or par[1] not in {g for g in SLAAS_INN_I.values()}:
            continue
        grunnrad[nokkel(r) + (par[1],)] = r

    ut = []
    for r in rader:
        par = (str(r.get("kilde", "")), str(r.get("kildefelt", "")))
        grunn = SLAAS_INN_I.get(par)
        mot = grunnrad.get(nokkel(r) + (grunn,)) if grunn else None
        if mot is None:
            ut.append(r)
            continue
        # NUMRENE SOM KOM INN I `tillatelser_trukket` er de som ble
        # trukket. De står allerede som `fjernet` i grunnraden — her får
        # de ordet som sier hvorfor.
        trukne = {l["verdi"] for d in r.get("differanse", ())
                  if d["retning"] == "lagt-til" for l in d["ledd"]}
        for d in mot.get("differanse", ()):
            if d["retning"] != "fjernet":
                continue
            for l in d["ledd"]:
                if l["verdi"] in trukne:
                    l["note"] = "trukket"
    return ut


# KILDENE SOM HELT OG HOLDENT HØRER TIL EN EGEN DEL.
#
# Utledet av `ENDRINGSTYPE_REGLER`, ikke listet: en kilde hvis `*`-regel
# peker på et slag i `EGEN_DEL`, har ingen rader som hører hjemme i ukas
# hovedtall. To lister som skal si det samme er formen F6 og F7 hadde.
#
# ## Hvorfor dette trengs, MÅLT uke 39
#
# «Ute av vårt utvalg» viste 24 hendelser. 22 av dem var selskaper som
# gikk ut av næringskodesøket vårt — altså selskapsdata, samme klasse som
# de 402 radene som allerede står for seg. De havnet i hovedtallet bare
# fordi `ny`/`borte` slår kildens egen regel, og et selskap som bytter
# næringskode er ikke mer «hendelse i havbruket» enn at det bytter
# adresse.
EGEN_DEL_KILDER = frozenset(
    kilde for (kilde, felt), slag in ENDRINGSTYPE_REGLER.items()
    if felt == "*" and slag in EGEN_DEL)


def endringstype(source: str, field: str, change_type: str) -> str:
    """Hvilken av `ENDRINGSTYPER` en changelog-rad hører til.

    ## Kilden i en egen del slår ALT

    Hører hele kilden hjemme i en egen del — se `EGEN_DEL_KILDER` — er
    hver av radene dens det slaget, uansett om den er `ny`, `borte`,
    `endret` eller et felt som kom eller gikk. En oppføring som går ut
    av vårt næringskodesøk er en opplysning om registeret, ikke en
    hendelse i havbruket, og den skal telles der resten av kildens rader
    telles.

    ## Ellers slår `ny` og `borte` alt annet

    En oppføring som kommer eller går er ÉN hendelse, ikke tjue. At det
    er `organisasjonsform` og `kommune` og nitten felt til som dukket
    opp samtidig, er hvordan `diff.compare()` skriver det — ikke hva som
    skjedde. Se `les_endringsuker()`, som slår dem sammen per entitet.
    """
    if source in EGEN_DEL_KILDER:
        return ENDRINGSTYPE_REGLER[(source, "*")]
    if change_type in ("ny", "borte", diff.FELT_NY, diff.FELT_BORTE):
        return change_type
    nøkkel = (source, field)
    if nøkkel in ENDRINGSTYPE_REGLER:
        return ENDRINGSTYPE_REGLER[nøkkel]
    if (source, "*") in ENDRINGSTYPE_REGLER:
        return ENDRINGSTYPE_REGLER[(source, "*")]
    UKJENTE_ENDRINGER[f"{source}/{field}"] += 1
    return "annet"


# Verdien i en «fra»- eller «til»-celle når oppføringen ikke fantes.
# Ikke tom, ikke «0» — overleveringens egen tekst.
IKKE_I_REGISTERET = "ikke i registeret"

# Tegnet som står der kilden ikke har en verdi, og FELTNAVNET en slik
# celle merkes med.
#
# ## Hvorfor merkingen må være en annen
#
# Tanken er den samme som `EIER_UKJENT_FELT` har hatt siden 19.09:
# verdien er VÅR tekst om fravær, ikke en verdi fra kilden, og porten
# skal ikke lete etter den i hvitelista.
#
# MÅLT 22.09.2026: porten stoppet publiseringen på fire
# lokalitetssider med `ukjent_navn — «W» 1 tegn`. Verdien var
# tankestreken, i en celle merket `data-felt="eier_navn"` fordi
# changelog-raden gjaldt det feltet og den gamle verdien var tom. En
# tankestrek er ikke et ukjent selskap; det er fraværet av et.
VERDI_MANGLER = "—"
VERDI_MANGLER_FELT = "verdi_mangler"


def personformnavn(navn: object) -> bool:
    """Ender navnet på en organisasjonsform SSB regner som personlig?

    «TESTVIK OG STRAUM ANS», «BRØDRENE X DA». Spørsmålet stilles til
    `core/persondata.PERSONFORMER` gjennom publiseringsvaktens egen
    suffiksleser — ikke til en liste her. To lister over hvilke
    endelser som betyr et personlig foretak, ville vært to steder å
    glemme den ene.

    ## Hva den brukes til, og hva den IKKE brukes til

    Den styrer om verdien blir SØKBAR, ikke om den vises. Navnet står
    på siden: det er et selskapsnavn fra et offentlig register, og de
    få tilfellene som er igjen er kvittert ut hver for seg (se
    `publiseringsvakt.kvitteringer`).

    Men en søkeindeks er noe annet enn en side. Den er en
    maskinlesbar liste over hvert ord på nettstedet, og et navn som
    kan slås opp DER er en oppføring i et register — ikke en opplysning
    på et ark. Det er samme gradering regel 3 gjør når den sier at et
    URL-rom er en liste over hvem som finnes, selv om hver side skulle
    være tom.

    MÅLT 22.09.2026: 14 av 2 338 indekserte sider bar et slikt navn.
    """
    return bool(publiseringsvakt.personform_i_navn(navn))


def feltmerke(verdi: object, felt: str) -> str:
    """Feltnavnet en celle merkes med — eller `verdi_mangler`.

    Kalles fra malene som en Jinja-global. Regelen i markupkontrakten er
    «har en `<td>` en `{{ }}`, har den `data-felt`»; denne sier HVILKEN
    merking, og svaret er at en tom verdi ikke er en verdi fra det
    feltet.
    """
    return felt if str(verdi or "").strip() else VERDI_MANGLER_FELT


def _omvendt(dato: str) -> tuple:
    """Sorteringsnøkkel som gjør en ISO-dato SYNKENDE i en stigende sort.

    Trengs fordi de andre leddene i nøkkelen skal stige. `reverse=True`
    på hele nøkkelen ville snudd dem også.
    """
    return tuple(-int(d) for d in dato.split("-"))


def _ukeslug(dato: str) -> str:
    """«2026-09-21» -> «2026-39». ISO-uke, og den står i URL-en.

    ISO-ÅRET og ikke kalenderåret: 2019-12-30 er mandag i uke 1 av
    2020, og `/endringer/2019-01/` for den datoen ville vært en adresse
    som peker på feil uke for alltid. En URL kan ikke gjøres om — se
    2026-09-16-url-struktur.md.
    """
    aar, ukenr = _isouke(dato)
    return f"{aar}-{ukenr:02d}"


def _po_av_endring(rad: dict, felles: Felles) -> str:
    """Produksjonsområdet raden gjelder, lest av lokaliteten.

    Nøkkelen `SAMLES_PER_OMRAADE` slår sammen på. Tom streng når
    lokaliteten ikke er i et område vi kjenner — og da blir nøkkelen
    delt med andre uten område, som er riktig: vi kan ikke påstå at de
    hører til det samme.
    """
    a = felles.akva.get(str(rad["entity_id"])) or {}
    return str(a.get("prodomraade_kode") or "")


def _hendelse(rad: dict, felles: Felles, antall_felt: int = 1) -> dict:
    """Én changelog-rad (eller én samlet ny/borte-oppføring) som en
    tabellrad på forsiden og på endringssiden.

    ## Hvem raden GJELDER, og hvorfor det ikke alltid er en lokalitet

    Overleveringen har kolonnen «Lokalitet». Dataene har tre slags
    entiteter: lokaliteter (akvakultur, biomasselag), TILLATELSER
    (eierskap) og SELSKAPER (enhetsregisteret). 776 av uke 39s 812
    hendelser gjelder ikke en lokalitet.
    
    Kolonnen heter derfor «Gjelder», og lokaliteten står i sin egen
    kolonne der den finnes. Å presse et selskap inn i en
    lokalitetskolonne ville vært designet som bestemte hva dataene
    inneholder.
    """
    kilde = str(rad["source"])
    eid = str(rad["entity_id"])
    felt = str(rad["field"])
    endring = str(rad["change_type"])
    slag = endringstype(kilde, felt, endring)

    gjelder_navn = gjelder_url = kommune = po = po_navn = ""
    lok_navn = lok_url = ""

    # EN OPPFØRING SOM ER BORTE, NAVNGIS IKKE. Verken med navn eller
    # med organisasjonsnummer.
    #
    # ## Hvorfor, og hva porten målte
    #
    # `hviteliste()` bygges av NYESTE øyeblikksbilde for hver kilde som
    # er `henting`-partisjonert (19.09.2026). En entitet som er BORTE er
    # per definisjon ikke i det øyeblikksbildet, så verken navnet eller
    # nummeret er gjort rede for. MÅLT 22.09.2026 stoppet porten
    # publiseringen med 341 funn på endringssidene, CSV-ene og feedene:
    # `ukjent_navn` og `ukjent_orgnr` på nettopp disse radene.
    #
    # Det er IKKE en feil i porten. Det er 18.09-beslutningen i en ny
    # form: changeloggen bærer verdier fra ELDRE øyeblikksbilder enn
    # hvitelista bygges av, og vakten kan ikke gå god for dem. Se
    # docs/beslutninger/2026-09-18-changeloggens-persondata-ligger-stille.md.
    #
    # ## Hvorfor hvitelista ikke bare utvides
    #
    # Fordi det ville gjenåpnet F15. En personform som ble skrevet inn
    # i et øyeblikksbilde FØR filteret fantes, er fjernet av lesedøra i
    # dag — men den står fortsatt i den gamle fila. En hviteliste som
    # leste «de siste N øyeblikksbildene» ville tatt den inn igjen, og
    # da ville vakten gått god for et navngitt menneske.
    #
    # Fra 05.10.2026 leser hvitelista likevel de to øyeblikksbildene
    # hver endringsuke i bygget er regnet mellom — men GJENNOM døra og
    # kildehooken, så det over gjelder ikke dem. Se
    # `publiseringsvakt._datoene()`. Borte-raden navngis fortsatt ikke:
    # det er et valg om siden, ikke bare om porten.
    #
    # ## Hva som står igjen
    #
    # Hendelsen. Kilden, datoen og antall felt. Det er nok til at en
    # leser ser at noe forsvant, og til at tellingen stemmer — og det
    # er mer enn å utelate raden, som ville gjort forsvinningen
    # usynlig. Identiteten står i changeloggen for den som har den.
    if endring == "borte":
        navn_av_kilde = {
            "akvakultur": "En lokalitet",
            "biomasselag": "En lokalitet",
            "eierskap": "En tillatelse",
            "enhetsregisteret": "Et selskap",
        }
        # SLAGET ER `endringstype()`s, ikke «borte» fast. Hører hele
        # kilden hjemme i en egen del, er også forsvinningen dens
        # selskapsdata — se `EGEN_DEL_KILDER`. MÅLT uke 39: 22 av de 24
        # «ute av vårt utvalg» var selskaper som byttet næringskode ut av
        # søket vårt.
        #
        # ETIKETTEN SLÅS OPP I `ENDRINGSTYPER` og skrives ikke her. Fram
        # til 24.09.2026 sto «Ute av registeret» i denne ordboka mens
        # tabellen over den sa «Ute av vårt utvalg» — to steder om samme
        # rad, og det stedet som ble vist på raden var det som 23.09
        # måtte forkastes som usant: 20 av 29 sto fortsatt i registeret.
        return {
            "dato": str(rad["observed_at"]),
            "forrige_dato": str(rad.get("forrige_observed_at") or ""),
            "uke": _ukeslug(str(rad["observed_at"])),
            "type": slag,
            "type_navn": next(x["navn"] for x in ENDRINGSTYPER
                              if x["id"] == slag),
            "kilde": kilde,
            # `entity_id` BEHOLDES IKKE. Den er et
            # organisasjonsnummer for `enhetsregisteret`, og et
            # ni-sifret tall vi ikke kan gjøre rede for er nøyaktig det
            # `NI_SIFFER` finnes for. Feed-iden bygges av dato, kilde og
            # feltantall, som er stabilt uten å bære identiteten.
            "entity_id": "",
            "kildefelt": felt,
            "felt": "change_type",
            "etikett": "Borte fra registeret",
            "fra": f"{antall_felt} felt",
            "til": IKKE_I_REGISTERET,
            "fra_felt": VERDI_MANGLER_FELT,
            "til_felt": VERDI_MANGLER_FELT,
            # EN BORTE-RAD HAR INGEN FORSKJELL Å VISE. Den er alt slått
            # sammen per entitet, og «N felt» er ikke en liste.
            "differanse": [],
            "fra_klasse": "", "til_klasse": "", "er_farge": False,
            "gjelder": f"{navn_av_kilde.get(kilde, 'En oppføring')} "
                       f"ute av {kilde}",
            "gjelder_felt": "gjelder",
            "identitet": "",
            "gjelder_url": "",
            "gjelder_slag": "borte",
            "lokalitet": "", "lokalitet_url": "",
            "kommune": "", "po": "", "po_navn": "",
            "anonym": True,
        }

    # HVA CELLEN MERKES MED, og hvorfor det ikke alltid er `entity_name`.
    #
    # `entity_name` står i `publiseringsvakt.NAVNEFELT`: en verdi merket
    # slik SKAL være et navn fra kilden, og porten slår den opp i
    # hvitelista. «Tillatelse N-R-0056» er ikke et navn fra kilden — det
    # er VÅR etikett på en entitet som ikke har noe navn. MÅLT stoppet
    # porten publiseringen på nettopp den strengen.
    #
    # Samme regel som `EIER_UKJENT_FELT` og `feltmerke()`: vår egen tekst
    # merkes aldri med kildens feltnavn.
    gjelder_felt = "gjelder"
    if kilde in ("akvakultur", "biomasselag"):
        a = felles.akva.get(eid) or {}
        gjelder_navn = visningsord.tittelform(a.get("navn", ""))
        gjelder_felt = "entity_name" if gjelder_navn else "gjelder"
        gjelder_navn = gjelder_navn or f"Lokalitet {eid}"
        gjelder_url = f"/lokalitet/{eid}/"
        gjelder_slag = "lokalitet"
        kommune = a.get("kommune", "")
        po, po_navn = a.get("prodomraade_kode", ""), a.get("prodomraade_navn", "")
        lok_navn, lok_url = gjelder_navn, gjelder_url
    elif kilde == "eierskap":
        gjelder_navn = f"Tillatelse {eid}"
        gjelder_slag = "tillatelse"
        d = felles.eierskap.get(eid) or {}
        orgnr = (d.get("eier_orgnr") or "").strip()
        if orgnr and orgnr in felles.tillatelser_per_eier:
            gjelder_url = f"/selskap/{orgnr}/"
        lokaliteter = _liste(d.get("lokaliteter"))
        if len(lokaliteter) == 1:
            a = felles.akva.get(lokaliteter[0]) or {}
            lok_navn = (visningsord.tittelform(a.get("navn", ""))
                        or f"Lokalitet {lokaliteter[0]}")
            lok_url = f"/lokalitet/{lokaliteter[0]}/"
            kommune = a.get("kommune", "")
            po, po_navn = (a.get("prodomraade_kode", ""),
                           a.get("prodomraade_navn", ""))
        elif lokaliteter:
            lok_navn = f"{len(lokaliteter)} lokaliteter"
    elif kilde == "enhetsregisteret":
        reg = felles.enhet.get(eid) or {}
        gjelder_slag = "selskap"
        if reg.get("navn"):
            gjelder_navn = reg["navn"]
            gjelder_felt = "entity_name"
            kommune = reg.get("kommune", "")
            if eid in felles.tillatelser_per_eier:
                gjelder_url = f"/selskap/{eid}/"
        else:
            # IKKE «Organisasjonsnummer 912345678». Selskapet står ikke
            # i nyeste øyeblikksbilde av enhetsregisteret, og da er
            # verken navnet eller nummeret gjort rede for av hvitelista
            # — nøyaktig samme grunn som at en `borte`-rad ikke navngis.
            # Et ni-sifret tall vi ikke kan gå god for er det
            # `NI_SIFFER` finnes for, og det gjelder også når tallet er
            # et organisasjonsnummer: ni siffer skiller ikke et AS fra
            # et ENK (docs/VURDERING-NI-SIFFER-PROVEN.md).
            gjelder_navn = "Et selskap som ikke står i nyeste uttrekk"
            gjelder_slag = "borte"
    else:
        gjelder_navn = f"En oppføring i {kilde}"
        gjelder_slag = kilde

    # EN OMRÅDEBESLUTNING GJELDER OMRÅDET, ikke den lokaliteten som
    # tilfeldigvis var den første raden i gruppa. Uten dette ville uke
    # 39 sagt «OTERNESET: rød -> gul» om et vedtak som traff 137
    # lokaliteter, og navnet hadde vært det eneste som skilte den fra
    # de 136 andre som ikke sto der.
    omfang = 1
    if (kilde, felt) in SAMLES_PER_OMRAADE:
        omfang = antall_felt
        kode = _po_av_endring(rad, felles)
        navn = felles.po_navn.get(kode, "")
        # NAVNET ALENE, ikke «Produksjonsområde 4 Nordhordland til
        # Stadt». Cellen merkes `prodomraade_navn`, og porten slår
        # verdien opp i hvitelista: en sammensatt streng står ikke der,
        # og MÅLT stoppet den publiseringen med 16 `ukjent_navn`. Det er
        # samme feil som «Eier: X → Y» gjorde i endringscellen — en
        # merking skal peke på ÉN verdi fra kilden.
        #
        # Nummeret står i sin egen kolonne, som for enhver annen rad.
        gjelder_navn = navn or (f"Produksjonsområde {kode}" if kode
                                else "Lokaliteter uten produksjonsområde")
        gjelder_felt = "prodomraade_navn" if navn else "gjelder"
        gjelder_url = f"/produksjonsomrade/{kode}/" if kode else ""
        gjelder_slag = "produksjonsomrade"
        po, po_navn = kode, navn
        lok_navn = lok_url = kommune = ""

    raa_fra = rad["old_value"] if rad["old_value"] is not None else ""
    raa_til = rad["new_value"] if rad["new_value"] is not None else ""
    if endring == "ny":
        fra, til = IKKE_I_REGISTERET, f"{antall_felt} felt registrert"
        fra_raa = til_raa = ""
    elif endring == "borte":
        fra, til = f"{antall_felt} felt", IKKE_I_REGISTERET
        fra_raa = til_raa = ""
    else:
        fra = visningsord.verdi(felt, raa_fra)
        til = visningsord.verdi(felt, raa_til)
        fra_raa, til_raa = str(raa_fra).strip().lower(), str(raa_til).strip().lower()

    return {
        "dato": str(rad["observed_at"]),
        "uke": _ukeslug(str(rad["observed_at"])),
        "forrige_dato": str(rad.get("forrige_observed_at") or ""),
        "type": slag,
        "type_navn": next(x["navn"] for x in ENDRINGSTYPER if x["id"] == slag),
        "kilde": kilde,
        "entity_id": eid,
        # KILDENS FELTNAVN, uansett radtype. `felt` under er det raden
        # HANDLER om for en leser, og den er «change_type» når hele
        # oppføringen kom eller gikk. `slaa_sammen_trukne()` trenger
        # feltet, og en nøkkel bygget av den andre ville tapt nettopp de
        # radene der kilden begynte eller sluttet å oppgi feltet.
        "kildefelt": felt,
        # `felt_ny` og `felt_borte` HANDLER OM ET FELT, ikke om
        # oppføringen. Fram til 25.09.2026 falt de i samme gren som
        # `borte` og fikk etiketten «Borte fra registeret» — også når
        # raden sa at kilden BEGYNTE å oppgi feltet. Typekolonnen ved
        # siden av sa «Felt oppgitt første gang» i den samme raden.
        "felt": felt if endring in ENDRET_ELLER_FELT else "change_type",
        "etikett": (visningsord.felt(felt) if endring in ENDRET_ELLER_FELT
                    else ("Ny oppføring" if endring == "ny"
                          else "Borte fra registeret")),
        "fra": fra,
        "til": til,
        # MERKINGEN PER VERDI, ikke per celle.
        #
        # «Endring»-cellen bærer en SAMMENSATT streng: «Eier:
        # HELGELAND SMOLT AS → KLUBBAN AS». Merkes hele cellen
        # `eier_navn`, leser porten den strengen som ETT navn — og det
        # står ikke i hvitelista, selv om begge selskapene gjør.
        # MÅLT: det var de to siste funnene før porten ble ren.
        #
        # Cellen merkes derfor med `endringstekst`, som ikke er et
        # feltnavn porten leter etter, og hver VERDI får sin egen
        # merking i et element inni. Det er det samme skillet
        # `_oppgitt_historikk()` gjør med navnet.
        "fra_felt": feltmerke(fra, felt if endring == "endret" else ""),
        "til_felt": feltmerke(til, felt if endring == "endret" else ""),
        # FORSKJELLEN, for de feltene som er lister. Tom for alle andre,
        # og da står pil-formen — se `_differanse()`.
        #
        # `ny` og `borte` er unntatt: de er alt slått sammen per entitet,
        # og «14 felt registrert» er ikke en liste med ledd.
        "differanse": (_differanse(felt, raa_fra, raa_til)
                       if endring not in ("ny", "borte") else []),
        # FARGEKLASSEN ER EN PRESENTASJONSKROK, som i fargetabellen: CSS
        # kan ikke velge på celletekst, så «hvilken av de tre» må stå
        # som en klasse for at ruta foran ordet skal kunne få farge.
        # Ordet er fortsatt bæreren.
        "fra_klasse": FARGE_KLASSE.get(_fargekode(fra_raa), ""),
        "til_klasse": FARGE_KLASSE.get(_fargekode(til_raa), ""),
        "er_farge": slag == "trafikklys",
        # HVOR MANGE RADER HENDELSEN ER SLÅTT SAMMEN AV. 1 for alt
        # annet enn en områdebeslutning, og da er det lokaliteter.
        "omfang": omfang,
        "gjelder": gjelder_navn,
        "gjelder_felt": gjelder_felt,
        # IDENTITETEN SOM PUBLISERES, som er noe annet enn `entity_id`.
        #
        # `entity_id` brukes internt — til å filtrere hendelser til et
        # område, til å slå opp en lokalitet. `identitet` er det som går
        # ut i CSV, JSON og feed-id-er, og den er TOM når vi ikke kan
        # navngi entiteten.
        #
        # Grunnen er at `entity_id` for `enhetsregisteret` ER et
        # organisasjonsnummer. Ni siffer skiller ikke et AS fra et ENK
        # (docs/VURDERING-NI-SIFFER-PROVEN.md), og et nummer som ikke
        # står i hvitelista er nøyaktig det `NI_SIFFER` finnes for.
        # MÅLT: porten meldte 22 slike i CSV-ene og JSON-filene etter at
        # navnene alt var fjernet — nummeret sto igjen i sin egen
        # kolonne.
        #
        # Enten er identiteten gjort rede for i sin helhet, eller så
        # publiseres den ikke.
        "identitet": eid if gjelder_felt == "entity_name" else "",
        "gjelder_url": gjelder_url,
        "gjelder_slag": gjelder_slag,
        "lokalitet": lok_navn,
        "lokalitet_url": lok_url,
        "kommune": kommune,
        "po": po,
        "po_navn": po_navn,
        "anonym": False,
    }


# Registerets skrivemåte av fargeordet er VERSALER («GUL»), forskriftens
# er normalisert ascii («gul»). Begge skal treffe den samme ruta.
_FARGEKODER = {"rod": "rod", "rød": "rod", "gul": "gul",
               "gronn": "gronn", "grønn": "gronn"}


def _fargekode(raa: str) -> str:
    return _FARGEKODER.get(raa, "")


def fargeklasse(verdi) -> str:
    """`lys-*`-klassen til et fargeord, tom for alt annet.

    For maler som får fargen som ORD og ikke som kode — fra- og
    til-cellene i vedtakstabellen på områdesiden. Til 08.10.2026 sto de
    uten klasse, og ruta foran «gul» var tom; se
    `test_fargeruta_i_registertabellen_har_fyll` for hvorfor det er feil.
    """
    return FARGE_KLASSE.get(_fargekode(str(verdi or "").strip().lower()), "")


def _datoord(datoer: list[str], med_aar: bool = True) -> str:
    """«21. september 2026», «14.–15. september» eller «14. og 20. mars».

    To datoer i samme måned skrives med tankestrek, som `ukespenn()`
    gjør. Flere enn to, eller på tvers av måneder, skrives ut med «og»:
    en tankestrek mellom 14. og 20. ville påstått at vi observerte noe
    hver dag i mellom, og det gjorde vi ikke.
    """
    if not datoer:
        return ""
    # ÅRET FJERNES PER DATO, ikke av den ferdige strengen. Et `rsplit`
    # på slutten tok året av den SISTE datoen og lot det stå på de
    # andre: «siden 2. september 2026, 7. september 2026 og 10.
    # september». Målt på uke 38.
    vist = [visningsord.dato(d) if med_aar
            else visningsord.dato(d).rsplit(" ", 1)[0] for d in datoer]
    if len(datoer) == 1:
        return vist[0]
    maaneder = {d[:7] for d in datoer}
    if len(datoer) == 2 and len(maaneder) == 1:
        return f"{datoer[0][8:].lstrip('0')}.–{vist[1]}"
    return visningsord.liste(vist)


def _ukemerke(datoer: list[str], forrige: list[str]) -> str:
    """«Observert 21. september 2026, endringer siden 14.–15. september».

    ## Hvorfor ikke kalenderuka

    Ukesiden sa «Observert i øyeblikksbildene 21.–27. september», og det
    er usant på to måter: vi observerte ÉN dag, og de seks andre dagene
    har vi ikke sett på. Uka er en ETIKETT på når vi så noe, ikke en
    periode vi dekker.

    ## Hvorfor «siden» og ikke «uka før»

    Fordi «uka før» ikke er ett svar. Kildene har ulikt etterslep, og
    for uke 39 sammenlignes det mot både 14. og 15. september. Datoene
    leses av radenes `forrige_observed_at` — ett oppslag, i dataene.

    Året står bare én gang når begge endene ligger i samme år.
    """
    if not datoer:
        return ""
    observert = _datoord(datoer)
    if not forrige:
        return f"Observert {observert}"
    samme_aar = {d[:4] for d in datoer} == {d[:4] for d in forrige}
    return (f"Observert {observert}, endringer siden "
            f"{_datoord(forrige, med_aar=not samme_aar)}")


# UKENE der de tekniske endringene innledes med en setning om
# artsbegrensningene. Bestemt av Heine 06.10.2026: artsbegrensningene
# forblir tekniske, men uke 35 skal si hva trinnet var — 118 lokaliteter
# samme dag (docs/KILDE-AKVAKULTUR.md punkt 4.5). En LISTE og ikke en
# terskel: hvilke uker som får setningen er et valg, ikke en regel om
# hva et «trinn» er. Tallene i setningen regnes av radene.
ARTSBEGRENSNING_SETNING_UKER = frozenset({"2026-35"})


def _artsbegrensninger(tekniske: list[dict]) -> list[dict]:
    """Per observasjonsdato: hvor mange lokaliteter, hvor mange mistet
    alle artsbegrensningene, og hvor mange fikk sine første.

    Bare tall, lest av `fra` og `til`. Ingen grunn: den er ikke sett
    (KILDE-AKVAKULTUR.md 4.5).
    """
    per_dato: dict[str, dict[str, set]] = {}
    for h in tekniske:
        if (h.get("kilde"), h.get("kildefelt")) != ("akvakultur",
                                                     "artsbegrensninger_antall"):
            continue
        try:
            fra, til = int(float(h["fra"] or 0)), int(float(h["til"] or 0))
        except ValueError:
            fra = til = -1
        d = per_dato.setdefault(h["dato"], {"alle": set(), "mistet": set(),
                                            "fikk": set()})
        d["alle"].add(h["entity_id"])
        if fra > 0 and til == 0:
            d["mistet"].add(h["entity_id"])
        if fra == 0 and til > 0:
            d["fikk"].add(h["entity_id"])
    return [{"dato": dato, "lokaliteter": len(d["alle"]),
             "mistet_alle": len(d["mistet"]), "fikk_forste": len(d["fikk"])}
            for dato, d in sorted(per_dato.items())]


# Kildene hver faktasetning bygger på. En setning står bare når HVER av
# dem ble sammenlignet med et tidligere øyeblikksbilde i uka.
UKEFAKTA_KILDER = {
    "eier": ("eierskap",),
    "fisk": ("biomasselag",),
    "kapasitet": ("eierskap", "akvakultur"),
}


def sammenlignet_per_uke() -> dict[str, frozenset[str]]:
    """{ukeslug: kildene som ble SAMMENLIGNET den uka}.

    En kilde er sammenlignet når den har et øyeblikksbilde i uka OG et
    tidligere å sammenligne det med. Det første øyeblikksbildet gir ingen
    endringer, og en uke uten henting heller ikke — i begge tilfeller
    ville «ingen» vært en påstand om noe vi ikke så etter.
    """
    ut: dict[str, set[str]] = defaultdict(set)
    for kilde in {k for ks in UKEFAKTA_KILDER.values() for k in ks}:
        for dato in snapshot.datoer(kilde)[1:]:
            ut[_ukeslug(dato)].add(kilde)
    return {k: frozenset(v) for k, v in ut.items()}


def _ukefakta(ledet: list[dict], sammenlignet: frozenset[str]) -> list[str]:
    """Tre faktasetninger om ukas vesentlige endringer, bygget av radene.

    Eierskifter, fisk til stede og kapasitet — i den rekkefølgen, og også
    når tallet er null: «ingen» er en måling når kilden ble sammenlignet
    den uka. Ble den ikke det, utelates setningen. Tallene er antall
    ULIKE tillatelser og lokaliteter, ikke antall rader, og ingen setning
    sier hvorfor noe skjedde.

    `ledet` er ukas vesentlige rader utenfor selskapsdelen, de samme som
    tabellen viser. En oppføring som kom eller gikk, telles ikke som et
    eierskifte: den er «ny i vårt utvalg» eller «ute av vårt utvalg», og
    står slik i tabellen.
    """
    def ulike(slag: str, felt: str, til: str | None = None) -> int:
        return len({h["entity_id"] for h in ledet
                    if h["type"] == slag and h["kildefelt"] == felt
                    and (til is None or str(h["til"]).lower() == til)})

    def dekket(setning: str) -> bool:
        return all(k in sammenlignet for k in UKEFAKTA_KILDER[setning])

    fakta: list[str] = []
    eier = ulike("eierskap", "eier_orgnr")
    if dekket("eier"):
        fakta.append((visningsord.antall(eier, "tillatelse", "tillatelser")
                      + " fikk ny eier.") if eier
                     else "Ingen tillatelser fikk ny eier.")

    inn, ut = ulike("biomasse", "har_fisk", "ja"), ulike("biomasse", "har_fisk", "nei")
    if dekket("fisk"):
        fakta.append(
            f"Fisk til stede: {visningsord.antall(inn, 'lokalitet', 'lokaliteter')} "
            f"gikk fra nei til ja, {visningsord.tall(ut)} fra ja til nei."
            if inn or ut else
            "Ingen lokaliteter endret status for fisk til stede.")
    # KAPASITET BYGGER PÅ TO KILDER, og hver del står for seg: en
    # endring på en lokalitet er observert selv om eierskapet ikke ble
    # sammenlignet den uka. «Ingen» krever at begge ble det.
    till = ulike("tillatelse", "kapasitet") if "eierskap" in sammenlignet else 0
    akva = "akvakultur" in sammenlignet
    lok = ulike("lokalitet", "kapasitet") if akva else 0
    midl = ulike("lokalitet", "kapasitet_midlertidig") if akva else 0
    deler = [visningsord.antall(n, entall, flertall)
             for n, entall, flertall in ((till, "tillatelse", "tillatelser"),
                                         (lok, "lokalitet", "lokaliteter")) if n]
    if deler:
        setning = f"Kapasiteten endret seg på {visningsord.liste(deler)}"
    elif dekket("kapasitet"):
        setning = "Ingen kapasitet endret seg"
    else:
        setning = ""
    if midl:
        setning = (f"{setning}, og den midlertidige kapasiteten på "
                   if setning else "Den midlertidige kapasiteten endret seg på ")
        setning += visningsord.antall(midl, "lokalitet", "lokaliteter")
    if setning:
        fakta.append(setning + ".")
    return fakta


def les_endringsuker(felles: Felles) -> list[dict]:
    """Én post per ISO-uke vi har observert endringer i, nyest først.

    ## `ny` og `borte` slås sammen per ENTITET

    `diff.compare()` skriver én rad per felt. For en oppføring som
    dukker opp eller forsvinner er det ikke tjue hendelser — det er én,
    skrevet tjue ganger. MÅLT uke 39: 625 `borte`-rader fra
    enhetsregisteret er 29 selskaper.

    En «endret»-rad er derimot ÉN hendelse per felt: at et selskap både
    byttet adresse og meldte konkurs er to ting som skjedde.

    ## Hva som IKKE er med

    Kilder der `observed_at` ikke er innsamlingsdatoen — se
    `ukentlige_kilder()`. Og UBELAGTE kilder, som ellers på nettstedet.
    Begge deler telles og står på siden.
    """
    ukentlige = sorted(ukentlige_kilder())
    ubelagt = ubelagte(felles.vilkaar)
    beveg = felles.bevegelse

    utenfor = beveg.filter(
        ~pl.col("source").is_in(ukentlige)
        & ~pl.col("source").is_in(sorted(MAALESERIER))
        & ~pl.col("source").is_in(sorted(ubelagt))).height

    # UBELAGTE kilder holdes ute HER, ikke bare av tellingen over. Fram
    # til 08.10.2026 var ingen UBELAGT kilde «henting», så `ukentlige`
    # ekskluderte dem allerede; `unntaksvekst` er den første, og uten
    # denne linja sto søknadene i uke 41 på ukessiden, i CSV-en og i
    # feeden. MÅLT mot en kopi av datarepoet med to snapshots.
    mine = beveg.filter(pl.col("source").is_in(ukentlige)
                        & ~pl.col("source").is_in(sorted(ubelagt)))

    # TO SLAGS SAMMENSLÅING, og de har hver sin nøkkel fordi de svarer
    # på hver sin «hva skjedde egentlig én gang her».
    #
    #   ny/borte      per (kilde, entitet, dato). Én oppføring som kom
    #                 eller gikk, skrevet én gang per felt.
    #   trafikklys    per (produksjonsområde, fra, til, dato). ÉN
    #                 fargebeslutning, skrevet én gang per lokalitet i
    #                 området — se `_po_av_endring()`.
    #   avledet       per (kilde, entitet, GRUNNFELT, paret). Ett felt
    #                 som endret seg fordi et annet gjorde det — se
    #                 `Source.avledet_av`.
    #
    # `felt_ny`/`felt_borte` slås IKKE sammen: der er hvert felt sin
    # egen hendelse, og det er hele poenget med å skille dem ut.
    #
    # DEN AVLEDEDE NØKKELEN HAR PARET MED, og ikke bare datoen. To uker
    # der først flagget og siden tallet flyttet seg, er to ting som
    # skjedde — og et felt som endrer seg ALENE er ikke et duplikat av
    # noe. Regelen er «i samme par», ikke «aldri».
    avledede = _avledede_felt()
    grunnfelt = {(k, grunn) for (k, _a), grunn in avledede.items()}
    samlet: dict[tuple, dict] = {}
    rader: list[dict] = []
    # VESENTLIG ELLER TEKNISK, klassifisert på changelog-radene FØR noe
    # slås sammen: reglene ser på andre rader (koordinatpar, fisk samme
    # uke), og de må se alle. Se `vesentlighet`.
    raa = list(mine.iter_rows(named=True))
    klasser = vesentlighet.klassifiser(raa)
    for r, kl in zip(raa, klasser):
        ct = str(r["change_type"])
        kilde_felt = (str(r["source"]), str(r["field"]))
        er_grunn = True
        if ct in ("ny", "borte"):
            nøkkel = ("entitet", str(r["source"]), str(r["entity_id"]),
                      ct, str(r["observed_at"]))
        elif kilde_felt in SAMLES_PER_OMRAADE:
            nøkkel = ("omraade", str(r["source"]), str(r["field"]),
                      _po_av_endring(r, felles), str(r["old_value"]),
                      str(r["new_value"]), str(r["observed_at"]))
        elif kilde_felt in avledede or kilde_felt in grunnfelt:
            er_grunn = kilde_felt not in avledede
            nøkkel = ("avledet", str(r["source"]), str(r["entity_id"]),
                      avledede.get(kilde_felt, str(r["field"])),
                      str(r["observed_at"]),
                      str(r["forrige_observed_at"]))
        else:
            rader.append(dict(_hendelse(r, felles), klasse=kl.klasse))
            continue
        post = samlet.get(nøkkel)
        if post is None:
            samlet[nøkkel] = {"rad": r, "felt": 1, "grunn": er_grunn,
                              "klasse": kl.klasse}
        else:
            post["felt"] += 1
            # EN SAMLET HENDELSE ER VESENTLIG HVIS NOEN AV RADENE ER DET.
            # Et avledet felt er teknisk fordi grunnfeltet ved siden av er
            # vesentlig; hendelsen er grunnfeltets.
            if kl.vesentlig:
                post["klasse"] = vesentlighet.VESENTLIG
            # GRUNNFELTET STÅR I HENDELSEN. «har_fisk: Nei -> Ja» er hva
            # som skjedde; «antall_arter: 0 -> 1» er følgen av det, og en
            # hendelse som viste følgen ville krevd at leseren regnet
            # baklengs. Rekkefølgen radene kommer i er changeloggens, så
            # valget kan ikke hvile på hvilken som kom først.
            if er_grunn and not post["grunn"]:
                post["rad"] = r
                post["grunn"] = True
    rader += [dict(_hendelse(p["rad"], felles, p["felt"]), klasse=p["klasse"])
              for p in samlet.values()]

    per_uke: dict[str, list[dict]] = defaultdict(list)
    for h in rader:
        per_uke[h["uke"]].append(h)
    sammenlignet = sammenlignet_per_uke()

    uker = []
    for slug in sorted(per_uke, reverse=True):
        # SORTERINGEN ER TRE LEDD, og bare det første er «nyest først».
        #
        # Første utkast sorterte alt synkende, og følgen var at
        # forsidens åtte rader ble Ø, Ø, Ø, Ø, Æ, Å, Å, Å — alfabetets
        # slutt, baklengs. Åtte rader som alle heter nesten det samme
        # ser ut som en feil i utvalget, og det var det også: navnet
        # skal stige, det er bare DATOEN som skal synke.
        #
        # Midterste ledd er typerekkefølgen fra `ENDRINGSTYPER`, som er
        # tematisk: trafikklys først, «annet» sist. En uke der noe
        # skjedde med fargen skal vise DET øverst, ikke et regnskapstall
        # fra Enhetsregisteret som tilfeldigvis er alfabetisk først.
        rang = {k["id"]: i for i, k in enumerate(ENDRINGSTYPER)}
        hendelser = sorted(
            per_uke[slug],
            key=lambda h: (_omvendt(h["dato"]), rang.get(h["type"], 99),
                           h["gjelder"]))
        # ORDENE FOR SORTERINGEN, ved siden av sorteringen.
        #
        # Forsiden viser de åtte øverste og må si hva «øverste» betyr —
        # ellers leser en fremmed utvalget som «de viktigste». Skrevet i
        # malen ville de to kunnet bli uenige den dagen nøkkelen endres,
        # og det ville ikke sagt fra.
        sortert_etter = "dato, så type, så navn"
        datoer = sorted({h["dato"] for h in hendelser})
        # DATOENE VI SAMMENLIGNET MOT, lest av radene og ikke regnet ut
        # av kalenderen. `forrige_observed_at` står på hver rad nettopp
        # fordi «uka før» ikke er ett svar: uke 39 sammenlignes mot både
        # 14. og 15. september.
        forrige_datoer = sorted({d for d in
                                 (h.get("forrige_dato") or "" for h in hendelser)
                                 if d})
        # DE VISTE RADENE ER SAMMENSLÅTTE, RADENE I FILA ER DET IKKE.
        #
        # `slaa_sammen_trukne()` slår `tillatelser` og `tillatelser_trukket`
        # sammen: to halvdeler av én hendelse, som én rad i tabellen.
        # `hendelser` er urørt og går til CSV, JSON, feed og JSON-LD — de
        # skal ha hver rad kilden ga oss.
        #
        # ALLE TALLENE PÅ SIDEN TELLER DISSE, ikke `hendelser`. Brikka
        # «Alle N rader» gjorde det fra 25.09.2026, da uke 36 sa «Alle 61
        # rader» over en side som viste 54. Typebrikkene, overskriftstallet
        # og «N rader til» ble stående på `hendelser`, og uke 41 viste
        # derfor brikker som summerte til 158 under «Alle 157», og «91
        # endringer» + «8 rader til» over en tabell med 98 rader. Én rad
        # (Oanes Sjø, `tillatelser_trukket`) var telt to ganger. Et tall som
        # sier hvor mange rader som står der, må telles der de står.
        egen_alle = slaa_sammen_trukne([h for h in hendelser
                                        if h["type"] in EGEN_DEL])
        ledet_alle = slaa_sammen_trukne([h for h in hendelser
                                         if h["type"] not in EGEN_DEL])
        # FILENES TALL, regnet som før 06.10.2026 (økt 3): alle radene,
        # vesentlige og tekniske. CSV- og JSON-hodet bruker det, og filene
        # skal ikke endre seg fordi SIDEN begynte å skille klassene.
        alle = Counter(h["type"] for h in ledet_alle + egen_alle)
        telt_fil = sum(n for t, n in alle.items()
                       if TELLER.get(t, True) and t not in EGEN_DEL)
        # VESENTLIG I TABELLEN, TEKNISK SAMLET. Hovedtabellen,
        # typebrikkene, overskriften og metabeskrivelsen teller bare de
        # vesentlige; de tekniske står i én sammenleggbar del med eget
        # antall. Klassen er `vesentlighet`s, satt på hver hendelse over.
        # Se docs/beslutninger/2026-10-06-tellingen-folger-radene.md.
        ves = vesentlighet.VESENTLIG
        ledet = [h for h in ledet_alle if h.get("klasse", ves) == ves]
        egen = [h for h in egen_alle if h.get("klasse", ves) == ves]
        tekniske = [h for h in ledet_alle + egen_alle
                    if h.get("klasse", ves) != ves]
        antall = Counter(h["type"] for h in ledet + egen)
        # UKAS TALL TELLER BARE DET SOM SKJEDDE I VERDEN. En rad med
        # `teller: False` står i tabellen og i feeden, men ikke i
        # «812 endringer» — samme asymmetri som `utvalgsutvidelse`:
        # merket og beholdt, ikke summert. Se `ENDRINGSTYPER`.
        # TRE TALL, OG DE SVARER PÅ TRE TING. MÅLT uke 39:
        #
        #   antall_rader      453   alle radene i uka
        #   antall            453 - 402 - 13 = 38   overskriftstallet
        #   antall_egen_del   402   selskapsdata, står for seg
        #   utenfor_tellingen  13   felt som kom eller gikk
        #
        # Et tall der 91 % er løpende registervedlikehold svarer ikke på
        # spørsmålet forsiden stiller. Se `selskap` i `ENDRINGSTYPER`.
        telt = sum(n for t, n in antall.items()
                   if TELLER.get(t, True) and t not in EGEN_DEL)
        ikke_telt = sum(n for t, n in antall.items()
                        if not TELLER.get(t, True) and t not in EGEN_DEL)
        # HVA TALLET TELLER, skrevet av slagene som faktisk er der.
        # «38 endringer» alene lar leseren tro det er alt.
        navn_i_ledet = [k["kort"] for k in ENDRINGSTYPER
                        if k["id"] not in EGEN_DEL and antall.get(k["id"])
                        and k.get("teller", True)]
        uker.append({
            "slug": slug,
            "aar": slug[:4],
            "ukenr": slug[5:],
            "vist": f"uke {int(slug[5:])}, {slug[:4]}",
            # KALENDERUKA, og den er IKKE når vi observerte noe. Den
            # står igjen fordi den svarer på «hvilken uke er dette», og
            # brukes der spørsmålet er det. Se `merke` under.
            "spenn": visningsord.ukespenn(datoer[0]),
            # HVA SOM FAKTISK SKJEDDE, i ord: hvilke dager vi observerte,
            # og hvilke dager vi sammenlignet mot.
            #
            # «Observert i øyeblikksbildene 21.–27. september» var usant
            # på to måter: vi observerte ÉN dag (21.), og de seks andre
            # dagene i spennet har vi ikke sett på. Sammenligningen går
            # dessuten mot 14. og 15. september, ikke mot «uka før» som
            # en ubestemt størrelse — kildene har ulikt etterslep, og for
            # uke 39 er det to ulike datoer.
            "merke": _ukemerke(datoer, forrige_datoer),
            "observert_datoer": datoer,
            "forrige_datoer": forrige_datoer,
            "datoer": datoer,
            "forste_dato": datoer[0],
            "siste_dato": datoer[-1],
            "hendelser": hendelser,
            "sortert_etter": sortert_etter,
            "ledet": ledet,
            "egen_del": egen,
            "antall": telt,
            "antall_egen_del": len(egen),
            "ledet_slag": visningsord.liste(navn_i_ledet),
            # RADENE SIDEN VISER, etter sammenslåingen.
            "antall_rader": len(ledet) + len(egen),
            # RADENE FILENE HAR. CSV-en og JSON-en er bygget av
            # `hendelser`, og nedlastingsnoten lover nettopp det: «alle
            # N radene i uka, ikke bare de som vises her». Er de to
            # tallene det samme, er løftet tomt; er de ulike, sier noten
            # sant. De er ulike fordi sammenslåingen er en visning.
            "antall_i_fila": len(hendelser),
            # TALLET LENKA TIL UKESIDEN SKAL BRUKE: det oppsummeringen
            # teller, pluss selskapsdataene som står for seg. Ikke
            # `antall_rader`, som også rommer radene som med vilje ikke
            # telles (felt som kom eller gikk) — en lenke som sa «Alle
            # 453 endringene» om et tall der 13 ikke er endringer,
            # motsier tabellen den står under.
            "antall_med_egen_del": telt + len(egen),
            "utenfor_tellingen": ikke_telt,
            # DE TEKNISKE, i sin egen del. Telles ikke i noe tall over.
            "tekniske_rader": tekniske,
            # TRE FAKTASETNINGER øverst på ukesiden. Se `_ukefakta()`.
            "fakta": _ukefakta(ledet, sammenlignet.get(slug, frozenset())),
            "artsbegrensninger": (_artsbegrensninger(tekniske)
                                  if slug in ARTSBEGRENSNING_SETNING_UKER
                                  else []),
            "tekniske": len(tekniske),
            "antall_fil": telt_fil,
            # Nedlastingene, med navnet de har på disk. Se
            # `endringer_datasett()`.
            "xlsx_filnavn": f"{endringer_stamme(slug)}.xlsx",
            "zip_filnavn": f"{endringer_stamme(slug)}.zip",
            "typer": [dict(k, antall=antall.get(k["id"], 0))
                      for k in ENDRINGSTYPER],
            "utenfor_uka": utenfor,
        })
    return uker


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
    # TREDJE BELEGGSGRAD, fra 23.09.2026. Fargen står ikke i noen
    # forskrift, og det er ikke en mangel i kilden: trafikklyset
    # avgjøres i to trinn, og et GULT område krever ingen bestemmelse.
    # Den står i departementets kunngjøring av fargeleggingen. Se
    # `beslutning.py`.
    "beslutning": "fargeordet står i departementets kunngjøring av "
                  "fargeleggingen, ikke i forskriften",
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
        rader.append(_fargerad(po, aar, felles))
    return rader


# BELEGGSRANGERING: hvilket belegg som VISES når flere kilder gir samme
# farge i samme celle.
#
# Sterkest først. Skillet er hvor DIREKTE fargeordet står:
#
#   ordrett         fargeordet står i forskriftens egen bestemmelse
#   beslutning      fargeordet står ordrett i departementets kunngjøring
#   kapittelhjemmel fargen er SLUTTET av hvilket kapittel området står i
#
# De to første er begge ordrett; forskjellen er hvilket dokument. Den
# tredje er en utledning, og den er svakere enn begge: ingen har skrevet
# ordet «grønn» om området — vi har lest det ut av en plassering.
#
# MÅLT 23.09.2026: 17 celler står som «grønn/utledet» og har samtidig en
# kunngjøring som sier «grønn» ordrett. De blir «beslutning», med
# utledningen listet ved siden av.
#
# DE ANDRE FORSVINNER IKKE. En celle der to uavhengige dokumenter sier
# det samme, er bedre belagt enn en der bare ett gjør det — og det er
# nettopp den opplysningen en rangering uten liste ville kastet.
BELEGGSRANG = ("ordrett", "beslutning", "kapitteloverskrift",
               "kapittelhjemmel")


def _fargerad(po: str, aar: str, felles: Felles) -> dict:
    """Én celle: sterkeste belegg først, de andre ved siden av.

    Samler ALLE kildene som sier noe om (område, runde), rangerer dem
    etter `BELEGGSRANG`, og lar den sterkeste bære cellen.
    """
    kandidater: list[dict] = []

    # Forskriften.
    d = (felles.po_farger.get(po) or {}).get(aar)
    if d and (d.get("farge") or "").strip():
        raa = d["farge"].strip()
        maate = (d.get("farge__lesemaate") or "").strip()
        kandidater.append({
            "lesemaate": maate,
            "lesemaate_tekst": LESEMAATE.get(maate, maate or "ukjent"),
            "raa": raa, "sitat": "", "sitat_dato": "", "sitat_url": "",
            "kilde": forskrift_for_runde(aar).get("id", "forskriften"),
        })

    # Departementets kunngjøring.
    b = beslutning.for_runde(aar).get(po)
    if b:
        kandidater.append({
            "lesemaate": "beslutning",
            "lesemaate_tekst": LESEMAATE["beslutning"],
            "raa": b["farge"], "sitat": b["sitat"], "sitat_dato": b["dato"],
            "sitat_url": beslutning.url(aar),
            "kilde": f"kunngjøringen {visningsord.dato(b['dato'])}",
        })

    if not kandidater:
        return {
            "aar": aar, "farge": FARGE_MANGLER,
            "farge_felt": FARGE_MANGLER_FELT, "farge_klasse": "",
            "lesemaate": "", "lesemaate_tekst": "ingen bestemmelse å lese",
            "sitat": "", "sitat_dato": "", "sitat_url": "", "ellers": [],
        }

    kandidater.sort(key=lambda k: BELEGGSRANG.index(k["lesemaate"])
                    if k["lesemaate"] in BELEGGSRANG else len(BELEGGSRANG))
    sterkest = kandidater[0]

    # KILDENE SOM SIER DET SAMME, og de som IKKE gjør det.
    #
    # En uenighet skal ikke gjemmes bak en rangering. MÅLT 23.09.2026
    # er det ingen — 46 av 46 overlappende celler er enige — men lista
    # sier hvilken det er, så en framtidig uenighet ser ut som en.
    ellers = [{"lesemaate_tekst": k["lesemaate_tekst"], "kilde": k["kilde"],
               "farge": visningsord.verdi("farge", k["raa"]),
               "enig": k["raa"] == sterkest["raa"]}
              for k in kandidater[1:]]

    return {
        "aar": aar,
        "farge": visningsord.verdi("farge", sterkest["raa"]),
        "farge_felt": "farge",
        "farge_klasse": FARGE_KLASSE.get(sterkest["raa"], ""),
        "lesemaate": sterkest["lesemaate"],
        "lesemaate_tekst": sterkest["lesemaate_tekst"],
        "sitat": sterkest["sitat"],
        "sitat_dato": sterkest["sitat_dato"],
        "sitat_url": sterkest["sitat_url"],
        "ellers": ellers,
    }


# ---------------------------------------------------- FORSKRIFTSRUNDENE
#
# Hvilken forskrift som uttaler seg om hvilken runde, LEST AV KILDEN og
# ikke gjengitt her. `sources/trafikklysvedtak.FORSKRIFTER` er tabellen
# som `gjenkjenn()` bruker for å avgjøre hvilket dokument en kropp ER,
# og den bærer tittel, FOR-nummer, runder og URL. En kopi hos
# publiseringsleddet ville vært en andre liste som kan bli stående
# gammel — formen F6 og F7 hadde.


def forskrift_for_runde(aar: str) -> dict:
    """{tittel, id, url} for forskriften som gir fargen i runde `aar`.

    NYESTE forskrift som dekker runden, og ikke den eldste. Grunnen er
    at det er den vi faktisk viser: hver runde skrives først av den
    eldste forskriften som dekker den og revideres deretter av de nyere
    (se `backfill.py --rapporter`), så verdien i nyeste
    `<aar>-12-31.parquet` kommer fra den nyeste kroppen.

    Tom dict for en runde ingen forskrift i tabellen dekker. Da står
    ingen lenke — en lenke til et dokument vi ikke har lest ville vært
    en påstand om hvor tallet kom fra.
    """
    from sources.trafikklysvedtak import FORSKRIFTER

    try:
        runde = int(aar)
    except (TypeError, ValueError):
        return {}
    treff = [f for f in FORSKRIFTER if runde in f.aar]
    if not treff:
        return {}
    siste = treff[-1]
    return {"tittel": siste.tittel, "id": siste.forskrift_id,
            "url": siste.url, "merknad": siste.merknad}


# ------------------------------------------------------- BIOMASSEGRAFEN
#
# ## HVORFOR DEN STÅR HER OG IKKE PÅ LOKALITETSSIDEN
#
# Overleveringen tegner biomassesøyler på lokalitetssiden.
# Fiskeridirektoratets offentlige biomassetall er per
# PRODUKSJONSOMRÅDE — se docs/KILDE-BIOMASSE.md — og mengdetallene per
# lokalitet ligger i biomassedatabasen etter
# akvakulturdriftsforskriften § 44, som er børssensitiv og ikke
# offentlig (bekreftet av HI 09.09.2026).
#
# Grafen er derfor flyttet dit tallene finnes. Lokalitetssiden har i
# stedet en ukestripe med ja/nei fra biomasselaget. Se avvik 1 i
# oppdraget.
#
# ## BIOMASSE REVIDERER FORTIDEN, og grafen må si det
#
# CLAUDE.md 1b-5: fila publiseres på nytt den 20. hver måned, og hver
# publisering kan endre tall helt tilbake til 2017. MÅLT 25.08.2026 mot
# en Wayback-kopi fra 07.08.2024: 490 av 3 973 felles rader (12,3 %)
# endret, i hvert eneste år i serien.
#
# Grafen viser NYESTE PÅSTAND om hver måned. Det er ikke det samme som
# «tallet for den måneden», og forskjellen står i bildeteksten framfor
# å bli pusset bort.

BIOMASSE_BREDDE = 900
BIOMASSE_HOYDE = 200
BIOMASSE_MARG = {"v": 56, "h": 12, "o": 14, "u": 28}


def biomassegraf(serie: list[dict]) -> dict | None:
    """Månedlige søyler over beholdningen i tonn, eller None.

    Samme grammatikk som lusegrafen — søyler, ikke en kurve — og av
    samme grunn: et månedstall er én påstand om én måned, ikke et punkt
    på en kontinuerlig kurve.
    """
    if not serie:
        return None
    verdier = []
    for m in serie:
        try:
            verdier.append(float(m["tonn"]))
        except (KeyError, TypeError, ValueError):
            verdier.append(None)
    if not any(v is not None for v in verdier):
        return None

    maks = max(v for v in verdier if v is not None)
    tak, trinn = _grafskala(maks / 1000.0)      # skalaen regnes i kilotonn
    tak, trinn = tak * 1000.0, trinn * 1000.0
    n = len(serie)
    v, h, o, u_ = (BIOMASSE_MARG["v"], BIOMASSE_MARG["h"],
                   BIOMASSE_MARG["o"], BIOMASSE_MARG["u"])
    plott_b = BIOMASSE_BREDDE - v - h
    plott_h = BIOMASSE_HOYDE - o - u_
    bunn = o + plott_h
    steg = plott_b / n
    bredde = round(max(steg * 0.82, 0.8), 2)

    def x(i: int) -> float:
        return round(v + steg * i, 1)

    def y(verdi: float) -> float:
        return round(o + plott_h * (1 - verdi / tak), 1)

    gulv = 1.2
    soyler = [{"x": x(i), "y": round(min(y(w), bunn - gulv), 1),
               "h": round(max(bunn - y(w), gulv), 1),
               "maaned": serie[i]["maaned"],
               "verdi": visningsord.tall(round(w))}
              for i, w in enumerate(verdier) if w is not None]

    linjer = []
    verdi = 0.0
    while verdi <= tak + 1e-9:
        linjer.append({"y": y(verdi), "verdi": verdi,
                       "etikett": visningsord.tall(round(verdi / 1000))})
        verdi += trinn

    aar = [{"x": x(i), "etikett": m["maaned"][:4]}
           for i, m in enumerate(serie)
           if i and m["maaned"][:4] != serie[i - 1]["maaned"][:4]]
    if aar:
        hver = max(1, math.ceil(len(aar) * 34 / plott_b))
        aar = aar[::hver]

    return {
        "bredde": BIOMASSE_BREDDE, "hoyde": BIOMASSE_HOYDE,
        "plott_x": v, "plott_y": o,
        "plott_bredde": plott_b, "plott_hoyde": plott_h,
        "bunn": round(bunn, 1),
        "soyler": soyler,
        "soylebredde": bredde,
        "linjer": linjer,
        "aar": aar,
        "maaneder": n,
        "maaneder_med_tall": sum(1 for w in verdier if w is not None),
        "maks": visningsord.tall(round(maks)),
        "maks_maaned": serie[verdier.index(max(
            w for w in verdier if w is not None))]["maaned"],
        "siste": (visningsord.tall(round(verdier[-1]))
                  if verdier[-1] is not None else ""),
        "fra": serie[0]["maaned"],
        "til": serie[-1]["maaned"],
    }


# Feltene biomassefila bærer, og som områdesiden viser. Eksplisitt
# liste: en kilde som legger til et felt skal ikke endre en publisert
# tabell uten at noen har bestemt det.
BIOMASSEFELT = ("biomasse_kg", "beholdning_antall", "beholdning_antall_laks",
                "beholdning_antall_regnbueorret", "utsett_smolt_antall",
                "uttak_antall", "dodfisk_antall", "romming_antall",
                "forforbruk_kg", "andel_av_beholdning")


def _biomasse() -> tuple[dict[str, list[dict]], dict[str, str]]:
    """({po: [måned, ...]}, {po: nyeste published_at}).

    ## `observed_at` ER MÅNEDSSLUTT, ikke hentedatoen

    Kilden er `verden`-partisjonert: fila for 2026-05-31 handler om mai
    2026, uansett når vi hentet den. Det er derfor serien kan gå tilbake
    til 2017 med seks uker med innsamling bak oss.

    ## NYESTE PÅSTAND PER MÅNED

    `snapshot.versjoner()` gir alle versjoner av samme dato, og vi tar
    den siste. For en revisjonskilde er det et VALG og ikke en
    selvfølge: de eldre versjonene er ikke feil, de er tidligere
    påstander om den samme måneden (CLAUDE.md 1b-5). Grafen viser den
    nyeste, og bildeteksten sier at det er det den gjør.
    """
    serier: dict[str, list[dict]] = defaultdict(list)
    utgitt: dict[str, str] = {}
    for dato in snapshot.datoer("biomasse"):
        versjonene = snapshot.versjoner("biomasse", dato)
        if not versjonene:
            continue
        _nr, ramme = versjonene[-1]
        publisert = snapshot.published_at_i(ramme) or ""
        per_po: dict[str, dict[str, str]] = defaultdict(dict)
        for eid, felt, verdi in ramme.select(
                ["entity_id", "field", "value"]).iter_rows():
            if str(felt) in BIOMASSEFELT:
                per_po[str(eid)][str(felt)] = verdi
        for eid, raa in per_po.items():
            kilo = raa.get("biomasse_kg") or ""
            try:
                tonn = float(kilo) / 1000.0
            except ValueError:
                tonn = None
            serier[eid].append({
                "maaned": dato,
                "tonn": tonn,
                "publisert": publisert,
                **{f: (raa.get(f) or "") for f in BIOMASSEFELT},
            })
            if publisert > utgitt.get(eid, ""):
                utgitt[eid] = publisert
    return dict(serier), utgitt


# Hvor mange uker med endringer områdesiden viser. Overleveringen sier
# tolv; tallet står her og ikke i malen.
PO_ENDRINGSUKER = 12


def _po_fargerader(po: str, felles: Felles) -> list[dict]:
    """Fargerundene med belegg OG lenke til forskriften.

    Utvider `_fargerader()` med forskriftsopplysningene, som leses av
    kilden — se `forskrift_for_runde()`.
    """
    ut = []
    for r in _fargerader(po, felles):
        ut.append(dict(r, forskrift=forskrift_for_runde(r["aar"])))
    return ut


def _rundeopplysninger(aar: str) -> dict:
    """Beslutningsdato, dokumenttype og tegnforklaring for én runde.

    Tegnforklaringen er IKKE felles for de fem rundene, og det er ikke
    en detalj: i 2018 ble de røde områdene ikke trukket ned. Se
    `beslutning.FOLGER`.

    Tom for en runde som ikke er godkjent — da står bare forskriftens
    egen lenke, som før.
    """
    if aar not in beslutning.GODKJENT:
        return {"dato": "", "type": "", "url": "", "tegn": []}
    dato = beslutning.KROPPER.get(aar, ("", ""))[0]
    return {
        "dato": dato,
        "type": beslutning.dokumenttype(aar),
        "url": beslutning.url(aar),
        "tegn": [dict(t, farge_vist=visningsord.verdi("farge", t["farge"]),
                      klasse=FARGE_KLASSE.get(t["farge"], ""))
                 for t in beslutning.tegnforklaring(aar)],
    }


def _po_saerskilt(po: str, felles: Felles) -> list[dict]:
    """Rundene der departementet sier det vurderte DETTE området særskilt.

    Fargeleggingen følger ekspertgruppens vurdering når de to
    grunnlagsårene er enige. Er de ikke det, sier kunngjøringen at
    departementet gjorde en egen vurdering — og navngir områdene.

    Setningen gjengis ordrett, med dato og lenke. Ingen tolkning: at
    en farge ble til på den ene eller andre måten er ikke vår sak å
    veie, og en oppsummering ville vært nettopp det.
    """
    ut = []
    for dato in felles.runder:
        aar = dato[:4]
        d = beslutning.saerskilt_for_runde(aar).get(po)
        if d:
            ut.append({"aar": aar, "sitat": d["sitat"], "dato": d["dato"],
                       "url": beslutning.url(aar)})
    return ut


def bygg_produksjonsomrade(po: str, felles: Felles) -> dict:
    """Alt én produksjonsområdeside trenger.

    Tar `felles` som krav og ikke som valgfritt: tretten sider leser de
    samme snapshotene, og en variant som leste selv ville vært en andre
    vei til samme side — formen F6 og F7 hadde.
    """
    lokaliteter = []
    for loknr in felles.lokaliteter_per_po.get(po, ()):
        a = felles.akva[loknr]
        mine_till = {nr: felles.eierskap[nr] for nr in
                     felles.tillatelser_per_lokalitet.get(loknr, ())}
        ovf = [{"dato": o.get("journal_dato", ""),
                "tillatelse": o.get("tillatelse_nr", ""),
                "mottaker_navn": o.get("mottaker_navn", ""),
                "mottaker_orgnr": o.get("mottaker_orgnr", "")}
               for nr in mine_till
               for o in felles.overforinger_per_tillatelse.get(nr, ())]
        selskap = _lokalitetens_selskap(mine_till, ovf, felles.eierskap)
        navn = visningsord.tittelform(a.get("navn", ""))
        kommune = a.get("kommune", "")
        lokaliteter.append({
            "loknr": loknr,
            "navn": navn,
            "original": a.get("navn", ""),
            "kommune": kommune,
            "selskap": selskap,
            "status": visningsord.verdi("versjon_status",
                                        a.get("versjon_status", "")),
            "kapasitet": visningsord.maalt(a.get("kapasitet", ""),
                                           a.get("kapasitet_enhet", "")),
            "arter": visningsord.verdi("arter", a.get("arter", "")),
            # `sist_endret` BYGGES IKKE HER LENGER (25.09.2026).
            # Kolonnen er ute av lokalitetstabellen på områdesiden: den
            # svarte på «når så VI dette» i en tabell som ellers svarer
            # på «hva står i registeret nå», og den kostet ett oppslag
            # over hele `felles.sist_endret` per lokalitet.
            #
            # Verdien finnes fortsatt der den betyr noe — kolonnen «Sist
            # endret» i registerfelt-tabellen på lokalitetssiden og på
            # selskapssiden, per FELT og ikke per entitet.
            # SØKENØKKELEN BYGGES HER og ikke av celletekst i
            # nettleseren. Et treff på et kolonnenavn eller på en dato i
            # en annen kolonne er et treff leseren ikke kan forklare.
            # Se `omraadesok()` i maler/kystloggen.js.
            "sok": " ".join(x.lower() for x in
                            (loknr, navn, a.get("navn", ""), kommune,
                             selskap.get("navn", "")) if x),
        })

    # Endringene for OMRÅDET SELV (trafikklysvedtak), og endringene i
    # lokalitetene i det. To ulike ting: den første er et
    # forvaltningsvedtak om området, den andre er hva som har skjedd med
    # anleggene i det. De står i hver sin tabell framfor å blandes.
    rader = felles.registerendringer.get(po, ())
    ubelagt = ubelagte(felles.vilkaar)
    om_omraadet = [_endringsrad(r, po) for r in rader
                   if not er_maaleserie(str(r["source"]), str(r["field"]))
                   and r["source"] not in ubelagt]
    om_omraadet.sort(key=lambda r: r["dato"], reverse=True)

    mine = {l["loknr"] for l in lokaliteter}
    uker = [u for u in les_endringsuker(felles)][:PO_ENDRINGSUKER]
    i_omraadet = slaa_sammen_trukne(
        [h for u in uker for h in u["hendelser"]
         if h["entity_id"] in mine or h["po"] == po])

    serie = felles.biomasse.get(po, [])
    return {
        "nr": po,
        "navn": felles.po_navn.get(po, ""),
        "status": (felles.akva[lokaliteter[0]["loknr"]].get("prodomraade_status", "")
                   if lokaliteter else ""),
        "naa": (felles.po_naa.get(po)
                or {"farge": FARGE_MANGLER, "klasse": "", "uenig": ""}),
        "akva_dato": felles.akva_dato,
        "akva_hentet": felles.akva_hentet,
        # KARTET OVER OMRÅDET, med hver lokalitet som en prikk.
        # Prikkene er en annen vei til tabellen under, aldri den
        # eneste: hver lokalitet står der med navn, kommune og
        # innehaver.
        "kart": kart.omraadekart(po, [
            (l["loknr"], l["navn"],
             felles.akva[l["loknr"]].get("breddegrad", ""),
             felles.akva[l["loknr"]].get("lengdegrad", ""))
            for l in lokaliteter]),
        "runder": _po_fargerader(po, felles),
        # Beslutningsdato, dokumenttype og tegnforklaring PER RUNDE.
        # Står ved siden av rundene og ikke i dem: den gjelder alle
        # tretten områdene i runden, ikke dette ene.
        "rundeopplysninger": [dict(_rundeopplysninger(d[:4]), aar=d[:4])
                              for d in felles.runder],
        # DEPARTEMENTETS EGEN MERKNAD om at det vurderte NETTOPP dette
        # området særskilt. Bare de rundene et menneske har lest, og
        # bare ordrett — se `beslutning.saerskilt()` og punktet i
        # oppdraget: «Kort, uten tolkning.»
        "saerskilt": _po_saerskilt(po, felles),
        "lokaliteter": lokaliteter,
        "lokaliteter_antall": len(lokaliteter),
        "selskaper_antall": len({l["selskap"]["orgnr"] for l in lokaliteter
                                 if l["selskap"]["orgnr"]}),
        "uten_kjent_eier": sum(1 for l in lokaliteter
                               if not l["selskap"]["orgnr"]),

        # ---- biomassen, flyttet hit fra lokalitetssiden ----
        "biomasse": biomassegraf(serie),
        "biomasse_rader": list(reversed(serie[-24:])),
        "biomasse_maaneder": len(serie),
        "biomasse_utgitt": felles.biomasse_utgitt.get(po, ""),

        # ---- endringene ----
        "endringer": om_omraadet,
        "i_omraadet": i_omraadet,
        "endringsuker": len(uker),
        # FRA MÅLESERIEINDEKSEN, ikke fra `registerendringer` — den
        # inneholder per konstruksjon ingen måleserierader, så en telling
        # der ville alltid gitt 0.
        "maaleserie_rader": felles.maaleserierader.get(po, 0),
        "ubelagte_rader": sum(1 for r in rader if r["source"] in ubelagt),
        "ubelagte_kilder": sorted(ubelagt),

        "siter": {
            "url": f"{_basisurl()}/produksjonsomrade/{po}/",
            "uke": visningsord.uke(felles.akva_dato),
            "dato": visningsord.dato(felles.akva_dato),
            "aar": felles.akva_dato[:4],
            "sjekksum": felles.sjekksum,
        },
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

# Eieren ER kjent, og vises likevel ikke. To ulike påstander, to ulike
# tekster — `EIER_UKJENT` betyr at kilden tier, denne betyr at vi
# tier.
#
# ## Hvorfor raden ikke bare utelates
#
# Tillatelsen finnes, og lokaliteten har den. En utelatt rad ville gjort
# at tabellen viste 9 av 10 tillatelser uten å si det, og det er samme
# feil som `EIER_UKJENT` ble laget for å unngå. Raden står; navnet gjør
# det ikke.
EIER_PERSONFORM = "eieren er en personform — navnet vises ikke"
EIER_PERSONFORM_FELT = "eier_personform"

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


def _eierrad(nr: str, d: dict, former: dict | None = None) -> dict:
    """Én rad i eierskapstabellen, med eller uten eiernavn.

    ## Spørsmålet stilles til KILDEN, i kildens vokabular

    `sources.eierskap.er_person()` er den samme funksjonen `personeier()`
    bruker for å la være å lage en selskapsside, og den samme `fetch()`
    bruker for å la være å hente raden i det hele tatt. Ett spørsmål,
    ett sted, tre ledd som stiller det.

    ## Hvorfor leddet trengs når kilden allerede filtrerer

    Fordi et snapshot er skrevet én gang og leses i årevis. MÅLT
    21.09.2026: mandagens eierskap-snapshot ble skrevet av kode fra før
    16.09, da `FORM_KART` ikke kjente `JointlyOwnedShippingCompany`.
    Tillatelsen H-FJ-0018 fikk derfor ingen `organisasjonsform`-rad, og
    lesedøra — som matcher på nettopp det feltet — har ingenting å bite
    i. Den tok de 8 andre (6 DA, 2 ANS) som hadde en oversatt kode.

    Døra er ikke i stykker. Den svarer på «bærer denne entiteten en
    personform», og for denne raden er svaret ærlig nei: formen står
    ikke der. `eier_type` gjør det, og det er kildens felt — derfor
    stilles spørsmålet her og ikke i `core/`.

    Det er samme skille som 1b-2: to felter som PLEIER å følge
    hverandre, helt til en kjøring med gammel kode skiller dem.
    """
    from sources.eierskap import er_person

    if er_person(d.get("eier_type")):
        return {
            "nr": nr,
            "eier_navn": EIER_PERSONFORM,
            "eier_felt": EIER_PERSONFORM_FELT,
            "eier_orgnr": "",
            "type": d.get("tillatelse_type", ""),
            "kapasitet": visningsord.maalt(d.get("kapasitet", ""),
                                           d.get("kapasitet_enhet", "")),
            # DATOEN I OSLO, ikke datodelen av UTC-stempelet. Se
            # `visningsord.oslodato()`: 2 854 av 2 943 `tildelt_tid`
            # faller på en annen dato i norsk tid.
            "tildelt_dato": visningsord.oslodato(d.get("tildelt_tid")),
            "tildelt_navn": "",
            "tildelt_orgnr": "",
        }
    return {
        "nr": nr,
        "eier_navn": d.get("eier_navn", ""),
        "eier_felt": "eier_navn",
        "eier_orgnr": d.get("eier_orgnr", ""),
        "type": d.get("tillatelse_type", ""),
        "kapasitet": visningsord.maalt(d.get("kapasitet", ""),
                                       d.get("kapasitet_enhet", "")),
        "tildelt_dato": visningsord.oslodato(d.get("tildelt_tid")),
        **_tildelt(d, former),
    }


def _navn_eller_skjult(navn: str, felt: str, orgnr: str = "",
                       former: dict | None = None) -> tuple[str, str, str]:
    """(verdi, feltmerke, orgnr) for en navnecelle — eller vår tekst.

    Navnet vises BARE når `publiseringsvakt.vises_som_organisasjon()`
    sier ja: en ikke-personlig formkode i navnet, eller et orgnr
    registeret gir en ikke-personlig form. Alt annet blir
    `skjult_navn()`, og orgnummeret går med — står nummeret igjen, er
    navnet ett oppslag i Brreg unna.

    `former` er `publiseringsvakt.formkart()`. None betyr at vi ikke vet
    noe om orgnummeret, og da avgjør navnet alene.
    """
    orgnr = (orgnr or "").strip()
    if publiseringsvakt.vises_som_organisasjon(
            navn, (former or {}).get(orgnr, ())):
        return navn, felt, orgnr
    kode = publiseringsvakt.personform_i_navn(navn)
    return (publiseringsvakt.skjult_navn(kode),
            publiseringsvakt.SKJULT_NAVN_FELT, "")


def _er_null(verdi: object) -> bool:
    """Sant når registerets tall er 0 — «0», «0.0». Tomt er ikke 0."""
    try:
        return float(str(verdi).strip()) == 0
    except ValueError:
        return False


def _tildelt(d: dict, former: dict | None = None) -> dict:
    """Hvem tillatelsen ble tildelt — eller at navnet ikke vises.

    Se `_navn_eller_skjult()`. MÅLT 05.10.2026: 12 `tildelt_navn` på
    formen «ETTERNAVN, FORNAVN» sto på det publiserte nettstedet fordi regelen før
    da bare skjulte det den GJENKJENTE som personlig.
    """
    navn, felt, orgnr = _navn_eller_skjult(
        d.get("tildelt_navn", ""), "tildelt_navn",
        d.get("tildelt_orgnr", ""), former)
    return {"tildelt_navn": navn, "tildelt_felt": felt,
            "tildelt_orgnr": orgnr}


def _tillatelsesrader(mine_till: dict, uten_eier: list[str],
                      former: dict | None = None) -> list[dict]:
    """Radene i eierskapstabellen — kjente OG ugjorte rede for.

    Samme radform for begge, med `eier_felt` som skiller dem. En egen
    tabell for de ukjente ville gjort fraværet til noe man kan overse;
    en utelatt rad ville gjort det usynlig.
    """
    rader = [
        _eierrad(nr, d, former) for nr, d in mine_till.items()
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

# Brakkleggingsstripa er LAV og ligger i bunnen, ikke som et bånd over
# hele høyden. Overleveringen tegner den slik, og det er riktigere enn
# båndet som sto her til 22.09.2026: et bånd over hele plottet leses som
# en verdi på y-aksen, og brakklegging er ikke en luseverdi. Stripa
# ligger UNDER nullinja og kan ikke forveksles med en søyle.
GRAF_BRAKK_HOYDE = 5

# Trinnene en y-akse får lov å bruke. Et «pent» tall er ikke en estetisk
# sak: 0,4 og 0,8 leses som fjerdedeler, 0,37 leses ikke som noe.
# TRINNENE GÅR OPP TIL 1 000, og ikke bare til 10. Stigen stoppet der
# så lenge den bare tjente lusegrafen, der 1,54 er en høy verdi. Da
# biomassegrafen kom til 22.09.2026 — 108 kilotonn på det høyeste — falt
# skalaen gjennom hele stigen og endte i reserven `maks / 4`, som ga
# aksen 0 / 27 / 54 / 81 / 108. Et «pent» tall er ikke en estetisk sak:
# 27 leses ikke som noe.
GRAF_TRINN = (0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0,
              20.0, 25.0, 50.0, 100.0, 200.0, 250.0, 500.0, 1000.0)


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
    tabellen sier fra i klartekst.

    ## SØYLER, ikke en kurve (22.09.2026)

    Fram til i dag var dette en brutt linje. Overleveringen tegner
    søyler, og det er ikke en smakssak her: en kurve TREKKER EN STREK
    MELLOM TO MÅLINGER, og påstår dermed noe om uka imellom. Lusetall er
    én telling per uke, ikke en kontinuerlig størrelse, og hver uke er
    en egen påstand.

    Den gamle koden måtte bryte linja ved hvert hull nettopp for å
    unngå å påstå noe om uker uten tall. Med søyler faller problemet
    bort av seg selv: en uke uten tall har ingen søyle, og et tomrom
    ligner ikke på en null.

    ## TILTAKSGRENSA ER SAMLET INN — fra BarentsWatch, ikke av oss

    Fram til 09.10.2026 sto det her at grensa ikke var samlet inn. Det
    var feil. `Lusegrense uke` hadde stått i hver sjøtemperaturkropp i
    `data/arkiv/` siden 2012 uten å bli lest (docs/MALING-FUNN-OKTOBER.md
    F4.5), og leses nå som `sjotemperatur.lusegrense` per lokalitet og
    uke: 0,5, og 0,2 i vårukene fra 2017. BarentsWatchs eget flagg
    `Over lusegrense uke` stemmer med den i alle 409 118 lokalitetsuker.

    Det som fortsatt gjelder, er grunnen til at den ikke ble tegnet:
    en strek på 0,5 tegnet av OSS ville vært en påstand om regelverket.
    Grensa er derfor kildens verdi for akkurat den uka, aldri en
    konstant i koden.

    Linja er TRAPPER, ikke en skrå strek: grensa gjelder hele uka og
    skifter ved ukeskiftet. Der kilden ikke oppgir en grense — eller
    lokaliteten mangler i uka — har linja et brudd, av samme grunn som en
    uke uten tall har et tomrom. Y-aksen tar med grensa, ellers ville en
    lokalitet med lave tall fått linja utenfor plottet.

    ## SØYLENE OVER GRENSA ER RUST (09.10.2026)

    Som i overleveringen: en søyle på eller over grensa for uka står i
    `--rust`, de andre i `--hav5`. «Over» er `_over_grensen()` — halv-opp
    til to desimaler, slik BarentsWatch selv regner, MÅLT mot deres eget
    flagg i 409 118 av 409 118 uker. Uten grense for uka er søylen ikke
    over: en uke uten grense er ikke en uke under den heller, men den får
    ingen farge vi ikke kan begrunne. Fargen gjør linja lesbar på telefon
    uten å telle søyler.
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

    grenser: list[float | None] = []
    for u in serie:
        try:
            grenser.append(float((u.get("lusegrense") or "").strip()))
        except ValueError:
            grenser.append(None)

    maks = max(v for v in verdier if v is not None)
    tak, trinn = _grafskala(max([maks] + [g_ for g_ in grenser
                                          if g_ is not None]))
    n = len(serie)

    # PLASSEN ER UKA, ikke radnummeret (08.10.2026).
    #
    # Fram til i dag sto rad nummer i på plass i. En uke lokaliteten ikke
    # står i hos kilden har ingen rad, så hullet ble TRYKKET SAMMEN: 24615
    # mangler 211 uker fra 2012-11-12 til 2016-11-21, og fire år forsvant
    # fra tidsaksen uten at noe på grafen viste det. 12020 og 12023
    # mangler 243. Se `manglende_uker()`.
    #
    # Nå står hver rad på uka den gjelder, talt fra første rad, og aksen
    # har plass til ALLE ukene i spennet. Et hull er et tomrom med samme
    # bredde som ukene det dekker — samme tegn som en uke uten tall, og
    # det er riktig: i begge tilfeller har kilden ikke sagt noe.
    #
    # En serie som ikke er én rad per uke i stigende rekkefølge, kaster.
    # `_lusserie()` lover det, og en graf som gjettet ville tegnet to
    # søyler oppå hverandre uten å si fra.
    forste = dt.date.fromisoformat(serie[0]["dato"])
    plass = [(dt.date.fromisoformat(u["dato"]) - forste).days // 7
             for u in serie]
    if any(b <= a for a, b in zip(plass, plass[1:])):
        raise ValueError("lusegraf: serien er ikke én rad per uke i "
                         "stigende rekkefølge")
    ukeplasser = plass[-1] + 1
    v, h, o, u_ = (GRAF_MARG["v"], GRAF_MARG["h"],
                   GRAF_MARG["o"], GRAF_MARG["u"])
    plott_b = GRAF_BREDDE - v - h
    plott_h = GRAF_HOYDE - o - u_ - GRAF_BRAKK_HOYDE
    bunn = o + plott_h

    # SØYLEBREDDEN ER PLASSEN PER UKE, uten mellomrom. 764 uker på 840
    # piksler er 1,1 px per uke, og et mellomrom der ville betydd at
    # halvparten av søylene forsvant. Tettheten ER formen: en serie på
    # femten år skal leses som en tidsakse, ikke som femten år med
    # tellbare pinner.
    steg = plott_b / ukeplasser
    bredde = round(max(steg, 0.8), 2)

    def x(i: int) -> float:
        return round(v + steg * i, 1)

    def y(verdi: float) -> float:
        return round(o + plott_h * (1 - verdi / tak), 1)

    # EN MÅLT NULL ER EN SØYLE, ikke ingenting.
    #
    # `y(0)` er nullinja, og en `<rect>` med høyde 0 tegner ikke en
    # piksel. Følgen ville vært at «telt til null lus» og «ingen telling
    # denne uka» så nøyaktig like ut — som er den ENE feilen denne
    # grafen ikke får gjøre, og som hele tabellen under står og roper om.
    #
    # MÅLT på OTERNESET: 124 av 558 uker med tall har verdien 0. Uten
    # gulvet ville nesten hver fjerde måling vært usynlig.
    #
    # Gulvet er 1,2 px — en hårstrek som ligger på nullinja og ikke kan
    # forveksles med en verdi. At den betyr NULL og ikke «litt», står i
    # bildeteksten.
    gulv = 1.2
    soyler = [{"x": x(plass[i]), "y": round(min(y(verdi), bunn - gulv), 1),
               "h": round(max(bunn - y(verdi), gulv), 1),
               "uke": f"{serie[i]['iso_aar']} uke {serie[i]['iso_uke']}",
               "verdi": visningsord.tall(verdi),
               "over": _over_grensen(serie[i].get("voksne_hunnlus") or "",
                                     serie[i].get("lusegrense") or "") is True}
              for i, verdi in enumerate(verdier) if verdi is not None]

    # Brakkleggingsstrekkene, slått sammen til sammenhengende bånd. Et
    # bånd BRYTES av et hull: en uke lokaliteten ikke står i hos kilden,
    # vet vi ikke om den var brakklagt.
    baand, start, forrige = [], None, None
    for i, rad in enumerate(serie + [{}]):
        her = plass[i] if i < n else None
        er_brakk = str(rad.get("brakklagt")) == "True"
        if start is not None and (not er_brakk or her != forrige + 1):
            baand.append({"x": x(start),
                          "bredde": round(max(x(forrige + 1) - x(start),
                                              1.0), 1)})
            start = None
        if er_brakk and start is None:
            start = her
        forrige = her

    # Grenselinja som én SVG-sti. Et løp er sammenhengende uker med en
    # grense; innenfor løpet er det vannrett for hver uke og loddrett der
    # verdien skifter. Et nytt løp begynner med en ny `M`.
    # Bare knekkpunktene skrives: 767 uker med samme grense er én `H`,
    # ikke 767.
    sti: list[str] = []
    forrige_plass = None
    forrige_y = None
    for i, g_ in enumerate(grenser + [None]):
        her = plass[i] if g_ is not None else None
        if forrige_plass is not None and (her is None
                                          or her != forrige_plass + 1):
            sti.append(f"H{x(forrige_plass + 1)}")      # løpet slutter
            forrige_plass = None
        if g_ is None:
            continue
        gy = y(g_)
        if forrige_plass is None:
            sti.append(f"M{x(her)} {gy}")
        elif gy != forrige_y:
            sti.append(f"H{x(her)} V{gy}")
        forrige_plass, forrige_y = her, gy
    med_grense = sum(1 for g_ in grenser if g_ is not None)
    grense = ({"d": " ".join(sti),
               "uker": med_grense,
               "uten": n - med_grense,
               "verdier": " og ".join(visningsord.tall(g_) for g_ in
                                      sorted({g_ for g_ in grenser
                                              if g_ is not None},
                                             reverse=True))}
              if med_grense else None)

    linjer = []
    verdi = 0.0
    while verdi <= tak + 1e-9:
        linjer.append({"y": y(verdi), "verdi": verdi,
                       "etikett": f"{verdi:.2f}".rstrip("0").rstrip(".")
                                  .replace(".", ",") or "0"})
        verdi += trinn

    # Årstallene. Ett merke per årsskifte, og bare hvert n-te når serien
    # er lang nok til at de ellers ville stått oppå hverandre. Tallet er
    # regnet av PLASSEN og ikke valgt: en etikett trenger ~34 px.
    #
    # Årsskiftet regnes av UKENE på aksen, ikke av radene: et årsskifte
    # inne i et hull skal stå der det er, ikke ved første rad etter.
    def isoaar(k: int) -> int:
        return (forste + dt.timedelta(weeks=k)).isocalendar()[0]

    aar = [{"x": x(k), "etikett": str(isoaar(k))}
           for k in range(1, ukeplasser) if isoaar(k) != isoaar(k - 1)]
    if aar:
        hver = max(1, math.ceil(len(aar) * 34 / plott_b))
        aar = aar[::hver]

    uten_tall = sum(1 for v_ in verdier if v_ is None)
    brakk = sum(1 for rad in serie if str(rad.get("brakklagt")) == "True")
    brakk_uten_tall = sum(1 for rad, v_ in zip(serie, verdier)
                          if v_ is None and str(rad.get("brakklagt")) == "True")
    return {
        "bredde": GRAF_BREDDE, "hoyde": GRAF_HOYDE,
        "plott_x": v, "plott_y": o,
        "plott_bredde": plott_b, "plott_hoyde": plott_h,
        "bunn": round(bunn, 1),
        "brakk_y": round(bunn + 2, 1),
        "brakk_hoyde": GRAF_BRAKK_HOYDE - 2,
        "soyler": soyler,
        # Søylene på eller over grensa — de som står i rust.
        "over": sum(1 for s in soyler if s["over"]),
        "soylebredde": bredde,
        "baand": baand,
        "grense": grense,
        "linjer": linjer,
        "aar": aar,
        "tak": tak,
        # Formateres HER og ikke i malen. `1.54` med punktum er engelsk,
        # og `visningsord.tall()` er det ene stedet nettstedet bestemmer
        # hvordan et tall ser ut på norsk.
        "maks": visningsord.tall(maks),
        "uker": n,
        # UKENE PÅ AKSEN, og de av dem lokaliteten ikke står i hos
        # kilden. `uker` er radene, som før: «N av M uker har tall»
        # handler om ukene kilden har uttalt seg om.
        "ukeplasser": ukeplasser,
        "mangler": ukeplasser - n,
        "uker_med_tall": n - uten_tall,
        "uten_tall": uten_tall,
        "brakklagt": brakk,
        "hull_forklart": brakk_uten_tall,
        "hull_uforklart": uten_tall - brakk_uten_tall,
        "nuller": sum(1 for v_ in verdier if v_ == 0),
        "fra": serie[0].get("dato", ""),
        "til": serie[-1].get("dato", ""),
    }


def _over_grensen(lus: str, grense: str) -> bool | None:
    """Er uka over tiltaksgrensa, regnet slik BarentsWatch regner?
    None når en av de to mangler.

    Lusetallet avrundes til to desimaler HALV OPP før det sammenlignes.
    MÅLT 09.10.2026 mot BarentsWatchs eget «Over lusegrense uke»: 409 118
    av 409 118 lokalitetsuker. Med Pythons `round()`, som gir 0,49 for
    0,495, er det tre avvik — alle 0,495 mot 0,5.
    """
    try:
        verdi = Decimal(lus.strip()).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return verdi >= Decimal(grense.strip())
    except (InvalidOperation, AttributeError):
        return None


def del_i_perioder(serie: list[dict]) -> list[list[dict]]:
    """Ukene i `serie` delt i produksjonsperioder, eldst først.

    En periode er sammenhengende uker der `brakklagt` er `False`. En uke
    BarentsWatch kaller brakklagt, eller en uke lokaliteten mangler i hos
    kilden, avslutter den. Se `produksjonsperioder()` for hvorfor.

    Ett sted, brukt av lokalitetssiden og av `unntaksanalyse`: to regler
    for hva en periode er, ville gitt to svar på samme spørsmål.
    """
    perioder: list[list[dict]] = []
    aapen: list[dict] | None = None
    for u in serie:
        if str(u.get("brakklagt")) != "False":
            aapen = None                    # brakk avslutter
            continue
        sammenheng = aapen is not None and (
            dt.date.fromisoformat(u["dato"])
            - dt.date.fromisoformat(aapen[-1]["dato"])).days == 7
        if not sammenheng:                  # første, eller etter et hull
            aapen = []
            perioder.append(aapen)
        aapen.append(u)
    return perioder


def produksjonsperioder(serie: list[dict], siste_dato: str) -> dict:
    """Uker over tiltaksgrensa i inneværende og forrige produksjonsperiode.

    ## Periodegrensa er BarentsWatchs, ikke vår

    En periode er sammenhengende uker der `brakklagt` er `False` — altså
    der BarentsWatch IKKE regner lokaliteten som «Trolig uten fisk».
    Feltet er deres slutning og ikke en innrapportert opplysning
    (docs/MALING-FUNN-OKTOBER.md F4.2), og siden sier det. Vi bygger ikke
    over korte brakkavbrudd og trimmer ikke kanter, slik analysen i F4
    gjør: en uke BarentsWatch kaller brakklagt, avslutter perioden.

    En uke lokaliteten MANGLER i hos kilden avslutter den også. Vi vet
    ikke hva som skjedde den uka, og å trekke perioden over hullet ville
    vært en påstand om at fisken sto der.

    INNEVÆRENDE finnes bare når perioden når den siste uka vi har fra
    BarentsWatch (`siste_dato`). Er lokaliteten brakklagt nå, eller borte
    fra kilden, er det ingen inneværende periode — bare en forrige.

    Per periode: første og siste uke, antall uker, uker med lusetall,
    uker over grensa, og uker med tall men uten grense hos kilden. De
    siste telles for seg: en uke uten grense er ikke en uke under den.
    """
    perioder = del_i_perioder(serie)

    def tall_for(p: list[dict]) -> dict:
        med_tall = [u for u in p if (u.get("voksne_hunnlus") or "").strip()]
        over = [u for u in med_tall
                if _over_grensen(u["voksne_hunnlus"], u.get("lusegrense") or "")]
        uten_grense = [u for u in med_tall
                       if _over_grensen(u["voksne_hunnlus"],
                                        u.get("lusegrense") or "") is None]
        return {"fra": p[0]["dato"], "til": p[-1]["dato"],
                "uker": len(p), "med_tall": len(med_tall),
                "over": len(over), "uten_grense": len(uten_grense)}

    innevaerende = forrige = None
    if perioder:
        if perioder[-1][-1]["dato"] == siste_dato:
            innevaerende = tall_for(perioder[-1])
            if len(perioder) > 1:
                forrige = tall_for(perioder[-2])
        else:
            forrige = tall_for(perioder[-1])
    return {"innevaerende": innevaerende, "forrige": forrige}


# ------------------------------------------------- DE TO HISTORIKKENE
#
# En lokalitetsside har to slags fortid, og de er IKKE det samme:
#
#   OBSERVERT AV KYSTLOGGEN   changeloggen. «Vi så at feltet endret seg
#                             denne mandagen.» Datoen er VÅR, og den
#                             sier bare når vi SÅ det — registeret
#                             oppgir ikke når det gjorde det.
#   OPPGITT AV REGISTERET     historikk kilden selv fører:
#                             journalførte overføringer, tildelings-
#                             datoer, første klarering. Datoen er
#                             KILDENS, og den gjelder en hendelse i
#                             verden.
#
# De skal aldri flettes i én tidslinje uten merking. En flettet liste
# ville latt «17. juni 2024: overført til X» (kildens påstand om noe som
# skjedde) stå ved siden av «14. september 2026: eier_navn endret»
# (vår påstand om når vi så det), og en leser ville lest begge som
# hendelser med dato. Den første er det; den andre er en observasjon.
#
# Derfor to lister, to overskrifter, to forklaringer og to visuelle
# former. Se avvik 4 i oppdraget og docs/design/.


def _observert_historikk(endringer: list[dict], dekning_fra: list[dict],
                         felles: Felles | None) -> list[dict]:
    """Changeloggen som en loddrett tidslinje, nyest først.

    SISTE POST ER «FØRSTE ØYEBLIKKSBILDE», og den er ikke pynt: uten den
    kan en leser ikke se forskjell på «ingenting har skjedd» og «vi
    begynte å se etter i forrige uke». Datoen er den eldste
    innsamlingsdatoen for kildene siden bygger på — ikke i dag, og ikke
    en kildes egen historikk.
    """
    poster = [{
        "dato": e["dato"],
        "uke": visningsord.isouke(e["dato"]),
        "datoslag": e["datoslag"],
        "datoord": e["datoord"],
        "etikett": e["etikett"],
        "felt": e["felt"],
        "fra": e["fra"],
        "til": e["til"],
        # EN TOM VERDI MERKES IKKE MED KILDENS FELTNAVN. Se
        # `feltmerke()` og målingen der.
        "fra_felt": feltmerke(e["fra"], e["felt"]),
        "til_felt": feltmerke(e["til"], e["felt"]),
        "differanse": e.get("differanse", []),
        "kildefelt": e.get("kildefelt", ""),
        "entity_id": e.get("entity_id", ""),
        "forrige_dato": e.get("forrige_dato", ""),
        "gjelder": e["gjelder"],
        "kilde": e["kilde"],
        "forste": False,
        # VESENTLIG ELLER TEKNISK, og registerets forklaring. Se
        # `_lokalitetsendringer()`. Rader uten klasse er vesentlige: det
        # er standarden i `vesentlighet` også.
        "klasse": e.get("klasse", vesentlighet.VESENTLIG),
        "forklaring": e.get("forklaring", ""),
        # FELT SOM ER SLÅTT SAMMEN til én hendelse. Se
        # `_samle_oppforinger()`.
        "samlet": e.get("samlet", 0),
        "endringstype": e.get("endringstype", ""),
    } for e in endringer]
    # SAMME SAMMENSLÅING SOM PÅ ENDRINGSSIDENE, fra det samme ene
    # stedet: tidslinja og ukestabellen skal ikke svare ulikt på hva som
    # skjedde med den samme tillatelsen.
    poster = slaa_sammen_trukne(poster)

    fra = min((d["fra"] for d in dekning_fra), default="")
    if fra:
        poster.append({
            "dato": fra,
            "uke": visningsord.isouke(fra),
            "etikett": "Første øyeblikksbilde",
            # DEN FØRSTE POSTEN ER EN OBSERVASJON: dette er dagen vi
            # begynte å hente, ikke en periode noe handler om.
            "datoslag": "henting",
            "datoord": "Observert",
            "felt": "observed_at",
            "fra": "",
            "til": "",
            "fra_felt": VERDI_MANGLER_FELT,
            "til_felt": VERDI_MANGLER_FELT,
            "differanse": [],
            "kildefelt": "",
            "entity_id": "",
            "forrige_dato": "",
            "gjelder": "lokaliteten",
            "kilde": "",
            "forste": True,
            "klasse": vesentlighet.VESENTLIG,
            "forklaring": "",
            "samlet": 0,
            "endringstype": "",
            # HVILKE KILDER DATOEN GJELDER. Setningen på siden sier
            # «registerfeltene», og her står navnene den bygger på, så
            # de to ikke kan bli uenige.
            "dekker": visningsord.liste(sorted(d["kilde"]
                                               for d in dekning_fra)),
        })
    # KRONOLOGISK, og ikke «sist i lista».
    #
    # Posten ble lagt til til slutt, og lista er nyest først — det er
    # riktig så lenge ingen annen post er ELDRE. Sykdomsflaggene er
    # datert til UKA de gjelder for (se APNE-SPORSMAL punkt 2), og en
    # slik dato kan ligge før første øyeblikksbilde. Da sto «Første
    # øyeblikksbilde» over poster som er eldre enn den, og påsto at
    # ingenting før den finnes i loggen.
    poster.sort(key=lambda r: _omvendt(r["dato"]))
    return poster


def _oppgitt_historikk(a: dict, tillatelser: list[dict],
                       overforinger: list[dict],
                       former: dict | None = None) -> list[dict]:
    """Historikken KILDEN selv fører, eldst først.

    Tre slag, og alle tre er datoer registeret oppgir som en dato for
    noe som skjedde — ikke som en dato for da vi så noe:

      første klarering     `akvakultur.forste_klarering`
      tildeling            `eierskap.tildelt_tid`, med hvem den gikk til
      overføring           `eierskap_historikk.journal_dato`

    JOURNALDATOEN ER «SENEST DA», ikke «akkurat da». Forbeholdet står på
    hver rad i dataene og gjentas i forklaringen på siden framfor å
    pusses bort.
    """
    # NAVNET STÅR FOR SEG, og det er ikke en formatering.
    #
    # Første utkast satte «T-G-0008 tildelt til STRAUMEN HAVBRUK AS» i
    # ett felt. Publiseringsvaktens `FELTMERKE` fanger hele celleteksten
    # som ÉN verdi, og «T-G-0008 tildelt til STRAUMEN HAVBRUK AS» står
    # ikke i hvitelista — selskapet gjør. Vakten ville meldt hver eneste
    # tildelingspost som `ukjent_navn`, og en vakt som feiler feil blir
    # slått av (samme begrunnelse som `_celleverdi()`).
    #
    # `navn` og `navn_felt` er derfor egne nøkler, og malen merker dem
    # med kildens eget feltnavn. Da ser porten verdien den skal se.
    poster = []
    # 1 782 av 1 782 `forste_klarering` faller på en annen dato i
    # Europe/Oslo enn i UTC. Se `visningsord.oslodato()`.
    klarert = visningsord.oslodato(a.get("forste_klarering"))
    if klarert:
        poster.append({
            "dato": klarert, "slag": "Første klarering",
            "hva": "Lokaliteten klarert av Fiskeridirektoratet",
            "navn": "", "navn_felt": "",
            "orgnr": "", "navn_er_i_dag": False,
            "kilde": "akvakultur", "felt": "forste_klarering",
            "presisjon": "dato oppgitt av registeret",
        })
    for till in tillatelser:
        if till["tildelt_dato"]:
            # NUMMERET ER IDENTITETEN, NAVNET ER «I DAG».
            #
            # MÅLT 24.09.2026: `tildelt_navn` er pub-aquas
            # `grantInformation.legalEntityName`, og det er DAGENS navn
            # på organisasjonsnummeret — ikke navnet ved tildelingen.
            # For 1 452 av 1 452 tillatelser der nummeret også står i
            # vårt Enhetsregister-uttrekk, er navnet identisk med dagens
            # `navn` der; for 1 463 av 1 463 som aldri har skiftet hender,
            # er det identisk med dagens `eier_navn`. Null avvik, også
            # for tildelinger fra 1995.
            #
            # «T-G-0008 tildelt til MOWI ASA» i 1995 leses som at
            # selskapet het det den gangen. Nummeret står derfor først,
            # og navnet merkes «i dag» — i sin EGEN celleverdi, ikke
            # sammensatt med nummeret: porten slår celleverdien opp i
            # hvitelista, og en sammensatt streng står ikke der.
            poster.append({
                "dato": till["tildelt_dato"],
                "slag": "Tillatelse tildelt",
                "hva": f"{till['nr']} tildelt",
                "navn": till["tildelt_navn"],
                "navn_felt": till.get("tildelt_felt", "tildelt_navn"),
                "orgnr": till.get("tildelt_orgnr", ""),
                # Vår tekst er ikke «dagens navn» på noe nummer.
                "navn_er_i_dag": (till.get("tildelt_felt")
                                  != publiseringsvakt.SKJULT_NAVN_FELT),
                "kilde": "eierskap", "felt": "tildelt_tid",
                "presisjon": "dato oppgitt av registeret",
            })
    for o in overforinger:
        if o["dato"]:
            navn, felt, _orgnr = _navn_eller_skjult(
                o["mottaker_navn"], "mottaker_navn",
                o.get("mottaker_orgnr", ""), former)
            poster.append({
                "dato": o["dato"],
                "slag": "Overføring journalført",
                "hva": f"{o['tillatelse']} overført",
                "navn": navn,
                "navn_felt": felt,
                "orgnr": "", "navn_er_i_dag": False,
                "kilde": "eierskap_historikk", "felt": "journal_dato",
                "presisjon": "journalført senest denne datoen",
            })
    poster.sort(key=lambda r: (r["dato"], r["slag"]))
    return poster


def har_selskapsside(orgnr: str, eierskap: dict[str, dict[str, str]]) -> bool:
    """Får dette organisasjonsnummeret en `/selskap/<orgnr>/`-side?

    Leses av EIERSKAPSRAMMA og ikke av en `Felles`, slik at begge veiene
    inn i `bygg_lokalitet()` svarer det samme. Fram til 22.09.2026 tok
    `_lokalitetens_selskap()` en `Felles`, og enkeltkjøringen — som
    ikke har en — lenket derfor ikke til selskapet i det hele tatt.

    To vilkår, og begge er de samme som `skriv_alle()` bruker:
    selskapet må eie minst én tillatelse, og kilden må ikke
    klassifisere det som en person. Det andre er ikke en formalitet:
    et URL-rom er en liste over hvem som finnes, selv om hver side
    skulle være tom. Se `personeier()` og regel 3.
    """
    from sources.eierskap import er_person

    mine = [d for d in eierskap.values()
            if (d.get("eier_orgnr") or "").strip() == orgnr]
    return bool(mine) and not any(er_person(d.get("eier_type")) for d in mine)


def _lokalitetens_selskap(mine_till: dict, overforinger: list[dict],
                          eierskap: dict[str, dict[str, str]]) -> dict:
    """Hvem som eier tillatelsene på lokaliteten nå, og siden når.

    ## Hvorfor «selskapet» kan være flere, og hvorfor det sies

    En lokalitet kan ha tillatelser fra ulike innehavere. Designet har
    ett felt for «Selskap»; dataene har ett til flere. Feltet bærer
    derfor ANTALLET når det er mer enn ett, og lenker til det som eier
    flest — med de andre nevnt. Å vise bare det første ville vært et
    valg tatt av dict-rekkefølgen.

    ## «Siden» er den SENESTE overføringen til det selskapet

    Og det er en journaldato, altså «senest da». Finnes ingen
    overføring, er svaret tomt og ikke en gjetning — vi vet da at
    selskapet eier tillatelsen, ikke når det begynte.
    """
    # PERSONFORMEN SPØRRES OM HER OGSÅ, og det er ikke dobbeltarbeid.
    #
    # `_eierrad()` gjør det for tabellraden. Denne funksjonen er en NY
    # vei til det samme navnet — overskriftens «Innehaver»-felt, som kom
    # 22.09.2026 — og en ny vei uten spørsmålet er en ny lekkasje.
    #
    # MÅLT: porten stoppet publiseringen på lokalitet 11593, der
    # navnet til innehaveren av H-FJ-0018 — en personform — sto i
    # overskriften mens tabellraden under sa «eieren er en
    # personform». To steder som skal
    # si det samme om hvem vi ikke navngir, er formen F6 og F7 hadde —
    # og her er prisen et navngitt menneske på en offentlig side.
    from sources.eierskap import er_person

    per_eier: dict[str, int] = defaultdict(int)
    navn_av: dict[str, str] = {}
    person: set[str] = set()
    for d in mine_till.values():
        orgnr = (d.get("eier_orgnr") or "").strip()
        if not orgnr:
            continue
        per_eier[orgnr] += 1
        if er_person(d.get("eier_type")):
            person.add(orgnr)
        else:
            navn_av[orgnr] = (d.get("eier_navn") or "").strip()
    if not per_eier:
        return {"navn": "", "orgnr": "", "url": "", "siden": "",
                "antall": 0, "flere": 0, "personform": False}

    orgnr = max(per_eier, key=lambda o: (per_eier[o], o))
    if orgnr in person:
        # NAVNET VISES IKKE, og raden forsvinner ikke. Samme tekst som
        # tabellen under bruker, fra det samme ene stedet.
        return {"navn": EIER_PERSONFORM, "orgnr": "", "url": "",
                "siden": "", "antall": len(per_eier),
                "flere": len(per_eier) - 1, "personform": True}

    siden = max((o["dato"] for o in overforinger
                 if (o.get("mottaker_orgnr") or "").strip() == orgnr), default="")
    har_side = har_selskapsside(orgnr, eierskap)
    return {
        "navn": navn_av.get(orgnr, ""),
        "orgnr": orgnr,
        "url": f"/selskap/{orgnr}/" if har_side else "",
        "siden": siden,
        "antall": len(per_eier),
        "flere": len(per_eier) - 1,
        "personform": False,
    }


def _biolagstripe(serie: list[dict], alle_uker: list[str]) -> dict | None:
    """Ukestripa: står det fisk på lokaliteten, uke for uke vi observerte.

    ## Dette erstatter biomassegrafen, og det er et avvik med en grunn

    Overleveringen tegner månedlige biomassesøyler på lokalitetssiden.
    Fiskeridirektoratets biomassetall er per PRODUKSJONSOMRÅDE, ikke per
    lokalitet — se docs/KILDE-BIOMASSE.md — og mengdetallene per
    lokalitet ligger i biomassedatabasen etter
    akvakulturdriftsforskriften § 44, som er børssensitiv og ikke
    offentlig. Grafen kan derfor ikke tegnes, og den er flyttet dit
    tallene faktisk finnes: områdesiden.

    Det vi HAR per lokalitet er ja/nei. Stripa viser det, og bare for de
    ukene vi faktisk har observert — to i dag. Et rutenett med 52 ruter
    der to er fylt ville påstått at vi vet noe om de femti andre.

    ## Hver rute bærer `siste_rapport`

    Kilden sier uttrykkelig at `observed_at` er hentetidspunktet vårt og
    at `siste_rapport` er måneden påstanden gjelder for. De kan ligge år
    fra hverandre. En rute uten den datoen ville sagt «fisk i uke 37»,
    og det er ikke det kilden påstår.
    """
    if not serie:
        return None
    ruter = []
    for uke in serie:
        har = (uke.get("har_fisk") or "").strip()
        ruter.append({
            "dato": uke["dato"],
            "uke": visningsord.uke(uke["dato"]),
            "har_fisk": har,
            "ja": har.lower() in ("ja", "true"),
            "arter": uke.get("arter_tilstede", ""),
            "siste_rapport": uke.get("siste_rapport", ""),
            "status": uke.get("lokalitet_status", ""),
            "tittel": (f"{visningsord.uke(uke['dato'])}: "
                       f"{'fisk til stede' if har.lower() in ('ja', 'true') else 'ingen fisk'}"
                       + (f", siste månedsrapport {uke.get('siste_rapport', '')}"
                          if uke.get("siste_rapport") else "")),
        })
    return {
        "ruter": ruter,
        "observerte_uker": len(ruter),
        "alle_uker": len(alle_uker),
        "med_fisk": sum(1 for r in ruter if r["ja"]),
        "siste_rapport": ruter[-1]["siste_rapport"],
        "arter": ruter[-1]["arter"],
        # DEN NYESTE UKA I LAGET, for alle lokaliteter. Står lokaliteten
        # ikke i den, er siste rute en gammel påstand — se
        # `lokalitetssammendrag()`.
        "siste_uke": alle_uker[-1] if alle_uker else "",
    }


# ---------------------------------------------------- oppsummeringen
#
# ÉN SETNING ØVERST på lokalitetssiden, satt sammen av leddene under.
# Hvert ledd er en målt opplysning som også står lenger ned på siden —
# setningen er en annen vei til dem, aldri den eneste. Mangler et ledd
# dataene, utelates det; det gjettes ikke. Se docs/design/BRIEF.md.
#
# Et ledd er en liste av biter: ("tekst", s), ("lenke", url, s) eller
# ("tid", iso, s). Datoene må være `<time datetime>` (markupkontrakten),
# og det kan bare malen skrive.

SAMMENDRAG_UKER = 12


def _fiskeledd(biolag: dict | None) -> list[tuple] | None:
    """«Fisk til stede siden uke 40, 2026», eller tilsvarende.

    BARE NÅR LOKALITETEN STÅR I DEN NYESTE UKA AV LAGET. Laget dekker
    lokaliteter med innsendt månedsrapport; en lokalitet som har falt ut,
    har ingen påstand om i dag, og den forrige er ikke en.

    «SIDEN» ER UKA VI FØRST SÅ DEN NYE TILSTANDEN, etter en observasjon
    av den motsatte. Uten et slikt skifte i serien vet vi ikke når
    tilstanden begynte, og da står månedsrapporten kilden oppgir i
    stedet — den er det kilden selv sier at påstanden gjelder for.
    """
    if not biolag or not biolag.get("ruter"):
        return None
    ruter = biolag["ruter"]
    siste = ruter[-1]
    if not siste.get("har_fisk") or siste["dato"] != biolag.get("siste_uke"):
        return None
    ledd: list[tuple] = [("tekst", "Fisk til stede" if siste["ja"]
                          else "Ingen fisk til stede")]
    skifte = next((ruter[i] for i in range(len(ruter) - 1, 0, -1)
                   if ruter[i]["ja"] != ruter[i - 1]["ja"]
                   and ruter[i - 1].get("har_fisk")), None)
    if skifte:
        ledd += [("tekst", " siden "),
                 ("tid", skifte["dato"], visningsord.uke(skifte["dato"]))]
    elif siste.get("siste_rapport"):
        ledd += [("tekst", " ifølge månedsrapporten for "),
                 ("tid", siste["siste_rapport"][:7],
                  visningsord.maaned(siste["siste_rapport"]))]
    return ledd


def _eierledd(selskap: dict) -> list[tuple] | None:
    """«eid av X siden 2022». Datoen er den siste overføringen til
    selskapet som er journalført — samme dato som faktalista viser.

    INGEN PERSONFORM og intet navn vi ikke har. Regel 3.

    Navnet står i menneskelig form — «Salmar Oppdrett AS» — fordi
    setningen er en ingress og ikke en registertabell. Den rå verdien
    står i registerfeltene. Se `visningsord.selskapsnavn()`."""
    if not selskap or selskap.get("personform") or not selskap.get("navn"):
        return None
    navn = visningsord.selskapsnavn(selskap["navn"])
    ledd: list[tuple] = [("tekst", "eid av "),
                         ("lenke", selskap["url"], navn) if selskap.get("url")
                         else ("tekst", navn)]
    if selskap.get("flere"):
        ledd.append(("tekst", f" og {visningsord.antall(selskap['flere'], 'innehaver', 'innehavere')} til"))
    elif selskap.get("siden"):
        ledd += [("tekst", " siden "),
                 ("tid", selskap["siden"], selskap["siden"][:4])]
    return ledd


def endringsvindu(referanse: str, dekning_fra: list[dict], uker: int
                  ) -> dict | None:
    """Vinduet «siste N uker», avgrenset av vår egen dekning.

    Har vi hentet i færre enn N uker, ville «0 endringer siste N uker»
    påstått at vi så etter i uker vi ikke så etter. Da begynner vinduet
    på den SENESTE av registerkildenes første henting, så hver kilde som
    teller har vært med hele vinduet, og `hele` er usann.

    REFERANSEN ER DATAENES, ikke klokka: datoen til øyeblikksbildet
    siden er bygget av. CLAUDE.md 1b.

        {"fra": iso (eksklusiv), "til": iso (inklusiv), "hele": bool,
         "uker": N}
    """
    try:
        ref = dt.date.fromisoformat(referanse[:10])
    except ValueError:
        return None
    dekket = max((d["fra"] for d in dekning_fra), default="")
    if not dekket:
        return None
    start = (ref - dt.timedelta(weeks=uker)).isoformat()
    hele = dekket <= start
    return {"fra": start if hele else dekket, "til": ref.isoformat(),
            "hele": hele, "uker": uker}


def vesentlige_i_vinduet(poster: list[dict], vindu: dict) -> list[dict]:
    """Tidslinjepostene som er vesentlige og ligger i vinduet. «Første
    øyeblikksbilde» er ikke en endring."""
    return [p for p in poster
            if not p.get("forste")
            and p.get("klasse", vesentlighet.VESENTLIG) == vesentlighet.VESENTLIG
            and vindu["fra"] < str(p.get("dato", ""))[:10] <= vindu["til"]]


def _endringsledd(observert: list[dict], dekning_fra: list[dict],
                  referanse: str) -> list[tuple] | None:
    """«2 vesentlige endringer siste 12 uker», eller «… siden <dato>»
    når vi har hentet i kortere tid. Se `endringsvindu()`."""
    vindu = endringsvindu(referanse, dekning_fra, SAMMENDRAG_UKER)
    if not vindu:
        return None
    n = len(vesentlige_i_vinduet(observert, vindu))
    tekst = (visningsord.antall(n, "vesentlig endring", "vesentlige endringer")
             if n else "ingen vesentlige endringer")
    if vindu["hele"]:
        return [("tekst", f"{tekst} siste {SAMMENDRAG_UKER} uker")]
    return [("tekst", f"{tekst} siden "),
            ("tid", vindu["fra"], visningsord.dato(vindu["fra"]))]


def lokalitetssammendrag(lok: dict) -> list[list[tuple]]:
    """Leddene i oppsummeringssetningen, i rekkefølge. Tom liste: ingen
    setning."""
    ledd = [
        _fiskeledd(lok.get("biolag")),
        _eierledd(lok.get("selskap") or {}),
        _endringsledd(lok.get("observert") or [], lok.get("dekning_fra") or [],
                      max(lok.get("akva_dato") or "",
                          lok.get("eierskap_dato") or "")),
    ]
    ledd = [l for l in ledd if l]
    # STOR FORBOKSTAV på det første leddet, hvilket det enn er.
    if ledd and ledd[0][0][0] == "tekst":
        s = ledd[0][0][1]
        ledd[0][0] = ("tekst", s[:1].upper() + s[1:])
    return ledd


# NABOLISTA, bygget én gang per `Felles`.
#
# Den er den samme for alle 1 782 sidene, og et gjennomløp av hele
# uttrekket per side er 1 782 gjennomløp av det samme. Nøkkelen er
# `id()` fordi `Felles` ikke kan hashes — den bærer polars-rammer — og
# i en batch finnes det én.
_NABOER: dict[int, tuple] = {}


def _naboer(loknr: str, akva: dict, nokkel: int) -> list[tuple]:
    """Naboene kartet skal tegne: alle ANDRE lokaliteter med posisjon.

    Selve lokaliteten er ikke med — den har sin egen markør, og en
    prikk oppå den ville sett ut som to anlegg. Utsnittet filtreres i
    `kart.posisjonskart()`, som er der rammen er kjent.

    `akva` er det SAMME uttrekket siden ellers bygges av, enten det kom
    fra `Felles` eller ble lest av enkeltveien. To veier til samme side
    som kunne svare ulikt er formen F6 og F7 hadde, og her ville
    følgen vært et kart med naboer i batch og uten dem alene.
    """
    if nokkel not in _NABOER:
        _NABOER[nokkel] = tuple(
            (nr, visningsord.tittelform(d.get("navn", "")),
             d.get("breddegrad", ""), d.get("lengdegrad", ""))
            for nr, d in akva.items()
            if d.get("breddegrad") and d.get("lengdegrad"))
    return [t for t in _NABOER[nokkel] if t[0] != loknr]


def _lus_fravaer(a: dict) -> str:
    """Hva registeret selv sier som forklarer at lusetallene mangler.

    «Det er ventet for anlegg som ikke har laksefisk» sto på HVER
    lokalitet som ikke finnes hos BarentsWatch, uansett hva registeret
    oppgir. Moltustranda (12325) er oppført med laks og fikk setningen
    likevel: grunnen der er at anlegget ligger på land.

    Tre svar, og bare de to første er en forklaring:

        "uten_laks"   arter har ikke `SALMON`
        "paa_land"    plasseringstype er `Onshore`
        ""            laks, ikke på land — registeret forklarer ikke
                      fraværet, og siden skal ikke gjøre det for det

    Ordene er kodene, ikke «laksefisk»: `SALMON` er «laks», og hvilke
    arter koden omfatter er ikke dokumentert (se `visningsord`).
    """
    arter = (a.get("arter") or "").split(";")
    if "SALMON" not in {x.strip() for x in arter}:
        return "uten_laks"
    if (a.get("plasseringstype") or "").strip() == "Onshore":
        return "paa_land"
    return ""


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
                         f"akvakultur-øyeblikksbildet {akva_dato}")
    a = akva[loknr]

    if felles is None:
        eierskap_dato, eierskap = _siste("eierskap")
        mine_till = {
            nr: d for nr, d in eierskap.items()
            if loknr in [x.strip() for x in (d.get("lokaliteter") or "").split(";")]
        }
        ovf = list(_overforinger().values())
        former = publiseringsvakt.formkart(
            _siste("enhetsregisteret")[1], eierskap, ovf)
        serie = _lusserie(loknr)
        endringer, maaleserie_rader, sist_endret = _endringer(
            loknr, sorted(mine_till))
        oppgitt = _liste(a.get("tillatelser"))
        uten_eier = _uten_eier(oppgitt, eierskap)
    else:
        eierskap_dato, eierskap = felles.eierskap_dato, felles.eierskap
        mine_till = {nr: eierskap[nr] for nr in
                     felles.tillatelser_per_lokalitet.get(loknr, ())}
        ovf = [o for nr in mine_till
               for o in felles.overforinger_per_tillatelse.get(nr, ())]
        former = felles.former
        serie = felles.lusserier.get(loknr, [])
        endringer, maaleserie_rader, sist_endret = _endringer_av_indeks(
            loknr, sorted(mine_till), felles)
        oppgitt = _liste(a.get("tillatelser"))
        uten_eier = _uten_eier(oppgitt, eierskap)

    # UKESNAPSHOTENE FOR LUSETALL, slått opp ÉN gang. Antallet står på
    # siden og den nyeste uka i filnavnet; to oppslag kunne svart ulikt.
    lusedatoer = (felles.lusetall_snapshots if felles
                  else snapshot.datoer("lusetall"))
    lus_versjon = _ukeslug(lusedatoer[-1]) if lusedatoer else ""

    overforinger = sorted(
        (o for o in ovf if o.get("tillatelse_nr") in mine_till),
        key=lambda o: (o.get("journal_dato", ""), o.get("tillatelse_nr", "")),
    )
    overforingsrader = [
        {
            "dato": o.get("journal_dato", ""),
            "tillatelse": o.get("tillatelse_nr", ""),
            "mottaker_navn": o.get("mottaker_navn", ""),
            "mottaker_orgnr": o.get("mottaker_orgnr", ""),
            "rekkefolge": o.get("rekkefolge", ""),
        }
        for o in overforinger
    ]
    tillatelsesrader = _tillatelsesrader(mine_till, uten_eier, former)
    dekning = felles.dekning_fra if felles else _dekning_fra()

    lok = {
        "loknr": loknr,
        "navn": a.get("navn", ""),
        # REGISTERETS VERSALER GJORT OM TIL TITTELFORM, for H1.
        # «OTERNESET» er ikke en opplysning om navnet — det er en
        # egenskap ved registerets inntastingsfelt. Originalen står
        # uendret i `navn` og i registerfelt-tabellen på samme side, og
        # det er den som er siterbar. Regelen og dens grense står i
        # `visningsord.tittelform`.
        "tittelnavn": visningsord.tittelform(a.get("navn", "")),
        "kommune": a.get("kommune", ""),
        "fylke": a.get("fylke", ""),
        "po_kode": a.get("prodomraade_kode", ""),
        "po_navn": a.get("prodomraade_navn", ""),
        "breddegrad": a.get("breddegrad", ""),
        "lengdegrad": a.get("lengdegrad", ""),
        "akva_dato": akva_dato,
        # NÅR VI HENTET, ikke hva raden gjelder for. Proveniens­linja i
        # bunnteksten oppgir begge — CLAUDE.md 1b-7.
        "akva_hentet": (felles.akva_hentet if felles else _hentet("akvakultur")),
        "eierskap_dato": eierskap_dato,
        # Sortert alfabetisk og ikke i kildens rekkefølge: kildens
        # rekkefølge er en tilfeldighet i et JSON-svar, og en tabell som
        # stokker om på seg selv mellom to kjøringer er en tabell ingen
        # kan diffe.
        # TRE ledd per rad, ikke to: kildens feltnavn, etiketten et
        # menneske leser, og verdien oversatt. Feltnavnet MÅ bli med —
        # det er `data-felt`, altså markupkontrakten, og det er det
        # publiseringsvakten leser. Etiketten er bare for øyet.
        # FIRE LEDD per rad, ikke tre: kildens feltnavn (til
        # `data-felt`), etiketten et menneske leser, verdien oversatt,
        # og NÅR VI SIST SÅ FELTET ENDRE SEG.
        #
        # Den fjerde er `observed_at` fra changeloggen og ikke en dato
        # registeret oppgir. Kolonnen heter derfor «Sist observert» og
        # ikke «Sist endret» i malen — registeret sier ikke når det
        # gjorde endringen, og en kolonne som påsto det ville vært
        # nøyaktig den forvekslingen CLAUDE.md 1b handler om.
        # FEMTE LEDD ER FARGEKLASSEN. Cella har `data-felt` og får
        # derfor ::before-ruta fra stilarket, men fyllet kommer av
        # `lys-*`-klassen — og uten den sto ruta tom i BEGGE moduser,
        # ved siden av ordet «gul». En tom rute ved siden av et fargeord
        # leses som at fargen mangler.
        "register": [(f, visningsord.felt(f), visningsord.verdi(f, v),
                      sist_endret.get((loknr, f), ""),
                      FARGE_KLASSE.get(_fargekode(str(v).strip().lower()), ""))
                     for f, v in sorted(a.items())],
        # KJENTE og UGJORTE REDE FOR i SAMME tabell, i nummerrekkefølge.
        # Regelen og målingen står i docs/REGEL-UENIGE-KILDER.md: en
        # lokalitet der vi ikke vet hvem som eier tillatelsene skal si
        # det, ikke vise en tom tabell.
        "tillatelser": tillatelsesrader,
        "tillatelser_oppgitt": len(oppgitt),
        "tillatelser_uten_eier": len(uten_eier),
        # TILLATELSER DER REGISTERET OPPGIR KAPASITET 0. «0 stykk» i en
        # tabellcelle, uten et ord, leses som en feil hos oss. Malen sier
        # hva det er — registerets verdi — og stiller den ved siden av
        # lokalitetens egen kapasitet. Den tolker den ikke.
        "tillatelser_null_kapasitet": sum(
            1 for r in tillatelsesrader
            if _er_null((eierskap.get(r["nr"]) or {}).get("kapasitet"))),
        # Teksten sendes INN og står ikke i malen: to steder som skal si
        # det samme om hva vi ikke vet, er formen F6 og F7 hadde.
        "eier_ukjent": EIER_UKJENT,
        "overforinger": overforingsrader,
        "lus": til_visning(list(reversed(serie[-LUSEUKER:]))),
        "lus_fra": serie[0]["dato"] if serie else "",
        "lus_til": serie[-1]["dato"] if serie else "",
        "lus_uker": len(serie),
        # UKENE SOM MANGLER mellom første og siste rad, og setningen som
        # navngir dem. `lus_uker` + antallet her = ukesnapshotene i
        # spennet. Se `manglende_uker()`.
        "lus_mangler": manglende_uker(serie, lusedatoer),
        "lus_mangler_tekst": manglende_tekst(
            manglende_uker(serie, lusedatoer)),
        # Hvor mange ukesnapshots vi HAR. Uten det kan en side med null
        # uker ikke skille «vi har ikke sett etter» fra «vi har sett i
        # 764 uker og ikke funnet den».
        "lusetall_snapshots": len(lusedatoer),
        # HVA DATAENE SIER OM HVORFOR den mangler. Se `_lus_fravaer()`.
        "lus_fravaer": _lus_fravaer(a),
        # Telles her og skrives ikke inn i malen for hånd. Et tall i en
        # mal er et tall som ikke oppdateres når dataene gjør det, og da
        # er siden usann neste uke uten at noen rørte den.
        "lus_uten_tall": sum(1 for u in serie if u["voksne_hunnlus"] == ""),
        # UKER MED ET TALL. Null betyr at lokaliteten aldri har hatt et
        # lusetall — også når den står i serien med tomme uker — og da
        # vises ikke knappen «Lusetall som CSV». Fila skrives likevel.
        "lus_med_tall": sum(1 for u in serie if u["voksne_hunnlus"] != ""),
        # Hele serien, urørt. CSV-en skrives av den; tabellen viser
        # slutten av den. At de to kommer fra SAMME liste er det som
        # gjør at de ikke kan bli uenige.
        "lus_serie": serie,
        "lusegraf": lusegraf(serie),
        "lusperioder": produksjonsperioder(
            serie, lusedatoer[-1] if lusedatoer else ""),
        # MATTILSYNETS SØKNADER OM UNNTAKSVEKST, når lokaliteten står i
        # lista med en sikker kobling. Lenker til analysesiden.
        "unntak": unntak_for_lokalitet(
            (felles.unntak if felles else unntak_per_lokalitet())
            .get(loknr, [])),
        # Nedlastingene. `lusetall.csv` er ikke lenger blant dem, men
        # skrives fortsatt. Navnet bærer dataversjonen — se
        # `lusetall_stamme()`.
        "xlsx_filnavn": f"{lusetall_stamme(loknr, lus_versjon)}.xlsx",
        "zip_filnavn": f"{lusetall_stamme(loknr, lus_versjon)}.zip",
        "endringer": endringer,
        "maaleserie_rader": maaleserie_rader,
        "dekning_fra": dekning,

        # ---- overskriften ----
        "status": visningsord.verdi("prodomraade_status",
                                    a.get("prodomraade_status", "")),
        "status_klasse": FARGE_KLASSE.get(
            _fargekode((a.get("prodomraade_status") or "").strip().lower()), ""),
        "arter": visningsord.verdi("arter", a.get("arter", "")),
        "klareringstype": visningsord.verdi("klareringstype",
                                            a.get("klareringstype", "")),
        "vanntype": visningsord.verdi("vanntype", a.get("vanntype", "")),
        "plassering": visningsord.verdi("plasseringstype",
                                        a.get("plasseringstype", "")),
        # KAPASITETEN ER REGISTERETS EGEN, ikke summen av tillatelsenes
        # MTB. Overleveringen ber om det siste; avvik 3 i oppdraget
        # setter det første. Grunnen er at de to er ULIKE STØRRELSER:
        # lokalitetens klarerte kapasitet er et vedtak om hva stedet
        # tåler, mens summen av tillatelser er hvor mye biomasse
        # innehaverne til sammen har lov til å ha — og en tillatelse kan
        # brukes på flere lokaliteter. En sum ville vært vårt regnestykke
        # presentert som registerets tall.
        "kapasitet": visningsord.maalt(a.get("kapasitet", ""),
                                       a.get("kapasitet_enhet", "")),
        "kapasitet_midlertidig": visningsord.maalt(
            a.get("kapasitet_midlertidig", ""), a.get("kapasitet_enhet", "")),
        "selskap": _lokalitetens_selskap(mine_till, overforingsrader, eierskap),

        # ---- kartet ----
        #
        # NABOENE OG OMRÅDEGRENSA er med fra 25.09.2026. Kartet sa før
        # bare «her ligger den»; nå sier det også hvem den ligger ved
        # siden av, og hvor grensa går. Begge deler er ting som står i
        # tabellene på siden — kartet er en annen vei til dem, aldri
        # den eneste.
        "posisjonskart": kart.posisjonskart(
            a.get("breddegrad"), a.get("lengdegrad"),
            naboer=_naboer(loknr, akva, id(felles) if felles else id(akva)),
            omraade=a.get("prodomraade_kode", "")),

        # ---- de to historikkene ----
        "observert": _observert_historikk(endringer, dekning, felles),
        "oppgitt": _oppgitt_historikk(a, tillatelsesrader, overforingsrader,
                                      former),

        # ---- fisk til stede ----
        "biolag": _biolagstripe(
            (felles.biomasselag.get(loknr, []) if felles
             else _biomasselag()[0].get(loknr, [])),
            (felles.biomasselag_uker if felles else _biomasselag()[1])),

        # ---- siteringen ----
        # URL-EN ER DEN FASTE ID-URL-EN, uten spørrestreng. Uka, datoen
        # og sjekksummen står i TEKSTEN. En `?uke=`-parameter ville
        # gjort identiteten til et argument på en side som ikke har noe
        # som leser den — se 2026-09-16-url-struktur.md punkt 3, og
        # avvik 5 i oppdraget.
        "siter": {
            "url": f"{_basisurl()}/lokalitet/{loknr}/",
            "uke": visningsord.uke(akva_dato),
            "dato": visningsord.dato(akva_dato),
            "aar": akva_dato[:4],
            "sjekksum": (felles.sjekksum if felles else _sjekksum("akvakultur")),
        },
    }
    # REGNES AV DET SIDEN ALLEREDE VISER, ikke slått opp på nytt.
    lok["sammendrag"] = lokalitetssammendrag(lok)
    return lok


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
        ]
        if lok["lus_mangler_tekst"]:
            linjer += [lok["lus_mangler_tekst"]]
        linjer += [""]
    else:
        linjer += [
            f"INGEN UKER. Lokaliteten finnes ikke i noen av de "
            f"{lok['lusetall_snapshots']} ukene vi har.",
            "Fila har hode og null rader.",
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
        f"Bygget {bygget} av Kystloggen fra øyeblikksbilder. Tallene er "
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


# ------------------------------------------- regnearket og datapakken
#
# Fra 07.10.2026 tilbys lusetallserien som Excel (.xlsx) og som
# datapakke (.zip) i stedet for som én CSV. `lusetall.csv` skrives
# fortsatt, med samme innhold som før: adressen er lenket til og sitert,
# og en adresse som slutter å svare er en sitering som slutter å virke.
# Den er bare ikke lenger knappen. Se nedlasting.py for formatene.

XLSX_MIME = ("application/vnd.openxmlformats-officedocument."
             "spreadsheetml.sheet")


def lusetall_stamme(loknr: str, uke: str) -> str:
    """Filnavnet uten endelse: «kystloggen-lusetall-20797-2026-37».

    NAVNET SIER HVA FILA ER, ikke «lusetall» for alt. Fram til
    07.10.2026 het hver eneste lokalitets fil `lusetall.csv`, og 1 782
    nedlastinger i samme mappe hos en leser ble `lusetall (1).csv`,
    `lusetall (2).csv` …

    UKA ER DATAVERSJONEN: ISO-uka til det NYESTE lusetallsnapshotet,
    altså hvor langt serien er sett etter — ikke byggeuka, og ikke siste
    uke lokaliteten selv har en rad. F6 var nettopp et filnavn datert
    etter kjøredagen over innhold fra en annen uke. En lokalitet som
    sluttet å rapportere i 2019, står i fila «-2026-37» fordi den er
    sett etter til og med uke 37 uten å bli funnet.

    Uten uke (ingen lusetallsnapshots i det hele tatt) står navnet uten
    den, framfor med en påfunnet.
    """
    return "-".join(x for x in ("kystloggen-lusetall", loknr, uke) if x)


def endringer_stamme(slug: str) -> str:
    """«kystloggen-endringer-2026-41». Uka er endringsukas egen, den
    samme som i adressen til ukesiden."""
    return f"kystloggen-endringer-{slug}"

# LISENSEN PER KILDE, som den skal stå i en nedlastet fil.
#
# Fra docs/LISENSKJEDE.md, tabellen, lest 25.08.–14.09.2026. Står her og
# ikke på kilden av samme grunn som `LISENS_URL`: hva vi oppgir i en
# fil vi distribuerer, er publiseringsleddets sak. En kilde som ikke
# står her, kaster i `kildelisens()` — en fil uten lisenslinje skal ikke
# skrives, samme regel som `UbelagtKilde`.
KILDELISENS = {
    "lusetall": ("BarentsWatch (opplysninger fra Mattilsynet)", "NLOD",
                 "https://www.barentswatch.no/artikler/api-vilkar"),
    "akvakultur": ("Fiskeridirektoratet, Akvakulturregisteret", "NLOD",
                   "https://www.fiskeridir.no/statistikk-tall-og-analyse/"
                   "lisens-for-bruk-av-fiskeridirektoratets-data"),
    "biomasselag": ("Fiskeridirektoratet, kartlaget for biomasse", "NLOD",
                    "https://www.fiskeridir.no/statistikk-tall-og-analyse/"
                    "lisens-for-bruk-av-fiskeridirektoratets-data"),
    "eierskap": ("Fiskeridirektoratet og Brønnøysundregistrene, "
                 "tillatelser og eiere",
                 "NLOD (Fiskeridirektoratet) og NLOD 2.0 "
                 "(Brønnøysundregistrene)",
                 "https://www.fiskeridir.no/statistikk-tall-og-analyse/"
                 "lisens-for-bruk-av-fiskeridirektoratets-data"),
    "enhetsregisteret": ("Brønnøysundregistrene, Enhetsregisteret",
                         "NLOD 2.0", "https://data.norge.no/nlod/no/2.0"),
    "unntaksvekst": ("Mattilsynet, oversikt over søknader om "
                     "unntaksvekst 2025/2026",
                     "uten vern etter åndsverkloven § 14",
                     "https://lovdata.no/lov/2018-06-15-40/§14"),
}


def kildelisens(kilder) -> list[tuple[str, str, str]]:
    """(utgiver, lisens, lenke) for kildene, i rekkefølge. Kaster på en
    kilde uten lisenslinje."""
    ut = []
    for kilde in kilder:
        if kilde not in KILDELISENS:
            raise UbelagtKilde(
                f"{kilde}: ingen lisenslinje i KILDELISENS. En nedlastet "
                f"fil skal si hvilken lisens dataene står under.")
        ut.append(KILDELISENS[kilde])
    return ut


# KOLONNENE I LUSETALLFILENE, med forklaring og hva en tom celle betyr.
# Navnene er `CSV_KOLONNER`, i samme rekkefølge — se
# `test_lusekolonnene_er_csv_kolonnene`. Kildenøkkelen i parentes er
# BarentsWatch sin, slik `sources/lusetall.py` mapper den.
LUSEKOLONNER = (
    nedlasting.Kolonne(
        "lokalitetsnummer", "string",
        "Fiskeridirektoratets lokalitetsnummer. Et nummer som identifiserer, "
        "ikke et tall å regne med, og lagret som tekst."),
    nedlasting.Kolonne(
        "dato", "date",
        "Mandagen i ISO-uka raden gjelder for. Kilden daterer hver uke til "
        "mandagen."),
    nedlasting.Kolonne(
        "iso_aar", "integer",
        "ISO-året uka hører til. Kan avvike fra kalenderåret rundt nyttår: "
        "2019-12-30 er uke 1 i 2020."),
    nedlasting.Kolonne("iso_uke", "integer", "ISO-ukenummeret, 1 til 53."),
    nedlasting.Kolonne(
        "voksne_hunnlus", "decimal",
        "Gjennomsnittlig antall voksne hunnlus per fisk, oppdretterens "
        "ukentlige telling rapportert til Mattilsynet (avgAdultFemaleLice).",
        "Kilden oppgir ikke noe tall for uka. Det er ikke null — se "
        "lus_er_rapportert på samme rad."),
    nedlasting.Kolonne(
        "lus_er_rapportert", "boolean",
        "Om lusetall er rapportert for uka (hasReportedLice). Skiller "
        "«rapportert null lus» fra «ikke rapportert».",
        "Kilden oppgir ikke feltet for uka."),
    nedlasting.Kolonne(
        "har_laksefisk", "boolean",
        "Om det står laksefisk på lokaliteten (hasSalmonoids).",
        "Kilden oppgir ikke feltet for uka."),
    nedlasting.Kolonne(
        "brakklagt", "boolean",
        "Om lokaliteten er brakklagt (isFallow).",
        "Kilden oppgir ikke feltet for uka."),
    nedlasting.Kolonne(
        "har_medikamentell_behandling", "boolean",
        "Om det er gjort medikamentell behandling mot lus "
        "(hasSubstanceTreatments). Målt 01.09.2026: siste uke kilden "
        "oppga sann for noen lokalitet, var 2024-11-11. Usann etter den "
        "uka kan derfor ikke leses som at det ikke ble gjort.",
        "Kilden oppgir ikke feltet for uka."),
    nedlasting.Kolonne(
        "har_mekanisk_fjerning", "boolean",
        "Om lus er fjernet mekanisk (hasMechanicalRemoval).",
        "Kilden oppgir ikke feltet for uka."),
    nedlasting.Kolonne(
        "har_rensefisk", "boolean",
        "Om det er satt ut rensefisk (hasCleanerfishDeployed). Målt "
        "01.09.2026: siste uke kilden oppga sann for noen lokalitet, var "
        "2023-04-17. Usann etter den uka kan derfor ikke leses som at det "
        "ikke ble gjort.",
        "Kilden oppgir ikke feltet for uka."),
)


def _hentet_spenn(stempler, hvorfra: str) -> list[str]:
    """Setningen om når VI hentet. Tom liste når ingenting er kjent.

    `fetched_at` handler om oss, ikke om kilden (CLAUDE.md 1b-7).
    Mangler stemplet på alle radene, sier fila ingenting om det framfor
    å finne på et tidspunkt.
    """
    kjente = sorted(s for s in stempler if s)
    if not kjente:
        return []
    forste, siste = (visningsord.tidspunkt(kjente[0]),
                     visningsord.tidspunkt(kjente[-1]))
    if forste == siste:
        return [f"Hentet fra {hvorfra} {siste}."]
    return [f"Hentet fra {hvorfra} mellom {forste} og {siste}. Eldre uker "
            f"er hentet i ettertid, samlet."]


def lusetall_datasett(lok: dict, setninger: list[str],
                      bygget: str) -> nedlasting.Datasett:
    """Lusetallserien for én lokalitet, som regneark og datapakke.

    Radene er `lus_serie` — den SAMME lista CSV-en, tabellen og grafen
    bygges av.
    """
    if lok["lus_uker"]:
        innhold = (f"Ukentlige lusetall for akvakulturlokalitet "
                   f"{lok['loknr']} {lok['navn']}, {lok['kommune']}: "
                   f"{lok['lus_uker']} uker fra {lok['lus_fra']} til "
                   f"{lok['lus_til']}, én rad per uke. "
                   f"{lok['lus_uten_tall']} av {lok['lus_uker']} uker har "
                   f"ikke noe tall for voksne hunnlus.")
    else:
        innhold = (f"Ingen uker. Lokalitet {lok['loknr']} {lok['navn']}, "
                   f"{lok['kommune']}, finnes ikke i noen av de "
                   f"{lok['lusetall_snapshots']} ukene vi har fra "
                   f"BarentsWatch. Fila har overskrift og null rader.")
    return nedlasting.Datasett(
        stamme=Path(lok["xlsx_filnavn"]).stem,
        tittel=f"Lusetall for lokalitet {lok['loknr']} {lok['navn']}",
        beskrivelse=innhold,
        kolonner=LUSEKOLONNER,
        rader=[{"lokalitetsnummer": lok["loknr"], **u}
               for u in lok["lus_serie"]],
        kilder=kildelisens(["lusetall"]),
        attribusjon=list(setninger),
        hentet=_hentet_spenn((u.get("hentet", "") for u in lok["lus_serie"]),
                             "BarentsWatch"),
        bygget=bygget,
        merknader=(["Tallene er gjengitt uendret fra kilden."]
                   + ([f"Manglende uker: {lok['lus_mangler_tekst']}"]
                      if lok["lus_mangler_tekst"] else [])),
        nokkel=("lokalitetsnummer", "dato"),
    )


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
        "creator": {"@type": "Organization", "name": "Kystloggen"},
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
        #
        # TO NEDLASTINGER, de samme som knappene. `lusetall.csv` svarer
        # fortsatt, men står ikke her: den er en gammel adresse som
        # holdes i live, ikke et tilbud.
        spenn = f"{lok['lus_uker']} uker, {lok['lus_fra']} til {lok['lus_til']}."
        data["distribution"] = [{
            "@type": "DataDownload",
            "name": f"Lusetall for lokalitet {lok['loknr']}, hele serien, "
                    f"{hva}",
            "description": f"{spenn} {beskrivelse}",
            "contentUrl": fil,
            "encodingFormat": format_,
            "creditText": (indeks.get("lusetall") or ("",))[0],
        } for fil, format_, hva, beskrivelse in (
            (lok["xlsx_filnavn"], XLSX_MIME, "Excel",
             "Regneark med arket «Om dataene»."),
            (lok["zip_filnavn"], "application/zip", "datapakke",
             "CSV, metadata.json etter W3C CSVW og README.txt."))]
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
    miljo = Environment(
        loader=FileSystemLoader(MALER),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # FILTRENE ER `visningsord`, ikke nye funksjoner. En mal som skriver
    # «16. september 2026» skal gjøre det gjennom det samme ene stedet
    # som CSV-en og byggerapporten bruker — to steder som staver
    # september hver for seg er formen F6 og F7 hadde.
    #
    # Bare DATOFORMENE er filtre. `verdi()` og `felt()` tar et feltnavn
    # og hører hjemme i Python, der den som bygger raden vet hvilket
    # felt det er; i malen ville feltnavnet måttet skrives en gang til.
    miljo.filters["dato"] = visningsord.dato
    miljo.filters["uke"] = visningsord.uke
    miljo.filters["isouke"] = visningsord.isouke
    miljo.filters["ukespenn"] = visningsord.ukespenn
    miljo.filters["maaned"] = visningsord.maaned
    miljo.filters["tidspunkt"] = visningsord.tidspunkt
    miljo.filters["tall"] = visningsord.tall
    # NAVN I VISNINGEN. Registrene skriver navn i versaler; sidene viser
    # dem i menneskelig form, og den rå verdien står i registerfeltene,
    # siteringen og nedlastingene. Filtre og ikke Python, fordi det er
    # MALEN som vet om en verdi står i en overskrift eller i en
    # registertabell. Se `visningsord.selskapsnavn()`.
    miljo.filters["tittelform"] = visningsord.tittelform
    miljo.filters["selskapsnavn"] = visningsord.selskapsnavn
    miljo.globals["kommunenavn"] = visningsord.kommunenavn
    # `feltmerke` er en GLOBAL og ikke et filter: den tar to argumenter
    # der rekkefølgen betyr noe, og `{{ "kommune"|feltmerke(r.kommune) }}`
    # leser baklengs. Se `feltmerke()`.
    # «1 tillatelser» sto på lokalitetssiden fra den ble bygget. Én
    # hjelper, brukt overalt — se visningsord.antall()/alle().
    miljo.globals["antall"] = visningsord.antall
    # TERSKELEN ER ETT TALL, i `vesentlighet`. Teksten som forklarer den,
    # leser det derfra og skriver det ikke av.
    miljo.globals["koordinatterskel"] = visningsord.tall(
        int(vesentlighet.KOORDINAT_TERSKEL_M))
    # TALL OG PROSENT SOM GLOBALER, ikke bare som filtre. Et filter
    # leses bakfra i en `{% if %}`-kjede, og et tall skrevet uten dem
    # står med tusenskille noen steder og uten andre — MÅLT 24.09.2026
    # sto «1717 av 1 782 lokaliteter (96.35 %)» på /om/, med tre
    # skrivemåter i én setning.
    miljo.globals["tall"] = visningsord.tall
    miljo.globals["prosent"] = visningsord.prosent
    miljo.globals["alle"] = visningsord.alle
    # `kilde` er en GLOBAL av samme grunn som `feltmerke`: den slår opp
    # en verdi i en tabell og hører hjemme der raden skrives. Se
    # `visningsord.KILDENAVN`.
    miljo.globals["kilde"] = visningsord.kilde
    # SAMME OPPSLAG SOM FILTER. `{{ liste|map("kildenavn") }}` krever et
    # filter; `kilde()` som global kan ikke brukes av `map`.
    miljo.filters["kildenavn"] = visningsord.kilde
    miljo.globals["feltmerke"] = feltmerke
    miljo.globals["fargeklasse"] = fargeklasse
    miljo.globals["personformnavn"] = personformnavn
    miljo.globals["attribusjonslenke"] = ATTRIBUSJONSLENKE
    miljo.globals["SKJULT_NAVN_FELT"] = publiseringsvakt.SKJULT_NAVN_FELT
    miljo.globals["VERDI_MANGLER"] = VERDI_MANGLER
    return miljo


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


# ------------------------------------------- KORT PÅ SMAL SKJERM
#
# EN TABELL PÅ 390 PIKSLER ER IKKE EN TABELL. Ni kolonner lusetall på en
# telefon ble til en vannrett rulleboks der kolonneoverskriften forsvant
# ut av syne før verdien kom inn i det — leseren måtte huske hva
# kolonne sju het mens hun dro.
#
# Under 640px legges hver rad om til et KORT: første celle er tittelen,
# og resten står som «etikett: verdi». Etiketten er kolonneoverskriften,
# og den settes HER, ved bygging, som `data-label` på hver `<td>`.
#
# ## Hvorfor ved bygging og ikke i malen
#
# Fordi det er 26 tabeller i ni maler, og et `data-label` skrevet for
# hånd er en andre kopi av `<th>`-teksten. De to ville kommet i utakt
# første gang noen døpte om en kolonne, og utakten ville vært usynlig på
# en bred skjerm. Her leses etiketten av tabellens eget hode, og kan
# ikke bli uenig med det.
#
# ## Hvorfor ikke i CSS
#
# `content: attr()` kan bare lese et attributt på elementet selv. En
# celle vet ikke hva kolonnen over den heter; det er tabellen som vet
# det, og tabellen finnes bare som HTML.

# TABELLENE SOM IKKE BLIR KORT, med id.
#
# `endringer-uker` på /endringer/ er en KRYSSTABELL: én rad per uke, én
# kolonne per endringstype, og tallene leses BÅDE langs raden og ned
# kolonnen. Som kort mister den den andre aksen helt — tretten
# «Trafikklys: 4»-linjer under hverandre er ikke en tabell man kan
# sammenligne uker i. Den beholder vannrett rulling, og første kolonne
# (uka) låses med `position: sticky` så raden kan følges.
#
# `akvakultur-alle` og `eierskap-selskaper` er INDEKSENE. Som kort er en
# rad i lokalitetsindeksen 295 px høy på 390 (MÅLT 08.10.2026: 525 434 px
# for 1 782 lokaliteter). Som tabell er den én linje, og nummeret og
# navnet — det man leter etter — står i de to første kolonnene. Resten
# ruller vannrett, som krysstabellen.
UTEN_KORT = frozenset({"endringer-uker", "akvakultur-alle",
                       "eierskap-selskaper",
                       # LOKALITETSLISTA PÅ OMRÅDE- OG SELSKAPSSIDEN er en
                       # indeks som de flate listene: én linje per rad, som
                       # ruller vannrett på telefon. Som kort var områdesiden
                       # med 137 lokaliteter 59 939 px høy på 390.
                       "akvakultur-lokaliteter",
                       # ANALYSESIDEN FOR UNNTAKSVEKST. Tallene leses ned
                       # kolonnene — godkjent mot avslått, før mot etter —
                       # som i krysstabellen. Som kort var hovedtabellen
                       # 29 681 px høy på 390 (MÅLT 09.10.2026), og hodet
                       # har to rader, som `_kolonnenavn()` ikke leser.
                       "unntak-lokaliteter", "unntak-perioder"})

_TABELL = re.compile(r"(<table\b[^>]*>)(.*?)(</table>)", re.S)
_TABELL_ID = re.compile(r'\bid="([^"]+)"')
_RAD = re.compile(r"(<tr\b[^>]*>)(.*?)(</tr>)", re.S)
_CELLE = re.compile(r"<(td|th)\b([^>]*)>", re.I)
_TAGG = re.compile(r"<[^>]*>")


def _kolonnenavn(kropp: str) -> list[str]:
    """Kolonneoverskriftene, i rekkefølge. Tom liste uten `<thead>`."""
    hode = re.search(r"<thead\b[^>]*>(.*?)</thead>", kropp, re.S)
    if not hode:
        return []
    rad = re.search(r"<tr\b[^>]*>(.*?)</tr>", hode.group(1), re.S)
    if not rad:
        return []
    return [" ".join(_TAGG.sub(" ", c).split())
            for c in re.findall(r"<th\b[^>]*>(.*?)</th>", rad.group(1), re.S)]


def med_datamerker(html: str) -> str:
    """`data-label` på hver `<td>`, lest av tabellens egen `<thead>`.

    Additivt og idempotent: en celle som alt har `data-label` røres
    ikke, og en tabell uten `<thead>` eller uten id går uendret
    igjennom. Kontrakten krever `<thead>` på hver tabell — dette legger
    ikke til et krav, det bruker det som alt er der.

    EN CELLE MED `colspan` FÅR INGEN ETIKETT. Den strekker seg over
    flere kolonner, og «Observert: Ingen endringer i uke 39» ville vært
    en etikett som lyver om hva cellen er. Tomradene er de eneste som
    har det.
    """
    def per_tabell(m: re.Match) -> str:
        aapning, kropp, slutt = m.group(1), m.group(2), m.group(3)
        ident = _TABELL_ID.search(aapning)
        if ident and ident.group(1) in UTEN_KORT:
            return m.group(0)
        navn = _kolonnenavn(kropp)
        if not navn:
            return m.group(0)

        # KLASSEN SIER AT TABELLEN KAN BLI KORT, og den settes her av
        # samme grunn som etiketten: unntakslista er i Python, og en
        # id-liste i CSS-en ved siden av ville vært det andre stedet å
        # glemme en tabell. Stilarket spør etter `.tabell--kort` og
        # trenger ikke vite hvilke tabeller det er.
        if "tabell--kort" not in aapning:
            if 'class="' in aapning:
                aapning = aapning.replace('class="', 'class="tabell--kort ', 1)
            else:
                aapning = aapning[:-1] + ' class="tabell--kort">'

        def per_rad(r: re.Match) -> str:
            celler = list(_CELLE.finditer(r.group(2)))
            ut, forrige = [], 0
            for i, c in enumerate(celler):
                ut.append(r.group(2)[forrige:c.start()])
                forrige = c.end()
                merke = ""
                if (c.group(1).lower() == "td" and i < len(navn)
                        and navn[i] and "data-label" not in c.group(2)
                        and "colspan" not in c.group(2).lower()):
                    merke = f' data-label="{escape(navn[i], quote=True)}"'
                ut.append(f"<{c.group(1)}{c.group(2)}{merke}>")
            ut.append(r.group(2)[forrige:])
            return r.group(1) + "".join(ut) + r.group(3)

        # BARE `<tbody>`. Hoderaden har ingen verdier å merke, og en
        # etikett på en kolonneoverskrift ville vært overskriften to
        # ganger.
        deler = re.split(r"(<tbody\b[^>]*>|</tbody>)", kropp)
        i_kropp = False
        ny = []
        for del_ in deler:
            if del_.startswith("<tbody"):
                i_kropp = True
            elif del_ == "</tbody>":
                i_kropp = False
            elif i_kropp:
                del_ = _RAD.sub(per_rad, del_)
            ny.append(del_)
        return aapning + "".join(ny) + slutt

    return _TABELL.sub(per_tabell, html)


def skriv_side(sti: Path, html: str) -> Path:
    """Én ferdig side til disk. ETT sted, for alle sidetyper.

    Alt som skal gjelde HVER side, gjør det her. I dag ett: `data-label`
    på hver verdicelle, så en tabell kan legges om til kort på smal
    skjerm — se `med_datamerker()`. Ni skrivesteder ville vært ni steder
    å glemme det neste.
    """
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text(med_datamerker(html), encoding="utf-8")
    return sti


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
    # KASTER PÅ UBELAGT før noe skrives. `_grunnkontekst()` bygger
    # setningene på nytt til bunnteksten; kallet her er porten, og den
    # skal stå FØR malen kompileres slik at en UBELAGT kilde stopper
    # siden framfor å rendres og kastes etterpå.
    attribusjon(SIDENS_KILDER, vilkaar)
    mal = mal or _miljo().get_template("lokalitet.html.j2")

    html = mal.render(
        lok=lok,
        **_grunnkontekst(
            felles, rot, sti, kilder=SIDENS_KILDER,
            tittel=f"{lok['tittelnavn']}, lokalitet {lok['loknr']} — Kystloggen",
            beskrivelse=(
                f"Registerdata, eierskap og ukentlige lusetall for "
                f"akvakulturlokalitet {lok['loknr']} {lok['tittelnavn']} i "
                f"{visningsord.tittelform(lok['kommune'])}, med endringslogg."),
            jsonld=jsonld(lok),
            proveniens_tekst=proveniens(
                lok["akva_dato"], lok["akva_hentet"],
                "Lusetallene er hentet fra BarentsWatch og gjelder uka "
                "de er datert til."),
            meny_aktiv="lokalitet",
            # KARTET ER PÅ SIDEN, og da må Kartverkets navn være det
            # også — i bunnteksten og under kartet. Se `KARTVERKET`.
            kart=lok["posisjonskart"] is not None,
            # UNDERTITTELEN I TREFFLISTA: kommune · område · innehaver.
            # De tre er det en leser skiller to lokaliteter på når begge
            # heter noe med «holmen». Innehaveren er den samme strengen
            # siden viser — også når kilden klassifiserer den som en
            # personform, og da er den «eieren er en personform».
            sidetype="Lokalitet",
            undertittel=SKILLE.join(
                x for x in (visningsord.tittelform(lok["kommune"]),
                            (f"{lok['po_kode']} {lok['po_navn']}"
                             if lok["po_kode"] else ""),
                            visningsord.selskapsnavn(lok["selskap"]["navn"]))
                if x),
            soketekst=f"{lok['tittelnavn']} {visningsord.tittelform(lok['kommune'])}",
            main_klasse="fullbredde",
            feed=f"/lokalitet/{loknr}/feed.xml",
            feed_tittel=f"Kystloggen: endringer for lokalitet {loknr}"),
    )

    # Mappe + index.html, som er hva en avsluttende skråstrek BETYR.
    # `skriv_side()` lager mappa; CSV-en under skrives i den samme.
    mappe = sti.parent
    skriv_side(sti, html)

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
    #
    # ÉN BYGGEDATO for alle tre filene. To oppslag på klokka kan svare
    # ulikt rundt midnatt, og da daterer CSV-en og regnearket seg til
    # hver sin dag (CLAUDE.md 1b, F7).
    bygget = dt.date.today().isoformat()
    setninger = attribusjon(["lusetall"], vilkaar)
    csv_sti = mappe / CSV_FILNAVN
    csv_sti.write_text(csv_tekst(lok, setninger, bygget), encoding="utf-8")

    # REGNEARKET OG DATAPAKKEN, av de samme radene. Skrives også når
    # serien er tom, av samme grunn som CSV-en: «vi har sett etter og
    # ikke funnet noe» er et svar.
    ds = lusetall_datasett(lok, setninger, bygget)
    xlsx_sti, zip_sti = mappe / ds.xlsx_navn, mappe / ds.zip_navn
    xlsx_sti.write_bytes(nedlasting.xlsx_bytes(ds))
    zip_sti.write_bytes(nedlasting.zip_bytes(ds))
    return [sti, csv_sti, xlsx_sti, zip_sti]


# -------------------------------------------------------- stilarket
#
# ## Én fil, lenket — ikke innebygd i hver side
#
# Innebygd i `<style>` ville stilarket kostet ~12 kB per side. Over
# 2 279 sider er det 27 MB, altså 18 % på et utputt som er 155 MB, og
# hver leser ville lastet det på nytt for hver side. Lenket er det én
# fil og én forespørsel, og nettleseren hentet den sist på forsiden.
#
# ## ÉN FIL, og det ble den 22.09.2026
#
# Fram til da var `/stil.css` to filer slått sammen: `maler/tokens.css`
# (Digdirs verdier ordrett, med tagg, sha256 og MIT-lisens) og
# `maler/stil.css` (vår). Grensa var at en oppgradering av tokens skulle
# kunne byttes ut som en blokk.
#
# Designoverleveringen fastsetter sin egen typeskala, sitt eget
# avstandsrutenett og radius 0 overalt, og da var det ingenting igjen i
# den hentede fila som faktisk ble brukt. Den er fjernet, og
# begrunnelsen står i sin helhet øverst i `maler/stil.css`. Følgen er at
# /om/ ikke lenger fører Digdir under «det vi låner» — ikke en
# utelatelse, men at vi ikke låner det.
#
# ## Stien er absolutt, som hver annen URL på nettstedet
#
# `/stil.css`, ikke `../../stil.css`. Sidene lenker alt absolutt (se
# 2026-09-16-url-struktur.md), så det er ingen ny begrensning — men det
# betyr at siden må SERVERES for å se riktig ut. Åpnet rett fra disk
# med `file://` finner nettleseren verken stilarket eller nabosidene.
#     python -m http.server --directory <ut-mappa>

STILFILER = ("stil.css",)


def stilark() -> str:
    """Stilarket. Én fil siden 22.09.2026 — se kommentaren over.

    Lista står igjen som en TUPPEL og ikke som en enkeltsti, fordi den
    er stedet en andre fil skal legges inn hvis det noen gang blir en
    av dem igjen. Rekkefølgen i lista er rekkefølgen i utputtet."""
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

# TRE FONTER FRA 22.09.2026, og to lisensfiler.
#
# `ibmplex-OFL.txt` dekker BEGGE Plex-familiene: hos google/fonts ligger
# de under hver sin katalog med hver sin OFL, og de to filene er
# bit-identiske (`sha256 7e6b2818…`). Én fil er derfor ikke en
# forenkling — det er den samme fila. Se docs/design/IBM-PLEX.md.
FONTFILER = ("newsreader.woff2", "newsreader-OFL.txt",
             "ibmplexsans.woff2", "ibmplexmono.woff2", "ibmplex-OFL.txt")

# IKONENE. Samme «K» i alle tre, samme kvadrat, tre formater fordi
# plattformene ber om tre:
#
#   favicon.svg          moderne nettlesere, skalerer til alt
#   favicon-32.png       reserven, og den som faktisk brukes i en
#                        fanetittel på eldre Safari og i bokmerkelister
#   apple-touch-icon.png iOS, 180x180, når noen legger siden på
#                        hjemskjermen
#
# «K»-en er IKKE tekst i SVG-en. Et favicon rendres uten nettstedets
# `@font-face`, så `font-family: Newsreader` ville falt til en
# systemserif og gitt en annen K enn ordmerket. Glyffen er hentet ut av
# Newsreader ved wght=600 og opsz=28 — samme instans som merket — og
# ligger som en `<path>`. Se docs/design/NEWSREADER.md.
#
# PNG-ene er rastret av SVG-en, ikke tegnet på nytt. De kan derfor ikke
# si noe annet enn den.
IKONFILER = ("favicon.svg", "favicon-32.png", "apple-touch-icon.png")

# SKRIPTET. Én fil, lastet med `defer`, og den legger ikke til én
# verdi på noen side — se `maler/kystloggen.js`.
# `kystloggen.js` lastes av hver side; `sok.js` bare av `/sok/`. Se
# modulkommentaren i sok.js for hvorfor de er to filer og ikke én.
SKRIPTFILER = ("kystloggen.js", "sok.js")

# HEROFOTOGRAFIET, i tre bredder. Hostet av oss, aldri hentet fra
# Unsplash i runtime: en `images.unsplash.com`-URL i markupen ville
# fortalt dem hvem som leser siden, og en side som henter sitt eget
# hovedbilde fra en tredjepart er en side som ser feil ut den dagen den
# tjenesten gjør det.
#
# Ligger i `bilde/` og ikke i rota, fordi rota er for filer som MÅ ligge
# der (`/stil.css`, fontene, faviconene, `robots.txt`).
#
# Motivet er skjærgård på Bømlo med et oppdrettsanlegg ved horisonten,
# av Endre Stedje. Det sto et annet herofotografi her 22.–26.09.2026 og
# et kart 26.–27.09; begge er ført i docs/design/HEROFOTO.md, som er
# proveniensen for alle tre.
BILDEMAPPE = "bilde"

BILDEFILER = ("hero-800.jpg", "hero-1600.jpg", "hero-2400.jpg")

# HEROENS BILDETEKST. Stedet og fotografen er EGENSKAPER VED FILA og
# hører derfor her, ved siden av filnavnene — ikke i malen. Malen
# skriver ingen navn; den er den samme uansett hvilket bilde som ligger
# der. Se kommentaren øverst i `maler/forside.html.j2`.
#
# `kommune` er ikke det samme som `sted`: den er NØKKELEN vi slår opp
# produksjonsområdet med, og den skrives slik registeret skriver den.
# `sted` er det leseren ser. For dette bildet er de like; for et bilde
# tatt på en navngitt holme ville de ikke vært det.
#
# PRODUKSJONSOMRÅDET STÅR IKKE HER. Det slås opp i registeret ved hver
# bygging — se `_herofoto()`. En kode skrevet av her ville vært et tall
# om VERDEN, hentet fra hukommelsen i stedet for fra kilden, og den
# ville blitt stående den dagen området endrer seg.
HEROFOTO = {
    "sted": "Bømlo",
    "kommune": "BØMLO",
    "fotograf": "Endre Stedje",
    "tjeneste": "Unsplash",
}

# KARTGEOMETRIEN SENDES IKKE UT. Den er tegnet INN i SVG-en på hver
# side, og en GeoJSON-fil ved siden av ville vært 365 kB ingen henter.
# LISENSFILA sendes ut: Natural Earth krever ingen attribusjon, men en
# lisens som ligger i repoet og ikke på nettstedet er en lisens en
# leser ikke kan finne. Se `docs/design/KARTGEOMETRI.md`.
GEOFILER = ("naturalearth-LICENSE.md",)


def _kopier_fra_maler(rot: Path, navn: tuple[str, ...], hvorfor: str) -> list[Path]:
    """Kopierer navngitte filer fra `maler/` til nettstedets rot.

    Kaster om en av dem mangler framfor å hoppe over den. Begge
    filtypene her feiler STILLE hvis de uteblir: en side uten fonten
    ser ut som et designvalg (`font-display: swap`), og en manglende
    favicon er bare en tom rute. Byggingen skal si fra i stedet."""
    rot.mkdir(parents=True, exist_ok=True)
    skrevet = []
    for fil in navn:
        kilde = MALER / fil
        if not kilde.exists():
            raise FileNotFoundError(f"{kilde} mangler. {hvorfor}")
        ut = rot / fil
        ut.write_bytes(kilde.read_bytes())
        skrevet.append(ut)
    return skrevet


def skriv_fonter(rot: Path) -> list[Path]:
    """Fonten og lisensen til nettstedets rot."""
    return _kopier_fra_maler(
        rot, FONTFILER,
        "Stilarket viser til fila; uten den er @font-face en død lenke.")


def skriv_ikoner(rot: Path) -> list[Path]:
    """Favicon-ene til nettstedets rot."""
    return _kopier_fra_maler(
        rot, IKONFILER,
        "base.html.j2 viser til fila i <head>.")


def skriv_skript(rot: Path) -> list[Path]:
    """Det ene skriptet til nettstedets rot."""
    return _kopier_fra_maler(
        rot, SKRIPTFILER,
        "base.html.j2 viser til fila; uten den mister siden tre "
        "forbedringer, men ingenting av innholdet.")


def skriv_bilder(rot: Path) -> list[Path]:
    """Bildene til `/bilde/`, og geometrifilene til rota.

    MAPPA LAGES BARE NÅR DET ER NOE Å LEGGE I DEN. `BILDEFILER` sto tom
    et døgn fra 26.09.2026 — heroen var et kart — og en `mkdir` som
    kjørte uansett, la igjen en tom `/bilde/` i utputtet: en mappe som
    viste til noe som ikke fantes lenger. Vakten blir stående selv om
    lista er full igjen; den koster én `if` og fanger neste gang.
    """
    skrevet = []
    if BILDEFILER:
        (rot / BILDEMAPPE).mkdir(parents=True, exist_ok=True)
    for navn in BILDEFILER:
        kilde = MALER / BILDEMAPPE / navn
        if not kilde.exists():
            raise FileNotFoundError(
                f"{kilde} mangler. Forsiden viser til fila i `srcset`; "
                f"uten den er heroen en tom flate.")
        ut = rot / BILDEMAPPE / navn
        ut.write_bytes(kilde.read_bytes())
        skrevet.append(ut)
    for navn in GEOFILER:
        kilde = MALER / "geo" / navn
        if not kilde.exists():
            raise FileNotFoundError(f"{kilde} mangler.")
        ut = rot / navn
        ut.write_bytes(kilde.read_bytes())
        skrevet.append(ut)
    return skrevet


# `skriv_norgeskart()` STO HER TIL 27.09.2026. Den skrev
# `/kart/norge.svg`, kysten med hver lokalitet, til forsidens hero.
#
# Heroen er et fotografi igjen, og fila er slettet — ikke bare tatt ut
# av malen. Målt før den ble det: `/kart/norge.svg` hadde nøyaktig én
# bruker, `<img class="hero-kart">`. Kystseksjonen tegner sitt eget kart
# inn i sida av `f.kart`. Se `kart.py`, der generatoren lå.


# ------------------------------------------------- ENDRINGSSIDENE
#
# `/endringer/`                      alle uker
# `/endringer/<år>-<uke>/`           én uke, alle typer
# `/endringer/<år>-<uke>/<type>/`    én uke, én type
#
# ## FILTERET ER STIER, IKKE EN SPØRRESTRENG
#
# Overleveringen tegner `<form method="get">` med avkrysningsbokser og
# `?type=`. En spørrestreng gjør identiteten til et argument, og en
# statisk side har ingenting som leser den — se
# 2026-09-16-url-struktur.md punkt 3, og avvik 5 i oppdraget.
#
# Hver type er derfor en EKTE SIDE, bygget ved bygging. Uten
# JavaScript er avkrysningsboksene vanlige lenker dit. Med JavaScript
# filtreres tabellen på stedet, og flere typer kan velges samtidig —
# det er forbedringen, og den er nettopp det en spørrestreng ikke kan
# gi uten en server.
#
# Prisen er 9 sider per uke. MÅLT: 5 uker gir 50 sider, og en uke
# koster ~0,1 s å rendre.

ENDRINGER_STI = "endringer"


def _ukens_csv(uke: dict) -> str:
    """Ukas hendelser som CSV, med attribusjonen i et kommentarhode.

    Samme form som lusetall-CSV-en: kolonneoverskriften er merkingen
    publiseringsvakten leser (`gransk_csv`), og kommentarhodet bærer
    vilkårene. Verdiene er de VISTE — de samme som står i tabellen —
    fordi dette er en nedlasting av siden, ikke av kilden. Rådataene
    ligger i changeloggen.
    """
    buffer = io.StringIO()
    for linje in (
            f"# Kystloggen — endringer observert i {uke['vist']}",
            # MERKET OG IKKE KALENDERUKA: «21.–27. september» påsto at
            # vi så på syv dager. Se `_ukemerke()`.
            f"# {uke['merke']}",
            f"# {uke['antall_fil']} hendelser, "
            f"observasjonsdatoer {', '.join(uke['datoer'])}",
            "#",
            "# «observert» er datoen VI så endringen i øyeblikksbildet,",
            "# ikke datoen registeret gjorde den. Registeret oppgir ikke",
            "# det siste.",
            "#",
            "# Kilder og vilkår:"):
        buffer.write(linje + "\n")
    for setning in attribusjon(ENDRINGSKILDER):
        buffer.write(f"#   {setning}\n")
    buffer.write("#\n")

    skriver = csv.writer(buffer, lineterminator="\n")
    skriver.writerow([k.navn for k in UKEKOLONNER])
    for rad in _ukens_rader(uke):
        skriver.writerow([rad[k.navn] for k in UKEKOLONNER])
    return buffer.getvalue()


def _ukens_rader(uke: dict) -> list[dict]:
    """Ukas hendelser som rader, for CSV-en, regnearket og datapakken.

    ÉN liste for alle tre. Se nedlasting.py.
    """
    # `entity_id` OG `entity_name` ER TOMME for en hendelse vi ikke
    # kan navngi. Kolonneoverskriften ER merkingen i en CSV
    # (`gransk_csv`), så en etikett som «Tillatelse N-R-0056» i
    # `entity_name`-kolonnen ville blitt lest som et navn — og det
    # er nøyaktig hva porten meldte. Se `_hendelse()`.
    return [{"observert": h["dato"], "uke": uke["slug"], "type": h["type"],
             "kilde": h["kilde"], "entity_id": h["identitet"],
             "entity_name": (h["gjelder"]
                             if h["gjelder_felt"] == "entity_name" else ""),
             "felt": h["felt"], "fra": h["fra"], "til": h["til"],
             "kommune": h["kommune"], "prodomraade_kode": h["po"],
             "prodomraade_navn": h["po_navn"]}
            for h in uke["hendelser"]]


# KOLONNENE I UKESFILENE. Rekkefølgen er den CSV-en har hatt siden
# 16.09.2026, og den endres ikke: en kolonne som flytter seg er et
# brudd for den som leser fila med et skript.
_KUN_NAVNGITTE = ("Tom når hendelsen gjelder noe vi ikke navngir med "
                  "kildens navn: en tillatelse, eller en oppføring som er "
                  "ute av utvalget vårt. entity_id og entity_name er da "
                  "begge tomme.")
_UTEN_LOKALITET = ("Tom når hendelsen ikke kan knyttes til én lokalitet "
                   "der registeret oppgir dette.")
UKEKOLONNER = (
    nedlasting.Kolonne(
        "observert", "date",
        "Datoen vi så endringen i øyeblikksbildet. Ikke datoen registeret "
        "gjorde den — registeret oppgir ikke det."),
    nedlasting.Kolonne(
        "uke", "string",
        "Endringsuka raden hører til, som år-uke (ISO). Samme verdi som i "
        "adressen til ukesiden."),
    nedlasting.Kolonne(
        "type", "string",
        "Hva slags endring. Verdiene står under «Merknad: type»."),
    nedlasting.Kolonne(
        "kilde", "string",
        "Hvilken av våre kilder endringen ble sett i: akvakultur, "
        "biomasselag, eierskap eller enhetsregisteret."),
    nedlasting.Kolonne(
        "entity_id", "string",
        "Lokalitetsnummer (akvakultur, biomasselag) eller "
        "organisasjonsnummer (enhetsregisteret). Et nummer som "
        "identifiserer, lagret som tekst.", _KUN_NAVNGITTE),
    nedlasting.Kolonne(
        "entity_name", "string",
        "Navnet kilden oppgir for lokaliteten eller selskapet.",
        _KUN_NAVNGITTE),
    nedlasting.Kolonne(
        "felt", "string", "Feltet som endret seg, med kildens feltnavn."),
    nedlasting.Kolonne(
        "fra", "string",
        "Verdien før, slik ukesiden viser den. Tekst, også når verdien er "
        "et tall: kolonnen bærer verdier fra mange ulike felt.",
        "Feltet var ikke oppgitt i forrige øyeblikksbilde (for eksempel "
        "«felt oppgitt første gang»)."),
    nedlasting.Kolonne(
        "til", "string",
        "Verdien etter, slik ukesiden viser den. Tekst, av samme grunn.",
        "Feltet er ikke oppgitt i dette øyeblikksbildet (for eksempel "
        "«felt ikke lenger oppgitt»)."),
    nedlasting.Kolonne(
        "kommune", "string",
        "Kommunen lokaliteten ligger i, fra Akvakulturregisteret.",
        _UTEN_LOKALITET),
    nedlasting.Kolonne(
        "prodomraade_kode", "string",
        "Produksjonsområdets nummer, 1 til 13. Tekst, fordi det er et "
        "nummer som identifiserer.", _UTEN_LOKALITET),
    nedlasting.Kolonne(
        "prodomraade_navn", "string", "Produksjonsområdets navn.",
        _UTEN_LOKALITET),
)



@lru_cache(maxsize=None)
def _hentet_snapshot(kilde: str, dato: str) -> str:
    """`fetched_at` i nyeste versjon av kildens snapshot for datoen. Tom
    når det ikke finnes eller ikke er stemplet."""
    versjoner = snapshot.versjoner(kilde, dato)
    return (snapshot.fetched_at_i(versjoner[-1][1]) or "") if versjoner else ""


def _ukens_hentet(uke: dict) -> str:
    """Da VI hentet øyeblikksbildet en endringsuke er bygget fra.

    Øyeblikksbildet er ukas SISTE observasjonsdato — den samme datoen
    `proveniens()` navngir. Har flere kilder et snapshot den dagen, er
    det den siste av hentingene. Tom når ingen er stemplet, og da
    utelates leddet framfor å låne et annet tidspunkt.

    ## Feilen dette er rettingen av (08.10.2026)

    Ukesiden sa `felles.akva_hentet` — hentetidspunktet til det NYESTE
    akvakultur-snapshotet. MÅLT i bygget 07.10.2026: /endringer/2026-35/
    og /endringer/2026-41/ sa begge «hentet 5. oktober 2026 kl. 12.07
    UTC». Uke 35 ble hentet 24. august. Et tidspunkt som handler om OSS,
    slått opp på feil sted — CLAUDE.md 1b, samme familie som F6 og F7.
    """
    stempler = [_hentet_snapshot(h["kilde"], h["dato"])
                for h in uke["hendelser"] if h["dato"] == uke["siste_dato"]]
    return max((x for x in stempler if x), default="")


def endringer_datasett(uke: dict, vilkaar=None,
                       bygget: str | None = None) -> nedlasting.Datasett:
    """Ukas hendelser som regneark og datapakke. Samme rader som CSV-en.

    HENTETIDSPUNKTET ER UKAS EGET, per kilde: snapshotet hver hendelse
    ble sett i. Ikke `akva_hentet`, som er det NYESTE øyeblikksbildets —
    for en eldre uke ville det vært et tidspunkt som handler om en annen
    henting enn den raden kom fra.
    """
    bygget = bygget or dt.date.today().isoformat()
    par = sorted({(h["kilde"], h["dato"]) for h in uke["hendelser"]})
    hentet = []
    for kilde in ENDRINGSKILDER:
        stempler = [_hentet_snapshot(k, d) for k, d in par if k == kilde]
        for setning in _hentet_spenn(stempler, kilde):
            hentet.append(setning)
    typer = "; ".join(f"{t['id']}: {t['hva']}" for t in ENDRINGSTYPER)
    return nedlasting.Datasett(
        stamme=endringer_stamme(uke["slug"]),
        tittel=f"Endringer observert i {uke['vist']}",
        beskrivelse=(
            f"{uke['merke']}. {uke['antall_fil']} hendelser i norske "
            f"akvakulturregistre, én rad per endret felt, med "
            f"observasjonsdato {', '.join(uke['datoer'])}. Alle radene i "
            f"uka, ikke bare dem ukesiden viser."),
        kolonner=UKEKOLONNER,
        rader=_ukens_rader(uke),
        kilder=kildelisens(ENDRINGSKILDER),
        attribusjon=attribusjon(ENDRINGSKILDER, vilkaar),
        hentet=hentet,
        bygget=bygget,
        merknader=[
            "«observert» er datoen vi så endringen i øyeblikksbildet, ikke "
            "datoen registeret gjorde den.",
            f"type: {typer}",
        ],
    )


def _ukens_json(uke: dict) -> str:
    """Ukas hendelser som JSON. Samme rader som CSV-en og tabellen."""
    return json.dumps({
        "uke": uke["slug"],
        "vist": uke["vist"],
        "kalenderuke": uke["spenn"],
        "merke": uke["merke"],
        "observasjonsdatoer": uke["datoer"],
        "sammenlignet_mot": uke["forrige_datoer"],
        # FILENS TALL, ikke sidens: sida teller bare de vesentlige.
        "antall": uke["antall_fil"],
        # FILAS RADER, ikke sidens. `hendelser` under er usammenslått
        # (se `slaa_sammen_trukne()`), og typetallene skal summere til
        # radene i samme fil — ikke til tabellen på siden.
        "typer": {k["id"]: n for k in ENDRINGSTYPER
                  for n in [sum(h["type"] == k["id"]
                                for h in uke["hendelser"])]},
        "merknad": ("«observert» er datoen vi så endringen i "
                    "øyeblikksbildet, ikke datoen registeret gjorde den"),
        "kilder": list(attribusjon(ENDRINGSKILDER)),
        "hendelser": [
            {"observert": h["dato"], "type": h["type"], "kilde": h["kilde"],
             "entity_id": h["identitet"],
             # TOM når «gjelder» er VÅR etikett og ikke kildens navn.
             # Se `_ukens_csv()` og `identitet` i `_hendelse()`.
             "entity_name": (h["gjelder"]
                             if h["gjelder_felt"] == "entity_name" else ""),
             "gjelder": h["gjelder"],
             "felt": h["felt"], "fra": h["fra"], "til": h["til"],
             "kommune": h["kommune"], "prodomraade_kode": h["po"],
             "prodomraade_navn": h["po_navn"]}
            for h in uke["hendelser"]],
    }, ensure_ascii=False, indent=1)


ENDRINGSKILDER = ("akvakultur", "biomasselag", "eierskap",
                  "enhetsregisteret")


def _ukens_overskriftstall(uke: dict, valgt: dict | None,
                           rader: list[dict]) -> int:
    """Tallet i ukesidens første setning — og i metabeskrivelsen.

    ETT TALL, TO STEDER. Metabeskrivelsen (og `og:description` og
    søkeindeksen, som leser den) sa `len(hendelser)`: radene i FILA, før
    sammenslåing og med selskapsdata. Uke 41 sa da «158 endringer» i
    søkeresultatet over en side som sa «90 endringer». MÅLT 06.10.2026.

    Ufiltrert side: `antall`, overskriftstallet. Typeside: radene som
    står i tabellen, som er det setningen «N av M rader … er X» teller.
    """
    return len(rader) if valgt else uke["antall"]


def _ukebeskrivelse(uke: dict, valgt: dict | None, rader: list[dict]) -> str:
    """Metabeskrivelsen, med samme tall og samme ord som overskriften."""
    n = _ukens_overskriftstall(uke, valgt, rader)
    if valgt:
        return (f"{n} av {visningsord.antall(uke['antall_rader'], 'rad', 'rader')} "
                f"i {uke['vist']} ({uke['spenn']}) er "
                f"{valgt['navn'].lower()} — norske akvakulturregistre.")
    return (f"{visningsord.antall(n, 'endring', 'endringer')} observert i "
            f"{uke['vist']} ({uke['spenn']}) i norske akvakulturregistre.")


# DIAGRAMMET I HØYRESPALTA på /endringer/: én stolpe per uke, piksler.
UKEDIAGRAM_STOLPE = 8
UKEDIAGRAM_LUFT = 4
UKEDIAGRAM_HOYDE = 20


def ukediagram(uker: list[dict]) -> dict:
    """Endringer per uke og type som små stolperader, til høyrespalta på
    endringsindeksen. Tallene er krysstabellens — `u["typer"]` — og
    tabellen står rett under, så diagrammet legger ikke til én verdi.

    ÉN SKALA PER RAD, og bildeteksten sier det. Diagrammet svarer på
    NÅR en type skjedde; HVOR MYE står som tall ved raden. Med én skala
    for alle ble hver rad unntatt selskapsdata en strek på én piksel —
    MÅLT 09.10.2026: 750 selskapsdata i én uke mot 83 fisk til stede i
    alle sju til sammen. En uke med noe får minst én piksel, så den ikke
    leses som null.

    Typene står i tabellens rekkefølge, så diagram og tabell kan leses
    mot hverandre; en type uten en eneste endring i noen uke er ikke en
    rad. Ukene står eldst til venstre, som i en tidsserie — motsatt av
    tabellen, som har nyeste øverst."""
    eldst_forst = list(reversed(uker))
    per_uke = [{k["id"]: k["antall"] for k in u["typer"]} for u in eldst_forst]
    steg = UKEDIAGRAM_STOLPE + UKEDIAGRAM_LUFT
    rader = []
    for k in ENDRINGSTYPER:
        tallrekke = [d.get(k["id"], 0) for d in per_uke]
        if not sum(tallrekke):
            continue
        maks = max(tallrekke)
        soyler = []
        for i, n in enumerate(tallrekke):
            h = max(1, round(UKEDIAGRAM_HOYDE * n / maks)) if n else 0
            soyler.append({"x": i * steg, "y": UKEDIAGRAM_HOYDE - h, "h": h,
                           "uke": eldst_forst[i]["vist"], "antall": n})
        rader.append({"id": k["id"], "navn": k["navn"],
                      "sum": sum(tallrekke), "soyler": soyler})
    return {"rader": rader,
            "bredde": max(0, len(uker) * steg - UKEDIAGRAM_LUFT),
            "hoyde": UKEDIAGRAM_HOYDE, "stolpe": UKEDIAGRAM_STOLPE,
            "forste": eldst_forst[0]["vist"] if uker else "",
            "siste": eldst_forst[-1]["vist"] if uker else ""}


def skriv_endringssider(rot: Path, felles: Felles,
                        uker: list[dict]) -> list[Path]:
    """Indeksen, ukesidene, typesidene og datafilene."""
    miljo = _miljo()
    uke_mal = miljo.get_template("endringer-uke.html.j2")
    indeks_mal = miljo.get_template("endringer-indeks.html.j2")
    skrevet: list[Path] = []

    def skriv_html(sti: Path, html: str) -> None:
        skrevet.append(skriv_side(sti, html))

    for i, uke in enumerate(uker):
        # NYERE og ELDRE, ikke «neste» og «forrige». Lista er sortert
        # nyest først, så `i - 1` er nyere. To navn som betyr det
        # motsatte av hva indeksen gjør, er en feil som ser riktig ut.
        nyere = uker[i - 1] if i else None
        eldre = uker[i + 1] if i + 1 < len(uker) else None
        mappe = rot / ENDRINGER_STI / uke["slug"]

        for slag in [None] + [k["id"] for k in ENDRINGSTYPER]:
            hendelser = ([h for h in uke["hendelser"] if h["type"] == slag]
                         if slag else uke["hendelser"])
            valgt = next((k for k in ENDRINGSTYPER if k["id"] == slag), None)
            sti = (mappe / slag / "index.html") if slag else (mappe / "index.html")
            url = (f"/{ENDRINGER_STI}/{uke['slug']}/{slag}/" if slag
                   else f"/{ENDRINGER_STI}/{uke['slug']}/")
            tittel = (f"{valgt['navn']} i {uke['vist']}" if valgt
                      else f"Endringer i {uke['vist']}")
            # SELSKAPSDATA STÅR FOR SEG PÅ UKESIDEN. På den ufiltrerte
            # sida deles radene; på en typeside er valget alt gjort, og
            # da er alt ett bord.
            #
            # RADENE ER `les_endringsuker()`s, ikke regnet her på nytt. Der
            # er de slått sammen og delt på klasse, og der er tallene telt
            # av dem. To steder som deler hver for seg, er formen F6 og F7
            # hadde. `uke["hendelser"]` er urørt og går til CSV-en,
            # JSON-en, feeden og JSON-LD-en.
            if slag:
                ledet = [h for h in uke["ledet"] + uke["egen_del"]
                         if h["type"] == slag]
                egen = []
                tekniske = [h for h in uke["tekniske_rader"]
                            if h["type"] == slag]
            else:
                ledet, egen = uke["ledet"], uke["egen_del"]
                tekniske = uke["tekniske_rader"]
            skriv_html(sti, uke_mal.render(
                u=uke, rader=ledet, egen=egen, valgt=valgt, url=url,
                tekniske=tekniske,
                overskriftstall=_ukens_overskriftstall(uke, valgt, ledet),
                nyere=nyere, eldre=eldre, uker_totalt=len(uker),
                # TIDSLINJA FLYTTET HIT 27.09.2026. Den sto på forsiden
                # og bare der, og forsiden viser nå ukas sak i tre
                # setninger og én lenke. Den er ikke slettet: den sier
                # noe ingen annen komponent sier — at KILDEN utga
                # forskriften på én dato og VI observerte den i
                # registeret på en annen. CLAUDE.md 1b-7.
                #
                # Den regnes PER UKE. På forsiden gjaldt den alltid
                # nyeste uke; her får hver uke sin egen, og
                # `_forskriftslinje()` gir `None` for de ukene som ikke
                # har en trafikklysendring å knytte den til — og for
                # dem som ligger FØR utgivelsen, der koblingen ville
                # vært usann.
                forskriftslinje=_forskriftslinje(felles, uke),
                siter={"url": _basisurl() + url,
                       "uke": uke["vist"], "aar": uke["aar"],
                       "spenn": uke["merke"],
                       "sjekksum": felles.sjekksum},
                **_grunnkontekst(
                    felles, rot, sti, kilder=ENDRINGSKILDER,
                    tittel=f"{tittel} — Kystloggen",
                    beskrivelse=_ukebeskrivelse(uke, valgt, ledet),
                    jsonld=_jsonld_uke(uke, hendelser, felles.vilkaar, url),
                    proveniens_tekst=proveniens(
                        uke["siste_dato"], _ukens_hentet(uke),
                        f"Sammenligning av øyeblikksbildene for "
                        f"{uke['vist']} og uka før."),
                    meny_aktiv="endringer",
                    sidetype="Endringsuke",
                    undertittel=(f"{valgt['navn']}{SKILLE}{uke['merke']}"
                                 if valgt else uke["merke"]),
                    soketekst=uke["vist"],
                    main_klasse="fullbredde",
                    feed="/endringer/feed.xml",
                    feed_tittel="Kystloggen: alle endringer")))

        # DATAFILENE ligger i UKAS egen mappe, ved siden av siden —
        # samme regel som lusetall-CSV-en (url-struktur punkt 8).
        #
        # `endringer.csv` er ikke lenger lenket fra siden; regnearket og
        # datapakken har tatt plassen. Den skrives likevel: adressen er
        # gitt ut, og den skal fortsette å svare.
        ds = endringer_datasett(uke, felles.vilkaar)
        for navn, innhold in (("endringer.csv", _ukens_csv(uke).encode()),
                              ("endringer.json", _ukens_json(uke).encode()),
                              (ds.xlsx_navn, nedlasting.xlsx_bytes(ds)),
                              (ds.zip_navn, nedlasting.zip_bytes(ds))):
            fil = mappe / navn
            fil.parent.mkdir(parents=True, exist_ok=True)
            fil.write_bytes(innhold)
            skrevet.append(fil)

    sti = rot / ENDRINGER_STI / "index.html"
    skriv_html(sti, indeks_mal.render(
        uker=uker,
        totalt=sum(u["antall"] for u in uker),
        typer=ENDRINGSTYPER,
        diagram=ukediagram(uker),
        analyse=_forside_unntak(felles),
        utenfor=(uker[0]["utenfor_uka"] if uker else 0),
        **_grunnkontekst(
            felles, rot, sti, kilder=ENDRINGSKILDER,
            tittel="Alle endringsuker — Kystloggen",
            beskrivelse=("Hver uke vi har observert endringer i de norske "
                         "akvakulturregistrene, med antall per uke."),
            jsonld=_script_trygg({
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "Alle endringsuker",
                "inLanguage": "nb",
            }),
            proveniens_tekst=proveniens(felles.akva_dato,
                                        felles.akva_hentet),
            meny_aktiv="endringer",
            sidetype="Liste",
            undertittel=f"{len(uker)} uker med observerte endringer",
            main_klasse="fullbredde",
            feed="/endringer/feed.xml",
            feed_tittel="Kystloggen: alle endringer")))
    return skrevet


def _jsonld_uke(uke: dict, rader: list[dict], vilkaar: dict,
                url: str) -> Markup:
    """schema.org/Dataset for én endringsuke."""
    kilder = []
    for kilde in ENDRINGSKILDER:
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
        "name": f"Endringer i norske akvakulturregistre, {uke['vist']}",
        "description": (
            f"{len(rader)} registerendringer observert i {uke['vist']} "
            f"({uke['spenn']}), sammenlignet med forrige øyeblikksbilde."),
        "inLanguage": "nb",
        "temporalCoverage": f"{uke['forste_dato']}/{uke['siste_dato']}",
        "dateModified": uke["siste_dato"],
        "isBasedOn": kilder,
        "creator": {"@type": "Organization", "name": "Kystloggen"},
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": XLSX_MIME,
             "contentUrl": uke["xlsx_filnavn"]},
            {"@type": "DataDownload", "encodingFormat": "application/zip",
             "contentUrl": uke["zip_filnavn"]},
            {"@type": "DataDownload", "encodingFormat": "application/json",
             "contentUrl": "endringer.json"},
        ],
    })


# ------------------------------------------------------------ FEEDENE
#
# Atom, og ikke RSS. Atom har en definert `id` per post og krever
# `updated` — to ting en changelog-rad faktisk har, og som RSS bare har
# som konvensjoner.
#
# ## EN FEED PER ENTITET, i entitetens EGEN mappe
#
#     /endringer/feed.xml                 alt
#     /lokalitet/<nr>/feed.xml            én lokalitet
#     /produksjonsomrade/<nr>/feed.xml    ett område
#     /selskap/<orgnr>/feed.xml           ett selskap
#
# Samme begrunnelse som for CSV-en (2026-09-16-url-struktur.md punkt 8):
# fila arver identiteten fra stien den ligger i, og mappa er
# selvstendig. Kopierer noen `/lokalitet/31397/`, følger siden, tallene
# og feeden med.
#
# ## TIDSPUNKTET I `updated` ER EN DATO, og klokkeslettet er ikke data
#
# Atom krever RFC 3339 — altså et klokkeslett. Changeloggen har en
# DATO: `observed_at` er dagen vi kjørte innsamlingen, og timen står
# ikke i raden. Vi skriver `T00:00:00Z`, og feedens `subtitle` sier at
# klokkeslettet er utfylling og ikke en opplysning.
#
# Alternativet var å slå opp `fetched_at` for hvert (kilde, dato)-par,
# som ville krevd å lese alle snapshots av alle kilder. Det er et ekte
# tidspunkt, og det er en reell forbedring — den står i
# docs/APNE-SPORSMAL.md.

ATOM_NS = "http://www.w3.org/2005/Atom"

# Hvor mange poster en feed bærer. En feed uten tak vokser til den
# ikke lastes; 50 er omtrent et halvår for en aktiv lokalitet og hele
# historikken for en rolig.
FEEDPOSTER = 50


def _xml(tekst: object) -> str:
    """Tekst som kan stå i et XML-element."""
    from xml.sax.saxutils import escape
    return escape("" if tekst is None else str(tekst))


def atomfeed(*, tittel: str, sti: str, undertittel: str,
             poster: list[dict], oppdatert: str) -> str:
    """En Atom-feed som tekst.

    `poster` er dicts med `id`, `tittel`, `dato`, `url` og `innhold`.
    `id` må være STABIL: den er postens identitet for enhver leser, og
    en id som endrer seg mellom to bygg gjør hver gamle post ulest på
    nytt.
    """
    basis = _basisurl()
    feed_url = basis + sti
    linjer = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<feed xmlns="{ATOM_NS}" xml:lang="nb">',
        f"  <title>{_xml(tittel)}</title>",
        f"  <subtitle>{_xml(undertittel)}</subtitle>",
        f"  <id>{_xml(feed_url)}</id>",
        f'  <link rel="self" type="application/atom+xml" '
        f'href="{_xml(feed_url)}"/>',
        f'  <link rel="alternate" type="text/html" '
        f'href="{_xml(basis + sti.rsplit("/", 1)[0] + "/")}"/>',
        f"  <updated>{_xml(oppdatert)}</updated>",
        "  <author><name>Kystloggen</name></author>",
        f"  <generator uri=\"{_xml(REPO)}\">Kystloggen</generator>",
    ]
    for post in poster:
        linjer += [
            "  <entry>",
            f"    <title>{_xml(post['tittel'])}</title>",
            f"    <id>{_xml(post['id'])}</id>",
            f'    <link rel="alternate" type="text/html" '
            f'href="{_xml(basis + post["url"])}"/>',
            f"    <updated>{_xml(post['dato'])}T00:00:00Z</updated>",
            f'    <content type="text">{_xml(post["innhold"])}</content>',
            "  </entry>",
        ]
    linjer.append("</feed>")
    return "\n".join(linjer) + "\n"


def _feedpost(h: dict, sti: str) -> dict:
    """Én hendelse som en Atom-post.

    IDEN ER SAMMENSATT AV DET SOM GJØR HENDELSEN UNIK: sti, dato, kilde
    og felt. Ingen tilfeldighet, ingen teller, ingen hash — en id som
    ikke kan regnes ut på nytt av de samme dataene er en id som endrer
    seg neste gang noe bygges om.
    """
    # `identitet` og ikke `entity_id`: en feed-id er en publisert
    # streng, og den skal ikke bære et nummer vi ikke kan gå god for.
    # Se `identitet` i `_hendelse()`.
    nøkkel = (f"{h['dato']}/{h['kilde']}/{h['identitet'] or 'uten-identitet'}"
              f"/{h['felt']}")
    verdi = (f"{h['etikett']}: {h['fra']} → {h['til']}"
             if h["fra"] or h["til"] else h["etikett"])
    sted = " · ".join(x for x in (h["kommune"],
                                  f"produksjonsområde {h['po']}" if h["po"]
                                  else "") if x)
    return {
        "id": f"{_basisurl()}{sti}#{nøkkel}",
        "tittel": f"{h['gjelder']}: {verdi}",
        "dato": h["dato"],
        "url": h["gjelder_url"] or sti.rsplit("/", 1)[0] + "/",
        "innhold": (f"{verdi}. Observert {visningsord.dato(h['dato'])} "
                    f"i {h['kilde']}."
                    + (f" {sted}." if sted else "")),
    }


def skriv_feeder(rot: Path, felles: Felles, uker: list[dict]) -> list[Path]:
    """Feedene: nettstedets, hver lokalitets, hvert områdes, hvert selskaps.

    Bygges av de SAMME ukene endringssidene bygges av. To veier til det
    samme regnskapet er formen F6 og F7 hadde — og for en feed er
    prisen at en leser får en post som ikke finnes på siden.
    """
    alle = [h for u in uker for h in u["hendelser"]]
    alle.sort(key=lambda h: h["dato"], reverse=True)
    skrevet: list[Path] = []
    i_dag = dt.date.today().isoformat()

    def skriv(sti: str, tittel: str, undertittel: str,
              hendelser: list[dict]) -> None:
        ut = rot / sti.lstrip("/")
        ut.parent.mkdir(parents=True, exist_ok=True)
        poster = [_feedpost(h, sti) for h in hendelser[:FEEDPOSTER]]
        oppdatert = ((poster[0]["dato"] if poster else i_dag) + "T00:00:00Z")
        ut.write_text(atomfeed(tittel=tittel, sti=sti,
                               undertittel=undertittel, poster=poster,
                               oppdatert=oppdatert), encoding="utf-8")
        skrevet.append(ut)

    note = ("Klokkeslettet i hver post er utfylling: changeloggen har en "
            "dato, ikke et tidspunkt. Datoen er når VI så endringen — "
            "registeret oppgir ikke når det gjorde den.")

    skriv("/endringer/feed.xml", "Kystloggen: alle endringer",
          f"Registerendringer observert i ukentlige øyeblikksbilder. {note}",
          alle)

    per_lokalitet: dict[str, list[dict]] = defaultdict(list)
    per_po: dict[str, list[dict]] = defaultdict(list)
    per_selskap: dict[str, list[dict]] = defaultdict(list)
    for h in alle:
        if h["gjelder_slag"] == "lokalitet":
            per_lokalitet[h["entity_id"]].append(h)
        elif h["gjelder_slag"] == "selskap":
            per_selskap[h["entity_id"]].append(h)
        if h["po"]:
            per_po[h["po"]].append(h)

    # EN FEED FOR HVER ENTITET SOM HAR EN SIDE, også de uten en eneste
    # endring. En feed som mangler er en 404 der leseren tror det er en
    # feil hos dem; en tom feed sier «ingenting har skjedd», som er et
    # svar. Samme regel som at CSV-en skrives med null rader.
    for loknr in felles.akva:
        navn = visningsord.tittelform(felles.akva[loknr].get("navn", ""))
        skriv(f"/lokalitet/{loknr}/feed.xml",
              f"Kystloggen: {navn or loknr}",
              f"Registerendringer for akvakulturlokalitet {loknr}. {note}",
              per_lokalitet.get(loknr, []))

    for po in felles.po_navn:
        skriv(f"/produksjonsomrade/{po}/feed.xml",
              f"Kystloggen: produksjonsområde {po} {felles.po_navn[po]}",
              f"Endringer i lokalitetene i produksjonsområde {po}. {note}",
              per_po.get(po, []))

    for orgnr in felles.tillatelser_per_eier:
        if personeier(orgnr, felles):
            continue
        navn = (felles.enhet.get(orgnr) or {}).get("navn", "") or orgnr
        skriv(f"/selskap/{orgnr}/feed.xml", f"Kystloggen: {navn}",
              f"Register- og eierskapsendringer for organisasjonsnummer "
              f"{orgnr}. {note}",
              per_selskap.get(orgnr, []))
    return skrevet


# ---------------------------------------------------------- SØKET
#
# Pagefind, selvhostet. Indeksen bygges av en binær ved bygging og
# legges i `/pagefind/`; modulen lastes av `/sok.js` i nettleseren ved
# FØRSTE TASTETRYKK, ikke ved sidelast.
#
# ## Hvorfor søket er JavaScript når ingenting annet er det
#
# Regelen er at TALLENE skal stå i kildekoden. Et søkeresultat er ikke
# et tall fra et register — det er en vei til siden der tallet står, og
# den siden er statisk HTML som kan siteres og arkiveres.
#
# Et søk over 2 337 sider som skal svare uten en server, MÅ kjøre i
# nettleseren. Alternativet er ingen søk. `/sok/` har derfor en
# veiviser til de tre flate indeksene, og den står der uansett.
#
# ## BINÆREN ER IKKE I REPOET
#
# 15,6 MB, og plattformspesifikk. Den er et VERKTØY, som `fonttools` og
# `pyftsubset` — ikke en avhengighet siden har i runtime. Den finnes på
# `PATH` eller i `HAVBRUK_PAGEFIND`.
#
# MANGLER DEN, SIER BYGGET DET. Siden `/sok/` skrives uansett og virker
# uten indeksen (veiviseren står der), men byggerapporten skal ikke
# tie: et søk som stille slutter å virke er nøyaktig formen på feilene
# i CLAUDE.md 1b.
#
# Og det stopper ikke der: `publiser.py` steg 4 NEKTER å legge ut til
# produksjon uten indeks, fordi en linje i en byggerapport er lest av
# ingen den dagen noen har det travelt. Til forhåndsvisning blir det en
# advarsel. Se `publiser.krev_sokeindeks()`.

PAGEFIND_KATALOG = "pagefind"

# FILENE PAGEFIND LEGGER IGJEN SOM VI IKKE BRUKER. Vi skriver vår egen
# søke-UI i `maler/sok.js` og laster bare `pagefind.js`; de ferdige
# grensesnittene er 120 kB kode ingen kjører.
#
# De slettes framfor å bli liggende, av samme grunn som at en font
# ingen viser til ikke sendes ut: en fil på nettstedet er en fil noen
# kan laste ned, og hver av dem må porten gå god for.
PAGEFIND_UBRUKT = (
    "pagefind-ui.js", "pagefind-ui.css",
    "pagefind-modular-ui.js", "pagefind-modular-ui.css",
    "pagefind-highlight.js",
)


def _pagefind_binaer() -> str:
    """Stien til pagefind-binæren, eller tom streng."""
    import shutil
    satt = (os.environ.get("HAVBRUK_PAGEFIND") or "").strip()
    if satt:
        return satt if Path(satt).exists() else ""
    return shutil.which("pagefind") or ""


def skriv_sokeindeks(rot: Path) -> dict:
    """Bygger Pagefind-indeksen over det ferdige nettstedet.

    KJØRES SIST, etter at hver side er skrevet: den leser HTML-en fra
    disk. Returnerer en rapport — byggeloggen skriver den, også når
    indeksen IKKE ble bygget.
    """
    import subprocess

    binaer = _pagefind_binaer()
    if not binaer:
        return {"bygget": False, "filer": 0, "byte": 0,
                "melding": ("pagefind-binæren ble ikke funnet (verken i "
                            "HAVBRUK_PAGEFIND eller på PATH). Søkesiden "
                            "er skrevet og veiviseren virker, men "
                            "søkefeltet svarer ikke.")}
    # KATALOGEN TØMMES FØRST. Pagefind skriver filnavn med en hash i,
    # så en kjøring over et endret nettsted legger NYE filer ved siden
    # av de gamle framfor å erstatte dem. MÅLT: to kjøringer ga 5 117
    # filer og 32,3 MB der én gir 2 568 og 21 MB — og halvparten var en
    # indeks over sider som ikke fantes lenger.
    #
    # Dette er det ENE stedet nettstedsbyggeren sletter noe den selv har
    # skrevet, og det er trygt av samme grunn som at hele mappa kan
    # slettes: den er en ren funksjon av snapshotene. Append-only
    # gjelder `data/raw/`, ikke utputtet — se
    # 2026-08-17-append-only-i-skrivelaget.md.
    import shutil as _shutil
    _shutil.rmtree(rot / PAGEFIND_KATALOG, ignore_errors=True)

    try:
        kjort = subprocess.run(
            [binaer, "--site", str(rot), "--output-subdir", PAGEFIND_KATALOG],
            capture_output=True, text=True, timeout=600, check=False)
    except OSError as feil:
        return {"bygget": False, "filer": 0, "byte": 0,
                "melding": f"pagefind kunne ikke kjøres: {feil}"}
    if kjort.returncode != 0:
        return {"bygget": False, "filer": 0, "byte": 0,
                "melding": (f"pagefind avsluttet med {kjort.returncode}: "
                            f"{(kjort.stderr or kjort.stdout).strip()[:300]}")}

    katalog = rot / PAGEFIND_KATALOG
    for navn in PAGEFIND_UBRUKT:
        (katalog / navn).unlink(missing_ok=True)

    filer = [f for f in katalog.rglob("*") if f.is_file()]
    sider = ""
    for linje in (kjort.stdout or "").splitlines():
        if "Indexed" in linje and "pages" in linje:
            sider = linje.strip()
    return {"bygget": True, "filer": len(filer),
            "byte": sum(f.stat().st_size for f in filer),
            "melding": sider or "indeksen er bygget"}


def bygg_sok(felles: Felles, uker: list[dict]) -> dict:
    """Tallene søkesiden oppgir. Målt, ikke skrevet."""
    selskaper = sum(1 for o in felles.tillatelser_per_eier
                    if not personeier(o, felles))
    lokaliteter = len(felles.akva)
    omraader = len(felles.po_navn)
    endringsuker = len(uker)
    # DE ANDRE SIDENE, telt og ikke gjettet: forsiden, /om/, /sok/, de
    # tre indeksene med sine sider, endringsindeksen og typesidene.
    indekser = 1 + indekssider(lokaliteter) + indekssider(selskaper)
    andre = 1 + 1 + 1 + indekser + 1 + endringsuker * len(ENDRINGSTYPER)
    return {
        "lokaliteter": lokaliteter,
        "produksjonsomraader": omraader,
        "selskaper": selskaper,
        "endringsuker": endringsuker,
        "andre": andre,
        "sider": lokaliteter + omraader + selskaper + endringsuker + andre,
        "per_side": INDEKS_PER_SIDE,
    }


def skriv_sok(rot: Path, felles: Felles, uker: list[dict]) -> Path:
    """Søkesiden. Skrives ALLTID, også uten en søkeindeks."""
    d = bygg_sok(felles, uker)
    sti = rot / "sok" / "index.html"
    mal = _miljo().get_template("sok.html.j2")
    html = mal.render(
        d=d,
        **_grunnkontekst(
            felles, rot, sti, kilder=FORSIDEKILDER,
            tittel="Søk — Kystloggen",
            beskrivelse=(f"Søk i {d['sider']} sider om norsk akvakultur: "
                         f"lokaliteter, produksjonsområder, selskaper og "
                         f"endringsuker."),
            jsonld=_script_trygg({
                "@context": "https://schema.org",
                "@type": "SearchResultsPage",
                "name": "Søk i Kystloggen",
                "inLanguage": "nb",
            }),
            proveniens_tekst=proveniens(felles.akva_dato, felles.akva_hentet),
            meny_aktiv="sok", side_skript="/sok.js",
            sidetype="Søk", undertittel=f"{d['sider']} sider"))
    return skriv_side(sti, html)


# ------------------------------------------- sitemap, robots, llms
#
# ## Domenet er avgjort (21.09.2026): kystloggen.no
#
# Fram til i dag sto det ingen standard her, og begrunnelsen var god:
# `sitemap.xml` krever ABSOLUTTE URL-er, vi hadde ikke noe vertsnavn, og
# et påfunnet domene er en påstand om noe som ikke er avgjort. Se
# docs/beslutninger/2026-09-16-url-struktur.md, som lar være å oppgi
# `url` i JSON-LD-en av nøyaktig samme grunn.
#
# Premisset er borte. Navnet og domenet er bestemt, og da er det ikke
# lenger varsomhet å utelate det — det er en sitemap som ikke duger for
# en søkemotor, hver eneste kjøring, til noen husker en miljøvariabel.
#
# `HAVBRUK_BASEURL` overstyrer fortsatt, og det er ikke en rest: en
# kopi som serveres et annet sted (en forhåndsvisning, et speil) skal
# ikke fortelle en crawler at den er originalen. Variabelen heter
# fortsatt `HAVBRUK_*` som `HAVBRUK_DATA_DIR`, fordi navnerommet
# tilhører REPOET og ikke nettstedet — og fordi en omdøping ville
# stoppet hver cron-jobb som allerede setter den.
#
# Settes den til tom streng EKSPLISITT, faller fila tilbake til
# relative stier med forklaringen i seg. Det er ikke det samme som at
# den er usatt, og skillet er med vilje: «jeg vet ikke hvor dette skal
# ligge» er en tilstand som fortsatt finnes.

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# Robotene som leter etter sitt EGET navn i robots.txt.
#
# Alle er dekket av `User-agent: *`, og står likevel her — se
# `skriv_robots()`. Lista er de agentene som er dokumentert av sine
# egne operatører per 23.09.2026, gruppert etter hva de gjør, fordi
# det er skillet en leser vil vite om:
#
#   søk       henter en side fordi noen spurte om noe nå
#   trening   henter en side for å bygge en modell
#   agent     henter en side på vegne av én bruker, der og da
#
# Vi skiller ikke på dem. Gruppene står som kommentar fordi den som
# senere VIL skille skal se hvilke navn som hører sammen.
AI_ROBOTER = (
    # OpenAI: søk, trening, agent
    "OAI-SearchBot", "GPTBot", "ChatGPT-User",
    # Anthropic: søk, trening, agent
    "ClaudeBot", "Claude-SearchBot", "Claude-User", "anthropic-ai",
    # Google
    "Google-Extended", "GoogleOther",
    # Microsoft / Bing
    "bingbot", "msnbot",
    # Perplexity
    "PerplexityBot", "Perplexity-User",
    # Apple, Amazon, Meta, ByteDance, Common Crawl, Mistral, You.com
    "Applebot", "Applebot-Extended", "Amazonbot", "meta-externalagent",
    "FacebookBot", "Bytespider", "CCBot", "MistralAI-User", "YouBot",
    # Internet Archive — ikke AI, men samme grunn til å stå her:
    # et arkiv som ikke kan arkiveres er et arkiv med ett punkt som
    # kan svikte.
    "ia_archiver", "archive.org_bot",
)

# Domenet nettstedet publiseres på. Én streng, ett sted.
BASEURL = "https://kystloggen.no"


def _basisurl() -> str:
    """Vertsnavnet sidene skal ligge på, eller tom streng.

    Leses ved KALL og ikke ved import, så en test kan sette den uten å
    laste modulen på nytt — samme grunn som `_http.brukeragent()`.
    """
    import os
    satt = os.environ.get("HAVBRUK_BASEURL")
    if satt is None:
        return BASEURL
    return satt.strip().rstrip("/")


def _urler(felles: Felles) -> list[str]:
    """Hver publiserte side, som sti. Rekkefølgen er lesningens.

    Lusetall-CSV-ene står ikke her: en sitemap er sider, ikke
    nedlastinger, og hver CSV er lenket fra sin egen lokalitetsside.
    """
    stier = ["/", "/om/", "/lokalitet/", "/produksjonsomrade/", "/selskap/"]
    # ANALYSESIDEN bare når den bygges — samme vilkår som skriv_alle().
    if felles.unntak:
        stier.append("/" + "/".join(UNNTAK_STI) + "/")
    # INDEKSENES ØVRIGE SIDER. Samme deling som `skriv_indekser()`.
    selskaper = sum(1 for o in felles.tillatelser_per_eier
                    if not personeier(o, felles))
    for sti, n in (("lokalitet", len(felles.akva)), ("selskap", selskaper)):
        stier += [indekssti(sti, k) for k in range(2, indekssider(n) + 1)]
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
            "<!-- HAVBRUK_BASEURL er satt til tom streng, så <loc> er "
            "RELATIVE stier. Sitemap-spesifikasjonen krever absolutte "
            "URL-er: bygg på nytt med variabelen usatt (da brukes "
            "nettstedets eget domene) eller satt til vertsnavnet denne "
            "kopien faktisk ligger på. -->")
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
    """robots.txt. Alt er åpent; det er poenget med å publisere det.

    ## Denne fila er ENESTE kilde til robotregler

    Cloudflare kan sette robotregler for et nettsted uten å røre
    `robots.txt` — «Bot Preference Sync» og liknende. Den er slått av
    med vilje: to steder som kan si ulike ting om hvem som slipper inn,
    er formen F6 og F7 hadde, og her ville det ene stedet vært en
    innstilling i et kontrollpanel ingen leser i koden.

    Er du usikker på om noe er skrudd på: det som står i denne fila er
    det vi MENER, og et avvik er en feil i oppsettet.

    ## AI-roboter nevnes ved navn, og får JA

    `User-agent: *` dekker dem alt. De står likevel oppført, fordi et
    fravær leses som et forbehold: flere av dem er laget for å lete
    etter en egen regel, og en operatør som leter i fila skal finne et
    svar og ikke en tolkning.

    Dette er ikke en tilfeldig raushet. Nettstedet er offentlige
    registerdata, sammenstilt og datert, og et arkiv som ikke kan leses
    av det folk faktisk bruker til å slå opp er et arkiv færre finner.
    Persondata holdes ute ved KILDEN og i lesedøra — ikke ved å nekte
    noen å lese sidene.
    """
    basis = _basisurl()
    linjer = [
        "# Kystloggen — offentlige registerdata, fritt tilgjengelige.",
        "# Sidene er statiske og tåler å bli indeksert i sin helhet.",
        "#",
        f"# Denne fila er ENESTE kilde til robotregler for "
        f"{basis or 'dette nettstedet'}.",
        "# Cloudflares «Bot Preference Sync» er slått AV.",
        "User-agent: *",
        "Allow: /",
        "",
        "# AI-søk, AI-agenter og AI-trening: ja, alt sammen.",
        "# «*» over dekker dem, men de står oppført fordi et fravær",
        "# leses som et forbehold.",
    ]
    for robot in AI_ROBOTER:
        linjer += [f"User-agent: {robot}", "Allow: /", ""]
    if basis:
        linjer.append(f"Sitemap: {basis}/sitemap.xml")
    else:
        linjer += [
            "# Sitemap-linja krever en absolutt URL. HAVBRUK_BASEURL er",
            "# satt til tom streng for denne byggingen — bygg på nytt",
            "# uten den for å få nettstedets eget domene.",
            "# Sitemap: https://<domene>/sitemap.xml",
        ]
    ut = rot / "robots.txt"
    ut.write_text("\n".join(linjer) + "\n", encoding="utf-8")
    return ut


# ------------------------------------------------ filer for verten
#
# `_redirects` og `_headers` er Cloudflare Pages' eget format, og de
# ligger i publiseringsmappa fordi det er DER de hører hjemme: en
# innstilling i et kontrollpanel er en innstilling ingen ser i et
# kodeopptak. Samme begrunnelse som robots.txt — se `skriv_robots()`.
#
# Filene starter med understrek og serveres ikke. Cloudflare leser dem
# og fjerner dem fra utputtet.

# Hodene som gjelder ALT. Verdien er én linje per hode.
#
# ## CSP-en kan være så streng som den er fordi siden er så enkel
#
# MÅLT 23.09.2026 over alle 2 348 sidene: NULL eksterne forespørsler.
# Fontene, ikonene, herofotoet, skriptene og søkeindeksen hostes av
# oss. Da er `'self'` ikke en innstramming som koster noe — det er en
# beskrivelse av det som allerede er sant, håndhevet.
#
# `'unsafe-inline'` for stil står der fordi SVG-ene i kartet og grafene
# bærer `fill`-attributter og fordi `<details>`-delen bruker `hidden`.
# Ingen inline `<style>`-blokk finnes, men attributtene teller.
# Skriptene har INGEN slik åpning: `kystloggen.js` og `sok.js` er
# eksterne filer, og en inline `<script>` skal ikke kunne snike seg
# inn uten at dette hodet må endres først.
#
# `wasm-unsafe-eval` er Pagefind. Uten den laster ikke søkemotoren.
VERTSHODER = (
    ("Content-Security-Policy",
     "default-src 'self'; "
     "script-src 'self' 'wasm-unsafe-eval'; "
     "style-src 'self' 'unsafe-inline'; "
     "img-src 'self' data:; "
     "font-src 'self'; "
     "connect-src 'self'; "
     "form-action 'self'; "
     "frame-ancestors 'none'; "
     "base-uri 'none'; "
     "object-src 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    # Ingen av sidene ber om kamera, mikrofon eller posisjon. Å si det
    # koster ingenting og fjerner en hel klasse spørsmål.
    ("Permissions-Policy", "geolocation=(), camera=(), microphone=()"),
)

# Per filtype: (mønster, [(hode, verdi)]).
#
# ## Content-Type står her fordi verten gjetter
#
# Cloudflare Pages gjetter på filendelsen. `.xml` blir `text/xml` uten
# tegnsett, og en Atom-feed med «Ø» i et selskapsnavn leses da som
# latin-1 av enkelte lesere. `.csv` blir `text/csv` uten tegnsett, med
# samme utfall i et regneark.
#
# Dette er ikke teoretisk for oss: 2 277 feeder og 1 787 CSV-er, og
# nesten hvert eneste norske stedsnavn har en æøå i seg.
VERTSFILHODER = (
    ("/*.xml", (("Content-Type", "application/atom+xml; charset=utf-8"),)),
    ("/*.csv", (("Content-Type", "text/csv; charset=utf-8"),)),
    ("/*.json", (("Content-Type", "application/json; charset=utf-8"),)),
    ("/*.txt", (("Content-Type", "text/plain; charset=utf-8"),)),
    # Fonter og bilder er UFORANDERLIGE: filnavnet bærer innholdet, og
    # et nytt innhold får et nytt navn. Ett år, og `immutable` så
    # nettleseren ikke engang spør.
    ("/*.woff2", (("Cache-Control", "public, max-age=31536000, immutable"),)),
    ("/bilde/*", (("Cache-Control", "public, max-age=31536000, immutable"),)),
    # Søkeindeksen skrives på nytt hver uke med nye filnavn (hashet av
    # Pagefind), så den tåler det samme.
    ("/pagefind/*", (("Cache-Control", "public, max-age=31536000, immutable"),)),
)


def skriv_vertsfiler(rot: Path) -> Path:
    """`_redirects` og `_headers` for Cloudflare Pages.

    Returnerer `_headers`; begge skrives.
    """
    # OMDIRIGERINGEN UTLEDES AV VERTSNAVNET, ikke skrevet av.
    #
    # En forhåndsvisning på pages.dev har ingen www-variant, og en
    # regel som pekte dit ville sendt leseren til et domene siden ikke
    # ligger på. Tomt vertsnavn gir ingen regel.
    basis = _basisurl()
    vert = basis.split("://", 1)[-1] if basis else ""
    if vert and not vert.startswith("www."):
        regel = (f"https://www.{vert}/* {basis}/:splat 301\n")
    else:
        regel = "# Ingen omdirigering: vertsnavnet er ikke satt.\n"
    (rot / "_redirects").write_text(
        "# www -> uten www, permanent.\n"
        "#\n"
        "# 301 og ikke 302: adressen uten www ER adressen, og en\n"
        "# midlertidig omdirigering ville latt søkemotorer beholde\n"
        "# begge som separate sider.\n" + regel,
        encoding="utf-8")

    linjer = ["# Hoder for Cloudflare Pages. Skrevet av nettsted.py —",
              "# endre der, ikke her.", "", "/*"]
    linjer += [f"  {navn}: {verdi}" for navn, verdi in VERTSHODER]
    for monster, hoder in VERTSFILHODER:
        linjer += ["", monster]
        linjer += [f"  {navn}: {verdi}" for navn, verdi in hoder]
    ut = rot / "_headers"
    ut.write_text("\n".join(linjer) + "\n", encoding="utf-8")
    return ut


def skriv_404(rot: Path, felles: Felles) -> Path:
    """404-siden, i samme drakt som resten.

    Cloudflare Pages serverer `/404.html` for alt som ikke finnes.

    Siden GJETTER IKKE hva leseren lette etter. Et lokalitetsnummer som
    ikke finnes kan være nedlagt, feilskrevet eller utenfor utvalget
    vårt, og en side som tipper ville tatt feil oftest der det betyr
    mest. Den peker på de tre flate listene og på søket.
    """
    sti = rot / "404.html"
    html = _miljo().get_template("404.html.j2").render(
        d={"lokaliteter": len(felles.akva),
           "produksjonsomraader": len(felles.po_navn),
           "selskaper": len(felles.tillatelser_per_eier)},
        **_grunnkontekst(
            felles, rot, sti, kilder=FORSIDEKILDER,
            tittel="Siden finnes ikke — Kystloggen",
            beskrivelse="Adressen finnes ikke på Kystloggen. "
                        "Her er listene og søket.",
            jsonld="", proveniens_tekst="", meny_aktiv=""))
    return skriv_side(sti, html)


def skriv_llms(rot: Path, felles: Felles) -> Path:
    """llms.txt — hva dette er, og hvor de fullstendige listene er.

    Peker på INDEKSENE og /om/, ikke på 1782 enkeltsider. En modell som
    følger fila skal finne alt på tre hopp, og en fil med 1782 lenker
    ville vært den samme lista som sitemap.xml, bare dårligere.
    """
    om = bygg_om(felles)
    basis = _basisurl()
    u = (lambda sti: basis + sti) if basis else (lambda sti: sti)
    tekst = f"""# Kystloggen

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
- [Alle innehavere]({u('/selskap/')}): innehaverne av minst én
  akvakulturtillatelse.

## Om kilder, metode og sitering

- [Om Kystloggen]({u('/om/')}): kildene med lisens og ordrett
  attribusjon, hvor ofte det samles inn, hva dekningen er, hva som
  bevisst ikke hentes, og en ferdig formatert referanse.
- [Kildekode og beslutningslogg]({om['repo']}): hver beslutning er
  skrevet ned med hva som ville snudd den, og hver terskel er målt.

## Sitering

{om['forfatter']} ({om['bygget'][:4]}). Kystloggen: sammenstilte
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
    "unntaksvekst": ("uten vern, åndsverkloven § 14",
                     "lovdata.no/lov/2018-06-15-40/§14", "09.10.2026"),
    "reguleringsomraader": ("CC BY 4.0", "doi.org/10.21335/NMDC-1923112433",
                            "14.09.2026"),
    # «ikke dokumentert», ikke «UBELAGT». Cellen leses av et menneske,
    # og arbeidsordet vårt er ikke et ord en leser kjenner. Verdien
    # betyr det samme: `ubelagte()` leser `vilkaar`, ikke denne strengen.
    "ekspertgruppen": ("ikke dokumentert", "ingen funnet",
                       "14.09.2026 (søkt)"),
}

# HVOR KILDEN SELV BOR. Bare der en leser trenger å komme videre, og
# bare adresser som står i kildens eget notat — en URL vi ikke har lest,
# er et gjett på en tredjeparts vegne (CLAUDE.md regel 4).
#
# I dag én: `ekspertgruppen` er den eneste kilden uten dokumentert
# lisens, og /om/ navngir den. Adressen er publikasjonssiden notatet
# viser til.
KILDE_URL = {
    "ekspertgruppen":
        "https://trafikklyssystemet.no/Publikasjoner/Ekspertgrupperapporter",
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
            # UTLEDET av hva byggene oppgir, ikke skrevet for hånd.
            # Se `viste_kilder()`.
            "publiseres": navn in viste_kilder(),
        })

    kontakt = _kontakt()

    return {
        "lokaliteter": total,
        "med_eier": med_eier,
        "dekning": round(med_eier / total * 100, 2) if total else 0.0,
        "uten_eier": len(uten),
        "uten_eier_med_tillatelse": len(oppgitt_likevel),
        "uten_tillatelse_noe_sted": len(uten) - len(oppgitt_likevel),
        "kilder": kilder,
        # NAVN OG LENKE, ikke det interne kildenavnet. «ekspertgruppen»
        # er mappa i data/raw; en leser som ser det, ser vårt
        # arbeidsnavn. Adressen står i `KILDE_URL`.
        "ubelagte": [{"navn": k["navn"],
                      "vist": visningsord.kilde(k["navn"]),
                      "url": KILDE_URL.get(k["navn"], "")}
                     for k in kilder if k["ubelagt"]],
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


# ---------------------------------------------------- det VI låner
#
# /om/ har siden 19.09 hatt en tabell over KILDENES lisenser. Den
# dekket ikke det nettstedet selv distribuerer: Digdirs designtokens og
# Newsreader ligger i utputtet, og begge har vilkår.
#
# For fonten er det ikke en høflighet. SIL OFL 1.1 krever at
# lisensteksten følger fonten, og `skriv_fonter()` legger den på
# /newsreader-OFL.txt — men en fil ingen vet om, er en fil ingen
# finner. Raden her er veien dit.
#
# Verdiene står som literaler og ikke som en lesning av filene. En
# parser som gjettet «lisens» ut av en CSS-kommentar ville vært et sted
# til der noe kan bli feil, og lista er tre rader som endres når noen
# bytter en avhengighet — altså sjeldnere enn parseren ville råtnet.
#
# DIGDIR STO HER TIL 22.09.2026. Raden er fjernet fordi låntakingen er
# det — designoverleveringen har sin egen typeskala og sitt eget
# avstandsrutenett, og `maler/tokens.css` finnes ikke lenger. En rad om
# et lån vi ikke lenger tar, ville vært en usann opplysning på den ene
# siden som finnes for å svare på om man kan stole på dette.
VAART_LAAN = (
    {"hva": "Newsreader",
     "rolle": "overskrifter, ordmerke og nøkkeltall",
     "lisens": "SIL Open Font License 1.1",
     "opphav": "Production Type, via google/fonts",
     "sti": "/newsreader-OFL.txt"},
    {"hva": "IBM Plex Sans",
     "rolle": "brødtekst, etiketter og tabeller",
     "lisens": "SIL Open Font License 1.1",
     "opphav": "IBM, via google/fonts",
     "sti": "/ibmplex-OFL.txt"},
    {"hva": "IBM Plex Mono",
     "rolle": "tallverdier i tabellkolonner",
     "lisens": "SIL Open Font License 1.1",
     "opphav": "IBM, via google/fonts",
     "sti": "/ibmplex-OFL.txt"},
    # HEROFOTOGRAFIET. Raden gikk ut 26.09.2026, da heroen ble et kart,
    # og kom inn igjen 27.09 med et nytt bilde og en ny fotograf. En rad
    # om et lån vi ikke lenger tar, ville vært en usann opplysning på den
    # ene siden som finnes for å svare på om man kan stole på dette — og
    # en rad som navnga FEIL fotograf ville vært verre.
    #
    # UNSPLASH KREVER INGEN NAVNGIVING. Fotografen står her, i heroens
    # bildetekst og i docs/design/HEROFOTO.md likevel, av samme grunn som
    # datokolonnen i lisenskjeden finnes: en side som ikke sier hvor et
    # bilde kommer fra, kan ingen etterprøve.
    {"hva": "Herofotografiet, av Endre Stedje",
     "rolle": "forsidens hero",
     "lisens": "Unsplash-lisensen (navngiving er frivillig)",
     "opphav": "unsplash.com/photos/nTRAnQQ3E18",
     "sti": "https://unsplash.com/license"},
    # NATURAL EARTH KREVER INGENTING og står her likevel: en side som
    # ikke sier hvor en kystlinje kommer fra, kan ingen etterprøve. Se
    # docs/LISENSKJEDE.md merknad G.
    # KARTVERKET KREVER NOE, og er den eneste raden her som gjør det:
    # CC BY 4.0 vil ha navnet der produktet brukes, og navnet står
    # under hvert kart og i bunnteksten på hver side som viser ett.
    {"hva": "Kystkontur, Kartverket N500 og N2000",
     "rolle": "kystlinja i kartene",
     "lisens": "CC BY 4.0 — © Kartverket",
     "opphav": "kartverket.no",
     "sti": "https://creativecommons.org/licenses/by/4.0/deed.no"},
    {"hva": "Kystlinje, Natural Earth 1:10 millioner",
     "rolle": "nabolandene i kartene",
     "lisens": "public domain",
     "opphav": "naturalearthdata.com",
     "sti": "/naturalearth-LICENSE.md"},
)


def skriv_om(rot: Path, felles: Felles) -> Path:
    """Rendrer og skriver /om/."""
    om = bygg_om(felles)
    mal = _miljo().get_template("om.html.j2")
    html = mal.render(
        om=om,
        laan=VAART_LAAN,
        **_grunnkontekst(
            felles, rot, rot / "om" / "index.html", kilder=OM_KILDER,
            tittel="Om Kystloggen — kilder, metode, dekning og sitering",
            beskrivelse=(
                "Hva Kystloggen er, hvilke offentlige kilder det bygger "
                "på med lisens og attribusjon, hvor ofte det samles inn, "
                "hva dekningen er, hvem som står bak, og hvordan du "
                "siterer det."),
            jsonld=_script_trygg({
                "@context": "https://schema.org",
                "@type": "AboutPage",
                "name": "Om Kystloggen",
                "inLanguage": "nb",
                "author": {"@type": "Person", "name": om["forfatter"]},
                "codeRepository": om["repo"],
            }),
            proveniens_tekst=proveniens(felles.akva_dato, felles.akva_hentet),
            meny_aktiv="om", sidetype="Om",
            undertittel="Kilder, metode, dekning og sitering"),
    )
    return skriv_side(rot / "om" / "index.html", html)


# ------------------------------------------- ANALYSEN: UNNTAKSVEKST
#
# /analyse/unntaksvekst/ — Mattilsynets godkjente og avslåtte søknader om
# unntaksvekst 2025/2026, holdt mot kapasiteten i registeret og driften
# målt mot vilkårene. Se docs/ANALYSE-UNNTAKSVEKST.md.
#
# SIDEN REGNER INGENTING SELV. Hvert tall er `unntaksanalyse` sitt, og
# den modulen leser bare kropper som ligger i `data/arkiv/` — søknadslista
# kildens egen `fetch()` ga, eierskapskroppene, Mattilsynets lakselus-
# rapporter og forskriftstekstene. Det denne delen gjør, er å sette dem
# på en side, med hash ved hvert grunnlag.
#
# INGEN VURDERING AV ENKELTAKTØRER. Tabellen står med tall og vilkårets
# tall ved siden av hverandre, og ingen celle sier «oppfylt» eller
# «brutt». Det er bestilt, og det er riktig: hvert vilkår har deler ingen
# kilde vi har, kan måle (`unntaksanalyse.MAALING`).

ANALYSE_KILDER = ("unntaksvekst", "akvakultur", "eierskap", "lusetall",
                  "sjotemperatur", "trafikklysvedtak")

# MATTILSYNETS API ER IKKE EN KILDE i `sources/` — det er hentet én gang
# for denne analysen (`arkiver_mattilsynet.py lakselus`). Vilkåret står i
# spesifikasjonen selv: «Dataene fra APIet … følger vilkårene i
# NLOD-lisensen» (info.license: NLOD 2.0, arkivert i
# `mattilsynet-openapi/`). NLOD 2.0 punkt 3 gir standardformen når
# lisensgiveren ikke har bedt om en egen; samme form som Brønnøysund-
# registrenes setning. Står her og ikke på en kilde, som `KARTVERKET`.
MATTILSYNET_API = ("Inneholder data under Norsk lisens for offentlige "
                   "data (NLOD) tilgjengeliggjort av Mattilsynet")

UNNTAK_STI = ("analyse", "unntaksvekst")
UNNTAK_STAMME = "unntaksvekst-2025-2026"


def unntak_per_lokalitet() -> dict[str, list[dict]]:
    """{lokalitetsnummer: [rad]} for de SIKRE koblingene i nyeste
    arkiverte søknadsliste. Tom når lista ikke er arkivert.

    Lest av BEGGE veiene inn i `bygg_lokalitet()` — batchen gjennom
    `les_felles()`, enkeltsiden direkte. To lesemåter av samme liste som
    kunne svart ulikt, er formen F6 og F7 hadde.
    """
    try:
        _k, svar = unntaksanalyse.soknader()
    except FileNotFoundError:
        return {}
    ut: dict[str, list[dict]] = defaultdict(list)
    for r in unntaksanalyse.del_rader(svar["rader"])["sikre"]:
        ut[str(r["lokalitet_nr"])].append(r)
    return dict(ut)


def unntak_for_lokalitet(rader: list[dict]) -> dict | None:
    """Linja lokalitetssiden viser: resultatet og antall søkere. None når
    lokaliteten ikke står i lista med en sikker kobling."""
    if not rader:
        return None
    resultater = sorted({r["resultat"] for r in rader})
    return {"resultat": " og ".join(r.lower() for r in resultater),
            "soknader": len(rader), "url": "/" + "/".join(UNNTAK_STI) + "/"}


def _hash_vist(sha: str) -> str:
    """sha256 i grupper på åtte. Se `nedlasting.sjekksum_vist()`: en hel
    heksadesimal sum har ni siffer på rad i 11,7 % av tilfellene, og
    porten leser dem som organisasjonsnumre."""
    return " ".join(sha[i:i + 8] for i in range(0, len(sha), 8))


def _isoukeverdi(aar: int, uke: int) -> str:
    """`2023-W40` — HTML-formen for en uke i `<time datetime>`."""
    return f"{aar}-W{uke:02d}"


def _kapasitetstekst(kap: dict) -> str:
    """Cella i kapasitetskolonnen. Bare det kroppene viser."""
    deler = []
    if kap["endringer"]:
        summer = ", ".join(f"+{visningsord.tall(v)} {('t' if e == 'TN' else e)}"
                           for e, v in sorted(kap["sum_endring"].items()))
        en = all(e["en_prosent"] for e in kap["endringer"])
        deler.append(f"{summer} på "
                     + visningsord.antall(len({e['tillatelse'] for e in kap['endringer']}),
                                          "tillatelse", "tillatelser")
                     + (", alle nøyaktig 1 %" if en else ""))
    if kap["inn"]:
        deler.append(visningsord.antall(len(kap["inn"]), "tillatelse",
                                        "tillatelser") + " tilknyttet")
    if kap["ut"]:
        deler.append(visningsord.antall(len(kap["ut"]), "tillatelse",
                                        "tillatelser") + " fjernet")
    return "; ".join(deler) if deler else "uendret"


def _andel(over: int, av: int) -> str:
    return f"{over} av {av}" if av else VERDI_MANGLER


def _maalvisning(m: dict) -> dict:
    """Tallene fra `unntaksanalyse.maal()` slik en celle viser dem."""
    return {
        "talte": m["talte"],
        "b1": _andel(m["b1_over_01"], m["b1_talte"]),
        "over": (_andel(m["over"], m["talte"] - m["uten_grense"])
                 if m["talte"] else VERDI_MANGLER),
        "med": str(m["b3_medikamentelle"]) if m["uker"] else VERDI_MANGLER,
        "ikke_med": (str(m["b4_ikke_medikamentelle"]) if m["uker"]
                     else VERDI_MANGLER),
        "maks_017": max(m["ledd2a_017_per_aar"].values(), default=0),
        "rekke": m["ledd2b_rekke"], "rekke_13_39": m["ledd2b_rekke_13_39"],
        "b2": m["b2_over"], "sluttet": m["b5_sluttet"],
    }


def _lokalitetslenke(loknr: str, felles: Felles, reserve: str) -> dict:
    a = felles.akva.get(loknr)
    if a is None:
        return {"nr": loknr, "navn": reserve, "url": ""}
    return {"nr": loknr, "navn": visningsord.tittelform(a.get("navn", "")),
            "url": f"/lokalitet/{loknr}/"}


def bygg_unntaksvekst(felles: Felles) -> dict | None:
    """Alle tallene analysesiden viser, eller None uten arkivert liste."""
    try:
        liste_kropp, svar = unntaksanalyse.soknader()
    except FileNotFoundError:
        return None
    deler = unntaksanalyse.del_rader(svar["rader"])
    vilkaar = unntaksanalyse.vilkaar()
    kropper = unntaksanalyse.eierskapskropper()

    numre = sorted({str(r["lokalitet_nr"]) for n in ("sikre", "usikre")
                    for r in deler[n]}, key=int)
    kv_fra, kv_til = unntaksanalyse.KVALIFIKASJON
    fra_dato = dt.date.fromisocalendar(*kv_fra, 1).isoformat()
    bw = unntaksanalyse.barentswatch_uker(numre, fra_dato)
    siste_bw = max((d for s in bw.values() for d in s), default=fra_dato)

    drifter = {nr: unntaksanalyse.drift(nr, bw.get(nr, {}), siste_bw)
               for nr in numre}
    kapasiteter = {nr: unntaksanalyse.kapasitet(nr, kropper) for nr in numre}

    # Siste uke Mattilsynet har levert for noen av lokalitetene. Står i
    # setningen øverst og er MÅLT av rapportene, ikke av kalenderen.
    siste_mt = max(((u.aar, u.uke) for d in drifter.values()
                    for u in d.uker.values()), default=kv_til)

    def selskap(r: dict) -> dict:
        if not r.get("soker_orgnr"):
            return {"navn": "", "url": ""}
        orgnr = r["soker_orgnr"]
        url = (f"/selskap/{orgnr}/" if orgnr in felles.tillatelser_per_eier
               and not personeier(orgnr, felles) else "")
        return {"navn": visningsord.selskapsnavn(r.get("soker_registernavn", "")),
                "url": url, "orgnr": orgnr}

    def po(r):
        return int(r["po"]) if str(r["po"]).isdigit() else 99

    rader = []
    for r in sorted(deler["sikre"], key=lambda r: (
            po(r), _lokalitetslenke(str(r["lokalitet_nr"]), felles,
                                    r["lokalitet"])["navn"],
            r.get("soker_registernavn", ""))):
        nr = str(r["lokalitet_nr"])
        d = drifter[nr]
        rader.append({
            "lok": _lokalitetslenke(nr, felles, r["lokalitet"]),
            "mattilsynet_navn": r["lokalitet"],
            "po": r["po"], "resultat": r["resultat"],
            "saksnummer": ", ".join(r["saksnumre"]),
            "soker": selskap(r),
            "kapasitet": _kapasitetstekst(kapasiteter[nr]),
            "kap_endret": bool(kapasiteter[nr]["endringer"]),
            "kv": _maalvisning(d.kvalifikasjon),
            "etter": _maalvisning(d.etter),
            "_drift": d, "_kap": kapasiteter[nr], "_rad": r,
        })

    usikre = [{"mattilsynet_navn": r["lokalitet"], "po": r["po"],
               "resultat": r["resultat"],
               "kandidat": _lokalitetslenke(str(r["lokalitet_nr"]), felles,
                                            str(r["lokalitet_nr"])),
               "soker": selskap(r)}
              for r in sorted(deler["usikre"], key=lambda r: (po(r), r["lokalitet"]))]
    uloste = [{"mattilsynet_navn": r["lokalitet"], "po": r["po"],
               "resultat": r["resultat"],
               "kandidater": len(r.get("kandidater") or []),
               "kobling": r["kobling"]}
              for r in sorted(deler["uloste"], key=lambda r: (po(r), r["lokalitet"]))]

    # PER PRODUKSJONSPERIODE, for periodene som når inn i tiden etter
    # kvalifikasjonsperioden. Én rad per (lokalitet, periode).
    etter_fra = dt.date.fromisocalendar(*unntaksanalyse.ETTER[0], 1).isoformat()
    perioder = []
    sett: set[str] = set()
    for rad in rader:
        nr = rad["lok"]["nr"]
        if nr in sett:
            continue
        sett.add(nr)
        d = rad["_drift"]
        for p in d.per_periode:
            if p["til"] < etter_fra:
                continue
            perioder.append({"lok": rad["lok"], "resultat": rad["resultat"],
                             "fra": p["fra"], "til": p["til"],
                             "aapen": p["aapen"], "bw_uker": p["bw_uker"],
                             **_maalvisning(p)})
        if d.etter_bw["uker"]:
            perioder.append({"lok": rad["lok"], "resultat": rad["resultat"],
                             "fra": "", "til": "", "aapen": False,
                             "bw_uker": 0, **_maalvisning(d.etter_bw)})

    # KONTROLLEN: én rad per lokalitet, sikre koblinger, kvalifikasjons-
    # perioden. En lokalitet med to ulike resultater ville stått i begge
    # grupper; den holdes utenfor og telles.
    per_lok: dict[str, set] = defaultdict(set)
    for r in deler["sikre"]:
        per_lok[str(r["lokalitet_nr"])].add(r["resultat"])
    blandet = sorted(n for n, v in per_lok.items() if len(v) > 1)
    grupper: dict[str, list[dict]] = defaultdict(list)
    for nr, v in per_lok.items():
        if nr not in blandet:
            grupper[next(iter(v))].append(drifter[nr].kvalifikasjon)
    kontroll = unntaksanalyse.kontroll(grupper)
    laveste_p = min((r["p"] for r in kontroll["rader"]), default=1.0)

    # KAPASITETEN, oppsummert: lokalitetene med en endring, og hvor mange.
    endret = sorted({rad["lok"]["nr"] for rad in rader if rad["kap_endret"]},
                    key=int)
    alle_en_prosent = all(e["en_prosent"] for nr in endret
                          for e in kapasiteter[nr]["endringer"])

    n_lok = len(per_lok)
    godkjent = sum(1 for v in per_lok.values() if v == {"Godkjent"})
    avslag = sum(1 for v in per_lok.values() if v == {"Avslag"})

    lus_kropper = [d.kropp for d in drifter.values()]
    # HVERT LEDD MED SIN MÅLING, slått opp i `MAALING`. Nøkkelen følger
    # forskriftens egen nummerering: «b.3» er første ledd bokstav b nr. 3,
    # «ledd2.a» er annet ledd bokstav a. Annet ledd begynner med avsnittet
    # «Selv om det observerte lusenivået».
    paragraf12, i_ledd2 = [], False
    for b in vilkaar["paragraf12"]:
        i_ledd2 = i_ledd2 or (b.nivaa == 0 and b.tekst.startswith("Selv om"))
        nr = b.nummer.rstrip(".")
        nokkel = (f"b.{nr}" if b.nivaa == 2
                  else f"ledd2.{nr}" if b.nivaa == 1 and i_ledd2
                  else "a." if b.nivaa == 1 and nr == "a" else "")
        merke, tekst = unntaksanalyse.MAALING.get(nokkel, ("", ""))
        paragraf12.append({"nivaa": b.nivaa, "nummer": b.nummer,
                           "tekst": b.tekst, "merke": merke, "maaling": tekst})

    def kilde(k: unntaksanalyse.Kropp, url: str = "") -> dict:
        return {"navn": k.navn, "sha": _hash_vist(k.sha256), "url": url}

    return {
        "n_lok": n_lok, "godkjent": godkjent, "avslag": avslag,
        "rader_sikre": len(deler["sikre"]),
        "kv_fra": _isoukeverdi(*kv_fra), "kv_til": _isoukeverdi(*kv_til),
        "kv_fra_vist": f"uke {kv_fra[1]}/{kv_fra[0]}",
        "kv_til_vist": f"uke {kv_til[1]}/{kv_til[0]}",
        "etter_fra_vist": "uke {1}/{0}".format(*unntaksanalyse.ETTER[0]),
        "etter_fra": _isoukeverdi(*unntaksanalyse.ETTER[0]),
        "siste_mt": _isoukeverdi(*siste_mt),
        "siste_mt_vist": f"uke {siste_mt[1]}/{siste_mt[0]}",
        "siste_bw": siste_bw,
        "kap_fra": kropper[0][0] if kropper else "",
        "kap_til": kropper[-1][0] if kropper else "",
        "kap_endret": [_lokalitetslenke(nr, felles, nr) for nr in endret],
        "kap_endret_avslag": sum(1 for nr in endret
                                 if per_lok.get(nr) == {"Avslag"}),
        "kap_alle_en_prosent": alle_en_prosent,
        "kap_po": sorted({str(rad["po"]) for rad in rader
                          if rad["kap_endret"]}, key=int),
        # Lokalitetene kontrollen holder utenfor fordi de ikke har én
        # telling i kvalifikasjonsperioden. Forklarer at tabellen teller
        # flere godkjente enn kontrollen.
        "uten_tellinger_lok": [
            _lokalitetslenke(nr, felles, nr) for nr in sorted(per_lok, key=int)
            if nr not in blandet and not drifter[nr].kvalifikasjon["talte"]],
        "rader": rader, "usikre": usikre, "uloste": uloste,
        "perioder": perioder,
        "kontroll": kontroll, "laveste_p": laveste_p,
        "blandet": blandet,
        "paragraf12": paragraf12,
        "paragraf12a": [b.tekst for b in vilkaar["paragraf12a"]],
        "lakselus8": [b.tekst for b in vilkaar["lakselus8"]],
        "endret_ved": vilkaar["endret_ved"],
        "lik_2023": vilkaar["lik_2023"],
        "lovkilder": [kilde(k, vilkaar["url"].get(dok, ""))
                      for dok, k in vilkaar["kilder"].items()],
        "liste": {**kilde(liste_kropp, svar.get("url", "")),
                  "kropp_sha": _hash_vist(svar.get("sha256", "")),
                  "hentet": liste_kropp.navn.split("/")[-1][:10]},
        "eierskap": [kilde(k) for _d, k, _t in kropper],
        "lakselus_n": len(lus_kropper),
        "lakselus_rapporter": sum(len(json.loads(k.data)["rapporter"])
                                  for k in lus_kropper),
        "utenfor": [{"lok": nr, **u} for nr, d in drifter.items()
                    for u in d.utenfor],
        "ulike_uker": sum(d.kvalifikasjon["ulike_uker"]
                          + d.etter["ulike_uker"] for d in drifter.values()),
        "uten_tellinger_kv": kontroll["uten_tellinger"],
        "mattilsynet_liste_url": svar.get("url", ""),
    }


UNNTAK_KOLONNER = (
    nedlasting.Kolonne("lokalitetsnummer", "string",
                       "Fiskeridirektoratets lokalitetsnummer, slik kilden "
                       "koblet Mattilsynets lokalitetsnavn til registeret."),
    nedlasting.Kolonne("lokalitet_navn", "string",
                       "Lokalitetens navn i Akvakulturregisteret."),
    nedlasting.Kolonne("mattilsynet_navn", "string",
                       "Lokalitetsnavnet slik Mattilsynets liste skriver det."),
    nedlasting.Kolonne("produksjonsomraade", "string",
                       "Produksjonsområdet Mattilsynets liste oppgir."),
    nedlasting.Kolonne("resultat", "string",
                       "Mattilsynets resultat: Godkjent eller Avslag."),
    nedlasting.Kolonne("saksnummer", "string", "Mattilsynets saksnummer."),
    nedlasting.Kolonne("navn", "string",
                       "Søkerens navn i Fiskeridirektoratets register. Bare "
                       "der kilden har koblet søkeren entydig til et "
                       "organisasjonsnummer med selskapsform.",
                       "Søkeren er ikke koblet til et selskap og er utelatt."),
    nedlasting.Kolonne("orgnr", "string",
                       "Søkerens organisasjonsnummer.",
                       "Søkeren er utelatt."),
    nedlasting.Kolonne("kapasitet_endring_tonn", "decimal",
                       "Summen av endret capacity.current på tillatelser med "
                       "aktiv tilknytning til lokaliteten, mellom første og "
                       "siste eierskapskropp.", "Ingen endring."),
    nedlasting.Kolonne("kapasitet_en_prosent", "boolean",
                       "Om hver endring er nøyaktig round(x × 1,01).",
                       "Ingen endring."),
    *(nedlasting.Kolonne(f"{fase}_{navn}", "integer", f"{forkl} ({tekst}).",
                         "Ingen rapporter i tidsrommet.")
      for fase, tekst in (("kv", "uke 40/2023–39/2025"),
                          ("etter", "fra uke 40/2025"))
      for navn, forkl in (
          ("tellinger", "Uker med lusetall fra Mattilsynet"),
          ("tellinger_uke13_39", "Uker med lusetall i uke 13–39"),
          ("over_010_uke13_39", "Uker med 0,10 eller flere voksne hunnlus "
                                "i uke 13–39"),
          ("maks_017_per_aar", "Flest uker med 0,17 eller flere i uke "
                               "13–39 i ett ISO-år"),
          ("rekke_010", "Lengste rekke påfølgende uker med 0,10 eller flere"),
          ("rekke_010_uke13_39", "Samme rekke, bare uke 13–39"),
          ("over_tiltaksgrense", "Uker på eller over BarentsWatchs "
                                 "tiltaksgrense"),
          ("over_tiltaksgrense_uke40_12", "Samme, i uke 40–12"),
          ("uten_grense", "Uker med tall uten grense hos BarentsWatch"),
          ("medikamentelle", "Oppføringer av medikamentell behandling"),
          ("ikke_medikamentelle", "Oppføringer av ikke-medikamentell "
                                  "behandling"),
          ("perioder_sluttet", "Produksjonsperioder som endte med brakk"))),
)


def unntak_datasett(a: dict, setninger: list[str], bygget: str
                    ) -> nedlasting.Datasett:
    """Tabellen per søker og lokalitet, med alle tallene, som nedlasting."""
    def fase(m: dict, f: str) -> dict:
        return {
            f"{f}_tellinger": str(m["talte"]),
            f"{f}_tellinger_uke13_39": str(m["b1_talte"]),
            f"{f}_over_010_uke13_39": str(m["b1_over_01"]),
            f"{f}_maks_017_per_aar": str(max(m["ledd2a_017_per_aar"].values(),
                                             default=0)),
            f"{f}_rekke_010": str(m["ledd2b_rekke"]),
            f"{f}_rekke_010_uke13_39": str(m["ledd2b_rekke_13_39"]),
            f"{f}_over_tiltaksgrense": str(m["over"]),
            f"{f}_over_tiltaksgrense_uke40_12": str(m["b2_over"]),
            f"{f}_uten_grense": str(m["uten_grense"]),
            f"{f}_medikamentelle": str(m["b3_medikamentelle"]),
            f"{f}_ikke_medikamentelle": str(m["b4_ikke_medikamentelle"]),
            f"{f}_perioder_sluttet": str(m["b5_sluttet"]),
        } if m["uker"] else {}

    rader = []
    for rad in a["rader"]:
        r, kap, d = rad["_rad"], rad["_kap"], rad["_drift"]
        summer = kap["sum_endring"]
        rader.append({
            "lokalitetsnummer": rad["lok"]["nr"],
            "lokalitet_navn": rad["lok"]["navn"],
            "mattilsynet_navn": r["lokalitet"],
            "produksjonsomraade": str(r["po"]),
            "resultat": r["resultat"],
            "saksnummer": "; ".join(r["saksnumre"]),
            "navn": r.get("soker_registernavn", "") if r.get("soker_orgnr") else "",
            "orgnr": r.get("soker_orgnr", ""),
            "kapasitet_endring_tonn": (str(summer.get("TN")) if "TN" in summer
                                       else ""),
            "kapasitet_en_prosent": (str(all(e["en_prosent"] for e in
                                             kap["endringer"]))
                                     if kap["endringer"] else ""),
            **fase(d.kvalifikasjon, "kv"), **fase(d.etter, "etter"),
        })
    return nedlasting.Datasett(
        stamme=UNNTAK_STAMME,
        tittel="Unntaksvekst 2025/2026: søknad, kapasitet og drift",
        beskrivelse=(
            f"{len(rader)} rader, én per søker og lokalitet, for "
            f"lokalitetene i Mattilsynets oversikt over søknader om "
            f"unntaksvekst 2025/2026 som kilden har koblet entydig til "
            f"Akvakulturregisteret. Lus og behandlinger er fra Mattilsynets "
            f"ukesrapporter; tiltaksgrense og produksjonsperioder er "
            f"BarentsWatchs. Ingen kolonne sier om et vilkår er oppfylt."),
        kolonner=UNNTAK_KOLONNER,
        rader=rader,
        kilder=(kildelisens(["unntaksvekst", "eierskap", "lusetall"])
                + [("Mattilsynet, lakselusrapporter via åpent API",
                    "NLOD 2.0", "https://data.norge.no/nlod/no/2.0")]),
        attribusjon=list(setninger),
        hentet=[f"Søknadslista arkivert {a['liste']['hentet']}; "
                f"lakselusrapportene hentet samme dag."],
        bygget=bygget,
        merknader=[
            "Lusetallet for en uke er det høyeste Mattilsynet har fått "
            "rapportert for uka; en behandling som står likt i to rapporter "
            "samme uke, telles én gang.",
            "En oppføring av behandling i en ukesrapport er ikke "
            "nødvendigvis det forskriften kaller én behandling.",
            "Produksjonsperiodene er BarentsWatchs vurdering «trolig uten "
            "fisk», ikke innrapportert slakting."],
        nokkel=("saksnummer", "lokalitetsnummer"),
    )


def skriv_unntaksvekst(rot: Path, felles: Felles) -> list[Path]:
    """/analyse/unntaksvekst/ med nedlastingene. Tom liste uten arkivert
    søknadsliste — og da står det i byggerapporten."""
    a = bygg_unntaksvekst(felles)
    if a is None:
        return []
    mappe = rot.joinpath(*UNNTAK_STI)
    sti = mappe / "index.html"
    kontekst = _grunnkontekst(
        felles, rot, sti, kilder=ANALYSE_KILDER,
        ekstra_attribusjon=(MATTILSYNET_API,),
        tittel="Unntaksvekst 2025/2026: fra søknad til drift",
        beskrivelse=(
            f"{a['n_lok']} lokaliteter Mattilsynet har godkjent eller avslått "
            f"for unntaksvekst 2025/2026: kapasiteten i registeret, og lus "
            f"og behandlinger målt mot vilkårene i "
            f"produksjonsområdeforskriften § 12."),
        jsonld=_script_trygg({
            "@context": "https://schema.org", "@type": "Dataset",
            "name": "Unntaksvekst 2025/2026: fra søknad til drift",
            "inLanguage": "nb",
            "temporalCoverage": f"{a['kv_fra']}/{a['siste_mt']}",
        }),
        proveniens_tekst=proveniens(felles.akva_dato, felles.akva_hentet),
        sidetype="Analyse",
        undertittel="Mattilsynets søknader om unntaksvekst holdt mot "
                    "kapasitet og drift",
        soketekst="unntaksvekst unntak kapasitetsøkning Mattilsynet")
    ds = unntak_datasett(a, kontekst["attribusjon"], kontekst["bygget"])
    html = _miljo().get_template("analyse-unntaksvekst.html.j2").render(
        a=a, xlsx=ds.xlsx_navn, zip=ds.zip_navn,
        sjekksum=nedlasting.sjekksum_vist(ds), **kontekst)
    mappe.mkdir(parents=True, exist_ok=True)
    (mappe / ds.xlsx_navn).write_bytes(nedlasting.xlsx_bytes(ds))
    (mappe / ds.zip_navn).write_bytes(nedlasting.zip_bytes(ds))
    return [skriv_side(sti, html), mappe / ds.xlsx_navn, mappe / ds.zip_navn]



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


# ------------------------------------------------------- høyrespalta
#
# Tallene i høyrespalta på indeks-, selskaps- og områdesidene. Se
# maler/marg.html.j2 og stil.css avsnitt 11b. Alt her er TELT av de
# samme snapshotene sidene ellers leser; ingenting er anslått.


def fordeling(rader: list[tuple[str, str, float, str]]) -> list[dict]:
    """[(tekst, url, antall, vist)] -> rader med `andel` i prosent av den
    største. Rekkefølgen er den som kommer inn: den velger sidetypen.

    `vist` er tallet slik det skal stå, fordi «79 260 tonn» og «158» er
    ulike former av det samme feltet."""
    storst = max((r[2] for r in rader), default=0) or 1
    return [{"tekst": tekst, "url": url, "antall": antall, "vist": vist,
             "andel": round(100 * antall / storst, 1)}
            for tekst, url, antall, vist in rader]


def _po_sortert(koder) -> list[str]:
    return sorted(koder, key=lambda k: int(k) if k.isdigit() else 0)


def _po_fordeling(felles: Felles, loknr) -> list[dict]:
    """Lokalitetene i `loknr` per produksjonsområde, i områdenes egen
    rekkefølge — sør til nord, som på kartet. Bare områder med minst én.
    Lokaliteter utenfor inndelingen er ikke en rad: de er ikke et
    område, og en stolpe for dem ville vært en stolpe for et fravær."""
    per = Counter((felles.akva[nr].get("prodomraade_kode") or "").strip()
                  for nr in loknr if nr in felles.akva)
    return fordeling([(f"{po} {felles.po_navn.get(po, '')}".strip(),
                       f"/produksjonsomrade/{po}/", per[po],
                       visningsord.tall(per[po]))
                      for po in _po_sortert(k for k in per if k)])


def _koordinater(felles: Felles, loknr) -> list[tuple[str, str]]:
    return [(felles.akva[nr].get("breddegrad", ""),
             felles.akva[nr].get("lengdegrad", ""))
            for nr in loknr if nr in felles.akva]


def _lokalitetsmarg(felles: Felles) -> dict:
    """Høyrespalta på lokalitetsindeksen: kartet, per område, per art.

    PER ART TELLES EN LOKALITET UNDER HVER ART DEN HAR. «OTHER_FISH;
    SALMON» er to koder (se visningsord), og 201 lokaliteter har mer
    enn én (MÅLT 09.10.2026) — summen av radene er derfor større enn
    antallet lokaliteter, og noten under sier det."""
    arter: Counter = Counter()
    for a in felles.akva.values():
        for kode in (a.get("arter") or "").split(";"):
            if kode.strip():
                arter[kode.strip()] += 1
    flere = sum(1 for a in felles.akva.values()
                if len([k for k in (a.get("arter") or "").split(";")
                        if k.strip()]) > 1)
    per_po = _po_fordeling(felles, felles.akva)
    return {
        "kart": kart.minikart(_koordinater(felles, felles.akva)),
        "per_po": per_po,
        # Summen av radene den står under, ikke et nytt oppslag.
        "i_po": sum(r["antall"] for r in per_po),
        "per_art": fordeling([
            (visningsord.verdi("arter", kode).capitalize(), "", n,
             visningsord.tall(n))
            for kode, n in arter.most_common()]),
        "flere_arter": flere,
    }


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

    # LOKALITETER UTEN KOORDINATER. Lista lå på forsiden til 22.09.2026,
    # ved siden av punktkartet den forklarte. Kartet er byttet ut med
    # områdekartet, og regnskapet flyttet hit — der alle 1 782 uansett
    # står. Uenighetsregelen er den samme: et punkt som mangler skal
    # ikke bare forsvinne. Se docs/REGEL-UENIGE-KILDER.md.
    _punkter, uten, _hoyde, _gitter = kartpunkter(felles.akva)
    return {"rader": rader, "antall": len(rader), "side": None,
            "marg": _lokalitetsmarg(felles),
            "akva_dato": felles.akva_dato,
            "uten_po": sum(1 for r in rader if not r["po_kode"]),
            "uten_omraade": uten_omraade_tekst(felles.akva),
            "uten_koordinater": [
                {"loknr": nr,
                 "navn": felles.akva[nr].get("navn", ""),
                 "kommune": felles.akva[nr].get("kommune", "")}
                for nr in uten],
            "uten_koordinater_antall": len(uten)}


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
            # KARTET ved tabellen, fylt med TABELLENS farge — nyeste
            # fastsatte runde — så kart og tabell sier det samme. Forsidens
            # kart viser fargen registeret oppgir nå, og står ved en tabell
            # som viser begge.
            "kart": kart.minikart(),
            "akva_dato": felles.akva_dato,
            "uten_po": sum(1 for a in felles.akva.values()
                           if not (a.get("prodomraade_kode") or "").strip()),
            "uten_omraade": uten_omraade_tekst(felles.akva)}


# DE STØRSTE, i høyrespalta på selskapsindeksen. Fem er nok til å svare
# på «hvem er størst» uten å bli en andre tabell.
SELSKAP_TOPP = 5

# «Siste fire uker» på selskapsindeksen: en måned, regnet i hele uker,
# som selskapssidens kvartal.
SELSKAP_INDEKS_UKER = 4


def _selskapsmarg(felles: Felles, rader: list[dict]) -> dict:
    """Høyrespalta på selskapsindeksen. `rader` er indeksens egne — uten
    personeierne, så ingen av listene kan navngi en person (regel 3).

    KAPASITETEN ER BARE TONN. `kapasitet_enhet` er tonn, dekar, stykk,
    kilo, kvadrat- og kubikkmeter og liter i det samme registeret (se
    `_samlet_kapasitet()`); en rangering på tvers av enhetene ville vært
    en rangering av ingenting. Tillatelser i andre enheter er telt, og
    noten sier hvor mange.

    ENDRINGENE er selskapssidens: `_selskapsendringer()` med et vindu på
    fire uker i stedet for tretten, så et selskap som teller her, har en
    rad i lista på sin egen side."""
    tonn: dict[str, float] = defaultdict(float)
    andre = 0
    endret = 0
    vindu = None
    for r in rader:
        orgnr = r["orgnr"]
        tillatelser = sorted(felles.tillatelser_per_eier.get(orgnr, ()))
        for nr in tillatelser:
            d = felles.eierskap[nr]
            try:
                verdi = float((d.get("kapasitet") or "").strip())
            except ValueError:
                continue
            if (d.get("kapasitet_enhet") or "").strip() == "TN":
                tonn[orgnr] += verdi
            else:
                andre += 1
        lok = sorted({l for nr in tillatelser
                      for l in _liste(felles.eierskap[nr].get("lokaliteter"))
                      if l in felles.akva})
        poster, vindu = _selskapsendringer(orgnr, lok, tillatelser, felles,
                                           uker=SELSKAP_INDEKS_UKER)
        endret += bool(poster)

    def tekst(r: dict) -> str:
        return visningsord.selskapsnavn(r["navn"]) or r["orgnr"]

    etter_tonn = sorted((r for r in rader if tonn.get(r["orgnr"])),
                        key=lambda r: (-tonn[r["orgnr"]], tekst(r)))
    etter_lok = sorted(rader, key=lambda r: (-r["lokaliteter"], tekst(r)))
    return {
        "tonn": fordeling([(tekst(r), f"/selskap/{r['orgnr']}/",
                            tonn[r["orgnr"]],
                            visningsord.maalt(tonn[r["orgnr"]], "TN"))
                           for r in etter_tonn[:SELSKAP_TOPP]]),
        "andre_enheter": andre,
        "lokaliteter": fordeling([(tekst(r), f"/selskap/{r['orgnr']}/",
                                   r["lokaliteter"],
                                   visningsord.tall(r["lokaliteter"]))
                                  for r in etter_lok[:SELSKAP_TOPP]]),
        "endret": endret,
        "vindu": vindu,
    }


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
    return {"rader": rader, "antall": len(rader), "side": None,
            "eierskap_dato": felles.eierskap_dato,
            "uten_registerdata": sum(1 for r in rader
                                     if not r["har_registerdata"]),
            "personeiere": personer,
            "marg": _selskapsmarg(felles, rader)}


# RADER PER INDEKSSIDE. MÅLT 08.10.2026 på 390 px: en indeksrad som
# tabell er ~45 px, og 100 rader med topp og bunntekst holder siden under
# 10 000 px — kravet i docs/design/BRIEF.md.
INDEKS_PER_SIDE = 100


def indekssider(antall: int, per_side: int = INDEKS_PER_SIDE) -> int:
    """Hvor mange sider en indeks med `antall` rader deles i. Minst én."""
    return max(1, -(-antall // per_side))


def indekssti(sti: str, nr: int) -> str:
    """`lokalitet`, 1 -> `/lokalitet/`; 3 -> `/lokalitet/side/3/`.

    SIDE 1 ER INDEKSENS EGEN ADRESSE. `/lokalitet/` har vært lenket til
    fra menyen, søkesiden og områdesidene siden den ble bygget, og den
    skal fortsatt være stedet man begynner — og ankeret
    `#akvakultur-uten-koordinater` står der.
    """
    return f"/{sti}/" if nr == 1 else f"/{sti}/side/{nr}/"


def _sidenavigasjon(sti: str, rader: list[dict], nokkel: str, nr: int,
                    per_side: int) -> dict:
    """Hvilken side dette er, og veien til hver av de andre.

    HVER SIDE LENKER TIL ALLE DE ANDRE, med spennet den dekker — «10001–
    11283» — og ikke bare til forrige og neste. En paginert liste der
    side 14 bare nås gjennom 13 andre, er en liste der side 14 ikke
    blir lest; to klikk unna er den ikke det.
    """
    n = indekssider(len(rader), per_side)
    sider = []
    for k in range(1, n + 1):
        bit = rader[(k - 1) * per_side:k * per_side]
        sider.append({"nr": k, "url": indekssti(sti, k),
                      "fra": bit[0][nokkel] if bit else "",
                      "til": bit[-1][nokkel] if bit else "",
                      "gjeldende": k == nr})
    return {"nr": nr, "antall": n, "sider": sider,
            "forrige": indekssti(sti, nr - 1) if nr > 1 else "",
            "neste": indekssti(sti, nr + 1) if nr < n else "",
            "fra_rad": (nr - 1) * per_side + 1,
            "til_rad": min(nr * per_side, len(rader))}


def _skriv_indeks(rot: Path, sti: str, mal_navn: str, data: dict,
                  tittel: str, beskrivelse: str, kilder: tuple,
                  felles: Felles, nokkel: str = "",
                  per_side: int = INDEKS_PER_SIDE) -> list[Path]:
    """Én indeks, på én eller flere sider. Samme form for alle tre.

    Med `nokkel` deles radene i sider på `per_side`; uten står alt på
    én. `nokkel` er feltet sidelenkene viser spennet i.
    """
    mal = _miljo().get_template(mal_navn)
    rader = data["rader"]
    n = indekssider(len(rader), per_side) if nokkel else 1
    ut = []
    for nr in range(1, n + 1):
        d = dict(data)
        if nokkel:
            d["rader"] = rader[(nr - 1) * per_side:nr * per_side]
            d["side"] = _sidenavigasjon(sti, rader, nokkel, nr, per_side)
        else:
            d["side"] = None
        fil = rot / indekssti(sti, nr).strip("/") / "index.html"
        sidetittel = tittel if nr == 1 else f"{tittel} (side {nr} av {n})"
        html = mal.render(
            d=d,
            **_grunnkontekst(
                felles, rot, fil, kilder=kilder,
                tittel=sidetittel, beskrivelse=beskrivelse,
                jsonld=_script_trygg({
                    "@context": "https://schema.org",
                    "@type": "CollectionPage",
                    "name": sidetittel,
                    "description": beskrivelse,
                    "inLanguage": "nb",
                }),
                proveniens_tekst=proveniens(felles.akva_dato, felles.akva_hentet),
                meny_aktiv=sti, sidetype="Liste",
                undertittel=f"{data['antall']} oppføringer"),
        )
        ut.append(skriv_side(fil, html))
    return ut


# INDEKSSIDENES KILDER. Navngitt og ikke inline, fordi `viste_kilder()`
# skal kunne telle dem med — se `bygg_om()`.
INDEKS_LOKALITET_KILDER = ("akvakultur",)
INDEKS_OMRAADE_KILDER = ("akvakultur", "trafikklysvedtak")
INDEKS_SELSKAP_KILDER = ("eierskap", "enhetsregisteret")


def viste_kilder() -> frozenset[str]:
    """Kildene som FAKTISK står på en publisert side.

    UNIONEN av det hver sidetype oppgir til `_grunnkontekst(kilder=...)`,
    og ikke en liste ved siden av. Det er de samme tuplene som driver
    attribusjonen i bunnteksten, så «vises her» og «hvem må navngis» kan
    ikke svare ulikt.

    Fram til 24.09.2026 leste kolonnen «Vises her» på /om/ `navn in
    OM_KILDER` — altså kildene OM-SIDEN SELV bruker. Den sto derfor
    «nei» for `biomasselag`, som står på hver ukesside, og «ja» for alt
    om-siden trengte. To lister som skal si det samme er formen F6 og F7
    hadde; her var den ene dessuten om noe annet enn kolonnen spurte om.

    `test_ingen_vist_kilde_staar_som_nei` holder at hver `kilder=`-tuppel
    i modulen er med her.
    """
    return frozenset(
        SIDENS_KILDER + ENDRINGSKILDER + FORSIDEKILDER + SELSKAPSKILDER
        + PO_KILDER + OM_KILDER + INDEKS_LOKALITET_KILDER
        + INDEKS_OMRAADE_KILDER + INDEKS_SELSKAP_KILDER + ANALYSE_KILDER)


def skriv_indekser(rot: Path, felles: Felles) -> list[Path]:
    """De tre indekssidene."""
    return [
        *_skriv_indeks(
            rot, "lokalitet", "indeks-lokalitet.html.j2",
            bygg_lokalitetsindeks(felles),
            "Alle akvakulturlokaliteter — Kystloggen",
            "Liste over alle norske akvakulturlokaliteter med "
            "nummer, navn, kommune og produksjonsområde.",
            INDEKS_LOKALITET_KILDER, felles, nokkel="loknr"),
        *_skriv_indeks(
            rot, "produksjonsomrade", "indeks-produksjonsomrade.html.j2",
            bygg_poindeks(felles),
            "Alle produksjonsområder — Kystloggen",
            "De tretten produksjonsområdene med nyeste trafikklysfarge "
            "og antall lokaliteter.",
            INDEKS_OMRAADE_KILDER, felles),
        *_skriv_indeks(
            rot, "selskap", "indeks-selskap.html.j2",
            bygg_selskapsindeks(felles),
            "Alle innehavere av akvakulturtillatelse — Kystloggen",
            "Liste over innehaverne av minst én "
            "akvakulturtillatelse, med antall tillatelser og lokaliteter.",
            INDEKS_SELSKAP_KILDER, felles, nokkel="navn"),
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


# FORSIDENS ENDRINGSTABELL STO HER TIL 27.09.2026, åtte rader og
# «Alle N endringer i uke W →». Tabellen er borte fra forsiden; hele
# uka står på `/endringer/<uke>/`, som er sida som finnes for den.
#
# `FORSIDERADER` er derfor FJERNET, ikke satt til 0. En konstant som
# styrer noe som ikke finnes, er neste persons feilsøking.

# HVOR MANGE SETNINGER AV SAMMENDRAGET FORSIDEN VISER.
#
# `_sammendrag()` kan returnere fire: ledesetningen, selskapsdata,
# flest og nest flest. Forsiden tar de tre første — den skal si hva
# som skjedde, ikke være ukessiden. Den fjerde («Deretter <type> med
# N») er den som faller, og den er den minst bærende av dem.
#
# Tallet står her og ikke som `[:3]` i malen: et tall i en mal er et
# tall ingen kan teste.
FORSIDESETNINGER = 3


def _ledede_typer(uke: dict) -> list[dict]:
    """Ukas endringstyper som TELLER, størst først.

    Bare slagene som er hendelser i havbruket: ikke selskapsdata (egen
    del), og ikke slag som ikke teller («felt oppgitt første gang»).
    Én funksjon for sammendraget og forsidens typestolper, så de to ikke
    kan bli uenige om hvilke slag uka bestod av.
    """
    return sorted((k for k in uke["typer"]
                   if k["antall"] and k.get("teller", True)
                   and k["id"] not in EGEN_DEL),
                  key=lambda k: -k["antall"])


# HVOR MANGE TYPER FORSIDEN VISER som stolper. Briefen ber om ukas
# viktigste tre til fem endringer øverst; de vesentlige står som
# faktasetninger, og typene viser hvor resten av uka ligger.
FORSIDETYPER = 5


def ukas_typer(uke: dict | None, n: int = FORSIDETYPER) -> list[dict]:
    """De største endringstypene i uka, med lenke til typesiden.

    Tallene er de samme som brikkene på ukesiden viser, og lenkene går
    til de samme sidene. `andel` er stolpens lengde i prosent av den
    største — en tegning av tallet, ikke et nytt tall.
    """
    if not uke:
        return []
    typer = _ledede_typer(uke)[:n]
    if not typer:
        return []
    storst = typer[0]["antall"]
    return [{"id": k["id"], "navn": k["navn"], "antall": k["antall"],
             "hva": k["hva"], "url": f"/endringer/{uke['slug']}/{k['id']}/",
             "andel": round(100 * k["antall"] / storst, 1)}
            for k in typer]


def _sammendrag(uke: dict | None) -> list[dict]:
    """Én til fire setninger om uka, generert av tallene.

    DOCSTRINGEN SA «én til tre» til 27.09.2026 og var usann: med både
    selskapsdata og to talltyper blir det fire. Forsiden tar de tre
    første — se `FORSIDESETNINGER` — og det er DEN begrensningen som er
    et valg. Denne funksjonen lager alle setningene det er belegg for.

    Hver setning er `{"tekst": ..., "brod": bool}`. `brod` er sant for
    den ene setningen som ikke er ukas sak: selskapsdataene som står for
    seg. Den sto i samme 29-pikslers overskriftsskrift som de andre og
    leste da som en hovedsak — og det er nettopp det
    23.09-beslutningen sier at den ikke er. Flagget er her og ikke en
    klasse i malen, fordi det er HER det er kjent hvilken setning det
    gjelder.

    ## Hvorfor generert og ikke skrevet

    Fordi den skal stemme hver mandag uten at noen leser korrektur. En
    håndskrevet ingress om «trafikklysuka» ville stått der uka etter
    også.

    ## Hvorfor det ikke er en tolkning

    Setningene sier HVA SOM ENDRET SEG og HVOR MANGE. De sier ikke
    hvorfor, og de sier ikke om det er mye eller lite: «362 lokaliteter
    fikk ny trafikklysfarge» er en telling, «uvanlig mange» ville vært
    en vurdering vi ikke har grunnlag for før vi har mer enn fem uker.
    """
    def sak(tekst: str) -> dict:
        return {"tekst": tekst, "brod": False}

    if uke is None or not uke["antall"]:
        return [sak("Ingen endringer i registrene denne uka. Alle felt "
                    "står som de sto forrige gang vi spurte.")]

    # BARE SLAGENE SOM TELLER. «Felt oppgitt første gang» er ikke en
    # hendelse i havbruket, og en oppsummering som sa «fordelt på ni
    # slag» og listet det som nest størst, ville gjort rapportering om
    # til aktivitet.
    # BARE SLAGENE SOM TELLER OG SOM ER LEDET. Selskapsdata står for
    # seg — 402 av uke 39s 440 — og en oppsummering som ledet med dem
    # ville svart på «hvor mange felt endret seg i et register» framfor
    # på «hva skjedde i havbruket denne uka».
    med_tall = _ledede_typer(uke)
    if not med_tall:
        return [sak("Ingen endringer i lokaliteter, tillatelser eller "
                    "trafikklys denne uka. Alle felt står som de sto "
                    "forrige gang vi spurte.")]
    # TALLET SIER HVA DET TELLER. «38 endringer» alene lar leseren tro
    # det er alt som skjedde; setningen navngir slagene, og neste
    # setning sier hvor selskapsdataene ble av.
    setninger = [
        sak(f"{visningsord.tall(uke['antall'])} endringer observert i "
            f"{uke['vist']}: {uke['ledet_slag']}.")
    ]
    if uke["antall_egen_del"]:
        # BRØDTEKST. Setningen sier hvor noe IKKE er, og en henvisning
        # satt i samme skrift som ukas sak leses som ukas sak.
        setninger.append({
            "tekst": (f"{visningsord.tall(uke['antall_egen_del'])} "
                      f"endringer i selskapsdata — ansatte, næringskode, "
                      f"adresse, regnskap — står for seg på ukessiden."),
            "brod": True})

    storst = med_tall[0]
    if storst["id"] == "trafikklys":
        setninger.append(sak(
            f"Akvakulturregisteret oppgir ny trafikklysfarge for "
            f"{visningsord.tall(storst['antall'])} "
            f"{'produksjonsområde' if storst['antall'] == 1 else 'produksjonsområder'}"
            f" — forskriften dateres til vedtaksåret, og dette er uka "
            f"registeret fulgte den opp."))
    else:
        setninger.append(sak(
            f"Flest endringer gjaldt {storst['kort']} "
            f"({visningsord.tall(storst['antall'])}): "
            f"{storst.get('forklaring', storst['hva'])}."))

    if len(med_tall) > 1:
        nest = med_tall[1]
        setninger.append(sak(
            f"Deretter {nest['navn'].lower()} med "
            f"{visningsord.tall(nest['antall'])}."))
    return setninger


def _forskriftslinje(felles: Felles, uke: dict | None) -> dict | None:
    """De to tidspunktene vi HAR for en trafikklysendring, og gapet.

    ## Overleveringen ber om tre punkter. Vi har to.

    Tidslinja i designet er «Fastsatt → Kunngjort → Observert her».
    FASTSATT-datoen er ikke samlet inn: `trafikklysvedtak` bærer `farge`
    og `farge__lesemaate` og ingenting annet, og en dato vi ikke har
    hentet skal ikke stå på siden. Punktet utelates — overleveringens
    egen regel for komponenten: «punkter uten dato utelates, dager
    beregnes ikke».

    De to vi har er belagte:

        utgitt        `published_at` på trafikklysvedtak-snapshotet.
                      Det er KILDENS eget tidspunkt (CLAUDE.md 1b-7),
                      lest av tjenesten og ikke utledet av oss.
        observert     `observed_at` på akvakulturradene. Det er OSS.

    ## Koblingen mellom dem er VÅR, og det står på siden

    At registeret endret farge fordi denne forskriften ble utgitt, er en
    slutning. Den er nærliggende og den er ikke bevist: ingen felt i
    noen av de to kildene viser til den andre. `note` sier det, og
    setningen rendres sammen med tidslinja — ikke i en fotnote noen
    kan hoppe over.
    """
    if uke is None:
        return None
    trafikklys = [h for h in uke["hendelser"] if h["type"] == "trafikklys"]
    if not trafikklys:
        return None

    runder = snapshot.datoer("trafikklysvedtak")
    utgitt = ""
    if runder:
        ramme = snapshot.versjoner("trafikklysvedtak", runder[-1])[-1][1]
        utgitt = snapshot.published_at_i(ramme) or ""
    if not utgitt:
        return None

    observert = min(h["dato"] for h in trafikklys)
    try:
        dager = (dt.date.fromisoformat(observert)
                 - dt.date.fromisoformat(utgitt[:10])).days
    except ValueError:
        return None
    if dager < 0:
        # Observert FØR utgivelsen: da er det ikke denne runden vi ser,
        # og en tidslinje som viste den ville vært en usann kobling.
        return None

    return {
        "utgitt": utgitt[:10],
        "utgitt_vist": visningsord.dato(utgitt[:10]),
        "observert": observert,
        "observert_vist": visningsord.dato(observert),
        "dager": dager,
        "antall": len(trafikklys),
        # OMRÅDER OG LOKALITETER ER TO TALL. Registeret fører fargen på
        # hver lokalitet, men beslutningen gjelder området — se
        # `SAMLES_PER_OMRAADE`. Forsiden sier begge, fordi «4 områder»
        # alene skjuler hvor mange som ble berørt og «362 lokaliteter»
        # alene later som det var 362 vedtak.
        "lokaliteter": sum(h.get("omfang", 1) for h in trafikklys),
        "runde": runder[-1][:4],
        "note": ("Koblingen mellom de to datoene er vår lesning. Ingen "
                 "felt i noen av kildene viser til den andre — "
                 "forskriften sier ikke når registeret skal følge opp, "
                 "og registeret sier ikke hvilken forskrift det følger."),
    }


def _omraaderader(felles: Felles) -> list[dict]:
    """De tretten radene i kysttabellen, med femårsstripa.

    Stripa er RUNDENE, ikke årene: 2018, 2020, 2022, 2024, 2026 er fem
    forskrifter, og et hull mellom dem er ikke en rute som mangler.
    `title` på hver rute bærer året og fargeordet, fordi en rute uten
    tekst er en farge som bærer mening alene.
    """
    rader = []
    for po in sorted(felles.po_navn, key=lambda k: int(k) if k.isdigit() else 0):
        runder = _fargerader(po, felles)
        naa = felles.po_naa.get(po) or {"farge": FARGE_MANGLER, "klasse": "",
                                        "uenig": ""}
        rader.append({
            "nr": po,
            "navn": felles.po_navn[po],
            "lokaliteter": len(felles.lokaliteter_per_po.get(po, ())),
            "farge": naa["farge"],
            "farge_klasse": naa["klasse"],
            "uenig": naa["uenig"],
            "stripe": [{"aar": r["aar"], "farge": r["farge"],
                        "klasse": r["farge_klasse"],
                        "tittel": f"{r['aar']}: {r['farge']}"}
                       for r in runder],
            "historie": _historietekst(runder),
        })
    return rader


def _historietekst(runder: list[dict]) -> str:
    """«grønn i alle fem runder», «gul → rød → gul», «ikke oppgitt i
    noen runde». Avledet av stripa, aldri skrevet.

    Runder UTEN farge hoppes over i pilrekka framfor å stå som «ikke
    oppgitt → gul → ikke oppgitt»: forskriften navngir bare områder der
    noe endrer seg, så en tom runde er fravær av en BESTEMMELSE og ikke
    fravær av en farge. At rutene i stripa likevel er skravert, er
    forskjellen på hva vi VET og hva som gjelder — og de to skal ikke
    slås sammen.
    """
    med = [r["farge"] for r in runder if r["farge"] != FARGE_MANGLER]
    if not med:
        return "ikke oppgitt i noen runde"
    kjede = [med[0]] + [f for forrige, f in zip(med, med[1:]) if f != forrige]
    if len(kjede) == 1:
        if len(med) == len(runder):
            return f"{kjede[0]} i alle {len(runder)} rundene"
        return f"{kjede[0]} i {len(med)} av {len(runder)} runder"
    return " → ".join(kjede)


FORSIDEKILDER = ("akvakultur", "eierskap", "lusetall", "trafikklysvedtak")

# TEGNFORKLARINGEN, I DEN REKKEFØLGEN FARGENE HØRER.
#
# Rekkefølgen er kildens egen alvorsgrad, ikke alfabetisk: rød, gul,
# grønn. «Ikke oppgitt» står sist, fordi den ikke er en farge men et
# fravær.
TEGNFORKLARING = (
    ("lys-rod", "rød"),
    ("lys-gul", "gul"),
    ("lys-gronn", "grønn"),
    ("rute--skravert", "ikke oppgitt"),
)


# SETNINGEN OM LOKALITETENE UTEN OMRÅDE. Ett sted, tre sider.
#
# Fram til 24.09.2026 sa forsiden «landbaserte anlegg og
# ferskvannslokaliteter har ingen», og lokalitetsindeksen det samme i
# parentes. Begge var for enkle: MÅLT 24.09.2026 er 402 av de 813 på
# land og 284 i ferskvann, brakkvann eller blandet — men 44 er
# slakterier, og 299 er sjølokaliteter for skjell, alger eller annen
# fisk. Og 56 er lakselokaliteter i sjø, som forklaringen ikke dekket i
# det hele tatt.
UTEN_OMRAADE_TEKST = (
    "Produksjonsområdene gjelder oppdrett av laks og ørret i sjø. "
    "{forklart} av de {uten} lokalitetene uten område er landanlegg, "
    "ferskvannslokaliteter, slakterier eller sjølokaliteter for andre "
    "arter. {rest} lakselokaliteter i sjø står også uten område i "
    "registeret; registeret sier ikke hvorfor."
)


def uten_omraade(akva: dict[str, dict[str, str]]) -> dict[str, int]:
    """Hvor mange lokaliteter som står uten produksjonsområde, og hvorfor.

    TALLENE HENTES AV DATAENE VED BYGGING, ikke skrevet inn. En setning
    med et tall i seg er en påstand som råtner: «757 av 813» er sann den
    uka den skrives, og usann uka etter uten at noe sier fra.

    Resten — lakselokaliteter i SJØ og SALTVANN som ikke er slakteri —
    er de som forklaringen ikke dekker. MÅLT 24.09.2026: 56 av 813, og
    registeret oppgir ingen grunn.
    """
    uten = [a for a in akva.values()
            if not (a.get("prodomraade_kode") or "").strip()]
    rest = [a for a in uten
            if a.get("plasseringstype") == "Offshore"
            and a.get("vanntype") == "Salt"
            and a.get("er_slakteri") != "True"
            and "SALMON" in (a.get("arter") or "")]
    return {"uten": len(uten), "rest": len(rest),
            "forklart": len(uten) - len(rest)}


def uten_omraade_tekst(akva: dict[str, dict[str, str]]) -> str:
    """`UTEN_OMRAADE_TEKST` med tallene fra dataene."""
    tall = uten_omraade(akva)
    return UTEN_OMRAADE_TEKST.format(
        forklart=visningsord.tall(tall["forklart"]),
        uten=visningsord.tall(tall["uten"]),
        rest=visningsord.tall(tall["rest"]))


def _tegnforklaring(omraader: list[dict]) -> list[dict]:
    """Bare de tegnene tabellen FAKTISK bruker, i fast rekkefølge.

    Fram til 24.09.2026 sto alle fire fast i malen, med en kommentar om
    at den skraverte ruta ble stående selv om ingen celle brukte den.
    Begrunnelsen — «en runde som ikke er lest ennå skal se ut som det»
    — gjelder ruta i STRIPA, og den forklarer nettopp hvorfor tegnet
    skal vises NÅR det brukes. En forklaring på et tegn som ikke står
    noe sted, er en forklaring leseren leter etter og ikke finner.
    """
    i_bruk = set()
    for o in omraader:
        if o.get("farge_klasse"):
            i_bruk.add(o["farge_klasse"])
        for s in o.get("stripe") or ():
            i_bruk.add(s.get("klasse") or "rute--skravert")
    return [{"klasse": k, "ord": ord_} for k, ord_ in TEGNFORKLARING
            if k in i_bruk]


def _herofoto(felles: Felles) -> dict:
    """Heroens bildetekst: sted, produksjonsområde og fotograf.

    STEDET LENKER TIL ET PRODUKSJONSOMRÅDE, og koden SLÅS OPP I
    REGISTERET — den er ikke skrevet av. Kommunen er nøkkelen, og
    svaret er området hver lokalitet i den kommunen ligger i.

    ENTYDIG ELLER INGEN LENKE. Finner oppslaget to ulike koder, er det
    ikke ett område kommunen «ligger i», og en lenke ville valgt det
    ene på leserens vegne. Da står stedet uten lenke — og byggeloggen
    sier hvorfor, framfor at en lenke stille blir borte.

    LOKALITETER UTEN OMRÅDE TELLER IKKE SOM UENIGHET. `null` er ikke en
    annen kode; det er fraværet av en. Målt for Bømlo 27.09.2026: 41
    lokaliteter, 16 i PO 3 «Karmøy til Sotra», 25 uten kode — 18
    sjølokaliteter for skjell og andre arter, og 7 på land eller i
    ferskvann. Trafikklysordningen omfatter dem ikke, og at de mangler
    kode sier ingenting om hvor kommunen ligger.

    Samme skille som ellers i repoet: å telle en tom verdi som en
    motstridende verdi, er regel 1b-2s feilform.
    """
    kommune = HEROFOTO["kommune"]
    koder = {d.get("prodomraade_kode") or ""
             for d in felles.akva.values()
             if (d.get("kommune") or "").upper() == kommune}
    koder.discard("")
    ut = dict(HEROFOTO)
    ut["po"] = koder.pop() if len(koder) == 1 else ""
    ut["po_navn"] = felles.po_navn.get(ut["po"], "")
    ut["koder"] = sorted(koder) if len(koder) > 1 else []
    if not ut["po"]:
        # STILLE BORTFALL ER DET ENESTE UAKSEPTABLE UTFALLET. En lenke
        # som forsvinner uten at noe sier fra, ser ut som et designvalg.
        print(f"  heroens bildetekst: {kommune} gir "
              f"{len(ut['koder']) or 'ingen'} produksjonsområde"
              f"{'r' if len(ut['koder']) != 1 else ''}"
              f"{' ' + ', '.join(ut['koder']) if ut['koder'] else ''}"
              f" — stedet står uten lenke")
    return ut


def bygg_forside(felles: Felles) -> dict:
    """Alt forsiden viser: heroen, uka, arkivtallene, kysten og feedene.

    Rekkefølgen i dicten er sidens: hero, denne uka, arkivtall, kysten,
    følg med.
    """
    _punkter, uten, _hoyde, _gitter = kartpunkter(felles.akva)
    uker = les_endringsuker(felles)
    uke = uker[0] if uker else None
    omraader = _omraaderader(felles)
    akva_datoer = snapshot.datoer("akvakultur")

    return {
        # HEROENS BILDETEKST. Stedet, fotografen, og produksjonsområdet
        # slått opp i registeret — se `_herofoto()`.
        "herofoto": _herofoto(felles),

        # ---- tallene ----
        "lokaliteter": len(felles.akva),
        "produksjonsomraader": len(felles.po_navn),
        "selskaper": sum(1 for o in felles.tillatelser_per_eier
                         if not personeier(o, felles)),
        "tillatelser": len(felles.eierskap),
        "luke_uker": len(felles.lusetall_snapshots),
        "lus_fra": (felles.lusetall_snapshots[0]
                    if felles.lusetall_snapshots else ""),
        "lus_til": (felles.lusetall_snapshots[-1]
                    if felles.lusetall_snapshots else ""),
        "akva_dato": felles.akva_dato,
        "akva_hentet": felles.akva_hentet,
        "eierskap_dato": felles.eierskap_dato,

        # ---- denne uka ----
        "uke": uke,
        "sammendrag": _sammendrag(uke)[:FORSIDESETNINGER],
        # UKAS STØRSTE TYPER, som stolper med lenke til typesiden. Se
        # `ukas_typer()`.
        "ukas_typer": ukas_typer(uke),
        # `forskriftslinje` OG `rader` STO HER TIL 27.09.2026.
        #
        # Tidslinja er FLYTTET til ukessiden og ikke slettet — den sier
        # noe ingen annen komponent sier. Tabellen er borte helt: hele
        # uka står på `/endringer/<uke>/`, og åtte av 440 rader over en
        # lenke til alle 440 er en omvei til den lenka.
        "forrige_uke": (uker[1]["slug"] if len(uker) > 1 else ""),
        "forrige_uke_vist": (uker[1]["vist"] if len(uker) > 1 else ""),
        "uker_totalt": len(uker),

        # ---- arkivtall ----
        # SNAPSHOTS, ikke filer: `snapshot.datoer()` teller datoer, og
        # to versjoner av samme dato er ett øyeblikksbilde av verden.
        "snapshots": len(akva_datoer),
        "forste_snapshot": akva_datoer[0] if akva_datoer else "",
        "siste_snapshot": akva_datoer[-1] if akva_datoer else "",
        "sjekksum": felles.sjekksum,

        # ---- kysten ----
        "omraader": omraader,
        "uten_omraade": uten_omraade_tekst(felles.akva),
        # BARE TEGNENE TABELLEN BRUKER. Se `_tegnforklaring()`.
        "tegnforklaring": _tegnforklaring(omraader),
        "kart": kart.kystkart(omraader),
        "i_omraade": sum(len(v) for v in felles.lokaliteter_per_po.values()),
        "runder": [d[:4] for d in felles.runder],

        # ---- det kartet IKKE viser ----
        #
        # PUNKTKARTET ER BORTE fra forsiden. Fram til 22.09.2026 var
        # forsidens kart 1 782 prikker med et gradnett; overleveringen
        # setter områdekartet der i stedet, og to kart over det samme
        # landet på den samme siden er ett kart for mye.
        #
        # Regnskapet over lokaliteter UTEN koordinater følger ikke med
        # prikkene ut. Det er uenighetsregelen (docs/REGEL-UENIGE-KILDER.md):
        # et punkt som mangler skal ikke bare forsvinne. Tallet står i
        # kartets bildetekst her, og hele lista står på
        # /lokalitet/#akvakultur-uten-koordinater — der alle 1 782
        # uansett er.
        "uten_koordinater_antall": len(uten),

        # ---- analysen ----
        # Tallene er lest av søknadslista i `felles`, ikke av analysen:
        # forsiden skal ikke regne om Mattilsynets kropper for en lenke.
        "unntak": _forside_unntak(felles),
    }


def _forside_unntak(felles: Felles) -> dict | None:
    """Lenka til analysesiden, med tallene den kan stå for. None når
    siden ikke bygges."""
    if not felles.unntak:
        return None
    resultat = {nr: {r["resultat"] for r in rader}
                for nr, rader in felles.unntak.items()}
    return {"url": "/" + "/".join(UNNTAK_STI) + "/",
            "lokaliteter": len(resultat),
            "godkjent": sum(1 for v in resultat.values() if v == {"Godkjent"}),
            "avslag": sum(1 for v in resultat.values() if v == {"Avslag"})}


def skriv_forside(rot: Path, felles: Felles, mal=None) -> Path:
    """Rendrer og skriver forsiden."""
    f = bygg_forside(felles)
    mal = mal or _miljo().get_template("forside.html.j2")
    html = mal.render(
        f=f,
        **_grunnkontekst(
            felles, rot, rot / "index.html", kilder=FORSIDEKILDER,
            tittel="Kystloggen — norske akvakulturlokaliteter, uke for uke",
            beskrivelse=(
                f"Offentlige registerdata om {f['lokaliteter']} norske "
                f"akvakulturlokaliteter, sammenstilt og datert: eierskap, "
                f"trafikklysfarge, lusetall og hva som har endret seg."),
            jsonld=jsonld_forside(f, felles.vilkaar),
            proveniens_tekst=proveniens(felles.akva_dato, felles.akva_hentet),
            feed="/endringer/feed.xml",
            feed_tittel="Kystloggen: alle endringer",
            kart=True,
            sidetype="Forside",
            undertittel="Et uavhengig arkiv over offentlige data om "
                        "norsk havbruk",
            main_klasse="fullbredde"),
    )
    return skriv_side(rot / "index.html", html)


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
        "name": "Kystloggen — norske akvakulturlokaliteter uke for uke",
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
    # Samme FIRE ledd som lokalitetssidens registertabell: kildens
    # feltnavn til `data-felt`, etiketten til øyet, verdien oversatt, og
    # da vi sist SÅ feltet endre seg. To registertabeller som viste
    # ulike kolonner ville vært to former for det samme.
    # FEM LEDD, som på lokalitetssiden. Femte er fargeklassen, og den
    # er tom for hvert felt her — selskapsregisteret har ingen farge.
    # Samme form i begge tabellene er likevel riktig: to registertabeller
    # med hver sin radform er to maler som må huske hver sin.
    register = [(f, visningsord.felt(f), visningsord.verdi(f, reg[f]),
                 felles.sist_endret.get((orgnr, f), ""),
                 FARGE_KLASSE.get(_fargekode(str(reg[f]).strip().lower()), ""))
                for f in SELSKAPSFELT if reg.get(f)]

    # Lokalitetene tillatelsene ligger på. En tillatelse kan ligge på
    # flere, og flere tillatelser kan ligge på samme — derfor et sett,
    # sortert som tall.
    # INNEHAVER SIDEN, per tillatelse: den SENESTE journalførte
    # overføringen til dette organisasjonsnummeret. Ikke den første —
    # en tillatelse kan ha vært innom og tilbake, og det er den siste
    # ankomsten som gjelder nå.
    siden_per_till: dict[str, str] = {}
    for nr in tillatelser:
        datoer = [o.get("journal_dato", "")
                  for o in felles.overforinger_per_tillatelse.get(nr, ())
                  if (o.get("mottaker_orgnr") or "").strip() == orgnr]
        if datoer:
            siden_per_till[nr] = max(datoer)

    lokaliteter: dict[str, dict] = {}
    for nr in tillatelser:
        for loknr in _liste(mine[nr].get("lokaliteter")):
            a = felles.akva.get(loknr)
            if a is None:
                continue
            post = lokaliteter.setdefault(loknr, {
                "loknr": loknr,
                "navn": visningsord.tittelform(a.get("navn", "")),
                "original": a.get("navn", ""),
                "kommune": a.get("kommune", ""),
                "po_kode": a.get("prodomraade_kode", ""),
                "po_navn": a.get("prodomraade_navn", ""),
                "status": visningsord.verdi("prodomraade_status",
                                            a.get("prodomraade_status", "")),
                "status_klasse": FARGE_KLASSE.get(_fargekode(
                    (a.get("prodomraade_status") or "").strip().lower()), ""),
                "kapasitet": visningsord.maalt(a.get("kapasitet", ""),
                                               a.get("kapasitet_enhet", "")),
                "siden": "",
                "tillatelser": [],
            })
            post["tillatelser"].append(nr)
            # ELDSTE ankomst blant tillatelsene på lokaliteten: det er
            # da selskapet FIKK fotfeste der. Den seneste ville sagt når
            # den nyeste tillatelsen kom, som er noe annet.
            d = siden_per_till.get(nr, "")
            if d and (not post["siden"] or d < post["siden"]):
                post["siden"] = d

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

    # ---- EIERSKAP OVER TID ----
    #
    # «Kom til» og «Gikk ut», slik overleveringen ber om. Vi har det
    # FØRSTE av de to og ikke det andre, og forskjellen er verdt å si:
    #
    #   KOM TIL    `eierskap_historikk` journalfører hver overføring TIL
    #              et organisasjonsnummer. Den datoen er kildens.
    #   GIKK UT    finnes ikke som en hendelse. En tillatelse som er
    #              overført VEKK er bare ikke lenger i selskapets
    #              portefølje, og journalraden står på MOTTAKEREN.
    #
    # Vi kan utlede den: en tillatelse selskapet har mottatt, som nå
    # eies av noen andre, er gått ut — og datoen er neste overføring i
    # rekka. Det er en SLUTNING, og den merkes som det.
    ut_av: list[dict] = []
    for nr, overf in felles.overforinger_per_tillatelse.items():
        rekka = sorted(overf, key=lambda o: (o.get("journal_dato", ""),
                                             o.get("rekkefolge", "")))
        for i, o in enumerate(rekka[:-1]):
            if (o.get("mottaker_orgnr") or "").strip() != orgnr:
                continue
            neste = rekka[i + 1]
            # IKKE `navn`: det er selskapets eget navn, og det står på
            # sida under. Fram til 05.10.2026 overskrev denne løkka det,
            # og 28 selskapssider fikk MOTTAKERENS navn i tittelen.
            mottaker, mottaker_felt, _orgnr = _navn_eller_skjult(
                neste.get("mottaker_navn", ""), "mottaker_navn",
                neste.get("mottaker_orgnr", ""), felles.former)
            ut_av.append({
                "dato": neste.get("journal_dato", ""),
                "tillatelse": nr,
                "navn": mottaker,
                "navn_felt": mottaker_felt,
                "retning": "ut",
                "slag": "Gikk ut",
                "hva": f"{nr} overført videre",
                "presisjon": "utledet: neste journalførte overføring",
            })

    eierskapslinje = sorted(
        [{"dato": o["dato"], "tillatelse": o["tillatelse"],
          "navn": "", "navn_felt": "", "retning": "inn", "slag": "Kom til",
          "hva": f"{o['tillatelse']} overført hit",
          "presisjon": "journalført senest denne datoen"}
         for o in overforinger] + ut_av,
        key=lambda o: (o["dato"], o["tillatelse"]), reverse=True)

    lokalitetsrader = [lokaliteter[k] for k in
                       sorted(lokaliteter, key=lambda e: int(e) if e.isdigit() else 0)]
    # HØYRESPALTA: hvor langs kysten lokalitetene ligger, og hvor mange
    # i hvert område. Tellingen er av de samme lokalitetene som lista.
    per_po = _po_fordeling(felles, lokaliteter)
    marg = ({"kart": kart.minikart(_koordinater(felles, lokaliteter)),
             "per_po": per_po,
             "utenfor_po": len(lokaliteter) - sum(r["antall"] for r in per_po)}
            if lokaliteter else None)
    samlet = _samlet_kapasitet(mine)
    endringer, vindu = _selskapsendringer(orgnr, sorted(lokaliteter),
                                          tillatelser, felles)

    return {
        "orgnr": orgnr,
        "navn": navn,
        # ORGANISASJONSNUMMERET GRUPPERES ALDRI, heller ikke i en
        # overskrift. `publiseringsvakt.NI_SIFFER` er «ni siffer på
        # rad», og «912 345 678» ville vært usynlig for den. Se
        # visningsord, regel 3.
        "enhetsregisteret_url":
            f"https://virksomhet.brreg.no/nb/oppslag/enheter/{orgnr}",
        "har_registerdata": bool(register),
        "register": register,
        "uten_registerdata_tekst": UTEN_REGISTERDATA,
        "enhet_dato": felles.enhet_dato,
        "eierskap_dato": felles.eierskap_dato,
        "akva_dato": felles.akva_dato,
        "tillatelser": [dict(r, siden=siden_per_till.get(r["nr"], ""))
                        for r in _tillatelsesrader(mine, [],
                                                   felles.former)],
        "tillatelser_antall": len(tillatelser),
        "lokaliteter": lokalitetsrader,
        "lokaliteter_antall": len(lokaliteter),
        "marg": marg,
        "overforinger": overforinger,

        # ---- nøkkeltallene i overskriften ----
        "samlet_kapasitet": samlet["vist"],
        "kapasitet_per_enhet": samlet["biter"],
        "kapasitetsenheter": samlet["enheter"],
        # VESENTLIGE ENDRINGER SISTE KVARTAL, og vinduet de er talt i.
        # Se `_selskapsendringer()` og `endringsvindu()`.
        "endringer": endringer,
        "endringsvindu": vindu,
        "aapen_liste": SELSKAP_AAPEN_LISTE,
        "nyeste_endringer": SELSKAP_NYESTE_ENDRINGER,
        "i_arkivet_siden": min((o["dato"] for o in overforinger), default=""),
        "eierskapslinje": eierskapslinje,
        "kom_til": sum(1 for o in eierskapslinje if o["retning"] == "inn"),
        "gikk_ut": sum(1 for o in eierskapslinje if o["retning"] == "ut"),

        "siter": {
            "url": f"{_basisurl()}/selskap/{orgnr}/",
            "uke": visningsord.uke(felles.eierskap_dato),
            "dato": visningsord.dato(felles.eierskap_dato),
            "aar": felles.eierskap_dato[:4],
            "sjekksum": _sjekksum("eierskap"),
        },
    }


# SELSKAPSSIDENS ENDRINGSVINDU: et kvartal, regnet i hele uker.
SELSKAP_UKER = 13

# En liste med flere rader enn dette står LUKKET på selskapssiden. Under
# grensa er en lukket liste bare et ekstra klikk. MÅLT 08.10.2026 på
# 390 px: selskapet med flest lokaliteter (158) var 150 018 px høyt med
# alle listene åpne.
SELSKAP_AAPEN_LISTE = 10

# Når endringslista er lukket, står de NYESTE likevel åpent over den —
# briefen setter vesentlige endringer øverst på selskapssiden. Fem, så
# siden holder seg under 5 000 px på 390 også for de største selskapene.
SELSKAP_NYESTE_ENDRINGER = 5

# (felles, {orgnr: tillatelser selskapet har GITT FRA SEG}). Bygget én
# gang per batch. Selve objektet holdes og sammenlignes med `is`, ikke
# `id()`: en id kan gjenbrukes etter at objektet er borte.
_AVGITT: list = [None, {}]


def _avgitte_tillatelser(orgnr: str, felles: Felles) -> set[str]:
    """Tillatelser der changeloggen viser at eieren GIKK FRA dette
    organisasjonsnummeret. De eies av noen andre nå, og står derfor ikke
    i `tillatelser_per_eier` — men at selskapet ga slipp på dem, er en
    endring for selskapet. Uten dem ville et salg vært usynlig på
    selgerens side."""
    if _AVGITT[0] is not felles:
        avgitt: dict[str, set[str]] = defaultdict(set)
        for eid, rader in felles.registerendringer.items():
            for r in rader:
                if (r["source"] == "eierskap" and r["field"] == "eier_orgnr"
                        and r["old_value"]):
                    avgitt[str(r["old_value"]).strip()].add(eid)
        _AVGITT[:] = [felles, dict(avgitt)]
    return _AVGITT[1].get(orgnr, set())


def _selskapsendringer(orgnr: str, lokaliteter: list[str],
                       tillatelser: list[str], felles: Felles,
                       uker: int = SELSKAP_UKER
                       ) -> tuple[list[dict], dict | None]:
    """(vesentlige endringer i vinduet, nyest først; vinduet).

    SAMME REGLER SOM LOKALITETSSIDENS TIDSLINJE, fra det samme stedet:
    `_lokalitetsendringer()` klassifiserer og slår sammen. Radene er
    endringer på selskapets lokaliteter, på tillatelsene det eier, og på
    tillatelsene det har gitt fra seg. En tillatelse som ligger på flere
    av lokalitetene, telles én gang.
    """
    vindu = endringsvindu(max(felles.akva_dato, felles.eierskap_dato),
                          felles.dekning_fra, uker)
    if not vindu:
        return [], None
    rader: list[dict] = []
    for loknr in lokaliteter:
        rader += [r for r in felles.registerendringer.get(loknr, ())
                  if r["source"] not in ENDRINGER_VIA_TILLATELSE]
    for nr in sorted(set(tillatelser) | _avgitte_tillatelser(orgnr, felles)):
        rader += [r for r in felles.registerendringer.get(nr, ())
                  if r["source"] in ENDRINGER_VIA_TILLATELSE]
    rader = [r for r in rader
             if vindu["fra"] < str(r["observed_at"])[:10] <= vindu["til"]]
    rader.sort(key=lambda r: str(r["observed_at"]), reverse=True)
    poster = slaa_sammen_trukne(_lokalitetsendringer(rader, ""))
    poster = vesentlige_i_vinduet(poster, vindu)
    for p in poster:
        eid = p["entity_id"]
        a = felles.akva.get(eid)
        p["gjelder"] = (f"tillatelse {eid}" if a is None
                        else f"lokalitet {eid}")
        p["lokalitet"] = eid if a is not None else ""
        p["lokalitetsnavn"] = (visningsord.tittelform(a.get("navn", ""))
                               if a is not None else "")
        # EN TOM VERDI MERKES IKKE MED KILDENS FELTNAVN — som i
        # `_observert_historikk()`.
        p["fra_felt"] = feltmerke(p["fra"], p["felt"])
        p["til_felt"] = feltmerke(p["til"], p["felt"])
    poster.sort(key=lambda r: _omvendt(r["dato"]))
    return poster, vindu


def _samlet_kapasitet(mine_till: dict) -> dict:
    """Summen av tillatelsenes kapasitet — og enhetene den er i.

    ## EN SUM MED FLERE ENHETER ER IKKE ÉN SUM

    `kapasitet_enhet` varierer mellom tonn, stykk, dekar,
    kvadratmeter, kubikkmeter og liter i det samme registeret. Å legge
    dem sammen ville gitt et tall uten mening, og å vise det uten
    enheten ville skjult at det er tullete.

    Summen regnes derfor PER ENHET, og alle enhetene vises. Har
    selskapet bare tonn, ser det ut som det designet ber om; har det
    to, sier siden det.
    """
    per_enhet: dict[str, float] = defaultdict(float)
    for d in mine_till.values():
        raa = (d.get("kapasitet") or "").strip()
        enhet = (d.get("kapasitet_enhet") or "").strip()
        try:
            per_enhet[enhet] += float(raa)
        except ValueError:
            continue
    biter = [visningsord.maalt(verdi, enhet)
             for enhet, verdi in sorted(per_enhet.items(),
                                        key=lambda kv: -kv[1])]
    return {"vist": " + ".join(biter), "biter": biter,
            "enheter": len(per_enhet)}


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
        "creator": {"@type": "Organization", "name": "Kystloggen"},
    })


def skriv_selskap(orgnr: str, rot: Path, felles: Felles, mal=None) -> Path:
    """Rendrer og skriver én selskapsside."""
    sel = bygg_selskap(orgnr, felles)
    vist_navn = visningsord.selskapsnavn(sel["navn"])
    mal = mal or _miljo().get_template("selskap.html.j2")
    html = mal.render(
        sel=sel,
        **_grunnkontekst(
            felles, rot, rot / "selskap" / orgnr / "index.html",
            kilder=SELSKAPSKILDER,
            # NAVNET I MENNESKELIG FORM i tittel, beskrivelse og
            # søketekst — det er det en søkemotor og en treffliste viser.
            # JSON-LD og siteringen bærer den rå verdien.
            tittel=f"{vist_navn or sel['orgnr']} — Kystloggen",
            beskrivelse=(
                f"Akvakulturtillatelser, lokaliteter og overføringer for "
                f"organisasjonsnummer {sel['orgnr']}"
                f"{' (' + vist_navn + ')' if vist_navn else ''}."),
            jsonld=jsonld_selskap(sel, felles.vilkaar),
            proveniens_tekst=proveniens(
                felles.eierskap_dato, _hentet("eierskap"),
                "Registerdataene om selskapet er fra "
                "Enhetsregisteret."),
            meny_aktiv="selskap",
            # ORGANISASJONSNUMMER · ANTALL LOKALITETER. Nummeret er
            # identiteten — to selskaper kan hete nesten det samme — og
            # antall lokaliteter er størrelsen. Nummeret grupperes
            # ALDRI, se visningsord regel 3.
            sidetype="Selskap",
            undertittel=(f"{orgnr}{SKILLE}"
                         f"{visningsord.antall(sel['lokaliteter_antall'], 'lokalitet', 'lokaliteter')}"),
            soketekst=vist_navn or orgnr,
            main_klasse="fullbredde",
            feed=f"/selskap/{orgnr}/feed.xml",
            feed_tittel=f"Kystloggen: endringer for {vist_navn or orgnr}"),
    )
    return skriv_side(rot / "selskap" / orgnr / "index.html", html)


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
        "creator": {"@type": "Organization", "name": "Kystloggen"},
    }
    if po["runder"]:
        data["temporalCoverage"] = (f"{po['runder'][0]['aar']}/"
                                    f"{po['runder'][-1]['aar']}")
    return _script_trygg(data)


def skriv_produksjonsomrade(po: str, rot: Path, felles: Felles,
                            mal=None) -> Path:
    """Rendrer og skriver én produksjonsområdeside."""
    d = bygg_produksjonsomrade(po, felles)
    mal = mal or _miljo().get_template("produksjonsomrade.html.j2")
    html = mal.render(
        po=d,
        **_grunnkontekst(
            felles, rot, rot / "produksjonsomrade" / po / "index.html",
            kilder=PO_KILDER,       # kaster på UBELAGT
            # DEPARTEMENTETS EGNE ORD står på denne siden, med lenke til
            # regjeringen.no. Ingen `Source.attribusjon` bærer det, og en
            # fraskrivelse som utelot parten hvis ord er sitert, ville
            # utelatt den ene som betyr mest her.
            siterte_organ=("regjeringen.no",),
            tittel=f"Produksjonsområde {d['nr']} {d['navn']} — Kystloggen",
            beskrivelse=(
                f"Trafikklysfarge per runde for produksjonsområde {d['nr']} "
                f"{d['navn']}, med lesemåte, og de {d['lokaliteter_antall']} "
                f"lokalitetene i området."),
            jsonld=jsonld_po(d, felles.vilkaar),
            proveniens_tekst=proveniens(
                felles.akva_dato, felles.akva_hentet,
                "Forskriftsrundene er lest fra Lovdata."),
            meny_aktiv="produksjonsomrade",
            kart=d["kart"] is not None,
            sidetype="Produksjonsområde",
            undertittel=(
                f"{visningsord.antall(d['lokaliteter_antall'], 'lokalitet', 'lokaliteter')}"
                f"{SKILLE}"
                f"{visningsord.antall(d['selskaper_antall'], 'selskap', 'selskaper')}"
                f"{SKILLE}{d['naa']['farge']} nå"),
            soketekst=d["navn"],
            main_klasse="fullbredde",
            feed=f"/produksjonsomrade/{po}/feed.xml",
            feed_tittel=f"Kystloggen: endringer i produksjonsområde {po}"),
    )
    return skriv_side(rot / "produksjonsomrade" / po / "index.html", html)


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
    endringssider: int = 0
    endringsuker: int = 0
    feeder: int = 0
    # Analysesidene som ble skrevet. 0 er et svar og står i rapporten:
    # uten arkivert søknadsliste bygges ikke /analyse/unntaksvekst/.
    analyser: int = 0
    sok: dict = None
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
        if self.sok is None:
            self.sok = {"bygget": False, "filer": 0, "byte": 0,
                        "melding": "ikke kjørt"}
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

    # ANALYSESIDEN. Egen fase i tidsmålingen: den leser Mattilsynets
    # kropper og BarentsWatchs uker på nytt, og en fase som ikke måles er
    # en fase ingen ser vokse.
    t0 = time.perf_counter()
    try:
        logg.analyser = 1 if skriv_unntaksvekst(rot, felles) else 0
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("analyse/unntaksvekst",
                            f"{type(feil).__name__}: {feil}"))
    tider["analyse"] = time.perf_counter() - t0

    # ENDRINGSSIDENE OG FEEDENE bygges av de SAMME ukene. Ett kall til
    # `les_endringsuker()`, og begge leser resultatet: to veier til det
    # samme regnskapet er formen F6 og F7 hadde, og for en feed er
    # prisen at en leser får en post som ikke finnes på siden.
    t0 = time.perf_counter()
    try:
        uker = les_endringsuker(felles)
        logg.endringssider = len(
            [s for s in skriv_endringssider(rot, felles, uker)
             if s.name == "index.html"])
        logg.endringsuker = len(uker)
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("endringer", f"{type(feil).__name__}: {feil}"))
        uker = []
    tider["endringssider"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        skriv_sok(rot, felles, uker)
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("sok", f"{type(feil).__name__}: {feil}"))

    try:
        logg.feeder = len(skriv_feeder(rot, felles, uker))
    except Exception as feil:                        # noqa: BLE001
        logg.feilet.append(("feeder", f"{type(feil).__name__}: {feil}"))
    tider["feeder"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    for skriv in (lambda: skriv_stil(rot),
                  lambda: skriv_fonter(rot),
                  lambda: skriv_ikoner(rot),
                  lambda: skriv_bilder(rot),
                  lambda: skriv_skript(rot),
                  lambda: skriv_sitemap(rot, felles),
                  lambda: skriv_robots(rot),
                  lambda: skriv_llms(rot, felles),
                  lambda: skriv_vertsfiler(rot),
                  lambda: skriv_404(rot, felles)):
        try:
            skriv()
        except Exception as feil:                    # noqa: BLE001
            logg.feilet.append(("maskinfiler", f"{type(feil).__name__}: {feil}"))
    tider["maskinfiler"] = time.perf_counter() - t0

    # SØKEINDEKSEN SIST. Den leser den ferdige HTML-en fra disk, så hver
    # side må være skrevet — også `/sok/` selv.
    t0 = time.perf_counter()
    logg.sok = skriv_sokeindeks(rot)
    tider["sokeindeks"] = time.perf_counter() - t0

    return logg, tider


# --------------------------------------------------------- porten


def vaktmelding(kjores_av: str) -> str:
    """Linja bygget skriver når det ikke kjørte porten selv.

    ## TO GRUNNER TIL Å HOPPE OVER, og de betyr motsatte ting

    Fram til 23.09.2026 fantes bare `--uten-vakt`, og meldingen var
    «VAKTEN ER HOPPET OVER. Siden skal ikke publiseres.» Den er riktig
    for et utviklingsbygg: ingen har gransket denne mappa, og da skal den
    ikke ut.

    Men `publiser.py` steg 2 sendte samme flagg, og den KJØRER porten —
    i sitt eget steg, med vilje, slik at `--uten-bygg` ikke kan hoppe
    over den. Meldingen sa da at en side ikke skulle publiseres, midt i
    skriptet som var i ferd med å publisere den etter en ren port. En
    advarsel som er usann i normaltilfellet er en advarsel ingen leser
    den dagen den er sann.

    Flagget bar altså ÉN bit der spørsmålet har to svar: «ingen gransker
    dette» og «noen andre gransker det». Skillet kan ikke gjettes her —
    bare den som kaller vet det — så det kommer inn som et navn, på
    samme måte som kjøredatoen i CLAUDE.md 1b. Tom streng er «ingen»,
    ikke en antakelse om hvem.
    """
    if kjores_av:
        return f"\nVAKTEN ER IKKE KJØRT HER. Den kjøres av {kjores_av}."
    return "\nVAKTEN ER HOPPET OVER. Siden skal ikke publiseres."


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

    # GRENSA I HISTORIKKEN. Filene fra før 23.09.2026 har ingen
    # kodeproveniens, og de kan ikke rettes — men tallet skrives hver
    # kjøring, av samme grunn som `filtrert_bort()`. Det skal synke.
    uten = publiseringsvakt.kodeproveniens_ukjente()
    if uten:
        sum_ = sum(int(f.utdrag.split()[0]) for f in uten)
        print(f"\n{sum_} snapshotfiler har ingen kodeproveniens "
              f"(skrevet før 23.09.2026, blokkerer ikke):")
        for f in uten:
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
          f"+ {logg.indekssider} indekssider + {logg.endringssider} "
          f"endringssider ({logg.endringsuker} uker) skrevet til {rot}")
    print(f"  {logg.feeder} Atom-feeder")
    print(f"  {logg.analyser} analyseside(r)"
          + ("" if logg.analyser else
             " — ingen arkivert søknadsliste i data/arkiv/unntaksvekst/"))
    # SØKEINDEKSEN RAPPORTERES ALLTID, også når den ikke ble bygget: et
    # søk som stille slutter å virke er formen på feilene i CLAUDE.md 1b.
    print(f"  søkeindeks    {'bygget' if logg.sok['bygget'] else 'IKKE BYGGET'}"
          f"  {logg.sok['filer']} filer, {logg.sok['byte'] / 1e6:.1f} MB")
    print(f"                {logg.sok['melding']}")
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


# ---------------------------------------------- BYGGET BYTTES INN
#
# Fram til 26.09.2026 skrev bygget rett oppå målmappa. Da ble hver fil
# det LAGER erstattet — og hver fil det ikke lenger lager, ble stående.
#
# MÅLT samme dag på `data/nettsted`: 119 filer ingen bygging fra main
# lager lenger. Tre av dem var herofotografiene, som porten stoppet
# publiseringen på; de 116 andre var pagefind-indeksfiler med
# innholdsadresserte navn, som får nytt navn ved hver bygging og derfor
# hadde hopet seg opp usett.
#
# Feilen er ikke bildene. Feilen er at en målmappe som skrives oppå,
# er summen av ALLE byggingene som noen gang har truffet den — og en
# slik mappe kan ingen prøve uttale seg om, fordi ingen vet hva som er
# i den.
#
# Bygget skriver derfor i en TOM mappe og bytter den inn til slutt.
# Feiler bygget, blir den gamle stående urørt, og den halvferdige
# ligger igjen til ettersyn.

ARBEIDSMAPPE = ".ny"


def byggemappe(rot: Path) -> Path:
    """En TOM mappe å bygge i, INNE i målmappa.

    Inne i og ikke ved siden av, og det er ikke en smaksak:
    `/data/nettsted/` er ignorert i datarepoet, mens en søstermappe
    ikke ville vært det. En avbrutt bygging ville da etterlatt 300 MB
    usporet innhold, og `publiser.py` steg 1 ville stoppet på «urent
    arbeidstre» ved neste forsøk.
    """
    rot.mkdir(parents=True, exist_ok=True)
    ny = rot / ARBEIDSMAPPE
    if ny.exists():
        shutil.rmtree(ny)
    ny.mkdir()
    return ny


def bytt_inn(ny: Path, rot: Path) -> None:
    """Bytter den ferdige byggemappa inn der målmappa sto.

    TRE OMDØPINGER OG INGEN KOPIERING: mappene ligger på samme
    filsystem, så byttet er metadata. Vinduet der målmappa ikke finnes
    er de mikrosekundene den midterste omdøpingen tar, og feiler den
    siste, legges den gamle tilbake.

    Den gamle slettes FØRST når den nye står på plass. En rekkefølge
    som slettet først ville vært et bygg som river ned siden før det
    vet om det klarer å sette opp en ny.
    """
    midlertidig = rot.parent / f".{rot.name}.ny"
    gammel = rot.parent / f".{rot.name}.gammel"
    for sti in (midlertidig, gammel):
        if sti.exists():
            shutil.rmtree(sti)
    ny.rename(midlertidig)
    rot.rename(gammel)
    try:
        midlertidig.rename(rot)
    except OSError:
        gammel.rename(rot)
        raise
    shutil.rmtree(gammel)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lokalitet", default="31397",
                    help="lokalitetsnummer å bygge (standard: 31397)")
    ap.add_argument("--alle", action="store_true",
                    help="bygg hver lokalitet i nyeste akvakultur-snapshot")
    ap.add_argument("--grense", type=int, default=None,
                    help="med --alle: bygg bare de N første (for en prøve)")
    ap.add_argument("--ut", default=str(UT), help="målmappe")
    # DE TO MÅTENE Å IKKE KJØRE PORTEN HER, og de utelukker hverandre
    # fordi de betyr motsatte ting. Se `vaktmelding()`. Ett flagg som
    # kunne stå sammen med det andre, ville vært to steder som kan si
    # ulike ting om samme sak.
    vakt = ap.add_mutually_exclusive_group()
    vakt.add_argument("--uten-vakt", action="store_true",
                      help="hopp over publiseringsvakten (bare utvikling). "
                           "Siden skal da ikke publiseres.")
    vakt.add_argument("--vakt-kjores-av", default="", metavar="HVEM",
                      help="hopp over porten HER fordi den som kaller "
                           "kjører den selv — navnet skrives i meldingen. "
                           "Settes av publiser.py.")
    args = ap.parse_args()

    rot = Path(args.ut)
    if args.alle:
        bygg = byggemappe(rot)
        logg, tider = skriv_alle(bygg, args.grense)
        if logg.feilet:
            _meld_bygg(logg, tider, bygg)
            print(f"\n  BYTTET IKKE INN: bygget feilet. {rot} står som "
                  f"før, og det halvferdige ligger i {bygg}.")
            return 1
        bytt_inn(bygg, rot)
        _meld_bygg(logg, tider, rot)
    else:
        filer = (skriv_lokalitet(args.lokalitet, rot)
                 + [skriv_stil(rot)] + skriv_fonter(rot)
                 + skriv_ikoner(rot))
        for f in filer:
            print(f"{f}  ({f.stat().st_size / 1024:.0f} kB)")
        print(f"  URL: /lokalitet/{args.lokalitet}/")
        print(f"  CSV: /lokalitet/{args.lokalitet}/{CSV_FILNAVN}")

    if args.uten_vakt or args.vakt_kjores_av:
        print(vaktmelding(args.vakt_kjores_av))
        return 0
    return gransk_og_meld(rot)


if __name__ == "__main__":
    raise SystemExit(main())
