"""MALING-DRIFT, økt 3b punkt 2–4: det reglene bygger på, målt i arkivet.

    .venv/bin/python analyse/drift/kjennetegn.py > analyse/drift/kjennetegn.txt

vilkar         per part: synlig tekst i hver kropp, og om kjennetegnet i
               `arkiver_vilkar.KJENNETEGN` står i hver av dem. Korteste
               synlige tekst over alle parter gir minstelengden for en
               første versjon.
havbruksfond   hver kropp i havbruksfondet/, regjeringen-pressemeldinger/
               og ntb-pressemeldinger/, etter hva loggene sier den var
               («side», «vedlegg» …), og om «havbruksfond» står i den
               synlige teksten.
auksjon        hver kropp: tom eller ikke, og om `<html` står i den.

Hver kropp med sti og sha256 over den utpakkede kroppen.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROT))
ARKIV = ROT.parent / "havbruk-radar-data" / "data" / "arkiv"

from arkiver_vilkar import KJENNETEGN, SIDER  # noqa: E402
from core.karantene import synlig_tekst  # noqa: E402


def kropp(p: Path) -> tuple[bytes, str]:
    b = gzip.open(p).read()
    return b, hashlib.sha256(b).hexdigest()


def main() -> None:
    print("Kjennetegn og grenser for punkt 2–4, målt i arkivet")
    print(f"arkiv: {ARKIV}\n")

    print("vilkar: synlig tekst og kjennetegn per kropp")
    korteste = None
    for part in SIDER:
        ord_ = KJENNETEGN.get(part, "")
        for p in sorted((ARKIV / f"vilkar-{part}").glob("*.gz")):
            b, sha = kropp(p)
            n = len(synlig_tekst(b))
            har = ord_.casefold() in synlig_tekst(b).casefold() if ord_ else None
            print(f"  vilkar-{part}/{p.name:<20} {n:>6} tegn  «{ord_}» {har}  {sha}")
            if korteste is None or n < korteste[0]:
                korteste = (n, f"vilkar-{part}/{p.name}")
    print(f"  korteste synlige tekst: {korteste[0]} tegn ({korteste[1]}); "
          f"halvparten: {korteste[0] // 2}\n")

    print("havbruksfond: «havbruksfond» i synlig tekst, etter hva loggen sier kroppen var")
    hva = defaultdict(set)
    for lg in sorted((ARKIV / "havbruksfondet").glob("*.logg.json")):
        for r in json.loads(lg.read_text()):
            if r.get("sha256"):
                hva[r["sha256"]].add(r.get("hva") or "?")
    for mappe in ("havbruksfondet", "regjeringen-pressemeldinger", "ntb-pressemeldinger"):
        filer = sorted((ARKIV / mappe).glob("*.gz"))
        if not filer:
            print(f"  {mappe}/: ingen kropper")
        for p in filer:
            b, sha = kropp(p)
            nevner = "havbruksfond" in synlig_tekst(b).casefold()
            print(f"  {mappe}/{p.name:<22} {','.join(sorted(hva.get(sha, {'(ikke i loggene)'}))):<26} "
                  f"{nevner!s:<5} {b[:5]!r:<14} {sha}")
    print()

    print("auksjon: tom og <html")
    tall = defaultdict(int)
    for p in sorted((ARKIV / "auksjon").glob("*.gz")):
        b, sha = kropp(p)
        tom, html = not b.strip(), b"<html" in b.lower()
        tall[(tom, html)] += 1
        print(f"  auksjon/{p.name:<22} {len(b):>8} B  tom {tom!s:<5} <html {html!s:<5} {sha}")
    print(f"  {sum(tall.values())} kropper: "
          + ", ".join(f"tom={t} <html={h}: {n}" for (t, h), n in sorted(tall.items())))


if __name__ == "__main__":
    main()
