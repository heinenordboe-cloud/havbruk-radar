"""AIS-lytteren på kystvakt-1. Lagrer Kystverkets strøm rått, time for time.

Hver linje lagres uendret, med VÅR mottakstid foran og en tabulator
imellom. Kildens klokke står i c:-feltet inne i linja. To klokker, to
eiere (CLAUDE.md 1b-7):

    <mottatt UTC, ISO, mikrosek>\t<linja slik den kom, med terminator>

Ingen dekoding, ingen filtrering, ingen sletting. Lytteren kan ikke
avgjøre hva som er søppel; det kan en parser senere, mot rådataene.

Én zstd-fil per UTC-time, skrevet én gang (CLAUDE.md §2):

    <rot>/<dato>/<dato>T<tt>Z.txt.zst          ferdig, 0444
    <rot>/<dato>/<dato>T<tt>Z.<n>.txt.zst      samme time etter omstart
    <rot>/<dato>/.<navn>.delvis                timen som skrives nå
    <rot>/<dato>/SHA256SUMS                    dagsmanifestet

En fil gjøres ferdig med os.link() til et ledig navn, som feiler i
stedet for å overskrive. En .delvis som ligger igjen etter et krasj,
røres ikke innvendig: den lenkes til `.avbrutt.txt.zst` og føres i
manifestet. Siste zstd-blokk kan være avkortet; alt før den leses.

Systemd-vakten (WatchdogSec) får livstegn bare når det kom DATA. Har
det ikke kommet noe på fem minutter, dreper systemd prosessen og
Restart=always starter den igjen. Vakten måler om strømmen leverer,
ikke om prosessen lever (1b-2: et forsøk er ikke et resultat).

    python3 lytter.py <rot> [port]
"""
import hashlib
import os
import signal
import socket
import sys
import time
from compression import zstd
from datetime import datetime, timezone
from pathlib import Path

VERT = os.environ.get("AIS_VERT", "153.44.253.27")  # miljøvariabel bare for prøvene
TIDSAVBRUDD = 60     # s uten data før vi kobler til på nytt
# s mellom zstd-blokker til disk, også når strømmen tier. Det er det
# som kan gå tapt om prosessen drepes: vakten dreper med SIGABRT.
BLOKK_HVERT = float(os.environ.get("AIS_BLOKK_S", 10))
STOPPSIGNALER = {signal.SIGTERM, signal.SIGINT}


class Stopp(Exception):
    pass


def logg(*a):
    print(*a, file=sys.stderr, flush=True)


