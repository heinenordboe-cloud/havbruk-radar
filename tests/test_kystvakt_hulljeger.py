"""kystvakt/hulljeger.py: hvilke timer er hull, og hvordan de blir vinduer."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kystvakt"))
import hulljeger  # noqa: E402

sys.path.pop(0)

NAA = datetime(2026, 10, 28, 20, 30, tzinfo=timezone.utc)


def regnskap(rot, time_, meldinger=170_000, pause=12.0):
    dag = rot / time_[:10]
    dag.mkdir(parents=True, exist_ok=True)
    (dag / f"{time_}Z.txt.zst").write_bytes(b"")
    (dag / f"{time_}Z.regnskap.json").write_text(
        json.dumps({"meldinger": meldinger, "lengste_pause_s": pause}))


def test_hull_er_tomme_lave_og_lange_pauser_innenfor_14_dogn(tmp_path):
    for t in range(0, 18):
        regnskap(tmp_path, f"2026-10-28T{t:02d}")
    regnskap(tmp_path, "2026-10-28T03", meldinger=40_000)
    regnskap(tmp_path, "2026-10-28T05", pause=130)
    (tmp_path / "2026-10-28" / "2026-10-28T07Z.regnskap.json").unlink()
    (tmp_path / "2026-10-28" / "2026-10-28T07Z.txt.zst").unlink()
    hull = dict(hulljeger.finn_hull(tmp_path, NAA))
    assert hull["2026-10-28T03"] == "40000 meldinger"
    assert hull["2026-10-28T05"] == "pause 130 s"
    assert hull["2026-10-28T07"] == "tom"
    # før lytteren fantes, er timene tomme; eldste tas med, innenfor 14 døgn
    assert min(hull) == "2026-10-14T23"  # 14 døgn minus to timers margin
    # de tre siste timene er lytterens, ikke hulljegerens
    assert "2026-10-28T17" not in hull and "2026-10-28T16" not in hull


def test_time_uten_regnskap_men_med_rafil_er_ikke_hull(tmp_path):
    dag = tmp_path / "2026-10-28"
    dag.mkdir()
    (dag / "2026-10-28T10Z.txt.zst").write_bytes(b"")
    assert hulljeger.er_hull(tmp_path, "2026-10-28T10") is None


def test_etterhentet_hentes_ikke_igjen(tmp_path):
    d = tmp_path / "etterhentet" / "2026-10-20"
    d.mkdir(parents=True)
    (d / "2026-10-20T00Z--2026-10-21T00Z.etterhentet.jsonl.zst").write_bytes(b"")
    hull = dict(hulljeger.finn_hull(tmp_path, NAA))
    assert not any(n.startswith("2026-10-20") for n in hull)
    assert "2026-10-21T00" in hull


def test_sammenhengende_hull_blir_vinduer_pa_inntil_24_timer():
    hull = [(f"2026-10-15T{t:02d}", "tom") for t in range(0, 24)]
    hull += [(f"2026-10-16T{t:02d}", "tom") for t in range(0, 3)]
    hull += [("2026-10-16T10", "pause 300 s")]
    v = hulljeger.vinduer(hull)
    assert [(a.strftime("%dT%H"), b.strftime("%dT%H")) for a, b in v] == [
        ("15T00", "16T00"), ("16T00", "16T03"), ("16T10", "16T11")]
