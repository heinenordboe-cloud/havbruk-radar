"""Backfill av historiske uker. Ved siden av run.py, ikke inni kjernen.

    python backfill.py --kilde lusetall --fra 2026-20 --til 2026-24
    python backfill.py --kilde lusetall --fra 2012-01 --til 2026-30
    python backfill.py --kilde lusetall --fra 2011-01 --til 2011-05  # stopper

Skriver snapshots i DATOREKKEFØLGE, eldst først, og utleder diff og
changelog per uke underveis. Rekkefølgen er ikke kosmetisk:
`diff.compare()` sammenligner mot forrige snapshot etter dato, så
prosesseres uker eldst først, får hver uke riktig forrige uke å
sammenligne mot. Kjøres de i motsatt rekkefølge, er hver diff tom.

`health.py` oppdateres IKKE. Volum- og feltreferansen er høyvannsmerker
mot forrige kjøring, og hundrevis av uker på rad ville enten fyrt
konstant eller forgiftet nivået. Se beslutningen fra 18.08.

## Fella som gjorde stoppvilkåret nødvendig

2010 og 2011 gir `200 OK` med tom liste, ikke `404`. En backfill som
ikke teller rader ville løpt bakover i det uendelige og sett like
vellykket ut hele veien. Derfor stopper den eksplisitt på første tomme
uke og sier fra.
"""

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import changelog, diff, registry, snapshot  # noqa: E402
from sources.lusetall import PAUSE_S, mandag  # noqa: E402


def _uker(fra: tuple[int, int], til: tuple[int, int]):
    """Alle (år, uke) fra og med `fra` til og med `til`, eldst først."""
    d = dt.date.fromisocalendar(fra[0], fra[1], 1)
    slutt = dt.date.fromisocalendar(til[0], til[1], 1)
    while d <= slutt:
        iso = d.isocalendar()
        yield iso.year, iso.week
        d += dt.timedelta(weeks=1)


def _parse_uke(tekst: str) -> tuple[int, int]:
    aar, uke = tekst.split("-")
    return int(aar), int(uke)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--kilde", required=True, help="kildenavn, f.eks. lusetall")
    p.add_argument("--fra", required=True, metavar="ÅÅÅÅ-UU")
    p.add_argument("--til", required=True, metavar="ÅÅÅÅ-UU")
    p.add_argument("--pause", type=float, default=PAUSE_S,
                   help=f"sekunder mellom kall (standard {PAUSE_S})")
    p.add_argument("--torrkjor", action="store_true",
                   help="hent og vis, skriv ingenting")
    args = p.parse_args()

    kilde = next((k for k in registry.discover() if k.name == args.kilde), None)
    if kilde is None:
        print(f"Ukjent eller inaktiv kilde: {args.kilde}")
        return 1
    if not hasattr(kilde, "hent_uke"):
        print(f"{args.kilde} har ingen hent_uke() og kan ikke backfilles.")
        return 1

    uker = list(_uker(_parse_uke(args.fra), _parse_uke(args.til)))
    print(f"Backfill {args.kilde}: {len(uker)} uker, {args.fra} -> {args.til}, "
          f"{args.pause}s pause"
          + (" (TØRRKJØRING)" if args.torrkjor else ""))

    skrevet = 0
    endringer_totalt = 0

    for aar, uke in uker:
        dato = mandag(aar, uke)
        try:
            rå = kilde.hent_uke(aar, uke)
        except Exception as e:
            print(f"  {dato} (uke {uke}/{aar}): FEIL {type(e).__name__}: {e}")
            return 1

        obs = list(kilde.parse(rå, dato))
        if not obs:
            # Ikke "ferdig" — dette er stoppvilkåret. En tom uke fra et
            # endepunkt som svarer 200 betyr at året ikke finnes.
            print(f"  {dato} (uke {uke}/{aar}): TOM — ingen observasjoner.")
            print(f"\nStoppet: uke {uke}/{aar} ga null rader. Tidligste uke "
                  f"med data er 2012-01. Skrev {skrevet} uker før dette.")
            return 1

        ramme = snapshot.to_frame(obs)
        if args.torrkjor:
            print(f"  {dato} (uke {uke}/{aar}): {ramme.height:>6} observasjoner, "
                  f"{ramme['entity_id'].n_unique():>5} lokaliteter")
        else:
            # Diff FØR skriving, som i run.py — ellers finner previous()
            # dagens egen fil og diffen blir tom.
            endr = diff.compare(ramme, dato)
            filer = snapshot.write(obs, dato)
            changelog.skriv(endr, dato)
            endringer_totalt += endr.height
            skrevet += 1
            print(f"  {dato} (uke {uke}/{aar}): {ramme.height:>6} observasjoner, "
                  f"{ramme['entity_id'].n_unique():>5} lokaliteter, "
                  f"{endr.height:>5} endringer -> {filer[0].name}")

        time.sleep(args.pause)

    print(f"\n{skrevet} uker skrevet, {endringer_totalt} endringer totalt.")
    print("health.json er URØRT — backfill oppdaterer ikke helsetilstanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
