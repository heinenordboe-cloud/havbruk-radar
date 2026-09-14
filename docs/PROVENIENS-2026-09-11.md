# Proveniensrevisjon 11.09.2026

> **Oppdatert 12.09.2026.** EKSTERN-kategorien er lukket. Sju kropper er
> arkivert, og de elleve påstandene som hvilte på dem er målt for første
> gang. Klassifiseringene under er de nye; «var EKSTERN» markerer hver
> rad som flyttet seg. Tellingen før og etter står nederst.

Én rad per påstand i de fire dokumentene under. Formålet er å skille det
som kan kjøres på nytt mot en arkivert kropp fra det som bare er skrevet
ned.

    MÅLT      kan kjøres mot en kropp i arkivet, og er kjørt
    MÅLBAR    kunne måles mot arkivet, men er ikke kjørt
    EKSTERN   hviler på en kropp som IKKE er i arkivet
    UBELAGT   ingen kropp å måle mot i det hele tatt

## Hva som ble arkivert 12.09.2026

Alle fem pressemeldingene ble hentet via Internet Archive med `id_`, på
nøyaktig de avtrykkene `VERIFISERING-PRESSEMELDINGER.md` dokumenterer.
**Alle fem sha256 og alle fem bytetall stemmer eksakt med de
dokumenterte verdiene.** Ingen kropp har endret seg.

| kropp | sti | byte | sha256 (16) | `published_at` | Memento-avstand |
|---|---|---|---|---|---|
| pm 30.10.2017 | `regjeringen-pressemeldinger/2017-10-30` | 52 013 | `896b9570c2d91346` | 2017-10-30 | **430 d** |
| pm 04.02.2020 | `…/2020-02-04` | 58 646 | `f02cd9a1494e908b` | 2020-02-04 | **368 d** |
| pm 07.06.2022 | `…/2022-06-07` | 58 792 | `637168e536c51114` | 2022-06-07 | 0 d |
| pm 06.03.2024 | `…/2024-03-06` | 57 118 | `c5681d286a37cf49` | 2024-03-06 | 0 d |
| pm 19.06.2026 | `…/2026-06-19` | 66 197 | `b804dafd845a9908` | 2026-06-19 | 54 d |
| høringsnotat 19.06.2026 | `regjeringen-horing/2026-06-19` | 445 534 | `afdc0345b23b97f5` | 2026-06-19T14:49:41 | 43 d |
| Meld. St. 16 (2014–2015) | `stortingsmeldinger/2015-03-20` | 5 446 269 | `4cdbfbf57f21830d` | 2015-03-20T06:21:04 | 2498 d |

`published_at` for pressemeldingene er LEST av kroppens eget «Dato:»-felt,
ikke av en header og ikke av Memento-stemplet (1b-7). For de to PDF-ene er
den lest av `/CreationDate`.

**Ett forbehold kartleggingen av pressemeldingene ikke nevnte:**
`VERIFISERING-PRESSEMELDINGER.md` advarer om at 2020- og 2026-avtrykkene
ligger «ett år og to måneder» etter utgivelsen. Målt er de 368 og 54
dager — men **2017-avtrykket ligger 430 dager etter, og det er det
største spriket av alle fem.** Det sto ikke i forbeholdet. 2017-kroppen
er også den som bærer PO7-avviket og den konservative regelen.

### To adresser måtte finnes, og den ene kom ut av arkivet selv

Pressemeldingenes sluger sto ikke i noe dokument; de ble funnet med
Waybacks CDX-indeks, filtrert på id-nummeret. Adressen til Meld. St. 16
(`/no/dokumenter/meld.-st.-16-2014-2015/id2401865/`) ble funnet som en
lenke **inne i pressemeldingen 04.02.2020**, altså i en kropp som var
arkivert få minutter i forveien.

