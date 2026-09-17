---
dato: 2026-09-16
tittel: URL-struktur og ankere — registerets ID som slug, aldri navnet
status: besluttet
commit: [fylles inn]
---

# URL-struktur og ankere

**Bestemt:** Den publiserte nettsiden bruker fire toppnivå-navnerom, med
registerets egen ID som slug og konsekvent avsluttende skråstrek:

    /lokalitet/<lokalitetsnummer>/      31397   Fiskeridirektoratets siteNr
    /produksjonsomrade/<nr>/            10      forskriftens PO-nummer
    /selskap/<orgnr>/                   928957489   Brregs organisasjonsnummer
    /om/                                kilder, lisenser, metode

Tabeller får stabile ankere på formen `#<kilde>-<hva>`, utledet av
kildenavnet og feltvokabularet — aldri av posisjon, nummerering eller
overskriftstekst.

**Hvorfor dette skrives før koden:** en URL er det eneste i en
publisering som ikke kan gjøres om. Design, tekst, tabeller og farger kan
skrives om når som helst. Den dagen noen siterer
`/lokalitet/31397/#lusetall-uke` i en artikkel, i en sak hos
Mattilsynet eller i et innlegg, er den strengen et løfte. Alt annet i
denne oppgaven er reverserbart; dette er det ikke.

---

## 1. Hvorfor ID og aldri navn

`OTERNESET` er et navn. `31397` er en identitet.

Navn endrer seg, og vi har målt at de gjør det: `enhetsregisteret` lagrer
`historiske_navn_antall` nettopp fordi Brreg fører dem, og
`akvakultur`-feltet `navn` er et felt som kan komme i en changelog-rad
som en hvilken som helst annen verdi. En URL bygget på navnet ville
brutt den uka lokaliteten skiftet navn, og den ville brutt STILLE — den
gamle adressen finnes ikke lenger, og ingen får vite hvorfor.

Verre: navn er ikke unike. To lokaliteter kan hete det samme i hver sin
kommune, og da må slug'en disambiguere med et tillegg (`-2`, kommunenavn,
fylke) som i seg selv er en sekvens eller et navn til. Da er man tilbake
til å ha bygget identiteten sin på noe som kan endres.

Valget er ikke nytt i dette repoet. `sources/akvakultur.py` valgte
allerede `siteNr` framfor `siteId` som `entity_id`, med denne
begrunnelsen:

> `siteId` er en intern nøkkel, og registeret har i tillegg `versionId`
> som endres ved hver versjonering — begge er dårlige ankere for en
> historikk som skal leses av mennesker.

URL-en arver den beslutningen i stedet for å ta en ny. Følgen er verdt å
merke seg: **slug'en i URL-en er den samme strengen som `entity_id` i
changeloggen.** En changelog-rad og en nettadresse peker på samme ting
uten en oversettelsestabell mellom seg, og en oversettelsestabell er et
sted der to sannheter kan skille lag.

### Tre ID-er, tre eiere — og alle tre er tredjeparts

| segment | ID | hvem eier den | hvorfor den er trygg |
|---|---|---|---|
| `/lokalitet/` | `siteNr` | Fiskeridirektoratet | Nummeret næringa selv bruker. Det er trykt i vedtak og brukt i Mattilsynets lusetall — slås opp av folk som ikke har vært på nettsiden vår. |
| `/selskap/` | organisasjonsnummer | Brønnøysundregistrene | Ni siffer, tildelt én gang, aldri gjenbrukt. Følger selskapet gjennom navneskifter og fusjon. |
| `/produksjonsomrade/` | PO-nummer 1–13 | Nærings- og fiskeridepartementet | Fastsatt i forskrift. Se punkt 4 for hvorfor denne er den svakeste av de tre. |

Ingen av dem er vår. Det er poenget: en ID vi fant på selv, ville vi
kunne endre selv.

## 2. Hvorfor trailing slash, konsekvent

`/lokalitet/31397/` og ikke `/lokalitet/31397`.

1. **Det er ett valg, ikke to.** Uten en regel oppstår begge formene, og
   da har hver side to adresser. To adresser er delt lenkeverdi, to
   oppføringer i en søkeindeks, og to strenger som må sammenlignes hver
   gang noen spør «er dette samme side».
2. **Relative lenker oppfører seg forutsigbart.** Fra
   `/lokalitet/31397/` peker `../` på `/lokalitet/`. Fra
   `/lokalitet/31397` peker `../` på roten. Den forskjellen er en
   feilkilde hver gang noen skriver en relativ lenke, og den viser seg
   først i nettleseren.
3. **Den er sann om filsystemet.** Siden ligger som
   `lokalitet/31397/index.html`. En sti som ender på skråstrek sier at
   dette er en mappe, og det er nøyaktig hva den er. Enhver statisk vert
   — GitHub Pages, Netlify, `python -m http.server`, en nginx med
   `try_files` — serverer den uten konfigurasjon.

Konsekvensen tas med: en vert som ikke redirigerer `/lokalitet/31397` til
`/lokalitet/31397/` gir 404 på den formen. Det er en akseptert kostnad,
og den er billigere enn to kanoniske adresser.

