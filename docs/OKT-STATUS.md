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

## 4. `[din vurdering]` — punkter som krever Heines dom

1. **Er `/CreationDate` god nok proveniens?** Den er lest fra dokumentet,
   ikke gjettet, men den er eksporttidspunktet — ikke en utgivelsesdato
   noen har gått god for. Alternativet er tom `published_at` for alle
   fem, og da kan revisjonsaksen ikke ordne kroppene i det hele tatt.
2. **Skal fasitfila `ekspertgruppen-po-kategori.csv` beholdes for 2023 og
   2024?** De to årgangene finnes ikke i kilden og kan ikke etterprøves.
   Å slette dem er å miste noens lesing; å beholde dem er å ha to fasiter
   med ulik proveniens side om side.
3. **Er `hi_smittepress_arealandel` og `hi_smittepress_roc_indeks` samme
   størrelse?** De er lagret som to felt fordi ordlyden er ulik og ingen
   av rapportene definerer dem mot hverandre. Slås de sammen, blir et
   metodeskifte til en verdiendring; holdes de fra hverandre, blir serien
   brutt i to.
4. **Skal 2022-rapportens sannsynlighetsfordeling trekkes ut?** Den er
   rikere enn kategorien, men finnes bare fra 2022 og ville gitt et felt
   med ett års historikk.

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