**Stortinget ble forsøkt først, som oppgaven ba om.** Stortinget svarer
200 og er ikke bak Cloudflare, men Meld. St. 16 lot seg ikke hente
derfra: «Lesevisning»-sida for `p=2014-2015&paperid=1-16` er et
React-skall på 7 kB uten lenker, søkesida er JS-drevet, og fire
PDF-mønstre ga 404. Kroppen er derfor departementets egen PDF via
Wayback — samme utgiver, og den som faktisk bærer tabellen.

## 1. `docs/KARTLEGGING-STYRINGSGRUPPEN.md`

| # | påstand | klassifisering | kropp |
|---|---|---|---|
| 1.1 | Ti rapporter, elleve kropper; sha256 og bytetall per kropp | **MÅLT** | alle 11 i `styringsgruppen/` |
| 1.2 | Sidetall per kropp (4, 11, 12, 13, 13, 14, 16, 22, 14, 18) | **MÅLT** | alle 11 |
| 1.3 | `published_at` fra `/CreationDate`, ti verdier | **MÅLT** | alle 11 |
| 1.4 | Produsentstrengene (Xerox, Konica, Word, Adobe) | **MÅLT** | alle 11 |
| 1.5 | `Last-Modified` per vert; NVA-batch innenfor fem sekunder | **MÅLT** (header lagret i hentelogg 10.09) | headere, ikke kropp |
| 1.6 | De to 2017-kroppene har intet tekstlag (0 tegn) | **MÅLT** | 2017 mai, 2017 sept |
| 1.7 | 2018 Tabell 1: 13 rader, kolonneoverskrifter ordrett | **MÅLT** | 2018 |
| 1.8 | 2018 `Råd 2017 For 2016–2017`: PO 2, 4, 6, 7 spriker, verste av to | **MÅLT** | 2018 |
| 1.9 | 2018-2019 Tabell 3: PO 2, 3, 4, 5, 7, 10 spriker, verste av to | **MÅLT** | 2018-2019 |
| 1.10 | Sammenslåingsregelen ordrett («lik vekting», «konservativ tilnærming») | **MÅLT** | 2018-2019 |
| 1.11 | Ingen sammenslåing i 2020–2025; «oddetallsår» forsvinner etter 2019 | **MÅLT** | 2020–2025 |
| 1.12 | 2021 har tre tabeller, omtaler både 2020 og 2021, slår ikke sammen | **MÅLT** | 2021 |
| 1.13 | Kolonneoverskrifter ordrett for 2020, 2021, 2022, 2023, 2024, 2025 | **MÅLT** | de seks |
| 1.14 | U+2012 figurstrek i `10‒30 %`, én forekomst i 2022 og 2023 | **MÅLT** | 2022, 2023 |
| 1.15 | Prosagjentakelse: 13 treff 2018–2024, null i 2025 | **MÅLT** | 2018–2025 |
| 1.16 | Formskiftet `Produksjonsområde N` → `PON` i 2023 | **MÅLT** | 2023 |
| 1.17 | UO-stempel i nøyaktig 2018-2019 og 2020 | **MÅLT** | alle 9 med tekst |
| 1.18 | 2025 Tabell 8: 13 rader, ingen PO endrer kategori 2024→2025 | **MÅLT** | 2025 |
| 1.19 | De to 2022-kroppene har identisk tekst (30 046 tegn), to sha256 | **MÅLT** | 2022 ×2 |
| 1.20 | 2024 PO9 `Lav-Moderat` mot 2025-kroppens `Moderat (11)` | **MÅLT** | 2024, 2025 |
| 1.21 | Steg 3: tabell mot prosaliste, 0 uenigheter i åtte parringer (65 celler) | **MÅLBAR** | 2018–2024 |
| 1.22 | 2024-kroppens ordmellomrom er et layout-artefakt | **MÅLT** | 2024 |
| 1.23 | `Områdene?`-feilen og de ombrukne tabellradene (to feilspor) | **MÅLBAR** | 2018 |
| 1.24 | Wayback: Memento-avstand 54 / 416 / 188 dager | **MÅLT** (header) | headere |
| 1.25 | Brage/`brage.nina.no` er avviklet; NVA har fire årganger | **EKSTERN** | et DNS-oppslag og et søkeresultat; ingen kropp å arkivere |
| 1.26 | regjeringen.no svarer 403 for vår klient | **EKSTERN** | en HTTP-status er en hendelse, ikke en kropp; bekreftet på nytt 12.09 |

