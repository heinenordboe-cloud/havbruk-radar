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
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import publiseringsvakt                                    # noqa: E402
from core import changelog, diff, snapshot                 # noqa: E402
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
# Ordrett fra lisensgiverne, kopiert fra docs/LISENSKJEDE.md og ikke
# gjengitt fra hukommelsen. Tabellen er den som avgjør hva som havner i
# bunnteksten, og den er indeksert på KILDENAVN — det samme navnet som
# `data/raw/<kilde>/` og changeloggens `source`-kolonne.
#
# En kilde som ikke står her kan ikke publiseres. Det er
# `docs/beslutninger/2026-09-12-lisenskjeden.md` sin regel utført i kode:
# **udokumentert lisens er UBELAGT, ikke antatt greit.** `ekspertgruppen`
# er UBELAGT og står derfor med en tom liste — bruker en side den,
# kaster byggingen i stedet for å publisere noe vi ikke har hjemmel for.
#
# Hvorfor tabellen ligger HER og ikke på `Source` i core/contract.py:
# det ville vært en utvidelse av kontrakten, og CLAUDE.md regel 1 sier at
# en slik utvidelse er brukerens avgjørelse og ikke en sidevirkning av en
# oppgave. Se «Kjente svakheter» nederst.
KILDEVILKAAR: dict[str, list[str]] = {
    "akvakultur": ["Kilde: Fiskeridirektoratet"],
    "biomasse": ["Kilde: Fiskeridirektoratet"],
    "biomasselag": ["Kilde: Fiskeridirektoratet"],
    "romming": ["Kilde: Fiskeridirektoratet"],
    "eierskap": [
        "Kilde: Fiskeridirektoratet",
        "Inneholder data under Norsk lisens for offentlige data (NLOD) "
        "tilgjengeliggjort av Brønnøysundregistrene",
    ],
    "eierskap_historikk": [
        "Kilde: Fiskeridirektoratet",
        "Inneholder data under Norsk lisens for offentlige data (NLOD) "
        "tilgjengeliggjort av Brønnøysundregistrene",
    ],
    "enhetsregisteret": [
        "Inneholder data under Norsk lisens for offentlige data (NLOD) "
        "tilgjengeliggjort av Brønnøysundregistrene",
    ],
    # Begge setningene, og den andre er ikke valgfri: den er
    # dataeierattribusjonen, og den trengs nettopp FORDI vi henter fra
    # BarentsWatch og ikke fra Mattilsynet.
    "lusetall": [
        "Data levert av BarentsWatch",
        "Opplysninger om lakselus, rensefisk og medikamentbruk er hentet "
        "fra Mattilsynet.",
    ],
    "sjotemperatur": ["Data levert av BarentsWatch"],
    "trafikklysvedtak": [
        "Kilde: Lovdata. Inneholder data under Norsk lisens for "
        "offentlige data (NLOD) 2.0",
    ],
    "reguleringsomraader": [
        "Havforskningsinstituttet, «Smittekontakt (lakselus) mellom "
        "oppdrettsanlegg og oppholdsområder for villfisk», CC BY 4.0",
    ],
    # UBELAGT per 14.09.2026 — søkt etter og ikke funnet. Tom liste er
    # ikke «ingen krav»; det er «vi vet ikke», og da publiseres den ikke.
    "ekspertgruppen": [],
}

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


def attribusjon(kilder) -> list[str]:
    """Setningene som må stå synlig, for de kildene siden faktisk bruker.

    Deduplisert med rekkefølgen intakt: `eierskap` og
    `eierskap_historikk` krever de samme to setningene, og den som leser
    bunnteksten skal ikke lure på hvorfor det står to like.

    Kaster på UBELAGT. Se `KILDEVILKAAR`.
    """
    ut: list[str] = []
    for kilde in kilder:
        if kilde not in KILDEVILKAAR:
            raise UbelagtKilde(
                f"{kilde} står ikke i KILDEVILKAAR. Udokumentert lisens er "
                f"UBELAGT, ikke antatt greit — se docs/LISENSKJEDE.md.")
        if not KILDEVILKAAR[kilde]:
            raise UbelagtKilde(
                f"{kilde} er UBELAGT i docs/LISENSKJEDE.md: vilkåret er "
                f"lett etter og ikke funnet. Siden bygges ikke. Lukk luken "
                f"med et spørsmål til utgiveren, ikke med mer kode.")
        for setning in KILDEVILKAAR[kilde]:
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


