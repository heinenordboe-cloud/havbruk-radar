# CLAUDE.md

Harde regler for dette repoet. Se `docs/ARKITEKTUR.md` for hvorfor.

## 1. `core/` endres ikke for å legge til en kilde

En ny kilde er én ny fil i `sources/` som arver `Source` og returnerer
`Observation`-objekter (se `core/contract.py`). Ingen registrering,
ingen import andre steder, ingen endring i `core/`.

Hvis en ny kilde later til å kreve en endring i `core/`: ikke gjør
unntaket. Si fra at kontrakten mangler noe, og la brukeren avgjøre om
`contract.py` skal utvides.

## 1b. En kilde leser aldri klokka — den får tiden inn

`fetch(kjoredato)` og `gjelder_for(kjoredato)` får datoen som argument.
Ingen kilde skal kalle `date.today()` eller `datetime.now()` for å
avgjøre hvilket tidsrom den henter, og kjernen slår opp kjøredatoen
nøyaktig ett sted: `run.py`.

Fire feil i dette prosjektet har hatt samme rotårsak — et tidspunkt
slått opp på nytt et sted til, eller et tidspunkt som handler om OSS
brukt som om det handlet om VERDEN:

- **F4:** frekvensvakten målte filnavnsdato der den skulle målt
  innsamlingstidspunkt, og leste permanent 28 dager for lusetall.
- **F6:** `run.py` daterte snapshotet etter kjøredagen mens kilden
  stemplet radene med uka de gjaldt for. Filnavnet løy om innholdet.
- **F7:** `fetch()` slo opp klokka mens `gjelder_for()` fikk datoen inn.
  To oppslag som kan svare ulikt rundt midnatt — og da får fila navn
  etter én uke og innhold fra en annen.
- **F8:** frekvensvakten målte `sist_forsok` der den skulle målt
  `sist_ok`. Lusetall feilet tre ganger på rad uten å hente en rad, og
  fikk syv dagers karantene for det.

Skillet som gjelder: `observed_at` handler om verden, `fetched_at` og
`sist_forsok` handler om oss. Blander du dem, blir feilen usynlig for
enhver kilde uten etterslep — og permanent for dem som har det.

### 1b-2. Et FORSØK er ikke et RESULTAT

Samme regel, uten klokka. `sist_forsok` og `fetched_at` sier at vi
prøvde. `sist_ok` og radene på disk sier at vi fikk noe. En vakt som
avgjør om vi skal hente, skal måle det siste — ellers gir en feilende
kjøring karantene på like vilkår med en vellykket, og en periode som
ikke kan hentes igjen går tapt mens jobben ser ut til å ha gjort
jobben sin.

F8 er formen i klartekst: `[vent] lusetall hentet i dag` om en kilde
som hadde feilet tre ganger og hentet null rader. `sist_forsok` var
satt, `sist_ok` var `null`, og vakten leste det feltet som var satt.

Alle fire feilene over har samme form som regel 3s ENK-kontroll: en
mekanisme som måler noe som LIGNER det den skal måle, og som er riktig
i akkurat de tilfellene der de to faller sammen — kilden uten
etterslep, kjøringen som lykkes, foretaket som er et AS. Den holder
helt til den ikke gjør det, og da er den stille.

Når du bygger en kontroll: still spørsmålet du faktisk vil ha svar på,
og velg feltet som svarer på DET. Er du fristet til å bruke et felt
fordi det «pleier å følge» det riktige — `feil_paa_rad` for «lyktes
vi», ni siffer for «er dette et selskap» — er det ikke en snarvei. Det
er neste nummer i denne lista.

### 1b-3. En verdi som avgjør hva dataene BETYR, lagres SAMMEN med dem

De to reglene over handler om å måle riktig ting. Denne handler om at
tingen i det hele tatt må være der å måle.

- **F9:** hvilke næringskoder vi søkte på lå bare i `config.yml` og i
  git. Et snapshot kunne fortelle hva vi FANT, men ikke hva vi LETTE
  ETTER — og da kan ingen sammenligning av to snapshots skille «ny i
  bransjen» fra «ny i vårt utvalg». 24.08.2026 ga det 25804 av 26673
  endringer (96,7 %): 908 selskaper som kom inn da lista ble utvidet
  kvelden 17.08, ingen av dem registrert siden forrige snapshot.

