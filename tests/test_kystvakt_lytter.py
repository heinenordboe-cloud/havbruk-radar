"""kystvakt/lytter.py: rått inn, rått ut, én fil per time, aldri overskrevet."""
import hashlib
import json
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


# --- Vakthunden og BarentsWatch (28.10.2026) ---------------------------------

def notify_socket(tmp_path):
    """En falsk systemd: tar imot sd_notify og husker hva som kom, når."""
    import tempfile
    # AF_UNIX tåler ikke macOS' lange tmp_path; /tmp er kort nok
    sti = str(Path(tempfile.mkdtemp(dir="/tmp")) / "n.sock")
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    s.bind(sti)
    s.settimeout(0.1)
    mottatt = []

    def les():
        while True:
            try:
                mottatt.append((time.monotonic(), s.recv(100)))
            except TimeoutError:
                continue
            except OSError:
                return

    threading.Thread(target=les, daemon=True).start()
    return sti, mottatt


def test_lytter_som_ikke_far_koblet_til_lever_og_venter_lenger(tmp_path):
    """Porten svarer ikke. Lytteren skal prøve igjen med økende ventetid,
    logge hvert forsøk, og gi vakten livstegn hele tiden: den er ikke hengt."""
    ledig = socket.socket()
    ledig.bind(("127.0.0.1", 0))
    port = ledig.getsockname()[1]
    ledig.close()  # ingen lytter på porten: tilkoblingen nektes
    sti, notes = notify_socket(tmp_path)
    env = {**os.environ, "AIS_VERT": "127.0.0.1", "AIS_VENT_MIN": "0.2",
           "NOTIFY_SOCKET": sti}
    p = subprocess.Popen([sys.executable, str(LYTTER), str(tmp_path / "raa"), str(port)],
                         env=env, stderr=subprocess.PIPE)
    time.sleep(2.5)
    p.send_signal(signal.SIGTERM)
    _, err = p.communicate(timeout=10)
    err = err.decode()
    assert p.returncode == 0, err
    assert "venter 0.2 s" in err and "venter 0.4 s" in err and "venter 0.8 s" in err
    assert "forsøk 3" in err
    vakt = [t for t, m in notes if m == b"WATCHDOG=1"]
    assert len(vakt) >= 4
    # aldri lenger enn ventetiden mellom to livstegn
    assert max(b - a for a, b in zip(vakt, vakt[1:])) < 1.5


def test_tilkoblet_og_stille_gir_ingen_livstegn(tmp_path):
    """Tilkoblet, én linje, så stillhet. Etter linja skal vakten ikke få
    flere livstegn: det er nettopp den lytteren vakten skal drepe."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    holdt = []

    def svar():
        k, _ = s.accept()
        k.sendall(LINJER[0])
        holdt.append(k)

    threading.Thread(target=svar, daemon=True).start()
    sti, notes = notify_socket(tmp_path)
    env = {**os.environ, "AIS_VERT": "127.0.0.1", "AIS_BLOKK_S": "0.2",
           "NOTIFY_SOCKET": sti}
    p = subprocess.Popen([sys.executable, str(LYTTER), str(tmp_path / "raa"),
                          str(s.getsockname()[1])], env=env, stderr=subprocess.PIPE)
    time.sleep(2.5)
    p.send_signal(signal.SIGTERM)
    _, err = p.communicate(timeout=10)
    vakt = [t for t, m in notes if m == b"WATCHDOG=1"]
    # ett før tilkoblingen, ett for linja; ingenting i de to stille sekundene
    assert len(vakt) == 2, (vakt, err)
    assert time.monotonic() - vakt[-1] > 2


def bw_server(linjer: list[bytes], tokens: list[str], strom_status=200):
    """Falsk BarentsWatch: tokenendepunkt og strøm over vanlig http."""
    import http.server
    import urllib.parse

    sett = {"token_kall": [], "auth": []}

    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            sett["token_kall"].append(urllib.parse.parse_qs(self.rfile.read(n).decode()))
            tok = tokens[min(len(sett["token_kall"]) - 1, len(tokens) - 1)]
            body = json.dumps({"access_token": tok, "expires_in": 3600}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            sett["auth"].append(self.headers["Authorization"])
            if strom_status != 200:
                self.send_response(strom_status)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            data = b"".join(linjer)
            for i in range(0, len(data), 11):  # chunker som deler linjer
                bit = data[i:i + 11]
                self.wfile.write(f"{len(bit):x}\r\n".encode() + bit + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.close_connection = True

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, sett


BW_LINJER = [
    b'{"type":"Position","messageType":1,"mmsi":257090580,"msgtime":"2026-10-28T14:44:46+00:00","stream":"terra"}\n',
    b'{"type":"Staticdata","messageType":5,"mmsi":258028100,"msgtime":"2026-10-28T14:44:47+00:00","name":"\xc3\x86GIR"}\n',
]


def kjor_bw(tmp_path, srv, sekunder=1.5):
    nokkel = tmp_path / "bw.env"
    nokkel.write_text("BW_AIS_CLIENT_ID=epost@x.no:prove\nBW_AIS_CLIENT_SECRET=hemmelig-verdi\n")
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    env = {**os.environ, "AIS_BW_NOKKEL": str(nokkel), "AIS_BW_TOKEN_URL": base + "/token",
           "AIS_BW_URL": base + "/v1/ais", "AIS_VENT_MIN": "0.2"}
    p = subprocess.Popen([sys.executable, str(LYTTER), str(tmp_path / "raa"), "bw"],
                         env=env, stderr=subprocess.PIPE)
    time.sleep(sekunder)
    p.send_signal(signal.SIGTERM)
    _, err = p.communicate(timeout=10)
    assert p.returncode == 0, err
    return err.decode()


def test_bw_linjene_lagres_uendret_og_tokenet_logges_aldri(tmp_path):
    srv, sett = bw_server(BW_LINJER, ["tok-AAA"])
    err = kjor_bw(tmp_path, srv, 3.0)  # data, så 2 s pause, så ny tilkobling
    srv.shutdown()
    filer = ferdige(tmp_path / "raa")
    p = [x for f in filer for x in poster(f)]
    # serveren lukker etter hver runde; første runde er de to linjene
    assert [l for _, l in p[:2]] == [l[:-1] for l in BW_LINJER]
    assert sett["auth"][0] == "Bearer tok-AAA"
    q = sett["token_kall"][0]
    assert q["scope"] == ["ais"] and q["grant_type"] == ["client_credentials"]
    assert "tok-AAA" not in err and "hemmelig-verdi" not in err
    # samme token gjenbrukes ved gjenoppkobling, det hentes ikke på nytt hver gang
    assert len(sett["auth"]) >= 2 and len(sett["token_kall"]) == 1


def test_bw_401_henter_nytt_token_og_venter_lenger(tmp_path):
    srv, sett = bw_server(BW_LINJER, ["tok-gammelt", "tok-nytt"], strom_status=401)
    err = kjor_bw(tmp_path, srv, 1.2)
    srv.shutdown()
    assert "strøm 401" in err and "venter 0.2 s" in err and "venter 0.4 s" in err
    assert sett["auth"][:2] == ["Bearer tok-gammelt", "Bearer tok-nytt"]
    assert "tok-" not in err
