"""Akvakulturregisteret (Fiskeridirektoratet) — lokaliteter.

Åpent API, ingen nøkkel. Dette er kilden som gjør prosjektet til havbruk
og ikke bare et generisk selskapsregister: kapasitet per lokalitet over
tid er det Enhetsregisteret aldri kan svare på.

Endepunkt: https://api.fiskeridir.no/pub-aqua/api/v1/sites
Swagger:   https://api.fiskeridir.no/pub-aqua/api/swagger-ui/index.html

## Paginering — verifisert mot levende API 17.08.2026

`range` er et INKLUSIVT intervall, ikke side/størrelse: `0-99` gir de
hundre første, `100-199` de neste hundre.

Fallgruven: et spenn på mer enn 100 gir ikke feilmelding. Det gir stille
ÉN rad. `range=0-999` returnerte 1 lokalitet, ikke 1000. Uoppdaget ville
det betydd én lokalitet i uka i historikken, og det ville du sett først
den dagen du prøvde å bruke dataene. Derfor er SPENN en konstant her, og
derfor sjekker fetch() at et fullt kall faktisk gir fulle sider.

## Personvern

`connections` inneholder kun tillatelsesnumre, datoer og status — ingen
innehaver, ingen persondata. Verifisert i faktisk respons.

Innehaveridentitet ligger på `/licenses`, som er en egen kilde og en egen
vurdering: der finnes `openLegalEntityNr` (ni siffer, organisasjonsnummer)
ved siden av en hashet `legalEntityNrId`. At det ene feltet heter "open"
tyder på at innehavere som er privatpersoner ikke får nummeret publisert.
Den kilden må derfor filtrere på ni siffer før noe lagres.

## Om entity_id

`siteNr` er valgt framfor `siteId`. Det er lokalitetsnummeret næringa
faktisk bruker, det er lesbart i en diff, og det lar seg slå opp hos
Fiskeridirektoratet. `siteId` er en intern nøkkel, og registeret har i
tillegg `versionId` som endres ved hver versjonering — begge er dårlige
ankere for en historikk som skal leses av mennesker.
"""

from typing import Any, Callable, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

STANDARD_BASE = "https://api.fiskeridir.no/pub-aqua/api/v1"

# Maks antall rader API-et gir per kall. Verifisert: 100 virker, 101+ gir
# stille én rad. Ikke øk uten å teste mot levende API.
SPENN = 100

# Ikke la en skrivefeil i config gi stille datatap.
MAKS_SIDER = 200


def _p(*nokler: str) -> Callable[[dict], Any]:
    """Nøstet oppslag: _p("placement", "municipalityCode")."""

    def hent(rad: dict) -> Any:
        node: Any = rad
        for nokkel in nokler:
            if not isinstance(node, dict):
                return None
            node = node.get(nokkel)
        return node

    return hent


def _lisensnumre(nokkel: str) -> Callable[[dict], Any]:
    """Sorterte tillatelsesnumre knyttet til lokaliteten.

    Sortert med vilje: uten det gir en vilkårlig rekkefølge fra API-et
    en falsk endring i diffen hver eneste uke.

    Endring her er et reelt signal — en tillatelse som flyttes til en
    annen lokalitet er kapasitet som flyttes.
    """

    def hent(rad: dict) -> Any:
        verdi = rad.get(nokkel)
        if not isinstance(verdi, list) or not verdi:
            return None
        numre = sorted(str(k.get("licenseNr")) for k in verdi if k.get("licenseNr"))
        return "; ".join(numre) or None

    return hent


def _antall(nokkel: str) -> Callable[[dict], Any]:
    def hent(rad: dict) -> Any:
        verdi = rad.get(nokkel)
        return len(verdi) if isinstance(verdi, list) else None

    return hent


def _liste(nokkel: str) -> Callable[[dict], Any]:
    def hent(rad: dict) -> Any:
        verdi = rad.get(nokkel)
        if not isinstance(verdi, list) or not verdi:
            return None
        return "; ".join(sorted(str(v) for v in verdi))

    return hent


