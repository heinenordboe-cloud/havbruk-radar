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

### Utfallet

**Ingen av de tre reglene stoppet arbeidet.** 0b fant ingen falske
hendelser i arkivet, 0c ga en grense for bw (og ingen for 5632, fordi
det ikke finnes et grunnlag), og 0d fant ingen uke der antallet gikk ned.

**0a. Slik arkiveres kroppene i dag.** MÅLBAR, lest i koden
(`havbruk-radar` på `0a78bbf`) og i workflowene i datarepoet, lest i
kopiene som lastes opp med `last-opp.sh`.

| Jobb | Hvor kroppen havner | «ny» mot «uendret» | Commit når skriptet er rødt |
|---|---|---|---|
| samle | `data/arkiv/<kilde>/<gjelder_for>.<ext>.gz`, `.2` ved kollisjon (`raw.arkiver`, `core/runner.py:279`), FØR parse | ingen: hver henting blir en fil | ja (`if: always()`), alt under `data/` utenom de andre jobbenes stier |
| vilkar | `vilkar-<part>/<dato>.bin.gz` (`raw.arkiver_ny`) | sha256 mot ALLE kropper i mappa | ja |
| auksjon | `auksjon/<dato>.bin.gz` (`raw.arkiver_ny`) | som vilkar | ja |
| havbruksfond | `havbruksfondet/`, og pressemeldingene under sin egen «Dato:» (`raw.arkiver_ny`) | som vilkar | ja |
| daglig | `<kilde>/<dato>.daglig.<ext>.gz` (`raw.arkiver` med merket `DAGLIG`) | kanonisk sha256 mot SISTE kropp, daglig eller ukentlig | ja, men bare navn som matcher `*.daglig.*` i toppen av mappa |
| luseinnkomst | `lusetall-innkomst/<mandag>.json.gz`, `.2` … (`raw.arkiver`) | sha256 mot siste kropp for SAMME uke | ja |
| ais-manifest | `ais-manifest/<kilde>/<dato>.SHA256SUMS`, og `data/ais/status.json` overskrevet hver kjøring | manifest: skrives én gang; status: alltid | NEI: commit bare når skrivesteget lyktes |

Den felles hjelperen finnes for SKRIVINGEN: `core/raw.py` eier
serialiseringen, navnene og løpenummeret (`_serialiser`, `_ledig_sti`,
`arkiver`, `arkiver_ny`, `kropper`, `orden`). Det finnes ingen felles
sjekk av kroppen, og tre ulike svar på «er den ny». Hver jobb skriver sin
egen logg.
*Feil hvis:* en av jobbene i tabellen kaller en felles funksjon som
vurderer innholdet i kroppen før den skrives.

**0b. Det halve snapshotet.** MÅLBAR: den halve kroppen er konstruert,
kroppen den er halvert fra er `data/arkiv/sjotemperatur/2026-10-05.txt.gz`
(utpakket 125 908 B, sha256
`8e3ed284fde0eff10305373e95228bbb60756e742e65649052f1dfd67df95d40`).
Skriptet er `analyse/drift/halvt_snapshot.py`, utskriften
`analyse/drift/halvt_snapshot.txt`.

Mot snapshotet 2026-09-28 gir den hele kroppen 628 changelog-rader, den
halve 1683. **532 lokaliteter blir «borte» bare med den halve kroppen**
(534 mot 2), og **0 blir «endret»** uten også å være det med den hele: de
294 endringene er en delmengde av den hele kroppens 599. Kommer uka etter
hel, står **alle 532 som «ny»** (1378 rader). Ingen av dem treffer en
signalregel, og sjøtemperatur er en måleserie, så nettstedet viser dem
ikke som hendelser i dag. Tidsaksen ville lest dem.

I ARKIVET: 0 falske hendelser etter stoppregelen. Hele `data/raw/` ble
lest; de eneste snapshotene med under 90 % av entitetene foran og minst
90 % etter er to år i `eierskap_historikk` (2017 og 2021), en årsserie
med nye entiteter hvert år. Ingen av de 86 entitetene som ble «borte»
der, kom tilbake som «ny» året etter.
*Feil hvis:* `diff.compare` mot 2026-09-28 gir et annet antall
lokaliteter med `borte` for den halve kroppen enn 534.

