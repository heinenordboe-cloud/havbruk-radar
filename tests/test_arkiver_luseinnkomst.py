"""arkiver_luseinnkomst.py: uke N..N-4, kroppen bare når den er ny for uka.

Ingen nettverk: kilden er falsk og svarer det `svar` sier per (år, uke).
"""

import gzip
import hashlib
import json

import pytest

import arkiver_luseinnkomst as ark
from core import raw as raw_arkiv
from sources import _barentswatch


def ukesvar(aar, uke, rapportert=1, fallow=1, lus=0.1):
    lok = [{"localityNo": 100 + i, "isFallow": False, "hasReportedLice": i < rapportert,
            "avgAdultFemaleLice": lus if i < rapportert else None} for i in range(4)]
    lok += [{"localityNo": 200 + i, "isFallow": True, "hasReportedLice": False}
            for i in range(fallow)]
    return {"year": aar, "week": uke, "localities": lok}


class Falsk:
    name = "lusetall"

    def __init__(self, svar):
        self.svar = svar
        self.kall = []

    def _klient(self):
        class K:
            def close(self):
                pass
        return K()

    def hent_uke(self, aar, uke, client=None):
        self.kall.append((aar, uke))
        verdi = self.svar.get((aar, uke)) or ukesvar(aar, uke)
        if isinstance(verdi, Exception):
            raise verdi
        return verdi


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(_barentswatch, "PAUSE_S", 0)
    return tmp_path / "arkiv" / ark.MAPPE


def logger(arkiv):
    return [json.loads(p.read_text()) for p in sorted(arkiv.glob("*.logg.json"))]


def kropper(arkiv):
    return sorted(p.name for p in arkiv.glob("*.gz"))


# Mandag 02.11.2026 er uke 45. N-4 er uke 41, mandag 05.10.
UKENE = [(2026, 45), (2026, 44), (2026, 43), (2026, 42), (2026, 41)]
MANDAGENE = ["2026-11-02", "2026-10-26", "2026-10-19", "2026-10-12", "2026-10-05"]


def test_henter_uke_n_til_n_minus_4_regnet_fra_kjoredatoen(arkiv):
    kilde = Falsk({})
    assert ark.main(["--dato", "2026-11-02"], kilde=kilde) == 0
    assert kilde.kall == UKENE
    assert kropper(arkiv) == sorted(f"{m}.json.gz" for m in MANDAGENE)


def test_kjoredatoen_midt_i_uka_gir_samme_uker(arkiv):
    kilde = Falsk({})
    ark.main(["--dato", "2026-11-08", "--torrkjor"], kilde=kilde)
    assert kilde.kall == UKENE


def test_kroppen_er_de_samme_bytene_som_innsamlingen_ville_skrevet(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    data, _ = raw_arkiv._serialiser(ukesvar(2026, 41))
    lagret = gzip.open(arkiv / "2026-10-05.json.gz", "rb").read()
    assert lagret == data
    post = [u for u in logger(arkiv)[0]["uker"] if u["uke"] == 41][0]
    assert post["sha256"] == hashlib.sha256(data).hexdigest()


def test_uendret_uke_gir_bare_logg(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    assert ark.main(["--dato", "2026-11-03"], kilde=Falsk({})) == 0
    assert len(kropper(arkiv)) == 5
    andre = logger(arkiv)[1]
    assert {u["status"] for u in andre["uker"]} == {"uendret"}
    assert andre["uker"][0]["sammenlignet_med"]["fil"] == "2026-11-02.json.gz"


def test_ny_kropp_for_en_uke_faar_lopenummer_og_rorer_ikke_de_andre(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    ark.main(["--dato", "2026-11-03"],
             kilde=Falsk({(2026, 44): ukesvar(2026, 44, rapportert=3)}))
    assert "2026-10-26.2.json.gz" in kropper(arkiv)
    assert len(kropper(arkiv)) == 6
    uke44 = [u for u in logger(arkiv)[1]["uker"] if u["uke"] == 44][0]
    assert uke44["status"] == "ny" and uke44["fil"] == "2026-10-26.2.json.gz"
    assert uke44["sammenlignet_med"]["fil"] == "2026-10-26.json.gz"
    assert (uke44["aktive"], uke44["rapportert"], uke44["andel"]) == (4, 3, 0.75)


def test_tilbake_til_en_tidligere_kropp_er_ny(arkiv):
    """A → B → A er en revisjon tilbake, ikke ingenting. Sammenlignes mot
    SISTE kropp for uka, ikke mot alle hashene i mappa."""
    a, b = ukesvar(2026, 44), ukesvar(2026, 44, rapportert=2)
    for dag, svar in (("2026-11-02", a), ("2026-11-03", b), ("2026-11-04", a)):
        ark.main(["--dato", dag], kilde=Falsk({(2026, 44): svar}))
    assert [n for n in kropper(arkiv) if n.startswith("2026-10-26")] == [
        "2026-10-26.2.json.gz", "2026-10-26.3.json.gz", "2026-10-26.json.gz"]


def test_published_at_er_tom_og_fetched_at_er_var(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    [logg] = logger(arkiv)
    assert logg["kode_commit"] == "0" * 40          # conftest låser den
    for u in logg["uker"]:
        assert u["published_at"] == ""
        assert u["fetched_at"].endswith("+00:00")
        assert u["observed_at"] in MANDAGENE


def test_en_uke_som_feiler_koster_ikke_de_andre(arkiv):
    kilde = Falsk({(2026, 43): RuntimeError("503")})
    assert ark.main(["--dato", "2026-11-02"], kilde=kilde) == 1
    assert len(kropper(arkiv)) == 4
    [logg] = logger(arkiv)
    feil = [u for u in logg["uker"] if u["status"] == "feil"]
    assert [(u["uke"], u["feil"]) for u in feil] == [(43, "RuntimeError: 503")]


def test_tom_uke_lagres_ikke(arkiv):
    kilde = Falsk({(2026, 45): {"year": 2026, "week": 45, "localities": []}})
    assert ark.main(["--dato", "2026-11-02"], kilde=kilde) == 1
    assert "2026-11-02.json.gz" not in kropper(arkiv)


def test_torrkjoring_skriver_ingenting(arkiv):
    assert ark.main(["--dato", "2026-11-02", "--torrkjor"], kilde=Falsk({})) == 0
    assert not arkiv.exists() or not any(arkiv.iterdir())


def test_to_kjoringer_samme_dag_gir_to_logger(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    assert sorted(p.name for p in arkiv.glob("*.logg.json")) == [
        "2026-11-02.fangst.2.logg.json", "2026-11-02.fangst.logg.json"]


def test_malingens_logg_teller_ikke_som_kropp(arkiv):
    arkiv.mkdir(parents=True)
    (arkiv / "2026-11-02.maling.logg.json").write_text("[]")
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    assert ark.siste_kropp("2026-11-02").name == "2026-11-02.json.gz"
