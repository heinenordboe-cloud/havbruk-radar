"""Vaktene i .claude/: kontrolløren og PreToolUse-hookene.

De kjører i Claude Code og ikke i pipelinen, men de er regler i
CLAUDE.md gjort mekaniske, og en regel som ikke er prøvd er en regel vi
tror på. Hver vakt har minst én prøve som skal stoppes og én som skal
slippe gjennom.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parents[1]
HOOKS = ROT / ".claude" / "hooks"


def _last(navn: str, sti: Path):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


kontrollor = _last("kontrollor_vakt", HOOKS / "kontrollor.py")
trekk = _last("kontroll_trekk", ROT / "verktoy" / "kontroll_trekk.py")


# ------------------------------------------------------------ kontrolløren

def _beslutning(svar: dict) -> str:
    return (svar.get("hookSpecificOutput") or {}).get("permissionDecision", "")


def test_kontrollor_bash_pakkes_inn_i_sandkasse():
    svar = kontrollor.vurder({"tool_name": "Bash", "cwd": str(ROT),
                              "tool_input": {"command": "echo hei; ls"}})
    assert _beslutning(svar) == "allow"
    ny = svar["hookSpecificOutput"]["updatedInput"]["command"]
    assert ny.startswith("sandbox-exec -p ")
    assert ny.endswith("/bin/bash -c 'echo hei; ls'"), \
        "hele kommandoen skal være ETT argument til bash i sandkassen"


@pytest.mark.skipif(not shutil.which("sandbox-exec"), reason="bare macOS")
def test_kontrollor_kan_ikke_skrive_men_kan_lese(tmp_path):
    """Kjernen sier nei, ikke et mønster i teksten: Python skriver heller
    ikke."""
    les = tmp_path / "les.txt"
    les.write_text("innhold\n")
    ut = tmp_path / "ut.txt"
    kommando = (f"cat {les}; echo x > {ut}; "
                f"{sys.executable} -c 'open(\"{ut}\", \"w\")'")
    svar = kontrollor.vurder({"tool_name": "Bash", "cwd": str(ROT),
                              "tool_input": {"command": kommando}})
    r = subprocess.run(["/bin/bash", "-c",
                        svar["hookSpecificOutput"]["updatedInput"]["command"]],
                       capture_output=True, text=True)
    assert "innhold" in r.stdout
    assert "Operation not permitted" in r.stderr
    assert not ut.exists()


@pytest.mark.skipif(not shutil.which("sandbox-exec"), reason="bare macOS")
def test_kontrollor_kan_ikke_lese_analyse_i_skallet():
    fil = next((ROT / "analyse").rglob("*.py"))
    svar = kontrollor.vurder({"tool_name": "Bash", "cwd": str(ROT),
                              "tool_input": {"command": f"head -1 {fil}"}})
    r = subprocess.run(["/bin/bash", "-c",
                        svar["hookSpecificOutput"]["updatedInput"]["command"]],
                       capture_output=True, text=True)
    assert r.returncode != 0 and not r.stdout


def test_kontrollor_read_i_analyse_nektes_og_docs_slipper():
    nekt = kontrollor.vurder({"tool_name": "Read", "cwd": str(ROT),
                              "tool_input": {"file_path": "analyse/x.py"}})
    assert _beslutning(nekt) == "deny"
    ok = kontrollor.vurder({"tool_name": "Read", "cwd": str(ROT),
                            "tool_input": {"file_path": "docs/RUNBOOK.md"}})
    assert ok == {}


def test_kontrollor_grep_over_analyse_nektes_og_i_docs_slipper():
    nekt = kontrollor.vurder({"tool_name": "Grep", "cwd": str(ROT),
                              "tool_input": {"pattern": "x"}})
    assert _beslutning(nekt) == "deny", "uten path søker Grep fra roten"
    ok = kontrollor.vurder({"tool_name": "Grep", "cwd": str(ROT),
                            "tool_input": {"pattern": "x", "path": "docs"}})
    assert ok == {}


def test_kontrollor_skriveverktoy_nektes():
    svar = kontrollor.vurder({"tool_name": "Write", "cwd": str(ROT),
                              "tool_input": {"file_path": "x.txt"}})
    assert _beslutning(svar) == "deny"


def test_trekk_teller_bare_bekreftet_maalt_med_tall(tmp_path):
    dok = tmp_path / "MALING-X.md"
    dok.write_text(
        "# Måling\n\n"
        "Testen bruker 954 lokaliteter. MÅLT.\n\n"
        "Delingen er MÅLBAR, ikke MÅLT, fordi 10 grenser kan ha flyttet seg.\n\n"
        "MÅLT at siden ble hentet 12.10.2026 i 2026.\n\n"
        "- **De to kroppene er enige** om 143 kommuner. MÅLT.\n\n"
        "```\nMÅLT 99 i en kodeblokk\n```\n", encoding="utf-8")
    alle = trekk.kandidater(dok)
    assert [(fra, tall) for fra, _, _, tall in alle] == [
        (3, ["954"]), (9, ["143"])]


def test_trekk_med_samme_fro_gir_samme_utvalg(tmp_path, capsys):
    dok = tmp_path / "MALING-X.md"
    dok.write_text("\n\n".join(f"Tallet er {n}. MÅLT." for n in range(10, 30)),
                   encoding="utf-8")
    trekk.main([str(dok), "--fro", "42"])
    en = capsys.readouterr().out
    trekk.main([str(dok), "--fro", "42"])
    assert capsys.readouterr().out == en
    assert "frø 42" in en and en.count("=== trekk") == 3
