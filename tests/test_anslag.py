"""Maskinanslagene: anslag.py og R6-modulen (økt 8). Skåreren: test_skaar_anslag.py.

Prøvene rører ikke ekte data. `isolert` flytter snapshotene og
predictions/maskin til tmp, og `ots` byttes ut med en som skriver en
OTS-fil med riktig hode og sum, uten nett.

Det som prøves mot repoet selv (ikke tmp), er det som ikke skal kunne
endre seg: R6s modul, forhåndsregistreringen og de forseglede ukefilene.
"""
import datetime as dt
import hashlib
import subprocess
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
import yaml

import anslag
import forsegl
import havbruksfond
import stempel
from core import kodeproveniens, paths, predictions, snapshot
from core.contract import Observation

T = dt.date(2026, 11, 9)                      # mandag i uke 46
K = T - dt.timedelta(weeks=4)                 # 2026-10-12
NAA = dt.datetime(2026, 11, 10, 20, 0, tzinfo=dt.timezone.utc)
OTS_HODE = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"


# ------------------------------------------------------------- hjelpere

def _falsk_ots(*args: str) -> subprocess.CompletedProcess:
    """`ots stamp <fil>` uten nett: hodet, versjon 1, sha256-operasjonen
    og summen av fila, slik `havbruksfond.ots_sum()` leser dem."""
    assert args[0] == "stamp"
    sti = Path(args[1])
    sha = hashlib.sha256(sti.read_bytes()).digest()
    Path(f"{sti}.ots").write_bytes(OTS_HODE + b"\x01\x08" + sha + b"\xf0ventende")
    return subprocess.CompletedProcess(list(args), 0, "", "")


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    maskin = tmp_path / "maskin"
    maskin.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(anslag, "MASKIN_DIR", maskin)
    monkeypatch.setattr(anslag, "FORSEGLINGER", maskin / "forseglinger.tsv")
    monkeypatch.setattr(stempel, "ots", _falsk_ots)
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", lambda: ("c0de" * 10, "ja"))
    return tmp_path


def _skriv(kilde: str, dato: dt.date, rader: dict[str, dict[str, str]]):
    """Ett snapshot: {entity_id: {felt: verdi}}."""
    obs = [Observation(entity_id=e, entity_type="lokalitet", entity_name=f"L{e}",
                       field=f, value=v, source=kilde, observed_at=dato.isoformat())
           for e, felt in rader.items() for f, v in felt.items()]
    obs = [replace(o, fetched_at="2026-11-10T12:00:00+00:00", source_version="1",
                   raw_hash="h", utvalg="{}") for o in obs]
    snapshot.write(obs, dato.isoformat())


def _uke(d: dt.date, brakklagt: dict[str, str] | None = None,
         lus: str = "0.1", lokaliteter=("11", "12", "13", "14", "15", "16")):
    """Lusetall og sjøtemperatur for én uke, seks lokaliteter."""
    brakklagt = brakklagt or {}
    _skriv("lusetall", d, {e: {"voksne_hunnlus": lus, "lus_er_rapportert": "True",
                               "brakklagt": brakklagt.get(e, "False"), "har_pd": "False"}
                           for e in lokaliteter})
    _skriv("sjotemperatur", d, {e: {"lusegrense": "0.5", "sjotemperatur": "9.0",
                                    "temperatur_er_rapportert": "True"}
                                for e in lokaliteter})


def _akvakultur(d: dt.date, po: str):
    _skriv("akvakultur", d, {e: {"prodomraade_kode": po}
                             for e in ("11", "12", "13", "14", "15", "16")})


def _grunnlag():
    """Ukene T−5 … T−4 og PO-koblingen før og etter T."""
    for k in (5, 4):
        _uke(T - dt.timedelta(weeks=k))
    _akvakultur(dt.date(2026, 11, 2), "2")
    _akvakultur(dt.date(2026, 11, 16), "7")     # etter utstedelsen: skal ikke brukes


# ---------------------------------------------- det som ikke skal endre seg

