"""ais_manifest.py: manifester skrives én gang, status overskrives."""
import io
import json
import sys

import pytest

import ais_manifest
from core import raw as raw_arkiv

S = "b" * 64
REGNSKAP = {"bw": {"timer": ["2026-10-29T06Z", "2026-10-30T05Z"],
                   "tomme": [], "mangler": ["2026-10-29T10Z"]}}


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(ais_manifest, "MANIFEST_DIR", tmp_path / "arkiv/ais-manifest")
    monkeypatch.setattr(ais_manifest, "STATUS", tmp_path / "ais/status.json")
    monkeypatch.setattr(ais_manifest, "DATA_DIR", tmp_path)
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path


def inn(monkeypatch, kropp: bytes):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(kropp)))


def utlevering(manifester=(), skrevet="2026-10-30T08:30:00Z", **felt):
    return {"skrevet": skrevet,
            "disk": {"brukt_prosent": 37.6, "ledig_bytes": 12349992960},
            "kopi_sist_ok": "2026-10-30T00:41:00Z", "regnskap": REGNSKAP,
            "manifester": list(manifester), **felt}


def kjør(monkeypatch, manifester, skrevet="2026-10-30T08:30:00Z"):
    inn(monkeypatch, json.dumps(utlevering(manifester, skrevet)).encode())
    assert ais_manifest.main() == 0


def test_skrives_en_gang_og_endring_faar_lopenummer(data, monkeypatch):
    m = {"kilde": "bw", "dato": "2026-10-29", "innhold": f"{S}  2026-10-29T00Z.txt.zst\n"}
    kjør(monkeypatch, [m])
    kjør(monkeypatch, [m], skrevet="2026-10-31T08:30:00Z")
    mappe = data / "arkiv/ais-manifest/bw"
    assert [p.name for p in mappe.iterdir()] == ["2026-10-29.SHA256SUMS"]
    assert json.loads((data / "ais/status.json").read_text())["skrevet"] == "2026-10-31T08:30:00Z"
    assert "manifester" not in json.loads((data / "ais/status.json").read_text())

    m2 = dict(m, innhold=m["innhold"] + f"{S}  2026-10-29T23Z.avbrutt.txt.zst\n")
    kjør(monkeypatch, [m2])
    assert sorted(p.name for p in mappe.iterdir()) == ["2026-10-29.2.SHA256SUMS", "2026-10-29.SHA256SUMS"]
    assert (mappe / "2026-10-29.SHA256SUMS").read_text() == m["innhold"]


@pytest.mark.parametrize("kilde,dato,innhold", [
    ("../x", "2026-10-29", ""),
    ("bw", "2026-10-29/../..", ""),
    ("bw", "2026-10-29", "ikke en sum\n"),
    ("bw", "2026-10-29", f"{S}  ../../ut\n"),
])
def test_avviser_det_som_ikke_er_et_manifest(data, kilde, dato, innhold):
    with pytest.raises(ValueError):
        ais_manifest.skriv_manifest(kilde, dato, innhold)



# ---------------------------------------------------------------- karantene
#
# MALING-DRIFT F2.2: `{"manifester": [], "skrevet": ""}` ga exit 0 og en
# status.json med bare `skrevet`. Nå sjekkes hele utleveringen først.

FEILSIDE = b"<!DOCTYPE html><html><body><h1>Feil</h1></body></html>"
GAMMEL = '{"skrevet": "2026-10-29T08:30:00Z"}\n'


@pytest.mark.parametrize("kropp,grunn", [
    (b'{"manifester": [], "skrevet": ""}', "skrevet er ikke et UTC-tidspunkt: ''"),
    (FEILSIDE, "ikke gyldig JSON"),
    (b"[]", "ikke et JSON-objekt, men list"),
    (b"", "ikke gyldig JSON"),
    (json.dumps(utlevering(disk={"brukt_prosent": "37"})).encode(), "disk mangler"),
    (json.dumps(utlevering(regnskap={})).encode(), "regnskap mangler"),
    (json.dumps(utlevering(regnskap={"bw": {"timer": ["x", "y"], "tomme": [],
                                            "mangler": []}})).encode(),
     "regnskap for 'bw'"),
    (json.dumps(utlevering(kopi_sist_ok=17)).encode(), "kopi_sist_ok"),
    (json.dumps(utlevering(regnskap={"bw": dict(REGNSKAP["bw"], per_time={
        "2026-10-30T05Z": {"meldinger": 3, "uten_mmsi": 4}})})).encode(),
     "har per_time, men"),
])
def test_mistenkt_utlevering_gaar_i_karantene_og_status_staar(data, monkeypatch,
                                                             capsys, kropp, grunn):
    (data / "ais").mkdir()
    (data / "ais/status.json").write_text(GAMMEL)
    inn(monkeypatch, kropp)

    assert ais_manifest.main() == 1
    assert (data / "ais/status.json").read_text() == GAMMEL, "forrige status står"
    [post] = (data / "arkiv/ais-manifest/karantene").glob("*.json")
    p = json.loads(post.read_text())
    assert p["status"] == "karantene" and any(grunn in g for g in p["grunn"])
    kroppen = post.with_name(post.name.removesuffix(".json"))
    import gzip
    assert gzip.decompress(kroppen.read_bytes()) == kropp, "slik den kom"
    assert "::error::Karantene (ais-manifest)" in capsys.readouterr().out


