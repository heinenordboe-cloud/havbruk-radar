"""Kildekontrakten.

Dette er den viktigste filen i repoet. Alt annet er utskiftbart.
Så lenge en kilde returnerer Observation-objekter, trenger resten av
systemet aldri vite hvor dataene kom fra.
"""

from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass(frozen=True)
class Observation:
    """Én målt egenskap ved én entitet på ett tidspunkt.

    Alt normaliseres hit. Enhetsregisteret har ett skjema,
    Akvakulturregisteret et helt annet — men begge ender her.
    """

    entity_id: str      # orgnr (9 siffer) eller lokalitetsnummer
    entity_type: str    # "selskap" | "lokalitet"
    entity_name: str
    field: str          # "antall_ansatte", "kapasitet_tonn", "kommune"
    value: str          # alt lagres som tekst; typing skjer i analysen
    source: str         # navnet på kilden som observerte
    # ISO-dato snapshotet GJELDER FOR — ikke datoen vi hentet det.
    # `observed_at` handler om verden, `fetched_at` om oss. Ved ukentlig
    # innsamling faller de sammen; ved backfill spriker de, og da er en
    # backfillet rad kjennelig på at `fetched_at` ligger langt etter.
    # Se docs/beslutninger/2026-08-18-observed-at-er-gyldighetsdato.md.
    observed_at: str

    fetched_at: str = ""     # UTC-tidsstempel for hentingen
    source_version: str = ""  # source.version på hentetidspunktet
    raw_hash: str = ""        # sha256 fra raw_arkiv.arkiver()

    # Hva kilden BA OM da denne raden ble hentet — kanonisk JSON fra
    # core/utvalg.py. `"{}"` betyr «kilden hentet alt», tom streng betyr
    # «kilden sa ingenting». De to er IKKE det samme, og snapshots
    # skrevet før 25.08.2026 har tom streng uansett hva kilden gjorde.
    #
    # Proveniens som de tre over, og stemplet av kjernen på samme måte:
    # ingen kilde setter dette feltet selv. Grunnen til at det må ligge
    # på raden og ikke i config: et snapshot skal kunne svare på om en
    # ny entitet er ny i VERDEN eller ny i UTVALGET, og det kan det ikke
    # hvis søket bare finnes i en fil som skrives om. Se core/utvalg.py.
    utvalg: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


