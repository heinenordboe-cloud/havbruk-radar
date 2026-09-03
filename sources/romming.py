"""Rømming — hendelser rapportert fra oppdretter.

Endepunkt: gis.fiskeridir.no/server/rest/services/Yggdrasil/Rømming/
           MapServer/0/query

Verifisert mot levende tjeneste 03.09.2026. Ingen nøkkel, ingen
registrering, ingen autentisering. `copyrightText` på tjenesten er
«Fiskeridirektoratet» — NLOD, og attribusjonen er et vilkår.

## Hendelsesdata, ikke aggregat

578 rader, én per rømmingsmelding, 2016-01-03 .. 2026-07-23. Hver rad
bærer `loknr`, som kobler rett mot `akvakultur` og videre mot
`eierskap`. 559 av 578 (96,7 %) peker på en lokalitet vi kjenner.

## observed_at er RØMMINGSÅRET, ikke hentetidspunktet

Ett snapshot per år, `<år>-12-31`, med den eksakte datoen i feltet
`rommingsdato`. Samme mønster som de 106 månedlige biomasse-snapshotene
og de 21 årssnapshotene i eierskapshistorikken: en hendelse hører til
tidspunktet den skjedde.

## Hvorfor kilden kjøres av backfill.py og ikke av run.py

Fordi `run.py` skriver ETT snapshot per kilde per kjøring, og den
invarianten bærer frekvensvakten, `finnes_allerede()` og
feilisoleringen. Elleve årganger i én kjøring kan ikke uttrykkes der.

Det er samme begrunnelse som `_backfill_maaneder` gir for at
revisjonskjøringen ligger utenfor `run.py`, og konsekvensen er den
samme: kilden får ingen post i health.json. Se
docs/beslutninger/2026-09-03-romming.md for hva det koster og hva
alternativet ville vært.

Backfillen er IDEMPOTENT på innhold: den skriver bare et år der radene
faktisk har endret seg. En ukentlig `backfill.py --kilde romming
--romming` koster derfor ett HTTP-kall og skriver ingenting når
ingenting har skjedd — det er den anbefalte kadensen.

## PERSONVERN: fritekstfeltene hentes IKKE

Tjenesten leverer to fritekstfelter skrevet av oppdretter,
`beskrivelse` (496 utfylte) og `gjenfangst_beskrivelse` (513 utfylte).
De inneholder persondata. Målt 03.09.2026, ordrett fra responsen:

    «Jan K Aarak tlf:90044345 er lokal fisker»
    «Fiskeridirektoratet ved Kristian Knox ble kontaktet umiddelbart»

— altså en navngitt privatperson med telefonnummer, en navngitt
saksbehandler, og ett felt med innlimt e-postkorrespondanse.

Fritekst kan ikke renses. En regex som stryker det som LIGNER et navn
eller et telefonnummer er den samme syntaktiske prøven på et semantisk
spørsmål som `core/persondata.py` advarer mot, og den ville feilet
stille på det den ikke kjente igjen. Feltene hentes derfor ikke, og de
forlater aldri `fetch()` — rå-arkivet ligger i git og er append-only.

## PERSONVERN: `selskapsnavn` lagres ikke

Responsen har ingen organisasjonsnummer — bare `selskapsnavn`
(«innehaver»), 138 distinkte verdier. Uten nummer finnes det ingen
autoritativ vei til organisasjonsformen, og regelen er uendret: det
filtreres på TYPE, aldri på navnesyntaks.

Brregs navnesøk ble prøvd og duger ikke. Det er et RELEVANSSØK, ikke et
oppslag: «LERØY MIDT AS» gir 439 228 treff, og «Måsøval Fiskeoppdrett
AS» rangerer «MÅSØVAL DRIFT» og «MÅSØVAL MULTISERVICE» — begge ENK —
blant de tre øverste. Å plukke øverste treff ville gitt feil selskap i
noen tilfeller og et enkeltpersonforetak i andre.

«Vet ikke» betyr aldri «slipp gjennom», så navnet lagres ikke.

Hendelsen selv er ikke persondata, og den beholdes: `loknr`, dato, art
og antall er lokalitets- og virksomhetsdata. Hvem som drev lokaliteten
kan leses av `eierskap` gjennom `loknr` — med det forbeholdet at det er
DAGENS eier og ikke nødvendigvis den som drev da rømmingen skjedde.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

STANDARD_BASE = ("https://gis.fiskeridir.no/server/rest/services/"
                 "Yggdrasil/R%C3%B8mming/MapServer/0/query")

# Tjenestens `maxRecordCount` er 2000. Vi ber om 1000 for å ligge trygt
# under, og pagineringen tar resten.
SPENN = 1000
MAKS_SIDER = 100

# Feltene som HENTES. Alt som ikke står her forlater aldri tjenesten.
#
# `beskrivelse`, `gjenfangst_beskrivelse` og `selskapsnavn` er bevisst
# utelatt — se modulens docstring. Det samme er `lat`/`lon`: posisjonen
# ligger allerede i `akvakultur` for lokaliteten, og to kilder til samme
# koordinat er to tellere for samme sak.
FELTER = (
    "objectid", "globalid", "loknr", "navn", "rommingsdato",
    "rommingsdato_antatt", "art", "storrelse", "storrelse_estimert",
    "status", "antall_romt_estimert", "antall_romt_fisk",
    "status_lokalitet", "kapsitet_lok", "plassering", "vannmiljo",
    "fylke", "kommunenr", "kommune", "rensefisk", "rensefisk_art",
    "rensefisk_antall_romt_estimert", "rensefisk_total",
    "rensefisk_antall_romt", "gjenfangst_iverksatt",
    "gjenfangst_gjennomfort", "intervall",
)

# Feltene som ALDRI skal hentes, og som `fetch()` fjerner om tjenesten
# skulle begynne å sende dem uoppfordret. Navnene står her framfor bare
# å være utelatt fra FELTER, slik at en vakt kan lete etter dem.
FORBUDTE = ("beskrivelse", "gjenfangst_beskrivelse", "selskapsnavn")

# Feltnavn ut, med kildens egne navn oversatt til repoets. Verdien
# lagres ORDRETT — se `antall_romt_estimert`, som er et INTERVALL
# («1-10», «Mer enn 10 000») og ikke et tall.
UT = {
    "loknr": "lokalitet_nr",
    "navn": "lokalitet_navn",
    "art": "art",
    "storrelse": "storrelse_kg",
    "storrelse_estimert": "storrelse_estimert_kg",
    "status": "meldingsstatus",
    "antall_romt_estimert": "antall_romt_estimert",
    "antall_romt_fisk": "antall_romt_endelig",
    "status_lokalitet": "lokalitet_status",
    "kapsitet_lok": "lokalitet_kapasitet",
    "plassering": "plassering",
    "vannmiljo": "vannmiljo",
    "fylke": "fylke",
    "kommunenr": "kommunenummer",
    "kommune": "kommune",
    "rensefisk": "har_rensefisk",
    "rensefisk_art": "rensefisk_art",
    "rensefisk_antall_romt_estimert": "rensefisk_romt_estimert",
    "rensefisk_total": "rensefisk_total",
    "rensefisk_antall_romt": "rensefisk_romt_endelig",
    "gjenfangst_iverksatt": "gjenfangst_iverksatt",
    "gjenfangst_gjennomfort": "gjenfangst_gjennomfort",
    "intervall": "intervall",
}

# Forbeholdet om hva GJENFANGST faktisk er. Bæres på hver rad, som
# `dato_forbehold` i eierskapshistorikken (CLAUDE.md 1b-3).
GJENFANGST_FORBEHOLD = (
    "gjenfangst_iverksatt (yes/no) og gjenfangst_gjennomfort (1/0) er "
    "JA/NEI-felter, ikke tall. Tjenesten oppgir INGEN gjenfanget mengde. "
    "En serie «rapportert mot gjenfanget» kan derfor ikke bygges av "
    "denne kilden — bare «rapportert, og om gjenfangst ble forsøkt»."
)

# Forbeholdet om antallet. `antall_romt_estimert` er et INTERVALL.
ANTALL_FORBEHOLD = (
    "antall_romt_estimert er oppdretters umiddelbare anslag og oppgis "
    "som et INTERVALL («1-10», «1000-10000», «Mer enn 10 000»). Det "
    "lagres ordrett og skal ikke gjøres om til et punktestimat. "
    "antall_romt_endelig settes når skadeomfanget er fastlagt, og "
    "mangler for 23,4 % av hendelsene."
)


def _dato(ms: object) -> str:
    """Epoch-millisekunder -> ISO-dato. Tom streng for manglende.

    UTC, eksplisitt. Kilden oppgir ingen tidssone, og en naiv
    `utcfromtimestamp` ville vært et tidspunkt uten sone i en kjede der
    alt annet er sonebevisst.
    """
    if ms in (None, ""):
        return ""
    return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc).date().isoformat()


def _rens(rad: dict) -> dict:
    """LAG 1: fjerner de forbudte feltene og beholder bare FELTER.

    Kjøres i `fetch()`, altså FØR arkivering. Rå-arkivet ligger i git og
    er append-only; en fritekst med et telefonnummer som kommer inn der,
    kan ikke fjernes igjen.
    """
    return {k: v for k, v in rad.items()
            if k in FELTER and k not in FORBUDTE}


class Romming(Source):
    name = "romming"
    entity_type = "romming"
    version = "1"

    # Kjøres av backfill.py, ikke av run.py — se modulens docstring.
    # Står likevel her fordi kontrakten krever den, og fordi den er
    # riktig for den anbefalte kadensen: ukentlig gjenkjøring av
    # backfillen, som skriver bare når noe faktisk har endret seg.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.romming.aktiv", False))

    # ---- henting -------------------------------------------------------

    def fetch(self, kjoredato: str) -> list[dict]:
        """Alle rømmingshendelser, RENSET før arkivering.

        Returnerer den filtrerte lista og ikke tjenestens råsvar. Det er
        et bevisst brudd på hovedregelen, av samme grunn og med samme
        presedens som `enhetsregisteret` og `eierskap`: råsvaret
        inneholder navngitte privatpersoner med telefonnummer i
        fritekst, og arkivet er uopprettelig.

        `utvalg` er `{}` og ikke ukjent — vi ber om alt (`where=1=1`) og
        får alt. At tre felter faller fra er VÅR filtrering, og den står
        i `utvalg` slik at et snapshot alene kan svare på hva vi hentet.

        `published_at` settes IKKE. Tjenesten sender ingen
        `Last-Modified`, og regel 1b-7 er tydelig: standarden er «vet
        ikke», aldri hentetidspunktet.
        """
        self.utvalg = {"utelatte_felter": sorted(FORBUDTE)}

        base = get("kilder.romming.base_url", STANDARD_BASE)
        c = httpx.Client(timeout=120.0, follow_redirects=True)
        ut: list[dict] = []
        try:
            for i in range(MAKS_SIDER):
                svar = _http.get(
                    c, base, hva=f"romming side {i}",
                    params={"where": "1=1", "outFields": ",".join(FELTER),
                            "returnGeometry": "false", "f": "json",
                            "orderByFields": "objectid",
                            "resultOffset": i * SPENN,
                            "resultRecordCount": SPENN})
                d = svar.json()
                if "error" in d:
                    raise RuntimeError(f"romming: {d['error']}")
                trekk = d.get("features") or []
                ut += [_rens(x.get("attributes") or {}) for x in trekk]
                if len(trekk) < SPENN:
                    break
            else:
                raise RuntimeError(
                    f"romming: over {MAKS_SIDER} sider. Pagineringen "
                    f"teller ikke ned — er tjenesten endret?")
        finally:
            c.close()
        return ut

    def gjelder_for(self, kjoredato: str) -> str:
        """Kjøredatoen. Backfillen overstyrer med rømmingsåret.

        Metoden finnes for kontraktens skyld. Den brukes ikke av
        backfill-modusen, som skriver ett snapshot per år ut fra
        `rommingsdato` — se `aar_i()`.
        """
        return kjoredato

    def aar_i(self, raw: list[dict]) -> list[str]:
        """Årene hendelsene faller i, eldst først.

        Samme rolle som `biomasse.maaneder()` og
        `ekspertgruppen.aar_i()`: kalleren skal slippe å kjenne
        datoformatet for å vite hvilke perioder den har fått.
        """
        aar = {_dato(r.get("rommingsdato"))[:4] for r in (raw or [])}
        return [f"{a}-12-31" for a in sorted(aar - {""})]

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: list[dict], observed_at: str) -> Iterable[Observation]:
        """LAG 2. Ett år av gangen.

        Filtreringen gjentas her selv om `fetch()` har gjort den. Det er
        ikke belte og bukseseler: `parse()` er veien en ARKIVERT kropp
        kommer inn igjen på, og en kropp fra før filteret — eller fra en
        framtidig versjon der `fetch()` er endret — møter dette laget
        som det eneste som står mellom den og disken.

        Samme begrunnelse og samme form som `enhetsregisteret.parse()`.
        """
        aar = observed_at[:4]
        for rad in raw or []:
            dato = _dato(rad.get("rommingsdato"))
            if dato[:4] != aar:
                continue

            # LAG 2: forbudte felter slippes aldri gjennom, uansett hva
            # kroppen måtte inneholde.
            rad = {k: v for k, v in rad.items() if k not in FORBUDTE}

            nøkkel = rad.get("globalid") or rad.get("objectid")
            if not nøkkel:
                continue
            # globalid, ikke (loknr, dato): to hendelser DELER lokalitet
            # og dato i to tilfeller (36817 og 32457), og med det paret
            # som nøkkel ville den ene stilltiende overskrevet den andre
            # i `snapshot.NOKKEL`.
            felles = dict(entity_id=str(nøkkel).strip("{}"),
                          entity_type=self.entity_type,
                          entity_name=str(rad.get("navn") or ""),
                          source=self.name, observed_at=observed_at)

            yield Observation(field="rommingsdato", value=dato, **felles)
            antatt = _dato(rad.get("rommingsdato_antatt"))
            if antatt:
                yield Observation(field="rommingsdato_antatt", value=antatt,
                                  **felles)

            for kilde_felt, ut_felt in UT.items():
                verdi = rad.get(kilde_felt)
                if verdi is None or verdi == "":
                    continue
                yield Observation(field=ut_felt, value=str(verdi), **felles)

            for felt, verdi in (("gjenfangst_forbehold", GJENFANGST_FORBEHOLD),
                                ("antall_forbehold", ANTALL_FORBEHOLD)):
                yield Observation(field=felt, value=verdi, **felles)
