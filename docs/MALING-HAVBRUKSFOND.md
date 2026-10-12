# Måling: Havbruksfondet

Målt 12.10.2026 mot `havbruk-radar-data` og kropper arkivert samme dag.
Skriptene ligger i `analyse/havbruksfond/` og arkiveringen i
`arkiver_havbruksfond.py`. Dokumentet beskriver hva som er målt. Det
vurderer ikke hva målingen er verdt.

**Merkene:** MÅLT = holdt mot en arkivert kropp med oppgitt sha256.
MÅLBAR = lest i et snapshot, avledet eller regnet ut av målte tall, men
ikke selv holdt mot en kropp. UBELAGT = ingen kropp vi har sier det.

---

## A1. Regelverket

### Funnet: det er en instruks, ikke en forskrift

Fordelingen mellom kommuner og fylkeskommuner står **ikke i en
forskrift**. Den står i Nærings- og fiskeridepartementets instruks til
Fiskeridirektoratet av 27.09.2024. Hvert år kommer et brev fra
departementet («orientering») med beløpet. Ingen kropp vi har lest
viser til en forskrift på Lovdata, og Fiskeridirektoratets side om
fondet viser bare til instruksen. Lovdata er derfor ikke arkivert for
dette punktet. (MÅLT at siden og instruksen ikke viser til en
forskrift. Vi har ikke søkt gjennom hele Lovdata.)

**Fiskeridirektoratets side lenker feil.** Lenketeksten «Instruks for
utbetalinger fra Havbruksfondet (pdf, 95.0 kB)» peker på «Orientering om
utbetalinger fra Havbruksfondet i 2025», som er beløpsbrevet av
10.11.2025. Instruksen svarer 404 på begge adressene den har hatt på
fiskeridir.no. Den ligger i Wayback, i et avtrykk fra 03.11.2024, og er
hentet derfra. Fra og med «Utbetalingene fra Havbruksfondet fordeles
med 80%» har Fiskeridirektoratets side samme ordlyd som instruksen.
MÅLT med tegnvis sammenligning etter at linjeskift er normalisert. Det
som skiller, er brevhodet, hilsenen, ett kolon og to skrivemåter:
instruksen skriver «akvakulturregistreret» og «Akvakulturregisteret»,
siden skriver «akvakulturregisteret» begge steder. Siden er derfor en
gjengivelse av den gjeldende instruksen, ikke av en annen versjon.

### Kroppene

Alle ble arkivert 12.10.2026 av `arkiver_havbruksfond.py` (kode `d47cfdd`)
og ligger i datarepoet med commit `7f16671`. `published_at` er
`X-Archive-Orig-Last-Modified` der Wayback hadde den. Ellers står feltet
tomt. `/CreationDate` er PDF-ens egen påstand og ikke en utgivelsestid.

| kropp | sti (`data/arkiv/…`) | sha256 | dato |
|---|---|---|---|
| Fiskeridirektoratets side om fondet | `havbruksfondet/2026-10-12.bin.gz` | `c1a2f596b3f7bfcf1a0422664dae431a957f6b468c278bccce9557266c4d6951` | hentet 12.10.2026 |
| **Instruks 27.09.2024** (gjeldende), Wayback 03.11.2024 | `havbruksfondet/2026-10-12.12.bin.gz` | `a47f03cf9327614f68c618e84c9399e92bc932725f366f38c25a9de69606b925` | PDF 2024-09-27 |
| Instruks 30.11.2022 (erstattet), Wayback 26.09.2023 | `havbruksfondet/2026-10-12.13.bin.gz` | `fb3ae757c1e585ee80e424da115ac13759496b790fd50ee91783037de7d15232` | PDF 2022-11-30 |
| Supplerende instruks 2023, Wayback 17.07.2024 | `havbruksfondet/2026-10-12.14.bin.gz` | `ef32a8ce9736f4f8653496df21a77c31686955ab22cb84f3d74a30aa0cd44628` | PDF 2023-12-01 |
| Orientering om utbetalinger 2025 | `havbruksfondet/2026-10-12.11.bin.gz` | `f855e14d60349543c693b66034bf331a4a0472785c0988c31a96e8a74fa1af8a` | brevet datert 10.11.2025 |
| Regneark, utbetaling 2025 | `havbruksfondet/2026-10-12.8.bin.gz` | `e26cfffe259153d0f9fd9d84c3f2a89b3d904e290c0f48f5978a667e38308b76` | |
| Regneark, utbetaling 2024 | `havbruksfondet/2026-10-12.7.bin.gz` | `4a56b3c077e3695f55971a95d51f1f9f82d52aa0db29c18220c93db52cb3ba55` | |
| Pressemelding, fastpris 2024 | `regjeringen-pressemeldinger/2024-06-06.bin.gz` | `ced658f6756116387248c7410e7d902cc3b1c2f958658b687943ccb3fe1200b7` | Last-Modified 06.06.2024 |
| Pressemelding, auksjon 2024 | `regjeringen-pressemeldinger/2024-06-25.bin.gz` | `ce7c58a074e794350d850bf64919d52ece1c242403c67594a99bd543e67046aa` | Last-Modified 25.06.2024 |
| Pressemelding, utbetaling 2025 | `regjeringen-pressemeldinger/2025-11-10.bin.gz` | `35b92f454817a8bc6430314b69b2b799a296e84f2feee60d0a1fe6d2396b8a69` | Last-Modified 05.12.2025, se under |

Regnearkene for 2017–2023 er også arkivert (`.2`–`.6`, `.9`, `.10`).
Alle sha256-ene står i `havbruksfondet/2026-10-12.logg.json`.

**Pressemeldingen 2025 er avtrykket fra 05.12.2025.** Skriptet ba om
avtrykket fra 10.11.2025 kl. 13.41, men Wayback svarte med avtrykket fra
05.12.2025. Avtrykket fra 10.11 er hentet for hånd og ligger ikke i
arkivet. Artikkelteksten i de to er tegn for tegn lik (5 990 tegn). Det
som skiller dem, er sidekrom rundt artikkelen. MÅLT.

### Ordrett

Alle sitatene er fra instruksen av 27.09.2024 med mindre noe annet er
oppgitt.

**Fordelingsnøkkelen**

> «Både kommunenes og fylkeskommunenes andel fordeles forholdsmessig
> basert på klarert lokalitets-MTB i den enkelte kommune og
> fylkeskommune, slik det går frem av akvakulturregistreret 1. september
> kl. 12.00 i utbetalingsåret.»

**Måledatoen:** «1. september kl. 12.00 i utbetalingsåret» (samme
setning). For 2026 betyr det 01.09.2026 kl. 12.00, altså 10.00 UTC.

**Arter og lokaliteter**

> «Lokalitets-MTB (maksimal tillatt biomasse) for alminnelige
> matfisktillatelser og tillatelser til særlige formål benyttes for
> fordelingsnøkkel. Kun lokaliteter for laks, ørret og regnbueørret i
> sjøvann inngår i fordelingsnøkkelen.»

**Lokaliteter over en kommunegrense**

> «Dersom det kartfestede arealbeslaget til en lokalitet (i overflaten),
> slik det er registrert i Akvakulturregisteret, krysser en kommunegrense
> (og eventuelt fylkesgrense), så skal utbetalingen denne lokaliteten gir
> opphav til, fordeles mellom angjeldende kommuner (og eventuelt
> fylkeskommuner) i samsvar med lokalitetens kartfestede arealbeslag
> innenfor hver av kommunene.»

**Delingen mellom kommuner og fylkeskommuner**

> «Utbetalingene fra Havbruksfondet fordeles med 80% til kommuner og 20%
> til fylkeskommuner, fra og med utbetalingsåret 2024.»

Instruksen av 2022 hadde «7/8 og 1/8».

**Regelen for ny biomasse**

> «En del av kommunenes andel, tilsvarende 1/8 av midlene som utbetales
> gjennom Havbruksfondet, kommer til fordeling blant kommuner som har
> klarert ny lokalitets-MTB innenfor en toårsperiode. Denne utbetalingen
> er oppad begrenset til 5 millioner kroner per enkeltkommune. Det
> eventuelt overskytende beløpet fordeles på alle kommuner basert på
> andel av lokalitets-MTB.»

> «Ved fordeling av midlene som skal fordeles med utgangspunkt i ny
> lokalitets-MTB, skal Fiskeridirektoratet legge til grunn ny
> lokalitets-MTB i en periode fra 1. september kl 12.00 i oddetallsår, og
> to kalenderår tilbake i tid. Det gjøres ikke fratrekk for
> lokalitets-MTB som har bortfalt i perioden.»

