---
dato: 2026-09-01
tittel: "Kildeleddet mot ROC: stoppregelen BESTOD IKKE — og kilden sluttet å publisere utvandringsvinduet"
status: gjeldende
commit: c314849
---

## Utfallet

**Stoppregelen bestod ikke.** Begge ledd måtte holde; det ene gjorde det.

| ledd | krav | målt | utfall |
|---|---|---|---|
| samlet R² | ≥ 0,67 (n = 60) | **0,4855** | **bestod ikke** |
| innen-PO R² | ≥ 0,25 | **0,4862** | bestod |

    n = 60 celler, 12 produksjonsområder, 2021-2025
    SAMLET      r = +0,6968   R² = 0,4855   95 % CI R² = [0,2895, 0,6525]   df = 57
    INNEN PO    r = +0,6973   R² = 0,4862   df = 48
    Spearman    rho = +0,7833      <- like-for-like-tallet notatet krever

Terskelen 0,67 er ikke valgt her. Den er slått opp på faktisk n i
tabellen som ble skrevet **før** celletallet var kjent — se tilføyelse
(1) i `2026-08-31-hypotesen-omdefineres.md` og `analyse/terskel_av_n.py`.
Analysekoden leser den derfra framfor å bære et eget tall.

**Regelen er ikke rørt etter at tallet ble sett.** Én aggregeringsvariant
er kjørt.

## Ingen celler falt ut

    ROC-celler lest        60    2021-2025, 12 PO hvert år
    falt ut, uten vindu     0
    falt ut, uten uker      0
    n                      60

Dette er endringen fra forrige kjøring, der n var 0. To ting flyttet
tallet, og ingen av dem er en oppmykning av regelen:

1. **Utvandringsmidtpunktet er nå trukket ut for alle årene** — 78 celler
   mot 13. Se neste avsnitt.
2. **PO7 i 2021 og 2022 kom tilbake.** De lå i v1-snapshots der
   ROC-uttrekket feilet på orddelingsmellomrom. Re-parsen med versjon 4
   leser dem, og 58 ROC-celler ble til 60 — 12 PO × 5 år, komplett.

## Det som ble funnet underveis, og som er viktigere enn tallet

**Ekspertgruppen sluttet å publisere utvandringsvinduet etter 2020.**

Målt på alle seks arkiverte kroppene:

| år | form | start/slutt som datoer | årsspesifikk |
|---|---|---|---|
| 2020 | «Antatt tidspunkt for utvandring: 24. april – 5. juni, med 50 % utvandring satt til 17. mai (uke 20)» | ja, 13/13 | ja |
| 2021 | «Beregnet tidspunkt for 50 % utvandring 11. mai (uke 19)» | nei | ja |
| 2022–2025 | «Utvandringsperioden fra elvene i PO1 er fra siste halvdel av april til begynnelsen av juni, med beregnet gjennomsnittlig midtpunkt 15/5» | nei — grensene er løs prosa | **nei** |

**2022, 2023, 2024 og 2025 er 13/13 identiske i alle seks parvise
sammenligninger.** Midtpunktene (15/5, 14/5, 17/5, 18/5, 20/5, 25/5, 2/6,
8/6, 10/6, 13/6, 20/6, 29/6, 27/6) gjentas uendret år etter år. Kilden
oppgir ikke et årsspesifikt vindu for de fire årene — den skriver av en
klimatologisk konstant per produksjonsområde. 2020 og 2021 er derimot
årsspesifikke (0/13 og 1/13 sammenfall med de øvrige).

Vedlegg I heter «Oversikt over laksevassdrag og utvandringstidspunkt for
smolt» og ville hatt datoene per elv. Det er **utgitt separat** og finnes
ikke i noen kropp — bare tittelen står på vedleggssiden. Verifisert på
2022, 2024 og 2025.

Forrige notat leste fraværet som «uttrekket er ikke gjort». Det var feil.
Uttrekket lot seg gjøre; **størrelsen finnes ikke å trekke ut.**

## Hva som ble målt, og med hvilket vindu

Vinduet er **kildens eget midtpunkt ± 20 dager**. Lengden er kildens,
ordrett fra 2024- og 2025-rapportene:

> «Start av utvandring er satt til 10 dager før og slutt av utvandring 30
> dager etter 25 % utvandring slik at den totale utvandringsperioden er
> satt til å vare i 40 dager som i tidligere år.»

Halvbredden er **vår** — kilden forankrer de 40 dagene på 25 %-datoen, og
det er 50 %-midtpunktet vi har. Det er den eneste frie parameteren i
aggregeringen, og den ble valgt og committet (`c314849`) **før noen
korrelasjon var regnet ut**.

Konstruksjonen er målt mot 2020, det ene året der kildens ekte vindu
finnes:

|  | snitt Jaccard mot ekte vindu | korrelasjon mellom treff og PO-nummer |
|---|---|---|
| fast uke 16–24 | 0,516 | **r = −0,928** |
| midtpunkt ± 20 d | **0,750** | **r = −0,028** |

Det er hele grunnen til at denne varianten kan brukes der
kontrollvarianten ikke kunne. Kontrollen bommet ikke bare — den bommet
**systematisk med breddegrad**, og var dermed konfundert med den
variabelen som slår alle prediktorene. Restfeilen i midtpunktsvinduet er
støy, ikke en gradient.

