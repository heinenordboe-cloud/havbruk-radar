"""Teller en rå AIS-fangst fra fang.py: volum, dekoding, TAG-blokker,
stasjoner og forsinkelse mellom kildens c: og vår mottakstid.

    .venv/bin/python -m analyse.ais.tell <fangst.txt|.gz> [hendelser.jsonl]

Leser kroppen slik den ligger i arkivet. Ingenting her er gjettet fra
dokumentasjon: hvert tall er talt i fila. Utskriften er tabellene i
docs/MALING-AIS.md, uendret.
"""
import gzip
import hashlib
import json
import statistics
import sys
from collections import Counter
from compression import zstd
from datetime import datetime

from pyais.exceptions import InvalidNMEAMessageException, UnknownMessageException
from pyais.messages import NMEASentenceFactory
from pyais.stream import IterMessages


def les(sti):
    with (gzip.open if str(sti).endswith(".gz") else open)(sti, "rb") as f:
        return f.read()


def ts(b: bytes) -> float:
    return datetime.fromisoformat(b.decode().replace("Z", "+00:00")).timestamp()


def tagfelt(linje: bytes) -> dict | None:
    """TAG-blokka er `\\k:v,k:v*hh\\` foran setningen. None hvis ingen."""
    if not linje.startswith(b"\\"):
        return None
    slutt = linje.find(b"\\", 1)
    if slutt < 0:
        return None
    kropp = linje[1:slutt].split(b"*")[0]
    ut = {}
    for del_ in kropp.split(b","):
        k, _, v = del_.partition(b":")
        ut[k.decode()] = v.decode(errors="replace")
    return ut


def fragmentnr(linje: bytes) -> int:
    """Fragmentnummeret i !AIVDM,<antall>,<nr>,... etter TAG-blokka."""
    setning = linje[linje.rfind(b"\\") + 1:] if linje.startswith(b"\\") else linje
    return int(setning.split(b",")[2])


