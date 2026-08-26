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


# --------------------------------------- stopp når TJENESTEN er nede (F12)

def test_maks_feil_paa_rad_stopper_kjoringen(isolert, monkeypatch, capsys):
    """F12: 522 uker på rad feilet med 401 og kjøringen gikk i ni timer.

    Én uke som feiler er en uke. N på rad er en tjeneste som er nede, og
    resten av intervallet er bortkastede kall.
    """
    kilde = FalskLusetall(feiler={(2026, 2), (2026, 3), (2026, 4)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-10")
    ut = capsys.readouterr().out

    assert kode == 1
    # Stoppet på den tredje, forsøkte ikke uke 5-10.
    assert kilde.hentet == [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    assert "STOPPET" in ut and "3 uker på rad" in ut
    assert "Skrev 1 uker" in ut
    # Feillista skal komme også når den stopper tidlig — ellers er hullet
    # usynlig, som før feillista fantes.
    assert "3 uke(r) FEILET" in ut
    assert "Kjør samme intervall på nytt" in ut


def test_spredte_feil_stopper_ikke(isolert, monkeypatch, capsys):
    """Telleren nullstilles av et RESULTAT, ikke av et forsøk (1b-2).

    To feil med en vellykket uke imellom er ikke en tjeneste som er nede,
    og en backfill på 761 uker skal tåle dem.
    """
    kilde = FalskLusetall(feiler={(2026, 2), (2026, 4), (2026, 6), (2026, 8)})

    kode = _kjor(monkeypatch, kilde, "2026-01", "2026-10")
    ut = capsys.readouterr().out

    assert kode == 1                      # hullene er reelle
    assert len(kilde.hentet) == 10        # men alle ti ble forsøkt
    assert "STOPPET" not in ut
    assert "4 uke(r) FEILET" in ut


def test_loggen_er_tidsstemplet(isolert, monkeypatch, capsys):
    """Uten tid per linje kan en ratebegrensning ikke skilles fra en
    tokenfeil i ettertid. Loggen fra 24.08 hadde ingen."""
    import re

    _kjor(monkeypatch, FalskLusetall(), "2026-01", "2026-02")
    ut = capsys.readouterr().out

    linjer = [ln for ln in ut.splitlines() if ln.strip()]
    assert linjer, "ingen utskrift å tidsstemple"
    monster = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}  ")
    assert all(monster.match(ln) for ln in linjer), \
        f"utidsstemplet linje: {[ln for ln in linjer if not monster.match(ln)][:3]}"


# ------------------------------------------------------ proveniens (1b-3)

class UtvalgKilde(FalskLusetall):
    """Setter utvalg i hent_uke(), slik sjotemperatur gjør."""

    def hent_uke(self, aar, uke, client=None):
        self.utvalg = {"rapporttype": ["Lice"]}
        return super().hent_uke(aar, uke)


def test_backfillede_rader_baerer_utvalg(isolert, monkeypatch, capsys):
    """Regel 1b-3: et snapshot skal alene kunne svare på hva vi lette etter.

    backfill.py kalte hent_uke() direkte og sendte aldri utvalget videre
    til stempl(). 389 206 rader ble skrevet med tomt utvalg 24.08.2026.
    """
    import polars as pl
    from core import utvalg as utvalg_modul

    assert _kjor(monkeypatch, UtvalgKilde(), "2026-01", "2026-02") == 0

    fil = isolert / "raw/lusetall/2025-12-29.parquet"
    if not fil.exists():
        fil = sorted((isolert / "raw/lusetall").glob("*.parquet"))[0]
    rader = pl.read_parquet(fil)

    forventet = utvalg_modul.serialiser({"rapporttype": ["Lice"]})
    assert rader["utvalg"].unique().to_list() == [forventet]
    assert forventet != "", "tomt utvalg leses «vet ikke», ikke «ingen filtrering»"


def test_kilde_uten_utvalg_gir_tomt_felt_ikke_krasj(isolert, monkeypatch, capsys):
    """En kilde som ikke oppgir utvalg skal fortsatt kunne backfilles."""
    import polars as pl

    assert _kjor(monkeypatch, FalskLusetall(), "2026-01", "2026-02") == 0
    fil = sorted((isolert / "raw/lusetall").glob("*.parquet"))[0]
    assert pl.read_parquet(fil)["utvalg"].unique().to_list() == [""]


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


# ---- månedsmodus -----------------------------------------------------
#
# Ukemodus gjør ett kall per uke og er bygget rundt at kall feiler.
# Månedsmodus gjør ETT kall for hele serien, og har derfor helt andre
# feilmoduser: ikke «uke 300 av 730 feilet», men «måneden ligger ikke i
# fila», og ikke «arkivér hver uke», men «arkivér svaret én gang».

class FalskBiomasse(Source):
    """Svarer på hent_alt(). `mangler` er måneder som ikke er i fila."""

    name = "biomasse"
    entity_type = "produksjonsomraade"

    def __init__(self, mangler=()):
        self.mangler = set(mangler)
        self.kall = 0

    def hent_alt(self, client=None):
        self.kall += 1
        self.utvalg = {}
        return "hele-serien"

    def gjelder_for(self, kjoredato):
        return "2026-04-30"

    def parse(self, raw, observed_at):
        aar, mnd = int(observed_at[:4]), int(observed_at[5:7])
        if (aar, mnd) in self.mangler:
            raise RuntimeError(f"{aar}-{mnd:02d} ligger ikke i fila")
        for po in ("1", "2"):
            yield Observation(
                entity_id=po, entity_type=self.entity_type,
                entity_name=f"PO {po}", field="beholdning_antall",
                value=f"{1000 + mnd}", source=self.name,
                observed_at=observed_at,
            )


def _kjor_mnd(monkeypatch, kilde, fra, til, ekstra=()):
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "biomasse",
                                     "--fra", fra, "--til", til, *ekstra])
    return backfill.main()


