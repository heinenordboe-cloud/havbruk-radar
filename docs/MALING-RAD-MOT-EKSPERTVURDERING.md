# Måling: løser styringsgruppen tvetydigheter ekspertgruppen lot stå?

Måling, ikke kilde. Ingenting er skrevet til `data/`, ingen kilde er lagt
i `sources/`, `core/` er urørt, og
`analyse/fasit/ekspertgruppen-po-kategori.csv` er ikke rørt.

**Svaret er én celle: PO9 i 2025.** Ingen andre av de 26 cellene er slik,
og 2024 — kontrollen — er enig i alle tretten.

**Og premisset for spørsmålet holder ikke helt:** styringsgruppen oppgir
en regel. Den står i den samme kroppen, tre setninger under tabellen. Se
punkt 5.

---

## Grunnlag

Alt er lest fra arkivet. Ingenting er hentet fra nett. Hver kropp er
hashet før lesing og holdt mot den dokumenterte verdien:

| kropp | kilde | sha256 | holdt mot |
|---|---|---|---|
| ekspertgruppen 2024 | `data/arkiv/ekspertgruppen/2024-12-31.bin.gz` | `b740d4bb…8d8b6d4` | `docs/KILDE-EKSPERTGRUPPEN.md` |
| ekspertgruppen 2025 | `data/arkiv/ekspertgruppen/2025-12-31.bin.gz` | `6083b40b…117db546` | `docs/KILDE-EKSPERTGRUPPEN.md` |
| styringsgruppen 2024 | råarkiv fra kartleggingen | `23ab0291…6657f8ad` | `docs/KARTLEGGING-STYRINGSGRUPPEN.md` |
| styringsgruppen 2025 | råarkiv fra kartleggingen | `82a6c496…13e8f8d3` | `docs/KARTLEGGING-STYRINGSGRUPPEN.md` |

Alle fire stemmer. Ingen kropp har endret seg mellom lesningene.

### Stoppregelen er lest og ikke utløst

Apparatet finnes, og det skiller de to tingene uttrykkelig. Ekspertgruppen
skriver én kategori i kolonnen `Konklusjon påvirkning` i tolv av tretten
rader, og i den trettende skriver den to: `Lav–Moderat*`, med
sannsynligheten for dødelighet over 10 % satt til `Like sannsynlig som
ikke` og en fotnote som sier hvorfor. Målingen er gjennomførbar slik den
er formulert.

### Tre parringer, ikke to

2024 finnes i to utgaver, og forskjellen er hele saken. Alle tre er målt
og rapportert hver for seg:

| merke | ekspertgruppens tabell | styringsgruppens tabell |
|---|---|---|
| **2024** | 2024-rapporten, Tabell 6.1 `Hovedkonklusjoner for 2024` | 2024-kroppen, Tabell 2 |
| **2025** | 2025-rapporten, Tabell 6.3 `Hovedkonklusjoner for 2025` | 2025-kroppen, Tabell 8, kolonnen `2025` |
| **2024\*** | 2025-rapporten, Tabell 6.1 `Oppdaterte hovedkonklusjoner for 2024` | 2025-kroppen, Tabell 8, kolonnen `2024` |

De 26 radene under er **2024** og **2025** — hvert år lest av kroppene som
er om det året i egen rett. **2024\*** er den reviderte utgaven, og den
står i sin egen tabell etterpå, fordi fargeleggingen i 2026 hviler på den
og fordi det er den pressemeldingen gjengir.

---

## 1. De 26 radene

Strengene er ordrett fra kroppene. `A` er ekspertgruppens konklusjon, `B`
det ekspertgruppen skriver om usikkerheten i den, `C` styringsgruppens
verdi, `D` det styringsgruppen skriver om usikkerheten. Ingen streng er
forkortet, oversatt eller normalisert — bindestreken i `Lav-Moderat` og
tankestreken i `Lav–Moderat*` er to forskjellige tegn, og de står som de
står.

