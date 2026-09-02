"""Verifiseringstabell for utvandringsvinduet: år x PO x dato, med
ORDRETT setning og SIDETALL.

Skrives for at et menneske skal kunne slå opp et par av dem i PDF-en og
se at parseren leste det kilden faktisk skrev. Sidetallet er med nettopp
for at den kontrollen skal ta sekunder og ikke minutter.

Kjør:  .venv/bin/python analyse/vindu_uttrekk.py

Leser BARE arkivet. Ingenting skrives til disk herfra — snapshotene
skrives av `backfill.py --kilde ekspertgruppen --rapporter`.
"""

import gzip
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from core.paths import ARKIV_DIR
from sources import ekspertgruppen as E

# Hvilken form hver kropp bruker. Skrevet ned framfor å utledes av
# årstallet: det er nettopp formskiftet som er funnet her, og en
# funksjon som gjetter formen kunne ikke oppdaget at den endret seg.
FORM = {
    2020: ("2020-formen: start + slutt + median", None, False),
    2021: ("2021-formen: bare median", None, False),
    2022: ("periodeformen, dato som 15/5", E._VINDU_2022, True),
    2023: ("periodeformen, dato som 15/5", E._VINDU_2022, True),
    2024: ("periodeformen, dato som 15. mai", E._VINDU_2024, False),
    2025: ("periodeformen, dato som 15. mai", E._VINDU_2024, False),
}


def _side_for(sider: list[str], po: str, aar: int) -> int:
    """Hvilken SIDE vindussetningen for dette PO-et står på.

    Leter side for side framfor å regne den ut av et tegnoffset i den
    flate teksten. Offsetet ville vært raskere og ville vært feil: `_flat`
    normaliserer mellomrom, så posisjonen der stemmer ikke med noen
    posisjon i noen side.
    """
    if aar == 2020:
        m = re.compile(r"Antatt\s+tidspunkt\s+for\s+utvandring")
    elif aar == 2021:
        m = re.compile(r"Beregnet\s+tidspunkt\s+for\s+50\s*%\s*utvandring")
    else:
        m = re.compile(r"[Uu]tvandringsperioden\s+fra\s+elvene\s+i\s+PO\s*"
                       + po + r"\b")
    for nr, side in enumerate(sider, 1):
        flat_side = " ".join(side.split())
        if not m.search(flat_side):
            continue
        if aar >= 2022:
            return nr
        # 2020 og 2021 navngir ikke PO-et i selve setningen. Sida må da
        # tilhøre riktig seksjon, og seksjonsoverskriften står på den
        # samme eller en tidligere side.
        overskrifter = re.findall(r"Produksjonsområde\s+(\d{1,2})\s*:",
                                  " ".join(sider[:nr]))
        if overskrifter and str(int(overskrifter[-1])) == po:
            return nr
    return 0


def _ordrett(seksjon: str, aar: int) -> str:
    """Setningen slik den står, uten løpende sidehode."""
    ren = E._SIDEHODE.sub(" ", seksjon)
    if aar == 2020:
        m = re.search(r"Antatt\s+tidspunkt\s+for\s+utvandring.{0,150}?\.", ren,
                      re.S)
    elif aar == 2021:
        m = re.search(r"Beregnet\s+tidspunkt\s+for\s+50\s*%\s*utvandring"
                      r".{0,100}?\)\.", ren, re.S)
    else:
        m = re.search(r"[Uu]tvandringsperioden\s+fra\s+elvene.{0,250}?"
                      r"(?:POet|produksjonsområdet)\.", ren, re.S)
    return " ".join(m.group(0).split()) if m else "(fant ikke setningen)"


def main() -> int:
    mappe = ARKIV_DIR / "ekspertgruppen"
    rader = []
    for aar, (merke, moenster, slash) in sorted(FORM.items()):
        fil = mappe / f"{aar}-12-31.bin.gz"
        if not fil.exists():
            print(f"\n{aar}: INGEN ARKIVERT KROPP ({fil.name})")
            continue
        raa = gzip.open(fil, "rb").read()
        sider = E._sider(raa, layout=False)
        flat = E._flat(sider)
        utg = E.gjenkjenn(sider[0])

        print("\n" + "=" * 78)
        print(f"{aar}  —  {utg.tittel}")
        print(f"        {merke}   ({len(sider)} sider)")
        print("=" * 78)

        seksjoner = E._seksjoner(flat)
        for po in sorted(seksjoner, key=int):
            seksjon = seksjoner[po]
            if aar == 2020:
                v = E._vindu(seksjon, aar)
            elif aar == 2021:
                v = E._vindu_2021(seksjon, aar)
            else:
                v = E._vindu_periode(seksjon, aar, moenster, slash)
            # Vakten kjøres også her, slik at tabellen ikke kan vise et
            # pent hull der kilden faktisk sa noe.
            E._krev_vindu(seksjon, v, po, aar)
            if not v:
                print(f"  PO{po:>2}   —  intet vindu oppgitt")
                continue
            side = _side_for(sider, po, aar)
            start = v.get(E.F_VINDU_START, "")
            slutt = v.get(E.F_VINDU_SLUTT, "")
            median = v.get(E.F_VINDU_MEDIAN, "")
            spenn = f"{start} .. {slutt}" if start else "(ingen datogrenser)"
            print(f"  PO{po:>2}   {spenn:<26}  median {median}   s. {side}")
            print(f"         «{_ordrett(seksjon, aar)}»")
            rader.append((aar, po, start, slutt, median))

    print("\n" + "=" * 78)
    print("OPPSUMMERING")
    print("=" * 78)
    per_aar: dict[int, int] = {}
    med_grenser: dict[int, int] = {}
    for aar, po, start, slutt, median in rader:
        per_aar[aar] = per_aar.get(aar, 0) + 1
        if start:
            med_grenser[aar] = med_grenser.get(aar, 0) + 1
    for aar in sorted(per_aar):
        print(f"  {aar}: {per_aar[aar]:2d} PO med median, "
              f"{med_grenser.get(aar, 0):2d} med start/slutt som datoer")

    # Er periodeformen den SAMME hvert år? Det er hovedfunnet, og det
    # skal telles og ikke påstås.
    print("\n  Er midtpunktet årsspesifikt? (dag-månad per PO, per år)")
    dagmnd: dict[int, dict[str, str]] = {}
    for aar, po, _s, _e, median in rader:
        dagmnd.setdefault(aar, {})[po] = median[5:]
    aarene = sorted(dagmnd)
    for a in aarene:
        for b in aarene:
            if a >= b:
                continue
            like = sum(1 for po in dagmnd[a]
                       if dagmnd[a].get(po) == dagmnd[b].get(po))
            felles = len(set(dagmnd[a]) & set(dagmnd[b]))
            print(f"    {a} mot {b}: {like}/{felles} PO har SAMME dag-måned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
