"""Plausibilitetssjekk: følger kildeleddet dekningen i stedet for sjøen?

    .venv/bin/python analyse/dekning.py

Kildeleddet bygger på `middel_lok(lus x (T+4,28)^2)` over de lokalitetene
som RAPPORTERTE. Slutter en gruppe å rapportere — utslakting,
brakklegging eller manglende innrapportering — endres middelet uten at
lusepresset i sjøen har endret seg.

På en offentlig side er den forvekslingen alvorlig: ingen kan skille
«lus falt» fra «de mest infiserte anleggene ble tømt», og forskjellen er
usynlig i kurven. Denne fila leter etter sammenfallene.

Den KORRIGERER ingenting. Om serien skal justeres for dekning er en egen
avgjørelse; her måles bare hvor stort problemet er.
"""

from __future__ import annotations

import math
import statistics as st
import sys
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

import kildeledd                                    # noqa: E402


def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 3:
        return float("nan")
    mx, my = st.mean(x), st.mean(y)
    tel = sum((a - mx) * (b - my) for a, b in zip(x, y))
    nev = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return tel / nev if nev else float("nan")


def _endringer(r: pl.DataFrame) -> pl.DataFrame:
    """Uke-til-uke-endring i verdi og dekning, per PO.

    RELATIV endring i verdi (den er lognormal-aktig og spenner flere
    størrelsesordener) og ABSOLUTT i antall lokaliteter.

    Bare mot FORRIGE UKE, ikke mot forrige rad: serien har hull, og et
    hopp over et hull ville sett ut som en brå endring som ikke er det.
    """
    return (r.sort("po", "uke_mandag")
             .with_columns(
                 pl.col("uke_mandag").str.strptime(pl.Date, "%Y-%m-%d").alias("d"))
             .with_columns(
                 pl.col("verdi").shift(1).over("po").alias("verdi_f"),
                 pl.col("n_rapporterende").shift(1).over("po").alias("rapp_f"),
                 pl.col("d").shift(1).over("po").alias("d_f"))
             .filter((pl.col("d") - pl.col("d_f")).dt.total_days() == 7)
             .filter(pl.col("verdi_f") > 0)
             .with_columns(
                 ((pl.col("verdi") - pl.col("verdi_f")) / pl.col("verdi_f")).alias("dverdi"),
                 (pl.col("n_rapporterende") - pl.col("rapp_f")).alias("drapp")))


