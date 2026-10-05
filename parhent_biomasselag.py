"""Henter BEGGE biomasselag-endepunktene i samme kjøring og sammenligner.
Kjøres for hånd.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data python parhent_biomasselag.py
    python parhent_biomasselag.py --torrkjor     # hent og sammenlign, skriv ingenting

## Hvorfor dette finnes

04.10.2026 kom første snapshot fra reserven, og 29 endringer mot 22.09
lot seg ikke fordele på kilden og byttet: primæren og reserven har
aldri svart på samme tidspunkt hos oss. Det eneste som gjør
endepunktets bidrag målbart er et PAR — begge kropper, hentet i samme
kjøring. Se docs/KILDE-BIOMASSELAG.md, «Parhenting».

## Hvorfor dette ikke er en del av kilden

`run.py` skriver ett snapshot per kilde per kjøring, og kjernen
arkiverer én kropp per kilde per kjøring (`core/runner.py`). Et par
krever to. Å bygge det inn i `core/` ble vurdert og valgt bort
04.10.2026. Dette verktøyet rører derfor verken `raw/biomasselag/`,
`arkiv/biomasselag/`, health.json eller changeloggen. Serien kommer
fortsatt fra `run.py`: primær, med reserve som fallback.

## Hva som skrives

Bare når BEGGE svarer:

    data/arkiv/biomasselag-par/primaer/<dato>.json.gz
    data/arkiv/biomasselag-par/reserve/<dato>.json.gz
    data/arkiv/biomasselag-par/sammenligning/<dato>.json

Kroppene er de samme som `Biomasselag.fetch()` ville arkivert: samme
FELTER, samme where, samme paginering og fullstendighetssjekk
(`biomasselag._hent_lag`). Sammenligningen bærer sha256 av begge, og
den hashen er `raw.arkiver()`s — samme som `raw_hash` på en
snapshotrad. Ingenting overskrives; samme dato to ganger gir løpenummer.

Svarer primæren ikke — HTTP-feil eller 200 OK med et error-objekt, samme
prøve som `biomasselag._er_primaerfeil()` — skrives INGENTING. En
feilkropp er ikke data, og en reservekropp alene er ikke et par: den
arkiverer `run.py` allerede hver uke.

Exitkode: 0 par skrevet (eller tørrkjørt), 2 primæren svarer ikke, 3
ingen av dem svarer, 4 bare reserven svarer ikke, 1 annen feil (f.eks.
en fullstendighetsfeil).
"""

import argparse
import datetime as dt
import json
import sys

import httpx

from core import raw
from core.config import get
from sources import biomasselag as bl

MAPPE = "biomasselag-par"

# Feltene som sammenlignes per lokalitet. `objectid` er ikke med: den er
# tildelt på nytt mellom endepunktene (720 av 1108, målt 02.10.2026) og
# sier ingenting om lokaliteten.
SAMMENLIGNES = ("navn", "status_lokalitet", "har_fisk", "arter", "siste_rapport")


class Nede(RuntimeError):
    """Endepunktet svarte ikke: HTTP-feil eller error-objekt i kroppen."""


def hent(klient: httpx.Client, base: str, utelatte: tuple[str, ...]) -> list[dict]:
    """Alle rader fra ETT endepunkt. Kaster `Nede` på en primærfeil,
    alt annet slippes gjennom som det er."""
    try:
        rader, _ukjente, _svar = bl._hent_lag(klient, base, utelatte)
    except Exception as e:
        if bl._er_primaerfeil(e):
            raise Nede(bl._grunn(e)) from e
        raise
    return rader


def _per_lokalitet(rader: list[dict]) -> dict[str, dict]:
    """loknr -> de sammenlignbare verdiene, med artene samlet som i parse()."""
    ut = {}
    for loknr, grupp in bl._samle(rader).items():
        forste = grupp[0]
        ut[loknr] = {
            "navn": bl._tekst(forste.get("navn")),
            "status_lokalitet": bl._tekst(forste.get("status_lokalitet")),
            "har_fisk": bl._tekst(forste.get("har_fisk")),
            "arter": bl.ARTSSKILLE.join(
                sorted({bl._tekst(r.get("art")) for r in grupp} - {""})),
            "siste_rapport": bl._dato(forste.get("siste_rapport")),
        }
    return ut


