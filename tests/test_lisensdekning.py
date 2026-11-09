"""Lisenskjeden bærer produktene: hver kilde har en rad, og «salgbart» er
det radene gir.

R4 (2026-11-04) fant 23 arkivmapper med innhold og ingen rad, og fire
produkter ingen hadde holdt mot tabellen. Prøvene under feiler når en
kilde i produkttabellen mangler rad, når en kilde i `sources/` mangler
rad, og når statusen som står skrevet ikke er den radene gir.

To av prøvene trenger datarepoet (mappene og kroppene). De LESER det der
CLAUDE.md §8 sier det ligger, ved siden av kodrepoet, og ikke gjennom
`core.paths.DATA_DIR`, som conftest.py med vilje peker på en tom
engangsmappe. Uten datarepoet (Actions) hoppes de over;
verktoy/lisensdekning.py sier det samme mot HAVBRUK_DATA_DIR.
"""
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "verktoy"))
import lisensdekning as L  # noqa: E402
sys.path.pop(0)

TEKST = L.LISENSKJEDE.read_text(encoding="utf-8")
RADER = L.mapperader(TEKST)
PRODUKTER = L.produkter(TEKST)


def test_tabellene_finnes():
    assert len(RADER) > 40
    assert [p["produkt"] for p in PRODUKTER] == [
        "Ukentlig hendelsesvarsel", "Kommuneanalyse: havbruksfondet",
        "Dokumentert registeruttrekk", "Analyse på oppdrag"]


@pytest.mark.parametrize("p", PRODUKTER, ids=lambda p: p["produkt"])
def test_hver_kilde_i_produkttabellen_har_rad(p):
    assert p["kilder"], "produktet oppgir ingen kilder"
    uten = [n for n, _ in p["kilder"] if not L.rad_for(n, RADER)]
    assert not uten, f"{p['produkt']}: ingen rad i mappetabellen for {uten}"


@pytest.mark.parametrize("p", PRODUKTER, ids=lambda p: p["produkt"])
def test_status_per_kilde_er_radens(p):
    for navn, skrevet in p["kilder"]:
        assert skrevet == L.status(navn, RADER), navn


@pytest.mark.parametrize("p", PRODUKTER, ids=lambda p: p["produkt"])
def test_hver_kilde_har_bruk(p):
    """Bruk-kolonnen nevner de samme kildene i samme rekkefølge, og hver
    med en av de to brukene."""
    assert [n for n, _ in p["bruk"]] == [n for n, _ in p["kilder"]]
    for navn, bruk in p["bruk"]:
        assert bruk in L.BRUK, f"{navn}: «{bruk}» er ikke en av {L.BRUK}"


@pytest.mark.parametrize("p", PRODUKTER, ids=lambda p: p["produkt"])
def test_salgbart_bare_uten_ubelagte_kilder_som_gjengis(p):
    ok, hindre = L.salgbart(p, RADER)
    if ok:
        assert p["status"] == "**ja**"
    else:
        assert p["status"].startswith("**nei**")
        for n in hindre:
            assert f"`{n}`" in p["status"], f"{n} hindrer salg, men er ikke nevnt"


def _kommuneanalysen(tekst: str) -> dict:
    [p] = [p for p in L.produkter(tekst)
           if p["produkt"] == "Kommuneanalyse: havbruksfondet"]
    return p


def test_kommuneanalysen_er_salgbar_fordi_instruksen_ikke_gjengis():
    """Prøven over må kunne feile: settes instruksen til «gjengis», er den
    UBELAGTE kilden en som bærer visningen, og produktet stopper."""
    p = _kommuneanalysen(TEKST)
    assert L.salgbart(p, RADER) == (True, [])
    gjengitt = TEKST.replace(
        "`havbruksfondet:instrukser` fakta og metode, med lenke",
        "`havbruksfondet:instrukser` gjengis", 1)
    assert gjengitt != TEKST
    assert L.salgbart(_kommuneanalysen(gjengitt), RADER) == (
        False, ["havbruksfondet:instrukser"])


def test_kilde_uten_bruk_regnes_som_gjengitt():
    """«Vet ikke» åpner ikke for salg: uten bruk-kolonne stopper de to
    UBELAGTE kildene igjen."""
    p = dict(_kommuneanalysen(TEKST), bruk=[])
    assert L.salgbart(p, RADER) == (
        False, ["havbruksfondet:instrukser", "havbruksfondet:pressemeldinger"])


def test_nektet_stopper_uansett_bruk():
    assert L.hindrer("NEKTET", L.FAKTA)
    assert L.hindrer("MANGLER RAD", L.FAKTA)
    assert L.hindrer("UBELAGT", L.GJENGIS)
    assert not L.hindrer("UBELAGT", L.FAKTA)
    assert not L.hindrer("belagt", L.GJENGIS)


def test_en_kilde_uten_rad_feller_produktet():
    """Prøven over må kunne feile: en kilde ingen rad dekker."""
    tekst = TEKST.replace("`lusetall` belagt · `sjotemperatur`",
                          "`lusetall` belagt · `ny-fangst` belagt · `sjotemperatur`", 1)
    [varsel] = [p for p in L.produkter(tekst) if p["produkt"] == "Ukentlig hendelsesvarsel"]
    assert not L.rad_for("ny-fangst", RADER)
    assert L.salgbart(varsel, RADER) == (False, ["ny-fangst"])


def test_hver_kilde_i_sources_har_rad():
    uten = [k for k in L.kildenavn() if not L.rad_for(k, RADER)]
    assert not uten, f"kildenavn uten rad i mappetabellen: {uten}"


def test_ubelagt_i_tabellen_er_ubelagt_paa_kilden():
    """`Source.attribusjon = None` er det nettstedet holder ute; tabellen
    og kilden skal si det samme."""
    from core import registry
    from core.contract import attribusjon_per_kilde
    for navn, vilkaar in attribusjon_per_kilde(registry.discover()).items():
        assert (L.status(navn, RADER) == "UBELAGT") == (vilkaar is None), navn


@pytest.mark.parametrize("rad", RADER, ids=lambda r: r["navn"])
def test_hver_rad_baerer(rad):
    assert L.svakheter(rad) == []


def test_svakheter_ser_en_belagt_rad_uten_sitat_og_kropp():
    rad = {"navn": "x", "status": "belagt", "lest": "08.11.2026",
           "kommersiell bruk": "ja", "videresalg": "«ja»", "attribusjon": "«Kilde»",
           "vilkår, arkivert": "fiskeridir.no"}
    assert L.svakheter(rad) == ["«kommersiell bruk» har ikke vilkåret ordrett",
                                "ingen arkivert vilkårsside"]


DATAREPO = ROT.parent / "havbruk-radar-data" / "data"
trenger_data = pytest.mark.skipif(not (DATAREPO / "arkiv").is_dir(),
                                  reason="datarepoet ligger ikke ved siden av")


@trenger_data
def test_hver_arkivmappe_har_rad():
    uten = [m for m in L.arkivmapper(DATAREPO) if not L.rad_for(m, RADER)]
    assert not uten, f"arkivmapper uten rad i LISENSKJEDE.md: {uten}"


@trenger_data
@pytest.mark.parametrize("rad", RADER, ids=lambda r: r["navn"])
def test_sitatene_staar_i_kroppen_de_peker_paa(rad):
    assert L.sitater_i_kroppen(rad, DATAREPO) == []
