#!/usr/bin/env python3
"""Trekker tre påstander merket MÅLT fra et målingsdokument, tilfeldig.

    .venv/bin/python verktoy/kontroll_trekk.py docs/MALING-X.md
    .venv/bin/python verktoy/kontroll_trekk.py docs/MALING-X.md --fro 1234

Brukes av kontrolløren (.claude/agents/kontrollor.md). Trekningen er
her og ikke i agenten fordi en modell som «velger tilfeldig» velger det
som er lett å regne ut. Frøet skrives ut, så trekningen kan gjøres om
av hvem som helst med samme dokument.

En PÅSTAND er ett avsnitt, ett listepunkt eller én tabellrad. Den er
med når den sier MÅLT uten å nekte det («ikke MÅLT», «MÅLBAR, ikke
MÅLT» teller ikke) og har minst ett tall som ikke er en dato, et
klokkeslett, et årstall eller en hash. Kodeblokker er ikke påstander.

Påstandene som trekkes, skal rapporteres alle tre. Trekkes en som ikke
lar seg etterprøve, er DET funnet; å trekke på nytt ville skjøvet
utvalget mot de enkle.
"""
from __future__ import annotations

import argparse
import random
import re
import secrets
import sys
from pathlib import Path

MAALT = re.compile(r"(?<![\wÆØÅæøå])MÅLT(?![\wÆØÅæøå])")
NEKTET = re.compile(r"(?i)\bikke\s+(?:selv\s+)?$")

DATO = re.compile(r"\b\d{1,2}\.\d{1,2}\.(?:\d{4})?|\b\d{4}-\d{2}(?:-\d{2})?")
KLOKKE = re.compile(r"\bkl\.?\s*\d{1,2}[.:]\d{2}")
HASH = re.compile(r"\b[0-9a-f]{7,64}\b")
AARSTALL = re.compile(r"(?:19|20)\d{2}")
STI = re.compile(r"`[^`]*`")
TALL = re.compile(r"(?<![\wÆØÅæøå.])\d+(?:[  ]\d{3})*(?:[,.]\d+)?")

PUNKT = re.compile(r"^\s*(?:[-*]|\d+\.)\s")


def enheter(linjer: list[str]) -> list[tuple[int, int, str]]:
    """(første linje, siste linje, tekst), 1-indeksert."""
    ut: list[tuple[int, int, str]] = []
    start, buf, i_kode = 0, [], False

    def lukk(slutt: int) -> None:
        nonlocal start, buf
        if buf:
            ut.append((start, slutt, "\n".join(buf)))
        start, buf = 0, []

    for nr, linje in enumerate(linjer, 1):
        if linje.lstrip().startswith("```"):
            lukk(nr - 1)
            i_kode = not i_kode
            continue
        if i_kode:
            continue
        tom = not linje.strip()
        innrykket_kode = linje.startswith("    ") and not buf and not PUNKT.match(linje)
        if tom or innrykket_kode:
            lukk(nr - 1)
            continue
        ny = (linje.startswith("|") or linje.startswith("#")
              or PUNKT.match(linje))
        if ny or not buf:
            lukk(nr - 1)
            start = nr
        buf.append(linje)
        if linje.startswith("|") or linje.startswith("#"):
            lukk(nr)
    lukk(len(linjer))
    return ut


def bekrefter_maalt(tekst: str) -> bool:
    for m in MAALT.finditer(tekst):
        foran = tekst[max(0, m.start() - 40):m.start()]
        if not NEKTET.search(foran):
            return True
    return False


def tall_i(tekst: str) -> list[str]:
    rest = STI.sub(" ", tekst)
    for monster in (KLOKKE, DATO, HASH):
        rest = monster.sub(" ", rest)
    return [t.strip() for t in TALL.findall(rest)
            if t.strip() and not AARSTALL.fullmatch(t.strip())]


def kandidater(dok: Path) -> list[tuple[int, int, str, list[str]]]:
    linjer = dok.read_text(encoding="utf-8").splitlines()
    ut = []
    for fra, til, tekst in enheter(linjer):
        if not bekrefter_maalt(tekst):
            continue
        tall = tall_i(tekst)
        if tall:
            ut.append((fra, til, tekst, tall))
    return ut


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dokument", type=Path)
    ap.add_argument("--antall", type=int, default=3)
    ap.add_argument("--fro", type=int, default=None,
                    help="frø for å gjøre om en trekning")
    a = ap.parse_args(argv)

    alle = kandidater(a.dokument)
    fro = a.fro if a.fro is not None else secrets.randbelow(2**32)
    print(f"dokument {a.dokument}: {len(alle)} påstander merket MÅLT med tall")
    print(f"frø {fro}")
    if len(alle) < a.antall:
        print(f"for få påstander til å trekke {a.antall}")
        return 1
    valgt = sorted(random.Random(fro).sample(range(len(alle)), a.antall))
    for n, i in enumerate(valgt, 1):
        fra, til, tekst, tall = alle[i]
        linjer = f"linje {fra}" if fra == til else f"linje {fra}-{til}"
        print(f"\n=== trekk {n}: påstand {i + 1} av {len(alle)}, "
              f"{a.dokument}:{fra} ({linjer})")
        print(tekst)
        print(f"--- tall i påstanden: {', '.join(tall)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
