# Runbook — drift, sikring og veien til nettside

## Hvor dataene faktisk ligger

To repo:

    havbruk-radar        offentlig — koden. Dette repoet.
    havbruk-radar-data   privat — historikken. Snapshotene.

Innsamlingen kjøres FRA datarepoet, som henter denne koden ved hver
kjøring. Retningen er et sikkerhetsvalg: et privat repo som leser
offentlig kode trenger ingen hemmelighet.

Historikken finnes dermed på minst tre steder uten at du gjør noe:
GitHub, klonen på din egen maskin, og hver Actions-kjøring. Et git-repo
er ikke en database du kan miste halvparten av — hver klon er en
fullstendig kopi. Det er den viktigste grunnen til at git ble valgt
over en database her.

Kjøre innsamlingen lokalt:

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data python run.py

Uten miljøvariabelen skrives det til `data/` i dette repoet, som er
gitignorert nettopp for at en lokal kjøring ikke skal havne i kodrepoet.

## Lokalt oppsett

Actions kjører Python 3.12. Kjør samme versjon lokalt, ellers finner du
versjonsforskjeller i produksjon mandag morgen i stedet for på skjermen din.
`.python-version` i rota sier hvilken versjon som gjelder; pyenv og de fleste
verktøy plukker den opp automatisk.

    brew install python@3.12          # om nødvendig
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    python -m pytest tests/ -q        # skal være grønt før du pusher

Avhengighetene er pinnet eksakt. Oppgradering er en bevisst handling:
bump versjonen i `requirements.txt`, kjør testene, commit.

## Nøkler: to steder, begge må stemme

Nøkler ligger aldri i fil. De refereres som `${NAVN}` i `config.yml` og
hentes fra miljøet — `~/.havbruk.env` lokalt, Actions-secrets i
datarepoet i drift. I dag er det to: `BARENTSWATCH_CLIENT_ID` og
`BARENTSWATCH_CLIENT_SECRET`.

De kreves av to kilder — `lusetall` og `sjotemperatur` — og er deklarert
i BEGGE blokkene i `config.yml`, ikke bare i den ene. Det er ikke
duplisering for duplikatets skyld: `core/miljo.py` spør per AKTIV kilde,
så en nøkkel som bare sto under `lusetall` ville vært usynlig den dagen
`lusetall` slås av og `sjotemperatur` står igjen alene. Feilmeldingen
navngir da begge config-stiene, som er riktig — det er to kilder som
mister innloggingen, ikke én.

**I drift er det to ledd, ikke ett.** Secreten må finnes i datarepoets
innstillinger, OG den må eksponeres til «Samle inn»-steget i `samle.yml`
via `env:`. Mangler det ene, ser det ut som det andre er i orden.
`${{ secrets.X }}` på en secret som ikke finnes blir tom streng — så
workflowen setter variabelen, og loggen sier likevel «er ikke satt».

Feiler en kjøring på dette, stopper `run.py` før innsamlingen og lister
ALLE manglende variabler samlet:

    2 miljøvariabel(er) kreves av en aktiv kilde, men er ikke satt:

      BARENTSWATCH_CLIENT_ID
          kreves av config-nøkkelen 'kilder.lusetall.client_id'

Sjekken ligger foran frekvensvakten med vilje: en manglende nøkkel er
feil i oppsettet, ikke i denne kjøringen, og skal si fra selv om kilden
uansett ville blitt hoppet over i dag. Se `core/miljo.py` og
`docs/beslutninger/2026-08-24-miljovariabler-sjekkes-for-innsamling.md`.

En ny kilde som trenger en nøkkel gjør tre ting, og ingen av dem er i
`core/`: skriver `${NAVN}` i sin blokk i `config.yml`, legger secreten i
datarepoet, og legger linja i `env:` i `samle.yml`. Sjekken finner den
selv.

## Sikring — det som faktisk kan gå galt

Rangert etter sannsynlighet, ikke etter hvor dramatisk det høres ut.

**1. Du mister GitHub-kontoen.** Klart mest sannsynlige tap. Nytt
telefonnummer, mistet 2FA-app, ingen recovery codes lagret.
→ Slå på 2FA, last ned recovery codes, legg dem et sted som ikke er
telefonen din. Ti minutter, én gang.

**2. En kilde slutter å levere og du merker det ikke.** Feilisoleringen
gjør jobben grønn selv når en kilde er død. `core/health.py` løser dette:
en kilde som kaster gir rød jobb og e-post fra GitHub.

Et KVALITETSVARSEL gjør det ikke — det blir en ::warning:: i
Annotations-panelet og et `DELVIS:`-prefiks i commit-meldingen. Da må du
faktisk se etter det, og commit-meldingen er stedet: den ligger i
GitHub-appen på telefonen uansett. Se
`docs/beslutninger/2026-08-31-tilsyn-feiler-ikke-jobben.md`.

**3. Actions deaktiveres.** GitHub slår av planlagte kjøringer etter 60
dager uten commit-aktivitet på default branch. Kun commits teller — ikke
tagger, issues eller PR-er.

To ting gjør at dette trolig ikke rammer deg: innsamlingen committer et
snapshot hver uke, og GitHubs egen formulering gjelder eksplisitt
*offentlige* repo. Datarepoet er privat og er sannsynligvis ikke omfattet.

"Trolig" og "sannsynligvis" er med vilje — dette er ikke verifisert i
praksis. Får du e-post om deaktivering: åpne datarepoet og trykk enable,
ellers står innsamlingen stille.