def test_maanedsmodus_henter_en_gang_for_hele_serien(isolert, monkeypatch, capsys):
    """Fila bærer alle månedene. 106 måneder skal koste ett kall, ikke 106."""
    kilde = FalskBiomasse()

    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04") == 0
    assert kilde.kall == 1

    ut = capsys.readouterr().out
    assert "4 måneder skrevet" in ut
    for dato in ("2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"):
        assert (isolert / "raw" / "biomasse" / f"{dato}.parquet").exists()


def test_arkivet_skrives_en_gang_og_alle_maanedene_deler_hash(isolert,
                                                              monkeypatch):
    """raw_hash er INNHOLDSADRESSERT (core/raw.py). 106 snapshots som
    peker på ett råsvar er en sann påstand — 106 identiske kopier av en
    650 kB fil i datarepoet er ikke en bedre en."""
    import polars as pl

    kilde = FalskBiomasse()
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04") == 0

    arkiv = sorted((isolert / "arkiv" / "biomasse").glob("*"))
    assert [p.name for p in arkiv] == ["2026-04-30.txt.gz"], \
        "arkivet dateres etter den nyeste måneden i intervallet"

    hasher = set()
    for p in sorted((isolert / "raw" / "biomasse").glob("*.parquet")):
        hasher |= set(pl.read_parquet(p)["raw_hash"].to_list())
    assert len(hasher) == 1 and hasher != {""}


def test_maaned_som_mangler_er_et_hull_ikke_et_avbrudd(isolert, monkeypatch,
                                                       capsys):
    """De øvrige månedene ligger i det samme svaret og er like gyldige.
    Å stoppe ville kastet dem for ingenting — men hullet skal navngis og
    kjøringen ende rødt."""
    kilde = FalskBiomasse(mangler=[(2026, 2)])

    kode = _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04")
    ut = capsys.readouterr().out

    assert kode != 0
    assert "3 måneder skrevet" in ut
    assert "1 måned(er) MANGLET" in ut
    assert "2026-02" in ut
    assert (isolert / "raw" / "biomasse" / "2026-03-31.parquet").exists()
    assert not (isolert / "raw" / "biomasse" / "2026-02-28.parquet").exists()


def test_maanedsmodus_er_gjenopptakbar(isolert, monkeypatch, capsys):
    """Uten dette gir en omstart .2-filer for hver måned som allerede lå
    der — både snapshot og arkiv løser kollisjon med løpenummer."""
    kilde = FalskBiomasse()
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-02")
    capsys.readouterr()

    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04") == 0
    ut = capsys.readouterr().out
    assert "2 måneder skrevet, 2 hoppet over" in ut
    assert not list((isolert / "raw" / "biomasse").glob("*.2.parquet"))


def test_til_klippes_ved_kildens_egen_etterslepsgrense(isolert, monkeypatch,
                                                       capsys):
    """Grensen spørres AV KILDEN med dagens dato, ikke regnet ut på nytt
    her. To tall som ligner er F7 — her finnes det bare ett svar."""
    kilde = FalskBiomasse()

    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-09") == 0
    ut = capsys.readouterr().out
    assert "Klipper der" in ut
    assert "4 måneder skrevet" in ut


def test_torrkjoring_skriver_ingenting(isolert, monkeypatch, capsys):
    kilde = FalskBiomasse()

    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04",
                     ekstra=("--torrkjor",)) == 0
    assert not (isolert / "raw").exists()
    assert not (isolert / "arkiv").exists()
    assert "TØRRKJØRING" in capsys.readouterr().out


