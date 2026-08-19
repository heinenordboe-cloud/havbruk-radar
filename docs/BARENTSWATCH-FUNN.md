# BarentsWatch fiskehelse — verifiseringsnotat

Verifisert mot levende tjeneste 18.08.2026. Alt under er målt, ikke
antatt. Rå responser ligger i `/tmp/bw-funn/` (ikke i datarepoet).

Dette er grunnlag for en spesifikasjon. Kilden er **ikke** bygget.

## Autentisering — virker

    POST https://id.barentswatch.no/connect/token
    body: client_id, client_secret, grant_type=client_credentials, scope=api

Bearer-token, `expires_in: 3600`, scope `api`. Alt i body, som antatt.
Tjenestens egen discovery-fil (`/.well-known/openid-configuration`, åpen)
bekrefter at både `client_secret_post` og `client_secret_basic` er
støttet, og at `api` er en gyldig scope.

**Merk om feilsøking:** en klient med feil secret gir `400
invalid_client`, ikke 401. Første forsøk feilet slik fordi portalen hadde
lagret en autofylt verdi fra passordbehandleren. Symptomet er
identisk med «feil nøkkel», så sjekk portalen før koden.

## Base-URL — bekreftet

`https://www.barentswatch.no/bwapi` — verifisert, ikke antatt.

OpenAPI-spesifikasjonen ligger på
`/bwapi/openapi/fishhealth/openapi.json` (675 KB). Den ligger **ikke**
på `/openapi/v1/openapi.json`, `/swagger/v1/swagger.json` eller
`/openapi.json` — alle fire gir 404.

## Endepunkter — 128, ikke 2

De to kjente fra bloggposten finnes, men er en liten del av flaten.
Disse er relevante for prosjektet:

    /v1/geodata/fishhealth/locality/{year}/{week}              alle lokaliteter, én uke
    /v1/geodata/fishhealth/locality/{localityNo}/{year}/{week} én lokalitet, én uke
    /v1/geodata/fishhealth/locality/{localityNo}/avgfemalelice/{year}   hele året
    /v1/geodata/fishhealth/locality/{localityNo}/liceTreatments/{year}
    /v1/geodata/fishhealth/locality/{localityNo}/liceMedicationEvents/{year}
    /v1/geodata/fishhealth/locality/{localityNo}/liceTypeDistribution/{year}
    /v1/geodata/fishhealth/locality/{localityNo}/seatemperature/{year}
    /v1/geodata/fishhealth/locality/{localityNo}/capacity/{year}
    /v1/geodata/fishhealth/locality/{localityNo}/disease/{year}
    /v1/geodata/fishhealth/locality/{localityNo}/escape/{year}
    /v1/geodata/fishhealth/locality/diseasezonehistory/{localityNo}
    /v1/geodata/fishhealth/localities
    /v1/geodata/fishhealth/localitiesoverlimitbyweek

Full liste i `/tmp/bw-funn/openapi-fishhealth.json`.

Merk avveiningen: ukeendepunktet gir alle lokaliteter i ett kall
(730 kall for 2012-2026). Per-lokalitet-per-år ville vært 1777 × 15 ≈
26 000 kall for samme dekning. Uken er riktig akse for backfill.

## 1. localityNo ER siteNr — ja

**Det viktigste spørsmålet, og svaret er ja.**

    BarentsWatch uke 30/2026:      1777 lokaliteter
    Fiskeridirektoratet 17.08:     1779 lokaliteter
    overlapp:                      1777  (100,0 % av BW, 99,9 % av FD)
    kun i BW: 0                    kun i FD: 2

Hver eneste lokalitet hos BarentsWatch finnes i vårt snapshot. Kobling
krever ingen oversettelsestabell.

    10029   FD: TUHOLMANE Ø     BW: Tuholmane Ø
    26295   FD: LANGØY          BW: Langøy

Navnene er identiske bortsett fra store/små bokstaver. **Ikke bruk navn
som nøkkel** — bruk nummeret, som er eksakt.

## 2. Felter per lokalitet per uke

Rå JSON, uredigert, for 10029 i uke 30/2026:

