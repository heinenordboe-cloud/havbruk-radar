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
