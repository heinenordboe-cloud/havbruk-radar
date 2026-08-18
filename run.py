"""Inngangspunkt. Én kjøring, åtte steg.

    python run.py                 # alle kilder som er forfalt
    python run.py --bare enhetsregisteret
    python run.py --torrkjor      # hent og vis alt, skriv ingenting
    python run.py --tving         # kjør selv om kilden ble hentet nylig
    python run.py --planlagt      # den ukentlige cron-kjøringen

Hver kilde har sin egen `min_dager_mellom`. Kjøringen henter bare de som
er forfalt, slik at en ny kilde kan aktiveres midt i uka uten å skrive
dagens snapshot for de andre på nytt.

`--torrkjor` hopper over forfallssjekken med vilje: en tørrkjøring er til
for å inspisere data, og da vil du se alt.

`--planlagt` er for workflowen, ikke for deg ved tastaturet. En manuell
kjøring som ikke finner noe forfalt skal være stille — det er riktig at
en kilde hentet i går ikke hentes på nytt. Men den SAME hendelsen på den
ukentlige cron-kjøringen betyr at uka gikk uten et snapshot, usynlig for
alt annet enn denne linjen. `--planlagt` gjør det skillet eksplisitt:
null forfalte kilder er da en feil, ikke en stille exit.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))   # så run.py virker uansett hvor du står

from core import (  # noqa: E402
    changelog, diff, health, paths, registry, runner, signals, snapshot,
)


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
                        help="kjør selv om dagens snapshot finnes (skriver ny fil med løpenummer)")
    parser.add_argument("--planlagt", action="store_true",
                        help="dette er den ukentlige cron-kjøringen: null forfalte "
                             "kilder er en feil, ikke en stille exit")
    parser.add_argument("--godta-volum", metavar="KILDE",
                        help="godta kildens siste volum som nytt friskt nivå, og "
                             "avslutt. Kvitteringen for et reelt fall — bruk den "
                             "når volumvarselet er riktig, ikke for å dempe det")
    args = parser.parse_args()

    # Kvittering, ikke innsamling: skriver health.json og avslutter.
    if args.godta_volum:
        ok, melding = health.godta_volum(args.godta_volum)
        print(melding)
        return 0 if ok else 1

    observed_at = datetime.now(timezone.utc).date().isoformat()

    # 1. Finn kilder
    kilder = registry.discover()
    if args.bare:
        kilder = [k for k in kilder if k.name == args.bare]
    if not kilder:
        print("Ingen aktive kilder funnet.")
        return 1

    print(f"\nKjøring {observed_at}")

    # 2. Hopp over kilder som ble hentet nylig nok
    if not args.torrkjor and not args.tving:
        kilder, venter = runner.velg_forfalte(kilder, observed_at)
        for kilde, dager in venter:
            nar = "i dag" if dager == 0 else f"for {dager} dag(er) siden"
            print(f"  [vent] {kilde.name:<20} hentet {nar}, "
                  f"går hver {kilde.min_dager_mellom}. dag")

        if not kilder:
            if args.planlagt:
                print("\n::error::Planlagt kjøring samlet ingenting — alle kilder "
                      "ble hoppet over av frekvensvakten. Uka er tapt hvis dette "
                      "ikke undersøkes.")
                return 1
            print("\n  Ingen kilder er forfalt. --tving overstyrer.")
            return 0

    # 3. Kjør dem, isoler feil
    observasjoner, resultater = runner.run_all(
        kilder, observed_at, arkiver=not args.torrkjor
    )
    for r in resultater:
        print(f"  [{'ok  ' if r.ok else 'FEIL'}] {r.source:<20} {r.count:>6} observasjoner")
        if not r.ok:
            print(f"         {r.error.strip().splitlines()[-1]}")

    if args.torrkjor:
        print(f"\nTørrkjøring — {len(observasjoner)} observasjoner, ingenting skrevet.")
        return 0

    # 4. Diff mot forrige snapshot (må skje FØR dagens skrives)
    naa = snapshot.to_frame(observasjoner)
    endringer = diff.compare(naa, observed_at)

    # 5. Skriv dagens snapshot
    filer = snapshot.write(observasjoner, observed_at)

    # 6. Scor endringene
    scoret = signals.score(endringer)

    # 7. Legg til i endringsloggen (egen fil per kjøring, aldri omskriving)
    changelog.skriv(endringer, observed_at)

    # 8. Oppdater helsetilstand
    tilstand, nede = health.oppdater(resultater, observed_at)
    health.skriv(tilstand)

    # 9. Skriv commit-melding
    melding = bygg_commitmelding(observed_at, resultater, endringer, scoret)
    paths.COMMIT_MSG_PATH.parent.mkdir(parents=True, exist_ok=True)
    paths.COMMIT_MSG_PATH.write_text(melding, encoding="utf-8")

    # 10. Oppsummer
    print(f"\n  {len(filer)} snapshot skrevet")
    print(f"  {endringer.height} endringer siden forrige kjøring")
    print(f"  {scoret.height} av dem traff en signalregel")

    for rad in scoret.head(15).iter_rows(named=True):
        print(f"    · {rad['entity_name']}: {rad['field']} "
              f"{rad['old_value']} → {rad['new_value']}  [{rad['signal']}]")

    # Tre ulike årsaker havner i samme liste, med samme konsekvens:
    # kilden er nede (har fungert før, feiler nå), den leverte for lite
    # (volumvakten), eller den leverte men ba om tilsyn (Source.advarsler,
    # f.eks. et NACE-søk uten treff). Meldingen sier derfor ikke lenger
    # "leverer ikke" — to av tre tilfeller leverte. Hver enkelt streng
    # sier hvilken det er.
    tilsyn = nede + [a for r in resultater for a in r.advarsler]

    if tilsyn:
        print(f"\n  KREVER TILSYN: {', '.join(tilsyn)}")
        return 1   # -> rød jobb -> e-post fra GitHub, hver uke til det er fikset

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
