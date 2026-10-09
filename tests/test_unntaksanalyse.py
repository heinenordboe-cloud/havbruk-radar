"""unntaksanalyse.py: vilkårene leses ordrett av arkivkroppen.

Kroppene her er bygget i Lovdatas form slik den er MÅLT 09.10.2026:
avsnitt i `<p class="avsnitt">`, listepunkter i `<table class="listeItem"
data-level="N">`, fotnoten i en tabell med `fotnote` i klassen.
"""

import gzip

import pytest

import unntaksanalyse as u
from core import paths


def _ledd_html(nivaa: int, nummer: str, tekst: str) -> str:
    if not nummer:
        return f'<p data-uid="0" class="morTag_a avsnitt">{tekst}</p>'
    return (f'<table data-level="{nivaa}" class="morTag_n leftMargin_{nivaa} '
            f'listeItem avsnitt no-text-indent"><tr>'
            f'<td class="listeitemNummer">{nummer}</td>'
            f'<td class="morTableAlignLeft">{tekst}</td></tr></table>')


def _dokument(paragrafer: dict[str, list[tuple]], fotnote: str = "") -> bytes:
    deler = ['<html><body><div class="toc">§ 12. Tilbud</div>']
    for nr, blokker in paragrafer.items():
        deler.append(f'<div data-id="PARAGRAF_{nr}" class="morTag_p paragraf" '
                     f'id="PARAGRAF_{nr}"><h3 class="paragrafHeader">§ {nr}.</h3>')
        deler += [_ledd_html(*b) for b in blokker]
        if fotnote:
            deler.append('<table class="textList fotnote avsnitt liste"><tr>'
                         '<td class="fotnoteNummer">0</td>'
                         f'<td class="fotnote">{fotnote}</td></tr></table>')
        deler.append("<div><span>indre div</span></div></div>")
    deler.append("</body></html>")
    return "".join(deler).encode("utf-8")


# § 12 slik den står, forkortet til starten av hvert ledd pluss litt.
PARAGRAF_12 = [(n, nr, start + " …") for n, nr, start in u.FORVENTET_12]


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


def _legg(arkiv, mappe: str, navn: str, data: bytes) -> None:
    (arkiv / mappe).mkdir(parents=True, exist_ok=True)
    with gzip.open(arkiv / mappe / navn, "wb") as f:
        f.write(data)


def _alle(arkiv, p12=PARAGRAF_12, lti_ekstra=()):
    sf = _dokument({"12": p12, "12a": [(0, "", "Søknad … innen 1. september i "
                                                "oddetallsår.")]},
                   fotnote="Endret ved forskrifter 28 sep 2023 nr. 1520.")
    lti = _dokument({"12": PARAGRAF_12 + list(lti_ekstra)})
    lus = _dokument({"8": [(0, "", "færre enn 0,5 voksen hunnlus")]})
    _legg(arkiv, "lovdata-produksjonsomradeforskriften", "2026-10-09.bin.gz", sf)
    _legg(arkiv, "lovdata-produksjonsomradeforskriften-endring-2023",
          "2026-10-09.bin.gz", lti)
    _legg(arkiv, "lovdata-lakselusforskriften", "2026-10-09.bin.gz", lus)
    _legg(arkiv, "trafikklysvedtak", "2026-12-31.bin.gz", b"<p>kap. 4</p>")


def test_paragrafen_leses_blokk_for_blokk_og_stopper_ved_sin_div():
    data = _dokument({"12": PARAGRAF_12, "12a": [(0, "", "neste paragraf")]})
    blokker, fotnote = u.paragraf(data, "12")
    assert [(b.nivaa, b.nummer) for b in blokker] == \
           [(n, nr) for n, nr, _ in u.FORVENTET_12]
    assert all("neste paragraf" not in b.tekst for b in blokker), \
        "en indre div skal ikke avslutte paragrafen for tidlig, og § 12a " \
        "skal ikke lekke inn"
    assert fotnote == []


