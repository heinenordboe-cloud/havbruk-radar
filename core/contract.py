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

    # Da KILDEN utga påstanden. Tom streng betyr «kilden sa ingenting».
    #
    # Et tidspunkt kan tilhøre tre parter, og de tre er ikke det samme:
    #
    #     observed_at    VERDEN   — hvilket tidspunkt raden handler om
    #     fetched_at     OSS      — når vi spurte
    #     published_at   KILDEN   — når kilden utga dette svaret
    #
    # De to siste faller sammen NESTEN, og bare når vi henter ferskt. En
    # kropp hentet fra et arkiv river dem fra hverandre: Wayback-kopien av
    # biomassefila ble hentet av oss 26.08.2026 og utgitt av
    # Fiskeridirektoratet 20.07.2024. To år.
    #
    # Uten feltet kan en slik kropp ikke skrives inn i det hele tatt. Enten
    # får den ELDSTE påstanden det NYESTE hentetidspunktet — og
    # revisjonsaksen leser baklengs — eller så finner vi på en proveniens.
    #
    # STANDARDEN ER IKKE `fetched_at`, og det er ikke en forglemmelse. En
    # kilde som ikke vet når noe ble utgitt skal si at den ikke vet. Sto
    # `fetched_at` her, ville hver eneste kilde automatisk PÅSTÅTT en
    # utgivelsesdato ingen har gått god for — og påstanden ville vært
    # usann i nøyaktig det tilfellet feltet finnes for. Samme skille som
    # `utvalg` gjør mellom «vet ikke» og «vet»: tom streng er ikke en
    # verdi, den er fraværet av en.
    #
    # Stemples av kjernen som de tre over. Kilden oppgir den i
    # `Source.published_at`, og bare der den har LEST den — se
    # `sources/biomasse.py`, som tar den fra `Last-Modified`.
    published_at: str = ""

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

    # Hvilke (entity_id, field)-par KROPPEN UTTALER SEG OM — kanonisk
    # JSON fra core/domene.py. Fire tilstander, se den modulen:
    #
    #   ""        ukjent          fravær av en verdi leses som FJERNING
    #   "*"       uttømmende      fravær leses som FJERNING
    #   "{}"      = det emitterte fravær leses som TAUSHET
    #   [[e,f]…]  + disse parene  taushet, unntatt disse
    #
    # `utvalg` sier hva vi BA OM. Dette sier hva kilden SVARTE OM, og de
    # er ikke det samme. Uten skillet kan `diff` ikke se forskjell på at
    # en kilde TIDDE om en celle og at den FJERNET verdien — begge blir
    # `new_value = null`, og den raden leses som en tilbaketrekking.
    #
    # Målt 15.09.2026 over hele changeloggen: 36 av 1873 revisjonsrader
    # var taushet lest som tilbaketrekking, og 34 av dem hos
    # trafikklysvedtak, der ingen forskrift noensinne har trukket tilbake
    # en farge. § 4-tabellen har bare tre rader.
    #
    # Bare DIFFERANSEN mot det emitterte lagres. Snapshotet bærer alt hva
    # som kom ut; det eneste som mangler er hva kroppen uttalte seg om
    # uten å gi en verdi. En full parliste på hver rad ble målt til 24x
    # filstørrelse hos ekspertgruppen og forkastet.
    #
    # Stemples av kjernen som de fire over. Kilden oppgir den i
    # `Source.domene`, og bare der den har LEST hva kroppen omtaler.
    domene: str = ""

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

    # Setningene lisensgiveren krever, ORDRETT, der kildens tall vises.
    #
    # ## Hvorfor den bor på kilden og ikke hos den som publiserer
    #
    # Vilkåret er en egenskap ved kilden på linje med endepunktet og
    # feltvalget. Lå lista hos publiseringsleddet, ville en ny kilde
    # kunne legges til uten at attribusjonen fulgte med — og den
    # manglende setningen ville vist seg først den dagen noen publiserte,
    # altså for sent. Samme form som `utvalg`: verdien settes der den er
    # kjent, ikke der den brukes.
    #
    # Dette er den femte utgaven av samme resonnement i denne fila.
    # `utvalg`, `published_at`, `domene` og `startdatofelt` ligger alle på
    # kilden fordi kilden er den eneste som VET, og fordi et andre sted å
    # slå det opp er et sted de to kan svare ulikt (F6, F7, F8).
    #
    # ## TO tilstander, og den tomme tuppelen er FORBUDT
    #
    #   None                 UBELAGT — kilden sier ingenting
    #   ("setning", ...)     dette kreves, ordrett
    #   ()                   ugyldig, kaster
    #
    # `utvalg` har tre tilstander fordi «vi ba om alt» er en meningsfull
    # påstand. Her er den tredje ikke sluppet inn, og det er et bevisst
    # valg av hvilken vei feilen skal peke: `()` og `None` er begge usanne
    # i Python, og en kilde som ved et uhell fikk `()` ville publisert
    # uten attribusjon i stillhet. `None` stopper publiseringen.
    #
    # En kilde som faktisk ikke krever navngivelse — CC0, offentlig
    # eiendom — finnes ikke i repoet i dag. Den dagen den kommer, er den
    # tredje tilstanden en kontraktsendring med et beslutningsnotat, ikke
    # en tom tuppel noen skrev. `()` er reservert for det, ikke ledig.
    #
    # ## UBELAGT er ikke det samme som fritt
    #
    # `None` betyr at vilkåret er lett etter og ikke funnet, eller at
    # ingen har lett. Begge deler er «vi vet ikke». En UBELAGT kilde kan
    # brukes i analyse og dokumentasjon; den skal ikke bære en publisert
    # visning. Se docs/LISENSKJEDE.md og
    # docs/beslutninger/2026-09-12-lisenskjeden.md.
    #
    # `core/` håndhever ikke den regelen — det gjør den som publiserer
    # (`nettsted.py`). Kjernen sier hva som er erklært; hva det får lov
    # til å bety er publiseringsleddets sak, fordi grensen går ulikt for
    # analyse og for publisering.
    attribusjon: tuple[str, ...] | None = None

    # Andre kildenavn denne kilden SKRIVER rader under.
    #
    # `eierskap` skriver både `eierskap` (ukentlig, hvem eier hva nå) og
    # `eierskap_historikk` (backfill, journalførte overføringer). Det er
    # to serier med helt ulike felter og kadens — se `HISTORIKK_KILDE` i
    # sources/eierskap.py for hvorfor de ikke er én.
    #
    # Uten denne er navnerommet i `data/raw/` STØRRE enn navnerommet
    # `registry.discover()` kjenner, og et oppslag fra kildenavn til
    # kilde er da ikke totalt. Det merkes ikke før noen slår opp
    # `eierskap_historikk` og får ingenting — og for `attribusjon` ville
    # «ingenting» betydd UBELAGT, altså en side som nekter å bygge av
    # feil grunn.
    #
    # Aliasene arver kildens attribusjon. Samme lisensgiver, samme
    # vilkår: det er den samme tjenesten som svarer.
    skriver_ogsaa: tuple[str, ...] = ()

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

    # Da KILDEN utga svaret `fetch()` nettopp hentet. ISO-8601 i UTC, eller
    # tom streng for «vet ikke». Se Observation.published_at for hvorfor
    # standarden ikke er hentetidspunktet.
    #
    # SETTES av kilden i det kallet som henter, leses av kjernen etterpå —
    # samme mekanikk og samme begrunnelse som `utvalg`. Sto den i en egen
    # metode, ville det vært et ANDRE oppslag som kan svare noe annet enn
    # det kallet faktisk fikk (F6, F7, F8).
    #
    # BARE der kilden har LEST den. Å utlede den av kjøredatoen, av en
    # publiseringsplan eller av «fila oppdateres den 20.» er å gjette på
    # en tredjeparts vegne. `sources/biomasse.py` tar den fra
    # `Last-Modified`-headeren, som tjenesten selv setter — og fra
    # `X-Archive-Orig-Last-Modified` når kroppen kommer fra Wayback, som
    # er den SAMME headeren bevart.
    #
    # To tilstander, ikke tre som i `utvalg`: enten vet vi når kilden utga
    # dette, eller så vet vi det ikke. Det finnes ikke noe «kilden utgir
    # ikke» — et svar er utgitt i det øyeblikket det gis; spørsmålet er
    # bare om noen skrev ned når.
    published_at: str = ""

    # Hvilke (entity_id, field)-par KROPPEN UTTALER SEG OM.
    #
    # SETTES av uttrekket i det kallet som leser kroppen, leses av kjernen
    # etterpå — samme mekanikk og samme begrunnelse som `utvalg` og
    # `published_at`. Sto den i en egen metode, ville det vært et ANDRE
    # oppslag som kan svare noe annet enn det kallet faktisk fikk.
    #
    # FIRE tilstander (se core/domene.py):
    #
    #   None                     ukjent — kilden sier ingenting
    #   domene.UTTOMMENDE        kroppen dekker hele nøkkelrommet
    #   {("3", "farge"), ...}    kroppen uttaler seg om NØYAKTIG disse
    #
    # De to siste er de eneste som sier noe. Standarden er None, ikke
    # UTTOMMENDE: en kilde som aldri har tenkt på spørsmålet skal ikke
    # automatisk påstå at kroppen dekker alt.
    #
    # ## Den ERKLÆRES, den utledes ikke
    #
    # Settet skal si hva kroppen UTTALER SEG OM, ikke hva `parse()`
    # returnerte. For hver kilde i repoet i dag er de to like, og et
    # uttrekk som returnerte «det jeg emitterte» ville bestått hver test.
    # Det er nøyaktig formen 1b-2 navngir.
    #
    # Den dagen en forskrift skriver «Produksjonsområde 9: ingen
    # justering», har kroppen uttalt seg om PO9 uten å gi en farge. Et
    # utledet domene ville kalt det taushet og undertrykt en ekte
    # fjerning; et erklært domene sier at PO9 ble omtalt, og raden
    # overlever. `domene.serialiser()` kaster hvis et emittert par
    # mangler i erklæringen — men den kan ikke oppdage det motsatte, og
    # derfor står regelen her.
    domene: object = None

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

    # HVA DATOEN I FILNAVNET ER — verden eller oss.
    #
    #   "verden"    `observed_at` er tidsrommet raden GJELDER FOR. En ny
    #               dato er et nytt tidsrom, og de gamle står ved lag.
    #               lusetall (uka), biomasse (måneden), eierskap_historikk
    #               (journalføringsåret), trafikklysvedtak (vedtaksåret).
    #   "henting"   `observed_at` er dagen VI spurte. En ny dato erstatter
    #               den forrige som svar på «hva gjelder nå».
    #               enhetsregisteret, akvakultur, eierskap, biomasselag.
    #   ""          ikke erklært. Kjernen tvinger ikke en tolkning; se
    #               under for hva den som leser skal gjøre med den.
    #
    # Dette er 1b-7 gjort til en egenskap ved kilden: `observed_at`
    # handler om VERDEN, `fetched_at` om OSS — og hvilken av de to som
    # BESTEMMER PARTISJONEN er ikke noe kjernen kan slutte seg til.
    #
    # ## Hvorfor den bor på kilden
    #
    # Sjette utgave av samme resonnement i denne fila. `utvalg`,
    # `published_at`, `domene`, `startdatofelt` og `attribusjon` ligger
    # alle her fordi kilden er den eneste som VET, og fordi et andre sted
    # å slå det opp er et sted de to kan svare ulikt (F6, F7, F8). En
    # liste i `core/` over hvilke kilder som er hva, ville i tillegg
    # brutt regel 1: en ny revisjonskilde ville krevd en endring i
    # kjernen for å bli lest riktig.
    #
    # ## Hva den brukes til, og hvorfor det ikke er en detalj
    #
    # `publiseringsvakt.hviteliste()` leser ALLE datoer for en
    # "verden"-kilde og NYESTE for en "henting"-kilde. Grunnen er at en
    # visning av en "verden"-kilde med rette viser hele serien —
    # lokalitetssiden viser 764 uker lusetall og 21 årganger overføringer
    # — mens et navn fra forrige ukes `enhetsregisteret` er et navn som
    # ikke gjelder lenger, og som en visning ikke skal hente fra.
    #
    # ## PER NAVN, fordi én klasse kan skrive to serier
    #
    # `eierskap` skriver ukentlig under sitt eget navn ("henting") og
    # backfiller under `eierskap_historikk` ("verden") — se
    # `skriver_ogsaa`. Én skalar kan derfor ikke dekke begge, og
    # erklæringen tar også en dict:
    #
    #     partisjonering = {"eierskap": "henting",
    #                       "eierskap_historikk": "verden"}
    #
    # Er den en dict, må HVERT navn kilden skriver under stå der.
    # `erklaert_partisjonering()` kaster på et manglende navn framfor å
    # falle tilbake på en standard: en glemt alias er nettopp den feilen
    # som ellers blir stille.
    #
    # ## En FEIL erklæring, og hvilken vei den peker
    #
    # Erklærer en "verden"-kilde seg som "henting", blir hvitelista for
    # liten, og porten melder hvert navn i historikken som `ukjent_navn`.
    # Det er høyt og irriterende, og det er den ufarlige retningen.
    #
    # Erklærer en "henting"-kilde seg som "verden", blir hvitelista for
    # stor: et navn som forsvant ut av registeret for et år siden er
    # plutselig gjort rede for, og en visning som viser det passerer
    # porten. Det er den stille retningen, og derfor etterprøver porten
    # erklæringen mot dataene — for en "henting"-kilde er `observed_at`
    # lik datoen i `fetched_at` i HVERT snapshot (målt 18.09.2026: 0
    # dagers avvik i alle fire), og for en "verden"-kilde er den det
    # ikke. Se `publiseringsvakt.grunnlagsfunn()`.
    partisjonering: "str | dict[str, str]" = ""

    def fjern_egne_personer(self, frame: Any) -> Any:
        """Rader KILDEN vet peker på en person, men som kjernen ikke ser.

        `persondata.fjern_personformer()` spør om `organisasjonsform` og
        `institusjonell_sektorkode` — registerets egne klassifiseringer.
        Den er døra, og den er nok for enhver kilde som skriver de to
        feltene.

        Noen kilder skriver dem ikke. MÅLT 18.09.2026 på
        `eierskap_historikk`: 21 årganger, 36 360 rader, **0 rader med
        `organisasjonsform` og 0 med `institusjonell_sektorkode`** —
        formen står i `mottaker_type`, i pub-aquas vokabular. Døra fjerner
        derfor 0 rader fra den kilden, og 4 overføringer som dagens grense
        utelukker blir stående.

        Standarden her er å ikke røre ramma. Det er riktig for elleve av
        tolv kilder, og en standard som gjorde noe annet ville vært en
        påstand om data kjernen ikke har sett.

        ## Hvorfor en HOOK og ikke en liste i `core/`

        16.09-notatet avviste å lukke dette med at «`core/` kjenner en
        kildes vokabular — to lister som skal si det samme, altså formen
        F6 og F7 hadde». Innvendingen gjelder en LISTE, ikke en
        delegering: her finnes oversettelsen på ett sted,
        `sources/eierskap.FORM_KART`, og kjernen spør den som eier den.
        Kjernen lærer ingen koder.

        ## Den er et TILLEGG, aldri en erstatning

        Den kalles i tillegg til døra og kan bare fjerne mer. En kilde
        som overstyrer denne til å returnere flere rader enn den fikk,
        har ikke filtrert — den har lagt til, og `publiseringsvakt`
        feller det.
        """
        return frame

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


