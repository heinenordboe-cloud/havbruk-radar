---
dato: 2026-08-17
tittel: Volumvakt, og hvorfor den måtte skrives om samme dag
status: gjeldende
commit: 3ab3632
---

# Volumvakt, og hvorfor den måtte skrives om samme dag

**Bestemt:** `health.py` sjekker antall observasjoner mot et lagret
friskt referansenivå i `health.json`. Faller det under `min_andel`
(default 0,90, overstyrbar per kilde), går kilden i samme `nede`-liste
som en kilde som ikke svarer, og blir der til nivået er tilbake eller
et nytt nivå er bevisst kvittert.

**Hvorfor vakten:** Alarmen fanget kun kilder som er nede. En kilde som
svarer men leverer feil var usynlig. `SCHEMA` i `snapshot.py` droppet de
tre proveniensfeltene stille tidligere i dag — kode riktig, tester
grønne, felter borte. Fanget kun fordi noen så etter.

**Hvorfor omskrivingen:** Første versjon sammenlignet mot forrige
snapshot. Simulert over fem uker med vedvarende brudd fyrte den i uke 3
og tidde i uke 4 og 5 — det ødelagte tallet ble neste ukes normal.
Det er nøyaktig feilmodusen beslutningen fra 16.08 fjernet fra
nede-alarmen, gjenskapt i ny form. En alarm som normaliserer bruddet er
verre enn ingen alarm.

**Kvittering:** Faller et register reelt, må nivået kunne aksepteres —
men som en handling, ikke automatisk. Uten det blir alarmen permanent
rød, og alarmtretthet er reverseringskriteriet fra 16.08.

**Terskelen er en vurdering, ikke et funn.** Fem samme-dags-snapshots
viser 0 % varians, men det beviser bare at et tregt register er stabilt
innenfor én dag. Ukentlig drift er ukjent til det finnes måneders data.

**Asymmetrisk med vilje:** en økning varsler ikke. Systemets feilmodus
er stille tap; en økning mister ingenting og synes i commit-meldingen.

**Rekkefølgeavhengighet:** `health.oppdater()` kalles etter
`snapshot.write()`, så dagens snapshot ligger på disk når vakten leser
`previous()`. Den overlever kun fordi datofilteret utelukker samme dato.
Inkluderes samme dag, sammenligner vakten dagen mot seg selv, får alltid
100 %, og dør stille. Dette er systemets andre subtile
rekkefølgeavhengighet.

**Ville snudd det:** At terskelen utløses av normal variasjon oftere enn
den fanger reelle feil. Da justeres tallet med data i hånd — vakten selv
er riktig.
