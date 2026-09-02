"""Hypotesetesten: hvor mye av ROC er bestemt allerede i kildeleddet?

    python analyse/kildeledd_mot_roc.py

Kjøres mot den PRE-REGISTRERTE stoppregelen i
docs/beslutninger/2026-08-31-hypotesen-omdefineres.md:

    R² ≥ 0,67 samlet  OG  innen-PO R² ≥ 0,25.  Begge må holde.

Regelen ble satt 31.08.2026 og regnet på nytt 01.09.2026 da celletallet
endret seg — begge ganger FØR noe tall var sett. Den justeres ikke her.
Består den ikke, er svaret «består ikke».

## De to variantene, og bare de to

    HOVED       kildens utvandringsMIDTPUNKT per (po, år) ± 20 dager.
                Mangler midtpunktet for en celle, FALLER CELLA UT — den
                fylles ikke.

                Ikke start- og sluttdato: kilden sluttet å oppgi dem
                etter 2020. Se `vindu_hoved` for målingen, og tilføyelse
                (2) i stoppregelnotatet for valget, som ble skrevet ned
                og committet (c314849) FØR noen korrelasjon var regnet.
                Halvbredden er den eneste frie parameteren, og den er
                VÅR — lengden er kildens egen.

    KONTROLL    fast uke 16-24 for alle PO alle år.

Kontrollen er ikke et alternativ som kan «vinne». Resultatet dens er
alt publisert (01.09.2026, R² = 0,5226) og kjøres uendret her bare for
at de to skal kunne stilles ved siden av hverandre. Den er der for å måle
hvor mye vindusvalget betyr, og den er KJENT skjev: 26.08.2026 ble
overlappen mellom uke 16-24 og ekspertgruppens eget vindu målt til 100 %
i PO1-2 og 0 % i PO13, monotont fallende med breddegrad. Et svakt
resultat i kontrollen kan derfor ikke skilles fra den skjevheten, og det
er nettopp derfor hovedvarianten er hovedvarianten.

En TREDJE variant kjøres ikke. Å prøve flere aggregeringer til én
består, er p-hacking, og da faller hele poenget med å skrive regelen på
forhånd.
"""

from __future__ import annotations

import datetime as dt
import math
import statistics as st
import sys
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

import kildeledd                                    # noqa: E402
from analyse import terskel_av_n                    # noqa: E402
from analyse import kjoringslogg                    # noqa: E402
from core.paths import DATA_DIR                     # noqa: E402

UT = ROT / "analyse" / "ut"
LOGG = UT / "kildeledd_mot_roc.kjoring.log"

F_ROC = "hi_smittepress_roc_indeks"
F_START = "utvandring_start"
F_SLUTT = "utvandring_slutt"
F_MEDIAN = "utvandring_median"

# Halvbredden i hovedvariantens vindu. Kilden oppgir LENGDEN selv —
# «den totale utvandringsperioden er satt til å vare i 40 dager som i
# tidligere år» (2024- og 2025-rapportene) — men den forankrer de 40
# dagene på 25 %-datoen, og det er 50 %-midtpunktet vi har. ±20 dager
# sentrerer kildens egen lengde på det punktet vi faktisk kjenner.
#
# Dette er den ENESTE frie parameteren i aggregeringen, og den er VÅR.
# Den er valgt og skrevet ned 01.09.2026 FØR noen korrelasjon var
# regnet ut — se tilføyelse (2) i stoppregelnotatet, commit c314849.
HALVBREDDE_DAGER = 20

# Stoppregelen. Det SAMLEDE leddet er en funksjon av n og slås opp i
# `analyse/terskel_av_n.py`, som er den samme tabellen som står i
# notatet — ikke et tall skrevet av her. Et tall skrevet av ville vært
# to tellere for samme sak, som er formen F6, F7 og F8 hadde.
#
# Innen-PO-leddet er IKKE en funksjon av n: metoden der var «velg
# |r| = 0,5 og kontroller at den er skilt fra null», ikke «løs for nedre
# kant». Det står derfor som et tall.
GRENSE_INNEN_PO = 0.25

