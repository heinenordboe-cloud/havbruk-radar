# Målte funn, oktober 2026

Målt 08.10.2026 mot `havbruk-radar-data` (lokalt, ikke publisert).
Skriptene ligger i `analyse/maling_okt/`. Kropper og stikkprøver som ble
hentet levende, ligger i `/tmp/maling-okt/` og er ikke i git.

**Merkene:** MÅLT = holdt mot arkivkroppen (sha256 oppgitt). MÅLBAR =
lest i snapshot eller avledet, men ikke holdt mot en kropp, eller
regnestykke på målte tall. Hvert funn har én linje «Feil hvis».

## De tre sterkeste funnene

_(fylles inn når alle punktene er målt)_

---

## 1. Uke 41: +1 % kapasitet er forskriftens kapittel 3, ikke en hendelse i sjøen

**Antallet er 33, ikke «rundt 40».** Changeloggen for eierskap
2026-10-05 har 41 `kapasitet`-rader: 33 `endret`, 6 `ny` og 2 `borte`.
De 8 siste er nye og utgåtte tillatelser (5 TR-O for ODE AS, VL-B-0015
slaktemerd for EIDE BRANDASUND AS, 2 R-V settefisk for BIOCLEANFISH AS)
og har ingenting med økningen å gjøre.

**F1.1 — MÅLT.** 33 tillatelser fikk kapasiteten økt mellom
eierskapskroppen for uke 40 og uke 41, og for alle 33 er ny kapasitet
nøyaktig `round(gammel × 1,01)` i hele tonn MTB.
Kilde: Fiskeridirektoratet pub-aqua `/licenses`, snapshot `eierskap`
2026-09-28 og 2026-10-05.
Kropper: `arkiv/eierskap/2026-09-28.json.gz`
sha256 `6e677a6024ee8665a366ed8f5efc356eb56c1ace2a857034a839162ac4c88b02`,
`arkiv/eierskap/2026-10-05.json.gz`
sha256 `581bca616e7d0b7706524cf6323e956a9dfbb4c99c9c77b1671f3aab2a171c11`
(lik `raw_hash` i snapshotene).
Feil hvis: tillatelser eid av privatpersoner, ENK eller sektor 2300 også
fikk økningen. De fjernes i `fetch()` før arkivering (93 i begge
kroppene), så de kan verken telles eller utelukkes fra arkivet.

| PO | selskap | orgnr | tillatelser | tonn økt | KOMM-MATF i PO |
|---|---|---|---:|---:|---:|
| 1 Svenskegrensen–Jæren | MOWI SEAWATER NORWAY AS | 921668236 | 23 | 212 | 26 |
| 12 Vest-Finnmark | MOWI SEAWATER NORWAY AS | 921668236 | 2 | 36 | 94 |
| 13 Øst-Finnmark | LERØY AURORA SJØ AS | 930155179 | 8 | 91 | 16 |
| **sum** | 2 selskaper | | **33** | **339 t** | 136 |

Alle 33 er `KOMM-MATF`, `MTK`, `TN`. Siste kolonne er antall kommersielle
matfisktillatelser i kroppen med samme PO. Det er grunnlaget den
avledede andelen hviler på: 23 av 26 i PO 1 og 2 av 94 i PO 12.

**F1.2 — MÅLT.** Mønsteret har ikke forekommet før i vår
eierskapsserie: kroppene 02.09, 14.09, 21.09 og 28.09.2026 har null
kapasitetsendringer mellom seg.
Kilde: samme, kroppene
`0c3525ca…` (14.09), `22142f87…` (21.09), `6e677a60…` (28.09).
Feil hvis: noen leser dette som at det ikke har skjedd før i
virkeligheten. Serien har fire uker. `eierskap_historikk` har ikke noe
kapasitetsfelt (felter: `mottaker_*`, `journal_*`, `tillatelse_nr`,
`rekkefolge`, `dato_forbehold`) og kan ikke svare på spørsmålet.

