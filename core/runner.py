"""Kjører alle kilder og isolerer feil per kilde.

Uten denne dør hele historikken din den dagen én kilde bytter format.
Med den mister du én kilde én uke, og resten kjører videre.
"""

import traceback
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from core import health
from core import domene as domene_modul
from core import utvalg as utvalg_modul
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
           fetched_at: str | None = None, utvalg: dict | None = None,
           published_at: str = "", domene: object = None) -> list[Observation]:
    """Setter proveniensfeltene på hver observasjon.

    Ligger her og ikke i hver kaller fordi stemplingen er kjernens
    ansvar: kilder rører aldri disse feltene. Både run_all() og
    backfill.py bruker den, slik at en backfillet rad bærer nøyaktig
    samme proveniens som en ukentlig — det er `fetched_at` langt etter
    `observed_at` som gjør den kjennelig, ikke et manglende felt.

    `published_at` er da KILDEN utga svaret, satt av dens egen `fetch()`
    der den har LEST den. Tom streng er «vet ikke», og det er standarden —
    ikke `fetched_at`. Sto hentetidspunktet der, ville hver kilde påstått
    en utgivelsesdato ingen har gått god for, og påstanden ville vært
    usann i nøyaktig det tilfellet feltet finnes for: en kropp hentet fra
    et arkiv, der de to ligger år fra hverandre. Se
    Observation.published_at.

    `utvalg` er hva kilden BA OM, satt av dens egen `fetch()`. Den
    stemples her av samme grunn som de tre andre: skulle hver kilde
    sette den på hver Observation, ville en kilde som glemte det gitt et
    snapshot som ser komplett ut og ikke kan svare på hvorfor en entitet
    dukket opp. En backfill uten fetch() har ikke noe utvalg å oppgi, og
    da blir feltet tomt — som leses «vet ikke», ikke «ingen filtrering».
    """
    naa = fetched_at or datetime.now(timezone.utc).isoformat()
    merket = utvalg_modul.serialiser(utvalg)

    # Observasjonene MÅ materialiseres før domenet serialiseres: kilder
    # yielder, og et generatoruttrykk kan bare leses én gang. Uten dette
    # ville `serialiser()` tømt strømmen og løkka under fått null rader.
    #
    # MERK at dette ikke er nok alene. `domene` settes av `parse()` mens
    # den leser kroppen, og KALLERENS argumenter evalueres før
    # generatorens kropp kjører. Derfor materialiserer hvert kallsted
    # OGSÅ — `stempl(list(kilde.parse(...)), …, domene=getattr(...))` —
    # ellers leses domenet fra forrige kall. Det er samme rekkefølgefelle
    # som F6 og F7: to oppslag som kan svare ulikt om det samme kallet.
    # `test_domenet_leses_etter_parse` holder det sant.
    batch = list(observasjoner)

    # Domenet stemples her og ikke i kilden, av samme grunn som de fire
    # andre proveniensfeltene: en kilde som glemte det ville gitt et
    # snapshot som ser komplett ut og ikke kan svare på hvorfor en celle
    # mangler. `serialiser()` får det ERKLÆRTE domenet og parene som
    # faktisk kom ut, og kaster hvis erklæringen ikke dekker emisjonene.
    domene_merket = domene_modul.serialiser(
        domene, {(o.entity_id, o.field) for o in batch})

    return [
        replace(obs, fetched_at=naa, source_version=source_version,
                raw_hash=raw_hash, utvalg=merket, published_at=published_at,
                domene=domene_merket)
        for obs in batch
    ]


def velg_forfalte(
    sources: list[Source], observed_at: str
) -> tuple[list[Source], list[tuple[Source, int]]]:
    """Deler kildene i (forfalt, må vente).

    En kilde er forfalt hvis den aldri er hentet med hell, eller hvis
    det er gått minst `min_dager_mellom` dager siden den sist LYKTES.

    Dette erstatter den gamle alt-eller-ingenting-guarden. Den nektet hele
    kjøringen når ÉN kilde hadde skrevet i dag, slik at en ny kilde ikke
    kunne aktiveres midt i uka uten å overskrive dagens snapshot for de
    andre. Nå hoppes bare den hentede kilden over.

    Merk konsekvensen: kjører du manuelt på en søndag, er den ukentlige
    kilden ikke forfalt mandag, og ukas snapshot ligger på søndagen i
    stedet. Ingen data går tapt, og neste uke er den forfalt igjen.

    Målingen går mot SISTE VELLYKKEDE INNSAMLING i health.json — ikke
    mot datoen på nyeste snapshotfil (F4), og ikke mot siste forsøk
    (F8). Et forsøk som feilet har ikke hentet noe, og skal ikke kunne
    sette kilden i karantene. Se health.dager_siden_ok.

    `None` fra vakten betyr «vet ikke når kilden sist lyktes», og
    behandles som forfalt. Fallback-oppførselen skal være å kjøre.
    """
    tilstand = health.les()
    forfalt: list[Source] = []
    venter: list[tuple[Source, int]] = []

    for source in sources:
        dager = health.dager_siden_ok(source.name, observed_at, tilstand)
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
            rawdata = source.fetch(kjoredato)
            raw_hash = ""
            if arkiver:
                raw_hash = raw_arkiv.arkiver(source.name, gjelder, rawdata)
            # `source.utvalg` LESES ETTER fetch(), aldri før. Kilden
            # setter den mens den henter, så verdien beskriver nødvendigvis
            # det kallet som nettopp ble gjort. Leste vi den før, ville vi
            # hatt to oppslag som kan svare ulikt — F6/F7/F8 om igjen.
            #
            # `list()` rundt parse() er samme sak en etasje ned, og den
            # er lett å overse: `domene` settes av `parse()` mens den
            # leser kroppen, og argumentene under evalueres FØR en
            # generators kropp kjører. Uten `list()` ville
            # `getattr(source, "domene", ...)` lest verdien fra FORRIGE
            # kall — None på det første — og snapshotet fått et domene
            # som beskriver en annen runde enn radene sine.
            batch = stempl(
                list(source.parse(rawdata, gjelder)),
                source_version=source.version,
                raw_hash=raw_hash,
                utvalg=getattr(source, "utvalg", None),
                # LESES ETTER fetch(), som utvalget og av samme grunn:
                # verdien skal beskrive det kallet som nettopp ble gjort.
                published_at=getattr(source, "published_at", "") or "",
                # Samme: uttrekket setter den mens det leser kroppen.
                domene=getattr(source, "domene", None),
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