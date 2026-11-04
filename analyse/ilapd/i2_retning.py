"""MALING-NYE-KILDER, etterskrift 04.11.2026 (økt 4c, punkt 1b–1f): ILA/PD,
retningen, kontrollprøven, de andre feltene og når v1 begynte å avvike.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/ilapd/i2_retning.py 2026-11-04 \
        > analyse/ilapd/i2_retning.txt

Reglene under er skrevet FØR noe ble hentet fra Mattilsynet i denne
økta og før noen uke ble klassifisert.

FASITEN. Mattilsynets `GET /api/sykdomstilfeller/v1/rapporteringer` uten
lokalitetsnummer, sidevis med `limit`/`offset` til en side kommer kortere
enn `limit`. Hver side arkiveres i `maling-ilapd/`. Et tilfelle er
AKTIVT i en ISO-uke (mandag–søndag, Europe/Oslo) når

    det ikke er ugyldiggjort (et ugyldiggjort tilfelle er etter
        Mattilsynets egen definisjon «ikke gyldig», og telles aldri;
        uenighet det forklarer, telles for seg),
    diagnosedato eller kvalitetssikretMistankedato er senest søndag, og
    avslutningsdato er tom eller tidligst mandag.

Det er samme regel som `i1_mattilsynet.py`, bortsett fra ugyldiggjøringen,
som i1 bare så i én uke. Mistanke teller som aktivt.

1b RETNINGEN. Siste uke i snapshotene (`raw/lusetall/`), som er uka
nettstedet viser: ALLE lokaliteter, ikke et utvalg. «Har v1, Mattilsynet
ikke» og «Mattilsynet har, v1 ikke», per sykdom. Mattilsynet-tilfeller på
lokaliteter som ikke står i v1-snapshotet, telles for seg. Det samme
regnes for v1-kroppen fra uke 44 (`maling-nye-kilder/2026-11-03.10`).

1c KONTROLLPRØVEN. Uke 44, kroppene `maling-nye-kilder/2026-11-03.10`
(v1) og `.11` (v2). Lokaliteter der v1 og v2 er enige om BEGGE
sykdommene. 20 trukket med `random.Random(20261104).sample` fra den
sorterte lista. Hver mot Mattilsynet. I tillegg: hele populasjonen.

1d DE ANDRE FELTENE. Hver v2-kropp i `lusetall-innkomst-v2/` pares med
v1-kroppen i `lusetall-innkomst/` for samme uke som er hentet nærmest i
tid (fra fangstloggene). Per felt: felles lokaliteter, like, ulike.
Parene er dem `sources/lusetall.py` leser, og v2-feltet som svarer:

    avgAdultFemaleLice      liceReport.adultFemaleLice.average
    hasReportedLice         liceReport.hasReported
    isFallow                liceReport.isFallow
    hasSalmonoids           hasSalmonoidLicense
    isSlaughterHoldingCage  isSlaughterHoldingCage
    isOnLand                locality.isOnLand
    hasCleanerfishDeployed  "RENSEFISK" i liceTreatments
    hasMechanicalRemoval    "IKKE_MEDIKAMENTELL" i liceTreatments
    hasSubstanceTreatments  "MEDIKAMENTELL" i liceTreatments
    hasIla / hasPd          sykdommen i diseases

Lusetall sammenlignes med toleranse 0,005 (v2 bærer float32-støy som
0.70000005). Temperatur finnes ikke i v1 (`LocalityDto` har ikke feltet)
og kan ikke sammenlignes.

1f NÅR. Hver fil i `raw/lusetall/` (alle versjoner), mot tilfellene som
var aktive den uka. Per uke: v1-flagg, Mattilsynet-aktive, «bare v1»,
«bare Mattilsynet», per sykdom. DEKNING: uker før det tidligste
startdatoet (mistanke eller diagnose) i Mattilsynets svar for sykdommen
er utenfor dekning og telles ikke.

DEFINISJONEN AV «BEGYNTE Å AVVIKE», valgt før tallene er sett: første
uke W der andelen uenige, (bare v1 + bare Mattilsynet) / (v1 ∪
Mattilsynet), er over 20 % for ILA og PD samlet, og forblir over 20 % i
hver uke etter W. Finnes ingen slik uke, er svaret «ikke funnet».

STOPP. Er Mattilsynets svar kortere enn 100 tilfeller av ILA og PD til
sammen, er pagineringen eller fasiten ikke det den ser ut til, og
målingen stopper før noe klassifiseres.
"""

