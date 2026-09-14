"""Arkiverer auksjonsresultatet for en tildelingsrunde. ETT FORSØK PER DAG,
OVER ET VINDU — fordi resultatet publiseres én gang og ikke kan hentes
i ettertid.

    python arkiver_auksjon.py                 # arkiver det som finnes nå
    python arkiver_auksjon.py --torrkjor      # si hva som ville skjedd

## Hvorfor dette ikke er en kilde

En kilde emitterer `Observation`-objekter, og det krever at formatet er
sett. **Formatet på 2026-resultatet er IKKE sett** — auksjonen holdes
27.09.2026, og siden finnes ikke ennå. CLAUDE.md regel 4: har du ikke
sett responsen, si det i stedet for å anta at den ligner en annen.

Derfor arkiverer denne bare. Prisene per produksjonsområde trekkes ut
senere, av en kilde som er skrevet mot en kropp som finnes — og kroppen
finnes fordi denne kjørte. Rekkefølgen er hele poenget: uttrekket kan
gjøres når som helst, hentingen kan bare gjøres den dagen.

## Hvorfor et NETT og ikke en adresse

Adressen til 2026-resultatet er ukjent. Det som ER sett (14.09.2026):

  * `fiskeridir.no/akvakultur/auksjon-av-produksjonskapasitet` svarer
    200 uten nøkkel, og lister nøyaktig ett barn per auksjonsrunde:
    juni 2018, lukket budrunde september 2018, august 2020, 2022,
    restauksjon 2023, og 2024. 2026-barnet vil dukke opp her.
  * 2024-resultatet ble publisert som pressemelding på regjeringen.no
    (`…/resultater-fra-auksjon-av-nye-oppdrettstillatelser-2024/
    id3046941/`) og var i Wayback 18:05 samme kveld som auksjonen.

Så: hent indeksen, arkiver den, og arkiver hvert barn. Nye barn fanges
uten at noen har gjettet en URL. regjeringen.no svarer 403 på direkte
henting (Cloudflare) og går derfor via Wayback, samme vei som
pressemeldingene i `data/arkiv/regjeringen-pressemeldinger/`.

## Hvorfor den kan kjøres hver dag uten å forsøple arkivet

`raw.arkiver_ny()` skriver bare når innholdet er NYTT. Ti kjøringer mot
en uendret indeks gir én fil. Det er det som gjør det trygt å legge
vinduet bredt — og vinduet MÅ være bredt, for cron er «best effort» og
en auksjon som utsettes en uke skal fortsatt fanges.

## `published_at` er tom, og det er et funn

Målt 14.09.2026: verken indeksen eller 2024-barnet sender
`Last-Modified`. Fiskeridirektoratet gir oss ingen utgivelsesdato for
disse sidene. Feltet settes da TOMT med en advarsel, aldri til
hentetidspunktet — CLAUDE.md 1b-7 punkt 1. For Wayback-kroppene leses
`X-Archive-Orig-Last-Modified` når den finnes.
"""

import argparse
import datetime as dt
import json
import re
import sys

import httpx

from core import raw as raw_arkiv
from sources import _http

KILDE = "auksjon"

INDEKS = "https://www.fiskeridir.no/akvakultur/auksjon-av-produksjonskapasitet"

# Wayback-indeksen over regjeringen.nos aktuelt-sider som nevner auksjon.
# Brukt fordi regjeringen.no svarer 403 på direkte henting.
#
# `from=` gjelder AVTRYKKETS tidspunkt, ikke sidens utgivelse. Målt
# 14.09.2026: `from=2026` alene ga 15 treff, hvorav havvind, kunstauksjon,
# mobilfrekvenser fra 2015 og 2024-runden — sider Wayback tilfeldigvis
# krøllet i 2026. Nettet må derfor strammes to ganger: URL-en må nevne
# oppdrett eller laks, OG avtrykket må ligge i auksjonsvinduet. Uten det
# arkiverer en «auksjonsarkivering» havvind.
CDX = ("http://web.archive.org/cdx/search/cdx?url=regjeringen.no/no/aktuelt/*"
       "&filter=original:.*auksjon.*&from={fra}&output=text"
       "&collapse=urlkey&fl=timestamp,original&limit=60")

# Bare disse ordene i URL-en regnes som lakseauksjon.
_RELEVANT = re.compile(r"oppdrett|laks|lakse|tillatels|loyve|løyve", re.I)

UA = "havbruk-radar/1.0 (kildearkivering; kontakt via repoet)"

_BARN = re.compile(
    r'href="(/akvakultur/auksjon-av-produksjonskapasitet/[A-Za-z0-9_-]+)"')


