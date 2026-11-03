# Måling: nye kilder som ikke kan hentes i ettertid

**Dato:** 03.11.2026, kallene 19.09–19.32 UTC (`fetched_at` i loggene).
**Spørsmålet:** For hver av seks kandidater (a–f): svarer den, hva sier
vilkåret, kan tilstanden på 01.09.2026 hentes i dag, hvor stor er en
kropp, og har kroppen personnavn som persondatafilteret ikke kan ta?
Prinsippet er fangst først, tolkning senere, og en kilde arkiveres bare
hvis den IKKE kan hentes bakover.

**Datagrunnlag:** alle kropper i `data/arkiv/maling-nye-kilder/` i
datarepoet, med fire logger som fører hvert kall (URL, metode, status,
headere, sha256, fil, `fetched_at`):

| logg | skript | kandidater |
|---|---|---|
| `2026-11-03.m1.logg.json` | `analyse/nye-kilder/m1_api.py` | a (lag 19), b, f |
| `2026-11-03.m1b.logg.json` | `analyse/nye-kilder/m1b_flater.py` | a (lag 80) |
| `2026-11-03.m1c.logg.json` | `analyse/nye-kilder/m1c_v2_stabil.py` | f (stabilitet) |
| `2026-11-03.m3.logg.json` | `analyse/nye-kilder/m3_web.py` | c, d, e |

Tallene er regnet av `analyse/nye-kilder/m2_api_analyse.py` og
`m4_web_analyse.py`, som bare leser arkivet og hasher hver kropp på nytt
mot loggen. Utskriftene står uendret i `m2_api_analyse.txt` og
`m4_web_analyse.txt` ved siden av.

Hashene er sha256 over den utpakkede kroppen i arkivet, feltet `sha256`
i loggene. For JSON er det svaret serialisert som `core.raw` gjør
(sortert på nøkkel), og det er ikke de samme bytene som kom over linja:
de står i `sha256_utpakket`. For `.bin.gz` er de to like. Under står
bare de 16 første tegnene; hele hashen står i loggene.

**Merkene** (definert i `docs/PROVENIENS-2026-09-11.md`): **MÅLT** holdt
mot en arkivert kropp med sha256; **MÅLBAR** avledet eller lest uten å
være holdt mot en kropp; **EKSTERN** hviler på en kropp som ikke er i
arkivet; **UBELAGT** ingen kropp sier det.

**To kropper er med vilje ikke arkivert.** RSS-strømmen fra iLaks har en
byline per sak og personnavn i titlene, og postene i søknadslagene har
søkers navn og organisasjonsnummer uten organisasjonsform (CLAUDE.md
regel 3). For begge fører loggen sha256 og tellinger, ikke innholdet.
Påstander om dem er EKSTERN. Ekspertgruppens og HIs rapportsider er
heller ikke arkivert, fordi vilkåret er uklart (se e).

## STOPP-regelen

Skrevet etter at kallene var gjort og før tabellene var regnet ut. Målingen
stopper og rapporterer i stedet for å bygge, for en kandidat, hvis

1. vilkåret ikke kan leses på en side som selv er arkivert eller kan
   arkiveres med `arkiver_vilkar.py`, eller sier at fangst krever avtale;
2. tilstanden på 01.09.2026 kan hentes i dag, med samme innhold som en
   kropp vi har fra den gang;
3. kroppen har personnavn i felt som `core/persondata.py` ikke kan
   filtrere (filteret arbeider på organisasjonsform, ikke på fritekst).

Den utløses for b, c, d og fire av fem sider i e. Se hver kandidat.

## Kortversjonen

| kandidat | svarer | kan hentes bakover | vilkår | persondata | bygget |
|---|---|---|---|---|---|
| a flatene | 200 | nei | NLOD (Fiskeridir.) | ingen personfelt | ja, `arkiver_flater.py` |
| b fiskehelse | 200 | **ja** | NLOD (BarentsWatch) | ingen | nei (regel 2) |
| c bransjemedia | iLaks 200, de tre andre uten RSS | delvis | forbudt (2) / UBELAGT (2) | byline og navn i titler | nei (regel 1 og 3) |
| d søknader | Fiskeridir. 200 | delvis | — | søkers navn uten organisasjonsform | nei, bare måling |
| e utgivelser | 200 / 403 / 405 | nei | CC BY 4.0 bare for regomr.geojson | ingen | ja, én side, `utgivelsesvakt.py` |
| f v2 | 200 | ja, men tolkningen kan skifte | NLOD (BarentsWatch) | ingen | ja, `arkiver_luseinnkomst.py --v2` |

## De tre sterkeste funnene

1. **F6.2: v1 og v2 er uenige om ILA og PD.** For hver av seks uker, hentet
   samme minutt fra begge endepunktene, har 26–28 lokaliteter ILA i bare
   det ene svaret og 53–56 PD i bare det ene. Lusetall, rapportert og
   brakklagt er like for alle 1777–1782 lokaliteter. Den dagen v1 slås
   av, endrer sykdomskolonnene seg uten at noe skjedde i sjøen.
2. **F1.2: flatelaget lar seg ikke spørre bakover, og sier det ikke.**
   `historicMoment` for 01.09.2026 ga byte for byte samme kropp som
   uten, med status 200. En spørring som ser ut til å virke, svarer om i
   dag.
3. **F3.1: to av fire bransjemedier forbyr fangsten uttrykkelig.**
   Fiskeribladet og Intrafish krever avtale for «skraping, crawling,
   indeksering, tekst/datautvinning».

Svakere: F1.4 (Wayback hadde ingen kopi av flatelaget) hviler på et
tomt svar fra en tjeneste som var nede deler av kvelden, og F5.3
(regjeringen.no) er ikke målt i det hele tatt.

---

## a. Arealene i Akvakulturregisteret

**F1.1 — Flatene med geometri ligger i lag 80, ikke 19. MÅLT.**
`fiskeridirWMS_akva/MapServer/19` (`flate_ihht_akvakulturregisteret`) har
1398 poster med `areal_m2`, og ingen av dem har geometri, også med
`returnGeometry=true` (`maling-nye-kilder/2026-11-03.2.json.gz`,
`0345f18838ff2669`). `FiskeridirWFS_akva/MapServer/80`
(`Flate_ihht_Akvakulturregisteret`) har 1372 flater med polygon, 1428
ringer og 9435 punkter, ett loknr per flate, og `exceededTransferLimit`
er ikke satt (`2026-11-03.28.json.gz`, `27982e4893d0d7c1`, 947 162 B
serialisert). Alle 1372 loknr i lag 80 finnes i lag 19; 26 i lag 19 har
ingen flate i lag 80. `copyrightText` er «Fiskeridirektoratet /
Akvakulturregister» i begge (`2026-11-03.json.gz`, `2026-11-03.27.json.gz`).
*Feil hvis:* en post i `2026-11-03.28.json.gz` mangler `geometry.rings`,
eller en post i `2026-11-03.2.json.gz` har `geometry`.