**4. Du ødelegger historikken selv.** `git push --force` etter en rebase.
→ Slå på branch protection på `main` i repo-innstillingene.

**5. GitHub forsvinner.** Minst sannsynlig. Speilingen til GitLab
(<https://gitlab.com/NordboeRadar-group/havbruk-radar-data>) er en
**bevist backup** fra 06.10.2026. Speilingen har pushet jevnlig siden
29.09.2026. Før det var `SPEIL_URL` og `SPEIL_TOKEN` ikke satt, og jobben
hadde aldri lyktes.

Gjenopprettingsprøven 06.10.2026 klonet fra GitLab til en tom mappe og
sammenlignet med `origin/main` på GitHub. Den skrev ikke til noen remote.

| Sjekk | Resultat |
|---|---|
| HEAD | `66d88dc` på begge |
| Historikk | 125 commits, alle hasher like og i samme rekkefølge |
| Rot-treet | likt (`a1e704c`), og `git fsck --full --strict` er ren |
| `data/raw` | 1850 filer, like i git-treet og i sha256 på disk |
| `data/arkiv` | 4858 filer, like i git-treet og i sha256 på disk |
| `data/changelog` | 1774 filer, like i git-treet og i sha256 på disk |
| `run.py --torrkjor` mot klonen | exit 0, alle 11 kilder ok, klonen urørt etterpå |
| Lesesidene mot klonen | samme utfall som mot GitHub-kopien, linje for linje |

`--torrkjor` hopper over frekvensvakten og `finnes_allerede()` og leser
derfor nesten ikke datamappa. Lesesidene ble kjørt for seg for å dekke
det. Mot kjøredato 2026-10-12 kjørte de `velg_forfalte`,
`finnes_allerede`, `siste_dato`, `datoer`, `previous` (antall rader og
hash), `dager_siden_ok`, `changelog.les_alt` (1 019 694 rader) og
`kodeproveniens_per_fil`.

Hva prøven IKKE dekker: at innsamlingen kan KJØRE fra GitLab. Datarepoets
`.github/workflows/` følger med i klonen, men GitLab kjører ikke GitHub
Actions. Forsvinner GitHub, er historikken trygg. Den ukentlige jobben
må da settes opp på nytt, enten med Actions på et nytt GitHub-repo eller
med GitLab CI. Til det er gjort, går det tapt én uke per uke (regel 5).

Står `speil.yml` rød, er det ikke støy: da stopper backupen fra den
dagen.

Speilworkflowen hører hjemme i DATAREPOET, ikke her — koden er allerede
offentlig og finnes i enhver klone, mens historikken er det eneste som
ikke kan skaffes på nytt. Codeberg eller GitLab, begge gratis.

Hemmelighetene heter `SPEIL_URL` og `SPEIL_TOKEN`. Det finnes ingen
bryter: `speil.yml` kjører alltid og blir rød når en av dem mangler.
Variabelen `SPEILING_AKTIV` slo jobben på fram til 05.09.2026, og ble
fjernet fordi en manglende variabel gjorde at jobben ble hoppet over uten
et ord — tre uker uten backup så ut som tre uker med. Workflowen leser den
ikke lenger. (En enda eldre versjon av dokumentasjonen sa `MIRROR_URL`,
som aldri har vært riktig.)

## Varslene som kommer til deg

Tre kanaler, og hver av dem svarer på sitt eget spørsmål:

| Kanal | Svarer på | Hvor du ser det |
|---|---|---|
| Rød jobb | En kilde mangler i snapshotet, eller noe stoppet kjøringen | E-post fra GitHub |
| Issuen «Innsamlingen trenger tilsyn» | Kjøringen endte DELVIS eller rød | Varsel fra GitHub når den opprettes eller kommenteres. Du nevnes med @ |
| `HEARTBEAT_URL` | Kjøringen skjedde i det hele tatt | E-post fra overvåkingstjenesten når signalet uteblir |
| Issuen «Publiseringen trenger tilsyn» | kystloggen.no svarte ikke som bygget sa, etter en publisering fra `publiser.yml` | Som innsamlingens issue. Se «Publisering fra GitHub» |

Issuen lages og lukkes av `.github/varsel.py` i datarepoet, som siste
steg i `samle.yml`. Den lukkes av seg selv når en kjøring som faktisk
samlet inn ender helt grønn. Tirsdagens gjenkjøring i en frisk uke rører
den ikke. Lukker du den for hånd, åpnes en ny ved neste DELVIS kjøring.

### Overvåking utenfra: `HEARTBEAT_URL`

Alle andre vakter kjører på GitHub. Blir Actions slått av, kontoen låst
eller cron droppet, tier de alle sammen — `tilsyn.yml` også. Den eneste
vakten som ikke deler skjebne med det den vokter, er en tjeneste utenfor
GitHub som venter på et signal hver uke og sier fra når det uteblir.

`samle.yml` sender et GET til `HEARTBEAT_URL` når innsamlingen skjedde:
«Samle inn» og «Commit snapshot» gikk, og `run.py` kom til slutten.
**Også når kjøringen er DELVIS.** Kvaliteten har issuen. Et
innholdsvarsel som står i ukevis ville ellers holdt overvåkingen rød i
ukevis, og da blir den mutet.

Mangler secreten, gir første steg en `::warning::` og innsamlingen går
som før. Det samme gjelder `HAVBRUK_KONTAKT`.

**Oppsett, en gang.** Eksemplet er Healthchecks.io (gratisnivå, ingen
installasjon). Cronitor og Better Stack virker likt: en URL som skal
kalles, og et varsel når den ikke blir det.
*Ikke prøvd herfra: stegene er skrevet ut fra hvordan tjenesten er
beskrevet, ikke fra et oppsett noen har gjort. Rett dem når du har gjort
det.*

1. Lag en konto på healthchecks.io med e-postadressen du vil varsles på.
2. Lag en ny «check». Navn: `havbruk-radar innsamling`.
3. Velg tidsplan som **cron**: `0 5 * * 1`, tidssone **UTC**. Det er
   mandagens innsamling i `samle.yml`.
4. **Grace time: 2 dager.** Tirsdagens gjenkjøring går 19:00 UTC, 38
   timer etter mandagen, og den skal få reparere en mandag som uteble før
   noen blir varslet. Med 2 dager kommer varselet onsdag 05:00 UTC, en
   time før `tilsyn.yml`.
5. Kopier ping-adressen (`https://hc-ping.com/<uuid>`).
6. I datarepoet: Settings → Secrets and variables → Actions → New
   repository secret. Navn `HEARTBEAT_URL`, verdi adressen. Sett også
   `HAVBRUK_KONTAKT` der hvis den mangler.
7. Kall adressen én gang for hånd for å se at checken går grønn:

       curl -fsS https://hc-ping.com/<uuid>

   En manuell kjøring av `samle.yml` sender **ikke** signal i en uke der
   alle kilder allerede er hentet: `run.py` samler ikke inn, og det er
   da signalet holdes tilbake. Første ekte signal kommer mandagen etter.

Adressen er en hemmelighet: den som har den, kan holde vakten grønn.
Den står derfor i secrets og ikke i workflowen.

## Publisering: `publiser.py`

Nettstedet ligger på **Cloudflare Pages**, prosjekt `kystloggen`,
domene `kystloggen.no`.

    python publiser.py                  # forhåndsvisning
    python publiser.py --produksjon     # kystloggen.no
    python publiser.py --uten-bygg      # bruk mappa som den er

**Første gang, og bare da:** Node.js må være installert (det gir
`npx`), og wrangler må være logget inn. Innloggingen skjer i
nettleseren, og skriptet rører ikke nøkler:

    npx wrangler@4.139.0 login

**Versjonen står med vilje.** Steg 5 kjører `npx wrangler@4.139.0`, og
innloggingen skal gjøres av den samme — tilstanden under
`~/Library/Preferences/.wrangler/` er wranglers egen, og to ulike
versjoner som skriver og leser den er to ting som kan si hver sitt.
Hvorfor den er pinnet i det hele tatt: se `WRANGLER` i `publiser.py`.
`tests/test_publiser.py` krever at tallet her og der er det samme.

Node.js er installert uten sudo: den offisielle tarballen fra
nodejs.org, sjekksum verifisert mot `SHASUMS256.txt` før utpakking, i
`~/.local/node`, med én PATH-linje i `~/.zshrc`. v24.21.0 LTS,
23.09.2026.

**Pagefind må også være installert** — samme mønster: offisiell
utgivelse for `aarch64-apple-darwin`, sjekksum sammenlignet før
utpakking, `~/.local/bin/pagefind`. Kommandoene står i
`requirements-verktoy.md`. Uten den bygges siden, men uten søk, og
**steg 4 nekter da produksjon.**

### Prosjektet ble opprettet ÉN gang, med `--force`

    npx wrangler pages project create kystloggen \
        --production-branch main --force

`--force` var nødvendig og skal IKKE gjentas. Wrangler 4.137
videresender `pages project create` til den nye Workers-baserte Pages,
som forventer å BYGGE i mappa den kjøres fra — den lette etter
`./build` og `./_site` og feilet. Vår modell er motsatt: vi laster opp
en ferdigbygget mappe.

Det mislykkede forsøket skrev to ting inn i repoet uoppfordret, og
begge ble fjernet: en `wrangler.jsonc` med feil prosjektnavn
(`havbruk-radar`) og en peker til `_site` som ikke finnes, og fem
linjer i `.gitignore`.

**`.wrangler/` står nå i `.gitignore`**, og det er ikke kosmetikk:
wrangler skriver en hurtigbuffer der hver gang den kjører, og
`publiser.py` steg 1 nekter å publisere fra et urent tre. Uten linja
ville hver eneste publisering stoppet på sin egen hurtigbuffer.

Nøklene ligger IKKE i repoet: `~/Library/Preferences/.wrangler/config/`.

    prosjekt          kystloggen
    produksjonsgren   main
    adresse           https://kystloggen.pages.dev

### Seks steg, og rekkefølgen er poenget

| # | steg | verner mot |
|---|---|---|
| 1 | sporbarhet | begge repoene rene og pushet — F15, to ganger |
| 2 | bygg | fra disk, ikke fra en cache |
| 3 | porten | ETT ukvittert funn stopper. Ingen overstyring |
| 4 | ukas tall | skrevet ut, og du må skrive «ja». Søkeindeksen målt: mangler den, nektes produksjon |
| 5 | wrangler | forhåndsvisning med mindre `--produksjon` |
| 6 | logg | én linje i `docs/publiseringslogg.tsv` i datarepoet |

`--uten-bygg` hopper over steg 2. **Den hopper ikke over porten.**

Steg 2 sender `--vakt-kjores-av "publiser.py steg 3"` til bygget, ikke
`--uten-vakt`. Begge hopper over porten i BYGGET; forskjellen er hva
bygget da skriver. Med `--uten-vakt` står «Siden skal ikke publiseres»,
som er riktig for et utviklingsbygg og var villedende midt i en
publisering der porten kjørte rent i steg 3.

Søkeindeksen måles i steg 4, på filene under `nettsted/pagefind/` — ikke
på byggerapporten, som ikke finnes med `--uten-bygg`. Produksjon nektes
uten indeks; forhåndsvisning advares. Se `docs/design/PAGEFIND.md`.

Steg 4 krever ordet `ja`, skrevet ut. Ikke `y`, ikke enter: et spørsmål
som kan besvares ved et uhell er ikke et spørsmål.

### Hvorfor begge repoene må være rene

Nettstedet er en funksjon av to ting — koden som bygger og dataene som
bygges. En publisering der ett av dem ikke kan gjøres rede for, er en
side ingen kan bygge på nytt, og da er sjekksummen i arkivlinja en
påstand uten dekning.

Skriptet kjører `git pull --ff-only` i datarepoet først, så en
publisering aldri bygger på en eldre kopi enn den som ligger på GitHub.

### Loggen

`docs/publiseringslogg.tsv` i DATAREPOET — der og ikke i koderepoet: en
publisering er en hendelse i historikken, og historikken bor der
dataene bor.

    tidspunkt  miljo  kode_commit  data_commit  uke

Skriptet skriver linja, og committer og pusher den selv (steg 6, fra
23.09.2026). `bygg.yml` og `publiser.yml` skriver den samme linja for
sine publiseringer, så loggen dekker begge veiene.

### Ingen nøkler — lokalt

`wrangler` autentiserer i nettleseren og lagrer sin egen tilstand under
`~/.config/.wrangler`. `publiser.py` leser den ikke, skriver den ikke,
og ber ikke om den.

Publiseringen fra GitHub bruker et API-token i datarepoets secrets. Det
er en annen nøkkel, med smalere rett — se under.

### Vertsnavnet i en forhåndsvisning

Bygget bruker `kystloggen.no` som kanonisk adresse. På en
forhåndsvisning betyr det at `<link rel=canonical>` peker til
produksjonsdomenet — som er riktig: forhåndsvisningen er en kopi, og
den skal ikke be en søkemotor indeksere seg selv.

Vil du ha en forhåndsvisning som oppgir SIN EGEN adresse:

    HAVBRUK_BASEURL=https://forhandsvisning.kystloggen.pages.dev \
        python publiser.py

## Publisering fra GitHub

Fra 07.10.2026 kan nettstedet bygges og legges ut fra GitHub Actions.
To workflows i DATAREPOET, og koden de kjører ligger i kodrepoet
(`publiser_ci.py`, `royktest.py`):

| Workflow | Starter | Gjør |
|---|---|---|
| **Bygg nettstedet** (`bygg.yml`) | av seg selv når innsamlingen ender grønn (også DELVIS), eller for hånd | bygger, kjører porten, legger ut til **forhåndsvisning**, lagrer byggemappa i 14 dager |
| **Publiser** (`publiser.yml`) | bare for hånd | legger et ferdig bygg ut på **kystloggen.no** og røyktester det |

Godkjenningen er at du starter `Publiser` selv. Datarepoet er privat på
GitHub Free, og der finnes ikke miljøer med påkrevd godkjenner.

**`bygg.yml` endrer ikke innsamlingen.** Den starter først når
`samle.yml` er ferdig, og den eneste skrivingen er logglinja. Bygger den
ikke, er snapshotene uansett skrevet.

Den bygger ikke når innsamlingen ikke skrev noe — tirsdagens
gjenkjøring i en frisk uke. Da står «Innsamlingen skrev ingenting nytt»
i oppsummeringen, og jobben er grønn.

### Fra mobilen

1. **Se på bygget først.** GitHub-appen → datarepoet → Actions →
   **Bygg nettstedet** → siste kjøring. Oppsummeringen viser ukas tall
   (de samme som steg 4 i `publiser.py`), sha256 over byggemappa og
   størrelsen. Forhåndsvisningen ligger på
   `https://forhandsvisning.kystloggen.pages.dev`.
2. Actions → **Publiser** → **Run workflow**.
3. `bekreft`: skriv `ja` — nøyaktig, med liten j. Pass på at telefonen
   ikke gjør den stor.
4. `run_id`: la stå tom. Da tas siste vellykkede bygg som har en
   byggemappe. Vil du legge ut et bestemt bygg, er tallet det siste i
   adressen til kjøringen (`…/actions/runs/<run_id>`).
5. **Run workflow**. Jobben laster ned bygget, sjekker sha256 mot det
   `bygg.yml` skrev, legger ut, skriver loggen og røyktester
   forsiden, nyeste uke, to lokaliteter og ett produksjonsområde.

*Ikke prøvd herfra: at GitHub-appen viser input-feltene til
`workflow_dispatch`. Gjør den ikke det, virker det samme fra
github.com i nettleseren på telefonen.*

Rød i `Publiser` betyr én av fire ting, og steget som feilet sier
hvilken: `bekreft` var ikke `ja`, summen avvek (ingenting er lastet
opp), en Cloudflare-nøkkel mangler (ingenting er lastet opp), eller
røyktesten feilet (siden ER ute — da kommer issuen «Publiseringen
trenger tilsyn», og den lukkes av neste røyktest som går).

Røyktesten leser ikke bytene: Cloudflare skriver om e-postlenken i
bunnteksten på veien ut (`/cdn-cgi/l/email-protection`, Scrape Shield),
så den levende siden er aldri byte-lik bygget. Målt 07.10.2026.

### Cloudflare-tokenet, med minst mulig rett

Én gang. *Ikke prøvd herfra: stegene følger Cloudflares beskrivelse av
Direct Upload fra CI, ikke et oppsett noen har gjort. Rett dem når du
har gjort det.*

1. dash.cloudflare.com → profilikonet → **My Profile** → **API Tokens**
   → **Create Token** → **Create Custom Token**.
2. Navn: `kystloggen publiser.yml`.
3. **Permissions**: én rad — `Account` · `Cloudflare Pages` · `Edit`.
   Ingenting annet: ingen Zone-rettigheter, ingen DNS, ingen Workers.
4. **Account Resources**: `Include` · kontoen der prosjektet
   `kystloggen` ligger. Ikke «All accounts».
5. **Client IP Address Filtering**: la stå tom. GitHubs maskiner har
   ikke faste adresser.
6. **TTL**: valgfritt. Setter du en sluttdato, blir både `bygg.yml` og
   `Publiser` røde med en autentiseringsfeil den dagen — skriv den i
   kalenderen.
7. **Continue to summary** → **Create Token**. Kopier tokenet; det vises
   bare én gang.
8. Konto-ID-en: dash.cloudflare.com → **Workers & Pages**, eller
   adressen når du står i kontoen (`dash.cloudflare.com/<konto-id>/…`).
   Den er ikke hemmelig, men legges ved siden av tokenet.
9. Datarepoet → Settings → Secrets and variables → Actions → **New
   repository secret**, to ganger:

       CLOUDFLARE_API_TOKEN     tokenet
       CLOUDFLARE_ACCOUNT_ID    konto-ID-en

Mangler én av dem, stopper `last-opp` før wrangler kalles og sier
hvilken. Til de er satt, er `bygg.yml` rød i steget «Legg ut til
forhåndsvisning» — byggemappa er da likevel lagret.

Tokenet kan bare legge ut på Pages. Lekker det, kan noen bytte ut
nettstedet — men ikke røre DNS, domenet eller noe annet i kontoen.
Trekk det tilbake samme sted (My Profile → API Tokens → Roll eller
Delete).

### Lagring

GitHub Free har 500 MB til artifacts. Byggemappa er ca. 67 MB komprimert
(målt 07.10.2026: 338 MB, 9057 filer, 67,4 MB med zip -6), og lagres i 14
dager. Med ett bygg i uka ligger to–tre ute samtidig. `bygg.yml` skriver
størrelsen og summen av alt som ligger i oppsummeringen, og varsler over
80 %. Gamle bygg slettes under Actions → Management → Artifacts.

### `publiser.py` lokalt er fortsatt reserven

Alt over kan gjøres for hånd som før — `python publiser.py
--produksjon` fra maskinen, med `npx wrangler@4.139.0 login`. Bruk den
når Actions er nede, når bygget er utløpt (14 dager), når tokenet er
trukket, eller når du vil se steg 4 i terminalen før du svarer.

De to veiene skriver i samme logg. Logglinja fra `bygg.yml` flytter
datarepoets `main`; `publiser.py` tar det inn selv med `git pull
--ff-only` i steg 1.

## Når innsamlingen NEKTER å kjøre

Fra 23.09.2026 stopper `run.py` før den henter noe, hvis kjøringen ikke
kan gjøres rede for. Se `core/kodeproveniens.py` og
`docs/beslutninger/2026-09-23-kodeproveniens-per-snapshot.md`.

### Hva du ser

```
::error::Innsamlingen startet ikke: HEAD abc123def456 finnes ikke på
origin/main. Push først.
  grunnlag: fjernlageret: origin/main = 9f8e7d6c5b4a
```

`run.py` returnerer 1. **Steget i GitHub Actions feiler, workflowen
feiler, og GitHub sender e-post til den som eier repoet** — samme vei
som en hvilken som helst annen feilet planlagt kjøring.

> **Sjekk én gang at ingenting svelger exit-koden.** Har steget
> `continue-on-error: true`, eller ender kommandoen på `|| true`, blir
> en nektet kjøring usynlig. Den skal ikke det.

### Hva du gjør

1. **Push det som mangler.** Det vanligste tilfellet er at en commit
   ligger lokalt.
2. **Kjør samle.yml på nytt** — Actions → samle → Run workflow, uten
   `--tving`.

### En ny kjøring senere i uka er UKAS øyeblikksbilde

Dette er verdt å si rett ut, fordi det avgjør om en nektet mandag er en
tapt uke:

**Den er det ikke.** En nektet kjøring henter ingenting, så:

- `sist_ok` står uendret, og frekvensvakten regner kilden som forfalt
  fortsatt. Den måler når vi sist LYKTES, ikke når vi sist prøvde —
  se F8.
- `finnes_allerede()` finner ingen fil for dagen, så ingenting hoppes
  over.

En kjøring tirsdag samler derfor inn som normalt, **uten flagg**.
Snapshotet får tirsdagens dato, og det er riktig: `observed_at` for en
`henting`-partisjonert kilde ER innsamlingsdatoen. For lusetall og de
andre `verden`-partisjonerte kildene får fila uka den gjelder for, som
alltid.

Fristen er søndag. Kjører du ikke innen da, er uka tapt for godt —
CLAUDE.md regel 5.

### De tre vilkårene, og hva som kan velte dem

| vilkår | git-kommando | kan den svikte i CI? |
|---|---|---|
| git svarer | `git rev-parse HEAD` | ja, ved «dubious ownership» — avvæpnet med `-c safe.directory` på hvert kall |
| treet er rent | `git status --porcelain` | nei, `actions/checkout` gir et rent tre |
| HEAD er på origin/main | `git ls-remote origin refs/heads/main`, ellers `refs/remotes/origin/main` | nei, begge veier er målt |

**Det finnes ikke noe flagg for å hoppe over dette.** `--torrkjor` er
unntatt, og bare den: den skriver ingen fil.

## Når volumvarselet fyrer

Kjøringen er grønn, men commiten er merket `DELVIS:` og loggen har en
linje som denne — **formen er hentet fra `core/health.py`, tallene er
konstruerte, og vakten har aldri fyrt i praksis:**

    enhetsregisteret (volum 62% av referanse 27074: 16786 observasjoner, uke 1)

**Hva det betyr:** kilden svarte uten feil, men leverte 62 % av det
volumet som sist ble godkjent som friskt. Ingen exception, ingen nedetid
— nettopp derfor finnes vakten. Det typiske er at etaten har endret et
feltnavn, `parse()` finner det ikke lenger, og resten av kjeden går
grønt videre med et hull i dataene. "uke 1" er hvor mange uker på rad
nivået har vært lavt; tallet vokser til noen gjør noe.

**Ødelagt kilde eller krympet register?** Rå-arkivet svarer. Råsvaret
fra hver henting ligger i `data/arkiv/<kilde>/<dato>.json.gz`, så
sammenlign denne uka mot forrige:

    cd ../havbruk-radar-data
    zcat data/arkiv/enhetsregisteret/2026-12-14.json.gz | head -c 2000
    zcat data/arkiv/enhetsregisteret/2026-12-07.json.gz | head -c 2000

Er råsvaret omtrent like stort begge uker, men snapshotet skrumpet, er
det VÅR parse som er ødelagt — feltnavn eller struktur er endret. Er
råsvaret selv blitt mindre, har registeret faktisk krympet.

**Når kvittering er riktig:** bare i det andre tilfellet — nivået er
reelt og skal bli den nye normalen. Da:

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data python run.py --godta-volum enhetsregisteret

**Når det er å skjule en feil:** hvis råsvaret er uendret. Da er
kvittering å gjøre datatapet permanent og usynlig — vakten slutter å
mase, og hullet fortsetter uke etter uke. Fiks kilden i stedet.
Kvittering er ikke en måte å få innboksen stille på; den er en påstand
om at det lave tallet er sant.

**Etterpå:** `--godta-volum` skriver `data/health.json` i datarepoet.
Commit den — uten commit er kvitteringen borte neste gang Actions
sjekker ut repoet på nytt, og alarmen fyrer igjen mandag.

    git commit -am "Godtar volum <N> for <kilde>: <hva som faktisk skjedde>"

Skriv HVORFOR nivået ble godtatt, ikke bare at det ble det. Om fire
måneder er den commit-meldingen eneste sted som skiller "registeret
krympet" fra "vi ga opp en tirsdag".

**Det finnes ingen ekte kvittering å vise til.** Volumvakten har aldri
fyrt for noen kilde — null `--godta-volum` i hele commit-historikken per
14.09.2026 — så både tallene og begrunnelsen i eksempelet over måtte
vært oppdiktet. De er derfor tatt ut.

Fram til 14.09.2026 sto her et eksempel som så målt ut og ikke var det:

> «Godtar volum 16786 for enhetsregisteret: NACE 10.209 flyttet til eget
> register»

Ingenting av det hadde hendt. `27074` er et ekte tall — 17.08-snapshotet
— men **16786 har aldri forekommet i noe snapshot**, og 10.209 ble
aldri «flyttet til eget register». Koden er utgått i gjeldende SN2007;
innholdet ligger nå i 10.202 og 10.203. Den sto i `config.yml` i to
dager, ga **null treff hele tiden**, og ble fjernet 17.08.2026.

Legg merke til hva det gjør med eksempelet: fordi 10.209 bidro med null
rader, kunne fjerningen av den **ikke** gi noe volumfall i det hele tatt
— langt mindre et fall til 62 %. Eksempelet illustrerte ikke bare en
hendelse som ikke skjedde, men en hendelse som ikke KUNNE skje.

En ekte hendelse ligger i `sources/enhetsregisteret._varsle_tomme_sok()`:
en utgått kode svarer `200 OK` med tom liste, ikke med en feil, og
volumvakten måler totalen per kilde og ser ikke enkeltsøk. Det er den
vakten som fanget 10.209 — ikke volumvakten.

### Det nærmeste en ekte sak, og hvorfor den ikke fyrte

Enhetsregisteret falt 51 622 → 51 524 mellom 24.08 og 14.09.2026. Fallet
er ekte, målt og forklart: fem aksjeselskaper fikk `slettedato` hos Brreg
og falt ut av søket, to konkursbo kom inn. Se
`docs/KILDE-ENHETSREGISTERET.md` punkt 5.2.

**Vakten sa likevel ingenting, og det var riktig.** 0,19 % er langt over
terskelen. Saken er derfor et eksempel på et ekte fall som IKKE skal
kvitteres ut — nivået er friskt, referansen følger med opp av seg selv,
og det er ingenting å godta.

Den dagen vakten faktisk fyrer, erstatt avsnittet over med den saken.
Et kjørt eksempel er verdt mer enn et konstruert, og et konstruert som
ser kjørt ut er verre enn ingen.

## Når innholdsvarselet fyrer

Ser slik ut — som ::warning:: i Annotations, ikke som rød jobb:

    KREVER TILSYN: lusetall.har_rensefisk (tomt 172 kjøringer på rad,
    grense 13; 1777 rader leveres fortsatt, alle «False»)

Merk siste ledd: **radene kommer.** Dette er ikke en kilde som er nede
og ikke et felt som er borte — feltet leveres komplett og har sluttet å
si noe. `har_rensefisk` sto slik i 171 uker uten at noe fyrte, fordi den
gamle vakten telte rader.

Rekkefølgen når det skjer:

1. Slå opp feltet hos kilden. Sluttet den å publisere det, eller sluttet
   verden å ha det? Det er et spørsmål til kilden, ikke til koden.
2. Er svaret «kilden sluttet å levere det»: det er datatap, og det kan
   ikke hentes inn igjen. Noter det i beslutningsloggen.
3. Er svaret «verdien er legitimt konstant nå»: kvitter ut med

       HAVBRUK_DATA_DIR=../havbruk-radar-data/data python run.py --godta-felt lusetall

   Det nullstiller strekket. Det rører IKKE gulvet — gulvet flyttes bare
   ved å bygge normalen på nytt.

**Normalen må være bygget for at vakten skal virke i det hele tatt:**

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data python run.py --bygg-feltnormal

Den leser hele historikken, regner ut hva hvert felt normalt inneholder,
og skriver `data/feltnormal/<dato>.json`. Fila skrives aldri om — en ny
bygging gir en ny fil, og nyeste gjelder. Commit den: den er grunnlaget
alarmene måles mot.

Kjør den på nytt når en kilde har fått nok historikk til at normalen blir
meningsfull. Akvakultur og enhetsregisteret hadde 8–9 snapshots i august
2026, alle fra samme uke — for lite til å påstå at et konstant felt er
dødt.

## Månedlig: revisjonskjøringen

```bash
python backfill.py --kilde biomasse --revisjon
```

**Kjører av seg selv den 22. i måneden**, `revisjon.yml` i datarepoet —
to dager etter at Fiskeridirektoratet publiserer fila på nytt den 20.
Fram til 06.10.2026 sto det her at den «hører i cron», men ingen workflow
kjørte den.

Gikk den rød, står grunnen i loggen: hentingen feilet, en måned mangler
i fila, eller `Grunnlagssprik`. Kjør den på nytt med «Run workflow» i
Actions, eller lokalt med linja over mot datarepoet. Kjøringen er
rekonstruktiv: en måned som går tapt, kan tas igjen senere, fordi hver
publisering er arkivert av den ukentlige innsamlingen.

MÅLT 06.10.2026, lokalt mot en klone av datarepoet: 105 måneder, 0
revidert. Stemmer med en tekstdiff av kroppene: september-utgaven endret
bare juni og juli 2026 mot august-utgaven, og juni var ikke skrevet før
september-utgaven kom.

## Månedlig: vilkårsarkiveringen

```bash
python arkiver_vilkar.py --torrkjor      # se hva den ville hentet
python arkiver_vilkar.py                 # arkiver
```

Kjører av seg selv den 2. i måneden (`vilkar.yml` i datarepoet). Henter
vilkårssidene til BarentsWatch, Fiskeridirektoratet, Brreg og Lovdata og
lagrer kroppen i `data/arkiv/vilkar-<part>/` når den er ny. Rød hvis én
side ikke kan hentes. Da har adressen trolig flyttet, slik Brregs gjorde
før 06.10.2026: finn den nye på utgiverens egen side, ikke gjett, og
rett `SIDER` i skriptet og lenka i `docs/LISENSKJEDE.md`.

Endret `tekst_sha256` i loggfila betyr at teksten på sida er en annen.
Les den, og oppdater LISENSKJEDE hvis vilkårene har endret seg.

## Auksjonsarkivering — kjører av seg selv, men bare i sesongen

```bash
python arkiver_auksjon.py --torrkjor      # se hva den ville hentet
python arkiver_auksjon.py                 # arkiver
```

Auksjonen for tildelingsrunde 2026 holdes **27.09.2026**. Prisene per
produksjonsområde publiseres én gang og kan ikke hentes i ettertid.

`auksjon.yml` i datarepoet fyrer **64 ganger over 42 døgn**: tre ganger i
døgnet 20.–30.09 (06, 14 og 20 UTC) og daglig gjennom oktober. Det er
ikke overdrevet — GitHubs cron er best effort, og `arkiver_ny()` skriver
bare når innholdet er nytt, så en kjøring som ikke finner noe koster
ingenting og committer ingenting.

**En commit fra denne jobben BETYR at noe nytt ble publisert.** Stillhet
er normaltilstanden.

Mistet en dag? Kjør `workflow_dispatch` med `fra` satt bakover —
Wayback holder kroppen selv om Fiskeridirektoratet bytter den ut.

Kroppene er RÅ og ikke parset. Uttrekket av priser per produksjonsområde
er en egen jobb uten frist; hentingen har fristen.

Hva den gjør: leser biomassefila og sjekker om kilden har OMBESTEMT SEG
om måneder vi allerede har skrevet. Der noe er endret, skrives
`<dato>.2.parquet` ved siden av den gamle — som blir stående urørt — og
changelog-fila får det samme løpenummeret. Der ingenting er endret,
skrives ingenting.

Uten datoer tar den alt vi har. Den er trygg å kjøre om igjen: samme fil
gir «0 måneder REVIDERT, N uendret», og en kropp som allerede er arkivert
arkiveres ikke på nytt.

Hvorfor det er verdt to minutter i måneden: biomassefila **reviderer
fortiden**. 490 av 3973 rader endret seg mellom august 2024 og august
2026, over hele serien tilbake til 2017 — lokaliteter som
omklassifiseres mellom produksjonsområder i ettertid. Hos
Fiskeridirektoratet forsvinner forrige versjon den 20. hver måned.
Kjøres ikke denne, forsvinner den for oss også.

### Når den ender rødt

**`GRUNNLAGSSPRIK`** betyr at `source_version` eller `utvalg` er ulikt
mellom de to versjonene. Da kan en forskjell like gjerne være vår egen
parser som kildens revisjon, og kjøringen nekter å påstå det siste.
Har du nettopp bumpet `source_version` med vilje, er dette forventet:
revisjonssporet starter på nytt fra neste skriving, og begge snapshots
står. Er den derimot uventet, har noen endret parseren uten å si fra.

**«N måned(er) MANGLET i fila»** betyr at en måned vi har skrevet ikke
lenger finnes i publiseringen. Det har ikke skjedd, og skulle det skje,
er det verdt å undersøke før noe annet.

## Ved behov: en eldre utgivelse inn i serien

```bash
python backfill.py --kilde biomasse --arkiv <wayback-url>
```

Ikke en fast jobb. Kjøres når noen finner en arkivkopi av biomassefila
som er eldre enn det vi har — hver av dem er en revisjonstilstand som
ikke finnes noe annet sted.

Kopien skrives som `<dato>.2.parquet` ved siden av den gamle, og
revisjonsradene mot den påfølgende utgivelsen havner i
`changelog/biomasse/<dato>.2.parquet`. Rekkefølgen leses av
`published_at`, ikke av filnavnet: en kopi skrevet i dag kan godt være
den eldste påstanden.

**Uten `published_at` skrives ingenting**, og det er meningen. Kroppen
må bære `Last-Modified` eller `X-Archive-Orig-Last-Modified`. En
arkivkopi uten utgivelsestidspunkt kan ikke plasseres i rekkefølgen, og
en gjettet dato er verre enn ingen kopi.

Kjøringen er idempotent: nøkkelen er utgivelsen, ikke filnavnet, så
samme kopi to ganger gir ikke to snapshots.

Kartlagt 26.08.2026: fire utgivelser til finnes i Wayback, i
JSON-varianten. Se docs/KILDE-BIOMASSE.md punkt 12.

## Månedlig sjekk (to minutter)

Alt i datarepoet:

- Åpne `data/health.json`. Har alle kilder `feil_paa_rad: 0`?
- Samme fil: er `innhold_nullstrekk` tom for alle kilder? Et tall som
  vokser uke for uke er et felt på vei til å dø.
- Se på commit-loggen. Er det commits hver mandag?
- `du -sh data/`. Under 200 MB? Ingen bekymring.

## Størrelse

Målt 17.08.2026: Enhetsregisteret 118 KB, Akvakulturregisteret 148 KB.
266 KB i uka blir ca. 14 MB i året med dagens to kilder. GitHub anbefaler
å holde repoer under 1 GB og har hard grense på 100 MB per fil.

Du har altså flere tiår med hodehøyde. Skulle det en dag bli trangt, er
løsningen å komprimere gamle snapshots til én fil per år — ikke å slette
noe.

## De fire månedene før nettsiden

Du trenger ikke nettside for å ha nytte av dette. Commit-meldingen
genereres fra endringsloggen og inneholder toppsignalene:

```
Snapshot 2026-09-14 — 23 endringer

* NORDLAKS OPPDRETT AS: antall_ansatte 210 -> 268 [Bemanningsendring over 20 %]
* SALMAR FARMING AS: navn ... [Navneendring]

ok   enhetsregisteret: 13402
```

Åpne GitHub-appen mandag morgen, les commit-meldingen, ferdig. Det er
produktet i miniatyr, og det er nok til å teste om signalreglene dine
faktisk fanger noe interessant — som er det du bør bruke høsten på.

## Når nettsiden skal opp

Ingenting i innsamlingen endres. Dette er hele poenget med å skille
`core/`, `sources/` og datalagringen.

1. `npx degit evidence-dev/template dashboard`
2. Pek Evidence på datarepoets `data/` via DuckDB — den leser parquet
   direkte, ingen import.
3. Koble til en byggetjeneste som kan lese private repo. Vercel, Netlify
   og Cloudflare Pages gjør alle det på gratisplanen. GitHub Pages gjør
   det IKKE — Pages fra privat repo krever GitHub Pro.
4. Actions committer mandag → siden bygges automatisk.

Nettsiden viser avledede tall. Rådataene forblir i det private repoet.

Det finnes ingen server å drifte i den kjeden. Innsamlingen dytter ikke
til nettsiden; nettsiden bygges av den samme committen som allerede skjer.

Fire måneder med data først gjør dessuten dashbordet mye lettere å designe:
du vet da hvilke felter som faktisk endrer seg, og slipper å gjette.

## Offentlig og privat

Koden er offentlig: ubegrensede Actions-minutter, og commit-historikken
er CV-en.

Dataene er private: 2000 gratis Actions-minutter i måneden, mot et
faktisk forbruk på under fem. Registerdataene i seg selv er åpne og kan
hentes av hvem som helst — det som ligger privat er tidsserien, fordi
den ikke kan rekonstrueres i etterkant.

Uansett: aldri nøkler eller tokens i koden. De hører hjemme i GitHub
Secrets. `config.yml` skal bare inneholde ting du er komfortabel med at
andre ser.
