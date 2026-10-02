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
