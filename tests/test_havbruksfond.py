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
import html
import io
import re
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


# ---------------------------------- tall og enhet på samme linje
#
# «7 800» og «t» sto på hver sin linje i en smal celle på 390 (Heine,
# 09.11.2026). Mellomrommet foran enheten skal være hardt i hver celle
# og hvert nøkkeltall, som tusenskillet allerede er.

_CELLE = re.compile(r"<(td|th|dd)\b[^>]*>(.*?)</\1>", re.S)
_BRUTT = re.compile(r"\d[ \t\r\n]+(?:t|tonn|prosentpoeng)\b|\d[ \t\r\n]+%")


def _brutte_enheter(side: str) -> list[str]:
    """Celler (td, th, dd) der et tall og enheten kan brytes fra hverandre."""
    ut = []
    for _, innhold in _CELLE.findall(side):
        tekst = html.unescape(re.sub(r"<[^>]+>", "", innhold))
        ut += [m.group() for m in _BRUTT.finditer(tekst)]
    return ut


def test_brutt_enhet_fanges():
    """Uten denne kunne prøvene under vært grønne fordi de ikke ser noe."""
    assert _brutte_enheter("<td>7 800 t</td><dd>+0,079\n  prosentpoeng</dd>"
                           "<td>1,2 %</td>") == ["0 t", "9\n  prosentpoeng", "2 %"]
    assert _brutte_enheter("<td>7&nbsp;800&nbsp;t</td><dd>+0,079&nbsp;prosentpoeng"
                           " (7\u00a0800\u00a0t til 9\u00a0000\u00a0t)</dd>") == []
    # Et ord som begynner på t er ikke enheten.
    assert _brutte_enheter("<dd>01.09.2025 til 31.08.2026</dd>") == []


def test_tonn_har_hardt_mellomrom():
    assert nettsted._tonn(7800) == "7\u00a0800\u00a0t"
    assert nettsted._tonn(212.4) == "212\u00a0t"


def test_malene_skriver_ingen_enhet_med_vanlig_mellomrom():
    """Et tall eller en verdi fra Python, så et vanlig mellomrom og
    enheten, i malkilden."""
    maler = Path(nettsted.MALER)
    for navn in MALENE:
        t = re.sub(r"\{#.*?#\}", " ", (maler / navn).read_text("utf-8"), flags=re.S)
        funn = re.findall(r"(?:\}\}|\d)[ \t\r\n]+(?:t|tonn|prosentpoeng)\b", t)
        assert not funn, (navn, funn)


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
def test_tall_og_enhet_holder_sammen_paa_kommunesidene():
    """Hver celle og hvert nøkkeltall på /kommune/ og de 143 sidene."""
    funn = {}
    for fil in sorted((NETTSTED / "kommune").rglob("index.html")):
        if brutt := _brutte_enheter(fil.read_text("utf-8")):
            funn[fil.relative_to(NETTSTED).as_posix()] = brutt[:3]
    assert not funn, list(funn.items())[:5]


@trenger_bygg
def test_aaret_foer_heter_noekkelen_med_dato():
    """«prosentpoeng fra 2025» kan leses som fjorårets utbetaling (Heine,
    09.11.2026). Tallet er Fiskeridirektoratets nøkkel per 01.09.2025, og
    sidene sier det med datoen."""
    import visningsord
    from core.karantene import synlig_tekst
    aar, dato = h.FORRIGE_AAR, visningsord.kortdato(h.FORRIGE_MAALING[:10])
    aarstall = re.compile(rf"(?:prosentpoeng fra|andelen siden|Andel(?:en)?) {aar}\b")
    funn = []
    for fil in sorted((NETTSTED / "kommune").rglob("index.html")):
        tekst = " ".join(synlig_tekst(fil.read_bytes()).split())
        funn += [(fil.parent.name, m.group()) for m in aarstall.finditer(tekst)]
        if fil.parent.name == "kommune":
            assert f"Nøkkel {dato}" in tekst
            assert f"prosentpoeng fra nøkkelen {dato}" in tekst
        else:
            assert f"prosentpoeng fra nøkkelen {dato}" in tekst, fil
            assert f"Hva som flyttet andelen siden {dato}" in tekst, fil
    assert not funn, funn[:5]


