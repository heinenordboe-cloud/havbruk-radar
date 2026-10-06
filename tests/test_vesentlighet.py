"""Vesentlig eller teknisk — én prøve per regel, og per grense.

Radene er konstruerte, i changeloggens form. `avledede` sendes inn, så
prøvene ikke spør kilderegisteret.
"""

import pytest

import vesentlighet as v
from vesentlighet import TEKNISK, VESENTLIG

AVLEDEDE = {("biomasselag", "antall_arter"): "har_fisk",
            ("akvakultur", "tillatelser_antall"): "tillatelser"}


def rad(kilde, felt, fra, til, endring="endret", eid="45140",
        dato="2026-10-05", forrige="2026-09-28"):
    return {"source": kilde, "field": felt, "old_value": fra,
            "new_value": til, "change_type": endring, "entity_id": eid,
            "observed_at": dato, "forrige_observed_at": forrige}


def klasser(*rader):
    return [k.klasse for k in v.klassifiser(rader, avledede=AVLEDEDE)]


# ---- vesentlig ----------------------------------------------------------

@pytest.mark.parametrize("r", [
    # eierskifte
    rad("eierskap", "eier_orgnr", "931064649", "935273781", eid="N-G-0066"),
    rad("eierskap", "eier_navn", "A AS", "B AS", eid="N-G-0066"),
    # tillatelse kom/gikk på lokaliteten
    rad("akvakultur", "tillatelser", "N-G-0066", "N-G-0066; N-G-0067"),
    rad("akvakultur", "tillatelser", "N-G-0066", None, endring="felt_borte"),
    rad("akvakultur", "tillatelser_trukket", None, "R-B-0003", endring="felt_ny"),
    rad("eierskap", "lokaliteter", "10110", "10110; 10113", eid="N-G-0066"),
    # kapasitet, alle slag
    rad("akvakultur", "kapasitet", "3120.0", "3600.0"),
    rad("akvakultur", "kapasitet_midlertidig", "3120.0", "3600.0"),
    rad("akvakultur", "kapasitet_enhet", "TN", "STK"),
    rad("eierskap", "kapasitet", "1261.0", "1274.0", eid="AG-F-0005"),
    # fisk til stede og arter
    rad("biomasselag", "har_fisk", "Ja", "Nei"),
    rad("biomasselag", "arter_tilstede", "Laks", "Laks; Regnbueørret"),
    rad("akvakultur", "arter", "SALMON", "SALMON; OTHER_FISH"),
    # klarering og status
    rad("akvakultur", "klareringstype", "TEMPORARY", "PERMANENT"),
    rad("akvakultur", "prodomraade_status", "rod", "gul"),
    rad("akvakultur", "versjon_status", "APPROVED", "PENDING"),
    # samdrift og samlokalisering
    rad("akvakultur", "har_samdrift", "True", "False"),
    rad("akvakultur", "har_samlokalisering", "False", "True"),
])
def test_vesentlige_endringer(r):
    assert klasser(r) == [VESENTLIG], r


@pytest.mark.parametrize("endring", ["ny", "borte"])
@pytest.mark.parametrize("kilde, felt", [
    ("eierskap", "eier_orgnr"), ("akvakultur", "navn"),
    # Også et felt som ellers er teknisk: oppføringen kom eller gikk.
    ("akvakultur", "versjon_gyldig_fra"),
])
def test_en_tillatelse_eller_lokalitet_som_kom_eller_gikk(kilde, felt, endring):
    assert klasser(rad(kilde, felt, None, "x", endring=endring)) == [VESENTLIG]


@pytest.mark.parametrize("fra, til", [
    ("False", "True"), ("True", "False"), (None, "True"), ("True", None)])
@pytest.mark.parametrize("felt", ["har_ila", "har_pd"])
def test_et_sykdomsflagg_som_settes_eller_oppheves(felt, fra, til):
    endring = "endret" if fra and til else ("ny" if til else "borte")
    assert klasser(rad("lusetall", felt, fra, til, endring=endring,
                       dato="2019-11-18")) == [VESENTLIG]


def test_et_felt_ingen_regel_nevner_er_vesentlig():
    """Standarden er å vise. Et felt ingen har tenkt på, skjules ikke."""
    assert klasser(rad("akvakultur", "kommune", "NAMSOS", "NAMSSKOGAN"),
                   rad("akvakultur", "et_nytt_felt", "a", "b")) \
        == [VESENTLIG, VESENTLIG]


# ---- koordinatene, og terskelen -----------------------------------------

def _flytting(fra, til, eid="45140"):
    return [rad("akvakultur", "breddegrad", str(fra[0]), str(til[0]), eid=eid),
            rad("akvakultur", "lengdegrad", str(fra[1]), str(til[1]), eid=eid)]


