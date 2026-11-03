"""MALING-NYE-KILDER, steg 3: kandidatene som er nettsider (c, d, e).

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/nye-kilder/m3_web.py 2026-11-03

Samme mappe og loggform som steg 1, i `<dato>.m3.logg.json`. To unntak fra
«hver kropp arkiveres», og de er med vilje:

  * RSS-strømmen fra iLaks arkiveres IKKE. Den har en byline per sak og
    personnavn i titlene (CLAUDE.md regel 3). Loggen fører sha256, antall
    saker, antall `dc:creator` og lengden på `description`, ikke innholdet.
  * Søknadslagene hos Fiskeridirektoratet arkiveres bare som metadata og
    antall. Postene har søkers navn og organisasjonsnummer uten
    organisasjonsform, og et ENK kan ikke skilles fra et AS der (regel 3).

Vilkårssidene arkiveres ikke her, men av arkiver_vilkar.py.
"""

import datetime as dt
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _http  # noqa: E402

MAPPE = "maling-nye-kilder"
SOK = "https://gis.fiskeridir.no/server/rest/services/Yggdrasil/Akvakultursøknader/MapServer"


def finn(sha: str) -> str:
    """Fila som allerede har de samme bytene (arkiver_ny skrev ikke)."""
    for f in sorted((ARKIV_DIR / MAPPE).glob("*.gz")):
        if hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest() == sha:
            return f.name
    raise LookupError(sha)


def main() -> None:
    dato = sys.argv[1]
    logg = []
    with httpx.Client(timeout=30, follow_redirects=True) as k:
        def kall(url, hva, *, arkiver=True, params=None, reserve=None):
            hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            # Ikke _http.get: en 403 eller 404 er selve målingen her.
            try:
                svar = k.get(url, params=params, headers={"User-Agent": _http.brukeragent()})
            except httpx.HTTPError as e:
                logg.append({"hva": hva, "url": url, "url_endelig": url, "status": "feil",
                             "feil": f"{type(e).__name__}: {e}", "fetched_at": hentet,
                             "byte_utpakket": 0, "sha256_utpakket": ""})
                return None
            post = {"hva": hva, "url": str(svar.request.url), "url_endelig": str(svar.url),
                    "status": svar.status_code, "fetched_at": hentet,
                    "byte_utpakket": len(svar.content),
                    "sha256_utpakket": hashlib.sha256(svar.content).hexdigest(),
                    "headere": {h: v for h, v in svar.headers.items()
                                if h.lower() != "set-cookie"}}
            if arkiver:
                sti = raw._ledig_sti(MAPPE, dato, "bin")
                sha, ny = raw.arkiver_ny(MAPPE, dato, svar.content)
                post.update(sha256=sha, fil=sti.name if ny else finn(sha))
            if reserve:
                post.update(reserve(svar.content))
            logg.append(post)
            return svar

        # c: robots.txt og strømmene
        for vert in ("www.ilaks.no", "www.kyst.no", "www.fiskeribladet.no", "www.intrafish.no"):
            kall(f"https://{vert}/robots.txt", f"c: robots.txt {vert}")

        def rss(b: bytes) -> dict:
            t = b.decode("utf-8", "replace")
            saker = re.findall(r"<item>(.*?)</item>", t, re.S)
            return {"saker": len(saker), "dc_creator": len(re.findall(r"<dc:creator>", t)),
                    "content_encoded": len(re.findall(r"<content:encoded>", t)),
                    "description_lengder": [len(m) for m in
                                            re.findall(r"<description>(.*?)</description>", t, re.S)],
                    "pubDate_forste_siste": [re.findall(r"<pubDate>(.*?)</pubDate>", t)[:1],
                                             re.findall(r"<pubDate>(.*?)</pubDate>", t)[-1:]]}
        kall("https://ilaks.no/feed/", "c: RSS iLaks (ikke arkivert)", arkiver=False, reserve=rss)
        for u in ("https://www.kyst.no/rss", "https://www.kyst.no/feed",
                  "https://www.fiskeribladet.no/rss", "https://www.intrafish.no/rss"):
            kall(u, f"c: RSS-forsøk {u} (ikke arkivert)", arkiver=False)

        # d: søknadslagene, bare metadata og antall
        for lag in (0, 2, 4):
            kall(f"{SOK}/{lag}", f"d: søknadslag {lag}, metadata", params={"f": "json"})
            kall(f"{SOK}/{lag}/query", f"d: søknadslag {lag}, antall",
                 params={"where": "1=1", "returnCountOnly": "true", "f": "json"})

        # e: sidene utgivelsesvakten kunne lest
        kall("https://ftp.nmdc.no/nmdc/IMR/Smittepress/regomr.geojson", "e: regomr.geojson")
        kall("https://trafikklyssystemet.no/Publikasjoner/Ekspertgrupperapporter",
             "e: ekspertgruppens rapportside (ikke arkivert, UBELAGT)", arkiver=False)
        kall("https://www.hi.no/hi/nettrapporter", "e: HIs rapportside (ikke arkivert, UBELAGT)",
             arkiver=False)
        kall("https://www.regjeringen.no/no/tema/mat-fiske-og-landbruk/fiskeri-og-havbruk/1/"
             "havbruk/trafikklyssystemet/id2788207/", "e: regjeringen, trafikklyssystemet")
        kall("https://www.regjeringen.no/robots.txt", "e: robots.txt regjeringen.no")
        kall("https://lovdata.no/robots.txt", "e: robots.txt lovdata.no")
        kall("https://lovdata.no/sok", "e: lovdata-søket, status",
             params={"q": "kapasitetsjustering"})
        kall("https://www.hi.no/robots.txt", "e: robots.txt hi.no")
        kall("https://web.archive.org/cdx/search/cdx", "e: wayback cdx, regjeringen trafikklys",
             params={"url": "regjeringen.no/no/tema/mat-fiske-og-landbruk/fiskeri-og-havbruk/1/havbruk/trafikklyssystemet/*",
                     "output": "json", "limit": "-5"})

    ut = ARKIV_DIR / MAPPE / f"{dato}.m3.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in logg:
        print(f"{p['status']:>4} {p['byte_utpakket']:>8} {(p.get('sha256') or p['sha256_utpakket'])[:12]} "
              f"{p.get('fil', '—'):<24} {p['hva']}")


if __name__ == "__main__":
    main()
