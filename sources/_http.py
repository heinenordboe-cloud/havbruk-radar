"""Delt HTTP-lag for kildene. Retry på transiente feil, ikke på permanente.

Ligger i `sources/` og ikke i `core/`: dette er infrastruktur kildene
deler, ikke en del av kildekontrakten. Kjernen vet ikke at HTTP finnes,
og en kilde som henter fra en fil eller en database skal ikke arve noe
herfra. `_`-prefikset gjør at registry hopper over fila — den er en
hjelper, ikke en kilde.

## Hva som retryes, og hvorfor ikke resten

Retry på timeout, tilkoblingsfeil, 5xx og 429. Alle fire betyr «prøv
igjen senere»: motparten er nede, overbelastet eller uinteressert i
akkurat nå.

IKKE på 4xx utenom 429. En 404 er ikke midlertidig, og en 401 blir ikke
bedre av å spørre tre ganger. Retry der er tre bortkastede kall og
tjuefem sekunder ekstra på en feil som uansett skal opp — verre, det
utsetter feilmeldingen som forteller deg hva som faktisk er galt.

## Hvorfor ikke bare la kilden feile

Innsamlingen kjører én gang i uka. En kilde som taper på et
nettverksglitt mandag 05:00 taper uka, og uka kan ikke hentes igjen.
Det er hele asymmetrien dette repoet er bygget rundt: en ekstra
forespørsel koster ingenting, en tapt uke koster permanent.

Retry erstatter ikke feilisoleringen i runner. Den flytter grensen for
hva som regnes som en feil verdt å felle kilden for.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

# Antall forsøk TOTALT, ikke antall omforsøk. Tre kall, to pauser.
FORSOK = 3

# Eksponentiell backoff: pause før forsøk 2, 3, 4 ... Med FORSOK = 3
# brukes de to første. Den tredje står her fordi den er neste trinn i
# serien — heves FORSOK, trengs ingen annen endring.
PAUSER = (1.0, 4.0, 16.0)

# Motparten sier «senere», ikke «nei».
RETRY_STATUS = frozenset({429})

# Nettverksfeil som betyr at forespørselen aldri kom fram, eller ikke
# kom tilbake. Bevisst eksplisitt framfor httpx.TransportError, som også
# dekker UnsupportedProtocol — en skrivefeil i en URL er permanent.
TRANSIENTE = (httpx.TimeoutException, httpx.NetworkError,
              httpx.RemoteProtocolError)


def _skal_retry(svar: httpx.Response) -> bool:
    return svar.status_code >= 500 or svar.status_code in RETRY_STATUS


def utfor(kall: Callable[[], httpx.Response], hva: str,
          forsok: int = FORSOK, sov: Callable[[float], None] | None = None,
          ) -> httpx.Response:
    """Kjør `kall` med retry, og returner et svar som har bestått status.

    Kaster `httpx.HTTPStatusError` på siste forsøk hvis statusen ikke er
    2xx — også for de retrybare, slik at kalleren ser den ekte feilen og
    ikke en innpakning. Permanente 4xx kastes umiddelbart.

    `sov` er injiserbar for testenes skyld. Ingen test skal bruke fem
    sekunder på å bevise at backoff virker. Slås opp ved kall og ikke
    som default-argument, ellers bindes time.sleep ved definisjon og
    lar seg ikke bytte ut i en test.
    """
    sov = sov or time.sleep
    siste: Exception | None = None

    for n in range(1, forsok + 1):
        grunn: str | None = None

        try:
            svar = kall()
        except TRANSIENTE as e:
            siste = e
            grunn = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        else:
            if not _skal_retry(svar):
                # 2xx passerer; permanent 4xx kastes her og nå.
                svar.raise_for_status()
                return svar

            grunn = f"HTTP {svar.status_code}"
            try:
                svar.raise_for_status()
            except httpx.HTTPStatusError as e:
                siste = e

        if n == forsok:
            break

        pause = PAUSER[min(n, len(PAUSER)) - 1]
        print(f"    [retry] {hva}: forsøk {n}/{forsok} feilet ({grunn}), "
              f"venter {pause:g}s")
        sov(pause)

    print(f"    [retry] {hva}: ga opp etter {forsok} forsøk ({grunn})")
    assert siste is not None
    raise siste


def get(client: httpx.Client, url: str, hva: str | None = None,
        **kwargs: Any) -> httpx.Response:
    """client.get() med retry. Kaster hvis statusen ikke er 2xx."""
    return utfor(lambda: client.get(url, **kwargs), hva or f"GET {url}")


def post(url: str, hva: str | None = None, **kwargs: Any) -> httpx.Response:
    """httpx.post() med retry, uten delt klient. For tokenkall og annet
    som skjer én gang og ikke hører hjemme i kildens økt."""
    return utfor(lambda: httpx.post(url, **kwargs), hva or f"POST {url}")
