# Sjøtemperatur — verifiseringsnotat og kildespesifikasjon

Verifisert mot levende tjeneste **24.08.2026**. Alt under er målt, ikke
antatt. Målingene er gjort på hele historikken der ikke annet står:
766 uker, 436 931 temperaturverdier.

Kilden er bygget: `sources/sjotemperatur.py`.

## 1. Endepunktet — to veier til samme tall

Utgangspunktet var det opplagte endepunktet:

    /v1/geodata/fishhealth/locality/{localityNo}/seatemperature/{year}

    → {localityNo, year, minMaxTemperatureIsSet, minSeaTemperature,
       maxSeaTemperature, data: [{week, seaTemperature, hasReported}, ...]}

Det virker, og oppløsningen er **ukentlig** — 52 eller 53 innslag per år,
med `null` for uker uten rapport. OpenAPI-beskrivelsen sier «weekly
reported sea temperature measured at or near a site», altså **målt**, ikke
modellert.

Aksen er derimot feil vei for dette repoet: én lokalitet per år per kall
er 1777 × 15 ≈ **26 000 kall** for full historikk.

Eksportendepunktet gir det samme på ukeaksen:

    /v1/geodata/download/fishhealth
        ?reporttype=Lice&filetype=csv
        &fromyear={år}&fromweek={uke}&toyear={år}&toweek={uke}

Alle lokaliteter for én uke i ett kall. **730 kall** for det samme.

### Krysset mot hverandre

Uke 30/2018, 12 lokaliteter, begge endepunktene:

    lokalitet   eksport-CSV   seatemperature/{år}
    15196          14.07          14.07
    12067          16.7           16.7
    12086          13.19          13.19
    11179          11.0           11.0
    38037           9.5            9.5
    13563          13.6           13.6
    13518          11.0           11.0
    29816          13.4           13.4
    14016          15.6           15.6
    12988          15.43          15.43
    12357          11.5           11.5
    11800          15.46          15.46

    avvik: 0 av 12

Dette er ikke to kilder til det samme tallet — det er to visninger av den
samme innrapporterte verdien. Kilden bruker eksporten.

**Prisen:** kolonnenavnene er norske og laget for et regneark
(`Sjøtemperatur`, `Lokalitetsnummer`, `Trolig uten fisk`), ikke for et
API. `filetype` har bare `Xlsx` og `Csv` — ingen JSON. Responsen har BOM
(`EF BB BF`). Kilden sjekker derfor at kolonnene finnes og kaster med
navns nevnelse hvis de er borte, og arkiverer rå-CSV-en før parse: en
omdøping blir en re-parse, ikke tapt historikk.

## 2. Tidsoppløsning og oppdateringsfrekvens

**Uke.** Temperaturen er ikke en egen serie — den er et felt i det samme
ukeskjemaet oppdretteren rapporterer lusetallet i.

Det avgjør frekvensen: `min_dager_mellom = 7`. En månedlig henting ville
mistet tre av fire uker permanent, siden snapshots er append-only og en
uke ikke kan hentes tilbake som en uke hvis den aldri ble skrevet.

## 3. Historisk dybde — 2012 uke 1

    2010 uke 1:     0 rader
    2011 uke 1:     0 rader
    2012 uke 1:  1117 rader

Samme fallgruve som lusetall: 2010 og 2011 gir `200 OK` med tom liste,
ikke 404. `backfill.py` stopper på første tomme uke og sier fra.

Dekning per år, uke 30, andel av rader med temperatur:

    2012 48.1%   2015 51.8%   2018 53.0%   2021 57.6%   2024 56.8%
    2013 51.0%   2016 50.0%   2019 54.3%   2022 55.0%   2025 55.6%
    2014 50.9%   2017 51.6%   2020 55.4%   2023 56.5%   2026 54.5%

De manglende ~45 % er brakklagte lokaliteter, som ikke skal måle noe.

## 4. Koblingen mot lusetall — 100 %

Det viktigste spørsmålet for analysen, og svaret er entydig. Av
lokalitetene som rapporterte lus i lusetall-endepunktet, hvor mange har
en temperatur i eksporten samme uke:

    uke 30/2012:  472 av 472   100,0 %
    uke 30/2018:  540 av 540   100,0 %
    uke 10/2022:  483 av 483   100,0 %
    uke 30/2026:  578 av 578   100,0 %

