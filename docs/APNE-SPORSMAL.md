# Åpne spørsmål

Det ubesvarte, med begrunnelse for hvorfor det betyr noe. To tekniske
spørsmål står igjen, sortert etter hva som blokkerer mest.

**Hygieneregel:** Når et spørsmål avgjøres, skrives beslutningen i
`docs/beslutninger/` og spørsmålet fjernes herfra **i samme slengen**.
Regelen er ikke pynt — den er utledet av et målt tilfelle. Punkt 4 i
forgjengeren til denne fila handlet om Akvakulturregisteret og ble
stående etter at kilden var i drift, og neste økt leste det som
prosjektets neste steg. Et spørsmål som er besvart, men fortsatt står
oppført som åpent, er verre enn ingen liste: det sender arbeid etter
noe som allerede er gjort.

Flyttet hit fra prosjektmappa 12.09.2026. Fila lå utenfor repoet, og
det var feil sted — et åpent spørsmål som ikke ligger ved siden av
beslutningene sine, blir ikke lukket ved siden av dem heller.

---

## 1. Hvordan oppdage det uvanlige uten å definere det på forhånd

**Status:** Ubesvart. Største spørsmål i prosjektet.

Reglene i `rules/signals.yml` i dag er terskler: kapasitet opp mer enn
ti prosent, konkursflagg endret, bemanning ned tjue prosent. De fanger
det man allerede vet man leter etter.

Det som mangler er å oppdage at noe er rart *uten* å ha sagt på forhånd
hva rart betyr. Et selskap som vokser mot bransjesnittet. En region der
flere aktører beveger seg samtidig. En endring som i seg selv er liten,
men som kommer på et uvanlig tidspunkt.

Det krever et sammenligningsgrunnlag, altså historikk. Derfor kan det
ikke bygges nå — men det kan designes nå, og designet avgjør hva som
kan spørres om senere.

**Å ta stilling til:** Skal signallaget skille mellom regler (kjent
mønster) og avvik (statistisk uventet)? Hvor mye historikk kreves før
avviksdelen gir mening — tolv uker, seks måneder? Skal terskler kunne
læres fra data i stedet for settes for hånd?

---

## 2. Hva en språkmodell skal og ikke skal gjøre i pipelinen

**Status:** Ubesvart, men retningen er klar.

Foreløpig vurdering: en modell er en dårlig erstatning for en regel, og
en god leser av det reglene har funnet. Regler er deterministiske,
etterprøvbare og gratis. Det er egenskaper man ikke bør gi fra seg for
noe som skal kjøre ukentlig i to år uten tilsyn.

Der en modell derimot kan gjøre noe regler ikke kan: sammenfatte ukas
endringer til lesbar tekst, og lese ustrukturert kildemateriale
(nyhetsartikler, høringer, kunngjøringer) og trekke ut strukturerte
observasjoner.

**Å ta stilling til:** Hvor i pipelinen kalles en modell, og hva skjer
når kallet feiler eller svarer feil? Skal modellsvar lagres som
observasjoner på lik linje med registerdata, eller merkes som avledet?
Kostnad per kjøring over to år?
