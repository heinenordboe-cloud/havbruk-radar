"""Endringsloggen. Én fil per kjøring, aldri en fil som skrives om.

Hvorfor dette ikke er én samlet changelog.parquet:

En parquet-fil komprimerer godt, men komprimert binærdata delta-komprimerer
elendig i git. Skriver du hele loggen på nytt hver uke, lagrer git en ny
nesten-full kopi hver gang — repostørrelsen vokser kvadratisk med tida, ikke
lineært. Etter to år er det forskjellen på noen megabyte og noen hundre.

Snapshotene i data/raw/ har alltid hatt riktig mønster: én fil per dato,
aldri rørt igjen. Her gjør vi det samme.

Bonuseffekt: en rekjøring samme dag overskriver sin egen fil i stedet for
å legge de samme radene til på nytt. Loggen kan ikke dobbeltføres.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from core.paths import CHANGELOG_DIR, GAMMEL_CHANGELOG as GAMMEL_FIL  # noqa: F401


def skriv(endringer: pl.DataFrame, observed_at: str) -> Path | None:
    """Skriver ukas endringer som egen fil. Returnerer stien, eller None."""
    if endringer.is_empty():
        return None

    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    sti = CHANGELOG_DIR / f"{observed_at}.parquet"
    endringer.write_parquet(sti)
    return sti


def skriv_per_dato(endringer: pl.DataFrame) -> list[Path]:
    """Én fil per OBSERVASJONSDATO, ikke én per kjøring.

    Etter at kilder fikk hver sin gyldighetsdato, kan én kjøring
    inneholde endringer med ulik `observed_at`: enhetsregisteret gjelder
    i dag, lusetall gjelder uka for fire uker siden. Skrives de i én fil
    navngitt etter kjøredatoen, arver changeloggen nøyaktig den feilen
    snapshotene nettopp ble kvitt.

    Fila navngis etter radenes egen dato, så navn og innhold ikke kan
    spriker. Rekkefølgen er eldste først, som `les_alt()` forventer.
    """
    skrevet = []
    grupper = sorted(endringer.group_by(["observed_at"]), key=lambda kv: kv[0])
    for (dato,), gruppe in grupper:
        sti = skriv(gruppe, str(dato))
        if sti is not None:
            skrevet.append(sti)
    return skrevet


# Kilder der en entitet bærer sin egen startdato, og hvilket felt det er.
#
# Brukes bare av merk_utvalgsutvidelse() under, altså på HISTORISKE rader
# som ble skrevet før diff.compare() kunne merke dem selv. Ordboka står
# her og ikke i core/diff.py fordi den er kildekunnskap: `registreringsdato`
# er Brregs ord. En kilde som ikke står her kan ikke etterprøves, og da
# blir radene stående som "ny" — usikkerhet skal se ut som usikkerhet.
STARTDATOFELT = {"enhetsregisteret": "registreringsdato"}


def merk_utvalgsutvidelse(
    endringer: pl.DataFrame,
    startdatofelt: dict[str, str] | None = None,
) -> pl.DataFrame:
    """Merker historiske «ny»-rader som i ettertid kan vises å være
    utvalgsutvidelse. Returnerer en NY ramme — rører ingen fil.

    Fra 24.08.2026 gjør `diff.compare()` dette selv, fordi snapshotene
    da begynte å bære med seg hva de ba om (`utvalg`-kolonnen). Radene
    som ble skrevet FØR det kan ikke rettes: changeloggen er append-only,
    og en fil som skrives om er den ene tingen dette repoet ikke gjør.

    Derfor merkes de ved LESING i stedet, og etterprøvbart:

        en entitet som er "ny" for oss, men hvis egen startdato ligger
        FØR snapshotet vi sammenlignet mot, kan ikke ha kommet inn fordi
        noe skjedde i verden. Den kom inn fordi vi begynte å se etter den.

    Testen er den samme som signalregelen `krev_dato_etter_forrige`
    bruker på ferske rader, og det er meningen: én definisjon av «ny i
    verden», brukt to steder.

    Den er også bredere enn årsaken den er navngitt etter. En utvidet
    næringskodeliste er ett svar på «hvorfor ble vår luke større»; en
    rettet paginering, et lettet filter eller et endepunkt som begynte å
    svare fullstendig er andre. Alle er samme klasse hendelse, og testen
    fanger dem alle uten å vite hvilken det var.

    Rader den IKKE rører:
      * alt som ikke er `change_type == "ny"`
      * kilder uten et kjent startdatofelt (`STARTDATOFELT`)
      * entiteter der startdatoen mangler i endringssettet
      * rader der vi ikke finner datoen det ble sammenlignet mot

    Alle fire lar raden stå som "ny". Å gjette ville undertrykt en ekte
    hendelse, og en undertrykt hendelse er en ingen får se.
    """
    from core import diff, snapshot          # sent: unngår importsyklus

    if endringer.is_empty() or "change_type" not in endringer.columns:
        return endringer

    felt_per_kilde = STARTDATOFELT if startdatofelt is None else startdatofelt

    # Datoen hver (kilde, observed_at) ble sammenlignet mot. Rader skrevet
    # fra 24.08 bærer den selv; eldre rader må slå den opp i snapshotene,
    # som fortsatt ligger der.
    baseline: dict[tuple[str, str], str] = {}
    par = endringer.select(["source", "observed_at"]).unique().iter_rows()
    for kilde, dato in par:
        kjent = ""
        if "forrige_observed_at" in endringer.columns:
            treff = endringer.filter(
                (pl.col("source") == kilde) & (pl.col("observed_at") == dato)
                & pl.col("forrige_observed_at").is_not_null()
                & (pl.col("forrige_observed_at") != "")
            )
            if not treff.is_empty():
                kjent = str(treff["forrige_observed_at"][0])
        if not kjent:
            forrige = snapshot.previous(str(kilde), before=str(dato))
            if forrige is not None and not forrige.is_empty():
                datoer = set(forrige["observed_at"].to_list())
                if len(datoer) == 1:
                    kjent = str(datoer.pop())
        if kjent:
            baseline[(str(kilde), str(dato))] = kjent

    # Entitetenes egne startdatoer, hentet fra endringssettet selv: en ny
    # entitet bringer med seg én rad per felt, så datoen ligger her.
    startdato: dict[tuple[str, str, str], str] = {}
    for kilde, felt in felt_per_kilde.items():
        rader = endringer.filter(
            (pl.col("source") == kilde) & (pl.col("field") == felt)
        ).select(["source", "observed_at", "entity_id", "new_value"])
        for k, d, e, v in rader.iter_rows():
            if v is not None:
                startdato[(str(k), str(d), str(e))] = str(v)

    def merk(rad: dict) -> str:
        if rad["change_type"] != "ny":
            return rad["change_type"]
        kilde, dato, eid = (str(rad["source"]), str(rad["observed_at"]),
                            str(rad["entity_id"]))
        if kilde not in felt_per_kilde:
            return "ny"
        mot = baseline.get((kilde, dato))
        egen = startdato.get((kilde, dato, eid))
        if not mot or not egen:
            return "ny"
        return diff.UTVALGSUTVIDELSE if egen <= mot else "ny"

    nye = [merk(r) for r in endringer.iter_rows(named=True)]
    return endringer.with_columns(
        pl.Series("change_type", nye, dtype=pl.Utf8)
    )


def _filer() -> list[Path]:
    if not CHANGELOG_DIR.exists():
        return []
    return sorted(CHANGELOG_DIR.glob("*.parquet"))


def les_alt() -> pl.DataFrame:
    """Hele endringsloggen, eldste først.

    Leser også den gamle samlefila hvis den finnes, så historikk fra før
    omleggingen ikke forsvinner. Analyselaget skal ikke måtte vite at
    formatet har endret seg.
    """
    rammer = []

    if GAMMEL_FIL.exists():
        rammer.append(pl.read_parquet(GAMMEL_FIL))

    rammer.extend(pl.read_parquet(f) for f in _filer())

    if not rammer:
        from core.diff import CHANGE_SCHEMA

        return pl.DataFrame(schema=CHANGE_SCHEMA)

    return pl.concat(rammer, how="diagonal_relaxed").sort("observed_at")
