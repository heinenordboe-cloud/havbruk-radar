"""A3: andelene fra A2 holdt mot fordelingen 2025.

    .venv/bin/python analyse/havbruksfond/a3_kontroll_2025.py

To kropper for 2025, og de skal si det samme:

  * pressemeldingen 10.11.2025 (`regjeringen-pressemeldinger/2025-11-10`),
    tabellen «Utbetalinger fra Havbruksfondet 2025», KOMMUNE og TOTALT
  * Fiskeridirektoratets regneark «Utbetalinger fra Havbruksfondet 2025»
    (`havbruksfondet/`), som i tillegg deler TOTALT i ANDEL NYKLARERT og
    ORDINÆR UTBETALING, og lister hver lokalitet med kapasitet per
    01.09.2025

Første kontroll er at de to er enige. Deretter sammenlignes andelene fra
A2 (31.08.2026) med 2025.

2025 er et ODDETALLSÅR: 763 165 711 kr av kommunenes 1 127 938 400 gikk
etter NY klarert MTB, ikke etter stående. TOTALT-andelen 2025 er derfor
ikke den samme størrelsen som en andel av stående MTB, og avviket mellom
dem er målbart kommune for kommune. Det er første forklaring som prøves.
Den andre er lokalitetene: Fiskeridirektoratets liste per 01.09.2025 mot
vårt utvalg per 31.08.2026, lokalitet for lokalitet. Det som står igjen
etter begge, er «uforklart».

Dette er en rimelighetskontroll, ikke en fasit.
"""
from __future__ import annotations

import gzip
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import a2_andeler as a2  # noqa: E402
import felles as f  # noqa: E402
from arkiver_vilkar import synlig_tekst  # noqa: E402

PM = f.D / "arkiv" / "regjeringen-pressemeldinger"


def pressemelding_2025() -> tuple[dict[str, int], dict[str, int], dict]:
    """(kommune -> kr, fylke -> kr, meta) fra pressemeldingen 10.11.2025."""
    for sti in sorted(PM.glob("2025-11-10*.gz")):
        raw = gzip.open(sti, "rb").read()
        t = synlig_tekst(raw)
        if "KOMMUNE TOTALT" in t:
            break
    else:
        raise FileNotFoundError("pressemeldingen 10.11.2025 er ikke arkivert")
    kom_t = t[t.index("KOMMUNE TOTALT") + len("KOMMUNE TOTALT"):
              t.index("Fylkeskommune Utbetaling")]
    fyl_t = t[t.index("Fylkeskommune Utbetaling") + len("Fylkeskommune Utbetaling"):
              t.index("Totalt:")]
    # «ALSTAHAUG 10 903 781 ALTA 22 011 944 …»: et navn er alt fram til
    # første siffer, et beløp er sifre i tregrupper.
    par = re.compile(r"\s*(\D+?)\s+(\d{1,3}(?: \d{3})*)(?=\s+\D|\s*$)")
    kom = {n.strip(): int(b.replace(" ", "")) for n, b in par.findall(kom_t)}
    fyl = {n.strip(): int(b.replace(" ", "")) for n, b in par.findall(fyl_t)}
    tot = int(re.search(r"Totalt:\s*([\d ]+?)\s*kroner", t).group(1)
              .replace(" ", ""))
    return kom, fyl, {"sti": str(sti.relative_to(f.D.parent)),
                      "sha256": hashlib.sha256(raw).hexdigest(), "totalt": tot}


def regneark_2025() -> tuple[dict, dict]:
    ark, meta = f.fdir_regneark(2025)
    ut = {}
    for r in ark["Utbetalingsoversikt"][2:]:
        if r and r[0].isdigit():
            ny = float(r[2] or 0)
            ut[r[0]] = {"navn": r[1], "ny": ny, "ordinar": float(r[3]),
                        "totalt": float(r[4])}
    lok = {}
    for r in ark["Lok. per. 01.09.25"][2:]:
        if r and r[0].isdigit():
            lok.setdefault(r[0], []).append((r[2], float(r[4]) * float(r[5])))
    return ut, {"meta": meta, "lok": lok}


def _t(x: float, fortegn: str = "") -> str:
    """Hele tall med mellomrom som tusenskille."""
    return f"{x:{fortegn},.0f}".replace(",", " ")


