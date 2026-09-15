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

## Sidefunn, presisert 14.09.2026: ÉN av tre deler kom utenfra

Første versjon av dette notatet sa at «ingen av kroppene ble hentet av
kilden selv». **Det var for bredt, og målingen under viser hvorfor.**

HI ekkoer `User-Agent` inn i sidene den serverer. Lest per delkropp:

| delkropp | lokal (09.09) | origin (14.09) | ny (14.09) |
|---|---|---|---|
| `rapport` | `curl/8.7.1` | `…ChatGPT-User/1.0…` | `havbruk-radar/1.0` |
| `grensetall_2026-36` | `python-httpx/0.28.1` | `python-httpx/0.28.1` | `havbruk-radar/1.0` |
| `grensetall_2026-37` | `python-httpx/0.28.1` | `python-httpx/0.28.1` | `havbruk-radar/1.0` |

`python-httpx/0.28.1` ER pipelinen — det var httpx' standardstreng fram
til 14.09.2026, fordi ingen kilde satte `User-Agent`.

Så: **to av tre delkropper kom fra `_hent_bevaring()` gjennom
`_http.get()` i begge de gamle kroppene.** Det er bare `rapport`-feltet
som bærer et fremmed verktøy — og det gjør det i BEGGE, med hvert sitt
verktøy. Mønsteret er ikke «noen hentet hele kroppen med curl»; det er at
`rapport`-feltet ble fylt utenfra to ganger, med to ulike verktøy.

Hvorfor akkurat det feltet, vet vi ikke. `hent_begge()` henter
`geojson` og `rapport` gjennom samme `_http.get()`-kall som de to andre,
så koden slik den står i dag ville gitt `python-httpx` på alle tre.

`geojson` kan ikke måles på denne måten — den er ikke HTML og bærer
intet ekko. Men den er byte-identisk i alle tre kroppene
(`e62b5686355a4586`), så spørsmålet har ingen praktisk vekt for
nyttelasten.

## Den tredje kroppen: første henting med kjent proveniens

Hentet 14.09.2026 gjennom `Reguleringsomraader.hent_begge()`, etter at
`_http.py` fikk en fast `User-Agent`. Arkivert som
`reguleringsomraader/2026-06-29.2.json.gz`, sha256 `f045861311ff3c16…`.

Den beviser seg selv: alle tre HI-sidene ekkoer nå `havbruk-radar/1.0`
tilbake. Det er første kropp i denne kilden der arkivet kan svare på hvem
som hentet den.

**De to gamle er ikke slettet.** De er observasjoner av at noe ble hentet
utenfor pipelinen, og den observasjonen er hele grunnen til at
`User-Agent` nå er satt. Regel 2 gjelder uansett, men her er den ikke en
formalitet: sletter man dem, sletter man beviset.

`geojson` er identisk i alle tre, så den nye kroppen er ikke en revisjon
og det er ikke skrevet noe nytt snapshot. Den eksisterende radens
`raw_hash` peker fortsatt på origin-kroppen, og det er en sann påstand om
hvor de radene kom fra.

---

## Hele arkivet skannet: 4 756 kropper, 21 kilder

Målt 14.09.2026, ikke gjettet. Skriptet leser hver `.gz` i
`data/arkiv/`, pakker ut JSON-kropper og skanner både rå og innmat etter
agentstrenger (`curl/`, `python-httpx/`, `requests/`, `Wget/`,
`ChatGPT-User/`, `GPTBot/`, `havbruk-radar/`) og etter vertens
`<!-- AGENT … -->`-ekko.

**Resultat: `reguleringsomraader` er den ENESTE kilden med et målbart
spor, 2 av 2 kropper. De øvrige 4 754 bærer ingenting.**

| kilde | kropper | spor |
|---|---|---|
| `reguleringsomraader` | 2 | ekko i begge |
| alle 20 øvrige | 4 754 | ingen |

De største kildene uten spor: `eierskap-overforinger` 3 029,
`lusetall` 764, `sjotemperatur` 764, `eierskap-brreg` 110.

### Hva et fravær av spor IKKE betyr

**UBESVARLIG, ikke «i orden».** De aller fleste verter ekkoer ikke
`User-Agent` tilbake — Fiskeridirektoratet, BarentsWatch, Brreg og
Lovdata gjør det ikke. For dem kan kroppen ikke svare på hvem som hentet
den, uansett hvem det var.

Havforskningsinstituttet er unntaket, og det er ren flaks at den ene
kilden der proveniensen sviktet også er den ene kilden med en vert som
røper det. Hadde `rapport`-feltet vært hentet fra Fiskeridirektoratet i
stedet, ville avviket vært usynlig og fortsatt vært der.

Derfor er `User-Agent` i `_http.py` ikke en opprydding etter ett funn.
Den er det eneste som gjør spørsmålet besvarbart framover for de kildene
som ikke har en vert som ekkoer — vi kan i det minste vite hva vi selv
sendte, og kropper hentet etter 14.09.2026 hos en ekkoende vert bærer
beviset.

### Sporet gjelder bare framover

Ingen av de 4 754 eldre kroppene får proveniens av dette. De er hentet
med `python-httpx/0.28.1`, som er sant for pipelinen og like sant for
ethvert annet Python-skript på maskinen. Skillet mellom «kilden hentet
den» og «noen kjørte httpx utenfor pipelinen» lar seg ikke gjenopprette
for dem, og skal ikke påstås.