def test_de_seks_maalte_flyttingene_faller_paa_hver_sin_side():
    """De seks fra changeloggen 06.10.2026, med koordinatene derfra."""
    maalt = {
        "33097": ((70.04375, 20.94965), (70.043833, 20.9501), TEKNISK),
        "45029": ((66.243483, 12.294183), (66.2433, 12.293967), TEKNISK),
        "45140": ((66.629683, 13.10985), (66.629483, 13.110067), TEKNISK),
        "10974": ((66.400717, 12.4117), (66.40075, 12.4124), TEKNISK),
        "17177": ((61.89445, 5.34815), (61.895283, 5.345833), VESENTLIG),
        "12237": ((62.116567, 5.420717), (62.11595, 5.4173), VESENTLIG),
    }
    for eid, (fra, til, ventet) in maalt.items():
        assert klasser(*_flytting(fra, til, eid)) == [ventet, ventet], eid


def test_terskelen_er_100_meter_og_inkluderende():
    assert v.KOORDINAT_TERSKEL_M == 100.0
    # 0,0009 grader breddegrad er ~100,08 m; 0,00089 er ~98,96 m.
    over = _flytting((66.0, 13.0), (66.0009, 13.0))
    under = _flytting((66.0, 13.0), (66.00089, 13.0))
    assert klasser(*over) == [VESENTLIG, VESENTLIG]
    assert klasser(*under) == [TEKNISK, TEKNISK]


def test_bare_lengdegraden_regnes_ved_ekvator():
    """Uten breddegraden er avstanden ukjent; ekvator gir den lengste, og
    en usikker flytting havner heller over terskelen enn under."""
    # 0,0005 grader lengde er 55,6 m ved ekvator, 22 m på 66 grader nord.
    assert klasser(rad("akvakultur", "lengdegrad", "13.0", "13.0005")) == [TEKNISK]
    assert klasser(rad("akvakultur", "lengdegrad", "13.0", "13.001")) == [VESENTLIG]


def test_en_koordinat_som_ikke_er_et_tall_er_vesentlig():
    assert klasser(rad("akvakultur", "breddegrad", "66.6", "ukjent")) == [VESENTLIG]


# ---- teknisk ------------------------------------------------------------

@pytest.mark.parametrize("felt", [
    "versjon_gyldig_fra", "versjon_aarsak", "artsbegrensninger_antall"])
def test_tekniske_felt(felt):
    assert klasser(rad("akvakultur", felt, "a", "b")) == [TEKNISK]


def test_et_artsfelt_som_gjentar_fisk_til_stede_er_teknisk():
    """45140 den 05.10.2026: tre rader, og én av dem er hendelsen."""
    rader = [rad("biomasselag", "har_fisk", "Ja", "Nei"),
             rad("biomasselag", "arter_tilstede", "Laks", None,
                 endring="felt_borte"),
             rad("biomasselag", "antall_arter", "1", "0")]
    assert klasser(*rader) == [VESENTLIG, TEKNISK, TEKNISK]


def test_artsfeltet_ALENE_er_vesentlig():
    """Uten en fisk-endring samme uke gjentar det ingenting."""
    assert klasser(rad("biomasselag", "arter_tilstede", "Laks", None,
                       endring="felt_borte")) == [VESENTLIG]


def test_gjentakelsen_gjelder_samme_uke_og_samme_lokalitet():
    fisk = rad("biomasselag", "har_fisk", "Ja", "Nei", dato="2026-10-05")
    annen_uke = rad("biomasselag", "arter_tilstede", "Laks", None,
                    endring="felt_borte", dato="2026-09-21")
    annen_lok = rad("biomasselag", "arter_tilstede", "Laks", None,
                    endring="felt_borte", eid="12325")
    samme_uke = rad("biomasselag", "arter_tilstede", None, "Laks",
                    endring="felt_ny", dato="2026-10-07")
    assert klasser(fisk, annen_uke, annen_lok, samme_uke) == [
        VESENTLIG, VESENTLIG, VESENTLIG, TEKNISK]


@pytest.mark.parametrize("fra, til, endring", [
    (None, "False", "ny"), ("False", None, "borte")])
@pytest.mark.parametrize("felt", ["har_ila", "har_pd"])
def test_et_sykdomsflagg_som_bare_kom_inn_eller_falt_ut_er_teknisk(
        felt, fra, til, endring):
    """20797: «— → ikke satt» betyr at lokaliteten kom inn i kilden, ikke
    at noe skjedde med anlegget."""
    assert klasser(rad("lusetall", felt, fra, til, endring=endring,
                       dato="2018-12-17")) == [TEKNISK]


def test_et_avledet_felt_er_teknisk_bare_naar_grunnfeltet_endret_seg():
    sammen = [rad("akvakultur", "tillatelser", "A", "A; B"),
              rad("akvakultur", "tillatelser_antall", "1", "2")]
    alene = [rad("akvakultur", "tillatelser_antall", "1", "2")]
    assert klasser(*sammen) == [VESENTLIG, TEKNISK]
    assert klasser(*alene) == [VESENTLIG]


def test_grunnen_star_paa_hver_klasse():
    [k] = v.klassifiser(_flytting((66.0, 13.0), (66.0002, 13.0))[:1],
                        avledede=AVLEDEDE)
    assert k.klasse == TEKNISK and k.grunn.startswith("flyttet") and not k.vesentlig
