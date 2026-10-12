"""A4: kommuner med lokaliteter klarert i perioden for ny lokalitets-MTB.

    .venv/bin/python analyse/havbruksfond/a4_ny_biomasse.py [dato]

Perioden, ordrett fra instruksen av 27.09.2024:

    «Ved fordeling av midlene som skal fordeles med utgangspunkt i ny
    lokalitets-MTB, skal Fiskeridirektoratet legge til grunn ny
    lokalitets-MTB i en periode fra 1. september kl 12.00 i oddetallsår,
    og to kalenderår tilbake i tid. Det gjøres ikke fratrekk for
    lokalitets-MTB som har bortfalt i perioden.»

Neste oddetallsår er 2027, så perioden som løper nå er
01.09.2025 kl. 12.00 – 01.09.2027 kl. 12.00. 2026 er et partallsår, og
utbetalingen i 2026 har ingen nyklarert-del.

## Hvorfor resultatet er MÅLBAR, ikke MÅLT

`forste_klarering` er datoen en LOKALITET ble klarert første gang. Det
regelverket teller er ny lokalitets-MTB, og Fiskeridirektoratets
regneark for 2025 viser hva de faktisk regnet: arket «Økt kapasitet» har
både nye lokaliteter (HistKap 0) og økt MTB på lokaliteter som fantes
fra før. Den andre gruppen har en `forste_klarering` langt bak i tid og
er usynlig for feltet. Skriptet måler hvor stor den gruppen var i 2025.
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a2_andeler as a2  # noqa: E402
import felles as f  # noqa: E402

# 01.09.2025 kl. 12.00 norsk tid er 10.00 UTC (sommertid).
FRA = "2025-09-01T10:00:00Z"
FRA_2025 = "2023-09-01T10:00:00Z"   # perioden Fiskeridirektoratet brukte i 2025
TIL_2025 = "2025-09-01T10:00:00Z"


def _t(x: float, fortegn: str = "") -> str:
    return f"{x:{fortegn},.0f}".replace(",", " ")


def main(dato: str = "2026-10-12") -> None:
    a = a2.beregn(dato, eierskap=dato if (f.D / "arkiv" / "eierskap" /
                                           f"{dato}.json.gz").exists()
                  else a2.EIERSKAP)
    med = a["med"]

    # ── kontroll mot 2025: hva fanger forste_klarering av det de telte? ──
    ark, meta = f.fdir_regneark(2025)
    okt = [r for r in ark["Økt kapasitet"][1:] if r and r[0].isdigit()]
    ny_2025 = {r[0]: float(r[8]) for r in okt if float(r[5]) == 0}
    okt_2025 = {r[0]: float(r[8]) for r in okt if float(r[5]) > 0}
    fk = dict(a["w"].select(["entity_id", "forste_klarering"]).iter_rows())
    treff = {e for e in ny_2025 if FRA_2025 <= fk.get(e, "") < TIL_2025}
    print("## Kontroll mot Fiskeridirektoratets 2025-regneark\n")
    print(f"Regneark `{meta['sti']}`, sha256 `{meta['sha256']}`.\n")
    print(f"- rader i «Økt kapasitet»: {len(okt)}")
    print(f"- av dem nye lokaliteter (HistKap 0): {len(ny_2025)}, "
          f"{_t(sum(ny_2025.values()))} t")
    print(f"- av dem økt MTB på eksisterende lokalitet: {len(okt_2025)}, "
          f"{_t(sum(okt_2025.values()))} t")
    andel = sum(okt_2025.values()) / (sum(okt_2025.values()) + sum(ny_2025.values()))
    print(f"- **andel av ny MTB 2025 som forste_klarering ikke kan se: "
          f"{andel:.1%}**")
    print(f"- nye lokaliteter 2025 med forste_klarering i 01.09.2023–01.09.2025 "
          f"i vårt snapshot {dato}: {len(treff)} av {len(ny_2025)}"
          + "".join(f"\n  - utenfor: {e} forste_klarering={fk.get(e, 'finnes ikke')}"
                    for e in sorted(set(ny_2025) - treff)))

    # ── kan versjonsfeltet se den andre gruppen? ─────────────────────
    # Bare SISTE versjon står i snapshotet, så en senere versjon av en
    # annen grunn skjuler en kapasitetsendring. Testen er hvor mange av
    # 2025-økningene feltet fortsatt peker på i dag.
    va = dict(a["w"].select(["entity_id", "versjon_aarsak"]).iter_rows())
    vg = dict(a["w"].select(["entity_id", "versjon_gyldig_fra"]).iter_rows())
    sett = {e for e in okt_2025
            if va.get(e) == "CAPACITY_CHANGE" and FRA_2025 <= vg.get(e, "") < TIL_2025}
    print(f"- økt MTB 2025 der `versjon_aarsak` = CAPACITY_CHANGE med "
          f"`versjon_gyldig_fra` i perioden, i snapshot {dato}: "
          f"{len(sett)} av {len(okt_2025)}, "
          f"{_t(sum(okt_2025[e] for e in sett))} av "
          f"{_t(sum(okt_2025.values()))} t")
    andre = sorted((va.get(e, "finnes ikke"), e) for e in set(okt_2025) - sett)
    print("  - de andre, etter `versjon_aarsak` i dag: " + ", ".join(
        f"{n} {sum(1 for x, _ in andre if x == n)}"
        for n in sorted({x for x, _ in andre})))

    # ── lokalitetene i perioden som løper nå ─────────────────────────
    nye = (med.filter(pl.col("forste_klarering") >= FRA)
           .select(["entity_id", "navn", "kommunenummer", "kommune",
                    "mtb", "forste_klarering", "klareringstype"])
           .sort(["kommunenummer", "forste_klarering"]))
    print(f"\n## Lokaliteter i nøkkelen med forste_klarering fra {FRA} "
          f"(snapshot {dato})\n")
    print(f"Snapshot `{a['meta']['sti']}`, raw_hash `{a['meta']['raw_hash'][0]}`.\n")
    print("| lokalitet | navn | kommune | MTB | forste_klarering | klarering |")
    print("|---|---|---|---|---|---|")
    for r in nye.iter_rows():
        print(f"| {r[0]} | {r[1]} | {r[2]} {r[3]} | {_t(r[4])} | {r[5][:10]} | "
              f"{r[6]} |")
    per = (nye.group_by(["kommunenummer", "kommune"])
           .agg(pl.len().alias("lokaliteter"), pl.col("mtb").sum())
           .sort("mtb", descending=True))
    print(f"\n**{per.height} kommuner, {nye.height} lokaliteter, "
          f"{_t(nye['mtb'].sum())} t**\n")
    print("| kommune | lokaliteter | MTB (t) |")
    print("|---|---|---|")
    for r in per.iter_rows():
        print(f"| {r[0]} {r[1]} | {r[2]} | {_t(r[3])} |")

    # ── økt MTB på eksisterende lokaliteter: bare det serien rekker ──
    forste = sorted(p.name[:10] for p in (f.D / "raw" / "akvakultur")
                    .glob("*.parquet"))[0]
    w0, _ = f.bred(forste)
    k0 = dict(w0.select(["entity_id", "mtb"]).iter_rows())
    okt = [(e, n, kn, k0[e], k) for e, n, kn, k in med.select(
               ["entity_id", "navn", "kommune", "mtb"]).iter_rows()
           if e in k0 and k > k0[e]]
    print(f"\n## Økt MTB på lokaliteter som fantes {forste} (snapshot {dato})\n")
    print(f"Serien begynner {forste}. Økning mellom 01.09.2025 og {forste} "
          f"kan ikke ses.\n")
    for e, n, kn, x, y in sorted(okt):
        print(f"- {e} {n} ({kn}): {_t(x)} → {_t(y)} t ({_t(y - x, '+')})")
    if not okt:
        print("Ingen.")

    kap = (med.filter((pl.col("versjon_aarsak") == "CAPACITY_CHANGE")
                      & (pl.col("versjon_gyldig_fra") >= FRA)
                      & (pl.col("forste_klarering") < FRA))
           .select(["entity_id", "navn", "kommunenummer", "kommune",
                    "mtb", "versjon_gyldig_fra"])
           .sort(["kommunenummer", "entity_id"]))
    print(f"\n## Lokaliteter fra før perioden med kapasitetsendring fra "
          f"{FRA} (`versjon_aarsak`, snapshot {dato})\n")
    print("Retningen og størrelsen står ikke i feltet; bare at kapasiteten "
          "ble endret, og når.\n")
    print("| lokalitet | navn | kommune | MTB nå | versjon_gyldig_fra |")
    print("|---|---|---|---|---|")
    for r in kap.iter_rows():
        print(f"| {r[0]} | {r[1]} | {r[2]} {r[3]} | {_t(r[4])} | {r[5][:10]} |")
    print(f"\n**{kap.height} lokaliteter i "
          f"{kap['kommunenummer'].n_unique()} kommuner.**")

    # ── ny MTB mot Fiskeridirektoratets egen startverdi ──────────────
    # Perioden som løper begynner 01.09.2025 kl. 12.00, og
    # Fiskeridirektoratets lokalitetsliste per den dagen er nettopp
    # utgangspunktet («HistKap» i 2025-regnearket). Økningen er nå minus
    # da, per lokalitet og kommune, uten fratrekk for det som har falt
    # bort (instruksen).
    start: dict[tuple[str, str], float] = {}
    for r in ark["Lok. per. 01.09.25"][2:]:
        if r and r[0].isdigit():
            start[(r[0], r[2])] = float(r[4]) * float(r[5])
    naa: dict[tuple[str, str], float] = {}
    for e, k, kp in med.select(["entity_id", "kommunenummer", "mtb"]).iter_rows():
        for kk, andel in (a["delte"].get(e) or [(k, 1.0)]):
            naa[(e, kk)] = kp * andel
    okning = {nk: v - start.get(nk, 0.0) for nk, v in naa.items()
              if v - start.get(nk, 0.0) > 0.5}
    navn = f.kommunenavn(a["w"])
    per_k: dict[str, list] = {}
    for (e, k), d in okning.items():
        per_k.setdefault(k, []).append((e, d, (e, k) not in start))
    print(f"\n## Ny lokalitets-MTB fra 01.09.2025 til {dato}, per kommune\n")
    print("Nå (snapshot) minus Fiskeridirektoratets lokalitetsliste per "
          "01.09.2025, bare økninger. «ny» = lokaliteten sto ikke på lista.\n")
    print("| kommune | ny MTB (t) | lokaliteter |")
    print("|---|---|---|")
    for k, xs in sorted(per_k.items(), key=lambda x: -sum(d for _, d, _ in x[1])):
        print(f"| {k} {navn.get(k, '?')} | {_t(sum(d for _, d, _ in xs))} | "
              + ", ".join(f"{e}{' (ny)' if ny else ''} {_t(d, '+')}"
                          for e, d, ny in sorted(xs)) + " |")
    print(f"\n**{len(per_k)} kommuner, {len(okning)} lokaliteter, "
          f"{_t(sum(okning.values()))} t.**")


if __name__ == "__main__":
    main(*sys.argv[1:])
