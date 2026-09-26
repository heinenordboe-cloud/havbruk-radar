# Kartgeometrien — hvor filene kommer fra

`maler/geo/` har tre filer: to hentede og ett AVLEDET utdrag.

    produksjonsomrader.geojson   Fiskeridirektoratets polygoner, NLOD
    land-norge.geojson           Natural Earth 1:10 m, public domain
    kystlinje.json.gz            Kartverket N500 + N2000, CC BY 4.0,
                                 avledet av verktoy/kystlinje.py

Alle tre tegnes INN i SVG-en ved bygging. Det ene unntaket er
forsidens hero: den er en egen fil, `/kart/norge.svg`, fordi den er den
samme på hver visning og kan caches for seg — se `skriv_norgeskart()`.

Av lisenstekstene følger bare Natural Earths med til nettstedets rot.
Kartverkets krav er en KREDITERING og ikke en tekstfil: «© Kartverket»
med lenke, under hvert kart og i bunnteksten på hver side som viser
ett. Porten håndhever det — se
`publiseringsvakt.kart_uten_attribusjon()`.

## PROJEKSJONEN ER UTM 33N (EPSG:25833)

Fra 25.09.2026. Før det var kartene ekvirektangulære med en
`cos(midtbredde)`-korreksjon, og den er riktig i ETT snitt og gradvis
feil bort fra det. Norge er tretten breddegrader langt. MÅLT på
oversiktskartets utsnitt:

    Lindesnes    58 °N    0,81x   en femtedel for smalt
    Nordhordland 64 °N    0,98x
    Nordkapp     71 °N    1,33x   en tredjedel for bredt

UTM 33N holder hele landet innenfor 0,7 % — målt mot Kartverkets egen
transformasjonstjeneste, se `tests/test_kart.py`.

**Og det gjør projeksjonen til en skalering.** Kartverkets kystkontur
ER i 25833, så `kart.Projeksjon` flytter origo og ganger med et tall.
Det som ikke er i 25833 — produksjonsområdene, Natural Earths
naboland, lokalitetenes koordinater — går gjennom `kart.utm33()` én
gang der det leses.

Gradnettet måtte bli POLYLINJER av samme grunn: i UTM krummer både
breddegrader og lengdegrader, og 16 grader fra sentralmeridianen er
meridiankonvergensen omtrent 15 grader.

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

**ROLLEN ER ENDRET 26.09.2026: Natural Earth tegner NABOLANDENE.**

Fram til da var den kystlinja på hvert kart. Grensa var kjent og stod
her: 1:10 m er omtrent 1 km oppløsning, og på et utsnitt på 36 km i 560
piksler er ett piksel 64 meter — kystlinja var altså 16 piksler grov.
Fjorder forsvant og holmer fantes ikke.

Kartverkets N500 har tatt over for Norge. Natural Earth blir værende
for Sverige, Finland og Danmark, som Kartverket ikke kartlegger, og som
landmassen under Kartverkets havflate på heroen. En kyst som stoppet
ved riksgrensa ville vært et Norge som svever i ingenting.

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

## kystlinje.json.gz — Kartverkets kystkontur, avledet

**Det AVLEDEDE utdraget.** Kildene lastes ned for hånd og ligger aldri i
repoet; utdraget gjør. Skriptet er `verktoy/kystlinje.py`, og
byggetrinnet leser bare utdraget og laster aldri ned noe.

| | |
|---|---|
| Kilde | Kartverket, N500 og N2000 Kartdata, laget `Arealdekke` |
| Lisens | **CC BY 4.0 — © Kartverket.** Se `docs/LISENSKJEDE.md` merknad J |
| Hentet | 2026-09-25 |
| Projeksjon | EPSG:25833 (EUREF89 UTM 33N), meter rundet til 10 m |
| Størrelse | 2 508 702 byte komprimert, 8,63 MB ukomprimert |
| sha256 | `d15bb418f3b65d86ec381a29851e6cca82b093fd6afb75bdf7a40c50ad24ba86` |

### Kildene, med sha256

    Basisdata_0000_Norge_25833_N500Kartdata_GML.zip    68 009 627 byte
    ae9ba9c1fff4d3e99fccdf26f288e7db428f6e8f9f7cfe2ecd816687605f79dc

    Basisdata_0000_Norge_25833_N2000Kartdata_GML.zip    4 939 454 byte
    66cf10c6c0bffffbe2343ae8b4597a8d334604134882633462de7dfc34ef514a

