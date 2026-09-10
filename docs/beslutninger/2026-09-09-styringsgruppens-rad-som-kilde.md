---
dato: 2026-09-09
tittel: Styringsgruppens råd som kilde — og sammenslåingen som forsvant i 2020
status: utkast
commit: [fylles inn]
---

## Hva som ble bestemt

Styringsgruppens råd hentes som en KILDE med samme kontrakt som
ekspertgruppen og trafikklysvedtak: `sources/styringsgruppen.py`, én
uttrekksfunksjon per kropp, rå-arkiv før parse, `published_at` lest av
kroppen.

Kilden bærer **`grunnlagsaar` som eget felt**, ikke bare `observed_at`.

Åtte av ti kropper er maskinlesbare. De to fra 2017 er skann uten
tekstlag og hentes ikke.

**Og — dette er notatets tyngste punkt — kilden gjør ikke spørsmålet
«følger departementet rådet» besvarbart for rundene fra og med 2022.**
Se «Sammenslåingen forsvant, og med den spørsmålet».

## Hvorfor nå

`docs/beslutninger/2026-09-05-vedtakskilden.md` listet dette som ett av
fire reverseringskriterier, med denne begrunnelsen:

> «**Styringsgruppens råd som egen kilde.** Leddet mellom ekspertgruppen
> og departementet er en tredje uttalelse, og
> `analyse/fasit/ekspertgruppen-po-kategori.csv` viser at noen celler
> allerede er hentet derfra for hånd. Uten den kan et avvik mellom
> ekspertgruppen og forskriften ikke plasseres: det kan like gjerne ha
> oppstått i styringsgruppen som hos departementet.»

Kriteriet er utløst. `docs/KARTLEGGING-STYRINGSGRUPPEN.md` (08.09.2026)
lokaliserte og hentet ti kropper og kartla formatet i hver. Dette notatet
avgjør hva som gjøres med dem.

To av de øvrige tre reverseringskriteriene i det notatet er også berørt,
og ett av dem er lukket — se «Hva som er lukket underveis».

## Formen er kartlagt, ikke antatt

Alt under er målt på kroppene, ikke lest ut av en oppsummering. Fullt
belegg i `docs/KARTLEGGING-STYRINGSGRUPPEN.md`.

| kropp | år omtalt | PO-tabell | sammenslått råd | prosagjentakelse | verdiformat |
|---|---|---|---|---|---|
| 2017 mai | — (skann) | — | — | — | — |
| 2017 sept | — (skann) | — | — | — | — |
| 2018 | 2016, 2017, 2018 | ja | **ja** — for 2016–2017 | ja, to former | terskler + kategorinavn |
| 2018-2019 | 2018, 2019 | ja | **ja** — for 2018-2019 | ja, punktliste | terskler |
| 2020 | 2020 | ja | nei | ja, punktliste | kategorinavn + terskler |
| 2021 | 2021 + oppdatert 2020 | ja ×3 | nei | ja, punktliste | kategorinavn + terskler |
| 2022 | 2022 | ja | nei | ja, punktliste | IPCC-ord + kategorinavn + terskler |
| 2023 | 2023 | ja | nei | ja, punktliste | IPCC-ord + kategorinavn + terskler |
| 2024 | 2024 | ja | nei | ja, punktliste | kategorinavn + terskler |
| 2025 | **2024 og 2025** | ja | **nei** — to årskolonner | **nei** | kategorinavn + midtpunktstall |

**Én uttrekksfunksjon per kropp, ikke én generisk parser.** Grunnlaget er
det samme som for ekspertgruppen, og spredningen er om mulig større:
kolonneoverskriftene endrer seg hvert år, konklusjonen flytter fra siste
til andre kolonne mellom 2023 og 2024, `10‒30 %` skifter tegn til U+2012,
`Produksjonsområde N` blir `PON` i 2023, 2024-kroppen mangler ordmellomrom
i tekstlaget, og punktlista forsvinner helt i 2025.

## `grunnlagsaar` er et eget felt, ikke en avledning

CLAUDE.md 1b-3: en verdi som avgjør hva dataene BETYR, lagres SAMMEN med
dem. Prøven er om et snapshot alene kan svare på hva verdien var da raden
ble skrevet.

For denne kilden er svaret nei uten feltet. `observed_at` sier hvilket
tidspunkt raden handler om. Men et råd gjelder ikke alltid ett år:

