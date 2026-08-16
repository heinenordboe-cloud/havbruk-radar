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
                found.append(KnektKilde(module_info.name, traceback.format_exc(limit=3)))
                continue

            if instance.enabled:
                found.append(instance)

    return sorted(found, key=lambda s: s.name)