## 3. Hva som IKKE er med, og hvorfor

**Ingen dato i stien.** `/2026/09/lokalitet/31397/` ville datert en side
som handler om et pågående forhold. Lokaliteten er den samme i oktober;
det er innholdet som er nytt. En dato i URL-en ville tvunget fram en ny
adresse hver uke, og da er ingen av dem verdt å sitere.

Dette er ikke det samme som at dataene er udaterte — tvert imot. Hver
verdi på siden bærer sin egen dato i markupen (`<time datetime>`), og
siden sier hvilket snapshot den er bygget fra. **Datoen hører til
verdien, ikke til adressen.** Det er samme skille som CLAUDE.md 1b-7 gjør
mellom `observed_at`, `fetched_at` og `published_at`: et tidspunkt er en
egenskap ved en påstand, ikke ved stedet påstanden står.

**Ingen query-parametre.** `?lokalitet=31397` gjør identiteten til et
argument. Da kan den samme siden nås som `?lokalitet=31397&utm_source=…`
og som `?utm_source=…&lokalitet=31397`, og det er igjen to adresser for
én side. En statisk side har heller ingenting å gjøre med en parameter:
det finnes ingen kode som leser den.

**Ingen sekvensielle indekser.** `/lokalitet/1/`, `/lokalitet/2/` ville
vært vår egen nummerering, og vår egen nummerering er den ene tingen vi
kan komme til å endre — ved en re-generering, en sortering, en ny kilde.
Den ville dessuten skjult identiteten: nummeret hadde ikke betydd noe
utenfor vår egen nettside.

**Ingen navn som tillegg.** `/lokalitet/31397-oterneset/` ser hjelpsomt
ut og er en felle: den innfører navnet i adressen bakveien. Skifter
lokaliteten navn, står valget mellom å bryte lenken eller å la adressen
lyve. Begge er dårligere enn å ikke ha navnet der.

**Ingen filendelse.** `/lokalitet/31397.html` binder adressen til
formatet. Skal siden en dag serveres som noe annet, er endelsen en løgn
som ikke lar seg rette uten å bryte lenken.

## 4. `/produksjonsomrade/` er det svakeste leddet, og det er målt

De tre ID-ene er ikke like solide, og det skal stå her framfor å oppdages
senere.

`siteNr` og organisasjonsnummer er REGISTERNØKLER: de identifiserer en
ting, og tingen fortsetter å eksistere. PO-nummeret er en REGULATORISK
INNDELING: det identifiserer en beslutning om hvordan kysten deles opp,
og en slik beslutning kan tas om igjen.

Og den er foreslått tatt om igjen. `analyse/reguleringsomraader.py`
målte 09.09.2026 alle 1 779 lokaliteter mot Havforskningsinstituttets
**28 foreslåtte reguleringsområder** (1A, 1B, 2A … 13B). De dekker
kysten finere enn dagens 13, og ingen lokalitet med `prodomraade_kode`
faller utenfor dem.

**Hva som skjer hvis de 28 trer i kraft:** ingenting med denne URL-en.
De 28 får sitt EGET navnerom, `/reguleringsomrade/<kode>/`, og
`/produksjonsomrade/10/` fortsetter å bety produksjonsområde 10 slik
forskriften definerte det.

Regelen bak er den som gjør resten av strukturen holdbar: **en sti
gjenbrukes aldri til en annen betydning.** Å la `/produksjonsomrade/10/`
peke på reguleringsområde 10A en dag ville gjort hver eksisterende lenke
til en usann påstand — og det ville vært usynlig, siden siden fortsatt
svarer 200. Et nytt begrep får en ny sti. Det koster en mappe.

## 5. Ankere

Hver tabell har en `id` som kan lenkes til:
`/lokalitet/31397/#lusetall-uke`.

### Navngivingsregelen

    #<kilde>-<hva>

- **`<kilde>`** er kildenavnet slik det står i `data/raw/<kilde>/` og i
  changeloggens `source`-kolonne: `akvakultur`, `lusetall`, `eierskap`,
  `eierskap_historikk`, `enhetsregisteret`. Det er allerede en kontrakt —
  det er navnet på en mappe med append-only filer, og en kilde som bytter
  navn er en mye større sak enn et anker.
- **`<hva>`** er hva tabellen viser, uttrykt i feltvokabularet kilden
  allerede har: `uke` for radene lusetall leverer per uke, `tillatelser`
  for tillatelsesradene i eierskap, `overforinger` for
  overføringshistorikken, `register` for registerfeltene.

Ankerne på lokalitetssiden blir da:

    #akvakultur-register        registerfeltene om lokaliteten
    #eierskap-tillatelser       hvem eier hvilken tillatelse nå
    #eierskap_historikk-overforinger    journalførte overføringer
    #lusetall-uke               voksne hunnlus per uke
    #endringer-register         changeloggen for lokaliteten

### Hva regelen forbyr, og hvorfor akkurat det

