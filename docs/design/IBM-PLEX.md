# IBM Plex Sans og Mono — hvor filene kommer fra, og hvordan de er laget

`maler/ibmplexsans.woff2` og `maler/ibmplexmono.woff2` er to av de tre
binærfilene nettstedet sender ut. De er hostet av oss og hentes aldri
fra en CDN. Dette er proveniensen — samme krav som til enhver annen
hentet fil i repoet, og samme mønster som `NEWSREADER.md`.

## Kilde og lisens

| | |
|---|---|
| Familier | IBM Plex Sans og IBM Plex Mono, av IBM (Bold Monday / Mike Abbink) |
| Opphav | `github.com/IBM/plex` via `google/fonts` |
| Lisens | SIL Open Font License 1.1 — `maler/ibmplex-OFL.txt` |
| Opphavsrett | Copyright 2019 IBM Corp. (Sans), Copyright 2017 IBM Corp. (Mono) |
| Hentet | 2026-09-22 |

Begge familiene ligger under SAMME OFL-fil hos `google/fonts`, og de to
kopiene er bit-identiske (`sha256 7e6b2818…` for begge). Én fil i
`maler/` er derfor ikke en forenkling — det er den samme fila.

OFL krever at lisensteksten følger fonten. `nettsted.skriv_fonter()`
kopierer `ibmplex-OFL.txt` til nettstedets rot sammen med woff2-filene;
en publisert side har dem på `/ibmplex-OFL.txt`,
`/ibmplexsans.woff2` og `/ibmplexmono.woff2`.

## Hvorfor disse to, og ikke systemfonten

Fram til 22.09.2026 var brødteksten systemets egen sans, og
begrunnelsen sto i `stil.css` avsnitt 2: ingen henting, og målebåndet
`--maal-tekst` var målt mot glyffbreddene i SF Pro og Helvetica.

Designoverleveringen setter brødteksten i IBM Plex Sans og
tallkolonnene i IBM Plex Mono, og det er ikke en smakssak her: en
tabellkolonne med tall skal ha fast sifferbredde, og `tabular-nums` i
en systemfont er et løfte fonten kan innfri eller la være, avhengig av
hvilken maskin leseren sitter på. En hostet mono er den eneste måten å
vite at kolonnen står i flukt hos alle.

Prisen er 51 kB til, og målebåndet måtte måles på nytt — se
`--maal-tekst` i `stil.css`.

## Sjekksummer

    kilde   IBMPlexSans[wdth,wght].ttf  (variabel, wght 100–700, wdth 75–100)
            3b031aa4216174205bd8471f88a49b91f093169e9e87bd5262242bc5967fe2e3

    kilde   IBMPlexMono-Regular.ttf     (statisk)
            6a3412f058c7d8dfd9170c41e85ade48e5156ecb89356110ca57a0a27734af46

    vår     maler/ibmplexsans.woff2     35 224 byte
            0e98868216b2ed175098bedc3ece2273382dc9b1f23bdd911bb12ebedfaa6344

    vår     maler/ibmplexmono.woff2     15 588 byte
            6e32afc77a2d702137db7bd95f8dd435db6861ae1ae8a56b001ac8a8e851edca

    lisens  maler/ibmplex-OFL.txt        4 456 byte
            7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da

## Hvordan de ble laget

Tegnsettet er ÉN streng, brukt på alle tre fontene. Det er med vilje:
tre fonter med hvert sitt subsett er tre steder en glyff kan mangle i
én av dem, og symptomet — ett tegn i en annen font midt i et ord — ser
ut som et designvalg framfor en manglende glyff.

    UNI="U+0020-007E,U+00A0-00FF,U+0100-017F,\
    U+2010-2015,U+2018-201A,U+201C-201E,U+2020-2022,U+2026,U+2030,\
    U+2032-2033,U+2039-203A,U+2044,U+20AC,U+2122,\
    U+2190-2193,U+2197,U+2212,U+2264-2265,U+00B0,U+00B7,U+00D7"

    # Sans: wdth låses, wght beholdes som akse 400–600
    fonttools varLib.instancer IBMPlexSans[wdth,wght].ttf \
        wdth=100 wght=400:600 -o PlexSans-pinned.ttf

    pyftsubset PlexSans-pinned.ttf --unicodes="$UNI" \
        --layout-features='kern,liga,calt,ccmp,locl,mark,mkmk' \
        --flavor=woff2 --output-file=ibmplexsans.woff2

    # Mono: statisk Regular, ingen akse å låse
    pyftsubset IBMPlexMono-Regular.ttf --unicodes="$UNI" \
        --layout-features='kern,ccmp,locl,mark,mkmk' \
        --flavor=woff2 --output-file=ibmplexmono.woff2

