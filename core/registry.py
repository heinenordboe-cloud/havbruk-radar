"""Finner kilder automatisk ved å skanne sources/.

Grunnen til at dette er en egen fil: du skal aldri måtte redigere
core/ for å legge til en kilde. Du dropper en fil i sources/ og den
er med i neste kjøring.

To ting denne fila garanterer, som begge er lært av å se dem feile:

1. En kildefil som ikke lar seg importere skal ikke stoppe de andre.
   Den blir en KnektKilde som feiler pent i runner, akkurat som en
   kilde med nede API. Ellers dør hele kjøringen av én skrivefeil.

2. Bare klasser som er DEFINERT i modulen registreres, ikke de som
   er importert inn i den. Uten den sjekken kjøres en delt baseklasse
   én gang per fil som importerer den, og observasjonene dobles.

## Invarianten: modulens filnavn ER kildens navn

`sources/akvakultur.py` må inneholde kilden som heter `akvakultur`.
Dette er ikke kosmetikk, og det er ikke en konvensjon som bare gjør
koden penere å lese.

En kildefil som ikke lar seg importere blir en KnektKilde. Da finnes
det ingen klasse å spørre om navn, og det eneste kjernen VET er
filnavnet. Bryter de to, rapporteres importfeilen under et navn
`health.json` aldri har sett — og en kilde health ikke kjenner er en
kilde uten historikk å måle mot.

Konkret: `sources/akvakulturregisteret.py` het `akvakultur` som kilde.
En importfeil der ble rapportert som «akvakulturregisteret», et navn
uten `sist_ok`, uten volumreferanse og uten `sist_forsok` — så
frekvensvakten så en ukjent kilde og nedetidsalarmen så en kilde som
aldri hadde fungert. Fila er døpt om, og
`test_modulnavn_er_kildenavn` feller enhver kilde som bryter
invarianten på nytt.

Moduler med `_`-prefiks er unntatt: de er delte hjelpere, ikke kilder,
og skannes ikke.
"""

import importlib
import inspect
import pkgutil
import traceback
from pathlib import Path

from core.contract import Source

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"


class KnektKilde(Source):
    """Plassholder for en kildefil som ikke lot seg laste.

    Den feiler i fetch() med den opprinnelige feilen. Da fanger runner
    den, health husker den, og du får varsel — i stedet for en kjøring
    som aldri startet.
    """

    def __init__(self, name: str, feil: str) -> None:
        self.name = name
        self.enabled = True
        self._feil = feil

    def fetch(self):
        raise RuntimeError(f"Kilden '{self.name}' kunne ikke lastes:\n{self._feil}")

    def parse(self, raw, observed_at):
        return []


def discover() -> list[Source]:
    """Returnerer én instans av hver aktiverte kilde."""
    found: list[Source] = []

    for module_info in pkgutil.iter_modules([str(SOURCES_DIR)]):
        if module_info.name.startswith("_"):
            continue  # _base.py, _hjelpere.py osv. hoppes over

        try:
            module = importlib.import_module(f"sources.{module_info.name}")
        except Exception:
            found.append(KnektKilde(module_info.name, traceback.format_exc(limit=3)))
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, Source) or obj is Source:
                continue
            if obj.__module__ != module.__name__:
                continue  # importert hit, ikke definert her

            try:
                instance = obj()
            except Exception:
                # Her FINNES klassen, så kilden kan navngi seg selv.
                # Bare importfeilen over må gjette ut fra filnavnet, og
                # det er invarianten i docstringen som gjør gjettet
                # riktig.
                found.append(KnektKilde(
                    getattr(obj, "name", module_info.name),
                    traceback.format_exc(limit=3),
                ))
                continue

            if instance.enabled:
                found.append(instance)

    return sorted(found, key=lambda s: s.name)
