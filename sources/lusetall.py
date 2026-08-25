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
from typing import Any, Callable, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _barentswatch

# Innlogging og ukeregning deles med `sjotemperatur` — se
# sources/_barentswatch.py. Navnene re-eksporteres her fordi
# `backfill.py` og testene importerer dem fra denne modulen, og fordi et
# navn som flyttes er et navn som kan bli borte i en importfeil hos noen
# andre. Delt KODE, ikke delt TILSTAND: hver kilde har sin egen Tilgang.
from sources._barentswatch import (  # noqa: F401
    PAUSE_S,
    STANDARD_BASE,
    STANDARD_TOKEN_URL,
    TIDLIGSTE,
    mandag,
    uke_med_etterslep,
)


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
        self._tilgang = _barentswatch.Tilgang(self.name)

    # ---- autentisering -------------------------------------------------
    #
    # Selve innloggingen ligger i sources/_barentswatch.py, delt med
    # `sjotemperatur`. De to metodene her er igjen fordi de er kildens
    # egen flate: testen for 400 invalid_client kaller `_hent_token()`
    # direkte, og en delegasjon er billigere enn å flytte en test som
    # dokumenterer en feil vi faktisk har hatt.

    def _hent_token(self) -> str:
        return self._tilgang.token()

    def _klient(self) -> httpx.Client:
        return self._tilgang.klient()

    # ---- henting -------------------------------------------------------

    def hent_uke(self, aar: int, uke: int, client: httpx.Client | None = None) -> dict:
        """Rå respons for én uke. Brukes av både fetch() og backfill."""
        # KJENT ingen filtrering, ikke ukjent. `/locality/{år}/{uke}` tar
        # ingen utvalgsparametre og returnerer alle lokaliteter som
        # rapporterte den uka — det er ikke fravær av kunnskap, det er
        # kunnskap om fravær av filtrering. Se core/utvalg.py om de tre
        # tilstandene, og `lus_er_rapportert` for det samme skillet en
        # etasje ned: None og 0 er ikke det samme.
        #
        # Settes HER og ikke i fetch(), fordi hent_uke() er det ene stedet
        # både ukejobben og backfill.py går gjennom. Sto det i fetch(),
        # bar backfillede rader dårligere proveniens enn ukentlige.
        self.utvalg = {}

        base = get("kilder.lusetall.base_url", STANDARD_BASE).rstrip("/")
        egen = client is None
        c = client or self._klient()
        try:
            # Gjennom Tilgang og ikke _http direkte: den legger én
            # re-autentisering på en 401 oppå retryen. Se F13.
            svar = self._tilgang.get(
                c, f"{base}/v1/geodata/fishhealth/locality/{aar}/{uke}",
                hva=f"uke {uke}/{aar}",
            )
            return svar.json()
        finally:
            if egen:
                c.close()

    def _uke_naa(self, kjoredato: str) -> tuple[int, int]:
        """Uka kilden henter når vi kjører `kjoredato`. Ett sted, ikke to.

        Både fetch() og gjelder_for() må svare på det samme spørsmålet, og
        begge får datoen inn. Ingen klokkeoppslag her: slo de opp hver sin
        klokke, kunne de svare ulikt rundt midnatt, og da får fila navn
        etter én uke og innhold fra en annen. Se Source.fetch.
        """
        uker = int(get("kilder.lusetall.uker_etterslep", 4))
        return uke_med_etterslep(dt.date.fromisoformat(kjoredato), uker)

    def gjelder_for(self, kjoredato: str) -> str:
        """Mandagen i uka vi henter — ikke dagen vi henter den.

        Se Source.gjelder_for. Dette er den samme regelen backfillen
        bruker når den navngir en fil, så en uke hentet ukentlig og den
        samme uka hentet i backfill havner på nøyaktig samme filnavn.
        """
        return mandag(*self._uke_naa(kjoredato))

    def fetch(self, kjoredato: str) -> dict:
        aar, uke = self._uke_naa(kjoredato)
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
