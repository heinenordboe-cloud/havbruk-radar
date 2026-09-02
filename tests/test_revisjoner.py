"""Revisjonssammendraget — analyse/revisjoner.py.

Tyngdepunktet ligger på de to tingene som faktisk kan gå galt uten at
noen ser det: at forsinkelsen regnes fra UTGIVELSE og ikke fra filnavn
(F14), og at verifiseringen ikke kan si «OK» om en rad den ikke fant.
"""

import datetime as dt

import polars as pl
import pytest

from analyse import revisjoner


def test_tall_taaler_komma_prosent_og_ulikhet():
    assert revisjoner._tall("1 234,5") == 1234.5
    assert revisjoner._tall("43 %") == 43.0
    assert revisjoner._tall("<1") == 1.0
    assert revisjoner._tall("moderat") is None
    assert revisjoner._tall(None) is None


def test_kategoriske_felter_trekker_ikke_medianen_ned():
    """`kategori` er «moderat», ikke et tall. Den skal FALLE UT av
    størrelsesmålet, ikke bli tvunget til 0."""
    rev = pl.DataFrame({
        "source": ["ekspertgruppen"] * 2,
        "entity_id": ["9", "9"],
        "entity_name": ["", ""],
        "field": ["kategori", "hi_smittepress_roc_indeks"],
        "old_value": ["lav", "10"],
        "new_value": ["moderat", "12"],
        "change_type": ["revidert"] * 2,
        "observed_at": ["2024-12-31"] * 2,
        "forrige_observed_at": ["2024-12-31"] * 2,
        "forrige_fetched_at": [""] * 2,
        "published_at": [""] * 2,
        "forrige_published_at": [""] * 2,
    })

    class TomTidslinje(revisjoner.Tidslinje):
        def spenn(self, kilde, dato):
            return None

    (rad,) = revisjoner.sammendrag(rev, TomTidslinje())
    assert rad["rader"] == 2
    # Bare den numeriske teller: |12-10|/10 = 0,2
    assert rad["numeriske"] == 1
    assert rad["median_endring"] == pytest.approx(0.2)


def test_forsinkelsen_regnes_av_utgivelse_ikke_av_lopenummer():
    """F14 i sammendraget.

    Wayback-kopien har det HØYESTE løpenummeret og den ELDSTE påstanden.
    Sorteres versjonene på filnavn, går forsinkelsen baklengs.
    """
    class Falsk(revisjoner.Tidslinje):
        def versjoner(self, kilde, dato):
            # v2 er utgitt FØR v1 — nøyaktig biomasse-tilfellet.
            return [
                ("2024-07-20T00:00:00+00:00", "2024-07-20T00:00:00+00:00", 2, None),
                ("2026-08-25T00:00:00+00:00", None, 1, None),
            ]

    t = Falsk()
    eldst, nyest, grense = t.spenn("biomasse", "2017-10-31")
    assert (nyest - eldst).days > 0, "forsinkelsen gikk baklengs"
    assert (nyest - eldst).days == 766
    # Den nyeste påstanden mangler published_at, så tallet er en ØVRE
    # GRENSE og skal merkes som det.
    assert grense is True


def test_kjent_utgivelse_paa_begge_sider_er_ikke_en_ovre_grense():
    class Falsk(revisjoner.Tidslinje):
        def versjoner(self, kilde, dato):
            return [
                ("2024-11-29T00:00:00+00:00", "2024-11-29T00:00:00+00:00", 1, None),
                ("2025-11-20T00:00:00+00:00", "2025-11-20T00:00:00+00:00", 2, None),
            ]

    _, _, grense = Falsk().spenn("ekspertgruppen", "2024-12-31")
    assert grense is False


def test_en_versjon_alene_gir_ingen_forsinkelse():
    """Én påstand er ikke en revisjon, og skal ikke gi et tall."""
    class Falsk(revisjoner.Tidslinje):
        def versjoner(self, kilde, dato):
            return [("2024-11-29T00:00:00+00:00", None, 1, None)]

    assert Falsk().spenn("x", "2024-12-31") is None


def _ramme(verdier: dict[str, str]) -> pl.DataFrame:
    return pl.DataFrame({
        "entity_id": ["9"] * len(verdier),
        "field": list(verdier),
        "value": list(verdier.values()),
    })


def _revrad(gammel: str, ny: str) -> pl.DataFrame:
    return pl.DataFrame({
        "source": ["ekspertgruppen"], "entity_id": ["9"], "entity_name": [""],
        "field": ["kategori"], "old_value": [gammel], "new_value": [ny],
        "change_type": ["revidert"], "observed_at": ["2024-12-31"],
        "forrige_observed_at": ["2024-12-31"], "forrige_fetched_at": [""],
        "published_at": [""], "forrige_published_at": [""],
    })


def _tidslinje(gammel_verdi, ny_verdi):
    class Falsk(revisjoner.Tidslinje):
        def versjoner(self, kilde, dato):
            return [
                ("2024-11-29T00:00:00+00:00", "2024-11-29T00:00:00+00:00", 1,
                 _ramme({"kategori": gammel_verdi} if gammel_verdi else {})),
                ("2025-11-20T00:00:00+00:00", "2025-11-20T00:00:00+00:00", 2,
                 _ramme({"kategori": ny_verdi} if ny_verdi else {})),
            ]
    return Falsk()


def test_verifisering_bekrefter_naar_verdiene_star_i_snapshotene():
    (v,) = revisjoner.verifiser(_revrad("lav", "moderat"), 1,
                                _tidslinje("lav", "moderat"))
    assert v["utfall"] == "OK"
    assert v["gammel_pa_disk"] == "lav"


def test_verifisering_feller_naar_gammel_verdi_ikke_star_der():
    """Kjernen i prøven: den skal ikke kunne si OK om en rad den ikke fant.

    F14 ga 1805 changelog-rader feil old_value. En verifisering som bare
    sjekket at det FANTES to snapshots ville bekreftet dem alle.
    """
    (v,) = revisjoner.verifiser(_revrad("lav", "moderat"), 1,
                                _tidslinje("hoy", "moderat"))
    assert v["utfall"] == "AVVIK"


def test_null_i_changeloggen_betyr_at_feltet_ikke_fantes():
    """PO9 2024: kilden hadde INGEN kategori, og fikk en.

    `old_value = "null"` skal pares med at feltet mangler i det eldste
    snapshotet — ikke med en verdi som bokstavelig talt er «null».
    """
    (v,) = revisjoner.verifiser(_revrad("null", "moderat"), 1,
                                _tidslinje(None, "moderat"))
    assert v["utfall"] == "OK"
    assert v["gammel_pa_disk"] is None


def test_tom_changelog_gir_tomt_sammendrag():
    assert revisjoner.sammendrag(pl.DataFrame()) == []
