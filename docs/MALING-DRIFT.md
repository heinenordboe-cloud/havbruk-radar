# Måling: hva fangstjobbene sjekker i kroppen før den lagres

Målt 02.11.2026, lokalt, mot `havbruk-radar` på `df2a535` og arkivet i
`havbruk-radar-data` slik det var etter `git pull` samme kveld. Skriptet
er `analyse/drift/kroppssjekk.py`; utskriften står uendret i
`analyse/drift/kroppssjekk.txt` og under «Utskriften».

Spørsmålet: for hver jobb som fanger data — hva sjekkes i kroppen før
den lagres (status, størrelse, format, antall rader), og hva skjer om
kilden svarer **200** med en feilside, en tom liste eller en halv kropp?
Dette er en måling. Ingenting er rettet; forslagene er én linje hver.

**Merkene:** MÅLT = holdt mot en arkivert kropp, med sha256 (her: de
ekte kroppene som ble halvert). MÅLBAR = sett ved å kjøre jobbens egen
kode lokalt mot en konstruert kropp, eller lest i koden med fil og linje
— ikke holdt mot en arkivert kropp. UBELAGT = ingen kjøring eller kropp
sier det.

## Slik ble det prøvd

Fire kropper, alle med status 200: `feilside` (en HTML-side på 146 B,
«Tjenesten er midlertidig utilgjengelig»), `tom_liste` (`[]`),
`tom_kropp` (null byte) og `halv` (første halvdel av en ekte arkivert
kropp for jobben). Hver kombinasjon kjøres i en egen prosess med
`HAVBRUK_DATA_DIR` pekt til en tom mappe. Nettet er en falsk
httpx-transport som svarer kroppen på hvert kall, unntatt BarentsWatchs
token-endepunkt, som får et gyldig token. «Lagret» er filer jobben
etterlot under `data/` utenom loggene. Lytterne prøves med prøveserveren
i `tests/test_kystvakt_lytter.py`; `ais_manifest.py` får kroppen på
stdin, som i `ais-manifest.yml`.

Fordi arkivmappa er tom, er hver kropp «ny». I drift sammenligner
`daglig`, `vilkar`, `havbruksfond` og `luseinnkomst` med siste lagrede
kropp, og en feilside skiller seg fra den — den blir altså også ny der.

## STOPP-regelen

Skrevet etter at de tre første tilfellene var kjørt (daglig/feilside,
daglig/tom_liste, vilkar/feilside), før resten. Målingen stopper og
rapporterer i stedet for å gå videre hvis:

1. `git status` i datarepoet viser en endring etter en kjøring — prøven
   har i så fall skrevet i det ekte arkivet, og hver rad etter det er mistenkt.
2. En jobb henter noe prøven ikke svarer på (et kall utenom httpx). Den
   jobben merkes UBELAGT i stedet for å tolkes.

**Utfall:** ingen av dem. `git status --short` i datarepoet var tom etter
begge fulle kjøringer. Vilkårsarkiveringen lagret fem kropper på 146 B,
som er feilsidens lengde: svarene kom fra prøven, ikke fra nettet.
Lytteren bruker `http.client`, ikke httpx, og ble derfor prøvd mot sin
egen prøveserver.

## De tre sterkeste funnene

**1. Tre jobber lagrer hva som helst og ender grønne (F1.1–F1.3).**
`arkiver_vilkar.py` og `arkiver_havbruksfond.py --daglig` lagret alle
fire kroppene som nye med exit 0. `arkiver_auksjon.py` lagret dem også;
tre av fire feilet ETTER lagringen, og den tomme kroppen ga exit 0.
*Hvorfor sterkest:* alle tolv tilfeller gikk samme vei, og en grønn
kjøring med en feilside i arkivet er nøyaktig den stillheten tilsynet
ikke kan se.

**2. En halv sjøtemperaturfil blir et snapshot med halve
lokalitetsmassen (F3.1).** Første halvdel av kroppen 2026-10-05 ga
`ok=True` og 1355 observasjoner; hele kroppen gir 2733. Volumvakten
(90 % av referansen 2739) gjør uka DELVIS, men `run.py` skriver
snapshotet uansett (`run.py:538`). *Hvorfor sterkt:* det er den eneste
av 48 samle-kombinasjonene som gir et snapshot med rader fra en
ødelagt kropp. *Svakere:* hva changeloggen gjør med de ~1380 som mangler,
er ikke kjørt (UBELAGT).