def erklaert_attribusjon(kilde: "Source") -> tuple[str, ...] | None:
    """Kildens attribusjon, validert. `None` = UBELAGT.

    Validerer framfor å stole på deklarasjonen, av samme grunn som
    `utvalg.normaliser()` gjør det: feltet settes av en kildeforfatter
    som skriver én fil og aldri leser denne, og en feilform her kommer
    ikke til syne før noen publiserer.

    De tre feilformene som stoppes:

      * `()` — se `Source.attribusjon`. Den tomme tuppelen er reservert
        for en framtidig CC0-tilstand, ikke ledig som «ingen krav».
      * en naken streng. `attribusjon = "Kilde: X"` er den nærliggende
        skrivefeilen, og den ville iterert som enkelttegn — en
        bunntekst med 13 punkter på én bokstav hver.
      * en tom setning i lista. En setning som ikke sier noe er ikke en
        attribusjon, og den ville stått som et tomt punktmerke.
    """
    erklaert = getattr(kilde, "attribusjon", None)
    if erklaert is None:
        return None

    if isinstance(erklaert, (str, bytes)):
        raise ValueError(
            f"{kilde.name}: attribusjon er en streng, ikke en sekvens av "
            f"setninger. Skriv ('{erklaert}',) med komma — uten den ville "
            f"lista iterert som enkelttegn.")

    setninger = tuple(str(s) for s in erklaert)
    if not setninger:
        raise ValueError(
            f"{kilde.name}: attribusjon er tom. Tom betyr ikke «ingen krav» "
            f"— det skrives som None (UBELAGT), og «krever ingen "
            f"navngivelse» er en kontraktsendring med et beslutningsnotat. "
            f"Se Source.attribusjon.")
    if any(not s.strip() for s in setninger):
        raise ValueError(
            f"{kilde.name}: attribusjon inneholder en tom setning.")
    return setninger