def test_et_ugyldig_manifest_holder_tilbake_hele_utleveringen(data, monkeypatch):
    god = {"kilde": "bw", "dato": "2026-10-29", "innhold": f"{S}  a.txt.zst\n"}
    darlig = {"kilde": "bw", "dato": "2026-10-30", "innhold": "ikke en sum\n"}
    inn(monkeypatch, json.dumps(utlevering([god, darlig])).encode())

    assert ais_manifest.main() == 1
    assert not (data / "arkiv/ais-manifest/bw").exists(), \
        "ingenting fra en mistenkt kropp kommer inn, heller ikke det gyldige"
    assert not (data / "ais/status.json").exists()


def test_den_ekte_formen_fra_kystvakt_1_slipper_gjennom(data, monkeypatch):
    """Formen i data/ais/status.json 02.11.2026, med 5632s tomme timer."""
    st = utlevering(regnskap={
        "bw": {"timer": ["2026-11-01T16Z", "2026-11-02T15Z"], "tomme": [], "mangler": []},
        "5632": {"timer": ["2026-11-01T16Z", "2026-11-02T15Z"],
                 "tomme": [f"2026-11-01T{h}Z" for h in range(16, 24)], "mangler": []}},
        kopi_sist_ok=None)
    inn(monkeypatch, json.dumps(st).encode())
    assert ais_manifest.main() == 0
    assert json.loads((data / "ais/status.json").read_text())["kopi_sist_ok"] is None


def test_per_time_fra_utleveringen_skrives_med_statusen(data, monkeypatch):
    pt = {"2026-10-30T05Z": {"meldinger": 824418, "uten_mmsi": 0}}
    st = utlevering(regnskap={"bw": dict(REGNSKAP["bw"], per_time=pt)})
    inn(monkeypatch, json.dumps(st).encode())
    assert ais_manifest.main() == 0
    skrevet = json.loads((data / "ais/status.json").read_text())
    assert skrevet["regnskap"]["bw"]["per_time"] == pt


def test_python_og_tjenestene_skrives_med_statusen(data, monkeypatch):
    tj = {"ais-bw.service": {"tilstand": "active", "resultat": "success"}}
    inn(monkeypatch, json.dumps(utlevering(python="3.14.4", tjenester=tj)).encode())
    assert ais_manifest.main() == 0
    skrevet = json.loads((data / "ais/status.json").read_text())
    assert skrevet["python"] == "3.14.4" and skrevet["tjenester"] == tj


@pytest.mark.parametrize("felt", [
    {"python": 3.14},
    {"python": "tre"},
    {"tjenester": []},
    {"tjenester": {}},
    {"tjenester": {"ais-bw.service": "active"}},
    {"tjenester": {"ais-bw.service": {"tilstand": "active"}}},
])
def test_uleselige_tjenester_eller_python_holder_tilbake_utleveringen(data, monkeypatch, felt):
    inn(monkeypatch, json.dumps(utlevering(**felt)).encode())
    assert ais_manifest.main() == 1
    assert not (data / "ais/status.json").exists()


def _prove(**felt):
    return {"tidspunkt": "2026-11-04T10:20:05Z", "kilde": "bw", "dato": "2026-10-29",
            "fil": "2026-10-29T05Z.txt.zst", "sha256": S, "manifest": S, "bytes": 10,
            "ok": True, "grunn": "lik manifestet", **felt}


@pytest.mark.parametrize("manifest,svar", [
    (f"{S}  2026-10-29T05Z.txt.zst\n", "lik"),
    (f"{'c' * 64}  2026-10-29T05Z.txt.zst\n", "ulik"),
    (f"{S}  2026-10-29T06Z.txt.zst\n", "mangler"),
])
def test_gjenopprettingen_holdes_mot_manifestet_i_datarepoet(data, monkeypatch, manifest, svar):
    """Manifestet i utleveringen skrives først, og da er det DET som er i
    arkivet: prøven holdes mot det GitHub har, ikke mot det serveren sier."""
    m = {"kilde": "bw", "dato": "2026-10-29", "innhold": manifest}
    inn(monkeypatch, json.dumps(utlevering([m], gjenoppretting=_prove())).encode())
    assert ais_manifest.main() == 0
    g = json.loads((data / "ais/status.json").read_text())["gjenoppretting"]
    assert g["mot_arkivet"] == svar and g["ok"] is True


def test_en_proeve_som_feilet_foer_hentingen_skrives_uten_mot_arkivet(data, monkeypatch):
    g = {"tidspunkt": "2026-11-04T10:20:05Z", "ok": False,
         "grunn": "ingen bekreftet datafil å hente i noen kvittering"}
    inn(monkeypatch, json.dumps(utlevering(gjenoppretting=g)).encode())
    assert ais_manifest.main() == 0
    assert json.loads((data / "ais/status.json").read_text())["gjenoppretting"] == g


@pytest.mark.parametrize("g", [{"ok": "ja"}, _prove(tidspunkt="i går"), _prove(sha256=1)])
def test_en_uleselig_gjenoppretting_holder_tilbake_utleveringen(data, monkeypatch, g):
    inn(monkeypatch, json.dumps(utlevering(gjenoppretting=g)).encode())
    assert ais_manifest.main() == 1
