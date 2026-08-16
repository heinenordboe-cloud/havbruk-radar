"""Finner kilder automatisk ved å skanne sources/.

Grunnen til at dette er en egen fil: du skal aldri måtte redigere
core/ for å legge til en kilde. Du dropper en fil i sources/ og den
er med i neste kjøring.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path

from core.contract import Source

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"


def discover() -> list[Source]:
    """Returnerer én instans av hver aktiverte kilde."""
    found: list[Source] = []

    for module_info in pkgutil.iter_modules([str(SOURCES_DIR)]):
        if module_info.name.startswith("_"):
            continue  # _base.py, _hjelpere.py osv. hoppes over

        module = importlib.import_module(f"sources.{module_info.name}")

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Source) and obj is not Source:
                instance = obj()
                if instance.enabled:
                    found.append(instance)

    return sorted(found, key=lambda s: s.name)
