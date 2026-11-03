"""core/karantene.py og karantene.py: én prøve per regel, og lagringen.

Ingen nettverk, og ingenting skrives i datarepoet: ARKIV_DIR peker til
tmp_path.
"""

import gzip
import hashlib
import json

import pytest

import karantene as cli
from core import karantene
from core import raw as raw_arkiv

FEILSIDE = (b"<!DOCTYPE html><html><head><title>Feil</title></head><body>"
            b"<h1>Tjenesten er midlertidig utilgjengelig</h1></body></html>")


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


# ---------------------------------------------------------------- reglene

@pytest.mark.parametrize("kropp", [b"", b"  \n\t"])
def test_ikke_tom_avviser_null_byte_og_bare_blanktegn(kropp):
    assert "tom kropp" in karantene.ikke_tom(kropp)


def test_ikke_tom_slipper_alt_med_innhold():
    assert karantene.ikke_tom(b"[]") is None


def test_html_krever_html_uansett_store_og_smaa_bokstaver():
    assert karantene.html(b"<!DOCTYPE html><HTML lang=no>") is None
    assert karantene.html(b"[]") == "ingen <html i kroppen"
    assert karantene.html(b"<!DOCTYPE html><body>uten rot</body>") is not None


def test_nevner_leser_den_synlige_teksten_uten_store_og_smaa_bokstaver():
    regel = karantene.nevner("havbruksfond")
    assert regel(b"<p>Utbetaling fra HAVBRUKSFONDET</p>") is None
    assert regel(FEILSIDE) == "synlig tekst nevner ikke «havbruksfond»"
    # I et skript eller en adresse er ordet ikke noe en leser ser.
    assert regel(b'<a href="/havbruksfondet">x</a><script>havbruksfond</script>') \
        is not None


def test_minst_tekst_teller_synlige_tegn():
    regel = karantene.minst_tekst(10)
    assert regel(b"<p>0123456789</p>") is None
    assert regel(b"<p>012345678</p><script>xxxxxxxxxx</script>") == \
        "synlig tekst 9 tegn, under minstelengden 10"


def test_andel_av_forrige_avviser_under_halvparten():
    regel = karantene.andel_av_forrige(b"<p>" + b"a" * 100 + b"</p>")
    assert regel(b"a" * 50) is None, "nøyaktig halvparten er godt nok"
    assert "under 50% av forrige versjon (100 tegn)" in regel(b"a" * 49)


def test_vurder_samler_hver_grunn_i_reglenes_rekkefolge():
    grunner = karantene.vurder(b"", [karantene.ikke_tom, karantene.html,
                                     karantene.nevner("x")])
    assert grunner == ["tom kropp (0 B)", "ingen <html i kroppen",
                       "synlig tekst nevner ikke «x»"]
    assert karantene.vurder(b"<html>x</html>", [karantene.html]) == []


# ---------------------------------------------------------------- lagringen

def test_sett_inn_lagrer_kroppen_utenfor_serien(arkiv, capsys):
    post = karantene.sett_inn("auksjon", "2026-11-03", FEILSIDE,
                              ["ingen <html i kroppen"], jobb="auksjon",
                              http_status=200, url="https://x")
    kropp = arkiv / "auksjon" / "karantene" / "2026-11-03.bin.gz"
    assert gzip.decompress(kropp.read_bytes()) == FEILSIDE
    assert post["sha256"] == hashlib.sha256(FEILSIDE).hexdigest()
    assert post["status"] == "karantene" and post["http_status"] == 200
    assert json.loads((kropp.parent / (kropp.name + ".json")).read_text()) == post
    # Serien ser den ikke: verken som kropp eller som allerede arkivert hash.
    assert raw_arkiv.kropper("auksjon") == []
    assert post["sha256"] not in raw_arkiv.hashene("auksjon")
    assert "::error::Karantene (auksjon): 2026-11-03" in capsys.readouterr().out


