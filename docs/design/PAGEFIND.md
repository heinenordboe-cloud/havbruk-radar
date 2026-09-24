# Pagefind — søket, og hva porten gjør med det

Søket på `/sok/` er Pagefind, selvhostet. Indeksen bygges av en binær
ved bygging og legges i `/pagefind/`; `maler/sok.js` laster modulen
derfra i nettleseren ved FØRSTE TASTETRYKK, ikke ved sidelast.

## Kilde og lisens

| | |
|---|---|
| Verktøy | Pagefind 1.4.0, av CloudCannon |
| Opphav | `github.com/CloudCannon/pagefind` |
| Lisens | MIT |
| Hentet | 2026-09-22 |
| Binær | `pagefind-v1.4.0-aarch64-apple-darwin.tar.gz` |
| sha256 | `647fa1da25fefeb24348ed09cccfcbcdd1dcab75c83e146c9f50336a78efb290` |

## BINÆREN ER IKKE I REPOET

15,6 MB, og plattformspesifikk. Den er et **verktøy**, som `fonttools`
og `pyftsubset` — ikke en avhengighet siden har i runtime. Den finnes
på `PATH`, eller i miljøvariabelen `HAVBRUK_PAGEFIND`.

    HAVBRUK_PAGEFIND=/sti/til/pagefind python nettsted.py --alle

Installert uten sudo i `~/.local/bin`, med sjekksummen sammenlignet før
utpakking — kommandoene står i `requirements-verktoy.md`, og det er
samme mønster som Node fikk 23.09.2026.

**Mangler den, sier bygget det.** `/sok/` skrives uansett, og
veiviseren til de tre flate indeksene virker — men byggerapporten
skriver `søkeindeks IKKE BYGGET` med grunnen. Et søk som stille slutter
å virke er nøyaktig formen på feilene i CLAUDE.md 1b.

### Og produksjon nektes

At bygget SIER det, er ikke nok: linja står i en rapport på 30 linjer,
og den dagen noen har det travelt er den lest av ingen.

`publiser.py` steg 4 nekter derfor å legge ut til **produksjon** uten
søkeindeks (`krev_sokeindeks()`, 23.09.2026). Til forhåndsvisning blir
det en advarsel, fordi forhåndsvisningen ses av den som ba om den og
produksjon av alle andre.

To ting om HVA den måler:

* **Filene, ikke rapporten.** `--uten-bygg` laster opp en mappe
  `publiser.py` ikke har bygget, og da finnes ingen rapport å lese. En
  rapport sier dessuten bare at vi PRØVDE (CLAUDE.md 1b-2); filene under
  `nettsted/pagefind/` sier at indeksen er der.
* **Også `pagefind.js`.** Uten modulen `maler/sok.js` laster ved første
  tastetrykk, svarer søkefeltet ingenting uansett hvor komplette
  tekstutdragene er.

Spriket mellom sider og tekstutdrag er IKKE dette skrittets sak — det er
portens `ugranska`-funn i steg 3, se nedenfor. To steder som stoppet på
samme spørsmål kunne svart ulikt på det.

### Og hva den IKKE svarer på

Om indeksen er over DISSE sidene. Katalogen tømmes før hvert bygg, så et
BYGG kan ikke etterlate en gammel indeks — men `--uten-bygg` laster opp
mappa som den ligger, og en indeks fra et tidligere bygg ville passert.

MÅLT 23.09.2026: utputtmappa bar en pagefind-indeks fra et tidligere
bygg — 2 349 sider, men en annen språkhash enn dagens
(`nb_64e7b3be60` mot `nb_47803f7523`) — skrevet av en binær som ikke
lenger fantes på `PATH`. Den var trolig i orden. Ingenting i prøven ville
sagt fra om den ikke var det.

Å lukke det krever et stempel som knytter indeksen til sidene den ble
bygget fra, og det finnes ikke i dag. Ført opp her framfor å bli
oppdaget: det er formen på CLAUDE.md 1b-2, en prøve som svarer på noe
som LIGNER spørsmålet.

## Hva som legges ut, og hvor mye

