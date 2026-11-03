"""Daglig fangst av akvakultursøknadene i Fiskeridirektoratets søknadsportal.

    python arkiver_soknader.py                # hent, filtrer, skriv det som er nytt
    python arkiver_soknader.py --torrkjor     # si hva som ville skjedd

Kjøres daglig av jobben `soknader` i `daglig.yml` i datarepoet.

## Hvorfor

`Yggdrasil/Akvakultursøknader/MapServer` er det eneste samlede registeret
over søknadene (docs/MALING-NYE-KILDER.md, d). Det sier hvordan søknaden
står NÅ, og bare nå. MÅLT 03.11.2026 (etterskriften til samme dokument):
`historicMoment` for 01.09.2026 ga samme sha256 som uten, lagene har
verken `timeInfo`, `editingInfo` eller relasjoner, og en ferdigbehandlet
søknad har bare sluttstatusen og tre datoer (`submittedat`, `withdrawnat`,
`evaluationfinishedat`). En søknad som går fra `RETURNED` til `SUBMITTED`,
eller får omsøkt MTB endret, etterlater ingen spor (CLAUDE.md regel 5).

## Hva som hentes

Lag 0 (under behandling), 2 (flate), 4 (ferdigbehandlet), 5 (flate
ferdigbehandlet) og 6 (gammel flate), alle felt, sortert på `objectid`,
sidevis forbi `maxRecordCount`. Punktlagene 0 og 4 uten geometri: de har
koordinatene som felt (grader ganger 100, se målingen). Flatelagene med.
Forankringspunktene (lag 1 og 7, 8732 punkter 03.11.2026) hentes IKKE:
de er installasjonens fortøyning, ikke søknaden, og ville mer enn doblet
kroppen. Det er et valg, ikke en måling.

## Persondata (CLAUDE.md regel 3)

Søkeren står som `applicantorganisationname` og
`applicantorganisationnumber`, uten organisasjonsform. Et ENK har ni
siffer som et AS. Hvert nummer slås derfor opp hos Brreg før noe lagres,
og en post slipper gjennom bare når

  * nummeret er ni siffer,
  * Brreg oppgir en organisasjonsform (også for en slettet enhet), og
  * verken formen eller sektoren er en personform
    (`core/persondata.er_personform`, `er_personsektor`).

Vet ikke = filtreres ut: 404, 410 og tomt nummer. Svarer ikke Brreg i
det hele tatt, stopper fangsten før noe skrives, også karantene: et
filter som ikke kjørte, er ikke et filter. Loggen fører antall per grunn,
aldri et nummer.

Målt 03.11.2026: 222 ulike søkernummer, ingen personform, ett ukjent
hos Brreg (404). Én søknad filtreres.

## Hva som skrives

I `data/arkiv/akvakultur-soknader/`:

  * kroppen, `<dato>.json.gz`, `{"<lag>": [poster]}` etter filteret,
    BARE når sha256 avviker fra siste lagrede. To hentinger ett minutt
    fra hverandre ga samme sha256 for lag 0 og 4 (MÅLT 03.11.2026).
  * én logg per kjøring, `<dato>.fangst.logg.json` (løpenummer ved flere
    samme dag), med sha256, `ny`/`uendret`, antall per lag og hva
    filteret tok. `published_at` står tom: tjenesten sender ingen
    `Last-Modified` (CLAUDE.md 1b-7).

## Når kroppen er mistenkt

Den felles kroppssjekken (core/karantene.py): et lag som ikke er JSON,
et `error`-objekt med 200, lag 0 eller 4 uten poster, eller et lag med
under halvparten så mange poster som i forrige kropp. Halvparten er ikke
målt; det finnes én kropp. Det som går i karantene, er også filtrert.

## Kodeproveniens

Som `arkiver_flater.py`: `kodeproveniens.krev_sporbar()` før noe hentes,
og `kode_commit`/`kode_rent` i loggen. `--torrkjor` er unntatt.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx

from core import karantene
from core import kodeproveniens
from core import persondata
from core import raw as raw_arkiv
from sources import _http

MAPPE = "akvakultur-soknader"
TJENESTE = ("https://gis.fiskeridir.no/server/rest/services/"
            "Yggdrasil/Akvakultursøknader/MapServer")
BRREG = "https://data.brreg.no/enhetsregisteret/api/enheter"
# lag -> med geometri
LAG = {0: False, 2: True, 4: False, 5: True, 6: True}
MAA_HA_POSTER = (0, 4)
ANDEL_AV_FORRIGE = 0.5
NR_FELT = "applicantorganisationnumber"
NI = re.compile(r"^\d{9}$")


class FilteretKjorteIkke(Exception):
    """Brreg svarte ikke. Da skrives ingenting."""


def hent_lag(klient: httpx.Client, lag: int):
    """Alle poster i laget, sidevis. JSON-svaret med alle features samlet,
    eller bytene fra første side som ikke var JSON."""
    q = {"where": "1=1", "outFields": "*", "returnGeometry": str(LAG[lag]).lower(),
         "orderByFields": "objectid", "f": "json"}
    samlet, side = None, 0
    while True:
        svar = _http.get(klient, f"{TJENESTE}/{lag}/query", hva=f"søknadslag {lag}",
                         params=dict(q, resultOffset=side))
        try:
            d = svar.json()
        except ValueError:
            return svar.content
        if not isinstance(d, dict) or "error" in d:
            return d
        if samlet is None:
            samlet = d
        else:
            samlet["features"] += d.get("features") or []
        if not d.get("exceededTransferLimit"):
            samlet.pop("exceededTransferLimit", None)
            return samlet
        side += len(d.get("features") or [])
        if not d.get("features"):
            return samlet


def hent(klient: httpx.Client) -> dict:
    return {str(lag): hent_lag(klient, lag) for lag in LAG}


def brreg_former(klient: httpx.Client, numre: set[str]) -> dict[str, dict]:
    """orgnr -> {"form", "sektor", "status"}. Aldri navn eller adresse."""
    ut: dict[str, dict] = {}
    liste = sorted(n for n in numre if NI.match(n))
    hode = {"Accept": "application/json"}
    try:
        for i in range(0, len(liste), 100):
            r = _http.get(klient, BRREG, hva="brreg, organisasjonsform",
                          params={"organisasjonsnummer": ",".join(liste[i:i + 100]),
                                  "size": 100}, headers=hode)
            for e in (r.json().get("_embedded") or {}).get("enheter", []):
                ut[e["organisasjonsnummer"]] = {
                    "status": "ok",
                    "form": (e.get("organisasjonsform") or {}).get("kode", ""),
                    "sektor": (e.get("institusjonellSektorkode") or {}).get("kode", "")}
        # Lista svarer bare for enheter som finnes. En slettet enhet svarer
        # 200 med organisasjonsformen på enkeltoppslaget (sources/eierskap.py,
        # brreg_form); 404 og 410 er «vet ikke».
        for n in liste:
            if n in ut:
                continue
            r = klient.get(f"{BRREG}/{n}", headers=dict(hode, **{"User-Agent": _http.brukeragent()}))
            if r.status_code in (404, 410):
                ut[n] = {"status": f"http {r.status_code}", "form": "", "sektor": ""}
                continue
            r.raise_for_status()
            d = r.json()
            ut[n] = {"status": "slettet" if d.get("slettedato") else "ok",
                     "form": (d.get("organisasjonsform") or {}).get("kode", ""),
                     "sektor": (d.get("institusjonellSektorkode") or {}).get("kode", "")}
    except Exception as e:  # noqa: BLE001
        raise FilteretKjorteIkke(f"{type(e).__name__}: {e}") from e
    return ut


def grunn(post: dict, former: dict[str, dict]) -> str:
    """«slipper» eller grunnen til at posten tas ut."""
    nr = str(post.get(NR_FELT) or "").strip()
    if not NI.match(nr):
        return "ikke ni siffer"
    f = former.get(nr)
    if f is None or not f["form"]:
        return "vet ikke"
    if persondata.er_personform(f["form"]) or persondata.er_personsektor(f["sektor"]):
        return "personform"
    return "slipper"


def numre(rå: dict) -> set[str]:
    return {str((f.get("attributes") or {}).get(NR_FELT) or "").strip()
            for d in rå.values() if isinstance(d, dict)
            for f in d.get("features") or []}


def filtrer(rå: dict, former: dict[str, dict]) -> tuple[dict, dict]:
    """Kroppen uten personene, og antall per grunn per lag."""
    ut, tall = {}, {}
    for lag, d in rå.items():
        if not isinstance(d, dict) or "features" not in d:
            ut[lag] = d
            continue
        c = Counter()
        beholdt = []
        for f in d["features"]:
            g = grunn(f.get("attributes") or {}, former)
            c[g] += 1
            if g == "slipper":
                beholdt.append(f)
        ut[lag] = dict(d, features=beholdt)
        tall[lag] = dict(c)
    return ut, tall


def mistenkt(kropp: dict, forrige: bytes | None) -> list[str]:
    grunner = []
    gammel = json.loads(forrige) if forrige is not None else {}
    for lag, d in kropp.items():
        if isinstance(d, (bytes, str)):
            b = d if isinstance(d, bytes) else d.encode("utf-8")
            grunner += [f"lag {lag}: svaret er ikke JSON ({len(b)} B)"]
            continue
        if not isinstance(d, dict):
            grunner.append(f"lag {lag}: svaret er {type(d).__name__}, ikke et objekt")
            continue
        if "error" in d:
            grunner.append(f"lag {lag}: tjenesten svarte med en feil: "
                           f"{json.dumps(d['error'], ensure_ascii=False)[:200]}")
            continue
        n = len(d.get("features") or [])
        if n == 0 and int(lag) in MAA_HA_POSTER:
            grunner.append(f"lag {lag}: ingen poster")
        g = len((gammel.get(lag) or {}).get("features") or [])
        if g and n < ANDEL_AV_FORRIGE * g:
            grunner.append(f"lag {lag}: {n} poster, under {ANDEL_AV_FORRIGE:.0%} av {g} "
                           f"i forrige kropp")
    return grunner


def siste_kropp() -> Path | None:
    filer = raw_arkiv.kropper(MAPPE)
    return filer[-1] if filer else None


def _lagret(kropp) -> dict:
    """Det som faktisk skrives: bytes fra et lag som ikke var JSON, blir
    tekst, så hele kroppen kan serialiseres som JSON (karantene)."""
    return {lag: (d.decode("utf-8", "replace") if isinstance(d, bytes) else d)
            for lag, d in kropp.items()}


def fang(dato: str, kropp: dict, filtrert: dict, hentet: str, torr: bool) -> dict:
    forrige = siste_kropp()
    lagret = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            lagret = f.read()
    grunner = mistenkt(kropp, lagret)
    if grunner:
        if torr:
            return {"status": "ville karantene", "grunn": grunner}
        return karantene.sett_inn(MAPPE, dato, _lagret(kropp), grunner, jobb="soknader",
                                  fetched_at=hentet, published_at="",
                                  endepunkt=TJENESTE, filtrert=filtrert,
                                  sammenlignet_med=forrige.name if forrige else None)

    data, ext = raw_arkiv._serialiser(kropp)
    sha = hashlib.sha256(data).hexdigest()
    sammenlignet = None
    if lagret is not None:
        sammenlignet = {"fil": forrige.name, "sha256": hashlib.sha256(lagret).hexdigest()}
    ny = sammenlignet is None or sammenlignet["sha256"] != sha
    post = {"observed_at": dato, "fetched_at": hentet, "published_at": "",
            "endepunkt": TJENESTE, "sha256": sha, "byte": len(data),
            "status": "ny" if ny else "uendret", "sammenlignet_med": sammenlignet,
            "poster": {lag: len(d["features"]) for lag, d in kropp.items()},
            "filtrert": filtrert}
    if ny and not torr:
        sti = raw_arkiv._ledig_sti(MAPPE, dato, ext)
        skrevet = raw_arkiv.arkiver(MAPPE, dato, kropp)
        assert skrevet == sha and sti.exists(), (sti, skrevet, sha)
        post["fil"] = sti.name
    return post


def skriv_logg(dato: str, logg: dict) -> Path:
    mappe = raw_arkiv.ARKIV_DIR / MAPPE
    mappe.mkdir(parents=True, exist_ok=True)
    sti, n = mappe / f"{dato}.fangst.logg.json", 2
    while sti.exists():
        sti, n = mappe / f"{dato}.fangst.{n}.logg.json", n + 1
    sti.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    return sti


def main(argv=None, hent_fn=None, former_fn=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for kroppen og loggen. Standard: i dag (UTC). "
                        "Slås opp her og sendes inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Søknadene {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    logg: dict = {"kjoring": "fangst", "kilde": MAPPE, "dato": dato}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Søknadsfangsten startet ikke: {e}")
            return 1
        logg.update(kode_commit=sha, kode_rent=tilstand)
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        with httpx.Client(timeout=120, follow_redirects=True) as k:
            rå = hent_fn() if hent_fn is not None else hent(k)
            former = (former_fn or (lambda nr: brreg_former(k, nr)))(numre(rå))
        kropp, filtrert = filtrer(rå, former)
        del rå  # ufiltrert skal ingen vei herfra
        post = fang(dato, kropp, filtrert, hentet, a.torrkjor)
    except FilteretKjorteIkke as e:
        print(f"::error::Søknadsfangsten: persondatafilteret kjørte ikke ({e}). "
              f"Ingenting er skrevet.")
        post = {"status": "feil", "feil": f"persondatafilteret kjørte ikke: {e}"}
    except Exception as e:  # noqa: BLE001 — loggen skal skrives uansett
        print(f"::error::Søknadsfangsten feilet: {type(e).__name__}: {e}")
        post = {"status": "feil", "feil": f"{type(e).__name__}: {e}"}
    logg["soknader"] = post

    if post["status"] in ("ny", "uendret"):
        tatt = sum(n for t in post["filtrert"].values()
                   for g, n in t.items() if g != "slipper")
        print(f"  {post['status']:<8} {post['poster']}  {post['byte']:>8} B  "
              f"{post['sha256'][:16]}…  mot "
              f"{(post['sammenlignet_med'] or {}).get('fil', 'ingenting')}; "
              f"{tatt} post(er) tatt ut av filteret")
    elif post["status"] != "feil":
        print(f"  {post['status']}: {'; '.join(post['grunn'])}")
    if not a.torrkjor:
        print(f"  logg        {skriv_logg(dato, logg).name}")
    return 0 if post["status"] in ("ny", "uendret") else 1


if __name__ == "__main__":
    sys.exit(main())
