"""Etterført logg for de sju auksjonskroppene fra 29.09.2026 (MALING-DRIFT
H2.1), skrevet 04.11.2026 (økt 4c, punkt 5).

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/drift/etterfor_auksjon.py

Kroppene ble skrevet av `auksjon.yml` og lagt til i `6648fbb`, men
kjøringen hoppet over loggen fordi dagens fantes. Det de mangler, kan ikke
skaffes i ettertid: `fetched_at` og `kode_commit` er ukjent og står tomme
(CLAUDE.md 1b-7: tom streng er fraværet av en verdi). Det som KAN
belegges, står:

    sha256, byte      av kroppen selv, utpakket
    commit            commiten som la fila til, fra `git log --diff-filter=A`
    lagt_til_i_git    den commitens committerdato, en ØVRE grense for
                      hentingen og ikke hentetidspunktet
    url_i_kroppen     `<link rel="canonical">` i kroppen, lest og ikke
                      utledet; det er sidens egen adresse, ikke nødvendigvis
                      den som ble hentet

Radene har ikke `ny`. En etterført rad er ikke en kjøring som så kroppen
for første gang, og «Feil hvis» i H2.1 er skrevet mot nettopp det feltet.
Fila heter `<dato>.etterfort.logg.json`, merket som `raw.DAGLIG`, så den
ikke tar et løpenummer en kjøring kunne fått.
"""

import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import ARKIV_DIR  # noqa: E402

DATO = "2026-09-29"
FILER = [f"{DATO}.bin.gz"] + [f"{DATO}.{n}.bin.gz" for n in range(2, 8)]
KANONISK = re.compile(rb'<link[^>]+rel="canonical"[^>]+href="([^"]+)"')


def main() -> None:
    mappe = ARKIV_DIR / "auksjon"
    ut = mappe / f"{DATO}.etterfort.logg.json"
    assert not ut.exists(), ut
    loggede = {r["sha256"] for f in mappe.glob("*.logg.json")
               for r in json.loads(f.read_text(encoding="utf-8"))
               if isinstance(r, dict) and r.get("sha256")}
    rader = []
    for navn in FILER:
        sti = mappe / navn
        kropp = gzip.decompress(sti.read_bytes())
        sha = hashlib.sha256(kropp).hexdigest()
        assert sha not in loggede, f"{navn} står allerede i en logg"
        commit, dato = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%H %cI", "--", sti.name],
            cwd=mappe, capture_output=True, text=True, check=True).stdout.split()
        m = KANONISK.search(kropp)
        rader.append({
            "fil": navn, "sha256": sha, "byte": len(kropp),
            "etterfort": True,
            "etterfort_dato": "2026-11-04",
            "grunn": "kjøringen hoppet over loggen fordi dagens fantes "
                     "(arkiver_auksjon.py før 04.11.2026; MALING-DRIFT H2.1)",
            "commit": commit, "lagt_til_i_git": dato,
            "url_i_kroppen": m.group(1).decode() if m else "",
            "fetched_at": "", "kode_commit": "", "kode_rent": "",
        })
        print(f"{navn} {sha[:16]} {len(kropp)} B {commit[:7]} {dato}")
    ut.write_text(json.dumps(rader, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Logg: {ut}")


if __name__ == "__main__":
    main()
