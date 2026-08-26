"""Hva versjonsvalget gjør med et tall — målt på biomasse.

    python analyse/biomasse_versjonsvalg.py --versjonsvalg 1
    python analyse/biomasse_versjonsvalg.py --versjonsvalg 2

Regner antall fisk per produksjonsområde per måned, og gjør ingenting
lurt med tallene. Poenget er ikke aggregatet — det er at de to
kjøringene over leser DE SAMME 81 MÅNEDENE og likevel svarer ulikt,
fordi de leser hver sin PÅSTAND om dem.

## Hvorfor denne fila finnes

`analyse/lusepress_mot_fasit.py` leser lusetall, sjøtemperatur og
akvakultur. Ingen av dem har flere versjoner av samme dato med ulikt
utgivelsestidspunkt, så versjonsvalget er der en tom kontrollmekanisme
— riktig ført i loggen, men uten noe å skille.

Biomasse er den kilden som faktisk river løpenummeret fra kronologien.
81 av 103 måneder finnes i to versjoner:

    2017-10-31.parquet     hentet 25.08.2026, utgitt (ukjent)
    2017-10-31.2.parquet   hentet 26.08.2026, utgitt 20.07.2024

`.2` har HØYERE løpenummer og er TO ÅR ELDRE. En analyse som leste
«nyeste fil» ville lest 2024-påstanden som om den var den gjeldende.
Denne fila er den empiriske prøven på at kjøringsloggen skiller de to —
og på at forskjellen er et tall og ikke en formalitet.

Se CLAUDE.md 1b-5 (kilder som reviderer fortiden), 1b-7 (published_at)
og F14.
"""

from __future__ import annotations

import argparse
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import snapshot                # noqa: E402
from analyse import kjoringslogg          # noqa: E402

UT = ROOT / "analyse" / "ut"
KILDE = "biomasse"
FELT = "beholdning_antall"


def overlappende(kilde: str) -> list[str]:
    """Datoene som finnes i MER ENN ÉN versjon, eldst først.

    Leser filnavn gjennom `snapshot.versjoner()` og ikke gjennom en glob:
    løpenummeret er ikke noe denne modulen skal kjenne formatet på, og
    `versjoner()` er stedet som eier det.

    Grunnen til at avgrensningen er de OVERLAPPENDE månedene og ikke hele
    serien: de 22 månedene som bare finnes i én versjon ville gjort de to
    kjøringene ulike av en annen grunn enn den vi måler. Da kunne en
    forskjell i tallet like gjerne vært et annet utvalg måneder som en
    annen påstand om de samme.
    """
    return [d for d in snapshot.datoer(kilde)
            if len(snapshot.versjoner(kilde, d)) > 1]


def fisk_per_po(lest: list[tuple[str, pl.DataFrame]]) -> dict[tuple[str, str], int]:
    """(dato, po) -> antall fisk. Tomme og utolkbare verdier utelates.

    IKKE lest som 0. Et produksjonsområde uten oppgitt beholdning og et
    med null fisk er ikke det samme, og et 0 her ville flyttet både
    summen og medianen. Samme skille som `lus_er_rapportert` gjør.
    """
    ut: dict[tuple[str, str], int] = {}
    for dato, ramme in lest:
        rader = ramme.filter(pl.col("field") == FELT).select("entity_id", "value")
        for po, verdi in rader.iter_rows():
            try:
                ut[(dato, po)] = int(verdi)
            except (TypeError, ValueError):
                continue
    return ut


def tabell(fisk: dict[tuple[str, str], int]) -> list[str]:
    """Sum fisk per år, og hvor mange PO-måneder summen hviler på."""
    per_aar: dict[str, list[int]] = defaultdict(list)
    for (dato, _po), n in fisk.items():
        per_aar[dato[:4]].append(n)
    linjer = [f"{'år':>6} {'PO-måneder':>11} {'sum fisk':>16} {'median PO-måned':>17}"]
    for aar in sorted(per_aar):
        v = per_aar[aar]
        linjer.append(f"{aar:>6} {len(v):>11} {sum(v):>16,} "
                      f"{int(st.median(v)):>17,}".replace(",", " "))
    alle = [n for v in per_aar.values() for n in v]
    linjer.append(f"{'sum':>6} {len(alle):>11} {sum(alle):>16,} "
                  f"{int(st.median(alle)):>17,}".replace(",", " "))
    return linjer


def argumenter(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--versjonsvalg", default=kjoringslogg.GJELDENDE,
        help="'gjeldende' (sist utgitte, standard), 'forste', eller et "
             "løpenummer. For biomasse er løpenummer 1 basefila hentet "
             "25.08.2026 og 2 Wayback-kopien utgitt 20.07.2024 — og den "
             "med høyest løpenummer er den ELDSTE påstanden.")
    ap.add_argument("--ut", default=None,
                    help="filnavn (uten mappe) for resultat og logg. "
                         "Standard: biomasse-versjon-<versjonsvalg>")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = argumenter(argv)
    valg = int(args.versjonsvalg) if args.versjonsvalg.isdigit() else args.versjonsvalg
    stamme = args.ut or f"biomasse-versjon-{valg}"
    UT.mkdir(parents=True, exist_ok=True)

    logg = kjoringslogg.Kjoringslogg(
        "biomasse_versjonsvalg", UT / f"{stamme}.kjoring.log")

    datoer = overlappende(KILDE)
    if not datoer:
        raise SystemExit(
            f"{KILDE} har ingen dato med flere versjoner — det er ingenting "
            f"å skille, og prøven ville vært tom.")
    overlapp = set(datoer)

    logg.valg("avgrensning.kilde", KILDE)
    logg.valg("avgrensning.datoer",
              "måneder som finnes i MER ENN ÉN versjon")
    logg.valg("avgrensning.antall", len(datoer))
    logg.valg("avgrensning.spenn", f"{datoer[0]} .. {datoer[-1]}")
    logg.valg("maal.felt", FELT)
    logg.valg("maal.aggregering", "sum og median over PO-måneder, per år")
    logg.valg("maal.manglende", "utelates; leses ALDRI som 0 fisk")

    lest = logg.les(KILDE, datoer[0], datoer[-1], versjonsvalg=valg,
                    behold=lambda d: d in overlapp,
                    forkastningsgrunn="finnes bare i én versjon")
    fisk = fisk_per_po(lest)
    logg.valg("resultat.po_maaneder", len(fisk))
    logg.valg("resultat.sum_fisk", sum(fisk.values()))

    linjer = [
        f"biomasse, {FELT}, versjonsvalg = {valg}",
        f"{len(datoer)} måneder ({datoer[0]} .. {datoer[-1]}), "
        f"{len(lest)} filer lest",
        "",
        *tabell(fisk),
        "",
        f"Kjøringslogg: {logg.peker_fra(UT)}",
        "  Alle valg bak tallene over, og hvilken snapshot-FIL hver måned",
        "  ble lest fra — med løpenummer og published_at. To kjøringer med",
        "  ulikt --versjonsvalg leser de samme datoene og ulike påstander.",
    ]
    resultat = UT / f"{stamme}.txt"
    resultat.write_text("\n".join(linjer) + "\n", encoding="utf-8")
    loggsti = logg.skriv()

    print("\n".join(linjer))
    print(f"\nskrevet: {resultat}\n         {loggsti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
