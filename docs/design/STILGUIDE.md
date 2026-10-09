# Stilguide

Gjeldende fra designrunden 08.10.2026. Briefen (`BRIEF.md`) er bindende
og går foran denne fila; denne fila sier hvordan briefen er gjort til
tokens og komponenter, når hver av dem brukes, og hvorfor.

Tre steder holder stilen, og de har hver sin jobb:

| Hvor | Hva som står der |
|---|---|
| `maler/stil.css` | Verdiene, og ved hver verdi det som er MÅLT: kontrast, dE, piksler. Avsnittene er nummerert 1–19, og guiden viser til dem. |
| Denne fila | Hvilken komponent som brukes til hva, og hva som bevisst ikke brukes. |
| Prøvene | At det fortsatt stemmer: `test_kontrast.py`, `test_nettsted.py`, `test_smalskjerm.py`, porten. |

Står en verdi her og i stilarket, er det stilarket som gjelder. Guiden
gjentar bare de verdiene som trengs for å forstå et valg.

## Sju prinsipper

1. **Papir, blekk og rust.** Papiret er flata, blekket er teksten, og
   rusten er den eneste aksenten — og den er bare skrift eller strek,
   aldri flate. Havet (mørk flate) brukes to steder: herofotografiet og
   bunnteksten.
2. **Data har farge, pynt har ikke.** Rød, gul og grønn finnes bare som
   trafikklys, og bare som fylt firkant. Søylene i grafene er én farge.
   Ingenting dekorativt er farget.
3. **Hårlinjer og luft skiller, ikke bokser.** En seksjon er en
   blekkstrek over en overskrift, en rad er en hårlinje under. En ramme
   betyr én ting: dette kan du fylle ut eller kopiere (søkefeltet,
   siteringsteksten).
4. **Én venstrekant.** Brødsmule, tittel, ingress, tabell og figur
   starter på samme linje. Tekst har et lesemål; tabeller og figurer
   har spalta.
5. **Tre nivåer under H1.** Seksjon (H2, serif), blokk (H3, serif,
   mindre) og etikett (sans, liten, rust). En fjerde størrelse som ligner
   en av dem, er en feil.
6. **Lenker ser ut som lenker der de er lenker.** I løpende tekst rust
   med strek. I tabeller og lister blekk med svak strek, så en side med
   80 navn ikke blir 80 oransje streker.
7. **Hel uten JavaScript, og tastaturet når alt.** Skriptet legger aldri
   til en verdi. Alt som kan holdes over med musa, kan nås med Tab eller
   piltastene, og fokus er synlig overalt.

## Tokens

### Farger (`stil.css` avsnitt 1)

| Token | Verdi | Rolle |
|---|---|---|
| `--papir` | `#f4eee6` | Flata alt står på, også toppen |
| `--papir2` | `#ebe3d8` | Tonet flate: brikke, kodebit |
| `--papir3` | `#d6cabc` | Hårlinjer mellom rader |
| `--felt` | `#fbf8f3` | Det man fyller ut eller kopierer |
| `--rad-pa` | `#efe8df` | Tabellrad under peker |
| `--ink` | `#0b2430` | All tekst, seksjonsstreken |
| `--ink-dempet` | `#566266` | Metalinjer, noter, tabellhode — 5,46:1 |
| `--ink-ring` | `#757c7d` | Ringen rundt en fargerute — 3,69:1 |
| `--rust` | `#aa3e04` | Lenker, etiketter, fokus, aksentstrek — 5,36:1 |
| `--rust-moerk` | `#8f390d` | Lenke under peker |
| `--hav9` | `#06161d` | Herotoning og bunntekst |
| `--hav5` | `#2f5f74` | Søylene i lus- og biomassegrafen |
| `--lys-rod` / `--lys-gul` / `--lys-gronn` | | Trafikklyset, og ingenting annet |
| `--kart-*` | | Land, hav, kyst og gradnett i kartene |

