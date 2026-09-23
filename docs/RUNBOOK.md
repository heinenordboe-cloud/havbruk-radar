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

**5. GitHub forsvinner.** Minst sannsynlig, men speilingen dekker det.
Speilworkflowen hører hjemme i DATAREPOET, ikke her — koden er allerede
offentlig og finnes i enhver klone, mens historikken er det eneste som
ikke kan skaffes på nytt. Codeberg eller GitLab, begge gratis.

Hemmelighetene heter `SPEIL_URL` og `SPEIL_TOKEN`, og variabelen som slår
det på heter `SPEILING_AKTIV`. Ingen andre navn — en tidligere versjon av
dokumentasjonen sa `MIRROR_URL`, som aldri har vært riktig.

## Publisering: `publiser.py`

Nettstedet ligger på **Cloudflare Pages**, prosjekt `kystloggen`,
domene `kystloggen.no`.

    python publiser.py                  # forhåndsvisning
    python publiser.py --produksjon     # kystloggen.no
    python publiser.py --uten-bygg      # bruk mappa som den er

**Første gang, og bare da:** logg inn i wrangler. Det skjer i
nettleseren, og skriptet rører ikke nøkler:

    npx wrangler login

### Seks steg, og rekkefølgen er poenget

| # | steg | verner mot |
|---|---|---|
| 1 | sporbarhet | begge repoene rene og pushet — F15, to ganger |
| 2 | bygg | fra disk, ikke fra en cache |
| 3 | porten | ETT ukvittert funn stopper. Ingen overstyring |
| 4 | ukas tall | skrevet ut, og du må skrive «ja» |
| 5 | wrangler | forhåndsvisning med mindre `--produksjon` |
| 6 | logg | én linje i `docs/publiseringslogg.tsv` i datarepoet |

`--uten-bygg` hopper over steg 2. **Den hopper ikke over porten.**

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

Skriptet skriver linja. **Du committer og pusher den selv**, som del av
neste datacommit.

### Ingen nøkler

`wrangler` autentiserer i nettleseren og lagrer sin egen tilstand under
`~/.config/.wrangler`. `publiser.py` leser den ikke, skriver den ikke,
og ber ikke om den.

### Vertsnavnet i en forhåndsvisning

Bygget bruker `kystloggen.no` som kanonisk adresse. På en
forhåndsvisning betyr det at `<link rel=canonical>` peker til
produksjonsdomenet — som er riktig: forhåndsvisningen er en kopi, og
den skal ikke be en søkemotor indeksere seg selv.

Vil du ha en forhåndsvisning som oppgir SIN EGEN adresse:

    HAVBRUK_BASEURL=https://forhandsvisning.kystloggen.pages.dev \
        python publiser.py

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

**Hører i cron, ved siden av `run.py`.** Én gang i måneden, etter den
20. — det er da Fiskeridirektoratet publiserer fila på nytt.

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
