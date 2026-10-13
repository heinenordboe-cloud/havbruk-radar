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

  * Kroppen skrives til `data/arkiv/<kilde>/<dato>.daglig.<ext>.gz`
    (`<dato>.daglig.2.<ext>.gz` osv.) BARE når sha256 av den kanoniske
    formen (se Akvakultur under) avviker fra siste lagrede kropp for
    kilden, daglig eller ukentlig. Det som skrives, er den rå kroppen. Merket `daglig` er
    `core.raw.DAGLIG`; det skiller navnene fra innsamlingens, se under.
  * Loggfila `data/arkiv/<kilde>/<dato>.daglig.logg.json` skrives hver
    kjøring, med løpenummer hvis den finnes: `kjoring: daglig`, sha256
    rå og kanonisk,
    når vi hentet, `ny` eller `uendret`, og hvilken kropp den ble
    sammenlignet med — og om DEN var daglig eller ukentlig, lest av
    merket i filnavnet.

Ingen snapshot, ingen changelog, og health.json røres ikke: dette er
råarkiv, ikke innsamling. `core/` er uendret. `data/kvitteringer/` er
portens og brukes ikke her.

## Siste lagrede kropp

`core.raw.kropper()`, i `raw.orden()`: dato, så innsamlingens før den
daglige samme dato, så løpenummer. F14 er grunnen til å nevne det:
filnavnet er en stedfortreder for rekkefølge, og arkivinnsetting brøt den
for biomasse. For kildene her er `gjelder_for()` kjøredatoen, så datoen
i navnet ER dagen kroppen ble hentet — og blir den likevel feil, mister
vi ingenting: hver daglig logg har sha256 for det vi fikk, også når det
var uendret. En feil «siste» gir i verste fall en kropp for mye, eller
en kropp som ikke skrives fordi de samme bytene allerede ligger der.

## Akvakultur: sammenlignet på kanonisk form

MÅLT 13.10.2026, to hentinger 20 sekunder fra hverandre og en tredje en
time senere: 1780 lokaliteter, samme lengde, ulik sha256 hver gang. Eneste
forskjell var rekkefølgen i `speciesTypes`. Byte for byte ville regelen
over skrevet ~450 kB hver dag.

Kroppen sammenlignes derfor på en kanonisk form der listene i `UORDNET`
er sortert, og den RÅ kroppen lagres når den kanoniske sha256 avviker fra
den forrige lagrede sin. Loggen fører begge.

Hvilke lister: MÅLT 13.10.2026 kl. 21.23–21.25 UTC, tre hentinger 60 s fra
hverandre, hver liste i hver lokalitet sammenlignet: `speciesTypes`
varierte i rekkefølge for 127 av 1780 (201 har mer enn ett element);
`connections` (1284 med >1), `obsoleteConnections` (645) og
`speciesLimitations` (1) var like i alle tre, og lokalitetene selv sto i
samme rekkefølge. Mot ukekroppene 28.09, 05.10 og 12.10 og hentingen
13.10, 1779 felles lokaliteter: `speciesTypes` skilte seg 406 ganger bare
i rekkefølge og aldri i innhold; de tre andre skilte seg aldri bare i
rekkefølge (18/157/7 ganger i innhold — det er endringer). Kanonisk sha256
var lik for alle tre hentingene (0931916b…).

## Samtidig med innsamlingen

`samle.yml` skriver de samme mappene fra sin egen checkout. Fram til
13.10.2026 kunne begge valgt `<dato>.json.gz` samme dag, og rebasen ville
stoppet på konflikten tre ganger på rad. Nå skriver innsamlingen aldri et
navn med `.daglig.`, og dette skriptet aldri et uten: filnavnene er
disjunkte, og `samle.yml` holder `*.daglig.*` utenfor sin `git add`. Se
`.github/jobber.yml` i datarepoet.

`daglig.yml` venter fortsatt til ingen innsamling kjører og tar inn main
før skriptet kjører — ikke for å unngå navnet, men så innsamlingens kropp
er den siste lagrede når det sammenlignes.

## Kodeproveniens

Som `arkiver_vilkar.py`: `kodeproveniens.krev_sporbar()` før noe hentes,
og `kode_commit`/`kode_rent` i hver logg. `--torrkjor` er unntatt.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path

from core import kodeproveniens
from core import raw as raw_arkiv
from core import registry