# Feltene der Fiskeridirektoratets fordeling står når fasiten er kvittert
# (`nettsted._fasit_vist()`). Et beløp utenfor dem er vårt, og det er et
# anslag.
FASITFELT = re.compile(r'<(dd|td)\b[^>]*\bdata-felt="fasit_[a-z_]+"[^>]*>.*?</\1>', re.S)
KRONER = re.compile(r"\bkr\b|\bkroner\b|\bmill(?:\.|ioner)\b")


def kroner_utenom_fasiten(side: str) -> list[str]:
    from core.karantene import synlig_tekst
    return KRONER.findall(synlig_tekst(FASITFELT.sub("", side).encode()))


@trenger_bygg
def test_ingen_kronebelop_paa_kommunesidene():
    """Før fasiten er kvittert, står ingen beløp. Etter står bare
    Fiskeridirektoratets, i feltene for det. Ellers ville et beløp vært
    et anslag."""
    for fil in sorted((NETTSTED / "kommune").rglob("index.html")):
        assert not kroner_utenom_fasiten(fil.read_text("utf-8")), fil


# --------------------------------- ingen tekst fra instruksen (0c)
#
# Instruksene og pressemeldingene brukes som fakta og metode, med lenke,
# og det er det som gjør kommuneanalysen salgbar (docs/LISENSKJEDE.md,
# bruk-kolonnen). Prøvene under holder sidene til det, og den første
# viser at de kan feile.

MALENE = ("kommune.html.j2", "kommuner.html.j2", "kommune-bevis.html.j2",
          "kommune-segl.html.j2")


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


# ---------------------------------------- andelstabellen (punkt 3)


@trenger_data
def test_andelstabellen_skrives_en_gang_og_leses_tilbake(datarepo, tmp_path, fordeling):
    """Prisberegningen i økt 13 leser `les_andelstabell()`. Tallene skal
    være fordelingens, og en ny kjøring med de samme radene skriver ikke."""
    sti = h.skriv_andelstabell(tmp_path)
    assert sti.name == f"andeler-{h.AAR}.csv"
    assert h.skriv_andelstabell(tmp_path) is None
    t = h.les_andelstabell(sti)
    assert len(t["kommune"]) == 143 and len(t["fylkeskommune"]) == 8
    for nr, k in fordeling["kommuner"].items():
        assert t["kommune"][nr]["andel"] == pytest.approx(k["andel"], abs=1e-10)
        assert t["kommune"][nr]["andel_2025"] == pytest.approx(k["andel_2025"], abs=1e-10)
    assert t["kommune"]["1866"]["delt"] and not t["kommune"]["5014"]["delt"]
    hode = [l for l in sti.read_text("utf-8").splitlines() if l.startswith("#")]
    assert any("sha256 ae33535555c1" in l for l in hode)
    assert any(h.segl()["sha256"] in l for l in hode)


@trenger_data
def test_en_odelagt_andelstabell_stopper_leseren(datarepo, tmp_path, fordeling):
    sti = tmp_path / "andeler.csv"
    tekst = h.tabelltekst(fordeling, [])
    sti.write_text(tekst.replace("kommune,5014,", "kommune,5014,", 1)
                   .replace("0.0458363829", "0.0558363829"))
    with pytest.raises(h.Tabellfeil, match="summerer"):
        h.les_andelstabell(sti)
    sti.write_text(tekst.replace("omraade", "navn", 1))
    with pytest.raises(h.Tabellfeil, match="kolonnene"):
        h.les_andelstabell(sti)


