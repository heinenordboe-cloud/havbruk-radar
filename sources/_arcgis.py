"""Delt kontrakt for ArcGIS-lagene: `biomasselag` og `romming`.

Ligger i `sources/` med `_`-prefiks, som `_http.py` og `_barentswatch.py`:
det er maskineri to kilder deler, ikke en kilde. Registry hopper over
fila.

## Hvorfor den finnes: ArcGIS sier «du spurte for bredt» med 200 OK

De to kildene pagineres likt — `resultOffset` + `resultRecordCount`, og
`if len(trekk) < SPENN: break` som slutt-test. Den testen hviler på en
antakelse ingen av dem sjekket: at en kort side betyr at laget er slutt.

MÅLT 19.09.2026 mot Biomasse-laget (1128 rader, `maxRecordCount` 2000):

    resultRecordCount=1000, offset=0      1000 rader   exceededTransferLimit=True
    resultRecordCount=1000, offset=1000    128 rader   exceededTransferLimit=(ikke satt)
    resultRecordCount=2000, offset=0      1128 rader   exceededTransferLimit=(ikke satt)
    resultRecordCount=3000, offset=0      1128 rader   exceededTransferLimit=(ikke satt)

Tjenesten avkorter altså til sitt eget tak UTEN å feile, og sier det i
`exceededTransferLimit`. Så lenge `SPENN` ligger under taket, er en kort
side et ekte sluttsignal, og flagget står bare på de fulle sidene.

**Den dagen tjenesten senker taket under vårt `SPENN`, snur det.** Med
`maxRecordCount = 500` og `SPENN = 1000` ville hver side gitt 500 rader
med flagget satt, `500 < 1000` ville lest som «siste side», og kilden
ville samlet 500 av 1128 rader med 200 OK og ingen feilmelding. Det er
den stille varianten av samme fallgruve pub-aqua har — der svarer
tjenesten 400 med taket i klartekst, og `_http.get()` kaster.

## Hva prøven spør om, og hvorfor akkurat det

    kort side  +  flagget satt      MOTSIGELSE — tjenesten avkortet, og
                                    sier at det finnes mer. Kaster.
    full side  +  flagget satt      normalt: vi ba om N, fikk N, mer
                                    finnes. Neste side.
    kort side  +  flagget ikke satt ekte slutt.

Prøven er altså ikke «kom det færre rader enn vi ba om» — det er det
normale på siste side, og en vakt som felte på det ville felt hver
kjøring. Den spør om det ENE tilfellet der vår slutt-test og tjenestens
eget svar er uenige. Se CLAUDE.md 1b-2: still spørsmålet du faktisk vil
ha svar på, og velg feltet som svarer på DET.
"""

from __future__ import annotations

from typing import Any


def sjekk_avkorting(svar: dict[str, Any], antall: int, spenn: int,
                    kilde: str, side: int) -> None:
    """Kaster hvis tjenesten avkortet siden OG sier at det finnes mer.

    Kalles rett før slutt-testen i pagineringsløkka, med den rå
    JSON-dicten og antall rader siden ga.

    Stille når alt er som det skal, og det er meningen: dette er en vakt
    mot en endring hos motparten, ikke en tilstand vi forventer. Målt
    19.09.2026 fyrer den ikke på noen av de to kildene — biomasselag
    henter 1000 + 128, romming 578 i én side.
    """
    if antall >= spenn:
        return                      # full side: flagget er forventet
    if not svar.get("exceededTransferLimit"):
        return                      # kort side uten flagg: ekte slutt

    raise RuntimeError(
        f"{kilde}: side {side} ga {antall} rader av {spenn} vi ba om, og "
        f"tjenesten satte exceededTransferLimit — den avkortet svaret og "
        f"sier at det finnes mer. Slutt-testen «kort side = siste side» "
        f"gjelder da ikke, og å stoppe her ville mistet resten i stillhet. "
        f"Sannsynligvis er tjenestens maxRecordCount senket under SPENN "
        f"({spenn}); sjekk laget og senk SPENN. Se sources/_arcgis.py."
    )
