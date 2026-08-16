"""Inngangspunkt. Én ukentlig kjøring, ni steg.

    python run.py                 # alle aktive kilder
    python run.py --bare enhetsregisteret
    python run.py --torrkjor      # hent og vis, ikke skriv noe
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))   # så run.py virker uansett hvor du står

from core import (  # noqa: E402
    changelog, diff, health, registry, runner, signals, snapshot,
)

COMMIT_MSG = ROOT / "data" / "siste_kjoring.txt"


def bygg_commitmelding(observed_at: str, resultater, endringer, scoret) -> str:
    """Commit-meldingen er nyhetsbrevet ditt de neste fire månedene.

    Du leser den i GitHub-appen på telefonen. Ingen nettside nødvendig.
    """
    linjer = [f"Snapshot {observed_at} — {endringer.height} endringer", ""]

    for rad in scoret.head(10).iter_rows(named=True):
        navn = rad["entity_name"] or rad["entity_id"]
        linjer.append(
            f"* {navn}: {rad['field']} {rad['old_value']} -> {rad['new_value']}"
            f" [{rad['signal']}]"
        )

    if scoret.height == 0 and endringer.height:
        linjer.append("* ingen endringer traff en signalregel")

    linjer.append("")
    for r in resultater:
        linjer.append(f"{'ok  ' if r.ok else 'FEIL'} {r.source}: {r.count}")

    return "\n".join(linjer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bare", help="kjør kun én kilde")
    parser.add_argument("--torrkjor", action="store_true", help="ikke skriv filer")
    parser.add_argument("--tving", action="store_true",
                        help="kjør selv om dagens snapshot finnes (overskriver)")
    args = parser.parse_args()

    observed_at = datetime.now(timezone.utc).date().isoformat()

    # 0. Er dagen allerede samlet? Da fører en ny kjøring de samme
    #    endringene inn i changeloggen på nytt. Nekt heller.
    if not args.torrkjor and not args.tving:
        alt_skrevet = snapshot.finnes_allerede(observed_at)
        if alt_skrevet:
            print(f"Snapshot for {observed_at} finnes allerede: "
                  f"{', '.join(alt_skrevet)}")
            print("Ingenting gjort. Bruk --tving for å overskrive, "
                  "eller --torrkjor for å bare se dataene.")
            return 0

    # 1. Finn kilder
    kilder = registry.discover()
    if args.bare:
        kilder = [k for k in kilder if k.name == args.bare]
    if not kilder:
        print("Ingen aktive kilder funnet.")
        return 1

    # 2. Kjør dem, isoler feil
    observasjoner, resultater = runner.run_all(kilder, observed_at)

    print(f"\nKjøring {observed_at}")
    for r in resultater:
        print(f"  [{'ok  ' if r.ok else 'FEIL'}] {r.source:<20} {r.count:>6} observasjoner")
        if not r.ok:
            print(f"         {r.error.strip().splitlines()[-1]}")

    if args.torrkjor:
        print(f"\nTørrkjøring — {len(observasjoner)} observasjoner, ingenting skrevet.")
        return 0

    # 3. Diff mot forrige snapshot (må skje FØR dagens skrives)
    naa = snapshot.to_frame(observasjoner)
    endringer = diff.compare(naa, observed_at)

    # 4. Skriv dagens snapshot
    filer = snapshot.write(observasjoner, observed_at)

    # 5. Scor endringene
    scoret = signals.score(endringer)

    # 6. Legg til i endringsloggen (egen fil per kjøring, aldri omskriving)
    changelog.skriv(endringer, observed_at)

    # 7. Oppdater helsetilstand
    tilstand, nede = health.oppdater(resultater, observed_at)
    health.skriv(tilstand)

    # 8. Skriv commit-melding
    melding = bygg_commitmelding(observed_at, resultater, endringer, scoret)
    COMMIT_MSG.write_text(melding, encoding="utf-8")

    # 9. Oppsummer
    print(f"\n  {len(filer)} snapshot skrevet")
    print(f"  {endringer.height} endringer siden forrige kjøring")
    print(f"  {scoret.height} av dem traff en signalregel")

    for rad in scoret.head(15).iter_rows(named=True):
        print(f"    · {rad['entity_name']}: {rad['field']} "
              f"{rad['old_value']} → {rad['new_value']}  [{rad['signal']}]")

    if nede:
        print(f"\n  NEDE: {', '.join(nede)} har fungert før og leverer ikke nå.")
        return 1   # -> rød jobb -> e-post fra GitHub, hver uke til det er fikset

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