Rollenavnene `--farge-*` er alias for de samme verdiene. De står fordi
`tests/test_kontrast.py` måler parene med dem; stilarket selv bruker de
korte navnene.

**Papiret ble lysere 08.10.2026**, fra `#e7dbd0` til `#f4eee6`. Den
gamle flata spiste kontrasten i all tekst som sto på den, og tabellene
så ut som de sto på kartong.

### Skrift (`stil.css` avsnitt 2)

| Familie | Brukes til | Aldri til |
|---|---|---|
| Newsreader | H1–H3, ingressen, ordmerket, nøkkeltallene | Brødtekst, tabeller |
| IBM Plex Sans | Brødtekst, etiketter, tabeller, menyen | — |
| IBM Plex Mono | Tallkolonner i tabeller og kode | Løpende tekst |

Én skala, sju trinn. Til 08.10.2026 var det seksten størrelser, flere av
dem 0,5 px fra hverandre.

| Token | Størrelse | Brukes til |
|---|---|---|
| `--tekst-xs` | 13 px | Etiketter, tabellhode, noter, kreditering |
| `--tekst-s` | 14 px | Tabellceller, metalinjer, verktøylinja |
| `--tekst-m` | 16 px | Brødtekst |
| `--tekst-ingress` | 19–24 px | Oppsummeringen øverst på en side |
| `--tekst-h3` | 20 px | Blokktittel |
| `--tekst-h2` | 24–32 px | Seksjonstittel |
| `--tekst-h1` | 34–56 px | Sidetittel |

`--tekst-tall` (28–40 px) er nøkkeltallene, og heroens motto har sin
egen størrelse. Rotstørrelsen settes ikke: 16 px er leserens.

Registerets versaler vises ikke som versaler. Navnet står i menneskelig
form («Villa Smolt AS», «Herøy, Møre og Romsdal»), og den rå verdien
står uendret i registerfeltene, siteringen og nedlastingene — se
`visningsord.selskapsnavn()` og `kommunenavn()`.

### Avstand og mål (`stil.css` avsnitt 2)

Et 4 px-rutenett i ni trinn: `--rom-4`, `-8`, `-12`, `-16`, `-24`,
`-32`, `-48`, `-64`, `-96`. Mellom seksjoner `--rom-seksjon`
(48–72 px), som klemmes på smal skjerm.

| Token | Verdi | Hva |
|---|---|---|
| `--maal-tekst` | 66ch | Løpende tekst |
| `--maal-note` | 78ch | Noter i liten skrift |
| `--maal-tittel` | 20em | Overskrifter |
| `--maal-om` | 44rem | Brødteksten på om-siden |
| `--maal-side` | 1400px | Hele siden |
| `--marg-side` | 16–56 px | Margen til skjermkanten |

Hjørnene er rette overalt.

## Oppsett

**`.ark`** er siden: høyst `--maal-side` bred, sentrert, med
`--marg-side` på hver side. En `.ark` inni en `.ark` — eller inni en
`main` uten `.fullbredde` — legger ikke på mer marg. Den regelen er det
som holder venstrekanten lik, og den står i stilarket så ingen mal må
huske den.

**`main.fullbredde`** brukes av sider med seksjoner som går kant til
kant: forsiden, lokalitet, selskap, område, ukene og endringslista.
Hver seksjon setter da sin egen `.ark`.

**`.seksjon`** gir luft over. Første seksjon i `main` får mindre, fordi
sidehodet har sin egen luft under seg.

**Lokalitetssiden** har to spalter fra 64rem: tidslinja til venstre,
tilstanden (`.lok-tilstand`) i en smal høyrespalte som følger med
nedover. Høyrespalta er kort med vilje — står den lenger enn venstre,
blir det tomrom ved siden av.

