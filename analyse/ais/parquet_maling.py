"""Parquet som analyselag for BarentsWatch-timene: størrelse og om alle felt kommer med.

    .venv/bin/python -m analyse.ais.parquet_maling <time.txt.zst>...

Ikke et analyselag; en måling av hva det ville kostet (MALING-AIS,
tillegget 30.10.2026). For hver time:

  - hver linje er `<vår tid>\\t<JSON>`; JSON-en flates ikke, nestede
    objekter blir struct-kolonner
  - én rad per melding, med `mottatt` (vår tid) og `rad` (linjenummeret)
    som egne kolonner, sortert på (mmsi, msgtime)
  - skrevet med zstd inni, nivå 3 og 19
  - lest tilbake, og hver rad sammenlignet med JSON-en den kom fra, med
    nullfelt fjernet: en nøkkel som ikke var i meldingen, er null i
    Parquet, og det er ikke et tapt felt

Parquet er ikke byte-likt med rålaget (nøkkelrekkefølge, tallformat,
mellomrom); det er derfor det ikke kan erstatte det.
"""
import hashlib
import io
import json
import sys
from collections import Counter
from compression import zstd
from pathlib import Path

import polars as pl


def uten_null(v):
    if isinstance(v, dict):
        return {k: uten_null(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [uten_null(x) for x in v]
    return v


def stier(d: dict, pre: str = "") -> list[str]:
    ut = []
    for k, v in d.items():
        ut.append(pre + k)
        if isinstance(v, dict):
            ut += stier(v, pre + k + ".")
    return ut


def maal(sti: Path) -> dict:
    raa = zstd.decompress(sti.read_bytes())
    rader, nokler = [], Counter()
    for i, linje in enumerate(raa.splitlines()):
        t, _, j = linje.partition(b"\t")
        d = json.loads(j)
        nokler.update(stier(d))
        rader.append({"rad": i, "mottatt": t.decode(), **d})
    df = pl.DataFrame(rader, infer_schema_length=None, strict=False)
    df = df.sort(["mmsi", "msgtime", "rad"])
    ut = {"time": sti.name, "sha256_lagret": hashlib.sha256(sti.read_bytes()).hexdigest(),
          "meldinger": len(rader), "raa_bytes": len(raa), "lagret_zstd19_bytes": sti.stat().st_size,
          "json_nokler": len(nokler), "kolonner": df.width}
    for niva in (3, 19):
        buf = io.BytesIO()
        df.write_parquet(buf, compression="zstd", compression_level=niva)
        ut[f"parquet_zstd{niva}_bytes"] = buf.tell()
    buf.seek(0)
    tilbake = pl.read_parquet(buf).sort("rad").to_dicts()
    avvik, ulike = Counter(), 0
    for r, orig in zip(tilbake, rader, strict=True):
        r, orig = uten_null(r), uten_null(orig)
        if r != orig:
            ulike += 1
            for k in set(r) | set(orig):
                if r.get(k) != orig.get(k):
                    avvik[k] += 1
    ut["rader_ulik_json"] = ulike
    ut["felt_med_avvik"] = dict(avvik.most_common())
    ut["nokler"] = dict(sorted(nokler.items()))
    return ut


def main() -> None:
    for p in sys.argv[1:]:
        print(json.dumps(maal(Path(p)), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
