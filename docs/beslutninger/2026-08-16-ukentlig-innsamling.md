---
dato: 2026-08-16
tittel: Ukentlig innsamling, ikke daglig
status: gjeldende
commit: 
---

# Ukentlig innsamling, ikke daglig

**Bestemt:** Cron mandag 05:00 UTC.

**Hvorfor:** Enhetsregisteret oppdateres i praksis daglig, men endringene
som betyr noe — kapasitet, eierskap, konkurs — beveger seg på måneders
skala. Daglig gir 52 ganger mer data uten 52 ganger mer signal, og bytter
et lesbart repo mot støy.

**Ville snudd det:** At det viser seg at endringer skjer og reverseres
innenfor en uke, altså at ukentlige snapshots går glipp av noe. Måles
best etter noen måneders drift.

**Status:** Skal opp til ny vurdering. Se `02_apne_sporsmal.md`.
