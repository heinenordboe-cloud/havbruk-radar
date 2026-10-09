# Kilde: `unntaksvekst` — Mattilsynets søknader om unntaksvekst 2025/2026

Kode: `sources/unntaksvekst.py`. Måling: `docs/MALING-UNNTAKSVEKST.md`.
Bygget 08.10.2026. Ukentlig via `run.py`. På nettstedet fra
09.10.2026, på /analyse/unntaksvekst/ og i ukesendringene (se punkt 6).

## 1. Hva som hentes

| kall | hvorfor |
|---|---|
| `GET mattilsynet.no/fisk-og-akvakultur/kapasitetsokning-2025-2026-oversikt-over-soknader` | lista, én HTML-tabell |
| `GET pub-aqua /entities` | kandidater for søkernavnet, med form og orgnr |
| `GET pub-aqua /sites` | lokalitetsnummer på navn + PO |
| `GET pub-aqua /licenses` | hvem som eier tillatelsene på en lokalitet (`via_soker`) |

Tabellhodet må være nøyaktig `Søker | Lokalitet | Prod.område |
Resultat | Saksnummer`, ellers kaster kilden. En tom tabell kaster også
— den skal ikke leses som at alle søknadene er trukket.

## 2. Hva som arkiveres, og hva som ikke gjør det

`data/arkiv/unntaksvekst/<dato>.json.gz` er **tabellen etter
søkerfilteret**, ikke HTML-kroppen. Ved siden av radene står

* `sha256` og `bytes` for HTML-kroppen slik den kom,
* `headere`: `date`, `age`, `x-cache-hit`, `cache-control`, og
  `last-modified`/`etag` om de noen gang dukker opp,
* `url` og `status`.

Grunnen er at kroppen inneholder søkernavn uten orgnr, og et av dem kan
være et enkeltpersonforetak. Arkivet er append-only i git. Samme valg
som `enhetsregisteret`, `eierskap` og `romming`. Kostnaden: kroppen kan
ikke parses på nytt fra arkivet — bare radene etter filteret.

`Date`, `Age` og `X-Cache-Hit` skrives også i kjøringsloggen:

    [unntaksvekst] sha256 b427beac0411 date='Thu, 08 Oct 2026 15:42:31 GMT' age='35280' x-cache-hit='hit'

Kopien fra CDN-et var 9 t 48 min gammel da den ble hentet. Uteblir både
`Age` og `X-Cache-Hit`, gir kilden en advarsel (KREVER TILSYN): da kan
kopiens alder ikke lenger leses.

`published_at` er tom. Siden har ingen `Last-Modified`, og `Date − Age`
er når CDN-et hentet kroppen — CDN-ets `fetched_at`, ikke Mattilsynets
utgivelse (1b-7).

## 3. Søkeren

Søkernavnet lagres bare når det kobles **entydig** til et orgnr med
**selskapsform**:

1. Navnet normaliseres (store bokstaver, ett mellomrom, `AS`/`ASA`/`SA`/
   `DA`/`ANS`/`ENK`/`BA` i enden strøket) og sammenlignes med HVER enhet
   i `/entities` — også personene.
2. Nøyaktig ett treff, ellers utelates søkeren.
3. Treffet må ha ni siffer og en `typeValue` som
   `sources/eierskap.FORM_KART` oversetter til en ikke-personform.

Ingen likhetsgrad, ingen prefiks. «Vet ikke» betyr filtrer ut. En rad
uten søker får `soker_utelatt = ja` og beholder lokalitet, PO, resultat
og saksnummer.

Felter når søkeren er med: `soker` (Mattilsynets skrivemåte),
`soker_orgnr`, `organisasjonsform`, `soker_utelatt = nei`.
`organisasjonsform` heter det samme som i `enhetsregisteret`, slik at
personvakten i `snapshot.write()` har noe å lese.

