# Måling: før ukejobben for maskinanslagene bygges

Målt 17.11.2026 (UTC), økt 14a, mot `havbruk-radar` på `b1d0a5e` og
`havbruk-radar-data` slik det var etter `git pull` samme kveld. Tre
spørsmål, stilt før `anslag.yml` skrives:

- **0a.** Hvor mange Actions-minutter bruker hver jobb i datarepoet på 30
  døgn, og hva legger ukejobben til?
- **0b.** Hva har `.komplett.ots` løst av feilen 11.11.2026, der en
  oppgradering av stemplene gjorde forseglingsprøven rød, og hva står
  igjen?
- **0c.** Når har mandagens innsamling faktisk startet de siste seks
  ukene?

Dette er en måling. Ingenting er rettet på grunnlag av den; det som
bygges etterpå, står i commitene for punkt 1–3.

**Merkene:** MÅLT = holdt mot en arkivert kropp, med sha256. MÅLBAR =
lest i en fil i kodrepoet, i git-historikken eller regnet ut av målte
tall, men ikke selv holdt mot en arkivert kropp. EKSTERN = hviler på noe
som ikke er arkivert. UBELAGT = ingen kropp sier det.

## Kroppen

Kjøringene og jobbene er hentet fra GitHubs REST-API med
`analyse/ukejobb/u1_hent.py` 17.11.2026 kl. 23:11–23:20 UTC, i 877 kall.
Svarene slik de kom, er ikke arkivert: de bærer navn og e-post på den
som committet, og commit-meldingene. Én redusert kropp er arkivert, med
id-er, navn på workflow og jobb, hendelse, utfall, tidspunkter og steg.

| kropp | utpakket | sha256 (utpakket) |
|---|---|---|
| `data/arkiv/maling-ukejobb/2026-11-17.json.gz` | 2 296 950 B | `e676a2ec3be2a7b3c48f83bd3204525939ebba1f85e351e2e8274a8e82db063d` |

Loggen `data/arkiv/maling-ukejobb/2026-11-17.u1.logg.json` fører sha256
og lengde for hvert av de 877 svarene. Kroppen har `kjoringer` (én post
per kjøring opprettet 12.10–17.11.2026) og `jobber` (én post per jobb,
alle forsøk, med `run_id` og `steps`).

Tabellene under «Utskriften» er utskriften av
`analyse/ukejobb/u2_tabeller.py`, uendret. Skriptet leser bare kroppen.

**Slik er tallene regnet.** En kjøring hører til vinduet etter datoen i
`created_at` (UTC). Workflowen er siste ledd i `path`. For hver jobb er
varigheten `completed_at` minus `started_at` i hele sekunder. En jobb
med `conclusion` lik `skipped`, eller uten ett av tidspunktene, teller
ikke. «Minutter rundet opp per jobb» er varigheten delt på 60 og rundet
opp til nærmeste hele minutt, minst 1, summert over jobbene. «Timer
etter cron» er `created_at` minus siste cron-tidspunkt for workflowen
til og med `created_at`.

Cron-tidene (UTC) er `utloser.schedule` i datarepoets
`.github/jobber.yml` 17.11.2026: `samle.yml` mandag 05:00 og tirsdag
19:00, `tilsyn.yml` 06:00, `daglig.yml` 05:23, `luseinnkomst.yml` 04:41,
`ais-manifest.yml` 08:17, `auksjon.yml` 06:17, `havbruksfond.yml` 06:41,
14:41 og 20:41, `oppslag.yml` onsdag 06:00, `speil.yml` mandag 07:00 og
tirsdag 21:00, og `stempel.yml` søndag 03:00.

## STOPP-regelen

Skrevet 17.11.2026 kl. 23:18 UTC, mens hentingen gikk og før den fulle
kroppen var regnet på. Kjent på det tidspunktet: én prøvedag (16.11) ga
56 minutter rundet opp per jobb, `billable` i API-et var 0 for de tre
kjøringene som ble spurt, og innsamlingen startet 13:25 UTC 16.11 og
13:41 UTC 09.11.

