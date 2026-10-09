"""Punkt 2: hva gir liceTreatments/{year} utover flaggene i lusetall?

Krever BARENTSWATCH_CLIENT_ID og BARENTSWATCH_CLIENT_SECRET i miljøet.
Skriver kroppene til /tmp/maling-okt/p2/ (aldri i git) og skriver ut
sha256 og feltstien til hver verdi som finnes i dem. Kjør:

    .venv/bin/python analyse/maling_okt/p2_licetreatments.py 11116 13284 45087

Lokalitetene er valgt fordi lusetall har `har_mekanisk_fjerning=True` i
flest uker i 2025 (33, 29 og 25).
"""
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources._barentswatch import Tilgang

UT = Path("/tmp/maling-okt/p2")
UT.mkdir(parents=True, exist_ok=True)
AAR = 2025


def stier(x, p=""):
    """Alle feltstier med verdi, lister slått sammen til []."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from stier(v, f"{p}.{k}" if p else k)
    elif isinstance(x, list):
        for v in x:
            yield from stier(v, p + "[]")
    elif x is not None:
        yield p, x


t = Tilgang("lusetall")
with t.klient() as c:
    for nr in sys.argv[1:] or ["11116", "13284", "45087"]:
        url = f"{t.base_url()}/v1/geodata/fishhealth/locality/{nr}/liceTreatments/{AAR}"
        r = t.get(c, url, hva=f"liceTreatments {nr}")
        b = r.content
        (UT / f"liceTreatments-{nr}-{AAR}.json").write_bytes(b)
        print(f"\n{nr} {AAR}  HTTP {r.status_code}  {len(b)} byte  "
              f"sha256 {hashlib.sha256(b).hexdigest()}  "
              f"content-type {r.headers.get('content-type')}  "
              f"last-modified {r.headers.get('last-modified')}")
        felt = collections.Counter()
        eks = {}
        for s, v in stier(json.loads(b)):
            felt[s] += 1
            eks.setdefault(s, v)
        for s, n in sorted(felt.items()):
            print(f"   {s:70s} {n:4d}  eks. {eks[s]!r}")
