# Måling 09.10.2026 — Mattilsynets liste over unntaksvekst 2025/2026

Siden «Kapasitetsøkning 2025/2026: Oversikt over søknader og vedtak»
lister søknader om unntaksvekst per lokalitet med resultat og
saksnummer. Den oppdateres løpende og er ikke arkivert. Spørsmålet er
om den kan hentes, om den finnes som åpne data, og om radene lar seg
knytte til et lokalitetsnummer.

**Måling, ingen kilde bygges.** Ingenting er skrevet til `data/`.

---

## 1. robots.txt — siden er tillatt

Hentet med `sources/_http.get()`, altså med prosjektets
`User-Agent: havbruk-radar/1.0`. `www.mattilsynet.no` og
`mattilsynet.no` svarer med samme kropp
(sha256 `ad2d6da1…0780bb`):

    User-agent: *

    Sitemap: https://www.mattilsynet.no/sitemap.xml

Ingen `Disallow`. `urllib.robotparser` gir `can_fetch = True` for
`havbruk-radar/1.0` mot side-URL-en. **MÅLT.** Ingen sperre å omgå.

## 2. Åpne data — lista finnes IKKE i API-et

Lenka «Åpne data (API)» nederst går til `/om-mattilsynet/api`, og
derfra til «Deling av offentlige data via API innen akvakultur-området».
Den peker på `https://akvakultur-offentlig-api.fisk.mattilsynet.io/docs/`
(Swagger), med spesifikasjonen på `/q/openapi`
(versjon `ed7f9fe`, NLOD 2.0, sha256 `779bf51d…e68303`).

REST-endepunktene (uten autentisering; abonnement krever Maskinporten):

| endepunkt | parametre |
|---|---|
| `GET /api/driftsplaner/v1/aktive/soknader` | `limit`, `offset`, `organisasjonsnummer`, `periodeStart` |
| `GET /api/helsestatus/v2/lokaliteter` | `limit`, `offset`, `lokalitetsnummer`, `order-by` |
| `GET /api/lakselus/v2/rapporteringer` | `aar`, `uke`, `lokalitetsnummer`, `organisasjonsnummer`, `fra-/til-rapporteringstidspunkt` |
| `GET /api/rensefisk/v1/rapporteringer` | `fra-/til-rapporteringstidspunkt` |
| `GET /api/sykdomstilfeller/v1/rapporteringer` | `lokalitetsnummer` |

Ingen av dem dekker unntaksvekst. Spesifikasjonen inneholder ikke
ordene «unntak», «kapasitet», «vekst», «vedtak» eller «saksnummer» noe
sted. `driftsplaner/…/soknader` er noe annet: `DriftsplanSøknadResponse`
har feltene `id`, `rapporteringstidspunkt`, `brakkleggingsperioder`,
`teknologier`, `flyttinger`, `utsettAvSettefisk`, `mottakAvFisk`,
`harRensefisk`, `harDrift`. **MÅLT mot spesifikasjonen; ingen
endepunkt er kalt** (regel 4: feltene over er det spesifikasjonen
lover, ikke noe vi har sett i en respons).

`robots.txt` på API-verten svarer 401, ikke 404 — det er ikke en
sperre, men heller ikke et svar.

## 3. Siden, hentet én gang

| | |
|---|---|
| URL | `https://mattilsynet.no/fisk-og-akvakultur/kapasitetsokning-2025-2026-oversikt-over-soknader` (ingen redirect) |
| kropp | `/tmp/unntaksvekst/side.html`, 138 165 byte |
| sha256 | `b427beac0411d44cd1565a6f8bf29dd0e58da64bbe2d46758d39b51601b50f22` (også i `side.html.sha256`) |
| headere | `/tmp/unntaksvekst/side.meta.json` |
| hentet | 2026-10-09T01:15:45Z |

To ting om tid (regel 1b-7), begge MÅLT:

* **Ingen `Last-Modified`.** En kilde ville måttet skrive
  `published_at` som ukjent. Eneste dato på siden er «Faglig gjennomgått
  11.12.2025», som er en redaksjonell påstand og ikke en
  utgivelsestid for lista.
* **Kroppen kom fra CDN-cache:** `x-cache-hit: hit`, `age: 34394`,
  `date: 08.10.2026 15:42:31 GMT`. Det vi fikk var ni og en halv time
  gammelt. `cache-control` gir `s-maxage=31536000`, så cachen kan i
  prinsippet holde på en kopi i et år. Hvor fort en endring i lista
  slår igjennom, er UBELAGT.