Målingen stopper og rapporterer, i stedet for at jobben bygges, hvis:

1. Summen for 30 døgn, rundet opp per jobb, ligger utenfor 1 200–2 000
   minutter. Heine leste ca. 1 600 av 2 000 under Billing 16.11.2026.
   Et avvik på mer enn en firedel betyr at regelen «hver jobb rundes
   opp til hele minutter» ikke beskriver regningen, og et anslag for
   ukejobben bygget på den ville vært et gjett.
2. Dagens forbruk pluss anslaget for ukejobben går over 2 000 minutter
   per 30 døgn. Jobben får i så fall ikke plass i gratiskvoten, og
   hvordan den skal lages, er Heines avgjørelse.
3. Kroppen mangler jobbene for en kjøring i vinduet, eller en kjøring
   kom to ganger. `u1_hent.py` stopper selv på begge.

En mandag uten planlagt innsamling i 0c er et funn, ikke en stopp.

**Utfall:** ingen av dem. Summen er 1 321 minutter (F0a.1), innenfor
1 200–2 000. Med ukejobben blir det ca. 1 350 (F0a.5), og ca. 1 670 i
takten fra første halvdel av november (F0a.3). Ingen kjøring i vinduet
mangler jobber. Alle seks mandagene hadde en planlagt innsamling.

## De tre sterkeste funnene

**1. Ukejobben får plass.** Datarepoet brukte 1 321 minutter på de 30
døgnene 18.10–16.11, regnet per jobb og rundet opp, og ukejobben legger
til ca. 27 (F0a.1, F0a.5). *Hvorfor sterkest:* summen er regnet av 764
jobber i en arkivert kropp, og den tåler at anslaget for ukejobben er
feil med en faktor ti. *Svakere:* avrundingsregelen er GitHubs
beskrivelse, ikke holdt mot regningen (F0a.4), og Heines 1 600 treffes
bare av takten 1.–16.11 (F0a.3).

**2. Tilsynet har ikke kjørt før kl. 12 UTC de to siste onsdagene.**
Den planlagte kjøringen startet 13:23 og 13:04 UTC onsdag 04.11 og 11.11
(F0c.3). En frist som skal gi rødt tilsyn «senest onsdag kl. 12 UTC»,
nås ikke av onsdagens kjøring slik cron står i dag. *Hvorfor sterkt:*
alle fem onsdagene er i kroppen, og de to seneste startene er de to
siste ukene. *Svakere:* fem onsdager er fem observasjoner.

**3. `.komplett.ots` har fjernet årsaken til feilen 11.11, men ingenting
prøver den.** Oppgraderingen skrives som en kopi, originalen står, og
prøven som ble rød, er grønn med begge i treet (F0b.2). Det som står
igjen, er at ingen kode holder en `.komplett.ots` mot fila, at
registreringens egen `.ots` fortsatt er den oppgraderte, og at uke 47
må oppgraderes for hånd (F0b.3). *Svakere:* dette er lest i kodrepoet og
git-historikken, ikke holdt mot en arkivert kropp.

## 0a. Actions-minuttene

**F0a.1 — 1 321 minutter på 30 døgn. MÅLT.** Kjøringene opprettet
18.10–16.11.2026 er 705, med 764 jobber som kjørte og 20 som ble hoppet
over. Jobbtiden er 881,0 minutter, og rundet opp per jobb 1 321. Kropp:
`maling-ukejobb/2026-11-17.json.gz`, sha256 `e676a2ec…063d`.
Feil hvis: summen av `ceil(sekunder / 60)`, minst 1, over jobbene i
vinduet ikke er 1 321.

**F0a.2 — Fire workflows står for 72 %. MÅLT.** `bygg.yml` 271 minutter
på 18 kjøringer, `havbruksfond.yml` 253 på 80, `speil.yml` 217 på 210 og
`stempel.yml` 210 på 201. De to siste har en medianjobb på 16 og 29
sekunder og betaler ett minutt hver gang. Kropp som F0a.1.
Feil hvis: en av de fire summene er en annen, eller de fire ikke er de
største.

