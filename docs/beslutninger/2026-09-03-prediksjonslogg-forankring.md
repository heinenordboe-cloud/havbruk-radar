---
dato: 2026-09-03
tittel: Prediksjonsloggen forankres utenfor repoet, og utfallet skrives ved siden av påstanden
status: utkast
commit: 
---

# Prediksjonsloggen forankres utenfor repoet

> **Utkast.** Alt under «Hva som var galt», «Hva som er gjort» og «Hva som
> ble målt» er skrevet fra koden og fra kjøringer mot filene på disk.
> Avsnittene merket **[din vurdering]** er ikke fylt ut — de er dine.

**Bestemt:** `forsegl.py` validerer prediksjonsfilene, hasher dem på to
nivåer og skriver `predictions/SEGL.txt`. Rot-hashen derfra forankres
utenfor repoet. Prediksjonsformatet utvides med `feil_hvis`, `konfidens`
og et `utfall`-felt som står tomt til vinduet er ute, og prediksjonsfila
kan for første gang endres etter commit — men bare i utfallsfeltene, og
bare fordi kjernehashen gjør oppmykningen etterprøvbar.

---

## Hva som var galt

Beslutningen fra 18.08 sier at «commit-tidsstempelet er ankeret, og det
er derfor prediksjonene ligger i git og ikke i en database».
`core/predictions.py` gjentar det i docstringen: «Commit-tidsstempelet
kan ikke forfalskes i etterkant.»

Det stemmer ikke. `GIT_AUTHOR_DATE` og `GIT_COMMITTER_DATE` er felter den
som committer fyller ut selv:

    GIT_AUTHOR_DATE="2020-01-01T12:00:00" \
    GIT_COMMITTER_DATE="2020-01-01T12:00:00" \
    git commit -m "spådd for lenge siden"

Hele historikken kan i tillegg skrives om med `filter-branch` og tvinges
ut på nytt. En tidslinje eieren kan redigere er ikke et bevis mot eieren,
og prediksjonsloggen er verdt nøyaktig så mye som beviset for at den ble
skrevet på forhånd.

Feilen er den samme formen som CLAUDE.md 1b-2 beskriver: **en mekanisme
som måler noe som LIGNER det den skal måle, og som er riktig i akkurat de
tilfellene der de to faller sammen.** Commit-tidsstempelet er sant hver
gang jeg ikke har grunn til å lyve. Det er nøyaktig den betingelsen et
bevis ikke får hvile på — beviset skal holde i det ene tilfellet der
motparten har grunn til å tvile, og der faller det.

To andre hull sto igjen, og de er lettere å se:

- **Ingen falsifisering skrevet på forhånd.** Formatet krevde `grunnlag`,
  men ikke hva som ville gjort anslaget GALT. Uten det kan et bomskudd
  fortelles om til et treff i etterkant — «egentlig var det jo dette jeg
  mente» — og begrunnelsen er ikke til hinder, den er råstoffet.
- **Ingen konfidens.** Loggen kunne si hvor ofte anslagene traff, men
  ikke om de var trygge når de burde vært det. Å treffe 70 % og ha sagt
  95 % er en annen og verre feil enn å bomme, og formatet kunne ikke se
  den i det hele tatt.

---

## Hva som er gjort

### `forsegl.py` — to hasher, ikke én

Den avgjørende designbeslutningen er at hvert anslag hashes på to nivåer.
Grunnen er en direkte konflikt mellom to av kravene:

    b) anslaget er ikke endret i etterkant
    c) bommene står der sammen med treffene

Krav (c) betyr at utfallet skal skrives inn ved siden av påstanden. Krav
(b) betyr at fila ikke skal endres. Med én filhash bryter (c) seglet hver
eneste gang et anslag avgjøres — altså nøyaktig når seglet trengs. Da blir
et brutt segl det normale, og et segl som brytes rutinemessig blir slått av.

Derfor:

| | Dekker | Endres når utfall føres inn | Verifiseres av |
|---|---|---|---|
| `filhash` | filas rå bytes | **ja** — det er meningen | `shasum -a 256`, uten dette verktøyet |
| `kjernehash` | påstandsfeltene alene, kanonisert | **nei** | `forsegl.py`, eller for hånd fra `SEGL.txt` |

`kjernehash` er den som forankres. Den utelater `utfall`, `utfall_dato`,
`utfall_kilde` og `utfall_note`, og bare dem. `grunnlag` er MED i kjernen:
en begrunnelse som kan omskrives i etterkant lar et bomskudd bli et treff
av andre grunner enn det påsto.

