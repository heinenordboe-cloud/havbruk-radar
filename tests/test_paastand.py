"""Påstandsmodellen: kilde, gjelder, verdi og nivå — og alderen.

Konstruerte påstander, ikke ekte data: suiten skal aldri lese
datarepoet. Tallene er de MÅLTE fra 20.10.2026, slik at en prøve som
feiler peker på en lokalitet noen kan slå opp.
"""

import pytest

import paastand
from paastand import OPPGITT, UKE, VURDERT, Paastand


def _fisk(gjelder, verdi="Ja"):
    return Paastand("fisk", "biomasselag", gjelder, verdi, felt="har_fisk")


def _lus(uke, verdi="True"):
    return Paastand("lus", "lusetall", uke, verdi, nivaa=VURDERT,
                    felt="brakklagt", periode=UKE)


# ---- a: Hendneset (10204) ------------------------------------------------
#
# MÅLT 20.10.2026: biomasselaget sa «Ja, Kveite» med `siste_rapport`
# 2025-12-31, og siden sa «Fisk til stede» — ti måneder etter. Åtte
# lokaliteter med fisk=Ja hadde siste rapport før 1.8.2026.

def test_a_rapporten_fra_desember_er_ukjent_i_oktober():
    v = paastand.vis(_fisk("2025-12-31"), "2026-10-19", "ja")
    assert v["utgaatt"] is True
    assert v["vist"] == "ukjent"
    # DATOEN FOR SISTE RAPPORT står, ikke en gjetning om i dag.
    assert v["herkomst"]["gjelder"] == "2025-12-31"
    assert v["herkomst"]["vist"] == "31.12.2025"


def test_a_grensa_er_to_maaneder_for_biomasselaget():
    """62 dager: august står seg 19. oktober, juli gjør det ikke."""
    assert paastand.aldersgrense("biomasselag") == 62
    assert not paastand.utgaatt(_fisk("2026-08-31"), "2026-10-19")
    assert paastand.utgaatt(_fisk("2026-07-31"), "2026-10-19")
    # Akkurat på grensa står den seg: «eldre enn», ikke «like gammel».
    assert not paastand.utgaatt(_fisk("2026-08-18"), "2026-10-19")
    assert paastand.utgaatt(_fisk("2026-08-17"), "2026-10-19")


def test_lusetallets_etterslep_er_vaart_og_trekkes_fra():
    """Uke 39 er den ferskeste vi henter 19. oktober, med vilje. Uten
    fradraget ville hver lusepåstand vært utgått den dagen den ble hentet."""
    assert paastand.etterslep("lusetall") == 28
    assert paastand.alder(_lus("2026-09-21"), "2026-10-19") == 0
    assert not paastand.utgaatt(_lus("2026-09-07"), "2026-10-19")
    assert paastand.utgaatt(_lus("2026-08-31"), "2026-10-19")


def test_en_hendelse_foreldes_ikke():
    p = Paastand("overforing", "eierskap_historikk", "2008-01-04",
                 "2008-01-04", felt="journal_dato")
    assert paastand.aldersgrense("eierskap_historikk") is None
    assert not paastand.utgaatt(p, "2026-10-19")


def test_en_kilde_uten_aldersgrense_kaster_i_stedet_for_aa_gjette():
    p = Paastand("noe", "romming", "2026-10-01", "1")
    with pytest.raises(paastand.UkjentAldersgrense):
        paastand.utgaatt(p, "2026-10-19")


# ---- formen ---------------------------------------------------------------

def test_en_paastand_uten_kilde_er_ikke_en_paastand():
    with pytest.raises(ValueError):
        Paastand("fisk", "", "2026-09-30", "Ja")


def test_gjelder_maa_vaere_en_dato():
    with pytest.raises(ValueError):
        Paastand("fisk", "biomasselag", "september", "Ja")


def test_ukjent_nivaa_kastes():
    with pytest.raises(ValueError):
        Paastand("fisk", "biomasselag", "2026-09-30", "Ja", nivaa="sannsynlig")


def test_en_indikasjon_vises_aldri():
    """«Trolig slakting» er vår slutning. Den går aldri på nettstedet."""
    p = Paastand("slakting", "biomasselag", "2026-09-30", "trolig",
                 nivaa=paastand.INDIKASJON)
    with pytest.raises(paastand.Indikasjon):
        paastand.vis(p, "2026-10-19")


def test_herkomsten_er_utgiver_og_dato_ikke_en_setning():
    h = paastand.herkomst(_fisk("2026-09-30"))
    assert (h["kort"], h["vist"], h["gjelder"]) == \
        ("Fiskeridir.", "30.09.2026", "2026-09-30")
    hl = paastand.herkomst(_lus("2026-09-21"))
    assert (hl["kort"], hl["vist"]) == ("BarentsWatch", "uke 39, 2026")


def test_vis_beholder_kildens_verdi_ved_siden_av_den_viste():
    v = paastand.vis(_fisk("2026-09-30"), "2026-10-19", "ja")
    assert (v["verdi"], v["vist"], v["nivaa"], v["utgaatt"]) == \
        ("Ja", "ja", OPPGITT, False)