## 2. `docs/MALING-RAD-MOT-EKSPERTVURDERING.md`

| # | påstand | klassifisering | kropp |
|---|---|---|---|
| 2.1 | De 26 cellene, parring 2024 og 2025, strenger ordrett | **MÅLBAR** | eg2024, eg2025, sg2024, sg2025 |
| 2.2 | Parring 2024\* (revidert), 13 celler | **MÅLBAR** | eg2025 T6.1, sg2025 T8 |
| 2.3 | Én AVGJORT-celle i alt: PO9 i 2025 | **MÅLT** | eg2025, sg2025 |
| 2.4 | eg2024 T6.1 PO9 = `Lav–Moderat*` | **MÅLT** | `ekspertgruppen/2024-12-31` |
| 2.5 | eg2025 T6.3 PO9 = `Lav–Moderat*`, `Like sannsynlig som ikke` | **MÅLT** | `ekspertgruppen/2025-12-31` |
| 2.6 | eg2025 T6.1 (oppdatert 2024) PO9 = `Moderat` | **MÅLT** | `ekspertgruppen/2025-12-31` |
| 2.7 | sg2025 Tabell 8 PO9 = `Moderat (11)` / `Moderat (10)*` | **MÅLT** | `styringsgruppen/2025-11-21` |
| 2.8 | Fotnotene i begge kropper, ordrett | **MÅLBAR** | eg2025, sg2025 |
| 2.9 | Medianregelen hos ekspertgruppen, ordrett | **MÅLBAR** | eg2024, eg2025 |
| 2.10 | Styringsgruppens regel: medianverdi lik 10 % → moderat | **MÅLT** | sg2025 |
| 2.11 | Hjemmelen: Meld. St. 16 (2014–15) tabell 10.1 sier det regelen påberoper | **MÅLT** *(var UBELAGT)* | `stortingsmeldinger/2015-03-20` `4cdbfbf57f21830d` — se «Tabell 10.1» |
| 2.12 | Aggregatvakt 2025: 1 høy (PO3), 9 moderat, 3 lav (PO1, 12, 13) | **MÅLT** (verdien) | sg2025 T8 |
| 2.13 | …at departementets høringsnotat 19.06.2026 oppgir samme aggregat | **MÅLT** *(var EKSTERN)* | `regjeringen-horing/2026-06-19` `afdc0345b23b97f5` — tallene stemmer |
| 2.14 | Aggregatvakt for 2024 finnes ikke i noen kropp | **MÅLBAR** | de fire kroppene |
| 2.15 | Strukturvakt: 13 rader i alle sju tabeller | **MÅLBAR** | de fire kroppene |
| 2.16 | Kroppens egen aggregatpåstand: «kun tre … i lav kategori» | **MÅLT** | sg2025 |
| 2.17 | Femte kontroll: to uttrekk gir identiske strenger i 12 av 13 | **MÅLBAR** | eg2024, sg2024 |
| 2.18 | Pressemeldingens tre påstander om PO9 | **MÅLT** *(var EKSTERN)* | `…/2026-06-19` `b804dafd845a9908` — ordrett bekreftet |
| 2.19 | Dokumentet sier selv: «Pressemeldingen selv er ikke lest» | — | dokumentets eget forbehold, står ved lag |
| 2.20 | `Moderat (10)` er avrundet; underliggende median ukjent | **UBELAGT** | tallet finnes ikke i noen kropp; bare ekspertgruppen kan svare |
| 2.21 | Formen `Lav–Moderat*` er ikke i bruk før 2024 | **MÅLBAR** | eg2017–eg2023 |

