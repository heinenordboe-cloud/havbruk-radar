"""MALING-NYE-KILDER, steg 2: regner ut tallene for a, b og f av kroppene steg 1 la.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/nye-kilder/m2_api_analyse.py 2026-11-03 \
        > analyse/nye-kilder/m2_api_analyse.txt

Leser bare arkivet: loggen fra steg 1 sier hvilken fil hvert kall ligger i,
og hver kropp hashes på nytt og holdes mot loggen før den brukes. Henter
ingenting.
"""

import collections
import gzip
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import ARKIV_DIR  # noqa: E402

MAPPE = ARKIV_DIR / "maling-nye-kilder"
DELTE = (10181, 10229, 11015, 11665, 13246, 13527, 14679, 19755, 33797, 45002)


def main() -> None:
    dato = sys.argv[1]
    logg = (json.loads((MAPPE / f"{dato}.m1.logg.json").read_text(encoding="utf-8"))
            + json.loads((MAPPE / f"{dato}.m1b.logg.json").read_text(encoding="utf-8")))
    sha_for = {}

    def kropp(hva: str):
        p = next(p for p in logg if p["hva"] == hva)
        fil = p["fil"]
        if fil == "(finnes fra før)":
            fil = sha_for[p["sha256"]]
        b = gzip.decompress((MAPPE / fil).read_bytes())
        assert hashlib.sha256(b).hexdigest() == p["sha256"], hva
        return json.loads(b), fil, p

    for p in logg:
        if p.get("fil", "").endswith(".gz"):
            sha_for.setdefault(p.get("sha256"), p["fil"])

    print("== a. Flatelaget, fiskeridirWMS_akva/MapServer/19")
    meta, fil, _ = kropp("a: metadata, lag 19")
    print(f"metadata {fil}: copyrightText={meta.get('copyrightText')!r}")
    print(f"  felt: {[f['name'] for f in meta['fields']]}")
    print(f"  timeInfo={meta.get('timeInfo')!r} editingInfo={meta.get('editingInfo')!r} "
          f"supportsQueryWithHistoricMoment={meta.get('supportsQueryWithHistoricMoment')!r}")
    h1, f1, p1 = kropp("a: hele laget, henting 1")
    h2, f2, p2 = kropp("a: hele laget, henting 2")
    print(f"henting 1 {f1} {p1['sha256'][:16]}… {p1['byte_serialisert']} B, "
          f"henting 2 sha {p2['sha256'][:16]}… lik: {p1['sha256'] == p2['sha256']}, "
          f"{p1['fetched_at']} / {p2['fetched_at']}")
    feat = h1["features"]
    loknr = [f["attributes"]["loknr"] for f in feat]
    print(f"  {len(feat)} flater, {len(set(loknr))} ulike loknr, "
          f"exceededTransferLimit={h1.get('exceededTransferLimit')!r}")
    flere = collections.Counter(loknr)
    print(f"  loknr med mer enn én flate: {sum(1 for v in flere.values() if v > 1)}")
    print(f"  poster med geometri: {sum(1 for f in feat if f.get('geometry'))}")
    print(f"  status_lokalitet: {dict(collections.Counter(f['attributes']['status_lokalitet'] for f in feat))}")
    print(f"  de ti delte lokalitetene i laget: "
          f"{[(n, flere.get(n, 0)) for n in DELTE]}")
    m80, f80, _ = kropp("a: metadata, lag 80")
    print(f"lag 80 metadata {f80}: name={m80.get('name')!r} copyrightText={m80.get('copyrightText')!r} "
          f"geometryType={m80.get('geometryType')!r} timeInfo={m80.get('timeInfo')!r} "
          f"editingInfo={m80.get('editingInfo')!r}")
    g1, g1f, g1p = kropp("a: lag 80 hele, henting 1")
    _, _, g2p = kropp("a: lag 80 hele, henting 2")
    _, _, ghp = kropp("a: lag 80 historicMoment 01.09.2026")
    gf = g1["features"]
    gl = collections.Counter(f["attributes"]["loknr"] for f in gf)
    print(f"lag 80 henting 1 {g1f} {g1p['sha256'][:16]}… {g1p['byte_serialisert']} B; "
          f"henting 2 lik: {g1p['sha256'] == g2p['sha256']}; historicMoment lik dagens: "
          f"{ghp['sha256'] == g1p['sha256']}")
    print(f"  {len(gf)} flater, {len(gl)} ulike loknr, mer enn én flate: "
          f"{sum(1 for v in gl.values() if v > 1)}, exceededTransferLimit={g1.get('exceededTransferLimit')!r}")
    print(f"  med polygon: {sum(1 for f in gf if (f.get('geometry') or {}).get('rings'))}, "
          f"ringer {sum(len(f['geometry']['rings']) for f in gf)}, "
          f"punkter {sum(len(r) for f in gf for r in f['geometry']['rings'])}")
    print(f"  felt: {sorted(gf[0]['attributes'])}")
    print(f"  loknr i 19 og ikke i 80: {len(set(loknr) - set(gl))}; i 80 og ikke i 19: {len(set(gl) - set(loknr))}")
    print(f"  de ti delte lokalitetene i lag 80: {[(n, gl.get(n, 0)) for n in DELTE]}")
    hm, fhm, _ = kropp("a: historicMoment 01.09.2026")
    naa = {f["attributes"]["loknr"]: f["attributes"] for f in feat}
    like = all(naa.get(x["attributes"]["loknr"]) == x["attributes"] for x in hm["features"])
    print(f"historicMoment {fhm}: error={'error' in hm}, {len(hm.get('features', []))} rader, "
          f"attributtene lik dagens for alle: {like}")
    wb, fwb, _ = kropp("a: wayback, lag 19 query")
    cdx, fcdx, _ = kropp("a: wayback cdx, lag 19")
    print(f"wayback available {fwb}: {wb.get('archived_snapshots')!r}; cdx {fcdx}: {len(cdx)} rader")

    # Akvakultur-kroppen fra den daglige fangsten samme dag: hvor mange
    # lokaliteter har en flate?
    ak = sorted((ARKIV_DIR / "akvakultur").glob(f"{dato}*.json.gz"))
    if ak:
        b = gzip.decompress(ak[-1].read_bytes())
        sites = json.loads(b)
        nr = {s.get("siteNr") for s in sites}
        print(f"akvakultur/{ak[-1].name} {hashlib.sha256(b).hexdigest()[:16]}…: "
              f"{len(nr)} lokaliteter; med flate i lag 80 {len(nr & set(gl))}, "
              f"flate uten lokalitet i kroppen {len(set(gl) - nr)}")

    print("\n== b. Fiskehelse")
    for lag in (26, 27):
        d, f, _ = kropp(f"b: Fiskeridir lag {lag}, nå")
        a = [x["attributes"] for x in d["features"]]
        print(f"lag {lag} {f}: {len(a)} rader; status {dict(collections.Counter(x['status_sykdom'] for x in a))}")
    v1, fv1, pv1 = kropp("f: v1 uke 36/2026")
    inn = ARKIV_DIR / "lusetall" / "2026-08-31.json.gz"
    bi = gzip.decompress(inn.read_bytes())
    vi = json.loads(bi)
    print(f"uke 36/2026 i dag {fv1} {pv1['sha256'][:16]}… mot innsamlingen lusetall/{inn.name} "
          f"{hashlib.sha256(bi).hexdigest()[:16]}…: lik={pv1['sha256'] == hashlib.sha256(bi).hexdigest()}")
    a_ = {l["localityNo"]: l for l in v1["localities"]}
    b_ = {l["localityNo"]: l for l in vi["localities"]}
    print(f"  lokaliteter i dag {len(a_)}, i innsamlingen {len(b_)}, felles {len(a_.keys() & b_.keys())}")
    for felt in sorted({k for l in list(a_.values()) + list(b_.values()) for k in l} - {"localityNo"}):
        ulik = sum(1 for k in a_.keys() & b_.keys() if a_[k].get(felt) != b_[k].get(felt))
        print(f"  {felt:<22} ulik i {ulik}")
    print(f"  ILA i dag {sum(1 for l in a_.values() if l['hasIla'])}, PD i dag "
          f"{sum(1 for l in a_.values() if l['hasPd'])}; ILA i innsamlingen "
          f"{sum(1 for l in b_.values() if l['hasIla'])}, PD {sum(1 for l in b_.values() if l['hasPd'])}")
    syke = next(p for p in logg if p["hva"].startswith("b: lokaliteter med ILA/PD"))["localityNo"]
    for nr in syke[:6]:
        d, f, _ = kropp(f"b: v3 sykdomshistorikk {nr}")
        print(f"  v3 {nr} {f}: {len(d)} tilfeller; "
              f"{[(x['name'], x['status'], (x.get('suspicionDate') or '')[:10], (x.get('diagnosisDate') or '')[:10], (x.get('closureDate') or '')[:10]) for x in d]}")
    for sone in ("ilaprotectionzone", "pdprotectionzone"):
        d, f, _ = kropp(f"b: v2 {sone} uke 36/2026")
        print(f"  v2 {sone} uke 36/2026 {f}: {type(d).__name__} med {len(d)} elementer")

    print("\n== f. v1 mot v2, samme minutt")
    uker = [p["hva"][len("f: v1 uke "):] for p in logg if p["hva"].startswith("f: v1 uke ")]
    for u in uker:
        v1, f1, p1 = kropp(f"f: v1 uke {u}")
        v2, f2, p2 = kropp(f"f: v2 uke {u}")
        a1 = {l["localityNo"]: l for l in v1["localities"]}
        a2 = {l["locality"]["no"]: l for l in v2}
        felles = a1.keys() & a2.keys()
        av = sum(1 for k in felles
                 if a1[k]["avgAdultFemaleLice"] != (a2[k]["liceReport"] or {}).get("adultFemaleLice", {}).get("average"))
        rap = sum(1 for k in felles if a1[k]["hasReportedLice"] != (a2[k]["liceReport"] or {}).get("hasReported"))
        fal = sum(1 for k in felles if a1[k]["isFallow"] != (a2[k]["liceReport"] or {}).get("isFallow"))
        ila = sum(1 for k in felles if a1[k]["hasIla"] != any("LAKSEANEMI" in d for d in a2[k]["diseases"]))
        pd = sum(1 for k in felles if a1[k]["hasPd"] != any("PANKREAS" in d for d in a2[k]["diseases"]))
        wid = sum(1 for k in felles if a1[k]["localityWeekId"] != a2[k]["localityWeekId"])
        print(f"uke {u:<8} v1 {f1:<20} {p1['byte_utpakket']:>8} B  v2 {f2:<20} {p2['byte_utpakket']:>8} B  "
              f"lok v1 {len(a1)} v2 {len(a2)} felles {len(felles)}  ulik: snitt hunnlus {av}, "
              f"rapportert {rap}, brakk {fal}, ILA {ila}, PD {pd}, localityWeekId {wid}")
        def retning(f1, f2):
            a = sum(1 for k in felles if f1(a1[k]) and not f2(a2[k]))
            b = sum(1 for k in felles if not f1(a1[k]) and f2(a2[k]))
            return f"{a} bare v1 / {b} bare v2"
        print(f"    ILA {retning(lambda x: x['hasIla'], lambda x: 'INFEKSIOES_LAKSEANEMI' in x['diseases'])}; "
              f"PD {retning(lambda x: x['hasPd'], lambda x: 'PANKREASSYKDOM' in x['diseases'])}; "
              f"laksefisk {retning(lambda x: x['hasSalmonoids'], lambda x: x['hasSalmonoidLicense'])}; "
              f"slaktemerd {retning(lambda x: x['isSlaughterHoldingCage'], lambda x: x['isSlaughterHoldingCage'])}; "
              f"på land {retning(lambda x: x['isOnLand'], lambda x: x['locality']['isOnLand'])}; "
              f"behandling {retning(lambda x: x['hasMechanicalRemoval'] or x['hasSubstanceTreatments'], lambda x: bool(x['liceTreatments']))}; "
              f"navn ulik {sum(1 for k in felles if a1[k]['name'] != a2[k]['locality']['name'])}, "
              f"kommunenr ulik {sum(1 for k in felles if a1[k]['municipalityNo'] != a2[k]['municipality']['no'])}")
    nokler = collections.Counter()
    sykdom = collections.Counter()
    for l in v2:
        nokler.update(l.keys())
        sykdom.update(l["diseases"])
    print(f"v2 toppnivåfelt: {sorted(nokler)}")
    print(f"v2 liceReport-felt: {sorted({k for l in v2 for k in (l['liceReport'] or {})})}")
    print(f"v2 sykdomsnavn (siste uke over): {dict(sykdom)}")
    print(f"v1 felt: {sorted({k for l in v1['localities'] for k in l})}")


if __name__ == "__main__":
    main()
