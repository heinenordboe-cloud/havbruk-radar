"""Hvilke miljøvariabler krever de aktive kildene — spurt FØR innsamlingen.

`config.get()` kaster først når verdien FAKTISK brukes. Det er med vilje
(se `core/config.py`): en manglende BarentsWatch-nøkkel skal felle
BarentsWatch, ikke Enhetsregisteret. Men «først når den brukes» betyr i
praksis etter at de andre kildene har brukt tjue sekunder på nett, og for
en kilde som hoppes over av frekvensvakten betyr det ALDRI.

Det var slik F8 fikk leve: `samle.yml` eksponerte variablene, men
secretsene fantes ikke i datarepoet. Lokalt lå de i skallet, backfillen
kjørte lokalt, og lørdagens test-dispatch hoppet over lusetall via
`finnes_allerede()`. Første kjøring som faktisk kalte `fetch()` var
mandagens cron — fire dager etter at feilen ble innført, og den uka er
ikke tapt bare fordi den var rød, men fordi ingen visste at den sto der.

Denne modulen stiller spørsmålet på forhånd, samlet, for alle. Den leser
IKKE kildekoden og vet ingenting om hvilken kilde som er hvilken — den
ser etter markøren `config.MANGLER`, som `_expander()` legger igjen der
en `${...}` ikke lot seg slå opp. En ny kilde som trenger en nøkkel får
den derfor med automatisk ved å skrive `${NAVN}` i sin egen blokk i
`config.yml`. Ingen registrering, ingen endring her.

## Hva den IKKE fanger

Bare variabler som står som `${NAVN}` i `config.yml`. Leser en kilde
`os.environ` direkte i sin egen fil, er den usynlig herfra — og det er
grunnen til at nøkler hører hjemme i `config.yml`, ikke i kildefila.
`HAVBRUK_DATA_DIR` er heller ikke med: den har en fallback i
`core/paths.py` og er derfor ikke påkrevd, bare valgfri.
"""

import re
from typing import Any, Iterator

from core.config import MANGLER, load

# `_expander()` erstatter ${NAVN} med markøren etterfulgt av navnet.
# Én streng kan inneholde flere — "${A}/${B}" gir to markører — så dette
# er findall, ikke split. `config.get()` tar bare den første, fordi den
# skal navngi ÉN variabel i en feilmelding. Denne skal navngi alle.
_MARKOR = re.compile(re.escape(MANGLER) + r"([A-Z_][A-Z0-9_]*)")


def _finn(node: Any, sti: str) -> Iterator[tuple[str, str]]:
    """(variabelnavn, config-sti) for hver uoppslåtte ${...} i treet."""
    if isinstance(node, dict):
        for nokkel, verdi in node.items():
            yield from _finn(verdi, f"{sti}.{nokkel}" if sti else str(nokkel))
    elif isinstance(node, list):
        for i, verdi in enumerate(node):
            yield from _finn(verdi, f"{sti}[{i}]")
    elif isinstance(node, str):
        for navn in _MARKOR.findall(node):
            yield navn, sti


def manglende(kilder) -> dict[str, list[str]]:
    """{VARIABELNAVN: [config-sti, ...]} for det de aktive kildene krever.

    `kilder` er instansene fra `registry.discover()` — altså kun de som
    er aktive. En nøkkel under en avslått kilde skal ikke felle kjøringen;
    det er hele poenget med `aktiv: false`.

    Invarianten modulnavn == kildenavn (se `core/registry.py`) er det som
    gjør `kilder.<navn>` til riktig oppslag. Brytes den, ser denne sjekken
    i feil blokk — og `test_modulnavn_er_kildenavn` feller den før det
    skjer.
    """
    cfg = load()

    # Alt UTENFOR `kilder:` gjelder uansett hvem som kjører. Det er tomt i
    # dag; det står her fordi en global nøkkel ellers ville vært den ene
    # tingen sjekken ikke så, og det er nøyaktig feilklassen den finnes for.
    trær: list[tuple[Any, str]] = [
        ({k: v for k, v in cfg.items() if k != "kilder"}, "")
    ]
    for kilde in kilder:
        blokk = (cfg.get("kilder") or {}).get(kilde.name)
        if blokk is not None:
            trær.append((blokk, f"kilder.{kilde.name}"))

    funn: dict[str, list[str]] = {}
    for tre, rot in trær:
        for navn, sti in _finn(tre, rot):
            funn.setdefault(navn, []).append(sti)
    return funn


def forklar(funn: dict[str, list[str]]) -> str:
    """Feilmeldingen. Navngir ALLE manglende variabler, ikke den første.

    Én om gangen betyr én rød kjøring per manglende nøkkel, og med
    ukentlig cron er det én uke per nøkkel. Lista skal kunne leses én
    gang og fikses én gang.
    """
    linjer = [
        f"{len(funn)} miljøvariabel(er) kreves av en aktiv kilde, "
        f"men er ikke satt:",
        "",
    ]
    for navn in sorted(funn):
        linjer.append(f"  {navn}")
        for sti in funn[navn]:
            linjer.append(f"      kreves av config-nøkkelen '{sti}'")
    linjer += [
        "",
        "  I drift: Actions-secrets i datarepoet, eksponert til steget",
        "  «Samle inn» i samle.yml via env:. Begge deler må være på plass —",
        "  en secret som finnes men ikke eksponeres er like usynlig som en",
        "  som ikke finnes.",
        "  Lokalt: ~/.havbruk.env",
    ]
    return "\n".join(linjer)
