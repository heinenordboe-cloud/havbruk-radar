"""Teller en døgnhenting fra historikk-API-et (hist_bw.py) linje for linje,
og holder timen i den mot strømmen. For en fil som er større enn minnet
på kystvakt-1: bare standardbiblioteket, og bare timens nøkler i minnet.

    python3 tell_hist_dogn.py <dogn.jsonl> <bw.txt> <time fra> <time til> <time.jsonl>

Kjøres på serveren; kroppen er for stor til datarepoet (935 MB for ett
døgn), så tallene herfra er MÅLBAR, ikke MÅLT, i docs/MALING-AIS.md.
"""
import hashlib
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone


def iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def main():
    hist_sti, bw_sti, fra, til = sys.argv[1], sys.argv[2], iso(sys.argv[3]), iso(sys.argv[4])
    sha = hashlib.sha256()
    status, s, strom, mmsi_med = Counter(), [], Counter(), set()
    t_forste = t_siste = None
    liste = None
    posisjoner = 0
    bytes_ = 0
    timen = set()
    tidligst = senest = None
    with open(hist_sti, "rb") as f:
        for linje in f:
            sha.update(linje)
            r = json.loads(linje)
            t_forste = t_forste or r["t"]
            t_siste = r["t"]
            bytes_ += len(r["body"].encode())
            if r["kall"] == "mmsiinarea":
                liste = (len(json.loads(r["body"])), r["s"])
            if not r["kall"].startswith("tracks"):
                continue
            status[r["status"]] += 1
            s.append(r["s"])
            if r["status"] != 200:
                continue
            for p in json.loads(r["body"]):
                posisjoner += 1
                strom[p.get("stream")] += 1
                mmsi_med.add(int(p["mmsi"]))
                t = iso(p["msgtime"])
                tidligst = t if tidligst is None else min(tidligst, t)
                senest = t if senest is None else max(senest, t)
                if fra <= t < til:
                    timen.add((int(p["mmsi"]), t))

    l_pos = set()
    with open(bw_sti, "rb") as f:
        for linje in f:
            d = json.loads(linje.partition(b"\t")[2])
            if d.get("type") == "Position":
                t = iso(d["msgtime"])
                if fra <= t < til:
                    l_pos.add((int(d["mmsi"]), t))

    s.sort()
    print(f"historikk sha256 (fila på serveren)  {sha.hexdigest()}")
    print(f"mmsiinarea: MMSI                 {liste[0]:10d}")
    print(f"mmsiinarea: sekunder             {liste[1]:10.2f}")
    print(f"sporkall                         {sum(status.values()):10d}  status {dict(status)}")
    print(f"sporkall: s median / p99 / maks  {statistics.median(s):.3f} / "
          f"{s[min(len(s) - 1, int(0.99 * len(s)))]:.3f} / {s[-1]:.3f}")
    print(f"sporkall: sum kalltid            {sum(s):10.0f} s")
    print(f"veggtid hele hentingen           {iso(t_siste) - iso(t_forste):10.0f} s")
    print(f"bytes i svarene                  {bytes_:10d}")
    print(f"posisjoner                       {posisjoner:10d}")
    print("  stream                         " + ", ".join(f"{k}:{v}" for k, v in strom.most_common()))
    print(f"MMSI med posisjoner              {len(mmsi_med):10d}")
    print(f"tidligste / seneste msgtime      {datetime.fromtimestamp(tidligst, timezone.utc):%Y-%m-%dT%H:%M:%S} / "
          f"{datetime.fromtimestamp(senest, timezone.utc):%Y-%m-%dT%H:%M:%S}")
    print()
    print(f"timen {sys.argv[3]} – {sys.argv[4]}")
    print(f"  posisjoner i døgnhentingen     {len(timen):10d}")
    print(f"  posisjoner i strømmen (GET)    {len(l_pos):10d}")
    print(f"  felles                         {len(timen & l_pos):10d}")
    tim = {}
    with open(sys.argv[5], "rb") as f:
        for linje in f:
            r = json.loads(linje)
            if r["kall"].startswith("tracks") and r["status"] == 200:
                for p in json.loads(r["body"]):
                    t = iso(p["msgtime"])
                    if fra <= t < til:
                        tim[(int(p["mmsi"]), t)] = 1
    print(f"  posisjoner i timehentingen     {len(tim):10d}")
    print(f"  felles døgn og time            {len(timen & set(tim)):10d}")


if __name__ == "__main__":
    main()
