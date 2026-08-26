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

Både `data/raw/<kilde>/<dato>.parquet` og
`data/changelog/<kilde>/<dato>.parquet` skrives én gang og røres aldri
igjen.

Changeloggen ble indeksert på DATO alene fram til 25.08.2026. Da var
datoen hele nøkkelen, og to kilder som gjaldt for samme dato kunne ikke
sameksistere — den andre skrivingen slettet den førstes rader.
`sjotemperatur` og `lusetall` har samme etterslep og deler dato, og
backfillen av den første tok 238 datoer fra den andre. Nøkkelen er
(kilde, dato) nå, som i `raw/`. Se `core/changelog.py` om F11.

De 761 filene som ble skrevet før omleggingen ligger flatt som
`data/changelog/<dato>.parquet`. De flyttes ikke — en skrevet fil røres
ikke — og `les_alt()` leser begge layoutene.

Grunnen er git, ikke minne. Komprimert parquet delta-komprimerer elendig,
så en fil som skrives om hver uke lagres som en ny nesten-full kopi hver
gang — repoet vokser kvadratisk i stedet for lineært. Målt over 104
simulerte uker: 1,9 MB mot 340 KB.

Analyselaget leser hele loggen med `changelog.les_alt()` og skal ikke
vite at den er delt i filer.

### Løpenummeret er ikke bare kollisjonshåndtering

`<dato>.2.parquet` fantes fra starten som svaret på «to skrivinger til
samme dato». Fra 25.08.2026 bærer det noe mer: for en kilde som
REVIDERER fortiden er `.2` en NY PÅSTAND om det samme tidspunktet, ikke
en gjentakelse av den gamle.

Fiskeridirektoratets biomassefil publiseres på nytt den 20. hver måned og
endrer tall tilbake til 2017. To snapshots som er uenige om mars 2018 er
begge sanne — de sier hva kilden sa på hver sin `fetched_at`. Append-only
er derfor ikke lenger bare en regel om repostørrelse her; det er det
eneste som bevarer at kilden har ombestemt seg, siden forrige versjon
forsvinner hos dem hver måned.

Changelog-fila får samme løpenummer som snapshotet, så
`2018-03-31.parquet` (bevegelse mot februar) og `2018-03-31.2.parquet`
(revisjon mot seg selv) lever side om side. Se `core/diff.revisjon()` og
CLAUDE.md 1b-5/1b-6.

### Og løpenummeret sier ikke lenger noe om rekkefølge

Fra 26.08.2026 sorteres versjoner av samme dato på `published_at` — da
KILDEN utga påstanden — og ikke på filnavnet. Grunnen er konkret:
Wayback-kopien av biomassefila ble skrevet inn den dagen, som `.2`, og
den er utgitt 20.07.2024 mens `.parquet` ved siden av er fra 2026.
Løpenummeret sier når VI skrev; `published_at` sier hvilken påstand som
avløste hvilken.

Det er tredje part i et tidspunkt, og den er ny: `observed_at` handler om
verden, `fetched_at` om oss, `published_at` om kilden. De to siste faller
sammen nesten — men bare når vi henter ferskt. Se CLAUDE.md 1b-7.

## Et snapshot bærer med seg hva det ba om

Hver rad har fire proveniensfelter kilden aldri rører: `fetched_at`,
`source_version`, `raw_hash` og `utvalg`. Det siste er søket kilden
faktisk gjorde — for Enhetsregisteret lista over næringskoder.

Grunnen er målt. Fram til 24.08.2026 lå den lista bare i `config.yml`
og i git-historikken, og da kan et snapshot fortelle hva vi FANT, men
ikke hva vi LETTE ETTER. Uka kodelista ble utvidet kom 908 selskaper
inn på én gang, og 25804 av ukas 26673 changelog-rader var dem — ikke
fordi noe skjedde i bransjen, men fordi luka vår ble større.

`diff.compare()` merker slike rader `utvalgsutvidelse`. De beholdes
(append-only), men `diff.bevegelse()` filtrerer dem bort før noe telles,
og ingen signalregel treffer dem. Se `core/utvalg.py` og
docs/beslutninger/2026-08-24-utvalgsutvidelse-er-ikke-endring.md.

Regelen bak, som gjelder enhver ny innstilling: **kan et snapshot alene
svare på hva verdien var da raden ble skrevet?** Kan det ikke det, hører
verdien hjemme på raden. Se CLAUDE.md 1b-3.

## Rekkefølgen i `run.py`

Diffen kjøres **før** dagens snapshot skrives. Skriver du først, finner
`snapshot.previous()` dagens egen fil og diffen blir tom. Det er den ene
subtile rekkefølgeavhengigheten i systemet, og den er verdt å huske.

## Volumvaktens referanse ligger i `health.json`, ikke i forrige snapshot

Volumvakten i `core/health.py` feller jobben når en kilde leverer
vesentlig færre observasjoner enn normalt — den stille feilen der et
feltnavn endres, `parse()` ikke finner det, og jobben likevel er grønn.

Den måler mot et referansenivå lagret i `health.json`: det siste
volumet som ble godkjent som friskt. Fristelsen er å regne det ut på
stedet i stedet, fra `snapshot.previous()`. Ikke gjør det. To grunner,
i rekkefølge etter hvor stille de feiler:

1. **Referansen ville flyttet seg med bruddet.** Måler du mot forrige
   snapshot, blir det ødelagte tallet neste ukes normal. Alarmen fyrer
   uken bruddet skjer og tier deretter, mens datatapet fortsetter — og
   det er nøyaktig feilmodusen `health.py` finnes for å hindre. Målt i
   simulering over fem uker med vedvarende brudd: rød i uke 3, grønn i
   uke 4 og 5. Et rullende snitt har samme feil, bare i sakte film.

2. **`health.oppdater()` kalles ETTER `snapshot.write()`** (steg 8 mot
   steg 5). Dagens fil ligger altså allerede på disk når vakten kjører.
   En `previous()`-basert vakt overlever bare fordi `previous()`
   filtrerer på strengt tidligere *dato* og dermed utelukker dagens
   `.N`-filer. Løsner den koblingen — f.eks. hvis noen lar `previous()`
   ta med samme dato for å få en «ferskere» baseline — sammenligner
   vakten dagen mot seg selv, får alltid 100 %, og dør uten et eneste
   feilsignal.

Kvitteringen for et reelt fall er `run.py --godta-volum <kilde>`, som
setter et nytt referansenivå. Commiten av `health.json` i datarepoet er
sporet: git log viser når nivået ble godtatt og hvorfor.

## Det som bevisst mangler

Ingen database, ingen kø, ingen orkestrator, ingen agenter. Systemet
kjører én gang i uka og feiler høyt når det feiler. Legg til kompleksitet
når du har et problem som krever det — ikke før.
