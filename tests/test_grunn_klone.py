"""Porten og en GRUNN klone av kodrepoet — ekte git, ikke en attrapp.

MÅLT 07.10.2026: bygg.yml hentet kodrepoet med `fetch-depth: 1`, og
porten meldte 15 snapshots som skrevet av kode som «ikke finnes på
origin/main». Alle 15 commitene fantes der; det var klonen som manglet
historikken bak HEAD. En full klone ga 0 funn.

Spørsmålet her er ikke om vi kaller git slik vi tror, men hva git
svarer i de to klonene. Derfor ekte repoer: et origin med tre commits,
én full klone og én grunn.

To krav:
  * I en FULL klone er en eldre commit på origin/main pushet.
  * I en GRUNN klone kan det ikke avgjøres — og da skal porten si at
    HISTORIKKEN MANGLER, ikke at commiten ikke finnes.
"""

import subprocess
from pathlib import Path

import pytest

import publiseringsvakt as vakt
from core import kodeproveniens as kp
from tests.test_publiseringsvakt import _kodefil

# Den ekte funksjonen; conftest stubber den ut for alle andre prøver.
_ekte = kp.paa_origin_main.__wrapped__


def _git(mappe: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(mappe), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture(scope="module")
def repoer(tmp_path_factory):
    rot = tmp_path_factory.mktemp("kodrepo")
    origin = rot / "origin.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch", "main",
                    str(origin)], check=True, capture_output=True)
    arbeid = rot / "arbeid"
    subprocess.run(["git", "clone", str(origin), str(arbeid)],
                   check=True, capture_output=True)
    for n, v in (("user.email", "t@example.invalid"), ("user.name", "T"),
                 ("commit.gpgsign", "false")):
        _git(arbeid, "config", n, v)
    shaer = []
    for i in range(3):
        (arbeid / "fil.txt").write_text(f"{i}\n", encoding="utf-8")
        _git(arbeid, "add", "-A")
        _git(arbeid, "commit", "-m", f"c{i}")
        shaer.append(_git(arbeid, "rev-parse", "HEAD"))
    _git(arbeid, "push", "origin", "main")

    full = rot / "full"
    grunn = rot / "grunn"
    # file:// og ikke en sti: git ignorerer --depth for lokale stier.
    subprocess.run(["git", "clone", f"file://{origin}", str(full)],
                   check=True, capture_output=True)
    subprocess.run(["git", "clone", "--depth", "1", f"file://{origin}",
                    str(grunn)], check=True, capture_output=True)
    assert _git(grunn, "rev-parse", "--is-shallow-repository") == "true"
    assert _git(full, "rev-parse", "--is-shallow-repository") == "false"
    return {"full": full, "grunn": grunn, "shaer": shaer}


@pytest.fixture
def i_klone(monkeypatch):
    """Pek kodeproveniens på en klone, med den ekte `paa_origin_main`."""
    def sett(mappe: Path):
        monkeypatch.setattr(kp, "ROT", mappe)
        monkeypatch.setattr(kp, "paa_origin_main", _ekte)
        kp._fjern_main.cache_clear()
    yield sett
    # Kan være byttet ut av prøven selv; monkeypatch rydder etter denne.
    getattr(kp._fjern_main, "cache_clear", lambda: None)()


def test_eldre_commit_er_pushet_i_full_klone(repoer, i_klone):
    i_klone(repoer["full"])
    pushet, hvordan = kp.paa_origin_main(repoer["shaer"][0])
    assert pushet is True, hvordan


def test_eldre_commit_kan_ikke_avgjores_i_grunn_klone(repoer, i_klone):
    """Det gamle svaret var `False` — «finnes ikke på origin/main» — om
    en commit som finnes der."""
    i_klone(repoer["grunn"])
    pushet, hvordan = kp.paa_origin_main(repoer["shaer"][0])
    assert pushet is None
    assert "historikken mangler" in hvordan
    assert "grunn" in hvordan


def test_head_avgjores_ogsaa_i_grunn_klone(repoer, i_klone):
    """HEAD er origin/main i CI, og det krever ingen historikk. Det er
    det innsamlingen spør om, og det skal fortsatt svare ja."""
    i_klone(repoer["grunn"])
    assert kp.paa_origin_main(repoer["shaer"][-1])[0] is True


def test_upushet_commit_er_nei_i_full_klone(repoer, i_klone, tmp_path):
    """En full klone som svarer nei, svarer nei — F15 skal fortsatt
    hete F15."""
    i_klone(repoer["full"])
    pushet, hvordan = kp.paa_origin_main("0123456789" * 4)
    assert pushet is False
    assert "historikken mangler" not in hvordan


@pytest.mark.parametrize("klone,ventet,ikke", [
    ("full", None, None),
    ("grunn", "historikken mangler", "finnes ikke"),
])
def test_porten_sier_hva_den_vet(repoer, i_klone, tmp_path, monkeypatch,
                                 klone, ventet, ikke):
    """Samme snapshot, samme origin. Den fulle klonen gir ingen funn; den
    grunne gir ett funn som sier at historikken mangler."""
    monkeypatch.setattr(vakt, "RAW_DIR", tmp_path)
    monkeypatch.setattr(vakt.snapshot, "RAW_DIR", tmp_path)
    _kodefil(tmp_path, "falsk", "2026-09-22.parquet",
             kode_commit=repoer["shaer"][0], kode_rent="ja")
    i_klone(repoer[klone])

    funn = vakt.kodeproveniensfunn()
    if ventet is None:
        assert funn == []
    else:
        [f] = funn
        assert ventet in f.utdrag and ikke not in f.utdrag, f.utdrag


def test_innsamlingens_sperre_sier_det_samme(repoer, i_klone, monkeypatch):
    """`krev_sporbar()` stopper fortsatt — en kjøring som ikke kan gjøre
    rede for koden sin skal ikke skrive — men sier hvorfor."""
    i_klone(repoer["grunn"])
    monkeypatch.setattr(kp, "commit", lambda: repoer["shaer"][0])
    with pytest.raises(kp.IkkeSporbar, match="historikken mangler") as e:
        kp.krev_sporbar()
    assert "Push først" not in str(e.value)


def test_full_klone_som_ikke_har_hentet_origin_main(repoer, i_klone,
                                                    monkeypatch):
    """MÅLT 07.10.2026: en full klone laget før tre nye pusher ga 15
    «finnes ikke». Fjernlagerets origin/main fantes ikke i klonen, og
    git svarte nei av samme grunn som i den grunne: den manglet det den
    skulle sammenligne med."""
    i_klone(repoer["full"])
    monkeypatch.setattr(kp, "_fjern_main", lambda: "f" * 40)
    pushet, hvordan = kp.paa_origin_main(repoer["shaer"][0])
    assert pushet is None
    assert "er ikke hentet i denne klonen" in hvordan
    assert "finnes ikke" not in hvordan
