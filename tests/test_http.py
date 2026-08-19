"""Det delte HTTP-laget. Ingen nett, ingen ekte venting.

`sov` injiseres i hver test — en test som beviser backoff ved å sove
tjueen sekunder er en test ingen kjører.
"""

import httpx
import pytest

from sources import _http


class FalskKlient:
    """Spiller av en liste med svar eller exceptions, ett per kall."""

    def __init__(self, *svar):
        self.svar = list(svar)
        self.kall = 0

    def get(self, url, **kwargs):
        self.kall += 1
        neste = self.svar.pop(0)
        if isinstance(neste, Exception):
            raise neste
        return neste


def _svar(status: int, url: str = "https://eksempel.no/x") -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("GET", url))


def _sovelogg():
    logg = []
    return logg, logg.append


# ---------------------------------------------------------------- retry


def test_femhundre_retryes_og_lykkes(monkeypatch):
    """Går gjennom get(), som er det kildene faktisk kaller."""
    logg = []
    monkeypatch.setattr(_http.time, "sleep", logg.append)

    klient = FalskKlient(_svar(503), _svar(502), _svar(200))
    svar = _http.get(klient, "https://eksempel.no/x")

    assert svar.status_code == 200
    assert klient.kall == 3
    assert logg == [1.0, 4.0]


def test_backoff_er_eksponentiell():
    klient = FalskKlient(_svar(500), _svar(500), _svar(200))
    logg, sov = _sovelogg()

    _http.utfor(lambda: klient.get("u"), "test", sov=sov)

    # To pauser på tre forsøk. Tredje trinn (16 s) brukes først hvis
    # FORSOK heves.
    assert logg == [1.0, 4.0]


def test_timeout_retryes():
    klient = FalskKlient(
        httpx.ConnectTimeout("tok for lang tid"),
        httpx.ReadTimeout("tok for lang tid"),
        _svar(200),
    )
    logg, sov = _sovelogg()

    assert _http.utfor(lambda: klient.get("u"), "test", sov=sov).status_code == 200
    assert klient.kall == 3


def test_tilkoblingsfeil_retryes():
    klient = FalskKlient(httpx.ConnectError("nede"), _svar(200))
    logg, sov = _sovelogg()

    assert _http.utfor(lambda: klient.get("u"), "test", sov=sov).status_code == 200


def test_429_retryes():
    """Motparten sier «senere», ikke «nei» — eneste 4xx som retryes."""
    klient = FalskKlient(_svar(429), _svar(200))
    logg, sov = _sovelogg()

    assert _http.utfor(lambda: klient.get("u"), "test", sov=sov).status_code == 200
    assert klient.kall == 2


# ---------------------------------------------------------------- permanent


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_permanent_4xx_retryes_ikke(status):
    """Retry på en 404 er tre bortkastede kall og en utsatt feilmelding."""
    klient = FalskKlient(_svar(status), _svar(200), _svar(200))
    logg, sov = _sovelogg()

    with pytest.raises(httpx.HTTPStatusError):
        _http.utfor(lambda: klient.get("u"), "test", sov=sov)

    assert klient.kall == 1, "permanent feil skal koste ett kall, ikke tre"
    assert logg == [], "ingen pause på en feil som ikke blir bedre"


def test_oppbrukt_retry_kaster_den_ekte_feilen():
    """Kalleren skal se motpartens feil, ikke en innpakning."""
    klient = FalskKlient(_svar(503), _svar(503), _svar(503))
    logg, sov = _sovelogg()

    with pytest.raises(httpx.HTTPStatusError) as e:
        _http.utfor(lambda: klient.get("u"), "test", sov=sov)

    assert e.value.response.status_code == 503
    assert klient.kall == _http.FORSOK


def test_oppbrukt_retry_paa_nettverksfeil_kaster_originalen():
    klient = FalskKlient(*[httpx.ConnectError("nede")] * _http.FORSOK)
    logg, sov = _sovelogg()

    with pytest.raises(httpx.ConnectError):
        _http.utfor(lambda: klient.get("u"), "test", sov=sov)


# ---------------------------------------------------------------- logging


def test_hvert_forsok_logges_med_utlosende_feil(capsys):
    klient = FalskKlient(_svar(503), httpx.ConnectError("nede"), _svar(200))
    logg, sov = _sovelogg()

    _http.utfor(lambda: klient.get("u"), "uke 30/2026", sov=sov)

    ut = capsys.readouterr().out
    assert "uke 30/2026" in ut
    assert "HTTP 503" in ut
    assert "ConnectError" in ut
    assert "forsøk 1/3" in ut and "forsøk 2/3" in ut


def test_oppgitt_logges(capsys):
    klient = FalskKlient(*[_svar(500)] * _http.FORSOK)
    logg, sov = _sovelogg()

    with pytest.raises(httpx.HTTPStatusError):
        _http.utfor(lambda: klient.get("u"), "sites 0-99", sov=sov)

    assert "ga opp etter 3 forsøk" in capsys.readouterr().out


# ---------------------------------------------------------------- kildene


def test_lusetall_tokenfeil_400_beholder_den_gode_meldingen(monkeypatch):
    """400 invalid_client skal fortsatt si hva som er galt, og ikke
    retryes — den blir ikke bedre av å spørre tre ganger."""
    from sources import lusetall

    monkeypatch.setenv("BARENTSWATCH_CLIENT_ID", "id")
    monkeypatch.setenv("BARENTSWATCH_CLIENT_SECRET", "feil")

    kall = {"n": 0}

    def falsk_post(url, **kwargs):
        kall["n"] += 1
        return httpx.Response(400, text="invalid_client",
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(_http.httpx, "post", falsk_post)

    with pytest.raises(RuntimeError, match="Sjekk at secreten"):
        lusetall.Lusetall()._hent_token()

    assert kall["n"] == 1