KONTROLL_UKER = (16, 24)


# ------------------------------------------------------------- statistikk

def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    tel = sum((a - mx) * (b - my) for a, b in zip(x, y))
    nev = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return tel / nev if nev else float("nan")


def spearman(x: list[float], y: list[float]) -> float:
    def rang(v):
        par = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(par):
            j = i
            while j + 1 < len(par) and v[par[j + 1]] == v[par[i]]:
                j += 1
            snitt = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[par[k]] = snitt
            i = j + 1
        return r
    return pearson(rang(x), rang(y))


def fisher_ci(r: float, df: int) -> tuple[float, float]:
    """95 %-intervall for r. df = n − 3 samlet; se notatet."""
    if df <= 0 or abs(r) >= 1:
        return float("nan"), float("nan")
    se = 1 / math.sqrt(df)
    z = math.atanh(r)
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


# ----------------------------------------------------------------- lesing

def les_ekspertgruppen(logg: kjoringslogg.Kjoringslogg) -> pl.DataFrame:
    """Gjeldende celle per (år, po, FELT) — ikke per fil.

    ## Hvorfor begge versjonsvalg leses

    `logg.les()` gir ÉN fil per dato. `GJELDENDE` er den sist utgitte, og
    for et år som er revidert er det revisjonen. Det er riktig når man
    spør «hva sier kilden nå om denne DATOEN», og feil her.

    Målt: 2025-rapporten reviderer 2024, men den restaterer bare
    KATEGORIEN — 26 observasjoner mot 2024-rapportens 50. Leser man bare
    `GJELDENDE`, forsvinner hele 2024s ROC, og n faller fra 58 til 46
    uten at noe sier fra. Samme mekanisme skjuler
    utvandringsvinduene: de finnes bare i 2020-rapporten, og 2020 er
    revidert av 2021-rapporten.

    En revisjon som ikke nevner et felt, har ikke TRUKKET TILBAKE feltet.
    Gjeldende påstand om (år, po, felt) er derfor den sist utgitte raden
    SOM FINNES for det feltet — og da må begge versjonene leses.

    Begge lesingene føres i loggen, som alt annet.
    """
    deler = [ramme for _, ramme in logg.les(
        "ekspertgruppen", "2000-01-01", "2099-12-31",
        versjonsvalg=kjoringslogg.ALLE)]
    alle = pl.concat(deler)
    return (alle
            .with_columns(pl.col("observed_at").str.slice(0, 4).cast(pl.Int64).alias("aar"))
            .sort("published_at")
            .group_by(["aar", "entity_id", "field"])
            .agg(pl.col("value").last()))


def celler(ramme: pl.DataFrame, felt: str) -> dict[tuple[int, int], str]:
    d = ramme.filter(pl.col("field") == felt)
    return {(r["aar"], int(r["entity_id"])): r["value"] for r in d.iter_rows(named=True)}


# ------------------------------------------------------------ aggregering

