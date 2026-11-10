#!/usr/bin/env python3
"""Faktaarkene fra R7 til lanseringsmappa, med en oversikt over dem.

    .venv/bin/python verktoy/faktaark_lansering.py
    .venv/bin/python verktoy/faktaark_lansering.py --ut ~/kystloggen-utkast/lansering/kommuner

Kopierer de 143 faktaarkene R7 laget (havbruk-analyse,
revisjon/2026-11-09-havbruksfond-pakke2/faktaark/) byte for byte, og
skriver OVERSIKT.md ved siden av dem: én rad per kommune, sortert etter
størst endring i andelen mot nøkkelen 01.09.2025, lest av R7s
ut/kommuner.csv. Ingen faktaark lages på nytt (økt L, punkt 4).

Stopper uten å skrive oversikten når et ark eller en rad mangler, når
CSV-en ikke har én rad per ark, eller når en kopi ikke har samme sha256
som originalen.

havbruk-analyse er privat. Arkene navngir kommuner og lokaliteter, ikke
selskaper (prøvd for «AS»/«ASA» 10.11.2026: 0 av 143), og de skrives
utenfor repoene.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
ANALYSE = ROT.parent / "havbruk-analyse"
R7 = "revisjon/2026-11-09-havbruksfond-pakke2"
UT = Path("~/kystloggen-utkast/lansering/kommuner").expanduser()
ANTALL = 143


def _sha(sti: Path) -> str:
    return hashlib.sha256(sti.read_bytes()).hexdigest()


def _pst(x: str) -> str:
    return f"{float(x):.4f} %".replace(".", ",")


def _pp(x: float) -> str:
    return f"{x:+.4f}".replace(".", ",").replace("-", "−")


def oversikt(rader: list[dict], ark: dict[str, str], kilde: dict) -> str:
    """Markdown, størst endring (absoluttverdi) først."""
    L = [
        "# Kommunene og havbruksfondet 2026: faktaarkene",
        "",
        f"{len(ark)} faktaark fra R7 (havbruk-analyse `{R7}/faktaark/`, siste commit "
        f"{kilde['commit']}), kopiert byte for byte. Ingen er laget på nytt.",
        "",
        "Sortert etter størst endring i andelen mot Fiskeridirektoratets nøkkel per "
        "01.09.2025, uansett retning. Endringen er andelen i A2 (registeret 31.08.2026) "
        "minus nøkkelen, i prosentpoeng. «Pakke 2» er andelen pakke 2 forventet "
        "(A2 med Havbruksstasjonen i Tromsø).",
        "",
        f"Kilde: `{R7}/ut/kommuner.csv`, sha256 `{kilde['csv_sha256']}`.",
        "",
        "| # | komnr | kommune | nøkkel 01.09.2025 | 2026 (A2) | endring (pp) | pakke 2 | gruppe | faktaark |",
        "|---:|---|---|---:|---:|---:|---:|---|---|",
    ]
    sortert = sorted(rader, key=lambda r: (-abs(float(r["endring_2025_2026_pp"])), r["komnr"]))
    for i, r in enumerate(sortert, 1):
        L.append(f"| {i} | {r['komnr']} | {r['kommune']} | {_pst(r['andel_2025_nokkel_pst'])} | "
                 f"{_pst(r['andel_2026_a2_pst'])} | {_pp(float(r['endring_2025_2026_pp']))} | "
                 f"{_pst(r['andel_2026_forventet_pst'])} | {r['gruppe']} | "
                 f"[{ark[r['komnr']]}]({ark[r['komnr']]}) |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ut", type=Path, default=UT)
    a = ap.parse_args(argv)
    kilde_dir = ANALYSE / R7
    arkene = sorted((kilde_dir / "faktaark").glob("*.md"))
    ark = {p.name.split("-", 1)[0]: p.name for p in arkene}
    with open(kilde_dir / "ut" / "kommuner.csv", encoding="utf-8", newline="") as f:
        rader = list(csv.DictReader(f))
    if len(arkene) != ANTALL or len(ark) != ANTALL:
        sys.exit(f"STOPPET: {len(arkene)} faktaark, {len(ark)} kommunenumre; ventet {ANTALL}")
    if sorted(r["komnr"] for r in rader) != sorted(ark):
        sys.exit(f"STOPPET: kommunene i kommuner.csv er ikke kommunene med faktaark: "
                 f"{sorted(set(r['komnr'] for r in rader) ^ set(ark))}")

    ut = a.ut.expanduser()
    ut.mkdir(parents=True, exist_ok=True)
    ulike = []
    for p in arkene:
        shutil.copyfile(p, ut / p.name)
        if _sha(ut / p.name) != _sha(p):
            ulike.append(p.name)
    if ulike:
        sys.exit(f"STOPPET: kopien er ikke lik originalen: {ulike}")

    commit = subprocess.run(
        ["git", "-C", str(ANALYSE), "log", "-1", "--format=%h", "--", f"{R7}/faktaark"],
        capture_output=True, text=True).stdout.strip()
    kilde = {"commit": commit or "ukjent", "csv_sha256": _sha(kilde_dir / "ut" / "kommuner.csv")}
    (ut / "OVERSIKT.md").write_text(oversikt(rader, ark, kilde), encoding="utf-8")
    print(f"{len(arkene)} faktaark kopiert til {ut}, alle med samme sha256 som originalen.")
    print(f"Oversikt: {ut / 'OVERSIKT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