| PO | år | A — ekspertgruppens konklusjon | B — ekspertgruppens usikkerhet | C — styringsgruppens verdi | D — styringsgruppens usikkerhet | klassifisering |
|---|---|---|---|---|---|---|
| 1 | 2024 | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig; prosaliste: <10%` | **ENIG** |
| 2 | 2024 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 3 | 2024 | `Høy` | `over 10 %: Veldig sannsynlig; over 30 %: Mer sannsynlig enn ikke` | `Høy` | `over 10 %: Veldig sannsynlig; over 30 %: Mer sannsynlig enn ikke; prosaliste: >30%` | **ENIG** |
| 4 | 2024 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 5 | 2024 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 6 | 2024 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 7 | 2024 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 8 | 2024 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 9 | 2024 | `Lav–Moderat*` | `over 10 %: Like sannsynlig som ikke; over 30 %: Veldig usannsynlig` | `Lav-Moderat` | `over 10 %: Like sannsynlig som ikke; over 30 %: Veldig usannsynlig; prosaliste: <10%/10-30%` | **ENIG** |
| 10 | 2024 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Veldig usannsynlig` | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Veldig usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 11 | 2024 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig; prosaliste: 10-30%` | **ENIG** |
| 12 | 2024 | `Lav` | `over 10 %: Usannsynlig; over 30 %: Veldig usannsynlig` | `Lav` | `over 10 %: Usannsynlig; over 30 %: Veldig usannsynlig; prosaliste: <10%` | **ENIG** |
| 13 | 2024 | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Svært usannsynlig` | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Svært usannsynlig; prosaliste: <10%` | **ENIG** |
| 1 | 2025 | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | `Lav (0,2)` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | **ENIG** |
| 2 | 2025 | `Moderat` | `over 10 %: Veldig sannsynlig; over 30 %: Mindre sannsynlig enn ikke` | `Moderat (26)` | `over 10 %: Veldig sannsynlig; over 30 %: Mindre sannsynlig enn ikke` | **ENIG** |
| 3 | 2025 | `Høy` | `over 10 %: Veldig sannsynlig; over 30 %: Sannsynlig` | `Høy (40)` | `over 10 %: Veldig sannsynlig; over 30 %: Sannsynlig` | **ENIG** |
| 4 | 2025 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat (19)` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | **ENIG** |
| 5 | 2025 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (14)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 6 | 2025 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat (21)` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | **ENIG** |
| 7 | 2025 | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Mindre sannsynlig enn ikke` | `Moderat (23)` | `over 10 %: Sannsynlig; over 30 %: Mindre sannsynlig enn ikke` | **ENIG** |
| 8 | 2025 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (13)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 9 | 2025 | `Lav–Moderat*` | `over 10 %: Like sannsynlig som ikke; over 30 %: Usannsynlig` | `Moderat (10)*` | `over 10 %: Like sannsynlig som ikke*; over 30 %: Usannsynlig` | **AVGJORT** |
| 10 | 2025 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (15)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 11 | 2025 | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (14)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 12 | 2025 | `Lav` | `over 10 %: Usannsynlig; over 30 %: Veldig usannsynlig` | `Lav (3)` | `over 10 %: Usannsynlig; over 30 %: Veldig usannsynlig` | **ENIG** |
| 13 | 2025 | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | `Lav (0,5)` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | **ENIG** |

### Den reviderte 2024 (parring 2024\*)

| PO | år | A — ekspertgruppens konklusjon | B — ekspertgruppens usikkerhet | C — styringsgruppens verdi | D — styringsgruppens usikkerhet | klassifisering |
|---|---|---|---|---|---|---|
| 1 | 2024* | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | `Lav (0,3)` | `over 10 %: Veldig usannsynlig; over 30 %: Veldig usannsynlig` | **ENIG** |
| 2 | 2024* | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (14)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 3 | 2024* | `Høy` | `over 10 %: Veldig sannsynlig; over 30 %: Mer sannsynlig enn ikke` | `Høy (39)` | `over 10 %: Veldig sannsynlig; over 30 %: Mer sannsynlig enn ikke` | **ENIG** |
| 4 | 2024* | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat (17)` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | **ENIG** |
| 5 | 2024* | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat (16)` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | **ENIG** |
| 6 | 2024* | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat (21)` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | **ENIG** |
| 7 | 2024* | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Mindre sannsynlig enn ikke` | `Moderat (24)` | `over 10 %: Sannsynlig; over 30 %: Mindre sannsynlig enn ikke` | **ENIG** |
| 8 | 2024* | `Moderat` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | `Moderat (18)` | `over 10 %: Sannsynlig; over 30 %: Usannsynlig` | **ENIG** |
| 9 | 2024* | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (11)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 10 | 2024* | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (14)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 11 | 2024* | `Moderat` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | `Moderat (12)` | `over 10 %: Mer sannsynlig enn ikke; over 30 %: Usannsynlig` | **ENIG** |
| 12 | 2024* | `Lav` | `over 10 %: Usannsynlig; over 30 %: Veldig usannsynlig` | `Lav (5)` | `over 10 %: Usannsynlig; over 30 %: Veldig usannsynlig` | **ENIG** |
| 13 | 2024* | `Lav` | `over 10 %: Veldig usannsynlig; over 30 %: Svært usannsynlig` | `Lav (0,6)` | `over 10 %: Veldig usannsynlig; over 30 %: Svært usannsynlig` | **ENIG** |

