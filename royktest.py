#!/usr/bin/env python3
"""Røyktest av kystloggen.no etter en publisering. Bare lesing.

    python royktest.py --mappe NETTSTED --kvittering K [--base URL] [--www URL]

Kjøres til slutt i `publiser.yml`. Fem sider hentes fra den levende
adressen og sammenlignes med byggemappa som nettopp ble lagt ut:

    forsiden                  /
    nyeste uke                /endringer/<uke>/
    to lokaliteter            /lokalitet/<nr>/, den første og den siste
                              med kart
    ett produksjonsområde     /produksjonsomrade/<nr>/, det første med kart

For hver: status 200, `Content-Security-Policy` LIK den `_headers` i
bygget oppgir, `© Kartverket` der siden har kart, og kontaktadressen fra
bygget som klartekst i en `mailto:`-lenke. Forsiden skal lenke
til nyeste uke, og ukesiden skal ha tittelen bygget ga den — det er det
som sier at det er DETTE bygget som svarer, og ikke det forrige.

## Hvorfor forventningen leses av bygget

Ikke av en liste i denne fila. Hvilke lokaliteter som har kart, hva uka
heter og hvilken CSP som gjelder, er alle ting bygget avgjør. En prøve
med egne kopier av dem ville målt om nettstedet er slik det VAR da
prøven ble skrevet.

## www videresender til samme sti

Fra 07.10.2026 svarer `www.kystloggen.no` med 301 til `kystloggen.no`
og samme sti (en Redirect Rule hos Cloudflare). Før det svarte begge
vertene 200 med samme side, og bare `<link rel="canonical">` sa hvilken
som var den riktige. Røyktesten henter forsiden og den første
lokaliteten fra `www`-verten UTEN å følge videresendingen, og krever
status 301 og `Location` lik adressen på apex. Ikke 302 eller 308: en
midlertidig videresending sier noe annet til den som lenker.

Den måler bare `https://`. Over `http://www` er det to hopp — først til
`https://www`, så til apex (MÅLT 07.10.2026) — og det første eies av
Cloudflares «Always Use HTTPS», ikke av regelen.

## Hva den IKKE sammenligner: bytene

MÅLT 07.10.2026: Cloudflare skriver om HTML-en på veien ut.
E-postlenken i bunnteksten blir til `/cdn-cgi/l/email-protection#…`, og
et skript fra `/cdn-cgi/scripts/` legges til (Scrape Shield, «Email
Address Obfuscation»). Den levende forsiden er derfor ikke byte-lik den
som ble lastet opp, og en sha256-sammenligning ville feilet hver gang.

## Adressen skal stå i klartekst

Fra 07.10.2026 er omskrivingen over en FEIL, ikke en egenskap. Heine
slår av Email Address Obfuscation for kystloggen.no, og røyktesten
krever at adressen bygget skrev står som `mailto:<adresse>` i HTML-en
som svarer, og at `/cdn-cgi/l/email-protection` ikke gjør det. Uten
JavaScript viser den omskrevne lenken «[email protected]», og skriptet
som dekoder den er kode porten aldri har sett.

Bytene sammenlignes fortsatt ikke. At obfuskeringen er av, betyr ikke
at Cloudflare ikke endrer noe annet — det er ikke målt.

## Nye forsøk

En utrulling hos Cloudflare Pages er atomisk, men det tar noen sekunder
før produksjonsadressen peker på den. Feiler noe, prøves hele runden på
nytt etter en pause, inntil `--forsok` ganger. Bare det siste forsøket
teller.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROT = Path(__file__).resolve().parent

BASE = "https://kystloggen.no"
WWW = "https://www.kystloggen.no"

# Setningen bunnteksten skriver der siden har kart. Samme verdi som
# `nettsted.KARTVERKET`, prøvd i tests/test_royktest.py — her som kopi
# fordi denne fila ikke skal trenge polars for å hente fem sider.
KARTVERKET = "© Kartverket"

# Det Cloudflare skriver e-postlenker om til. Står den i en side, er
# adressen ikke lenger lesbar uten skriptet som dekoder den.
OBFUSKERT = "/cdn-cgi/l/email-protection"

UA = "kystloggen-royktest (+https://github.com/heinenordboe-cloud/havbruk-radar)"


@dataclass(frozen=True)
class Side:
    sti: str              # f.eks. "/lokalitet/10029/"
    kart: bool            # skal ha kartattribusjon
    tittel: str = ""      # <title> slik bygget skrev den; tom = sjekkes ikke
    lenke: str = ""       # en href forsiden skal ha; tom = sjekkes ikke


def _tittel(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return m.group(1).strip() if m else ""


def _har_kart(fil: Path) -> bool:
    return KARTVERKET in fil.read_text(encoding="utf-8", errors="replace")


def csp(mappe: Path) -> str:
    """CSP-en `_headers` gir alle sider (`/*`)."""
    blokk = ""
    for linje in (mappe / "_headers").read_text(encoding="utf-8").splitlines():
        if linje and not linje[0].isspace():
            blokk = linje.strip()
        elif blokk == "/*" and linje.strip().lower().startswith(
                "content-security-policy:"):
            return linje.split(":", 1)[1].strip()
    return ""


def kontakt(mappe: Path) -> str:
    """Adressen bygget skrev i bunnteksten på forsiden. Tom når ingen."""
    m = re.search(r'href="mailto:([^"]+)"',
                  (mappe / "index.html").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def utvalg(mappe: Path, uke: str) -> list[Side]:
    """De fem sidene, med det bygget sier at de skal inneholde.

    `ValueError` når bygget ikke har dem — da er det utvalget som ikke
    kan settes sammen, og det skal ikke se ut som en feil på nettstedet.
    """
    def nummerert(katalog: str) -> list[Path]:
        filer = [p / "index.html" for p in (mappe / katalog).iterdir()
                 if p.name.isdigit() and (p / "index.html").exists()]
        return sorted(filer, key=lambda p: int(p.parent.name))

    uke_fil = mappe / "endringer" / uke / "index.html"
    if not uke or not uke_fil.exists():
        raise ValueError(f"bygget har ingen side for uke «{uke}»")
    lok = [p for p in nummerert("lokalitet") if _har_kart(p)]
    po = [p for p in nummerert("produksjonsomrade") if _har_kart(p)]
    if len(lok) < 2 or not po:
        raise ValueError(f"bygget har {len(lok)} lokaliteter og {len(po)} "
                         f"produksjonsområder med kart; trenger 2 og 1")
    return [
        Side("/", kart=True, lenke=f"/endringer/{uke}/"),
        Side(f"/endringer/{uke}/", kart=False,
             tittel=_tittel(uke_fil.read_text(encoding="utf-8"))),
        Side(f"/lokalitet/{lok[0].parent.name}/", kart=True),
        Side(f"/lokalitet/{lok[-1].parent.name}/", kart=True),
        Side(f"/produksjonsomrade/{po[0].parent.name}/", kart=True),
    ]


def hent(url: str) -> tuple[int, dict[str, str], str, str]:
    """(status, hoder, kropp, endelig adresse). Kaster ikke på 4xx/5xx."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return (r.status, {k.lower(): v for k, v in r.headers.items()},
                    r.read().decode("utf-8", errors="replace"), r.geturl())
    except urllib.error.HTTPError as e:
        return (e.code, {k.lower(): v for k, v in e.headers.items()},
                "", url)


