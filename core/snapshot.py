"""Skriver snapshots. Overskriver aldri noe.

Filnavnet er datoen. Det er hele versjonssystemet — git tar resten.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from core.contract import Observation
from core.paths import RAW_DIR  # noqa: F401  (monkeypatches i testene treffer her)

SCHEMA = [
    "entity_id",
    "entity_type",
    "entity_name",
    "field",
    "value",
    "source",
    "observed_at",
    "fetched_at",
    "source_version",
    "raw_hash",
]


# Én kilde skal levere én verdi per entitet og felt per kjøring. Dette er
# invarianten i observasjonsformatet, ikke en egenskap ved noen enkelt kilde,
# og derfor håndheves den her — i trakta alt går gjennom — og ikke i hver
# kilde for seg.
#
# `source` er med i nøkkelen med vilje: to KILDER som observerer samme felt
# på samme entitet er kryssvalidering og skal beholdes. Det er samme kilde
# to ganger som er feilen.
NOKKEL = ["entity_id", "field", "source"]


def to_frame(observations: list[Observation]) -> pl.DataFrame:
    """Observasjoner til tabell, med duplikater fjernet.

    Hvorfor dedupliseringen ligger her: en kilde som gjør flere søk kan få
    samme entitet i retur fra to av dem. Enhetsregisteret søker på ni
    NACE-koder, og 15 selskaper matchet to av dem 17.08.2026 — det ga 503
    identiske ekstrarader. Mønsteret er ikke særegent for Brreg; enhver
    kilde som filtrerer på en kodeliste kan treffe det.

    Konsekvensen av å la dem stå er ikke bare støy i parquet: diff.compare()
    joiner på (entity_id, field), så en duplisert rad blir til en duplisert
    ENDRING den uka verdien faktisk endrer seg. Endringsloggen er produktet,
    og den kan ikke rapportere samme hendelse to ganger.

    `maintain_order=True` fordi rekkefølgen ellers varierer mellom kjøringer.
    Det ville gitt en ny parquet-fil i git selv når ingenting er endret.
    """
    if not observations:
        return pl.DataFrame(schema={col: pl.Utf8 for col in SCHEMA})
    frame = pl.DataFrame([o.as_dict() for o in observations]).select(SCHEMA)
    return frame.unique(subset=NOKKEL, keep="first", maintain_order=True)


def _ledig_sti(target_dir: Path, observed_at: str) -> Path:
    """Neste ledige filnavn for denne datoen. Samme mønster som
    raw_arkiv.arkiver(): kollisjon løser seg med løpenummer, ikke
    overskriving."""
    sti = target_dir / f"{observed_at}.parquet"
    if not sti.exists():
        return sti

    n = 2
    while True:
        sti = target_dir / f"{observed_at}.{n}.parquet"
        if not sti.exists():
            return sti
        n += 1


def _dato_og_versjon(stem: str) -> tuple[str, int]:
    """'2026-08-17.3' -> ('2026-08-17', 3). Uten løpenummer: versjon 1.

    Datoen inneholder ingen punktum, så første del er alltid datoen —
    uansett hvor mange løpenumre som følger.
    """
    dato, _, versjon = stem.partition(".")
    return dato, int(versjon) if versjon else 1


def write(observations: list[Observation], observed_at: str) -> list[Path]:
    """Én parquet-fil per kilde per kjøring. Skriver aldri om — kolliderer
    filnavnet med et som finnes, får den neste et løpenummer."""
    frame = to_frame(observations)
    written = []

    for (source,), group in frame.group_by(["source"]):
        target_dir = RAW_DIR / str(source)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = _ledig_sti(target_dir, observed_at)
        group.write_parquet(path)
        written.append(path)

    return written


def finnes_allerede(observed_at: str) -> list[str]:
    """Kilder som allerede har skrevet snapshot for denne datoen.

    Kjører du to ganger samme dag, sammenligner diffen mot forrige UKE
    på nytt og fører de samme endringene inn i changeloggen en gang til.
    run.py bruker denne til å nekte, i stedet for å doble tallene dine.
    """
    if not RAW_DIR.exists():
        return []
    return sorted(
        katalog.name
        for katalog in RAW_DIR.iterdir()
        if katalog.is_dir() and (katalog / f"{observed_at}.parquet").exists()
    )


def siste_dato(source: str) -> str | None:
    """Datoen for siste snapshot fra denne kilden, eller None.

    Flere filer kan dele dato (løpenummer ved kollisjon) — det er
    datoen som teller her, ikke hvilken fil som var sist alfabetisk.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None
    filer = sorted(target_dir.glob("*.parquet"), key=lambda p: _dato_og_versjon(p.stem))
    return _dato_og_versjon(filer[-1].stem)[0] if filer else None


