"""Hvilke enheter er en fysisk person forkledd som et foretak.

Dette er en juridisk vurdering, ikke en innstilling. Den ligger i kode og
ikke i `config.yml` av samme grunn som feltvalget gjør det: hvem vi nekter
å lagre data om skal ikke kunne endres ved et uhell i en YAML-fil.

## Grensa går ved SEKTOREN, ikke ved formen alene

Fra 16.09.2026 er grensa **SSBs institusjonelle sektor**: 8200
husholdninger og 2300 personlige foretak. Alle organisasjonsformer som
registeret plasserer der, filtreres bort.

    8200   husholdninger        ENK                    personen selv
    2300   personlige foretak   DA, ANS, PRE           deltakerne
    2100   private AS           AS, ASA, SA            beholdes

Fram til 16.09 gikk grensa ved formen `ENK` alene, med den begrunnelsen
at et ansvarlig selskap er et eget rettssubjekt med eget
organisasjonsnummer og egen partsevne, mens et enkeltpersonforetak ER
innehaveren. Det resonnementet er fortsatt riktig om RETTSSUBJEKTET. Det
avgjorde bare ikke spørsmålet vi faktisk stiller, som er om RADEN vi
lagrer peker på et navngitt menneske.

For et DA med to deltakere er feltene vi lagrer — navn, kommune,
postnummer, næringskode, registreringsår, `konkurs`,
`under_tvangsavvikling` — det samme settet som gjorde de 34 ENK-ene til
persondata. Deltakerne hefter personlig, og de står i rolleregisteret
denne pipelinen aldri spør etter; at vi ikke spør, gjør dem ikke
uidentifiserbare.

Hvorfor sektoren og ikke en lengre liste over former: en liste er en
oppregning noen må huske å utvide, en sektor er et FELT registeret selv
fyller ut. Kommer det en form vi aldri har sett, sier sektoren hva den
er — se `er_personsektor()`, som er det andre av to uavhengige ledd.

## ALLE 64, ikke bare de 46 med personnavn

Det åpne spørsmålet fra 22.08 kunne vært avgjort snevrere: filtrer de
DA/ANS-ene som HAR et personnavn («Hansen og Olsen DA»), behold resten.
Den veien er stengt, og den er stengt med et tall.

Målt 15.09.2026 på enhetsregisteret-snapshotet: en navneprøve — to eller
tre ord, ingen bedriftsord — treffer **1278 av 1807** entiteter, og
**1196 av dem er AS**. Brreg skriver navn i VERSALER (1795 av 1807), så
«NORDLAKS OPPDRETT AS» og «HANSEN OG OLSEN DA» har nøyaktig samme form.

Navneprøven er altså ikke bare upresis, den er verdiløs alene — og en
regel som avhenger av hvordan et navn SER UT, er ikke en regel. Det er
samme feil som ni-siffer-prøven fra 16.08: en syntaktisk prøve der
spørsmålet er semantisk. Derfor filtreres alle 64 DA/ANS/PRE, ikke de 46
som tilfeldigvis også ser slik ut.

Filteret her rører aldri `navn`. Det spør om to felter, og begge er
registerets egne klassifiseringer: `organisasjonsform` og
`institusjonell_sektorkode`.

## Dataene som ble målt

Egne snapshots, lest med `pl.read_parquet` for å se dem ufiltrert:

    2026-08-17 (før kildefilteret)    ENK 34, alle sektor 8200
                                      DA 27 + ANS 21, alle sektor 2300
    2026-09-14 (etter)                ENK 0
                                      DA 32 + ANS 31 + PRE 1, alle 2300

Ingen enhet i noe snapshot har sektor 2300 eller 8200 med en annen form
enn de fire. Formlista og sektorlista peker altså på nøyaktig samme
enheter i dag — og det er hele poenget med å ha begge: den dagen de
peker ulikt, er det fordi registeret har fått noe vi ikke kjente.

`KBO` (konkursbo, 31 stk.) og `NUF` (21) mangler sektorkode helt. De
fanges ikke av sektorleddet, og de står ikke i formlista. Et konkursbo
etter et enkeltpersonforetak er et kjent, åpent hull — se
docs/beslutninger/2026-09-16-grensa-gaar-ved-sektor-2300.md.
"""

import polars as pl

# Feltet en kilde oppgir organisasjonsformen i. Vakten i snapshot.write()
# ser bare det den kan lese, og dette er navnet den leter etter.
FORM_FELT = "organisasjonsform"

