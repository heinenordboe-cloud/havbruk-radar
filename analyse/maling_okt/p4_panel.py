"""Punkt 4, steg 1: lokalitet × uke-panel bygget direkte fra arkivkroppene.

Leser data/arkiv/lusetall/*.json.gz (BarentsWatch, én kropp per uke) og
data/arkiv/sjotemperatur/*.txt.gz (BarentsWatch-eksporten for samme uke,
som også bærer «Lusegrense uke», «Over lusegrense uke», PO og «Trolig
uten fisk»). Snapshotene brukes ikke: panelet er MÅLT mot kroppene.

Skriver /tmp/maling-okt/p4/panel.parquet og kropp-hashene ved siden av.
Finnes flere kropper for samme uke (løpenummer), brukes den SISTE.
"""
import csv
import gzip
import hashlib
import io
import json
import os
import re
from pathlib import Path

import polars as pl

D = Path(os.environ.get("HAVBRUK_DATA_DIR", "../havbruk-radar-data/data"))
UT = Path("/tmp/maling-okt/p4"); UT.mkdir(parents=True, exist_ok=True)


def siste_per_dato(mappe, ext):
    valgt = {}
    for f in sorted(mappe.glob(f"*.{ext}.gz")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:\.(\d+))?\." + ext, f.name)
        n = int(m.group(2) or 1)
        if m.group(1) not in valgt or n > valgt[m.group(1)][0]:
            valgt[m.group(1)] = (n, f)
    return {d: f for d, (n, f) in sorted(valgt.items())}


BOOL = ["isFallow", "hasSalmonoids", "hasReportedLice", "hasCleanerfishDeployed",
        "hasMechanicalRemoval", "hasSubstanceTreatments", "hasPd", "hasIla",
        "isOnLand", "isSlaughterHoldingCage"]
rader, hasher = [], []
for dato, f in siste_per_dato(D / "arkiv/lusetall", "json").items():
    b = gzip.open(f, "rb").read()
    hasher.append(f"lusetall {dato} {hashlib.sha256(b).hexdigest()} {f.name}")
    for l in json.loads(b)["localities"]:
        r = {"uke": dato, "loknr": int(l["localityNo"]),
             "lus": l.get("avgAdultFemaleLice")}
        for k in BOOL:
            r[k] = l.get(k)
        rader.append(r)
lus = pl.DataFrame(rader, schema_overrides={"lus": pl.Float64})

UKJENT = {}
rader = []
for dato, f in siste_per_dato(D / "arkiv/sjotemperatur", "txt").items():
    b = gzip.open(f, "rb").read()
    hasher.append(f"sjotemperatur {dato} {hashlib.sha256(b).hexdigest()} {f.name}")
    for r in csv.DictReader(io.StringIO(b.decode("utf-8-sig"))):
        def tall(x):
            x = (x or "").strip().replace(",", ".")
            try:
                return float(x) if x else None
            except ValueError:
                UKJENT[x] = UKJENT.get(x, 0) + 1   # f.eks. «Ukjent»
                return None
        rader.append({"uke": dato, "loknr": int(r["Lokalitetsnummer"]),
                      "lusegrense": tall(r["Lusegrense uke"]),
                      "over_grense_bw": (r["Over lusegrense uke"] or "").strip() or None,
                      "temp": tall(r["Sjøtemperatur"]),
                      "trolig_uten_fisk": (r["Trolig uten fisk"] or "").strip() or None,
                      "po": (r["ProduksjonsområdeId"] or "").strip() or None})
sj = pl.DataFrame(rader)
p = lus.join(sj, on=["uke", "loknr"], how="left").sort("loknr", "uke")
p.write_parquet(UT / "panel.parquet")
(UT / "kropper-sha256.txt").write_text("\n".join(hasher) + "\n")
print(p.height, "rader,", p["loknr"].n_unique(), "lokaliteter,", p["uke"].n_unique(), "uker",
      p["uke"].min(), "->", p["uke"].max())
print("lusetall-rader uten treff i sjøtemperaturkroppen:", p.filter(pl.col("lusegrense").is_null() & pl.col("po").is_null()).height)
print("ikke-numeriske verdier i tallkolonnene:", UKJENT)
print("sha256 over hashlista:", hashlib.sha256("\n".join(hasher).encode()).hexdigest())