def dager_siden_observasjon(source: str, observed_at: str) -> int | None:
    """Alderen på den nyeste OBSERVASJONEN fra kilden. None = ingen finnes.

    Het `dager_siden` og ble brukt som frekvensvakt. Det var feil, og
    navnet var grunnen: den svarer på «hvor gammel er nyeste
    observasjon», ikke på «når samlet vi sist inn». For kilder uten
    etterslep er de to like, og forskjellen var usynlig. For lusetall
    med uker_etterslep=4 er de aldri like — nyeste fil er ALLTID datert
    fire uker tilbake, også når kilden kjører perfekt.

    Frekvensvakten spør health.dager_siden_kjoring() i stedet. Denne
    måler datafriskhet, som er et ekte spørsmål, bare ikke det
    spørsmålet.

    Negativt tall (snapshot datert fram i tid) returneres som det er.
    """
    sist = siste_dato(source)
    if sist is None:
        return None
    try:
        return (date.fromisoformat(observed_at) - date.fromisoformat(sist)).days
    except ValueError:
        return None   # filnavn som ikke er en dato: behandles som aldri hentet


def previous(source: str, before: str) -> pl.DataFrame | None:
    """Siste snapshot fra denne kilden før gitt dato.

    Ved flere filer på samme (siste) dato — kollisjon løst med
    løpenummer — velges den med høyest løpenummer, ikke den som
    sorterer sist alfabetisk (".10" < ".2" alfabetisk, ikke tallmessig).
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None

    earlier = sorted(
        (p for p in target_dir.glob("*.parquet") if _dato_og_versjon(p.stem)[0] < before),
        key=lambda p: _dato_og_versjon(p.stem),
    )
    if not earlier:
        return None

    return pl.read_parquet(earlier[-1])


def les_mellom(source: str, fra: str, til: str) -> list[tuple[str, pl.DataFrame]]:
    """Alle snapshots fra denne kilden i intervallet [fra, til], eldst først.

    `previous()` svarer på "hva sto her sist". Prediksjonsloggen trenger
    noe annet: hele forløpet gjennom et vindu, fordi et anslag treffer
    den uka terskelen passeres — ikke bare hvis verdien tilfeldigvis
    fortsatt er over den når vinduet lukker. Leser man kun endepunktene,
    scores en kapasitetsøkning som ble reversert i uke ni som bom, og
    anslaget var riktig.

    Begge endepunkter er inklusive. `fra` må være med: det er der
    utgangsverdien hentes.

    Flere filer på samme dato (løpenummer ved kollisjon) gir flere
    innslag med samme dato, sortert slik at høyeste løpenummer kommer
    sist — samme rekkefølge som `previous()` velger etter.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return []

    aktuelle = sorted(
        (p for p in target_dir.glob("*.parquet")
         if fra <= _dato_og_versjon(p.stem)[0] <= til),
        key=lambda p: _dato_og_versjon(p.stem),
    )
    return [(_dato_og_versjon(p.stem)[0], pl.read_parquet(p)) for p in aktuelle]
