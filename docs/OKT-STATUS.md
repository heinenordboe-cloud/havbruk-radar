# Øktstatus 23.09.2026 — de fire punktene før lansering

Skrevet ved et avbrudd. **Testsuiten er grønn: 1 074 passerte.** Porten
er ren (14 kvitterte funn står). Bygget er verifisert etter hver
endring.

Forrige øktstatus står nederst i fila, uendret.

---

## Ferdig og pushet

### 1. Endringssiden for uke 39: 812 → 440 endringer

`docs/beslutninger/2026-09-23-en-hendelse-er-ikke-en-rad.md`
(commit `b196b32`). Tre målte feil i tellingen, alle med formen fra
CLAUDE.md 1b, pluss én publiseringsblokker:

- **362 trafikklysrader er fire vedtak.** PO 4 rød→gul (137
  lokaliteter), PO 9/10/11 grønn→gul (109/72/44). Fargen er en egenskap
  ved OMRÅDET, ført på hver lokalitet av registeret.
  `nettsted.SAMLES_PER_OMRAADE`.
- **«Ute av registeret» var usant for 20 av 22.** Slo opp alle 29
  selskapene i Brønnøysunds åpne API: 20 sto der fortsatt med ny
  næringskode, 2 var slettet, 7 hadde aldri forsvunnet. Alle 32
  «ny»-entitetene var registrert 1995–2026-04, null i september.
  Etiketten heter nå «Ute av vårt utvalg» / «Ny i vårt utvalg».
- **Et felt som kom er ikke en ny oppføring.**
  `changelog.merk_feltbevegelse()` spør snapshotene om entiteten står
  på begge sider. Nye slag `felt_ny`/`felt_borte`, vises og telles
  ikke.
- **Changeloggen fikk en lesedør.** 18.09-beslutningen skrev at «en
  'endringer denne uka' på tvers av kilder, eller en CSV av loggen»
  ville snudd valget. Designrunden bygget den. `les_alt()` går nå
  gjennom `fjern_personformer()`: 380 rader, 20 entiteter, ved lesing.

De 369 `antall_ansatte`-endringene står: verdi til verdi, median ±2,
maks 87. Én månedlig oppdatering, men 369 forskjellige fakta.

### 2. Trafikklyset: ny beleggsgrad «beslutning»

`docs/beslutninger/2026-09-23-fargeleggingen-er-et-eget-belegg.md` og
`docs/VERIFISERING-FARGELEGGINGEN.md` (commit `295d1e4`).

Trafikklyset besluttes i to trinn, og et gult område krever ingen
forskrift. Det forklarer alle 19 tomme cellene — de var ikke en mangel
ved kilden.

    begge kildene sier noe   46   enige 46, sprik 0
    bare beslutningen        19
    bare forskriften          0

`beslutning.py` leser de fem arkiverte pressemeldingene, pinnet på
sha256. 2026-kolonnen er full, og registerets «gjelder nå» stemmer med
2026-runden for alle tretten.

**Alle fem pressemeldingene var allerede arkivert og verifisert.**
Ingen re-arkivering trengtes; summene er identiske med
`docs/VERIFISERING-PRESSEMELDINGER.md`.

PO9 bærer departementets egen merknad om den særskilte vurderingen,
ordrett og med kilde.

Områdenavnene står som de står: produksjonsområdeforskriften bruker to
stavemåter av fem navn, og Akvakulturregisterets navn er § 3s, tegn for
tegn, for alle tretten. Punkt 4 i oppdraget er dermed besvart —
«Ryfylket» kommer fra kilden og beholdes.

---

## Ikke pushet ennå (ligger i arbeidskatalogen)

### 3. Publiseringsblokkerne — delvis

`docs/beslutninger/2026-09-23-eier-type-inn-i-hooken.md`, utkast.

**PERSONFORMER — nesten lukket.** Sju ledd er på plass: kildens
`fetch()`, `parse()`, lesedøra i `snapshot._les()`, `snapshot.write()`,
porten, changeloggens nye lesedør, og fra i dag `eier_type` i
`eierskap.fjern_egne_personer()` pluss samme hook i
`nettsted._siste()`.