## 3. `docs/beslutninger/2026-09-09-styringsgruppens-rad-som-kilde.md`

| # | påstand | klassifisering | kropp |
|---|---|---|---|
| 3.1 | Formattabellen (år omtalt, PO-tabell, sammenslått råd, prosa, format) | **MÅLT** | alle 11 |
| 3.2 | Åtte av ti kropper er maskinlesbare | **MÅLT** | alle 11 |
| 3.3 | Sammenslåingsregelen, sitert ordrett | **MÅLT** | 2018-2019 |
| 3.4 | Regelen etterprøvd på ti av ti sprikende områder | **MÅLT** | 2018, 2018-2019 |
| 3.5 | Fra 2020 finnes verken kolonnen eller regelen | **MÅLT** | 2020–2025 |
| 3.6 | 2021 er oddetallsår og har begge grunnlagsår, men slår ikke sammen | **MÅLT** | 2021 |
| 3.7 | Premisset om mandatoverskridelse er målt og forkastet (26 celler) | **MÅLBAR** | de fire kroppene |
| 3.8 | Over 2020–2024 er sg enig med eg i alle 65 celler | **MÅLBAR** | sg2020–sg2024 |
| 3.9 | «Vi mener derfor» er en tolkning, ikke en gitt prosedyre | **MÅLT** 11.09 | mandatet, se Del A |
| 3.10 | Departementet 06.03.2024: «Fargeleggingen følger direkte av handlingsregelen…» | **MÅLT** *(var EKSTERN)* | `…/2024-03-06` `c5681d286a37cf49` — ordrett |
| 3.11 | Aggregatvakt fra høringsnotatet 19.06.2026 | **MÅLT, MED AVVIK** *(var EKSTERN)* | `regjeringen-horing/2026-06-19` — tallene ja, PO-ene NEI, se «Avvik 2» |
| 3.12 | Pressemeldinger finnes for alle fem runder, med grunnlagsår 2016+2017 … 2024+2025 | **MÅLT** *(var EKSTERN)* | alle fem; årsparene lest av hver kropp |
| 3.13 | `grunnlagsaar` trengs som eget felt | — | konstruksjonsvalg, ikke en påstand om verden |

## 3b. Styringsgruppens ØVRIGE dokumenter — nytt 12.09.2026

Ti dokumenter arkivert 12.09.2026 i `data/arkiv/styringsgruppen-ovrige/`
og `data/arkiv/styringsgruppen-mandater/`. Radene under er nye påstander
som følger av dem.

| # | påstand | klassifisering | kropp |
|---|---|---|---|
| 3.14 | Ingen av de ti øvrige dokumentene har en sammenslått kategori per PO over to år | **MÅLT** | alle ti |
| 3.15 | Trendgruppen (Vollset mfl., des. 2021) anbefaler «på det sterkeste» lik vekting av de to årene | **MÅLT** | `…-ovrige/2022-12-09.5` `abed47187f26d966` |
| 3.16 | Styringsgruppen slutter seg til at «begge årene bør derfor sees under ett» (31.08.2022) | **MÅLT** | `…-ovrige/2022-12-09.4` `c6c6e3c4d5f11bf7` |
| 3.17 | …men setningen er en metodisk advarsel om LESING, ikke en regel for å sette et sammenslått råd | **MÅLT** | samme kropp, avsnittets kontekst |
| 3.18 | 2018-mandatet har «oddetallsår» og «kapasitetsjusteringer» | **MÅLT** | `…-mandater/2018-06-26` `24b97d153ed5baec` |
| 3.19 | 2020-mandatet har ingen av dem, og har «fargelegging» i stedet | **MÅLT** | `…-mandater/2020-05-18` `418f1f90cc79fa43` |
| 3.20 | Mandatrevisjonen er datert 18.05.2020 (`/CreationDate` 12:14 på begge filer) | **MÅLT** | begge 2020-filene |
| 3.21 | Kroppenes sitat av 2020-mandatet utelater ordet «sammen» | **MÅLT** | mandatet mot sg2020–sg2024 |
| 3.22 | 2020-mandatet skapte oppdragsklausulen de øvrige dokumentene leveres under | **MÅLT** | `…-mandater/2020-05-18` |
| 3.23 | Myklebust mfl. 2024 sier ingenting om rådsform (bare målt på ordlista) | **MÅLT, AVGRENSET** | `…-ovrige/2024-04-30.2` `0ae12e44bcef5755` |
| 3.24 | Brage (`brage.nina.no`) er avviklet — bekreftet på nytt | **MÅLT** | DNS + to klienter, se § 3c |