**Målt 08.10.2026: 81 av 84 rader beholder søkeren**, 20 ulike søkere,
alle `AS`. De 3 som utelates er «Marø Havbruk og E. Karstensen
Fiskeoppdrett» — to foretak i én celle, uten treff.

## 4. Lokalitetsnummeret

Slått opp i `/sites` på navn + `prodAreaCode`, og merket med hvordan:

| `lokalitet_kobling` | betydning | `lokalitet_nr` | målt 08.10 |
|---|---|---|---:|
| `entydig` | ett register-navn likt i oppgitt PO | satt | 70 |
| `via_soker` | flere like navn, nøyaktig ett med tillatelse eid av søkerens orgnr | satt | 0 |
| `usikker` | ikke likt i PO, men nøyaktig én skrivevariant i PO | satt, **ikke bekreftet** | 11 |
| `flertydig` | flere kandidater | tom | 3 |
| `annen_po` | navnet finnes bare i andre PO | tom | 0 |
| `ikke_funnet` | ingen kandidat | tom | 0 |

`lokalitet_kandidater` lister numrene som ble vurdert.

Skrivevariant (`_skrivevariant()`): det ene navnet er det andre pluss ett
ord (`HAMNSUNDET I`), eller tegnlikhet ≥ 0,85 etter at `VEST`/`AUST`/
`NORD`/`SØR` er forkortet. Det er en markering, ikke en kobling, og den
skal ikke telles som koblet.

Avvik fra målingen, alle forklart:

* **Brandalskuta → BRANDASKUTA (12040), `usikker`.** Målingen hadde den
  som «ingen kandidat» fordi den bare så etter like navn. Én bokstav
  skiller dem.
* **Djupvik PO 3, `flertydig`.** I PO 3 finnes DJUPEVIK (10338) og
  DJUPEVIKA ×2, alle skrivevarianter. Målingen fant navnet bare i PO 8/9.
* **Djupevika PO 3, `flertydig`, ikke `via_soker`.** Målingen løste den
  på øyemål: 20455 eies av SJØTROLL HAVBRUK **SJØ** AS. Søkeren «Sjøtroll
  Havbruk» kobles til SJØTROLL HAVBRUK AS (929363833), som er et annet
  orgnr. Regelen krever samme orgnr, og gjetter ikke på konsernet.

## 5. Entitet og tidsakse

`entity_id = <saksnumre>|<LOKALITETSNAVN>|PO<n>`, `entity_type =
soknad_lokalitet`. Raden er søker × lokalitet (målingen punkt 3), og
saksnummeret skiller søkerne. Nøkkelen bygger på Mattilsynets navn, ikke
registerets, så den flytter seg ikke om koblingen endres.

`partisjonering = "henting"`: lista sier hva som er søkt og avgjort nå.
Erklært før første snapshot, ikke målt (se `test_partisjoneringen_er_den_malte`).
`domene` er uttømmende: en rad som forsvinner fra lista er fjernet, ikke
fortiet — men se punkt 2: en gammel CDN-kopi kan gi en rad som kommer og
går. Sjekk `headere.age` i arkivet før en `borte` leses som et vedtak.

## 6. Lisens — belagt i lov, åndsverkloven § 14 (fra 09.10.2026)

Til 09.10.2026 sto kilden som UBELAGT: lista ligger ikke i det
NLOD-lisensierte API-et, og vilkårene for nettsidens innhold var ikke
lest. Det holdt kilden ute av publiserte visninger.

Belagt i lov 09.10.2026: lista er en oversikt over vedtak av offentlig
myndighet og er uten vern etter åndsverkloven § 14; den er fakta uten
verkshøyde, og den er ingen vesentlig investering i innsamling i § 24s
forstand. Paragrafene står ordrett med hash i `docs/LISENSKJEDE.md`
merknad K, der følgene også står.

Mattilsynets side «Vil du bruke tekstar frå Mattilsynet?» beholdes som
praksis: `attribusjon` er `("Kilde: Mattilsynet",)`, og adressen og
datoen står ved tabellen på analysesiden.
