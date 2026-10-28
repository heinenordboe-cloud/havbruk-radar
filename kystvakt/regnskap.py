"""Kvalitetsregnskap per time og kilde for AIS-lytterne på kystvakt-1.

    python3 regnskap.py time <kilde> <rot> <annen kilde> <annen rot> <klokkemappe>
    python3 regnskap.py klokke <klokkemappe>

`time` går gjennom alle ferdige timer under <rot> som mangler regnskap,
og skriver ett per time ved siden av råfilene:

    <rot>/<dato>/<dato>T<tt>Z.regnskap.json      0444, skrevet én gang

En time er ferdig når den ikke har en .delvis og klokka er forbi den.
Sammenligningen med den andre kilden venter til den andres time også er
ferdig, men ikke lenger enn to timer: da skrives regnskapet med
`annen: null`, og grunnen står i fila. Et regnskap skrives aldri om.

`klokke` legger én linje i minuttet fra `chronyc -c tracking` i
<klokkemappe>/<dato>.csv, med vår tid foran. Regnskapet leser den: om
chrony var synkronisert, er et spørsmål om timen, ikke om øyeblikket
regnskapet ble skrevet.

Ingen dekoding av betydning her, bare det regnskapet trenger: MMSI og
kildens klokke. For NMEA er det bit 8–37 i nyttelasten og c: i
TAG-blokka; for BarentsWatch `mmsi` og `msgtime`.
"""
import json
import os
import statistics
import subprocess
import sys
from compression import zstd
from datetime import datetime, timedelta, timezone
from pathlib import Path

VENT_PAA_ANNEN = timedelta(hours=2)


def ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def nmea_mmsi(setning: bytes) -> int | None:
    """MMSI fra første fragment av en !AIVDM/!AIVDO. None for resten."""
    f = setning.split(b",")
    if len(f) < 7 or not f[0].endswith((b"VDM", b"VDO")) or f[2] != b"1" or len(f[5]) < 7:
        return None
    bits = 0
    for c in f[5][:7]:
        v = c - 48
        if v > 40:
            v -= 8
        bits = (bits << 6) | (v & 0x3F)
    return (bits >> 4) & 0x3FFFFFFF  # 42 bit: type 6, repetisjon 2, mmsi 30, 4 til overs


def les_nmea(linje: bytes) -> tuple[int | None, float | None]:
    kilde_t = None
    setning = linje
    if linje.startswith(b"\\"):
        slutt = linje.find(b"\\", 1)
        if slutt > 0:
            for del_ in linje[1:slutt].split(b"*")[0].split(b","):
                k, _, v = del_.partition(b":")
                if k == b"c" and v.isdigit():
                    kilde_t = int(v) / (1000 if len(v) > 11 else 1)
            setning = linje[slutt + 1:]
    return nmea_mmsi(setning.rstrip(b"\r")), kilde_t


def les_bw(linje: bytes) -> tuple[int | None, float | None]:
    try:
        d = json.loads(linje)
        return int(d["mmsi"]), ts(d["msgtime"])
    except (ValueError, KeyError, TypeError):
        return None, None


def timefiler(rot: Path, time_: str) -> list[Path]:
    return sorted((rot / time_[:10]).glob(f"{time_}Z*.txt.zst"))


def ferdig(rot: Path, time_: str, naa: datetime) -> bool:
    if datetime.fromisoformat(time_ + ":00:00+00:00") + timedelta(hours=1) > naa:
        return False
    return not list((rot / time_[:10]).glob(f".{time_}Z*.delvis"))


def les_time(rot: Path, time_: str, leser):
    mottatt, mmsi, forsinkelse = [], set(), []
    meldinger = ugyldige = 0
    for sti in timefiler(rot, time_):
        try:
            data = zstd.decompress(sti.read_bytes())
        except zstd.ZstdError:
            # En .avbrutt kan ha en avkortet siste blokk; les det som går.
            d = zstd.ZstdDecompressor()
            data = d.decompress(sti.read_bytes())
        for rad in data.split(b"\n"):
            if not rad:
                continue
            t, _, linje = rad.partition(b"\t")
            vaar = ts(t.decode())
            mottatt.append(vaar)
            meldinger += 1
            m, kilde_t = leser(linje)
            if m is None:
                ugyldige += 1
            else:
                mmsi.add(m)
            if kilde_t is not None:
                forsinkelse.append(vaar - kilde_t)
    return mottatt, mmsi, forsinkelse, meldinger, ugyldige


def manifest(rot: Path, filer: list[Path]) -> dict:
    navn = {f.name for f in filer}
    ut = {}
    m = rot / (filer[0].parent.name if filer else "") / "SHA256SUMS"
    if filer and m.exists():
        for l in m.read_text().splitlines():
            sha, _, n = l.partition("  ")
            if n in navn:
                ut[n] = sha
    return ut


