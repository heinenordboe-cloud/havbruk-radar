"""MALING-DRIFT, økt 3b: halv mandag og hel tirsdag gjennom run.py, uten --tving.

    .venv/bin/python analyse/drift/gjenkjoring_etter.py > analyse/drift/gjenkjoring_etter.txt

`run.main()` selv, `--bare sjotemperatur` og UTEN `--tving`, så
frekvensvakten og steg 2b avgjør om kilden hentes — som i drift. Hver
kjøring i en egen prosess med HAVBRUK_DATA_DIR pekt til en kopi av
data/raw/sjotemperatur/ (datoene før 2026-10-05), health.json og
feltnormal/. I kopien av health.json er `sist_ok` for sjotemperatur satt
til 2026-10-26, uka før, som om mandagens innsamling ennå ikke hadde gått.
Nettet er en falsk httpx-transport som i kroppssjekk.py.

    mandag  2026-11-02  den halve kroppen (første halvdel av
                        data/arkiv/sjotemperatur/2026-10-05.txt.gz)
    tirsdag 2026-11-03  den hele kroppen

Det som leses, er filene run.py etterlot: snapshotene for uka med merket,
`sist_ok` etter hver kjøring, og changelog-radene for uka per type.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
DATAREPO = ROT.parent / "havbruk-radar-data" / "data"
KROPP = "sjotemperatur/2026-10-05.txt.gz"
UKA = "2026-10-05"


def _kropp(hva: str) -> bytes:
    with gzip.open(DATAREPO / "arkiv" / KROPP, "rb") as f:
        hel = f.read()
    return hel[: len(hel) // 2] if hva == "halv" else hel


def en(hva: str, dato: str) -> None:
    sys.path.insert(0, str(ROT))
    os.chdir(ROT)
    import datetime as dt

    import httpx

    from core import kodeproveniens

    data = _kropp(hva)

    def svar(self, request):
        if "connect/token" in str(request.url):
            return httpx.Response(200, json={"access_token": "x", "expires_in": 3600,
                                             "token_type": "Bearer"}, request=request)
        return httpx.Response(200, content=data, request=request,
                              headers={"Content-Type": "text/csv"})

    httpx.HTTPTransport.handle_request = svar
    kodeproveniens.krev_sporbar = lambda *a, **k: ("0" * 40, "rent")

    import run

    class Klokke(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime.fromisoformat(dato + "T06:00:00+00:00")

    run.datetime = Klokke
    sys.argv = ["run.py", "--bare", "sjotemperatur"]
    sys.exit(run.main())


def main() -> None:
    import polars as pl

    print("Halv mandag og hel tirsdag gjennom run.py, uten --tving")
    print(f"datarepo: {DATAREPO}")
    for hva in ("halv", "hel"):
        b = _kropp(hva)
        print(f"  {hva:<5} {len(b):>7} B  sha256 {hashlib.sha256(b).hexdigest()}")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "raw" / "sjotemperatur").mkdir(parents=True)
        for p in sorted((DATAREPO / "raw" / "sjotemperatur").glob("*.parquet")):
            if p.name[:10] < UKA:
                shutil.copy2(p, data / "raw" / "sjotemperatur" / p.name)
        helse = json.loads((DATAREPO / "health.json").read_text())
        helse["sjotemperatur"]["sist_ok"] = "2026-10-26"
        (data / "health.json").write_text(json.dumps(helse))
        if (DATAREPO / "feltnormal").is_dir():
            shutil.copytree(DATAREPO / "feltnormal", data / "feltnormal")
        print(f"  volum_referanse {helse['sjotemperatur'].get('volum_referanse')}, "
              f"sist_ok før mandag 2026-10-26\n")

        env = dict(os.environ, HAVBRUK_DATA_DIR=str(data),
                   BARENTSWATCH_CLIENT_ID="prove", BARENTSWATCH_CLIENT_SECRET="prove")
        for hva, dato in (("halv", "2026-11-02"), ("hel", "2026-11-03")):
            r = subprocess.run([sys.executable, __file__, "--en", hva, dato], env=env,
                               capture_output=True, text=True, timeout=900)
            print(f"{dato} ({hva}): exit {r.returncode}")
            for l in r.stdout.splitlines():
                if any(s in l for s in ("[ok", "[FEIL", "[delvis]", "[vent]", "[har]")):
                    print(f"    {l.strip()[:150]}")
            h = json.loads((data / "health.json").read_text())["sjotemperatur"]
            print(f"    health: sist_ok {h.get('sist_ok')}, sist_forsok {h.get('sist_forsok')}, "
                  f"sist_ufullstendig {h.get('sist_ufullstendig')}")
            for p in sorted((data / "raw" / "sjotemperatur").glob(f"{UKA}*.parquet")):
                s = pl.read_parquet(p)
                print(f"    snapshot {p.name}: {s.height} rader, "
                      f"ufullstendig {sorted(set(s['ufullstendig']))}")
            sti = data / "changelog" / "sjotemperatur" / f"{UKA}.parquet"
            e = pl.read_parquet(sti) if sti.exists() else None
            for t in ("ny", "endret", "borte"):
                d = e.filter(pl.col("change_type") == t) if e is not None else None
                print(f"    changelog {UKA} {t:<7} "
                      f"{0 if d is None else d.height:>5} rader")
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--en":
        en(sys.argv[2], sys.argv[3])
    else:
        main()
