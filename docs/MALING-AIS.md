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
