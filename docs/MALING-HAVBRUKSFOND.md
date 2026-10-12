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
Vekt: kapasitet (MTB, tonn). Kommune: kommunenummer. Fylke: fylkesnummer.
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
| 2026-08-31 | 1779 | 1065 | 11 | 1054 | 3 795 214 | 143 | 8 |
| 2026-09-07 | 1779 | 1065 | 11 | 1054 | 3 795 214 | 143 | 8 |

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


**Endret kapasitet: 0**


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
| 46 Vestland | 785 779 | 20.7045% | 20.7045% |
| 18 Nordland | 785 066 | 20.6857% | 20.6857% |
| 50 Trøndelag | 704 649 | 18.5668% | 18.5668% |
| 55 Troms | 573 712 | 15.1167% | 15.1167% |
| 56 Finnmark | 386 541 | 10.1850% | 10.1850% |
| 15 Møre og Romsdal | 326 282 | 8.5972% | 8.5972% |
| 11 Rogaland | 200 490 | 5.2827% | 5.2827% |
| 42 Agder | 32 695 | 0.8615% | 0.8615% |

### Kommunene, alle 143

| # | komnr | kommune | MTB 31.08 | andel 31.08 | andel 07.09 | delt |
|---|---|---|---|---|---|---|
| 1 | 5014 | FRØYA | 172 526 | 4.5459% | 4.5459% |  |
| 2 | 5060 | NÆRØYSUND | 143 675 | 3.7857% | 3.7857% |  |
| 3 | 5530 | SENJA | 130 604 | 3.4413% | 3.4413% |  |
| 4 | 5603 | HAMMERFEST | 116 091 | 3.0589% | 3.0589% |  |
| 5 | 5056 | HITRA | 102 950 | 2.7126% | 2.7126% |  |
| 6 | 5534 | KARLSØY | 75 640 | 1.9930% | 1.9930% |  |
| 7 | 4602 | KINN | 74 370 | 1.9596% | 1.9596% |  |
| 8 | 1103 | STAVANGER | 72 548 | 1.9116% | 1.9116% | ja |
| 9 | 1573 | SMØLA | 72 540 | 1.9114% | 1.9114% |  |
| 10 | 5601 | ALTA | 71 515 | 1.8843% | 1.8843% |  |
| 11 | 5503 | HARSTAD | 63 385 | 1.6701% | 1.6701% |  |
| 12 | 4617 | KVINNHERAD | 59 850 | 1.5770% | 1.5770% |  |
| 13 | 5501 | TROMSØ | 57 438 | 1.5134% | 1.5134% |  |
| 14 | 4626 | ØYGARDEN | 56 910 | 1.4995% | 1.4995% |  |
| 15 | 1836 | RØDØY | 55 298 | 1.4570% | 1.4570% | ja |
| 16 | 5058 | ÅFJORD | 54 900 | 1.4466% | 1.4466% |  |
| 17 | 5049 | FLATANGER | 54 040 | 1.4239% | 1.4239% |  |
| 18 | 1866 | HADSEL | 53 337 | 1.4054% | 1.4054% | ja |
| 19 | 1848 | STEIGEN | 52 440 | 1.3817% | 1.3817% |  |
| 20 | 4625 | AUSTEVOLL | 52 420 | 1.3812% | 1.3812% |  |
| 21 | 5542 | SKJERVØY | 52 370 | 1.3799% | 1.3799% |  |
| 22 | 1834 | LURØY | 50 972 | 1.3431% | 1.3431% | ja |
| 23 | 5055 | HEIM | 49 358 | 1.3005% | 1.3005% | ja |
| 24 | 4631 | ALVER | 49 315 | 1.2994% | 1.2994% | ja |
| 25 | 4613 | BØMLO | 46 560 | 1.2268% | 1.2268% |  |
| 26 | 1875 | HAMARØY | 46 240 | 1.2184% | 1.2184% |  |
| 27 | 5514 | IBESTAD | 45 170 | 1.1902% | 1.1902% |  |
| 28 | 4635 | GULEN | 44 570 | 1.1744% | 1.1744% |  |
| 29 | 1838 | GILDESKÅL | 43 900 | 1.1567% | 1.1567% |  |
| 30 | 4636 | SOLUND | 43 860 | 1.1557% | 1.1557% |  |
| 31 | 5618 | MÅSØY | 41 574 | 1.0954% | 1.0954% |  |
| 32 | 4624 | BJØRNAFJORDEN | 39 690 | 1.0458% | 1.0458% |  |
| 33 | 1818 | HERØY I NORDLAND | 39 598 | 1.0434% | 1.0434% | ja |
| 34 | 5614 | LOPPA | 36 239 | 0.9549% | 0.9549% |  |
| 35 | 1811 | BINDAL | 35 380 | 0.9322% | 0.9322% |  |
| 36 | 1870 | SORTLAND | 34 224 | 0.9018% | 0.9018% | ja |
| 37 | 5007 | NAMSOS | 34 060 | 0.8974% | 0.8974% |  |
| 38 | 4616 | TYSNES | 33 480 | 0.8822% | 0.8822% |  |
| 39 | 5052 | LEKA | 33 360 | 0.8790% | 0.8790% |  |
| 40 | 5620 | NORDKAPP | 33 235 | 0.8757% | 0.8757% |  |
| 41 | 4648 | BREMANGER | 31 200 | 0.8221% | 0.8221% |  |
| 42 | 4645 | ASKVOLL | 30 420 | 0.8015% | 0.8015% |  |
| 43 | 1827 | DØNNA | 29 340 | 0.7731% | 0.7731% |  |
| 44 | 1580 | HARAM | 27 991 | 0.7375% | 0.7375% | ja |
| 45 | 1868 | ØKSNES | 27 439 | 0.7230% | 0.7230% |  |
| 46 | 1813 | BRØNNØY | 27 305 | 0.7195% | 0.7195% | ja |
| 47 | 5546 | KVÆNANGEN | 27 000 | 0.7114% | 0.7114% |  |
| 48 | 1837 | MELØY | 26 700 | 0.7035% | 0.7035% |  |
| 49 | 4637 | HYLLESTAD | 26 520 | 0.6988% | 0.6988% |  |
| 50 | 4207 | FLEKKEFJORD | 26 520 | 0.6988% | 0.6988% |  |
| 51 | 5616 | HASVIK | 26 472 | 0.6975% | 0.6975% |  |
| 52 | 1845 | SØRFOLD | 24 900 | 0.6561% | 0.6561% |  |
| 53 | 1820 | ALSTAHAUG | 24 818 | 0.6539% | 0.6539% | ja |
| 54 | 1804 | BODØ | 24 766 | 0.6526% | 0.6526% |  |
| 55 | 5528 | DYRØY | 24 575 | 0.6475% | 0.6475% |  |
| 56 | 1547 | AUKRA | 23 800 | 0.6271% | 0.6271% |  |
| 57 | 1576 | AURE | 23 402 | 0.6166% | 0.6166% | ja |
| 58 | 1865 | VÅGAN | 23 311 | 0.6142% | 0.6142% | ja |
| 59 | 5512 | TJELDSUND | 23 240 | 0.6124% | 0.6124% |  |
| 60 | 1146 | TYSVÆR | 23 100 | 0.6087% | 0.6087% |  |
| 61 | 5624 | LEBESBY | 23 025 | 0.6067% | 0.6067% |  |
| 62 | 4638 | HØYANGER | 22 620 | 0.5960% | 0.5960% |  |
| 63 | 4622 | KVAM | 22 319 | 0.5881% | 0.5881% |  |
| 64 | 5057 | ØRLAND | 21 840 | 0.5755% | 0.5755% |  |
| 65 | 1806 | NARVIK | 21 040 | 0.5544% | 0.5544% |  |
| 66 | 1851 | LØDINGEN | 20 428 | 0.5383% | 0.5383% |  |
| 67 | 1506 | MOLDE | 19 790 | 0.5214% | 0.5214% |  |
| 68 | 5059 | ORKLAND | 19 220 | 0.5064% | 0.5064% |  |
| 69 | 4615 | FITJAR | 18 740 | 0.4938% | 0.4938% |  |
| 70 | 5020 | OSEN | 18 720 | 0.4933% | 0.4933% |  |
| 71 | 5516 | GRATANGEN | 18 120 | 0.4774% | 0.4774% |  |
| 72 | 1505 | KRISTIANSUND | 17 940 | 0.4727% | 0.4727% |  |
| 73 | 4612 | SVEIO | 17 940 | 0.4727% | 0.4727% |  |
| 74 | 4630 | OSTERØY | 17 940 | 0.4727% | 0.4727% |  |
| 75 | 5510 | KVÆFJORD | 17 870 | 0.4709% | 0.4709% |  |
| 76 | 1554 | AVERØY | 17 590 | 0.4635% | 0.4635% |  |
| 77 | 1867 | BØ I NORDLAND | 17 176 | 0.4526% | 0.4526% | ja |
| 78 | 4618 | ULLENSVANG | 17 160 | 0.4521% | 0.4521% |  |
| 79 | 5605 | SØR-VARANGER | 16 260 | 0.4284% | 0.4284% |  |
| 80 | 1160 | VINDAFJORD | 16 080 | 0.4237% | 0.4237% |  |
| 81 | 4649 | STAD | 16 080 | 0.4237% | 0.4237% |  |
| 82 | 1520 | ØRSTA | 14 820 | 0.3905% | 0.3905% |  |
| 83 | 1535 | VESTNES | 14 040 | 0.3699% | 0.3699% |  |
| 84 | 1860 | VESTVÅGØY | 13 560 | 0.3573% | 0.3573% |  |
| 85 | 4646 | FJALER | 13 260 | 0.3494% | 0.3494% |  |
| 86 | 1133 | HJELMELAND | 13 140 | 0.3462% | 0.3462% |  |
| 87 | 1145 | BOKN | 12 880 | 0.3394% | 0.3394% |  |
| 88 | 1134 | SULDAL | 12 580 | 0.3315% | 0.3315% |  |
| 89 | 1816 | VEVELSTAD | 12 480 | 0.3288% | 0.3288% |  |
| 90 | 1577 | VOLDA | 12 480 | 0.3288% | 0.3288% |  |
| 91 | 5632 | BÅTSFJORD | 11 570 | 0.3049% | 0.3049% |  |
| 92 | 1812 | SØMNA | 11 395 | 0.3003% | 0.3003% | ja |
| 93 | 4634 | MASFJORDEN | 11 020 | 0.2904% | 0.2904% |  |
| 94 | 1511 | VANYLVEN | 10 920 | 0.2877% | 0.2877% |  |
| 95 | 5636 | UNJÁRGA - NESSEBY | 10 560 | 0.2782% | 0.2782% |  |
| 96 | 1828 | NESNA | 10 140 | 0.2672% | 0.2672% |  |
| 97 | 1853 | EVENES | 9 600 | 0.2530% | 0.2530% |  |
| 98 | 5522 | SALANGEN | 9 600 | 0.2530% | 0.2530% |  |
| 99 | 1106 | HAUGESUND | 9 540 | 0.2514% | 0.2514% |  |
| 100 | 1108 | SANDNES | 9 410 | 0.2479% | 0.2479% |  |
| 101 | 1579 | HUSTADVIKA | 9 360 | 0.2466% | 0.2466% |  |
| 102 | 1840 | SALTDAL | 9 119 | 0.2403% | 0.2403% |  |
| 103 | 4611 | ETNE | 9 010 | 0.2374% | 0.2374% |  |
| 104 | 5518 | LOABÁK - LAVANGEN | 9 000 | 0.2371% | 0.2371% |  |
| 105 | 1841 | FAUSKE | 8 596 | 0.2265% | 0.2265% |  |
| 106 | 1149 | KARMØY | 8 580 | 0.2261% | 0.2261% |  |
| 107 | 1144 | KVITSØY | 8 280 | 0.2182% | 0.2182% |  |
| 108 | 1815 | VEGA | 7 620 | 0.2008% | 0.2008% |  |
| 109 | 1560 | TINGVOLL | 7 520 | 0.1981% | 0.1981% |  |
| 110 | 1130 | STRAND | 7 492 | 0.1974% | 0.1974% | ja |
| 111 | 4632 | AUSTRHEIM | 7 125 | 0.1877% | 0.1877% | ja |
| 112 | 5544 | NORDREISA | 7 100 | 0.1871% | 0.1871% |  |
| 113 | 1557 | GJEMNES | 7 020 | 0.1850% | 0.1850% |  |
| 114 | 1508 | ÅLESUND | 6 720 | 0.1771% | 0.1771% |  |
| 115 | 1532 | GISKE | 6 329 | 0.1668% | 0.1668% | ja |
| 116 | 1578 | FJORD | 6 240 | 0.1644% | 0.1644% |  |
| 117 | 4627 | ASKØY | 6 240 | 0.1644% | 0.1644% |  |
| 118 | 1525 | STRANDA | 6 240 | 0.1644% | 0.1644% |  |
| 119 | 1833 | RANA | 6 240 | 0.1644% | 0.1644% |  |
| 120 | 1514 | SANDE I MØRE OG ROMSDAL | 5 724 | 0.1508% | 0.1508% | ja |
| 121 | 1151 | UTSIRA | 5 460 | 0.1439% | 0.1439% |  |
| 122 | 1539 | RAUMA | 5 460 | 0.1439% | 0.1439% |  |
| 123 | 5536 | LYNGEN | 5 400 | 0.1423% | 0.1423% |  |
| 124 | 4614 | STORD | 4 680 | 0.1233% | 0.1233% |  |
| 125 | 1822 | LEIRFJORD | 4 680 | 0.1233% | 0.1233% |  |
| 126 | 1515 | HERØY I MØRE OG ROMSDAL | 4 116 | 0.1085% | 0.1085% | ja |
| 127 | 4650 | GLOPPEN | 3 900 | 0.1028% | 0.1028% |  |
| 128 | 1835 | TRÆNA | 3 600 | 0.0949% | 0.0949% |  |
| 129 | 5526 | SØRREISA | 3 600 | 0.0949% | 0.0949% |  |
| 130 | 5540 | GÁIVUOTNA - KÅFJORD - KAIVUONO | 3 600 | 0.0949% | 0.0949% |  |
| 131 | 1871 | ANDØY | 3 184 | 0.0839% | 0.0839% |  |
| 132 | 1859 | FLAKSTAD | 3 120 | 0.0822% | 0.0822% |  |
| 133 | 4623 | SAMNANGER | 3 120 | 0.0822% | 0.0822% |  |
| 134 | 4633 | FEDJE | 3 120 | 0.0822% | 0.0822% |  |
| 135 | 1824 | VEFSN | 3 120 | 0.0822% | 0.0822% |  |
| 136 | 1528 | SYKKYLVEN | 3 120 | 0.0822% | 0.0822% |  |
| 137 | 4225 | LYNGDAL | 2 340 | 0.0617% | 0.0617% |  |
| 138 | 4206 | FARSUND | 2 340 | 0.0617% | 0.0617% |  |
| 139 | 4628 | VAKSDAL | 2 340 | 0.0617% | 0.0617% |  |
| 140 | 1516 | ULSTEIN | 2 340 | 0.0617% | 0.0617% |  |
| 141 | 4215 | LILLESAND | 1 495 | 0.0394% | 0.0394% |  |
| 142 | 1122 | GJESDAL | 1 400 | 0.0369% | 0.0369% |  |
| 143 | 1566 | SURNADAL | 780 | 0.0206% | 0.0206% |  |

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
  ligger høyere. For Frøya, Bokn, Harstad og Bremanger kommer det i
  tillegg en mindre del som skyldes lokaliteter. Ingen av de ti er
  uforklart. MÅLT: avviket er delt i to ledd regnet av de to
  kroppene, og lokalitetene er holdt mot regnearkets liste.
