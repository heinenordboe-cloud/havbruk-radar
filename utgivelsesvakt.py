"""Ukentlig vakt over sidene der de statiske kildene gir ut en ny utgave.

    python utgivelsesvakt.py                 # hent, og skriv det som er nytt
    python utgivelsesvakt.py --torrkjor      # si hva som ville skjedd

Kjøres ukentlig av jobben `utgivelsesvakt` i `samle.yml` i datarepoet. Når
en kropp er ny, skriver skriptet navnet i `$GITHUB_OUTPUT` (`endret=…`), og
jobben åpner en issue. Ingen tolkning og ingen parser: varselet sier bare
at noe er nytt, og et menneske legger utgaven inn.

## Hvorfor

Steg 2b i run.py hopper over en statisk kilde så lenge nyeste utgave
ligger skrevet. En ny utgave blir derfor ikke oppdaget før noen legger den
inn for hånd. Fila eller sida som lister utgivelsene, overskriver seg selv,
og den forrige tilstanden finnes ikke hos utgiveren (CLAUDE.md regel 5).

## Hvilke sider, og hvorfor bare én

MÅLT 03.11.2026 (docs/MALING-NYE-KILDER.md, e). Bare de sidene med et
avklart vilkår står i `SIDER`:

  * regomr.geojson hos NMDC: CC BY 4.0 (LISENSKJEDE merknad D), arkivert.
  * Ekspertgruppens rapportside (trafikklyssystemet.no) og HIs
    rapportside: ingen vilkår funnet. UBELAGT, og da arkiveres de ikke.
  * Regjeringens side om trafikklyssystemet: 403 med Cloudflares
    utfordring, og Wayback var nede ved målingen. Ikke målt.
  * Lovdata-søket: robots.txt stenger `/sok` for alle og hele nettstedet
    for `User-agent: *`. Bygges ikke.

## Hva som skrives

I `data/arkiv/utgivelse-<navn>/`, for hver side:

  * kroppen slik den kom (bytes, `<dato>.bin.gz`), BARE når sha256
    avviker fra siste lagrede kropp for siden;
  * én logg per kjøring i `data/arkiv/utgivelsesvakt/<dato>.logg.json`,
    med sha256, `ny`/`uendret`, sammenlignet med, `Last-Modified` slik
    verten sendte den, og `fetched_at`.

`published_at` står tom. For regomr.geojson er `Last-Modified` målt til å
ligge to måneder etter utgivelsen (sources/reguleringsomraader.py); den
er når fila sist ble skrevet på verten, ikke når HI ga ut grensene
(CLAUDE.md 1b-7). Den føres i loggen som det den er.

## Når kroppen er mistenkt

Den felles kroppssjekken (core/karantene.py), per side i `SIDER`. For
GeoJSON: kroppen må være JSON med minst én feature, og den må ikke være
HTML. En mistenkt kropp går i karantene, og kjøringen ender rød.

## Kodeproveniens

Som `arkiver_daglig.py`: `kodeproveniens.krev_sporbar()` før noe hentes,
og `kode_commit`/`kode_rent` i loggen. `--torrkjor` er unntatt.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import httpx

from core import karantene
from core import kodeproveniens
from core import raw as raw_arkiv
from sources import _http

LOGG = "utgivelsesvakt"


def geojson(kropp: bytes) -> str | None:
    """JSON med minst én feature, og ikke en HTML-side."""
    if b"<html" in kropp[:2000].lower():
        return "kroppen er en HTML-side, ikke GeoJSON"
    try:
        d = json.loads(kropp)
    except ValueError:
        return "kroppen er ikke JSON"
    if not isinstance(d, dict) or not d.get("features"):
        return "GeoJSON uten features"
    return None


SIDER = {
    "regomr": {
        "url": "https://ftp.nmdc.no/nmdc/IMR/Smittepress/regomr.geojson",
        "regler": [karantene.ikke_tom, geojson],
        "kilde": "reguleringsomraader",
    },
}


def mappe(navn: str) -> str:
    return f"utgivelse-{navn}"


def siste_kropp(navn: str) -> Path | None:
    filer = raw_arkiv.kropper(mappe(navn))
    return filer[-1] if filer else None


def vakt(navn: str, side: dict, kropp: bytes, last_modified: str,
         dato: str, hentet: str, torr: bool) -> dict:
    post = {"side": navn, "url": side["url"], "kilde": side["kilde"],
            "fetched_at": hentet, "published_at": "",
            "last_modified": last_modified, "byte": len(kropp)}
    grunner = karantene.vurder(kropp, side["regler"])
    if grunner:
        if torr:
            return dict(post, status="ville karantene", grunn=grunner)
        return dict(post, **karantene.sett_inn(
            mappe(navn), dato, kropp, grunner, jobb="utgivelsesvakt",
            fetched_at=hentet, url=side["url"], published_at="",
            last_modified=last_modified))

    sha = hashlib.sha256(kropp).hexdigest()
    forrige = siste_kropp(navn)
    sammenlignet = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            sammenlignet = {"fil": forrige.name,
                            "sha256": hashlib.sha256(f.read()).hexdigest()}
    ny = sammenlignet is None or sammenlignet["sha256"] != sha
    post.update(sha256=sha, status="ny" if ny else "uendret",
                sammenlignet_med=sammenlignet)
    if ny and not torr:
        sti = raw_arkiv._ledig_sti(mappe(navn), dato, "bin")
        skrevet = raw_arkiv.arkiver(mappe(navn), dato, kropp)
        assert skrevet == sha and sti.exists(), (sti, skrevet, sha)
        post["fil"] = sti.name
    return post


def hent(klient: httpx.Client, url: str) -> tuple[bytes, str]:
    r = _http.get(klient, url, hva=f"utgivelsesvakt {url}")
    return r.content, r.headers.get("Last-Modified", "")


def main(argv=None, hent_fn=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for kroppene og loggen. Standard: i dag (UTC). "
                        "Slås opp her og sendes inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Utgivelsesvakt {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    logg: dict = {"kjoring": "utgivelsesvakt", "dato": dato, "sider": []}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Utgivelsesvakten startet ikke: {e}")
            return 1
        logg.update(kode_commit=sha, kode_rent=tilstand)
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    feil = 0
    with httpx.Client(timeout=120, follow_redirects=True) as klient:
        for navn, side in SIDER.items():
            hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            try:
                kropp, lm = (hent_fn or (lambda u: hent(klient, u)))(side["url"])
                post = vakt(navn, side, kropp, lm, dato, hentet, a.torrkjor)
            except Exception as e:  # noqa: BLE001 — én side skal ikke koste de andre
                print(f"::error::Utgivelsesvakt: {navn} feilet: {type(e).__name__}: {e}")
                post = {"side": navn, "url": side["url"], "status": "feil",
                        "feil": f"{type(e).__name__}: {e}"}
            logg["sider"].append(post)
            if post["status"] in ("ny", "uendret"):
                print(f"  {post['status']:<8} {navn:<10} {post['byte']:>8} B  "
                      f"{post['sha256'][:16]}…  mot "
                      f"{(post['sammenlignet_med'] or {}).get('fil', 'ingenting')}"
                      f"  Last-Modified {post['last_modified'] or '—'}")
            else:
                feil += 1
                print(f"  {post['status']:<8} {navn:<10} {'; '.join(post.get('grunn') or [post.get('feil', '')])}")

    endret = [s["side"] for s in logg["sider"] if s["status"] == "ny"]
    if not a.torrkjor:
        ut = raw_arkiv.ARKIV_DIR / LOGG
        ut.mkdir(parents=True, exist_ok=True)
        sti, n = ut / f"{dato}.logg.json", 2
        while sti.exists():
            sti, n = ut / f"{dato}.{n}.logg.json", n + 1
        sti.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  logg        {sti.name}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"endret={' '.join(endret)}\n")
    print(f"\n{len(SIDER)} side(r), {len(endret)} ny(e), {feil} feil eller i karantene.")
    return 1 if feil else 0


if __name__ == "__main__":
    sys.exit(main())
