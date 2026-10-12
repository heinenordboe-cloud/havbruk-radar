#!/usr/bin/env python3
"""PreToolUse-vakt: data/arkiv/ og data/raw/ i datarepoet skrives én gang.

CLAUDE.md regel 2. Rådata og råarkiv skrives av `raw.arkiver_ny()` og
`snapshot.write()`, som aldri overskriver og løser kollisjon med
løpenummer. Denne vakten stopper alt ANNET som ville skrevet, flyttet
eller slettet der:

  Write, Edit, MultiEdit, NotebookEdit   på en fil der
  rm, rmdir, unlink, shred, truncate,
  touch, tee, dd of=                      med en sti der
  mv                                      med en sti der, til eller fra
  cp, rsync, install, ln, ditto           med målet der
  sed -i, perl -i                         på en fil der
  > >> >| &>                              omdirigert dit
  git rm, git mv, git clean               med en sti der
  find … -delete / -exec rm               under en sti der
  xargs rm|mv|…                           når en sti der står i kommandoen

Python-skriptene som arkiverer (`arkiver_*.py`, `run.py`,
`backfill.py`) berøres ikke: de går gjennom `raw.arkiver_ny()`, og
vakten ser bare kommandolinja. Lesing (`ls`, `zcat`, `shasum`, `cp` FRA
arkivet) slipper gjennom.

Stien er vernet når den ligger under `<datarepo>/data/arkiv` eller
`<datarepo>/data/raw`, der datarepoet er `../havbruk-radar-data`,
`HAVBRUK_DATA_DIR` når den er satt, eller en hvilken som helst mappe som
heter havbruk-radar-data. Relative stier løses mot `cwd` og mot `cd` i
samme kommando.

Exit 2 stopper kallet og grunnen går til Claude. Exit 2 også når vakten
selv feiler: en vakt som krasjer skal stenge.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shlex
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
DATAREPO_NAVN = "havbruk-radar-data"
VERNET = ("arkiv", "raw")

SLETT = {"rm", "rmdir", "unlink", "shred", "truncate", "touch", "tee"}
KOPI = {"cp", "rsync", "install", "ln", "ditto", "gcp"}
OMDIRIGERING = {">", ">>", ">|", "&>", "&>>"}
SKILLE = {";", "&&", "||", "|", "&", "(", ")", "|&"}
INNPAKNING = {"sudo", "env", "command", "nohup", "time", "nice", "builtin",
              "do", "then", "else", "elif", "!", "{"}
SKALL = {"bash", "sh", "zsh", "dash"}


def _datamapper() -> list[Path]:
    mapper = [(ROT.parent / DATAREPO_NAVN / "data").resolve()]
    if os.environ.get("HAVBRUK_DATA_DIR"):
        mapper.append(Path(os.environ["HAVBRUK_DATA_DIR"]).expanduser().resolve())
    return mapper


def vernet(sti: Path) -> bool:
    """Ligger stien i data/arkiv/ eller data/raw/ i datarepoet?"""
    for data in _datamapper():
        for under in VERNET:
            mappe = data / under
            if sti == mappe or mappe in sti.parents:
                return True
    deler = sti.parts
    for i in range(len(deler) - 2):
        if (deler[i] == DATAREPO_NAVN and deler[i + 1] == "data"
                and deler[i + 2] in VERNET):
            return True
    return False


def _losn(ord_: str, cwd: Path) -> list[Path]:
    """Stien ordet peker på, og hva det matcher som glob."""
    tekst = os.path.expanduser(os.path.expandvars(ord_))
    p = Path(tekst)
    if not p.is_absolute():
        p = cwd / p
    ut = [Path(os.path.normpath(p))]
    try:
        ut.append(p.resolve())
    except (OSError, RuntimeError):
        pass
    if any(c in tekst for c in "*?["):
        ut += [Path(t).resolve() for t in glob.glob(str(p))]
    return ut


def _treff(ord_: list[str], cwd: Path) -> str:
    for o in ord_:
        if o.startswith("-") and "=" not in o:
            continue
        verdi = o.split("=", 1)[1] if o.startswith("-") or o.startswith("of=") else o
        if any(vernet(p) for p in _losn(verdi, cwd)):
            return o
    return ""


def _ord(kommando: str) -> list[str]:
    lex = shlex.shlex(kommando.replace("\n", " ; "), posix=True,
                      punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def _segmenter(ord_: list[str]) -> list[list[str]]:
    ut, seg = [], []
    for o in ord_:
        if o in SKILLE:
            if seg:
                ut.append(seg)
            seg = []
        else:
            seg.append(o)
    if seg:
        ut.append(seg)
    return ut


def _verb(seg: list[str]) -> tuple[str, list[str]]:
    i = 0
    while i < len(seg) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[i])
                            or seg[i] in INNPAKNING):
        i += 1
    if i >= len(seg):
        return "", []
    return os.path.basename(seg[i]), seg[i + 1:]


def vurder_bash(kommando: str, cwd: Path, dybde: int = 0) -> str:
    """Grunnen til å stoppe, eller tom streng."""
    try:
        ord_ = _ord(kommando)
    except ValueError:
        # Ubalanserte anførselstegn: vi vet ikke hva som er argumenter.
        # Står en vernet sti og et skriveverb i teksten, stoppes det.
        if re.search(r"(arkiv|raw)/", kommando) and re.search(
                r"\b(rm|mv|cp|truncate|tee|touch)\b|sed\s+-i|>", kommando):
            return "kommandoen kan ikke tolkes, og den nevner arkiv/ eller raw/"
        return ""

    hele = _treff([o for o in ord_ if o not in SKILLE | OMDIRIGERING], cwd)
    for seg in _segmenter(ord_):
        # Omdirigering kan stå hvor som helst i segmentet.
        for i, o in enumerate(seg):
            if o in OMDIRIGERING and i + 1 < len(seg) and not seg[i + 1].startswith("&"):
                if _treff([seg[i + 1]], cwd):
                    return f"omdirigering {o} til {seg[i + 1]}"
        renset = [o for i, o in enumerate(seg)
                  if o not in OMDIRIGERING and not (i and seg[i - 1] in OMDIRIGERING)
                  and o not in ("<", "<<", "<<<")]
        verb, arg = _verb(renset)
        if verb == "cd":
            if arg:
                cwd = _losn(arg[0], cwd)[0]
            continue
        if verb in SKALL and "-c" in arg and dybde < 3:
            indre = arg[arg.index("-c") + 1] if arg.index("-c") + 1 < len(arg) else ""
            grunn = vurder_bash(indre, cwd, dybde + 1)
            if grunn:
                return grunn
            continue
        # En variabel eller `$(...)` kan peke hvor som helst. Nevner
        # kommandoen en vernet sti, stoppes et skriveverb som tar en.
        skriver = verb in SLETT | KOPI | {"mv", "dd"} or (
            verb in ("sed", "gsed", "perl")
            and any(a.startswith("-") and "i" in a[1:] for a in arg))
        if skriver and hele and (any("$" in a or "`" in a for a in arg)
                                 or re.search(r"\$\(|`", kommando)):
            return f"{verb} med variabel eller $(...) i en kommando som nevner {hele}"
        if verb in SLETT and (t := _treff(arg, cwd)):
            return f"{verb} {t}"
        if verb == "dd" and (t := _treff([a for a in arg if a.startswith("of=")], cwd)):
            return f"dd {t}"
        if verb == "mv" and (t := _treff(arg, cwd)):
            return f"mv {t}"
        if verb in KOPI:
            filer = [a for a in arg if not a.startswith("-")]
            mal = [a.split("=", 1)[1] for a in arg if a.startswith("--target-directory=")]
            if "-t" in arg and arg.index("-t") + 1 < len(arg):
                mal.append(arg[arg.index("-t") + 1])
            elif filer:
                mal.append(filer[-1])
            if t := _treff(mal, cwd):
                return f"{verb} til {t}"
        if verb in ("sed", "gsed") and any(
                a == "--in-place" or a.startswith("--in-place=")
                or (a.startswith("-") and not a.startswith("--") and "i" in a[1:])
                for a in arg) and (t := _treff(arg, cwd)):
            return f"{verb} -i {t}"
        if verb == "perl" and any(a.startswith("-") and "i" in a[1:] for a in arg) \
                and (t := _treff(arg, cwd)):
            return f"perl -i {t}"
        if verb == "git" and arg:
            under = next((a for a in arg if not a.startswith("-")), "")
            if under in ("rm", "mv", "clean") and (t := _treff(arg[arg.index(under) + 1:], cwd)):
                return f"git {under} {t}"
        if verb == "find" and ("-delete" in arg or any(
                a in ("-exec", "-execdir", "-ok") and i + 1 < len(arg)
                and os.path.basename(arg[i + 1]) in SLETT | {"mv"}
                for i, a in enumerate(arg))) and (t := _treff(arg, cwd)):
            return f"find {t} med sletting"
        if verb == "xargs" and hele:
            indre = next((a for a in arg if not a.startswith("-")), "")
            if os.path.basename(indre) in SLETT | KOPI | {"mv", "sed"}:
                return f"xargs {indre} i en kommando som nevner {hele}"
    return ""


def vurder(inn: dict) -> str:
    verktoy = inn.get("tool_name", "")
    data = inn.get("tool_input") or {}
    cwd = Path(inn.get("cwd") or os.getcwd())
    if verktoy in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        sti = data.get("file_path") or data.get("notebook_path") or ""
        if sti and any(vernet(p) for p in _losn(sti, cwd)):
            return f"{verktoy} på {sti}"
        return ""
    if verktoy == "Bash":
        return vurder_bash(data.get("command", ""), cwd)
    return ""


def main() -> int:
    try:
        grunn = vurder(json.load(sys.stdin))
    except Exception as e:                       # noqa: BLE001
        print(f"arkivvakten feilet ({e!r}); kallet stoppes.", file=sys.stderr)
        return 2
    if grunn:
        print(f"CLAUDE.md regel 2: data/arkiv/ og data/raw/ i datarepoet "
              f"skrives én gang, av raw.arkiver_ny() og snapshot.write(). "
              f"Stoppet: {grunn}. Skal en kropp inn, kjør skriptet som "
              f"arkiverer den.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
