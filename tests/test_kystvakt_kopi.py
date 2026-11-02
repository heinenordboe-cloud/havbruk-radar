"""kystvakt/kopi.py og rydd.py mot en «boks» som er en mappe i tmp."""
import hashlib
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kystvakt"))
import kopi  # noqa: E402
import rydd  # noqa: E402

sys.path.pop(0)


@pytest.fixture
def oppsett(tmp_path, monkeypatch):
    srv, boks, kv = tmp_path / "srv", tmp_path / "boks", tmp_path / "kv"
    boks.mkdir()
    kv.mkdir()
    monkeypatch.setattr(kopi, "SRV", srv)

    def rsync(relative, ignorer_eksisterende):
        for r in relative:
            mål = boks / r
            if ignorer_eksisterende and mål.exists():
                continue
            mål.parent.mkdir(parents=True, exist_ok=True)
            if mål.exists():
                mål.chmod(0o644)
            shutil.copy2(srv / r, mål)

    def fjern_sha256(relative):
        return {r: hashlib.sha256((boks / r).read_bytes()).hexdigest()
                for r in relative if (boks / r).exists()}

    monkeypatch.setattr(kopi, "rsync", rsync)
    monkeypatch.setattr(kopi, "fjern_sha256", fjern_sha256)
    return srv, boks, kv


def ferdig(dag: Path, navn: str, innhold: bytes) -> None:
    dag.mkdir(parents=True, exist_ok=True)
    (dag / navn).write_bytes(innhold)
    (dag / navn).chmod(0o444)
    with open(dag / "SHA256SUMS", "a") as m:
        m.write(f"{hashlib.sha256(innhold).hexdigest()}  {navn}\n")


def test_kopierer_ferdige_og_bekrefter(oppsett):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/2026-10-29"
    ferdig(dag, "2026-10-29T00Z.txt.zst", b"en")
    (dag / "2026-10-29T00Z.regnskap.json").write_text("{}")
    (dag / ".2026-10-29T01Z.delvis").write_bytes(b"halv")
    kopi.kopier_rot(srv / "ais/bw", kv)
    assert (boks / "ais/bw/2026-10-29/2026-10-29T00Z.txt.zst").read_bytes() == b"en"
    assert (boks / "ais/bw/2026-10-29/2026-10-29T00Z.regnskap.json").exists()
    assert (boks / "ais/bw/2026-10-29/SHA256SUMS").exists()
    assert not (boks / "ais/bw/2026-10-29/.2026-10-29T01Z.delvis").exists()
    linjer = (kv / "ais/bw/2026-10-29.bekreftet").read_text().splitlines()
    assert len(linjer) == 3

    # Ny time samme døgn: bare den nye og det voksne manifestet sendes.
    ferdig(dag, "2026-10-29T01Z.txt.zst", b"to")
    kopi.kopier_rot(srv / "ais/bw", kv)
    assert (boks / "ais/bw/2026-10-29/SHA256SUMS").read_bytes() == (dag / "SHA256SUMS").read_bytes()
    assert len((kv / "ais/bw/2026-10-29.bekreftet").read_text().splitlines()) == 5


def test_lokal_fil_ulik_manifestet_stopper(oppsett):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/2026-10-29"
    ferdig(dag, "2026-10-29T00Z.txt.zst", b"en")
    (dag / "2026-10-29T00Z.txt.zst").chmod(0o644)
    (dag / "2026-10-29T00Z.txt.zst").write_bytes(b"odelagt")
    with pytest.raises(kopi.Stopp, match="manifestets"):
        kopi.kopier_rot(srv / "ais/bw", kv)
    assert not (kv / "ais/bw/2026-10-29.bekreftet").exists()
    assert not (boks / "ais/bw/2026-10-29/2026-10-29T00Z.txt.zst").exists()


def test_boksen_har_en_annen_fil_stopper(oppsett):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/2026-10-29"
    ferdig(dag, "2026-10-29T00Z.txt.zst", b"en")
    (boks / "ais/bw/2026-10-29").mkdir(parents=True)
    (boks / "ais/bw/2026-10-29/2026-10-29T00Z.txt.zst").write_bytes(b"halv")
    with pytest.raises(kopi.Stopp, match="boksen sier"):
        kopi.kopier_rot(srv / "ais/bw", kv)
    assert not (kv / "ais/bw/2026-10-29.bekreftet").exists()


