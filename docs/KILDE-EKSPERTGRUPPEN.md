# Ekspertgruppen — verifiseringsnotat og kildespesifikasjon

Verifisert mot fem nedlastede rapporter 26.–27.08.2026. Alt her er MÅLT
på kroppene som ligger i `data/arkiv/ekspertgruppen/`, ikke lest ut av en
nettside eller av dokumentasjon.

Kilden er `sources/ekspertgruppen.py`. Lesehjelperen for analysen er
`analyse/ekspertgruppen_celler.py`.

---

## 1. Hva dette er

Ekspertgruppen for vurdering av lusepåvirkning plasserer hvert av de
tretten produksjonsområdene i én av tre kategorier for lakselusindusert
villfiskdødelighet på utvandrende villakssmolt:

| kategori | dødelighet | rapportens egen ordlyd (2020, kap. 5) |
|---|---|---|
| `lav` | under 10 % | «Lav: < 10 % lakselusindusert villfiskdødelighet» |
| `moderat` | 10–30 % | «Moderat: 10-30 % lakselusindusert villfiskdødelighet» |
| `hoy` | over 30 % | «Høy: >30 % lakselusindusert villfiskdødelighet» |

Departementet fargelegger produksjonsområdene etter denne vurderingen.
Det er altså ikke en indikator ved siden av trafikklyssystemet — det er
måltallet systemet styres etter.

Fram til 26.08.2026 lå tallene i
`analyse/fasit/ekspertgruppen-po-kategori.csv`, skrevet for hånd, uten
proveniens, uten rå-arkiv og uten `source_version`. Det var CLAUDE.md
1b-3 i måltallet: en verdi utenfor dataene avgjorde hva de betyr, uten
spor av hvor den kom fra.

**Kontroll av den gamle fasiten:** håndfasiten og maskinuttrekket er
IDENTISKE på alle 39 cellene der begge har en verdi (2020, 2021, 2022 ×
13 PO). Det validerer begge to. Fasitfila er ikke slettet — se punkt 9.

---

## 2. Kildens form: N KROPPER som hver dekker M ÅR

Denne formen finnes ikke ellers i repoet.

    lusetall, sjotemperatur    én kropp per periode
    biomasse                   én kropp for alle periodene
    ekspertgruppen             N kropper som hver dekker M perioder,
                               og som OVERLAPPER

Overlappen er ikke noe vi påfører kilden. Rapportene gjentar hverandres
år, med kildens egne ord:

- 2018-rapportens kapittel 4: «For 2017 konkluderte ekspertgruppen med
  lav risiko … i ti produksjonsområder (1, 2, 6, 7, 8, 9, 10, 11, 12 og
  13) …», og tilsvarende for 2016.
- 2021-rapporten har en egen Tabell 2 for 2020: «Vurderingene for 2020 er
  oppdatert etter møte i september i ekspertgruppen.»

Derfor: **én observasjon om hvert år rapporten dekker, med rapportens
`published_at`.** To rapporter som er uenige om 2020 er ikke en feil —
det er to påstander om samme tidspunkt, gjort på hver sin dato, og begge
er sanne. Se CLAUDE.md 1b-5.

`observed_at` er årets siste dag (`2020-12-31`), av samme grunn som
biomasse bruker månedens siste: det er slutten av perioden raden
beskriver.

---

## 3. `published_at` — `/CreationDate`, ikke `Last-Modified`

Dette er kildens viktigste avvik fra `sources/biomasse.py`, og det er
målt, ikke antatt.

### Målingen som avgjorde det

Biomasse tar `published_at` fra `Last-Modified`, som Fiskeridirektoratet
setter presist (den 20. hver måned, ~04:40 UTC). Her er den samme
headeren noe helt annet. Målt 26.08.2026:

    hi.no/resources/rapport-2020_ekspertgruppen_final.pdf
        Last-Modified: Fri, 05 Aug 2022 12:39:43 GMT   rapport fra nov. 2020
    trafikklyssystemet.no/.../W Rapport ekspertgruppe 2017.pdf
        Last-Modified: Thu, 10 Mar 2022 11:20:43 GMT   rapport fra okt. 2017
    trafikklyssystemet.no/.../Rapport2018_final.pdf
        Last-Modified: Thu, 10 Mar 2022 11:40:00 GMT   rapport fra nov. 2018

