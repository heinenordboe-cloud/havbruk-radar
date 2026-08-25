# Biomasse — verifiseringsnotat og kildespesifikasjon

Alt i dette notatet er **målt** mot levende tjeneste 25.08.2026 med
`curl` og `python3`, eller mot en Wayback-kopi av den samme fila hentet
07.08.2024. Der noe bare er lest og ikke verifisert, står det uttrykkelig.

**Kilde: Fiskeridirektoratet.** Dataene er lisensiert under NLOD, og
attribusjonen er et vilkår — se punkt 10.

---

## 1. Endepunktet — én statisk fil, ikke et API

```
https://register.fiskeridir.no/biomassestatistikk/
    BIOSTAT-LAKS-OMR/biostat-total-omr.csv
```

Målt 25.08.2026:

| | |
|---|---|
| Størrelse | 650 588 bytes (650 585 uten BOM) |
| `Last-Modified` | Thu, 20 Aug 2026 04:38:18 GMT |
| `Content-Type` | `text/csv` (uten charset) |
| Rader | 5199 |
| Kolonner | 23 |
| Skilletegn | `;` |
| Tegnsett | UTF-8 med BOM |
| Linjeskift | CRLF (5200 `\r` i svaret) |
| Autentisering | ingen |

Det finnes **ingen spørrestreng, ingen paginering, ingen delta og ingen
API-vert**. `api.fiskeridir.no` svarer 404. Hver nedlasting er hele
serien. Det er ikke en begrensning å arbeide rundt — det er egenskapen
som gjør revisjonshistorikken bevarbar (punkt 5).

XLSX- og JSON-varianter finnes på samme sti. **JSON-varianten har feil
metadata**: `Metadata.Tittel` sier «Utsett av rensefisk pr. lokalitet
(fylke)», og `Forklaring`-blokken beskriver `LOKNR` og `UTSETT_1000STK`
— felter som ikke finnes i `Data`. Selve dataene er riktige; blokken er
kopiert fra feil fil. Fylkesvariantens metadata er korrekte. Kilden leser
CSV.

---

## 2. Kolonnene, og hvilke vi leser

```
ÅR;MÅNED_KODE;MÅNED;PO_KODE;PO_NAVN;ARTSID;UTSETTSÅR;BEHFISK_STK;
BIOMASSE_KG;UTSETT_SMOLT_STK;UTSETT_SMOLT_STK_MINDRE_ENN_500G;
FORFORBRUK_KG;UTTAK_STK;UTTAK_KG;UTTAK_SLØYD_KG;UTTAK_HODEKAPPET_KG;
UTTAK_RUNDVEKT_KG;DØDFISK_STK;UTKAST_STK;RØMMING_STK;ANDRE_STK;
ANDRE_NY_STK;TELLEFEIL_STK
```

Definisjonene er tjenestens egne, hentet fra `Forklaring`-blokken i
**fylkesvarianten** (`biostat-total-flk.json`), som er den korrekte:

> `BEHFISK_STK` — «Beholdning av fisk ved månedslutt, målt i antall stk.»
>
> `BIOMASSE_KG` — «Biomasse ved månedslutt. Biomasse er definert som
> antall fisk multiplisert med gjennomsnittlig vekt.»
>
> `UTSETTSÅR` — «Årstall fisken ble satt ut i sjøen som smolt.»
>
> `DØDFISK_STK` — «Tap av fisk i løpet av måneden, registrert som
> dødfisk.»

**Antall fisk er det innrapporterte; biomassen er det avledede.** Det er
motsatt vei av hva navnet «biomassestatistikk» antyder, og det er grunnen
til at denne kilden finnes: Stien mfl. 2005 sitt `N_fisk` kan leses
direkte. Ingen omregning med snittvekt, ingen tilnærming å dokumentere.

Kilden leser tolv kolonner og emitter ni målte felter per
produksjonsområde:

| felt | kolonne |
|---|---|
| `beholdning_antall` | `BEHFISK_STK`, summert over art og utsettsår |
| `beholdning_antall_laks` | samme, bare `LAKS` |
| `beholdning_antall_regnbueorret` | samme, bare `REGNBUEØRRET` |
| `biomasse_kg` | `BIOMASSE_KG` |
| `utsett_smolt_antall` | `UTSETT_SMOLT_STK` |
| `uttak_antall` | `UTTAK_STK` |
| `dodfisk_antall` | `DØDFISK_STK` |
| `romming_antall` | `RØMMING_STK` |
| `forforbruk_kg` | `FORFORBRUK_KG` |

Pluss ett avledet felt, `andel_av_beholdning` — se punkt 6.

**`UTSETTSÅR` summeres bort.** Den er ekte informasjon (fiskens
generasjon), men ville ganget feltantallet med fem-seks og gitt kohorter
som oppstår og forsvinner — altså «ny»/«borte» i changeloggen hver gang
en generasjon slaktes ut. De øvrige ni kolonnene leses ikke. Begge deler
er en **re-parse** og ikke tapt historikk: hele fila arkiveres for hver
kjøring.

Kolonner vi ikke leser står ikke i `PAAKREVDE`, med vilje: skjemaet
vokste fra 21 til 23 kolonner i 2024 (`ANDRE_NY_STK` og `TELLEFEIL_STK`,
begge udokumenterte i tjenestens `Forklaring`), og en kolonne til skal
ikke kunne felle en måned.

Målt over alle 5199 rader, i de kolonnene vi leser: **null tomme celler,
null desimalkomma, null negative verdier.** `BIOMASSE_KG` har maks tre
desimaler; de øvrige er heltall. (`TELLEFEIL_STK` er negativ i 1816
rader, men den leses ikke.)

---

## 3. Historisk dybde — 2017-10, og ikke tidligere

106 måneder, **2017-10 til 2026-07, uten hull**. Serien starter der fordi
trafikklyssystemet og produksjonsområdene ble innført 15.10.2017. Det
finnes ingen eldre PO-tall — verken her eller andre steder.

Dekning på det nivået analysen bruker: **1339 av 1339 forventede
PO×måned-celler for 2018–2026. Null manglende.** Alle tretten
produksjonsområdene er til stede i hver eneste av de 106 månedene, og
`(null)`-kategorien likeså.

### Fylkesvarianten — notert, ikke bygget

`BIOSTAT-LAKS-FLK/biostat-total-flk.csv` har samme kolonner med `FYLKE`
i stedet for `PO_KODE`: 8485 rader, **2005-01 til 2026-07, 259 måneder
uten hull**.

Den er ikke bygget, og begrensningen er grunnen: **fylke er ikke
produksjonsområde**, og fylkesgrensene flytter seg inne i serien. Målt:
kolonnen inneholder både `Troms og Finnmark` og `Troms`/`Finnmark` på
hver sin side av regionreformen, pluss `Uoppgitt`. En serie som skifter
geografisk inndeling midtveis kan ikke sammenlignes med seg selv uten en
kartlegging ingen har laget. Skal den inn, må den kartleggingen bygges og
dokumenteres først.

---

## 4. Frekvens og etterslep — dette er MÅNEDER

Innrapporteringsfristen er den 7. i påfølgende måned
(akvakulturdriftsforskriften § 44, via Altinn). Fila publiseres på nytt
**den 20. hver måned** — bekreftet både av sidetekst («Statistikken blir
oppdatert den 20.») og av `Last-Modified`. Måned M er altså først synlig
~50 dager etter at M begynte.

Etterslepet her er ikke lusetalls N-4. Det er ikke fire uker, og det er
ikke valgt av samme grunn.

### `maaneder_etterslep = 4`

Publiseringsplanen alene ville tilsagt to. Fire er valgt fordi det ikke
er publiseringen som er problemet, men **revisjonen** — og revisjonen har
en målbar avklingingskurve.

Målt ved å krysse Wayback-kopien fra 07.08.2024 mot dagens fil, 3973
felles rader, gruppert etter hvor gammel måneden var da 2024-kopien ble
laget:

