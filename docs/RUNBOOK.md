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
regresjon gir rød jobb og e-post fra GitHub.

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

## Når volumvarselet fyrer

Du har fått rød jobb og en linje som denne:

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

    git commit -am "Godtar volum 16786 for enhetsregisteret: NACE 10.209 flyttet til eget register"

Skriv HVORFOR nivået ble godtatt, ikke bare at det ble det. Om fire
måneder er den commit-meldingen eneste sted som skiller "registeret
krympet" fra "vi ga opp en tirsdag".

## Når innholdsvarselet fyrer

Ser slik ut:

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
