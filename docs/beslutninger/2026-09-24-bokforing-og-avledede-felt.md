---
dato: 2026-09-24
tittel: Bokføring og avledede felt teller ikke som bevegelse
status: utkast
commit: eaaf918
---

# Bokføring og avledede felt teller ikke som bevegelse

**UTKAST.** «Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt

Anvendelse av `2026-09-23-en-hendelse-er-ikke-en-rad`, ikke ny regel.
En kilde deklarerer to slags felt, og kjernen leser deklarasjonen uten
å kjenne kildenavnet (regel 1):

- **bokføring** — felt som sier noe om rapporteringen, ikke om
  entiteten. Lagres i changeloggen som før, teller ikke i ukas tall og
  vises ikke på entitetens tidslinje. Første: `biomasselag.siste_rapport`.
- **avledet av** — felt som endrer seg fordi et annet felt endret seg.
  Når begge endres i samme par av øyeblikksbilder, er det én hendelse.
  Første: `biomasselag.antall_arter`, avledet av `har_fisk`.

## Målingen som utløste det

Uke 38, «Fisk til stede» 513, én kilde, paret 2026-09-10 → 2026-09-15
(målt 24.09.2026):

    siste_rapport   383   321 av dem uten har_fisk-endring
    har_fisk         65   42 Nei→Ja, 23 Ja→Nei
    antall_arter     65   66 av 66 overlapp med har_fisk

Begge kroppene reparset med dagens kode: 0 avvik mot snapshotene.
Feltene betyr det samme som da de ble skrevet. Feilen var i tellingen,
ikke i dataene.

Etter endringen, målt per uke:

    uke        antall før   antall etter
    2026-39            38             38
    2026-38           560            112
    2026-37            50             50
    2026-36            28             28
    2026-35           123            123
    SUM               799            351

## Følger

Uke 38 går fra 560 til 112. Totalen på /endringer/ går fra 799 til 351.
Feeden har allerede levert rader for `siste_rapport`. De forsvinner fra
sidene, men ikke fra lesere som har hentet dem.

## Utvidet 25.09: to felt til, og ett som ble målt og ikke erklært

De to kandidatene 24.09-målingen fant, er nå erklært av kildene sine:

    akvakultur.tillatelser_antall   avledet av tillatelser
    eierskap.lokaliteter_antall     avledet av lokaliteter

MÅLT 25.09.2026 over hele changeloggen (1 015 754 rader). Målingen fra
24.09 ble gjentatt, og den holder i BEGGE retninger — som er leddet
24.09 ikke stilte:

    felt                            rader   med grunnfeltet   grunnfeltet uten
    akvakultur.tillatelser_antall      24         24/24               0/24
    eierskap.lokaliteter_antall        21         21/21               0/21

Tallet har aldri flyttet seg uten lista, og lista aldri uten tallet.
Nøkkelen er (entitet, par), altså `forrige_observed_at -> observed_at`,
og ikke datoen alene.

Ukas tall, målt gjennom `les_endringsuker()` med og uten de to
erklæringene. De to kolonneparene er de to tallene siden faktisk viser:
`antall` er setningen på ukesiden («17 endringer observert i uke 36,
2026»), tabellrader er `meta description` og lengden på tabellen.
Bygget og lest i HTML-en, ikke bare i ramma:

    uke        antall før   antall etter   tabellrader før   etter
    2026-39            16             14               453     451
    2026-38           109            105               220     216
    2026-37            48             41                90      83
    2026-36            26             17                70      61
    2026-35           121            121               186     186
    SUM               320            298              1019     997

22 rader forsvinner, og alle 22 er tellingen. Ingen ny hendelse kommer
til, og selskapsdelen står urørt (630 begge veier). Uke 35 flytter seg
ikke: den uka er akvakultur-bevegelsen artsbegrensninger, som ikke har
noe grunnfelt — se under.

### `tillatelser_trukket` samvarierer 13/13 og er IKKE erklært