> «Generelt legger departementet opp til at utbetalingene til kommuner i
> partallsår fordeles etter klarert lokalitets-MTB, mens kommuner med ny
> klarert lokalitets-MTB tilgodeses for dette i oddetallsår.»

**«1/8 av midlene» betyr 1/8 av to års utbetalinger.** Det er MÅLT
fra regnearkene og orienteringen. Orienteringen for 2025 avsetter
763 165 711 kr til ny lokalitets-MTB. Utbetalingen i 2024 var
3 756 322 151,20 + 939 080 537,80 = 4 695 402 689,00 kr (regnearket
2024). Utbetalingen i 2025 var 1 409 923 000 kr. Summen delt på 8 er
**763 165 711,1 kr**, altså samme beløp ned til kronen. 2026 er et
partallsår, så utbetalingen i 2026 har ingen nyklarert-del, og hele
kommunenes andel fordeles etter stående MTB.

**Andel av kapasitetssalget som går til fondet**

Fastpris 2024 (`regjeringen-pressemeldinger/2024-06-06`):

> «De samlede inntektene fra fastpristildelingen var 476 millioner
> kroner, hvorav 55 prosent går til kommuner og fylkeskommuner gjennom
> Havbruksfondet.»

Auksjon 2024 (`regjeringen-pressemeldinger/2024-06-25`):

> «55 prosent av inntektene fra auksjonen fordeles til kommuner og
> fylkeskommuner med havbruksvirksomhet gjennom Havbruksfondet. Dette
> kommer i tillegg til 55 prosent av inntektene fra
> fastpristildelingen, samt produksjonsavgiften i sin helhet.»

**Produksjonsavgiften.** Faktaboksen i pressemeldingen 10.11.2025:

> «Havbruksfondet tilføres 55 prosent av inntektene for salg av nye
> oppdrettstillatelser, og produksjonsavgiften på fisk i sin helhet.»

### Hva som mangler, og hvorfor jeg ikke stoppet

Nøkkelen (hvem som får hvilken andel) er entydig: måledato, arter,
lokaliteter, deling og nybiomasseregel står ordrett i én instruks. Det
var det A2 trengte. Hullene gjelder hvor mye penger som kommer inn, og
det berører A7. A7 er et gulv av andre grunner også. Derfor gikk jeg
videre. Mener du at hullene under burde ha stoppet arbeidet, gjelder
A2–A7 med forbeholdet.

1. **55 % står bare i pressemeldinger.** Vedtaket bak andelen
   (budsjettvedtaket i Stortinget) er ikke arkivert. Andelen er oppgitt
   for 2024-runden og gjentatt i en faktaboks 10.11.2025. **Ingen kropp
   fra 2026 oppgir den.** UBELAGT for 2026.
2. **Unntaksvekst er ikke nevnt.** Ingen kropp sier hvor stor andel av
   unntaksveksten som går til fondet. Unntaksveksten selges til samme
   pris som fastpris (270 000 kr/t, pressemeldingen 10.09.2026). UBELAGT.
3. **Bokføringsperioden er borte fra instruksen.** Instruksen av 2022
   sa: «Direktoratet utbetaler midler fra salgs- og auksjonsinntekter
   bokført i perioden fra og med 1. september foregående år til og med
   31. august året for utbetalingen.» Instruksen av 2024 har ikke
   setningen. Ble regelen fra 2022 videreført, havner salget etter
   fristen 28.09.2026 i utbetalingen **2027**, ikke 2026. Det er
   UBELAGT hvilken regel som gjelder nå. Beløpet bestemmes uansett av
   den årlige orienteringen, som ifølge instruksen «fordrer
   budsjettfullmakt fra Stortinget».
4. **«Alminnelige matfisktillatelser og tillatelser til særlige
   formål».** Regelverket sier ikke hvordan en lokalitet med bare
   tillatelser for andre arter skal behandles. I 2025 tok
   Fiskeridirektoratet med to slike lokaliteter og holdt ni andre
   utenfor. Se A2.

---

## A2. Andelene

    .venv/bin/python analyse/havbruksfond/a2_andeler.py

Skriptet bruker `analyse/havbruksfond/felles.py`. Tabellene under er
utskriften fra kjøringen 12.10.2026, uendret.

### Hva målingen sier om 01.09.2026 kl. 12.00

Registeret har ingen tidsakse, så tilstanden ved måledatoen kan ikke
hentes i ettertid. Snapshotet på den ene siden ble hentet 31.08.2026 kl.
11.27 UTC, nesten et døgn før. Snapshotet på den andre siden ble hentet
07.09.2026 kl. 10.00 UTC, seks døgn etter. **Mellom de to kom ingen
lokalitet til i utvalget, ingen falt ut, og ingen endret kapasitet.**
MÅLT mot begge kroppene. Begge gir derfor nøyaktig de samme andelene, og
de er andelene per 01.09.2026 kl. 12.00, med ett forbehold: en endring
som ble gjort og reversert mellom to hentinger, kan ikke ses.

### Filteret, og hvordan det er holdt mot Fiskeridirektoratets eget

**Vekten er `max(kapasitet, kapasitet_midlertidig)`, ikke `kapasitet`.**
Testen bruker de 954 lokalitetene som ikke har fått ny versjon siden
01.09.2025 kl. 12.00 (`versjon_gyldig_fra` før den datoen) og derfor må
ha samme tall nå som da. For alle 954 er Fiskeridirektoratets MTB lik
`max(kapasitet, kapasitet_midlertidig)`. Med `kapasitet` alene stemmer
946, med `kapasitet_midlertidig` alene 953. MÅLT. Første utkast av
målingen brukte `kapasitet`. Det ble rettet før push i en egen commit.
Største utslag var Kjølvika I i Gildeskål, som har 780 t `kapasitet`
og 2 576 t `kapasitet_midlertidig`.

Filteret har to ledd (se under). Ledd 2 kom til fordi `arter` på en
lokalitet sier hva lokaliteten er klarert for, ikke hvilke tillatelser
som står der. Begge ledd er holdt mot Fiskeridirektoratets egen
lokalitetsliste for 2025, arket «Lok. per. 01.09.25» i regnearket
`havbruksfondet/2026-10-12.8.bin.gz`:

- **Ledd 1 tar med alle 1 048 lokalitetene** fra deres 2025-liste
  som fortsatt finnes i registeret. 17 av de 1 065 i deres liste finnes
  ikke lenger. MÅLT.
- **Ledd 1 tar med 17 lokaliteter som ikke står på deres liste:**
  - **9 holdes utenfor av ledd 2.** De har bare tillatelser for andre
    arter (torsk, kveite, alger). MÅLT.
  - **7 er klarert første gang etter 01.09.2025** og kunne ikke stå på
    listen (se A4). MÅLT.
  - **1 er 38097 HØGÅS (Strand, 780 t).** Den står på
    Fiskeridirektoratets liste for 2024, mangler på listen for 2025 og
    har `versjon_aarsak = PERM_SITE_RESURRECTED` med
    `versjon_gyldig_fra` 03.10.2025. Den var altså ute av registeret
    01.09.2025 og kom tilbake en måned senere. MÅLT mot regnearkene og
    snapshotet.
- **Ledd 2 holder ute to lokaliteter som Fiskeridirektoratet regnet
  med i 2025:** 10768 INDRE KÅRVIK I (650 t) og 15236
  SKULGAMBUKT (975 t), begge Havbruksstasjonen i Tromsø med tillatelsene
  T-T-0032, T-T-0061 og T-T-0322. Ingen av dem har laks, ørret eller
  regnbueørret i eierskapskroppen 02.09.2026. Om de hadde det
  01.09.2025, kan ikke avgjøres; det finnes ingen eierskapskropp fra
  da. Uforklart. Virkningen er 1 625 t av 3,8 mill. t, altså
  0,043 prosentpoeng for Tromsø og mindre for alle andre.
- **Ingen lokalitet er altså med hos oss og utelatt hos dem uten en
  målt forklaring.** Det motsatte gjelder bare de to i Tromsø.

