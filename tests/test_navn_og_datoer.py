"""Én form for navn og én regel for datoer i synlig tekst (R1a, punkt 5).

Navn: registeret skriver i versaler. På sidene står selskaper i
`selskapsnavn()` (AS og ASA alltid i versaler) og steder i
`tittelform()`, overalt — også i siteringen, registerfeltene, tidslinja
og endringstabellene. Kildens skrivemåte står i nedlastingene.
`visningsord.navneregel()` er regelen.

Datoer: ISO står bare i `<time datetime>`, i filer og i URL-er. Synlig
tekst får `kortdato()` eller `dato()` (visningsord, datoregelen).

MÅLT 25.11.2026 på bygget av 32cfa52 (D1 A3 og A4): versaler fra
registeret i siteringen på 478 selskapssider og i registerfelt,
tidslinje og endringstabeller, og 156 587 ISO-datoer i synlig tekst.
Etter rettingen: 0 utenfor lusedelen. Lusedelen på lokalitetssiden
(tabellen, notene og grafen, 100 872) venter på syklusstripa (16c), og
prøven hopper over `<section id="lakselus">`.

Prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og hoppes over
uten.
"""
import html
import os
import re
from pathlib import Path

import pytest

import publiseringsvakt as vakt
import visningsord

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted")

ISO = re.compile(r"(?<![\d-])\d{4}-\d{2}-\d{2}(?![\d-])")
LUSEDEL = re.compile(r'<section[^>]*id="lakselus".*?</section>', re.S)


def _synlig(side: str) -> str:
    kropp = side.split("<body", 1)[-1]
    kropp = re.sub(r"<!--.*?-->", " ", kropp, flags=re.S)
    kropp = re.sub(r"<(script|style|template)\b.*?</\1\s*>", " ", kropp,
                   flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", kropp)).split())


def _sider():
    return sorted(p for p in NETTSTED.rglob("*.html") if "pagefind" not in p.parts)


def test_regelen_gir_versaler_bare_der_den_selv_vil():
    """Prøvenes mål for «rå versaler»: et navn i VERSALER som en av de to
    reglene ville endret. Regelens egne versaler (AS, NRS, LTD) er ikke
    det."""
    assert _raa("AUSTEVOLL MELAKS AS") and _raa("MØRE OG ROMSDAL")
    assert not _raa("Austevoll Melaks AS") and not _raa("NRS Feøy AS")
    assert not _raa("1814SALMON AS"), "ord med siffer står urørt i regelen"


def _raa(verdi: str) -> bool:
    v = verdi.strip()
    # BEGGE reglene ville endret den: et selskapsnavn regelen lar stå
    # (ord med siffer, NRS, LTD) er regelens form og ikke rå versaler.
    return (v == v.upper() and any(c.isalpha() for c in v)
            and visningsord.selskapsnavn(v) != v and visningsord.tittelform(v) != v)


@trenger_bygg
def test_ingen_iso_dato_i_synlig_tekst_utenfor_lusedelen():
    funn = []
    for fil in _sider():
        side = LUSEDEL.sub(" ", fil.read_text(encoding="utf-8"))
        treff = ISO.findall(_synlig(side))
        if treff:
            funn.append((fil.relative_to(NETTSTED).as_posix(), treff[:3]))
    assert not funn, f"{len(funn)} sider: {funn[:6]}"


@trenger_bygg
def test_navnene_staar_i_en_form():
    felt = (visningsord.SELSKAPSNAVNFELT | visningsord.STEDSNAVNFELT
            | {"navn", "entity_name"})
    funn = []
    for fil in _sider():
        for f, verdi in vakt.felt_verdier(fil.read_text(encoding="utf-8")):
            if f in felt and _raa(verdi):
                funn.append((fil.relative_to(NETTSTED).as_posix(), f, verdi))
    assert not funn, f"{len(funn)} celler: {funn[:6]}"


@trenger_bygg
def test_siteringen_paa_selskapssiden_har_navnet_fra_h1():
    sider = sorted((NETTSTED / "selskap").glob("*/index.html"))
    if not sider:
        pytest.skip("bygget har ingen selskapssider")
    feil = []
    for fil in sider:
        side = fil.read_text(encoding="utf-8")
        h1 = re.search(r"<h1><span data-navn>(.*?)</span></h1>", side, re.S)
        sitat = re.search(r'id="siterbar">Kystloggen \(\d{4}\)\.\s*<i>(.*?), organisasjonsnummer', side, re.S)
        if h1 and sitat and html.unescape(h1.group(1)).strip() != html.unescape(sitat.group(1)).strip():
            feil.append((fil.parent.name, sitat.group(1)[:40]))
    assert not feil, f"{len(feil)} av {len(sider)}: {feil[:6]}"
