---
dato: 2026-08-17
tittel: Én verdi per (entity_id, field, source) per kjøring
status: gjeldende
commit: 9880ed9
---

# Én verdi per (entity_id, field, source) per kjøring

**Bestemt:** Invarianten i observasjonsformatet er én verdi per
`(entity_id, field, source)` per kjøring. Den håndheves i
`snapshot.to_frame()`.

**Hvorfor ikke i kilden:** Enhetsregisteret søker på ni NACE-koder, og
et selskap som treffer to av dem returneres to ganger. Fristelsen er å
deduplisere der feilen oppsto. Men mønsteret er ikke særegent for
Brreg — enhver kilde som filtrerer på en kodeliste kan få samme entitet
fra flere søk, og en fiks i kilden lar neste kilde arve problemet på
nytt. Invarianten tilhører formatet, ikke kilden som tilfeldigvis brøt
den først.

**Hvorfor ikke bare i diff:** Da blir de dupliserte radene stående i
parquet-fila. Snapshotet er det varige artefaktet som ikke kan
gjenskapes, og hver framtidige leser — dashbord, analyse, volumvakt —
måtte kjenne til feilen og filtrere den bort selv. `to_frame()` er
dessuten trakta `run.py` sender alt gjennom før både diff og skriving,
så én fiks dekker begge.

**Hvorfor `source` er med i nøkkelen:** To KILDER som observerer samme
felt på samme entitet er kryssvalidering, og det er noe av det mest
verdifulle systemet kan produsere. Det er samme kilde to ganger som er
feilen. Uten `source` i nøkkelen ville invarianten stilltiende kastet
den ene av to uavhengige observasjoner.

**Hvorfor diff også deduplicerer, uten at det er samme ansvar to
steder:** `to_frame()` håndhever invarianten på det vi SKRIVER.
`diff.compare()` LESER snapshots skrevet før invarianten fantes, og de
filene er append-only — de kan ikke rettes. Joinen på
`(entity_id, field)` fanner ut mot et duplisert grunnlag, og da
rapporteres samme endring én gang per duplikat den uka verdien endrer
seg. Verifisert: to like gamle rader ga to identiske endringer.
Endringsloggen er produktet, og den kan ikke rapportere samme hendelse
to ganger. Uten forsvaret i diff ville mandagens changelog
dobbeltrapportert hver endring på de 15 berørte selskapene.

Skillet er altså: den ene siden håndhever en regel framover, den andre
forsvarer seg mot historikk den ikke har lov til å reparere.

**Målt på ekte data** (re-parse av arkivet fra 17.08.2026):

    observasjoner før    27074
    etter to_frame()     26571
    fjernet                503

    entiteter  938 -> 938
    feltnavn    32 -> 32

Null verdikonflikter blant duplikatene — alle 503 var identiske rader
uten informasjonsinnhold. Tapsfriheten er verifisert ved semi-join mot
originalen: alle 26571 beholdte rader finnes uendret der, og
`original.unique()` er nøyaktig lik resultatet.

**Prisen:** Enhetsregisteret faller fra ~27074 til ~26571 observasjoner
for de gamle kodene. Volumvakten har ingen referanse ennå, så nivået
etableres på det deduplikerte tallet ved første kjøring — ingen falsk
alarm.

**Ville snudd det:** Ingenting. Men merk: skulle en framtidig kilde
legitimt trenge flere verdier per nøkkel — flere målinger av samme felt
på samme entitet i samme kjøring — er det FORMATET som må utvides, med
et felt som skiller dem. Invarianten skal ikke svekkes for å få plass
til det.
