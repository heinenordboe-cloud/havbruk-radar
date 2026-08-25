"""Delt lag mot BarentsWatch. Innlogging og ukeregning, ikke kildelogikk.

Ligger i `sources/` med `_`-prefiks av samme grunn som `_http.py`:
registry hopper over den, og kjernen skal ikke vite at BarentsWatch
finnes. To kilder henter herfra — `lusetall` og `sjotemperatur` — og
begge trenger nøyaktig det samme tokenet og nøyaktig den samme
oversettelsen mellom ISO-uke og dato.

## Hvorfor tokenet deles, men økten ikke gjør det

Hver kilde får sin egen `Tilgang`. To kilder som henter i samme kjøring
gjør da to tokenkall i stedet for ett, og det er med vilje: en kilde som
feiler skal ikke kunne dra en annen med seg, heller ikke gjennom en delt
klient som er lukket eller et token som er invalidert. Kostnaden er ett
HTTP-kall i uka.

Det som deles er KODEN, ikke TILSTANDEN. Feilmeldingen om `400
invalid_client` er den dyrest lærte linja i denne fila (se
docs/BARENTSWATCH-FUNN.md), og den skal ikke finnes i to utgaver som kan
drifte fra hverandre.

## Hvorfor ukeregningen ligger her og ikke i én av kildene

`mandag()` og `uke_med_etterslep()` bodde i `sources/lusetall.py` fram
til 24.08.2026, og `backfill.py` importerte dem derfra. Da
`sjotemperatur` kom til, ville det andre alternativet vært at den nye
kilden importerte fra den gamle — en kilde som avhenger av en annen
kilde, stikk i strid med at kilder er uavhengige plugins.

Valget av mandag som datoen en ISO-uke får står for alltid i filnavnene
til to kilder nå, ikke én. Det er derfor det er ett sted.
"""

from __future__ import annotations

import datetime as dt
import time

import httpx

from core.config import get
from sources import _http

STANDARD_BASE = "https://www.barentswatch.no/bwapi"
STANDARD_TOKEN_URL = "https://id.barentswatch.no/connect/token"

# Tidligste uke med data. 2010 og 2011 gir 200 OK med tom liste, ikke
# 404 — målt for begge endepunktene, se docs/BARENTSWATCH-FUNN.md og
# docs/KILDE-SJOTEMPERATUR.md.
TIDLIGSTE = (2012, 1)

# Ingen dokumentert ratebegrensning, ingen X-RateLimit-headere. Målt
# 0,19 s per kall mot ukeendepunktet og 0,8 s mot eksporten. Pausen er
# forsikring, ikke etterlevelse: fravær av en dokumentert grense er ikke
# fravær av en grense, og vi skal bruke denne kilden i to år.
PAUSE_S = 0.5


def mandag(aar: int, uke: int) -> str:
    """ISO-uke -> dato for mandagen. Uke 34/2026 -> '2026-08-17'.

    Valget står for alltid i filnavnene og skal ikke endres senere.
    """
    return dt.date.fromisocalendar(aar, uke, 1).isoformat()


def uke_med_etterslep(i_dag: dt.date, uker: int) -> tuple[int, int]:
    """ISO-år og -uke `uker` uker før `i_dag`."""
    d = i_dag - dt.timedelta(weeks=uker)
    iso = d.isocalendar()
    return iso.year, iso.week


class Tilgang:
    """OAuth2 client credentials for én kilde. Cacher tokenet.

    `kilde` er config-prefikset: `Tilgang("lusetall")` leser
    `kilder.lusetall.client_id` og så videre. Nøklene står i `config.yml`
    med `${}`-syntaks under HVER kilde som bruker dem, ikke bare én gang
    globalt — det er slik `core/miljo.py` klarer å si «denne AKTIVE
    kilden mangler en nøkkel» før innsamlingen starter, og å tie om en
    kilde som er slått av.
    """

    def __init__(self, kilde: str) -> None:
        self.kilde = kilde
        self._token: str | None = None
        self._token_utloper: float = 0.0

    def base_url(self) -> str:
        return get(f"kilder.{self.kilde}.base_url", STANDARD_BASE).rstrip("/")

    def token(self) -> str:
        """Token caches og gjenbrukes. En backfill er hundrevis av kall;
        ett tokenkall per API-kall er hverken nødvendig eller høflig."""
        if self._token and time.monotonic() < self._token_utloper:
            return self._token

        # get() kaster hvis miljøvariabelen mangler. Det er med vilje: en
        # kilde som ikke får logge inn skal feile rødt, ikke returnere
        # tomt — ellers ser den ut som en uke uten lus, eller en uke der
        # ingen målte temperaturen.
        cid = get(f"kilder.{self.kilde}.client_id")
        sec = get(f"kilder.{self.kilde}.client_secret")
        if not cid or not sec:
            raise RuntimeError(
                "BARENTSWATCH_CLIENT_ID/-SECRET mangler. Kilden feiler "
                "heller enn å levere tomt."
            )

        url = get(f"kilder.{self.kilde}.token_url", STANDARD_TOKEN_URL)
        try:
            svar = _http.post(url, hva="tokenkall", data={
                "client_id": cid,
                "client_secret": sec,
                "grant_type": "client_credentials",
                "scope": "api",
            }, timeout=30)
        except httpx.HTTPStatusError as e:
            # Feil secret gir 400 invalid_client, ikke 401. Verdt å si.
            # 400 er permanent, så _http prøver ikke igjen — feilen kommer
            # med én gang, slik den skal.
            if e.response.status_code == 400:
                raise RuntimeError(
                    f"400 fra token-endepunktet ({e.response.text[:120]}). "
                    f"Sjekk at secreten i portalen er den samme som i miljøet."
                ) from e
            raise

        data = svar.json()
        self._token = data["access_token"]
        # Fornyes 60 s før utløp, så et kall ikke dør midt i en backfill.
        self._token_utloper = time.monotonic() + int(data.get("expires_in", 3600)) - 60
        return self._token

    def klient(self, accept: str = "application/json") -> httpx.Client:
        return httpx.Client(
            headers={"Authorization": f"Bearer {self.token()}",
                     "Accept": accept},
            timeout=120,
        )
