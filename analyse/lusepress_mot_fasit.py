"""Første utforskning: skiller lusetallene ekspertgruppens kategorier?

    python analyse/lusepress_mot_fasit.py

Leser snapshots fra HAVBRUK_DATA_DIR, kobler mot fasiten i
analyse/fasit/ og skriver tall til stdout + plott til analyse/ut/.

Dette er utforskning. Ingen modell, ingen regresjon, ingen konklusjon
om at noe virker. Ingenting i core/ røres.

Avgrensning 2018-2026: rapporteringsdekningen steg fra 80,7 % (2012)
til 99,2 % (2026) og PO-dekningen fra 78,1 % til 95,6 %. En stigende
trend i et aggregat over hele serien kan være ren dekningsvekst.
Produksjonsområdene ble innført 2017, så PO-kartet er heller ikke
retroaktivt gyldig før det. Dekning per år rapporteres, slik at
avgrensningen kan etterprøves.
"""

from __future__ import annotations

import csv
import datetime as dt
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Snapshots leses gjennom `snapshot.les_mellom()`, ikke med
# `pl.read_parquet()` på en glob. Det er ikke en stilpreferanse:
# persondatafilteret ligger i `snapshot._les()`, og snapshotene fra
# 16.-17.08.2026 inneholder 34 enkeltpersonforetak hver som er
# append-only og blir stående. En analyse som globber selv, leser dem —
# og `test_ingen_leser_snapshots_utenom_les()` feller den for det.
from core import snapshot                # noqa: E402

FASIT = ROOT / "analyse" / "fasit" / "ekspertgruppen-po-kategori.csv"
UT = ROOT / "analyse" / "ut"

FRA_AAR, TIL_AAR = 2018, 2026
UTVANDRING = (16, 24)        # utgangspunkt
UTVANDRING_VID = (14, 26)    # følsomhetssjekk
KATEGORIER = ["lav", "moderat", "hoy"]
RANG = {"lav": 0, "moderat": 1, "hoy": 2}


# ---------------------------------------------------------------- innlesing

def les_fasit() -> dict[tuple[int, int], dict]:
    """(po, aar) -> rad. `ukjent` beholdes som rad; den er en opplysning."""
    ut = {}
    with FASIT.open(encoding="utf-8") as f:
        rader = csv.DictReader(r for r in f if not r.startswith("#"))
        for r in rader:
            ut[(int(r["po"]), int(r["aar"]))] = {
                "kategori": r["kategori"],
                "kilde": r["kilde"],
                "sikkerhet": r["sikkerhet"],
            }
    return ut


def po_kart() -> dict[str, int]:
    """localityNo -> produksjonsområde, fra nyeste akvakultursnapshot.

    ADVARSEL, og den gjelder hele analysen: dette er dagens PO-tilhørighet
    påført historiske uker. En lokalitet flytter seg ikke, så koden er
    stabil for lokaliteter som fortsatt finnes — men en lokalitet som ble
    slettet fra registeret før i dag har ingen kode i det hele tatt, og
    faller ut. Det er hele grunnen til at PO-dekning rapporteres per år.
    """
    siste = snapshot.siste_dato("akvakultur")
    if siste is None:
        raise SystemExit("fant ingen akvakultursnapshots")
    _, df = snapshot.les_mellom("akvakultur", siste, siste)[-1]
    par = df.filter(pl.col("field") == "prodomraade_kode").select("entity_id", "value")
    return {e: int(v) for e, v in par.iter_rows() if v not in (None, "")}


def les_uker() -> list[dict]:
    """Én rad per lokalitet-uke, for uker i [FRA_AAR, TIL_AAR]."""
    kart = po_kart()
    rader = []
    # Intervallet er kalenderdatoer, mens avgrensningen er ISO-år. De to
    # spriker rundt nyttår, så vinduet er med vilje en dag vidt i hver
    # ende og ISO-året sjekkes på nytt per fil under.
    for dato_tekst, df in snapshot.les_mellom(
            "lusetall", f"{FRA_AAR - 1}-12-01", f"{TIL_AAR + 1}-01-31"):
        iso = dt.date.fromisoformat(dato_tekst).isocalendar()
        if not (FRA_AAR <= iso.year <= TIL_AAR):
            continue
        bred = df.pivot(values="value", index="entity_id", on="field",
                        aggregate_function="first")
        for r in bred.iter_rows(named=True):
            lus = r.get("voksne_hunnlus")
            rader.append({
                "lok": r["entity_id"],
                "aar": iso.year,
                "uke": iso.week,
                "po": kart.get(r["entity_id"]),
                "brakklagt": r.get("brakklagt") == "True",
                "rapportert": r.get("lus_er_rapportert") == "True",
                "lus": float(lus) if lus not in (None, "") else None,
                "rensefisk": r.get("har_rensefisk") == "True",
                "mekanisk": r.get("har_mekanisk_fjerning") == "True",
                "medikament": r.get("har_medikamentell_behandling") == "True",
            })
    return rader


