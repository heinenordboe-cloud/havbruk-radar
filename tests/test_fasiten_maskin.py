"""Maskinanslagene under /fasiten/ (økt 16b, 23.11.2026).

K2 og K6 forsegles hver uke fra uke 46. Uke 46 og 47 ligger i kodrepoet,
senere uker i datarepoet, og fasiten.json fører alle. Prøvene holder:

  1. Typene leses av data, og ingen mal under /fasiten/ har et typenavn
     (16b, 1a).
  2. Med en konstruert fasit, bygget av den ekte: én uke som bommet, én
     som traff og én åpen gir riktig rekkefølge, riktige ord og like
     rader (1b, 1f, 1i). Mønsteret er tests/test_fasit_konstruert.py:
     de ekte filene, med én ting endret.
  3. Kopiene (1d): hver uke i fasiten.json har sin kopi, og sha256 på
     hver kopi er den forseglinger.tsv førte, for fila og for stempelet.
     Bygget og porten stopper en kopi som ikke er det, hver prøvd med en
     feil laget med vilje.

Prøvene som leser de ekte ukene, trenger datarepoet ved siden av og
hoppes over uten det (fiksturen `ekte_maskin` i conftest.py). De siste
trenger et bygget nettsted og kjøres i porten.
"""
import copy
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import pytest

import anslag
import nettsted
import publiseringsvakt as v
import royktest
import skaar_anslag
from tests.test_fasiten import _main, _tekst

MALER = Path(__file__).resolve().parent.parent / "maler"
FASITMALER = ("fasiten.html.j2", "fasit-type.html.j2", "fasit-felles.html.j2")


# ------------------------------------------------- typene leses av data


def test_hver_registrert_type_har_navn_og_adresse_paa_nettstedet():
    """En type som er registrert og stemplet, får et navn og en adresse
    før den forsegles. Uten dem stopper fasen (se neste prøve)."""
    assert set(anslag.TYPER) <= set(nettsted.ANSLAGSTYPER)
    slugger = [m["slug"] for m in nettsted.ANSLAGSTYPER.values()]
    assert len(set(slugger)) == len(slugger)
    import havbruksfond as h
    assert h.FASITMAPPE.split("/")[1] not in slugger
    for m in nettsted.ANSLAGSTYPER.values():
        assert m["navn"] and m["ingress"] and m["kilder"]
        assert set(m["kilder"]) <= set(nettsted.kildevilkaar())


def test_en_type_uten_navn_stopper_fasen(tmp_path):
    f = {"anslag": [{"type": "K9", "klasse": "hovedtype", "uke": "2026-W46",
                     "repo": "havbruk-radar", "fil": "predictions/maskin/2026-46.yml"}]}
    with pytest.raises(ValueError, match="K9"):
        nettsted._maskintyper(f, None)


def _uten_kommentarer(mal: str) -> str:
    return re.sub(r"\{#.*?#\}", "", mal, flags=re.S)


def test_ingen_typenavn_i_malene():
    """Typene står i data, ikke i malene: navnene, kodene og adressene i
    `ANSLAGSTYPER`, og havbruksfondet i de forseglede filene."""
    import havbruksfond as h
    forbudt = {"Havbruksfond", "havbruksfond", "K2", "K6", str(h.AAR)}
    for m in nettsted.ANSLAGSTYPER.values():
        forbudt |= {m["navn"], m["slug"]}
    forbudt |= {k for k in nettsted.ANSLAGSTYPER}
    for navn in FASITMALER:
        tekst = _uten_kommentarer((MALER / navn).read_text(encoding="utf-8"))
        assert [f for f in forbudt if f in tekst] == [], navn


def test_ukene_leses_av_fila_og_skrives_paa_norsk():
    assert nettsted._ukene_vist("antall i uke 2026-W41 … 2026-W44") == "uke 41–44, 2026"
    assert nettsted._ukene_vist("snitt i uke 2026-W52") == "uke 52, 2026"
    assert nettsted._ukene_vist("uke 2026-W52 … 2027-W03") == "uke 52, 2026–uke 3, 2027"
    assert nettsted._ukene_vist("ingen uke") == ""


# ------------------------------------------------- den konstruerte fasiten


def _ekte(ekte_maskin) -> dict:
    if not ekte_maskin:
        pytest.skip("datarepoet med fasiten.json ligger ikke ved siden av")
    return json.loads(skaar_anslag.FASIT.read_text(encoding="utf-8"))


