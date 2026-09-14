"""Biomasselaget — nåtilstanden, datoen som ikke er observed_at, og
arten som ikke får forsvinne.

Tre ting testes fordi tre ting kan gå galt stille:

1. Ti lokaliteter har to arter. Slås de ikke sammen, kolliderer de i
   `snapshot.NOKKEL` og den ene forsvinner uten feilmelding.
2. `siste_rapport` er et ekte datofelt og en fristende `observed_at`.
   Den spenner 21 år over radene, og brukt som gyldighetsdato dikter
   den opp en proveniens.
3. Feltlåsen mot arkivet virker bare hvis den virker i BEGGE lag.
"""

import datetime as dt

import pytest

from sources import biomasselag
from sources.biomasselag import Biomasselag

# 2026-08-31 og 2010-01-31 i epoch-millisekunder, UTC.
AUG_2026 = 1788134400000
JAN_2010 = 1264896000000


def _rad(**over):
    d = {"objectid": 1635645, "loknr": 13143, "navn": "BONDEJORDA",
         "status_lokalitet": "AKTIV", "siste_rapport": AUG_2026,
         "har_fisk": "Ja", "art": "Laks"}
    d.update(over)
    return d


def _felt(obs, navn):
    return {o.entity_id: o.value for o in obs if o.field == navn}


# ------------------------------------------------- arten forsvinner ikke

def test_to_arter_paa_samme_lokalitet_blir_en_sammenslatt_verdi():
    """Målt 10.09.2026: ti lokaliteter har to rader, identiske i alt
    unntatt `art`. Med (entity_id, field) som nøkkel ville den ene falt
    bort i `unique(keep="first")`."""
    raw = [_rad(objectid=1, art="Regnbueørret"), _rad(objectid=2, art="Laks")]
    obs = list(Biomasselag().parse(raw, "2026-09-10"))

    assert _felt(obs, "arter_tilstede") == {"13143": "Laks;Regnbueørret"}
    assert _felt(obs, "antall_arter") == {"13143": "2"}


def test_sammenslaingen_er_sortert_og_ikke_radrekkefolgen():
    """Ellers ville en omstokking hos tjenesten sett ut som en endring."""
    a = list(Biomasselag().parse(
        [_rad(objectid=1, art="Laks"), _rad(objectid=2, art="Regnbueørret")],
        "2026-09-10"))
    b = list(Biomasselag().parse(
        [_rad(objectid=2, art="Regnbueørret"), _rad(objectid=1, art="Laks")],
        "2026-09-10"))
    assert _felt(a, "arter_tilstede") == _felt(b, "arter_tilstede")


def test_ingen_nokkelkollisjon_mellom_de_sammenslatte_radene():
    """Selve feilen testen over finnes for: (entity_id, field) skal være
    unik etter parse, ellers spiser snapshot.to_frame() en observasjon."""
    raw = [_rad(objectid=1, art="Kveite"), _rad(objectid=2, art="Torsk"),
           _rad(objectid=3, loknr=13337, art="Laks")]
    obs = list(Biomasselag().parse(raw, "2026-09-10"))
    nokler = [(o.entity_id, o.field) for o in obs]
    assert len(nokler) == len(set(nokler))


def test_verdiene_baeres_ordrett_og_oversettes_ikke():
    """«Ja»/«Nei» blir ikke bool, og artsnavnene blir ikke kategorier."""
    obs = list(Biomasselag().parse([_rad(art="Røye")], "2026-09-10"))
    assert _felt(obs, "har_fisk") == {"13143": "Ja"}
    assert _felt(obs, "arter_tilstede") == {"13143": "Røye"}


def test_ukjent_art_slipper_gjennom_uendret():
    """En ny artsverdi er noe vi vil SE, ikke noe et filter skal spise."""
    obs = list(Biomasselag().parse([_rad(art="Berggylt")], "2026-09-10"))
    assert _felt(obs, "arter_tilstede") == {"13143": "Berggylt"}


def test_uten_fisk_gir_ingen_art_men_et_null():
    """`har_fisk = Nei` medfører `art = null`. Feltet utelates da helt,
    men `antall_arter` sier 0 — ellers kan ikke et snapshot alene skille
    «ingen fisk» fra «arten manglet i svaret»."""
    obs = list(Biomasselag().parse([_rad(har_fisk="Nei", art=None)],
                                   "2026-09-10"))
    assert "arter_tilstede" not in {o.field for o in obs}
    assert _felt(obs, "antall_arter") == {"13143": "0"}
    assert _felt(obs, "har_fisk") == {"13143": "Nei"}


# --------------------------------------------- datoen som ikke er observed_at

def test_observed_at_er_kjoredatoen_og_ikke_siste_rapport():
    """Raden fra 2010 er ikke en observasjon vi gjorde i 2010. Den er en
    påstand laget gjør I DAG om at siste rapport kom i 2010."""
    obs = list(Biomasselag().parse([_rad(siste_rapport=JAN_2010)],
                                   "2026-09-10"))
    assert {o.observed_at for o in obs} == {"2026-09-10"}
    assert _felt(obs, "siste_rapport") == {"13143": "2010-01-31"}


def test_gjelder_for_er_kjoredatoen():
    assert Biomasselag().gjelder_for("2026-09-10") == "2026-09-10"


