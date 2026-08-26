---
dato: 2026-08-26
tittel: En analyse skriver ned valgene sine, og versjonsvalget er ett av dem
status: vedtatt
commit:
---

# En analyse skriver ned valgene sine, og versjonsvalget er ett av dem

**Bestemt:** hver analysekjøring skriver en `*.kjoring.log` ved siden av
resultatet, med alle valg som påvirket tallene — og snapshots leses
gjennom loggen, ikke ved siden av den.

**Skillet:** et analysetall er en egenskap ved dataene OG ved valgene.
Står bare det første nedskrevet, kan ingen si om et nytt tall er et nytt
funn eller et endret valg.

## Hvorfor

`analyse/lusepress_mot_fasit.py` ga `rho = +0,761` for en delvis
Stien-proxy. Tallet er reproduserbart bare hvis man kjenner vinduet (uke
16–24), startåret (2018), målet (`snitt_uvektet`), aggregeringen (snitt
av ukesnitt, uvektet), fasitfilas innhold, `PERSONFORMER`-lista, og
hvilke snapshots som lå på disk den dagen. Ingen av dem sto noe sted.

Det er samme klasse som F9, F10 og F14: en verdi utenfor dataene avgjør
hva de betyr. Regel 1b-3 stiller prøven for et snapshot, og den gjelder
ordrett for et resultat.

## Versjonsvalget er den delen som er ny

Fram til 26.08.2026 var «hvilken fil er datoen 2017-10-31» et spørsmål
med ett svar. Etter arkivinnsettingen har 81 biomassemåneder to:

    2017-10-31.parquet     hentet 25.08.2026, utgitt (ukjent)
    2017-10-31.2.parquet   hentet 26.08.2026, utgitt 20.07.2024

Høyest løpenummer er eldst. En analyse som leser «2017-10-31» leser én
bestemt PÅSTAND om den måneden, og loggen fører derfor løpenummer OG
`published_at` for hver eneste fil — ikke bare datoen.

Målt: `analyse/biomasse_versjonsvalg.py` over de 81 overlappende
månedene gir **248 av 1134 PO-måneder ulikt tall (21,9 %), i hvert
eneste år**, og en total som spriker med 241 233 fisk. Årssummene for
2018 og 2020–2023 er identiske mens medianene flytter seg — det er
speilparene fra 1b-5, lokaliteter omklassifisert mellom PO i ettertid.

## Hvorfor lesingen går GJENNOM loggen

En logg som skrives ved siden av lesingen er en PÅSTAND om den. En logg
som skrives AV lesingen er en BESKRIVELSE av den. To tellere for samme
sak er formen F6, F7 og F8 hadde, og en analyse som leser gjennom
`snapshot.les_mellom()` og separat noterer «leste lusetall 2018–2026»
kan ta feil om seg selv.

`Kjoringslogg.les()` er derfor lesedøra. Den kan ikke føre noe annet enn
det som faktisk ble lest.

Tre ting følger som ikke var planlagt, men falt ut av å ha én dør:

- **`PERSONFORMER` føres uten at analysen ber om det.** Lista virker i
  `snapshot._les()`, altså inne i døra loggen eier.
- **En dato som ble VALGT BORT skilles fra en som ikke fantes.** De fire
  desemberukene i 2017 som faller utenfor ISO-året føres som forkastet
  med grunn. «Uke 52/2017 ble lest» og «uke 52/2017 ble valgt bort» gir
  ulike tall.
- **Én kilde kan ikke leses med to versjonsvalg i samme kjøring.** Da
  ville halve resultatet hvilt på én påstand og halve på en annen, og
  loggen ikke kunne si hvilken halvdel som var hvilken. Det kaster.

## Hva loggen avdekket med en gang

`lusetall` har `utvalg` **ukjent** i alle 448 snapshots, mens
`sjotemperatur` har `{"rapporttype":["Lice"]}`. De to prediktorene i
samme analyse hviler på hver sin dokumenterte utvalgsstatus, og det var
ikke synlig noe sted før loggen skrev det ned. Det er ikke nødvendigvis
galt — de er hentet fra to endepunkter i samme rapport — men det er
nettopp den typen forskjell en analyse ikke skal kunne overse.

## Hva som ville snudd det

- Blir loggen så stor at ingen leser den — 988 linjer for lusepress i
  dag, drøyt 900 av dem én linje per snapshot-fil — skal fillista
  komprimeres, ikke fjernes. Datoen alene er ikke nok så lenge en dato
  kan ha flere versjoner.
- Får `core/` en gang en lesevei som gir løpenummer og ramme sammen
  (`les_mellom()` gjør det ikke i dag), skal `Kjoringslogg.les()` bygge
  på den framfor på `datoer()` + `versjoner()`.
- Slutter en dato å kunne ha flere versjoner — arkivkopiene fjernes,
  eller revisjonene lagres et annet sted — faller begrunnelsen for
  `versjonsvalg`, men ikke for loggen.
