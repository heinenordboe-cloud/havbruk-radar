---
dato: 2026-10-06
tittel: Vesentlig eller teknisk — én regel for hver registerendring, og en koordinatterskel på 100 m
status: utkast
commit: [fylles inn]
---

# Vesentlig eller teknisk

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt

- Hver endring i registerkildene klassifiseres som **vesentlig** eller
  **teknisk** av `vesentlighet.klassifiser()`. Regelen står ett sted og
  brukes av lokalitetssiden og ukesiden. En rapportmotor kan bruke den
  uten nettstedet: modulen kjenner bare changelog-raden.
- Reglene, i den rekkefølgen de prøves:

      ILA/PD           vesentlig når «satt» står på en av sidene
                       teknisk når flagget bare går mellom tomt og ikke satt
      ny / borte       vesentlig
      koordinater      vesentlig fra 100 m, ellers teknisk
      felt kom/gikk    teknisk når det gjentar fisk til stede samme uke
      avledet felt     teknisk når grunnfeltet endret seg i samme par
      tekniske felt    versjon gyldig fra, versjonsårsak, artsbegrensninger
      alt annet        vesentlig

- **Standarden er vesentlig.** Et felt ingen regel nevner, vises øverst.
- Koordinatterskelen er **100 m**, valgt av Heine 06.10.2026. Den står
  som én konstant (`KOORDINAT_TERSKEL_M`) og flytter seg ikke av seg selv.

## Tre punkter der bestillingen er tolket

Bestillingen listet klassene. På tre steder er regelen en tolkning:

1. **ILA/PD.** Bestillingen sa «ILA/PD: vesentlig». Men en rad «— →
   ikke satt» eller «ikke satt → —» betyr at lokaliteten kom inn i eller
   falt ut av BarentsWatch, ikke at et flagg ble satt. På 20797 var alle
   fire endringene på siden av den typen. Slike rader er tekniske. Et
   flagg som settes eller oppheves («True» på en av sidene), er
   vesentlig.
2. **Avledede felt** (`Source.avledet_av`: `antall_arter`,
   `tillatelser_antall`, `lokaliteter_antall`) er tekniske når
   grunnfeltet endret seg i samme par. Ukesiden slår dem allerede inn i
   grunnfeltets rad (2026-09-24-bokforing-og-avledede-felt.md).
   Lokalitetssiden viste dem som egne endringer.
3. **Versjonsårsak** er teknisk som rad, og vises som forklaring på
   endringen samme dag på lokalitetssiden (bestillingens punkt 3).

## Målt 06.10.2026: koordinatendringene

Hele changeloggen, lest gjennom `changelog.les_alt()`. Bare
`akvakultur` har koordinater, og den har sju uker. Det er 30 rader:
12 `endret` (6 flyttinger) og 18 `ny`/`borte` (lokaliteter som kom
eller gikk). Kontrollert mot de 14 snapshotene: de samme 6.

    19,4   22,5   24,2   31,4   |   152,7   190,5   meter

Alle seks har `versjon_aarsak = COORDINATES`. Ingen er avrundingsstøy.
Seks punkter er ikke en fordeling, og terskelen er et valg, ikke en
måling (CLAUDE.md 1b-4). Den bør måles på nytt når loggen er et halvt
år.

## Målt 06.10.2026: klassene over alle ukentlige kilder

Selskapsdata (enhetsregisteret) er holdt utenfor: de står for seg på
ukesiden, og reglene er skrevet for lokaliteter og tillatelser.

    teknisk   artsbegrensninger_antall              135
              antall_arter, følger av har_fisk        77
              arter_tilstede kom/gikk med fisk        77
              tillatelser_antall, følger av            26
              versjon_gyldig_fra                      17
              lokaliteter_antall, følger av           16
              versjon_aarsak                          12
              koordinater under 100 m                  8   (4 flyttinger)

Felt som ble vesentlige fordi INGEN regel nevner dem: kommune og
kommunenummer (akvakultur 3+3, eierskap 2), `eierskap.lokaliteter`
(17: en tillatelse som flyttet mellom lokaliteter) og
`prodomraade_status` (362: trafikklysfargen).

Per uke, ukesidens hovedtabell:

    uke        rader   vesentlige   tekniske
    2026-41       98           75         23
    2026-40       35           21         14
    2026-39       12            8          4
    2026-38      170           94         76
    2026-37       37           25         12
    2026-36       14           13          1
    2026-35      121            2        119

## Målt 06.10.2026: 173 forklaringer, 18 færre rader

Rapporten fra økt 2 sa at 173 rader fikk en registerforklaring, mens
totalen på lokalitetssidene bare falt med 18 (6 316 før, 4 274 + 2 024 =
6 298 etter). Begge tallene er riktige, og de teller hver sin ting.

- **18** er versjonsårsak-radene som forsvant som egne rader: 12 `endret`
  og 6 `ny`. Alle 18 i loggen fikk noe å forklare. Ingen ble stående
  alene.
- **173** er radene som fikk forklaringen. Én årsak forklarer alle de
  andre akvakultur-radene for samme lokalitet samme dag:

      mottakere per årsak   lokaliteter   rader
                       24             6     144   nye lokaliteter (45302–45307)
                        5             2      10   kapasitet og tillatelser
                        3             2       6   koordinater og versjonsdato
                        2             5      10
                        1             3       3
                                     18     173

**144 av de 173 er støy.** En ny lokalitet har 24 felt som «kom», og
hver av dem står med «(registeret: ny lokalitet)». På 45302 står det 24
ganger i tidslinja. Forklaringen er sann, men den hører til lokaliteten
og ikke til hvert felt. Ikke rettet: se rapporten fra økt 3 for
forslaget.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
