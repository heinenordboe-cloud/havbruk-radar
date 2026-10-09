# Måling 09.10.2026 — Mattilsynets API for lakselus og rensefisk

Spørsmålet: dekker Mattilsynets åpne API det BarentsWatchs to døde
flagg sluttet å vise — `har_rensefisk` (siste `True` 2023-04-17) og
`har_medikamentell_behandling` (siste `True` 2024-11-11)? Og hvor langt
tilbake går det?

**Måling, ingen kilde bygges.** Ingenting er skrevet til `data/`.

## Kort svar

* **Medikamentell behandling: ja, og bedre enn flagget noen gang gjorde
  etter 2023.** Lakselusrapportene har `medikamentelleBehandlinger` med
  type og virkestoff. 1 123 behandlingsuker etter 2024-11-11, der
  BarentsWatch viser 0.
* **Flagget døde i JANUAR 2024, ikke november.** I 4. kvartal 2023 er
  samsvaret 198 av 198 uker. Fra uke 1/2024 viser BarentsWatch én
  eneste `True` (Torangskjeret, uke 46) mot 625 behandlingsuker hos
  Mattilsynet. 2024-11-11 er et enkelttilfelle, ikke dødsdatoen.
* **Rensefisk: nei, hullet dekkes ikke.** Lakselusrapportene har ikke
  noe rensefiskfelt. Rensefisk-endepunktet har månedsrapporter fra
  12/2025 og fram — hullet 2023-04 → 2025-11 står åpent.
* **Hvor langt tilbake:** lakselus fra uke 40/2023 (~500 rapporter per
  uke), rensefisk fra 12/2025. Ingenting av betydning før det.

## 1. Kallene

Vert `https://akvakultur-offentlig-api.fisk.mattilsynet.io`, spesifikasjon
`/q/openapi` versjon `ed7f9fe` (NLOD 2.0), se
`docs/MALING-UNNTAKSVEKST.md` punkt 2. Alle kall gjennom
`sources/_http.get()`, altså med `User-Agent: havbruk-radar/1.0`.

**`Client-Id` er påkrevd. MÅLT:** uten headeren svarer tjenesten
`400 {"errors":["Validation error: must not be blank ('getAll.clientId'
= 'null')"]}`. Med `Client-Id: havbruk-radar` svarer den 200. Ingen
nøkkel, ingen registrering.

Ingen `Last-Modified` på noe svar. En kilde ville skrevet `published_at`
tom.

Kroppene ligger i `/tmp/mattilsynet-api/`, hver med `.sha256` og
`.meta.json` (URL, status, headere, hentetidspunkt):

| fil | kall | byte | sha256 |
|---|---|---:|---|
| `lakselus_21415_side000.json` | `lakselus/v2/rapporteringer?lokalitetsnummer=21415` | 67 209 | `e3baa7c1…d6d172` |
| `lakselus_11913_side000.json` | `…?lokalitetsnummer=11913` | 58 651 | `ee299249…189434` |
| `lakselus_30837_side000.json` | `…?lokalitetsnummer=30837` | 119 578 | `34f6ab85…52c5c6c7` |
| `rensefisk_alle_side000.json` | `rensefisk/v1/rapporteringer` (alt) | 1 988 653 | `8dba7fac…c21a71e1` |
| `lakselus_ufiltrert.json` | `lakselus/v2/rapporteringer` uten parametre | 54 763 009 | `3d778f92…0ba3df` |

Hentet 2026-10-09 01:51–01:53 UTC.

### Lokalitetene

Valgt fordi de hadde begge flaggene `True` i vår lusetall-serie før de
døde:

| nr | navn | hvorfor |
|---|---|---|
| 21415 | Dyrholmen | `har_rensefisk` til 2023-04-10, flest uker av alle 2022–23 |
| 11913 | Kjeahola | `har_rensefisk` til 2023-03-13, medikament 2023 |
| 30837 | Torangskjeret | den eneste `har_medikamentell_behandling = True` i hele 2024 (2024-11-11) |

## 2. Paginering og filtre — MÅLT

* `limit`/`offset` virker. Rensefisk hentet som `limit=1000` (519
  rader) og som seks sider `limit=100` gir nøyaktig samme 519 `id`-er.
* **Uten `limit` er det ikke noe tak:** et ufiltrert lakselus-kall ga
  hele tabellen, 96 845 rapporter og 54,8 MB, i ett svar.
* `aar`, `uke` og `lokalitetsnummer` filtrerer som lovet:
  `aar=2023&uke=39` ga bare (2023, 39); `aar=2023&lokalitetsnummer=21415`
  ga 13 rapporter, uke 40–52.
* Rensefisk har ikke `lokalitetsnummer`-filter — bare tidsrom. De tre
  lokalitetene er funnet ved å filtrere hele svaret lokalt.

## 3. Hvor langt tilbake

**Lakselus**, fra det ufiltrerte svaret:

| år | rapporter |
|---|---:|
| 2021 | 4 |
| 2022 | 19 |
| 2023 | 7 363 |
| 2024 | 32 362 |
| 2025 | 33 854 |
| 2026 | 23 242 |