def test_r6_modulen_er_fila_backtesten_ble_laget_med():
    assert anslag.sha256(anslag.R6_STI) == anslag.R6_SHA256
    registrering = (paths.ROT / "predictions" / "maskin" / "FORHANDSREGISTRERING.md")
    assert anslag.R6_SHA256 in registrering.read_text(encoding="utf-8")


def test_en_endret_modul_regner_ikke(monkeypatch):
    monkeypatch.setattr(anslag, "R6_SHA256", "0" * 64)
    with pytest.raises(SystemExit, match="ikke den som er registrert"):
        anslag.modulen()


def _forseglet(sti: Path) -> bool:
    ots = Path(f"{sti}.ots")
    return ots.exists() and havbruksfond.ots_sum(ots.read_bytes()) == anslag.sha256(sti)


def test_forhandsregistreringen_er_den_som_ble_stemplet():
    assert _forseglet(paths.ROT / "predictions" / "maskin" / "FORHANDSREGISTRERING.md")


def test_ukefilene_i_repoet_er_forseglet_og_fort():
    """En forseglet ukefil røres aldri. Endres den, stemmer ikke summen."""
    maskin = paths.ROT / "predictions" / "maskin"
    tsv = maskin / "forseglinger.tsv"
    ført = tsv.read_text(encoding="utf-8") if tsv.exists() else ""
    for sti in sorted(maskin.glob("*.yml")):
        assert anslag.uke_fra_filnavn(sti.name), f"{sti.name} er ikke en ukefil"
        assert _forseglet(sti), f"{sti.name}: summen i .ots er ikke fila"
        assert f"\t{sti.name}\t{anslag.sha256(sti)}\t" in ført


def test_maskinfilene_er_utenfor_de_manuelle_prediksjonene():
    """core.predictions og forsegl.py leser predictions/*.yml. Ukefilene
    ligger én mappe ned og har et annet format; de skal ikke valideres som
    manuelle anslag eller inn i SEGL.txt."""
    alle = {p.resolve() for p in predictions._filer()} | {p.resolve() for p in forsegl._filer()}
    assert not any("maskin" in p.parts for p in alle)


# ------------------------------------------------------------ regningen

def test_anslaget_er_r6s_rader_for_uke_T(monkeypatch):
    """regn_ut() kaller R6s funksjoner med siste uke T+3 og T+4 og tar ut
    radene med i == T. Den regner ikke selv."""
    t = anslag.r6.wi(T)
    kall = {}

    def k_hasard(p, siste_wi):
        kall["k_hasard"] = siste_wi
        return [{"i": i, "po": "2", "y": 0, "a": 3, "b": 4, "m": m}
                for i, m in ((t - 1, 9.0), (t, 1.23456), (t + 1, 8.0))], {}

    def k_sesong(serie, kol, siste_wi, gap, klipp, foran=4):
        kall["k_sesong"] = (kol, siste_wi, gap, klipp, foran)
        return [{"i": t, "po": "2", "y": None, "a": 0.2, "b": None, "m": 0.25}], {}

    p = pl.DataFrame({"wi": [t - 4, t - 4, t - 4], "po": ["2", "2", "2"],
                      "brakklagt": ["False", "False", "True"]})
    serie = pl.DataFrame({"po": ["2"], "wi": [t - 4], "n_lus": [7]})
    monkeypatch.setattr(anslag.r6, "lokalitetspanel", lambda data: p)
    monkeypatch.setattr(anslag.r6, "po_ukeserie", lambda p_: serie)
    monkeypatch.setattr(anslag.r6, "k_hasard", k_hasard)
    monkeypatch.setattr(anslag.r6, "k_sesong", k_sesong)

    res = anslag.regn_ut({}, T)
    assert kall == {"k_hasard": t + 3, "k_sesong": ("K6", t + 4, 8, (0.0, None), 4)}
    assert res["K2"]["2"] == {"m": 1.23456, "a": 3, "b": 4, "lokaliteter": 2}
    assert res["K6"]["2"] == {"m": 0.25, "a": 0.2, "b": None, "lokaliteter": 7}


