"""Skriver snapshots. Overskriver aldri noe.

Filnavnet er datoen. Det er hele versjonssystemet — git tar resten.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from core import persondata
from core import utvalg as utvalg_modul
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
    # Hva kilden ba om. Proveniens som de tre over — se core/utvalg.py.
    # Verdien er lik for hver rad i ett snapshot, så parquet
    # ordbok-koder den bort. Målt på enhetsregisteret 24.08: 51623 rader
    # og en 100-tegns utvalgsstreng koster 1156 bytes, 0,53 % av fila.
    "utvalg",
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


def _vakt_mot_personformer(source: str, group: pl.DataFrame) -> None:
    """Nekter å skrive et snapshot som inneholder en filtrert
    organisasjonsform.

    Filteret i kilden er der data faktisk holdes ute. Denne vakten er der
    fordi et filter noen glemmer å oppdatere ikke er en garanti: en ny
    kilde som henter selskapsdata, en re-parse gjennom en vei som ikke
    filtrerer, eller en backfill som går utenom kildens `fetch()` — alle
    tre ender her, i den ene trakta alt skrives gjennom. Samme plassering
    og samme begrunnelse som datokontrollen under.

    Hva vakten IKKE dekker, sagt rett ut: den ser bare rader der feltet
    heter `organisasjonsform`. En kilde som kaller det noe annet, eller
    som ikke oppgir formen i det hele tatt, går forbi. Den fanger at et
    kjent filter sviktet — ikke at lista over personformer er riktig.
    """
    if persondata.FORM_FELT not in group["field"].to_list():
        return

    funn = (
        group.filter(pl.col("field") == persondata.FORM_FELT)
        .filter(pl.col("value").str.strip_chars().str.to_uppercase()
                .is_in(sorted(persondata.PERSONFORMER)))
    )
    if funn.is_empty():
        return

    former = sorted(set(funn["value"].to_list()))
    raise ValueError(
        f"{source}: {funn.height} enhet(er) med organisasjonsform {former} "
        f"i radene. Formen er en fysisk person, ikke et selskap "
        f"(se core/persondata.py), og snapshotet skrives ikke. Filteret i "
        f"kilden har sviktet eller er omgått — rett det der, ikke her."
    )


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
    filnavnet med et som finnes, får den neste et løpenummer.

    `observed_at` må stemme med radenes egen `observed_at`, og det
    kontrolleres her. Grunnen er en ekte feil: run.py sendte kjøredatoen
    hit mens lusetall stemplet radene med uka de gjaldt for, så fila het
    2026-08-24 og inneholdt uke 31. Et filnavn som lyver om innholdet er
    verre enn ingen fil, fordi alt nedstrøms — diff, changelog,
    prediksjoner — leser datoen fra navnet.

    Kontrollen ligger her og ikke hos kalleren fordi dette er trakta alt
    går gjennom: både run.py og backfill.py skriver herfra, og en
    invariant som skal holde for begge hører hjemme i den ene veien de
    deler. Samme begrunnelse gjelder personformvakten, se
    `_vakt_mot_personformer`.

    Merk rekkefølgen: rå-arkivet skrives FØR parse(), altså før noe kommer
    hit. Vakten stopper et snapshot, ikke en arkivfil. Skal persondata
    holdes ute av arkivet også, må det skje i kildens `fetch()` — som er
    grunnen til at enhetsregisteret filtrerer begge steder.
    """
    frame = to_frame(observations)
    written = []

    for (source,), group in frame.group_by(["source"]):
        _vakt_mot_personformer(str(source), group)

        datoer = sorted(set(group["observed_at"].to_list()))
        if datoer != [observed_at]:
            raise ValueError(
                f"{source}: filnavnet skulle vært {observed_at}, men radene "
                f"er observert {datoer}. Ett snapshot er ett tidspunkt — "
                f"skriv dem hver for seg, eller finn ut hvorfor de spriker."
            )

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

    Frekvensvakten spør health.dager_siden_ok() i stedet. Denne
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


def _les(sti: Path) -> pl.DataFrame:
    """DEN ENE DØRA INN TIL ET SNAPSHOT PÅ DISK.

    Alt som leser innholdet i `data/raw/<kilde>/<dato>.parquet` går
    herfra, og derfor ligger persondatafilteret her og ikke i hver leser.
    `previous()` og `les_mellom()` er de eneste kallerne, og de er i sin
    tur de eneste veiene diff, prediksjoner og visning har inn til
    rådataene.

    Grunnen til at det må være ETT sted: snapshotene fra 16.–17.08.2026
    inneholder 34 enkeltpersonforetak hver, og de filene er append-only
    og blir stående. Filteret er derfor ikke en engangsopprydding som kan
    kjøres ferdig, men en betingelse hver lesing må oppfylle — og en
    betingelse som må oppfylles hver gang, skal ikke være noe en ny
    leseveis forfatter må huske.

    `test_ingen_leser_snapshots_utenom_les()` håndhever at det forblir
    slik: den nekter at `read_parquet` dukker opp i denne modulen mer enn
    én gang, eller i en annen modul som kjenner RAW_DIR.
    """
    frame = persondata.fjern_personformer(pl.read_parquet(sti))

    # Snapshots skrevet før 24.08.2026 har ingen `utvalg`-kolonne. De
    # skal kunne leses, og de skal lese som «vet ikke» — ikke som «ingen
    # filtrering». Tom streng er nettopp det skillet, se utvalg.les().
    #
    # Kolonnen legges til her og ikke hos hver leser av samme grunn som
    # persondatafilteret ligger her: dette er den ene døra, og en
    # betingelse som må oppfylles hver gang skal ikke være noe en ny
    # lesevei må huske.
    if "utvalg" not in frame.columns:
        frame = frame.with_columns(pl.lit("", dtype=pl.Utf8).alias("utvalg"))
    return frame


def utvalg_i(frame: pl.DataFrame) -> dict | None:
    """Utvalget et snapshot ble hentet med. None = vet ikke.

    Ett snapshot er ett kall, så alle rader bærer samme verdi. Spriker
    de likevel — to kilder slått sammen i én ramme, eller en håndredigert
    fil — er svaret None. Å plukke den første av flere ville vært et
    gjett, og et gjett her undertrykker rader.
    """
    if frame.is_empty() or "utvalg" not in frame.columns:
        return None
    verdier = set(frame["utvalg"].to_list())
    if len(verdier) != 1:
        return None
    return utvalg_modul.les(verdier.pop())


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

    return _les(earlier[-1])


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
    return [(_dato_og_versjon(p.stem)[0], _les(p)) for p in aktuelle]
