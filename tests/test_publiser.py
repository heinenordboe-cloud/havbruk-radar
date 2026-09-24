"""Publiseringsskriptet — prøvene som ikke kan tas i etterkant.

Steg 5 kan ikke prøves her: den laster opp noe. Det som KAN prøves er
stegene som avgjør om den skal få gjøre det, og steg 6, som rydder opp
etter den. De to første er begge skrevet etter en observert feil:

  * **Søkeindeksen.** `nettsted.py` bygger siden ferdig også når
    pagefind-binæren mangler — `/sok/` skrives, veiviseren virker, og
    byggerapporten skriver `søkeindeks IKKE BYGGET`. Leses ikke den
    linja av et menneske, går siden ut med et søkefelt som tar imot
    tastetrykk og svarer ingenting. Produksjon nektes derfor; en
    forhåndsvisning advares, fordi den ses av den som ba om den.

  * **Meldingen fra byggesteget.** `publiser.py` sendte `--uten-vakt` i
    steg 2, og bygget skrev «Siden skal ikke publiseres» midt i
    skriptet som var i ferd med å publisere den etter en ren port i steg
    3. Prøven her binder de to filene sammen: kommandoen steg 2 kjører
    skal gi en melding som navngir porten, ikke en som nekter.

Prøven på søket måler FILENE, ikke byggerapporten — se
`publiser.sokeindeks()`. Derfor kan den kjøres uten å bygge noe.

De to gruppene nederst kom til 23.09.2026, og har ingen observert feil
bak seg — de er to hull som ble sett før de rakk å bli en:

  * **`--produksjon` med `--uten-bygg`.** Da lastes en mappa opp som
    dette skriptet ikke bygget, og søkeindeksen under `pagefind/` kan
    være fra et helt annet bygg. Prøven i steg 4 ville ikke sagt fra:
    den spør om det FINNES en indeks. Flaggene utelukker hverandre.

  * **Bokføringen i steg 6.** Logglinja ble skrevet og latt ligge
    ucommitet, og et urent datarepo stopper NESTE publisering i steg 1.
    Prøvene her kjører ekte git mot en ekte origin, fordi spørsmålet
    ikke er om vi kaller det vi tror vi kaller, men om linja havner på
    `origin/main`.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import nettsted
import publiser


ROT = Path(__file__).resolve().parent.parent


# ---- søkeindeksen -----------------------------------------------------

def _skriv_indeks(ut: Path, sider: int = 2, utdrag: int = 2,
                  modul: bool = True) -> Path:
    """En pagefind-katalog med de filene prøven ser etter.

    Tallene settes fra hverandre med vilje i én av testene: sider og
    utdrag som IKKE stemmer er porten sitt funn (`ugranska`), ikke
    dette skriptets.
    """
    pf = ut / "pagefind"
    (pf / "fragment").mkdir(parents=True, exist_ok=True)
    (pf / "pagefind-entry.json").write_text(json.dumps(
        {"version": "1.4.0",
         "languages": {"nb": {"hash": "nb_0", "wasm": "nb",
                              "page_count": sider}}}), encoding="utf-8")
    for i in range(utdrag):
        (pf / "fragment" / f"nb_{i}.pf_fragment").write_bytes(b"x")
    if modul:
        (pf / "pagefind.js").write_text("export {}", encoding="utf-8")
    return pf


def test_uten_pagefind_katalog_er_soket_borte(tmp_path):
    mangel, linje = publiser.sokeindeks(tmp_path)
    assert "ikke bygget" in mangel
    assert linje == "søkeindeks: 0 sider, 0 tekstutdrag"


def test_entry_uten_tekstutdrag_er_ogsaa_borte(tmp_path):
    """En indeks som oppgir sider, men ikke har utdrag, svarer ingenting."""
    _skriv_indeks(tmp_path, sider=2, utdrag=0)
    mangel, _ = publiser.sokeindeks(tmp_path)
    assert "ikke bygget" in mangel


def test_modulen_nettleseren_laster_maa_vaere_der(tmp_path):
    """2349 tekstutdrag hjelper ikke om `pagefind.js` er slettet."""
    _skriv_indeks(tmp_path, modul=False)
    mangel, _ = publiser.sokeindeks(tmp_path)
    assert publiser.SOKEMODUL in mangel


def test_hel_indeks_gir_ingen_mangel(tmp_path):
    _skriv_indeks(tmp_path, sider=3, utdrag=3)
    mangel, linje = publiser.sokeindeks(tmp_path)
    assert mangel == ""
    assert linje == "søkeindeks: 3 sider, 3 tekstutdrag"


def test_produksjon_nektes_uten_soek(tmp_path):
    with pytest.raises(publiser.Stopp) as feil:
        publiser.krev_sokeindeks(tmp_path, produksjon=True)
    assert "Ingenting er lastet opp" in str(feil.value)


def test_forhandsvisning_advarer_og_gaar_videre(tmp_path):
    """Ingen `Stopp`. Advarselen skal stå, og nevne at produksjon nektes."""
    linjer = publiser.krev_sokeindeks(tmp_path, produksjon=False)
    tekst = "\n".join(linjer)
    assert "ADVARSEL" in tekst
    assert "Produksjon nektes" in tekst


def test_produksjon_gaar_gjennom_med_hel_indeks(tmp_path):
    _skriv_indeks(tmp_path, sider=4, utdrag=4)
    linjer = publiser.krev_sokeindeks(tmp_path, produksjon=True)
    assert linjer == ["  søkeindeks: 4 sider, 4 tekstutdrag"]


def test_sprik_mellom_sider_og_utdrag_eies_av_porten(tmp_path):
    """Her stoppes det ikke — funnet er portens, og det er ikke det samme.

    `sider != utdrag` betyr at ordtabellene kan være bygget av noe ingen
    har gransket, og det er `publiseringsvakt.gransk()` som melder det som
    `ugranska` i steg 3. Ville dette skriptet også stoppet på det, hadde
    to steder svart på samme spørsmål — og da kan de svare ulikt.
    """
    _skriv_indeks(tmp_path, sider=5, utdrag=2)
    mangel, linje = publiser.sokeindeks(tmp_path)
    assert mangel == ""
    assert linje == "søkeindeks: 5 sider, 2 tekstutdrag"


# ---- meldingen fra byggesteget ---------------------------------------

def test_bygget_alene_sier_fortsatt_at_siden_ikke_skal_publiseres():
    assert nettsted.vaktmelding("") == (
        "\nVAKTEN ER HOPPET OVER. Siden skal ikke publiseres.")


def test_byggkommandoen_navngir_den_som_kjorer_porten():
    """Den observerte feilen, prøvd på tvers av de to filene."""
    kommando = publiser.byggkommando()
    assert "--uten-vakt" not in kommando
    hvem = kommando[kommando.index("--vakt-kjores-av") + 1]
    melding = nettsted.vaktmelding(hvem)

    assert "skal ikke publiseres" not in melding
    assert "publiser.py" in melding
    assert f"steg {publiser.PORTSTEG}" in melding


def test_portsteget_er_steget_porten_faktisk_kjorer_i():
    """Ett tall, to steder som sier det. Dette er det andre stedet.

    Sier meldingen «steg 3» mens overskriften over porten sier noe annet,
    er den like villedende som den var da den sa «skal ikke publiseres».
    """
    kilde = (ROT / "publiser.py").read_text(encoding="utf-8")
    assert f'print(f"\\n[{{PORTSTEG}}/6] publiseringsvakten")' in kilde
    assert "[3/6]" not in kilde


def test_nettsted_godtar_flagget_og_bare_ett_av_de_to():
    """Kjørt som kommando: argparse er en del av kontrakten her.

    `--help` bygger ingenting. Kjøringen med begge flagg skal feile — de
    betyr motsatte ting, og et bygg der begge sto ville ikke hatt noe
    entydig svar på hvem som gransker mappa.
    """
    hjelp = subprocess.run([sys.executable, "nettsted.py", "--help"],
                           cwd=ROT, capture_output=True, text=True)
    assert hjelp.returncode == 0
    assert "--vakt-kjores-av" in hjelp.stdout

    begge = subprocess.run(
        [sys.executable, "nettsted.py", "--uten-vakt",
         "--vakt-kjores-av", "publiser.py steg 3"],
        cwd=ROT, capture_output=True, text=True)
    assert begge.returncode != 0
    assert "not allowed with" in begge.stderr


# ---- utelukkelsen mellom --produksjon og --uten-bygg -----------------

def _publiser(*flagg: str) -> subprocess.CompletedProcess:
    """Kjør skriptet som kommando. `parse_args()` står først i `main()`,
    så en kjøring som feiler i argparse har ikke rørt noe repo."""
    return subprocess.run([sys.executable, "publiser.py", *flagg],
                          cwd=ROT, capture_output=True, text=True)


def test_produksjon_og_uten_bygg_utelukker_hverandre():
    """Produksjon bygger alltid, så indeksen hører til sidene som går ut.

    Uten denne kan `--uten-bygg --produksjon` legge ut en mappe der
    `pagefind/` er igjen fra et tidligere bygg. Prøven i steg 4 spør om
    det FINNES en indeks, ikke om den er over disse sidene — se
    `publiser.sokeindeks()`, som måler det.
    """
    begge = _publiser("--produksjon", "--uten-bygg")
    assert begge.returncode != 0
    assert "not allowed with" in begge.stderr


def test_hvert_flagg_staar_alene_i_hjelpen():
    hjelp = _publiser("--help")
    assert hjelp.returncode == 0
    assert "--produksjon" in hjelp.stdout
    assert "--uten-bygg" in hjelp.stdout


# ---- bokføringen av logglinja ---------------------------------------

def _datarepo(tmp_path: Path) -> Path:
    """Et datarepo med en origin å pushe til. Ekte git, ikke en attrapp.

    Bokføringen er tre git-kall i rekkefølge mot et repo med en
    fjernkopi. En attrapp ville prøvd at vi kaller det vi tror vi
    kaller — og det er ikke det samme som at linja havner på
    `origin/main`. CLAUDE.md regel 6.
    """
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch", "main",
                    str(origin)], check=True, capture_output=True)
    arbeid = tmp_path / "data"
    subprocess.run(["git", "clone", str(origin), str(arbeid)],
                   check=True, capture_output=True)
    for n, v in (("user.email", "test@example.invalid"),
                 ("user.name", "Test"), ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", str(arbeid), "config", n, v],
                       check=True, capture_output=True)
    (arbeid / "README.md").write_text("data\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(arbeid), "add", "-A"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(arbeid), "commit", "-m", "start"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(arbeid), "push", "-u", "origin", "main"],
                   check=True, capture_output=True)
    return arbeid


@pytest.fixture
def datarepo(tmp_path, monkeypatch):
    arbeid = _datarepo(tmp_path)
    logg = arbeid / "docs" / "publiseringslogg.tsv"
    monkeypatch.setattr(publiser, "DATAREPO", arbeid)
    monkeypatch.setattr(publiser, "LOGG", logg)
    return arbeid


def _pa_origin(arbeid: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(arbeid), "show", "origin/main:docs/"
         "publiseringslogg.tsv"], capture_output=True, text=True).stdout


def test_logglinja_havner_paa_origin_og_treet_blir_rent(datarepo):
    """Prøven er ikke at vi commitet — den er at NESTE steg 1 går."""
    problem, gjenstaar = publiser.bokfor("a" * 40, "b" * 40,
                                         "produksjon", "2026-39")
    assert (problem, gjenstaar) == ("", [])

    urent = subprocess.run(["git", "-C", str(datarepo), "status",
                            "--porcelain"], capture_output=True, text=True)
    assert urent.stdout == ""

    subprocess.run(["git", "-C", str(datarepo), "fetch", "--quiet", "origin"],
                   check=True, capture_output=True)
    upushet = subprocess.run(
        ["git", "-C", str(datarepo), "log", "origin/main..HEAD", "--oneline"],
        capture_output=True, text=True)
    assert upushet.stdout == ""

    innhold = _pa_origin(datarepo)
    assert innhold.startswith("tidspunkt\tmiljo\t")
    assert f"\tproduksjon\t{'a' * 40}\t{'b' * 40}\t2026-39\n" in innhold


def test_commitmeldingen_navngir_miljo_og_begge_commitene(datarepo):
    publiser.bokfor("a" * 40, "b" * 40, "forhandsvisning", "2026-39")
    tittel = subprocess.run(
        ["git", "-C", str(datarepo), "log", "-1", "--format=%s"],
        capture_output=True, text=True).stdout.strip()
    assert tittel == publiser.loggmelding("a" * 40, "b" * 40,
                                          "forhandsvisning")
    assert "forhandsvisning" in tittel
    assert "a" * 12 in tittel and "b" * 12 in tittel


def test_bokforingen_rorer_ingen_andre_filer(datarepo):
    """Den ene fila, og bare den — også når noe annet ligger i treet.

    Steg 1 har krevd et rent tre, så dette skal ikke kunne skje. «Skal
    ikke» er ikke «kan ikke», og en publisering skal ikke kunne dra en
    halvferdig endring i datarepoet med seg på lasset.
    """
    (datarepo / "README.md").write_text("rotet til\n", encoding="utf-8")
    (datarepo / "nyfil.txt").write_text("ubedt\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(datarepo), "add", "-A"],
                   check=True, capture_output=True)

    problem, _ = publiser.bokfor("a" * 40, "b" * 40, "produksjon", "2026-39")
    assert problem == ""

    rort = subprocess.run(
        ["git", "-C", str(datarepo), "show", "--name-only", "--format=",
         "HEAD"], capture_output=True, text=True).stdout.split()
    assert rort == ["docs/publiseringslogg.tsv"]
    assert "data\n" == subprocess.run(
        ["git", "-C", str(datarepo), "show", "HEAD:README.md"],
        capture_output=True, text=True).stdout


def test_linja_legges_til_og_skrives_ikke_om(datarepo):
    """Append-only, som alt annet i datarepoet. CLAUDE.md regel 2."""
    publiser.bokfor("a" * 40, "b" * 40, "forhandsvisning", "2026-38")
    publiser.bokfor("c" * 40, "d" * 40, "produksjon", "2026-39")
    linjer = _pa_origin(datarepo).strip().splitlines()
    assert len(linjer) == 3
    assert linjer[1].split("\t")[1:] == ["forhandsvisning", "a" * 40,
                                         "b" * 40, "2026-38"]
    assert linjer[2].split("\t")[1:] == ["produksjon", "c" * 40,
                                         "d" * 40, "2026-39"]


def test_feilet_push_sier_fra_uten_aa_paastaa_at_noe_kan_gjores_om(datarepo):
    """Steg 5 har lastet opp. En feil her er en MANGLENDE BOKFØRING.

    Origin flyttes under føttene på oss, så pushen avvises. Da skal
    linja være committet, grunnen stå i klartekst, og kommandoene som
    gjenstår være de som faktisk gjenstår — ikke en `Stopp`, som i dette
    skriptet alltid betyr at ingenting er lastet opp.
    """
    fremmed = datarepo.parent / "fremmed"
    subprocess.run(["git", "clone", str(datarepo.parent / "origin.git"),
                    str(fremmed)], check=True, capture_output=True)
    for n, v in (("user.email", "x@example.invalid"), ("user.name", "X")):
        subprocess.run(["git", "-C", str(fremmed), "config", n, v],
                       check=True, capture_output=True)
    (fremmed / "annet.txt").write_text("i veien\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(fremmed), "add", "-A"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(fremmed), "commit", "-m", "kom først"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(fremmed), "push", "origin", "main"],
                   check=True, capture_output=True)

    problem, gjenstaar = publiser.bokfor("a" * 40, "b" * 40,
                                         "produksjon", "2026-39")
    assert "committet, men ikke pushet" in problem
    assert gjenstaar and gjenstaar[-1] == "git push origin HEAD:main"

    # Committet, og bare den ene fila — treet er rent, så det som
    # gjenstår er ett push og ingen opprydding.
    urent = subprocess.run(["git", "-C", str(datarepo), "status",
                            "--porcelain"], capture_output=True, text=True)
    assert urent.stdout == ""
    rort = subprocess.run(
        ["git", "-C", str(datarepo), "show", "--name-only", "--format=",
         "HEAD"], capture_output=True, text=True).stdout.split()
    assert rort == ["docs/publiseringslogg.tsv"]
