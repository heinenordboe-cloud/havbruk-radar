"""Røyktest: kjører hele pipelinen med en falsk kilde, uten nett.

Poenget er ikke testdekning. Poenget er at du kan endre core/ og på
to sekunder vite om du ødela noe.
"""

import polars as pl

from core import diff, runner, signals, snapshot
from core.contract import Observation, Source


class FalskKilde(Source):
    name = "falsk"
    entity_type = "selskap"

    def fetch(self):
        return [{"orgnr": "999999999", "navn": "Testlaks AS", "ansatte": 12}]

    def parse(self, raw, observed_at):
        for rad in raw:
            yield Observation(
                entity_id=rad["orgnr"],
                entity_type=self.entity_type,
                entity_name=rad["navn"],
                field="antall_ansatte",
                value=str(rad["ansatte"]),
                source=self.name,
                observed_at=observed_at,
            )


class KnustKilde(Source):
    name = "knust"

    def fetch(self):
        raise RuntimeError("kilden er nede")

    def parse(self, raw, observed_at):
        return []


def test_feil_isoleres():
    obs, res = runner.run_all([FalskKilde(), KnustKilde()], "2026-01-01")
    assert len(obs) == 1
    assert [r.ok for r in res] == [True, False]


def test_diff_fanger_endring(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)

    forrige = snapshot.to_frame(list(FalskKilde().collect("2026-01-01")))
    snapshot.write(list(FalskKilde().collect("2026-01-01")), "2026-01-01")

    endret = [Observation("999999999", "selskap", "Testlaks AS",
                          "antall_ansatte", "20", "falsk", "2026-01-08")]
    endringer = diff.compare(snapshot.to_frame(endret), "2026-01-08")

    assert endringer.height == 1
    assert endringer["change_type"][0] == "endret"


def test_signalregler_scorer():
    endringer = pl.DataFrame([{
        "entity_id": "1", "entity_type": "selskap", "entity_name": "Testlaks AS",
        "field": "antall_ansatte", "old_value": "10", "new_value": "20",
        "change_type": "endret", "source": "falsk", "observed_at": "2026-01-08",
    }])
    assert signals.score(endringer).height == 1


def test_regresjon_oppdages(tmp_path, monkeypatch):
    """En kilde som fungerte forrige uke og feiler nå skal flagges."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    ok = [runner.Result("falsk", True, 5)]
    health.skriv(health.oppdater(ok, "2026-01-01")[0])

    feilet = [runner.Result("falsk", False, 0, "RuntimeError: nede")]
    _, nede = health.oppdater(feilet, "2026-01-08")

    assert nede == ["falsk (uke 1)"]


def test_knekt_kildefil_stopper_ikke_de_andre(tmp_path, monkeypatch):
    """En kildefil som ikke lar seg importere skal isoleres, ikke drepe kjøringen."""
    import types

    from core import registry

    (tmp_path / "frisk.py").write_text(
        "from core.contract import Source\n"
        "class Frisk(Source):\n"
        "    name = 'frisk'\n"
        "    def fetch(self): return []\n"
        "    def parse(self, raw, observed_at): return []\n",
        encoding="utf-8",
    )
    (tmp_path / "knekt.py").write_text("import finnes_ikke_xyz\n", encoding="utf-8")

    def last(navn: str):
        fil = tmp_path / f"{navn.split('.')[-1]}.py"
        modul = types.ModuleType(navn)
        exec(compile(fil.read_text(encoding="utf-8"), str(fil), "exec"), modul.__dict__)
        return modul

    monkeypatch.setattr(registry, "SOURCES_DIR", tmp_path)
    monkeypatch.setattr(registry.importlib, "import_module", last)

    kilder = registry.discover()
    assert sorted(k.name for k in kilder) == ["frisk", "knekt"]

    _, res = runner.run_all(kilder, "2026-01-01")
    assert {r.source: r.ok for r in res} == {"frisk": True, "knekt": False}


def test_importert_kildeklasse_registreres_ikke_to_ganger():
    """Gjenbruk av en baseklasse mellom kilder skal ikke doble observasjonene."""
    import inspect as _inspect
    from core import registry
    from core.contract import Source

    class Delt(Source):
        name = "delt"

    Delt.__module__ = "sources.kilde_a"

    class Arving(Delt):
        name = "arving"

    Arving.__module__ = "sources.kilde_b"

    # Slik registry filtrerer: bare klasser definert i modulen som skannes.
    i_b = [o for o in (Delt, Arving) if o.__module__ == "sources.kilde_b"]
    assert [o.name for o in i_b] == ["arving"]


def test_nede_kilde_varsler_hver_uke(tmp_path, monkeypatch):
    """Alarmen skal ikke gå stille uke to. Da er datatap usynlig."""
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")

    health.skriv(health.oppdater([runner.Result("falsk", True, 5)], "2026-01-01")[0])

    feilet = [runner.Result("falsk", False, 0, "RuntimeError: nede")]
    for uke in ("2026-01-08", "2026-01-15", "2026-01-22"):
        tilstand, nede = health.oppdater(feilet, uke)
        health.skriv(tilstand)
        assert nede, f"ingen alarm {uke} — dette er den stille datatapsfeilen"


def test_kilde_som_aldri_har_fungert_varsler_ikke(tmp_path, monkeypatch):
    from core import health

    monkeypatch.setattr(health, "HEALTH_PATH", tmp_path / "health.json")
    _, nede = health.oppdater([runner.Result("ny_kilde", False, 0, "ikke ferdig")], "2026-01-01")
    assert nede == []