def _avgjor(f: dict, uke: str, traff: bool) -> None:
    """K2 i `uke` avgjort for hver PO. Traff: utfallet er anslaget, og
    modellen slår begge referansene. Bom: utfallet er siste verdi, og
    referansen a kan ikke slås."""
    for r in f["anslag"]:
        if r["type"] != "K2" or r["uke"] != uke:
            continue
        m, a, b = r["anslag"], r["referanse_a"], r["referanse_b"]
        y = m if traff else a
        fm, fa, fb = abs(y - m), abs(y - a), abs(y - b)
        r.update(status="avgjort", grunn="", utfall=y,
                 skaar={"feil_modell": round(fm, 4), "feil_a": round(fa, 4),
                        "feil_b": round(fb, 4), "slo_begge": fm < fa and fm < fb})
        assert r["skaar"]["slo_begge"] is traff, r["id"]


@pytest.fixture
def konstruert(ekte_maskin, tmp_path):
    """Den ekte fasiten med uke 46 bommet og uke 47 truffet for K2. Uke 48
    og K6 er åpne, som i dag. Uka som bommet, åpner før den som traff:
    står den likevel etter, er den flyttet ned."""
    f = copy.deepcopy(_ekte(ekte_maskin))
    if "2026-W48" not in {r["uke"] for r in f["anslag"]}:
        pytest.skip("uke 48 er ikke forseglet i dette datarepoet")
    _avgjor(f, "2026-W46", traff=False)
    _avgjor(f, "2026-W47", traff=True)
    f["treffliste"]["K2"]["avgjorte_uker"] = 2
    ut = tmp_path / "ut"
    stier = nettsted.skriv_fasiten(ut, maskin=f)
    assert stier == ["/fasiten/", "/fasiten/havbruksfondet-2026/",
                     "/fasiten/brakklegging/", "/fasiten/voksne-hunnlus/"]
    return ut


def _rader(side: str, tabell: str) -> list[str]:
    """`<tr>` i tbody i tabellen med `id`, som markup."""
    m = re.search(rf'<table id="{tabell}".*?<tbody>(.*?)</tbody>', side, re.S)
    assert m, tabell
    return re.findall(r"<tr>.*?</tr>", m.group(1), re.S)


def _form(markup: str) -> str:
    """Raden uten det som SKAL være ulikt: tallene og ordet."""
    return re.sub(r"\b(Traff|Bom)\b", "ORD", re.sub(r"\d+(?:,\d+)?", "0", markup))


def test_oversikten_har_aapne_foerst_og_bommen_der_datoen_setter_den(konstruert):
    side = (konstruert / "fasiten" / "index.html").read_text("utf-8")
    aapne = [_tekst(r) for r in _rader(side, "fasit-aapne")]
    avgjorte = [_tekst(r) for r in _rader(side, "fasit-avgjorte")]
    assert aapne == [
        "– Havbruksfondet 2026 12.10.2026 og 09.11.2026 10 Venter på fordelingen",
        "11.01.2027 Brakklegging per produksjonsområde, uke 48, 2026 23.11.2026 13 Åpen"]
    assert avgjorte == [
        "28.12.2026 Brakklegging per produksjonsområde, uke 46, 2026 10.11.2026 13 "
        "13 avgjort: 0 traff, 13 bom",
        "04.01.2027 Brakklegging per produksjonsområde, uke 47, 2026 17.11.2026 13 "
        "13 avgjort: 13 traff, 0 bom"]
    tekst = _tekst(_main(side))
    assert ("Neste fasit 11.01.2027 · Brakklegging per produksjonsområde, uke 48, 2026 · "
            "13 påstander") in tekst
    assert "Brakklegging per produksjonsområde: 2 av 12 uker avgjort." in tekst
    # Prøvetypen står nederst, merket, og etter regelen om nye typer.
    assert tekst.index("Prøvetype Voksne hunnlus per fisk, per produksjonsområde") > tekst.index(
        "Avgjorte påstander")


