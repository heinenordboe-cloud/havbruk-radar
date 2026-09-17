# Vurdering 17.09.2026 — prøven har feilet tre ganger. Er det samme feil?

`publiseringsvakt.py` har to prøver som leter etter en VERDI i et ferdig
dokument: `ukjent_orgnr` (nisifrede tall) og `personform` (koder som
`ENK`). Begge har måttet rettes etter møtet med ekte output, og nå tre
ganger på tre uker:

| dato | hvor | hva skjedde |
|---|---|---|
| 15.09 | HTML | `\b\d{9}\b` traff heltallsdelen av `96697320.109`, biomasse i kilo. **Falskt funn.** |
| 16.09 | HTML | `DA` kom inn i `PERSONFORMER` og kolliderte med `kapasitet_enhet = DA`, dekar, 748 rader. **Fire falske funn** på den ene ekte genererte fila. |
| 16.–17.09 | CSV | Tokenregelen fra 15.09 krever at tallet ikke har komma på noen side. I en CSV er kommaet avgrenseren, så `999888777,Kari` ga **ingen funn**. Et orgnummer i en CSV-kolonne var usynlig. |

Spørsmålet fra oppgaven: er det samme feil hver gang, og bør prøven
virke på en annen måte?

**Kort svar: nei, det er to feil — og den ene av dem kan ikke fjernes,
bare flyttes dit den er billigst.**

---

## 1. Prøven har to ledd, og bare det ene har sviktet

`ukjent_orgnr` gjør to ting etter hverandre:

1. **Tokenisering.** Finn kandidatene: hvilke byte-sekvenser i dette
   dokumentet er et tall på ni siffer?
2. **Proveniens.** Er kandidaten gjort rede for — finnes den igjen blant
   orgnumrene i de FILTRERTE snapshotene?

Ledd 2 er det som gjør vakten mulig i det hele tatt. Modulens egen
docstring forklarer hvorfor: et forbud mot mønsteret `\b\d{9}\b` er målt
ugjennomførbart, siden 1807 `entity_id` og 2953 `eier_orgnr` ER nisifrede
tall. Ved å snu prøven til en hviteliste avgjør PROVENIENSEN og ikke
mønsteret, og det leddet er format-uavhengig og har aldri sviktet.

**Alle tre feilene ligger i ledd 1 eller i dets motstykke for
`personform`.** Ingen av dem har vært en feil i «er dette nummeret gjort
rede for».

Det er verdt å si rett ut, fordi det avgjør hvor alvorlig saken er: den
bærende ideen holder. Det som har gått galt er innpakningen rundt
verdien.

## 2. To av tre er samme feil. Den tredje er en annen.

### Familie A — TOKENISERING: hvor slutter verdien? (15.09 og 16.–17.09)

Disse to er samme feil, og de er hverandres speilbilde:

- 15.09 var regelen for LØS. `\b` står mellom siffer og punktum, så
  heltallsdelen av et desimaltall ble et treff.
- 16.–17.09 var den samme rettingen for STRAM. Lookaround-en som
  utelukket punktum utelukket også komma, og i en CSV er kommaet ikke en
  desimalseparator — det er strukturen.

Begge er samme spørsmål: **hvilke tegn rundt tallet hører til tallet, og
hvilke er formatets egne skilletegn?** Og det spørsmålet har et annet
svar i HTML enn i CSV enn i JSON. Det er ikke en svakhet ved akkurat
disse regexene — det er en egenskap ved å lete etter verdier i en flat
tekst som et format har pakket dem inn i.

Rettingen 17.09 er derfor riktig i FORM og ikke bare i virkning: CSV-en
parses, cellene hentes ut, og prøven stilles på cellen — der formatets
skilletegn ikke lenger finnes. Regexen er uendret; det er inndataene som
er ryddet først.

