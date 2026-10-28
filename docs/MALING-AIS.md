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

### Kroppene

| kilde | fil i `data/arkiv/` | sha256 (utpakket) |
|---|---|---|
| ais-bw | `ais-bw/2026-10-28.bin.gz` | `de3498c4aa4cf8015bc9bfbb4011d00664c455699efd4b883f300f7791f48881` |
| ais-5632 | `ais-5632/2026-10-28.2.bin.gz` | `b5ca60f16754af354cbd84380498b62459a0632c9bb486b7923220ee8dfe18e7` |
| ais-bw-openapi | `ais-bw-openapi/2026-10-28.bin.gz` | `2a33f30f04b7cbc43cb42cafccec09580085bdce4b3dbfcc810cf17e1993a7f6` |
| ais-bw-hist-openapi | `ais-bw-hist-openapi/2026-10-28.bin.gz` | `29e875f8733d2a821949917e70f172f0be8eb3726b3eb0c257a93c763abc6f1e` |

De to strømmene ble fanget samtidig på kystvakt-1, 14:44:47–15:44:47
UTC 28.10.2026: `fang_bw.py` mot `GET /v1/ais` som brukeren `ais`,
`fang.py` mot 5632 som `vakt`. Begge med vår mottakstid foran linja.
Hendelsesloggene er `analyse/ais/hendelser-bw.jsonl` og
`analyse/ais/hendelser-5632-b.jsonl` (våre egne, ikke kropper). chrony
før og etter: 0,00013 s og 0,00026 s fra NTP, stratum 3.

OpenAPI-dokumentene er de samme bytene som ble lest før stoppregelen;
hashene over er de samme som der.

### Utskriften

    .venv/bin/python -m analyse.ais.tell_bw \
        ../havbruk-radar-data/data/arkiv/ais-bw/2026-10-28.bin.gz \
        analyse/ais/hendelser-bw.jsonl \
        ../havbruk-radar-data/data/arkiv/ais-5632/2026-10-28.2.bin.gz

```
kropp sha256 (fil slik fang_bw.py skrev den)  de3498c4aa4cf8015bc9bfbb4011d00664c455699efd4b883f300f7791f48881
varighet                               3601 s
linjer                               170893
meldinger per minutt                   2848
bytes fra kilden                   52027390
bytes i fangstfila (med vår tid)   56812394

linjer som ikke er JSON                   0    0.00%
JSON uten mmsi eller msgtime              0    0.00%
med mmsi og lesbar msgtime           170893  100.00%
type                             Position:132548, Staticdata:34314, Aton:3770, BinaryBroadcastMessageMetHyd:260, SafetyRelated:1
messageType                      1:91825, 3:27208, 5:24875, 18:12650, 24:9439, 21:3770, 27:738, 8:260, 9:127, 12:1
stream                           terra:164406, offshore:5502, satellite:985
unike MMSI                             4147
unike MMSI med StaticData              3789

forsinkelse mottatt − msgtime (s) min -59.2  median 1.6  p90 2.2  p99 2.8  maks 6727.2
msgtime etter mottakstid                 40
  stream=offshore   median      0.3  p99      1.0  maks      1.5
  stream=satellite  median      2.0  p99   6722.2  maks   6727.2
  stream=terra      median      1.6  p99      2.7  maks     12.7

tilkoblinger                              1
brudd: kilden lukket (eof)                0
brudd: annen feil                         0
mislykte tilkoblinger                     0
hull > 10 s mellom linjer                 1
lengste hull mellom linjer             12.6 s

5632 kropp sha256                b5ca60f16754af354cbd84380498b62459a0632c9bb486b7923220ee8dfe18e7
unike MMSI 5632                         288
felles MMSI                             225
bare i BarentsWatch                    3922
bare i 5632                              63

posisjoner i fart, BW                 38937
posisjoner i fart, 5632                 512
samme posisjon i begge                   50
msgtime − 5632 c: (s)            min 0.0  median 0.0  p90 0.0  maks 0.0
|msgtime − c:| > 60 s                     0

volum                    per time       per døgn         per år
kilden rå                  52.02 MB      1248.4 MB      455.68 GB
fangstfil rå               56.80 MB      1363.3 MB      497.59 GB
fangstfil gzip -9           5.95 MB       142.8 MB       52.13 GB
fangstfil zstd -3           6.23 MB       149.5 MB       54.57 GB
fangstfil zstd -19          2.96 MB        70.9 MB       25.90 GB
```