Prøven er enkel, og den skal stilles om hver innstilling som påvirker
innsamlingen: **kan et snapshot alene svare på hva denne verdien var da
raden ble skrevet?** Kan det ikke det, skal verdien stemples på raden —
som `fetched_at`, `source_version`, `raw_hash` og nå `utvalg`.

`diff.compare()` hadde regelen for feltnavn fra før: et nytt FELT er en
skjemautvidelse, ikke en hendelse, og 18687 rader ble undertrykt på det
grunnlaget 17.08. Forskjellen på de to var aldri prinsipiell — bare at
feltnavnene lå i dataene og næringskodene ikke gjorde det.

Merk asymmetrien i hvordan de behandles: skjemautvidelsen SLETTES fordi
påstanden er sikker fra de to snapshotene alene. Utvalgsutvidelsen
MERKES og radene beholdes, fordi påstanden hviler på et felt som kan
være tomt. En undertrykt rad er en hendelse ingen får se.

Kjente steder regelen ennå ikke er oppfylt, med vitende og vilje:
`core/persondata.PERSONFORMER` (virker ved LESING, så lista kan endre
hva et gammelt snapshot inneholder) og pagineringstaket i
`sources/enhetsregisteret.py` (avkortning gir en advarsel, ikke et
merke i dataene). Se beslutningen fra 24.08.

## 2. Data skrives én gang, aldri om

Append-only gjelder `data/raw/<kilde>/<dato>.parquet`,
`data/changelog/<dato>.parquet` og rå-arkivet i `data/arkiv/`. En fil
for en gitt dato skrives, og røres aldri igjen — kollisjon løses med
løpenummer, ikke overskriving. Grunnen er git: en fil som skrives om
hver uke vokser repoet kvadratisk i stedet for lineært.

Unntaket er changelog: den overskriver sin egen fil for samme dato
med vilje. `les_alt()` konkatenerer filene, så en ekstra fil ville
dobbeltført hver endring i loggen. Append-only gjelder rådata —
changelog er avledet og kan regnes ut på nytt fra snapshotene.
Vil du endre det, må `les_alt()` deduplisere først.

## 3. Ingen roller eller persondata fra Enhetsregisteret

Bare virksomhets- og lokalitetsdata hentes. Roller, gateadresser og
andre personopplysninger hentes bevisst ikke inn — verken dette repoet
eller datarepoet skal være et personregister.

**Noen ORGANISASJONSFORMER er personer.** Et enkeltpersonforetak er ikke
et eget rettssubjekt: foretaket ER innehaveren, og da er navn, kommune,
postnummer, næring og konkursflagg opplysninger om et navngitt menneske.
Å utelate rolleendepunktet og gateadressen er ikke nok — 34 ENK lå i
hvert snapshot i fem dager fordi de kom inn gjennom det ordinære
næringskodesøket. `core/persondata.py` eier lista, kilden filtrerer i
`fetch()` før arkivering, og `snapshot.write()` nekter å skrive et
snapshot som likevel inneholder dem.

Kontrollen som sviktet, sviktet på samme måte som feilene i 1b: åpningen
16.08 ble begrunnet med at alle `entity_id` var ni siffer, og et ENK har
ni siffer akkurat som et AS. Skillet fantes i dataene
(`organisasjonsform`), men ble ikke båret over i kontrollen som skulle
håndheve det. Når du skal bevise at noe ikke er der, spør om DET du
faktisk vil vite, ikke om noe som korrelerer med det.

## 4. Skill mellom bekreftet og antatt

Har du ikke selv sett et endepunkt, en respons eller et format, si det
uttrykkelig i stedet for å anta at det stemmer med et annet kildeformat
eller med dokumentasjonen.

## 5. Historikken kan ikke rekonstrueres

Snapshotet fra en gitt dato lar seg ikke hente i etterkant, selv om
registerdataene er åpne. Foreslå aldri å utsette innsamling til fordel
for mer bygging — en ukes forsinket kjøring er en uke tapt historikk,
ikke en uke spart arbeid.

## 6. Verifiser empirisk

En endring som ser riktig ut i koden er ikke verifisert før du har
kjørt den og sett resultatet i fila (parquet, arkiv, changelog — det
som faktisk endret seg). Kjør testene og les resultatet, ikke bare
diffen.
