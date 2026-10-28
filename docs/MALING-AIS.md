# Måling: Kystverkets åpne AIS-strøm (09)

Påbegynt 28.10.2026 på kystvakt-1 (Hetzner, Helsingfors, 89.167.57.216).
Skriptene ligger i `analyse/ais/`: `fang.py` fanger strømmen rått på
serveren, `tell.py` teller fangsten på Macen. Fangsten er en kropp i
`data/arkiv/` i datarepoet; tabellene under er utskriften fra `tell.py`,
uendret.

**Merkene:** MÅLT = talt i en arkivert kropp, sha256 oppgitt. MÅLBAR =
regnet ut av målte tall (framskrivinger per døgn og år). EKSTERN =
hviler på noe som ikke er i arkivet. UBELAGT = ingen kropp sier det.

**Spørsmålet:** svarer strømmen, dekoder den, og hvor mye er den — per
time, døgn og år, rå og komprimert? Har linjene kildens klokke (c:), og
hvor langt etter den kommer de fram hos oss?

## STOPPREGEL

*Skrevet 28.10.2026 ca. 04:58 UTC, FØR noen fangst er talt. 5631 hadde
da ikke svart på ett eneste forsøk siden 04:44 (se under).*

> **Målingen av 5631 stopper og rapporterer i stedet for å gå videre til
> arkivering (punkt 4) hvis ett av disse slår til:**
>
> 1. 5631 svarer ikke innen vaktløkka gir opp (240 forsøk, ett i
>    minuttet fra 04:52 UTC).
> 2. Under 95 % av de forventede meldingene dekoder (forventet =
>    énsetningsmeldinger + første fragment av flerdelte).
> 3. Under 95 % av linjene har en TAG-blokk med c:. Da finnes ikke
>    kildens klokke, og lagringsformatet med to klokker hviler på noe
>    strømmen ikke leverer.
> 4. Flere enn 3 brudd (eof eller feil) i løpet av timen.
>
> **Port 5632 arkiveres ikke i denne økta uansett utfall.** Den er ikke
> dokumentert av Kystverket, og hva den er, avgjør Heine.

Tersklene er mine, satt før tallene. 95 % er valgt fordi en strøm som
mister mer enn hver tjuende melding i dekoding ikke er «strømmen
dekoder». Tre brudd i timen er over 70 i døgnet.

## Hva som ble observert før fangsten

- **5631 svarte ikke.** Fra kystvakt-1: 9 forsøk 04:44–04:49 UTC,
  alle med tidsavbrudd (TCP SYN uten svar). Fra Macen (hjemmenett) ett
  forsøk 04:46, samme utfall. `tracepath` når 195.0.241.193 i hopp 17
  og får ikke svar etter det. Kystverkets side «Access to AIS data»
  oppgir fortsatt 153.44.253.27 port 5631, uten varsel om endring
  (lest 28.10.2026). EKSTERN: siden er ikke arkivert.
- **5632 på samme vert svarte**, og var den eneste av 5631, 5632, 80 og
  443 som gjorde det. Porten står ikke på Kystverkets side.

## Utfallet av stoppregelen

**Punkt 1 er ikke avgjort, men 5631 er ikke målt.** Da dette ble
skrevet, hadde 5631 ikke svart på ett eneste av 61 forsøk fra 04:52 til
05:52 UTC (`analyse/ais/proving-5631.log`, 61 linjer, alle `timeout`).
Løkka har 240 forsøk og går til ca. 08:52 UTC. Svarer 5631 før det,
fanges en time automatisk til `~/maling/strom-5631.txt` på serveren,
men den blir verken talt eller arkivert i denne økta.

Arkiveringen (punkt 4) er ikke startet. Vilkåret i oppdraget var at
målingen holder, og det finnes ingen måling av 5631 som kan holde.
Lytteren er bygget, prøvd og installert på kystvakt-1, men står som
`disabled`.

**Punkt 3 i oppdraget (strømmen mot nedlastingen) er ikke gjort.** Det
forutsatte at økt 2 hadde målt nedlastingen (MALING-AIS-HISTORIKK), og
det dokumentet finnes ikke. Uten 5631 var det uansett ingen strøm å
holde mot den.

**Notatet fra en annen AI (110–120 MB/døgn rå, 15–18 MB komprimert)
er fortsatt EKSTERN.** Det handler om 5631 og er ikke prøvd.

Det som FINNES, er en time av 5632, målt ved siden av. Den svarer ikke
på oppdragets spørsmål, men den svarer på hva 5632 er, og det trengs
for å bestemme hva som skjer videre.

## Kroppen

