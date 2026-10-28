"""Teller en rå fangst av BarentsWatchs Live AIS-strøm fra fang_bw.py, og
holder den mot 5632 fanget i samme time med fang.py.

    .venv/bin/python -m analyse.ais.tell_bw <bw.txt|.gz> <hendelser-bw.jsonl> \
        <5632.txt|.gz>

Leser kroppene slik de ligger i arkivet. Utskriften er tabellene i
tillegget i docs/MALING-AIS.md, uendret.

Stoppregel 2 (er `msgtime` kildens klokke?) prøves ved å finne SAMME
posisjonsrapport i begge: lik MMSI og lik posisjon. Bare fartøy i fart
(over 1 knop) og bare type 1, 2, 3, 18 og 19 er med: et fartøy i ro
sender samme posisjon i timevis, og type 27 har grovere oppløsning, så
begge ville gitt treff som ikke er samme sending.
"""
import gzip
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from compression import zstd
from datetime import datetime

from pyais.stream import IterMessages

from analyse.ais.tell import les, pst, tagfelt, ts


def iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def rader(kropp: bytes):
    r = kropp.split(b"\n")
    if r and r[-1] == b"":
        r.pop()
    for linje in r:
        t, _, l = linje.partition(b"\t")
        yield ts(t), l


def les_5632(kropp: bytes):
    """(mmsi-sett, posisjoner) der posisjoner er (mmsi, lat, lon) -> [c:]."""
    linjer, c_for = [], []
    for t, l in rader(kropp):
        linjer.append(l.rstrip(b"\r\n"))
        f = tagfelt(l)
        c_for.append(int(f["c"]) if f and f.get("c", "").isdigit() else None)
    mmsi, pos = set(), defaultdict(list)
    # IterMessages mister koblingen til linja; c: står på første fragment,
    # og alle posisjonsrapporter er énsetningsmeldinger, så de telles for seg.
    for m in IterMessages(linjer):
        try:
            d = m.decode()
        except Exception:
            continue
        if getattr(d, "mmsi", None):
            mmsi.add(int(d.mmsi))
    for l, c in zip(linjer, c_for):
        if c is None:
            continue
        try:
            d = next(iter(IterMessages([l]))).decode()
        except Exception:
            continue
        if d.msg_type in (1, 2, 3, 18, 19) and (d.speed or 0) > 1 and d.lat is not None:
            pos[(int(d.mmsi), round(d.lat, 4), round(d.lon, 4))].append(c)
    return mmsi, pos


