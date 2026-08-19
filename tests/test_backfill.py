"""Backfill-loopen. Ingen nett — hent_uke er byttet ut.

Poenget med disse testene er ikke å teste henting, men å teste hva som
skjer når en uke feiler midt i 730.
"""

import datetime as dt

import pytest

import backfill
from core import raw as raw_arkiv, snapshot
from core.contract import Observation, Source


class FalskLusetall(Source):
    """Svarer på hent_uke(). `feiler` er uker som skal kaste."""

    name = "lusetall"
    entity_type = "lokalitet"

    def __init__(self, feiler=(), tomme=()):
        self.feiler = set(feiler)
        self.tomme = set(tomme)
        self.hentet = []

    def hent_uke(self, aar, uke, client=None):
        self.hentet.append((aar, uke))
        if (aar, uke) in self.feiler:
            raise RuntimeError(f"503 fra tjenesten (uke {uke})")
        return {"year": aar, "week": uke,
                "localities": [] if (aar, uke) in self.tomme else [
                    {"localityNo": 10029, "name": "X", "avgAdultFemaleLice": 0.2,
                     "hasReportedLice": True, "isFallow": False},
                ]}

    def parse(self, raw, observed_at):
        for lok in raw.get("localities", []):
            yield Observation(
                entity_id=str(lok["localityNo"]), entity_type=self.entity_type,
                entity_name="", field="voksne_hunnlus",
                value=str(lok["avgAdultFemaleLice"]), source=self.name,
                observed_at=observed_at,
            )


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(backfill.snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(backfill.changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(backfill.time, "sleep", lambda s: None)
    return tmp_path


def _kjor(monkeypatch, kilde, fra, til, ekstra=()):
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr(backfill, "_ferskeste_tillatte", lambda k: (2026, 30))
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "lusetall",
                                     "--fra", fra, "--til", til,
                                     "--pause", "0", *ekstra])
    return backfill.main()


def test_uke_som_feiler_stopper_ikke_resten(isolert, monkeypatch, capsys):
    """continue, ikke break. Å avbryte på uke 300 av 730 fordi én uke
    feilet er å kaste alt som allerede lyktes."""
    kilde = FalskLusetall(feiler={(2026, 2)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-04")

    # Alle fire uker ble forsøkt, ikke bare de to første.
    assert kilde.hentet == [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    assert kode == 1

    ut = capsys.readouterr().out
    assert "3 uker skrevet" in ut


def test_feillista_skrives_ut_og_gir_exit_1(isolert, monkeypatch, capsys):
    kilde = FalskLusetall(feiler={(2026, 2), (2026, 4)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-05")
    ut = capsys.readouterr().out

    assert kode == 1
    assert "2 uke(r) FEILET" in ut
    assert "uke  2/2026" in ut and "uke  4/2026" in ut
    assert "503 fra tjenesten" in ut
    # Hullene skal kunne lukkes uten å regne dem ut for hånd.
    assert "Kjør samme intervall på nytt" in ut


def test_uten_feil_er_exit_0(isolert, monkeypatch, capsys):
    kilde = FalskLusetall()

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-03")

    assert kode == 0
    assert "FEILET" not in capsys.readouterr().out


def test_gjenopptakelse_henter_bare_de_som_mangler(isolert, monkeypatch, capsys):
    """Feillista er bare nyttig hvis en ny kjøring faktisk lukker hullene."""
    forste = FalskLusetall(feiler={(2026, 2)})
    assert _kjor(monkeypatch, forste, "2026-01", "2026-04") == 1
    capsys.readouterr()

    andre = FalskLusetall()
    assert _kjor(monkeypatch, andre, "2026-01", "2026-04") == 0

    # Bare uka som manglet ble hentet på nytt.
    assert andre.hentet == [(2026, 2)]
    assert "1 uker skrevet, 3 hoppet over" in capsys.readouterr().out


def test_tom_uke_stopper_fortsatt(isolert, monkeypatch, capsys):
    """En tom uke betyr at året ikke finnes. Da er alt eldre også tomt,
    og å fortsette er å brenne kall på ingenting."""
    kilde = FalskLusetall(tomme={(2026, 3)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-05")

    assert kode == 1
    assert kilde.hentet == [(2026, 1), (2026, 2), (2026, 3)]   # stoppet
    assert "Stoppet:" in capsys.readouterr().out
