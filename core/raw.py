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


def hashene(kilde: str) -> set[str]:
    """sha256 av alt som allerede ligger arkivert for kilden.

    Leser og hasher filene. Det er greit her: funksjonen kalles én gang
    per kjøring, ikke én gang per periode, og arkivet for en månedlig
    kilde er titalls filer — ikke titusener.
    """
    mappe = ARKIV_DIR / kilde
    if not mappe.exists():
        return set()
    ut = set()
    for sti in mappe.glob("*.gz"):
        with gzip.open(sti, "rb") as f:
            ut.add(hashlib.sha256(f.read()).hexdigest())
    return ut


def arkiver_ny(kilde: str, observed_at: str, raw: Any) -> tuple[str, bool]:
    """Arkiverer råsvaret HVIS innholdet ikke allerede ligger der.
    Returnerer (sha256, ble_skrevet).

    Regelen `arkiver()` følger er «hver skriving blir en fil». Den er
    riktig for den løpende jobben, som henter én ny publisering hver
    gang. Den er feil for en REVISJONSKJØRING: den leser den samme
    publiseringen som månedsjobben allerede arkiverte, og ville lagt igjen
    en identisk 200 kB-kopi hver måned for å dokumentere ingenting.

    Regelen her er én linje lengre og lettere å huske: **hver DISTINKTE
    kropp vi laster ned arkiveres nøyaktig én gang.** Den fanger også
    tilfellet ingen tenker på — at revisjonskjøringen leser en kropp
    månedsjobben ikke rakk, fordi den var rød — for da er hashen ny, og
    kroppen skrives.

    Hashen returneres uansett, og det er den som havner på radene.
    `raw_hash` er innholdsadressert (se modulens docstring), så et
    snapshot som peker på en arkivfil skrevet av en TIDLIGERE kjøring er
    en sann påstand om hvor det kom fra.
    """
    data, _ = _serialiser(raw)
    sha = hashlib.sha256(data).hexdigest()
    if sha in hashene(kilde):
        return sha, False
    return arkiver(kilde, observed_at, raw), True