import datetime as dt
import gzip
import hashlib
import json
import random
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR, RAW_DIR  # noqa: E402
from sources import _http  # noqa: E402

MAPPE = "maling-ilapd"
API = "https://akvakultur-offentlig-api.fisk.mattilsynet.io/api/sykdomstilfeller/v1/rapporteringer"
KLIENT = {"Client-Id": "havbruk-radar", "Accept": "application/json"}
LIMIT = 1000
OSLO = ZoneInfo("Europe/Oslo")
V1_44 = "maling-nye-kilder/2026-11-03.10.json.gz"
V2_44 = "maling-nye-kilder/2026-11-03.11.json.gz"
MANDAG_44 = dt.date(2026, 10, 26)
# sykdom: (v1-felt, snapshotfelt, v2-navn, Mattilsynets sykdomstype)
SYKDOM = {"ILA": ("hasIla", "har_ila", "INFEKSIOES_LAKSEANEMI", "INFEKSIØS_LAKSEANEMI"),
          "PD": ("hasPd", "har_pd", "PANKREASSYKDOM", "PANKREASSYKDOM")}
GRENSE = 0.20
FROE = 20261104
STOPP_MINST = 100


def les(sti: Path):
    b = gzip.decompress(sti.read_bytes())
    return json.loads(b), hashlib.sha256(b).hexdigest()


def dag(instant):
    if not instant:
        return None
    return dt.datetime.fromisoformat(instant.replace("Z", "+00:00")).astimezone(OSLO).date()


def hent_alle(dato: str) -> list[dict]:
    """Alle sykdomstilfeller, side for side, hver side arkivert."""
    alle, logg, offset = [], [], 0
    with httpx.Client(timeout=120) as k:
        while True:
            hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            r = _http.get(k, API, hva=f"sykdomstilfeller offset {offset}",
                          params={"limit": LIMIT, "offset": offset}, headers=KLIENT)
            side = r.json()
            sti = raw._ledig_sti(MAPPE, dato, "json")
            sha, ny = raw.arkiver_ny(MAPPE, dato, side)
            if not ny:
                sti = next(f for f in sorted((ARKIV_DIR / MAPPE).glob("*.gz"))
                           if hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest() == sha)
            logg.append({"hva": f"sykdomstilfeller offset {offset}", "url": str(r.request.url),
                         "status": r.status_code, "fetched_at": hentet,
                         "byte_utpakket": len(r.content), "tilfeller": len(side),
                         "sha256": sha, "fil": sti.name})
            print(f"side offset {offset}: {len(side)} tilfeller, {sti.name} ({sha[:16]})")
            alle.extend(side)
            if len(side) < LIMIT:
                break
            offset += LIMIT
    ut = ARKIV_DIR / MAPPE / f"{dato}.i2.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Logg: {ut.name}\n")
    return alle


class Fasit:
    def __init__(self, tilfeller: list[dict]):
        self.per = {s: [] for s in SYKDOM}
        self.ugyldige = {s: [] for s in SYKDOM}
        for t in tilfeller:
            for s, (_, _, _, mt) in SYKDOM.items():
                if t.get("sykdomstype") not in (mt, mt.replace("Ø", "OE")):
                    continue
                diag, mist = dag(t.get("diagnosedato")), dag(t.get("kvalitetssikretMistankedato"))
                start = min(d for d in (diag, mist) if d) if (diag or mist) else None
                rad = (int(t["lokalitetsnummer"]), start, dag(t.get("avslutningsdato")), t)
                if start is None:
                    continue
                (self.ugyldige if t.get("ugyldiggjøringsdato") else self.per)[s].append(rad)
        self.forst = {s: min((r[1] for r in self.per[s]), default=None) for s in SYKDOM}

    @staticmethod
    def _aktiv(rader, mandag):
        sondag = mandag + dt.timedelta(days=6)
        return {nr: t for nr, start, slutt, t in rader
                if start <= sondag and (slutt is None or slutt >= mandag)}

    def aktive(self, s, mandag):
        return self._aktiv(self.per[s], mandag)

    def ugyldig_aktive(self, s, mandag):
        return self._aktiv(self.ugyldige[s], mandag)