| alder ved hentingen | andel rader som **senere** ble revidert |
|---|---|
| 0 mnd (ferskeste måned) | **28,8 %** |
| 1 mnd | 19,2 % |
| 2 mnd | 11,3 % |
| 3 mnd | 10,4 % |
| 4–80 mnd | ~8–15 %, flatt |

**Kurven flater ut ved alder 2.** Det som gjenstår — omtrent 11 % — er
ikke etterslep som setter seg; det er permanent omklassifisering som
ingen ventetid fjerner (punkt 5). Å vente lenger enn til alder 2 kjøper
altså ingenting.

Fire GARANTERER alder ≥ 2 uansett hvilken dag i måneden jobben kjører:

- kjører vi den 20. eller senere, er ferskeste publiserte måned
  kjøremåneden minus 1, og måneden vi skriver har alder 3
- kjører vi før den 20., er ferskeste publiserte måned kjøremåneden
  minus 2, og måneden vi skriver har alder 2

Tre ville gitt alder 1 — 19,2 % — omtrent halvparten av dagene. Grensen
skal ikke avhenge av hvilken ukedag cron traff.
`test_etterslepet_gir_alder_minst_to_uansett_dag_i_maaneden` håndhever
det over hver dag i to år.

Regnestykket er **vårt**. Fila vet selv hvilke måneder den bærer, og
`parse()` kaster hvis måneden ikke er der. Det er samme prinsipp som
F13: når motparten kan svare selv, er svaret dens bedre enn regnestykket
ditt. Regnestykket velger måneden, fila bekrefter den.

### `min_dager_mellom = 7` for en månedlig kilde

Dette ser feil ut og er det ikke. Sju betyr ikke «fila endrer seg hver
uke» — den endrer seg den 20. hver måned. Sju betyr **«tilby kilden til
kjøringen hver uke, og la `finnes_allerede()` avgjøre»**.

Grunnen er at `min_dager_mellom` teller DAGER SIDEN SIST, mens målet er
en KALENDERMÅNED. De to glir fra hverandre, og glidningen lager hull: med
28 dager og en ukentlig cron kan et vellykket treff sent i mars gjøre
kilden forfalt 28. april, som en cron på mandager kan bomme på — og da
hopper `gjelder_for()` fra én måned til den neste uten at måneden imellom
noen gang blir skrevet. Med 31 dager er hullet enda lettere å treffe.

Med sju er kilden forfalt hver uke, `gjelder_for()` peker på samme måned
i tre–fire uker på rad, og steg 2b i `run.py` hopper over den med
`[har] biomasse …`. Det koster ingenting: **2b kjører før hentingen**, så
en måned som ligger skrevet bruker ikke et nedlastingskall.

Bieffekten er ønsket og viktig: den ene kjøringen per måned som faktisk
henter, skjer i løpet av månedens første sju dager — altså alltid før den
20. **Hver publisering blir derfor arkivert nøyaktig én gang.** Ingen
publisering hoppes over, ingen arkiveres to ganger.

---

## 5. Revisjon — fortiden ligger ikke fast her

Dette er en kilde av et slag repoet ikke har hatt før, og det er den
egenskapen alt annet i kilden er formet av.

Registrene vi ellers henter fra sier hva som gjelder **nå**. Denne sier
hva Fiskeridirektoratet **i dag mener gjaldt i 2017** — og den meningen
endrer seg.

### Målingen

Wayback-kopien fra 07.08.2024 mot dagens fil, 3973 felles rader
(nøkkel: år, måned, PO, art, utsettsår):

| | |
|---|---|
| Rader endret | **490 (12,3 %)** |
| Berørte år | 2017 til 2024 — **hele serien** |
| Endring i sum `BEHFISK_STK` | **+0,006 %** |

Summen står praktisk talt stille mens 12,3 % av radene beveger seg. Det
er ikke nye innrapporteringer. De største utslagene kommer i **speilpar**:

```
2017-10  PO 5      REGNBUEØRRET  2017:  2 553 307  ->  1 130 530
2017-10  (null)    REGNBUEØRRET  2017:    310 173  ->  1 732 950
                                          ^^^^^^^^^^^^^^^^^^^^^^^
                              nøyaktig 1 422 777 fisk, begge veier
```

