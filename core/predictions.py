"""Prediksjonsloggen. Hva du trodde, skrevet før du visste.

Dette er det eneste laget i systemet som ikke kan rekonstrueres.

Snapshots kan backfilles — lusetall ligger ute tilbake til 2012, og
Akvakulturregisteret versjonerer seg selv internt. Changelog, signaler
og mønstre er rene funksjoner av arkivet og kan regnes ut på nytt når
som helst. Alt det kan en konkurrent skaffe seg på en kveld.

Et anslag skrevet ned FØR utfallet kan ingen skaffe seg i etterkant.
Commit-tidsstempelet er ankeret, og det er derfor prediksjonene ligger
i git og ikke i en database.

Sekundært, og på kort sikt viktigere: dette er måleinstrumentet som gjør
vektene i `rules/signals.yml` til noe annet enn gjetninger. Fila sier det
selv — «kvalifiserte gjetninger, ikke validerte tall». Uten fasit på hva
som faktisk betydde noe, forblir de gjetninger uansett hvor mange kilder
som legges til.

## Formatet er strengt med vilje

Reverseringskriteriet i beslutningen fra 17.08 sier: blir prediksjonene
så vage at de ikke kan feile, er problemet formatet, ikke ideen. Derfor
validerer `valider()` hardt, og derfor er `grunnlag` obligatorisk. Et
anslag uten begrunnelse er en myntkast man kan huske selektivt.

## Du kan ikke spå fortiden

`vindu.fra` må være samme dato som filnavnet eller senere. Uten den
regelen kan et anslag skrives i dag om et vindu som lukket i fjor, og
hele treffraten blir verdiløs. Regelen er mekanisk, ikke en æressak.

## Resultatene er avledet, ikke sannhet

Et resultat er en ren funksjon av (prediksjon, snapshots i vinduet).
Begge er append-only, så evalueringen gir samme svar hver gang den
kjøres. Derfor skrives resultatene som data og ikke tilbake i
prediksjonsfila — den skal aldri røres etter at den er committet.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import yaml

from core.paths import DATA_DIR, ROT

PREDIKSJON_DIR = ROT / "predictions"
RESULTAT_DIR = DATA_DIR / "prediksjoner"

TYPER = {"endring", "verdi", "uendret"}
RETNINGER = {"opp", "ned"}

# Et grunnlag på tre ord er ikke et grunnlag. Tallet er en vurdering,
# ikke et funn — men noe må stå der, ellers forsvinner begrunnelsen
# først og etterprøvbarheten rett etterpå.
MIN_GRUNNLAG = 25

RESULTAT_SCHEMA = {
    "id": pl.Utf8,
    "entitet": pl.Utf8,
    "kilde": pl.Utf8,
    "felt": pl.Utf8,
    "type": pl.Utf8,
    "utfall": pl.Utf8,        # "traff" | "bom" | "kan_ikke_avgjores"
    "begrunnelse": pl.Utf8,   # hvorfor evalueringen konkluderte slik
    "utgangsverdi": pl.Utf8,
    "sluttverdi": pl.Utf8,
    "vindu_fra": pl.Utf8,
    "vindu_til": pl.Utf8,
    "evaluert_at": pl.Utf8,
}


# ---------------------------------------------------------------- lasting


def _filer() -> list[Path]:
    if not PREDIKSJON_DIR.exists():
        return []
    return sorted(PREDIKSJON_DIR.glob("*.yml"))


def last() -> list[dict]:
    """Alle prediksjoner fra alle filer, med `_fil` og `_fildato` påstemplet.

    Filnavnet er datoen anslaget ble skrevet. Den brukes til å nekte
    anslag om fortiden, så den må følge med raden.
    """
    ut: list[dict] = []
    for sti in _filer():
        innhold = yaml.safe_load(sti.read_text(encoding="utf-8")) or {}
        for p in innhold.get("prediksjoner", []) or []:
            ut.append({**p, "_fil": sti.name, "_fildato": sti.stem})
    return ut


# --------------------------------------------------------------- validering


def _valider_en(p: dict) -> list[str]:
    feil: list[str] = []
    pid = p.get("id", "<uten id>")

    for felt in ("id", "entitet", "kilde", "felt", "type", "grunnlag"):
        if not str(p.get(felt) or "").strip():
            feil.append(f"{pid}: mangler {felt}")

    grunnlag = str(p.get("grunnlag") or "").strip()
    if grunnlag and len(grunnlag) < MIN_GRUNNLAG:
        feil.append(
            f"{pid}: grunnlag er {len(grunnlag)} tegn, minst {MIN_GRUNNLAG} kreves"
        )

    typ = p.get("type")
    if typ not in TYPER:
        feil.append(f"{pid}: type må være en av {sorted(TYPER)}, ikke {typ!r}")

    if typ == "endring":
        if p.get("retning") not in RETNINGER:
            feil.append(f"{pid}: type=endring krever retning opp eller ned")
        if not isinstance(p.get("terskel_prosent"), (int, float)):
            feil.append(f"{pid}: type=endring krever terskel_prosent som tall")
    elif typ == "verdi":
        if not str(p.get("verdi") or "").strip():
            feil.append(f"{pid}: type=verdi krever verdi")
    elif typ == "uendret":
        if not isinstance(p.get("terskel_prosent"), (int, float)):
            feil.append(f"{pid}: type=uendret krever terskel_prosent som tall")

    vindu = p.get("vindu") or {}
    fra, til = str(vindu.get("fra") or ""), str(vindu.get("til") or "")
    try:
        d_fra, d_til = date.fromisoformat(fra), date.fromisoformat(til)
    except ValueError:
        feil.append(f"{pid}: vindu.fra og vindu.til må være ISO-datoer")
        return feil

    if d_til <= d_fra:
        feil.append(f"{pid}: vindu.til må være etter vindu.fra")

    # Du kan ikke spå fortiden. Uten denne er treffraten verdiløs.
    fildato = p.get("_fildato")
    if fildato:
        try:
            if d_fra < date.fromisoformat(fildato):
                feil.append(
                    f"{pid}: vindu.fra ({fra}) er før fila ble skrevet ({fildato})"
                )
        except ValueError:
            feil.append(f"{pid}: filnavnet {fildato!r} er ikke en dato")

    return feil


def valider(prediksjoner: list[dict] | None = None) -> list[str]:
    """Alle feil, ikke bare den første. Tom liste = alt i orden."""
    prediksjoner = last() if prediksjoner is None else prediksjoner
    feil: list[str] = []

    sett: dict[str, str] = {}
    for p in prediksjoner:
        feil.extend(_valider_en(p))
        pid = str(p.get("id") or "")
        if pid:
            if pid in sett:
                feil.append(f"{pid}: id går igjen i {sett[pid]} og {p.get('_fil')}")
            else:
                sett[pid] = str(p.get("_fil"))

    return feil


# --------------------------------------------------------------- evaluering


def _tall(verdi) -> float | None:
    try:
        return float(str(verdi).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _serie(kilde: str, entitet: str, felt: str, fra: str, til: str):
    """(utgangsverdi, observasjoner i vinduet) for én entitet og ett felt.

    Utgangsverdien hentes fra siste snapshot til og med `fra`. Uten den
    finnes ingen målestokk, og anslaget kan ikke avgjøres — det er et
    ærligere utfall enn å gjette en nullverdi.
    """
    from core import snapshot

    rammer = snapshot.les_mellom(kilde, fra, til)

    utgang = None
    i_vindu: list[tuple[str, str]] = []

    for dato, ramme in rammer:
        treff = ramme.filter(
            (pl.col("entity_id") == entitet) & (pl.col("field") == felt)
        )
        if treff.height == 0:
            continue
        verdi = str(treff["value"][0])
        if dato <= fra:
            utgang = verdi          # siste før eller på vindusstart vinner
        else:
            i_vindu.append((dato, verdi))

    return utgang, i_vindu


def _utfall(p: dict, utgang: str | None, i_vindu: list[tuple[str, str]]):
    if utgang is None:
        return "kan_ikke_avgjores", "ingen utgangsverdi ved vindusstart", None
    if not i_vindu:
        return "kan_ikke_avgjores", "ingen observasjoner i vinduet", None

    typ = p["type"]
    siste = i_vindu[-1][1]

    if typ == "verdi":
        mål = str(p["verdi"])
        for dato, verdi in i_vindu:
            if verdi == mål:
                return "traff", f"{felt_navn(p)} ble {mål} {dato}", verdi
        return "bom", f"{felt_navn(p)} ble aldri {mål} i vinduet", siste

    gammel = _tall(utgang)
    if gammel is None:
        return "kan_ikke_avgjores", f"utgangsverdi {utgang!r} er ikke et tall", siste
    if gammel == 0:
        # Samme fella som i signals.py: nullvernet mot divisjon spiser
        # den mest interessante hendelsen. Her sies det høyt i stedet
        # for å svare feil.
        return "kan_ikke_avgjores", "utgangsverdi er null, prosent er udefinert", siste

    terskel = float(p["terskel_prosent"])

    if typ == "endring":
        retning = p["retning"]
        for dato, verdi in i_vindu:
            ny = _tall(verdi)
            if ny is None:
                continue
            endring = (ny - gammel) / gammel * 100
            if retning == "opp" and endring >= terskel:
                return "traff", f"{endring:+.1f} % {dato}", verdi
            if retning == "ned" and endring <= -terskel:
                return "traff", f"{endring:+.1f} % {dato}", verdi
        nyeste = _tall(siste)
        faktisk = (nyeste - gammel) / gammel * 100 if nyeste is not None else 0.0
        return "bom", f"endte på {faktisk:+.1f} %, krevde {terskel} % {retning}", siste

    # type == "uendret"
    for dato, verdi in i_vindu:
        ny = _tall(verdi)
        if ny is None:
            continue
        endring = (ny - gammel) / gammel * 100
        if abs(endring) > terskel:
            return "bom", f"beveget seg {endring:+.1f} % {dato}", verdi
    return "traff", f"holdt seg innenfor ±{terskel} %", siste


def felt_navn(p: dict) -> str:
    return f"{p['entitet']}.{p['felt']}"


def forfalte(idag: str, prediksjoner: list[dict] | None = None) -> list[dict]:
    """Prediksjoner hvis vindu er lukket og som ikke er evaluert før.

    Anslag med formatfeil hoppes over. Uten det får et ugyldig anslag et
    resultat, havner i `alt_evaluert()`, og er dermed borte for godt i det
    øyeblikket YAML-en rettes — retting gjør det ikke evaluerbart igjen.

    Fanget ved å kjøre `run.py`, ikke av testene: et anslag med
    `vindu.fra == vindu.til` gikk i tilsyn-lista som det skulle, OG ble
    skrevet til resultatfila i samme kjøring.
    """
    prediksjoner = last() if prediksjoner is None else prediksjoner
    ferdige = alt_evaluert()
    return [
        p for p in prediksjoner
        if not _valider_en(p)
        and str((p.get("vindu") or {}).get("til") or "") <= idag
        and str(p.get("id")) not in ferdige
    ]


def evaluer(idag: str, prediksjoner: list[dict] | None = None) -> pl.DataFrame:
    """Avgjør alle forfalte anslag. Skriver ingenting."""
    rader = []
    for p in forfalte(idag, prediksjoner):
        vindu = p["vindu"]
        fra, til = str(vindu["fra"]), str(vindu["til"])
        utgang, i_vindu = _serie(p["kilde"], str(p["entitet"]), p["felt"], fra, til)
        utfall, begrunnelse, sluttverdi = _utfall(p, utgang, i_vindu)
        rader.append({
            "id": str(p["id"]),
            "entitet": str(p["entitet"]),
            "kilde": str(p["kilde"]),
            "felt": str(p["felt"]),
            "type": str(p["type"]),
            "utfall": utfall,
            "begrunnelse": begrunnelse,
            "utgangsverdi": utgang,
            "sluttverdi": sluttverdi,
            "vindu_fra": fra,
            "vindu_til": til,
            "evaluert_at": idag,
        })

    if not rader:
        return pl.DataFrame(schema=RESULTAT_SCHEMA)
    return pl.DataFrame(rader).select(list(RESULTAT_SCHEMA)).cast(RESULTAT_SCHEMA)


# --------------------------------------------------------------- resultater


def alt_evaluert() -> set[str]:
    """Id-ene som allerede har et resultat. Hindrer dobbeltevaluering."""
    if not RESULTAT_DIR.exists():
        return set()
    ider: set[str] = set()
    for sti in sorted(RESULTAT_DIR.glob("*.parquet")):
        ider.update(pl.read_parquet(sti)["id"].to_list())
    return ider


def skriv(resultater: pl.DataFrame, idag: str) -> Path | None:
    """Én fil per evalueringsdato. Samme append-only-mønster som
    changeloggen: en samlefil som skrives om hver uke vokser repoet
    kvadratisk i git."""
    if resultater.height == 0:
        return None
    RESULTAT_DIR.mkdir(parents=True, exist_ok=True)
    sti = RESULTAT_DIR / f"{idag}.parquet"
    n = 2
    while sti.exists():
        sti = RESULTAT_DIR / f"{idag}.{n}.parquet"
        n += 1
    resultater.write_parquet(sti)
    return sti


def treffrate() -> pl.DataFrame:
    """Treffrate per kilde og type, over alle avgjorte anslag.

    `kan_ikke_avgjores` telles for seg. Er den andelen høy, er det
    formatet eller kildedekningen som svikter — ikke dømmekraften.
    """
    if not RESULTAT_DIR.exists():
        return pl.DataFrame(schema={"kilde": pl.Utf8, "type": pl.Utf8})

    filer = sorted(RESULTAT_DIR.glob("*.parquet"))
    if not filer:
        return pl.DataFrame(schema={"kilde": pl.Utf8, "type": pl.Utf8})

    alle = pl.concat([pl.read_parquet(f) for f in filer], how="vertical")
    return (
        alle.group_by(["kilde", "type"])
        .agg(
            pl.len().alias("antall"),
            (pl.col("utfall") == "traff").sum().alias("traff"),
            (pl.col("utfall") == "bom").sum().alias("bom"),
            (pl.col("utfall") == "kan_ikke_avgjores").sum().alias("uavklart"),
        )
        .sort(["kilde", "type"])
    )
