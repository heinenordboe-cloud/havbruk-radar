---
dato: 2026-10-05
tittel: Et navn som ender på en personform vises ikke — heller ikke som tildelt
status: utkast
commit: (denne)
---

# Personformnavn vises ikke

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt

Et `tildelt_navn` eller `mottaker_navn` som ender på en personform
(`publiseringsvakt.personform_i_navn()`: endelsen lest av `FORM_SUFFIKS`,
avgjort av `persondata.er_personform()`) byttes i generatoren mot
`«<kode> (navn ikke vist)»`, merket `data-felt="navn_skjult"`.
Orgnummeret ved siden av fjernes, og cellen holdes utenfor søkeindeksen.

Porten maskerer NØYAKTIG den teksten i en celle med den merkingen. Står
noe annet i en `navn_skjult`-celle, er det et `ukjent_navn`.

De tre kvitteringene fra 2026-09-19 er trukket i datarepoet
(`data/kvitteringer/2026-10-05.json`).

## Målt 05.10.2026, lokalt bygg mot havbruk-radar-data (e087df1)

    gammel kode   14 personform-funn, alle kvittert, 14 lokalitetssider
                  3 ulike verdier, alle ANS, alle i `tildelt_navn`
                  de 3 tildelt_orgnr på 12 + 1 + 1 sider
    ny kode        0 personform-funn, 0 kvitteringer aktive
                  de 3 tildelt_orgnr på 0 sider
                  14 forekomster av «ANS (navn ikke vist)»

Utenom de 14 lokalitetssidene endret bygget seg ikke av dette. 28
selskapssider skilte seg mellom to bygg på samme data, men bare i hvilket
av to navn på samme orgnummer tittelen bruker — en forskjell som finnes
uten denne endringen.

## Hvorfor endelsen og ikke registeret

For `tildelt_navn` finnes ingen annen form i dataene: 0 av de 3
tildelt_orgnr står i enhetsregisteret-snapshotet, rått eller gjennom
døra, og `eierskap.organisasjonsform` er formen til den som eier
tillatelsen NÅ (AS for alle tre). Kvitteringen fra 19.09 sier det samme,
og sier også at endelsen er navnet og ikke formen. Det står fortsatt.

## Hva den ikke dekker

- **ENK.** Et enkeltpersonforetak bærer ingen endelse, og
  `FORM_SUFFIKS` har ikke koden. Et ENK-navn i `tildelt_navn` fanges
  ikke av denne regelen.
- **`eier_navn`.** Er uendret: den har `eier_type` og
  `organisasjonsform`, og `_eierrad()` spør dem.
