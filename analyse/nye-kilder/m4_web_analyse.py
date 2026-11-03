"""MALING-NYE-KILDER, steg 4: tabellen for c, d og e av loggen fra steg 3.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/nye-kilder/m4_web_analyse.py 2026-11-03 \
        > analyse/nye-kilder/m4_web_analyse.txt

Leser bare arkivet. Hver arkivert kropp hashes på nytt og holdes mot loggen.
"""

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import ARKIV_DIR  # noqa: E402

MAPPE = ARKIV_DIR / "maling-nye-kilder"


def main() -> None:
    dato = sys.argv[1]
    logg = json.loads((MAPPE / f"{dato}.m3.logg.json").read_text(encoding="utf-8"))
    alle = {}
    for navn in (f"{dato}.m1.logg.json", f"{dato}.m1b.logg.json",
                 f"{dato}.m1c.logg.json", f"{dato}.m3.logg.json"):
        for p in json.loads((MAPPE / navn).read_text(encoding="utf-8")):
            if str(p.get("fil", "")).endswith(".gz"):
                alle.setdefault(p["sha256"], p["fil"])

    def kropp(p) -> bytes | None:
        if "sha256" not in p:
            return None
        fil = alle[p["sha256"]]
        b = gzip.decompress((MAPPE / fil).read_bytes())
        assert hashlib.sha256(b).hexdigest() == p["sha256"], p["hva"]
        return b

    for p in logg:
        b = kropp(p)
        fil = alle.get(p.get("sha256"), "—")
        if p["status"] == "feil":
            print(f"feil {p['hva']}: {p['feil'][:120]}")
            continue
        print(f"{p['status']:>4} {p['byte_utpakket']:>8} {(p.get('sha256') or p['sha256_utpakket'])[:16]}  "
              f"{fil:<24} {p['hva']}")
        if p["url_endelig"] != p["url"]:
            print(f"       videresendt til {p['url_endelig'][:110]}")
        if "saker" in p:
            print(f"       {p['saker']} saker, {p['dc_creator']} dc:creator, "
                  f"{p['content_encoded']} content:encoded, description-lengder "
                  f"{p['description_lengder']}, pubDate {p['pubDate_forste_siste']}")
        if b is None:
            continue
        if "robots.txt" in p["hva"] and p["status"] == 200:
            t = b.decode("utf-8", "replace")
            blokk = re.split(r"(?im)^\s*user-agent:\s*", t)
            for i, del_ in enumerate(blokk[1:], 1):
                linjer = [l.strip() for l in del_.splitlines() if l.strip()]
                agent = linjer[0]
                regler = [l for l in linjer[1:] if re.match(r"(?i)(dis)?allow|crawl-delay", l)]
                if agent == "*" or "/sok" in " ".join(regler) or regler == ["Disallow: /"]:
                    print(f"       User-agent {agent}: {regler[:6]}")
        if "metadata" in p["hva"]:
            m = json.loads(b)
            print(f"       {m.get('name')!r}: felt {[f['name'] for f in m.get('fields', [])]}")
        if "antall" in p["hva"]:
            print(f"       {json.loads(b)}")
        if "regjeringen, trafikklys" in p["hva"]:
            t = b.decode("utf-8", "replace")
            print(f"       tittel {re.search(r'<title>(.*?)</title>', t).group(1)!r}, "
                  f"challenges.cloudflare.com i kroppen: {'challenges.cloudflare.com' in t}")
        if "wayback" in p["hva"]:
            print(f"       {b[:160]!r}")


if __name__ == "__main__":
    main()
