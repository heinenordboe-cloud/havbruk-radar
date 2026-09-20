"""Rømming — og fritekstfeltene som IKKE hentes.

Tjenesten leverer to fritekstfelter skrevet av oppdretter. Målt
03.09.2026 inneholder de en navngitt privatperson med telefonnummer, en
navngitt saksbehandler og innlimt e-postkorrespondanse.

Fritekst kan ikke renses. Testene under passer på at feltene stoppes i
BEGGE lag, og at ingen framtidig endring slipper dem inn bakveien.
"""

import pytest

from sources import romming
from sources.romming import Romming


def _rad(**over):
    d = {"objectid": 1, "globalid": "{ABC-1}", "loknr": 12224,
         "navn": "ISANE", "rommingsdato": 1535977800000,
         "art": "Laks", "status": "Del 1",
         "antall_romt_estimert": "1-10", "antall_romt_fisk": None,
         "gjenfangst_iverksatt": "no", "gjenfangst_gjennomfort": "0",
         "fylke": "VESTLAND", "kommunenr": "4648"}
    d.update(over)
    return d


# ---------------------------------------------------- fritekst stoppes

FRITEKST = {
    "beskrivelse": "Svært stor spredning",
    "gjenfangst_beskrivelse": "Jan K Aarak tlf:90044345 er lokal fisker",
    "selskapsnavn": "NORDFJORD FORSØKSSTASJON AS",
}


def test_lag1_fjerner_fritekst_og_navn():
    """`_rens` kjører i fetch(), altså FØR arkivering."""
    ut = romming._rens(_rad(**FRITEKST))
    for forbudt in romming.FORBUDTE:
        assert forbudt not in ut
    assert "Jan K Aarak" not in repr(ut)
    assert "90044345" not in repr(ut)


def test_lag1_beholder_de_strukturerte_feltene():
    ut = romming._rens(_rad(**FRITEKST))
    for felt in ("loknr", "rommingsdato", "art", "antall_romt_estimert",
                 "gjenfangst_iverksatt"):
        assert felt in ut


def test_lag2_stopper_fritekst_som_lag1_slapp_forbi():
    """parse() er veien en ARKIVERT kropp kommer inn igjen på.

    Kroppen her er konstruert som om den var arkivert FØR filteret
    fantes — nøyaktig veien enhetsregisteret beskriver.
    """
    obs = list(Romming().parse([_rad(**FRITEKST)], "2018-12-31"))
    t = repr(obs)
    assert "Jan K Aarak" not in t
    assert "90044345" not in t
    assert "NORDFJORD" not in t
    for o in obs:
        assert o.field not in romming.FORBUDTE


def test_telefonnummer_i_fritekst_naar_aldri_en_observasjon():
    rad = _rad(gjenfangst_beskrivelse="Ring 90044345 for kontakt",
               beskrivelse="Kontaktperson Ola Nordmann, tlf 99887766")
    obs = list(Romming().parse([rad], "2018-12-31"))
    t = repr(obs)
    for forbudt in ("90044345", "99887766", "Ola Nordmann", "Kontaktperson"):
        assert forbudt not in t


def test_ingen_forbudt_felt_star_i_uttrekket():
    """FORBUDTE og UT skal ikke kunne overlappe. Uten denne testen ville
    et forbudt felt kunne legges til i UT ved et uhell."""
    assert not (set(romming.UT) & set(romming.FORBUDTE))
    assert not (set(romming.FELTER) & set(romming.FORBUDTE))


def test_selskapsnavn_lagres_ikke():
    """Ingen organisasjonsnummer finnes, og Brregs navnesøk er et
    relevanssøk som rangerer ENK blant treffene. «Vet ikke» betyr
    aldri «slipp gjennom» — heller ikke på feltnivå."""
    obs = list(Romming().parse([_rad(selskapsnavn="NOEN AS")], "2018-12-31"))
    assert all("selskap" not in o.field for o in obs)
    assert "NOEN AS" not in repr(obs)


# ------------------------------------------------------------ innholdet

def test_hendelsen_lander_i_sitt_eget_aar():
    rad = _rad(rommingsdato=1535977800000)   # 2018-09-03
    assert Romming().aar_i([rad]) == ["2018-12-31"]
    assert list(Romming().parse([rad], "2019-12-31")) == []
    assert list(Romming().parse([rad], "2018-12-31")) != []


def test_antall_lagres_ordrett_som_intervall():
    """«1-10» er kildens presisjon. Å gjøre den om til et tall ville
    vært vår presisjon på kildens vegne — samme regel som `_prosent`
    i ekspertgruppen."""
    obs = list(Romming().parse([_rad(antall_romt_estimert="Mer enn 10 000")],
                               "2018-12-31"))
    felt = {o.field: o.value for o in obs}
    assert felt["antall_romt_estimert"] == "Mer enn 10 000"


def test_forbeholdene_staar_paa_hver_rad():
    """Gjenfangst er JA/NEI, ikke en mengde. Parqueten skal bære det
    selv om den havner et annet sted (CLAUDE.md 1b-3)."""
    obs = list(Romming().parse([_rad()], "2018-12-31"))
    felt = {o.field: o.value for o in obs}
    assert "JA/NEI" in felt["gjenfangst_forbehold"]
    assert "INTERVALL" in felt["antall_forbehold"]


