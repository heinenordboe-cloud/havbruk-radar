"""Endringsloggen. Én fil per (kilde, dato), aldri en fil som skrives om.

Hvorfor dette ikke er én samlet changelog.parquet:

En parquet-fil komprimerer godt, men komprimert binærdata delta-komprimerer
elendig i git. Skriver du hele loggen på nytt hver uke, lagrer git en ny
nesten-full kopi hver gang — repostørrelsen vokser kvadratisk med tida, ikke
lineært. Etter to år er det forskjellen på noen megabyte og noen hundre.

Snapshotene i data/raw/ har alltid hatt riktig mønster: én fil per kilde per
dato, aldri rørt igjen. Her gjør vi det samme.

Bonuseffekt: en rekjøring av samme KILDE samme dato overskriver sin egen
fil i stedet for å legge de samme radene til på nytt. Loggen kan ikke
dobbeltføres.

## Hvorfor (kilde, dato) og ikke dato alene — F11

Fram til 25.08.2026 het fila `changelog/<dato>.parquet`, og `skriv()` gjorde
`write_parquet()` rett på den. Da var datoen alene nøkkelen, og to kilder som
gjaldt for samme dato kunne ikke sameksistere: den andre skrivingen slettet
den førstes rader.

Det traff. Sjøtemperatur-backfillen 24.08 skrev 238 datoer i 2012–2016 som
lusetall allerede eide, og lusetalls endringer for de datoene forsvant fra
arbeidstreet. De lå urørt i git, og changeloggen er avledet, så ingenting
gikk tapt permanent — men det var flaks, ikke design.

Merk hva som IKKE var årsaken: den ukentlige kjøringen er trygg. `run.py`
slår sammen alle kilders endringer til én ramme og kaller `skriv_per_dato()`
én gang, så to kilder med samme `observed_at` havner i samme fil sammen.
`2026-08-24.parquet` inneholder både akvakultur og enhetsregisteret og
beviser det. Kollisjonen krever to ADSKILTE skrivinger til samme dato:
backfill av én kilde om gangen, eller en kilde som hentes igjen senere fordi
den var rød i ukens kjøring. Begge er normale operasjoner i dette repoet, og
den siste er nøyaktig tilstanden sjotemperatur står i nå.

## Hvorfor ikke slå sammen ved skriving

Alternativet var å lese fila som ligger der, konkatenere og skrive tilbake.
Det ble valgt bort:

  - Det ER en omskriving. Rule 2 finnes fordi en fil som skrives om hver
    uke får git til å lagre en ny nesten-full kopi hver gang. En
    sammenslåing gjør changeloggen til akkurat den fila igjen — bare med
    flere skrivinger enn før, ikke færre.
  - Den kan ikke skille «erstatt mine egne rader fra en rekjøring» fra
    «legg til en annen kildes rader» uten en nøkkel den ikke har. Med
    (kilde, dato) i FILNAVNET er det skillet gratis: du overskriver din
    egen fil, og nabofilene finnes ikke for deg.
  - En avbrutt sammenslåing står igjen med en fil som har mistet den ene
    kildens rader og ikke fått den andres. Én skriving per fil kan bare
    lykkes eller la fila være.

Filnavnet bærer nå det samme som innholdet, som `raw/<kilde>/<dato>.parquet`
alltid har gjort — og kilden LESES ut av radene i stedet for å sendes inn
ved siden av dem, så navn og innhold ikke kan sprike (F6).

## Om de gamle flate filene

De 761 filene som ble skrevet før omleggingen ligger fortsatt som
`changelog/<dato>.parquet`, og `les_alt()` leser dem. De flyttes ikke:
en skrevet fil røres ikke, og glob-mønstrene skiller dem trivielt
(`*.parquet` mot `*/*.parquet`).

Det gir ett tvetydig tilfelle, og det avvises heller enn å gjettes: skriver
noen en kilde på nytt for en dato der den gamle flate fila allerede
inneholder den kilden, ville `les_alt()` telt radene to ganger. `skriv()`
kaster da, med beskjed om hvilken fil som er i veien.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from core.paths import CHANGELOG_DIR, GAMMEL_CHANGELOG as GAMMEL_FIL  # noqa: F401


class Kildekollisjon(RuntimeError):
    """En skriving ville fått `les_alt()` til å telle de samme radene to
    ganger, fordi den gamle flate fila for datoen allerede bærer kilden.

    Egen type fordi den betyr noe annet enn en I/O-feil: ingenting er galt
    med dataene, men layouten fra før omleggingen kan ikke uttrykke det som
    skal skrives. Se modulens docstring.
    """


def _kilden_i(endringer: pl.DataFrame) -> str:
    """Kilden radene tilhører. Kastet hvis de ikke er enige.

    Leses UT AV radene i stedet for å sendes inn ved siden av dem: filnavnet
    skal si det samme som innholdet, og to argumenter som kan sprike er
    nøyaktig formen F6 kostet oss.
    """
    if "source" not in endringer.columns:
        raise ValueError(
            "Endringene mangler `source`-kolonnen, og da kan ikke fila "
            "navngis etter kilden. Kom rammen utenom diff.compare()?"
        )
    kilder = endringer["source"].unique().to_list()
    if len(kilder) != 1:
        raise ValueError(
            f"Endringene bærer {len(kilder)} kilder ({sorted(kilder)}), og "
            f"én fil bærer én kilde. Bruk skriv_per_dato(), som grupperer "
            f"på (dato, kilde) før den skriver."
        )
    return str(kilder[0])


def _gammel_flat_fil(observed_at: str, kilde: str) -> Path | None:
    """Den flate fila fra før omleggingen, HVIS den allerede har kilden.

    Finnes den uten kilden — det vanlige, f.eks. lusetall i 2012–2016 mens
    sjotemperatur backfilles inn ved siden av — er det ingen kollisjon:
    de to filene bærer hver sine rader, og `les_alt()` konkatenerer dem.
    """
    flat = CHANGELOG_DIR / f"{observed_at}.parquet"
    if not flat.exists():
        return None
    try:
        kilder = set(pl.read_parquet(flat, columns=["source"])["source"].to_list())
    except Exception:
        # Uleselig gammel fil skal ikke blokkere en ny skriving. Den blir
        # uansett oppdaget av les_alt(), som er stedet å si fra om den.
        return None
    return flat if kilde in kilder else None


def skriv(endringer: pl.DataFrame, observed_at: str) -> Path | None:
    """Skriver én kildes endringer for én dato. Returnerer stien, eller None.

    Fila er `changelog/<kilde>/<dato>.parquet`. Kilden leses ut av radene,
    så to kilder som gjelder for samme dato skriver til hver sin fil og kan
    ikke slette hverandre. En rekjøring av SAMME kilde samme dato
    overskriver sin egen fil, som før — loggen dobbeltføres ikke.
    """
    if endringer.is_empty():
        return None

    kilde = _kilden_i(endringer)

    i_veien = _gammel_flat_fil(observed_at, kilde)
    if i_veien is not None:
        raise Kildekollisjon(
            f"{i_veien.name} er fra før changeloggen ble indeksert på "
            f"(kilde, dato), og inneholder allerede rader fra {kilde!r} for "
            f"{observed_at}. Skrives {kilde}/{observed_at}.parquet nå, "
            f"teller les_alt() de samme endringene to ganger. Fila er "
            f"append-only og flyttes ikke av seg selv — avgjør for hånd "
            f"om den skal beholdes eller erstattes."
        )

    mappe = CHANGELOG_DIR / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    sti = mappe / f"{observed_at}.parquet"
    endringer.write_parquet(sti)
    return sti


def skriv_per_dato(endringer: pl.DataFrame) -> list[Path]:
    """Én fil per (KILDE, OBSERVASJONSDATO), ikke én per kjøring.

    Etter at kilder fikk hver sin gyldighetsdato, kan én kjøring
    inneholde endringer med ulik `observed_at`: enhetsregisteret gjelder
    i dag, lusetall gjelder uka for fire uker siden. Skrives de i én fil
    navngitt etter kjøredatoen, arver changeloggen nøyaktig den feilen
    snapshotene nettopp ble kvitt.

    Grupperingen tar kilden med seg fordi to kilder kan dele dato —
    lusetall og sjotemperatur har samme etterslep og gjør det hver uke.
    Delte de fil, ville den ene kildens rader vært den andres å slette
    neste gang én av dem hentes alene. Se modulens docstring om F11.

    Fila navngis etter radenes egen dato og egen kilde, så navn og innhold
    ikke kan sprike. Rekkefølgen er eldste først, som `les_alt()` forventer.
    """
    skrevet = []
    grupper = sorted(endringer.group_by(["observed_at", "source"]),
                     key=lambda kv: kv[0])
    for (dato, _kilde), gruppe in grupper:
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
    """Alle changelog-filer, begge layouter.

    `*.parquet` er de flate filene fra før 25.08.2026, `*/*.parquet` er
    `<kilde>/<dato>.parquet`. Sorteres på DATOEN (filnavnet) og ikke på
    hele stien, ellers ville kildemappa bestemt rekkefølgen og les_alt()
    fått 2012 fra sjotemperatur før 2011 fra lusetall.
    """
    if not CHANGELOG_DIR.exists():
        return []
    flate = list(CHANGELOG_DIR.glob("*.parquet"))
    per_kilde = list(CHANGELOG_DIR.glob("*/*.parquet"))
    return sorted(flate + per_kilde, key=lambda p: (p.stem, p.parent.name))


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
