"""Komprimering av rålaget, målt på kystvakt-1 (MALING-AIS, tillegget 30.10.2026).

    python3 komprimering.py <arbeidsmappe> <time.txt.zst>... --trening <time.txt.zst>...

Pakker ut hver time til rå bytes (det lytteren komprimerte), og pakker
den så inn på nytt med hver kandidat. For hver kandidat: størrelse,
CPU-sekunder og maks RSS for prosessen som komprimerte, og sha256 av
utpakket fil mot originalen. Ordboka trenes på andre timer enn dem som
måles.

To slags kandidater:

    cli      zstd/xz på hele fila, slik et etterarbeid ville gjort det
    lytter   compression.zstd med FLUSH_BLOCK hvert 10. s etter VÅR
             mottakstid (første felt), slik lytter.py skriver

Bare `lytter`-kandidatene kan brukes av lytteren uten å skrive om
ferdige filer (§2). CLI-tallene er referansen for hva formatet koster.

Kjøres under en minnegrense, så det er målingen som stopper og ikke
lytteren:

    sudo systemd-run --scope -p MemoryMax=350M -p MemorySwapMax=0 \
        -p CPUWeight=1 --uid=vakt --gid=vakt nice -n19 python3 komprimering.py ...

En kandidat som blir drept (signal 9), er over grensa. Det er et svar,
ikke en feil.
"""
import hashlib
import json
import os
import subprocess
import sys
from compression import zstd
from datetime import datetime
from pathlib import Path

BLOKK_S = 10.0


def sha(sti: Path) -> str:
    h = hashlib.sha256()
    with open(sti, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def kjør(cmd: list[str], ut: Path | None = None, inn: Path | None = None) -> dict:
    """Kjører cmd som barn og returnerer rusage for nettopp det barnet."""
    fi = open(inn, "rb") if inn else subprocess.DEVNULL
    fu = open(ut, "wb") if ut else subprocess.DEVNULL
    p = subprocess.Popen(cmd, stdin=fi, stdout=fu, stderr=subprocess.PIPE)
    _, status, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(status)
    feil = p.stderr.read().decode(errors="replace")[-300:]
    for f in (fi, fu):
        if hasattr(f, "close"):
            f.close()
    return {"kode": p.returncode, "cpu_s": round(ru.ru_utime + ru.ru_stime, 1),
            "maks_rss_mb": round(ru.ru_maxrss / 1024, 1), "feil": feil if p.returncode else ""}


def lytter_modus(raa: Path, ut: Path, vindu: int, ordbok: str) -> None:
    """Komprimerer som lytter.py: én ramme, blokk når 10 s av vår tid har gått."""
    opt = {zstd.CompressionParameter.compression_level: 19}
    if vindu:
        opt[zstd.CompressionParameter.window_log] = vindu
        opt[zstd.CompressionParameter.enable_long_distance_matching] = True
    d = zstd.ZstdDict(Path(ordbok).read_bytes()) if ordbok else None
    z = zstd.ZstdCompressor(options=opt, zstd_dict=d)
    forrige = None
    with open(raa, "rb") as fi, open(ut, "wb") as fu:
        for linje in fi:
            t = datetime.fromisoformat(linje[:linje.index(b"\t")].decode()).timestamp()
            if forrige is None:
                forrige = t
            elif t - forrige >= BLOKK_S:
                fu.write(z.flush(zstd.ZstdCompressor.FLUSH_BLOCK))
                forrige = t
            fu.write(z.compress(linje))
        fu.write(z.flush(zstd.ZstdCompressor.FLUSH_FRAME))


def main() -> None:
    if sys.argv[1] == "_lytter":
        lytter_modus(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
        return
    arb = Path(sys.argv[1])
    i = sys.argv.index("--trening")
    timer, trening = [Path(p) for p in sys.argv[2:i]], [Path(p) for p in sys.argv[i + 1:]]
    arb.mkdir(exist_ok=True)

    # Ordboka: 16 MB fra hver treningstime, i 128 KB-biter (omtrent en
    # 10-sekunders blokk rå).
    prøver = []
    for t in trening:
        raa = arb / (t.name[:-4])
        kjør(["zstd", "-dc", str(t)], ut=raa)
        bit = arb / (raa.name + ".16mb")
        with open(raa, "rb") as f, open(bit, "wb") as g:
            g.write(f.read(16 << 20))
        raa.unlink()
        prøver.append(str(bit))
    ordbok = arb / "ordbok"
    r = kjør(["zstd", "--train-fastcover", "-B131072", "--maxdict=112640", *prøver, "-o", str(ordbok)])
    print(json.dumps({"ordbok_trening": r, "bytes": ordbok.stat().st_size if ordbok.exists() else None,
                      "sha256": sha(ordbok) if ordbok.exists() else None}), flush=True)

    py = sys.executable
    for t in timer:
        raa = arb / t.name[:-4]
        kjør(["zstd", "-dc", str(t)], ut=raa)
        fasit = sha(raa)
        rad = {"time": t.name, "raa_bytes": raa.stat().st_size, "raa_sha256": fasit,
               "lagret_bytes": t.stat().st_size}
        kandidater = {
            "cli zstd -19": (["zstd", "-19", "-c", str(raa)], ["zstd", "-dc"]),
            "cli zstd -19 --long=27": (["zstd", "-19", "--long=27", "-c", str(raa)], ["zstd", "-dc"]),
            "cli zstd -19 ordbok": (["zstd", "-19", "-D", str(ordbok), "-c", str(raa)],
                                    ["zstd", "-dc", "-D", str(ordbok)]),
            "cli xz -9": (["xz", "-9", "-T1", "-c", str(raa)], ["xz", "-dc"]),
            "lytter zstd 19": ([py, __file__, "_lytter", str(raa), "-", "0", ""], ["zstd", "-dc"]),
            "lytter zstd 19 vindu 27": ([py, __file__, "_lytter", str(raa), "-", "27", ""], ["zstd", "-dc"]),
            "lytter zstd 19 ordbok": ([py, __file__, "_lytter", str(raa), "-", "0", str(ordbok)],
                                      ["zstd", "-dc", "-D", str(ordbok)]),
        }
        for navn, (inn_cmd, ut_cmd) in kandidater.items():
            kompr = arb / "kandidat"
            if "-" in inn_cmd and inn_cmd[1] == __file__:
                inn_cmd[inn_cmd.index("-")] = str(kompr)
                r = kjør(inn_cmd)
            else:
                r = kjør(inn_cmd, ut=kompr)
            if r["kode"] == 0:
                tilbake = arb / "tilbake"
                d = kjør(ut_cmd, ut=tilbake, inn=kompr)
                r["bytes"] = kompr.stat().st_size
                r["andel_av_lagret"] = round(r["bytes"] / rad["lagret_bytes"], 3)
                r["sha256_lik"] = d["kode"] == 0 and sha(tilbake) == fasit
                r["utpakk_cpu_s"], r["utpakk_rss_mb"] = d["cpu_s"], d["maks_rss_mb"]
                tilbake.unlink(missing_ok=True)
            kompr.unlink(missing_ok=True)
            rad[navn] = r
            print(json.dumps({"time": t.name, "kandidat": navn, **r}), flush=True)
        raa.unlink()


if __name__ == "__main__":
    main()