def test_en_uke_som_bommet_og_en_som_traff_har_like_rader(konstruert):
    """Samme plass, samme skrift: radene er like når tallene og ordet er
    tatt ut, i oversikten og på typesiden."""
    side = (konstruert / "fasiten" / "index.html").read_text("utf-8")
    bom, traff = _rader(side, "fasit-avgjorte")
    assert _form(bom) == _form(traff)
    type_ = (konstruert / "fasiten" / "brakklegging" / "index.html").read_text("utf-8")
    bom_rader = _rader(type_, "uke-2026-46-tabell")
    traff_rader = _rader(type_, "uke-2026-47-tabell")
    assert [_form(r) for r in bom_rader] == [_form(r) for r in traff_rader]
    # Ordet, utfallet og avviket, i den cella og i den rekkefølgen. Uten
    # `felles` har området ikke navn, bare nummer.
    po3 = [_tekst(r) for r in (bom_rader[2], traff_rader[2])]
    # Én desimal i hver tallcelle, også utfallet og avviket (16b, rettinger 4).
    en = r"\d+,\d"
    assert re.fullmatch(rf"3 {en} ({en}) {en} Bom · utfall \1 · avvik {en}", po3[0]), po3[0]
    assert re.fullmatch(rf"3 ({en}) {en} {en} Traff · utfall \1 · avvik 0,0", po3[1]), po3[1]


def test_anslagene_har_en_desimal_og_fila_har_den_forseglede(konstruert, ekte_maskin):
    """3,548 sto ved siden av 4,0829 (16b, rettinger 4). Hver tallcelle på
    typesidene har én desimal, avrundet, og under hver tabell står at den
    forseglede verdien står i ukefila. Ukefila og kopien er uendret."""
    assert nettsted._maaltall(4.0829, 1) == "4,1"
    assert nettsted._maaltall(3.548, 1) == "3,5"
    assert nettsted._maaltall(7, 1) == "7,0"
    assert nettsted._maaltall(None, 1) is None
    assert nettsted._maaltall(4.0829) == "4,0829"          # uten: som i fila
    for slug in ("brakklegging", "voksne-hunnlus"):
        side = (konstruert / "fasiten" / slug / "index.html").read_text("utf-8")
        celler = re.findall(r'<td class="tall"[^>]*data-felt="(?:anslag|referanse_[ab])"[^>]*>([^<]*)</td>',
                            side)
        assert celler and all(re.fullmatch(r"\d+,\d|–", c) for c in celler), slug
        tabeller = len(re.findall(r'<table[^>]*class="[^"]*\bfasit-anslag\b', side))
        assert side.count("Avrundet. Den forseglede verdien står i ukefila.") == tabeller, slug
    # Kopien av ukefila er byte for byte den forseglede.
    import skaar_anslag
    for k in skaar_anslag.forseglede_kopier(_ekte(ekte_maskin)):
        if k["slag"] == "fil":
            assert (konstruert / k["sti"]).read_bytes() == k["kilde"].read_bytes()


def test_grunnen_til_skaares_ikke_staar_i_klartekst():
    """Hvilke områder, hvilken verdi og hvilken uke (16b, rettinger 5),
    lest av grunnen i fasiten.json. En grunn i en annen form gir den
    generelle setningen, ikke en halv oversettelse."""
    g = "færre enn 5 lokaliteter med lusetall og lusegrense i uke"
    rader = [
        {"po": 13, "status": "skåres ikke", "grunn": f"skåres ikke: referanse b mangler ({g} 2025-W52)"},
        {"po": 2, "status": "åpen", "grunn": ""},
        {"po": 1, "status": "skåres ikke", "grunn": f"skåres ikke: referanse a mangler ({g} 2026-W44); "
                                                    "anslaget mangler (det bygger på referanse a)"}]
    assert nettsted._skaares_ikke_grunn(rader) == {
        "innledning": ["Områdene 1 og 13 skåres ikke.",
                       "Der hadde færre enn 5 lokaliteter lusetall og lusegrense i uka "
                       "verdien gjelder:"],
        "punkter": ["Område 1: siste verdi (uke 44, 2026). Anslaget bygger på den og "
                    "mangler også.",
                    "Område 13: verdien i fjor (uke 52, 2025)."]}
    assert nettsted._skaares_ikke_grunn(rader[1:2]) is None
    rart = [{"po": 4, "status": "skåres ikke", "grunn": "skåres ikke: utfallet mangler"}]
    assert nettsted._skaares_ikke_grunn(rart)["punkter"] == []


