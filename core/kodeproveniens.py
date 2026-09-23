"""Hvilken KODE som skrev et øyeblikksbilde.

## Hvorfor dette finnes: F15, to ganger

`fetched_at` sier når vi spurte. `source_version` sier hvilken versjon
kilden selv oppga. Ingen av dem sier hvilken kode som kjørte, og det er
ikke en teoretisk mangel:

**F15 (21.09.2026).** 47 commits lå ucommitet-men-upushet i to uker.
Den ukentlige innsamlingen kjører fra det som er PUSHET, og kjørte
derfor kode fra før 16.09. Grensa ved SSB-sektor 2300 var ikke aktiv, og
mandagens snapshot ble skrevet med personformer i seg.

**Andre gang (23.09.2026).** `sources/eierskap.fjern_egne_personer()`
utelot `eier_type` med begrunnelsen at «en slik rad forsvinner fra neste
snapshot av seg selv». MÅLT: `parse()` dropper H-FJ-0018 fra
arkivkroppene både 14.09 og 21.09 — men snapshotet 21.09 har den
likevel, fordi kjøringen brukte den gamle koden. Feilen var usynlig i
dataene: ingenting i fila sier hvilken kode som skrev den.

Kilden hadde selv skrevet ned symptomet et år før symptomet:

> «snapshotene som alt ligger på disk er skrevet av to ulike filtre og
> bærer BEGGE `source_version = "1"`. De er ikke til å skille fra
> hverandre i dataene, bare på `fetched_at`.»

## Regelen den håndhever

CLAUDE.md 1b-3: **kan et snapshot alene svare på hva denne verdien var
da raden ble skrevet?** Kan det ikke det, skal verdien stemples på
raden — som `fetched_at`, `source_version`, `raw_hash` og `utvalg`.

Hvilken kode som kjørte er nøyaktig en slik verdi. Den avgjør hva
dataene BETYR: samme kropp gir 1934 eller 2611 overføringer alt etter
hvilket filter som leste den.

## Tre ting, ikke ett

    kode_commit   sha for HEAD da fila ble skrevet
    kode_rent     «ja» hvis arbeidstreet var rent, «nei» ellers

Og det tredje står ikke i fila, fordi det handler om verden og ikke om
raden: **om commiten finnes på `origin/main`.** Det kan endre seg etter
at fila er skrevet (en commit kan bli pushet senere), så det spørres på
nytt hver gang porten kjører. Se `publiseringsvakt`.
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent

# Verdiene `kode_rent` kan ha. Ikke booleans: kolonnen er tekst som alt
# annet i skjemaet, og en tom streng må kunne bety «vet ikke» — som for
# `utvalg` og `published_at`.
RENT = "ja"
URENT = "nei"
UKJENT = ""


class IkkeSporbar(RuntimeError):
    """Koden som skulle kjøre kan ikke gjøres rede for.

    Reises av `krev_sporbar()`, som innsamlingen kaller FØR den henter
    noe. Den skal stoppe høylytt: en kjøring som skriver et snapshot
    ingen kan spore tilbake til kode, lager en fil som er
    uetterprøvbar for alltid — og append-only betyr at den ikke kan
    rettes etterpå.
    """


def _git(*args: str) -> str:
    """Git-utdata som tekst, eller tom streng om kommandoen ikke svarer.

    Tom streng og ikke et unntak: modulen skal kunne importeres og
    testes utenfor et git-arbeidstre. Den som KREVER sporbarhet kaller
    `krev_sporbar()`, som gjør fraværet til en feil.
    """
    try:
        ut = subprocess.run(("git", *args), cwd=ROT, capture_output=True,
                            text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return ut.stdout.strip() if ut.returncode == 0 else ""


def commit() -> str:
    """sha for HEAD, eller tom streng."""
    return _git("rev-parse", "HEAD")


def rent() -> str:
    """`RENT` hvis arbeidstreet er rent, `URENT` hvis ikke, `UKJENT` ellers.

    `status --porcelain` teller BÅDE usporede og endrede filer. En
    usporet fil er ikke uskyldig: en ny `sources/*.py` som ikke er
    committet, er kode som kjører og som ingen kan finne igjen.
    """
    if not commit():
        return UKJENT
    ut = _git("status", "--porcelain")
    return URENT if ut else RENT


@lru_cache(maxsize=4)
def paa_origin_main(sha: str) -> bool:
    """Er denne commiten en stamfar til `origin/main`?

    Det er spørsmålet «kjørte dette fra noe alle kan se», og det er et
    annet spørsmål enn «finnes commiten lokalt». F15 var nettopp en
    commit som fantes lokalt og ikke hos noen andre.

    Svaret kan endre seg over tid — en commit som ikke var pushet da
    fila ble skrevet, kan være pushet i dag — og derfor lagres det ikke
    i fila. Det spørres på nytt.
    """
    if not sha:
        return False
    # `merge-base --is-ancestor` gir exit 0 for ja, 1 for nei. `_git()`
    # skiller dem ikke, så kallet gjøres direkte her.
    try:
        ut = subprocess.run(
            ("git", "merge-base", "--is-ancestor", sha, "origin/main"),
            cwd=ROT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return ut.returncode == 0


def krev_sporbar() -> tuple[str, str]:
    """(commit, rent) — eller `IkkeSporbar` med grunnen skrevet ut.

    Tre vilkår, og alle tre må holde FØR innsamlingen henter noe:

      1. Vi står i et git-arbeidstre som svarer.
      2. Arbeidstreet er rent.
      3. HEAD finnes på `origin/main`.

    Vilkår 3 er det som fanger F15. De to første fanger den vanligere
    varianten: en lokal endring som aldri ble committet.

    Ingen escape-flagg. Et flagg for å hoppe over dette ville vært
    flagget som står i cron-jobben om et halvt år.
    """
    sha = commit()
    if not sha:
        raise IkkeSporbar(
            "git svarer ikke i " + str(ROT) + ". Innsamlingen skriver "
            "filer som er append-only, og en fil som ikke kan spores "
            "tilbake til kode er uetterprøvbar for alltid.")

    tilstand = rent()
    if tilstand != RENT:
        raise IkkeSporbar(
            f"arbeidstreet er ikke rent (HEAD {sha[:12]}). Commit eller "
            f"still tilbake før du samler inn — ellers vet ingen hvilken "
            f"kode som skrev fila.\n\n" + (_git("status", "--short") or ""))

    if not paa_origin_main(sha):
        raise IkkeSporbar(
            f"HEAD {sha[:12]} finnes ikke på origin/main. Push først.\n\n"
            f"Det er F15: 47 commits lå upushet i to uker, den ukentlige "
            f"innsamlingen kjørte gammel kode, og mandagens snapshot ble "
            f"skrevet med personformer i seg. Se CLAUDE.md regel 7.")

    return sha, tilstand
