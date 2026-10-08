# Stilguide: åpne punkter

Denne fila ble opprettet 06.10.2026. Repoet hadde ingen stilguide fra
før. Designsystemet fra overleveringen ligger i
`overlevering/Kystloggen - Designsystem.dc.html` og er et eksternt
dokument, og fargene og skalaene står i `maler/stil.css`. Her står det
som er bestemt å *ikke* rette ennå, og hvorfor, slik at det ikke blir
glemt.

`tests/test_nettsted.py::KJENTE_UDEFINERTE` peker hit. En variabel som
står der, må stå her.

## `--farge-stripe` — løst 08.10.2026

Radtonen i tabellene hadde ikke virket siden 22.09.2026, fordi
variabelen ikke var definert. I designrunden 08.10.2026 ble vekselvis
tone erstattet av en tone på raden under peker (`--rad-pa`), som gjør
jobben der den trengs: å følge en rad tvers over en lang tabell. Bruken
er fjernet fra stilarket, og `KJENTE_UDEFINERTE` i
`tests/test_nettsted.py` er tom.

## Rettet samme dag, til orientering

- `--rom-48`: taket på tilstandsspalta på lokalitetssiden (`3584188`).
- `--fs-16`: tegnforklaringen per runde på områdesiden (`.rundefakta-liste
  dt`). Satt til `1rem`, som er designsystemets brødtekst (16 px).
