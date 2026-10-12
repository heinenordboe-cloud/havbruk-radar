"""A2: hver kommunes og fylkeskommunes andel av Havbruksfondet 2026.

    .venv/bin/python analyse/havbruksfond/a2_andeler.py

Måledatoen er 1. september 2026 kl. 12.00 (instruksen av 27.09.2024).
Akvakulturregisteret har ingen tidsakse, så andelen den dagen kan ikke
hentes i ettertid (CLAUDE.md regel 5). Det som finnes er snapshotene på
hver side: 31.08.2026 (hentet 11:27 UTC, ett døgn før) og 07.09.2026
(hentet 10:00 UTC, seks døgn etter). Alt som skjedde mellom dem, listes;
det som ikke flyttet seg mellom dem, sto slik også 01.09 kl. 12.00.

Filteret står i `felles.FILTER` og ordrett i dokumentet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import felles as f  # noqa: E402

FOR, ETTER = "2026-08-31", "2026-09-07"
# Eneste eierskapskropp i nærheten: 02.09.2026 (neste er 14.09).
EIERSKAP = "2026-09-02"


def beregn(dato: str, eierskap: str = EIERSKAP) -> dict:
    w, meta = f.bred(dato)
    lisens, lmeta = f.lakselisenser(eierskap)
    med, ute = f.filtrer(w, lisens)
    delte = f.delte_2025()
    navn = f.kommunenavn(w)
    # Kommuner som bare får MTB gjennom en delt lokalitet, har ikke
    # nødvendigvis en egen lokalitet i snapshotet. Navnet tas da fra
    # Fiskeridirektoratets 2025-regneark.
    ark, _ = f.fdir_regneark(2025)
    for r in ark["Lok. per. 01.09.25"][2:]:
        if r and r[0].isdigit():
            navn.setdefault(r[2], r[3].title())
    kom, fyl = f.andeler(med, delte, navn)
    return {"dato": dato, "w": w, "meta": meta, "lisens": lmeta, "med": med,
            "ute": ute, "l1": f.ledd1(w).height, "delte": delte,
            "kom": kom, "fyl": fyl}


def _mtb(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def main() -> None:
    a, b = beregn(FOR), beregn(ETTER)

    print("## Filteret\n\n```\n" + f.FILTER + "\n```\n")
    print("## Kroppene\n")
    print("| | akvakultur | raw_hash (arkivkroppen) | parquet sha256 | hentet |")
    print("|---|---|---|---|---|")
    for x in (a, b):
        m = x["meta"]
        print(f"| {x['dato']} | `{m['sti']}` | `{m['raw_hash'][0]}` | "
              f"`{m['parquet_sha256']}` | {m['fetched_at'][0]} |")
    print(f"\nTillatelsesarter fra `{a['lisens']['sti']}`, "
          f"sha256 `{a['lisens']['sha256']}`.\n")

    print("| | lokaliteter i snapshotet | ledd 1 | holdt ute av ledd 2 | med | "
          "MTB med (tonn) | kommuner | fylker |")
    print("|---|---|---|---|---|---|---|---|")
    for x in (a, b):
        print(f"| {x['dato']} | {x['w'].height} | {x['l1']} | "
              f"{x['ute'].height} | {x['med'].height} | "
              f"{_mtb(x['kom']['mtb'].sum())} | {x['kom'].height} | "
              f"{x['fyl'].height} |")

    print("\n### Holdt ute av ledd 2 (31.08)\n")
    for r in a["ute"].select(["entity_id", "navn", "kommune", "mtb",
                              "tillatelser"]).sort("entity_id").iter_rows():
        print(f"- {r[0]} {r[1]} ({r[2]}), {_mtb(r[3])} t — {r[4]}")

    print("\n### Delte lokaliteter (andel fra Fiskeridirektoratet 01.09.2025)\n")
    med_a = set(a["med"]["entity_id"])
    for e, deler in sorted(a["delte"].items()):
        inn = "med" if e in med_a else "IKKE i filteret 31.08"
        print(f"- {e}: " + ", ".join(f"{k} {andel:.4f}" for k, andel in deler)
              + f" ({inn})")

    # ── endringer mellom de to kroppene ──────────────────────────────
    print(f"\n## Endringer {FOR} → {ETTER} i det filtrerte utvalget\n")
    ka = dict(a["med"].select(["entity_id", "mtb"]).iter_rows())
    kb = dict(b["med"].select(["entity_id", "mtb"]).iter_rows())
    na = {r[0]: r[1:] for r in a["w"].select(
        ["entity_id", "navn", "kommunenummer", "kommune"]).iter_rows()}
    nb = {r[0]: r[1:] for r in b["w"].select(
        ["entity_id", "navn", "kommunenummer", "kommune"]).iter_rows()}
    for tittel, ider in (("Kom til", sorted(set(kb) - set(ka))),
                         ("Forsvant", sorted(set(ka) - set(kb)))):
        print(f"**{tittel}: {len(ider)}**\n")
        for e in ider:
            n = nb.get(e) or na.get(e)
            k = kb.get(e, ka.get(e))
            hvorfor = ""
            if tittel == "Forsvant" and e in nb:
                hvorfor = " — finnes fortsatt, men faller ut av filteret"
            if tittel == "Kom til" and e in na:
                hvorfor = " — fantes fra før, men kom inn i filteret"
            print(f"- {e} {n[0]} ({n[2]} {n[1]}), {_mtb(k)} t{hvorfor}")
        print()
    endret = [(e, ka[e], kb[e]) for e in sorted(set(ka) & set(kb))
              if ka[e] != kb[e]]
    print(f"**Endret MTB: {len(endret)}**\n")
    for e, x, y in endret:
        print(f"- {e} {na[e][0]} ({na[e][2]}): {_mtb(x)} → {_mtb(y)} t "
              f"({y - x:+,.0f})".replace(",", " "))
    flyttet = [e for e in set(ka) & set(kb) if na[e][1] != nb[e][1]]
    print(f"\n**Byttet kommunenummer: {len(flyttet)}**"
          + "".join(f"\n- {e} {na[e][1]} → {nb[e][1]}" for e in flyttet))

    # ── sammenslåtte og delte kommuner ───────────────────────────────
    print("\n## Kommunenumre mot Fiskeridirektoratets 2025-regneark\n")
    ark, _ = f.fdir_regneark(2025)
    fd = {}
    for r in ark["Lok. per. 01.09.25"][2:]:
        if r and r[0].isdigit():
            fd.setdefault(r[0], set()).add(r[2])
    vaar = dict(a["w"].select(["entity_id", "kommunenummer"]).iter_rows())
    ulik = [(e, sorted(k), vaar[e]) for e, k in fd.items()
            if e in vaar and vaar[e] not in k]
    print(f"Lokaliteter i begge der vårt kommunenummer ikke er blant "
          f"Fiskeridirektoratets: **{len(ulik)}**")
    for e, k, v in ulik:
        print(f"- {e}: 2025 {k}, 31.08.2026 {v}")
    fd_kom = {r[0] for r in ark["Kommuner"][4:] if r and r[0].isdigit()}
    vaar_kom = set(a["kom"]["kommunenummer"])
    print(f"\nKommunenumre med MTB 2025 men ikke 31.08.2026: "
          f"{sorted(fd_kom - vaar_kom)}")
    print(f"Kommunenumre med MTB 31.08.2026 men ikke 2025: "
          f"{sorted(vaar_kom - fd_kom)}")

    # ── andelene ─────────────────────────────────────────────────────
    print(f"\n## Fylkeskommunene\n")
    print("| fylke | MTB 31.08 | andel 31.08 | andel 07.09 |")
    print("|---|---|---|---|")
    fb = dict(b["fyl"].select(["fylkesnummer", "andel"]).iter_rows())
    for nr, mtb, andel in a["fyl"].iter_rows():
        print(f"| {nr} {f.FYLKER.get(nr, '?')} | {_mtb(mtb)} | "
              f"{andel:.4%} | {fb.get(nr, 0):.4%} |")

    print(f"\n## Kommunene, alle {a['kom'].height}\n")
    print("| # | komnr | kommune | MTB 31.08 | andel 31.08 | andel 07.09 | delt |")
    print("|---|---|---|---|---|---|---|")
    kbn = dict(b["kom"].select(["kommunenummer", "andel"]).iter_rows())
    for i, (nr, mtb, delt, navn, andel) in enumerate(
            a["kom"].select(["kommunenummer", "mtb", "delt", "kommune",
                             "andel"]).iter_rows(), 1):
        print(f"| {i} | {nr} | {navn} | {_mtb(mtb)} | {andel:.4%} | "
              f"{kbn.get(nr, 0):.4%} | {'ja' if delt else ''} |")
    ikke_a = set(kbn) - set(a["kom"]["kommunenummer"])
    if ikke_a:
        print(f"\nBare i 07.09: {sorted(ikke_a)}")


if __name__ == "__main__":
    main()
