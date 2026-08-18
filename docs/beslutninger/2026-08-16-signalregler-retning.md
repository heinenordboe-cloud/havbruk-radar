---
dato: 2026-08-16
tittel: Signalregler har retning
status: gjeldende
commit: 62fe7d4
---

# Signalregler har retning

**Bestemt:** `retning: opp | ned | begge` i `rules/signals.yml`.
Kapasitets- og bemanningsreglene er splittet i to hver.

**Hvorfor:** Regelen het "Kapasitetsøkning over 10 %", men koden brukte
absoluttverdi. Et kutt på ti prosent ble scoret under et navn som påsto
det motsatte. En endringslogg som lyver om retning er verre enn ingen
endringslogg — den blir lest og trodd.

**Sidegevinst:** Nedbemanning og bemanningsvekst kan nå vektes ulikt.
Nedbemanning er satt høyere (6 mot 5), fordi det er det mer akutte
signalet i en bransje med konsolidering. Det er en vurdering, ikke en
sannhet, og den er én linje YAML å endre.

**Ville snudd det:** At vektingen i praksis gir en topp-10-liste som er
mindre nyttig å lese enn den var. Vurderes når det finnes nok endringer
til at listen faktisk fylles.
