"""Punkt 4: produksjonssykluser per lokalitet 2012–2026 fra lusetall.

Krever /tmp/maling-okt/p4/panel.parquet fra p4_panel.py (bygget av
arkivkroppene). Grenseregelen er målt, ikke valgt på forhånd; se
docs/MALING-FUNN-OKTOBER.md punkt 4a.

  UNIVERS    hasSalmonoids & !isOnLand & !isSlaughterHoldingCage
  PRODUKSJON isFallow == False
  SYKLUS     sammenhengende produksjonsuker; brakkavbrudd på 1–2 uker
             bygges over (tvetydig, telles for seg); hull i serien bryter
  KANT       uker uten lusetall i starten/slutten av en syklus trimmes
             bort og er «ikke tilordnbare»
  KORT       syklus på < 4 uker etter trimming er «tvetydig kort løp»
  SENSUR     syklus som berører seriens første/siste uke eller et hull
"""
import collections
import gzip
import json
import os
import sys
from pathlib import Path

import polars as pl

D = Path(os.environ.get("HAVBRUK_DATA_DIR", "../havbruk-radar-data/data"))
T = Path("/tmp/maling-okt/p4")
BRO = 2          # brakkavbrudd <= BRO uker bygges over
MIN = 4          # kortere enn MIN uker etter trimming = tvetydig
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(16); pl.Config.set_fmt_str_lengths(40)

p = pl.read_parquet(T / "panel.parquet").with_columns(pl.col("uke").str.to_date())
FORSTE, SISTE = p["uke"].min(), p["uke"].max()
univ = p.filter(pl.col("hasSalmonoids") & ~pl.col("isOnLand") & ~pl.col("isSlaughterHoldingCage"))
print(f"univers: {univ.height} lokalitetsuker, {univ['loknr'].n_unique()} lokaliteter "
      f"(slaktemerd-uker utelatt: {p.filter(pl.col('hasSalmonoids') & ~pl.col('isOnLand') & pl.col('isSlaughterHoldingCage')).height})")

u = univ.sort("loknr", "uke").with_columns(
    ((pl.col("uke") - pl.col("uke").shift(1).over("loknr")).dt.total_days() != 7)
    .fill_null(True).alias("brudd"))
u = u.with_columns(
    ((pl.col("isFallow") != pl.col("isFallow").shift(1).over("loknr")) | pl.col("brudd"))
    .fill_null(True).cum_sum().over("loknr").alias("run"))
runs = u.group_by("loknr", "run", maintain_order=True).agg(
    pl.col("isFallow").first().alias("brakk"), pl.len().alias("n"),
    pl.col("brudd").first().alias("etter_hull"))
runs = runs.with_columns(
    pl.col("brakk").shift(1).over("loknr").alias("forr"),
    pl.col("brakk").shift(-1).over("loknr").alias("neste"),
    pl.col("etter_hull").shift(-1).over("loknr").fill_null(True).alias("hull_etter"))
blipp = runs.filter(pl.col("brakk") & (pl.col("n") <= BRO) & (pl.col("forr") == False)
                    & (pl.col("neste") == False) & ~pl.col("etter_hull") & ~pl.col("hull_etter"))
print(f"tvetydig: brakkavbrudd på 1–{BRO} uker mellom to produksjonsløp: {blipp.height}")
u = u.join(blipp.select("loknr", "run").with_columns(pl.lit(True).alias("blipp")),
           on=["loknr", "run"], how="left").with_columns(pl.col("blipp").fill_null(False))
u = u.with_columns((~pl.col("isFallow") | pl.col("blipp")).alias("prod"))
u = u.with_columns(
    ((pl.col("prod") != pl.col("prod").shift(1).over("loknr")) | pl.col("brudd"))
    .fill_null(True).cum_sum().over("loknr").alias("sid"))

# Trimming av kanter uten lusetall
u = u.with_columns(
    pl.col("hasReportedLice").cast(pl.Int32).cum_sum().over("loknr", "sid").alias("_f"),
    pl.col("hasReportedLice").cast(pl.Int32).reverse().cum_sum().reverse().over("loknr", "sid").alias("_b"))