def klokke_for(klokkemappe: Path, time_: str) -> dict:
    sti = klokkemappe / f"{time_[:10]}.csv"
    prover = []
    if sti.exists():
        for l in sti.read_text().splitlines():
            if l.startswith(time_):
                f = l.split(",")
                # vår tid, så chronyc -c: ... [5] system time, [14] leap status
                if len(f) >= 15:
                    prover.append((float(f[5]), f[14]))
    synk = [p for p in prover if p[1] == "Normal" and abs(p[0]) < 0.1]
    return {
        "prover": len(prover),
        "synkronisert": len(synk),
        "maks_avvik_s": max((abs(p[0]) for p in prover), default=None),
        "svar": None if not prover else len(synk) == len(prover),
    }


def startet(rot: Path) -> str | None:
    """Timen lytteren startet i (lytter.py skriver <rot>/STARTET), eller None."""
    try:
        return (rot / "STARTET").read_text().strip()[:13]
    except FileNotFoundError:
        return None


def regnskap_for(kilde, rot, annen, annen_rot, klokkemappe, time_, naa) -> dict | None:
    leser = les_bw if kilde == "bw" else les_nmea
    annen_leser = les_bw if annen == "bw" else les_nmea
    filer = timefiler(rot, time_)
    shaer = manifest(rot, filer)
    mottatt, mmsi, forsinkelse, meldinger, ugyldige = les_time(rot, time_, leser)

    start = ts(time_ + ":00:00Z")
    kanter = [start] + sorted(mottatt) + [start + 3600]
    lengste = max(b - a for a, b in zip(kanter, kanter[1:]))

    annen_svar = None
    grunn = None
    annen_start = startet(annen_rot)
    if annen_start and annen_start <= time_ and ferdig(annen_rot, time_, naa):
        # En time uten filer hos den andre er en tom time, ikke en ukjent.
        _, amm, _, _, _ = les_time(annen_rot, time_, annen_leser)
        annen_svar = {"kilde": annen, "unike_mmsi": len(amm), "felles_mmsi": len(mmsi & amm),
                      "bare_her": len(mmsi - amm), "bare_der": len(amm - mmsi)}
    elif datetime.fromisoformat(time_ + ":00:00+00:00") + timedelta(hours=1) + VENT_PAA_ANNEN > naa:
        return None  # vent på den andre kilden
    else:
        grunn = (f"{annen}: lyttet ikke ennå" if not annen_start or annen_start > time_
                 else f"{annen}: timen ikke ferdig etter {VENT_PAA_ANNEN}")

    return {
        "kilde": kilde,
        "time": time_ + "Z",
        "skrevet": naa.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filer": {f.name: shaer.get(f.name) for f in filer},
        "meldinger": meldinger,
        "uten_mmsi": ugyldige,
        "unike_mmsi": len(mmsi),
        "lengste_pause_s": round(lengste, 3),
        "forsinkelse_s": None if not forsinkelse else {
            "median": round(statistics.median(forsinkelse), 3),
            "maks": round(max(forsinkelse), 3),
            "min": round(min(forsinkelse), 3),
            "antall": len(forsinkelse),
        },
        "chrony": klokke_for(klokkemappe, time_),
        "annen": annen_svar,
        "annen_mangler": grunn,
    }


def skriv_en_gang(sti: Path, data: dict) -> None:
    fd = os.open(sti, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def kjør_time(kilde, rot, annen, annen_rot, klokkemappe) -> None:
    naa = datetime.now(timezone.utc)
    forste = startet(rot)
    if not forste:
        return
    # Hver time fra lytterens første, også de uten en eneste fil: en time
    # uten data er det regnskapet finnes for å vise.
    timer, t = [], datetime.fromisoformat(forste + ":00:00+00:00")
    while t + timedelta(hours=1) <= naa:
        timer.append(t.strftime("%Y-%m-%dT%H"))
        t += timedelta(hours=1)
    for time_ in timer:
        (rot / time_[:10]).mkdir(exist_ok=True)
        sti = rot / time_[:10] / f"{time_}Z.regnskap.json"
        if sti.exists() or not ferdig(rot, time_, naa):
            continue
        r = regnskap_for(kilde, rot, annen, annen_rot, klokkemappe, time_, naa)
        if r is None:
            continue
        skriv_en_gang(sti, r)
        print(f"{sti.name}: {r['meldinger']} meldinger, {r['unike_mmsi']} MMSI, "
              f"lengste pause {r['lengste_pause_s']:.0f} s", flush=True)


def kjør_klokke(klokkemappe: Path) -> None:
    klokkemappe.mkdir(parents=True, exist_ok=True)
    naa = datetime.now(timezone.utc)
    ut = subprocess.run(["chronyc", "-c", "tracking"], capture_output=True, text=True,
                        timeout=20).stdout.strip() or "ingen svar"
    with open(klokkemappe / f"{naa:%Y-%m-%d}.csv", "a") as f:
        f.write(f"{naa:%Y-%m-%dT%H:%M:%SZ},{ut}\n")


def main() -> None:
    if sys.argv[1] == "klokke":
        kjør_klokke(Path(sys.argv[2]))
    else:
        _, _, kilde, rot, annen, annen_rot, klokke = sys.argv
        kjør_time(kilde, Path(rot), annen, Path(annen_rot), Path(klokke))


if __name__ == "__main__":
    main()
