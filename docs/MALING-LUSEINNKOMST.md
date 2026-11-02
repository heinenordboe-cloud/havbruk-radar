# Måling 02.11.2026 — når lusetallene kommer inn

Spørsmålet: kan vi se lusetallene komme inn uke for uke, før uka er
komplett? Lusetallskilden henter uke N−4 én gang og fryser den
(`docs/KILDE-LUSETALL.md`). Mellom inneværende uke og N−4 svarer
BarentsWatch med et register som overskriver seg selv, og hver dag vi
ikke ser det, er tapt (CLAUDE.md regel 5).

**Måling, ingen kilde bygges i dette dokumentet.** Fire delspørsmål:

* a. Gir API-et tall for uke N og N−1 til N−4 før de er komplette, og
  hvor stor andel av de aktive lokalitetene har rapportert i hver?
* b. Finnes et tidsstempel for når en lokalitet rapporterte, eller må
  det utledes av når tallet dukket opp hos oss?
* c. Endres tall i ettertid? Dagens svar for N−4 og eldre uker mot
  kroppene innsamlingen arkiverte.
* d. Antall kall og bytes per dag for en daglig fangst av N til N−4.

## Stoppregel

Skrevet før noe ble hentet, 02.11.2026 kl. 19.15 UTC.

**STOPP** hvis endepunktet `/v1/geodata/fishhealth/locality/{år}/{uke}`
for inneværende uke (45/2026) og N−1 (44/2026) svarer med noe annet enn
200 og en liste lokaliteter der minst én aktiv lokalitet har
`hasReportedLice: true` — altså hvis API-et ikke gir ukomplette uker,
bare ferdige. Da bygges ingen daglig fangst; jeg rapporterer og foreslår
et alternativ.

**STOPP også** hvis andelen er den samme (innenfor ett prosentpoeng) i
alle fem ukene N til N−4 — da er det ingen innkomst å se — eller hvis
svaret for samme uke varierer mellom to kall rett etter hverandre uten
at innholdet endres på en måte som kan kanoniseres bort (da kan «ny
kropp» ikke skilles fra støy).

Går målingen videre forbi et av disse, står det hvorfor under.

**Utfall av stoppregelen:** ingen av de tre er utløst. Uke 45 og 44
svarer 200 med 3 og 188 rapporterte aktive lokaliteter (F1.1), andelen
går fra 0,5 % til 99,3 % over de fem ukene (F1.2), og to kall mot uke 41
med ett sekunds mellomrom ga samme sha256 (F1.6).

## Datagrunnlag

Hentet 02.11.2026 kl. 18.59.33–18.59.51 UTC med
`analyse/luseinnkomst/m1_hent.py 2026-11-02`, samme nøkler og samme
`Tilgang` som `sources/lusetall.py`, samme endepunkt
(`/v1/geodata/fishhealth/locality/{år}/{uke}`) og samme serialisering
som innsamlingen (`core.raw._serialiser`, `sort_keys`). Tallene i
tabellene er utskriften av `analyse/luseinnkomst/m2_analyse.py
2026-11-02`, uendret. Den leser bare arkivet.

Inneværende uke er 45/2026 (mandag 02.11). N−4 er uke 41, som
innsamlingen hentet samme dag (commit `9bee6fe` i datarepoet, 13.14 UTC).

Alle kropper ligger i `havbruk-radar-data/data/arkiv/`. sha256 er over
den utpakkede kroppen.

