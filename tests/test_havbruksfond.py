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
          "kommune-segl.html.j2",
          # Fasiten, fra 16.11.2026: siden med de forseglede anslagene,
          # oversikten, og setningene om andel og beløp som også står på
          # /kommune/.
          "fasit-havbruksfond.html.j2", "fasiten.html.j2",
          "andel-og-belop.html.j2")


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


# FILENE NETTSTEDET HAR EN KOPI AV, og commiten hver kom inn i (Heine,
# økt 16a): fila fra 12.10 er 66016dd, stempelet er det oppgraderte fra
# 3154667, og fila og stempelet fra 09.11 er e1efe15. Summene er av
# bytene i de commitene, MÅLT 16.11.2026 med `git show <commit>:<fil>`.
# Byttes en fil i predictions/, er det en annen fil nettstedet legger ut,
# og det skal ikke skje uten at denne tabellen endres.
KOPIER = {
    "predictions/havbruksfond-2026.md": (
        "66016dd3e636a03ab4f13563c110125e1cfcc27d",
        "de9ba03432837c0cfc2fd0b2b145bfdad2e7ebcf47dea4a6addb626e38387002"),
    "predictions/havbruksfond-2026.md.ots": (
        "31546677baa01a34bf7c086b6d4a805bd60e4a0e",
        "dd6664a4f504afd3858bc53499acbda510b5c4151e65812fa9fc960c8be3c697"),
    "predictions/havbruksfond-2026-pakke2.md": (
        "e1efe15f0b8bd6874411120fdd571f2b8c2807f4",
        "ccb451bdde451430d48c7a3f62ec037d98a0c91b2ae4b631cd2165bbc69701a0"),
    "predictions/havbruksfond-2026-pakke2.md.ots": (
        "e1efe15f0b8bd6874411120fdd571f2b8c2807f4",
        "d948dafee1fdc1648e57cda347da3a75e42e159bef0515e37557272583b5f011"),
}


def test_kopiene_er_filene_fra_commitene_de_kom_inn_i():
    """Det nettstedet kopierer, er bytene fra commitene over. Der
    historikken finnes (ikke i en grunn klone), hentes fila ut av commiten
    og summeres på nytt."""
    import hashlib
    import subprocess
    assert {k["kilde"].relative_to(h.ROT).as_posix() for k in h.forseglede_kopier()} \
        == set(KOPIER)
    hentet = 0
    for rel, (commit, sum_) in KOPIER.items():
        assert hashlib.sha256((h.ROT / rel).read_bytes()).hexdigest() == sum_, rel
        blob = subprocess.run(["git", "-C", str(h.ROT), "cat-file", "blob",
                               f"{commit}:{rel}"], capture_output=True)
        if blob.returncode == 0:
            hentet += 1
            assert hashlib.sha256(blob.stdout).hexdigest() == sum_, (rel, commit)
    # Og commitene er de siste som står for hver fil i FORSEGLINGER.
    siste = {f["fil"] + (".ots" if hva == "ots" else ""): c
             for f in h.FORSEGLINGER for repo, c, hva in f["commits"]
             if repo == "havbruk-radar"}
    assert siste == {rel: commit for rel, (commit, _) in KOPIER.items()}
    if not hentet:
        pytest.skip("commitene finnes ikke i denne klonen; bare filene er prøvd")


def test_forseglingene_lenker_til_fasitsiden_ikke_til_kodrepoet():
    s = {x["pakke"]: x for x in nettsted._forseglingene()}
    assert s["pakke 1"] == {"pakke": "pakke 1", "dato": "2026-10-12",
                            "side": "/fasiten/havbruksfondet-2026/#forseglet-2026-10-12"}
    assert s["pakke 2"]["side"] == "/fasiten/havbruksfondet-2026/#forseglet-2026-11-09"
    assert "github.com" not in repr(s)


def _main(side: str) -> str:
    """Innholdet på siden. Bunnteksten er felles for hele nettstedet og har
    lenken «Kildekoden»; den er ikke en del av kommunesiden."""
    return re.search(r"<main\b.*?</main>", side, re.S).group(0)


LINJA = ("Anslagene ble forseglet før fordelingen, 12.10.2026 og 09.11.2026. "
         "Se anslagene og hvordan du sjekker dem.")


