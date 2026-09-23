---
dato: 2026-09-22
tittel: Grensen mellom fri gjenbruk og avtalt uttrekk
status: utkast
commit: [fylles inn]
---

# Grensen mellom fri gjenbruk og avtalt uttrekk

**UTKAST.** Hva som er bestemt står under. «Hvorfor» og «hva som ville
snudd det» skrives av Heine.

## Bestemt

Tre nivåer, og de står på `/om/#gjenbruk` i samme rekkefølge:

1. **Fri gjenbruk med kildehenvisning.** Tallene er offentlige data,
   gjengitt uendret. En artikkel, en oppgave, en høringsuttalelse eller
   en analyse kan bruke dem fritt, mot å oppgi Kystloggen, hvilket
   øyeblikksbilde som er brukt, og med kildenes egen attribusjon
   videreført. Hver side har en ferdig referanse med uke, dato og
   sjekksum.

2. **Systematisk uttrekk av hele databasen krever avtale.** Én side, én
   uke, én lokalitets CSV er fri bruk. Å hente alt, jevnlig, for å
   bygge en egen kopi av arkivet er gjenbruk av INNSAMLINGEN og ikke av
   et tall.

3. **Bulk-tilgang og verifiserte uttrekk med sjekksum etter avtale.**

## Hva som følger av det, teknisk

- **Det lages INGEN samlet fil og intet endepunkt med hele
  endringsloggen på tvers av uker.** CSV og JSON finnes per UKE
  (`/endringer/<år>-<uke>/endringer.csv`) og per LOKALITET
  (`/lokalitet/<nr>/lusetall.csv`), og ikke noe sted som et samlet
  uttrekk.

  Det er ikke en teknisk begrensning som kan vokse bort: en samlet fil
  ville gjort nivå 2 til nivå 1 uten at noen tok beslutningen.

- **Rå-kroppene publiseres ikke.** `data/arkiv/` blir liggende der det
  ligger.

- **Sjekksummene publiseres ikke, med ett unntak:** den ene summen i
  arkivlinja på forsiden, som identifiserer nyeste øyeblikksbilde. Den
  er nok til å sitere det. En full sum-liste ville vært halve
  verifikasjonstjenesten gitt bort.

- Sitering trenger ingen avtale, og siteringsboksene på hver side er
  bygget for at den skal være mulig uten å spørre.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
