# Måling 14.09.2026 — kollisjonen i `reguleringsomraader/2026-06-29`

To versjoner av samme dato, én lokal og én på origin, med ulik sha256 i
både arkivkroppen og snapshotet. Spørsmålet: bærer de ulike data, eller
er de samme observasjon hentet to ganger?

**MÅLT: de bærer ikke ulike data.** Ingen løpenummer skrevet, origin
beholdt.

---

## Det som kolliderte

| fil | lokal | origin |
|---|---|---|
| `arkiv/reguleringsomraader/2026-06-29.json.gz` | `792ceffe…` 130 812 B | `b3bf1a1a…` 130 923 B |
| `raw/reguleringsomraader/2026-06-29.parquet` | `fb2274f0…` 11 228 B | `f8b4aec4…` |

Lokalversjonene er bevart utenfor arbeidstreet i
`~/havbruk-kollisjon-2026-09-14/` med `SHA256SUMS.txt`, hash bekreftet
etter kopiering, før rebasen ble kjørt.

---

## Snapshotene: 224 av 224 rader like

Alle tolv kolonner sammenlignet med polars, sortert:

    IDENTISKE uten fetched_at og raw_hash:   True

De to som skiller seg:

    fetched_at   lokal 2026-09-09T20:01:58Z    origin 2026-09-14T10:24:23Z
    raw_hash     lokal aa06340c2c43d405…       origin 0401a180499de87a…

Begge handler om **oss**, ikke om verden (1b-7). `entity_id`, `field`,
`value`, `observed_at`, `published_at`, `source_version`, `utvalg` —
alle like. `observed_at` og `published_at` er `2026-06-29` i begge.

**`raw_hash` peker riktig i begge.** Den er innholdsadressert, ikke
filnavnsadressert, og hver av dem hasher til sin egen arkivkropp:

    lokal    arkiv aa06340c2c43d405…  ==  raw_hash aa06340c2c43d405…
    origin   arkiv 0401a180499de87a…  ==  raw_hash 0401a180499de87a…

At hashene er ulike er altså ikke et avvik — det er to sanne påstander
om hvor hver rad kom fra.

---

## Kroppen: nyttelasten er byte-identisk

Kroppen er en JSON med fem nøkler. Samme nøkkelsett i begge.

| nøkkel | lik | hva det er |
|---|---|---|
| `geojson` | **JA** (31 719 tegn) | de 28 reguleringsområdene |
| `geojson_last_modified` | **JA** | kildens egen utgivelsesdato |
| `rapport` | nei | HIs landingsside, HTML |
| `grensetall_2026-36` | nei | landingsside, HTML |
| `grensetall_2026-37` | nei | landingsside, HTML |

**Observasjonen ligger i `geojson`, og den er identisk.** De tre som
skiller seg er landingssider hos HI, og alle tre skiller seg på nøyaktig
samme tre måter:

1. **Rendringstidspunkt.** HI stempler det inn i sida:
   `<!-- DATODATO 2026-09-09 21:49:48 -->` mot
   `<!-- DATODATO 2026-09-14 12:19:42 -->`.
2. **Ekko av User-Agent.** HI skriver den som spurte inn i sida:
   `<!-- AGENT curl/8.7.1 -->` mot
   `<!-- AGENT Mozilla/5.0 … ChatGPT-User/1.0 … -->`.
3. **Én sidepanelpost.** `rapport-fra-havforskningen-2026-42`
   («Fremmedstoffer i villfisk 2025») ble utgitt mellom de to hentingene
   og skjøv `2026-28` ut av «siste rapporter»-lista. Fire linjer inn,
   fire linjer ut, i hver av de tre sidene.

Diffen er 13–16 linjer per side av 2 690–3 792. Ingen av dem rører
grensetallene eller reguleringsområdene.

---

## Hvorfor dette ikke er en revisjon

Kilden har ikke ombestemt seg. `geojson_last_modified` er lik, og
nyttelasten er byte-identisk — Havforskningsinstituttet sier nøyaktig det
samme 14.09 som 09.09.

Forskjellen kommer fra **oss**: når vi spurte, og hvilken klient vi
spurte med. Det er samme skille som `diff.revisjon()` bygger på, og
samme grunn til at `eierskap_historikk` v1→v2 ble skrevet med
`--reparse` og null changelog-rader: en `revidert`-rad her ville vært en
påstand om at HI endret noe, og det ville vært en anklage mot en
tredjepart for et tidsstempel vi selv utløste.

Derfor er det **ikke** skrevet et `.2`-løpenummer etter biomassens
revisjonsspor. Revisjonssporet finnes for at kilden skal kunne ombestemme
seg; her har den ikke gjort det.

---

## Sidefunn: ingen av kroppene ble hentet av kilden selv

`sources/reguleringsomraader.py` setter ingen `User-Agent`. HI ekkoer den
den får, og de to kroppene oppgir `curl/8.7.1` og
`Mozilla/5.0 … ChatGPT-User/1.0; +https://openai.com/bot`.

Ingen av delene er kildens egen henting gjennom `_http.py` — begge
kroppene er hentet med verktøy utenfor pipelinen, og den ene identifiserte
seg som en OpenAI-bot. Det endrer ingenting ved dataene, som er målt like,
men det betyr at **proveniensen for denne kilden er svakere enn arkivet
antyder**: et arkiv skal kunne si hvem som hentet kroppen, og her sier det
to ulike ting som ingen av dem er oss.

Notert, ikke rettet. En `User-Agent` som navngir prosjektet hører i
`_http.py` og gjelder alle kilder — det er en egen beslutning.
