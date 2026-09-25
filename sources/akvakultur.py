"""Akvakulturregisteret (Fiskeridirektoratet) — lokaliteter.

Åpent API, ingen nøkkel. Dette er kilden som gjør prosjektet til havbruk
og ikke bare et generisk selskapsregister: kapasitet per lokalitet over
tid er det Enhetsregisteret aldri kan svare på.

Endepunkt: https://api.fiskeridir.no/pub-aqua/api/v1/sites
Swagger:   https://api.fiskeridir.no/pub-aqua/api/swagger-ui/index.html

## Paginering — målt 17.08.2026, MÅLT PÅ NYTT 19.09.2026

`range` er et INKLUSIVT intervall, ikke side/størrelse: `0-99` gir de
hundre første, `100-199` de neste hundre. Taket er 100 rader per kall.

**Rettelse 19.09.2026.** Fram til i dag sto det her at et spenn over 100
«ikke gir feilmelding — det gir stille ÉN rad», med `range=0-999` som
måling. Det reproduserer ikke. Målt mot levende API i dag, både `/sites`
og `/licenses`:

    range=0-98     200   99 rader
    range=0-99     200  100 rader
    range=0-100    400  {"errors":["The range specification is out of
                        bounds. Limit is set to: 100. Range can be
                        specified e.g: 0-99"]}
    range=0-199    400  samme
    range=0-999    400  samme

Kanten er eksakt 100, og over den svarer tjenesten 400 med taket i
klartekst. `_http.get()` kaller `raise_for_status()`, så en for bred
`range` kaster før noe kommer tilbake til løkka her.

Hvorfor den gamle påstanden sannsynligvis var en målefeil og ikke en
endring hos motparten: feilkroppen er en dict med ÉN nøkkel (`errors`),
og `len()` av den er 1. Et måleskript som skriver `len(json)` uten å se
på statuskoden leser altså «1 rad» der svaret var en feil. Den samme
feilen ble gjort på nytt 19.09.2026 før den ble oppdaget. Det kan ikke
bevises i ettertid at det var dette som skjedde 17.08 — men gjennom
`_http.get()` kunne symptomet aldri oppstått, for 400 kaster.

Slutt-testen er MÅLT sunn i tillegg: `range=1700-1799` gir 82 rader,
`1800-1899` gir 0, og `5000-5099` gir 0. En kort side betyr her ekte
slutt, og det finnes ingen `exceededTransferLimit`-ekvivalent å lese —
til forskjell fra ArcGIS-lagene, se `sources/_arcgis.py`.

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

# Maks antall rader API-et gir per kall, og vi ligger PRESIS PÅ TAKET.
# Målt 19.09.2026: 0-99 gir 100 rader, 0-100 gir 400 med «Limit is set
# to: 100». Ett tall opp og hver eneste kjøring feiler — høyt, og det er
# den ufarlige retningen. Ikke øk uten å måle mot levende API.
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

    # NLOD. Lisenssiden lest 25.08.2026: «Den som tar i bruk data fra
    # Fiskeridirektoratet godtar automatisk lisensen.» Ordlyden er en av
    # de tre godkjente formene — se docs/LISENSKJEDE.md merknad A.
    attribusjon = ("Kilde: Fiskeridirektoratet",)
    entity_type = "lokalitet"

    # Ukentlig registeruttrekk: `gjelder_for()` returnerer kjøredatoen,
    # og snapshotet svarer på «hva står i registeret nå». En ny dato
    # ERSTATTER den forrige som svar på det spørsmålet. Målt: 0 dagers
    # avvik mellom observed_at og fetched_at i alle 5 snapshots.
    partisjonering = "henting"

    # `tillatelser_antall` ER `tillatelser` TALT. Begge leses av samme
    # `connections`-liste i samme rad — lisensnumrene der, lengden her.
    #
    # MÅLT 25.09.2026 over hele changeloggen (1 015 754 rader): 24 rader
    # for `tillatelser_antall` og 24 for `tillatelser`, og de gjelder
    # NØYAKTIG de samme 24 (lokalitet, par). 0 i hver retning — tallet har
    # aldri flyttet seg uten lista, og lista aldri uten tallet.
    #
    # Endrer tallet seg ALENE, teller det. Det ville betydd at en
    # tillatelse kom eller gikk uten at numrene endret seg, altså at
    # `connections` bar en oppføring uten `licenseNr`, og det er noe
    # kilden sier som ingenting annet sier. Regelen er «i samme par».
    #
    # ## `tillatelser_trukket` er MÅLT og IKKE deklarert
    #
    # Ikke fordi målingen er svakere: alle 13 radene faller i samme par
    # som `tillatelser`, og også i samme par som `tillatelser_antall`.
    # 13/13, mot 66/66 for det feltet som ble deklarert 24.09.
    #
    # Forskjellen er hva raden SIER. At T-T-0035 forsvant fra lokalitet
    # 10560 står i `tillatelser` (der forsvant feltet helt: den var
    # lokalitetens eneste). At den forsvant
    # fordi den ble TRUKKET, og ikke flyttet til en annen lokalitet, står
    # bare i `tillatelser_trukket` — registeret flytter oppføringen fra
    # `connections` til `obsoleteConnections`, og ingen av de to
    # gjenstående feltene bærer statusen. For lokalitet 12235 07.09.2026
    # er hele opplysningen der: `tillatelser` mistet M-VN-0024, -0025 og
    # -0026 og fikk -0027 og -0028, og bare `tillatelser_trukket` svarer
    # hvilke tre av de fem som ble trukket.
    #
    # Et tall som kan regnes ut av grunnfeltet er en FØLGE. Et ord om
    # hvorfor grunnfeltet flyttet seg er en OPPLYSNING, og den kan ikke
    # slås sammen bort uten at leseren må regne baklengs på noe som ikke
    # står noe sted. Samme skille som holdt `antall_ansatte` tellende
    # 24.09, bare fra den andre siden: der var samvariasjonen 46 %, her
    # er den 100 %, og prosenten avgjorde ingen av dem.
    #
    # ## `artsbegrensninger_antall` KAN ikke deklareres
    #
    # Den ser ut som en telling, og den er det — men lista den teller
    # (`speciesLimitations`) lagres ikke, så det finnes ingen grunnfelt å
    # slå den sammen med. Tallet er det ENESTE sporet vi har av
    # artsbegrensningene. MÅLT 25.09.2026 i de arkiverte kroppene:
    # formen er uendret gjennom alle 13 kropper (liste av objekt med
    # `code`, `faoAlpha3Code`, `latinName`, `nbNoName`, `nnNoName`,
    # `enGbName`; aldri fraværende, aldri noe annet enn en liste), mens
    # INNHOLDET falt fra 119 til 44 oppføringer mellom 17.08 og 24.08 og
    # har ligget der siden — 118 lokaliteter flyttet seg på én dato, og
    # det var ikke en omkoding. Hele målingen står i
    # docs/KILDE-AKVAKULTUR.md punkt 4.5, formen i punkt 6.
    avledet_av = {"tillatelser_antall": "tillatelser"}

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

        # Ett fullt kall som gir én rad.
        #
        # Vakten ble skrevet 17.08.2026 mot en påstand om at et for bredt
        # spenn gir stille én rad. Den påstanden reproduserer ikke — se
        # modulens docstring: tjenesten svarer 400, og `_http.get()`
        # kaster før vi kommer hit. Vakten kan altså ikke lenger nås av
        # den feilen den ble skrevet for.
        #
        # Den står likevel, og det er et valg: den koster to
        # sammenligninger i uka, og den fanger ENHVER vei til «hele
        # registeret ble én rad» — en base_url som peker på et
        # enkeltoppslag, en tjeneste som begynner å svare 200 med en
        # tom-nær kropp, et filter vi ikke vet at vi har. Å fjerne den
        # ville byttet en billig vakt mot ingenting.
        if len(lokaliteter) < SPENN and len(lokaliteter) <= 1:
            raise ValueError(
                f"Fikk bare {len(lokaliteter)} lokalitet(er) totalt. "
                f"Registeret har 1782 (målt 19.09.2026). Enten peker "
                f"base_url et annet sted, eller tjenesten svarer 200 på "
                f"noe som ikke er hele laget."
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
