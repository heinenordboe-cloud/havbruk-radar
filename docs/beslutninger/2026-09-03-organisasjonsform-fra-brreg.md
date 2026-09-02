---
dato: 2026-09-03
tittel: Organisasjonsform hentes fra Brreg for oppløste selskaper — skjevheten falt fra 26,4 % til 0,6 %
status: gjeldende
commit: e1c89d1
---

## Hva som ble bestemt

Historiske mottakere som ikke finnes i pub-aquas `/entities` får
organisasjonsformen slått opp hos Brreg
(`data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`), og filteret
bruker den.

**Regelen er uendret.** Det filtreres fortsatt på TYPE, aldri på
navnesyntaks. Det som er endret er hvor typen kommer fra når pub-aqua
ikke har den.

## Problemet, målt

Backfillen (`e1c89d1`) fjernet 694 av 2628 overføringer — 26,4 %. Bare
**17** av dem var personer. De øvrige 677 ble stoppet av vilkåret «typen
må være kjent», fordi mottakeren er oppløst og mangler i dagens
entitetsregister.

De 110 distinkte ukjente mottakerne var i praksis konsolideringen selv:

    182x  MOWI NORWAY AS            16x  PAN FISH NORWAY AS
     43x  CERMAQ FINNMARK FARMING   15x  AQUA FARMS AS
     25x  SALMAR FINNMARK AS        12x  MARINE HARVEST LABRUS AS

Filteret rammet altså fortrinnsvis de OPPKJØPTE selskapene — nøyaktig de
hendelsene serien finnes for å dokumentere. **Serien kunne ikke
publiseres i den formen.**

## API-et, målt før noe ble bygget

Fem kjente oppløste selskaper ble slått opp og full respons dumpet.

| | |
|---|---|
| statuskode | **200 OK** for alle fem |
| `respons_klasse` | `"SlettetEnhet"` |
| `organisasjonsform.kode` | **finnes** — `AS` for alle fem |
| `slettedato` | satt: 2006-12-04 … 2026-05-06 |
| øvrige felter | `navn`, `historiskeNavn`, `_links` |

**Det avgjørende spørsmålet — overlever `organisasjonsform` på en slettet
enhet — er ja.** Veien er farbar.

Til sammenligning, en AKTIV enhet svarer med langt mer:
`forretningsadresse`, `postadresse`, `epostadresse`, `telefon`, `mobil`,
`naeringskode1`, `konkurs`, `institusjonellSektorkode` og mer. Et ENK
(`985937028`) svarer med gateadresse og personens mobilnummer.

Statuskodene som ble observert: **200** (aktiv og slettet), **404**
(ukjent nummer). **410 Gone** er dokumentert for juridisk fjernede
enheter, men forekom ikke i vårt utvalg.

## Personvern: kroppen reduseres før arkivering

`brreg_form()` returnerer **tre felter** —
`organisasjonsnummer`, `organisasjonsform`, `slettedato` — og status.
Navnet er ikke blant dem: `officialName` fra overføringen dekker behovet,
og et navn fra Brreg ville vært en personopplysning for hver personform.

Rå-arkivet ligger i git og er append-only. Samme avveining og samme
løsning som `/entities` i forrige økt: filtrer i `fetch()`, arkivér det
filtrerte.

### Personformene arkiveres ikke i det hele tatt

Et arkiv som sier «dette organisasjonsnummeret tilhører et
enkeltpersonforetak» er en opplysning om et navngitt menneske.

De utelates derfor helt, og det koster ingenting i oppførsel: en
mottaker som mangler i typekartet er UKJENT, og ukjent stoppes — samme
utfall som personform. De to tilstandene er ikke til å skille fra
hverandre nedstrøms, med vilje. Prisen er at de slås opp på nytt ved en
gjenkjøring, og det er en håndfull kall.

### Filteret måtte lære et andre vokabular

pub-aqua sier `SoleProprietorship`, Brreg sier `ENK`. Uten at
`er_person()` kjente begge, ville en Brreg-`ENK` sluppet rett gjennom —
og rettelsen ville brutt regelen den skulle bevare.

`er_person()` spør nå `core/persondata.er_personform()` for Brreg-siden.
Lista kopieres ikke inn i kilden: to lister som skal si det samme er
formen F6, F7 og F8 hadde.

## Resultatet

    typekart               485  ->  595
    beholdt      1934 (73,6 %)  ->  2611 (99,4 %)
    fjernet               694   ->    17
    unike mottakere       225   ->   335
    ukjent type           677   ->     0

Alle 110 ble slått opp: **110 `ok`, 0 personform, 0 ikke funnet, 0
fjernet.** Hver eneste ukjente mottaker var et selskap.

De 17 som fortsatt stoppes er alle personer uten organisasjonsnummer —
Fiskeridirektoratet holder tilbake nummeret for fysiske personer, men
publiserer navnet.

### Filtreringsrate per år — der skjevheten faktisk vises

| år | totalt | rate FØR | rate ETTER |
|---|---|---|---|
| 2006 | 84 | **82,1 %** | 1,2 % |
| 2007 | 245 | **76,3 %** | 0,0 % |
| 2008 | 111 | 55,0 % | 0,9 % |
| 2009 | 50 | 48,0 % | 2,0 % |
| 2010 | 31 | 51,6 % | 3,2 % |
| 2011 | 31 | 41,9 % | 0,0 % |
| 2012 | 42 | **76,2 %** | 4,8 % |
| 2013 | 87 | 25,3 % | 1,1 % |
| 2014 | 80 | **82,5 %** | 2,5 % |
| 2015 | 75 | 24,0 % | **6,7 %** |
| 2016 | 44 | 25,0 % | 0,0 % |
| 2017 | 20 | 5,0 % | 0,0 % |
| 2018 | 73 | 32,9 % | 2,7 % |
| 2019 | 328 | 6,1 % | 0,0 % |
| 2020 | 67 | 20,9 % | 0,0 % |
| 2021 | 39 | 5,1 % | 0,0 % |
| 2022 | 728 | 8,0 % | 0,0 % |
| 2023 | 121 | 8,3 % | 0,0 % |
| 2024 | 135 | 22,2 % | 0,7 % |
| 2025 | 146 | 10,3 % | 0,0 % |
| 2026 | 91 | 1,1 % | 0,0 % |

