"""Kjører alle kilder og isolerer feil per kilde.

Uten denne dør hele historikken din den dagen én kilde bytter format.
Med den mister du én kilde én uke, og resten kjører videre.
"""

import traceback
from dataclasses import dataclass

from core.contract import Observation, Source


@dataclass
class Result:
    source: str
    ok: bool
    count: int
    error: str = ""


def run_all(sources: list[Source], observed_at: str) -> tuple[list[Observation], list[Result]]:
    observations: list[Observation] = []
    results: list[Result] = []

    for source in sources:
        try:
            batch = source.collect(observed_at)
            observations.extend(batch)
            results.append(Result(source.name, True, len(batch)))
        except Exception:
            results.append(
                Result(source.name, False, 0, traceback.format_exc(limit=3))
            )

    return observations, results
