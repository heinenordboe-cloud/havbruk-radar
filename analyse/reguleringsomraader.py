"""Tilordner akvakulturregisterets lokaliteter til HIs 28 reguleringsområder.

    .venv/bin/python analyse/reguleringsomraader.py

Punkt-i-polygon, ett punkt per lokalitet, mot de 28 polygonene i
`sources/reguleringsomraader.py`. Svarer på fire ting:

    1  hvor mange lokaliteter i hvert av de 28 områdene
    2  hvor mange utenfor alle 28, og om det er samme mengde som de som
       mangler produksjonsområde hos Fiskeridirektoratet
    3  KRYSSKONTROLLEN: stemmer tallet i det tilordnede området med
       lokalitetens `prodomraade_kode`
    4  områdene HI oppgir som tomme — 1A, 12D og 13A

## Dette er en ANALYSE, ikke en kilde

Resultatet er utledbart av to snapshots som allerede ligger i
`data/raw/`, og skal derfor ikke skrives som snapshots. Kjør den på nytt
når enten akvakultursnapshotet eller reguleringsområdene endrer seg.

## Hvorfor punkt 3 er den viktigste

De tre andre er tellinger. Punkt 3 er en KONTROLL, og den er gratis:
Fiskeridirektoratet har allerede plassert 969 av lokalitetene i et
produksjonsområde, HI har tegnet 28 områder inni de samme tretten, og
tallet i et reguleringsområdenavn ER produksjonsområdet. To uavhengige
parter har altså svart på samme spørsmål.

Treffer alle, er både polygonene og posisjonene våre bekreftet på én
gang — ingen av delene kunne vært feil uten at avvikene ble mange.

Treffer noen ikke, vet vi IKKE uten videre hvilken side som tar feil, og
da skal begge mistenkes. Et anlegg kan ligge millimeter fra en grense
HI har tegnet i grov oppløsning; en koordinat i registeret kan være
feilregistrert; produksjonsområdekoden kan være satt etter en annen
grense enn den geometriske. Analysen LISTER avvikene og velger ikke.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import snapshot                                    # noqa: E402
from sources.reguleringsomraader import (OMRAADER, inneholder,  # noqa: E402
                                         produksjonsomraade)

AKVAKULTUR = "akvakultur"
REGULERING = "reguleringsomraader"
LUSETALL = "lusetall"

# HIs egne utvandringsvinduer og anleggstall, LEST av tabell 1 i
# 2026-37 (arkivert i `data/arkiv/reguleringsomraader/2026-06-29.json.gz`
# som `grensetall_2026-37`). Bare de tre områdene oppgaven spør om.
#
# Tallet er HIs «antall anlegg med produksjon i utvandringsperioden per
# reguleringsområde (gjennomsnitt siste fire år)». Stjernen i tabellen
# betyr at området ikke fikk beregnet akseptabelt utslipp «fordi få
# eller ingen anlegg var i drift årene 2022-2025».
#
# Ført her og ikke lest av HTML-en ved kjøring, med vilje: å parse
# grensetallrapporten ville vært å bygge en kilde av den, og det er
# nettopp det beslutningen fra 09.09.2026 sier at vi ikke gjør. Tre tall
# skrevet av med kilde oppgitt er en sitering, ikke en kilde.
HI_UTVANDRING = {
    "1A":  ((4, 24), (6, 23), 0),
    "12D": ((6, 9), (8, 1), 0),
    "13A": ((6, 8), (7, 29), 0),
}


def _wkt_punkter(wkt: str) -> list[tuple[float, float]]:
    """Punktene ut av standard WKT, slik kilden lagret dem.

    Leses av SNAPSHOTET og ikke av geojson-kroppen i arkivet, med vilje:
    da er det den lagrede geometrien som prøves. Er WKT-en vi skriver
    ubrukelig, skal det vise seg her og ikke om to år.
    """
    inni = wkt[wkt.index("((") + 2: wkt.rindex("))")]
    return [(float(a), float(b))
            for a, b in (p.split() for p in inni.split(", "))]


def _bredt(frame: pl.DataFrame) -> pl.DataFrame:
    """Langt format til bredt: én rad per entitet, én kolonne per felt."""
    return frame.pivot(on="field", index="entity_id", values="value")


def omraader() -> list[tuple[str, list[tuple[float, float]]]]:
    dato = snapshot.siste_dato(REGULERING)
    if not dato:
        raise SystemExit(
            f"Ingen snapshot fra {REGULERING}. Kjør "
            f"`run.py --bare {REGULERING}` først."
        )
    _, ramme = snapshot.versjoner(REGULERING, dato)[-1]
    bredt = _bredt(ramme)
    ut = [(r["entity_id"], _wkt_punkter(r["geometri"]))
          for r in bredt.iter_rows(named=True)]
    return sorted(ut, key=lambda p: (int(p[0][:-1]), p[0][-1]))


def lokaliteter() -> pl.DataFrame:
    dato = snapshot.siste_dato(AKVAKULTUR)
    if not dato:
        raise SystemExit(f"Ingen snapshot fra {AKVAKULTUR}.")
    _, ramme = snapshot.versjoner(AKVAKULTUR, dato)[-1]
    return _bredt(ramme)


def tilordne(lok: pl.DataFrame,
             omr: list[tuple[str, list[tuple[float, float]]]]) -> list[dict]:
    """Ett treff per lokalitet. Flere treff er et funn, ikke noe å velge i.

    Områdene skal ikke overlappe. Gjør de det, sier raden det (`flere`)
    i stedet for at den første i lista vinner — en stille førstevinner
    ville gjort et geometriproblem usynlig i tellingen.
    """
    ut = []
    for r in lok.iter_rows(named=True):
        try:
            lon = float(r["lengdegrad"])
            lat = float(r["breddegrad"])
        except (TypeError, ValueError):
            ut.append({**r, "regomr": None, "flere": []})
            continue
        traff = [navn for navn, pkt in omr if inneholder(pkt, lon, lat)]
        ut.append({**r, "regomr": traff[0] if traff else None,
                   "flere": traff if len(traff) > 1 else []})
    return ut


def uten_po_i_omr(rader: list[dict]) -> list[dict]:
    """Lokaliteter som FALLER i et reguleringsområde, men som
    Fiskeridirektoratet ikke har gitt en produksjonsområdekode.

    De er ikke en feil i noen av retningene. Produksjonsområdene gjelder
    matfisk av laks og ørret i sjø; et settefiskanlegg på land eller i
    ferskvann har ingen kode, men har fortsatt en koordinat som ligger
    innenfor et polygon tegnet langs kysten.
    """
    return [r for r in rader if r["regomr"] and not r.get("prodomraade_kode")]


def _laksefisk_i_vinduet(ider: list[str], aar: int,
                         fra: tuple[int, int],
                         til: tuple[int, int]) -> set[str]:
    """Hvilke av lokalitetene som rapporterte laksefisk i vinduet.

    `har_laksefisk` og ikke `lus_er_rapportert`: spørsmålet er om det sto
    fisk i anlegget, ikke om noen rapporterte lus på den. Regel 1b-2 —
    still spørsmålet du faktisk vil ha svar på.

    ÉN uke med laksefisk er nok til å telle. Det er den mest romslige
    lesningen av «anlegg med produksjon i utvandringsperioden», og den er
    valgt med vilje: den kan bare gjøre HIs tall MER sannsynlig, aldri
    mindre. Finner den likevel anlegg der HI oppgir null, er det ikke
    fordi terskelen ble satt strengt.
    """
    import datetime as dt

    start = dt.date(aar, *fra).isoformat()
    slutt = dt.date(aar, *til).isoformat()
    ut: set[str] = set()
    for dato in snapshot.datoer(LUSETALL):
        if not start <= dato <= slutt:
            continue
        for _, ramme in snapshot.versjoner(LUSETALL, dato):
            traff = ramme.filter(
                pl.col("entity_id").is_in(ider)
                & (pl.col("field") == "har_laksefisk")
                & (pl.col("value") == "True"))
            ut |= set(traff["entity_id"].to_list())
    return ut


def main() -> int:
    omr = omraader()
    lok = lokaliteter()
    rader = tilordne(lok, omr)

    n = len(rader)
    print(f"\n{'='*72}")
    print(f"Reguleringsområder x akvakulturregisteret — {n} lokaliteter")
    print(f"{'='*72}")

    # ---- 1. fordeling ---------------------------------------------------
    telling = Counter(r["regomr"] for r in rader if r["regomr"])
    print(f"\n1. LOKALITETER PER REGULERINGSOMRÅDE\n")
    for navn, _ in omr:
        print(f"   {navn:>4}  {telling.get(navn, 0):4d}")
    print(f"   {'sum':>4}  {sum(telling.values()):4d}")

    # ---- 2. utenfor -----------------------------------------------------
    utenfor = [r for r in rader if not r["regomr"]]
    har_po = [r for r in rader if r.get("prodomraade_kode")]
    uten_po = [r for r in rader if not r.get("prodomraade_kode")]
    begge = [r for r in utenfor if not r.get("prodomraade_kode")]
    print(f"\n2. UTENFOR ALLE 28\n")
    print(f"   utenfor alle 28 polygoner        {len(utenfor):4d}")
    print(f"   uten prodomraade_kode i registeret {len(uten_po):4d}")
    print(f"   begge deler                      {len(begge):4d}")
    print(f"   utenfor MEN med prodomraade_kode {len(utenfor) - len(begge):4d}")
    print(f"   i et område MEN uten kode        "
          f"{len(uten_po) - len(begge):4d}")

    for hva, gruppe in (("utenfor alle 28", utenfor),
                        ("i et område, uten kode", uten_po_i_omr(rader))):
        vann = Counter(str(r.get("vanntype")) for r in gruppe)
        plass = Counter(str(r.get("plasseringstype")) for r in gruppe)
        print(f"\n   {hva} ({len(gruppe)}):")
        print(f"     vanntype    {dict(vann.most_common())}")
        print(f"     plassering  {dict(plass.most_common())}")

    overlapp = [r for r in rader if r["flere"]]
    if overlapp:
        print(f"\n   ADVARSEL: {len(overlapp)} lokaliteter traff FLERE "
              f"områder. Polygonene skal ikke overlappe.")

    # ---- 3. krysskontrollen ---------------------------------------------
    avvik = [r for r in har_po if r["regomr"]
             and produksjonsomraade(r["regomr"]) != r["prodomraade_kode"]]
    traff = [r for r in har_po if r["regomr"]]
    print(f"\n3. KRYSSKONTROLL — tallet i reguleringsområdet mot "
          f"prodomraade_kode\n")
    print(f"   med prodomraade_kode i registeret   {len(har_po):4d}")
    print(f"   av dem tilordnet et reguleringsområde {len(traff):4d}")
    print(f"   ENIGE                               "
          f"{len(traff) - len(avvik):4d}")
    print(f"   AVVIK                               {len(avvik):4d}")
    for r in sorted(avvik, key=lambda r: r["entity_id"]):
        print(f"     {r['entity_id']:>6} {str(r.get('navn'))[:26]:<26} "
              f"register PO{r['prodomraade_kode']:<3} "
              f"-> geometri {r['regomr']:<4} "
              f"({float(r['lengdegrad']):.4f}, {float(r['breddegrad']):.4f})")

    # ---- 4. områdene HI oppgir som tomme --------------------------------
    print(f"\n4. OMRÅDENE HI OPPGIR MED NULL AKTIVE ANLEGG\n")
    print("   HI teller anlegg MED PRODUKSJON I UTVANDRINGSVINDUET, snittet")
    print("   over 2022-2025 (2026-37 tabell 1). Vi teller alt som er")
    print("   REGISTRERT. Tallene skal ikke være like — men de tre områdene")
    print("   skal være tomme eller nesten tomme.\n")
    print(f"   {'omr':>4}  {'alle':>5}  {'m/laks':>7}  {'i sjø':>7}  "
          f"{'aktive':>7}")
    for navn in ("1A", "12D", "13A"):
        i_omr = [r for r in rader if r["regomr"] == navn]
        laks = [r for r in i_omr if "SALMON" in str(r.get("arter", ""))]
        sjo = [r for r in laks if str(r.get("vanntype")) == "Salt"
               and str(r.get("plasseringstype")) != "Onshore"]
        aktive = [r for r in sjo
                  if str(r.get("har_kommersiell_aktivitet")) == "True"]
        print(f"   {navn:>4}  {len(i_omr):5d}  {len(laks):7d}  "
              f"{len(sjo):7d}  {len(aktive):7d}")

    print("\n   Registrert er ikke det samme som I DRIFT. Spørsmålet HI")
    print("   svarte på er om anleggene hadde produksjon i UTVANDRINGS-")
    print("   VINDUET, og det kan vi spørre lusetallene om direkte:\n")
    for navn, (fra, til, hi) in HI_UTVANDRING.items():
        # Samme filter som kolonnen «i sjø» over: laks, saltvann, ikke
        # landbasert. Den strammeste lesningen, valgt fordi den bare kan
        # gjøre HIs null MER sannsynlig.
        ider = [r["entity_id"] for r in rader if r["regomr"] == navn
                and "SALMON" in str(r.get("arter", ""))
                and str(r.get("vanntype")) == "Salt"
                and str(r.get("plasseringstype")) != "Onshore"]
        if not ider:
            print(f"   {navn:>4}  ingen sjølokaliteter med laks registrert "
                  f"— HI oppgir {hi}")
            continue
        print(f"   {navn:>4}  vindu {fra[1]:02d}.{fra[0]:02d}-"
              f"{til[1]:02d}.{til[0]:02d}, HI oppgir {hi} anlegg:")
        for aar in (2022, 2023, 2024, 2025):
            i_drift = _laksefisk_i_vinduet(ider, aar, fra, til)
            print(f"          {aar}: {len(i_drift)} med laksefisk rapportert "
                  f"{sorted(i_drift)}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
