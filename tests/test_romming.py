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
