#!/usr/bin/env python3
"""Publiseringen fra GitHub Actions — `publiser.py` uten et menneske i steg 4.

    python publiser_ci.py bygg --kvittering K           bygg.yml: steg 1–4
    python publiser_ci.py sjekk MAPPE --kvittering K    publiser.yml: summen
    python publiser_ci.py last-opp MAPPE --miljo M      steg 5
    python publiser_ci.py logg --kvittering K --miljo M steg 6

Workflowene bor i DATAREPOET (`bygg.yml`, `publiser.yml`), som
`samle.yml`, og henter dette skriptet fra kodrepoet.

## Hva som er likt, og hva som ikke er det

Stegene er `publiser.py` sine, kalt som funksjoner — porten, ukas tall,
søkeindeksen, wrangler-kommandoen og bokføringen finnes ett sted. Det
som skiller er tre ting, og hver av dem er valgt:

  * **Ingen «ja» i steg 4.** Spørsmålet er flyttet, ikke fjernet:
    `bygg.yml` legger bare ut til forhåndsvisning, og produksjon skjer
    når Heine selv starter `publiser.yml` og skriver «ja» der.
  * **Bygget måles som et PRODUKSJONSBYGG**, også når det bare går til
    forhåndsvisning. Det er dette bygget, byte for byte, som senere kan
    legges ut på kystloggen.no — da må det ha passert de prøvene
    produksjon krever (kontaktadressen i porten, søkeindeksen i steg 4)
    før det får en kvittering.
  * **Kvitteringen.** sha256 over hele mappa, sammen med commitene og
    uka, skrives til en fil som lagres ved siden av byggemappa.
    `publiser.yml` legger ikke ut noe den ikke kan finne igjen der.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROT))

import publiser                                            # noqa: E402
from publiser import Stopp                                 # noqa: E402

MILJOER = ("forhandsvisning", "produksjon")

# DE TO VERDIENE WRANGLER LESER FRA MILJØET når den ikke er logget inn.
# Begge må være satt; mangler én, svarer Cloudflare med en feil som ikke
# sier hvilken. Sjekket her, før kallet, og navngitt.
CLOUDFLARE = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")


# ------------------------------------------------------------ bygg

def bygg(kvittering: Path) -> dict:
    """Steg 1–4. Skriver kvitteringen og returnerer den."""
    print("\n[1/4] sporbarhet")
    kode = publiser.krev_sporbar(ROT, "koderepoet")
    data = publiser.krev_sporbar(publiser.DATAREPO, "datarepoet")
    print(f"      kode {kode[:12]}  ·  data {data[:12]}")

    print("\n[2/4] bygg")
    publiser.kjor(*publiser.byggkommando(
        av=f"{Path(__file__).name} bygg, steg 3"), vis=True)
    ut = publiser.UT
    if not ut.is_dir():
        raise Stopp(f"\n  STOPPET: {ut} finnes ikke.")

    print("\n[3/4] publiseringsvakten (som for produksjon)")
    print("\n".join(publiser.kjor_porten(ut, produksjon=True)))

    print("\n[4/4] ukas endringer")
    uke, linjer = publiser.ukas_tall()
    sok = publiser.krev_sokeindeks(ut, produksjon=True)
    sha, filer, byte = publiser.mappesum(ut)
    k = {
        "kode_commit": kode,
        "data_commit": data,
        "uke": uke,
        "sha256": sha,
        "filer": filer,
        "byte": byte,
        "bygget": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    print("\n".join(linjer + sok))
    print(f"\n  {filer} filer, {byte / 1e6:.1f} MB")
    print(f"  sha256 {sha}")

    kvittering.parent.mkdir(parents=True, exist_ok=True)
    kvittering.write_text(json.dumps(k, indent=2) + "\n", encoding="utf-8")
    oppsummer(oppsummering(k, linjer + sok))
    return k


def oppsummering(k: dict, linjer: list[str]) -> str:
    """Jobboppsummeringen: ukas tall slik steg 4 skriver dem, og summen.

    Det er her Heine leser tallene før han starter `publiser.yml` — den
    samme teksten som `publiser.py` viser før den spør om «ja».
    """
    return "\n".join([
        f"## Bygg for uke {k['uke'] or '(ingen)'}",
        "",
        "```",
        *linjer,
        "```",
        "",
        "| | |",
        "|---|---|",
        f"| sha256 over byggemappa | `{k['sha256']}` |",
        f"| filer | {k['filer']} |",
        f"| størrelse ukomprimert | {k['byte'] / 1e6:.1f} MB |",
        f"| kode | `{k['kode_commit']}` |",
        f"| data | `{k['data_commit']}` |",
        "",
    ])


def oppsummer(tekst: str) -> None:
    """Legg til i jobboppsummeringen når vi kjører i Actions."""
    sti = os.environ.get("GITHUB_STEP_SUMMARY")
    if sti:
        with open(sti, "a", encoding="utf-8") as f:
            f.write(tekst + "\n")


def les_kvittering(sti: Path) -> dict:
    try:
        k = json.loads(sti.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Stopp(f"\n  STOPPET: kvitteringen {sti} kan ikke leses: {e}")
    mangler = [n for n in ("kode_commit", "data_commit", "uke", "sha256")
               if not k.get(n)]
    if mangler:
        raise Stopp(f"\n  STOPPET: kvitteringen {sti} mangler "
                    f"{', '.join(mangler)}.")
    return k


# ------------------------------------------------------------ sjekk

def sjekk(mappe: Path, k: dict) -> str:
    """Summen over `mappe`, eller `Stopp` når den ikke er kvitteringens.

    Dette er hele grunnen til at produksjon ikke bygger på nytt: porten
    og søkeindeksen ble målt på en mappe i `bygg.yml`, og den mappa er
    det eneste som har passert dem. En annen mappe — avkortet i
    nedlastingen, fra et annet bygg, eller endret etterpå — har ikke det,
    uansett hvor lik den er.
    """
    if not mappe.is_dir():
        raise Stopp(f"\n  STOPPET: {mappe} finnes ikke.")
    sha, filer, byte = publiser.mappesum(mappe)
    if sha != k["sha256"]:
        raise Stopp(
            f"\n  STOPPET: sha256 over byggemappa avviker fra kvitteringen.\n"
            f"    kvitteringen  {k['sha256']}  ({k.get('filer')} filer)\n"
            f"    lastet ned    {sha}  ({filer} filer)\n"
            f"  Dette er ikke mappa bygg.yml målte. Ingenting er lastet opp.")
    print(f"  sha256 {sha} — lik kvitteringen ({filer} filer, "
          f"{byte / 1e6:.1f} MB)")
    return sha


# ------------------------------------------------------------ steg 5

def krev_cloudflare(miljo: dict | None = None) -> None:
    """`Stopp` som navngir hver verdi som mangler. Verdiene vises ikke."""
    miljo = os.environ if miljo is None else miljo
    mangler = [n for n in CLOUDFLARE if not (miljo.get(n) or "").strip()]
    if mangler:
        raise Stopp(
            f"\n  STOPPET: {' og '.join(mangler)} er ikke satt.\n"
            f"  Legg {'dem' if len(mangler) > 1 else 'den'} under Settings → "
            f"Secrets and variables → Actions i datarepoet. Se «Publisering "
            f"fra GitHub» i docs/RUNBOOK.md.\n  Ingenting er lastet opp.")


def last_opp(mappe: Path, miljo: str) -> None:
    krev_cloudflare()
    if not mappe.is_dir():
        raise Stopp(f"\n  STOPPET: {mappe} finnes ikke.")
    produksjon = miljo == "produksjon"
    print(f"\nwrangler → {miljo}")
    publiser.kjor(*publiser.wranglerkommando(mappe, produksjon), vis=True)


# ------------------------------------------------------------ steg 6

def logg(k: dict, miljo: str, forsok: int = 3) -> str:
    """Steg 6, med nye forsøk når origin har flyttet seg.

    Tom streng når linja står på `origin/main`, ellers grunnen.

    `publiser.bokfor()` sier fra og gir opp når pushen avvises, fordi et
    menneske sitter ved tastaturet og kan gjøre resten. Her gjør ingen
    det, og datarepoet skrives av fem andre workflows. En avvist push er
    da som regel bare at en av dem kom først — samme løsning som
    `samle.yml`: rebase og prøv igjen.

    Linja skrives ÉN gang. Nye forsøk gjelder bare pushen; å kalle
    `bokfor()` på nytt ville skrevet linja to ganger.
    """
    problem, _ = publiser.bokfor(k["kode_commit"], k["data_commit"],
                                 miljo, k["uke"])
    if not problem or "ikke pushet" not in problem:
        return problem
    for _ in range(forsok):
        feil = (publiser.prov("git", "pull", "--rebase", "--quiet",
                              "origin", "main", mappe=publiser.DATAREPO)
                or publiser.prov("git", "push", "--quiet", "origin",
                                 "HEAD:main", mappe=publiser.DATAREPO))
        if not feil:
            return ""
        problem = f"logglinja er committet, men ikke pushet:\n    {feil}"
    return problem


# ------------------------------------------------------------ hoved

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="kommando", required=True)

    b = sub.add_parser("bygg", help="steg 1–4, skriv kvitteringen")
    b.add_argument("--kvittering", type=Path, required=True)

    sj = sub.add_parser("sjekk", help="summen mot kvitteringen")
    sj.add_argument("mappe", type=Path)
    sj.add_argument("--kvittering", type=Path, required=True)

    o = sub.add_parser("last-opp", help="steg 5")
    o.add_argument("mappe", type=Path)
    o.add_argument("--miljo", choices=MILJOER, required=True)

    lg = sub.add_parser("logg", help="steg 6")
    lg.add_argument("--kvittering", type=Path, required=True)
    lg.add_argument("--miljo", choices=MILJOER, required=True)

    a = ap.parse_args(argv)
    if a.kommando == "bygg":
        bygg(a.kvittering)
    elif a.kommando == "sjekk":
        sjekk(a.mappe, les_kvittering(a.kvittering))
    elif a.kommando == "last-opp":
        last_opp(a.mappe, a.miljo)
    elif a.kommando == "logg":
        problem = logg(les_kvittering(a.kvittering), a.miljo)
        if problem:
            # Siden er ute. Det er bokføringen som mangler — rød, fordi
            # en upushet linje ellers står ukjent til neste gang noen
            # leser loggen og finner et hull.
            print(f"::error::Siden er lagt ut til {a.miljo}, men "
                  f"publiseringsloggen er ikke pushet: {problem}")
            return 1
        print(f"      {publiser.LOGG.relative_to(publiser.DATAREPO)} — "
              f"committet og pushet")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stopp as e:
        tekst = str(e).strip()
        print(tekst)
        # STOPPET-linja som annotasjon, så grunnen står øverst i
        # kjøringen og ikke bare inne i stegets logg. Porten skriver
        # funnene FØR den, så første linje er ikke alltid grunnen.
        linjer = tekst.splitlines()
        grunn = next((l for l in linjer if "STOPPET" in l), linjer[0])
        print(f"::error::{grunn.strip().replace('STOPPET: ', '')}")
        sys.exit(1)