def vindu_hoved(median: dict, po: int, aar: int):
    """Kildens midtpunkt ± HALVBREDDE_DAGER, eller None. Fylles ALDRI.

    ## Hvorfor ikke start- og sluttdatoen

    Fordi kilden slutter å oppgi dem etter 2020. Målt på alle seks
    arkiverte kroppene 01.09.2026:

        2020        start + slutt + median, alle som datoer.  13/13 PO
        2021        BARE medianen                             13/13 PO
        2022-2025   medianen, og grensene som LØS PROSA       13/13 PO
                    («fra siste halvdel av april til begynnelsen av
                    juni») — og 13/13 IDENTISK i alle fire årene

    Vedlegg I («Oversikt over laksevassdrag og utvandringstidspunkt for
    smolt») ville hatt datoene per elv, men er utgitt separat og finnes
    ikke i noen kropp. Det er altså ikke et uttrekk som mangler; det er
    en størrelse kilden sluttet å publisere.

    ## Hvorfor dette ikke er kontrollvariantens feil om igjen

    Kontrollen er ubrukelig ikke fordi den bommer, men fordi den bommer
    SYSTEMATISK MED BREDDEGRAD. Målt mot 2020, det ene året der kildens
    ekte vindu finnes:

                      snitt Jaccard   korr. mellom treff og PO-nummer
        fast uke 16-24     0,516            r = -0,928
        midtpunkt ± 20 d   0,750            r = -0,028

    Restfeilen her er støy, ikke en gradient som kan forveksles med den
    variabelen som slår alle prediktorene.

    ## Samme vindusregel for ALLE celler

    Også for 2020, der det ekte vinduet finnes. To ulike vindusdefinisjoner
    i én regresjon ville gjort cellene usammenlignbare, og forskjellen
    mellom dem ville ligget i utfallet uten å være synlig. Valget er
    uansett tomt i praksis: 2020 har ingen ROC-celle.
    """
    m = median.get((aar, po))
    if not m:
        return None
    midt = dt.date.fromisoformat(m)
    bredde = dt.timedelta(days=HALVBREDDE_DAGER)
    return midt - bredde, midt + bredde


def vindu_kontroll(po: int, aar: int):
    """Fast uke 16-24, mandag til mandag."""
    lav, hoy = KONTROLL_UKER
    return (dt.date.fromisocalendar(aar, lav, 1),
            dt.date.fromisocalendar(aar, hoy, 7))


def prediktor(full: pl.DataFrame, po: int, vindu) -> float | None:
    """Middel av kildeleddet over ukene i vinduet. None = ingen uker."""
    a, b = vindu
    d = full.filter((pl.col("po") == po)
                    & (pl.col("uke_mandag") >= a.isoformat())
                    & (pl.col("uke_mandag") <= b.isoformat()))
    return None if d.is_empty() else float(d["verdi"].mean())


def bygg(full, roc, median, variant: str):
    """(po, aar) -> (kildeledd, roc), og hvorfor celler falt ut."""
    par, uten_vindu, uten_uker = {}, [], []
    for (aar, po), verdi in sorted(roc.items()):
        v = (vindu_hoved(median, po, aar) if variant == "hoved"
             else vindu_kontroll(po, aar))
        if v is None:
            uten_vindu.append((aar, po))
            continue
        p = prediktor(full, po, v)
        if p is None:
            uten_uker.append((aar, po))
            continue
        par[(aar, po)] = (p, float(verdi))
    return par, uten_vindu, uten_uker


def mål(par: dict) -> dict:
    """R² samlet, innen-PO og Spearman. Tomt inn gir tomt ut."""
    if len(par) < 4:
        return {"n": len(par)}
    x = [v[0] for v in par.values()]
    y = [v[1] for v in par.values()]
    r = pearson(x, y)
    lo, hi = fisher_ci(r, len(x) - 3)

    # Innen-PO: trekk PO-middelet fra BEGGE sider. Frihetsgrader er
    # n − antall grupper, ikke n − 3: hver gruppe koster ett middel.
    po_er = sorted({po for _, po in par})
    mx = {p: st.mean([par[k][0] for k in par if k[1] == p]) for p in po_er}
    my = {p: st.mean([par[k][1] for k in par if k[1] == p]) for p in po_er}
    ix = [par[k][0] - mx[k[1]] for k in par]
    iy = [par[k][1] - my[k[1]] for k in par]
    df_innen = len(par) - len(po_er)
    r_innen = pearson(ix, iy) if df_innen > 1 else float("nan")

    return {
        "n": len(par), "grupper": len(po_er),
        "r": r, "R2": r * r, "ci_R2": (lo * abs(lo), hi * abs(hi)),
        "r_innen": r_innen, "R2_innen": r_innen * r_innen,
        "df_innen": df_innen,
        "rho": spearman(x, y),
    }


