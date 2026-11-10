"""Fasiten: Fiskeridirektoratets fordeling mot pakke 1 og pakke 2.

Fordelingen 2026 var ikke publisert 10.11.2026 kl. 13 UTC. Prøvene kjører
kjeden mot kroppene for 2025, slik `fasit_havbruksfond.py --torrkjor 2025`
gjør, og holder tallene mot det A3 og pakke 2 sier om 2025. Det er ikke et
treff: 2025 er et oddetallsår med en del for ny MTB, og anslagene gjelder
2026. Det de viser, er at hvert ledd leser det det skal, og at 2025-
formatet bærer hele kjeden.

De fleste trenger datarepoet ved siden av og hoppes over uten det.
"""
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import fasit_havbruksfond as fa
import havbruksfond as h
import nettsted
from core import paths, snapshot
from tests.test_havbruksfond import FASITFELT, kroner_utenom_fasiten

DATAREPO = Path(__file__).resolve().parent.parent.parent / "havbruk-radar-data" / "data"
trenger_data = pytest.mark.skipif(
    not (DATAREPO / "raw" / "akvakultur" / f"{h.FOR}.parquet").exists(),
    reason="datarepoet ligger ikke ved siden av")


@pytest.fixture(scope="module")
def torr2025():
    """Hele fasiten for 2025-kroppene, uten nett: én gang for modulen."""
    if not (DATAREPO / "raw" / "akvakultur" / f"{h.FOR}.parquet").exists():
        pytest.skip("datarepoet ligger ikke ved siden av")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
        mp.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
        yield fa.fasit(2025, nett=False)


# ------------------------------------------------------------ pakke 2


def test_pakke2_leses_som_den_ble_forseglet():
    p = h.pakke2()
    assert [x["id"] for x in p["paastander"]] == [f"2026-11-09-{i}" for i in range(1, 10)]
    assert [x["konfidens"] for x in p["paastander"]] == [90, 80, 75, 85, 90, 70, 55, 35, 95]
    assert p["kommuner"]["5501"] == {"navn": "TROMSØ", "gruppe": "G", "mtb": 59063.0,
                                     "andel": pytest.approx(0.015475)}
    assert p["fylker"]["55"]["andel"] == pytest.approx(0.15085)
    assert {x["nr"] for x in p["lokaliteter"] if x["paastand"] == "P2-3"} == {"10768", "15236"}
    assert sum(1 for x in p["lokaliteter"] if x["paastand"] == "P2-5") == 9
    persflua = next(x for x in p["lokaliteter"] if x["nr"] == "33417")
    assert persflua["deling"] == {} and persflua["forventet"] == "ikke delt"
    assert next(x for x in p["lokaliteter"] if x["nr"] == "10181")["deling"] == {
        "1532": 0.352441, "1580": 0.647566}


def test_en_pakke2_med_feil_form_leses_ikke(tmp_path):
    """En rad mindre i kommunetabellen, og anslaget er ikke det som ble
    forseglet. Da skal ingenting avgjøres mot det."""
    tekst = h.ANSLAG2.read_text(encoding="utf-8")
    sti = tmp_path / "p2.md"
    sti.write_text(tekst.replace("| 1566 | SURNADAL | U | 780 | 0.0204% |\n", ""), "utf-8")
    with pytest.raises(ValueError, match="143|grupper"):
        h.pakke2(sti)


def test_leddene_i_pakke1_leses_ordrett():
    import re
    import yaml
    tekst = h.ANSLAG.read_text(encoding="utf-8")
    p = yaml.safe_load(re.search(r"```yaml\n(.*?)```", tekst, re.S).group(1))["prediksjoner"][0]
    ledd = fa._ledd(p["feil_hvis"])
    assert sorted(ledd) == [1, 2, 3, 4]
    assert ledd[1].startswith("Tabellen «Utbetalinger fra Havbruksfondet 2026» har en kolonne")
    assert ledd[2] == "Kommunesettet er ikke de samme 143 kommunenumrene som i A2."
    assert "Mekanismen" not in ledd[4]


# ---------------------------------------------------------- forseglingene