**Lokaliteter blir omklassifisert mellom produksjonsområder i ettertid.**

Aggregert til PO×år, som er nivået analysen bruker (2018–2023, 78 celler):

| | |
|---|---|
| Celler endret | 15 av 78 |
| Endret mer enn 1 % | 9 |
| Største utslag | PO 5 i 2018: 256,5 → 246,5 mill. fisk (−3,90 %) |
| Median endring | 0,000 % |

De fleste cellene står stille. PO 5 og PO 8 flytter seg systematisk.

### Hva det betyr for innsamlingen

**To snapshots som er uenige om 2018 er ikke en feil.** De sier hva
kilden sa på hver sin dato, og begge er sanne utsagn. Derav:

- `observed_at` = **siste dag i måneden**. Ikke en pyntedato:
  `BEHFISK_STK` er beholdning ved *månedslutt*, og strømmene (fôr, uttak,
  dødfisk, rømming) er summert over måneden og dermed også ferdige da.
  `maaned_av()` kaster på enhver annen dato.
- `fetched_at` = kjøredatoen, satt av kjernen.
- **Ingen rad skrives om.** Fila for en måned skrives én gang.

### Hvordan revisjonshistorikken bevares

`fetch()` returnerer **hele fila**, ikke måneden vi skal skrive. Kjernen
arkiverer det `fetch()` returnerer (`runner.run_all`: fetch → arkivér →
parse), så hver kjøring legger igjen en komplett kopi av serien slik den
så ut den dagen, i `data/arkiv/biomasse/<måned>.txt.gz`.

Sammen med `min_dager_mellom = 7` (punkt 4) gir det **nøyaktig én
arkivert kopi per publisering**, for alltid. Det er det eneste stedet
historikken over hva Fiskeridirektoratet *sa om fortiden* finnes — hos
dem forsvinner forrige versjon den 20. hver måned.

Lese den tilbake:

```bash
zcat data/arkiv/biomasse/2026-04-30.txt.gz > gammel.csv
zcat data/arkiv/biomasse/2026-08-31.txt.gz > ny.csv
# nøkkel: ÅR;MÅNED_KODE;PO_KODE;ARTSID;UTSETTSÅR
```

### Det changeloggen IKKE kan si — og hvorfor

`diff.compare()` sammenligner et snapshot mot det **forrige etter dato**.
For biomasse betyr det at mars sammenlignes med februar, som er riktig og
nyttig: det er industriens faktiske bevegelse.

Men «måned M ble revidert» er ikke den sammenligningen. Det er to utsagn
om **samme** tidspunkt, gjort på hver sin `fetched_at`, og changeloggen
har ingen akse for det. Å legge den til ville krevd endringer i
`core/diff.py` og `CHANGE_SCHEMA` — altså en endring i `core/` for å
legge til en kilde, som CLAUDE.md regel 1 uttrykkelig forbyr uten at
eieren har bestemt seg.

**Derfor er den ikke bygget.** Ingenting går tapt i mellomtiden: hele
fila ligger arkivert for hver publisering, så påstanden kan alltid
utledes i ettertid. Se punkt 11 for hva en slik utvidelse ville kreve.

---

## 6. `(null)`-kategorien — den lagres, den filtreres ikke bort

0,96–4,57 % av all fisk ligger på rader der `PO_KODE` er `(null)`.
Andelen per måned, målt:

| måned | andel av fisk | andel av biomasse |
|---|---|---|
| 2017-10 | 4,57 % | 4,79 % |
| 2018-01 | 4,21 % | 4,52 % |
| 2020-01 | 2,72 % | 2,95 % |
| 2022-01 | 1,54 % | 2,25 % |
| 2024-01 | 1,23 % | 1,64 % |
| 2026-01 | 3,45 % | 3,00 % |
| 2026-07 | 3,33 % | 3,69 % |

Laveste måned 0,96 %, høyeste 4,57 %.

