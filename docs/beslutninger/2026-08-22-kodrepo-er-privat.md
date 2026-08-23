---
dato: 2026-08-22
tittel: Innsamlingen henter kodrepoet med token, ikke med åpenhet
status: utkast
commit: 
---

# Innsamlingen henter kodrepoet med token

> **Utkast.** Alt under «Hva som skjedde», «Hva som er endret» og
> «Påstander som ikke stemmer» er skrevet fra diffen og fra
> kjøringsloggene. Avsnittene merket **[din vurdering]** er dine.

**Bestemt:** `samle.yml` i datarepoet gjør checkout av kodrepoet med
`secrets.KODE_REPO_TOKEN`. Kodrepoet forblir privat. Tilgangen er fikset,
ikke synligheten.

---

## Hva som skjedde

Innsamlingen feilet på checkout av kodrepoet, to kjøringer på rad (#6 og
#7, 22.08.2026):

    remote: Repository not found.
    fatal: repository 'https://github.com/heinenordboe-cloud/havbruk-radar/' not found

`GITHUB_TOKEN` gjelder bare repoet en workflow bor i. Da kodrepoet ble
lukket 18.08 ([2026-08-18-repoene-er-private.md](2026-08-18-repoene-er-private.md)),
mistet datarepoets workflow tilgangen til det — men workflowen ble ikke
endret, fordi ingenting i den nevnte at den var avhengig av at kodrepoet
lå åpent. Avhengigheten var i FRAVÆRET av et token, og et fravær er ikke
noe man leser over.

**Feilmeldingen er en del av historien.** GitHub svarer «Repository not
found» — 404, ikke 403 — på et privat repo man ikke har tilgang til. Det
er et bevisst valg fra GitHub (en 403 ville bekreftet at repoet finnes),
men konsekvensen her er at symptomet ser ut som et feilstavet reponavn og
ikke som en manglende tilgang. Det peker feil vei før man har begynt.

## Hva som var galt med feilmeldingen vår

Steget «Marker feil tydelig» sa:

    Innsamlingen feilet 2026-08-22. Ingen commit betyr ingen aktivitet.

Begge påstandene var gale i denne kjøringen:

- **Innsamlingen kjørte aldri.** Checkout feilet før den, så `run.py` ble
  ikke startet. «Innsamlingen feilet» sender deg til kildene og
  API-nøklene når problemet ligger i tilgangen til koden.
- **«Commit snapshot» gikk grønt.** Steget har `if: always()`, fant
  ingenting å committe, og `git diff --staged --quiet && exit 0` er et
  legitimt utfall. Meldingen leste et normalt utfall som et symptom.

En feilmelding som peker på feil steg er verre enn ingen melding: den
koster tiden det tar å utelukke det den pekte på. To kjøringer gikk med.

## Hva som er endret

**`samle.yml`:**

- Checkout av kodrepoet bruker `secrets.KODE_REPO_TOKEN`, med
  `persist-credentials: false` — vi leser koden, vi pusher den ikke, og
  da skal tokenet ikke bli liggende i `kode/.git/config` jobben ut. Samme
  begrunnelse som `speil.yml` allerede bruker for sitt token.
- Steget het «Hent koden fra det offentlige repoet». Det heter nå «Hent
  koden fra kodrepoet (privat — krever token)».
- Hvert steg har fått en `id`, slik at feilmeldingen kan lese utfallet av
  hvert enkelt.
- «Marker feil tydelig» skriver nå ut alle stegene med utfall, navngir
  det FØRSTE som står som `failure`, og sier separat om innsamlingen
  fullførte — fordi det er det egentlige spørsmålet, og fordi et rødt
  checkout-steg og en feilende kilde har samme konsekvens for uka.
- Headerkommentaren begrunnet retningen med at kodrepoet var offentlig.
  Den begrunnelsen falt. Det som står igjen og fortsatt holder: tokenet i
  datarepoet trenger kun LESETILGANG til kode, mens motsatt vei ville
  krevd skrivetilgang til historikken.

**`speil.yml`:** ikke funksjonelt endret. Headeren begrunnet at kodrepoet
ikke speiles med at «koden ligger offentlig på GitHub og i enhver klone».
Halve argumentet falt: koden finnes nå på GitHub og i arbeidskopien, og
ingen andre steder. Det som holder er at historikken ikke kan gjenskapes
mens kode kan det — men skillet er ikke lenger offentlig/privat.

**[din vurdering]** — om kodrepoet også skal speiles nå. Det er ikke
lenger replikert av at hvem som helst kan klone det.

**`.github/workflows/README.md`** i kodrepoet: samme feilaktige
begrunnelse, rettet.

## Verifisert

YAML-en parser, og alle syv steg har id. Feilmeldingsskriptet er kjørt
mot fire scenarier med utfallene satt som miljøvariabler:

| scenario | melding |
|----------|---------|
| checkout av kodrepoet feiler (#6/#7) | «Hent koden fra kodrepoet» + innsamlingen fullførte ikke |
| en kilde feiler | «Samle inn» + innsamlingen fullførte ikke |
| push av snapshot feiler | «Commit snapshot», ingen falsk påstand om innsamlingen |
| rødt uten navngitt steg | sier at ingen steg står som failure |

Selve tilgangen kan ikke verifiseres herfra — den krever en kjøring med
secreten. Det er `workflow_dispatch` som avgjør om dette virker.

## Påstander som ikke stemmer, og som IKKE er rettet

Listet, ikke endret. Prosjektet har ingen `00_prosjekt.md`; det som
tilsvarer den her er `docs/ARKITEKTUR.md` og `docs/RUNBOOK.md`.

**Levende påstander om at kodrepoet er offentlig:**

| fil | sted | hva som står |
|-----|------|--------------|
| `docs/ARKITEKTUR.md` | §3, overskrift | «To repo: kode offentlig, data privat» |
| `docs/ARKITEKTUR.md` | §3 | «et privat repo som leser offentlig kode trenger ingen hemmelighet» — dette er nettopp antakelsen som feilet |
| `docs/RUNBOOK.md` | linje 7 | «havbruk-radar   offentlig — koden. Dette repoet.» |
| `docs/RUNBOOK.md` | linje 12 | samme sikkerhetsbegrunnelse som ARKITEKTUR §3 |
| `docs/RUNBOOK.md` | linje 73 | «koden er allerede offentlig og finnes i enhver klone» — begrunnelsen for at kun datarepoet speiles |
| `docs/RUNBOOK.md` | §«Offentlig og privat» | «Koden er offentlig: ubegrensede Actions-minutter, og commit-historikken er CV-en» |
| `docs/beslutninger/2026-08-17-beslutningslogg-i-repoet.md` | «Hvorfor offentlig» | står som `status: gjeldende`, og hele begrunnelsen for å legge loggen i repoet er at den er synlig |

**To av disse har praktiske konsekvenser, ikke bare ordlyd:**

- **Actions-minutter.** RUNBOOK sier kodrepoet har ubegrensede minutter
  fordi det er offentlig. Private repo har 2000 gratis minutter i
  måneden, delt på kontoen. `test.yml` kjører på hver push. Forbruket er
  fortsatt lite, men taket finnes nå.
- **Deaktivering av planlagte kjøringer.** RUNBOOK linje 62 antar at
  60-dagersregelen gjelder offentlige repo, og at datarepoet
  «sannsynligvis ikke er omfattet». Den antakelsen er merket uverifisert
  allerede, og bør verifiseres nå som begge repo er private — det er
  cron-jobben i datarepoet som står på spill.

**Ikke medregnet:** `docs/DASHBORD.md` §«Et mellomsteg som koster ti
minutter» foreslår GitHub Pages for en offentlig side. Det er et forslag
om noe som ikke er bygget, ikke en påstand om dagens tilstand — men Pages
på et privat repo krever betalt plan, så forslaget er dyrere enn det ser
ut.

**Riktige som de er:** beslutningspostene fra 16.08 og 18.08 beskriver
fortiden korrekt og skal ikke endres.

## Prisen

**[din vurdering]**

## Ville snudd det

**[din vurdering]**
