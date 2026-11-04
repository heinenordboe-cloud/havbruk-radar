"""arkiver_auksjon.py: de tre stille tilfellene sier fra.

Tom indeks, feil i Wayback-oppslaget, og feil sammen med nye kropper sto
bare som en `print` fram til 06.10.2026. Jobben var grønn, og loggfila
sa ingenting. Nå gir de `::warning::` og en post i loggfila.

Ingen nettverk: `_hent` og `_http.get` byttes ut.
"""

import json
import sys

import pytest

import arkiver_auksjon as ark
from core import raw as raw_arkiv

INDEKS_MED_BARN = (b'<html><a href="/akvakultur/auksjon-av-produksjonskapasitet/'
                   b'auksjon-2022">2022</a></html>')


@pytest.fixture
def kjor(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")

    def kjor(hent, cdx):
        monkeypatch.setattr(ark, "_hent", lambda klient, url: hent(url))
        monkeypatch.setattr(ark._http, "get",
                            lambda klient, url, hva=None: cdx(url))
        monkeypatch.setattr(sys, "argv", ["arkiver_auksjon.py",
                                          "--dato", "2026-10-06"])
        kode = ark.main()
        logg = json.loads((tmp_path / "arkiv" / ark.KILDE
                           / "2026-10-06.logg.json").read_text())
        return kode, logg
    return kjor


class Svar:
    def __init__(self, tekst):
        self.text = tekst


def _advarsler(logg):
    return [r["advarsel"] for r in logg if "advarsel" in r]


def test_wayback_som_feiler_er_en_advarsel_og_ikke_null_avtrykk(kjor, capsys):
    def cdx(url):
        raise RuntimeError("504 Gateway Time-out")

    kode, logg = kjor(lambda url: (INDEKS_MED_BARN, ""), cdx)

    assert kode == 0, "indeksen kom inn som ny; dagen er ikke tom"
    assert _advarsler(logg) == ["wayback_feilet"]
    ut = capsys.readouterr().out
    assert "::warning::Auksjonsarkivering: Wayback-oppslaget (CDX) feilet: " \
           "504 Gateway Time-out" in ut


def test_tom_indeks_er_en_advarsel(kjor, capsys):
    kode, logg = kjor(lambda url: (b"<html>ingen lenker</html>", ""),
                      lambda url: Svar(""))

    assert _advarsler(logg) == ["tom_indeks"]
    assert "lenket ingen auksjonsrunder" in capsys.readouterr().out
    assert kode == 0


def test_indeks_som_ikke_kan_leses_er_feil_og_advarsel(kjor):
    def hent(url):
        raise RuntimeError("tilkobling nektet")

    kode, logg = kjor(hent, lambda url: Svar(""))

    assert [r for r in logg if "feil" in r], "selve indeksen er en feil"
    assert _advarsler(logg) == ["tom_indeks"]
    assert kode == 1, "feil og ingenting nytt: rød, som før"


def test_feil_sammen_med_nye_kropper_er_en_advarsel(kjor, capsys):
    def hent(url):
        if url.endswith("auksjon-2022"):
            raise RuntimeError("500")
        return INDEKS_MED_BARN, ""

    kode, logg = kjor(hent, lambda url: Svar(""))

    assert kode == 0, "noe nytt kom inn; grønn, som før"
    assert _advarsler(logg) == ["feil_med_nye"]
    assert "1 adresse(r) feilet samme dag som 1 ny(e)" in capsys.readouterr().out


def test_en_vanlig_dag_har_ingen_advarsler(kjor, capsys):
    kode, logg = kjor(lambda url: (INDEKS_MED_BARN, ""), lambda url: Svar(""))

    assert kode == 0
    assert _advarsler(logg) == []
    assert "::warning::" not in capsys.readouterr().out


# ---- kodeproveniens ---------------------------------------------------


def test_hver_arkivert_kropp_har_kodeproveniens_i_loggen(kjor):
    kode, logg = kjor(lambda url: (INDEKS_MED_BARN, ""), lambda url: Svar(""))

    kropper = [r for r in logg if "sha256" in r]
    assert kropper
    for r in kropper:
        assert r["kode_commit"] == "0" * 40      # conftest låser den
        assert r["kode_rent"] == "ja"
        assert r["fetched_at"].endswith("+00:00")
    # Advarsels- og feilposter er ikke kropper og får ikke stempel.
    assert all("kode_commit" not in r for r in logg if "sha256" not in r)


def test_andre_kjoring_samme_dag_faar_egen_logg(kjor, tmp_path):
    # Til 04.11.2026 ble loggen hoppet over når dagens fantes, og sju
    # kropper fra 29.09.2026 sto uten fetched_at og kode_commit.
    _, forste = kjor(lambda url: (INDEKS_MED_BARN, ""), lambda url: Svar(""))
    _, igjen = kjor(lambda url: (INDEKS_MED_BARN + b"<p>ny</p>", ""),
                    lambda url: Svar(""))
    assert igjen == forste, "den første står urørt"
    andre = json.loads((tmp_path / "arkiv" / ark.KILDE
                        / "2026-10-06.2.logg.json").read_text())
    nye = [r for r in andre if r.get("ny")]
    assert nye, "kroppen fra andre kjøring er logget"
    assert all(r["kode_commit"] == "0" * 40 and r["fetched_at"] for r in nye)


def test_kode_som_ikke_kan_spores_henter_ingenting(tmp_path, monkeypatch, capsys):
    """Samme sperre som run.py, spurt FØR noe hentes."""
    from core import kodeproveniens

    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("arbeidstreet er ikke rent")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)

    def hent(url):
        raise AssertionError("skulle ikke hentet noe")
    monkeypatch.setattr(ark, "_hent", lambda klient, url: hent(url))
    monkeypatch.setattr(sys, "argv", ["arkiver_auksjon.py", "--dato", "2026-10-06"])

    assert ark.main() == 1
    assert "::error::Auksjonsarkiveringen startet ikke: arbeidstreet er ikke rent" \
        in capsys.readouterr().out
    assert not (tmp_path / "arkiv").exists()



