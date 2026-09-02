"""Kildeleddet — Stiens formel som ukentlig serie per produksjonsområde.

Fire ting testes hardt, fordi de er hele verdien:

1. At FULL faktisk er Stiens formel, regnet for hånd på et kjent tall.
2. At DELVIS ikke er kildeleddet, og ikke kan forveksles med det.
3. At N_fisk ALDRI ekstrapoleres — en uke uten dekket måned mangler.
4. At forbeholdet og formelen står PÅ RADEN (CLAUDE.md 1b-3).

Testene rører ikke ekte data. `conftest.py` flytter HAVBRUK_DATA_DIR til
en engangsmappe, og hver test flytter i tillegg `snapshot.RAW_DIR`.
"""

import datetime as dt

import polars as pl
import pytest

import kildeledd
from analyse import kjoringslogg
from core import snapshot

SCHEMA = [
    "entity_id", "entity_type", "entity_name", "field",
    "value", "source", "observed_at", "fetched_at",
    "source_version", "raw_hash",
]


@pytest.fixture
def rot(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    monkeypatch.setattr(snapshot, "RAW_DIR", raw)
    monkeypatch.setattr(kildeledd, "UT_DIR", tmp_path / "kildeledd")
    return raw


def skriv(raw, kilde, dato, rader, entity_type="lokalitet"):
    """rader: [(entity_id, field, value), ...]"""
    mappe = raw / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    pl.DataFrame([{
        "entity_id": e, "entity_type": entity_type, "entity_name": f"E{e}",
        "field": f, "value": str(v), "source": kilde, "observed_at": dato,
        "fetched_at": "", "source_version": "1", "raw_hash": "",
    } for e, f, v in rader]).select(SCHEMA).write_parquet(mappe / f"{dato}.parquet")


def grunnoppsett(raw, uker, *, po_kode="3", biomasse=None, lus=0.5, temp=10.0):
    """Én lokalitet i PO3, én uke-liste, valgfrie biomassemåneder."""
    skriv(raw, "akvakultur", "2026-01-05",
          [("100", "prodomraade_kode", po_kode),
           ("100", "prodomraade_navn", "Karmøy til Sotra")])
    for uke in uker:
        skriv(raw, "lusetall", uke,
              [("100", "lus_er_rapportert", "True"),
               ("100", "voksne_hunnlus", lus)])
        skriv(raw, "sjotemperatur", uke, [("100", "sjotemperatur", temp)])
    for maaned_slutt, antall in (biomasse or {}).items():
        skriv(raw, "biomasse", maaned_slutt,
              [(po_kode, "beholdning_antall", antall)],
              entity_type="produksjonsomraade")


def kjor(tmp_path, raw, fra=2020, til="2020-12-31"):
    logg = kjoringslogg.Kjoringslogg("test", tmp_path / "t.log")
    return kildeledd.bygg(logg, fra, til)


# ------------------------------------------------------- formelen

def test_full_er_stiens_formel_regnet_for_haand(rot, tmp_path):
    """N_fisk × lus × 0,17 × (T + 4,28)², på ett tall noen kan ettergå.

    lus = 0,5, T = 10 -> 0,5 × (14,28)² = 101,9592
    × 1 000 000 fisk × 0,17               = 17 333 064
    """
    grunnoppsett(rot, ["2020-06-01"], biomasse={"2020-06-30": 1_000_000})
    ramme = kjor(tmp_path, rot)

    full = ramme.filter(pl.col("serie") == "full")
    assert full.height == 1
    assert full["verdi"][0] == pytest.approx(0.5 * (10 + 4.28) ** 2 * 1_000_000 * 0.17)
    assert full["verdi"][0] == pytest.approx(17_333_064.0)
    assert full["n_fisk"][0] == 1_000_000
    assert full["enhet"][0] == "klekte nauplier per time"


def test_delvis_er_ikke_kildeleddet(rot, tmp_path):
    """Uten N_fisk OG uten 0,17. Blandes de to, er tallet 5,9x for lite
    eller millioner ganger for stort — og ingen av delene syns."""
    grunnoppsett(rot, ["2020-06-01"], biomasse={"2020-06-30": 1_000_000})
    delvis = kjor(tmp_path, rot).filter(pl.col("serie") == "delvis")

    assert delvis.height == 1
    assert delvis["verdi"][0] == pytest.approx(0.5 * (10 + 4.28) ** 2)
    assert delvis["n_fisk"][0] is None
    assert "ikke nauplier" in delvis["enhet"][0]   # enheten sier det selv
    assert "UTEN N_fisk" in delvis["formel"][0]


def test_konstantene_er_stiens_egne(rot, tmp_path):
    assert kildeledd.STIEN_K == 0.17
    assert kildeledd.STIEN_T0 == 4.28


# ------------------------------------------- ingen ekstrapolering

def test_uke_uten_dekket_maaned_mangler_i_full(rot, tmp_path):
    """Den bindende begrensningen. Juni har biomasse, juli har ikke —
    og juli skal da IKKE få junis tall båret videre."""
    grunnoppsett(rot, ["2020-06-01", "2020-07-06"],
                 biomasse={"2020-06-30": 1_000_000})
    ramme = kjor(tmp_path, rot)

    assert sorted(ramme.filter(pl.col("serie") == "full")["uke_mandag"]) == ["2020-06-01"]
    # DELVIS har begge: den trenger ikke N_fisk.
    assert sorted(ramme.filter(pl.col("serie") == "delvis")["uke_mandag"]) == \
        ["2020-06-01", "2020-07-06"]


def test_hull_fylles_ikke_med_gjennomsnitt(rot, tmp_path):
    """Mai og juli dekket, juni ikke. Juni skal mangle, ikke bli snittet."""
    grunnoppsett(rot, ["2020-05-04", "2020-06-01", "2020-07-06"],
                 biomasse={"2020-05-31": 1_000_000, "2020-07-31": 3_000_000})
    full = kjor(tmp_path, rot).filter(pl.col("serie") == "full")

    assert sorted(full["uke_mandag"]) == ["2020-05-04", "2020-07-06"]
    assert 2_000_000 not in full["n_fisk"].to_list()


def test_n_fisk_foeres_ikke_bakover(rot, tmp_path):
    """Biomasse finnes fra 2017-10. Uker før det har ingen FULL-verdi,
    uansett hvor nær de ligger."""
    grunnoppsett(rot, ["2017-09-25", "2017-10-02"],
                 biomasse={"2017-10-31": 1_000_000})
    full = kjor(tmp_path, rot, fra=2017, til="2017-12-31")

    assert sorted(full.filter(pl.col("serie") == "full")["uke_mandag"]) == ["2017-10-02"]


# -------------------------------------------- valget som er logget

def test_maanedsverdien_baeres_flatt_over_ukene(rot, tmp_path):
    """Alle uker i juni får junis beholdning — ikke en interpolasjon.

    Valget er dokumentert i `_n_fisk` og i beslutningsnotatet. Testen
    finnes for at det ikke skal kunne endres stille: en interpolasjon
    ville gitt fire ulike n_fisk her, og ingen av dem finnes hos
    Fiskeridirektoratet.
    """
    uker = ["2020-06-01", "2020-06-08", "2020-06-15", "2020-06-22"]
    grunnoppsett(rot, uker, biomasse={"2020-06-30": 1_000_000})
    full = kjor(tmp_path, rot).filter(pl.col("serie") == "full")

    assert full.height == 4
    assert full["n_fisk"].unique().to_list() == [1_000_000]
    assert full["aggregering"].unique().to_list() == [kildeledd.BAER_MAANED]


def test_uka_hoerer_til_mandagens_maaned(rot, tmp_path):
    """Uke 27/2020 begynner 29. juni og teller som JUNI, selv om fem av
    dens sju dager er i juli. Måneden leses av kildens egen observed_at."""
    grunnoppsett(rot, ["2020-06-29"],
                 biomasse={"2020-06-30": 1_000_000, "2020-07-31": 9_000_000})
    full = kjor(tmp_path, rot).filter(pl.col("serie") == "full")

    assert full["n_fisk_maaned"][0] == "2020-06"
    assert full["n_fisk"][0] == 1_000_000


# ------------------------------------ verdien står PÅ raden (1b-3)

def test_forbehold_og_formel_staar_paa_hver_rad(rot, tmp_path):
    """En parquet som havner på en annen maskin skal bære sin egen
    begrensning. Regel 1b-3: verdien som avgjør hva dataene BETYR,
    lagres SAMMEN med dem."""
    grunnoppsett(rot, ["2020-06-01"], biomasse={"2020-06-30": 1_000_000})
    ramme = kjor(tmp_path, rot)

    assert ramme.height > 0
    for rad in ramme.iter_rows(named=True):
        assert "N_fisk_PO" in rad["forbehold"]
        assert "sum_lok" in rad["forbehold"]
        assert rad["formel"]
        assert rad["stien_k"] == 0.17
        assert rad["stien_t0"] == 4.28
        assert rad["aggregering"] == kildeledd.BAER_MAANED


def test_skjemaet_er_eksplisitt_og_ikke_utledet(rot, tmp_path):
    """n_fisk er Int64 også når de første radene mangler den.

    Utledet skjema ville gjort kolonnetypen til en egenskap ved
    RADREKKEFØLGEN: en serie som starter i 2012 har 296 DELVIS-uker uten
    N_fisk foran seg, og polars leste den som Null og falt så over den
    første i64-en i 2017.
    """
    grunnoppsett(rot, ["2020-05-04", "2020-06-01"],
                 biomasse={"2020-06-30": 1_000_000})
    ramme = kjor(tmp_path, rot)

    assert ramme.schema["n_fisk"] == pl.Int64
    assert ramme.schema["verdi"] == pl.Float64
    assert list(ramme.columns) == list(kildeledd.SKJEMA)


# ------------------------------------------------ hva som telles med

def test_lokalitet_uten_rapportert_lus_telles_ikke(rot, tmp_path):
    skriv(rot, "akvakultur", "2026-01-05", [("100", "prodomraade_kode", "3"),
                                            ("200", "prodomraade_kode", "3")])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.5"),
           ("200", "lus_er_rapportert", "False"), ("200", "voksne_hunnlus", "9.0")])
    skriv(rot, "sjotemperatur", "2020-06-01",
          [("100", "sjotemperatur", "10.0"), ("200", "sjotemperatur", "10.0")])

    delvis = kjor(tmp_path, rot).filter(pl.col("serie") == "delvis")
    assert delvis["n_lokaliteter"][0] == 1
    assert delvis["verdi"][0] == pytest.approx(0.5 * (10 + 4.28) ** 2)