def test_rader_med_ulik_siste_rapport_havner_i_SAMME_snapshot():
    """112 distinkte verdier i feltet skal ikke gi 112 snapshots."""
    raw = [_rad(loknr=1, siste_rapport=AUG_2026),
           _rad(loknr=2, siste_rapport=JAN_2010)]
    obs = list(Biomasselag().parse(raw, "2026-09-10"))
    assert {o.observed_at for o in obs} == {"2026-09-10"}


def test_dato_forbeholdet_baeres_paa_hver_rad():
    """1b-3: et snapshot alene må kunne svare på hva observed_at betyr."""
    obs = list(Biomasselag().parse([_rad(), _rad(loknr=13337)], "2026-09-10"))
    b = _felt(obs, "dato_forbehold")
    assert set(b) == {"13143", "13337"}
    assert "HENTETIDSPUNKTET" in next(iter(b.values()))


def test_arts_forbeholdet_sier_at_mengde_ikke_finnes():
    obs = list(Biomasselag().parse([_rad()], "2026-09-10"))
    tekst = _felt(obs, "arts_forbehold")["13143"]
    assert "INGEN mengde" in tekst
    assert "44" in tekst


def test_dato_konverteres_i_utc_og_ikke_i_lokal_sone():
    """Naiv lokaltid ville flyttet 2026-08-31 til 30. eller 31. avhengig
    av hvor maskinen står."""
    assert biomasselag._dato(AUG_2026) == "2026-08-31"
    assert biomasselag._dato(JAN_2010) == "2010-01-31"
    assert biomasselag._dato(None) == ""
    assert biomasselag._dato("") == ""


# ------------------------------------------------------------ feltlåsen

# Et felt tjenesten kunne finne på å legge til i morgen. Arkivet ligger i
# git og er append-only — kommer dette inn, kan det ikke fjernes igjen.
NYTT = {"innehaver": "Ola Nordmann", "kontakt_epost": "ola@example.no"}


def test_lag1_slipper_bare_FELTER_gjennom():
    ut = biomasselag._rens(_rad(**NYTT))
    assert set(ut) <= set(biomasselag.FELTER)
    assert "Ola Nordmann" not in repr(ut)


def test_lag2_stopper_et_felt_lag1_slapp_forbi():
    """parse() er veien en ARKIVERT kropp kommer inn igjen på."""
    obs = list(Biomasselag().parse([_rad(**NYTT)], "2026-09-10"))
    assert "Ola Nordmann" not in repr(obs)
    assert {o.field for o in obs} & set(NYTT) == set()


def test_ukjent_felt_i_metadata_gir_advarsel_ikke_stillhet():
    """Låsen skal ikke gjøre en tjenesteendring usynlig."""
    felter = [{"name": n} for n in biomasselag.FELTER]
    felter += [{"name": "innehaver"}]
    assert biomasselag._ukjente_felter(felter) == ["innehaver"]


def test_kjente_utelatte_felter_gir_ikke_advarsel():
    felter = [{"name": n} for n in
              biomasselag.FELTER + biomasselag.KJENTE_UTELATTE]
    assert biomasselag._ukjente_felter(felter) == []


# ------------------------------------------------------------- advarsler

def test_ny_har_fisk_verdi_varsles_men_felles_ikke():
    a = biomasselag._vurder([_rad(har_fisk="Ukjent")], [])
    assert any("har_fisk har nye verdier" in x for x in a)


def test_har_fisk_nei_med_art_varsles():
    """Målt 10.09.2026 forekommer det ikke. Gjør det det, betyr feltene
    ikke lenger det docstringen sier."""
    a = biomasselag._vurder([_rad(har_fisk="Nei", art="Laks")], [])
    assert any("har_fisk=Nei OG" in x for x in a)


def test_intet_avvik_gir_ingen_advarsler():
    assert biomasselag._vurder([_rad(), _rad(har_fisk="Nei", art=None)], []) == []


# --------------------------------------------------------- published_at

def test_published_at_er_tom_uten_last_modified():
    """1b-7: standarden er «vet ikke», aldri hentetidspunktet. Verten
    sendte ingen slik header 10.09.2026."""
    assert biomasselag._utgitt({"etag": '"c5b049c3"'}) == ""
    assert biomasselag._utgitt({}) == ""


def test_published_at_leses_hvis_verten_begynner_a_sende_den():
    ut = biomasselag._utgitt({"Last-Modified": "Mon, 31 Aug 2026 06:00:00 GMT"})
    assert ut == "2026-08-31T06:00:00+00:00"


# ------------------------------------------------------------- rader ut

def test_rad_uten_loknr_slippes():
    """Uten lokalitetsnummer finnes ingen entitet å feste påstanden til."""
    obs = list(Biomasselag().parse([_rad(loknr=None)], "2026-09-10"))
    assert obs == []


def test_entity_type_er_lokalitet_som_i_akvakultur():
    """Kobling mot akvakultur og eierskap hviler på dette."""
    obs = list(Biomasselag().parse([_rad()], "2026-09-10"))
    assert {o.entity_type for o in obs} == {"lokalitet"}
    assert {o.entity_id for o in obs} == {"13143"}
