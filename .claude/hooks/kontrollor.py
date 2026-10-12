#!/usr/bin/env python3
"""PreToolUse-vakt for kontrolløren (.claude/agents/kontrollor.md).

Kontrolløren skal regne et tall ut på nytt fra kroppen, uten å se
skriptet som laget det og uten å kunne skrive noe. To ting håndheves
her, og ingen av dem hviler på at agenten følger instruksen:

  Bash        kommandoen kjøres om i `sandbox-exec` med en profil som
              nekter ALL filskriving (unntatt /dev/null og terminalen),
              all lesing under `analyse/`, kodrepoets `.git`, samtalene i
              ~/.claude/projects og /tmp, og alt nettverk. Det er kjernen
              som sier nei, ikke et mønster i kommandoteksten. Python,
              pipes og `$(...)` kjører inne i sandkassen, fordi hele
              kommandoen blir ett argument til en bash som starter der.
  Read/Grep/Glob
              nektes for de samme stiene. Grep og Glob nektes også når
              søkeroten ligger OVER en stengt mappe, fordi søket da
              går ned i den.

Hvorfor `analyse/` og `.git`: skriptene ligger i `analyse/`, og
`git show HEAD:analyse/...` ville lest dem uten å røre mappa.
Hvorfor ~/.claude/projects og /tmp: der ligger samtalen som produserte
dokumentet og mellomresultatene fra den, og kontrolløren skal aldri få
dem.

Hookens svar: `allow` med kommandoen pakket inn, eller `deny` med grunn.
Exit 2 ved feil i selve vakten, så en vakt som krasjer stenger i stedet
for å slippe gjennom.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
DATAREPO = (ROT.parent / "havbruk-radar-data").resolve()


def stengte() -> list[Path]:
    """Mappene kontrolløren ikke får lese. Reelle stier: sandkassen ser
    /private/tmp, ikke /tmp."""
    return [
        (ROT / "analyse").resolve(),
        (ROT / ".git").resolve(),
        (Path.home() / ".claude" / "projects").resolve(),
        Path("/private/tmp"),
    ]


def profil() -> str:
    """Sandkasseprofilen. Alt er lov unntatt det som nektes eksplisitt."""
    lesing = " ".join(f'(subpath "{p}")' for p in stengte())
    return (
        "(version 1)"
        "(allow default)"
        "(deny file-write*)"
        '(allow file-write* (literal "/dev/null") (literal "/dev/zero")'
        ' (literal "/dev/tty") (literal "/dev/dtracehelper")'
        ' (regex #"^/dev/fd/") (regex #"^/dev/ttys"))'
        f"(deny file-read* {lesing})"
        "(deny network*)"
    )


def pakk_inn(kommando: str) -> str:
    """Hele kommandoen som ETT enkeltsitert argument til en bash i
    sandkassen. Ingenting i den evalueres av skallet utenfor."""
    return ("sandbox-exec -p " + shlex.quote(profil())
            + " /bin/bash -c " + shlex.quote(kommando))


def _under(sti: Path, mappe: Path) -> bool:
    return sti == mappe or mappe in sti.parents


def stengt_sti(sti: Path) -> Path | None:
    """Mappa `sti` ligger i, hvis den er stengt."""
    for m in stengte():
        if _under(sti, m):
            return m
    return None


def stengt_soek(rot: Path) -> Path | None:
    """For Grep/Glob: stengt hvis roten er i ELLER over en stengt mappe."""
    for m in stengte():
        if _under(rot, m) or _under(m, rot):
            return m
    return None


def _losn(verdi: str, cwd: str) -> Path:
    p = Path(verdi).expanduser()
    if not p.is_absolute():
        p = Path(cwd) / p
    return p.resolve()


def vurder(inn: dict) -> dict:
    """Hookens JSON-svar for ett verktøykall."""
    verktoy = inn.get("tool_name", "")
    data = inn.get("tool_input") or {}
    cwd = inn.get("cwd") or str(ROT)

    def nekt(grunn: str) -> dict:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": grunn}}

    if verktoy == "Bash":
        kommando = data.get("command", "")
        ny = dict(data)
        ny["command"] = pakk_inn(kommando)
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason":
                "kontrolløren: kjøres i sandkasse uten skriving og nett",
            "updatedInput": ny}}

    if verktoy == "Read":
        sti = _losn(data.get("file_path", ""), cwd)
        m = stengt_sti(sti)
        if m:
            return nekt(f"Kontrolløren får ikke lese {m}. Regn ut tallet "
                        f"fra kroppen i datarepoet, ikke fra skriptet "
                        f"eller samtalen som laget det.")
        return {}

    if verktoy in ("Grep", "Glob"):
        rot = _losn(data.get("path") or cwd, cwd)
        m = stengt_soek(rot)
        if m:
            return nekt(f"Søket ville gått gjennom {m}, som er stengt for "
                        f"kontrolløren. Søk i docs/ eller i {DATAREPO}.")
        return {}

    # Alt annet (Write, Edit, ...) skal agenten ikke ha. Står det i
    # verktøylista likevel, nektes det her.
    return nekt(f"Kontrolløren har bare lesende verktøy; {verktoy} er nektet.")


def main() -> int:
    try:
        inn = json.load(sys.stdin)
        svar = vurder(inn)
    except Exception as e:                       # noqa: BLE001
        print(f"kontrollør-vakten feilet ({e!r}); kallet stoppes.",
              file=sys.stderr)
        return 2
    if svar:
        print(json.dumps(svar, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
