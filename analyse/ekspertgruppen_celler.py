"""Cellene fra ekspertgruppen, med sikkerhetsgrad — og verktøyet for å
verifisere dem.

    python analyse/ekspertgruppen_celler.py --uverifisert
    python analyse/ekspertgruppen_celler.py --uverifisert --felt kategori
    python analyse/ekspertgruppen_celler.py --verifiser 2020-12-31 2 kategori

`sources/ekspertgruppen.py` skriver hver verdi med sin MASKINELLE
lesemåte, `tabell` eller `lopende_tekst`. Den tredje graden — verifisert
av et menneske — kan ikke ligge i snapshotet:

  - snapshots er append-only (CLAUDE.md regel 2), så et menneske som
    leser rapporten i morgen kan ikke skrive om fila fra i dag, og
  - verifikasjonen er per CELLE, mens lesemåten er per felt per rapport.

Den føres derfor i `analyse/fasit/ekspertgruppen-verifisert.csv` og
legges på ved LESING. Samme sted og samme begrunnelse som den gamle
fasitfila hadde — den er en forutsetning for et resultat, ikke en
observasjon om verden — men nå ved siden av dataene i stedet for i
stedet for dem.

## Verifikasjonen er bundet til VERDIEN og til KROPPEN

Kvitteringen bærer både verdien som ble lest og sha256 av rapporten den
ble lest i. Endrer en forbedret parser verdien, matcher ikke
kvitteringen lenger, og cellen faller tilbake til uverifisert.

Det er CLAUDE.md 1b-4 anvendt på en kvittering: en referanse skal ikke
flytte seg selv. Uten bindingen ville en verifikasjon gjort 24.08 arvet
seg videre til et tall ingen har sett, og det er verre enn ingen
verifikasjon — det er en usann påstand om at noen har sett etter.

## `tolk()` tvinger kalleren til å ta stilling

Kilden lagrer ulikheter ORDRETT: «< 1 %» blir `"<1"`, ikke `0.5` og ikke
`1`. `float("<1")` kaster, og det er meningen. `tolk()` returnerer
`(relasjon, tall)` slik at en analyse må skrive ned hva den gjør med en
ulikhet i stedet for å svelge den.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import sys
from pathlib import Path
from typing import Iterable, NamedTuple

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import snapshot                                    # noqa: E402
from core.paths import ARKIV_DIR                             # noqa: E402
from sources.ekspertgruppen import SIKKERHET_SUFFIKS         # noqa: E402

KVITTERING = ROOT / "analyse" / "fasit" / "ekspertgruppen-verifisert.csv"
KOLONNER = ["observed_at", "po", "felt", "verdi", "rapport_sha256",
            "verifisert_av", "dato", "merknad"]

VERIFISERT = "verifisert"
KILDE = "ekspertgruppen"


class Celle(NamedTuple):
    """Én verdi med sin sikkerhetsgrad, slik en analyse ser den."""
    observed_at: str
    po: str
    felt: str
    verdi: str
    # `tabell` | `lopende_tekst` | `verifisert`
    sikkerhet: str
    raw_hash: str


def _kvitteringer() -> dict[tuple[str, str, str], dict]:
    """Leser kvitteringsfila. Tom dict når den ikke finnes ennå."""
    if not KVITTERING.exists():
        return {}
    with KVITTERING.open(encoding="utf-8") as f:
        rader = [r for r in csv.DictReader(
            line for line in f if not line.startswith("#"))]
    return {(r["observed_at"], r["po"], r["felt"]): r for r in rader}


def _arkivhasher() -> dict[str, str]:
    """sha256 -> filnavn for kildens arkiverte kropper.

    Brukes bare til å gi et lesbart navn i utlistingen. `raw_hash` på
    raden er innholdsadressert (se core/raw.py), så det er hashen som er
    identiteten — filnavnet er en bekvemmelighet.
    """
    import gzip
    mappe = ARKIV_DIR / KILDE
    if not mappe.exists():
        return {}
    ut = {}
    for sti in sorted(mappe.glob("*.gz")):
        with gzip.open(sti, "rb") as f:
            ut[hashlib.sha256(f.read()).hexdigest()] = sti.name
    return ut


def les(fra: str = "0000-00-00", til: str = "9999-99-99") -> list[Celle]:
    """Alle celler fra kilden, med sikkerhetsgrad påført.

    Leser GJENNOM `snapshot.les_mellom()`, ikke med `pl.read_parquet()`
    på en glob: persondatafilteret og `published_at`-fallbacken ligger i
    `snapshot._les()`, og `test_ingen_leser_snapshots_utenom_les()` feller
    enhver analyse som går utenom.

    ## Sist utgitte påstand PER FELT, ikke per snapshot

    Versjonene av en dato slås sammen felt for felt, i
    utgivelsesrekkefølge. Det er ikke det samme som å ta siste snapshot,
    og forskjellen er ekte: 2021-rapporten gjentar 2020 med en OPPDATERT
    TABELL, men uten avsnittene. Tar man siste snapshot, forsvinner
    utvandringsvinduet og de kontinuerlige estimatene fra
    2020-rapporten — ikke fordi ekspertgruppen trakk dem tilbake, men
    fordi den neste rapporten ikke gjentok dem.

    Et felt som ikke er nevnt på nytt er ikke revidert bort. Det er
    nøyaktig samme regel `diff.revisjon_mellom()` følger når den bare
    sammenligner FELLES felter, og den må gjelde begge veier: en
    opplysning som ikke telles som revisjon når den forsvinner, kan ikke
    forsvinne når vi leser heller.
    """
    kvitteringer = _kvitteringer()
    ut: list[Celle] = []

    # {dato: {(po, felt): rad}} — bygget i utgivelsesrekkefølge, så en
    # senere påstand overskriver en tidligere PER FELT.
    gjeldende: dict[str, dict[tuple[str, str], dict]] = {}
    for dato, ramme in snapshot.les_mellom(KILDE, fra, til):
        felt_for_felt = gjeldende.setdefault(dato, {})
        for rad in ramme.iter_rows(named=True):
            felt_for_felt[(rad["entity_id"], rad["field"])] = rad

    for dato, verdier in sorted(gjeldende.items()):
        for (po, felt), rad in sorted(verdier.items()):
            if felt.endswith(SIKKERHET_SUFFIKS):
                continue
            lesemaate = verdier.get((po, felt + SIKKERHET_SUFFIKS), {})
            sikkerhet = lesemaate.get("value", "")

            kvittering = kvitteringer.get((dato, po, felt))
            # Kvitteringen gjelder NØYAKTIG den verdien og NØYAKTIG den
            # kroppen den ble skrevet for. Se modulens docstring.
            if (kvittering
                    and kvittering["verdi"] == rad["value"]
                    and kvittering["rapport_sha256"] == rad["raw_hash"]):
                sikkerhet = VERIFISERT

            ut.append(Celle(dato, po, felt, rad["value"], sikkerhet,
                            rad["raw_hash"]))
    return ut


def tolk(verdi: str) -> tuple[str, float]:
    """`"<1"` -> `("<", 1.0)`.  `"34"` -> `("=", 34.0)`.

    Finnes for at ingen analyse skal kunne bruke en ulikhet som om den
    var et punktestimat. Kilden lagrer «< 1 %» ordrett fordi det er det
    ekspertgruppen faktisk skrev; her tvinges kalleren til å skrive ned
    hva den gjør med det.

    Kaster på en verdi som ikke er et tall i det hele tatt — «moderat/lav»
    fra en sammensatt celle er ikke et estimat, og skal ikke bli 0.
    """
    tekst = verdi.strip()
    relasjon = "="
    if tekst[:1] in ("<", ">"):
        relasjon, tekst = tekst[0], tekst[1:]
    try:
        return relasjon, float(tekst)
    except ValueError as e:
        raise ValueError(
            f"{verdi!r} er ikke et tallestimat. Sammensatte kategorier "
            f"(«moderat/lav») og kategoriord skal ikke tvinges til tall."
        ) from e


def uverifiserte(celler: Iterable[Celle]) -> list[Celle]:
    return [c for c in celler if c.sikkerhet != VERIFISERT]


def _skriv_kvittering(observed_at: str, po: str, felt: str, verdi: str,
                      raw_hash: str, av: str, merknad: str) -> None:
    """Legger til én kvittering. Skriver hodet hvis fila er ny."""
    ny = not KVITTERING.exists()
    KVITTERING.parent.mkdir(parents=True, exist_ok=True)
    with KVITTERING.open("a", encoding="utf-8", newline="") as f:
        if ny:
            f.write(
                "# Menneskelig verifikasjon av enkeltceller fra\n"
                "# sources/ekspertgruppen.py. Skrives av\n"
                "# `analyse/ekspertgruppen_celler.py --verifiser`.\n"
                "#\n"
                "# Kvitteringen gjelder NØYAKTIG den verdien og NØYAKTIG\n"
                "# den rapporten den ble skrevet for. Endrer en forbedret\n"
                "# parser verdien, matcher den ikke lenger, og cellen\n"
                "# faller tilbake til uverifisert. Det er med vilje: en\n"
                "# kvittering skal ikke arve seg videre til et tall ingen\n"
                "# har sett.\n")
            csv.writer(f).writerow(KOLONNER)
        csv.writer(f).writerow(
            [observed_at, po, felt, verdi, raw_hash, av,
             dt.date.today().isoformat(), merknad])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--uverifisert", action="store_true",
                   help="vis celler som ikke er verifisert av et menneske")
    p.add_argument("--felt", help="begrens til ett felt, f.eks. kategori")
    p.add_argument("--aar", help="begrens til ett år, f.eks. 2020")
    p.add_argument("--verifiser", nargs=3,
                   metavar=("OBSERVED_AT", "PO", "FELT"),
                   help="kvitter for én celle etter å ha lest den i "
                        "rapporten")
    p.add_argument("--av", default="", help="hvem som verifiserte")
    p.add_argument("--merknad", default="", help="fritekst til kvitteringen")
    args = p.parse_args()

    celler = les()
    if args.felt:
        celler = [c for c in celler if c.felt == args.felt]
    if args.aar:
        celler = [c for c in celler if c.observed_at.startswith(args.aar)]

    if args.verifiser:
        observed_at, po, felt = args.verifiser
        treff = [c for c in les()
                 if (c.observed_at, c.po, c.felt) == (observed_at, po, felt)]
        if not treff:
            print(f"Fant ingen celle {observed_at} PO{po} {felt!r}.")
            return 1
        if not args.av:
            print("--av kreves: en kvittering uten navn er ikke en "
                  "kvittering.")
            return 1
        c = treff[0]
        _skriv_kvittering(c.observed_at, c.po, c.felt, c.verdi, c.raw_hash,
                          args.av, args.merknad)
        print(f"Kvittert: {c.observed_at} PO{c.po} {c.felt} = {c.verdi!r} "
              f"(rapport {c.raw_hash[:16]}…)")
        return 0

    if not celler:
        print("Ingen celler. Er kilden backfillet?")
        return 1

    ugjorte = uverifiserte(celler)
    navn = _arkivhasher()

    if args.uverifisert:
        print(f"{len(ugjorte)} uverifiserte celler av {len(celler)}\n")
        forrige = None
        for c in ugjorte:
            nøkkel = (c.observed_at, c.raw_hash)
            if nøkkel != forrige:
                print(f"\n  {c.observed_at}   rapport "
                      f"{navn.get(c.raw_hash, c.raw_hash[:16] + '…')}")
                forrige = nøkkel
            print(f"    PO{c.po:<3} {c.felt:<44} {c.verdi:<12} "
                  f"[{c.sikkerhet}]")
        print(f"\nKvitter med:\n"
              f"  python analyse/ekspertgruppen_celler.py "
              f"--verifiser <observed_at> <po> <felt> --av <navn>")
        return 0

    # Standardvisning: sammendrag per felt og lesemåte.
    print(f"{len(celler)} celler, {len(ugjorte)} uverifiserte\n")
    print(f"  {'felt':<44} {'tabell':>8} {'tekst':>8} {'verif.':>8}")
    felter: dict[str, dict[str, int]] = {}
    for c in celler:
        felter.setdefault(c.felt, {}).setdefault(c.sikkerhet, 0)
        felter[c.felt][c.sikkerhet] += 1
    for felt in sorted(felter):
        t = felter[felt]
        print(f"  {felt:<44} {t.get('tabell', 0):>8} "
              f"{t.get('lopende_tekst', 0):>8} {t.get(VERIFISERT, 0):>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
