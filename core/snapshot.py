"""Skriver snapshots. Overskriver aldri noe.

Filnavnet er datoen. Det er hele versjonssystemet — git tar resten.
"""

from __future__ import annotations

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


def previous(source: str, before: str) -> pl.DataFrame | None:
    """Siste snapshot fra denne kilden før gitt dato."""
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None

    earlier = sorted(p for p in target_dir.glob("*.parquet") if p.stem < before)
    if not earlier:
        return None

    return pl.read_parquet(earlier[-1])