Målt 17.09 på det samme tallet i ti innpakninger:

    <td>999888777</td>            finnes
    {"orgnr": "999888777"}        finnes
    {"orgnr": 999888777}          finnes
    orgnr;999888777               finnes
    | 999888777 | (markdown)      finnes
    999888777\tKari (rå TSV)      finnes
    999888777,Kari  (rå CSV)      USYNLIG   <- lukket 17.09 ved å parse
    [999888777, 123] (JSON)       USYNLIG   <- står åpent

**JSON-lista er den samme feilen i et format som ennå ikke er lukket.**
Ingen generator i repoet skriver `.json` i dag, og JSON-LD-en i
`nettsted.py` bærer ingen organisasjonsnumre — men det er en påstand om
i dag. Hullet står i `publiseringsvakt.py` sin docstring, målt, framfor å
bli oppdaget av en lekkasje.

### Familie B — VERDIEN BETYR NOE ANNET I ET ANNET FELT (16.09)

`DA` er ikke en tokeniseringsfeil. Tallet — koden — ble funnet helt
riktig. Problemet er at `DA` **er en gyldig verdi to steder**:
`organisasjonsform = DA` er delt ansvar, `kapasitet_enhet = DA` er dekar.

Ingen tokenisering kan skille dem, for de er tegn for tegn like. Bare
FELTET kan.

Og her er forskjellen fra familie A verdt å merke seg: `ukjent_orgnr` har
ikke dette problemet i det hele tatt. Et orgnummer i hvitelista er
legitimt uansett hvilket felt det står i — det er det samme selskapet.
`personform` er det motsatte: koden er helt tom for mening uten feltet
sitt.

Det er derfor de to prøvene ikke kan få samme behandling, og hvorfor
«samme feil tre ganger» er feil diagnose.

## 3. Så hva ER rotårsaken?

Begge familiene har samme opphav ett hakk lenger opp:

**Generatoren VET hvilket felt hver verdi kom fra, og kaster det bort før
vakten får se dokumentet.**

Observasjonsformatet er `(entity_id, field, value)`. Feltet er der hele
veien gjennom pipelinen. Så rendres det til HTML eller CSV, og da er
verdien igjen alene — og vakten må rekonstruere fra punktum, komma og
avstand det generatoren hadde i hånda.

Hver av de tre rettingene er en bedre rekonstruksjon for ett format.
Hver av dem var riktig for formatet den ble skrevet for, og to av dem var
gale for det neste.

Det er CLAUDE.md 1b-2 i en femte utgave: **en kontroll som måler noe som
LIGNER det den skal måle, og som er riktig i akkurat de tilfellene der de
to faller sammen.** «Tegn rundt tallet» ligner «hvilket felt tallet
tilhører», og de faller sammen i HTML helt til de ikke gjør det i CSV.

## 4. Bør prøven virke på en annen måte?

Fire veier er vurdert. **Ingen av dem bygges nå** — dette er en vurdering,
og valget er eierens.

### A. Fortsette med én rekonstruksjon per format

Det som skjer i dag. `.csv`/`.tsv` parses per kolonne; alt annet leses som
tekst.

- **For:** billig, og hvert format får en riktig løsning.
- **Mot:** et nytt format trenger en ny rekonstruksjon, og fraværet
  oppdages av en LEKKASJE, ikke av en test. JSON-hullet er beviset: det
  ble funnet fordi noen målte, ikke fordi noe feilet.

### B. La generatoren skrive et manifest over hva den rendret

Vakten sammenligner output mot manifestet i stedet for å gjette.

- **For:** feltet er tilbake, presist.
- **Mot, og det er avgjørende:** manifestet er PRODUSENTENS EGEN PÅSTAND.
  En generator som lekker et felt den ikke burde, fører det heller ikke
  opp. Vakten finnes nettopp for å fange det generatoren gjorde galt, og
  en vakt som spør generatoren om fasiten er ikke en vakt. Den kan LEGGE
  TIL dekning («du rendret et felt du ikke skulle»), men den kan ikke
  erstatte granskningen av utputtet.

