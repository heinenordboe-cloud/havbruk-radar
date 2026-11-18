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


# Ukejobben slik den står i datarepoets jobber.yml (anslag.yml, økt 14a).
UKEJOBB = {"skriver": ["predictions/maskin"], "feilprove": None,
           "stillhet": {"maks_dogn": 1, "maales": "ukefil", "fra": "2026-11-23"}}


def test_groenne_torrkjoringer_er_ikke_krav_1_for_ukejobben():
    """18.11.2026 hadde anslag.yml to grønne kjøringer, begge tørrkjøringer,
    og kontrollen sa «mangler 3». Et forsøk er ikke et resultat: krav 1 er
    en uke jobben selv har forseglet, og raden skal si hva som ikke er prøvd."""
    ut = ferdig.workflows({"anslag.yml": UKEJOBB}, {},
                          kall=lambda repo, fil: 2, uker=lambda mappe: [])
    assert "mangler 1, 3" in ut[0]
    assert "1 mangler: stemplingen, commiten og pushen er ikke prøvd i Actions" in ut[0]
    assert "2 grønne kjøringer, ingen ukefil fra jobben; første uke er 2026-11-23" in ut[0]
    assert "vellykkede i Actions" not in ut[0]
    assert "jobber.yml 1 døgn (ukefil)" in ut[0]


def test_en_uke_jobben_har_forseglet_er_krav_1():
    sett = []
    ut = ferdig.workflows({"anslag.yml": UKEJOBB}, {}, kall=lambda repo, fil: 3,
                          uker=lambda mappe: sett.append(mappe) or ["2026-48.yml", "2026-49.yml"])
    assert sett == ["predictions/maskin"]
    assert "mangler 3 " in ut[0] and "1 mangler" not in ut[0]
    assert "1 2 uke(r) forseglet av jobben i Actions, sist 2026-49.yml" in ut[0]


def test_uten_historikken_er_krav_1_ikke_oppfylt():
    """Kan kontrollen ikke lese om jobben har forseglet noe, er ikke det et
    argument for å si at den har."""
    for uker in (None, lambda mappe: None):
        ut = ferdig.workflows({"anslag.yml": UKEJOBB}, {}, kall=lambda repo, fil: None, uker=uker)
        assert "mangler 1, 3" in ut[0]
        assert "datarepoets historikk kunne ikke leses (ukjent antall grønne kjøringer" in ut[0]


def test_andre_jobber_maales_som_foer():
    jobber = {"a.yml": {"stillhet": {"maks_dogn": 2, "maales": "commit"}, "feilprove": None}}
    ut = ferdig.workflows(jobber, {}, kall=lambda repo, fil: 3,
                          uker=lambda mappe: 1 / 0)       # skal ikke spørres
    assert "mangler 3" in ut[0] and "1 3 vellykkede i Actions" in ut[0]


def _commit(repo: Path, sti: str, hvem: str) -> None:
    import subprocess
    (repo / sti).parent.mkdir(parents=True, exist_ok=True)
    (repo / sti).write_text("x")
    git = ["git", "-C", str(repo), "-c", f"user.name={hvem}", "-c", "user.email=a@b"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", sti], check=True)


def test_bare_jobbens_egne_stempler_teller(tmp_path):
    """En uke forseglet for hånd fra Mac-en viser at verktøyet virker lokalt,
    ikke at jobben har stemplet, committet og pushet i Actions. En ukefil
    uten stempel og en .komplett.ots teller heller ikke."""
    import subprocess
    assert ferdig.forseglet_av_jobben(tmp_path, "predictions/maskin") is None
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    m = "predictions/maskin"
    _commit(tmp_path, f"{m}/fasiten.json", "havbruk-radar")
    _commit(tmp_path, f"{m}/2026-48.yml", "Heine Nordboe")
    _commit(tmp_path, f"{m}/2026-48.yml.ots", "Heine Nordboe")
    _commit(tmp_path, f"{m}/2026-49.yml", "havbruk-radar")
    assert ferdig.forseglet_av_jobben(tmp_path, m) == []
    _commit(tmp_path, f"{m}/2026-49.yml.ots", "havbruk-radar")
    _commit(tmp_path, f"{m}/2026-48.yml.komplett.ots", "havbruk-radar")
    _commit(tmp_path, f"{m}/2027-01.yml.ots", "havbruk-radar")
    assert ferdig.forseglet_av_jobben(tmp_path, m) == ["2026-49.yml", "2027-01.yml"]


def test_en_tjeneste_som_ikke_er_aktiv_har_ikke_kjort():
    status = {"skrevet": "2026-11-04T04:17:04Z", "tjenester": {
        "ais-bw.service": {"tilstand": "active", "resultat": "success"},
        "ais-5632.service": {"tilstand": "failed", "resultat": "exit-code"}}}
    ut = ferdig.tjenester(FERDIG, status)
    assert "ferdig" in ut[0]
    assert "mangler 1, 3" in ut[1]
    assert all("mangler 1" in linje for linje in ferdig.tjenester(FERDIG, None))