Før: de tidlige årene tapte halvparten til fire femtedeler av
overføringene sine. Etter: ingen år over 6,7 %, og de fleste 0.

**En restskjevhet står igjen, og den skal oppgis.** 14 av de 17
gjenværende ligger før 2016. Private personer eide oftere tillatelser i
de tidlige årene, og de kan ikke lagres. Restskjevheten er under én
prosent samlet, men den er ikke null og den er ikke tilfeldig fordelt.

## Hvorfor navnesyntaks fortsatt ikke er et alternativ

106 av de 110 ukjente mottakerne hadde selskapsendelse i navnet. Det
hadde vært fristende å bruke.

Men «navnet slutter på AS» er en SYNTAKTISK prøve på et SEMANTISK
spørsmål, og `core/persondata.py` advarer ordrett mot den: «å filtrere PÅ
NAVNET er nøyaktig samme feil som ni-siffer-testen fra 16.08». Et ENK kan
hete «LYNGSSKJELLAN V/ARNE SAMUELSEN» og et AS kan hete «Ola Nordmann
AS». Navnet er ikke formen.

Målingen bekrefter at snarveien ville gitt riktig svar her — og det er
nettopp derfor den er farlig. En prøve som er riktig i de tilfellene man
tester den på, og feil i de man ikke tenkte på, er den stille feilformen
hele dette repoet er bygget rundt.

## Serien måler JOURNALFØRINGER, ikke oppkjøp

Dette står her uavhengig av Brreg-rettelsen, og det skal med hver gang
tallene brukes.

2019 (328) og 2022 (728) utgjør **40 % av alle overføringer**. Begge er
kjente omstruktureringer, ikke oppkjøpsbølger:

- **2019:** Marine Harvest → Mowi. Brreg-oppslaget viser det direkte:
  `959352887` het `MARINE HARVEST NORWAY AS` fram til 2019-01-21, ble
  `MOWI NORWAY AS`, og ble slettet 2019-12-16. Et navnebytte og en
  fusjon inn i morselskapet.
- **2022:** en konsernintern omorganisering.

En flytting av tillatelser mellom selskaper i samme konsern
journalføres som en overføring, men **ingen kjøpte noe**.

**Serien er «journalførte overføringer av tillatelser», ikke
«eierskifter».** En graf som viser en topp i 2022 og lar leseren tro det
var et oppkjøpsår, er misvisende på en måte som er vanskelig å oppdage
utenfra. Navnet på enhver visning skal si journalførte overføringer.

## Konsernstruktur — veien finnes, men den rekker ikke bakover

Undersøkt, ikke bygget.

Endepunktet er `data.brreg.no/enhetsregisteret/api/konsernstruktur/{orgnr}`
— **ikke** under `/enheter/`, som var derfor det første forsøket ga 404.
Det kom til 24. juni 2026 og finnes i JSON og CSV.

Kallet på `929706331` (FRØY HAVBRUK AS) gir øverste mor
(`GÅSØ NÆRINGSUTVIKLING AS`) og et helt tre av døtre, hver med `nivaa`,
`knytningsform` (`KDAT` «Konsern datter», `KMOR`, «Øverste mor»),
`grunnlag` (eierandel, «100 %») og `dato`.

To grenser gjør at den ikke løser problemet i dag:

1. **Den 404-er for slettede enheter.** MOWI NORWAY AS, MOWI SEAWATER
   NORWAY AS og GRIEG SEAFOOD ROGALAND SJØ AS gir alle 404. Det er
   nøyaktig de oppløste selskapene som er interessante for en historisk
   analyse.
2. **`dato` er dagens.** Treet som returneres er konsernstrukturen NÅ
   (2026-02-19 i eksempelet), ikke slik den var da overføringen ble
   journalført. Å avgjøre om en overføring i 2012 var konsernintern
   krever strukturen i 2012.

Å bruke den ville derfor kreve enten en egen tidsserie av
konsernstrukturer bygget framover fra i dag, eller en kilde til
historiske konsernforhold. Begge deler er en egen beslutning.

## Hvordan de reviderte snapshotene ble skrevet

`backfill.py --kilde eierskap --overforinger --reparse`. De 21
årssnapshotene fikk hver sin `.2.parquet` ved siden av den gamle, og
**ingen changelog-rader**.

Det siste er ikke en formalitet: kroppene er byte for byte de samme, og
det som er endret er VÅRT filter. En «ny»-rad ville påstått at det kom en
overføring til, når sannheten er at vi endelig klarte å lese den vi
allerede hadde. Samme regel og samme begrunnelse som ekspertgruppens
`--reparse`.

## Hva som ville snudd det

- **Brreg slutter å oppgi organisasjonsform for slettede enheter.** Da
  faller de 677 tilbake til ukjent, og serien er publiserbar bare med
  skjevheten oppgitt i hver visning.
- **pub-aqua begynner å beholde oppløste enheter i `/entities`.** Da er
  Brreg-oppslaget overflødig.
- **En kilde til historiske konsernforhold.** Da kan konserninterne
  overføringer skilles fra ekte eierskifter, og «journalførte
  overføringer» kan endelig deles i to serier som betyr noe hver for seg.
