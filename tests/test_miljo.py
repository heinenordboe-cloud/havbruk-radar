"""Kreves en nøkkel av en aktiv kilde, skal kjøringen dø FØR innsamlingen.

F8, 24.08.2026: `samle.yml` eksponerte BARENTSWATCH_CLIENT_ID og
-SECRET, men secretsene fantes ikke i datarepoet. Lokalt lå de i skallet,
backfillen kjørte lokalt, og lørdagens test-dispatch hoppet over lusetall
via `finnes_allerede()`. Første kjøring som faktisk kalte `fetch()` var
mandagens cron. Feilklassen er «virker lokalt fordi skallet har det»,
og den kan bare fanges av noe som spør på forhånd.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from core import miljo

ROT = Path(__file__).resolve().parent.parent

NOKLER = ("BARENTSWATCH_CLIENT_ID", "BARENTSWATCH_CLIENT_SECRET")


class Kilde:
    """Kildens navn er alt sjekken trenger — den slår opp i config.yml
    på `kilder.<navn>`, ikke i kildekoden."""

    def __init__(self, navn):
        self.name = navn


@pytest.fixture
def fersk_config():
    """config.load() er lru_cache'et. Uten tømming både før og etter ser
    testen configen en tidligere testfil lastet, med de miljøvariablene
    DEN hadde."""
    from core import config

    config.load.cache_clear()
    yield config
    config.load.cache_clear()


@pytest.fixture
def uten_nokler(monkeypatch):
    for navn in NOKLER:
        monkeypatch.delenv(navn, raising=False)


# ---- selve sjekken -----------------------------------------------------


def test_navngir_alle_manglende_samlet(uten_nokler, fersk_config):
    """Begge nøklene i ett svar. Én om gangen ville med ukentlig cron
    blitt én rød uke per nøkkel."""
    funn = miljo.manglende([Kilde("lusetall")])

    assert set(funn) == set(NOKLER)
    assert funn["BARENTSWATCH_CLIENT_ID"] == ["kilder.lusetall.client_id"]
    assert funn["BARENTSWATCH_CLIENT_SECRET"] == ["kilder.lusetall.client_secret"]


def test_melding_nevner_hver_variabel_og_hvor_den_kreves(uten_nokler, fersk_config):
    tekst = miljo.forklar(miljo.manglende([Kilde("lusetall")]))

    for navn in NOKLER:
        assert navn in tekst
    assert "kilder.lusetall.client_id" in tekst
    assert "kilder.lusetall.client_secret" in tekst
    # Feilen satt i to ledd. Meldingen må nevne begge, ellers sjekker du
    # bare det ene og tror du er ferdig.
    assert "secret" in tekst.lower()
    assert "samle.yml" in tekst


def test_en_satt_en_mangler_gir_bare_den_manglende(monkeypatch, fersk_config):
    monkeypatch.setenv("BARENTSWATCH_CLIENT_ID", "satt")
    monkeypatch.delenv("BARENTSWATCH_CLIENT_SECRET", raising=False)

    assert set(miljo.manglende([Kilde("lusetall")])) == {
        "BARENTSWATCH_CLIENT_SECRET"
    }


def test_alt_satt_gir_ingen_funn(monkeypatch, fersk_config):
    for navn in NOKLER:
        monkeypatch.setenv(navn, "satt")

    assert miljo.manglende([Kilde("lusetall")]) == {}


def test_tom_streng_teller_som_ikke_satt(monkeypatch, fersk_config):
    """`${{ secrets.X }}` på en secret som ikke finnes blir TOM STRENG,
    ikke en manglende variabel. Det var nøyaktig tilstanden i CI 24.08:
    env-blokka satte variabelen, verdien var tom. En sjekk som bare spør
    om variabelen finnes, hadde sagt god for kjøringen."""
    for navn in NOKLER:
        monkeypatch.setenv(navn, "")

    assert set(miljo.manglende([Kilde("lusetall")])) == set(NOKLER)


def test_kilder_som_ikke_er_aktive_teller_ikke(uten_nokler, fersk_config):
    """Lista kommer fra registry.discover(), som bare gir aktive kilder.
    Er lusetall slått av, skal ikke nøkkelen felle Enhetsregisteret."""
    assert miljo.manglende([Kilde("enhetsregisteret")]) == {}
    assert miljo.manglende([]) == {}


def test_ukjent_kildenavn_krasjer_ikke(uten_nokler, fersk_config):
    """En kilde uten egen blokk i config.yml er lovlig."""
    assert miljo.manglende([Kilde("finnes_ikke_i_config")]) == {}


def test_to_variabler_i_samme_streng_fanges_begge(monkeypatch, fersk_config):
    """`config.get()` navngir bare den FØRSTE markøren i en streng, fordi
    den skal nevne én variabel i én feilmelding. Denne skal nevne alle —
    ellers arver den begrensningen den finnes for å rette opp."""
    from core import config

    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.delenv("B_KEY", raising=False)
    # Bare miljo.load byttes, ikke config.load: `from core.config import
    # load` gjør navnet til miljos eget, og en patch på config-modulen
    # ville dessuten overlevd fersk_config sin cache_clear i teardown.
    monkeypatch.setattr(
        miljo, "load",
        lambda: config._expander({"kilder": {"x": {"url": "${A_KEY}:${B_KEY}"}}}),
    )

    funn = miljo.manglende([Kilde("x")])
    assert set(funn) == {"A_KEY", "B_KEY"}


def test_variabel_utenfor_kilder_blokka_kreves_uansett(monkeypatch, fersk_config):
    """Det finnes ingen global nøkkel i dag. Sjekken dekker den likevel,
    fordi en global nøkkel ellers ville vært den ene tingen som slapp
    unna — og det er nøyaktig feilklassen dette er bygget mot."""
    from core import config

    monkeypatch.delenv("GLOBAL_KEY", raising=False)
    monkeypatch.setattr(
        miljo, "load",
        lambda: config._expander({"felles": {"token": "${GLOBAL_KEY}"},
                                  "kilder": {}}),
    )

    assert set(miljo.manglende([])) == {"GLOBAL_KEY"}


# ---- at run.py faktisk stopper ----------------------------------------


def test_run_py_stopper_for_innsamlingen(uten_nokler):
    """Ikke bare at sjekken svarer riktig — at kjøringen faktisk dør på
    den, og dør FØR den har brukt tid på nett.

    Egen prosess med vilje: det er `python run.py` i workflowen som er
    påstanden, og en importert main() ville arvet dette testmiljøets
    allerede lastede config-cache.
    """
    with tempfile.TemporaryDirectory(prefix="havbruk-miljotest-") as tmp:
        env = {k: v for k, v in os.environ.items() if k not in NOKLER}
        env["HAVBRUK_DATA_DIR"] = tmp

        resultat = subprocess.run(
            [sys.executable, str(ROT / "run.py")],
            capture_output=True, text=True, timeout=60, env=env, cwd=str(ROT),
        )

        assert resultat.returncode == 1, resultat.stdout + resultat.stderr

        ut = resultat.stdout
        for navn in NOKLER:
            assert navn in ut, ut
        assert "::error::" in ut

        # Beviset for at den stoppet TIDLIG: ingen kilde rakk å levere,
        # ingenting ble skrevet, og datamappa er urørt.
        assert "observasjoner" not in ut, ut
        assert "snapshot skrevet" not in ut, ut
        assert list(Path(tmp).iterdir()) == []


def test_run_py_stopper_ogsa_nar_kilden_ville_blitt_hoppet_over(uten_nokler):
    """Kjernen i F8. Lørdagens dispatch gikk grønt fordi lusetall ble
    hoppet over av `finnes_allerede()` — feilen fantes, men ingen kjøring
    rørte den. `--bare lusetall` med `--tving` ville uansett stoppet;
    poenget her er at den stopper UTEN --tving, altså på den veien der
    frekvensvakten ellers hadde fått lov til å skjule den."""
    with tempfile.TemporaryDirectory(prefix="havbruk-miljotest-") as tmp:
        env = {k: v for k, v in os.environ.items() if k not in NOKLER}
        env["HAVBRUK_DATA_DIR"] = tmp

        resultat = subprocess.run(
            [sys.executable, str(ROT / "run.py"), "--bare", "lusetall"],
            capture_output=True, text=True, timeout=60, env=env, cwd=str(ROT),
        )

        assert resultat.returncode == 1, resultat.stdout + resultat.stderr
        assert "BARENTSWATCH_CLIENT_ID" in resultat.stdout
        # Ikke «hentet i dag, går hver 7. dag» — sjekken skal ligge foran
        # frekvensvakten, ikke bak den.
        assert "[vent]" not in resultat.stdout, resultat.stdout
        assert "[har]" not in resultat.stdout, resultat.stdout
