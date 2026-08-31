---
dato: 2026-08-31
tittel: Månedlig N_fisk bæres flatt over ukene, ikke interpolert
status: gjeldende
commit: [fylles inn]
---

## Hva som ble bestemt

I kildeleddet (`kildeledd.py`) ganges hver uke med **beholdningen ved
slutten av sin egen måned**. N_fisk interpoleres ikke mellom
månedsmidtpunkter.

Måneden er **måneden i mandagens dato** — kildens egen `observed_at` —
ikke en måned regnet ut av ukemidten. En uke som krysser et månedsskifte
havner i mandagens måned.

Valget står som `aggregering = "baer_maaned"` på hver eneste rad i begge
utdatafilene, og i kjøringsloggen.

## Hvorfor

Lus og temperatur er ukentlige. `BEHFISK_STK` er månedlig, og er
dessuten **beholdningen ved månedslutt** — et øyeblikksbilde, ikke et
snitt over måneden. Begge sammensetninger er forsvarlige; det
uforsvarlige ville vært at valget ikke framgår av output.

Tre grunner, i rekkefølge etter vekt:

1. **Det er en beholdning, ikke en rate.** En interpolasjon mellom to
   månedslutt antar at bestanden vokser jevnt gjennom måneden. Det gjør
   den ikke: utsett og slakt er klumpete hendelser, og
   `utsett_smolt_antall` og `uttak_antall` i den samme fila er
   MÅNEDSSUMMER — de sier hvor mye som skjedde, ikke når i måneden. En
   glatt kurve ville påstått en tidsprofil ingen kilde har oppgitt.
2. **Sporbarhet.** Hver ukeverdi peker tilbake på nøyaktig ett publisert
   tall. Med interpolasjon er hver ukeverdi et tall vi fant på, som ikke
   finnes hos Fiskeridirektoratet, og en leser som slår opp fila finner
   ikke igjen noe.
3. **Presedens.** `analyse/lusepress_mot_fasit.nfisk_for_uke` avviser
   allerede interpolasjon med samme begrunnelse — «en interpolasjon
   mellom to månedslutt ville vært et tall vi fant på». To steder som
   regner det samme leddet skal ikke velge hver sin vei.

## Prisen, som ikke skal bortforklares

Serien får **sprang ved månedsskiftene**. Et sprang i FULL-serien som
ikke finnes i DELVIS-serien er et månedsskifte i N_fisk, ikke en
hendelse i sjøen. Det står i `oversikt.html` ved siden av figurene, ikke
bare i koden.

En uke som krysser månedsskiftet er dessuten grovere koblet enn en
dag-for-dag-vekting ville vært: uke 18/2021 begynner 3. mai og teller
som mai, uke 17/2021 begynner 26. april og teller som april selv om fire
av dens sju dager er i mai.

## Hva som ville snudd det

- **Fiskeridirektoratet publiserer beholdning oftere enn månedlig.** Da
  er valget borte, ikke bare endret.
- **Utsett og uttak blir datert innenfor måneden.** Da finnes det en
  målt tidsprofil å fordele etter, og fordelingen ville vært lest
  framfor antatt — det er forskjellen på denne beslutningen og en
  interpolasjon.
- **En måling viser at valget flytter tallet mye.**
  `analyse/lusepress_mot_fasit.aggregeringsvariantene` kjører allerede
  to varianter side om side for vindusanalysen. Viser en tilsvarende
  måling på den ukentlige serien at flat bæring og interpolasjon spriker
  vesentlig, må begge stå i output framfor at én velges.