Kanoniseringen er sortert JSON, ikke rå YAML. En reformatert fil eller en
rettet kommentar er ikke en endret påstand, og et segl som brøt på
whitespace ville blitt slått av etter tredje falske alarm.

`--sjekk` skiller de to bruddene fra hverandre i klartekst — «en
kjernehash har endret seg» mot «utdatert, men ingen påstand er endret».
Uten det skillet er utgangen fra verktøyet ubrukelig som bevis: en
skeptiker kan ikke se forskjell på juks og normal drift.

### Formatet utvidet med tre felter

`feil_hvis`, `konfidens` og `utfall` er nå påkrevd av `forsegl.py`.

Merk hvem som krever dem: **`forsegl.py`, ikke `core/predictions.py`.** En
fil uten `konfidens` kjører fint gjennom den ukentlige jobben og blir
evaluert som før. Den kan bare ikke forsegles. Skillet er bevisst — en
manglende konfidens skal ikke felle innsamlingen, og CLAUDE.md regel 1
sier at kontrakten i `core/` ikke utvides for å få til noe i et lag over.

`utfall`-NØKKELEN må finnes fra dag én, tom. Mangler nøkkelen helt, kan et
utfall legges til senere uten at noen ser at det kom til. Feltet er sin
egen kvittering — samme grunn som at `utvalg` skiller «ukjent» fra «ingen
filtrering» i stedet for å utelate feltet (CLAUDE.md 1b-3).

### Gamle anslag fylles ikke inn retroaktivt

`FORMAT_FRA = 2026-09-03`. De tre anslagene i `2026-08-18.yml` er skrevet
før feltene fantes, og de får dem ikke nå. De merkes `førformat` i seglet
og teller ikke i kalibreringen.

Dette er CLAUDE.md 1b-7 anvendt uendret: gamle snapshots har ikke
`published_at`, og de fylles ikke inn i ettertid, fordi 103
biomasse-snapshots da ville PÅSTÅTT en utgivelsesdato ingen har gått god
for. Samme her. En `konfidens` satt 03.09 på et anslag fra 18.08 ville
vært satt etter at to av tre vinduer alt hadde begynt å bevege seg, og en
kalibreringskurve bygget på et slikt tall måler ingenting.

Prisen er at de tre første anslagene ikke kan telle med. Den prisen er
riktig av en annen grunn også: beslutningen fra 18.08 sier selv at de er
utledet av Claude fra offentlige vedtak, ikke av en bransjevurdering, og
at de derfor ikke måler det loggen finnes for å måle.

### Malen heter `.yaml`, ikke `.yml`

`core.predictions.last()` leser `predictions/*.yml`. Het malen `.yml`,
ville kjørejobben lest den som et ekte anslag og treffraten inneholdt en
mal. Endelsen er det som holder den utenfor, og både malen og `forsegl.py`
sier det høyt — en fallgruve som bare er unngått, blir gått i neste gang.

---

## Regelen som er myket opp, og hvorfor det ikke er regel 2

Fram til i dag sto det i `predictions/README.md`: «Filen røres aldri etter
at den er committet.» Den regelen gjelder ikke lenger for utfallsfeltene.

**CLAUDE.md regel 2 er ikke berørt.** Den er uttømmende om hva den dekker
— `data/raw/<kilde>/<dato>.parquet`, `data/changelog/<dato>.parquet` og
`data/arkiv/` — og `predictions/` står ikke der. Begrunnelsen bak regel 2
er heller ikke til stede her: den handler om at git vokser kvadratisk når
en fil skrives om hver uke. En prediksjonsfil får ett utfall skrevet inn
én gang, ikke ukentlig.

Oppmykningen er likevel et brudd med den strengere regelen mappa hadde
selv, og den hviler helt på kjernehashen. **Uten den ville dette vært en
ren svekkelse:** «fila kan endres etter commit» uten et mål på hva som
ikke ble endret er bare tillit med flere ord.

`[din vurdering]` — om oppmykningen er verdt det, eller om utfallet heller
burde ligget i en separat, egen-forseglet fil. Argumentet for det siste er
at det bevarer den gamle regelen uendret. Argumentet mot er at krav (c)
handler om at bommen skal stå DER treffet står, og et utfall i en annen
fil er lettere å la være å skrive.

---

## Hva som ble målt

Kjørt mot filene på disk 03.09.2026, ikke resonnert fram:

**Egenskapstest av de to hashene** — fire tilfeller, alle som ventet:

| Endring | `kjernehash` | Forventet |
|---|---|---|
| utfall + utfall_dato + note ført inn | uendret | uendret (krav c uten å bryte b) |
| `terskel_prosent` 10 → 3 | endret | endret (påstand strammet inn) |
| `grunnlag` omskrevet | endret | endret |
| nøkkelrekkefølge stokket om | uendret | uendret (format er ikke innhold) |

**`filhash` mot uavhengig verktøy:** `shasum -a 256
predictions/2026-08-18.yml` gir
`1816cc9e0801fa101265d39e181d7369006681fa14bb95c6a5e2b69b0ff73674`, som er
det `SEGL.txt` oppgir. En skeptiker trenger ikke `forsegl.py` for det
leddet.

**`--sjekk` i sandkasse**, mot en kopi av mappa, tre tilfeller:

    uendret fil            -> 0   «Seglet stemmer»
    påstand omskrevet      -> 2   «SEGLET ER BRUTT: en kjernehash har endret seg»
    utfall ført inn        -> 2   «utdatert, men ingen påstand er endret»

De to siste har samme exit-kode og ulik tekst med vilje: begge krever at
et menneske ser på det, men bare det ene er juks.

**Testsuiten:** 632 tester grønne etter endringen. `forsegl.py` legger
ingenting til i `core/` og endrer ingen eksisterende fil.

**Seglet som ble skrevet:** 3 anslag i 1 fil, rot
`f2361f46a1314fb2338feeefc71cd4a8df2e817c39b2800cec78c05dcc940d7e`.

---

## Hva dette IKKE løser

Verdt å si eksplisitt, fordi et halvt bevis som presenteres som et helt er
verre enn ingen:

- **Ankeret finnes ikke ennå.** Tabellen i `predictions/README.md` er tom.
  Inntil en rad står der, er hele oppsettet en beskrivelse av hva som
  *ville* holdt. Verktøyet er laget; ankeret er ikke satt, og et segl som
  bare ligger i repoet er skrevet av den det skal binde.
- **Seglet binder de filene som finnes, ikke de som ikke gjør det.**
  Ingenting hindrer at ti anslag ble skrevet og tre forseglet. Det er
  skrevet inn i README-en under «Hva du IKKE kan verifisere», fordi en
  skeptiker vil finne det uansett og det er bedre å ha sagt det først.
- **En signert tag binder identitet, ikke tid.** Den kan lages når som
  helst med hvilken som helst dato i meldingen. Kommandoen er dokumentert;
  taggene er ikke laget.
- **Ærligheten i `grunnlag` kan ingen hash bevise.** At det ikke er endret
  etterpå, er verifiserbart. At det ble skrevet ærlig i utgangspunktet,
  er det ikke.

`[din vurdering]` — om hvilket anker som velges. OpenTimestamps krever
ingen tillit til noen tredjepart, men gir et bevis som er vanskeligere å
forklare til en leser. En offentlig, tidsstemplet publisering er lettere å
kontrollere for et menneske, men hviler på en plattform som kan slettes.

---

## Prisen

Et steg til i arbeidsflyten, og det er et steg som må gjøres for hånd:
forankringen kan ikke automatiseres uten at automatikken selv blir noe
som må stoles på. Kjørejobben er urørt, så prisen faller ikke på
innsamlingen — men et anslag som skrives uten at rot-tallet forankres, er
et anslag som ikke er bevist, og ingenting i systemet vil si fra.

`[din vurdering]` — om det skal legges til en påminnelse i tilsynet, eller
om et uforankret segl skal få stå som en kjent, akseptert mangel.

---

## Ville snudd det

- At forankringen viser seg for tungvint til å bli gjort, slik at seglet
  står uforankret i måneder. Da er dette dokumentasjon av et bevis som
  ikke føres, og en tom ankertabell er verre enn ingen tabell: den ser ut
  som et løfte.
- At kjernehashen brytes av rutinemessige, uskyldige endringer jeg ikke
  har forutsett. Da er kanoniseringen for stram, og feltmengden i kjernen
  må snevres inn — men hvert felt som flyttes ut, er ett felt som kan
  endres i ettertid uten at det synes.
- At `utfall`-feltet i praksis ikke blir fylt ut. Da er krav (c) ikke
  oppfylt uansett hva formatet krever, og utfallet bør leses direkte fra
  `data/prediksjoner/` i stedet — som er append-only og ikke kan
  redigeres selektivt.
