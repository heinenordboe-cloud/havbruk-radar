"""Enhetsregisteret (Brønnøysund).

Åpent API, ingen nøkkel, ingen registrering. Dette er kilden som skal
kjøre fra dag én — den er stabil og krever ingenting av deg.

Docs: https://data.brreg.no/enhetsregisteret/api/dokumentasjon
"""

from typing import Iterable

import httpx

from core.config import get
from core.contract import Observation, Source

BASE = "https://data.brreg.no/enhetsregisteret/api/enheter"


class Enhetsregisteret(Source):
    name = "enhetsregisteret"
    entity_type = "selskap"
    enabled = True

    def fetch(self) -> list[dict]:
        koder = get("kilder.enhetsregisteret.naeringskoder", [])
        sidestorrelse = get("kilder.enhetsregisteret.sidestorrelse", 100)
        enheter: list[dict] = []

        with httpx.Client(timeout=30, headers={"Accept": "application/json"}) as client:
            for kode in koder:
                side = 0
                while True:
                    response = client.get(BASE, params={
                        "naeringskode": kode,
                        "size": sidestorrelse,
                        "page": side,
                    })
                    response.raise_for_status()
                    payload = response.json()

                    batch = payload.get("_embedded", {}).get("enheter", [])
                    enheter.extend(batch)

                    total_sider = payload.get("page", {}).get("totalPages", 1)
                    side += 1
                    if side >= total_sider or not batch:
                        break

        return enheter

    def parse(self, raw: list[dict], observed_at: str) -> Iterable[Observation]:
        felter = {
            "antall_ansatte": lambda e: e.get("antallAnsatte"),
            "organisasjonsform": lambda e: (e.get("organisasjonsform") or {}).get("kode"),
            "naeringskode": lambda e: (e.get("naeringskode1") or {}).get("kode"),
            "kommune": lambda e: (e.get("forretningsadresse") or {}).get("kommune"),
            "kommunenummer": lambda e: (e.get("forretningsadresse") or {}).get("kommunenummer"),
            "konkurs": lambda e: e.get("konkurs"),
            "under_avvikling": lambda e: e.get("underAvvikling"),
            "registreringsdato": lambda e: e.get("registreringsdatoEnhetsregisteret"),
            "navn": lambda e: e.get("navn"),
        }

        for enhet in raw:
            orgnr = enhet.get("organisasjonsnummer")
            navn = enhet.get("navn", "")
            if not orgnr:
                continue

            for felt, hent in felter.items():
                verdi = hent(enhet)
                if verdi is None:
                    continue
                yield Observation(
                    entity_id=str(orgnr),
                    entity_type=self.entity_type,
                    entity_name=str(navn),
                    field=felt,
                    value=str(verdi),
                    source=self.name,
                    observed_at=observed_at,
                )