To uavhengige verter, tre kropper, samme svar: headeren sier når fila ble
flyttet inn i dagens publiseringsløsning. To av dem deler til og med
tidspunkt på tjue minutter — det er en migreringsjobb, ikke en utgivelse.

Brukt som `published_at` ville den datert 2017-rapporten til 2022 og
lest revisjonsaksen baklengs for hele serien.

### Det som brukes

PDF-ens egen `/CreationDate`, satt av verktøyet som laget dokumentet:

| kropp | `/CreationDate` | produsent |
|---|---|---|
| 2016+2017 | `D:20171006061014Z` | Word / Mac OS X Quartz PDFContext |
| 2018 | `D:20181120124257+00'00'` | Microsoft Word |
| 2020 | `D:20201123130644+01'00'` | Microsoft Word 2016 |
| 2021 | `D:20211111154825+01'00'` | Microsoft Word 2016 |
| 2022 | `D:20221201103434+01'00'` | Microsoft Word 2016 |

Alle fem faller i vurderingsårets oktober–desember, som er når
ekspertgruppen leverer. Den er LEST av dokumentet, ikke utledet av en
publiseringsplan — CLAUDE.md 1b-7 punkt 2.

### Vakten mot re-eksport

`/CreationDate` er eksporttidspunktet, ikke nødvendigvis utgivelsen.
2016/2017-kroppen er kjørt gjennom «Mac OS X Quartz PDFContext», altså
re-eksportert; hadde den re-eksporten skjedd i 2026, ville feltet sagt
2026.

Derfor kreves datoen å ligge i `[nyeste vurderingsår, +1]`. Nedre grense
fordi en rapport ikke kan skrives før året den vurderer er omme; øvre
fordi leveransen kommer på høsten samme år eller tidlig året etter.
Faller den utenfor, settes `published_at` TOM med en advarsel — en
gjettet dato er verre enn ingen. Alle fem kroppene passerer i dag;
vakten finnes for den sjette.

### Delvise datoer nektes, selv om standarden tillater dem

ISO 32000 (7.9.4) lar alt etter årstallet utelates: `D:2020` er en gyldig
dato. `_les_pdf_dato()` nekter den likevel.

To grunner. Ingen av de fem kroppene har en slik dato, så å støtte
formen er å anta noe om et format vi ikke har sett (CLAUDE.md regel 4).
Og tolkningen ville uansett vært et gjett: `D:2020` som 1. januar
daterer en novemberrapport ti måneder for tidlig, i et felt som
sammenlignes LEKSIKOGRAFISK i `snapshot.publisert()` og
`diff.revisjon()`.

### Wayback gir TILGANG, ikke proveniens

2021- og 2022-rapportene ligger på regjeringen.no, som svarer 403 for
oss på både artikkelsider og direkte PDF-URL-er. Kroppene hentes via
Internet Archive.

Merk hva som IKKE endrer seg av det. `X-Archive-Orig-Last-Modified`
bevarer opphavets `Last-Modified` — og opphavets `Last-Modified` er
migreringsdatoen målt over. **Wayback flytter ikke problemet, den bevarer
det.** For biomasse var den headeren løsningen; her er den den samme
feilkilden, arkivert. `/CreationDate` leses av kroppen og er den samme
uansett hvilken adresse kroppen kom fra.

---

## 4. Én uttrekksfunksjon per rapportår

Den viktigste designbeslutningen, og den er tatt fordi rapportene MÅLT er
forskjellige dokumenter:

| kropp | sider | metodetabell | usikkerhet i tabellen | vindu per PO |
|---|---|---|---|---|
| 2016+2017 | 64 | nei — kategori i prosa | nei | nei, standardisert 40 dager |
| 2018 | 27 | ja, 6 metoder | **nei — det er CELLEFARGE** | nei |
| 2020 | 107 | ja, 7 metoder | ja, med pil | **ja, som datoer** |
| 2021 | 109 | ja ×2 (2020 og 2021) | ja, med pil | nei |
| 2022 | 130 | nei — SHELF | i prosa | nei, bare verbale perioder |

2022 byttet metode helt: ekspertgruppen gikk over til SHELF-elisitering
med en sannsynlighetsfordeling per kategori, og metodetabellen finnes
ikke lenger. 2018-tabellen koder usikkerhet som cellefarge («Farger på
rutene markerer liten, middels og stor usikkerhet»), som ikke finnes i
teksten i det hele tatt.

