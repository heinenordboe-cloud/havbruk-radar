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

## To ulike «feil», to ulike svar

En TOM uke stopper kjøringen. Den betyr at året ikke finnes, og alt
eldre vil også være tomt — å fortsette er å brenne API-kall på
ingenting.

En uke som FEILER gjør det ikke. Retryen i `sources/_http.py` har
allerede brukt opp forsøkene sine, så feilen er enten permanent eller
en tjeneste som var nede akkurat da. Å avbryte hele backfillen på uke
300 av 730 fordi én uke feilet er å kaste 429 vellykkede kall — og
kjøringen er gjenopptakbar, så det er ingenting å vinne på å stoppe.

Prisen for å fortsette er at et hull kan bli usynlig. Det betales med
feillista til slutt: hver uke som feilet skrives ut, og kjøringen
avsluttes med feilkode. Uten den lista ville `continue` vært en stille
feil av samme slag som resten av repoet er bygget for å hindre.
"""

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import changelog, diff, raw as raw_arkiv, registry, runner, snapshot  # noqa: E402
from core.config import get  # noqa: E402
from sources.lusetall import PAUSE_S, mandag, uke_med_etterslep  # noqa: E402


def _ferskeste_tillatte(kilde) -> tuple[int, int]:
    """Nyeste uke backfill får lov å skrive.

    Samme N-4-grense som den løpende kilden bruker. Går backfill
    lenger fram, skriver den uker den ukentlige jobben også vil skrive
    (dobbeltskriving, .2-filer), eller uker som ennå er ufullstendige og
    dermed permanent halve. Stopper den for tidlig, blir det hull.
    Grensen må være den SAMME på begge sider, ikke to tall som ligner.
    """
    uker = int(get(f"kilder.{kilde.name}.uker_etterslep", 4))
    # UTC, ikke date.today(). run.py regner kjøredatoen i UTC, og grensen
    # skal være den SAMME på begge sider — to klokker som er uenige om
    # hvilken dag det er, er nok til å flytte grensen en hel ISO-uke ved
    # et ukeskille. Da skriver backfillen enten en uke den ukentlige
    # jobben også tar, eller lar en uke ligge mellom seg og den.
    return uke_med_etterslep(dt.datetime.now(dt.timezone.utc).date(), uker)


def _uker(fra: tuple[int, int], til: tuple[int, int]):
    """Alle (år, uke) fra og med `fra` til og med `til`, eldst først."""
    d = dt.date.fromisocalendar(fra[0], fra[1], 1)
    slutt = dt.date.fromisocalendar(til[0], til[1], 1)
    while d <= slutt:
        iso = d.isocalendar()
        yield iso.year, iso.week
        d += dt.timedelta(weeks=1)


def _finnes_allerede(kilde_navn: str, dato: str) -> bool:
    """Er uka allerede skrevet?

    Gjør backfillen gjenopptakbar. Uten dette gir en omstart etter et
    avbrudd `.2`-filer for hver uke som allerede lå der — både snapshot
    og arkiv — fordi begge løser kollisjon med løpenummer i stedet for å
    overskrive. Et avbrudd på år åtte ville blitt sju år med duplikater å
    rydde for hånd, og filene er append-only.

    Sjekken skjer FØR hentingen, så en omstart heller ikke bruker opp
    API-kall på uker som er ferdige.
    """
    mappe = snapshot.RAW_DIR / kilde_navn
    if not mappe.exists():
        return False
    return ((mappe / f"{dato}.parquet").exists()
            or any(mappe.glob(f"{dato}.*.parquet")))


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

    til = _parse_uke(args.til)
    grense = _ferskeste_tillatte(kilde)
    if dt.date.fromisocalendar(*til, 1) > dt.date.fromisocalendar(*grense, 1):
        print(f"  --til {args.til} er ferskere enn etterslepsgrensen "
              f"{grense[0]}-{grense[1]:02d}. Klipper der: uker etter den er "
              f"enten ufullstendige eller den ukentlige jobbens ansvar.")
        til = grense

    uker = list(_uker(_parse_uke(args.fra), til))
    if not uker:
        print("Ingen uker i intervallet.")
        return 1

    print(f"Backfill {args.kilde}: {len(uker)} uker, {args.fra} -> "
          f"{til[0]}-{til[1]:02d}, {args.pause}s pause"
          + (" (TØRRKJØRING)" if args.torrkjor else ""))

    skrevet = 0
    hoppet = 0
    endringer_totalt = 0
    feilede: list[tuple[str, int, int, str]] = []

    for aar, uke in uker:
        dato = mandag(aar, uke)

        if not args.torrkjor and _finnes_allerede(kilde.name, dato):
            hoppet += 1
            continue

        try:
            rå = kilde.hent_uke(aar, uke)
        except Exception as e:
            # Videre, ikke stopp. Retryen i sources/_http.py har allerede
            # brukt opp forsøkene sine på transiente feil, så det som
            # kommer hit er enten permanent eller en uke som var nede
            # akkurat nå. Å avbryte hele backfillen på uke 300 av 730
            # fordi ÉN uke feilet er å kaste 429 vellykkede kall.
            #
            # Dette er bare forsvarlig sammen med feillista nedenfor.
            # Uten den ville hoppet blitt stille, og et hull i
            # historikken usynlig — nøyaktig feilmodusen resten av
            # repoet er bygget for å hindre.
            feil = f"{type(e).__name__}: {e}"
            print(f"  {dato} (uke {uke}/{aar}): FEIL {feil}")
            feilede.append((dato, uke, aar, feil))
            time.sleep(args.pause)
            continue

        # Arkivet FØR parse, som i runner.run_all(). Uten det er en
        # parse-feil oppdaget om et halvt år permanent datatap for alle
        # 730 ukene — og det er hele begrunnelsen for rå-arkivet.
        raw_hash = ""
        if not args.torrkjor:
            raw_hash = raw_arkiv.arkiver(kilde.name, dato, rå)

        obs = runner.stempl(kilde.parse(rå, dato),
                            source_version=kilde.version, raw_hash=raw_hash)
        if not obs:
            # Ikke "ferdig" — dette er stoppvilkåret. En tom uke fra et
            # endepunkt som svarer 200 betyr at året ikke finnes.
            print(f"  {dato} (uke {uke}/{aar}): TOM — ingen observasjoner.")
            print(f"\nStoppet: uke {uke}/{aar} ga null rader. Tidligste uke "
                  f"med data er 2012-01. Skrev {skrevet} uker før dette.")
            if feilede:
                print(f"{len(feilede)} uke(r) feilet også underveis:")
                for d, u, a, f in feilede:
                    print(f"  {d}  uke {u:>2}/{a}  {f}")
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

    print(f"\n{skrevet} uker skrevet, {hoppet} hoppet over (fantes "
          f"allerede), {endringer_totalt} endringer totalt.")
    print("health.json er URØRT — backfill oppdaterer ikke helsetilstanden.")

    if feilede:
        print(f"\n{len(feilede)} uke(r) FEILET:")
        for dato, uke, aar, feil in feilede:
            print(f"  {dato}  uke {uke:>2}/{aar}  {feil}")
        print("\nHullene er reelle. Kjør samme intervall på nytt — uker som "
              "allerede er skrevet hoppes over, så bare disse hentes.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
