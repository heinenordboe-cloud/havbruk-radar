# Skjermbilder av det som faktisk ble bygget

Tatt 23.09.2026 av det ferdige bygget, ikke av prototypene.
Lys modus, `deviceScaleFactor: 1`, fem sider i to bredder.

| Fil | Side |
|---|---|
| `forside-*.png` | `/` |
| `lokalitet-31397-*.png` | `/lokalitet/31397/` — OTERNESET |
| `produksjonsomrade-4-*.png` | `/produksjonsomrade/4/` — Nordhordland til Stadt |
| `selskap-964118191-*.png` | `/selskap/964118191/` — MOWI ASA |
| `endringer-2026-39-*.png` | `/endringer/2026-39/` — siste uke |

## Bildene er KUTTET ved 9 000 px, og det står her fordi det er et kutt

Full sidehøyde for endringssiden er 65 472 px ved 390 px bredde: 812
rader. Et slikt bilde er ikke et skjermbilde av et design, det er et
arkiv av en tabell — og det ville ligget i git for alltid.

Kuttet gjelder `lokalitet-390`, `produksjonsomrade-4` i begge bredder,
`selskap-964118191` i begge og `endringer-2026-39` i begge. Forsiden og
lokalitetssiden ved 1440 px er hele.

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