### Utfallet av stoppregelen (BarentsWatch)

**Ingen av de tre slo til.** 170 893 av 170 893 linjer har `mmsi` og
lesbar `msgtime` (punkt 1). 50 posisjoner i fart finnes i begge
strømmene, og `msgtime` er lik 5632s c: på sekundet for alle 50 (punkt
2: median 0,0 s, maks 0,0 s). 2848 meldinger i minuttet (punkt 3).
Lytteren ble derfor bygget (punkt 2–5 i oppdraget).

### Funnene (BarentsWatch)

**F2.1 — `msgtime` er kildens klokke.** MÅLT, `ais-bw` + `ais-5632`
(`.2`). 50 posisjonsrapporter fra fartøy i fart (over 1 knop, type 1,
2, 3, 18, 19) har samme MMSI og samme posisjon (fire desimaler) i begge
kroppene, og for alle 50 er `msgtime` − c: = 0 s.
*Feil hvis:* to ulike sendinger fra samme fartøy kan ha samme posisjon
til fire desimaler mens det er i fart. Fire desimaler er 11 m; over
1 knop flytter fartøyet seg 11 m på 21 s.

**F2.2 — Strømmen leverer, hel og fortløpende.** MÅLT, `ais-bw`.
170 893 meldinger på 3601 s, alle JSON, én tilkobling hele timen, null
brudd, lengste hull mellom linjer 12,6 s. 4147 unike MMSI, 3789 av dem
med Staticdata (type 5 og 24: navn, kallesignal, skipstype, mål).
*Feil hvis:* timen er typisk. Den var en onsdag ettermiddag; natt og
helg er ikke målt. At ingen brudd kom fra kilden, står i vår egen
hendelseslogg og er MÅLBAR, ikke MÅLT (kontrollørens rettelse til F1.7).

**F2.3 — Forsinkelse: median 1,6 s, p99 2,8 s for land.** MÅLT,
`ais-bw`. Per `stream`: `terra` median 1,6 s, maks 12,7 s; `offshore`
median 0,3 s; `satellite` median 2,0 s, maks 6727 s (1,9 t). 40
meldinger har `msgtime` inntil 59,2 s ETTER vår mottakstid, 38 av dem
fra `terra`.
*Feil hvis:* vår klokke gikk feil. chrony var innenfor 0,3 ms av NTP
før og etter timen. 59 s fram i tid er da en klokke hos kilden eller en
stasjon, ikke hos oss — hvilken, sier ikke dataene.

**F2.4 — Strømmen er dekodet, og det koster noe.** MÅLT, `ais-bw`.
Meldingstypene er 1, 3, 5, 8, 9, 12, 18, 21, 24 og 27. Type 4
(basestasjoner) finnes ikke, og NMEA-linjene finnes ikke: det vi
lagrer, er BarentsWatchs tolkning, ikke det fartøyet sendte. Typen
står som `Staticdata` (ikke `StaticData` som i OpenAPI-dokumentet) og
`SafetyRelated`, som ikke står i beskrivelsen.
*Feil hvis:* GET har et format med rå NMEA. Det har ikke OpenAPI-
dokumentet (EKSTERN til det ble arkivert; nå `ais-bw-openapi`).

