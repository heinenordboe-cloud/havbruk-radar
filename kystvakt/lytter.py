"""AIS-lytteren på kystvakt-1. Lagrer en AIS-strøm rått, time for time.

To kilder, samme lagring:

    python3 lytter.py <rot> bw       BarentsWatch Live AIS, POST /v1/ais
    python3 lytter.py <rot> <port>   Kystverkets TCP-strøm (5632, 5631)

Hver linje lagres uendret, med VÅR mottakstid foran og en tabulator
imellom. Kildens klokke står inne i linja: `msgtime` hos BarentsWatch,
c: i TAG-blokka hos Kystverket. To klokker, to eiere (CLAUDE.md 1b-7):

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

## Vakthunden

Systemd-vakten (WatchdogSec) skal drepe en lytter som ER tilkoblet og
har sluttet å få data, og ingen annen (1b-2: et forsøk er ikke et
resultat, men et mislykket forsøk er heller ikke en hengt prosess).

- Tilkoblet: livstegn bare når det kom DATA. Lytteren har ikke noe eget
  tidsavbrudd for stillhet; det er vakten som avgjør, med WatchdogSec
  satt etter kildens lengste normale pause.
- Ikke tilkoblet: livstegn hele tiden, også mens vi venter. Et forsøk
  som feiler, logges, og neste venter dobbelt så lenge (5 s til 5 min).
  Ingen drap, ingen krasjrapport. En tilkobling som lyktes, men som
  kilden lukket uten data, er ikke et feilet forsøk: fast 10 s pause.

Vakten sender SIGTERM (WatchdogSignal i unit-fila), ikke SIGABRT: timen
lukkes ordentlig, og det blir ingen kjernedump i /var/crash.
"""
import hashlib
import http.client
import json
import os
import signal
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from compression import zstd
from datetime import datetime, timezone
from pathlib import Path

VERT = os.environ.get("AIS_VERT", "153.44.253.27")  # miljøvariabel bare for prøvene
BW_NOKKEL = os.environ.get("AIS_BW_NOKKEL", "/etc/kystvakt/barentswatch-ais.env")
BW_TOKEN_URL = os.environ.get("AIS_BW_TOKEN_URL", "https://id.barentswatch.no/connect/token")
BW_STROM_URL = os.environ.get("AIS_BW_URL", "https://live.ais.barentswatch.no/v1/ais")
# s mellom zstd-blokker til disk, også når strømmen tier. Det er det
# som kan gå tapt om maskinen mister strømmen.
BLOKK_HVERT = float(os.environ.get("AIS_BLOKK_S", 10))
BW_ALT = {"downsample": False, "includePosition": True, "includeStatic": True,
          "includeAton": True, "includeSafetyRelated": True,
          "includeBinaryBroadcastMetHyd": True}
VENT_MIN = float(os.environ.get("AIS_VENT_MIN", 5))  # miljøvariabel bare for prøvene
VENT_MAKS = 300.0
# Tilkoblet, men kilden lukket uten å sende noe. Det er ikke en kilde som
# ikke svarer, og ventetiden øker ikke: 5632 gjorde dette på 333 av 336
# tilkoblinger 28.10 (median 9 s), og dataene kom i de tre som ble holdt
# åpne, i 159–195 s. 30 s fanger slike vinduer og er 120 tilkoblinger i
# timen, ikke 360. Økende ventetid ville gått glipp av dem.
VENT_TOM = float(os.environ.get("AIS_VENT_TOM", 30))
# zstd-nivå. Målt 28.10.2026 på kystvakt-1 mot fem minutter BarentsWatch
# uten nedsampling (248 MB/time fra kilden), med blokk hvert 10. s:
# nivå 3 gir 592 MB/døgn og 0,6 s CPU per time; nivå 19 gir 345 MB/døgn,
# 139 s CPU per time (under 4 % av én kjerne) og 89 MB minne. Disken har
# 15 GB ledig: nivå 19 er forskjellen på 25 og 43 dager før kopien
# utenfor serveren må finnes.
ZSTD_NIVA = int(os.environ.get("AIS_ZSTD_NIVA", 19))
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


