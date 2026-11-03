"""MALING-NYE-KILDER, etterskrift 03.11.2026 (økt 4b, punkt 3): ILA/PD,
v1 mot v2 mot Mattilsynet.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/ilapd/i1_mattilsynet.py 2026-11-03 \
        > analyse/ilapd/i1_mattilsynet.txt

Reglene under er skrevet FØR noe ble hentet fra Mattilsynet og før noen
lokalitet ble klassifisert.

UTVALGET. Uke 44/2026, kroppene `maling-nye-kilder/2026-11-03.10.json.gz`
(v1) og `.11.json.gz` (v2), hentet med ett sekunds mellomrom. Fire grupper:
ILA bare i v1, ILA bare i v2, PD bare i v1, PD bare i v2. Hver gruppe
sorteres på lokalitetsnummer, og de fem første i hver tas: 4 × 5 = 20.
Ingen andre valg.

FASITEN. Mattilsynets åpne API, `GET /api/sykdomstilfeller/v1/
rapporteringer?lokalitetsnummer=N` (NLOD 2.0, spesifikasjonen arkivert i
`mattilsynet-openapi/`). Svaret arkiveres i `maling-ilapd/`. Et tilfelle
av sykdommen er AKTIVT i uka når

    ugyldiggjøringsdato er tom (eller etter uka),
    diagnosedato eller kvalitetssikretMistankedato er senest søndag, og
    avslutningsdato er tom eller tidligst mandag.

Datoene er Mattilsynets `Instant` lest i Europe/Oslo («2026-05-11T22:00Z»
er 12.05). «påvist» når diagnosedato er senest søndag, ellers «mistanke».

ENIG. En versjon er enig med Mattilsynet for en lokalitet når flagget
(v1 `hasIla`/`hasPd`, v2 `diseases` inneholder sykdommen) er sant nøyaktig
når et aktivt tilfelle finnes. Mistanke teller som aktivt. Utskriften
viser i tillegg hva svaret blir om bare «påvist» teller; det brukes ikke
i STOPP-regelen.

STOPP. Nettstedet og snapshotene bruker v1 (`har_ila`, `har_pd`). Er v1
uenig med Mattilsynet i 5 eller flere av de 20, er det vi publiserer feil
i et omfang som ikke er støy: målingen stopper, ingenting rettes, og
punktet rapporteres som STOPP.
"""

import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _http  # noqa: E402

MAPPE = "maling-ilapd"
API = "https://akvakultur-offentlig-api.fisk.mattilsynet.io/api/sykdomstilfeller/v1/rapporteringer"
KLIENT = {"Client-Id": "havbruk-radar", "Accept": "application/json"}
V1 = "maling-nye-kilder/2026-11-03.10.json.gz"
V2 = "maling-nye-kilder/2026-11-03.11.json.gz"
MANDAG, SONDAG = dt.date(2026, 10, 26), dt.date(2026, 11, 1)
OSLO = ZoneInfo("Europe/Oslo")
SYKDOM = {"ILA": ("hasIla", "INFEKSIOES_LAKSEANEMI", "INFEKSIØS_LAKSEANEMI"),
          "PD": ("hasPd", "PANKREASSYKDOM", "PANKREASSYKDOM")}
PER_GRUPPE = 5
STOPP_GRENSE = 5


def les(sti: str):
    b = gzip.decompress((ARKIV_DIR / sti).read_bytes())
    return json.loads(b), hashlib.sha256(b).hexdigest()


def dag(instant: str | None) -> dt.date | None:
    if not instant:
        return None
    return dt.datetime.fromisoformat(instant.replace("Z", "+00:00")).astimezone(OSLO).date()


def tilstand(tilfeller: list[dict], mt_type: str) -> tuple[str, list[str]]:
    """«påvist», «mistanke» eller «ingen» i uke 44, og tilfellene som
    avgjorde det (alle av typen, med datoene)."""
    beste, linjer = "ingen", []
    for t in tilfeller:
        # Spesifikasjonen staver typen med Ø; svarformen er ikke sett for ILA.
        if t.get("sykdomstype") not in (mt_type, mt_type.replace("Ø", "OE")):
            continue
        ugyldig, diag = dag(t.get("ugyldiggjøringsdato")), dag(t.get("diagnosedato"))
        mist, slutt = dag(t.get("kvalitetssikretMistankedato")), dag(t.get("avslutningsdato"))
        start = min(d for d in (diag, mist) if d) if (diag or mist) else None
        aktiv = ((ugyldig is None or ugyldig > SONDAG) and start is not None
                 and start <= SONDAG and (slutt is None or slutt >= MANDAG))
        if aktiv:
            ny = "påvist" if diag and diag <= SONDAG else "mistanke"
            if beste != "påvist":
                beste = ny
        linjer.append(f"{t['id'][:8]} mistanke {mist} diagnose {diag} avsluttet {slutt}"
                      f"{' ugyldig ' + str(ugyldig) if ugyldig else ''}"
                      f"{' — AKTIV uke 44' if aktiv else ''}")
    return beste, linjer


