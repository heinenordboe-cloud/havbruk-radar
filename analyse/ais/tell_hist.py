"""Teller en henting fra historikk-API-et (hist_bw.py) og holder den mot
strømmen fanget av fang_bw.py: hva kostet det, og dekker det timen?

    .venv/bin/python -m analyse.ais.tell_hist <hist.jsonl|.gz> <bw.txt|.gz> <fra> <til>

Dekning måles på posisjonsrapporter: (MMSI, msgtime) i strømmen innenfor
[fra, til), og hvor mange av dem historikken også har. Historikk-API-et
gir bare posisjoner (AisComboSimple), så Staticdata, Aton og MetHyd
telles ikke med. Utskriften er tabellen i tillegget i docs/MALING-AIS.md.
"""
import hashlib
import json
import statistics
import sys
from collections import Counter
from datetime import datetime

from analyse.ais.tell import les, pst


def iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def main():
    hist = les(sys.argv[1])
    bw = les(sys.argv[2])
    fra, til = iso(sys.argv[3]), iso(sys.argv[4])

    rader = [json.loads(l) for l in hist.split(b"\n") if l]
    spor = [r for r in rader if r["kall"].startswith("tracks")]
    liste = next(r for r in rader if r["kall"] == "mmsiinarea")
    status = Counter(r["status"] for r in spor)
    s = [r["s"] for r in spor]
    t0, t1 = iso(rader[0]["t"]), iso(rader[-1]["t"])

    h_pos, h_strom, h_mmsi = set(), Counter(), set()
    for r in spor:
        if r["status"] != 200:
            continue
        for p in json.loads(r["body"]):
            h_pos.add((int(p["mmsi"]), iso(p["msgtime"])))
            h_strom[p.get("stream")] += 1
            h_mmsi.add(int(p["mmsi"]))

    l_pos, l_strom, l_mmsi = {}, Counter(), set()
    for linje in bw.split(b"\n"):
        if not linje:
            continue
        d = json.loads(linje.partition(b"\t")[2])
        if d.get("type") != "Position":
            continue
        mt = iso(d["msgtime"])
        if fra <= mt < til:
            l_pos[(int(d["mmsi"]), mt)] = d.get("stream")
            l_mmsi.add(int(d["mmsi"]))

    funnet = Counter()
    for k, st in l_pos.items():
        funnet[(st, k in h_pos)] += 1
    i_vindu = {k for k in h_pos if fra <= k[1] < til}

    print(f"historikk sha256                 {hashlib.sha256(hist).hexdigest()}")
    print(f"strøm sha256                     {hashlib.sha256(bw).hexdigest()}")
    print(f"vindu                            {sys.argv[3]} – {sys.argv[4]}")
    print(f"mmsiinarea: MMSI                 {len(json.loads(liste['body'])):10d}")
    print(f"mmsiinarea: sekunder             {liste['s']:10.2f}")
    print(f"sporkall                         {len(spor):10d}  status {dict(status)}")
    print(f"sporkall: s median / p99 / maks  {statistics.median(s):.3f} / {pst(s, 99):.3f} / {max(s):.3f}")
    print(f"sporkall: sum kalltid            {sum(s):10.0f} s")
    print(f"veggtid hele hentingen           {t1 - t0:10.0f} s  (med pause mellom kall)")
    print(f"bytes i svarene                  {sum(len(r['body'].encode()) for r in rader):10d}")
    print(f"posisjoner i historikken         {len(h_pos):10d}  i vinduet {len(i_vindu)}")
    print("  stream                         " + ", ".join(f"{k}:{v}" for k, v in h_strom.most_common()))
    print(f"MMSI med posisjoner              {len(h_mmsi):10d}")
    print()
    print(f"posisjoner i strømmen i vinduet  {len(l_pos):10d}  MMSI {len(l_mmsi)}")
    alle = sum(funnet.values())
    treff = sum(v for (st, ja), v in funnet.items() if ja)
    print(f"  av dem i historikken           {treff:10d}  {treff / alle:7.2%}")
    for st in sorted({st for st, _ in funnet}, key=str):
        ja, nei = funnet[(st, True)], funnet[(st, False)]
        print(f"  stream={st!s:10s}             {ja:8d} av {ja + nei:8d}  {ja / (ja + nei):7.2%}")
    med_spor = {k: st for k, st in l_pos.items() if k[0] in h_mmsi}
    t2 = sum(1 for k in med_spor if k in h_pos)
    print(f"  for MMSI med spor: i historikken {t2:8d} av {len(med_spor):8d}  {t2 / max(1, len(med_spor)):7.2%}")
    nede = [k for k in med_spor if k not in h_pos]
    if nede:
        # hvor tett ligger de manglende på dem historikken har, per fartøy?
        hist_per = {}
        for m, t in h_pos:
            hist_per.setdefault(m, []).append(t)
        avst = [min(abs(t - x) for x in hist_per[m]) for m, t in nede]
        print(f"  manglende: s til nærmeste i historikken  median {statistics.median(avst):.0f}  p90 {pst(avst, 90):.0f}")
    print(f"historikkens posisjoner i vinduet som finnes i strømmen  "
          f"{len(i_vindu & set(l_pos)):d} av {len(i_vindu)}")
    print(f"MMSI i strømmen, ikke i listen   {len(l_mmsi - set(json.loads(liste['body']))):10d}")
    print(f"MMSI i strømmen uten spor        {len(l_mmsi - h_mmsi):10d}")


if __name__ == "__main__":
    main()
