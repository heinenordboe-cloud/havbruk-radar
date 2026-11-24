"""Forsiden fra økt 16b (23.11.2026): de tre flatene og tallbåndet.

  1. Flate c er ÉN endring med navn, valgt etter en regel i koden: størst
     kapasitetsendring i tonn, ellers et eierskifte, ellers en ny
     lokalitet. Et navn som kan være en person, står aldri der.
  2. Havbruksfondet står først så lenge fordelingen ikke er kommet, og i
     sju dager etter fasiten, også ved bom. Så står det sist.
  3. Tallbåndet: startdatoen og ukene på rad uten hull, målt fra
     snapshotene. Et hull vises som et hull.
  4. Ingen tall i forsidens mal for flatene, og ingen anslagstall på den
     bygde forsiden (regelen fra 10.11.2026, i BRIEF fra 16b).

De siste prøvene trenger et bygget nettsted og kjøres i porten.
"""
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import nettsted

MALER = Path(__file__).resolve().parent.parent / "maler"


# --------------------------------------------------------- ukas endring


def _h(slag, felt, eid, fra="", til="", **mer):
    return {"type": slag, "kildefelt": felt, "entity_id": eid, "fra": fra, "til": til,
            "gjelder": mer.pop("gjelder", eid), "gjelder_url": mer.pop("url", f"/x/{eid}/"),
            "kilde": mer.pop("kilde", ""), **mer}


def _felles(person: set[str] = frozenset()):
    eierskap = {
        "T-1": {"eier_orgnr": "911111111", "eier_navn": "STOR LAKS AS",
                "eier_type": "LimitedLiabilityCompany", "kapasitet": "3600.0",
                "kapasitet_enhet": "TN"},
        "T-2": {"eier_orgnr": "922222222", "eier_navn": "LITEN LAKS AS",
                "eier_type": "LimitedLiabilityCompany", "kapasitet": "780.0",
                "kapasitet_enhet": "TN"},
        "T-3": {"eier_orgnr": "933333333", "eier_navn": "STYKK AS",
                "eier_type": "LimitedLiabilityCompany", "kapasitet": "90000.0",
                "kapasitet_enhet": "STK"},
    }
    for nr in person:
        eierskap[nr]["eier_type"] = "SoleProprietorship"
    per_eier: dict[str, list[str]] = {}
    for nr, t in eierskap.items():
        per_eier.setdefault(t["eier_orgnr"], []).append(nr)
    akva = {"10001": {"kapasitet": "3120.0", "kapasitet_enhet": "TN", "kommune": "HITRA"},
            "45311": {"kapasitet": "1200.0", "kapasitet_enhet": "TN",
                      "kommune": "HJELMELAND"}}
    return SimpleNamespace(eierskap=eierskap, akva=akva, tillatelser_per_eier=per_eier)


def _tekst(ledd) -> str:
    return "".join(s["tekst"] for s in ledd) if ledd else ""


def test_stoerst_kapasitetsendring_i_tonn_vinner():
    rader = [_h("tillatelse", "kapasitet", "T-2", "780", "900"),
             _h("tillatelse", "kapasitet", "T-1", "3 600", "3 640"),
             # STYKK, ikke tonn: et større tall, men ikke i tonn.
             _h("tillatelse", "kapasitet", "T-3", "90 000", "120 000"),
             _h("eierskap", "eier_orgnr", "T-1", "999999999", "911111111")]
    ledd = nettsted.ukas_endring({"ledet": rader}, _felles())
    assert _tekst(ledd) == ("Liten Laks AS: kapasiteten på tillatelse T-2 økte fra 780 "
                            "til 900 tonn.")
    navn = [s for s in ledd if s["url"]]
    assert navn == [{"tekst": "Liten Laks AS", "url": "/selskap/922222222/",
                     "felt": "eier_navn", "kode": False}]
    assert [s["tekst"] for s in ledd if s["kode"]] == ["T-2"]


def test_en_lokalitet_kan_vinne_og_nedgang_er_nedgang():
    rader = [_h("tillatelse", "kapasitet", "T-2", "780", "800"),
             _h("lokalitet", "kapasitet", "10001", "3 120", "2 340",
                gjelder="Ulvan", url="/lokalitet/10001/")]
    assert _tekst(nettsted.ukas_endring({"ledet": rader}, _felles())) == (
        "Ulvan i Hitra: kapasiteten gikk ned fra 3 120 til 2 340 tonn.")


def test_en_person_som_eier_hoppes_over():
    """Den største endringen gjelder en tillatelse med en eier kilden
    klassifiserer som person. Den står ikke; den neste gjør det."""
    rader = [_h("tillatelse", "kapasitet", "T-1", "3 600", "4 000"),
             _h("tillatelse", "kapasitet", "T-2", "780", "800")]
    ledd = nettsted.ukas_endring({"ledet": rader}, _felles(person={"T-1"}))
    assert _tekst(ledd).startswith("Liten Laks AS:")
    assert "Stor Laks" not in _tekst(ledd)


def test_ellers_et_eierskifte_og_ellers_en_ny_lokalitet():
    skifte = [_h("eierskap", "eier_orgnr", "T-2", "999999999", "922222222"),
              _h("eierskap", "eier_orgnr", "T-1", "988888888", "911111111"),
              _h("ny", "navn", "45311", gjelder="Breivik", url="/lokalitet/45311/",
                 kilde="akvakultur")]
    # Eierskiftet på tillatelsen med størst kapasitet i tonn.
    assert _tekst(nettsted.ukas_endring({"ledet": skifte}, _felles())) == (
        "Tillatelse T-1 fikk ny eier: Stor Laks AS.")
    ny = [r for r in skifte if r["type"] == "ny"]
    assert _tekst(nettsted.ukas_endring({"ledet": ny}, _felles())) == (
        "Ny lokalitet: Breivik i Hjelmeland.")