**F1.2 — Tilstanden på 01.09.2026 kan ikke hentes. MÅLT.** Lag 80 og 19
har `timeInfo`, `editingInfo` og `supportsQueryWithHistoricMoment` lik
`None`. Spørringen mot lag 80 med `historicMoment` lik 01.09.2026
12.00 UTC ga samme sha256 som uten (`27982e4893d0d7c1`, loggen
`m1b`, tredje kall); mot lag 19 ga den fem poster med attributter lik
dagens (`2026-11-03.3.json.gz`). Tjenesten ignorerer parameteren og
svarer 200.
*Feil hvis:* kall 3 i `2026-11-03.m1b.logg.json` har en annen sha256 enn
kall 2.

**F1.3 — Ingen ordningsstøy. MÅLT.** To hentinger av lag 80, 19.12.06 og
19.12.27 UTC, ga samme sha256, sortert på `loknr`. Det
samme for lag 19. Fangsten kan sammenligne på sha256 av kroppen.
*Feil hvis:* kall 2 og 3 i `m1b`-loggen har ulik sha256.

**F1.4 — Wayback hadde ingen kopi. MÅLT, svakt.** `archive.org/wayback/
available` for spørringen svarte `archived_snapshots: {}`
(`2026-11-03.4.json.gz`), og CDX for `MapServer/19*` svarte `[]`
(`2026-11-03.5.json.gz`). Internet Archive var «Temporarily Offline» for
et kall en time senere (ikke arkivert), så et tomt svar kan være en
tjeneste som svarer tomt, ikke et arkiv uten kopi. F1.2 bærer
konklusjonen alene.
*Feil hvis:* `2026-11-03.4.json.gz` har en nøkkel under `archived_snapshots`.

**F1.5 — Alle ti delte lokaliteter har en flate. MÅLT.** De ti
lokalitetene havbruksfondet deler over en kommunegrense
(MALING-HAVBRUKSFOND, «Delte lokaliteter») har hver nøyaktig én flate i
lag 80. Mot akvakulturkroppen fra den daglige fangsten samme dag
(`akvakultur/2026-11-03.daglig.json.gz`, `7a29fc77dfb88eb2`, 1784
lokaliteter) har 1371 en flate, og én flate har et loknr som ikke er i
den kroppen.
*Feil hvis:* en av de ti mangler blant `features[].attributes.loknr` i
`2026-11-03.28.json.gz`.

**F1.6 — Ingen personfelt. MÅLT.** Feltene er `loknr`, `navn`,
`lokalitet`, `status_lokalitet`, `plassering`, `vannmiljo`, `fylke`,
`kommune`, `areal_m2`, `objectid`, `globalid`, `st_area(shape)` og
`st_perimeter(shape)`. `navn` er lokalitetens navn, det samme som
`akvakultur` allerede henter hver uke; innehaver står ikke i laget, og
det finnes ingen organisasjonsform for filteret å virke på.
*Feil hvis:* `fields` i `2026-11-03.27.json.gz` har et felt for innehaver.

**Vilkår.** NLOD, Fiskeridirektoratets side, arkivert
`vilkar-fiskeridir/2026-11-02.bin.gz` (`021c8692f14104b1`). Rad i
LISENSKJEDE.md.

**Hvor ofte den endres:** ukjent. Én dag gir ingen endringsrate; fangsten
lagrer bare en ny kropp, så kostnaden er én kropp per endring.

**Bygget:** `arkiver_flater.py`, daglig, `data/arkiv/akvakultur-flater/`.

## b. Fiskehelsestatus per lokalitet hos BarentsWatch

**F2.1 — Uke 36/2026 i dag er lik innsamlingens på ILA og PD. MÅLT.**
v1-ukesvaret for uke 36 hentet 03.11.2026 (`2026-11-03.18.json.gz`,
`94ac7149d96f7030`) mot innsamlingens kropp for samme uke
(`lusetall/2026-08-31.json.gz`, `f8fe2cfb9bd2b17b`): 1777 felles
lokaliteter, `hasIla` ulik i 0 og `hasPd` ulik i 0 (16 med ILA og 46 med
PD i begge). Av alle 18 felt er disse ulike: `hasSalmonoids` i 4,
`isSlaughterHoldingCage` i 2, `avgAdultFemaleLice`, `hasReportedLice` og
`hasMechanicalRemoval` i 1. `hasSalmonoids` og `isSlaughterHoldingCage`
er lokalitetens tillatelser lagt på hver uke (MALING-LUSEINNKOMST F1.4),
ikke ukesobservasjoner. Hvorfor de tre andre er ulike, er ikke
undersøkt; ingen av dem er ILA eller PD.
*Feil hvis:* `m2_api_analyse.txt` viser `hasIla` eller `hasPd` ulik i mer
enn 0.

**F2.2 — Sykdomshistorikken går tilbake til 2013. MÅLT.**
`GET /v3/geodata/fishhealth/locality/{nr}/disease` for seks av
lokalitetene med ILA eller PD i uke 36 ga 2–7 tilfeller hver, med
mistanke-, diagnose- og avslutningsdato. Eldste diagnose 2013-08-05
(10045, `2026-11-03.21.json.gz`).
`GET /v2/…/ilaprotectionzone/2026/36` ga fem soner
(`2026-11-03.26.json.gz`); `pdprotectionzone` for samme uke ga en tom
liste.

**F2.3 — Fiskeridirektoratets sykdomslag er nåtid. MÅLT.** Lag 26 (PD,
29 poster) og 27 (ILA, 14), med status og datoer men uten historikk
(`2026-11-03.6.json.gz`, `.7.json.gz`). `copyrightText` er
«Barentswatch / Veterinærinstituttet»: det er BarentsWatchs tall vist
på nytt.

