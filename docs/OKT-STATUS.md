# Øktstatus 27.08.2026 — ekspertgruppen som kilde

Økta ble avbrutt midt i testkjøringen. Denne fila er skrevet for at
neste økt skal slippe å gjette hva som står.

**Ingenting er pushet.** Kode ligger på branchen
`ekspertgruppen-som-kilde` (695251f), data på `main` i datarepoet
(eef0363).

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

## 2. Ikke ferdig

### Testsuiten er IKKE verifisert — dette er det viktigste

Full suite er **ikke kjørt** etter at kilden ble lagt til. Siste fulle
kjøring ga 413 passerte, men det var før `sources/ekspertgruppen.py`
fantes. Alt som teller kilder — registry-tester, pipeline-tester,
`test_modulnavn_er_kildenavn` — har ukjent status.

`tests/test_ekspertgruppen.py` alene: **63 passerte, 2 feilet.**

| Test | Symptom | Ikke diagnostisert |
|---|---|---|
| `test_pdf_datoformatet[D:2020]` | `_les_pdf_dato("D:2020")` gir `None` | PDF-standarden tillater år uten måned/dag; regexet krever MMDD. Uavklart om testen eller koden har rett. |
| `test_arealandel_og_roc_er_to_felter` | `_ROC` bommer på «er 27 %» | Den valgfrie ordgruppen `(?:\w+\s*)?` spiser tallet når det ikke står et ord foran. Regexet traff 20 verdier i de ekte kroppene, så feilen er i robustheten, ikke i uttrekket som ble kjørt. |

Ingen av de to er undersøkt ferdig. **Ikke merge branchen før begge er
avklart og hele suiten er grønn.**

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
  skifte. 13 slike toårshopp, og de må ikke telles sammen med de 52
  ettårsovergangene.

### 3d. Det kontinuerlige måltallet er tynnere enn håpet

Forrige beslutningsnotat regnet med «65 celler med et kontinuerlig
utfall». Målt: **HI virtuell smolt oppgir årets vektede og uvektede snitt
for bare 4 av 13 produksjonsområder i 2020-rapporten.** De ni andre
oppgir seriens spenn over 2012–2020 og elvenes spenn innen året — to
andre størrelser om andre tidsrom. Uttrekket leser dem ikke, og feltet er
fraværende, ikke null.

Faktisk uttrukket: 8 celler `hi_virtuell_smolt_vektet`/`_uvektet`, 15
`hi_smittepress_arealandel`, 20 `hi_smittepress_roc_indeks`.

**Dette svekker premisset for å legge om til kontinuerlig utfall.** Det
bør avgjøres før neste analyseøkt.

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