En generisk parser over den spredningen ville gitt riktig FORM og feil
TALL — prosjektets egen feilklasse, CLAUDE.md 1b-2. `parse()` NEKTER å
emittere for et år ingen skrevet funksjon dekker.

### Tabellene leses med `extraction_mode="layout"`

Uten den kollapser kolonnene til en tokenstrøm, og en rad med TOMME
celler kan ikke tilordnes metode: PO1 i 2020 har verken trål, bur eller
SINTEF, så åtte kolonner kommer ut som fem tokens.

To feller i de faktiske kroppene:

- **Superskript på egen linje.** PO12 i 2020 og PO4/PO12 i 2021 får
  usikkerhetssuffikset på linja OVER grunnlinja. Uten sammenslåing blir
  «Lav» stående uten usikkerhet.
- **Celler med mellomrom.** «Høy mid» (PO3 Bur, 2020) og «Lav stor» (PO6
  Trål, 2021) er én celle brutt av ordelingen.

Kolonnetilordningen går på nærmeste overskriftssenter, ikke på en grense
midt mellom to overskrifter: cellene er sentrerte, ikke venstrestilte, og
kolonnebredden varierer med den bredeste cellen.

### Kryssjekken — to lesinger av samme kropp

Rapportene sier hovedkonklusjonen to ganger: i oppsummeringstabellen og i
avsnittet under hvert produksjonsområde. `_kryssjekk()` krever at de
stemmer for alle tretten, og kaster ellers.

Det er den eneste kontrollen som kan felle et uttrekk som er syntaktisk
vellykket og semantisk feil — nøyaktig det en tabellparser med forskjøvet
kolonnetilordning ville produsert. Den er også garantien for at pypdf-
advarslene («Rotated text discovered», «Ignoring wrong pointing object»,
dempet til ERROR) ikke skjuler noe: skulle en advarsel bety at innhold
manglet, ville de to lesingene sprikt.

### PDF-en deler ord

2018-rapportens kapittel 4 skriver «hø y risiko for lakselusindusert
dødel ighet i to områder (3, 4)». Uten slakk for orddelingsmellomrom
fant lesingen bare 11 av 13 produksjonsområder for 2017 — og de to som
falt ut var nettopp de to i høy-kategorien. Slakken gjelder bare
kategoriordene i den ene lesingen; å normalisere bort alle enkelt-
mellomrom i hele dokumentet ville slått sammen ord som skal stå fra
hverandre.

---

## 5. Dekningsflaten

Målt på de fem kroppene. Tallet er antall PO med **årets verdi**;
`(+Ns)` er PO der rapporten bare oppgir et flerårsspenn eller et snitt
over serien, som ikke er brukbart som årlig utfall.

| felt | 16/17→16 | 16/17→17 | 18→16 | 18→17 | 18→18 | 20→20 | 21→20 | 21→21 | 22→22 |
|---|---|---|---|---|---|---|---|---|---|
| kategori | 13 | 13 | 13 | 13 | 13 | 13 | 13 | 13 | 13 |
| utvandringsvindu | 0 | 0 | 0 | 0 | 0 | **13** | 0 | 0 | 0 |
| HI VS vektet | 0 | 0 (+13s) | 0 | 0 | 0 | **4** (+9s) | 0 | 0 (+13s) | 0 (+13s) |
| HI VS uvektet | 0 | 0 (+13s) | 0 | 0 | 0 | **4** (+9s) | 0 | 0 (+13s) | 0 (+13s) |
| VI VS vektet+uvektet | 0 | 0 | 0 | 0 | 0 | **8** (+4s) | 0 | **10** (+3s) | 0 (+13s) |
| SINTEF VS uvektet | 0 | 0 | 0 | 0 | 0 | **5** | 0 | **5** | **6** |
| HI smittepress ROC | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **11** | **11** |
| arealandel over terskel | 0 | 0 | 0 | 0 | 0 | **13** | 0 | 1 | 1 |

Summert over alle rapportene:

| felt | (po, år)-celler | ettårsoverganger | år |
|---|---|---|---|
| **kategori** | **78** | **52** | 2016–18, 2020–22 |
| HI smittepress ROC | 22 | 11 | 2021, 2022 |
| VI virtuell smolt | 18 | 8 | 2020, 2021 |
| SINTEF virtuell smolt | 16 | 10 | 2020–2022 |
| arealandel over terskel | 15 | 2 | 2020 (+2 løse) |
| HI VS vektet / uvektet | 4 / 4 | 0 | 2020 |
| utvandringsvindu | 13 | 0 | 2020 |