def test_uten_noen_av_dem_staar_ingen_flate_og_ingen_ingen_linje():
    rader = [_h("biomasse", "har_fisk", "10001", "Nei", "Ja"),
             _h("tillatelse", "kapasitet", "T-3", "90 000", "120 000")]
    assert nettsted.ukas_endring({"ledet": rader}, _felles()) is None
    assert nettsted.ukas_endring(None, _felles()) is None


# --------------------------------------------- havbruksfondet først


def _flater(monkeypatch, i_dag: str, hentet: str | None):
    d = {"navn": "Havbruksfondet 2026", "sti": "/fasiten/havbruksfondet-2026/",
         "forseglinger": [{"dato": "2026-10-12"}, {"dato": "2026-11-09"}],
         "kommuner": 143, "oppsummert": "Venter på fordelingen" if hentet is None
         else "9 avgjort: 2 traff, 7 bom",
         "fasit": None if hentet is None else {"hentet": hentet}}
    k2 = {"navn": "Brakklegging per produksjonsområde", "sti": "/fasiten/brakklegging/",
          "siste": {"uke": "2026-W48"}, "neste": {"uke": "2026-W46", "aapner": "2026-12-28"},
          "uker_vist": "0 av 12 uker avgjort"}
    monkeypatch.setattr(nettsted, "bygg_fasiten",
                        lambda felles: {"havbruksfond": d, "hovedtyper": [k2]})
    monkeypatch.setattr(nettsted, "byggedato", lambda: i_dag)
    monkeypatch.setattr(nettsted, "ukas_endring", lambda uke, felles: None)
    return nettsted.forsideflater(None, None)


def test_havbruksfondet_staar_foerst_til_sju_dager_etter_fasiten(monkeypatch):
    uten = _flater(monkeypatch, "2026-11-23", None)
    assert [f["etikett"] for f in uten] == ["Havbruksfondet 2026",
                                           "Brakklegging per produksjonsområde"]
    assert uten[0]["tekst"] == ("Andelen for 143 kommuner, forseglet 12.10.2026 og "
                                "09.11.2026. Venter på fordelingen.")
    # Hver dato med sin uke: neste fasit gjelder uke 46, ikke den sist
    # forseglede (16b, rettinger 1).
    assert uten[1]["tekst"] == ("Sist forseglet: uke 48. Neste fasit: 28.12.2026 "
                                "(uke 46). 0 av 12 uker avgjort.")
    # Også ved bom: sju dager etter fasiten står det først, så sist.
    assert _flater(monkeypatch, "2026-12-08", "2026-12-01T09:00:00+00:00")[0][
        "etikett"] == "Havbruksfondet 2026"
    etter = _flater(monkeypatch, "2026-12-09", "2026-12-01T09:00:00+00:00")
    assert etter[-1]["etikett"] == "Havbruksfondet 2026"
    assert etter[-1]["tekst"].endswith("9 avgjort: 2 traff, 7 bom.")


# --------------------------------------------------------- tallbåndet


def test_ukene_paa_rad_og_hullene():
    uker = ["2026-08-17", "2026-08-24", "2026-08-31"]
    assert nettsted.arkivrekke(uker) == {
        "fra": "2026-08-17", "fra_rad": "2026-08-17", "paa_rad": 3, "hull": []}
    # To hentinger i samme uke er én uke; en uke uten er et hull.
    med_hull = ["2026-08-16", "2026-08-17", "2026-08-24", "2026-09-14", "2026-09-21"]
    assert nettsted.arkivrekke(med_hull) == {
        "fra": "2026-08-16", "fra_rad": "2026-09-14", "paa_rad": 2,
        "hull": ["uke 36, 2026", "uke 37, 2026"]}
    assert nettsted.arkivrekke([])["paa_rad"] == 0


def test_ingen_tall_i_malen_for_flatene_og_tallbaandet():
    mal = re.sub(r"\{#.*?#\}", "", (MALER / "forside.html.j2").read_text(encoding="utf-8"),
                 flags=re.S)
    flater = re.search(r'<section class="ark flater".*?</section>', mal, re.S).group(0)
    baand = re.search(r'<ul class="arkivtall">.*?</ul>', mal, re.S).group(0)
    for del_ in (flater, baand):
        uten_kode = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", "", del_, flags=re.S)
        assert not re.findall(r"\d", re.sub(r"<[^>]+>", "", uten_kode)), del_[:80]


# ------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").exists(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted")


@trenger_bygg
def test_ingen_anslagstall_paa_forsiden(ekte_maskin):
    """Forsiden sier hva som er forseglet og når fasiten åpner, aldri hva
    anslaget var. Hvert anslag og hver referanse med desimaler i
    fasiten.json, slik siden ville skrevet det, står ikke på forsiden."""
    if not ekte_maskin:
        pytest.skip("datarepoet med fasiten.json ligger ikke ved siden av")
    import skaar_anslag
    from visningsord import tall
    f = json.loads(skaar_anslag.FASIT.read_text(encoding="utf-8"))
    tekst = " ".join(re.sub(r"<[^>]+>", " ",
                            (NETTSTED / "index.html").read_text("utf-8")).split())
    verdier = {tall(r[k]) for r in f["anslag"] for k in ("anslag", "referanse_a", "referanse_b")
               if isinstance(r[k], float) and r[k] != int(r[k])}
    assert verdier, "fasiten har ingen tall med desimaler; prøven ser ingenting"
    assert sorted(v for v in verdier if v in tekst) == []
    assert "Neste fasit:" in tekst and "Sist forseglet: uke" in tekst
