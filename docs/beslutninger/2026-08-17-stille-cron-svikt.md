---
dato: 2026-08-17
tittel: Stille cron-svikt er en feil, ikke en stille exit
status: gjeldende
commit: e7d224f
---

# Stille cron-svikt er en feil, ikke en stille exit

**Bestemt:** `run.py --planlagt` returnerer feilkode hvis ingen kilder
er forfalt. Workflowen setter flagget kun på cron-kjøringen. Manuell
kjøring beholder stille exit.

**Hvorfor:** Frekvensvakten finnes for å hindre unødvendige skrivinger
midt i uka, og der er stillhet riktig. Men den ukentlige kjøringen har
én oppgave: garantere at uka fikk et snapshot. Returnerer den «null
samlet, alt grønt», er det ikke ingenting å gjøre — det er tapt
historikk uten varsel.

Verre: `health.py` bygger på at en rød jobb varsler. En grønn jobb som
ikke samlet noe ser identisk ut som en uke der alt gikk knirkefritt.
Dette er samme feilmodus som `health.py` selv beskriver som den
farligste i systemet.

**Utløsende observasjon:** Manuell kjøring av workflowen 17.08 ble grønn
på 11 sekunder uten å samle noe. Uten den observasjonen ville mandagens
cron gitt samme resultat, usett.

**Selvforsterkende:** `--tving` som workflow_dispatch-input gjør at
enhver manuell testkjøring midt i uka flytter «sist hentet» framover, og
øker sjansen for at neste mandag treffer fella.

**Prisen:** En rød jobb i tilfeller der data faktisk er samlet
tidligere samme uke av en manuell kjøring. Det er riktig — det betyr at
den ukentlige garantien ikke holdt.

**Ville snudd det:** At det utløses ofte nok til at det blir støy. Da
er problemet frekvensvakten, ikke alarmen.
