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

Tre feil i dette prosjektet har hatt samme rotårsak — et tidspunkt slått
opp på nytt et sted til, eller et tidspunkt som handler om OSS brukt som
om det handlet om VERDEN:

- **F4:** frekvensvakten målte filnavnsdato der den skulle målt
  innsamlingstidspunkt, og leste permanent 28 dager for lusetall.
- **F6:** `run.py` daterte snapshotet etter kjøredagen mens kilden
  stemplet radene med uka de gjaldt for. Filnavnet løy om innholdet.
- **F7:** `fetch()` slo opp klokka mens `gjelder_for()` fikk datoen inn.
  To oppslag som kan svare ulikt rundt midnatt — og da får fila navn
  etter én uke og innhold fra en annen.

Skillet som gjelder: `observed_at` handler om verden, `fetched_at` og
`sist_forsok` handler om oss. Blander du dem, blir feilen usynlig for
enhver kilde uten etterslep — og permanent for dem som har det.

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