Det siste leddet kom fordi premisset for å utelate `eier_type` sviktet:
MÅLT at `parse()` dropper H-FJ-0018 fra begge arkivkroppene, men at
snapshotet 21.09 har den likevel — F15, innsamlingen kjørte upushet
kode. Hvitelista leste den fila og gjorde dermed rede for en personform.
Nå er navnet og orgnummeret ute av hvitelista.

**Står igjen, kvittert:** tre personformnavn på 14 lokalitetssider, i
`tildelt_navn`. `tildelt_type` finnes ikke, så de kan ikke lukkes med
data — bare med navneendelsen, og den brukes til å OPPDAGE i porten,
ikke til å skjule. Kvittert av Heine 19.09.2026.

**Hvitelista mot `eierskap_historikk` — LØST**, og det ble løst 19.09.
`_datoene()` leser alle datoer for `verden`-partisjonerte kilder og
nyeste for `henting`. Verifisert 23.09: 21 årganger leses
(2006-12-31 … 2026-12-31), 2 213 orgnumre og 12 237 navn i hvitelista,
0 av de 106 personentitetene blant dem. Porten gir exit 0.

---

## Hva jeg holdt på med da økta ble avbrutt

Jeg hadde nettopp bekreftet at lokalitet 11593 rendrer riktig etter
hook-endringen («Innehaver: ikke oppgitt av kilden»), og hadde åpnet
`maler/lokalitet.html.j2` linje 106 for å se på en KOSMETISK ting:
nøkkeltallet viser «1 tillatelser» der det skal stå «1 tillatelse».
Ingen endring gjort. Det er ikke en usannhet, bare dårlig norsk.

## Hva som står igjen

1. **Kosmetikk:** entall/flertall på `tillatelser_oppgitt` i
   `maler/lokalitet.html.j2` linje 106, og samme sjekk for de andre
   nøkkeltallene.
2. **Punkt 2, resten:** rundene 2018, 2020, 2022 og 2024 er parset og
   lagt fram ordrett i `docs/VERIFISERING-FARGELEGGINGEN.md`. Heine
   leser avsnittene, og rundene legges til i `beslutning.GODKJENT` én
   for én. Til da står 12 celler som «ikke oppgitt».
3. **De fem utkastene** venter på «Hvorfor» og «hva som ville snudd
   det»: design-implementert, gratis-mot-betalt-grense,
   en-hendelse-er-ikke-en-rad, fargeleggingen-er-et-eget-belegg,
   eier-type-inn-i-hooken.
4. **Skjermbildene i `docs/design/implementert/`** er tatt før punkt 1
   og 2. Forsiden og endringssiden viser 812 der de nå ville vist 440,
   og PO-sidene mangler «beslutning»-ruta. De bør tas på nytt.
5. **APNE-SPORSMAL punkt 8** (ingen test måler en side som er lagt ut)
   står åpent.

---

# Øktstatus 27.08.2026 — ekspertgruppen som kilde

> **Note 09.09.2026.** Dette er et øktreferat fra 27.08.2026 og er ikke
> omskrevet. To ting i det er siden blitt feil, og begge gjelder
> ekspertgruppen: hovedrapportene for 2023, 2024 og 2025 ER lokalisert
> (Nasjonalt vitenarkiv, 01.09.2026), så dekningstallene i punkt 3b
> gjelder bare fram til den datoen; og dokumentasjonen som står som
> «mangler» i punktet under er skrevet — beslutningsnotatet fikk dato
> 2026-08-27, ikke 2026-08-26. Se `docs/REVISJON-2026-09-09.md`.

Kilden er lukket og målt. Analysen er ikke kjørt.

**Testsuiten er grønn: 482 passerte.** Branchen
`ekspertgruppen-som-kilde` er klar til å merges.

---

## 1. Ferdig og etterprøvd

### `sources/ekspertgruppen.py`

Ny kilde etter samme kontrakt som biomasse. Fem rapportkropper
2016–2022, én uttrekksfunksjon per kropp.

Etterprøvd mot de fem arkiverte kroppene: **alle ni (rapport, år)-par
leser 13 av 13 produksjonsområder**, og for hver av dem er tabellen og
den løpende teksten enige om hovedkonklusjonen (`_kryssjekk`).