def _hent(klient: httpx.Client, url: str) -> tuple[bytes, str]:
    """Kroppen og `published_at` lest av svaret. Tom streng = vet ikke.

    Går gjennom `sources/_http.py` for retry på timeout, tilkoblingsfeil,
    5xx og 429 — samme lag som kildene bruker. En auksjonsdag er ikke
    dagen å oppdage at et enkeltkall feilet transient.
    """
    r = _http.get(klient, url, hva=f"auksjonsarkiv {url}")
    # Wayback bærer originalens egen header videre. Den er KILDENS
    # utgivelse; `Memento-Datetime` er arkivets hentetidspunkt og ville
    # vært feil part (1b-7).
    utgitt = (r.headers.get("X-Archive-Orig-Last-Modified")
              or r.headers.get("Last-Modified") or "")
    return r.content, utgitt


def _arkiver(klient: httpx.Client, url: str, dato: str, torr: bool,
             logg: list) -> None:
    try:
        kropp, utgitt = _hent(klient, url)
    except Exception as e:
        print(f"  FEIL  {url}\n        {e}")
        logg.append({"url": url, "feil": str(e)})
        return

    if torr:
        print(f"  ville arkivert  {len(kropp):>7} B  {url}")
        logg.append({"url": url, "byte": len(kropp), "torrkjoring": True})
        return

    h, ny = raw_arkiv.arkiver_ny(KILDE, dato, kropp)
    merke = "NY" if ny else "uendret"
    print(f"  {merke:<8} {len(kropp):>7} B  {h[:16]}…  {url}")
    if not utgitt:
        print(f"           published_at TOM — svaret bærer ingen "
              f"Last-Modified. Ikke satt til hentetidspunktet (1b-7).")
    logg.append({"url": url, "byte": len(kropp), "sha256": h, "ny": ny,
                 "published_at": utgitt})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--fra", default="20260920",
                   help="Tidligste Wayback-avtrykk som regnes med "
                        "(ÅÅÅÅMMDD). Standard er en uke før auksjonen "
                        "27.09.2026. Filteret gjelder AVTRYKKET, ikke "
                        "sidens utgivelse — se CDX-kommentaren.")
    p.add_argument("--dato", default="",
                   help="observed_at for arkivfilene. Standard: i dag. "
                        "Kjernen slår opp kjøredatoen ett sted (1b), så "
                        "den sendes inn her og leses ikke av noen "
                        "underfunksjon.")
    a = p.parse_args()

    dato = a.dato or dt.date.today().isoformat()
    print(f"Auksjonsarkivering {dato}"
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    logg: list = []

    klient = httpx.Client(timeout=60.0, follow_redirects=True,
                          headers={"User-Agent": UA})

    print(f"\nIndeks:")
    _arkiver(klient, INDEKS, dato, a.torrkjor, logg)

    try:
        indeks, _ = _hent(klient, INDEKS)
        barn = sorted(set(_BARN.findall(indeks.decode("utf-8", "replace"))))
    except Exception as e:
        print(f"  Indeksen kunne ikke leses for barnelenker: {e}")
        barn = []

    print(f"\n{len(barn)} auksjonsrunde(r) lenket fra indeksen:")
    for sti in barn:
        _arkiver(klient, "https://www.fiskeridir.no" + sti, dato,
                 a.torrkjor, logg)

    print(f"\nRegjeringen.no via Wayback:")
    try:
        r = _http.get(klient, CDX.format(fra=a.fra),
                      hva="CDX-oppslag auksjon")
        rader = [ln.split() for ln in r.text.splitlines() if ln]
    except Exception as e:
        print(f"  CDX-oppslaget feilet: {e}")
        rader = []

    treff = [(ts, u) for ts, u in rader if _RELEVANT.search(u)]
    print(f"  {len(rader)} avtrykk fra {a.fra} nevner auksjon, "
          f"{len(treff)} av dem oppdrett/laks")
    for ts, u in treff:
        _arkiver(klient, f"https://web.archive.org/web/{ts}id_/{u}",
                 dato, a.torrkjor, logg)

    nye = sum(1 for r in logg if r.get("ny"))
    feil = sum(1 for r in logg if "feil" in r)
    print(f"\n{len(logg)} adresse(r), {nye} ny(e) kropp(er), {feil} feil.")

    if not a.torrkjor:
        sti = raw_arkiv.ARKIV_DIR / KILDE / f"{dato}.logg.json"
        sti.parent.mkdir(parents=True, exist_ok=True)
        if not sti.exists():
            sti.write_text(json.dumps(logg, indent=2, ensure_ascii=False))
            print(f"Logg: {sti}")

    # Feil skal være synlige i Actions, men skal IKKE stoppe de øvrige
    # adressene — én død lenke er ikke en grunn til å miste resten.
    return 1 if feil and nye == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