def test_fotnoten_er_ikke_et_ledd():
    data = _dokument({"12": PARAGRAF_12}, fotnote="Endret ved forskrift X.")
    blokker, fotnote = u.paragraf(data, "12")
    assert len(blokker) == len(u.FORVENTET_12)
    assert fotnote == ["Endret ved forskrift X."]


def test_en_paragraf_som_ikke_finnes_kaster():
    with pytest.raises(ValueError, match="fant ikke § 99"):
        u.paragraf(_dokument({"12": PARAGRAF_12}), "99")


def test_vilkaarene_bærer_kropp_og_hash(arkiv):
    _alle(arkiv)
    v = u.vilkaar()
    assert [b.nummer for b in v["paragraf12"]][3:9] == \
           ["1.", "2.", "3.", "4.", "5.", "6."]
    assert v["lik_2023"] is True
    k = v["kilder"]["produksjonsomradeforskriften"]
    assert k.navn == "lovdata-produksjonsomradeforskriften/2026-10-09.bin.gz"
    assert len(k.sha256) == 64
    assert v["endret_ved"] == ["Endret ved forskrifter 28 sep 2023 nr. 1520."]


def test_endringsinstruksen_i_lti_teller_ikke_som_ordlyd(arkiv):
    """MÅLT: «Ny § 12a skal lyde:» står inne i § 12-diven i
    FOR-2023-09-28-1520."""
    _alle(arkiv, lti_ekstra=[(0, "", "Ny § 12a skal lyde:")])
    assert u.vilkaar()["lik_2023"] is True


def test_en_endret_ordlyd_i_lti_gir_ulik_ikke_feil(arkiv):
    _alle(arkiv, lti_ekstra=[(2, "7.", "Et nytt vilkår.")])
    assert u.vilkaar()["lik_2023"] is False


def test_endret_ordlyd_feller_analysen(arkiv):
    """En forskrift som endres skal stoppe analysen, ikke stå sitert
    slik den var."""
    endret = list(PARAGRAF_12)
    endret[3] = (2, "1.", "Det var færre enn 0,2 voksne hunnlus …")
    _alle(arkiv, p12=endret)
    with pytest.raises(u.VilkaarEndret, match="ordlyden"):
        u.vilkaar()


def test_et_vilkaar_som_faller_bort_feller_analysen(arkiv):
    _alle(arkiv, p12=PARAGRAF_12[:-1])
    with pytest.raises(u.VilkaarEndret):
        u.vilkaar()


def test_nyeste_arkivfil_vinner_etter_lopenummer(arkiv):
    _legg(arkiv, "m", "2026-10-09.bin.gz", b"en")
    _legg(arkiv, "m", "2026-10-09.2.bin.gz", b"to")
    _legg(arkiv, "m", "2026-09-01.3.bin.gz", b"gammel")
    assert u.siste_kropp("m").data == b"to"


def test_tomt_arkiv_kaster_i_stedet_for_aa_svare_tomt(arkiv):
    (arkiv / "m").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="ingen arkivert kropp"):
        u.siste_kropp("m")


def test_hvert_vilkaar_har_et_merke():
    """Ingen rad sier OPPFYLT. Merkene er de tre dokumentet bruker."""
    assert {m for m, _ in u.MAALING.values()} <= {"MÅLBAR", "DELVIS",
                                                  "IKKE MÅLBAR"}
    assert {"b.1", "b.2", "b.3", "b.4", "b.5", "b.6", "a.", "ledd2.a",
            "ledd2.b"} == set(u.MAALING)


# ------------------------------------------- 2. søknadene og kapasiteten

import json  # noqa: E402


def _tillatelse(nr, kap, *lok, aktiv=True, eier="921668236"):
    return {"licenseNr": nr, "openLegalEntityNr": eier,
            "capacity": {"current": kap, "unit": "TN"},
            "connections": [{"active": aktiv, "siteNr": l} for l in lok]}


