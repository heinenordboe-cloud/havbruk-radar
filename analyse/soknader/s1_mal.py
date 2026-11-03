"""MALING-NYE-KILDER, etterskrift 03.11.2026 (økt 4b, punkt 1): søknadslaget.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/soknader/s1_mal.py 2026-11-03 \
        > analyse/soknader/s1_mal.txt

Henter `Yggdrasil/Akvakultursøknader/MapServer` hos Fiskeridirektoratet og
måler punkt 1a, 1b og 1d. Loggen er `maling-soknader/<dato>.s1.logg.json`
i datarepoets arkiv, samme form som analyse/nye-kilder/m3_web.py.

Hva som arkiveres, og hva som ikke gjør det (CLAUDE.md regel 3):

  * metadata for tjenesten og hvert lag: arkivert;
  * postene slik de kom: IKKE arkivert. Loggen fører sha256, antall og
    lengde. Søkers navn og organisasjonsnummer står der uten
    organisasjonsform;
  * postene etter persondatafilteret (`filtrer` under): arkivert. Det er
    samme filter som fangsten bruker, så tallene om de filtrerte postene
    er holdt mot en kropp;
  * Brreg-oppslagene: IKKE arkivert. Bare antall per organisasjonsform
    og status står i utskriften, aldri et nummer som peker på en person.

Filteret, «vet ikke = filtreres ut»: en post slipper gjennom bare når
`applicantorganisationnumber` er ni siffer OG Brreg oppgir en
organisasjonsform OG verken formen eller sektoren er en personform
(`core/persondata.er_personform`, `er_personsektor`). 404, 410, tomt
nummer, feil i oppslaget: posten filtreres.
"""

import datetime as dt
import gzip
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import persondata  # noqa: E402
from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _http  # noqa: E402

MAPPE = "maling-soknader"
SOK = "https://gis.fiskeridir.no/server/rest/services/Yggdrasil/Akvakultursøknader/MapServer"
BRREG = "https://data.brreg.no/enhetsregisteret/api/enheter"
LAG = {0: "under behandling", 1: "forankringspunkt", 2: "flate",
       4: "ferdigbehandlet", 5: "flate ferdigbehandlet",
       6: "gammel flate", 7: "forankringspunkt ferdigbehandlet"}
DATOFELT = ("submittedat", "withdrawnat", "evaluationfinishedat")
DATO_HIST = dt.datetime(2026, 9, 1, 12, tzinfo=dt.timezone.utc)
NI = re.compile(r"^\d{9}$")


def finn(sha: str) -> str:
    for f in sorted((ARKIV_DIR / MAPPE).glob("*.gz")):
        if hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest() == sha:
            return f.name
    raise LookupError(sha)


def brreg_former(k: httpx.Client, nr: set[str]) -> dict[str, dict]:
    """orgnr -> {"status", "form", "sektor"}. Aldri navn."""
    ut: dict[str, dict] = {}
    liste = sorted(n for n in nr if NI.match(n))
    for i in range(0, len(liste), 100):
        bit = liste[i:i + 100]
        r = k.get(BRREG, params={"organisasjonsnummer": ",".join(bit), "size": 100},
                  headers={"Accept": "application/json", "User-Agent": _http.brukeragent()})
        r.raise_for_status()
        for e in (r.json().get("_embedded") or {}).get("enheter", []):
            ut[e["organisasjonsnummer"]] = {
                "status": "ok", "form": (e.get("organisasjonsform") or {}).get("kode", ""),
                "sektor": (e.get("institusjonellSektorkode") or {}).get("kode", "")}
    # Lista svarer bare for enheter som finnes. Slettede svarer 200 med
    # `SlettetEnhet` på enkeltoppslaget; 404 og 410 er «vet ikke».
    for n in liste:
        if n in ut:
            continue
        r = k.get(f"{BRREG}/{n}", headers={"Accept": "application/json",
                                           "User-Agent": _http.brukeragent()})
        if r.status_code in (404, 410):
            ut[n] = {"status": f"http {r.status_code}", "form": "", "sektor": ""}
            continue
        r.raise_for_status()
        d = r.json()
        ut[n] = {"status": "slettet" if d.get("slettedato") else "ok",
                 "form": (d.get("organisasjonsform") or {}).get("kode", ""),
                 "sektor": (d.get("institusjonellSektorkode") or {}).get("kode", "")}
    return ut