# Feltet en kilde oppgir SSB-sektoren i. Andre ledd i samme prøve, og
# det eneste som kan fange en form vi ikke har sett før.
SEKTOR_FELT = "institusjonell_sektorkode"

# SSBs institusjonelle sektorkoder der enheten er en fysisk person eller
# en personlig sammenslutning. Dette ER grensa; formlista under er de
# kodene vi har MÅLT at havner her.
PERSONSEKTORER = frozenset({"8200", "2300"})

# Brreg-koder som ligger i en personsektor. Målt mot egne snapshots og
# mot Brregs enhetsoppslag, ikke lest ut av dokumentasjon:
#
#     ENK   enkeltpersonforetak   8200   foretaket ER innehaveren
#     DA    delt ansvar           2300   deltakerne hefter personlig
#     ANS   ansvarlig selskap     2300   samme
#     PRE   partrederi            2300   samme
#
# Lista kan bare VOKSE. En form som er filtrert bort i et snapshot og
# senere tas ut av lista, ville gjort et gammelt snapshot rikere ved
# lesing enn det var forrige gang det ble lest — og da er historikken
# ikke lenger etterrettelig. Se docs/FORSLAG-personformer-versjonering.md.
PERSONFORMER = frozenset({"ENK", "DA", "ANS", "PRE"})


def er_personform(kode: object) -> bool:
    """Sant hvis organisasjonsformkoden betyr «denne enheten er et eller
    flere navngitte mennesker». Tåler None og andre typer: en enhet uten
    oppgitt form er ikke en kjent personform, og skal ikke stoppes på
    det grunnlaget — den kan stoppes av sektoren i stedet."""
    return isinstance(kode, str) and kode.strip().upper() in PERSONFORMER


def er_personsektor(kode: object) -> bool:
    """Sant hvis SSB-sektoren er en personsektor.

    Det UAVHENGIGE leddet. `er_personform()` kan bare kjenne igjen det
    noen har skrevet inn i lista; denne spør registeret selv. Kommer det
    en form vi aldri har sett, og plasserer Brreg den i 2300, stoppes
    den her uten at noen har måttet huske noe.

    Motsatt vei mangler sektoren for `KBO` og `NUF`, og der er formlista
    det eneste som virker. Derfor to ledd og ikke ett.

    Tåler tall like godt som streng: sektorkoden er sifre, og en kilde
    som leverer den som `int` skal ikke slippe forbi på det.
    """
    if kode is None or isinstance(kode, bool):
        return False
    return str(kode).strip() in PERSONSEKTORER


def _personene(frame: pl.DataFrame) -> pl.DataFrame:
    """Radene som PEKER UT en person — form- eller sektorraden.

    Ett sted, brukt av både `fjern_personformer()` og `tell_personer()`.
    To uttrykk som skal si det samme er formen F6 og F7 hadde, og her
    ville de gitt en teller som sier noe annet enn filteret gjorde.
    """
    verdi = pl.col("value").str.strip_chars()
    return frame.filter(
        ((pl.col("field") == FORM_FELT)
         & verdi.str.to_uppercase().is_in(sorted(PERSONFORMER)))
        | ((pl.col("field") == SEKTOR_FELT)
           & verdi.is_in(sorted(PERSONSEKTORER)))
    )


