---
dato: 2026-10-05
tittel: Et navn som ender på en personform vises ikke — heller ikke som tildelt
status: utkast
commit: d934c10, 2c880f7
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

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