| kall | fil | sha256 |
|---|---|---|
| uke 45/2026 (N) | `lusetall-innkomst/2026-11-02.json.gz` | `7bc84a1e676dbe5a57780353fbc0b8ac6a494dc14e255816b2371e6cf16237d1` |
| uke 44/2026 (N−1) | `lusetall-innkomst/2026-10-26.json.gz` | `bfcad06f37e52b6843799fad23e5da5740186783c18f12048aca8896816e77b8` |
| uke 43/2026 (N−2) | `lusetall-innkomst/2026-10-19.json.gz` | `30ef394a4474647991ff45a768ccaf4837dba18047ee4a48d84acf3698f27691` |
| uke 42/2026 (N−3) | `lusetall-innkomst/2026-10-12.json.gz` | `02b6c9e6a11c2dc2a1d2eaaf2a4e15eeab5d445c7cacccf844ba73b12df66199` |
| uke 41/2026 (N−4), begge kall | `lusetall-innkomst/2026-10-05.json.gz` | `35169a1ae83afbd0524e1d9fe91e4e5c16fcc62fcd75052b56f315245d666436` |
| uke 40/2026, i dag | `lusetall-innkomst/2026-09-28.json.gz` | `3549b7e642faf289dea7d21a85df396f70a8cd3f20f7b8c996f6349955fd7744` |
| uke 39/2026, i dag | `lusetall-innkomst/2026-09-21.json.gz` | `21f5c28b86c7ae9b96cb1b5a56280d38cb04b3a1b54e8324dd5fd97b2d7c2443` |
| uke 38/2026, i dag | `lusetall-innkomst/2026-09-14.json.gz` | `71d081a7135413512cdc715bd9461bf662ed0d4d703f7eec8d93fd53756ae686` |
| uke 37/2026, i dag | `lusetall-innkomst/2026-09-07.json.gz` | `20deac79758e94fbdd7b2ac4fc232a1d0e1c74180f0dd2bb90cce66ea0378ca2` |
| uke 41/2025, i dag | `lusetall-innkomst/2025-10-06.json.gz` | `2614a38eb9408dd23e551bff7b1a41a261bceff283b54e10d51da15bd012861e` |
| uke 41/2024, i dag | `lusetall-innkomst/2024-10-07.json.gz` | `ba22fe3a54367840c94487588424fe58818a64bd09f74d67d1bcee507b2deda3` |
| uke 41/2020, i dag = innsamlingens | `lusetall/2020-10-05.json.gz` | `fb134ec6d9f30e3b7a8de78a0e2379ded81914d79fa2ed01cec6c46a06f1962f` |
| uke 41/2016, i dag | `lusetall-innkomst/2016-10-10.json.gz` | `8dd58b0562b3a05d173d94fd7fdb1bacee982cfa8d2d20e039993fbbcd6badc4` |
| innsamlingens uke 40/2026 | `lusetall/2026-09-28.json.gz` | `61e0df4fff3f5efda69a3e522b6f5a385117c7f1c81b61da366dd0691061e4d3` |
| innsamlingens uke 39/2026 | `lusetall/2026-09-21.json.gz` | `5bfc9e04180cf3266ec390a3ecf0d007b3c0555334666082a65fb267a18ae8f3` |
| innsamlingens uke 38/2026 | `lusetall/2026-09-14.json.gz` | `05f4affc655130f449751c43ee3353f1faaa63f6ef7afb8eb08b937e71d64e02` |
| innsamlingens uke 37/2026 | `lusetall/2026-09-07.json.gz` | `f4543c206d95b2de85a95e799d528230a15404f9b6b4da4356a212f3331a26bb` |
| innsamlingens uke 41/2025 | `lusetall/2025-10-06.json.gz` | `59db53968e770f4ffe9108b843e3497f25d27e1b98305a0a4bcaaecccf507d8d` |
| innsamlingens uke 41/2024 | `lusetall/2024-10-07.json.gz` | `06971ce21cc3c67130d7b4312d46035182f54eb914652a2a60cf3a5304c7fac6` |
| innsamlingens uke 41/2016 | `lusetall/2016-10-10.json.gz` | `fc6387941538f7ecfb2c9c27918c1048daa9b28412e967263ea8ee9b2736d758` |
| OpenAPI-spesifikasjonen | `lusetall-innkomst-openapi/2026-11-02.json.gz` | `d3f328e89202cf6e20f890b53c16a7d4808965a29476f19344348555b9d7f99d` |
| lokalitet 10029, uke 44 | `lusetall-innkomst-lokalitet/2026-11-02.json.gz` | `c31ef5c014b1a95bc92a2ad943413ecc98f9770e311679bae9279d7c78c6d73f` |
| kallogg (headere, bytes, tider) | `lusetall-innkomst/2026-11-02.maling.logg.json` | `f89a7ef0e3228b772474946982ba019faf309304ae7ae0b1799c69118908d5ca` |