def lenke(t: dict) -> str:
    return f"{API}/{t['id']}"


def del_b(f: Fasit) -> None:
    filer = sorted((RAW_DIR / "lusetall").glob("*.parquet"))
    siste = filer[-1]
    mandag = dt.date.fromisoformat(siste.name[:10])
    sha = hashlib.sha256(siste.read_bytes()).hexdigest()
    d = pl.read_parquet(siste)
    alle = set(int(x) for x in d["entity_id"].unique())
    print(f"=== 1b: siste snapshot {siste.name} (uke {mandag.isocalendar()[1]}), sha256 {sha}")
    print(f"{len(alle)} lokaliteter i snapshotet\n")
    for s, (_, felt, _, _) in SYKDOM.items():
        v1 = set(int(x) for x in d.filter((pl.col("field") == felt)
                                          & (pl.col("value") == "True"))["entity_id"])
        mt = f.aktive(s, mandag)
        mt_inn = set(mt) & alle
        bare_v1, bare_mt = sorted(v1 - set(mt)), sorted(mt_inn - v1)
        ugyldig = f.ugyldig_aktive(s, mandag)
        print(f"{s}: v1 {len(v1)}, Mattilsynet aktive {len(mt)} (i snapshotet {len(mt_inn)}), "
              f"begge {len(v1 & mt_inn)}")
        print(f"  har v1, Mattilsynet ikke: {len(bare_v1)} "
              f"(av dem forklart av et ugyldiggjort tilfelle: {len(set(bare_v1) & set(ugyldig))})")
        print(f"  Mattilsynet har, v1 ikke: {len(bare_mt)}")
        print(f"  Mattilsynet-aktive utenfor snapshotet: {sorted(set(mt) - alle)}")
        print(f"  bare v1: {bare_v1}")
        print(f"  bare Mattilsynet: {bare_mt}")
        # Siste tilfelle av sykdommen for hver «bare v1», for lenkene.
        for nr in bare_v1[:3]:
            tidl = sorted((r for r in f.per[s] if r[0] == nr), key=lambda r: r[1])
            if tidl:
                _, st, sl, t = tidl[-1]
                print(f"    {nr}: siste tilfelle start {st}, avsluttet {sl}, {lenke(t)}")
            else:
                print(f"    {nr}: intet gyldig tilfelle av sykdommen hos Mattilsynet")
        for nr in bare_mt[:3]:
            _, st, sl, t = sorted((r for r in f.per[s] if r[0] == nr), key=lambda r: r[1])[-1]
            print(f"    {nr}: aktivt tilfelle start {st}, avsluttet {sl}, {lenke(t)}")
        print()

    v1_44, s1 = les(ARKIV_DIR / V1_44)
    print(f"--- uke 44, v1-kroppen {V1_44} ({s1[:16]})")
    a1 = {l["localityNo"]: l for l in v1_44["localities"]}
    for s, (f1, _, _, _) in SYKDOM.items():
        v1 = {k for k, l in a1.items() if l[f1]}
        mt = set(f.aktive(s, MANDAG_44))
        print(f"{s}: v1 {len(v1)}, Mattilsynet {len(mt)}, begge {len(v1 & mt)}, "
              f"har v1, Mattilsynet ikke {len(v1 - mt)}, Mattilsynet har, v1 ikke "
              f"{len((mt & set(a1)) - v1)}, Mattilsynet utenfor v1 {len(mt - set(a1))}")
    print()


def v2_har(l: dict, navn: str) -> bool:
    return navn in (l.get("diseases") or [])