def tell_personer(frame: pl.DataFrame) -> dict[str, int]:
    """{organisasjonsform: antall entiteter} som `fjern_personformer()`
    ville tatt ut av denne ramma.

    Filtrering er stille av natur — en entitet som forsvinner ved lesing
    etterlater seg ingen rad å savne — og uten et tall kan ingen skille
    «filteret tok 64» fra «det var ingen der». Samme begrunnelse som
    telleren i `sources/enhetsregisteret.py`, og samme form: ENTITETER,
    ikke rader.

    AGGREGAT, aldri identiteter. Nøkkelen er organisasjonsformen og
    verdien er et antall. En entitet som bare sektorleddet fanget — altså
    en form vi ikke kjenner — føres under formkoden sin, og under
    `(uten form)` om ramma ikke har en formrad for den. Det er da den
    eneste måten å se at det finnes en femte personform på.

    ## HVA ET SVAR PÅ 0 BETYR, OG HVA DET IKKE BETYR

    Den teller det `fjern_personformer()` ville tatt, og ikke noe mer.
    Begge går gjennom `_personene()` nettopp for at telleren ikke skal
    kunne si noe annet enn filteret gjorde — og det er grunnen til at
    denne funksjonen IKKE utvides til å spørre kilden.

    Følgen skal sies rett ut, fordi den er målt: **0 her betyr «døra tar
    ingen», ikke «det er ingen person her».** MÅLT 24.09.2026 på
    `eierskap_historikk`: 36 360 rader, 0 med `organisasjonsform` og 0 med
    `institusjonell_sektorkode`, altså 0 fra denne telleren — mens
    `Source.fjern_egne_personer()` fjerner 4 entiteter, fordi formen står
    i `mottaker_type`. Et svar på 0 som leses som «ingen der» er den
    formen CLAUDE.md 1b-2 handler om.

    `persondata` kan ikke lukke det selv uten å lære kildenes vokabular,
    og det er nøyaktig det `Source.fjern_egne_personer()` finnes for å
    unngå. Aggregatet et MENNESKE leser, teller derfor begge ledd:
    `snapshot.filtrert_bort()` legger hookens entiteter til under
    `(kildens eget tillegg)`. Spørsmålet «hvor mange ble holdt ute» stilles
    der, ikke her.
    """
    if frame.is_empty() or not {"entity_id", "field", "value"} <= set(frame.columns):
        return {}

    personer = set(_personene(frame)["entity_id"].to_list())
    if not personer:
        return {}

    former = dict(
        frame.filter((pl.col("field") == FORM_FELT)
                     & pl.col("entity_id").is_in(sorted(personer)))
        .select(["entity_id", "value"]).iter_rows()
    )

    ut: dict[str, int] = {}
    for eid in personer:
        kode = (former.get(eid) or "").strip().upper() or "(uten form)"
        ut[kode] = ut.get(kode, 0) + 1
    return dict(sorted(ut.items()))


def person_ider(frame: pl.DataFrame) -> list[str]:
    """`entity_id` til hver entitet ramma peker ut som en fysisk person.

    Samme prøve som `fjern_personformer()`, men svaret er LISTA framfor
    den filtrerte ramma. Changeloggens lesedør trenger id-ene: den kan
    ikke stille spørsmålet selv, fordi en changelog-rad har `old_value`
    og `new_value` der et øyeblikksbilde har `value`.
    """
    if frame.is_empty() or not {"entity_id", "field", "value"} <= set(frame.columns):
        return []
    return [str(e) for e in _personene(frame)["entity_id"].unique().to_list()]


def fjern_personformer(frame: pl.DataFrame) -> pl.DataFrame:
    """Alle rader om entiteter som er fysiske personer, ut av en ramme.

    Navnet er beholdt fra da lista var `{"ENK"}` og formen var eneste
    prøve. Funksjonen spør nå om BEGGE feltene — se `er_personsektor()`
    — og det er et bevisst valg å ikke døpe den om: den er nevnt ved navn
    i tre beslutningsnotater og i kjøringsloggen, og en omdøping ville
    gjort de referansene stumme uten å gjøre noe klarere.

    Dette er leseveien. Kilden filtrerer ved henting, men snapshotene som
    allerede ligger i datarepoet inneholder både de 34 ENK-ene og de 64
    DA/ANS/PRE-ene, og de filene er append-only — se
    `docs/beslutninger/2026-09-16-grensa-gaar-ved-sektor-2300.md`. De
    blir stående på disk og forsvinner her i stedet, hver gang de leses.

    HELE ENTITETEN, ikke bare form- eller sektorraden. Fjernes bare raden
    som sier `organisasjonsform = DA`, står navnet, kommunen,
    postnummeret og konkursflagget igjen — altså nøyaktig persondataene,
    uten etiketten som gjorde dem gjenkjennelige. Det ville vært verre
    enn ingen filtrering, fordi neste revisjon ikke ville funnet dem.

    Entiteter uten noen av de to radene blir stående. Vi kan ikke vite
    hva de er, og en kilde uten organisasjonsformer — lokaliteter fra
    Akvakulturregisteret, lusetall — skal gå urørt gjennom. Det er grensa
    for hva denne funksjonen kan love: den fjerner det den kan se.
    """
    if frame.is_empty() or not {"entity_id", "field", "value"} <= set(frame.columns):
        return frame

    personer = _personene(frame)["entity_id"].unique().to_list()
    if not personer:
        return frame

    return frame.filter(~pl.col("entity_id").is_in(personer))


