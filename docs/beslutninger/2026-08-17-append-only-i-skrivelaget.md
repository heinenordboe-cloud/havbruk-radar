---
dato: 2026-08-17
tittel: Append-only-guarden flyttes ned i skrivelaget
status: gjeldende
commit: a5ca326
---

# Append-only-guarden flyttes ned i skrivelaget

**Bestemt:** `snapshot.write()` nekter å overskrive. Finnes
`{dato}.parquet`, skrives `{dato}.2.parquet`. Samme mønster som
rå-arkivet. `--tving` overstyrer forfallssjekken, ikke append-only.

**Hvorfor:** Guarden lå i `run.py` og gjaldt kun uten `--tving`. Løftet
fra 16.08 — data skrives én gang, aldri om — var altså fortsatt ikke
sant i praksis, bare mindre usant. I dag ble et snapshot uten
proveniensfelter overskrevet av ett med. Ingen skade, men det er samme
mønster som ga tre skrivinger 16.08.

Et skrivelag som kan overskrive er et skrivelag man må huske å ikke
bruke feil. Guarden hører hjemme der skrivingen skjer, ikke i
inngangspunktet.

**Sidefunn:** `siste_dato()` ville lest `2026-08-17.2` som ugyldig dato
og rapportert kilden som aldri hentet — det ville brutt frekvensstyringen
helt stille. `previous()` sorterte filnavn som tekst, så `.10` kom før
`.2`. Begge rettet, begge dekket av nye tester (27 → 29).

**Prisen:** Flere filer ved manuelle rekjøringer. 17.08 endte med fem
snapshots for samme dato. Det er ikke rot — det er fem faktiske
hentinger som alle er bevart.

**Ville snudd det:** Ingenting.

**Målt på første kjøring:** Rå-arkiv 641 KB (akvakultur 445 KB,
enhetsregisteret 196 KB) mot 266 KB snapshots — arkivet er ca. 2,4×
snapshotene, altså ~33 MB i året. Godt under reverseringsgrensen.

**Presisering om plassering:** Arkivet ligger i `data/arkiv/<kilde>/`,
ikke i `data/raw/` — den mappa er snapshotene. Verifisert ved re-parse:
arkivet fra 17.08 ga 27 074 observasjoner, identisk med kjøringen.
