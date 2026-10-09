"""Arkiverer Mattilsynets kropper for analysen av unntaksvekst.

    python arkiver_mattilsynet.py liste            # søknadslista, via kilden
    python arkiver_mattilsynet.py liste --torrkjor

Kjøres for hånd, ikke av en workflow. Se docs/ANALYSE-UNNTAKSVEKST.md.

## Hvorfor dette ikke er run.py

`unntaksvekst` er en ukentlig kilde, og mandagens kjøring skriver den
første versjonen av lista til `data/arkiv/unntaksvekst/` sammen med et
snapshot. Analysen trenger lista NÅ, og den trenger den med hash.

`run.py --bare unntaksvekst` ville skrevet mer enn lista: helsetilstand,
endringslogg for dagen, og en dom over hvert anslag i `predictions/` med
vindu som lukker i dag — på en fredag, uten resten av ukas kilder. Det er
ikke denne analysens sak å gjøre.

Her kalles derfor KILDENS EGEN `fetch()`, og svaret arkiveres under
kildens navn og datoen kilden selv oppgir, slik `runner.run_all()` gjør.
Ingen kobling skrives om: søkerfilteret og lokalitetskoblingen er
kildens, og de er det analysen bruker («bruk de entydige koblingene fra
kilden»). En arkivfil uten snapshot er lov — se `core/raw.py`.

## Kodeproveniens

Som de andre arkivskriptene: `kodeproveniens.krev_sporbar()` før noe
hentes, og `kode_commit`, `kode_rent` og `fetched_at` i sidevogna
`data/arkiv/mattilsynet/<dato>.logg.json`. `--torrkjor` skriver ingen fil
og er unntatt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from core import kodeproveniens
from core import raw as raw_arkiv
from sources.unntaksvekst import KOBLET, Unntaksvekst

LOGG_KILDE = "mattilsynet"


def _logg(dato: str, poster: list[dict]) -> None:
    mappe = raw_arkiv.ARKIV_DIR / LOGG_KILDE
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / f"{dato}.logg.json"
    n = 2
    while sti.exists():
        sti = mappe / f"{dato}.{n}.logg.json"
        n += 1
    sti.write_text(json.dumps(poster, indent=2, ensure_ascii=False))
    print(f"Logg: {sti}")


def liste(kjoredato: str, torr: bool, proveniens: dict) -> int:
    """Søknadslista via `Unntaksvekst.fetch()`, arkivert under kildens navn."""
    kilde = Unntaksvekst()
    gjelder = kilde.gjelder_for(kjoredato)
    raw = kilde.fetch(kjoredato)
    rader = raw["rader"]
    koblet = sum(r["kobling"] in KOBLET for r in rader)
    print(f"  {len(rader)} rader, {koblet} med entydig lokalitet, "
          f"kropp sha256 {raw['sha256'][:16]}…")
    for a in kilde.advarsler:
        print(f"::warning::{a}")
    if torr:
        print("  TØRRKJØRING — ingenting skrevet.")
        return 0

    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sha, ny = raw_arkiv.arkiver_ny(kilde.name, gjelder, raw)
    print(f"  {'NY' if ny else 'uendret':<8} unntaksvekst/{gjelder}  "
          f"sha256 {sha[:16]}…")
    _logg(gjelder, [{
        "hva": "liste", "kilde": kilde.name, "url": raw["url"],
        "observed_at": gjelder, "sha256": sha, "ny": ny,
        "kropp_sha256": raw["sha256"], "kropp_byte": raw["bytes"],
        "headere": raw["headere"], "rader": len(rader), "koblet": koblet,
        "source_version": kilde.version, "published_at": "",
        "fetched_at": hentet, **proveniens}])
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("hva", choices=("liste",))
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="kjøredatoen. Standard: i dag. Sendes inn og leses "
                        "ikke av noen underfunksjon (1b).")
    a = p.parse_args(argv)

    kjoredato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Mattilsynet-arkivering {kjoredato}: {a.hva}"
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    proveniens: dict = {}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Mattilsynet-arkiveringen startet ikke: {e}")
            return 1
        proveniens = {"kode_commit": sha, "kode_rent": tilstand}
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    return liste(kjoredato, a.torrkjor, proveniens)


if __name__ == "__main__":
    sys.exit(main())
