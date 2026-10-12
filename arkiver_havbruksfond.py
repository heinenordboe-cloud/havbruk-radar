"""Arkiverer regelverket og utbetalingene for Havbruksfondet, med hash.

    python arkiver_havbruksfond.py                 # arkiver det som finnes nå
    python arkiver_havbruksfond.py --torrkjor      # si hva som ville skjedd

Kjøres for hånd, ikke av en workflow (ennå — se docs/MALING-HAVBRUKSFOND.md
punkt A6).

## Hvorfor

Fordelingen av Havbruksfondet mellom kommuner og fylkeskommuner står
IKKE i en forskrift. Den står i en instruks fra Nærings- og
fiskeridepartementet til Fiskeridirektoratet, og i departementets årlige
orientering om beløpet. MÅLT 12.10.2026: ingen forskrift på Lovdata
regulerer fordelingen; Fiskeridirektoratets side om fondet viser til
instruksen av 27.09.2024.

Og den siden lenker FEIL. Lenketeksten «Instruks for utbetalinger fra
Havbruksfondet (pdf, 95.0 kB)» peker på «Orientering om utbetalinger fra
Havbruksfondet i 2025», som er beløpsbrevet av 10.11.2025 — ikke
instruksen. Selve instruksen finnes ikke lenger på fiskeridir.no (404 på
begge adressene den har hatt). Den finnes i Wayback, avtrykk
03.11.2024. Derfor arkiveres den herfra, via `id_`, slik
pressemeldingene i `regjeringen-pressemeldinger/` er hentet.

Hva som hentes, og hvor det havner:

    havbruksfondet/
        Fiskeridirektoratets side om fondet, og hvert vedlegg den lenker
        (orienteringen 2025 og regnearkene med utbetalingene 2017–2025).
        Vedleggene leses av siden ved hver kjøring, så et nytt regneark
        for 2026 fanges uten at noen har gjettet adressen.
    havbruksfondet/  (Wayback)
        Instruksen av 27.09.2024 (gjeldende), instruksen av 30.11.2022
        (erstattet, men den eneste som sier hvilken BOKFØRINGSPERIODE
        salgsinntektene utbetales for) og den supplerende instruksen for
        2023.
    regjeringen-pressemeldinger/  (Wayback)
        Pressemeldingene som sier hvor stor andel av salget som går til
        fondet: fastpristildelingen og auksjonen 2024, og utbetalingen
        10.11.2025 med fordelingen per kommune. regjeringen.no svarer 403
        på direkte henting.

## Hva som lagres

Kroppen slik den kom, gzippet, gjennom `raw.arkiver_ny()` — én fil per
DISTINKTE kropp, så en uendret side gir ingen ny fil. Loggfila er
sidevogna: `data/arkiv/havbruksfondet/<dato>.logg.json`, én per kjøring.

Filnavnet i `havbruksfondet/` er kjøredatoen, som i `lovdata-*` og
`auksjon/`. Filnavnet i `regjeringen-pressemeldinger/` er pressemeldingens
egen «Dato:», som for de seks som ligger der fra før — mappa er ordnet
etter utgivelse, og en pressemelding skrevet inn under hentedagen ville
brutt det.

## `published_at`

Leses fra `X-Archive-Orig-Last-Modified` (Wayback bærer originalens
header videre) eller `Last-Modified`, og står ellers TOM — aldri
hentetidspunktet, og aldri `Memento-Datetime`, som er da ARKIVET hentet
kroppen (CLAUDE.md 1b-7). PDF-ens egne metadata (`/CreationDate`) og
brevets dato står i loggen ved siden av, merket som det de er.

## Kodeproveniens

Som de andre arkivskriptene: `kodeproveniens.krev_sporbar()` før noe
hentes, og `kode_commit`, `kode_rent` og `fetched_at` i loggen for hver
kropp. `--torrkjor` skriver ingen fil og er unntatt.
"""

import argparse
import datetime as dt
import io
import json
import re
import sys

import httpx

from arkiver_vilkar import synlig_tekst
from core import kodeproveniens
from core import raw as raw_arkiv
from sources import _http

KILDE = "havbruksfondet"
PRESSE = "regjeringen-pressemeldinger"

SIDE = "https://www.fiskeridir.no/akvakultur/havbruksfondet"

UA = "havbruk-radar/1.0 (kildearkivering; kontakt via repoet)"

