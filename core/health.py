"""Helsesjekk mellom kjøringer.

Det farligste feilmodus i dette systemet er ikke at noe krasjer.
Det er at én kilde slutter å levere, feilen isoleres pent, jobben
går grønt, og du oppdager i februar at du mangler ni uker med data.

Derfor: vi husker forrige kjøring, og hvis en kilde som fungerte
i forrige uke feiler nå, avsluttes jobben med feilkode. Da sender
GitHub deg e-post.
"""

import json
from pathlib import Path

from core.runner import Result

HEALTH_PATH = Path(__file__).resolve().parent.parent / "data" / "health.json"


def les() -> dict:
    if not HEALTH_PATH.exists():
        return {}
    return json.loads(HEALTH_PATH.read_text(encoding="utf-8"))


def oppdater(resultater: list[Result], observed_at: str) -> tuple[dict, list[str]]:
    """Returnerer ny helsetilstand og liste over kilder som nettopp brakk."""
    forrige = les()
    ny: dict = {}
    regresjoner: list[str] = []

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

        # Fungerte forrige uke, feiler nå -> dette skal vekke deg.
        if not r.ok and gammel.get("feil_paa_rad", 0) == 0 and gammel.get("sist_ok"):
            regresjoner.append(r.source)

    return ny, regresjoner


def skriv(tilstand: dict) -> None:
    HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_PATH.write_text(
        json.dumps(tilstand, indent=2, ensure_ascii=False), encoding="utf-8"
    )
