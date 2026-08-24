---
dato: 2026-08-24
tittel: Miljøvariabler sjekkes samlet før innsamlingen, ikke ved første bruk
status: utkast
commit: 
---

# Nøklene sjekkes før innsamlingen, samlet

> **UTKAST.** Skrevet ut fra den røde kjøringen og diffen, ikke som
> ferdig vurdering.

**Bestemt:** `run.py` spør `core/miljo.py` om alle aktive kilder har
miljøvariablene sine FØR frekvensvakten, og dør med én melding som
navngir samtlige manglende. `config.get()` beholder sin oppførsel —
den kaster fortsatt først når verdien brukes, og feller fortsatt bare
sin egen kilde.

## Hva som skjedde

Mandag 24.08 05:00 UTC feilet lusetall i cron med

    RuntimeError: BARENTSWATCH_CLIENT_ID er ikke satt, men kreves av
    config-nøkkelen 'kilder.lusetall.client_id'

Meldingen var riktig. Tidspunktet var ikke.

`samle.yml` har eksponert begge variablene til «Samle inn» siden
`adf1031`, 18.08. Det var aldri eksponeringen som manglet — det var
Actions-secretsene i datarepoet. `${{ secrets.X }}` på en secret som
ikke finnes blir **tom streng**, ikke en feil, så steget satte
variabelen og satte den til ingenting.

Feilen kunne dermed leve i seks dager:

| dag | kjøring | hvorfor den ikke traff |
|---|---|---|
| 18.–22.08 | backfill | kjørte lokalt, der skallet har `~/.havbruk.env` |
| 22.08 (lør) | test-dispatch | `finnes_allerede()` hoppet over lusetall |
| 24.08 (man) | cron | første kjøring som faktisk kalte `fetch()` |

## Skillet

`config.get()` kaster ved BRUK med vilje, og den beslutningen står:
en manglende BarentsWatch-nøkkel skal felle BarentsWatch, ikke
Enhetsregisteret. Men «ved bruk» har to konsekvenser som ikke ble tenkt
igjennom da den ble tatt:

1. **Én om gangen.** Manglet begge nøklene, ville den navngitt den
   første, blitt fikset, og navngitt den andre uka etter. Med ukentlig
   cron er det én tapt uke per nøkkel.
2. **Aldri, for en kilde som hoppes over.** Frekvensvakten og
   `finnes_allerede()` er begge bygget for å SPARE oss et API-kall. De
   sparer oss like effektivt for oppdagelsen av at kallet ikke ville
   virket. En feil som bare avdekkes av kilder som faktisk kjører, er
   usynlig nøyaktig så lenge kilden ikke kjører.

Sjekken ligger derfor foran begge vaktene, og kjører på en kilde som
skal hoppes over i dag også. En manglende nøkkel er feil i OPPSETTET,
ikke i denne kjøringen — den skal si fra den dagen den oppstår, ikke
den dagen den rammer. Konkret ville lørdagens dispatch da vært rød.

Dette er samme form som F4, F6 og F7 (se `CLAUDE.md` punkt 1b), men
ikke samme innhold: der handlet det om et tidspunkt slått opp to
steder, her om en forutsetning som bare kontrolleres på den ene veien
gjennom koden der den brukes. Fellesnevneren er kontrollen som
korrelerer med det den skal bevise i stedet for å spørre om det —
samme som ENK-åpningen i punkt 3.

## Hvorfor sjekken ikke kjenner noen kilder

`core/miljo.py` leser ingen kildekode og har ingen liste over nøkler.
Den leter etter markøren `config.MANGLER`, som `_expander()` legger
igjen der en `${...}` ikke lot seg slå opp, i `kilder.<navn>`-blokka
til hver kilde `registry.discover()` ga tilbake — pluss alt utenfor
`kilder:`, som gjelder uansett hvem som kjører.

En ny kilde som trenger en nøkkel får den derfor med ved å skrive
`${NAVN}` i sin egen blokk i `config.yml`. Ingen registrering, ingen
endring i `core/` — CLAUDE.md punkt 1 holder.

Invarianten modulnavn == kildenavn er det som gjør `kilder.<navn>` til
riktig oppslag. Den er allerede håndhevet av
`test_modulnavn_er_kildenavn`.

## Hva den ikke fanger

Bare `${NAVN}` i `config.yml`. Leser en kilde `os.environ` direkte i sin
egen fil, er den usynlig herfra. Det er ikke en mangel som skal lappes
med mer skanning — det er begrunnelsen for at nøkler hører hjemme i
`config.yml`. `HAVBRUK_DATA_DIR` er bevisst utenfor: den har fallback i
`core/paths.py` og er valgfri, ikke påkrevd.

`backfill.py` har ikke sjekken. Den kjøres for hånd, av et menneske som
ser feilen med en gang, og har ikke frekvensvakten som kan skjule den.

## Verifisert

`python run.py` med begge variablene fjernet, mot en tom datamappe:
stopper etter «Kjøring 2026-08-24», navngir begge, `exit 1`, ingen
`[vent]`- eller `[har]`-linjer, ingenting skrevet. Med variablene satt:
`miljo.manglende(registry.discover())` er tom for alle tre aktive
kilder. `tests/test_miljo.py`, 11 tester; suiten 190 grønne.

## Ville snudd det

Hvis en kilde noen gang legitimt skal kunne kjøre UTEN sin nøkkel — en
kilde med både anonym og autentisert modus, der den anonyme er god nok.
Da er en manglende nøkkel ikke lenger en feil i oppsettet, og sjekken
måtte spurt kilden i stedet for configen. Det finnes ingen slik kilde
i dag, og en kilde som leverer mindre uten å si fra er nettopp det
prosjektet ellers er bygget for å unngå.