**`.med-marg`** er det samme mønsteret gjort felles (09.10.2026): to
barn, `.med-marg-hoved` og `.marg`, i to spalter fra 64rem. Høyrespalta
er `.marg-blokk`-er — blekkstrek, etikett, innhold — og innholdet er
ett av tre: nøkkeltall (`dl.fakta`), en fordeling (`.fordeling`) eller
et minikart (`.minikart`). Byggeklossene står i `maler/marg.html.j2`.
Lesespalta blir ikke bredere; tomrommet på brede skjermer fylles med
tall som hører til siden, aldri med pynt og aldri med det som står til
venstre. Under 64rem kommer høyrespalta etter hovedinnholdet.

| Side | Hovedspalta | Høyrespalta |
|---|---|---|
| Lokalitetsindeksen | tittel, søk, lista | minikart med alle, per område, per art |

**Minikartet** er hele kysten på 320 px: land, de tretten områdene og
punktene som én `path` (`kart.minikart()`). Det har ikke `data-kart`,
fordi det ikke bruker Kartverkets kontur.

## Komponenter

### Toppen (avsnitt 3)

Menylinja (`.toppbar`) står på papiret med en hårlinje under. Ordmerket
til venstre, fem punkter til høyre; under 640 px på hver sin linje.
Ingen hamburger. Siden man står på har `aria-current` og en rust strek.

Til 08.10.2026 var toppen et mørkt bånd over hele sidehodet. Det veide
mer enn innholdet og gjorde hver side til to.

### Sidehodet (avsnitt 3)

I denne rekkefølgen, og ingen av dem er obligatoriske utenom H1:

| Del | Klasse | Når |
|---|---|---|
| Brødsmule | `.sti` | Alle sider unntatt forsiden |
| Tittel | `h1` | Alltid, én |
| Metalinje | `.lok-undertittel` | Type, nummer, dato — i dempet sans |
| Ingress | `.lok-sammendrag`, `.uke-ingress` | Når siden har en oppsummeringssetning bygget av data |
| Fakta | `.uke-fakta` | Korte setninger med strek foran, ikke punkter |
| Nøkkeltall | `.nokkeltall` | 2–5 tall med etikett, uten boks, hårlinje over |
| Verktøylinje | `.handlinger` | Følg, siter, last ned |
| Forbehold om siden | `.sidehode-note` | Når hele siden har et forbehold |

### Verktøylinja (avsnitt 3)

`<ul class="handlinger">` med `<a class="handling">` i. Lenker i blekk
med en svak strek, på én linje. En nedlasting er `.handling--last` og
får en pil foran.

**Ikke knapper.** Følg, siter og last ned fører et sted — til en feed,
et anker, en fil — og det er lenker. Til 08.10.2026 sto de som
omrissknapper, og det så ut som en mal.

### Knappen (avsnitt 5)

`.knapp`: mørk flate, lys skrift, rette hjørner. **Bare for en handling
på siden**: søk, kopier. Det finnes én knappestil; omrissknappen er
fjernet.

### Seksjonshodet og etiketten (avsnitt 4)

`.seksjonshode` er en blekkstrek over en etikett og en H2, med en
eventuell «Se alle»-lenke til høyre. `.etikett` er 13 px halvfet rust
sans, aldri versaler — den sier hva slags ting som kommer, H2 sier hva
den er.

`.videre` er «Se alle … →»: blekk med en tykk rust strek. Den sier alltid
hvor den fører.

### Tabeller (avsnitt 7)

- **Tittelen over** (`<p class="tabelltittel" id="…">`, koblet med
  `aria-labelledby`), **noten under** (`.tabellnote`). Til 08.10.2026
  hang tittelen etter tabellen.
- Hårlinjer mellom radene, ingen loddrette streker, ingen ramme. Raden
  under peker får `--rad-pa`.
- Tall høyrestilt i mono. Tabellhodet fester seg til vinduet over 62rem.
- `.tabellramme` med `role="region"` og `tabindex="0"`: en bred tabell
  ruller i sin egen boks, aldri dokumentet. `.tabellramme--ruller` når
  den skal rulle også på bred skjerm.
- Navn i tabeller er lenker i blekk, ikke rust.

