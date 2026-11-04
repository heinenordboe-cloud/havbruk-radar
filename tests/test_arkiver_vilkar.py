"""arkiver_vilkar.py: kroppen lagres uendret og én gang, med hash — og en
mistenkt kropp går i karantene i stedet for inn i serien.

Ingen nettverk: `_hent` byttes ut.
"""

import gzip
import hashlib
import json

import pytest

import arkiver_vilkar as ark
from core import raw as raw_arkiv
from core.karantene import synlig_tekst

# En vilkårsside slik reglene ser den: lang nok for en første versjon, og
# med hver parts kjennetegn (NLOD, opphavsrett, og fra 03.11.2026 CC BY 4.0,
# datautvinning, datamining og Oceanspace Media). Se ark.KJENNETEGN.
TEKST = ("Data er lisensiert under NLOD. Opphavsretten tilhører oss. " * 14
         + "CC BY 4.0. Ingen datautvinning eller datamining. Oceanspace Media. ")
SIDE = f"<html><script>x=1</script><p>{TEKST}</p></html>".encode()
FEILSIDE = (b"<!DOCTYPE html><html><head><title>Feil</title></head><body>"
            b"<h1>Tjenesten er midlertidig utilgjengelig</h1></body></html>")


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


def _sider(monkeypatch, svar):
    monkeypatch.setattr(ark, "_hent", lambda klient, url: svar(url))


def _logg(arkiv, dato):
    return json.loads((arkiv / "vilkar" / f"{dato}.logg.json").read_text())


def test_hver_side_lagres_uendret_med_hash(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (SIDE, "Thu, 02 Nov 2023 10:00:00 GMT"))

    assert ark.main(["--dato", "2026-10-06"]) == 0

    for part in ark.SIDER:
        [fil] = (arkiv / f"vilkar-{part}").glob("*.gz")
        assert fil.name == "2026-10-06.bin.gz"
        assert gzip.open(fil).read() == SIDE, "kroppen slik den kom"
    logg = _logg(arkiv, "2026-10-06")
    assert {r["part"] for r in logg} == set(ark.SIDER)
    assert all(r["sha256"] == hashlib.sha256(SIDE).hexdigest() for r in logg)
    assert all(r["published_at"] == "Thu, 02 Nov 2023 10:00:00 GMT" for r in logg)
    assert all(r["tekst_sha256"] == hashlib.sha256(TEKST.strip().encode()).hexdigest()
               for r in logg), "teksthashen ser bort fra skript og tagger"


def test_samme_kropp_neste_maaned_skrives_ikke_igjen(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-10-06"])
    assert ark.main(["--dato", "2026-11-02"]) == 0

    for part in ark.SIDER:
        assert len(list((arkiv / f"vilkar-{part}").glob("*.gz"))) == 1
    assert not any(r["ny"] for r in _logg(arkiv, "2026-11-02"))


def test_uten_last_modified_er_published_at_tom(arkiv, monkeypatch):
    """Aldri hentetidspunktet (CLAUDE.md 1b-7)."""
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-10-06"])
    assert all(r["published_at"] == "" for r in _logg(arkiv, "2026-10-06"))


def test_en_side_som_feiler_gir_rod_men_de_andre_arkiveres(arkiv, monkeypatch, capsys):
    def svar(url):
        if "brreg" in url:
            raise RuntimeError("403")
        return SIDE, ""
    _sider(monkeypatch, svar)

    assert ark.main(["--dato", "2026-10-06"]) == 1
    assert f"::error::Vilkårsarkivering: {ark.SIDER['brreg']}" \
           in capsys.readouterr().out
    assert not (arkiv / "vilkar-brreg").exists()
    assert len(list((arkiv / "vilkar-barentswatch").glob("*.gz"))) == 1


def test_hver_arkivert_kropp_har_kodeproveniens_i_loggen(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-10-06"])
    for r in _logg(arkiv, "2026-10-06"):
        assert r["kode_commit"] == "0" * 40      # conftest låser den
        assert r["kode_rent"] == "ja"
        assert r["fetched_at"].endswith("+00:00")


def test_kode_som_ikke_kan_spores_henter_ingenting(arkiv, monkeypatch, capsys):
    """Samme sperre som run.py, spurt FØR noe hentes."""
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("HEAD finnes ikke på origin/main")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)

    def hent(url):
        raise AssertionError("skulle ikke hentet noe")
    _sider(monkeypatch, hent)

    assert ark.main(["--dato", "2026-10-06"]) == 1
    assert "::error::Vilkårsarkiveringen startet ikke" in capsys.readouterr().out
    assert not arkiv.exists()


def test_torrkjoring_krever_ikke_sporbar_kode(arkiv, monkeypatch):
    """Den skriver ingen fil, så det finnes ingen fil å gjøre rede for."""
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("urent")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)
    _sider(monkeypatch, lambda url: (SIDE, ""))

    assert ark.main(["--torrkjor"]) == 0
    assert not arkiv.exists()