**3. En gyldig, men tom utlevering overskriver AIS-statusen (F2.2).**
`ais_manifest.py` stopper på alt som ikke er JSON, men
`{"manifester": [], "skrevet": ""}` ga exit 0 og en `status.json` med
bare `skrevet`. Tilsynet leser den neste morgen og blir rødt
(`.github/tilsyn.py`, `ais()`: `KeyError` gir `::error::`), så det er
fanget — ett døgn senere, og forrige status er overskrevet.

Svakere enn de tre: daglig og luseinnkomst (F4), der nesten alt stoppes,
og lytterne (F1.4), der fraværet av sjekk er et valg.

## Tabellen

Sammenstilling av utskriften under, ikke utskrift selv. Jobber uten
kroppssjekk øverst.

| Jobb | Hva sjekkes før lagring | Feilside | Tom liste / tom kropp | Halv kropp | Forslag |
|---|---|---|---|---|---|
| vilkar | status (`_http`); ingenting i kroppen | lagret, exit 0 | lagret, exit 0 | lagret, exit 0 | Avvis en kropp der synlig tekst er under halvparten av forrige versjons, og la den bli rød. |
| havbruksfond (`--daglig`) | status; `%PDF` bare for vedlegg (`arkiver_havbruksfond.py:240`) | lagret, exit 0 | lagret, exit 0 | lagret, exit 0 | Krev «Havbruksfond» i synlig tekst på siden før den lagres. |
| lytterne (bw, 5632) | status ved tilkobling (`lytter.py:273`); linjene lagres urørt | lagret | lagret | lagret | La tilsynet feile når andelen linjer uten MMSI i regnskapet passerer en målt grense. |
| auksjon | status; kroppen arkiveres FØR den tolkes | lagret, exit 1 | lagret, exit 1 / lagret, exit 0 | lagret, exit 1 | Avvis tom kropp og kropp uten `<html` før arkivering. |
| ais-manifest | gyldig JSON (workflowen og `json.load`); manifestlinjer mot regex | stoppet, exit 1 | stoppet / stoppet | stoppet | Krev `skrevet`, `disk` og `regnskap` før `status.json` overskrives. |
| samle (12 kilder) | status; rå kropp arkiveres alltid før parse (`core/runner.py:279`); parse per kilde; tom levering og volumvakt i `health.py` | 10 kilder feiler i `fetch()` eller `parse()`; sjøtemperatur ok med 0 rader | eierskap og sjøtemperatur ok med 0 rader; resten feiler | sjøtemperatur 1355 av 2733 rader, snapshot skrives; resten feiler eller gir samme antall | Hold snapshotet tilbake når volumvakten slår til, eller merk radene. |
| daglig (eierskap, biomasselag, akvakultur) | status; kildenes `fetch()` | alle tre feiler | eierskap lagret (57 B), de to andre feiler | alle tre feiler | La `eierskap.fetch()` avvise null tillatelser. |
| luseinnkomst | JSON og `localities` ikke tom (`arkiver_luseinnkomst.py:92`) | feiler | feiler | feiler | Sammenlign antall lokaliteter med forrige kropp for uka. |

## Funnene

### F1 Ingen kroppssjekk

**F1.1 Vilkårsarkiveringen lagrer feilsiden.** MÅLBAR. Alle fire kroppene
ga fem nye filer (`vilkar-barentswatch`, `-brreg`, `-fiskeridir`,
`-lovdata`, `-mattilsynet`) og exit 0. Koden sammenligner sha256 og
synlig tekst med forrige versjon, men bare for å avgjøre «ny» eller
«uendret», ikke for å avvise.
*Feil hvis:* `arkiver_vilkar.py` avviser noen av de fire kroppene når
den kjøres mot en tom arkivmappe.

