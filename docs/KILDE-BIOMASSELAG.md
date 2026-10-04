# Biomasselag — endepunkter og feltlister

Kildens hovedbeskrivelse står i modulens docstring
(`sources/biomasselag.py`) og i `docs/beslutninger/2026-09-10-biomasselag.md`.
Dette dokumentet gjelder ENDEPUNKTENE: hvilke det er, hva hvert av dem
har av felt, og hva som er målt mot hva.

## 1. To endepunkter, ett lag

| rolle | URL | målt |
|---|---|---|
| primær | `https://gis.fiskeridir.no/server/rest/services/Yggdrasil/Biomasse/MapServer/0` | 10.09.2026, 02.10.2026 |
| reserve | `https://gis.fiskeridir.no/server/rest/services/fiskeridirWMS_akva/MapServer/6` | 02.10.2026 |

Reserven brukes BARE når primæren feiler med HTTP-feil (status,
tidsavbrudd, tilkobling) eller et error-objekt i svaret. Fullstendighetsfeil
(`count` ≠ antall rader, `exceededTransferLimit` på en kort side, null
rader) utløser den ikke, og gjelder for begge.

Hvilket endepunkt som svarte, står på hver rad i snapshotet
(`endepunkt`, full URL) og i `health.json` (`endepunkt`). Brukes reserven,
legger kilden en advarsel — `biomasselag: reserve fiskeridirWMS_akva/6
(primær: code 500)` — som havner i `advarsler_sist` i health.json og i
KREVER TILSYN i jobben.

### Hvorfor reserven er samme lag — og hva som er ulikt

**Bekreftet 02.10.2026 03:52 UTC**, mot arkivet
`data/arkiv/biomasselag/2026-09-22.json.gz` (sha256 `8ce65772…`, 1128
rader). Råsvarene ligger utenfor repoet, med sha256, og er ikke arkivert.

- Lagbeskrivelsen er ordrett lik, `copyrightText` er «Fiskeridirektoratet»,
  `maxRecordCount` er 2000.
- 1127 rader, 1118 `loknr`. Mot arkivet: 1118 felles, 0 bare i den ene.
- Av 1108 lokaliteter med én rad begge steder: 4 ulik `har_fisk`, 4 ulik
  `art`, 14 ulik `siste_rapport`. Ingen `siste_rapport` etter 2026-08-31.
  Forskjellene er forenlige med at reserven viser en NYERE tilstand enn
  arkivet — sene augustrapporter — men to rader gikk BAKOVER
  (10726, 10747: 2026-08-31 → 2026-07-31). Hvorfor, er ikke kjent.
- **`objectid` er tildelt på nytt for 720 av 1108 lokaliteter.** Den er
  ingen nøkkel på tvers av hentinger. Ukesammenligningen bruker
  `(loknr, felt)`, og `objectid` emitteres ikke — se
  `tests/test_biomasselag.py`, «ukesammenligningen: nøkkel».

**Ikke bekreftet:** at de to endepunktene leser samme database. Det er
sannsynlig — samme beskrivelse, samme loknr-mengde, og primærens
metadata svarer fortsatt med 16 felt som alle finnes i reserven — men
primærens `/query` svarte ikke 02.10, så samme tilstand på samme tidspunkt
er ikke målt.

## 2. Feltene vi henter — like for begge

`FELTER`: `objectid`, `loknr`, `navn`, `status_lokalitet`,
`siste_rapport`, `har_fisk`, `art`. Samme navn og samme typer i begge lag.

## 3. KJENTE_UTELATTE per endepunkt

Skjemakontrollen er per endepunkt: hvert lag sammenlignes mot sin egen
liste, og et felt som verken hentes eller står der gir en advarsel.

### Primær — `KJENTE_UTELATTE` (16 felt totalt)

`symbol1`, `kapasitet_lok`, `aktuell_kapasitet`, `plassering`,
`vannmiljo`, `fylke`, `kommune`, `produksjonsomraade`, `shape`.
Begrunnelsen står i modulens docstring, «Hva som IKKE hentes».

### Reserve — `KJENTE_UTELATTE_RESERVE` (23 felt totalt, 22 uten `shape`)

De ni over, pluss sju som bare finnes i reserven. Verdiene er lest
02.10.2026 fra fem rader, ikke bare feltnavnene:

| felt | eksempel | hvorfor ikke hentet |
|---|---|---|
| `lokalitet` | `"13477 MEKJARVIK"` | `loknr` og `navn` slått sammen — ingenting nytt |
| `symbol2` | `0.0` | symbolisering, som `symbol1` |
| `vannmiljo_kode` | `"Salt"`, `"Mixed"` | `akvakultur.vanntype` har det |
| `fylkeskode` | `"11"` | `akvakultur.fylke` har det, og raden er fryst ved siste rapport |
| `kommunenr` | `"1127"` | som `fylkeskode` |
| `lat` | `59.022` | geometri; `akvakultur` har posisjonen. Samme valg som `romming` |
| `lon` | `5.618` | som `lat` |

Ingen av de sju er persondata. Ingen av dem er heller en opplysning
`akvakultur` ikke allerede har, og grunnen fra docstringen gjelder dem
like mye: hele raden er fryst ved siste rapport, så en kopi herfra ville
vært en DÅRLIGERE kopi.

## 4. Hva som ikke er undersøkt

- Om reserven kan ha et annet `maxRecordCount` i framtida enn primæren.
  Pagineringen og `_arcgis.sjekk_avkorting` er de samme for begge, så
  et senket tak gir en feil, ikke stille avkorting.
- Om Geonorge-nedlastingen («Akvakultur – lokaliteter», GML med
  `<app:biomasse>`) kunne vært en tredje vei. Målt 02.10.2026: den har
  `har_fisk` som true/false og samme tilstand som reserven, men mangler
  `siste_rapport`, den faktiske arten og 44 lokaliteter. Ikke bygget.