**Den opplagte forklaringen — settefisk og landanlegg — holder ikke.**
Snittvekten i `(null)`-radene er **2,02 kg** mot **1,86 kg** i
PO-radene. Det er voksen matfisk uten produksjonsområde.
**Årsaken er ukjent**, og den skal stå som ukjent til noen har spurt
Fiskeridirektoratet. Dette er en antakelse vi ikke gjør, ikke en
antakelse vi gjør forsiktig.

Radene lagres som entiteten **`uten_po`** (`entity_name`:
«Uten produksjonsområde»). De filtreres ikke bort, fordi en nevner som
forsvinner stille er verre enn en nevner som er rar: en analyse som
summerer PO 1–13 og kaller det «Norge» tar systematisk feil med opptil
4,6 %, og ville ikke merket det.

### `andel_av_beholdning`

Feltet er **avledet** — entitetens `beholdning_antall` delt på summen
over alle fjorten — og lagres likevel, av to grunner:

1. Det er nevneren. En konsument som har droppet `uten_po` får da et tall
   som ikke stemmer med vårt, i stedet for et tall som *ser riktig ut*.
   Samme begrunnelse som CLAUDE.md 1b-3: verdien som avgjør hva dataene
   BETYR, lagres sammen med dem.
2. Det emitteres for **hver** entitet, ikke bare for `uten_po`. Et felt
   med én rad har per konstruksjon null minoritet, og
   `health._vurder_innhold()` ville lest det som et dødt felt og fyrt
   hver måned i det uendelige. Fjorten rader med fjorten ulike andeler
   gir minoritet 13.

---

## 7. En art som mangler — null, ikke ingenting

903 av 1484 PO-måneder har bare `LAKS`. Ingen har bare `REGNBUEØRRET`.
Da emitteres `beholdning_antall_regnbueorret = 0`.

Det er en **tolkning**, og den er begrunnet i en måling: fila inneholder
**250 rader med `BEHFISK_STK = 0`** — eksplisitte nuller for kohorter
som er slaktet helt ut i løpet av måneden. Eksempel fra 2017-10, PO 12,
`LAKS`, utsettsår 2015: null beholdning, 336 597 uttak, 1460 dødfisk.

Registeret skriver altså nullen når kohorten finnes. En kohort som ikke
finnes i det hele tatt har ingen fisk, og null er det riktige svaret —
ikke «vet ikke».

Motsatt valg ville gitt et felt som forsvinner og kommer tilbake alt
etter hvilke arter som står i sjøen, og feltvakten i `health.py` er
bygget for å reagere på nettopp det.

---

## 8. Koblingen mot det vi har

`prodomraade_kode` i akvakultursnapshotene har verdiene `'1'`…`'13'` —
strenger uten padding, målt mot siste snapshot 25.08.2026. **Identisk med
dagens `PO_KODE`.** Ingen mapping, ingen navnematching.

Men koden har byttet format: **nullpadet (`01`) i 2024-kopien, upadet
(`1`) i dag.** Uten normalisering ville PO 1 vært to entiteter, og hver
av dem sett ut som «ny» den dagen formatet snudde. `_po()` normaliserer,
og **kaster** på en form den ikke kjenner — et stille fjortende
produksjonsområde ville lagt seg ved siden av de tretten og telt med i
nevneren uten at noen så det.

Fasiten `analyse/fasit/ekspertgruppen-po-kategori.csv` er nøklet på
`(po, aar)`, og `per_po_aar()` aggregerer allerede dit. Månedsoppløsning
er **finere enn analysen trenger**.

### Forbeholdet Stien-proxyen må bære

Stien-formelen er per enhet: `N_fisk × N_hunnlus`. Vi får `N_fisk` bare
på PO-nivå, mens `N_hunnlus` finnes per lokalitet. Da er

```
Σᵢ (N_fiskᵢ × lusᵢ)  ≠  N_fisk_PO × middel(lus)
```

Forskjellen er **kovariansen mellom anleggsstørrelse og lusenivå innen
produksjonsområdet**. Har store anlegg systematisk andre lusetall enn
små, er PO-produktet skjevt — og fortegnet på skjevheten er ikke kjent.

