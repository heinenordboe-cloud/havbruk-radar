# Lansering: hva som må være sant før første publisering

Sjekkliste med status. Skrevet 23.09.2026. **Ingenting er publisert.**

Hosting og domene er IKKE valgt, og det er med vilje: tallene under er
grunnlaget for det valget.

---

## Målingen

### Publiseringsmappa

MÅLT 23.09.2026, bygget fra 6 ukentlige øyeblikksbilder:

    9 005 filer     269,5 MB logisk (277 MB på disk)

    .html            2 348 filer    176,9 MB
    .csv             1 787 filer     71,5 MB
    .xml (Atom)      2 278 filer      2,8 MB
    .pf_fragment     2 348 filer      8,5 MB   søkeindeks
    .pf_index          217 filer      7,5 MB   søkeindeks
    .jpg                 3 filer      1,3 MB   herofoto
    .woff2               3 filer      0,1 MB   fontene
    resten              21 filer      1,9 MB

Per katalog: `lokalitet/` 236 MB, `pagefind/` 21 MB, `selskap/` 13 MB,
`endringer/` 3,6 MB, `produksjonsomrade/` 1,8 MB.

**Største filer:**

| fil | kB |
|---|---:|
| `bilde/hero-2400.jpg` | 800 |
| `lokalitet/index.html` | 595 |
| `endringer/2026-38/index.html` | 483 |
| `endringer/2026-38/biomasse/index.html` | 380 |
| `bilde/hero-1600.jpg` | 367 |
| `endringer/2026-39/selskap/index.html` | 263 |
| `endringer/2026-39/index.html` | 262 |
| `selskap/921668236/index.html` | 241 |

### Vekst per uke

MÅLT ved å bygge nettstedet på nytt med changeloggen avkortet — samme
generator, samme maler, bare færre uker. Ikke et anslag.

    4 uker    6 405 filer    247,9 MB
    5 uker    6 405 filer    248,3 MB    +0 filer, +0,34 MB
    6 uker    6 420 filer    249,6 MB    +15 filer, +1,30 MB

**Vekst: 0,3–1,3 MB og 0–15 filer per uke.** De 15 filene er én
endringsuke: indeksside, tolv typesider, CSV og JSON. Uken som ga 0
filer er den første — den har ingen forrige å sammenligne mot.

Tallene er uten søkeindeksen (21 MB), som følger sideantallet og ikke
ukene.

**Fremskrevet:** ~50 MB i året, ~0,5 GB på ti år. Størrelsen i dag er
ikke drevet av historikken, men av at hver lokalitet har en side, en
feed og en CSV.

### Eksterne forespørsler: NULL

MÅLT ved å lese hvert attributt som utløser en forespørsel — `href` på
`<link>`, `src`, `srcset`, `@import`, `url()` i CSS — over alle 2 348
HTML-sidene, `stil.css` og begge skriptene:

    eksterne forespørsler        0
    alt annet hostes av oss      fonter, ikoner, herofoto, søkeindeks

De eneste absolutte URL-ene i utputtet er **lenker og identifikatorer**,
ikke forespørsler:

| vert | forekomster | hva |
|---|---:|---|
| `data.norge.no` | 5 138 | NLOD-lisens-URI i JSON-LD |
| `github.com` | 2 352 | lenke til kildekoden i bunnteksten |
| `schema.org` | 2 348 | `@context` i JSON-LD (hentes ikke) |
| `kystloggen.no` | 2 341 | vår egen kanoniske adresse |
| `virksomhet.brreg.no` | 481 | lenke til selskapet i Enhetsregisteret |
| `lovdata.no` | 58 | lenke til forskriften |
| `www.regjeringen.no` | 8 | lenke til kunngjøringen |

`example.com` forekommer to ganger, begge inne i Pagefinds eget
bibliotek som base for URL-parsing. Ingen forespørsel.

---

## Sjekkliste

### Personvern og proveniens