**Delte lokaliteter.** Instruksen deler en lokalitet over en
kommunegrense etter kartfestet arealbeslag. Kroppen vår har ett punkt
per lokalitet og ingen flate. Andelene for de ti lokalitetene
Fiskeridirektoratet delte i 2025, er tatt fra regnearket deres og brukt
uendret. MÅLBAR, ikke MÅLT, fordi en grense eller en
lokalitet kan ha flyttet seg siden. To av de ti byttet registrert
kommune mellom de to snapshotene: 19755 (1812 Sømna → 1813 Brønnøy) og
10181 (1532 Giske → 1580 Haram). Det endrer ikke andelene her, fordi
delingen tas fra regnearket og ikke fra kommunefeltet. Det viser at
kommunefeltet alene ikke kan brukes for disse lokalitetene. Ingen
lokalitet som har kommet til etter 01.09.2025, er delt hos oss. Om noen
av dem krysser en grense, vet vi ikke.

**Sammenslåtte og delte kommuner.** Kommuner og kommunenumre er de
samme i Fiskeridirektoratets regneark for 2025 og i snapshotet
31.08.2026. Ingen kommune er slått sammen eller delt mellom de to
datoene. For hver lokalitet som finnes i begge, er kommunenummeret vårt
blant deres. MÅLT. Fylkene utledes av kommunenummeret
(`fylkesnummer` == de to første sifrene i `kommunenummer` for alle 1 779
lokaliteter, MÅLT). Reformen 01.01.2024, som delte Troms og Finnmark,
ligger altså allerede i både 2025 og 2026.

### Filteret

```
Ledd 1, akvakultursnapshotet (data/raw/akvakultur/<dato>.parquet):
    'SALMON' in arter            (laks, ørret, regnbueørret)
    vanntype        == 'Salt'
    plasseringstype == 'Offshore'
    kapasitet_enhet == 'TN'      (MTB i tonn)
  Ikke filtrert på: klareringstype (PERMANENT og TEMPORARY tas med),
  er_slakteri, har_kommersiell_aktivitet.
Ledd 2, eierskapskroppen (data/arkiv/eierskap/<dato>.json.gz):
    holdes UTENFOR hvis lokaliteten har aktive koblinger og INGEN av
    tillatelsene har laks (071101), ørret (071301) eller regnbueørret
    (071401) i species.fishCodes. Uten aktive koblinger: holdes inne.
Vekt: mtb = max(kapasitet, kapasitet_midlertidig), tonn.
Kommune: kommunenummer. Fylke: fylkesnummer.
Delte lokaliteter: andelen fra Fiskeridirektoratets 2025-regneark.
```

### Kroppene

| | akvakultur | raw_hash (arkivkroppen) | parquet sha256 | hentet |
|---|---|---|---|---|
| 2026-08-31 | `data/raw/akvakultur/2026-08-31.parquet` | `ae33535555c13634c19485170fe028d7db1a13be9ecd4ff34941474d5925563d` | `32e3883c439fe4413fd32bc8b44e6d58111aec7dd8b9893355c3ebaf8f26801e` | 2026-08-31T11:27:00.740210+00:00 |
| 2026-09-07 | `data/raw/akvakultur/2026-09-07.parquet` | `63fa21cce31fb43b32307bab2b50c9af1540582094e0285a042da7df2d8a26a3` | `9ef0424763afd9fcfca2bd1eb683371f325fb915a764038e0bcb43b0bf01c31a` | 2026-09-07T10:00:19.584925+00:00 |

Tillatelsesarter fra `data/arkiv/eierskap/2026-09-02.json.gz`, sha256 `6b22413510b5fbd59789e842f5f11dfc84df33fb0cdf4faf098e5ccf9bec39c9`.

| | lokaliteter i snapshotet | ledd 1 | holdt ute av ledd 2 | med | MTB med (tonn) | kommuner | fylker |
|---|---|---|---|---|---|---|---|
| 2026-08-31 | 1779 | 1065 | 11 | 1054 | 3 815 004 | 143 | 8 |
| 2026-09-07 | 1779 | 1065 | 11 | 1054 | 3 815 004 | 143 | 8 |

#### Holdt ute av ledd 2 (31.08)

- 10768 INDRE KÅRVIK I (TROMSØ), 650 t — T-T-0032
- 11411 LILLEELV (HADSEL), 780 t — N-H-0010
- 11737 SKORPA (GULEN), 150 t — VL-G-0003
- 12233 STOKKENESET (STAD), 1 560 t — SF-S-0026; SF-S-0027
- 12634 INNERNESSET (FLATANGER), 300 t — NT-F-0030
- 15236 SKULGAMBUKT (TROMSØ), 975 t — T-T-0032; T-T-0061; T-T-0322
- 16797 FOLDERØYHOLMEN (BØMLO), 1 560 t — H-B-0049; VL-B-0007
- 18595 YTTERHAVNA (SORTLAND), 325 t — N-SO-0003
- 22296 GRØNSET (GJEMNES), 3 120 t — M-GS-0010; M-GS-0011; M-GS-0014; M-GS-0015
- 26876 LANGNESET (HADSEL), 780 t — N-H-0029
- 29417 YTRE VASSHOLMEN (HERØY I NORDLAND), 780 t — N-HR-0078

#### Delte lokaliteter (andel fra Fiskeridirektoratet 01.09.2025)

- 10181: 1532 0.3524, 1580 0.6476 (med)
- 10229: 1576 0.0004, 5055 0.9996 (med)
- 11015: 1818 0.6326, 1820 0.3674 (med)
- 11665: 4631 0.9711, 4632 0.0289 (med)
- 13246: 1514 0.3890, 1515 0.6110 (med)
- 13527: 1865 0.0556, 1866 0.9445 (med)
- 14679: 1867 0.6463, 1870 0.3537 (med)
- 19755: 1812 0.3313, 1813 0.6688 (med)
- 33797: 1103 0.0023, 1130 0.9977 (med)
- 45002: 1834 0.9931, 1836 0.0069 (med)

### Endringer 2026-08-31 → 2026-09-07 i det filtrerte utvalget

**Kom til: 0**


**Forsvant: 0**


**Endret MTB: 0**


**Byttet kommunenummer: 2**
- 10181 1532 → 1580
- 19755 1812 → 1813

### Kommunenumre mot Fiskeridirektoratets 2025-regneark

Lokaliteter i begge der vårt kommunenummer ikke er blant Fiskeridirektoratets: **0**

Kommunenumre med MTB 2025 men ikke 31.08.2026: []
Kommunenumre med MTB 31.08.2026 men ikke 2025: []

### Fylkeskommunene

| fylke | MTB 31.08 | andel 31.08 | andel 07.09 |
|---|---|---|---|
| 18 Nordland | 791 956 | 20.7590% | 20.7590% |
| 46 Vestland | 787 759 | 20.6490% | 20.6490% |
| 50 Trøndelag | 713 229 | 18.6954% | 18.6954% |
| 55 Troms | 574 112 | 15.0488% | 15.0488% |
| 56 Finnmark | 386 541 | 10.1321% | 10.1321% |
| 15 Møre og Romsdal | 328 222 | 8.6034% | 8.6034% |
| 11 Rogaland | 200 490 | 5.2553% | 5.2553% |
| 42 Agder | 32 695 | 0.8570% | 0.8570% |

### Kommunene, alle 143

