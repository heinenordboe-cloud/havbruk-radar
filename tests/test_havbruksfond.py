"""Havbruksfondet per kommune: tallene er det forseglede anslaget.

`havbruksfond.fordeling()` er ÉN vei til andelene, for kommunesidene,
skåreren og andelstabellen. Prøvene her holder den mot anslaget som ble
forseglet 12.10.2026 (predictions/havbruksfond-2026.md, med .ots), og
mot det målingen fant i A3: Skjervøy, Haram og Tromsø.

De fleste prøvene trenger datarepoet ved siden av (snapshotene, eierskaps-
kroppen og regnearkene). conftest.py peker DATA_DIR på en tom mappe; her
pekes snapshot-døra og arkivet på datarepoet for prøven. Uten datarepoet
(Actions) hoppes de over.
"""
import gzip
import io
from pathlib import Path

import pytest

import havbruksfond as h
import nettsted
from core import paths, snapshot

DATAREPO = Path(__file__).resolve().parent.parent.parent / "havbruk-radar-data" / "data"
trenger_data = pytest.mark.skipif(
    not (DATAREPO / "raw" / "akvakultur" / f"{h.FOR}.parquet").exists(),
    reason="datarepoet ligger ikke ved siden av")


@pytest.fixture
def datarepo(monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
    monkeypatch.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
    return DATAREPO


@pytest.fixture
def fordeling(datarepo):
    return h.fordeling()


def test_seglet_holder():
    """Anslaget er fila som ble stemplet: summen i .ots er fila sin."""
    s = h.segl()
    assert s["uendret"], s


def test_anslaget_leses_med_alle_kommuner_og_fylker():
    a = h.anslaget()
    assert len(a["kommuner"]) == 143 and len(a["fylker"]) == 8
    assert a["kommuner"]["5014"] == pytest.approx(0.045836)
    assert sum(a["fylker"].values()) == pytest.approx(1, abs=1e-5)


@trenger_data
def test_fordelingen_er_det_forseglede_anslaget(fordeling):
    """Kommune for kommune og fylke for fylke, på anslagets fire
    desimaler. Faller denne, viser sidene noe annet enn det som ble
    forseglet."""
    a = h.anslaget()
    assert set(fordeling["kommuner"]) == set(a["kommuner"])
    for nr, k in fordeling["kommuner"].items():
        assert round(k["andel"] * 100, 4) == round(a["kommuner"][nr] * 100, 4), nr
    for nr, f in fordeling["fylker"].items():
        assert round(f["andel"] * 100, 4) == round(a["fylker"][nr] * 100, 4), nr


@trenger_data
def test_tallene_fra_maalingen(fordeling):
    """A2: 1 065 i ledd 1, 11 holdt ute av ledd 2, 3 815 004 t. A3: samlet
    MTB hos Fiskeridirektoratet 01.09.2025 var 3 793 021 t."""
    assert fordeling["ledd1"] == 1065
    assert len(fordeling["ute"]) == 11
    assert round(fordeling["total"]) == 3815004
    assert round(fordeling["total_2025"]) == 3793021


@trenger_data
def test_hva_som_flyttet_andelen_er_det_a3_fant(fordeling):
    k = fordeling["kommuner"]
    skjervoy = k["5542"]
    assert round(skjervoy["endring"] * 100, 3) == -0.150
    assert [(x["nr"], x["endring"], x["grunn"]) for x in skjervoy["flytt"]] == [
        ("36237", -5400.0, "ute_av_registeret")]
    haram = {x["nr"]: x for x in k["1580"]["flytt"]}
    assert haram["45299"]["grunn"] == "ny" and haram["45299"]["endring"] == 4680
    assert haram["12281"]["grunn"] == "endret" and haram["12281"]["endring"] == 780
    tromso = {x["nr"]: x["grunn"] for x in k["5501"]["flytt"]}
    assert tromso["10768"] == tromso["15236"] == "ledd2"


@trenger_data
def test_endringen_er_summen_av_de_to_leddene(fordeling):
    for nr, k in fordeling["kommuner"].items():
        assert k["fra_egne"] + k["fra_landet"] == pytest.approx(k["endring"],
                                                                 abs=1e-12), nr


@trenger_data
def test_andelen_2025_er_fiskeridirektoratets_egen(datarepo, fordeling):
    """Andelen 2025 regnes av lokalitetsarket. Den skal være lik «i %» i
    arket «Kommuner», som er tallet Fiskeridirektoratet selv oppga."""
    ark, _ = h.regneark(2025)
    oppgitt = {r[0]: float(r[5]) for r in ark["Kommuner"][4:] if r and r[0].isdigit()}
    assert len(oppgitt) == 143
    for nr, k in fordeling["kommuner"].items():
        assert k["andel_2025"] == pytest.approx(oppgitt[nr], abs=1e-12), nr


@trenger_data
def test_lokalitetsarket_leses_i_begge_aarenes_form(datarepo):
    """2024 og 2025 har lokalitetslista i ulik kolonnerekkefølge."""
    for aar, lokaliteter in ((2024, None), (2025, 1065)):
        rader = h.lokalitetsark(h.regneark(aar)[0])
        assert rader and all(r["nr"].isdigit() and len(r["komnr"]) == 4 for r in rader)
        if lokaliteter:
            assert len({r["nr"] for r in rader}) == lokaliteter
    assert len(h.delte(h.lokalitetsark(h.regneark(2025)[0]))) == 10


@trenger_data
def test_grunnlagssprik_kaster(datarepo, monkeypatch):
    """To snapshots som gir ulik nøkkel, gir ingen andel per 01.09."""
    ekte = h.nokkel

    def skjev(dato, *a, **k):
        n = ekte(dato, *a, **k)
        if dato == h.ETTER:
            n.plasser["5014"] = n.plasser["5014"][1:]
        return n
    monkeypatch.setattr(h, "nokkel", skjev)
    with pytest.raises(h.Grunnlagssprik):
        h.fordeling()


@trenger_data
def test_faktaene_med_lenke_staar_i_kroppene(datarepo):
    """Datoene sidene oppgir, er lest av kroppene. Ingen tekst fra dem
    gjengis; prøven ser bare at datoen er deres."""
    import pypdf
    from core.karantene import synlig_tekst
    pdf = gzip.open(datarepo / "arkiv" / h.INSTRUKS["kropp"]).read()
    tekst = " ".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    assert "27. september 2024" in tekst
    assert "1. september kl. 12.00" in tekst
    melding = synlig_tekst(gzip.open(datarepo / "arkiv" / h.FORDELT[2025]["kropp"]).read())
    assert "10.11.2025" in melding


@trenger_data
def test_ingen_kroner_regnes(fordeling):
    """Nøkkelen har tonn og andeler, ingen beløp."""
    k = fordeling["kommuner"]["5014"]
    assert not [n for n in k if "kr" in n or "belop" in n or "utbetal" in n]


def test_prosentpoeng_har_fortegn_og_null_har_ikke():
    assert nettsted._pp(0.00079) == "+0,079"
    assert nettsted._pp(-0.0015) == "−0,150"
    assert nettsted._pp(1e-9) == "0,000"


def test_uten_grunnlag_ingen_kommunesider(tmp_path):
    """Mangler snapshotene, skrives ingen side — og bygget feiler ikke."""
    from types import SimpleNamespace
    assert nettsted.skriv_kommuner(tmp_path, SimpleNamespace(akva={})) == []
    assert not (tmp_path / "kommune").exists()


# ------------------------------------------------- mot portens bygg

NETTSTED = Path(__import__("os").environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "kommune" / "index.html").exists(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted med /kommune/")


@trenger_bygg
def test_hver_kommune_har_side_og_staar_i_sitemapen():
    sider = sorted(p.parent.name for p in (NETTSTED / "kommune").glob("*/index.html"))
    assert len(sider) == 143
    sitemap = (NETTSTED / "sitemap.xml").read_text("utf-8")
    assert "/kommune/</loc>" in sitemap
    assert all(f"/kommune/{nr}/</loc>" in sitemap for nr in sider)
    assert "143 kommuner" in (NETTSTED / "llms.txt").read_text("utf-8")


@trenger_bygg
def test_ingen_kronebelop_paa_kommunesidene():
    """Fordelingen 2026 er ikke publisert. Et beløp ville vært et anslag."""
    import re
    from core.karantene import synlig_tekst
    for fil in sorted((NETTSTED / "kommune").rglob("index.html")):
        tekst = synlig_tekst(fil.read_bytes())
        assert not re.search(r"\bkr\b|\bkroner\b|\bmill(?:\.|ioner)\b", tekst), fil


# --------------------------------- ingen tekst fra instruksen (0c)
#
# Instruksene og pressemeldingene brukes som fakta og metode, med lenke,
# og det er det som gjør kommuneanalysen salgbar (docs/LISENSKJEDE.md,
# bruk-kolonnen). Prøvene under holder sidene til det, og den første
# viser at de kan feile.

MALENE = ("kommune.html.j2", "kommuner.html.j2", "kommune-bevis.html.j2")


@pytest.fixture
def kildeskiver(datarepo):
    return h.kildeskiver()


@trenger_data
def test_gjengitt_finner_en_setning_fra_instruksen(datarepo, kildeskiver):
    """Uten denne kunne prøvene under vært grønne fordi de ikke ser noe."""
    instruks = h.kroppstekst(h.INSTRUKS["kropp"])
    setning = next(s for s in instruks.split(". ") if len(h.ordene(s)) >= 10)
    side = f"<p>Kommunen og fondet. {setning}.</p>"
    funn = h.gjengitt(side, kildeskiver)
    assert funn and {rel for rel, _ in funn} >= {h.INSTRUKS["kropp"]}
    # Artslista alene er et faktum, ikke en formulering.
    assert h.gjengitt("laks, ørret og regnbueørret i sjø", kildeskiver) == []


@trenger_data
def test_alle_kroppene_har_tekst(kildeskiver):
    """En kropp uten lesbar tekst ville gjort prøven blind for den."""
    for rel, s in kildeskiver.items():
        assert len(s) > 200, rel


@trenger_data
def test_malene_gjengir_ingen_tekst(kildeskiver):
    """Prosaen står i malene. Uten Jinja og tagger skal den ikke ha seks
    ord på rad fra noen av kroppene."""
    import re
    maler = Path(nettsted.MALER)
    for navn in MALENE:
        t = (maler / navn).read_text("utf-8")
        t = re.sub(r"\{#.*?#\}|\{%.*?%\}|\{\{.*?\}\}|<[^>]+>", " ", t, flags=re.S)
        assert h.gjengitt(t, kildeskiver) == [], navn


@trenger_bygg
@trenger_data
def test_kommunesidene_gjengir_ingen_tekst(kildeskiver):
    """Hver side under /kommune/ i portens bygg, synlig tekst."""
    from core.karantene import synlig_tekst
    funn = []
    sider = sorted((NETTSTED / "kommune").rglob("index.html"))
    assert len(sider) == 144
    for fil in sider:
        funn += [(fil.relative_to(NETTSTED).as_posix(), rel, s) for rel, s in
                 h.gjengitt(synlig_tekst(fil.read_bytes()), kildeskiver)]
    assert not funn, funn[:10]
