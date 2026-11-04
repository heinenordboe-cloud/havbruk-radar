"""Hvilke av de tre kravene i CLAUDE.md §8 som mangler.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data .venv/bin/python verktoy/ferdig.py

En jobb, tjeneste eller test er ikke ferdig før

  1  den har kjørt i sitt ekte miljø, ikke bare lokalt
       workflow   minst én vellykket kjøring i Actions (gh api)
       tjeneste   `active` og `success` i data/ais/status.json, slik
                  kystvakt-1 meldte sist
       prøver     `miljo` i verktoy/ferdig.yml, og for «Tester» en grønn
                  kjøring i Actions
  2  den har frist i jobber.yml eller sjekk i Healthchecks
       workflow   `stillhet` i datarepoets .github/jobber.yml, ellers
                  `healthchecks` i ferdig.yml
       ellers     `frist` i ferdig.yml
  3  en feil laget med vilje har vist at varselet kommer
                  `feilprove` i jobber.yml eller ferdig.yml

Skriver én linje per jobb, tjeneste og prøvesamling, med «mangler 1, 3»
og hva som ble lest. Exit 0: kontrollen SIER hva som mangler, den stopper
ingenting. Det som mangler, står i rapporten (CLAUDE.md §8).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROT = Path(__file__).resolve().parent.parent
FERDIG = Path(__file__).resolve().parent / "ferdig.yml"
DATAREPO = "heinenordboe-cloud/havbruk-radar-data"
KODREPO = "heinenordboe-cloud/havbruk-radar"


def vellykkede(repo: str, fil: str) -> int | None:
    """Antall vellykkede kjøringer av workflowen, eller None uten svar."""
    r = subprocess.run(["gh", "api", f"repos/{repo}/actions/workflows/{fil}/runs"
                        "?status=success&per_page=1", "--jq", ".total_count"],
                       capture_output=True, text=True)
    return int(r.stdout) if r.returncode == 0 and r.stdout.strip().isdigit() else None


def rad(navn: str, ekte: str | None, frist: str | None, feilprove: str | None) -> str:
    mangler = [str(i) for i, v in ((1, ekte), (2, frist), (3, feilprove)) if not v]
    hva = "ferdig" if not mangler else f"mangler {', '.join(mangler)}"
    detalj = "; ".join(f"{i} {v}" for i, v in ((1, ekte), (2, frist), (3, feilprove)) if v)
    return f"  {navn:<34} {hva:<16} {detalj}"


def workflows(jobber: dict, hc: dict, kall=vellykkede) -> list[str]:
    ut = []
    for fil, j in jobber.items():
        n = kall(DATAREPO, fil)
        ekte = f"{n} vellykkede i Actions" if n else None
        s = j.get("stillhet")
        frist = (f"jobber.yml {s['maks_dogn']} døgn ({s['maales']})" if s else hc.get(fil))
        ut.append(rad(fil, ekte, frist, j.get("feilprove")))
    return ut


def tjenester(ferdig: dict, status: dict | None) -> list[str]:
    tj = (status or {}).get("tjenester") or {}
    ut = []
    for enhet, f in ferdig["tjenester"].items():
        v = tj.get(enhet) or {}
        ekte = (f"{v['tilstand']}/{v['resultat']} {status.get('skrevet', '')}"
                if v.get("tilstand") == "active" and v.get("resultat") == "success" else None)
        ut.append(rad(enhet, ekte, f.get("frist"), f.get("feilprove")))
    return ut


def prover(ferdig: dict, kall=vellykkede) -> list[str]:
    ut = []
    for navn, f in ferdig["prover"].items():
        ekte = f.get("miljo")
        if ekte and navn.startswith("Tester"):
            n = kall(KODREPO, "test.yml")
            ekte = f"{ekte}, {n} vellykkede" if n else None
        ut.append(rad(navn, ekte, f.get("frist"), f.get("feilprove")))
    return ut


def main() -> int:
    data = Path(os.environ.get("HAVBRUK_DATA_DIR", ROT / "data"))
    jobber_yml = data.parent / ".github" / "jobber.yml"
    status_json = data / "ais" / "status.json"
    jobber = yaml.safe_load(jobber_yml.read_text(encoding="utf-8"))["jobber"]
    ferdig = yaml.safe_load(FERDIG.read_text(encoding="utf-8"))
    status = json.loads(status_json.read_text(encoding="utf-8")) if status_json.exists() else None

    print("Ferdig? Krav 1 ekte miljø, 2 frist eller sjekk, 3 feil med vilje (CLAUDE.md §8)")
    print(f"\nWorkflows i datarepoet ({jobber_yml})")
    linjer = workflows(jobber, ferdig.get("healthchecks") or {})
    print(*linjer, sep="\n")
    print(f"\nTjenester på kystvakt-1 ({status_json})")
    linjer += tjenester(ferdig, status)
    print(*linjer[-len(ferdig["tjenester"]):], sep="\n")
    print("\nPrøvesamlinger")
    p = prover(ferdig)
    linjer += p
    print(*p, sep="\n")
    uferdige = sum(1 for linje in linjer if " mangler " in linje)
    print(f"\n{len(linjer) - uferdige} av {len(linjer)} ferdige.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
