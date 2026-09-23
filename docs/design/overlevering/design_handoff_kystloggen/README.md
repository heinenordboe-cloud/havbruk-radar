# Overlevering: Kystloggen (kystloggen.no)

## Oversikt
Kystloggen er et uavhengig, åpent arkiv over offentlige data om norsk havbruk. Registrene viser bare nåtilstanden. Kystloggen lagrer hvert ukentlige øyeblikksbilde og viser **endringene**. Bevegelsen er produktet. Trafikklysfarge er én endringstype blant flere; designet må tåle at trafikklyssystemet erstattes.

Sidetyper: forside, `/lokalitet/<nr>/`, `/produksjonsomrade/<nr>/`, `/selskap/<orgnr>/`, `/endringer/<år>-<uke>/`, `/om/`.

## Om designfilene
Filene i `design/` er **designreferanser laget i HTML**, ikke produksjonskode. De bruker inline-stiler og en liten JS-runtime for å kunne vises i designverktøyet. Oppgaven er å gjenskape dem som **statisk HTML fra Jinja2 med egen CSS**:
- Ingen React, ingen Tailwind, ingen CDN, ingen Google Fonts.
- Newsreader, IBM Plex Sans og IBM Plex Mono hostes selv (alle er OFL). Bruk woff2 og `font-display: swap`.
- Kartene i referansen bruker d3, topojson og Leaflet fra CDN. I produksjonen må kartet enten rendres til SVG på byggetidspunktet (anbefalt) eller bruke selvhostede biblioteker.

## Fidelity
**Hi-fi.** Farger, typografi, avstander og komponenter er endelige. **Alle tall, datoer og mange navn er plassholdere** (se egen liste). Hent alt fra dataene, og kopier ingenting fra designet.

Plassholdermerking i designet:
- Stiplet rustfarget understrek = tall eller dato som hentes fra data.
- `[hakeparentes]` = tekst som hentes fra data (kommune, selskap, orgnr).
- Den rustfargede stripen «Designreferanse» øverst skal **ikke** med i produksjonen.

---

## Harde krav
1. **Farge bærer aldri mening alene.** Ved hver farge står teksten: `rød`, `gul`, `grønn` eller `ikke oppgitt`.
2. **Alt innhold fungerer uten JavaScript.** JS er bare forbedring (se tabellen under).
3. **Tabeller er ekte `<table>`** med `<thead>` og `<th scope="col">`. Radhoder får `<th scope="row">` der det er naturlig (registerfeltene).
4. **Monospace brukes bare til tallverdier i tabellkolonner** (nummer, mengder, ISO-datoer). Aldri til etiketter, overskrifter, datoer i løpende tekst eller forklaringer.
5. **Datoer:** i løpende tekst «16. september 2026». I tabeller brukes ISO («2026-09-16»). Uker skrives «uke 38, 2026». ISO-uke (`2026-W38`) står bare i filer, URL-er og `title`/hover.
6. **Kolonnen heter «Observert», ikke «Endret».** Vi vet når vi så endringen, ikke når registeret gjorde den.
7. **Tetthet.** Tabellrader er 8–10 px vertikal padding. Ingen kort med skygge.

---

## Designtokens

### Farger
| Token | Hex | Bruk |
|---|---|---|
| `--hav9` | `#06161d` | Mørk bakgrunn: hero, header på undersider, kystseksjonen, bunntekst |
| `--hav8` | `#0b2430` | Primærknapper, tekst (= `--ink`) |
| `--hav7` | `#123241` | Hover på mørk flate |
| `--hav5` | `#2f5f74` | Lusesøyler under tiltaksgrensen |
| `--hav3` | `#7ba0b1` | Dempet tekst på mørk flate (brødsmuler, etiketter) |
| — | `#9fb9c4` | Sekundærtekst på mørk flate |
| — | `#c9d6dc` | Tegnforklaringer på mørk flate |
| `--papir` | `#e7dbd0` | Hovedbakgrunn |
| `--papir2` | `#efe6dd` | Innfelt flate: siteringsboks, arkivlinje, skjemafelt |
| `--papir3` | `#d8c9bb` | Linjer på papir |
| `--rust` | `#aa3e04` | **Eneste aksent**: lenker, seksjonsetiketter, ordmerkelinjal, hover, over tiltaksgrense |
| — | `#d9804a` | Rust på mørk flate (etiketter og understrek) |
| `--ink` | `#0b2430` | Tekst på papir; dempes med alfa 0.6–0.75 |