# ---------------------------------------------------------------- dekning

def dekning(rader: list[dict]) -> None:
    print(seksjon("1. DEKNING PER ÅR — grunnlaget for avgrensningen"))
    print(f"{'år':>5} {'lok-uker':>9} {'aktive':>8} {'rapp.':>8} {'rapp/aktiv':>11}"
          f" {'m/PO':>7} {'PO-dekn.':>9} {'uker':>5}")
    per_aar = defaultdict(list)
    for r in rader:
        per_aar[r["aar"]].append(r)
    for aar in sorted(per_aar):
        rs = per_aar[aar]
        aktive = [r for r in rs if not r["brakklagt"]]
        rapp = [r for r in aktive if r["rapportert"]]
        med_po = [r for r in rapp if r["po"] is not None]
        uker = len({r["uke"] for r in rs})
        print(f"{aar:>5} {len(rs):>9} {len(aktive):>8} {len(rapp):>8}"
              f" {len(rapp)/max(len(aktive),1):>10.1%}"
              f" {len(med_po):>7} {len(med_po)/max(len(rapp),1):>8.1%} {uker:>5}")
    print("\n  rapp/aktiv = andel ikke-brakklagte lokaliteter som rapporterte lus.")
    print("  PO-dekn.   = andel av de rapporterende som har en PO-kode i dagens")
    print("               akvakulturregister. Resten er lokaliteter som er slettet")
    print("               fra registeret siden, eller som aldri hadde PO (landbaserte).")
    print()
    print("  MERK: PO-dekningen for 2018 og 2019 er 90,3 % og 91,0 %, ikke over 92 %")
    print("  som avgrensningen antok. Tallet passerer 92 % først i 2021. Nevneren er")
    print("  sjekket: andel av AKTIVE gir 90,1 %, andel av ALLE lok-uker gir 51,0 %,")
    print("  og andel innen uke 16-24 gir 89,8 %. Ingen av dem gir 92 % for 2018.")
    print("  Avgrensningen står — 90 % er langt over 78 % i 2012, og forskjellen på")
    print("  90 og 92 er små i forhold til det avgrensningen skal beskytte mot — men")
    print("  premisset var ikke helt riktig, og da skal det stå at det ikke var det.")


# ---------------------------------------------------------------- prediktorer

def hvilke_inngangsdata(rader: list[dict]) -> None:
    print(seksjon("2. HVILKE AV EKSPERTGRUPPENS TRE INNGANGSDATA HAR VI?"))
    n_lus = sum(1 for r in rader if r["lus"] is not None)
    print(f"  antall lus     JA   — `voksne_hunnlus`, snitt voksne hunnlus per fisk")
    print(f"                        per lokalitet per uke. {n_lus} verdier 2018-2026.")
    print(f"  antall fisk    NEI  — finnes ikke i lusetall. Alle 19 feltene i")
    print(f"                        BarentsWatch-responsen er sjekket mot rå-arkivet:")
    print(f"                        ingen biomasse, ingen fiskeantall, ingen kapasitet.")
    print(f"  sjøtemperatur  NEI  — finnes ikke i ukeendepunktet. Det finnes et eget")
    print(f"                        endepunkt (.../seatemperature/{{år}}), men det er")
    print(f"                        per lokalitet per år og er ikke hentet.")
    print()
    print("  KONSEKVENS: smittepressproxyen fra Stien mfl. 2005")
    print("      nauplier = N_fisk × N_hunnlus × 0,17 × (T + 4,28)²")
    print("  bygges IKKE. To av tre innganger mangler, og en proxy bygget på")
    print("  én av tre er ikke den formelen — den er lusetallet med et navn")
    print("  som lover mer enn det holder.")
    print()
    print("  Akvakultursnapshotet har `kapasitet` (MTB i tonn) per lokalitet. Det er")
    print("  et TAK, ikke en beholdning: en lokalitet med 3600 tonn MTB kan stå tom.")
    print("  Lus × kapasitet ville vært lus × «hvor mye det er lov å ha der», og")
    print("  rangert lokaliteter etter tillatelse framfor etter fisk. Det er en")
    print("  annen størrelse enn ekspertgruppens, og den bygges ikke her.")