**0c. Linjer uten MMSI.** EKSTERN: timeregnskapene ligger på kystvakt-1,
ikke i arkivet. sha256 over stien og sha256 for hver av de 272 filene:
`83d54f8c3ae51152591836060493205c3d28319a7012d2e82b997e799adc2bc7`.
Skriptet er `analyse/drift/mmsi_andel.py`, utskriften
`analyse/drift/mmsi_andel.txt`.

bw: 136 timer fra 2026-10-28T16Z til 2026-11-03T07Z, alle med meldinger
(74 459 til 957 333 i timen). Høyeste andel uten MMSI er 0,0013 % (1 av
74 459 i den første timen); i 132 av timene er den 0. Regelen gir **1 %**.
5632: alle 136 timene er tomme, så det finnes ingen fordeling å bygge en
grense på. 5632 får ingen grense i punkt 6; den tomme kilden er allerede
rød i tilsynet etter et døgn (`AIS_TOM_FEIL`).
*Feil hvis:* et timeregnskap for bw i perioden har `uten_mmsi` over 1 %
av `meldinger`.

**0d. Luseinnkomsten.** MÅLT, holdt mot kroppene med sha256 i
`analyse/drift/luseinnkomst_ned.txt` (skriptet
`analyse/drift/luseinnkomst_ned.py`). 12 uker har 2–3 hentinger hver,
og i ingen av dem går antallet lokaliteter ned. Uke N til N−4 er bare
hentet i ett tidsrom, 02.11.2026 13.14–19.24 UTC; de sju eldre ukene er
hentet to ganger med opptil 75 døgn imellom (2016-10-10: 1 674 i august
og 1 674 i november). Regelen i punkt 9 bygges, men grunnlaget er én
kveld for de ukene den gjelder.
*Feil hvis:* en uke i `lusetall-innkomst/` har en henting med færre
lokaliteter enn hentingen før.

## Etterskrift 03.11.2026: kroppssjekken etter rettingen

Teksten over er ikke endret. Kroppssjekken er kjørt på nytt mot koden
etter økt 3b, punkt 1–9, med de samme fire kroppene:
`.venv/bin/python analyse/drift/kroppssjekk.py --med-arkiv`, utskriften i
`analyse/drift/kroppssjekk.etter.txt` (kroppssjekk.txt er 02.11.2026 og
står uendret). Skriptet skiller nå `lagret` (i serien) fra `karantene`
(`data/arkiv/<mappe>/karantene*/`, core/karantene.py). Med `--med-arkiv`
kjøres vilkar, havbruksfond, auksjon og luseinnkomst også med en kopi av
jobbens egne mapper i arkivet, så reglene som sammenligner med forrige
kropp, har en forrige kropp.

### De fire kroppene, før og etter

Hver celle er «02.11 → 03.11». Alle radene er MÅLBAR: konstruerte kropper
gjennom jobbens egen kode, som i tabellen over.

| Jobb | Merke | Feilside | Tom liste / tom kropp | Halv kropp |
|---|---|---|---|---|
| vilkar | MÅLBAR | 5 lagret, exit 0 → 5 i karantene, exit 1 | 5 lagret, exit 0 → 5 i karantene, exit 1 | 5 lagret, exit 0 → 5 i karantene, exit 1: 677 tegn, under minstelengden 740, og med arkivet under halvparten av forrige versjon |
| havbruksfond (`--daglig`) | MÅLBAR | lagret, exit 0 → karantene, exit 1 | lagret, exit 0 → karantene, exit 1 | lagret, exit 0 → lagret, exit 0: den halve siden nevner fondet |
| lytterne (bw, 5632) | MÅLBAR | lagret → lagret, urørt med vilje; tilsynet rødt når en bw-time har over 1 % linjer uten MMSI | som feilsiden | som feilsiden |
| auksjon | MÅLBAR | lagret, exit 1 → lagret, exit 1: HTML, fanget av tolkingen | lagret, exit 1 / exit 0 → karantene, exit 1 | lagret, exit 1 → lagret, exit 1 |
| ais-manifest | MÅLBAR | stoppet, exit 1 → karantene, exit 1 | stoppet → karantene, exit 1 | stoppet → karantene, exit 1; tomme felt: status overskrevet, exit 0 → karantene, forrige status står, exit 1 |
| samle (sjøtemperatur) | MÅLBAR | ok med 0 rader → Kolonnefeil, kilden feiler | ok med 0 rader → Kolonnefeil, kilden feiler | 1 355 rader, 532 lokaliteter «borte» → 1 355 rader, snapshot merket ufullstendig, 0 «borte» |
| samle (eierskap) | MÅLBAR | feiler → feiler | tom liste: ok med 0 rader → Mistenkt, 1 i karantene, kilden feiler | feiler → feiler |
| daglig (eierskap) | MÅLBAR | akvakultur feiler, exit 1 → uendret | tom liste: eierskap lagret 57 B → 1 i karantene, exit 1 | feiler → feiler |
| luseinnkomst | MÅLBAR | feiler, ingenting lagret → uendret | tom liste: feiler → 5 i karantene, exit 1; tom kropp: uendret | feiler, ingenting lagret → uendret |