**F2.5 — BarentsWatch og 5632 i samme time: 225 felles MMSI.** MÅLT,
`ais-bw` + `ais-5632` (`.2`). 4147 MMSI i BarentsWatch, 288 i 5632, 225
i begge. 3922 bare i BarentsWatch. 63 bare i 5632: 18 basestasjoner
(type 4 / MMSI 00…), 13 med bare type 27, 19 norske (MID 257), resten
spredt.
*Feil hvis:* 5632 var representativ den timen. Det var den ikke:
1029 linjer mot 10 650 om morgenen, og 5632 lukket 325 tilkoblinger fra
kilden (eof) mot 0 om morgenen (vår logg, MÅLBAR). At de 19 norske er
fiskefartøy under 15 m eller fritidsbåter BarentsWatch filtrerer bort,
er UBELAGT.

**F2.6 — 5632 lukker de fleste tilkoblinger uten data.** MÅLBAR, vår
hendelseslogg. 336 tilkoblinger, 333 lukket av kilden uten data etter
median 9 s; de tre som ga data, varte 159–195 s. Om morgenen samme dag:
0 eof på en time.
*Feil hvis:* lukkingen skyldes noe hos oss. Ingen annen prosess hos oss
var koblet til 5632 i timen.

**F2.7 — Volum: 52 MB i timen fra kilden, 71 MB i døgnet arkivert.**
MÅLT for timen, `ais-bw`; døgn og år er MÅLBAR (lineært). Fangstfila
med vår tid: 56,8 MB rå, 6,2 MB zstd -3, 3,0 MB zstd -19. Slik lytteren
skriver (blokk hvert 10. s, målt på kystvakt-1): nivå 3 gir 152 MB/døgn,
nivå 19 gir 71 MB/døgn for 27 s CPU per time og 89 MB minne. Dette er
den nedsamplede GET-strømmen; det lytteren lagrer, er nesten fem ganger
så stort (F2.8).
*Feil hvis:* ettermiddagen er typisk. Natt er ikke målt.

**F2.8 — GET /v1/ais er nedsamplet; POST med `downsample: false` er
det ikke.** MÅLT, `ais-bw-get-5min` + `ais-bw-full-5min`. Fanget
samtidig 17:16:54–17:21:54 UTC: GET 14 943 meldinger, POST 71 004.
Høyst 5 posisjoner per MMSI på fem minutter i GET, 302 i POST. Alle
14 943 GET-linjer finnes byte for byte i POST, og begge har de samme
3439 fartøyene med posisjon. GET er altså en delmengde, og ingenting i
OpenAPI-dokumentet sier det (det sier at nedsampling er noe man slår PÅ
i POST). Timen i F2.1–F2.7 er GET, og tallene der gjelder den
nedsamplede strømmen; stoppregelen holder for begge, fordi linjene er
de samme.
*Feil hvis:* forskjellen er tilfeldig for de fem minuttene. Et prøvekall
på to minutter 17:13 UTC (ikke arkivert, MÅLBAR) ga samme forhold:
GET 6248, `downsample: true` 6246, `downsample: false` 28 525.

    .venv/bin/python -m analyse.ais.tell_get_post \
        ../havbruk-radar-data/data/arkiv/ais-bw-get-5min/2026-10-28.bin.gz \
        ../havbruk-radar-data/data/arkiv/ais-bw-full-5min/2026-10-28.bin.gz

```
== GET  sha256 f12d109527c3b91443ebe918336649beafbc3f4a1b000032104e3f9ddd13c090
   meldinger    14943  på 299 s  =    2997 per minutt
   type      Position:11729, Staticdata:2875, Aton:316, BinaryBroadcastMessageMetHyd:23
   MMSI med posisjon   3439  posisjoner per MMSI median 4  maks 5
   bytes fra kilden    4535332  =    54.6 MB/time  zstd -19    97.4 MB/døgn (hel ramme)
== POST full  sha256 b708ebcc7a45b08da8348c33950f96d983ff92f439dc8accb8cd50dab7995c1b
   meldinger    71004  på 300 s  =   14224 per minutt
   type      Position:66595, Staticdata:3616, Aton:646, BinaryBroadcastMessageMetHyd:147
   MMSI med posisjon   3439  posisjoner per MMSI median 16  maks 302
   bytes fra kilden   20633888  =   248.0 MB/time  zstd -19   344.7 MB/døgn (hel ramme)
== GET mot POST full
   GET-linjer som finnes byte for byte i POST      14943 av 14943
   GET-meldinger med samme mmsi/msgtime/type i POST    14943 av 14943
   MMSI med posisjon bare i GET                        0
   MMSI med posisjon bare i POST                       0
```