class _IkkeFolg(urllib.request.HTTPRedirectHandler):
    """Lar en 3xx bli stående som svar i stedet for å følge den."""

    def redirect_request(self, *args, **kwargs):
        return None


def hent_uten_videresending(url: str) -> tuple[int, dict[str, str], str, str]:
    """Som `hent()`, men en 301 er svaret, ikke et mellomsteg."""
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": UA})
    try:
        with urllib.request.build_opener(_IkkeFolg).open(req, timeout=30) as r:
            return (r.status, {k.lower(): v for k, v in r.headers.items()},
                    "", r.geturl())
    except urllib.error.HTTPError as e:
        return (e.code, {k.lower(): v for k, v in e.headers.items()},
                "", url)


def sjekk_www(www: str, base: str, sti: str,
              henter=hent_uten_videresending) -> list[str]:
    """Feilene for én sti på www-verten. Tom liste når den gir 301 til
    samme sti på `base`."""
    url = www.rstrip("/") + sti
    navn = www.split("://", 1)[-1].rstrip("/") + sti
    try:
        status, hoder, _, _ = henter(url)
    except (urllib.error.URLError, OSError) as e:
        return [f"{navn}: kunne ikke hentes ({e})"]
    maal = base.rstrip("/") + sti
    if status != 301:
        return [f"{navn}: status {status}, ikke 301 til {maal}"]
    if hoder.get("location", "") != maal:
        return [f"{navn}: 301 til «{hoder.get('location', '')}», ikke "
                f"til {maal}"]
    return []


