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

---

## Fra designimplementeringen 22.09.2026

### 1. Hva BETYR ILA- og PD-flagget i BarentsWatch?

**Status: udokumentert hos kilden. Ordlyden på siden er nøytral.**

`lusetall.har_ila` og `har_pd` kommer fra `hasIla`/`hasPd` i
BarentsWatchs fiskehelse-API. Den offisielle OpenAPI-beskrivelsen
(hentet 22.09.2026 fra
`https://www.barentswatch.no/bwapi/openapi/fishhealth/openapi.json`,
sha256 `240c7d4596be8bcd…829e5a11`) sier om feltet bare:

> `hasIla` — «Does the site have ISA disease this week»
> `hasPd` — «Does the site have PD disease this week»

Den skiller **ikke** mistanke fra påvist.

At skillet FINNES hos kilden, er derimot dokumentert i det samme
skjemaet:

    IlaPd.ruling            «Mistanke or Påvist»
    IlaPdCase               suspectedDate, confirmedDate,
                            disproved, disprovedDate
    LocalityIlaPdLink       suspected (bool), confirmed (bool)

Den ENE boolske verdien vi får per uke kan altså dekke begge
tilstandene, og hvilken av dem den dekker står ikke skrevet noe sted vi
har lest.

**Følgen:** siden sier «ILA-flagg i BarentsWatch: satt», aldri «ILA
påvist». Ordet «påvist» brukes ikke før det er målt. En feilaktig
«påvist» ville vært en påstand om en veterinærmedisinsk konklusjon, om
et anlegg med navn og adresse.

**Hvordan spørsmålet kan avgjøres:** `ilaPdCase`-endepunktet gir
`suspectedDate`/`confirmedDate` per sak. En måling som henter sakene
for et utvalg lokaliteter og sammenligner mot ukeflagget, vil vise om
flagget står i mistankevinduet, i påvistvinduet, eller i begge. Det er
et kildespørsmål med et målbart svar — det er bare ikke målt.

MÅLT i vår egen changelog 22.09.2026: 3 323 `endret`-rader for de to
feltene, over 723 uker og 2 074 lokaliteter. Nyeste endring er
2024-12-09.

### 2. Sykdomsflaggene er datert til UKA, ikke til dagen vi så dem

`lusetall` er `verden`-partisjonert: `observed_at` er mandagen i ISO-uka
tellingen gjelder for. En ILA-endring datert 2019-11-18 gjelder uke 47
av 2019 — vi backfilte den i 2026.

Følgen er at sykdomsflaggene **ikke kan telle i ukesregnskapet** på
`/endringer/<år>-<uke>/`, som er en side om hva VI så en bestemt uke.
De står i lokalitetens tidslinje, merket «gjelder uka, ikke dagen vi så
det», og de telles i «utenfor ukesregnskapet».

Typen «Sykdom (ILA/PD)» vises derfor med 0 i alle
innsamlingsukene. Det er riktig, men det er også en etikett som aldri
kan bli noe annet så lenge lusetall er `verden`-partisjonert.

**Hva som ville løst det:** en kolonne i changeloggen for da raden ble
SKREVET (vår `fetched_at` for det snapshotet), ved siden av
`observed_at`. Da kunne en hendelse stå på begge akser med hver sin
dato. Det er en endring i `core/changelog.py` og dermed en egen
beslutning.

### 3. Atom-feedenes `updated` har et klokkeslett vi ikke har

Atom krever RFC 3339, altså et tidspunkt. Changeloggen har en DATO. Vi
skriver `T00:00:00Z`, og feedens `subtitle` sier at klokkeslettet er
utfylling.

**Hva som ville løst det:** `fetched_at` for (kilde, observed_at), som
ER et ekte tidspunkt. Det krever å lese alle snapshots av alle kilder
ved bygging, eller å bære feltet i changeloggen — se punkt 2, samme
endring.

### 4. Tiltaksgrensen for lakselus er ikke samlet inn