def main() -> int:
    serier = kildeledd.les_serier()
    if not serier:
        print("Ingen kildeledd-serie. Kjør kildeledd.py først.")
        return 1

    for navn, r in serier.items():
        print(f"\n{'='*76}\n{navn.upper()} — {r.height} rader\n{'='*76}")

        # --- 1. dekning per PO over tid -------------------------------
        print("\n  Rapporterende lokaliteter per PO (av alle i PO-et):")
        print(f"    {'PO':>3} {'uker':>6} {'rapp min':>9} {'median':>7} {'maks':>5}"
              f" {'i PO':>6} {'brakkl.':>8} {'aktiv+stille':>13}")
        for po in sorted(r["po"].unique().to_list()):
            d = r.filter(pl.col("po") == po)
            stille = (d["n_i_po"] - d["n_brakklagt"] - d["n_rapporterende"])
            print(f"    {po:>3} {d.height:>6} {d['n_rapporterende'].min():>9}"
                  f" {d['n_rapporterende'].median():>7.0f}"
                  f" {d['n_rapporterende'].max():>5}"
                  f" {d['n_i_po'].median():>6.0f}"
                  f" {d['n_brakklagt'].median():>8.0f}"
                  f" {stille.median():>13.0f}")

        e = _endringer(r)
        if e.is_empty():
            continue

        # --- 2. samvariasjon ------------------------------------------
        print("\n  Samvariasjon uke-til-uke, endring i verdi mot endring i "
              "antall rapporterende:")
        print(f"    {'PO':>3} {'n':>6} {'r':>8}   tolkning")
        alle_r = []
        for po in sorted(e["po"].unique().to_list()):
            d = e.filter(pl.col("po") == po)
            rr = pearson(d["drapp"].to_list(), d["dverdi"].to_list())
            alle_r.append(rr)
            flagg = "" if abs(rr) < 0.20 else ("  <- SAMVARIERER" if rr > 0
                                               else "  <- MOTSATT")
            print(f"    {po:>3} {d.height:>6} {rr:>+8.3f}{flagg}")
        samlet = pearson(e["drapp"].to_list(), e["dverdi"].to_list())
        print(f"    {'alle':>3} {e.height:>6} {samlet:>+8.3f}")

        # --- 3. de brå fallene ----------------------------------------
        print("\n  Uker der BÅDE dekningen og verdien falte brått"
              " (rapporterende -3 eller mer, verdi ned >30 %):")
        brå = (e.filter((pl.col("drapp") <= -3) & (pl.col("dverdi") <= -0.30))
                .sort("dverdi"))
        if brå.is_empty():
            print("    ingen")
        else:
            print(f"    {'PO':>3} {'uke':>12} {'rapp':>12} {'verdi':>10}")
            for row in brå.head(15).iter_rows(named=True):
                print(f"    {row['po']:>3} {row['uke_mandag']:>12}"
                      f" {int(row['rapp_f']):>5} -> {int(row['n_rapporterende']):<4}"
                      f" {row['dverdi']*100:>9.0f} %")
            print(f"    ({brå.height} slike uker av {e.height})")

        # --- 3b. hvor tynt er middelet? -------------------------------
        #
        # Det tydeligste funnet, og det som faktisk må stå på nettsiden:
        # et middel over 1-3 lokaliteter er ikke et områdeestimat. Ett
        # anlegg som tømmes svinger det fullstendig, og kurven viser et
        # fall som aldri skjedde i sjøen.
        print("\n  Hvor tynt er middelet?")
        for grense in (1, 3, 5, 10):
            d = r.filter(pl.col("n_rapporterende") <= grense)
            po_er = sorted(d["po"].unique().to_list())
            print(f"    n_rapporterende <= {grense:>2}: {d.height:>5} rader "
                  f"({d.height / r.height:>5.1%})"
                  + (f"  PO {po_er}" if po_er and len(po_er) <= 6 else
                     f"  {len(po_er)} PO"))

        print("\n  Andel uker med <= 5 rapporterende, per PO:")
        tynne = []
        for po in sorted(r["po"].unique().to_list()):
            d = r.filter(pl.col("po") == po)
            andel = d.filter(pl.col("n_rapporterende") <= 5).height / d.height
            if andel > 0.01:
                tynne.append((po, andel, int(d["n_rapporterende"].median())))
        for po, andel, med in sorted(tynne, key=lambda t: -t[1]):
            print(f"    PO {po:>2}: {andel:>6.1%} av ukene   (median {med})")
        if not tynne:
            print("    ingen PO over 1 %")

        # --- 4. systematisk forskjell mellom PO -----------------------
        print("\n  Systematisk: henger PO-ets typiske dekning sammen med "
              "PO-ets typiske verdi?")
        po_er = sorted(r["po"].unique().to_list())
        med_rapp = [float(r.filter(pl.col("po") == p)["n_rapporterende"].median())
                    for p in po_er]
        med_verdi = [float(r.filter(pl.col("po") == p)["verdi"].median())
                     for p in po_er]
        rr = pearson(med_rapp, med_verdi)
        print(f"    median n_rapporterende mot median verdi, over {len(po_er)} PO:"
              f" r = {rr:+.3f}")
        print("    (Et PO med mange anlegg har både mer rapportering og mer "
              "fisk. Sammenhengen er ventet og er ikke i seg selv en feil "
              "— den sier at PO-størrelse er en skjult variabel i enhver "
              "sammenligning MELLOM områder.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