| # | komnr | kommune | MTB 31.08 | andel 31.08 | andel 07.09 | delt |
|---|---|---|---|---|---|---|
| 1 | 5014 | FRØYA | 174 866 | 4.5836% | 4.5836% |  |
| 2 | 5060 | NÆRØYSUND | 146 795 | 3.8478% | 3.8478% |  |
| 3 | 5530 | SENJA | 130 604 | 3.4234% | 3.4234% |  |
| 4 | 5603 | HAMMERFEST | 116 091 | 3.0430% | 3.0430% |  |
| 5 | 5056 | HITRA | 102 950 | 2.6986% | 2.6986% |  |
| 6 | 5534 | KARLSØY | 75 640 | 1.9827% | 1.9827% |  |
| 7 | 4602 | KINN | 75 150 | 1.9699% | 1.9699% |  |
| 8 | 1103 | STAVANGER | 72 548 | 1.9017% | 1.9017% | ja |
| 9 | 1573 | SMØLA | 72 540 | 1.9014% | 1.9014% |  |
| 10 | 5601 | ALTA | 71 515 | 1.8746% | 1.8746% |  |
| 11 | 5503 | HARSTAD | 63 385 | 1.6615% | 1.6615% |  |
| 12 | 4617 | KVINNHERAD | 61 050 | 1.6003% | 1.6003% |  |
| 13 | 5058 | ÅFJORD | 58 020 | 1.5208% | 1.5208% |  |
| 14 | 5501 | TROMSØ | 57 438 | 1.5056% | 1.5056% |  |
| 15 | 4626 | ØYGARDEN | 56 910 | 1.4917% | 1.4917% |  |
| 16 | 1866 | HADSEL | 56 037 | 1.4689% | 1.4689% | ja |
| 17 | 1836 | RØDØY | 55 298 | 1.4495% | 1.4495% | ja |
| 18 | 5049 | FLATANGER | 54 040 | 1.4165% | 1.4165% |  |
| 19 | 1848 | STEIGEN | 53 220 | 1.3950% | 1.3950% |  |
| 20 | 5542 | SKJERVØY | 52 770 | 1.3832% | 1.3832% |  |
| 21 | 4625 | AUSTEVOLL | 52 420 | 1.3740% | 1.3740% |  |
| 22 | 1834 | LURØY | 50 972 | 1.3361% | 1.3361% | ja |
| 23 | 5055 | HEIM | 49 358 | 1.2938% | 1.2938% | ja |
| 24 | 4631 | ALVER | 49 315 | 1.2927% | 1.2927% | ja |
| 25 | 4613 | BØMLO | 46 560 | 1.2204% | 1.2204% |  |
| 26 | 1875 | HAMARØY | 46 400 | 1.2163% | 1.2163% |  |
| 27 | 1838 | GILDESKÅL | 45 891 | 1.2029% | 1.2029% |  |
| 28 | 5514 | IBESTAD | 45 170 | 1.1840% | 1.1840% |  |
| 29 | 4635 | GULEN | 44 570 | 1.1683% | 1.1683% |  |
| 30 | 4636 | SOLUND | 43 860 | 1.1497% | 1.1497% |  |
| 31 | 5618 | MÅSØY | 41 574 | 1.0897% | 1.0897% |  |
| 32 | 4624 | BJØRNAFJORDEN | 39 690 | 1.0404% | 1.0404% |  |
| 33 | 1818 | HERØY I NORDLAND | 39 598 | 1.0379% | 1.0379% | ja |
| 34 | 5614 | LOPPA | 36 239 | 0.9499% | 0.9499% |  |
| 35 | 1811 | BINDAL | 35 380 | 0.9274% | 0.9274% |  |
| 36 | 1870 | SORTLAND | 34 224 | 0.8971% | 0.8971% | ja |
| 37 | 5007 | NAMSOS | 34 060 | 0.8928% | 0.8928% |  |
| 38 | 4616 | TYSNES | 33 480 | 0.8776% | 0.8776% |  |
| 39 | 5052 | LEKA | 33 360 | 0.8744% | 0.8744% |  |
| 40 | 5620 | NORDKAPP | 33 235 | 0.8712% | 0.8712% |  |
| 41 | 4648 | BREMANGER | 31 200 | 0.8178% | 0.8178% |  |
| 42 | 4645 | ASKVOLL | 30 420 | 0.7974% | 0.7974% |  |
| 43 | 1827 | DØNNA | 29 340 | 0.7691% | 0.7691% |  |
| 44 | 1813 | BRØNNØY | 28 564 | 0.7487% | 0.7487% | ja |
| 45 | 1580 | HARAM | 27 991 | 0.7337% | 0.7337% | ja |
| 46 | 1868 | ØKSNES | 27 439 | 0.7192% | 0.7192% |  |
| 47 | 5546 | KVÆNANGEN | 27 000 | 0.7077% | 0.7077% |  |
| 48 | 1837 | MELØY | 26 700 | 0.6999% | 0.6999% |  |
| 49 | 4207 | FLEKKEFJORD | 26 520 | 0.6951% | 0.6951% |  |
| 50 | 4637 | HYLLESTAD | 26 520 | 0.6951% | 0.6951% |  |
| 51 | 5616 | HASVIK | 26 472 | 0.6939% | 0.6939% |  |
| 52 | 1547 | AUKRA | 24 960 | 0.6543% | 0.6543% |  |
| 53 | 1845 | SØRFOLD | 24 900 | 0.6527% | 0.6527% |  |
| 54 | 1820 | ALSTAHAUG | 24 818 | 0.6505% | 0.6505% | ja |
| 55 | 1804 | BODØ | 24 766 | 0.6492% | 0.6492% |  |
| 56 | 5528 | DYRØY | 24 575 | 0.6442% | 0.6442% |  |
| 57 | 1576 | AURE | 23 402 | 0.6134% | 0.6134% | ja |
| 58 | 1865 | VÅGAN | 23 311 | 0.6110% | 0.6110% | ja |
| 59 | 5512 | TJELDSUND | 23 240 | 0.6092% | 0.6092% |  |
| 60 | 1146 | TYSVÆR | 23 100 | 0.6055% | 0.6055% |  |
| 61 | 5624 | LEBESBY | 23 025 | 0.6035% | 0.6035% |  |
| 62 | 4638 | HØYANGER | 22 620 | 0.5929% | 0.5929% |  |
| 63 | 4622 | KVAM | 22 319 | 0.5850% | 0.5850% |  |
| 64 | 5057 | ØRLAND | 21 840 | 0.5725% | 0.5725% |  |
| 65 | 1806 | NARVIK | 21 040 | 0.5515% | 0.5515% |  |
| 66 | 1851 | LØDINGEN | 20 428 | 0.5355% | 0.5355% |  |
| 67 | 1506 | MOLDE | 19 790 | 0.5187% | 0.5187% |  |
| 68 | 5059 | ORKLAND | 19 220 | 0.5038% | 0.5038% |  |
| 69 | 4615 | FITJAR | 18 740 | 0.4912% | 0.4912% |  |
| 70 | 5020 | OSEN | 18 720 | 0.4907% | 0.4907% |  |
| 71 | 5516 | GRATANGEN | 18 120 | 0.4750% | 0.4750% |  |
| 72 | 4612 | SVEIO | 17 940 | 0.4702% | 0.4702% |  |
| 73 | 4630 | OSTERØY | 17 940 | 0.4702% | 0.4702% |  |
| 74 | 1505 | KRISTIANSUND | 17 940 | 0.4702% | 0.4702% |  |
| 75 | 5510 | KVÆFJORD | 17 870 | 0.4684% | 0.4684% |  |
| 76 | 1554 | AVERØY | 17 590 | 0.4611% | 0.4611% |  |
| 77 | 1867 | BØ I NORDLAND | 17 176 | 0.4502% | 0.4502% | ja |
| 78 | 4618 | ULLENSVANG | 17 160 | 0.4498% | 0.4498% |  |
| 79 | 5605 | SØR-VARANGER | 16 260 | 0.4262% | 0.4262% |  |
| 80 | 1160 | VINDAFJORD | 16 080 | 0.4215% | 0.4215% |  |
| 81 | 4649 | STAD | 16 080 | 0.4215% | 0.4215% |  |
| 82 | 1520 | ØRSTA | 14 820 | 0.3885% | 0.3885% |  |
| 83 | 1535 | VESTNES | 14 040 | 0.3680% | 0.3680% |  |
| 84 | 1860 | VESTVÅGØY | 13 560 | 0.3554% | 0.3554% |  |
| 85 | 4646 | FJALER | 13 260 | 0.3476% | 0.3476% |  |
| 86 | 1133 | HJELMELAND | 13 140 | 0.3444% | 0.3444% |  |
| 87 | 1145 | BOKN | 12 880 | 0.3376% | 0.3376% |  |
| 88 | 1134 | SULDAL | 12 580 | 0.3298% | 0.3298% |  |
| 89 | 1577 | VOLDA | 12 480 | 0.3271% | 0.3271% |  |
| 90 | 1816 | VEVELSTAD | 12 480 | 0.3271% | 0.3271% |  |
| 91 | 5632 | BÅTSFJORD | 11 570 | 0.3033% | 0.3033% |  |
| 92 | 1812 | SØMNA | 11 395 | 0.2987% | 0.2987% | ja |
| 93 | 4634 | MASFJORDEN | 11 020 | 0.2889% | 0.2889% |  |
| 94 | 1511 | VANYLVEN | 10 920 | 0.2862% | 0.2862% |  |
| 95 | 5636 | UNJÁRGA - NESSEBY | 10 560 | 0.2768% | 0.2768% |  |
| 96 | 1828 | NESNA | 10 140 | 0.2658% | 0.2658% |  |
| 97 | 1853 | EVENES | 9 600 | 0.2516% | 0.2516% |  |
| 98 | 5522 | SALANGEN | 9 600 | 0.2516% | 0.2516% |  |
| 99 | 1106 | HAUGESUND | 9 540 | 0.2501% | 0.2501% |  |
| 100 | 1108 | SANDNES | 9 410 | 0.2467% | 0.2467% |  |
| 101 | 1579 | HUSTADVIKA | 9 360 | 0.2453% | 0.2453% |  |
| 102 | 1840 | SALTDAL | 9 119 | 0.2390% | 0.2390% |  |
| 103 | 4611 | ETNE | 9 010 | 0.2362% | 0.2362% |  |
| 104 | 5518 | LOABÁK - LAVANGEN | 9 000 | 0.2359% | 0.2359% |  |
| 105 | 1841 | FAUSKE | 8 596 | 0.2253% | 0.2253% |  |
| 106 | 1149 | KARMØY | 8 580 | 0.2249% | 0.2249% |  |
| 107 | 1144 | KVITSØY | 8 280 | 0.2170% | 0.2170% |  |
| 108 | 1815 | VEGA | 7 620 | 0.1997% | 0.1997% |  |
| 109 | 1560 | TINGVOLL | 7 520 | 0.1971% | 0.1971% |  |
| 110 | 1130 | STRAND | 7 492 | 0.1964% | 0.1964% | ja |
| 111 | 4632 | AUSTRHEIM | 7 125 | 0.1868% | 0.1868% | ja |
| 112 | 5544 | NORDREISA | 7 100 | 0.1861% | 0.1861% |  |
| 113 | 1557 | GJEMNES | 7 020 | 0.1840% | 0.1840% |  |
| 114 | 1578 | FJORD | 7 020 | 0.1840% | 0.1840% |  |
| 115 | 1508 | ÅLESUND | 6 720 | 0.1761% | 0.1761% |  |
| 116 | 1532 | GISKE | 6 329 | 0.1659% | 0.1659% | ja |
| 117 | 4627 | ASKØY | 6 240 | 0.1636% | 0.1636% |  |
| 118 | 1833 | RANA | 6 240 | 0.1636% | 0.1636% |  |
| 119 | 1525 | STRANDA | 6 240 | 0.1636% | 0.1636% |  |
| 120 | 1514 | SANDE I MØRE OG ROMSDAL | 5 724 | 0.1500% | 0.1500% | ja |
| 121 | 1151 | UTSIRA | 5 460 | 0.1431% | 0.1431% |  |
| 122 | 1539 | RAUMA | 5 460 | 0.1431% | 0.1431% |  |
| 123 | 5536 | LYNGEN | 5 400 | 0.1415% | 0.1415% |  |
| 124 | 4614 | STORD | 4 680 | 0.1227% | 0.1227% |  |
| 125 | 1822 | LEIRFJORD | 4 680 | 0.1227% | 0.1227% |  |
| 126 | 1515 | HERØY I MØRE OG ROMSDAL | 4 116 | 0.1079% | 0.1079% | ja |
| 127 | 4650 | GLOPPEN | 3 900 | 0.1022% | 0.1022% |  |
| 128 | 1835 | TRÆNA | 3 600 | 0.0944% | 0.0944% |  |
| 129 | 5526 | SØRREISA | 3 600 | 0.0944% | 0.0944% |  |
| 130 | 5540 | GÁIVUOTNA - KÅFJORD - KAIVUONO | 3 600 | 0.0944% | 0.0944% |  |
| 131 | 1871 | ANDØY | 3 184 | 0.0835% | 0.0835% |  |
| 132 | 1859 | FLAKSTAD | 3 120 | 0.0818% | 0.0818% |  |
| 133 | 4623 | SAMNANGER | 3 120 | 0.0818% | 0.0818% |  |
| 134 | 4633 | FEDJE | 3 120 | 0.0818% | 0.0818% |  |
| 135 | 1528 | SYKKYLVEN | 3 120 | 0.0818% | 0.0818% |  |
| 136 | 1824 | VEFSN | 3 120 | 0.0818% | 0.0818% |  |
| 137 | 1516 | ULSTEIN | 2 340 | 0.0613% | 0.0613% |  |
| 138 | 4206 | FARSUND | 2 340 | 0.0613% | 0.0613% |  |
| 139 | 4225 | LYNGDAL | 2 340 | 0.0613% | 0.0613% |  |
| 140 | 4628 | VAKSDAL | 2 340 | 0.0613% | 0.0613% |  |
| 141 | 4215 | LILLESAND | 1 495 | 0.0392% | 0.0392% |  |
| 142 | 1122 | GJESDAL | 1 400 | 0.0367% | 0.0367% |  |
| 143 | 1566 | SURNADAL | 780 | 0.0204% | 0.0204% |  |

