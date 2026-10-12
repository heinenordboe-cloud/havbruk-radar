#!/usr/bin/env python3
"""PreToolUse-vakt på `git commit`: personnavn i docs/ og analyse/.

CLAUDE.md regel 3, på tekstene vi skriver selv. Publiseringsvakten
holder navn borte fra NETTSTEDET; denne holder dem borte fra REPOET,
og den kjører før committen, fordi en commit med et navn i er
historikk (regel 2), og historikken følger med den dagen repoet åpnes.

Regelen er publiseringsvaktens, ikke en kopi:

  personform_i_navn   et navn som ender på en personformkode
                      («… ANS», «… DA»). Prøves på hver tabellcelle,
                      hver CSV-celle og hver rekke av ord i versaler i
                      løpende tekst, fordi et navn i en måling står der
                      like gjerne som i en tabell.
  PERSONNAVN          «ETTERNAVN, FORNAVN». Prøves bare på HELE celler,
                      som i porten: over løpende tekst treffer mønsteret
                      «KOMMUNE, FYLKE» (MÅLT 05.10.2026, 1 818 strenger).

Hvilke former som er personlige, avgjør `core/persondata.PERSONFORMER`
gjennom `publiseringsvakt`, så grensa flytter seg med den.

Filene er de ENDREDE tekstfilene under docs/ og analyse/: i indeksen, i
arbeidstreet (for `git commit -a` og `git add … && git commit`) og nye
filer som ikke er ignorert. Det er en overtelling med vilje: et treff i
en fil som ikke blir med, koster en ekstra `git add` av riktig fil; et
navn som slapp gjennom, kan ikke tas tilbake.

Rapporten gir fil, linje og hvilken regel som slo til, aldri navnet:
hookens utskrift havner i samtalen og kan havne i en logg.

Exit 2 stopper committen. Exit 2 også når vakten selv feiler, fordi en
vakt som krasjer skal stenge, ikke slippe gjennom.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
MAPPER = ("docs/", "analyse/")

# Ord i versaler, minst to etter hverandre: et navn slik registrene og
# målingene skriver det. Organisasjonsformen er siste ord.
_VERSAL = r"[A-ZÆØÅÉÜÖÄ0-9][A-ZÆØÅÉÜÖÄ0-9&'.\-/]*"
VERSALREKKE = re.compile(rf"{_VERSAL}(?:[ \t]+{_VERSAL})+")
MARKDOWN = re.compile(r"[*`_]+")


def _vakt():
    sys.path.insert(0, str(ROT))
    import publiseringsvakt
    return publiseringsvakt


def er_commit(kommando: str) -> list[Path]:
    """Mappene det committes i, eller tom liste når kommandoen ikke er
    en `git commit`. Følger `cd` og `git -C`."""
    try:
        lex = shlex.shlex(kommando.replace("\n", " ; "), posix=True,
                          punctuation_chars=True)
        lex.whitespace_split = True
        ord_ = list(lex)
    except ValueError:
        return [Path.cwd()] if re.search(r"\bgit\b.*\bcommit\b", kommando) else []
    cwd = Path.cwd()
    ut: list[Path] = []
    segment: list[str] = []
    for o in ord_ + [";"]:
        if o in (";", "&&", "||", "|", "&", "(", ")"):
            if segment and segment[0] == "cd" and len(segment) > 1:
                cwd = (cwd / os.path.expanduser(segment[1])).resolve()
            elif segment and segment[0] == "git":
                mappe, i = cwd, 1
                while i < len(segment) and segment[i].startswith("-"):
                    if segment[i] == "-C" and i + 1 < len(segment):
                        mappe = (cwd / os.path.expanduser(segment[i + 1])).resolve()
                        i += 2
                    elif segment[i] in ("-c", "--git-dir", "--work-tree"):
                        i += 2
                    else:
                        i += 1
                if i < len(segment) and segment[i] == "commit":
                    ut.append(mappe)
            segment = []
        else:
            segment.append(o)
    return ut


def _git(mappe: Path, *args: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(mappe), *args],
                       capture_output=True, text=True, check=True)
    return [linje for linje in r.stdout.splitlines() if linje]


def endrede_filer(mappe: Path) -> tuple[Path, list[str]]:
    """(repoets rot, endrede stier under docs/ og analyse/)."""
    rot = Path(_git(mappe, "rev-parse", "--show-toplevel")[0])
    stier = set(_git(rot, "diff", "--cached", "--name-only", "--diff-filter=ACMR"))
    stier |= set(_git(rot, "diff", "--name-only", "--diff-filter=ACMR"))
    stier |= set(_git(rot, "ls-files", "--others", "--exclude-standard"))
    return rot, sorted(s for s in stier if s.startswith(MAPPER))


def _tekst(sti: Path) -> str | None:
    try:
        data = sti.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _celler(linje: str, endelse: str) -> list[str]:
    if endelse in (".csv", ".tsv"):
        skille = "\t" if endelse == ".tsv" else ","
        try:
            rad = next(csv.reader(io.StringIO(linje), delimiter=skille))
        except (csv.Error, StopIteration):
            return []
        return [c.strip() for c in rad]
    if linje.lstrip().startswith("|"):
        return [MARKDOWN.sub("", c).strip() for c in linje.strip().strip("|").split("|")]
    return []


# En kolonne er en NAVNEKOLONNE når overskriften sier det. Det er
# markdown-utgaven av portens `NAVNEFELT`: PERSONNAVN prøves bare der,
# fordi mønsteret over alle celler også treffer «MÅLT, AVGRENSET» og
# «DA, ANS, PRE» (MÅLT 12.10.2026 over docs/ og analyse/).
NAVNEKOLONNE = re.compile(
    r"(?i)navn|eier|selskap|mottaker|innehaver|foretak|kjøper|selger|"
    r"tildelt|avgiver|person")
SKILLERAD = re.compile(r"^\s*\|?\s*:?-{3,}")
_ORD = re.compile(r"[A-Za-zÆØÅæøåÉÜÖÄéüöä]{2,}")


def _kodeord(vakt) -> frozenset[str]:
    return frozenset(vakt.FORMKODER) | frozenset(vakt.persondata.PERSONFORMER) | {"OG"}


def _som_navn(kandidat: str, kodeord: frozenset[str]) -> str:
    """Kandidaten fra første ord med bokstaver, eller tom streng når den
    ikke har et eneste ord som ikke er en formkode. «32 DA», «DA, ANS,
    PRE» og «2 ANS, 6 DA» er opptellinger av former, ikke navn."""
    ord_ = kandidat.split()
    while ord_ and not _ORD.search(ord_[0]):
        ord_.pop(0)
    return " ".join(ord_) if _har_navneord(ord_[:-1], kodeord) else ""


def _har_navneord(ord_: list[str], kodeord: frozenset[str]) -> bool:
    """Minst ett ord med bokstaver som ikke er en formkode."""
    return any(_ORD.fullmatch(o.strip(",.()")) and o.strip(",.()").upper() not in kodeord
               for o in ord_)


def funn_i_tekst(tekst: str, endelse: str = ".md") -> list[tuple[int, str]]:
    """(linjenummer, regel) for hvert treff. Aldri selve navnet."""
    vakt = _vakt()
    kodeord = _kodeord(vakt)
    ut: list[tuple[int, str]] = []
    linjer = tekst.splitlines()
    overskrift: list[str] = []
    for nr, linje in enumerate(linjer, 1):
        celler = _celler(linje, endelse)
        if endelse in (".csv", ".tsv") and nr == 1:
            overskrift = celler
        elif linje.lstrip().startswith("|"):
            neste = linjer[nr] if nr < len(linjer) else ""
            if SKILLERAD.match(neste):
                overskrift = celler
            if SKILLERAD.match(linje):
                continue
        elif endelse not in (".csv", ".tsv"):
            overskrift = []

        kandidater = celler + [m.group(0) for m in
                               VERSALREKKE.finditer(MARKDOWN.sub("", linje))]
        kode = next((k for k in (vakt.personform_i_navn(_som_navn(c, kodeord))
                                 for c in kandidater) if k), "")
        if kode:
            ut.append((nr, f"navn med personformen {kode}"))
            continue
        navneceller = [c for i, c in enumerate(celler)
                       if i < len(overskrift) and NAVNEKOLONNE.search(overskrift[i])
                       and c != overskrift[i]]
        if any(vakt.PERSONNAVN.fullmatch(c) and _har_navneord(c.split(), kodeord)
               for c in navneceller if c):
            ut.append((nr, "«ETTERNAVN, FORNAVN» i en navnecelle"))
    return ut


def vurder(kommando: str) -> list[str]:
    """Linjene som stopper committen. Tom liste: slipp gjennom."""
    rapport: list[str] = []
    for mappe in er_commit(kommando):
        rot, stier = endrede_filer(mappe)
        for rel in stier:
            tekst = _tekst(rot / rel)
            if tekst is None:
                continue
            for nr, regel in funn_i_tekst(tekst, Path(rel).suffix.lower()):
                rapport.append(f"{rel}:{nr}: {regel}")
    return rapport


def main() -> int:
    try:
        inn = json.load(sys.stdin)
        if inn.get("tool_name") != "Bash":
            return 0
        kommando = (inn.get("tool_input") or {}).get("command", "")
        if "commit" not in kommando:
            return 0
        os.chdir(inn.get("cwd") or ROT)
        rapport = vurder(kommando)
    except Exception as e:                       # noqa: BLE001
        print(f"persondatavakten feilet ({e!r}); committen stoppes.",
              file=sys.stderr)
        return 2
    if rapport:
        print("CLAUDE.md regel 3: committen stoppes. Teksten under docs/ "
              "eller analyse/ har det publiseringsvakten leser som et "
              "personnavn (navnet gjentas ikke her):", file=sys.stderr)
        for linje in rapport:
            print(f"  {linje}", file=sys.stderr)
        print("Fjern navnet, eller skriv det som publiseringsvakt."
              "skjult_navn() gjør.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