def pst(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def main():
    kropp = les(sys.argv[1])
    hendelser = []
    if len(sys.argv) > 2:
        hendelser = [json.loads(l) for l in open(sys.argv[2])]

    rader = kropp.split(b"\n")
    if rader and rader[-1] == b"":
        rader.pop()
    mottatt, linjer = [], []
    for r in rader:
        t, _, linje = r.partition(b"\t")
        mottatt.append(ts(t))
        linjer.append(linje + b"\n")  # terminatoren slik kilden sendte den
    kilde = b"".join(linjer)

    start = [h for h in hendelser if h["hendelse"] == "start"]
    ferdig = [h for h in hendelser if h["hendelse"] == "ferdig"]
    if start and ferdig:
        t0 = ts(start[0]["t"].encode()); t1 = ts(ferdig[-1]["t"].encode())
    else:
        t0, t1 = mottatt[0], mottatt[-1]
    varighet = t1 - t0

    # Setningsnivå
    gyldig = ugyldig_sjekksum = uparsbar = 0
    enkelt = flerdel_start = 0
    for l in linjer:
        try:
            s = NMEASentenceFactory.produce(l.rstrip(b"\r\n"))
        except (InvalidNMEAMessageException, UnknownMessageException, Exception):
            uparsbar += 1
            continue
        if not s.is_valid:
            ugyldig_sjekksum += 1
        else:
            gyldig += 1
        if getattr(s, "frag_cnt", 1) == 1:
            enkelt += 1
        elif s.frag_num == 1:
            flerdel_start += 1
    forventet = enkelt + flerdel_start

    # Meldingsnivå: pyais setter sammen flerdelte og dekoder
    satt_sammen = dekodet = 0
    mmsi = set()
    typer = Counter()
    for m in IterMessages([l.rstrip(b"\r\n") for l in linjer]):
        satt_sammen += 1
        try:
            d = m.decode()
        except Exception:
            continue
        dekodet += 1
        typer[d.msg_type] += 1
        if getattr(d, "mmsi", None):
            mmsi.add(int(d.mmsi))

    # TAG-blokk, c:, s:
    med_tag = med_c = 0
    stasjoner = Counter()
    forsinkelse = []
    for l, t in zip(linjer, mottatt):
        f = tagfelt(l)
        if f is None:
            continue
        med_tag += 1
        if "s" in f:
            stasjoner[f["s"]] += 1
        if "c" in f and f["c"].isdigit():
            med_c += 1
            c = int(f["c"])
            if c > 1e11:  # millisekunder
                c = c / 1000
            forsinkelse.append(t - c)

    # Brudd
    brudd = [h for h in hendelser if h["hendelse"] == "brudd"]
    feilet = [h for h in hendelser if h["hendelse"] == "tilkobling_feilet"]
    hull = [b - a for a, b in zip(mottatt, mottatt[1:]) if b - a > 60]

    n = len(linjer)
    print(f"kropp sha256 (fil slik fang.py skrev den)  {hashlib.sha256(kropp).hexdigest()}")
    print(f"varighet                         {varighet:10.0f} s")
    print(f"linjer                           {n:10d}")
    print(f"bytes fra kilden                 {len(kilde):10d}")
    print(f"bytes i fangstfila (med vår tid) {len(kropp):10d}")
    print()
    print(f"setninger med gyldig sjekksum    {gyldig:10d}  {gyldig/n:7.2%}")
    print(f"setninger med feil sjekksum      {ugyldig_sjekksum:10d}  {ugyldig_sjekksum/n:7.2%}")
    print(f"linjer pyais ikke parser         {uparsbar:10d}  {uparsbar/n:7.2%}")
    print(f"meldinger forventet (1-delte + første fragment) {forventet:d}")
    print(f"meldinger satt sammen            {satt_sammen:10d}  {satt_sammen/forventet:7.2%}")
    print(f"meldinger dekodet                {dekodet:10d}  {dekodet/forventet:7.2%}")
    print(f"unike MMSI                       {len(mmsi):10d}")
    print("meldingstyper (topp 8)           " + ", ".join(f"{k}:{v}" for k, v in typer.most_common(8)))
    print()
    print(f"linjer med TAG-blokk             {med_tag:10d}  {med_tag/n:7.2%}")
    print(f"linjer med c:                    {med_c:10d}  {med_c/n:7.2%}")
    print(f"unike s: (stasjoner)             {len(stasjoner):10d}")
    print("s: med flest linjer              " + ", ".join(f"{k}:{v}" for k, v in stasjoner.most_common(5)))
    if forsinkelse:
        print("forsinkelse mottatt − c: (s)     "
              f"min {min(forsinkelse):.1f}  median {statistics.median(forsinkelse):.1f}  "
              f"p90 {pst(forsinkelse, 90):.1f}  p99 {pst(forsinkelse, 99):.1f}  "
              f"maks {max(forsinkelse):.1f}")
        print(f"linjer med c: etter mottakstid   {sum(1 for x in forsinkelse if x < 0):10d}")
    print()
    eof = sum(1 for h in brudd if h.get("grunn") == "eof")
    vaar = sum(1 for h in brudd if "timed out" in h.get("grunn", ""))
    print(f"brudd: kilden lukket (eof)       {eof:10d}")
    print(f"brudd: vårt tidsavbrudd, stille  {vaar:10d}")
    print(f"brudd: annen feil                {len(brudd) - eof - vaar:10d}")
    print(f"mislykte tilkoblinger            {len(feilet):10d}")
    print(f"hull > 60 s mellom linjer        {len(hull):10d}")
    lengst = max(b - a for a, b in zip(mottatt, mottatt[1:]))
    print(f"lengste hull mellom linjer       {lengst:10.0f} s")
    uten_c = [l for l in linjer if (f := tagfelt(l)) is not None and "c" not in f]
    senere = sum(1 for l in uten_c if fragmentnr(l) > 1)
    print(f"linjer uten c:                   {len(uten_c):10d}  (av dem fragment nr > 1: {senere})")
    print()
    print("volum                    per time       per døgn         per år")
    def rad(navn, b):
        h = b / varighet * 3600
        print(f"{navn:22s} {h/1e6:9.2f} MB {h*24/1e6:11.1f} MB {h*24*365/1e9:11.2f} GB")
    rad("kilden rå", len(kilde))
    rad("kilden gzip -9", len(gzip.compress(kilde, 9)))
    rad("fangstfil rå", len(kropp))
    rad("fangstfil gzip -9", len(gzip.compress(kropp, 9)))
    rad("fangstfil zstd -3", len(zstd.compress(kropp, 3)))
    rad("fangstfil zstd -19", len(zstd.compress(kropp, 19)))


if __name__ == "__main__":
    main()