**Under 640 px blir hver rad et kort** (`.tabell--kort`): første celle
er korttittelen, og hver verdi får kolonnenavnet til venstre fra
`data-label`. Etiketten flyter i cella, så en etikett på to linjer gjør
cella høyere i stedet for å legge seg over neste rad. Tabeller som
leses langs begge aksene (krysstabellen på `/endringer/`) blir ikke
kort; de står i `nettsted.UTEN_KORT`.

**Endringsloggene som kort** er tre linjer: hva (halvfet), hvordan, og en
dempet metalinje med dato · sted · område · type. En celle uten verdi
står ikke i metalinja.

### Utvidbare deler (avsnitt 8)

Én form for alt som står bak et klikk: `.tallboks`, `.egen-del`,
`.feedmonstre` og `.forbehold`. En hårlinje over og en summary med en
strek-pil som vris. Summaryen sier hva som ligger bak — «Vis alle 83
endringene», ikke «Mer».

**Forbehold slettes aldri.** De kan flyttes ned eller legges bak en
`<details>`, og summaryen sier at det er et forbehold. Et anker inn i
en lukket del åpner den (`aapneAnker()` i `kystloggen.js`).

### Sitering og nedlasting (avsnitt 8)

`.siterboks` er en seksjon med blekkstrek. Selve referansen står i
`.siterbar` på `--felt` med en hårlinje rundt — det er stedet på siden
man kopierer fra, og det eneste som har ramme. Kopierknappen er `hidden`
i markupen og slås på av skriptet.

`.nedlasting` er en etikett og en verktøylinje, med noten under.

### Trafikklyset (avsnitt 9)

**Ordet bærer, ruta forsterker.** Cella inneholder «rød», «gul» eller
«grønn» i vanlig tekstfarge, og ruta er et `::before` som bare finnes i
CSS-en (WCAG 1.4.1).

- Ruta tegnes **bare der den har fyll** (`lys-rod`, `lys-gul`,
  `lys-gronn`), eller der den er bevisst tom (`farge_mangler`, stiplet).
  En tom rute ved et fargeord leses som at fargen mangler.
- Fargen gis av verdien, ikke feltet: `nettsted.fargeklasse()`.
- I tabellkort står ruta på `::after`, fordi `::before` er etiketten.
- `.rute` og `.rundestripe` er samme rute utenfor tabeller.
- Ringen er nøytral: gul når ikke 3:1 mot papiret, så det er ringen som
  gjør at ruta synes.

### Brikkene (avsnitt 6)

`.typemerke` er en lenke til en filtrert side, minst 44 px høy.
`--valgt` er blekk med lys skrift. `--tom` er en type uten endringer:
dempet, uten flate, og `aria-disabled`.

### Typestolpene på forsiden (avsnitt 6)

Ukas fem største typer med antall og en stolpe. Stolpen er en SVG-`rect`
med bredde i prosent av den største — ikke en inline-stil, så CSP-en
kan stå som den er. Typene er lenker til typesidene.

### Grafer (avsnitt 10)

- Søylene er `--hav5`, én farge.
- Tiltaksgrensa er en stiplet `--rust`-linje i trapper: BarentsWatchs
  «Lusegrense uke» for lokaliteten, uke for uke (`sjotemperatur.lusegrense`).
  Brudd der kilden ikke oppgir noen; aldri en konstant vi har satt.
- Brakklagte uker er et grått bånd. Tomrom er ingen rapport, ikke null.
- Svake vannrette hjelpelinjer, ingen ramme.
- Grafen er ett tabulatorstopp. Piltastene, Home og End går gjennom
  søylene; søylen i fokus er blekk, og verdien leses av en skjult
  statuslinje.

### Kart (avsnitt 10)

- Land `--kart-land`, hav `--kart-hav`, kyst `--kart-kyst`. Lagene som
  bare er bakgrunn har `pointer-events: none`, så pekeren treffer
  punktene og ikke landet over dem.
- Nabolokalitetene er små og dempet; under peker og i fokus blir de
  større og rust.
- Områdekartet har tak på høyden: et høyt område krymper i bredden og
  står ved venstrekanten.