**F0a.3 — Første halvdel av november gikk i en takt på 1 641 minutter
per 30 døgn. MÅLT.** Kjøringene opprettet 01.11–16.11.2026 ga 875
minutter rundet opp per jobb på 16 døgn. Ukene er ujevne: 232, 214, 485
og 308 minutter i de fire hele ukene 43–46. Kropp som F0a.1.
Feil hvis: summen for de 16 døgnene ikke er 875.

Heine leste ca. 1 600 av 2 000 under Billing 16.11.2026. Om det tallet
er månedens forbruk regnet opp til 30 døgn, er UBELAGT: lesingen er ikke
arkivert. 1 641 passer med det; 1 321 gjør det ikke.

**F0a.4 — API-et oppgir ikke fakturerte minutter. EKSTERN.**
`/actions/runs/<id>/timing` svarte `billable` med `total_ms` 0 for tre
kjøringer 17.11.2026 (44139563172, 42627615966 og 39238477963), mens
`run_duration_ms` var 23 000, 89 000 og 77 000.
`/users/<bruker>/settings/billing/usage` og `…/billing/actions` svarte
403 for tokenet. Svarene er ikke arkivert. Regelen «hver jobb rundes
opp til hele minutter» er lest i GitHubs dokumentasjon og ikke holdt mot
en regning.

**F0a.5 — Ukejobben legger til ca. 27 minutter per 30 døgn. MÅLBAR.**
Regnet slik:

- Den starter etter hver ferdige kjøring av innsamlingen, og
  innsamlingen kjørte 9 ganger i vinduet (MÅLT, kropp som F0a.1: fem
  mandager og fire tirsdager, alle planlagte). Med én reservekjøring i
  uka kommer 30/7 = 4,3 til: 13,3 kjøringer per 30 døgn.
- Åtte steg den deler med de to jobbene har en sum av medianene på 28
  sekunder og en sum av de lengste på 204 sekunder (MÅLT, kropp som
  F0a.1). Stegene er «Set up job», «Hent datarepoet (her havner
  snapshotene)», «Hent koden fra kodrepoet», «Sett opp Python» og
  «Installer avhengigheter» i `samle.yml`, og «Installer
  OpenTimestamps-klienten», «Stemple» og «Commit stemplene» i
  `stempel.yml`. Varigheten er stegets `completed_at` minus
  `started_at`, for steg med `conclusion` lik `success` i de grønne
  kjøringene i vinduet; medianen og den lengste tas per steg.
- `anslag.py --torrkjor` tok 10,5 sekunder på Mac-en 17.11.2026, med 35
  sekunder prosessortid. `skaar_anslag.py --torrkjor` tok 0,1 sekunder,
  fordi ingen uke er avgjort ennå; når den leser panelet, blir den som
  `anslag.py`. På en maskin med to kjerner er det anslått til 20–40
  sekunder hver. Ikke målt i Actions.
- 28 + 40 + 40 = 108 sekunder gir to minutter per kjøring: 13,3 × 2 =
  27 minutter. Tre minutter per kjøring gir 40.

Feil hvis: første kjøring i Actions tar mer enn tre minutter, eller
jobben starter oftere enn 14 ganger på 30 døgn.

## 0b. Stemplene og feilen 11.11.2026

Alt i dette avsnittet er MÅLBAR: filene ligger i kodrepoets
`predictions/maskin/` og i git-historikken der, ikke i arkivet.
Stempelmanifestene i `data/stempler/` fører summene av dem.

