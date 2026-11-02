"""Daglig fangst av lusetallene mens de kommer inn: uke N til N-4.

    python arkiver_luseinnkomst.py                 # hent, og skriv det som er nytt
    python arkiver_luseinnkomst.py --torrkjor      # si hva som ville skjedd

Kjøres daglig av `luseinnkomst.yml` i datarepoet.

## Hvorfor

Lusetallskilden henter uke N-4 én gang og fryser den. Mellom inneværende
uke og N-4 er BarentsWatchs ukesvar et register som overskriver seg selv:
MÅLT 02.11.2026 hadde uke 45 0,5 % rapportert, uke 44 30,3 %, uke 43
93,2 %, uke 42 97,1 % og uke 41 99,3 % (docs/MALING-LUSEINNKOMST.md F1.2).
Hvordan en uke fyller seg opp, og om et tall endres før N-4, kan bare sees
av den som henter mens det skjer (CLAUDE.md regel 5).

## Hva som skrives

For hver uke N..N-4, i `data/arkiv/lusetall-innkomst/`:

  * kroppen, `<mandag>.json.gz` (`<mandag>.2.json.gz` osv.), BARE når
    sha256 avviker fra siste lagrede kropp for SAMME uke i denne mappa.
    Samme endepunkt og samme serialisering som innsamlingen
    (`Lusetall.hent_uke`, `core.raw`), så hashen kan sammenlignes med
    `data/arkiv/lusetall/`. Ingen kanonisk form: to kall mot samme uke ga
    samme sha256 (F1.6), så det finnes ingen ordningsstøy å sortere bort.
  * én logg per kjøring, `<kjøredato>.fangst.logg.json` (løpenummer ved
    flere samme dag), med en post per uke: når vi hentet, sha256, `ny`
    eller `uendret`, hvilken kropp den ble sammenlignet med, og andelen
    rapporterte.

Ingen snapshot, ingen changelog, health.json røres ikke. `core/` er
uendret. Bare dette skriptet og målingen skriver mappa.

## Tidene i loggen

`fetched_at` handler om OSS. Svaret har ikke noe tidspunkt for når en
lokalitet rapporterte (F1.5), og `Last-Modified` er tidspunktet svaret ble
laget. `published_at` står derfor tom, aldri `fetched_at` (CLAUDE.md
1b-7). Det loggene til sammen kan si om en rapport, er at den kom mellom
to av VÅRE hentinger.

## Siste lagrede kropp

Navnet er uka kroppen gjelder for (`observed_at`, verden), ikke dagen vi
hentet den. «Siste» er høyeste løpenummer for den uka, og det er en
stedfortreder for skrivetid (F14). Den holder her fordi bare dette
skriptet skriver mappa, én kjøring om gangen (concurrency-gruppa i
workflowen), og hver kjøring skriver høyst én kropp per uke. Skrivetiden
selv står i loggene.

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
import time
from pathlib import Path

from core import kodeproveniens
from core import raw as raw_arkiv
from sources import _barentswatch
from sources.lusetall import Lusetall, rapportert_andel

MAPPE = "lusetall-innkomst"

# Uke N til N-4. N-4 er uka innsamlingen fryser; den tas med så serien
# ender i den samme kroppen innsamlingen har.
UKER = range(0, 5)

ENDEPUNKT = "/v1/geodata/fishhealth/locality/{year}/{week}"


def siste_kropp(mandag: str) -> Path | None:
    """Siste lagrede kropp for uka, etter løpenummer (se docstringen)."""
    filer = [p for p in raw_arkiv.kropper(MAPPE)
             if raw_arkiv.orden(p)[0] == mandag and not raw_arkiv.merke(p.name)]
    return filer[-1] if filer else None


def fang_uke(kilde, aar: int, uke: int, klient, torr: bool) -> dict:
    mandag = _barentswatch.mandag(aar, uke)
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rå = kilde.hent_uke(aar, uke, klient)
    if not rå.get("localities"):
        # 2010 og 2011 gir 200 med tom liste (BARENTSWATCH-FUNN punkt 3).
        # En tom uke N er ikke en uke uten lus, og skal ikke lagres som en.
        raise ValueError(f"uke {uke}/{aar}: svaret har ingen lokaliteter")
    data, ext = raw_arkiv._serialiser(rå)
    sha = hashlib.sha256(data).hexdigest()

    forrige = siste_kropp(mandag)
    sammenlignet = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            sammenlignet = {"fil": forrige.name,
                            "sha256": hashlib.sha256(f.read()).hexdigest()}
    ny = sammenlignet is None or sammenlignet["sha256"] != sha

    aktive, rapportert, andel = rapportert_andel(rå)
    post = {
        "aar": aar, "uke": uke, "observed_at": mandag,
        "fetched_at": hentet, "published_at": "",
        "sha256": sha, "byte": len(data),
        "status": "ny" if ny else "uendret", "sammenlignet_med": sammenlignet,
        "lokaliteter": len(rå["localities"]), "aktive": aktive,
        "rapportert": rapportert, "andel": round(andel, 4),
    }
    if ny and not torr:
        sti = raw_arkiv._ledig_sti(MAPPE, mandag, ext)
        skrevet = raw_arkiv.arkiver(MAPPE, mandag, rå)
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


def main(argv=None, kilde=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="Kjøredatoen uke N regnes fra. Standard: i dag (UTC). "
                        "Slås opp her og sendes inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    i_dag = dt.date.fromisoformat(dato)
    print(f"Lusetall, innkomst {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    logg: dict = {"kjoring": "fangst", "kilde": "lusetall", "dato": dato,
                  "endepunkt": ENDEPUNKT, "uker": []}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Lusefangsten startet ikke: {e}")
            return 1
        logg.update(kode_commit=sha, kode_rent=tilstand)
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    kilde = kilde or Lusetall()
    feil = nye = 0
    klient = kilde._klient()
    try:
        for k in UKER:
            aar, uke = _barentswatch.uke_med_etterslep(i_dag, k)
            try:
                post = fang_uke(kilde, aar, uke, klient, a.torrkjor)
            except Exception as e:  # noqa: BLE001 — én uke skal ikke koste de andre
                print(f"::error::Lusefangst uke {uke}/{aar} feilet: "
                      f"{type(e).__name__}: {e}")
                logg["uker"].append({"aar": aar, "uke": uke, "status": "feil",
                                     "feil": f"{type(e).__name__}: {e}"})
                feil += 1
                continue
            logg["uker"].append(post)
            nye += post["status"] == "ny"
            print(f"  N-{k} {uke:>2}/{aar}  {post['status']:<8} "
                  f"{post['rapportert']:>4}/{post['aktive']:<4} {post['andel']:>7.1%}  "
                  f"{post['sha256'][:16]}…  mot "
                  f"{(post['sammenlignet_med'] or {}).get('fil', 'ingenting')}")
            time.sleep(_barentswatch.PAUSE_S)
    finally:
        klient.close()

    if not a.torrkjor:
        print(f"  logg        {skriv_logg(dato, logg).name}")
    print(f"\n{len(UKER)} uke(r), {nye} ny(e) kropp(er), {feil} feil.")
    return 1 if feil else 0


if __name__ == "__main__":
    sys.exit(main())