---

## A3. Kontroll mot 2025

    .venv/bin/python analyse/havbruksfond/a3_kontroll_2025.py

Grunnlaget er to kropper fra 2025. Pressemeldingen 10.11.2025 er hentet
via Wayback (regjeringen.no svarer 403) og ligger i
`regjeringen-pressemeldinger/2025-11-10.bin.gz`. Den har tabellen
KOMMUNE/TOTALT for 143 kommuner og beløpene for 8 fylkeskommuner.
Fiskeridirektoratets regneark for 2025 ligger i
`havbruksfondet/2026-10-12.8.bin.gz`. Det deler TOTALT i ANDEL
NYKLARERT og ORDINÆR UTBETALING og lister hver lokalitet med MTB per
01.09.2025. Begge er arkivert i A1.

### Det viktigste først

- **De to 2025-kroppene er enige** om beløpet til alle 143 kommuner,
  med avvik under 1 kr. MÅLT.
- **Rangkorrelasjonen er ρ = 0,940 mot TOTALT og ρ = 0,997 mot ORDINÆR.**
  2025 var et oddetallsår: 763 mill. av kommunenes 1 128 mill. kr gikk
  etter ny MTB, så TOTALT-andelen 2025 er en annen størrelse enn en
  andel av stående MTB. Uten nyklarert-delen er sammenhengen nesten
  perfekt. MÅLT.
- **Alle de 10 største avvikene mot TOTALT forklares av
  nyklarert-delen 2025.** Kommuner som fikk inntil 5 mill. kr for ny
  MTB i 2025 (Bokn, Tingvoll, Saltdal, Båtsfjord, Stad, Bremanger), ligger
  lavere i 2026. Kommuner som ikke fikk noe (Kinn, Stavanger, Harstad),
  ligger høyere. For Frøya, Bokn, Kinn, Harstad og Bremanger kommer det
  i tillegg en mindre del som skyldes lokaliteter. Ingen av de ti er
  uforklart. MÅLT: avviket er delt i to ledd regnet av de to
  kroppene, og lokalitetene er holdt mot regnearkets liste.
- **Alle de 10 største avvikene mot ORDINÆR forklares av lokaliteter**
  som har kommet til, forsvunnet eller endret MTB siden 01.09.2025.
  Ingen er uforklart. Det største er Skjervøy, −0,150 prosentpoeng,
  fordi én lokalitet på 5 400 t er borte. MÅLT lokalitet for lokalitet.
- Fylkeskommunene avviker med høyst 0,32 prosentpoeng (Nordland).
  Fylkenes andel 2025 hadde ingen nyklarert-del, så her er det bare
  stående MTB som skiller.

Dette er en rimelighetskontroll og ikke en fasit. 2025 bygger på
registeret ett år før, og det fanger ikke opp en feil som er lik i både
deres og vår metode.

### Kroppene

- pressemelding: `data/arkiv/regjeringen-pressemeldinger/2025-11-10.bin.gz`, sha256 `35b92f454817a8bc6430314b69b2b799a296e84f2feee60d0a1fe6d2396b8a69`
- regneark: `data/arkiv/havbruksfondet/2026-10-12.8.bin.gz`, sha256 `e26cfffe259153d0f9fd9d84c3f2a89b3d904e290c0f48f5978a667e38308b76`

### Pressemeldingen mot regnearket

- kommuner i pressemeldingen: 143, i regnearket: 143
- navn i pressemeldingen uten treff i regnearket: []
- kommuner der beløpet avviker med 1 kr eller mer: 0
- sum kommuner 1 127 938 403 + fylker 281 984 600 = 1 409 923 003 (avrunding); «Totalt:» 1 409 923 000

### Rangkorrelasjon (Spearman)

- A2 31.08.2026 mot TOTALT 2025, 143 kommuner (mangler = 0): **ρ = 0.9398**
- samme, bare de 143 som finnes i begge: ρ = 0.9398
- A2 mot ORDINÆR 2025 (uten nyklarert-delen), 143 kommuner: ρ = 0.9967
- bare i 2025: []
- bare i 2026: []

### De 20 største

