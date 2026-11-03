"""arkiver_soknader.py: søknadslagene hver dag, filtrert før noe skrives.

Ingen nettverk: `hent_fn` gir svaret og `former_fn` Brreg-oppslaget, som
`hent_fn` i test_arkiver_flater.py.
"""

import gzip
import json

import httpx
import pytest

import arkiver_soknader as ark
from core import raw as raw_arkiv

AS, ENK, DA_SEKTOR, UKJENT, SLETTET = "911111111", "922222222", "933333333", "944444444", "955555555"
FORMER = {
    AS: {"status": "ok", "form": "AS", "sektor": "2100"},
    ENK: {"status": "ok", "form": "ENK", "sektor": "8200"},
    # En form vi ikke kjenner, men som Brreg plasserer i personsektoren.
    DA_SEKTOR: {"status": "ok", "form": "XYZ", "sektor": "2300"},
    UKJENT: {"status": "http 404", "form": "", "sektor": ""},
    SLETTET: {"status": "slettet", "form": "AS", "sektor": "2100"},
}


def post(i, nr, navn="SØKER"):
    return {"attributes": {"objectid": i, "applicationno": f"S{i}", NR: nr,
                           "applicantorganisationname": f"{navn} {i}",
                           "status_application": "SUBMITTED"}}


NR = ark.NR_FELT


def svar(n_as=4):
    lag = {}
    for l in ark.LAG:
        poster = [post(i, AS) for i in range(n_as)]
        poster += [post(100, ENK, "PERSON"), post(101, DA_SEKTOR, "PERSON"),
                   post(102, UKJENT, "PERSON"), post(103, "", "PERSON"),
                   post(104, SLETTET, "BORTE")]
        lag[str(l)] = {"displayFieldName": "applicationno", "features": poster}
    return lag


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv" / ark.MAPPE


@pytest.fixture(autouse=True)
def sporbar(monkeypatch):
    monkeypatch.setattr(ark.kodeproveniens, "krev_sporbar", lambda: ("a" * 40, "rent"))


def kjor(rå, dato="2026-11-03", former=None):
    return ark.main(["--dato", dato], hent_fn=lambda: rå,
                    former_fn=former or (lambda nr: {n: FORMER[n] for n in nr if n in FORMER}))


def kropper(arkiv):
    return sorted(p.name for p in arkiv.glob("*.gz"))


def logger(arkiv):
    return {p.name: json.loads(p.read_text()) for p in arkiv.glob("*.logg.json")}


def alt_skrevet(arkiv) -> bytes:
    return b"".join(gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
                    for p in sorted(arkiv.rglob("*")) if p.is_file())


def test_forste_kropp_er_filtrert_og_ingen_person_er_skrevet(arkiv):
    assert kjor(svar()) == 0
    assert kropper(arkiv) == ["2026-11-03.json.gz"]
    kropp = json.loads(gzip.decompress((arkiv / "2026-11-03.json.gz").read_bytes()))
    for lag in kropp.values():
        assert {f["attributes"][NR] for f in lag["features"]} == {AS, SLETTET}
    alt = alt_skrevet(arkiv)
    for nr in (ENK, DA_SEKTOR, UKJENT):
        assert nr.encode() not in alt
    assert b"PERSON" not in alt
    p = logger(arkiv)["2026-11-03.fangst.logg.json"]["soknader"]
    assert p["status"] == "ny" and p["poster"]["0"] == 5 and p["published_at"] == ""
    assert p["filtrert"]["0"] == {"slipper": 5, "personform": 2, "vet ikke": 1,
                                  "ikke ni siffer": 1}


def test_uendret_gir_bare_logg(arkiv):
    kjor(svar())
    assert kjor(svar(), "2026-11-04") == 0
    assert kropper(arkiv) == ["2026-11-03.json.gz"]
    p = logger(arkiv)["2026-11-04.fangst.logg.json"]["soknader"]
    assert p["status"] == "uendret"
    assert p["sammenlignet_med"]["fil"] == "2026-11-03.json.gz"


def test_andre_kjoring_samme_dag_faar_egen_logg(arkiv):
    kjor(svar())
    kjor(svar(5))
    assert set(logger(arkiv)) == {"2026-11-03.fangst.logg.json", "2026-11-03.fangst.2.logg.json"}
    assert kropper(arkiv) == ["2026-11-03.2.json.gz", "2026-11-03.json.gz"]