---

## 2. Antall per klassifisering

| parring | ENIG | AVGJORT | AVVIK | IKKE_MALBAR | sum |
|---|---:|---:|---:|---:|---:|
| 2024 (kroppene om 2024) | 13 | 0 | 0 | 0 | 13 |
| 2025 (kroppene om 2025) | 12 | **1** | 0 | 0 | 13 |
| 2024\* (2025-kroppenes reviderte 2024) | 13 | 0 | 0 | 0 | 13 |

**Én AVGJORT-celle i alt: PO9 i 2025.** Null AVVIK og null IKKE_MALBAR i
alle tre parringene — ingen formulering var uklar nok til å måtte legges
fram for avgjørelse.

Kontrollen holder: pressemeldingen sier de er enige i 2024, og målingen
finner dem enige i 2024 — i begge utgaver av året.

### At tallet er 1 og ikke 13 er selve poenget

Ekspertgruppens usikkerhetsapparat gir utslag i mange celler. I 2025
alene står det `Mindre sannsynlig enn ikke` for dødelighet over 30 % i
PO2 og PO7, og `Mer sannsynlig enn ikke` for over 10 % i fem områder. Det
er grader, ikke sidestillinger: konklusjonen er oppgitt, og
styringsgruppen som gjentar den har ikke avgjort noe.

Bare formen der kroppen oppgir **to kategorier som likeverdige** er talt.
Den finnes i to skrivemåter, begge i tabellcella og begge markert med
fotnote: `Lav–Moderat*` i kolonnen `Konklusjon påvirkning`, og `Like
sannsynlig som ikke` i kolonnen `Sannsynlighet for dødelighet over 10 %`.
De opptrer alltid sammen.

Hadde piler og grader vært talt med, ville tallet blitt tosifret og sett
ut som et funn. Det ville vært det samme mønsteret som `Områdene?`-feilen
i kartleggingen, med den forskjellen at det slår i vår favør — og det er
den farlige retningen.

---

## 3. AVGJORT-cellen: PO9 i 2025, begge kropper i sin helhet

### Ekspertgruppens 2025-rapport

Tabell 6.3, `Hovedkonklusjoner for 2025`, raden for PO9:

    PO9      Lav–Moderat*      Like sannsynlig som ikke      Usannsynlig

Fotnoten under tabellen:

> «\* Ekspertgruppen vurderer lakselusindusert dødelighet i PO9 til å være
> helt på grensen mellom lav og moderat og at informasjonsgrunnlaget ikke
> er tilstrekkelig til å avgjøre hvilken av disse kategoriene som har
> sannsynlighetsovervekt i dette POet.»

Avsnittet om produksjonsområdet, kapittel 6.4, `Produksjonsområde 9:
Vestfjorden og Vesterålen`:

> «Konklusjon: Lav til moderat lakselusindusert villaksdødelighet i 2025
>
> Det er usannsynlig at lakselusindusert villaksdødelighet var over 30 % i
> 2025, og det er like sannsynlig at dødeligheten var over 10 % som at den
> var under 10 % (Figur 6.45).»

Fotnoten til heterogenitetstabellen (Tabell 6.4) sier det samme en tredje
gang:

> «\*Hovedkonklusjon for PO9 er at det er like sannsynlig at dødeligheten
> er under som over 10 %. Heterogenitsvurderingene vist her går på om
> enkeltbestander har dødelighet over 10 %.»

(Skrivefeilen «Heterogenitsvurderingene» er kroppens egen.)

Tre steder i samme kropp, samme utsagn: ekspertgruppen velger ikke.

### Styringsgruppens 2025-kropp

Tabell 8, raden for PO9:

    PO9       Moderat (11)        Moderat (10)*

Kolonnene er `2024` og `2025`. Tallet i parentes er midtpunktet i
sannsynlighetsfordelingen; bildeteksten sier at det er midtpunktet som
gir konklusjonen. **For 2025 er midtpunktet 10** — nøyaktig på grensen
mellom kategoriene, som er grunnen til at ekspertgruppen ikke kunne
velge.

Fotnoten under Tabell 8:

> «\*Ekspertgruppen vurderer lakselusindusert dødelighet i PO9 til å være
> på grensen mellom lav og moderat, og at informasjonsgrunnlaget ikke er
> tilstrekkelig til å avgjøre hvilken av disse kategoriene som har
> sannsynlighetsovervekt.»