Lista er én `<table>` med kolonnene Søker, Lokalitet, Prod.område,
Resultat, Saksnummer. **84 rader**, alle med fem celler.

### Per resultat og PO

| PO | Godkjent | Avslag | sum |
|---:|---:|---:|---:|
| 3 | 32 | 4 | 36 |
| 4 | 23 | 2 | 25 |
| 8 | 7 | 8 | 15 |
| 9 | 1 | 0 | 1 |
| 11 | 2 | 0 | 2 |
| 13 | 4 | 1 | 5 |
| **sum** | **69** | **15** | **84** |

Hva en rad ER, er verdt å merke:

* Siden sier «Mattilsynet mottok **84 søknader**». Tabellen har 84
  rader. Men raden er **søker × lokalitet**, ikke en søknad: det er
  bare **38 ulike saksnummer** og **21 søkere**. «Søknad» i Mattilsynets
  telling betyr altså lokalitet-i-søknad.
* **66 ulike (lokalitet, PO)**. 15 lokaliteter står med flere søkere —
  Andal, Bleket og Dalsvåg NV med tre hver. Ingen lokalitet har fått
  ulikt resultat for ulike søkere.
* Én rad har to saksnummer adskilt med linjeskift i cella
  (Gnarnesvika), to andre med komma. En parser må tåle begge.

## 4. Kobling mot akvakultur-snapshotet

Mot `akvakultur/2026-10-05.parquet` (1 782 lokaliteter). Nøkkel:
lokalitetsnavn (store bokstaver, mellomrom normalisert) + PO
(`prodomraade_kode`). Ingen fuzzy-matching i tallene under.

| utfall | rader | (lok, PO) |
|---|---:|---:|
| **entydig** — nøyaktig én lokalitet | **70** | **54** |
| flertydig — to i samme PO | 1 | 1 |
| navnet finnes, men ikke i oppgitt PO | 1 | 1 |
| navnet finnes ikke | 12 | 10 |

**70 av 84 rader (83 %) får et entydig lokalitetsnummer. MÅLT.**

De 14 som ikke gjør det:

* **Flertydig, løst via `eierskap`:** Djupevika PO 3 (Sjøtroll) har to
  kandidater. 20455 eies av SJØTROLL HAVBRUK SJØ AS, 26595 av LERØY
  VEST SJØ AS. Søkeren skiller dem — **71 av 84** med det steget.
  MÅLT, men koblingen søker→eier er her gjort på øyemål, ikke med
  orgnr (lista har ikke orgnr).
* **Skrivevariant med én kandidat i samme PO — UBELAGT, 10 rader:**
  Hamnsundet → HAMNSUNDET I, Andalsvågen → ANDALSVÅGEN I, Skysselvika
  Vest → SKYSSELVIKA V (2), Øksengården → ØKSENGÅRD (2), Gourtesjokah →
  GOURTESJOUKA, Teigland → TEIGLAND I, Kvaløy → KVALØY Ø, Hundsholmen →
  HUNDHOLMEN. Sannsynlige, men ingen av dem er bekreftet, og de skal
  ikke telles som koblet uten det.
* **Uløst, 3 rader:** Saltkjelen 1 (PO 3 har både SALTKJELEN I og II;
  «1 = I» er et gjett), Brandalskuta (ingen kandidat), Djupvik PO 3
  (navnet finnes bare i PO 8 og 9, og uten PO).

Det er Mattilsynets navn som avviker fra registerets, ikke omvendt:
samme lokalitet står som «Teigland I» hos Quatro Laks og «Teigland» hos
Tombre, og som «Kvaløy Ø» hos Lingalaks og Varde men «Kvaløy» hos
Tombre. Lista er skrevet for hånd.

---

## Hva målingen sier

* Siden kan hentes, og bare der: lista finnes ikke i det åpne API-et.
* Formatet er en håndskrevet HTML-tabell uten lokalitetsnummer, uten
  orgnr og uten utgivelsestid. Koblingen er navnebasert og stopper på
  83 % uten skjønn.
* Siden er ikke arkivert, og CDN-et kan servere en gammel kopi. Hver
  henting vi ikke gjør, er en versjon av lista som er borte (regel 5).
