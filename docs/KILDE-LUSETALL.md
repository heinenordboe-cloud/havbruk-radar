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

## Hva som ville snudd det

At rapporteringsandelen viser seg å variere sesongmessig på en måte som
gjør 80 %-grensen til støy. Da justeres tallet med data i hånd — vakten
selv er riktig.