Styringsgruppen gjengir altså ekspertgruppens forbehold ordrett, og
skriver `Moderat` i cella likevel.

---

## 4. Pressemeldingens beskrivelse av PO9, holdt mot kroppene

Departementets pressemelding 19.06.2026, slik den er gjengitt i
oppdraget, gjør tre påstander. To stemmer. Den tredje stemmer bare mot
den ene av to utgaver av 2024, og pressemeldingen sier ikke hvilken.

| påstand | kroppene | stemmer? |
|---|---|---|
| «ekspertgruppen vurderte området som moderat påvirket i 2024» | 2024-rapporten Tabell 6.1: `Lav–Moderat*`. **2025-rapporten** Tabell 6.1 (oppdatert 2024): `Moderat` | **bare mot den reviderte** |
| «for 2025 var det like sannsynlig at påvirkningen var lav som moderat» | 2025-rapporten Tabell 6.3: `Lav–Moderat*`, `Like sannsynlig som ikke` | **ja** |
| «styringsgruppens råd var likevel moderat også i 2025» | Styringsgruppens Tabell 8, kolonnen 2025: `Moderat (10)*` | **ja** |

Den første påstanden er ikke gal, men den er **udatert**. Da
ekspertgruppen leverte for 2024, skrev den `Lav–Moderat*` for PO9 — samme
tvetydighet som i 2025. Kategorien ble `Moderat` først et år senere, i
2025-rapportens forenklede nye SHELF-vurdering, og rapporten sier selv
hvorfor:

> «Oppdateringen innebærer at påvirkningen i PO9 i 2024 blir vurdert til
> moderat, mens den i fjorårets rapport ble vurdert til å være helt på
> grensen mellom lav og moderat. Sannsynlighetskategorien for dødelighet
> over 10 % i PO9 endres dermed fra like sannsynlig som ikke til mer
> sannsynlig enn ikke.»

Lest som en beskrivelse av 2024-rapporten er påstanden altså **usann**.
Lest som en beskrivelse av grunnlaget for fargeleggingen i 2026 — som er
2025-rapporten, der begge år er oppdatert — er den sann.

**Og styringsgruppen avgjorde ingenting i 2024.** Der ekspertgruppen skrev
`Lav–Moderat*`, skrev styringsgruppens 2024-kropp `Lav-Moderat` i tabellen
og `<10%/10-30%` i punktlista. Den førte tvetydigheten videre uendret.
Avgjørelsen skjer for første gang i 2025-kroppen.

---

## 5. Oppgir noen kropp en regel?

**Ja — én gjør det, og det er nettopp den kroppen som avgjør.**

Styringsgruppens 2025-kropp, i avsnittet rett etter Tabell 8:

> «Ekspertgruppen vurderer lakselusindusert dødelighet i PO 9 til å være
> helt på grensen mellom lav og moderat og informasjonsgrunnlaget er ikke
> tilstrekkelig til å avgjøre hvilken av disse kategoriene som har
> sannsynlighetsovervekt. Styringsgruppen forstår definisjonen av
> miljøpåvirkning i Stortingsmelding 16 (2014-15) tabell 10.1. som at
> kategorien lav er mindre enn 10 % og at kategori moderat er fra og med
> 10 % til og med 30 %. Vi mener derfor at en medianverdi lik 10 % bør
> plasseres i moderat påvirkning.»

Det er en regel, den er skrevet ned, den har en hjemmel (Meld. St. 16
(2014–2015) tabell 10.1), og den treffer nøyaktig cella: PO9s midtpunkt
for 2025 er `10`.

Formuleringen «Vi mener derfor» er verdt å merke seg. Regelen oppgis som
styringsgruppens **tolkning** av stortingsmeldingens intervallgrenser, ikke
som en regel den er gitt. Det er en tolkning av hvor grensen går, ikke en
prosedyre for å veie to sidestilte kategorier mot hverandre — men i dette
tilfellet avgjør den saken, fordi tvetydigheten nettopp er at medianen
ligger på grensen.

### Ekspertgruppen har en regel som IKKE avgjør dette

Begge ekspertgrupperapportene forklarer hvordan konklusjonen settes, med
identisk ordlyd:

> «Legg merke til at det ikke er større sannsynlighet enn 50 % for at
> moderat er riktig kategori (45 %). Men ettersom midtpunktet (medianen)
> i sannsynlighetsfordelingen er i moderat kategori, settes
> hovedkonklusjonen til "moderat". Medianen er definert som den verdien
> der det er like stor sannsynlighet for at dødeligheten er høyere som
> lavere.»