```json
{
  "localityNo": 10029,
  "localityWeekId": 2109394,
  "name": "Tuholmane Ø",
  "hasReportedLice": true,
  "isFallow": false,
  "avgAdultFemaleLice": 0.02,
  "hasCleanerfishDeployed": false,
  "hasMechanicalRemoval": false,
  "hasSubstanceTreatments": false,
  "hasPd": false,
  "hasIla": false,
  "municipalityNo": "1149",
  "municipality": "Karmøy",
  "lat": 59.371233,
  "lon": 5.216333,
  "isOnLand": false,
  "inFilteredSelection": true,
  "hasSalmonoids": true,
  "isSlaughterHoldingCage": false
}
```

19 felter. `avgAdultFemaleLice` er tallet som betyr noe — voksne hunnlus
per fisk, med grenseverdi 0,5 i sesong. `hasReportedLice` skiller
«rapportert null» fra «ikke rapportert», som er samme skille som
`ansatte_er_registrert` i Enhetsregisteret og må bevares på samme måte.

Toppnivået er `{year, week, localities: [...]}`.

## 3. Historisk dybde — 2012 uke 1

    2010 uke 1:     0 lokaliteter
    2011 uke 1:     0 lokaliteter
    2012 uke 1:  1999 lokaliteter,  366 med lusetall
    2013 uke 1:  1843 lokaliteter,  467 med lusetall

**Fallgruve:** 2010 og 2011 gir `200 OK` med tom liste, ikke 404. En
backfill som ikke sjekker antall vil skrive tomme snapshots for år som
ikke finnes, og de er append-only.

Registeret var større før: 1999 lokaliteter i 2012 mot 1777 i dag.

## 4. Rapporteringsetterslep — kritisk for append-only

Andel av AKTIVE lokaliteter (ikke brakklagte) som har rapportert:

    uke   lokaliteter  brakklagt  aktive  rapportert  andel av aktive
     30         1777       1195     582         578           99,3 %
     31         1777       1201     576         570           99,0 %
     32         1777       1187     590         576           97,6 %
     33         1777       1177     600         528           88,0 %
     34         1777       1176     601          32            5,3 %

Uke 34 er inneværende uke. **Henter man inneværende uke, fanger man
5 % av dataene og fryser det for alltid.**

Andelen av totalen (32 %) er misvisende: to tredeler av lokalitetene er
brakklagte og skal ikke rapportere. Måler man mot aktive, er
rapporteringen tilnærmet komplett — men først etter to uker.

**Konsekvens for spesifikasjonen:** hent uke N-2 eller eldre, aldri
inneværende uke. Uke 33 på 88 % er også for tidlig. Dette er grunnen til
at `observed_at` som gyldighetsdato (beslutning 18.08) er nødvendig her:
snapshotet må dateres til uken det gjelder, ikke til dagen vi hentet det,
ellers kan ikke etterslepet håndteres i det hele tatt.

## 5. Ratebegrensning — ingen dokumentert

**Ingen rate-headere i det hele tatt.** Ingen `X-RateLimit-*`, ingen
`Retry-After`, ingen `Quota`. Responsen har bare
cache-control, etag, last-modified og sikkerhetsheadere.

Målt: 10 sekvensielle kall på 1,9 s = **0,19 s per kall**, alle 200.
Backfill 2012-2026 er ~730 ukekall ≈ **2 minutter**.

At det ikke finnes en dokumentert grense betyr ikke at det ikke finnes
en. Uten et tak å forholde seg til bør backfill selvbegrense — en liten
pause mellom kall og respekt for `etag`/`last-modified` — framfor å
kjøre så fort tjenesten tillater.

## Åpne spørsmål til spesifikasjonen

- Hvilke av de 19 feltene skal lagres som observasjoner? `lat`/`lon` og
  `municipality` duplikerer Fiskeridirektoratet; `avgAdultFemaleLice`,
  behandlingsflaggene og `hasPd`/`hasIla` er nye.
- Skal brakklagte lokaliteter gi observasjoner, eller bare `isFallow`?
- Ukesakse mot datoakse: filnavnet er en dato, men kilden er ukebasert.
  Mandagen i ISO-uken er det opplagte valget, men det bør stå skrevet.