**F1.3 — MÅLT.** Lokalitetskapasiteten (`capacity` på `/sites`) flyttet
seg ikke for noen lokalitet mellom uke 40 og 41. Økningen ligger bare på
tillatelsen.
Kilde: akvakultur, `arkiv/akvakultur/2026-10-05.json.gz` mot
`2026-09-28.json.gz`.
Feil hvis: lokalitetsklareringen oppdateres med etterslep. Da kommer den
i en senere uke, og det er verdt å se etter.

**F1.4 — MÅLT. Forskriften er funnet:** *Forskrift om
kapasitetsjusteringer for tillatelser til akvakultur med matfisk i sjø
av laks, ørret og regnbueørret i 2026* (FOR-2026-08-20-1764), kapittel 3,
§ 7: tilbud om å øke tillatelseskapasiteten «med 1 prosent» mot
vederlag, avrundet til nærmeste hele tonn. Etter § 3 gjelder kapittelet
bare de grønne områdene PO 1, 12 og 13, og det er nøyaktig de tre
områdene de 33 ligger i. Vederlaget er 270 000 kr per tonn (§ 10), og
søknadsfristen var 28. september 2026 (§ 11). Uke 41 er første henting
etter fristen.
Kilde: Lovdata via `trafikklysvedtak`, `arkiv/trafikklysvedtak/2026-12-31.bin.gz`
sha256 `08b6090d993b96444ba54043079382de2a25750f571b7b98414158bc7abc4cd8`,
`published_at` 2026-08-20.
Feil hvis: økningen har en annen hjemmel som tilfeldigvis også gir 1 %
i de samme tre områdene. Kroppen viser bare at tallet er endret, ikke
vedtaket bak det.

**F1.5 — MÅLBAR.** Med forskriftens pris tilsvarer 339 tonn
**91,53 mill. kr** i vederlag til staten. Det er et regnestykke, ikke et
betalingstall: § 10 sier at økningen faller bort hvis vederlaget ikke er
betalt, så registreringen tyder på betaling, men viser den ikke.

**F1.6 — MÅLT. Samme ordning har stått i hver
kapasitetsjusteringsforskrift siden 2017.** Grønne områder og pris har
skiftet:

| forskrift | økning | kr/tonn | frist | områder |
|---|---|---:|---|---|
| FOR-2017-12-20-2397 | 2 pst. | 120 000 | 31.01.2018 | 1, 7, 8, 9, 10, 11, 12, 13 |
| FOR-2020-02-04-105 | 1 prosent | 156 000 | 25.02.2020 | 1, 2, 6, 7, 8, 9, 11, 12, 13 |
| FOR-2022-06-07-972 | 1 prosent | 200 000 | 28.06.2022 | 1, 6, 8, 9, 10, 11, 12, 13 |
| FOR-2024-03-22-515 | 1 prosent | 170 000 | 17.04.2024 | 1, 9, 10, 11, 12, 13 |
| FOR-2026-08-20-1764 | 1 prosent | 270 000 | 28.09.2026 | 1, 12, 13 |

Kilde: `arkiv/trafikklysvedtak/`, sha256 `9dd38abd…` (2018),
`0ac5a328…` (2020), `31f1b88e…` (2022), `5184ac61…` (2024),
`08b6090d…` (2026). Fulle hasher står i skriptets utskrift.
Feil hvis: Lovdata-sida viser gjeldende tekst og ikke teksten slik den
ble vedtatt. Kroppene er hentet 05.–15.09.2026. En senere endring av en
eldre forskrift ville stå i kroppen uten å skilles fra den opprinnelige.

Merk at 2026-forskriften har det smaleste grønne utvalget i serien. Den
tilsvarende økningen i 2020, 2022 og 2024 ligger før eierskapsserien
starter og kan ikke måles med våre data.

