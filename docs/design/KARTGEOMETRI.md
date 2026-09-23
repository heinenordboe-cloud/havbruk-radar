# Kartgeometrien — hvor filene kommer fra

`maler/geo/` har to hentede filer. Begge tegnes INN i SVG-en ved
bygging og sendes ikke ut som filer; det er bare Natural Earths
lisenstekst som følger med til nettstedets rot.

## produksjonsomrader.geojson — Fiskeridirektoratets offisielle polygoner

| | |
|---|---|
| Kilde | `gis.fiskeridir.no`, tjenesten `FiskeridirWFS_akva`, lag 43 «Produksjonsomraader» |
| Lisens | NLOD — se `docs/LISENSKJEDE.md` merknad A og H |
| Hentet | 2026-09-22 |
| Størrelse | 24 784 byte, 13 polygoner |
| sha256 | `7f4c319fd0c810b85b5b46044c3d1698a6538128df77368a96018240eb8ac681` |

    curl "https://gis.fiskeridir.no/server/rest/services/\
    FiskeridirWFS_akva/MapServer/43/query\
    ?where=1%3D1&outFields=*&outSR=4326&f=geojson"

Ingen etterbehandling: fila er tjenestens svar, ordrett.

**Overleveringen ba uttrykkelig om disse.** Referansefilenes
områdegrenser var forenklet etter breddegrad — bånd tegnet på tvers av
kysten — og README-en sa: «Områdegrensene på kartet er forenklet etter
breddegrad, så bruk de offisielle polygonene.» Det er gjort, og
merknaden «områdegrenser forenklet» trengs derfor ikke.

### Feltene, og det ene som IKKE brukes

Hver flate bærer `id` (1–13), `name`, `areal`, `sjoareal`,
`sjoareal_gl` og `status`. Vi bruker `id` og geometrien. `name`
brukes ikke — områdenavnet leses av `akvakultur.prodomraade_navn`, som
er den kilden resten av nettstedet bruker, og to navnelister som kan
bli uenige er formen F6 og F7 hadde.

`status` bærer «grønn», «gul» og «rød», og ser dermed ut som svaret på
hvilken farge et område har. Den brukes IKKE. Begrunnelsen står i
`kart.py`: fargen er et forvaltningsvedtak med en dato og en hjemmel,
og et statusfelt i et karttjenestelag er en tredjeparts gjengivelse av
det uten noen av delene — det kan ikke si hvilken RUNDE det gjelder, og
ikke om fargeordet står i forskriften eller er utledet.

## land-norge.geojson — Natural Earth 1:10 m landflater, klippet

| | |
|---|---|
| Kilde | `natural-earth-vector`, `geojson/ne_10m_land.geojson` |
| Lisens | Public domain — `maler/geo/naturalearth-LICENSE.md`, kopiert ut til `/naturalearth-LICENSE.md` |
| Hentet | 2026-09-22 |
| sha256, kilde | `1ac90796408bc6ad6911d69448485d3c4dbf2190370080368a09976e1c9f7416` (10 157 965 byte, 11 features) |
| sha256, vår | `00e34a67340ed2272e857c30f96b36c5509622b453216a4c5d294695837368a8` (492 338 byte, 697 flater, 27 819 punkter) |

### FLATER OG IKKE LINJER, og hvorfor det ble byttet

Første utkast brukte `ne_10m_coastline`, som er LINJER
(sha256 `6f75ae0e…6788f6`, klippet til 364 719 byte / 220 linjer /
20 724 punkter). Det ga et posisjonskart der kysten var noen streker
uten innside: en leser kunne ikke se hvilken side som var land.

`ne_10m_land` er flater. Kystlinja er da flatens egen kant, tegnet som
strek oppå fyllet — én kilde, to roller, og de kan ikke bli uenige.
Prisen er 128 kB mer i repoet og 7 099 punkter til.

Natural Earth ber uttrykkelig om at kreditering ikke er nødvendig, og
oppgir en formulering for dem som vil likevel: **«Made with Natural
Earth.»**

### Hvorfor 1:10 m og ikke 1:110 m

Overleveringen: «Posisjonskartet trenger finere kystlinje enn
1:110 m.» 1:10 m er elleve ganger finere, og det er den fineste
oppløsningen Natural Earth har. Alternativene var Kartverkets N-serier
(NLOD, men store nedlastinger bak Geonorges API) og
OpenStreetMap-avledet kystlinje (ODbL — attribusjon og
del-på-samme-vilkår, en tyngre lisens å ta inn i et arkiv som skal stå
i ti år). Public domain og én fil vant.

**Grensa, sagt rett ut:** 1:10 m er omtrent 1 km oppløsning. På
forsidens oversiktskart er det mer enn nok. På et posisjonskart som
dekker 36 km er en fjordarm gjengitt med noen få punkter, og små holmer
finnes ikke. Kartet sier hvor lokaliteten ligger i forhold til kysten;
det sier ikke hvordan bunnen eller sundet ser ut. Det står i
bildeteksten på hver side.

### Klippingen

Kilda er hele verden — elleve landmasser, der Eurasia er én ring med
hundretusenvis av punkter. Vi klipper hver ring mot ruta
**3–33 °Ø, 57–72 °N** med **Sutherland-Hodgman**: algoritmen klipper
mot én akseparallell kant om gangen og SETTER INN skjæringspunktene, så
resultatet er en ny, LUKKET ring som følger rammen der landet går ut av
bildet.

En linjedeler duger ikke her. Kastes en bit av en ring, er den ikke en
ring lenger, og `Z` lukker den da mot et vilkårlig punkt — et trekantet
«land» tvers over fjorden.

Koordinatene er rundet til fire desimaler (≈ 11 m).

    27 819 punkter beholdt, 349 358 forkastet i den raske utsilingen.
    10,2 MB ble 492 kB.

Den SAMME algoritmen står i `kart._flatekant()` og brukes på nytt ved
bygging, mot posisjonskartets mye mindre utsnitt. MÅLT: uten den
skriver hver av de 1 782 lokalitetssidene ut alle 27 819 punkter; med
den er snittet 1 995 byte, og 1 lokalitet har ikke land i utsnittet i
det hele tatt.

Ruta tar med svenskekysten, finskekysten, Bottenvika og
Danmark — det er ikke en feil. En kystlinje som stoppet ved
riksgrensen ville vært et Norge som svever i ingenting, og
nabolandenes kyst er den referansen som gjør at Oslofjorden og
Bottenvika kan skilles.

Selve forenklingen til visningsoppløsning skjer ved bygging, i
`kart.forenkle()` (Douglas-Peucker), og den måles i PIKSLER og ikke i
grader — se modulens egen begrunnelse.

## Oppdatering

Hent på nytt, sammenlign sha256, kjør klippingen på nytt, og skriv om
tallene her. Kartfiler fra en tjeneste kan endre seg uten at noe i
dataene beveger seg — samme grunn som at datokolonnen i
`LISENSKJEDE.md` finnes.