def test_sett_inn_skriver_aldri_om_men_gir_lopenummer(arkiv):
    karantene.sett_inn("vilkar-x", "2026-11-03", b"a", "grunn")
    karantene.sett_inn("vilkar-x", "2026-11-03", b"b", "grunn")
    navn = sorted(p.name for p in (arkiv / "vilkar-x" / "karantene").iterdir())
    assert navn == ["2026-11-03.2.bin.gz", "2026-11-03.2.bin.gz.json",
                    "2026-11-03.bin.gz", "2026-11-03.bin.gz.json"]


def test_kropp_med_merke_faar_en_mappe_daglig_yml_committer(arkiv):
    """daglig.yml legger til `data/arkiv/<kilde>/*.daglig.*` i toppen av
    mappa, og ingenting annet. Mappa må matche det mønsteret."""
    karantene.sett_inn("eierskap", "2026-11-03", [], "null tillatelser",
                       merke=raw_arkiv.DAGLIG)
    [mappe] = [p for p in (arkiv / "eierskap").iterdir()]
    assert mappe.name == "karantene.daglig.d"
    assert mappe.match("*.daglig.*")
    assert (mappe / "2026-11-03.daglig.json.gz").exists()


# ---------------------------------------------------------------- kvitteringen

def test_ukvittert_er_rodt_og_avvist_tar_den_ut(arkiv, capsys):
    karantene.sett_inn("auksjon", "2026-11-03", FEILSIDE, "ingen <html")
    assert cli.main([]) == 1
    assert "UKVITTERT" in capsys.readouterr().out

    kropp = arkiv / "auksjon" / "karantene" / "2026-11-03.bin.gz"
    assert cli.main(["--kvitter", str(kropp), "--avvist",
                     "--grunn", "feilside fra prøven"]) == 0
    [(_, _, kv)] = karantene.poster()
    assert kv["utfall"] == "avvist" and kv["grunn"] == "feilside fra prøven"
    assert cli.main([]) == 0
    assert raw_arkiv.kropper("auksjon") == [], "avvist kommer aldri inn"


def test_godtatt_skriver_kroppen_inn_i_serien_med_samme_filtype(arkiv):
    rå = {"localities": [{"localityNo": 1}]}
    karantene.sett_inn("lusetall-innkomst", "2026-10-26", rå, "færre lokaliteter")
    [(kropp, post, _)] = karantene.poster()
    kv = karantene.kvitter(kropp, "godtatt", "BarentsWatch slo sammen to")
    assert kv["skrevet_til"] == "lusetall-innkomst/2026-10-26.json.gz"
    [i_serien] = raw_arkiv.kropper("lusetall-innkomst")
    assert hashlib.sha256(gzip.open(i_serien).read()).hexdigest() == post["sha256"]


def test_godtatt_med_merke_faar_merket_i_serien(arkiv):
    karantene.sett_inn("eierskap", "2026-11-03", [{"a": 1}], "grunn",
                       merke=raw_arkiv.DAGLIG)
    [(kropp, _, _)] = karantene.poster()
    kv = karantene.kvitter(kropp, "godtatt", "riktig likevel")
    assert kv["skrevet_til"] == "eierskap/2026-11-03.daglig.json.gz"


def test_kvittering_krever_utfall_grunn_og_riktig_kropp(arkiv):
    karantene.sett_inn("auksjon", "2026-11-03", FEILSIDE, "grunn")
    [(kropp, _, _)] = karantene.poster()
    with pytest.raises(ValueError):
        karantene.kvitter(kropp, "kanskje", "x")
    with pytest.raises(ValueError):
        karantene.kvitter(kropp, "avvist", "  ")
    kropp.chmod(0o644)
    kropp.write_bytes(gzip.compress(b"noe annet"))
    with pytest.raises(ValueError, match="stemmer ikke"):
        karantene.kvitter(kropp, "avvist", "x")


def test_en_kvittering_skrives_en_gang(arkiv):
    karantene.sett_inn("auksjon", "2026-11-03", FEILSIDE, "grunn")
    [(kropp, _, _)] = karantene.poster()
    karantene.kvitter(kropp, "avvist", "x")
    with pytest.raises(FileExistsError):
        karantene.kvitter(kropp, "godtatt", "ombestemt")
