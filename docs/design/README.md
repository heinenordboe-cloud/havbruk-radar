# Designmateriale som ikke er en beslutning

Her ligger tre logoforslag som **ikke er valgt**, og som lå i en
scratchpad da de ble laget. De ligger i repoet av én grunn: en
scratchpad slettes, og arbeidet ville vært borte uten at noen merket
det. Det er samme regel som CLAUDE.md punkt 5 — historikken lar seg
ikke rekonstruere — anvendt på noe mindre viktig enn et snapshot.

## Status 21.09.2026, ettermiddag

**Navnet er Kystloggen, og merket er ordet.** Ingen av de tre
forslagene under ble valgt. Ordmerket er «Kystloggen» i Newsreader
600, med én diskré aksentbruk: en tynn rustlinje under ordet —
`.merke--strek`. En logg er linjert.

Den andre varianten som ble tegnet, `.merke--punktum`, setter i stedet
et punktum i aksentfarge etter ordet. Begge ligger i `maler/stil.css`
avsnitt 2b; å bytte er å bytte klassen i `maler/merke.html.j2`, og
ingenting annet. Det var hele grunnen til at den fila ble laget, og
byttet fra «havbruk-radar» til «Kystloggen» bekreftet at det holder:
én linje i én fil.

Filene under er derfor skisser som IKKE ble brukt. De ligger her fordi
en forkastet skisse er en beslutning man skal kunne gå tilbake til, og
fordi de ellers ville forsvunnet med scratchpaden.

## `logoforslag.html`

Tre ordmerker, hvert vist i tre størrelser og på to flater (papir og
havbånd). Formene er SVG i markupen, ikke bildefiler — de arver
tekstfargen og kan ikke bli uskarpe.

| # | Navn | Hva formen sier | Innvending |
|---|------|-----------------|------------|
| 1 | Dybdelinje | Ekkoloddets spor: overflate, ett loddskudd ned, bunn. Måling, ikke dekorasjon. Sier hva nettstedet *gjør*. | Abstrakt; leses ikke uten forklaring. |
| 2 | Kvantisert bølge | Bølgen som trappekurve — leses både som sjø og som tidsserie. Prikken er siste måling. | Mest detaljert; svakest i 16 px. |
| 3 | Merden i vannskorpa | Ringen sett halvt over og halvt under flata. Den ene tingen dataene handler om. | Binder merket til bransjen, og kan leses som et standpunkt om oppdrett. |

Åpnes fila rett fra disk, henter den fonten fra `../../maler/newsreader.woff2`.

## Paletten hører ikke hjemme her

Fargene med begrunnelse, målte avstander og AA-tall står i
`maler/stil.css` avsnitt 1 — der de brukes. En kopi her ville vært en
kopi som kan bli gammel.
