"""Fart: byte per side mot et budsjett (økt 16b, 6a).

Tre sider: forsiden, /fasiten/ og én lokalitetsside. For hver måles alt
nettleseren henter når siden lastes på 1440x900, fordelt på HTML, CSS,
JS, fonter og bilder, og summen holdes mot budsjettet under.

## Budsjettet er målt, ikke valgt

10 % over det sidene veide da budsjettet ble satt (Heine, 16b), MÅLT
24.11.2026 i Chromium mot portens bygg av 16b, uten komprimering (den
lokale tjeneren pakker ikke; Cloudflare gjør det for HTML, CSS og JS, så
det som går over nettet er mindre). Tallene for 15a står ved siden av,
så et budsjett utledet av en side som var blitt tung, ville synes.

Et budsjett som følger sidene, er ikke et budsjett (CLAUDE.md 1b-4). Det
flyttes bare ved en skrevet endring her, med ny måling og grunn.

## Hva som telles

Svaret på hver forespørsel siden gjør til den er lastet og nettet er
stille: dokumentet, stilarket, skriptene, fontene og bildene, og det
skriptene selv henter. Et bilde som lastes lat og står under bretten,
hentes ikke og telles ikke.

Prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og Playwright,
og kjøres i porten.
"""
import os
import socketserver
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest

LOKALITET = "/lokalitet/31397/"

# BYTE PER SIDE, 10 % over målingen 24.11.2026 (portens bygg av 16b).
# I parentes: målingen for 16b og for 15a (portens bygg av 48e19ed).
BUDSJETT = {
    "/": 760_831,           # 16b: 691 664 · 15a: 684 767
    "/fasiten/": 281_798,   # 16b: 256 180 · 15a: 229 074
    LOKALITET: 491_869,     # 16b: 447 153 · 15a: 441 313
}

SLAG = {"document": "html", "stylesheet": "css", "script": "js",
        "font": "fonter", "image": "bilder"}

ROT = os.environ.get("HAVBRUK_NETTSTED", "")
trenger_bygg = pytest.mark.skipif(
    not ROT or not (Path(ROT) / "index.html").exists(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted — "
           "bygg med `python nettsted.py --alle --ut <mappe>` først")


def tjen(rot: str):
    class Tyst(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    class Gjenbruk(socketserver.TCPServer):
        allow_reuse_address = True

    t = Gjenbruk(("127.0.0.1", 0), partial(Tyst, directory=str(Path(rot))))
    threading.Thread(target=t.serve_forever, daemon=True).start()
    return t, f"http://127.0.0.1:{t.server_address[1]}"


def vekt(nettleser, url: str) -> dict:
    """{"html": n, "css": n, "js": n, "fonter": n, "bilder": n, "annet": n,
    "sum": n} i byte for siden på `url`, i en ny fane uten hurtigbuffer."""
    kontekst = nettleser.new_context(viewport={"width": 1440, "height": 900},
                                     device_scale_factor=1)
    side = kontekst.new_page()
    svar = []
    side.on("response", lambda r: svar.append(r))
    side.goto(url, wait_until="networkidle")
    ut = {k: 0 for k in ("html", "css", "js", "fonter", "bilder", "annet")}
    for r in svar:
        try:
            n = len(r.body())
        except Exception:   # noqa: BLE001 — en omdirigering har ingen kropp
            continue
        ut[SLAG.get(r.request.resource_type, "annet")] += n
    kontekst.close()
    ut["sum"] = sum(ut.values())
    return ut


@pytest.fixture(scope="module")
def maalt():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="playwright og chromium installeres for hånd (requirements-verktoy.md), "
               "ikke fra requirements-dev.txt")
    t, base = tjen(ROT)
    with playwright.sync_playwright() as p:
        nettleser = p.chromium.launch()
        try:
            yield {sti: vekt(nettleser, base + sti) for sti in BUDSJETT}
        finally:
            nettleser.close()
            t.shutdown()


def test_budsjettet_er_satt_for_hver_side():
    assert all(isinstance(v, int) and v > 0 for v in BUDSJETT.values()), BUDSJETT


@trenger_bygg
@pytest.mark.parametrize("sti", list(BUDSJETT))
def test_ingen_side_over_budsjettet(maalt, sti):
    m = maalt[sti]
    assert m["sum"] <= BUDSJETT[sti], (
        f"{sti}: {m['sum']:,} byte over budsjettet {BUDSJETT[sti]:,} "
        f"({', '.join(f'{k} {v:,}' for k, v in m.items() if k != 'sum')})")


if __name__ == "__main__":
    # python tests/test_fart.py <bygg>: vekten per side, til budsjettet.
    import json
    import sys
    from playwright.sync_api import sync_playwright
    t, base = tjen(sys.argv[1])
    with sync_playwright() as p:
        b = p.chromium.launch()
        print(json.dumps({sti: vekt(b, base + sti) for sti in BUDSJETT}, indent=1))
        b.close()
    t.shutdown()