Fire ting tabellen ikke viser av seg selv:

- **2018-rapporten har ingen modellavsnitt i det hele tatt.** 27 sider,
  skrevet under tidsnød — rapporten sier det selv: «Ekspertgruppen fikk
  mandatet fra styringsgruppen 3. oktober 2018 med kort tidsfrist.»
- **2016/17-rapporten har HI VS-avsnitt for alle 13, men bare spenn.**
  Ingen årsverdi noe sted.
- **SINTEF kjøres bare for PO 2–7.** Taket er 6 PO per år, ikke 13.
- **VI VS er den mest regelmessige av modellene** («Uvektet og vektet
  gjennomsnitt av dødelighet var henholdsvis 9 og 6 %»), men 2022 la om
  til elvevise spenn og mistet PO-snittet.

### Hva som gjør at et estimat ikke leses

Ni av tretten områder i 2020-rapporten oppgir HI VS som *seriens* spenn:
«varierte mellom 5 og 20 % i perioden 2012 – 2020». Det er en annen
størrelse om et annet tidsrom. Å lese den som årets verdi ville vært
riktig form og feil tall, så feltet er FRAVÆRENDE, ikke null.

---

## 6. Utvandringsvinduet — datoer, ikke uker

Bare 2020-rapporten oppgir det per produksjonsområde, og der som datoer
med et uketall bare for medianen:

| PO | antatt utvandring | 50 % | PO | antatt utvandring | 50 % |
|---|---|---|---|---|---|
| 1 | 24.04 – 05.06 | 17.05 (uke 20) | 8 | 20.05 – 06.07 | 13.06 (uke 24) |
| 2 | 24.04 – 10.06 | 18.05 (uke 21) | 9 | 20.05 – 13.07 | 13.06 (uke 24) |
| 3 | 24.04 – 17.06 | 21.05 (uke 21) | 10 | 22.05 – 20.07 | 22.06 (uke 25) |
| 4 | 24.04 – 17.06 | 23.05 (uke 21) | 11 | 03.06 – 20.07 | 25.06 (uke 26) |
| 5 | 24.04 – 17.06 | 24.05 (uke 21) | 12 | 03.06 – 27.07 | 29.06 (uke 26) |
| 6 | 23.04 – 16.06 | 18.05 (uke 20) | 13 | **27.06 – 27.07** | 09.07 (uke 28) |
| 7 | 23.04 – 23.06 | 24.05 (uke 21) | | | |

**Uketallet for start og slutt er VÅR avledning**, og den er årsavhengig:
samme dato faller i ulik ISO-uke fra år til år. Kilden lagrer datoene;
analyselaget regner om når det trenger uker, og står da for regnestykket
selv.

De øvrige rapportene har det ikke. 2016/17 brukte et standardisert
40-dagersvindu for alle vassdrag; 2018 og 2021 sier ingenting per PO;
2022 gir verbale perioder («fra siste halvdel av april til begynnelsen
av juni») som ikke er datoer.

Konsekvensen for analysen: vinduet finnes for ett år og må antas for de
øvrige. Analysen som brukte et fast uke 16–24 hadde 0 % overlapp med
PO13s faktiske vindu; se
`docs/beslutninger/2026-08-26-full-stien-proxy-forklarer-ikke-kategoriene.md`.

---

## 7. Sikkerhet per celle

Hver verdi får et søsterfelt `<felt>__sikkerhet`:

| verdi | betyr |
|---|---|
| `tabell` | lest fra en tabellcelle, maskinelt |
| `lopende_tekst` | lest fra et avsnitt, maskinelt |
| `verifisert` | et menneske har lest cellen i rapporten |

Den tredje ligger IKKE i snapshotet, og kan ikke: snapshots er
append-only, så et menneske som leser rapporten i morgen kan ikke skrive
om en fil fra i dag. Verifikasjonen føres i
`analyse/fasit/ekspertgruppen-verifisert.csv` og legges på ved LESING.

