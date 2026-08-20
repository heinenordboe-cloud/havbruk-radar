"""Gyldighetsdato mot kjøredato, gjennom hele innsamlingsløypa.

`observed_at` handler om verden, kjøredatoen om oss. Beslutningen fra
18.08 slo det fast, men regelen ble bare implementert i lusetall.parse().
run.py navnga filene etter kjøredagen, så den SAMME uka fikk ett filnavn
fra backfill (ukas mandag) og et annet fra ukejobben (kjøredagen).

Det er tredje gang samme rotårsak slår ut — F1 og F4 var de to første.
Testene her holder på begge sider av skjøten: at en uke havner samme
sted uansett hvilken vei den kom inn, og at kilder UTEN etterslep ikke
merker noe til at skillet finnes.
"""

import datetime as dt
import types

import polars as pl
import pytest

import backfill
import run as run_modul
from core import (changelog, diff, health, paths, raw as raw_arkiv, registry,
                 runner, snapshot)
from core.contract import Observation, Source
from sources.lusetall import Lusetall, mandag, uke_med_etterslep

MANDAG_24 = "2026-08-24"          # dagen jobben kjører
UKE_31 = "2026-07-27"             # mandagen i uke 31/2026 — N-4 fra den dagen
UKE_30 = "2026-07-20"             # siste uke backfillen rakk


# ------------------------------------------------------------- kilder

class TregKilde(Source):
    """Kilde med fire ukers etterslep, som lusetall."""

    name = "treg"
    entity_type = "lokalitet"

    def __init__(self, verdi="0.2"):
        self.verdi = verdi
        self.hentet_uke = None

    def gjelder_for(self, kjoredato: str) -> str:
        return mandag(*uke_med_etterslep(dt.date.fromisoformat(kjoredato), 4))

    def fetch(self, kjoredato):
        return {"verdi": self.verdi}

    def parse(self, raw, observed_at):
        self.hentet_uke = observed_at
        yield Observation(
            entity_id="10029", entity_type=self.entity_type, entity_name="X",
            field="voksne_hunnlus", value=raw["verdi"], source=self.name,
            observed_at=observed_at,
        )


class KjappKilde(Source):
    """Kilde uten etterslep. Rører ikke gjelder_for()."""

    name = "kjapp"
    entity_type = "selskap"

    def __init__(self, verdi="12"):
        self.verdi = verdi

    def fetch(self, kjoredato):
        return {"verdi": self.verdi}

    def parse(self, raw, observed_at):
        yield Observation(
            entity_id="999999999", entity_type=self.entity_type,
            entity_name="Testlaks AS", field="antall_ansatte",
            value=raw["verdi"], source=self.name, observed_at=observed_at,
        )


# ------------------------------------------------------------ oppsett

