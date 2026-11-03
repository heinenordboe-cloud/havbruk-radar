"""MALING-NYE-KILDER, etterskrift 03.11.2026, punkt 0 og 5: Lovdata.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/lovdata/l1_hent.py 2026-11-03

Henter og arkiverer i `data/arkiv/maling-lovdata/`, med loggen
`<dato>.l1.logg.json` (URL, status, headere, sha256, fil, `fetched_at`),
samme form som analyse/nye-kilder/m3_web.py:

  * robots.txt for lovdata.no og api.lovdata.no, slik de er nå;
  * Wayback-CDX for de to robots.txt-ene og én kopi (`id_`) per digest,
    den siste kopien for hver;
  * to metadatakall mot api.lovdata.no: lista over de åpne pakkene og
    API-spesifikasjonen.

Ingen pakke lastes ned. robots.txt for api.lovdata.no stenger hele
verten for `*`, og STOPP-regelen i etterskriften holder nedlastingen
tilbake til Heine har bestemt (se dokumentet).
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
from sources import _http  # noqa: E402

MAPPE = "maling-lovdata"
CDX = "https://web.archive.org/cdx/search/cdx"


def finn(sha: str) -> str:
    """Fila som allerede har de samme bytene (arkiver_ny skrev ikke)."""
    for f in sorted((ARKIV_DIR / MAPPE).glob("*.gz")):
        if hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest() == sha:
            return f.name
    raise LookupError(sha)


def main() -> None:
    dato = sys.argv[1]
    logg = []
    with httpx.Client(timeout=60, follow_redirects=True) as k:
        def kall(url, hva, *, params=None, forsok=1):
            for n in range(forsok):
                hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                try:
                    svar = k.get(url, params=params,
                                 headers={"User-Agent": _http.brukeragent()})
                except httpx.HTTPError as e:
                    svar, feil = None, f"{type(e).__name__}: {e}"
                # Internet Archive svarer «Temporarily Offline» med 503
                # deler av kvelden (MALING-NYE-KILDER F1.4).
                if svar is not None and svar.status_code < 500:
                    break
                if n + 1 < forsok:
                    time.sleep(20)
            if svar is None:
                logg.append({"hva": hva, "url": url, "status": "feil", "feil": feil,
                             "fetched_at": hentet, "byte_utpakket": 0,
                             "sha256_utpakket": ""})
                return None
            post = {"hva": hva, "url": str(svar.request.url), "url_endelig": str(svar.url),
                    "status": svar.status_code, "fetched_at": hentet,
                    "byte_utpakket": len(svar.content),
                    "sha256_utpakket": hashlib.sha256(svar.content).hexdigest(),
                    "headere": {h: v for h, v in svar.headers.items()
                                if h.lower() != "set-cookie"}}
            sti = raw._ledig_sti(MAPPE, dato, "bin")
            sha, ny = raw.arkiver_ny(MAPPE, dato, svar.content)
            post.update(sha256=sha, fil=sti.name if ny else finn(sha))
            logg.append(post)
            return svar

        kall("https://lovdata.no/robots.txt", "robots.txt lovdata.no")
        kall("https://api.lovdata.no/robots.txt", "robots.txt api.lovdata.no")

        for vert in ("lovdata.no", "api.lovdata.no"):
            svar = kall(CDX, f"wayback cdx, robots.txt {vert}", forsok=4,
                        params={"url": f"{vert}/robots.txt", "from": "2025",
                                "output": "json",
                                "fl": "timestamp,statuscode,digest,length"})
            try:
                rader = svar.json()[1:] if svar is not None else []
            except ValueError:
                rader = []
            siste = {}
            for ts, status, digest, _ in rader:
                if status == "200":
                    siste[digest] = ts
            for digest, ts in sorted(siste.items(), key=lambda p: p[1]):
                kall(f"https://web.archive.org/web/{ts}id_/https://{vert}/robots.txt",
                     f"wayback-kopi robots.txt {vert} {ts} (digest {digest})", forsok=4)

        kall("https://api.lovdata.no/v1/publicData/list", "api: lista over åpne pakker")
        kall("https://api.lovdata.no/swagger/api.json", "api: spesifikasjonen")

    ut = ARKIV_DIR / MAPPE / f"{dato}.l1.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in logg:
        print(f"{p['status']:>4} {p['byte_utpakket']:>8} "
              f"{(p.get('sha256') or p['sha256_utpakket'])[:12]} "
              f"{p.get('fil', '—'):<20} {p['fetched_at']}  {p['hva']}")


if __name__ == "__main__":
    main()