def main() -> None:
    dato = sys.argv[1]
    v1, s1 = les(V1)
    v2, s2 = les(V2)
    a1 = {l["localityNo"]: l for l in v1["localities"]}
    a2 = {l["locality"]["no"]: l for l in v2}
    felles = sorted(a1.keys() & a2.keys())
    print(f"v1 {V1} sha256 {s1}\nv2 {V2} sha256 {s2}\n{len(felles)} felles lokaliteter\n")

    grupper = {}
    for navn, (felt1, felt2, _) in SYKDOM.items():
        f1 = {k for k in felles if a1[k][felt1]}
        f2 = {k for k in felles if felt2 in a2[k]["diseases"]}
        grupper[(navn, "bare v1")] = sorted(f1 - f2)
        grupper[(navn, "bare v2")] = sorted(f2 - f1)
        print(f"{navn}: v1 {len(f1)}, v2 {len(f2)}, begge {len(f1 & f2)}, bare v1 {len(f1 - f2)}, "
              f"bare v2 {len(f2 - f1)}")
    utvalg = [(s, g, k) for (s, g), ks in grupper.items() for k in ks[:PER_GRUPPE]]
    print(f"\nUtvalg: {len(utvalg)} (de {PER_GRUPPE} laveste lokalitetsnumrene i hver gruppe)\n")

    logg = []
    svar = {}
    with httpx.Client(timeout=60) as k:
        for nr in sorted({n for _, _, n in utvalg}):
            hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            r = _http.get(k, API, hva=f"sykdomstilfeller {nr}",
                          params={"lokalitetsnummer": nr}, headers=KLIENT)
            sti = raw._ledig_sti(MAPPE, dato, "json")
            sha, ny = raw.arkiver_ny(MAPPE, dato, r.json())
            if not ny:
                sti = next(f for f in sorted((ARKIV_DIR / MAPPE).glob("*.gz"))
                           if hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest() == sha)
            logg.append({"hva": f"sykdomstilfeller {nr}", "url": str(r.request.url),
                         "status": r.status_code, "fetched_at": hentet,
                         "byte_utpakket": len(r.content),
                         "sha256_utpakket": hashlib.sha256(r.content).hexdigest(),
                         "sha256": sha, "fil": sti.name})
            svar[nr] = (r.json(), sha, sti.name)

    enig = {"v1": 0, "v2": 0}
    enig_pavist = {"v1": 0, "v2": 0}
    print("sykdom gruppe   lokalitet  navn                       v1    v2    Mattilsynet  enig  fil (sha256)")
    for s, g, nr in utvalg:
        felt1, felt2, mt = SYKDOM[s]
        tilf, sha, fil = svar[nr]
        t, linjer = tilstand(tilf, mt)
        f1, f2 = bool(a1[nr][felt1]), felt2 in a2[nr]["diseases"]
        aktiv, pavist = t != "ingen", t == "påvist"
        hvem = [v for v, f in (("v1", f1), ("v2", f2)) if f == aktiv]
        for v in hvem:
            enig[v] += 1
        for v, f in (("v1", f1), ("v2", f2)):
            if f == pavist:
                enig_pavist[v] += 1
        print(f"{s:<6} {g:<8} {nr:>9}  {a2[nr]['locality']['name'][:26]:<26} {str(f1):<5} {str(f2):<5} "
              f"{t:<12} {','.join(hvem) or 'ingen':<5} {fil} ({sha[:16]})")
        for linje in linjer:
            print(f"{'':>27}{linje}")
    n = len(utvalg)
    print(f"\nEnig med Mattilsynet (mistanke teller): v1 {enig['v1']} av {n}, v2 {enig['v2']} av {n}")
    print(f"Enig med Mattilsynet (bare påvist teller): v1 {enig_pavist['v1']} av {n}, "
          f"v2 {enig_pavist['v2']} av {n}")
    uenig_v1 = n - enig["v1"]
    print(f"STOPP-regelen: v1 uenig i {uenig_v1} av {n}; grensen er {STOPP_GRENSE}. "
          f"{'STOPP' if uenig_v1 >= STOPP_GRENSE else 'ikke utløst'}")

    ut = ARKIV_DIR / MAPPE / f"{dato}.i1.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nLogg: {ut.name}")


if __name__ == "__main__":
    main()
