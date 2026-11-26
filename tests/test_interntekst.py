"""Interne feltnavn og interne merknader står ikke i synlig tekst.

Kildene stempler merknader på rader de skriver — `dato_forbehold`,
`arts_forbehold`, `gjenfangst_forbehold` — som sier hvordan raden skal
leses (CLAUDE.md 1b-3). De hører hjemme i snapshotene og changeloggen.
På en side er de vårt eget arbeidsspråk, med feltnavn som `observed_at`
og `siste_rapport` midt i setningen (BRIEF.md: «Ingen interne ord … i
synlig tekst»).

MÅLT 25.11.2026 på bygget av 32cfa52 (sluttkontrollen 15b, funn A, målt
på nytt i økt R1a): biomasselagets to merknader sto som «vesentlig
endring» på 6 sider, lokalitet 45148, 45230 og 45252 og de tre
selskapene deres. En lokalitet som kom inn i laget, fikk én changelog-rad
per felt, også for merknadene, og «ny» er vesentlig. Ingen andre
snake_case-ord sto i synlig tekst på noen av de 2 625 sidene, og ingen av
de tre andre merknadene sto på noen side.

Rettingen er kildens egen erklæring (`Source.bokforing`), lest av den ene
lesedøra `nettsted._les_beveg()`. Ingen liste i nettstedet.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import html
import importlib
import os
import pkgutil
import re
from pathlib import Path

import polars as pl
import pytest

import nettsted
import sources
from core import registry
from core.contract import erklaert_bokforing


def merknader() -> dict[str, str]:
    """{«modul.KONSTANT»: tekst} for hver merknad en kilde stempler på rader.

    Kildenes egen navneskikk: merknaden står i en konstant `*_FORBEHOLD`
    og skrives i feltet `*_forbehold`. `test_merknadene_er_funnet` holder
    oppslaget ærlig, så det ikke kan finne null og stå grønt.
    """
    ut = {}
    for info in pkgutil.iter_modules(sources.__path__):
        modul = importlib.import_module(f"sources.{info.name}")
        for navn, verdi in vars(modul).items():
            if navn.endswith("_FORBEHOLD") and isinstance(verdi, str):
                ut[f"{info.name}.{navn}"] = verdi
    return ut


def test_merknadene_er_funnet():
    funnet = merknader()
    for kjent in ("biomasselag.DATO_FORBEHOLD", "biomasselag.ARTS_FORBEHOLD",
                  "eierskap.DATO_FORBEHOLD", "romming.GJENFANGST_FORBEHOLD",
                  "romming.ANTALL_FORBEHOLD"):
        assert kjent in funnet, kjent
    assert all(len(t) > 60 for t in funnet.values())


def test_biomasselagets_merknader_er_bokforing():
    kilde = next(k for k in registry.discover() if k.name == "biomasselag")
    felt = erklaert_bokforing(kilde)
    assert ("biomasselag", "dato_forbehold") in felt
    assert ("biomasselag", "arts_forbehold") in felt
    # Feltene om FISKEN står igjen: de er det siden handler om.
    for f in nettsted.BIOLAGFELT:
        if f != "siste_rapport":
            assert ("biomasselag", f) not in felt, f


def test_en_lokalitet_som_kommer_inn_i_laget_mister_bare_merknadene(monkeypatch):
    """Gjennom døra, med kildens ekte erklæring. Raden for fisken står."""
    def rad(felt, verdi):
        return {"entity_id": "45252", "entity_type": "lokalitet",
                "entity_name": "HOHOLMEN", "field": felt, "old_value": None,
                "new_value": verdi, "change_type": "ny",
                "source": "biomasselag", "observed_at": "2026-09-15",
                "forrige_observed_at": "2026-09-10",
                "forrige_fetched_at": "", "published_at": "",
                "forrige_published_at": ""}

    rader = [rad("har_fisk", "Ja"), rad("lokalitet_status", "AKTIV"),
             rad("dato_forbehold", "observed_at er HENTETIDSPUNKTET vårt"),
             rad("arts_forbehold", "arter_tilstede er artene")]
    monkeypatch.setattr(nettsted.changelog, "les_alt",
                        lambda **k: pl.DataFrame(rader))
    monkeypatch.setattr(nettsted.changelog, "merk_utvalgsutvidelse",
                        lambda r: r)
    monkeypatch.setattr(nettsted.changelog, "merk_feltbevegelse",
                        lambda r, kilder=(): r)
    for buffer in (nettsted._les_beveg, nettsted._bokforingsfelt):
        buffer.cache_clear()
    try:
        felt = sorted(nettsted._les_beveg()["field"].to_list())
    finally:
        for buffer in (nettsted._les_beveg, nettsted._bokforingsfelt):
            buffer.cache_clear()
    assert felt == ["har_fisk", "lokalitet_status"]


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted")

# Et identifikator-ord med understrek: `observed_at`, `arter_tilstede`.
# Ikke når det står i en sti, et filnavn eller et anker.
SNAKE = re.compile(r"(?<![\w/.#-])[a-zæøå]+(?:_[a-zæøå0-9]+)+(?![\w/.-])")


def synlig_tekst(side: str) -> str:
    """Det en leser kan få se: `<body>` uten skript, stil, maler og
    kommentarer, taggene borte og mellomrommene slått sammen. Innhold bak
    en lukket `<details>` er med: det står på siden, ett klikk unna."""
    kropp = side.split("<body", 1)[-1]
    kropp = re.sub(r"<!--.*?-->", " ", kropp, flags=re.S)
    kropp = re.sub(r"<(script|style|template)\b.*?</\1\s*>", " ", kropp,
                   flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", kropp)).split())


def _sider():
    return sorted(p for p in NETTSTED.rglob("*.html")
                  if "pagefind" not in p.parts)


@trenger_bygg
def test_ingen_interne_feltnavn_i_synlig_tekst():
    funn = {}
    for fil in _sider():
        ord_ = sorted(set(SNAKE.findall(synlig_tekst(fil.read_text(encoding="utf-8")))))
        if ord_:
            funn[fil.relative_to(NETTSTED).as_posix()] = ord_
    assert not funn, f"{len(funn)} sider: {dict(list(funn.items())[:6])}"


@trenger_bygg
def test_ingen_intern_merknad_i_synlig_tekst():
    # De første 60 tegnene er nok til å kjenne igjen en merknad, og tåler
    # at en lang setning brytes annerledes i en celle.
    biter = {k: " ".join(v.split())[:60] for k, v in merknader().items()}
    funn = []
    for fil in _sider():
        tekst = synlig_tekst(fil.read_text(encoding="utf-8"))
        funn += [(fil.relative_to(NETTSTED).as_posix(), k)
                 for k, bit in biter.items() if bit in tekst]
    assert not funn, f"{len(funn)} treff: {funn[:6]}"
