"""Daglig fangst av lusetallene mens de kommer inn: uke N til N-4.

    python arkiver_luseinnkomst.py                 # hent, og skriv det som er nytt
    python arkiver_luseinnkomst.py --torrkjor      # si hva som ville skjedd
    python arkiver_luseinnkomst.py --v2            # det samme fra v2-endepunktet

Kjøres daglig av `luseinnkomst.yml` i datarepoet, én jobb per endepunkt.

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

## v2 ved siden av v1 (`--v2`, fra 03.11.2026)

`GET /v1/…/locality/{year}/{week}` er merket utgått (MALING-LUSEINNKOMST
F1.8). Etterfølgeren, `POST /v2/…/locality/{year}/{week}` med `{}` som
filter, hentes for de samme ukene, i `data/arkiv/lusetall-innkomst-v2/`,
med egen logg. Ingen tolkning og ingen overgang: målet er en overlapp som
kan vise om serien fortsetter likt den dagen v1 slås av.

MÅLT 03.11.2026 (docs/MALING-NYE-KILDER.md, f): samme lokaliteter og samme
lusetall, men ILA og PD er uenige for 26–28 og 53–56 lokaliteter per uke.
Det er grunnen til at overlappen trengs, og den skal ikke glattes over her.
Tre kall mot uke 41 over ti minutter ga samme sha256, så sha256 av
kroppen avgjør om den er ny, som for v1.

Egen mappe og ikke et merke i v1-mappa: et merke må være bokstaver
(`raw._NAVN`), og en karantene i en undermappe ville ligget utenfor det
tilsynet leser (`*/karantene*/`).

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

from core import karantene
from core import kodeproveniens
from core import raw as raw_arkiv
from sources import _barentswatch
from sources.lusetall import Lusetall, rapportert_andel

MAPPE = "lusetall-innkomst"

# Uke N til N-4. N-4 er uka innsamlingen fryser; den tas med så serien
# ender i den samme kroppen innsamlingen har.
UKER = range(0, 5)

ENDEPUNKT = "/v1/geodata/fishhealth/locality/{year}/{week}"

MAPPE_V2 = "lusetall-innkomst-v2"
ENDEPUNKT_V2 = "POST /v2/geodata/fishhealth/locality/{year}/{week}"


def siste_kropp(mandag: str, mappe: str = MAPPE) -> Path | None:
    """Siste lagrede kropp for uka, etter løpenummer (se docstringen)."""
    filer = [p for p in raw_arkiv.kropper(mappe)
             if raw_arkiv.orden(p)[0] == mandag and not raw_arkiv.merke(p.name)]
    return filer[-1] if filer else None


def mistenkt(rå: dict, forrige: bytes | None, aar: int, uke: int) -> list[str]:
    """Grunnene til at kroppen ikke skal inn i serien. Tom liste: ingen.

    Tom liste med lokaliteter: 2010 og 2011 gir 200 med tom liste
    (BARENTSWATCH-FUNN punkt 3), og en tom uke N er ikke en uke uten lus.
    Til 03.11.2026 kastet den og tok kroppen med seg; nå går den i
    karantene som resten.

    FÆRRE LOKALITETER enn forrige kropp for samme uke (MALING-DRIFT F4.2,
    fra 03.11.2026). En uke fyller seg opp med rapporter, men lista over
    lokaliteter krymper ikke: målt 03.11.2026 i 12 uker med 2–3 hentinger
    hver, og antallet gikk aldri ned (MALING-DRIFT 0d,
    analyse/drift/luseinnkomst_ned.txt). For uke N til N-4 er grunnlaget
    én kveld, 02.11.2026; for de sju eldre ukene opptil 75 døgn. En kropp
    med færre er en halv kropp, ikke en uke der lokaliteter forsvant.
    """
    lokaliteter = rå.get("localities") if isinstance(rå, dict) else None
    if not lokaliteter:
        return [f"uke {uke}/{aar}: svaret har ingen lokaliteter"]
    if forrige is not None:
        n = len(json.loads(forrige).get("localities") or [])
        if len(lokaliteter) < n:
            return [f"uke {uke}/{aar}: {len(lokaliteter)} lokaliteter, færre enn "
                    f"{n} i forrige kropp for uka"]
    return []


def fang_uke(kilde, aar: int, uke: int, klient, torr: bool) -> dict:
    mandag = _barentswatch.mandag(aar, uke)
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rå = kilde.hent_uke(aar, uke, klient)

    forrige = siste_kropp(mandag)
    lagret = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            lagret = f.read()
    grunner = mistenkt(rå, lagret, aar, uke)
    if grunner:
        if torr:
            return {"aar": aar, "uke": uke, "observed_at": mandag,
                    "status": "ville karantene", "grunn": grunner}
        return dict(karantene.sett_inn(
            MAPPE, mandag, rå, grunner, jobb="luseinnkomst", fetched_at=hentet,
            published_at="", sammenlignet_med=forrige.name if forrige else None),
            aar=aar, uke=uke)

    data, ext = raw_arkiv._serialiser(rå)
    sha = hashlib.sha256(data).hexdigest()
    sammenlignet = None
    if lagret is not None:
        sammenlignet = {"fil": forrige.name,
                        "sha256": hashlib.sha256(lagret).hexdigest()}
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


def hent_uke_v2(kilde, aar: int, uke: int, klient):
    """Rå kropp for én uke fra v2. JSON når svaret er JSON; ellers bytene,
    så en feilside med 200 kan legges i karantene i stedet for å tapes."""
    url = f"{kilde._tilgang.base_url()}/v2/geodata/fishhealth/locality/{aar}/{uke}"
    svar = kilde._tilgang.post(klient, url, hva=f"v2 uke {uke}/{aar}", json={})
    try:
        return svar.json()
    except ValueError:
        return svar.content


def mistenkt_v2(rå, forrige: bytes | None, aar: int, uke: int) -> list[str]:
    """Som `mistenkt()`, for v2-formen: svaret er en liste av lokaliteter.

    Ikke JSON (en feilside med 200), ikke en liste, en tom liste, eller
    færre lokaliteter enn forrige kropp for samme uke. Den siste regelen
    hviler på samme måling som v1 (MALING-DRIFT 0d); 03.11.2026 hadde v1
    og v2 like mange lokaliteter i hver av de seks ukene som ble hentet.
    """
    if isinstance(rå, (bytes, str)):
        b = rå if isinstance(rå, bytes) else rå.encode("utf-8")
        return [f"uke {uke}/{aar}: svaret er ikke JSON ({len(b)} B)"] + \
            karantene.vurder(b, [karantene.ikke_tom])
    if not isinstance(rå, list):
        return [f"uke {uke}/{aar}: svaret er {type(rå).__name__}, ikke en liste"]
    if not rå:
        return [f"uke {uke}/{aar}: svaret har ingen lokaliteter"]
    if forrige is not None:
        n = len(json.loads(forrige))
        if len(rå) < n:
            return [f"uke {uke}/{aar}: {len(rå)} lokaliteter, færre enn "
                    f"{n} i forrige kropp for uka"]
    return []


def fang_uke_v2(kilde, aar: int, uke: int, klient, torr: bool) -> dict:
    mandag = _barentswatch.mandag(aar, uke)
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rå = hent_uke_v2(kilde, aar, uke, klient)

    forrige = siste_kropp(mandag, MAPPE_V2)
    lagret = None
    if forrige is not None:
        with gzip.open(forrige, "rb") as f:
            lagret = f.read()
    grunner = mistenkt_v2(rå, lagret, aar, uke)
    if grunner:
        if torr:
            return {"aar": aar, "uke": uke, "observed_at": mandag,
                    "status": "ville karantene", "grunn": grunner}
        return dict(karantene.sett_inn(
            MAPPE_V2, mandag, rå, grunner, jobb="luseinnkomst-v2",
            fetched_at=hentet, published_at="",
            sammenlignet_med=forrige.name if forrige else None),
            aar=aar, uke=uke)

    data, ext = raw_arkiv._serialiser(rå)
    sha = hashlib.sha256(data).hexdigest()
    sammenlignet = None
    if lagret is not None:
        sammenlignet = {"fil": forrige.name,
                        "sha256": hashlib.sha256(lagret).hexdigest()}
    ny = sammenlignet is None or sammenlignet["sha256"] != sha
    rapportert = sum(1 for l in rå if (l.get("liceReport") or {}).get("hasReported"))
    post = {
        "aar": aar, "uke": uke, "observed_at": mandag,
        "fetched_at": hentet, "published_at": "",
        "sha256": sha, "byte": len(data),
        "status": "ny" if ny else "uendret", "sammenlignet_med": sammenlignet,
        "lokaliteter": len(rå), "rapportert": rapportert,
    }
    if ny and not torr:
        sti = raw_arkiv._ledig_sti(MAPPE_V2, mandag, ext)
        skrevet = raw_arkiv.arkiver(MAPPE_V2, mandag, rå)
        assert skrevet == sha and sti.exists(), (sti, skrevet, sha)
        post["fil"] = sti.name
    return post


def skriv_logg(dato: str, logg: dict, mappe_navn: str = MAPPE) -> Path:
    mappe = raw_arkiv.ARKIV_DIR / mappe_navn
    mappe.mkdir(parents=True, exist_ok=True)
    sti, n = mappe / f"{dato}.fangst.logg.json", 2
    while sti.exists():
        sti, n = mappe / f"{dato}.fangst.{n}.logg.json", n + 1
    sti.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    return sti


def main(argv=None, kilde=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--v2", action="store_true",
                   help="Hent fra v2-endepunktet (POST) til lusetall-innkomst-v2/.")
    p.add_argument("--dato", default="",
                   help="Kjøredatoen uke N regnes fra. Standard: i dag (UTC). "
                        "Slås opp her og sendes inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    i_dag = dt.date.fromisoformat(dato)
    mappe = MAPPE_V2 if a.v2 else MAPPE
    fang = fang_uke_v2 if a.v2 else fang_uke
    print(f"Lusetall, innkomst {dato}" + (" (v2)" if a.v2 else "")
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    logg: dict = {"kjoring": "fangst", "kilde": "lusetall", "dato": dato,
                  "endepunkt": ENDEPUNKT_V2 if a.v2 else ENDEPUNKT, "uker": []}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Lusefangsten startet ikke: {e}")
            return 1
        logg.update(kode_commit=sha, kode_rent=tilstand)
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    kilde = kilde or Lusetall()
    feil = nye = karantenert = 0
    klient = kilde._klient()
    try:
        for k in UKER:
            aar, uke = _barentswatch.uke_med_etterslep(i_dag, k)
            try:
                post = fang(kilde, aar, uke, klient, a.torrkjor)
            except Exception as e:  # noqa: BLE001 — én uke skal ikke koste de andre
                print(f"::error::Lusefangst uke {uke}/{aar} feilet: "
                      f"{type(e).__name__}: {e}")
                logg["uker"].append({"aar": aar, "uke": uke, "status": "feil",
                                     "feil": f"{type(e).__name__}: {e}"})
                feil += 1
                continue
            logg["uker"].append(post)
            if post["status"] in (karantene.STATUS, "ville karantene"):
                karantenert += 1
                print(f"  N-{k} {uke:>2}/{aar}  {post['status']:<8} "
                      f"{'; '.join(post['grunn'])}")
                continue
            nye += post["status"] == "ny"
            andel = (f"{post['rapportert']:>4}/{post['aktive']:<4} {post['andel']:>7.1%}"
                     if "aktive" in post else
                     f"{post['rapportert']:>4}/{post['lokaliteter']:<4} rapportert")
            print(f"  N-{k} {uke:>2}/{aar}  {post['status']:<8} {andel}  "
                  f"{post['sha256'][:16]}…  mot "
                  f"{(post['sammenlignet_med'] or {}).get('fil', 'ingenting')}")
            time.sleep(_barentswatch.PAUSE_S)
    finally:
        klient.close()

    if not a.torrkjor:
        print(f"  logg        {skriv_logg(dato, logg, mappe).name}")
    print(f"\n{len(UKER)} uke(r), {nye} ny(e) kropp(er), {feil} feil, "
          f"{karantenert} i karantene.")
    return 1 if feil or karantenert else 0


if __name__ == "__main__":
    sys.exit(main())
