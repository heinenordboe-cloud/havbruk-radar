"""arkiver_daglig.py: kroppen skrives bare når den avviker fra siste lagrede.

Ingen nettverk: kildene er falske, og `registry.discover` byttes ut.
"""

import gzip
import hashlib
import json

import pytest

import arkiver_daglig as ark
from core import raw as raw_arkiv
from core import registry


class Falsk:
    """En kilde som svarer det `svar` sier, og kan feile."""

    version = "1"

    def __init__(self, name, svar):
        self.name, self.svar = name, svar
        self.utvalg = {"utelatt": ["PERSON"]}

    def fetch(self, kjoredato):
        verdi = self.svar[self.name]
        if isinstance(verdi, Exception):
            raise verdi
        return verdi


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path / "arkiv"


@pytest.fixture
def svar(monkeypatch):
    s = {"eierskap": {"tillatelser": [1]}, "biomasselag": [{"a": 1}]}
    monkeypatch.setattr(registry, "discover",
                        lambda: [Falsk(n, s) for n in ("eierskap", "biomasselag")])
    return s


def logger(arkiv, kilde):
    return [json.loads(p.read_text()) for p in sorted((arkiv / kilde).glob("*.logg.json"))]


def kropper(arkiv, kilde):
    return sorted(p.name for p in (arkiv / kilde).glob("*.gz"))


def test_forste_kjoring_skriver_kropp_og_logg(arkiv, svar):
    assert ark.main(["--dato", "2026-10-13"]) == 0
    assert kropper(arkiv, "eierskap") == ["2026-10-13.daglig.json.gz"]
    [logg] = logger(arkiv, "eierskap")
    assert logg["kjoring"] == "daglig" and logg["status"] == "ny"
    assert logg["fil"] == "2026-10-13.daglig.json.gz"
    assert logg["sammenlignet_med"] is None
    assert logg["kode_commit"] == "0" * 40          # conftest låser den
    assert logg["utvalg"] == {"utelatt": ["PERSON"]}


