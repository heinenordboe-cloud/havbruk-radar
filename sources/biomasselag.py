"""Biomasselaget (Fiskeridirektoratet) — står det fisk på lokaliteten.

Endepunkt: gis.fiskeridir.no/server/rest/services/Yggdrasil/Biomasse/
           MapServer/0/query

Verifisert mot levende tjeneste 10.09.2026. Ingen nøkkel, ingen
registrering, ingen autentisering. `copyrightText` på tjenesten er
«Fiskeridirektoratet» — NLOD, og attribusjonen er et vilkår. Samme
tjenestekatalog og samme vilkår som `romming`.

Tjenestens egen beskrivelse, ordrett:

    «Viser status (om det stod fisk og hvilken art) på lokalitet ved
     siste innsendte månedsrapport fra oppdretter. Ved lokaliteter der
     det står flere arter blir det symbolisert etter den arten som har
     mest biomasse [kg].»

## Hvorfor kilden finnes: ja/nei er alt vi får, og ja/nei er nok

Selve biomassedatabasen etter akvakulturdriftsforskriften § 44 — antall
fisk per anlegg per måned — er børssensitiv og ikke offentlig. Bekreftet
av Havforskningsinstituttet 09.09.2026. Antallet får vi aldri.

Dette laget gir det som IKKE er stengt: om det stod fisk, og hvilken
art. Det er HIs eget kriterium for «aktivt anlegg», og det er den
uavhengige kontrollen `lusetall.brakklagt` aldri kunne være alene.

## NÅTILSTAND UTEN HISTORIKK — derfor haster den

Laget bærer ÉN tilstand: den siste innsendte rapporten per lokalitet.
Det finnes ingen tidsserie å hente, ingen `?dato=`-parameter og ingen
arkivkopi hos Fiskeridirektoratet. Forrige ukes tilstand finnes ikke
noe sted etter at den er overskrevet.

Verdien av kilden er derfor null i dag og vokser med kalendertid alene.
Det er samme begrunnelse hele repoet hviler på (CLAUDE.md regel 5), men
her er den ikke et argument om prioritering — den er hele kilden. En uke
som ikke arkiveres er borte, og ingen mengde bygging senere henter den
tilbake. Se docs/beslutninger/2026-09-10-biomasselag.md.

## observed_at ER HENTETIDSPUNKTET, og det er MÅLT, ikke antatt

`siste_rapport` finnes som datofelt, og det var det første jeg lette
etter. Det duger ikke som `observed_at`, og grunnen er verdt å skrive
ned fordi den ser ut som det motsatte ved første øyekast.

Feltet er PER RAD, ikke per lag. Målt 10.09.2026 over alle 1127 rader:
112 distinkte verdier, fra **2005-04-30 til 2026-08-31**. Det sier når
DEN lokaliteten sist sendte månedsrapport — ikke hvilken måned laget som
helhet gjelder for.

To ting følger, og bare det andre er åpenbart:

1. Det finnes ingen felles dato å sette. Feltet brukt som `observed_at`
   ville gitt 112 snapshots per henting, og brutt `run.py`s invariant om
   ett snapshot per kilde per kjøring.
2. Verre: det ville vært en oppdiktet proveniens. Raden med
   `siste_rapport = 2010-01-31` er ikke en observasjon vi gjorde i 2010.
   Den er en påstand laget gjør I DAG om at siste rapport kom i 2010.
   `observed_at = 2010-01-31` ville sagt at vi så dette i 2010, og det
   gjorde vi ikke. Det er nøyaktig feilen 1b-7 beskriver, bare med
   `observed_at` i stedet for `published_at`.

`observed_at` er derfor kjøredatoen: dette er hva laget SA den dagen vi
spurte. `siste_rapport` bæres som felt på hver rad, og `dato_forbehold`
sier rett ut at datoen er hentetidspunkt og ikke rapporteringstidspunkt
(CLAUDE.md 1b-3). Alderen på hver enkelt påstand blir da et regnestykke
en leser kan gjøre av raden alene — `observed_at` minus
`siste_rapport` — i stedet for noe som er skjult.

## «Ja» ER nåtid. «Nei» ER IKKE. Målt 10.09.2026

Alderen `2026-09-10 − siste_rapport`, i måneder, over de 1117:

                  n   median   >3 mnd   >12 mnd   >60 mnd   maks
    alle       1117      2.0    34,6 %    17,8 %     7,2 %    257
    har_fisk=Ja 630      2.0     1,1 %     0,0 %     0,0 %     10
    har_fisk=Nei 487     9.0    78,0 %    40,9 %    16,4 %    257

De to halvdelene av laget er ikke samme slags påstand:

  - **`har_fisk = "Ja"`** er fersk. 623 av 630 er rapportert innen tre
    måneder, ingen er eldre enn ti. Det er en påstand om nåtid.
  - **`har_fisk = "Nei"`** er en ABSORBERENDE tilstand. Fire av ti er
    over et år gamle, én av seks over fem år, og den eldste er fra
    2005-04-30. Meldeplikten i § 44 følger fisken: en lokalitet som
    tømmes slutter å rapportere, og raden fryser på den siste
    meldingen om at det var tomt.

`har_fisk = "Nei"` betyr derfor ikke «tom nå». Den betyr «ikke meldt
fisk siden `siste_rapport`». Enhver bruk som teller tomme lokaliteter må
lese `siste_rapport` ved siden av, og det er derfor feltet ligger på
raden og ikke bare i denne docstringen.

## published_at settes IKKE

Verten sender ingen `Last-Modified`. Målt 10.09.2026:

    server: Microsoft-IIS/10.0
    cache-control: must-revalidate,max-age=0,public
    etag: "c5b049c3"

`etag` er ikke et tidspunkt. Etter 1b-7 er standarden «vet ikke», aldri
hentetidspunktet, så feltet står tomt. Headeren LESES likevel i tilfelle
tjenesten begynner å sende den — den utledes bare ikke.

## Én rad per (lokalitet, ART), ikke per lokalitet

1127 rader, 1117 distinkte `loknr`. Ti lokaliteter har to arter og
dermed to rader. Kontrollert felt for felt 10.09.2026: de doble radene
er IDENTISKE i alt unntatt `art`, `symbol1` og `objectid`. Artsparene er
9 × (Laks, Regnbueørret) og 1 × (Kveite, Torsk).

Det er ikke en detalj. `snapshot.NOKKEL` er `(entity_id, field, source)`,
så med `loknr` som entitet og `art` som felt ville den ene arten falt
stille bort i `unique(keep="first")` — en tapt observasjon uten
feilmelding, som er formen på F14. Artene samles derfor til ETT felt,
`arter_tilstede`, sortert og skilt med «;». Separatoren er VÅR;
verdiene er kildens, ordrett.

## Artsverdiene bæres ORDRETT

Målt 10.09.2026, alle verdier som forekommer:

    har_fisk = "Ja"  / art = "Laks"            548
    har_fisk = "Nei" / art = null              487
    har_fisk = "Ja"  / art = "Regnbueørret"     54
    har_fisk = "Ja"  / art = "Torsk"            20
    har_fisk = "Ja"  / art = "Kveite"           17
    har_fisk = "Ja"  / art = "Røye"              1

`har_fisk = "Nei"` medfører `art = null`, uten unntak i utvalget.

Ingen av disse gjøres om til egne kategorier, og «Ja»/«Nei» blir ikke
til bool. Hva Fiskeridirektoratet KALLER en art kan endre seg, og den
endringen er noe vi vil se i changeloggen — ikke noe en oversettelse
skal spise. `VENTEDE_*` under er skrevne kvitteringer på hva som fantes
den dagen, og de brukes til å VARSLE om noe nytt, aldri til å filtrere.

## `art` her er ikke `arter` i akvakultur

Akvakulturregisteret har allerede et felt som heter `arter`. Det er
artene lokaliteten har TILLATELSE for. Dette laget sier hva som faktisk
STOD DER ved siste rapport. Samme ord, to helt ulike påstander, og
feltet heter derfor `arter_tilstede` her.

## Hva som IKKE hentes, og hvorfor

Laget har `fylke`, `kommune`, `kapasitet_lok`, `aktuell_kapasitet`,
`plassering`, `vannmiljo`, `produksjonsomraade` og `navn`. Alle sammen
finnes fra før i `akvakultur`, som `fylke`, `kommune`, `kapasitet`,
`plasseringstype`, `vanntype`, `prodomraade_navn` og `navn`. De hentes
ikke hit, av samme grunn som `romming` lar være å hente `lat`/`lon`: to
kilder til samme opplysning er to tellere for samme sak, og den ene
teller feil i changeloggen den uka de spriker.

Her er grunnen sterkere enn som så, og den er MÅLT. **Hele raden er
fryst ved siste rapport, ikke bare fiskestatusen.** Fylkesnavnet
«TROMS OG FINNMARK» — et fylke som opphørte 01.01.2024 — står på 18
rader 10.09.2026. Alle 18 har `har_fisk = "Nei"`, og alle har
`siste_rapport` i 2023 eller tidligere. «VIKEN», som opphørte samme dag,
står på én. De 193 radene med «TROMS» eller «FINNMARK» har rapporter
helt fram til 2026.

Hentet vi `fylke` herfra, ville vi altså skrevet ned et fylke som ikke
finnes, for lokaliteter `akvakultur` har det riktige fylket for. Det er
ikke duplisering — det er en dårligere kopi.

`symbol1` er symbolisering, ikke data — den er en kopi av `art` med
`"ingen biomasse"` der `art` er null og `"Andre"` for Røye. `shape` er
geometri vi ikke bruker.

## PERSONVERN: laget har ingen persondata, og filteret er en LÅS

Feltlista er lest fra tjenestens egen metadata, ikke fra dokumentasjon:
det finnes ingen innehaver, ingen adresse og ingen fritekst her. Det er
den motsatte situasjonen av `romming`.

Filteret finnes likevel, og det virker motsatt vei av rømmingens: vi ber
om en EKSPLISITT feltliste (`FELTER`) i stedet for `outFields=*`. Grunnen
er at rå-arkivet ligger i git og er append-only. Et felt Fiskeridirektoratet
legger til i morgen — et innehavernavn, en kontaktperson — ville med `*`
havnet i arkivet før noe menneske hadde sett det, og der kan det ikke
fjernes igjen.

Prisen for låsen er at et NYTT og nyttig felt blir usynlig. Den prisen
betales ikke: `fetch()` leser lagets feltliste ved hver henting og
ADVARER om felter tjenesten har som vi ikke ber om. Da ser vi endringen
uten å arkivere den, og utvidelsen blir et valg noen tar med åpne øyne.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

STANDARD_BASE = ("https://gis.fiskeridir.no/server/rest/services/"
                 "Yggdrasil/Biomasse/MapServer/0")

# Tjenestens `maxRecordCount` er 2000, og laget hadde 1127 rader
# 10.09.2026 — ett kall holdt, `exceededTransferLimit` var ikke satt.
# Vi pagineres likevel: taket er tjenestens, ikke vårt, og en kilde som
# stille mister rad 2001 den dagen næringa vokser er ikke verdt
# innsparingen på ett HTTP-kall i uka.
SPENN = 1000
MAKS_SIDER = 50

# Feltene som HENTES. Alt annet forlater aldri tjenesten — se modulens
# docstring om hvorfor lista er en lås og ikke en bekvemmelighet.
#
# `symbol1`, `shape` og de sju feltene `akvakultur` allerede har står
# bevisst ikke her.
FELTER = ("objectid", "loknr", "navn", "status_lokalitet",
          "siste_rapport", "har_fisk", "art")

# Felter tjenesten HADDE 10.09.2026 og som vi bevisst ikke ber om.
# Skrevet ned framfor bare utelatt, slik at feltvakten under kan skille
# «kjent, valgt bort» fra «nytt siden sist».
KJENTE_UTELATTE = ("symbol1", "kapasitet_lok", "aktuell_kapasitet",
                   "plassering", "vannmiljo", "fylke", "kommune",
                   "produksjonsomraade", "shape")

# Verdiene som fantes 10.09.2026. En SKREVET kvittering, ikke en
# referanse utledet av forrige kjøring (CLAUDE.md 1b-4). Brukes bare til
# å varsle om noe nytt — aldri til å filtrere, og aldri til å oversette.
VENTEDE_HAR_FISK = frozenset({"Ja", "Nei"})
VENTEDE_ARTER = frozenset({"Laks", "Regnbueørret", "Torsk", "Kveite", "Røye"})

# Vår separator mellom artsnavn. Verdiene på hver side er kildens.
# Ingen artsnavn i VENTEDE_ARTER inneholder tegnet, så sammenslåingen
# lar seg reversere av en leser: `value.split(";")`.
ARTSSKILLE = ";"

# Forbeholdet om DATOEN. Bæres på hver rad, som `dato_forbehold` i
# eierskapshistorikken og `gjenfangst_forbehold` i rømming
# (CLAUDE.md 1b-3). Uten det kan et snapshot ikke alene svare på hva
# `observed_at` betyr her.
DATO_FORBEHOLD = (
    "observed_at er HENTETIDSPUNKTET vårt, ikke rapporteringstidspunktet. "
    "Laget bærer siste innsendte månedsrapport PER LOKALITET, og "
    "siste_rapport på denne raden sier hvilken måned nettopp denne "
    "påstanden gjelder for. De to kan ligge år fra hverandre: målt "
    "10.09.2026 spente siste_rapport fra 2005-04-30 til 2026-08-31 over "
    "112 distinkte verdier. Alderen på påstanden er observed_at minus "
    "siste_rapport, og den må regnes ut per rad."
)

# Forbeholdet om ARTEN og om hva laget IKKE sier.
ARTS_FORBEHOLD = (
    "arter_tilstede er artene oppdretter meldte som tilstede ved siste "
    "månedsrapport, ordrett fra kilden og skilt med «;» av oss — "
    "antall_arter sier hvor mange. Laget oppgir INGEN mengde: verken "
    "antall fisk eller kilo biomasse. "
    "Biomassedatabasen etter akvakulturdriftsforskriften § 44 er "
    "borssensitiv og ikke offentlig (bekreftet av HI 09.09.2026), så "
    "dette er ja/nei og art, aldri hvor mye. Feltet er heller ikke det "
    "samme som akvakultur.arter, som er artene lokaliteten har "
    "TILLATELSE for."
)


def _dato(ms: object) -> str:
    """Epoch-millisekunder -> ISO-dato. Tom streng for manglende.

    UTC, eksplisitt, av samme grunn som i `romming`: kilden oppgir ingen
    tidssone, og en naiv `utcfromtimestamp` ville vært et tidspunkt uten
    sone i en kjede der alt annet er sonebevisst.
    """
    if ms in (None, ""):
        return ""
    return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc).date().isoformat()


def _tekst(v: object) -> str:
    """Kildeverdi -> streng, ORDRETT. `None` blir tom streng."""
    return "" if v is None else str(v).strip()


def _ukjente_felter(felter: object) -> list[str]:
    """Felter tjenesten har som vi verken henter eller har valgt bort.

    Låsen i `FELTER` gjør at et nytt felt aldri havner i arkivet. Denne
    gjør at det heller ikke blir usynlig.
    """
    kjent = set(FELTER) | set(KJENTE_UTELATTE)
    if not isinstance(felter, list):
        return []
    navn = {f.get("name") for f in felter if isinstance(f, dict)}
    return sorted(n for n in navn - kjent if n)


def _vurder(rader: list[dict], ukjente: list[str]) -> list[str]:
    """Advarsler kilden vil si fra om uten å felle seg selv.

    Ingen av disse kaster. En ny artsverdi eller et nytt felt er
    nettopp det vi vil SE, og en kilde som feller seg selv på det
    taper uka den skulle ha fanget endringen i.
    """
    ut: list[str] = []

    if ukjente:
        ut.append(f"biomasselag: tjenesten har {len(ukjente)} felt(er) vi "
                  f"ikke henter og ikke har valgt bort: {', '.join(ukjente)}. "
                  f"Sjekk om de bærer persondata FØR du utvider FELTER — "
                  f"arkivet er append-only.")

    nye_status = sorted({_tekst(r.get("har_fisk")) for r in rader}
                        - VENTEDE_HAR_FISK - {""})
    if nye_status:
        ut.append(f"biomasselag: har_fisk har nye verdier {nye_status}. "
                  f"Verdiene lagres ordrett som alltid — dette er et "
                  f"varsel om at ordforrådet er endret, ikke en feil.")

    nye_arter = sorted({_tekst(r.get("art")) for r in rader}
                       - VENTEDE_ARTER - {""})
    if nye_arter:
        ut.append(f"biomasselag: art har nye verdier {nye_arter}. "
                  f"Lagres ordrett. Kvitter i VENTEDE_ARTER når du har "
                  f"sett på dem.")

    # Målt 10.09.2026: `har_fisk = "Nei"` medfører `art = null` uten
    # unntak. Bryter det sammen, betyr feltene ikke lenger det vi tror.
    sprik = [r for r in rader
             if _tekst(r.get("har_fisk")) == "Nei" and _tekst(r.get("art"))]
    if sprik:
        ut.append(f"biomasselag: {len(sprik)} rad(er) har har_fisk=Nei OG "
                  f"en art. Det forekom ikke 10.09.2026, og de to feltene "
                  f"betyr da ikke lenger det docstringen sier.")

    tomme = [r for r in rader if not _tekst(r.get("har_fisk"))]
    if tomme:
        ut.append(f"biomasselag: {len(tomme)} rad(er) mangler har_fisk. "
                  f"Det er selve spørsmålet kilden finnes for.")

    return ut


class Biomasselag(Source):
    """Står det fisk på lokaliteten, og hvilken art.

    Kjøres av `run.py` sammen med `akvakultur`. Kilden er NÅTILSTAND —
    det er hele grunnen til at den finnes, og det er derfor den ikke har
    en backfill-modus å tilby.
    """

    name = "biomasselag"
    entity_type = "lokalitet"
    version = "1"

    # Ukentlig, som akvakultur. Laget oppdateres når oppdretterne sender
    # månedsrapport, så en uke uten endring er vanlig — men uka som IKKE
    # hentes er borte, og det er asymmetrien som setter kadensen.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.biomasselag.aktiv", False))

    # ---- henting -------------------------------------------------------

    def fetch(self, kjoredato: str) -> list[dict]:
        """Alle rader i laget, med bare feltene i `FELTER`.

        `kjoredato` brukes ikke til å velge tidsrom — laget har bare ett,
        og det er nå. Argumentet står fordi kontrakten krever at en kilde
        FÅR tiden inn i stedet for å slå den opp (CLAUDE.md 1b).

        Returnerer den filtrerte lista og ikke et råsvar med alle felter.
        Filtreringen skjer i selve forespørselen (`outFields`), så det
        tjenesten sender ER det vi arkiverer — se docstringen om hvorfor
        `outFields=*` ikke er et alternativ når arkivet er append-only.

        `utvalg` er ikke `{}`: vi ber om alle RADER (`where=1=1`), men om
        et utvalg FELTER. Et snapshot skal alene kunne svare på hva vi
        ba om (1b-3), og «vi utelot ni felter» er en del av det svaret.
        """
        self.utvalg = {"utelatte_felter": sorted(KJENTE_UTELATTE)}

        base = get("kilder.biomasselag.base_url", STANDARD_BASE).rstrip("/")
        c = httpx.Client(timeout=120.0, follow_redirects=True)
        rader: list[dict] = []
        ukjente: list[str] = []
        try:
            # Feltlista FØRST: den er billig, og den er det eneste som
            # ser et nytt felt vi ikke ber om.
            meta = _http.get(c, base, hva="biomasselag metadata",
                             params={"f": "json"}).json()
            if "error" in meta:
                raise RuntimeError(f"biomasselag metadata: {meta['error']}")
            ukjente = _ukjente_felter(meta.get("fields"))

            for i in range(MAKS_SIDER):
                svar = _http.get(
                    c, f"{base}/query", hva=f"biomasselag side {i}",
                    params={"where": "1=1", "outFields": ",".join(FELTER),
                            "returnGeometry": "false", "f": "json",
                            "orderByFields": "objectid",
                            "resultOffset": i * SPENN,
                            "resultRecordCount": SPENN})
                d = svar.json()
                if "error" in d:
                    raise RuntimeError(f"biomasselag: {d['error']}")
                trekk = d.get("features") or []
                rader += [_rens(x.get("attributes") or {}) for x in trekk]
                if len(trekk) < SPENN:
                    break
            else:
                raise RuntimeError(
                    f"biomasselag: over {MAKS_SIDER} sider. Pagineringen "
                    f"teller ikke ned — er tjenesten endret?")

            # LESES, utledes ikke (1b-7). Verten sendte ingen
            # `Last-Modified` 10.09.2026, og da blir dette tom streng —
            # «vet ikke», ikke hentetidspunktet.
            self.published_at = _utgitt(svar.headers)
        finally:
            c.close()

        if not rader:
            raise RuntimeError(
                "biomasselag: null rader. Laget hadde 1127 rader "
                "10.09.2026, og et tomt svar er ikke en tom uke — det er "
                "en tjeneste som har endret seg.")

        self.advarsler = _vurder(rader, ukjente)
        return rader

    def gjelder_for(self, kjoredato: str) -> str:
        """Kjøredatoen. Laget er nåtilstand og har intet etterslep.

        Se modulens docstring om hvorfor `siste_rapport` IKKE brukes her
        selv om den er et ekte datofelt.
        """
        return kjoredato

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: list[dict], observed_at: str) -> Iterable[Observation]:
        """Én entitet per LOKALITET, med artene samlet til ett felt.

        Kilden leverer én rad per (lokalitet, art). Slås de ikke sammen,
        kolliderer de i `snapshot.NOKKEL` og den ene arten forsvinner
        stille — se modulens docstring.

        Filtreringen mot `FELTER` gjentas her selv om forespørselen
        allerede gjorde den. Samme begrunnelse og samme form som
        `romming.parse()`: dette laget er veien en ARKIVERT kropp kommer
        inn igjen på, og en kropp fra en framtidig versjon der `FELTER`
        er utvidet møter dette som det eneste som står mellom den og
        disken.
        """
        for loknr, rader in _samle(raw or []).items():
            forste = rader[0]
            felles = dict(entity_id=loknr,
                          entity_type=self.entity_type,
                          entity_name=_tekst(forste.get("navn")),
                          source=self.name, observed_at=observed_at)

            arter = sorted({_tekst(r.get("art")) for r in rader} - {""})

            for felt, verdi in (
                    ("har_fisk", _tekst(forste.get("har_fisk"))),
                    ("arter_tilstede", ARTSSKILLE.join(arter)),
                    ("antall_arter", str(len(arter))),
                    ("siste_rapport", _dato(forste.get("siste_rapport"))),
                    ("lokalitet_status", _tekst(forste.get("status_lokalitet"))),
                    ("dato_forbehold", DATO_FORBEHOLD),
                    ("arts_forbehold", ARTS_FORBEHOLD)):
                if verdi == "":
                    continue
                yield Observation(field=felt, value=verdi, **felles)


def _rens(rad: dict) -> dict:
    """Beholder bare `FELTER`. Kjøres i `fetch()`, FØR arkivering."""
    return {k: v for k, v in rad.items() if k in FELTER}


def _samle(rader: list[dict]) -> dict[str, list[dict]]:
    """Rader gruppert på `loknr`, i den rekkefølgen de kom.

    Rader uten `loknr` slippes: uten lokalitetsnummer finnes det ingen
    entitet å feste påstanden til, og et `objectid` er en intern nøkkel
    som ikke lar seg slå opp hos noen.
    """
    ut: dict[str, list[dict]] = {}
    for rad in rader:
        loknr = _tekst(rad.get("loknr"))
        if not loknr:
            continue
        ut.setdefault(loknr, []).append(rad)
    return ut


def _utgitt(headere: object) -> str:
    """`Last-Modified` -> ISO-8601 i UTC. Tom streng for «vet ikke».

    Samme rolle som `biomasse._utgitt`, men uten Wayback-varianten:
    denne kilden hentes bare levende. Verten sendte ingen slik header
    10.09.2026 — funksjonen finnes fordi den kan begynne, ikke fordi den
    gjør det i dag.
    """
    try:
        rå = headere.get("Last-Modified")          # type: ignore[union-attr]
    except AttributeError:
        return ""
    if not rå:
        return ""
    try:
        t = dt.datetime.strptime(rå, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return ""
    return t.replace(tzinfo=dt.timezone.utc).isoformat()
