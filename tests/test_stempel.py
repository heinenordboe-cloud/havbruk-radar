"""stempel.py: manifest for nye filer, stempel, og oppgradering av en kopi.

Ingen nettverk: `ots`-klienten byttes ut med en som skriver det den
ekte ville skrevet. Repoene er ekte git-repoer i tmp, så manifestet bygges
av det git kjenner.
"""

import hashlib
import os
import re
import subprocess
from pathlib import Path

import pytest

import stempel


def _git(repo: Path, *args: str) -> None:
    miljo = dict(os.environ, GIT_AUTHOR_NAME="x", GIT_AUTHOR_EMAIL="x@x",
                 GIT_COMMITTER_NAME="x", GIT_COMMITTER_EMAIL="x@x")
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=miljo,
                   capture_output=True)


def _skriv(repo: Path, sti: str, innhold: bytes) -> None:
    (repo / sti).parent.mkdir(parents=True, exist_ok=True)
    (repo / sti).write_bytes(innhold)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", sti)


class FalskOts:
    """Skriver det `ots` skriver. `komplett` styrer hva upgrade svarer."""

    def __init__(self):
        self.komplett = False
        self.stamp_feiler = False
        self.kall = []

    def __call__(self, *args):
        self.kall.append(args)
        handling, fil = args[0], Path(args[1])
        if handling == "stamp":
            if self.stamp_feiler:
                return subprocess.CompletedProcess(args, 1, "", "kalender nede")
            Path(f"{fil}.ots").write_bytes(b"VENTER")
            return subprocess.CompletedProcess(args, 0, "", "")
        if handling == "upgrade":
            if not self.komplett:
                return subprocess.CompletedProcess(
                    args, 1, "", "Failed! Timestamp not complete\n")
            fil.rename(Path(f"{fil}.bak"))
            fil.write_bytes(b"KOMPLETT")
            return subprocess.CompletedProcess(
                args, 0, "", "Success! Timestamp complete\n")
        raise AssertionError(args)


@pytest.fixture
def repoer(tmp_path, monkeypatch):
    data_repo, kode = tmp_path / "mappe-paa-runneren", tmp_path / "kode"
    for r in (data_repo, kode):
        r.mkdir()
        _git(r, "init", "-q")
    _skriv(data_repo, "data/arkiv/eierskap/2026-10-12.json.gz", b"kropp")
    _skriv(data_repo, "data/raw/eierskap/2026-10-12.parquet", b"rader")
    _skriv(data_repo, "data/health.json", b"{}")
    _skriv(kode, "predictions/2026-08-18.yml", b"anslag")
    monkeypatch.setattr(stempel, "DATA", data_repo / "data")
    monkeypatch.setattr(stempel, "DATAREPO", data_repo)
    monkeypatch.setattr(stempel, "KODEREPO", kode)
    monkeypatch.setattr(stempel, "STEMPEL_DIR", data_repo / "data" / "stempler")
    ots = FalskOts()
    monkeypatch.setattr(stempel, "ots", ots)
    return data_repo, kode, ots


def _linjer(sti: Path) -> list[tuple[str, str]]:
    return [tuple(l.split("  ", 1)) for l in sti.read_text().splitlines()
            if l and not l.startswith("#")]


def test_forste_manifest_har_hver_sporet_fil_og_begge_head(repoer):
    data_repo, kode, ots = repoer
    assert stempel.main(["--dato", "2026-10-13"]) == 0
    m = data_repo / "data" / "stempler" / "2026-10-13.manifest.txt"
    linjer = _linjer(m)
    assert [s for _, s in linjer] == [
        "havbruk-radar-data/data/arkiv/eierskap/2026-10-12.json.gz",
        "havbruk-radar-data/data/raw/eierskap/2026-10-12.parquet",
        "havbruk-radar/predictions/2026-08-18.yml",
    ]
    assert dict((s, h) for h, s in linjer)[
        "havbruk-radar/predictions/2026-08-18.yml"] == hashlib.sha256(b"anslag").hexdigest()
    tekst = m.read_text()
    for repo, navn in ((kode, "havbruk-radar"), (data_repo, "havbruk-radar-data")):
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        assert re.search(rf"^# HEAD  {re.escape(navn)}\s+{sha}$", tekst, re.M)
    assert Path(f"{m}.ots").read_bytes() == b"VENTER"


