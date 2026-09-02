---
dato: 2026-09-01
tittel: "Kildeleddet mot ROC: stoppregelen kan ikke evalueres — utvandringsvinduet mangler for hver eneste celle"
status: erstattet-av 2026-09-01-kildeledd-mot-roc-bestod-ikke.md
commit: 1601d5e
---

> **ERSTATTET 01.09.2026, senere samme dag.** Premisset under — at
> vinduet bare manglet et uttrekk — var feil. Kilden SLUTTET å
> publisere utvandringsvinduet etter 2020, og det som finnes for
> 2021-2025 er midtpunktet alene. Regelen er siden evaluert med et
> konstruert vindu og BESTOD IKKE. Se
> [2026-09-01-kildeledd-mot-roc-bestod-ikke.md](2026-09-01-kildeledd-mot-roc-bestod-ikke.md).

## Utfallet

**Stoppregelen kan ikke evalueres.** Ikke «bestod», ikke «bestod ikke» —
hovedvarianten har **n = 0**.

Regelen var pre-registrert mot ekspertgruppens FAKTISKE utvandringsvindu
per (po, år). Vinduet finnes på disk for **13 celler, alle i 2020**. ROC
finnes for **58 celler, alle i 2021–2025**. Snittet er tomt. Alle 58
cellene falt ut fordi vinduet mangler, slik regelen krever at de skal —
de fylles ikke med et standardvindu.

    ROC-celler lest       58   2021:11  2022:11  2023:12  2024:12  2025:12
    utvandringsvindu      13   2020:13
    overlapp               0

## Hva regelen sa

Fra `2026-08-31-hypotesen-omdefineres.md`, satt 31.08 og regnet på nytt
01.09 — begge ganger før noe tall var sett:

> R² ≥ 0,67 samlet **og** innen-PO R² ≥ 0,25. Begge må holde.

Regelen er ikke rørt i denne kjøringen.

## Kontrollvarianten, som ikke er svaret

Fast uke 16–24, kjørt som spesifisert for å måle hva vindusvalget betyr:

| | verdi | mot regelen |
|---|---|---|
| n | 58 celler, 12 PO | |
| samlet | r = +0,7229, **R² = 0,5226** | 95 % CI R² = [0,326, 0,684], df = 55 — **bestod ikke** (< 0,67) |
| innen PO | r = +0,5489, **R² = 0,3013** | df = 46 — **bestod** (≥ 0,25) |
| Spearman rho | **+0,8057** | like-for-like-tallet notatet krever |

**Dette tallet kan ikke tre inn for hovedvarianten,** og det er ikke en
formalitet. Overlappen mellom uke 16–24 og ekspertgruppens eget vindu
ble målt 26.08.2026 til 100 % i PO1–2 og **0 % i PO13**, monotont
fallende med breddegrad. Feilen er altså konfundert med nøyaktig den
variabelen som slår alle prediktorene, og et for lavt R² her kan ikke
skilles fra vindusskjevheten. Det er hele grunnen til at
hovedvarianten er hovedvarianten.

Ingen tredje variant er kjørt.

## Hva kontrollen likevel sier

Den kan ikke avgjøre regelen, men den er ikke uten innhold, og det skal
stå like tydelig som et negativt resultat:

- rho +0,81 og R² 0,52 er **sterkere enn noe den fulle Stien-proxyen
  oppnådde mot kategori** (rho +0,703, rho² 0,494). Kildeleddet mot ROC
  er en tettere sammenheng enn kildeleddet mot kategori — som det skal
  være, siden ROC ligger nærmere kildeleddet i kjeden.
- **Innen-PO-leddet bestod**, med R² 0,30 over 46 frihetsgrader. Det er
  det leddet som skiller en mekanisme fra et kart, og det utelukker at
  sammenhengen bare er geografi.

Med en KJENT skjev aggregering forklarer kildeleddet altså halvparten av
variasjonen i ROC, og en tredjedel av den innen produksjonsområde.

