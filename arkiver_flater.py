"""Daglig fangst av lokalitetsflatene i Akvakulturregisteret.

    python arkiver_flater.py                  # hent, og skriv det som er nytt
    python arkiver_flater.py --torrkjor       # si hva som ville skjedd

Kjøres daglig av jobben `flater` i `daglig.yml` i datarepoet.

## Hvorfor

Havbruksfondet deler en lokalitet over en kommunegrense etter kartfestet
arealbeslag (MALING-HAVBRUKSFOND, «Delte lokaliteter»). Kroppene vi har,
har ett punkt per lokalitet og ingen flate. Fiskeridirektoratets kartlag
sier hvordan flaten er NÅ, og bare nå: MÅLT 03.11.2026 ga spørringen med
`historicMoment` for 01.09.2026 byte for byte samme kropp som uten, laget
har verken `timeInfo` eller `editingInfo`, og Wayback hadde ingen kopi
(docs/MALING-NYE-KILDER.md, a). En flate som flyttes, er borte for den som
ikke hentet den før (CLAUDE.md regel 5).

## Hva som hentes

`FiskeridirWFS_akva/MapServer/80` (Flate_ihht_Akvakulturregisteret), alle
felt med geometri, sortert på `loknr`. Ikke `fiskeridirWMS_akva/19`: det
laget har de samme flatene med `areal_m2`, men svarer uten geometri.
1372 flater og 917 kB 03.11.2026, under tjenestens `maxRecordCount` 2000,
så ett kall. Ingen personfelt: lokalitetsnummer, lokalitetsnavn, status,
plassering, fylke, kommune og areal. Innehaver står ikke i laget.

## Hva som skrives

I `data/arkiv/akvakultur-flater/`:

  * kroppen, `<dato>.json.gz` (`<dato>.2.json.gz` osv.), BARE når sha256
    avviker fra siste lagrede kropp. Svaret serialiseres som `core.raw`
    gjør. To hentinger 21 s fra hverandre ga samme sha256 (MÅLT 03.11.2026),
    så ingen kanonisk form trengs.
  * én logg per kjøring, `<dato>.fangst.logg.json` (løpenummer ved flere
    samme dag), med sha256, `ny`/`uendret`, sammenlignet med, antall
    flater og `fetched_at`. `published_at` står tom: tjenesten sender
    ingen `Last-Modified` (CLAUDE.md 1b-7).

Datoen i navnet er dagen vi hentet. Kartlaget sier hva som gjelder nå, så
`observed_at` og hentedagen er samme dag.

## Når kroppen er mistenkt

Den felles kroppssjekken (core/karantene.py): et svar som ikke er JSON,
et `error`-objekt med 200 (ArcGIS svarer slik, se sources/biomasselag.py),
ingen flater, `exceededTransferLimit` satt (tjenesten avkortet uten å
feile, sources/_arcgis.py), eller under halvparten så mange flater som
forrige kropp. Halvparten er ikke målt: det finnes én kropp å måle mot.
Den er samme halvering som vilkårsarkivet bruker, og skal byttes mot et
målt tall når fangsten har gått en stund.

## Kodeproveniens

Som `arkiver_daglig.py`: `kodeproveniens.krev_sporbar()` før noe hentes,
og `kode_commit`/`kode_rent` i loggen. `--torrkjor` er unntatt.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path

import httpx

from core import karantene
from core import kodeproveniens
from core import raw as raw_arkiv
from sources import _http

MAPPE = "akvakultur-flater"
LAG = ("https://gis.fiskeridir.no/server/rest/services/"
       "FiskeridirWFS_akva/MapServer/80")
SPORRING = {"where": "1=1", "outFields": "*", "returnGeometry": "true",
            "orderByFields": "loknr", "f": "json"}
ANDEL_AV_FORRIGE = 0.5


def hent(klient: httpx.Client):
    """Svaret som JSON, eller bytene når det ikke er JSON (en feilside
    med 200 skal i karantene, ikke tapes)."""
    svar = _http.get(klient, f"{LAG}/query", hva="flatelaget", params=SPORRING)
    try:
        return svar.json()
    except ValueError:
        return svar.content


def mistenkt(rå, forrige: bytes | None) -> list[str]:
    if isinstance(rå, (bytes, str)):
        b = rå if isinstance(rå, bytes) else rå.encode("utf-8")
        return [f"svaret er ikke JSON ({len(b)} B)"] + karantene.vurder(b, [karantene.ikke_tom])
    if not isinstance(rå, dict):
        return [f"svaret er {type(rå).__name__}, ikke et objekt"]
    if "error" in rå:
        return [f"tjenesten svarte med en feil: {json.dumps(rå['error'], ensure_ascii=False)[:200]}"]
    flater = rå.get("features")
    if not flater:
        return ["svaret har ingen flater"]
    if rå.get("exceededTransferLimit"):
        return [f"exceededTransferLimit er satt: tjenesten avkortet etter {len(flater)} flater"]
    if forrige is not None:
        n = len(json.loads(forrige).get("features") or [])
        if len(flater) < ANDEL_AV_FORRIGE * n:
            return [f"{len(flater)} flater, under {ANDEL_AV_FORRIGE:.0%} av {n} i forrige kropp"]
    return []


def siste_kropp() -> Path | None:
    filer = raw_arkiv.kropper(MAPPE)
    return filer[-1] if filer else None


def fang(dato: str, rå, hentet: str, torr: bool) -> dict:
    forrige = siste_kropp()
    lagret = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            lagret = f.read()
    grunner = mistenkt(rå, lagret)
    if grunner:
        if torr:
            return {"status": "ville karantene", "grunn": grunner}
        return karantene.sett_inn(MAPPE, dato, rå, grunner, jobb="flater",
                                  fetched_at=hentet, published_at="",
                                  endepunkt=LAG,
                                  sammenlignet_med=forrige.name if forrige else None)

    data, ext = raw_arkiv._serialiser(rå)
    sha = hashlib.sha256(data).hexdigest()
    sammenlignet = None
    if lagret is not None:
        sammenlignet = {"fil": forrige.name, "sha256": hashlib.sha256(lagret).hexdigest()}
    ny = sammenlignet is None or sammenlignet["sha256"] != sha
    post = {"observed_at": dato, "fetched_at": hentet, "published_at": "",
            "endepunkt": LAG, "sha256": sha, "byte": len(data),
            "status": "ny" if ny else "uendret", "sammenlignet_med": sammenlignet,
            "flater": len(rå["features"])}
    if ny and not torr:
        sti = raw_arkiv._ledig_sti(MAPPE, dato, ext)
        skrevet = raw_arkiv.arkiver(MAPPE, dato, rå)
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


def main(argv=None, hent_fn=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for kroppen og loggen. Standard: i dag (UTC). "
                        "Slås opp her og sendes inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Flatene {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    logg: dict = {"kjoring": "fangst", "kilde": MAPPE, "dato": dato}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Flatefangsten startet ikke: {e}")
            return 1
        logg.update(kode_commit=sha, kode_rent=tilstand)
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        if hent_fn is not None:
            rå = hent_fn()
        else:
            with httpx.Client(timeout=120, follow_redirects=True) as k:
                rå = hent(k)
        post = fang(dato, rå, hentet, a.torrkjor)
    except Exception as e:  # noqa: BLE001 — loggen skal skrives uansett
        print(f"::error::Flatefangsten feilet: {type(e).__name__}: {e}")
        post = {"status": "feil", "feil": f"{type(e).__name__}: {e}"}
    logg["flater"] = post

    if post["status"] in ("ny", "uendret"):
        print(f"  {post['status']:<8} {post['flater']:>5} flater {post['byte']:>8} B  "
              f"{post['sha256'][:16]}…  mot "
              f"{(post['sammenlignet_med'] or {}).get('fil', 'ingenting')}")
    elif post["status"] != "feil":
        print(f"  {post['status']}: {'; '.join(post['grunn'])}")
    if not a.torrkjor:
        print(f"  logg        {skriv_logg(dato, logg).name}")
    return 0 if post["status"] in ("ny", "uendret") else 1


if __name__ == "__main__":
    sys.exit(main())
