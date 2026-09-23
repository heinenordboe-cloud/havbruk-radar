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
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import polars as pl
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import beslutning                                          # noqa: E402
import kart                                                # noqa: E402
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
    """Adressen folk melder feil til, fra `HAVBRUK_KONTAKT`.

    Tom streng når den ikke er satt, og bunnteksten SIER at den ikke er
    satt framfor å skrive en påfunnet adresse. Samme skille som
    `utvalg`: tom er fraværet av en verdi, ikke en verdi.

    Leses av miljøet og ikke av en fil i repoet, fordi en e-postadresse
    i et offentlig repo er en adresse høsteroboter finner.
    """
    return (os.environ.get("HAVBRUK_KONTAKT") or "").strip()


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
                   side_skript: str = "") -> dict:
    """Nøklene `base.html.j2` krever, for hvilken som helst sidetype."""
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
        "kanonisk": kanonisk_url(sti, rot),
        "jsonld": jsonld,
        "attribusjon": attribusjon(kilder,
                                   felles.vilkaar if felles else None),
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
    # Adressen folk melder feil til. Tom når `HAVBRUK_KONTAKT` ikke er
    # satt, og da SIER bunnteksten det framfor å finne på en.
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


@lru_cache(maxsize=1)
def _les_beveg() -> pl.DataFrame:
    """Changeloggen slik NETTSTEDET skal lese den. Ett sted.

    Tre merkinger og ett filter, i den rekkefølgen:

        merk_utvalgsutvidelse   entiteten kom fordi VI begynte å spørre
        merk_feltbevegelse      det var et FELT som kom eller gikk, ikke
                                entiteten
        bevegelse()             fjerner det som ikke skjedde i verden

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
    return diff.bevegelse(alle)


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
    rader = [_endringsrad(r, loknr) for r in register_rader]
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
    return ([_endringsrad(r, loknr) for r in rader],
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
    {"id": "tillatelse", "navn": "Tillatelse", "kort": "tillatelser",
     "hva": "tillatelsens formål, kapasitet eller lokaliteter"},
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


def endringstype(source: str, field: str, change_type: str) -> str:
    """Hvilken av `ENDRINGSTYPER` en changelog-rad hører til.

    ## `ny` og `borte` slår alt annet

    En oppføring som kommer eller går er ÉN hendelse, ikke tjue. At det
    er `organisasjonsform` og `kommune` og nitten felt til som dukket
    opp samtidig, er hvordan `diff.compare()` skriver det — ikke hva som
    skjedde. Se `_ukens_hendelser()`, som slår dem sammen per entitet.
    """
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

    «MELAKS ANS», «BRØDRENE X DA». Spørsmålet stilles til
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
    from publiseringsvakt import FORM_SUFFIKS
    from core import persondata

    tekst = str(navn or "").strip()
    treff = FORM_SUFFIKS.search(tekst)
    return bool(treff) and persondata.er_personform(treff.group(1))


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
        return {
            "dato": str(rad["observed_at"]),
            "uke": _ukeslug(str(rad["observed_at"])),
            "type": "borte",
            "type_navn": "Ute av registeret",
            "kilde": kilde,
            # `entity_id` BEHOLDES IKKE. Den er et
            # organisasjonsnummer for `enhetsregisteret`, og et
            # ni-sifret tall vi ikke kan gjøre rede for er nøyaktig det
            # `NI_SIFFER` finnes for. Feed-iden bygges av dato, kilde og
            # feltantall, som er stabilt uten å bære identiteten.
            "entity_id": "",
            "felt": "change_type",
            "etikett": "Borte fra registeret",
            "fra": f"{antall_felt} felt",
            "til": IKKE_I_REGISTERET,
            "fra_felt": VERDI_MANGLER_FELT,
            "til_felt": VERDI_MANGLER_FELT,
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
        "type": slag,
        "type_navn": next(x["navn"] for x in ENDRINGSTYPER if x["id"] == slag),
        "kilde": kilde,
        "entity_id": eid,
        "felt": felt if endring == "endret" else "change_type",
        "etikett": (visningsord.felt(felt) if endring == "endret"
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

    mine = beveg.filter(pl.col("source").is_in(ukentlige))

    # TO SLAGS SAMMENSLÅING, og de har hver sin nøkkel fordi de svarer
    # på hver sin «hva skjedde egentlig én gang her».
    #
    #   ny/borte      per (kilde, entitet, dato). Én oppføring som kom
    #                 eller gikk, skrevet én gang per felt.
    #   trafikklys    per (produksjonsområde, fra, til, dato). ÉN
    #                 fargebeslutning, skrevet én gang per lokalitet i
    #                 området — se `_po_av_endring()`.
    #
    # `felt_ny`/`felt_borte` slås IKKE sammen: der er hvert felt sin
    # egen hendelse, og det er hele poenget med å skille dem ut.
    samlet: dict[tuple, dict] = {}
    rader: list[dict] = []
    for r in mine.iter_rows(named=True):
        ct = str(r["change_type"])
        if ct in ("ny", "borte"):
            nøkkel = ("entitet", str(r["source"]), str(r["entity_id"]),
                      ct, str(r["observed_at"]))
        elif (str(r["source"]), str(r["field"])) in SAMLES_PER_OMRAADE:
            nøkkel = ("omraade", str(r["source"]), str(r["field"]),
                      _po_av_endring(r, felles), str(r["old_value"]),
                      str(r["new_value"]), str(r["observed_at"]))
        else:
            rader.append(_hendelse(r, felles))
            continue
        post = samlet.get(nøkkel)
        if post is None:
            samlet[nøkkel] = {"rad": r, "felt": 1}
        else:
            post["felt"] += 1
    rader += [_hendelse(p["rad"], felles, p["felt"]) for p in samlet.values()]

    per_uke: dict[str, list[dict]] = defaultdict(list)
    for h in rader:
        per_uke[h["uke"]].append(h)

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
        datoer = sorted({h["dato"] for h in hendelser})
        antall = Counter(h["type"] for h in hendelser)
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
        egen = [h for h in hendelser if h["type"] in EGEN_DEL]
        ledet = [h for h in hendelser if h["type"] not in EGEN_DEL]
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
            "spenn": visningsord.ukespenn(datoer[0]),
            "datoer": datoer,
            "forste_dato": datoer[0],
            "siste_dato": datoer[-1],
            "hendelser": hendelser,
            "ledet": ledet,
            "egen_del": egen,
            "antall": telt,
            "antall_egen_del": len(egen),
            "ledet_slag": visningsord.liste(navn_i_ledet),
            "antall_rader": len(hendelser),
            "utenfor_tellingen": ikke_telt,
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
            "sist_endret": max(
                (d for (e, _f), d in felles.sist_endret.items() if e == loknr),
                default=""),
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
    i_omraadet = [h for u in uker for h in u["hendelser"]
                  if h["entity_id"] in mine or h["po"] == po]

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


def _eierrad(nr: str, d: dict) -> dict:
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
            "tildelt_dato": (d.get("tildelt_tid") or "")[:10],
            "tildelt_navn": "",
        }
    return {
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


def _tillatelsesrader(mine_till: dict, uten_eier: list[str]) -> list[dict]:
    """Radene i eierskapstabellen — kjente OG ugjorte rede for.

    Samme radform for begge, med `eier_felt` som skiller dem. En egen
    tabell for de ukjente ville gjort fraværet til noe man kan overse;
    en utelatt rad ville gjort det usynlig.
    """
    rader = [
        _eierrad(nr, d) for nr, d in mine_till.items()
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

    ## INGEN TILTAKSGRENSE, og ingen rustfargede søyler

    Overleveringen tegner en stiplet tiltaksgrense på 0,5 og farger
    søylene over den i rust. Begge deler er utelatt, og det er en
    beslutning og ikke en forglemmelse: **grensa er ikke samlet inn.**

    Den står i lakselusforskriften, den varierer med sesong (0,2 i
    vårperioden, 0,5 ellers) og med vedtak per lokalitet, og ingen av
    delene finnes i `lusetall`. En strek på 0,5 tegnet av oss ville
    vært en påstand om regelverket, ikke en gjengivelse av en kilde —
    og en søyle farget rust fordi den er over en strek vi fant på, ville
    vært en vurdering forkledd som data.

    Alle søyler står derfor i `--hav5`, som er nettstedets egen farge.
    Se docs/APNE-SPORSMAL.md.
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
    plott_h = GRAF_HOYDE - o - u_ - GRAF_BRAKK_HOYDE
    bunn = o + plott_h

    # SØYLEBREDDEN ER PLASSEN PER UKE, uten mellomrom. 764 uker på 840
    # piksler er 1,1 px per uke, og et mellomrom der ville betydd at
    # halvparten av søylene forsvant. Tettheten ER formen: en serie på
    # femten år skal leses som en tidsakse, ikke som femten år med
    # tellbare pinner.
    steg = plott_b / n
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
    soyler = [{"x": x(i), "y": round(min(y(verdi), bunn - gulv), 1),
               "h": round(max(bunn - y(verdi), gulv), 1),
               "uke": f"{serie[i]['iso_aar']} uke {serie[i]['iso_uke']}",
               "verdi": visningsord.tall(verdi)}
              for i, verdi in enumerate(verdier) if verdi is not None]

    # Brakkleggingsstrekkene, slått sammen til sammenhengende bånd.
    baand, start = [], None
    for i, rad in enumerate(serie + [{}]):
        er_brakk = str(rad.get("brakklagt")) == "True"
        if er_brakk and start is None:
            start = i
        elif not er_brakk and start is not None:
            baand.append({"x": x(start),
                          "bredde": round(max(x(i) - x(start), 1.0), 1)})
            start = None

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
    aar = [{"x": x(i), "etikett": rad.get("iso_aar", "")}
           for i, rad in enumerate(serie)
           if i and rad.get("iso_aar") != serie[i - 1].get("iso_aar")]
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
        "soylebredde": bredde,
        "baand": baand,
        "linjer": linjer,
        "aar": aar,
        "tak": tak,
        # Formateres HER og ikke i malen. `1.54` med punktum er engelsk,
        # og `visningsord.tall()` er det ene stedet nettstedet bestemmer
        # hvordan et tall ser ut på norsk.
        "maks": visningsord.tall(maks),
        "uker": n,
        "uker_med_tall": n - uten_tall,
        "uten_tall": uten_tall,
        "brakklagt": brakk,
        "hull_forklart": brakk_uten_tall,
        "hull_uforklart": uten_tall - brakk_uten_tall,
        "nuller": sum(1 for v_ in verdier if v_ == 0),
        "fra": serie[0].get("dato", ""),
        "til": serie[-1].get("dato", ""),
    }


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
        "gjelder": e["gjelder"],
        "kilde": e["kilde"],
        "forste": False,
    } for e in endringer]

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
            "gjelder": "lokaliteten",
            "kilde": "",
            "forste": True,
        })
    return poster


def _oppgitt_historikk(a: dict, tillatelser: list[dict],
                       overforinger: list[dict]) -> list[dict]:
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
    klarert = (a.get("forste_klarering") or "")[:10]
    if klarert:
        poster.append({
            "dato": klarert, "slag": "Første klarering",
            "hva": "Lokaliteten klarert av Fiskeridirektoratet",
            "navn": "", "navn_felt": "",
            "kilde": "akvakultur", "felt": "forste_klarering",
            "presisjon": "dato oppgitt av registeret",
        })
    for till in tillatelser:
        if till["tildelt_dato"]:
            poster.append({
                "dato": till["tildelt_dato"],
                "slag": "Tillatelse tildelt",
                "hva": f"{till['nr']} tildelt",
                "navn": till["tildelt_navn"],
                "navn_felt": "tildelt_navn",
                "kilde": "eierskap", "felt": "tildelt_tid",
                "presisjon": "dato oppgitt av registeret",
            })
    for o in overforinger:
        if o["dato"]:
            poster.append({
                "dato": o["dato"],
                "slag": "Overføring journalført",
                "hva": f"{o['tillatelse']} overført",
                "navn": o["mottaker_navn"],
                "navn_felt": "mottaker_navn",
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
        serie = felles.lusserier.get(loknr, [])
        endringer, maaleserie_rader, sist_endret = _endringer_av_indeks(
            loknr, sorted(mine_till), felles)
        oppgitt = _liste(a.get("tillatelser"))
        uten_eier = _uten_eier(oppgitt, eierskap)

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
    tillatelsesrader = _tillatelsesrader(mine_till, uten_eier)
    dekning = felles.dekning_fra if felles else _dekning_fra()

    return {
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
        "register": [(f, visningsord.felt(f), visningsord.verdi(f, v),
                      sist_endret.get((loknr, f), ""))
                     for f, v in sorted(a.items())],
        # KJENTE og UGJORTE REDE FOR i SAMME tabell, i nummerrekkefølge.
        # Regelen og målingen står i docs/REGEL-UENIGE-KILDER.md: en
        # lokalitet der vi ikke vet hvem som eier tillatelsene skal si
        # det, ikke vise en tom tabell.
        "tillatelser": tillatelsesrader,
        "tillatelser_oppgitt": len(oppgitt),
        "tillatelser_uten_eier": len(uten_eier),
        # Teksten sendes INN og står ikke i malen: to steder som skal si
        # det samme om hva vi ikke vet, er formen F6 og F7 hadde.
        "eier_ukjent": EIER_UKJENT,
        "overforinger": overforingsrader,
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
        "posisjonskart": kart.posisjonskart(a.get("breddegrad"),
                                            a.get("lengdegrad")),

        # ---- de to historikkene ----
        "observert": _observert_historikk(endringer, dekning, felles),
        "oppgitt": _oppgitt_historikk(a, tillatelsesrader, overforingsrader),

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
        f"Bygget {bygget} av Kystloggen fra snapshots. Tallene er "
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
    miljo.filters["tidspunkt"] = visningsord.tidspunkt
    miljo.filters["tall"] = visningsord.tall
    # `feltmerke` er en GLOBAL og ikke et filter: den tar to argumenter
    # der rekkefølgen betyr noe, og `{{ "kommune"|feltmerke(r.kommune) }}`
    # leser baklengs. Se `feltmerke()`.
    # «1 tillatelser» sto på lokalitetssiden fra den ble bygget. Én
    # hjelper, brukt overalt — se visningsord.antall()/alle().
    miljo.globals["antall"] = visningsord.antall
    miljo.globals["alle"] = visningsord.alle
    miljo.globals["feltmerke"] = feltmerke
    miljo.globals["personformnavn"] = personformnavn
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
                f"akvakulturlokalitet {lok['loknr']} {lok['navn']} i "
                f"{lok['kommune']}, med endringslogg."),
            jsonld=jsonld(lok),
            proveniens_tekst=proveniens(
                lok["akva_dato"], lok["akva_hentet"],
                "Lusetallene er hentet fra BarentsWatch og gjelder uka "
                "de er datert til."),
            meny_aktiv="lokalitet",
            main_klasse="fullbredde",
            feed=f"/lokalitet/{loknr}/feed.xml",
            feed_tittel=f"Kystloggen: endringer for lokalitet {loknr}"),
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

# HEROFOTOGRAFIET, i tre bredder. Hostet av oss, aldri hentet fra
# Unsplash i runtime: en `images.unsplash.com`-URL i markupen ville
# fortalt dem hvem som leser siden, og en side som henter sitt eget
# hovedbilde fra en tredjepart er en side som ser feil ut den dagen den
# tjenesten gjør det.
#
# Ligger i `bilde/` og ikke i rota, fordi rota er for filer som må
# ligge der (`/stil.css`, fontene, faviconene, `robots.txt`). Se
# `docs/design/HEROFOTO.md` for proveniens, lisens og sha256.
# SKRIPTET. Én fil, lastet med `defer`, og den legger ikke til én
# verdi på noen side — se `maler/kystloggen.js`.
# `kystloggen.js` lastes av hver side; `sok.js` bare av `/sok/`. Se
# modulkommentaren i sok.js for hvorfor de er to filer og ikke én.
SKRIPTFILER = ("kystloggen.js", "sok.js")

BILDEMAPPE = "bilde"
BILDEFILER = ("hero-800.jpg", "hero-1600.jpg", "hero-2400.jpg")

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
    """Herofotografiet til `/bilde/`, og kartlisensen til rota."""
    (rot / BILDEMAPPE).mkdir(parents=True, exist_ok=True)
    skrevet = []
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
            f"# {uke['spenn']}",
            f"# {uke['antall']} hendelser, "
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
    skriver.writerow(["observert", "uke", "type", "kilde", "entity_id",
                      "entity_name", "felt", "fra", "til", "kommune",
                      "prodomraade_kode", "prodomraade_navn"])
    for h in uke["hendelser"]:
        # `entity_id` OG `entity_name` ER TOMME for en hendelse vi ikke
        # kan navngi. Kolonneoverskriften ER merkingen i en CSV
        # (`gransk_csv`), så en etikett som «Tillatelse N-R-0056» i
        # `entity_name`-kolonnen ville blitt lest som et navn — og det
        # er nøyaktig hva porten meldte. Se `_hendelse()`.
        skriver.writerow([h["dato"], uke["slug"], h["type"], h["kilde"],
                          h["identitet"],
                          h["gjelder"] if h["gjelder_felt"] == "entity_name"
                          else "", h["felt"],
                          h["fra"], h["til"], h["kommune"], h["po"],
                          h["po_navn"]])
    return buffer.getvalue()


def _ukens_json(uke: dict) -> str:
    """Ukas hendelser som JSON. Samme rader som CSV-en og tabellen."""
    return json.dumps({
        "uke": uke["slug"],
        "vist": uke["vist"],
        "spenn": uke["spenn"],
        "observasjonsdatoer": uke["datoer"],
        "antall": uke["antall"],
        "typer": {k["id"]: k["antall"] for k in uke["typer"]},
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


def skriv_endringssider(rot: Path, felles: Felles,
                        uker: list[dict]) -> list[Path]:
    """Indeksen, ukesidene, typesidene og datafilene."""
    miljo = _miljo()
    uke_mal = miljo.get_template("endringer-uke.html.j2")
    indeks_mal = miljo.get_template("endringer-indeks.html.j2")
    skrevet: list[Path] = []

    def skriv_html(sti: Path, html: str) -> None:
        sti.parent.mkdir(parents=True, exist_ok=True)
        sti.write_text(html, encoding="utf-8")
        skrevet.append(sti)

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
            if slag:
                ledet, egen = hendelser, []
            else:
                ledet = [h for h in hendelser if h["type"] not in EGEN_DEL]
                egen = [h for h in hendelser if h["type"] in EGEN_DEL]
            skriv_html(sti, uke_mal.render(
                u=uke, rader=ledet, egen=egen, valgt=valgt, url=url,
                nyere=nyere, eldre=eldre, uker_totalt=len(uker),
                siter={"url": _basisurl() + url,
                       "uke": uke["vist"], "aar": uke["aar"],
                       "spenn": uke["spenn"],
                       "sjekksum": felles.sjekksum},
                **_grunnkontekst(
                    felles, rot, sti, kilder=ENDRINGSKILDER,
                    tittel=f"{tittel} — Kystloggen",
                    beskrivelse=(
                        f"{len(hendelser)} endringer observert i "
                        f"{uke['vist']} ({uke['spenn']}) i norske "
                        f"akvakulturregistre."),
                    jsonld=_jsonld_uke(uke, hendelser, felles.vilkaar, url),
                    proveniens_tekst=proveniens(
                        uke["siste_dato"], felles.akva_hentet,
                        f"Sammenligning av øyeblikksbildene for "
                        f"{uke['vist']} og uka før."),
                    meny_aktiv="endringer",
                    main_klasse="fullbredde",
                    feed="/endringer/feed.xml",
                    feed_tittel="Kystloggen: alle endringer")))

        # DATAFILENE ligger i UKAS egen mappe, ved siden av siden —
        # samme regel som lusetall-CSV-en (url-struktur punkt 8).
        for navn, tekst in (("endringer.csv", _ukens_csv(uke)),
                            ("endringer.json", _ukens_json(uke))):
            fil = mappe / navn
            fil.parent.mkdir(parents=True, exist_ok=True)
            fil.write_text(tekst, encoding="utf-8")
            skrevet.append(fil)

    sti = rot / ENDRINGER_STI / "index.html"
    skriv_html(sti, indeks_mal.render(
        uker=uker,
        totalt=sum(u["antall"] for u in uker),
        typer=ENDRINGSTYPER,
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
            {"@type": "DataDownload", "encodingFormat": "text/csv",
             "contentUrl": "endringer.csv"},
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
    # tre indeksene, endringsindeksen og typesidene.
    andre = 1 + 1 + 1 + 3 + 1 + endringsuker * len(ENDRINGSTYPER)
    return {
        "lokaliteter": lokaliteter,
        "produksjonsomraader": omraader,
        "selskaper": selskaper,
        "endringsuker": endringsuker,
        "andre": andre,
        "sider": lokaliteter + omraader + selskaper + endringsuker + andre,
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
            meny_aktiv="sok", side_skript="/sok.js"))
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text(html, encoding="utf-8")
    return sti


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
        "# Cloudflares «Bot Preference Sync» er slått AV med vilje.",
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
    sti.write_text(html, encoding="utf-8")
    return sti


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
- [Alle selskaper]({u('/selskap/')}): selskapene som eier minst én
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

    kontakt = _kontakt()

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
    # DE TO SISTE KREVER INGENTING, og står her likevel. En side som
    # ikke sier hvor et bilde eller en kystlinje kommer fra, kan ingen
    # etterprøve — samme grunn som at datokolonnen i lisenskjeden
    # finnes. Se docs/LISENSKJEDE.md merknad G.
    {"hva": "Herofotografiet, av Wolfgang Hasselmann",
     "rolle": "forsidens hero",
     "lisens": "Unsplash-lisensen (navngiving er frivillig)",
     "opphav": "unsplash.com/photos/cbaS3DXXCl4",
     "sti": ""},
    {"hva": "Kystlinje, Natural Earth 1:10 millioner",
     "rolle": "kartene",
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
            meny_aktiv="om"),
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

    # LOKALITETER UTEN KOORDINATER. Lista lå på forsiden til 22.09.2026,
    # ved siden av punktkartet den forklarte. Kartet er byttet ut med
    # områdekartet, og regnskapet flyttet hit — der alle 1 782 uansett
    # står. Uenighetsregelen er den samme: et punkt som mangler skal
    # ikke bare forsvinne. Se docs/REGEL-UENIGE-KILDER.md.
    _punkter, uten, _hoyde, _gitter = kartpunkter(felles.akva)
    return {"rader": rader, "antall": len(rader),
            "akva_dato": felles.akva_dato,
            "uten_po": sum(1 for r in rader if not r["po_kode"]),
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
        d=data,
        **_grunnkontekst(
            felles, rot, rot / sti / "index.html", kilder=kilder,
            tittel=tittel, beskrivelse=beskrivelse,
            jsonld=_script_trygg({
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": tittel,
                "description": beskrivelse,
                "inLanguage": "nb",
            }),
            proveniens_tekst=proveniens(felles.akva_dato, felles.akva_hentet),
            meny_aktiv=sti),
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
            "Alle akvakulturlokaliteter — Kystloggen",
            "Flat liste over alle norske akvakulturlokaliteter med "
            "nummer, navn, kommune og produksjonsområde.",
            ("akvakultur",), felles),
        _skriv_indeks(
            rot, "produksjonsomrade", "indeks-produksjonsomrade.html.j2",
            bygg_poindeks(felles),
            "Alle produksjonsområder — Kystloggen",
            "De tretten produksjonsområdene med nyeste trafikklysfarge "
            "og antall lokaliteter.",
            ("akvakultur", "trafikklysvedtak"), felles),
        _skriv_indeks(
            rot, "selskap", "indeks-selskap.html.j2",
            bygg_selskapsindeks(felles),
            "Alle selskaper med akvakulturtillatelse — Kystloggen",
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


# HVOR MANGE RADER FORSIDENS ENDRINGSTABELL VISER. Overleveringen sier
# åtte, og deretter «Alle N endringer i uke W →». Tallet står her og
# ikke i malen: et tall i en mal er et tall ingen kan teste.
FORSIDERADER = 8


def _sammendrag(uke: dict | None) -> list[str]:
    """Én til tre setninger om uka, generert av tallene.

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
    if uke is None or not uke["antall"]:
        return ["Ingen endringer i registrene denne uka. Alle felt står "
                "som de sto forrige gang vi spurte."]

    # BARE SLAGENE SOM TELLER. «Felt oppgitt første gang» er ikke en
    # hendelse i havbruket, og en oppsummering som sa «fordelt på ni
    # slag» og listet det som nest størst, ville gjort rapportering om
    # til aktivitet.
    # BARE SLAGENE SOM TELLER OG SOM ER LEDET. Selskapsdata står for
    # seg — 402 av uke 39s 440 — og en oppsummering som ledet med dem
    # ville svart på «hvor mange felt endret seg i et register» framfor
    # på «hva skjedde i havbruket denne uka».
    med_tall = sorted((k for k in uke["typer"]
                       if k["antall"] and k.get("teller", True)
                       and k["id"] not in EGEN_DEL),
                      key=lambda k: -k["antall"])
    if not med_tall:
        return ["Ingen endringer i lokaliteter, tillatelser eller "
                "trafikklys denne uka. Alle felt står som de sto forrige "
                "gang vi spurte."]
    # TALLET SIER HVA DET TELLER. «38 endringer» alene lar leseren tro
    # det er alt som skjedde; setningen navngir slagene, og neste
    # setning sier hvor selskapsdataene ble av.
    setninger = [
        f"{visningsord.tall(uke['antall'])} endringer observert i "
        f"{uke['vist']}: {uke['ledet_slag']}."
    ]
    if uke["antall_egen_del"]:
        setninger.append(
            f"{visningsord.tall(uke['antall_egen_del'])} endringer i "
            f"selskapsdata — ansatte, næringskode, adresse, regnskap — "
            f"står for seg på ukessiden.")

    storst = med_tall[0]
    if storst["id"] == "trafikklys":
        setninger.append(
            f"Akvakulturregisteret oppgir ny trafikklysfarge for "
            f"{visningsord.tall(storst['antall'])} "
            f"{'produksjonsområde' if storst['antall'] == 1 else 'produksjonsområder'}"
            f" — forskriften dateres til vedtaksåret, og dette er uka "
            f"registeret fulgte den opp.")
    else:
        setninger.append(
            f"Størst er {storst['navn'].lower()} med "
            f"{visningsord.tall(storst['antall'])}: {storst['hva']}.")

    if len(med_tall) > 1:
        nest = med_tall[1]
        setninger.append(
            f"Deretter {nest['navn'].lower()} med "
            f"{visningsord.tall(nest['antall'])}.")
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
        "sammendrag": _sammendrag(uke),
        "forskriftslinje": _forskriftslinje(felles, uke),
        # FORSIDENS KORTE TABELL viser bare det som er LEDET. De 402
        # selskapsdataradene står på ukessiden, i sin egen del.
        "rader": (uke["ledet"][:FORSIDERADER] if uke else []),
        "flere_rader": (max(len(uke["ledet"]) - FORSIDERADER, 0)
                        if uke else 0),
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
    }


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
            main_klasse="fullbredde"),
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
    register = [(f, visningsord.felt(f), visningsord.verdi(f, reg[f]),
                 felles.sist_endret.get((orgnr, f), ""))
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
            ut_av.append({
                "dato": neste.get("journal_dato", ""),
                "tillatelse": nr,
                "navn": neste.get("mottaker_navn", ""),
                "navn_felt": "mottaker_navn",
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
    samlet = _samlet_kapasitet(mine)

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
                        for r in _tillatelsesrader(mine, [])],
        "tillatelser_antall": len(tillatelser),
        "lokaliteter": lokalitetsrader,
        "lokaliteter_antall": len(lokaliteter),
        "overforinger": overforinger,

        # ---- nøkkeltallene i overskriften ----
        "samlet_kapasitet": samlet["vist"],
        "kapasitetsenheter": samlet["enheter"],
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
    return {"vist": " + ".join(biter), "enheter": len(per_enhet)}


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
    mal = mal or _miljo().get_template("selskap.html.j2")
    html = mal.render(
        sel=sel,
        **_grunnkontekst(
            felles, rot, rot / "selskap" / orgnr / "index.html",
            kilder=SELSKAPSKILDER,
            tittel=f"{sel['navn'] or sel['orgnr']} — Kystloggen",
            beskrivelse=(
                f"Akvakulturtillatelser, lokaliteter og overføringer for "
                f"organisasjonsnummer {sel['orgnr']}"
                f"{' (' + sel['navn'] + ')' if sel['navn'] else ''}."),
            jsonld=jsonld_selskap(sel, felles.vilkaar),
            proveniens_tekst=proveniens(
                felles.eierskap_dato, _hentet("eierskap"),
                "Registerdataene om selskapet er fra "
                "Enhetsregisteret."),
            meny_aktiv="selskap",
            main_klasse="fullbredde",
            feed=f"/selskap/{orgnr}/feed.xml",
            feed_tittel=f"Kystloggen: endringer for {sel['navn'] or orgnr}"),
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
            main_klasse="fullbredde",
            feed=f"/produksjonsomrade/{po}/feed.xml",
            feed_tittel=f"Kystloggen: endringer i produksjonsområde {po}"),
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
    endringssider: int = 0
    endringsuker: int = 0
    feeder: int = 0
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
                 + [skriv_stil(rot)] + skriv_fonter(rot)
                 + skriv_ikoner(rot))
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
