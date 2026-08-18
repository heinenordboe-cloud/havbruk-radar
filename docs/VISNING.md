# Intern visning — spesifikasjon

Skrevet som oppdrag til Claude Code. Ikke kode her, men nok til at
implementasjonen ikke trenger å gjette.

## Hvorfor den finnes

Ikke for å se pen ut. For å gjøre dataene tenkbare.

Tre ting står stille uten den:

**Prediksjoner.** Du kan ikke skrive et anslag om et felt du aldri har
sett. Blank side er ikke manglende bransjekunnskap — det er manglende
utsyn.

**Mønsterregler.** Domenekunnskap kan ikke kodes inn i data du ikke har
sett bevege seg. Reglene i `rules/signals.yml` er generiske nettopp
fordi de ble skrevet før noen så på tallene.

**Blindsonen.** `signals.py` kaster i dag hver endring ingen regel
treffer. Du vet ikke hva du ikke ser, og det kan du ikke rette uten å
telle det.

Dette er **ikke** dashbordet. Beslutningen fra 16.08 om å utsette
nettsiden står. Den utstilte siden skal forklare seg selv for
utenforstående; denne skal være tett, stygg og fullstendig. Blir de
samme ting, er begge dårlige.

## Hvor den skrives, og hvorfor ikke i git

`vis.py` i reporoten leser fra `HAVBRUK_DATA_DIR` og skriver
`oversikt.html` dit, **gitignorert**, og skriver stien til stdout.

Den committes ikke. En generert HTML-fil som skrives om hver uke er
nøyaktig mønsteret beslutningen fra 16.08 forbød for changeloggen: git
lagrer en ny nesten-full kopi hver gang, og repoet vokser kvadratisk.
Visningen er en ren funksjon av snapshots og changelog — begge
append-only — så den kan alltid regenereres og skal derfor aldri lagres.

Kjøres på kommando, ikke i den ukentlige jobben. Innsamlingen skal ikke
kunne felles av et lesevektøy.

## Fem visninger

### 1. Oversikt

Én skjerm som svarer «lever det, og hvor stort er det»: kilder med siste
hentedato og dager siden, antall entiteter, felter og observasjoner per
kilde, helsetilstand fra `health.json`, og antall åpne prediksjoner.

### 2. Felter — den viktigste akkurat nå

Per kilde, én rad per felt:

- hvor mange entiteter har feltet utfylt (dekning)
- antall distinkte verdier
- tre eksempelverdier
- hvor mange ganger feltet har endret seg siden innsamlingen startet
- numerisk eller ikke

**Dette er visningen som gjør «ingen peiling» til en liste.** Et felt som
aldri endrer seg er verdiløst å spå om. Et felt med tre distinkte verdier
er en `verdi`-prediksjon. Et numerisk felt med spredning er en
`endring`-prediksjon. Lav dekning betyr at anslag om det feltet ofte vil
ende som `kan_ikke_avgjores`.

Sorter fallende på antall endringer. Toppen av den lista er der det er
noe å mene noe om.

### 3. Endringer

Hele changeloggen, ikke bare de scorede. Hver rad: dato, kilde, entitet,
felt, fra, til, og signal + vekt hvis en regel traff.

**Uklassifiserte endringer skal være synlige og telles øverst**, ikke
gjemmes bak et filter. Tallet «412 endringer, 38 scoret, 374
uklassifiserte» er den ærlige målingen av blindsonen. Grupper de
uklassifiserte på felt — det peker rett på hvilke regler som mangler.

Filtre: kilde, felt, dato, scoret/uscoret. Fritekstsøk på entitetsnavn.

### 4. Entitet

Søk opp én lokalitet eller ett selskap. Vis alle felter med gjeldende
verdi, og for hvert felt hele verdiforløpet med dato.

Dette er skjermen du står på når du bestemmer deg for om du tror noe
kommer til å skje med akkurat den lokaliteten. Den skal kunne åpnes
direkte fra en rad i visning 3.

### 5. Prediksjoner

Åpne anslag med vindu og hvor lenge det er igjen, og avgjorte anslag med
utfall og begrunnelse. Andel `kan_ikke_avgjores` skal vises for seg — er
den høy, svikter formatet eller kildedekningen, ikke dømmekraften.

## Hva den ikke skal gjøre

**Ikke skrive noe.** Rent lesevektøy. Ingen filskriving utenom
`oversikt.html`.

**Ikke finne på tall.** Viser bare det pipelinen allerede har utledet.
Er et aggregat interessant nok til å vises, hører det hjemme i
pipelinen, ikke i en visning som ingen andre kan se regnestykket bak.

**Ingen grafer i v1.** Tabeller med tall er raskere å lese og lyver
mindre. Om noe skal tegnes senere, er det sparklines i feltvisningen —
ikke før du vet hva du ser etter.

**Ingen CDN, ingen npm, ingen server.** Én selvstendig HTML-fil med
CSS og JS inline. Avhengigheter som hentes fra nett råtner over to år,
og det er samme argument som pinningen av `requirements.txt`.

## Teknisk form

Python i `vis.py`, polars til å lese parquet, en HTML-streng ut.
Data legges inn som JSON i en `<script>`-tagg; filtrering og søk skjer
i vanilla JS i nettleseren, ikke ved regenerering.

**Navngitt feilmodus:** hele datasettet inline slutter å virke når det
blir stort nok. I dag er det rundt 27 000 observasjoner per kjøring, og
det går fint. Med to års historikk er det millioner. Grensa går et sted
rundt 20–50 MB HTML, og når den nås er svaret å legge per-entitet-detalj
i egne JSON-filer ved siden av, ikke å slutte å vise ting. Skriv
filstørrelsen til stdout ved hver kjøring, så merkes det før det blir et
problem.

## Akseptansetest

Regel 6 gjelder: den er ikke verifisert før tallene er sett.

Kjør `run.py`, noter antall observasjoner per kilde og antall endringer
fra utskriften. Kjør `vis.py` og sammenlign med oversikten. Spriker de,
leser visningen feil — og en visning som viser feil tall er verre enn
ingen visning, fordi den blir trodd.

Sjekk i tillegg at summen scoret + uklassifisert er lik totalt antall
endringer. Det er den ene summen som ikke kan stemme ved et sammentreff.

## Rekkefølge

1. Visning 2 (felter) alene. Den er halve verdien og kan bygges på en kveld.
2. Visning 1 og 3.
3. Visning 4.
4. Visning 5 — kan vente til det finnes prediksjoner å vise.

## Hva som ville snudd det

At visningen blir noe du pynter på i stedet for noe du leser. Da er den
blitt dashbordet før tiden, og dashbordet skal vente til historikken
finnes. Kjennetegnet er at du bruker en kveld på utseende uten å ha
skrevet en regel eller et anslag etterpå.