Koblingsnøkkelen er `Lokalitetsnummer`, som er det samme som
`localityNo` hos lusetall og `siteNr` hos Fiskeridirektoratet — allerede
verifisert 18.08, se BARENTSWATCH-FUNN.md.

Eksporten gir litt FLERE temperaturrader enn lusrapporter (530 mot 472 i
uke 30/2012): noen brakklagte lokaliteter måler temperatur likevel.

**Merk utvalgsforskjellen:** eksporten dekker bare lokaliteter med
laksetillatelse, ~1066 per uke mot lusetalls 1777. Det er nøyaktig de
lokalitetene som teller lus, så for analysen er dekningen komplett — men
kilden er smalere enn lusetall, og det er tilsiktet.

## 5. Etterslep — det samme som lusetall, ikke likt det

Temperaturen kommer i samme skjema som lustallet, så etterslepet er ikke
sammenlignbart med lusetalls — det er identisk. `uker_etterslep: 4`.

Andel av ikke-brakklagte lokaliteter med temperatur, målt 24.08.2026:

    uke 29   99,8 %      uke 33   97,0 %
    uke 30   99,5 %      uke 34   30,8 %   ← inneværende uke
    uke 31   99,7 %      uke 35    1,3 %
    uke 32   98,5 %      uke 36    0,0 %

### Hvorfor vakten måler akkurat denne brøken

Dette er et F10-spørsmål, og det er verdt å skrive ned hva som ble
forkastet:

- **«Andel av dem som telte lus som har temperatur»** er **100,0 % i hver
  eneste uke fra 2012 til 2026** — også i uke 35, der åtte lokaliteter
  har rapportert. Den ville aldri fyrt. Det er formen fra F10: et mål som
  er riktig akkurat der de to tingene faller sammen, og stille ellers.
- **«Andel av alle rader»** er ~55 % hver uke, fordi to tredeler er
  brakklagte. Den ville fyrt alltid.
- **«Andel av ikke-brakklagte»** skiller: 97–100 % på ferdige uker,
  30,8 % på den ferskeste. Det er den som brukes.

### Terskelen er målt, ikke gjettet

Over alle **763 ferdige uker** 2012–2026:

    laveste uke      76,8 %   (uke 21/2013)
    nest laveste     77,8 %   (uke 51/2012)
    tredje laveste   85,3 %   (uke 52/2012)
    p1               90,2 %
    p5               96,1 %
    median           99,4 %
    høyeste         100,0 %

    terskel 80 %:  2 falske alarmer av 763   (0,26 %)
    terskel 85 %:  2 falske alarmer av 763
    terskel 90 %:  7 falske alarmer av 763
    terskel 95 %: 27 falske alarmer av 763

`min_rapportert_andel: 0.80`. To falske alarmer, begge i oppstartsårene
2012–2013, og den ferskeste uka fanges med 49 prosentpoengs margin
(30,8 % mot 80 %).

Tallet er ikke utledet av feilen det skal fange — den kontrollen F10
krever. De ufullstendige ukene er målt for seg (uke 34–36/2026) og
inngår ikke i fordelingen over de 763.

At tallet er det samme som lusetalls er ikke en avskrift. Det er regnet
ut på nytt, på en annen brøk, over en annen kolonne.

## 6. Verdiområde — og uteliggerne som IKKE fjernes

436 931 verdier, 2012–2026:

    min      -0,2        p1      2,70
    p0.1      0,00       p5      3,86
    median    8,69       p95    15,40
    maks    196,18       p99    17,00
                         p99.9  19,68

98 % ligger mellom **2,7 og 17,0 grader** — som forventet på
oppdrettsdyp i norsk sjø.

    < 2 grader:    1619   (0,371 %)
    > 18 grader:   1422   (0,325 %)
    < 0 grader:       2   (-0,1 og -0,2, lokalitet 14016, uke 7-8/2026)
    > 25 grader:     56

De to negative er plausible — sjøvann fryser først ved −1,8 °C. De 56
over 25 er det ikke:

    196,18  (uke 24/2025, lok 13229)    98,00  (uke  9/2025, lok 11298)
    173,44  (uke 47/2024, lok 27015)    96,00  (uke 52/2023, lok 32717)
    158,90  (uke 33/2026, lok 38877)    96,00  (uke  3/2024, lok 12870)
    142,00  (uke 42/2025, lok 13345)    81,19  (uke 19/2024, lok 31777)

