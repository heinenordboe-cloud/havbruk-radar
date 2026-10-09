# Målte funn, oktober 2026

Målt 08.10.2026 mot `havbruk-radar-data` (lokalt, ikke publisert).
Skriptene ligger i `analyse/maling_okt/`. Kropper og stikkprøver som ble
hentet levende, ligger i `/tmp/maling-okt/` og er ikke i git.

**Merkene:** MÅLT = holdt mot arkivkroppen (sha256 oppgitt). MÅLBAR =
lest i snapshot eller avledet, men ikke holdt mot en kropp, eller
regnestykke på målte tall. Hvert funn har én linje «Feil hvis».

## De tre sterkeste funnene

**1. Uke 41 er forskriften, ikke markedet (F1.1 + F1.4).** 33
tillatelser, ikke «rundt 40», fikk nøyaktig `round(x × 1,01)` tonn MTB
mellom kroppene 28.09 og 05.10.2026. Alle ligger i PO 1, 12 og 13, og
det er nøyaktig de grønne områdene i kapittel 3 i FOR-2026-08-20-1764:
1 % mot 270 000 kr/t, søknadsfrist 28.09.2026. Bare to selskaper tok
tilbudet: MOWI SEAWATER NORWAY AS (25 tillatelser, 248 t) og LERØY
AURORA SJØ AS (8, 91 t).
*Hvorfor sterkest:* fire uavhengige kjennetegn stemmer uten ett unntak:
faktoren, avrundingen, områdene og tidspunktet rett etter fristen. Alt
er holdt mot tre arkivkropper med hash, og ordningen finnes i hver
forskriftsversjon siden 2017.

**2. Lusegrensa ligger allerede i arkivet, for hver lokalitet og uke
2012–2026 (F4.5).** `Lusegrense uke` og `Over lusegrense uke` står i hver
sjøtemperaturkropp i `data/arkiv/`. BarentsWatchs flagg er nøyaktig
`round(voksne_hunnlus, 2) >= Lusegrense uke` i **409 118 av 409 118**
uker, med 0,2 i ukene i april–juni fra 2017. `nettsted.py` sier at
grensa «ikke er samlet inn», og lusegrafen er tegnet uten den av den
grunn.
*Hvorfor sterkest:* null avvik på over 400 000 uker, målt mot kropper vi
allerede har. Funnet endrer hva nettstedet kan vise, uten én ny henting.

**3. `isFallow` er BarentsWatchs slutning, ikke en observasjon
(F4.2).** Feltet er identisk med «Trolig uten fisk» i alle 822 467 uker
der begge finnes. Indre brakkløp på nøyaktig 3 uker forekommer **0**
ganger, mot 231 på 4 uker. Produksjonsløp ender med høyst 3 uker uten
lusetall (3 unntak av 7 326). Hver syklus-, brakk- og
dekningsanalyse bygget på lusetall arver denne slutningen. Det samme
gjelder at `hasSalmonoids` er statisk (F4.1), og at rensefisk- og
medikamentflaggene er døde siden 2023-04 og 2024-11 (F4.6).
*Hvorfor sterkest:* likheten er eksakt, og 0-gapet ved 3 uker er et
strukturelt fingeravtrykk som tilfeldig rapportering ikke gir.
Konsekvensen gjelder alt videre arbeid med syklusene. Selve «4 uker
uten rapport»-regelen er en hypotese og ikke bekreftet.

Svakere, og hvorfor: punkt 2 er bare kartlagt i dokumentasjonen
(nøklene mangler lokalt). Punkt 3 domineres av en Cermaq-intern flytting
som ikke kan skilles fra et oppkjøp. 96,1 % enighet med biomasselaget
(F4.4) er solid, men gjelder bare én måned.

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

---

## 4. Produksjonssyklusen per lokalitet 2012–2026 fra lusetall

