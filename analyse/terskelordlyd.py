"""Trekker ut hver setning i `analyse/tekst-norm/` som kobler et prosenttall
til terskelordlyd.

Spørsmålet steget skal gjøre besvarbart er hvordan ekspertgruppen har
FORMULERT grensene mellom lav, moderat og høy dødelighet, og om ordlyden
har flyttet seg mellom kroppene. Steget svarer ikke på det — det legger
setningene på bordet.

## Ingen normalisering av innholdet

«0-10 %», «under 10 %» og «lavere enn 10 prosent» skal stå som tre rader,
ikke som én verdi. Skillet mellom FORM og VERDI er en lesning, og
lesningen gjøres av mennesket etterpå. Setningene skrives ut ordrett slik
de står i `tekst-norm/`, med kildefil og setningsnummer, slik at hver rad
kan slås opp igjen i fila.

Steget leser BARE `tekst-norm/`. Ikke PDF-ene, ikke `tekst/`. Trenger et
uttrekk noe som ikke overlevde normaliseringen, er det normaliseringen
som skal endres — ikke dette steget som skal få en egen vei inn til
kilden. Da får man to uttrekk som kan svare ulikt om samme kropp.

## De tre mønstrene, og hva de IKKE fanger

  prosenttall   `\\d` etterfulgt av valgfritt mellomrom og `%`.
                Fanger «10 %», «10-30 %», «> 30 %», «0,2 %».
                Fanger IKKE «30 prosent» skrevet med bokstaver. Ordet
                «prosent» står 74 ganger i de åtte kroppene, mest som
                «prosentpoeng» og «prosentandel» uten tall foran. Å ta
                det med ville utvidet uttrekket fra et tegn til en
                ordliste, og ordlister er tolkning.

  ordlyd        delstreng, uten hensyn til store/små bokstaver, av:
                dødelighet, terskel, grense, kategori, lav, moderat, høy.
                Delstreng med vilje: «grense» skal fange «lusegrense» og
                «kategorigrensene», «høy» skal fange «høyere» og
                «høyeste». Prisen er treff som «Lavangen» og «slave».
                Et uttrekk som er for vidt kan leses og forkastes; et som
                er for smalt er stille. Regel 4-holdningen, én etasje ned.

  setning       deling etter `.`, `!` eller `?` fulgt av mellomrom og en
                STOR forbokstav. Sifferkravet er det som holder «mfl.
                2021», «ca. 30 %» og «Nr. 39» samlet. Det holder ikke
                «jf. Tabell 3» samlet — der deles setningen på feil sted,
                og det er en KJENT svakhet, ikke en usett.

Merk at tabellene kommer ut av pypdf som en tokenstrøm uten kolonner (se
`uttrekk_tekst.py`). En «setning» fra et tabellavsnitt er derfor en
radstrøm, ikke prosa. Den utelates ikke — den er ofte nettopp der
kategorigrensene står — men den skal leses som det den er.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

INN_DIR = Path(__file__).resolve().parent / "tekst-norm"
UT_FIL = Path(__file__).resolve().parent / "fasit" / "terskelordlyd.md"

PROSENT = re.compile(r"\d\s*%")

ORDLYD = ("dødelighet", "terskel", "grense", "kategori", "lav", "moderat",
          "høy")

# Setningsslutt: .!? + eventuelle sitat-/parentestegn, mellomrom, og en
# stor forbokstav (eventuelt bak et åpningstegn).
SETNINGSSKILLE = re.compile(
    r'(?<=[.!?])["\'»”\)\]]*\s+(?=[«"\'\(\[]*[A-ZÆØÅ])')


def setninger(tekst: str) -> list[str]:
    """Normalisert tekst -> setninger, i rekkefølge, tomme fjernet."""
    ut: list[str] = []
    for avsnitt in tekst.split("\n"):
        avsnitt = avsnitt.strip()
        if not avsnitt:
            continue
        ut.extend(s.strip() for s in SETNINGSSKILLE.split(avsnitt) if s.strip())
    return ut


def treff(setning: str) -> list[str]:
    """Hvilke ordlydsord setningen inneholder — tom liste = ikke et treff."""
    if not PROSENT.search(setning):
        return []
    lav = setning.casefold()
    return [ord_ for ord_ in ORDLYD if ord_ in lav]


def main() -> int:
    kilder = sorted(INN_DIR.glob("*.txt"))
    if not kilder:
        print(f"Fant ingen txt-filer i {INN_DIR}. Kjør normaliser.py først.",
              file=sys.stderr)
        return 1

    funn: dict[str, list[tuple[int, str, list[str]]]] = {}
    antall_setninger: dict[str, int] = {}

    for kilde in kilder:
        alle = setninger(kilde.read_text(encoding="utf-8"))
        antall_setninger[kilde.name] = len(alle)
        funn[kilde.name] = [
            (nr, s, ord_) for nr, s in enumerate(alle, start=1)
            if (ord_ := treff(s))
        ]

    linjer: list[str] = [
        "# Terskelordlyd i ekspertgruppe-kroppene",
        "",
        "Hver setning i `analyse/tekst-norm/` som inneholder et prosenttall",
        "(`\\d` + `%`) sammen med minst ett av: dødelighet, terskel, grense,",
        "kategori, lav, moderat, høy. Delstreng, uten hensyn til",
        "store/små bokstaver.",
        "",
        "Ordrett fra kilden. Ingen normalisering av innholdet — to",
        "formuleringer som betyr det samme står som to rader. Årstallet i",
        "filnavnet er KROPPENS år, ikke vurderingsårets.",
        "",
        "Generert av `analyse/terskelordlyd.py`.",
        "",
        "## Treff per fil",
        "",
        "| fil | setninger i fila | treff |",
        "| --- | ---: | ---: |",
    ]
    for navn in sorted(funn):
        linjer.append(f"| {navn} | {antall_setninger[navn]} | "
                      f"{len(funn[navn])} |")
    linjer += ["", f"**Sum:** {sum(len(v) for v in funn.values())} treff i "
               f"{len(funn)} filer.", ""]

    for navn in sorted(funn):
        linjer += [f"## {navn}", ""]
        if not funn[navn]:
            linjer += ["Ingen treff.", ""]
            continue
        for nr, setning, ord_ in funn[navn]:
            linjer.append(f"- **{navn}:{nr}** _({', '.join(ord_)})_  ")
            linjer.append(f"  {setning}")
        linjer.append("")

    UT_FIL.parent.mkdir(parents=True, exist_ok=True)
    UT_FIL.write_text("\n".join(linjer) + "\n", encoding="utf-8")

    # Bare tall til terminalen. Setningene står i fila, og en dump av dem
    # her ville vært lesing forkledd som kjøring.
    print(f"{len(kilder)} filer i {INN_DIR}\n")
    print(f"{'fil':<12}{'setninger':>12}{'treff':>8}")
    print("-" * 32)
    for navn in sorted(funn):
        merknad = "" if funn[navn] else "   <- ingen treff"
        print(f"{navn:<12}{antall_setninger[navn]:>12}"
              f"{len(funn[navn]):>8}{merknad}")
    print(f"\nSkrevet: {UT_FIL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
