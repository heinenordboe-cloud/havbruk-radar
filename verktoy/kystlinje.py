#!/usr/bin/env python3
"""Kartverkets kystkontur → ett avledet utdrag i repoet.

    python3 verktoy/kystlinje.py N500.zip N2000.zip

ZIPENE LASTES NED FOR HÅND, én gang, og ligger ALDRI i repoet. Skriptet
skriver ut sha256 av hver av dem, og den summen føres i
docs/design/KARTGEOMETRI.md. Det er proveniensen: uten den kan ingen
vite hvilken utgave utdraget er laget av, og Kartverket gir ut nye
versjoner uten at noe i dataene våre beveger seg.

    https://nedlasting.geonorge.no/geonorge/Basisdata/N500Kartdata/GML/
        Basisdata_0000_Norge_25833_N500Kartdata_GML.zip
    https://nedlasting.geonorge.no/geonorge/Basisdata/N2000Kartdata/GML/
        Basisdata_0000_Norge_25833_N2000Kartdata_GML.zip

## Hva utdraget er, og hvorfor det er ETT

`maler/geo/kystlinje.json.gz`. Byggetrinnet leser den og laster ALDRI
ned noe — samme regel som resten av nettstedet: en side som henter en
fil fra en tredjepart ser feil ut den dagen den tjenesten gjør det.

To oppløsninger i samme fil, fordi de svarer på hver sin ting:

    n500    lokalitetskartet, 36 km bredt. Bare det som ligger nær en
            lokalitet — se `NAERHET_M`.
    n2000   oversiktskartet på forsiden, hele kysten.

## Hva som hentes ut av GML-en

    Havflate      havet som FLATE, med øyer som interiørringer. Fylles
                  uten strek; da er en tilstøtende havflate usynlig.
    Kystkontur    kystlinja som LINJE. Tegnes som strek oppå fyllet.

De to holdes fra hverandre med vilje. Tegnes havflata med strek, vises
delelinjene mellom nabo-havflater som rette streker tvers over sjøen —
MÅLT på prøveklippene 25.09.2026.

## Avrundingen

Koordinatene er EPSG:25833, altså METER, og rundes til hele 10 m. Ved
36 km i 560 piksler er ett piksel 64 m: 10 m er en sjettedels piksel,
og en desimal til er en desimal ingen ser.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from kart import utm33                                     # noqa: E402
from core import snapshot                                  # noqa: E402

GML_NS = "{http://www.opengis.net/gml/3.2}"
UT = ROT / "maler" / "geo" / "kystlinje.json.gz"

# HVOR NÆR EN LOKALITET N500-GEOMETRIEN MÅ VÆRE.
#
# Lokalitetskartet er 36 km bredt og sentrert på lokaliteten, så
# halvdiagonalen er 25,5 km. 20 km er mindre enn det, og det er et valg:
# hjørnene av utsnittet kan mangle kystlinje der ingen lokalitet ligger
# innenfor 20 km, og de hjørnene er åpent hav eller innland. Prisen er
# målt — se KARTGEOMETRI.md.
NAERHET_M = 20_000

# Avrundingen. Meter.
RUTE_M = 10

TAK_BYTE = 3_000_000    # over dette: stopp og si fra


def sjekksum(sti: Path) -> str:
    h = hashlib.sha256()
    with sti.open("rb") as f:
        for bit in iter(lambda: f.read(1 << 20), b""):
            h.update(bit)
    return h.hexdigest()


def _arealdekke(zipsti: Path) -> bytes:
    """`Arealdekke`-GML-en ut av zipen, uten å pakke ut resten."""
    with zipfile.ZipFile(zipsti) as z:
        navn = [n for n in z.namelist() if "Arealdekke" in n and n.endswith(".gml")]
        if len(navn) != 1:
            raise SystemExit(f"{zipsti.name}: fant {len(navn)} Arealdekke-filer")
        return z.read(navn[0])


def _les(gml: bytes) -> tuple[list, list]:
    """(havflater som ringgrupper, kystkonturer som linjer).

    Ringene i én flate holdes SAMMEN: en øy er en interiørring, og
    tegnes den som sin egen bane blir den fylt som hav i stedet for å
    bli et hull.
    """
    hav: list[list[list[tuple[float, float]]]] = []
    kyst: list[list[tuple[float, float]]] = []
    for _, el in ET.iterparse(__import__("io").BytesIO(gml), events=("end",)):
        navn = el.tag.split("}")[-1]
        if navn not in ("Havflate", "Kystkontur"):
            continue
        ringer = []
        for pos in el.iter(GML_NS + "posList"):
            tall = [float(x) for x in pos.text.split()]
            ringer.append(list(zip(tall[0::2], tall[1::2])))
        if ringer:
            if navn == "Havflate":
                hav.append(ringer)
            else:
                kyst.extend(ringer)
        el.clear()
    return hav, kyst


def _boks(punkter) -> tuple[float, float, float, float]:
    xs = [p[0] for p in punkter]
    ys = [p[1] for p in punkter]
    return min(xs), min(ys), max(xs), max(ys)


def _naer(boks, rutenett: set[tuple[int, int]], steg: int) -> bool:
    """Berører bokså en rute der det ligger en lokalitet?

    Rutenettet er grovt med vilje: en eksakt avstandstest mot 1 782
    punkter for hver av 250 000 ringer er 445 millioner regnestykker.
    Ruta er `NAERHET_M` bred, så en treff-rute betyr «innenfor 20 til
    28 km» — og det slaget er på den RAUSE siden, som er den riktige:
    litt for mye geometri er noen kilobyte, litt for lite er et hull i
    kartet.
    """
    x0, y0, x1, y1 = boks
    for ix in range(int(x0 // steg), int(x1 // steg) + 1):
        for iy in range(int(y0 // steg), int(y1 // steg) + 1):
            if (ix, iy) in rutenett:
                return True
    return False


def lokalitetsruter(steg: int) -> set[tuple[int, int]]:
    """Rutene som ligger innenfor `NAERHET_M` av en lokalitet.

    Lokalitetene leses av NYESTE øyeblikksbilde av `akvakultur`. Kommer
    det en ny lokalitet et sted vi ikke har geometri, sier bygget fra —
    se `kart.py`. Utdraget lages på nytt da, ikke automatisk.
    """
    # SAMME VEI INN SOM NETTSTEDET. `snapshot.versjoner()` kjører
    # lesedøra; en `read_parquet` her ville gått utenom den.
    dato = snapshot.siste_dato("akvakultur")
    ramme = snapshot.versjoner("akvakultur", dato)[-1][1]
    import polars as pl
    rader = ramme.filter(pl.col("field").is_in(["breddegrad", "lengdegrad"]))
    per: dict[str, dict[str, str]] = {}
    for eid, felt, verdi in rader.select(["entity_id", "field", "value"]).iter_rows():
        per.setdefault(str(eid), {})[str(felt)] = str(verdi)

    ruter: set[tuple[int, int]] = set()
    n = 0
    for d in per.values():
        try:
            lat, lon = float(d["breddegrad"]), float(d["lengdegrad"])
        except (KeyError, ValueError):
            continue
        e, nord = utm33(lat, lon)
        n += 1
        # Rutene innenfor NAERHET_M i hver retning.
        r = int(math.ceil(NAERHET_M / steg))
        ix, iy = int(e // steg), int(nord // steg)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                ruter.add((ix + dx, iy + dy))
    print(f"  {n} lokaliteter -> {len(ruter)} ruter à {steg/1000:.0f} km")
    return ruter


def _rund(ring) -> list[list[int]]:
    """Meter rundet til `RUTE_M`, og punkter som faller sammen fjernet."""
    ut: list[list[int]] = []
    for x, y in ring:
        p = [int(round(x / RUTE_M)) * RUTE_M, int(round(y / RUTE_M)) * RUTE_M]
        if not ut or p != ut[-1]:
            ut.append(p)
    return ut


def utdrag(n500: Path, n2000: Path) -> dict:
    steg = NAERHET_M
    ruter = lokalitetsruter(steg)

    print(f"  leser {n500.name} …")
    hav5, kyst5 = _les(_arealdekke(n500))
    hav5_n = [[_rund(r) for r in flate] for flate in hav5
              if _naer(_boks([p for r in flate for p in r]), ruter, steg)]
    kyst5_n = [_rund(l) for l in kyst5 if _naer(_boks(l), ruter, steg)]
    print(f"    havflater {len(hav5)} -> {len(hav5_n)}   "
          f"kystlinjer {len(kyst5)} -> {len(kyst5_n)}")

    print(f"  leser {n2000.name} …")
    hav20, kyst20 = _les(_arealdekke(n2000))
    print(f"    havflater {len(hav20)}   kystlinjer {len(kyst20)}")

    return {
        "om": ("Kartverket, N500 og N2000 Kartdata, Arealdekke. "
               "CC BY 4.0 — © Kartverket. EPSG:25833, meter rundet "
               f"til {RUTE_M} m. Avledet av verktoy/kystlinje.py."),
        "epsg": 25833,
        "rute_m": RUTE_M,
        "naerhet_m": NAERHET_M,
        "n500": {"hav": hav5_n, "kyst": kyst5_n},
        "n2000": {"hav": [[_rund(r) for r in f] for f in hav20],
                  "kyst": [_rund(l) for l in kyst20]},
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.splitlines()[2].strip())
        return 2
    n500, n2000 = Path(sys.argv[1]), Path(sys.argv[2])
    for f in (n500, n2000):
        if not f.exists():
            raise SystemExit(f"{f} finnes ikke")
    print("Kildene, med sha256 — før i KARTGEOMETRI.md:")
    for f in (n500, n2000):
        print(f"  {f.name}\n    {f.stat().st_size} byte\n    {sjekksum(f)}")

    data = utdrag(n500, n2000)
    raa = json.dumps(data, separators=(",", ":")).encode("utf-8")
    pakket = gzip.compress(raa, 9, mtime=0)

    print(f"\n  ukomprimert {len(raa)/1e6:.2f} MB")
    print(f"  komprimert  {len(pakket)/1e6:.2f} MB")
    if len(pakket) > TAK_BYTE:
        print(f"\nSTOPP: utdraget er over {TAK_BYTE/1e6:.0f} MB. "
              f"Ikke skrevet. Rapporter før noe commites.")
        return 1

    UT.parent.mkdir(parents=True, exist_ok=True)
    UT.write_bytes(pakket)
    print(f"\n  skrevet {UT.relative_to(ROT)}")
    print(f"  sha256  {sjekksum(UT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