def _eierskap(arkiv, dato, *tillatelser, navn=None):
    _legg(arkiv, "eierskap", navn or f"{dato}.json.gz",
          json.dumps({"tillatelser": list(tillatelser),
                      "personer_fjernet": 0}).encode())


def test_raden_deles_etter_kildens_kobling():
    rader = [{"kobling": k, "lokalitet": k} for k in
             ("entydig", "via_soker", "usikker", "flertydig", "annen_po",
              "ikke_funnet")]
    d = u.del_rader(rader)
    assert [r["kobling"] for r in d["sikre"]] == ["entydig", "via_soker"]
    assert [r["kobling"] for r in d["usikre"]] == ["usikker"]
    assert len(d["uloste"]) == 3


def test_en_ukjent_kobling_faller_ikke_stille_i_en_av_de_tre():
    with pytest.raises(ValueError, match="ukjent kobling"):
        u.del_rader([{"kobling": "kanskje", "lokalitet": "X"}])


def test_kapasiteten_leses_per_kropp_og_merker_en_prosent(arkiv):
    _eierskap(arkiv, "2026-09-28", _tillatelse("A", 1068.0, "100"),
              _tillatelse("B", 500.0, "100"), _tillatelse("C", 900.0, "200"))
    _eierskap(arkiv, "2026-10-05", _tillatelse("A", 1079.0, "100"),
              _tillatelse("B", 530.0, "100"), _tillatelse("C", 999.0, "200"))
    kap = u.kapasitet("100", u.eierskapskropper())
    assert [(e["tillatelse"], e["endring"], e["en_prosent"])
            for e in kap["endringer"]] == [("A", 11.0, True), ("B", 30.0, False)]
    assert kap["sum_endring"] == {"TN": 41.0}
    assert (kap["fra"], kap["til"]) == ("2026-09-28", "2026-10-05")
    assert [t["nr"] for t in kap["tillatelser"]] == ["A", "B"], \
        "C er på en annen lokalitet"


def test_halv_opp_ikke_halv_til_partall():
    """1050 × 1,01 = 1060,5 → 1061. round() ville gitt 1060."""
    assert u._halv_opp(1050 * 1.01) == 1061.0


def test_en_tillatelse_som_flyttes_inn_er_en_hendelse_ikke_en_endring(arkiv):
    _eierskap(arkiv, "2026-09-28", _tillatelse("A", 100.0, "100"),
              _tillatelse("B", 200.0, "300"))
    _eierskap(arkiv, "2026-10-05", _tillatelse("A", 100.0, "100"),
              _tillatelse("B", 200.0, "300", "100"))
    kap = u.kapasitet("100", u.eierskapskropper())
    assert kap["endringer"] == []
    assert kap["inn"] == [{"fra": "2026-09-28", "til": "2026-10-05",
                           "tillatelse": "B"}]


def test_en_inaktiv_tilknytning_teller_ikke(arkiv):
    _eierskap(arkiv, "2026-10-05", _tillatelse("A", 100.0, "100", aktiv=False))
    assert u.kapasitet("100", u.eierskapskropper())["tillatelser"] == []


def test_siste_versjon_av_en_dato_brukes(arkiv):
    _eierskap(arkiv, "2026-10-05", _tillatelse("A", 1.0, "100"))
    _eierskap(arkiv, "2026-10-05", _tillatelse("A", 2.0, "100"),
              navn="2026-10-05.2.json.gz")
    [(dato, _k, t)] = u.eierskapskropper()
    assert dato == "2026-10-05" and t["A"]["capacity"]["current"] == 2.0


def test_soknadene_er_kildens_arkiverte_svar(arkiv):
    svar = {"rader": [{"kobling": "entydig", "lokalitet_nr": "100"}],
            "sha256": "ab" * 32, "bytes": 3, "headere": {}}
    _legg(arkiv, "unntaksvekst", "2026-10-09.json.gz",
          json.dumps(svar).encode())
    k, lest = u.soknader()
    assert lest == svar and k.navn == "unntaksvekst/2026-10-09.json.gz"
