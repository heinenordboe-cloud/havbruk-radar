# CLAUDE.md

Harde regler for dette repoet. Se `docs/ARKITEKTUR.md` for hvorfor.

## 1. `core/` endres ikke for å legge til en kilde

En ny kilde er én ny fil i `sources/` som arver `Source` og returnerer
`Observation`-objekter (se `core/contract.py`). Ingen registrering,
ingen import andre steder, ingen endring i `core/`.

Hvis en ny kilde later til å kreve en endring i `core/`: ikke gjør
unntaket. Si fra at kontrakten mangler noe, og la brukeren avgjøre om
`contract.py` skal utvides.

## 2. Data skrives én gang, aldri om

Append-only gjelder `data/raw/<kilde>/<dato>.parquet`,
`data/changelog/<dato>.parquet` og rå-arkivet i `data/arkiv/`. En fil
for en gitt dato skrives, og røres aldri igjen — kollisjon løses med
løpenummer, ikke overskriving. Grunnen er git: en fil som skrives om
hver uke vokser repoet kvadratisk i stedet for lineært.

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
