---
dato: 2026-10-07
tittel: "Forslag: ukesfiler eldre enn 12 uker publiseres ikke"
status: FORSLAG — ikke bygget, venter på ja eller nei fra Heine
---

# Forslag: ukesfiler eldre enn 12 uker publiseres ikke

Punkt 6 i nedlastingsoppgaven 07.10.2026. **Ingenting her er bygget.**
Notatet sier hva som ville endret seg, og hva det sparer.

## Forslaget slik det er stilt

Ukesfilene (CSV, JSON, ZIP — og regnearket, som kom i samme oppgave)
for endringsuker eldre enn 12 uker legges ikke ut. Ukesiden står og
viser alt som før, men nedlastingslinja erstattes av

> Eldre uker som fil: kontakt@kystloggen.no

## Hva det sparer — MÅLT 07.10.2026

I dag: **0 filer.** Bygget har 7 endringsuker (2026-35 til 2026-41), og
ingen av dem er eldre enn 12 uker.

Hver uke har 4 nedlastingsfiler (`endringer.csv`, `endringer.json`,
`kystloggen-endringer-<uke>.xlsx`, `kystloggen-endringer-<uke>.zip`),
til sammen 52–250 kB per uke (snitt 110 kB over de 7). Besparelsen er
4 × (antall uker − 12):

| endringsuker i bygget | filer spart | av 12 635 i dag |
|---|---|---|
| 7 (i dag) | 0 | 0 % |
| 26 (februar 2027) | 56 | 0,4 % |
| 52 (august 2027) | 160 | 1,3 % |
| 104 (august 2028) | 368 | 2,9 % |

Det som vokser med ukene, er ikke filene: det er sidene. En uke er 17
filer i sin mappe pluss 13 søkeutdrag, og 26 av de 30 blir stående
under forslaget. **Mot filtaket hos Cloudflare (20 000) flytter
forslaget lite** — én ny fil per lokalitet (1 782) flytter mer enn to
års ukesfiler.

## Hva som ville endret seg

1. **`skriv_endringssider()` i nettsted.py**: de fire filene skrives bare
   for de 12 nyeste endringsukene. «Eldre enn 12 uker» regnes mot den
   NYESTE endringsuka i dataene, ikke mot klokka — ellers ville et bygg
   av de samme dataene gitt ulike filer etter hvilken dag det kjørte
   (CLAUDE.md 1b).
2. **`maler/endringer-uke.html.j2`**: nedlastingslinja («Excel (.xlsx) ·
   Data (.zip) · JSON · Atom-feed») blir for de eldre ukene en setning
   med `mailto:`-lenke til adressen i `nettsted.kontakt` (config.yml) —
   ikke en adresse skrevet i malen. Atom-feeden lenkes fortsatt.
3. **`_jsonld_uke()`**: `distribution` utelates for de eldre ukene. En
   JSON-LD som oppgir en `DataDownload` som svarer 404, er en påstand
   som ikke holder.
4. **Testene**: en ny som krever at uke 13 og eldre har null
   nedlastingsfiler og kontaktsetningen, og at uke 12 har alle fire.

## Det forslaget kolliderer med

- **Gamle adresser skal fortsatt virke.** Samme oppgave sa at
  `endringer.csv` skal fortsette å svare (punkt 1). En uke som blir 13
  uker gammel mister både `endringer.csv` og `endringer.json`, og en
  lenke noen har lagt til dem gir 404. Det ville vært den første
  adressen dette nettstedet trekker tilbake med vilje.
- **Siterbarheten.** Ukesiden siteres med «sjekksum …» og viser alle
  radene, men fila er det et verktøy kan lese. Etter 12 uker må den som
  vil etterprøve en eldre uke, skrive en e-post.
- **Arbeid for kontakt@.** Hver forespørsel er en uke som må bygges for
  hånd fra datarepoet. Det finnes ikke noe verktøy for det i dag.

## Vurdering

Begrunnelsen kan ikke være filtaket: målt sparer forslaget 0 filer i dag
og 160 om et år. Er grunnen en annen — at eldre ukesfiler ikke skal
ligge åpent, eller lagring i Actions-artifacten (124 MB per bygg, se
RUNBOOK «Lagring») — er det den som bør veies. Artifacten sparer for
øvrig bare rundt 110 kB komprimert per uke på dette.

Bygges ikke før Heine sier ja.