@pytest.fixture
def isolert(tmp_path, monkeypatch):
    """Egen datamappe, og en klokke som står stille på mandag 24.08."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(backfill.snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    monkeypatch.setattr(paths, "COMMIT_MSG_PATH", tmp_path / "siste.txt")
    monkeypatch.setattr(backfill.time, "sleep", lambda s: None)

    class FrossenKlokke:
        @staticmethod
        def now(tz=None):
            return dt.datetime(2026, 8, 24, 5, 0, tzinfo=dt.timezone.utc)

    monkeypatch.setattr(run_modul, "datetime", FrossenKlokke)

    # Prediksjoner er ikke det som testes her, og de leser ekte YAML.
    monkeypatch.setattr(run_modul, "predictions", types.SimpleNamespace(
        valider=lambda: [],
        evaluer=lambda dato: pl.DataFrame(),
        skriv=lambda fasit, dato: None,
    ))
    return tmp_path


def _kjor_uke(monkeypatch, kilder, ekstra=()):
    """Én ukekjøring, slik cron-jobben gjør den."""
    monkeypatch.setattr(run_modul.registry, "discover", lambda: list(kilder))
    monkeypatch.setattr("sys.argv", ["run.py", *ekstra])
    return run_modul.main()


def _les(sti):
    return pl.read_parquet(sti)


# ------------------------------------------------- selve gyldighetsdatoen

def test_ukekjoring_daterer_etter_uka_ikke_kjoredagen(isolert, monkeypatch):
    """Kjernen i funnet: mandag 24.08 skal skrive uke 31 til 2026-07-27.

    Før rettingen het fila 2026-08-24 og inneholdt rader observert
    2026-07-27 — filnavnet løy om innholdet.
    """
    treg = TregKilde()
    _kjor_uke(monkeypatch, [treg])

    fil = isolert / "raw/treg" / f"{UKE_31}.parquet"
    assert fil.exists(), f"forventet {UKE_31}.parquet, fant " \
                         f"{[p.name for p in (isolert / 'raw/treg').iterdir()]}"
    assert not (isolert / "raw/treg" / f"{MANDAG_24}.parquet").exists()

    # Filnavn OG kolonne, ikke bare det ene.
    assert _les(fil)["observed_at"].unique().to_list() == [UKE_31]
    assert treg.hentet_uke == UKE_31, "parse() skal få gyldighetsdatoen"


def test_arkivet_dateres_likt_med_snapshotet(isolert, monkeypatch):
    """Arkivet er grunnlaget for en re-parse. Ligger det på feil dato,
    må den som re-parser gjette hvilken uke fila hører til."""
    _kjor_uke(monkeypatch, [TregKilde()])

    arkiver = [p.name for p in (isolert / "arkiv/treg").iterdir()]
    assert arkiver == [f"{UKE_31}.json.gz"]


def test_changeloggen_dateres_etter_observasjonen(isolert, monkeypatch):
    """Endringene gjelder uka de ble observert i, ikke dagen vi så dem."""
    # Uke 30 finnes fra før, slik backfillen etterlot den.
    snapshot.write(list(TregKilde("0.1").parse({"verdi": "0.1"}, UKE_30)), UKE_30)

    _kjor_uke(monkeypatch, [TregKilde("0.9")])

    filer = sorted(p.name for p in (isolert / "changelog").iterdir())
    assert filer == [f"{UKE_31}.parquet"]

    rader = _les(isolert / "changelog" / f"{UKE_31}.parquet")
    assert rader["observed_at"].unique().to_list() == [UKE_31]
    assert rader["new_value"].to_list() == ["0.9"]


def test_kilder_med_og_uten_etterslep_i_samme_kjoring(isolert, monkeypatch):
    """Én kjøring, to datoer. Hver kilde skal på sin egen."""
    _kjor_uke(monkeypatch, [TregKilde(), KjappKilde()])

    assert (isolert / "raw/treg" / f"{UKE_31}.parquet").exists()
    assert (isolert / "raw/kjapp" / f"{MANDAG_24}.parquet").exists()

    assert (_les(isolert / "raw/treg" / f"{UKE_31}.parquet")
            ["observed_at"].unique().to_list() == [UKE_31])
    assert (_les(isolert / "raw/kjapp" / f"{MANDAG_24}.parquet")
            ["observed_at"].unique().to_list() == [MANDAG_24])


# ------------------------------------------------- kilder uten etterslep

def test_kilder_uten_etterslep_er_uendret(isolert, monkeypatch):
    """Standardsvaret er kjøredatoen. En kilde uten etterslep skal ikke
    merke at skillet finnes."""
    _kjor_uke(monkeypatch, [KjappKilde()])

    fil = isolert / "raw/kjapp" / f"{MANDAG_24}.parquet"
    assert fil.exists()
    assert _les(fil)["observed_at"].unique().to_list() == [MANDAG_24]
    assert [p.name for p in (isolert / "arkiv/kjapp").iterdir()] \
        == [f"{MANDAG_24}.json.gz"]


def test_de_ekte_kildene_uten_etterslep_arver_standarden():
    """akvakultur og enhetsregisteret skal IKKE ha overstyrt gjelder_for.

    Går noen og legger inn en overstyring der uten å mene det, daterer de
    seg selv i fortida. Testen leser klassene, ikke nett.
    """
    from sources.akvakultur import Akvakulturregisteret
    from sources.enhetsregisteret import Enhetsregisteret

    for klasse in (Akvakulturregisteret, Enhetsregisteret):
        assert klasse.gjelder_for is Source.gjelder_for, \
            f"{klasse.__name__} har overstyrt gjelder_for()"
        assert klasse().gjelder_for("2026-08-24") == "2026-08-24"


# ------------------------------------------------------- den ekte kilden

def test_lusetall_gjelder_for_er_ukas_mandag():
    assert Lusetall().gjelder_for(MANDAG_24) == UKE_31


def test_lusetall_henter_og_daterer_samme_uke():
    """fetch() og gjelder_for() må svare på det samme spørsmålet.

    Regnes de ut hver for seg, kan de drifte fra hverandre — og da får
    fila navn etter én uke og innhold fra en annen. De deler _uke_naa().
    """
    kilde = Lusetall()

    assert kilde._uke_naa(MANDAG_24) == (2026, 31)
    assert mandag(*kilde._uke_naa(MANDAG_24)) == kilde.gjelder_for(MANDAG_24)


# ------------------------------------------------- invarianten mot backfill

def test_backfill_og_ukekjoring_gir_samme_fil_for_samme_uke(isolert, monkeypatch):
    """Invarianten. Samme uke, to veier inn, ett filnavn og én dato.

    Dette er hele grunnen til at feilen var alvorlig: uten den kan ikke
    de to løypene møtes uten å legge igjen en skjøt.
    """
    # Vei 1: backfill av uke 31.
    monkeypatch.setattr(backfill.registry, "discover", lambda: [_BackfillTreg()])
    monkeypatch.setattr(backfill, "_ferskeste_tillatte", lambda k: (2026, 40))
    monkeypatch.setattr(backfill.changelog, "CHANGELOG_DIR", isolert / "changelog")
    monkeypatch.setattr("sys.argv", ["backfill.py", "--kilde", "treg",
                                     "--fra", "2026-31", "--til", "2026-31",
                                     "--pause", "0"])
    assert backfill.main() == 0

    fra_backfill = sorted((isolert / "raw/treg").iterdir())
    assert [p.name for p in fra_backfill] == [f"{UKE_31}.parquet"]
    dato_backfill = _les(fra_backfill[0])["observed_at"].unique().to_list()

    # Vei 2: den ukentlige jobben, samme uke.
    for p in fra_backfill:
        p.unlink()
    _kjor_uke(monkeypatch, [TregKilde()])

    fra_uke = sorted((isolert / "raw/treg").iterdir())
    assert [p.name for p in fra_uke] == [f"{UKE_31}.parquet"]
    assert _les(fra_uke[0])["observed_at"].unique().to_list() == dato_backfill


class _BackfillTreg(TregKilde):
    """TregKilde med hent_uke(), slik backfill krever."""

    def hent_uke(self, aar, uke, client=None):
        return {"verdi": "0.2"}


def test_serien_er_kontinuerlig_over_skjoten(isolert, monkeypatch):
    """Uke 30 fra backfill, uke 31 fra ukejobben: ingen hull, ingen
    duplikat, og ukene ligger sju dager fra hverandre."""
    snapshot.write(list(TregKilde("0.1").parse({"verdi": "0.1"}, UKE_30)), UKE_30)

    _kjor_uke(monkeypatch, [TregKilde("0.2")])

    filer = sorted(p.stem for p in (isolert / "raw/treg").iterdir())
    assert filer == [UKE_30, UKE_31]

    d = [dt.date.fromisoformat(f) for f in filer]
    assert (d[1] - d[0]).days == 7
    assert len(set(filer)) == len(filer), "ingen dato to ganger"


# ----------------------------------------------------------- vaktene

def test_uke_som_alt_er_skrevet_hoppes_over(isolert, monkeypatch, capsys):
    """snapshot.finnes_allerede() er nå koblet inn i run.py.

    Uten den ville kjøring nummer to i samme uke pekt på samme
    gyldighetsdato og lagt igjen en .2-fil ved siden av den første.

    health.json tømmes mellom kjøringene med vilje. Frekvensvakten er
    førstelinja, men den svarer `None -> forfalt` for en kilde den ikke
    kjenner — og det er nøyaktig tilstanden lusetall står i nå, der
    health.json bare kjenner akvakultur og enhetsregisteret. Da er denne
    vakten det eneste som står mellom en gjenkjøring og en .2-fil.
    """
    treg = TregKilde()
    _kjor_uke(monkeypatch, [treg])
    capsys.readouterr()

    health.HEALTH_PATH.unlink()          # kilden er «ukjent» igjen

    andre = TregKilde()
    kode = _kjor_uke(monkeypatch, [andre])

    assert andre.hentet_uke is None, "skal ikke koste et API-kall engang"
    assert kode == 0
    assert "ligger skrevet fra før" in capsys.readouterr().out
    assert sorted(p.name for p in (isolert / "raw/treg").iterdir()) \
        == [f"{UKE_31}.parquet"], "ingen .2-fil"


def test_tving_overstyrer_har_allerede(isolert, monkeypatch):
    """--tving er den bevisste veien rundt vakten, og løpenummeret
    finnes nettopp for det tilfellet."""
    _kjor_uke(monkeypatch, [TregKilde()])
    _kjor_uke(monkeypatch, [TregKilde()], ekstra=["--tving"])

    assert sorted(p.name for p in (isolert / "raw/treg").iterdir()) \
        == [f"{UKE_31}.2.parquet", f"{UKE_31}.parquet"]


def test_frekvensvakten_maaler_fortsatt_kjoredato(isolert, monkeypatch):
    """health.json skal stemples med DAGEN VI KJØRTE, ikke med uka.

    Sendes gyldighetsdatoen hit, tror vakten at kilden sist kjørte for
    fire uker siden — hver eneste uke. Det er F4 om igjen.
    """
    _kjor_uke(monkeypatch, [TregKilde()])

    post = health.les()["treg"]
    assert post["sist_forsok"] == MANDAG_24
    assert post["sist_ok"] == MANDAG_24
    assert health.dager_siden_kjoring("treg", MANDAG_24) == 0


# -------------------------------------------------------- selve vaktposten

def test_write_nekter_filnavn_som_ikke_stemmer_med_radene(isolert):
    """Vaktposten som gjør skjøten umulig å lage på nytt."""
    obs = list(TregKilde().parse({"verdi": "0.2"}, UKE_31))

    with pytest.raises(ValueError, match="filnavnet skulle vært"):
        snapshot.write(obs, MANDAG_24)

    assert not (isolert / "raw/treg").exists(), "ingenting skal være skrevet"
