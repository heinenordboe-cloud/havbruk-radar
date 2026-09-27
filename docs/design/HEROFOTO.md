# Herofotografiet — hvor fila kommer fra, og hva som står i den

`maler/bilde/hero-{800,1600,2400}.jpg` er de tre siste binærfilene
nettstedet sender ut. De er hostet av oss og hentes aldri fra Unsplash i
runtime. Dette er proveniensen — samme krav som til fontene, og samme
mønster som `NEWSREADER.md` og `IBM-PLEX.md`.

Fila er byttet én gang. **Det som står nederst, under «Historikken», er
en TIDLIGERE fil og ikke denne.** Den seksjonen slettes ikke: en
proveniens som bare viser den siste fila, kan ikke svare på hva en
arkivert kopi av forsiden fra september 2026 viste.

---

## Kilde og lisens

| | |
|---|---|
| Motiv | Skjærgård i vinterlys, med et oppdrettsanlegg ved horisonten |
| Sted | Bømlo, Vestland — fotografens egen stedsangivelse på Unsplash |
| Fotograf | Endre Stedje |
| Kilde | <https://unsplash.com/photos/nTRAnQQ3E18> |
| Lisens | Unsplash-lisensen — fri bruk, også kommersielt, uten tillatelse |
| Utgitt | 12.02.2021 (`created_at` hos Unsplash) |
| Hentet | 2026-09-27 |
| Original | 5460 × 3640, altså 3:2 liggende |

Unsplash-lisensen krever **ikke** navngiving. Fotografen er likevel
navngitt i bildeteksten i heroen, på `/om/` og her, av samme grunn som
at kildene er det: en side som ikke sier hvor noe kommer fra, kan ingen
etterprøve. Lisensen forbyr å selge kopier av bildet uendret og å bygge
en konkurrerende bildetjeneste på det — ingen av delene skjer her.

Lisensvilkåret er lest 27.09.2026 på <https://unsplash.com/license>, og
datoen står også i `docs/LISENSKJEDE.md`. Et vilkår er en tredjeparts
påstand som kan endres uten at fila beveger seg.

**IKKE UNSPLASH+.** Det er et eget, betalt lisensnivå med andre vilkår,
og et bilde derfra kunne ikke ligget her. Sjekket i Unsplashs eget
API-svar for bildet: `premium: false`, `plus: false`.

## HVORFOR AKKURAT DETTE MOTIVET

Anlegget står i bildet. En rad merder med gule blåser og en båt ved
siden, ute ved horisonten i venstre halvdel — det nettstedet handler om,
i motivet, uten å være poenget. Det var grunnen til at dette ble valgt
framfor fire andre kandidater 27.09.2026.

**Ingen merking er lesbar.** Hele anlegget er ~35 piksler høyt i en
original som er 5460 bred. Utsnitt i full oppløsning er gransket før
fila ble hentet: ingen selskapsnavn, ingen logo, ingen skrogtekst. Det
var en forutsetning for valget, ikke en etterpåbetraktning — et
fotografi på forsiden som navnga ett foretak, ville vært en redaksjonell
påstand nettstedet ikke gjør noe annet sted.

**Ingen gjenkjennelige personer.** Det eneste menneskeskapte i forgrunnen
er et hvitt sjømerke på et nes.

## HVORFOR VI HOSTER DET SELV

`images.unsplash.com` i markupen ville gjort tre ting vi ikke vil:
fortalt Unsplash hvem som leser forsiden, gjort sidens hovedbilde
avhengig av at en tredjepart svarer, og lagt en tredjeparts URL inn i
en side som skal kunne arkiveres. Samme argument som for fontene.

## Sjekksummer

    maler/bilde/hero-800.jpg     92 684 byte
    6224f61202565528906461f2ecfc484a88cf935a7ad86a76a200557aaa35677b

    maler/bilde/hero-1600.jpg   331 228 byte
    3dac4870d4895a111da2154461f661e6990db5dd9ba6797c557cd639335e906e

    maler/bilde/hero-2400.jpg   694 755 byte
    5104b250b2fbf42a9c3c5114491908e58f3b2bb817aaa0420ce2ed694c0e11f5

## Hvordan de ble hentet

    curl -o hero-<w>.jpg \
      "https://images.unsplash.com/photo-1613150487508-7d793b71cf72\
       ?fm=jpg&q=55&w=<w>"

Tre bredder fordi `srcset` skal ha noe å velge mellom: en telefon henter
93 kB der en 1440-skjerm henter 331.

**KVALITETEN ER 55, ikke 72 som forrige fil.** Budsjettet var 800 ≤ 120
kB og 1600 ≤ 350 kB, og dette motivet er dyrere enn det forrige: bergene
i forgrunnen er finmasket tekstur som JPEG bruker mange byte på. Målt
over fem kvalitetstrinn:

    q    800        1600
    35   —          209 315
    42   —          259 209
    48   —          286 442
    55    92 684    331 228      <- valgt
    62   101 769    365 327      <- 1600 over taket
    72   109 299    393 188