- 2018-kroppens `Råd 2017 For 2016–2017` gjelder **to** år.
- 2018-2019-kroppens `Råd 2018-2019` gjelder **to** år.
- 2020-, 2021-, 2022-, 2023- og 2024-kroppene gir råd for **ett**.
- 2025-kroppen gir råd for **to**, men i **to separate kolonner**.

En rad med `observed_at = 2019-12-31` og verdien `10-30%` betyr noe helt
annet om den er ett års vurdering enn om den er et sammenslått råd for
2018 og 2019. Uten feltet kan ingen analyse skille dem, og en
sammenligning mot vedtaket ville sammenlignet to ulike størrelser uten å
vite det.

Feltet er da også det eneste stedet endringen i 2020 blir SYNLIG i
dataene. Uten det er den bare et fravær i prosaen.

Formen er `grunnlagsaar` som en sortert liste, lagret som streng —
`"2018,2019"` eller `"2020"` — av samme grunn som `utvalg` er en tom
streng framfor et gjett når den er ukjent: fraværet skal kunne skilles
fra en verdi.

## Sammenslåingen forsvant, og med den spørsmålet

Dette er funnet som gjør kilden verdt å bygge og som samtidig begrenser
hva den kan brukes til.

**Fram til og med 2019 slo styringsgruppen sammen to vurderingsår til ett
råd, og skrev ned regelen.** 2018-2019-kroppen:

> «Grunnet variasjoner mellom år og metoder, samt usikkerhetene i
> ekspertgruppens vurderinger, er styringsgruppens råd basert på lik
> vekting av årene 2018 og 2019. Vi har ikke grunnlag for å vekte et av
> de to årene over det andre.»

> «Der ekspertgruppens vurderinger for kategori av dødelighet for et
> område er forskjellig i 2018 og 2019 har styringsgruppen, på lik måte
> som for rådet avgitt i 2017, valgt en konservativ tilnærming for samlet
> vurdering av lakselusindusert dødelighet (Tabell 3).»

Regelen er etterprøvd på to runder, uavhengig av hverandre. For
2018-2019: seks områder spriker (PO 2, 3, 4, 5, 7, 10), og rådet er det
verste av de to i alle seks. For 2016–2017, lest av 2018-kroppens
Tabell 1: fire spriker (PO 2, 4, 6, 7), og rådet er det verste i alle
fire. Åtte av åtte.

**Fra 2020-kroppen finnes verken kolonnen eller regelen.** Overskriften
er `Styringsgruppens vurderinger for 2020`, tabellen har én årskolonne,
og ingen setning sier hvordan to år veies. Det er ikke en glipp:
2021-kroppen er et ODDETALLSÅR — et år systemet gir råd om
kapasitetsjustering — og har begge grunnlagsårene liggende i kroppen
(Tabell 1 for 2021, Tabell 2 for oppdatert 2020). Råstoffet er der. Den
slår dem likevel ikke sammen.

2025-kroppen dekker to år i overskrift og tabell, men har én kolonne per
år og ingen sammenslått. Spørsmålet oppstår ikke, fordi «ingen av
produksjonsområdene endret kategori fra 2024 til 2025».

### Følgen: spørsmålet er ikke besvarbart fra runde 2022

`analyse/vedtak_mot_rad.py` rapporterer dekning og samforekomst og
beregner ingen treffrate, fordi koblingen råd → farge ikke er definert i
regelverket. Den begrunnelsen står. Men det er nå en grunn til:

- **Der de to årene er LIKE, følger fargen mekanisk.** Departementet sier
  det selv, 06.03.2024: «Fargeleggingen følger direkte av
  handlingsregelen i trafikklyssystemet i områdene hvor ekspertenes
  vurdering av miljøpåvirkningen er lik i begge år.» En treffrate over
  disse cellene måler at en tautologi holder.
- **Der de SPRIKER, finnes det ikke lenger noe sammenslått råd å måle
  mot.** Fram til 2019 fantes det en kolonne som sa hva rådet var når
  årene var uenige. Fra 2020 finnes den ikke. Departementet gjør da
  «en samlet vurdering» — og den har ingen motpart på rådssiden.

Det er altså ikke bare oversettelsen råd → farge som mangler. **Selve
rådet mangler for nettopp de cellene der spørsmålet er interessant.**

Kilden bygges likevel, fordi den gjør fraværet MÅLBART framfor bare
påstått, og fordi den svarer på det andre spørsmålet:
`vedtak_mot_rad.py` kan nå plassere et avvik mellom ekspertgruppen og
forskriften på ett av to ledd i stedet for å la det henge mellom dem.