Kroppene for uke 41/2026 og 41/2020 var like innsamlingens. Den første
ble likevel skrevet i `lusetall-innkomst/`, fordi N−4 hører til serien
som skal fanges; den andre ble ikke skrevet på nytt.

**Merkene:** MÅLT = holdt mot en arkivert kropp, sha256 over. MÅLBAR =
regnet ut av målte tall, eller lest i et snapshot. EKSTERN = hviler på
noe som ikke er i arkivet. UBELAGT = ingen kropp sier det. Hvert funn har
én linje «Feil hvis».

## De tre sterkeste funnene

**1. API-et gir ukomplette uker, og innkomsten er bratt (F1.1, F1.2).**
Andel aktive lokaliteter som har rapportert, i dag: uke 45 0,5 %, 44
30,3 %, 43 93,2 %, 42 97,1 %, 41 99,3 %. Hele innkomsten skjer mellom N
og N−2; N−3 og N−4 er etterslepet. Det er dette en daglig fangst ser, og
det innsamlingen aldri ser, fordi den bare henter N−4.
*Hvorfor sterkest:* fem kropper fra samme minutt, samme endepunkt, samme
regel for «aktiv» som kilden bruker (`rapportert_andel`).

**2. Lusetallene er ikke revidert etter N−4 i noen av de 15 791
lokalitetsukene som ble sammenlignet (F1.3).** `avgAdultFemaleLice` og
`hasReportedLice` er like i dagens svar og innsamlingens kropp for uke
37–41/2026, 41/2025, 41/2024, 41/2020 og 41/2016. Det som endret seg,
er 1–3 lokaliteter per uke i `hasSalmonoids`,
`isSlaughterHoldingCage` og én gang `isFallow` (F1.4).
*Hvorfor sterkt:* ni par kropper med hash, opptil ti år mellom
hentingene. *Hvorfor ikke sterkere:* det sier ingenting om hva som
skjer FØR N−4, og det er der en daglig fangst skal se. Det spørsmålet
kan ingen kropp vi har i dag svare på.

**3. Det finnes ikke noe rapporteringstidspunkt i svaret (F1.5).** Ingen
egenskap i ukeskjemaet bærer et tidspunkt, og `Last-Modified` er
tidspunktet svaret ble laget, ikke da tallet ble utgitt. Når en lokalitet
rapporterte, kan bare avgrenses av VÅRE hentinger: tidligst etter
forrige henting der den ikke hadde rapportert, senest ved den første der
den hadde det. Det er `fetched_at`, og den handler om oss (CLAUDE.md
1b-7).

Svakere: F1.4 (hvorfor flaggene endrer seg er en tolkning, ikke en
måling) og F1.7 (`version` i per-lokalitet-svaret er ett tall i én
kropp).

## a. Gir API-et ukomplette uker?

**F1.1 — Ja. MÅLT.** Uke 45 og 44 svarer 200 med 1 782 lokaliteter
hver, og 3 og 188 aktive har `hasReportedLice: true`. Kropper:
`lusetall-innkomst/2026-11-02.json.gz` og `…/2026-10-26.json.gz`.
*Feil hvis:* en av de to kroppene har null aktive lokaliteter med
`hasReportedLice: true`.

**F1.2 — Andelen per uke, i dag. MÅLT.** Utskriften av `m2_analyse.py`:

| kall | lokaliteter | brakklagt | aktive | rapportert | andel | kropp | sha256 |
|---|---:|---:|---:|---:|---:|---|---|
| N-0 (45/2026) | 1782 | 1162 | 620 | 3 | 0.5% | `lusetall-innkomst/2026-11-02.json.gz` | `7bc84a1e676d…` |
| N-1 (44/2026) | 1782 | 1162 | 620 | 188 | 30.3% | `lusetall-innkomst/2026-10-26.json.gz` | `bfcad06f37e5…` |
| N-2 (43/2026) | 1780 | 1160 | 620 | 578 | 93.2% | `lusetall-innkomst/2026-10-19.json.gz` | `30ef394a4474…` |
| N-3 (42/2026) | 1779 | 1168 | 611 | 593 | 97.1% | `lusetall-innkomst/2026-10-12.json.gz` | `02b6c9e6a11c…` |
| N-4 (41/2026) | 1779 | 1175 | 604 | 600 | 99.3% | `lusetall-innkomst/2026-10-05.json.gz` | `35169a1ae83a…` |
| N-4 igjen (41/2026) | 1779 | 1175 | 604 | 600 | 99.3% | `lusetall-innkomst/2026-10-05.json.gz` | `35169a1ae83a…` |
| N-5 (40/2026) | 1780 | 1174 | 606 | 602 | 99.3% | `lusetall-innkomst/2026-09-28.json.gz` | `3549b7e642fa…` |
| N-6 (39/2026) | 1779 | 1166 | 613 | 611 | 99.7% | `lusetall-innkomst/2026-09-21.json.gz` | `21f5c28b86c7…` |
| N-7 (38/2026) | 1778 | 1170 | 608 | 604 | 99.3% | `lusetall-innkomst/2026-09-14.json.gz` | `71d081a71354…` |
| N-8 (37/2026) | 1776 | 1171 | 605 | 600 | 99.2% | `lusetall-innkomst/2026-09-07.json.gz` | `20deac79758e…` |
| uke 41/2025 | 1773 | 1158 | 615 | 610 | 99.2% | `lusetall-innkomst/2025-10-06.json.gz` | `2614a38eb940…` |
| uke 41/2024 | 1759 | 1135 | 624 | 620 | 99.4% | `lusetall-innkomst/2024-10-07.json.gz` | `ba22fe3a5436…` |
| uke 41/2020 | 1693 | 1062 | 631 | 627 | 99.4% | `lusetall/2020-10-05.json.gz` | `fb134ec6d9f3…` |
| uke 41/2016 | 1674 | 1097 | 577 | 546 | 94.6% | `lusetall-innkomst/2016-10-10.json.gz` | `8dd58b0562b3…` |

Mønsteret er det samme som 18.08.2026 (`docs/BARENTSWATCH-FUNN.md`
punkt 4: 5,3 / 88,0 / 97,6 / 99,0 / 99,3 %), men N−1 er lavere i dag
(30,3 % mot 88,0 %). Det kan være ukedagen: 18.08 var en tirsdag, i dag
er mandag kveld. **Det er en tolkning, UBELAGT.** Den daglige fangsten
avgjør det.

Merk at nevneren flytter seg: 620 aktive i uke 45 og 44, 604 i uke 41.
`isFallow` er BarentsWatchs slutning av manglende rapporter
(`docs/MALING-FUNN-OKTOBER.md` F4.2), så en lokalitet som ikke
rapporterer, kan gå over til brakklagt i ettertid og forsvinne fra
nevneren. Det følger av F4.2 og F1.4 under, og er MÅLBAR, ikke målt
her.
*Feil hvis:* `rapportert_andel` på en av kroppene gir andre tall enn
tabellen.

## c. Endres tall i ettertid?

**F1.3 — Ikke lusetallene, etter N−4. MÅLT.** Dagens svar mot
innsamlingens kropp for samme uke, per lokalitet og felt. Utskriften av
`m2_analyse.py`:

| uke | innsamlet (fil) | lokaliteter i dag / ved innsamling | bare i dag | bare ved innsamling | lokaliteter med endret felt | felt (antall lokaliteter) |
|---|---|---|---:|---:|---:|---|
| 2026/41 | `lusetall/2026-10-05.json.gz` | 1779/1779 | 0 | 0 | 0 | — |
| 2026/40 | `lusetall/2026-09-28.json.gz` | 1780/1780 | 0 | 0 | 3 | `hasSalmonoids` 2, `isSlaughterHoldingCage` 2, `isFallow` 1 |
| 2026/39 | `lusetall/2026-09-21.json.gz` | 1779/1779 | 0 | 0 | 2 | `hasSalmonoids` 2, `isSlaughterHoldingCage` 2 |
| 2026/38 | `lusetall/2026-09-14.json.gz` | 1778/1778 | 0 | 0 | 2 | `hasSalmonoids` 2, `isSlaughterHoldingCage` 2 |
| 2026/37 | `lusetall/2026-09-07.json.gz` | 1776/1776 | 0 | 0 | 2 | `hasSalmonoids` 2, `isSlaughterHoldingCage` 2 |
| 2025/41 | `lusetall/2025-10-06.json.gz` | 1773/1773 | 0 | 0 | 2 | `hasSalmonoids` 2, `isSlaughterHoldingCage` 2 |
| 2024/41 | `lusetall/2024-10-07.json.gz` | 1759/1759 | 0 | 0 | 3 | `hasSalmonoids` 3, `isSlaughterHoldingCage` 1 |
| 2020/41 | `lusetall/2020-10-05.json.gz` | 1693/1693 | 0 | 0 | 0 | — |
| 2016/41 | `lusetall/2016-10-10.json.gz` | 1674/1674 | 0 | 0 | 1 | `hasSalmonoids` 1 |