u = u.with_columns((pl.col("prod") & ((pl.col("_f") == 0) | (pl.col("_b") == 0))).alias("kant"))
cyc = u.filter(pl.col("prod") & ~pl.col("kant")).group_by("loknr", "sid").agg(
    pl.col("uke").min().alias("fra"), pl.col("uke").max().alias("til"), pl.len().alias("uker"),
    pl.col("blipp").sum().alias("blipp_uker"),
    (~pl.col("hasReportedLice")).sum().alias("uker_uten_lus"),
    # BWs egen regel, målt lik «Over lusegrense uke» i 409 118 av 409 118 uker
    (pl.col("lus").round(2) >= pl.col("lusegrense")).sum().alias("over_grense"),
    pl.col("lusegrense").is_not_null().sum().alias("med_grense"),
    (pl.col("over_grense_bw") == "Ja").sum().alias("over_grense_bw"),
    pl.col("hasMechanicalRemoval").sum().alias("mekanisk"),
    pl.col("hasSubstanceTreatments").sum().alias("medikament"),
    pl.col("hasCleanerfishDeployed").sum().alias("rensefisk"),
    pl.col("hasPd").sum().alias("pd"), pl.col("hasIla").sum().alias("ila"),
    pl.col("temp").mean().alias("temp"), pl.col("temp").is_not_null().sum().alias("temp_uker"),
    pl.col("po").drop_nulls().mode().first().alias("po"),
    pl.col("po").drop_nulls().n_unique().alias("po_n"),
    pl.col("brudd").first().alias("start_hull"))
# sensur: berører første/siste uke, eller grenser mot hull
sid_max = u.group_by("loknr", "sid").agg(pl.col("uke").min().alias("s0"), pl.col("uke").max().alias("s1"))
nxt = u.group_by("loknr", "sid").agg(pl.col("brudd").first().alias("b0")).sort("loknr", "sid").with_columns(
    pl.col("b0").shift(-1).over("loknr").fill_null(True).alias("hull_etter"))
cyc = cyc.join(sid_max, on=["loknr", "sid"]).join(nxt.select("loknr", "sid", "hull_etter"), on=["loknr", "sid"])
cyc = cyc.with_columns(
    ((pl.col("s0") == FORSTE) | pl.col("start_hull")).alias("sensur_start"),
    ((pl.col("s1") == SISTE) | pl.col("hull_etter")).alias("sensur_slutt"),
    (pl.col("uker") < MIN).alias("kort"))
cyc = cyc.with_columns((~pl.col("sensur_start") & ~pl.col("sensur_slutt") & ~pl.col("kort")).alias("hel"))
cyc.write_parquet(T / "sykluser.parquet")
u.select("loknr", "uke", "prod", "kant", "blipp", "sid", "isFallow", "po").write_parquet(T / "uker.parquet")

# --- 4a: telling og tilordning
prod_uker = u.filter(pl.col("prod")).height
kort_uker = cyc.filter(pl.col("kort"))["uker"].sum()
kant_uker = u.filter(pl.col("kant")).height
rapp_brakk = u.filter(pl.col("isFallow") & pl.col("hasReportedLice")).height
print(f"\nuker i univers {u.height}, produksjonsuker {prod_uker}, brakkuker {u.filter(~pl.col('prod')).height}")
print(f"ikke tilordnbare: kantuker uten lusetall {kant_uker}, uker i korte løp {kort_uker}, "
      f"brakkuker MED lusetall {rapp_brakk}")
ikke = kant_uker + kort_uker
print(f"andel ikke tilordnbare av produksjonsukene: {ikke}/{prod_uker} = {ikke/prod_uker:.2%}; "
      f"av alle uker i universet: {ikke/u.height:.2%}")
print(f"\nsykluser: {cyc.height} totalt; korte (<{MIN} uker) {cyc['kort'].sum()}; "
      f"sensurert start {cyc.filter(~pl.col('kort'))['sensur_start'].sum()}, "
      f"sensurert slutt {cyc.filter(~pl.col('kort'))['sensur_slutt'].sum()}; hele {cyc['hel'].sum()}")
print(f"lokaliteter med minst én hel syklus: {cyc.filter(pl.col('hel'))['loknr'].n_unique()}")
h = cyc.filter(pl.col("hel"))
print("lengde (uker) for hele sykluser:", h["uker"].describe().rows())
print(h.with_columns(pl.col("uker").cut([13, 26, 52, 65, 78, 91, 104, 130]).alias("b")).group_by("b").len().sort("b"))
print("sykluser med PO-skifte innen syklusen:", cyc.filter(pl.col("po_n") > 1).height)