**Ikke posisjon.** `#tabell-3` er ugyldig fra den dagen noen setter inn
en tabell foran den. Det er samme feilform som en sekvensiell indeks i
stien, og den er verre her: `#tabell-3` fortsetter å FUNGERE, den peker
bare på noe annet. En lenke som går til feil sted er verre enn en lenke
som er død, fordi ingen får vite det.

**Ikke overskriftstekst.** `#hva-har-lusetallene-vaert` er den vanlige
løsningen (Markdown-verktøy gjør dette automatisk), og den binder
adressen til en formulering. Hver språkvask flytter ankeret. Overskrifter
er design; ankere er ikke.

**Ikke æøå.** `#produksjonsområde` er lovlig i en URL, men blir
`%C3%A5`-kodet når det kopieres, og den strengen overlever ikke å bli
limt inn i en e-post og ut igjen. ASCII, små bokstaver, bindestrek.

**Ikke entitets-ID-en.** `#lokalitet-31397-lusetall` er redundant: siden
ER lokaliteten. Redundansen ville dessuten betydd at det samme ankeret
het noe forskjellig på hver side, og da kan man ikke lære det.

### Hvorfor dette er stabilt når nye seksjoner kommer til

Fordi ankeret er en FUNKSJON AV INNHOLDET, ikke av rekkefølgen. En ny
tabell over rømmingshendelser blir `#romming-hendelser` uansett hvor på
siden den plasseres, og den flytter ikke på noe eksisterende. To tabeller
kan ikke kollidere uten at de viser det samme fra samme kilde — og da er
det tabellene som er feil, ikke navngivingen.

Underskrift-nivået er ikke adressert her med vilje: ankere gis bare til
TABELLER i denne runden, fordi det er tabellene som bærer tall noen vil
sitere.

## 6. Hva URL-rommet genereres FRA — og hvorfor det er en personvernsak

Sidene genereres av snapshotene, lest gjennom `snapshot._les()`. Det er
den ene døra som kjører `persondata.fjern_personformer()`, og følgen er
ikke bare teknisk:

**Et foretak i SSB-sektor 8200 eller 2300 får aldri en URL.** Ikke fordi
generatoren husker å hoppe over det, men fordi entiteten ikke finnes i
ramma generatoren leser fra. En `/selskap/<orgnr>/`-side for et
enkeltpersonforetak kan ikke oppstå ved en forglemmelse — den ville
krevd at noen bygget en lesevei utenom døra, og
`test_ingen_leser_snapshots_utenom_les()` feller det.

Det er verdt å skrive ned her fordi URL-rommet er den ene tingen som
lekker uten å vise innhold: en katalog over adresser er en liste over
hvem som finnes, selv om hver side skulle være tom. Se
`docs/beslutninger/2026-09-16-grensa-gaar-ved-sektor-2300.md`.

## 7. Det som ikke er bestemt her

- **Indekssider.** `/lokalitet/` uten nummer — liste, søk, kart? Ikke
  avgjort. Navnerommet er reservert av strukturen, og innholdet er et
  designspørsmål.
- **Språk.** Ingen `/no/`-prefiks nå. Kommer engelsk senere, er det
  `/en/` som legges til og norsk som blir stående på roten — ellers
  flyttes hver eksisterende side.
- **Paginering av lange serier.** Lusetallserien for OTERNESET er 764
  uker. Hvordan den deles opp er et designspørsmål, men det er ikke et
  URL-spørsmål før noen vil lenke til en bit av den. Skjer det, er svaret
  en anker-fragment eller `/lokalitet/31397/lusetall/` — en UTVIDELSE av
  strukturen, ikke en endring av den.

## Ville snudd det

- **At `siteNr` gjenbrukes.** Hele valget hviler på at nummeret peker på
  én lokalitet for alltid. Viser det seg at Fiskeridirektoratet tildeler
  et nedlagt anleggs nummer på nytt, er nummeret ikke en identitet, og
  da må URL-en bære noe mer — en periode eller en versjon. Dette er
  ikke etterprøvd mot registeret; det er en antakelse, og den står her
  som en antakelse. Prøven er billig: to lokaliteter med samme `siteNr`
  og ulik `forste_klarering` i historikken vår ville vist det.
- **At sidene må serveres av noe annet enn en statisk vert.** Trailing
  slash og mappestruktur er valgt for statiske filer. Skulle siden en
  dag kjøre bak en applikasjonsserver med ruting, er `/lokalitet/31397`
  uten skråstrek det mer naturlige — men da er byttet en redirect, ikke
  en omlegging.
- **At produksjonsområdene avvikles helt.** Erstattes de av de 28 uten å
  bestå ved siden av, blir `/produksjonsomrade/<nr>/` et historisk
  navnerom. Da skal det bli stående og si at det er historisk — ikke
  fjernes, og ikke gjenbrukes.

**Ville IKKE snudd det:** at en navneslug ville sett penere ut i en
lenkeforhåndsvisning. Det er et designargument mot en
holdbarhetsbeslutning, og siden er tom for design i denne runden nettopp
for at de to ikke skal blandes.