## Premisset om mandatoverskridelse er målt og forkastet

Arbeidet startet med en mistanke: at styringsgruppen løser tvetydigheter
ekspertgruppen lot stå, uten hjemmel, og dermed tar avgjørelser som ikke
er dens.

`docs/MALING-RAD-MOT-EKSPERTVURDERING.md` (09.09.2026) målte det over 26
celler, 13 PO × 2 år, med en tredje parring for den reviderte 2024.
Resultatet:

| parring | ENIG | AVGJORT | AVVIK | IKKE_MALBAR |
|---|---:|---:|---:|---:|
| 2024 | 13 | 0 | 0 | 0 |
| 2025 | 12 | **1** | 0 | 0 |
| 2024 revidert | 13 | 0 | 0 | 0 |

**Én celle: PO9 i 2025.** Og styringsgruppen oppgir en regel for den, tre
setninger under tabellen:

> «Styringsgruppen forstår definisjonen av miljøpåvirkning i
> Stortingsmelding 16 (2014-15) tabell 10.1. som at kategorien lav er
> mindre enn 10 % og at kategori moderat er fra og med 10 % til og med
> 30 %. Vi mener derfor at en medianverdi lik 10 % bør plasseres i
> moderat påvirkning.»

Regelen har hjemmel, den er skrevet ned, og den treffer nøyaktig cella:
PO9s midtpunkt for 2025 er `10`. Ekspertgruppen har på sin side en
medianregel som normalt produserer én kategori, og som ikke diskriminerer
når medianen ligger på selve grensen.

Merk formen: «Vi mener derfor» er en TOLKNING av stortingsmeldingens
intervallgrenser, ikke en prosedyre styringsgruppen er gitt. Det er verdt
å notere, men det er ikke mandatoverskridelse, og notatet skal ikke
antyde noe annet.

**Premisset er forkastet.** Kilden bygges ikke for å avdekke
overskridelse. Den bygges fordi leddet mangler i repoet.

Over 2020–2024 er styringsgruppen dessuten enig med ekspertgruppen i alle
65 celler der begge har en verdi. Det er et funn om kilden, ikke bare om
uttrekket.

## Kryssjekken finnes for 2018–2024 og ikke for 2025

Alle kropper fra 2018 til 2024 sier rådet TO ganger — i tabellen og i
punktlista. `docs/KILDE-EKSPERTGRUPPEN.md` punkt 4 kaller den doble
lesingen «den eneste kontrollen som kan felle et uttrekk som er
syntaktisk vellykket og semantisk feil».

2025-kroppen har ingen punktliste. Målt: null treff på alle formene fra
de tidligere kroppene. Rådet står bare i Tabell 8.

Uttrekket for 2025 må derfor ha en EKSTERN vakt. Målingen brukte tre, og
alle passerte på første kjøring uten justering:

1. Strukturvakt: nøyaktig 13 rader, PO 1–13 én gang.
2. Aggregatvakt fra departementets høringsnotat 19.06.2026: 1 høy,
   9 moderat, 3 lav, med høy i PO3 og lav i PO1, PO12, PO13. Bekreftet en
   gang til av fargeleggingsmeldingen samme dag — se
   `docs/VERIFISERING-PRESSEMELDINGER.md`.
3. Kroppens egen påstand: «kun tre av de tretten produksjonsområdene i
   lav kategori».

Vakt 2 er en VAKT og ikke en fasit. Slår den ut, vet vi at noe er galt,
men ikke hvilken side som tar feil. Uttrekket skal ikke justeres for å
treffe tallet.

## Det som IKKE bygges

- **De to 2017-kroppene.** Skann uten tekstlag — 3 og 10 tegn uttrukket
  av til sammen femten sider, fra en Xerox- og en Konica
  Minolta-kopimaskin. OCR er ikke gjort, og en OCR-lesing ville vært vår
  lesing av et bilde, ikke kildens tekst. Rådet for 2016–2017 er likevel
  ikke tapt: 2018-kroppens Tabell 1 restaterer det i tekst.
- **Usikkerhetsgradene som eget felt.** De finnes i syv former over ni
  kropper — ord i egen kolonne, superscript, piler, dobbeltpiler,
  IPCC-sannsynlighetsord, sannsynlighetskolonner per terskel, og
  midtpunktstall. De lagres ORDRETT sammen med verdien, som
  `ekspertgruppen.kategori_ordrett`, og normaliseres ikke.
- **Heterogenitetsanalysene** fra 2023 og senere. Kartlagt, ikke
  uttrukket.

