"""kystvakt/lytter.py: rått inn, rått ut, én fil per time, aldri overskrevet."""
import hashlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

zstd = pytest.importorskip("compression.zstd")

LYTTER = Path(__file__).resolve().parent.parent / "kystvakt" / "lytter.py"
LINJER = [
    b"\\s:2573345,c:1793163060*0A\\!BSVDM,1,1,,A,13m?Qc701GQ`9fR`ELVRpBL:0@1L,0*2D\r\n",
    b"\\g:1-2-17,s:2573505,c:1793163061*55\\!BSVDM,2,1,7,B,55NBP6000002...,0*00\r\n",
    b"ingen tag-blokk og ingen \\r\n",
]
HALE = b"\\s:avkortet,c:17931"


def server(data: bytes):
    """Sender `data` til den første som kobler til, og lukker."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)

    def svar():
        k, _ = s.accept()
        for i in range(0, len(data), 7):  # små biter: linjer deles over recv()
            k.sendall(data[i:i + 7])
        time.sleep(0.2)
        k.close()
        s.close()

    threading.Thread(target=svar, daemon=True).start()
    return s.getsockname()[1]


def kjor(rot: Path, data: bytes) -> str:
    port = server(data)
    env = {**os.environ, "AIS_VERT": "127.0.0.1"}
    p = subprocess.Popen([sys.executable, str(LYTTER), str(rot), str(port)],
                         env=env, stderr=subprocess.PIPE)
    frist = time.monotonic() + 10
    while time.monotonic() < frist:
        if not list(rot.glob("*/.*.delvis")):
            time.sleep(0.05)
            continue
        time.sleep(0.6)  # serveren lukker, halen skrives
        break
    p.send_signal(signal.SIGTERM)
    _, err = p.communicate(timeout=10)
    assert p.returncode == 0, err
    return err.decode()


def ferdige(rot: Path) -> list[Path]:
    return sorted(rot.glob("*/*.txt.zst"))


def poster(sti: Path) -> list[tuple[bytes, bytes]]:
    ut = []
    for post in zstd.decompress(sti.read_bytes()).split(b"\n")[:-1]:
        t, tab, linje = post.partition(b"\t")
        assert tab
        ut.append((t, linje))
    return ut


def test_linjene_lagres_uendret_med_var_tid(tmp_path):
    err = kjor(tmp_path, b"".join(LINJER) + HALE)
    [fil] = ferdige(tmp_path)
    p = poster(fil)
    gjenskapt = b"".join(l + b"\n" for _, l in p)
    assert gjenskapt == b"".join(LINJER) + HALE + b"\n"
    assert all(t.endswith(b"Z") and len(t) == 27 for t, _ in p)
    assert "ufullstendig hale: 19 B" in err
    assert oct(fil.stat().st_mode & 0o777) == "0o444"
    assert not list(tmp_path.glob("*/.*.delvis"))


def test_manifestet_har_hashen_til_fila(tmp_path):
    kjor(tmp_path, b"".join(LINJER))
    [fil] = ferdige(tmp_path)
    manifest = (fil.parent / "SHA256SUMS").read_text()
    assert manifest == f"{hashlib.sha256(fil.read_bytes()).hexdigest()}  {fil.name}\n"


def test_omstart_samme_time_overskriver_ikke(tmp_path):
    kjor(tmp_path, LINJER[0])
    [forste] = ferdige(tmp_path)
    for_ = forste.read_bytes()
    kjor(tmp_path, LINJER[1])
    filer = ferdige(tmp_path)
    if len({f.parent for f in filer}) == 1 and filer[0].name[:13] == filer[-1].name[:13]:
        assert [f.name.split(".", 1)[1] for f in filer] == ["2.txt.zst", "txt.zst"]
    assert forste.read_bytes() == for_
    assert len((forste.parent / "SHA256SUMS").read_text().splitlines()) >= 1


def test_avbrutt_delvis_rores_ikke_men_fores(tmp_path):
    dag = tmp_path / "2026-10-28"
    dag.mkdir()
    delvis = dag / ".2026-10-28T05Z.delvis"
    innhold = zstd.compress(b"x\tlinje\n")[:-3]  # avkortet midt i rammen
    delvis.write_bytes(innhold)
    kjor(tmp_path, LINJER[0])
    avbrutt = dag / "2026-10-28T05Z.avbrutt.txt.zst"
    assert avbrutt.read_bytes() == innhold
    assert f"  {avbrutt.name}\n" in (dag / "SHA256SUMS").read_text()


def test_timeskifte_lukker_forrige_time(tmp_path, monkeypatch):
    sys.path.insert(0, str(LYTTER.parent))
    try:
        import lytter
    finally:
        sys.path.pop(0)
    tider = iter([b"2026-10-28T05:59:59.999999Z", b"2026-10-28T06:00:00.000001Z"])
    monkeypatch.setattr(lytter, "stempel", lambda: next(tider))
    lyt = lytter.Lytter(tmp_path, 0)
    lyt.skriv([b"a"])
    lyt.skriv([b"b"])
    lyt.lukk()
    navn = [f.name for f in ferdige(tmp_path)]
    assert navn == ["2026-10-28T05Z.txt.zst", "2026-10-28T06Z.txt.zst"]
    assert poster(ferdige(tmp_path)[0]) == [(b"2026-10-28T05:59:59.999999Z", b"a")]


def test_stille_strom_mister_ikke_det_som_kom_for_drap(tmp_path):
    """Vakten dreper etter fem stille minutter. Det som kom før stillheten
    skal ligge på disk da, ikke i kompressorens buffer."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    holdt = []

    def svar():
        k, _ = s.accept()
        k.sendall(LINJER[0])
        holdt.append(k)  # åpen og stille

    threading.Thread(target=svar, daemon=True).start()
    env = {**os.environ, "AIS_VERT": "127.0.0.1", "AIS_BLOKK_S": "0.3"}
    p = subprocess.Popen([sys.executable, str(LYTTER), str(tmp_path),
                          str(s.getsockname()[1])], env=env, stderr=subprocess.PIPE)
    time.sleep(2)
    p.kill()
    p.communicate(timeout=10)
    [delvis] = tmp_path.glob("*/.*.delvis")
    data = zstd.ZstdDecompressor().decompress(delvis.read_bytes())
    assert data.endswith(b"\t" + LINJER[0][:-1] + b"\n")
