---
dato: 2026-08-25
tittel: Feltvakten måler levering, ikke innhold
status: utkast
commit:
---

# Feltvakten måler levering, ikke innhold

> **UTKAST.** Skrevet ut fra målingene under. «Prisen» og «Ville snudd
> det» er skisser og skal skrives om for hånd.

**Bestemt:** en innholdsvakt ved siden av feltvakten. Målet er
`minoritet` — rader som ikke har feltets vanligste verdi. Normalen
bygges fra HELE historikken med `--bygg-feltnormal` og lagres
append-only i `data/feltnormal/<dato>.json`, aldri av den ukentlige
kjøringen.

**Skillet:** «kom feltet» er ikke «sa feltet noe». For et felt som
varierer er de to like. For et felt som fryser er de aldri like.

## Tallene

To felter i lusetall er døde, og begge leverer fulle kolonner:

| felt | siste innhold | tomt siden | nivå før |
|---|---|---:|---:|
| `har_rensefisk` | 2023-04-17 | **171 uker** | 46,5 lok./uke |
| `har_medikamentell_behandling` | 2024-01-01 (blip 2024-11-11) | **89 uker** | 44,6 lok./uke |

Begge leverte 1777 rader hver eneste uke gjennom hele perioden.
`felt_referanse` i health.json sto på 1777 for begge. Vakten så to fulle
kolonner og tidde i tre år.

Referansen ble dessuten satt sommeren 2026, da begge for lengst var
døde. Den festet dødsleiet som normaltilstand — en referanse som
oppdaterer seg selv, målt mot seg selv.

## Målet: minoritet, ikke «antall True»

Ett tall for alle datatyper: **hvor mange rader har IKKE feltets
vanligste verdi denne uka.**

    har_rensefisk    1777 rader, alle False    -> 0
    har_laksefisk    1360 True, 417 False      -> 417
    voksne_hunnlus   571 rader, 193 verdier    -> 479
    kapasitet_enhet  1346 TN, 433 andre        -> 433

Oppdraget sa «for boolske felter, følg antall True». Det er nesten
riktig, og det bommer på én sak: **et boolsk felt kan dø i begge
retninger.** `har_laksefisk` er True for 1360 av 1777. Skulle det fryse
til bare True, ville «antall True» STEGET fra 1360 til 1777 — en vakt
som teller sanne verdier ville sett vekst i det øyeblikket feltet
sluttet å skille noe fra noe. Minoriteten faller uansett hvilken verdi
feltet fryser til.

`sanne` (boolsk), `ikke_null`, `median` og `p95` (numerisk) lagres
likevel per felt. De er det et menneske leser når alarmen går — «minoritet
falt fra 46 til 0» sier ikke hva slags felt det var. De styrer den ikke.

## Terskelen er målt, ikke gjettet

760 uker ga grunnlaget. **Et prosentfall duger ikke.** De små feltene
faller legitimt 70–90 % fra uke til uke:

    felt                          verste ukesfall   nulluker   lengste nullstrekk
    har_ila                                  0,17         22                   22
    har_mekanisk_fjerning                    0,14         24                    7
    har_pd                                   0,80         33                   33
    har_rensefisk                            0,08        178                  171
    har_medikamentell_behandling             0,29        134                   89
    lus_er_rapportert                        0,78          0                    0
    voksne_hunnlus                           0,63          0                    0
    brakklagt                                0,95          0                    0

Null er en helt normal uke for et lite felt. Det er STREKKET som skiller
en stille uke fra et dødt felt. Simulert over alle 761 uker:

    N= 8 uker  ->  5 alarmer
    N=13 uker  ->  5 alarmer   <- valgt
    N=26 uker  ->  4 alarmer

Med N=13: null alarmer i 2014–2022, og de fem som fyrer er `har_pd`
(2012, før BarentsWatch rapporterte det), `har_ila` (2012–13, samme),
`har_rensefisk` (2023) og `har_medikamentell_behandling` (to ganger,
2024 og 2025, fordi den ene True-verdien 2024-11-11 nullstiller
strekket). Ingen falske.

### Grensa er flat, og det er et valg

`normalt_nullstrekk` lagres per felt, men brukes IKKE som unntak. Hvert
eneste nullstrekk over 13 uker i 761 uker historikk er enten en oppstart
eller et dødsfall — ingen er «normalt».

