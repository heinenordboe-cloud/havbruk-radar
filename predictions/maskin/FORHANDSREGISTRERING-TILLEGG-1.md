# Tillegg 1 til forhåndsregistreringen: hvor ukefilene ligger

Skrevet 17.11.2026 kl. 23:35 UTC, i uke 2026-W47. HEAD i `havbruk-radar`
var b1d0a5e. Fila stemples med OpenTimestamps
(`FORHANDSREGISTRERING-TILLEGG-1.md.ots`) og committes før noen uke er
forseglet i datarepoet.

`FORHANDSREGISTRERING.md` er ikke endret. Dette tillegget endrer én
ting: hvor filene ligger.

## Fra og med uke 2026-W48

Uke 2026-W48 begynner mandag 23.11.2026. Fra og med den uka ligger
ukefila `predictions/maskin/<år>-<uke>.yml`, stempelet `.ots` ved siden
av den og `forseglinger.tsv` i `havbruk-radar-data`, under samme relative
sti som før. `anslag.py` skriver fra da av bare der.

`fasiten.json` og `treffliste.md` skrives ett sted, i `havbruk-radar-data`
under `predictions/maskin/`, og dekker alle forseglede uker. Hver rad i
`fasiten.json` oppgir repoet og stien til ukefila.

Uke 2026-W46 og 2026-W47 er forseglet i `havbruk-radar` og blir liggende
der, uendret, med `forseglinger.tsv` for de to ukene. Ingen ukefil
flyttes, og ingen uke ligger begge steder.

`havbruk-radar-data` er et privat repo. En ukefil kan derfor ikke leses i
det åpne kodrepoet den uka den forsegles. Beviset for tidspunktet er som
før blokken i det oppgraderte stempelet. Det gjelder sha256 av fila,
uansett hvor fila ligger.

## Ingenting annet endres

Typene (K2 hovedtype, K6 PRØVETYPE), modellen, referansene, målet,
skåren, fristen søndag 24:00 UTC, hva som teller og lesemåten er som i
`FORHANDSREGISTRERING.md`. En uke er forseglet når ukefila har en `.ots`
ved siden av seg og summen i den er sha256 av fila.
