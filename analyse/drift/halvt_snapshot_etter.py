"""MALING-DRIFT, økt 3b punkt 7: det halve snapshotet gjennom run.py, etter rettingen.

    .venv/bin/python analyse/drift/halvt_snapshot_etter.py > analyse/drift/halvt_snapshot_etter.txt

Ikke en etterligning av run.py, som halvt_snapshot.py (0b) er: dette er
`run.main()` selv, `--bare sjotemperatur --tving`, i en egen prosess med
HAVBRUK_DATA_DIR pekt til en kopi av data/raw/sjotemperatur/ (datoene før
2026-10-05), health.json og feltnormal/. Nettet er en falsk
httpx-transport, som i kroppssjekk.py: BarentsWatchs token-endepunkt får et
gyldig token, eksportkallet får kroppen. Kodeproveniensen er satt til en
fast sha.

    uke 41   kjøredato 2026-11-02, den halve kroppen (første halvdel av
             data/arkiv/sjotemperatur/2026-10-05.txt.gz)
    uke 42   kjøredato 2026-11-09, den HELE kroppen med Uke 41 byttet til
             42 i hver rad — konstruert: uke 42 er ikke hentet ennå, og
             tilbakeslaget skal måles mot en hel uke

Det som leses, er filene run.py etterlot: merket `ufullstendig` på
snapshotene og changelog-radene per type.
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


def _kropp(hva: str) -> bytes:
    with gzip.open(DATAREPO / "arkiv" / KROPP, "rb") as f:
        hel = f.read()
    if hva == "halv":
        return hel[: len(hel) // 2]
    tekst = hel.decode("utf-8-sig").splitlines()
    ut = [tekst[0]] + [("42" + linje[2:]) if linje.startswith("41,") else linje
                       for linje in tekst[1:]]
    return ("﻿" + "\n".join(ut) + "\n").encode("utf-8")


def en(hva: str, dato: str) -> None:
    """Én run.main() i denne prosessen, med kroppen på nettet."""
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
    sys.argv = ["run.py", "--bare", "sjotemperatur", "--tving"]
    sys.exit(run.main())


def main() -> None:
    import polars as pl

    print("Det halve snapshotet gjennom run.py, etter rettingen (økt 3b punkt 7)")
    print(f"datarepo: {DATAREPO}")
    for hva in ("halv", "hel42"):
        b = _kropp(hva)
        print(f"  {hva:<6} {len(b):>7} B  sha256 {hashlib.sha256(b).hexdigest()}")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "raw" / "sjotemperatur").mkdir(parents=True)
        for p in sorted((DATAREPO / "raw" / "sjotemperatur").glob("*.parquet")):
            if p.name[:10] < "2026-10-05":
                shutil.copy2(p, data / "raw" / "sjotemperatur" / p.name)
        shutil.copy2(DATAREPO / "health.json", data / "health.json")
        if (DATAREPO / "feltnormal").is_dir():
            shutil.copytree(DATAREPO / "feltnormal", data / "feltnormal")
        ref = json.loads((data / "health.json").read_text())["sjotemperatur"]
        print(f"  volum_referanse for sjotemperatur i health.json: "
              f"{ref.get('volum_referanse')}\n")

        env = dict(os.environ, HAVBRUK_DATA_DIR=str(data),
                   BARENTSWATCH_CLIENT_ID="prove", BARENTSWATCH_CLIENT_SECRET="prove")
        for hva, dato, uke in (("halv", "2026-11-02", "2026-10-05"),
                               ("hel42", "2026-11-09", "2026-10-12")):
            r = subprocess.run([sys.executable, __file__, "--en", hva, dato], env=env,
                               capture_output=True, text=True, timeout=900)
            linjer = [l for l in r.stdout.splitlines()
                      if "[ok" in l or "[FEIL" in l or "[delvis]" in l or "KREVER" in l]
            print(f"uke {uke} ({hva}, kjøredato {dato}): exit {r.returncode}")
            for l in linjer:
                print(f"    {l.strip()[:150]}")
            snap = pl.read_parquet(data / "raw" / "sjotemperatur" / f"{uke}.parquet")
            print(f"    snapshot {uke}: {snap.height} rader, "
                  f"{snap['entity_id'].n_unique()} lokaliteter, ufullstendig "
                  f"{sorted(set(snap['ufullstendig']))}")
            sti = data / "changelog" / "sjotemperatur" / f"{uke}.parquet"
            endr = pl.read_parquet(sti) if sti.exists() else None
            if endr is None:
                print("    changelog: ingen rader")
            else:
                for t in ("ny", "endret", "borte"):
                    d = endr.filter(pl.col("change_type") == t)
                    print(f"    changelog {t:<7} {d.height:>5} rader "
                          f"{d['entity_id'].n_unique():>5} lokaliteter  "
                          f"mot {sorted(set(d['forrige_observed_at']))}")
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--en":
        en(sys.argv[2], sys.argv[3])
    else:
        main()
