# Prediksjoner

Hva du trodde, skrevet ned før du visste.

Dette er det eneste laget i prosjektet som ikke kan rekonstrueres.
Snapshots kan backfilles — lusetall ligger ute tilbake til 2012.
Changelog og signaler er rene funksjoner av arkivet og kan regnes ut
på nytt. Et anslag skrevet før utfallet kan ingen skaffe seg i
etterkant, og commit-tidsstempelet er beviset.

Sekundært, og på kort sikt viktigere: dette er måleinstrumentet som gjør
vektene i `rules/signals.yml` til noe annet enn gjetninger. Fila sier det
selv. Uten fasit på hva som faktisk betydde noe, forblir de gjetninger
uansett hvor mange kilder som legges til.

## Regelen som gjør loggen verdt noe

**Commit anslaget før vinduet åpner.** `vindu.fra` må være samme dato som
filnavnet eller senere, og valideringen håndhever det. Uten den regelen
kan et anslag skrives etter utfallet, og hele treffraten er verdiløs —
også for deg selv, fordi du ikke lenger kan vite hvilke du skrev i
forkant.

## Fila

Én fil per dato du skriver anslag: `predictions/2026-08-18.yml`.
Filen røres aldri etter at den er committet. Endrer du mening, skriver du
et nytt anslag i en ny fil — det gamle blir stående som det du trodde da.

```yaml
prediksjoner:
  - id: "2026-08-18-1"
    entitet: "10029"            # entity_id: orgnr eller lokalitetsnummer
    kilde: "akvakultur"
    felt: "kapasitet"
    type: "endring"
    retning: "opp"
    terskel_prosent: 10
    vindu:
      fra: "2026-08-18"
      til: "2027-02-18"
    grunnlag: >
      Tillatelser ble flyttet hit i juli, og lokaliteten ligger i et
      grønt produksjonsområde. Kapasiteten følger etter tillatelsen,
      ikke omvendt.
```

## Tre typer

**`endring`** — feltet beveger seg minst `terskel_prosent` i `retning`
(`opp` eller `ned`) på et tidspunkt i vinduet.

**`verdi`** — feltet tar verdien `verdi` på et tidspunkt i vinduet.
For trafikklys, konkursflagg og andre ikke-numeriske felter.

```yaml
    type: "verdi"
    felt: "prodomraade_status"
    verdi: "RØD"
```

**`uendret`** — feltet holder seg innenfor ±`terskel_prosent` gjennom
hele vinduet. Det er et ekte anslag: «her skjer ingenting» er en påstand
som kan feile.

## Hvordan et anslag avgjøres

Utgangsverdien hentes fra siste snapshot til og med `vindu.fra`.
Deretter leses **hele forløpet** gjennom vinduet, ikke bare sluttverdien.

Det er et bevisst valg. En kapasitetsøkning på 20 % i februar som er
reversert i mars er et treff — du spådde bevegelsen, og den kom.
Leser man kun endepunktene, dømmes riktige anslag som bom.

Tre utfall:

- `traff` — vilkåret ble oppfylt i vinduet
- `bom` — vinduet lukket uten at det skjedde
- `kan_ikke_avgjores` — ingen utgangsverdi, ingen observasjoner i
  vinduet, eller utgangsverdi null (prosent er udefinert)

**Følg med på andelen `kan_ikke_avgjores`.** Er den høy, er det formatet
eller kildedekningen som svikter, ikke dømmekraften din. Et anslag om et
felt som ikke samles inn kan aldri avgjøres.

## Kjøring

Prediksjoner avgjøres automatisk i den ukentlige kjøringen, etter at
dagens snapshot er skrevet. Resultatene havner i
`data/prediksjoner/<dato>.parquet` og i commit-meldingen.

    python run.py --fasit     # treffrate per kilde og type

Resultatene er avledet: de er en ren funksjon av (anslag, snapshots i
vinduet), og begge er append-only. Derfor skrives de aldri tilbake i
denne mappa.

Et formatavvik feller ikke kjøringen — innsamlingen er viktigere, og en
tapt uke kan ikke hentes igjen mens en feilskrevet YAML kan rettes i
morgen. Avviket gjør jobben rød i stedet.

## Hva som er verdt å spå

Anslag som kun gjentar en signalregel måler ingenting. Verdien ligger i
det reglene ikke kan se: at noe skjer et bestemt sted, innen en bestemt
tid, av en grunn du kan begrunne. `grunnlag` er obligatorisk og har
minstelengde nettopp fordi begrunnelsen er det som gjør et bomskudd
lærerikt.

Begynn med tre til fem. Sett vinduene ulikt — noe på tre måneder, noe på
tolv — slik at treffraten etter hvert kan brytes ned på horisont.
