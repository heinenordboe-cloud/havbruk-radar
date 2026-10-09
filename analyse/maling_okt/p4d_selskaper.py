"""Punkt 4d: hvilke selskaper står bak brakkleggingene siste 12 måneder.

DAGENS eierkobling: lokalitet -> aktive tillatelser i eierskapskroppen
05.10.2026 -> eier. Ikke eieren da lokaliteten ble brakklagt. En lokalitet
med flere eiere telles hos hver. Personeide tillatelser er fjernet i
kroppen (regel 3), så en lokalitet uten selskapskobling telles for seg.
Krever /tmp/maling-okt/p4/brakk_12.parquet fra p4_sykluser.py.
"""
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path

import polars as pl

D = Path(os.environ.get("HAVBRUK_DATA_DIR", "../havbruk-radar-data/data"))
f = D / "arkiv/eierskap/2026-10-05.json.gz"
b = gzip.open(f, "rb").read()
print(f"eierskap 2026-10-05 sha256 {hashlib.sha256(b).hexdigest()}")
eiere = collections.defaultdict(set)
for l in json.loads(b)["tillatelser"]:
    for k in l.get("connections") or []:
        if k.get("active"):
            eiere[int(k["siteNr"])].add((l["legalEntityName"], l["openLegalEntityNr"]))

br = pl.read_parquet("/tmp/maling-okt/p4/brakk_12.parquet")
rader, uten = [], 0
for loknr, po in br.select("loknr", "po").iter_rows():
    e = eiere.get(loknr)
    if not e:
        uten += 1
        continue
    for navn, nr in e:
        rader.append((loknr, po, navn, nr, len(e)))
print(f"brakklegginger {br.height}, lokaliteter {br['loknr'].n_unique()}, "
      f"uten selskapskobling i dag {uten}, med flere eiere {sum(1 for r in rader if r[4] > 1)} rader")
df = pl.DataFrame(rader, schema=["loknr", "po", "selskap", "orgnr", "eiere"], orient="row")
pl.Config.set_tbl_rows(60); pl.Config.set_fmt_str_lengths(40)
tot = df.group_by("selskap", "orgnr").agg(pl.len().alias("brakkl"), pl.col("loknr").n_unique().alias("lok"),
                                           pl.col("po").unique().sort().alias("po")).sort("brakkl", descending=True)
print(tot.head(25))
print("selskaper totalt:", tot.height)
top = df.group_by("po", "selskap").len().sort("po", "len", descending=[False, True]).group_by("po", maintain_order=True).head(3)
print(top)
df.write_csv("/tmp/maling-okt/p4/brakk_12_selskap.csv")