# ---------------------------------------------------------------- karantene
#
# MALING-DRIFT F1.1: feilside, tom liste, tom kropp og halv kropp ble alle
# lagret som nye kropper, med exit 0.

@pytest.mark.parametrize("kropp", [FEILSIDE, b"[]", b""])
def test_forste_versjon_under_minstelengden_gaar_i_karantene(arkiv, monkeypatch,
                                                              capsys, kropp):
    _sider(monkeypatch, lambda url: (kropp, ""))

    assert ark.main(["--dato", "2026-11-02"]) == 1
    for part in ark.SIDER:
        assert raw_arkiv.kropper(f"vilkar-{part}") == [], "ikke i serien"
        [fil] = (arkiv / f"vilkar-{part}" / "karantene").glob("*.gz")
        assert gzip.open(fil).read() == kropp, "men tatt vare på"
    logg = _logg(arkiv, "2026-11-02")
    assert all(r["status"] == "karantene" for r in logg)
    assert all(r["kode_commit"] == "0" * 40 for r in logg)
    assert "::error::Karantene (vilkar)" in capsys.readouterr().out


def test_under_halvparten_av_forrige_versjon_gaar_i_karantene(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-10-06"])
    halv = SIDE[: len(SIDE) // 2 - 40]
    _sider(monkeypatch, lambda url: (halv, ""))

    assert ark.main(["--dato", "2026-11-02"]) == 1
    [r] = [r for r in _logg(arkiv, "2026-11-02") if r["part"] == "brreg"]
    assert r["grunn"] == [f"synlig tekst {len(synlig_tekst(halv))} tegn, under 50% "
                          f"av forrige versjon ({len(TEKST.strip())} tegn)"]
    assert len(raw_arkiv.kropper("vilkar-brreg")) == 1, "forrige står alene"


def test_ingen_side_hentes_fra_lovdata():
    """Lovdata-hentingene er stoppet fra 04.11.2026."""
    assert not any("lovdata" in url for url in ark.SIDER.values())


def test_uten_kjennetegnet_gaar_kroppen_i_karantene(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-10-06"])
    uten = SIDE.replace(b"NLOD", b"en lisens")
    _sider(monkeypatch, lambda url: (uten, ""))

    assert ark.main(["--dato", "2026-11-02"]) == 1
    grunner = {r["part"]: r.get("grunn") for r in _logg(arkiv, "2026-11-02")}
    assert grunner["brreg"] == ["synlig tekst nevner ikke «NLOD»"]
    assert grunner["mattilsynet"] is None, \
        "Mattilsynets kjennetegn er opphavsretten, og den står der"


def test_en_lengre_versjon_med_kjennetegnet_er_ny(arkiv, monkeypatch):
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-10-06"])
    _sider(monkeypatch, lambda url: (SIDE + b"<p>Nytt punkt.</p>", ""))

    assert ark.main(["--dato", "2026-11-02"]) == 0
    assert all(r["ny"] for r in _logg(arkiv, "2026-11-02"))


def test_torrkjoring_sier_hva_som_ville_gaatt_i_karantene(arkiv, monkeypatch, capsys):
    _sider(monkeypatch, lambda url: (FEILSIDE, ""))
    assert ark.main(["--torrkjor"]) == 1
    assert "ville satt i karantene" in capsys.readouterr().out
    assert not arkiv.exists()


def test_kjennetegnene_er_maalt_for_hver_part():
    assert set(ark.KJENNETEGN) == set(ark.SIDER)


def test_andre_kjoring_samme_dag_faar_egen_logg(arkiv, monkeypatch):
    # Til 03.11.2026 ble loggen hoppet over når dagens fantes, og kroppene
    # fra kjøring nummer to sto uten fetched_at og kode_commit.
    _sider(monkeypatch, lambda url: (SIDE, ""))
    ark.main(["--dato", "2026-11-03"])
    _sider(monkeypatch, lambda url: (SIDE + b"<p>Nytt punkt.</p>", ""))
    assert ark.main(["--dato", "2026-11-03"]) == 0
    andre = json.loads((arkiv / "vilkar" / "2026-11-03.2.logg.json").read_text())
    assert all(r["ny"] and r["kode_commit"] == "0" * 40 for r in andre)
    assert all(r["ny"] for r in _logg(arkiv, "2026-11-03")), "den første står urørt"