Lytteren bruker POST uten nedsampling fra 17:33:37 UTC. Volumet blir
248 MB i timen fra kilden; slik lytteren skriver (zstd -19, blokk hvert
10. s, målt på kystvakt-1) 345 MB i døgnet for 139 s CPU per time.
Framskrevet lineært fra fem minutter en ettermiddag (MÅLBAR): 15 GB
ledig disk holder i rundt 43 dager.

### Historikk-API-et (1d)

| kilde | fil i `data/arkiv/` | sha256 (utpakket) |
|---|---|---|
| ais-bw-hist | `ais-bw-hist/2026-10-28.bin.gz` | `f2062fd52dfadd3c36c435ba6243d85cf18cd6bb6b6d6e7dc39e0f2faae06d49` |

Hentet av `analyse/ais/hist_bw.py` på kystvakt-1 som `ais`, 16:26–17:09
UTC: `openaisarea`, så `mmsiinarea` med rektangelet rundt det åpne
området for timen i F2.1–F2.7, så `tracks/{mmsi}/{fra}/{til}` for hver
MMSI med `filterSatellitePositions=false`. Ett kall om gangen, 0,5 s
pause. Ett kall (MMSI 257079080) ble brutt av vår egen bruddprøve
(`ss -K` mot samme adresse, 16:39:14) og står med status null.

    .venv/bin/python -m analyse.ais.tell_hist \
        ../havbruk-radar-data/data/arkiv/ais-bw-hist/2026-10-28.bin.gz \
        ../havbruk-radar-data/data/arkiv/ais-bw/2026-10-28.bin.gz \
        2026-10-28T14:44:47Z 2026-10-28T15:44:47Z

```
historikk sha256                 f2062fd52dfadd3c36c435ba6243d85cf18cd6bb6b6d6e7dc39e0f2faae06d49
strøm sha256                     de3498c4aa4cf8015bc9bfbb4011d00664c455699efd4b883f300f7791f48881
vindu                            2026-10-28T14:44:47Z – 2026-10-28T15:44:47Z
mmsiinarea: MMSI                       3814
mmsiinarea: sekunder                   2.80
sporkall                               3814  status {200: 3813, None: 1}
sporkall: s median / p99 / maks  0.158 / 0.250 / 0.360
sporkall: sum kalltid                   624 s
veggtid hele hentingen                 2536 s  (med pause mellom kall)
bytes i svarene                    34556954
posisjoner i historikken             134369  i vinduet 134135
  stream                         terra:128198, offshore:3725, satellite:3321
MMSI med posisjoner                    3813

posisjoner i strømmen i vinduet      132289  MMSI 3812
  av dem i historikken                86923   65.71%
  stream=offshore                   2138 av     3359   63.65%
  stream=satellite                   737 av      737  100.00%
  stream=terra                     84048 av   128193   65.56%
  for MMSI med spor: i historikken    86923 av   132247   65.73%
  manglende: s til nærmeste i historikken  median 20  p90 31
MMSI i strømmen, ikke i listen            0
MMSI i strømmen uten spor                 1
```

Samme henting for et døgn, 2026-10-27T15:44:47Z–2026-10-28T15:44:47Z,
17:12–18:14 UTC. Kroppen er 935 MB og ligger bare på kystvakt-1
(`/srv/ais/maling/hist-dogn.jsonl`); den er for stor til datarepoet, så
tallene under er MÅLBAR, ikke MÅLT. Talt på serveren:

    python3 analyse/ais/tell_hist_dogn.py hist-dogn.jsonl strom-bw.txt \
        2026-10-28T14:44:47Z 2026-10-28T15:44:47Z hist-time.jsonl

