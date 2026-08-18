---
dato: 2026-08-16
tittel: Data skrives én gang, aldri om
status: gjeldende
commit: 03b5194
---

# Data skrives én gang, aldri om

**Bestemt:** Endringsloggen er `data/changelog/<dato>.parquet`, ikke én
samlet `changelog.parquet`. `run.py` nekter dessuten å kjøre hvis dagens
snapshot allerede finnes; `--tving` overstyrer.

**Hvorfor:** Komprimert parquet delta-komprimerer elendig i git. En fil
som skrives om hver uke lagres som en ny nesten-full kopi hver gang, og
repoet vokser kvadratisk. Målt over 104 simulerte uker med 40 endringer
hver: 1,9 MB mot 340 KB i `.git`. Snapshotene hadde alltid riktig mønster;
changeloggen brøt det.

Samme-dags-guarden løser det andre halve problemet: uten den førte en
manuell rekjøring de samme endringene inn i loggen på nytt, fordi diffen
sammenlignet mot forrige uke igjen. Reprodusert før fiksen.

**Merk:** Dagens parquet ble faktisk skrevet tre ganger 16.08 før guarden
kom (44074 → 44128 → 44074 bytes). Løftet i `snapshot.py` om at
ingenting overskrives var ikke sant i praksis. Nå er det det.

**Ville snudd det:** Ingenting rimelig. Append-only er billigere på alle
akser som betyr noe her.