**Konklusjon:** kan hentes bakover, og arkiveres derfor ikke. Ukesvaret
er allerede i serien gjennom `lusetall`. Vilkår NLOD
(`vilkar-barentswatch/2026-11-02.bin.gz`, `573408e59b7b17d5`).

## c. Overskrifter fra bransjemedia

**F3.1 — Fiskeribladet og Intrafish forbyr fangsten. EKSTERN, arkiveres
nå.** Fiskeribladets vilkår (`/vilkar`) sier at «medieovervåkning,
eksemplarfremstilling, skraping, crawling, indeksering,
tekst/datautvinning» av innholdet krever gyldig avtale. Intrafish' vilkår
(DN Media Group Global AS) sier det samme på engelsk. Sidene hentes inn
av `arkiver_vilkar.py` i denne økta og blir MÅLT når de ligger i
`vilkar-fiskeribladet/` og `vilkar-intrafish/`.

**F3.2 — Kyst.no og iLaks: ingen vilkår for gjenbruk. EKSTERN.**
Kyst.no lenker til Oceanspace Medias abonnementsvilkår, som ikke nevner
gjenbruk, RSS eller automatisk henting. iLaks har ingen vilkårsside på
forsiden, bare personvernerklæring og kontakt. UBELAGT for begge.

**F3.3 — robots.txt stenger ikke for oss. MÅLT.** iLaks har bare
`Crawl-delay: 1` (`2026-11-03.bin.gz`), Kyst.no `Disallow:` uten sti
(`.2.bin.gz`). Fiskeribladet og Intrafish stenger noen få stier for `*`
og hele nettstedet for en rekke navngitte roboter (33 i utskriften), ikke
for vår User-Agent
(`.3.bin.gz`, `.4.bin.gz`).

**F3.4 — Bare iLaks har RSS. EKSTERN.** `ilaks.no/feed/`: 12 saker, 12
`dc:creator`, ingen `content:encoded`, `description` på 698–971 tegn,
saker fra 02.11 15.25 til 03.11 18.50 UTC (sha256 `8df347cf1ad416e6`,
ikke arkivert). `/rss` og `/feed` hos Kyst.no, Fiskeribladet og Intrafish
gir 404, og ingen av forsidene har en `alternate`-lenke til en strøm.

**F3.5 — Personnavn filteret ikke kan ta. EKSTERN.** Hver sak har en
byline (`dc:creator`), og titler nevner personer. `core/persondata.py`
filtrerer på organisasjonsform og kan ikke lese fritekst. Selv tittel,
URL og tid alene (uten `description`) har navn.

**Kan hentes bakover:** delvis. Strømmen viser to døgn; Fiskeribladet og
Intrafish har `sitemap.xml` med URL-er, men den første tittelen en sak
ble utgitt med, finnes ikke noe sted. Ikke målt videre, siden regel 1 og
3 i STOPP-regelen allerede er utløst.

**Konklusjon:** bygges ikke.

## d. Akvakultursøknader til offentlig ettersyn

**F4.1 — Fylkeskommunene samler dem ikke per fylke. EKSTERN.** I de
oversendelsesbrevene søket fant (kommuner i Nordland, Trøndelag, Møre og
Romsdal, Troms, Rogaland og Agder), sender fylkeskommunen søknaden til
kommunen, og kommunen legger den ut. Søkeren kunngjør i Norsk
Lysingsblad og i to lokalaviser, og fristen er fire uker. Søknadene
ligger derfor på kommunenes sider, én kommune om gangen. Ingen av de åtte
fylkeskommunenes forsider har en lenke til en samlet liste over
akvakultursøknader; Vestland og Møre og Romsdal har en side for
høyringar, Finnmark for planer og høringer. Ikke lest videre.

**F4.2 — Det finnes ett samlet register: søknadsportalen. MÅLT.**
`Yggdrasil/Akvakultursøknader/MapServer` hos Fiskeridirektoratet: 296
søknader under behandling (lag 0), 149 søknadsflater (lag 2) og 664
ferdigbehandlede (lag 4) (`2026-11-03.6.bin.gz`, `.8.bin.gz`,
`.10.bin.gz`). Lag 4 har `submittedat`, `withdrawnat` og
`evaluationfinishedat`, så tilstanden på en dato kan delvis regnes ut
bakover. Datoen for offentlig ettersyn står ikke i noen av lagene
(`.5.bin.gz`, `.7.bin.gz`, `.9.bin.gz`).

**F4.3 — Søkers navn uten organisasjonsform. MÅLT.** Lagene har
`applicantorganisationname` og `applicantorganisationnumber`, ingen
organisasjonsform. Lag 0 har et felt som bare heter `type`; i postene
som ble lest (ikke arkivert) er det søknadstypen, `NEW_SITE` og
`CHANGE_SITE`. Et enkeltpersonforetak har ni siffer som et AS
(CLAUDE.md regel 3), og filteret kan ikke skille dem uten et oppslag mot
Enhetsregisteret.

**Konklusjon:** bare måling, som bestilt. Bygges noe, er det
søknadsportalen og ikke 8 fylker, og det krever et oppslag på
organisasjonsform før arkivering.

## e. Utgivelsesvakt for de statiske kildene

**F5.1 — regomr.geojson: belagt, og uendret siden innsamlingen. MÅLT.**
`ftp.nmdc.no/…/regomr.geojson`, 31 719 B, `Last-Modified: Fri, 28 Aug
2026 05:00:09 GMT`, sha256 `e62b5686355a4586`
(`maling-nye-kilder/2026-11-03.11.bin.gz`), byte-lik `geojson`-feltet i
begge kroppene i `reguleringsomraader/`. CC BY 4.0 på NMDCs
landingsside (LISENSKJEDE merknad D), som `arkiver_vilkar.py` arkiverer
fra nå. Den forrige versjonen av fila finnes ikke hos NMDC når den er
skrevet over.

**F5.2 — Ekspertgruppens og HIs rapportsider: UBELAGT.**
`trafikklyssystemet.no/Publikasjoner/Ekspertgrupperapporter` (200,
218 625 B) og `hi.no/hi/nettrapporter` (200, 128 021 B) svarer, men ingen
av dem har en vilkårsside. hi.no har bare en personvernerklæring.
Ekspertgrupperapportene selv er UBELAGT fra før (LISENSKJEDE merknad E).
Ikke arkivert.

