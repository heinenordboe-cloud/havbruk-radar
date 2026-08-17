# Workflows

`test.yml` kjører testsuiten på hver push og PR. Den bor her.

**Innsamlingen bor ikke her.** Den ligger i det private datarepoet
`havbruk-radar-data`, som henter denne koden ved hver kjøring og
committer snapshotene til seg selv.

Retningen er et sikkerhetsvalg: et privat repo som leser offentlig kode
trenger ingen hemmelighet. Motsatt vei ville krevd et token med
skrivetilgang liggende tilgjengelig for et repo hvem som helst kan lese.

Vil du kjøre innsamlingen lokalt:

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data python run.py

Uten miljøvariabelen skrives det til `data/` her, som er gitignorert.
