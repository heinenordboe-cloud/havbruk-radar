---
dato: 2026-09-23
tittel: Designet fra overleveringen implementert, med sju avvik
status: utkast
commit: [fylles inn]
---

# Designet implementert, med sju avvik

**UTKAST.** Hva som ble bestemt står under. «Hvorfor» og «hva som ville
snudd det» skrives av Heine.

Designoverleveringen i
`docs/design/overlevering/design_handoff_kystloggen/` er implementert i
Jinja2-malene og `maler/stil.css`. Referansefilene er brukt til å SE,
aldri som kode: ingen React, ingen Tailwind, ingen CDN, ingen Google
Fonts, ingen d3, ingen topojson, ingen Leaflet.

## Bestemt: sju avvik fra overleveringen

### 1. Biomassegrafen står på områdesiden, ikke på lokalitetssiden

Fiskeridirektoratets offentlige biomassetall er per
PRODUKSJONSOMRÅDE (`docs/KILDE-BIOMASSE.md`). Mengdetallene per
lokalitet ligger i biomassedatabasen etter
akvakulturdriftsforskriften § 44, som er børssensitiv og ikke offentlig
— bekreftet av HI 09.09.2026.

Grafen er flyttet dit tallene finnes: 104 månedlige søyler per område,
2017-10 til 2026-05. På lokalitetssiden står i stedet en **ukestripe**
fra `biomasselag` — fisk til stede ja/nei — **bare for de ukene vi har
observert**. I dag er det to. Et rutenett med 52 ruter der to er fylt
ville påstått at vi vet noe om de femti andre.

Hver rute bærer `siste_rapport`, fordi kilden selv sier at
`observed_at` er hentetidspunktet vårt og at `siste_rapport` er måneden
påstanden gjelder for. MÅLT 10.09.2026 spente de 112 distinkte verdiene
fra 2005-04-30 til 2026-08-31.

### 2. Lusegrafen har ingen tiltaksgrense og ingen rustfargede søyler

Alle søyler står i `--hav5`. Brakklegging er en lav stripe under
nullinja; uker uten rapport har ingen søyle.

Grensa er **ikke samlet inn**. Den står i lakselusforskriften, varierer
med sesong (0,2 i vårperioden, 0,5 ellers) og kan settes per lokalitet
ved vedtak. Ingen av delene finnes i `lusetall`. En strek på 0,5 tegnet
av oss ville vært en påstand om regelverket; en søyle farget rust fordi
den er over en strek vi fant på, en vurdering forkledd som data.

Grafen er dessuten **søyler og ikke en kurve**, som overleveringen
tegner den. En kurve trekker en strek mellom to målinger og påstår noe
om uka imellom; lusetall er én telling per uke.

### 3. Lokalitetens kapasitet er registerets eget felt

`kapasitet`/`kapasitet_enhet` fra `akvakultur`, ikke summen av
tillatelsenes MTB. De to er ULIKE STØRRELSER: lokalitetens klarerte
kapasitet er et vedtak om hva stedet tåler, mens summen av tillatelser
er hvor mye biomasse innehaverne til sammen har lov til å ha — og en
tillatelse kan brukes på flere lokaliteter. En sum ville vært vårt
regnestykke presentert som registerets tall.

På SELSKAPSSIDEN summeres tillatelsene, men **per enhet**:
`kapasitet_enhet` varierer mellom tonn, stykk, dekar, kvadratmeter,
kubikkmeter og liter i det samme registeret. MÅLT over de 200 første
selskapene: 147 har én enhet, 50 har to, 3 har tre.

### 4. To typer historikk, aldri flettet

    OBSERVERT AV KYSTLOGGEN   changeloggen, som en loddrett tidsakse.
                              Datoen er VÅR.
    OPPGITT AV REGISTERET     journalførte overføringer, tildelinger og
                              første klarering, som en tabell med en
                              PRESISJONSKOLONNE. Datoen er KILDENS.