@trenger_bygg
def test_forseglingen_staar_paa_oversikten_og_hver_kommuneside():
    """Én linje, Heines ord: datoen hvert anslag ble forseglet, og én lenke
    til siden som forklarer dem og har filene og stemplene. Uten «pakke 1»
    og «pakke 2»: det er interne ord (økt L)."""
    sider = sorted((NETTSTED / "kommune").rglob("index.html"))
    assert len(sider) == 144
    for fil in sider:
        side = fil.read_text("utf-8")
        segl = re.search(r'<p class="historikk-forklaring" id="segl">(.*?)</p>', side, re.S)
        assert segl, fil
        assert re.findall(r'href="([^"]+)"', segl.group(1)) == [
            "/fasiten/havbruksfondet-2026/"], fil
        tekst = _avsnitt(segl.group(0))
        assert len(tekst) <= 110 and tekst == LINJA, tekst
    assert (NETTSTED / "fasiten" / "havbruksfondet-2026" / "index.html").is_file()


@trenger_bygg
def test_ingen_lenke_til_kodrepoet_paa_kommunesidene():
    """En journalist eller kunde skal aldri måtte til kodrepoet for å lese
    eller sjekke et anslag (Heine, økt 16a). Til 16.11.2026 hadde hver av
    de 144 sidene fire lenker dit. Prøven leser innholdet (`<main>`), ikke
    bunnteksten, som er lik på hver side av nettstedet."""
    sider = sorted((NETTSTED / "kommune").rglob("index.html"))
    assert len(sider) == 144
    funn = [fil.parent.name for fil in sider
            if "github.com" in _main(fil.read_text("utf-8"))]
    assert funn == []
    # Og prøven ser det den leter etter: bunnteksten har lenken.
    assert "github.com" in sider[0].read_text("utf-8")


@trenger_bygg
def test_ingen_pakke_paa_kommunesidene():
    """«Pakke 1» og «pakke 2» er interne ord og står ingen steder i den
    synlige teksten under /kommune/ (Heine, økt L)."""
    funn = []
    for fil in sorted((NETTSTED / "kommune").rglob("index.html")):
        funn += [(fil.parent.name, m) for m in
                 re.findall(r"(?i)\bpakke\s*\d", _avsnitt(fil.read_text("utf-8")))]
    assert not funn, funn[:5]


@trenger_bygg
def test_slik_sjekker_du_oss_staar_paa_fasitsiden_ikke_paa_oversikten():
    """De tre linjene flyttet 16.11.2026 til siden med filene og stemplene
    de handler om (tests/test_fasiten.py holder teksten). På oversikten
    står linja med lenken, og ankeret #sjekk er beholdt."""
    side = (NETTSTED / "kommune" / "index.html").read_text("utf-8")
    assert "Slik sjekker du oss" not in _avsnitt(_main(side))
    assert "opentimestamps.org" not in _main(side)
    assert 'id="sjekk"' in side
    fasit = (NETTSTED / "fasiten" / "havbruksfondet-2026" / "index.html").read_text("utf-8")
    seksjon = re.search(r'<section[^>]*id="sjekk".*?</section>', fasit, re.S).group(0)
    # Heines tekst (16b, rettinger 2). En linje over 110 tegn står i to
    # avsnitt i samme punkt; hvert avsnitt holder grensa.
    fil = "havbruksfondet-2026-forseglet-2026-11-09.md"
    avsnitt = [_avsnitt(p) for p in re.findall(r"<p>.*?</p>", seksjon, re.S)]
    assert avsnitt == [
        f"Last ned {fil}", f"og stempelet med blokka ({fil}.ots).",
        "Dra begge filene inn på opentimestamps.org. Den viser hvilken "
        "Bitcoin-blokk stempelet ligger i.",
        "Med egen Bitcoin-node: ots verify."]
    assert _avsnitt(re.findall(r"<li>.*?</li>", seksjon, re.S)[1]).startswith(
        f"shasum -a 256 {fil} skal gi ccb451bd…01a0")
    assert "no-bitcoin" not in seksjon
    assert re.search(r'<a href="https://opentimestamps.org/" rel="external">opentimestamps.org'
                     r'<svg[^>]*aria-label="ekstern side"', seksjon)
    assert all(len(l) <= 110 for l in avsnitt)


