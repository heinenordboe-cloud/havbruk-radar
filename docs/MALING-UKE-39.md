# Måling: uke 39 mot arkivkroppene

MÅLT 23.09.2026, etter at tellingen ble rettet
(`docs/beslutninger/2026-09-23-en-hendelse-er-ikke-en-rad.md`).

**Spørsmålet:** er det som står igjen reelle endringer i kilden, eller
er noe fortsatt en artefakt?

**Svaret: alle 453 radene er reelle.** Hver eneste er kontrollert mot de
arkiverte API-kroppene fra 14.09 og 21.09 — ikke mot snapshotene, som er
vår egen tolkning av dem. Null avvik.

## Fordelingen

    slag                         rader
    Selskapsopplysning             402
    Ute av vårt utvalg              24
    Felt ikke lenger oppgitt         7
    Tillatelse                       6
    Felt oppgitt første gang         6
    Trafikklys                       4
    Lokalitetsopplysning             4
                                   ---
                                   453   (440 telles, 13 gjør ikke)

    kilde og felt                              rader
    enhetsregisteret  antall_ansatte             369   <- over 20
    enhetsregisteret  change_type (ny/borte/felt) 35   <- over 20
    enhetsregisteret  naeringskode                 8
    enhetsregisteret  siste_innsendte_aarsregnskap 8
    enhetsregisteret  poststed                     6
    akvakultur        prodomraade_status           4   (362 rader)
    enhetsregisteret  ansatte_er_registrert        3
    akvakultur        tillatelser*                 6
    akvakultur        versjon_*                    4
    eierskap          change_type                  2
    enhetsregisteret  kapital/aksjer/mva/vedtekt   8

## Gruppe 1 — `antall_ansatte`, 369 rader: REELL

    stemmer med arkivkroppene   369
    avvik                         0
    entitet mangler i en kropp    0

Eksempler, `antallAnsatte` i Brønnøysunds egen kropp begge datoer:

| orgnr | navn | 14.09 | 21.09 |
|---|---|---:|---:|
| 996482537 | AKVAFUTURE AS | 42 | 43 |
| 979494009 | ALSAKER FJORDBRUK AS | 42 | 44 |
| 932201070 | ANDFJORD SALMON AS | 37 | 38 |

Median endring ±2, største sprang 87. Dette er A-ordningens månedlige
oppdatering: 369 forskjellige fakta som kommer samme dag, ikke ett
vedtak skrevet 369 ganger. De telles.

## Gruppe 2 — `change_type`, 35 entiteter: REELL, og skillet holder

Prøven er den samme som `changelog.merk_feltbevegelse()` stiller, men
mot KROPPENE i stedet for snapshotene:

    slag          entiteter   arkivkroppene sier        stemmer
    borte                22   entiteten gikk            22 av 22
    felt_borte            7   står i begge              7 av 7
    felt_ny               6   står i begge              6 av 6

| slag | orgnr | navn |
|---|---|---|
| borte | 914333849 | AQS HOLDING AS |
| borte | 916025068 | FYLKESNES INVEST AS |
| borte | 919170646 | BJØRØYA HOLDING AS |
| felt_borte | 917437009 | HYDRO SHIPPING AS |
| felt_borte | 921136846 | SØRSMOLT AS |
| felt_ny | 911763680 | EIDESVIK RENSEFISK AS |
| felt_ny | 921567529 | GREEN SEALICE SOLUTIONS AS |

De 22 gikk ut av SØKET vårt, og etiketten sier det. 20 av dem sto
fortsatt i Enhetsregisteret 23.09 med en næringskode utenfor lista vår;
2 var slettet. Målingen står i beslutningsnotatet.

## Resten av `enhetsregisteret`: 402 av 402 stemmer

Hele `endret`-mengden ble kontrollert felt for felt mot kroppene, med
kildens egen `FELTER`-oppskrift for uttrekket — ikke en avskrift.

    antall_ansatte                 369  stemmer
    naeringskode                     8  stemmer
    siste_innsendte_aarsregnskap     8  stemmer
    poststed                         6  stemmer
    ansatte_er_registrert            3  stemmer
    aksjekapital                     2  stemmer
    antall_aksjer                    2  stemmer
    kapital_innfort_dato             2  stemmer
    vedtektsdato                     1  stemmer
    registrert_i_mvaregisteret       1  stemmer

(De fire boolske feltene så først ut som avvik: `True` mot `true`. Det
er prøvens normalisering, ikke dataene.)

## `akvakultur`: 362 av 362 stemmer

`placement.prodAreaStatus` i kroppen, begge datoer:

| loknr | navn | 14.09 | 21.09 | PO |
|---|---|---|---|---:|
| 10086 | REKEVIKI | RØD | GUL | 4 |
| 10087 | KALVØYA N | RØD | GUL | 4 |
| 10091 | VÅGSØYA | RØD | GUL | 4 |

Registeret flyttet fire hele produksjonsområder samme dag. De vises som
fire hendelser med antall lokaliteter, ikke som 362.

## `eierskap`: 2 av 2 stemmer

| tillatelse | 14.09-kroppen | 21.09-kroppen |
|---|---|---|
| SF-B-0048 | står der | borte |
| SF-B-0056 | står der | borte |

Kroppen gikk fra 2 953 til 2 951 tillatelser.

## Konklusjon

Ingenting rettes. Den forrige runden fjernet 372 rader som ikke var
hendelser; det som står igjen er kildens egne endringer, verifisert mot
kildens egne svar.