**F1.2 Havbruksfondarkiveringen lagrer feilsiden.** MÅLBAR. Alle fire ga
`havbruksfondet/2026-11-02.bin.gz` og exit 0. Den halve kroppen er
første halvdel av `data/arkiv/havbruksfondet/2026-10-28.bin.gz` (MÅLT:
utpakket 25 545 B, sha256
`40b98b7666e72d42ad3c11b7ac4005991f21df669b899db4f9b32ca8d9dabe96`).
*Feil hvis:* `--daglig` hopper over siden når kroppen ikke er en side om
fondet.

**F1.3 Auksjonsarkiveringen lagrer før den tolker.** MÅLBAR. Alle fire
ga `auksjon/2026-11-02.bin.gz`. Feilside, tom liste og halv kropp feilet
deretter i tolkingen (`ValueError` ved utpakking av lenkene), exit 1. Den
tomme kroppen ga exit 0. Halv kropp: første halvdel av
`data/arkiv/auksjon/2026-10-29.bin.gz` (MÅLT: utpakket 21 359 B, sha256
`ec349d722235fb7400c3b3c652c413483f1d5b2bc78096d0e88f04ca67c6c9ed`).
*Feil hvis:* en tom 200 gir rød kjøring eller ingen fil.

**F1.4 Lytterne lagrer alt etter 200.** MÅLBAR. bw-lytteren skrev
feilsiden, `[]` og en avkortet JSON-linje som én linje hver, og
regnskapets leser (`regnskap.les_bw`) fant ingen MMSI i noen av dem. Det
er et valg (rådata lagres urørt), men regnskapet teller dem som
`meldinger`. Konsekvens rettet i samme økt: pulsen til overvåkingen
utenfra krever meldinger MED MMSI (`df2a535`, `regnskap.puls()`).
*Feil hvis:* lytteren forkaster linjer som ikke er JSON.

### F2 Bare formatet sjekkes

**F2.1 ais-manifest stopper på alt som ikke er gyldig JSON.** MÅLBAR.
Feilside, `[]`, tom og halv utlevering ga exit 1 og ingen fil.
*Feil hvis:* en av dem gir en skrevet fil.

**F2.2 En gyldig, men tom utlevering overskriver statusen.** MÅLBAR.
`{"manifester": [], "skrevet": ""}` ga exit 0 og `data/ais/status.json`
med bare `skrevet`. `tilsyn.py ais()` leser `st["disk"]` og gir
`::error::` på `KeyError` — lest i koden, ikke kjørt.
*Feil hvis:* `ais_manifest.py` avviser svaret.

### F3 Samle: kildene tolker, volumvakten melder, snapshotet skrives

**F3.1 Halv sjøtemperaturfil gir et halvt snapshot.** MÅLBAR. Første
halvdel av `data/arkiv/sjotemperatur/2026-10-05.txt.gz` (MÅLT: utpakket
125 908 B, sha256
`8e3ed284fde0eff10305373e95228bbb60756e742e65649052f1dfd67df95d40`) ga
`ok=True`, 1355 rader; hele kroppen gir 2733 med samme kode. 1355/2739 er
49 %, under `STANDARD_MIN_ANDEL = 0.90` i `core/health.py`, så uka blir
DELVIS. `run.py` skriver snapshotet for hver kilde med `r.ok` og rader,
uavhengig av volumvarselet (`run.py:524–538`).
*Feil hvis:* `run.py` hopper over snapshotet når volumvakten slår til.

**F3.2 Feilside og tom kropp gir sjøtemperatur `ok` med 0 rader.**
MÅLBAR. Ingen exception; `health.py` behandler det som TOM LEVERING:
`sist_ok` røres ikke, uka blir DELVIS, tirsdagen prøver igjen (lest i
`core/health.py`, ikke kjørt). Eierskap gjør det samme med `[]`, og gir i
tillegg personfilter-advarselen.
*Feil hvis:* `sjotemperatur.parse()` kaster på en kropp uten kolonnene.

**F3.3 De andre ti kildene stopper i `fetch()` eller `parse()`.** MÅLBAR. Akvakultur,
biomasselag, ekspertgruppen, enhetsregisteret, lusetall, romming og
unntaksvekst feiler for alle fire; biomasse, reguleringsområder og
trafikklysvedtak også, bortsett fra trafikklysvedtak med halv kropp, som
gir 12 rader — samme antall som hele kroppen. Den rå kroppen er arkivert
FØR tolkingen for biomasse, reguleringsområder, sjøtemperatur og
trafikklysvedtak (`core/runner.py:279`), med vilje: en parse-feil skal
ikke koste kroppen. For de øvrige stopper `fetch()` selv, så ingenting
arkiveres.
*Feil hvis:* en av dem gir `ok=True` med rader for feilside eller tom
liste.