def test_manglende_temperatur_leses_ikke_som_null_grader(rot, tmp_path):
    """0,0 grader finnes som ekte måling. Med (T + 4,28)² er forskjellen
    på «ukjent» og «0» et faktisk tall på smittepresset, så en lokalitet
    uten temperatur skal falle ut — ikke bli 4,28² × lus."""
    skriv(rot, "akvakultur", "2026-01-05", [("100", "prodomraade_kode", "3")])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.5")])
    skriv(rot, "sjotemperatur", "2020-06-01",
          [("100", "temperatur_er_rapportert", "False")])

    assert kjor(tmp_path, rot).is_empty()


def test_lokalitet_uten_po_kode_faller_ut(rot, tmp_path):
    skriv(rot, "akvakultur", "2026-01-05", [("100", "breddegrad", "60.1")])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.5")])
    skriv(rot, "sjotemperatur", "2020-06-01", [("100", "sjotemperatur", "10.0")])

    assert kjor(tmp_path, rot).is_empty()


def test_middel_over_lokaliteter_ikke_sum(rot, tmp_path):
    """PO-leddet er N_fisk_PO × MIDDEL over lokaliteter. En sum ville
    telt fisken to ganger — én gang i N_fisk_PO og én gang i antallet
    lokaliteter — og det er nettopp forvekslingen forbeholdet handler om.
    """
    skriv(rot, "akvakultur", "2026-01-05", [("100", "prodomraade_kode", "3"),
                                            ("200", "prodomraade_kode", "3")])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.4"),
           ("200", "lus_er_rapportert", "True"), ("200", "voksne_hunnlus", "0.6")])
    skriv(rot, "sjotemperatur", "2020-06-01",
          [("100", "sjotemperatur", "10.0"), ("200", "sjotemperatur", "10.0")])

    delvis = kjor(tmp_path, rot).filter(pl.col("serie") == "delvis")
    assert delvis["n_lokaliteter"][0] == 2
    assert delvis["verdi"][0] == pytest.approx(0.5 * (10 + 4.28) ** 2)