def attribusjon_per_kilde(kilder: "Iterable[Source]") -> dict[str, tuple[str, ...] | None]:
    """{kildenavn: setninger eller None} for alle navn kildene SKRIVER under.

    Indeksen er på NAVN og ikke på klasse, fordi det er navnet som står i
    `data/raw/<kilde>/` og i changeloggens `source`-kolonne — det er den
    strengen den som publiserer har i hånda.

    `skriver_ogsaa` er med i indeksen, og aliasene arver kildens
    attribusjon. Uten det ville `eierskap_historikk` slått opp til
    ingenting, og ingenting leses som UBELAGT.

    Et navn som kolliderer er en feil og ikke en sammenslåing: to kilder
    som skriver under samme navn skriver i den samme mappa, og da er det
    ikke attribusjonen som er problemet.
    """
    ut: dict[str, tuple[str, ...] | None] = {}
    for kilde in kilder:
        setninger = erklaert_attribusjon(kilde)
        for navn in (kilde.name, *getattr(kilde, "skriver_ogsaa", ())):
            if navn in ut:
                raise ValueError(
                    f"to kilder skriver under navnet {navn!r}. Navnet er "
                    f"mappa i data/raw/ — de ville skrevet oppå hverandre.")
            ut[str(navn)] = setninger
    return ut


