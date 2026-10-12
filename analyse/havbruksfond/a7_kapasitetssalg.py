"""A7: inntekter fra kapasitetssalget 2026, og fondets andel per kommune.

    .venv/bin/python analyse/havbruksfond/a7_kapasitetssalg.py

Kjøres på nytt hver uke: leser hver changelogfil for `eierskap` fra og
med FRA, så en ny uke kommer med uten endring i skriptet.

## Hva som telles

Hver `kapasitet`-rad i changeloggen for eierskap der en tillatelse fikk
HØYERE kapasitet. Økningen klassifiseres slik:

    fastpris    ny == round(gammel × 1,01), hele tonn — kapittel 3 i
                FOR-2026-08-20-1764 (se docs/MALING-FUNN-OKTOBER.md F1.4)
    uavklart    alt annet: unntaksvekst, auksjon eller noe tredje.
                Changeloggen sier ikke hvilken hjemmel en økning har.

Nye tillatelser (`ny`, kapasitet fra ingenting) listes for seg som
uavklart. De kan være auksjonen («auksjon av nye tillatelser»,
pressemeldingen 10.09.2026), men kan like gjerne være noe annet.

## Kronebeløpet er et GULV

Bare fastprisøkningene prises, med 270 000 kr/t fra pressemeldingen
10.09.2026. Tallet er lavere enn det fondet faktisk får, fordi:

  1. unntaksvekst selges til samme pris, men kan ikke skilles fra annet
     i changeloggen, og telles ikke
  2. auksjonsprisene er ikke i noen kilde vi har
  3. en økning som ikke er registrert i pub-aqua ennå, er ikke med
  4. tillatelser eid av personer, ENK og sektor 2300 fjernes i
     `fetch()` før arkivering, og kan ikke ses i det hele tatt
"""
from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import a2_andeler as a2  # noqa: E402
import felles as f  # noqa: E402
from arkiver_vilkar import synlig_tekst  # noqa: E402

FRA = "2026-09-28"
# Andelen av salgsinntektene som går til fondet. Se dokumentet, A1: sagt
# for fastpris og auksjon 2024, gjentatt som faktaboks 10.11.2025.
FONDETS_ANDEL = 0.55
KOMMUNER, FYLKER = 0.80, 0.20


_kropper: dict[str, dict] = {}


def _tillatelse(dato: str, nr: str) -> dict:
    """Tillatelsen i eierskapskroppen for changeloggens uke."""
    if dato not in _kropper:
        _kropper[dato] = f.tillatelser(dato)
    return _kropper[dato].get(nr, {})


def _type(dato: str, nr: str) -> str:
    t = _tillatelse(dato, nr)
    ty = t.get("type") or {}
    return f"{ty.get('tag', '?')} {ty.get('productionStageValue', '')}".strip()


def _laks(dato: str, nr: str) -> bool:
    return f.er_laks(_tillatelse(dato, nr))


