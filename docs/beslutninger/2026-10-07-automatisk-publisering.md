---
dato: 2026-10-07
tittel: Nettstedet bygges i Actions etter hver innsamling, og produksjon er et bygg Heine starter selv
status: utkast
commit: (denne)
---

# Automatisk bygg, manuell produksjon

**UTKAST.** Hva som ble bestemt står under, med det som ble målt.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Hva som ble bestemt

1. **`bygg.yml` i datarepoet** starter når «Ukentlig innsamling» ender
   `success` — DELVIS er `success` med vilje i `samle.yml` — og kan
   startes for hånd. Den kjører `publiser.py` steg 1–4 gjennom
   `publiser_ci.py bygg`, legger ut til forhåndsvisning, lagrer
   byggemappa og en kvittering som artifacts i 14 dager, og skriver
   logglinja (`forhandsvisning`).
2. **Bygget måles som et produksjonsbygg** også når det bare går til
   forhåndsvisning: porten med `produksjon=True`, søkeindeksen påkrevd.
   Det er den samme mappa som senere kan gå til kystloggen.no.
3. **`publiser.yml` bygger ingenting.** Bare `workflow_dispatch`, med
   `bekreft` som må være nøyaktig `ja`. Den laster ned et bygg, krever at
   sha256 over mappa er kvitteringens, legger ut til produksjon, skriver
   logglinja (`produksjon`) og røyktester fem sider på kystloggen.no.
4. **Godkjenningen er hendelsen, ikke et miljø.** Datarepoet er privat
   på GitHub Free; miljøer med påkrevd godkjenner finnes ikke der.
   Ingenting annet enn at Heine starter `publiser.yml` kan legge ut i
   produksjon fra Actions.
5. **Røyktesten har sin egen issue**, «Publiseringen trenger tilsyn»,
   fra `varsel.py --publisering`. Den deler ikke issue med innsamlingen,
   fordi innsamlingens lukkes av en grønn innsamling.
6. **Ingen nytt bygg når innsamlingen ikke skrev noe.** Står `main` der
   den sto da `samle.yml` startet (`workflow_run.head_sha`), bygges det
   ikke. Har `main` flyttet seg av en annen grunn, bygges det likevel.
7. **Kontaktadressen på nettstedet står i config.yml**
   (`nettsted.kontakt: kontakt@kystloggen.no`). `HAVBRUK_KONTAKT` er
   bare User-Agent.
8. **`publiser.py` lokalt er fortsatt reserven**, uendret i oppførsel.
   Porten, wrangler-kommandoen og summen er trukket ut som funksjoner
   begge veiene bruker.

## Målt

- `publiser_ci.py bygg` lokalt mot datarepoet 07.10.2026: porten ren,
  uke 2026-41, 9057 filer, 337,7 MB, sha256 `68997a57…ea92b818`.
  Samme sum etter en `zip -6`/`unzip`-runde; zip-fila 67,4 MB.
- `publiser_ci.py sjekk` på en kopi med én byte lagt til: stopper, exit 1.
- `royktest.py` mot den levende kystloggen.no med det bygget: alle fem
  sider svarer. Med uka satt til 2026-40: «/: lenker ikke til nyeste
  uke», exit 1.
- Den levende forsiden er ikke byte-lik bygget: Cloudflare skriver om
  e-postlenken til `/cdn-cgi/l/email-protection#…` og legger til
  `/cdn-cgi/scripts/…/email-decode.min.js` (Scrape Shield). Røyktesten
  sammenligner derfor ikke bytene.
- `nettsted.py --alle` med og uten `HAVBRUK_KONTAKT`: `diff -rq` uten
  forskjeller.
- pagefind 1.4.0 for `x86_64-unknown-linux-musl`: sha256 `8737736d…`
  likt i den utgitte `.sha256`-fila, i GitHubs release-API og i en egen
  nedlasting.

## Ikke målt

- Ingen av de to workflowene har kjørt på GitHub. `gh` finnes ikke på
  maskinen der de ble skrevet, og ingen secrets er opprettet.
- Byggetiden på en GitHub-maskin (lokalt 2 min 32 s) og dermed
  forbruket av de 2000 Actions-minuttene i måneden.
- Om tokenet med bare `Cloudflare Pages: Edit` er nok for `wrangler
  pages deploy` 4.139.0. Cloudflares beskrivelse sier det; ingen har
  prøvd.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