Himmelen er kontrollert visuelt ved q=55 på et 1600-utsnitt: ingen
blokkartefakter, ingen banding. Det er den flata teksten står på, så det
er den flata som avgjorde.

**IKKE FORHÅNDSBESKÅRET.** Fila er liggende 3:2, som kilden leverer
den, og utsnittet velges i CSS med `object-position`. En beskjæring
baker inn et valg som da ikke lenger kan gjøres om uten å hente bildet
på nytt — og her er valget dessuten forskjellig per skjermbredde: på
390 piksler er det bredden som beskjæres, på 1440 er det høyden.

## Hva som står av data inne i filene

Publiseringsvakten kan ikke lese en JPEG som tekst, og den skal ikke
anta at en binærfil er trygg. Segmentene er derfor lest ut én gang, og
alle tre filene har de samme:

    APP0 (0xE0)   JFIF 1.02, 72x72 dpi, 16 byte
    APP2 (0xE2)   ICC-profil, «sRGB IEC61966-2.1», Hewlett-Packard 1998,
                  3 160 byte
    DQT, SOF2, DHT, SOS   selve bildet, progressiv

**Ingen APP1.** Det er EXIF- og XMP-segmentet, og fraværet av det betyr
at det ikke finnes kameramodell, serienummer, opptakstidspunkt,
GPS-posisjon eller fotografnavn i fila. Ingen APP13 (IPTC) og ingen
APP14 heller.

**Hva som ble fjernet, og av hvem:** ingenting av oss. Unsplashs CDN
leverer allerede uten APP1 — også den utransformerte originalen på 4,7
MB, som er kontrollert særskilt nettopp for å kunne si dette: der er
segmentene APP0 og APP2 og ikke noe mer. Vi kan derfor **ikke** si hva
fotografens egen fil inneholdt, bare at ingen av de tre filene vi sender
ut bærer EXIF eller GPS. Det er forskjell på de to påstandene, og bare
den andre er noe vi har sett.

De eneste lesbare strengene i de første 8 kB er ICC-profilens egne:
«sRGB IEC61966-2.1», «IEC http://www.iec.ch», «Copyright (c) 1998
Hewlett-Packard Company» og tilsvarende. Kontrollert i alle tre filene.

`publiseringsvakt.BINAERFILER` pinner sha256-summene over: endres en
fil, treffer ikke summen lenger, porten faller til `ugranska`, og
inspeksjonen må gjøres på nytt.

## Oppdatering

Hent på nytt, les segmentene, skriv om summene her OG i
`publiseringsvakt.BINAERFILER`. Gjør du bare det ene, faller porten —
og det er slik den skal virke.

---

# Historikken

## 22.09.2026 – 26.09.2026: snøfjell over mørkt hav

Forsidens første herofotografi. Byttet til et kart 26.09.2026
(`5ddffed`), og kartet ble byttet til dette bildet 27.09.2026.

| | |
|---|---|
| Motiv | «Snowy mountains overlook a dark choppy ocean under cloudy skies» |
| Fotograf | Wolfgang Hasselmann |
| Kilde | <https://unsplash.com/photos/cbaS3DXXCl4> |
| Lisens | Unsplash-lisensen |
| Hentet | 2026-09-22 |
| Original | portrett 2:3, utsnitt valgt med `object-position: center 42%` |

Sjekksummene, for den som gransker en arkivert kopi av forsiden fra den
uka:

    hero-800.jpg    106 379 byte
    4aececeb4f01f8b9cfc445d3dc687c9f6fd8415c788615e5ffc4af9035b0ccbd

    hero-1600.jpg   375 531 byte
    3c8c0e7f92dbcc8e63791f96886f7faeef079b60834f3ad716c8433f7a7ac1e8

    hero-2400.jpg   818 791 byte
    1233af0d2cb4ced13f084ca41aaae198d6cea6a172585ddb1af085e6a244c781

Hentet med `?fm=jpg&q=72&w=<w>&auto=format&fit=crop`. Segmentene var de
samme tre som nå — APP0, APP2, ingen APP1.

Hvorfor det gikk ut: skybildet var en stemning og ikke en opplysning.
Heroen ble kartet over kysten med hver lokalitet på den, og det varte i
ett døgn: et kart i heroen gjentok kartet lenger ned på siden, og en
forside som åpner med det samme kartet to ganger sier mindre enn en som
åpner med kysten og deretter viser den oppdelt.

## 26.09.2026 – 27.09.2026: kartet

`/kart/norge.svg`, skrevet av `nettsted.skriv_norgeskart()`. En SVG er
tekst, granskes som all annen tekst og trengte ingen pinning — derfor
sto `BINAERFILER` uten herofiler i det døgnet.

Fila er slettet sammen med heroen, og det er målt før den ble det:
`/kart/norge.svg` hadde nøyaktig én bruker, `<img class="hero-kart">` på
forsiden. Kystseksjonen lenger ned tegner sitt eget kart INN i sida av
`f.kart` og har aldri hentet denne fila. Kartene ellers på nettstedet —
lokalitet, område — er uberørte; det er `kart.norgeskart()` alene som
gikk ut.
