---
dato: 2026-09-01
tittel: "har_rensefisk og har_medikamentell_behandling er datatap hos kilden, ikke en parserfeil"
status: gjeldende
commit: e424c1e
---

## Hva som ble bestemt

De to feltene rettes **ikke**, fordi det ikke er noe å rette i vår kode.
`sources/lusetall.py` mapper riktig nøkkel og skriver nøyaktig det
BarentsWatch sender. Kilden har sluttet å fylle feltene.

Feltene beholdes i uttrekket, og innholdsvakten kvitteres **ikke** ut med
`--godta-felt`. KREVER TILSYN fortsetter å fyre hver uke.

## Diagnosen, målt mot rå-arkivet

762 arkiverte responser, 2012-01-02 til 2026-08-03. For hvert felt er
antall `True` og `False` talt i hver enkelt kropp.

| kilde-nøkkel | vårt felt | siste uke med minst én `True` | uker med bare `False` |
|---|---|---|---|
| `hasCleanerfishDeployed` | `har_rensefisk` | **2023-04-17** | 172 |
| `hasSubstanceTreatments` | `har_medikamentell_behandling` | **2024-11-11** | 90 |
| `hasMechanicalRemoval` | `har_mekanisk_fjerning` | 2026-08-03 (levende) | 0 |

Tallene 172 og 90 er nøyaktig dem innholdsvakten oppgir. Vakten teller
altså riktig, og den har telt riktig hele tiden.

## Hypotesen som ble avvist, og hvorfor

Mistanken var to ting, og begge er målt bort:

1. **Feil nøkkel i mappingen.** Nei. `hasCleanerfishDeployed` og
   `hasSubstanceTreatments` står i responsen med de navnene, i hver
   eneste av de 762 kroppene.

2. **`False` som default når feltet mangler** — samme feilklasse som
   F14, der en stedfortreder brukes som om den var tingen selv. Nei.
   Feltene er ALDRI fraværende: en telling som skiller `True`, `False`
   og `<MANGLER>` gir null `<MANGLER>` over hele serien. Det finnes ikke
   et manglende felt å gjøre om til manglende.

Og skjemaet er urørt: **null endringer i nøkkelsettet** over 762 kropper.
Kilden har ikke flyttet feltene, ikke døpt dem om og ikke sluttet å sende
dem. Den sender dem, og verdien er `False`.

Feltene HAR levd: 2012-01-02 ga 9 `True` for rensefisk og 49 for
medikamentell behandling. Det er ikke felter som aldri virket.

## Hvorfor vakten ikke skal kvitteres ut

`--godta-felt` nullstiller strekket. RUNBOOK-en sier når det er riktig:
når nivået er reelt og skal bli den nye normalen. Det er ikke tilfellet
her. Dette er datatap, og en kvittering ville gjort tapet permanent og
usynlig — vakten slutter å mase, og hullet fortsetter uke etter uke.

Kostnaden ved å la den stå er lav siden 31.08.2026: KREVER TILSYN gir
`::warning::` og ikke rød jobb, så en vakt som fyrer hver uke koster en
linje i Annotations, ikke et rødt kryss som lærer noen å ignorere alle
røde kryss. Se `2026-08-31-tilsyn-feiler-ikke-jobben.md`.

## Hva som IKKE er avgjort

**Om tallene finnes et annet sted hos BarentsWatch.** Feltene kan ha
flyttet til et annet endepunkt, eller rapporteringsplikten kan ha endret
seg. Det er ikke undersøkt — det krever et kall mot API-et som ikke er
gjort, og CLAUDE.md regel 4 sier at det som ikke er sett ikke skal
antas. Det er et spørsmål til BarentsWatch, ikke til koden.

**Om `False` betyr «nei» eller «vet ikke».** Kilden skiller ikke, og
derfor kan ikke vi det heller. Fra 2023-04-24 er `har_rensefisk` i
praksis uten informasjonsinnhold, uansett hvilken av de to det er.

## Hva som ville snudd det

- BarentsWatch begynner å sende `True` igjen — da fyrer vakten av seg
  selv og strekket nullstilles ved neste kjøring med innhold.
- Feltene finnes på et annet endepunkt. Da er det en ny lesevei å legge
  til, ikke en retting av den som finnes.
- Dokumentasjon fra BarentsWatch på at `False` her betyr «ikke
  rapportert» og ikke «nei». Da skal parseren skrive fravær, og DET
  ville vært F14-rettingen hypotesen lette etter.