class Source:
    """Arv fra denne. Kjernen finner deg automatisk.

    Ny kilde = ny fil i sources/. Ingen registrering, ingen import
    noe annet sted, ingen endring i core/.
    """

    name: str = "ukjent"
    entity_type: str = "selskap"
    enabled: bool = True
    version: str = "1"

    # Ting kilden vil si fra om uten å felle seg selv.
    #
    # Noen feil er for alvorlige til å ties i hjel, men for små til at
    # kilden skal kaste: et tomt NACE-søk betyr at én av syv koder er
    # utgått, og kaster fetch() da, mister du ukas data for de seks
    # andre. Kjernen samler disse opp og lar kjøringen ende rødt, slik
    # at én knekt ting koster én ting og ikke alt.
    #
    # SETT den, ikke append til den: `self.advarsler = [...]`. Gjør du
    # `self.advarsler.append(...)` treffer du lista på KLASSEN, som
    # deles av alle instanser og aldri tømmes.
    advarsler: list[str] = []

    # Hvilket UTVALG kilden ba om. `{"naeringskoder": ["03.211", ...]}`
    # — nøkkel til liste, se core/utvalg.py for formatet.
    #
    # SETTES AV `fetch()`, leses av kjernen etterpå. Nøyaktig samme
    # mekanikk som `advarsler`, og samme felle: SETT den
    # (`self.utvalg = {...}`), ikke muter dicten på klassen.
    #
    # At den settes av fetch() og ikke er en egen metode, er poenget.
    # En `utvalg(kjoredato)`-metode ville vært et ANDRE oppslag mot
    # config, og to oppslag som kan svare ulikt er mønsteret fra F6, F7
    # og F8. Setter fetch() den mens den henter, beskriver den
    # nødvendigvis det kallet som faktisk ble gjort.
    #
    # TRE tilstander, ikke to (se core/utvalg.py):
    #
    #   {"naeringskoder": [...]}   kjent utvalg
    #   {}                         kjent: kilden filtrerer ikke
    #   None                       ukjent — kilden sier ingenting
    #
    # Standarden er None og ikke {}. Sto den som {}, ville enhver kilde
    # som aldri har tenkt på spørsmålet automatisk påstått at den henter
    # alt, og den påstanden har ingen gått god for. En kilde må si det
    # selv: `self.utvalg = {}` i hent_uke(), slik lusetall gjør.
    #
    # `{}` og None er begge usanne i Python og lett å blande. Spør med
    # utvalg.er_ukjent() og utvalg.henter_alt(), ikke med `if not`.
    utvalg: dict | None = None

    # Feltet som bærer entitetens EGEN startdato i verden — datoen den ble
    # til, ikke datoen vi først så den. For Enhetsregisteret er det
    # `registreringsdato`.
    #
    # Den uka utvalget utvides er dette det eneste som skiller «selskapet
    # ble stiftet i går» fra «vi begynte å lete der i går». Uten det ville
    # en ekte nyregistrering blitt merket utvalgsutvidelse sammen med de
    # 908 gamle, og en ekte hendelse forsvunnet stille — nøyaktig
    # feilmodusen merkingen finnes for å unngå.
    #
    # Kilden oppgir navnet fordi navnet er kildens. `core/` skal ikke
    # kjenne Brregs ordforråd. Tom streng: kilden kan ikke etterprøves,
    # og da merkes alle nye entiteter i en utvidelsesuke.
    startdatofelt: str = ""

    # Hvor ofte kilden skal hentes, i dager. Ikke alle kilder beveger seg
    # like fort, og noen straffes for å hentes for sjelden:
    #
    #   7   registre der endringer er forvaltningsvedtak (Brreg, Fiskeridir)
    #   1-2 kilder der oppføringer FORSVINNER (stillingsannonser). Henter du
    #       ukentlig, finnes ikke annonsen som ble lagt ut tirsdag og fylt
    #       fredag. Det er tapt historikk, ikke tapt ferskhet.
    #   30  årlige kilder (regnskap) — de kommer inn løpende, men ingenting
    #       skjer på ukesskala.
    #
    # Kjøringen hopper over kilder som er hentet nylig nok. Det er også det
    # som gjør at du kan aktivere en ny kilde midt i uka uten å skrive
    # dagens snapshot for de andre på nytt.
    min_dager_mellom: int = 7

    def fetch(self, kjoredato: str) -> Any:
        """Hent rådata for kjøringen som skjer `kjoredato`.

        En kilde LESER ALDRI KLOKKA. Trenger den å vite hvilket tidsrom
        den skal hente, får den datoen inn — den slår den ikke opp selv.

        Dette er ikke en stilpreferanse. Tre feil i dette prosjektet har
        hatt samme rotårsak, og alle tre kom av at et tidspunkt ble slått
        opp på nytt et sted til:

          F4   frekvensvakten leste filnavnsdato der den skulle lest
               innsamlingstidspunkt
          F6   run.py daterte snapshotet etter kjøredagen, mens kilden
               stemplet radene med uka de gjaldt for
          F7   fetch() slo opp klokka selv, mens gjelder_for() fikk
               kjøredatoen inn — to klokkeoppslag som kunne svare ulikt
               rundt midnatt, og da får fila navn etter én uke og innhold
               fra en annen

        Med datoen som argument finnes det ett tidspunkt per kjøring, og
        det er umulig for to deler av samme kjøring å være uenige om
        hvilken dag det er.
        """
        raise NotImplementedError

    def parse(self, raw: Any, observed_at: str) -> Iterable[Observation]:
        """Gjør rådata om til observasjoner."""
        raise NotImplementedError

    def collect(self, observed_at: str) -> list[Observation]:
        """Hent og tolk i ett. `observed_at` er både kjøredato og
        gyldighetsdato her — den brukes av tester og av kilder uten
        etterslep. Kjernen går veien om run_all(), som holder de to fra
        hverandre."""
        return list(self.parse(self.fetch(observed_at), observed_at))

    def gjelder_for(self, kjoredato: str) -> str:
        """Hvilken dato snapshotet GJELDER for når vi henter `kjoredato`.

        `observed_at` handler om verden, kjøredatoen om oss. For de fleste
        kilder er de samme dag: spør du Brreg på mandag, får du mandagens
        register. Standardsvaret er derfor kjøredatoen selv, og en kilde
        uten etterslep skal ikke trenge å vite at denne metoden finnes.

        En kilde med etterslep er ikke i den situasjonen. Lusetall henter
        uke N-4 fordi ferskere uker er ufullstendige, og da GJELDER
        snapshotet den uka — ikke dagen vi spurte. Uten dette skillet
        daterer den ukentlige jobben hver fil fire uker for sent, mens
        backfillen daterer den samme uka riktig, og serien får en skjøt
        midt i seg der de to møtes.

        Dette er den samme rotårsaken som frekvensvakten gikk på (F4):
        et tidspunkt som handler om oss brukt som om det handlet om
        verden. Beslutningen fra 18.08 slo fast at observed_at er
        gyldighetsdato — dette er den regelen gjort tilgjengelig for
        innsamlingsløypa, ikke bare for kildens egen parse().
        """
        return kjoredato