Begge fra `nedlasting.geonorge.no/geonorge/Basisdata/`, 25.09.2026.
Summene er skriptets egne; det skriver dem ut hver kjøring.

### Hva som er i fila

    n500    lokalitetskartet, 36 km bredt
            hav     516 flater, 222 140 punkter
            kyst  12 357 linjer, 226 400 punkter
    n2000   oversiktskartet, hele kysten
            hav      87 flater,  29 640 punkter
            kyst   2 362 linjer,  30 653 punkter

**To lag, og de har hver sin rolle.** `Havflate` er havet som FLATE med
øyer som interiørringer, og fylles UTEN strek. `Kystkontur` er kystlinja
som LINJE og tegnes som strek oppå. Tegnes havflata med strek i stedet,
vises delelinjene mellom nabo-havflater som rette streker tvers over
sjøen — målt på prøveklippene 25.09.2026.

**Prisen, sagt rett ut:** de to lagene bærer i praksis den SAMME
geometrien to ganger, 222 140 og 226 400 punkter. Det er halve fila.
Alternativet er å merke hvilke segmenter av havflatas ringer som er ekte
kyst, og det er en topologijobb mot to datasett som kan være uenige om
et punkt. Fila er 2,5 MB og taket er 3; det er ikke verdt den
kompleksiteten før taket er nådd.

### 20 km-regelen, og hva den faktisk kuttet

N500 tas bare med der det ligger en lokalitet innenfor 20 km. Målt:

    havflater   530 -> 516     kystlinjer  12 504 -> 12 357

Regelen biter på KYSTLINJENE, som er korte, og nesten ikke på
havflatene, som er få og store: en havflates omskrevne rektangel dekker
et helt havområde, og da er det alltid en lokalitet i det. At tallet er
så lite er i seg selv et funn — norsk kyst er tett dekket av
akvakultur, og «nær en lokalitet» er nesten hele kysten.

Grensa er 20 km mens lokalitetskartets halvdiagonal er 25,5 km. Hjørner
av et utsnitt kan derfor mangle kystlinje der ingen lokalitet ligger
innenfor 20 km — de hjørnene er åpent hav eller innland.

### Hvor utdraget brukes, og med hvilken toleranse

    lokalitetskart   n500    36 km, 560 px, toleranse 1,6 px
    områdekart       n500    området selv, 760 px, toleranse 0,7 px
                     n2000   der n500 gir et kart over 150 kB
    /kart/norge.svg  n2000   hele kysten, 1800 px, toleranse 0,8 px

**Toleransen på lokalitetskartet er 1,6 piksler, og det er ikke en
smakssak.** Ved 36 km i 560 piksler er ett piksel 64 meter, så 1,6
piksler er 102 meter — PRESIS der N500 selv slutter. Under det kaster
vi kildens egen støy; over det ville vi kastet kysten. Taket på 60 kB
per side er nådd akkurat der kilden tar slutt. MÅLT på de seks tetteste
skjærgårdene: 0,35 px ga 69 kB, 1,6 px gir 57 kB, og bildet er det
samme.

**Områdekartet velger serie per område, og valget er målt.** De tretten
er ulike: PO 1 er 120 km bredt, PO 4 er 330. `omraadekart()` tegner med
N500 først, måler hva kartet koster, og faller til N2000 over 150 kB.
Målt på det bygde nettstedet 26.09.2026:

    N500     PO 2, 5, 7, 10, 11, 12, 13      43-149 kB
    N2000    PO 1, 3, 4, 6, 8, 9             64-111 kB

«De nordlige er store» ville vært et gjett om geometri vi har liggende.

**Taket måler HELE kartet, ikke banedataene.** Første utkast talte bare
`d`-strengene, og det er stedfortrederen fra CLAUDE.md regel 1b-2: den
er riktig helt til prikkene blir mange. I PO 9 er lokalitetsprikkene
72 kB av et kart på 207 — over en tredjedel. `kart._svgbyte()` regner
markupen slik malen skriver den, pluss `RAMME_BYTE` = 2000 for
`<svg>`-taggen, gruppene og målestokken; rammen er målt på de tretten
bygde sidene (907–1814 byte). Anslaget kan bli feil om malen endres, og
prøven som HOLDER løftet leser derfor den ferdige sida:
`test_ingen_omraadeside_har_et_kart_over_150_kb`.