**Kvitteringen er bundet til verdien OG til kroppens sha256.** Endrer en
forbedret parser verdien, matcher kvitteringen ikke lenger, og cellen
faller tilbake til uverifisert. Det er CLAUDE.md 1b-4 anvendt på en
kvittering: en referanse skal ikke flytte seg selv. Uten bindingen ville
en verifikasjon arvet seg videre til et tall ingen har sett — verre enn
ingen verifikasjon, fordi den påstår at noen har sett etter.

    python analyse/ekspertgruppen_celler.py --uverifisert
    python analyse/ekspertgruppen_celler.py --verifiser 2020-12-31 2 kategori --av HN

### Kjent følge for feltvakten

`__sikkerhet`-feltene er konstante innenfor ett snapshot, så `minoritet`
er 0 og `health._vurder_innhold()` teller nullstrekk. Med én kjøring i
året treffer standardgrensen på 13 tidligst i 2039.

Terskelen er **ikke** hevet for å dempe den. Alarmen ville da vært SANN:
den ville betydd at ingen har verifisert en eneste celle på tretten år.
Se CLAUDE.md 1b-4 om å ikke utlede en terskel av selve feilen.

### Ulikheter lagres ordrett

«< 1 %» og «under 1 %» er kildens faktiske utsagn. `value` blir `"<1"`;
`float("<1")` kaster, og det er meningen.
`analyse/ekspertgruppen_celler.tolk()` returnerer `(relasjon, tall)` og
tvinger kalleren til å skrive ned hva den gjør med en ulikhet.

Sammensatte celler beholdes sammensatt: «Mod/Lav» i 2018-tabellen blir
`moderat/lav`, som ikke er slåbar opp i en kategoriordbok. Samme
prinsipp.

---

## 8. Revisjonsaksen

`backfill.py --rapporter` leser kroppene i UTGIVELSESREKKEFØLGE, eldst
først. Da er hvert år først en førstegangsskriving (`diff.compare`) og
deretter en revisjon (`diff.revisjon`) for hver nyere rapport som uttaler
seg om det. Motsatt vei ville hver eldre rapport vært en ELDRE påstand om
en dato som alt er skrevet, og `diff.revisjon()` kaster `Feilrekkefolge`.

**Resultatet: 12 revisjonsrader, alle for 2020**, mellom 2020-rapporten
(utgitt 2020-11-23) og 2021-rapporten (2021-11-11).

| PO | felt | fra | til |
|---|---|---|---|
| 2 | `metode_hi_smittepress_kategori` | hoy | moderat |
| 10 | `metode_hi_smittepress_usikkerhet` | stor | middels |
| 2 | `metode_hi_virtuell_smolt_usikkerhet` | middels | stor |
| 5 | `metode_hi_virtuell_smolt_usikkerhet` | stor | middels |
| 6 | `metode_hi_virtuell_smolt_usikkerhet` | middels | liten |
| 7 | `metode_hi_virtuell_smolt_usikkerhet` | stor | middels |
| 7 | `metode_vi_virtuell_smolt_usikkerhet` | stor | middels |
| 8 | `metode_vi_virtuell_smolt_usikkerhet` | stor | middels |
| 2, 6 | `metode_hi_virtuell_smolt_retning` (+ `__sikkerhet`) | pil lagt til / fjernet | |

2021-rapporten beskriver dette selv, i prosa: «kategorisering for HI
smitte er redusert fra høy til moderat påvirkning i produksjonsområde 2,
usikkerheten til HI smitte er endret fra stor til middels i
produksjonsområde 10 … Usikkerheten til VI virtuell smolt er endret fra
stor til middels i produksjonsområder 7 og 8. **Ingen hovedkonklusjoner
er endret.**»

Hver eneste endring den beskriver ligger i changeloggen, og ingenting
annet gjør det. Det er den sterkeste kontrollen som finnes på at
uttrekket leser riktig.

**Svaret på «skiller de seg på kategori eller på estimatene»: ingen av
delene.** De skiller seg på metodenes egne kategorier og usikkerheter.
`kategori` er uendret for alle 13.

### Celler med mer enn én påstand

39 (13 PO × 2016, 2017, 2020). Bare 2020 ga en lagret versjon nr. 2 —
2018-rapportens gjentakelse av 2016 og 2017 var ordrett identisk, og en
identisk `.2`-fil ville vært en påstand om at kilden sa noe nytt da den
ikke gjorde det.

### Pilens plassering

2020 skriver «Modstor↑», 2021 «Mod↑stor». Samme utsagn.
`_les_celle()` normaliserer begge til `(moderat, stor, opp)`. Uten det
ville hele 2020-tabellen sett revidert ut i 2021-rapporten, og de tolv
ekte revisjonene druknet.

