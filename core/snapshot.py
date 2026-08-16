"""Skriver snapshots. Overskriver aldri noe.

Filnavnet er datoen. Det er hele versjonssystemet — git tar resten.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from core.contract import Observation

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

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


def previous(source: str, before: str) -> pl.DataFrame | None:
    """Siste snapshot fra denne kilden før gitt dato."""
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None

    earlier = sorted(p for p in target_dir.glob("*.parquet") if p.stem < before)
    if not earlier:
        return None

    return pl.read_parquet(earlier[-1])
