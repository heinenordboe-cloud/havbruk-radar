"""Prediksjonsloggen.

To ting testes hardt, fordi de er hele verdien:

1. At formatet ikke slipper gjennom anslag som ikke kan feile.
2. At et anslag som traff MIDT i vinduet scores som treff, selv om
   verdien var tilbake der den startet da vinduet lukket.

Punkt to er grunnen til at `snapshot.les_mellom()` finnes. Leser man
bare endepunktene, dømmes en riktig spådd kapasitetsøkning som ble
reversert som bom.
"""

import polars as pl
import pytest

from core import predictions as pred
from core import snapshot

SCHEMA = [
    "entity_id", "entity_type", "entity_name", "field",
    "value", "source", "observed_at", "fetched_at",
    "source_version", "raw_hash",
]


@pytest.fixture
def rot(tmp_path, monkeypatch):
    """Isolerer både snapshots og resultatfiler til denne testen."""
    raw = tmp_path / "raw"
    monkeypatch.setattr(snapshot, "RAW_DIR", raw)
    monkeypatch.setattr(pred, "RESULTAT_DIR", tmp_path / "prediksjoner")
    return raw


def skriv_snapshot(raw, kilde, dato, entitet, felt, verdi):
    mappe = raw / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    pl.DataFrame([{
        "entity_id": entitet,
        "entity_type": "lokalitet",
        "entity_name": "Testlokalitet",
        "field": felt,
        "value": str(verdi),
        "source": kilde,
        "observed_at": dato,
        "fetched_at": "",
        "source_version": "1",
        "raw_hash": "",
    }]).select(SCHEMA).write_parquet(mappe / f"{dato}.parquet")


def p(**over):
    grunn = "Fem sesonger på slakteri: kapasitet flyttes før tillatelsen endres."
    base = {
        "id": "2026-01-01-1",
        "entitet": "10029",
        "kilde": "akvakultur",
        "felt": "kapasitet",
        "type": "endring",
        "retning": "opp",
        "terskel_prosent": 10,
        "vindu": {"fra": "2026-01-01", "til": "2026-03-01"},
        "grunnlag": grunn,
        "_fil": "2026-01-01.yml",
        "_fildato": "2026-01-01",
    }
    base.update(over)
    return base


# ------------------------------------------------------------- validering


def test_gyldig_prediksjon_gir_ingen_feil():
    assert pred.valider([p()]) == []


@pytest.mark.parametrize("felt", ["id", "entitet", "kilde", "felt", "grunnlag"])
def test_manglende_obligatorisk_felt_fanges(felt):
    feil = pred.valider([p(**{felt: ""})])
    assert any(felt in f for f in feil)


def test_for_kort_grunnlag_avvises():
    feil = pred.valider([p(grunnlag="tror det")])
    assert any("grunnlag" in f for f in feil)


def test_endring_uten_retning_avvises():
    feil = pred.valider([p(retning=None)])
    assert any("retning" in f for f in feil)


def test_endring_uten_terskel_avvises():
    feil = pred.valider([p(terskel_prosent=None)])
    assert any("terskel_prosent" in f for f in feil)


def test_verdi_uten_verdi_avvises():
    feil = pred.valider([p(type="verdi", verdi=None)])
    assert any("krever verdi" in f for f in feil)


def test_kan_ikke_spaa_fortiden():
    """Vinduet kan ikke starte før fila ble skrevet. Uten denne er hele
    treffraten verdiløs, fordi et anslag kan skrives etter utfallet."""
    feil = pred.valider([p(vindu={"fra": "2025-06-01", "til": "2026-03-01"})])
    assert any("før fila ble skrevet" in f for f in feil)


def test_vindu_maa_ha_varighet():
    feil = pred.valider([p(vindu={"fra": "2026-01-01", "til": "2026-01-01"})])
    assert any("etter vindu.fra" in f for f in feil)


def test_duplikat_id_fanges():
    feil = pred.valider([p(), p(entitet="10030")])
    assert any("går igjen" in f for f in feil)


def test_alle_feil_rapporteres_ikke_bare_forste():
    feil = pred.valider([p(id="", grunnlag="kort", type="tull")])
    assert len(feil) >= 3


# -------------------------------------------------------------- evaluering