Verre: `har_medikamentell_behandling` har et 45-ukers strekk i
historikken, og det strekket ER dødsfallet. Et unntak utledet av feltets
egen historikk ville gjort vakten blind for nettopp den feilen den
finnes for. Første versjon hadde det unntaket; den ble oppdaget ved å
kjøre byggingen mot ekte data og se at tallet 45 kom fra 2024.

## To prøver, som fanger hver sin ting

**Gulvet** er et LAVVANNSMERKE — speilbildet av `volum_referanse`, som
er et høyvannsmerke. Det settes til det laveste feltet har vært i hele
historikken, og heves aldri av seg selv. Da er antall historiske falske
alarmer null per konstruksjon, og en ny alarm betyr bokstavelig «lavere
enn dette feltet noen gang har vært».

**Nullstrekket** fanger det gulvet ikke kan: et felt som allerede har
vært tomt en gang har `gulv = 0`, og kan aldri falle under det.

At begge trengs er ikke en antakelse. I replayen under fanget gulvet det
ene feltet og strekket det andre.

## Verifisert: ville vakten fanget det DA det skjedde?

Normal bygget av 574 uker (2012-01-02 .. 2022-12-26) — før begge
dødsfallene. Deretter 187 uker 2023–2026 spilt av, uke for uke:

    293 alarmer over 187 uker, fordelt på nøyaktig TO felter:

    har_rensefisk                 første alarm 2023-07-17
      «tomt 13 kjøringer på rad, grense 13; 1735 rader leveres
       fortsatt, alle «False»»
      -> 13 uker etter siste True (2023-04-17). Strekkprøven.

    har_medikamentell_behandling  første alarm 2024-01-01
      «innhold 0 under gulvet 1 — laveste på 574 uker; 1745 rader
       leveres fortsatt»
      -> samme uke som feltet døde. Gulvprøven.

De ni andre feltene ga null alarmer på 187 uker. 293 er de to som fyrer
hver uke etterpå — samme oppførsel som volumvakten, og med vilje: en
alarm som tier etter første uke er den feilmodusen `health.py` finnes
for å hindre.

Mot dagens produksjonsdata, med normalen bygget av alle 761 uker:

    KREVER TILSYN (2):
      lusetall.har_medikamentell_behandling (tomt 90 kjøringer på rad,
        grense 13; 1777 rader leveres fortsatt, alle «False»)
      lusetall.har_rensefisk (tomt 172 kjøringer på rad, grense 13;
        1777 rader leveres fortsatt, alle «False»)

Strekket arves fra normalens `dodt_naa`. Uten det ville et felt som har
vært tomt i 171 uker begynt på null den dagen vakten ble tatt i bruk, og
trengt 13 nye uker på å si fra om noe som har vart i tre år.

## Andre felter med samme mønster

Bygget for alle tre kilder:

| kilde | felt | funn |
|---|---|---|
| lusetall | `har_rensefisk` | tomt 171 av 761 uker |
| lusetall | `har_medikamentell_behandling` | tomt 89 av 761 uker |
| akvakultur | `versjon_status` | `APPROVED` for alle 1779, alle 8 snapshots |
| enhetsregisteret | `kapital_valuta` | `NOK` for alle 1673, alle 8 snapshots |
| enhetsregisteret | `paategninger_antall` | median minoritet 1 av 1810 |
| enhetsregisteret | `under_tvangsavvikling` | median minoritet 3 av 1810 |

De fire siste er **ikke** dødsfall — de er felter som aldri har hatt
innhold i den korte historikken vi har. Akvakultur har 8 snapshots,
enhetsregisteret 9, begge fra samme uke. Vakten teller strekket deres
(9 kjøringer) men fyrer ikke før 13, og det er riktig: vi kan ikke
påstå at et felt er dødt når vi bare har sett det i én uke.

Det er den samme mangelen som resten av kartleggingen viste — for
registrene finnes det ingen historikk å bygge en normal av ennå.
`--bygg-feltnormal` bør kjøres på nytt når de har et års drift.

## Normalen lagres append-only

