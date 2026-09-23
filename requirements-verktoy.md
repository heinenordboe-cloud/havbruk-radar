# Verktøy som ikke er Python-pakker

`requirements.txt` pinner det nettstedet og innsamlingen trenger for å
KJØRE. Denne fila står for det som trengs for å BYGGE ting som deretter
ligger i repoet eller i utputtet — verktøy, ikke avhengigheter.

Skillet er at ingenting her er importert av noen kodelinje. Mangler de,
sier bygget fra; det faller ikke stille.

## fonttools + brotli — fontene

    pip install fonttools brotli

Brukes én gang per font, av kommandoene i `docs/design/NEWSREADER.md` og
`docs/design/IBM-PLEX.md`. De ferdige `.woff2`-filene ligger i `maler/`
med sha256, så et bygg trenger dem ikke.

## pagefind 1.4.0 — søkeindeksen

    https://github.com/CloudCannon/pagefind/releases/tag/v1.4.0
    pagefind-v1.4.0-aarch64-apple-darwin.tar.gz
    sha256 647fa1da25fefeb24348ed09cccfcbcdd1dcab75c83e146c9f50336a78efb290

Kjøres av `nettsted.skriv_sokeindeks()` på slutten av hvert bygg, over
den ferdige HTML-en. Finnes på `PATH` eller i `HAVBRUK_PAGEFIND`:

    HAVBRUK_PAGEFIND=/sti/til/pagefind python nettsted.py --alle

**Mangler den, bygges siden likevel.** `/sok/` skrives, og veiviseren
til de tre flate indeksene virker — men byggerapporten skriver
`søkeindeks IKKE BYGGET` med grunnen. Et søk som stille slutter å virke
er nøyaktig formen på feilene i CLAUDE.md 1b.

Binæren er 15,6 MB og plattformspesifikk, og ligger derfor ikke i
repoet. Se `docs/design/PAGEFIND.md`.

## Chrome (headless) — skjermbildene

Brukes bare til å ta bilder av det ferdige nettstedet til
`docs/design/implementert/`. Ingenting i bygget avhenger av den.