Alle i 2023–2026. Dette er tastefeil hos innrapportør.

**Kilden fjerner dem ikke, og advarer ikke om dem.**

- Å fjerne dem ville vært kilden som redigerer virkeligheten. Det som ble
  rapportert er det som lagres; `value` er tekst og typingen skjer i
  analysen (`core/contract.py`).
- Å advare ville gitt utslag i 6 % av alle uker, og i 2025 omtrent
  annenhver. Verste uke har tre uteliggere, så det finnes ingen terskel
  som både fyrer på det unormale og tier på det normale. En advarsel som
  fyrer hele tiden er verre enn ingen.

Analysen skal filtrere på et intervall den velger selv. Dette avsnittet
er grunnlaget for å velge det.

Egen merknad om **eksakt 0,0**: 675 forekomster, konsentrert i 2012
(442) og 2013 (172), nesten borte etterpå. 0,0 er en lovlig målt verdi og
lagres som det — men mønsteret tyder på «ikke utfylt» ført som null i de
tidlige årene. Det er nøyaktig derfor `temperatur_er_rapportert` finnes
som eget felt: er verdien 0,0, sier flagget at noen faktisk skrev noe.

## 7. Sesong og breddegrad — kontrollen på at tallene er ekte

Median over alle år, per uke:

    uke  1   6,6      uke 19   7,3      uke 37  13,7
    uke  5   5,5      uke 23   9,6      uke 41  11,8
    uke  9   5,1      uke 27  12,0      uke 45   9,8
    uke 11   5,0  ←   uke 31  13,8      uke 49   7,9
    uke 15   5,7      uke 33  14,0  ←   uke 51   7,3

Minimum i uke 11 (mars), maksimum i uke 33–35 (august). Sjøen ligger to
måneder etter lufta, som den skal.

Breddegradsgradienten, median per 2-gradersbånd:

    °N        uke 5 (vinter)   uke 30 (sommer)
    58–60          6,3              15,3
    60–62          6,5              14,8
    62–64          6,4              13,5
    64–66          5,3              13,2
    66–68          4,9              12,9
    68–70          4,2              12,0
    70–72          4,1              10,2

Monotont fallende nordover i begge sesonger, og **sommergradienten er
brattere enn vintergradienten** (5,1 mot 2,2 grader over 12 breddegrader).
Det er riktig fysikk: Golfstrømmen holder vinteren jevn langs hele kysten,
mens soltilskuddet om sommeren er det som skiller sør fra nord.

## 8. Felter kilden emitter

    sjotemperatur              tallet, som tekst. Bare når det finnes.
    temperatur_er_rapportert   True/False, på HVER rad.

Ikke noe mer. CSV-en har 20 kolonner, men de 18 andre eies allerede:
`lusetall` eier lusetallene og driftsflaggene, `akvakultur` eier navn,
kommune, fylke, breddegrad og produksjonsområde
(`prodomraade_kode`/-`navn`/-`status`). To kilder som skriver samme felt
med hver sin skrivemåte legger igjen en permanent falsk forskjell i
dataene — samme grunn som at `lusetall` ikke emitter `navn`.

`temperatur_er_rapportert` er ikke pynt: 0,0 grader er en lovlig verdi
(se over), og uten flagget blir «ingen rapport» til 0 grader i enhver
analyse. Med `(T + 4,28)²` fra Stien mfl. 2005 er forskjellen mellom
«ukjent» og «0» et konkret, troverdig utseende tall på smittepresset.
Samme skille som `lus_er_rapportert` og `ansatte_er_registrert`.

## 9. Utvalget

    {"rapporttype": ["Lice"]}

`reporttype` er ikke bare et format: eksporten er delt i tre rapporter
(`Disease`, `Lice`, `Treatments`), og hvilken vi ber om avgjør HVILKE
lokaliteter som kommer med. Ber noen senere også om `Disease`, kommer det
inn lokaliteter som er nye i utvalget og ikke i verden — nøyaktig
hendelsen regel 1b-3 og `core/utvalg.py` finnes for.

`filetype` står ikke i utvalget: den endrer ikke hvilke entiteter vi får,
bare hvordan de er pakket. Se `utvalg.normaliser()` om hvorfor skalarer
som `sidestorrelse` heller ikke hører hjemme der.

## 10. Ratebegrensning

Ingen dokumentert grense, ingen `X-RateLimit-*`, ingen `Retry-After` —
samme bilde som resten av BarentsWatch.