# Vedleggene siden lenker. Både `download` og `inline` forekommer.
_VEDLEGG = re.compile(
    r'href="(/akvakultur/havbruksfondet/_/attachment/(?:download|inline)/[^"]+)"')

_W = "https://web.archive.org/web/{ts}id_/{url}"
_F = "https://www.fiskeridir.no/Akvakultur/Tema/Havbruksfondet"

# Dokumenter som bare finnes i Wayback. Avtrykkene er valgt fra
# CDX-indeksen 12.10.2026; de er de eneste med status 200.
INSTRUKSER = {
    "instruks-2024-09-27": _W.format(
        ts="20241103064951",
        url=f"{_F}/Endring%20av%20instruks%20for%20utbetalinger%20gjennom%20"
            "Havbruksfondet.pdf/_/attachment/download/278368a3-b2c0-4f50-bdd4-"
            "5aaedc9a870b:4e1ba9181d7f93c46054bb1d5614c8360d58070e/Endring%20av"
            "%20instruks%20for%20utbetalinger%20gjennom%20Havbruksfondet.pdf"),
    "instruks-2022-11-30": _W.format(
        ts="20230926131336",
        url=f"{_F}/_/attachment/download/35da28c9-61eb-4221-bd7c-6ec6899cbddf:"
            "a81446f91e8f2ca342d4cc25091350576c6bf089/Endring%20av%20instruks"
            "%20for%20utbetalinger%20fra%20Havbruksfondet.pdf"),
    "supplerende-instruks-2023": _W.format(
        ts="20240717042758",
        url=f"{_F}/_/attachment/inline/dfe50934-ad3a-43d8-a627-c296232bd302:"
            "cde957908c9f7e4e1643a7071b0fc8b5b8a63a84/supplerende-instruks-"
            "utbetalinger-havbruksfondet-2023.pdf"),
}

_R = "https://www.regjeringen.no/no/aktuelt/"
PRESSEMELDINGER = {
    # «hvorav 55 prosent går til kommuner og fylkeskommuner gjennom
    # Havbruksfondet» — fastprisinntektene.
    "fastpris-2024": _W.format(
        ts="20240606192920",
        url=_R + "auksjon-av-oppdrettstillatelser-holdes-24.-juni/id3043772/"),
    # «55 prosent av inntektene fra auksjonen … i tillegg til 55 prosent av
    # inntektene fra fastpristildelingen, samt produksjonsavgiften i sin
    # helhet.»
    "auksjon-2024": _W.format(
        ts="20240625180537",
        url=_R + "resultater-fra-auksjon-av-nye-oppdrettstillatelser-2024/"
                 "id3046941/"),
    # Fordelingen per kommune og fylkeskommune 2025, og faktaboksen.
    "utbetaling-2025": _W.format(
        ts="20251110134104",
        url=_R + "milliardutbetaling-fra-havbruksfondet/id3138552/"),
}

# «Pressemelding | Dato: 10.11.2025 | Nærings- og fiskeridepartementet»
_DATO = re.compile(r"Dato:\s*(\d\d)\.(\d\d)\.(\d{4})")


def pressedato(kropp: bytes) -> str:
    """Pressemeldingens egen dato, ISO. Tom når den ikke står der."""
    m = _DATO.search(synlig_tekst(kropp))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def vedlegg(side: bytes) -> list[str]:
    """Absolutte adresser til hvert vedlegg siden lenker, sortert, unike."""
    stier = set(_VEDLEGG.findall(side.decode("utf-8", "replace")))
    return sorted("https://www.fiskeridir.no" + s.replace("&amp;", "&")
                  for s in stier)


def pdf_metadata(kropp: bytes) -> dict[str, str]:
    """PDF-ens egne felt, ordrett. Dokumentets påstand, ikke en utgivelse."""
    if not kropp.startswith(b"%PDF"):
        return {}
    try:
        import pypdf
        m = pypdf.PdfReader(io.BytesIO(kropp)).metadata or {}
    except Exception:
        return {}
    return {k.lstrip("/"): str(m.get(k, "")) for k in
            ("/Title", "/CreationDate", "/ModDate") if m.get(k)}


def _hent(klient: httpx.Client, url: str) -> tuple[bytes, str]:
    """Kroppen og `published_at` lest av svaret. Tom streng = vet ikke."""
    r = _http.get(klient, url, hva=f"havbruksfondarkiv {url}")
    utgitt = (r.headers.get("X-Archive-Orig-Last-Modified")
              or r.headers.get("Last-Modified") or "")
    return r.content, utgitt


