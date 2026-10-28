"""Legger en fangst fra fang.py i rå-arkivet, byte for byte.

    .venv/bin/python -m analyse.ais.arkiver_fangst <kilde> <dato> <fangst.txt>

Kroppen er fila slik fang.py skrev den (vår mottakstid + linja), og
hashen er sha256 over nettopp de bytene. Lagres via raw.arkiver_ny(), så
samme fangst arkiveres bare én gang.
"""
import sys
from pathlib import Path

from core import raw


def main():
    kilde, dato, sti = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    sha, skrevet = raw.arkiver_ny(kilde, dato, sti.read_bytes())
    print(f"{kilde} {dato} sha256 {sha} {'skrevet' if skrevet else 'fantes'}")
    for p in raw.kropper(kilde):
        print(p)


if __name__ == "__main__":
    main()
