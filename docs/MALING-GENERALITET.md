# Måling: er maskinen generisk eller havbruksspesifikk?

Målt 15.09.2026 mot `8063e45`. To spørsmål, begge besvart med tall:

- **(a)** Hva i `core/` forutsetter havbruk?
- **(b)** Hva har hver av de elleve kildene kostet å legge til?

Ingenting er rettet. Målingen er svaret.

Metode: (a) er en token-skanning av `core/*.py` der kommentarer og
docstrings skilles fra kode, etterfulgt av lesing av hvert treff. (b) er
git-historikken, med testene faktisk kjørt i et arbeidstre sjekket ut på
hver enkelt historiske commit — ikke lest ut av commit-meldinger.

---

## (a) Havbruksantakelser i `core/`

`core/` er 4275 linjer over 17 filer. Skanningen fant **fem** steder der
et domeneord står i kode og ikke i prosa. Ingen av dem er havbruk.

### Reelle koblinger — men til NORSK REGISTERFORVALTNING, ikke til havbruk

| # | Sted | Hva | Dom |
|---|------|-----|-----|
| 1 | `core/changelog.py:220` | `STARTDATOFELT = {"enhetsregisteret": "registreringsdato"}` | **Reell.** Ett kildenavn og ett Brreg-feltnavn hardkodet i kjernen. |
| 2 | `core/persondata.py:57` | `FORM_FELT = "organisasjonsform"` | **Reell.** Brregs feltnavn. |
| 3 | `core/persondata.py:62` | `PERSONFORMER = frozenset({"ENK"})` | **Reell.** Brreg-kode for enkeltpersonforetak. |

Alle tre er norsk foretaksregister-kunnskap. Ingen av dem nevner fisk,
lokalitet, biomasse, tillatelse eller produksjonsområde. Kjørte du denne
maskinen mot Brreg for byggebransjen, ville alle tre fortsatt vært
riktige og nødvendige.

To av dem er også erklært som unntak der de står:

- `changelog.py:213-219` skriver selv at ordboka «står her og ikke i
  `core/diff.py` fordi det er kildekunnskap», og at en kilde som ikke
  står der blir stående umerket — usikkerhet ser ut som usikkerhet.
- `persondata.py` er navngitt i CLAUDE.md regel 3 som en bevisst
  plassering: filteret må virke ved lesing, ikke bare i kilden, fordi
  snapshotene fra 16.–17.08 er append-only og inneholder 34 ENK hver.

Regel 1b-3 er ikke oppfylt for nr. 3, og det er visst: `PERSONFORMER`
virker ved LESING, så lista kan endre hva et gammelt snapshot
inneholder. Det står i CLAUDE.md som et kjent, åpent punkt.

### Bare navngiving

| # | Sted | Hva | Dom |
|---|------|-----|-----|
| 4 | `core/paths.py:23` | `HAVBRUK_DATA_DIR` | **Navn.** Miljøvariabelens navn. Ingen logikk henger i det. |
| 5 | `core/miljo.py:111` | `"  Lokalt: ~/.havbruk.env"` | **Navn.** En streng i en feilmelding. |

### Ordforråd i kontrakten — navngiving med en kant

`core/contract.py` bruker domeneeksempler i kommentarer og i én
standardverdi:

| Sted | Hva |
|------|-----|
| `contract.py:20` | `# orgnr (9 siffer) eller lokalitetsnummer` |
| `contract.py:21` | `# "selskap" \| "lokalitet"` |
| `contract.py:23` | `# "antall_ansatte", "kapasitet_tonn", "kommune"` |
| `contract.py:91` | `entity_type: str = "selskap"` |
| `contract.py:108, 123` | `{"naeringskoder": ["03.211", ...]}` som eksempel på `utvalg` |