**F5.3 — Regjeringens side om trafikklyssystemet: ikke målt.** 403 med
Cloudflares utfordring («Just a moment…», `2026-11-03.14.bin.gz`), også
for `robots.txt` (`.15.bin.gz`). Wayback-CDX svarte `[]`
(`.19.bin.gz`), og var nede tidligere samme kveld. `.12.bin.gz` og
`.13.bin.gz` er de samme to 403-sidene fra et forsøk som fikk timeout før
loggen ble skrevet; de har en annen nonce og derfor en annen hash.

**F5.4 — Lovdata-søket er stengt. MÅLT.** `lovdata.no/robots.txt` har
`User-agent: *` med `Disallow: /`, og `/sok` er stengt også for de
navngitte søkemotorene (`2026-11-03.16.bin.gz`). Søket svarer 405
(`.17.bin.gz`). Dette gjelder hele nettstedet for `*`, og er et funn om
`arkiver_lovdata.py` og `trafikklysvedtak` også. Ikke rettet her.

**Bygget:** `utgivelsesvakt.py`, ukentlig, bare regomr.geojson.

## f. BarentsWatch v2 for lusetall

**F6.1 — Samme uker og samme lokaliteter. MÅLT.** `POST /v2/geodata/
fishhealth/locality/{year}/{week}` med `{}` for uke 45–41 og 36/2026,
hver hentet rett etter v1 for samme uke: like mange lokaliteter
(1777–1782), samme `localityNo` og samme `localityWeekId` for hver.
Snitt hunnlus, rapportert og brakklagt er ulike i 0 lokaliteter i alle
seks ukene. Kroppene er `2026-11-03.8.json.gz`–`.19.json.gz` (v1 par, v2
odde). v2 er 1,21–1,23 MB per uke mot 0,76 MB for v1.

**F6.2 — ILA og PD er uenige. MÅLT.** Mellom v1 (`hasIla`, `hasPd`) og
v2 (`diseases` inneholder `INFEKSIOES_LAKSEANEMI`, `PANKREASSYKDOM`):

    uke 45   ILA 14 bare v1 / 12 bare v2   PD 35 bare v1 / 18 bare v2
    uke 44   ILA 14 / 12                   PD 35 / 18
    uke 43   ILA 14 / 12                   PD 35 / 21
    uke 42   ILA 14 / 12                   PD 35 / 21
    uke 41   ILA 14 / 13                   PD 35 / 21
    uke 36   ILA 15 / 13                   PD 35 / 20

(utskriften i `m2_api_analyse.txt`). v2 har også `FRANCISELLOSE`, som v1
ikke har noe felt for. Hva som skiller dem (sone, mistanke, status), er
ikke undersøkt: målet her er fangst, ikke tolkning.
*Feil hvis:* `m2_api_analyse.txt` viser 0 for ILA og PD i en av ukene.

**F6.3 — Feltene. MÅLT.** v2: `diseases`, `geometry`,
`hasSalmonoidLicense`, `isFiltered`, `isSlaughterHoldingCage`,
`liceReport` (`adultFemaleLice`, `mobileLice`, `stationaryLice`,
`totalLice` med snitt, forrige ukes snitt og trend, `hasReported`,
`isFallow`, `seaTemperature`), `liceTreatments`, `locality`,
`localityWeekId`, `municipality`. v1-feltene `hasCleanerfishDeployed`,
`hasMechanicalRemoval` og `hasSubstanceTreatments` finnes ikke som felt;
behandlingene står i `liceTreatments`. «Mekanisk fjerning eller
medikamentell behandling» i v1 og «`liceTreatments` ikke tom» i v2 er
ulike i 0 lokaliteter i alle seks ukene. `seaTemperature` per lokalitet og uke
finnes bare i v2.

**F6.4 — Byte-stabilt. MÅLT.** To kall mot uke 41, 19.19.57 og 19.20.18
UTC (loggen `m1c`), og kallet ti minutter før, 19.10.08
(`2026-11-03.17.json.gz`), ga samme sha256 `8960a9389073c90a`. Fangsten sammenligner på sha256.

**Vilkår:** samme som v1, BarentsWatchs API-vilkår, NLOD
(`vilkar-barentswatch/2026-11-02.bin.gz`). Spesifikasjonen
(`lusetall-innkomst-openapi/2026-11-02.json.gz`, `d3f328e89202cf6e`) har
ikke `info.license`.

**Kan hentes bakover:** ja, uke 36 svarer. Men F6.2 viser at en uke
hentet fra v2 etter at v1 er borte, ikke kan holdes mot v1 for den uka.
Det er derfor fangsten startes: ikke for å bevare v2, men for å ha
overlappen.

**Bygget:** `arkiver_luseinnkomst.py --v2`, daglig, uke N til N−4,
`data/arkiv/lusetall-innkomst-v2/`.

## Etterskrift 03.11.2026, kveld: Lovdata, søknadslaget og ILA/PD (økt 4b)

Teksten over er ikke endret. Kallene ble gjort 21.48–22.10 UTC. Tre
nye logger, samme form som de fire over:

| logg | skript | punkt |
|---|---|---|
| `maling-lovdata/2026-11-03.l1.logg.json` | `analyse/lovdata/l1_hent.py` | 0 og 5 |
| `maling-soknader/2026-11-03.s1.logg.json` | `analyse/soknader/s1_mal.py` | 1 |
| `maling-ilapd/2026-11-03.i1.logg.json` | `analyse/ilapd/i1_mattilsynet.py` | 3 |

Utskriftene står uendret i `analyse/soknader/s1_mal.txt` og
`analyse/ilapd/i1_mattilsynet.txt`, og stille hopp i
`analyse/drift/stille_hopp.txt` (MALING-DRIFT). Hashene er som over:
sha256 over den utpakkede kroppen, de 16 første tegnene.

### Punkt 0: arkiver_lovdata.py og robots.txt

**F7.1 — Ingen workflow kjører arkiver_lovdata.py. MÅLBAR.** Skriptet
sier selv «Kjøres for hånd, ikke av en workflow». `.github/jobber.yml`
har ingen lovdata-sti, og `git log --all -S arkiver_lovdata` i
datarepoet er tom. Det finnes altså ingen workflow å fjerne den fra, og
ingen workflow-fil er skrevet for punktet. Arkivet står.
*Feil hvis:* en workflow i datarepoet kaller `arkiver_lovdata.py`.

**F7.2 — Alle kroppene hentet fra lovdata.no siden starten.** Fra
arkivet og loggene; tre jobber har hentet derfra, ikke én:

| hentet (UTC) | jobb | adresse | kropp | sha256 |
|---|---|---|---|---|
| 05.09 17.18 | `trafikklysvedtak` (backfill) | `LTI/forskrift/2017-12-20-2397` | `trafikklysvedtak/2018-12-31.bin.gz` | `9dd38abdaea60f9e` |
| 05.09 17.18 | samme | `LTI/forskrift/2020-02-04-105` | `trafikklysvedtak/2020-12-31.bin.gz` | `0ac5a3286bdb1c89` |
| 05.09 17.18 | samme | `LTI/forskrift/2022-06-07-972` | `trafikklysvedtak/2022-12-31.bin.gz` | `31f1b88e228b2e74` |
| 05.09 17.18 | samme | `LTI/forskrift/2024-03-22-515` | `trafikklysvedtak/2024-12-31.bin.gz` | `5184ac61c32a30ae` |
| 14.09 (commit `e3134c2`) | `trafikklysvedtak` | `LTI/forskrift/2026-08-20-1764` | `trafikklysvedtak/2026-12-31.bin.gz` | `08b6090d993b9644` |
| 06.10 (loggen har ingen tid) | `arkiver_vilkar.py` | `info/brukeravtale` | `vilkar-lovdata/2026-10-06.bin.gz` | `33f46a49695d9cc7` |
| 08.10 16.07, 09.10 06.57 | samme | samme | uendret | `33f46a49695d9cc7` |
| 09.10 05.59 | `arkiver_lovdata.py` | `SF/forskrift/2017-01-16-61` | `lovdata-produksjonsomradeforskriften/2026-10-09.bin.gz` | `f44406e410705f3d` |
| 09.10 05.59 | samme | `LTI/forskrift/2023-09-28-1520` | `lovdata-produksjonsomradeforskriften-endring-2023/2026-10-09.bin.gz` | `7a8d1ec516273008` |
| 09.10 05.59 | samme | `SF/forskrift/2012-12-05-1140` | `lovdata-lakselusforskriften/2026-10-09.bin.gz` | `0ae73fa83534c0f4` |
| 09.10 15.46 | samme, de tre over igjen | samme | uendret | som over |
| 09.10 15.46 | samme | `NL/lov/2018-06-15-40` | `lovdata-andsverkloven/2026-10-09.bin.gz` | `b60131c4a8bbe6fe` |
| 02.11 15.10 | `arkiver_vilkar.py` | `info/brukeravtale` | `vilkar-lovdata/2026-11-02.bin.gz` | `4ef5a05f2e3e0266` |
| 03.11 09.06, 19.51, og én kjøring mellom dem uten logg | samme | samme | uendret | `4ef5a05f2e3e0266` |
| 03.11 19.2x, 21.48 | målingene | `robots.txt`, `sok` | `maling-nye-kilder/2026-11-03.16.bin.gz`, `.17.bin.gz`, `maling-lovdata/2026-11-03.bin.gz` | `cbafdcc28cde8a5c` (robots.txt) |

`arkiver_lovdata.py` har kjørt to ganger, begge 09.10.2026, og hentet sju
kropper, fire av dem forskjellige. Snapshotet `trafikklysvedtak/
2026-12-31.parquet` har `fetched_at` 15.09 21.03 og `raw_hash` lik
kroppen fra 14.09; om 15.09 også var et kall mot lovdata.no, er
UBELAGT. Skriptets docstring nevner to lesinger av
produksjonsområdeforskriften 05.09 og 23.09 som ikke ble arkivert:
UBELAGT. Kjøringen 03.11 uten logg er det stille hoppet i
MALING-DRIFT.
*Feil hvis:* en kropp under `lovdata-*/`, `vilkar-lovdata/` eller
`trafikklysvedtak/` mangler i tabellen.

**F7.3 — robots.txt sa `User-agent: *` / `Disallow: /` i hver kopi som
finnes. MÅLT for kopiene, MÅLBAR for datoene mellom dem.** Wayback-CDX
for `lovdata.no/robots.txt` fra 2025 (`maling-lovdata/2026-11-03.3.bin.gz`,
`1d0f503e3527569f`) og én kopi av hver digest:

| kopi | sha256 | `*` stengt |
|---|---|---|
| Wayback 13.04.2025 og 05.07.2025 (`.4.bin.gz`, samme bytes) | `18791cb36d43ba98` | ja |
| Wayback 01.10.2025 (`.5.bin.gz`) | `7aa611491b1d5cc2` | ja |
| Wayback 14.05.2026, digesten som går fra 13.11.2025 (`.bin.gz`) | `cbafdcc28cde8a5c` | ja |
| vår henting 03.11.2026 19.2x og 21.48 (`maling-nye-kilder/.16.bin.gz`, `maling-lovdata/.bin.gz`) | `cbafdcc28cde8a5c` | ja |

Den siste Wayback-kopien er 14.05.2026, og vår første er 03.11.2026.
Alle hentedatoene i F7.2 ligger mellom de to, som er byte-like. Hva
robots.txt sa på selve dagen, er ikke sett for noen av dem. Mellom
versjonene skiller bare listen over navngitte roboter; `*` har
`Disallow: /` i alle.
*Feil hvis:* en av kroppene i tabellen mangler `Disallow: /` under
`User-agent: *`.

**F7.4 — lovdata.no hentes fortsatt automatisk av én jobb.
MÅLBAR.** `arkiver_vilkar.py` har `lovdata.no/info/brukeravtale` i
`SIDER` og kjøres av `vilkar.yml` den 2. hver måned, neste gang
02.12.2026. `trafikklysvedtak` henter bare når `NYESTE_RUNDE` endres i
koden (`gjelder_for`), og har ikke hentet siden 14.09 (`health.json`:
«2026-12-31 ligger skrevet fra før»). Ingen av dem er endret.

**F7.5 — Lovdatas egen brukeravtale tillater det robots.txt stenger.
MÅLT.** `vilkar-lovdata/2026-11-02.bin.gz` (`4ef5a05f2e3e0266`; synlig
tekst lik versjonen fra 06.10) gir et unntak under NLOD 2.0 for
«Regelverk i Norsk Lovtidend», «Gjeldende formelle lover» og «Gjeldende
sentrale forskrifter», «kun for enkeltlover og -forskrifter», og sier at
massenedlasting ikke er tillatt og at større nedlastinger skal gå
gjennom de åpne API-ene. Det `arkiver_lovdata.py` hentet, er fire
enkeltdokumenter. Hvilket av de to dokumentene som gjelder for en
robot, er ikke målbart her.
*Feil hvis:* den synlige teksten i kroppen ikke nevner NLOD 2.0.

