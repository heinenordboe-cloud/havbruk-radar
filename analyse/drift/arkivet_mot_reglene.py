"""MALING-DRIFT, økt 3b punkt 10: ville en ekte kropp i arkivet gått i karantene?

    .venv/bin/python analyse/drift/arkivet_mot_reglene.py > analyse/drift/arkivet_mot_reglene.txt

Hver regel fra punkt 2–9 holdt mot hver kropp i arkivet den gjelder for,
med jobbens egen kode (reglene, ikke en kopi av dem). Kroppene leses i
`raw.orden()`, og der regelen sammenligner med forrige kropp, er forrige
den som ligger foran i samme rekkefølge — slik jobben ville sett den.

    vilkar         vilkar-<part>/: regler() mot forrige versjon, eller
                   minstelengden for den første
    havbruksfond   havbruksfondet/: kroppene loggene kaller «side»
    auksjon        auksjon/: alle
    luseinnkomst   lusetall-innkomst/: mistenkt() per uke mot forrige kropp
    eierskap       eierskap/: null tillatelser, innsamlingens og de daglige
    sjotemperatur  sjotemperatur/: _les_csv() på hver kropp
    ais-manifest   data/ais/status.json i hver commit i datarepoet

Per jobb: antall kropper, hvor mange som ville gått i karantene, og
sha256 over én linje per kropp, `<sti fra data/arkiv/> <sha256>\n`, i
den rekkefølgen kroppene leses (partene i SIDER-rekkefølge for vilkar,
`raw.orden()` i hver mappe) — så samme grunnlag kan kjennes igjen.
Ingenting skrives.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
DATAREPO = ROT.parent / "havbruk-radar-data"
ARKIV = DATAREPO / "data" / "arkiv"
sys.path.insert(0, str(ROT))

import ais_manifest  # noqa: E402
import arkiver_auksjon  # noqa: E402
import arkiver_havbruksfond  # noqa: E402
import arkiver_luseinnkomst  # noqa: E402
import arkiver_vilkar  # noqa: E402
from core import karantene, raw as raw_arkiv  # noqa: E402
from sources import sjotemperatur  # noqa: E402

raw_arkiv.ARKIV_DIR = ARKIV


def les(p: Path) -> bytes:
    with gzip.open(p, "rb") as f:
        return f.read()


class Telling:
    def __init__(self, jobb: str):
        self.jobb, self.n, self.treff, self.h = jobb, 0, [], hashlib.sha256()

    def kropp(self, navn: str, data: bytes, grunner: list[str]) -> None:
        self.n += 1
        self.h.update(f"{navn} {hashlib.sha256(data).hexdigest()}\n".encode())
        if grunner:
            self.treff.append((navn, grunner))

    def skriv(self) -> None:
        print(f"  {self.jobb:<14} {self.n:>5} kropper, {len(self.treff)} ville gått i "
              f"karantene   sha256 {self.h.hexdigest()}")
        for navn, grunner in self.treff:
            print(f"      {navn}: {'; '.join(grunner)}")


def vilkar() -> Telling:
    t = Telling("vilkar")
    for part in arkiver_vilkar.SIDER:
        forrige = None
        for p in raw_arkiv.kropper(arkiver_vilkar.kilde(part)):
            b = les(p)
            regler = ([karantene.ikke_tom, karantene.minst_tekst(arkiver_vilkar.MINSTE_TEKST)]
                      if forrige is None else
                      [karantene.ikke_tom,
                       karantene.andel_av_forrige(forrige, arkiver_vilkar.ANDEL_AV_FORRIGE),
                       karantene.nevner(arkiver_vilkar.KJENNETEGN[part])])
            t.kropp(f"vilkar-{part}/{p.name}", b, karantene.vurder(b, regler))
            forrige = b
    return t


def havbruksfond() -> Telling:
    t = Telling("havbruksfond")
    sider = set()
    for lg in sorted((ARKIV / "havbruksfondet").glob("*.logg.json")):
        sider |= {r["sha256"] for r in json.loads(lg.read_text())
                  if r.get("hva") == "side" and r.get("sha256")}
    for p in raw_arkiv.kropper("havbruksfondet"):
        b = les(p)
        if hashlib.sha256(b).hexdigest() in sider:
            t.kropp(f"havbruksfondet/{p.name}", b,
                    karantene.vurder(b, arkiver_havbruksfond.SIDE_REGLER))
    return t


def auksjon() -> Telling:
    t = Telling("auksjon")
    for p in raw_arkiv.kropper("auksjon"):
        b = les(p)
        t.kropp(f"auksjon/{p.name}", b, karantene.vurder(b, arkiver_auksjon.REGLER))
    return t


def luseinnkomst() -> Telling:
    t = Telling("luseinnkomst")
    forrige: dict[str, bytes] = {}
    for p in raw_arkiv.kropper(arkiver_luseinnkomst.MAPPE):
        b, mandag = les(p), raw_arkiv.orden(p)[0]
        aar, uke = __import__("datetime").date.fromisoformat(mandag).isocalendar()[:2]
        t.kropp(f"lusetall-innkomst/{p.name}", b,
                arkiver_luseinnkomst.mistenkt(json.loads(b), forrige.get(mandag), aar, uke))
        forrige[mandag] = b
    return t


def eierskap() -> Telling:
    t = Telling("eierskap")
    for p in raw_arkiv.kropper("eierskap"):
        b = les(p)
        d = json.loads(b)
        t.kropp(f"eierskap/{p.name}", b,
                [] if d.get("tillatelser") else ["null tillatelser"])
    return t


def sjotemp() -> Telling:
    t = Telling("sjotemperatur")
    for p in raw_arkiv.kropper("sjotemperatur"):
        b = les(p)
        try:
            sjotemperatur._les_csv(b.decode("utf-8"))
            grunner = []
        except sjotemperatur.Kolonnefeil as e:
            grunner = [str(e)[:120]]
        t.kropp(f"sjotemperatur/{p.name}", b, grunner)
    return t


def ais() -> Telling:
    t = Telling("ais-manifest")
    shaer = subprocess.run(["git", "-C", str(DATAREPO), "log", "--format=%H", "--",
                            "data/ais/status.json"], capture_output=True, text=True,
                           check=True).stdout.split()
    for sha in shaer:
        b = subprocess.run(["git", "-C", str(DATAREPO), "show", f"{sha}:data/ais/status.json"],
                           capture_output=True, check=True).stdout
        data = dict(json.loads(b), manifester=[])
        t.kropp(f"data/ais/status.json@{sha[:12]}", b, ais_manifest.feil_i(data))
    return t


def main() -> None:
    print("De nye reglene mot hver kropp i arkivet de gjelder for (økt 3b punkt 10)")
    print(f"arkiv: {ARKIV}\n")
    for f in (vilkar, havbruksfond, auksjon, luseinnkomst, eierskap, sjotemp, ais):
        f().skriv()


if __name__ == "__main__":
    main()
