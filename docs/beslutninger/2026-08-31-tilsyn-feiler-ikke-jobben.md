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

Endringen strekker seg over to repoer, og begge må med for at den skal
virke:

| repo | commit | hva |
| --- | --- | --- |
| `havbruk-radar` | `64e6976` | exit-kode-logikken i `run.py`, `::warning::`-annotasjonen, `tilsyn=`-utfallet til `GITHUB_OUTPUT` |
| `havbruk-radar-data` | `564baff` | `samle.yml` leser `outputs.tilsyn` i tillegg til `outcome`, slik at DELVIS-merket dekker det samme som før |
| `havbruk-radar` | `e652713` | presiseringen under: prediksjonsformat tilbake til exit 1 |

Rekkefølgen på pushen er ikke likegyldig: koden først, workflowen etter.
Motsatt vei kjører ny DELVIS-logikk mot en `run.py` som ikke skriver
`tilsyn=` — og da leses utfallet som tomt, merket faller bort på uker med
et kvalitetsvarsel, og feilen er stille.

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

## Presisering (samme dag)

**Formatfeil i prediksjons-YAML er uttrykkelig UNNTATT fra dette.** Et
anslag i `predictions/` som ikke lot seg lese gir exit 1, med
`::error::`, på linje med forfalte kilder og unntak i fetch/parse.

Grunnen er at det ikke er en datakvalitetsobservasjon. Skillet som
gjelder er mellom en **leveranse som uteble** og en **observasjon om
innholdet**:

- Et volumfall, et dødt felt, et NACE-søk uten treff — dette er
  observasjoner om noe VI IKKE STYRER. Alarmen står til noen har
  undersøkt og kvittert, og den nullstiller seg ikke; derfor rødlyser
  den hver uke uansett hva som skjedde akkurat den uka, og derfor er den
  en `::warning::`.
- En feilskrevet YAML i `predictions/` er en fil vi selv eier, som ble
  skrevet feil og ikke lot seg lese. `predictions.evaluer()` hopper over
  anslaget, så et vindu som lukket i dag lukket uten dom — og et anslag
  som ikke ble avgjort i vinduet sitt blir aldri avgjort. Det er samme
  form som en tapt uke: noe som skulle vært skrevet, ble ikke skrevet.

Asymmetrien i «kan rettes i morgen» er det som avgjør. Volumvarselet
lider ingenting av å vente en uke — det står der fortsatt. Anslaget gjør
det: fristen er passert når noen oppdager det.

Presiseringen finnes fordi beslutningsteksten over var upresis nok til å
bli lest bokstavelig i feil retning én gang allerede. Setningen «Jobben
skal kun feile ved reelle feil: forfalte kilder, eller uventede unntak i
fetch/parse» ble lest som en uttømmende liste, og formatfeil — som lå i
samme `tilsyn`-liste i koden av historiske grunner — fulgte med over til
exit 0. Det gamle `run.py` hadde en eksplisitt kommentar om at avviket
skulle gjøre jobben rød; kommentaren ble omskrevet i stedet for å bli
lest som innsigelsen den var.

## Hva ville snudd det

Hvis KREVER TILSYN i praksis viser seg å fange reelle, tidssensitive
feil — altså at et rødt flagg her faktisk betyr "noe er akutt galt nå"
og ikke "noe har vært rart en stund" — bør det tilbake til å feile
jobben. Samme hvis warning-annotations i praksis blir oversett (ikke
sjekket ukentlig), slik at terskelbrudd aldri følges opp.
