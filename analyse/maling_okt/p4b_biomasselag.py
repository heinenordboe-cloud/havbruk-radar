"""Punkt 4b: lusetallets brakk/produksjon mot biomasselagets `har_fisk`.

Biomasselaget er fryst ved `siste_rapport` (månedsslutt). Hver rad holdes
mot lusetall-uka som INNEHOLDER den datoen (mandag i ISO-uka), og mot
syklusklassifiseringen fra p4_sykluser.py. Bare ukene panelet dekker
(2012-01-02 .. 2026-09-07) kan sammenlignes.
"""
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path

import polars as pl

D = Path(os.environ.get("HAVBRUK_DATA_DIR", "../havbruk-radar-data/data"))
T = Path("/tmp/maling-okt/p4")
uker = pl.read_parquet(T / "uker.parquet")
panel = pl.read_parquet(T / "panel.parquet").with_columns(pl.col("uke").str.to_date()).select(
    "loknr", "uke", "isFallow", "hasReportedLice", "hasSalmonoids", "isOnLand", "isSlaughterHoldingCage")
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_cols(12)

for f in sorted((D / "arkiv/biomasselag").glob("*.json.gz")):
    b = gzip.open(f, "rb").read()
    rader = json.loads(b)
    df = pl.DataFrame([{"loknr": r["loknr"], "har_fisk": r["har_fisk"], "art": r.get("art"),
                        "siste": dt.datetime.fromtimestamp(r["siste_rapport"] / 1000, dt.UTC).date()
                        if r.get("siste_rapport") else None} for r in rader], infer_schema_length=None)
    df = df.with_columns((pl.col("siste") - pl.duration(days=pl.col("siste").dt.weekday() - 1)).alias("uke"))
    j = df.join(panel, on=["loknr", "uke"], how="left").join(
        uker.select("loknr", "uke", "prod", "kant"), on=["loknr", "uke"], how="left")
    j = j.with_columns(pl.when(pl.col("isFallow").is_null()).then(pl.lit("ikke i lusetall den uka"))
                       .when(~pl.col("hasSalmonoids") | pl.col("isOnLand") | pl.col("isSlaughterHoldingCage"))
                       .then(pl.lit("utenfor univers"))
                       .when(pl.col("kant")).then(pl.lit("produksjon, kantuke uten lus"))
                       .when(pl.col("prod")).then(pl.lit("produksjon"))
                       .otherwise(pl.lit("brakk")).alias("lusetall"))
    print(f"\n{f.name} sha256 {hashlib.sha256(b).hexdigest()}  rader {df.height}  "
          f"siste_rapport {df['siste'].min()} .. {df['siste'].max()}")
    sam = j.filter(pl.col("uke") <= dt.date(2026, 9, 7))
    print(sam.group_by("har_fisk", "lusetall").len().sort("lusetall", "har_fisk"))
    if f.name.startswith("2026-10-05"):
        x = sam.filter(pl.col("lusetall").is_in(["produksjon", "brakk"]))
        avvik = x.filter(((pl.col("har_fisk") == "Ja") & (pl.col("lusetall") == "brakk")) |
                         ((pl.col("har_fisk") == "Nei") & (pl.col("lusetall") == "produksjon")))
        print("avvik eksempler:"); print(avvik.select("loknr", "har_fisk", "art", "siste", "uke", "isFallow", "hasReportedLice").sort("siste", descending=True).head(12))
        print("avvik per siste_rapport-måned:", avvik.group_by(pl.col("siste").dt.strftime("%Y-%m")).len().sort("siste", descending=True).head(8).rows())
        print("enige per siste_rapport (siste 3 mnd):", x.filter(pl.col("siste") >= dt.date(2026, 6, 30)).group_by("siste", "har_fisk", "lusetall").len().sort("siste", "har_fisk", "lusetall").rows())
