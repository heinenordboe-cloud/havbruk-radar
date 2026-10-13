"""Daglig arkiv av kroppene til registre som endrer seg mellom mandagene.

    python arkiver_daglig.py                  # hent, og skriv det som er nytt
    python arkiver_daglig.py --torrkjor       # si hva som ville skjedd

Kjøres daglig av `daglig.yml` i datarepoet.

## Hvorfor

Den ukentlige innsamlingen tar ett bilde i uka. Registrene den henter fra
sier hva som gjelder NÅ og overskriver seg selv: en tillatelse som skifter
eier tirsdag og igjen torsdag, er borte før mandagen kommer. Et
øyeblikksbilde kan ikke hentes i etterkant (CLAUDE.md regel 5).

## Hva som skrives

For hver kilde i `KILDER`: kroppen `fetch()` returnerer, serialisert som
`core.raw` gjør for innsamlingen — samme bytes, samme sha256.

  * Kroppen skrives til `data/arkiv/<kilde>/<dato>.<ext>.gz`, samme
    navnekonvensjon og løpenummer som den ukentlige, BARE når sha256
    avviker fra siste lagrede kropp for kilden, daglig eller ukentlig.
  * Loggfila `data/arkiv/<kilde>/<dato>.logg.json` skrives hver kjøring,
    med løpenummer hvis den finnes: `kjoring: daglig`, sha256, når vi
    hentet, `ny` eller `uendret`, og hvilken kropp den ble sammenlignet
    med — og om DEN var daglig eller ukentlig. En kropp er daglig når en
    daglig logg peker på den; ukentlige kropper har ingen logg.

Ingen snapshot, ingen changelog, og health.json røres ikke: dette er
råarkiv, ikke innsamling. `core/` er uendret. `data/kvitteringer/` er
portens og brukes ikke her.

## Siste lagrede kropp

Hentes etter filnavn (dato, løpenummer). F14 er grunnen til å nevne det:
filnavnet er en stedfortreder for rekkefølge, og arkivinnsetting brøt den
for biomasse. For kildene her er `gjelder_for()` kjøredatoen, så datoen
i navnet ER dagen kroppen ble hentet — og blir den likevel feil, mister
vi ingenting: hver daglig logg har sha256 for det vi fikk, også når det
var uendret. En feil «siste» gir i verste fall en kropp for mye, eller
en kropp som ikke skrives fordi de samme bytene allerede ligger der.

## Akvakultur venter

MÅLT 13.10.2026, to hentinger 20 sekunder fra hverandre og en tredje en
time senere: 1780 lokaliteter, samme lengde (6 718 929 byte), ulik sha256
hver gang. Eneste forskjell var rekkefølgen i `speciesTypes` — for 77 av
de 201 lokalitetene med mer enn én art etter 20 sekunder, 73 etter en
time. Eierskap og biomasselag var byte-like over den samme timen, og med
mandagens ukekropp. Kroppen blir aldri byte-lik, og regelen over ville skrevet ~450 kB
hver dag. Lagringsformen er Heines valg, og kilden står ikke i `KILDER`
før den er tatt.

## Samtidig med innsamlingen

`samle.yml` skriver de samme mappene. Hentet begge samme dag med hver sin
checkout, kunne begge valgt `<dato>.json.gz`, og rebasen ville stoppet på
konflikten. `daglig.yml` venter derfor til ingen innsamling kjører, tar
inn siste main, og først da kjører dette skriptet. Se `delt` i
`.github/jobber.yml` i datarepoet.

## Kodeproveniens

Som `arkiver_vilkar.py`: `kodeproveniens.krev_sporbar()` før noe hentes,
og `kode_commit`/`kode_rent` i hver logg. `--torrkjor` er unntatt.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

from core import kodeproveniens
from core import raw as raw_arkiv
from core import registry

# Kildene som arkiveres daglig. Navnet er kildens `name`.
KILDER = ("eierskap", "biomasselag")

_NAVN = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\.(\d+))?\.[a-z]+\.gz$")


def _orden(sti: Path) -> tuple[str, int]:
    m = _NAVN.match(sti.name)
    return (m.group(1), int(m.group(2) or 1)) if m else ("", 0)


def siste_kropp(kilde: str) -> Path | None:
    mappe = raw_arkiv.ARKIV_DIR / kilde
    filer = [p for p in mappe.glob("*.gz") if _NAVN.match(p.name)] \
        if mappe.exists() else []
    return max(filer, key=_orden) if filer else None


def daglige(kilde: str) -> set[str]:
    """Filnavnene daglige logger sier at de skrev."""
    ut = set()
    for sti in (raw_arkiv.ARKIV_DIR / kilde).glob("*.logg.json"):
        try:
            post = json.loads(sti.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if post.get("kjoring") == "daglig" and post.get("fil"):
            ut.add(post["fil"])
    return ut


def _sha(sti: Path) -> str:
    with gzip.open(sti, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def arkiver(kilde, dato: str, torr: bool) -> dict:
    """Én kilde: hent, sammenlign med siste lagrede, skriv hvis ny."""
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rå = kilde.fetch(dato)
    data, ext = raw_arkiv._serialiser(rå)
    sha = hashlib.sha256(data).hexdigest()

    forrige = siste_kropp(kilde.name)
    sammenlignet = None
    if forrige is not None:
        sammenlignet = {
            "fil": forrige.name, "sha256": _sha(forrige),
            "kjoring": "daglig" if forrige.name in daglige(kilde.name) else "ukentlig",
        }
    ny = sammenlignet is None or sammenlignet["sha256"] != sha

    post = {
        "kjoring": "daglig", "kilde": kilde.name, "observed_at": dato,
        "fetched_at": hentet, "sha256": sha, "byte": len(data),
        "status": "ny" if ny else "uendret", "sammenlignet_med": sammenlignet,
        "source_version": getattr(kilde, "version", ""),
        "utvalg": getattr(kilde, "utvalg", None),
        "published_at": getattr(kilde, "published_at", "") or "",
        "endepunkt": getattr(kilde, "endepunkt", "") or "",
        "advarsler": list(getattr(kilde, "advarsler", []) or []),
    }
    if ny and not torr:
        # Stien `arkiver()` vil velge, slått opp først så loggen kan si den.
        # Ingen andre skriver mappa mens dette kjører (se docstringen).
        sti = raw_arkiv._ledig_sti(kilde.name, dato, ext)
        skrevet = raw_arkiv.arkiver(kilde.name, dato, rå)
        assert skrevet == sha and sti.exists(), (kilde.name, sti, skrevet, sha)
        post["fil"] = sti.name
    return post


def skriv_logg(kilde: str, dato: str, post: dict) -> Path:
    mappe = raw_arkiv.ARKIV_DIR / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    sti, n = mappe / f"{dato}.logg.json", 2
    while sti.exists():
        sti, n = mappe / f"{dato}.{n}.logg.json", n + 1
    sti.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
    return sti


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for kroppene og loggene. Standard: i dag "
                        "(UTC). Slås opp her og sendes inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Daglig arkiv {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    proveniens: dict = {}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Det daglige arkivet startet ikke: {e}")
            return 1
        proveniens = {"kode_commit": sha, "kode_rent": tilstand}
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    kilder = {k.name: k for k in registry.discover()}
    feil = nye = 0
    for navn in KILDER:
        kilde = kilder.get(navn)
        try:
            if kilde is None or not hasattr(kilde, "fetch"):
                raise LookupError(f"fant ingen kilde som heter {navn!r}")
            post = arkiver(kilde, dato, a.torrkjor)
        except Exception as e:  # noqa: BLE001 — én kilde skal ikke koste de andre
            print(f"::error::Daglig arkiv: {navn} feilet: {type(e).__name__}: {e}")
            feil += 1
            continue
        for v in post["advarsler"]:
            print(f"::warning::{v}")
        nye += post["status"] == "ny"
        print(f"  {post['status'].upper() if post['status'] == 'ny' else post['status']:<8} "
              f"{navn:<12} {post['byte']:>9} B  {post['sha256'][:16]}…  mot "
              f"{(post['sammenlignet_med'] or {}).get('fil', 'ingenting')} "
              f"({(post['sammenlignet_med'] or {}).get('kjoring', '—')})")
        if not a.torrkjor:
            print(f"           logg {skriv_logg(navn, dato, dict(post, **proveniens)).name}")

    print(f"\n{len(KILDER)} kilde(r), {nye} ny(e) kropp(er), {feil} feil.")
    return 1 if feil else 0


if __name__ == "__main__":
    sys.exit(main())