958 lokaliteter. Serien begynner i praksis **uke 40/2023** med 500
rapporter (uke 39: 45, uke 34: 10). Tidligste `rapporteringstidspunkt`
er 2023-08-25. Det som står før uke 34/2023 er enkeltrapporter levert
senere — en rapport for 2021 uke 25 er levert 2024-01-09.

For de tre: Dyrholmen og Kjeahola fra uke 40/2023, Torangskjeret fra
uke 31/2024. Det ufiltrerte svaret har ingen eldre rad for noen av dem.

Kvalitetsfunn, ikke undersøkt videre:

* én rapport med `år = 1, uke = 1` (lokalitet 13562, levert 2025-09-23),
* sju rapporter for 2026 uke 52, levert 2.–7. januar 2026 — sannsynligvis
  2025 uke 52 med feil år. UBELAGT,
* **4 533 (lokalitet, uke)-par har mer enn én rapport.** Torangskjeret
  uke 46/2024 har to, fra to ulike selskaper med identiske lusetall og
  behandlinger — samdrift, rapportert av hver innehaver. En kilde må
  bestemme om raden er rapporten eller lokaliteten.

**Rensefisk:** 519 månedsrapporter fra 115 lokaliteter, (2025, 12) til
(2026, 9). Én rapport for desember 2025, deretter 44–72 per måned.
Tidligste `rapporteringstidspunkt` 2026-01-23. Hvorfor det begynner
der — ny rapporteringsplikt eller ny tjeneste — er UBELAGT.

## 4. Medikamentell behandling mot BarentsWatch

Sammenlignet per (lokalitet, ISO-uke) mot `har_medikamentell_behandling`
i `data/raw/lusetall/`, 154 ukesfiler 2023-10-02 … 2026-09-07. En uke
teller som behandlet hos Mattilsynet når `medikamentelleBehandlinger`
eller en `kombinasjonsbehandlinger[].medikamentelleBehandlinger` er
ikke-tom.

| periode | felles (lok, uke) | BW `True` | MT behandlet | begge |
|---|---:|---:|---:|---:|
| 2023 u40 – 2024 u46 | 33 929 | 203 | 824 | 199 |
| 2024 u47 – 2026 u39 | 55 639 | **0** | **1 123** | 0 |

Delt på kvartal i den første perioden:

| kvartal | MT behandlet | av dem BW `True` |
|---|---:|---:|
| 2023 K4 | 198 | **198** |
| 2024 K1 | 119 | 0 |
| 2024 K2 | 121 | 0 |
| 2024 K3 | 212 | 0 |
| 2024 K4 (til u46) | 174 | 1 |

Siste uker med BW `True`: 2023-12-18 (12), 2023-12-25 (7), så ingenting
før 2024-11-11 (1). **Flagget sluttet å bære informasjon i januar 2024.**
Strekket feltvakten teller begynner etter enkelttilfellet 2024-11-11:
95 uker til siste ukesfil (2026-09-07). Det reelle strekket fra
2024-01-01 er 141 uker. Samme form som
F10 nevner om referansen: den ble satt av data som allerede inneholdt
feilen.

Fordelingen på type i perioden flagget levde (2023 u40 – 2024 u46):
`FORBEHANDLING` 487 uker (109 med BW `True`), `BADEBEHANDLING` 336 (90),
kombinasjon/annen 4 (0). Flagget skilte altså ikke på type; det sluttet.

For de tre lokalitetene:

| lok | Mattilsynet, uker med behandling | BarentsWatch `True` |
|---|---|---|
| 21415 | 2023 u43, u44 | 2023 u43, u44 |
| 11913 | 2023 u48, **2024 u5, 2025 u18** | 2023 u48 |
| 30837 | 2024 u46 | 2024 u46 |

Kjeahola 2025 uke 18 er en badebehandling BarentsWatch ikke viser.

## 5. Rensefisk mot BarentsWatch

`har_rensefisk` er `False` i alle 271 420 (lokalitet, uke) fra
2023-10-02. Mattilsynets lakselusrapport har **ikke noe rensefiskfelt**
(`LakselusrapporteringDto`: lusetelling, tre slags behandlinger,
resistens, følsomhet — se spesifikasjonen). Rensefisk står bare i
`rensefisk/v1`, og det begynner 12/2025.

For de tre: Dyrholmen har rensefiskrapport for 2026-08 og -09, Kjeahola
for 2026-01 og -06…-09, Torangskjeret for 2026-09.

Rensefisk-rapporten er rikere enn flagget var — per merd og art:
beholdning, utsett, uttak per årsak, og fôr. Men den dekker ikke
2023-04-24 → 2025-11, og det hullet er ikke å finne i dette API-et.

## 6. Hva målingen ikke sier

* Om API-et har data fra før uke 40/2023 et annet sted (et
  arkivendepunkt, en eksport). Spesifikasjonen nevner ingen.
* Om `rensefisk/v1` er komplett: 115 lokaliteter kan være alle som bruker
  rensefisk, eller bare de som rapporterer i den nye løsningen. UBELAGT.
* Om BarentsWatch henter fra dette API-et. Attribusjonen deres sier
  «hentet fra Mattilsynet», men om det er samme tjeneste er ikke sett.
* Lisensen er NLOD 2.0 ifølge spesifikasjonen. Hvilken
  attribusjonssetning den krever, er ikke lest.
