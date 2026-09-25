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

## Hvorfor

[Heine]

## Hva som ville snudd det

[Heine]