Linje 20, 23, 108 og 123 er **eksempler i kommentarer** — feltet er en
fri streng, og ingen kodesti leser verdien. Linje 21 og 91 er nær en
reell kobling: `entity_type` har ingen enum og ingen validering, men
standardverdien `"selskap"` gjør at en kilde som ikke sier noe blir et
selskap. Det er en antakelse om NÆRINGSLIV, ikke om havbruk, og den er
mykere enn den ser ut — `signals.py:91` matcher på `entity_type` som en
vilkårlig streng og kjenner ingen bestemte verdier.

`utvalg`-formatet er verdt en egen merknad. `core/utvalg.py` sier selv
(linje 31-36) at nøkkelen er kildens og ikke kjernens: modulen kan si
«utvalget ble bredere» uten å vite hva en næringskode er. Skanningen
bekrefter det — `normaliser()`, `er_utvidet()` og `beskriv()` leser
nøkler generisk og har ingen kjennskap til `naeringskoder`.

### Der havbruket faktisk bor

Domenekunnskapen ligger utenfor `core/`, og den er ikke liten:

| Sted | Hva |
|------|-----|
| `rules/segments.yml` | NACE-kode → segment i havbruksverdikjeden, med versjonering |
| `rules/signals.yml` | 24 signalregler over feltnavn som `kapasitet_tonn`, `har_laksefisk` |
| `config.yml` | næringskodelista, endepunkter, per-kilde-terskler |
| `sources/*.py` | 8495 linjer, alt sammen domene |
| `kildeledd.py` | hardkoder `"akvakultur"`, `"sjotemperatur"`, `"biomasse"`, `"lusetall"` (linje 77, 172, 209, 230, 344) |
| `analyse/` | 20 filer |

`kildeledd.py` er den ene modulen utenfor `sources/` som kjenner kilder
ved navn. Den ligger i rota, ikke i `core/`, og importeres ikke av noe i
`core/`.

### Skanningen som ikke ga treff

Følgende ble søkt etter i kode i `core/` og finnes **ikke**: `lokalitet`
som verdi eller nøkkel, `tillatelse`, `produksjonsomraade`/`PO`,
`biomasse`, `art`, `merd`, `MTB`, `trafikklys`, `laks`, `fisk`, `tonn`,
`kommune`, `naeringskode`. Alle forekomster av disse ordene i `core/` er
i docstrings og kommentarer, der de opptrer som eksempler eller som
referat av målinger — ordrikt, men uten kodekobling.

### Kadens er en antakelse, havbruk er det ikke

Det `core/` faktisk forutsetter er en **ukentlig rytme**, ikke en
bransje:

- `contract.py:186` — `min_dager_mellom: int = 7`
- `core/feltnormal.py` og `core/health.py` regner nullstrekk i *uker*;
  `STANDARD_MAKS_NULLSTREKK = 13` er simulert over 761 uker lusetall
- `core/health.py:95` — `STANDARD_MIN_ANDEL = 0.90`, uttrykkelig ikke
  målt mot reell ukesvarians

Tallene er kalibrert på havbrukskilder, men størrelsen de måler
(«hvor lenge siden sist», «hvor mye av normalen kom») er bransjeløs.
En kilde med daglig kadens ville trenge andre tall, ikke annen kode —
og begge er overstyrbare per kilde i `config.yml`.

---

## (b) Hva har hver kilde kostet?

### Definisjoner

- **Commits til grønn**: antall commits på `main` fra den første commiten
  som legger til kildefila, til og med den første der kildens egen test
  passerer. Målt ved å sjekke ut hver commit i et arbeidstre og kjøre
  `pytest` der. `1` betyr at fila og en grønn test kom i samme commit.
- **Linjer i kildefila**: `wc -l` på fila ved introduksjonen og i dag.
- **Linjer endret i `core/`**: i vinduet introduksjon → grønn.

### Tabellen

