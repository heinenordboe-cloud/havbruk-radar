"""Rå-arkiv. Skrives før parse(), aldri om.

Uten dette er hver feil i parse() permanent datatap: kildene overskriver
seg selv, så et feiltolket felt oppdaget i uke 30 kan ikke rettes for
ukene før. Med arkivet er samme feil en re-parse.

Filnavnet er datoen. Kjøres samme dato flere ganger, får de neste et
løpenummer — ingenting overskrives.
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