`analyse/maling_okt/p1_kapasitet_uke41.py`

---

## 2. BarentsWatch `liceTreatments/{year}`: IKKE MÅLT, bare kartlagt i dokumentasjonen

**Kroppene er ikke hentet.** `BARENTSWATCH_CLIENT_ID` og `-SECRET` finnes
bare som Actions-secrets i datarepoet og er ikke satt i dette skallet.
Skriptet `analyse/maling_okt/p2_licetreatments.py` er klart og feiler
rødt på manglende nøkkel, slik `Tilgang` skal. Med nøklene i miljøet
henter det 2025 for 11116, 13284 og 45087 til `/tmp/maling-okt/p2/` og
skriver ut sha256 og hver feltsti som har verdi. Lokalitetene er de med
flest uker `har_mekanisk_fjerning=True` i 2025 (33, 29 og 25).

**F2.1 — MÅLT, men bare mot dokumentasjonen.** BarentsWatchs egen
OpenAPI-spesifikasjon dokumenterer at `liceTreatments/{year}` svarer med
`AllTreatmentsGraphDataDto`: `localityNo`, `year` og `data[]` per
**uke**. Hvert ukeelement har:

| felt | innhold ifølge spesifikasjonen |
|---|---|
| `week` | ukenummer. **Ingen dato innen uka.** |
| `medicinalTreatments[]` | `name` (virkestoff eller «Other»), `substanceId`, `type` («InFeed»/«Bath»), `entireLocality`, `numberOfCages` |
| `nonMedicinalTreatments[]` | `type` ∈ TERMISK / MEKANISK / FERSKVANNS / ANNEN_BEHANDLING, `doneBeforeLiceCount`, `entireLocality`, `numberOfCages` |
| `combinationTreatments[]` | lister av begge typene over |
| `cleanerFishTreatments[]` | `name` (art), `quantity`, `entireLocality` |
| `mechanicalRemoval`, `mechanicalRemovalEntireLocality` | boolske |
| `version` | heltall |

`liceMedicationEvents/{year}` peker på samme skjema. Det finnes også et
skjema `LiceReport.Treatment` med `startDate`/`endDate` (date-time) og
`TreatmentDetail` med `quantity`, `concentration` og `substance`. Ifølge
spesifikasjonen brukes det **ikke** av `liceTreatments`.
Kilde: `https://www.barentswatch.no/bwapi/openapi/fishhealth/openapi.json`,
hentet 09.10.2026 00:10 UTC, 682 325 byte,
sha256 `0ee19dc69687b7bd00694333ee34b58f91d632524d5088427804f819fa78a8fc`
(i `/tmp/maling-okt/p2/`).
Feil hvis: svaret avviker fra spesifikasjonen. Responsen er dokumentert
som `text/plain`, og det er nettopp et felt som må sees i en kropp
(CLAUDE.md regel 4).

**Svaret på spørsmålet, så langt det kan gis uten kropp:** etter
dokumentasjonen gir endepunktet **behandlingstype** (termisk, mekanisk,
ferskvann, fôr eller bad, og virkestoff), **antall merder** og
**rensefiskart med antall**. Det gir **ikke dato** utover uke og år.
Den finere datoen (`startDate`) finnes bare i et skjema endepunktet ikke
bruker.

Det er relevant fordi flaggene vi har, er døde: i 2025 er
`har_medikamentell_behandling` og `har_rensefisk` `True` i **0** uker for
alle lokaliteter, mens `har_mekanisk_fjerning` lever (MÅLBAR, lest i
snapshotene `lusetall/2025-*.parquet`; se også
`docs/beslutninger/2026-09-01-lusetall-to-felter-er-datatap.md`).

---

## 3. Tillatelseshandel 08.10.2025–08.10.2026 per produksjonsområde