## 5. Uke 40 (04.10.2026): første snapshot fra reserven

Kjøringen 04.10.2026 21:03 UTC (datarepoet `8b80cb8`, merket DELVIS
fordi en vakt ba om tilsyn) skrev `raw/biomasselag/2026-10-04.parquet`
fra reserven: 1127 rader, 1118 lokaliteter, 7358 observasjoner,
`raw_hash` `6351f631…` (sha256 av den dekomprimerte kroppen i
`arkiv/biomasselag/2026-10-04.json.gz`).

Siste snapshot fra primæren er `2026-09-22` (`raw_hash` `069abea8…`). Den
kolonnen `endepunkt` fantes ikke da; at det var primæren er utledet av at
reserven ikke fantes i koden før 02.10, ikke lest av raden.
`2026-09-15` og `2026-09-22` har BYTE-LIK kropp — primæren sto stille den
uka.

### 10726 og 10747 felt for felt

Fra arkivkroppene. Radhash er sha256 av raden som JSON med sorterte
nøkler, avkortet til 12 tegn.

| loknr | kropp | endepunkt | siste_rapport | objectid | radhash |
|---|---|---|---|---|---|
| 10726 | 2026-09-10 | primær | 2026-07-31 | 1636256 | `b2e8e9e0d601` |
| 10726 | 2026-09-15 | primær | 2026-08-31 | 1637008 | `bc5a0c87f87f` |
| 10726 | 2026-09-22 | primær | 2026-08-31 | 1637008 | `bc5a0c87f87f` |
| 10726 | 2026-10-04 | reserve | **2026-07-31** | 1641538 | `14e51163bccb` |
| 10747 | 2026-09-10 | primær | 2026-08-31 | 1635633 | `318aa98296e2` |
| 10747 | 2026-09-15 | primær | 2026-08-31 | 1637384 | `396249d3c474` |
| 10747 | 2026-09-22 | primær | 2026-08-31 | 1637384 | `396249d3c474` |
| 10747 | 2026-10-04 | reserve | **2026-07-31** | 1642025 | `e195579dfe35` |

Alle andre felt er like i alle fire: `art` Laks, `har_fisk` Ja,
`status_lokalitet` AKTIV, `navn` ULØYBUKT / FUTNES. Bare `siste_rapport`
(og `objectid`, som ikke er en nøkkel) skiller.

**Henger reserven etter? Ikke som lag.** Mot primæren 22.09, alle 1118
felles lokaliteter: 1103 lik `siste_rapport`, 13 FRAMOVER i reserven, 2
bakover (de to over). Nyeste `siste_rapport` er 2026-08-31 i begge, og
august har 672 lokaliteter i primæren mot 683 i reserven. Et lag som
hang etter som helhet ville vist det motsatte.

For de to lokalitetene ligger reserven én rapportmåned bak. I veggtid:
primæren hadde 2026-08-31 for 10747 senest 10.09 20:28 UTC og for 10726
senest 15.09 21:58 UTC; reserven har det ikke 04.10 21:03 — minst 24 og
19 dager. **Hvorfor er ikke avgjort**, og kan ikke avgjøres uten et
samtidig svar fra primæren. To forklaringer passer dataene:

- reserven har en eldre kopi av akkurat disse radene, eller
- augustrapporten er trukket eller rettet etter 22.09, og reserven er
  den FERSKESTE av de to.

At 13 rader gikk framover taler mot en generelt utdatert kopi, men
utelukker ikke at enkeltrader er det.

### Endringene mot 22.09: endepunkt eller ekte?

`changelog/biomasselag/2026-10-04.parquet`: 29 rader på 15 lokaliteter.

| felt | rader | |
|---|---|---|
| `siste_rapport` | 15 | 13 framover, 2 bakover (10726, 10747) |
| `antall_arter` | 5 | |
| `arter_tilstede` | 5 | 2 ny, 2 borte, 1 endret |
| `har_fisk` | 4 | 21495, 32397 Nei→Ja; 45072, 10821 Ja→Nei |

Det er samme 29 rader på samme 15 lokaliteter som ble målt live mot
reserven 02.10 (docs/beslutninger/2026-10-02-biomasselag-reserve.md
punkt 5). Reserven har ikke endret seg i disse lokalitetene mellom 02.10
og 04.10.

**Hvor mange skyldes byttet, kan ikke måles.** Det krever primær og
reserve på samme tidspunkt, og primærens `/query` har ikke svart på noe
tidspunkt reserven er hentet: feil 29.09, 01.10, 02.10 og 04.10
(se under). Vi har primær 22.09 og reserve 02.10/04.10 — ti til tolv
dager fra hverandre, og forskjellen er byttet og tida blandet.

Det som KAN sies, uten å være en måling:

- **2 rader er mistenkelige**: `siste_rapport` bakover kan ikke være en
  ny rapport. De er enten byttet eller en trukket rapport (over).
- **27 rader er forenlige med ekte endring**: datoer framover til
  2026-08-31, og `har_fisk`/`arter_tilstede`/`antall_arter` endrer seg
  bare på lokaliteter der `siste_rapport` også gikk framover. Forenlig er
  ikke bekreftet — en reserve som var FERSKERE enn primæren ville gitt
  nøyaktig samme mønster.
- Primæren sto stille 15.09 → 22.09 (byte-lik kropp). 13 sene
  augustrapporter mellom 22.09 og 02.10 er derfor ikke det man ville
  forventet av primærens egen takt, men heller ikke utelukket.

Forslag til hvordan det kan måles neste gang:
docs/FORSLAG-endepunkt-i-endringsloggen.md.