### Advarsel om arkivdatoene i `styringsgruppen-ovrige/`

`/CreationDate` er **ikke** utgivelsesdato for fem av kroppene der. Fire
er re-eksportert i samme batch 09.12.2022, og filnavnene arver den.
Kroppenes egne kolofondatoer, lest av side 1–3:

    2022-12-09.bin.gz     Thorstad mfl., kriterier vekting     28.06.2021
    2022-12-09.2.bin.gz   SG råd vekting                       06.07.2021
    2022-12-09.3.bin.gz   SG råd heterogenitet                 31.05.2021
    2022-12-09.4.bin.gz   SG råd årlig variasjon               31.08.2022
    2022-12-09.5.bin.gz   Trendgruppen/Vollset mfl.       des. 2021
    2024-04-30.2.bin.gz   Myklebust mfl.                       09.04.2024

Filene står som de står — regel 2 — og `raw_hash` er innholdsadressert,
så ingen påstand peker feil. Men **en framtidig kilde må lese
kolofondatoen, ikke `/CreationDate`, for disse seks.** Mandatfilene og de
to 2024-filene er derimot pålitelige.

## 3c. Brage-konklusjonen fra 09.09 er etterprøvd og STÅR

Kartleggingen 09.09 konkluderte med at `brage.nina.no` er avviklet. Et
søketreff 11.09 så ut til å motsi det. Målt 12.09.2026:

    host brage.nina.no      -> alias for brage.unit.no
    host brage.unit.no      -> ingen adresse
    curl https://brage.nina.no/...  -> 000, ingen tilkobling
    WebFetch (annen klient)         -> getaddrinfo ENOTFOUND

Treffet 11.09 var søkemotorens indeks, ikke en levende tjeneste.
**09.09-konklusjonen var riktig, og fire-vert-bildet står.**

Én presisering den gangen ikke hadde: handlene oppfører seg ULIKT.
Publikasjonshandler (`11250/3104585`, `3132111`, `3167955`) 302-er til
NVA og virker. Samlingshandelen `11250/2788898` 302-er til
`brage.nina.no` og er en blindvei. Samlingen «Trafikklyssystemet i
havbruk» finnes bare som Wayback-kopi; innholdet er migrert til NVA og
lot seg hente derfra.

## 4. `docs/beslutninger/2026-09-09-departementets-po9-begrunnelse.md`