MÅLT 22.09.2026 over 2 338 sider:

    2 560 filer, 16,2 MB, bygget på 8,1 s

    pagefind.js                 33,9 kB   modulen /sok.js laster
    pagefind-entry.json          ~1 kB    peker på resten
    wasm.nb.pagefind            54,3 kB   søkemotoren, norsk stemming
    wasm.unknown.pagefind       52,7 kB   samme motor, uten stemming
    fragment/*.pf_fragment      ~2 338    ett tekstutdrag per side
    index/*.pf_index               ~13    ordtabeller

De ferdige grensesnittene Pagefind også legger igjen —
`pagefind-ui.*`, `pagefind-modular-ui.*`, `pagefind-highlight.js`, til
sammen ~120 kB — **slettes etter kjøringen**. Vi skriver vår egen
søke-UI i `maler/sok.js` og laster bare `pagefind.js`. En fil på
nettstedet er en fil noen kan laste ned, og hver av dem må porten gå
god for.

## Katalogen tømmes før hver kjøring

Pagefind skriver filnavn med en hash i, så en kjøring over et endret
nettsted legger NYE filer ved siden av de gamle framfor å erstatte dem.
MÅLT: to kjøringer ga 5 117 filer og 32,3 MB der én gir 2 560 og
16,2 MB — og halvparten var en indeks over sider som ikke fantes
lenger.

Dette er det ene stedet nettstedsbyggeren sletter noe den selv har
skrevet. Det er trygt av samme grunn som at hele utputtmappa kan
slettes: den er en ren funksjon av snapshotene. Append-only gjelder
`data/raw/`, ikke utputtet.

## HVA PORTEN GJØR MED FILENE

Dette er den vanskelige delen, og den er verdt å skrive ned fordi
publiseringsvakten stoppet byggingen fire ganger på veien.

### `.pf_fragment` — PAKKET TEKST, granskes

Gzip rundt `pagefind_dcd` + JSON. De bærer **teksten fra sidene**:
navn, kommuner, orgnumre, alt. De er like publiserte som HTML-en, og de
er laget for å lastes ned.

De kan ikke pinnes på sha256 som fontene: summen endres hver uke fordi
innholdet ER sidene. De kan ikke legges i `TEKSTTYPER`: de er ikke
tekst. Den tredje veien er å pakke dem ut og granske innholdet med de
samme tre prøvene som for HTML, og det er den som er tatt —
`publiseringsvakt._pakket_tekst()`.

MÅLT: 0 falske funn. Prøvene virker på dem som på HTML.

### `.pf_index` og `.pf_meta` — AVLEDET, granskes ikke hver for seg

CBOR-ordtabeller. Tre veier ble prøvd:

1. La dem stå som `ugranska`. Porten faller da hver uke på 2 558 filer,
   og en port som alltid faller blir slått av.
2. Pakke dem ut og granske dem som tekst. **MÅLT: 2 418 funn, alle
   falske.** CBOR-rammen limer sammen nabotokener, og «20260126» + en
   lengdebyte «2» blir «202601262» — ni siffer på rad som `NI_SIFFER`
   leser som et organisasjonsnummer. Ingen av dem er et tall. En vakt
   som feiler feil blir slått av.
3. Erklære dem AVLEDET av tekstutdragene, som ER gransket.

**Derivasjonsargumentet:** Pagefind trekker ut teksten fra en side én
gang og skriver den til BÅDE `.pf_fragment` og ordtabellene. Er
utdragene rene, er tabellene bygget av rene ord.

Argumentet hviler på at det finnes ett utdrag per indeksert side.
Holder ikke det, er ordtabellen bygget av noe vakten ikke har sett.
`test_hvert_indeksert_sideutdrag_granskes` håndhever det, og den er
grunnen til at dette ikke bare er en påstand.

Samme form som ikonene: PNG-ene er rastret av `favicon.svg`, som vakten
leser som tekst.

### `wasm.*.pagefind` — PINNET på sha256

Søkemotoren, ikke dataene våre. Innholdet kommer fra binæren og er
uavhengig av hva som indekseres. Summene står i
`publiseringsvakt.BINAERFILER`; en annen versjon av Pagefind gir andre
summer, og porten faller til `ugranska`.

### `pagefind.js` og `pagefind-entry.json`

`.js` og `.json` står i `TEKSTTYPER` og granskes som all annen tekst.

## HVA SOM IKKE INDEKSERES

`data-pagefind-body` på `<main>` og på sidehodet avgrenser indeksen til
INNHOLD. Uten den bærer hvert av de 2 338 utdragene menyens seks lenker
og bunntekstens fire spalter — et søk på «Lovdata» ville truffet alle
sidene, og utdraget i trefflista ville vært bunnteksten.

`data-pagefind-ignore` står på navneverdier som ender på en
organisasjonsform SSB regner som personlig (ANS, DA, PRE …). **Navnet
står på siden** — det er et selskapsnavn fra et offentlig register, og
de få tilfellene er kvittert ut hver for seg — men det gjøres ikke
søkbart.

En søkeindeks er noe annet enn en side: den er en maskinlesbar liste
over hvert ord på nettstedet, og et navn som kan slås opp der er en
oppføring i et register. Samme gradering som regel 3 gjør når den sier
at et URL-rom er en liste over hvem som finnes, selv om hver side
skulle være tom.

MÅLT 22.09.2026: 14 av 2 338 sider bar et slikt navn.

## Oppdatering

Hent en ny binær, sammenlign sha256 mot tabellen over, kjør bygget, og
skriv om wasm-summene her OG i `publiseringsvakt.BINAERFILER`.
