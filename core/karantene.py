"""Felles kroppssjekk med karantene.

    grunner = karantene.vurder(kropp, [karantene.ikke_tom, karantene.html])
    if grunner:
        post = karantene.sett_inn("auksjon", dato, kropp, grunner, jobb="auksjon")
        ...                                   # og kjøringen ender med exit 1

En kropp går aldri tapt, men en mistenkt kropp kommer aldri inn i serien.

## Hvorfor

MALING-DRIFT (02.11.2026): tre fangstjobber lagret en feilside, en tom
liste og en halv kropp som nye kropper, og endte grønne. En grønn kjøring
med en feilside i arkivet er nøyaktig den stillheten tilsynet ikke kan se.

To krav trekker hver sin vei, og karantenen holder begge:

  * En kropp går aldri tapt. Et svar som ikke ble lagret, kan ikke hentes
    igjen (CLAUDE.md regel 5), og en regel som tar feil, skal ikke koste
    kroppen den tok feil om.
  * En mistenkt kropp kommer aldri inn i serien. Der blir den forrige
    versjon for neste sammenligning, hashen den bærer blir «allerede
    arkivert», og innholdet blir en påstand.

## Hvorfor dette er kjernen og ikke en kilde

En ny kilde er én fil i sources/ (regel 1). Dette er ikke en kilde, men
oppførsel hver fangstjobb og hver ny kilde skal dele: hva som er en
mistenkt kropp, hvor den lagres, hva posten sier, og at kjøringen blir
rød. Sto det i hvert skript, ville det vært sju beskrivelser av samme
ting, og den ene som drev fra de andre ville vært formen F6 og F7 hadde.
Kilder melder fra med `Mistenkt`; jobbene og `runner.run_all` legger
kroppen i karantene.

## Hvor karantenen ligger

`data/arkiv/<mappe>/karantene/`, i jobbens egen arkivmappe:

  * UTENFOR serien. Alt som leser en serie — `raw.kropper()`,
    `raw.hashene()`, `backfill.py`, `unntaksanalyse.py` — globber `*.gz` i
    TOPPEN av mappa. En undermappe er ikke med.
  * INNENFOR det jobbens workflow allerede committer (`git add -A --
    data/arkiv/<mappe>`), også når skriptet er rødt. Ingen workflow må
    endres for at kroppen skal overleve runneren. Unntaket er daglig.yml,
    som bare legger til navn som matcher `*.daglig.*` i toppen av mappa:
    en kropp med merke havner derfor i `karantene.<merke>.d/`.
  * Under data/arkiv/, så arkivvakten verner den og stempel.py
    tidsstempler den som alt annet der.

## Hva som lagres

To filer per kropp, begge skrevet én gang og aldri om (regel 2):

    <dato>[.N].<ext>.gz         kroppen, serialisert som raw.arkiver() gjør
    <dato>[.N].<ext>.gz.json    posten: sha256, status «karantene», grunn

`status` er «karantene», samme felt som «ny» og «uendret» i jobbenes
logger. HTTP-statusen står i `http_status` der jobben kjenner den.

## Ut av karantenen

Bare med en skrevet kvittering, `<kropp>.kvittert.json`, laget av
`karantene.py --kvitter`. Den sier «avvist» (kroppen var feil og blir
liggende) eller «godtatt» (regelen tok feil, og kroppen skrives inn i
serien). Uten kvittering er tilsynet rødt (`.github/tilsyn.py` i
datarepoet leser de samme navnene). Ingenting flytter seg av seg selv
(CLAUDE.md 1b-4).
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import html as html_modul
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable

from core import persondata
from core import raw as raw_arkiv

Regel = Callable[[bytes], "str | None"]

STATUS = "karantene"
MAPPE = "karantene"
POST = ".json"
KVITTERING = ".kvittert.json"
UTFALL = ("avvist", "godtatt")


class Mistenkt(Exception):
    """En kropp som ikke skal inn i serien, med grunnen og kroppen.

    Kastes av en kildes `fetch()` eller `parse()`. Kroppen er med fordi en
    vanlig exception i `fetch()` tar den med seg: `runner.run_all`
    arkiverer det `fetch()` RETURNERER, og det daglige arkivet likeså. Med
    kroppen på unntaket kan kalleren legge den i karantene i stedet.
    """

    def __init__(self, grunn: str, kropp: Any = None):
        super().__init__(grunn)
        self.grunn = grunn
        self.kropp = kropp


# ---------------------------------------------------------------- reglene
#
# Hver regel tar kroppen som bytes og svarer med grunnen, eller None når
# den ikke har noe å utsette. Grunnen er en setning en leser av posten
# skal forstå uten koden.

def synlig_tekst(kropp: bytes) -> str:
    """Teksten en leser ser, uten skript, stil og tagger. Grovt med vilje:
    den skal bare kunne si om ordene er de samme som sist, og om de er der.

    Flyttet hit fra arkiver_vilkar.py 03.11.2026, uendret, så teksthashene
    i loggene fra før er de samme."""
    t = kropp.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return " ".join(html_modul.unescape(t).split())


def ikke_tom(kropp: bytes) -> str | None:
    """Null byte, eller bare blanktegn."""
    return None if kropp.strip() else f"tom kropp ({len(kropp)} B)"


def html(kropp: bytes) -> str | None:
    """`<html` et sted i kroppen, uten store/små bokstaver."""
    return None if b"<html" in kropp.lower() else "ingen <html i kroppen"


def nevner(ord_: str) -> Regel:
    """Ordet i den synlige teksten, uten store/små bokstaver."""
    def regel(kropp: bytes) -> str | None:
        if ord_.casefold() in synlig_tekst(kropp).casefold():
            return None
        return f"synlig tekst nevner ikke «{ord_}»"
    regel.__name__ = f"nevner({ord_!r})"
    return regel


def minst_tekst(tegn: int) -> Regel:
    """Minst `tegn` tegn synlig tekst."""
    def regel(kropp: bytes) -> str | None:
        n = len(synlig_tekst(kropp))
        return None if n >= tegn else (
            f"synlig tekst {n} tegn, under minstelengden {tegn}")
    regel.__name__ = f"minst_tekst({tegn})"
    return regel


def andel_av_forrige(forrige: bytes, andel: float = 0.5) -> Regel:
    """Synlig tekst minst `andel` av den forrige versjonens."""
    f = len(synlig_tekst(forrige))

    def regel(kropp: bytes) -> str | None:
        n = len(synlig_tekst(kropp))
        return None if n >= andel * f else (
            f"synlig tekst {n} tegn, under {andel:.0%} av forrige versjon "
            f"({f} tegn)")
    regel.__name__ = f"andel_av_forrige({andel})"
    return regel


def vurder(kropp: bytes, regler: Iterable[Regel]) -> list[str]:
    """Grunnene, i reglenes rekkefølge. Tom liste: ingenting å utsette."""
    return [g for regel in regler if (g := regel(kropp))]


# ---------------------------------------------------------------- lagringen

def mappe_for(arkivmappe: str, merke: str = "") -> Path:
    """Karantenemappa for en arkivmappe. Se modulens docstring for `.d`."""
    navn = f"{MAPPE}.{merke}.d" if merke else MAPPE
    return raw_arkiv.ARKIV_DIR / arkivmappe / navn


def _skriv_en_gang(sti: Path, data: bytes) -> None:
    fd = os.open(sti, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def sett_inn(arkivmappe: str, observed_at: str, raw: Any,
             grunn: str | list[str], *, merke: str = "", jobb: str = "",
             fetched_at: str = "", **meta: Any) -> dict:
    """Legger kroppen i karantene og returnerer posten, til jobbens logg.

    Skriver `::error::`. Kalleren skal i tillegg ende med exit 1 — det er
    kallerens exit-kode, og den samler som regel flere ting.

    Nekter en kropp med kontaktfelt, som `raw.arkiver()` gjør: karantenen
    ligger i samme datarepo og skrives like append-only (regel 3).
    """
    persondata.nekt_kontaktfelt(arkivmappe, raw)
    data, ext = raw_arkiv._serialiser(raw)
    grunner = [grunn] if isinstance(grunn, str) else list(grunn)
    sha = hashlib.sha256(data).hexdigest()

    mappe = mappe_for(arkivmappe, merke)
    mappe.mkdir(parents=True, exist_ok=True)
    stamme = f"{observed_at}.{merke}" if merke else observed_at
    n = 1
    while True:
        navn = f"{stamme}.{ext}.gz" if n == 1 else f"{stamme}.{n}.{ext}.gz"
        sti = mappe / navn
        try:
            _skriv_en_gang(sti, gzip.compress(data, compresslevel=9, mtime=0))
            break
        except FileExistsError:
            n += 1

    post = {
        "status": STATUS,
        "grunn": grunner,
        "kilde": arkivmappe,
        "observed_at": observed_at,
        # Når VI hentet kroppen (1b-7). Jobben vet det best; ellers nå.
        "fetched_at": fetched_at or dt.datetime.now(dt.timezone.utc)
                                     .isoformat(timespec="seconds"),
        "sha256": sha,
        "byte": len(data),
        "fil": sti.relative_to(raw_arkiv.ARKIV_DIR).as_posix(),
        "jobb": jobb,
        **meta,
    }
    _skriv_en_gang(sti.with_name(sti.name + POST),
                   (json.dumps(post, indent=2, ensure_ascii=False) + "\n")
                   .encode("utf-8"))
    print(f"::error::Karantene ({jobb or arkivmappe}): {observed_at}: "
          f"{'; '.join(grunner)}. Kroppen ({len(data)} B, sha256 {sha[:16]}…) "
          f"ligger i data/arkiv/{post['fil']} og er IKKE i serien. Se "
          f"karantene.py for kvittering.")
    return post


def poster(arkiv_dir: Path | None = None) -> list[tuple[Path, dict, dict | None]]:
    """(kroppen, posten, kvitteringen eller None) for hver kropp i karantene."""
    rot = arkiv_dir or raw_arkiv.ARKIV_DIR
    ut = []
    for p in sorted(rot.glob(f"*/{MAPPE}*/*.gz{POST}")):
        kropp = p.with_name(p.name[: -len(POST)])
        kv = kropp.with_name(kropp.name + KVITTERING)
        ut.append((kropp, json.loads(p.read_text(encoding="utf-8")),
                   json.loads(kv.read_text(encoding="utf-8")) if kv.exists() else None))
    return ut


def kvitter(kropp: Path, utfall: str, grunn: str) -> dict:
    """Skriver kvitteringen. «godtatt» skriver også kroppen inn i serien.

    Kroppen leses og sjekkes mot posten først: en kvittering for en kropp
    som ikke er den posten beskriver, ville vært en påstand om noe annet.
    """
    if utfall not in UTFALL:
        raise ValueError(f"utfall må være ett av {UTFALL}, ikke {utfall!r}")
    if not grunn.strip():
        raise ValueError("en kvittering uten grunn sier ikke hva som ble avgjort")
    post = json.loads(kropp.with_name(kropp.name + POST).read_text(encoding="utf-8"))
    data = gzip.decompress(kropp.read_bytes())
    if hashlib.sha256(data).hexdigest() != post["sha256"]:
        raise ValueError(f"{kropp.name}: kroppen stemmer ikke med posten")

    kv = {"kvittert": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
          "utfall": utfall, "grunn": grunn.strip(), "sha256": post["sha256"]}
    if utfall == "godtatt":
        kv["skrevet_til"] = _inn_i_serien(kropp, post, data)
    _skriv_en_gang(kropp.with_name(kropp.name + KVITTERING),
                   (json.dumps(kv, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return kv


def _inn_i_serien(kropp: Path, post: dict, data: bytes) -> str:
    """Kroppen inn i serien, med samme filtype og merke den ble hentet med,
    og bare når de samme bytene ikke ligger der fra før."""
    arkivmappe = post["kilde"]
    ext = kropp.name.removesuffix(".gz").rsplit(".", 1)[-1]
    raw = (json.loads(data) if ext == "json" else
           data.decode("utf-8") if ext == "txt" else data)
    if raw_arkiv._serialiser(raw)[0] != data:
        raise ValueError(f"{kropp.name}: kroppen lar seg ikke skrive tilbake "
                         f"med de samme bytene")
    if post["sha256"] in raw_arkiv.hashene(arkivmappe):
        return ""
    merke = kropp.parent.name.removeprefix(f"{MAPPE}.").removesuffix(".d") \
        if kropp.parent.name != MAPPE else ""
    sti = raw_arkiv._ledig_sti(arkivmappe, post["observed_at"], ext, merke)
    raw_arkiv.arkiver(arkivmappe, post["observed_at"], raw, merke)
    return sti.relative_to(raw_arkiv.ARKIV_DIR).as_posix()