def _arkiver(klient, hva: str, url: str, kilde: str, dato: str,
             torr: bool, logg: list, kropp_og_utgitt=None) -> bytes | None:
    try:
        kropp, utgitt = kropp_og_utgitt or _hent(klient, url)
    except Exception as e:
        print(f"::error::Havbruksfondarkivering: {url} kunne ikke hentes: {e}")
        logg.append({"hva": hva, "url": url, "feil": str(e)})
        return None

    if kilde == PRESSE:
        egen = pressedato(kropp)
        if not egen:
            print(f"::warning::{hva}: fant ingen «Dato:» i kroppen; "
                  f"skrives under kjøredatoen {dato}.")
        dato = egen or dato

    post = {"hva": hva, "url": url, "kilde": kilde, "observed_at": dato,
            "byte": len(kropp), "published_at": utgitt}
    meta = pdf_metadata(kropp)
    if meta:
        post["pdf"] = meta
    if torr:
        print(f"  ville arkivert  {len(kropp):>7} B  {kilde}/{dato}  {hva}")
        logg.append(dict(post, torrkjoring=True))
        return kropp

    # Når VI hentet kroppen (CLAUDE.md 1b-7: OSS, ikke kilden).
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sha, ny = raw_arkiv.arkiver_ny(kilde, dato, kropp)
    print(f"  {'NY' if ny else 'uendret':<8} {len(kropp):>7} B  {sha[:16]}…  "
          f"{kilde}/{dato}  {hva}")
    logg.append(dict(post, sha256=sha, ny=ny, fetched_at=hentet))
    return kropp


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for arkivfilene i havbruksfondet/. "
                        "Standard: i dag. Sendes inn og leses ikke av noen "
                        "underfunksjon (1b).")
    a = p.parse_args(argv)

    dato = a.dato or dt.date.today().isoformat()
    print(f"Havbruksfondarkivering {dato}"
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    proveniens: dict = {}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Havbruksfondarkiveringen startet ikke: {e}")
            return 1
        proveniens = {"kode_commit": sha, "kode_rent": tilstand}
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    logg: list = []
    with httpx.Client(timeout=60.0, follow_redirects=True,
                      headers={"User-Agent": UA}) as klient:
        print("\nFiskeridirektoratet:")
        side = _arkiver(klient, "side", SIDE, KILDE, dato, a.torrkjor, logg)
        lenker = vedlegg(side) if side else []
        if side is not None and not lenker:
            # Siden har lenket ni regneark og ett brev siden før 12.10.2026.
            # Null er ikke «ingen utbetalinger» — det er en side som har
            # endret form, og da fanges ikke årets regneark heller.
            print(f"::warning::{SIDE} lenket ingen vedlegg.")
            logg.append({"advarsel": "ingen_vedlegg", "url": SIDE})
        for url in lenker:
            _arkiver(klient, "vedlegg", url, KILDE, dato, a.torrkjor, logg)

        print("\nInstrukser (Wayback):")
        for navn, url in INSTRUKSER.items():
            _arkiver(klient, navn, url, KILDE, dato, a.torrkjor, logg)

        print("\nPressemeldinger (Wayback):")
        for navn, url in PRESSEMELDINGER.items():
            _arkiver(klient, navn, url, PRESSE, dato, a.torrkjor, logg)

    for r in logg:
        if "sha256" in r:
            r.update(proveniens)

    nye = sum(1 for r in logg if r.get("ny"))
    feil = sum(1 for r in logg if "feil" in r)
    print(f"\n{sum(1 for r in logg if 'url' in r)} adresse(r), {nye} ny(e) "
          f"kropp(er), {feil} feil.")

    if not a.torrkjor:
        mappe = raw_arkiv.ARKIV_DIR / KILDE
        mappe.mkdir(parents=True, exist_ok=True)
        sti = mappe / f"{dato}.logg.json"
        n = 2
        while sti.exists():
            sti = mappe / f"{dato}.{n}.logg.json"
            n += 1
        sti.write_text(json.dumps(logg, indent=2, ensure_ascii=False))
        print(f"Logg: {sti}")

    return 1 if feil else 0


if __name__ == "__main__":
    sys.exit(main())
