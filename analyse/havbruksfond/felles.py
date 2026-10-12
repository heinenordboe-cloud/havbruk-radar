"""Felles for målingen av Havbruksfondet: filteret, andelene og kroppene.

Svarene står i docs/MALING-HAVBRUKSFOND.md. Alt her leser data som
allerede ligger i datarepoet; ingenting hentes fra nettet.

## Fordelingsnøkkelen, ordrett fra instruksen av 27.09.2024

    «Både kommunenes og fylkeskommunenes andel fordeles forholdsmessig
    basert på klarert lokalitets-MTB i den enkelte kommune og
    fylkeskommune, slik det går frem av akvakulturregistreret
    1. september kl. 12.00 i utbetalingsåret.»

    «Lokalitets-MTB (maksimal tillatt biomasse) for alminnelige
    matfisktillatelser og tillatelser til særlige formål benyttes for
    fordelingsnøkkel. Kun lokaliteter for laks, ørret og regnbueørret i
    sjøvann inngår i fordelingsnøkkelen.»

## Filteret, og hvorfor det har to ledd

Ledd 1 er feltene i akvakultursnapshotet. Ledd 2 er artene på
tillatelsene lokaliteten er koblet til, lest av eierskapskroppen —
for `arter` på lokaliteten sier hva lokaliteten er KLARERT for, ikke
hvilke tillatelser som står der. MÅLT 12.10.2026 mot Fiskeridirektoratets
egen lokalitetsliste for 2025 (`Lok. per. 01.09.25`): av 1 065
lokaliteter som består ledd 1 per 31.08.2026, holder ledd 2 elleve
utenfor. Ni av dem var også utenfor Fiskeridirektoratets liste — åtte
med bare matfisktillatelser uten laks, ørret eller regnbueørret (torsk,
kveite), én med bare algetillatelse. To var INNE hos dem: 10768 og 15236,
Havbruksstasjonen i Tromsø, 1 625 t, med tillatelser for røye, torsk,
kveite og skjell. Det er et avvik vi ikke kan forklare fra kroppene, og
det står i dokumentet.

Lokaliteter uten noen aktiv kobling holdes INNE. Fiskeridirektoratet
regnet med to slike i 2025; regelverket sier ikke hva som skal skje med
dem, og det er Fiskeridirektoratets praksis som avgjøres mot.

## Lokaliteter over en kommunegrense

Instruksen deler en slik lokalitet etter «kartfestet arealbeslag». Det
har vi ikke — kroppen har ett punkt per lokalitet. Fiskeridirektoratets
regneark for 2025 har andelene for de ti lokalitetene som ble delt da, og
de brukes her, merket. En lokalitet som har kommet til eller flyttet
grense etter 01.09.2025 kan ikke deles av oss, og havner i sin
registrerte kommune.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROT))
from publiseringsvakt import xlsx_ark  # noqa: E402

D = Path(os.environ.get("HAVBRUK_DATA_DIR",
                        ROT.parent / "havbruk-radar-data" / "data"))

# Laks, ørret og regnbueørret, som Fiskeridirektoratet koder dem.
LAKSEARTER = {"071101": "Laks", "071301": "Ørret", "071401": "Regnbueørret"}

FILTER = """\
Ledd 1, akvakultursnapshotet (data/raw/akvakultur/<dato>.parquet):
    'SALMON' in arter            (laks, ørret, regnbueørret)
    vanntype        == 'Salt'
    plasseringstype == 'Offshore'
    kapasitet_enhet == 'TN'      (MTB i tonn)
  Ikke filtrert på: klareringstype (PERMANENT og TEMPORARY tas med),
  er_slakteri, har_kommersiell_aktivitet.
Ledd 2, eierskapskroppen (data/arkiv/eierskap/<dato>.json.gz):
    holdes UTENFOR hvis lokaliteten har aktive koblinger og INGEN av
    tillatelsene har laks (071101), ørret (071301) eller regnbueørret
    (071401) i species.fishCodes. Uten aktive koblinger: holdes inne.