- Alt kartet viser, står også i en tabell på siden.

### Verktøytipset (avsnitt 10)

`.verktoytips`: blekkflate, papirskrift, 13 px. Tegnet av
`kystloggen.js` for alt i et kart eller en graf som har `<title>`.

- Det står **inne i figuren** og snur ved kanten av tegneflata, så det
  aldri dekker bildeteksten.
- Det vises ved fokus, ikke bare under peker.
- Det er `aria-hidden`: lenka har navnet i `aria-label`, og grafen har
  statuslinja.
- Uten skript viser nettleseren `<title>` selv.

### Sidenavigasjonen (avsnitt 11)

`.sidenav` på de delte indeksene: hver side lenker til alle de andre med
nummerspennet den dekker. Over og under tabellen.

### Bunnteksten (avsnitt 17)

Full bredde på `--hav9`. Kilder og vilkår, arkivet, kontakt, og en
proveniensline med byggedato. Det er det andre stedet havet brukes.

## Fokus og peker

- `:focus-visible` er en 2 px rust ring med 2 px luft, overalt.
  Nabopunktene i kartene får i stedet en større, rust prikk, og et
  område på kystkartet en blekkstrek rundt.
- Peker gir tone på tabellrader, mørkere søyle, rust kartpunkt og
  tydeligere strek på lenker. Ingen opplysning finnes bare under
  peker: det tipset viser, viser fokus også, og tabellen under har det.
- Berøring: et trykk på en søyle viser verdien til neste trykk.

## Regler stilarket ikke kan bryte

Disse står i hodet av `stil.css`, og porten eller prøvene feller brudd.

1. **Ingen elementer inne i en `data-felt`-celle.** Porten leser teksten
   fram til første `<`; en `<span>` rundt verdien gjør den blind.
   Pynt gjøres med `::before`, `::after` eller på cella selv.
2. **Ingen klasse med ordet `navn` eller `eier`**, heller ikke som ledd
   i et sammensatt navn (`typestolpe-navn`). Porten leser den som
   «her står et navn». Unntaket er cellene som faktisk bærer et navn.
3. **Markupkontrakten** — `data-felt`, tabell-id-ene, `<caption>` eller
   `aria-labelledby`, `th scope`, `time datetime` — endres ikke av en
   designrunde.
4. **Ingen eksterne ressurser.** Fontene ligger hos oss, og et ikon er
   en strek, en firkant eller et tegn fra fontene. Plex Sans har pilene
   (↓ ↑ → ←), men ikke trekanter; vinkelpilen i en summary er tegnet
   med CSS.
5. **Ikke skriv et tokennavn etterfulgt av kolon i en kommentar i
   palettavsnittet.** Kontrastprøven leser paletten med et regulært
   uttrykk.

## Bevisst ikke brukt

| Ikke | Hvorfor |
|---|---|
| Mørk modus | Hver farge måtte vedlikeholdes to ganger, og feilene sto i modusen ingen så på. Se `BRIEF.md`. |
| Omrissknapper | Så ut som en mal. Lenker er lenker, og det finnes én knapp. |
| Bokser rundt seksjoner | Tre rammer på en skjerm er støy; hårlinje og luft gjør jobben. |
| Vekselvis radtone | Erstattet av tone på raden under peker, som følger raden der det trengs. |
| Skygger og runde hjørner | Arkiv, ikke app. |
| Versaler i løpende tekst | Registerets versaler er en egenskap ved inntastingsfeltet, ikke ved navnet. |
| Ikonfonter og bildeikoner | Eksterne ressurser, og ingen av dem sier mer enn ordet. |
| Mørkt bånd i toppen | Se toppen over. |

## Kjente udefinerte variabler

`tests/test_nettsted.py::KJENTE_UDEFINERTE` peker hit: en variabel som
brukes uten å være definert, må stå her med grunnen. Lista er tom fra
08.10.2026. Den siste, `--farge-stripe`, er fjernet sammen med den
vekselvise radtonen den skulle gi.
