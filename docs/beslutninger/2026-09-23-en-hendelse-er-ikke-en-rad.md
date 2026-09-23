---
dato: 2026-09-23
tittel: En hendelse er ikke en rad — uke 39 var 812 og er 440
status: utkast
commit: [fylles inn]
---

# En hendelse er ikke en rad

**UTKAST.** Hva som ble bestemt står under, med målingene.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

Endringssiden for uke 39 viste **812 endringer**. Tallet er feil på tre
forskjellige måter, og alle tre har samme form som feilene i CLAUDE.md
1b: et mål som LIGNER det spørsmålet man vil ha svar på.

Etter dette viser uke 39 **440 endringer** og 453 rader. Forskjellen på
de to tallene står på siden.

## Målingen, før noe ble endret

    slag                    rader   kilde
    Selskapsopplysning        402   enhetsregisteret
    Trafikklys                362   akvakultur
    Ute av registeret          31   enhetsregisteret 29, eierskap 2
    Ny i registeret             7   enhetsregisteret
    Tillatelse                  6   akvakultur 4, eierskap 2
    Lokalitetsopplysning        4   akvakultur
                              ---
                              812

De tre største er 795 av de 812.

## Bestemt 1: en områdebeslutning er ÉN hendelse, ikke 362

**Reell endring i kilden, feil telling hos oss.**

`akvakultur.prodomraade_status` ga 362 rader den 21.09. Alle 362 er
ekte: verdifordelingen i snapshotene flyttet seg fra
`{GUL 381, GRØNN 318, RØD 270}` den 14.09 til
`{GUL 743, RØD 133, GRØNN 93}` den 21.09.

Men de er **fire** hendelser:

    PO  4   RØD   -> GUL   137 lokaliteter
    PO  9   GRØNN -> GUL   109
    PO 10   GRØNN -> GUL    72
    PO 11   GRØNN -> GUL    44

Hver lokalitet i hvert område fikk samme nye verdi samme dag, fordi
fargen ikke er en egenskap ved lokaliteten. Den er en egenskap ved
OMRÅDET, ført på hver lokalitet av registeret.

Det er nøyaktig samme form som `ny`/`borte`, der `diff.compare()`
skriver én rad per felt for én oppføring som kom eller gikk — og som
nettstedet har slått sammen siden det ble bygget. Forskjellen er bare
hva raden deles på: entiteten der, området her.

Slås sammen på **(område, fra, til, dato)** — ikke bare på området.
To lokaliteter i samme område som gikk hver sin vei, er to vedtak.

`nettsted.SAMLES_PER_OMRAADE`. Hendelsen gjelder området, ikke den
lokaliteten som tilfeldigvis var første rad i gruppa, og den bærer
`omfang` = antall lokaliteter. Forsiden sier begge tall: fire områder,
ført på 362 lokaliteter.

## Bestemt 2: «Ute av registeret» var usant for 20 av 22

**Artefakt, og en side som var faktisk usann.**

Luka vår inn i Enhetsregisteret ER et næringskodesøk. En oppføring som
går ut av søket, går ikke nødvendigvis ut av registeret.

MÅLT 23.09.2026: alle 29 selskapene uke 39 kalte «Ute av registeret»
ble slått opp i Brønnøysunds åpne API.

    ute av UTVALGET (ny næringskode, står i registeret)   20
    faktisk slettet fra Enhetsregisteret                   2
    feltnivå, entiteten sto der hele tiden                 7   (se punkt 3)

De 20 hadde byttet til 68.200 eiendom, 55.100 hotell, 10.410 fôr,
46.900 engroshandel, 41.000 bygg, 74.110 juridisk … Alle sto i
registeret, ingen var slettet, ingen var konkurs.

Samme vei inn: alle 32 «Ny i registeret»-entitetene ble slått opp.
**Null av dem var registrert i september 2026.** Eldste var fra
1995-02-20. Alle var nye bare for OSS.