@trenger_bygg
def test_tromso_viser_de_to_lokalitetene_med_kilde_og_ingen_andre():
    """Målte fakta, ingen forventning: ikke med i andelen (eierskapet 02.09),
    med hos Fiskeridirektoratet (listene 01.09.2024 og 01.09.2025), og
    andelen med dem (regnet), med lenke til det forseglede anslaget under
    andelen. Bare Tromsø har lokaliteter som dette."""
    side = (NETTSTED / "kommune" / "5501" / "index.html").read_text("utf-8")
    blokk = re.search(r'<dl class="fakta fakta--tett" id="holdt-ute">.*?</dl>', side, re.S)
    assert blokk, "Tromsø mangler linja om de to lokalitetene"
    dt = _avsnitt(re.search(r"<dt>.*?</dt>", blokk.group(0), re.S).group(0))
    dd = [_avsnitt(x).replace(chr(0xA0), " ")
          for x in re.findall(r"<dd>.*?</dd>", blokk.group(0), re.S)]
    assert dt == "Indre Kårvik I og Skulgambukt (Havbruksstasjonen i Tromsø)"
    assert dd == [
        "er ikke med i andelen over, fordi de ikke har tillatelse for laksefisk. "
        "Fiskeridir. · 02.09.2026",
        "Fiskeridirektoratet tok dem med i 2024 og 2025. "
        "Fiskeridir. · 01.09.2024 og 01.09.2025",
        "Med dem blir andelen 1,5475 %. Fiskeridir. · 31.08.2026 · regnet"]
    assert all(len(x) <= 110 for x in dd)
    andel = re.search(r'<a href="([^"]+)">1,5475', blokk.group(0))
    assert andel and andel.group(1) == "/fasiten/havbruksfondet-2026/#forseglet-2026-11-09"
    andre = [f.parent.name for f in (NETTSTED / "kommune").glob("*/index.html")
             if f.parent.name != "5501" and 'id="holdt-ute"' in f.read_text("utf-8")]
    assert andre == []


@trenger_data
def test_hver_del_av_tromso_linja_er_maalt(datarepo, fordeling):
    """Hver påstand i Tromsø-linja holdt mot kroppen den kommer fra: de to
    lokalitetene står på Fiskeridirektoratets lister 01.09.2024 og
    01.09.2025 med 650 og 975 t, ingen av tillatelsene deres har
    laksefisk i eierskapet 02.09.2026, innehaveren er ett aksjeselskap,
    og andelen med dem er den som ble forseglet 09.11.2026."""
    lister = {aar: {r["nr"]: r["kap"] for r in h.lokalitetsark(h.regneark(aar)[0])}
              for aar in (2024, 2025)}
    for liste in lister.values():
        assert (liste.get("10768"), liste.get("15236")) == (650.0, 975.0)
    lisens, _ = h.lakselisenser()
    assert lisens["10768"] is False and lisens["15236"] is False
    m = nettsted._med_hos_fiskeridir(
        fordeling, lambda nr, navn: {"nr": nr, "navn": navn, "url": ""},
        nettsted._forseglingene())
    assert list(m) == ["5501"]
    t = m["5501"]
    assert [l["nr"] for l in t["lokaliteter"]] == ["10768", "15236"]
    assert t["innehaver"] == "Havbruksstasjonen i Tromsø"
    assert t["andel"] == "1,5475 %"
    assert t["url"] == "/fasiten/havbruksfondet-2026/#forseglet-2026-11-09"


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


# ------------------------------ delte lokaliteter (gjennomgangen 11.11)


def test_nettstedets_tabell_har_ikke_ordet_maalbar(monkeypatch):
    """«Målbar» er et ord fra målingene våre. Tabellen leserne laster ned,
    sier at delingen ikke er målt i år; datarepoets egen fil er som før."""
    f = {"kropper": []}
    ute = "\n".join(h.tabellhode(f, nettsted=True))
    assert "MÅLBAR" not in ute.upper() and "(ikke målt i år)" in ute
    assert "(MÅLBAR, ikke målt i år)" in "\n".join(h.tabellhode(f, kode="x"))


