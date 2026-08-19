"""Kjører alle kilder og isolerer feil per kilde.

Uten denne dør hele historikken din den dagen én kilde bytter format.
Med den mister du én kilde én uke, og resten kjører videre.
"""

import traceback
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from core import raw as raw_arkiv

from core import snapshot
from core.contract import Observation, Source


@dataclass
class Result:
    source: str
    ok: bool
    count: int
    error: str = ""
    # Kilden leverte, men vil at noen skal se på noe. Se Source.advarsler.
    advarsler: list[str] = field(default_factory=list)


def stempl(observasjoner, source_version: str, raw_hash: str,
           fetched_at: str | None = None) -> list[Observation]:
    """Setter proveniensfeltene på hver observasjon.

    Ligger her og ikke i hver kaller fordi stemplingen er kjernens
    ansvar: kilder rører aldri disse feltene. Både run_all() og
    backfill.py bruker den, slik at en backfillet rad bærer nøyaktig
    samme proveniens som en ukentlig — det er `fetched_at` langt etter
    `observed_at` som gjør den kjennelig, ikke et manglende felt.
    """
    naa = fetched_at or datetime.now(timezone.utc).isoformat()
    return [
        replace(obs, fetched_at=naa, source_version=source_version,
                raw_hash=raw_hash)
        for obs in observasjoner
    ]


def velg_forfalte(
    sources: list[Source], observed_at: str
) -> tuple[list[Source], list[tuple[Source, int]]]:
    """Deler kildene i (forfalt, må vente).

    En kilde er forfalt hvis den aldri er hentet, eller hvis det er gått
    minst `min_dager_mellom` dager siden sist.

    Dette erstatter den gamle alt-eller-ingenting-guarden. Den nektet hele
    kjøringen når ÉN kilde hadde skrevet i dag, slik at en ny kilde ikke
    kunne aktiveres midt i uka uten å overskrive dagens snapshot for de
    andre. Nå hoppes bare den hentede kilden over.

    Merk konsekvensen: kjører du manuelt på en søndag, er den ukentlige
    kilden ikke forfalt mandag, og ukas snapshot ligger på søndagen i
    stedet. Ingen data går tapt, og neste uke er den forfalt igjen.
    """
    forfalt: list[Source] = []
    venter: list[tuple[Source, int]] = []

    for source in sources:
        dager = snapshot.dager_siden(source.name, observed_at)
        if dager is None or dager >= source.min_dager_mellom:
            forfalt.append(source)
        else:
            venter.append((source, dager))

    return forfalt, venter


def run_all(
    sources: list[Source],
    observed_at: str,
    arkiver: bool = True,
) -> tuple[list[Observation], list[Result]]:
    observations: list[Observation] = []
    results: list[Result] = []

    for source in sources:
        try:
            # collect() kollapset fetch() og parse() til ett kall. Kjernen
            # åpner dem og arkiverer imellom — uten det er hver feil i
            # parse() permanent datatap.
            rawdata = source.fetch()
            raw_hash = ""
            if arkiver:
                raw_hash = raw_arkiv.arkiver(source.name, observed_at, rawdata)
            batch = stempl(
                source.parse(rawdata, observed_at),
                source_version=source.version,
                raw_hash=raw_hash,
            )
            observations.extend(batch)
            results.append(
                Result(source.name, True, len(batch),
                       advarsler=list(getattr(source, "advarsler", [])))
            )
        except Exception:
            results.append(
                Result(source.name, False, 0, traceback.format_exc(limit=3),
                       advarsler=list(getattr(source, "advarsler", [])))
            )

    return observations, results