Det påstås ikke at ±20 dager er kildens vindu. 2020s ekte vinduer varer
30 til 61 dager, snitt 50,5, og de er ikke symmetriske om medianen.
Jaccard 0,750 er tallet på hvor godt konstruksjonen treffer.

## Hva vindusrettingen faktisk gjorde

Kontrollvarianten er kjørt uendret ved siden av, og forskjellen mellom
de to er lærerik:

| | fast uke 16–24 | midtpunkt ± 20 d |
|---|---|---|
| samlet R² | 0,5078 | **0,4855** |
| innen-PO R² | 0,3194 | **0,4862** |
| Spearman rho | +0,7956 | +0,7833 |

Det **samlede** leddet gikk litt NED og det **innen-PO** gikk kraftig
OPP — fra 0,32 til 0,49, over 48 frihetsgrader.

Det er nøyaktig mønsteret man skulle vente hvis det faste vinduets
samlede R² var delvis båret av breddegradskonfunderingen. Da vinduet
sluttet å følge breddegrad, forsvant noe av mellom-PO-samsvaret, mens
sammenhengen INNEN hvert område ble tydeligere. Kartet ble svakere;
mekanismen ble sterkere.

## Hvilken forklaring peker dette mot

Notatet fra 31.08 stilte tre. Utfallet peker mot **forklaring 1 —
transport dominerer** — men svakere enn et rent nullresultat ville gjort,
og forklaring 2 er fortsatt ikke eliminerbar.

1. **Transport dominerer.** Kildeleddet forklarer 49 % av variasjonen i
   ROC og kommer ikke i nærheten av 0,67. Nedre kant av intervallet
   (0,2895) ligger under den fulle Stien-proxyens 0,494, så vi kan ikke
   engang si at dette er sikkert bedre enn proxyen mot kategori. Over
   halvparten av ROC blir bestemt et sted mellom kildeleddet og utfallet,
   og LADiM + NorKyst800 er det som står der.
2. **Vår PO-aggregering ødelegger det.** Fortsatt ikke eliminerbar. HI
   regner per lokalitet; vi har N_fisk bare per produksjonsområde. Den
   grensen står til fiskeantall per lokalitet publiseres, og et negativt
   utfall kan derfor ikke skille 1 fra 2 — som 31.08-notatet sa på
   forhånd at det ikke ville kunne.
3. **Ekspertgruppens øvrige innspill dominerer kategorien.** Uberørt.
   Denne kjøringen måler mot ROC, ikke mot kategorien.

**Det innen-PO-leddet bestod, er ikke en trøstepremie.** Det er leddet
som skiller en mekanisme fra et kart, og med R² 0,4862 over 48
frihetsgrader er sammenhengen innen ett produksjonsområde over år klart
skilt fra null. Kildeleddet FØLGER ROC innen et område. Det bestemmer
den bare ikke.

## Hva resultatet IKKE er

Det er ikke hovedvarianten slik den ble forhåndsregistrert 31.08. Den
krevde kildens faktiske vindu per (po, år), og for 2022–2025 finnes ikke
den størrelsen — verken hos oss eller hos ekspertgruppen. Utfallet er
**kildeleddet mot ROC med et konstruert vindu**, og Jaccard 0,750 hører
med hver gang tallet siteres.

Erstatter `2026-09-01-kildeledd-mot-roc-resultat.md`, som konkluderte med
at regelen ikke kunne evalueres.

## Hva som ville snudd det

- **Fiskeantall per lokalitet blir offentlig.** Da kan forklaring 2
  elimineres direkte, og et negativt utfall blir et utsagn om transport
  alene i stedet for om transport ELLER vår aggregering.
- **Ekspertgruppen begynner å oppgi vinduet som datoer igjen**, slik
  2020-rapporten gjorde, eller Vedlegg I arkiveres ved siden av
  hovedrapporten. Da forsvinner den siste frie parameteren.
- **En ROC fra en annen modellkjede enn LADiM/NorKyst800.** Da finnes det
  igjen en uavhengig fasit, og den opprinnelige hypotesen kan stilles på
  nytt.

## Kjøringen

`analyse/kildeledd_mot_roc.py`, kjøringslogg
`analyse/ut/kildeledd_mot_roc.kjoring.log`. Prediktoren er FULL
kildeledd-serie (`kildeledd.les_serier()["full"]`), ført i loggen med
innholds-hash. Utfallet er lest gjennom `kjoringslogg.les(...,
versjonsvalg=ALLE)` og slått sammen per (år, po, felt) på seneste
`published_at` — `GJELDENDE` ville skjult 2024s ROC bak 2025-rapportens
kategorirevisjon.

Snapshotene er skrevet av `backfill.py --kilde ekspertgruppen
--rapporter --reparse`, som leser de arkiverte kroppene framfor å hente
på nytt. 13 år re-parset, **ingen changelog-rader**: forskjellen mot
forrige versjon er vår egen parser, og en `revidert`-rad ville påstått at
ekspertgruppen ombestemte seg om noe vi selv leste feil.