# De to lovlige verdiene for `Source.partisjonering`. Tom streng er en
# tredje TILSTAND — ikke erklært — og ikke en verdi: den står ikke her,
# slik at en kilde ikke kan erklære «ikke erklært».
PARTISJONERINGER = ("verden", "henting")


def navnene_kilden_skriver(kilde: "Source") -> tuple[str, ...]:
    """Hvert navn kilden skriver rader under. `name` først.

    Ett sted, fordi tre funksjoner trenger den samme lista og en fjerde
    variant av `(kilde.name, *skriver_ogsaa)` er et sted den kan bli
    uenig med de andre.
    """
    return (str(kilde.name), *(str(n) for n in getattr(kilde, "skriver_ogsaa", ())))


def erklaert_partisjonering(kilde: "Source") -> dict[str, str]:
    """{navn: "verden" | "henting" | ""} for hvert navn kilden skriver.

    Validerer framfor å stole på deklarasjonen, av samme grunn som
    `erklaert_attribusjon()` gjør det: feltet settes av en kildeforfatter
    som skriver én fil og aldri leser denne.

    De fire feilformene som stoppes:

      * en ukjent verdi. `"ukentlig"` er den nærliggende skrivefeilen, og
        den ville lest som «ikke erklært» og dermed gitt den strengeste
        tolkningen i stillhet.
      * en dict som mangler et navn kilden skriver under. Den glemte
        aliasen er nettopp feilen denne formen finnes for å fange —
        `eierskap_historikk` uten erklæring leses som nyeste dato alene,
        og det er 20 av 21 årganger usett.
      * en dict med et navn kilden IKKE skriver under. Da er erklæringen
        om en annen kilde, og den ville sett riktig ut for alltid.
      * noe som verken er streng eller dict.
    """
    erklaert = getattr(kilde, "partisjonering", "")
    navn = navnene_kilden_skriver(kilde)

    if isinstance(erklaert, str):
        if erklaert and erklaert not in PARTISJONERINGER:
            raise ValueError(
                f"{kilde.name}: partisjonering {erklaert!r} er ikke en av "
                f"{PARTISJONERINGER}. En ukjent verdi ville lest som «ikke "
                f"erklært», altså nyeste dato alene, uten at noen så det.")
        return {n: erklaert for n in navn}

    if not isinstance(erklaert, dict):
        raise ValueError(
            f"{kilde.name}: partisjonering er {type(erklaert).__name__}, "
            f"og skal være en streng eller en dict per navn. Se "
            f"Source.partisjonering.")

    ut: dict[str, str] = {}
    for n in navn:
        if n not in erklaert:
            raise ValueError(
                f"{kilde.name}: partisjonering er en dict, og da må hvert "
                f"navn kilden skriver under stå der. {n!r} mangler — og en "
                f"glemt serie leses som nyeste dato alene.")
        verdi = str(erklaert[n])
        if verdi not in PARTISJONERINGER:
            raise ValueError(
                f"{kilde.name}: partisjonering[{n!r}] = {verdi!r} er ikke en "
                f"av {PARTISJONERINGER}.")
        ut[n] = verdi

    ukjente = set(erklaert) - set(navn)
    if ukjente:
        raise ValueError(
            f"{kilde.name}: partisjonering nevner {sorted(ukjente)}, som "
            f"kilden ikke skriver under. En erklæring om en annen kilde "
            f"ville sett riktig ut for alltid.")
    return ut


