---
dato: 2026-09-24
tittel: Changelogdøra leser kildens tillegg — en dør som frikjente på feil felt
status: utkast
commit: d0dc123
---

# Changelogdøra leser kildens tillegg

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt 1: `changelog.fjern_personformer()` leser unionen

Døra filtrerte på `snapshot.personentiteter()` alene, og det settet bygges
av `organisasjonsform`. I `eierskap_historikk` står formen i
`mottaker_type` og fanges bare av kildens eget tillegg. Fire entiteter i
2009-12-31.2, 2014-12-31 og 2014-12-31.2 var derfor usynlige for døra.

Døra spør nå om kildens klasse har overstyrt hooken
(`_kilder_med_eget_tillegg()`). Ingen ny liste, ingen kilde nevnt ved navn.
Probingen spørres av klassen, ikke av nyeste fil: de fire står ikke i
nyeste fil, og en probe der ville hoppet over kilden som før.

MÅLT 24.09.2026:

    kilde                 rå       fjernet før   fjernet etter
    enhetsregisteret      27970           380             380
    eierskap_historikk    30104             0              16
    alle andre                0             0               0
    SUM                 1016150           380             396

Personsettet gikk fra 106 til 111 par. Fem nye par, men +16 rader, fordi
('eierskap', 'H-FJ-0018') ikke har rader i loggen.

`LANSERING.md` punkt 5 sto som OPPFYLT 23.09 uten å være det for denne
kilden. Nettstedet var vernet av markup-porten og av at kilden er utelatt
fra endringstabellen. Changeloggen som helhet, som er det bulktilgangen
leverer, var det ikke.

Prøver: 1cb6816 bygger en kilde med formen i `mottaker_type` og ingen
`organisasjonsform`-rad, krever at døra alene ser null, og krever at raden
er ute etter `les_alt()`. `test_standardtillegget_kan_ikke_fjerne_noe`
holder påstanden snarveien hviler på. En prøve mot datarepoet ble skrevet
og fjernet: `tests/conftest.py` peker `HAVBRUK_DATA_DIR` til en engangsmappe,
så den kunne bare hoppe over seg selv. Målingen står her i stedet.

## Bestemt 2: filene skrives om gjennom døra, ikke gjennom `diff.compare()`

De to changelog-filene er skrevet om slik hver leser allerede så dem:
`changelog.fjern_personformer()` på radene som lå der.

    2014-12-31   632 -> 624 rader
                 e3993578b6ef17a319fb8d51bf20a149ed7e173f4231e250bfc9502d1041c86e
              -> 163178f2de6b8f74c155be87786707edf8cd3daf2b1ce375c06952d30d10bb01
    2015-12-31   568 -> 560 rader
                 4eff4e5b3b230f4f1b41a4d26868958a56e36a215b8b0923b19e676ac786135a
              -> 53fdf549812f8a80ec89a3da75659182254c0e8ec645c0fefe80bea69a8b7272

Bekreftet på disk med `pl.read_parquet` uten dør: 0 av de fire står igjen.
Rådata er urørt. Datarepoet: d9abfc2.

`diff.compare()` ble tørrkjørt først og ga 1304 rader for 2014 der fila
har 632, og 616 nye for 2015. Hver dato har et `.2`-snapshot fra
re-parsingen 19.09 (2014: 112 -> 624 rader), og compare mot nyeste versjon
ville skrevet nettopp det `backfill --reparse` bevisst ikke skriver: en
endring i VÅRT filter lest som en påstand om at industrien flyttet seg.
En rettelse i lesingen skal bare kunne fjerne rader.

## Bestemt 3: `tell_personer()` er uendret, `filtrert_bort()` er utvidet

`tell_personer()` og `persondata.fjern_personformer()` deler
`_personene()`, slik at telleren ikke kan svare noe annet enn filteret.
Docstringen sier nå at 0 betyr «døra tar ingen», ikke «ingen her» (756de47).

Tallet som leses som «hvor mange ble holdt ute»,
`snapshot.filtrert_bort()`, tar hookens entiteter med under etiketten
`(kildens eget tillegg)`, uten formkode, fordi kjernen ikke vet hvilken
form kilden så. Målt: `eierskap` 2026-09-21 ->
{(kildens eget tillegg): 1, ANS: 2, DA: 6}.

`LANSERING.md` punkt 5 sier nå 380 rader / 20 entiteter per lesing, med
de 16 ute av filene (b1abbef).

## Hvorfor

[Heine]

## Hva som ville snudd det

[Heine]