**Vinduet er journalføringsdato i [2025-10-08, 2026-10-08).** Bare
overføringer der **både kjøper og selger** er AS eller ASA
(`LimitedLiabilityCompany`, `PublicLimitedCompany`, `AS`, `ASA`) er med.
Persondatafilteret går på begge parter. En part med personform, uten
ni-sifret nummer eller med ukjent form holder hele overføringen utenfor,
og navnet skrives aldri ut. Selgeren er forrige mottaker i kjeden, eller
den opprinnelig tildelte for kjedens første overføring. Kildene har
ingen avgiver, så selger er avledet (se `docs/KILDE-EIERSKAP.md` punkt 4).

### Dekning per ledd

| ledd | kilde | dekker | inn | ut |
|---|---|---|---:|---:|
| A | `arkiv/eierskap-overforinger/` (3029 kropper) | journalført til `ajourDate` 31.08.–02.09.2026 | 134 | 2 (selger uten ni-sifret nummer/person) |
| B | `arkiv/eierskap/` 02.09 → 05.10.2026 | eierskifte mellom ukekropper | 1 | 20 nye tillatelser uten selger |
| — | ingenting | 05.10–08.10.2026 | — | — |

* **Ledd A:** 136 overføringer i vinduet, 134 med. 7 parter manglet
  form i våre kropper. De ble slått opp hos Brreg **i minnet** med
  kildens egen `brreg_form()`, og alle 7 svarte `ok` med selskapsform.
  Ingenting ble skrevet.
* **Ledd B** ser bare tillatelser som står i begge kroppene. Kroppene er
  allerede personfiltrert, så et skifte fra eller til en personeier er
  usynlig.
* **Kapasitet og PO er DAGENS** (eierskapskroppen 05.10.2026), ikke
  verdien på overføringsdagen. PO er tillatelsens egen `prodAreaCode`.
  For 4 overføringer er PO tatt via aktiv lokalitet i akvakultur
  05.10.2026 (sha256 `b415394a…`), merket «via lokalitet». 80 overføringer
  har ingen PO. Det er torsk, settefisk, stamfisk, slakt og andre arter
  utenfor PO-ordningen (se 3.3). 1 tillatelse (SF-H_-0019) står ikke i
  noen eierskapskropp og mangler kapasitet.

**F3.1 — MÅLT.** I vinduet ble **135 overføringer** mellom selskaper
journalført, fordelt på **40 journalnumre**, **33 kjøpere** og
**34 selgere**. Av dem gjelder **55 overføringer (9 journalnumre)**
tillatelser i et produksjonsområde.
Kilde: Fiskeridirektoratet pub-aqua `/licenses/{nr}/transfers`. 3029
kropper, sha256 for hver i `/tmp/maling-okt/p3/overforinger-sha256.txt`,
sha256 over den lista
`19f8473a52888ceed8343a6125a98b273b6cfeef3fb28740743b7eeef4a8eda4`.
Pluss eierskapskroppene `6b22413510b5…` (02.09) til `581bca616e7d…`
(05.10).
Feil hvis: `journalDate` ligger langt fra overdragelsen. Datoen er
udokumentert og skal leses «senest da». Eller hvis en kjede mangler et
ledd, slik at «forrige mottaker» ikke er den som faktisk solgte.

### 3.1 Per produksjonsområde (laks, ørret, regnbueørret i sjø)

Kapasitet i tonn MTB (TN), dagens verdi, summert bare innen PO og enhet.

