"""Punkt 1: +1 % kapasitet i uke 41, målt mot arkivkroppene for eierskap.

Leser bare data/arkiv/eierskap og data/arkiv/trafikklysvedtak. Skriver
ingenting. Kjør:  HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
    .venv/bin/python analyse/maling_okt/p1_kapasitet_uke41.py
"""
import collections
import gzip
import hashlib
import html
import json
import os
import re
from pathlib import Path

D = Path(os.environ.get("HAVBRUK_DATA_DIR", "../havbruk-radar-data/data"))


def kropp(sti):
    b = gzip.open(sti, "rb").read()
    return hashlib.sha256(b).hexdigest(), b


def tillatelser(dato):
    h, b = kropp(D / "arkiv/eierskap" / f"{dato}.json.gz")
    r = json.loads(b)
    return h, r["personer_fjernet"], {l["licenseNr"]: l for l in r["tillatelser"]}


def kapasitet(l):
    return (l.get("capacity") or {}).get("current")


# 1. Kapasitetsendringer mellom hver påfølgende kropp
datoer = sorted(p.name[:10] for p in (D / "arkiv/eierskap").glob("*.json.gz"))
forrige = None
for d in datoer:
    h, fjernet, L = tillatelser(d)
    if forrige:
        endr = [n for n in L if n in forrige and kapasitet(forrige[n]) != kapasitet(L[n])]
        pluss1 = sum(1 for n in endr if round(kapasitet(forrige[n]) * 1.01) == kapasitet(L[n]))
        print(f"{d}  sha256 {h}  tillatelser {len(L)}  personer_fjernet {fjernet}  "
              f"kapasitet endret {len(endr)}  derav round(x*1.01) {pluss1}")
    forrige = L

# 2. Uke 40 mot uke 41
_, _, l0 = tillatelser("2026-09-28")
_, _, l1 = tillatelser("2026-10-05")
endr = sorted(n for n in l1 if n in l0 and kapasitet(l0[n]) != kapasitet(l1[n]))
per = collections.defaultdict(lambda: [0, 0.0])
for n in endr:
    l = l1[n]
    assert l["capacity"]["unit"] == "TN" and l["capacity"]["type"] == "MTK"
    k = (l["placement"]["prodAreaCode"], l["legalEntityName"], l["openLegalEntityNr"])
    per[k][0] += 1
    per[k][1] += kapasitet(l) - kapasitet(l0[n])
print("\nPO | selskap | orgnr | tillatelser | tonn økt")
for k, (n, t) in sorted(per.items(), key=lambda x: int(x[0][0])):
    print(*k, n, t, sep=" | ")
print("sum tonn", sum(v[1] for v in per.values()))

# Hvor mange kommersielle matfisktillatelser fantes i de tre områdene
grunn = collections.Counter(
    str(l["placement"]["prodAreaCode"]) for l in l1.values()
    if str((l.get("placement") or {}).get("prodAreaCode")) in ("1", "12", "13")
    and (l.get("type") or {}).get("tag") == "KOMM-MATF")
print("KOMM-MATF i kroppen per PO:", dict(grunn))

for n in sorted(set(l1) - set(l0)):
    print("ny", n, l1[n]["legalEntityName"], l1[n]["type"]["tag"], kapasitet(l1[n]))
for n in sorted(set(l0) - set(l1)):
    print("borte", n, l0[n]["legalEntityName"], l0[n]["type"]["tag"], kapasitet(l0[n]))

# 3. Forskriftene: 1 %-kapitlet i hver versjon
for f in sorted((D / "arkiv/trafikklysvedtak").glob("*.bin.gz")):
    h, b = kropp(f)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", b.decode(), flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    def finn(p):
        m = re.search(p, t)
        return m.group(0) if m else None
    print(f"\n{f.name}  sha256 {h}")
    for p in (r"Dato FOR-\S+", r"med (1 prosent|2 pst\.) mot", r"Vederlaget er [\d .]+kroner",
              r"Søknaden skal sendes senest \d+\. \w+ \d{4}",
              r"Kapittel [23] (om økt kapasitet på eksisterende tillatelser )?gjelder"
              r"( tillatelser hjemmehørende i| tillatelse hjemmehørende i| for)? følgende[^§]*?(?=🔗)"):
        print("  ", finn(p))
