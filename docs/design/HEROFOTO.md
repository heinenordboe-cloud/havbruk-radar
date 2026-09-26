# Herofotografiet — HISTORIKK, ute av bruk 26.09.2026

**FILENE ER SLETTET.** `maler/bilde/hero-{800,1600,2400}.jpg` lå her
fram til 26.09.2026 og er borte: heroen er nå et kart — Kartverkets
kystkontur med hver av de 1 782 lokalitetene tegnet inn, se
`KARTGEOMETRI.md`. Skybildet var en stemning uten en eneste opplysning
i seg.

Notatet står igjen som historikk over hva som en gang lå der, og fordi
proveniensen til en fil som HAR vært publisert ikke slettes med fila.
Pinningene i `publiseringsvakt.BINAERFILER` og raden i tabell 2 i
`LISENSKJEDE.md` er derimot fjernet: en kvittering for noe som ikke
finnes er støy som skjuler at den ekte fila er ukvittert, og en rad om
et lån vi ikke lenger tar er en usann opplysning.

Alt under er slik det sto.

---

Dette var proveniensen — samme krav som til fontene, og samme mønster
som `NEWSREADER.md` og `IBM-PLEX.md`.

## Kilde og lisens

| | |
|---|---|
| Motiv | «Snowy mountains overlook a dark choppy ocean under cloudy skies» |
| Fotograf | Wolfgang Hasselmann |
| Kilde | <https://unsplash.com/photos/cbaS3DXXCl4> |
| Lisens | Unsplash-lisensen — fri bruk, også kommersielt, uten tillatelse |
| Hentet | 2026-09-22 |

Unsplash-lisensen krever **ikke** navngiving. Fotografen er likevel
navngitt på `/om/` og her, av samme grunn som at kildene er det: en
side som ikke sier hvor noe kommer fra, kan ingen etterprøve. Lisensen
forbyr å selge kopier av bildet uendret og å bygge en konkurrerende
bildetjeneste på det — ingen av delene skjer her.

## HVORFOR VI HOSTER DET SELV

`images.unsplash.com` i markupen ville gjort tre ting vi ikke vil:
fortalt Unsplash hvem som leser forsiden, gjort sidens hovedbilde
avhengig av at en tredjepart svarer, og lagt en tredjeparts URL inn i
en side som skal kunne arkiveres. Samme argument som for fontene.

## Sjekksummer

    maler/bilde/hero-800.jpg    106 379 byte
    4aececeb4f01f8b9cfc445d3dc687c9f6fd8415c788615e5ffc4af9035b0ccbd

    maler/bilde/hero-1600.jpg   375 531 byte
    3c8c0e7f92dbcc8e63791f96886f7faeef079b60834f3ad716c8433f7a7ac1e8

    maler/bilde/hero-2400.jpg   818 791 byte
    1233af0d2cb4ced13f084ca41aaae198d6cea6a172585ddb1af085e6a244c781

## Hvordan de ble hentet

    curl -o hero-<w>.jpg \
      "https://images.unsplash.com/photo-1778598707323-dff7934497a8\
       ?fm=jpg&q=72&w=<w>&auto=format&fit=crop"

Tre bredder fordi `srcset` skal ha noe å velge mellom: en telefon
henter 106 kB der en 1440-skjerm henter 375.

**IKKE FORHÅNDSBESKÅRET.** Fila er portrett 2:3, som kilden leverer
den, og utsnittet velges i CSS med `object-position: center 42%`.
Overleveringen ber uttrykkelig om det: en beskjæring baker inn et valg
som da ikke lenger kan gjøres om uten å hente bildet på nytt.

## Hva som står av data inne i filene

Publiseringsvakten kan ikke lese en JPEG som tekst, og den skal ikke
anta at en binærfil er trygg. Segmentene er derfor lest ut én gang, og
alle tre filene har de samme:

    APP0 (0xE0)   JFIF 1.02, 72x72 dpi
    APP2 (0xE2)   ICC-profil, «sRGB IEC61966-2.1», Hewlett-Packard 1998
    DQT, SOF2, DHT, SOS   selve bildet

**Ingen APP1.** Det er EXIF-segmentet, og fraværet av det betyr at det
ikke finnes kameramodell, serienummer, opptakstidspunkt, GPS-posisjon
eller fotografnavn i fila — Unsplashs CDN stripper dem. De eneste
lesbare strengene i de første 4 kB er ICC-profilens egne
(«sRGB IEC61966-2.1», «IEC http://www.iec.ch» og tilsvarende).

`publiseringsvakt.BINAERFILER` pinner sha256-summene over: endres en
fil, treffer ikke summen lenger, porten faller til `ugranska`, og
inspeksjonen må gjøres på nytt. Det skjedde faktisk ved første bygg —
de tre filene gikk ut umerket, og porten stoppet publiseringen med
«ugranska — .jpg». Det er slik den skal virke.

## Oppdatering

Hent på nytt, les segmentene, skriv om summene her OG i
`publiseringsvakt.BINAERFILER`. Ingen automatikk: en binærfil som
endrer seg uten at noen ser inn i den, er en binærfil ingen har sett i.