**F0b.1 — Feilen.** Commit `fa18c55` (11.11.2026 kl. 07:49 UTC) byttet
ut to stempler med oppgraderte: `2026-46.yml.ots` gikk fra 1 050 til
4 159 B (sha256 `f75df113…` til `01d603a7…`), og
`FORHANDSREGISTRERING.md.ots` fra 980 til 3 088 B (`6939de7a…` til
`956be059…`). «Tester» ble rød på den commiten (kjøring 42982282553):
`tests/test_anslag.py::test_forseglede_ukefiler_er_uendret`, med
meldingen «2026-46.yml.ots er byttet ut», én feilet og 2 307 grønne.
`forseglinger.tsv` fører `ots_sha256` `f75df113…` for uke 46, og fila
hadde en annen sum. Commit `c415868` (kl. 18:14 UTC) la originalen
tilbake, og «Tester» ble grønn (kjøring 43075834903). Manifestene
`2026-11-10.7` og `2026-11-11.2` i `data/stempler/` fører begge summene
for begge filene.
Feil hvis: `git show fa18c55 --stat` viser andre filer eller størrelser,
eller manifestene fører andre summer.

**F0b.2 — Hva `.komplett.ots` har løst.** `stempel.oppgrader()`
(`stempel.py`) oppgraderer en kopi i en midlertidig mappe og skriver den
som `<fil>.komplett.ots`. Originalen røres ikke, så linja i
`forseglinger.tsv` holder, og det blir ingen `.bak` i treet.
`skaar_anslag.py --oppgrader` gjør dette for hver `.ots` i mappa som
ikke har en `.komplett.ots`. I dag (`b1d0a5e`) er `2026-46.yml.ots`
originalen, med summen som er ført, og `2026-46.yml.komplett.ots`
(4 159 B, Bitcoin-blokkene 975346, 975350 og 975379) er byte for byte
stempelet `fa18c55` la i originalens sted. Prøven som ble rød 11.11, er
grønn med begge i treet.
Feil hvis: sha256 av `2026-46.yml.ots` ikke er `f75df113…a332fef00`,
eller `.komplett.ots` ikke er `01d603a7…6d7a0e13`.

**F0b.3 — Hva som står igjen.**

1. `FORHANDSREGISTRERING.md.ots` ble ikke lagt tilbake. Den er fortsatt
   det oppgraderte stempelet (3 088 B, `956be059…`), byte for byte lik
   `FORHANDSREGISTRERING.md.komplett.ots`. Det ventende stempelet fra
   10.11 (980 B, `6939de7a…`) finnes i git (`d469d8c`) og i manifestet
   `2026-11-10.7`. Ingen prøve holder den fila mot en ført sum:
   `test_forhandsregistreringen_er_den_som_ble_stemplet` krever bare at
   summen i stempelet er filas, og det gjelder begge. Beviset er ikke
   svekket, men «originalen endres aldri» holder ikke for denne fila.
2. Ingen kode og ingen prøve holder en `.komplett.ots` mot noe.
   `skaar_anslag.segl()` setter `stempel_komplett` etter om fila finnes.
   En `.komplett.ots` for en annen sum, eller uten en blokk, ville stått
   som komplett. Holdt for hånd 17.11: begge de to som finnes, er
   stemplet for riktig fil og bærer blokker.
3. `2026-47.yml.ots` venter (595 B, ingen blokk). Prøvd 17.11.2026 kl.
   23:15 UTC på en kopi utenfor repoet: `ots upgrade` svarte «Success!
   Timestamp complete», med attestasjon fra tre kalendre. Stempelet kan
   altså oppgraderes nå. Ukejobben kan ikke gjøre det: uke 47 ligger i
   kodrepoet, og jobben skal bare skrive i datarepoet.
4. `--oppgrader` leser én mappe. Når ukene ligger to steder, må det
   bestemmes hvilken den oppgraderer.
5. `ots upgrade <fil>.ots` for hånd bytter fortsatt ut originalen og
   legger igjen `<fil>.ots.bak`. Prøven fanger en byttet ukefil-`.ots`,
   som 11.11. `.bak`-fila er usporet, så `kodeproveniens.rent()` sier at
   treet ikke er rent, og `anslag.py` nekter å lage neste uke. I
   `~/kystloggen-utkast/ots-oppgradert/` ligger fem filer fra 10.–17.11,
   blant dem to `.ots.bak` med summene til de to originalene.

## 0c. Når innsamlingen og tilsynet starter

