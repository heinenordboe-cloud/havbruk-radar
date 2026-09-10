"""Skriver ut ren tekst fra de arkiverte ekspertgruppe-rapportene.

Ett steg, med vilje: gzip -> pypdf -> tekst -> `analyse/tekst/<aar>.txt`.
Ingen mønstre, ingen tolkning, ingen uttrekk. Alt som skal LESES ut av
rapportene hører hjemme i et senere steg som tar disse filene som
inngang — da kan uttrekket kjøres om igjen uten å røre PDF-ene.

Kroppene leses fra `data/arkiv/ekspertgruppen/` i datarepoet, ikke fra
snapshots. Spørsmålet et senere steg skal kunne stille er hva kilden SA,
og det står bare i kroppen.

## Årstallet i filnavnet er KROPPENS år, ikke vurderingsårets

Arkivfilene heter `<nyeste vurderingsår>-12-31.bin.gz`, og flere av
kroppene uttaler seg om mer enn ett år: 2016+2017-rapporten ligger som
`2017-12-31`, og 2025-rapporten dekker også 2024. Utskriften arver det
navnet uendret — én txt-fil per KROPP. Å døpe filene etter vurderingsår
ville krevd en mening om hvilken rapport som «eier» 2024, og det er
nettopp en tolkning dette steget ikke skal gjøre.

## `extraction_mode` er standard, ikke "layout"

`sources/ekspertgruppen.py` leser tabellene med `extraction_mode="layout"`
fordi kolonneposisjonene bærer betydning der. Her er valget bevisst det
motsatte: standardmodus er det rette tekstuttrekket, og layout er en
tilpasning til en bestemt lesemåte. Trenger et senere steg kolonnene,
er det steget som skal be om dem.

Merk følgen, så den ikke kommer som en overraskelse: tabeller kommer ut
som en tokenstrøm uten kolonner. Prosaen er intakt.
"""

from __future__ import annotations

import gzip
import io
import logging
import sys
from pathlib import Path

import pypdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.paths import ARKIV_DIR  # noqa: E402

KILDE = "ekspertgruppen"
UT_DIR = Path(__file__).resolve().parent / "tekst"


def _les_kropp(sti: Path) -> tuple[int, str]:
    """Rå PDF-bytes -> (antall sider, tekst side for side).

    2023-kroppen fra Nasjonalt vitenarkiv er AES-kryptert med TOM
    passordstreng — den er ikke passordbeskyttet i praksis, bare
    kryptert ved lagring. `decrypt("")` er derfor ikke et forsøk på å
    bryte noe; det er den dokumenterte veien inn i en slik fil, og den
    krever `cryptography` (se requirements.txt).
    """
    rå = gzip.open(sti, "rb").read()
    leser = pypdf.PdfReader(io.BytesIO(rå))
    if leser.is_encrypted:
        leser.decrypt("")
    return len(leser.pages), "\n".join(
        (side.extract_text() or "") for side in leser.pages)


def main() -> int:
    # pypdf klager høylytt om objektpekere i flere av kroppene. Det er
    # ikke feil vi kan gjøre noe med — kroppen er som den er — og støyen
    # ville druknet tegntallene.
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    kilde_dir = ARKIV_DIR / KILDE
    kropper = sorted(kilde_dir.glob("*.bin.gz"))
    if not kropper:
        print(f"Fant ingen kropper i {kilde_dir}", file=sys.stderr)
        return 1

    UT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{len(kropper)} kropper i {kilde_dir}\n")
    print(f"{'fil':<16}{'sider':>7}{'tegn':>12}")
    print("-" * 35)

    for kropp in kropper:
        aar = kropp.name.split("-")[0]
        sider, tekst = _les_kropp(kropp)

        ut = UT_DIR / f"{aar}.txt"
        ut.write_text(tekst, encoding="utf-8")
        print(f"{ut.name:<16}{sider:>7}{len(tekst):>12}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