### Havflata slutter ved datakanten, og det er synlig

`Havflate` dekker Norges sjøterritorium — et belte langs kysten — og
ikke havet utenfor. Der beltet slutter, har vi ingen opplysning, og
hvilken farge den flata får er et VALG om hva «ingen opplysning» skal
se ut som. De to kartene svarer ulikt, og begge svarene er målt.

**Områdekartet: bakgrunnen er hav, og landet kommer fra Natural
Earth.** Utsnittene er 120–330 km brede, og den vestlige fjerdedelen
ligger utenfor beltet. MÅLT på PO 4: 150 av 760 piksler åpent hav malt
i landfargen. Natural Earths grove land legges derfor under havflata.
Den er aldri synlig der Kartverket har data, så 1 km oppløsning spiller
ingen rolle; den svarer bare på om dette er havbunn eller åpent hav der
Kartverket tier — og ved 300 meter per piksel er 1 km tre piksler.

**Lokalitetskartet: bakgrunnen er land, og Natural Earth brukes
ikke.** Samme grep der ville vært feil, og det er målt: ved 36 km i 560
piksler er ett piksel 64 meter, så Natural Earths kystlinje er 15
piksler unna. Målt på seks tilfeldige lokaliteter er **5–28 % av
utsnittet verken NE-land eller havflate** — de prosentene ville blitt
malt som sjø, og mye av dem er land.

**Prisen, sagt rett ut:** et 36 km-utsnitt som når utenfor beltet,
maler åpent hav i landfargen. Det gjelder de lokalitetene som ligger
langt til havs. Målt 26.09.2026: tre lokaliteter har over 10 km til
nærmeste kystkontur — 11899 (19,8 km, Nordsjøen utenfor Egersund),
11851 (11,2) og 45275 (11,1) — og på deres sider er mesteparten av
kartet feil farge. Det er ikke rettet, fordi rettingen krever å vite
hvor Kartverkets DEKNING slutter, og den opplysningen finnes ikke i
`Havflate`: flatas ytterring følger kysten på den ene siden og
datakanten på den andre, uten å si hvilken som er hvilken.
`Dataavgrensning` i N500 er linjer, ikke flater, og å sette dem sammen
til en dekningsflate er en topologijobb. Åpent spørsmål, ikke en
glemsel.

### DYBDEDATA ER VURDERT OG VALGT BORT

Kartverket gir ut dybdekurver under den samme lisensen — CC BY 4.0,
åpne data. Lisensen er lest og står ordrett i `docs/LISENSKJEDE.md`
merknad J. To ting avgjorde:

1. **Forbeholdet.** «Sjøkart – Dybdedata» bærer et vilkår de andre
   datasettene ikke har: *«Dataene er ikke godkjent for navigasjon. De
   er ikke egnet for nøyaktige masseberegninger.»* Det er ikke en
   formalitet på et nettsted som viser oppdrettsanlegg i sjøen — en
   dybdekurve ved siden av en lokalitet SER UT som et sjøkart, og det
   er nettopp den lesningen Kartverket fraskriver seg. Kildens egen
   beskrivelse av de generaliserte kurvene sier dessuten at de er
   «grove og har varierende kvalitet og nøyaktighet».
2. **Størrelsen.** De generaliserte kurvene er 104,7 MB (SOSI) eller
   91,7 MB (S57) landsdekkende; de fulle dybdedataene er 18,4 GB
   fordelt på 427 filer. Ingen av dem finnes som GeoJSON eller
   GeoPackage.

Blir de tatt i bruk en dag, må forbeholdet stå ved VISNINGEN og ikke
bare i lisensfila. Og da hører de hjemme på en egen side om bunnen —
ikke som et lag under et kart som svarer på hvor et anlegg ligger.

### Oppdatering

Last ned på nytt, kjør `verktoy/kystlinje.py`, og skriv om sha256 og
tallene over. **Gjør det sjelden.** Fila ligger i git, og git glemmer
ingenting: hver ny utgave legger seg oppå den forrige i historikken.

## Oppdatering

Hent på nytt, sammenlign sha256, kjør klippingen på nytt, og skriv om
tallene her. Kartfiler fra en tjeneste kan endre seg uten at noe i
dataene beveger seg — samme grunn som at datokolonnen i
`LISENSKJEDE.md` finnes.