def test_ugyldig_maaned_avvises():
    with pytest.raises(ValueError):
        backfill._parse_maaned("2026-13")


def test_maanedsloopen_taaler_arsskiftet():
    assert list(backfill._maaneder((2025, 11), (2026, 2))) == [
        (2025, 11), (2025, 12), (2026, 1), (2026, 2)]


def test_alle_maanedene_deler_ett_hentetidspunkt(isolert, monkeypatch):
    """De kom fra det samme kallet. 103 stempler som spriker på
    mikrosekundet ville påstått 103 hentinger — og for en kilde som
    reviderer fortiden er fetched_at ikke bokføring, men hvilken påstand
    raden er (CLAUDE.md 1b-5)."""
    import polars as pl

    kilde = FalskBiomasse()
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04") == 0

    stempler = set()
    for p in sorted((isolert / "raw" / "biomasse").glob("*.parquet")):
        stempler |= set(pl.read_parquet(p)["fetched_at"].to_list())
    assert len(stempler) == 1


# ---- revisjonsmodus --------------------------------------------------
#
# Speilbildet av månedsmodus: backfill skriver månedene vi MANGLER,
# revisjon gjennomgår månedene vi HAR. Testene under holder de to fra
# hverandre, og passer på at en revisjon ikke rører den gamle fila.

class ReviderendeBiomasse(FalskBiomasse):
    """Som FalskBiomasse, men `verdi` kan byttes mellom kjøringene —
    slik den ekte fila endrer seg mellom to publiseringer."""

    def __init__(self, verdi="1000", mangler=(), version="1"):
        super().__init__(mangler=mangler)
        self.verdi = verdi
        self.version = version

    def hent_alt(self, client=None):
        # Kroppen skal endre seg SAMMEN med verdiene. En falsk kilde der
        # svaret er konstant mens parsingen endrer seg ville skjult at
        # arkivet dedupliserer på innhold.
        self.kall += 1
        self.utvalg = {}
        return f"hele-serien-{self.verdi}"

    def parse(self, raw, observed_at):
        aar, mnd = int(observed_at[:4]), int(observed_at[5:7])
        if (aar, mnd) in self.mangler:
            raise RuntimeError(f"{aar}-{mnd:02d} ligger ikke i fila")
        for po in ("1", "2"):
            # PO 1 varierer med MÅNEDEN, så compare() har ekte bevegelse
            # å finne, og med `verdi`, så revisjon() har ekte revisjon å
            # finne. De to aksene må kunne skilles i den samme fila.
            yield Observation(
                entity_id=po, entity_type=self.entity_type,
                entity_name=f"PO {po}", field="beholdning_antall",
                value=str(int(self.verdi) + mnd) if po == "1" else "500",
                source=self.name, observed_at=observed_at,
            )


def test_revisjon_skriver_bare_der_noe_faktisk_er_endret(isolert, monkeypatch,
                                                         capsys):
    """En identisk `.2`-fil ville vært ren støy i et append-only repo —
    og en påstand om at kilden sa noe nytt da den ikke gjorde det."""
    import polars as pl

    kilde = ReviderendeBiomasse(verdi="1000")
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03") == 0
    capsys.readouterr()

    # Ingen endring: ingen nye filer.
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03",
                     ekstra=("--revisjon",)) == 0
    ut = capsys.readouterr().out
    assert "0 måneder REVIDERT, 3 uendret" in ut
    assert not list((isolert / "raw" / "biomasse").glob("*.2.parquet"))

    # Kilden ombestemmer seg.
    kilde.verdi = "1750"
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03",
                     ekstra=("--revisjon",)) == 0
    ut = capsys.readouterr().out
    assert "3 måneder REVIDERT, 0 uendret" in ut

    # Den gamle fila står URØRT ved siden av den nye.
    mappe = isolert / "raw" / "biomasse"
    gammel = pl.read_parquet(mappe / "2026-01-31.parquet")
    ny = pl.read_parquet(mappe / "2026-01-31.2.parquet")
    assert gammel.filter(pl.col("entity_id") == "1")["value"][0] == "1001"
    assert ny.filter(pl.col("entity_id") == "1")["value"][0] == "1751"


def test_revisjonens_changelog_sletter_ikke_bevegelsens(isolert, monkeypatch):
    """Løpenummeret på changelog-fila skal følge snapshotets. Uten det
    ville «januar mot januar» skrevet over «januar mot desember»."""
    import polars as pl

    kilde = ReviderendeBiomasse(verdi="1000")
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03")
    kilde.verdi = "1750"
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03", ekstra=("--revisjon",))

    mappe = isolert / "changelog" / "biomasse"
    assert sorted(p.name for p in mappe.glob("2026-02-28*")) == [
        "2026-02-28.2.parquet", "2026-02-28.parquet"]
    assert set(pl.read_parquet(mappe / "2026-02-28.parquet")["change_type"]) \
        == {"endret"}
    assert set(pl.read_parquet(mappe / "2026-02-28.2.parquet")["change_type"]) \
        == {"revidert"}