Det halve snapshotet er i tillegg kjørt gjennom `run.main()` selv,
`analyse/drift/halvt_snapshot_etter.py` og `halvt_snapshot_etter.txt`
(MÅLBAR, falsk transport, kopi av datamappa): uka med den halve kroppen
skrives med `ufullstendig` «ja» og 0 «borte» (var 1 376 rader for 534
lokaliteter i 0b). Uka etter, hel, gir 9 «ny» (var 1 378 rader for 532),
og 305 endringer, 9 nye felt og 12 borte mot 2026-09-28 for lokalitetene
den halve kroppen manglet — de samme den hele kroppen har mot den uka.

### Arkivets egne kropper mot de nye reglene

`analyse/drift/arkivet_mot_reglene.py`, utskriften i
`analyse/drift/arkivet_mot_reglene.txt`. Hver regel med jobbens egen
kode, mot hver kropp i arkivet den gjelder for, i `raw.orden()`; der
regelen sammenligner med forrige kropp, er forrige den som ligger foran.
sha256 er over (sti, sha256 av den utpakkede kroppen) for hver kropp,
sortert som i utskriften.

| Jobb | Merke | Kropper | I karantene | sha256 over grunnlaget |
|---|---|---|---|---|
| vilkar, `vilkar-*/` | MÅLT | 11 | 0 | `c7bef67bc357210da183568be2fc3c864cfcb25b26a577167711f968d92da748` |
| havbruksfond, sidene i `havbruksfondet/` | MÅLT | 6 | 0 | `c711393391083cf280cd92fa964b16a4b0266be3ad14241c887aecb58b650083` |
| auksjon, `auksjon/` | MÅLT | 94 | 0 | `7f8e7356ecec5372e1786dcd2d2b2993aed48ad4ec00f82990e9322e43026d68` |
| luseinnkomst, `lusetall-innkomst/` | MÅLT | 13 | 0 | `1d5ad70236f45d1d9c12591fcf835a9d1c2f24415b39745487ee27cf12298974` |
| eierskap, `eierskap/` | MÅLT | 24 | 0 | `22e62db6ddc89e1f2988ff35956d5cd3ca43926a28dc770c1f193a5e61d484b5` |
| sjøtemperatur, `sjotemperatur/` | MÅLT | 771 | 0 | `f643c02d4fc755d8aa9cc7b4a09322e797b5c04d6cc13a885da7c39cab9dd84a` |
| ais-manifest, `data/ais/status.json` i git | MÅLBAR | 3 | 0 | `35d89af4143a7f87a753b123d3261b777f321b81dd846dd3a285cf2e6559b934` |

Statusene er MÅLBAR og ikke MÅLT: de ligger i git, ikke i arkivet.
*Feil hvis:* en av kroppene i tabellen gir en grunn når regelen kjøres
mot den, eller antallet kropper i en av mappene er et annet.

### Det som ikke er rettet

* **En HTML-kropp som er feil**, slipper gjennom auksjonens kroppssjekk
  (feilsiden og den halve kroppen er lagret) og fanges som før av
  tolkingen, rødt. Regelen er den F1.3 ba om: tom kropp og kropp uten
  `<html`.
* **Den halve havbruksfondsiden** nevner fondet og lagres. Ordet skiller
  en feilside fra siden, ikke en halv side fra en hel.
