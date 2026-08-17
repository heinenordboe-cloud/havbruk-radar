"""Endringsloggen. Én fil per kjøring, aldri en fil som skrives om.

Hvorfor dette ikke er én samlet changelog.parquet:

En parquet-fil komprimerer godt, men komprimert binærdata delta-komprimerer
elendig i git. Skriver du hele loggen på nytt hver uke, lagrer git en ny
nesten-full kopi hver gang — repostørrelsen vokser kvadratisk med tida, ikke
lineært. Etter to år er det forskjellen på noen megabyte og noen hundre.

Snapshotene i data/raw/ har alltid hatt riktig mønster: én fil per dato,
aldri rørt igjen. Her gjør vi det samme.

Bonuseffekt: en rekjøring samme dag overskriver sin egen fil i stedet for
å legge de samme radene til på nytt. Loggen kan ikke dobbeltføres.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from core.paths import CHANGELOG_DIR, GAMMEL_CHANGELOG as GAMMEL_FIL  # noqa: F401


def skriv(endringer: pl.DataFrame, observed_at: str) -> Path | None:
    """Skriver ukas endringer som egen fil. Returnerer stien, eller None."""
    if endringer.is_empty():
        return None

    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    sti = CHANGELOG_DIR / f"{observed_at}.parquet"
    endringer.write_parquet(sti)
    return sti


def _filer() -> list[Path]:
    if not CHANGELOG_DIR.exists():
        return []
    return sorted(CHANGELOG_DIR.glob("*.parquet"))


def les_alt() -> pl.DataFrame:
    """Hele endringsloggen, eldste først.

    Leser også den gamle samlefila hvis den finnes, så historikk fra før
    omleggingen ikke forsvinner. Analyselaget skal ikke måtte vite at
    formatet har endret seg.
    """
    rammer = []

    if GAMMEL_FIL.exists():
        rammer.append(pl.read_parquet(GAMMEL_FIL))

    rammer.extend(pl.read_parquet(f) for f in _filer())

    if not rammer:
        from core.diff import CHANGE_SCHEMA

        return pl.DataFrame(schema=CHANGE_SCHEMA)

    return pl.concat(rammer, how="diagonal_relaxed").sort("observed_at")
