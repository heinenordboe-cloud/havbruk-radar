"""MALING-NYE-KILDER, steg 1c: er v2-svaret byte-stabilt mellom to kall?

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/nye-kilder/m1c_v2_stabil.py 2026-11-03

Uke 41/2026 (N-4) med POST to ganger, 20 s mellom. Avgjør om fangsten kan
sammenligne på sha256 av kroppen alene, slik v1-fangsten gjør (F1.6 i
MALING-LUSEINNKOMST), eller trenger en kanonisk form som akvakultur.
Kroppene i data/arkiv/maling-nye-kilder/ (arkiver_ny: en byte-lik kropp
skrives ikke to ganger), loggen i `<dato>.m1c.logg.json`.
"""

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _barentswatch  # noqa: E402

MAPPE = "maling-nye-kilder"
URL = "https://www.barentswatch.no/bwapi/v2/geodata/fishhealth/locality/2026/41"


def main() -> None:
    dato = sys.argv[1]
    tilgang = _barentswatch.Tilgang("lusetall")
    klient = tilgang.klient()
    logg = []
    try:
        for n in (1, 2):
            hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            svar = tilgang.post(klient, URL, hva=f"v2 uke 41/2026, kall {n}", json={})
            data = svar.json()
            ser, ext = raw._serialiser(data)
            sti = raw._ledig_sti(MAPPE, dato, ext)
            sha, ny = raw.arkiver_ny(MAPPE, dato, data)
            rekkefolge = hashlib.sha256(json.dumps(
                [l["locality"]["no"] for l in data]).encode()).hexdigest()
            logg.append({"hva": f"f: v2 uke 41/2026, kall {n}", "url": URL,
                         "status": svar.status_code, "fetched_at": hentet,
                         "sha256_utpakket": hashlib.sha256(svar.content).hexdigest(),
                         "sha256": sha, "fil": sti.name if ny else "(finnes fra før)",
                         "sha256_rekkefolge_localityNo": rekkefolge,
                         "headere": dict(svar.headers)})
            time.sleep(20)
    finally:
        klient.close()
    ut = ARKIV_DIR / MAPPE / f"{dato}.m1c.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in logg:
        print(p["status"], p["sha256_utpakket"][:16], p["sha256"][:16], p["fil"],
              p["sha256_rekkefolge_localityNo"][:16], p["hva"])


if __name__ == "__main__":
    main()
