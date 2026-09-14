# Lusetall (BarentsWatch fiskehelse) — kildespesifikasjon

Oppdrag til Claude Code. Alle tall her er verifisert mot levende tjeneste
18.08.2026, se `docs/BARENTSWATCH-FUNN.md`. Ingenting er antatt.

## Hvorfor denne kilden

Lusepress per lokalitet per uke, tilbake til 2012. Det er fjorten år med
ukesserier på én kveld — ikke seks måneders venting. Og den kobler rett
inn i de 1779 lokalitetene som allerede samles: `localityNo` hos
BarentsWatch **er** `siteNr` hos Fiskeridirektoratet, verifisert med 100 %
overlapp på 1777 lokaliteter, null som bare finnes hos BarentsWatch.

Nummeret er nøkkelen, ikke navnet. Navnene skiller seg på store og små
bokstaver mellom kildene.

## Forutsetning

`observed_at` er datoen snapshotet gjelder for, ikke datoen vi hentet det.
Se [beslutningen](beslutninger/2026-08-18-observed-at-er-gyldighetsdato.md).
Uten det skillet kan rapporteringsetterslepet under ikke håndteres i en
append-only-modell overhodet.

## Etterslepet — det som avgjør designet

Andel av **aktive** lokaliteter som har rapportert, målt 18.08.2026:

| Uke | Andel |
|---|---|
| 34 (inneværende) | 5,3 % |
| 33 | 88,0 % |
| 32 | 97,6 % |
| 31 | 99,0 % |
| 30 | 99,3 % |

Målt mot aktive, ikke totalen. To tredeler av lokalitetene er brakklagte
og skal ikke rapportere, så andel av totalen (32 %) er misvisende.

**Kilden henter uke N−4.** Ved N−3 er tallet 99,0 mot 99,3, altså
marginalt — men lusetall haster ikke for noen analyse her, og en måneds
etterslep koster ingenting mot at en ufullstendig uke er permanent.

**Kilden skal nekte å skrive en uke der andelen rapporterte er under
80 %.** Ikke som unntak som feller kjøringen, men som `advarsler` på
kilden, slik at uka merkes `DELVIS:` i commit-meldingen og kan hentes på
nytt senere. Dette er vakten mot at etterslepet endrer seg uten at noen
merker det.

Fra 31.08.2026 gjør en advarsel ikke jobben rød — den blir en
::warning::. Merket i commit-meldingen er derfor det som bærer signalet
her; se `docs/beslutninger/2026-08-31-tilsyn-feiler-ikke-jobben.md`.

## Ferskheten, målt 01.09.2026

Etterslepet er ikke bare en policy i koden — det er målt på det som
faktisk ligger på disk, og det er **nøyaktig 28 dager**:

    uke 31  observed_at 2026-07-27  hentet 2026-08-24   28 d
    uke 32  observed_at 2026-08-03  hentet 2026-08-31   28 d

Sjøtemperatur følger samme takt (28 d for uke 32), som den skal — det er
den samme rapporten.

Eldre uker i arkivet viser større tall (opptil 170 d), men de er
backfillet i én omgang 19.08.2026 og sier ingenting om den ukentlige
rytmen. Bare kjøringer med `fetched_at` etter backfillen måler den.

**Hva en nettside kan love:** ferskeste lusetall er fire uker gamle, og
det er en KONSTANT, ikke en variabel. Den følger av at kilden henter uke
N−4 for å få 99,3 % rapportert i stedet for 99,0 % ved N−3. Lover man
ferskere enn fire uker, lover man noe innsamlingen ikke er innstilt på å
gi — og innstillingen er et bevisst valg, ikke en begrensning hos
BarentsWatch.

Det forplanter seg: `kildeledd-delvis.parquet` slutter fire uker bak i
tid av nøyaktig samme grunn, og det er ikke et hull i beregningen.

## Ukedato-konvensjonen

Endepunktet tar år og uke; filnavnet må være en dato.

**Mandag i ISO-uka.** Uke 34 i 2026 blir `2026-08-17.parquet`. Valget
blir stående for alltid i filnavnene og skal ikke endres senere.

## Endepunkt og paginering

    GET {base}/v1/geodata/fishhealth/locality/{year}/{week}

Alle lokaliteter for én uke i ett kall. Det er riktig akse for backfill:
730 kall tilbake til 2012, mot rundt 26 000 med per-lokalitet-per-år.

Det finnes 128 endepunkter totalt, blant dem behandlinger, sjøtemperatur,
sykdom og rømming. **De bygges ikke nå.** Én kilde om gangen — det er
prinsippet prosjektet hviler på. Rømming og sykdom er verdt egne
vurderinger senere.

## Autentisering

OAuth2 client credentials mot `https://id.barentswatch.no/connect/token`,
alt i body, scope `api`.

**Token caches og gjenbrukes.** Backfill er 730 kall; ett token-kall per
API-kall er hverken nødvendig eller høflig. Fornyes når det utløper.

**Miljøvariabler:** `BARENTSWATCH_CLIENT_ID` og
`BARENTSWATCH_CLIENT_SECRET`. `BARENTSWATCH_KEY` i `core/config.py` og
`samle.yml` **slettes helt** — ikke som alias, ikke som fallback. Den er
en antakelse om en API-nøkkel-form fra før noen hadde sett API-et, og en
død referanse i en docstring er nøyaktig det som ga forvirringen.

Begge inn i Actions-secrets i `havbruk-radar-data`, begge gjennom
`samle.yml`, referert som `${...}` i `config.yml`. Verdien aldri i fil.

**Mangler en av dem, skal kilden feile rødt** — ikke returnere tomt. En
kilde som leverer null fordi den ikke fikk logge inn ser ellers ut som en
uke uten lus.