**Datafarger (trafikklys).** Disse er DATA og brukes aldri på knapper, varsler eller pynt.
| Verdi | Hex | Form |
|---|---|---|
| rød | `#93211c` | helfylt |
| gul | `#c8992f` | helfylt |
| grønn | `#2f6b4f` | helfylt |
| ikke oppgitt | skravur `repeating-linear-gradient(45deg, #6f8a95 0 1.3px, transparent 1.3px 4.5px)` på mørk flate; `rgba(11,36,48,.55)` på papir | skravert, **samme form på kart og i ruter** |
| utledet (områdeside) | fyll i fargen med alfa ≈ .3 + 2 px innvendig kant i full farge | skiller «utledet av kapittelplassering» fra «ordlyd i forskriften» |

Linjer: `rgba(11,36,48,.4)` under tabellhode, `.1` mellom rader, `.18–.3` seksjonsskiller. På mørk flate brukes `rgba(231,219,208,.1–.35)`.

### Typografi
| Rolle | Font | Str./linje | Vekt | Merknad |
|---|---|---|---|---|
| Ordmerke hero | Newsreader | clamp(50px, 7vw, 104px) / .86 | 300 | letter-spacing −.035em, rustlinjal under |
| Ordmerke nav | Newsreader | 19px / 1 | 400 | 2 px rust underlinje |
| H1 underside | Newsreader | clamp(40px, 5vw, 76px) / .95 | 300 | −.03em |
| H1 lokalitet | Newsreader | clamp(46px, 6vw, 88px) / .92 | 300 | |
| H2 seksjon | Newsreader | clamp(28px, 3vw, 46px) / 1.05–1.1 | 300–400 | −.02em |
| H2 blokk | Newsreader | 26–30px / 1.1 | 400 | |
| Ukessammendrag | Newsreader | clamp(22px, 2.1vw, 29px) / 1.3 | 400 | maks 34ch |
| Seksjonsetikett | IBM Plex Sans | 15px / 1 | 500 | rust, vanlig setning, aldri versaler |
| Brødtekst | IBM Plex Sans | 15–17px / 1.55–1.65 | 400 | |
| Etikett / metadata | IBM Plex Sans | 13–13.5px / 1.3–1.5 | 400 | dempet |
| Tabellhode | IBM Plex Sans | 12.5px / 1.3 | 500 | `rgba(11,36,48,.6)`, vanlig setning |
| Tabellcelle tekst | IBM Plex Sans | 14–14.5px / 1.3 | 400/500 | lokalitetsnavn 500 |
| Tabellcelle tall | IBM Plex Mono | 13.5px / 1.3 | 400 | høyrestilt, `tabular-nums` |
| Nøkkeltall | Newsreader | clamp(36px, 3.6vw, 52px) / 1 | 300 | etikett i Newsreader 18px |

`font-variant-numeric: tabular-nums` settes på alle tabeller.

### Avstander og layout
- Innholdsbredde: `max-width: 1400px`, sidemarg `clamp(20px, 4vw, 56px)`.
- Seksjonspadding: `clamp(36px, 4vw, 56px)` til `clamp(44px, 5vw, 72px)` vertikalt.
- Skala i bruk: 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 40, 44, 56, 64, 72.
- Hjørner: 0 overalt. Ingen skygger, bortsett fra kartets hover-tooltip.
- Rammer tegnes som `box-shadow: inset 0 0 0 1px …` eller `border`.

