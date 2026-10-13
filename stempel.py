"""Tidsstempler nye filer i arkivet med OpenTimestamps.

    python stempel.py                 # manifest for nye filer, stemple, oppgradere
    python stempel.py --torrkjor      # si hva som ville blitt stemplet

Kjøres av `stempel.yml` i datarepoet etter hver fangstjobb.

## Hvorfor

Git beviser ikke når noe ble skrevet: `GIT_COMMITTER_DATE` settes av den
som committer, og en historikk kan skrives om og tvinges ut. Det er
`forsegl.py`s argument for prediksjonene, og det gjelder arkivet like
mye — påstanden «denne kroppen fantes 13.10.2026» er hele verdien av en
henting som ikke kan gjøres om igjen (CLAUDE.md regel 5). Et stempel i
Bitcoin-kjeden er et anker utenfor repoet, på en dato ingen av oss kan
flytte.

## Hva som skrives

`data/stempler/<dato>.manifest.txt` (med løpenummer når datoen finnes):

  * sha256 for hver fil i `data/arkiv/` og `data/raw/` der (sti, sha256)
    ikke står i et tidligere manifest,
  * det samme for filene i kodrepoets `predictions/` — de endres med
    vilje når et utfall skrives inn, og hver versjon får sin linje,
  * HEAD i begge repoene.

En fil i arkivet som har fått nytt innhold etter at den sto i et
manifest, får en ny linje. Regel 2 sier at det ikke skal skje; skjer det,
står det her.

Stiene er gitt fra mappa repoene ligger i (`havbruk-radar-data/data/...`,
`havbruk-radar/predictions/...`), ikke fra der en runner sjekket dem ut.
Fra den mappa sjekker `shasum` hver linje uten dette verktøyet:

    grep -v '^#' havbruk-radar-data/data/stempler/<fil>.manifest.txt \\
        | shasum -a 256 -c

Ingen nye filer gir intet manifest. HEAD alene er ikke nytt innhold.

## Stempling og oppgradering

`ots stamp` lager `<manifest>.ots`, som venter på kalendrene. Samme kjøring
oppgraderer hvert ventende stempel: en KOPI oppgraderes, og blir den
fullstendig, skrives den som `<manifest>.komplett.ots`. Originalen endres
aldri. `ots upgrade` flytter ellers fila den får til `.bak` og skriver
over navnet — prøvd 13.10.2026 på en kopi av
predictions/havbruksfond-2026.md.ots: exit 0 og «Timestamp complete» når
kalendrene har en blokk (971138 og 971140), exit 1 når de fortsatt venter.

Et manifest uten `.ots` (kalendrene svarte ikke sist) stemples ved neste
kjøring.

Verifisering står i docs/RUNBOOK.md, «Tidsstempler».
"""

import argparse
import datetime as dt
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from core import paths

KODEREPO = paths.ROT
DATA = paths.DATA_DIR
DATAREPO = DATA.parent
STEMPEL_DIR = DATA / "stempler"
DATAMAPPER = ("arkiv", "raw")
PREDIKSJONER = "predictions"

_LINJE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def _navn(repo: Path) -> str:
    """Navnet repoet har på GitHub, ikke mappa det står i på en runner."""
    return "havbruk-radar-data" if repo == DATAREPO else "havbruk-radar"


def _sha(sti: Path) -> str:
    h = hashlib.sha256()
    with sti.open("rb") as f:
        for blokk in iter(lambda: f.read(1 << 20), b""):
            h.update(blokk)
    return h.hexdigest()


def kjente() -> set[tuple[str, str]]:
    """(sha256, sti) fra alle tidligere manifester."""
    ut = set()
    for m in sorted(STEMPEL_DIR.glob("*.manifest.txt")) if STEMPEL_DIR.exists() else []:
        for linje in m.read_text(encoding="utf-8").splitlines():
            treff = _LINJE.match(linje)
            if treff:
                ut.add((treff.group(1), treff.group(2)))
    return ut


def _sporet(repo: Path, *mapper: str) -> list[Path]:
    """Filene git kjenner i mappene. Det som er committet er det repoet
    påstår; en .DS_Store eller en halvskrevet fil på disken er det ikke."""
    r = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--", *mapper],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git ls-files i {repo}: {r.stderr.strip()}")
    return [repo / s for s in r.stdout.split("\0") if s]


def filer() -> list[tuple[str, Path]]:
    """(sti i manifestet, fila på disk), sortert."""
    data = [d.relative_to(DATAREPO).as_posix() for d in (DATA / u for u in DATAMAPPER)]
    ut = [(f"{_navn(DATAREPO)}/{p.relative_to(DATAREPO).as_posix()}", p)
          for p in _sporet(DATAREPO, *data)]
    ut += [(f"{_navn(KODEREPO)}/{p.relative_to(KODEREPO).as_posix()}", p)
           for p in _sporet(KODEREPO, PREDIKSJONER)]
    return sorted(ut)


def nye() -> list[tuple[str, str]]:
    """(sha256, sti) for filene som ikke står i et tidligere manifest."""
    sett = kjente()
    ut = []
    for sti, fil in filer():
        sha = _sha(fil)
        if (sha, sti) not in sett:
            ut.append((sha, sti))
    return ut


def head(repo: Path) -> str:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else f"(ukjent: {r.stderr.strip()})"


