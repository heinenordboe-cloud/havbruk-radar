"""Skåreren: Fiskeridirektoratets fordeling mot det forseglede anslaget.

Fordelingen for 2026 er ikke publisert (08.11.2026). Prøvene leser
regnearket for 2025 som formatprøve, slik skåreren gjør med
`--formatprove 2025`: formatet skal være kjent den dagen 2026 kommer, og
tallene skal være de A3 fant. Det er ikke et treff.
"""
import hashlib
import json
from pathlib import Path

import pytest

import havbruksfond as h
import skaar_havbruksfond as s
from core import paths, snapshot

DATAREPO = Path(__file__).resolve().parent.parent.parent / "havbruk-radar-data" / "data"
trenger_data = pytest.mark.skipif(
    not (DATAREPO / "arkiv" / "havbruksfondet").is_dir(),
    reason="datarepoet ligger ikke ved siden av")


@pytest.fixture
def datarepo(monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
    monkeypatch.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
    return DATAREPO


@trenger_data
def test_formatproven_leser_2025_regnearket(datarepo):
    """Hele 2025-fordelingen leses: 143 kommuner, 8 fylkeskommuner, og
    avvikene er speilbildet av A3 (Frøya +0,537 der, −0,537 her)."""
    r = s.skaar(2025)
    assert r["kommuner_antall"] == 143 and r["fylker_antall"] == 8
    assert r["feil_hvis"]["2_kommunesett_ulikt"] == {"bare_i_fordelingen": [],
                                                    "bare_i_anslaget": []}
    # 2025 er et oddetallsår: ledd 1 i `feil_hvis` slår til, som det skal.
    assert r["feil_hvis"]["1_nyklarert_over_0"] == 48
    assert r["storste_feil"]["nr"] == "5014"
    assert round(r["storste_feil"]["avvik_pp"], 4) == -0.5367
    assert (r["innenfor"], r["fylker_innenfor"]) == (40, 2)
    assert sum(x["fasit_andel"] for x in r["kommuner"]) == pytest.approx(1)


@trenger_data
def test_fylkene_leses_i_begge_aarenes_form(datarepo):
    for aar in (2024, 2025):
        f = s.fylkestall(h.regneark(aar)[0])
        assert len(f) == 8 and all(v["belop"] > 0 for v in f.values()), aar


def test_et_brutt_segl_stopper_skaareren(monkeypatch):
    monkeypatch.setattr(h, "segl", lambda *a: {"uendret": False})
    with pytest.raises(ValueError, match="stemplet"):
        s.skaar(2025)
    assert s.main(["--formatprove", "2025", "--ut", "/tmp/finnes-ikke-9"]) == 2


def test_uten_aarets_regneark_skrives_ingenting(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "segl", lambda *a: {"uendret": True})
    monkeypatch.setattr(h, "anslaget", lambda *a: {"kommuner": {}, "fylker": {}})

    def mangler(aar):
        raise FileNotFoundError(f"fant ikke regnearket for {aar}")
    monkeypatch.setattr(h, "regneark", mangler)
    monkeypatch.setattr(h, "skaringsmappe", lambda: tmp_path / "havbruksfond")
    assert s.main([]) == 0
    assert not (tmp_path / "havbruksfond").exists()


def test_formatproven_skrives_aldri_i_datarepoet():
    with pytest.raises(SystemExit):
        s.main(["--formatprove", "2025", "--ut", str(paths.DATA_DIR / "havbruksfond")])
    with pytest.raises(SystemExit):
        s.main(["--formatprove", "2025"])


def _skaring(aar=2026, avvik=0.01):
    return {"aar": aar, "terskel_pp": 0.05, "regneark": {"sti": "x", "sha256": "0"},
            "anslag": {"fil": "a", "sha256": "1", "uendret": True},
            "kommuner_antall": 1, "innenfor": 1, "skaaret": 1,
            "storste_feil": {"nr": "5014", "navn": "FRØYA", "avvik_pp": avvik,
                             "fasit_andel": 0.05, "anslag_andel": 0.05, "innenfor": True},
            "middel_abs_avvik_pp": avvik, "fylker_innenfor": 0, "fylker_antall": 0,
            "fylker_storste_feil": None,
            "feil_hvis": {"1_nyklarert_over_0": 0,
                          "2_kommunesett_ulikt": {"bare_i_fordelingen": [], "bare_i_anslaget": []},
                          "3_kommuner_utenfor": 0, "4_fylker_utenfor": 0},
            "kommuner": [{"nr": "5014", "navn": "FRØYA", "fasit_andel": 0.05,
                          "anslag_andel": 0.05, "avvik_pp": avvik, "innenfor": True}],
            "fylker": []}


def test_skaringen_skrives_en_gang_og_aldri_om(tmp_path):
    [js, md] = s.skriv(_skaring(), tmp_path)
    assert js.name == "skaring-2026.json" and md.name == "skaring-2026.md"
    assert s.skriv(_skaring(), tmp_path) == []
    [js2, _] = s.skriv(_skaring(avvik=0.02), tmp_path)
    assert js2.name == "skaring-2026.2.json"
    assert json.loads(js.read_text())["storste_feil"]["avvik_pp"] == 0.01


def test_formatproven_sier_det_overst(tmp_path):
    [js, md] = s.skriv(_skaring(aar=2025), tmp_path, formatprove=True)
    assert js.name == "formatprove-2025.json"
    assert md.read_text().startswith("**FORMATPRØVE")
    assert json.loads(js.read_text())["formatprove"].startswith("FORMATPRØVE")


def test_skaringen_vises_bare_med_kvittering_for_akkurat_den_fila(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path)
    mappe = h.skaringsmappe()
    [js, _] = s.skriv(_skaring(), mappe)
    assert h.lest_skaring(2026) is None                     # ingen kvittering
    kv = {"dato": "2026-11-20", "lest_av": "Heine Nordboe", "skaring": js.name,
          "sha256": hashlib.sha256(js.read_bytes()).hexdigest()}
    (mappe / "lest-2026.json").write_text(json.dumps(kv))
    assert h.lest_skaring(2026)["lest"]["dato"] == "2026-11-20"
    js.write_text(js.read_text().replace("0.01", "0.02"))   # fila endret etter lesing
    assert h.lest_skaring(2026) is None
    kv["skaring"] = "../utenfor.json"
    (mappe / "lest-2026.json").write_text(json.dumps(kv))
    assert h.lest_skaring(2026) is None
