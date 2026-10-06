---
dato: 2026-10-06
tittel: Ukas tall telles på radene slik de vises — en trukket tillatelse er én hendelse, ikke to
status: utkast
commit: 5377d08
---

# Ukas tall telles på radene slik de vises

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

Erstatter regelen som sto i kodekommentaren ved `nettsted.SLAAS_INN_I`
fra 25.09.2026 (28f4e71) til 06.10.2026:

> DETTE ER VISNING, IKKE TELLING. […] Ukas tall regnes derfor før denne
> sammenslåingen og er uendret av den.

og i docstringen til `slaa_sammen_trukne()`: «TELLINGEN RØRES IKKE. Den
som kaller teller før, ikke etter». Regelen hadde aldri et eget notat.

Lukker også det åpne punktet i 2026-09-24-bokforing-og-avledede-felt.md:

> Følgen er at et trukket tillatelsesledd fortsatt gir TO hendelser der
> det skjedde én ting […] en sammenslåing måtte vist BEGGE. Åpent.

Sammenslåingen som viser begge kom dagen etter (28f4e71). Tellingen
fulgte ikke med.

## Bestemt

- Typebrikkene, overskriftstallet («N endringer observert») og «N rader
  til står i tabellen uten å telle med» regnes av radene ETTER
  `slaa_sammen_trukne()`: de radene tabellen faktisk viser. Det gjorde
  brikka «Alle N rader» allerede fra 25.09 (4b92ba1).
- En `tillatelser`-rad og en `tillatelser_trukket`-rad i samme par er
  dermed ÉN hendelse i alle tallene på siden, som i tabellen.
- To likheter skal alltid holde, og
  `test_tallene_paa_ukesiden_teller_radene_som_staar_der` krever dem:

      sum(typebrikkene)                       = «Alle N rader»
      «N endringer» + «N rader til»          = rader i hovedtabellen

- Filene endres ikke. CSV, JSON, feed og JSON-LD har fortsatt hver rad
  kilden ga (`uke["hendelser"]`, `antall_i_fila`). JSON-ens `typer`
  teller nå filas egne rader, slik at fila summerer til seg selv og ikke
  til siden.
- `tillatelser_trukket` er fortsatt IKKE erklært i `Source.avledet_av`.
  Det som er bestemt her, er bare at visningens sammenslåing også er
  tellingens. Begrunnelsen i 24.09-notatet for ikke å erklære feltet
  (ordet «trukket» er en opplysning, ikke en følge) står.

## Målt 06.10.2026, mot havbruk-radar-data

Feilen som ble sett, uke 41:

    typebrikkene summerte til   158     «Alle» sa   157
    «91 endringer» + «8 til» =   99     hovedtabellen  98 rader

Én rad: Oanes Sjø (lokalitet), `R-B-0003 (trukket)`.

Overskriftstallet per uke, før og etter:

    uke        før   etter   sammenslått   rader i fila
    2026-41     91      90             1            158
    2026-40     33      31             2             98
    2026-39     14      12             2            451
    2026-38    105     105             0            216
    2026-37     41      37             4             83
    2026-36     17      13             7             61
    2026-35    121     121             0            186

16 hendelser over sju uker. Tallene står på forsiden, ukesidene og
ukeoversikten, og alle flyttet seg samme dag.

## Endret samme dag: overskriften teller de VESENTLIGE

Bestilt av Heine 06.10.2026, etter at `vesentlighet` kom (se
2026-10-06-vesentlig-og-teknisk.md). Regelen over står: tallene telles
på radene slik de vises. Det som endres er HVILKE rader hovedtabellen
viser.

- Hovedtabellen, typebrikkene, «Alle N rader», overskriften («N
  endringer observert») og metabeskrivelsen teller bare de
  **vesentlige** radene.
- De **tekniske** står i én sammenleggbar del under hovedtabellen, med
  eget antall («23 tekniske endringer»), og telles ikke i noe tall over.
- **CSV og JSON er uendret**, byte for byte i alle sju ukene (målt mot
  bygget før endringen). Hodet deres teller som før: `antall_fil`, alle
  radene. JSON-ens `antall` er fortsatt 90 for uke 41, mens siden sier 75.
- Typesidene (`/endringer/2026-41/tillatelse/`) viser de vesentlige av
  typen i tabellen og de tekniske av typen i sin egen del.

De to likhetene fra over holder fortsatt, nå for de vesentlige:

    sum(typebrikkene)                       = «Alle N rader»
    «N endringer» + «N rader til»          = rader i hovedtabellen

Målt 06.10.2026, sidene før og etter:

    uke        overskrift      «Alle»       hovedtabell    tekniske
               før   etter    før  etter    før  etter
    2026-41     90     75     157   134      98     75        23
    2026-40     31     21      96    82      35     21        14
    2026-39     12      8     449   445      12      8         4
    2026-38    105     94     216   140     170     94        76
    2026-37     37     25      79    67      37     25        12
    2026-36     13     12      54    53      14     13         1
    2026-35    121      2     186    67     121      2       119

«Alle» rommer selskapsdataene, som ikke klassifiseres som tekniske
(reglene er skrevet for lokaliteter og tillatelser). Uke 35 er
artsbegrensningene: 118 av 119 rader er tekniske.

## Hva som ikke er dekket

- Metabeskrivelsen på ukesidene (og `og:description` og søkeindeksen)
  sa `len(hendelser)`, altså radene i fila: «158 endringer» for uke 41.
  Rettet i en egen commit samme dag, med samme tall som overskriften.
- JSON-LD-en (`Dataset.description`) sier fortsatt radene i fila, «158
  registerendringer». Den beskriver datasettet, ikke siden, og står
  urørt.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