def _t(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def pris() -> tuple[int, str]:
    """Fastprisen, lest av pressemeldingen 10.09.2026 og ikke skrevet inn."""
    sti = f.D / "arkiv" / "regjeringen-pressemeldinger" / "2026-09-10.bin.gz"
    t = synlig_tekst(gzip.open(sti, "rb").read())
    m = re.search(r"Én prosent selges til fastpris\..{0,120}?Prisen er "
                  r"([\d ]+) kroner per tonn", t)
    if not m:
        raise ValueError(f"fant ikke fastprisen i {sti}")
    return int(m.group(1).replace(" ", "")), m.group(0)


def endringer() -> pl.DataFrame:
    filer = sorted(p for p in (f.D / "changelog" / "eierskap").glob("*.parquet")
                   if p.name[:10] >= FRA)
    c = pl.concat([pl.read_parquet(p).with_columns(pl.lit(p.name).alias("fil"))
                   for p in filer], how="diagonal_relaxed")
    return (c.filter(pl.col("field") == "kapasitet")
            .with_columns(pl.col("old_value").cast(pl.Float64).alias("gammel"),
                          pl.col("new_value").cast(pl.Float64).alias("ny")))


def main() -> None:
    kr_t, sitat = pris()
    c = endringer()
    filer = sorted(c["fil"].unique())
    okt = (c.filter((pl.col("change_type") == "endret")
                    & (pl.col("ny") > pl.col("gammel")))
           .with_columns((pl.col("ny") - pl.col("gammel")).alias("tonn"),
                         ((pl.col("gammel") * 1.01).round(0) == pl.col("ny"))
                         .alias("fastpris"))
           .sort(["observed_at", "entity_id"]))
    ned = c.filter((pl.col("change_type") == "endret")
                   & (pl.col("ny") < pl.col("gammel")))
    nye = c.filter(pl.col("change_type") == "ny").sort("entity_id")

    print(f"## Grunnlaget\n\nChangeloggfiler for eierskap fra {FRA}: "
          f"{', '.join(filer)}.\n")
    print(f"Pris, ordrett fra `regjeringen-pressemeldinger/2026-09-10`: "
          f"«{sitat}»\n")
    print(f"- økt kapasitet på eksisterende tillatelse: {okt.height}")
    print(f"- redusert kapasitet: {ned.height}")
    print(f"- nye tillatelser med kapasitet: {nye.height}\n")

    print("## Hver tillatelse med økt kapasitet\n")
    print("| uke | tillatelse | type | laks/ørret/regnbueørret | gammel | ny | "
          "tonn økt | klasse |")
    print("|---|---|---|---|---|---|---|---|")
    for r in okt.select(["observed_at", "entity_id", "gammel", "ny", "tonn",
                         "fastpris"]).iter_rows():
        print(f"| {r[0]} | {r[1]} | {_type(r[0], r[1])} | "
              f"{'ja' if _laks(r[0], r[1]) else 'nei'} | {r[2]:.0f} | "
              f"{r[3]:.0f} | {r[4]:.0f} | "
              f"{'fastpris (1 %)' if r[5] else 'uavklart'} |")

    print("\n## Nye tillatelser (uavklart)\n")
    print("| uke | tillatelse | type | laks/ørret/regnbueørret | kapasitet |")
    print("|---|---|---|---|---|")
    for r in nye.select(["observed_at", "entity_id", "ny"]).iter_rows():
        print(f"| {r[0]} | {r[1]} | {_type(r[0], r[1])} | "
              f"{'ja' if _laks(r[0], r[1]) else 'nei'} | {_t(r[2])} |")
    if ned.height:
        print("\n## Redusert kapasitet (ikke regnet med)\n")
        for r in ned.select(["observed_at", "entity_id", "gammel", "ny"]).iter_rows():
            print(f"- {r[0]} {r[1]}: {r[2]:.0f} → {r[3]:.0f}")

    tonn_f = okt.filter(pl.col("fastpris"))["tonn"].sum()
    tonn_u = okt.filter(~pl.col("fastpris"))["tonn"].sum()
    kr = tonn_f * kr_t
    fond = kr * FONDETS_ANDEL
    print("\n## Gulvet\n")
    print(f"- fastpris: {okt.filter(pl.col('fastpris')).height} tillatelser, "
          f"**{_t(tonn_f)} t × {_t(kr_t)} kr = {_t(kr)} kr**")
    print(f"- uavklart, ikke priset: "
          f"{okt.filter(~pl.col('fastpris')).height} økninger, {_t(tonn_u)} t; "
          f"{nye.height} nye tillatelser")
    print(f"- fondets andel {FONDETS_ANDEL:.0%}: **{_t(fond)} kr** "
          f"(kommuner {_t(fond * KOMMUNER)}, fylkeskommuner "
          f"{_t(fond * FYLKER)})")

    a = a2.beregn(a2.FOR)
    print("\n## Fordelt etter andelene fra A2 (31.08.2026)\n")
    print("| fylkeskommune | andel | kr |")
    print("|---|---|---|")
    for nr, _, andel in a["fyl"].iter_rows():
        print(f"| {nr} {f.FYLKER.get(nr, '?')} | {andel:.3%} | "
              f"{_t(fond * FYLKER * andel)} |")
    print("\n| # | kommune | andel | kr |")
    print("|---|---|---|---|")
    for i, (nr, navn, andel) in enumerate(
            a["kom"].select(["kommunenummer", "kommune", "andel"]).iter_rows(), 1):
        print(f"| {i} | {nr} {navn} | {andel:.3%} | "
              f"{_t(fond * KOMMUNER * andel)} |")


if __name__ == "__main__":
    main()
