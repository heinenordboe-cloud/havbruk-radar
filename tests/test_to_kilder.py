"""To kilder på samme side som ser ut som en motsigelse: hver verdi står
med sin kilde og sin dato.

Lilleelv (11411), 23.11.2026: undertittelen sa «laks», månedsrapportene
«Røye», og «Ja» sto i samme rad som «brakklagt uke 40». Undertittelen
hadde verken kilde eller dato, og «Ja» hadde ingen kilde i raden. Det så
ut som én kilde som motsa seg selv.

MÅLT 23.11.2026 på bygget av f2c2896, 1 786 lokalitetssider:

    81  undertittelens arter (Akvakulturregisteret) og nyeste
        månedsrapport (biomasselaget) har ikke én art felles
   125  sider med 213 månedsrader der «Ja» står ved «brakklagt» eller
        «Nei» ved «ikke brakklagt»; 82 av radene er en konflikt
        (`paastand.konflikt()`) og merket «uenige»
    23  sider der tilstanden viser «Fisk ja» og «Lakselus brakklagt»
        (de hadde kilde og dato fra før)

Ingen verdi endres eller velges bort. Prøvene holder at begge står, med
navn og dato ved verdien.

Den siste prøven trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import html
import os
import re
from pathlib import Path

import pytest

from tests.test_nettsted import _fisk_og_lus, _side


def _flat(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", markup)).split())


def _maanedsrader(side: str) -> list[str]:
    tabell = re.search(r'<table id="biomasselag-maaned".*?</table>', side, re.S)
    return re.findall(r'<tr data-kilde="biomasselag".*?</tr>', tabell.group(0), re.S) \
        if tabell else []


HERKOMST = r'<span class="herkomst">{kilde} · <time datetime="([\d-]+)">[^<]*</time></span>'


def _celle(rad: str, felt: str) -> str:
    m = re.search(rf'<td[^>]*data-felt="{felt}"[^>]*>(.*?)</td>', rad, re.S)
    return m.group(1) if m else ""


def test_raden_har_kilde_og_dato_ved_begge_verdiene():
    """Utenfor BarentsWatchs univers (som Lilleelv): ingen konflikt, men
    «Ja» og «brakklagt» står begge, hver med navn og dato."""
    side = _fisk_og_lus("2026-08-31", "Ja", "2026-08-31", "True", laks="False")
    rader = _maanedsrader(side)
    assert len(rader) == 1
    rad = rader[0]
    fisk = _celle(rad, "har_fisk")
    assert _flat(fisk).startswith("Ja ")
    assert re.search(HERKOMST.format(kilde="Fiskeridir."), fisk).group(1) == "2026-08-31"
    bw = _celle(rad, "brakklagt")
    assert _flat(bw).startswith("brakklagt ")
    assert re.search(HERKOMST.format(kilde="BarentsWatch"), bw).group(1) == "2026-08-31"
    assert ">uenige<" not in rad
    assert '<th scope="col">Samme uke</th>' in side


def test_undertittelen_sier_hvem_som_oppgir_arten():
    side = _side()
    assert re.search(r'</p>\s*<p class="herkomst lok-undertittel-kilde">'
                     r'Akvakulturregisteret · <time datetime="[\d-]+">', side)


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "lokalitet").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted med lokalitetssider")


@trenger_bygg
def test_hver_verdi_som_kan_motsi_en_annen_har_kilde_og_dato():
    """På hver lokalitetsside: undertittelen har Akvakulturregisteret og en
    dato, og i hver rad i «Månedsrapporter» står fisk-verdien med
    Fiskeridir. og månedsslutten, og BarentsWatch-verdien med BarentsWatch
    og uka. Verdiene foran er kildens, i de ordene siden alltid har brukt."""
    sider = sorted((NETTSTED / "lokalitet").glob("*/index.html"))
    assert len(sider) > 100, "fant ikke lokalitetssidene"
    feil, rader_sett, par_sett = [], 0, 0
    for fil in sider:
        side = fil.read_text(encoding="utf-8")
        loknr = fil.parent.name
        if not re.search(r'<p class="lok-undertittel">.*?</p>\s*'
                         r'<p class="herkomst lok-undertittel-kilde">'
                         r'Akvakulturregisteret · <time datetime="[\d-]+">', side, re.S):
            feil.append((loknr, "undertittelen har ikke kilde og dato"))
        for rad in _maanedsrader(side):
            rader_sett += 1
            dato = re.search(r'<th scope="row"><time datetime="([\d-]+)"', rad).group(1)
            fisk = _celle(rad, "har_fisk")
            if fisk:
                m = re.search(HERKOMST.format(kilde="Fiskeridir."), fisk)
                if not m or m.group(1) != dato:
                    feil.append((loknr, dato, "fisk uten kilde og dato", _flat(fisk)))
                if _flat(fisk).split(" ")[0] not in ("Ja", "Nei"):
                    feil.append((loknr, dato, "fisk-verdien", _flat(fisk)))
            bw = _celle(rad, "brakklagt")
            if bw:
                if not re.search(HERKOMST.format(kilde="BarentsWatch"), bw):
                    feil.append((loknr, dato, "BarentsWatch uten kilde og dato", _flat(bw)))
                if not re.match(r"(ikke )?brakklagt ", _flat(bw)):
                    feil.append((loknr, dato, "BarentsWatch-verdien", _flat(bw)))
                fv = _flat(fisk).split(" ")[0]
                par_sett += (fv == "Ja" and _flat(bw).startswith("brakklagt")) or (
                    fv == "Nei" and _flat(bw).startswith("ikke brakklagt"))
    assert not feil, f"{len(feil)} funn: {feil[:5]}"
    assert rader_sett > 1000 and par_sett >= 1, (
        f"prøven har ikke sett tilfellet: {rader_sett} rader, {par_sett} par")
