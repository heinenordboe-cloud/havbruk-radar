"""Gjør det umulig for testene å skrive til den ekte datamappa.

core/paths.py leser HAVBRUK_DATA_DIR ved import og regner ut
DATA_DIR/RAW_DIR/ARKIV_DIR/... én gang. Andre moduler importerer disse
verdiene ved navn (`from core.paths import ARKIV_DIR`), så en
monkeypatch.setenv() i en fixture kommer for sent — importen har
allerede skjedd før noen fixture rekker å kjøre.

Denne fila kjører før pytest importerer noe testmodul i det hele tatt,
så miljøvariabelen er satt til en engangsmappe før core.paths (eller
noe som importerer den) leses for første gang. Per-test-isolasjon
(monkeypatch.setattr på RAW_DIR/ARKIV_DIR i enkelttester) kommer i
tillegg — denne fila er sikkerhetsnettet for testene som glemmer det.
"""

import atexit
import os
import shutil
import tempfile

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="havbruk-radar-tester-")
os.environ["HAVBRUK_DATA_DIR"] = _TEST_DATA_DIR
atexit.register(shutil.rmtree, _TEST_DATA_DIR, ignore_errors=True)


# ---------------------------------------------------------- kodeproveniens
#
# `snapshot.write()` stempler hvilken commit som skrev fila, og om
# arbeidstreet var rent — se core/kodeproveniens.py. Begge deler leses
# av `git`, og da avhenger testene av utviklerens arbeidstre: den samme
# testen ville vært grønn med rent tre og rød med urent.
#
# Det er samme problem denne fila løser for datamappa, og løsningen er
# den samme: testene får sitt eget, faste svar. Den ekte oppførselen
# prøves av testene som selv setter verdiene.

import pytest


@pytest.fixture(autouse=True)
def _fast_kodeproveniens(monkeypatch):
    from core import kodeproveniens

    monkeypatch.setattr(kodeproveniens, "commit", lambda: "0" * 40)
    monkeypatch.setattr(kodeproveniens, "rent", lambda: kodeproveniens.RENT)
    monkeypatch.setattr(kodeproveniens, "paa_origin_main",
                        lambda sha: (bool(sha), "testfast"))
