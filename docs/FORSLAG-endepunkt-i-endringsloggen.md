# Forslag: endepunktet følger med inn i endringsloggen

**Ikke bygget.** Dette er valget presentert med avveininger, til
avgjørelse. Ingenting i `core/` er endret. Alle tre variantene under
krever en endring i `core/diff.py` (og A også i `CHANGELOG_SKJEMA`), og
etter CLAUDE.md regel 1 er det din avgjørelse, ikke kildens.

## Problemet, presist

`endepunkt` ligger på hver rad i snapshotet siden 02.10.2026
(`Observation.endepunkt`), men ikke i changeloggen. `diff.compare()`
sammenligner `(entity_id, field)` mellom to snapshots og vet ikke at de
kom fra hvert sitt lag.

Første tilfelle: changeloggen `biomasselag/2026-10-04` har 29 rader på 15
lokaliteter, primær (`2026-09-22`, uten `endepunkt`-kolonne) mot reserve
(`2026-10-04`). To av dem går bakover i `siste_rapport` (10726, 10747:
2026-08-31 → 2026-07-31). Om de 29 er kildens bevegelse eller byttets,
kan ikke måles — se docs/KILDE-BIOMASSELAG.md, «Uke 40».

Ingen rad i changeloggen sier at et bytte skjedde. Om to år ser de 29
radene ut som vanlige endringer.

## Tre varianter

### A. Proveniens på raden — ingen filtrering (anbefalt)

`endepunkt` og `forrige_endepunkt` i `CHANGELOG_SKJEMA`, fylt fra
snapshotene på samme måte som `domene`/`forrige_domene` (en
`snapshot.endepunkt_i()` ved siden av `snapshot.domene_i()`). Tom streng
= vet ikke, slik at 2026-09-22-siden leses som ukjent og ikke som
«primær» (regel 2, og samme valg som `published_at`).

`diff.bevegelse()` endres IKKE. Commit-meldingen og health får en linje
når `endepunkt != forrige_endepunkt` og begge er kjente:
`biomasselag: 29 endringer over endepunktbytte (Yggdrasil/0 → akva/6)`.

- **For:** ingen ekte endring blir borte. 21495 og 32397 fikk fisk, 45072
  og 10821 ble tømt — fire `har_fisk`-endringer som godt kan være ekte,
  og som ville vært usynlige under B.
- **Mot:** de falske endringene står fortsatt i «X endringer denne uka».
  Leseren må selv se merket.

### B. Merk raden som `endepunktbytte`, filtrer fra bevegelse

Ny `change_type` på linje med `utvalgsutvidelse` (1b-3): radene BEHOLDES,
men `endepunktbytte` legges i `IKKE_BEVEGELSE`.

- **For:** «X endringer denne uka» blir aldri forurenset av et bytte.
- **Mot:** filteret er grovt. Det gjør hele uka taus, også de ekte
  endringene. 1b-3s asymmetri sier at en undertrykt rad er en hendelse
  ingen får se — og her vet vi ikke hvilke rader det gjelder, bare at
  noen kan gjelde. `utvalgsutvidelse` kunne merkes per rad fordi
  påstanden var sikker per rad. Det kan ikke denne.

### C. Nekt å sammenligne, som `Grunnlagssprik` i `revisjon()`

`compare()` kaster når endepunktene er kjente og ulike.

- **Mot:** ukas changelog for kilden blir ikke skrevet. Det er riktig for
  revisjonsaksen (der er spørsmålet ubesvarlig) men feil her: en
  lokalitet som får fisk mens primæren er nede, er fortsatt en hendelse.
  Forkastes.

## Det som faktisk ville gjort det MÅLBART

Ingen av de tre skiller falske fra ekte endringer. Det krever begge
endepunktene på samme tidspunkt, og det har vi aldri hatt — primæren
svarte ikke på `/query` 02.10 eller 04.10.

Forslag til kilden (ikke `core/`): den dagen primæren svarer igjen,
henter `fetch()` ÉN gang også reserven og legger kroppen i arkivet som
en egen fil ved siden av, uten å parse den til snapshotet. Da finnes et
par (primær, reserve) med samme hentetidspunkt, og differansen mellom dem
ER endepunktets bidrag. Det gjør punkt 4 i etterkontrollen 04.10 målbart
i ettertid — men bare framover, ikke for uke 40. Uavklart: om arkivet
tåler to kropper for samme kilde og dato uten løpenummerkollisjon
(regel 2, F14), og om det krever en kontraktsendring.

## Anbefaling

A nå, og parhentingen ved tilbakebytte. B bare hvis bytter blir vanlige
og endringstallet faktisk villeder noen.
