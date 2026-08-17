"""Skriver snapshots. Overskriver aldri noe.

Filnavnet er datoen. Det er hele versjonssystemet — git tar resten.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from core.contract import Observation
from core.paths import RAW_DIR  # noqa: F401  (monkeypatches i testene treffer her)

SCHEMA = ["entity_id", "entity_type", "entity_name", "field", "value", "source", "observed_at"]


def to_frame(observations: list[Observation]) -> pl.DataFrame:
    if not observations:
        return pl.DataFrame(schema={col: pl.Utf8 for col in SCHEMA})
    return pl.DataFrame([o.as_dict() for o in observations]).select(SCHEMA)


def write(observations: list[Observation], observed_at: str) -> list[Path]:
    """Én parquet-fil per kilde per kjøring."""
    frame = to_frame(observations)
    written = []

    for (source,), group in frame.group_by(["source"]):
        target_dir = RAW_DIR / str(source)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{observed_at}.parquet"
        group.write_parquet(path)
        written.append(path)

    return written


def finnes_allerede(observed_at: str) -> list[str]:
    """Kilder som allerede har skrevet snapshot for denne datoen.

    Kjører du to ganger samme dag, sammenligner diffen mot forrige UKE
    på nytt og fører de samme endringene inn i changeloggen en gang til.
    run.py bruker denne til å nekte, i stedet for å doble tallene dine.
    """
    if not RAW_DIR.exists():
        return []
    return sorted(
        katalog.name
        for katalog in RAW_DIR.iterdir()
        if katalog.is_dir() and (katalog / f"{observed_at}.parquet").exists()
    )


def siste_dato(source: str) -> str | None:
    """Datoen for siste snapshot fra denne kilden, eller None."""
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None
    datoer = sorted(p.stem for p in target_dir.glob("*.parquet"))
    return datoer[-1] if datoer else None


def dager_siden(source: str, observed_at: str) -> int | None:
    """Dager siden kilden sist ble hentet. None = aldri hentet.

    Negativt tall (snapshot datert fram i tid) returneres som det er, og
    behandles av kalleren som "ikke forfalt" — det er tryggere enn å
    overskrive noe som allerede finnes.
    """
    sist = siste_dato(source)
    if sist is None:
        return None
    try:
        return (date.fromisoformat(observed_at) - date.fromisoformat(sist)).days
    except ValueError:
        return None   # filnavn som ikke er en dato: behandles som aldri hentet


def previous(source: str, before: str) -> pl.DataFrame | None:
    """Siste snapshot fra denne kilden før gitt dato."""
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None

    earlier = sorted(p for p in target_dir.glob("*.parquet") if p.stem < before)
    if not earlier:
        return None

    return pl.read_parquet(earlier[-1])