### Punkt 1 og 2: søknadslaget

**STOPP-regelen** er oppdragets egen, gitt før målingen: fangst bygges
bare hvis tilstanden ikke kan hentes bakover, vilkåret er avklart og
persondatafilteret holder; ellers fanges ingenting, og det står her.
Skriptet ble prøvekjørt to ganger mot en kopi i scratch (21.54 UTC)
før kjøringen mot arkivet (21.55); tallene var de samme.

Postene slik de kom, er ikke arkivert (søkers navn og nummer uten
organisasjonsform). Etter filteret er lag 0, 2 og 4 arkivert i
`maling-soknader/` (`.9.json.gz` `ffe1c6efe5e45029`, `.10.json.gz`
`be41567aa60ff3e4`, `.11.json.gz` `7ce188024ead66a8`). Filteret tok én
søknad i lag 0 og 2 og ingen i lag 4, så tall om lag 4 er holdt mot
kroppen, og tall om lag 0 med 296 poster er EKSTERN (295 står i
kroppen).

**F8.1 — Sju lag, ingen historikk. MÅLT.** Metadata for tjenesten og
hvert lag er arkivert (`maling-soknader/2026-11-03.json.gz` til
`.8.json.gz`). Lag 0 under behandling, 1 forankringspunkt, 2 flate, 4
ferdigbehandlet, 5 flate ferdigbehandlet, 6 gammel flate, 7
forankringspunkt ferdigbehandlet; ingen tabeller. Alle har
`timeInfo`, `editingInfo` og `supportsQueryWithHistoricMoment` tomme,
og `relationships` er tom liste. Lag 0 og 4 har søknadsnummer, søker,
type, `status_application`, `submittedat`, lokalitetsnummer og -navn,
koordinater, kommune, omsøkt MTB (`desiredbiomass_value`), planlagt
produksjon, art og antall nye tillatelser; lag 4 har i tillegg
`withdrawnat`, `evaluation_result` og `evaluationfinishedat`. Ingen
felt sier når posten sist ble endret.
*Feil hvis:* metadata for lag 0 eller 4 har et datofelt for endring,
eller `relationships` er ikke tom.

**F8.2 — `historicMoment` ignoreres. EKSTERN.** Lag 0 og 4 spurt med
`historicMoment` for 01.09.2026 12 UTC ga samme sha256 som uten
(`77b22b6dbe370ba9`, `ba5e5c229981409e`, loggen `s1`). De samme to
hashene kom i prøvekjøringen ett minutt før, så svaret er byte-stabilt.
Kroppene er ikke arkivert, se over.
*Feil hvis:* de to `historicMoment`-radene i `s1`-loggen har en annen
sha256 enn spørringen uten.

**F8.3 — En ferdigbehandlet søknad beholder ikke statusforløpet. MÅLT
for lag 4.** 664 søknader: `PROCESSED` 573, `WITHDRAWN` 91;
`evaluation_result` `GRANTED` 492, `DENIED` 81, tom 91. Det som finnes
om forløpet, er tre datoer: `submittedat` (664), `evaluationfinishedat`
(573) og `withdrawnat` (91). Domenet for `status_application` har sju
koder (`CREATED`, `SUBMITTED`, `COMPLETE`, `INCOMPLETE`, `PROCESSED`,
`WITHDRAWN`, `RETURNED`); lag 0 viser bare `SUBMITTED` 260 og
`RETURNED` 36 (EKSTERN). Av søknadene i lag 4 var 657 sendt inn før
01.09.2026 og 65 av dem ikke avsluttet da, etter datoene; hvilken
status og hvilken omsøkt MTB de hadde 01.09, står ikke noe sted. 0
søknadsnumre står i både lag 0 og lag 4.
*Feil hvis:* lag 4-kroppen har et annet antall `PROCESSED` enn 573.

**Tilstanden 01.09.2026 kan altså ikke hentes**, bare delvis regnes ut:
at en søknad var under behandling, men ikke hva den sa.

**F8.4 — Hvor ofte endres en søknad: bare datoene kan svare. MÅLT for
lag 4.** De siste 30 døgnene før 03.11.2026: 34 sendt inn (lag 0,
EKSTERN), 16 ferdigbehandlet og 3 trukket (lag 4). Endringer uten ny
dato (`RETURNED` tilbake til `SUBMITTED`, ny MTB, ny flate) kan ikke ses
i én henting. Det er det fangsten skal måle. UBELAGT inntil den har gått
en stund.

**F8.5 — Ingen av søkerne er personer; én er ukjent. EKSTERN.** 222
ulike søkernummer i alle sju lag, alle ni siffer, ingen tomme. Brreg:
214 aktive, 7 slettet, 1 svarer 404. Former: AS 207, FYLK 5, ASA 3,
ORGL 3, STI 2, FLI 1, ukjent 1. Ingen i sektor 8200 eller 2300, ingen
ENK, DA, ANS eller PRE. Filteret (vet ikke = ut) tok den ene ukjente:
én post i lag 0, 1 og 2, ingen i 4–7. Brreg-svarene er ikke arkivert;
utskriften har bare tellingene.

**F8.6 — Vilkåret er NLOD. MÅLT.** Tjenesten har `copyrightText`
«Fiskeridirektoratet» (`maling-soknader/2026-11-03.json.gz`).
`vilkar-fiskeridir/2026-11-02.bin.gz` (`021c8692f14104b1`): «All bruk av
data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige
data (NLOD).» Siden arkiveres månedlig av `arkiver_vilkar.py` fra før.
Rad i LISENSKJEDE. `gis.fiskeridir.no/robots.txt` svarer 404 (EKSTERN,
ikke arkivert).
*Feil hvis:* den synlige teksten i `vilkar-fiskeridir/2026-11-02.bin.gz`
ikke nevner NLOD.

