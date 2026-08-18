---
dato: 2026-08-16
tittel: Feil isoleres ved import, ikke bare ved kjøring
status: gjeldende
commit: 40a32ee
---

# Feil isoleres ved import, ikke bare ved kjøring

**Bestemt:** `registry.discover()` fanger importfeil per kildefil og gjør
den om til en `KnektKilde` som feiler i `fetch()`. Kilder registreres bare
fra modulen de er definert i.

**Hvorfor:** `runner.py` lovet at én knekt kilde koster én kilde én uke.
Løftet holdt ikke: en kildefil som ikke lot seg importere krasjet
`discover()` før `run_all` startet, og drepte hele kjøringen — også de
friske kildene. Verifisert ved å legge en fil med ugyldig import i
`sources/`. Dette er nøyaktig scenarioet den kvelden Akvakulturregisteret
aktiveres og noe skrives feil.

Definisjonssjekken løser en annen sak: `inspect.getmembers` plukket også
opp importerte klasser, så gjenbruk av en baseklasse mellom to kilder ville
kjørt den ene to ganger og doblet observasjonene. Reprodusert.

**Om kontrakten:** Dette krevde endring i `core/`, som normalt er signalet
om at noe er galt. Her var det motsatt — endringen reparerer et løfte
kjernen allerede ga, uten å utvide hva en kilde må vite. En ny kilde er
fortsatt én ny fil.

**Ville snudd det:** Ingenting. Uten dette er hver ny kildefil et
sjansespill for hele historikken.