Overleveringen tegner en stiplet tiltaksgrense på 0,5 i lusegrafen, og
farger søyler over den i rust. Ingen av delene er bygget.

Grensa står i lakselusforskriften, varierer med sesong (0,2 i
vårperioden, 0,5 ellers) og kan settes per lokalitet ved vedtak. Ingen
av delene finnes i `lusetall`. En strek tegnet av oss ville vært en
påstand om regelverket, ikke en gjengivelse av en kilde.

**Hva som ville løst det:** forskriften som kilde, på samme måte som
`trafikklysvedtak` — med uttrekk, lesemåte og belegg per verdi.

### 5. En `borte`-oppføring kan ikke navngis

`hviteliste()` bygges av NYESTE øyeblikksbilde for hver
`henting`-partisjonerte kilde. En entitet som er BORTE er per
definisjon ikke der, så verken navnet eller organisasjonsnummeret er
gjort rede for. Endringssidene viser derfor `borte`-hendelser uten
identitet: kilde, dato og antall felt.

Hvitelista kan ikke bare utvides til «de siste N øyeblikksbildene»:
det ville gjenåpnet F15, der personformer skrevet inn før filteret
fantes ville blitt vasket inn igjen.

**Hva som ville løst det:** en egen, filtrert hviteliste over
entiteter som HAR vært i utvalget, bygget gjennom den samme lesedøra
og med personformene fjernet. Det er en utvidelse av
`publiseringsvakt.hviteliste()` og dermed en egen beslutning med sin
egen måling.

### 6. Kystlinja er 1:10 millioner

Omtrent 1 km oppløsning. På forsidens oversiktskart er det mer enn nok.
På et posisjonskart som dekker 36 km er en fjordarm gjengitt med noen
få punkter, og små holmer finnes ikke. 1 av 1 782 lokaliteter har ikke
land i utsnittet i det hele tatt.

Alternativene er Kartverkets N-serier (NLOD, men store nedlastinger bak
Geonorges API) og OpenStreetMap-avledet kystlinje (ODbL —
del-på-samme-vilkår, en tyngre lisens å ta inn i et arkiv som skal stå
i ti år).

### 7. Pagineringstaket og PERSONFORMER står fortsatt (fra 24.08.2026)

Se `docs/beslutninger/2026-08-24-utvalgsutvidelse-er-ikke-endring.md`.
Designrunden har ikke rørt noen av dem.

### 8. Ingen test måler en side som er LAGT UT

Fra 23.09.2026.

Forsiden rullet vannrett ved 390 px fra den ble bygget til den ble
skjermbildet — `document.scrollWidth` var 489 der viewporten var 390.
Den var den eneste av sju sidetyper med feilen, og 1 056 tester var
grønne hele tiden.

Grunnen er at ingen av dem måler et LAYOUT. `test_kontrast.py` leser
CSS-en som tekst og regner luminans; `test_markupkontrakt.py` leser
malene som tekst og krever `data-felt` og `scope`; resten leser data.
Ingen av dem vet hvor bred en `<figure>` ble.

En slik test krever en nettleser, og en nettleser er 200 MB som må
holdes oppdatert — den samme avveiningen som pagefind-binæren, men med
en vesentlig forskjell: pagefind-binæren er valgfri og bygget SIER fra
når den mangler. En layouttest som ikke kan kjøre, er en test som
stille slutter å gjelde, og det er formen på F4 og F8.

**Spørsmålet:** skal repoet ha en layoutprøve som krever Chrome, kjørt
manuelt før en designendring pushes og med et skript i `docs/`, eller
skal bredden håndheves i CSS-en selv — for eksempel med en regel om at
hvert rutenett må oppgi `grid-template-columns`, og en tekstprøve som
leser CSS-en slik kontrastprøven gjør?

Den andre veien fanger nettopp denne feilen og koster ingenting. Den
fanger ikke neste, som blir noe annet.