**F0c.1 — Mandagens innsamling har startet 5,6 til 8,7 timer etter
cron. MÅLT.** Cron er mandag kl. 05:00 UTC. De seks mandagene
12.10–16.11.2026 ble kjøringen opprettet 12:52, 10:34, 10:49, 13:13,
13:41 og 13:25 UTC: 7,9, 5,6, 5,8, 8,2, 8,7 og 8,4 timer etter. Alle
seks ble grønne, og jobben tok 74 til 85 sekunder i de fem som ligger i
vinduet for 0a. Kropp: `maling-ukejobb/2026-11-17.json.gz`, sha256
`e676a2ec…063d`; kjøringene av `samle.yml` med `event` lik `schedule`.
Feil hvis: en av de seks `created_at` er en annen, eller en mandag
mangler.

**F0c.2 — Tirsdagens gjenkjøring har startet 3,2 til 4,9 timer etter
cron. MÅLT.** Cron er tirsdag kl. 19:00 UTC. Fem tirsdager,
13.10–10.11.2026: 23:12, 22:10, 22:52, 23:52 og 23:56 UTC. Den seneste
ble ferdig 23:56:51, tre minutter før onsdag. Kropp som F0c.1.
Feil hvis: en av de fem `created_at` er en annen.

**F0c.3 — Tilsynet har startet onsdager mellom 10:43 og 13:23 UTC.
MÅLT.** Cron er hver dag kl. 06:00 UTC. De fem onsdagene
14.10–11.11.2026: 10:45, 10:43, 11:44, 13:23 og 13:04. To av fem er
etter kl. 12:00. Over alle 35 planlagte kjøringene er forsinkelsen 3,8
til 9,0 timer, med median 5,9. Kropp som F0c.1; kjøringene av
`tilsyn.yml` med `event` lik `schedule`.
Feil hvis: en av de fem `created_at` er en annen.

**F0c.4 — Kveldens cron er mindre forsinket enn morgenens. MÅLT.**
Cron-tidene 03:00–08:17 UTC har en forsinkelse fra 3,8 til 10,6 timer,
over ni workflows. De to cron-tidene tirsdag kveld, 19:00 for
`samle.yml` og 21:00 for `speil.yml`, har fra 2,7 til 4,9 timer, over
fem kjøringer hver. `havbruksfond.yml` er ikke med: den har tre
cron-tider per døgn, og en kjøring som er mer forsinket enn avstanden
til neste, kan ikke plasseres. Kropp som F0c.1; cron-tidene står i
`CRON` i skriptet, lest av `jobber.yml`.
Feil hvis: en planlagt kjøring av de ni workflowene ligger utenfor
intervallet for sin cron-tid.

## Utskriften

`analyse/ukejobb/u1_hent.txt`:

    Actions-kjøringer i heinenordboe-cloud/havbruk-radar-data, opprettet 2026-10-12 … 2026-11-17 (UTC)
      API-kall: 877 (ingen svar arkivert; sha256 per svar i loggen)
      sha256 over svarene (linjer «url sha256», i hentet rekkefølge): f3518a0817c9456c9da0d66d9c07856786e736448a85bc16225ab704b74d2b58
      kjøringer: 840   jobber (alle forsøk): 922
      redusert kropp: maling-ukejobb/2026-11-17.json.gz, 2296950 B utpakket, sha256 e676a2ec3be2a7b3c48f83bd3204525939ebba1f85e351e2e8274a8e82db063d
      logg: maling-ukejobb/2026-11-17.u1.logg.json

`analyse/ukejobb/u2_tabeller.txt`:

Kropp: maling-ukejobb/2026-11-17.json.gz, 2296950 B utpakket, sha256 e676a2ec3be2a7b3c48f83bd3204525939ebba1f85e351e2e8274a8e82db063d
  kjøringer opprettet 2026-10-12 … 2026-11-17: 840, jobber (alle forsøk): 922
  kjøringer uten jobber i kroppen: 1
  kjøringer som ikke var ferdige ved hentingen: 0

### 0a. Jobbtid per workflow, kjøringer opprettet 2026-10-18 … 2026-11-16 (30 døgn)

