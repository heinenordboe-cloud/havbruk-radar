"""MALING-NYE-KILDER, steg 1b: flatene MED geometri (kandidat a).

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/nye-kilder/m1b_flater.py 2026-11-03

Steg 1 hentet fiskeridirWMS_akva/MapServer/19, som svarer med `areal_m2`
men uten geometri (`geometry` mangler i hver post, også med
returnGeometry=true). Samme flater med polygon ligger i
FiskeridirWFS_akva/MapServer/80. Metadata, hele laget to ganger med 20 s
mellomrom, og historicMoment for 01.09.2026, i samme mappe og med samme
loggform som steg 1, i `<dato>.m1b.logg.json`.
"""

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _http  # noqa: E402

MAPPE = "maling-nye-kilder"
LAG = "https://gis.fiskeridir.no/server/rest/services/FiskeridirWFS_akva/MapServer/80"
SPORRING = {"where": "1=1", "outFields": "*", "returnGeometry": "true",
            "orderByFields": "loknr", "f": "json"}


def main() -> None:
    dato = sys.argv[1]
    logg = []
    with httpx.Client(timeout=120, follow_redirects=True) as k:
        def kall(url, hva, params):
            hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            svar = _http.get(k, url, hva=hva, params=params)
            data = svar.json()
            ser, ext = raw._serialiser(data)
            sti = raw._ledig_sti(MAPPE, dato, ext)
            sha, ny = raw.arkiver_ny(MAPPE, dato, data)
            logg.append({
                "hva": hva, "metode": "GET", "url": str(svar.request.url),
                "status": svar.status_code, "fetched_at": hentet,
                "byte_utpakket": len(svar.content),
                "sha256_utpakket": hashlib.sha256(svar.content).hexdigest(),
                "headere": dict(svar.headers), "sha256": sha,
                "byte_serialisert": len(ser), "fil": sti.name if ny else "(finnes fra før)"})

        kall(LAG, "a: metadata, lag 80", {"f": "json"})
        for n in (1, 2):
            kall(f"{LAG}/query", f"a: lag 80 hele, henting {n}", SPORRING)
            time.sleep(20)
        ms = int(dt.datetime(2026, 9, 1, 12, tzinfo=dt.timezone.utc).timestamp() * 1000)
        kall(f"{LAG}/query", "a: lag 80 historicMoment 01.09.2026",
             dict(SPORRING, historicMoment=str(ms)))

    ut = ARKIV_DIR / MAPPE / f"{dato}.m1b.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in logg:
        print(f"{p['status']} {p['byte_utpakket']:>8} {p['sha256'][:12]} {p['fil']:<24} {p['hva']}")


if __name__ == "__main__":
    main()