def sjekk(base: str, side: Side, forventet_csp: str, henter=hent,
          adresse: str = "") -> list[str]:
    """Feilene for én side. Tom liste når den er som bygget sier."""
    url = base.rstrip("/") + side.sti
    try:
        status, hoder, kropp, endelig = henter(url)
    except (urllib.error.URLError, OSError) as e:
        return [f"{side.sti}: kunne ikke hentes ({e})"]
    if status != 200:
        return [f"{side.sti}: status {status}"]
    feil = []
    if endelig.rstrip("/") != url.rstrip("/"):
        feil.append(f"{side.sti}: videresendt til {endelig}")
    naa = hoder.get("content-security-policy", "")
    if not naa:
        feil.append(f"{side.sti}: ingen Content-Security-Policy")
    elif naa != forventet_csp:
        feil.append(f"{side.sti}: Content-Security-Policy er ikke den "
                    f"_headers oppgir: «{naa}»")
    if side.kart and KARTVERKET not in kropp:
        feil.append(f"{side.sti}: kartattribusjonen «{KARTVERKET}» mangler")
    if side.lenke and f'href="{side.lenke}"' not in kropp:
        feil.append(f"{side.sti}: lenker ikke til nyeste uke {side.lenke} — "
                    f"svarer et eldre bygg?")
    if adresse and f'href="mailto:{adresse}"' not in kropp:
        feil.append(f"{side.sti}: kontaktadressen {adresse} står ikke som "
                    f"klartekst i en mailto:-lenke")
    if OBFUSKERT in kropp:
        feil.append(f"{side.sti}: e-postadressen er skrevet om til "
                    f"{OBFUSKERT} — Email Address Obfuscation er på hos "
                    f"Cloudflare")
    if side.tittel and _tittel(kropp) != side.tittel:
        feil.append(f"{side.sti}: tittelen er «{_tittel(kropp)}», bygget "
                    f"skrev «{side.tittel}»")
    return feil


def www_stier(sider: list[Side]) -> list[str]:
    """Forsiden og den første lokaliteten: roten og en dyp sti."""
    return [sider[0].sti, next(s.sti for s in sider
                               if s.sti.startswith("/lokalitet/"))]


def kjor(base: str, sider: list[Side], forventet_csp: str,
         forsok: int, pause: float, henter=hent,
         adresse: str = "", www: str = "",
         www_henter=hent_uten_videresending) -> list[str]:
    """Feilene fra siste forsøk. Tom liste når alt svarer.

    `www` tom: videresendingen sjekkes ikke (en annen `--base` enn
    produksjon har ingen www-vert å sjekke)."""
    feil: list[str] = []
    for n in range(1, forsok + 1):
        feil = [f for s in sider
                for f in sjekk(base, s, forventet_csp, henter, adresse)]
        if www:
            feil += [f for sti in www_stier(sider)
                     for f in sjekk_www(www, base, sti, www_henter)]
        if not feil:
            return []
        print(f"  forsøk {n}/{forsok}: {len(feil)} feil")
        if n < forsok:
            time.sleep(pause)
    return feil


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mappe", type=Path, required=True,
                    help="byggemappa som ble lagt ut")
    ap.add_argument("--kvittering", type=Path, required=True)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--www", default=None,
                    help=f"www-verten som skal gi 301 til --base. Standard "
                         f"{WWW} når --base er {BASE}, ellers ingen")
    ap.add_argument("--forsok", type=int, default=4)
    ap.add_argument("--pause", type=float, default=20.0)
    a = ap.parse_args(argv)
    www = a.www if a.www is not None else (WWW if a.base == BASE else "")

    uke = json.loads(a.kvittering.read_text(encoding="utf-8")).get("uke", "")
    forventet_csp = csp(a.mappe)
    try:
        if not forventet_csp:
            raise ValueError("_headers i bygget oppgir ingen "
                             "Content-Security-Policy for /*")
        adresse = kontakt(a.mappe)
        if not adresse:
            raise ValueError("forsiden i bygget har ingen mailto:-lenke — "
                             "står nettsted.kontakt i config.yml?")
        sider = utvalg(a.mappe, uke)
    except (OSError, ValueError) as e:
        print(f"::error::Røyktesten kunne ikke settes opp: {e}")
        return 1

    print(f"Røyktest av {a.base}, uke {uke}, kontakt {adresse}:")
    for s in sider:
        print(f"  {s.sti}")
    if www:
        for sti in www_stier(sider):
            print(f"  {www}{sti} → 301")
    feil = kjor(a.base, sider, forventet_csp, a.forsok, a.pause,
                adresse=adresse, www=www)

    rader = ["## Røyktest", "", f"{a.base}, uke {uke}", "",
             "| side | |", "|---|---|"]
    for s in sider:
        egne = [f for f in feil if f.startswith(f"{s.sti}:")]
        rader.append(f"| `{s.sti}` | {'; '.join(egne) or 'ok'} |")
    if www:
        vert = www.split("://", 1)[-1].rstrip("/")
        egne = [f for f in feil if f.startswith(f"{vert}/")]
        rader.append(f"| `{vert}` → 301 | {'; '.join(egne) or 'ok'} |")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a",
                  encoding="utf-8") as f:
            f.write("\n".join(rader) + "\n")

    if feil:
        for f in feil:
            print(f"::error::Røyktest: {f}")
        return 1
    print("  alle sider svarer som bygget sier")
    return 0


if __name__ == "__main__":
    sys.exit(main())
