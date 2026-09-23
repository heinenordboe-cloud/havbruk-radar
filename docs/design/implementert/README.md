# Skjermbilder av det som faktisk ble bygget

Tatt 23.09.2026 av det ferdige bygget, ikke av prototypene.
Lys modus, `deviceScaleFactor: 1`, fem sider i to bredder.

**Fornyet 23.09.2026, etter tre endringer som alle er synlige i
bildene:** uke 39 sier 38 endringer og ikke 812, selskapsdata står i
sin egen sammenfoldede del nederst på endringssiden, og
produksjonsområdesiden har den nye beleggsgraden «beslutning» med
sitatet fra departementets kunngjøring.

| Fil | Side |
|---|---|
| `forside-*.png` | `/` |
| `lokalitet-31397-*.png` | `/lokalitet/31397/` — OTERNESET |
| `produksjonsomrade-4-*.png` | `/produksjonsomrade/4/` — Nordhordland til Stadt |
| `selskap-964118191-*.png` | `/selskap/964118191/` — MOWI ASA |
| `endringer-2026-39-*.png` | `/endringer/2026-39/` — siste uke |

## Bildene er KUTTET ved 9 000 px, og det står her fordi det er et kutt

| fil | px | hel? |
|---|---:|---|
| `forside-1440` | 5 086 | hel |
| `forside-390` | 7 484 | hel |
| `lokalitet-31397-1440` | 7 467 | hel |
| `lokalitet-31397-390` | 9 000 | kuttet av 12 538 |
| `produksjonsomrade-4-1440` | 9 000 | kuttet av 14 695 |
| `produksjonsomrade-4-390` | 9 000 | kuttet av 25 097 |
| `selskap-964118191-1440` | 9 000 | kuttet av 16 816 |
| `selskap-964118191-390` | 9 000 | kuttet av 45 401 |
| `endringer-2026-39-1440` | 5 518 | hel |
| `endringer-2026-39-390` | 9 000 | kuttet av 9 112 |

Endringssiden ved 1440 px er nå HEL, og det er en følge av designet og
ikke av kuttet: de 402 selskapsdataradene ligger i en `<details>` som
skriptet lukker. Før 23.09 var den samme siden 43 322 px.

## Hvordan de er tatt

Chrome i hodeløs modus over DevTools-protokollen —
`Page.captureScreenshot` med `captureBeyondViewport`, som er det eneste
som gir mer enn viewporten. `Emulation.setEmulatedMedia` tvinger
`prefers-color-scheme: light`, fordi maskinen som tar bildet kan stå i
mørk modus og da ville bildene vist noe annet enn det som ble bedt om.

Skriptet er ikke i repoet: det er et verktøy, som pagefind-binæren og
`pyftsubset`. Se `docs/design/PAGEFIND.md` om hvorfor verktøy ikke bor
her.

## Én feil ble funnet av å ta dem

Ved 390 px var forsiden 489 px bred — den eneste siden på nettstedet
med vannrett rulling. `.kyst-to` var et rutenett uten
`grid-template-columns`, og et `<svg>` med egne `width`/`height`
bidrar med SIN EGEN bredde til en `auto`-kolonne selv om det står
`inline-size: 100%` på det. Rettet i `maler/stil.css` samme dag; alle
sju sidetypene måler nå 390.
