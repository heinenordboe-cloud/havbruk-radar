# Vurdering 14.09.2026 — trenger volumvakten et andre ledd mot drift?

Foranledningen: Enhetsregisteret falt 51 622 → 51 558 → 51 524 over tre
uker. 0,19 % totalt, godt under volumvaktens terskel, og vakten sa
ingenting. Ekstrapolert blir 0,2 % i uka til 10 % på et år.

**Vurdering, ikke kode.** Konklusjonen er: ja til et andre ledd, men
IKKE det leddet spørsmålet foreslår.

---

## 1. Et «N uker på rad»-ledd ville fyrt på denne saken — og tatt feil

Dette er det avgjørende, og det bør sies først.

Fallet er **målt ekte** (se `docs/KILDE-ENHETSREGISTERET.md` punkt 5.2):
fem aksjeselskaper fikk `slettedato` hos Brreg mellom 25.08 og 10.09,
mistet næringskoden og falt ut av søket. To konkursbo kom inn. Råsvaret
krympet i takt med snapshotet, og radregnskapet går opp på raden.

**Dataene gjorde nøyaktig det de skulle.** Et selskap som slettes fra
Enhetsregisteret skal forsvinne fra vår serie også — alt annet ville vært
å bære en avviklet enhet videre i det uendelige.

En regel som sier «tre uker med fall på rad → varsle» ville altså gitt
sin aller første alarm på en uke der ingenting var galt. Og den ville
gjort det igjen hver gang bransjen har en dårlig måned.

Det er 1b-2-mønsteret i ren form: et mål som LIGNER det man vil vite
(«taper vi data?») målt med noe annet (« faller tallet?»), riktig i akkurat
de tilfellene der de to faller sammen. En vakt som fyrer på sann
bevegelse blir ignorert innen andre kvartal, og da er den borte den uka
den betyr noe. Samme argument som `--planlagt` ikke brukes på
tirsdagskjøringen.

## 2. Terskelen kan uansett ikke settes fra disse dataene

Regel 1b-4: en referanse bygges av historikk, ikke av forrige kjøring, og
den skal ikke utledes av data som allerede inneholder fenomenet.

Sammenlignbar serie for Enhetsregisteret er **fire punkter**. Alt før
24.08 er uforlignbart — næringskodelista ble utvidet 17.08 og
foretakstallet gikk 938 → 1 810.

Fire punkter gir tre differanser. Tre negative på rad har sannsynlighet
1/8 under ren støy; det er ikke et signal, og det er ikke et grunnlag for
å velge N. Å sette N = 3 fordi vi nettopp så tre, er å utlede terskelen
av hendelsen den skal fange — feilen `maks_nullstrekk` unngikk ved å
simuleres over 761 uker.

**Det finnes ingen kilde i repoet med nok historikk til å kalibrere en
drift-terskel i dag.** Lusetall og sjøtemperatur har 764 snapshots, men
de er backfillet i én omgang og sier ingenting om ukentlig drift.

## 3. Det som faktisk burde måles: er fallet FORKLART?

Spørsmålet vakten skal svare på er ikke «falt tallet» og ikke «falt det
lenge». Det er:

> **Er endringen i volum gjort rede for av changeloggen?**

For denne saken er svaret ja, og det er regnestykket som viser det:

    rader 24.08                              51 622
      − 5 foretak slettet, 28–29 felter hver   −141
      + 2 nye konkursbo                         +42
      ± 1 805 felles foretak                     +1
    rader 14.09                              51 524   ✔

`data/changelog/enhetsregisteret/` bærer nøyaktig de fem entitetene som
`borte` med 28–29 rader hver. Volumfallet og changeloggen forteller
samme historie, uavhengig av hverandre.

**Det er avstemmingen som er signalet.** Et felt som slutter å bli
parset gir et volumfall UTEN motsvarende `borte`-rader — changeloggen ser
et skjema som krympet, ikke entiteter som forsvant, og
`diff.compare()` undertrykker skjemaendringer med vilje. Nettopp derfor
er det hullet usynlig i dag, og nettopp derfor er avstemming det riktige
andre leddet.