**F8.7 — Kobling: 627 søknader har lokalitetsnummer, alle i registeret.
MÅLT for lag 4.** Mot de 31 akvakultur-kroppene i arkivet
(`akvakultur/2026-08-17.json.gz` `b1d36b5caedf4c3d` til
`2026-11-03.daglig.2.json.gz` `5b53e1b336d980f6`, 1790 ulike
lokalitetsnummer):

    lag 0   296 søknader, sitenr i 130, alle 130 i registeret;
            166 uten, 40 av dem innen 500 m av en lokalitet i registeret
    lag 4   664 søknader, sitenr i 497, alle 497 i registeret;
            167 uten, 81 av dem innen 500 m; 83 innvilget uten sitenr

Ingen av lokalitetsnumrene ble sett første gang etter
`2026-08-17.json.gz`; vinduet er bare 17.08–03.11, så «kom senere i
registeret» kan ikke måles lenger bakover. Feltene
`sitelatitudedecimaldegree` og `sitelongitudedecimaldegree` er grader
ganger 100 (6588,035 for 65,881 i registeret, lokalitet 36017). Delt på
100 er medianavstanden mellom søknad og register 0,000 km i lag 4 og
0,007 km i lag 0, og under 0,5 km for 494 av 497 og 128 av 130.
*Feil hvis:* en søknad i lag 4-kroppen har et `sitenr` som ikke finnes i
noen akvakultur-kropp.

**F8.8 — Bygget: `arkiver_soknader.py`, daglig.** Lag 0, 2, 4, 5 og 6
(forankringspunktene, lag 1 og 7, er utelatt med vilje). Hvert
søkernummer slås opp hos Brreg før noe skrives; feiler oppslaget,
skrives ingenting, heller ikke karantene. Kroppssjekk og karantene som
`arkiver_flater.py`. Egen sti `data/arkiv/akvakultur-soknader/` og
jobben `soknader` i `daglig.yml`, med frist 2 døgn i `jobber.yml`; de
tre workflow-filene er skrevet, ikke lagt inn.

**F8.9 — Første kjøring for hånd. MÅLT.** Kodrepoets `97e8655`, fra en
fersk klone (som jobben i Actions), 03.11.2026 22.11.40 UTC. Lagret
`akvakultur-soknader/2026-11-03.json.gz`, sha256 `ac5f99e37de8811a`,
1 525 094 byte utpakket og 199 675 byte gzippet, med 295, 148, 664, 297 og
125 poster i lag 0, 2, 4, 5 og 6, og loggen
`2026-11-03.fangst.logg.json` (`kode_rent` «ja», `filtrert`: «vet ikke»
1 i lag 0 og 1 i lag 2). Kroppen har 221 ulike søkernummer, alle ni
siffer; geometri bare i lag 2, 5 og 6.
*Feil hvis:* kroppen har et annet antall poster i lag 0 enn 295.

### Punkt 3: ILA og PD, v1 mot v2 mot Mattilsynet

**F9.1 — Nettstedet og snapshotene bruker v1. MÅLBAR, lest i koden.**
`sources/lusetall.py` henter `v1/geodata/fishhealth/locality/{år}/{uke}`
og skriver `hasIla` som `har_ila` og `hasPd` som `har_pd` (linje 93–94).
Nettstedet viser feltene som hendelser med teksten «ILA-flagg satt i
BarentsWatch» (`nettsted.py`, `MAALESERIE_HENDELSER` og kommentaren ved
`("lusetall", "har_ila")`). v2-kroppene arkiveres av
`arkiver_luseinnkomst.py --v2` og leses ikke av noe.

**Reglene** står i toppen av `analyse/ilapd/i1_mattilsynet.py`, committet
i `3db1bed` før skriptet ble kjørt (forfatterdato 22.02.56 UTC, første
kall til Mattilsynet 22.03.01; committerdatoen er fra en omordning av
de upushede commitene før push): uke 44/2026, de fem laveste
lokalitetsnumrene i hver av de fire uenige gruppene, Mattilsynets
`sykdomstilfeller/v1/rapporteringer` som fasit (et tilfelle er aktivt
når mistanke eller diagnose er senest søndag, avslutningen tidligst
mandag, og det ikke er ugyldiggjort), mistanke teller som aktivt, og
STOPP hvis v1 er uenig med Mattilsynet i 5 eller flere av de 20.

**F9.2 — Uke 44: v1 har 16 ILA og 46 PD, v2 har 14 og 29. MÅLT.** v1
`maling-nye-kilder/2026-11-03.10.json.gz` (`ed20098a24ddc4a9`), v2
`.11.json.gz` (`5a75f2819a61487d`), 1782 felles lokaliteter. Begge har
ILA på 2 og PD på 11; bare v1 har ILA på 14 og PD på 35, bare v2 ILA på
12 og PD på 18.
*Feil hvis:* antallet lokaliteter med `hasIla` sann i v1-kroppen er et
annet enn 16.

**F9.3 — v1 er uenig med Mattilsynet i 20 av 20, v2 i 0. MÅLT.** Hvert
svar fra Mattilsynet er arkivert i `maling-ilapd/` (fila og hashen står
per lokalitet i `i1_mattilsynet.txt`). Datoene er Mattilsynets, lest i
Europe/Oslo:

| sykdom | bare i | lokalitet | Mattilsynet, uke 44 | tilfellet | fil |
|---|---|---|---|---|---|
| ILA | v1 | 10839 | ingen | diagnose 11.06.2024, avsluttet 28.03.2025 | `.3.json.gz` |
| ILA | v1 | 11667 | ingen | diagnose 25.07.2024, avsluttet 07.02.2025 | `.8.json.gz` |
| ILA | v1 | 11758 | ingen | diagnose 02.07.2024, avsluttet 06.12.2024 | `.10.json.gz` |
| ILA | v1 | 12370 | ingen | diagnose 22.08.2024, avsluttet 21.08.2025 | `.12.json.gz` |
| ILA | v1 | 12449 | ingen | mistanke 12.07.2024, avsluttet 14.12.2024 | `.16.json.gz` |
| ILA | v2 | 11272 | påvist | diagnose 23.09.2026, åpent | `.4.json.gz` |
| ILA | v2 | 12625 | mistanke | mistanke 09.07.2026, åpent | `.17.json.gz` |
| ILA | v2 | 13581 | mistanke | mistanke 11.05.2026, åpent | `.18.json.gz` |
| ILA | v2 | 13811 | mistanke | mistanke 31.08.2026, åpent | `.19.json.gz` |
| ILA | v2 | 17077 | påvist | diagnose 19.06.2025, åpent | `.20.json.gz` |
| PD | v1 | 10054 | ingen | diagnose 19.07.2024, avsluttet 18.07.2025 | `.json.gz` |
| PD | v1 | 10298 | ingen | diagnose 20.11.2024, avsluttet 25.05.2025 | `.2.json.gz` |
| PD | v1 | 11488 | ingen | diagnose 05.08.2024, avsluttet 12.10.2025 | `.5.json.gz` |
| PD | v1 | 11492 | ingen | diagnose 13.12.2024, avsluttet 15.06.2025 | `.6.json.gz` |
| PD | v1 | 11525 | ingen | diagnose 12.06.2024, avsluttet 05.08.2025 (et dobbelttilfelle ugyldiggjort 13.11.2025) | `.7.json.gz` |
| PD | v2 | 11688 | påvist | diagnose 06.07.2026, åpent | `.9.json.gz` |
| PD | v2 | 11810 | påvist | diagnose 18.09.2026, åpent | `.11.json.gz` |
| PD | v2 | 12385 | mistanke | mistanke 26.02.2026, åpent | `.13.json.gz` |
| PD | v2 | 12394 | påvist | diagnose 05.03.2026, åpent | `.14.json.gz` |
| PD | v2 | 12435 | påvist | diagnose 21.10.2025, åpent | `.15.json.gz` |

