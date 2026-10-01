---
dato: 2026-10-01
tittel: Forfall måles i ISO-uker for ukentlige kilder, ikke i dager
status: utkast
commit: [fylles inn]
---

# Forfall per ISO-uke

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt 1: en ukentlig kilde er forfalt når uka mangler, ikke når sju dager har gått

`core/runner.velg_forfalte()` måler forfall i ISO-UKER for kilder med
`min_dager_mellom == 7`. Kilden er forfalt hvis `sist_ok` ligger i en
tidligere ISO-uke enn kjøredatoen. Andre kadenser teller dager som før.

Dagtellingen drev kilden framover i uka, én dag per redning. Målt i
datarepoet, alle verdier av `biomasselag.sist_ok` siden kilden ble
bygget:

    commit     kjøring              sist_ok           ISO       dager
    ────────────────────────────────────────────────────────────────
    a45596a5   man 14.09 10:24      (kilden mangler i health.json)
    20ec6107   tir 15.09 21:58      2026-09-15 tir    2026-W38
    cdaf1f9e   man 21.09 10:29      2026-09-15 tir    2026-W38      6
    b3e80ea5   tir 22.09 21:52      2026-09-22 tir    2026-W39      7
    457ecfc3   man 28.09 11:32      2026-09-22 tir    2026-W39      6
    748d4044   tir 29.09 22:52      2026-09-22 tir    2026-W39   feil
    767bfb67   tor 01.10 19:12      2026-09-22 tir    2026-W39   feil

Tirsdagsankeret ble satt av F15s mekanisme: kilden ble commitet mandag
14.09 kl. 10:22, og mandagskjøringen startet 10:24. Den kjørte på det
som var PUSHET, og `biomasselag` sto ikke i health.json etterpå — nøkkelen
ble født tirsdag 15.09.

Fra da av: mandag er 6 dager etter forrige tirsdag, 6 < 7, ikke forfalt.
Tirsdagens gjenkjøring tok kilden hver uke og satte `sist_ok` til en ny
tirsdag. Mandagen kom aldri til.

**Følgen er at gjenkjøringen sluttet å være en reserve.** Den var det
ENESTE forsøket i uka, og et eneste forsøk har ingen reserve igjen når
det feiler. Tirsdag 29.09 var kilden forfalt, og da svarte endepunktet
500. Uke 40 har ikke noe biomasselag-snapshot, og en uke som er forbi kan
ikke hentes (regel 5).

Ukeregelen spør om det vi faktisk vil vite — har vi ukas snapshot — i
stedet for om noe som korrelerer med det. Mandag henter da alltid alt, og
tirsdag blir en ekte reserve: en kilde som lyktes mandag er ikke forfalt
tirsdag, og en som uteble er det.

Den fanger også årsskiftet, som dagtellingen ikke kunne se: tirsdag
29.12.2026 (2026-W53) til mandag 04.01.2027 (2027-W01) er 6 dager, og
uke 1 skulle hentes.

## Bestemt 2: uka leses av `observed_at`, og ingen klokke slås opp

`velg_forfalte()` regner ISO-uka av datostrengen den får inn. Den slår
ikke opp klokka, og den slår ikke opp en tidssone.

Oppgaven ba om «inneværende ISO-uke (Europe/Oslo)». Kjøredatoen slås opp
nøyaktig ett sted — `run.py`, i UTC — og et andre oppslag i en annen sone
er F6/F7 om igjen: to svar som kan være uenige rundt midnatt, og da får
fila navn etter én uke og innhold fra en annen. Hvilken sone kjøredatoen
leses i er `run.py`s sak, og den står urørt her.

I praksis er valget uten virkning for de planlagte kjøringene: mandag
05:00 UTC og tirsdag 19:00 UTC ligger i samme ISO-uke i begge soner. De
to kan bare skille lag for en kjøring mellom 00:00 og 02:00 norsk tid.
**Skal kjernen bli Oslo-basert, er det `run.py:264` som endres** — og den
datoen mater `gjelder_for()` i alle kilder, altså `observed_at`, arkivnavn
og snapshot-filnavn. Det er en annen beslutning enn denne.