| # | påstand | klassifisering | kropp |
|---|---|---|---|
| 4.1 | Departementets PO9-begrunnelse, sitert ordrett | **MÅLT** *(var EKSTERN)* | `…/2026-06-19` — sitatet stemmer tegn for tegn |
| 4.2 | «moderat påvirket i 2024» er sann bare om den reviderte versjonen | **MÅLT** (kroppssiden) | eg2024, eg2025 |
| 4.3 | «like sannsynlig lav som moderat i 2025» stemmer | **MÅLT** (kroppssiden) | eg2025 T6.3 |
| 4.4 | «styringsgruppens råd … moderat også i 2025» stemmer | **MÅLT** (kroppssiden) | sg2025 T8 |
| 4.5 | 2025-rapportens egen setning om oppdateringen av PO9 | **MÅLBAR** | eg2025 |
| 4.6 | sg2024 førte tvetydigheten videre uendret | **MÅLT** | sg2024 |
| 4.7 | `diff.revisjon()` skrev 14 revisjonsrader til `2024-12-31.2.parquet` | **MÅLBAR** | `data/raw/ekspertgruppen/` |
| 4.8 | Departementets fire lister over sprikende områder (2020, 2022, 2024, 2026) | **MÅLT** *(var EKSTERN)* | de fire kroppene; se «Avvik 1» om PO-numrene i 2020 |
| 4.9 | Bare runde 2018 har et målt avvik fra rådet | **MÅLT** *(var EKSTERN)* | alle fem; bare 2017-kroppen sier det uttrykkelig — men taushet er ikke bevis |
| 4.10 | Wayback-avtrykkene av 2020- og 2026-meldingene ligger ett år / to måneder etter | **MÅLT, UFULLSTENDIG** *(var EKSTERN)* | 368 og 54 dager — men 2017 ligger 430 dager unna og var ikke nevnt |
| 4.11 | Skillet sprikende ≠ avvik fra rådet | — | tolkning av 4.8, som nå er MÅLT |
| 4.12 | **NY:** PO7 2018-runden — råd moderat, vedtak grønt, samfunnsøkonomisk begrunnet, statsråd navngitt | **MÅLT** | `…/2017-10-30` `896b9570c2d91346` |
| 4.13 | **NY:** den konservative regelen med betingelsen «usikkerheten er middels eller høy» | **MÅLT** | `…/2017-10-30`; betingelsen finnes ikke i noen styringsgruppekropp, se «Avvik 3» |

---

## Hva målingen ga

Ni av elleve EKSTERN-påstander er bekreftet ordrett. Tre avvik står igjen,
og de er avvik i REPOETS gjengivelse, ikke i kroppene.

### Tabell 10.1, ordrett — og hva den ikke sier

`stortingsmeldinger/2015-03-20`, side 60:

> **Tabell 10.1 Grenseverdier for lakselusindikator.**
>
> | Lav risiko/påvirkning | Moderat risiko/påvirkning | Høy risiko/påvirkning |
> |---|---|---|
> | Det er sannsynlig at **< 10 prosent** av populasjonen dør pga. luseinfeksjon. | Det er sannsynlig at **10 – 30 prosent** av populasjonen dør pga. luseinfeksjon. | Det er sannsynlig at **> 30 prosent** av populasjonen dør pga. luseinfeksjon. |

Styringsgruppens 2025-kropp gjengir den slik: «kategorien lav er mindre
enn 10 % og … kategori moderat er fra og med 10 % til og med 30 %».

**Første ledd står ordrett i tabellen** (`< 10 prosent`). **Andre ledd
gjør det ikke:** frasen «fra og med» forekommer **null ganger i hele
meldingen**, og tabellen skriver bare `10 – 30 prosent` uten å si om
endepunktene er med.

Men gjengivelsen er likevel riktig, og den er **framtvunget av tabellen
selv**: når lav er `< 10` og høy er `> 30`, tilhører verdiene 10 og 30
ingen av dem. Skal de tre kategoriene dekke skalaen, må moderat være
lukket i begge ender. Styringsgruppens lesning er den eneste som ikke
etterlater et hull.

Formen deres er dessuten ærlig: «forstår … som» og «Vi mener derfor»
merker det som en tolkning. **Hjemmelen holder** — med det presiseringen
at inklusiviteten er utledet av notasjonen, ikke sitert fra teksten.

### Avvik 1 — de seks områdene i 2020 er navngitt, ikke nummerert