# ---- kontaktfelt i et råsvar ---------------------------------------------
#
# Regel 3 gjelder rå-arkivet like mye som snapshotene. Fram til 09.11.2026
# lagret `enhetsregisteret` hele Brreg-svaret i `data/arkiv/`, og fila fra
# 02.11.2026 hadde 1 655 gateadresser, 455 telefonnumre, 332 mobilnumre,
# 439 e-postadresser og 183 hjemmesider. Feltvalget i `FELTER` holdt dem
# ute av snapshotet, men ikke av kroppen.
#
# Lista er Brregs egne feltnavn, målt på et arkivert svar 07.11.2026 (alle
# 73 feltstier i 1 805 enheter). Bare disse kan peke på et menneske eller
# en kontaktkanal; resten er register- og regnskapsdata. Adresseobjektet
# beholdes uten adresselinjene: `kommune`, `kommunenummer`, `postnummer`,
# `poststed`, `landkode` og `land` er geografien snapshotet bruker.
KONTAKTFELT = frozenset({"telefon", "mobil", "epostadresse", "hjemmeside"})

# Brregs adresseobjekter, og nøkkelen som bærer gate eller postboks i dem.
# `beliggenhetsadresse` står på underenheter; den er med så en kilde som
# begynner å hente dem, møter vakten i stedet for å slippe gjennom.
ADRESSEOBJEKTER = frozenset({"forretningsadresse", "postadresse",
                             "beliggenhetsadresse"})
ADRESSELINJE = "adresse"


def _har_verdi(v: object) -> bool:
    return v not in (None, "", [], {})


def uten_kontaktfelt(enhet: dict) -> tuple[dict, list[str]]:
    """En kopi av enheten uten kontaktfeltene, og hvilke stier som ble
    fjernet. Originalen røres ikke.

    Bare toppnivået og de tre adresseobjektene ses på. Det er der Brreg
    legger dem, og en dypere vask ville vært en gjetning om felt ingen
    har sett. Vakten under går derimot gjennom HELE kroppen: det er den
    som skal fange det denne ikke vet om.
    """
    ut = dict(enhet)
    fjernet: list[str] = []
    for felt in sorted(KONTAKTFELT):
        if felt in ut:
            if _har_verdi(ut[felt]):
                fjernet.append(felt)
            del ut[felt]
    for obj in sorted(ADRESSEOBJEKTER):
        a = ut.get(obj)
        if isinstance(a, dict) and ADRESSELINJE in a:
            if _har_verdi(a[ADRESSELINJE]):
                fjernet.append(f"{obj}.{ADRESSELINJE}")
            ut[obj] = {k: v for k, v in a.items() if k != ADRESSELINJE}
    return ut, fjernet


def kontaktfelt_i(raw: object) -> dict[str, int]:
    """Hvor mange ganger hvert kontaktfelt står med en verdi, hvor som
    helst i en JSON-kropp. Tom dict betyr at kroppen er ren.

    Leter etter NØKLENE, ikke etter noe som ser ut som et telefonnummer.
    Det er grensa for hva prøven kan love: et nummer i fritekst går forbi
    (se `sources/romming.py`, som har sin egen vakt for det).
    """
    ut: dict[str, int] = {}

    def gaa(o: object) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in KONTAKTFELT and _har_verdi(v):
                    ut[k] = ut.get(k, 0) + 1
                elif (k in ADRESSEOBJEKTER and isinstance(v, dict)
                      and _har_verdi(v.get(ADRESSELINJE))):
                    n = f"{k}.{ADRESSELINJE}"
                    ut[n] = ut.get(n, 0) + 1
                gaa(v)
        elif isinstance(o, list):
            for x in o:
                gaa(x)

    gaa(raw)
    return dict(sorted(ut.items()))


def nekt_kontaktfelt(kilde: str, raw: object) -> None:
    """Kaster hvis en kropp som skal arkiveres har kontaktfelt.

    Samme rolle for rå-arkivet som `snapshot._nekt_personformer()` har for
    snapshotene: filteret i kilden er der feltene faktisk holdes ute, og
    dette er trakta alt skrives gjennom, for den kilden som glemmer det.

    Bare strukturerte kropper (dict og list) prøves. Bytes og tekst er
    PDF, HTML, regneark og XML, og der er en nøkkel ikke en nøkkel. Målt
    07.11.2026: ingen av de strukturerte kroppene i noen annen arkivmappe
    har noen av feltene, så vakten stopper bare `enhetsregisteret`.
    """
    if not isinstance(raw, (dict, list)):
        return
    funn = kontaktfelt_i(raw)
    if funn:
        detaljer = ", ".join(f"{k} {n}" for k, n in funn.items())
        raise ValueError(
            f"{kilde}: kroppen har kontaktfelt ({detaljer}) og arkiveres "
            f"ikke. Regel 3: adresser, telefon og e-post hentes ikke inn, "
            f"heller ikke til rå-arkivet. Fjern dem i kildens fetch() med "
            f"persondata.uten_kontaktfelt() — ikke her.")
