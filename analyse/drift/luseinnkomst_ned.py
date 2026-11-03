"""MALING-DRIFT 0d: går antallet lokaliteter i en uke noen gang ned?

    .venv/bin/python analyse/drift/luseinnkomst_ned.py > analyse/drift/luseinnkomst_ned.txt

For hver uke i data/arkiv/lusetall-innkomst/: antallet lokaliteter
(`len(localities)`) i hver henting, i rekkefølgen de ble gjort. En henting
er enten en kropp i mappa eller en post i en fangstlogg
(`<dato>.fangst[.N].logg.json`), som også fører de uendrede hentingene med
sha256 og antall. Rekkefølgen er `fetched_at`: fra fangstloggen, og for en
kropp ingen fangstlogg nevner (skrevet av målingen 02.11.2026) fra
målingens logg, første kall mot uka. Finnes ingen av delene, står kroppen
først etter løpenummeret (regelen i etterskriften 03.11.2026).

Uke N−4 hentes også av innsamlingen til data/arkiv/lusetall/. Den kroppen
står med i rekken for sin uke, med `fetched_at` fra snapshotet
data/raw/lusetall/<mandag>.parquet. Samme endepunkt og samme
serialisering (arkiver_luseinnkomst.py), så antallene kan sammenlignes.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parents[2]
DATAREPO = ROT.parent / "havbruk-radar-data" / "data"
MAPPE = DATAREPO / "arkiv" / "lusetall-innkomst"


def kropp(sti: Path) -> tuple[str, int]:
    with gzip.open(sti, "rb") as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest(), len(json.loads(data)["localities"])


def main() -> None:
    print("MALING-DRIFT 0d — antall lokaliteter per henting, per uke")
    print(f"mappe: {MAPPE}\n")

    hentinger: dict[str, list[tuple[str, str, int, str]]] = {}
    kjent: set[str] = set()
    for logg in sorted(MAPPE.glob("*.fangst*.logg.json")):
        for post in json.loads(logg.read_text())["uker"]:
            if post.get("status") not in ("ny", "uendret"):
                continue
            hentinger.setdefault(post["observed_at"], []).append(
                (post["fetched_at"], post["sha256"], post["lokaliteter"],
                 f"{logg.name} ({post['status']})"))
            kjent.add(post["sha256"])

    maling: dict[str, str] = {}
    for logg in sorted(MAPPE.glob("*.maling*.logg.json")):
        for post in json.loads(logg.read_text()):
            deler = post.get("url", "").rstrip("/").split("/")
            if len(deler) > 2 and deler[-3] == "locality":
                nokkel = f"{deler[-2]}/{int(deler[-1]):02d}"
                maling[nokkel] = min(maling.get(nokkel, "~"), post["fetched_at"])

    kropper = sorted(p for p in MAPPE.glob("*.json.gz"))
    print(f"{len(kropper)} kropper, "
          f"{sum(len(v) for v in hentinger.values())} poster i fangstloggene\n")
    for sti in kropper:
        sha, n = kropp(sti)
        mandag = sti.name[:10]
        if sha not in kjent:
            # Skrevet av målingen 02.11; ingen fangstlogg nevner den.
            aar, uke = dt.date.fromisoformat(mandag).isocalendar()[:2]
            hentinger.setdefault(mandag, []).insert(
                0, (maling.get(f"{aar}/{uke:02d}", ""), sha, n,
                    f"{sti.name} (målingen)"))
        raa = DATAREPO / "raw" / "lusetall" / f"{mandag}.parquet"
        innsamlet = DATAREPO / "arkiv" / "lusetall" / f"{mandag}.json.gz"
        if innsamlet.exists() and raa.exists() and not any(
                h[3].startswith("lusetall/") for h in hentinger[mandag]):
            hentet = pl.read_parquet(raa, columns=["fetched_at"])["fetched_at"]
            s, m = kropp(innsamlet)
            hentinger[mandag].append((str(hentet.min()), s, m,
                                      f"lusetall/{innsamlet.name} (innsamlingen)"))

    ned = []
    for mandag in sorted(hentinger):
        # Stabil sortering: en kropp uten tidspunkt ("") står først.
        rad = sorted(hentinger[mandag], key=lambda h: h[0])
        print(f"{mandag}: {len(rad)} henting(er)")
        for t, sha, n, hvor in rad:
            print(f"    {t:<32} {n:>5}  {sha}  {hvor}")
        for (t1, _, n1, _), (t2, _, n2, _) in zip(rad, rad[1:]):
            if n2 < n1:
                ned.append((mandag, t1, n1, t2, n2))
    print(f"\nNed fra en henting til neste for samme uke: {len(ned)}")
    for mandag, t1, n1, t2, n2 in ned:
        print(f"    {mandag}: {n1} ({t1}) -> {n2} ({t2})")


if __name__ == "__main__":
    main()