Tre avklaringer som ble målt, ikke antatt:

- **`published_at` leses av PDF-ens `/CreationDate`.** `Last-Modified`
  er målt til å være en CMS-migreringsdato på to av to verter
  (hi.no sier 2022 om en rapport fra 2020, trafikklyssystemet.no sier
  2022 om en fra 2017). Vakt: faller `/CreationDate` utenfor
  `[vurderingsår, +1]`, er den en re-eksport, og `published_at` settes
  tom med advarsel.
- **Wayback gir tilgang, ikke proveniens.** Korreksjonen fra forrige
  runde er innarbeidet: `X-Archive-Orig-Last-Modified` bevarer
  opphavets header, og opphavets header er migreringsdatoen.
- **Utvandringsvinduet finnes i ÉN av fem rapporter.** Bare 2020 har det
  per PO, og der som datoer — ikke uker. 2016/17 brukte et standardisert
  40-dagersvindu, 2018 har ingenting, 2021 ingenting, 2022 bare verbale
  perioder («fra siste halvdel av april»).

### `backfill.py --rapporter`

Tredje modus, dispatchet på `utgivelser()` slik `hent_uke()`/`hent_alt()`
allerede gjør. Leser kroppene i utgivelsesrekkefølge, eldst først, slik
at hvert år først skrives (`compare`) og deretter revideres (`revisjon`)
av hver nyere rapport.

### `analyse/ekspertgruppen_celler.py`

Sikkerhetsgrad per celle. Snapshotet bærer den maskinelle lesemåten
(`tabell` / `lopende_tekst`); menneskelig verifikasjon føres i
`analyse/fasit/ekspertgruppen-verifisert.csv` og legges på ved lesing,
bundet til **både verdien og rapportens sha256** — så en forbedret parser
som flytter verdien opphever kvitteringen i stedet for å arve den.

`--uverifisert` lister cellene. `tolk()` returnerer `(relasjon, tall)` og
tvinger kalleren til å ta stilling til ulikheter.

### Data skrevet

6 snapshots (2016, 2017, 2018, 2020, 2021, 2022), 2020 i to versjoner.
**12 revisjonsrader.** 5 rapportkropper arkivert, 24 MB, hashene
verifisert etter gzip-runden.

Den kritiske: 2020-rapporten fantes ved øktas start bare i en agents
verktøycache.

---

### Testtilstand: grønn

Full suite: **482 passerte, 0 feilet.**

De tre feilene som sto ved avbruddet er diagnostisert og rettet. To av
dem var koden, én var testen:

| Feil | Verdikt | Hva som ble gjort |
|---|---|---|
| `test_ingen_kilde_setter_published_at_uten_a_normalisere` | **koden** | `_utgitt` returnerte en tuppel som ble pakket ut før tilordning, så vakten kunne ikke se statisk at verdien gikk gjennom en registrert UTC-normaliserer. Formen på tilordningen ER egenskapen som kan etterprøves. Advarselen kommer nå ut gjennom en liste, og `self.published_at = _utgitt(...)` er igjen et direkte kall. |
| `test_arealandel_og_roc_er_to_felter` | **koden**, og testen fanget et ekte tap | Den valgfrie ordgruppa `(?:\w+\s*)?` slukte tallet når det ikke sto et ord foran: «er 27 %» ga treff med tomt tall, «er moderat (33 %)» ga 33. **2 av 22 ROC-verdier falt stille bort**, én i hver av 2021- og 2022-kroppene, og begge var blant de høyeste i sitt år. |
| `test_pdf_datoformatet[D:2020]` | **testen** | Den påsto at ISO 32000s år-uten-måned skal tolkes som 1. januar. Ingen av de fem kroppene har den formen (regel 4), og tolkningen ville datert en novemberrapport ti måneder for tidlig i et felt som sammenlignes leksikografisk. Nektelsen er nå bevisst og dokumentert i stedet for tilfeldig. |

ROC-rettingen endret dataene. Snapshotene ble re-derivert fra det urørte
rå-arkivet — 2021 gikk fra 366 til 368 observasjoner, 2022 fra 72 til 74.
Revisjonsradene er uendret på 12.