# ---- karantene (MALING-DRIFT F1.3) -------------------------------------
#
# Til 03.11.2026 ble kroppen arkivert før den ble lest, og en tom kropp ga
# exit 0. Nå går tom kropp og kropp uten <html i karantene FØR arkivering.

@pytest.mark.parametrize("kropp,grunn", [
    (b"", ["tom kropp (0 B)", "ingen <html i kroppen"]),
    (b"[]", ["ingen <html i kroppen"]),
])
def test_tom_kropp_og_kropp_uten_html_gaar_i_karantene(kjor, tmp_path, capsys,
                                                       kropp, grunn):
    kode, logg = kjor(lambda url: (kropp, ""), lambda url: Svar(""))

    assert kode == 1
    assert raw_arkiv.kropper(ark.KILDE) == [], "ingenting i serien"
    [post] = [r for r in logg if r.get("status") == "karantene"]
    assert post["grunn"] == grunn and post["url"] == ark.INDEKS
    assert post["kode_commit"] == "0" * 40
    assert (tmp_path / "arkiv" / ark.KILDE / "karantene"
            / "2026-10-06.bin.gz").exists(), "men tatt vare på"
    assert _advarsler(logg) == ["tom_indeks"], "ingen lenker lest av den"
    assert "::error::Karantene (auksjon)" in capsys.readouterr().out


def test_lenkene_leses_av_kroppen_som_ble_arkivert(kjor):
    """Indeksen hentes én gang, ikke én gang til for lenkene."""
    hentet = []

    def hent(url):
        hentet.append(url)
        return INDEKS_MED_BARN, ""
    kjor(hent, lambda url: Svar(""))
    assert hentet.count(ark.INDEKS) == 1
