---
dato: 2026-10-05
tittel: Et navn som ender på en personform vises ikke — heller ikke som tildelt
status: utkast
commit: d934c10, 2c880f7, 9fe7f56, 18779ff
---

# Personformnavn vises ikke

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt

- Et `tildelt_navn` eller `mottaker_navn` som ender på en personform
  byttes i generatoren mot `«<kode> (navn ikke vist)»`, merket
  `data-felt="navn_skjult"`. Regelen er
  `publiseringsvakt.personform_i_navn()`: endelsen lest av
  `FORM_SUFFIKS`, avgjort av `persondata.er_personform()`. Ingen liste
  navn.
- Orgnummeret ved siden av fjernes, og cellen holdes utenfor
  søkeindeksen.
- Porten maskerer NØYAKTIG den teksten i en celle med den merkingen.
  Står noe annet i en `navn_skjult`-celle, er det et `ukjent_navn`.
- De tre kvitteringene fra 2026-09-19 er trukket i datarepoet
  (`data/kvitteringer/2026-10-05.json`, 9dd439e).
- Formen leses av endelsen fordi den er den eneste formen dataene har
  for en tildelt: MÅLT 05.10.2026 står 0 av de 3 tildelt_orgnr i
  enhetsregisteret-snapshotet, rått eller gjennom døra, og
  `eierskap.organisasjonsform` er formen til den som eier tillatelsen
  NÅ (AS for alle tre).

## Målt 05.10.2026, lokalt bygg mot havbruk-radar-data

    før d934c10    14 personform-funn, alle kvittert, 14 lokalitetssider
                   3 ulike verdier, alle ANS, alle i `tildelt_navn`
                   de 3 tildelt_orgnr på 12 + 1 + 1 sider
    etter 2c880f7   0 personform-funn, 0 kvitteringer aktive
                   de 3 tildelt_orgnr på 0 sider
                   14 forekomster av «ANS (navn ikke vist)»
                   bygget skiller seg fra «før» i nøyaktig de 14
                   lokalitetssidene, ingen andre filer

d934c10 alene ga i tillegg 28 selskapssider med feil navn i tittelen:
«Gikk ut»-løkka i `bygg_selskap()` overskrev variabelen `navn`. Rettet
i 2c880f7. Rapporten til pakke 11 kalte dette ikke-determinisme; det
var det ikke.

## Hva som ikke er dekket

- **ENK.** Et enkeltpersonforetak bærer ingen endelse, og
  `FORM_SUFFIKS` har ikke koden. MÅLT 05.10.2026: 12 `tildelt_navn` på
  formen «ETTERNAVN, FORNAVN» uten orgnr, og 2 personnavn med orgnr,
  står i bygget og fanges ikke av regelen.
- **`eier_navn`.** Uendret: den har `eier_type` og `organisasjonsform`,
  og `_eierrad()` spør dem.

## Bestemt senere samme dag: regelen er SNUDD

Regelen over skjulte et navn når den GJENKJENTE det som personlig. Et
navn den ikke kjente igjen som noe, ble vist. MÅLT 05.10.2026 med curl
mot produksjon: 12 personnavn på formen «ETTERNAVN, FORNAVN» og 2
personnavn med orgnr sto på 15 lokalitetssider, ett treff per side, og
søkeindeksen i det lokale bygget bar dem også.

- Et `tildelt_navn` eller `mottaker_navn` vises nå BARE når
  `publiseringsvakt.vises_som_organisasjon()` sier ja:
  - en ikke-personlig formkode som eget ord hvor som helst i navnet
    (`ORGORD`: kodene i `FORMKODER` minus `PERSONFORMER`, pluss «A/S»,
    «A.S», «A.S.»), eller
  - et orgnr som `formkart()` gir en ikke-personlig form (enhetsregisteret
    `organisasjonsform`, eierskap `organisasjonsform`/`eier_type`,
    eierskap_historikk `mottaker_type`),
  - og aldri når noe sier personlig: en personform på orgnummeret
    (`sources.eierskap.er_person()`), en personformkode i navnet, eller
    formen «ETTERNAVN, FORNAVN» (`PERSONNAVN`).
- Alt annet vises som «(navn ikke vist)», uten orgnr. Er en personform
  kjent av endelsen, står koden foran: «ANS (navn ikke vist)».
- Ingen lister med navn. Generatoren og hvitelista bruker SAMME to
  funksjoner.
- Hvitelista tar et navn fra enhetsregisteret, eierskap og
  eierskap_historikk inn bare når det består regelen, og orgnummeret i
  paret følger navnet (`ORGANISASJONSNAVN`).
- Ny portprøve `personnavn`: «ETTERNAVN, FORNAVN» i en navnecelle er et
  funn som ikke kan kvitteres, uansett hvitelista. Bare navneceller:
  over hele teksten treffer mønsteret 1 818 distinkte «KOMMUNE, FYLKE».

Målt mot havbruk-radar-data 9dd439e, 851 distinkte navn, vist før → etter:

    person «ETTERNAVN, FORNAVN»     12 → 0
    person med orgnr (trolig ENK)    2 → 0
    selskap uten endelse            19 → 19
    annet (offentlig, stiftelse…)   36 → 25
    med kjent endelse              779 → 779   (3 ANS skjult fra før)

    hvitelista: −28 navn (12 på personnavnform), −16 orgnr, 0 nye
    porten: grønn på fullt bygg

De 11 «annet» som nå skjules, har verken en kode i navnet eller en form
på orgnummeret i noen av våre kilder.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