Pressemeldingen 04.02.2020, under mellomtittelen **«Områder med endring
fra 2018 til 2019»**, navngir seks områder: Ryfylke, Nord-Trøndelag med
Bindal, Karmøy til Sotra, Andøy til Senja, Nordhordland til Stadt og
Stadt til Hustadvika. Det er PO 2, 7, 3, 10, 4 og 5.

**Listen stemmer** — men PO-numrene er VÅR oversettelse. Kroppen oppgir
dem ikke. De tre andre rundene oppgir numrene selv: «Ryfylke (PO2),
Nordhordland til Stadt (PO4) og Stadt til Hustadvika (PO5)» (2022),
«Nordhordland til Stadt (PO4) og Helgeland til Bodø (PO8)» (2024),
«Vestfjorden og Vesterålen (PO9)» (2026).

Merk kryssjekken: de seks navnene departementet oppgir for 2018/2019 er
nøyaktig de seks PO-ene jeg målte i styringsgruppens egen Tabell 3
(PO 2, 3, 4, 5, 7, 10). To organisasjoner, to dokumenter, samme seks.

### Avvik 2 — aggregatvakten er bare halvt uavhengig

`MALING` skriver: «Fra departementets høringsnotat 19.06.2026: 1 høy, 9
moderat, 3 lav, **med høy i PO3 og lav i PO1, PO12 og PO13**.»

Høringsnotatet sier, ordrett:

> «Styringsgruppens vurdering for 2025, viser at det i 2025 er ett
> produksjonsområde som vurderes til høy påvirkning, ni
> produksjonsområder vurderes til moderat påvirkning, og tre
> produksjonsområder vurderes til lav påvirkning.»

**Tallene stemmer. Områdene står ikke der.** Notatet nevner verken PO3,
PO1, PO12 eller PO13, og fordeler ingen farger per område — det er
kontrollert mot hele kroppen.

PO-identitetene må altså ha kommet fra kroppen vakten skulle kontrollere
(sg2025 Tabell 8). En vakt er bare en vakt så langt den er uavhengig av
det den vokter. **Tallmengden 1/9/3 er en ekte ekstern kontroll; hvilke
områder det gjelder er det ikke.**

### Avvik 3 — departementets versjon av den konservative regelen har en betingelse kildene ikke har

Pressemeldingen 30.10.2017, ordrett:

> «Styringsgruppen har ut i fra ekspertgruppens rapport gjort en samlet
> vurdering av lakselusindusert dødelighet for laks i perioden 2016-2017.
> Styringsgruppens råd er basert på lik vekting av årene. Der
> vurderingene er forskjellig for et område i de to årene **og
> usikkerheten er middels eller høy**, har styringsgruppen valgt en
> konservativ tilnærming. Dette innebærer konkret at det er det året med
> høyest risiko for luseindusert dødelighet som har blitt førende for
> rådet.»

Styringsgruppens egen 2018-2019-kropp har INGEN slik betingelse:

> «Der ekspertgruppens vurderinger for kategori av dødelighet for et
> område er forskjellig i 2018 og 2019 har styringsgruppen, på lik måte
> som for rådet avgitt i 2017, valgt en konservativ tilnærming …»

Betingelsen er altså departementets tilføyelse, eller en muntlig
presisering som aldri nådde rapporten. **Og den er aldri satt på prøve.**
Målt i 2018-kroppens Tabell 1 er usikkerheten for de fire sprikende
områdene `Stor` (PO2), `Middels` (PO4), `Stor` (PO6) og `Middels` (PO7).
Alle fire oppfyller betingelsen, så den utelukker ingenting. Det finnes
ikke ett tilfelle i noen kropp der kategoriene spriker og usikkerheten er
`Liten`.

### PO7 — bekreftet i sin helhet, statsråden navngitt

> «- Min vurdering er i hovedsak den samme som rådene fra styringsgruppen,
> men etter en helhetlig vurdering har jeg valgt å sette produksjonsområde
> 7 til grønt. Jeg mener at lusepåvirkningen i området ligger innenfor et
> akseptabelt risikonivå og at dette kan underbygges av gode faglige
> vurderinger, sier fiskeriminister Sandberg.»