Hver av de ti lokalitetene bare v1 flagger, har et tilfelle Mattilsynet
avsluttet mellom 06.12.2024 og 12.10.2025, og ingenting aktivt i uke 44.
Hver av de ti bare v2 flagger, har et åpent tilfelle med mistanke eller
diagnose fra 13.06.2025 eller senere. Teller bare «påvist», er v1 enig i
4 av 20 og v2 i 16 (de fire med bare mistanke). Hvorfor v1 henger igjen,
er ikke undersøkt.
*Feil hvis:* svaret fra Mattilsynet for en av de ti «bare v1» har et
tilfelle av sykdommen uten avslutningsdato før 26.10.2026, eller svaret
for en av de ti «bare v2» ikke har et åpent tilfelle.

**STOPP utløst.** v1 er uenig i 20 av 20, grensen var 5. Det nettstedet
og snapshotene viser som ILA- og PD-flagg, er feil for disse
lokalitetene, målt mot Mattilsynets egne tilfeller. Ingenting er rettet,
og ingenting er tolket utover tabellen. Utvalget er bare uenige
lokaliteter; hvor stor andel av alle flaggene som er feil, er ikke målt.

### Punkt 5: Lovdatas åpne datasett

**STOPP-regel**, skrevet etter at robots.txt for api.lovdata.no var lest
for første gang (utforskende, ikke arkivert) og før noe annet ble målt:
er hentestedet stengt for `*` i sin egen robots.txt, lastes ingen pakke
ned. Lista, spesifikasjonen og robots.txt hentes én gang hver og
arkiveres, og spørsmålet om forskriftene er med, står åpent til Heine
har bestemt om robots.txt gjelder.

**F10.1 — Datasettene finnes, uten nøkkel. MÅLT.**
`api.lovdata.no/v1/publicData/list` (`maling-lovdata/2026-11-03.7.bin.gz`,
`67a4b176082398e4`) lister seks pakker, alle med `lastModified`
03.11.2026 02.31–02.32 UTC: `gjeldende-lover.tar.bz2` (5 810 283 B),
`gjeldende-sentrale-forskrifter.tar.bz2` (21 516 248 B),
`lovtidend-avd1-2001-2025.tar.bz2` (69 320 068 B),
`lovtidend-avd1-2026.tar.bz2` (1 642 194 B) og to for avdeling II
(lokale forskrifter). Spesifikasjonen (`.8.bin.gz`, `fbcaf3f97d310318`)
sier at de to første er «free datasets […] no user or authentication
required», og at `publicData`-endepunktene ikke krever nøkkel. Den har
ingen `info.license`.
*Feil hvis:* lista i `.7.bin.gz` har et annet antall pakker enn seks.

**F10.2 — Lisensen står i brukeravtalen, ikke i API-et. MÅLT.**
`vilkar-lovdata/2026-11-02.bin.gz` (`4ef5a05f2e3e0266`): NLOD 2.0 for
regelverk i Norsk Lovtidend, gjeldende lover og gjeldende sentrale
forskrifter, med kilde «Lovdata». Samme avsnitt viser større
nedlastinger til «våre åpne API-er», med lenke til
`api.lovdata.no/swagger#/Public%20data`. Se F7.5.

**F10.3 — Hentestedet er stengt i sin egen robots.txt. MÅLT.**
`api.lovdata.no/robots.txt` er 25 byte, `User-agent: *` og
`Disallow: /` (`maling-lovdata/2026-11-03.2.bin.gz`, `efdb5938a9736727`).
Wayback har seks kopier fra 25.01.2025 til 23.03.2026, alle med samme
digest (`.6.bin.gz`), og kopien fra 23.03.2026 er byte-lik vår. Etter
sin robots.txt er hentestedet altså ikke tillatt. Brukeravtalen
(F10.2) sender likevel brukerne dit. STOPP-regelen er utløst, og ingen
pakke er lastet ned.
*Feil hvis:* `.2.bin.gz` har noe annet enn de to linjene.

**F10.4 — Er trafikklysforskriften og kapasitetsjusteringen med?
UBELAGT.** Ingen pakke er åpnet. Beskrivelsene peker på hvor de ville
ligget: FOR-2017-01-16-61 er en sentral forskrift (dokumenttypen `SF`
hos Lovdata, den samme `arkiver_lovdata.py` hentet), altså i
`gjeldende-sentrale-forskrifter`; kapasitetsjusteringsforskriftene er
kunngjøringer i Lovtidend avdeling I (`LTI`), altså i
`lovtidend-avd1-2001-2025` og, for runden 2026, `lovtidend-avd1-2026`.
Det er en lesning av navnene, ikke av innholdet.

**Forslag til utgivelsesvakten: ikke gitt.** Kravet var at hentestedet
holder, og etter robots.txt gjør det ikke. Bestemmer Heine at
brukeravtalens henvisning går foran robots.txt for et API, er forslaget
dette: ukentlig henting av `publicData/list` i `utgivelsesvakt.py`, med
ny kropp og issue når `sizeBytes` for `gjeldende-sentrale-forskrifter`
endres. Ikke `lastModified`: alle seks pakkene har samme natt, så feltet
kan være byggetiden og ikke endringen (én henting, ikke målt over tid).
