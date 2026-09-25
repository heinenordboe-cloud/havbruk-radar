"""390 piksler: ingen vannrett rulling i body, og ingen celle kuttet.

## Hvorfor denne prøven ikke går i den vanlige runden

Den trenger et FERDIG BYGGET nettsted og en nettleser. Bygget tar ~45
sekunder og Chromium starter i ett til; den vanlige runden er på sju.
En prøve som gjorde hver kjøring et minutt lengre, er en prøve noen
slår av.

Den kjøres derfor mot en bygd mappe, oppgitt i miljøet:

    python nettsted.py --alle --ut /tmp/ut
    HAVBRUK_NETTSTED=/tmp/ut python -m pytest tests/test_smalskjerm.py

Uten variabelen hoppes den over, og den sier hvorfor.

## Hva som måles, og hva som ikke kan måles her

MÅLT PÅ RENDRET SIDE, ikke i CSS-en. Om en tabell «blir et kort» er et
resultat av `data-label`, `display: block`, målebånd, ordbrytning og
skriftmetrikk sammen — og hvert av de fem leddene kan være riktig mens
resultatet er en celle som er bredere enn skjermen. Det samme
argumentet som kontrastprøven bruker for å regne framfor å lese.

To ting måles:

  1. `documentElement.scrollWidth` mot vindusbredden. Ruller siden
     vannrett på en telefon, er noe bredere enn skjermen — og det er den
     feilen kortene finnes for å fjerne.
  2. Hver celle i en korttabell: `scrollWidth` mot `clientWidth`. En
     celle som er bredere enn sin egen boks har innhold utenfor kanten,
     også når siden ikke ruller.

Tabellen som IKKE blir kort — krysstabellen på /endringer/ — står i sin
egen `overflow-x: auto`-ramme, og at den ruller er meningen. Prøven
måler derfor sida og kortcellene, ikke rammene.
"""

import os
import socketserver
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest

BREDDE = 390

# Én side per sidetype. Lokalitetssiden har den bredeste tabellen på
# nettstedet (ni kolonner lusetall), og /endringer/ har unntaket.
SIDER = (
    "/",
    "/lokalitet/",
    "/lokalitet/31397/",
    "/produksjonsomrade/4/",
    "/selskap/",
    "/endringer/",
    "/endringer/2026-39/",
    "/om/",
    "/sok/",
)

ROT = os.environ.get("HAVBRUK_NETTSTED", "")

pytestmark = pytest.mark.skipif(
    not ROT,
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted — "
           "bygg med `python nettsted.py --alle --ut <mappe>` først")


@pytest.fixture(scope="module")
def tjener():
    """Sidene bruker ABSOLUTTE adresser og må serveres, ikke åpnes.

    `file://` ville gitt brutte bilder, brutt navigasjon og — verst for
    denne prøven — et stilark som ikke kom fram, altså en side uten
    kortlayout som prøven ville målt som om den var siden vår.
    """
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
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        nettleser = p.chromium.launch()
        s = nettleser.new_page(viewport={"width": BREDDE, "height": 844})
        yield s
        nettleser.close()


@pytest.mark.parametrize("sti", SIDER)
def test_ingen_vannrett_rulling_paa_390(side, tjener, sti):
    side.goto(tjener + sti, wait_until="load")
    bredde = side.evaluate(
        "() => [document.documentElement.scrollWidth, window.innerWidth]")
    dokument, vindu = bredde
    assert dokument <= vindu, (
        f"{sti}: dokumentet er {dokument}px bredt i et {vindu}px vindu")


@pytest.mark.parametrize("sti", SIDER)
def test_ingen_celle_er_kuttet_paa_390(side, tjener, sti):
    side.goto(tjener + sti, wait_until="load")
    kuttet = side.evaluate("""() => {
      const ut = [];
      /* BARE `<tbody>`. Hoderadene er visuelt skjult (1px) og dermed
         «kuttet» per definisjon — de er ikke noe en leser ser. */
      for (const c of document.querySelectorAll(".tabell--kort tbody td, "
                                                + ".tabell--kort tbody th")) {
        if (c.scrollWidth > c.clientWidth + 1) {
          ut.push((c.dataset.label || c.textContent).trim().slice(0, 40)
                  + " (" + c.scrollWidth + " > " + c.clientWidth + ")");
        }
      }
      return ut.slice(0, 5);
    }""")
    assert not kuttet, f"{sti}: celler utenfor egen kant: {kuttet}"