@trenger_data
def test_nettstedets_tabell_bestaar_porten(datarepo, fordeling):
    """Kopien på /kommune/ har ingen stier til repoet og ingen kolonne
    porten leser som et selskapsnavn."""
    import publiseringsvakt as v
    tekst = h.tabelltekst(fordeling, h.tabellhode(fordeling, nettsted=True), nettsted=True)
    assert v.tekstfunn("kommune/andeler-2026.csv", ".csv", tekst, set(), set()) == []
    assert "Kilde: Fiskeridirektoratet" in tekst


def _fasit_for_tabellen(fordeling) -> dict:
    """Det fasitceller() leser av en fasit: beløp, andel og MTB for én
    kommune og ett fylke, og summen av tabellen."""
    return {"tabell": {"sha256": "ab" * 32},
            "sider": {"kommuner": {"5501": {"belop": 18931168.0, "andel": 0.016784}},
                      "fylker": {"55": {"belop": 42800605.0, "andel": 0.151783}}},
            "avvik": {"kommuner": [{"nr": "5501", "fasit_mtb": 58564.0}]}}


@trenger_data
def test_nettstedets_tabell_har_tomme_fasitkolonner(datarepo, fordeling):
    """Før fasiten er kvittert: kolonnene finnes og er tomme i hver rad.
    Med den: fylt for kommunen og fylket den har. Datarepoets fil får dem
    ikke, for `les_andelstabell()` krever nøyaktig TABELLKOLONNER."""
    import csv as csv_
    def rader(tekst):
        return list(csv_.DictReader(io.StringIO(h._rader_i(tekst))))
    tom = rader(h.tabelltekst(fordeling, [], nettsted=True))
    assert tuple(tom[0]) == h.TABELLKOLONNER + h.FASITKOLONNER and len(tom) == 151
    assert all(r[k] == "" for r in tom for k in h.FASITKOLONNER)
    fylt = {(r["niva"], r["nr"]): r for r in rader(
        h.tabelltekst(fordeling, [], fasit=_fasit_for_tabellen(fordeling), nettsted=True))}
    t = fylt[("kommune", "5501")]
    assert (t["fasit_belop_kr"], t["fasit_andel"], t["fasit_mtb_tonn"]) == (
        "18931168.00", "0.0167840000", "58564.000")
    # Seks desimaler, som endring_pp.
    assert float(t["fasit_avvik_pp"]) == pytest.approx((0.016784 - float(t["andel"])) * 100,
                                                       abs=1e-6)
    assert t["fasit_kilde_sha256"] == "ab" * 32
    assert fylt[("fylkeskommune", "55")]["fasit_belop_kr"] == "42800605.00"
    assert fylt[("fylkeskommune", "55")]["fasit_mtb_tonn"] == ""
    assert fylt[("kommune", "5014")]["fasit_belop_kr"] == ""
    assert tuple(rader(h.tabelltekst(fordeling, []))[0]) == h.TABELLKOLONNER


# ------------------------------------ forseglingen på sidene (økt L)