## Hva `core/` skal gjøre

Ingenting. Kilden er én ny fil i `sources/` som arver `Source` og
returnerer `Observation`-objekter. `grunnlagsaar` er et felt på raden,
ikke en utvidelse av kontrakten — samme form som `utvalg` og
`farge__lesemaate`.

Revisjonsaksen finnes allerede og trengs: 2018-kroppen reviderer
2016–2017, 2018-2019-kroppen reviderer 2018 («Ny vurdering av
lakselusindusert dødelighet for 2018 med oppdaterte modeller»),
2021-kroppen reviderer 2020, og 2025-kroppen reviderer 2024.

## Hva som er lukket underveis

`docs/VERIFISERING-PRESSEMELDINGER.md` (09.09.2026) lukket ett av de
fire reverseringskriteriene i vedtaksnotatet:

> «**Et departementsdokument som oppgir grunnlagsårene for rundene 2018,
> 2020 og 2022.** I dag er de bare lest for 2024 og 2026, og de tre
> eldste rundene telles derfor ikke som sammenlignbare.»

Grunnlagsårene er nå lest ordrett av departementets egne
pressemeldinger for **alle fem runder**: 2016+2017 → runde 2018,
2018+2019 → 2020, 2020+2021 → 2022, 2022+2023 → 2024, 2024+2025 → 2026.

Det utvider ikke sammenligningsgrunnlaget slik notatet håpet, av grunnen
i «Sammenslåingen forsvant». Grunnlagsårene er nå kjent for alle fem
runder; det sammenslåtte RÅDET finnes bare for de to første.

## Hva som ville snudd dette

- **At en kropp etter 2019 viser seg å slå sammen likevel.** Kartleggingen
  leste ni kropper og fant ingen sammenslått kolonne etter
  2018-2019-kroppen. Skulle en av dem vise seg å bære en sammenslåing vi
  ikke så — i et vedlegg, i en tabell vi leste som ettårig, i en setning
  utenfor rådsavsnittet — er «spørsmålet er ikke besvarbart fra runde
  2022» feil, og `vedtak_mot_rad.py` skal da regne på de cellene.
- **At styringsgruppen gjeninnfører sammenslåingen.** 2025-kroppen dekker
  to år uten å slå dem sammen, og slapp unna fordi ingen PO endret
  kategori. Spriker de to årene i en framtidig kropp, MÅ styringsgruppen
  ta stilling — og gjør den det med en skrevet regel, er leddet
  gjenopprettet.
- **At ekspertgruppens egne kropper for 2019 og tidligere blir
  tilgjengelige.** Da er styringsgruppens gjengivelse ikke lenger det
  eneste vi har for de årene, og annenhånds-forbeholdet under faller
  bort.
- **At koblingen råd → farge skrives inn i regelverket.** Da blir
  treffraten beregnelig for de cellene der rådet finnes, og
  `vedtak_mot_rad.py` skal beregne den, med skala og hjemmel ført i
  kjøringsloggen.
- **At en kropp gir en ANNEN verdi enn ekspertgruppen uten å oppgi
  regel.** Målingen fant én avgjort celle med regel og null avvik. Blir
  det to celler uten regel, er premisset som ble forkastet her, ikke
  forkastet lenger, og notatet skal skrives om.

## Et forbehold som skal bæres i dataene

Styringsgruppens kropper GJENGIR ekspertgruppens vurderinger. For årene
der vi har ekspertgruppens egen kropp er det redundans. For **2019** er
det den eneste kilden vi har: 2018-2019-kroppens Tabell 2 er
ekspertgruppens 2019-vurdering per PO med metodekolonner og konklusjon,
og ekspertgruppens egen 2019-kropp er ikke lokalisert.

Den verdien er ANNENHÅNDS og skal bære det. Konkret: `source` er
`styringsgruppen`, ikke `ekspertgruppen`, og en analyse som slår dem
sammen skal måtte velge det selv.

Merk at kroppen SITERER ekspertgruppens 2019-rapport med full tittel og
forfatterrekke (Vollset mfl. 2019). Rapporten finnes altså; vi har ikke
en kopi. Det flytter 2019 i `docs/KILDE-EKSPERTGRUPPEN.md` punkt 9 fra
«vi vet ikke om den finnes» til «vi vet at den finnes og når den ikke» —
men punktet er ikke rettet på dette grunnlaget, fordi beviset ligger i en
kropp som ikke er i repoet. Se `docs/REVISJON-2026-09-09.md`.
