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

## Månedlig sjekk (to minutter)

Alt i datarepoet:

- Åpne `data/health.json`. Har alle kilder `feil_paa_rad: 0`?
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