### Brytpunkter
Designet er flytende (auto-fit-grid og flex-wrap). I CSS kan dette uttrykkes med:
- `≥ 1100px`: to kolonner i kystseksjonen (kart | tabell), lokalitetsheader (fakta | kart).
- `640–1099px`: én kolonne, fakta-`dl` i to kolonner.
- `< 640px`: én kolonne. Brede tabeller (endringer, lokaliteter) scroller horisontalt i en `overflow-x:auto`-beholder med `min-width` 620–820px. Anbefaling: under 640px kan endringstabellen bytte til stablede rader (`tr{display:grid}`) med «Observert» og «Endring» øverst. Tabellsemantikken beholdes.
- Hero-høyde: `clamp(460px, 60vh, 560px)`, så «Denne uka» starter over bretten på 1440×900.

---

## Sidene

### Forsiden `/`
Rekkefølge: **hero → denne uka → arkivtall → kysten → følg med → bunntekst**.

1. **Hero.** Fotografi 1a (Wolfgang Hasselmann/Unsplash), `object-position: center 42%` (ikke forhåndsbeskjær). Mørk gradient bare nederst: 0 % → .45, 22–42 % → 0, 70 % → .8, 100 % → .96. Nav øverst. Nederst står tagline, ordmerke med linjal, setningen «Registrene viser nå. Vi tar vare på før.» og søkeskjemaet `<form action="/sok/" method="get">`. Ingen tegnede måker. Lysskimmeret (34 s) er valgfritt og skal respektere `prefers-reduced-motion`.
2. **Denne uka i registrene.** Den ligger rett under heroen.
   - Hode: etiketten «Denne uka i registrene», uke og datoer, lenke til forrige uke.
   - Sammendrag: 1–3 setninger i Newsreader, generert fra ukas endringer. For trafikklysuker vises også **tidslinjen med tre punkter** (Fastsatt → Kunngjort → Observert her), plassert proporsjonalt med dager og med antall dager mellom.
   - Endringstyper: seks etiketter (Trafikklys, Biomasse, Eierskap, Tillatelse, Ny lokalitet, Nedlagt lokalitet) med antall. Typer med 0 er dempet, men **vises alltid**. Hver lenker til `/endringer/<uke>/?type=…`.
   - Tabell med kolonnene Observert (ISO-dato, mono) | Lokalitet (lenke) | Kommune | Produksjonsområde | Endring (typeord + fra → til; farge og tekst for trafikklys). Maks 8 rader, deretter «Alle N endringer i uke 38 →».
   - **Tilstander** (se prop `uke` i referansen): *trafikklys* (med tidslinje), *eierskap* (uten tidslinje, med forklaring av feltet), *stille uke* (tom tabell med én forklarende rad, alle typer 0).
3. **Arkivtall.** Én linje: lokaliteter · selskaper · N ukentlige øyeblikksbilder siden [dato]. Under står «Siste øyeblikksbilde: [dato] · sjekksum [a3f9…c21e] · Slik samler vi inn» med lenke til `/om/#metode`.
4. **Kysten.** Mørk seksjon. Kart til venstre, tabellen over de 13 områdene til høyre (Nr. | Område + historietekst | 2018–2026-stripe | Lokaliteter). Tegnforklaringen viser rød, gul, grønn og skravert «ikke oppgitt i forskriften». Dekningsnoten står under.
5. **Følg med.** Feed-URL-er i en liste. Ukesbrev-skjemaet `<form method="post" action="/ukesbrev/">` har ett felt og én knapp.
6. **Bunntekst** (felles): kilder med lisens, metode, siteringsveiledning, kildekode, kontakt, Heine Valø Nordbøe. Nederst én proveniens-linje.

### Lokalitetsside `/lokalitet/<nr>/` (viktigst)
- **Header** (mørk):
  - brødsmule (Kystloggen / område / Lokalitet nr)
  - H1-navn med registerets versaler omgjort til tittelform (skriv «Oterneset», behold originalen i registerfelt-tabellen)
  - linje med nr · status · art
  - `dl` med Kommune, Produksjonsområde (lenke + farge og tekst), Selskap (lenke + siden-dato) og Tillatelser (antall + samlet MTB)
  - knapper for feed og siter
  - posisjonskart med koordinater i `figcaption`