> «-Bildet som tegnes i ekspertgruppens rapport gir meg tro på at den gode
> utviklingen i produksjonsområde 7 er en trend som vil vare. Det er lagt
> vekt på at **de positive samfunnsøkonomiske konsekvensene er vurdert til
> å være betydelig større enn de negative**, sier Sandberg»

Vedtaket i samme kropp: «Regjeringen har besluttet at 8
produksjonsområder settes til grønt (produksjonsområdene 1 og 7-13) …».
Ekspertgruppens grunnlag, også i kroppen: «moderat i 2016 og lav i 2017»
for PO7, med usikkerhet «middels» — altså et sprik som etter den
konservative regelen gir moderat.

Kroppen er den eneste av de fem som uttrykkelig sier at departementet gikk
mot rådet. De fire andre inneholder ingen slik formulering — men de sier
heller ikke at rådet ble fulgt, så **taushet er ikke belegg for at avvik
ikke fant sted** i de rundene.

## Sammendrag — før og etter

| | 11.09 (før) | etter pressemeldingene | etter styringsgruppe-dokumentene |
|---|---:|---:|---:|
| MÅLT | 41 | **51** | **61** |
| MÅLT, med forbehold | 0 | **2** (3.11, 4.10) | **3** (+3.23) |
| MÅLBAR | 14 | 14 | 14 |
| EKSTERN | **11** | **2** | **2** |
| UBELAGT | 2 | **1** | **1** |
| ikke en påstand om verden | 3 | 3 | 3 |
| **sum** | **71** | **73** | **84** |

Siste kolonne er de elleve radene i § 3b, alle MÅLT (én avgrenset).
EKSTERN-tallet står stille: de to som er igjen er en DNS-feil og en
HTTP-status, og 3.24 legger en MÅLT observasjon ved siden av den ene —
den erstatter den ikke.

De to nye radene er 4.12 (PO7-avviket) og 4.13 (den konservative regelen
med betingelsen), som ikke hadde egne rader før kroppene fantes.

### Det som fortsatt ikke kan måles, og hvorfor

- **1.25 — Brage er avviklet, NVA har fire årganger.** Et DNS-oppslag som
  feiler og et søkeresultat er hendelser, ikke kropper. Det finnes
  ingenting å arkivere; påstanden må kjøres på nytt mot nett for å
  etterprøves.
- **1.26 — regjeringen.no svarer 403.** Samme sak: en HTTP-status er en
  hendelse. Den er bekreftet på nytt 12.09.2026 — Meld. St. 16-sida ga
  403 mens Stortinget ga 200 i samme økt.
- **2.20 — den underliggende medianen bak `Moderat (10)`.** Tallet er
  avrundet i alle fire kroppene, og ingen av dem oppgir om det er 9,96
  eller 10,04. Bare ekspertgruppen kan svare, og skillet er nøyaktig det
  styringsgruppens regel hviler på. Dette er en grense repoet ikke kan
  flytte ved å arkivere mer.

### Hva som nå er sant om departementssiden

Fram til 12.09.2026 hvilte alt repoet påstår om departementets handlinger
på fem kropper som ikke fantes. Nå er alle fem arkiverte, byte for byte
identiske med det som ble dokumentert 09.09, og de ni påstandene som
hvilte på dem er kjørt.

To av dem overlevde ikke uendret: aggregatvakten er bare halvt uavhengig
(Avvik 2), og Wayback-forbeholdet utelot det største spriket — 2017-kroppen
ligger 430 dager fra sitt avtrykk, se «Hva som ble arkivert» øverst.
Rettelsene står her, ikke i de opprinnelige dokumentene, som blir stående
slik de ble skrevet — med den forskjellen at de nå kan etterprøves.