| # | krav | status |
|---|---|---|
| 1 | Ingen roller eller gateadresser hentes | **OPPFYLT** — kilden ber ikke om dem |
| 2 | Personformer filtreres i `fetch()` og `parse()` | **OPPFYLT** |
| 3 | Lesedør i `snapshot._les()` | **OPPFYLT** — 72 rader fjernes per lesing |
| 4 | `snapshot.write()` nekter personformer | **OPPFYLT** |
| 5 | Lesedør i `changelog.les_alt()` | **OPPFYLT 23.09, UTVIDET 24.09** — unionen av døra og kildens tillegg. 380 rader / 20 entiteter fjernes per lesing; de 16 utvidelsen fanget er ute av filene |
| 6 | `eier_type` i kildens egen hook | **OPPFYLT 23.09** |
| 7 | Generatoren og porten leser LIKT | **OPPFYLT 23.09** — `nettsted._siste()` kaller hooken |
| 8 | Tre personformnavn i `tildelt_navn` | **KVITTERT** — se under |
| 9 | Kodeproveniens per øyeblikksbilde | **OPPFYLT 23.09** for nye filer |
| 10 | Innsamlingen nekter å kjøre upushet | **OPPFYLT 23.09** |

**Punkt 8, i sin helhet.** Tre selskapsnavn som ender på ANS står på 14
lokalitetssider, i feltet `tildelt_navn` — den tillatelsen opprinnelig
ble tildelt, i ett tilfelle i 1995. Porten melder dem som `personform`
hver kjøring, og de er kvittert av Heine 19.09.2026.

De kan ikke lukkes med data: **`tildelt_type` finnes ikke.** Feltet er
`None` på alle fire tillatelsene, og den eneste prøven som ville
truffet er endelsen i navnet. Den brukes til å OPPDAGE i porten, der en
falsk positiv koster en kvittering. Å bruke den til å SKJULE er en annen
retning: da koster en falsk positiv en opplysning som forsvinner uten at
noen ser det.

**Kvitteringen er mekanismen, og den er avgitt.** Ingen handling
gjenstår med mindre Heine ombestemmer seg.

**Punkt 5, hva utvidelsen 24.09 la til.** Døra filtrerte på
`snapshot.personentiteter()`, og settet ble bygget av
`persondata.person_ider()` alene — altså av `organisasjonsform` og
`institusjonell_sektorkode`. Den var dermed blind for entitetene
`Source.fjern_egne_personer()` finnes for. MÅLT 24.09.2026 over hele
loggen (1 016 150 rader, ufiltrert), FØR regenereringen under:

    kilde                fjernet før    fjernet etter
    enhetsregisteret             380              380
    eierskap_historikk             0               16
    alle andre                     0                0
    SUM                          380              396

Personsettet gikk fra 106 til 111 par. De fem nye er fire
overføringsmottakere i `eierskap_historikk` og én tillatelse i
`eierskap`; den siste har ingen rader i loggen, og derfor er 16 og ikke
21 forskjellen i rader. De 16 radene er dessuten fjernet FRA FILENE —
changeloggen er avledet og overskriver sin egen dato — og MÅLT etterpå
fjerner døra 380 rader og 20 entiteter per lesing, alle
`enhetsregisteret`. De 380 blir liggende med vilje; se beslutningen
18.09. Se også
`docs/beslutninger/2026-09-24-changelogdora-leser-kildens-tillegg.md`.

**Punkt 9, grensa i historikken.** 1 833 snapshotfiler er skrevet før
23.09.2026 og har ingen kodeproveniens. De blir stående — append-only —
og telles per kilde hver kjøring. Tallet skal synke med én uke om
gangen. Det blokkerer ikke.

### Innhold

| # | krav | status |
|---|---|---|
| 11 | Alle 65 trafikklysceller har en farge | **OPPFYLT 23.09** — 65 av 65 |
| 12 | Ingen plassholder fra designet i utputtet | **OPPFYLT** — 33 mønstre, alle treff verifisert |
| 13 | Ukas tall teller bare det som skjedde | **OPPFYLT 23.09** |
| 14 | Entall og flertall | **OPPFYLT 23.09** |
| 15 | Alle sider måler 390 px uten vannrett rulling | **OPPFYLT** |
| 16 | WCAG 2.2 AA kontrast, målt | **OPPFYLT** — `tests/test_kontrast.py` |

