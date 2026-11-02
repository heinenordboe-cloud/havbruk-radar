"""MALING-LUSEINNKOMST, steg 2: regn ut a og c av kroppene steg 1 la i arkivet.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/luseinnkomst/m2_analyse.py 2026-11-02

Leser bare arkivet: loggen fra steg 1 sier hvilke kropper som hører til
hvilket kall (sha256), og kroppene finnes i lusetall-innkomst/ eller, når
de var like innsamlingens, i lusetall/. Ingen nettverkskall.
"""

import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import ARKIV_DIR  # noqa: E402
from sources.lusetall import rapportert_andel  # noqa: E402


def kropp_med_sha(sha: str) -> tuple[dict, str]:
    for mappe in ("lusetall-innkomst", "lusetall"):
        for sti in sorted((ARKIV_DIR / mappe).glob("*.json.gz")):
            with gzip.open(sti, "rb") as f:
                b = f.read()
            if hashlib.sha256(b).hexdigest() == sha:
                return json.loads(b), f"{mappe}/{sti.name}"
    raise LookupError(sha)


def lokaliteter(k: dict) -> dict:
    return {x["localityNo"]: x for x in k.get("localities", [])}


def main() -> None:
    dato = sys.argv[1]
    logg = json.loads((ARKIV_DIR / "lusetall-innkomst" /
                       f"{dato}.maling.logg.json").read_text())
    uker = [p for p in logg if "uke" in p]

    print("## a. Andel aktive som har rapportert, i dag\n")
    print("| kall | lokaliteter | brakklagt | aktive | rapportert | andel | kropp | sha256 |")
    print("|---|---:|---:|---:|---:|---:|---|---|")
    for p in uker:
        k, fil = kropp_med_sha(p["sha256_kanonisk_json"])
        aktive, rapp, andel = rapportert_andel(k)
        n = len(k["localities"])
        print(f"| {p['hva']} | {n} | {n - aktive} | {aktive} | {rapp} | "
              f"{andel:.1%} | `{fil}` | `{p['sha256_kanonisk_json'][:12]}…` |")

    print("\n## c. Dagens svar mot innsamlingens kropp for samme uke\n")
    print("| uke | innsamlet (fil) | lokaliteter i dag / ved innsamling | bare i dag | bare ved innsamling | "
          "lokaliteter med endret felt | felt (antall lokaliteter) |")
    print("|---|---|---|---:|---:|---:|---|")
    for p in uker:
        inn = p.get("innsamlingens")
        if not inn or p["hva"].startswith("N-4 igjen"):
            continue
        idag, _ = kropp_med_sha(p["sha256_kanonisk_json"])
        da, _ = kropp_med_sha(inn["sha256"])
        a, b = lokaliteter(idag), lokaliteter(da)
        felles = a.keys() & b.keys()
        felt = Counter()
        endret = 0
        for nr in felles:
            diff = [f for f in a[nr].keys() | b[nr].keys()
                    if a[nr].get(f) != b[nr].get(f)]
            if diff:
                endret += 1
                felt.update(diff)
        topp = ", ".join(f"`{f}` {n}" for f, n in sorted(felt.items(), key=lambda x: (-x[1], x[0])))
        print(f"| {p['aar']}/{p['uke']} | `{inn['fil']}` | {len(a)}/{len(b)} | "
              f"{len(a.keys() - b.keys())} | {len(b.keys() - a.keys())} | "
              f"{endret} | {topp or '—'} |")
        toppnivaa = {k for k in idag.keys() | da.keys() if k != "localities"
                     and idag.get(k) != da.get(k)}
        if toppnivaa:
            print(f"|  | toppnivå ulikt: {sorted(toppnivaa)} | | | | | |")


if __name__ == "__main__":
    main()
