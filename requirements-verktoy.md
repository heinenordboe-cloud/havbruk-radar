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

### Installert uten sudo, samme mønster som Node

Utpakket i `~/.local/bin`, som allerede ligger på `PATH`. Ingen
pakkebrønn, ingen `sudo`, og **sjekksummen sammenlignes før utpakking** —
en tarball fra nett som pakkes ut før den er kjent, er pakket ut.

Kjørt i en engangsmappe, ikke i repoet: tarballen har ingen toppkatalog
og legger `pagefind` i arbeidsmappa.

    U=https://github.com/CloudCannon/pagefind/releases/download/v1.4.0
    F=pagefind-v1.4.0-aarch64-apple-darwin.tar.gz
    cd "$(mktemp -d)" && curl -fLO "$U/$F"
    shasum -a 256 "$F"
    # 647fa1da25fefeb24348ed09cccfcbcdd1dcab75c83e146c9f50336a78efb290
    # SAMMENLIGN MED LINJA OVER. Er de ulike: stopp her.
    tar -xzf "$F"
    install -m 755 pagefind ~/.local/bin/pagefind
    pagefind --version          # pagefind 1.4.0

MÅLT 23.09.2026, etter installasjonen over:

    tarball    9 166 484 byte   sha256 647fa1da…78efb290  (utgitt sum)
    binær     15 639 520 byte   sha256 a10044e5…a3872791  (utpakket)

Binærsummen står her for å kunne svare på «er det denne binæren som er
installert» senere — den utgitte summen svarer bare for tarballen, og
den er borte etter utpakkingen.

### Mangler den

**Siden bygges likevel.** `/sok/` skrives, og veiviseren til de tre
flate indeksene virker — men byggerapporten skriver `søkeindeks IKKE
BYGGET` med grunnen, og **`publiser.py` steg 4 nekter å publisere til
PRODUKSJON** uten indeks. Til forhåndsvisning blir det en advarsel.

Skillet er hvem som ser mangelen: en forhåndsvisning ses av den som ba
om den, produksjon av alle andre. Et søkefelt som tar imot tastetrykk og
svarer ingenting er nøyaktig formen på feilene i CLAUDE.md 1b — stille,
og usynlig for den som ikke visste at det skulle kommet et svar.

Porten måler FILENE under `nettsted/pagefind/`, ikke byggerapporten: med
`--uten-bygg` finnes ingen rapport å lese, og en rapport sier uansett
bare at vi prøvde (CLAUDE.md 1b-2).

Binæren er 15,6 MB og plattformspesifikk, og ligger derfor ikke i
repoet. Se `docs/design/PAGEFIND.md`.

## playwright 1.63.0 + chromium — skjermbildene i serie

    pip install playwright
    python -m playwright install chromium

Brukes av gjennomgangsbildene i `docs/design/implementert/<dato>/`, der
hver sidetype tas i to bredder og deles i biter. Kom inn 24.09.2026, og
den står her framfor bare i `.venv` av samme grunn som pypdf og Jinja2 i
`requirements.txt`: en ad hoc-installasjon ingen har skrevet ned, er
nøyaktig det disse filene finnes for å hindre.

**Ikke i `requirements.txt`**, og skillet er det samme som for pagefind:
ingen kodelinje importerer den. Bygget og innsamlingen kjører uten den;
det er bildene som ikke kan tas.

Chromium-bygget lastes ned av `playwright install` til
`~/Library/Caches/ms-playwright/` (94 MB), ikke til repoet.

Hvorfor den og ikke Chrome under: helsidesbilder med `clip`, så en høy
side kan deles i biter uten at helsidesfila skrives — og to bredder i
samme kjøring, med `deviceScaleFactor` satt.

## Chrome (headless) — enkeltbilder

Brukes bare til å ta bilder av det ferdige nettstedet til
`docs/design/implementert/`. Ingenting i bygget avhenger av den.