**Panelet er bygget direkte fra arkivkroppene, ikke fra snapshotene:**
767 lusetallkropper (`arkiv/lusetall/*.json.gz`) og 767
sjøtemperaturkropper (`arkiv/sjotemperatur/*.txt.gz`, BarentsWatchs
CSV-eksport for samme uke), 2012-01-02 til 2026-09-07. Det gir
1 327 334 lokalitetsuker for 2706 lokaliteter. sha256 for hver kropp står
i `/tmp/maling-okt/p4/kropper-sha256.txt`, og sha256 over den lista er
`67bf9365fb1d96ece3185feb2c2b78050c2c16f75a31a19015ccaecb0b104dcd`.
Siste uke: lusetall `f4543c20…`, sjøtemperatur `61eab555…`.
Alt under er derfor MÅLT mot kropp. Der en regel er valgt av oss, står
det.

### 4a. Grenseregelen, og hva den hviler på

Tre egenskaper ved feltene avgjør regelen. Alle tre er målt:

**F4.1 — MÅLT. `hasSalmonoids` (lagret som `har_laksefisk`) er en
lokalitetsegenskap og ikke «fisk i sjøen nå».** Bare 79 av 2706
lokaliteter skifter verdi i løpet av 14 år, til sammen 88 ganger.
Eksempel: 10029 går `True → False` 2020-05-18 og tilbake uka etter.
Feltet kan derfor ikke markere en syklusgrense. Det brukes bare til å
avgrense universet.
Feil hvis: BarentsWatch har tolket feltet annerledes tidligere i serien.
Da gjelder målingen bare slik feltet står i dagens kropper.

**F4.2 — MÅLT. `isFallow` er BarentsWatchs egen slutning «Trolig uten
fisk».** De to er like i alle 822 467 lokalitetsuker der begge finnes
(`True`=«Ja» 390 827, `False`=«Nei» 431 640). Mønsteret tyder på at
slutningen bygger på manglende rapportering:
* Et indre brakkløp på **nøyaktig 3 uker forekommer 0 ganger**. Det er
  32 av 1 uke, 13 av 2 uker og **231 av 4 uker**.
* Av 7 326 avsluttede produksjonsløp ender 6 155 med en rapportert uke
  rett før brakk. Resten ender med 1, 2 eller 3 uker uten lusetall (561,
  392 og 215). Bare 3 ender med 4.

At regelen er «4 uker uten rapport → brakk», er en **hypotese, ikke
bekreftet**. Den er forenlig med tallene, men BarentsWatch dokumenterer
den ikke.
Feil hvis: BarentsWatch setter flagget fra innrapportert «ingen fisk».
Da er 0-gapet ved 3 uker en tilfeldighet, noe 7 326 løp gjør lite
sannsynlig.

**Regelen** (`analyse/maling_okt/p4_sykluser.py`):

    UNIVERS    hasSalmonoids & !isOnLand & !isSlaughterHoldingCage
               (788 055 lokalitetsuker, 1 412 lokaliteter;
                slaktemerd utelatt: 34 405 uker)
    PRODUKSJON isFallow == False
    SYKLUS     sammenhengende produksjonsuker; brakkavbrudd på 1–2 uker
               bygges over (ingen 3-ukers finnes, så grensa er målt);
               hull i serien bryter
    KANT       uker uten lusetall i starten eller slutten av en syklus
               trimmes bort: fisken kan ha vært borte
    KORT       < 4 uker etter trimming = tvetydig kort løp
    SENSUR     berører seriens første/siste uke eller et hull

**Tvetydige mønstre, listet:**

