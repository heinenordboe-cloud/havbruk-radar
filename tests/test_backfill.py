"""Backfill-loopen. Ingen nett — hent_uke er byttet ut.

Poenget med disse testene er ikke å teste henting, men å teste hva som
skjer når en uke feiler midt i 730.
"""

import datetime as dt

import httpx
import pytest

import backfill
from core import raw as raw_arkiv, snapshot
from core.contract import Observation, Source
from sources import _http


class FalskLusetall(Source):
    """Svarer på hent_uke(). `feiler` er uker som skal kaste."""

    name = "lusetall"
    entity_type = "lokalitet"

    def __init__(self, feiler=(), tomme=()):
        self.feiler = set(feiler)
        self.tomme = set(tomme)
        self.hentet = []

    def hent_uke(self, aar, uke, client=None):
        self.hentet.append((aar, uke))
        if (aar, uke) in self.feiler:
            raise RuntimeError(f"503 fra tjenesten (uke {uke})")
        return {"year": aar, "week": uke,
                "localities": [] if (aar, uke) in self.tomme else [
                    {"localityNo": 10029, "name": "X", "avgAdultFemaleLice": 0.2,
                     "hasReportedLice": True, "isFallow": False},
                ]}

    def parse(self, raw, observed_at):
        for lok in raw.get("localities", []):
            yield Observation(
                entity_id=str(lok["localityNo"]), entity_type=self.entity_type,
                entity_name="", field="voksne_hunnlus",
                value=str(lok["avgAdultFemaleLice"]), source=self.name,
                observed_at=observed_at,
            )


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(backfill.snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(backfill.changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(backfill.time, "sleep", lambda s: None)
    return tmp_path


def _kjor(monkeypatch, kilde, fra, til, ekstra=()):
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr(backfill, "_ferskeste_tillatte", lambda k: (2026, 30))
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "lusetall",
                                     "--fra", fra, "--til", til,
                                     "--pause", "0", *ekstra])
    return backfill.main()