def test_revisjon_hopper_over_maaneder_vi_ikke_har(isolert, monkeypatch,
                                                   capsys):
    """En måned som ikke er skrevet er ikke en revisjon — den er
    backfillens bord, og skal ikke smugles inn her hvor changeloggen
    ville kalt den «revidert»."""
    kilde = ReviderendeBiomasse(verdi="1000")
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-02")
    capsys.readouterr()

    kilde.verdi = "1750"
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-04",
                     ekstra=("--revisjon",)) == 0
    ut = capsys.readouterr().out
    assert "2 måneder REVIDERT" in ut
    assert "2 hoppet over (ikke skrevet ennå)" in ut
    assert not (isolert / "raw" / "biomasse" / "2026-03-31.parquet").exists()


def test_revisjon_uten_datoer_tar_alt_vi_har(isolert, monkeypatch, capsys):
    """Cron-linja er `--kilde biomasse --revisjon`. Datoer som må flyttes
    hver måned er datoer noen glemmer å flytte."""
    kilde = ReviderendeBiomasse(verdi="1000")
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03")
    capsys.readouterr()

    kilde.verdi = "1750"
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "biomasse",
                                     "--revisjon"])
    assert backfill.main() == 0
    ut = capsys.readouterr().out
    assert "2026-01 -> 2026-03" in ut
    assert "3 måneder REVIDERT" in ut


def test_grunnlagssprik_stopper_revisjonen_og_gir_exit_1(isolert, monkeypatch,
                                                         capsys):
    """Bumpes source_version, kan en forskjell like gjerne være vår egen
    parser. Da skal begge snapshots stå, og jobben bli rød."""
    kilde = ReviderendeBiomasse(verdi="1000", version="1")
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-02")
    capsys.readouterr()

    kilde.verdi, kilde.version = "1750", "2"
    assert _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-02",
                     ekstra=("--revisjon",)) == 1
    ut = capsys.readouterr().out
    assert "GRUNNLAGSSPRIK" in ut
    assert "2 måned(er) kunne IKKE vurderes" in ut
    assert not list((isolert / "raw" / "biomasse").glob("*.2.parquet"))


def test_revisjon_avvises_for_en_ukekilde(isolert, monkeypatch, capsys):
    """Uten hent_alt() finnes det ikke to versjoner av samme uke å
    sammenligne — hver uke er sitt eget kall."""
    kilde = FalskLusetall()
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "lusetall",
                                     "--revisjon"])
    assert backfill.main() == 1
    assert "--revisjon krever en kilde" in capsys.readouterr().out


def test_ukekilde_uten_datoer_sier_fra(isolert, monkeypatch, capsys):
    kilde = FalskLusetall()
    monkeypatch.setattr(backfill.registry, "discover", lambda: [kilde])
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "lusetall"])
    assert backfill.main() == 1
    assert "--fra og --til kreves" in capsys.readouterr().out


def test_samme_kropp_arkiveres_ikke_to_ganger(isolert, monkeypatch, capsys):
    """Revisjonskjøringen leser den samme publiseringen som månedsjobben
    allerede arkiverte. Uten hash-sjekken ville den lagt igjen en
    identisk 200 kB-kopi hver måned for å dokumentere ingenting."""
    kilde = ReviderendeBiomasse(verdi="1000")
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03")
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03", ekstra=("--revisjon",))
    capsys.readouterr()

    arkiv = sorted((isolert / "arkiv" / "biomasse").glob("*"))
    assert len(arkiv) == 1, [p.name for p in arkiv]

    # En NY kropp arkiveres, også når den kommer fra revisjonskjøringen.
    kilde.verdi = "1750"
    _kjor_mnd(monkeypatch, kilde, "2026-01", "2026-03", ekstra=("--revisjon",))
    assert "allerede arkivert" not in capsys.readouterr().out
    assert len(list((isolert / "arkiv" / "biomasse").glob("*"))) == 2


def test_hashene_leser_det_som_ligger_der(isolert):
    from core import raw as ra
    assert ra.hashene("biomasse") == set()
    h = ra.arkiver("biomasse", "2026-01-31", "en kropp")
    assert ra.hashene("biomasse") == {h}
    assert ra.arkiver_ny("biomasse", "2026-02-28", "en kropp") == (h, False)
    h2, skrev = ra.arkiver_ny("biomasse", "2026-02-28", "en annen kropp")
    assert skrev and h2 != h
    assert ra.hashene("biomasse") == {h, h2}