- **Alle de 10 største avvikene mot ORDINÆR forklares av lokaliteter**
  som har kommet til, forsvunnet eller endret MTB siden 01.09.2025.
  Ingen er uforklart. Den største er Nærøysund (−0,175 prosentpoeng: to
  lokaliteter borte, én redusert, én økt). MÅLT lokalitet for lokalitet.
- Fylkeskommunene avviker med høyst 0,25 prosentpoeng (Nordland).
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

- A2 31.08.2026 mot TOTALT 2025, 143 kommuner (mangler = 0): **ρ = 0.9395**
- samme, bare de 143 som finnes i begge: ρ = 0.9395
- A2 mot ORDINÆR 2025 (uten nyklarert-delen), 143 kommuner: ρ = 0.9966
- bare i 2025: []
- bare i 2026: []

### De 20 største

| # 2025 | kommune | andel 2025 TOTALT | andel 2026 (A2) | # 2026 |
|---|---|---|---|---|
| 1 | FRØYA | 4.047% | 4.546% | 1 |
| 2 | NÆRØYSUND | 3.612% | 3.786% | 2 |
| 3 | SENJA | 3.198% | 3.441% | 3 |
| 4 | HAMMERFEST | 2.957% | 3.059% | 4 |
| 5 | HITRA | 2.631% | 2.713% | 5 |
| 6 | SMØLA | 1.973% | 1.911% | 9 |
| 7 | ALTA | 1.952% | 1.884% | 10 |
| 8 | KARLSØY | 1.937% | 1.993% | 6 |
| 9 | TROMSØ | 1.678% | 1.513% | 13 |
| 10 | ÅFJORD | 1.667% | 1.447% | 16 |
| 11 | HADSEL | 1.625% | 1.405% | 18 |
| 12 | RØDØY | 1.609% | 1.457% | 15 |
| 13 | KVINNHERAD | 1.601% | 1.577% | 12 |
| 14 | LURØY | 1.601% | 1.343% | 22 |
| 15 | KINN | 1.568% | 1.960% | 7 |
| 16 | STAVANGER | 1.530% | 1.912% | 8 |
| 17 | STEIGEN | 1.436% | 1.382% | 19 |
| 18 | HAMARØY | 1.422% | 1.218% | 26 |
| 19 | GILDESKÅL | 1.411% | 1.157% | 29 |
| 20 | SOLUND | 1.368% | 1.156% | 30 |