def test_endring_opp_treffer(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "traff"
    assert "+20.0 %" in res["begrunnelse"][0]


def test_endring_opp_bommer(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1050)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "bom"


def test_treff_midt_i_vinduet_teller_selv_om_det_reverseres(rot):
    """Kjernepåstanden. Kapasiteten går opp 20 % i februar og tilbake i
    mars. Endepunktene alene ville sagt bom; anslaget var riktig."""
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)
    skriv_snapshot(rot, "akvakultur", "2026-02-25", "10029", "kapasitet", 1000)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "traff"


def test_retning_respekteres(rot):
    """Et kutt scorer ikke under en regel som spådde vekst."""
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 700)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "bom"


def test_verdi_treffer(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "prodomraade_status", "GRØNN")
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "prodomraade_status", "RØD")

    res = pred.evaluer("2026-03-02", [p(
        type="verdi", verdi="RØD", felt="prodomraade_status",
        retning=None, terskel_prosent=None,
    )])
    assert res["utfall"][0] == "traff"


def test_uendret_bommer_naar_noe_beveger_seg(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1300)

    res = pred.evaluer("2026-03-02", [p(
        type="uendret", terskel_prosent=5, retning=None,
    )])
    assert res["utfall"][0] == "bom"


def test_uten_utgangsverdi_er_uavklart_ikke_bom(rot):
    """Mangler målestokken, er ærlig uavklart riktigere enn å dømme."""
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "kan_ikke_avgjores"


def test_uten_observasjoner_i_vinduet_er_uavklart(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "kan_ikke_avgjores"


def test_utgangsverdi_null_sies_hoyt(rot):
    """Samme fella som `signals.py` har i dag: nullvernet mot divisjon
    spiser hendelsen. Her svares det uavklart i stedet for stille bom."""
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 0)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 500)

    res = pred.evaluer("2026-03-02", [p()])
    assert res["utfall"][0] == "kan_ikke_avgjores"
    assert "null" in res["begrunnelse"][0]


def test_apent_vindu_evalueres_ikke(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)

    assert pred.evaluer("2026-02-15", [p()]).height == 0


# -------------------------------------------------------------- resultater


def test_evalueres_bare_en_gang(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)

    forste = pred.evaluer("2026-03-02", [p()])
    pred.skriv(forste, "2026-03-02")

    assert pred.evaluer("2026-03-09", [p()]).height == 0


def test_skriving_overskriver_aldri(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)
    res = pred.evaluer("2026-03-02", [p()])

    a = pred.skriv(res, "2026-03-02")
    b = pred.skriv(res, "2026-03-02")
    assert a != b and a.exists() and b.exists()


def test_treffrate_teller_uavklarte_for_seg(rot):
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)
    pred.skriv(pred.evaluer("2026-03-02", [p()]), "2026-03-02")

    rate = pred.treffrate()
    assert rate["traff"][0] == 1
    assert rate["uavklart"][0] == 0


# ------------------------------------------------------- ekte prediksjonsfiler


def test_repoets_egne_prediksjoner_er_gyldige():
    """Kjører mot `predictions/` i repoet. Er den tom, er testen triviell
    — men den dagen du skriver et anslag, fanges formatfeilen i CI og
    ikke fire måneder senere når vinduet lukker."""
    assert pred.valider() == []


def test_ugyldig_anslag_evalueres_aldri(rot):
    """Regresjonstest for en feil testene ikke fanget, men en kjøring gjorde.

    Et anslag med formatfeil ble evaluert, skrevet til resultatfila og
    dermed markert som ferdig. Retting av YAML-en hjalp ikke — anslaget
    var borte for godt. Formatfeil skal gi tilsyn, ikke et resultat.
    """
    skriv_snapshot(rot, "akvakultur", "2026-01-01", "10029", "kapasitet", 1000)
    skriv_snapshot(rot, "akvakultur", "2026-02-01", "10029", "kapasitet", 1200)

    ugyldig = p(grunnlag="for kort")
    assert pred.valider([ugyldig]) != []
    assert pred.evaluer("2026-03-02", [ugyldig]).height == 0

    # og når den rettes, er den fortsatt evaluerbar
    assert pred.evaluer("2026-03-02", [p()]).height == 1
