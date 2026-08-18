---
dato: 2026-08-16
tittel: Repoet er offentlig
status: gjeldende
commit: 
---

# Repoet er offentlig

**Bestemt:** `havbruk-radar` er gjort offentlig. Erstatter beslutningen
lenger ned om å holde det privat.

**Hvorfor:** README var presentabel nok, og verdien av synlig
commit-historikk begynner å løpe fra dag én. Betingelsen fra
privat-beslutningen er verifisert: snapshotet inneholder kun selskapsdata
(954 enheter, ni felter, alle entity_id ni siffer), ingen roller, ingen
persondata — bekreftet ved inspeksjon av både kode og parquet-fil.

**Forpliktelser dette utløste:** MIT-lisens på koden og NLOD-attribusjon
for Brreg-data i README, begge på plass. NLOD er bekreftet i Brregs egen
OpenAPI-spesifikasjon, ikke antatt.

**Ville snudd det:** At persondata må inn i pipelinen, eller at
produktretningen blir alvor og endringsloggen er selve varen.
