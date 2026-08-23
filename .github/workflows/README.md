# Workflows

`test.yml` kjører testsuiten på hver push og PR. Den bor her.

**Innsamlingen bor ikke her.** Den ligger i det private datarepoet
`havbruk-radar-data`, som henter denne koden ved hver kjøring og
committer snapshotene til seg selv.

Begge repoene er private. Datarepoets `samle.yml` gjør derfor checkout av
DETTE repoet med `secrets.KODE_REPO_TOKEN` — `GITHUB_TOKEN` gjelder bare
repoet en workflow bor i. Uten tokenet svarer GitHub «Repository not
found» (404, ikke 403), og feilen ser ut som et feilstavet reponavn.

Retningen er fortsatt et sikkerhetsvalg, men ikke det som sto her før.
Begrunnelsen var «et privat repo som leser offentlig kode trenger ingen
hemmelighet», og den falt da dette repoet ble lukket 18.08.2026. Det som
står igjen, og som er det egentlige argumentet: tokenet i datarepoet
trenger bare LESETILGANG til kode. Motsatt vei ville krevd et token med
skrivetilgang til historikken, og historikken er den ene tingen som ikke
kan hentes på nytt.

Vil du kjøre innsamlingen lokalt:

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data python run.py

Uten miljøvariabelen skrives det til `data/` her, som er gitignorert.