- **Lakselus**:
  - søylediagram per uke fra 2012; uker uten rapport er tomrom, ikke null
  - tiltaksgrensen er en stiplet rustlinje; søyler over grensen er rust, under er `--hav5`, og brakklegging vises som en lav grå stripe
  - Tegnforklaring i `figcaption`.
  - **Tabellen med tallene** ligger i `<details>` rett under, med de siste ukene synlig og lenke til CSV/JSON.
- **Biomasse**: graf der tall finnes (samme grammatikk: månedlige søyler i `--hav5`). **Mangler data**: skravert boks med forklaring (vist i designet).
- **Endringer vi har sett**: loddrett tidslinje (`<ol>`). Hver post har dato (ISO-uke i `title`), feltnavn og fra → til. Nyeste øverst, og nyeste punkt i rust. Siste post er «Første øyeblikksbilde».
- **Tillatelser**: tabell (Tillatelse | Formål | Tonn MTB | Tildelt).
- **Registerfeltene**: tabell (Felt `th[scope=row]` | Verdi | Sist endret).
- **Siteringsboks**: ferdig referanse med URL med `?uke=` og kopier-knapp.

### Områdeside `/produksjonsomrade/<nr>/`
- Header med navn, antall lokaliteter og selskaper, og feed.
- **Trafikklys 2018–2026** stort: én blokk per runde med år, fargeord, belegg («fargeordet står i forskriften» / «utledet av kapittelplassering») og lenke til forskriftsrunden. Heltrukket fyll betyr ordlyd, tonet fyll med kant betyr utledet, skravur betyr ikke oppgitt.
- **Lokalitetene i området**: søkefelt (`GET ?q=`, filtreres også live med JS) og tabell (Nr. | Lokalitet | Kommune | Selskap | Status | Tonn MTB | Sist endret), deretter «Viser X av N · Vis alle · CSV».
- **Endringer i området**: siste 12 uker, kompakt tabell.

### Selskapsside `/selskap/<orgnr>/`
- Header med navn, orgnr og fire nøkkeltall (lokaliteter nå, tillatelser nå, samlet MTB, i arkivet siden), feed og lenke til Enhetsregisteret.
- Tabellene Lokaliteter og Tillatelser, begge med «Innehaver siden».
- **Eierskap over tid**: tidslinje med «Kom til» og «Gikk ut».

### Endringsside `/endringer/<år>-<uke>/`
- Permanent side per uke med forrige/neste og permalenke.
- Sammendrag i Newsreader.
- Filter på endringstype som `<form method="get">` med avkrysningsbokser `name="type"`. Uten JS sendes skjemaet; med JS filtreres tabellen direkte.
- Komplett tabell (Observert | Lokalitet | Kommune | Produksjonsområde | Type | Endring) med `<caption>` «Viser X av N endringer».
- Nedlasting: CSV, JSON og feed. Siteringsboks.

### Om `/om/`
Innholdsliste til venstre og brødtekst maks ~760px. Seksjoner: Hva dette er · Kildene (tabell med lisens) · Innsamling og metode · Dekning og begrensninger · Hvem som står bak · Slik siterer du.

---

## Komponenter

Datafeltene er foreslåtte navn; tilpass modellen.