Dette er en dokumenterbar tilnærming, ikke en skjult en, og den skal stå
i enhver framstilling som bruker proxyen. Den kan ikke fjernes med bedre
kode: den fjernes bare av biomasse per lokalitet, som ikke publiseres
(punkt 9).

---

## 9. Per lokalitet — finnes ikke åpent

Undersøkt 25.08.2026:

- **ArcGIS «Biomasse»**
  (`gis.fiskeridir.no/server/rest/services/Yggdrasil/Biomasse/FeatureServer/0`).
  Felter: `loknr, navn, status_lokalitet, siste_rapport, har_fisk, art,
  kapasitet_lok, aktuell_kapasitet, plassering, vannmiljo, fylke,
  kommune, produksjonsomraade`. **Ingen tonnasje, intet antall**, og bare
  siste rapport — ingen historikk.
- **`Yggdrasil/Produksjonsintensitet`.** Gjennomsnittlig stående biomasse
  i **tonn/km² per vannforekomst**, 2015–2025 i 24-måneders bolker.
  Finere geografi enn PO, men tonnasje uten antall og et toårig glidende
  snitt. Ubrukelig til Stien.
- **`biostat-utsett2c-omr-rensef-lok.csv`** er den eneste åpne fila med
  `LOKNR` (10 583 rader, 2019–2025, avsluttet 01.01.2026, bare utsett av
  rensefisk). Den viser at Fiskeridirektoratet *kan* publisere på
  lokalitetsnivå; de gjør det bare ikke for laksebiomasse.

`portal.fiskeridir.no/nedlasting` redirigerer til en ArcGIS-portalside.
Ingen åpen vei til biomasse per lokalitet ble funnet.

**Ikke verifisert:** hvorfor. Om det er taushetsplikt etter fvl. § 13
(biomasse per lokalitet er konkurransesensitivt) eller bare
publiseringspraksis, er ikke fastslått. Det skal ikke gjettes.

---

## 10. Lisens og attribusjon

NLOD — Norsk lisens for offentlige data. Fra
`fiskeridir.no/statistikk-tall-og-analyse/lisens-for-bruk-av-fiskeridirektoratets-data`:

> «Den som tar i bruk data fra Fiskeridirektoratet godtar automatisk
> lisensen.»

**Ingen registrering, ingen avtale, ingen søknad, ingen nøkkel.**

Vilkåret er attribusjon. Godkjente former er «Kilde:
Fiskeridirektoratet», «Kilde rådata: Fiskeridirektoratet» eller «Kilde
for rådata som vi har benyttet i vår sammenstilling:
Fiskeridirektoratet». Attribusjonen skal ikke fremstilles som om
Fiskeridirektoratet anbefaler eller går god for vår sammenstilling.

**Enhver visning, rapport eller publisering som bruker disse tallene må
bære attribusjonen.** Det er et lisensvilkår, ikke en høflighet.

---

## 11. Det som IKKE er bygget

**Revisjon inn i changeloggen.** Se punkt 5. Krever en
sammenligningsakse `core/diff.py` ikke har (samme `observed_at`, ulik
`fetched_at`). Ville trolig kreve: et nytt `change_type`
(`"revidert"`), et felt for hvilken `fetched_at` det sammenlignes mot i
`CHANGE_SCHEMA`, og en variant av `snapshot.previous()` som finner
forrige *versjon av samme dato* i stedet for forrige dato. Det er en
utvidelse av kontrakten, og eieren avgjør den.

**Automatisk skriving av reviderte måneder som `.2`-snapshots.**
Mekanikken finnes allerede (`snapshot._ledig_sti` løser kollisjon med
løpenummer, `previous()` velger høyeste), men `run.py` skriver ett
snapshot per kilde per kjøring, så det ville krevd en egen
revisjonskjøring. Ikke bygget før changeloggspørsmålet over er avgjort —
snapshots uten en changelog som kan forklare dem er halve svaret.

**Fylkesvarianten.** Punkt 3.

**`UTSETTSÅR` som egen akse.** Punkt 2. Re-parse av arkivet når den
trengs.

**Årsaken til `(null)`.** Punkt 6. Krever et spørsmål til
Fiskeridirektoratet, ikke mer kode.