| # 2025 | kommune | andel 2025 TOTALT | andel 2026 (A2) | # 2026 |
|---|---|---|---|---|
| 1 | FRØYA | 4.047% | 4.584% | 1 |
| 2 | NÆRØYSUND | 3.612% | 3.848% | 2 |
| 3 | SENJA | 3.198% | 3.423% | 3 |
| 4 | HAMMERFEST | 2.957% | 3.043% | 4 |
| 5 | HITRA | 2.631% | 2.699% | 5 |
| 6 | SMØLA | 1.973% | 1.901% | 9 |
| 7 | ALTA | 1.952% | 1.875% | 10 |
| 8 | KARLSØY | 1.937% | 1.983% | 6 |
| 9 | TROMSØ | 1.678% | 1.506% | 14 |
| 10 | ÅFJORD | 1.667% | 1.521% | 13 |
| 11 | HADSEL | 1.625% | 1.469% | 16 |
| 12 | RØDØY | 1.609% | 1.449% | 17 |
| 13 | KVINNHERAD | 1.601% | 1.600% | 12 |
| 14 | LURØY | 1.601% | 1.336% | 22 |
| 15 | KINN | 1.568% | 1.970% | 7 |
| 16 | STAVANGER | 1.530% | 1.902% | 8 |
| 17 | STEIGEN | 1.436% | 1.395% | 19 |
| 18 | HAMARØY | 1.422% | 1.216% | 26 |
| 19 | GILDESKÅL | 1.411% | 1.203% | 27 |
| 20 | SOLUND | 1.368% | 1.150% | 30 |

### De 10 største avvikene (prosentpoeng, A2 minus TOTALT 2025)

| kommune | 2025 TOTALT | 2026 A2 | avvik | av det: nyklarert 2025 | av det: stående MTB | forklaring |
|---|---|---|---|---|---|---|
| FRØYA | 4.047% | 4.584% | +0.537 | +0.458 | +0.079 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den); lokaliteter: 1 nye, 4 borte, 5 endret, netto +3 996 t |
| BOKN | 0.739% | 0.338% | -0.402 | -0.369 | -0.032 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den); lokaliteter: 0 nye, 0 borte, 1 endret, netto -1 150 t |
| KINN | 1.568% | 1.970% | +0.401 | +0.392 | +0.009 | nyklarert-delen 2025 (kommunen fikk 0 kr av den); lokaliteter: 0 nye, 0 borte, 1 endret, netto +780 t |
| TINGVOLL | 0.595% | 0.197% | -0.398 | -0.397 | -0.001 | nyklarert-delen 2025 (kommunen fikk 4 923 240 kr av den) |
| SALTDAL | 0.636% | 0.239% | -0.397 | -0.395 | -0.001 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den) |
| BÅTSFJORD | 0.687% | 0.303% | -0.384 | -0.382 | -0.002 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den) |
| BREMANGER | 1.200% | 0.818% | -0.382 | -0.254 | -0.128 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den); lokaliteter: 0 nye, 1 borte, 1 endret, netto -4 680 t |
| HARSTAD | 1.288% | 1.661% | +0.374 | +0.322 | +0.052 | nyklarert-delen 2025 (kommunen fikk 0 kr av den); lokaliteter: 0 nye, 0 borte, 1 endret, netto +2 330 t |
| STAVANGER | 1.530% | 1.902% | +0.372 | +0.383 | -0.011 | nyklarert-delen 2025 (kommunen fikk 0 kr av den) |
| STAD | 0.782% | 0.421% | -0.361 | -0.358 | -0.002 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den) |

### De 10 største avvikene mot ORDINÆR 2025 (prosentpoeng)

Nyklarert-delen er tatt ut. Det som står igjen, er forskjell i stående MTB: lokaliteter som kom, forsvant eller endret MTB, og at alle andre kommuners MTB flyttet seg (nevneren).

| kommune | ORDINÆR 2025 | 2026 A2 | avvik | MTB 2025 | MTB 2026 | forklaring |
|---|---|---|---|---|---|---|
| SKJERVØY | 1.534% | 1.383% | -0.150 | 58 170 | 52 770 | 0 nye, 1 borte, 0 endret: −36237 5 400 t |
| HARAM | 0.594% | 0.734% | +0.140 | 22 531 | 27 991 | 1 nye, 0 borte, 1 endret: +45299 4 680 t, 12281 +780 t |
| BREMANGER | 0.946% | 0.818% | -0.128 | 35 880 | 31 200 | 0 nye, 1 borte, 1 endret: −13550 3 120 t, 12224 -1 560 t |
| KARLSØY | 1.868% | 1.983% | +0.115 | 70 840 | 75 640 | 0 nye, 0 borte, 2 endret: 10757 +1 800 t, 36257 +3 000 t |
| NÆRØYSUND | 3.961% | 3.848% | -0.113 | 150 239 | 146 795 | 0 nye, 2 borte, 1 endret: −13959 3 120 t, −26335 3 120 t, 45262 +2 796 t |
| LURØY | 1.447% | 1.336% | -0.111 | 54 872 | 50 972 | 0 nye, 2 borte, 0 endret: −21337 2 340 t, −26675 1 560 t |
| HERØY I NORDLAND | 0.936% | 1.038% | +0.101 | 35 520 | 39 598 | 1 nye, 0 borte, 1 endret: +45300 3 599 t, 37857 +479 t |
| SØMNA | 0.198% | 0.299% | +0.101 | 7 495 | 11 395 | 1 nye, 0 borte, 0 endret: +45282 3 900 t |
| SORTLAND | 0.797% | 0.897% | +0.100 | 30 224 | 34 224 | 1 nye, 0 borte, 0 endret: +45301 4 000 t |
| HAMMERFEST | 3.143% | 3.043% | -0.100 | 119 211 | 116 091 | 0 nye, 1 borte, 0 endret: −34577 3 120 t |

### Lokalitetene bak avvikene mot TOTALT

**FRØYA**
- ny siden 01.09.2025: 45280, 4 776 t
- borte siden 01.09.2025: 24456, 3 120 t
- borte siden 01.09.2025: 24696, 3 900 t
- borte siden 01.09.2025: 30437, 3 120 t
- borte siden 01.09.2025: 31959, 5 460 t
- endret: 12394, +3 900 t
- endret: 12435, +3 120 t
- endret: 14042, +3 120 t
- endret: 28636, +5 460 t
- endret: 33757, -780 t

**BOKN**
- endret: 38957, -1 150 t

**KINN**
- endret: 39577, +780 t

**BREMANGER**
- borte siden 01.09.2025: 13550, 3 120 t
- endret: 12224, -1 560 t

**HARSTAD**
- endret: 26055, +2 330 t

### Fylkeskommunene

| fylke | 2025 | 2026 A2 | avvik (pp) |
|---|---|---|---|
| Vestland | 20.818% | 20.649% | -0.169 |
| Nordland | 20.435% | 20.759% | +0.324 |
| Trøndelag | 18.810% | 18.695% | -0.114 |
| Troms | 15.178% | 15.049% | -0.130 |
| Finnmark | 10.210% | 10.132% | -0.078 |
| Møre og Romsdal | 8.392% | 8.603% | +0.212 |
| Rogaland | 5.296% | 5.255% | -0.040 |
| Agder | 0.862% | 0.857% | -0.005 |

Samlet MTB i nøkkelen: Fiskeridirektoratet 01.09.2025 3 793 021 t, A2 31.08.2026 3 815 004 t (+0.58%)

---

## A4. Ny biomasse

    .venv/bin/python analyse/havbruksfond/a4_ny_biomasse.py [snapshotdato]

**Perioden.** Etter instruksen gjelder perioden «fra 1. september kl 12.00
i oddetallsår, og to kalenderår tilbake i tid». Neste oddetallsår er
2027, så perioden som løper nå, er **01.09.2025 kl. 12.00 –
01.09.2027 kl. 12.00**. Den utbetales i 2027. Utbetalingen i 2026 har
ingen nyklarert-del (A1). Kjøringen under er gjort mot snapshotet
12.10.2026.

### Svaret: `forste_klarering` gir MÅLBAR, ikke MÅLT

Med `forste_klarering` fra 01.09.2025 kl. 12.00 får vi **7 lokaliteter
i 7 kommuner, 27 675 t**. Feltet måler noe annet enn regelverket.
Regelverket teller *ny lokalitets-MTB*. Feltet sier når en *lokalitet*
ble klarert første gang. Fiskeridirektoratets regneark for 2025 viser
forskjellen. Arket «Økt kapasitet» har 67 rader: 24 nye lokaliteter
(107 945 t) og 43 lokaliteter som fantes fra før og fikk mer MTB
(60 244 t).