| Komponent | Datafelt | Tom | Én verdi | Mange | Mangler data |
|---|---|---|---|---|---|
| **Nav** | — | — | — | lenkene brytes til ny linje under 640px | — |
| **Ordmerke med linjal** | — | — | — | — | — |
| **Søk** | `q` | placeholder-tekst | — | resultatside (ikke tegnet) | — |
| **Ukessammendrag** | `uke`, `endringer[]`, `forskrift{fastsatt,kunngjort}` | «Ingen endringer i registrene denne uka…» | setning for én type | 1–3 setninger, største type først | uten tidslinje hvis forskriftsdatoer mangler |
| **Tidslinje, tre punkter** | `fastsatt`, `kunngjort`, `observert_fra/til` | skjules | — | — | punkter uten dato utelates, dager beregnes ikke |
| **Endringstype-etiketter** | `type`, `antall` | alle seks vises med 0, dempet | én aktiv | flere aktive | — |
| **Endringstabell** | `observert`, `lokalitet{nr,navn}`, `kommune`, `po{nr,navn}`, `type`, `fra`, `til` | én rad med forklaring | 1 rad | maks 8 på forsiden; alle på ukesiden | tom celle = «—», aldri 0 |
| **Endringsverdi** | `fra`, `til`, `type` | — | trafikklys: firkant + ord; andre: bare tekst | — | «ikke i registeret» |
| **Arkivlinje** | `antall_lokaliteter`, `antall_selskaper`, `antall_snapshots`, `første_snapshot`, `siste_snapshot`, `sjekksum` | — | — | — | — |
| **Områdetabell** | `nr`, `navn`, `farger[2018..2026]`, `antall_lokaliteter` | — | — | 13 rader | runde uten farge = skravert + «ikke oppgitt» |
| **Femårsstripe** | `farger[]` + `title` per rute | — | — | 5 ruter 18×14, gap 3 | skravert |
| **Historietekst** | avledet av `farger[]` | «ikke oppgitt i noen runde» | «grønn i alle fem runder» | «gul → rød → gul» | — |
| **Kystkart** | `po[].farge_2026`, `po[].antall` | — | — | — | skravert bånd |
| **Faktaliste (`dl`)** | se side | — | — | — | «—» |
| **Loddrett tidslinje** | `dato`, `uke`, `felt`, `fra`, `til` | «Ingen endringer siden første øyeblikksbilde» | 1 post + «Første øyeblikksbilde» | nyeste øverst, paginer etter 25 | — |
| **Lusegraf + tabell** | `uke`, `år`, `hunnlus`, `brakklagt`, `tiltaksgrense` | «Ingen lusetall rapportert» | — | 2012→ | ingen rapport = tomrom; tabell: «—» + «ingen rapport» |
| **Biomasse** | `måned`, `tonn` | skravert forklaringsboks (tegnet) | — | månedssøyler | skravert boks |
| **Datatabell** | varierer | «Ingen rader» | — | `overflow-x:auto` under 640px | «—» |
| **Siteringsboks** | `tittel`, `uke`, `snapshot_dato`, `url` | — | — | — | — |
| **Fargerunder (område)** | `år`, `farge`, `belegg: ordlyd\|utledet\|ikke_oppgitt`, `kilde_url` | — | — | 5 runder, flere legges til | skravert |
| **Feedliste** | `url` | — | — | — | — |
| **Ukesbrev-skjema** | `epost` | — | — | — | feilmelding under feltet (ikke tegnet): sans 13px, rust |
| **Proveniens-linje** | `snapshot_uke`, `hentet_tidspunkt` | — | — | — | — |

Interaksjoner:
- Lenker har rust ved hover.
- Rader i tabeller får `rgba(11,36,48,.04)` ved hover.
- Knapper: `--hav8` som hviletilstand, `--rust` ved hover.
- Fokus: `outline: 2px solid #aa3e04; outline-offset: 2px`.

---

## JavaScript: hva krever det, og hva vises uten

| Element | Med JS | Uten JS |
|---|---|---|
| Kystkart | hover-tooltip (navn, farge, antall), markering, klikk til område | statisk SVG rendret ved bygg; områdene er `<a>`-lenker. Tabellen ved siden av har alt innholdet |
| Posisjonskart | zoom og panorering | statisk SVG/PNG med markør og koordinater i `figcaption` |
| Lusegraf | hover med ukesverdi | SVG rendret ved bygg + tabell i `<details>` |
| Kopier-knapp (sitering) | kopierer og viser «Kopiert» | teksten er markerbar, knappen skjules (`<noscript>`-stil eller `hidden` til JS er lastet) |
| Filter på endringsside | live filtrering | `<form method="get">`; serveren/bygget lager `?type=`-varianter, eller alle rader vises |
| Søk i område | live filtrering | `GET ?q=` til søkesiden |
| Hero-lysskimmer | CSS-animasjon | — (ikke JS) |

