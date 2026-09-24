"""Publiseringsskriptet — søkeindeksen, som ikke kan prøves i etterkant.

Steg 5 kan ikke prøves her: den laster opp noe. Det som KAN prøves er
stegene som avgjør om den skal få gjøre det, og dette er ett av dem.

`nettsted.py` bygger siden ferdig også når pagefind-binæren mangler —
`/sok/` skrives, veiviseren til de tre flate indeksene virker, og
byggerapporten skriver `søkeindeks IKKE BYGGET`. Leses ikke den linja av
et menneske, går siden ut med et søkefelt som tar imot tastetrykk og
svarer ingenting. Produksjon nektes derfor i steg 4; en forhåndsvisning
advares, fordi den ses av den som ba om den.

Prøven måler FILENE, ikke byggerapporten — se `publiser.sokeindeks()` for
hvorfor. Derfor kan testene her kjøres uten å bygge noe.
"""

import json
from pathlib import Path

import pytest

import publiser


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