| mønster | antall | eksempel | behandling |
|---|---:|---|---|
| brakkavbrudd 1–2 uker mellom to produksjonsløp | 45 | 17357 fra 2017-02-13 | bygget over |
| uker uten lusetall i kanten av en syklus | 2 069 uker | 10041 2015-05-25–06-08 | ikke tilordnet |
| løp kortere enn 4 uker | 466 løp / 739 uker | 10194 2012-09-10 (3 uker) | ikke tilordnet |
| produksjonsløp uten én eneste lusetelling | 81 (75 på 1 uke) | — | blir korte løp |
| brakkuker MED lusetall | 54 | 10281 2025-05-05 (0,0 lus) | regnet som brakk |
| hull i serien (uke mangler i kroppen) | 71 i 67 lokaliteter | — | bryter syklusen, sensur |
| svært lange sykluser > 130 uker | 19 | 11116 2014-06-09–2021-05-31 (365 uker) | beholdt. Trolig overlappende generasjoner uten brakk |
| `hasSalmonoids` skifter | 88 skift | 10029 2020-05-18 | bare universavgrensning |

**F4.3 — MÅLT (med regelen over).** **7 845 sykluser** i universet. Av
dem er **6 485 hele** (ikke korte, ikke sensurert), 466 korte, 326
sensurert i starten og 569 i slutten. 1 136 lokaliteter har minst én hel
syklus. **Andelen produksjonsuker som ikke kan tilordnes er 0,65 %**
(2 808 av 431 660), eller 0,36 % av alle uker i universet.
Kilde og hash: panelet over.
Feil hvis: en syklus med sammenhengende lusetall i virkeligheten er to
generasjoner uten brakk mellom. Lusetall kan ikke se det, og de 19
lengste er kandidatene.

Lengdefordeling for de 6 485 hele (uker i sjø, fra første til siste
lusetelling): median **68**, kvartiler 43 og 79, snitt 61,4.

    ≤13: 362   14–26: 476   27–52: 1204   53–65: 950   66–78: 1769
    79–91: 1328   92–104: 292   105–130: 85   >130: 19

Hele sykluser per sluttår ligger stabilt på 416–505 fra 2013 til 2025
(2012: 264 og 2026: 338 er avkortet av seriens kanter).

### 4b. Kontroll mot biomasselaget

**F4.4 — MÅLT.** I den nyeste biomasselagkroppen stemmer `har_fisk`
med lusetallets produksjon/brakk i **955 av 994** lokaliteter der begge
kan sammenlignes (96,1 %). Hver rad er holdt mot lusetall-uka som
inneholder `siste_rapport`.
Kilde: `arkiv/biomasselag/2026-10-05.json.gz`
sha256 `08ca97df3778435aa617fae9f43799e379bb011103d146201ece7529e83b598c`,
mot panelet.
Feil hvis: `siste_rapport` er rapporteringsdatoen og ikke datoen
beholdningen gjelder for. Da er uka feil valgt. Å flytte én uke bakover
gir 94,7 %, så samme uke er den beste justeringen av de to.

| `har_fisk` | lusetall: produksjon | lusetall: brakk |
|---|---:|---:|
| Ja | **560** (10029, 10041, 10045) | 20 (10318, 11864, 11971) |
| Nei | 19 (11225, 33157, 45124) | **395** (10518, 10821, 10822) |

Utenfor sammenligningen: 23 lokaliteter finnes ikke i lusetall den uka,
68 er utenfor universet (landbasert, slaktemerd, ikke laksefisk), og
rader med `siste_rapport` etter 2026-09-07 er ikke med. 22 av de 39
avvikene har `siste_rapport` 2026-08-31, og 19 av dem er «Ja / brakk».
Det er forenlig med utslakting i månedens siste dager, men det er ikke
målt.

De fire eldre kroppene gir samme bilde (95,8–96,8 %).
`2026-09-15` og `2026-09-22` er byte-like (`069abea8…`), som
`docs/KILDE-BIOMASSELAG.md` punkt 5 allerede sier.

### 4c. Per syklus: lus over grensen, behandling, rensefisk, PD/ILA, temperatur