| Kilde | Intro | Dato | Grønn | Commits | Linjer ved intro | Linjer nå | `core/` i vinduet |
|-------|-------|------|-------|---------:|------:|------:|------:|
| enhetsregisteret | `5fa83aa` | 15.08 | `d4ed4af` (17.08) | 21 | 82 | 484 | 0 \* |
| akvakultur | `5fa83aa` | 15.08 | `7fe4f21` (16.08) | 10 | 76 | 239 | 0 \* |
| lusetall | `67dbe36` | 18.08 | samme | **1** | 239 | 226 | **0** |
| sjotemperatur | `75e35ce` | 25.08 | samme | **1** | 411 | 413 | **0** |
| biomasse | `ad6c2df` | 25.08 | samme | **1** | 672 | 738 | **0** |
| ekspertgruppen | `4241646` | 27.08 | `e6af220` | 3 | 1652 | 2425 | **0** |
| eierskap | `8e4092d` | 02.09 | samme | **1** | 398 | 659 | **0** |
| romming | `e4b15f3` | 02.09 | samme | **1** | 321 | 321 | **0** |
| trafikklysvedtak | `6e7f5ed` | 05.09 | samme | **1** | 1332 | 1332 | **0** |
| reguleringsomraader | `d415a77` | 09.09 | samme | **1** | 746 | 746 | **0** |
| biomasselag | `dfd9a56` | 14.09 | samme | **1** | 518 | 518 | **0** |

\* De to første er ikke sammenlignbare med resten. `5fa83aa` er
rot-commiten: den SKAPTE `core/` (404 linjer) i samme slag. `akvakultur`
lå der som et deaktivert stillas med `sti: ""` og `aktiv: false`, og
`enhetsregisteret` er kilden maskinen ble bygget rundt. Å si at de
kostet 0 linjer i `core/` er meningsløst — de kostet hele `core/`.

Merknader til de øvrige:

- **ekspertgruppen** er den eneste som ikke var grønn ved introduksjon.
  Commit-meldingen sier det selv: «ARBEIDSLAGRINGSPUNKT … TESTSUITEN ER
  IKKE VERIFISERT». Målt ved utsjekk: 2 feilende, 63 passerende ved
  intro; 69 passerende to commits senere (`e6af220`, «Tre testfeil
  diagnostisert og rettet — to var koden, én var testen»).
- **sjotemperatur** sine 411 linjer er uten `sources/_barentswatch.py`
  (210 linjer), som ble trukket ut av lusetall i samme commit. Uttrekket
  gjorde `lusetall` 13 linjer mindre enn den var.

### Nullet i `core/`-kolonnen er ekte, og det er større enn tabellen viser

`core/` er ikke rørt siden `557df2b`, 02.09.2026 — **de siste 30
commitene**. I det vinduet kom fire kilder inn: `romming` (02.09),
`trafikklysvedtak` (05.09), `reguleringsomraader` (09.09) og
`biomasselag` (14.09), til sammen 2917 linjer i `sources/`. Null linjer
i `core/`.

Årsaken ser man i importene. Hver eneste kilde importerer nøyaktig det
samme fra kjernen, og ingenting mer:

```
core.config          → get
core.contract        → Observation, Source
sources              → _http  (eller _barentswatch)
```

To kilder importerer i tillegg `core.persondata`: `enhetsregisteret` og
`eierskap`, begge fordi de henter fra Brreg. Ingen kilde importerer
`diff`, `snapshot`, `health`, `changelog`, `signals`, `feltnormal`,
`utvalg`, `predictions`, `raw`, `registry`, `runner`, `paths` eller
`miljo`.

### Men: kilder har forandret `core/` ETTER at de ble grønne

Vinduet «intro → grønn» fanger ikke alt. Av de 42 commitene som har rørt
`core/`, er 15 sporbare til en bestemt kilde, ut fra commit-meldingenes
egen begrunnelse:

| Kilde | Linjer i `core/` etter grønn | Commits |
|-------|------:|---------|
| lusetall | 880 | `fe2ecac` F4 frekvensvakt · `2156706` gjelder_for · `c52cadf` prediksjonsvindu · `98aed0e` feltnormal/innhold · `65bbf9f` utvalgets tre tilstander · `6d3dbcd` exit-kode |
| biomasse | 868 | `adcf440` revisjonsaksen · `18d7a47` published_at · `2c93654` F14 løpenummer |
| enhetsregisteret | 718 | `ac68b78` utvalgsutvidelse · `04eb4dc` ENK i kilden · `88fde04` ENK ved lesing · `761e6e2` skjemautvidelse |
| sjotemperatur | 171 | `cf0421a` changelog på (kilde, dato) — F11 |
| eierskap | 40 | `557df2b` `infer_schema_length=None` i `diff` |
| akvakultur | 0 | |
| ekspertgruppen | 0 | |
| romming | 0 | |
| trafikklysvedtak | 0 | |
| reguleringsomraader | 0 | |
| biomasselag | 0 | |
| **Sum** | **2677** | |

De resterende 27 core-commitene er rammeverksarbeid uten én kilde som
utløser: volumvakt, prediksjonslogg, signalreglenes grammatikk,
append-only i `write()`, rå-arkivet, miljøvariabelkontrollen.

To ting er verdt å lese ut av den tabellen.

**Den faller.** Ordnet etter når kilden kom inn: 718 (15.08), 880
(18.08), 171 (25.08), 868 (25.08), 0, 40 (02.09), 0, 0, 0, 0, 0. De to
siste kildene som utløste noe i `core/` var `biomasse` (25.08) og
`eierskap` (02.09), og `eierskap` kostet 40 linjer. De seks siste
kildene har utløst null.

**Hva de utløste er ikke kildespesifikt.** Ingen av de 2677 linjene
legger en kilde inn i kjernen. De legger et SKILLE inn i kjernen som
kilden var den første til å trenge:

- `biomasse` er den første kilden som reviderer fortiden → `diff.revisjon()`
- `biomasse` er den første kroppen hentet fra et arkiv → `published_at`
- `sjotemperatur` er den andre kilden med samme etterslep som en annen →
  changelog-nøkkelen ble `(kilde, dato)`
- `lusetall` er den første kilden med etterslep → `gjelder_for()`
- `enhetsregisteret` er den første kilden med et utvalg → `utvalg`
- `eierskap` er den første kilden med disjunkte entitetssett mellom
  nabosnapshots → skjemautledningen i `diff` leste bare 100 rader

`eierskap`-tilfellet er det reneste eksempelet på formen. Testene var
grønne ved introduksjon; feilen lå latent i `diff.compare()` og hadde
aldri fyrt fordi hver eksisterende kilde blander `ny`, `endret` og
`borte` innenfor de første hundre radene. Commiten sier det selv:
«Feilen lå i skjemautledningen, ikke i dataene.» Kilden avdekket et
rammeverksproblem — den krevde ikke en tilpasning.

### Faller linjetallet i kildefila? Nei.

| Rekkefølge | Kilde | Linjer nå |
|---|---|---:|
| 1 | enhetsregisteret | 484 |
| 2 | akvakultur | 239 |
| 3 | lusetall | 226 |
| 4 | sjotemperatur | 413 |
| 5 | biomasse | 738 |
| 6 | ekspertgruppen | 2425 |
| 7 | eierskap | 659 |
| 8 | romming | 321 |
| 9 | trafikklysvedtak | 1332 |
| 10 | reguleringsomraader | 746 |
| 11 | biomasselag | 518 |

Ingen trend nedover. Det henger ikke sammen med rammeverkets modenhet,
men med hva kilden må gjøre for å komme fra en HTTP-respons til
`Observation`-objekter:

| Kilde | Form | Linjer | `def` |
|-------|------|------:|------:|
| lusetall | JSON-API, én uke per kall | 226 | 10 |
| akvakultur | JSON-API, feltkart i config | 239 | 11 |
| romming | JSON-API per år | 321 | 7 |
| sjotemperatur | CSV | 413 | 10 |
| enhetsregisteret | JSON-API, paginert, ENK-filter | 484 | 14 |
| biomasselag | JSON-API + kobling mot akvakultur | 518 | 11 |
| eierskap | JSON-API, to endepunkt koblet | 659 | 15 |
| biomasse | CSV, revisjonskilde | 738 | 18 |
| reguleringsomraader | JSON/geodata | 746 | 19 |
| trafikklysvedtak | Forskriftstekst, regex over lovdata | 1332 | 33 |
| ekspertgruppen | PDF, seks overlappende rapporter | 2425 | 58 |

De to største er de to som leser fritekst. `ekspertgruppen` henter ut
kategorier fra PDF-rapporter der `published_at` må leses fra PDF-ens
`/CreationDate` fordi `Last-Modified` er en CMS-migreringsdato;
`trafikklysvedtak` leser fire kapasitetsjusteringsforskrifter på
lovdata.no. Det er kildenes format som koster, ikke maskinen.

Nesten halvparten av linjene er dessuten ikke kode:

| Kilde | Totalt | Kode | Kommentar/docstring | Andel |
|-------|------:|-----:|-----:|-----:|
| ekspertgruppen | 2425 | 1128 | 1055 | 44 % |
| trafikklysvedtak | 1332 | 584 | 616 | 46 % |
| reguleringsomraader | 746 | 360 | 310 | 42 % |
| biomasse | 738 | 294 | 375 | 51 % |
| eierskap | 659 | 280 | 323 | 49 % |
| biomasselag | 518 | 228 | 241 | 47 % |
| enhetsregisteret | 484 | 226 | 196 | 40 % |
| sjotemperatur | 413 | 181 | 194 | 47 % |
| romming | 321 | 163 | 127 | 40 % |
| akvakultur | 239 | 137 | 60 | 25 % |
| lusetall | 226 | 112 | 83 | 37 % |
| **Sum** | **8495** | **3856** | | |

Målt i kode er den største kilden 1128 linjer, ikke 2425, og
mediankilden er 226.

### Der kontrakten faktisk vokser: `backfill.py`

`core/` står stille, men `backfill.py` (1513 linjer) gjør ikke det. Tre
kilder utvidet den ved introduksjon:

| Kilde | Intro-commit | `backfill.py` |
|-------|------|------:|
| biomasse | `ad6c2df` | +189 / −5 |
| ekspertgruppen | `4241646` | +203 / −5 |
| romming | `e4b15f3` | +138 / −0 |
| reguleringsomraader | `d415a77` | +1 / −1 |

Mekanismen er fem valgfrie metoder som `backfill.py:main()` sjekker med
`hasattr`:

| Metode | Strategi | Kilder som har den |
|--------|----------|--------------------|
| `hent_uke` | inline i `main()` | lusetall, sjotemperatur |
| `hent_alt` | `_backfill_maaneder` | biomasse |
| `utgivelser` | `_backfill_rapporter` | ekspertgruppen, trafikklysvedtak |
| `aar_i` | `_backfill_hendelser` | ekspertgruppen, romming, trafikklysvedtak |
| `overforinger` | `_backfill_overforinger` | eierskap |

**Ingen av de fem er nevnt i `core/contract.py`.** Skanningen fant ett
treff på ordet `hent_uke` der, og det er en kommentar om noe annet
(linje 130, om `utvalg`). Det er en andre kildekontrakt som vokser
uregulert utenfor den dokumenterte.

`backfill.py` hardkoder til gjengjeld ingen kildenavn — 0 treff på de
elleve navnene. Dispatchen går på evne, ikke på identitet, og en ny
kilde som passer en av de fem strategiene koster fortsatt null linjer
der. `reguleringsomraader` og `biomasselag` er begge i den situasjonen.