def per_po_aar(rader: list[dict], vindu: tuple[int, int]) -> dict:
    """(po, aar) -> prediktorer. Bare rapporterende lokaliteter med PO."""
    lav, hoy = vindu
    bøtte = defaultdict(lambda: defaultdict(list))   # (po,aar) -> uke -> [lus]
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not (lav <= r["uke"] <= hoy):
            continue
        bøtte[(r["po"], r["aar"])][r["uke"]].append(r["lus"])

    ut = {}
    for nøkkel, per_uke in bøtte.items():
        alle = [x for v in per_uke.values() for x in v]
        if not alle:
            continue
        ukesnitt = [st.mean(v) for v in per_uke.values() if v]
        ut[nøkkel] = {
            # Uvektet: hver uke teller likt, uansett hvor mange lokaliteter
            # som rapporterte den uka. Vektet: hver lokalitet-uke teller likt,
            # så uker med mange rapporterende drar mer.
            "snitt_uvektet": st.mean(ukesnitt),
            "snitt_vektet": st.mean(alle),
            "maks": max(alle),
            "p95": persentil(alle, 0.95),
            "median": st.median(alle),
            "n_lokuker": len(alle),
            "n_lok": len({0 for _ in alle}) if False else None,
            "n_uker": len(per_uke),
        }
    # antall unike rapporterende lokaliteter, som kontrollvariabel
    lok = defaultdict(set)
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not (lav <= r["uke"] <= hoy):
            continue
        lok[(r["po"], r["aar"])].add(r["lok"])
    for k in ut:
        ut[k]["n_lok"] = len(lok[k])
    return ut