---

## Plassholdere som IKKE skal inn i koden
Alt nedenfor kommer fra designet og skal hentes fra data:

**Forsiden**
- Uke 38, «14.–20. september 2026»
- Sammendrag: 15, 8, 7, 26 dager. Tidslinje: 20.08, 11.09, 15.–16.09, 22 dager
- Typeantall: 15 og 0
- Rader: datoene 2026-09-15/16, [kommune], [område]. Lokalitetsnavnene er ekte fra uke 38, men skal likevel hentes
- «Alle 15 endringer i uke 38»
- Eierskapsscenario: [Selskap A/B AS], [LOKALITET A–C], 3
- Arkivtall: 1 782, 481, 214, «mars 2022», «16. september 2026», sjekksum a3f9…c21e
- Antall per område: 12, 48, 88, 141, 96, 118, 84, 132, 71, 62, 58, 32, 27
- Dekning: 969 av 1 782
- Proveniens: «uke 38, 2026, hentet 16. september 2026 kl. 04.09»

**Lokalitet**
- [i drift], [Laks, regnbueørret], [Kommune], [Selskap AS]
- 17. juni 2024; 3 tillatelser; 3 120 t
- Koordinater 60°58,4′ N, 5°02,0′ Ø
- Alle loggposter (datoer, 2 340 → 3 120, [Selskap A AS])
- Lusetabellen (0,21 …); tiltaksgrense 0,5
- Tillatelsesnr. H-AV-0012/0147/0221 med 1 560/780/780 og datoer
- Alle registerfelt-verdier og datoer
- Siteringsdato

**Område**
- 141 lokaliteter, 63 selskaper
- Belegg per runde
- Forskriftsdatoene 2017-12-19, 2020-02-04, 2022-06-15, 2024-06-20, 2026-08-20
- Alle tabellrader ([nr], [LOKALITET], MTB, datoer), «Viser 8 av 141», 12 uker

**Selskap**
- [Selskap AS], [9xx xxx xxx], 7, 12, 9 360, 14. mars 2022
- Alle tabellrader og tidslinjeposter

**Endringer**
- Uke 37/38/39, datoer, 15 og 0, «Viser X av 15»

**Om**
- 04.00, 14. mars 2022, 2012, 969/1 782
- [bruker] i GitHub-URL, [e-postadresse]

Trafikklysfargene per område og år (PO1, 3, 4, 5, 12, 13) er oppgitt av oppdragsgiver. De skal likevel leses fra forskriftsdataene.

**Må verifiseres:** kildenes lisens (NLOD 2.0 for Fiskeridirektoratet og BarentsWatch). Områdegrensene på kartet er forenklet etter breddegrad, så bruk de offisielle polygonene.

---

## Ressurser
- Herofoto: «Snowy mountains overlook a dark choppy ocean under cloudy skies», Wolfgang Hasselmann, Unsplash-lisens. https://unsplash.com/photos/cbaS3DXXCl4. Last det ned og host det selv i flere bredder (`srcset`: 800/1600/2400).
- Kystlinje: Natural Earth 1:110 m (world-atlas), public domain.
- Fonter: Newsreader (Production Type, OFL), IBM Plex Sans og Mono (OFL).
- Ingen ikoner. Piler er tekst («→», «↗»).

## Filer (i `design/`)
- `Kystloggen - Forsiden v2.dc.html`: forsiden. Prop `uke` viser tilstandene trafikklys, eierskap og stille.
- `Kystloggen - Lokalitet v2.dc.html`
- `Kystloggen - Område.dc.html`
- `Kystloggen - Selskap.dc.html`
- `Kystloggen - Endringer uke.dc.html`
- `Kystloggen - Om.dc.html`
- `KL Topp.dc.html`, `KL Fot.dc.html`: felles nav og bunntekst
- `kystloggen-viz.js`: kart og graf som referanse (logikk for projeksjon, bånd og etiketter)
- `Visning v2.dc.html`: alle sider på 1440 og 390