def _avsnitt(side: str) -> str:
    """Teksten slik avsnittsvakten leser den (`publiseringsvakt.
    avsnittsfunn`): taggene borte, tekstnodene rett etter hverandre.
    `synlig_tekst()` setter mellomrom rundt hvert element («( fil , .ots )»)
    og ville målt en annen linje enn den leseren ser."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", side)).split())


@trenger_bygg
def test_forseglingen_staar_paa_oversikten_og_hver_kommuneside():
    """Én linje med pakke 1 og pakke 2, datoen og lenke til fila og .ots
    ved commiten der de kom inn i kodrepoet."""
    import nettsted as n
    lenker = [f"{n.REPO}/blob/66016dd3e636a03ab4f13563c110125e1cfcc27d/"
              "predictions/havbruksfond-2026.md",
              f"{n.REPO}/blob/04d91ddc890279935d00639179d4192fc97890fd/"
              "predictions/havbruksfond-2026.md.ots",
              f"{n.REPO}/blob/e1efe15f0b8bd6874411120fdd571f2b8c2807f4/"
              "predictions/havbruksfond-2026-pakke2.md",
              f"{n.REPO}/blob/e1efe15f0b8bd6874411120fdd571f2b8c2807f4/"
              "predictions/havbruksfond-2026-pakke2.md.ots"]
    sider = sorted((NETTSTED / "kommune").rglob("index.html"))
    assert len(sider) == 144
    for fil in sider:
        side = fil.read_text("utf-8")
        segl = re.search(r'<p class="historikk-forklaring" id="segl">(.*?)</p>', side, re.S)
        assert segl, fil
        assert all(f'href="{l}"' in segl.group(1) for l in lenker), fil
        tekst = _avsnitt(segl.group(0))
        assert len(tekst) <= 110 and tekst == (
            "Anslagene ble forseglet før fordelingen: pakke 1 12.10.2026 "
            "(fil, .ots) og pakke 2 09.11.2026 (fil, .ots)."), tekst


@trenger_bygg
def test_slik_sjekker_du_oss_i_tre_linjer():
    side = (NETTSTED / "kommune" / "index.html").read_text("utf-8")
    seksjon = re.search(r'<section[^>]*id="sjekk".*?</section>', side, re.S).group(0)
    assert "Slik sjekker du oss" in seksjon
    assert len(re.findall(r"<li>", seksjon)) == 3
    assert "ots --no-bitcoin verify" in seksjon and "shasum -a 256" in seksjon


@trenger_bygg
def test_tromso_sier_hva_pakke2_forventer_og_ingen_andre():
    """Tromsø-siden viser pakke 1s andel og et fall fra nøkkelen
    01.09.2025. Pakke 2 forventer Havbruksstasjonen med, og siden sier
    det, med tallene fra begge pakkene og lenke til pakke 2."""
    side = (NETTSTED / "kommune" / "5501" / "index.html").read_text("utf-8")
    tekst = _avsnitt(side)
    assert ("Pakke 2 forventer Havbruksstasjonens to lokaliteter (10768, 15236) med: "
            "1,5475 %, mot 1,5056 % i pakke 1.") in tekst.replace(" ", " ")
    assert "predictions/havbruksfond-2026-pakke2.md" in side
    andre = [f.parent.name for f in (NETTSTED / "kommune").glob("*/index.html")
             if f.parent.name != "5501" and "Havbruksstasjonen" in f.read_text("utf-8")]
    assert andre == []


@trenger_bygg
def test_nettstedets_csv_har_tomme_fasitkolonner():
    import csv as csv_
    tekst = (NETTSTED / "kommune" / "andeler-2026.csv").read_text("utf-8")
    rader = list(csv_.DictReader(io.StringIO(h._rader_i(tekst))))
    assert len(rader) == 151 and tuple(rader[0])[-len(h.FASITKOLONNER):] == h.FASITKOLONNER
    assert all(r[k] == "" for r in rader for k in h.FASITKOLONNER)


def test_jsonld_paa_kommunesidene_bestaar_porten(tmp_path):
    """Hvert Dataset i `isBasedOn`, også regnearket som ikke er en kilde i
    `sources/`, har det Search Console krever. Første fulle bygg stoppet
    på 144 sider fordi regnearknoden manglet `description`."""
    import publiseringsvakt as v
    d = {"maaledato": "2026-09-01", "forrige": 2025,
         "fiskeridir": "https://www.fiskeridir.no/akvakultur/havbruksfondet"}
    jsonld = nettsted._jsonld_kommune("Frøya, Trøndelag: havbruksfondet 2026",
                                      "x" * 60, "/kommune/5014/",
                                      nettsted.kildevilkaar(), d)
    (tmp_path / "index.html").write_text(f"<html><body>{jsonld}</body></html>")
    assert v.jsonldfunn(tmp_path) == []
