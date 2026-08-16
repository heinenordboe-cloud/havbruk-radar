"""Kildekontrakten.

Dette er den viktigste filen i repoet. Alt annet er utskiftbart.
Så lenge en kilde returnerer Observation-objekter, trenger resten av
systemet aldri vite hvor dataene kom fra.
"""

from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass(frozen=True)
class Observation:
    """Én målt egenskap ved én entitet på ett tidspunkt.

    Alt normaliseres hit. Enhetsregisteret har ett skjema,
    Akvakulturregisteret et helt annet — men begge ender her.
    """

    entity_id: str      # orgnr (9 siffer) eller lokalitetsnummer
    entity_type: str    # "selskap" | "lokalitet"
    entity_name: str
    field: str          # "antall_ansatte", "kapasitet_tonn", "kommune"
    value: str          # alt lagres som tekst; typing skjer i analysen
    source: str         # navnet på kilden som observerte
    observed_at: str    # ISO-dato for kjøringen

    def as_dict(self) -> dict:
        return asdict(self)


class Source:
    """Arv fra denne. Kjernen finner deg automatisk.

    Ny kilde = ny fil i sources/. Ingen registrering, ingen import
    noe annet sted, ingen endring i core/.
    """

    name: str = "ukjent"
    entity_type: str = "selskap"
    enabled: bool = True

    def fetch(self) -> Any:
        """Hent rådata. Ingen rensing, ingen tolkning her."""
        raise NotImplementedError

    def parse(self, raw: Any, observed_at: str) -> Iterable[Observation]:
        """Gjør rådata om til observasjoner."""
        raise NotImplementedError

    def collect(self, observed_at: str) -> list[Observation]:
        return list(self.parse(self.fetch(), observed_at))
