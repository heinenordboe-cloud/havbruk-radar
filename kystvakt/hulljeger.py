"""Hulljegeren: henter timer BarentsWatch-lytteren mangler, fra historikk-API-et.

    python3 hulljeger.py <rot> [maks_sekunder]

Kjøres hver natt som brukeren `ais`. Den leser regnskapet
(kystvakt/regnskap.py) og finner timer innenfor historikk-API-ets 14
døgn som er

  - tomme: ingen råfil og intet regnskap, eller
  - unormalt lave: færre enn GULV_MELDINGER meldinger, eller en pause
    lengre enn GULV_PAUSE_S.

Sammenhengende hull hentes som ett vindu på inntil 24 timer: først
`mmsiinarea` for vinduet, så sporet til hver MMSI. Det koster ett kall
per fartøy per VINDU, ikke per time: 3814 MMSI for én time og 4409 for
et døgn (målt 28.10.2026, se MALING-AIS).

Historikken er tynnere enn strømmen lytteren lagrer. Den har omtrent
like mange posisjoner som den nedsamplede GET-strømmen, men ikke de
samme sekundene (MALING-AIS, historikk-API-et). En etterhentet time er
et lappeteppe over et hull, ikke en erstatning for timen.
Eldste hull først, fordi det er de som forsvinner først.

Det som hentes, lagres rått og uendret, i EGNE filer, aldri flettet inn
i råfilene fra lytteren (CLAUDE.md §2):

    <rot>/etterhentet/<dato>/<fra>--<til>.etterhentet.jsonl.zst   0444
    <rot>/etterhentet/<dato>/SHA256SUMS

Hver linje er ett kall: {"t": vår tid, "kall", "status", "s", "body":
svaret som tekst}. Formatet er ikke lytterens: historikk-API-et gir
bare posisjoner (AisComboSimple: navn og skipstype, ingen
StaticData, ingen messageType), så en etterhentet time er en annen og
fattigere kropp enn en lyttet time, og den skal kunne skilles fra den.

## Gulvet

GULV_MELDINGER er satt FØR det finnes historikk å bygge det av, og er
derfor lavt med vilje: fem målte minutter uten nedsampling (28.10 kl.
17:16 UTC) ga 14 224 meldinger i minuttet, rundt 850 000 i timen, og
den nedsamplede GET-timen 14:44–15:44 hadde 170 893. Gulvet fanger en
time som er tom eller nesten tom, ikke en time som er tynn. Det er et
lavvannsmerke, ikke et rullende snitt
(1b-4): det flytter seg bare når noen skriver det om, etter at et par
uker regnskap viser hva en natt i februar faktisk gir.
GULV_PAUSE_S er satt etter vakten: WatchdogSec er 120 s, og
lengste pause i den målte timen var 12,6 s.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from compression import zstd
from datetime import datetime, timedelta, timezone
from pathlib import Path

NOKKEL = os.environ.get("AIS_BW_NOKKEL", "/etc/kystvakt/barentswatch-ais.env")
TOKEN_URL = os.environ.get("AIS_BW_TOKEN_URL", "https://id.barentswatch.no/connect/token")
LIVE = os.environ.get("AIS_BW_LIVE", "https://live.ais.barentswatch.no")
HIST = os.environ.get("AIS_BW_HIST", "https://historic.ais.barentswatch.no")
GULV_MELDINGER = 50_000
GULV_PAUSE_S = 60.0
# Historikk-API-et har 14 døgn. En time nær kanten kan være delvis borte
# før vi rekker den; de to siste timene er lytterens, ikke våre ennå.
ELDST = timedelta(days=14) - timedelta(hours=2)
YNGST = timedelta(hours=3)
MAKS_VINDU = 24
PAUSE_S = float(os.environ.get("AIS_HULL_PAUSE", 0.5))


def logg(*a):
    print(*a, file=sys.stderr, flush=True)


def naa_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def tid(time_: str) -> datetime:
    return datetime.fromisoformat(time_ + ":00:00+00:00")


def timenavn(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H")


def etterhentede(rot: Path) -> set[str]:
    """Timer som allerede er hentet: fra filnavnene, <fra>--<til>."""
    ut = set()
    for f in (rot / "etterhentet").glob("*/*.etterhentet.jsonl.zst"):
        fra, til = f.name.split(".")[0].split("--")
        t = tid(fra[:13])
        while t < tid(til[:13]):
            ut.add(timenavn(t))
            t += timedelta(hours=1)
    return ut


def er_hull(rot: Path, time_: str) -> str | None:
    """Grunnen til at timen er et hull, eller None."""
    dag = rot / time_[:10]
    regnskap = dag / f"{time_}Z.regnskap.json"
    if regnskap.exists():
        r = json.loads(regnskap.read_text())
        if r["meldinger"] < GULV_MELDINGER:
            return f"{r['meldinger']} meldinger"
        if r["lengste_pause_s"] > GULV_PAUSE_S:
            return f"pause {r['lengste_pause_s']:.0f} s"
        return None
    if list(dag.glob(f"{time_}Z*.txt.zst")) or list(dag.glob(f".{time_}Z*.delvis")):
        return None  # lytteren har timen; regnskapet er ikke skrevet ennå
    return "tom"


def finn_hull(rot: Path, naa: datetime) -> list[tuple[str, str]]:
    ferdig = etterhentede(rot)
    t = (naa - ELDST).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    slutt = naa - YNGST
    hull = []
    while t + timedelta(hours=1) <= slutt:
        n = timenavn(t)
        if n not in ferdig and (grunn := er_hull(rot, n)):
            hull.append((n, grunn))
        t += timedelta(hours=1)
    return hull


def vinduer(hull: list[tuple[str, str]]) -> list[tuple[datetime, datetime]]:
    ut = []
    for n, _ in hull:
        t = tid(n)
        if ut and ut[-1][1] == t and ut[-1][1] - ut[-1][0] < timedelta(hours=MAKS_VINDU):
            ut[-1] = (ut[-1][0], t + timedelta(hours=1))
        else:
            ut.append((t, t + timedelta(hours=1)))
    return ut


class Token:
    def __init__(self):
        self.verdi, self.utloper = None, 0.0

    def hent(self, forny=False) -> str:
        # Veggklokke: om tokenet er utløpt, handler om verden (F13).
        if forny or not self.verdi or time.time() > self.utloper:
            env = dict(l.split("=", 1) for l in open(NOKKEL).read().splitlines() if "=" in l)
            data = urllib.parse.urlencode({
                "client_id": env["BW_AIS_CLIENT_ID"],
                "client_secret": env["BW_AIS_CLIENT_SECRET"],
                "grant_type": "client_credentials", "scope": "ais"}).encode()
            with urllib.request.urlopen(TOKEN_URL, data, timeout=30) as r:
                d = json.load(r)
            self.verdi = d["access_token"]
            self.utloper = time.time() + int(d.get("expires_in", 3600)) - 600
        return self.verdi


def kall(tok: Token, navn: str, url: str, body: dict | None = None) -> dict:
    """Ett kall, med én ny innlogging på 401. Svaret som en arkivlinje."""
    for forsok in (1, 2):
        hdr = {"Authorization": "Bearer " + tok.hent(forny=forsok == 2)}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdr["Content-Type"] = "application/json"
        t, t0 = naa_iso(), time.monotonic()  # varighet handler om oss: monotonic
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data, hdr), timeout=120) as r:
                status, tekst = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, tekst = e.code, e.read().decode(errors="replace")
        except Exception as e:  # noqa: BLE001 — et svar uten status er også et svar
            status, tekst = None, repr(e)
        linje = {"t": t, "kall": navn, "status": status,
                 "s": round(time.monotonic() - t0, 3), "body": tekst}
        if status != 401:
            return linje
    return linje


def hent_vindu(rot: Path, tok: Token, fra: datetime, til: datetime) -> Path:
    f, t = fra.strftime("%Y-%m-%dT%H:%M:%SZ"), til.strftime("%Y-%m-%dT%H:%M:%SZ")
    dag = rot / "etterhentet" / f[:10]
    dag.mkdir(parents=True, exist_ok=True)
    stamme = f"{f[:13]}Z--{t[:13]}Z"
    delvis = dag / f".{stamme}.delvis"
    if delvis.exists():
        delvis.unlink()  # et avbrutt vindu hentes på nytt fra start; det er ikke arkivert
    z = zstd.ZstdCompressor(level=19)
    with open(delvis, "xb") as ut:
        def skriv(linje):
            ut.write(z.compress((json.dumps(linje, ensure_ascii=False) + "\n").encode()))

        omr = kall(tok, "openaisarea", f"{LIVE}/v1/openaisarea")
        skriv(omr)
        pkt = [p for poly in json.loads(omr["body"])["coordinates"] for ring in poly for p in ring]
        lo0, lo1 = min(p[0] for p in pkt), max(p[0] for p in pkt)
        la0, la1 = min(p[1] for p in pkt), max(p[1] for p in pkt)
        rekt = {"type": "Polygon", "coordinates": [[[lo0, la0], [lo1, la0], [lo1, la1],
                                                     [lo0, la1], [lo0, la0]]]}
        liste = kall(tok, "mmsiinarea", f"{HIST}/v1/historic/mmsiinarea",
                     {"polygon": rekt, "msgTimeFrom": f, "msgTimeTo": t})
        skriv(liste)
        if liste["status"] != 200:
            raise RuntimeError(f"mmsiinarea {liste['status']}")
        mmsier = json.loads(liste["body"])
        logg(f"{stamme}: {len(mmsier)} MMSI")
        feil = 0
        qf, qt = urllib.parse.quote(f), urllib.parse.quote(t)
        for i, m in enumerate(mmsier, 1):
            time.sleep(PAUSE_S)
            linje = kall(tok, f"tracks {m}", f"{HIST}/v1/historic/tracks/{m}/{qf}/{qt}"
                         "?modelFormat=Json&filterSatellitePositions=false")
            feil += linje["status"] != 200
            skriv(linje)
            if i % 1000 == 0:
                logg(f"{stamme}: {i}/{len(mmsier)}, {feil} feil")
        ut.write(z.flush(zstd.ZstdCompressor.FLUSH_FRAME))
        ut.flush()
        os.fsync(ut.fileno())
    sti = dag / f"{stamme}.etterhentet.jsonl.zst"
    os.link(delvis, sti)  # feiler heller enn å overskrive
    os.chmod(sti, 0o444)
    delvis.unlink()
    sha = hashlib.sha256(sti.read_bytes()).hexdigest()
    with open(dag / "SHA256SUMS", "a") as m:
        m.write(f"{sha}  {sti.name}\n")
        m.flush()
        os.fsync(m.fileno())
    logg(f"ferdig {sti.name} {sti.stat().st_size} B, {len(mmsier)} MMSI, {feil} feil, sha256 {sha}")
    return sti


def main() -> None:
    rot = Path(sys.argv[1])
    maks = float(sys.argv[2]) if len(sys.argv) > 2 else 6 * 3600
    start = time.monotonic()  # hvor lenge VI har holdt på: monotonic
    naa = datetime.now(timezone.utc)
    hull = finn_hull(rot, naa)
    v = vinduer(hull)
    logg(f"{len(hull)} hull i {len(v)} vinduer: "
         + ", ".join(f"{n} ({g})" for n, g in hull[:12]) + (" …" if len(hull) > 12 else ""))
    tok = Token()
    for fra, til in v:
        if time.monotonic() - start > maks:
            logg(f"tidsgrensen {maks:.0f} s nådd; resten tas neste natt")
            break
        hent_vindu(rot, tok, fra, til)


if __name__ == "__main__":
    main()
