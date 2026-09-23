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


# Miljøet hvert git-kall får.
#
# ## `GIT_TERMINAL_PROMPT=0` og `BatchMode=yes` er ikke pynt
#
# `ls-remote` mot et privat repo uten legitimasjon SPØR om passord. I en
# CI-jobb finnes ingen å spørre, og kallet henger til jobben times ut.
# En innsamling som henger er verre enn en som feiler: den feiler ikke
# høylytt, den blir borte.
GIT_MILJO = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_SSH_COMMAND": "ssh -oBatchMode=yes -oStrictHostKeyChecking=accept-new",
    "GIT_ASKPASS": "",
    "GCM_INTERACTIVE": "never",
}

# `safe.directory` settes på HVERT kall.
#
# Git nekter å lese et arbeidstre som eies av en annen bruker enn den
# som kjører — «detected dubious ownership» — og returnerer da en
# feilkode. Det skjer i CI-jobber som kjører i en container med annen
# UID enn runneren som sjekket ut koden.
#
# Følgen ville vært at `commit()` ga tom streng, `krev_sporbar()` sa
# «git svarer ikke», og den ukentlige innsamlingen stoppet av en grunn
# som ikke handler om koden i det hele tatt.
#
# Å oppgi at mappa vi kjører i er mappa vi kjører i, svekker ingenting:
# den sier ikke noe om hvilken kode som er pushet.


def _git(*args: str, tid: int = 30) -> tuple[int, str]:
    """(exit-kode, utdata). `-1` når kommandoen ikke lot seg kjøre.

    Skillet mellom «git svarte nei» og «git svarte ikke» er hele
    grunnen til at denne returnerer koden og ikke bare teksten: det
    første handler om koden, det andre om maskinen, og de skal ikke
    behandles likt av noe som kan stoppe en innsamling.
    """
    import os

    try:
        ut = subprocess.run(
            ("git", "-c", f"safe.directory={ROT}", *args),
            cwd=ROT, capture_output=True, text=True, timeout=tid,
            env={**os.environ, **GIT_MILJO})
    except (OSError, subprocess.SubprocessError):
        return -1, ""
    return ut.returncode, (ut.stdout + ut.stderr).strip()


def _git_ut(*args: str) -> str:
    """Bare utdata, tom streng om kallet ikke gikk. For de enkle spørsmålene."""
    kode, ut = _git(*args)
    return ut if kode == 0 else ""


def commit() -> str:
    """sha for HEAD, eller tom streng."""
    return _git_ut("rev-parse", "HEAD")


def rent() -> str:
    """`RENT` hvis arbeidstreet er rent, `URENT` hvis ikke, `UKJENT` ellers.

    `status --porcelain` teller BÅDE usporede og endrede filer. En
    usporet fil er ikke uskyldig: en ny `sources/*.py` som ikke er
    committet, er kode som kjører og som ingen kan finne igjen.
    """
    if not commit():
        return UKJENT
    kode, ut = _git("status", "--porcelain")
    if kode != 0:
        return UKJENT
    return URENT if ut else RENT


@lru_cache(maxsize=4)
def _fjern_main() -> str:
    """sha `origin/main` peker på HOS FJERNLAGERET, eller tom streng.

    Dette er spørsmålet vi faktisk vil ha svar på — «finnes koden der
    alle kan se den» — stilt til den som vet. Samme prinsipp som
    `Tilgang.get()`s re-autentisering på 401 og som regel 3: spør om
    DET du vil vite, ikke om noe som korrelerer med det.

    Den lokale `refs/remotes/origin/main` korrelerer bare. Den
    oppdateres ved `fetch`, så på en utviklermaskin kan den være uker
    gammel: en commit som ER pushet leses som upushet, og en commit som
    er force-pushet bort leses som pushet.

    Tom streng når fjernlageret ikke lar seg spørre — ingen legitimasjon
    (`persist-credentials: false`), ingen nett. Da svarer
    `paa_origin_main()` på den lokale referansen i stedet, og sier det.
    """
    kode, ut = _git("ls-remote", "origin", "refs/heads/main", tid=20)
    if kode != 0 or not ut:
        return ""
    første = ut.split("\n")[0].split()
    return første[0] if første and len(første[0]) == 40 else ""


def _lokal_main() -> str:
    """sha den LOKALE `refs/remotes/origin/main` peker på, eller tom.

    I CI er den fersk: `actions/checkout` hentet den sekunder før, og da
    er den like god som fjernlageret. På en utviklermaskin kan den være
    gammel — se `_fjern_main()`.
    """
    return _git_ut("rev-parse", "--verify", "--quiet",
                   "refs/remotes/origin/main")


def _er_stamfar(sha: str, mot: str) -> bool:
    """Er `sha` lik eller stamfar til `mot`?

    `--is-ancestor` gir exit 0 for ja og 1 for nei, og -1 fra `_git()`
    når kallet ikke gikk. Bare 0 er ja. I et GRUNT arbeidstre kan git
    mangle historikken mellom to ulike commiter og svare nei på noe som
    er sant — derfor sjekkes likhet først, som er tilfellet i CI.
    """
    if sha == mot:
        return True
    kode, _ = _git("merge-base", "--is-ancestor", sha, mot)
    return kode == 0


@lru_cache(maxsize=4)
def paa_origin_main(sha: str) -> tuple[bool, str]:
    """(er den pushet, hvordan vi vet det).

    Andre leddet er ikke pynt: det skiller «fjernlageret sa ja» fra «den
    lokale referansen sa ja» fra «ingen av dem kunne svare», og det er
    forskjellen på et svar og et gjett.

    Svaret kan endre seg over tid — en commit som ikke var pushet da
    fila ble skrevet, kan være pushet i dag — og derfor lagres det ikke
    i fila. Det spørres på nytt. CLAUDE.md 1b-7.
    """
    if not sha:
        return False, "ingen HEAD"

    fjern = _fjern_main()
    if fjern:
        return _er_stamfar(sha, fjern), f"fjernlageret: origin/main = {fjern[:12]}"

    lokal = _lokal_main()
    if lokal:
        return (_er_stamfar(sha, lokal),
                f"lokal refs/remotes/origin/main = {lokal[:12]} "
                f"(fjernlageret svarte ikke)")

    return False, ("verken fjernlageret eller en lokal "
                   "refs/remotes/origin/main kunne svare")


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
            f"kode som skrev fila.\n\n" + (_git_ut("status", "--short") or ""))

    pushet, hvordan = paa_origin_main(sha)
    if not pushet:
        raise IkkeSporbar(
            f"HEAD {sha[:12]} finnes ikke på origin/main. Push først.\n"
            f"  grunnlag: {hvordan}\n\n"
            f"Det er F15: 47 commits lå upushet i to uker, den ukentlige "
            f"innsamlingen kjørte gammel kode, og mandagens snapshot ble "
            f"skrevet med personformer i seg. Se CLAUDE.md regel 7.")

    return sha, tilstand
