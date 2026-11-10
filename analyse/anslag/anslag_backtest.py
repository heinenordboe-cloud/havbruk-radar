#!/usr/bin/env python3
"""Anslag mot naiv referanse — BACKTEST, ikke forseglede anslag.

Spesifikasjonen står i FORHANDSREGISTRERING.md i samme mappe, committet
før noe utfall var lest (commit 85eed2c, 09.11.2026 04:00:37 UTC). Dette
skriptet gjør det fila sier, og ikke noe mer. Der registreringen var
taus, står presiseringen som en kommentar merket PRESISERING.

INGENTING HER TELLER I TREFFLISTA. Resultatene er hva en enkel modell
VILLE gjort i fortiden.

Lesing: bare gjennom `analyse.kjoringslogg.Kjoringslogg.les()` i
havbruk-radar, som går gjennom `snapshot.versjoner()` -> `_les()` og
dermed persondatafilteret. Kildens eget tillegg
(`Source.fjern_egne_personer`) kjøres etterpå for `eierskap` og
`eierskap_historikk`. Ingen rå parquet-lesing her.

Kjøring (fra havbruk-analyse):

    HAVBRUK_RADAR=../havbruk-radar \\
    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \\
        python revisjon/2026-11-09-anslag-backtest/anslag_backtest.py

`--mellomlager <fil>` pickler panelene ETTER lesedøra, så en ny kjøring
ikke leser 2 600 filer på nytt. Panelene er aggregater per lokalitet og
uke, uten navn.

Utskrift: tabellene i MALING-ANSLAG.md, og TSV-ene i `ut/`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import math
import os
import pickle
import random
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

HER = Path(__file__).resolve().parent
RADAR = Path(os.environ.get("HAVBRUK_RADAR")
             or HER.parents[2] / "havbruk-radar").resolve()
os.environ.setdefault(
    "HAVBRUK_DATA_DIR", str(RADAR.parent / "havbruk-radar-data" / "data"))
sys.path.insert(0, str(RADAR))

import polars as pl  # noqa: E402

from analyse import kjoringslogg as kl  # noqa: E402
from core import snapshot  # noqa: E402
from core.config import get  # noqa: E402
from core.paths import RAW_DIR  # noqa: E402

UT = HER / "ut"

# ---------------------------------------------------------------- konstanter
# Alt under står i FORHANDSREGISTRERING.md. Endres noe her, er det et AVVIK.

BASE = dt.date(2012, 1, 2)            # mandag, uke 1/2012: wi = 0
TRENING_FRA = dt.date(2017, 1, 2)
TRENING_TIL = dt.date(2022, 12, 26)   # siste mandag i trening
TEST_FRA = dt.date(2023, 1, 2)
PO_ER = [str(i) for i in range(1, 14)]
MIN_NEVNER = 5
GLATT = 5                             # sentrert sirkulært ukesnitt
BOOT_N = 2000
BOOT_FRO = 20261109
BOOT_BLOKK_UKE = 8
BOOT_BLOKK_MND = 3
VINDUER = (4, 8, 12)
# Ensidig t, 5 %, df = L-1. Tabellverdier: t_0.95(3), t_0.95(7), t_0.95(11).
T_KRIT = {4: 2.353, 8: 1.895, 12: 1.796}
P4_GRENSE = 0.6
SIG_GRENSE = 0.8
MAKS_STREKK = 13                      # S2, maks_nullstrekk
S1_GRENSE = 0.10
S3_UKER = 26
S3_MND = 12
HASARD_BOTTER = [(1, 26), (27, 52), (53, 65), (66, 78), (79, 91),
                 (92, 104), (105, 10**9)]

MERKE = "BACKTEST — teller ikke i trefflista"


def wi(d: dt.date) -> int:
    return (d - BASE).days // 7


def uke_dato(i: int) -> dt.date:
    return BASE + dt.timedelta(weeks=i)


def isouke(i: int) -> int:
    u = uke_dato(i).isocalendar()[1]
    return 52 if u == 53 else u


def mi(d: dt.date) -> int:
    return d.year * 12 + d.month - 1


def mnd_tekst(m: int) -> str:
    return f"{m // 12:04d}-{m % 12 + 1:02d}"


# ------------------------------------------------------------------ lesing

def _sti(kilde: str, dato: str, nr: int) -> Path:
    navn = f"{dato}.parquet" if nr == 1 else f"{dato}.{nr}.parquet"
    return RAW_DIR / kilde / navn


def _slaa_sammen(lest: list[tuple[str, pl.DataFrame]], felter: list[str]
                 ) -> pl.DataFrame:
    """Lange rader (dato, entity_id, field, value) for `felter`.

    Rekkefølgen fra `les()` er eldst utgitt først per dato. Ved ALLE
    vinner derfor den SISTE per (dato, entitet, felt), altså den sist
    utgitte påstanden om det feltet — lesemåten KILDE-EIERSKAP.md §1
    sier er den eneste riktige.
    """
    deler = []
    for dato, ramme in lest:
        sub = (ramme.filter(pl.col("field").is_in(felter))
               .select(["entity_id", "field", "value"])
               .with_columns(pl.lit(dato).alias("dato")))
        deler.append(sub)
    if not deler:
        return pl.DataFrame(schema={"dato": pl.Utf8, "entity_id": pl.Utf8,
                                    "field": pl.Utf8, "value": pl.Utf8})
    alt = pl.concat(deler, how="vertical")
    return (alt.group_by(["dato", "entity_id", "field"], maintain_order=True)
            .agg(pl.col("value").last()))


def _bred(lang: pl.DataFrame) -> pl.DataFrame:
    return lang.pivot(on="field", index=["dato", "entity_id"],
                      values="value", aggregate_function="last")


def les_alt(logg: kl.Kjoringslogg) -> dict:
    """Panelene, lest gjennom lesedøra. Ett kall per kilde og år."""
    hooker = snapshot._kilder_med_eget_tillegg()
    for kilde in ("eierskap", "eierskap_historikk"):
        if kilde not in hooker:
            raise SystemExit(f"STOPP: {kilde} har ikke eget persontillegg "
                             f"i registeret; persondatafilteret er ufullstendig.")

    sist = "2026-12-31"
    data: dict = {}

    # Lusetall, GJELDENDE. Per år for å holde minnet nede.
    lus = []
    for aar in range(2012, 2027):
        lest = logg.les("lusetall", f"{aar}-01-01", f"{aar}-12-31",
                        versjonsvalg=kl.GJELDENDE)
        lus.append(_slaa_sammen(lest, ["voksne_hunnlus", "lus_er_rapportert",
                                       "brakklagt", "har_pd"]))
    data["lus"] = _bred(pl.concat(lus))

    # Sjøtemperatur, ALLE, slått sammen per felt på sist utgitte.
    sjo = []
    for aar in range(2012, 2027):
        lest = logg.les("sjotemperatur", f"{aar}-01-01", f"{aar}-12-31",
                        versjonsvalg=kl.ALLE)
        sjo.append(_slaa_sammen(lest, ["lusegrense", "sjotemperatur",
                                       "temperatur_er_rapportert"]))
    data["sjo"] = _bred(pl.concat(sjo))

    # Biomasse, GJELDENDE.
    lest = logg.les("biomasse", "2017-01-01", sist, versjonsvalg=kl.GJELDENDE)
    data["bio"] = _bred(_slaa_sammen(lest, ["utsett_smolt_antall"]))

    # PO for lokalitet: akvakultur, siste snapshot.
    akv_dato = snapshot.datoer("akvakultur")[-1]
    akv = logg.les("akvakultur", akv_dato, akv_dato, versjonsvalg=kl.GJELDENDE)
    lok_po = dict(akv[-1][1].filter(pl.col("field") == "prodomraade_kode")
                  .select(["entity_id", "value"]).iter_rows())
    data["lok_po"] = {str(k): str(v).strip() for k, v in lok_po.items()}
    data["akv_dato"] = akv_dato

    # PO for tillatelse: eierskap, siste snapshot, etter kildens tillegg.
    eie_dato = snapshot.datoer("eierskap")[-1]
    eie = logg.les("eierskap", eie_dato, eie_dato, versjonsvalg=kl.GJELDENDE)
    ramme = hooker["eierskap"].fjern_egne_personer(eie[-1][1])
    data["till_po"] = {str(k): str(v).strip() for k, v in
                       ramme.filter(pl.col("field") == "prodomraade_kode")
                       .select(["entity_id", "value"]).iter_rows()}
    data["eie_dato"] = eie_dato
    data["eie_hook_tok"] = len(snapshot._tillegget_fjerner(hooker["eierskap"],
                                                            eie[-1][1]))

    # Overføringer, ALLE, kildens tillegg på hver fil FØR sammenslåing.
    lest = logg.les("eierskap_historikk", "2006-01-01", sist,
                    versjonsvalg=kl.ALLE)
    tok = 0
    filtrert = []
    hentet: dict[str, list[str]] = defaultdict(list)
    for dato, r in lest:
        etter = hooker["eierskap_historikk"].fjern_egne_personer(r)
        tok += r.select("entity_id").n_unique() - etter.select("entity_id").n_unique()
        filtrert.append((dato, etter))
        hentet[dato].append(snapshot.fetched_at_i(r) or "")
    data["over"] = _bred(_slaa_sammen(filtrert, ["tillatelse_nr", "journal_dato"]))
    data["over_hook_tok"] = tok
    data["over_hentet"] = dict(hentet)

    # S5: hva lesedøra tok ut av lokalitets- og PO-kildene.
    s5 = {}
    for kilde in ("lusetall", "sjotemperatur", "biomasse", "akvakultur"):
        sum_ = 0
        datoer = sorted({l.observed_at for l in logg._lesinger if l.kilde == kilde})
        for d in datoer:
            sum_ += sum(snapshot.filtrert_bort(kilde, d).values())
        s5[kilde] = (sum_, len(datoer))
    data["s5"] = s5

    # sha256 per fil som ble lest. Over FILA, som maling-protokollen sier.
    filer = []
    for l in logg._lesinger:
        sti = _sti(l.kilde, l.observed_at, l.versjon)
        h = hashlib.sha256(sti.read_bytes()).hexdigest()
        filer.append((l.kilde, l.observed_at, l.versjon,
                      str(sti.relative_to(RAW_DIR.parent.parent)), h, l.n_rader))
    data["filer"] = filer
    return data


# ------------------------------------------------------------- utfallene

def _hundredeler(tekst: str | None) -> int | None:
    """BarentsWatchs regel: to desimaler, halv opp. None hvis ulesbar."""
    if tekst is None:
        return None
    try:
        v = Decimal(str(tekst).strip()).quantize(Decimal("0.01"), ROUND_HALF_UP)
    except InvalidOperation:
        return None
    return int(v * 100)


def lokalitetspanel(data: dict) -> pl.DataFrame:
    """En rad per (uke, lokalitet) med PO og de feltene kandidatene trenger."""
    lus = data["lus"].rename({"entity_id": "lok"})
    sjo = data["sjo"].rename({"entity_id": "lok"})
    p = lus.join(sjo, on=["dato", "lok"], how="full", coalesce=True)
    po = pl.DataFrame({"lok": list(data["lok_po"]),
                       "po": list(data["lok_po"].values())})
    p = p.join(po, on="lok", how="left")
    p = p.with_columns(
        pl.col("dato").str.to_date().alias("d"),
    ).with_columns(
        ((pl.col("d") - pl.lit(BASE)).dt.total_days() // 7).cast(pl.Int64).alias("wi"),
    )
    # Hundredeler for lus og grense, via Decimal på unike verdier.
    for kol, ny in (("voksne_hunnlus", "lus_h"), ("lusegrense", "grense_h")):
        unike = [v for v in p[kol].unique().to_list() if v is not None]
        kart = {v: _hundredeler(v) for v in unike}
        p = p.with_columns(pl.col(kol).replace_strict(
            kart, default=None, return_dtype=pl.Int64).alias(ny))
    return p


def po_ukeserie(p: pl.DataFrame) -> pl.DataFrame:
    """y per (po, wi) for K1, K5, K6, med nevnere."""
    lus_ok = ((pl.col("lus_er_rapportert") == "True")
              & pl.col("lus_h").is_not_null() & pl.col("grense_h").is_not_null())
    temp_ok = ((pl.col("temperatur_er_rapportert") == "True")
               & pl.col("sjotemperatur").is_not_null())
    q = p.filter(pl.col("po").is_in(PO_ER))
    k16 = (q.filter(lus_ok)
           .with_columns((pl.col("lus_h") >= pl.col("grense_h")).cast(pl.Float64).alias("over"),
                         pl.col("voksne_hunnlus").cast(pl.Float64).alias("lusf"))
           .group_by(["po", "wi"])
           .agg(pl.col("over").mean().alias("K1"), pl.col("lusf").mean().alias("K6"),
                pl.len().alias("n_lus")))
    k5 = (q.filter(temp_ok)
          .with_columns(pl.col("sjotemperatur").cast(pl.Float64).alias("t"))
          .group_by(["po", "wi"])
          .agg(pl.col("t").mean().alias("K5"), pl.len().alias("n_temp")))
    return k16.join(k5, on=["po", "wi"], how="full", coalesce=True)


def hendelser(p: pl.DataFrame, felt: str) -> pl.DataFrame:
    """(lok, po, wi) der `felt` gikk False -> True fra uke wi-1 til wi.
    Begge ukene må ha lokaliteten med feltet. Fravær er ikke en hendelse."""
    a = p.select(["lok", "po", "wi", felt]).filter(pl.col(felt).is_not_null())
    b = a.with_columns((pl.col("wi") + 1).alias("wi")).rename({felt: "for"})
    j = a.join(b.select(["lok", "wi", "for"]), on=["lok", "wi"], how="inner")
    return j.filter((pl.col("for") == "False") & (pl.col(felt) == "True"))


# ------------------------------------------------------------- skåringen

def skaar(rader: list[dict], blokk: int, vinduer=VINDUER) -> dict:
    """rader: {i (utstedelsesindeks), po, y, a, b, m}. Bare hele rader."""
    rader = [r for r in rader if None not in (r["y"], r["a"], r["b"], r["m"])
             and not any(isinstance(r[k], float) and math.isnan(r[k])
                         for k in ("y", "a", "b", "m"))]
    if not rader:
        return {"n_rader": 0, "n_utst": 0}
    per = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    for r in rader:
        s = per[r["i"]]
        s[0] += abs(r["y"] - r["m"])
        s[1] += abs(r["y"] - r["a"])
        s[2] += abs(r["y"] - r["b"])
        s[3] += 1
    idx = sorted(per)
    Sm = [per[i][0] for i in idx]
    Sa = [per[i][1] for i in idx]
    Sb = [per[i][2] for i in idx]
    C = [per[i][3] for i in idx]
    N = len(idx)
    n = sum(C)
    mae_m, mae_a, mae_b = sum(Sm) / n, sum(Sa) / n, sum(Sb) / n
    ss_a = 1 - mae_m / mae_a if mae_a else float("nan")
    ss_b = 1 - mae_m / mae_b if mae_b else float("nan")

    # Blokk-bootstrap over utstedelser.
    rng = random.Random(BOOT_FRO)
    bs_a, bs_b = [], []
    B = min(blokk, N)
    for _ in range(BOOT_N):
        valgt: list[int] = []
        while len(valgt) < N:
            s = rng.randrange(0, N - B + 1)
            valgt.extend(range(s, s + B))
        valgt = valgt[:N]
        sm = sum(Sm[j] for j in valgt)
        sa = sum(Sa[j] for j in valgt)
        sb = sum(Sb[j] for j in valgt)
        bs_a.append(1 - sm / sa if sa else float("nan"))
        bs_b.append(1 - sm / sb if sb else float("nan"))
    bs_a.sort()
    bs_b.sort()
    lo = int(0.025 * BOOT_N)
    hi = int(0.975 * BOOT_N) - 1
    ut = {"n_rader": n, "n_utst": N, "mae_m": mae_m, "mae_a": mae_a,
          "mae_b": mae_b, "ss_a": ss_a, "ss_b": ss_b,
          "ss_a_lo": bs_a[lo], "ss_a_hi": bs_a[hi],
          "ss_b_lo": bs_b[lo], "ss_b_hi": bs_b[hi],
          "fra": idx[0], "til": idx[-1]}

    # Ukentlige differanser: snitt over PO av |e_ref| - |e_modell|.
    da = [(Sa[j] - Sm[j]) / C[j] for j in range(N)]
    db = [(Sb[j] - Sm[j]) / C[j] for j in range(N)]
    for L in vinduer:
        if N < L:
            ut[f"P{L}"] = ut[f"P{L}sig"] = float("nan")
            continue
        vinn = sig = tot = 0
        for s in range(0, N - L + 1):
            w = range(s, s + L)
            sm = sum(Sm[j] for j in w)
            if sm < sum(Sa[j] for j in w) and sm < sum(Sb[j] for j in w):
                vinn += 1
            if L in T_KRIT and _t_sig(da[s:s + L], L) and _t_sig(db[s:s + L], L):
                sig += 1
            tot += 1
        ut[f"P{L}"] = vinn / tot
        ut[f"P{L}sig"] = sig / tot if L in T_KRIT else float("nan")
    return ut


def _t_sig(d: list[float], L: int) -> bool:
    m = sum(d) / L
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (L - 1))
    if sd == 0:
        return m > 0
    return m / (sd / math.sqrt(L)) > T_KRIT[L]


def lengste_like_strekk(verdier_per_uke: dict[int, set]) -> tuple[int, int]:
    """(lengde, start-wi) for lengste rekke uker der alle hadde én og samme
    verdi — og samme verdi uke til uke. S2."""
    best = (0, -1)
    run, start, forrige, forrige_i = 0, -1, None, None
    for i in sorted(verdier_per_uke):
        v = verdier_per_uke[i]
        if len(v) == 1 and v == forrige and run > 0 and forrige_i == i - 1:
            run += 1
        elif len(v) == 1:
            run, start = 1, i
        else:
            run, start = 0, -1
        forrige = v if len(v) == 1 else None
        forrige_i = i
        if run > best[0]:
            best = (run, start)
    return best


# ------------------------------------------------------------- kandidatene

def k_sesong(serie: pl.DataFrame, kol: str, siste_wi: int, gap: int,
             klipp: tuple[float | None, float | None],
             foran: int = 4) -> tuple[list[dict], dict]:
    """K1/K5/K6. Mål uke W, informasjon uke W-gap, utstedelse T = W-foran.
    Hovedvarselet: foran = 4, gap = 8. Nåvarselet: foran = 0, gap = 4."""
    nevner = "n_temp" if kol == "K5" else "n_lus"
    s = serie.filter(pl.col(kol).is_not_null() & (pl.col(nevner) >= MIN_NEVNER))
    y = {(po, w): v for po, w, v in s.select(["po", "wi", kol]).iter_rows()}

    # Klimatologi fra trening: mål-uker i [TRENING_FRA, TRENING_TIL].
    t0, t1 = wi(TRENING_FRA), wi(TRENING_TIL)
    sum_ = defaultdict(list)
    for (po, w), v in y.items():
        if t0 <= w <= t1:
            sum_[(po, isouke(w))].append(v)
    raa = {k: sum(v) / len(v) for k, v in sum_.items()}
    C = {}
    for po in PO_ER:
        for u in range(1, 53):
            vals = [raa.get((po, (u - 1 + k) % 52 + 1)) for k in range(-(GLATT // 2), GLATT // 2 + 1)]
            vals = [v for v in vals if v is not None]
            C[(po, u)] = sum(vals) / len(vals) if vals else None

    lo, hi = klipp
    rader = []
    for W in range(wi(TEST_FRA), siste_wi + 1):
        K = W - gap
        for po in PO_ER:
            yv = y.get((po, W))
            a = y.get((po, K))
            b = y.get((po, W - 52))
            cW, cK = C.get((po, isouke(W))), C.get((po, isouke(K)))
            m = None
            if a is not None and cW is not None and cK is not None:
                m = a + cW - cK
                if lo is not None:
                    m = max(lo, m)
                if hi is not None:
                    m = min(hi, m)
            rader.append({"i": W - foran, "po": po, "y": yv, "a": a, "b": b, "m": m})
    return rader, {"klima_celler": sum(1 for v in C.values() if v is not None)}


def blokksum(teller: dict[tuple[str, int], int], po: str, fra: int, til: int) -> int:
    return sum(teller.get((po, w), 0) for w in range(fra, til + 1))


def k_hasard(p: pl.DataFrame, siste_wi: int) -> tuple[list[dict], dict]:
    """K2: brakklegginger i T..T+3."""
    hend = hendelser(p, "brakklagt").filter(pl.col("po").is_in(PO_ER))
    teller: dict = defaultdict(int)
    starter_lok: dict[str, set] = defaultdict(set)
    for lok, po, w in hend.select(["lok", "po", "wi"]).iter_rows():
        teller[(po, w)] += 1
        starter_lok[lok].add(w)

    # Aktiv lengde per (lok, wi).
    q = (p.filter(pl.col("po").is_in(PO_ER))
         .select(["lok", "po", "wi", "brakklagt"]).sort(["lok", "wi"]))
    aktiv: dict[str, dict[int, tuple[int, bool]]] = {}
    lok_po = {}
    for lok, rows in q.group_by("lok", maintain_order=True):
        lok = lok[0]
        ws = rows["wi"].to_list()
        bs = rows["brakklagt"].to_list()
        lok_po[lok] = rows["po"][0]
        d: dict[int, tuple[int, bool]] = {}
        run, sensurert, forrige = 0, False, None
        for w, b in zip(ws, bs):
            er_aktiv = b == "False"
            if er_aktiv and forrige == w - 1 and run > 0:
                run += 1
            elif er_aktiv:
                run, sensurert = 1, (w == 0)
            else:
                run, sensurert = 0, False
            if er_aktiv:
                d[w] = (run, sensurert)
            forrige = w
        aktiv[lok] = d

    def botte(run: int, sens: bool) -> str:
        if sens:
            return "ukjent"
        for a, b in HASARD_BOTTER:
            if a <= run <= b:
                return f"{a}-{b if b < 10**9 else ''}"
        return "?"

    # Trening: K med K+4 >= TRENING_FRA og K+7 <= TRENING_TIL.
    t0, t1 = wi(TRENING_FRA), wi(TRENING_TIL)
    tall = defaultdict(lambda: [0, 0])
    for lok, d in aktiv.items():
        st = starter_lok.get(lok, set())
        for K, (run, sens) in d.items():
            if K + 4 >= t0 and K + 7 <= t1:
                c = tall[botte(run, sens)]
                c[1] += 1
                if any(K + k in st for k in range(4, 8)):
                    c[0] += 1
    h = {k: v[0] / v[1] for k, v in tall.items() if v[1]}

    # Indeks: lokaliteter aktive i uke K per PO.
    per_K: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for lok, d in aktiv.items():
        for K, (run, sens) in d.items():
            per_K[K].append((lok_po[lok], botte(run, sens)))

    rader = []
    for T in range(wi(TEST_FRA), siste_wi - 3 + 1):
        K = T - 4
        modell = defaultdict(float)
        for po, bt in per_K.get(K, []):
            modell[po] += h.get(bt, 0.0)
        for po in PO_ER:
            rader.append({"i": T, "po": po,
                          "y": blokksum(teller, po, T, T + 3),
                          "a": blokksum(teller, po, T - 7, T - 4),
                          "b": blokksum(teller, po, T - 52, T - 49),
                          "m": modell.get(po, 0.0)})
    return rader, {"hasard": {k: (round(v, 4), tall[k][1]) for k, v in sorted(h.items())},
                   "teller": teller}


def k_snitt52_uke(p: pl.DataFrame, felt: str, siste_wi: int) -> tuple[list[dict], dict]:
    """K7: nye PD i T..T+3; modell = antall i T-55..T-4 x 4/52."""
    hend = hendelser(p, felt).filter(pl.col("po").is_in(PO_ER))
    teller: dict = defaultdict(int)
    for po, w in hend.select(["po", "wi"]).iter_rows():
        teller[(po, w)] += 1
    rader = []
    for T in range(wi(TEST_FRA), siste_wi - 3 + 1):
        for po in PO_ER:
            rader.append({"i": T, "po": po,
                          "y": blokksum(teller, po, T, T + 3),
                          "a": blokksum(teller, po, T - 7, T - 4),
                          "b": blokksum(teller, po, T - 52, T - 49),
                          "m": blokksum(teller, po, T - 55, T - 4) * 4 / 52})
    return rader, {"teller": teller}


def k_utsett(data: dict) -> tuple[list[dict], dict]:
    """K3: utsett i måned M; informasjon til og med M-2."""
    bio = data["bio"].filter(pl.col("entity_id").is_in(PO_ER))
    u = {}
    for dato, po, v in bio.select(["dato", "entity_id", "utsett_smolt_antall"]).iter_rows():
        if v is None:
            continue
        u[(po, mi(dt.date.fromisoformat(dato)))] = float(v)
    # Andel per kalendermåned, 2018–2022.
    andel = defaultdict(list)
    for po in PO_ER:
        for aar in range(2018, 2023):
            ms = [aar * 12 + k for k in range(12)]
            if any((po, m) not in u for m in ms):
                continue
            tot = sum(u[(po, m)] for m in ms)
            if tot <= 0:
                continue
            for k, m in enumerate(ms):
                andel[(po, k)].append(u[(po, m)] / tot)
    s = {k: sum(v) / len(v) for k, v in andel.items()}

    siste = max(m for _, m in u)
    rader = []
    for M in range(mi(TEST_FRA), siste + 1):
        for po in PO_ER:
            t12 = [u.get((po, M - k)) for k in range(2, 14)]
            m = (sum(t12) * s[(po, M % 12)]
                 if None not in t12 and (po, M % 12) in s else None)
            rader.append({"i": M, "po": po, "y": u.get((po, M)),
                          "a": u.get((po, M - 2)), "b": u.get((po, M - 12)),
                          "m": m})
    return rader, {"u": u, "siste": siste,
                   "andeler": {k: round(v, 4) for k, v in sorted(s.items())}}


def k_eierskifte(data: dict, test_til: dt.date) -> tuple[list[dict], dict]:
    """K4: overføringer med journal_dato i T..T+27."""
    over = data["over"]
    dag = defaultdict(int)
    uten_po = defaultdict(int)
    med_po = defaultdict(int)
    alle_datoer = []
    for till, jd in over.select(["tillatelse_nr", "journal_dato"]).iter_rows():
        if not jd:
            continue
        d = dt.date.fromisoformat(str(jd)[:10])
        alle_datoer.append(d)
        po = data["till_po"].get(str(till))
        if po in PO_ER:
            dag[(po, d)] += 1
            med_po[d.year] += 1
        else:
            uten_po[d.year] += 1

    def sum_dager(po: str, fra: dt.date, til: dt.date) -> int:
        n, d = 0, fra
        while d <= til:
            n += dag.get((po, d), 0)
            d += dt.timedelta(days=1)
        return n

    rader = []
    T = TEST_FRA
    while T + dt.timedelta(days=27) <= test_til:
        i = wi(T)
        for po in PO_ER:
            rader.append({"i": i, "po": po,
                          "y": sum_dager(po, T, T + dt.timedelta(days=27)),
                          "a": sum_dager(po, T - dt.timedelta(days=28), T - dt.timedelta(days=1)),
                          "b": sum_dager(po, T - dt.timedelta(days=364), T - dt.timedelta(days=337)),
                          "m": sum_dager(po, T - dt.timedelta(days=364), T - dt.timedelta(days=1)) * 28 / 364})
        T += dt.timedelta(weeks=1)
    return rader, {"uten_po": dict(uten_po), "med_po": dict(med_po),
                   "forste": min(alle_datoer) if alle_datoer else None,
                   "siste": max(alle_datoer) if alle_datoer else None}


# ---------------------------------------------------------------- utskrift

def f(x, n=3) -> str:
    if x is None:
        return "–"
    if isinstance(x, float):
        if math.isnan(x):
            return "–"
        return f"{x:.{n}f}"
    return str(x)


def tabell(hode: list[str], rader: list[list]) -> list[str]:
    ut = ["| " + " | ".join(hode) + " |",
          "|" + "|".join("---" for _ in hode) + "|"]
    for r in rader:
        ut.append("| " + " | ".join(str(c) for c in r) + " |")
    return ut


def dom(r: dict, stopp: str | None) -> str:
    if stopp:
        return f"stoppet ({stopp})"
    if not r.get("n_rader"):
        return "ingen rader"
    if not (r["ss_a"] > 0 and r["ss_b"] > 0):
        return "slår ikke"
    if r["ss_a_lo"] > 0 and r["ss_b_lo"] > 0:
        return "slår referansen"
    return "uavklart"


def utforskende(rader_alle: dict) -> list[str]:
    """UTENFOR REGISTRERINGEN. Skrevet etter at testtallene var sett.

    MAE belønner medianen, og for sjeldne tellinger er medianen 0. Her er
    K2 og K7 skåret som «minst én hendelse i PO-en i vinduet», med Brier:
    modellen som sannsynlighet 1 - exp(-ŷ) (Poisson), referansene som 0/1.
    Teller ikke som ferdighet; det er et innspill til målvalget i økt 8.
    """
    ut = ["## Utforskende, utenfor registreringen", "",
          "Brier for «minst én hendelse» (modell 1 − e^−ŷ, referanser 0/1).", ""]
    rad = []
    for navn in ("K2", "K7"):
        rr = [r for r in rader_alle[navn] if None not in (r["y"], r["a"], r["b"], r["m"])]
        e = [1.0 if r["y"] >= 1 else 0.0 for r in rr]
        pm = [1 - math.exp(-r["m"]) for r in rr]
        pa = [1.0 if r["a"] >= 1 else 0.0 for r in rr]
        pb = [1.0 if r["b"] >= 1 else 0.0 for r in rr]
        bs = [sum((x - y) ** 2 for x, y in zip(pp, e)) / len(e) for pp in (pm, pa, pb)]
        rad.append([navn, len(e), f(sum(e) / len(e), 3), f(bs[0], 4), f(bs[1], 4),
                    f(bs[2], 4), f(1 - bs[0] / bs[1]), f(1 - bs[0] / bs[2])])
    ut += tabell(["kandidat", "rader", "andel med hendelse", "Brier modell", "Brier a",
                  "Brier b", "BSS a", "BSS b"], rad) + [""]
    return ut


def kontrolltall(data: dict, p: pl.DataFrame) -> list[str]:
    """Enkelttall fra navngitte filer, til MÅLT-påstandene i dokumentet."""
    sha = {(k, d, n): (sti, h) for k, d, n, sti, h, _ in data["filer"]}

    def fil(kilde: str, dato: str) -> str:
        treff = sorted((n, v) for (k, d, n), v in sha.items() if k == kilde and d == dato)
        return "; ".join(f"`{v[0]}` sha256 `{v[1]}`" for _, v in treff)

    ut = ["## Kontrollerbare tall", ""]
    w0 = 0
    n0 = p.filter((pl.col("wi") == w0) & pl.col("voksne_hunnlus").is_not_null()).height
    ut.append(f"T1 lusetall 2012-01-02: {n0} lokaliteter med `voksne_hunnlus`. "
              f"{fil('lusetall', '2012-01-02')}")
    w02 = wi(dt.date(2017, 4, 17))
    n02 = p.filter((pl.col("wi") == w02) & (pl.col("grense_h") == 20)).height
    n02_for = p.filter((pl.col("wi") == w02 - 1) & (pl.col("grense_h") == 20)).height
    ut.append(f"T2 sjotemperatur 2017-04-17: {n02} lokaliteter med `lusegrense` 0.2 "
              f"(uka før: {n02_for}). {fil('sjotemperatur', '2017-04-17')}")
    po_tall = defaultdict(int)
    for v in data["lok_po"].values():
        po_tall[v] += 1
    ut.append(f"T3 akvakultur {data['akv_dato']}: {len(data['lok_po'])} lokaliteter med "
              f"`prodomraade_kode`, {sum(po_tall[x] for x in PO_ER)} av dem i PO 1–13. "
              f"{fil('akvakultur', data['akv_dato'])}")
    ut.append("")
    # T4: K1-utfallet for siste uke, alle PO.
    W = int(p.filter(pl.col("voksne_hunnlus").is_not_null())["wi"].max())
    q = (p.filter((pl.col("wi") == W) & pl.col("po").is_in(PO_ER)
                  & (pl.col("lus_er_rapportert") == "True")
                  & pl.col("lus_h").is_not_null() & pl.col("grense_h").is_not_null())
         .group_by("po").agg((pl.col("lus_h") >= pl.col("grense_h")).sum().alias("over"),
                             pl.len().alias("n"))
         .sort(pl.col("po").cast(pl.Int64)))
    dato = str(uke_dato(W))
    ut.append(f"T4 K1-utfallet uke {dato} (over grensa / rapporterende med grense), "
              f"lusetall {fil('lusetall', dato)}; sjotemperatur {fil('sjotemperatur', dato)}:")
    ut.append("")
    ut += tabell(["PO", "over", "n"], [[po, o, n] for po, o, n in q.iter_rows()]) + [""]
    # T5: brakklegginger i samme uke, PO 1–13.
    h = hendelser(p, "brakklagt").filter(pl.col("po").is_in(PO_ER) & (pl.col("wi") == W))
    forrige = str(uke_dato(W - 1))
    ut.append(f"T5 brakklegginger uke {dato} (fra `brakklagt` False i {forrige} til True), "
              f"PO 1–13: {h.height}. lusetall {fil('lusetall', forrige)}")
    # T6: utsett siste måned.
    bio = data["bio"].filter(pl.col("entity_id").is_in(PO_ER))
    sist = bio["dato"].max()
    sumu = sum(float(v) for v in bio.filter(pl.col("dato") == sist)["utsett_smolt_antall"].to_list())
    ut.append(f"T6 biomasse {sist}: utsett_smolt_antall summert over PO 1–13 = {int(sumu)}. "
              f"{fil('biomasse', sist)}")
    # T7: tillatelser i historikken uten PO.
    nr = set(x for x in data["over"]["tillatelse_nr"].to_list() if x)
    uten = sum(1 for x in nr if x not in data["till_po"])
    ut.append(f"T7 eierskap_historikk (alle {sum(1 for r in data['filer'] if r[0] == 'eierskap_historikk')} "
              f"filer, se ut/filer.tsv): {len(nr)} ulike `tillatelse_nr`, {uten} finnes ikke "
              f"som tillatelse med `prodomraade_kode` i eierskap {data['eie_dato']} "
              f"({len(data['till_po'])} tillatelser). {fil('eierskap', data['eie_dato'])}")
    ut.append("")
    return ut


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mellomlager", type=Path, default=None)
    args = ap.parse_args()
    UT.mkdir(exist_ok=True)

    logg = kl.Kjoringslogg("anslag_backtest", UT / "anslag_backtest.kjoring.log")
    logg.valg("merke", MERKE)
    logg.valg("forhandsregistrering", "FORHANDSREGISTRERING.md, commit 85eed2c")
    logg.valg("trening", f"{TRENING_FRA}..{TRENING_TIL}")
    logg.valg("test_fra", TEST_FRA)

    if args.mellomlager and args.mellomlager.exists():
        with args.mellomlager.open("rb") as fh:
            data = pickle.load(fh)
        print(f"# panelene fra mellomlager {args.mellomlager} (lest gjennom "
              f"lesedøra i en tidligere kjøring; se kjøringsloggen der)")
    else:
        data = les_alt(logg)
        logg.skriv()
        if args.mellomlager:
            with args.mellomlager.open("wb") as fh:
                pickle.dump(data, fh)

    # Filmanifest.
    with (UT / "filer.tsv").open("w", encoding="utf-8") as fh:
        fh.write("kilde\tobserved_at\tversjon\tsti\tsha256\trader\n")
        for rad in data["filer"]:
            fh.write("\t".join(str(x) for x in rad) + "\n")

    p = lokalitetspanel(data)
    serie = po_ukeserie(p)
    siste_lus = int(p.filter(pl.col("voksne_hunnlus").is_not_null())["wi"].max())
    siste_sjo = int(p.filter(pl.col("sjotemperatur").is_not_null())["wi"].max())

    linjer: list[str] = [f"# {MERKE}", ""]

    # --------------------------------------------------- 2. dekning
    linjer += ["## Dekning (punkt 2)", ""]

    def forste(kol: str, vilkaar=None) -> str:
        q = p.filter(pl.col(kol).is_not_null())
        if vilkaar is not None:
            q = q.filter(vilkaar)
        return str(uke_dato(int(q["wi"].min()))) if q.height else "–"

    def siste(kol: str) -> str:
        q = p.filter(pl.col(kol).is_not_null())
        return str(uke_dato(int(q["wi"].max()))) if q.height else "–"

    uker_lus = p.filter(pl.col("voksne_hunnlus").is_not_null())["wi"].n_unique()
    dekn = [
        ["voksne_hunnlus", forste("voksne_hunnlus"), siste("voksne_hunnlus"), uker_lus],
        ["lusegrense", forste("lusegrense"), siste("lusegrense"),
         p.filter(pl.col("lusegrense").is_not_null())["wi"].n_unique()],
        ["lusegrense = 0.2", forste("lusegrense", pl.col("grense_h") == 20), "", ""],
        ["brakklagt", forste("brakklagt"), siste("brakklagt"),
         p.filter(pl.col("brakklagt").is_not_null())["wi"].n_unique()],
        ["har_pd", forste("har_pd"), siste("har_pd"),
         p.filter(pl.col("har_pd").is_not_null())["wi"].n_unique()],
        ["sjotemperatur", forste("sjotemperatur"), siste("sjotemperatur"),
         p.filter(pl.col("sjotemperatur").is_not_null())["wi"].n_unique()],
    ]
    linjer += tabell(["felt", "første uke", "siste uke", "uker"], dekn) + [""]

    # S1: PO-kobling.
    s1 = {}
    for navn, fra, til in (("trening", wi(TRENING_FRA), wi(TRENING_TIL)),
                           ("test", wi(TEST_FRA), siste_lus)):
        q = p.filter((pl.col("wi") >= fra) & (pl.col("wi") <= til)
                     & pl.col("voksne_hunnlus").is_not_null())
        # null i `po` må telles som «uten»: `is_in` på null gir null, og
        # filter() dropper null. Første kjøring talte derfor 0 (rettet før
        # MALING-dokumentet ble skrevet; skåringen var ikke berørt).
        uten = q.filter(~pl.col("po").is_in(PO_ER).fill_null(False)).height
        s1[navn] = (uten, q.height, uten / q.height if q.height else float("nan"))
    linjer += tabell(
        ["S1 lokalitetsuker med lusetall", "uten PO", "i alt", "andel"],
        [[k, v[0], v[1], f(v[2], 4)] for k, v in s1.items()]) + [""]
    s1_stopp_lok = s1["test"][2] > S1_GRENSE

    # S2: døde felt.
    def strekk(kol: str, transform=None, fra=wi(TRENING_FRA), til=None) -> tuple:
        til = til if til is not None else siste_lus
        q = (p.filter((pl.col("wi") >= fra) & (pl.col("wi") <= til)
                      & pl.col(kol).is_not_null() & pl.col("po").is_in(PO_ER)))
        if transform is not None:
            q = q.with_columns(transform.alias(kol))
        per = {w: set(v) for w, v in q.group_by("wi").agg(pl.col(kol).unique())
               .select(["wi", kol]).iter_rows()}
        n, s = lengste_like_strekk(per)
        return n, (str(uke_dato(s)) if s >= 0 else "–")

    over_uttr = (pl.when((pl.col("lus_er_rapportert") == "True")
                         & pl.col("lus_h").is_not_null() & pl.col("grense_h").is_not_null())
                 .then((pl.col("lus_h") >= pl.col("grense_h")).cast(pl.Utf8))
                 .otherwise(None))
    p = p.with_columns(over_uttr.alias("over"))
    s2 = {"K1 over grensa": strekk("over"),
          "K2 brakklagt": strekk("brakklagt"),
          "K5 sjotemperatur": strekk("sjotemperatur"),
          "K6 voksne_hunnlus": strekk("voksne_hunnlus"),
          "K7 har_pd": strekk("har_pd")}
    linjer += tabell(["S2 utfallsfelt (2017–)", "lengste uke-rekke der alle lokaliteter er like",
                      "fra"], [[k, v[0], v[1]] for k, v in s2.items()]) + [""]

    # S4: overføringshistorikken.
    hentet = data["over_hentet"]
    aar_naa = max(hentet)
    sist_hentet = max(h for h in hentet[aar_naa] if h)
    test_til_k4 = dt.date.fromisoformat(sist_hentet[:10]) - dt.timedelta(days=1)
    linjer += [f"S4: eierskap_historikk {aar_naa}: {len(hentet[aar_naa])} versjoner, "
               f"fetched_at {', '.join(sorted(h[:19] for h in hentet[aar_naa]))}. "
               f"K4-testen slutter med vinduer som ender senest {test_til_k4}.", ""]

    # S5.
    linjer += tabell(["S5 kilde", "entiteter lesedøra tok ut (sum over datoer)", "datoer lest"],
                     [[k, v[0], v[1]] for k, v in data["s5"].items()]) + [""]
    linjer += [f"Persontillegg: `eierskap` {data['eie_hook_tok']} entiteter i "
               f"{data['eie_dato']}; `eierskap_historikk` {data['over_hook_tok']} "
               f"(sum over filer).", ""]

    # --------------------------------------------------- kandidatene
    stopp: dict[str, str | None] = {}
    res: dict[str, dict] = {}
    ekstra: dict[str, dict] = {}
    rader_alle: dict[str, list[dict]] = {}

    def s2_stopp(nokkel: str) -> str | None:
        return "S2" if s2[nokkel][0] >= MAKS_STREKK else None

    def s1_s(navn: str) -> str | None:
        return "S1" if s1_stopp_lok else None

    k1, e1 = k_sesong(serie, "K1", siste_lus, 8, (0.0, 1.0))
    k1n, _ = k_sesong(serie, "K1", siste_lus, 4, (0.0, 1.0), foran=0)
    k5, e5 = k_sesong(serie, "K5", siste_sjo, 8, (None, None))
    k6, e6 = k_sesong(serie, "K6", siste_lus, 8, (0.0, None))
    k2, e2 = k_hasard(p, siste_lus)
    k7, e7 = k_snitt52_uke(p, "har_pd", siste_lus)
    k3, e3 = k_utsett(data)
    k4, e4 = k_eierskifte(data, test_til_k4)
    for navn, rader, blokk, st in (
            ("K1", k1, BOOT_BLOKK_UKE, s1_s("K1") or s2_stopp("K1 over grensa")),
            ("K1 nåvarsel", k1n, BOOT_BLOKK_UKE, s1_s("K1") or s2_stopp("K1 over grensa")),
            ("K2", k2, BOOT_BLOKK_UKE, s1_s("K2") or s2_stopp("K2 brakklagt")),
            ("K3", k3, BOOT_BLOKK_MND, None),
            ("K4", k4, BOOT_BLOKK_UKE, None),
            ("K5", k5, BOOT_BLOKK_UKE, s1_s("K5") or s2_stopp("K5 sjotemperatur")),
            ("K6", k6, BOOT_BLOKK_UKE, s1_s("K6") or s2_stopp("K6 voksne_hunnlus")),
            ("K7", k7, BOOT_BLOKK_UKE, s1_s("K7") or s2_stopp("K7 har_pd"))):
        vinduer = VINDUER + ((1,) if navn == "K3" else ())
        res[navn] = skaar(rader, blokk, vinduer)
        rader_alle[navn] = rader
        min_utst = S3_MND if navn == "K3" else S3_UKER
        if st is None and res[navn].get("n_utst", 0) < min_utst:
            st = "S3"
        stopp[navn] = st

    # S1 for K4: overføringer i testperioden uten PO.
    tp = [y for y in e4["uten_po"] if y >= TEST_FRA.year] + \
         [y for y in e4["med_po"] if y >= TEST_FRA.year]
    uten = sum(e4["uten_po"].get(y, 0) for y in set(tp))
    med = sum(e4["med_po"].get(y, 0) for y in set(tp))
    andel_k4 = uten / (uten + med) if (uten + med) else float("nan")
    if andel_k4 > S1_GRENSE:
        stopp["K4"] = "S1"
    linjer += [f"S1 for K4: {uten} av {uten + med} overføringer fra {TEST_FRA.year} "
               f"uten PO-kobling ({f(andel_k4, 4)}). Første journal_dato "
               f"{e4['forste']}, siste {e4['siste']}.", ""]

    # Utfall per uke per PO.
    linjer += ["### Utfall per PO i testperioden", ""]
    ut_rader = []
    for navn in ("K1", "K2", "K3", "K4", "K5", "K6", "K7"):
        rr = [r for r in rader_alle[navn] if r["y"] is not None]
        if not rr:
            ut_rader.append([navn, 0, "–", "–", "–"])
            continue
        per_utst = defaultdict(int)
        for r in rr:
            per_utst[r["i"]] += 1
        ys = [r["y"] for r in rr]
        null = sum(1 for y in ys if y == 0) / len(ys)
        ut_rader.append([navn, len(per_utst), f(len(rr) / len(per_utst), 1),
                         f(sum(ys) / len(ys), 3), f(null, 3)])
    linjer += tabell(["kandidat", "utstedelser med utfall", "PO med utfall per utstedelse",
                      "snitt utfall per PO", "andel PO-utfall = 0"], ut_rader) + [""]
    nl = serie.filter(pl.col("wi") >= wi(TEST_FRA))
    linjer += [f"Lokaliteter bak hver PO-andel (K1/K6) i test: median "
               f"{f(float(nl['n_lus'].median()), 0)}, min {nl['n_lus'].min()}; "
               f"K5: median {f(float(nl['n_temp'].median()), 0)}.", ""]

    # --------------------------------------------------- 3. resultat
    linjer += ["## Resultat (punkt 3)", ""]
    hode = ["kandidat", "utst.", "rader", "MAE modell", "MAE a", "MAE b",
            "SS a [95 %]", "SS b [95 %]", "P4", "P4sig", "P8", "P8sig",
            "P12", "P12sig", "dom"]
    rr = []
    for navn, r in res.items():
        if not r.get("n_rader"):
            rr.append([navn] + ["–"] * 13 + [dom(r, stopp[navn])])
            continue
        rr.append([navn, r["n_utst"], r["n_rader"], f(r["mae_m"], 4), f(r["mae_a"], 4),
                   f(r["mae_b"], 4),
                   f"{f(r['ss_a'])} [{f(r['ss_a_lo'])}, {f(r['ss_a_hi'])}]",
                   f"{f(r['ss_b'])} [{f(r['ss_b_lo'])}, {f(r['ss_b_hi'])}]",
                   f(r["P4"], 2), f(r["P4sig"], 2), f(r["P8"], 2), f(r["P8sig"], 2),
                   f(r["P12"], 2), f(r["P12sig"], 2), dom(r, stopp[navn])])
    linjer += tabell(hode, rr) + [""]
    linjer += [f"K3 per enkelt utstedelse (L = 1, ≈ fire uker, utenfor registreringen): "
               f"P1 = {f(res['K3'].get('P1'), 2)}.", ""]

    def periode(navn: str, r: dict) -> str:
        if not r.get("n_rader"):
            return "–"
        if navn == "K3":
            return f"{mnd_tekst(r['fra'])} … {mnd_tekst(r['til'])}"
        return f"{uke_dato(r['fra'])} … {uke_dato(r['til'])}"
    linjer += tabell(["kandidat", "utstedelser (T)"],
                     [[k, periode(k, v)] for k, v in res.items()]) + [""]

    # Per PO, for innsyn.
    per_po_rader = []
    for navn in res:
        if not res[navn].get("n_rader"):
            continue
        for po in PO_ER:
            rr2 = [r for r in rader_alle[navn] if r["po"] == po
                   and None not in (r["y"], r["a"], r["b"], r["m"])]
            if not rr2:
                continue
            em = sum(abs(r["y"] - r["m"]) for r in rr2) / len(rr2)
            ea = sum(abs(r["y"] - r["a"]) for r in rr2) / len(rr2)
            eb = sum(abs(r["y"] - r["b"]) for r in rr2) / len(rr2)
            per_po_rader.append([navn, po, len(rr2), f(em, 4), f(ea, 4), f(eb, 4),
                                 f(1 - em / ea if ea else float("nan")),
                                 f(1 - em / eb if eb else float("nan"))])
    with (UT / "per_po.tsv").open("w", encoding="utf-8") as fh:
        fh.write(f"# {MERKE}\n")
        fh.write("kandidat\tpo\trader\tmae_modell\tmae_a\tmae_b\tss_a\tss_b\n")
        for r in per_po_rader:
            fh.write("\t".join(str(x) for x in r) + "\n")
    po_slaar = defaultdict(int)
    for r in per_po_rader:
        try:
            if float(r[6]) > 0 and float(r[7]) > 0:
                po_slaar[r[0]] += 1
        except ValueError:
            pass
    linjer += ["PO der modellen slår begge referanser (av 13): " + ", ".join(
        f"{k} {po_slaar.get(k, 0)}" for k in res if res[k].get("n_rader")), ""]

    # Modellparametre som ble estimert på trening.
    linjer += ["### Estimert på trening", ""]
    linjer += ["K2 hasard per bøtte (andel, n): " + "; ".join(
        f"{k}: {v[0]} (n={v[1]})" for k, v in e2["hasard"].items()), ""]
    linjer += [f"K1/K5/K6 klimatologiceller med verdi: {e1['klima_celler']}, "
               f"{e5['klima_celler']}, {e6['klima_celler']} av {13 * 52}.", ""]

    # --------------------------------------------------- 4. anbefaling
    linjer += ["## Anbefaling etter registrert regel (punkt 4)", ""]
    avgjort_uker = {"K1": 8, "K1 nåvarsel": 4, "K2": 7, "K5": 8, "K6": 8, "K7": 7}
    mnd_etterslep = int(get("kilder.biomasse.maaneder_etterslep", 4))
    uke_etterslep = int(get("kilder.lusetall.uker_etterslep", 4))
    linjer += [f"Etterslep i config.yml: lusetall {uke_etterslep} uker, biomasse "
               f"{mnd_etterslep} måneder.", ""]
    # Måned M skrives første kjøring i M+4: fra 1. i M er det ~17 uker.
    avgjort_uker["K3"] = round(mnd_etterslep * 30.44 / 7)
    avgjort_uker["K4"] = None  # backfill, ikke ukentlig — se S4
    anb = []
    for navn, r in res.items():
        d = dom(r, stopp[navn])
        lag = avgjort_uker.get(navn)
        innen8 = lag is not None and lag <= 8
        anbefalt = (d == "slår referansen" and r.get("P4", 0) >= P4_GRENSE and innen8)
        anb.append((r.get("P4", float("nan")) if r.get("n_rader") else -1, navn, d, lag,
                    anbefalt, r))
    anb.sort(key=lambda x: (-(x[0] if not math.isnan(x[0]) else -1)))
    linjer += tabell(["kandidat", "dom", "P4", "P4sig", "avgjort etter (uker)",
                      "anbefalt", "skiller fra flaks på (uker)"],
                     [[n, d, f(r.get("P4"), 2), f(r.get("P4sig"), 2),
                       f(lag) if lag is not None else "ikke ukentlig",
                       "ja" if a else "nei",
                       ", ".join(str(L) for L in VINDUER
                                 if r.get(f"P{L}sig", 0) >= SIG_GRENSE) or "ingen"]
                      for _, n, d, lag, a, r in anb]) + [""]

    linjer += utforskende(rader_alle)
    linjer += kontrolltall(data, p)

    tekst = "\n".join(linjer)
    print(tekst)
    (UT / "utskrift.md").write_text(tekst + "\n", encoding="utf-8")
    with (UT / "resultat.tsv").open("w", encoding="utf-8") as fh:
        fh.write(f"# {MERKE}\n")
        nokler = ["n_utst", "n_rader", "mae_m", "mae_a", "mae_b", "ss_a", "ss_a_lo",
                  "ss_a_hi", "ss_b", "ss_b_lo", "ss_b_hi", "P4", "P4sig", "P8",
                  "P8sig", "P12", "P12sig"]
        fh.write("kandidat\t" + "\t".join(nokler) + "\tdom\n")
        for navn, r in res.items():
            fh.write(navn + "\t" + "\t".join(f(r.get(k), 6) for k in nokler)
                     + f"\t{dom(r, stopp[navn])}\n")


if __name__ == "__main__":
    main()
