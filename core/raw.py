"""Rå-arkiv. Skrives før parse(), aldri om.

Uten dette er hver feil i parse() permanent datatap: kildene overskriver
seg selv, så et feiltolket felt oppdaget i uke 30 kan ikke rettes for
ukene før. Med arkivet er samme feil en re-parse.

Filnavnet er datoen. Kjøres samme dato flere ganger, får de neste et
løpenummer — ingenting overskrives.

VIKTIG: `raw_hash` på en Observation er INNHOLDSADRESSERT, ikke
filnavnsadressert. Den sier hvilket råsvar observasjonen kom fra, ikke
hvilken fil det ligger i.

Vil du finne arkivfila for en observasjon, hash arkivfilene og match på
innhold:

    gzip.open(fil, "rb").read()  ->  hashlib.sha256(...).hexdigest()

Ikke match løpenummer mot løpenummer. De to tellerne teller forskjellige
ting og vil aldri holde tritt: arkivet skrives før parse(), snapshotet
etter, så hver henting som ikke ender i et snapshot (parse-feil, et
snapshot som forkastes) legger igjen en arkivfil uten motstykke. Målt i
datarepoet 17.08.2026 var forskyvningen allerede én: snapshot `.2`
tilhørte arkiv `.3`, `.3` tilhørte `.4`, `.4` tilhørte `.5`.

Flere arkivfiler kan dele hash når råsvaret er byte-identisk mellom
kjøringer. Det er ikke flertydighet som betyr noe — innholdet er det
samme, og en re-parse gir samme resultat uansett hvilken du åpner.
"""

import gzip
import hashlib
import json
from typing import Any

from core.paths import ARKIV_DIR


def _serialiser(raw: Any) -> tuple[bytes, str]:
    """fetch() er typet Any, så en kilde kan returnere CSV eller bytes
    like gjerne som JSON."""
    if isinstance(raw, bytes):
        return raw, "bin"
    if isinstance(raw, str):
        return raw.encode("utf-8"), "txt"
    # sort_keys: uten den kan samme respons gi ulik hash mellom kjøringer.
    return json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8"), "json"


def _ledig_sti(kilde: str, observed_at: str, ext: str):
    mappe = ARKIV_DIR / kilde
    mappe.mkdir(parents=True, exist_ok=True)

    sti = mappe / f"{observed_at}.{ext}.gz"
    if not sti.exists():
        return sti

    n = 2
    while True:
        sti = mappe / f"{observed_at}.{n}.{ext}.gz"
        if not sti.exists():
            return sti
        n += 1


def arkiver(kilde: str, observed_at: str, raw: Any) -> str:
    """Skriver råsvaret gzippet. Returnerer sha256 av innholdet."""
    data, ext = _serialiser(raw)
    sti = _ledig_sti(kilde, observed_at, ext)

    with gzip.open(sti, "wb", compresslevel=9) as f:
        f.write(data)

    return hashlib.sha256(data).hexdigest()
