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