Målt: ~0,8 s per ukekall. Et helt år i ett kall tar ~3,5 s og gir 6,6 MB.

Merk at et helt år FAKTISK kan hentes i ett kall
(`fromweek=1&toweek=53`), altså 15 kall for hele historikken i stedet for
730. Kilden gjør det likevel ukevis, fordi et snapshot er én uke: å hente
år og dele dem opp ville krevd en egen backfill-vei utenom den som
allerede er testet, og gjort gjenopptak grovkornet — et avbrudd midt i
2019 ville måttet hente hele 2019 på nytt.

Målt på den faktiske backfillen: **27 uker per minutt**, altså ~2,2 s per
uke med `--pause 0.4`. Kallet er 0,8 s av det; resten er diff, skriving
og changelog. 730 uker tar ~27 minutter, én gang.

### 401-blokkene 24.–25.08.2026 — forklart: maskinen sov (F13)

To backfiller stoppet på `401 Unauthorized`. Årsaken er den samme, og
den er fastslått — den har ingenting med ratebegrensning å gjøre.

`Tilgang.token()` cachet utløpstiden som
`time.monotonic() + expires_in - 60`. På macOS er `time.monotonic()`
`mach_absolute_time()` (bekreftet med `time.get_clock_info`), og den
står stille mens maskinen sover. Serverens klokke gjør ikke det.

Kjøringen 25.08 er målt linje for linje, og tidsstemplene avgjør det:

    09:16:43  uke 11/2022 skrevet          ~4 s per uke
    09:18:37  uke 12/2022 skrevet          114 s
    09:18:39  Entering Sleep ... Using Batt (94 %)
              ... Sleep/DarkWake på batteri i 38 minutter ...
    09:52:14  uke 13/2022: 401
    09:56:34  Wake ... due to lid / HID Activity
    09:57:16  uke 15/2022: 401  ->  STOPPET etter tre på rad

Søvnen begynte to sekunder etter at uke 12 ble skrevet. Regnestykket:
tokenet ble hentet 08:42:57, maskinen var våken til 09:18:39 (36 min),
sov 38 min, og våknet med et token som var 74 minutter gammelt i verden
mens vår klokke sa 36. TTL er 60. Koden fornyet aldri på 401, så hver
påfølgende uke fikk samme døde token.

Kjøringen 24.08 er den samme feilen over natta: 22:58 til 08:05, det
meste av det i søvn. Den tidligere antakelsen her — serverside-blokkering
etter ~30 kall/min — var **feil**, og den ble bare stående fordi loggen
manglet tidsstempler. Uke 239 var ikke en grense hos BarentsWatch; det
var tidspunktet maskinen sovnet.

Rettet 25.08.2026 på to steder, se `sources/_barentswatch.py` og
CLAUDE.md 1b-1:

  - alderen måles med veggklokka, som er den som handler om verden
  - `Tilgang.get()` re-autentiserer ÉN gang på 401 og prøver om igjen.
    Serveren er autoriteten på om tokenet duger; en klokke kan bare
    fange at vi regnet feil, aldri at en nøkkel er rullert eller en
    tilgang trukket.

### Om `pause_s = 2.0`

`Sjotemperatur.pause_s` er 2,0 mot lusetalls 0,5. Den ble satt 25.08 som
forsikring mot en ratebegrensning som viste seg ikke å finnes, og den
blir stående på egne meritter, ikke på den begrunnelsen:

Eksporten er 128 kB per ukekall mot lusetalls få kilobyte. ~20 kall/min
i stedet for ~30 tar hele historikken fra ~27 til ~48 minutter — 21
minutter, én gang, for en kilde vi skal bruke i to år mot et API uten
dokumentert grense. `docs/BARENTSWATCH-FUNN.md` §5 sier at fravær av en
dokumentert grense ikke er fravær av en grense, og det står ved lag selv
om det ikke var det som skjedde her.

Målt: 534 uker på 74 minutter med denne pausen, inkludert 38 minutter
søvn — altså ~36 minutter reell kjøretid for 534 uker.

## 11. Det som IKKE er bygget

Stien-formelen (`N_fisk × N_hunnlus × 0,17 × (T + 4,28)²`) er ikke
implementert. Antall fisk mangler fortsatt, og en formel med to av tre
ledd er ikke den formelen — den er lusetall med et navn som lover mer.
Konklusjonen fra forrige analyse står.
