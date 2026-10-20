"""Publiseringen fra GitHub Actions — det som kan prøves uten å laste opp.

`publiser_ci.py` kaller stegene i `publiser.py`. Prøvene her gjelder det
som er NYTT: summen over byggemappa, sperren for nøklene som mangler, og
bokføringen som prøver pushen på nytt når origin har flyttet seg.
"""

import json
import subprocess
from pathlib import Path

import pytest

import publiser
import publiser_ci
from tests.test_publiser import _datarepo, _pa_origin


# ---- summen over byggemappa ------------------------------------------

def _mappe(rot: Path) -> Path:
    (rot / "lokalitet" / "1").mkdir(parents=True)
    (rot / "index.html").write_text("<p>forside</p>", encoding="utf-8")
    (rot / "lokalitet" / "1" / "index.html").write_text("<p>1</p>",
                                                         encoding="utf-8")
    (rot / "_headers").write_text("/*\n  X: y\n", encoding="utf-8")
    return rot


def test_summen_er_den_samme_for_de_samme_filene(tmp_path):
    """To kopier av samme mappe, skrevet i ulik rekkefølge og til ulik
    tid, er de samme filene. Summen skal ikke vite forskjell."""
    a = _mappe(tmp_path / "a")
    b = tmp_path / "b"
    (b / "lokalitet" / "1").mkdir(parents=True)
    for rel in ("_headers", "lokalitet/1/index.html", "index.html"):
        (b / rel).write_bytes((a / rel).read_bytes())
    assert publiser.mappesum(a) == publiser.mappesum(b)
    assert publiser.mappesum(a)[1:] == (3, sum(
        p.stat().st_size for p in a.rglob("*") if p.is_file()))


@pytest.mark.parametrize("endring", ["innhold", "navn", "ny fil", "borte"])
def test_summen_endres_av_hver_slags_endring(tmp_path, endring):
    """Innhold, navn, en fil til og en fil mindre. En sum over bare
    innholdet ville ikke sett at en fil flyttet seg."""
    m = _mappe(tmp_path / "m")
    for_ = publiser.mappesum(m)[0]
    if endring == "innhold":
        (m / "index.html").write_text("<p>forside!</p>", encoding="utf-8")
    elif endring == "navn":
        (m / "lokalitet" / "1").rename(m / "lokalitet" / "2")
    elif endring == "ny fil":
        (m / "robots.txt").write_text("", encoding="utf-8")
    else:
        (m / "_headers").unlink()
    assert publiser.mappesum(m)[0] != for_


# ---- nøklene -----------------------------------------------------------