### En verdi som dukker opp gir TO changelog-rader

Én for verdien og én for `__sikkerhet`-søsteren. Det er prisen for å ha
proveniensen på raden, og den er akseptert, ikke oversett.

---

## 9. Årene vi ikke har

| år | status | hva som er sjekket |
|---|---|---|
| 2016–2018 | **dekket** | |
| **2019** | **UBESVART SPØRSMÅL — ikke bekreftet fravær** | `trafikklyssystemet.no/Publikasjoner/Ekspertgrupperapporter` har en årstallsoverskrift «2019» med TOMT innhold. Ingen rapport lenket, ingen appendiks. 2018-rapporten sier at gruppen «er forespurt om å fortsette dette arbeidet i 2018 og 2019», så en 2019-vurdering kan ha eksistert uten å bli lagt ut. Vi vet ikke. |
| 2020–2022 | **dekket** | |
| 2023 | **ikke lokalisert** | Rapporten finnes (sitert som Vollset mfl. 2023). Bare vedlegg 1, 5, 6 og 7 ligger i `trafikklyssystemet.no/Portals/3/Publikasjoner/2023/`. Hovedrapporten er publisert av departementet; regjeringen.no svarer 403 på både artikkelsider og PDF-er for oss. |
| 2024 | **ikke lokalisert** | Levert NFD juni 2025. Bare `Vedlegg III Modellrapport HI 2024.pdf` er funnet. |
| 2025 | **ikke lokalisert** | Levert NFD desember 2025 (regjeringen.no id3141673). |

Skillet mellom 2019 og 2023–2025 er reelt og skal ikke viskes ut. For
2023–2025 VET vi at rapportene finnes og at vi ikke når dem. For 2019 vet
vi ikke om det finnes noe å nå.

Indekssiden er levende — nyeste oppslag er fra 02.06.2026 — men
dokumentlistene stopper på 2022.

### Fasitfila beholdes

`analyse/fasit/ekspertgruppen-po-kategori.csv` slettes ikke, fordi den
har 2023 og 2024 som kilden ikke har. Den er nå en ANNEN slags påstand
enn kilden: et menneskes lesing uten sporbart dokument. Se
beslutningsnotatet fra 27.08 for hvordan de to skal holdes fra hverandre.

---

## 10. Frekvens

`min_dager_mellom = 7` for en årlig kilde. Samme resonnement som
biomasse: sju betyr ikke «det kommer en rapport hver uke», men «tilby
kilden til kjøringen hver uke og la `finnes_allerede()` avgjøre».

Begrunnelsen er sterkere her enn for biomasse, fordi
publiseringsMÅNEDEN ikke er fast. Målt på kroppene: oktober (2017),
november (2018, 2020, 2021), desember (2022) — og departementet la ut
2024-vurderingen i juni 2025 og 2025-vurderingen i desember 2025. Et
etterslep i dager måtte gjettet hvilken måned, og gjettet ville vært feil
annethvert år.

Steg 2b i `run.py` hopper over kilden uten å hente så lenge nyeste år
ligger skrevet, så kostnaden mellom rapportene er null nedlastinger.

---

## 11. Lisens og attribusjon

Rapportene er offentlige utredninger levert Nærings- og
fiskeridepartementet, publisert av styringsgruppen for vurdering av
lakseluspåvirkning (drift: NINA) og av departementet. Ingen nøkkel, ingen
registrering, ingen avtale.

Sitering følger rapportenes egen form, f.eks.: Vollset, K.W., Nilsen, F.,
Ellingsen, I., Finstad, B., Karlsen, Ø., Myksvoll, M., Stige, L.C.,
Sægrov, H., Ugedal, O., Qviller, L., Dalvin, S. 2020. *Vurdering av
lakselusindusert villfiskdødelighet per produksjonsområde i 2020.*
Rapport fra ekspertgruppe for vurdering av lusepåvirkning.

---

## 12. Det som IKKE er bygget

- **2022-rapportens sannsynlighetsfordeling.** SHELF-metoden gir en
  fordeling over de tre kategoriene per PO («Det er mer sannsynlig enn
  ikke at … var mellom 10 og 30 %»). Rikere enn kategorien, men finnes
  bare fra 2022 og ville gitt et felt med ett års historikk. Kroppen er
  arkivert; det er en re-parse den dagen noen vil ha den.