| workflow | kjøringer | jobber som kjørte | hoppet over | jobbtid, minutter | minutter rundet opp per jobb | andel | median jobb, s | lengste jobb, s |
|---|---|---|---|---|---|---|---|---|
| bygg.yml | 18 | 18 | 0 | 262,8 | 271 | 20,5 % | 926 | 1187 |
| havbruksfond.yml | 80 | 80 | 0 | 214,8 | 253 | 19,2 % | 145 | 337 |
| speil.yml | 210 | 210 | 0 | 66,6 | 217 | 16,4 % | 16 | 143 |
| stempel.yml | 201 | 201 | 0 | 107,1 | 210 | 15,9 % | 29 | 169 |
| auksjon.yml | 30 | 30 | 0 | 87,6 | 105 | 7,9 % | 181 | 277 |
| daglig.yml | 32 | 76 | 0 | 51,0 | 85 | 6,4 % | 37 | 233 |
| luseinnkomst.yml | 17 | 32 | 0 | 26,7 | 39 | 3,0 % | 37 | 248 |
| tilsyn.yml | 37 | 37 | 0 | 7,3 | 37 | 2,8 % | 11 | 36 |
| publiser.yml | 22 | 22 | 20 | 21,4 | 33 | 2,5 % | 60 | 197 |
| test.yml | 23 | 23 | 0 | 6,4 | 23 | 1,7 % | 16 | 30 |
| ais-manifest.yml | 19 | 19 | 0 | 10,7 | 21 | 1,6 % | 25 | 100 |
| samle.yml | 9 | 9 | 0 | 8,6 | 14 | 1,1 % | 74 | 85 |
| oppslag.yml | 2 | 2 | 0 | 7,5 | 8 | 0,6 % | 224 | 226 |
| revisjon.yml | 2 | 2 | 0 | 1,0 | 2 | 0,2 % | 29 | 31 |
| gjenoppretting.yml | 2 | 2 | 0 | 0,9 | 2 | 0,2 % | 27 | 29 |
| vilkar.yml | 1 | 1 | 0 | 0,7 | 1 | 0,1 % | 42 | 42 |
| **sum** | 705 | 764 | 20 | 881,0 | 1321 | 100,0 % |  |  |

Sum rundet opp per jobb: 1321 minutter på 30 døgn. Per 30 døgn: 1321.
Kjøringer i vinduet med mer enn ett forsøk: 0.
Kjøringer i vinduet uten jobber i kroppen: 0.
Av dette opprettet 2026-11-01 … 2026-11-16: 875 minutter på 16 døgn. I samme takt per 30 døgn: 1641.

| ISO-uke | minutter rundet opp per jobb |
|---|---|
| 2026-W42 | 26 |
| 2026-W43 | 232 |
| 2026-W44 | 214 |
| 2026-W45 | 485 |
| 2026-W46 | 308 |
| 2026-W47 | 56 |

### 0a. Stegene ukejobben har felles med innsamlingen og tidsstemplingen