# Kildene som arkiveres daglig. Navnet er kildens `name`.
KILDER = ("eierskap", "biomasselag", "akvakultur")

# Lister uten meningsbærende rekkefølge, per post i kroppen. Sorteres i den
# kanoniske formen som sammenlignes; den lagrede kroppen er rå. MÅLT, ikke
# antatt — se «Akvakultur» i docstringen. En kilde som ikke står her,
# sammenlignes byte for byte.
UORDNET = {"akvakultur": ("speciesTypes",)}

def siste_kropp(kilde: str) -> Path | None:
    """Siste lagrede kropp, innsamlingens eller daglig (`raw.orden()`)."""
    filer = raw_arkiv.kropper(kilde)
    return filer[-1] if filer else None


def kanonisk_sha(kilde: str, data: bytes) -> str:
    """sha256 av den kanoniske formen: kroppen med listene i `UORDNET`
    sortert, serialisert som `core.raw` gjør. For en kilde uten slike
    lister er den lik sha256 av kroppen.

    Leser bytene, ikke objektet `fetch()` ga: den lagrede kroppen og den
    nye går da gjennom nøyaktig samme vei."""
    felt = UORDNET.get(kilde, ())
    if not felt:
        return hashlib.sha256(data).hexdigest()
    poster = json.loads(data)
    for post in poster:
        for navn in felt:
            if isinstance(post.get(navn), list):
                post[navn] = sorted(post[navn], key=lambda x: json.dumps(
                    x, ensure_ascii=False, sort_keys=True))
    return hashlib.sha256(raw_arkiv._serialiser(poster)[0]).hexdigest()


def arkiver(kilde, dato: str, torr: bool) -> dict:
    """Én kilde: hent, sammenlign med siste lagrede, skriv hvis ny.

    Sammenligningen er på den kanoniske formen; det som skrives, er den
    rå kroppen. Begge sha256 står i loggen."""
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rå = kilde.fetch(dato)
    data, ext = raw_arkiv._serialiser(rå)
    sha = hashlib.sha256(data).hexdigest()
    kanon = kanonisk_sha(kilde.name, data)

    forrige = siste_kropp(kilde.name)
    sammenlignet = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            lagret = f.read()
        sammenlignet = {
            "fil": forrige.name, "sha256": hashlib.sha256(lagret).hexdigest(),
            "sha256_kanonisk": kanonisk_sha(kilde.name, lagret),
            "kjoring": "daglig" if raw_arkiv.merke(forrige.name) == raw_arkiv.DAGLIG
                       else "ukentlig",
        }
    ny = sammenlignet is None or sammenlignet["sha256_kanonisk"] != kanon

    post = {
        "kjoring": "daglig", "kilde": kilde.name, "observed_at": dato,
        "fetched_at": hentet, "sha256": sha, "sha256_kanonisk": kanon,
        "kanonisk_sorterer": list(UORDNET.get(kilde.name, ())),
        "byte": len(data),
        "status": "ny" if ny else "uendret", "sammenlignet_med": sammenlignet,
        "source_version": getattr(kilde, "version", ""),
        "utvalg": getattr(kilde, "utvalg", None),
        "published_at": getattr(kilde, "published_at", "") or "",
        "endepunkt": getattr(kilde, "endepunkt", "") or "",
        "advarsler": list(getattr(kilde, "advarsler", []) or []),
    }
    if ny and not torr:
        # Stien `arkiver()` vil velge, slått opp først så loggen kan si den.
        # Bare dette skriptet skriver `.daglig.`-navn (se docstringen).
        sti = raw_arkiv._ledig_sti(kilde.name, dato, ext, raw_arkiv.DAGLIG)
        skrevet = raw_arkiv.arkiver(kilde.name, dato, rå, raw_arkiv.DAGLIG)
        assert skrevet == sha and sti.exists(), (kilde.name, sti, skrevet, sha)
        post["fil"] = sti.name
    return post


def skriv_logg(kilde: str, dato: str, post: dict) -> Path:
    mappe = raw_arkiv.ARKIV_DIR / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    stamme = f"{dato}.{raw_arkiv.DAGLIG}"
    sti, n = mappe / f"{stamme}.logg.json", 2
    while sti.exists():
        sti, n = mappe / f"{stamme}.{n}.logg.json", n + 1
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