## Ratebegrensning

Ingen dokumentert grense, ingen `X-RateLimit-*`, ingen `Retry-After`.
Målt 0,19 s per kall.

Fravær av dokumentert grense er ikke fravær av grense. **Legg inn en
pause på 0,5 s mellom kall i backfill.** 730 kall blir da seks minutter i
stedet for to. Det er en billig forsikring mot å bli stengt ute fra en
kilde vi skal bruke i to år.

## Felter

19 felter kommer tilbake. Feltnavn i observasjonene skal være norske, som
i de andre kildene — feltnavn er en kontrakt mot historikken, og en
omdøping senere leser diffen som at det gamle forsvant og et nytt oppsto.

**`hasReportedLice` må bevares som eget felt.** Det skiller «rapportert
null lus» fra «ikke rapportert», nøyaktig samme skille som
`ansatte_er_registrert` i Enhetsregisteret. Uten det blir en manglende
rapport til en null i enhver analyse, og det er feil på den farlige
måten.

**Ikke emit `navn`.** Akvakulturkilden eier lokalitetsnavnet. Emitter
begge kilder `navn` med ulik store/små bokstaver, står det en permanent
falsk forskjell i dataene. Lusetall emitter kun lusespesifikke felter.

Feltvalget forøvrig gjøres i `sources/lusetall.py`, ikke i `config.yml` —
samme begrunnelse som for akvakultur.

## Backfill

**Fella:** 2010 og 2011 gir `200 OK` med tom liste, ikke `404`. En
backfill som ikke teller rader vil løpe bakover i det uendelige og skrive
tomme snapshots for år som ikke finnes.

`snapshot.write()` skriver ikke fil for en tom ramme, så skaden er
begrenset — men backfillen skal stoppe eksplisitt og si fra, ikke løpe
videre stille.

**Tidligste uke med data er 2012 uke 1.**

Backfill kjøres eldst først, slik at `diff.compare()` regner ut endringer
mellom historiske uker underveis. `health.py` skal ikke oppdateres under
backfill — volumreferansen er et høyvannsmerke mot forrige kjøring, og
730 uker på rad vil enten fyre konstant eller forgifte nivået.

## Frekvens

`min_dager_mellom = 7`.

Merk at cronen fyrer ukentlig, så en kilde kan ikke i praksis gå oftere
enn det uansett. Det er riktig her.

## Akseptansetest

Regel 6. Ikke verifisert før tallene er sett i fila.

1. Hent én uke, skriv snapshot, og bekreft at antall lokaliteter i
   parquet stemmer med antall i rå JSON.
2. Bekreft at `entity_id` fra lusetall finnes igjen som `entity_id` i
   akvakultur-snapshotet for samme uke. Det er hele koblingspåstanden.
3. Bekreft at en lokalitet med `hasReportedLice: false` gir en observasjon
   med det feltet, og ikke en manglende rad.
4. Kjør backfill for tre uker og bekreft tre filer med riktige datoer,
   mandag i hver ISO-uke.
5. Kjør backfill mot 2011 og bekreft at den stopper og sier fra, ikke
   skriver tomme filer.

## Lisens og attribusjon

Vilkårene på `www.barentswatch.no/artikler/api-vilkar` er sist oppdatert
02.11.2023 og lest 12.09.2026. Etter mønster av
`docs/KILDE-BIOMASSE.md` punkt 10; hele kjeden står i
`docs/LISENSKJEDE.md`.

Data fra BarentsWatch-API-ene er gjort tilgjengelig under **NLOD** med
mindre API-dokumentasjonen sier noe annet. **Kommersiell bruk er
uttrykkelig tillatt.**

**Attribusjonen skal være synlig for SLUTTBRUKER**, ikke bare i et repo
eller i en kildekommentar. To setninger, og begge er ordrette krav:

> «Data levert av BarentsWatch»

> «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra
> Mattilsynet.»

Den andre er **dataeierattribusjonen**, og den er ikke valgfri fordi vi
henter fra BarentsWatch i stedet for fra Mattilsynet — det er nettopp
da den trengs. Den dekker nøyaktig de feltene denne kilden bærer:
lusetallene, `har_rensefisk` og `har_medikamentell_behandling`. At de to
siste har sluttet å bære informasjon (se
`docs/beslutninger/2026-09-01-lusetall-to-felter-er-datatap.md`) endrer
ikke attribusjonsplikten — vi henter dem fortsatt, og de ligger i
snapshotene.

**Enhver visning, rapport eller publisering som bruker disse tallene må
bære begge setningene.** Det er et lisensvilkår, ikke en høflighet.

Fire plikter til, som ikke er attribusjon og derfor lett faller ut:

1. **Kommersielle brukere bes registrere API-klienten** med formål,
   firma og kontaktperson.
2. **BarentsWatch skal kontaktes før høytrafikkbruk**, ellers kan de
   fakturere serverkostnader. Én ukentlig kjøring er ikke det. En ny
   backfill over de 762 ukene er nettopp det plikten handler om — se
   «Backfill» over.
3. **«BarentsWatch» kan ikke inngå i tjenestenavnet.**
4. **Datainnholdet skal ikke endres.** Arkivlaget oppfyller dette av seg
   selv: rå-kroppen lagres uendret og hashet før noe parses. Det som
   avledes (`kildeledd`) er merket som avledet og er ikke en gjengivelse
   av kildens data.

Plikt 1 og 2 krever en HANDLING fra oss, ikke bare en setning i en
visning. Ingen av dem er utført per 14.09.2026, og ingen av dem er
utløst ennå.

## Hva som ville snudd det

At rapporteringsandelen viser seg å variere sesongmessig på en måte som
gjør 80 %-grensen til støy. Da justeres tallet med data i hånd — vakten
selv er riktig.
