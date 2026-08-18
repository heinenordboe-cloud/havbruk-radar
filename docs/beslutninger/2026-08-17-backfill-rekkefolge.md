---
dato: 2026-08-17
tittel: Backfill kommer etter de forsvinnende kildene, ikke før
status: gjeldende
commit: 
---

# Backfill kommer etter de forsvinnende kildene, ikke før

**Bestemt:** Historiske data hentes inn, men først etter at kildene som
overskriver seg selv er i drift. Backfill-observasjoner merkes med
eget felt som skiller «da vi så det» fra «da det gjaldt».

**Hvorfor rekkefølgen:** Kilder deles i tre. Rene arkiver
(Regnskapsregisteret, biomassestatistikk, laksepris) gir like mye data
om et år som i dag. Kilder som overskriver seg selv (Akvakulturregisterets
kapasitet og trafikklys, lusetall, stillingsannonser) mister en
uke hver uke som går. Å bruke en kveld på backfill koster ingenting
senere; å utsette en forsvinnende kilde koster permanent.

**Hvorfor merking:** `observed_at` betyr «da vi så det». En rad fra
Regnskapsregisteret for 2022 er observert i dag, om noe som skjedde i
2022. Blandes de to, kan ikke tidsserien skille mellom når noe skjedde
og når vi fikk vite det — og hele endringsloggen blir upålitelig.
Feltet må finnes før første backfill, ikke etter.

**Ikke verifisert:** Brregs oppdateringsendepunkt kan muligens gi
selskapshistorikk bakover. Hvor langt tilbake, og om endringene er
tidsstemplet per felt eller kun per enhet, er ukjent til det er testet.

**Ville snudd det:** At et arkiv viser seg å ha begrenset levetid — at
en etat fjerner historiske årganger. Da flyttes den kilden opp i
prioritet, fordi den ikke lenger er et arkiv.