health.json overskrives i sin helhet hver kjøring. Den er riktig sted
for tilstand som endrer seg ukentlig — `sist_ok`, `feil_paa_rad`,
strekkene. Den er feil sted for en normal utledet av 760 uker historikk:

1. **En fil som skrives om kan ikke svare på «hva var normalen i uke X».**
   Svaret finnes da bare i git-loggen til datarepoet, og en analyse
   leser ikke git. Samme mangel som utvalgsutvidelsen — CLAUDE.md 1b-3.
2. **Normalen skal ikke kunne endres av en ukentlig kjøring i det hele
   tatt.** Det var nettopp en automatisk oppdatert referanse som festet
   dødsleiet til `har_rensefisk`.

Kostnaden er null i praksis. health.json er 5213 bytes og er rørt av
fem commits; en normalfil er av samme størrelsesorden og skrives bare
når noen bevisst bygger eller kvitterer. Argumentet fra
`core/changelog.py` om kvadratisk repovekst gjelder ikke her — det
handler om filer som skrives om HVER uke.

Kollisjon på samme dato løses med løpenummer, som snapshots. Det avdekket
en feil ved skriving av testen: alfabetisk sortering setter
`2026-08-25.2.json` FØR `2026-08-25.json`, fordi `'2' < 'j'`. `les()`
ville servert en normal som var kvittert ut. Samme felle som
`snapshot._dato_og_versjon()` finnes for, og den ble gjort på nytt i en
ny modul.

`--godta-felt` nullstiller strekket, men rører ALDRI gulvet. Gulvet
flyttes bare ved å bygge normalen på nytt, med en begrunnelse som blir
stående i fila.

## Prisen

*(skisse — skrives om)*

- **En ny fil å huske å bygge.** Vakten er stille til `--bygg-feltnormal`
  er kjørt, og den stillheten ser ut som helse. Det er valgt over
  alternativet — å alarmere på et grunnlag vi ikke har — men det er en
  reell kostnad, og det er ingenting i kjøringen som minner om det.
- **`minoritet` er grovt.** Et felt der 3 av 1777 rader avviker teller
  som «har innhold». `paategninger_antall` og `under_tvangsavvikling`
  ligger der i dag.
- **13 uker er kalibrert på lusetall alene.** Det er den eneste kilden
  med historikk. For en daglig kilde ville 13 kjøringer vært to uker,
  og tallet må da revideres per kilde (`kilder.<navn>.maks_nullstrekk`).
- **Alarmen kan ikke skille «kilden sluttet å levere» fra «verden
  sluttet å ha dette».** Den sier at feltet er tomt, ikke hvorfor. Det
  er et spørsmål til kilden.

## Ville snudd det

*(skisse — skrives om)*

- At `minoritet` viser seg for grov, altså at et felt degraderer uten å
  fryse helt. Da er svaret en fordelingsprøve, ikke en lavere terskel.
- At 13 uker gir falske alarmer på en kilde som ikke er lusetall. Da er
  det per-kilde-tallet som skal settes, ikke standarden.
- At normalen viser seg å måtte bygges ofte. Da er append-only feil form
  og den hører hjemme i health.json likevel — men da er også spørsmålet
  hvorfor normalen ikke er stabil.

## Mønsteret

Sjuende gang, og det er samme setning hver gang: **en mekanisme som
måler noe som ligner det den skal måle.**

    F4   filnavnsdato   der den skulle målt innsamlingstidspunkt
    F8   sist_forsok    der den skulle målt sist_ok
    F9   «ny for oss»   der den skulle målt «ny i verden»
    F10  antall rader   der den skulle målt innhold

Alle fire er riktige i akkurat de tilfellene der de to tingene faller
sammen: kilden uten etterslep, kjøringen som lykkes, uka utvalget står
stille, feltet som varierer. Alle fire er stille når de tar feil.

Det nye i F10 er hvor referansen kom fra. F9 handlet om en tilstand som
ikke var lagret; her var den lagret, men **utledet av data som allerede
inneholdt feilen.** En referanse satt sommeren 2026 kunne ikke se at to
felter hadde vært døde siden 2023 — den målte dagens null mot gårsdagens
null og fant dem like. Regelen som følger står i CLAUDE.md 1b-4: en
referanse skal bygges av historikk som er verifisert frisk, og den skal
ikke kunne flytte seg av seg selv.