- `forste_klarering` fanger alle **24 av 24** nye lokaliteter fra
  2025. Den delen måler feltet riktig. MÅLT.
- Den ser ikke økningen på lokaliteter som fantes fra før. Det var
  **35,8 % av ny MTB i 2025**. MÅLT.

### Bedre: Fiskeridirektoratets egen startverdi

Periodens startpunkt er 01.09.2025. Fiskeridirektoratets lokalitetsliste
per den dagen er arkivert (A1), og det er den regnearket kaller
«HistKap». Nå minus da, lokalitet for lokalitet og bare økninger, gir
**29 kommuner, 37 lokaliteter og 82 608 t** per 12.10.2026 (tabellen
nederst). Det er nærmere regelverket, men fortsatt MÅLBAR og ikke MÅLT,
av tre grunner:

1. En økning som er gjort og reversert mellom to av våre hentinger,
   ses ikke. Fiskeridirektoratet gjør «ikke fratrekk for
   lokalitets-MTB som har bortfalt», så den ville trolig telt med hos
   dem.
2. 38097 HØGÅS er telt som ny (780 t). Den var ute av registeret
   01.09.2025 og kom tilbake 03.10.2025 (A2). Om Fiskeridirektoratet
   regner en gjenoppstått lokalitet som ny MTB, er UBELAGT.
3. Delte lokaliteter er fordelt med andelene fra 2025.

Taket på 5 mill. kr per kommune og potten for 2027 er ikke regnet ut.
Potten er 1/8 av utbetalingene i 2026 og 2027, og ingen av dem er kjent.

### Versjonsfeltet som snarvei: testet, og det mister en femtedel

`versjon_aarsak = CAPACITY_CHANGE` med `versjon_gyldig_fra` i perioden
peker på 34 av de 43 økningene fra 2025 (46 785 av 60 244 t). De andre ni
har fått en senere versjon av en annen grunn (koordinater, areal,
vedtaksstatus), eller en senere kapasitetsendring. Bare siste versjon
står i snapshotet. MÅLT. Feltet sier heller ikke hvor stor endringen
var, eller i hvilken retning.

### Kontroll mot Fiskeridirektoratets 2025-regneark

Regneark `data/arkiv/havbruksfondet/2026-10-12.8.bin.gz`, sha256 `e26cfffe259153d0f9fd9d84c3f2a89b3d904e290c0f48f5978a667e38308b76`.

- rader i «Økt kapasitet»: 67
- av dem nye lokaliteter (HistKap 0): 24, 107 945 t
- av dem økt MTB på eksisterende lokalitet: 43, 60 244 t
- **andel av ny MTB 2025 som forste_klarering ikke kan se: 35.8%**
- nye lokaliteter 2025 med forste_klarering i 01.09.2023–01.09.2025 i vårt snapshot 2026-10-12: 24 av 24
- økt MTB 2025 der `versjon_aarsak` = CAPACITY_CHANGE med `versjon_gyldig_fra` i perioden, i snapshot 2026-10-12: 34 av 43, 46 785 av 60 244 t
  - de andre, etter `versjon_aarsak` i dag: AREA_EVENT 2, CAPACITY_CHANGE 2, COORDINATES 4, DECISION_STATUS_CHANGED 1

### Lokaliteter i nøkkelen med forste_klarering fra 2025-09-01T10:00:00Z (snapshot 2026-10-12)

Snapshot `data/raw/akvakultur/2026-10-12.parquet`, raw_hash `69a4c7efaf2f423e294d4c8cff4ec8c36abc227503b7ff268f8fd94cc7917c9d`.

| lokalitet | navn | kommune | MTB | forste_klarering | klarering |
|---|---|---|---|---|---|
| 45299 | HARAM | 1580 HARAM | 4 680 | 2026-06-15 | PERMANENT |
| 45282 | LAKSVIKA | 1812 SØMNA | 3 900 | 2026-01-29 | PERMANENT |
| 45300 | SKIPBÅTSVÆR | 1818 HERØY I NORDLAND | 3 599 | 2026-06-16 | PERMANENT |
| 45298 | FORNES I | 1853 EVENES | 3 600 | 2026-06-06 | PERMANENT |
| 45301 | KINNHOLMEN | 1870 SORTLAND | 4 000 | 2026-07-02 | PERMANENT |
| 45280 | KLOVNINGAN | 5014 FRØYA | 4 776 | 2026-01-06 | TEMPORARY |
| 45289 | BÅRÅSA | 5057 ØRLAND | 3 120 | 2026-04-12 | PERMANENT |

**7 kommuner, 7 lokaliteter, 27 675 t**

| kommune | lokaliteter | MTB (t) |
|---|---|---|
| 5014 FRØYA | 1 | 4 776 |
| 1580 HARAM | 1 | 4 680 |
| 1870 SORTLAND | 1 | 4 000 |
| 1812 SØMNA | 1 | 3 900 |
| 1853 EVENES | 1 | 3 600 |
| 1818 HERØY I NORDLAND | 1 | 3 599 |
| 5057 ØRLAND | 1 | 3 120 |

### Økt MTB på lokaliteter som fantes 2026-08-17 (snapshot 2026-10-12)

Serien begynner 2026-08-17. Økning mellom 01.09.2025 og 2026-08-17 kan ikke ses.

- 16281 KASTEVIKA (BØMLO): 780 → 1 200 t (+420)

### Lokaliteter fra før perioden med kapasitetsendring fra 2025-09-01T10:00:00Z (`versjon_aarsak`, snapshot 2026-10-12)

Retningen og størrelsen står ikke i feltet; bare at kapasiteten ble endret, og når.

| lokalitet | navn | kommune | MTB nå | versjon_gyldig_fra |
|---|---|---|---|---|
| 12265 | GUDMUNDSET | 1508 ÅLESUND | 3 120 | 2026-01-19 |
| 20815 | SLETTVIKA | 1520 ØRSTA | 4 680 | 2026-05-17 |
| 27395 | RINDARØY | 1547 AUKRA | 1 560 | 2026-01-14 |
| 12839 | VINDSNES | 1578 FJORD | 3 900 | 2026-01-25 |
| 22335 | STORVIKA | 1579 HUSTADVIKA | 6 240 | 2026-04-07 |
| 12281 | ROGNE | 1580 HARAM | 7 800 | 2025-11-23 |
| 35737 | SÆTEROSEN | 1813 BRØNNØY | 3 599 | 2026-07-14 |
| 36317 | VARHOLMEN | 1813 BRØNNØY | 5 460 | 2026-01-08 |
| 37857 | SEISKJÆRET | 1818 HERØY I NORDLAND | 3 599 | 2026-01-19 |
| 45037 | Kjølvika I | 1838 GILDESKÅL | 2 576 | 2026-09-24 |
| 27996 | KALVHODET | 1865 VÅGAN | 4 990 | 2026-02-11 |
| 20897 | GISLØY S | 1868 ØKSNES | 3 600 | 2026-07-16 |
| 39577 | SILDA | 4602 KINN | 3 120 | 2026-07-19 |
| 16281 | KASTEVIKA | 4613 BØMLO | 1 200 | 2026-09-28 |
| 11575 | KOLØY N | 4615 FITJAR | 2 340 | 2026-07-01 |
| 26295 | LANGØY | 4631 ALVER | 8 280 | 2026-05-05 |
| 11803 | KYRAVIKA | 4646 FJALER | 4 680 | 2025-11-25 |
| 12394 | ØRNØYA | 5014 FRØYA | 8 580 | 2026-01-05 |
| 12435 | GRØTTINGSØY | 5014 FRØYA | 10 140 | 2026-01-08 |
| 14042 | KATTHOLMEN | 5014 FRØYA | 7 800 | 2025-12-21 |
| 28636 | RATAREN | 5014 FRØYA | 10 920 | 2025-12-21 |
| 33757 | HÅBRANDEN | 5014 FRØYA | 5 460 | 2025-12-14 |
| 12348 | KÅHOLMEN | 5056 HITRA | 3 900 | 2026-06-30 |
| 13503 | HEGGVIKA | 5056 HITRA | 4 680 | 2026-06-30 |
| 33417 | PERSFLUA | 5057 ØRLAND | 3 120 | 2026-04-12 |
| 30297 | KRABBHOLMEN | 5058 ÅFJORD | 6 240 | 2026-01-05 |
| 45262 | TAREGGA ØST | 5060 NÆRØYSUND | 3 600 | 2025-10-27 |
| 13804 | ROGNDALEN | 5501 TROMSØ | 3 599 | 2026-06-02 |
| 26055 | TOPPSUND Ø | 5503 HARSTAD | 8 000 | 2026-02-17 |
| 26615 | HAUG | 5510 KVÆFJORD | 4 280 | 2026-06-25 |
| 31177 | HILDERKLEIVA | 5510 KVÆFJORD | 1 200 | 2026-03-13 |
| 10757 | DÅVØYA | 5534 KARLSØY | 7 200 | 2025-11-23 |
| 36257 | MJØNES | 5534 KARLSØY | 10 200 | 2025-11-23 |