def test_globalid_er_noekkelen_ikke_lokalitet_og_dato():
    """To hendelser DELER lokalitet og dato i kilden (36817, 32457).
    Med det paret som nøkkel ville den ene overskrevet den andre."""
    a = _rad(globalid="{A}", loknr=36817, rommingsdato=1770732900000)
    b = _rad(globalid="{B}", loknr=36817, rommingsdato=1770732900000)
    obs = list(Romming().parse([a, b], "2026-12-31"))
    assert len({o.entity_id for o in obs}) == 2


def test_dato_er_utc_ikke_naiv():
    assert romming._dato(1535977800000) == "2018-09-03"
    assert romming._dato(None) == ""
    assert romming._dato("") == ""


def test_kilden_leser_aldri_klokka():
    k = Romming()
    assert k.gjelder_for("2026-09-03") == "2026-09-03"
    assert k.gjelder_for("2020-01-01") == "2020-01-01"


def test_rad_uten_noekkel_faller_ut():
    obs = list(Romming().parse([_rad(globalid=None, objectid=None)],
                               "2018-12-31"))
    assert obs == []


# ---- avkortet ArcGIS-svar: 200 OK som betyr «du spurte for bredt» -----
#
# MÅLT 19.09.2026 mot Biomasse-laget (1128 rader, maxRecordCount 2000):
#
#     resultRecordCount=1000, offset=0     1000 rader  exceededTransferLimit=True
#     resultRecordCount=1000, offset=1000   128 rader  (ikke satt)
#     resultRecordCount=3000, offset=0     1128 rader  (ikke satt)
#
# Så lenge SPENN ligger under tjenestens tak er en kort side ekte slutt.
# Senker tjenesten taket under SPENN, blir hver side kort OG flagget satt
# — og «kort side = siste side» mister resten i stillhet. Det er den
# stille motsatsen til pub-aquas 400, se sources/_arcgis.py.

from sources import _arcgis                                    # noqa: E402


def test_avkortet_side_med_flagg_kaster():
    """Motsigelsen: tjenesten ga færre rader enn vi ba om OG sier at det
    finnes mer. Å stoppe der ville mistet resten."""
    with pytest.raises(RuntimeError, match="exceededTransferLimit"):
        _arcgis.sjekk_avkorting({"exceededTransferLimit": True}, 500, 1000,
                                "romming", 0)


def test_full_side_med_flagg_er_normalt():
    """Vi ba om 1000, fikk 1000, og det finnes mer. Det er hver eneste
    ikke-siste side — en vakt som felte her ville felt hver kjøring."""
    _arcgis.sjekk_avkorting({"exceededTransferLimit": True}, 1000, 1000,
                            "romming", 0)


def test_kort_side_uten_flagg_er_ekte_slutt():
    """Den vanlige siste siden: 578 rader av 1000 for romming i dag."""
    _arcgis.sjekk_avkorting({}, 578, 1000, "romming", 0)
    _arcgis.sjekk_avkorting({"exceededTransferLimit": False}, 578, 1000,
                            "romming", 0)


def test_vakten_ligger_ETT_sted_for_begge_kildene():
    """`biomasselag` og `romming` pagineres likt, og prøven er den samme.
    To kopier er to steder å glemme den ene — formen F6 og F7 hadde."""
    import inspect

    from sources import biomasselag, romming

    for modul in (biomasselag, romming):
        kilde = inspect.getsource(modul)
        assert "_arcgis.sjekk_avkorting(" in kilde, modul.__name__
        assert "exceededTransferLimit" not in kilde.split('"""')[-1], (
            f"{modul.__name__} leser flagget selv — prøven skal ligge i "
            f"sources/_arcgis.py, ikke i kilden")


def test_romming_feller_et_avkortet_svar_ende_til_ende(monkeypatch):
    """Hele veien gjennom `fetch()`: et gyldig 200-svar som er avkortet.

    Før 19.09.2026 returnerte denne løkka pent med halve laget. Testen
    planter nøyaktig det svaret tjenesten ville gitt om `maxRecordCount`
    ble senket til 500, og krever at kilden nå faller på det.
    """
    class Svar:
        def __init__(self, d):
            self._d = d

        def json(self):
            return self._d

    rader = [{"attributes": {"objectid": i, "aar": 2026}} for i in range(500)]
    avkortet = {"features": rader, "exceededTransferLimit": True}
    monkeypatch.setattr(romming._http, "get",
                        lambda *a, **kw: Svar(avkortet))

    with pytest.raises(RuntimeError, match="avkortet"):
        Romming().fetch("2026-09-19")


def test_uten_vakten_ville_samme_svar_gaatt_stille(monkeypatch):
    """Kontrollen av kontrollen: med vakten slått av returnerer den
    samme løkka 500 rader og sier ingenting. Det var oppførselen fram
    til 19.09.2026, og det er grunnen til at vakten finnes."""
    class Svar:
        def __init__(self, d):
            self._d = d

        def json(self):
            return self._d

    rader = [{"attributes": {"objectid": i, "aar": 2026}} for i in range(500)]
    avkortet = {"features": rader, "exceededTransferLimit": True}
    monkeypatch.setattr(romming._http, "get",
                        lambda *a, **kw: Svar(avkortet))
    monkeypatch.setattr(romming._arcgis, "sjekk_avkorting",
                        lambda *a, **kw: None)

    ut = Romming().fetch("2026-09-19")
    assert len(ut) == 500, "uten vakten stopper løkka stille på halve laget"
