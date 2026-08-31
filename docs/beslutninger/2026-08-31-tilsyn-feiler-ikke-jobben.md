---
dato: 2026-08-31
tittel: "Datakvalitetsvarsler (KREVER TILSYN) skal ikke feile den ukentlige jobben"
status: besluttet
commit: 64e6976
---

## Beslutning

KREVER TILSYN-vakten (terskelbrudd i datakvalitet, f.eks. et felt som
har levert samme verdi i for mange kjøringer på rad) skal ikke lenger
gi exit code 1 i den ukentlige innsamlingsjobben. Jobben skal kun
feile (exit 1) ved reelle feil: kilder som var planlagt hentet denne
uka og ikke ble det ("forfalte kilder"), eller uventede unntak i
fetch/parse. KREVER TILSYN-funn logges fortsatt — som GitHub Actions
warning-annotation, og påvirker fortsatt DELVIS-prefikset i
commit-meldingen — de slutter bare å farge selve jobbstatusen rød.

## Hvorfor

Telleren bak KREVER TILSYN nullstilles ikke når terskelen er brutt.
Det betyr at når terskelen først er brutt (som med
lusetall.har_medikamentell_behandling og lusetall.har_rensefisk, 90 og
172 kjøringer), rødlyser jobben hver eneste uke framover, uavhengig av
om noe faktisk er galt akkurat den uka — helt til rotårsaken i
kildekoden er fikset. En status som er rød av grunner som ikke er
denne ukas problem, slutter å bære informasjon. Da blir det naturlig å
ignorere de røde kryssene, og systemet mister poenget sitt akkurat når
det trengs — når en reell feil dukker opp samtidig med et kjent, uløst
kvalitetsvarsel.

Reelle feil (kilde som ikke oppdaterte seg, snapshot som ikke ble
skrevet, unntak i pipelinen) er en annen alvorlighetsgrad enn "et felt
ser mistenkelig stabilt ut over tid", og bør ikke dele signal.

## Hva ville snudd det

Hvis KREVER TILSYN i praksis viser seg å fange reelle, tidssensitive
feil — altså at et rødt flagg her faktisk betyr "noe er akutt galt nå"
og ikke "noe har vært rart en stund" — bør det tilbake til å feile
jobben. Samme hvis warning-annotations i praksis blir oversett (ikke
sjekket ukentlig), slik at terskelbrudd aldri følges opp.