Det er regelen som normalt PRODUSERER én kategori. PO9 er det ene
tilfellet der den ikke diskriminerer: medianen ligger på selve grensen, og
regelen sier ikke hvilken side den da faller på. Ekspertgruppen svarer
med å la begge stå. Styringsgruppen svarer med å definere grensen.

### De øvrige kroppene

| kropp | oppgir regel for sidestilte kategorier? |
|---|---|
| ekspertgruppen 2024 | nei — medianregelen finnes, men avgjør ikke grensetilfellet |
| ekspertgruppen 2025 | nei — samme |
| styringsgruppen 2024 | **nei**, og kroppen avgjør heller ikke: den viderefører `Lav-Moderat` |
| styringsgruppen 2025 | **ja** — medianverdi lik 10 % plasseres i moderat |

Sett mot kartleggingen: den skrevne sammenslåingsregelen for to
vurderingsår forsvant med 2020-kroppen og er ikke kommet tilbake. Regelen
som dukker opp i 2025-kroppen er en annen slags regel — den løser en
tvetydighet innenfor ett år, ikke mellom to år. Fraværet fra kartleggingen
står altså ved lag.

---

## 6. Vaktene

2025-kroppen har ingen prosaliste, så uttrekket av Tabell 8 har ingen
intern redundans. Fire vakter er satt inn i stedet. Alle passerte på
første kjøring, og ingen av dem er justert for å treffe.

**Aggregatvakt, 2025.** Fra departementets høringsnotat 19.06.2026: 1 høy,
9 moderat, 3 lav, med høy i PO3 og lav i PO1, PO12 og PO13.

    vakt sg2025 Tabell 8 / 2025: 13 rader, {'lav': 3, 'moderat': 9, 'hoy': 1},
                                 høy=[3], lav=[1, 12, 13]   OK

**Aggregatvakt, 2024: finnes ikke.** Ingen av de fire kroppene oppgir et
aggregat for 2024. Vakten kan derfor ikke kjøres for det året, og det er
skrevet ned framfor å bli erstattet med noe som ligner.

**Strukturvakt, alle sju tabellene.** Nøyaktig 13 rader, PO 1–13 én gang
hver, i eg2024 T6.1, eg2025 T6.1, eg2025 T6.3, sg2024 T2, sg2024s
prosaliste, sg2025 T8 og sg2025 T2. Alle sju OK.

**Kroppens egen aggregatpåstand.** Styringsgruppens 2025-kropp skriver «I
dag, ti år etter etablering av Trafikklyssystemet, er kun tre av de tretten
produksjonsområdene i lav kategori.» Uttrekket gir 3, i PO1, PO12 og PO13.
Det er en vakt hentet fra kroppen selv, uavhengig av høringsnotatet.

### En femte kontroll som falt ut av målingen

Styringsgruppens 2024-tabell og ekspertgruppens 2024-tabell er lest av to
forskjellige PDF-er med to uavhengig skrevne uttrekk — posisjonsbasert for
ekspertgruppen, ordlistebasert for styringsgruppen, fordi 2024-kroppens
Adobe-eksport har ødelagt tekstlag. De to gir **identiske strenger i 12 av
13 celler**. Den trettende er PO9, der forskjellen er typografisk:
ekspertgruppen skriver `Lav–Moderat*` med tankestrek og fotnotemerke,
styringsgruppen `Lav-Moderat` med bindestrek og uten.

To uttrekk, to dokumenter, samme svar. Det er den redundansen 2025 mangler.

---

## 7. Kjente begrensninger

1. **Målingen dekker 2024 og 2025.** Tidligere årganger er ikke undersøkt
   for sidestilte kategorier. Formen `Lav–Moderat*` er ikke i bruk i
   kroppene før 2024 — 2022- og 2023-kroppene skriver én kategori med
   superscript-usikkerhet — men det er ikke uttømmende ettersøkt her.
2. **«Like sannsynlig som ikke» er ikke definert i kroppenes Tabell 1.**
   Den IPCC-avledede ordlista har åtte trinn, og dette uttrykket er ikke
   ett av dem; det opptrer bare i tabellkroppen. At det betyr 50/50 er
   lest av fotnotene, som sier det med ord, ikke utledet av skalaen.
3. **`Moderat (10)` er avrundet.** Kroppene oppgir midtpunktet som et
   heltall for PO9 i 2025. Om den underliggende medianen er 9,96 eller
   10,04 står ikke i noen av dem, og styringsgruppens regel skiller på
   nettopp det punktet.
4. **Pressemeldingen selv er ikke lest.** Påstandene er tatt fra oppdraget,
   og sammenstillingen i punkt 4 gjelder dem slik de er gjengitt der.