def _uke(dato: str) -> str:
    """«2026 uke 34» av en dato. Lusetall daterer hver uke til MANDAGEN i
    ISO-uka (docs/KILDE-LUSETALL.md), så ukenummeret er en annen skriving
    av den samme datoen og ikke et nytt tall."""
    aar, uke, _ = dt.date.fromisoformat(dato).isocalendar()
    return f"{aar} uke {uke:02d}"


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

    Hver uke får ALLE feltene i `LUSEFELT`, med `INGEN_VERDI` der kilden
    tidde. Utfyllingen skjer her og ikke i malen: `StrictUndefined` gjør
    en manglende nøkkel til en feil i stedet for en tom celle, og det er
    riktig — men da må den som leser dataene bestemme hva fraværet BETYR,
    og det kan ikke en HTML-mal.
    """
    rader = []
    for dato in snapshot.datoer("lusetall"):
        for _nr, ramme in snapshot.versjoner("lusetall", dato):
            sub = ramme.filter(pl.col("entity_id") == loknr)
            if sub.is_empty():
                continue
            raa = {str(f): v for f, v in
                   sub.select(["field", "value"]).iter_rows()}
            uke = {}
            for felt in LUSEFELT:
                verdi = raa.get(felt)
                uke[felt] = (INGEN_VERDI if verdi in (None, "")
                             else JANEI.get(verdi, verdi))
            uke["dato"] = dato
            uke["uke"] = _uke(dato)
            rader.append(uke)
    return rader


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


def _endringer(loknr: str, tillatelser: list[str]) -> tuple[list[dict], int]:
    """(registerendringer nyest først, antall måleserierader).

    Tar med endringer som gjelder lokaliteten SELV og endringer som
    gjelder en TILLATELSE på den. Det andre er en indirekte kobling, og
    den er med fordi et eierskifte er noe av det viktigste som kan skje
    med en lokalitet — men raden gjelder tillatelsen, og det står i
    kolonnen «Gjelder» framfor å pusses bort.

    `diff.bevegelse()` er allerede kjørt: `utvalgsutvidelse` og
    `revidert` er ikke bevegelse. Se docs/ARKITEKTUR.md.
    """
    alle = changelog.merk_utvalgsutvidelse(changelog.les_alt())
    beveg = diff.bevegelse(alle)

    mine = beveg.filter(
        (pl.col("entity_id") == loknr)
        | ((pl.col("source").is_in(["eierskap", "eierskap_historikk"]))
           & pl.col("entity_id").is_in(tillatelser))
    )

    maaleserie = mine.filter(pl.col("source").is_in(sorted(MAALESERIER))).height

    register = mine.filter(~pl.col("source").is_in(sorted(MAALESERIER)))
    rader = []
    for r in register.sort("observed_at", descending=True).iter_rows(named=True):
        rader.append({
            "dato": str(r["observed_at"]),
            "gjelder": ("lokaliteten" if str(r["entity_id"]) == loknr
                        else f"tillatelse {r['entity_id']}"),
            "kilde": str(r["source"]),
            "felt": str(r["field"]),
            "fra": r["old_value"] if r["old_value"] is not None else "",
            "til": r["new_value"] if r["new_value"] is not None else "",
        })
    return rader, maaleserie


# --------------------------------------------------------- sida


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


def bygg_lokalitet(loknr: str) -> dict:
    """Alle dataene én lokalitetsside trenger. Ingen HTML her."""
    akva_dato, akva = _siste("akvakultur")
    if loknr not in akva:
        raise SystemExit(f"lokalitet {loknr} finnes ikke i "
                         f"akvakultur-snapshotet {akva_dato}")
    a = akva[loknr]

    eierskap_dato, eierskap = _siste("eierskap")
    mine_till = {
        nr: d for nr, d in eierskap.items()
        if loknr in [x.strip() for x in (d.get("lokaliteter") or "").split(";")]
    }

    ovf = _overforinger()
    overforinger = sorted(
        (o for o in ovf.values() if o.get("tillatelse_nr") in mine_till),
        key=lambda o: (o.get("journal_dato", ""), o.get("tillatelse_nr", "")),
    )

    serie = _lusserie(loknr)
    endringer, maaleserie_rader = _endringer(loknr, sorted(mine_till))

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
        "lus": list(reversed(serie[-LUSEUKER:])),
        "lus_fra": serie[0]["dato"] if serie else "",
        "lus_til": serie[-1]["dato"] if serie else "",
        "lus_uker": len(serie),
        # Telles her og skrives ikke inn i malen for hånd. Et tall i en
        # mal er et tall som ikke oppdateres når dataene gjør det, og da
        # er siden usann neste uke uten at noen rørte den.
        "lus_uten_tall": sum(1 for u in serie
                             if u["voksne_hunnlus"] == INGEN_VERDI),
        "endringer": endringer,
        "maaleserie_rader": maaleserie_rader,
        "dekning_fra": _dekning_fra(),
    }


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
    kilder = []
    for kilde in SIDENS_KILDER:
        node = {
            "@type": "Dataset",
            "name": kilde,
            "creditText": KILDEVILKAAR[kilde][0],
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
    if lok["lus"]:
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


def skriv_lokalitet(loknr: str, rot: Path = UT) -> Path:
    """Rendrer og skriver én lokalitetsside. Returnerer stien."""
    lok = bygg_lokalitet(loknr)
    setninger = attribusjon(SIDENS_KILDER)          # kaster på UBELAGT

    html = _miljo().get_template("lokalitet.html.j2").render(
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
    return sti


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lokalitet", default="31397",
                    help="lokalitetsnummer å bygge (standard: 31397)")
    ap.add_argument("--ut", default=str(UT), help="målmappe")
    ap.add_argument("--uten-vakt", action="store_true",
                    help="hopp over publiseringsvakten (bare utvikling)")
    args = ap.parse_args()

    rot = Path(args.ut)
    sti = skriv_lokalitet(args.lokalitet, rot)
    kb = sti.stat().st_size / 1024
    print(f"{sti}  ({kb:.0f} kB)")
    print(f"  URL: /lokalitet/{args.lokalitet}/")

    if args.uten_vakt:
        print("\nVAKTEN ER HOPPET OVER. Siden skal ikke publiseres.")
        return 0
    return gransk_og_meld(rot)


if __name__ == "__main__":
    raise SystemExit(main())