def test_brreg_svarer_ikke_gir_ingenting(arkiv):
    def nede(nr):
        raise ark.FilteretKjorteIkke("ConnectError: nede")
    assert kjor(svar(), former=nede) == 1
    assert kropper(arkiv) == []
    assert not list(arkiv.rglob("karantene*"))
    p = logger(arkiv)["2026-11-03.fangst.logg.json"]["soknader"]
    assert p["status"] == "feil" and "persondatafilteret" in p["feil"]


def test_tomt_lag_gaar_i_karantene_filtrert(arkiv):
    rå = svar()
    rå["4"]["features"] = []
    assert kjor(rå) == 1
    assert kropper(arkiv) == []
    assert ENK.encode() not in alt_skrevet(arkiv)
    p = logger(arkiv)["2026-11-03.fangst.logg.json"]["soknader"]
    assert p["status"] == "karantene" and p["grunn"] == ["lag 4: ingen poster"]


def test_halvert_lag_gaar_i_karantene(arkiv):
    kjor(svar(20))
    assert kjor(svar(3), "2026-11-04") == 1
    p = logger(arkiv)["2026-11-04.fangst.logg.json"]["soknader"]
    assert p["status"] == "karantene"
    assert any("under 50% av 21" in g for g in p["grunn"])


def test_feilside_gaar_i_karantene(arkiv):
    rå = svar()
    rå["2"] = b"<html>Tjenesten er midlertidig utilgjengelig</html>"
    assert kjor(rå) == 1
    p = logger(arkiv)["2026-11-03.fangst.logg.json"]["soknader"]
    assert p["status"] == "karantene" and p["grunn"][0].startswith("lag 2: svaret er ikke JSON")


def test_torrkjoring_skriver_ingenting(arkiv):
    assert ark.main(["--dato", "2026-11-03", "--torrkjor"], hent_fn=svar,
                    former_fn=lambda nr: FORMER) == 0
    assert not arkiv.exists()


def test_grunnene():
    assert ark.grunn({NR: AS}, FORMER) == "slipper"
    assert ark.grunn({NR: SLETTET}, FORMER) == "slipper"
    assert ark.grunn({NR: ENK}, FORMER) == "personform"
    assert ark.grunn({NR: DA_SEKTOR}, FORMER) == "personform"
    assert ark.grunn({NR: UKJENT}, FORMER) == "vet ikke"
    assert ark.grunn({NR: "966666666"}, FORMER) == "vet ikke"
    assert ark.grunn({NR: "12345678"}, FORMER) == "ikke ni siffer"
    assert ark.grunn({}, FORMER) == "ikke ni siffer"


def test_hent_lag_blar_forbi_maxrecordcount():
    sider = []

    def svar_(req):
        side = int(req.url.params["resultOffset"])
        sider.append(side)
        feats = [{"attributes": {"objectid": i}} for i in range(side, min(side + 2, 5))]
        return httpx.Response(200, json={"features": feats,
                                         "exceededTransferLimit": side + 2 < 5})
    with httpx.Client(transport=httpx.MockTransport(svar_)) as k:
        d = ark.hent_lag(k, 0)
    assert sider == [0, 2, 4]
    assert [f["attributes"]["objectid"] for f in d["features"]] == [0, 1, 2, 3, 4]
    assert "exceededTransferLimit" not in d


def test_brreg_former_slaar_opp_slettede_enkeltvis():
    def svar_(req):
        if req.url.path.endswith("/enheter"):
            return httpx.Response(200, json={"_embedded": {"enheter": [
                {"organisasjonsnummer": AS, "organisasjonsform": {"kode": "AS"},
                 "institusjonellSektorkode": {"kode": "2100"}}]}})
        if req.url.path.endswith(SLETTET):
            return httpx.Response(200, json={"organisasjonsform": {"kode": "AS"},
                                             "slettedato": "2025-01-01"})
        return httpx.Response(404)
    with httpx.Client(transport=httpx.MockTransport(svar_)) as k:
        f = ark.brreg_former(k, {AS, SLETTET, UKJENT, ""})
    assert f[AS]["form"] == "AS" and f[SLETTET]["status"] == "slettet"
    assert f[UKJENT] == {"status": "http 404", "form": "", "sektor": ""}
    assert "" not in f


def test_brreg_nede_kaster_filteret_kjorte_ikke(monkeypatch):
    monkeypatch.setattr(ark._http, "utfor", lambda f, hva: f())

    def svar_(req):
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(svar_)) as k:
        with pytest.raises(ark.FilteretKjorteIkke):
            ark.brreg_former(k, {AS})
