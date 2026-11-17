"""Maskinanslagene: anslag.py og R6-modulen (økt 8). Skåreren: test_skaar_anslag.py.

Prøvene rører ikke ekte data. `isolert` flytter snapshotene og begge
mappene med ukefiler (kodrepoets og datarepoets predictions/maskin) til
tmp, og `ots` byttes ut med en som skriver en OTS-fil med riktig hode og
sum, uten nett.

Det som prøves mot repoene selv (ikke tmp), er det som ikke skal kunne
endre seg: R6s modul, forhåndsregistreringen med tillegget, og de
forseglede ukefilene begge steder. Datarepoets mappe prøves når repoet
står ved siden av (lokalt og i porten); i kodrepoets Actions finnes den
ikke, og `anslag.mapper()` gir da bare kodrepoets.
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
    """Snapshotene og begge mappene i tmp. Grensa flyttes til prøvenes
    uke, så uke 46 går veien jobben går fra uke 48: ukefila havner i
    datarepoets mappe, og kodrepoets står tom."""
    kode = tmp_path / "kode" / "predictions" / "maskin"
    data = tmp_path / "data" / "predictions" / "maskin"
    kode.mkdir(parents=True)
    data.mkdir(parents=True)
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(anslag, "KODE_MASKIN", kode)
    monkeypatch.setattr(anslag, "MASKIN_DIR", data)
    monkeypatch.setattr(anslag, "FORSTE_I_DATAREPOET", T)
    monkeypatch.setattr(anslag, "KODE_UKER", ())
    monkeypatch.setattr(stempel, "ots", _falsk_ots)
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", lambda: ("c0de" * 10, "ja"))
    return tmp_path


EKTE_DATAREPO = paths.ROT.parent / "havbruk-radar-data"


@pytest.fixture
def ekte(monkeypatch):
    """De ekte mappene, for prøvene som holder de forseglede filene.

    tests/conftest.py peker HAVBRUK_DATA_DIR på en engangsmappe, så
    datarepoets mappe må pekes ut her. Den står ved siden av kodrepoet
    lokalt og i porten. I kodrepoets Actions finnes den ikke, og da er
    kodrepoets mappe den eneste, som uten HAVBRUK_DATA_DIR. Gir True når
    datarepoet er med."""
    monkeypatch.setattr(anslag, "MASKIN_DIR",
                        EKTE_DATAREPO / "predictions" / "maskin"
                        if EKTE_DATAREPO.exists() else anslag.KODE_MASKIN)
    return EKTE_DATAREPO.exists()


def _logg() -> Path:
    return anslag.forseglingslogg(anslag.MASKIN_DIR)


def _flytt_til_kodrepoet(navn: str) -> None:
    """Ukefila, stempelet og loggen fra datarepoets mappe til kodrepoets,
    slik uke 46 og 47 ligger: forseglet, og utenfor det jobben skriver."""
    for n in (navn, f"{navn}.ots"):
        (anslag.MASKIN_DIR / n).rename(anslag.KODE_MASKIN / n)
    _logg().rename(anslag.forseglingslogg(anslag.KODE_MASKIN))


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


def test_tillegget_er_det_som_ble_stemplet():
    """Tillegget sier hvor ukefilene ligger fra uke 48. Det er stemplet før
    første uke i datarepoet, og røres ikke etterpå."""
    assert anslag.TILLEGG
    for navn in anslag.TILLEGG:
        assert _forseglet(paths.ROT / "predictions" / "maskin" / navn), navn


def _forte(maskin: Path) -> list[list[str]]:
    tsv = anslag.forseglingslogg(maskin)
    return [linje.split("\t") for linje in
            (tsv.read_text(encoding="utf-8").splitlines()[1:] if tsv.exists() else [])]


def test_forseglede_ukefiler_er_uendret(ekte):
    """En stemplet ukefil røres aldri, i noen av de to mappene. Hver linje
    i forseglinger.tsv skal fortsatt stemme: fila har summen som ble ført,
    `.ots` er stemplet for den summen, og `.ots`-fila er den samme. En
    ukefil UTEN `.ots` er lov: stempelet kan ha feilet i jobben, og neste
    kjøring samme uke stempler den. Den teller ikke før det, og
    skaar_anslag.py fører den under ikke_tellende."""
    for maskin in anslag.mapper():
        hvor = anslag.repo(maskin / "x")
        fort = set()
        for uke, fil, sha, stemplet, ots_sha in _forte(maskin):
            sti = maskin / fil
            assert anslag.isouke(anslag.uke_fra_filnavn(fil)) == uke, (hvor, fil)
            assert anslag.sha256(sti) == sha, f"{hvor}: {fil} er endret etter at den ble stemplet"
            ots = Path(f"{sti}.ots")
            assert havbruksfond.ots_sum(ots.read_bytes()) == sha, f"{hvor}: {ots.name} gjelder ikke fila"
            assert anslag.sha256(ots) == ots_sha, f"{hvor}: {ots.name} er byttet ut"
            fort.add(fil)
        for sti in sorted(maskin.glob("*.yml")):
            assert anslag.uke_fra_filnavn(sti.name), f"{hvor}: {sti.name} er ikke en ukefil"
            if Path(f"{sti}.ots").exists():
                assert sti.name in fort, (f"{hvor}: {sti.name} er stemplet, men ikke ført "
                                          f"i forseglinger.tsv")


def test_kodrepoet_har_uke_46_og_47_og_ingen_andre(ekte):
    """De to ukene som ble forseglet for hånd, ligger i kodrepoet og blir
    der. Ingen uke fra og med 48 gjør det: jobben skriver bare i
    datarepoet, og en ukefil her ville vært en uke som ligger to steder
    eller på feil sted."""
    assert anslag.KODE_UKER == ("2026-46.yml", "2026-47.yml")
    assert sorted(p.name for p in anslag.KODE_MASKIN.glob("*.yml")) == list(anslag.KODE_UKER)
    assert [linje[1] for linje in _forte(anslag.KODE_MASKIN)] == list(anslag.KODE_UKER)
    for navn in anslag.KODE_UKER:
        assert anslag.mappe(anslag.uke_fra_filnavn(navn)) == anslag.KODE_MASKIN
    assert anslag.mappe(dt.date(2026, 11, 23)) == anslag.MASKIN_DIR
    assert anslag.isouke(anslag.FORSTE_I_DATAREPOET) == "2026-W48"
    if ekte:
        assert anslag.repo(anslag.MASKIN_DIR / "2026-48.yml") == "havbruk-radar-data"
        assert not anslag.i_kodetreet(anslag.MASKIN_DIR)


def test_ingen_ukefil_ligger_i_feil_repo(ekte):
    """Mot de ekte mappene: hver ukefil ligger der `mappe()` sier, og ingen
    uke finnes begge steder."""
    sett: dict[str, str] = {}
    for maskin in anslag.mapper():
        for sti in sorted(maskin.glob("*.yml")):
            T = anslag.uke_fra_filnavn(sti.name)
            assert T is not None and anslag.mappe(T) == maskin, (
                f"{sti.name} ligger i {anslag.repo(sti)}")
            assert sti.name not in sett, f"{sti.name} finnes i {sett[sti.name]} og {anslag.repo(sti)}"
            sett[sti.name] = anslag.repo(sti)
            assert not anslag.feil_sted(T)


def test_hver_komplett_ots_er_et_oppgradert_stempel_for_fila(ekte):
    """`ots upgrade` rett på et stempel byttet det ut 11.11.2026, og prøven
    over ble rød. Oppgraderingen ligger derfor ved siden av, som
    `.komplett.ots`. Den skal være stemplet for samme fil og bære en
    blokk; ellers er navnet alt den har (docs/MALING-UKEJOBB.md, F0b.3)."""
    for maskin in anslag.mapper():
        for k in sorted(maskin.glob("*.komplett.ots")):
            fil = maskin / k.name.removesuffix(".komplett.ots")
            data = k.read_bytes()
            assert havbruksfond.ots_sum(data, k.name) == anslag.sha256(fil), k.name
            assert havbruksfond.ots_blokker(data, k.name), f"{k.name} bærer ingen blokk"


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
    linje = _logg().read_text(encoding="utf-8").splitlines()[1].split("\t")
    assert linje[:4] == ["2026-W46", "2026-46.yml", anslag.sha256(sti), "2026-11-10T20:00:00Z"]


def test_ukefila_havner_i_datarepoet_og_kodetreet_rores_ikke(isolert):
    _grunnlag()
    assert _lag(isolert) == 0
    assert sorted(p.name for p in anslag.MASKIN_DIR.iterdir()) == [
        "2026-46.yml", "2026-46.yml.ots", "forseglinger.tsv"]
    assert not list(anslag.KODE_MASKIN.iterdir())


def test_en_uke_som_ligger_i_kodrepoet_lages_ikke_i_datarepoet(isolert, capsys):
    """Samme uke to steder er to påstander om hva som ble forseglet."""
    _grunnlag()
    (anslag.KODE_MASKIN / "2026-46.yml").write_text("uke: 2026-W46\n", encoding="utf-8")
    assert _lag(isolert) == 2
    assert "ligger i havbruk-radar, men 2026-W46 hører hjemme i havbruk-radar-data" in (
        capsys.readouterr().out)
    assert not list(anslag.MASKIN_DIR.iterdir())


def test_en_forseglet_uke_i_kodrepoet_blir_staaende(isolert, monkeypatch):
    """Uke 47 i den ekte uka: fila ligger i kodrepoet og er stemplet. En
    kjøring samme uke lager ingenting, verken der eller i datarepoet."""
    _grunnlag()
    assert _lag(isolert) == 0
    _flytt_til_kodrepoet("2026-46.yml")
    monkeypatch.setattr(anslag, "FORSTE_I_DATAREPOET", T + dt.timedelta(weeks=1))
    for_ = {p.name: p.read_bytes() for p in anslag.KODE_MASKIN.iterdir()}
    assert _lag(isolert, naa=NAA + dt.timedelta(hours=1)) == 0
    assert {p.name: p.read_bytes() for p in anslag.KODE_MASKIN.iterdir()} == for_
    assert not list(anslag.MASKIN_DIR.iterdir())


def test_ingen_ukefil_skrives_i_kodetreet(isolert, monkeypatch, capsys):
    """En uke før grensa som ikke finnes, lages ikke: kodrepoet skrives
    aldri. Og uten et datarepo ved siden av (HAVBRUK_DATA_DIR mangler)
    er datamappa `data/` i kodetreet, og da skrives heller ingenting."""
    _grunnlag()
    monkeypatch.setattr(anslag, "FORSTE_I_DATAREPOET", T + dt.timedelta(weeks=1))
    assert _lag(isolert) == 2
    assert "det lages ingen ny ukefil i kodrepoet" in capsys.readouterr().out
    monkeypatch.setattr(anslag, "FORSTE_I_DATAREPOET", T)
    i_treet = paths.ROT / "finnes-ikke" / "predictions" / "maskin"
    monkeypatch.setattr(anslag, "MASKIN_DIR", i_treet)
    assert _lag(isolert) == 2
    assert "Sett HAVBRUK_DATA_DIR" in capsys.readouterr().out
    assert not i_treet.parent.parent.exists()
    assert not list(anslag.KODE_MASKIN.iterdir())


def test_ukefila_lages_aldri_paa_nytt(isolert):
    _grunnlag()
    assert _lag(isolert) == 0
    sti = anslag.MASKIN_DIR / "2026-46.yml"
    for_ = sti.read_bytes(), _logg().read_bytes()
    _uke(K, lus="5.0")                                # en ny versjon av uke T−4
    assert _lag(isolert, naa=NAA + dt.timedelta(hours=1)) == 0
    assert (sti.read_bytes(), _logg().read_bytes()) == for_


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
