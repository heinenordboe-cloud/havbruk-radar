---
dato: 2026-08-17
tittel: Testene kan ikke nå ekte data
status: gjeldende
commit: 3df41c1
---

# Testene kan ikke nå ekte data

**Bestemt:** `tests/conftest.py` setter `HAVBRUK_DATA_DIR` til en fersk
temp-mappe ved modulimport, med opprydding via `atexit`.

**Hvorfor:** To tester kalte `runner.run_all(arkiver=True)` uten å
isolere `ARKIV_DIR`, og siden `HAVBRUK_DATA_DIR` pekte på det private
datarepoet, skrev hver pytest-kjøring falske arkivfiler rett inn i
historikken. Testdata i det som er hele fortrinnet.

**Hvorfor conftest og ikke en fixture:** `core/paths.py` beregner
stiene ved import, og andre moduler binder verdiene ved navn. Når en
fixture kjører, har pytest allerede importert alt. `conftest.py` på
modulnivå er det eneste punktet som er tidlig nok.

**Poenget er ikke lappen, men umuligheten:** Å isolere de to testene
hadde løst i dag. Å gjøre testene ute av stand til å nå ekte data løser
resten av prosjektet.

**Verifisert:** Filliste i datarepoet før og etter full testkjøring —
uendret. Og positivt bekreftet at temp-mappa faktisk ble opprettet og
brukt, ikke bare at ingenting ble skrevet ved et sammentreff.

**Ville snudd det:** Ingenting.