def spearman(x: list[float], y: list[float]) -> float:
    def rang(v):
        orden = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[orden[j + 1]] == v[orden[i]]:
                j += 1
            for k in range(i, j + 1):
                r[orden[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rang(x), rang(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return sxy / (sxx * syy) ** 0.5


def main() -> None:
    pm_kom, pm_fyl, pm_meta = pressemelding_2025()
    rk, rk_ekstra = regneark_2025()
    a = a2.beregn(a2.FOR)
    vaar = dict(a["kom"].select(["kommunenummer", "andel"]).iter_rows())
    vaar_mtb = dict(a["kom"].select(["kommunenummer", "mtb"]).iter_rows())

    print("## Kroppene\n")
    print(f"- pressemelding: `{pm_meta['sti']}`, sha256 `{pm_meta['sha256']}`")
    print(f"- regneark: `{rk_ekstra['meta']['sti']}`, sha256 "
          f"`{rk_ekstra['meta']['sha256']}`\n")

    # ── er de to 2025-kroppene enige? ────────────────────────────────
    navn2nr = {v["navn"]: k for k, v in rk.items()}
    uten = sorted(set(pm_kom) - set(navn2nr))
    avvik = [(n, pm_kom[n], rk[navn2nr[n]]["totalt"]) for n in pm_kom
             if n in navn2nr and abs(pm_kom[n] - rk[navn2nr[n]]["totalt"]) >= 1]
    print("## Pressemeldingen mot regnearket\n")
    print(f"- kommuner i pressemeldingen: {len(pm_kom)}, i regnearket: {len(rk)}")
    print(f"- navn i pressemeldingen uten treff i regnearket: {uten}")
    print(f"- kommuner der beløpet avviker med 1 kr eller mer: {len(avvik)}"
          + "".join(f"\n  - {n}: {p} mot {r:.2f}" for n, p, r in avvik))
    print(f"- sum kommuner {sum(pm_kom.values()):,} + fylker "
          f"{sum(pm_fyl.values()):,} = "
          f"{sum(pm_kom.values()) + sum(pm_fyl.values()):,} (avrunding); "
          f"«Totalt:» {pm_meta['totalt']:,}".replace(",", " "))

    tot25 = sum(pm_kom.values())
    tot25_ord = sum(v["ordinar"] for v in rk.values())
    a25 = {navn2nr[n]: b / tot25 for n, b in pm_kom.items()}
    a25o = {k: v["ordinar"] / tot25_ord for k, v in rk.items()}

    alle = sorted(set(a25) | set(vaar))
    rho = spearman([a25.get(k, 0) for k in alle], [vaar.get(k, 0) for k in alle])
    felles_ = sorted(set(a25) & set(vaar))
    rho_f = spearman([a25[k] for k in felles_], [vaar[k] for k in felles_])
    rho_o = spearman([a25o.get(k, 0) for k in alle], [vaar.get(k, 0) for k in alle])
    print("\n## Rangkorrelasjon (Spearman)\n")
    print(f"- A2 31.08.2026 mot TOTALT 2025, {len(alle)} kommuner "
          f"(mangler = 0): **ρ = {rho:.4f}**")
    print(f"- samme, bare de {len(felles_)} som finnes i begge: ρ = {rho_f:.4f}")
    print(f"- A2 mot ORDINÆR 2025 (uten nyklarert-delen), {len(alle)} kommuner: "
          f"ρ = {rho_o:.4f}")
    print(f"- bare i 2025: {sorted(set(a25) - set(vaar))}")
    print(f"- bare i 2026: {sorted(set(vaar) - set(a25))}")

    navn = {**{k: v["navn"].title() for k, v in rk.items()},
            **dict(a["kom"].select(["kommunenummer", "kommune"]).iter_rows())}

    print("\n## De 20 største\n")
    print("| # 2025 | kommune | andel 2025 TOTALT | andel 2026 (A2) | # 2026 |")
    print("|---|---|---|---|---|")
    r26 = {k: i for i, k in enumerate(sorted(vaar, key=lambda k: -vaar[k]), 1)}
    for i, k in enumerate(sorted(a25, key=lambda k: -a25[k])[:20], 1):
        print(f"| {i} | {navn[k]} | {a25[k]:.3%} | {vaar.get(k, 0):.3%} | "
              f"{r26.get(k, '–')} |")

    # ── avvikene, og hva som forklarer dem ───────────────────────────
    # Lokalitetene per kommune: Fiskeridirektoratet 01.09.2025 mot oss.
    fd_lok: dict[str, dict[str, float]] = {}
    for e, deler in rk_ekstra["lok"].items():
        for k, mtb in deler:
            fd_lok.setdefault(k, {})[e] = mtb
    vaar_lok: dict[str, dict[str, float]] = {}
    for e, k, kap in a["med"].select(
            ["entity_id", "kommunenummer", "mtb"]).iter_rows():
        for kk, andel in (a["delte"].get(e) or [(k, 1.0)]):
            vaar_lok.setdefault(kk, {})[e] = kap * andel

    print("\n## De 10 største avvikene (prosentpoeng, A2 minus TOTALT 2025)\n")
    print("| kommune | 2025 TOTALT | 2026 A2 | avvik | av det: nyklarert 2025 "
          "| av det: stående MTB | forklaring |")
    print("|---|---|---|---|---|---|---|")
    topp = sorted(alle, key=lambda k: -abs(vaar.get(k, 0) - a25.get(k, 0)))[:10]
    detaljer = []
    for k in topp:
        d = vaar.get(k, 0) - a25.get(k, 0)
        bonus = a25o.get(k, 0) - a25.get(k, 0)    # hva nyklarert-delen gjorde
        rest = vaar.get(k, 0) - a25o.get(k, 0)    # flytting i stående MTB
        fd, vv = fd_lok.get(k, {}), vaar_lok.get(k, {})
        kom_til = {e: vv[e] for e in set(vv) - set(fd)}
        borte = {e: fd[e] for e in set(fd) - set(vv)}
        endret = {e: vv[e] - fd[e] for e in set(fd) & set(vv)
                  if abs(vv[e] - fd[e]) > 0.5}
        d_mtb = sum(vv.values()) - sum(fd.values())
        forkl = []
        if abs(bonus) >= abs(rest):
            forkl.append(f"nyklarert-delen 2025 (kommunen fikk "
                         f"{_t(rk.get(k, {}).get('ny', 0))} kr av den)")
        if kom_til or borte or endret:
            forkl.append(f"lokaliteter: {len(kom_til)} nye, {len(borte)} borte, "
                         f"{len(endret)} endret, netto {_t(d_mtb, '+')} t")
        if not forkl:
            forkl.append("uforklart")
        print(f"| {navn[k]} | {a25.get(k, 0):.3%} | {vaar.get(k, 0):.3%} | "
              f"{d * 100:+.3f} | {bonus * 100:+.3f} | {rest * 100:+.3f} | "
              f"{'; '.join(forkl)} |")
        detaljer.append((navn[k], kom_til, borte, endret))

    # ── samme, mot ORDINÆR 2025: bare stående MTB står igjen ─────────
    print("\n## De 10 største avvikene mot ORDINÆR 2025 (prosentpoeng)\n")
    print("Nyklarert-delen er tatt ut. Det som står igjen, er forskjell i "
          "stående MTB: lokaliteter som kom, forsvant eller endret MTB, og "
          "at alle andre kommuners MTB flyttet seg (nevneren).\n")
    print("| kommune | ORDINÆR 2025 | 2026 A2 | avvik | MTB 2025 | MTB 2026 "
          "| forklaring |")
    print("|---|---|---|---|---|---|---|")
    topp_o = sorted(alle, key=lambda k: -abs(vaar.get(k, 0) - a25o.get(k, 0)))[:10]
    for k in topp_o:
        fd, vv = fd_lok.get(k, {}), vaar_lok.get(k, {})
        kom_til = {e: vv[e] for e in set(vv) - set(fd)}
        borte = {e: fd[e] for e in set(fd) - set(vv)}
        endret = {e: vv[e] - fd[e] for e in set(fd) & set(vv)
                  if abs(vv[e] - fd[e]) > 0.5}
        if kom_til or borte or endret:
            forkl = (f"{len(kom_til)} nye, {len(borte)} borte, {len(endret)} "
                     f"endret: " + ", ".join(
                         [f"+{e} {_t(t)} t" for e, t in sorted(kom_til.items())]
                         + [f"−{e} {_t(t)} t" for e, t in sorted(borte.items())]
                         + [f"{e} {_t(t, '+')} t" for e, t in sorted(endret.items())]))
        else:
            forkl = "uforklart"
        print(f"| {navn[k]} | {a25o.get(k, 0):.3%} | {vaar.get(k, 0):.3%} | "
              f"{(vaar.get(k, 0) - a25o.get(k, 0)) * 100:+.3f} | "
              f"{_t(sum(fd.values()))} | {_t(sum(vv.values()))} | {forkl} |")

    print("\n### Lokalitetene bak avvikene mot TOTALT\n")
    for n, kt, b, e in detaljer:
        if kt or b or e:
            print(f"**{n}**")
            for x, t in sorted(kt.items()):
                print(f"- ny siden 01.09.2025: {x}, {_t(t)} t")
            for x, t in sorted(b.items()):
                print(f"- borte siden 01.09.2025: {x}, {_t(t)} t")
            for x, t in sorted(e.items()):
                print(f"- endret: {x}, {_t(t, '+')} t")
            print()

    # ── fylkeskommunene ──────────────────────────────────────────────
    print("## Fylkeskommunene\n")
    fyl26 = dict(a["fyl"].select(["fylkesnummer", "andel"]).iter_rows())
    fyl_navn = {v: k for k, v in f.FYLKER.items()}
    tot_f = sum(pm_fyl.values())
    print("| fylke | 2025 | 2026 A2 | avvik (pp) |")
    print("|---|---|---|---|")
    for n, b in sorted(pm_fyl.items(), key=lambda x: -x[1]):
        nr = fyl_navn.get(n, "?")
        print(f"| {n} | {b / tot_f:.3%} | {fyl26.get(nr, 0):.3%} | "
              f"{(fyl26.get(nr, 0) - b / tot_f) * 100:+.3f} |")

    # ── samlet MTB, vår mot deres ────────────────────────────────────
    s25 = sum(m for v in fd_lok.values() for m in v.values())
    print(f"\nSamlet MTB i nøkkelen: Fiskeridirektoratet 01.09.2025 "
          f"{_t(s25)} t, A2 31.08.2026 {_t(sum(vaar_mtb.values()))} t "
          f"({sum(vaar_mtb.values()) / s25 - 1:+.2%})")


if __name__ == "__main__":
    main()
