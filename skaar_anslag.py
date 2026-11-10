"""Skåreren for maskinanslagene: utfallet, fasiten.json og trefflista.

    python skaar_anslag.py                  # skriv fasiten.json og treffliste.md
    python skaar_anslag.py --torrkjor       # skriv til stdout, ikke til disk
    python skaar_anslag.py --oppgrader      # oppgrader ventende stempler først (nett)
    python skaar_anslag.py --prov-backtest  # regn R6s tall for K2 og K6 på nytt

Leser de forseglede ukefilene i `predictions/maskin/`, holder hver mot
stempelet, regner ut utfallet der dataene er kommet, og skriver

    predictions/maskin/fasiten.json    én rad per forseglet anslag
    predictions/maskin/treffliste.md   MAE per type mot begge referansene

Begge er en ren funksjon av ukefilene, `forseglinger.tsv`, stemplene og
snapshotene. Det står ikke noe tidspunkt fra kjøringen i dem, så en
kjøring uten noe nytt gir ingenting å committe.

## Hva som teller

Bare forseglede uker (FORHANDSREGISTRERING.md, «Hva som teller»): en
`.ots` ved siden av ukefila, summen i den lik sha256 av fila, og
stempelet ført i `forseglinger.tsv` før uka var omme. En ukefil som ikke
oppfyller det, står under `ikke_tellende` i fasiten.json med grunnen, og
ingen av radene dens teller.

## Utfallet

Regnes med R6s funksjoner, som anslaget: `hendelser()` for K2 og
`po_ukeserie()` for K6, med PO-koblingen ukefila oppgir. Det leses når
alle ukene det bygger på står i våre snapshots (K2: T−1 … T+3 i
`lusetall`; K6: T+4 i `lusetall` og `sjotemperatur`), med gjeldende
versjon. Før det er anslaget «åpent».

Skåren per rad er absolutt feil for modellen og for hver referanse.
Trefflista er R6s `skaar()` over de avgjorte radene, og dommen er R6s
`dom()` når minst 12 uker er avgjort (FORHANDSREGISTRERING.md,
«Lesemåte»). Før det står «for tidlig».

## Backtesten står adskilt

R6s tall for K2 og K6 står i `BACKTEST`, frosset fra
MALING-ANSLAG.md (havbruk-analyse 7d258f7, data 1f82890), og skrives i
en egen del av begge filene, merket BACKTEST. De telles aldri sammen med
de forseglede ukene. `--prov-backtest` regner dem ut på nytt med modulen
og sier om de fortsatt stemmer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl
import yaml

import anslag
import havbruksfond
import stempel
from analyse import kjoringslogg as kl
from core import snapshot

FASIT = anslag.MASKIN_DIR / "fasiten.json"
TREFFLISTE = anslag.MASKIN_DIR / "treffliste.md"
MIN_UKER_DOM = 12

BACKTEST = {
    "merke": "BACKTEST — teller ikke i trefflista",
    "kilde": ("R6, MALING-ANSLAG.md 09.11.2026 (havbruk-analyse 7d258f7, data "
              "havbruk-radar-data 1f82890). Hva modellen VILLE gjort i 2023–2026."),
    "typer": {
        "K2": {"klasse": "hovedtype", "utstedelser": "2023-01-02 … 2026-09-14",
               "n_utst": 194, "n_rader": 2522, "mae_m": 1.3066, "mae_a": 1.7958,
               "mae_b": 1.6475, "ss_a": 0.272, "ss_a_lo": 0.241, "ss_a_hi": 0.308,
               "ss_b": 0.207, "ss_b_lo": 0.162, "ss_b_hi": 0.258, "P4": 0.87,
               "dom": "slår referansen"},
        "K6": {"klasse": "PRØVETYPE", "utstedelser": "2022-12-05 … 2026-09-07",
               "n_utst": 197, "n_rader": 2300, "mae_m": 0.0502, "mae_a": 0.0670,
               "mae_b": 0.0620, "ss_a": 0.252, "ss_a_lo": 0.183, "ss_a_hi": 0.340,
               "ss_b": 0.190, "ss_b_lo": 0.064, "ss_b_hi": 0.299, "P4": 0.56,
               "dom": "slår referansen"},
    },
}
# Siste lusetalluke og PO-kobling i R6, for `--prov-backtest`.
BACKTEST_SISTE = "2026-10-05"
BACKTEST_KOBLING = "2026-11-02"


# ------------------------------------------------------------- ukefilene

def forseglinger() -> dict[str, dict]:
    """{filnavn: rad} fra forseglinger.tsv. Første linje per fil gjelder."""
    ut: dict[str, dict] = {}
    if not anslag.FORSEGLINGER.exists():
        return ut
    linjer = anslag.FORSEGLINGER.read_text(encoding="utf-8").splitlines()
    hode = linjer[0].split("\t")
    for linje in linjer[1:]:
        if linje.strip():
            rad = dict(zip(hode, linje.split("\t")))
            ut.setdefault(rad["fil"], rad)
    return ut


def ukefiler() -> list[tuple[dt.date, Path]]:
    return sorted((T, p) for p in anslag.MASKIN_DIR.glob("*.yml")
                  if (T := anslag.uke_fra_filnavn(p.name)) is not None)


def segl(T: dt.date, sti: Path, ført: dict[str, dict]) -> tuple[dict | None, str]:
    """(forseglingen, "") hvis uka teller, ellers (None, grunnen)."""
    ots = Path(f"{sti}.ots")
    if not ots.exists():
        return None, "ikke stemplet: ingen .ots"
    sha = anslag.sha256(sti)
    try:
        stemplet = havbruksfond.ots_sum(ots.read_bytes(), ots.name)
    except ValueError as e:
        return None, f"stempelet kan ikke leses: {e}"
    if stemplet != sha:
        return None, f"summen i {ots.name} er {stemplet}, ikke fila ({sha})"
    rad = ført.get(sti.name)
    if rad is None:
        return None, "stempelet er ikke ført i forseglinger.tsv"
    tid = dt.datetime.fromisoformat(rad["stemplet"].replace("Z", "+00:00"))
    if tid >= anslag.frist(T):
        return None, f"stemplet {rad['stemplet']}, etter fristen {anslag.frist(T).isoformat()}"
    komplett = ots.with_name(ots.name.removesuffix(".ots") + ".komplett.ots")
    return {"forseglet": rad["stemplet"], "sha256": sha,
            "stempel": anslag.vis(ots),
            "stempel_komplett": komplett.exists()}, ""


# --------------------------------------------------------------- utfallet

def utfallene(filer: list[tuple[dt.date, Path, dict]], logg: kl.Kjoringslogg) -> dict:
    """{(T, type, po): (y, grunn)} for alle anslag i de tellende filene.
    y er None når utfallet ikke er kjent; grunnen sier hvorfor.

    Panelet leses først når et utfall kan regnes ut. Rett etter at en uke
    er forseglet, står ingen uke etter T−4 i våre data, og da er det
    ingenting å lese."""
    lus_datoer = set(snapshot.datoer("lusetall"))
    sjo_datoer = set(snapshot.datoer("sjotemperatur"))
    ut: dict = {}
    if not filer:
        return ut
    fra = (min(T for T, _, _ in filer) - dt.timedelta(weeks=1)).isoformat()
    til = max(lus_datoer) if lus_datoer else fra
    lest: dict = {}
    paneler: dict[str, tuple] = {}

    def panel(kart: str) -> tuple:
        """(brakklegginger per (po, uke), K6 og nevner per (po, uke)) med
        PO-koblingen `kart`, regnet av R6s funksjoner."""
        if kart not in paneler:
            if not lest:
                lest.update(anslag.les_panel(logg, fra, til, kart))
                kobling = lest["lok_po"]
            else:
                akv = logg.les("akvakultur", kart, kart, versjonsvalg=kl.GJELDENDE)
                kobling = {str(k): str(v).strip() for k, v in
                           akv[-1][1].filter(pl.col("field") == "prodomraade_kode")
                           .select(["entity_id", "value"]).iter_rows()}
            p = anslag.r6.lokalitetspanel({"lus": lest["lus"], "sjo": lest["sjo"],
                                           "lok_po": kobling})
            teller: dict = defaultdict(int)
            for po, w in (anslag.r6.hendelser(p, "brakklagt")
                          .filter(pl.col("po").is_in(anslag.r6.PO_ER))
                          .select(["po", "wi"]).iter_rows()):
                teller[(po, w)] += 1
            k6 = {(po, w): (v, n) for po, w, v, n in anslag.r6.po_ukeserie(p)
                  .select(["po", "wi", "K6", "n_lus"]).iter_rows()}
            paneler[kart] = (teller, k6)
        return paneler[kart]

    for T, sti, innhold in filer:
        kart = str(innhold["po_kobling"]).removeprefix("akvakultur ").strip()
        t = anslag.r6.wi(T)
        mangler_k2 = [d for d in (T + dt.timedelta(weeks=k) for k in range(-1, 4))
                      if d.isoformat() not in lus_datoer]
        W = T + dt.timedelta(weeks=4)
        mangler_k6 = [f"{kilde} {W}" for kilde, s in (("lusetall", lus_datoer),
                                                      ("sjotemperatur", sjo_datoer))
                      if W.isoformat() not in s]
        for po in anslag.r6.PO_ER:
            if mangler_k2:
                ut[(T, "K2", po)] = (None, f"venter på lusetall {mangler_k2[0]}")
            else:
                ut[(T, "K2", po)] = (anslag.r6.blokksum(panel(kart)[0], po, t, t + 3), "")
            if mangler_k6:
                ut[(T, "K6", po)] = (None, f"venter på {mangler_k6[0]}")
                continue
            v, n = panel(kart)[1].get((po, t + 4), (None, None))
            if v is None or n is None or n < anslag.r6.MIN_NEVNER:
                ut[(T, "K6", po)] = (None, f"skåres ikke: {n or 0} lokaliteter i måluka, "
                                           f"færre enn {anslag.r6.MIN_NEVNER}")
            else:
                ut[(T, "K6", po)] = (v, "")
    return ut


# ------------------------------------------------------------- skåringen

def _r(x, n=anslag.DESIMALER):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(x, n) if isinstance(x, float) else x


def fasiten(data_til: str, tellende: list[tuple[dt.date, Path, dict, dict]],
            ikke_tellende: list[dict], utfall: dict) -> dict:
    rader = []
    for T, sti, innhold, s in tellende:
        for p in innhold["prediksjoner"]:
            type_, po = p["type"], str(p["entitet"]).removeprefix("PO")
            y, grunn = utfall.get((T, type_, po), (None, "ukjent"))
            # Avrundet før skåren, så hvert tall i fila kan regnes ut av fila.
            y = _r(y)
            m, a, b = p["anslag"], p["referanse_a"], p["referanse_b"]
            rad = {"id": p["id"], "type": type_, "klasse": p["klasse"], "po": po,
                   "uke": innhold["uke"], "fil": anslag.vis(sti),
                   **s, "aapningsdato": innhold["typer"][type_]["aapningsdato"],
                   "anslag": m, "referanse_a": a, "referanse_b": b}
            if None in (m, a, b):
                rad.update(status="skåres ikke", grunn=p.get("merknad") or
                           "anslaget eller en referanse mangler", utfall=y, skaar=None)
            elif y is None:
                apen = grunn.startswith("venter")
                rad.update(status="åpen" if apen else "skåres ikke", grunn=grunn,
                           utfall=None, skaar=None)
            else:
                fm, fa, fb = abs(y - m), abs(y - a), abs(y - b)
                rad.update(status="avgjort", utfall=y,
                           skaar={"feil_modell": _r(fm), "feil_a": _r(fa),
                                  "feil_b": _r(fb), "slo_begge": fm < fa and fm < fb})
            rader.append(rad)

    treff = {}
    for type_, meta in anslag.TYPER.items():
        mine = [r for r in rader if r["type"] == type_]
        avgjort = [r for r in mine if r["status"] == "avgjort"]
        res = anslag.r6.skaar([{"i": anslag.r6.wi(anslag.fra_isouke(r["uke"])),
                                "po": r["po"], "y": r["utfall"], "a": r["referanse_a"],
                                "b": r["referanse_b"], "m": r["anslag"]} for r in avgjort],
                              anslag.r6.BOOT_BLOKK_UKE)
        n_utst = res.get("n_utst", 0)
        dom = (anslag.r6.dom(res, None) if n_utst >= MIN_UKER_DOM
               else f"for tidlig: {n_utst} av {MIN_UKER_DOM} uker avgjort")
        treff[type_] = {
            "klasse": meta["klasse"],
            "forseglede_uker": len({r["uke"] for r in mine}),
            "avgjorte_uker": n_utst, "avgjorte_rader": res.get("n_rader", 0),
            **{k: _r(res.get(k), 4) for k in ("mae_m", "mae_a", "mae_b", "ss_a", "ss_a_lo",
                                             "ss_a_hi", "ss_b", "ss_b_lo", "ss_b_hi")},
            "dom": dom,
        }
    return {
        "merke": ("Forseglede maskinanslag per produksjonsområde. Bare forseglede "
                  "uker teller. K6 er en PRØVETYPE."),
        "registrering": "predictions/maskin/FORHANDSREGISTRERING.md",
        "data_til": data_til,
        "anslag": rader,
        "treffliste": treff,
        "ikke_tellende": ikke_tellende,
        "backtest": BACKTEST,
    }


# ------------------------------------------------------------ trefflista

def _f(x, n=4) -> str:
    return "–" if x is None else (f"{x:.{n}f}" if isinstance(x, float) else str(x))


def _tabell(hode: list[str], rader: list[list]) -> list[str]:
    return (["| " + " | ".join(hode) + " |", "|" + "|".join("---" for _ in hode) + "|"]
            + ["| " + " | ".join(str(c) for c in r) + " |" for r in rader])


def treffliste(f: dict) -> str:
    L = ["# Trefflista for maskinanslagene", "",
         "Bare forseglede uker teller. Backtesten står nederst, adskilt og merket",
         "BACKTEST, og telles ikke. Hva som er registrert, står i",
         "`FORHANDSREGISTRERING.md`; hver rad står i `fasiten.json`.", "",
         (f"Lusetall til og med uke {anslag.isouke(dt.date.fromisoformat(f['data_til']))} "
          f"({f['data_til']})." if f["data_til"] else "Ingen lusetall i datarepoet."), ""]
    navn = {"K2": "K2, brakklegginger de neste fire ukene — hovedtype",
            "K6": "K6, snitt voksne hunnlus om fire uker — PRØVETYPE"}
    for type_, t in f["treffliste"].items():
        L += [f"## {navn[type_]}", ""]
        if type_ == "K6":
            L += ["Prøvetype: forseglet og skåret som K2, men ikke et hovedresultat.", ""]
        L += _tabell(["forseglede uker", "avgjorte uker", "avgjorte rader", "MAE modell",
                      "MAE a (siste verdi)", "MAE b (i fjor)", "SS a", "SS b", "dom"],
                     [[t["forseglede_uker"], t["avgjorte_uker"], t["avgjorte_rader"],
                       _f(t["mae_m"]), _f(t["mae_a"]), _f(t["mae_b"]), _f(t["ss_a"], 3),
                       _f(t["ss_b"], 3), t["dom"]]]) + [""]
        per_uke = defaultdict(list)
        for r in f["anslag"]:
            if r["type"] == type_:
                per_uke[r["uke"]].append(r)
        rader = []
        for uke, rr in sorted(per_uke.items()):
            av = [r for r in rr if r["status"] == "avgjort"]

            def snitt(k: str) -> str:
                return _f(sum(r["skaar"][k] for r in av) / len(av)) if av else "–"
            status = (f"{len(av)} avgjort" if av else
                      "åpen" if any(r["status"] == "åpen" for r in rr) else "skåres ikke")
            rader.append([uke, rr[0]["forseglet"], rr[0]["aapningsdato"], status,
                          snitt("feil_modell"), snitt("feil_a"), snitt("feil_b")])
        L += _tabell(["uke", "forseglet (UTC)", "åpningsdato", "rader", "MAE modell",
                      "MAE a", "MAE b"], rader) + [""]
    if f["ikke_tellende"]:
        L += ["## Ukefiler som ikke teller", ""]
        L += _tabell(["fil", "grunn"], [[x["fil"], x["grunn"]] for x in f["ikke_tellende"]])
        L += [""]
    b = f["backtest"]
    L += [f"## {b['merke']}", "", b["kilde"], ""]
    L += _tabell(["type", "utstedelser", "rader", "MAE modell", "MAE a", "MAE b",
                  "SS a [95 %]", "SS b [95 %]", "P4", "dom"],
                 [[f"{k} ({v['klasse']})", f"{v['utstedelser']} ({v['n_utst']})", v["n_rader"],
                   _f(v["mae_m"]), _f(v["mae_a"]), _f(v["mae_b"]),
                   f"{_f(v['ss_a'], 3)} [{_f(v['ss_a_lo'], 3)}, {_f(v['ss_a_hi'], 3)}]",
                   f"{_f(v['ss_b'], 3)} [{_f(v['ss_b_lo'], 3)}, {_f(v['ss_b_hi'], 3)}]",
                   _f(v["P4"], 2), v["dom"]] for k, v in b["typer"].items()])
    return "\n".join(L) + "\n"


# ------------------------------------------------------------ backtesten

def prov_backtest(logg: kl.Kjoringslogg) -> int:
    """R6s tall for K2 og K6, regnet på nytt med modulen over R6s periode."""
    m6 = anslag.modulen()
    data = anslag.les_panel(logg, anslag.FORSTE, BACKTEST_SISTE, BACKTEST_KOBLING)
    p = m6.lokalitetspanel(data)
    serie = m6.po_ukeserie(p)
    siste = m6.wi(dt.date.fromisoformat(BACKTEST_SISTE))
    rader = {"K2": m6.k_hasard(p, siste)[0],
             "K6": m6.k_sesong(serie, "K6", siste, 8, (0.0, None))[0]}
    feil = 0
    for type_, frosset in BACKTEST["typer"].items():
        res = m6.skaar(rader[type_], m6.BOOT_BLOKK_UKE)
        for k in ("n_utst", "n_rader", "mae_m", "mae_a", "mae_b", "ss_a", "ss_a_lo",
                  "ss_a_hi", "ss_b", "ss_b_lo", "ss_b_hi", "P4"):
            n = 4 if k.startswith("mae") else 3 if k.startswith("ss") else 2
            naa = round(res[k], n) if isinstance(res[k], float) else res[k]
            lik = naa == frosset[k]
            feil += not lik
            print(f"  {type_} {k:8} frosset {frosset[k]!s:>8}  nå {naa!s:>8}  "
                  f"{'likt' if lik else 'AVVIK'}")
    print("Backtesten stemmer." if not feil else f"{feil} avvik fra den frosne backtesten.")
    return 0 if not feil else 1


# -------------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--torrkjor", action="store_true")
    ap.add_argument("--oppgrader", action="store_true",
                    help="oppgrader ventende .ots til .komplett.ots først (nett)")
    ap.add_argument("--prov-backtest", action="store_true")
    a = ap.parse_args(argv)
    anslag.modulen()
    logg = kl.Kjoringslogg("skaar_anslag", anslag.MASKIN_DIR / "skaar_anslag.kjoring.log")
    if a.prov_backtest:
        return prov_backtest(logg)

    if a.oppgrader:
        for ots in sorted(anslag.MASKIN_DIR.glob("*.ots")):
            if ots.name.endswith(".komplett.ots"):
                continue
            if ots.with_name(ots.name.removesuffix(".ots") + ".komplett.ots").exists():
                continue
            utfall = stempel.oppgrader(ots)
            print(f"  {'komplett' if utfall else 'venter  ' if utfall is False else 'ukjent  '}"
                  f"  {ots.name}")

    ført = forseglinger()
    tellende, ikke_tellende = [], []
    for T, sti in ukefiler():
        s, grunn = segl(T, sti, ført)
        if s is None:
            ikke_tellende.append({"fil": anslag.vis(sti), "grunn": grunn})
            print(f"::warning::{sti.name} teller ikke: {grunn}")
            continue
        innhold = yaml.safe_load(sti.read_text(encoding="utf-8"))
        tellende.append((T, sti, innhold, s))

    utfall = utfallene([(T, sti, innhold) for T, sti, innhold, _ in tellende], logg)
    lus = snapshot.datoer("lusetall")
    f = fasiten(lus[-1] if lus else "", tellende, ikke_tellende, utfall)
    tekst_json = json.dumps(f, ensure_ascii=False, indent=1) + "\n"
    tekst_md = treffliste(f)
    for type_, t in f["treffliste"].items():
        print(f"  {type_} ({t['klasse']}): {t['forseglede_uker']} forseglede uker, "
              f"{t['avgjorte_uker']} avgjort, MAE {_f(t['mae_m'])} / {_f(t['mae_a'])} / "
              f"{_f(t['mae_b'])}, {t['dom']}")
    if a.torrkjor:
        print(tekst_json, end="")
        print(tekst_md, end="")
        return 0
    for sti, tekst in ((FASIT, tekst_json), (TREFFLISTE, tekst_md)):
        if sti.exists() and sti.read_text(encoding="utf-8") == tekst:
            print(f"  {sti.name} uendret")
            continue
        sti.write_text(tekst, encoding="utf-8")
        print(f"  skrevet {anslag.vis(sti)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
