"""Skriver AIS-dagsmanifestene og -statusen fra kystvakt-1 inn i datarepoet.

    ssh utlevering@kystvakt-1 | python ais_manifest.py

Kjøres av ais-manifest.yml. Inn kommer JSON-en fra kystvakt/utlevering.py;
serveren har ingen skrivetilgang til repoene, så det er GitHub som henter
og denne som skriver. Rådataene havner aldri i git, bare sha256 per fil.

    data/arkiv/ais-manifest/<kilde>/<dato>.SHA256SUMS      én gang
    data/arkiv/ais-manifest/<kilde>/<dato>.<n>.SHA256SUMS  hvis det endret seg
    data/ais/status.json                                   hver kjøring

Manifestene ligger under data/arkiv/ og stemples av stempel.yml som alle
andre arkivfiler. Et manifest skrives aldri om (CLAUDE.md §2): sier
serveren noe annet om et døgn enn det som står, får det nye svaret neste
løpenummer, og begge blir stående. Det skal ikke skje for et lukket døgn,
og det er derfor det skal synes.

status.json overskrives, som health.json. Den er tilstand, ikke historikk,
og tilsyn.py leser den.

## En mistenkt utlevering (MALING-DRIFT F2.2, fra 03.11.2026)

Til 03.11.2026 ble `{"manifester": [], "skrevet": ""}` skrevet som ny
status med exit 0, og tilsynet fant det først neste morgen, med forrige
status overskrevet. Nå sjekkes HELE utleveringen før noe skrives:
`skrevet`, `disk` og `regnskap` med riktig type, `kopi_sist_ok` som et
tidspunkt eller null, og hvert manifest. Feiler noe, går kroppen slik den
kom i karantene (`data/arkiv/ais-manifest/karantene/`, core/karantene.py),
verken manifester eller status skrives, forrige status.json står, og
kjøringen ender med exit 1. Manifestene leveres på nytt i 30 døgn
(utlevering.py, MANIFEST_DOGN), så et døgn går ikke tapt av at én
utlevering ble holdt tilbake.

Bare standardbiblioteket og stdlib-modulene i core/: workflowen
installerer ingen pakker.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

from core import karantene
from core.paths import ARKIV_DIR, DATA_DIR

MANIFEST_DIR = ARKIV_DIR / "ais-manifest"
STATUS = DATA_DIR / "ais" / "status.json"
KILDE = re.compile(r"^[a-z0-9-]+$")
DATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIDSPUNKT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}Z$")
LINJE = re.compile(r"[0-9a-f]{64}  [^/\s][^/]*")


def _manifestfeil(kilde, dato, innhold) -> str | None:
    """Hva som er galt med ett manifest, eller None."""
    if not (isinstance(kilde, str) and KILDE.match(kilde)
            and isinstance(dato, str) and DATO.match(dato)):
        return f"ugyldig kilde/dato: {kilde!r} {dato!r}"
    if not isinstance(innhold, str):
        return f"{kilde}/{dato}: innholdet er ikke tekst"
    for linje in innhold.splitlines():
        if not LINJE.fullmatch(linje):
            return f"{kilde}/{dato}: uleselig manifestlinje {linje!r}"
    return None


def skriv_manifest(kilde: str, dato: str, innhold: str) -> Path | None:
    """Stien som ble skrevet, eller None når det samme svaret alt står."""
    feil = _manifestfeil(kilde, dato, innhold)
    if feil:
        raise ValueError(feil)
    mappe = MANIFEST_DIR / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    finnes = sorted(mappe.glob(f"{dato}.*SHA256SUMS"))
    if any(p.read_text() == innhold for p in finnes):
        return None
    kandidater = [mappe / f"{dato}.SHA256SUMS"] + [mappe / f"{dato}.{n}.SHA256SUMS"
                                                    for n in range(2, 1000)]
    for sti in kandidater:
        try:
            with open(sti, "x") as f:
                f.write(innhold)
            return sti
        except FileExistsError:
            continue
    raise RuntimeError(f"{kilde}/{dato}: tom for løpenummer")


def _tall(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _timer(v) -> bool:
    return isinstance(v, list) and all(isinstance(t, str) and TIME.match(t) for t in v)


def _per_time(v) -> bool:
    """{time: {"meldinger", "uten_mmsi"}} med ikke-negative heltall, og ikke
    flere uten MMSI enn meldinger. Fra utlevering.py 03.11.2026; eldre
    utleveringer har ikke feltet, og tilsynet sier fra om det selv."""
    def heltall(x):
        return isinstance(x, int) and not isinstance(x, bool) and x >= 0
    return isinstance(v, dict) and all(
        isinstance(t, str) and TIME.match(t) and isinstance(r, dict)
        and heltall(r.get("meldinger")) and heltall(r.get("uten_mmsi"))
        and r["uten_mmsi"] <= r["meldinger"]
        for t, r in v.items())


def feil_i(data) -> list[str]:
    """Hva som er galt med utleveringen. Tom liste: ingenting.

    Typene er de tilsyn.py leser: `skrevet` og `kopi_sist_ok` som
    tidspunkt, `disk.brukt_prosent` som tall, og `tomme` og `mangler` som
    timer. Et felt tilsynet ikke kan lese, gir det en `KeyError` om et
    døgn — her stoppes det før det overskriver noe."""
    if not isinstance(data, dict):
        return [f"utleveringen er ikke et JSON-objekt, men {type(data).__name__}"]
    ut = []
    if not (isinstance(data.get("skrevet"), str) and TIDSPUNKT.match(data["skrevet"])):
        ut.append(f"skrevet er ikke et UTC-tidspunkt: {data.get('skrevet')!r}")
    disk = data.get("disk")
    if not (isinstance(disk, dict) and _tall(disk.get("brukt_prosent"))
            and isinstance(disk.get("ledig_bytes"), int)
            and not isinstance(disk.get("ledig_bytes"), bool)):
        ut.append(f"disk mangler brukt_prosent eller ledig_bytes: {disk!r}")
    # Fraværende eller null leser tilsynet som «ingen kopi», og det er rødt
    # der. En annen type ville felt tilsynet selv.
    kopi = data.get("kopi_sist_ok")
    if kopi is not None and not (isinstance(kopi, str) and TIDSPUNKT.match(kopi)):
        ut.append(f"kopi_sist_ok er verken et tidspunkt eller null: {kopi!r}")
    regnskap = data.get("regnskap")
    if not (isinstance(regnskap, dict) and regnskap):
        ut.append(f"regnskap mangler: {regnskap!r}")
    else:
        for kilde, r in regnskap.items():
            if not (isinstance(r, dict) and _timer(r.get("timer"))
                    and len(r["timer"]) == 2 and _timer(r.get("tomme"))
                    and _timer(r.get("mangler"))):
                ut.append(f"regnskap for {kilde!r} har ikke timer, tomme og "
                          f"mangler som timer: {r!r}"[:300])
            elif "per_time" in r and not _per_time(r["per_time"]):
                ut.append(f"regnskap for {kilde!r} har per_time, men ikke som "
                          f"timer med meldinger og uten_mmsi: {r['per_time']!r}"[:300])
    manifester = data.get("manifester")
    if not isinstance(manifester, list):
        ut.append(f"manifester er ikke en liste: {type(manifester).__name__}")
    else:
        for m in manifester:
            if not isinstance(m, dict):
                ut.append(f"et manifest er ikke et objekt: {m!r}"[:300])
                continue
            feil = _manifestfeil(m.get("kilde"), m.get("dato"), m.get("innhold"))
            if feil:
                ut.append(feil)
    return ut


def main() -> int:
    kropp = sys.stdin.buffer.read()
    try:
        data = json.loads(kropp)
    except ValueError as e:
        grunner = [f"ikke gyldig JSON: {e}"]
    else:
        grunner = feil_i(data)
    if grunner:
        # Dagen VI tok imot den (1b-7: OSS). Slått opp ett sted, her.
        dato = dt.datetime.now(dt.timezone.utc).date().isoformat()
        karantene.sett_inn("ais-manifest", dato, kropp, grunner, jobb="ais-manifest")
        print(f"::error::AIS-manifest: utleveringen er ikke skrevet. Forrige "
              f"{STATUS.name} står, og manifestene leveres på nytt i morgen.")
        return 1
    nye = [s for m in data["manifester"]
           if (s := skriv_manifest(m["kilde"], m["dato"], m["innhold"]))]
    status = {k: v for k, v in data.items() if k != "manifester"}
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1) + "\n")
    for s in nye:
        print(f"[ny] {s.relative_to(DATA_DIR)}")
    print(f"{len(nye)} nye manifester, status {status['skrevet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