# ------------------------------------------------------- skriving

def test_hver_serie_faar_sin_egen_fil(rot, tmp_path):
    grunnoppsett(rot, ["2020-06-01"], biomasse={"2020-06-30": 1_000_000})
    ramme = kjor(tmp_path, rot)

    for serie in ("full", "delvis"):
        sti = kildeledd.skriv(ramme, serie)
        assert sti.exists()
        skrevet = pl.read_parquet(sti)
        assert skrevet["serie"].unique().to_list() == [serie]


def test_kildeledd_py_kan_importeres_og_har_hjelp():
    """Ingen annen test kjører modulen som skript. En syntaksfeil i
    argparse-delen ville ellers sluppet gjennom hele suiten."""
    import subprocess
    import sys
    from pathlib import Path

    rot = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, str(rot / "kildeledd.py"), "--help"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "--fra" in r.stdout and "--til" in r.stdout


# ------------------------------------------------- dekningen bak middelet
#
# Uten disse kolonnene kan ingen skille «lus falt» fra «anleggene med
# mest lus ble tømt». De to ser IDENTISKE ut i kurven, og forskjellen er
# hele skillet mellom en riktig og en misvisende graf.

def test_dekningen_telles_per_po_per_uke(rot, tmp_path):
    """n_i_po teller ALLE, n_rapporterende de som leverte, n_brakklagt
    de som er markert brakklagt."""
    skriv(rot, "akvakultur", "2026-01-05",
          [(str(e), "prodomraade_kode", "3") for e in (100, 200, 300, 400)])
    skriv(rot, "lusetall", "2020-06-01", [
        # rapporterer, i drift
        ("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.5"),
        ("100", "brakklagt", "False"),
        ("200", "lus_er_rapportert", "True"), ("200", "voksne_hunnlus", "0.5"),
        ("200", "brakklagt", "False"),
        # brakklagt, rapporterer ikke
        ("300", "lus_er_rapportert", "False"), ("300", "brakklagt", "True"),
        # I DRIFT, men rapporterte ikke — den interessante gruppa
        ("400", "lus_er_rapportert", "False"), ("400", "brakklagt", "False"),
    ])
    skriv(rot, "sjotemperatur", "2020-06-01",
          [(str(e), "sjotemperatur", "10.0") for e in (100, 200, 300, 400)])

    d = kjor(tmp_path, rot).filter(pl.col("serie") == "delvis")
    assert d.height == 1
    assert d["n_i_po"][0] == 4
    assert d["n_rapporterende"][0] == 2
    assert d["n_brakklagt"][0] == 1
    assert d["n_lokaliteter"][0] == 2
    # Aktive anlegg som ikke rapporterte: 4 - 1 - 2 = 1
    assert (d["n_i_po"][0] - d["n_brakklagt"][0] - d["n_rapporterende"][0]) == 1


