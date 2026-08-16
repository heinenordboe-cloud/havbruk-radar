# Runbook — drift, sikring og veien til nettside

## Hvor dataene faktisk ligger

Etter første push finnes historikken tre steder uten at du gjør noe mer:

1. GitHub (opprinnelsen)
2. Din egen maskin (klonen)
3. Hver GitHub Actions-kjøring sjekker ut hele repoet

Et git-repo er ikke en database du kan miste halvparten av. Hver klon er
en fullstendig kopi med hele historikken. Det er den viktigste grunnen
til at git ble valgt over Supabase her.

## Sikring — det som faktisk kan gå galt

Rangert etter sannsynlighet, ikke etter hvor dramatisk det høres ut.

**1. Du mister GitHub-kontoen.** Klart mest sannsynlige tap. Nytt
telefonnummer, mistet 2FA-app, ingen recovery codes lagret.
→ Slå på 2FA, last ned recovery codes, legg dem et sted som ikke er
telefonen din. Ti minutter, én gang.

**2. En kilde slutter å levere og du merker det ikke.** Feilisoleringen
gjør jobben grønn selv når en kilde er død. `core/health.py` løser dette:
regresjon gir rød jobb og e-post fra GitHub.

**3. Actions deaktiveres.** GitHub slår av planlagte kjøringer etter
60 dager uten aktivitet i repoet. Siden hver kjøring committer, nullstilles
telleren selv. Men får du e-post om deaktivering: åpne repoet og trykk
enable, ellers står innsamlingen stille.

**4. Du ødelegger historikken selv.** `git push --force` etter en rebase.
→ Slå på branch protection på `main` i repo-innstillingene.

**5. GitHub forsvinner.** Minst sannsynlig, men speilingen i
`.github/workflows/speil.yml` dekker det. Codeberg eller GitLab, gratis.

## Månedlig sjekk (to minutter)

- Åpne `data/health.json`. Har alle kilder `feil_paa_rad: 0`?
- Se på commit-loggen. Er det commits hver mandag?
- `du -sh data/` lokalt. Under 200 MB? Ingen bekymring.

## Størrelse

Én kjøring med Enhetsregisteret er i størrelsesorden 100–200 KB komprimert
parquet. Femtito kjøringer i året blir rundt 5–10 MB. GitHub anbefaler å
holde repoer under 1 GB og har hard grense på 100 MB per fil.

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
`core/`, `sources/` og `data/`.

1. `npx degit evidence-dev/template dashboard`
2. Pek Evidence på `data/` via DuckDB — den leser parquet direkte, ingen import.
3. Koble repoet til Vercel. Vercel bygger på hver push.
4. Actions committer mandag → Vercel bygger automatisk → siden er oppdatert.

Det finnes ingen server å drifte i den kjeden. Innsamlingen dytter ikke
til nettsiden; nettsiden bygges av den samme committen som allerede skjer.

Fire måneder med data først gjør dessuten dashbordet mye lettere å designe:
du vet da hvilke felter som faktisk endrer seg, og slipper å gjette.

## Offentlig eller privat repo

Alt her er offentlige registerdata. Offentlig repo gir ubegrensede
Actions-minutter og er samtidig CV-en — commit-historikken er beviset
på at systemet har kjørt siden 2026.

Privat repo har 2000 gratis minutter i måneden, som også holder rikelig.
Bytt til offentlig senere hvis du vil; historikken følger med.

Uansett valg: aldri nøkler eller tokens i koden. De hører hjemme i
GitHub Secrets. `config.yml` skal bare inneholde ting du er komfortabel
med at andre ser.
