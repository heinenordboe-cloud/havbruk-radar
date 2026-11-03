"""MALING-DRIFT 0b: hva changeloggen gjør med et halvt snapshot.

    .venv/bin/python analyse/drift/halvt_snapshot.py > analyse/drift/halvt_snapshot.txt

To deler, og stoppregelen i etterskriften 03.11.2026 gjelder den andre.

PRØVEN. Første halvdel av den ekte kroppen
data/arkiv/sjotemperatur/2026-10-05.txt.gz (sha256 8e3ed284…), tolket av
sources/sjotemperatur.py, stemplet som runner.run_all() gjør, og så diffet,
skrevet, scoret og ført i changeloggen som run.py steg 4–7 gjør. Det skjer
i en egen prosess med HAVBRUK_DATA_DIR pekt til en tom mappe med en kopi av
data/raw/sjotemperatur/ fra datoene før 2026-10-05. Den HELE kroppen kjøres
samme vei i en egen kopi, og forskjellen mellom de to er det den halve
kroppen alene skaper.

Neste uke (2026-10-12) er ikke hentet ennå. Tilbakeslaget — at det som
manglet kommer tilbake som «ny» når neste kropp er hel — prøves ved å la
den hele kroppen komme uka etter det halve snapshotet: samme rader, datert
2026-10-12. Da er hver forskjell tilbakeslaget og ingenting annet.

ARKIVET. Hvert snapshot i data/raw/<kilde>/ (nyeste påstand per dato, som
snapshot.previous() velger), antall entiteter. Et halvt snapshot har færre
enn 90 % av entitetene i snapshotet foran, og snapshotet etter har igjen
minst 90 %. For hvert slikt: `borte` i changeloggen på datoen, og hvor
mange av de samme entitetene som står som `ny` på datoen etter. Ingenting
skrives i datarepoet; den delen leser bare.
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
from dataclasses import replace
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
DATAREPO = ROT.parent / "havbruk-radar-data" / "data"
KROPP = "sjotemperatur/2026-10-05.txt.gz"
DATO, NESTE = "2026-10-05", "2026-10-12"
ANDEL = 0.90


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- prøven

def _rad(navn: str, endr) -> dict:
    """Rader og lokaliteter per endringstype."""
    import polars as pl
    ut = {"navn": navn, "rader": endr.height}
    for t in ("ny", "endret", "borte", "felt_ny", "felt_borte"):
        d = endr.filter(pl.col("change_type") == t)
        ut[t] = (d.height, d["entity_id"].n_unique())
    return ut


def prove(hva: str) -> None:
    """Én kropp gjennom run.py steg 4–7, i HAVBRUK_DATA_DIR. Skriver JSON."""
    sys.path.insert(0, str(ROT))
    os.chdir(ROT)
    import polars as pl

    from core import changelog, diff, signals, snapshot
    from core.runner import stempl
    from sources.sjotemperatur import Sjotemperatur

    with gzip.open(DATAREPO / "arkiv" / KROPP, "rb") as f:
        hel = f.read()
    kilde = Sjotemperatur()

    def obs(kropp: bytes, dato: str):
        tekst = kropp.decode("utf-8-sig")
        rader = stempl(kilde.parse(tekst, dato), source_version=kilde.version,
                       raw_hash=_sha(kropp), utvalg={"rapporttype": ["Lice"]},
                       kilde=kilde)
        return rader

    kropp = hel if hva == "hel" else hel[: len(hel) // 2]
    rader = obs(kropp, DATO)
    ramme = snapshot.to_frame(rader)
    endr = diff.compare(ramme, DATO)
    snapshot.write(rader, DATO)
    changelog.skriv_per_dato(endr)
    scoret = signals.score(endr)
    lest = changelog.merk_feltbevegelse(changelog.les_alt())
    ut = {"kropp": hva, "byte": len(kropp), "sha256": _sha(kropp),
          "observasjoner": len(rader),
          "lokaliteter": ramme["entity_id"].n_unique(),
          "mot_forrige": _rad("mot 2026-09-28", lest.filter(
              pl.col("observed_at") == DATO)),
          "scoret_treff": signals.treff(scoret).height,
          # Fra changeloggen slik den leses (etter merk_feltbevegelse),
          # samme ramme som tabellen over.
          "borte_id": sorted(lest.filter((pl.col("observed_at") == DATO)
                                         & (pl.col("change_type") == "borte"))
                             ["entity_id"].unique().to_list()),
          "endret": sorted(f"{r['entity_id']}|{r['field']}|{r['new_value']}"
                           for r in lest.filter(
                               (pl.col("observed_at") == DATO)
                               & (pl.col("change_type") == "endret"))
                           .iter_rows(named=True))}

    # Uka etter: den hele kroppen, datert NESTE, mot det som nå står skrevet.
    neste = [replace(r, observed_at=NESTE) for r in obs(hel, NESTE)]
    endr2 = diff.compare(snapshot.to_frame(neste), NESTE)
    snapshot.write(neste, NESTE)
    changelog.skriv_per_dato(endr2)
    lest2 = changelog.merk_feltbevegelse(changelog.les_alt())
    ut["uka_etter"] = _rad("hel kropp uka etter", lest2.filter(
        pl.col("observed_at") == NESTE))
    ut["uka_etter_treff"] = signals.treff(signals.score(endr2)).height
    ut["ny_uka_etter_id"] = sorted(lest2.filter(
        (pl.col("observed_at") == NESTE) & (pl.col("change_type") == "ny"))
        ["entity_id"].unique().to_list())
    print(json.dumps(ut, ensure_ascii=False))


def kjor_prove(hva: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "raw" / "sjotemperatur").mkdir(parents=True)
        for p in sorted((DATAREPO / "raw" / "sjotemperatur").glob("*.parquet")):
            if p.name[:10] < DATO:
                shutil.copy2(p, data / "raw" / "sjotemperatur" / p.name)
        env = dict(os.environ, HAVBRUK_DATA_DIR=str(data))
        r = subprocess.run([sys.executable, __file__, "--prove", hva], env=env,
                           capture_output=True, text=True, timeout=900)
        if r.returncode:
            raise SystemExit(r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])


def linje(r: dict) -> str:
    return (f"{r['navn']:<20} rader {r['rader']:>6}   "
            + "   ".join(f"{t} {r[t][0]:>5} ({r[t][1]:>4} lok.)"
                         for t in ("ny", "endret", "borte", "felt_ny", "felt_borte")))


# ---------------------------------------------------------------- arkivet

def arkivet() -> None:
    """Halve snapshots i data/raw/ og changelog-radene på datoene deres."""
    sys.path.insert(0, str(ROT))
    os.chdir(ROT)
    import polars as pl

    from core import changelog, snapshot
    from core.paths import RAW_DIR

    logg = changelog.les_alt(ufiltrert=True).select(
        "source", "observed_at", "entity_id", "change_type")
    funn = 0
    for mappe in sorted(p for p in RAW_DIR.iterdir() if p.is_dir()):
        kilde = mappe.name
        datoer = snapshot.datoer(kilde)
        antall = []
        for d in datoer:
            ramme = snapshot.forrige_versjon(kilde, d)
            antall.append(ramme["entity_id"].n_unique() if ramme is not None else 0)
        halve = [i for i in range(1, len(datoer) - 1)
                 if antall[i] < ANDEL * antall[i - 1]
                 and antall[i + 1] >= ANDEL * antall[i - 1]]
        print(f"  {kilde:<20} {len(datoer):>4} snapshots, "
              f"{len(halve)} halve")
        for i in halve:
            d, etter = datoer[i], datoer[i + 1]
            borte = set(logg.filter((pl.col("source") == kilde)
                                    & (pl.col("observed_at") == d)
                                    & (pl.col("change_type") == "borte"))
                        ["entity_id"].to_list())
            tilbake = borte & set(logg.filter(
                (pl.col("source") == kilde) & (pl.col("observed_at") == etter)
                & (pl.col("change_type") == "ny"))["entity_id"].to_list())
            funn += len(tilbake)
            print(f"      {datoer[i - 1]} {antall[i - 1]:>6}  ->  {d} {antall[i]:>6}"
                  f"  ->  {etter} {antall[i + 1]:>6}   borte {len(borte):>5} "
                  f"entiteter, {len(tilbake):>5} av dem ny igjen {etter}")
    print(f"\n  Falske hendelser i arkivet etter stoppregelen: {funn} entiteter")


def main() -> None:
    with gzip.open(DATAREPO / "arkiv" / KROPP, "rb") as f:
        hel = f.read()
    print("MALING-DRIFT 0b — et halvt snapshot gjennom changeloggen")
    print(f"datarepo: {DATAREPO}\n")
    print(f"Kroppen: data/arkiv/{KROPP}  {len(hel)} B  sha256 {_sha(hel)}")
    print(f"Halv:    første {len(hel) // 2} B  sha256 {_sha(hel[: len(hel) // 2])}\n")

    ut = {hva: kjor_prove(hva) for hva in ("hel", "halv")}
    print("PRØVEN (run.py steg 4–7 i en kopi; changeloggen lest med "
          "merk_feltbevegelse)")
    for hva in ("hel", "halv"):
        r = ut[hva]
        print(f"  {hva:<5} {r['byte']:>7} B  {r['observasjoner']:>5} obs.  "
              f"{r['lokaliteter']:>5} lokaliteter  signaltreff {r['scoret_treff']}")
        print(f"        {linje(r['mot_forrige'])}")
        print(f"        {linje(r['uka_etter'])}  signaltreff {r['uka_etter_treff']}")
    falske_borte = sorted(set(ut["halv"]["borte_id"]) - set(ut["hel"]["borte_id"]))
    falske_endret = sorted(set(ut["halv"]["endret"]) - set(ut["hel"]["endret"]))
    tilbake = set(falske_borte) & set(ut["halv"]["ny_uka_etter_id"])
    print(f"\n  Bare den halve: borte for {len(falske_borte)} lokaliteter, "
          f"endret for {len({e.split('|')[0] for e in falske_endret})} "
          f"({len(falske_endret)} rader). {len(tilbake)} av de "
          f"{len(falske_borte)} står som ny uka etter.")
    for e in falske_endret[:5]:
        print(f"      endret bare i den halve: {e}")

    print("\nARKIVET (stoppregelen, data/raw/ og data/changelog/, bare lesing)")
    r = subprocess.run([sys.executable, __file__, "--arkivet"],
                       env=dict(os.environ, HAVBRUK_DATA_DIR=str(DATAREPO)),
                       capture_output=True, text=True, timeout=1800)
    print(r.stdout.rstrip())
    if r.returncode:
        print(r.stderr)
        sys.exit(r.returncode)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--prove":
        prove(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "--arkivet":
        arkivet()
    else:
        main()