| PO | overf. | journalnr | kjøper ← selger | tillatelser | TN |
|---|---:|---:|---|---:|---:|
| 2 | 10 | 1 | NORDSJØ FJORDBRUK AS ← ROGALAND FJORDBRUK AS | 10 | 7 661 |
| 5 | 1 | 1 | SALMAR OPPDRETT AS ← ØYLAKS MTB AS | 1 | 733 |
| 6 | 2 | 1 | SALMAR OPPDRETT AS ← HITRAMAT FARMING AS | 2 | 888 |
| 8 (via lok.) | 2 | 1 | BENCHMARK GENETICS NORWAY AS ← BENCHMARK GENETICS SALTEN AS (stamfisk) | 2 | 1 140 |
| 9 | 1 | 1 | ELLINGSEN SEAFOOD AS ← NORDLY INNOVATION AS | 1 | 100 |
| 10 | 5 | 2 | SALMAR OPPDRETT AS ← WILSGÅRD FARMING AS (3) / NOR SEAFOOD AS (2) | 5 | 4 870 |
| 11 | 5 | 2 | SALMAR OPPDRETT AS ← WILSGÅRD FARMING AS (3) / NOR SEAFOOD AS (2) | 5 | 4 890 |
| 12 | 27 | 1 | CERMAQ NORWAY SALMON AS ← CERMAQ FINNMARK FARMING AS | 27 | 26 249 |
| 12 (via lok.) | 2 | 2 | CERMAQ FINNMARK AS → CERMAQ FINNMARK FARMING AS → CERMAQ NORWAY SALMON AS (visning) | 1 | 780 |

PO 1, 3, 4, 7 og 13: ingen overføring mellom selskaper i vinduet.

**F3.2 — MÅLT.** **SalMar Oppdrett AS er kjøper i 4 av 9 områder**
(PO 5, 6, 10, 11): 13 tillatelser i fire transaksjoner. Wilsgård og
Nor Seafood går hver over både PO 10 og 11 under samme journalnummer
(2026000006 og 2025000214).
Kilde: som F3.1.
Feil hvis: journalnummeret ikke identifiserer én transaksjon.

**F3.3 — MÅLT, men ikke tolkbart som handel.** Den største flyttingen
(PO 12: 27 tillatelser og 26 249 TN, journalført 11.05.2026) går
mellom to selskaper med samme navnestamme, CERMAQ. Det samme gjelder
Benchmark Genetics i PO 8. Om dette er konserninternt, kan **ikke**
avgjøres med offentlige data (`docs/KILDE-EIERSKAP.md` punkt 6), og
tallet skal ikke stå alene som «kapasitet som skiftet eier».
Feil hvis: noen leser 26 249 TN som et oppkjøp.

### 3.2 Månedsfordeling (alle 135)

    2025-10   4    2026-01  32    2026-04   1    2026-07   3
    2025-11   5    2026-02   2    2026-05  36    2026-08   3
    2025-12  36    2026-03   5    2026-06   7    2026-09   1  (ledd B)

### 3.3 Utenfor PO-ordningen (80 overføringer, 32 journalnumre)

| type | enhet | overf. | kapasitet | kjøpere | selgere |
|---|---|---:|---:|---:|---:|
| KOMM-MATF (andre arter, mest torsk) | TN | 32 | 26 189,5 | 13 | 11 |
| KOMM-ALTKO | DA | 24 | 363 | 2 | 2 |
| KOMM-SETT | TN | 8 | 6 184,6 | 7 | 7 |
| KOMM-SETT | STK | 4 | 14 500 000 | 3 | 4 |
| KOMM-SETT | KG | 1 | 0 | 1 | 1 |
| SLAK-MATF | TN | 5 | 3 466 | 3 | 3 |
| KOMM-STAM | TN / KG | 3 / 1 | 490 / 500 | 2 / 1 | 2 / 1 |
| KOMM-AKRAS | DA | 1 | 11 | 1 | 1 |
| ukjent | — | 1 | — | 1 | 1 |

Største kjøpere i KOMM-MATF uten PO: ODE AS 10 (7 800 TN), NORCOD AS 5
(3 599 TN), CODLIFE AS 4 (3 120 TN). Full liste i
`/tmp/maling-okt/p3/kjopere.csv` og `selgere.csv`.

`analyse/maling_okt/p3_tillatelseshandel.py --brreg`