def main():
    bw = les(sys.argv[1])
    hendelser = [json.loads(l) for l in open(sys.argv[2])]
    k5632 = les(sys.argv[3])

    mottatt, msgtime, ikke_json, uten_felt = [], [], 0, 0
    strom_per_melding = []
    eksempler_ikke_json = Counter()
    typer, mtyper, strommer = Counter(), Counter(), Counter()
    mmsi = set()
    mmsi_statisk = set()
    pos_bw = defaultdict(list)
    kilde = []
    for t, l in rader(bw):
        kilde.append(l + b"\n")
        mottatt.append(t)
        try:
            d = json.loads(l)
        except ValueError:
            ikke_json += 1
            eksempler_ikke_json[l[:20]] += 1
            continue
        if not isinstance(d, dict) or "mmsi" not in d or not d.get("msgtime"):
            uten_felt += 1
            continue
        try:
            mt = iso(d["msgtime"])
        except ValueError:
            uten_felt += 1
            continue
        msgtime.append((t, mt))
        strom_per_melding.append(d.get("stream"))
        typer[d.get("type")] += 1
        mtyper[d.get("messageType")] += 1
        strommer[d.get("stream")] += 1
        mmsi.add(int(d["mmsi"]))
        if str(d.get("type")).lower() == "staticdata":  # kilden skriver «Staticdata»
            mmsi_statisk.add(int(d["mmsi"]))
        if (d.get("type") == "Position" and d.get("messageType") in (1, 2, 3, 18, 19)
                and (d.get("speedOverGround") or 0) > 1 and d.get("latitude") is not None):
            pos_bw[(int(d["mmsi"]), round(d["latitude"], 4), round(d["longitude"], 4))].append(mt)
    kilde = b"".join(kilde)

    start = [h for h in hendelser if h["hendelse"] == "start"]
    ferdig = [h for h in hendelser if h["hendelse"] == "ferdig"]
    if start and ferdig:
        t0, t1 = iso(start[0]["t"]), iso(ferdig[-1]["t"])
    else:  # fangsten er ikke ferdig: bruk første og siste linje
        t0, t1 = mottatt[0], mottatt[-1]
    varighet = t1 - t0
    n = len(mottatt)
    gyldige = len(msgtime)
    forsinkelse = [t - mt for t, mt in msgtime]

    print(f"kropp sha256 (fil slik fang_bw.py skrev den)  {hashlib.sha256(bw).hexdigest()}")
    print(f"varighet                         {varighet:10.0f} s")
    print(f"linjer                           {n:10d}")
    print(f"meldinger per minutt             {n / varighet * 60:10.0f}")
    print(f"bytes fra kilden                 {len(kilde):10d}")
    print(f"bytes i fangstfila (med vår tid) {len(bw):10d}")
    print()
    print(f"linjer som ikke er JSON          {ikke_json:10d}  {ikke_json/n:7.2%}"
          + (f"  ({', '.join(f'{k!r}:{v}' for k, v in eksempler_ikke_json.most_common(3))})"
             if ikke_json else ""))
    print(f"JSON uten mmsi eller msgtime     {uten_felt:10d}  {uten_felt/n:7.2%}")
    print(f"med mmsi og lesbar msgtime       {gyldige:10d}  {gyldige/n:7.2%}")
    print("type                             " + ", ".join(f"{k}:{v}" for k, v in typer.most_common()))
    print("messageType                      " + ", ".join(f"{k}:{v}" for k, v in mtyper.most_common()))
    print("stream                           " + ", ".join(f"{k}:{v}" for k, v in strommer.most_common()))
    print(f"unike MMSI                       {len(mmsi):10d}")
    print(f"unike MMSI med StaticData        {len(mmsi_statisk):10d}")
    print()
    print("forsinkelse mottatt − msgtime (s) "
          f"min {min(forsinkelse):.1f}  median {statistics.median(forsinkelse):.1f}  "
          f"p90 {pst(forsinkelse, 90):.1f}  p99 {pst(forsinkelse, 99):.1f}  "
          f"maks {max(forsinkelse):.1f}")
    print(f"msgtime etter mottakstid         {sum(1 for x in forsinkelse if x < 0):10d}")
    for s in sorted(k for k in strommer if k):
        f = [t - mt for (t, mt), st in zip(msgtime, strom_per_melding) if st == s]
        print(f"  stream={s:10s} median {statistics.median(f):8.1f}  p99 {pst(f, 99):8.1f}"
              f"  maks {max(f):8.1f}")
    print()

    brudd = [h for h in hendelser if h["hendelse"] == "brudd"]
    feilet = [h for h in hendelser if h["hendelse"] == "tilkobling_feilet"]
    tilkoblet = [h for h in hendelser if h["hendelse"] == "tilkoblet"]
    eof = sum(1 for h in brudd if h.get("grunn") == "eof")
    print(f"tilkoblinger                     {len(tilkoblet):10d}")
    print(f"brudd: kilden lukket (eof)       {eof:10d}")
    print(f"brudd: annen feil                {len(brudd) - eof:10d}")
    print(f"mislykte tilkoblinger            {len(feilet):10d}")
    hull = [b - a for a, b in zip(mottatt, mottatt[1:])]
    print(f"hull > 10 s mellom linjer        {sum(1 for h in hull if h > 10):10d}")
    print(f"lengste hull mellom linjer       {max(hull):10.1f} s")
    print()

    m5632, pos5632 = les_5632(k5632)
    print(f"5632 kropp sha256                {hashlib.sha256(k5632).hexdigest()}")
    print(f"unike MMSI 5632                  {len(m5632):10d}")
    print(f"felles MMSI                      {len(mmsi & m5632):10d}")
    print(f"bare i BarentsWatch              {len(mmsi - m5632):10d}")
    print(f"bare i 5632                      {len(m5632 - mmsi):10d}")
    print()
    felles = set(pos_bw) & set(pos5632)
    avvik = []
    for k in felles:
        # nærmeste par per posisjon; et fartøy i fart er på en posisjon én gang
        avvik.append(min((mt - c for mt in pos_bw[k] for c in pos5632[k]), key=abs))
    print(f"posisjoner i fart, BW            {len(pos_bw):10d}")
    print(f"posisjoner i fart, 5632          {len(pos5632):10d}")
    print(f"samme posisjon i begge           {len(felles):10d}")
    if avvik:
        print("msgtime − 5632 c: (s)            "
              f"min {min(avvik):.1f}  median {statistics.median(avvik):.1f}  "
              f"p90 {pst(avvik, 90):.1f}  maks {max(avvik):.1f}")
        print(f"|msgtime − c:| > 60 s            {sum(1 for a in avvik if abs(a) > 60):10d}")
    print()

    print("volum                    per time       per døgn         per år")

    def rad(navn, b):
        h = b / varighet * 3600
        print(f"{navn:22s} {h/1e6:9.2f} MB {h*24/1e6:11.1f} MB {h*24*365/1e9:11.2f} GB")
    rad("kilden rå", len(kilde))
    rad("fangstfil rå", len(bw))
    rad("fangstfil gzip -9", len(gzip.compress(bw, 9)))
    rad("fangstfil zstd -3", len(zstd.compress(bw, 3)))
    rad("fangstfil zstd -19", len(zstd.compress(bw, 19)))


if __name__ == "__main__":
    main()