def del_c(f: Fasit) -> None:
    v1, s1 = les(ARKIV_DIR / V1_44)
    v2, s2 = les(ARKIV_DIR / V2_44)
    a1 = {l["localityNo"]: l for l in v1["localities"]}
    a2 = {l["locality"]["no"]: l for l in v2}
    felles = sorted(a1.keys() & a2.keys())
    enige = [k for k in felles
             if all(bool(a1[k][f1]) == v2_har(a2[k], n2) for f1, _, n2, _ in SYKDOM.values())]
    print(f"=== 1c: uke 44, v1 {s1[:16]}, v2 {s2[:16]}; {len(felles)} felles, "
          f"{len(enige)} enige om begge sykdommene")
    mt = {s: set(f.aktive(s, MANDAG_44)) for s in SYKDOM}
    utvalg = random.Random(FROE).sample(enige, 20)
    stemmer = 0
    print("lokalitet  ILA v1/v2  ILA MT  PD v1/v2  PD MT  stemmer")
    for k in sorted(utvalg):
        ok = all(bool(a1[k][f1]) == (k in mt[s]) for s, (f1, _, _, _) in SYKDOM.items())
        stemmer += ok
        print(f"{k:>9}  {str(bool(a1[k]['hasIla'])):<9}  {str(k in mt['ILA']):<6}  "
              f"{str(bool(a1[k]['hasPd'])):<8}  {str(k in mt['PD']):<5}  {'ja' if ok else 'NEI'}")
    print(f"Utvalget: begge stemmer med Mattilsynet for {stemmer} av 20")
    for s, (f1, _, _, _) in SYKDOM.items():
        flagget = [k for k in enige if a1[k][f1]]
        uten = [k for k in enige if not a1[k][f1]]
        print(f"Hele populasjonen, {s}: enige om flagg {len(flagget)}, av dem MT aktiv "
              f"{sum(k in mt[s] for k in flagget)}; enige om intet flagg {len(uten)}, av dem MT aktiv "
              f"{sum(k in mt[s] for k in uten)}")
    print()


def fangstlogg(mappe: str) -> dict[str, str]:
    """{filnavn: fetched_at} fra alle loggene i mappa."""
    ut = {}
    for logg in sorted((ARKIV_DIR / mappe).glob("*.logg.json")):
        d = json.loads(logg.read_text(encoding="utf-8"))
        for u in d.get("uker", []):
            fil = u.get("fil")
            if fil and u.get("status") == "ny":
                ut[fil] = u["fetched_at"]
    return ut


def tall(x):
    return None if x is None else round(float(x), 2)


PAR = {
    "avgAdultFemaleLice": lambda l: tall(((l.get("liceReport") or {}).get("adultFemaleLice") or {}).get("average")),
    "hasReportedLice": lambda l: (l.get("liceReport") or {}).get("hasReported"),
    "isFallow": lambda l: (l.get("liceReport") or {}).get("isFallow"),
    "hasSalmonoids": lambda l: l.get("hasSalmonoidLicense"),
    "isSlaughterHoldingCage": lambda l: l.get("isSlaughterHoldingCage"),
    "isOnLand": lambda l: (l.get("locality") or {}).get("isOnLand"),
    "hasCleanerfishDeployed": lambda l: "RENSEFISK" in (l.get("liceTreatments") or []),
    "hasMechanicalRemoval": lambda l: "IKKE_MEDIKAMENTELL" in (l.get("liceTreatments") or []),
    "hasSubstanceTreatments": lambda l: "MEDIKAMENTELL" in (l.get("liceTreatments") or []),
    "hasIla": lambda l: v2_har(l, "INFEKSIOES_LAKSEANEMI"),
    "hasPd": lambda l: v2_har(l, "PANKREASSYKDOM"),
}