**33 lokaliteter i 25 kommuner.**

### Ny lokalitets-MTB fra 01.09.2025 til 2026-10-12, per kommune

Nå (snapshot) minus Fiskeridirektoratets lokalitetsliste per 01.09.2025, bare økninger. «ny» = lokaliteten sto ikke på lista.

| kommune | ny MTB (t) | lokaliteter |
|---|---|---|
| 5014 FRØYA | 20 376 | 12394 +3 900, 12435 +3 120, 14042 +3 120, 28636 +5 460, 45280 (ny) +4 776 |
| 1580 HARAM | 5 460 | 12281 +780, 45299 (ny) +4 680 |
| 5534 KARLSØY | 4 800 | 10757 +1 800, 36257 +3 000 |
| 1818 HERØY I NORDLAND | 4 078 | 37857 +479, 45300 (ny) +3 599 |
| 1870 SORTLAND | 4 000 | 45301 (ny) +4 000 |
| 1812 SØMNA | 3 900 | 45282 (ny) +3 900 |
| 4631 ALVER | 3 600 | 26295 +3 600 |
| 1853 EVENES | 3 600 | 45298 (ny) +3 600 |
| 1813 BRØNNØY | 3 599 | 35737 +1 259, 36317 +2 340 |
| 5058 ÅFJORD | 3 120 | 30297 +3 120 |
| 5057 ØRLAND | 3 120 | 45289 (ny) +3 120 |
| 5060 NÆRØYSUND | 2 796 | 45262 +2 796 |
| 5624 LEBESBY | 2 400 | 13337 +2 400 |
| 5503 HARSTAD | 2 330 | 26055 +2 330 |
| 1865 VÅGAN | 1 870 | 27996 +1 870 |
| 4615 FITJAR | 1 560 | 11575 +1 560 |
| 4646 FJALER | 1 560 | 11803 +1 560 |
| 1508 ÅLESUND | 1 560 | 12265 +1 560 |
| 1520 ØRSTA | 1 560 | 20815 +1 560 |
| 1868 ØKSNES | 1 260 | 20897 +1 260 |
| 1578 FJORD | 780 | 12839 +780 |
| 5056 HITRA | 780 | 13503 +780 |
| 1579 HUSTADVIKA | 780 | 22335 +780 |
| 1130 STRAND | 780 | 38097 (ny) +780 |
| 4602 KINN | 780 | 39577 +780 |
| 5510 KVÆFJORD | 680 | 26615 +680 |
| 1547 AUKRA | 560 | 27395 +560 |
| 5501 TROMSØ | 499 | 13804 +499 |
| 4613 BØMLO | 420 | 16281 +420 |

**29 kommuner, 37 lokaliteter, 82 608 t.**

---

## A5. Anslaget

### Formatet kan ikke bære det, og det er tre grunner til det

Målt mot `core/predictions.py`, ikke bare mot malen:

1. **Det finnes ingen kilde.** Et anslag avgjøres med
   `snapshot.les_mellom(kilde, fra, til)`. Utbetalingen fra fondet er
   ingen kilde i `sources/`. Uten snapshots blir utfallet
   `kan_ikke_avgjores` («ingen utgangsverdi ved vindusstart»).
2. **Ingen av typene passer.** `endring` og `uendret` måler prosent
   bevegelse fra en utgangsverdi i et snapshot. `verdi` krever at
   strengen er nøyaktig lik. Anslaget sier at en andel havner innenfor
   et intervall rundt et tall vi har regnet ut. Det er ingen av de tre.
3. **Påstanden gjelder 143 entiteter.** Malen har én `entitet` per
   anslag.

**Hva som må til:**

- en kilde `sources/havbruksfond.py` som leser Fiskeridirektoratets
  regneark (`havbruksfondet/`, arkivert i A1 og fanget av A6). Den
  skal gi én observasjon per kommune og fylkeskommune
  (`entity_id` = kommunenummer, felt `andel` og `utbetaling`) med
  `observed_at` = måledatoen 01.09. Det er én ny fil og ingen endring i
  `core/` (regel 1);
- en ny type i `core/predictions.py`, for eksempel `intervall` med
  `verdi_min` og `verdi_max`. Det **er** en endring i `core/`, og den
  avgjør du;
- én prediksjon per kommune, laget av et skript fra A2-tabellen, i
  stedet for én påstand om alle.

### Anslaget, ferdig utfylt unntatt konfidens

Referanseverdiene er A2-tabellen «Kommunene, alle 143» og
«Fylkeskommunene» over, slik de står i commit `a4608a3`. `vindu.fra`
må være datoen du committer fila, eller senere (valideringen krever det).
Fila skal hete etter samme dato.

```yaml
prediksjoner:
  - id: "<dato>-1"
    entitet: "kommuner"            # FORMATET BÆRER DET IKKE: gjelder alle 143
    kilde: "havbruksfond"          # FINNES IKKE i sources/ (se over)
    felt: "andel"
    type: "intervall"              # FINNES IKKE i core/predictions.TYPER
    verdi_min: "A2-andel − 0,05 prosentpoeng, per kommune"
    verdi_max: "A2-andel + 0,05 prosentpoeng, per kommune"
    vindu:
      fra: "<dato>"
      til: "2026-12-31"
    grunnlag: >
      Utbetalingen 2026 er i et partallsår. Etter instruksen av 27.09.2024
      fordeles da hele kommunenes andel etter klarert lokalitets-MTB per
      01.09.2026 kl. 12.00, uten nyklarert-del. A2 har regnet ut denne
      andelen fra registeret 31.08.2026 og 07.09.2026, og de to
      snapshotene er like. Filteret og vekten (max av kapasitet og
      midlertidig kapasitet) er holdt mot Fiskeridirektoratets egen
      lokalitetsliste for 2025. Der stemmer vekten for 954 av 954
      lokaliteter som ikke er endret siden. Andelen per kommune er da
      MTB i kommunen delt på samlet MTB, og den skal treffe
      Fiskeridirektoratets tall med mindre de har brukt en lokalitet vi
      holder ute eller utelatt en vi tar med.
    feil_hvis: >
      Én av disse fire er nok til at påstanden faller.
      (1) Tabellen «Utbetalinger fra Havbruksfondet 2026» har en kolonne
      ANDEL NYKLARERT med beløp over 0 for noen kommune. Da er
      partallsregelen ikke fulgt.
      (2) Kommunesettet er ikke de samme 143 kommunenumrene som i A2.
      (3) For minst én kommune avviker TOTALT / sum TOTALT for kommunene
      mer enn 0,05 prosentpoeng fra A2.
      (4) For minst én fylkeskommune avviker andelen mer enn 0,05
      prosentpoeng fra A2.
      Mekanismen er feil hvis Fiskeridirektoratets lokalitetsliste per
      01.09.2026 tar med eller utelater andre lokaliteter enn filteret
      gjør. To kjente kandidater er Havbruksstasjonen i Tromsø (1 625 t)
      og HØGÅS (780 t).
    konfidens:                     # fylles av Heine
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
```

**Hvordan anslaget avgjøres for hånd mot 2025-formatet:** ta
regnearket for 2026 (A6 arkiverer det), arket «Utbetalingsoversikt». Del
TOTALT per KOMNR på summen for kommunene, og del BELØP per FYLKESNR i
arket «Fylkeskommuner» på summen for fylkeskommunene. Hold tallene mot
A2-tabellene, kommune for kommune. Pressemeldingen har samme tabell med
kommunenavn i stedet for nummer. A3 viser at de to stemmer overens.

**Hvorfor ±0,05 prosentpoeng:** den største kjente usikkerheten er
Havbruksstasjonen i Tromsø. Den gir 0,043 prosentpoeng for Tromsø hvis
Fiskeridirektoratet tar lokalitetene med igjen. Alle andre kjente
forskjeller er mindre. Det er en terskel, ikke et konfidensintervall.