| kilde | fil i `data/arkiv/` | sha256 (utpakket) |
|---|---|---|
| ais-5632 | `ais-5632/2026-10-28.bin.gz` | `e12f03003bb9d5eeebbecf57454ee1493198f0e7d621057b06855166ad42036f` |

Fanget av `analyse/ais/fang.py` på kystvakt-1, 04:52:03–05:52:04 UTC
28.10.2026. Hver linje er `<vår mottakstid>\t<linja fra kilden>`.
Tilkoblingsloggen er `analyse/ais/hendelser-5632.jsonl` (vår egen, ikke
en kropp).

## Utskriften

    .venv/bin/python -m analyse.ais.tell \
        ../havbruk-radar-data/data/arkiv/ais-5632/2026-10-28.bin.gz \
        analyse/ais/hendelser-5632.jsonl

```
kropp sha256 (fil slik fang.py skrev den)  e12f03003bb9d5eeebbecf57454ee1493198f0e7d621057b06855166ad42036f
varighet                               3600 s
linjer                                10650
bytes fra kilden                     783019
bytes i fangstfila (med vår tid)    1081219

setninger med gyldig sjekksum         10650  100.00%
setninger med feil sjekksum               0    0.00%
linjer pyais ikke parser                  0    0.00%
meldinger forventet (1-delte + første fragment) 10595
meldinger satt sammen                 10595  100.00%
meldinger dekodet                     10595  100.00%
unike MMSI                             1287
meldingstyper (topp 8)           1:5102, 27:3139, 3:1486, 4:619, 18:131, 5:55, 24:39, 21:24

linjer med TAG-blokk                  10650  100.00%
linjer med c:                         10595   99.48%
unike s: (stasjoner)                      4
s: med flest linjer              NorSat_3:5545, NorSat_2:3966, AISSat_4:1131, NorSat_1:8
forsinkelse mottatt − c: (s)     min 0.6  median 6184.5  p90 29774.4  p99 29980.0  maks 30159.2
linjer med c: etter mottakstid            0

brudd: kilden lukket (eof)                0
brudd: vårt tidsavbrudd, stille          12
brudd: annen feil                         0
mislykte tilkoblinger                     0
hull > 60 s mellom linjer                13
lengste hull mellom linjer              666 s
linjer uten c:                           55  (av dem fragment nr > 1: 55)

volum                    per time       per døgn         per år
kilden rå                   0.78 MB        18.8 MB        6.86 GB
kilden gzip -9              0.21 MB         5.1 MB        1.87 GB
fangstfil rå                1.08 MB        25.9 MB        9.47 GB
fangstfil gzip -9           0.23 MB         5.5 MB        2.00 GB
fangstfil zstd -3           0.22 MB         5.4 MB        1.96 GB
fangstfil zstd -19          0.18 MB         4.4 MB        1.61 GB
```

## De tre sterkeste funnene

**1. 5632 er satellitt-AIS levert i etterkant, med opptil 8,4 timers
etterslep (F1.4).** Median avstand mellom kildens c: og vår mottakstid
er 6184 s (1,7 t), p90 8,3 t, maks 8,4 t. Ingen linje har c: etter
mottakstiden.
*Hvorfor sterkest:* tallet er talt i 10 595 linjer, og det endrer hva
en arkivfil «per time» betyr: timen vi MOTTOK, ikke timen skipet sendte.
Det er 1b-7 i praksis: med bare én av klokkene ville arkivet løyet om
når skipene var der.

**2. 5632 dekoder fullt ut, og hver linje har TAG-blokk (F1.2, F1.3).**
100 % av setningene har gyldig sjekksum, og 100 % av de forventede
meldingene dekoder med pyais 3.3.1. c: mangler på 55 linjer, og alle 55
er fragment 2 av 2: kilden setter c: på første fragment.
*Hvorfor sterk:* null avvik, talt i hele kroppen.

**3. 5631 svarte ikke i løpet av timen (F1.1).** Ett forsøk i minuttet,
ingen svar, fra to nett. Utfallet er sikkert. Hvorfor 5631 ikke svarer,
vet vi ikke.

Svakere: volumet (F1.6) er én time natt til onsdag av en kilde som
leverer i støt. Det kan ikke framskrives trygt, og det handler ikke om
5631.

## Funnene

**F1.1 — 5631 svarte ikke, 04:44–05:52 UTC.** MÅLBAR: lest i vår egen
prøvelogg (`analyse/ais/proving-5631.log`), ikke i en kropp fra kilden.
71 forsøk i alt (9 manuelle fra serveren, 1 fra Macen, 61 i løkka),
alle tidsavbrudd.
*Feil hvis:* forsøkene gikk mot feil adresse. De gikk mot 153.44.253.27,
samme vert som svarte på 5632 i samme minutt.