**F3.4 Trafikklysvedtak har ingen volumreferanse.** MÅLBAR. `health.json`
har `volum_referanse: null` for kilden, så volumvakten kan ikke slå til
for den. Sammen med F3.3 er det likevel ikke målt noen kropp som gir
færre rader uten feil.
*Feil hvis:* `health.json` har en referanse for `trafikklysvedtak`.

### F4 Det meste stoppes

**F4.1 Daglig arkiv.** MÅLBAR. Biomasselag og akvakultur feilet for alle
fire (akvakultur med egen grense: «Fikk bare 0 lokalitet(er) …»).
Eierskap godtok `[]` og lagret en kropp på 57 B, med personfilter-
advarselen som `::warning::`. Kjøringens exit 1 kom fra de to andre;
alene ville eierskap ha gitt exit 0 — lest i `arkiver_daglig.py`
(`return 1 if feil else 0`), ikke kjørt alene.
*Feil hvis:* `eierskap.fetch()` kaster på en tom liste.

**F4.2 Luseinnkomst.** MÅLBAR. Alle fire feilet før lagring; koden krever
at `localities` finnes og ikke er tom (`arkiver_luseinnkomst.py:92`). Ikke
prøvd: et svar med riktig form og få lokaliteter. Det finnes ingen
nedre grense for antallet i fangsten (UBELAGT om den trengs).
*Feil hvis:* en av de fire gir en fil under `lusetall-innkomst/`.

## Utskriften

Kjørt `.venv/bin/python analyse/drift/kroppssjekk.py`, se
`analyse/drift/kroppssjekk.txt` (uendret). Linjene for samle er én per
kilde og kropp; `rå arkivert` teller filer under `data/arkiv/`.

## Etterskrift 03.11.2026: fire målinger før rettingen (økt 3b, punkt 0)

Teksten over er ikke endret. Denne delen står før noe av funnene over er
rettet, og reglene under ble skrevet og committet før 0b, 0c og 0d ble
kjørt. Resultatene står under reglene.

### Reglene, skrevet før målingen

**0b, stoppregel.** Målingen kjører changeloggen og endringsdeteksjonen
(`diff.compare`, `changelog.skriv_per_dato`, `signals.score`) mot
snapshotet fra den halve sjøtemperaturkroppen, og leter i tillegg i
ARKIVET etter et halvt snapshot som allerede har gitt falske hendelser.
Et halvt snapshot er her et snapshot i `data/raw/<kilde>/` med færre enn
90 % (volumvaktens `STANDARD_MIN_ANDEL`) av entitetene i snapshotet
foran, der snapshotet etter igjen har minst 90 %. En falsk hendelse er
en `borte`-rad i `data/changelog/<kilde>/` på datoen til et slikt
snapshot, for en entitet som står som `ny` på datoen etter. Finnes én
eneste: arbeidet stopper før punkt 1, radene listes, og Heine avgjør.

**0c, grensen for lytterne.** Grunnlaget er hvert timeregnskap siden
28.10.2026 med minst én melding, per kilde, og andelen er
`uten_mmsi / meldinger`. Grensen per kilde blir den høyeste timeandelen i
grunnlaget, rundet opp til nærmeste hele prosent, så grunnlaget selv gir
null alarmer. Ligger den høyeste andelen på 50 % eller mer, eller spenner
timene over mer enn 20 prosentpoeng, bygges ingen grense i punkt 6:
fordelingen rapporteres, og grunnen står her.

**0d, luseinnkomsten.** For hver uke i `data/arkiv/lusetall-innkomst/`:
antallet lokaliteter i hver kropp, i rekkefølgen kroppene ble hentet
(`fetched_at` i fangstloggene, løpenummeret der loggen mangler). Går
antallet ned fra én kropp til den neste for samme uke, bygges ikke
regelen i punkt 9; kroppene listes i stedet.
