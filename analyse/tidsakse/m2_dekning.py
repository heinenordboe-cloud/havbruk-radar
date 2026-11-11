"""Dekningen i tidsaksen: per lag og uke, slik den faktisk ble bygget.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \\
        .venv/bin/python analyse/tidsakse/m2_dekning.py > analyse/tidsakse/m2_dekning.txt

Bygger tidsaksen med `tidsakse.bygg()` og skriver de tre filene til
`analyse/ut/tidsakse/` (ikke committet), med sha256, så tallene under er
knyttet til nøyaktig de filene. Telleren er lokaliteter med en ikke-tom
celle i laget (`<lag>__kilde` satt) per ISO-uke.

`m2_dekning.tsv` ved siden av har hele tabellen: én rad per uke på aksen,
én kolonne per lag. Utskriften og TSV-en er determinstiske.
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROT))

import tidsakse                                     # noqa: E402
from analyse import kjoringslogg                    # noqa: E402

UT = Path(__file__).resolve().parent
BYGG = ROT / "analyse" / "ut" / "tidsakse"

res = tidsakse.bygg(logg=kjoringslogg.Kjoringslogg("tidsakse", BYGG / tidsakse.LOGGNAVN))
summer = tidsakse.skriv(res, BYGG)
t = res.tabell


def skriv(*deler) -> None:
    print(*deler)


skriv("# Dekningen i tidsaksen (analyse/tidsakse/m2_dekning.py)")
skriv()
skriv("== 1. Filene")
for navn, sha in summer.items():
    skriv(f"   {navn} sha256 {sha} byte {(BYGG / navn).stat().st_size}")
n_lok, n_uke = t["lokalitet"].n_unique(), t["mandag"].n_unique()
skriv(f"   tidsakse.parquet: {t.height} rader = {n_lok} lokaliteter × {n_uke} uker "
      f"({t['uke'].min()}..{t['uke'].max()}), {len(t.columns)} kolonner")
skriv(f"   hendelser.parquet: {res.hendelser.height} rader; konflikter.parquet: "
      f"{res.konflikter.height} rader")

# ------------------------------------------------------------- per lag og uke
lagene = list(tidsakse.LAG)
per_uke = (t.group_by("mandag", "uke")
           .agg([pl.col(tidsakse.kolonne(lag, "kilde")).is_not_null().sum().alias(lag)
                 for lag in lagene]
                + [pl.col("konflikt").is_not_null().sum().alias("konflikt")])
           .sort("mandag"))
per_uke.write_csv(UT / "m2_dekning.tsv", separator="\t")

skriv()
skriv("== 2. Per lag: første og siste uke med en celle, uker med og uten, celler")
skriv("lag | første uke | siste uke | uker med celle | uker uten celle mellom første og siste | "
      "celler | median per uke med celle | høyest")
for lag in lagene:
    s = per_uke.filter(pl.col(lag) > 0)
    if s.is_empty():
        skriv(f"{lag} | - | - | 0 | - | 0 | - | -")
        continue
    mellom = per_uke.filter((pl.col("mandag") >= s["mandag"].min())
                            & (pl.col("mandag") <= s["mandag"].max()) & (pl.col(lag) == 0))
    skriv(f"{lag} | {s['uke'].min()} | {s['uke'].max()} | {s.height} | "
          f"{mellom.height}{(': ' + ', '.join(mellom['uke'].to_list())) if 0 < mellom.height <= 6 else ''} | "
          f"{int(s[lag].sum())} | {int(s[lag].median())} | {int(s[lag].max())}")

skriv()
skriv("== 3. Per år: lokalitetsuker med celle per lag (år = ISO-året i uka)")
aar = (per_uke.with_columns(pl.col("uke").str.slice(0, 4).alias("aar"))
       .group_by("aar").agg([pl.col(lag).sum() for lag in lagene] + [pl.len().alias("uker")])
       .sort("aar"))
skriv("år uker | " + " | ".join(lagene))
for r in aar.iter_rows(named=True):
    skriv(f"{r['aar']} {r['uker']:3d} | " + " | ".join(str(r[lag]) for lag in lagene))

skriv()
skriv("== 4. Uke for uke fra uke 33/2026, der de fleste lagene begynner")
skriv("uke | " + " | ".join(lagene) + " | konflikt")
for r in per_uke.filter(pl.col("mandag") >= "2026-08-10").iter_rows(named=True):
    skriv(f"{r['uke']} | " + " | ".join(str(r[lag]) for lag in lagene) + f" | {r['konflikt']}")

skriv()
skriv("== 5. Konflikter per par, og hendelser per type")
k = res.konflikter.group_by("par").agg(pl.len().alias("rader"),
                                       pl.col("lokalitet").n_unique().alias("lokaliteter"),
                                       pl.col("uke").min().alias("første"),
                                       pl.col("uke").max().alias("siste")).sort("par")
for r in k.iter_rows():
    skriv(f"   {r[0]}: {r[1]} celler, {r[2]} lokaliteter, {r[3]}..{r[4]}")
h = res.hendelser.group_by("r9", "type").agg(
    pl.len().alias("n"), pl.col("uke").filter(pl.col("uke") != "").min().alias("første"),
    pl.col("uke").max().alias("siste"),
    (pl.col("uke") == "").sum().alias("uten_uke")).sort("r9")
for r in h.iter_rows():
    skriv(f"   {r[0]} {r[1]}: {r[2]}, {r[3]}..{r[4]}, uten uke (bare intervall) {r[5]}")
st = res.hendelser.group_by("stempel_status").len().sort("stempel_status")
skriv("   stempel på første fil: " + ", ".join(f"{a or '(ingen)'} {b}" for a, b in st.rows()))
utelatt = int(t["eierskap__personform_utelatt"].cast(pl.Int64, strict=False).sum() or 0)
skriv(f"   eierleddet: lokalitetsuker med en tillatelse der eieren er en personform "
      f"(eier ikke ført): {t.filter(pl.col('eierskap__personform_utelatt').cast(pl.Int64, strict=False) > 0).height}, "
      f"tillatelser til sammen {utelatt}")