## Bestemt 3: framtidig `sist_ok` holder fortsatt kilden igjen

Sammenligningen er «`sist_ok` ligger i en TIDLIGERE uke», ikke «ulik uke».
De to er bare uenige når `sist_ok` ligger i framtida, og der skal vakten
holde igjen som før: en health.json med klokkerot er ikke et argument for
å hente på nytt. Invarianten er eldre enn denne beslutningen og har sin
egen test (`test_kjoretidspunkt_fram_i_tid_gir_ikke_ny_kjoring`).

Fallback-retningen er ellers uendret: ukjent eller ulesbar `sist_ok` gir
forfalt. En uke som ikke hentes kan ikke hentes igjen, mens en henting
for mye er en fil med løpenummer.

## Bestemt 4: kadensen stemples i health.json

`min_dager_mellom` skrives på hver post i `data/health.json`, for ALLE
registrerte kilder ved hver kjøring — også kilder som ikke var forfalte
og kilder som feilet.

Tilsynet i datarepoet skal feile onsdag når en ukentlig kilde mangler
ukas snapshot, og det må vite hvilke kilder som er ukentlige. Kadensen er
erklært på kilden, altså i kodrepoet. De to andre veiene dit ble
forkastet:

- **Tilsynet henter kodrepoet.** Gir dead man's switchen to nye feilmåter
  den ikke har i dag — utløpt token og feilende pip. En vakt som blir rød
  av noe annet enn det den vakter, blir mutet, og en mutet dead man's
  switch er verre enn ingen. `tilsyn.yml` leser med vilje ÉN fil.
- **Lista hardkodes i tilsynet.** En andre sannhet om kadensen, som
  driver stille: en ny ukentlig kilde blir ikke vaktet, en kilde som
  bytter kadens blir feilvaktet. CLAUDE.md 1b-2.

health.json er kanalen som allerede finnes — kodrepoet skriver den,
datarepoet eier den. Ingen ny avhengighet mellom repoene, og kilden er
fortsatt eneste eier av tallet. Dette er 1b-3: verdien som avgjør om en
manglende uke er en FEIL eller helt normalt, lagres sammen med dataene.

Alle kilder og ikke bare dagens resultater, fordi en kilde som ikke
kjørte er nettopp den tilsynet skal se. Kadensen er en ERKLÆRING fra
kilden, ikke en måling av kjøringen, så den er like sann for en kilde som
ikke kjørte. `--historisk` rører fortsatt ikke health.json.

## Bestemt 5: et manglende kadensfelt er en feil med navn

I `.github/tilsyn.py` behandles en kilde uten `min_dager_mellom` som en
feil som navngir kilden — samme retning som `sist_ok: None` gir forfalt.
Alternativet er at kontrollen tier om nøyaktig de kildene den ikke kan
lese, og en vakt som blir stille av manglende data er den feilmodusen
`tilsyn.py` finnes for å hindre.

## Bestemt 6: varseltekstene sier «kjøring» der de teller kjøringer

`feil_paa_rad` og `volum_lavt_paa_rad` går opp én gang per KJØRING som
ser problemet, og det er ikke én per uke: mandag og tirsdag er to, en
manuell kjøring er en tredje. «uke 3» om tre kjøringer samme uke sier at
bruddet har stått i tre uker.

`samle.yml` påsto i tillegg «Denne uka har ikke noe fullstendig snapshot»
også når én av elleve kilder feilet. `run.py` skriver nå `mangler` til
`GITHUB_OUTPUT`, og workflowen navngir kildene i stedet for å påstå mer
enn den vet. Tom verdi er «vet ikke», ikke «ingen feilet» — skillet gjøres
på `outcome` ved siden av.

## Hvorfor

<!-- Skrives av Heine. -->

## Hva som ville snudd det

<!-- Skrives av Heine. -->