# --- 4c: per syklus, fordelt per PO (bare hele sykluser)
# Flaggene døde: rensefisk etter 2023-04-17, medikament etter 2024-11-11.
for c in ("hasCleanerfishDeployed", "hasSubstanceTreatments", "hasMechanicalRemoval", "hasPd", "hasIla"):
    print(f"{c}: siste uke True {p.filter(pl.col(c))['uke'].max()}")
DOD = pl.date(2023, 4, 17)
pr = h.with_columns(pl.col("po").cast(pl.Int32)).group_by("po").agg(
    pl.len().alias("sykluser"),
    pl.col("uker").median().alias("uker_med"),
    (pl.col("over_grense") / pl.col("uker")).median().alias("andel_over_med"),
    (pl.col("over_grense") > 0).mean().alias("andel_m_over"),
    pl.col("mekanisk").median().alias("mek_med"),
    (pl.col("mekanisk") > 0).mean().alias("andel_m_mek"),
    pl.col("medikament").filter(pl.col("til") < DOD).median().alias("med_med*"),
    (pl.col("medikament") > 0).filter(pl.col("til") < DOD).mean().alias("andel_m_med*"),
    (pl.col("rensefisk") > 0).filter(pl.col("til") < DOD).mean().alias("andel_m_rf*"),
    (pl.col("til") < DOD).sum().alias("n*"),
    (pl.col("pd") > 0).mean().alias("andel_pd"),
    (pl.col("ila") > 0).mean().alias("andel_ila"),
    pl.col("temp").mean().alias("temp_snitt")).sort("po").with_columns(pl.col(pl.Float64).round(3))
print("\n4c per PO (hele sykluser):"); print(pr)
pr.write_csv(T / "per_po.csv")
print("grensesjekk: våre over_grense mot BW 'Over lusegrense uke'=Ja:",
      h["over_grense"].sum(), h["over_grense_bw"].sum())

alle = h.select(pl.len().alias("sykluser"), pl.col("uker").median(),
                (pl.col("over_grense") > 0).mean().alias("andel_m_over"),
                (pl.col("mekanisk") > 0).mean().alias("andel_m_mek"),
                (pl.col("pd") > 0).mean().alias("andel_pd"), (pl.col("ila") > 0).mean().alias("andel_ila"))
print("alle hele:", alle.rows())
print("hele sykluser per sluttår:", h.group_by(pl.col("til").dt.year()).len().sort("til").rows())

# --- 4d: brakklegging = første brakkuke etter en syklus (hele eller sensurert start)
avsl = cyc.filter(~pl.col("kort") & ~pl.col("sensur_slutt")).with_columns(
    (pl.col("til") + pl.duration(weeks=1)).alias("brakk_fra"))
avsl = avsl.with_columns(pl.col("brakk_fra").dt.strftime("%Y-%m").alias("mnd"),
                         pl.col("brakk_fra").dt.month().alias("m"), pl.col("po").cast(pl.Int32))
print("\n4d brakklegginger totalt:", avsl.height)
sesong = avsl.pivot(on="m", index="po", values="loknr", aggregate_function="len",
                    sort_columns=True).sort("po").fill_null(0)
print("per PO og kalendermåned, 2012–2026:"); print(sesong)
sesong.write_csv(T / "brakk_po_maaned_alle.csv")
SIST12 = SISTE - pl.duration(weeks=52)
s12 = avsl.filter(pl.col("brakk_fra") > SISTE - __import__("datetime").timedelta(weeks=52))
print(f"siste 12 mnd ({(SISTE - __import__('datetime').timedelta(weeks=52))} -> {SISTE}):", s12.height)
t12 = s12.pivot(on="mnd", index="po", values="loknr", aggregate_function="len",
                sort_columns=True).sort("po").fill_null(0)
print(t12); t12.write_csv(T / "brakk_po_maaned_12.csv")
s12.select("loknr", "po", "fra", "til", "uker", "brakk_fra").write_parquet(T / "brakk_12.parquet")
