---
name: ny-kilde
description: Sjekklista for å legge til en ny datakilde i havbruk-radar (en fil i sources/). Bruk når en oppgave ber om å bygge, aktivere eller hente inn en ny kilde.
---

# Ny kilde

En kilde er ÉN ny fil i `sources/`. `core/` endres ikke (CLAUDE.md
regel 1). Ser det ut som kontrakten mangler noe, si fra og la Heine
avgjøre om `core/contract.py` skal utvides.

1. **Mønsteret.** Arv `Source` fra `core/contract.py` og returner
   `Observation`-objekter. Les en eksisterende kilde av samme slag først:
   `sources/lusetall.py` (API med nøkler), `sources/biomasse.py`
   (revisjonskilde, `published_at` fra `Last-Modified`),
   `sources/trafikklysvedtak.py` (dokumenter). `registry.discover()`
   finner fila selv; ingen registrering. `fetch(kjoredato)` og
   `gjelder_for(kjoredato)` får datoen inn og leser aldri klokka (1b).
   Avklar om kilden reviderer fortiden før etterslepet velges (1b-5).
2. **Persondata.** Bare virksomhets- og lokalitetsdata (regel 3).
   Filtrer personformer i `fetch()` før arkivering med
   `core/persondata.py` (`fjern_personformer`, `er_personform`), slik
   `sources/eierskap.py` og `sources/enhetsregisteret.py` gjør.
   `snapshot.write()` nekter et snapshot med personformer.
3. **KILDE-dokumentet.** `docs/KILDE-<NAVN>.md`: endepunkt, format og
   respons slik de er SETT (regel 4), med dato og hash. Mal:
   `docs/KILDE-TRAFIKKLYSVEDTAK.md`.
4. **Lisenskjeden.** Én rad i tabellen i `docs/LISENSKJEDE.md` med lisens,
   hjemmel, ordrett attribusjon og datoen vilkåret ble lest. Uten den er
   kilden UBELAGT. Sett `attribusjon` på klassen.
5. **Med i innsamlingen.** `kilder.<navn>` i `config.yml` (`aktiv: true`,
   etterslep, nøkler som `${VARIABEL}`). Prøv med
   `.venv/bin/python run.py --bare <navn> --torrkjor`. Den ukentlige
   jobben kjører det som er PUSHET (regel 7). Trenger kilden en nøkkel
   som Actions-secret i datarepoets workflow, må Heine legge den inn
   selv; workflow-filene er sperret.
6. **Tester** i `tests/test_<navn>.py` mot en lagret kropp, ikke mot
   nettet. Deretter porten (CLAUDE.md §8).
