---
dato: 2026-09-19
tittel: CSS er fritt, markup er en kontrakt — og kontrakten har en test
status: besluttet
commit: [fylles inn]
---

# CSS er fritt, markup er en kontrakt

**Bestemt:** Fire ting i den genererte HTML-en kan ikke endres av en
designrunde, bare av en beslutning med sin egen test:

1. **`data-felt` på hver verdicelle** — feltnavnet verdien kom fra.
2. **Semantiske tabeller** — `<table>` med `<caption>`, `<thead>` og
   `<th scope>`.
3. **Stabile ankere** — hver tabell har en `id`.
4. **`<time datetime>`** rundt hver dato, og JSON-LD-en på siden.

Alt annet er fritt: klassenavn, farger, kolonnerekkefølge, teksten i en
caption, hvilke tabeller som finnes, mellomrom.

`tests/test_markupkontrakt.py` håndhever punkt 1–3 over **alle maler**,
og prøven globber `maler/*.html.j2` framfor å liste dem. En ny sidetype
er dekket i det den legges der.

---

## 1. Hvorfor nå, og hvorfor ikke etterpå

Fire nye sidetyper skal bygges. I dag er `data-felt` en konvensjon:
`maler/lokalitet.html.j2` følger den fordi den ble skrevet mens
beslutningen 18.09 var fersk. **En ny mal som glemmer den gir en port som
er blind der, uten at noe feiler.**

Det er den samme feilformen som ble målt 18.09.2026: 24 navneverdier fra
changeloggen sto i endringstabellen, og `ukjent_navn` kunne ikke se én av
dem, fordi cellene var umerkede. Funnet kom ikke av at bygget ble rødt —
det kom av at noen målte. Med fire sidetyper til er det fire ganger så
mange steder å ikke måle.

Kostnaden av å gjøre det nå er 18 celler i én mal. Etterpå er det fire
maler skrevet uten kontrakten, og en prøve som feller alt på første
kjøring.

## 2. Hva `data-felt` er, og hva den ikke er

Merkingen sier **hvilket felt i kildens vokabular verdien kom fra** —
ikke hvordan den skal se ut, og ikke hva den betyr. Porten leser den mot
`NAVNEFELT`, `persondata.FORM_FELT` og `persondata.SEKTOR_FELT`;
alt annet er navn porten ikke bryr seg om, og det er meningen.

Regelen er derfor uten unntaksliste: **har en `<td>` en `{{ }}`, har den
`data-felt`.** En regel med unntak er en regel noen må huske, og
unntakslista ville vokst med hver sidetype.

Følgen er at også celler porten ikke leser blir merket — `rekkefolge`,
`gjelder`, `kilde`. Det er en pris verdt å betale: alternativet er å
avgjøre per celle om den er «interessant nok», og den avgjørelsen ville
blitt tatt på nytt, annerledes, i hver ny mal.

**Radnøkler er ikke verdiceller.** `<th scope="row">{{ e.felt }}</th>` er
feltnavnet, altså nøkkelen. Prøven krever merking på `<td>`, ikke på
`<th>`.

**Samme feltnavn kan stå i to tabeller med hver sin betydning.** Fra i
dag bærer både registertabellen og eierskapstabellen
`data-felt="kapasitet"` — lokalitetens kapasitet og tillatelsens — og
begge er riktige, for begge kildene kaller feltet det. En leser som
samler merkingene i en dict mister den ene bak den andre;
`felt_verdier()` returnerer derfor PAR, og en test som bygget en dict er
rettet.

## 3. Hvorfor prøven leser MALENE og ikke en rendret side

En prøve på rendret HTML trenger data. Suiten har ingen — `conftest.py`
peker `HAVBRUK_DATA_DIR` til en engangsmappe — så en rendret prøve måtte
hatt en fikstur per sidetype. Da er vi tilbake til en liste noen må huske
å utvide, og det er nøyaktig det som ikke virker.

Malene er kildekode, og de kan granskes uten data. Det gjør prøven
statisk og generell: `maler/*.html.j2`, uten navn i koden.

Grensa den arver, sagt rett ut: prøven ser `{{ }}` i malen, ikke verdier
i utputtet. En mal som setter sammen HTML i en makro eller inkluderer en
partial med en umerket celle, går klar. Det er det samme slaget grense
som porten selv har — den ser det generatoren merker — og den er skrevet
ned framfor å bli oppdaget.

Kommentarer fjernes før granskningen. En kommentar som FORKLARER
kontrakten inneholder `<td>` som eksempel, og første utgave av prøven
meldte sin egen dokumentasjon som brudd.

## 4. Plantet og verifisert

Prøven er kjørt mot ti konstruerte maler, alle med filnavn som **ikke**
er lokalitetssiden:

    verdicelle uten data-felt                     1 brudd, navngir fila
    samme celle MED data-felt                     rent
    celle med fast tekst (ingen {{ }})            rent
    radnøkkel i <th scope="row">                  rent
    tabell uten <caption>                         brudd
    tabell uten <thead>                           brudd
    tabell uten id                                brudd
    fire NYE sidetyper med samme feil             4 brudd, alle navngitt
    kommentar med <td> som eksempel               rent

Og mot dagens `maler/`: **18 brudd før, 0 etter.** De 18 var
verdiceller i lokalitetssiden som aldri hadde blitt merket — orgnumre,
kapasitet, hele lusetabellen, datoene og changeloggens `gjelder`/`kilde`.

## Hva som ville snudd det

- **At merkingen må bety noe for porten for å være verdt kostnaden.**
  Den gjør ikke det i dag for `rekkefolge` og `gjelder`. Skulle regelen
  strammes til «bare felter porten leser», er prisen en unntaksliste per
  sidetype, og gevinsten er 6 attributter mindre. Det er en dårlig byttehandel.
- **At en sidetype ikke er tabeller.** Et kart, en graf eller en
  tekstside har ingen verdiceller, og prøven sier da ingenting om den.
  Da må kontrakten utvides med hva merkingen er i det formatet —
  `data-felt` på en SVG-node, for eksempel — og det er en egen
  beslutning med sin egen måling. Prøven ville vært GRØNN og blind, og
  det er verdt å vite før den første ikke-tabellsiden skrives.
- **At prøven begynner å felle legitime designvalg.** Da er den for
  streng, og det skal vise seg som brudd på ting som åpenbart ikke er
  kontrakten. Ingen av de ti plantede tilfellene er i den kategorien i
  dag.

**Ville IKKE snudd det:** at en mal blir lengre av attributtene. Markup
som maskiner leser er ikke pynt, og den koster det den koster.
