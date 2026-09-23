# Newsreader — hvor fila kommer fra, og hvordan den er laget

`maler/newsreader.woff2` er en av de tre binærfilene nettstedet sender
ut — de to andre er IBM Plex Sans og Mono, se `IBM-PLEX.md`. Den er
hostet av oss og hentes aldri fra en CDN. Dette er proveniensen — samme
krav som til enhver annen hentet fil i repoet.

**Fila er laget om 22.09.2026** (vekt 300 og samisk lagt til). Den
forrige utgaven — `wght` 400–700, 203 glyffer, 35 520 byte, sha256
`d8e551fa…8b01fcc7` — står nederst under «Forrige utgave», fordi en
sjekksum som forsvinner er en sjekksum ingen kan etterprøve.

## Kilde og lisens

| | |
|---|---|
| Familie | Newsreader, av Production Type |
| Opphav | `github.com/productiontype/Newsreader` via `google/fonts` |
| Lisens | SIL Open Font License 1.1 — `maler/newsreader-OFL.txt` |
| Opphavsrett | Copyright 2020 The Newsreader Project Authors |

OFL krever at lisensteksten følger fonten. `nettsted.skriv_fonter()`
kopierer derfor både `newsreader.woff2` og `newsreader-OFL.txt` til
nettstedets rot; en publisert side har dem på `/newsreader.woff2` og
`/newsreader-OFL.txt`.

## Sjekksummer

    kilde   Newsreader.ttf (variabel, opsz 6–72, wght 200–800)
            8a08d13f8a6c0d51be379a60af84f945f65369a67e509ee3c3bdcc421254d7c1

    vår     maler/newsreader.woff2   64 800 byte
            14209ccee1fac927285fbf69eab415c27815d6b90c249ed07b807cf37f75faa9

    lisens  maler/newsreader-OFL.txt
            fdfad38143ec470553cae82a1e45320bdd1b9ec70415d37bd0171051d8a4ded8

## Hvordan den ble laget

    fonttools varLib.instancer Newsreader.ttf opsz=28 wght=300:700 \
        -o Newsreader-pinned.ttf

    pyftsubset Newsreader-pinned.ttf --unicodes="$UNI" \
        --layout-features='kern,liga,calt,ccmp,locl,mark,mkmk' \
        --flavor=woff2 --output-file=newsreader.woff2

`$UNI` er den SAMME strengen de to Plex-fontene bruker, ordrett fra
`IBM-PLEX.md`. Tre fonter med hvert sitt subsett er tre steder en glyff
kan mangle i én av dem, og symptomet — ett tegn i en annen font midt i
et ord — ser ut som et designvalg framfor en manglende glyff.

451 kB TTF ble 64,8 kB woff2. `wght` er beholdt som akse 300–700, slik
at `font-weight: 300 700` i `@font-face` er en påstand fila kan innfri.

### Hvorfor 300 og ikke 400 som gulv

Designoverleveringen setter hver eneste Newsreader-overskrift i 300:
ordmerket i heroen (104 px), H1 på undersidene (76 px), H2 på
seksjonene (46 px) og nøkkeltallene (52 px). Bare ordmerket i
navigasjonen og noen blokkoverskrifter står i 400.

Det er ikke pynt. En displayserif i 104 px satt i Regular er tung på en
måte den ikke er i 16 px — vekt og optisk størrelse trekker samme vei,
og en font som bare har 400 som letteste vekt kan ikke sette en stor
overskrift lett. Fram til 22.09.2026 hadde fila ikke 300, og en
`font-weight: 300` i CSS-en ville da fått 400 uten å si fra.

### Og hvorfor 203 glyffer ble 339

Latin Extended-A, av samme grunn som i `IBM-PLEX.md`: samiske
stedsnavn. Begrunnelsen og målingen står der, og den gjelder alle tre
fontene.

## opsz ER 28, selv om navnetabellen sier «16pt»

Dette er den ene fella i fila, og den er verdt å skrive ned fordi den
ser ut som en motsigelse.

`name`-tabellen i den ferdige fonten sier `Newsreader 16pt`. Den
strengen er IKKE en opplysning om hva som er pinnet — `varLib.instancer`
skriver ikke om familienavnet når `opsz` låses, så etiketten er en
levning fra kilda.

Verdien er i stedet MÅLT, ved å instansiere kilda på fire ulike `opsz`
og sammenligne punktkoordinatene i glyffen `H` mot fila vi sender ut:

    opsz=14   (443, 111), (614, 61), (614, 0), (93, 0), …
    opsz=16   (423, 101), (588, 50), (588, 0), (89, 0), …
    opsz=18   (403,  91), (561, 39), (561, 0), (85, 0), …
    opsz=28   (412,  87), (574, 37), (574, 0), (82, 0), …   <- vår fil

Det er samme prøve som ellers i repoet: spør om DET du vil vite
(«hvilken optisk størrelse har omrisset») framfor om noe som korrelerer
med det («hva heter fila»). Se CLAUDE.md 1b-2.

28 er valgt fordi fonten bare settes i overskrifter og i ordmerket —
36px, 24px, 20px. Brødteksten er systemets sans, og et `opsz` for
brødtekst ville vært feil optisk størrelse for den eneste jobben fonten
har.

## Hva som står av tekst inne i fila

Publiseringsvakten kan ikke lese en woff2 som tekst, og den skal ikke
anta at en binærfil er trygg. `name`-tabellen er derfor inspisert én
gang, og innholdet er:

    nameID   0  Copyright 2020 The Newsreader Project Authors (…)
    nameID   1  Newsreader 16pt
    nameID   2  Regular
    nameID   3  1.003;PROD;Newsreader16pt-Regular
    nameID   4  Newsreader 16pt Regular
    nameID   5  Version 1.003
    nameID   6  Newsreader16pt-Regular
    nameID 256  Weight            257  Optical Size
    nameID 259  Light             260  Regular
    nameID 261  Medium            262  SemiBold
    nameID 263  Bold
    nameID 268  Italic            269  Roman

(`259 Light` kom til 22.09.2026 med vektaksens nye gulv. Resten er
uendret; tabellen er lest på nytt av fila som faktisk går ut.)

Ingen personnavn, ingen ni-sifrede tall, ingenting fra kildene våre.
`publiseringsvakt.BINAERFILER` pinner sha256-summen over: endres fila,
faller porten og inspeksjonen må gjøres på nytt.


## Forrige utgave (til og med 21.09.2026)

    vår     maler/newsreader.woff2   35 520 byte
            d8e551fa73a848a2bb3806bc725cb1b705c8ec1e7c203e8b51c5ee338b01fcc7
            opsz=28, wght 400–700, 203 glyffer

Kilda er den samme fila, og sha256-en på den er uendret
(`8a08d13f…1254d7c1`) — det er BARE instansieringen og subsettet som er
gjort om. Summen står her slik at en gammel publisering kan
etterprøves; `publiseringsvakt.BINAERFILER` pinner bare den nye, fordi
det er den som går ut.
