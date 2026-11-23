"""Ingen side vi lenker til fra kystloggen.no fører inn i kodrepoet,
utenom «Kildekoden» i bunnteksten (Heine, 23.11.2026).

MÅLT 23.11.2026 på bygget av f2c2896, alle filer utenom søkeindeksen
(HTML, XML, JSON, TXT, CSV, JS, MD, og innholdet i zip og xlsx):

    2 623  «Kildekoden» i bunnteksten                      (skal stå)
    2 280  <generator uri="…"> i feedene                    rettet
        2  llms.txt: en lenke, og siteringsadressen         rettet
        2  /om/: lenken under «Hvem som står bak»           rettet
        1  /om/: «codeRepository» i JSON-LD                 rettet

Ingen i nedlastingene. Kontaktlinja «via GitHub» står bare når
`nettsted.kontakt` mangler i config.yml, og den er satt.

Den siste prøven trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import os
import re
import zipfile
from pathlib import Path

import pytest

import nettsted
from tests.test_nettsted import _om, smaafelles  # noqa: F401  (fiksturen)

KODREPO = re.compile(
    r"https?://(?:www\.)?github\.com/heinenordboe-cloud/havbruk-radar(?!-data)[^\s\"'<>)]*")
BUNNTEKST = re.compile(
    r'<a href="https://github\.com/heinenordboe-cloud/havbruk-radar">Kildekoden</a>')


def test_feeden_har_ingen_adresse_til_kodrepoet():
    kilde = Path(nettsted.__file__).read_text(encoding="utf-8")
    assert "<generator>Kystloggen</generator>" in kilde
    assert "generator uri" not in kilde


def test_llms_siterer_nettstedet_og_lenker_ikke_til_kodrepoet(
        tmp_path, smaafelles, monkeypatch):
    monkeypatch.setenv("HAVBRUK_BASEURL", "https://kystloggen.no")
    tekst = nettsted.skriv_llms(tmp_path, smaafelles).read_text("utf-8")
    assert not KODREPO.search(tekst), KODREPO.findall(tekst)
    sitering = tekst.split("## Sitering", 1)[1]
    assert "https://kystloggen.no" in sitering


def test_om_siden_lenker_ikke_til_kodrepoet_i_innholdet():
    side = _om()
    main = side.split("<main", 1)[1].split("</main>", 1)[0]
    assert not KODREPO.search(main), KODREPO.findall(main)
    assert '"codeRepository"' not in side
    # Kontaktlinja uten adresse peker til lenken i bunnteksten.
    uten = " ".join(_om(kontakt="").split())
    assert "Kontakt går via GitHub" in uten
    assert not KODREPO.search(uten.split("<main", 1)[1].split("</main>", 1)[0])


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file() or not (NETTSTED / "om").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et fullt bygget nettsted")

TEKST = {".html", ".xml", ".json", ".txt", ".csv", ".js", ".md"}


@trenger_bygg
def test_bare_bunnteksten_lenker_til_kodrepoet():
    funn, bunntekst = [], 0
    for fil in NETTSTED.rglob("*"):
        if not fil.is_file() or "pagefind" in fil.parts:
            continue
        rel = fil.relative_to(NETTSTED).as_posix()
        if fil.suffix in TEKST:
            tekst = fil.read_text(encoding="utf-8", errors="ignore")
            if fil.suffix == ".html":
                bunntekst += len(BUNNTEKST.findall(tekst))
                tekst = BUNNTEKST.sub("", tekst)
            funn += [(rel, m.group(0)) for m in KODREPO.finditer(tekst)]
        elif fil.suffix in (".zip", ".xlsx"):
            with zipfile.ZipFile(fil) as z:
                for navn in z.namelist():
                    data = z.read(navn).decode("utf-8", errors="ignore")
                    funn += [(f"{rel}!{navn}", m.group(0)) for m in KODREPO.finditer(data)]
    assert not funn, f"{len(funn)} funn: {funn[:5]}"
    assert bunntekst > 1000, f"bare {bunntekst} sider har «Kildekoden»"