* **En kropp som ikke er JSON**, feiler inne i kildens `fetch()` (samle,
  daglig, luseinnkomst) før noen har den, og går tapt som før. Det samme
  gjelder en utlevering workflowen avviser før `ais_manifest.py`.
* **ais-manifest.yml committer bare når skrivesteget lyktes.** En kropp
  `ais_manifest.py` legger i karantene, blir derfor liggende på runneren
  til Commit-steget kjører også når skriptet er rødt. Det er en
  workflow-endring.
* **Tilsynets MMSI-grense virker først når kystvakt/utlevering.py fra
  03.11.2026 er installert** på kystvakt-1. Inntil den er byttet, er
  tilsynet rødt med at tallene mangler.
* **En uke med bare et ufullstendig snapshot har fortsatt `sist_ok`**,
  så tirsdagens gjenkjøring prøver ikke på nytt.

**Rettelse samme dag, etter kontrolløren** (én kjøring, tre av tre
trukne påstander i tabellen over stemte). Teksten over er ikke endret.
«sortert som i utskriften» om sha256 over grunnlaget er upresist:
hashen er over én linje per kropp, `<sti fra data/arkiv/> <sha256>` og
linjeskift, i den rekkefølgen skriptet leser kroppene — partene i
`SIDER`-rekkefølgen i arkiver_vilkar.py for vilkar, og `raw.orden()`
innenfor hver mappe. Kontrolløren fant formatet ved å prøve; alfabetisk
rekkefølge for vilkar gir en annen hash.

## Etterskrift 03.11.2026, kveld: tre av punktene som ikke var rettet

Teksten over er ikke endret. Tre av punktene under «Det som ikke er
rettet» er rettet samme kveld:

* **En uke med bare et ufullstendig snapshot får ikke lenger `sist_ok`**
  (kodrepoet `98a98c9`). Steg 2b i run.py henter på nytt en dato som bare
  ligger som ufullstendige snapshots, og det merkede blir stående ved
  siden av det nye. For en uke med begge er det hele snapshotet det som
  gjelder for diff og changelog (`snapshot.gjeldende`). Gjennom
  `run.main()` uten `--tving` (`analyse/drift/gjenkjoring_etter.py`,
  utskriften i `gjenkjoring_etter.txt`, MÅLBAR): halv kropp mandag gir
  `2026-10-05` merket «ja» og uendret `sist_ok`; hel kropp tirsdag gir
  `2026-10-05.2` merket «nei», `sist_ok` tirsdag, og changeloggen for uka
  blir den hele kroppens 628 rader mot 2026-09-28. Gir også gjenkjøringen
  et ufullstendig snapshot, er tilsynet rødt fra onsdag. Ingen terskel er
  endret (prøven i datarepoet, `e4e6d68`).
* **kystvakt/utlevering.py er installert på kystvakt-1**: sha256
  `e6116000ade275347a59ef228bfa1535cd397b70cee3bcea6777a2a0906e97a7` ut,
  `ddc024051e5652f513694434a76becdf469bc63714e717e82c1dff8689318d7f` inn,
  samme eier og rettigheter, og kommandoene står i RUNBOOK (`43f1df2`).
  «AIS-manifest» startet for hånd (run 41693343894) var grønn og
  leverte `per_time` for alle 24 timene i bw. Tilsynet startet for hånd
  (run 41693500788) er ikke lenger rødt for manglende tall, bare for
  5632s tomme døgn, som er ventet.
* **ais-manifest.yml committer også når skrivesteget er rødt**
  (datarepoet `90d8706`), så en utlevering i karantene blir ikke
  liggende igjen på runneren. Jobben ender fortsatt rød.

**Etter kontrolløren** (én kjøring til, tre av tre trukne påstander
stemte). Tabellen «Arkivets egne kropper mot de nye reglene» er målt mot
arkivet slik det sto på datarepoets `81e9d84` (03.11.2026 02.39 UTC),
før dagens fangster. `lusetall-innkomst/` har fått åtte kropper siden
(`cb14088`, `9ac6ebc`), og hashen over grunnlaget treffer de 13 som lå
der. «Feil hvis» gjelder arkivet på den commiten.