### De 10 største avvikene (prosentpoeng, A2 minus TOTALT 2025)

| kommune | 2025 TOTALT | 2026 A2 | avvik | av det: nyklarert 2025 | av det: stående MTB | forklaring |
|---|---|---|---|---|---|---|
| FRØYA | 4.047% | 4.546% | +0.499 | +0.458 | +0.041 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den); lokaliteter: 1 nye, 4 borte, 5 endret, netto +1 656 t |
| BOKN | 0.739% | 0.339% | -0.400 | -0.369 | -0.031 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den); lokaliteter: 0 nye, 0 borte, 1 endret, netto -1 150 t |
| TINGVOLL | 0.595% | 0.198% | -0.397 | -0.397 | -0.000 | nyklarert-delen 2025 (kommunen fikk 4 923 240 kr av den) |
| SALTDAL | 0.636% | 0.240% | -0.395 | -0.395 | -0.000 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den) |
| KINN | 1.568% | 1.960% | +0.391 | +0.392 | -0.001 | nyklarert-delen 2025 (kommunen fikk 0 kr av den) |
| HARSTAD | 1.288% | 1.670% | +0.382 | +0.322 | +0.060 | nyklarert-delen 2025 (kommunen fikk 0 kr av den); lokaliteter: 0 nye, 0 borte, 1 endret, netto +2 330 t |
| BÅTSFJORD | 0.687% | 0.305% | -0.382 | -0.382 | -0.000 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den) |
| STAVANGER | 1.530% | 1.912% | +0.382 | +0.383 | -0.001 | nyklarert-delen 2025 (kommunen fikk 0 kr av den) |
| BREMANGER | 1.200% | 0.822% | -0.378 | -0.254 | -0.124 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den); lokaliteter: 0 nye, 1 borte, 1 endret, netto -4 680 t |
| STAD | 0.782% | 0.424% | -0.359 | -0.358 | -0.000 | nyklarert-delen 2025 (kommunen fikk 5 000 000 kr av den) |