@trenger_bygg
def test_delingen_sier_hvor_den_kommer_fra_med_kilde():
    """En delt lokalitet (Oksebåsen V i Haram og Giske) sto med lenken
    «målbar». Nå står hvor delingen kommer fra én gang under tabellen, med
    kilde og dato, og forbeholdet er ett klikk unna. Ordet står ingen
    steder under /kommune/, heller ikke i tabellen som lastes ned."""
    sider = sorted((NETTSTED / "kommune").glob("*/index.html"))
    delte = []
    for fil in sider:
        side = fil.read_text("utf-8")
        celler = [_avsnitt(c) for c in re.findall(
            r'<td[^>]*data-felt="delingsandel"[^>]*>(.*?)</td>', side, re.S)]
        linje = re.search(r'<p class="historikk-forklaring" id="deling">(.*?)</p>', side, re.S)
        if any(celler):
            delte.append(fil.parent.name)
            assert linje, fil
            tekst = _avsnitt(linje.group(0))
            assert tekst == ("Delingen er Fiskeridirektoratets, fra beregningen for 2025, "
                             "og er ikke målt i år. Fiskeridir. · 01.09.2025"), tekst
            assert len(tekst) <= 110
            assert '<a href="/kommune/#deling">ikke målt i år</a>' in linje.group(1)
            assert 'datetime="2025-09-01"' in linje.group(1)
        else:
            assert not linje, fil
    # Ti lokaliteter deles mellom to kommuner hver.
    assert len(delte) == 20 and {"1580", "1532"} <= set(delte)
    haram = (NETTSTED / "kommune" / "1580" / "index.html").read_text("utf-8")
    assert [_avsnitt(c) for c in re.findall(
        r'<td[^>]*data-felt="delingsandel"[^>]*>(.*?)</td>', haram, re.S) if _avsnitt(c)] \
        == ["64,76 %, delt med Giske"]      # `_avsnitt` gjør det harde mellomrommet vanlig
    for fil in sorted((NETTSTED / "kommune").rglob("index.html")):
        assert not re.search(r"(?i)målbar", _avsnitt(_main(fil.read_text("utf-8")))), fil
    assert "MÅLBAR" not in (NETTSTED / "kommune" / "andeler-2026.csv").read_text("utf-8").upper()
    oversikt = (NETTSTED / "kommune" / "index.html").read_text("utf-8")
    punkt = re.search(r'<li id="deling">(.*?)</li>', oversikt, re.S)
    assert punkt and _avsnitt(punkt.group(0)) == (
        "En lokalitet over en kommunegrense er delt som i Fiskeridirektoratets "
        "beregning for 2025.")
    # Det gamle ankeret står, så en lenke til /kommune/#maalbar lander her.
    assert '<span id="maalbar"></span>' in punkt.group(1)


# ----------------------- delene summerer til totalen (gjennomgangen 12.11)


def _tusendeler(vist: str) -> int:
    """«+0,079» -> 79 og «−0,150» -> −150: prosentpoeng i hele tusendeler."""
    return round(float(vist.replace("−", "-").replace(",", ".")) * 1000)


def test_delene_avrundes_etter_storste_rest():
    """Tromsø, med tallene fra registeret: −0,029515 og −0,008897 er
    −0,038412. Hver for seg blir de −0,030 og −0,009, som er −0,039. Den
    som er nærmest neste tusendel, får den."""
    assert nettsted._pp_deler((-0.00029515038, -0.00008896873), -0.00038411911) \
        == ["−0,029", "−0,009"]
    assert [nettsted._pp(-0.00029515038), nettsted._pp(-0.00008896873)] \
        == ["−0,030", "−0,009"]
    # Uten egne endringer er hele endringen landets, og null har ikke fortegn.
    assert nettsted._pp_deler((0.0, 0.00079), 0.00079) == ["0,000", "+0,079"]
    # Deler som allerede summerer, røres ikke.
    assert nettsted._pp_deler((0.00143, -0.00003), 0.0014) == ["+0,143", "−0,003"]
    # Tre deler, to tusendeler å dele ut: de to med størst rest får hver sin.
    assert nettsted._pp_deler((0.0000166, 0.0000167, 0.0000167), 0.00005) \
        == ["+0,001", "+0,002", "+0,002"]
    # Fire desimaler virker likt.
    assert nettsted._pp_deler((-0.00029515038, -0.00008896873), -0.00038411911, 4) \
        == ["−0,0295", "−0,0089"]


def test_deler_som_ikke_er_totalen_kaster():
    """Da er det ikke avrundingen som skiller, og en justering ville
    skjult det."""
    with pytest.raises(ValueError, match="summerer ikke"):
        nettsted._pp_deler((0.001, 0.002), 0.0031)


@trenger_data
def test_delene_summerer_til_endringen_som_vises_i_alle_kommuner(fordeling):
    """Alle 143: de to leddene i «Hva som flyttet andelen» summerer til
    endringen øverst på siden, og ingen av dem er mer enn én tusendel fra
    sin sanne verdi. MÅLT 16.11.2026: 7 kommuner justeres, Tromsø er én."""
    justert = []
    assert len(fordeling["kommuner"]) == 143
    for nr, k in fordeling["kommuner"].items():
        sanne = (k["fra_egne"], k["fra_landet"])
        vist = nettsted._pp_deler(sanne, k["endring"])
        assert sum(map(_tusendeler, vist)) == _tusendeler(nettsted._pp(k["endring"])), nr
        for v, s in zip(vist, sanne):
            assert abs(_tusendeler(v) - s * 100 * 1000) < 1, (nr, v, s)
        if vist != [nettsted._pp(s) for s in sanne]:
            justert.append(nr)
    assert len(justert) == 7 and "5501" in justert, justert