def slipper(post: dict, former: dict[str, dict]) -> tuple[bool, str]:
    nr = str(post.get("applicantorganisationnumber") or "").strip()
    if not NI.match(nr):
        return False, "ikke ni siffer"
    f = former.get(nr)
    if f is None or not f["form"]:
        return False, f"vet ikke ({f['status'] if f else 'ikke slått opp'})"
    if persondata.er_personform(f["form"]) or persondata.er_personsektor(f["sektor"]):
        return False, f"personform {f['form']}/{f['sektor'] or '—'}"
    return True, f["form"]


def avstand_km(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def main() -> None:
    dato = sys.argv[1]
    logg: list[dict] = []
    k = httpx.Client(timeout=120, follow_redirects=True)

    def kall(url, hva, params=None, *, arkiver=True, kropp=None):
        hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        if kropp is None:
            svar = k.get(url, params=params, headers={"User-Agent": _http.brukeragent()})
            svar.raise_for_status()
            innhold, status, adr = svar.content, svar.status_code, str(svar.request.url)
        else:
            innhold, status, adr = kropp, "avledet", url
        post = {"hva": hva, "url": adr, "status": status, "fetched_at": hentet,
                "byte_utpakket": len(innhold),
                "sha256_utpakket": hashlib.sha256(innhold).hexdigest()}
        if arkiver:
            sti = raw._ledig_sti(MAPPE, dato, "json")
            sha, ny = raw.arkiver_ny(MAPPE, dato, json.loads(innhold))
            post.update(sha256=sha, fil=sti.name if ny else finn(sha))
        logg.append(post)
        return json.loads(innhold), post

    meta, _ = kall(SOK, "tjenesten, metadata", {"f": "json"})
    print(f"Tjenesten: copyrightText «{meta.get('copyrightText')}», lag "
          f"{[(l['id'], l['name']) for l in meta['layers']]}, tabeller {meta.get('tables')}")

    lagmeta, poster, rasha = {}, {}, {}
    for lag in LAG:
        m, _ = kall(f"{SOK}/{lag}", f"lag {lag}, metadata", {"f": "json"})
        lagmeta[lag] = m
        q = {"where": "1=1", "outFields": "*", "returnGeometry": "false",
             "orderByFields": "objectid", "f": "json"}
        # Lag 1 har flere poster enn maxRecordCount (2000): sidevis.
        poster[lag], side = [], 0
        while True:
            d, p = kall(f"{SOK}/{lag}/query",
                        f"lag {lag}, poster fra {side} (IKKE arkivert)",
                        dict(q, resultOffset=side), arkiver=False)
            poster[lag] += [f["attributes"] for f in d["features"]]
            if side == 0:
                rasha[lag] = p["sha256_utpakket"]
            if not d.get("exceededTransferLimit"):
                break
            side += len(d["features"])
        # 1a: historicMoment. Samme spørring, med og uten.
        if lag in (0, 4):
            d2, p2 = kall(f"{SOK}/{lag}/query",
                          f"lag {lag}, historicMoment 01.09.2026 12 UTC (IKKE arkivert)",
                          dict(q, resultOffset=0,
                               historicMoment=str(int(DATO_HIST.timestamp() * 1000))),
                          arkiver=False)
            p2["lik_uten"] = p2["sha256_utpakket"] == rasha[lag]

    print("\n== 1a. Lagene")
    for lag, navn in LAG.items():
        m = lagmeta[lag]
        print(f"lag {lag} {navn}: {len(poster[lag])} poster, timeInfo {m.get('timeInfo')}, "
              f"editingInfo {m.get('editingInfo')}, supportsQueryWithHistoricMoment "
              f"{m.get('supportsQueryWithHistoricMoment')}, relationships {m.get('relationships')}")
        print(f"   felt: {', '.join(f['name'] for f in m.get('fields') or [])}")
    for p in logg:
        if "lik_uten" in p:
            print(f"{p['hva']}: sha256 {p['sha256_utpakket'][:16]}, lik spørringen uten: {p['lik_uten']}")

    for lag in (0, 4):
        ps = poster[lag]
        print(f"\nlag {lag} ({LAG[lag]}), {len(ps)} poster")
        for felt in ("status_application", "evaluation_result", "soeknadstype", "type"):
            if ps and felt in ps[0]:
                print(f"   {felt}: {dict(Counter(p.get(felt) for p in ps).most_common())}")
        for felt in DATOFELT:
            if ps and felt in ps[0]:
                v = [p[felt] for p in ps if p.get(felt)]
                if v:
                    a, b = (dt.datetime.fromtimestamp(x / 1000, dt.timezone.utc).date() for x in (min(v), max(v)))
                    print(f"   {felt}: {len(v)} satt, {a} – {b}")
                else:
                    print(f"   {felt}: 0 satt")
        n_mtb = sum(1 for p in ps if p.get("desiredbiomass_value") not in (None, 0))
        print(f"   desiredbiomass_value (omsøkt MTB) satt i {n_mtb}")
        nr = Counter(p.get("applicationno") for p in ps)
        print(f"   applicationno: {len(nr)} ulike, {sum(1 for v in nr.values() if v > 1)} går igjen")

    # Hvor ofte endres tilstanden: hendelser per 30 døgn etter datoene.
    # Det er det eneste lagene selv sier; en endring i omsøkt MTB eller
    # status uten ny dato kan ikke ses i én henting.
    naa = dt.datetime.fromisoformat(dato + "T00:00:00+00:00").timestamp() * 1000
    for navn, lag, felt in (("innsendt", 0, "submittedat"), ("innsendt", 4, "submittedat"),
                            ("ferdigbehandlet", 4, "evaluationfinishedat"),
                            ("trukket", 4, "withdrawnat")):
        n = sum(1 for p in poster[lag] if (p.get(felt) or 0) >= naa - 30 * 86400000)
        print(f"siste 30 døgn før {dato}: {n} {navn} (lag {lag}, {felt})")

    a0 = {p["applicationno"] for p in poster[0]}
    a4 = {p["applicationno"] for p in poster[4]}
    print(f"\nsøknadsnummer i både lag 0 og lag 4: {len(a0 & a4)}")

    # 1a: tilstanden 01.09.2026 regnet ut av datoene i lag 4.
    t = DATO_HIST.timestamp() * 1000
    innsendt_for = [p for p in poster[4] if p.get("submittedat") and p["submittedat"] < t]
    aapen = [p for p in innsendt_for
             if not ((p.get("evaluationfinishedat") or math.inf) < t
                     or (p.get("withdrawnat") or math.inf) < t)]
    uten_slutt = [p for p in poster[4] if not p.get("evaluationfinishedat") and not p.get("withdrawnat")]
    print(f"lag 4: {len(innsendt_for)} innsendt før 01.09.2026, {len(aapen)} av dem var ikke "
          f"avsluttet da (etter datoene); {len(uten_slutt)} har verken evaluationfinishedat "
          f"eller withdrawnat")
    l0_for = [p for p in poster[0] if p.get("submittedat") and p["submittedat"] < t]
    l0_uten = [p for p in poster[0] if not p.get("submittedat")]
    print(f"lag 0: {len(l0_for)} innsendt før 01.09.2026, {len(l0_uten)} uten submittedat "
          f"(status: {dict(Counter(p.get('status_application') for p in l0_uten))})")

    # 1b: søker
    alle_nr = {str(p.get("applicantorganisationnumber") or "").strip()
               for lag in LAG for p in poster[lag]}
    former = brreg_former(k, alle_nr)
    print("\n== 1b. Søker")
    print(f"ulike søkernummer i alle lag: {len(alle_nr)}, ni siffer: "
          f"{sum(1 for n in alle_nr if NI.match(n))}, tomme: {sum(1 for n in alle_nr if not n)}")
    print(f"Brreg: {dict(Counter(f['status'] for f in former.values()))}")
    print(f"former: {dict(Counter(f['form'] or '—' for f in former.values()).most_common())}")
    print(f"sektor 8200/2300: {sum(1 for f in former.values() if persondata.er_personsektor(f['sektor']))}")
    filtrert = {}
    for lag in LAG:
        grunner = Counter()
        beholdt = []
        for p in poster[lag]:
            ok, g = slipper(p, former)
            grunner["slipper" if ok else g.split(" (")[0].split(" ")[0]] += 1
            if ok:
                beholdt.append(p)
        filtrert[lag] = beholdt
        print(f"lag {lag}: {len(poster[lag])} poster, {dict(grunner.most_common())}")

    for lag in (0, 2, 4):
        kropp = json.dumps({"lag": lag, "features": filtrert[lag]}, ensure_ascii=False,
                           sort_keys=True).encode("utf-8")
        kall(f"{SOK}/{lag}/query", f"lag {lag}, etter persondatafilteret", kropp=kropp)

    # 1d: kobling til lokalitetsregisteret (akvakultur-kroppene i arkivet)
    print("\n== 1d. Kobling til lokalitetsnummer")
    kropper = sorted((ARKIV_DIR / "akvakultur").glob("*.json.gz"), key=raw.orden)
    forste = json.loads(gzip.decompress(kropper[0].read_bytes()))
    siste = json.loads(gzip.decompress(kropper[-1].read_bytes()))
    alle_sites: dict[str, tuple] = {}
    forst_sett: dict[str, str] = {}
    for f in kropper:
        for s in json.loads(gzip.decompress(f.read_bytes())):
            nr = str(s.get("siteNr"))
            alle_sites.setdefault(nr, (s.get("latitude"), s.get("longitude")))
            forst_sett.setdefault(nr, f.name)
    print(f"akvakultur-kropper: {len(kropper)}, {kropper[0].name} ({len(forste)} lokaliteter, "
          f"sha256 {hashlib.sha256(gzip.decompress(kropper[0].read_bytes())).hexdigest()[:16]}) – "
          f"{kropper[-1].name} ({len(siste)}, sha256 "
          f"{hashlib.sha256(gzip.decompress(kropper[-1].read_bytes())).hexdigest()[:16]}); "
          f"{len(alle_sites)} ulike lokalitetsnummer i alle")
    for lag in (0, 4):
        ps = poster[lag]
        med = [p for p in ps if str(p.get("sitenr") or "").strip()]
        i_reg = [p for p in med if str(p["sitenr"]).strip() in alle_sites]
        senere = [p for p in i_reg if forst_sett[str(p["sitenr"]).strip()] != kropper[0].name]
        uten = [p for p in ps if not str(p.get("sitenr") or "").strip()]
        naer = 0
        med_koord = sum(1 for p in uten if p.get("sitelatitudedecimaldegree")
                        and p.get("sitelongitudedecimaldegree"))
        print(f"lag {lag}: uten sitenr, med koordinater: {med_koord}")
        # «decimaldegree» er grader ganger 100: 6588.035 for 65.880967 i
        # registeret (lokalitet 36017). Avviket mot registeret for postene
        # som HAR sitenr, står under.
        for p in uten:
            la, lo = p.get("sitelatitudedecimaldegree"), p.get("sitelongitudedecimaldegree")
            if la and lo and any(s[0] and avstand_km((la / 100, lo / 100), s) < 0.5
                                 for s in alle_sites.values()):
                naer += 1
        avvik = sorted(avstand_km((p["sitelatitudedecimaldegree"] / 100,
                                   p["sitelongitudedecimaldegree"] / 100),
                                  alle_sites[str(p["sitenr"]).strip()])
                       for p in i_reg if p.get("sitelatitudedecimaldegree")
                       and alle_sites[str(p["sitenr"]).strip()][0])
        if avvik:
            print(f"lag {lag}: med sitenr, avstand søknad–register (grader/100): median "
                  f"{avvik[len(avvik) // 2]:.3f} km, under 0,5 km i {sum(a < 0.5 for a in avvik)} "
                  f"av {len(avvik)}")
        print(f"lag {lag}: {len(ps)} poster, sitenr satt i {len(med)}, av dem i registeret "
              f"{len(i_reg)} (første gang sett etter {kropper[0].name}: {len(senere)}); "
              f"uten sitenr {len(uten)} (soeknadstype {dict(Counter(p.get('soeknadstype') for p in uten))}), "
              f"av dem {naer} innen 500 m av en lokalitet i registeret")
        if lag == 4:
            g = [p for p in uten if p.get("evaluation_result") in ("GRANTED", "PARTIALLY_GRANTED")]
            print(f"   lag 4 innvilget uten sitenr: {len(g)}")

    ut = ARKIV_DIR / MAPPE / f"{dato}.s1.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nLogg: {ut.name}")
    for p in logg:
        print(f"  {p['status']!s:>7} {p['byte_utpakket']:>8} "
              f"{(p.get('sha256') or p['sha256_utpakket'])[:16]} {p.get('fil', '—'):<20} "
              f"{p['fetched_at']}  {p['hva']}")


if __name__ == "__main__":
    main()
