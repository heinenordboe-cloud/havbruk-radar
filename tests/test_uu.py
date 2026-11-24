"""Universell utforming: axe-core mot portens bygg (økt 16b, 6b).

Seks sider skal ikke ha brudd på WCAG 2.1 AA, slik axe-core måler det:
forsiden, /fasiten/, siden for K2, én lokalitet, ett selskap og /kommune/.
Brudd på andre sidetyper listes i rapporten for økta og rettes ikke her.

## axe-core er vendret, ikke installert

`tests/vendor/axe-core-4.10.3/` har axe.min.js og lisensen (MPL-2.0),
pakket ut av npm-tarballen axe-core-4.10.3.tgz. Tarballens sha512 var den
npm oppgir (`dist.integrity`) før noe ble pakket ut, 24.11.2026. Summen
av fila står under og holdes her: en annen fil er en annen måling.
Ingen pip-avhengighet, så kodrepoets Actions installerer ingenting nytt.
Se requirements-verktoy.md.

## Uten nett

axe settes inn fra fila, og hver forespørsel som ikke går til den lokale
tjeneren, avvises. En side som prøvde å hente noe utenfra, ville feilet
her i stedet for å bli målt med noe den fikk fra nett.

Prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og Playwright med
Chromium, som test_smalskjerm.py, og kjøres i porten.
"""
import hashlib
import os
import socketserver
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest

AXE = Path(__file__).resolve().parent / "vendor" / "axe-core-4.10.3" / "axe.min.js"
# MÅLT 24.11.2026 på fila pakket ut av den kontrollerte tarballen.
AXE_SHA256 = "880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb"
LISENS_SHA256 = "af175b9d96ee93c21a036152e1b905b0b95304d4ae8c2c921c7609100ba8df7e"

# WCAG 2.1 AA, slik axe merker reglene: nivå A og AA i 2.0 og 2.1.
TAGGER = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

# DE SEKS SIDENE (16b, 6b). Lokaliteten og selskapet er de
# test_smalskjerm.py også bruker: Oterneset har den bredeste tabellen, og
# selskapet har lenkerader og lange lister.
SIDER = ("/", "/fasiten/", "/fasiten/brakklegging/", "/lokalitet/31397/",
         "/selskap/921668236/", "/kommune/")

ROT = os.environ.get("HAVBRUK_NETTSTED", "")
trenger_bygg = pytest.mark.skipif(
    not ROT or not (Path(ROT) / "index.html").exists(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted — "
           "bygg med `python nettsted.py --alle --ut <mappe>` først")


def test_axe_er_den_vendrede_fila_med_lisensen():
    """Summen av axe.min.js og lisensen ved siden av. Prøven kjører uten
    bygg, så en byttet fil stopper den vanlige runden også."""
    assert hashlib.sha256(AXE.read_bytes()).hexdigest() == AXE_SHA256
    lisens = AXE.parent / "LICENSE"
    assert hashlib.sha256(lisens.read_bytes()).hexdigest() == LISENS_SHA256
    assert AXE.read_text(encoding="utf-8").startswith("/*! axe v4.10.3")
    assert "Mozilla Public License" in lisens.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tjener():
    class Tyst(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    class Gjenbruk(socketserver.TCPServer):
        allow_reuse_address = True

    t = Gjenbruk(("127.0.0.1", 0), partial(Tyst, directory=str(Path(ROT))))
    threading.Thread(target=t.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{t.server_address[1]}"
    t.shutdown()


@pytest.fixture(scope="module")
def side(tjener):
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="playwright og chromium installeres for hånd (requirements-verktoy.md), "
               "ikke fra requirements-dev.txt")
    with playwright.sync_playwright() as p:
        nettleser = p.chromium.launch()
        s = nettleser.new_page(viewport={"width": 1440, "height": 900})
        # UTEN NETT: alt som ikke går til den lokale tjeneren, avvises.
        s.route("**/*", lambda rute: rute.continue_()
                if rute.request.url.startswith(tjener) else rute.abort())
        yield s
        nettleser.close()


def brudd(side, url: str) -> list[dict]:
    """Bruddene axe finner på siden, som (regel, alvor, antall, første
    treff). Brukes også av skriptet som lister de andre sidetypene."""
    side.goto(url, wait_until="load")
    side.evaluate("document.fonts.ready")
    side.add_script_tag(content=AXE.read_text(encoding="utf-8"))
    res = side.evaluate(
        """async (tagger) => {
          const r = await axe.run(document, {
            runOnly: {type: 'tag', values: tagger}, resultTypes: ['violations']});
          return r.violations.map(v => ({
            regel: v.id, alvor: v.impact, antall: v.nodes.length,
            hjelp: v.help, forste: v.nodes[0].target.join(' ')}));
        }""", TAGGER)
    return res


@trenger_bygg
@pytest.mark.parametrize("sti", SIDER)
def test_ingen_brudd_paa_wcag_21_aa(side, tjener, sti):
    funnet = brudd(side, tjener + sti)
    assert not funnet, f"{sti}: " + "; ".join(
        f"{b['regel']} ({b['alvor']}, {b['antall']}): {b['forste']}" for b in funnet)