def persentil(xs: list[float], p: float) -> float:
    """Lineær interpolasjon. Ingen numpy i dette repoet."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    i = p * (len(s) - 1)
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


# ---------------------------------------------------------------- utskrift

def seksjon(t: str) -> str:
    return f"\n{'=' * 74}\n {t}\n{'=' * 74}"


def tabell_prediktorer(pred: dict, fasit: dict, vindu: tuple[int, int]) -> None:
    print(seksjon(f"3. PREDIKTORER PER PO PER ÅR — uke {vindu[0]}-{vindu[1]}"))
    print(f"{'PO':>3} {'år':>5} {'kategori':>9} {'snitt_uv':>9} {'snitt_v':>8}"
          f" {'median':>7} {'p95':>6} {'maks':>6} {'n_lok':>6} {'n_uker':>7}")
    for (po, aar) in sorted(pred):
        p = pred[(po, aar)]
        kat = fasit.get((po, aar), {}).get("kategori", "—")
        print(f"{po:>3} {aar:>5} {kat:>9} {p['snitt_uvektet']:>9.3f}"
              f" {p['snitt_vektet']:>8.3f} {p['median']:>7.3f} {p['p95']:>6.2f}"
              f" {p['maks']:>6.2f} {p['n_lok']:>6} {p['n_uker']:>7}")


def fordeling_per_kategori(pred: dict, fasit: dict, vindu: tuple[int, int],
                           bare_verifisert: bool = False) -> None:
    tittel = "4. FORDELING PER KATEGORI — overlapper de?"
    if bare_verifisert:
        tittel = "4b. SAMME, UTEN 2024 (som er utledet, ikke lest)"
    print(seksjon(tittel + f"  [uke {vindu[0]}-{vindu[1]}]"))
    for navn in ["snitt_uvektet", "snitt_vektet", "p95", "maks", "n_lok"]:
        grupper = defaultdict(list)
        for (po, aar), p in pred.items():
            f = fasit.get((po, aar))
            if not f or f["kategori"] == "ukjent":
                continue
            if bare_verifisert and f["sikkerhet"] != "verifisert":
                continue
            grupper[f["kategori"]].append(p[navn])
        print(f"\n  {navn}")
        print(f"    {'kategori':>9} {'n':>3} {'min':>7} {'p25':>7} {'median':>7}"
              f" {'p75':>7} {'maks':>7}")
        for kat in KATEGORIER:
            v = grupper.get(kat, [])
            if not v:
                continue
            print(f"    {kat:>9} {len(v):>3} {min(v):>7.3f} {persentil(v,0.25):>7.3f}"
                  f" {st.median(v):>7.3f} {persentil(v,0.75):>7.3f} {max(v):>7.3f}")
        overlapp_dom(grupper)


def overlapp_dom(grupper: dict) -> None:
    """Overlapper lav og hoy i det hele tatt? Og er det ETT tall som skiller?"""
    lav, hoy = grupper.get("lav", []), grupper.get("hoy", [])
    if not lav or not hoy:
        return
    if max(lav) < min(hoy):
        print(f"    -> lav og hoy er ADSKILT (lav maks {max(lav):.3f} < "
              f"hoy min {min(hoy):.3f})")
    else:
        # hvor mange lav-verdier ligger over den laveste hoy-verdien
        n = sum(1 for x in lav if x >= min(hoy))
        print(f"    -> OVERLAPP: {n} av {len(lav)} lav-år ligger over laveste "
              f"hoy-år ({min(hoy):.3f}); lav maks {max(lav):.3f}")


def rangkorrelasjon(pred: dict, fasit: dict) -> None:
    """Spearman uten scipy: rangér begge, Pearson på rangene.

    Dette er en beskrivelse av samvariasjon, ikke en modell og ikke en
    test. Ingen p-verdi — 43 observasjoner over 13 områder er ikke
    uavhengige, og en p-verdi ville lovet mer enn tallet holder.
    """
    print(seksjon("5. SAMVARIASJON MED KATEGORIRANG (Spearman, beskrivende)"))
    for navn in ["snitt_uvektet", "snitt_vektet", "median", "p95", "maks", "n_lok"]:
        par = [(p[navn], RANG[fasit[(po, aar)]["kategori"]])
               for (po, aar), p in pred.items()
               if fasit.get((po, aar), {}).get("kategori") in RANG]
        if len(par) < 5:
            continue
        r = spearman([a for a, _ in par], [b for _, b in par])
        print(f"  {navn:>14}  rho = {r:+.3f}   (n = {len(par)})")


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(ranger(xs), ranger(ys))


def ranger(xs: list[float]) -> list[float]:
    par = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(par):
        j = i
        while j + 1 < len(par) and xs[par[j + 1]] == xs[par[i]]:
            j += 1
        snitt = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[par[k]] = snitt
        i = j + 1
    return r


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = st.mean(xs), st.mean(ys)
    tel = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    nev = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return tel / nev if nev else 0.0


def foelsomhet(p16: dict, p14: dict, fasit: dict) -> None:
    print(seksjon("6. FØLSOMHET FOR VINDUET — uke 16-24 mot 14-26"))
    print(f"{'PO':>3} {'år':>5} {'16-24':>8} {'14-26':>8} {'endring':>9}")
    diffs = []
    for k in sorted(p16):
        if k not in p14:
            continue
        a, b = p16[k]["snitt_uvektet"], p14[k]["snitt_uvektet"]
        diffs.append((b - a) / a if a else 0.0)
        if abs((b - a) / a if a else 0) > 0.15:
            print(f"{k[0]:>3} {k[1]:>5} {a:>8.3f} {b:>8.3f} {(b-a)/a:>+8.1%}")
    print(f"\n  {len(diffs)} PO-år sammenlignet. Median relativ endring: "
          f"{st.median(diffs):+.1%}. Rader over vises bare når endringen er "
          f"større enn 15 %.")
    r16 = [(k, p16[k]["snitt_uvektet"]) for k in sorted(p16) if k in p14]
    r14 = [(k, p14[k]["snitt_uvektet"]) for k in sorted(p16) if k in p14]
    print(f"  Spearman mellom de to vinduene: "
          f"{spearman([v for _, v in r16], [v for _, v in r14]):+.3f}")
    for navn, pr in [("16-24", p16), ("14-26", p14)]:
        par = [(p["snitt_uvektet"], RANG[fasit[k]["kategori"]])
               for k, p in pr.items() if fasit.get(k, {}).get("kategori") in RANG]
        print(f"  rho mot kategori, vindu {navn}: "
              f"{spearman([a for a,_ in par],[b for _,b in par]):+.3f} (n={len(par)})")


def spesifikke_sporsmaal(pred: dict, fasit: dict) -> None:
    print(seksjon("7. DE FIRE SPESIFIKKE SPØRSMÅLENE"))

    print("\n  a) PO3 og PO4 har aldri vært lav. Skiller de seg i tallene?")
    aldri_lav = {3, 4}
    a = [p["snitt_uvektet"] for (po, aar), p in pred.items() if po in aldri_lav]
    b = [p["snitt_uvektet"] for (po, aar), p in pred.items() if po not in aldri_lav]
    print(f"     PO3+PO4  n={len(a):>3}  median {st.median(a):.3f}  "
          f"spenn {min(a):.3f}-{max(a):.3f}")
    print(f"     øvrige   n={len(b):>3}  median {st.median(b):.3f}  "
          f"spenn {min(b):.3f}-{max(b):.3f}")
    print(f"     Andel av øvrige som ligger over PO3+PO4s median: "
          f"{sum(1 for x in b if x > st.median(a))/len(b):.1%}")

    print("\n  b) PO2 gikk hoy -> lav -> moderat i 2020-2022. Synlig i lusetallene?")
    print(f"     {'år':>5} {'kategori':>9} {'snitt_uv':>9} {'snitt_v':>8} {'p95':>6} {'n_lok':>6}")
    for aar in range(FRA_AAR, TIL_AAR + 1):
        p = pred.get((2, aar))
        if not p:
            continue
        kat = fasit.get((2, aar), {}).get("kategori", "—")
        print(f"     {aar:>5} {kat:>9} {p['snitt_uvektet']:>9.3f} "
              f"{p['snitt_vektet']:>8.3f} {p['p95']:>6.2f} {p['n_lok']:>6}")

    print("\n  c) Toårige mønstre (sonestyrt, toårig produksjon)?")
    print("     Korrelasjon mellom årets og fjorårets snitt (lag 1), og mot")
    print("     året før det (lag 2), per PO. Et toårig mønster gir negativ")
    print("     lag-1 og positiv lag-2.")
    print(f"     {'PO':>3} {'n_år':>5} {'lag1':>7} {'lag2':>7}")
    lag1_alle, lag2_alle = [], []
    for po in range(1, 14):
        serie = [(aar, pred[(po, aar)]["snitt_uvektet"])
                 for aar in range(FRA_AAR, TIL_AAR + 1) if (po, aar) in pred]
        if len(serie) < 5:
            continue
        v = [x for _, x in serie]
        l1 = pearson(v[:-1], v[1:]) if len(v) > 2 else float("nan")
        l2 = pearson(v[:-2], v[2:]) if len(v) > 3 else float("nan")
        lag1_alle.append(l1)
        lag2_alle.append(l2)
        print(f"     {po:>3} {len(v):>5} {l1:>+7.2f} {l2:>+7.2f}")
    print(f"     median lag1 {st.median(lag1_alle):+.2f}, "
          f"lag2 {st.median(lag2_alle):+.2f}")


def baseline(fasit: dict) -> None:
    print(seksjon("8. BASELINE — regelen enhver modell må slå"))
    par = []
    for (po, aar), f in fasit.items():
        forrige = fasit.get((po, aar - 1))
        if not forrige or f["kategori"] == "ukjent" or forrige["kategori"] == "ukjent":
            continue
        par.append((po, aar, forrige["kategori"], f["kategori"]))
    par.sort()
    n = len(par)
    lik = sum(1 for *_, a, b in par if a == b)
    lik_eller_opp = sum(1 for *_, a, b in par if RANG[b] - RANG[a] in (0, 1))
    print(f"  Sammenlignbare år-par (begge kjent): {n}")
    print(f"  «samme som i fjor»            : {lik:>3}/{n} = {lik/n:.1%}")
    print(f"  «samme som i fjor, eller ett hakk opp»: {lik_eller_opp:>3}/{n} = "
          f"{lik_eller_opp/n:.1%}")
    alltid = defaultdict(int)
    for *_, b in par:
        alltid[b] += 1
    for kat in KATEGORIER:
        print(f"  «alltid {kat}»{'':>{max(0,20-len(kat))}}: {alltid[kat]:>3}/{n} = "
              f"{alltid[kat]/n:.1%}")
    print("\n  Endringene som faktisk skjedde:")
    for po, aar, a, b in par:
        if a != b:
            print(f"    PO{po:<3} {aar-1}->{aar}  {a} -> {b}")


def retning_ved_skifte(pred: dict, fasit: dict) -> None:
    """De 11 gangene kategorien FAKTISK endret seg — beveget lusetallet seg
    samme vei? Dette er ikke en modell; det er å telle fortegn."""
    print(seksjon("8b. BEVEGET LUSETALLET SEG SAMME VEI SOM KATEGORIEN?"))
    print(f"{'PO':>4} {'skifte':>12} {'retning':>8} {'snitt_uv':>17} {'endring':>9} {'p95':>15} {'enig':>6}")
    enige = 0
    n = 0
    for (po, aar), f in sorted(fasit.items()):
        forrige = fasit.get((po, aar - 1))
        if not forrige or "ukjent" in (f["kategori"], forrige["kategori"]):
            continue
        if f["kategori"] == forrige["kategori"]:
            continue
        a, b = pred.get((po, aar - 1)), pred.get((po, aar))
        if not a or not b:
            continue
        n += 1
        opp = RANG[f["kategori"]] > RANG[forrige["kategori"]]
        d = b["snitt_uvektet"] - a["snitt_uvektet"]
        enig = (d > 0) == opp
        enige += enig
        print(f"{po:>4} {forrige['kategori'][:3]+'->'+f['kategori'][:3]:>12}"
              f" {'opp' if opp else 'ned':>8}"
              f" {a['snitt_uvektet']:>8.3f}->{b['snitt_uvektet']:<8.3f}"
              f" {d:>+9.3f} {a['p95']:>7.2f}->{b['p95']:<7.2f}"
              f" {'ja' if enig else 'NEI':>6}")
    print(f"\n  {enige} av {n} skifter har lusetallet på riktig side. "
          f"Myntkast gir {n/2:.1f}.")
    print("  Dette er ikke en test — 11 skifter, avhengige av hverandre innen PO.")
    print("  Det er tellingen av fortegn, og den står som den er.")


def uro(rader: list[dict], pred: dict) -> None:
    """Ting som ser rart ut. Like verdifullt som svaret."""
    print(seksjon("9. TING SOM SER RART UT"))

    # tomme PO-år
    manglende = [(po, aar) for po in range(1, 14)
                 for aar in range(FRA_AAR, TIL_AAR + 1) if (po, aar) not in pred]
    if manglende:
        print(f"  PO-år uten data i uke 16-24: {manglende}")

    # PO-år med svært få lokaliteter
    tynne = sorted(((p["n_lok"], po, aar) for (po, aar), p in pred.items()))[:8]
    print("\n  Tynneste PO-år (antall rapporterende lokaliteter i vinduet):")
    for n_lok, po, aar in tynne:
        print(f"    PO{po:<3} {aar}  n_lok={n_lok:<4} "
              f"snitt {pred[(po,aar)]['snitt_uvektet']:.3f}")

    # rapporterte lus uten rapporteringsflagg og omvendt
    a = sum(1 for r in rader if r["lus"] is not None and not r["rapportert"])
    b = sum(1 for r in rader if r["lus"] is None and r["rapportert"])
    print(f"\n  Lok-uker med lusetall, men lus_er_rapportert=False: {a}")
    print(f"  Lok-uker med lus_er_rapportert=True, men uten lusetall: {b}")

    # ekstremverdier
    ekstreme = sorted((r for r in rader if r["lus"] is not None),
                      key=lambda r: -r["lus"])[:5]
    print("\n  Høyeste enkeltmålinger 2018-2026:")
    for r in ekstreme:
        print(f"    lok {r['lok']:>7}  {r['aar']} uke {r['uke']:>2}  "
              f"PO{str(r['po']):<5} {r['lus']:.2f} voksne hunnlus")

    # 2026 er et delår
    n26 = sum(1 for r in rader if r["aar"] == 2026)
    uker26 = sorted({r["uke"] for r in rader if r["aar"] == 2026})
    print(f"\n  2026 er et DELÅR: uker {uker26[0]}-{uker26[-1]} "
          f"({len(uker26)} uker, {n26} lok-uker). Serien slutter uke "
          f"{uker26[-1]} fordi kilden henter med fire ukers etterslep.")

    # feltnormal-fellen fra CLAUDE.md 1b-4: kom feltet, eller sa det noe?
    print("\n  Kontroll av felt som «kom» men kanskje ikke «sa noe» (jf. F10):")
    for felt in ["rensefisk", "mekanisk", "medikament"]:
        pr_aar = defaultdict(lambda: [0, 0])
        for r in rader:
            pr_aar[r["aar"]][0] += 1
            pr_aar[r["aar"]][1] += 1 if r[felt] else 0
        andeler = " ".join(f"{aar}:{n/max(t,1):.1%}" for aar, (t, n) in sorted(pr_aar.items()))
        print(f"    {felt:<12} {andeler}")


# ---------------------------------------------------------------- plott

def plott(pred: dict, fasit: dict) -> Path:
    """To enkle plott som SVG i én HTML-fil. Ingen matplotlib i repoet,
    og en ny avhengighet er ikke verdt en utforskning."""
    UT.mkdir(exist_ok=True)
    farge = {"lav": "#2f7d32", "moderat": "#c98a00", "hoy": "#b3261e",
             "ukjent": "#bbbbbb"}

    # --- plott 1: snitt per PO-år, punkt farget etter kategori -----------
    punkter = [(po, aar, p["snitt_uvektet"],
                fasit.get((po, aar), {}).get("kategori", "ukjent"))
               for (po, aar), p in pred.items()]
    maks = max(v for *_, v, _ in punkter)
    B, H, MV, MH, MT, MB = 900, 380, 55, 20, 30, 55
    def x(po): return MV + (po - 0.5) * (B - MV - MH) / 13
    def y(v): return H - MB - (v / maks) * (H - MT - MB)

    s = [f'<svg viewBox="0 0 {B} {H}" width="100%" font-family="system-ui" font-size="11">']
    s.append(f'<text x="{MV}" y="18" font-size="13" font-weight="600">Snitt voksne '
             f'hunnlus per rapporterende lokalitet, uke 16-24 — farget etter '
             f'ekspertgruppens kategori</text>')
    for t in [0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        if t > maks: break
        s.append(f'<line x1="{MV}" y1="{y(t):.1f}" x2="{B-MH}" y2="{y(t):.1f}" '
                 f'stroke="#e5e5e5"/>')
        s.append(f'<text x="{MV-8}" y="{y(t)+4:.1f}" text-anchor="end" '
                 f'fill="#666">{t:.1f}</text>')
    s.append(f'<line x1="{MV}" y1="{y(0.5):.1f}" x2="{B-MH}" y2="{y(0.5):.1f}" '
             f'stroke="#b3261e" stroke-dasharray="4 3"/>'
             if 0.5 <= maks else '')
    for po in range(1, 14):
        s.append(f'<text x="{x(po):.1f}" y="{H-MB+18}" text-anchor="middle" '
                 f'fill="#333">PO{po}</text>')
    spenn = TIL_AAR - FRA_AAR
    for po, aar, v, kat in punkter:
        dx = ((aar - FRA_AAR) / spenn - 0.5) * ((B - MV - MH) / 13 - 12)
        s.append(f'<circle cx="{x(po)+dx:.1f}" cy="{y(v):.1f}" r="4" '
                 f'fill="{farge[kat]}" fill-opacity="0.85"><title>PO{po} {aar}: '
                 f'{v:.3f} ({kat})</title></circle>')
    s.append(f'<text x="{MV}" y="{H-8}" fill="#666">Hvert punkt er ett PO-år; '
             f'x-posisjon innen kolonnen går fra {FRA_AAR} (venstre) til '
             f'{TIL_AAR} (høyre). Grå = år uten fasit.</text>')
    s.append('</svg>')
    p1 = "".join(s)

    # --- plott 2: fordeling per kategori ---------------------------------
    grupper = defaultdict(list)
    for (po, aar), p in pred.items():
        f = fasit.get((po, aar))
        if f and f["kategori"] != "ukjent":
            grupper[f["kategori"]].append(p["snitt_uvektet"])
    B2, H2 = 900, 260
    m2 = max(x for v in grupper.values() for x in v)
    def x2(v): return 70 + (v / m2) * (B2 - 110)
    s = [f'<svg viewBox="0 0 {B2} {H2}" width="100%" font-family="system-ui" font-size="11">']
    s.append('<text x="70" y="18" font-size="13" font-weight="600">Fordeling av '
             'samme snitt, per kategori. Overlapper de?</text>')
    for i, kat in enumerate(KATEGORIER):
        v = sorted(grupper.get(kat, []))
        if not v:
            continue
        yy = 55 + i * 62
        s.append(f'<text x="62" y="{yy+4}" text-anchor="end" font-weight="600" '
                 f'fill="{farge[kat]}">{kat}</text>')
        s.append(f'<line x1="{x2(min(v)):.1f}" y1="{yy}" x2="{x2(max(v)):.1f}" '
                 f'y2="{yy}" stroke="{farge[kat]}" stroke-width="2" '
                 f'stroke-opacity="0.35"/>')
        s.append(f'<line x1="{x2(st.median(v)):.1f}" y1="{yy-12}" '
                 f'x2="{x2(st.median(v)):.1f}" y2="{yy+12}" '
                 f'stroke="{farge[kat]}" stroke-width="2"/>')
        for val in v:
            s.append(f'<circle cx="{x2(val):.1f}" cy="{yy}" r="4" '
                     f'fill="{farge[kat]}" fill-opacity="0.55"><title>{val:.3f}'
                     f'</title></circle>')
        s.append(f'<text x="{B2-30}" y="{yy+4}" text-anchor="end" fill="#666">'
                 f'n={len(v)}, median {st.median(v):.3f}</text>')
    for t in [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
        if t > m2: break
        s.append(f'<line x1="{x2(t):.1f}" y1="35" x2="{x2(t):.1f}" y2="{H2-40}" '
                 f'stroke="#eee"/>')
        s.append(f'<text x="{x2(t):.1f}" y="{H2-24}" text-anchor="middle" '
                 f'fill="#666">{t:.2f}</text>')
    s.append('</svg>')
    p2 = "".join(s)

    ut = UT / "lusepress.html"
    ut.write_text(
        "<meta charset='utf-8'><title>Lusepress mot ekspertgruppen</title>"
        "<style>body{font-family:system-ui;max-width:960px;margin:2rem auto;"
        "padding:0 1rem;color:#222}p{color:#555;line-height:1.5}</style>"
        "<h1>Lusepress mot ekspertgruppens kategorier</h1>"
        "<p>Utforskning, ikke modell. Snitt voksne hunnlus per rapporterende "
        f"lokalitet i utvandringsvinduet uke 16–24, {FRA_AAR}–{TIL_AAR}. "
        "Fasit for 2020–2024; øvrige år er grå fordi kategorien ikke er kjent.</p>"
        + p1 + p2, encoding="utf-8")
    return ut


# ---------------------------------------------------------------- hoved

def main() -> int:
    fasit = les_fasit()
    rader = les_uker()
    print(f"Leste {len(rader)} lokalitet-uker, {FRA_AAR}-{TIL_AAR}.")

    dekning(rader)
    hvilke_inngangsdata(rader)

    p16 = per_po_aar(rader, UTVANDRING)
    p14 = per_po_aar(rader, UTVANDRING_VID)

    tabell_prediktorer(p16, fasit, UTVANDRING)
    fordeling_per_kategori(p16, fasit, UTVANDRING)
    fordeling_per_kategori(p16, fasit, UTVANDRING, bare_verifisert=True)
    rangkorrelasjon(p16, fasit)
    foelsomhet(p16, p14, fasit)
    spesifikke_sporsmaal(p16, fasit)
    baseline(fasit)
    retning_ved_skifte(p16, fasit)
    uro(rader, p16)

    sti = plott(p16, fasit)
    print(seksjon("PLOTT"))
    print(f"  {sti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