def sd_notify(melding: str) -> None:
    adr = os.environ.get("NOTIFY_SOCKET")
    if not adr:
        return
    if adr.startswith("@"):
        adr = "\0" + adr[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.sendto(melding.encode(), adr)


def lenk_ferdig(delvis: Path, stamme: str, merke: str = "") -> Path:
    """Gir fila et ledig endelig navn uten å kunne overskrive noe."""
    stamme = f"{stamme}.{merke}" if merke else stamme
    mappe = delvis.parent
    kandidater = [mappe / f"{stamme}.txt.zst"]
    kandidater += [mappe / f"{stamme}.{n}.txt.zst" for n in range(2, 1000)]
    for sti in kandidater:
        try:
            os.link(delvis, sti)
        except FileExistsError:
            continue
        os.chmod(sti, 0o444)
        delvis.unlink()
        sha = hashlib.sha256(sti.read_bytes()).hexdigest()
        with open(delvis.parent / "SHA256SUMS", "a") as m:
            m.write(f"{sha}  {sti.name}\n")
            m.flush()
            os.fsync(m.fileno())
        logg(f"ferdig {sti.name} {sti.stat().st_size} B sha256 {sha}")
        return sti
    raise RuntimeError(f"ingen ledige navn for {stamme}")


def rydd_avbrutte(rot: Path) -> None:
    for delvis in rot.glob("*/.*.delvis"):
        stamme = delvis.name[1:-len(".delvis")]
        logg(f"fant avbrutt {delvis.name}")
        lenk_ferdig(delvis, stamme, "avbrutt")


class Time:
    """Én UTC-time under skriving."""

    def __init__(self, rot: Path, time_: str):
        dato = time_[:10]
        mappe = rot / dato
        mappe.mkdir(parents=True, exist_ok=True)
        self.stamme = f"{time_}Z"
        self.time = time_
        self.sti = mappe / f".{self.stamme}.delvis"
        fd = os.open(self.sti, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        self.f = os.fdopen(fd, "wb")
        self.z = zstd.ZstdCompressor(level=3)
        self.sist_blokk = time.monotonic()

    def skriv(self, data: bytes) -> None:
        self.f.write(self.z.compress(data))
        if time.monotonic() - self.sist_blokk >= BLOKK_HVERT:
            self.blokk()

    def blokk(self) -> None:
        """Alt kompressoren har tatt imot, ut til kjernen. Overlever at
        prosessen drepes; ikke at maskinen mister strømmen."""
        self.f.write(self.z.flush(zstd.ZstdCompressor.FLUSH_BLOCK))
        self.f.flush()
        self.sist_blokk = time.monotonic()

    def lukk(self) -> None:
        self.f.write(self.z.flush(zstd.ZstdCompressor.FLUSH_FRAME))
        self.f.flush()
        os.fsync(self.f.fileno())
        self.f.close()
        lenk_ferdig(self.sti, self.stamme)



def stempel() -> bytes:
    # Veggklokke: mottakstiden handler om verden (1b-1).
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ").encode()


class Lytter:
    def __init__(self, rot: Path, port: int):
        self.rot, self.port = rot, port
        self.aapen: Time | None = None

    def blokk(self) -> None:
        signal.pthread_sigmask(signal.SIG_BLOCK, STOPPSIGNALER)
        try:
            if self.aapen:
                self.aapen.blokk()
        finally:
            signal.pthread_sigmask(signal.SIG_UNBLOCK, STOPPSIGNALER)

    def skriv(self, linjer: list[bytes]) -> None:
        # Et signal mellom compress() og write(), eller midt i et
        # timeskifte, ville latt kompressoren ha spist data som aldri nådde
        # fila. Stoppsignalene venter til skrivingen er ferdig; de leveres
        # i recv(), connect() eller sleep().
        signal.pthread_sigmask(signal.SIG_BLOCK, STOPPSIGNALER)
        try:
            self._skriv(linjer)
        finally:
            signal.pthread_sigmask(signal.SIG_UNBLOCK, STOPPSIGNALER)

    def _skriv(self, linjer: list[bytes]) -> None:
        t = stempel()
        time_ = t[:13].decode()  # 2026-10-28T05
        if self.aapen is None or self.aapen.time != time_:
            if self.aapen:
                self.aapen.lukk()
                self.aapen = None
            self.aapen = Time(self.rot, time_)
        self.aapen.skriv(b"".join(t + b"\t" + l + b"\n" for l in linjer))

    def lytt(self) -> None:
        while True:
            try:
                s = socket.create_connection((VERT, self.port), timeout=15)
            except OSError as e:
                logg(f"tilkobling feilet: {e!r}")
                time.sleep(10)
                continue
            # Kort tidsavbrudd så blokka tømmes mens strømmen tier; brudd
            # først etter TIDSAVBRUDD uten data.
            s.settimeout(BLOKK_HVERT)
            logg(f"tilkoblet {VERT}:{self.port}")
            buf = b""
            sist_data = time.monotonic()
            try:
                while True:
                    try:
                        bit = s.recv(65536)
                    except TimeoutError:
                        self.blokk()
                        if time.monotonic() - sist_data > TIDSAVBRUDD:
                            logg(f"brudd: ingen data på {TIDSAVBRUDD} s")
                            break
                        continue
                    sist_data = time.monotonic()
                    if not bit:
                        logg("brudd: eof")
                        break
                    buf += bit
                    *hele, buf = buf.split(b"\n")
                    if hele:
                        self.skriv(hele)
                        sd_notify("WATCHDOG=1")
            except OSError as e:
                logg(f"brudd: {e!r}")
            finally:
                s.close()
                if buf:
                    # Halen etter siste \n kom aldri ferdig. Den lagres
                    # likevel, med vår \n som postskille, og nevnes her.
                    logg(f"ufullstendig hale: {len(buf)} B")
                    self.skriv([buf])
            time.sleep(2)

    def lukk(self) -> None:
        if self.aapen:
            self.aapen.lukk()
            self.aapen = None


def main() -> None:
    rot = Path(sys.argv[1])
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5631
    rot.mkdir(parents=True, exist_ok=True)
    rydd_avbrutte(rot)

    def stopp(*_):
        raise Stopp

    for sig in STOPPSIGNALER:
        signal.signal(sig, stopp)
    lytter = Lytter(rot, port)
    sd_notify("READY=1")
    try:
        lytter.lytt()
    except Stopp:
        pass
    finally:
        signal.pthread_sigmask(signal.SIG_BLOCK, STOPPSIGNALER)
        lytter.lukk()
        logg("stoppet")


if __name__ == "__main__":
    main()
