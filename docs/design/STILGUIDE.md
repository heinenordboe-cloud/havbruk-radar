# Stilguide: åpne punkter

Denne fila ble opprettet 06.10.2026. Repoet hadde ingen stilguide fra
før. Designsystemet fra overleveringen ligger i
`overlevering/Kystloggen - Designsystem.dc.html` og er et eksternt
dokument, og fargene og skalaene står i `maler/stil.css`. Her står det
som er bestemt å *ikke* rette ennå, og hvorfor, slik at det ikke blir
glemt.

`tests/test_nettsted.py::KJENTE_UDEFINERTE` peker hit. En variabel som
står der, må stå her.

## `--farge-stripe` er udefinert, og radtonen i tabellene har ikke virket siden 22.09.2026

**Hva den skulle gjøre.** Annenhver rad i alle tabeller får en svak tone.
Kommentaren i `maler/stil.css` (ved `tbody tr:nth-child(even)`) sier:

> På en tabell med tre rader er den nesten usynlig; på /lokalitet/ med
> 1 782 rader og seks kolonner er den forskjellen på å kunne følge en rad
> tvers over og ikke. Tonen er 1,06:1 mot arket — den skal kunne ANES,
> ikke ses.

Den brukes tre steder: `tbody tr:nth-child(even)` og to regler for
korttabellene under 640 px (`.tabell--kort`).

**Hva som skjedde.** Variabelen var definert som `var(--stripe)` fra
Digdirs tokens. Da de ble tatt ut, 22.09.2026 (`781c7e8`, «Tokens og
fonter: Digdirs skjelett ut, tre egne fonter inn»), forsvant
definisjonen, men bruken ble stående. En udefinert `var()` gjør
`background` ugyldig når verdien regnes ut, uten feilmelding, så
radene har stått uten tone siden da.

**Hvorfor den ikke rettes nå.** Å definere den slår på en synlig endring
i hver tabell på nettstedet, i begge fargemodus. Verdien må velges for
lys og mørk modus og måles mot arket, og `tests/test_kontrast.py` leser
paletten. Det er en designbeslutning, ikke en feilretting.

**Når den rettes:** definer `--farge-stripe` i begge paletter, kjør
kontrastprøven, ta skjermbilder av en lang tabell (`/lokalitet/`) og en
kort (lokalitetens registerfelt) i 390 og 1440, lys og mørk, og stryk
den fra `KJENTE_UDEFINERTE`. Prøven feiler hvis den blir definert uten
å bli strøket.

## Rettet samme dag, til orientering

- `--rom-48`: taket på tilstandsspalta på lokalitetssiden (`3584188`).
- `--fs-16`: tegnforklaringen per runde på områdesiden (`.rundefakta-liste
  dt`). Satt til `1rem`, som er designsystemets brødtekst (16 px).
