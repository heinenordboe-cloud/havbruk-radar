"""Har hver arkivmappe og hver kilde en rad i lisenskjeden — og bærer den?

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \\
        .venv/bin/python verktoy/lisensdekning.py

Leser to tabeller i `docs/LISENSKJEDE.md`:

  MAPPETABELLEN   én rad per mappe i `data/arkiv/` og per kildenavn i
                  `sources/`, med vilkåret ordrett, datoen det ble lest,
                  den arkiverte vilkårssiden og en status.
  PRODUKTTABELLEN hvilke rader hvert produkt hviler på.

og sier hva som mangler. Skriver ingenting.

## Hvorfor et verktøy og ikke bare en prøve

R4 (2026-11-04) fant 23 arkivmapper med innhold og uten rad. Mappene
kommer til av seg selv — en ny fangst er én fil i repoet og én mappe i
datarepoet — mens tabellen bare endrer seg når noen skriver i den. En
prøve i kodrepoet ser ikke datarepoet i Actions; dette verktøyet gjør
det, og `tests/test_lisensdekning.py` kjører det samme når mappa finnes.

## En rad BÆRER når

  * `lest` er en dato (dd.mm.åååå),
  * statusen er en av `STATUSER`,
  * en `belagt`-rad har et sitat («…») i hver av de tre vilkårskolonnene,
    og vilkårskolonnen peker på en arkivert kropp (`mappe/fil`), og
  * en `UBELAGT`-rad sier hvorfor (ikke tom).

Sitatene holdes i tillegg mot kroppen de peker på (`sitater_i_kroppen`):
et sitat som ikke står i den arkiverte teksten, er ikke ordrett.
"""
from __future__ import annotations

import fnmatch
import gzip
import re
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
LISENSKJEDE = ROT / "docs" / "LISENSKJEDE.md"

MAPPETABELL = "## Mappetabellen"
PRODUKTTABELL = "## Produktene"

# `belagt i lov`: åndsverkloven § 14 eller annen lovtekst, ikke et vilkår
# fra utgiveren (merknad K). `egen`: vi har laget innholdet selv.
# `ikke innhold`: vilkårssider, målekropper og spesifikasjoner, som ikke
# selges. `NEKTET`: vilkåret forbyr bruken.
STATUSER = ("belagt", "belagt i lov", "UBELAGT", "NEKTET", "egen", "ikke innhold")
BAERER = ("belagt", "belagt i lov", "egen")

_DATO = re.compile(r"\b\d\d\.\d\d\.\d{4}\b")
_SITAT = re.compile(r"«([^»]+)»")
_KROPP = re.compile(r"`([a-z0-9_.-]+/[0-9][0-9A-Za-z_.-]*\.(?:bin|json)\.gz)`")
_NAVN = re.compile(r"`([^`]+)`")


def _tabell(tekst: str, overskrift: str) -> list[dict[str, str]]:
    """Den første markdown-tabellen etter `overskrift`, som rader."""
    i = tekst.find("\n" + overskrift)
    if i < 0:
        return []
    linjer = tekst[i + 1:].splitlines()[1:]
    rader: list[list[str]] = []
    for linje in linjer:
        if linje.startswith("## "):
            break
        if linje.startswith("|"):
            rader.append([c.strip() for c in linje.strip().strip("|").split("|")])
        elif rader:
            break
    if len(rader) < 2:
        return []
    hode = rader[0]
    return [dict(zip(hode, r)) for r in rader[2:]]


def mapperader(tekst: str) -> list[dict[str, str]]:
    """Mappetabellen. `navn` er mønsteret i første kolonne, uten backticks."""
    ut = []
    for r in _tabell(tekst, MAPPETABELL):
        for navn in _NAVN.findall(r.get("mappe", "")):
            ut.append(dict(r, navn=navn))
    return ut


def rad_for(navn: str, rader: list[dict[str, str]]) -> list[dict[str, str]]:
    """Radene som dekker `navn` (eksakt, `navn:del` eller et glob-mønster)."""
    return [r for r in rader
            if r["navn"] == navn or r["navn"].split(":")[0] == navn
            or ("*" in r["navn"] and fnmatch.fnmatch(navn, r["navn"]))]


def svakheter(r: dict[str, str]) -> list[str]:
    """Hva raden mangler for å bære. Tom liste = raden er komplett."""
    feil = []
    status = r.get("status", "").strip("* ")
    if status not in STATUSER:
        feil.append(f"status «{status}» er ikke en av {STATUSER}")
    if not _DATO.search(r.get("lest", "")):
        feil.append("ingen dato i «lest»")
    if status == "belagt":
        for kol in ("kommersiell bruk", "videresalg", "attribusjon"):
            if not _SITAT.search(r.get(kol, "")):
                feil.append(f"«{kol}» har ikke vilkåret ordrett")
        if not _KROPP.search(r.get("vilkår, arkivert", "")):
            feil.append("ingen arkivert vilkårsside")
    if status == "UBELAGT" and not r.get("vilkår, arkivert", "").strip():
        feil.append("UBELAGT uten grunn")
    return feil