Dette er målingen prompten ba om først, og den snudde ikke svaret —
den gjorde begrunnelsen skarpere.

    tillatelser_trukket    13 rader    13/13 i samme par som tillatelser
                                       13/13 i samme par som tillatelser_antall
                                        0/13 alene

100 %, altså sterkere samvariasjon enn de 66/66 som fikk `antall_arter`
erklært 24.09. Og likevel nei, fordi **spørsmålet ikke er om feltet
BEVEGER seg sammen med grunnfeltet, men om det SIER noe grunnfeltet ikke
sier.**

At T-T-0035 forsvant fra lokalitet 10560 31.08.2026 står i
`tillatelser`. At den forsvant fordi den ble TRUKKET, og ikke flyttet
til en annen lokalitet, står bare i `tillatelser_trukket` — registeret
flytter oppføringen fra `connections` til `obsoleteConnections`, og
ingen av de to andre feltene bærer den statusen. Lokalitet 12235
07.09.2026 er formen i klartekst: `tillatelser` mistet M-VN-0024, -0025
og -0026 og fikk -0027 og -0028, og bare `tillatelser_trukket` svarer
hvilke tre av de fem som ble trukket.

Et tall som kan regnes ut av grunnfeltet er en FØLGE. Et ord om hvorfor
grunnfeltet flyttet seg er en OPPLYSNING. Samme skille som holdt
`enhetsregisteret.antall_ansatte` tellende 24.09, bare fra andre siden:
der var samvariasjonen 46 %, her er den 100 %, og prosenten avgjorde
ingen av dem. En terskel på prosent ville tatt feil i begge tilfellene.

Følgen er at et trukket tillatelsesledd fortsatt gir TO hendelser der
det skjedde én ting: `tillatelser` og `tillatelser_trukket`. Det er ikke
løst her, og det er ikke det samme problemet — de to radene sier hver
sin halvdel av hendelsen, og en sammenslåing måtte vist BEGGE. Åpent.

### `artsbegrensninger_antall` kan ikke erklæres, og 118-endringen var ingen omkoding

24.09-notatet sa at listen bak tallet ikke lagres, og at 118 endringer
derfor ikke har noe å slås sammen med. Begge ledd er nå målt i de
arkiverte kroppene, og hele målingen står i
docs/KILDE-AKVAKULTUR.md punkt 4.5 og 6. Kort:

* **Formen er uendret gjennom alle 13 kropper.** Liste, alltid til
  stede, hvert element et objekt med seks nøkler som alltid er satt
  (`code`, `faoAlpha3Code`, `latinName`, `nbNoName`, `nnNoName`,
  `enGbName`). En re-parse kan altså hente både artskode og navn.
* **Trinnet 24.08 var ikke en omkoding.** `speciesTypes` tok ikke over
  (0 av 118 endret settet; 6 endret rekkefølgen og ikke noe mer),
  `connections` bærer ingen art, og 112 av 118 hadde
  `speciesLimitations` som sitt ENESTE endrede felt. 76 lokaliteter
  mistet alt, 42 fikk sine første, og per 21.09 har 0 av de 76 fått det
  samme igjen. Ett trinn, én retning, fem uker.
* **Tallet er derfor eneste spor.** Å erklære det avledet ville skjult
  den eneste raden som finnes om artsbegrensninger. Det gjøres ikke.

Rettet samme sted: punkt 6 sa at `tillatelser_trukket` er «et antall».
Den er lisensnumrene, en semikolonliste som `tillatelser`. `FELTER`
bruker `_lisensnumre`, ikke `_antall`.

### Vakten som fulgte

`avledet_av` navngir felt som strenger, og en omdøping ville stoppet
sammenslåingen uten å feile — i den retningen som bare gir FLERE
hendelser, altså den støyende. Begge kildene har nå en prøve på at de
erklærte navnene er felt `parse()` faktisk skriver, lest av radene og
ikke av `FELTER`. Prøvd ved å brekke erklæringen: begge prøvene faller.

## Hvorfor

[Heine]

## Hva som ville snudd det

[Heine]