def test_forseglingene_holder():
    """Begge filene er det som ble forseglet, og .ots-summen er filas. En
    commit som finnes her, har fila uendret (en grunn klon i Actions har
    dem ikke, og da er de ikke prøvd)."""
    for x in fa.forseglinger(nett=False):
        assert x["brutt"] == [], x
        assert x["sha256"] == x["sha256_forseglet"] == x["ots_sum"]
        assert all(c["lik"] for c in x["commits"] if c["prøvd"]), x["commits"]


def test_et_endret_anslag_bryter_seglet(tmp_path):
    rot = tmp_path / "havbruk-radar"
    for f in h.FORSEGLINGER:
        (rot / f["fil"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(h.ROT / f["fil"], rot / f["fil"])
        shutil.copy2(h.ROT / (f["fil"] + ".ots"), rot / (f["fil"] + ".ots"))
    (rot / "predictions/havbruksfond-2026-pakke2.md").write_text("endret\n")
    brutt = [b for x in fa.forseglinger(rot=rot, nett=False) for b in x["brutt"]]
    assert len(brutt) == 1 and "pakke2.md har sha256" in brutt[0]


def test_et_brutt_segl_stopper_fasiten(monkeypatch, tmp_path):
    monkeypatch.setattr(fa, "forseglinger", lambda **k: [{"brutt": ["sha256 ulik"]}])
    monkeypatch.setattr(h, "skaringsmappe", lambda: tmp_path / "havbruksfond")
    assert fa.main(["--uten-nett"]) == 2
    assert not (tmp_path / "havbruksfond").exists()


# -------------------------------------------------------- tørrkjøringen


@trenger_data
def test_pakke1_mot_2025(torr2025):
    """2025 er et oddetallsår: ledd 1 slår til (48 kommuner, som skåreren
    fant), og ledd 3 og 4 med A3s største avvik (Frøya −0,537, Nordland
    −0,324). Kommunesettet er likt."""
    p1 = torr2025["pakke1"]
    assert p1["utfall"] == "bom"
    assert [x["slaar_til"] for x in p1["ledd"]] == [True, False, True, True]
    assert len(p1["ledd"][0]["tall"]["kommuner_over_0"]) == 48
    assert round(p1["kommuner_utenfor"][0]["avvik_pp"], 4) == -0.5367
    assert p1["kommuner_utenfor"][0]["nr"] == "5014"
    assert p1["fylker_utenfor"][0]["nr"] == "18"


@trenger_data
def test_pakke2_mot_2025(torr2025):
    """P2-1 SKAL treffe 2025: gruppe U er per definisjon Fiskeridirektoratets
    egne tall per 01.09.2025. P2-3 og P2-6 likeså (listen 2025 er grunnlaget
    for dem), og P2-4 skal bomme (HØGÅS manglet i 2025)."""
    utfall = {x["paastand"]: x["utfall"] for x in torr2025["pakke2"]}
    assert utfall == {"P2-1": "traff", "P2-2": "bom", "P2-3": "traff", "P2-4": "bom",
                      "P2-5": "traff", "P2-6": "traff", "P2-7": "bom", "P2-8": "bom",
                      "P2-9": "traff"}
    p2_2 = next(x for x in torr2025["pakke2"] if x["paastand"] == "P2-2")
    assert len(p2_2["avvik"]) == 26
    p2_4 = next(x for x in torr2025["pakke2"] if x["paastand"] == "P2-4")
    assert p2_4["avvik"] == [{"nr": "38097", "navn": "HØGÅS", "forventet_t": 780.0,
                              "fasit_t": None, "hvorfor": "mangler på listen"}]


@trenger_data
def test_avvikene_mot_2025_i_tre_grupper(torr2025):
    g = torr2025["avvik"]
    assert not g["foreloepig"]
    kom = {k["nr"]: k for k in g["kommuner"]}
    # HØGÅS er et grensetilfelle, og Strand er der det skiller.
    assert kom["1130"]["gruppe"] == "G" and "38097" in kom["1130"]["hvorfor"]
    # En lokalitet som er borte fra registeret, er grunnlaget, ikke oss.
    lok = {(x["nr"], x["komnr"]): x for x in g["lokaliteter"]}
    assert lok[("36237", "5542")]["gruppe"] == "R"
    # En ny lokalitet i nøkkelen vår som ikke står på listen, er vår.
    assert lok[("45280", "5014")]["gruppe"] == "V"
    # Andelen alene flyttes av nyklarert-delen, og den står i tabellen.
    assert kom["1560"]["gruppe"] == "R" and "nyklarert" in kom["1560"]["hvorfor"]
    # Hver kommune med avvik har én gruppe, og ingen uten avvik har det.
    assert all(k["gruppe"] in fa.GRUPPER for k in g["kommuner"]
               if abs(k["p2_avvik_pp"]) > fa.P2_PP)
    assert sum(g["antall"].values()) == sum(1 for k in g["kommuner"] if k["gruppe"])


@trenger_data
def test_pressemeldingen_og_regnearket_er_enige_for_2025(torr2025):
    """A3: alle 143 beløp er like i de to kroppene, med avvik under 1 kr."""
    mh = torr2025["pressemelding_mot_regnearket"]
    assert mh["dato"] == "2025-11-10"
    assert mh["kommuner_ulike"] == [] and mh["fylker_ulike"] == []


@trenger_data
def test_tabellen_vises_med_sti_og_sha256(torr2025):
    tb = torr2025["tabell"]
    assert tb["form"] == "regneark" and tb["sti"] == "havbruksfondet/2026-10-12.8.bin.gz"
    assert tb["sha256"] == "e26cfffe259153d0f9fd9d84c3f2a89b3d904e290c0f48f5978a667e38308b76"
    assert tb["url"].endswith("utbetaling%202025_til%20publisering.xlsx")


def test_torrkjoringen_skrives_aldri_i_datarepoet():
    for argv in (["--torrkjor", "2025", "--ut", str(paths.DATA_DIR / "havbruksfond")],
                 ["--torrkjor", "2025"], ["--sider"]):
        with pytest.raises(SystemExit):
            fa.main(argv)


# --------------------------------------------------- skriving og kvittering


def _fasit(aar=2026, belop=1000.0, kode="abc"):
    return {"aar": aar, "tabell": {"form": "regneark", "sti": "havbruksfondet/x.bin.gz",
                                   "sha256": "0" * 64, "url": "https://example.invalid/x.xlsx",
                                   "hentet": "2026-11-12T14:45:00+00:00", "publisert": "",
                                   "dato": "", "arkivdato": "2026-11-12", "merknader": []},
            "pressemelding_mot_regnearket": None, "uleselig": [], "forseglinger": [],
            "pakke1": {"id": "x", "konfidens": 75, "utfall": "traff", "ledd": [],
                       "kommuner_utenfor": [], "fylker_utenfor": []},
            "pakke2": [],
            "avvik": {"foreloepig": False, "kommuner": [], "fylker": [], "lokaliteter": [],
                      "netto_t": {g: 0.0 for g in fa.GRUPPER},
                      "antall": {g: 0 for g in fa.GRUPPER},
                      "fylker_antall": {g: 0 for g in fa.GRUPPER}},
            "sider": {"kommuner": {"5501": {"belop": belop, "andel": 0.015}},
                      "fylker": {"55": {"belop": belop, "andel": 0.15}}},
            "kode": kode, "_tider": {}}


def test_fasiten_skrives_en_gang_og_aldri_om(tmp_path):
    [js, md] = fa.skriv(_fasit(), tmp_path)
    assert (js.name, md.name) == ("fasit-2026.json", "fasit-2026.md")
    assert fa.skriv(_fasit(), tmp_path) == []
    assert fa.skriv(_fasit(kode="def"), tmp_path) == []      # bare koden er ny
    [js2, _] = fa.skriv(_fasit(belop=2000.0), tmp_path)
    assert js2.name == "fasit-2026.2.json"
    assert json.loads(js.read_text())["sider"]["kommuner"]["5501"]["belop"] == 1000.0


def test_torrkjoringen_sier_det_overst(tmp_path):
    [js, md] = fa.skriv(_fasit(aar=2025), tmp_path, torrkjoring=True)
    assert js.name == "torrkjoring-2025.json"
    assert md.read_text().startswith("**TØRRKJØRING")
    assert json.loads(js.read_text())["torrkjoring"].startswith("TØRRKJØRING")


def test_kvitteringen_gjelder_akkurat_den_fila(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path)
    mappe = h.skaringsmappe()
    [js, _] = fa.skriv(_fasit(), mappe)
    assert h.lest_fasit(2026) is None                        # ikke kvittert
    # En kvittering for skåringen fra økt 9 er ikke en kvittering for fasiten.
    (mappe / "lest-2026.json").write_text(json.dumps(
        {"dato": "2026-11-20", "skaring": js.name,
         "sha256": hashlib.sha256(js.read_bytes()).hexdigest()}))
    assert h.lest_fasit(2026) is None
    kv = fa.kvitter(2026)
    assert kv.name == "lest-fasit-2026.json"
    assert h.lest_fasit(2026)["lest"]["fasit"] == "fasit-2026.json"
    js.write_text(js.read_text().replace("1000.0", "1001.0"))  # endret etter lesing
    assert h.lest_fasit(2026) is None


def test_uten_aarets_tabell_skrives_ingenting(monkeypatch, tmp_path):
    monkeypatch.setattr(fa, "forseglinger", lambda **k: [{"brutt": []}])
    monkeypatch.setattr(fa, "les_tabellen", lambda aar, p2: (None, None, []))
    monkeypatch.setattr(h, "skaringsmappe", lambda: tmp_path / "havbruksfond")
    assert fa.main(["--uten-nett"]) == 0
    assert not (tmp_path / "havbruksfond").exists()


# ------------------------------------------------------- kommunesidene


def _felles():
    return SimpleNamespace(akva={}, vilkaar=nettsted.kildevilkaar(),
                           kontakt=nettsted._kontakt())


@trenger_data
def test_kommunesiden_viser_belopet_med_kilde_og_dato(torr2025, tmp_path, monkeypatch):
    """Med fasiten: beløpet, Fiskeridirektoratets andel og avviket fra
    registerets andel, med kilden og datoen vi hentet tabellen. Ingen
    andre beløp på sidene."""
    monkeypatch.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
    monkeypatch.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
    monkeypatch.setattr(nettsted, "DATA_DIR", DATAREPO)
    data = {k: v for k, v in torr2025.items() if not k.startswith("_")}
    assert len(nettsted.skriv_kommuner(tmp_path, _felles(), fasit=data)) == 143
    side = (tmp_path / "kommune" / "5501" / "index.html").read_text("utf-8")
    assert 'data-felt="fasit_belop">18 931 168 kr</dd>' in side
    assert "Fiskeridirektoratets fordeling 2025" in side
    assert "1,6784 %" in side and "+0,1728" in side
    assert 'datetime="2026-10-12"' in side and data["tabell"]["url"] in side
    oversikt = (tmp_path / "kommune" / "index.html").read_text("utf-8")
    assert "1 127 938 400 kr" in oversikt
    for fil in (tmp_path / "kommune").rglob("index.html"):
        tekst = fil.read_text("utf-8")
        assert FASITFELT.search(tekst), fil                  # prøven ser feltene
        assert not kroner_utenom_fasiten(tekst), fil


@trenger_data
def test_uten_kvittering_ingen_belop(tmp_path, monkeypatch):
    """En fasit som er skrevet, men ikke kvittert, står ikke på sidene."""
    monkeypatch.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
    monkeypatch.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
    monkeypatch.setattr(nettsted, "DATA_DIR", DATAREPO)
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path)
    fa.skriv(_fasit(), h.skaringsmappe())
    d = nettsted.bygg_kommuner(_felles())
    assert d["fasit"] is None
    fa.kvitter(2026)
    assert nettsted.bygg_kommuner(_felles())["fasit"]["per_kommune"]["5501"]["belop"] == \
        "1 000 kr"