def test_main_stopper_med_exit_1_og_uten_sist_ok(oppsett, monkeypatch):
    srv, boks, kv = oppsett
    ferdig(srv / "ais/bw/2026-10-29", "a.txt.zst", b"en")
    monkeypatch.setattr(kopi, "fjern_sha256", lambda rel: {})
    monkeypatch.setattr(sys, "argv", ["kopi.py", str(kv), str(srv / "ais/bw")])
    with pytest.raises(SystemExit) as e:
        kopi.main()
    assert e.value.code == 1
    assert not (kv / "SIST_OK").exists()


def gammel(sti: Path, dager: float) -> None:
    t = time.time() - dager * 86400
    os.utime(sti, (t, t))


def test_rydd_sletter_bare_det_boksen_har(oppsett):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/2026-10-10"
    for n in ("a.txt.zst", "b.txt.zst", "c.txt.zst"):
        ferdig(dag, n, n.encode())
    (dag / "a.regnskap.json").write_text("{}")
    kopi.kopier_rot(srv / "ais/bw", kv)
    (boks / "ais/bw/2026-10-10/b.txt.zst").unlink()      # mangler på boksen
    for n in ("a.txt.zst", "b.txt.zst", "a.regnskap.json"):
        gammel(dag / n, 15)                               # c er ung
    slettet, beholdt = rydd.rydd_rot(srv / "ais/bw", 14, time.time())
    assert (slettet, beholdt) == (1, 1)
    assert not (dag / "a.txt.zst").exists()
    assert (dag / "b.txt.zst").exists() and (dag / "c.txt.zst").exists()
    assert (dag / "a.regnskap.json").exists() and (dag / "SHA256SUMS").exists()

    # Kopien neste natt godtar at a er borte lokalt. At boksen har mistet
    # en fil den bekreftet, ser bare ryddingen, og den sier fra hver natt
    # (exit 1) uten å slette, til noen har sett på det.
    kopi.kopier_rot(srv / "ais/bw", kv)
    assert rydd.rydd_rot(srv / "ais/bw", 14, time.time()) == (0, 1)
    assert (dag / "b.txt.zst").exists()


def test_rydd_dekker_etterhentet(oppsett):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/etterhentet/2026-10-14"
    ferdig(dag, "2026-10-14T21Z--2026-10-15T21Z.etterhentet.jsonl.zst", b"hull")
    kopi.kopier_rot(srv / "ais/bw/etterhentet", kv)
    gammel(dag / "2026-10-14T21Z--2026-10-15T21Z.etterhentet.jsonl.zst", 20)
    assert rydd.rydd_rot(srv / "ais/bw/etterhentet", 14, time.time()) == (1, 0)


def test_rydd_maaler_vaar_mtime_ikke_mappedatoen(oppsett):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/etterhentet/2026-10-01"           # gammel dato, hentet nå
    ferdig(dag, "x.etterhentet.jsonl.zst", b"hull")
    kopi.kopier_rot(srv / "ais/bw/etterhentet", kv)
    assert rydd.rydd_rot(srv / "ais/bw/etterhentet", 14, time.time()) == (0, 0)


def test_rydd_torrkjor_sletter_ingenting(oppsett, monkeypatch):
    srv, boks, kv = oppsett
    dag = srv / "ais/bw/2026-10-10"
    for n in ("a.txt.zst", "b.txt.zst"):
        ferdig(dag, n, n.encode())
    kopi.kopier_rot(srv / "ais/bw", kv)
    (boks / "ais/bw/2026-10-10/b.txt.zst").unlink()
    for n in ("a.txt.zst", "b.txt.zst"):
        gammel(dag / n, 15)
    assert rydd.rydd_rot(srv / "ais/bw", 14, time.time(), torrkjor=True) == (1, 1)
    assert (dag / "a.txt.zst").exists() and (dag / "b.txt.zst").exists()

    monkeypatch.setattr(sys, "argv", ["rydd.py", "--torrkjor", "14", str(srv / "ais/bw")])
    with pytest.raises(SystemExit) as e:
        rydd.main()
    assert e.value.code == 1
    assert (dag / "a.txt.zst").exists()
