"""Helsesjekk mellom kjøringer.

Det farligste feilmodus i dette systemet er ikke at noe krasjer.
Det er at én kilde slutter å levere, feilen isoleres pent, jobben
går grønt, og du oppdager i februar at du mangler ni uker med data.

Derfor: vi husker forrige kjøring, og så lenge en kilde som HAR
fungert er nede, avsluttes jobben med feilkode. Hver uke, ikke bare
den første. Da sender GitHub deg e-post helt til det er fikset.

Alternativet — å varsle kun ved overgangen fungerte->feiler — gir
nøyaktig feilmodusen beskrevet over, bare forskjøvet én uke: mister
du den ene e-posten, er alt grønt igjen mens datatapet fortsetter.
"""

import json

from core.paths import HEALTH_PATH  # noqa: F401
from core.runner import Result


def les() -> dict:
    if not HEALTH_PATH.exists():
        return {}
    return json.loads(HEALTH_PATH.read_text(encoding="utf-8"))


def oppdater(resultater: list[Result], observed_at: str) -> tuple[dict, list[str]]:
    """Returnerer ny helsetilstand og liste over kilder som er nede.

    "Nede" = kilden har fungert minst én gang før, og feiler nå. En kilde
    som aldri har levert (nyskrevet, ikke ferdig) varsler ikke — den ser
    du på skjermen mens du jobber med den.
    """
    forrige = les()
    ny: dict = {}
    nede: list[str] = []

    for r in resultater:
        gammel = forrige.get(r.source, {})
        strekk = 0 if r.ok else gammel.get("feil_paa_rad", 0) + 1

        ny[r.source] = {
            "sist_ok": observed_at if r.ok else gammel.get("sist_ok"),
            "sist_forsok": observed_at,
            "feil_paa_rad": strekk,
            "antall_sist": r.count,
            "siste_feil": "" if r.ok else r.error.strip().splitlines()[-1][:300],
        }

        # Har fungert før, er nede nå -> dette skal vekke deg. Hver uke.
        if not r.ok and gammel.get("sist_ok"):
            nede.append(f"{r.source} (uke {strekk})")

    return ny, nede


def skriv(tilstand: dict) -> None:
    HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_PATH.write_text(
        json.dumps(tilstand, indent=2, ensure_ascii=False), encoding="utf-8"
    )