def test_uke_som_feiler_stopper_ikke_resten(isolert, monkeypatch, capsys):
    """continue, ikke break. Å avbryte på uke 300 av 730 fordi én uke
    feilet er å kaste alt som allerede lyktes."""
    kilde = FalskLusetall(feiler={(2026, 2)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-04")

    # Alle fire uker ble forsøkt, ikke bare de to første.
    assert kilde.hentet == [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    assert kode == 1

    ut = capsys.readouterr().out
    assert "3 uker skrevet" in ut


def test_feillista_skrives_ut_og_gir_exit_1(isolert, monkeypatch, capsys):
    kilde = FalskLusetall(feiler={(2026, 2), (2026, 4)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-05")
    ut = capsys.readouterr().out

    assert kode == 1
    assert "2 uke(r) FEILET" in ut
    assert "uke  2/2026" in ut and "uke  4/2026" in ut
    assert "503 fra tjenesten" in ut
    # Hullene skal kunne lukkes uten å regne dem ut for hånd.
    assert "Kjør samme intervall på nytt" in ut


def test_uten_feil_er_exit_0(isolert, monkeypatch, capsys):
    kilde = FalskLusetall()

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-03")

    assert kode == 0
    assert "FEILET" not in capsys.readouterr().out


def test_gjenopptakelse_henter_bare_de_som_mangler(isolert, monkeypatch, capsys):
    """Feillista er bare nyttig hvis en ny kjøring faktisk lukker hullene."""
    forste = FalskLusetall(feiler={(2026, 2)})
    assert _kjor(monkeypatch, forste, "2026-01", "2026-04") == 1
    capsys.readouterr()

    andre = FalskLusetall()
    assert _kjor(monkeypatch, andre, "2026-01", "2026-04") == 0

    # Bare uka som manglet ble hentet på nytt.
    assert andre.hentet == [(2026, 2)]
    assert "1 uker skrevet, 3 hoppet over" in capsys.readouterr().out


def test_tom_uke_stopper_fortsatt(isolert, monkeypatch, capsys):
    """En tom uke betyr at året ikke finnes. Da er alt eldre også tomt,
    og å fortsette er å brenne kall på ingenting."""
    kilde = FalskLusetall(tomme={(2026, 3)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-05")

    assert kode == 1
    assert kilde.hentet == [(2026, 1), (2026, 2), (2026, 3)]   # stoppet
    assert "Stoppet:" in capsys.readouterr().out


# ------------------------------------------------- retry gjennom hele veien

class TimeoutKlient:
    """Står i for httpx.Client. `feil` er antall ReadTimeout per uke før
    den svarer — akkurat feilen som stoppet backfillen i uke 44/2014."""

    def __init__(self, feil: dict[tuple[int, int], int]):
        self.feil = dict(feil)
        self.kall: list[tuple[int, int]] = []

    def get(self, url, **kwargs):
        aar, uke = (int(x) for x in url.rsplit("/", 2)[-2:])
        self.kall.append((aar, uke))

        igjen = self.feil.get((aar, uke), 0)
        if igjen:
            self.feil[(aar, uke)] = igjen - 1
            raise httpx.ReadTimeout("timed out",
                                    request=httpx.Request("GET", url))

        return httpx.Response(200, request=httpx.Request("GET", url), json={
            "year": aar, "week": uke,
            "localities": [
                {"localityNo": 10029, "name": "X", "avgAdultFemaleLice": 0.2,
                 "hasReportedLice": True, "isFallow": False},
            ],
        })


class HttpLusetall(FalskLusetall):
    """Henter gjennom det EKTE retry-laget i sources/_http.py.

    FalskLusetall over kaster direkte og beviser derfor bare backfillens
    egen feilhåndtering. Denne går veien kilden faktisk går — utfor(),
    PAUSER, FORSOK — så det som testes er sammenkoblingen, ikke en
    etterligning av den.
    """

    def __init__(self, klient: TimeoutKlient):
        super().__init__()
        self.klient = klient

    def hent_uke(self, aar, uke, client=None):
        self.hentet.append((aar, uke))
        svar = _http.get(self.klient, f"https://test.invalid/locality/{aar}/{uke}",
                         hva=f"uke {uke}/{aar}")
        return svar.json()


@pytest.fixture
def sovelogg(monkeypatch):
    """Fanger retry-pausene, og bare dem.

    `isolert` nuller backfill.time.sleep, men backfill.time og _http.time
    ER den samme modulen — en patch på den ene treffer den andre, og
    backfillens egen pause mellom uker havner i loggen. Derfor byttes
    backfills referanse ut med en egen stand-in først, slik at det som
    logges her utelukkende er backoff.
    """
    import types

    logg: list[float] = []
    monkeypatch.setattr(backfill, "time", types.SimpleNamespace(sleep=lambda s: None))
    monkeypatch.setattr(_http.time, "sleep", logg.append)
    return logg


def test_backoff_bruker_hele_serien_og_redder_uka(isolert, monkeypatch,
                                                  sovelogg, capsys):
    """Tre timeouts på rad, svar på fjerde forsøk.

    Dette er uka FORSOK = 3 ville tapt: med to omforsøk gir den opp
    rett før svaret kommer. Pausene skal være 1, 4 og 16 sekunder — og
    uka skal ligge skrevet etterpå.
    """
    klient = TimeoutKlient({(2014, 44): 3})
    kilde = HttpLusetall(klient)

    kode = _kjor(monkeypatch, kilde, "2014-44", "2014-44")

    assert sovelogg == [1.0, 4.0, 16.0], "hele backoff-serien, i rekkefølge"
    assert klient.kall == [(2014, 44)] * 4, "tre feil + ett svar = fire kall"
    assert kode == 0

    # Ikke bare exit-koden: fila skal faktisk ligge der.
    assert (snapshot.RAW_DIR / "lusetall" / "2014-10-27.parquet").exists()
    assert "1 uker skrevet" in capsys.readouterr().out


def test_oppbrukt_retry_feller_uka_men_ikke_kjoringen(isolert, monkeypatch,
                                                     sovelogg, capsys):
    """Uke 2 svarer aldri. Uke 1, 3 og 4 skal skrives likevel."""
    klient = TimeoutKlient({(2026, 2): 99})
    kilde = HttpLusetall(klient)

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-04")
    ut = capsys.readouterr().out

    # Uka koster fire kall og tre pauser, så gir den seg.
    assert klient.kall.count((2026, 2)) == _http.FORSOK
    assert sovelogg == [1.0, 4.0, 16.0]

    # Og kjøringen går videre til uker som kommer ETTER den som feilet.
    assert kilde.hentet == [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    assert "3 uker skrevet" in ut

    # Feillista er ikke tom, altså er exit-koden det ikke heller.
    assert kode != 0
    assert "1 uke(r) FEILET" in ut
    assert "ReadTimeout" in ut, "feillista skal navngi den ekte feilen"


def test_exit_null_naar_feillista_er_tom(isolert, monkeypatch, sovelogg):
    """Motprøven: samme vei gjennom _http, men uten en uke som feiler.

    Uten denne beviser testen over bare at koden kan bli 1, ikke at 1
    betyr noe.
    """
    kilde = HttpLusetall(TimeoutKlient({}))

    assert _kjor(monkeypatch, kilde, "2026-01", "2026-04") == 0
    assert sovelogg == [], "ingen feil, ingen pauser"
