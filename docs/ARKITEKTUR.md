# Hvorfor strukturen ser slik ut

Tre avgjørelser bestemmer nesten alt annet.

## 1. Skillet mellom `core/` og `sources/`

`core/` er infrastruktur og endres nesten aldri. `sources/` er der arbeidet
skjer og vokser hver måned. Grunnen til å skille dem hardt er at de har helt
ulik levetid: en kilde brekker når en etat bytter format, kjernen brekker bare
når du selv bestemmer deg for å endre den.

Testen på at skillet holder: kan du legge til en kilde uten å åpne `core/`?
Hvis svaret blir nei en dag, er det et signal om at kontrakten i
`contract.py` mangler noe — ikke at du skal gjøre et unntak.

## 2. Observasjonsformatet

Alle kilder normaliseres til `(entity_id, field, value, observed_at)`.
Det er nesten irriterende enkelt, og det er poenget. Alternativet er én
tabell per kilde, og da må diff-, signal- og dashbordlaget kjenne hver
enkelt kilde. Med ett format kjenner de null.

Prisen er at alt lagres som tekst og typing skjer i analysen. Det er en
god byttehandel når kildene er uforutsigbare.

## 3. To repo: kode offentlig, data privat

`havbruk-radar` er koden. `havbruk-radar-data` er historikken.

Registerdataene er NLOD-lisensiert og kan hentes av hvem som helst i
morgen. Det som ikke kan hentes i morgen, er snapshotet fra en gitt
mandag. Tid er den eneste ressursen som ikke lar seg kopiere i
etterkant — derfor ligger historikken privat, ikke tallene.

Innsamlingen kjøres FRA datarepoet, som henter denne koden ved hver
kjøring. Retningen er et sikkerhetsvalg: et privat repo som leser
offentlig kode trenger ingen hemmelighet. Motsatt vei ville krevd et
skrivetoken tilgjengelig i et repo hvem som helst kan lese.

`core/paths.py` er det eneste stedet datamappa defineres.
`HAVBRUK_DATA_DIR` overstyrer den.

## 4. Git som database

Ingen server, ingen migrasjoner, ingen drift. Én parquet per kilde per
kjøring, committet. Git gir versjonering og diff gratis og permanent.

Konsekvensen er at `data/` aldri skal i `.gitignore` i DATAREPOET —
dataene *er* det repoet. I kodrepoet er den derimot ignorert, slik at
en lokal kjøring ikke committer historikk til feil sted.

## Append-only, aldri omskriving

Både `data/raw/<kilde>/<dato>.parquet` og `data/changelog/<dato>.parquet`
skrives én gang og røres aldri igjen.

Grunnen er git, ikke minne. Komprimert parquet delta-komprimerer elendig,
så en fil som skrives om hver uke lagres som en ny nesten-full kopi hver
gang — repoet vokser kvadratisk i stedet for lineært. Målt over 104
simulerte uker: 1,9 MB mot 340 KB.

Analyselaget leser hele loggen med `changelog.les_alt()` og skal ikke
vite at den er delt i filer.

## Rekkefølgen i `run.py`

Diffen kjøres **før** dagens snapshot skrives. Skriver du først, finner
`snapshot.previous()` dagens egen fil og diffen blir tom. Det er den ene
subtile rekkefølgeavhengigheten i systemet, og den er verdt å huske.

## Det som bevisst mangler

Ingen database, ingen kø, ingen orkestrator, ingen agenter. Systemet
kjører én gang i uka og feiler høyt når det feiler. Legg til kompleksitet
når du har et problem som krever det — ikke før.