**Merk for neste re-parse:** dette var trygt fordi dataene var lokale,
upushede og bare timer gamle. Etter push er en parserendring en
`source_version`-bump og en ny versjon ved siden av — ikke en
re-derivering.

---

## 2. Ikke ferdig

### Dokumentasjon som mangler

- `docs/KILDE-EKSPERTGRUPPEN.md` — ikke skrevet. Kilden er udokumentert
  utenfor docstringene, som riktignok er fyldige.
- `docs/beslutninger/2026-08-26-ekspertgruppen-som-kilde.md` — ikke
  skrevet. Punktene som krever Heines egen dom står under.

### Analysen er ikke kjørt

Etter avtale. Ingen rho, ingen korrelasjoner, ingen konklusjon om
hypotesen.

---

## 3. Funn som må inn i beslutningsnotatet

### 3a. Revisjonsaksen: de skiller seg på METODENE, ikke på kategorien

12 revisjonsrader, alle for 2020, alle mellom 2020-rapporten
(utgitt 2020-11-23) og 2021-rapporten (2021-11-11):

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
| 2, 6 | `metode_hi_virtuell_smolt_retning` (+ deres `__sikkerhet`) | pil lagt til / fjernet | |

**Svaret på spørsmålet:** de skiller seg verken på kategorien eller på de
kontinuerlige estimatene. De skiller seg på metodenes egne kategorier og
usikkerheter. `kategori` — hovedkonklusjonen — er uendret for alle 13
produksjonsområder.

2021-rapporten sier det selv: «kategorisering for HI smitte er redusert
fra høy til moderat påvirkning i produksjonsområde 2 … usikkerheten til
VI virtuell smolt er endret fra stor til middels i produksjonsområder 7
og 8. **Ingen hovedkonklusjoner er endret.**» Hver eneste endring den
beskriver ligger i changeloggen, og ingenting annet gjør det.

**Celler med mer enn én påstand:** 39 (13 PO × 2016, 2017, 2020). Bare
2020 ga en lagret versjon nr. 2 — 2018-rapportens gjentakelse av 2016 og
2017 var ordrett identisk, og en identisk `.2`-fil ville vært en påstand
om at kilden sa noe nytt da den ikke gjorde det.

### 3b. Dekning: 78 celler mot 65 — men ikke et supersett

| | gammel fasit | ny kilde |
|---|---|---|
| år med kategori | 2020–2024 | 2016–2018, 2020–2022 |
| (po, år)-celler | 65 | **78** |
| ettårsoverganger | 52 | **52** |
| kategoriskift | 11 | **13** |

**Kilden mister 2023 og 2024** (26 celler) som den håndskrevne fasiten
hadde. Hovedrapportene for de årene er ikke lokalisert på noen åpen
adresse — bare vedleggene ligger ute, og regjeringen.no svarer 403.

**Uavhengig kontroll:** fasiten og maskinuttrekket er **identiske på alle
39 cellene der begge har en verdi**. Det validerer begge.

### 3c. To ting som må telles for seg

- **Biomasse begynner 2017-10.** Full Stien-proxy kan ikke strekkes til
  2016 i det hele tatt, og 2017 er delvis: utvandringsvinduet
  (april–juli) ligger før seriens start. Reelt proxy-dekkede år er 2018,
  2020, 2021, 2022.
- **2019-hullet bryter persistensaksen.** 2018→2020 er ikke et ettårig
  skifte. **13 slike toårshopp, hvorav 2 er kategoriskift**, og de må
  ikke telles sammen med de 52 ettårsovergangene.

### 3d. Dekningsflaten — hele den, ikke ett felt

Forrige runde målte HI virtuell smolt i 2020-rapporten og fant årets
verdi for 4 av 13 PO. Det var ett felt i én rapport. Her er hele flaten,
målt på de fem arkiverte kroppene.

Tallet er antall PO med **årets verdi**; `(+Ns)` er PO der rapporten bare
oppgir et flerårsspenn eller et snitt over serien, som ikke er brukbart
som årlig utfall.

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

Summert over alle rapportene, og med ettårsoverganger — som er det et
utfall må ha for å kunne måle bevegelse:

| felt | (po, år)-celler | ettårsoverganger | år |
|---|---|---|---|
| **kategori** | **78** | **52** | 2016–18, 2020–22 |
| HI smittepress ROC | 22 | 11 | 2021, 2022 |
| VI VS vektet+uvektet | 18 | 8 | 2020, 2021 |
| SINTEF VS uvektet | 16 | 10 | 2020–2022 |
| arealandel over terskel | 15 | 2 | 2020 (+2 løse) |
| HI VS vektet / uvektet | 4 / 4 | 0 | 2020 |
| utvandringsvindu | 13 | 0 | 2020 |

Fire ting som ikke er åpenbare fra tabellen:

- **2018-rapporten har ingen modellavsnitt i det hele tatt.** 27 sider,
  skrevet under tidsnød. Bare kategorien.
- **2016/17-rapporten har HI VS-avsnitt for alle 13, men bare spenn.**
  Ingen årsverdi noe sted.
- **SINTEF dekker bare PO 2–7.** Modellen kjøres ikke for de andre, så
  taket er 6 PO per år, ikke 13.
- **VI VS er den mest regelmessige av modellene** («Uvektet og vektet
  gjennomsnitt av dødelighet var henholdsvis 9 og 6 %»), men 2022 la om
  til elvevise spenn og mistet PO-snittet.

### 3e. Finnes et kontinuerlig utfall med flere brukbare celler enn kategorien?

**Nei. For alle fire modellene.**

| | celler | mot kategoriens 78 | ettårsoverganger |
|---|---|---|---|
| HI smittepress ROC | 22 | 28 % | 11 |
| VI virtuell smolt | 18 | 23 % | 8 |
| SINTEF virtuell smolt | 16 | 21 % | 10 |
| arealandel over terskel | 15 | 19 % | 2 |
| HI virtuell smolt | 4 | 5 % | 0 |

Det største kontinuerlige feltet har under en tredjedel av kategoriens
celler og drøyt en femtedel av dens 52 ettårsoverganger.

De kan ikke legges sammen heller. Ingen av dem dekker de samme årene:
ROC finnes bare 2021–2022, arealandelen i praksis bare 2020, VI bare
2020–2021, SINTEF bare 2020–2022 og bare for PO 2–7. Å slå ROC og
arealandel sammen krever dessuten at noen avgjør om de er samme
størrelse — se punkt 3 under `[din vurdering]`.

**Omleggingen til kontinuerlig utfall er ikke mulig med disse
rapportene.** Det er ikke en påstand om at et kontinuerlig estimat ville
vært dårligere. Det er at ekspertgruppen ikke publiserer et som dekker
nok (po, år)-celler til å bære et måltall.

Forrige beslutningsnotat regnet med «65 celler med et kontinuerlig
utfall» og pekte på det som den store styrkegevinsten framfor en bedre
prediktor. **Det premisset holder ikke.**

Hva som ville snudd det: at HIs egne modellrapporter («Rapport fra
havforskningen», en annen serie enn ekspertgruppens) tabellerer
per-PO-estimater for hele 2012–2025. De er ikke undersøkt. Det er den
neste tråden hvis et kontinuerlig utfall fortsatt er ønsket — og den
ligger utenfor denne kilden.

---

## 4. `[din vurdering]` — AVKLART 16.09.2026, se hvor

De fire punktene som sto her lå åpne siden 27.08. Alle fire er besvart
et annet sted i mellomtiden, og ingen av dem var løsbærende ved
gjennomgangen 16.09.2026. De er derfor tatt ut herfra — regelen i
`docs/APNE-SPORSMAL.md` gjelder: **et spørsmål som er besvart, men
fortsatt står oppført som åpent, sender arbeid etter noe som allerede er
gjort.** Spørsmålene står igjen med hvor svaret ligger, ikke slettet
sporløst.