# Feltnavn er en kontrakt mot historikken. Døper du om et felt senere,
# ser diffen det som at det gamle forsvant og et nytt oppsto.
FELTER: dict[str, Callable[[dict], Any]] = {
    "navn": lambda r: r.get("name"),

    # --- kapasitet: hele grunnen til at kilden finnes ---
    # Enheten lagres ALLTID sammen med tallet. Uten den er "780" ubrukelig
    # den dagen en lokalitet oppgis i antall i stedet for tonn.
    "kapasitet": lambda r: r.get("capacity"),
    "kapasitet_enhet": lambda r: r.get("capacityUnitType"),
    "kapasitet_midlertidig": lambda r: r.get("tempCapacity"),

    # --- produksjonsområde og trafikklys ---
    # prodAreaStatus er trafikklysordningen: RØD betyr pålagt nedtrekk,
    # GRØNN betyr vekstmulighet. Ingen publiserer denne koblet mot
    # lokalitet over tid.
    "prodomraade_kode": _p("placement", "prodAreaCode"),
    "prodomraade_navn": _p("placement", "prodAreaName"),
    "prodomraade_status": _p("placement", "prodAreaStatus"),

    # --- geografi ---
    "kommune": _p("placement", "municipalityName"),
    "kommunenummer": _p("placement", "municipalityCode"),
    "fylke": _p("placement", "countyName"),
    "fylkesnummer": _p("placement", "countyCode"),
    "breddegrad": lambda r: r.get("latitude"),
    "lengdegrad": lambda r: r.get("longitude"),

    # --- art ---
    "arter": _liste("speciesTypes"),
    "artsbegrensninger_antall": _antall("speciesLimitations"),

    # --- plassering og type ---
    "plasseringstype": lambda r: r.get("placementType"),
    "vanntype": lambda r: r.get("waterType"),
    "er_slakteri": lambda r: r.get("isSlaughtery"),
    "har_kommersiell_aktivitet": lambda r: r.get("hasCommercialActivity"),
    "har_samlokalisering": lambda r: r.get("hasColocation"),
    "har_samdrift": lambda r: r.get("hasJointOperation"),

    # --- tillatelser knyttet til lokaliteten ---
    "tillatelser": _lisensnumre("connections"),
    "tillatelser_antall": _antall("connections"),
    "tillatelser_trukket": _lisensnumre("obsoleteConnections"),

    # --- versjon og klarering ---
    "forste_klarering": lambda r: r.get("firstClearanceTime"),
    "klareringstype": lambda r: r.get("firstClearanceType"),
    "versjon_status": _p("version", "status"),
    "versjon_aarsak": _p("version", "versionCauseType"),
    "versjon_gyldig_fra": _p("version", "validFrom"),
}


class Akvakulturregisteret(Source):
    name = "akvakultur"
    entity_type = "lokalitet"

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.akvakultur.aktiv", False))

    def fetch(self, kjoredato: str) -> list[dict]:
        # `kjoredato` brukes ikke: registeret har ingen etterslep, og
        # svaret er hva som gjelder nå. Argumentet står fordi kontrakten
        # krever at en kilde FÅR tiden inn i stedet for å slå den opp —
        # se Source.fetch. En kilde som ikke trenger den, ignorerer den.
        base = get("kilder.akvakultur.base_url", STANDARD_BASE).rstrip("/")
        lokaliteter: list[dict] = []
        start = 0

        with httpx.Client(timeout=60, headers={"Accept": "application/json"}) as client:
            for side in range(MAKS_SIDER):
                svar = _http.get(
                    client,
                    f"{base}/sites",
                    params={"range": f"{start}-{start + SPENN - 1}"},
                    hva=f"sites {start}-{start + SPENN - 1}",
                )
                batch = svar.json()

                if not isinstance(batch, list):
                    raise ValueError(
                        f"Forventet liste fra /sites, fikk {type(batch).__name__}"
                    )

                lokaliteter.extend(batch)

                if len(batch) < SPENN:
                    break   # siste side

                start += SPENN
            else:
                raise RuntimeError(
                    f"Stoppet etter {MAKS_SIDER} sider uten å nå slutten. "
                    f"Enten har registeret vokst kraftig, eller pagineringen "
                    f"er endret."
                )

        # Ett fullt kall som gir én rad er symptomet på for bredt spenn.
        # Da samler du én lokalitet i uka uten å få feilmelding.
        if len(lokaliteter) < SPENN and len(lokaliteter) <= 1:
            raise ValueError(
                f"Fikk bare {len(lokaliteter)} lokalitet(er) totalt. "
                f"Sannsynligvis er SPENN for stort — API-et returnerer "
                f"stille én rad i stedet for å feile."
            )

        return lokaliteter

    def parse(self, raw: list[dict], observed_at: str) -> Iterable[Observation]:
        for lokalitet in raw:
            lok_nr = lokalitet.get("siteNr")
            navn = lokalitet.get("name", "")
            if lok_nr is None:
                continue

            for felt, hent in FELTER.items():
                verdi = hent(lokalitet)
                if verdi is None:
                    continue
                yield Observation(
                    entity_id=str(lok_nr),
                    entity_type=self.entity_type,
                    entity_name=str(navn),
                    field=felt,
                    value=str(verdi),
                    source=self.name,
                    observed_at=observed_at,
                )
