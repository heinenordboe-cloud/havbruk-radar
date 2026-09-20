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

---

## 3. Domenet er ikke valgt, og tre filer sier det

**Status:** Ubesvart. Blokkerer publisering, ikke bygging.

`sitemap.xml` krever absolutte URL-er etter spesifikasjonen, og
`robots.txt` sin `Sitemap:`-linje gjør det samme. Vi har ikke noe
vertsnavn, og et påfunnet ett ville vært en påstand om noe som ikke er
avgjort — samme grunn som JSON-LD-en lar være å oppgi `url`, se
`docs/beslutninger/2026-09-16-url-struktur.md`.

Bygget leser `HAVBRUK_BASEURL`. Uten den skrives stiene relative, og
begge filene sier i klartekst at de må bygges på nytt før de duger for
en søkemotor. **Det stoppet ikke byggingen fordi ingen side blir usann
av det** — en relativ sti peker riktig i en nettleser; det er bare
crawleren som trenger mer.

**Å ta stilling til:** hvilket domene, og dermed om
`HAVBRUK_BASEURL` settes i byggejobben eller i et
konfigurasjonssteg.

---

## 4. Kartet har ingen kystlinje, og punktene er ikke klikkbare

**Status:** Ubesvart. Design, ikke sannhet.

Forsidekartet er 1782 punkter uten bakgrunn. To ting mangler, og ingen
av dem gjør siden usann:

1. **Ingen kystlinje.** Vi har ingen kystlinjegeometri vi har lisens
   til å tegne. Kartverkets N50 er NLOD, men det er en ny kilde med
   egen lisensrad, egen vurdering og et størrelsesspørsmål — en
   forenklet kystlinje er fort flere megabyte inline SVG. Siden sier i
   dag uttrykkelig at kartet er punktene og ingenting annet.
2. **Punktene lenker ikke.** 1782 `<a>`-elementer med `<title>` ville
   omtrent doblet fila (82 kB i dag). Lokalitetslista dekker behovet
   for å finne fram; kartet viser utbredelse.

**Å ta stilling til:** om kartet skal være en inngang (klikkbare
punkter, farge etter trafikklysstatus) eller forbli en illustrasjon.
Farge etter status er det mest fristende og det som krever mest
omtanke: fargen gjelder produksjonsområdet, ikke lokaliteten, og et
kart som farger 1782 punkter etter et områdevedtak inviterer til å
lese det som en egenskap ved anlegget.

---

## 5. En side kan ikke si HVILKEN av de to grunnene som gjelder

**Status:** Ubesvart. Arvet fra `docs/REGEL-UENIGE-KILDER.md` punkt 4.

Når en tillatelse mangler eier, oppgir siden begge mulige grunner
(privatperson, eller ukjent eiertype) fordi snapshotet ikke inneholder
de filtrerte radene i det hele tatt. Målt 20.09.2026 gjelder det 84
tillatelser: 55 av den første grunnen, 29 av den andre.

Å gjøre det presist per tillatelse krever at `sources/eierskap.py`
STEMPLER grunnen i det øyeblikket den filtrerer — regel 1b-3, verdien
som avgjør hva dataene betyr lagres sammen med dem. Det er en
kildeendring med sin egen måling.

**Det stoppet ikke byggingen fordi siden ikke blir usann av det:** den
sier begge grunnene og påstår ikke å vite hvilken. Den blir bare mindre
presis enn den kunne vært.

---

## 6. Produksjonsområdesiden viser ikke biomasse

**Status:** Ubesvart. Utelatelse, ikke feil.

`biomasse` er månedlige beholdningstall per produksjonsområde — 10 990
changelog-rader mot trafikklysvedtakets 47 — og ble lagt i `MAALESERIER`
20.09.2026 slik at vedtaket ikke drukner i serien. Følgen er at siden
teller dem og viser dem ikke.

Det er riktig for en ENDRINGSTABELL, men det betyr at området ikke viser
hvor mye fisk som faktisk står der, og det er noe av det mest
interessante vi har om et produksjonsområde. Lusetall har samme form på
lokalitetssiden og løses der med en egen tabell over serien.

**Å ta stilling til:** om produksjonsområdesiden skal ha en
biomassetabell med sin egen serie, slik lokalitetssiden har for
lusetall. Kilden reviderer bakover (12,3 % av radene, målt 25.08), så en
slik tabell må vise hvilken henting tallene kommer fra — ellers sier den
noe annet neste måned uten at noen rørte den.