| spørsmålet | svaret ligger i | hva det ble |
|---|---|---|
| 1. Er `/CreationDate` god nok proveniens? | `docs/KILDE-EKSPERTGRUPPEN.md` punkt 3 | **Ja, MED vakt mot re-eksport.** Målt: `Last-Modified` er en CMS-migreringsdato på to av to verter. Datoen kreves innenfor `[vurderingsår, +1]`, ellers settes `published_at` tom. Samme valg er senere tatt for styringsgruppen. |
| 2. Skal fasitens 2023 og 2024 beholdes? | `2026-08-27-ekspertgruppen-som-kilde.md` og `KILDE-EKSPERTGRUPPEN.md` punkt 9 | **Beholdes, men degradert** til «et menneskes lesing uten sporbart dokument». Premisset er dessuten borte: hovedrapportene ble funnet 01.09.2026, og kilden HAR nå 2023, 2024 og 2025. |
| 3. Er arealandel og ROC samme størrelse? | `2026-08-27-ekspertgruppen-som-kilde.md`, «UTFALL av stoppregelen» | **Ja.** Definisjonene er ordrett like i 2020, 2021 og 2022, de er perfekt komplementære over 39 PO-år, og det er ingen sprang ved formuleringsskiftet. De lagres fortsatt som to felt — sammenslåingen er analysens valg, ikke innsamlingens. |
| 4. Skal 2022-sannsynlighetsfordelingen trekkes ut? | `KILDE-EKSPERTGRUPPEN.md` punkt 12, og docstringen i `_uttrekk_2022()` | **Ikke nå.** Innvendingen var ett års historikk; etter 01.09.2026 finnes fordelingen også i 2023-, 2024- og 2025-kroppene, i ulik tabellform. Kroppene er arkivert — det er en re-parse den dagen noen vil ha dem. |

**Ingen av de fire er samme spørsmål som grensa ved sektor 2300**
(`2026-09-16-grensa-gaar-ved-sektor-2300.md`). Det spørsmålet lå i
ENK-notatet fra 22.08, ikke her. Punkt 1 deler riktignok FEILFAMILIE med
det — en stedfortreder som er riktig akkurat så lenge den faller sammen
med det man egentlig spør om (CLAUDE.md 1b-2) — men `/CreationDate` mot
`published_at` og navneform mot personform er to ulike spørsmål med hvert
sitt svar.

**Ett funn fra gjennomgangen, som ikke er et åpent spørsmål men en
retting:** punkt 2s premiss falt bort, og da ble fasiten etterprøvbar for
første gang for 2023 og 2024. Målt 16.09.2026 mot snapshotene:

    2020   13 av 13 enige
    2021   13 av 13 enige
    2022   13 av 13 enige
    2023   13 av 13 enige
    2024   12 av 13 — PO9: fasiten sier «lav», rapporten sier «moderat»

Den ene uenige raden er nettopp den fasiten selv merker `utledet` og ikke
`verifisert`, og `lusepress_mot_fasit.py` har allerede en seksjon 4b som
kjører uten 2024 av den grunn. Raden er ikke rettet her — det er en
endring i en fasitfil med egen proveniens, og den skal gjøres bevisst.

---

## 5. Kjente konsekvenser som er akseptert, ikke oversett

- **En verdi som dukker opp eller forsvinner gir to changelog-rader** —
  én for verdien og én for `__sikkerhet`-søsteren. Det er prisen for å
  ha proveniensen på raden.
- **`__sikkerhet`-feltene er konstante i ett snapshot**, så `minoritet`
  er 0 og feltvakten teller nullstrekk. Med én kjøring i året treffer
  standardgrensen på 13 tidligst i 2039. Terskelen er **ikke** hevet for
  å dempe den: alarmen ville da vært sann — den ville betydd at ingen har
  verifisert en eneste celle på tretten år.
- **pypdf logger «Rotated text discovered» og «Ignoring wrong pointing
  object».** Dempet til ERROR. Garantien for at det ikke skjuler noe er
  `_kryssjekk`, som leser hovedkonklusjonen to ganger av hver kropp og
  krever enighet for alle tretten områdene.

---

## 6. Første steg neste økt

1. Diagnostiser de to feilende testene.
2. Kjør full suite. Tallet, ikke inntrykket.
3. Skriv `docs/KILDE-EKSPERTGRUPPEN.md` og beslutningsnotatet.
4. Avklar punktene i seksjon 4.
5. Merge branchen. Push begge repo.