def kildenavn() -> list[str]:
    """Hvert navn en kilde i `sources/` skriver under, med `skriver_ogsaa`."""
    sys.path.insert(0, str(ROT))
    from core import registry
    from core.contract import attribusjon_per_kilde
    return sorted(attribusjon_per_kilde(registry.discover()))


def arkivmapper(data: Path) -> list[str]:
    arkiv = data / "arkiv"
    return sorted(p.name for p in arkiv.iterdir() if p.is_dir()) if arkiv.is_dir() else []


def sitater_i_kroppen(r: dict[str, str], data: Path) -> list[str]:
    """Sitatene i raden som IKKE står i noen av kroppene raden peker på."""
    sys.path.insert(0, str(ROT))
    from core.karantene import synlig_tekst
    tekster = []
    for sti in _KROPP.findall(r.get("vilkår, arkivert", "")):
        fil = data / "arkiv" / sti
        if not fil.exists():
            return [f"kroppen {sti} finnes ikke"]
        b = gzip.open(fil).read()
        tekster += [synlig_tekst(b), b.decode("utf-8", "replace")]
    if not tekster:
        return []
    sitater = [s for kol in ("kommersiell bruk", "videresalg", "attribusjon")
               for s in _SITAT.findall(r.get(kol, ""))]
    return [s for s in sitater if not any(s in t for t in tekster)]


# --------------------------------------------------------------- produkter

def produkter(tekst: str) -> list[dict]:
    """Produkttabellen: {produkt, kilder: [(navn, status skrevet)], status}."""
    ut = []
    for r in _tabell(tekst, PRODUKTTABELL):
        kilder = re.findall(r"`([^`]+)`\s*([A-Za-zÆØÅæøå ]+?)(?=\s*(?:·|$))",
                            r.get("kilder og status", ""))
        ut.append({"produkt": r.get("produkt", ""), "kilder": kilder,
                   "status": r.get("salgbart", "")})
    return ut


def status(navn: str, rader: list[dict[str, str]]) -> str:
    """Den svakeste statusen blant radene som dekker `navn`."""
    st = [r.get("status", "").strip("* ") for r in rad_for(navn, rader)]
    if not st:
        return "MANGLER RAD"
    for svak in ("NEKTET", "UBELAGT", "ikke innhold"):
        if svak in st:
            return svak
    return st[0]


def salgbart(p: dict, rader: list[dict[str, str]]) -> tuple[bool, list[str]]:
    """Salgbart bare når ingen av kildene er UBELAGT (eller verre)."""
    hindre = [n for n, _ in p["kilder"] if status(n, rader) not in BAERER]
    return not hindre, hindre


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(ROT))
    from core.paths import DATA_DIR
    tekst = LISENSKJEDE.read_text(encoding="utf-8")
    rader = mapperader(tekst)
    mapper, kilder = arkivmapper(DATA_DIR), kildenavn()

    print(f"{len(mapper)} mapper i {DATA_DIR / 'arkiv'}, {len(kilder)} kildenavn "
          f"i sources/, {len(rader)} rader i mappetabellen.\n")
    mangler = [("mappe", m) for m in mapper if not rad_for(m, rader)]
    mangler += [("kilde", k) for k in kilder if not rad_for(k, rader)]
    print(f"UTEN RAD: {len(mangler)}")
    for hva, n in mangler:
        print(f"  {hva:6} {n}")

    halve = [(r["navn"], f) for r in rader for f in svakheter(r)]
    print(f"\nRADER SOM IKKE BÆRER: {len(halve)}")
    for n, f in halve:
        print(f"  {n:45} {f}")

    feil_sitat = [(r["navn"], s) for r in rader for s in sitater_i_kroppen(r, DATA_DIR)]
    print(f"\nSITATER SOM IKKE STÅR I KROPPEN: {len(feil_sitat)}")
    for n, s in feil_sitat:
        print(f"  {n:45} «{s[:60]}»")

    ubelagt = sorted({r["navn"] for r in rader if status(r["navn"], rader) == "UBELAGT"})
    print(f"\nUBELAGT: {len(ubelagt)}\n  " + "\n  ".join(ubelagt))

    print("\nPRODUKTENE")
    for p in produkter(tekst):
        ok, hindre = salgbart(p, rader)
        print(f"  {p['produkt']:40} {'salgbart' if ok else 'IKKE salgbart: ' + ', '.join(hindre)}")
    return 1 if mangler or halve or feil_sitat else 0


if __name__ == "__main__":
    sys.exit(main())