**Punkt 11, lukket.** Alle fem fargeleggingsrundene er lest mot sidene
på regjeringen.no (PDF 23.09.2026 kl. 11.45–11.46) og lagt i
`beslutning.GODKJENT`. Ingen celle står tom.

    før:    46 av 65, 19 tomme
    etter:  65 av 65, 0 tomme

    17  grønn / utledet      17  grønn / ordrett     17  gul / beslutning
     7  rød   / ordrett       5  gul   / ordrett      2  rød / beslutning

Der begge kildene sier noe, er de enige i 46 av 46. Null sprik.

**Det som står igjen her er mindre:** den SÆRSKILTE VURDERINGEN for
2018 (PO7) og 2020 (PO2–PO5, PO7, PO10) er lagt fram ordrett i
`docs/VERIFISERING-FARGELEGGINGEN.md`, men ikke publisert —
`SAERSKILT_GODKJENT` er {2022, 2024, 2026}. Parseren finner dem heller
ikke, så publisering krever enten en utvidet parser eller en tabell
skrevet for hånd. Det avgjøres etter lesingen.

### Dokumentasjon

| # | krav | status |
|---|---|---|
| 17 | Lisens per kilde, udokumentert = UBELAGT | **OPPFYLT** — `docs/LISENSKJEDE.md` |
| 18 | Lisens for det nettstedet selv distribuerer | **OPPFYLT** — tabell 2 |
| 19 | Beslutningsnotater med «Hvorfor» | **DELVIS** — 20 står som utkast |
| 20 | Åtte åpne spørsmål er skrevet ned | **OPPFYLT** — `docs/APNE-SPORSMAL.md` |

**Punkt 19.** 20 notater har `status: utkast`, og fem av dem er fra
designrunden og de siste to dagene:

    2026-09-22-gratis-mot-betalt-grense.md
    2026-09-23-design-implementert.md
    2026-09-23-en-hendelse-er-ikke-en-rad.md
    2026-09-23-fargeleggingen-er-et-eget-belegg.md
    2026-09-23-kodeproveniens-per-snapshot.md
    2026-09-23-selskapsdata-star-for-seg.md
    2026-09-23-eier-type-inn-i-hooken.md

Alle har «Hva som ble bestemt» utfylt med målinger. Det som mangler er
«Hvorfor» og «Hva som ville snudd det», som er Heines å skrive.

**Er dette en lanseringsblokker?** Det er en vurdering, ikke en måling.
Notatene dokumenterer valg som allerede er tatt og som er synlige i
koden; et utkast uten «Hvorfor» hindrer ingen i å bruke nettstedet. Men
regelen i repoet er at et valg skal kunne etterprøves, og et notat uten
begrunnelse kan bare etterprøves på HVA, ikke på HVORFOR.

### Drift

| # | krav | status |
|---|---|---|
| 21 | Porten er blokkerende og kjøres ved hvert bygg | **OPPFYLT** |
| 22 | Ukentlig innsamling kjører | **OPPFYLT** |
| 23 | Byggetid | **MÅLT** — 39 s bygg, 85 s med port og søkeindeks |
| 24 | Hosting valgt | **IKKE GJORT** — utenfor denne runden |
| 25 | Domene | **IKKE GJORT** — utenfor denne runden |
| 26 | DOI | **IKKE GJORT** — utenfor denne runden |
| 27 | Ukesbrev | **IKKE BYGGET** — bevisst, se design-notatet |

---

## Det korte svaret

Tre ting står igjen før første publisering, og bare ett av dem er
arbeid:

1. **Heine leser de to særskilte vurderingene** (2018 PO7, 2020
   faktaboksen) og avgjør om de skal publiseres. Fargeleggingen selv er
   lest og lagt inn — 65 av 65 celler.
2. **Heine skriver «Hvorfor» i utkastene** — eller bestemmer at det kan
   vente.
3. **Hosting og domene velges**, med tallene over som grunnlag.

Kvitteringen for de tre personformnavnene er allerede avgitt.