537 kB TTF ble 35,2 kB woff2 (Sans), 136 kB ble 15,6 kB (Mono).
`wght` er beholdt som akse 400–600 i Sans, slik at
`font-weight: 400 600` i `@font-face` er en påstand fila kan innfri —
designet bruker 400, 500 og 600.

Mono har bare én vekt fordi den bare har én jobb: tallverdier i
tabellkolonner. En mono i halvfet ville vært en ny rolle, og en fil
som bærer en vekt ingen bruker er en fil som påstår noe om designet.

## HVORFOR TEGNSETTET ER STØRRE ENN DET SOM MÅLES I BRUK

MÅLT 22.09.2026 over alle 2 281 publiserte HTML-filer: 105 unike tegn,
hvorav 17 over ASCII. Det ville vært et subsett på under 130 glyffer.
Filene her har 351 (Sans), 347 (Mono) og 339 (Newsreader).

Forskjellen er Latin Extended-A, og den står der for SAMISK. Registeret
er en tredjeparts liste over stedsnavn i Norge, og den listen er ikke
ferdig: `Á` står allerede 71 ganger i utputtet, og `Č`, `Đ`, `Ŋ`, `Š`,
`Ŧ` og `Ž` er de neste når en lokalitet i Finnmark får et navn på
nordsamisk. Et subsett målt på dagens utputt ville vært riktig i dag og
falt tilbake på en annen font i det ordet neste uke — og det synes som
et annet omriss midt i et navn.

Det er samme regel som ellers her: et tall som bare stemmer for dagens
data er ikke et mål, det er et sammentreff. Prisen for hele
Latin Extended-A er målt til 136 glyffer og noen kB per fil.

## Hva som står av tekst inne i filene

Publiseringsvakten kan ikke lese en woff2 som tekst, og den skal ikke
anta at en binærfil er trygg. `name`-tabellene er derfor inspisert én
gang, og innholdet er:

    ibmplexsans.woff2
      nameID   0  Copyright 2019 IBM Corp. All rights reserved.
      nameID   1  IBM Plex Sans          nameID   2  Regular
      nameID   3  IBM;IBMPlexSans-Regular;3.201;2024
      nameID   4  IBM Plex Sans Regular  nameID   5  Version 3.201
      nameID   6  IBMPlexSans-Regular
      nameID 256/295  Weight             nameID 304  Width
      nameID 264/267–270, 299–302        stil- og vektnavn
      nameID 306–308  Normal, Italic, Roman

    ibmplexmono.woff2
      nameID   0  Copyright 2017 IBM Corp. All rights reserved.
      nameID   1  IBM Plex Mono          nameID   2  Regular
      nameID   3  2.3;IBM ;IBMPlexMono-Regular
      nameID   4  IBM Plex Mono Regular  nameID   5  Version 2.3
      nameID   6  IBMPlexMono-Regular

Ingen personnavn, ingen ni-sifrede tall, ingenting fra kildene våre.
`publiseringsvakt.BINAERFILER` pinner sha256-summene over: endres en
fil, faller porten og inspeksjonen må gjøres på nytt.

## Oppdatering

Hent kildefilene på nytt, sammenlign sha256 mot tallene over, kjør de
samme kommandoene, og skriv om summene her OG i
`publiseringsvakt.BINAERFILER`. Ingen npm, ingen byggesteg, ingen
automatikk — samme begrunnelse som for `tokens.css`.
