"""Akvakulturregisteret (Fiskeridirektoratet).

STATUS: deaktivert til du har bekreftet endepunktet.

Fiskeridirektoratet har et åpent API på https://api.fiskeridir.no/pub-aqua/
med Swagger her:
    https://api.fiskeridir.no/pub-aqua/api/swagger-ui/index.html

Gjør dette (10 minutter):
  1. Åpne Swagger-lenken, finn endepunktet som lister lokaliteter/tillatelser.
  2. Lim inn stien i config.yml under kilder.akvakultur.sti
  3. Kjør `python run.py --bare akvakultur` og se på rådataene.
  4. Rett opp feltnavnene i parse() nedenfor.
  5. Sett `aktiv: true` i config.yml.

Merk: kjernen isolerer feil per kilde, så selv om denne feiler
kjører Enhetsregisteret videre og historikken din fortsetter.
"""

from typing import Iterable

import httpx

from core.config import get
from core.contract import Observation, Source


class Akvakulturregisteret(Source):
    name = "akvakultur"
    entity_type = "lokalitet"

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.akvakultur.aktiv", False))

    def fetch(self) -> list[dict]:
        base = get("kilder.akvakultur.base_url", "https://api.fiskeridir.no/pub-aqua/api/v1")
        sti = get("kilder.akvakultur.sti", "")
        if not sti:
            raise ValueError("Sti til akvakultur-endepunktet er ikke satt i config.yml")

        with httpx.Client(timeout=60, headers={"Accept": "application/json"}) as client:
            response = client.get(f"{base.rstrip('/')}/{sti.lstrip('/')}")
            response.raise_for_status()
            payload = response.json()

        # API-er pakker lister ulikt. Håndter de to vanligste formene.
        if isinstance(payload, dict):
            for nøkkel in ("content", "data", "results", "items"):
                if isinstance(payload.get(nøkkel), list):
                    return payload[nøkkel]
            return [payload]
        return payload

    def parse(self, raw: list[dict], observed_at: str) -> Iterable[Observation]:
        # TODO: rett feltnavnene når du har sett faktisk respons (steg 3 over).
        feltkart = get("kilder.akvakultur.feltkart", {})

        for lokalitet in raw:
            lok_id = lokalitet.get(get("kilder.akvakultur.id_felt", "siteNr"))
            navn = lokalitet.get(get("kilder.akvakultur.navn_felt", "name"), "")
            if lok_id is None:
                continue

            for kildefelt, vårt_felt in feltkart.items():
                verdi = lokalitet.get(kildefelt)
                if verdi is None:
                    continue
                yield Observation(
                    entity_id=str(lok_id),
                    entity_type=self.entity_type,
                    entity_name=str(navn),
                    field=str(vårt_felt),
                    value=str(verdi),
                    source=self.name,
                    observed_at=observed_at,
                )