def sammenlign(primaer: list[dict], reserve: list[dict]) -> dict:
    """Ren funksjon: to radlister inn, sammenligningen ut."""
    p, r = _per_lokalitet(primaer), _per_lokalitet(reserve)
    felles = sorted(p.keys() & r.keys(), key=lambda k: (len(k), k))

    avvik = {}
    for felt in SAMMENLIGNES:
        ulike = [k for k in felles if p[k][felt] != r[k][felt]]
        avvik[felt] = {"antall": len(ulike), "loknr": ulike}

    rapport = []
    for k in felles:
        a, b = p[k]["siste_rapport"], r[k]["siste_rapport"]
        if a != b:
            retning = ("reserve nyere" if b > a else "reserve eldre") \
                if a and b else "ett tomt"
            rapport.append({"loknr": k, "primaer": a, "reserve": b,
                            "retning": retning})

    return {
        "rader": {"primaer": len(primaer), "reserve": len(reserve)},
        "lokaliteter": {"primaer": len(p), "reserve": len(r),
                        "felles": len(felles),
                        "bare_primaer": sorted(p.keys() - r.keys()),
                        "bare_reserve": sorted(r.keys() - p.keys())},
        "felt_som_avviker": avvik,
        "siste_rapport": {
            "reserve_nyere": sum(x["retning"] == "reserve nyere" for x in rapport),
            "reserve_eldre": sum(x["retning"] == "reserve eldre" for x in rapport),
            "ett_tomt": sum(x["retning"] == "ett tomt" for x in rapport),
            "nyeste": {"primaer": max((v["siste_rapport"] for v in p.values()), default=""),
                       "reserve": max((v["siste_rapport"] for v in r.values()), default="")},
            "forskjeller": rapport,
        },
    }


def _skriv_sammenligning(dato: str, innhold: dict):
    mappe = raw.ARKIV_DIR / MAPPE / "sammenligning"
    mappe.mkdir(parents=True, exist_ok=True)
    sti, n = mappe / f"{dato}.json", 2
    while sti.exists():
        sti, n = mappe / f"{dato}.{n}.json", n + 1
    sti.write_text(json.dumps(innhold, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    return sti


def _naa() -> str:
    """Når VI spurte. Handler om oss, ikke om laget (1b)."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def kjor(dato: str, torrkjor: bool = False) -> int:
    primaer_url = get("kilder.biomasselag.base_url", bl.STANDARD_BASE).rstrip("/")
    reserve_url = get("kilder.biomasselag.reserve_url", bl.RESERVE_BASE).rstrip("/")

    status = {}
    rader = {}
    klient = httpx.Client(timeout=120.0, follow_redirects=True)
    try:
        for side, url, utelatte in (
                ("primaer", primaer_url, bl.KJENTE_UTELATTE),
                ("reserve", reserve_url, bl.KJENTE_UTELATTE_RESERVE)):
            hentet = _naa()
            try:
                rader[side] = hent(klient, url, utelatte)
                status[side] = {"url": url, "hentet": hentet, "svarer": True}
                print(f"  {side}: {len(rader[side])} rader  ({url})")
            except Nede as e:
                status[side] = {"url": url, "hentet": hentet, "svarer": False,
                                "grunn": str(e)}
                print(f"  {side}: SVARER IKKE ({e})  ({url})")
    finally:
        klient.close()

    if not status["primaer"]["svarer"]:
        print("\nPrimæren svarer ikke. Ingenting arkivert — en feilkropp er "
              "ikke data, og reserven alene er ikke et par.")
        return 3 if not status["reserve"]["svarer"] else 2
    if not status["reserve"]["svarer"]:
        print("\nReserven svarer ikke. Ingenting arkivert — primæren alene "
              "er ikke et par.")
        return 4

    resultat = sammenlign(rader["primaer"], rader["reserve"])
    lok, sr = resultat["lokaliteter"], resultat["siste_rapport"]
    print(f"\n  lokaliteter  primær {lok['primaer']}  reserve {lok['reserve']}"
          f"  felles {lok['felles']}  bare primær {len(lok['bare_primaer'])}"
          f"  bare reserve {len(lok['bare_reserve'])}")
    for felt, v in resultat["felt_som_avviker"].items():
        print(f"  {felt:18} {v['antall']} avvik")
    print(f"  siste_rapport      reserve nyere {sr['reserve_nyere']}, "
          f"eldre {sr['reserve_eldre']}, ett tomt {sr['ett_tomt']}; "
          f"nyeste {sr['nyeste']['primaer']} / {sr['nyeste']['reserve']}")

    if torrkjor:
        print("\nTØRRKJØRING — ingenting skrevet.")
        return 0

    for side in ("primaer", "reserve"):
        status[side]["sha256"] = raw.arkiver(f"{MAPPE}/{side}", dato, rader[side])
    sti = _skriv_sammenligning(dato, {"dato": dato, "endepunkter": status,
                                      **resultat})
    print(f"\n  primær  sha256 {status['primaer']['sha256']}")
    print(f"  reserve sha256 {status['reserve']['sha256']}")
    print(f"  sammenligning  {sti}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="Dato i filnavnene. Standard: i dag (UTC). Slås opp "
                        "her og bare her (CLAUDE.md 1b).")
    a = p.parse_args()
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Parhenting biomasselag {dato}"
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))
    try:
        return kjor(dato, a.torrkjor)
    except Exception as e:
        print(f"\nFEIL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