Summen av «lokaliteter i dag» over de ni radene er 15 791. Ingen av dem
har endret `avgAdultFemaleLice`, `hasReportedLice` eller
behandlingsflaggene.

Hva som IKKE er målt: om et lusetall endres mellom første rapport og
N−4. Uke 41/2026 er sammenlignet med en kropp fra samme dag, uke 37–40
med kropper hentet ved N−4. Ingen kropp i arkivet er hentet før N−4 for
noen uke, bortsett fra de fem i dag. Spørsmålet er UBELAGT, og det er
det den daglige fangsten skal svare på.
*Feil hvis:* én av de 15 791 felles lokalitetene har ulik
`avgAdultFemaleLice` eller `hasReportedLice` i de to kroppene for sin
uke.

**F1.4 — Flaggene som endrer seg, endrer seg bakover i tid. MÅLT.**
Lokalitetene, med verdi ved innsamling → i dag:

    uke 37–40/2026  19395 Bakka           hasSalmonoids, isSlaughterHoldingCage  True → False
    uke 37–40/2026  13494 Flerengstrand   hasSalmonoids, isSlaughterHoldingCage  True → False
    uke 41/2025     13494 Flerengstrand   samme
    uke 41/2025     27395 Rindarøy        hasSalmonoids, isSlaughterHoldingCage  True → False
    uke 41/2024     13494 Flerengstrand   hasSalmonoids, isSlaughterHoldingCage  True → False
    uke 41/2024     31717 Gjerset V       hasSalmonoids                          True → False
    uke 41/2024     12884 Sandnesbukta    hasSalmonoids                          True → False
    uke 41/2016     33397 Daugstad        hasSalmonoids                          True → False
    uke 40/2026     11179 Alterosen       isFallow                               True → False

Flerengstrand har skiftet verdi i uker fra 2024, 2025 og 2026 på én
gang. **Tolkning, MÅLBAR:** `hasSalmonoids` og `isSlaughterHoldingCage`
er ikke en ukesobservasjon, men lokalitetens tillatelser slik de er når
svaret lages, lagt på hver uke. Det gjelder `har_laksefisk` og
`er_slaktemerd` i lusetallskilden også, og er et funn om den, ikke om
fangsten. `isFallow` for Alterosen i uke 40 er den andre sorten (F1.2):
en slutning som er trukket tilbake.
*Feil hvis:* en av de ni linjene ikke finnes i parene av kropper over.

## b. Finnes et tidsstempel for når en lokalitet rapporterte?

**F1.5 — Nei. MÅLT.** Ukesvaret (`LocalityDto`) har disse feltene og
ingen andre: `avgAdultFemaleLice`, `hasCleanerfishDeployed`, `hasIla`,
`hasMechanicalRemoval`, `hasPd`, `hasReportedLice`, `hasSalmonoids`,
`hasSubstanceTreatments`, `inFilteredSelection`, `isFallow`, `isOnLand`,
`isSlaughterHoldingCage`, `lat`, `localityNo`, `localityWeekId`, `lon`,
`municipality`, `municipalityNo`, `name`. Heller ikke v2-svaret
(`LocalityWeekReportV2`) eller per-lokalitet-svaret
(`Licereport.Models.LocalityWeek`) har et tidspunkt for rapporten. Det
eneste rapporteringstidspunktet i spesifikasjonen er
`CleanerFishReportExportDto.reportingTime`, som gjelder rensefisk.
Kilde: `lusetall-innkomst-openapi/2026-11-02.json.gz`.