- **VI og SINTEFs kontinuerlige estimater.** Formene er kartlagt (punkt
  5) men ikke uttrukket. VI ville gitt 18 celler, SINTEF 16.
- **Usikkerhet per metode i 2018.** Den er cellefarge og finnes ikke i
  teksten.
- **VIs scenariomarkører `*`/`**` i 2018.** Fotnoten definerer dem som
  spriket mellom forventet og verste scenario — en annen skala enn
  liten/middels/stor. Markørene strippes fra kategorien.
- **Appendiksene.** Hver rapport har 7–11 vedlegg med
  underlagsmodellene. De er ikke hentet.


## 2023, 2024 og 2025 — funnet i Nasjonalt vitenarkiv (01.09.2026)

De tre årgangene sto som ULOKALISERT fram til 01.09.2026. De ligger
ikke på trafikklyssystemet.no: `Publikasjoner/Ekspertgrupperapporter`
er hentet rå og gjennomsøkt, og siden nevner ikke 2023, 2024 eller 2025
med ett eneste tegn — ingen årsmappe, ingen NVA-lenke. Det samme gjelder
alle sju søskensidene under `Publikasjoner/`.

De ble funnet i **Nasjonalt vitenarkiv (NVA)** via søke-API-et:

    https://api.nva.unit.no/search/resources?query=lakselusindusert+villfiskdødelighet

| år | landingsside | Brage-handle | sider |
|---|---|---|---|
| 2023 | `nva.sikt.no/registration/01994cb82ce4-…` | `hdl.handle.net/11250/3104585` | 181 |
| 2024 | `nva.sikt.no/registration/01994cb7facb-…` | `hdl.handle.net/11250/3167955` | 157 |
| 2025 | `nva.sikt.no/registration/019aba84ab68-…` | `hdl.handle.net/11250/5323072` | 162 |

Handlene løser nå til NVA — Brage@NINA er migrert inn.

### Nedlastingen har TO ledd

NVA serverer ikke kroppen på en fast adresse. `GET
/publication/{id}/filelink/{fil}` gir JSON med en **presignert S3-URI**
som utløper, og den slås derfor opp ved hver henting. `Utgivelse.url`
er landingssiden — det som er siterbart og stabilt — og `filelink` er
endepunktet. En presignert URI i tabellen ville vært en adresse som
slutter å virke uten at noen har rørt den.

### `/CreationDate`, målt

    2023   D:20231122075159+01'00'   Microsoft Word for Microsoft 365
    2024   D:20241129084216+01'00'   Microsoft Word for Microsoft 365
    2025   D:20251120165148+01'00'   Microsoft Word for Microsoft 365

Alle tre i vurderingsårets november, som de fem foregående. Vakten i
`_utgitt()` passerer for alle tre.

sha256 på kroppene, verifisert 01.09.2026:

    2023   9f66a827d3bfc1c028b75102792ec88fb9af860e2f0f54fe6df5576a39803101
    2024   b740d4bb020df3017e4d784ba68667646e5d502010c724b818f6ea6308d8b6d4
    2025   6083b40bf9fa3fc0041c5d4515825d77d28be004fd40b8e128dfcbd0117db546

### 2023-kroppen er AES-kryptert

Den eneste av åtte. `pypdf` kaster `DependencyError` før første side er
lest, og `cryptography==50.0.1` er derfor pinnet i `requirements.txt`.
Uten den kan 2023 ikke leses i det hele tatt.

### 2025-rapporten dekker TO år

Kapittel 6.1 heter «Oppdaterte hovedkonklusjoner for 2024» og er en
forenklet ny SHELF-vurdering etter at de virtuelle postsmoltmodellene
ble oppdatert. Rapporten sier det selv:

> «Oppdateringen innebærer at påvirkningen i PO9 i 2024 blir vurdert til
> moderat, mens den i fjorårets rapport ble vurdert til å være helt på
> grensen mellom lav og moderat.»

Samme form som 2021-kroppen, som reviderer 2020. `aar=(2024, 2025)`, og
`diff.revisjon()` skrev 14 revisjonsrader til `2024-12-31.2.parquet`.

### PO9: kilden nekter å velge

