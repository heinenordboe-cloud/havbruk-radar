---
dato: 2026-08-17
tittel: Volumvakt: en kilde kan feile uten å være nede
status: erstattet-av 2026-08-17-volumvakt.md
commit: 
---

# Volumvakt: en kilde kan feile uten å være nede

**Bestemt:** `health.py` sjekker antall observasjoner mot forrige
snapshot. Faller det under `min_andel` (default 0,90, overstyrbar per
kilde i `config.yml`), går kilden i samme `nede`-liste som en kilde som
ikke svarer — rød jobb.

**Hvorfor:** Alarmen fanget kun kilder som er nede. En kilde som svarer,
men leverer feil, var usynlig. Endrer en etat et feltnavn, finner
`parse()` det ikke, observasjonstallet faller, og jobben blir grønn.
Oppdages det i uke 40 er tjue uker ødelagt.

Ikke hypotetisk: `SCHEMA` i `snapshot.py` droppet de tre
proveniensfeltene stille tidligere i dag. Koden var riktig, testene
grønne, feltene borte fra parquet. Fanget kun fordi noen så etter.

**Terskelen er en vurdering, ikke et funn.** De fem samme-dags-
snapshotene viser 0 % varians, men det beviser bare at et tregt register
er stabilt innenfor én dag. Ukentlig drift er ukjent til det finnes noen
måneders data.

**Asymmetrisk med vilje:** en økning varsler ikke. Systemets erklærte
feilmodus er stille tap; en økning mister ingenting, og synes allerede i
commit-meldingen.

**Første kjøring varsler ikke** — gated på at `previous()` returnerer
None, altså på faktisk datatilgjengelighet framfor helsetilstand.

**Prisen:** Falske positiver ved reell nedgang i registeret. En etat som
sletter enheter i bulk gir rød jobb uten at noe er galt.

**Ville snudd det:** At terskelen utløses av normal variasjon oftere enn
den fanger reelle feil. Da justeres tallet med data i hånd, ikke
prinsippet — vakten selv er riktig.
