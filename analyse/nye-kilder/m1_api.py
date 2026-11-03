"""MALING-NYE-KILDER, steg 1: kandidatene som er API-er (a, b, f).

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/nye-kilder/m1_api.py 2026-11-03

Datoen er kjøredatoen og gis inn (CLAUDE.md 1b). Hver kropp arkiveres i
data/arkiv/maling-nye-kilder/ med `raw.arkiver_ny` (samme serialisering
som innsamlingen), og én logg, `<dato>.m1.logg.json`, fører hvert kall:
URL, metode, status, headere, bytes, sha256 av den serialiserte kroppen,
fila den ligger i og fetched_at.

  a  Fiskeridirektoratets flatelag (fiskeridirWMS_akva/MapServer/19):
     metadata, hele laget to ganger, og spørringen med historicMoment for
     01.09.2026. Wayback-oppslag for laget.
  b  BarentsWatch fiskehelse: v1-ukesvaret for uke 36/2026 (01.09.2026) i
     dag, mot innsamlingens kropp for samme uke; v3-sykdomshistorikk for
     lokalitetene med ILA eller PD den uka; v2-sonene for uke 36.
     Fiskeridirektoratets lag 26/27 (PD/ILA nå).
  f  BarentsWatch v2 (POST) for uke N..N-4 og uke 36, med v1 for de
     samme ukene hentet rett før, så parene er fra samme minutt.

Ingen snapshot, ingen changelog.
"""

import datetime as dt
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _barentswatch, _http  # noqa: E402
from sources._barentswatch import mandag, uke_med_etterslep  # noqa: E402

MAPPE = "maling-nye-kilder"
BW = "https://www.barentswatch.no/bwapi"
GIS = "https://gis.fiskeridir.no/server/rest/services/fiskeridirWMS_akva/MapServer"


def naa() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def main() -> None:
    kjoredato = dt.date.fromisoformat(sys.argv[1])
    logg: list[dict] = []

    def lagre(post: dict, data) -> None:
        ser, ext = raw._serialiser(data)
        sti = raw._ledig_sti(MAPPE, kjoredato.isoformat(), ext)
        sha, ny = raw.arkiver_ny(MAPPE, kjoredato.isoformat(), data)
        post.update(sha256=sha, byte_serialisert=len(ser),
                    fil=sti.name if ny else "(finnes fra før)")

    def kall(klient, metode: str, url: str, hva: str, *, json_kropp=None,
             params=None, arkiver=True):
        hentet = naa()
        t0 = time.monotonic()
        if metode == "POST":
            svar = _http.utfor(lambda: klient.post(url, json=json_kropp,
                                                   params=params), hva)
        else:
            svar = _http.get(klient, url, hva=hva, params=params)
        post = {
            "hva": hva, "metode": metode, "url": str(svar.request.url),
            "kropp_sendt": json_kropp, "status": svar.status_code,
            "fetched_at": hentet, "sekunder": round(time.monotonic() - t0, 3),
            "byte_utpakket": len(svar.content),
            "sha256_utpakket": hashlib.sha256(svar.content).hexdigest(),
            "headere": {k: v for k, v in svar.headers.items()
                        if k.lower() != "set-cookie"},
        }
        try:
            data = svar.json()
        except ValueError:
            data = svar.content
        if arkiver:
            lagre(post, data)
        logg.append(post)
        return data, post

    # ------------------------------------------------------------------ a
    with httpx.Client(timeout=120, follow_redirects=True) as k:
        kall(k, "GET", f"{GIS}/19", "a: metadata, lag 19", params={"f": "json"})
        q = {"where": "1=1", "outFields": "*", "returnGeometry": "true",
             "orderByFields": "loknr", "f": "json"}
        for n in (1, 2):
            kall(k, "GET", f"{GIS}/19/query", f"a: hele laget, henting {n}", params=q)
            time.sleep(20)
        ms = int(dt.datetime(2026, 9, 1, 12, tzinfo=dt.timezone.utc).timestamp() * 1000)
        kall(k, "GET", f"{GIS}/19/query", "a: historicMoment 01.09.2026",
             params=dict(q, historicMoment=str(ms), returnGeometry="false",
                         resultRecordCount="5"))
        kall(k, "GET", "https://archive.org/wayback/available",
             "a: wayback, lag 19 query",
             params={"url": f"{GIS}/19/query", "timestamp": "20260901"})
        kall(k, "GET", "https://web.archive.org/cdx/search/cdx",
             "a: wayback cdx, lag 19", params={
                 "url": "gis.fiskeridir.no/server/rest/services/fiskeridirWMS_akva/MapServer/19*",
                 "output": "json", "limit": "50"})

        # ---------------------------------------------------------- b (nå)
        for lag in (26, 27):
            kall(k, "GET", f"{GIS}/{lag}/query", f"b: Fiskeridir lag {lag}, nå",
                 params={"where": "1=1", "outFields": "*",
                         "returnGeometry": "false", "f": "json"})

    tilgang = _barentswatch.Tilgang("lusetall")
    klient = tilgang.klient()
    pause = _barentswatch.PAUSE_S
    try:
        # ------------------------------------------------------- b og f
        uker = [uke_med_etterslep(kjoredato, n) for n in range(0, 5)] + [(2026, 36)]
        for aar, uke in uker:
            v1, _ = kall(klient, "GET", f"{BW}/v1/geodata/fishhealth/locality/{aar}/{uke}",
                         f"f: v1 uke {uke}/{aar}")
            time.sleep(pause)
            kall(klient, "POST", f"{BW}/v2/geodata/fishhealth/locality/{aar}/{uke}",
                 f"f: v2 uke {uke}/{aar}", json_kropp={})
            time.sleep(pause)
            if (aar, uke) == (2026, 36):
                syke = sorted({l["localityNo"] for l in v1["localities"]
                               if l.get("hasIla") or l.get("hasPd")})
                logg.append({"hva": "b: lokaliteter med ILA/PD uke 36/2026 i v1 nå",
                             "localityNo": syke})
                for nr in syke[:6]:
                    kall(klient, "GET", f"{BW}/v3/geodata/fishhealth/locality/{nr}/disease",
                         f"b: v3 sykdomshistorikk {nr}")
                    time.sleep(pause)
                for sone in ("ilaprotectionzone", "pdprotectionzone"):
                    kall(klient, "GET", f"{BW}/v2/geodata/fishhealth/{sone}/2026/36",
                         f"b: v2 {sone} uke 36/2026")
                    time.sleep(pause)
                innsamlet = ARKIV_DIR / "lusetall" / f"{mandag(2026, 36)}.json.gz"
                if innsamlet.exists():
                    with gzip.open(innsamlet, "rb") as f:
                        b = f.read()
                    logg.append({"hva": "b: innsamlingens kropp uke 36/2026",
                                 "fil": f"lusetall/{innsamlet.name}",
                                 "sha256": hashlib.sha256(b).hexdigest()})
    finally:
        klient.close()

    ut = ARKIV_DIR / MAPPE / f"{kjoredato.isoformat()}.m1.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in logg:
        print(f"{p.get('status', ''):>4} {p.get('byte_utpakket', ''):>9} "
              f"{(p.get('sha256') or '')[:12]:<12} {p.get('fil', ''):<28} {p['hva']}")
    print(f"Logg: {ut}")


if __name__ == "__main__":
    main()