@pytest.mark.parametrize("miljo,mangler", [
    ({}, ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"]),
    ({"CLOUDFLARE_API_TOKEN": "t"}, ["CLOUDFLARE_ACCOUNT_ID"]),
    ({"CLOUDFLARE_API_TOKEN": "  ", "CLOUDFLARE_ACCOUNT_ID": "a"},
     ["CLOUDFLARE_API_TOKEN"]),
])
def test_en_manglende_noekkel_navngis(miljo, mangler):
    """`${{ secrets.X }}` på en secret som ikke finnes blir TOM STRENG.
    Wrangler svarer da med en feil som ikke sier hvilken som mangler."""
    with pytest.raises(publiser.Stopp) as e:
        publiser_ci.krev_cloudflare(miljo)
    for navn in mangler:
        assert navn in str(e.value)
    for navn in set(publiser_ci.CLOUDFLARE) - set(mangler):
        assert navn not in str(e.value)


def test_begge_noekler_slipper_gjennom():
    publiser_ci.krev_cloudflare({"CLOUDFLARE_API_TOKEN": "t",
                                 "CLOUDFLARE_ACCOUNT_ID": "a"})


def test_ingen_opplasting_uten_noekler(tmp_path, monkeypatch):
    """Sperren står FØR wrangler kalles, ikke i feilmeldingen etterpå."""
    for n in publiser_ci.CLOUDFLARE:
        monkeypatch.delenv(n, raising=False)
    kalt = []
    monkeypatch.setattr(publiser, "kjor", lambda *a, **k: kalt.append(a))
    with pytest.raises(publiser.Stopp):
        publiser_ci.last_opp(tmp_path, "produksjon")
    assert kalt == []


def test_opplastingen_er_publisers_kommando(tmp_path, monkeypatch):
    """Versjonen og grenen sies ett sted. Se `publiser.WRANGLER`."""
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
    kalt = []
    monkeypatch.setattr(publiser, "kjor", lambda *a, **k: kalt.append(a))
    publiser_ci.last_opp(tmp_path, "forhandsvisning")
    publiser_ci.last_opp(tmp_path, "produksjon")
    assert kalt == [tuple(publiser.wranglerkommando(tmp_path, False)),
                    tuple(publiser.wranglerkommando(tmp_path, True))]
    assert kalt[0][-1] == publiser.FORHANDSGREN
    assert kalt[1][-1] == publiser.PRODUKSJONSGREN


def test_miljoet_maa_vaere_et_av_de_to():
    with pytest.raises(SystemExit):
        publiser_ci.main(["last-opp", ".", "--miljo", "prod"])


# ---- kvitteringen ------------------------------------------------------

def test_kvittering_uten_sum_stopper(tmp_path):
    k = tmp_path / "k.json"
    k.write_text(json.dumps({"kode_commit": "a", "data_commit": "b",
                             "uke": "2026-41", "sha256": ""}),
                 encoding="utf-8")
    with pytest.raises(publiser.Stopp, match="sha256"):
        publiser_ci.les_kvittering(k)


def test_oppsummeringen_baerer_summen_og_ukas_tall():
    k = {"kode_commit": "a" * 40, "data_commit": "b" * 40,
         "uke": "2026-41", "sha256": "c" * 64, "filer": 3, "byte": 1e6}
    tekst = publiser_ci.oppsummering(k, ["  uke 41, 2026", "  12 endringer"])
    assert "c" * 64 in tekst
    assert "  12 endringer" in tekst
    assert "a" * 40 in tekst and "b" * 40 in tekst


def test_byggkommandoen_navngir_ci_skriptet():
    kommando = publiser.byggkommando(av="publiser_ci.py bygg, steg 3")
    assert kommando[-2:] == ["--vakt-kjores-av",
                             "publiser_ci.py bygg, steg 3"]


# ---- bokføringen -------------------------------------------------------

@pytest.fixture
def datarepo(tmp_path, monkeypatch):
    arbeid = _datarepo(tmp_path)
    monkeypatch.setattr(publiser, "DATAREPO", arbeid)
    monkeypatch.setattr(publiser, "LOGG",
                        arbeid / "docs" / "publiseringslogg.tsv")
    return arbeid


def _kom_forst(datarepo: Path) -> None:
    """En annen workflow pusher til datarepoet mens vi bygger."""
    fremmed = datarepo.parent / "fremmed"
    subprocess.run(["git", "clone", str(datarepo.parent / "origin.git"),
                    str(fremmed)], check=True, capture_output=True)
    for n, v in (("user.email", "x@example.invalid"), ("user.name", "X")):
        subprocess.run(["git", "-C", str(fremmed), "config", n, v],
                       check=True, capture_output=True)
    (fremmed / "annet.txt").write_text("i veien\n", encoding="utf-8")
    for args in (["add", "-A"], ["commit", "-m", "kom først"],
                 ["push", "origin", "main"]):
        subprocess.run(["git", "-C", str(fremmed), *args],
                       check=True, capture_output=True)


K = {"kode_commit": "a" * 40, "data_commit": "b" * 40, "uke": "2026-41",
     "sha256": "c" * 64}


def test_avvist_push_proves_igjen_og_linja_havner_paa_origin(datarepo):
    """`publiser.bokfor()` gir opp her, fordi et menneske kan gjøre
    resten. I Actions gjør ingen det."""
    _kom_forst(datarepo)
    assert publiser_ci.logg(K, "forhandsvisning") == ""
    linjer = _pa_origin(datarepo).splitlines()
    assert len(linjer) == 2                    # overskrift + ÉN linje
    assert linjer[1].split("\t")[1:] == ["forhandsvisning", "a" * 40,
                                         "b" * 40, "2026-41", "", ""]


def test_ny_push_skriver_ikke_linja_to_ganger(datarepo):
    publiser_ci.logg(K, "produksjon")
    assert len(_pa_origin(datarepo).splitlines()) == 2


# ---- summen mot kvitteringen (publiser.yml) ---------------------------

def test_lik_sum_slipper_gjennom(tmp_path):
    m = _mappe(tmp_path / "m")
    sha = publiser.mappesum(m)[0]
    assert publiser_ci.sjekk(m, dict(K, sha256=sha)) == sha


def test_avvik_fra_kvitteringen_stopper(tmp_path):
    """Én byte er nok. Mappa som passerte porten er den ENE mappa."""
    m = _mappe(tmp_path / "m")
    k = dict(K, sha256=publiser.mappesum(m)[0])
    (m / "index.html").write_text("<p>forside.</p>", encoding="utf-8")
    with pytest.raises(publiser.Stopp, match="avviker fra kvitteringen"):
        publiser_ci.sjekk(m, k)


def test_ingen_mappe_stopper(tmp_path):
    with pytest.raises(publiser.Stopp, match="finnes ikke"):
        publiser_ci.sjekk(tmp_path / "borte", K)


# ---- automatisk utlegging: de fire vilkårene ---------------------------

KODE, ANNEN = "a" * 40, "f" * 40


def _logg(sti: Path, *linjer: tuple[str, str, str]) -> Path:
    sti.write_text("tidspunkt\tmiljo\tkode_commit\tdata_commit\tuke\n" + "".join(
        f"2026-10-0{i + 1}T12:00:00+00:00\t{m}\t{k}\t{d}\t2026-41\n"
        for i, (m, k, d) in enumerate(linjer)), encoding="utf-8")
    return sti


def test_a_holder_naar_koden_er_den_produksjon_kjorer(tmp_path):
    logg = _logg(tmp_path / "l.tsv", ("produksjon", KODE, "d1"),
                 ("forhandsvisning", ANNEN, "d2"))
    siste = publiser_ci.siste_produksjon(logg)
    assert siste["kode_commit"] == KODE      # forhåndsvisningen teller ikke
    assert publiser_ci.vilkar_kode({"kode_commit": KODE}, siste).holder
    v = publiser_ci.vilkar_kode({"kode_commit": ANNEN}, siste)
    assert not v.holder and "koden er ny" in v.tekst


def test_a_holder_ikke_uten_produksjonslinje(tmp_path):
    logg = _logg(tmp_path / "l.tsv", ("forhandsvisning", KODE, "d1"))
    assert publiser_ci.siste_produksjon(logg) is None
    assert not publiser_ci.vilkar_kode({"kode_commit": KODE}, None).holder
    assert publiser_ci.siste_produksjon(tmp_path / "finnes-ikke.tsv") is None


@pytest.mark.parametrize("port,holder", [
    ({"ukvitterte": 0, "kvitterte": 3}, True),
    ({"ukvitterte": 2, "kvitterte": 0}, False),
    (None, False),                           # kvittering fra før feltet
    ({"kvitterte": 1}, False),
])
def test_b_porten(port, holder):
    k = {} if port is None else {"port": port}
    assert publiser_ci.vilkar_port(k).holder is holder


BAND = {"endringer": {"min": 1, "maks": 282},
        "lokaliteter": {"min": 1743, "maks": 1819}}


@pytest.mark.parametrize("maal,holder", [
    ({"endringer": 61, "lokaliteter": 1780}, True),
    ({"endringer": 1, "lokaliteter": 1743}, True),       # grensene er med
    ({"endringer": 282, "lokaliteter": 1819}, True),
    ({"endringer": 0, "lokaliteter": 1780}, False),
    ({"endringer": 283, "lokaliteter": 1780}, False),
    ({"endringer": 61, "lokaliteter": 1742}, False),
    ({"endringer": 61, "lokaliteter": 1820}, False),
    ({"endringer": 61}, False),
    (None, False),
])
def test_d_baandet(maal, holder):
    k = {} if maal is None else {"maal": maal}
    assert publiser_ci.vilkar_band(k, BAND).holder is holder


def test_d_holder_ikke_uten_baand():
    k = {"maal": {"endringer": 61, "lokaliteter": 1780}}
    assert not publiser_ci.vilkar_band(k, {}).holder


def test_baandet_i_config_er_det_som_er_maalt():
    """Tallene og regelen står i config.yml med målingen. Endres de uten
    at kommentaren følger, er det denne prøven som sier fra."""
    assert publiser_ci.normalbaand() == BAND


class Datarepo:
    """Et git-repo med commits på formen samle.yml og revisjon.yml skriver."""

    def __init__(self, rot: Path):
        self.rot = rot
        subprocess.run(["git", "init", "-q", str(rot)], check=True)
        self.n = 0

    def commit(self, emne: str, dag: str, stier=("data/health.json", "data/raw/a/x.parquet"),
               hvem: str = "havbruk-radar") -> str:
        for sti in stier:
            self.n += 1
            (self.rot / sti).parent.mkdir(parents=True, exist_ok=True)
            (self.rot / sti).write_text(str(self.n))
        tid = f"{dag}T12:00:00+00:00"
        env = {"GIT_AUTHOR_NAME": hvem, "GIT_COMMITTER_NAME": hvem,
               "GIT_AUTHOR_EMAIL": "a@b", "GIT_COMMITTER_EMAIL": "a@b",
               "GIT_AUTHOR_DATE": tid, "GIT_COMMITTER_DATE": tid,
               "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
        subprocess.run(["git", "-C", str(self.rot), "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", str(self.rot), "commit", "-q", "-m", emne],
                       check=True, env=env)
        return subprocess.run(["git", "-C", str(self.rot), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    return Datarepo(tmp_path / "data-repo")


def _c(repo, sha):
    return publiser_ci.vilkar_delvis({"data_commit": sha}, repo.rot)


def test_c_holder_for_en_hel_uke(repo):
    sha = repo.commit("Snapshot 2026-10-12 — 61 endringer", "2026-10-12")
    v = _c(repo, sha)
    assert v.holder, v.tekst


def test_c_holder_ikke_for_en_delvis_uke(repo):
    sha = repo.commit("DELVIS: Snapshot 2026-10-12 — 61 endringer", "2026-10-12")
    assert "DELVIS" in _c(repo, sha).tekst and not _c(repo, sha).holder


def test_c_tirsdagens_health_alene_skjuler_ikke_en_delvis_mandag(repo):
    """dc8b126: health.json alene, mandagens emnelinje, uten merket."""
    repo.commit("DELVIS: Snapshot 2026-10-05", "2026-10-05")
    sha = repo.commit("Snapshot 2026-10-05", "2026-10-06", stier=("data/health.json",))
    v = _c(repo, sha)
    assert not v.holder and "DELVIS: Snapshot 2026-10-05" in v.tekst


def test_c_en_delvis_gjenkjoring_redder_ikke_uka(repo):
    """b3e80ea: tirsdagen skrev et snapshot uten merket, mandagen var DELVIS."""
    repo.commit("DELVIS: Snapshot 2026-09-21", "2026-09-21")
    sha = repo.commit("Snapshot 2026-09-22 — 0 endringer", "2026-09-22")
    assert not _c(repo, sha).holder


def test_c_forrige_uke_teller_ikke(repo):
    repo.commit("DELVIS: Snapshot 2026-10-05", "2026-10-05")
    sha = repo.commit("Snapshot 2026-10-12", "2026-10-12")
    assert _c(repo, sha).holder


def test_c_revisjonen_og_arkivene_er_ikke_innsamlingen(repo):
    repo.commit("Snapshot 2026-10-12", "2026-10-12")
    repo.commit("Revisjon biomasse 2026-10-22: 1 måneder REVIDERT", "2026-10-22",
                stier=("data/raw/biomasse/2026-07-31.2.parquet",))
    sha = repo.commit("Auksjonsarkiv 2026-10-23", "2026-10-23",
                      stier=("data/arkiv/auksjon/x.logg.json",))
    v = _c(repo, sha)
    assert v.holder and "Snapshot 2026-10-12" in v.tekst


def test_c_et_snapshot_skrevet_av_et_menneske_sier_ikke_om_uka_er_hel(repo):
    sha = repo.commit("Snapshot for hånd", "2026-10-12", hvem="Heine Nordboe")
    v = _c(repo, sha)
    assert not v.holder and "Heine Nordboe" in v.tekst


def test_c_data_commit_avgjor_hva_som_er_med(repo):
    """En DELVIS-commit ETTER datacommiten er ikke i bygget."""
    sha = repo.commit("Snapshot 2026-10-12", "2026-10-12")
    repo.commit("DELVIS: Snapshot 2026-10-13", "2026-10-13")
    assert _c(repo, sha).holder


def test_c_holder_ikke_uten_innsamling_eller_lesbar_historikk(repo, tmp_path):
    sha = repo.commit("Auksjonsarkiv", "2026-10-12", stier=("data/arkiv/a/x",))
    assert not _c(repo, sha).holder
    v = publiser_ci.vilkar_delvis({"data_commit": "0" * 40}, repo.rot)
    assert not v.holder and "kunne ikke leses" in v.tekst


def _hel_kvittering(repo, logg_dir: Path) -> Path:
    sha = repo.commit("Snapshot 2026-10-12", "2026-10-12")
    (repo.rot / "docs").mkdir(exist_ok=True)
    _logg(repo.rot / "docs" / "publiseringslogg.tsv", ("produksjon", KODE, "d0"))
    k = logg_dir / "kvittering.json"
    k.write_text(json.dumps({
        "kode_commit": KODE, "data_commit": sha, "uke": "2026-42", "sha256": "s",
        "port": {"ukvitterte": 0, "kvitterte": 0},
        "maal": {"endringer": 61, "lokaliteter": 1780}}), encoding="utf-8")
    return k


def test_alle_fire_holder_og_doera_er_aapen(repo, tmp_path, monkeypatch):
    k = _hel_kvittering(repo, tmp_path)
    ut = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(ut))
    monkeypatch.setattr(publiser_ci, "normalbaand", lambda: BAND)
    rapport = tmp_path / "rapport.md"
    assert publiser_ci.main(["automatisk", "--kvittering", str(k),
                             "--datarepo", str(repo.rot), "--rapport", str(rapport)]) == 0
    assert ut.read_text() == "apen=ja\n"
    assert rapport.read_text().count("✓") == 4


@pytest.mark.parametrize("vilkar", ["a", "b", "c", "d"])
def test_ett_vilkar_som_ikke_holder_lukker_doera(repo, tmp_path, monkeypatch, vilkar):
    k = _hel_kvittering(repo, tmp_path)
    kv = json.loads(k.read_text())
    if vilkar == "a":
        kv["kode_commit"] = ANNEN
    elif vilkar == "b":
        del kv["port"]
    elif vilkar == "c":
        kv["data_commit"] = repo.commit("DELVIS: Snapshot 2026-10-12", "2026-10-12")
    else:
        kv["maal"]["endringer"] = 5000
    k.write_text(json.dumps(kv))
    ut = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(ut))
    monkeypatch.setattr(publiser_ci, "normalbaand", lambda: BAND)
    rapport = tmp_path / "rapport.md"
    publiser_ci.main(["automatisk", "--kvittering", str(k),
                      "--datarepo", str(repo.rot), "--rapport", str(rapport)])
    assert ut.read_text() == "apen=nei\n"
    [linje] = [l for l in rapport.read_text().splitlines() if "✗" in l]
    assert f"**{vilkar} " in linje


def test_kvitteringen_baerer_porten_og_ukas_tall(tmp_path, monkeypatch):
    """Det publiser.yml leser vilkår b og d av, skrives av bygget."""
    monkeypatch.setattr(publiser, "krev_sporbar", lambda *a: "c" * 40)
    monkeypatch.setattr(publiser, "kjor", lambda *a, **k: None)
    monkeypatch.setattr(publiser, "UT", tmp_path)
    monkeypatch.setattr(publiser, "port", lambda ut, produksjon: (["rent"], 2))
    monkeypatch.setattr(publiser, "ukas_maal", lambda: (
        "2026-42", ["  61 endringer"], {"endringer": 61, "lokaliteter": 1780}))
    monkeypatch.setattr(publiser, "krev_sokeindeks", lambda ut, produksjon: [])
    monkeypatch.setattr(publiser, "mappesum", lambda ut: ("s" * 64, 3, 10))
    k = publiser_ci.bygg(tmp_path / "k" / "kvittering.json")
    assert k["port"] == {"ukvitterte": 0, "kvitterte": 2}
    assert k["maal"] == {"endringer": 61, "lokaliteter": 1780}
    assert json.loads((tmp_path / "k" / "kvittering.json").read_text())["maal"] == k["maal"]


# ---- tilbakerulling via Cloudflare Pages ------------------------------

GOD, GAMMEL = "ea2f3923-4130-49b7-814e-07cd2c6f7dd5", \
    "6c147962-4339-4f08-8bb5-c05b2cfa8ff1"
FELT = "\t".join(publiser.LOGGFELT)


def _logg7(sti: Path, *linjer: tuple[str, ...]) -> Path:
    """(tidspunkt, miljo, kode, data, uke, deployment_id, kilde)."""
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text(FELT + "\n" + "".join("\t".join(l) + "\n" for l in linjer),
                   encoding="utf-8")
    return sti


def _for_og_etter_tilbakerulling(sti: Path, tilbake_kode: str) -> Path:
    """W ute 13.10, X ut 19.10, så rullet tilbake til W 20.10."""
    return _logg7(
        sti,
        ("2026-10-13T22:06:52+00:00", "produksjon", "w" * 40, "d1", "2026-42",
         GAMMEL, "etterfylt"),
        ("2026-10-19T10:45:14+00:00", "produksjon", "x" * 40, "d2", "2026-43",
         GOD, "wrangler"),
        ("2026-10-20T09:00:00+00:00", "forhandsvisning", "x" * 40, "d3",
         "2026-43", "", ""),
        ("2026-10-20T10:00:00+00:00", "tilbakerulling", tilbake_kode, "d1",
         "2026-42", GAMMEL, "tilbakerulling"))


def test_a_etter_tilbakerulling_slipper_ikke_ut_koden_som_ble_rullet_bort(tmp_path):
    """Mandagen etter: main har fortsatt koden X, produksjon kjører W.
    Siste PRODUKSJONSlinje sier X — leste vilkår a den, holdt det."""
    logg = _for_og_etter_tilbakerulling(tmp_path / "l.tsv", "w" * 40)
    siste = publiser_ci.siste_produksjon(logg)
    assert siste["miljo"] == "tilbakerulling"
    v = publiser_ci.vilkar_kode({"kode_commit": "x" * 40}, siste)
    assert not v.holder
    assert "produksjon kjører wwwwwwwwwwww" in v.tekst
    assert "tilbakerullet til 6c147962" in v.tekst


def test_a_etter_tilbakerulling_stopper_ikke_samme_kode(tmp_path):
    """Rullet tilbake for DATA, med samme kode: neste databygg med den
    koden skal kunne gå ut, som før tilbakerullingen."""
    logg = _for_og_etter_tilbakerulling(tmp_path / "l.tsv", "w" * 40)
    v = publiser_ci.vilkar_kode({"kode_commit": "w" * 40},
                                publiser_ci.siste_produksjon(logg))
    assert v.holder, v.tekst


def test_a_etter_tilbakerulling_til_ukjent_kode_holder_ikke(tmp_path):
    """Målutrullingen fantes ikke i loggen: kode_commit er tom. «Vet ikke»
    holder aldri — heller ikke for en kvittering som også mangler den."""
    logg = _for_og_etter_tilbakerulling(tmp_path / "l.tsv", "")
    siste = publiser_ci.siste_produksjon(logg)
    for kode in ("x" * 40, "w" * 40, ""):
        v = publiser_ci.vilkar_kode({"kode_commit": kode}, siste)
        assert not v.holder and "vet ikke hvilken kode" in v.tekst


def test_a_leser_fortsatt_en_logg_med_fem_kolonner(tmp_path):
    """Loggen fra før 20.10.2026 har ingen deployment-kolonner."""
    logg = _logg(tmp_path / "l.tsv", ("produksjon", KODE, "d1"))
    assert publiser_ci.vilkar_kode({"kode_commit": KODE},
                                   publiser_ci.siste_produksjon(logg)).holder


class Cloudflare:
    """Pages-API-et slik prøven 20.10.2026 viste det: rollback flytter
    `canonical_deployment`, ikke `latest_deployment`."""

    def __init__(self, ute: str, utrullinger: dict, flytter: bool = True):
        self.ute, self.utr, self.flytter, self.kall = ute, utrullinger, flytter, []

    def __call__(self, metode, sti):
        self.kall.append((metode, sti))
        if (metode, sti) == ("GET", ""):
            return {"result": {"canonical_deployment": {"id": self.ute}}}
        id_ = sti.split("/")[2]
        if metode == "GET":
            return {"result": self.utr[id_]}
        assert sti.endswith("/rollback")
        if self.flytter:
            self.ute = id_
        return {"result": self.utr[id_]}


def _utr(miljo="production", status="success"):
    return {"environment": miljo, "latest_stage": {"status": status},
            "url": "https://6c147962.kystloggen.pages.dev"}


def test_tilbakerulling_spor_cloudflare_om_maalet_er_ute():
    cf = Cloudflare(GOD, {GAMMEL: _utr()})
    u = publiser_ci.tilbakerull(GAMMEL, kall=cf, pause=0)
    assert u["url"].startswith("https://6c147962.")
    assert ("POST", f"/deployments/{GAMMEL}/rollback") in cf.kall
    assert cf.kall[-1] == ("GET", "")          # siste ord er canonical


def test_rollback_som_svarte_men_ikke_flyttet_noe_stopper():
    """200 fra rollback er en bestilling, ikke et resultat (1b-2)."""
    cf = Cloudflare(GOD, {GAMMEL: _utr()}, flytter=False)
    with pytest.raises(publiser.Stopp, match=f"{GOD} er i produksjon, ikke {GAMMEL}"):
        publiser_ci.tilbakerull(GAMMEL, kall=cf, forsok=2, pause=0)


@pytest.mark.parametrize("maal,utr,grunn", [
    ("ikke-en-id", {}, "ikke en deployment_id"),
    (GAMMEL, {GAMMEL: _utr(miljo="preview")}, "'preview'-utrulling"),
    (GAMMEL, {GAMMEL: _utr(status="failure")}, "status 'failure'"),
])
def test_ingen_rollback_naar_maalet_ikke_kan_settes_tilbake(maal, utr, grunn):
    cf = Cloudflare(GOD, utr)
    with pytest.raises(publiser.Stopp, match=grunn):
        publiser_ci.tilbakerull(maal, kall=cf, pause=0)
    assert not [k for k in cf.kall if k[0] == "POST"]


def test_maalet_som_allerede_er_ute_faar_ingen_rollback():
    cf = Cloudflare(GAMMEL, {GAMMEL: _utr()})
    publiser_ci.tilbakerull(GAMMEL, kall=cf, pause=0)
    assert not [k for k in cf.kall if k[0] == "POST"]


def test_tilbakerullingslinja_baerer_maalets_kode_data_og_uke(datarepo):
    _for_og_etter_tilbakerulling(publiser.LOGG, "w" * 40)
    for args in (["add", "-A"], ["commit", "-qm", "logg"], ["push", "-q"]):
        subprocess.run(["git", "-C", str(datarepo), *args], check=True,
                       capture_output=True)
    assert publiser_ci.logg_tilbakerulling(GOD) == ""
    siste = publiser.les_logg(publiser.LOGG)[-1]
    assert (siste["miljo"], siste["kode_commit"], siste["data_commit"],
            siste["uke"], siste["deployment_id"], siste["deployment_kilde"]) == \
        ("tilbakerulling", "x" * 40, "d2", "2026-43", GOD, "tilbakerulling")
    assert _pa_origin(datarepo).rstrip("\n").splitlines()[-1].split("\t")[1:] == \
        ["tilbakerulling", "x" * 40, "d2", "2026-43", GOD, "tilbakerulling"]


def test_tilbakerulling_til_en_id_loggen_ikke_kjenner(datarepo):
    """Kode og uke står tomme — og vilkår a holder da ikke."""
    assert publiser_ci.logg_tilbakerulling(GAMMEL) == ""
    siste = publiser_ci.siste_produksjon(publiser.LOGG)
    assert (siste["kode_commit"], siste["deployment_id"]) == ("", GAMMEL)
    assert not publiser_ci.vilkar_kode({"kode_commit": KODE}, siste).holder


def test_logg_tar_deployment_id_fra_miljoet(datarepo, tmp_path, monkeypatch):
    """publiser.yml gir id-en som DEPLOYMENT_ID, ikke som flagg: koden som
    kjører er bygget sin, og en eldre kode ville stoppet på et ukjent
    argument etter at siden er ute."""
    k = tmp_path / "k.json"
    k.write_text(json.dumps(K))
    monkeypatch.setenv("DEPLOYMENT_ID", GOD)
    assert publiser_ci.main(["logg", "--kvittering", str(k),
                             "--miljo", "produksjon"]) == 0
    monkeypatch.setenv("DEPLOYMENT_ID", "tull")
    assert publiser_ci.main(["logg", "--kvittering", str(k),
                             "--miljo", "produksjon"]) == 0
    rader = publiser.les_logg(publiser.LOGG)
    assert [(r["deployment_id"], r["deployment_kilde"]) for r in rader] == \
        [(GOD, "wrangler"), ("", "")]


def test_last_opp_gir_id_en_videre(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
    ut = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(ut))
    monkeypatch.setattr(publiser, "last_opp", lambda m, p: (GOD, ""))
    assert publiser_ci.last_opp(tmp_path, "produksjon") == GOD
    assert ut.read_text() == f"deployment_id={GOD}\n"


def test_i_produksjon_krev_stopper_paa_feil_utrulling(tmp_path, monkeypatch):
    """Røyktesten etter en tilbakerulling spør Cloudflare først."""
    cf = Cloudflare(GOD, {})
    monkeypatch.setattr(publiser_ci, "cloudflare", cf)
    monkeypatch.setattr(publiser_ci.time, "sleep", lambda s: None)
    logg = _for_og_etter_tilbakerulling(tmp_path / "l.tsv", "w" * 40)
    ut = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(ut))
    publiser_ci.main(["i-produksjon", "--krev", GOD, "--logg", str(logg)])
    assert ut.read_text().splitlines() == [f"deployment_id={GOD}",
                                           "opprettet=", "uke=2026-43"]
    with pytest.raises(publiser.Stopp, match=f"ikke {GAMMEL}"):
        publiser_ci.main(["i-produksjon", "--krev", GAMMEL])
