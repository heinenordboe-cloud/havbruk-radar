"""Kjører alle kilder og isolerer feil per kilde.

Uten denne dør hele historikken din den dagen én kilde bytter format.
Med den mister du én kilde én uke, og resten kjører videre.
"""

import traceback
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from core import health
from core import raw as raw_arkiv
from core.contract import Observation, Source


@dataclass
class Result:
    source: str
    ok: bool
    count: int
    error: str = ""
    # Kilden leverte, men vil at noen skal se på noe. Se Source.advarsler.
    advarsler: list[str] = field(default_factory=list)
    # Datoen kildens data GJELDER for — ikke datoen vi kjørte. Kalleren
    # trenger den for å navngi snapshotet og datere diffen, og kan ikke
    # regne den ut selv uten å kjenne kildens etterslepsregel.
    # Se Source.gjelder_for.
    gjelder_for: str = ""


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

    Målingen går mot INNSAMLINGSTIDSPUNKTET i health.json, ikke mot
    datoen på nyeste snapshotfil. De to er bare like for kilder uten
    etterslep. Se health.dager_siden_kjoring.

    `None` fra vakten betyr «vet ikke når kilden sist kjørte», og
    behandles som forfalt. Fallback-oppførselen skal være å kjøre.
    """
    tilstand = health.les()
    forfalt: list[Source] = []
    venter: list[tuple[Source, int]] = []

    for source in sources:
        dager = health.dager_siden_kjoring(source.name, observed_at, tilstand)
        if dager is None or dager >= source.min_dager_mellom:
            forfalt.append(source)
        else:
            venter.append((source, dager))

    return forfalt, venter


def run_all(
    sources: list[Source],
    kjoredato: str,
    arkiver: bool = True,
) -> tuple[list[Observation], list[Result]]:
    """Henter hver kilde og isolerer feilene.

    `kjoredato` er dagen VI kjører, ikke datoen dataene gjelder for. Hver
    kilde oversetter selv den ene til den andre med `gjelder_for()`, og
    det er den oversatte datoen som brukes til arkivnavn og til
    `observed_at` på observasjonene. Kalleren får den tilbake i
    `Result.gjelder_for` og skal bruke den — ikke kjøredatoen — når
    snapshotet navngis.
    """
    observations: list[Observation] = []
    results: list[Result] = []

    for source in sources:
        # Kildens egen gyldighetsdato, ikke kjøredatoen. For kilder uten
        # etterslep er de like, og da endrer dette ingenting. For lusetall
        # er de aldri like. Se Source.gjelder_for.
        #
        # Utenfor try-blokken med vilje: en kilde som ikke klarer å svare
        # på hvilken dato den gjelder for, skal ikke få lov til å bli
        # rapportert med tom dato — da hadde feilen dukket opp igjen som
        # et filnavn uten dato langt nedstrøms.
        gjelder = source.gjelder_for(kjoredato)

        try:
            # collect() kollapset fetch() og parse() til ett kall. Kjernen
            # åpner dem og arkiverer imellom — uten det er hver feil i
            # parse() permanent datatap.
            rawdata = source.fetch()
            raw_hash = ""
            if arkiver:
                raw_hash = raw_arkiv.arkiver(source.name, gjelder, rawdata)
            batch = stempl(
                source.parse(rawdata, gjelder),
                source_version=source.version,
                raw_hash=raw_hash,
            )
            observations.extend(batch)
            results.append(
                Result(source.name, True, len(batch),
                       advarsler=list(getattr(source, "advarsler", [])),
                       gjelder_for=gjelder)
            )
        except Exception:
            results.append(
                Result(source.name, False, 0, traceback.format_exc(limit=3),
                       advarsler=list(getattr(source, "advarsler", [])),
                       gjelder_for=gjelder)
            )

    return observations, results