@trenger_bygg
def test_delene_summerer_paa_hver_kommuneside():
    """Lest av sidene slik de er bygget: «Lokalitetene her» og «Resten av
    landet» er endringen i nøkkeltallene øverst, på alle 143."""
    sider = sorted((NETTSTED / "kommune").glob("*/index.html"))
    assert len(sider) == 143
    tall = r"([+−]?\d+,\d{3})"
    for fil in sider:
        side = fil.read_text("utf-8")
        total = re.search(rf'data-felt="endring"[^>]*>{tall}</dd>', side)
        egne = re.search(rf"<dt>Lokalitetene her</dt>\s*<dd>{tall}", side)
        landet = re.search(rf"<dt>Resten av landet</dt>\s*<dd>{tall}", side)
        assert total and egne and landet, fil
        assert _tusendeler(egne.group(1)) + _tusendeler(landet.group(1)) \
            == _tusendeler(total.group(1)), (fil.parent.name, egne.group(1),
                                            landet.group(1), total.group(1))
    tromso = (NETTSTED / "kommune" / "5501" / "index.html").read_text("utf-8")
    assert re.search(rf"<dt>Lokalitetene her</dt>\s*<dd>{tall}", tromso).group(1) == "−0,029"
    assert re.search(rf"<dt>Resten av landet</dt>\s*<dd>{tall}", tromso).group(1) == "−0,009"


# ------------------------------- andel er ikke beløp (gjennomgangen 12.11)

ANDEL_OG_BELOP = [
    "Andelen sier hvor stor del av utbetalingen hver kommune får, ikke hvor mye.",
    "Beløpet avhenger av hva staten har fått inn, og det anslår vi ikke."]


def test_setningene_om_andel_og_belop_staar_ett_sted():
    """De to sidene som viser dem, inkluderer samme mal, og ingen annen
    mal har sin egen kopi av teksten."""
    maler = Path(nettsted.MALER)
    egen = (maler / "andel-og-belop.html.j2").read_text("utf-8")
    assert all(s in egen for s in ANDEL_OG_BELOP)
    for navn in ("kommuner.html.j2", "fasit-havbruksfond.html.j2"):
        assert '{% include "andel-og-belop.html.j2" %}' in (maler / navn).read_text("utf-8"), navn
    andre = [m.name for m in maler.glob("*.j2") if m.name != "andel-og-belop.html.j2"
             and "Andelen sier hvor stor del" in m.read_text("utf-8")]
    assert andre == []


@trenger_bygg
def test_oversikten_sier_at_andelen_ikke_er_et_belop():
    """/kommune/ er der andelen vises første gang. De to setningene står
    over tabellen, etter linja om fordelingen, og er de samme som under
    statusen på siden med de forseglede anslagene. De 143 kommunesidene
    har dem ikke: de viser andelen for én kommune, med oversikten ett
    klikk unna."""
    oversikt = (NETTSTED / "kommune" / "index.html").read_text("utf-8")
    avsnitt = [_avsnitt(p) for p in re.findall(r"<p\b[^>]*>.*?</p>", _main(oversikt), re.S)]
    her = [avsnitt.index(s) for s in ANDEL_OG_BELOP]
    assert her[1] == her[0] + 1
    assert "ikke publisert ennå" in avsnitt[her[0] - 1] or \
        "har publisert fordelingen" in avsnitt[her[0] - 1]
    assert _main(oversikt).index(ANDEL_OG_BELOP[1]) < _main(oversikt).index('<table id="kommuner-andel"')
    assert all(len(s) <= 110 for s in ANDEL_OG_BELOP)
    fasit = (NETTSTED / "fasiten" / "havbruksfondet-2026" / "index.html").read_text("utf-8")
    assert all(s in _avsnitt(_main(fasit)) for s in ANDEL_OG_BELOP)
    med = [f.parent.name for f in (NETTSTED / "kommune").glob("*/index.html")
           if ANDEL_OG_BELOP[0] in f.read_text("utf-8")]
    assert med == []