`Last-Modified` på hvert av de 15 ukesvarene ligger innen ett sekund fra
vår `fetched_at` for kallet (kallogg). Det er tidspunktet svaret ble
laget, ikke da tallet ble utgitt, og kan ikke brukes som `published_at`
(CLAUDE.md 1b-7 regel 2). ETag er en UUID og var lik for de to kallene
mot uke 41, med `Cache-Control: max-age=120`.

Spesifikasjonen sier om per-lokalitet-endepunktet: «The information is
updated nightly, with data reported to the Norwegian Food Safety
Authority via AltInn.» Det er kildens egen påstand, lest i den arkiverte
spesifikasjonen, ikke observert i dataene.

**Konsekvensen:** når en lokalitet rapporterte, kan bare avgrenses av
våre hentinger: etter den siste der `hasReportedLice` var `false`, og
senest ved den første der den var `true`. Begge er `fetched_at`. De
handler om OSS, og en fangst som lagrer dem, lagrer en øvre og en nedre
grense, ikke et tidspunkt. Oppdateres kilden hver natt, er én henting
per døgn nok til å finne natta.
*Feil hvis:* et av de tre skjemaene har en egenskap med `format:
date-time` eller et navn med «report» og «time»/«date».

**F1.7 — `version` og `localityWeekId`. MÅLT, men tolkningen er
UBELAGT.** Per-lokalitet-svaret for 10029 uke 44 har `"version": 2` og
`"id": 2152925`, som er samme tall som `localityWeekId` for 10029 i
ukesvaret. `version` står ikke i ukesvaret. Ett tall i én kropp sier
ikke om 2 betyr «revidert én gang» eller noe annet. `localityWeekId`
finnes for alle lokaliteter, også dem som ikke har rapportert (uke 45:
1 782 id-er for 3 rapporter), så den er ikke et rapporteringsnummer.
Den daglige fangsten kan avgjøre om id-en skifter når en lokalitet
rapporterer.
*Feil hvis:* `localityWeek.version` i
`lusetall-innkomst-lokalitet/2026-11-02.json.gz` ikke er 2.

**F1.8 — Endepunktet er merket `deprecated: true`. MÅLT.**
`GET /v1/geodata/fishhealth/locality/{year}/{week}`, som både
lusetallskilden og denne målingen bruker, er merket utgått i
spesifikasjonen. Etterfølgeren er `POST /v2/…/locality/{year}/{week}`
med et annet skjema. Ingen dato er oppgitt. Det er et funn om
lusetallskilden. Fangsten bruker samme endepunkt med vilje, så kroppene
kan sammenlignes byte for byte med innsamlingens.
*Feil hvis:* `paths["/v1/geodata/fishhealth/locality/{year}/{week}"].get.deprecated`
ikke er `true` i den arkiverte spesifikasjonen.

## d. Kall og bytes per dag

**F1.6 — Svaret er stabilt mellom to kall. MÅLT.** Uke 41 hentet to
ganger med ett sekunds mellomrom: samme sha256
(`35169a1a…66436`), og samme som innsamlingens kropp fra samme dag.
Uten ordningsstøy trengs ingen kanonisk form som for akvakultur
(`arkiver_daglig.UORDNET`): sha256 av kroppen avgjør om den er ny.
*Feil hvis:* de to kallene mot uke 41 i kallogg har ulik
`sha256_kanonisk_json`.

**F1.9 — Kostnaden. MÅLT for én dag, MÅLBAR fram.** Fra kallogg:

    kall per dag        1 tokenkall + 5 ukekall
    over linja (gzip)   633 571 B for de fem ukene
    utpakket            3 812 506 B
    tid per ukekall     0,38–1,23 s
    lagret per kropp    60–62 kB (gzip -9 i arkivet)

Lagres en kropp bare når den er ny, er det verste tilfellet fem nye
kropper per dag, rundt 310 kB. Hvor mange som faktisk er nye, er ikke
målt; fra F1.2 er det rimelig å vente at N til N−2 skifter oftest og N−4
sjeldnest. Seks kall i døgnet er under det BarentsWatchs vilkår kaller
høytrafikk (`docs/KILDE-LUSETALL.md`, plikt 2), men det er vår
vurdering, ikke deres.
*Feil hvis:* summen av `byte_linje` for de fem første kallene i
kallogg ikke er 633 571.