**F4.5 — MÅLT. Lusegrensa ER samlet inn, men den er ikke parset.**
`nettsted.py` (tegningen av lusegrafen) sier at «grensa er ikke samlet
inn». Den står likevel i hver sjøtemperaturkropp som `Lusegrense uke`
(0,5, eller 0,2 i ukene i april–juni fra 2017), sammen med BarentsWatchs
egen `Over lusegrense uke`. BarentsWatchs flagg er nøyaktig
`round(voksne_hunnlus, 2) >= Lusegrense uke`: **409 118 av 409 118**
uker stemmer. Det er grensen og regelen som brukes under.
Kilde: `arkiv/sjotemperatur/`, se hashlista.
Feil hvis: «grensen slik den står i repoet» skal leses som en konstant i
koden. Da finnes den ikke, og tallene under hviler på BarentsWatchs
kolonne.

**F4.6 — MÅLT. To av behandlingsflaggene er døde og kan bare brukes
bakover:** `hasCleanerfishDeployed` er sist `True` **2023-04-17**, og
`hasSubstanceTreatments` er sist `True` **2024-11-11**.
`hasMechanicalRemoval`, `hasPd` og `hasIla` lever fram til siste uke.
Kolonnene merket * under er derfor bare regnet på hele sykluser som
sluttet før 2023-04-17 (n*).
Feil hvis: flaggene kommer tilbake. Da er det en pause og ikke et
dødsfall, men tallene for sykluser etter 2023 er uansett tomme.

Per PO, hele sykluser. «Andel m/» er andelen sykluser med minst én slik
uke. Medianene er antall uker per syklus.

| PO | sykl. | uker med. | andel uker over grense, med. | andel m/ over grense | mek. uker med. | andel m/ mek. | med.* uker med. | andel m/ med.* | andel m/ rensefisk* | n* | andel m/ PD | andel m/ ILA | temp °C snitt |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 98 | 54,5 | 0,000 | 0,27 | 0 | 0,24 | 0 | 0,32 | 0,62 | 76 | 0,00 | 0,00 | 11,0 |
| 2 | 394 | 65 | 0,017 | 0,63 | 1 | 0,57 | 2 | 0,64 | 0,75 | 302 | 0,36 | 0,04 | 10,2 |
| 3 | 1022 | 67 | 0,024 | 0,64 | 3 | 0,67 | 2 | 0,69 | 0,81 | 768 | 0,37 | 0,02 | 10,5 |
| 4 | 949 | 66 | 0,028 | 0,68 | 3 | 0,67 | 2 | 0,70 | 0,50 | 712 | 0,39 | 0,01 | 10,2 |
| 5 | 299 | 69 | 0,027 | 0,69 | 4 | 0,72 | 2 | 0,70 | 0,74 | 213 | 0,40 | 0,02 | 10,0 |
| 6 | 873 | 73 | 0,027 | 0,72 | 5 | 0,68 | 2 | 0,65 | 0,83 | 650 | 0,53 | 0,04 | 9,5 |
| 7 | 412 | 61 | 0,013 | 0,53 | 5 | 0,75 | 2 | 0,63 | 0,57 | 295 | 0,09 | 0,03 | 9,0 |
| 8 | 651 | 66 | 0,015 | 0,57 | 3 | 0,63 | 2 | 0,62 | 0,54 | 478 | 0,01 | 0,04 | 8,5 |
| 9 | 680 | 53 | 0,014 | 0,57 | 1 | 0,51 | 2 | 0,78 | 0,12 | 508 | 0,00 | 0,03 | 8,1 |
| 10 | 408 | 74 | 0,014 | 0,61 | 1 | 0,55 | 3 | 0,85 | 0,17 | 300 | 0,00 | 0,04 | 7,6 |
| 11 | 252 | 68 | 0,000 | 0,32 | 0,5 | 0,50 | 2 | 0,69 | 0,21 | 182 | 0,00 | 0,03 | 7,3 |
| 12 | 408 | 77 | 0,000 | 0,47 | 0 | 0,40 | 2 | 0,76 | 0,16 | 311 | 0,01 | 0,06 | 6,7 |
| 13 | 39 | 68 | 0,000 | 0,10 | 0 | 0,10 | 0 | 0,45 | 0,21 | 29 | 0,00 | 0,00 | 7,1 |
| alle | 6485 | 68 | | 0,60 | | 0,61 | | | | | 0,23 | 0,03 | |