Både 2024- og 2025-rapporten skriver «Konklusjon: Lav til moderat» i
avsnittet og «Lav–Moderat*» i tabellen, med fotnote om at
informasjonsgrunnlaget ikke er tilstrekkelig. Da står `kategori` TOM og
`kategori_ordrett` bærer ordlyden. Å presse den inn i én av tre ville
vært å ta et valg kilden uttrykkelig har latt være å ta.

### Tre feller i disse tre kroppene, alle fanget av vakter

1. **`Konklusjon: Lav til moderat` ga treff på `Lav`.** Riktig antall,
   feil verdi — ville skrevet `kategori=lav` for PO9 i to år.
   `_KONKLUSJON_ETT_AAR` har nå et negativt lookahead.
2. **Oppsummeringstabellen finnes to ganger i 2025-kroppen**, én for
   hvert år, og de er uenige om PO9. Tabellsiden velges nå av
   OVERSKRIFTEN, som navngir året, ikke av bildeteksten.
3. **Overskriften står også i innholdsfortegnelsen.** Kravet er nå
   overskrift OG et fullt sett rader.

2023-tabellen har dessuten kategorien i SISTE kolonne med usikkerheten
limt på som hevet skrift («Lavmiddels»), mens 2024/2025 har den i den
andre. Egne radmønstre, ikke ett som tåler begge — et mønster som tålte
begge ville tatt feil kolonne i den ene.

### ROC-dekningen — undersøkt 01.09.2026, og det var en bug

Hypotesen stemte. Målt mot kroppene: verdien STO der i 17 av 19
manglende tilfeller, i fem former mønsteret ikke tålte, pluss én etikett
`_hi_avsnitt` ikke kjente.

| form | ordrett fra kroppen | traff |
|---|---|---|
| «høy» faller bort | «Indeksen for risiko for **påvirkning** er høy (31 %)» | 2024 PO5, PO7; 2025 PO7 |
| **var** for **er** | «Indeksen for risiko for høy påvirkning **var** 43 %.» | 2025 PO2, PO8, PO9, PO11, PO12 |
| lang innskyting | «... er moderat i 2025 **for produksjonsområdet som helhet** (11 %)» | 2024 PO4; 2025 PO3, PO4 |
| omvendt ordstilling | «... **er indeksen** for risiko for påvirkning høy for 2024 (36 %)» | 2024 PO6 |
| sidehode i setningen | «... for høy **Rapport fra ekspertgruppe for vurdering av lusepåvirkning 152** påvirkning er lav (2 %)» | 2023 PO12 |
| ny etikett | «**HI kategorisert smittepress**:» | 2025 PO1,2,3,5,7,8,9,10 |

Den stille halvdelen av `_ROC` var `(?:[^\W\d_]+\s*)*`: den krevde REN
BOKSTAVTEKST mellom verbet og tallet, og falt derfor på ÅRSTALLET — «er
moderat i 2024 (23 %)» stoppet ordløpet ved «2024».

Sidehodet FJERNES nå i `_hi_avsnitt` framfor at mønstrene mykes opp. Et
mønster som tålte seksti tegn mellom «høy» og «påvirkning» ville tålt
hva som helst der, og da er det ikke lenger den setningen vi leser.

**PO1 er dekning, ikke bug.** Rapporten oppgir ingen indeks for PO1 i noe
år: 2021–2023 gir en AREALANDEL i stedet («forhøyet påvirkning utgjør
< 1 % av det kystnære arealet»), 2024 og 2025 gir bare en kvalitativ
vurdering. Uttrekket skal TIE der, ikke kaste.

Etter rettingen leser parseren **12 av 13 PO i hvert år 2021–2025**, med
PO1 som eneste fravær — 60 ROC-celler mot 43.

### Hvorfor setningstellingen ikke fanget det

`_krev_antall` krever et FORVENTET ANTALL. ROC har ikke ett: PO1 mangler
legitimt, og en terskel på 13 ville fyrt hver eneste årgang. En terskel
på «det vi fikk sist» er 1b-4s referanse som følger dataene.

Vakten som fantes var altså riktig bygget for kategorien, der tallet ER
13, og kunne ikke være det for et felt med ukjent dekning.

`_ROC_KANDIDAT` er svaret: nevner avsnittet «Indeksen for risiko» uten at
en verdi kommer ut, kastes `Rapportfeil`. Den trenger ikke vite hva
summen skal bli — den spør om vi leste det kilden faktisk skrev, og det
spørsmålet har et svar for hvert enkelt avsnitt. Den fant 2023 PO12 med
det samme.
