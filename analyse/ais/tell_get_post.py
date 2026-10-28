"""Holder GET /v1/ais mot POST /v1/ais med downsample=false, fanget samtidig
av fang_bw.py i fem minutter. Er GET nedsamplet, og er den en del av POST?

    .venv/bin/python -m analyse.ais.tell_get_post <get.txt|.gz> <full.txt|.gz>

Utskriften er tabellen for F2.8 i docs/MALING-AIS.md.
"""
import hashlib
import json
import statistics
import sys
from collections import Counter
from compression import zstd
from datetime import datetime

from analyse.ais.tell import les


def iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def les_strom(kropp: bytes):
    linjer, mottatt = [], []
    for r in kropp.split(b"\n"):
        if r:
            t, _, l = r.partition(b"\t")
            linjer.append(l)
            mottatt.append(iso(t.decode()))
    return linjer, mottatt


def main():
    kropper = {"GET": les(sys.argv[1]), "POST full": les(sys.argv[2])}
    data = {}
    for navn, k in kropper.items():
        linjer, mottatt = les_strom(k)
        meldinger = [json.loads(l) for l in linjer]
        varighet = mottatt[-1] - mottatt[0]
        pos = Counter(m["mmsi"] for m in meldinger if m["type"] == "Position")
        data[navn] = (linjer, meldinger, varighet, pos)
        kilde = sum(len(l) + 1 for l in linjer)
        z = len(zstd.compress(k, 19))
        print(f"== {navn}  sha256 {hashlib.sha256(k).hexdigest()}")
        print(f"   meldinger {len(linjer):8d}  på {varighet:.0f} s  = {len(linjer) / varighet * 60:7.0f} per minutt")
        print("   type      " + ", ".join(f"{a}:{b}" for a, b in Counter(m["type"] for m in meldinger).most_common()))
        print(f"   MMSI med posisjon {len(pos):6d}  posisjoner per MMSI median {statistics.median(pos.values()):.0f}"
              f"  maks {max(pos.values())}")
        print(f"   bytes fra kilden {kilde:10d}  = {kilde / varighet * 3600 / 1e6:7.1f} MB/time"
              f"  zstd -19 {z / varighet * 86400 / 1e6:7.1f} MB/døgn (hel ramme)")
    gl, gm, _, gpos = data["GET"]
    fl, fm, _, fpos = data["POST full"]
    fset = set(fl)
    nokkel = lambda m: (m["mmsi"], m["msgtime"], m["type"], m.get("messageType"))
    fn = set(map(nokkel, fm))
    print("== GET mot POST full")
    print(f"   GET-linjer som finnes byte for byte i POST   {sum(1 for l in gl if l in fset):8d} av {len(gl)}")
    print(f"   GET-meldinger med samme mmsi/msgtime/type i POST {sum(1 for m in gm if nokkel(m) in fn):8d} av {len(gm)}")
    print(f"   MMSI med posisjon bare i GET                 {len(set(gpos) - set(fpos)):8d}")
    print(f"   MMSI med posisjon bare i POST                {len(set(fpos) - set(gpos)):8d}")


if __name__ == "__main__":
    main()