def test_typesiden_har_aapne_uker_foerst_og_saa_etter_aapningsdato(konstruert):
    type_ = (konstruert / "fasiten" / "brakklegging" / "index.html").read_text("utf-8")
    assert re.findall(r'<section class="[^"]*\bfasit-blokk\b[^"]*" id="(uke-[\d-]+)"',
                      type_) == [
        "uke-2026-48", "uke-2026-46", "uke-2026-47"]
    tekst = _tekst(_main(type_))
    assert "2 av 12 uker avgjort. 26 avgjort: 13 traff, 13 bom." in tekst
    # Den åpne uka har ingen statuskolonne: tretten «Åpen» er én
    # forklaring gjentatt per rad.
    assert "<th scope=\"col\">Status</th>" not in type_.split('id="uke-2026-46"')[0]


def test_slik_sjekker_du_oss_ber_om_stempelet_med_blokka(konstruert):
    """Heines tekst (16b, rettinger 2) på /fasiten/ og typesidene: ukefila,
    .komplett.ots og den korte summen, opentimestamps.org merket som ekstern,
    og ingen `--no-bitcoin`, som bare viser blokka."""
    for rel in ("fasiten/index.html", "fasiten/brakklegging/index.html"):
        side = (konstruert / rel).read_text("utf-8")
        seksjon = re.search(r'<section[^>]*id="sjekk".*?</section>', side, re.S).group(0)
        punkt = [_tekst(li) for li in re.findall(r"<li>.*?</li>", seksjon, re.S)]
        assert punkt[0] == "Last ned 2026-48.yml og stempelet med blokka (2026-48.yml.komplett.ots).", rel
        assert re.fullmatch(r"shasum -a 256 2026-48\.yml skal gi [0-9a-f]{8}…[0-9a-f]{4}\.",
                            punkt[1]), punkt[1]
        assert punkt[2] == ("Dra begge filene inn på opentimestamps.org. Den viser hvilken "
                            "Bitcoin-blokk stempelet ligger i. Med egen Bitcoin-node: ots verify.")
        assert 'href="/fasiten/2026-48.yml.komplett.ots" download' in seksjon
        assert 'rel="external"' in seksjon and 'aria-label="ekstern side"' in seksjon
        assert "no-bitcoin" not in side, rel


def test_slik_sjekker_du_oss_bruker_siste_uke_med_blokka(ekte_maskin, monkeypatch):
    """En uke er forseglet timer før stempelet med blokka finnes. Uten
    .komplett.ots for uke 48 står uke 47 i «Slik sjekker du oss», og
    forsiden sier fortsatt at uke 48 er sist forseglet."""
    import skaar_anslag
    f = copy.deepcopy(_ekte(ekte_maskin))
    ekte = skaar_anslag.forseglede_kopier
    monkeypatch.setattr(skaar_anslag, "forseglede_kopier", lambda m=None: [
        k for k in ekte(m) if not (k["uke"] == "2026-W48" and k["slag"] == "komplett")])
    o = nettsted.bygg_fasiten(maskin=f)
    assert o["sjekk"]["uke"] == "2026-W47" and o["sjekk"]["komplett"] == "2026-47.yml.komplett.ots"
    assert {t["sjekk"]["uke"] for t in o["typer"]} == {"2026-W47"}
    assert {t["siste"]["uke"] for t in o["typer"]} == {"2026-W48"}


def test_porten_har_ingenting_aa_innvende_mot_den_konstruerte(konstruert):
    for side in sorted(konstruert.glob("fasiten/**/index.html")):
        rel = side.relative_to(konstruert).as_posix()
        assert v.tekstfunn(rel, ".html", side.read_text("utf-8"), set(), set()) == [], rel
    assert v.jsonldfunn(konstruert) == []


# ---------------------------------------------------------------- kopiene


def _forseglinger() -> dict[str, dict]:
    """{uke: rad} fra forseglinger.tsv begge steder, lest her og ikke av
    koden som skal prøves."""
    ut = {}
    for mappe in (anslag.KODE_MASKIN, anslag.MASKIN_DIR):
        linjer = (mappe / "forseglinger.tsv").read_text(encoding="utf-8").splitlines()
        hode = linjer[0].split("\t")
        for linje in linjer[1:]:
            rad = dict(zip(hode, linje.split("\t")))
            ut.setdefault(rad["uke"], {**rad, "mappe": mappe})
    return ut


