"""Publiseringsskriptet — de to prøvene som ikke kan tas i etterkant.

Steg 5 kan ikke prøves her: den laster opp noe. Det som KAN prøves er
stegene som avgjør om den skal få gjøre det, og de to som står her er
begge skrevet etter en observert feil:

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