def del_d() -> None:
    t1, t2 = fangstlogg("lusetall-innkomst"), fangstlogg("lusetall-innkomst-v2")
    print("=== 1d: v1 mot v2 per felt, hver v2-kropp mot nærmeste v1-henting av samme uke")
    totalt = {f: [0, 0] for f in PAR}
    for fil2 in sorted(t2):
        uke = fil2[:10]
        kand = [(abs(dt.datetime.fromisoformat(t1[f1]) - dt.datetime.fromisoformat(t2[fil2])), f1)
                for f1 in t1 if f1.startswith(uke)]
        if not kand:
            print(f"{fil2}: ingen v1-henting av uka")
            continue
        avstand, fil1 = min(kand)
        v1, s1 = les(ARKIV_DIR / "lusetall-innkomst" / fil1)
        v2, s2 = les(ARKIV_DIR / "lusetall-innkomst-v2" / fil2)
        a1 = {l["localityNo"]: l for l in v1["localities"]}
        a2 = {l["locality"]["no"]: l for l in v2}
        felles = a1.keys() & a2.keys()
        print(f"uke {uke}: v1 {fil1} ({s1[:16]}) mot v2 {fil2} ({s2[:16]}), "
              f"{avstand.total_seconds():.0f} s mellom, {len(felles)} felles "
              f"(bare v1 {len(a1.keys() - a2.keys())}, bare v2 {len(a2.keys() - a1.keys())})")
        linje = []
        for felt, hent in PAR.items():
            v = a1
            ulike = sum(1 for k in felles
                        if (tall(v[k][felt]) if felt == "avgAdultFemaleLice" else v[k][felt]) != hent(a2[k]))
            totalt[felt][0] += len(felles) - ulike
            totalt[felt][1] += ulike
            linje.append(f"{felt} {ulike}")
        print("  ulike: " + ", ".join(linje))
    print("Totalt over parene (like / ulike):")
    for felt, (like, ulike) in totalt.items():
        print(f"  {felt:<24} {like:>6} {ulike:>6}")
    print()


def del_f(f: Fasit) -> None:
    print("=== 1f: hver snapshotfil i raw/lusetall mot Mattilsynets aktive tilfeller den uka")
    print(f"Tidligste start hos Mattilsynet: ILA {f.forst['ILA']}, PD {f.forst['PD']}")
    print("fil                  sha256           ILA v1 MT bareV1 bareMT ugyl | "
          "PD v1 MT bareV1 bareMT ugyl | andel")
    uker = []
    for fil in sorted((RAW_DIR / "lusetall").glob("*.parquet")):
        mandag = dt.date.fromisoformat(fil.name[:10])
        d = pl.read_parquet(fil, columns=["entity_id", "field", "value"])
        alle = set(int(x) for x in d["entity_id"].unique())
        rad, uenige, union, dekket = [], 0, 0, True
        for s, (_, felt, _, _) in SYKDOM.items():
            if f.forst[s] is None or mandag < f.forst[s]:
                dekket = False
            v1 = set(int(x) for x in d.filter((pl.col("field") == felt)
                                              & (pl.col("value") == "True"))["entity_id"])
            mt = set(f.aktive(s, mandag)) & alle
            ug = set(f.ugyldig_aktive(s, mandag))
            bv, bm = v1 - mt, mt - v1
            uenige += len(bv) + len(bm)
            union += len(v1 | mt)
            rad.append(f"{len(v1):>3} {len(mt):>3} {len(bv):>6} {len(bm):>6} {len(bv & ug):>4}")
        andel = uenige / union if union else 0.0
        sha = hashlib.sha256(fil.read_bytes()).hexdigest()[:16]
        print(f"{fil.name:<20} {sha}  {rad[0]} | {rad[1]} | "
              f"{andel:.2f}{'' if dekket else ' (utenfor dekning)'}")
        if dekket:
            uker.append((fil.name, andel))
    start = None
    for i, (navn, a) in enumerate(uker):
        if all(x > GRENSE for _, x in uker[i:]):
            start = navn
            break
    print(f"\nFørste uke der andelen uenige er over {GRENSE:.0%} og forblir det: "
          f"{start or 'ikke funnet'} ({len(uker)} uker innenfor dekning)")


def main() -> None:
    dato = sys.argv[1]
    tilfeller = hent_alle(dato)
    f = Fasit(tilfeller)
    n = {s: len(f.per[s]) for s in SYKDOM}
    print(f"Tilfeller i alt {len(tilfeller)}; gyldige ILA {n['ILA']}, PD {n['PD']}; "
          f"ugyldiggjorte ILA {len(f.ugyldige['ILA'])}, PD {len(f.ugyldige['PD'])}\n")
    if n["ILA"] + n["PD"] < STOPP_MINST:
        print(f"STOPP: under {STOPP_MINST} tilfeller av ILA og PD")
        return
    del_b(f)
    del_c(f)
    del_d()
    del_f(f)


if __name__ == "__main__":
    main()
