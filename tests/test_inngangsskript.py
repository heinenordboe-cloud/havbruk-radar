"""Inngangsskriptene som kjøres med færre pakker enn requirements.txt.

ais-manifest.yml installerer ingen pakker og kjører ais_manifest.py. bcd4221
(07.11.2026) lot core/karantene.py importere core/persondata.py, som
importerer polars, og jobben var rød 07.11 og 08.11 uten at noen prøve sa
fra: prøvene kjører der alt i requirements.txt er installert.

Hver prøve under importerer ett inngangsskript i en egen prosess. En
sperre først i `sys.meta_path` slipper gjennom standardbiblioteket,
kodrepoets egne moduler og pakkene jobben installerer, og ingenting
annet. Importen kjører modulnivået, ikke main(): det var der
ModuleNotFoundError kom.

Målt 08.11.2026 i datarepoets workflows:

    workflow:jobb              installerer                    kjører fra kodrepoet
    ais-manifest.yml:hent      ingenting                      ais_manifest.py
    publiser.yml:publiser      PyYAML, bare i automatisk      publiser_ci.py, royktest.py
    publiser.yml:tilbakerull   ingenting                      publiser_ci.py, royktest.py
    stempel.yml:stempel        opentimestamps-client==0.7.2   stempel.py

tilsyn.yml installerer PyYAML, men henter ikke kodrepoet. Alle andre jobber
som henter det, installerer requirements.txt. kystvakt-1 kjører
kystvakt/*.py med /usr/bin/python3 og ingen pakker; den har sin egen prøve. Står datarepoet ved siden av
kodrepoet, sjekker `test_tabellen_er_workflowene` at dette fortsatt er
sant; i kodrepoets Actions finnes det ikke, og den prøven hoppes over.

Late importer, inne i en funksjon, prøves ikke her. Målt samme dag:
publiser_ci.py når nettsted og publiseringsvakt (polars) bare fra `bygg`,
som kjøres i bygg.yml med requirements.txt, og core.config (PyYAML) bare
fra `automatisk`, der PyYAML er installert.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROT = Path(__file__).resolve().parent.parent
KODREPO = "heinenordboe-cloud/havbruk-radar"
WORKFLOWS = ROT.parent / "havbruk-radar-data/.github/workflows"

# Toppnavnene en pakke gir `import`, med avhengighetene. opentimestamps-client
# 0.7.2 er målt 08.11.2026 med importlib.metadata på klienten som er
# installert lokalt (GitPython, PySocks, appdirs, opentimestamps,
# pycryptodomex, python-bitcoinlib, typing_extensions).
TOPPNAVN = {
    "PyYAML": ("yaml", "_yaml"),
    "opentimestamps-client": ("otsclient", "opentimestamps", "bitcoin", "git",
                              "gitdb", "smmap", "socks", "sockshandler",
                              "appdirs", "Cryptodome", "typing_extensions"),
}

# workflow:jobb -> (installeres alltid, installeres bare av og til, skript).
# En pakke som bare installeres av og til, slippes ikke gjennom: skriptet
# kjøres også uten den. publiser.yml:publiser installerer PyYAML når
# modus er automatisk, og kjører publiser_ci.py uten den når et menneske
# har sagt ja.
JOBBER = {
    "ais-manifest.yml:hent": ((), (), ("ais_manifest",)),
    "publiser.yml:publiser": ((), ("PyYAML",), ("publiser_ci", "royktest")),
    "publiser.yml:tilbakerull": ((), (), ("publiser_ci", "royktest")),
    "stempel.yml:stempel": (("opentimestamps-client",), (), ("stempel",)),
}

# Kjøres med `-I -S`: ingen PYTHONPATH, ingen .pth-filer. Standardbiblioteket
# er sys.path slik `-S` etterlater den; pakkene legges til etterpå, bak
# sperren.
SPERRE = r'''
import importlib, importlib.machinery, site, sys
rot, modul, *tillatt = sys.argv[1:]
tillatt = set(tillatt)
stdlib = list(sys.path)

class Sperre:
    def find_spec(self, navn, sti=None, mal=None):
        if ("." in navn or navn in tillatt or navn in sys.stdlib_module_names
                or navn in sys.builtin_module_names):
            return None
        for steder in (stdlib, [rot]):
            if importlib.machinery.PathFinder.find_spec(navn, steder) is not None:
                return None
        raise ModuleNotFoundError(
            f"No module named {navn!r} (ikke installert der skriptet kjøres)", name=navn)

sys.path[:0] = [rot]
sys.path += site.getsitepackages()
sys.meta_path.insert(0, Sperre())
importlib.import_module(modul)
'''


def importer(modul: str, tillatt=(), rot: Path = ROT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", SPERRE, str(rot), modul, *tillatt],
        capture_output=True, text=True, timeout=120)


TILFELLER = [(jobb, skript, alltid)
             for jobb, (alltid, _, skriptene) in JOBBER.items()
             for skript in skriptene]


@pytest.mark.parametrize("jobb,skript,pakker", TILFELLER,
                         ids=[f"{j}-{s}" for j, s, _ in TILFELLER])
def test_inngangsskriptet_importeres_med_jobbens_pakker(jobb, skript, pakker):
    tillatt = [n for p in pakker for n in TOPPNAVN[p]]
    r = importer(skript, tillatt)
    assert r.returncode == 0, (
        f"{jobb} kjører {skript}.py med "
        f"{', '.join(pakker) or 'bare standardbiblioteket'}, og importen "
        f"feiler der:\n{r.stderr}")


# kystvakt-1 kjører kystvakt/*.py fra /opt/kystvakt med /usr/bin/python3
# (3.14.4) og ingen pakker, og bare kystvakt-filene ligger der. Til fase 3
# av 3.14-overgangen holdt kodrepoets test.yml dette med en egen jobb der
# bare pytest var installert.
@pytest.mark.skipif(sys.version_info < (3, 14),
                    reason="kystvakt-1 kjører 3.14; compression.zstd finnes først der")
def test_kystvakt_skriptene_importeres_med_standardbiblioteket():
    feil = {}
    for p in sorted((ROT / "kystvakt").glob("*.py")):
        r = importer(p.stem, rot=ROT / "kystvakt")
        if r.returncode:
            feil[p.name] = r.stderr.strip().splitlines()[-1]
    assert not feil, feil


def test_sperren_stopper_det_jobben_ikke_har():
    """Feil med vilje: polars er installert der prøvene kjører. Slipper
    sperren den gjennom, prøver prøvene over ingenting."""
    r = importer("polars")
    assert r.returncode != 0
    assert "No module named 'polars'" in r.stderr


def test_sperren_slipper_det_jobben_har():
    assert importer("yaml").returncode != 0
    r = importer("yaml", TOPPNAVN["PyYAML"])
    assert r.returncode == 0, r.stderr


def _jobber_uten_requirements(mappe: Path) -> dict:
    """Det tabellen over påstår, lest av workflowene: hver jobb som henter
    kodrepoet uten å installere requirements.txt."""
    ut = {}
    for fil in sorted(mappe.glob("*.yml")):
        for navn, jobb in (yaml.safe_load(fil.read_text()).get("jobs") or {}).items():
            steg = jobb.get("steps") or []
            kode = next((s["with"].get("path", ".") for s in steg
                         if str(s.get("uses", "")).startswith("actions/checkout")
                         and (s.get("with") or {}).get("repository") == KODREPO), None)
            if kode is None:
                continue
            alltid, av_og_til, skript, requirements = set(), set(), set(), False
            for s in steg:
                kjor = s.get("run") or ""
                for m in re.finditer(r"\bpip install ([^\n]+)", kjor):
                    ordene = m.group(1).split()
                    requirements |= "-r" in ordene
                    pakker = {re.split(r"[=<>~!]", o)[0] for o in ordene
                              if not o.startswith("-")}
                    (av_og_til if s.get("if") else alltid).update(pakker)
                for m in re.finditer(r"\bpython3?\s+([\w./-]+)\.py\b", kjor):
                    sti = m.group(1)
                    if sti.startswith(f"{kode}/"):
                        skript.add(sti[len(kode) + 1:])
                    elif s.get("working-directory") == kode and "/" not in sti:
                        skript.add(sti)
            if not requirements:
                ut[f"{fil.name}:{navn}"] = (tuple(sorted(alltid)),
                                            tuple(sorted(av_og_til)),
                                            tuple(sorted(skript)))
    return ut


@pytest.mark.skipif(not WORKFLOWS.is_dir(),
                    reason="datarepoets workflows står ikke ved siden av kodrepoet")
def test_tabellen_er_workflowene():
    assert _jobber_uten_requirements(WORKFLOWS) == JOBBER