def partisjonering_per_kilde(kilder: "Iterable[Source]") -> dict[str, str]:
    """{kildenavn: "verden" | "henting" | ""} for alle navn kildene skriver.

    Indeksen er på NAVN og ikke på klasse, av samme grunn som i
    `attribusjon_per_kilde()`: navnet er mappa i `data/raw/`, og det er
    strengen den som leser har i hånda.
    """
    ut: dict[str, str] = {}
    for kilde in kilder:
        for navn, verdi in erklaert_partisjonering(kilde).items():
            if navn in ut:
                raise ValueError(
                    f"to kilder skriver under navnet {navn!r}. Navnet er "
                    f"mappa i data/raw/ — de ville skrevet oppå hverandre.")
            ut[navn] = verdi
    return ut


def kilder_per_navn(kilder: "Iterable[Source]") -> dict[str, "Source"]:
    """{kildenavn: kilden som skriver under navnet}.

    Brukes av den som leser til å spørre kilden selv —
    `fjern_egne_personer()` er den ene grunnen i dag. Alias peker på
    samme instans som kilden sin: det er én kilde med to serier.
    """
    ut: dict[str, "Source"] = {}
    for kilde in kilder:
        for navn in navnene_kilden_skriver(kilde):
            if navn in ut:
                raise ValueError(
                    f"to kilder skriver under navnet {navn!r}. Navnet er "
                    f"mappa i data/raw/ — de ville skrevet oppå hverandre.")
            ut[navn] = kilde
    return ut