def test_health_json_og_ukjente_filer_er_ikke_med(repoer):
    data_repo, _, _ = repoer
    (data_repo / "data" / "arkiv" / "eierskap" / ".DS_Store").write_bytes(b"x")
    stempel.main(["--dato", "2026-10-13"])
    stier = [s for _, s in _linjer(data_repo / "data/stempler/2026-10-13.manifest.txt")]
    assert not any("health.json" in s or ".DS_Store" in s for s in stier)


def test_ingen_nye_filer_gir_intet_manifest(repoer):
    data_repo, _, _ = repoer
    stempel.main(["--dato", "2026-10-13"])
    _git(data_repo, "add", "-A")
    _git(data_repo, "commit", "-q", "-m", "stempel")
    stempel.main(["--dato", "2026-10-14"])
    assert sorted(p.name for p in (data_repo / "data/stempler").glob("*.txt")) == [
        "2026-10-13.manifest.txt"]


def test_neste_manifest_har_bare_det_nye(repoer):
    data_repo, kode, _ = repoer
    stempel.main(["--dato", "2026-10-13"])
    _skriv(data_repo, "data/arkiv/eierskap/2026-10-13.json.gz", b"ny kropp")
    _skriv(kode, "predictions/2026-08-18.yml", b"anslag med utfall")
    stempel.main(["--dato", "2026-10-13"])
    andre = data_repo / "data/stempler/2026-10-13.2.manifest.txt"
    assert [s for _, s in _linjer(andre)] == [
        "havbruk-radar-data/data/arkiv/eierskap/2026-10-13.json.gz",
        "havbruk-radar/predictions/2026-08-18.yml",
    ]


def test_en_arkivfil_med_nytt_innhold_faar_ny_linje(repoer):
    """Regel 2 sier at det ikke skal skje. Skjer det, står det i neste manifest."""
    data_repo, _, _ = repoer
    stempel.main(["--dato", "2026-10-13"])
    _skriv(data_repo, "data/arkiv/eierskap/2026-10-12.json.gz", b"omskrevet")
    stempel.main(["--dato", "2026-10-14"])
    [(sha, sti)] = _linjer(data_repo / "data/stempler/2026-10-14.manifest.txt")
    assert sti.endswith("2026-10-12.json.gz")
    assert sha == hashlib.sha256(b"omskrevet").hexdigest()


def test_oppgradering_skriver_komplett_og_rorer_ikke_originalen(repoer):
    data_repo, _, ots = repoer
    stempel.main(["--dato", "2026-10-13"])
    stempler = data_repo / "data" / "stempler"
    original = stempler / "2026-10-13.manifest.txt.ots"
    assert not (stempler / "2026-10-13.manifest.txt.komplett.ots").exists()

    ots.komplett = True
    stempel.main(["--dato", "2026-10-14"])
    assert original.read_bytes() == b"VENTER"
    assert (stempler / "2026-10-13.manifest.txt.komplett.ots").read_bytes() == b"KOMPLETT"
    assert not list(stempler.glob("*.bak"))

    # Og en komplett oppgraderes ikke på nytt.
    ots.kall.clear()
    stempel.main(["--dato", "2026-10-15"])
    assert not [k for k in ots.kall if k[0] == "upgrade"]


def test_stempel_som_feiler_er_rodt_og_tas_igjen_neste_gang(repoer, capsys):
    data_repo, _, ots = repoer
    ots.stamp_feiler = True
    assert stempel.main(["--dato", "2026-10-13"]) == 1
    m = data_repo / "data/stempler/2026-10-13.manifest.txt"
    assert m.exists() and not Path(f"{m}.ots").exists()
    assert "::error::ots stamp 2026-10-13.manifest.txt feilet" in capsys.readouterr().out

    ots.stamp_feiler = False
    assert stempel.main(["--dato", "2026-10-14"]) == 0
    assert Path(f"{m}.ots").exists()


def test_et_stempel_som_venter_for_lenge_gir_varsel(repoer, capsys):
    stempel.main(["--dato", "2026-10-13"])
    capsys.readouterr()
    stempel.main(["--dato", "2026-10-16"])
    assert "::warning::2026-10-13.manifest.txt.ots har ventet 3 døgn" \
        in capsys.readouterr().out


def test_torrkjoring_skriver_ingenting(repoer):
    data_repo, _, ots = repoer
    assert stempel.main(["--torrkjor", "--dato", "2026-10-13"]) == 0
    assert not (data_repo / "data" / "stempler").exists()
    assert not ots.kall