def _data_dict() -> dict:
    """Et panel som R6s les_alt() ville gitt: seks lokaliteter i PO 2 med
    lus 0,1 hver uke fra 2016-12-26 til uke T−4, alle aktive. Lokalitet 11
    brakklegges i uke T−5 og lokalitet 12 i uke T−50."""
    uker = []
    d = dt.date(2016, 12, 26)
    while d <= K:
        uker.append(d)
        d += dt.timedelta(weeks=1)
    lus, sjo = [], []
    for d in uker:
        for e in ("11", "12", "13", "14", "15", "16"):
            brakk = ((e == "11" and d == T - dt.timedelta(weeks=5))
                     or (e == "12" and d == T - dt.timedelta(weeks=50)))
            lus.append({"dato": d.isoformat(), "entity_id": e, "voksne_hunnlus": "0.1",
                        "lus_er_rapportert": "True", "brakklagt": str(brakk),
                        "har_pd": "False"})
            sjo.append({"dato": d.isoformat(), "entity_id": e, "lusegrense": "0.5",
                        "sjotemperatur": "9.0", "temperatur_er_rapportert": "True"})
    return {"lus": pl.DataFrame(lus), "sjo": pl.DataFrame(sjo),
            "lok_po": {e: "2" for e in ("11", "12", "13", "14", "15", "16")}}


def test_regn_ut_med_r6s_funksjoner_paa_et_kjent_panel():
    res = anslag.regn_ut(_data_dict(), T)
    k2, k6 = res["K2"]["2"], res["K6"]["2"]
    # Ingen brakklegging i trening: hasarden er null overalt.
    assert k2["m"] == 0.0
    assert (k2["a"], k2["b"], k2["lokaliteter"]) == (1, 1, 6)
    # Flatt lusenivå: sesongen endrer ingenting.
    assert round(k6["m"], 6) == 0.1 and k6["a"] == pytest.approx(0.1)
    assert k6["b"] == pytest.approx(0.1) and k6["lokaliteter"] == 6
    assert res["K6"].get("1", {}).get("m") is None


def test_merknaden_sier_hvilken_uke_som_mangler():
    m = anslag._merknad("K6", {"m": None, "a": None, "b": 0.1, "lokaliteter": 4}, T)
    assert m == ("skåres ikke: referanse a mangler (færre enn 5 lokaliteter med lusetall "
                 "og lusegrense i uke 2026-W42); anslaget mangler (det bygger på referanse a)")
    m = anslag._merknad("K6", {"m": 0.1, "a": 0.1, "b": None, "lokaliteter": 5}, T)
    assert m == ("skåres ikke: referanse b mangler (færre enn 5 lokaliteter med lusetall "
                 "og lusegrense i uke 2025-W50)")
    m = anslag._merknad("K6", {"m": None, "a": 0.1, "b": 0.1, "lokaliteter": 9}, T)
    assert m == "skåres ikke: anslaget mangler (ingen sesongverdi for PO-en)"
    assert anslag._merknad("K2", {"m": 0.0, "a": 0, "b": 0, "lokaliteter": 0}, T) == ""


# ------------------------------------------------------------ lesingen

def test_lesingen_stopper_ved_uke_T_minus_4(isolert):
    _grunnlag()
    _uke(T - dt.timedelta(weeks=3), lus="9.9")     # finnes, men er etter T−4
    logg = anslag.kl.Kjoringslogg("prove", isolert / "logg")
    data = anslag.les_panel(logg, anslag.FORSTE, K.isoformat(), anslag.akvakultur_dato(T))
    assert data["lus"]["dato"].max() == K.isoformat()
    assert "9.9" not in data["lus"]["voksne_hunnlus"].to_list()
    assert set(data["lok_po"].values()) == {"2"}        # koblingen fra 02.11, ikke 16.11


# ------------------------------------------------------- kommandoen

def _lag(isolert, *args, naa=NAA) -> int:
    return anslag.main(["--forsegl", *args], naa=naa)


