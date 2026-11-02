"""kystvakt/regnskap.py: ett regnskap per ferdig time, skrevet én gang."""
import json
import sys
from compression import zstd
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kystvakt"))
import regnskap  # noqa: E402

sys.path.pop(0)

NMEA = b"\\s:NorSat_3,c:1793197200*00\\!AIVDM,1,1,,A,13m?Qc701GQ`9fR`ELVRpBL:0@1L,0*2D\r"
BW = (b'{"type":"Position","mmsi":257090580,"msgtime":"2026-10-28T13:59:58+00:00"}',
      b'{"type":"Staticdata","mmsi":258028100,"msgtime":"2026-10-28T14:00:01+00:00"}')


def timefil(rot, navn, rader):
    dag = rot / navn[:10]
    dag.mkdir(parents=True, exist_ok=True)
    (dag / f"{navn}.txt.zst").write_bytes(zstd.compress(b"".join(t + b"\t" + l + b"\n" for t, l in rader)))


def test_regnskap_teller_og_sammenligner(tmp_path, monkeypatch):
    bw, k5632, klokke = tmp_path / "bw", tmp_path / "5632", tmp_path / "klokke"
    timefil(bw, "2026-10-28T14Z", [(b"2026-10-28T14:00:00.500000Z", BW[0]),
                                   (b"2026-10-28T14:10:00.000000Z", BW[1])])
    timefil(k5632, "2026-10-28T14Z", [(b"2026-10-28T14:20:00.000000Z", NMEA)])
    (k5632 / "STARTET").write_text("2026-10-28T13:59:00.000000Z\n")
    klokke.mkdir()
    (klokke / "2026-10-28.csv").write_text(
        "2026-10-28T14:01:00Z,65D8456C,x,3,1,0.0001,0,0,0,0,0,0,0,64,Normal\n"
        "2026-10-28T15:01:00Z,65D8456C,x,3,1,0.5,0,0,0,0,0,0,0,64,Normal\n")
    naa = datetime(2026, 10, 28, 15, 10, tzinfo=timezone.utc)
    r = regnskap.regnskap_for("bw", bw, "5632", k5632, klokke, "2026-10-28T14", naa)
    assert r["meldinger"] == 2 and r["unike_mmsi"] == 2
    # 14:00:00.5 − 13:59:58 = 2.5 s og 14:10:00 − 14:00:01 = 599 s
    assert r["forsinkelse_s"] == {"median": 300.75, "maks": 599.0, "min": 2.5, "antall": 2}
    assert r["lengste_pause_s"] == 3000.0  # 14:10 til timens slutt
    assert r["chrony"] == {"prover": 1, "synkronisert": 1, "maks_avvik_s": 0.0001, "svar": True}
    assert regnskap.les_nmea(NMEA) == (257155500, 1793197200.0)  # som pyais
    assert r["annen"] == {"kilde": "5632", "unike_mmsi": 1, "felles_mmsi": 0,
                          "bare_her": 2, "bare_der": 1}