Etiketten er derfor **«Ute av vårt utvalg»** og **«Ny i vårt utvalg»**,
og forklaringen sier hvorfor: «Den kan være slettet fra registeret,
eller ha fått en næringskode utenfor søket vårt — vi kan ikke se
hvilket.»

Vi kunne slått opp mot Brønnøysund ved bygging og skrevet «slettet» der
det er sant. Det gjøres ikke: det ville vært et tredjepartsoppslag gjort
i dag om en påstand datert i fjor, og det er det motsatte av 1b-7.
Det svakeste sanne utsagnet er det eneste vi har.

## Bestemt 3: et FELT som kom er ikke en ny oppføring

**Artefakt.** `diff.compare()` skriver `ny`/`borte` per (entitet, felt),
og det er sant på feltnivå. Nettstedet samlet radene per entitet og
kalte resultatet «Ny i registeret».

MÅLT uke 39, mot snapshotene 14.09 og 21.09:

    «ny»     7 entiteter — 0 nye. Alle sju sto i BEGGE snapshots.
             Seks fikk `antall_ansatte` for første gang, én
             `mva_registreringsdato`.
    «borte»  29 entiteter — 22 faktisk borte. De sju andre sto i begge
             og mistet bare `antall_ansatte`.

`changelog.merk_feltbevegelse()` spør snapshotene om entiteten finnes på
BEGGE sider, og merker `felt_ny`/`felt_borte`. Prøven er den 1b-2 krever:
ikke «hvor mange felt hadde raden» — det er en stedfortreder som er
riktig helt til en oppføring kommer inn med ett felt — men om entiteten
står der.

**Vises**, med egen etikett: «Felt oppgitt første gang» og «Felt ikke
lenger oppgitt». **Telles ikke.** At et selskap begynner å oppgi antall
ansatte er en opplysning om rapporteringen, ikke en hendelse i
havbruket. Radene står i tabellen, i CSV-en og i feeden; tallet over
tabellen sier 440 og en note sier at 13 rader til står uten å telle.

Samme asymmetri som `utvalgsutvidelse` i 1b-3: merket og beholdt, ikke
summert.

## Bestemt 4: changeloggen får en lesedør

**Ikke et telleproblem — en publiseringsblokker.**

18.09-beslutningen lot 381 changelog-rader med persondata ligge, og
skrev ned hva som ville snudd valget:

> En visning uten `entity_id`-filter — en oversiktsside, et søk, en
> «endringer denne uka» på tvers av kilder, eller en CSV av loggen ved
> siden av sidene — fjerner vilkår 1 og 3 samtidig. … det skal avgjøres
> FØR visningen skrives, ikke etterpå.

Designrunden bygget nøyaktig det. MÅLT 23.09.2026 nådde én rad om en
personform uke 39s side — et DA, som «Ny i vårt utvalg». Den hadde
ingen navn på siden bare fordi entiteten var ute av snapshotet og
oppslaget falt til en nøytral etikett. Det er ikke en beskyttelse; det
er en fjerde tilfeldighet.

`changelog.les_alt()` går fra i dag gjennom
`changelog.fjern_personformer()`, som spør `snapshot.personentiteter()`
— **krysspeilingen**, som 18.09-notatet målte til å ta alle 19 der
loggens egne felt bare tar 16. MÅLT: 380 rader, 20 entiteter, fjernes
ved lesing. Filene røres ikke.

## Hva som IKKE ble endret

**De 402 selskapsopplysningene, hvorav 369 `antall_ansatte`.** De er
reelle: verdi til verdi, median ±2, største sprang 87, og bare 7 av 386
var første observasjon. At de alle kommer samme dag er én månedlig
oppdatering fra Brønnøysund, men tallene er 369 forskjellige fakta —
ikke ett vedtak skrevet 369 ganger. De telles.

`diff.compare()` skriver fortsatt `ny`/`borte` per felt. Merkingen skjer
ved LESING, som `merk_utvalgsutvidelse()` og `merk_taushet()`, fordi
changeloggen er append-only og de skrevne radene ikke kan rettes.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