def merk_start(rot: Path) -> None:
    """<rot>/STARTET: når denne lytteren lyttet første gang, skrevet én
    gang. Regnskapet teller timer fra den, så en time uten en eneste
    linje blir ført som tom, ikke borte. Uten den kan ingen skille «stille
    time» fra «lytteren fantes ikke ennå» når kilden aldri har sendt noe."""
    try:
        fd = os.open(rot / "STARTET", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError:
        return
    with os.fdopen(fd, "wb") as f:
        f.write(stempel() + b"\n")


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
        self.z = zstd.ZstdCompressor(level=ZSTD_NIVA)
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


class Tcp:
    """Kystverkets rå NMEA-strøm over TCP."""

    def __init__(self, port: int):
        self.port = port
        self.s: socket.socket | None = None

    def navn(self) -> str:
        return f"{VERT}:{self.port}"

    def koble(self) -> None:
        self.s = socket.create_connection((VERT, self.port), timeout=15)
        # Kort tidsavbrudd så blokka tømmes mens strømmen tier. Det er
        # ikke et brudd; stillhet avgjøres av vakten.
        self.s.settimeout(BLOKK_HVERT)

    def les(self) -> bytes | None:
        """Bytes, b"" ved eof, None når det bare var stille en stund."""
        try:
            return self.s.recv(65536)
        except TimeoutError:
            return None

    def lukk(self) -> None:
        if self.s:
            self.s.close()
            self.s = None


class BarentsWatch:
    """BarentsWatch Live AIS: JSON, én melding per linje, med token.

    POST med downsample=false og alle include-flagg, ikke GET: GET er
    nedsamplet til omtrent én posisjon per fartøy per minutt, uten at
    dokumentasjonen sier det (MALING-AIS F2.8, målt 28.10.2026). Ingen
    filter på område, MMSI, skipstype eller land.

    Tokenet finnes bare i minnet til denne prosessen. Det skrives ikke
    til disk og logges aldri; nøklene det lages av, ligger i BW_NOKKEL,
    som bare brukeren `ais` kan lese. Det fornyes ti minutter før det
    utløper, også midt i en tilkobling, så en ny tilkobling aldri må
    vente på et tokenkall som feiler.
    """

    def __init__(self):
        self.c = self.r = None
        self.token: str | None = None
        self.utloper = 0.0

    def navn(self) -> str:
        return BW_STROM_URL

    def hent_token(self) -> str:
        # Veggklokke: om tokenet er utløpt hos BarentsWatch, handler om
        # verden, og verden sover ikke når vi gjør det (F13).
        if self.token and time.time() < self.utloper:
            return self.token
        env = dict(l.split("=", 1) for l in open(BW_NOKKEL).read().splitlines() if "=" in l)
        data = urllib.parse.urlencode({
            "client_id": env["BW_AIS_CLIENT_ID"],
            "client_secret": env["BW_AIS_CLIENT_SECRET"],
            "grant_type": "client_credentials",
            "scope": "ais",
        }).encode()
        try:
            with urllib.request.urlopen(BW_TOKEN_URL, data, timeout=30) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            # Bare status og feilkode fra svaret; aldri det vi sendte.
            raise RuntimeError(f"tokenkall {e.code} {e.read()[:80]!r}") from None
        self.token = d["access_token"]
        self.utloper = time.time() + int(d.get("expires_in", 3600)) - 600
        logg(f"nytt token, gyldig {int(d.get('expires_in', 3600))} s")
        return self.token

    def koble(self) -> None:
        u = urllib.parse.urlsplit(BW_STROM_URL)
        kobling = http.client.HTTPConnection if u.scheme == "http" else http.client.HTTPSConnection
        self.c = kobling(u.hostname, u.port, timeout=30)  # http bare for prøvene
        self.c.request("POST", u.path, body=json.dumps(BW_ALT), headers={
            "Authorization": "Bearer " + self.hent_token(),
            "Content-Type": "application/json"})
        r = self.c.getresponse()
        if r.status != 200:
            if r.status == 401:
                self.token = None  # serveren vet best (F13); neste forsøk henter nytt
            raise RuntimeError(f"strøm {r.status} {r.read(200)!r}")
        # Lesingen har ikke noe eget tidsavbrudd for stillhet: et
        # tidsavbrudd midt i en chunk ville latt http.client stå i en
        # ukjent tilstand. Stillhet mens vi er tilkoblet er vaktens sak.
        self.c.sock.settimeout(None)
        self.r = r

    def les(self) -> bytes | None:
        if time.time() >= self.utloper:
            try:
                self.hent_token()  # fornyes før det trengs, mens strømmen står
            except Exception as e:  # noqa: BLE001 — prøves igjen ved neste lesing
                logg(f"tokenfornying feilet: {e}")
        return self.r.read1(65536)

    def lukk(self) -> None:
        if self.c:
            self.c.close()
        self.c = self.r = None


class Lytter:
    def __init__(self, rot: Path, kilde):
        self.rot, self.kilde = rot, kilde
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
        # i lesingen, tilkoblingen eller ventingen.
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

    def vent(self, s: float) -> None:
        """Venter uten å bli tatt for en hengt lytter: livstegn underveis."""
        slutt = time.monotonic() + s  # hvor lenge VI venter: monotonic
        while (igjen := slutt - time.monotonic()) > 0:
            sd_notify("WATCHDOG=1")
            time.sleep(min(igjen, 5))
        sd_notify("WATCHDOG=1")

    def lytt(self) -> None:
        vent = VENT_MIN
        forsok = 0
        while True:
            sd_notify("WATCHDOG=1")
            forsok += 1
            try:
                self.kilde.koble()
            except Exception as e:  # noqa: BLE001 — alt som hindrer tilkobling
                self.kilde.lukk()
                logg(f"tilkobling feilet (forsøk {forsok}): {e}; venter {vent:g} s")
                self.vent(vent)
                vent = min(vent * 2, VENT_MAKS)
                continue
            logg(f"tilkoblet {self.kilde.navn()} (forsøk {forsok})")
            buf = b""
            fikk_data = False
            try:
                while True:
                    bit = self.kilde.les()
                    if bit is None:
                        self.blokk()
                        continue
                    if not bit:
                        logg("brudd: eof" + ("" if fikk_data else " uten data"))
                        break
                    buf += bit
                    *hele, buf = buf.split(b"\n")
                    if hele:
                        self.skriv(hele)
                        sd_notify("WATCHDOG=1")
                        if not fikk_data:
                            fikk_data, vent, forsok = True, VENT_MIN, 0
            except Stopp:
                raise
            except Exception as e:  # noqa: BLE001
                logg(f"brudd: {e!r}")
            finally:
                self.kilde.lukk()
                if buf:
                    # Halen etter siste \n kom aldri ferdig. Den lagres
                    # likevel, med vår \n som postskille, og nevnes her.
                    logg(f"ufullstendig hale: {len(buf)} B")
                    self.skriv([buf])
            self.vent(2 if fikk_data else VENT_TOM)

    def lukk(self) -> None:
        if self.aapen:
            self.aapen.lukk()
            self.aapen = None


def main() -> None:
    rot = Path(sys.argv[1])
    hva = sys.argv[2] if len(sys.argv) > 2 else "5631"
    kilde = BarentsWatch() if hva == "bw" else Tcp(int(hva))
    rot.mkdir(parents=True, exist_ok=True)
    merk_start(rot)
    rydd_avbrutte(rot)

    def stopp(*_):
        raise Stopp

    for sig in STOPPSIGNALER:
        signal.signal(sig, stopp)
    lytter = Lytter(rot, kilde)
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