def _sum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _holder_kopiene(rot: Path, f: dict) -> None:
    """Hver uke i fasiten har sin kopi, med summene forseglinger.tsv førte."""
    ført = _forseglinger()
    uker = sorted({r["uke"] for r in f["anslag"]})
    assert uker, "fasiten har ingen uker"
    for uke in uker:
        rad = ført[uke]
        fil = rot / "fasiten" / rad["fil"]
        assert _sum(fil.read_bytes()) == rad["sha256"], fil
        ots = rot / "fasiten" / (rad["fil"] + ".ots")
        assert _sum(ots.read_bytes()) == rad["ots_sha256"], ots
        komplett = rad["mappe"] / (rad["fil"] + ".komplett.ots")
        kopi = rot / "fasiten" / komplett.name
        assert kopi.exists() == komplett.exists(), kopi
        if komplett.exists():
            assert kopi.read_bytes() == komplett.read_bytes(), kopi


def test_bygget_skriver_en_kopi_av_hver_uke_med_summene_fra_forseglingen(ekte_maskin, tmp_path):
    f = _ekte(ekte_maskin)
    nettsted.skriv_forseglede(tmp_path, f)
    _holder_kopiene(tmp_path, f)
    # Ingen andre ukefiler enn fasitens.
    assert sorted(p.name for p in (tmp_path / "fasiten").glob("*.yml")) == sorted(
        {Path(r["fil"]).name for r in f["anslag"]})


@pytest.fixture
def falske_mapper(ekte_maskin, tmp_path, monkeypatch):
    """Kopier av begge mappene, som kan ødelegges."""
    _ekte(ekte_maskin)
    kode, data = tmp_path / "kode", tmp_path / "data"
    shutil.copytree(anslag.KODE_MASKIN, kode)
    shutil.copytree(anslag.MASKIN_DIR, data)
    monkeypatch.setattr(anslag, "KODE_MASKIN", kode)
    monkeypatch.setattr(anslag, "MASKIN_DIR", data)
    monkeypatch.setattr(skaar_anslag, "FASIT", data / "fasiten.json")
    return kode, data


def test_en_endret_ukefil_stopper_bygget_og_ingenting_skrives(falske_mapper, tmp_path):
    kode, _ = falske_mapper
    fil = kode / "2026-47.yml"
    fil.write_bytes(fil.read_bytes() + b"\n")
    ut = tmp_path / "ut"
    with pytest.raises(ValueError, match="2026-47.yml"):
        nettsted.skriv_forseglede(ut, skaar_anslag.les_fasit())
    assert not list(ut.rglob("*.yml"))


def test_et_oppgradert_stempel_for_en_annen_uke_stopper_bygget(falske_mapper, tmp_path):
    kode, _ = falske_mapper
    shutil.copy(kode / "2026-46.yml.komplett.ots", kode / "2026-47.yml.komplett.ots")
    with pytest.raises(ValueError, match="gjelder ikke ukefila"):
        nettsted.skriv_forseglede(tmp_path / "ut", skaar_anslag.les_fasit())


def test_porten_feller_en_kopi_som_ikke_er_den_forseglede(ekte_maskin, tmp_path):
    f = _ekte(ekte_maskin)
    nettsted.skriv_fasiten(tmp_path, maskin=f)
    funn, ok = v.forseglingsfunn(tmp_path)
    assert funn == []
    kopier = skaar_anslag.forseglede_kopier()
    assert {k["sti"] for k in kopier} <= ok
    # En byte i en ukefil.
    fil = tmp_path / "fasiten" / "2026-46.yml"
    fil.write_bytes(fil.read_bytes().replace(b"K2", b"K3", 1))
    # Et stempel som er en annen ukes.
    shutil.copy(tmp_path / "fasiten" / "2026-46.yml.ots", tmp_path / "fasiten" / "2026-47.yml.ots")
    # En kopi som mangler, mens /fasiten/ lenker til den.
    (tmp_path / "fasiten" / "2026-46.yml.komplett.ots").unlink()
    funn, ok = v.forseglingsfunn(tmp_path)
    assert sorted(x.fil for x in funn) == ["fasiten/2026-46.yml", "fasiten/2026-46.yml.komplett.ots",
                                          "fasiten/2026-47.yml.ots"]
    assert not {x.fil for x in funn} & ok


def test_roykttesten_finner_ukefilene_og_lenkene_til_dem(ekte_maskin, tmp_path):
    f = _ekte(ekte_maskin)
    nettsted.skriv_fasiten(tmp_path, maskin=f)
    nettsted.skriv_vertsfiler(tmp_path)
    funnet = {x.sti: x.innholdstype for x in royktest.forseglede(tmp_path)}
    for k in skaar_anslag.forseglede_kopier():
        assert "/" + k["sti"] in funnet, k["sti"]
    assert funnet["/fasiten/2026-46.yml"] == "text/plain; charset=utf-8"
    assert funnet["/fasiten/2026-46.yml.ots"] == "application/octet-stream"
    type_ = (tmp_path / "fasiten" / "brakklegging" / "index.html").read_text("utf-8")
    lenket = set(royktest._FORSEGLET_LENKE.findall(type_))
    assert {"/fasiten/2026-46.yml", "/fasiten/2026-46.yml.ots",
            "/fasiten/2026-46.yml.komplett.ots"} <= lenket


