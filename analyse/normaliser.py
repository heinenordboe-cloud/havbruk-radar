"""Normaliserer PDF-utskriftene i `analyse/tekst/` til én linje per avsnitt.

Inngangen er `analyse/uttrekk_tekst.py` sin utskrift: pypdf legger et
linjeskift der PDF-en har en tekstlinje, og en tekstlinje i en A4-rapport
slutter midt i en setning. Et setningsuttrekk kan ikke kjøres på det.

Steget gjør NØYAKTIG tre ting, og ingenting mer:

  1. stripper etterhengende mellomrom på hver linje
  2. slår sammen linjene innenfor et avsnitt til én linje
     (tom linje = avsnittsskille, og beholdes som tom linje)
  3. slår sammen linjer der den forrige slutter med bindestrek

Ingen fjerning av sidetall, ingen sammenslåing av doble mellomrom, ingen
retting av «laksel us» og «post stsmolt». Slikt er tolkning, og tolkningen
hører hjemme i lesingen — ikke her. Det som ikke er linjeskift, står.

## Bindestrekregelen beholder bindestreken. Det er ikke det vanlige valget

Standardoppskriften på avstavning er å SLETTE bindestreken og skjøte
ordhalvdelene: «post-\\nsmolt» -> «postsmolt». Den oppskriften er feil for
disse kroppene, og målt feil — ikke antatt.

165 linjer i de åtte filene slutter med bindestrek. Gjennomgått én for én
er ingen av dem utvetydig avstavning. De er:

  - talløyer:      «(0-10 %, 10-» + «30 % eller > 30 %»   -> «10-30 %»
  - sammensatte:   «ROC-» + «indeks», «VPS-» + «modell»
  - egennavn:      «Nord-» + «Norge»
  - sidetall:      «Interactions 5: 1-» + «16.»
  - URL-er:        «...basis-of-the-» + «traffic-light-system...»
  - tabellstreker: «13 0-10 % Nei -» + « -»

Sletter man bindestreken her, blir «10-30 %» til «1030 %» — og det er
nøyaktig tokenet `terskelordlyd.py` leter etter i neste steg. Skjøter man
med et mellomrom i stedet, blir det «10- 30 %». Begge er en påstand om
kilden som kilden ikke har gjort.

Det finnes en håndfull tilfeller som LIGNER avstavning — «Trål-» +
«fangst», «Smitte-» + «press», «lakselus-» + «indusert» — alle fra smale
tabelloverskrifter. De er ikke til å skille fra en ekte sammensetning med
bindestrek, og de samme tabellene bryter ord UTEN bindestrek også
(«Konklus» + «jon1» i 2017-kroppen). Det finnes altså ikke noe signal å
avgjøre saken på; en regel som gjettet ville vært CLAUDE.md 1b-2 om igjen
— et mål som LIGNER det den skal måle, og som er riktig helt til det ikke
er det. Prisen for å ta feil er asymmetrisk: «Trål-fangst» er lesbart,
«1030 %» er en oppdiktet verdi.

Derfor: linjene skjøtes uten mellomrom, og bindestreken blir stående.
Tegnene i fila er kildens egne.

## Vakten måler tegn UTEN mellomrom

Sammenslåingen fjerner linjeskift og etterhengende mellomrom, og legger
ett mellomrom mellom skjøtte linjer. Teller man alle tegn, faller tallet
uansett, og et fall kan da ikke skille «vi fjernet linjeskift» fra «vi
spiste et avsnitt». Trekker man mellomrom fra på begge sider, skal tallet
stå tilnærmet stille — regelen over fjerner ingen synlige tegn i det hele
tatt. Gulvet på 95 % er derfor romslig med vilje: slår det ut, er det
innhold som er borte, ikke avrunding.
"""

from __future__ import annotations

import sys
from pathlib import Path

INN_DIR = Path(__file__).resolve().parent / "tekst"
UT_DIR = Path(__file__).resolve().parent / "tekst-norm"

# Andel av kildens tegn (mellomrom trukket fra) som må overleve.
GULV = 0.95


def _tegn(tekst: str) -> int:
    """Antall tegn når alt som er mellomrom er trukket fra."""
    return len("".join(tekst.split()))


def normaliser(tekst: str) -> tuple[str, int]:
    """Rå PDF-utskrift -> (én linje per avsnitt, antall bindestreksskjøter)."""
    ut: list[str] = []
    avsnitt: list[str] = []
    bindestreker = 0

    for rå in tekst.split("\n"):
        linje = rå.rstrip()
        if not linje:
            if avsnitt:
                ut.append("".join(avsnitt))
                avsnitt = []
            ut.append("")
            continue

        if not avsnitt:
            avsnitt.append(linje)
        elif avsnitt[-1].endswith("-"):
            bindestreker += 1
            avsnitt.append(linje)
        else:
            avsnitt.append(" " + linje)

    if avsnitt:
        ut.append("".join(avsnitt))

    return "\n".join(ut), bindestreker


def main() -> int:
    kilder = sorted(INN_DIR.glob("*.txt"))
    if not kilder:
        print(f"Fant ingen txt-filer i {INN_DIR}", file=sys.stderr)
        return 1

    UT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{len(kilder)} filer i {INN_DIR}\n")
    print(f"{'fil':<12}{'tegn før':>12}{'tegn etter':>12}"
          f"{'u/mellomrom':>14}{'andel':>9}{'bindestrek':>12}")
    print("-" * 71)

    sum_bindestreker = 0
    for kilde in kilder:
        rå = kilde.read_text(encoding="utf-8")
        norm, bindestreker = normaliser(rå)
        sum_bindestreker += bindestreker

        før, etter = _tegn(rå), _tegn(norm)
        andel = etter / før if før else 1.0
        if andel < GULV:
            raise SystemExit(
                f"{kilde.name}: normaliseringen spiste innhold — "
                f"{etter} av {før} tegn uten mellomrom ({andel:.1%}), "
                f"gulvet er {GULV:.0%}")

        (UT_DIR / kilde.name).write_text(norm, encoding="utf-8")
        print(f"{kilde.name:<12}{len(rå):>12}{len(norm):>12}"
              f"{etter:>8}/{før:<5}{andel:>8.1%}{bindestreker:>12}")

    print()
    if sum_bindestreker == 0:
        print("Ingen bindestreksskjøter i noen av de åtte filene. "
              "Regelen er død kode og skal fjernes.")
    else:
        print(f"{sum_bindestreker} bindestreksskjøter totalt. Bindestreken "
              f"BEHOLDES — se modulens docstring for hvorfor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
