---
dato: 2026-08-18
tittel: Prediksjonsloggen i drift, og hvorfor hele forløpet leses framfor endepunktene
status: gjeldende
commit: a389a6e
---

# Prediksjonsloggen i drift

**Bestemt:** `predictions/<dato>.yml` med obligatorisk retning, vindu,
terskel og grunnlag. `core/predictions.py` validerer og avgjør anslag
automatisk når vinduet lukker, som steg 9 i `run.py`. Resultatene skrives
til `data/prediksjoner/<dato>.parquet`.

**Hvorfor nå og ikke om noen måneder:** Etter at kildeklassifiseringen
viste seg feil, er dette det eneste laget der «kan ikke rekonstrueres» er
bokstavelig sant. En konkurrent med ti års backfillet historikk har
fortsatt null anslag gjort på forhånd, og commit-tidsstempelet kan ikke
forfalskes i etterkant.

Sekundært, og på kort sikt viktigere: dette er måleinstrumentet som gjør
vektene i `rules/signals.yml` til noe annet enn gjetninger. Fila
innrømmer selv at de er kvalifiserte gjetninger uten validering. De
forblir det uansett hvor mange kilder som legges til, fordi ingenting
ellers forteller hvilke signaler som faktisk betydde noe.

**Hele forløpet, ikke endepunktene.** Et anslag treffer den uka terskelen
passeres. Går kapasiteten opp 25 % i september og tilbake i oktober, er
anslaget om vekst riktig — bevegelsen kom. Leses kun start og slutt,
dømmes riktige anslag som bom. Dette er grunnen til at
`snapshot.les_mellom()` finnes, og det er dekket av test.

**Du kan ikke spå fortiden.** `vindu.fra` må være samme dato som filnavnet
eller senere. Uten den regelen kan et anslag skrives etter utfallet, og
treffraten er verdiløs — også for meg selv, fordi jeg da ikke lenger kan
vite hvilke jeg skrev i forkant.

**Grunnlag er obligatorisk med minstelengde.** Reverseringskriteriet fra
17.08 sier at blir anslagene så vage at de ikke kan feile, er problemet
formatet. Et anslag uten begrunnelse lærer ingenting når det bommer.

**Tre utfall, ikke to.** `kan_ikke_avgjores` telles for seg. Er andelen
høy, svikter formatet eller kildedekningen, ikke dømmekraften. Utgangsverdi
null gir uavklart framfor stille bom — samme felle som `signals.py` har med
`if old == 0: return False`, men her sagt høyt.

**Formatfeil feller ikke kjøringen.** Innsamlingen er viktigere: en tapt
uke kan ikke hentes igjen, mens en feilskrevet YAML kan rettes i morgen.
Avviket går i tilsyn-lista og gjør jobben rød.

**Feil fanget ved kjøring, ikke av tester:** Første versjon evaluerte
anslag med formatfeil, skrev resultatet, og markerte dem som ferdige —
slik at retting av YAML-en ikke hjalp. 86 tester var grønne. Den falt
først da `run.py` ble kjørt for ekte. Regel 6 gjorde jobben sin.

**De tre første anslagene er ikke mine vurderinger.** De er utledet av
Claude fra trafikklysvedtaket 19.06.2026 sammenholdt med registeret, som
fortsatt viser en eldre runde på fire av tretten produksjonsområder. De
er en god måte å ta mekanikken i bruk på, men de måler ikke det loggen
finnes for å måle. Det gjør den først når jeg skriver et anslag som ikke
kunne vært utledet av offentlige dokumenter alene.

**Prisen:** Et lag til å vedlikeholde, og en fristelse til å skrive
anslag som er trygge nok til å treffe. Den fristelsen er ikke løst av
formatet.

**Ville snudd det:** At andelen `kan_ikke_avgjores` blir høy nok til at
loggen ikke måler noe. Da er problemet at anslagene handler om felter
kildene ikke dekker godt nok, og formatet må kreve at feltet finnes før
et anslag godtas.
