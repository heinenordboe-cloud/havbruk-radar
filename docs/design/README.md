# Designmateriale som ikke er en beslutning

Her ligger tre logoforslag som **ikke er valgt**, og som lå i en
scratchpad da de ble laget. De ligger i repoet av én grunn: en
scratchpad slettes, og arbeidet ville vært borte uten at noen merket
det. Det er samme regel som CLAUDE.md punkt 5 — historikken lar seg
ikke rekonstruere — anvendt på noe mindre viktig enn et snapshot.

## Status 21.09.2026

**Logo og navn er ikke bestemt.** Nettstedet bruker ordmerket som ren
tekst i Newsreader, uten grafisk form. Markupen står ett sted,
`maler/merke.html.j2`, og stilen henger på klassen `.merke` i
`maler/stil.css`. Et valgt merke byttes inn ved å redigere den ene
malen; ingenting annet skal trenge å røres.

Det betyr også at ingenting i denne mappa er en påstand om hva
nettstedet heter eller ser ut som. Filene er skisser.

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