def manifest(linjer: list[tuple[str, str]], dato: str) -> str:
    topp = [
        "# STEMPELMANIFEST — havbruk-radar",
        f"# Skrevet av stempel.py {dato}. Ikke rediger: fila er stemplet,",
        "# og en rettet linje er ikke en rettelse.",
        "#",
        "# Hver linje: sha256 over filas bytes, to mellomrom, stien fra mappa",
        "# repoene ligger i. Bare filer som ikke sto i et tidligere manifest.",
        "#",
        f"# HEAD  {_navn(KODEREPO):<20} {head(KODEREPO)}",
        f"# HEAD  {_navn(DATAREPO):<20} {head(DATAREPO)}",
        f"# filer {len(linjer)}",
        "",
    ]
    return "\n".join(topp + [f"{sha}  {sti}" for sha, sti in linjer]) + "\n"


def ledig(dato: str) -> Path:
    sti, n = STEMPEL_DIR / f"{dato}.manifest.txt", 2
    while sti.exists():
        sti, n = STEMPEL_DIR / f"{dato}.{n}.manifest.txt", n + 1
    return sti


def ots(*args: str) -> subprocess.CompletedProcess:
    """`ots`-klienten. Byttes ut i prøvene."""
    return subprocess.run(["ots", *args], capture_output=True, text=True)


def stemple(manifest_sti: Path) -> bool:
    r = ots("stamp", str(manifest_sti))
    ok = r.returncode == 0 and Path(f"{manifest_sti}.ots").exists()
    if not ok:
        print(f"::error::ots stamp {manifest_sti.name} feilet (exit {r.returncode}): "
              f"{(r.stderr or r.stdout).strip()[-400:]}")
    return ok


def oppgrader(ventende: Path) -> bool | None:
    """Oppgrader en KOPI av `<x>.ots`. True: `<x>.komplett.ots` er skrevet.
    False: fortsatt ventende. None: klienten feilet på noe annet."""
    komplett = ventende.with_name(ventende.name.removesuffix(".ots") + ".komplett.ots")
    with tempfile.TemporaryDirectory() as t:
        kopi = Path(t) / ventende.name
        shutil.copy2(ventende, kopi)
        r = ots("upgrade", str(kopi))
        tekst = (r.stdout + r.stderr)
        if r.returncode == 0 and "Timestamp complete" in tekst:
            shutil.copy2(kopi, komplett)
            return True
        if "not complete" in tekst or "Pending" in tekst:
            return False
        print(f"::warning::ots upgrade {ventende.name} (exit {r.returncode}): "
              f"{tekst.strip()[-400:]}")
        return None


# Døgn et stempel kan vente på kalendrene før det sies fra om.
VENTER_MAKS = 2


def _alder(ventende: Path, dato: str) -> int | None:
    """Døgn siden manifestet ble skrevet, etter datoen i navnet vårt."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", ventende.name)
    if not m:
        return None
    return (dt.date.fromisoformat(dato) - dt.date.fromisoformat(m.group(1))).days


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="Datoen i manifestnavnet. Standard: i dag (UTC), slått "
                        "opp her og sendt inn (CLAUDE.md 1b).")
    a = p.parse_args(argv)
    dato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Stempel {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    linjer = nye()
    print(f"  {len(linjer)} fil(er) som ikke står i et tidligere manifest")
    if a.torrkjor:
        for sha, sti in linjer[:20]:
            print(f"    {sha[:16]}…  {sti}")
        if len(linjer) > 20:
            print(f"    … og {len(linjer) - 20} til")
        return 0

    feil = False
    STEMPEL_DIR.mkdir(parents=True, exist_ok=True)
    if linjer:
        sti = ledig(dato)
        sti.write_text(manifest(linjer, dato), encoding="utf-8")
        print(f"  manifest  {sti.name}")
    else:
        print("  ingen nye filer, intet manifest")

    # Hvert manifest uten stempel, også et som ble skrevet en tidligere
    # kjøring da kalendrene ikke svarte.
    for m in sorted(STEMPEL_DIR.glob("*.manifest.txt")):
        if not Path(f"{m}.ots").exists():
            if stemple(m):
                print(f"  stemplet  {m.name}.ots")
            else:
                feil = True

    for ventende in sorted(STEMPEL_DIR.glob("*.manifest.txt.ots")):
        if ventende.name.endswith(".komplett.ots"):
            continue
        if ventende.with_name(ventende.name.removesuffix(".ots") + ".komplett.ots").exists():
            continue
        utfall = oppgrader(ventende)
        print(f"  {'komplett ' if utfall else 'venter   ' if utfall is False else 'ukjent   '}"
              f"{ventende.name}")
        # Kalendrene har vanligvis en blokk innen timer. Venter et stempel
        # i dagevis, er det kalendrene og ikke kjeden som er problemet — og
        # dør de før oppgraderingen, dør beviset med dem.
        alder = _alder(ventende, dato)
        if not utfall and alder is not None and alder > VENTER_MAKS:
            print(f"::warning::{ventende.name} har ventet {alder} døgn på "
                  f"kalendrene (mer enn {VENTER_MAKS}). Se `ots info` på fila.")

    return 1 if feil else 0


if __name__ == "__main__":
    sys.exit(main())
