"""Lusetall (BarentsWatch fiskehelse) — lusepress per lokalitet per uke.

Verifisert mot levende tjeneste 18.08.2026, se docs/BARENTSWATCH-FUNN.md.
Spesifikasjon i docs/KILDE-LUSETALL.md.

Endepunkt: {base}/v1/geodata/fishhealth/locality/{year}/{week}
Alle lokaliteter for én uke i ett kall — også brakklagte og
ikke-rapporterende, som kommer med flagg i stedet for å utelates.

## Om koblingen

`localityNo` HER er `siteNr` hos Fiskeridirektoratet. Verifisert: 100 %
av 1777 lokaliteter i uke 30/2026 finnes i akvakultursnapshotet, null
finnes bare her. Nummeret er nøkkelen, ikke navnet — navnene skiller seg
på store og små bokstaver mellom kildene.

Derfor emitter denne kilden ikke `navn`. Akvakultur eier lokalitetsnavnet,
og to kilder som skriver samme felt med ulik skrivemåte ville lagt igjen
en permanent falsk forskjell i dataene.

## Om etterslepet

Inneværende uke har 5 % av aktive lokaliteter rapportert. Uke N-4 har
99,3 %. Snapshots er append-only, så en ufullstendig uke er permanent —
derfor hentes uke N-4, og derfor nekter kilden å skrive en uke der under
80 % av de aktive har rapportert.

## Om observed_at

`observed_at` er mandagen i ISO-uka dataene gjelder for, ikke dagen vi
hentet dem. Uten det skillet kan etterslepet ikke håndteres i det hele
tatt. Se beslutningen fra 18.08.
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any, Callable, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source

STANDARD_BASE = "https://www.barentswatch.no/bwapi"
STANDARD_TOKEN_URL = "https://id.barentswatch.no/connect/token"

# Tidligste uke med data. 2010 og 2011 gir 200 OK med tom liste, ikke 404.
TIDLIGSTE = (2012, 1)

# Ingen dokumentert ratebegrensning, ingen X-RateLimit-headere. Målt
# 0,19 s per kall. Pausen er forsikring, ikke etterlevelse: fravær av en
# dokumentert grense er ikke fravær av en grense, og vi skal bruke denne
# kilden i to år.
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


# Feltnavn er en kontrakt mot historikken. Døper du om et felt senere,
# leser diffen det som at det gamle forsvant og et nytt oppsto.
#
# `navn` er bevisst utelatt — se modulens docstring.
FELTER: dict[str, Callable[[dict], Any]] = {
    # --- lusepresset, hele grunnen til at kilden finnes ---
    "voksne_hunnlus": lambda r: r.get("avgAdultFemaleLice"),

    # Skiller "rapportert null lus" fra "ikke rapportert". Uten dette blir
    # en manglende rapport til en null i enhver analyse, og det er feil på
    # den farlige måten. Samme skille som ansatte_er_registrert.
    "lus_er_rapportert": lambda r: r.get("hasReportedLice"),

    # --- drift ---
    "brakklagt": lambda r: r.get("isFallow"),
    "har_laksefisk": lambda r: r.get("hasSalmonoids"),
    "er_slaktemerd": lambda r: r.get("isSlaughterHoldingCage"),
    "er_landbasert": lambda r: r.get("isOnLand"),

    # --- tiltak mot lus ---
    "har_rensefisk": lambda r: r.get("hasCleanerfishDeployed"),
    "har_mekanisk_fjerning": lambda r: r.get("hasMechanicalRemoval"),
    "har_medikamentell_behandling": lambda r: r.get("hasSubstanceTreatments"),

    # --- sykdom ---
    "har_pd": lambda r: r.get("hasPd"),
    "har_ila": lambda r: r.get("hasIla"),
}


class Lusetall(Source):
    name = "lusetall"
    entity_type = "lokalitet"
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.lusetall.aktiv", False))
        self._token: str | None = None
        self._token_utloper: float = 0.0

    # ---- autentisering -------------------------------------------------

    def _hent_token(self) -> str:
        """Token caches og gjenbrukes. Backfill er 730 kall; ett
        token-kall per API-kall er hverken nødvendig eller høflig."""
        if self._token and time.monotonic() < self._token_utloper:
            return self._token

        # get() kaster hvis miljøvariabelen mangler. Det er med vilje: en
        # kilde som ikke får logge inn skal feile rødt, ikke returnere
        # tomt — ellers ser den ut som en uke uten lus.
        cid = get("kilder.lusetall.client_id")
        sec = get("kilder.lusetall.client_secret")
        if not cid or not sec:
            raise RuntimeError(
                "BARENTSWATCH_CLIENT_ID/-SECRET mangler. Kilden feiler "
                "heller enn å levere tomt."
            )

        url = get("kilder.lusetall.token_url", STANDARD_TOKEN_URL)
        svar = httpx.post(url, data={
            "client_id": cid,
            "client_secret": sec,
            "grant_type": "client_credentials",
            "scope": "api",
        }, timeout=30)

        if svar.status_code == 400:
            # Feil secret gir 400 invalid_client, ikke 401. Verdt å si.
            raise RuntimeError(
                f"400 fra token-endepunktet ({svar.text[:120]}). Sjekk at "
                f"secreten i portalen er den samme som i miljøet."
            )
        svar.raise_for_status()

        data = svar.json()
        self._token = data["access_token"]
        # Fornyes 60 s før utløp, så et kall ikke dør midt i en backfill.
        self._token_utloper = time.monotonic() + int(data.get("expires_in", 3600)) - 60
        return self._token

    def _klient(self) -> httpx.Client:
        return httpx.Client(
            headers={"Authorization": f"Bearer {self._hent_token()}",
                     "Accept": "application/json"},
            timeout=60,
        )

    # ---- henting -------------------------------------------------------

    def hent_uke(self, aar: int, uke: int, client: httpx.Client | None = None) -> dict:
        """Rå respons for én uke. Brukes av både fetch() og backfill."""
        base = get("kilder.lusetall.base_url", STANDARD_BASE).rstrip("/")
        egen = client is None
        c = client or self._klient()
        try:
            svar = c.get(f"{base}/v1/geodata/fishhealth/locality/{aar}/{uke}")
            svar.raise_for_status()
            return svar.json()
        finally:
            if egen:
                c.close()

    def fetch(self) -> dict:
        uker = int(get("kilder.lusetall.uker_etterslep", 4))
        aar, uke = uke_med_etterslep(dt.date.today(), uker)
        rå = self.hent_uke(aar, uke)
        self.advarsler = _vurder_rapportering(rå)
        return rå

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: dict, observed_at: str) -> Iterable[Observation]:
        """observed_at kommer fra kjernen, men lusetall vet bedre: dataene
        gjelder mandagen i uka de ble målt, ikke dagen vi hentet dem."""
        aar, uke = raw.get("year"), raw.get("week")
        gjelder = mandag(int(aar), int(uke)) if aar and uke else observed_at

        for lok in raw.get("localities", []):
            nr = lok.get("localityNo")
            if nr is None:
                continue
            navn = lok.get("name", "")

            for felt, hent in FELTER.items():
                verdi = hent(lok)
                if verdi is None:
                    continue
                yield Observation(
                    entity_id=str(nr),
                    entity_type=self.entity_type,
                    entity_name=str(navn),
                    field=felt,
                    value=str(verdi),
                    source=self.name,
                    observed_at=gjelder,
                )


def rapportert_andel(rå: dict) -> tuple[int, int, float]:
    """(aktive, rapportert, andel). Andelen måles mot AKTIVE lokaliteter.

    Mot totalen ville tallet vært rundt 32 %, fordi to tredeler er
    brakklagte og ikke skal rapportere. Det ville gjort vakten meningsløs.
    """
    lok = rå.get("localities", [])
    aktive = [x for x in lok if not x.get("isFallow")]
    rapportert = [x for x in aktive if x.get("hasReportedLice")]
    andel = len(rapportert) / len(aktive) if aktive else 0.0
    return len(aktive), len(rapportert), andel


def _vurder_rapportering(rå: dict) -> list[str]:
    """Advarsel hvis uka ser ufullstendig ut. Ikke exception: snapshotet
    skal fortsatt skrives, men jobben skal bli rød så uka kan hentes på
    nytt senere."""
    grense = float(get("kilder.lusetall.min_rapportert_andel", 0.80))
    aktive, rapportert, andel = rapportert_andel(rå)
    if aktive and andel < grense:
        return [
            f"lusetall uke {rå.get('week')}/{rå.get('year')}: bare "
            f"{andel:.1%} av {aktive} aktive lokaliteter har rapportert "
            f"(grense {grense:.0%}). Uka er trolig for fersk — hent den "
            f"på nytt senere."
        ]
    return []