def test_kroppen_er_de_samme_bytene_som_innsamlingen_ville_skrevet(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    data, _ = raw_arkiv._serialiser(svar["eierskap"])
    lagret = gzip.open(arkiv / "eierskap" / "2026-10-13.daglig.json.gz", "rb").read()
    assert lagret == data
    assert logger(arkiv, "eierskap")[0]["sha256"] == hashlib.sha256(data).hexdigest()


def test_uendret_mot_ukentlig_kropp_gir_bare_logg(arkiv, svar):
    """Mandagens kropp fra innsamlingen har ingen logg: den er ukentlig."""
    raw_arkiv.arkiver("eierskap", "2026-10-12", svar["eierskap"])
    assert ark.main(["--dato", "2026-10-13"]) == 0
    assert kropper(arkiv, "eierskap") == ["2026-10-12.json.gz"]
    [logg] = logger(arkiv, "eierskap")
    assert logg["status"] == "uendret" and "fil" not in logg
    assert logg["sammenlignet_med"]["fil"] == "2026-10-12.json.gz"
    assert logg["sammenlignet_med"]["kjoring"] == "ukentlig"


def test_uendret_mot_daglig_kropp_sier_daglig(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    ark.main(["--dato", "2026-10-14"])
    assert kropper(arkiv, "eierskap") == ["2026-10-13.daglig.json.gz"]
    andre = logger(arkiv, "eierskap")[1]
    assert andre["status"] == "uendret"
    assert andre["sammenlignet_med"] == {
        "fil": "2026-10-13.daglig.json.gz", "kjoring": "daglig",
        "sha256": logger(arkiv, "eierskap")[0]["sha256"]}


def test_endret_kropp_samme_dag_som_innsamlingen_faar_eget_navn(arkiv, svar):
    raw_arkiv.arkiver("eierskap", "2026-10-13", svar["eierskap"])
    svar["eierskap"] = {"tillatelser": [1, 2]}
    ark.main(["--dato", "2026-10-13"])
    assert kropper(arkiv, "eierskap") == ["2026-10-13.daglig.json.gz", "2026-10-13.json.gz"]
    [logg] = logger(arkiv, "eierskap")
    assert logg["status"] == "ny" and logg["fil"] == "2026-10-13.daglig.json.gz"
    assert logg["sammenlignet_med"]["fil"] == "2026-10-13.json.gz"


def test_lopenummeret_teller_innenfor_daglig(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    svar["eierskap"] = {"tillatelser": [1, 2]}
    ark.main(["--dato", "2026-10-13"])
    assert kropper(arkiv, "eierskap") == [
        "2026-10-13.daglig.2.json.gz", "2026-10-13.daglig.json.gz"]
    assert ark.siste_kropp("eierskap").name == "2026-10-13.daglig.2.json.gz"


def test_siste_kropp_ser_begge_og_innsamlingen_forst_samme_dato(arkiv, svar):
    """`raw.orden()`: dato, så merke, så løpenummer — ikke filnavnet, der
    `.daglig.` ville stått foran `.2.` og bak `.json.gz`."""
    ark.main(["--dato", "2026-10-13"])
    raw_arkiv.arkiver("eierskap", "2026-10-13", {"tillatelser": [7]})
    raw_arkiv.arkiver("eierskap", "2026-10-13", {"tillatelser": [8]})
    assert [p.name for p in raw_arkiv.kropper("eierskap")] == [
        "2026-10-13.json.gz", "2026-10-13.2.json.gz", "2026-10-13.daglig.json.gz"]
    raw_arkiv.arkiver("eierskap", "2026-10-14", {"tillatelser": [9]})
    assert ark.siste_kropp("eierskap").name == "2026-10-14.json.gz"


def test_innsamlingen_skriver_aldri_et_daglig_navn_og_omvendt(arkiv, svar):
    """Det som gjør navnene disjunkte. Innsamlingen (`core/runner.py`)
    kaller `raw.arkiver()` uten merke."""
    for _ in range(3):
        ark.main(["--dato", "2026-10-13"])
        svar["eierskap"] = {"tillatelser": [len(kropper(arkiv, "eierskap"))]}
        raw_arkiv.arkiver("eierskap", "2026-10-13", svar["eierskap"])
    for navn in kropper(arkiv, "eierskap"):
        daglig = navn in {l.get("fil") for l in logger(arkiv, "eierskap")}
        assert (raw_arkiv.merke(navn) == "daglig") == daglig, navn


def test_tilbake_til_en_gammel_kropp_er_en_endring(arkiv, svar):
    """A, B, A: den tredje avviker fra SISTE lagrede (B), og skrives — selv
    om de samme bytene ligger i arkivet fra før. Det er forskjellen fra
    `raw.arkiver_ny()`, og det er den som bevarer at registeret gikk tilbake."""
    a = svar["eierskap"]
    ark.main(["--dato", "2026-10-13"])
    svar["eierskap"] = {"tillatelser": [9]}
    ark.main(["--dato", "2026-10-14"])
    svar["eierskap"] = a
    ark.main(["--dato", "2026-10-15"])
    assert kropper(arkiv, "eierskap") == [
        "2026-10-13.daglig.json.gz", "2026-10-14.daglig.json.gz", "2026-10-15.daglig.json.gz"]


def test_to_kjoringer_samme_dag_gir_to_logger(arkiv, svar):
    ark.main(["--dato", "2026-10-13"])
    ark.main(["--dato", "2026-10-13"])
    navn = sorted(p.name for p in (arkiv / "eierskap").glob("*.logg.json"))
    assert navn == ["2026-10-13.daglig.2.logg.json", "2026-10-13.daglig.logg.json"]


def test_en_kilde_som_feiler_koster_ikke_de_andre(arkiv, svar, capsys):
    svar["eierskap"] = RuntimeError("503")
    assert ark.main(["--dato", "2026-10-13"]) == 1
    assert "::error::Daglig arkiv: eierskap feilet: RuntimeError: 503" \
        in capsys.readouterr().out
    assert not (arkiv / "eierskap").exists()
    assert kropper(arkiv, "biomasselag") == ["2026-10-13.daglig.json.gz"]


def test_torrkjoring_skriver_ingenting(arkiv, svar, monkeypatch):
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("urent")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)
    assert ark.main(["--torrkjor", "--dato", "2026-10-13"]) == 0
    assert not arkiv.exists()


def test_kode_som_ikke_kan_spores_henter_ingenting(arkiv, svar, monkeypatch, capsys):
    from core import kodeproveniens

    def ikke(*a, **k):
        raise kodeproveniens.IkkeSporbar("HEAD finnes ikke på origin/main")
    monkeypatch.setattr(kodeproveniens, "krev_sporbar", ikke)
    svar["eierskap"] = AssertionError("skulle ikke hentet noe")
    assert ark.main(["--dato", "2026-10-13"]) == 1
    assert "::error::Det daglige arkivet startet ikke" in capsys.readouterr().out
    assert not arkiv.exists()


def test_akvakultur_er_ikke_med_for_lagringsformen_er_valgt():
    """MÅLT 13.10.2026: kroppen er aldri byte-lik (rekkefølgen i
    speciesTypes). Se modulens docstring. Prøven står så kilden ikke
    legges til uten at noen har sett hvorfor den mangler."""
    assert "akvakultur" not in ark.KILDER


def _git(cwd, *args, sjekk=True):
    import subprocess
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, capture_output=True, text=True, check=sjekk)


def _to_kloner(tmp_path):
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    _git(tmp_path, "clone", "-q", "origin.git", "samle")
    (tmp_path / "samle" / "README").write_text("x")
    _git(tmp_path / "samle", "add", "README")
    _git(tmp_path / "samle", "commit", "-q", "-m", "start")
    _git(tmp_path / "samle", "push", "-q", "origin", "main")
    _git(tmp_path, "clone", "-q", "origin.git", "daglig")
    return tmp_path / "samle", tmp_path / "daglig"


@pytest.mark.parametrize("merket", [True, False])
def test_innsamling_og_daglig_samme_dato_fra_hver_sin_checkout(
        tmp_path, svar, monkeypatch, merket):
    """samle.yml og daglig.yml checker ut før hverandre har pushet, og
    skriver begge eierskap for 13.10 med ULIKT innhold. Med merket rebaser
    den siste rent; uten (slik det var fram til 13.10.2026) stopper rebasen
    på konflikt — den formen rebase-løkka prøver tre ganger og gir opp."""
    samle, daglig = _to_kloner(tmp_path)

    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", samle / "data" / "arkiv")
    raw_arkiv.arkiver("eierskap", "2026-10-13", {"tillatelser": ["ukentlig"]})

    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", daglig / "data" / "arkiv")
    if not merket:
        monkeypatch.setattr(raw_arkiv, "DAGLIG", "")
    svar["eierskap"] = {"tillatelser": ["daglig"]}
    assert ark.main(["--dato", "2026-10-13"]) == 0

    for klone in (samle, daglig):
        _git(klone, "add", "-A", "data")
        _git(klone, "commit", "-q", "-m", klone.name)
    _git(samle, "push", "-q", "origin", "main")
    rebase = _git(daglig, "pull", "-q", "--rebase", "origin", "main", sjekk=False)

    if not merket:
        assert rebase.returncode != 0 and "CONFLICT" in rebase.stdout + rebase.stderr
        return
    assert rebase.returncode == 0, rebase.stderr
    _git(daglig, "push", "-q", "origin", "main")
    filer = sorted(p.name for p in (daglig / "data/arkiv/eierskap").iterdir())
    assert filer == ["2026-10-13.daglig.json.gz", "2026-10-13.daglig.logg.json",
                     "2026-10-13.json.gz"]
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", daglig / "data" / "arkiv")
    assert {json.loads(gzip.open(p).read())["tillatelser"][0]
            for p in raw_arkiv.kropper("eierskap")} == {"ukentlig", "daglig"}