Vekt: kapasitet (MTB, tonn). Kommune: kommunenummer. Fylke: fylkesnummer.
Delte lokaliteter: andelen fra Fiskeridirektoratets 2025-regneark."""


def sha256_fil(sti: Path) -> str:
    return hashlib.sha256(sti.read_bytes()).hexdigest()


def bred(dato: str) -> tuple[pl.DataFrame, dict]:
    """Akvakultursnapshotet for `dato`, én rad per lokalitet."""
    sti = D / "raw" / "akvakultur" / f"{dato}.parquet"
    d = pl.read_parquet(sti)
    meta = {"sti": str(sti.relative_to(D.parent)),
            "parquet_sha256": sha256_fil(sti),
            # Snapshotene fra før 31.08.2026 har ikke alle kolonnene.
            "raw_hash": (d["raw_hash"].unique().to_list()
                         if "raw_hash" in d.columns else []),
            "fetched_at": (d["fetched_at"].unique().to_list()
                           if "fetched_at" in d.columns else [])}
    w = d.pivot(on="field", index="entity_id", values="value",
                aggregate_function="first")
    return w.with_columns(pl.col("kapasitet").cast(pl.Float64)), meta


def tillatelser(dato: str) -> dict[str, dict]:
    """licenseNr -> tillatelsen slik eierskapskroppen for `dato` har den."""
    raw = gzip.open(D / "arkiv" / "eierskap" / f"{dato}.json.gz", "rb").read()
    return {t["licenseNr"]: t for t in json.loads(raw)["tillatelser"]}


def er_laks(t: dict) -> bool:
    return bool({x["code"] for x in (t.get("species") or {})
                 .get("fishCodes", [])} & set(LAKSEARTER))


def lakselisenser(dato: str) -> tuple[dict[str, bool], dict]:
    """siteNr -> har minst én aktiv laksetillatelse. Fravær = ingen kobling."""
    sti = D / "arkiv" / "eierskap" / f"{dato}.json.gz"
    raw = gzip.open(sti, "rb").read()
    b = json.loads(raw)
    per: dict[str, bool] = {}
    for t in b["tillatelser"]:
        arter = {f["code"] for f in (t.get("species") or {}).get("fishCodes", [])}
        laks = bool(arter & set(LAKSEARTER))
        for c in t.get("connections", []):
            if c.get("active"):
                per[c["siteNr"]] = per.get(c["siteNr"], False) or laks
    return per, {"sti": str(sti.relative_to(D.parent)),
                 "sha256": hashlib.sha256(raw).hexdigest()}


def ledd1(w: pl.DataFrame) -> pl.DataFrame:
    return w.filter(pl.col("arter").str.contains("SALMON")
                    & (pl.col("vanntype") == "Salt")
                    & (pl.col("plasseringstype") == "Offshore")
                    & (pl.col("kapasitet_enhet") == "TN"))


def filtrer(w: pl.DataFrame, lisens: dict[str, bool]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(med, holdt_utenfor_av_ledd_2)."""
    l1 = ledd1(w)
    ute = [e for e in l1["entity_id"] if e in lisens and not lisens[e]]
    return (l1.filter(~pl.col("entity_id").is_in(ute)),
            l1.filter(pl.col("entity_id").is_in(ute)))


def fdir_regneark(aar: int) -> tuple[dict[str, list[list[str]]], dict]:
    """Fiskeridirektoratets beregningsregneark for `aar`, fra arkivet."""
    mappe = D / "arkiv" / "havbruksfondet"
    tittel = f"Utbetalinger fra Havbruksfondet {aar}"
    for sti in sorted(mappe.glob("*.bin.gz")):
        raw = gzip.open(sti, "rb").read()
        ark = xlsx_ark(raw) if raw[:2] == b"PK" else None
        if not ark:
            continue
        ark = dict(ark)
        forste = ark.get("Utbetalingsoversikt", [[""]])[0]
        if forste and forste[0].strip() == tittel:
            return ark, {"sti": str(sti.relative_to(D.parent)),
                         "sha256": hashlib.sha256(raw).hexdigest()}
    raise FileNotFoundError(f"fant ikke regnearket for {aar} i {mappe}")


def delte_2025() -> dict[str, list[tuple[str, float]]]:
    """Lokalitetene Fiskeridirektoratet delte mellom kommuner 01.09.2025."""
    ark, _ = fdir_regneark(2025)
    per = collections.defaultdict(list)
    for r in ark["Lok. per. 01.09.25"][2:]:
        if r and r[0].isdigit():
            per[r[0]].append((r[2], float(r[5])))
    return {k: v for k, v in per.items() if len(v) > 1}


def kommunenavn(w: pl.DataFrame) -> dict[str, str]:
    """kommunenummer -> navn, fra HELE snapshotet (også ufiltrerte rader)."""
    return dict(w.select(["kommunenummer", "kommune"]).unique().iter_rows())


def andeler(med: pl.DataFrame, delte: dict, navn: dict[str, str]
            ) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(per kommune, per fylke) med MTB og andel."""
    rader = []
    for e, kom, kap in med.select(
            ["entity_id", "kommunenummer", "kapasitet"]).iter_rows():
        for k, a in (delte.get(e) or [(kom, 1.0)]):
            rader.append((k, kap * a, e in delte))
    r = pl.DataFrame(rader, schema=["kommunenummer", "mtb", "delt"],
                     orient="row")
    kom = (r.group_by("kommunenummer").agg(pl.col("mtb").sum(),
                                            pl.col("delt").any())
           .with_columns(pl.col("kommunenummer").replace_strict(
               navn, default="?").alias("kommune"))
           .with_columns((pl.col("mtb") / pl.col("mtb").sum()).alias("andel"))
           .sort("mtb", descending=True))
    fyl = (r.with_columns(pl.col("kommunenummer").str.slice(0, 2)
                          .alias("fylkesnummer"))
           .group_by("fylkesnummer").agg(pl.col("mtb").sum())
           .with_columns((pl.col("mtb") / pl.col("mtb").sum()).alias("andel"))
           .sort("mtb", descending=True))
    return kom, fyl


FYLKER = {"11": "Rogaland", "15": "Møre og Romsdal", "18": "Nordland",
          "31": "Østfold", "32": "Akershus", "33": "Buskerud",
          "39": "Vestfold", "40": "Telemark", "42": "Agder",
          "46": "Vestland", "50": "Trøndelag", "55": "Troms",
          "56": "Finnmark"}