Ulik visuell form, egen forklaring over hver, aldri i samme liste. En
flettet tidslinje ville latt «17. juni 2024: overført til X» stå ved
siden av «14. september 2026: eier_navn endret», og en leser ville lest
begge som hendelser med dato. Den første er det; den andre er en
observasjon.

Siste post i den observerte er «Første øyeblikksbilde, \<dato\>».

**Et tredje skille kom til underveis:** en rad fra en
`verden`-partisjonert kilde er datert til UKA DEN GJELDER FOR, ikke til
dagen vi så den. Hver slik post er merket, og ordet leses av kildens
egen `partisjonering`.

### 5. Ingen spørrestrenger som bærer innhold

- **Endringsfilteret er stier:** `/endringer/<år>-<uke>/<type>/` er en
  ekte side, bygget ved bygging. Uten JavaScript er avkrysningsboksene
  lenker dit; med JavaScript filtreres tabellen på stedet og flere
  typer kan velges samtidig.
- **Siteringsboksen** bruker den faste ID-URL-en. Uke, dato og sjekksum
  står i TEKSTEN. Ingen `?uke=`.
- **Søket** er Pagefind, selvhostet. Uten JavaScript peker søkeskjemaet
  til `/sok/`, som er en veiviser til de tre flate indeksene.
- **Områdesøket** filtrerer tabellen med JavaScript på en
  `data-sok`-nøkkel generatoren bygger. Uten JavaScript vises hele
  tabellen.

Den ENE spørrestrengen som finnes er `/sok/?q=`, og den bærer et
søkeord — ikke en identitet.

### 6. Ukesbrevskjemaet er ikke bygget

«Følg med» viser bare feeds. Et skjema som poster til en adresse ingen
lytter på, er verre enn ingen: det ser ut som en vei inn.

Atom-feeder for hver lokalitet, hvert område, hvert selskap og for hele
nettstedet — 2 277 til sammen, generert av changeloggen. Også for
entiteter uten en eneste endring: en feed som mangler er en 404 der
leseren tror det er en feil hos dem.

### 7. Kartene er SVG tegnet ved bygging

Ingen fliser, ingen karttjeneste, ingen CDN, ingen JavaScript.

- **Områdegeometrien** er Fiskeridirektoratets OFFISIELLE polygoner,
  hentet fra deres ArcGIS-tjeneste (NLOD, 13 flater). Merknaden
  «områdegrenser forenklet» trengs derfor ikke.
- **Kystlinja** er Natural Earth 1:10 millioner LANDFLATER (public
  domain), klippet til ruta 3–33 °Ø / 57–72 °N med Sutherland-Hodgman.
  Flater og ikke linjer: et posisjonskart med bare streker har ingen
  innside.
- Områdene er `<a>`-lenker i SVG-en, så kartet er navigasjon også uten
  JavaScript.

Lisensene står i `docs/LISENSKJEDE.md` tabell 2 og i
`docs/design/KARTGEOMETRI.md`.

## Bestemt: tre ting overleveringen ikke hadde

- **Åtte endringstyper, ikke seks.** De to som manglet i lista er
  «Selskapsopplysning» (402 av uke 39s 812) og
  «Lokalitetsopplysning». README-en sier selv: «Datafeltene er
  foreslåtte navn; tilpass modellen.» En niende, «Sykdom (ILA/PD)»,
  kom til 22.09 — se APNE-SPORSMAL.md punkt 1 og 2.
- **Tre målte avvik i paletten**, alle for å nå WCAG AA: dempet blekk
  som heksverdi og ikke alfa, rød senket 10 % for luminansskille mot
  grønn, og en nøytral ring rundt den gule ruta.
- **Digdirs `tokens.css` er fjernet.** Overleveringen har sin egen
  typeskala, sitt eget avstandsrutenett og radius 0 overalt; etter det
  var ingenting igjen i den hentede fila som ble brukt.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