def test_time_uten_filer_far_regnskap_med_null(tmp_path, monkeypatch):
    rot, annen, klokke = tmp_path / "a", tmp_path / "b", tmp_path / "k"
    timefil(rot, "2026-10-28T10Z", [(b"2026-10-28T10:00:01.000000Z", NMEA)])
    (rot / "STARTET").write_text("2026-10-28T09:58:00.000000Z\n")
    annen.mkdir()
    (annen / "STARTET").write_text("2026-10-28T11:30:00.000000Z\n")
    klokke.mkdir()

    class Naa(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 28, 14, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(regnskap, "datetime", Naa)
    regnskap.kjør_time("5632", rot, "bw", annen, klokke)
    dag = rot / "2026-10-28"
    # timen lytteren startet i, og timen før: før lytteren regnes ingenting
    assert not (dag / "2026-10-28T08Z.regnskap.json").exists()
    assert json.loads((dag / "2026-10-28T09Z.regnskap.json").read_text())["meldinger"] == 0
    tom = json.loads((dag / "2026-10-28T11Z.regnskap.json").read_text())
    assert tom["meldinger"] == 0 and tom["lengste_pause_s"] == 3600.0 and tom["filer"] == {}
    # den andre startet 11:30: timen 10 er ikke dens
    ti = json.loads((dag / "2026-10-28T10Z.regnskap.json").read_text())
    assert ti["annen"] is None and ti["annen_mangler"] == "bw: lyttet ikke ennå"
    # 12: den andre lyttet, men sendte ingenting: tom mengde, ikke ukjent
    tolv = json.loads((dag / "2026-10-28T12Z.regnskap.json").read_text())
    assert tolv["annen"] == {"kilde": "bw", "unike_mmsi": 0, "felles_mmsi": 0,
                             "bare_her": 0, "bare_der": 0}
    # og et regnskap skrives aldri om
    regnskap.kjør_time("5632", rot, "bw", annen, klokke)
    assert oct((dag / "2026-10-28T11Z.regnskap.json").stat().st_mode & 0o777) == "0o444"


# ---- puls til overvåkingen utenfra (fra 02.11.2026) ----------------------

def _r(time_, meldinger, uten_mmsi=0):
    return {"time": time_, "meldinger": meldinger, "uten_mmsi": uten_mmsi}


def test_puls_naar_nyeste_time_har_meldinger():
    sendt = []
    ut = regnskap.puls([_r("2026-11-02T18Z", 0), _r("2026-11-02T19Z", 41000)],
                       url="https://hc-ping.example/x", send=sendt.append)
    assert sendt == ["https://hc-ping.example/x"] and "puls sendt" in ut


def test_ingen_puls_naar_nyeste_time_er_tom():
    """Tre timer tatt igjen, den siste tom: lytteren er stille NÅ."""
    sendt = []
    regnskap.puls([_r("2026-11-02T17Z", 40000), _r("2026-11-02T19Z", 0),
                   _r("2026-11-02T18Z", 39000)], url="u", send=sendt.append)
    assert sendt == []


def test_ingen_puls_uten_ny_time_eller_adresse(tmp_path, monkeypatch):
    sendt = []
    assert regnskap.puls([], url="u", send=sendt.append) == "ingen ny time"
    monkeypatch.setattr(regnskap, "PULS", str(tmp_path / "finnes-ikke.env"))
    assert regnskap.puls_url(str(tmp_path / "finnes-ikke.env")) is None
    assert "mangler" in regnskap.puls([_r("2026-11-02T19Z", 1)], send=sendt.append)
    assert sendt == []


def test_puls_som_feiler_stopper_ikke_regnskapet():
    def nede(url):
        raise OSError("nett nede")
    assert "kom ikke fram" in regnskap.puls([_r("2026-11-02T19Z", 1)], url="u",
                                            send=nede)


def test_puls_url_leses_fra_fila(tmp_path):
    f = tmp_path / "puls-ais.env"
    f.write_text('# signal\nPULS_URL="https://hc-ping.example/abc"\n')
    assert regnskap.puls_url(str(f)) == "https://hc-ping.example/abc"
    f.write_text("ANNET=1\n")
    assert regnskap.puls_url(str(f)) is None


def test_kjor_time_sender_puls_bare_for_bw(tmp_path, monkeypatch):
    bw, k5632, klokke = tmp_path / "bw", tmp_path / "5632", tmp_path / "klokke"
    timefil(bw, "2026-10-28T14Z", [(b"2026-10-28T14:00:00.500000Z", BW[0])])
    (bw / "STARTET").write_text("2026-10-28T14:00:00Z\n")
    (k5632 / "2026-10-28").mkdir(parents=True)
    (k5632 / "STARTET").write_text("2026-10-28T14:00:00Z\n")
    klokke.mkdir()

    class Klokke(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 28, 15, 10, tzinfo=timezone.utc)
    monkeypatch.setattr(regnskap, "datetime", Klokke)
    sendt = []
    monkeypatch.setattr(regnskap, "_send", sendt.append)
    monkeypatch.setattr(regnskap, "puls_url", lambda sti=None: "https://hc-ping.example/bw")
    regnskap.kjør_time("5632", k5632, "bw", bw, klokke)
    assert sendt == []
    regnskap.kjør_time("bw", bw, "5632", k5632, klokke)
    assert sendt == ["https://hc-ping.example/bw"]


def test_ingen_puls_naar_timen_bare_har_linjer_uten_mmsi():
    """En feilside etter 200 lagres linje for linje av lytteren og telles
    som meldinger. Den skal ikke holde vakten grønn."""
    sendt = []
    ut = regnskap.puls([_r("2026-11-02T19Z", 12, uten_mmsi=12)], url="u",
                       send=sendt.append)
    assert sendt == [] and "ingen med MMSI" in ut
