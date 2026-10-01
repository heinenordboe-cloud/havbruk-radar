"""Kjører alle kilder og isolerer feil per kilde.

Uten denne dør hele historikken din den dagen én kilde bytter format.
Med den mister du én kilde én uke, og resten kjører videre.
"""

import traceback
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone

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
           published_at: str = "", *, kilde) -> list[Observation]:
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

    `kilde` er OBLIGATORISK og nøkkelordbasert. Den er her bare for
    `domene`, og bare fordi det feltet settes av `parse()` — se
    kommentaren i kroppen. De øvrige feltene sendes som verdier, og det
    er ikke inkonsekvens: `source_version`, `utvalg` og `published_at`
    settes alle av `fetch()`, som er ferdig før kalleren i det hele tatt
    bygger argumentlista. For dem finnes ingen rekkefølgefelle å lukke.

    `utvalg` er hva kilden BA OM, satt av dens egen `fetch()`. Den
    stemples her av samme grunn som de tre andre: skulle hver kilde
    sette den på hver Observation, ville en kilde som glemte det gitt et
    snapshot som ser komplett ut og ikke kan svare på hvorfor en entitet
    dukket opp. En backfill uten fetch() har ikke noe utvalg å oppgi, og
    da blir feltet tomt — som leses «vet ikke», ikke «ingen filtrering».
    """
    naa = fetched_at or datetime.now(timezone.utc).isoformat()
    merket = utvalg_modul.serialiser(utvalg)

    # RETT HER er hele grunnen til at `kilde` sendes inn og ikke
    # `domene`-verdien.
    #
    # `domene` settes av `parse()` MENS den leser kroppen, og et
    # kallsted som skrev `stempl(kilde.parse(...), domene=kilde.domene)`
    # ville lest verdien FØR generatorens kropp kjørte — altså fra
    # forrige kall, eller None på det første. Snapshotet ville fått et
    # domene som beskriver en annen periode enn radene sine. Det er samme
    # rekkefølgefelle som F6 og F7: to oppslag som kan svare ulikt om det
    # samme kallet.
    #
    # Fram til 15.09.2026 ble den holdt i sjakk av at hvert av de sju
    # kallstedene skrev `list(kilde.parse(...))`. Det er en regel ingen
    # kan SE ved lesing, og et åttende kallsted ville ikke blitt fanget.
    # Nå materialiseres strømmen her, og domenet leses etterpå — fra
    # kilden, av den ene funksjonen som vet at rekkefølgen betyr noe.
    batch = list(observasjoner)
    erklart = getattr(kilde, "domene", None)

    # Domenet stemples her og ikke i kilden, av samme grunn som de fire
    # andre proveniensfeltene: en kilde som glemte det ville gitt et
    # snapshot som ser komplett ut og ikke kan svare på hvorfor en celle
    # mangler. `serialiser()` får det ERKLÆRTE domenet og parene som
    # faktisk kom ut, og kaster hvis erklæringen ikke dekker emisjonene.
    domene_merket = domene_modul.serialiser(
        erklart, {(o.entity_id, o.field) for o in batch})

    return [
        replace(obs, fetched_at=naa, source_version=source_version,
                raw_hash=raw_hash, utvalg=merket, published_at=published_at,
                domene=domene_merket)
        for obs in batch
    ]


# Kadensen som måles i ISO-UKER og ikke i dager. Tallet er fortsatt
# `min_dager_mellom` på kilden — det er ikke et nytt felt å holde i takt,
# bare en annen lesning av det som står der. Se velg_forfalte.
UKENTLIG = 7


def _isouke(dato: str) -> tuple[int, int] | None:
    """(ISO-år, ISO-uke) for en datostreng. None når den ikke er lesbar.

    ISO-ÅRET og ikke kalenderåret: 29.12.2026 er uke 53 i ISO-år 2026, og
    04.01.2027 er uke 1 i ISO-år 2027. Tuppelet kan derfor sammenlignes
    rett over et årsskifte, mens (kalenderår, uke) ville sagt at uke 53
    kom ETTER uke 1 i samme år.
    """
    try:
        return date.fromisoformat(dato).isocalendar()[:2]
    except (TypeError, ValueError):
        return None


def _uke_er_eldre(sist_ok: str | None, observed_at: str) -> bool:
    """Ligger `sist_ok` i en tidligere ISO-uke enn kjøredatoen?

    True betyr forfalt. `None` eller en ulesbar dato gir True: vet vi
    ikke når kilden sist lyktes, kjører vi. Fallback-oppførselen skal
    være å kjøre — en uke som ikke hentes kan ikke hentes igjen, mens en
    henting for mye er en fil med løpenummer.

    Er kjøredatoen selv ulesbar, er svaret False. Da vet vi ingenting om
    hvilken uke vi er i, og «hent alt» på det grunnlaget ville vært å
    skrive snapshots på en dato vi ikke kan tolke.
    """
    naa = _isouke(observed_at)
    if naa is None:
        return False
    da = _isouke(sist_ok) if sist_ok else None
    if da is None:
        return True
    return da < naa


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

    ## Ukentlige kilder måles i ISO-UKER, ikke i dager

    En kilde med `min_dager_mellom == UKENTLIG` er forfalt hvis den ikke
    har et `sist_ok` i DENNE ISO-uka. Andre kadenser teller dager som før.

    Dagtellingen drev kilden framover i uka, én dag per redning. F16,
    målt i datarepoet: `biomasselag` fikk sin første `sist_ok` tirsdag
    15.09.2026, fordi kilden ble commitet 14.09 kl. 10:22 — to minutter
    før mandagskjøringen, som derfor kjørte uten den (samme familie som
    F15: pushet kode er det som kjører). Mandag 21.09 var det 6 dager
    siden, under 7, og kilden var ikke forfalt. Tirsdagens gjenkjøring
    tok den: `sist_ok` ble 22.09, også en tirsdag. Mandag 28.09: 6 dager
    igjen. Tirsdag 29.09 var kilden forfalt, og DA feilet endepunktet.

    Konsekvensen er at gjenkjøringen sluttet å være en reserve. Den var
    den ENESTE kjøringen som hentet kilden, og en kilde med bare ett
    forsøk i uka har ingen reserve igjen når det forsøket feiler. Uke 40
    gikk tapt på det, og en tapt uke kan ikke hentes (regel 5).

    ISO-uka fjerner driften ved å spørre om det vi faktisk vil vite:
    har vi ukas snapshot. Mandag henter da alltid alt, og tirsdag blir
    en ekte reserve igjen — en kilde som lyktes mandag er ikke forfalt
    tirsdag, og en som uteble er det.

    Den fanger også årsskiftet, som dagtellingen ikke kunne se: tirsdag
    29.12.2026 (2026-W53) til mandag 04.01.2027 (2027-W01) er 6 dager.
    To ulike uker, og uke 1 skal hentes.

    Merk konsekvensen for en manuell søndagskjøring: søndag og mandag
    ligger i ULIKE ISO-uker (søndag er uke N, mandag er uke N+1), så en
    kilde hentet på søndag ER forfalt mandag. Det er motsatt av hva
    dagtellingen gjorde, og det er med vilje — mandagen er den planlagte
    innsamlingen, og den skal ikke kunne stå over fordi noen prøvde noe
    i helgen.

    Sammenligningen er «sist_ok ligger i en TIDLIGERE uke», ikke «ulik
    uke». Forskjellen gjelder bare når `sist_ok` ligger i FRAMTIDA, og
    der skal vakten fortsatt holde igjen: en health.json med klokkerot
    er ikke et argument for å hente på nytt. Se
    test_kjoretidspunkt_fram_i_tid_gir_ikke_ny_kjoring.

    Uka leses av `observed_at`, som kalleren sender inn. Ingen klokke og
    ingen tidssone slås opp her — kjøredatoen slås opp nøyaktig ett sted
    (run.py, CLAUDE.md 1b), og hvilken sone den stedet bruker er dets
    sak. Et andre oppslag i en annen sone er F6/F7 om igjen: to svar som
    kan være uenige rundt midnatt, og da får fila navn etter én uke og
    innhold fra en annen.

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

        if source.min_dager_mellom == UKENTLIG:
            sist = (tilstand.get(source.name) or {}).get("sist_ok")
            if _uke_er_eldre(sist, observed_at):
                forfalt.append(source)
            else:
                # `dager` kan være None her bare hvis datoen er ulesbar,
                # og da svarte _uke_er_eldre allerede «forfalt». Står vi
                # her, har kilden en lesbar dato i denne uka eller senere.
                venter.append((source, dager if dager is not None else 0))
            continue

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
            # `domene` er den ene som IKKE kan sendes som verdi herfra:
            # den settes av `parse()`, som ikke har kjørt ennå når denne
            # argumentlista bygges. Derfor tar `stempl()` kilden.
            batch = stempl(
                source.parse(rawdata, gjelder),
                source_version=source.version,
                raw_hash=raw_hash,
                utvalg=getattr(source, "utvalg", None),
                # LESES ETTER fetch(), som utvalget og av samme grunn:
                # verdien skal beskrive det kallet som nettopp ble gjort.
                published_at=getattr(source, "published_at", "") or "",
                kilde=source,
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