| workflow | steg | kjøringer | median, s | lengste, s |
|---|---|---|---|---|
| samle.yml | Samle inn | 9 | 45 | 55 |
| samle.yml | Hent datarepoet (her havner snapshotene) | 9 | 8 | 15 |
| samle.yml | Installer avhengigheter | 9 | 4 | 11 |
| samle.yml | Hent koden fra kodrepoet | 9 | 3 | 3 |
| samle.yml | Sett opp Python | 9 | 2 | 5 |
| samle.yml | Commit snapshot | 9 | 2 | 4 |
| samle.yml | Set up job | 9 | 1 | 3 |
| samle.yml | Signal til overvåkingen | 5 | 1 | 1 |
| samle.yml | Varsle i issue | 9 | 1 | 2 |
| samle.yml | Sjekk valgfrie secrets | 9 | 0 | 1 |
| samle.yml | Post Sett opp Python | 9 | 0 | 1 |
| samle.yml | Post Hent koden fra kodrepoet | 9 | 0 | 1 |
| samle.yml | Post Hent datarepoet (her havner snapshotene) | 9 | 0 | 1 |
| samle.yml | Complete job | 9 | 0 | 0 |
| stempel.yml | Hent datarepoet | 201 | 9 | 90 |
| stempel.yml | Stemple | 201 | 5 | 144 |
| stempel.yml | Hent koden fra kodrepoet | 201 | 3 | 44 |
| stempel.yml | Installer OpenTimestamps-klienten | 201 | 3 | 13 |
| stempel.yml | Commit stemplene | 201 | 2 | 10 |
| stempel.yml | Set up job | 201 | 1 | 3 |
| stempel.yml | Sett opp Python | 201 | 0 | 1 |
| stempel.yml | Post Sett opp Python | 201 | 0 | 1 |
| stempel.yml | Post Hent koden fra kodrepoet | 201 | 0 | 1 |
| stempel.yml | Post Hent datarepoet | 201 | 0 | 2 |
| stempel.yml | Complete job | 201 | 0 | 1 |

Hele jobben i samle.yml, grønne kjøringer: 9, median 74 s, lengste 85 s.
Hele jobben i stempel.yml, grønne kjøringer: 201, median 29 s, lengste 169 s.
Sum av medianene for de 8 stegene ukejobben også har (oppsett, begge repoene, Python, pakkene, klienten, et stempel, en commit): 28 s. Sum av de lengste: 204 s.

### 0a. Hvor ofte ukejobben ville startet: ferdige kjøringer av innsamlingen

| opprettet (UTC) | ukedag | hendelse | utfall | jobb, s |
|---|---|---|---|---|
| 2026-10-19T10:34:58Z | man | schedule | success | 74 |
| 2026-10-20T22:10:02Z | tir | schedule | success | 24 |
| 2026-10-26T10:49:59Z | man | schedule | success | 85 |
| 2026-10-27T22:52:26Z | tir | schedule | success | 23 |
| 2026-11-02T13:13:38Z | man | schedule | success | 83 |
| 2026-11-03T23:52:26Z | tir | schedule | success | 25 |
| 2026-11-09T13:41:01Z | man | schedule | success | 84 |
| 2026-11-10T23:56:10Z | tir | schedule | success | 38 |
| 2026-11-16T13:25:52Z | man | schedule | success | 77 |

Kjøringer av samle.yml i vinduet: 9 på 30 døgn.

### 0c. Mandagens innsamling og tirsdagens gjenkjøring: når de startet

| ISO-uke | cron (UTC) | opprettet (UTC) | timer etter cron | jobben ferdig | utfall | kjøring |
|---|---|---|---|---|---|---|
| 2026-W42 | man 12.10 05:00 | man 12.10 12:52:21 | 7,9 | 12:53:37 | success | 38251786809 |
| 2026-W42 | tir 13.10 19:00 | tir 13.10 23:12:49 | 4,2 | 23:13:20 | success | 38482836256 |
| 2026-W43 | man 19.10 05:00 | man 19.10 10:34:58 | 5,6 | 10:36:14 | success | 39238477963 |
| 2026-W43 | tir 20.10 19:00 | tir 20.10 22:10:02 | 3,2 | 22:10:29 | success | 39506073668 |
| 2026-W44 | man 26.10 05:00 | man 26.10 10:49:59 | 5,8 | 10:51:27 | success | 40310456042 |
| 2026-W44 | tir 27.10 19:00 | tir 27.10 22:52:26 | 3,9 | 22:52:51 | success | 40598063982 |
| 2026-W45 | man 02.11 05:00 | man 02.11 13:13:38 | 8,2 | 13:15:03 | success | 41451137811 |
| 2026-W45 | tir 03.11 19:00 | tir 03.11 23:52:26 | 4,9 | 23:52:54 | success | 41742525517 |
| 2026-W46 | man 09.11 05:00 | man 09.11 13:41:01 | 8,7 | 13:42:28 | success | 42627615966 |
| 2026-W46 | tir 10.11 19:00 | tir 10.11 23:56:10 | 4,9 | 23:56:51 | success | 42927367172 |
| 2026-W47 | man 16.11 05:00 | man 16.11 13:25:52 | 8,4 | 13:27:26 | success | 43875675474 |

