---
dato: 2026-09-23
tittel: eier_type inn i personhooken — premisset for å la den stå ute sviktet
status: utkast
commit: [fylles inn]
---

# `eier_type` inn i hooken

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt 1: `eier_type` er med i `eierskap.fjern_egne_personer()`

Fram til i dag sto den ukentlige seriens `eier_type` uttrykkelig utenfor
hooken, med denne begrunnelsen — ordrett fra docstringen, og med en test
som holdt den (`test_eier_type_staar_UTTRYKKELIG_ikke_i_hooken`):

> «en slik rad forsvinner fra neste snapshot av seg selv, fordi
> `fetch()` og `parse()` stopper den — målt på arkivkroppen fra 14.09,
> der dagens kode dropper H-FJ-0018 helt»

**Resonnementet var riktig. Premisset ble usant.**

MÅLT 23.09.2026:

    parse() på arkivkroppen 2026-09-14   H-FJ-0018: 0 observasjoner
    parse() på arkivkroppen 2026-09-21   H-FJ-0018: 0 observasjoner
    snapshotet 2026-09-21 på disk        H-FJ-0018: 16 rader

Filteret virker. Snapshotet ble bare ikke skrevet av det: den ukentlige
innsamlingen 21.09 kjørte kode fra før 16.09, fordi 47 commits lå
upushet. Det er F15, og CLAUDE.md regel 7 er skrevet samme dag om samme
hendelse.

Fila er append-only og blir stående. `eierskap` er `henting`-partisjonert,
så `publiseringsvakt.hviteliste()` leser NØYAKTIG den fila — og **gjorde
dermed rede for navnet på en personform**. Lesedøra kan ikke fjerne
raden: `organisasjonsform` er `None` for den, og det er unntaket regel 7
navngir.

Det som holdt navnet borte fra sidene var at `_lokalitetens_selskap()`
spør `er_person()`. Det er én funksjon, ikke en dør. En visning som ikke
spurte, ville fått porten til å si grønt.

Målt etter endringen: navnet og orgnummeret er ute av hvitelista, og
«uten eier» går fra 65 til 66 lokaliteter. Den ene er 11593, og at den
står uten innehaver er riktig svar.

## Bestemt 2: generatoren kaller hooken, ikke bare porten

`publiseringsvakt._rammene_for()` har kalt `fjern_egne_personer()` siden
19.09. `nettsted._siste()` gjorde det ikke. To lesemåter av samme kilde
som kan svare ulikt er formen F6 og F7 hadde — og her var retningen den
farlige: **porten så færre rader enn siden**.

`nettsted._uten_egne_personer()` er nå det ene stedet generatoren gjør
det, med samme rekkefølgevern: en hook kan bare fjerne.

## Hva som IKKE er løst, og står som kvittert

Tre personformnavn står fortsatt på 14 lokalitetssider, i feltet
`tildelt_navn` — den tillatelsen opprinnelig ble tildelt, i ett tilfelle
i 1995. Porten melder dem som `personform`, og de er kvittert av Heine
19.09.2026.

De kan ikke lukkes med data: **`tildelt_type` finnes ikke**. Feltet er
`None` på alle fire tillatelsene, og den eneste prøven som ville truffet
er endelsen i navnet. Den brukes til Å OPPDAGE i porten, der en falsk
positiv koster en kvittering. Å bruke den til Å SKJULE er en annen
retning: da koster en falsk positiv en opplysning som forsvinner uten at
noen ser det.

Valget er Heines, og kvitteringen er mekanismen for det.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
