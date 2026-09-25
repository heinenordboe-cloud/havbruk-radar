---
dato: 2026-09-23
tittel: Selskapsdata står for seg — 402 av 440 var registervedlikehold
status: utkast
commit: [fylles inn]
---

# Selskapsdata står for seg

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Målingen

Etter at tellingen ble rettet sto uke 39 med 440 telte endringer.
**402 av dem — 91 % — var ett eneste slag:** opplysninger om selskaper
fra Enhetsregisteret. 369 av de 402 var `antall_ansatte`.

Radene er ekte. Hver eneste er kontrollert mot Brønnøysunds egne
API-kropper fra 14.09 og 21.09, med null avvik
(`docs/MALING-UKE-39.md`). Det er ikke sannheten som er problemet.

Et tall der 91 % er A-ordningens månedlige oppdatering av ansatt-tall,
svarer ikke på «hva skjedde i havbruket denne uka». Det svarer på «hvor
mange felt endret seg i et register», og de to ser like ut helt til man
spør hva de betyr.

## Bestemt 1: egen etikett, «Selskapsdata»

Var «Selskapsopplysning». Dekker ansatte, næringskode, adresse,
regnskap, kapital og konkurs.

## Bestemt 2: telles ikke i ukas overskriftstall

Uke 39 sier nå **38**, ikke 440 og ikke 812.

    453   alle radene i uka
    402   selskapsdata, står for seg
     13   felt som kom eller gikk (fra forrige runde)
     38   overskriftstallet

Samme asymmetri som `utvalgsutvidelse` og `revidert` i CLAUDE.md 1b-6:
radene beholdes, merkes og vises — de summeres bare ikke som aktivitet.

## Bestemt 3: tallet sier hva det teller

«38 endringer» alene lar leseren tro det er alt som skjedde. Forsiden
skriver derfor:

> 38 endringer observert i uke 39, 2026: trafikklys, tillatelser,
> oppføringer som gikk ut og lokalitetsopplysninger.
>
> 402 endringer i selskapsdata — ansatte, næringskode, adresse,
> regnskap — står for seg på ukessiden.

**Slagene i setningen bygges av dem som faktisk er der**, ikke av en
fast liste. En fast setning ville stått og løyet den uka et slag
mangler. `visningsord.liste()`.

Lenken under tabellen går til alle 453, selskapsdata medregnet.

## Bestemt 4: forsidens korte tabell viser dem ikke

De åtte radene på forsiden hentes fra `uke["ledet"]`. En forside der
sju av åtte rader er «antall ansatte: 42 → 43» er en forside som skjuler
den ene som betyr noe.

## Bestemt 5: på ukessiden i en `<details open>`

Åpen uten JavaScript, lukket av skriptet. Rekkefølgen er hele poenget:
en del som må ÅPNES av et skript er en del som ikke finnes for den som
har skript av. Det er samme regel som kopierknappen som er `hidden` til
den virker, speilvendt.

Typesiden `/endringer/<uke>/selskap/` viser dem som før, i ett bord —
der er valget alt gjort.

## Hva som IKKE ble endret

CSV-en, JSON-en og feeden har alle 453 radene. Delingen er en
VISNING, ikke et filter på dataene: den som vil ha alt, får alt, og
`docs/beslutninger/2026-09-22-gratis-mot-betalt-grense.md` gjelder som
før.

De 13 `felt_ny`/`felt_borte`-radene står fortsatt i hovedtabellen uten
å telle. De er i dag alle fra Enhetsregisteret, men slaget er ikke
knyttet til én kilde, og å folde dem bort ville skjult en
lokalitetsrad den dagen den kommer.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]

## Utvidet 24.09

Regelen gjaldt bare `endret`-radene. `ny`, `borte`, `felt_ny` og
`felt_borte` slo kildens egen regel i `endringstype()` og havnet i
hovedtallet — også når HELE kilden hører hjemme i den egne delen.

Avsnittet rett over sa at «slaget ikke er knyttet til én kilde». Det
stemmer for slaget, og det var nettopp derfor kilden måtte spørres i
stedet: `EGEN_DEL_KILDER` utledes av at en kildes `*`-regel peker på et
slag med `egen_del`, ikke av en liste.

Samme sted lå en andre feil: den tidlige returen for `borte` skrev
`type_navn = "Ute av registeret"` for hånd, mens tabellen over den sa
«Ute av vårt utvalg». Etiketten slås nå opp i `ENDRINGSTYPER`, og
raden sier det samme som oppsummeringen.

MÅLT 24.09.2026, ukas tall:

    uke        før    etter
    2026-39     38       16
    2026-38    112      109
    2026-37     50       48
    2026-36     28       26
    2026-35    123      121
    SUM        351      320

Per type, der noe flyttet seg:

    uke        type                        før   etter
    2026-39    Ute av vårt utvalg           24       2
    2026-39    Felt oppgitt første gang      6       0
    2026-39    Felt ikke lenger oppgitt      7       0
    2026-39    Selskapsdata                402     437
    2026-38    Ute av vårt utvalg           10       8
    2026-38    Ny i vårt utvalg             14      13
    2026-38    Felt oppgitt første gang     46      42
    2026-38    Felt ikke lenger oppgitt     26      23
    2026-38    Selskapsdata                 36      46
    2026-37    Ute av vårt utvalg            2       0
    2026-37    Felt oppgitt første gang      1       0
    2026-37    Felt ikke lenger oppgitt      2       0
    2026-37    Selskapsdata                 37      42
    2026-36    Ute av vårt utvalg            2       1
    2026-36    Ny i vårt utvalg              2       1
    2026-36    Felt oppgitt første gang      4       3
    2026-36    Felt ikke lenger oppgitt      2       1
    2026-36    Selskapsdata                 36      40
    2026-35    Ute av vårt utvalg            2       0
    2026-35    Felt oppgitt første gang      4       0
    2026-35    Selskapsdata                 59      65

De 22 som forsvant fra uke 39s «Ute av vårt utvalg» er selskapene
23.09-målingen allerede hadde slått opp: 20 av 29 sto fortsatt i
Enhetsregisteret og hadde byttet næringskode ut av søket vårt. De to som
står igjen er tillatelser fra `eierskap`, og de er ikke selskapsdata.