def test_dekningen_telles_foer_filtrene_ikke_etter(rot, tmp_path):
    """Poenget med tellerne er nettopp de som FALLER UT av middelet.

    Telte vi etter filtrene, ville n_rapporterende vært lik
    n_lokaliteter, og kolonnen kunne ikke avdekket noe som helst.
    """
    skriv(rot, "akvakultur", "2026-01-05",
          [(str(e), "prodomraade_kode", "3") for e in (100, 200)])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.5"),
           ("200", "lus_er_rapportert", "True"), ("200", "voksne_hunnlus", "0.5")])
    # 200 mangler TEMPERATUR og faller ut av middelet, men den RAPPORTERTE.
    skriv(rot, "sjotemperatur", "2020-06-01", [("100", "sjotemperatur", "10.0")])

    d = kjor(tmp_path, rot).filter(pl.col("serie") == "delvis")
    assert d["n_rapporterende"][0] == 2
    assert d["n_lokaliteter"][0] == 1


def test_po_uke_uten_en_eneste_rapport_gir_ingen_rad(rot, tmp_path):
    """Tellerne oppretter bøtta for hvert (po, uke). Uten en vakt ville
    en uke der ingen rapporterte gitt st.mean([]) og krasjet."""
    skriv(rot, "akvakultur", "2026-01-05", [("100", "prodomraade_kode", "3")])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "False"), ("100", "brakklagt", "True")])
    skriv(rot, "sjotemperatur", "2020-06-01", [("100", "sjotemperatur", "10.0")])

    assert kjor(tmp_path, rot).is_empty()


def test_nevnerforbeholdet_staar_paa_hver_rad(rot, tmp_path):
    """Samme krav som formelen og aggregeringen: parqueten skal bære sin
    egen begrensning hvis den havner et annet sted (CLAUDE.md 1b-3)."""
    grunnoppsett(rot, ["2020-06-01"], biomasse={"2020-06-30": 1000})
    r = kjor(tmp_path, rot)
    for rad in r.iter_rows(named=True):
        assert "n_rapporterende" in rad["forbehold"]
        assert "middel" in rad["forbehold"].lower()


def test_dekningskolonnene_staar_i_skjemaet(rot, tmp_path):
    for felt in ("n_i_po", "n_rapporterende", "n_brakklagt"):
        assert felt in kildeledd.SKJEMA, f"{felt} mangler i SKJEMA"
        assert kildeledd.SKJEMA[felt] == pl.Int64


def test_manglende_brakklagt_telles_ikke_som_brakklagt(rot, tmp_path):
    """Et felt som ikke er levert er IKKE en False. Samme skille som
    lus_er_rapportert gjør en etasje ned."""
    skriv(rot, "akvakultur", "2026-01-05", [("100", "prodomraade_kode", "3")])
    skriv(rot, "lusetall", "2020-06-01",
          [("100", "lus_er_rapportert", "True"), ("100", "voksne_hunnlus", "0.5")])
    skriv(rot, "sjotemperatur", "2020-06-01", [("100", "sjotemperatur", "10.0")])

    d = kjor(tmp_path, rot).filter(pl.col("serie") == "delvis")
    assert d["n_brakklagt"][0] == 0
    assert d["n_i_po"][0] == 1