```
historikk sha256 (fila på serveren)  731c54944eac0c2b7e516ae70c40f3a5f23137bdad5786b7be0e2039e7651325
mmsiinarea: MMSI                       4409
mmsiinarea: sekunder                  17.55
sporkall                               4409  status {200: 4409}
sporkall: s median / p99 / maks  0.345 / 0.610 / 1.497
sporkall: sum kalltid                  1514 s
veggtid hele hentingen                 3742 s
bytes i svarene                   835510173
posisjoner                          3302488
  stream                         terra:3000234, satellite:223978, offshore:78276
MMSI med posisjoner                    4409
tidligste / seneste msgtime      2026-10-27T15:44:40 / 2026-10-28T15:44:40

timen 2026-10-28T14:44:47Z – 2026-10-28T15:44:47Z
  posisjoner i døgnhentingen         134537
  posisjoner i strømmen (GET)        132289
  felles                              86965
  posisjoner i timehentingen         134135
  felles døgn og time                134135
```

Og fem minutter mot den FULLE strømmen (17:16:54–17:21:54, de første
300 MMSI i `mmsiinarea`-lista):

| kilde | fil i `data/arkiv/` | sha256 (utpakket) |
|---|---|---|
| ais-bw-hist-5min | `ais-bw-hist-5min/2026-10-28.bin.gz` | `b3c906a4a5406503c165ee01a73e31c233e14b6b9e088ab573f9650a5cb679d2` |

    .venv/bin/python -m analyse.ais.tell_hist \
        ../havbruk-radar-data/data/arkiv/ais-bw-hist-5min/2026-10-28.bin.gz \
        ../havbruk-radar-data/data/arkiv/ais-bw-full-5min/2026-10-28.bin.gz \
        2026-10-28T17:16:54Z 2026-10-28T17:21:54Z

```
historikk sha256                 b3c906a4a5406503c165ee01a73e31c233e14b6b9e088ab573f9650a5cb679d2
strøm sha256                     b708ebcc7a45b08da8348c33950f96d983ff92f439dc8accb8cd50dab7995c1b
vindu                            2026-10-28T17:16:54Z – 2026-10-28T17:21:54Z
mmsiinarea: MMSI                       3439
mmsiinarea: sekunder                   0.51
sporkall                                300  status {200: 300}
sporkall: s median / p99 / maks  0.159 / 0.243 / 0.289
sporkall: sum kalltid                    49 s
veggtid hele hentingen                  199 s  (med pause mellom kall)
bytes i svarene                      605468
posisjoner i historikken                927  i vinduet 922
  stream                         terra:921, offshore:6
MMSI med posisjoner                     300

posisjoner i strømmen i vinduet       66017  MMSI 3439
  av dem i historikken                  922    1.40%
  stream=offshore                      6 av     2163    0.28%
  stream=terra                       916 av    63854    1.43%
  for MMSI med spor: i historikken      922 av     5648   16.32%
  manglende: s til nærmeste i historikken  median 20  p90 31
historikkens posisjoner i vinduet som finnes i strømmen  922 av 922
MMSI i strømmen, ikke i listen            2
MMSI i strømmen uten spor              3139
```

**F2.9 — Historikken kan hentes for et helt område, men bare fartøy for
fartøy.** MÅLT for timen (`ais-bw-hist`), MÅLBAR for døgnet. Én
`mmsiinarea` gir lista (3814 MMSI for timen på 2,8 s; 4409 for døgnet
på 17,6 s), deretter ett `tracks`-kall per MMSI. Timen: 3814 kall, 0,158 s
i median, 42 min med pausen. Døgnet: 4409 kall, 0,345 s i median, 62 min
med pausen, 835 MB svar. Et døgn koster altså omtrent like mange kall
som en time, fordi kostnaden følger fartøyene, ikke klokka.
*Feil hvis:* `mmsiinarea` mangler fartøy. For timen manglet ingen av de
3812 med posisjon i strømmen; for de fem minuttene manglet 2 av 3439.