Formen, som prinsipp og ikke som kode:

    forventet_volum = forrige_volum
                      − rader fra entiteter markert «borte»
                      + rader fra entiteter markert «ny»
                      ± netto feltendringer blant felles entiteter

    avvik = |faktisk_volum − forventet_volum|

Er avviket null, er fallet gjort rede for uansett hvor stort det er.
Er avviket stort, er noe forsvunnet uten at changeloggen så det — og DET
er alltid verdt et varsel, også når volumet steg.

## 4. Hva det ville koste, og hvorfor det ikke er gratis

Tre innvendinger, og de er ekte:

1. **Avstemmingen er ikke alltid mulig.** `utvalgsutvidelse` og
   `revidert` filtreres ut av `diff.bevegelse()` med vilje. En uke der
   utvalget utvides vil aldri stemme, og regelen må kjenne unntaket —
   ellers er den første falske alarmen innebygd.
2. **Den flytter vakten fra snapshot til changelog.** Volumvakten leser i
   dag ett tall og er robust mot at changeloggen er ødelagt. Et ledd som
   krever begge deler feiler når enten den ene eller den andre svikter,
   og «vakten sa fra fordi vakten var ødelagt» er en kjent måte å lære
   folk å ignorere den på.
3. **Den fanger ikke det spørsmålet stilte.** Ekte, langsom krymping av
   registeret over et år vil stemme perfekt hver uke, og avstemmingen vil
   tie. Det er riktig — det er bransjen som krymper, ikke dataene — men
   det er ikke det samme som å svare på «faller vi mot null».

Punkt 3 er verdt å være ærlig om: **det finnes ikke noen vakt som kan
skille «bransjen krymper» fra «vi mister data» uten å se på hva som
forsvant.** Den skillelinjen går gjennom innholdet, ikke gjennom
størrelsen, og enhver ren talltest vil bomme på den ene eller den andre.

## 5. Anbefaling

**Ikke bygg et «N uker fall på rad»-ledd.** Det ville fyrt på denne saken
og tatt feil, terskelen kan ikke kalibreres fra tre differanser, og
kostnaden er en vakt folk slutter å lese.

**Bygg avstemming mot changeloggen når det trengs** — men ikke ennå.
Formen i punkt 3 er riktig, og den er verdt å skrive ned nå slik at
neste person ikke starter med trenddeteksjon. Men den bør vente til det
finnes en sak den ville fanget: et volumfall som changeloggen IKKE
forklarer. Det har ikke skjedd.

**Gjør i mellomtiden det billige.** To ting som ikke er en ny vakt:

* ~~Skriv `antall_filtrert` til kjøringsloggen eller arkivet~~ —
  **GJORT 14.09.2026.** Arkivkroppen bærer nå en `meta`-post med
  antallet, samme mønster som `eierskap` sitt `personer_fjernet`. En uke
  der foretak ble omklassifisert til ENK kan nå skilles fra en uke der de
  ble slettet. Tiltaket virker bare framover: arkivfilene til og med
  14.09 har ingen slik post og får den aldri. Se
  `docs/KILDE-ENHETSREGISTERET.md` punkt 5.2.
* **Rapporter volumendring per uke i kjøringsloggen**, som et tall
  mennesker leser, ikke som en terskel maskiner fyrer på.
  Commit-meldingen leses på telefonen hver mandag; «enhetsregisteret
  −34 (−0,07 %)» der koster ingenting og gjør at et fall over et halvår
  blir sett av en person lenge før noen vakt ville reagert.

Det siste er det egentlige svaret på spørsmålet. Langsom drift oppdages
av at noen ser den samme linjen femti uker på rad — ikke av en terskel
som per konstruksjon er satt der drift ikke når.

## 6. Hva som ville snudd det

At et volumfall dukker opp som changeloggen ikke gjør rede for. Da er
avstemmingen i punkt 3 ikke lenger en hypotese, og den skal bygges med
det tilfellet som testcase.

Eller: at Enhetsregisteret faller tolv uker på rad med samme fortegn. Da
er tre differanser blitt til tolv, N kan settes empirisk, og spørsmålet
om drift er et annet spørsmål enn det var i dag.