## Hvilken forklaring peker dette mot

Notatet stilte tre:

1. **Transport dominerer.** Kontrollen taler IMOT at den dominerer helt
   — 52 % samlet og 30 % innen-PO overlever en aggregering som er
   systematisk feil i nord. Men den kan ikke måle hvor mye som er igjen
   når vindusfeilen fjernes.
2. **Vår PO-aggregering ødelegger det.** Fortsatt ikke eliminerbar. HI
   regner per lokalitet; vi har N_fisk bare per produksjonsområde, og
   den grensen står til fiskeantall per lokalitet publiseres.
3. **Ekspertgruppens øvrige innspill dominerer kategorien.** Uberørt av
   denne kjøringen — den måler mot ROC, ikke mot kategorien.

**Ingen av de tre er avgjort.** Det som er avgjort er at spørsmålet ikke
kan stilles med det som ligger på disk i dag.

## Det som blokkerer, og som var kjent

`2026-08-26-full-stien-proxy-forklarer-ikke-kategoriene.md` navnga dette
som steg 1 for neste økt:

> «Vinduet per PO er 13 rader i en fasitfil med proveniens, samme mønster
> som `ekspertgruppen-po-kategori.csv`. Det retter en kjent, målt,
> breddegradskonfundert feil. Det skal gjøres uansett hva man mener om
> hypotesen.»

Det steget er ikke tatt. Uten det kan stoppregelen ikke kjøres, og med
et standardvindu ville den svart på et annet spørsmål enn den ble
skrevet for.

Merk hva som IKKE er nok: å bruke 2020-vinduene på 2021–2025. Det er å
fylle et hull med et standardvindu, og notatet fra 26.08 sier uttrykkelig
at 2020-vinduene er «lest maskinelt ut av PDF-en for 2020 og brukt på
alle årene» — en tilnærming som «må leses av et menneske og føres som
fasit med kilde og sikkerhet før de brukes i et resultat».

## En lesefeil funnet underveis

Første kjøring ga n = 46, ikke 58. Årsaken var i analysen, ikke i
dataene: `kjoringslogg.les()` gir ÉN fil per dato, og `GJELDENDE` er den
sist utgitte. For 2024 er det 2025-rapportens revisjon, som restaterer
BARE kategorien — 26 observasjoner mot 2024-rapportens 50. Hele 2024s
ROC forsvant, og utvandringsvinduene likeså, siden 2020 er revidert av
2021-rapporten.

En revisjon som ikke nevner et felt har ikke trukket feltet tilbake.
`kjoringslogg.ALLE` er lagt til: hver versjon av hver dato, ført i loggen
som før, og kalleren slår sammen per (år, po, felt) på seneste
`published_at`. Vakten mot BLANDEDE versjonsvalg er urørt — ALLE er ett
valg, ikke en blanding, og den vakten feller fortsatt et forsøk på å
lese samme kilde med to valg.

Hadde feilen stått, ville den senket n med 20 % og gjort det usynlig.

## Hva som ville snudd det

- **Utvandringsvinduet per (po, år) som fasit**, lest av et menneske med
  kilde og sikkerhet. Da kan regelen kjøres som skrevet, og først da er
  et utfall et utfall.
- Ekspertgruppen begynner å oppgi vinduet i rapportene igjen slik
  2020-rapporten gjorde. Da leses det av kilden i stedet for å føres for
  hånd.
- Fiskeantall per lokalitet blir offentlig, slik at forklaring 2 kan
  elimineres direkte framfor å stå som forbehold ved siden av hvert tall.

## Kjøringen

`analyse/kildeledd_mot_roc.py`, kjøringslogg
`analyse/ut/kildeledd_mot_roc.kjoring.log`. Prediktoren er
`kildeledd-full.parquet` (5798 rader, 448 uker, 13 PO, 2017-10-02 ..
2026-04-27), ført i loggen med innholds-hash. Utfallet er lest gjennom
`kjoringslogg.les(..., versjonsvalg=ALLE)`.