### De 10 største avvikene mot ORDINÆR 2025 (prosentpoeng)

Nyklarert-delen er tatt ut. Det som står igjen, er forskjell i stående MTB: lokaliteter som kom, forsvant eller endret MTB, og at alle andre kommuners MTB flyttet seg (nevneren).

| kommune | ORDINÆR 2025 | 2026 A2 | avvik | MTB 2025 | MTB 2026 | forklaring |
|---|---|---|---|---|---|---|
| NÆRØYSUND | 3.961% | 3.786% | -0.175 | 150 239 | 143 675 | 0 nye, 2 borte, 2 endret: −13959 3 120 t, −26335 3 120 t, 37177 -3 120 t, 45262 +2 796 t |
| SKJERVØY | 1.534% | 1.380% | -0.154 | 58 170 | 52 370 | 0 nye, 1 borte, 1 endret: −36237 5 400 t, 32357 -400 t |
| HARAM | 0.594% | 0.738% | +0.144 | 22 531 | 27 991 | 1 nye, 0 borte, 1 endret: +45299 4 680 t, 12281 +780 t |
| KARLSØY | 1.868% | 1.993% | +0.125 | 70 840 | 75 640 | 0 nye, 0 borte, 2 endret: 10757 +1 800 t, 36257 +3 000 t |
| BREMANGER | 0.946% | 0.822% | -0.124 | 35 880 | 31 200 | 0 nye, 1 borte, 1 endret: −13550 3 120 t, 12224 -1 560 t |
| HERØY I NORDLAND | 0.936% | 1.043% | +0.107 | 35 520 | 39 598 | 1 nye, 0 borte, 1 endret: +45300 3 599 t, 37857 +479 t |
| SORTLAND | 0.797% | 0.902% | +0.105 | 30 224 | 34 224 | 1 nye, 0 borte, 0 endret: +45301 4 000 t |
| LURØY | 1.447% | 1.343% | -0.104 | 54 872 | 50 972 | 0 nye, 2 borte, 0 endret: −21337 2 340 t, −26675 1 560 t |
| SØMNA | 0.198% | 0.300% | +0.103 | 7 495 | 11 395 | 1 nye, 0 borte, 0 endret: +45282 3 900 t |
| EVENES | 0.158% | 0.253% | +0.095 | 6 000 | 9 600 | 1 nye, 0 borte, 0 endret: +45298 3 600 t |

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
- endret: 33757, -3 120 t

**BOKN**
- endret: 38957, -1 150 t

**HARSTAD**
- endret: 26055, +2 330 t

**BREMANGER**
- borte siden 01.09.2025: 13550, 3 120 t
- endret: 12224, -1 560 t

### Fylkeskommunene

| fylke | 2025 | 2026 A2 | avvik (pp) |
|---|---|---|---|
| Vestland | 20.818% | 20.704% | -0.113 |
| Nordland | 20.435% | 20.686% | +0.251 |
| Trøndelag | 18.810% | 18.567% | -0.243 |
| Troms | 15.178% | 15.117% | -0.062 |
| Finnmark | 10.210% | 10.185% | -0.025 |
| Møre og Romsdal | 8.392% | 8.597% | +0.205 |
| Rogaland | 5.296% | 5.283% | -0.013 |
| Agder | 0.862% | 0.861% | -0.000 |

Samlet MTB i nøkkelen: Fiskeridirektoratet 01.09.2025 3 793 021 t, A2 31.08.2026 3 795 214 t (+0.06%)