PO er sjøtemperaturkroppens `ProduksjonsområdeId`, som modus over
syklusens uker. Ingen syklus skifter PO underveis. Temperatur er snittet
av ukene med `Sjøtemperatur`, og dekningen er 95–99,7 % av
produksjonsukene per år. `hasMechanicalRemoval` er nesten tomt før 2016
(0,4–0,7 % av ukene mot 4–13 % senere), så mekanisk behandling for
sykluser før 2016 er en undertelling.

**F4.7 — MÅLT. PD-gradienten.** Andelen hele sykluser med minst én
PD-uke er 36–53 % i PO 2–6, 9 % i PO 7, og 0–1,5 % fra PO 8 og nordover.
Kilde: panelet (`hasPd`).
Feil hvis: `hasPd` sier hvor PD er påvist i et overvåkingsprogram, og
ikke at lokaliteten har PD. Det er ikke undersøkt hva flagget bygger på.

### 4d. Brakklegging per PO og måned

En brakklegging er første uke etter siste lusetelling i en ikke-kort
syklus som ikke er sensurert i slutten. 6 810 for hele serien.

Per PO og kalendermåned, 2012–2026 (første brakkuke):

| PO | jan | feb | mar | apr | mai | jun | jul | aug | sep | okt | nov | des |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 12 | 11 | 18 | 8 | 13 | 4 | 3 | 3 | 4 | 11 | 6 | 11 |
| 2 | 42 | 38 | 43 | 46 | 33 | 55 | 38 | 20 | 16 | 16 | 28 | 37 |
| 3 | 92 | 88 | 84 | 94 | 107 | 134 | 107 | 74 | 81 | 90 | 70 | 78 |
| 4 | 101 | 69 | 79 | 95 | 74 | 97 | 79 | 73 | 80 | 64 | 95 | 90 |
| 5 | 22 | 18 | 19 | 14 | 19 | 33 | 24 | 35 | 21 | 41 | 28 | 38 |
| 6 | 58 | 65 | 100 | 86 | 62 | 75 | 77 | 77 | 84 | 89 | 82 | 65 |
| 7 | 25 | 29 | 46 | 36 | 41 | 57 | 36 | 36 | 44 | 35 | 31 | 25 |
| 8 | 58 | 53 | 69 | 77 | 55 | 53 | 49 | 63 | 72 | 58 | 41 | 47 |
| 9 | 57 | 65 | 62 | 46 | 66 | 68 | 46 | 54 | 58 | 64 | 56 | 52 |
| 10 | 31 | 40 | 31 | 38 | 61 | 52 | 30 | 27 | 21 | 27 | 38 | 31 |
| 11 | 22 | 24 | 35 | 13 | 13 | 10 | 18 | 21 | 24 | 24 | 25 | 33 |
| 12 | 38 | 46 | 45 | 29 | 22 | 32 | 32 | 40 | 42 | 28 | 30 | 25 |
| 13 | 11 | 7 | 4 | 0 | 2 | 1 | 0 | 3 | 4 | 1 | 3 | 3 |

**F4.8 — MÅLT. Siste 12 måneder med lusetall (2025-09-08 →
2026-09-07): 504 brakklegginger på 488 lokaliteter.**