### 0c. Tilsynet: når den planlagte kjøringen startet, per ukedag

| ukedag | kjøringer | tidligst | senest | hver kjøring (UTC) |
|---|---|---|---|---|
| man | 5 | 11:24 | 14:31 | 19.10 11:24, 26.10 11:42, 02.11 13:59, 09.11 14:31, 16.11 14:08 |
| tir | 5 | 10:31 | 15:01 | 20.10 10:31, 27.10 11:10, 03.11 13:08, 10.11 13:52, 17.11 15:01 |
| ons | 5 | 10:43 | 13:23 | 14.10 10:45, 21.10 10:43, 28.10 11:44, 04.11 13:23, 11.11 13:04 |
| tor | 5 | 10:28 | 14:07 | 15.10 10:28, 22.10 10:45, 29.10 11:53, 05.11 13:37, 12.11 14:07 |
| fre | 5 | 10:15 | 13:31 | 16.10 10:15, 23.10 10:36, 30.10 11:46, 06.11 13:21, 13.11 13:31 |
| lør | 5 | 09:49 | 12:37 | 17.10 09:49, 24.10 09:54, 31.10 11:20, 07.11 11:59, 14.11 12:37 |
| søn | 5 | 10:01 | 13:03 | 18.10 10:01, 25.10 10:17, 01.11 12:10, 08.11 12:20, 15.11 13:03 |

### 0c. Forsinkelsen etter cron, alle planlagte kjøringer med kjent cron

Ikke med, fordi de har flere cron-tider per døgn: havbruksfond.yml.

| cron (UTC) | workflow | kjøringer | minst, timer | median, timer | mest, timer |
|---|---|---|---|---|---|
| 03:00 | stempel.yml | 5 | 4,9 | 7,1 | 7,6 |
| 04:41 | luseinnkomst.yml | 15 | 6,7 | 7,9 | 9,2 |
| 05:00 | samle.yml | 6 | 5,6 | 8,0 | 8,7 |
| 05:23 | daglig.yml | 34 | 4,1 | 6,3 | 9,3 |
| 06:00 | tilsyn.yml | 35 | 3,8 | 5,9 | 9,0 |
| 06:00 | oppslag.yml | 1 | 7,5 | 7,5 | 7,5 |
| 06:17 | auksjon.yml | 37 | 4,3 | 6,8 | 9,9 |
| 07:00 | speil.yml | 6 | 6,7 | 9,4 | 10,0 |
| 08:17 | ais-manifest.yml | 15 | 6,6 | 8,1 | 10,6 |
| 19:00 | samle.yml | 5 | 3,2 | 4,2 | 4,9 |
| 21:00 | speil.yml | 5 | 2,7 | 3,3 | 4,1 |


## Etterskrift 17.11.2026: kontrolløren

Kontrolløren (`.claude/agents/kontrollor.md`) fikk bare stien til dette
dokumentet og trakk tre påstander med frø 3147045608: F0a.2, første punkt
i F0a.5 og F0c.2. Alle tre ga treff mot kroppen `e676a2ec…063d`. Den ble
kjørt én gang.

Én merknad om ordlyden i F0a.2: «betaler ett minutt hver gang» gjelder
ikke hver jobb. Av 210 jobber i `speil.yml` ble 206 rundet opp til ett
minutt, én til to og tre til tre. Av 201 i `stempel.yml` ble 195 til ett
minutt, tre til to og tre til tre. Summene i F0a.2 er ikke berørt.
Tellingen er regnet på nytt av kroppen etter merknaden, med samme svar.

Kontrolløren etterprøver at tallene følger av den reduserte kroppen. At
kroppen gjengir de 877 API-svarene, er ikke etterprøvd: svarene er ikke
arkivert, og loggen fører bare sha256 og lengde for hvert.

Teksten over er ikke endret.
