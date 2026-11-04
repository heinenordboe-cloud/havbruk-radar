"""verktoy/ferdig.py: hvilke av de tre kravene i CLAUDE.md §8 som mangler."""
import sys
from pathlib import Path

import yaml

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "verktoy"))
sys.path.insert(0, str(ROT / "kystvakt"))
import ferdig  # noqa: E402
import utlevering  # noqa: E402

sys.path.pop(0)
sys.path.pop(0)

FERDIG = yaml.safe_load(ferdig.FERDIG.read_text(encoding="utf-8"))


def test_tjenestene_er_de_utleveringen_melder():
    """En enhet lyttere.sh slår på, men som ikke står her, ville aldri
    blitt spurt om de tre kravene."""
    assert list(FERDIG["tjenester"]) == list(utlevering.TJENESTER)


def test_hver_post_har_frist_og_feilprove():
    for gruppe in ("tjenester", "prover"):
        for navn, f in FERDIG[gruppe].items():
            assert set(f) >= {"frist", "feilprove"}, navn


def test_raden_sier_hvilke_krav_som_mangler():
    assert "ferdig" in ferdig.rad("x.yml", "1 vellykket", "jobber.yml 2 døgn", "2026-11-04: a; b")
    assert "mangler 1, 3" in ferdig.rad("x.yml", None, "jobber.yml 2 døgn", None)
    assert "mangler 1, 2, 3" in ferdig.rad("x.yml", None, None, None)


def test_workflows_leser_stillhet_healthchecks_og_kjoringene():
    jobber = {"a.yml": {"stillhet": {"maks_dogn": 2, "maales": "commit"}, "feilprove": None},
              "b.yml": {"stillhet": None, "feilprove": None},
              "c.yml": {"stillhet": None, "feilprove": "2026-11-04: x; y"}}
    ut = ferdig.workflows(jobber, {"c.yml": "Healthchecks «c»"},
                          kall=lambda repo, fil: {"a.yml": 3, "c.yml": 1}.get(fil, 0))
    assert "mangler 3" in ut[0] and "jobber.yml 2 døgn (commit)" in ut[0]
    assert "mangler 1, 2, 3" in ut[1]
    assert "ferdig" in ut[2] and "Healthchecks «c»" in ut[2]


def test_en_tjeneste_som_ikke_er_aktiv_har_ikke_kjort():
    status = {"skrevet": "2026-11-04T04:17:04Z", "tjenester": {
        "ais-bw.service": {"tilstand": "active", "resultat": "success"},
        "ais-5632.service": {"tilstand": "failed", "resultat": "exit-code"}}}
    ut = ferdig.tjenester(FERDIG, status)
    assert "ferdig" in ut[0]
    assert "mangler 1, 3" in ut[1]
    assert all("mangler 1" in linje for linje in ferdig.tjenester(FERDIG, None))