def grense_samlet(n: int) -> float:
    """Terskelen for det samlede leddet ved dette n.

    Slås opp, regnes ikke ut på nytt. Tabellen er skrevet ned FØR n var
    kjent (tilføyelse (1) i stoppregelnotatet), og en terskel som regnes
    ut etter at tallet er sett er ingen pre-registrert terskel.
    """
    return terskel_av_n.grense_for(n)


def skriv_mål(navn: str, m: dict) -> None:
    print(f"\n  --- {navn}")
    if m["n"] < 4:
        print(f"      n = {m['n']} — for få celler til å regne noe.")
        return
    lo, hi = m["ci_R2"]
    print(f"      n = {m['n']}, {m['grupper']} produksjonsområder")
    print(f"      SAMLET     r = {m['r']:+.4f}   R² = {m['R2']:.4f}   "
          f"95 % CI R² = [{lo:.4f}, {hi:.4f}]  (df = {m['n']-3})")
    print(f"      INNEN PO   r = {m['r_innen']:+.4f}   R² = {m['R2_innen']:.4f}   "
          f"(df = {m['df_innen']})")
    print(f"      Spearman rho = {m['rho']:+.4f}")
    g = grense_samlet(m["n"])
    a = "BESTOD" if m["R2"] >= g else "BESTOD IKKE"
    b = "BESTOD" if m["R2_innen"] >= GRENSE_INNEN_PO else "BESTOD IKKE"
    print(f"      mot {g} (n = {m['n']}):  {a}        "
          f"mot {GRENSE_INNEN_PO}:  {b}")


