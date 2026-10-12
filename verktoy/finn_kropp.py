#!/usr/bin/env python3
"""Finner en kropp i datarepoet ut fra sha256, hel eller som prefiks.

    .venv/bin/python verktoy/finn_kropp.py 6e677a60
    .venv/bin/python verktoy/finn_kropp.py b740d4bb 8d8b6d4    # prefiks og suffiks

Dokumentene oppgir hashen over den UTPAKKEDE kroppen for `.gz` i
`data/arkiv/`, og over fila selv for `.parquet` i `data/raw/`. Begge
prøves for hver fil, så et treff sier også hvilken av dem hashen var.

Bare lesing. Brukes av kontrolløren (.claude/agents/kontrollor.md), som
kjører i en sandkasse uten skrivetilgang.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("HAVBRUK_DATA_DIR")
            or ROT.parent / "havbruk-radar-data" / "data").resolve()


def treff(prefiks: str, suffiks: str = ""):
    """(sti, hva som er hashet, hel sha256) for hver fil som passer."""
    filer = sorted(DATA.glob("arkiv/**/*.gz")) + sorted(DATA.glob("raw/**/*.parquet"))
    for sti in filer:
        b = sti.read_bytes()
        kandidater = [("fila", hashlib.sha256(b).hexdigest())]
        if sti.suffix == ".gz":
            kandidater.append(("utpakket", hashlib.sha256(gzip.decompress(b)).hexdigest()))
        for hva, h in kandidater:
            if h.startswith(prefiks) and h.endswith(suffiks):
                yield sti, hva, h


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    prefiks = argv[0].lower().rstrip("….")
    suffiks = argv[1].lower().lstrip("….") if len(argv) > 1 else ""
    funnet = 0
    for sti, hva, h in treff(prefiks, suffiks):
        print(f"{sti.relative_to(DATA.parent)}  sha256({hva}) {h}")
        funnet += 1
    if not funnet:
        print(f"ingen kropp under {DATA} har sha256 {prefiks}…{suffiks}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