| PO | 25-09 | 25-10 | 25-11 | 25-12 | 26-01 | 26-02 | 26-03 | 26-04 | 26-05 | 26-06 | 26-07 | 26-08 | 26-09 | sum |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 2 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 2 | 1 | 9 |
| 2 | 3 | 0 | 3 | 3 | 3 | 4 | 1 | 1 | 2 | 1 | 4 | 4 | 0 | 29 |
| 3 | 6 | 4 | 5 | 4 | 3 | 9 | 6 | 10 | 3 | 9 | 8 | 3 | 1 | 71 |
| 4 | 6 | 3 | 6 | 16 | 7 | 2 | 2 | 9 | 1 | 12 | 3 | 4 | 3 | 74 |
| 5 | 0 | 2 | 1 | 4 | 3 | 1 | 2 | 1 | 0 | 1 | 3 | 2 | 1 | 21 |
| 6 | 3 | 3 | 4 | 11 | 9 | 3 | 8 | 4 | 5 | 7 | 5 | 7 | 1 | 70 |
| 7 | 2 | 2 | 4 | 4 | 3 | 3 | 3 | 2 | 5 | 6 | 1 | 2 | 0 | 37 |
| 8 | 4 | 5 | 3 | 4 | 9 | 3 | 4 | 5 | 4 | 4 | 6 | 6 | 3 | 60 |
| 9 | 2 | 3 | 3 | 3 | 3 | 5 | 4 | 0 | 6 | 5 | 2 | 7 | 1 | 44 |
| 10 | 0 | 2 | 0 | 4 | 1 | 1 | 5 | 4 | 3 | 7 | 2 | 4 | 1 | 34 |
| 11 | 3 | 1 | 5 | 2 | 3 | 0 | 2 | 0 | 1 | 1 | 0 | 1 | 1 | 20 |
| 12 | 1 | 3 | 1 | 3 | 2 | 3 | 1 | 2 | 3 | 0 | 8 | 4 | 1 | 32 |
| 13 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 3 |

Brakklegginger de siste ≤ 3 ukene før 2026-09-07 er undertalt.
Syklusen er sensurert til lusetall har sett brakk.

**Hvem står bak — DAGENS eierkobling.** Lokalitet → aktive tillatelser
i eierskapskroppen 2026-10-05 (`581bca61…`) → eier. Det er eieren nå,
ikke eieren da lokaliteten ble brakklagt. En lokalitet med flere eiere
telles hos hver (623 rader for 499 brakklegginger). 5 brakklegginger har
ingen selskapskobling i dag (personeid eller uten aktiv tillatelse,
regel 3). 146 eiere i alt.

| eier | orgnr | brakklegginger | PO |
|---|---|---:|---|
| MOWI SEAWATER NORWAY AS | 921668236 | 86 | 1–8, 10–12 |
| SALMAR OPPDRETT AS | 928957489 | 68 | 5–7, 10–12 |
| CERMAQ NORWAY SALMON AS | 930152366 | 31 | 9, 12 |
| NORDLAKS HAVBRUK AS | 929911946 | 17 | 9, 10 |
| NOVA SEA HAVBRUK AS | 827248312 | 16 | 8 |
| LERØY VEST SJØ AS | 930185698 | 15 | 3–5 |
| SINKABERG HAVBRUK AS | 926968955 | 15 | 7, 8 |
| LERØY MIDT SJØ AS | 930155209 | 15 | 5, 6 |
| ORGANIC SEAFARM AS | 996198944 | 15 | 8 |
| ENGESUND FISKEOPPDRETT AS | 923070591 | 14 | 3, 4 |

Største per PO: PO 3 LERØY VEST SJØ (12), PO 4 ENGESUND og MOWI (11
hver), PO 6 SALMAR OPPDRETT (21), PO 8 MOWI (20), PO 12 CERMAQ NORWAY
SALMON (20). Full fordeling i `/tmp/maling-okt/p4/brakk_12_selskap.csv`.
Feil hvis: noen leser tabellen som hvem som brakkla. Ved en
eieroverføring det siste året (punkt 3) står kjøperen her og ikke den som
brakkla.

Skript: `p4_panel.py` → `p4_sykluser.py` → `p4b_biomasselag.py`,
`p4d_selskaper.py`.
