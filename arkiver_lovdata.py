"""Arkiverer forskriftstekster fra lovdata.no som kropper med hash.

    python arkiver_lovdata.py                 # arkiver det som finnes nå
    python arkiver_lovdata.py --torrkjor      # si hva som ville skjedd

Kjøres for hånd, ikke av en workflow.

## Hvorfor

Analysen av unntaksvekst (docs/ANALYSE-UNNTAKSVEKST.md) måler drift mot
vilkårene i produksjonsområdeforskriften § 12, og vilkårene skal stå
ORDRETT med kilde og hash. Fram til 09.10.2026 lå forskriften ikke i
arkivet: den var lest to ganger (05.09 og 23.09.2026) og sitert med en
hash i docs/VERIFISERING-FARGELEGGINGEN.md, men kroppen var ikke tatt
vare på. Et sitat ingen kan holde mot det som sto der, er et sitat
leseren må tro på.

Kapasitetsjusteringsforskriftene ligger allerede i
`data/arkiv/trafikklysvedtak/`, hentet av den kilden. Dette skriptet
henter det de viser til og som manglet:

    produksjonsomradeforskriften
        SF-versjonen, altså den konsoliderte teksten slik den gjelder
        NÅ. § 12 er vilkårene for unntaksvekst, § 12a søknadsfristen og
        kvalifikasjonsperioden.
    produksjonsomradeforskriften-endring-2023
        LTI-versjonen av FOR-2023-09-28-1520, endringen som ga § 12
        dagens ordlyd og la til §§ 12a–12c. Den viser at ordlyden var på
        plass FØR kvalifikasjonsperioden 2023–2025 begynte (uke 40/2023).
        En konsolidert tekst alene kan ikke svare på det: den sier hva
        som gjelder i dag, ikke hva som gjaldt da.
    lakselusforskriften
        SF-versjonen. § 12 nr. 2 viser til «Grensene i forskrift
        5. desember 2012 nr. 1140 om bekjempelse av lakselus § 8».
    andsverkloven
        NL-versjonen av LOV-2018-06-15-40. § 14 er grunnlaget for at
        Mattilsynets søknadsliste kan gjengis: «Lover, forskrifter,
        rettsavgjørelser og andre vedtak av offentlig myndighet» er uten
        vern. Lagt til 09.10.2026; se docs/LISENSKJEDE.md merknad K.

## Hva som lagres

Kroppen slik den kom, gzippet, i `data/arkiv/lovdata-<dokument>/`,
gjennom `raw.arkiver_ny()` — én mappe per dokument, så en kropp bare
sammenlignes med sine egne tidligere versjoner. Samme form som
`arkiver_vilkar.py`, og loggfila er sidevogna: `data/arkiv/lovdata/
<dato>.logg.json`, én per kjøring.

`published_at` leses fra `Last-Modified` der tjenesten sender den, og
står ellers tom — aldri hentetidspunktet (CLAUDE.md 1b-7). Målt
05.09.2026 (docs/KILDE-TRAFIKKLYSVEDTAK.md): lovdata.no sender ingen.
Dokumentets egne metadatafelt «Sist endret» og «Ikrafttredelse» LESES og
står i loggen ved siden av, merket som det de er: Lovdatas påstand om
dokumentet, ikke en utgivelsestid for kroppen.

## Kodeproveniens

Som de andre arkivskriptene: `kodeproveniens.krev_sporbar()` før noe
hentes, og `kode_commit`, `kode_rent` og `fetched_at` i loggen for hver
kropp. `--torrkjor` skriver ingen fil og er unntatt.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import sys

import httpx

from arkiver_vilkar import synlig_tekst
from core import kodeproveniens
from core import raw as raw_arkiv
from sources import _http

DOKUMENTER = {
    "produksjonsomradeforskriften":
        "https://lovdata.no/dokument/SF/forskrift/2017-01-16-61",
    "produksjonsomradeforskriften-endring-2023":
        "https://lovdata.no/dokument/LTI/forskrift/2023-09-28-1520",
    "lakselusforskriften":
        "https://lovdata.no/dokument/SF/forskrift/2012-12-05-1140",
    "andsverkloven":
        "https://lovdata.no/dokument/NL/lov/2018-06-15-40",
}

LOGG_KILDE = "lovdata"

# Metadatafeltene Lovdata skriver i dokumenthodet, som «Sist endret
# FOR-2026-04-26-689». Leses ordrett; et felt som ikke står der, blir tomt.
#
# Verdiens FORM står i mønsteret, ikke bare navnet. «Ikrafttredelse» er
# også overskriften på siste paragraf, og innholdsfortegnelsen står
# foran dokumenthodet: et mønster på navnet alene ga «Vedlegg» og «og»
# (MÅLT 09.10.2026 på produksjonsområde- og lakselusforskriften).
#
# `LOV-` ved siden av `FOR-` fra åndsverkloven: en lov har lovens
# nummer i «Dato», og et mønster på bare `FOR-` ga tomt felt.
_DATO = r"\d\d\.\d\d\.\d{4}"
METAFELT = {
    "Dato": r"(?:FOR|LOV)-\d{4}-\d\d-\d\d-\d+",
    "Sist endret": r"(?:FOR|LOV)-\d{4}-\d\d-\d\d-\d+",
    "Ikrafttredelse": _DATO,
    # Klokkeslettet er valgfritt: en lov har «Kunngjort 15.06.2018» uten.
    "Kunngjort": _DATO + r"(?: kl\. \d\d\.\d\d)?",
}


def kilde(dokument: str) -> str:
    return f"lovdata-{dokument}"


def metadata(kropp: bytes) -> dict[str, str]:
    """Lovdatas egne felt i dokumenthodet, ordrett. Tomme når de mangler."""
    tekst = synlig_tekst(kropp)
    ut = {}
    for felt, form in METAFELT.items():
        m = re.search(rf"\b{re.escape(felt)} ({form})", tekst)
        ut[felt] = m.group(1) if m else ""
    return ut


def _hent(klient: httpx.Client, url: str) -> tuple[bytes, str]:
    r = _http.get(klient, url, hva=f"lovdataarkiv {url}")
    return r.content, r.headers.get("Last-Modified", "")


def arkiver(klient: httpx.Client, dokument: str, url: str, dato: str,
            torr: bool) -> dict:
    try:
        kropp, utgitt = _hent(klient, url)
    except Exception as e:
        print(f"::error::Lovdataarkivering: {url} kunne ikke hentes: {e}")
        return {"dokument": dokument, "url": url, "feil": str(e)}

    tekst_sha = hashlib.sha256(synlig_tekst(kropp).encode("utf-8")).hexdigest()
    post = {"dokument": dokument, "url": url, "byte": len(kropp),
            "tekst_sha256": tekst_sha, "published_at": utgitt,
            "lovdata": metadata(kropp)}
    if torr:
        print(f"  ville arkivert  {len(kropp):>7} B  {url}")
        return dict(post, torrkjoring=True)

    # Når VI hentet kroppen (CLAUDE.md 1b-7: OSS, ikke kilden).
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sha, ny = raw_arkiv.arkiver_ny(kilde(dokument), dato, kropp)
    print(f"  {'NY' if ny else 'uendret':<8} {len(kropp):>7} B  "
          f"{sha[:16]}…  {url}")
    return dict(post, sha256=sha, ny=ny, fetched_at=hentet)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for arkivfilene. Standard: i dag. "
                        "Sendes inn og leses ikke av noen underfunksjon (1b).")
    a = p.parse_args(argv)

    dato = a.dato or dt.date.today().isoformat()
    print(f"Lovdataarkivering {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    proveniens: dict = {}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Lovdataarkiveringen startet ikke: {e}")
            return 1
        proveniens = {"kode_commit": sha, "kode_rent": tilstand}
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    with httpx.Client(timeout=60.0, follow_redirects=True) as klient:
        logg = [arkiver(klient, dok, url, dato, a.torrkjor)
                for dok, url in DOKUMENTER.items()]

    for r in logg:
        if "sha256" in r:
            r.update(proveniens)

    nye = sum(1 for r in logg if r.get("ny"))
    feil = sum(1 for r in logg if "feil" in r)
    print(f"\n{len(logg)} dokument(er), {nye} ny(e) kropp(er), {feil} feil.")

    if not a.torrkjor:
        mappe = raw_arkiv.ARKIV_DIR / LOGG_KILDE
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