def main() -> int:
    UT.mkdir(parents=True, exist_ok=True)
    logg = kjoringslogg.Kjoringslogg("kildeledd_mot_roc", LOGG)
    logg.valg("stoppregel.kilde",
              "docs/beslutninger/2026-08-31-hypotesen-omdefineres.md")
    logg.valg("stoppregel.samlet", "slås opp i analyse/terskel_av_n.py "
                                   "på faktisk n")
    logg.valg("stoppregel.innen_po", GRENSE_INNEN_PO)
    logg.valg("stoppregel.satt_for_maaling", True)
    logg.valg("prediktor", "kildeledd FULL — N_fisk × middel_lok(lus × "
                           "(T+4,28)²) × 0,17, per PO per uke")
    logg.valg("utfall", f"ekspertgruppen.{F_ROC} per (po, år)")
    logg.valg("aggregering.hoved",
              f"kildens utvandringsMIDTPUNKT per (po, år) ± "
              f"{HALVBREDDE_DAGER} dager (kildens egen 40-dagers "
              f"utvandringsperiode); celle uten midtpunkt FALLER UT")
    logg.valg("aggregering.hoved.halvbredde_dager", HALVBREDDE_DAGER)
    logg.valg("aggregering.hoved.er_konstruert", True)
    logg.valg("aggregering.hoved.jaccard_mot_2020", 0.750)
    logg.valg("aggregering.hoved.korr_treff_mot_po", -0.028)
    logg.valg("aggregering.hoved.valgt_for_maaling", "c314849")
    logg.valg("aggregering.kontroll", f"fast uke {KONTROLL_UKER[0]}-{KONTROLL_UKER[1]}")
    logg.valg("varianter_kjort", "hoved, kontroll — ingen tredje")
    logg.valg("lesing.versjoner", "ALLE, slått sammen per (år, po, felt) "
                                  "på seneste published_at")

    serier = kildeledd.les_serier()
    if "full" not in serier:
        print("kildeledd-full.parquet finnes ikke. Kjør kildeledd.py først.")
        return 1
    full = serier["full"]
    logg.fil("kildeledd.full", DATA_DIR / "kildeledd" / "kildeledd-full.parquet")
    logg.valg("prediktor.rader", full.height)
    logg.valg("prediktor.spenn",
              f"{full['uke_mandag'].min()} .. {full['uke_mandag'].max()}")

    eg = les_ekspertgruppen(logg)
    roc = celler(eg, F_ROC)
    start, slutt = celler(eg, F_START), celler(eg, F_SLUTT)
    median = celler(eg, F_MEDIAN)

    print(f"\n{'='*74}\nHypotesetest: kildeleddet mot ROC")
    print(f"{'='*74}")
    print(f"\n  ROC-celler lest fra disk : {len(roc)}")
    for aar in sorted({a for a, _ in roc}):
        po = sorted(p for a, p in roc if a == aar)
        print(f"      {aar}: {len(po):>2} PO {po}")
    print(f"  vindu med START+SLUTT    : {len(start)} celler "
          f"({sorted({a for a, _ in start})})")
    print(f"  vindu med MIDTPUNKT      : {len(median)} celler "
          f"({sorted({a for a, _ in median})})")
    for aar in sorted({a for a, _ in median}):
        po = sorted(p for a, p in median if a == aar)
        print(f"      {aar}: {len(po):>2} PO")
    logg.valg("lest.roc_celler", len(roc))
    logg.valg("lest.vindu_start_slutt_celler", len(start))
    logg.valg("lest.vindu_midtpunkt_celler", len(median))
    logg.valg("lest.vindu_midtpunkt_aar", sorted({a for a, _ in median}) or "(ingen)")

    resultater = {}
    for variant in ("hoved", "kontroll"):
        par, uten_vindu, uten_uker = bygg(full, roc, median, variant)
        print(f"\n{'-'*74}\n  VARIANT: {variant}")
        print(f"      celler inn                 : {len(roc)}")
        print(f"      falt ut, mangler vindu     : {len(uten_vindu)}")
        if uten_vindu:
            per = {}
            for a, p in uten_vindu: per.setdefault(a, []).append(p)
            for a in sorted(per): print(f"          {a}: PO {sorted(per[a])}")
        print(f"      falt ut, ingen uker i vindu: {len(uten_uker)}"
              + (f"  {sorted(uten_uker)}" if uten_uker else ""))
        print(f"      celler igjen               : {len(par)}")
        logg.valg(f"{variant}.n", len(par))
        logg.valg(f"{variant}.falt_ut_uten_vindu", len(uten_vindu))
        logg.valg(f"{variant}.falt_ut_uten_uker", len(uten_uker))
        m = mål(par)
        resultater[variant] = m
        skriv_mål(variant, m)
        for k in ("R2", "R2_innen", "rho", "n"):
            if k in m:
                logg.valg(f"{variant}.{k}", f"{m[k]:.4f}" if isinstance(m[k], float) else m[k])

    print(f"\n{'='*74}")
    h = resultater["hoved"]
    if h["n"] < 4:
        print("  UTFALL: stoppregelen KAN IKKE EVALUERES.")
        print(f"  Hovedvarianten har n = {h['n']}. Regelen er pre-registrert mot")
        print("  ekspertgruppens eget utvandringsvindu, og det finnes ikke for")
        print("  noen celle som også har ROC.")
        print("  Kontrollen kan ikke tre inn i stedet — den er kjent")
        print("  breddegradsskjev, og det er grunnen til at den er kontroll.")
        logg.valg("utfall", "KAN IKKE EVALUERES — hovedvarianten har n = 0")
    else:
        a = h["R2"] >= grense_samlet(h["n"])
        b = h["R2_innen"] >= GRENSE_INNEN_PO
        print(f"  UTFALL: {'BESTOD' if a and b else 'BESTOD IKKE'}")
        logg.valg("utfall", "bestod" if a and b else "bestod ikke")
    print(f"{'='*74}")

    sti = logg.skriv()
    print(f"\n  kjøringslogg: {sti}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