### C. Utvide merkekonvensjonen til å gjelde alle verdier

`ukjent_navn` har allerede formen: generatoren merker navn med
`data-navn` eller `class="eier"`, og vakten leser merkingen. I CSV er
kolonneoverskriften den samme merkingen. Det kunne utvides til hvert felt
— `<td data-felt="organisasjonsform">DA</td>` — og da ville `personform`
sluttet å gjette i HTML også.

- **For:** ett mekanisme i stedet for tre, og den er halvbygget.
- **Mot:** merkingen er også produsentens påstand, med samme svakhet som
  B — men i en mildere form, fordi den feiler ÅPENT: en umerket verdi blir
  ikke godkjent, den blir bare ikke sett av den presise prøven.
- **Og den må ikke erstatte den brede prøven.** Går `personform` over til
  «bare merkede celler», blir en bar `ENK` i løpende tekst usynlig — og
  det er dårligere enn i dag. Riktig form er begge: **merket → presist,
  umerket → bred prøve for de entydige kodene.** Som er omtrent det som
  finnes, uten at det er skrevet ned som ÉN design på tvers av formater.

### D. Slutte å gjette, og bare granske det vi selv har generert

Vakten leter i alle filer i publiseringsmappa. Et alternativ er å granske
bare filer generatoren selv skrev, i den formen den skrev dem.

- **Mot:** da forsvinner hele poenget. En fil noen la i mappa ved siden
  av — en eksport, en gammel kopi, en `.parquet` — er like publisert, og
  `ugranska`-slaget finnes nettopp for å si fra om dem.

## 5. Anbefaling

**Behold A, skriv ned C som retningen, og lukk JSON-hullet når noen
skriver en `.json`.**

Begrunnelsen er at prisen for å ta feil ikke er symmetrisk, og at den
peker ulik vei for de to prøvene:

- **`ukjent_orgnr` feiler i dag mot for LITE.** Et manglende funn er en
  publisert lekkasje. Her er det verdt å parse formatet, fordi
  tokeniseringen da forsvinner som problem i stedet for å bli finjustert.
  Det er gjort for CSV. JSON er den neste, og den er billig.
- **`personform` feiler mot for MYE.** Et falskt funn på hver
  arealangivelse ville fått vakten slått av — som er argument 1 mot
  blokkering i beslutningen 15.09, og det eneste argumentet der som ble
  prøvd mot virkeligheten og viste seg reelt. Her er en presis, merket
  prøve gevinsten, og den brede prøven må bli stående under som gulv.

Det som IKKE bør gjøres er å lete etter en enkelt, format-uavhengig
regex. Tre forsøk har vist at den ikke finnes, og et fjerde forsøk ville
vært det samme som å utlede `domene` av det uttrekket emitterte: en
størrelse som er riktig i akkurat de tilfellene man har sett.

## 6. Hva som ville endret vurderingen

- **At noen skriver en generator som ikke merker.** Hele C hviler på at
  merkingen faktisk settes. Kommer det en side bygget av en annen mal
  uten `data-`-attributter, er den presise prøven blind der, og da er den
  brede prøven det eneste som står igjen — og den må fortsatt duge.
- **At vakten begynner å felle falskt i drift.** I dag er den blokkerende
  og ren på det ene ekte utputtet vi har. Begynner den å melde falske
  funn i en ukentlig jobb, er presisjon viktigere enn dekning, og da
  flyttes vekten mot C raskere enn planlagt.
- **At et format med lekkasjepotensial blir publisert før det er
  dekket.** `.parquet`, `.xlsx` og `.pdf` rapporteres i dag som
  `ugranska` — vakten sier at den ikke har lest dem. Blir en av dem en
  fast del av publiseringen, er `ugranska` ikke lenger et ærlig svar,
  men en permanent advarsel ingen leser.
