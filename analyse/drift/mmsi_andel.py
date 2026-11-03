"""MALING-DRIFT 0c: andelen linjer uten MMSI per time, per lytter.

    .venv/bin/python analyse/drift/mmsi_andel.py > analyse/drift/mmsi_andel.txt
    .venv/bin/python analyse/drift/mmsi_andel.py <mappe>   # en kopi som finnes

Grunnlaget er timeregnskapene `kystvakt/regnskap.py` skriver på kystvakt-1,
ett per time og kilde, 0444 og skrevet én gang:

    /srv/ais/bw/<dato>/<dato>T<tt>Z.regnskap.json        bw
    /srv/ais5632/raa/<dato>/<dato>T<tt>Z.regnskap.json   5632

De ligger ikke i datarepoet. Uten mappe hentes de over ssh som `vakt`
(`sudo -n tar` til stdout, bare lesing), og sha256 for hver fil står i
utskriften, så samme grunnlag kan kjennes igjen senere.

Andelen er `uten_mmsi / meldinger`, for timer med minst én melding.
`uten_mmsi` teller linjer regnskapets leser ikke fant en MMSI i: for bw en
JSON-linje uten `mmsi`, for 5632 alt som ikke er første fragment av en
!AIVDM/!AIVDO — også andre fragment av en flerdelt melding, som er
normalt. Regelen for grensen står i etterskriften 03.11.2026.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import statistics
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROTER = {"bw": "srv/ais/bw", "5632": "srv/ais5632/raa"}
FRA = "2026-10-28"


def hent(mappe: Path) -> None:
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "kystvakt",
         "sudo -n sh -c 'cd / && tar -cf - srv/ais/bw/20*/*.regnskap.json "
         "srv/ais5632/raa/20*/*.regnskap.json'"],
        capture_output=True, timeout=300)
    if r.returncode:
        raise SystemExit(r.stderr.decode())
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        t.extractall(mappe, filter="data")


def kvantil(verdier: list[float], q: float) -> float:
    s = sorted(verdier)
    return s[min(len(s) - 1, math.ceil(q * len(s)) - 1)]


def main(mappe: Path, hvor: str) -> None:
    print("MALING-DRIFT 0c — linjer uten MMSI per time, per lytter")
    print(f"grunnlag: timeregnskapene fra {FRA}, {hvor}\n")
    alle = hashlib.sha256()
    for kilde, rel in ROTER.items():
        filer = sorted(p for p in (mappe / rel).glob("20*/*.regnskap.json")
                       if p.name[:10] >= FRA)
        timer = []
        for p in filer:
            data = p.read_bytes()
            alle.update(f"{rel}/{p.parent.name}/{p.name} ".encode()
                        + hashlib.sha256(data).hexdigest().encode() + b"\n")
            r = json.loads(data)
            timer.append((r["time"], r["meldinger"], r.get("uten_mmsi", 0)))
        med = [(t, m, u, u / m) for t, m, u in timer if m > 0]
        andeler = [a for *_, a in med]
        print(f"{kilde}: {len(timer)} timer ({timer[0][0]} – {timer[-1][0]}), "
              f"{len(med)} med minst én melding, {len(timer) - len(med)} tomme")
        if not med:
            continue
        print(f"  meldinger per time: min {min(m for _, m, *_ in med)}, "
              f"median {statistics.median(m for _, m, *_ in med):.0f}, "
              f"maks {max(m for _, m, *_ in med)}")
        print(f"  andel uten MMSI:    min {min(andeler):.4%}  median "
              f"{statistics.median(andeler):.4%}  p95 {kvantil(andeler, .95):.4%}  "
              f"p99 {kvantil(andeler, .99):.4%}  maks {max(andeler):.4%}")
        print(f"  spenn {(max(andeler) - min(andeler)) * 100:.2f} prosentpoeng")
        print("  de fem høyeste timene:")
        for t, m, u, a in sorted(med, key=lambda x: -x[3])[:5]:
            print(f"    {t}  {u:>7} av {m:>7}  {a:.4%}")
        print("  de fem laveste timene:")
        for t, m, u, a in sorted(med, key=lambda x: x[3])[:5]:
            print(f"    {t}  {u:>7} av {m:>7}  {a:.4%}")
        maks = max(andeler)
        grense = math.ceil(maks * 100) / 100
        stopp = maks >= 0.5 or (maks - min(andeler)) > 0.20
        print(f"  regelen: maks {maks:.4%} rundet opp til hele prosent = "
              f"{grense:.0%}" + ("  -> STOPP, ingen grense bygges" if stopp else ""))
        print()
    print(f"sha256 over (sti, sha256) for hver fil, sortert: {alle.hexdigest()}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(Path(sys.argv[1]), sys.argv[1])
    else:
        with tempfile.TemporaryDirectory() as tmp:
            hent(Path(tmp))
            main(Path(tmp), "kystvakt-1 over ssh (sudo -n tar, bare lesing)")
