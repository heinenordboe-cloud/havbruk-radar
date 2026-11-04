"""kystvakt/gjenopprett.py: én tilfeldig fil tilbake fra boksen, holdt mot manifestet."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kystvakt"))
import gjenopprett  # noqa: E402
import kopi  # noqa: E402

sys.path.pop(0)

DATO = "2026-10-28"
FIL = f"{DATO}T16Z.txt.zst"
INNHOLD = b"!AIVDM,1,1,,A,13u?etPv2;0n:dDPwUM1U1Cb069D,0*24\n"
SUM = hashlib.sha256(INNHOLD).hexdigest()


@pytest.fixture
def oppsett(tmp_path, monkeypatch):
    """/srv med én bekreftet bw-fil, og en «boks» som er en mappe."""
    srv, boks = tmp_path / "srv", tmp_path / "boks"
    monkeypatch.setattr(kopi, "SRV", srv)
    dag = srv / "ais/bw" / DATO
    dag.mkdir(parents=True)
    (dag / "SHA256SUMS").write_text(f"{SUM}  {FIL}\n")
    kv = srv / "ais/kopi"
    (kv / "ais/bw").mkdir(parents=True)
    (kv / "ais/bw" / f"{DATO}.bekreftet").write_text(f"{SUM}  {FIL}\n")
    (boks / "ais/bw" / DATO).mkdir(parents=True)
    (boks / "ais/bw" / DATO / FIL).write_bytes(INNHOLD)

    def hent(rel, mappe):
        if not (boks / rel).exists():
            raise subprocess.CalledProcessError(23, ["rsync"], "", "No such file")
        return Path(shutil.copy(boks / rel, mappe))

    monkeypatch.setattr(gjenopprett, "hent", hent)
    return srv, kv, boks


def test_fila_fra_boksen_er_lik_manifestet(oppsett):
    srv, kv, _ = oppsett
    assert gjenopprett.main([str(kv), str(srv / "ais/bw")]) == 0
    r = json.loads((kv / gjenopprett.RESULTAT).read_text())
    assert r["ok"] is True and r["kilde"] == "bw" and r["dato"] == DATO and r["fil"] == FIL
    assert r["sha256"] == r["manifest"] == SUM and r["bytes"] == len(INNHOLD)


def test_endrede_bytes_paa_boksen_er_en_feil(oppsett):
    srv, kv, boks = oppsett
    (boks / "ais/bw" / DATO / FIL).write_bytes(INNHOLD + b"x")
    assert gjenopprett.main([str(kv), str(srv / "ais/bw")]) == 1
    r = json.loads((kv / gjenopprett.RESULTAT).read_text())
    assert r["ok"] is False and "manifestets linje" in r["grunn"]


def test_en_fil_boksen_ikke_leverer_er_en_feil(oppsett):
    srv, kv, boks = oppsett
    (boks / "ais/bw" / DATO / FIL).unlink()
    assert gjenopprett.main([str(kv), str(srv / "ais/bw")]) == 1
    r = json.loads((kv / gjenopprett.RESULTAT).read_text())
    assert r["ok"] is False and "leverte ikke" in r["grunn"]


def test_bare_bekreftede_filer_med_samme_sum_trekkes(oppsett):
    """En fil som står i manifestet, men ikke er bekreftet (eller er
    bekreftet med en annen sum), er ikke en backup å prøve."""
    srv, kv, _ = oppsett
    (srv / "ais/bw" / DATO / "SHA256SUMS").write_text(
        f"{SUM}  {FIL}\n{'c' * 64}  {DATO}T17Z.txt.zst\n")
    assert gjenopprett.kandidater(kv, srv / "ais/bw") == [(DATO, FIL, SUM)]
    (kv / "ais/bw" / f"{DATO}.bekreftet").write_text(f"{'d' * 64}  {FIL}\n")
    assert gjenopprett.kandidater(kv, srv / "ais/bw") == []
    assert gjenopprett.main([str(kv), str(srv / "ais/bw")]) == 1
    assert "ingen bekreftet" in json.loads((kv / gjenopprett.RESULTAT).read_text())["grunn"]


def test_feilen_med_vilje_gaar_til_ut_og_ikke_til_maanedens_resultat(oppsett, tmp_path):
    srv, kv, _ = oppsett
    ut = tmp_path / "med-vilje.json"
    assert gjenopprett.main(["--forvent", "0" * 64, "--ut", str(ut),
                             str(kv), str(srv / "ais/bw")]) == 1
    r = json.loads(ut.read_text())
    assert r["ok"] is False and "--forvent" in r["grunn"] and r["sha256"] == SUM
    assert not (kv / gjenopprett.RESULTAT).exists()
    # Uten --ut nekter den: en prøve med vilje skal ikke stå som resultatet.
    assert gjenopprett.main(["--forvent", "0" * 64, str(kv), str(srv / "ais/bw")]) == 2
    assert not (kv / gjenopprett.RESULTAT).exists()
