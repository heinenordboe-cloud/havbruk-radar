#!/usr/bin/env python3
"""Publiser Kystloggen til Cloudflare Pages.

    python publiser.py                  # forhåndsvisning
    python publiser.py --produksjon     # kystloggen.no

## Hvorfor dette er et skript og ikke seks kommandoer i RUNBOOK

Fordi rekkefølgen er hele poenget, og fordi ett av stegene er et
spørsmål til et menneske. En liste med seks kommandoer blir til fem
kommandoer den dagen noen har det travelt, og det er alltid den samme
som ryker: porten.

## Stegene, og hva hvert av dem verner mot

    1  sporbarhet   begge repoene rene og pushet. F15, to ganger:
                    en publisering fra kode ingen kan finne igjen er
                    en påstand ingen kan etterprøve.
    2  bygg         fra det som ligger på disk, ikke fra en cache
    3  porten       ETT ukvittert funn stopper. Ingen overstyring.
    4  ukas tall    skrevet ut, og du må skrive «ja»
    5  wrangler     forhåndsvisning med mindre --produksjon
    6  logg         én linje i datarepoet: hva som ble lagt ut, når,
                    fra hvilken kode og hvilke data

## Ingen nøkler her

`wrangler` autentiserer i nettleseren (`npx wrangler login`) og lagrer
sin egen tilstand under `~/.config/.wrangler`. Dette skriptet leser
den ikke, skriver den ikke, og ber ikke om den. Kjører du uten å være
logget inn, sier wrangler fra selv.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROT))

from core.paths import DATA_DIR                            # noqa: E402

DATAREPO = DATA_DIR.parent
UT = DATA_DIR / "nettsted"
LOGG = DATAREPO / "docs" / "publiseringslogg.tsv"

PROSJEKT = "kystloggen"

# GRENENE HOS CLOUDFLARE PAGES, og de er ikke det samme som grenene i
# git — de er etiketter på en utrulling. Pages behandler ÉN av dem som
# produksjon; alt annet blir en forhåndsvisning med sin egen adresse.
#
# ## Hvorfor produksjonsgrenen står her og ikke utelates
#
# Fram til 23.09.2026 sendte `--produksjon` ingen `--branch` i det hele
# tatt, og lot wrangler utlede den av git. Det virker — helt til noen
# publiserer fra en annen gren enn `main`, og da går utrullingen til en
# forhåndsvisning UTEN at noe sier fra. En publisering som stille blir
# noe annet enn det den ba om, er verre enn en som feiler.
#
# Navnet «main» er valgt fordi det er grenen koden utgis fra, og fordi
# `kodeproveniens.krev_sporbar()` allerede krever at HEAD finnes på
# `origin/main`. To steder som sier «main» om samme gren er greit; to
# steder som KAN si ulike ting er det ikke — derfor står den her, som
# én konstant.
PRODUKSJONSGREN = "main"
FORHANDSGREN = "forhandsvisning"

# En forhåndsvisning som lander i produksjon er den ene feilen dette
# skriptet ikke kan oppdage i ettertid.
assert FORHANDSGREN != PRODUKSJONSGREN


class Stopp(SystemExit):
    """Publiseringen stanset. Meldingen sier hvor og hvorfor."""


def kjor(*args: str, mappe: Path = ROT, vis: bool = False) -> str:
    """Kjør en kommando. `Stopp` ved feil, med kommandoens egen melding."""
    try:
        ut = subprocess.run(args, cwd=mappe, text=True,
                            capture_output=not vis)
    except FileNotFoundError:
        # En kommando som ikke finnes skal si HVA som mangler, ikke
        # vise et spor fra subprocess. Dette rammer `npx` på en maskin
        # uten Node, og da er svaret å installere Node — ikke å lese
        # en stakktrace.
        raise Stopp(
            f"\n  STOPPET: kommandoen «{args[0]}» finnes ikke.\n"
            + ("  Installer Node.js (som gir npx), og kjør\n"
               "    npx wrangler login\n"
               "  én gang før første publisering."
               if args[0] == "npx" else ""))
    if ut.returncode != 0:
        melding = (ut.stderr or ut.stdout or "").strip() if not vis else ""
        raise Stopp(f"\n  STOPPET i {mappe.name}: {' '.join(args)}\n"
                    f"  {melding}")
    return (ut.stdout or "").strip() if not vis else ""


def git(*args: str, mappe: Path) -> str:
    return kjor("git", *args, mappe=mappe)


# ------------------------------------------------------------ steg 1

def krev_sporbar(mappe: Path, navn: str) -> str:
    """Rent tre, ingenting upushet. Returnerer commit-sha.

    ## Hvorfor BEGGE repoene

    Nettstedet er en funksjon av to ting: koden som bygger og dataene
    som bygges. En publisering der ett av dem ikke kan gjøres rede for,
    er en side ingen kan bygge på nytt — og da er sjekksummen i
    arkivlinja en påstand uten dekning.

    Dette er den samme regelen som `core/kodeproveniens.py` håndhever
    for innsamlingen, av samme grunn: F15 skjedde to ganger.
    """
    urent = git("status", "--porcelain", mappe=mappe)
    if urent:
        raise Stopp(
            f"\n  STOPPET: {navn} har et urent arbeidstre.\n\n{urent}\n\n"
            f"  Commit eller still tilbake. En publisering fra et tre "
            f"ingen kan gjenskape, er en side ingen kan bygge på nytt.")

    git("fetch", "--quiet", "origin", mappe=mappe)
    upushet = git("log", "origin/main..HEAD", "--oneline", mappe=mappe)
    if upushet:
        raise Stopp(
            f"\n  STOPPET: {navn} har commits som ikke er pushet.\n\n"
            f"{upushet}\n\n  Push først. CLAUDE.md regel 7.")

    return git("rev-parse", "HEAD", mappe=mappe)


# ------------------------------------------------------------ steg 4

def ukas_tall() -> tuple[str, list[str]]:
    """(ukeslug, linjer) — hva som ligger i den ferskeste uka.

    Leses av det som NETTOPP ble bygget, ikke av changeloggen på nytt:
    spørsmålet er «hva er det jeg er i ferd med å legge ut», og det
    svares bare av utputtet.
    """
    import collections

    import nettsted

    felles = nettsted.les_felles()
    uker = nettsted.les_endringsuker(felles)
    if not uker:
        return "", ["Ingen endringsuker."]

    u = uker[0]
    linjer = [
        f"  {u['vist']} ({u['spenn']})",
        f"  {u['antall']} endringer · {u['antall_egen_del']} selskapsdata "
        f"· {u['utenfor_tellingen']} felt som kom eller gikk "
        f"· {u['antall_rader']} rader i alt",
        "",
        "  per type:",
    ]
    for k in u["typer"]:
        if k["antall"]:
            merke = "" if k.get("teller", True) else "   (telles ikke)"
            linjer.append(f"    {k['antall']:>6}  {k['navn']}{merke}")

    linjer += ["", "  per kilde:"]
    for kilde, n in collections.Counter(
            h["kilde"] for h in u["hendelser"]).most_common():
        linjer.append(f"    {n:>6}  {kilde}")
    return u["slug"], linjer


def spor(tekst: str) -> None:
    """Krev «ja». Alt annet stopper.

    Ikke «y», ikke enter, ikke «ja» med stor J som feiler stille. Et
    spørsmål som kan besvares ved et uhell er ikke et spørsmål.
    """
    try:
        svar = input(tekst).strip().lower()
    except EOFError:
        # Ingen å spørre. Da er svaret nei — et spørsmål uten et
        # menneske er ikke besvart, og en publisering som gikk gjennom
        # fordi stdin var lukket ville vært den verste varianten:
        # stille, og uten at noen hadde sett tallene.
        raise Stopp("\n\n  STOPPET: ingen å spørre (stdin er lukket). "
                    "Kjør fra et terminalvindu.")
    if svar != "ja":
        raise Stopp("\n  Avbrutt. Ingenting er lastet opp.")


# ------------------------------------------------------------ steg 6

def skriv_logg(kode: str, data: str, miljo: str, uke: str) -> None:
    """Én linje per publisering, i DATAREPOET.

    Der og ikke i koderepoet: en publisering er en hendelse i
    historikken, og historikken bor der dataene bor. Linja er
    append-only som alt annet der.
    """
    LOGG.parent.mkdir(parents=True, exist_ok=True)
    ny = not LOGG.exists()
    with LOGG.open("a", encoding="utf-8") as f:
        if ny:
            f.write("tidspunkt\tmiljo\tkode_commit\tdata_commit\tuke\n")
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()}\t"
                f"{miljo}\t{kode}\t{data}\t{uke}\n")


# ------------------------------------------------------------ hoved

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--produksjon", action="store_true",
                    help="legg ut på kystloggen.no. Uten denne går "
                         "publiseringen til forhåndsvisningen.")
    ap.add_argument("--uten-bygg", action="store_true",
                    help="hopp over byggingen og bruk mappa som den er. "
                         "Porten kjøres uansett.")
    args = ap.parse_args()

    miljo = "produksjon" if args.produksjon else "forhandsvisning"
    print(f"\nKystloggen → {miljo}")

    # 1. Kan denne publiseringen gjøres rede for?
    print("\n[1/6] sporbarhet")
    git("pull", "--ff-only", "--quiet", mappe=DATAREPO)
    kode = krev_sporbar(ROT, "koderepoet")
    data = krev_sporbar(DATAREPO, "datarepoet")
    print(f"      kode {kode[:12]}  ·  data {data[:12]}  ·  begge rene "
          f"og pushet")

    # 2. Bygg.
    if args.uten_bygg:
        print("\n[2/6] bygg — hoppet over (--uten-bygg)")
    else:
        print("\n[2/6] bygg")
        kjor(sys.executable, "nettsted.py", "--alle", "--uten-vakt", vis=True)

    if not UT.is_dir():
        raise Stopp(f"\n  STOPPET: {UT} finnes ikke.")

    # 3. Porten. Egen kjøring, også når bygget nettopp kjørte den:
    #    `--uten-bygg` skal ikke kunne hoppe over den.
    print("\n[3/6] publiseringsvakten")
    import publiseringsvakt

    funn = publiseringsvakt.gransk(UT)
    igjen = publiseringsvakt.ukvittert(funn)
    kvitterte = [f for f in funn if f.kvittert]
    for f in publiseringsvakt.kodeproveniens_ukjente():
        print(f"      {f}")
    if igjen:
        for f in igjen:
            print(f"      {f}")
        raise Stopp(f"\n  STOPPET: {len(igjen)} ukvitterte funn. "
                    f"Ingenting er lastet opp.")
    print(f"      rent — {len(kvitterte)} kvitterte funn står")

    # 4. Hva er det jeg legger ut?
    print("\n[4/6] ukas endringer")
    uke, linjer = ukas_tall()
    print("\n".join(linjer))
    filer = sum(1 for p in UT.rglob("*") if p.is_file())
    bytes_ = sum(p.stat().st_size for p in UT.rglob("*") if p.is_file())
    print(f"\n  {filer} filer, {bytes_ / 1e6:.1f} MB → {miljo}")
    spor(f'\n  Skriv «ja» for å laste opp til {miljo}: ')

    # 5. Ut.
    # GRENEN OPPGIS ALLTID, også for produksjon. Se `PRODUKSJONSGREN`.
    gren = PRODUKSJONSGREN if args.produksjon else FORHANDSGREN
    print(f"\n[5/6] wrangler → {miljo} (gren {gren})")
    wrangler = ["npx", "wrangler", "pages", "deploy", str(UT),
                "--project-name", PROSJEKT, "--branch", gren]
    kjor(*wrangler, vis=True)

    # 6. Logg.
    print("\n[6/6] logg")
    skriv_logg(kode, data, miljo, uke)
    print(f"      {LOGG.relative_to(DATAREPO)} — commit og push den.")
    print(f"\nFerdig. {miljo}.\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stopp as e:
        print(e)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Avbrutt. Ingenting er lastet opp.")
        sys.exit(1)