**F1.2 — 5632 dekoder: 10 595 av 10 595 meldinger.** MÅLT, `ais-5632`.
10 650 linjer, alle med gyldig sjekksum og alle parset av pyais. Alle
flerdelte meldinger ble satt sammen.
*Feil hvis:* pyais godtar setninger med feil sjekksum. Det gjør den
(`is_valid` er en egenskap, ikke en sperre); derfor er sjekksummen talt
for seg.

**F1.3 — TAG-blokk på 100 % av linjene, c: på 99,48 %.** MÅLT, `ais-5632`.
De 55 uten c: er alle fragment 2. Kildens klokke har sekundoppløsning
(10 siffer).
*Feil hvis:* c: står andre steder enn i TAG-blokka. `tell.py` leser
bare blokka mellom de to første `\`.

**F1.4 — Etterslep: median 1,7 t, maks 8,4 t.** MÅLT, `ais-5632`. Minste
avstand 0,6 s. Vår mottakstid er veggklokka på kystvakt-1, synkronisert
med chrony (0,0000002 s fra NTP ved oppsett).
*Feil hvis:* c: er en annen klokke enn mottakstidspunktet i satellitten
eller på bakken. Hva c: betyr hos Kystverket, er ikke dokumentert for
5632. Tallet er avstanden mellom de to stemplene, ikke en påstand om
hvor tiden gikk.

**F1.5 — Fire s:-stasjoner, alle med satellittnavn.** MÅLT for navnene,
`ais-5632`: NorSat_3 5545 linjer, NorSat_2 3966, AISSat_4 1131,
NorSat_1 8. At de er satellitter, er EKSTERN (navnene er norske
AIS-satellitter, men ingen kropp her sier det). 1287 unike MMSI, alle
meldingstyper med.
*Feil hvis:* en stasjon uten s: finnes. Alle 10 650 linjer har TAG-blokk,
og tellingen er over s: i blokka.

**F1.6 — Volum 5632: 0,78 MB kildebytes i timen.** MÅLT for timen,
`ais-5632`. Framskrevet (MÅLBAR, lineært): 18,8 MB/døgn rå og 5,1 MB
gzip -9. Arkivformatet med vår tid foran: 25,9 MB/døgn rå, 5,4 MB
zstd -3, 1,96 GB/år.
*Feil hvis:* timen er typisk. Den er ikke vist å være det: strømmen kom
i støt med 13 hull over 60 s, det lengste 666 s.

**F1.7 — Ingen brudd fra kilden.** MÅLT, `ais-5632` + hendelsesloggen.
0 eof og 0 mislykte tilkoblinger. De 12 bruddene i loggen er VÅRT
tidsavbrudd i `fang.py` (120 s uten data), ikke kildens.
*Feil hvis:* kilden lukker stille uten FIN. Da ville neste tilkobling
feilet eller gitt et hopp i c:. Ingen tilkobling feilet.

## Hva dette betyr for lytteren, uten å avgjøre noe

- Lagringsformatet (vår tid + linja uendret) holder for 5632: c: står i
  linja, og avstanden til vår tid er timer, ikke sekunder.
- Vakten (WatchdogSec=300) ville startet lytteren på nytt under 5632s
  stille strekk (opptil 666 s). Det mister ikke data (prøvd), men gir
  `.N`-filer i samme time.
- Tallene for 5631 finnes ikke. Hvilken port som skal arkiveres, og om
  lytteren skal stå klar mot 5631 til den svarer, avgjør Heine.

## Etterskrift 28.10.2026: kontrolløren

Teksten over er ikke endret. Kontrolløren trakk tre påstander (frø
1381581499): to TREFF og ett avvik.

- **F1.7 skal ha merket MÅLBAR, ikke det merket som står.** «0 eof» og
  «ingen brudd fra kilden» er talt i `analyse/ais/hendelser-5632.jsonl`,
  vår egen logg, som ikke ligger i arkivet og ikke har noen sha256.
  Kroppen kan bare vise hullene (13 over 60 s, lengste 666 s), og de
  stemmer. At ingen av dem var at kilden lukket, står bare i loggen.
- **MB betyr 10⁶ byte**, og «kildebytes» er linjene slik kilden sendte
  dem, med `\r\n` (alle 10 650 linjer ender slik). Kontrolløren måtte
  anta begge deler for å få 0,78 i F1.6.

Bare én kjøring av kontrolløren, bestemt på forhånd.

## Tillegg 28.10.2026: BarentsWatch Live AIS

Teksten over er ikke endret. Dette tillegget måler den samme åpne
AIS-dataen slik BarentsWatch leverer den (oppdraget «AIS via
BarentsWatch», punkt 1). Skriptene er `analyse/ais/fang_bw.py`
(strømmen), `fang.py` (5632 i samme time) og tellerne som navngis
under.

### Hva som ble observert før fangsten

- **Tokenet.** Lusetallklienten får `400 invalid_scope` for `scope=ais`
  (14:2x UTC). AIS krever en EGEN klient under «AIS API» på Min side
  (developer.barentswatch.no/docs/tutorial, lest 28.10.2026, EKSTERN).
  Den nye klienten ga `invalid_client` til secreten ble satt på nytt;
  fra 14:43 gir den `200`, `scope ais`, `aud ais`, `expires_in 3600`.
  Nøklene ligger bare på kystvakt-1, lesbare bare for `ais`.
- **OpenAPI** (`live.ais.barentswatch.no/live/openapi/ais/openapi.json`,
  sha256 `2a33f30f04b7cbc43cb42cafccec09580085bdce4b3dbfcc810cf17e1993a7f6`,
  og historikk-API-ets `historic.ais.barentswatch.no/open/openapi/ais/openapi.json`,
  sha256 `29e875f8733d2a821949917e70f172f0be8eb3726b3eb0c257a93c763abc6f1e`)
  sier — EKSTERN til de er arkivert:
  - `GET /v1/ais` er en strøm, «JSON streaming», én melding per linje
    så lenge vi er koblet til. `/v1/sse/ais` er det samme som SSE.
    POST-variantene filtrerer og kan nedsample (maks én melding per
    minutt per MMSI). Vi bruker GET: ingen filter, ingen nedsampling.
  - Meldingene er DEKODET JSON, ikke NMEA. Typene: 1, 2, 3, 9, 18, 19,
    27 som `Position`; 5 og 24 som `StaticData` (navn, kallesignal,
    `shipType`, `shipLength`, `shipWidth`, dimensjon A–D, `draught`);
    8 som `BinaryBroadcastMessageMetHyd`; 21 som `Aton`. Hver melding har
    `msgtime` (date-time) og `stream`. Hva `msgtime` er — kildens
    mottak, Kystverkets eller BarentsWatchs — står ikke.
  - Begrensninger (developer.barentswatch.no/docs/AIS/live-ais-api):
    norsk økonomisk sone, fiskevernsonen ved Svalbard og vernesonen
    ved Jan Mayen; ingen fiskefartøy under 15 m; ingen fritids- eller
    seilfartøy under 45 m; ingen data eldre enn 14 dager. Lisensen i
    OpenAPI-dokumentet er NLOD. Vilkårssiden utviklerdokumentasjonen
    viser til (`barentswatch.no/om/api-vilkar`) gir 404.
  - Historikk-API-et har spor PER FARTØY
    (`/v1/historic/tracks/{mmsi}/{fra}/{til}`, `filterSatellitePositions`
    er sann som standard) og en liste over MMSI i et område
    (`POST /v1/historic/mmsiinarea`, høyst 7 dager). Et helt område kan
    ikke hentes i ett kall.
- **Kystverkets nedlasting** (`ais-public.kystverket.no/ais-download/`)
  svarte ikke 14:35 UTC, fra Macen eller fra kystvakt-1: TCP opp, TLS
  nullstilt i håndtrykket. Over http svarer Azure med «Azure Container
  App - Unavailable» (404). 1e kan ikke måles.

### STOPPREGEL (BarentsWatch)

*Skrevet 28.10.2026 ca. 14:50 UTC, FØR strømmen er åpnet.*

> **Lytteren mot BarentsWatch bygges ikke (punkt 2 og utover) hvis ett
> av disse slår til i timen som fanges:**
>
> 1. Under 95 % av linjene er JSON med `mmsi` og en `msgtime` som kan
>    leses som et tidspunkt.
> 2. `msgtime` er ikke kildens klokke. Prøven: posisjonsmeldinger som
>    finnes i BÅDE BarentsWatch-strømmen og 5632 i samme time, matchet
>    på MMSI og posisjon. Er medianavstanden mellom `msgtime` og 5632s
>    `c:` over 60 s, er `msgtime` et senere stempel enn kildens, og
>    oppdraget sier stopp («API-et gir ikke posisjoner med kildens
>    tidsstempel»).
> 3. Strømmen leverer under 10 meldinger i minuttet over timen.
>
> Brudd stopper ikke målingen. De telles, og lytteren må tåle dem.

60 s er valgt fordi 5632s c: har sekundoppløsning og stasjonene på
bakken stempler innen sekunder; et senere stempel i en mellomledd
ville vist seg som minutter eller timer (F1.4: median 1,7 t for
satellitt). Er det for få matchede posisjoner til en median (under
30), er punkt 2 ikke avgjort, og det sies.
