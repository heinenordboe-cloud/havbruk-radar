"""Arkiverer Mattilsynets kropper for analysen av unntaksvekst.

    python arkiver_mattilsynet.py liste            # søknadslista, via kilden
    python arkiver_mattilsynet.py lakselus         # rapportene per lokalitet
    python arkiver_mattilsynet.py lakselus --torrkjor

Kjøres for hånd, ikke av en workflow. Se docs/ANALYSE-UNNTAKSVEKST.md.

## Hvorfor dette ikke er run.py

`unntaksvekst` er en ukentlig kilde, og mandagens kjøring skriver den
første versjonen av lista til `data/arkiv/unntaksvekst/` sammen med et
snapshot. Analysen trenger lista NÅ, og den trenger den med hash.

`run.py --bare unntaksvekst` ville skrevet mer enn lista: helsetilstand,
endringslogg for dagen, og en dom over hvert anslag i `predictions/` med
vindu som lukker i dag — på en fredag, uten resten av ukas kilder. Det er
ikke denne analysens sak å gjøre.

Her kalles derfor KILDENS EGEN `fetch()`, og svaret arkiveres under
kildens navn og datoen kilden selv oppgir, slik `runner.run_all()` gjør.
Ingen kobling skrives om: søkerfilteret og lokalitetskoblingen er
kildens, og de er det analysen bruker («bruk de entydige koblingene fra
kilden»). En arkivfil uten snapshot er lov — se `core/raw.py`.

## `lakselus`: rapportene for lokalitetene i lista

Mattilsynets åpne API (docs/MALING-MATTILSYNET-API.md) har lakselus-
rapportene fra uke 40/2023, med lusetelling og behandlinger per uke.
Ett kall per lokalitet i den nyeste arkiverte lista — de sikre OG de
usikre koblingene, så de usikre kan vises for seg — mot
`/api/lakselus/v2/rapporteringer?lokalitetsnummer=N`. Uten `limit` er
det ikke noe tak (MÅLT 09.10.2026: 96 845 rapporter i ett svar).

Hver lokalitet får sin egen mappe, og hver henting sin egen fil:

    data/arkiv/mattilsynet-lakselus/<lokalitetsnummer>/<dato>.json.gz

gjennom `raw.arkiver_ny()`, så en uendret kropp ikke skrives to ganger.
Spesifikasjonen (`/q/openapi`) arkiveres ved siden av, i
`mattilsynet-openapi/`: den er belegget for lisensen («Dataene fra APIet
… følger vilkårene i NLOD-lisensen») og for hvilken API-versjon kroppene
kom fra.

## PERSONVERN: rapportøren slippes bare gjennom med selskapsform

Hver rapport bærer `organisasjonsnummer` og `organisasjonsnavn` for den
som rapporterte. Er det et enkeltpersonforetak, er navnet et menneske
(CLAUDE.md regel 3), og rå-arkivet er append-only i git.

Filteret går derfor i minnet FØR arkivering, med samme regel som
`unntaksvekst`: nummeret slås opp i den nyeste eierskapskroppens
`enheter`, og navn og nummer beholdes bare når formen er en kjent
ikke-personform (`sources.eierskap.FORM_KART`). Alt annet — ukjent
nummer, ukjent form, personform — blanker begge feltene. Lusetallene og
behandlingene beholdes: de er lokalitetsdata.

Det arkiverte er derfor ikke kroppen, men rapportene etter filteret, med
kroppens sha256 og størrelse ved siden av. Samme presedens som
`unntaksvekst`, `eierskap` og `enhetsregisteret`.

## Kodeproveniens

Som de andre arkivskriptene: `kodeproveniens.krev_sporbar()` før noe
hentes, og `kode_commit`, `kode_rent` og `fetched_at` i sidevogna
`data/arkiv/mattilsynet/<dato>.logg.json`. `--torrkjor` skriver ingen fil
og er unntatt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
import time

import httpx

from core import kodeproveniens, persondata
from core import raw as raw_arkiv
from sources import _http
from sources.eierskap import FORM_KART, er_organisasjonsnummer, er_person
from sources.unntaksvekst import KOBLET, Unntaksvekst

LOGG_KILDE = "mattilsynet"
LAKSELUS_KILDE = "mattilsynet-lakselus"
OPENAPI_KILDE = "mattilsynet-openapi"

API = "https://akvakultur-offentlig-api.fisk.mattilsynet.io"
LAKSELUS = API + "/api/lakselus/v2/rapporteringer"
OPENAPI = API + "/q/openapi"

# PÅKREVD, MÅLT 09.10.2026: uten den svarer tjenesten 400 «must not be
# blank». Ingen nøkkel og ingen registrering — bare et navn på klienten.
KLIENT = {"Client-Id": "havbruk-radar", "Accept": "application/json"}

# Lokalitetene som hentes: de sikre koblingene og forslagene. Uløste har
# ikke noe nummer å spørre etter.
HENTES = KOBLET | {"usikker"}

# Headerne som tas vare på. Ingen Last-Modified er MÅLT (09.10.2026);
# den tas med om den dukker opp, og blir da `published_at`.
HEADERE = ("date", "last-modified", "etag", "content-type")

# MÅLT 09.10.2026: med 0,5 s svarte tjenesten 429 to ganger på 60 kall.
PAUSE_S = 2.0


def _logg(dato: str, poster: list[dict]) -> None:
    mappe = raw_arkiv.ARKIV_DIR / LOGG_KILDE
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / f"{dato}.logg.json"
    n = 2
    while sti.exists():
        sti = mappe / f"{dato}.{n}.logg.json"
        n += 1
    sti.write_text(json.dumps(poster, indent=2, ensure_ascii=False))
    print(f"Logg: {sti}")


def liste(kjoredato: str, torr: bool, proveniens: dict) -> int:
    """Søknadslista via `Unntaksvekst.fetch()`, arkivert under kildens navn."""
    kilde = Unntaksvekst()
    gjelder = kilde.gjelder_for(kjoredato)
    raw = kilde.fetch(kjoredato)
    rader = raw["rader"]
    koblet = sum(r["kobling"] in KOBLET for r in rader)
    print(f"  {len(rader)} rader, {koblet} med entydig lokalitet, "
          f"kropp sha256 {raw['sha256'][:16]}…")
    for a in kilde.advarsler:
        print(f"::warning::{a}")
    if torr:
        print("  TØRRKJØRING — ingenting skrevet.")
        return 0

    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sha, ny = raw_arkiv.arkiver_ny(kilde.name, gjelder, raw)
    print(f"  {'NY' if ny else 'uendret':<8} unntaksvekst/{gjelder}  "
          f"sha256 {sha[:16]}…")
    _logg(gjelder, [{
        "hva": "liste", "kilde": kilde.name, "url": raw["url"],
        "observed_at": gjelder, "sha256": sha, "ny": ny,
        "kropp_sha256": raw["sha256"], "kropp_byte": raw["bytes"],
        "headere": raw["headere"], "rader": len(rader), "koblet": koblet,
        "source_version": kilde.version, "published_at": "",
        "fetched_at": hentet, **proveniens}])
    return 0


# ---------------------------------------------------------------- lakselus

def selskapsformer() -> dict[str, str]:
    """{orgnr: typeValue} fra den nyeste eierskapskroppens `enheter`.

    Kroppen er allerede personfiltrert av `eierskap`; at et nummer står
    her, er ikke nok i seg selv — formen prøves i `beholdes()`."""
    filer = sorted((raw_arkiv.ARKIV_DIR / "eierskap").glob("*.json.gz"))
    if not filer:
        raise FileNotFoundError("ingen eierskapskropp å slå opp formene i")
    d = json.loads(gzip.open(filer[-1], "rb").read())
    return {str(e.get("openNr") or "").strip(): str(e.get("typeValue") or "")
            for e in d.get("enheter") or []}


def beholdes(orgnr: str, former: dict[str, str]) -> bool:
    """Er rapportøren et selskap vi VET er et selskap? «Vet ikke» er nei."""
    type_verdi = former.get(orgnr, "")
    form = FORM_KART.get(type_verdi, "")
    return bool(er_organisasjonsnummer(orgnr) and form
                and not er_person(type_verdi)
                and not persondata.er_personform(form))


def filtrer(rapporter: list[dict], former: dict[str, str]) -> tuple[list[dict], int]:
    """(rapportene med rapportøren blanket der den ikke er et kjent
    selskap, antall blanket)."""
    ut, blanket = [], 0
    for r in rapporter:
        orgnr = str(r.get("organisasjonsnummer") or "").strip()
        if beholdes(orgnr, former):
            ut.append(r)
        else:
            ut.append({**r, "organisasjonsnummer": "", "organisasjonsnavn": ""})
            blanket += 1
    return ut, blanket


def _hent(klient: httpx.Client, url: str, params: dict | None = None):
    return _http.get(klient, url, hva=f"mattilsynet {url} {params or ''}",
                     params=params, headers=KLIENT)


def lokaliteter() -> list[str]:
    """Lokalitetsnumrene i den nyeste arkiverte lista som skal hentes."""
    filer = sorted((raw_arkiv.ARKIV_DIR / "unntaksvekst").glob("*.json.gz"))
    if not filer:
        raise FileNotFoundError("ingen arkivert søknadsliste — kjør `liste` først")
    rader = json.loads(gzip.open(filer[-1], "rb").read())["rader"]
    return sorted({str(r["lokalitet_nr"]) for r in rader
                   if r.get("kobling") in HENTES and r.get("lokalitet_nr")},
                  key=int)


def lakselus(kjoredato: str, torr: bool, proveniens: dict) -> int:
    numre = lokaliteter()
    former = selskapsformer()
    print(f"  {len(numre)} lokaliteter, {len(former)} kjente selskapsnumre")
    logg: list[dict] = []
    feil = 0
    with httpx.Client(timeout=120.0, follow_redirects=True) as c:
        spes = _hent(c, OPENAPI)
        versjon = (spes.json().get("info") or {}).get("version", "")
        lisens = (spes.json().get("info") or {}).get("license") or {}
        print(f"  spesifikasjon versjon {versjon!r}, lisens {lisens}")
        if not torr:
            sha, ny = raw_arkiv.arkiver_ny(OPENAPI_KILDE, kjoredato, spes.content)
            logg.append({"hva": "openapi", "url": OPENAPI, "sha256": sha,
                         "ny": ny, "versjon": versjon, "lisens": lisens,
                         "fetched_at": _naa(), "published_at": "",
                         **proveniens})

        for i, nr in enumerate(numre, 1):
            try:
                svar = _hent(c, LAKSELUS, {"lokalitetsnummer": nr})
                rapporter = svar.json()
                if not isinstance(rapporter, list):
                    raise ValueError("svaret er ikke en liste")
                andre = {str(r.get("lokalitetsnummer")) for r in rapporter} - {nr}
                if andre:
                    raise ValueError(f"svaret har rapporter for {sorted(andre)}")
            except Exception as e:
                feil += 1
                print(f"::error::Mattilsynet lakselus {nr}: {e}")
                logg.append({"hva": "lakselus", "lokalitet": nr,
                             "feil": str(e)})
                continue
            filtrert, blanket = filtrer(rapporter, former)
            headere = {h: svar.headers[h] for h in HEADERE if h in svar.headers}
            post = {"url": str(svar.url), "status": svar.status_code,
                    "sha256": hashlib.sha256(svar.content).hexdigest(),
                    "bytes": len(svar.content), "headere": headere,
                    "api_versjon": versjon, "rapporter": filtrert,
                    "rapportor_blanket": blanket}
            if torr:
                print(f"  [{i}/{len(numre)}] {nr}: {len(rapporter)} rapporter, "
                      f"{blanket} rapportør(er) blanket")
            else:
                sha, ny = raw_arkiv.arkiver_ny(f"{LAKSELUS_KILDE}/{nr}",
                                               kjoredato, post)
                print(f"  [{i}/{len(numre)}] {nr}: {len(rapporter)} rapporter, "
                      f"{blanket} blanket, {'NY' if ny else 'uendret'} "
                      f"{sha[:12]}…")
                logg.append({"hva": "lakselus", "lokalitet": nr, "url": str(svar.url),
                             "sha256": sha, "ny": ny,
                             "kropp_sha256": post["sha256"],
                             "rapporter": len(rapporter),
                             "rapportor_blanket": blanket,
                             "published_at": headere.get("last-modified", ""),
                             "fetched_at": _naa(), **proveniens})
            time.sleep(PAUSE_S)

    if not torr:
        _logg(kjoredato, logg)
    print(f"\n{len(numre)} lokaliteter, {feil} feil.")
    return 1 if feil else 0


def _naa() -> str:
    """Når VI hentet kroppen (CLAUDE.md 1b-7: OSS, ikke kilden)."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("hva", choices=("liste", "lakselus"))
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="kjøredatoen. Standard: i dag. Sendes inn og leses "
                        "ikke av noen underfunksjon (1b).")
    a = p.parse_args(argv)

    kjoredato = a.dato or dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"Mattilsynet-arkivering {kjoredato}: {a.hva}"
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    proveniens: dict = {}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Mattilsynet-arkiveringen startet ikke: {e}")
            return 1
        proveniens = {"kode_commit": sha, "kode_rent": tilstand}
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    if a.hva == "liste":
        return liste(kjoredato, a.torrkjor, proveniens)
    return lakselus(kjoredato, a.torrkjor, proveniens)


if __name__ == "__main__":
    sys.exit(main())
