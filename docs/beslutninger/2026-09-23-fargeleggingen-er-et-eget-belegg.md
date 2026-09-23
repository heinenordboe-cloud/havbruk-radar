---
dato: 2026-09-23
tittel: Fargeleggingen er et eget belegg — de 19 tomme cellene var ikke en mangel
status: utkast
commit: [fylles inn]
---

# Fargeleggingen er et eget belegg

**UTKAST.** Hva som ble bestemt står under, med målingene.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt: en tredje beleggsgrad, «beslutning»

    ordrett            fargeordet står i FORSKRIFTENS bestemmelse
    kapittelhjemmel    fargen er utledet av hvilket kapittel i
                       FORSKRIFTEN området er plassert i
    beslutning         fargeordet står i departementets kunngjøring av
                       fargeleggingen, ikke i forskriften   <- NY

`sources/trafikklysvedtak.py` leser kapasitetsjusteringsforskriftene, og
MÅLT 20.09.2026 kunne 19 av 65 celler ikke leses av dem.

**Grunnen var ikke at forskriftene er ufullstendige.** Trafikklyset
besluttes i to trinn: departementet fargelegger alle 13 områdene, og
deretter fastsettes forskrift for det som må REGULERES — vekst i grønne
områder og nedtrekk i røde. Et gult område krever ingen bestemmelse.
Fargen finnes; den står bare ikke i Lovtidend.

De 19 tomme cellene var altså riktig lest og feil forstått. Kilden
manglet ingenting.

## Bestemt: belegget er et annet sted, ikke et svakere belegg

«Utledet» er tonet ned visuelt, fordi fargeordet IKKE står — det er
sluttet fra kapittelplasseringen. «Beslutning» er ikke tonet ned:
fargeordet står ordrett, i en kunngjøring fra det organet som traff
vedtaket. Forskjellen er HVOR det står.

Ruta får derfor fullt fyll med en stiplet underkant, og
**setningen står på siden** — i en `<details>` ved siden av fargen, med
dato og lenke. En farge som ikke kan slås opp i Lovtidend må kunne
etterprøves der den vises.

## Målingen: de to kildene er aldri uenige

MÅLT 23.09.2026 over alle 65 cellene:

    begge sier noe      46   enige 46, sprik 0
    bare beslutningen   19
    bare forskriften     0

Etter dette har alle 13 områdene en farge i 2026, og **registerets
«gjelder nå» stemmer med 2026-runden for alle tretten**. De ni gule som
tidligere sto som «ikke oppgitt» i forskriftstabellen mens registeret sa
«gul», var ikke en uenighet mellom kildene. Det var én kilde som tiet.

## Bestemt: bare runde 2026 publiseres nå

`beslutning.GODKJENT = {"2026"}` er en **menneskelig kvittering**, ikke
en teknisk grense. Avsnittene skal leses mot kroppen av et menneske før
de publiseres. Alle fem rundene er parset og lagt fram ordrett i
`docs/VERIFISERING-FARGELEGGINGEN.md`; de fire andre legges til når de
er lest.

Til da står 12 celler som «ikke oppgitt». En tom celle er ærligere enn
en celle ingen har sett på.

## Bestemt: ingen utledning fra «resten ble gule»

Bare celler der kunngjøringens ordlyd navngir området fylles. En setning
som «ni områder får gult lys» uten oppregning fyller ingenting — den er
et sammendrag, ikke en oppregning.

En TALLREKKE er derimot en oppregning: 2017-meldingens
«produksjonsområdene 1 og 7-13» navngir åtte områder, komprimert. Å
skrive ut 7, 8, 9, 10, 11, 12, 13 er aritmetikk, ikke en slutning om
verden.

## Bestemt: PO9 bærer departementets egen merknad

Kunngjøringen 19.06.2026 sier at fargeleggingen følger ekspertgruppens
vurdering når de to grunnlagsårene er enige, og at departementet vurderer
området særskilt når de ikke er det. For 2026 gjelder det ett område.
Setningen står ordrett på PO9s side, med dato og lenke, uten et
sammendrag foran: hvorfor en farge ble som den ble, er ikke vår sak å
veie.

`beslutning.saerskilt()` finner det samme for 2022 (PO2, PO4, PO5) og
2024 (PO4, PO8). De vises ikke før rundene er godkjent.

## Bestemt: områdenavnene står som de står

MÅLT mot produksjonsområdeforskriften (FOR-2017-01-16-61), hentet
23.09.2026: forskriften bruker **to stavemåter av fem av navnene, i to
deler av seg selv**. § 3, som oppretter områdene, skriver «Ryfylket»,
«Nordhordland til Stadt», «Stadt til Hustadvika». Vedlegg 1, som
avgrenser dem geografisk, skriver «Ryfylke», «Nordhordland til Stad»,
«Stad til Hustadvika».

Akvakulturregisterets navn er § 3s, tegn for tegn, for alle tretten.
Ingenting endres. Hele tabellen står i
`docs/VERIFISERING-FARGELEGGINGEN.md`.

## Bestemt: dette er ikke en kilde

Ingen `Observation`, ingen `data/raw/`, ingen nettverkskall ved bygging.
`beslutning.py` leser fem arkiverte kropper og ingenting annet, og
summene er pinnet — en kropp som har endret seg stopper med
`Kroppsprik` framfor å bli lest stille.

Beslutningen fra 2018 kan ikke hentes på nytt i 2027, og en «kilde» som
bare kan lese fem arkiverte filer er ikke en kilde. Den er
dokumentasjonsgrunnlag, samme status som
`docs/VERIFISERING-PRESSEMELDINGER.md`.
`docs/beslutninger/2026-09-05-vedtakskilden.md`, som valgte vekk
pressemeldinger som KILDE, står uendret.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
