"""Skriver AIS-dagsmanifestene og -statusen fra kystvakt-1 inn i datarepoet.

    ssh utlevering@kystvakt-1 | python ais_manifest.py

Kjøres av ais-manifest.yml. Inn kommer JSON-en fra kystvakt/utlevering.py;
serveren har ingen skrivetilgang til repoene, så det er GitHub som henter
og denne som skriver. Rådataene havner aldri i git, bare sha256 per fil.

    data/arkiv/ais-manifest/<kilde>/<dato>.SHA256SUMS      én gang
    data/arkiv/ais-manifest/<kilde>/<dato>.<n>.SHA256SUMS  hvis det endret seg
    data/ais/status.json                                   hver kjøring

Manifestene ligger under data/arkiv/ og stemples av stempel.yml som alle
andre arkivfiler. Et manifest skrives aldri om (CLAUDE.md §2): sier
serveren noe annet om et døgn enn det som står, får det nye svaret neste
løpenummer, og begge blir stående. Det skal ikke skje for et lukket døgn,
og det er derfor det skal synes.

status.json overskrives, som health.json. Den er tilstand, ikke historikk,
og tilsyn.py leser den.
"""
import json
import re
import sys
from pathlib import Path

from core.paths import ARKIV_DIR, DATA_DIR

MANIFEST_DIR = ARKIV_DIR / "ais-manifest"
STATUS = DATA_DIR / "ais" / "status.json"
KILDE = re.compile(r"^[a-z0-9-]+$")
DATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def skriv_manifest(kilde: str, dato: str, innhold: str) -> Path | None:
    """Stien som ble skrevet, eller None når det samme svaret alt står."""
    if not (KILDE.match(kilde) and DATO.match(dato)):
        raise ValueError(f"ugyldig kilde/dato: {kilde!r} {dato!r}")
    for linje in innhold.splitlines():
        if not re.fullmatch(r"[0-9a-f]{64}  [^/\s][^/]*", linje):
            raise ValueError(f"{kilde}/{dato}: uleselig manifestlinje {linje!r}")
    mappe = MANIFEST_DIR / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    finnes = sorted(mappe.glob(f"{dato}.*SHA256SUMS"))
    if any(p.read_text() == innhold for p in finnes):
        return None
    kandidater = [mappe / f"{dato}.SHA256SUMS"] + [mappe / f"{dato}.{n}.SHA256SUMS"
                                                    for n in range(2, 1000)]
    for sti in kandidater:
        try:
            with open(sti, "x") as f:
                f.write(innhold)
            return sti
        except FileExistsError:
            continue
    raise RuntimeError(f"{kilde}/{dato}: tom for løpenummer")


def main() -> None:
    data = json.load(sys.stdin)
    nye = [s for m in data["manifester"]
           if (s := skriv_manifest(m["kilde"], m["dato"], m["innhold"]))]
    status = {k: v for k, v in data.items() if k != "manifester"}
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1) + "\n")
    for s in nye:
        print(f"[ny] {s.relative_to(DATA_DIR)}")
    print(f"{len(nye)} nye manifester, status {status['skrevet']}")


if __name__ == "__main__":
    main()