# ------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "fasiten" / "index.html").exists(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted med /fasiten/")


@trenger_bygg
def test_portens_bygg_har_en_kopi_av_hver_uke_i_fasiten(ekte_maskin):
    _holder_kopiene(NETTSTED, _ekte(ekte_maskin))


@trenger_bygg
def test_portens_bygg_har_en_side_per_type_og_neste_fasit(ekte_maskin):
    f = _ekte(ekte_maskin)
    for kode in {r["type"] for r in f["anslag"]}:
        assert (NETTSTED / "fasiten" / nettsted.ANSLAGSTYPER[kode]["slug"] / "index.html").exists()
    tekst = _tekst(_main((NETTSTED / "fasiten" / "index.html").read_text("utf-8")))
    assert "Neste fasit" in tekst and "Slik sjekker du oss" in tekst
    assert ("Nye typer anslag legges bare til etter at de er målt mot enkle referanser, "
            "og registreres og stemples før første forsegling.") in tekst


@trenger_bygg
def test_bunnteksten_paa_fasitsidene_oppgir_den_nyeste_hentingen(ekte_maskin):
    """/fasiten/ sto med havbruksfondets nøkkel fra 31.08 og typesidene
    med uka lusetallene gjelder (16b, rettinger 3). Nå: når de nyeste
    dataene på siden ble hentet, og der lusetall vises, linja om uka.
    Typesidene oppgir lusetallene fasiten er skåret mot (`data_til`), og
    oversikten den nyeste av dem og havbruksfondets side."""
    def bunn(rel):
        side = (NETTSTED / rel).read_text("utf-8")
        blokk = re.search(r'<div class="ark bunn-proveniens".*?</div>', side, re.S).group(0)
        attr = dict(re.findall(r'data-proveniens-(\w+)="([^"]*)"', blokk))
        return attr, _tekst(blokk)
    oversikt, o_tekst = bunn("fasiten/index.html")
    fondet, _ = bunn("fasiten/havbruksfondet-2026/index.html")
    for slug in ("brakklegging", "voksne-hunnlus"):
        attr, tekst = bunn(f"fasiten/{slug}/index.html")
        assert (attr["kilde"], attr["gjelder"]) == ("lusetall", _ekte(ekte_maskin)["data_til"])
        assert tekst.startswith("Data hentet " + nettsted.visningsord.tidspunkt(attr["hentet"]))
        assert "Lusetallene gjelder uka de er datert til." in tekst, slug
        assert oversikt["hentet"] >= attr["hentet"]
    assert oversikt["hentet"] >= fondet["hentet"]
    assert "Lusetallene gjelder" not in o_tekst


# ------------------------------------------------- menyen (16b, 3)


def test_fasitsidene_merker_fasiten_i_menyen(tmp_path):
    """Kommuner og Fasiten står i menyen fra 16b, og siden du står på er
    merket med `aria-current`, som de andre punktene."""
    nettsted.skriv_fasiten(tmp_path)
    for side in sorted(tmp_path.glob("fasiten/**/index.html")):
        meny = re.search(r'<nav class="hovedmeny".*?</nav>', side.read_text("utf-8"), re.S).group(0)
        assert re.findall(r'aria-current="page">([^<]+)<', meny) == ["Fasiten"], side


@trenger_bygg
def test_portens_bygg_merker_kommunene_og_fasiten_i_menyen():
    for rel, ventet in (("kommune/index.html", "Kommuner"), ("kommune/1580/index.html", "Kommuner"),
                        ("fasiten/index.html", "Fasiten"),
                        ("fasiten/brakklegging/index.html", "Fasiten")):
        meny = re.search(r'<nav class="hovedmeny".*?</nav>',
                         (NETTSTED / rel).read_text("utf-8"), re.S).group(0)
        assert re.findall(r'aria-current="page">([^<]+)<', meny) == [ventet], rel
        assert 'href="/kommune/"' in meny and 'href="/fasiten/"' in meny