def test_ukefila_skrives_forsegles_og_fores(isolert, capsys):
    _grunnlag()
    assert _lag(isolert) == 0
    sti = anslag.MASKIN_DIR / "2026-46.yml"
    innhold = yaml.safe_load(sti.read_text(encoding="utf-8"))
    assert innhold["uke"] == "2026-W46" and innhold["informasjon_til"] == K.isoformat()
    assert innhold["po_kobling"] == "akvakultur 2026-11-02"
    assert innhold["kode"] == "c0de" * 10
    assert innhold["typer"]["K6"]["klasse"] == "PRØVETYPE"
    assert innhold["typer"]["K2"]["aapningsdato"] == "2026-12-28"
    assert innhold["typer"]["K6"]["aapningsdato"] == "2027-01-04"
    assert innhold["typer"]["K2"]["lokaliteter"].startswith("aktive lokaliteter")
    rader = innhold["prediksjoner"]
    assert len(rader) == 26 and len({r["id"] for r in rader}) == 26
    assert {r["klasse"] for r in rader if r["type"] == "K6"} == {"PRØVETYPE"}
    assert "PRØVETYPE" in sti.read_text(encoding="utf-8").splitlines()[0]
    assert _forseglet(sti)
    linje = anslag.FORSEGLINGER.read_text(encoding="utf-8").splitlines()[1].split("\t")
    assert linje[:4] == ["2026-W46", "2026-46.yml", anslag.sha256(sti), "2026-11-10T20:00:00Z"]


def test_ukefila_lages_aldri_paa_nytt(isolert):
    _grunnlag()
    assert _lag(isolert) == 0
    sti = anslag.MASKIN_DIR / "2026-46.yml"
    for_ = sti.read_bytes(), anslag.FORSEGLINGER.read_bytes()
    _uke(K, lus="5.0")                                # en ny versjon av uke T−4
    assert _lag(isolert, naa=NAA + dt.timedelta(hours=1)) == 0
    assert (sti.read_bytes(), anslag.FORSEGLINGER.read_bytes()) == for_


def test_en_uke_lages_bare_i_uka_den_gjelder(isolert):
    _grunnlag()
    assert _lag(isolert, naa=dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.timezone.utc),
                *["--uke", "2026-W46"]) == 2
    assert _lag(isolert, *["--uke", "2026-W45"]) == 2
    assert not list(anslag.MASKIN_DIR.glob("*.yml"))


def test_uten_uke_T_minus_4_lages_ingenting(isolert):
    _uke(T - dt.timedelta(weeks=5))
    _akvakultur(dt.date(2026, 11, 2), "2")
    assert _lag(isolert) == 2
    assert not list(anslag.MASKIN_DIR.glob("*.yml"))


def test_fristen_gjelder_ogsaa_stempelet(isolert):
    """En ukefil som ble skrevet, men ikke stemplet i uka, er tapt."""
    _grunnlag()
    assert anslag.main([], naa=NAA) == 0
    sti = anslag.MASKIN_DIR / "2026-46.yml"
    assert anslag.forsegl(sti, T, dt.datetime(2026, 11, 16, 0, 1, tzinfo=dt.timezone.utc)) == 2
    assert not Path(f"{sti}.ots").exists()


def test_kode_som_ikke_er_pushet_lager_ikke_anslag(isolert, monkeypatch):
    _grunnlag()

    def nekt():
        raise kodeproveniens.IkkeSporbar("HEAD finnes ikke på origin/main")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", nekt)
    assert _lag(isolert) == 2
    assert not list(anslag.MASKIN_DIR.glob("*.yml"))


def test_torrkjoring_skriver_ingenting(isolert, capsys):
    _grunnlag()
    assert anslag.main(["--torrkjor", "--uke", "2026-W46"],
                       naa=dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc)) == 0
    assert "MASKINANSLAG FOR UKE 2026-W46" in capsys.readouterr().out
    assert not list(anslag.MASKIN_DIR.iterdir())
