"""Tilgang: tokenets levetid og 401-veien. Ingen nett.

To feil bor her, og begge handler om hvem som EIER svaret på «duger
tokenet fortsatt»:

  F13  vi regnet det ut selv, med en klokke som står stille når maskinen
       sover. Serverens klokke gjør ikke det.
  ---  og selv med riktig klokke er utregningen bare et anslag. Serveren
       vet. Den sier 401.
"""

import httpx
import pytest

from sources import _barentswatch, _http


class FalsktTokensvar:
    """Står i for httpx.Response fra token-endepunktet."""

    def __init__(self, token: str, expires_in: int = 3600):
        self._data = {"access_token": token, "expires_in": expires_in}

    def json(self):
        return self._data


@pytest.fixture
def tilgang(monkeypatch):
    """En Tilgang med nøkler, en tellende token-utsteder og styrt klokke."""
    monkeypatch.setattr(_barentswatch, "get", lambda n, s=None: {
        "kilder.test.client_id": "id",
        "kilder.test.client_secret": "hemmelig",
    }.get(n, s if s is not None else "https://test.invalid"))

    utstedt = []

    def falsk_post(url, hva=None, **kw):
        utstedt.append(url)
        return FalsktTokensvar(f"token-{len(utstedt)}")

    monkeypatch.setattr(_http, "post", falsk_post)

    klokke = {"vegg": 1_000_000.0, "mono": 5_000.0}
    monkeypatch.setattr(_barentswatch.time, "time", lambda: klokke["vegg"])
    monkeypatch.setattr(_barentswatch.time, "monotonic", lambda: klokke["mono"])

    t = _barentswatch.Tilgang("test")
    t._test_utstedt = utstedt
    t._test_klokke = klokke
    return t


# ----------------------------------------------------- F13: klokkevalget

def test_token_fornyes_naar_veggklokka_gaar_selv_om_monotonic_star_stille(tilgang):
    """F13, nøyaktig som den skjedde 25.08.2026.

    Maskinen sov 38 minutter på batteri. mach_absolute_time() — som er
    time.monotonic() på macOS — står stille under søvn; serverens klokke
    gjør ikke det. Tokenet ble 74 minutter gammelt hos BarentsWatch mens
    vår klokke sa 36, og TTL er 60.
    """
    assert tilgang.token() == "token-1"
    assert len(tilgang._test_utstedt) == 1

    # Maskinen sover. Veggklokka går en drøy time, monotonic står bom stille.
    tilgang._test_klokke["vegg"] += 3600
    mono_for = tilgang._test_klokke["mono"]

    assert tilgang.token() == "token-2", \
        "tokenet er utløpt hos serveren og skal fornyes"
    assert len(tilgang._test_utstedt) == 2
    assert tilgang._test_klokke["mono"] == mono_for, \
        "monotonic sto stille — det er hele poenget med testen"


def test_token_gjenbrukes_saa_lenge_det_faktisk_lever(tilgang):
    """Hundrevis av kall i en backfill skal ikke gi hundrevis av tokenkall."""
    assert tilgang.token() == "token-1"
    tilgang._test_klokke["vegg"] += 600          # ti minutter, TTL er 3600
    assert tilgang.token() == "token-1"
    assert len(tilgang._test_utstedt) == 1


def test_monotonic_brukes_ikke_til_tokenalder(tilgang):
    """Vakten mot at noen «rydder» tilbake til monotonic.

    Står monotonic stille mens veggklokka går, skal tokenet fornyes.
    Ville koden lest monotonic, ville den ansett tokenet som ferskt.
    """
    tilgang.token()
    tilgang._test_klokke["mono"] += 100_000      # monotonic spretter langt fram
    assert tilgang.token() == "token-1", \
        "monotonic skal ikke kunne utløse en fornyelse på egen hånd"


# ------------------------------------------- 401: serveren er autoriteten

class FalskKlient:
    """Svarer med kodene i `koder`, én per kall. `headers` er ekte nok til
    at re-autentiseringen kan skrive i den."""

    def __init__(self, *koder):
        self.koder = list(koder)
        self.headers: dict[str, str] = {}
        self.sett_token: list[str | None] = []

    def get(self, url, **kw):
        self.sett_token.append(self.headers.get("Authorization"))
        kode = self.koder.pop(0) if self.koder else 200
        return httpx.Response(kode, request=httpx.Request("GET", url),
                              json={"uke": 30})

    def close(self):
        pass


def test_401_loses_av_re_autentisering(tilgang, capsys):
    """Første kall 401, andre 200 — og det andre bærer et NYTT token."""
    c = FalskKlient(401, 200)
    c.headers["Authorization"] = f"Bearer {tilgang.token()}"

    svar = tilgang.get(c, "https://test.invalid/uke", hva="uke 30/2022")

    assert svar.status_code == 200
    assert c.sett_token == ["Bearer token-1", "Bearer token-2"], \
        "andre forsøk skal bruke et ferskt token, ikke det samme"
    assert len(tilgang._test_utstedt) == 2
    assert "[auth]" in capsys.readouterr().out


def test_401_som_overlever_re_autentisering_kastes(tilgang):
    """Ekte 401 — feil nøkkel, trukket tilgang — skal opp og felle kilden."""
    c = FalskKlient(401, 401, 401, 401)
    c.headers["Authorization"] = f"Bearer {tilgang.token()}"

    with pytest.raises(httpx.HTTPStatusError) as ei:
        tilgang.get(c, "https://test.invalid/uke", hva="uke 30/2022")

    assert ei.value.response.status_code == 401
    assert len(c.sett_token) == 2, "ett ordinært kall og ÉN ny sjanse, ikke flere"
    assert len(tilgang._test_utstedt) == 2, "re-autentisering skjer én gang"


def test_401_utloser_ikke_transient_retry(tilgang):
    """401 skal fortsatt ikke retryes som transient feil av _http.

    Ville _http behandlet den som transient, ville hvert av de to kallene
    blitt fire. Skillet er hele grunnen til at re-autentiseringen ligger
    utenfor retry-laget: å spørre om igjen med NOE NYTT er en annen
    handling enn å gjenta seg selv.
    """
    c = FalskKlient(401, 401)
    c.headers["Authorization"] = f"Bearer {tilgang.token()}"

    with pytest.raises(httpx.HTTPStatusError):
        tilgang.get(c, "https://test.invalid/uke", hva="uke 30/2022")

    assert len(c.sett_token) == 2


def test_andre_feilkoder_gaar_urort_gjennom(tilgang):
    """404 er ikke et tokenproblem og skal ikke gi en ny innlogging."""
    c = FalskKlient(404)
    c.headers["Authorization"] = f"Bearer {tilgang.token()}"

    with pytest.raises(httpx.HTTPStatusError) as ei:
        tilgang.get(c, "https://test.invalid/uke", hva="uke 30/2022")

    assert ei.value.response.status_code == 404
    assert len(tilgang._test_utstedt) == 1, "ingen re-autentisering på 404"


def test_forny_kaster_det_gamle_tokenet(tilgang):
    assert tilgang.token() == "token-1"
    assert tilgang.forny() == "token-2"
    assert tilgang.token() == "token-2"
    assert len(tilgang._test_utstedt) == 2