**F2.10 — Døgnet dekker timen.** MÅLBAR. Alle 134 135 posisjoner fra
timehentingen finnes i døgnhentingen, som har 134 537 i samme time.
*Feil hvis:* de to hentingene ser samme feil. De er gjort med 25
minutters mellomrom mot samme API; noe uavhengig er det ikke.

**F2.11 — Historikken er en nedsamplet delmengde av den fulle strømmen,
og en ANNEN nedsampling enn GET.** MÅLT, `ais-bw-hist-5min` +
`ais-bw-full-5min`: alle 922 historikkposisjoner i de fem minuttene
finnes i den fulle strømmen, men de er 16 % av strømmens posisjoner for
de samme 300 fartøyene. Mot GET-timen (`ais-bw-hist` + `ais-bw`): nesten
like mange posisjoner (134 135 mot 132 289), men bare 86 923 felles;
de som mangler, ligger median 20 s fra nærmeste i historikken. Begge
plukker omtrent én posisjon i minuttet per fartøy, på ulike sekunder.
*Feil hvis:* den fulle strømmen er alt Kystverket har. Det vet vi ikke;
at POST uten nedsampling er hele datasettet, er UBELAGT.

### Hulljegeren: bygget, med et forbehold

Oppdraget sa: er historikk-API-et bare per fartøy og for tregt, bygg
den ikke. Det er bare per fartøy, men ikke for tregt: et døgnhull koster
rundt en time (F2.9), og et hull på en time koster 42 minutter. Hver
natt i seks timer rekker rundt seks døgn. Hulljegeren er bygget
(`kystvakt/hulljeger.py`).

Forbeholdet er F2.11: det hulljegeren henter, er ikke det lytteren ville
lagret. Det er omtrent én posisjon i minuttet per fartøy, uten
Staticdata, Aton og MetHyd, og det ligger i egne filer merket
`etterhentet`. Det lapper et hull i SPORET; det gjenskaper ikke timen.

Timene før lytteren startet (fra 14.10 til 28.10 kl. 16) er tomme i
regnskapet, og hulljegeren henter dem fra natt til 29.10, eldste først,
fordi de er de første som forsvinner fra API-et. Det er rundt 14 døgn
og tre netter.

### De tre sterkeste funnene (BarentsWatch)

**1. GET /v1/ais er nedsamplet; POST med `downsample: false` gir nesten
fem ganger så mye (F2.8).** *Hvorfor sterkest:* det endret hva
lytteren lagrer. Uten målingen ville arkivet hatt én posisjon i
minuttet per fartøy og sett ut som hele strømmen. Talt i to kropper
fanget samtidig, og GET er en ren delmengde byte for byte.

**2. `msgtime` er kildens klokke (F2.1).** 50 av 50 felles posisjoner
har `msgtime` lik 5632s c: på sekundet. Det er det som gjør at to
klokker i arkivet (vår mottakstid og `msgtime`) betyr to eiere, ikke to
stempler fra samme sted (1b-7). *Svakere enn 1:* 50 er få, og bare
satellittpar kunne matches den timen.

**3. Historikken kan lappe hull, men ikke gjenskape dem (F2.9–F2.11).**
Et døgn koster en time med kall, så hulljegeren er mulig; men det den
henter, er en tredje, tynnere utgave av dataene.

Svakere: volum og disk (F2.7, F2.8) er framskrevet fra fem minutter en
ettermiddag, og 5632-sammenligningen (F2.5) er gjort i en time da 5632
nesten ikke leverte.

### Kontrolløren

Én kjøring, bestemt på forhånd (frø 458890695): tre påstander trukket,
tre treff (225 felles MMSI, 52 MB i timen, 3814 MMSI i `mmsiinarea`),
ingen avvik.
