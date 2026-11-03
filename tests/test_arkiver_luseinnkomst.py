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


# ---- karantene (MALING-DRIFT F4.2) -------------------------------------

def test_tom_uke_gaar_i_karantene_og_er_tatt_vare_paa(arkiv, capsys):
    tom = {"year": 2026, "week": 45, "localities": []}
    assert ark.main(["--dato", "2026-11-02"], kilde=Falsk({(2026, 45): tom})) == 1
    [kropp] = (arkiv / "karantene").glob("*.gz")
    assert kropp.name == "2026-11-02.json.gz"
    assert json.loads(gzip.decompress(kropp.read_bytes())) == tom
    [logg] = logger(arkiv)
    [u45] = [u for u in logg["uker"] if u["uke"] == 45]
    assert u45["status"] == "karantene"
    assert "::error::Karantene (luseinnkomst)" in capsys.readouterr().out


def test_faerre_lokaliteter_enn_forrige_kropp_gaar_i_karantene(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    halv = ukesvar(2026, 44, rapportert=2)
    halv["localities"] = halv["localities"][:3]

    assert ark.main(["--dato", "2026-11-03"], kilde=Falsk({(2026, 44): halv})) == 1
    assert [n for n in kropper(arkiv) if n.startswith("2026-10-26")] == \
        ["2026-10-26.json.gz"], "forrige kropp står som siste for uka"
    [u44] = [u for u in logger(arkiv)[1]["uker"] if u["uke"] == 44]
    assert u44["grunn"] == ["uke 44/2026: 3 lokaliteter, færre enn 5 i forrige kropp for uka"]
    assert u44["sammenlignet_med"] == "2026-10-26.json.gz"

    # Neste dag er uka hel igjen, og sammenlignes mot den gode kroppen.
    assert ark.main(["--dato", "2026-11-04"],
                    kilde=Falsk({(2026, 44): ukesvar(2026, 44, rapportert=2)})) == 0
    assert "2026-10-26.2.json.gz" in kropper(arkiv)


def test_flere_lokaliteter_er_en_vanlig_ny_kropp(arkiv):
    ark.main(["--dato", "2026-11-02"], kilde=Falsk({}))
    assert ark.main(["--dato", "2026-11-03"],
                    kilde=Falsk({(2026, 44): ukesvar(2026, 44, fallow=2)})) == 0
    assert "2026-10-26.2.json.gz" in kropper(arkiv)


def test_torrkjoring_sier_fra_om_karantene(arkiv, capsys):
    tom = {"year": 2026, "week": 45, "localities": []}
    assert ark.main(["--dato", "2026-11-02", "--torrkjor"],
                    kilde=Falsk({(2026, 45): tom})) == 1
    assert "ville karantene" in capsys.readouterr().out
    assert not arkiv.exists() or not any(arkiv.iterdir())


# ---------------------------------------------------------------- v2 (--v2)
#
# Den falske kilden svarer som POST /v2/…/locality/{year}/{week}: en liste.
# `svar` kan gi en liste, bytes (en feilside med 200) eller et unntak.

def v2svar(aar, uke, n=4):
    return [{"locality": {"no": 100 + i, "name": f"L{i}", "isOnLand": False},
             "liceReport": {"hasReported": i == 0}, "diseases": []} for i in range(n)]


class FalskV2(Falsk):
    def __init__(self, svar):
        super().__init__(svar)
        kilde = self

        class Tilgang:
            def base_url(self):
                return "https://bw.test/bwapi"

            def post(self, klient, url, hva=None, **kw):
                assert kw == {"json": {}}, kw
                aar, uke = (int(x) for x in url.rsplit("/", 2)[-2:])
                kilde.kall.append((aar, uke))
                verdi = kilde.svar.get((aar, uke))
                verdi = v2svar(aar, uke) if verdi is None else verdi
                if isinstance(verdi, Exception):
                    raise verdi

                class Svar:
                    content = verdi if isinstance(verdi, bytes) else json.dumps(verdi).encode()

                    def json(self):
                        return json.loads(self.content)
                return Svar()
        self._tilgang = Tilgang()

    def hent_uke(self, aar, uke, client=None):
        raise AssertionError("--v2 skal ikke røre v1")


@pytest.fixture
def arkiv_v2(arkiv):
    return arkiv.parent / ark.MAPPE_V2


def test_v2_henter_de_samme_ukene_til_egen_mappe(arkiv, arkiv_v2):
    kilde = FalskV2({})
    assert ark.main(["--v2", "--dato", "2026-11-02"], kilde=kilde) == 0
    assert kilde.kall == UKENE
    assert kropper(arkiv_v2) == sorted(f"{m}.json.gz" for m in MANDAGENE)
    assert not arkiv.exists() or kropper(arkiv) == []
    [logg] = logger(arkiv_v2)
    assert logg["endepunkt"] == ark.ENDEPUNKT_V2
    assert [u["status"] for u in logg["uker"]] == ["ny"] * 5


def test_v2_kroppen_er_svaret_serialisert_som_innsamlingen(arkiv_v2):
    ark.main(["--v2", "--dato", "2026-11-02"], kilde=FalskV2({}))
    b = gzip.decompress((arkiv_v2 / "2026-11-02.json.gz").read_bytes())
    assert b == raw_arkiv._serialiser(v2svar(2026, 45))[0]


def test_v2_uendret_uke_gir_bare_logg(arkiv_v2):
    ark.main(["--v2", "--dato", "2026-11-02"], kilde=FalskV2({}))
    ark.main(["--v2", "--dato", "2026-11-02"], kilde=FalskV2({}))
    assert len(kropper(arkiv_v2)) == 5
    andre = json.loads((arkiv_v2 / "2026-11-02.fangst.2.logg.json").read_text())
    assert [u["status"] for u in andre["uker"]] == ["uendret"] * 5


def test_v2_feilside_med_200_gaar_i_karantene_og_er_tatt_vare_paa(arkiv_v2):
    side = b"<html><body>Service unavailable</body></html>"
    assert ark.main(["--v2", "--dato", "2026-11-02"],
                    kilde=FalskV2({(2026, 45): side})) == 1
    assert "2026-11-02.json.gz" not in kropper(arkiv_v2)
    [kropp] = (arkiv_v2 / "karantene").glob("*.gz")
    assert gzip.decompress(kropp.read_bytes()) == side
    post = json.loads(kropp.with_name(kropp.name + ".json").read_text())
    assert post["status"] == "karantene" and "ikke JSON" in post["grunn"][0]
    assert len(kropper(arkiv_v2)) == 4


def test_v2_tom_liste_gaar_i_karantene(arkiv_v2):
    assert ark.main(["--v2", "--dato", "2026-11-02"],
                    kilde=FalskV2({(2026, 45): []})) == 1
    [post] = [json.loads(p.read_text())
              for p in (arkiv_v2 / "karantene").glob("*.gz.json")]
    assert post["grunn"] == ["uke 45/2026: svaret har ingen lokaliteter"]
    assert "2026-11-02.json.gz" not in kropper(arkiv_v2)


def test_v2_faerre_lokaliteter_enn_forrige_gaar_i_karantene(arkiv_v2):
    ark.main(["--v2", "--dato", "2026-11-02"], kilde=FalskV2({}))
    assert ark.main(["--v2", "--dato", "2026-11-02"],
                    kilde=FalskV2({(2026, 44): v2svar(2026, 44, n=3)})) == 1
    assert len(kropper(arkiv_v2)) == 5
    assert len(list((arkiv_v2 / "karantene").glob("*.gz"))) == 1


def test_v2_en_uke_som_feiler_koster_ikke_de_andre(arkiv_v2):
    assert ark.main(["--v2", "--dato", "2026-11-02"],
                    kilde=FalskV2({(2026, 43): RuntimeError("nede")})) == 1
    assert len(kropper(arkiv_v2)) == 4
    statuser = [u["status"] for u in logger(arkiv_v2)[0]["uker"]]
    assert statuser.count("feil") == 1
