---
dato: 2026-10-06
tittel: Koordinatterskelen er 100 m — bygget på seks målinger, vurderes på nytt ved årsskiftet
status: besluttet 06.10.2026, vurderes på nytt ved årsskiftet 2026/2027
commit: 006acf8
---

# Koordinatterskelen er 100 m

## Bestemt

- En flytting av en lokalitet på **100 m eller mer** er en vesentlig
  endring. Under 100 m er den teknisk. Grensa er inkluderende: 100 m er
  vesentlig.
- Terskelen står som én konstant, `vesentlighet.KOORDINAT_TERSKEL_M`.
  Teksten på lokalitetssiden og ukesiden leser den derfra.
- **Den flytter seg ikke av seg selv** (CLAUDE.md 1b-4). Den endres bare
  ved en ny måling og en ny beslutning.
- Valgt av Heine 06.10.2026, blant 50, 100 og 150 m.

## Grunnlaget: seks målinger

Hele changeloggen per 06.10.2026, lest gjennom `changelog.les_alt()`.
Bare `akvakultur` har koordinater, og den har sju uker (fra 17.08.2026).
Kontrollert mot de 14 snapshotene: de samme seks, ingen andre.

| Observert | Lokalitet | Avstand |
|---|---|---:|
| 2026-09-28 | 33097 Skjervøy V | 19,4 m |
| 2026-10-05 | 45029 Ramnøya N | 22,5 m |
| 2026-10-05 | 45140 Nordskaftet | 24,2 m |
| 2026-09-28 | 10974 Store Bukkøy N | 31,4 m |
| 2026-08-24 | 17177 Grunneneset | 152,7 m |
| 2026-10-05 | 12237 Brudevika | 190,5 m |

Ingenting mellom 32 og 152 m. Alle seks har `versjon_aarsak =
COORDINATES` hos registeret. Avstanden er haversine med jordradius
6 371 008,8 m.

**Seks punkter er ikke en fordeling.** Terskelen er et valg, ikke en
måling. Den ligger i det tomme feltet, og alle verdier fra 32 til 152 m
ville gitt samme deling i dag (4 tekniske, 2 vesentlige). Det er
framtidige flyttinger i det intervallet som avgjør om valget var godt.

## Vurderes på nytt ved årsskiftet

Ved årsskiftet 2026/2027 har loggen rundt 20 uker. Da skal målingen
kjøres på nytt, med samme metode:

1. Alle `endret`-rader for `akvakultur.breddegrad`/`lengdegrad`, parret
   per (lokalitet, dato), avstand i meter.
2. Kontroll mot snapshotene.
3. Fordelingen rapporteres, sammen med hvor mange som havner på hver
   side av dagens terskel, og hvor mange som ligger mellom 32 og 152 m.

Spørsmålet er om det tomme feltet fortsatt er tomt. Er det ikke, skal
terskelen vurderes mot det som faktisk ligger der, og ikke mot de seks
fra i dag.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

Ny måling ved årsskiftet (over). Utover det: [Heine skriver.]
