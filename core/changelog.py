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

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import polars as pl

from core import domene
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


def skriv(endringer: pl.DataFrame, observed_at: str,
          versjon: int = 1) -> Path | None:
    """Skriver én kildes endringer for én dato. Returnerer stien, eller None.

    Fila er `changelog/<kilde>/<dato>.parquet`. Kilden leses ut av radene,
    så to kilder som gjelder for samme dato skriver til hver sin fil og kan
    ikke slette hverandre. En rekjøring av SAMME kilde samme dato
    overskriver sin egen fil, som før — loggen dobbeltføres ikke.

    ## Om `versjon`

    En kilde som REVIDERER fortiden skriver samme `observed_at` flere
    ganger, og den andre skrivingen er ikke en rekjøring av den første —
    den er et nytt utsagn om det samme tidspunktet. Snapshotet får da
    løpenummer (`<dato>.2.parquet`, se `snapshot._ledig_sti`), og
    changelog-fila skal bære det SAMME nummeret.

    Uten det ville revisjonsradene overskrevet bevegelsesradene for den
    måneden: `diff.compare()` skrev «mars mot februar» dit i sin tid, og
    `diff.revisjon()` ville lagt «mars mot mars» oppå. To ulike spørsmål,
    ett filnavn, og den førstes svar borte.

    Nummeret skal komme fra snapshotet som faktisk ble skrevet, ikke
    telles opp her — to tellere for samme sak er formen F6/F7 kostet oss.
    Kalleren leser det av stien `snapshot.write()` returnerte.

    `les_alt()` plukker begge opp: `_filer()` globber `*/*.parquet`, og
    `2018-03-31.2` sorterer etter `2018-03-31`.
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
    navn = f"{observed_at}.parquet" if versjon <= 1 \
        else f"{observed_at}.{versjon}.parquet"
    sti = mappe / navn
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


def merk_feltbevegelse(
    endringer: pl.DataFrame,
    kilder: Iterable[str] | None = None,
) -> pl.DataFrame:
    """Skiller «entiteten kom/gikk» fra «ET FELT kom/gikk».

    `diff.compare()` skriver `ny` og `borte` per (entitet, felt), og det
    er sant på feltnivå. Men et nettsted som samler radene per entitet og
    kaller resultatet «Ny i registeret», stiller et ANNET spørsmål enn
    det raden svarer på — og de to faller bare sammen når alle feltene
    kom samtidig.

    MÅLT 23.09.2026, uke 39, enhetsregisteret 14.09 -> 21.09:

        «ny»     7 entiteter, 0 av dem nye. Seks fikk `antall_ansatte`
                 for første gang, én `mva_registreringsdato`.
        «borte»  29 entiteter, 22 av dem faktisk borte. De sju andre
                 sto i begge snapshots og mistet bare `antall_ansatte`.

    ## Prøven er den samme som regel 3 krever: spør om DET du vil vite

    Ikke «hvor mange felt hadde raden» — det er en stedfortreder som er
    riktig helt til en entitet kommer inn med ett felt. Spørsmålet er om
    ENTITETEN står i snapshotet på den andre siden, og det er nøyaktig
    det som slås opp her.

    ## `kilder` begrenser oppslaget, ikke definisjonen

    1 569 (kilde, dato)-par i changeloggen har `ny`- eller `borte`-rader,
    og 1 528 av dem er lusetall og sjøtemperatur — to serier på 764 uker
    som ikke vises som ukesendringer i det hele tatt. Å lese 1 528
    snapshots for å svare på et spørsmål ingen stiller, er
    oppslagskostnaden og ikke regelen. Uten `kilder` gjelder den alle.

    Rader den IKKE rører, alle fire med samme begrunnelse som
    `merk_utvalgsutvidelse()` — å gjette ville undertrykt en ekte
    hendelse:

      * alt som ikke er `ny` eller `borte`
      * kilder utenfor `kilder`
      * rader der snapshotet på den andre siden ikke finnes
      * entiteter vi ikke finner igjen på noen av sidene
    """
    from core import diff, snapshot          # sent: unngår importsyklus

    if endringer.is_empty() or "change_type" not in endringer.columns:
        return endringer

    bare = frozenset(str(k) for k in kilder) if kilder is not None else None
    aktuelle = endringer.filter(pl.col("change_type").is_in(["ny", "borte"]))
    if bare is not None:
        aktuelle = aktuelle.filter(pl.col("source").is_in(sorted(bare)))
    if aktuelle.is_empty():
        return endringer

    # Entitetene i snapshotet FØR og snapshotet PÅ hver dato. Begge
    # trengs: `ny` spør om entiteten fantes før, `borte` om den finnes nå.
    for_par: dict[tuple[str, str], frozenset[str]] = {}
    naa_par: dict[tuple[str, str], frozenset[str]] = {}
    for kilde, dato in aktuelle.select(["source", "observed_at"]).unique().iter_rows():
        kilde, dato = str(kilde), str(dato)
        forrige = snapshot.previous(kilde, before=dato)
        if forrige is not None and not forrige.is_empty():
            for_par[(kilde, dato)] = frozenset(
                str(e) for e in forrige["entity_id"].to_list())
        naa = snapshot.les_mellom(kilde, dato, dato)
        if naa:
            naa_par[(kilde, dato)] = frozenset(
                str(e) for e in naa[-1][1]["entity_id"].to_list())

    def merk(rad: dict) -> str:
        ct = str(rad["change_type"])
        if ct not in ("ny", "borte"):
            return ct
        kilde, dato = str(rad["source"]), str(rad["observed_at"])
        if bare is not None and kilde not in bare:
            return ct
        par = (kilde, dato)
        før, naa = for_par.get(par), naa_par.get(par)
        if før is None or naa is None:
            return ct
        eid = str(rad["entity_id"])
        # BEGGE SIDER MÅ KJENNE ENTITETEN for at det skal være et felt
        # som flyttet seg. Er den bare på én side, er det entiteten.
        if eid in før and eid in naa:
            return diff.FELT_NY if ct == "ny" else diff.FELT_BORTE
        return ct

    nye = [merk(r) for r in endringer.iter_rows(named=True)]
    return endringer.with_columns(
        pl.Series("change_type", nye, dtype=pl.Utf8)
    )


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


# Kilder der en KROPP kan tie om en celle uten å ha fjernet den, og der
# de allerede skrevne radene derfor ikke kan leses som tilbaketrekkinger.
#
# Brukes bare av `merk_taushet()` under, altså på rader skrevet FØR
# `domene` fantes (15.09.2026). Rader fra og med da bærer domenet selv,
# og `diff` skriver ikke slike rader i det hele tatt.
#
# Lista er MÅLT, ikke antatt. 15.09.2026, over hele changeloggen, via
# kjeden published_at -> snapshotversjon -> raw_hash -> arkivkropp:
#
#     kilde              kropp uttømmende?   falske rader
#     trafikklysvedtak   NEI, § 4 har 3 rader   34 revidert + 8 borte
#     ekspertgruppen     NEI, tabellerer valgt   2 revidert + 40 borte
#     biomasse           JA, hele serien          0 av 1809
#     romming            JA, alle hendelser       0
#
# De øvrige kildene skriver `borte` fordi en entitet FAKTISK forsvant fra
# et register — lusetall 35587, sjotemperatur 12220 — og de skal ikke
# røres. Derfor en lukket liste og ikke en heuristikk: en kilde som ikke
# står her blir stående som før, og usikkerhet ser ut som usikkerhet.
TAUSHETSKILDER = frozenset({"trafikklysvedtak", "ekspertgruppen"})


def _taushet_av_domenet(rad: dict) -> bool | None:
    """Sier radens eget `domene` at dette var taushet? None = vet ikke.

    Raden alene er nok, og det er en følge av at bare DIFFERANSEN lagres:
    at `new_value` er null betyr at paret ikke ble emittert, så
    tilhørigheten til domenet avgjøres av differansen alene. Ingen
    snapshot trengs. Se core/domene.py.
    """
    fra_disk = str(rad.get("domene") or "")
    if not fra_disk:
        return None
    if fra_disk == domene.UTTOMMENDE:
        return False          # kroppen dekker alt: fraværet ER en fjerning
    lest = domene.les(fra_disk)
    if lest is None or lest == domene.UTTOMMENDE:
        return None
    return [str(rad["entity_id"]), str(rad["field"])] not in lest


def merk_taushet(endringer: pl.DataFrame,
                 kilder: frozenset[str] | None = None,
                 ogsaa_tidsaksen: bool = False) -> pl.DataFrame:
    """Merker rader som sier at noe forsvant, men der kilden bare TIDDE.
    Returnerer en NY ramme — rører ingen fil.

    Fra 15.09.2026 skriver `diff.compare()` og `diff.revisjon_mellom()`
    ikke slike rader i det hele tatt, fordi snapshotene da begynte å bære
    hvilke par kroppen uttaler seg om (`domene`). Radene som ble skrevet
    FØR det kan ikke rettes: changeloggen er append-only i praksis, og en
    fil som skrives om er den ene tingen dette repoet ikke gjør.

    Derfor merkes de ved LESING i stedet, nøyaktig som
    `merk_utvalgsutvidelse()` gjør det for den andre halvdelen av samme
    problem. Formen er den samme: rader skrevet etterpå bærer svaret
    selv, eldre rader må avgjøres av noe som fortsatt ligger der.

    To veier inn, i denne rekkefølgen:

      1. **Radens eget `domene`.** Presist, etterprøvbart fra raden
         alene.
      2. **`TAUSHETSKILDER`.** For rader uten domenet: kilder der det er
         MÅLT at kroppen kan tie. Se konstantens egen dokumentasjon for
         målingen og for hvorfor lista er lukket.

    ## Bare REVISJONSAKSEN, med mindre du ber om noe annet

    `revidert` sammenligner to kroppers syn på SAMME `observed_at`. Der er
    taushet en usann påstand: at 2026-forskriften ikke gjentar PO9s farge
    for 2024 betyr ikke at fargen ble trukket tilbake.

    `borte` sammenligner to ULIKE `observed_at`. «PO5 har ingen
    metode_bur_kategori i 2021» er sant om 2021 uansett hvorfor — året har
    ingen slik verdi hos oss. Målt 15.09.2026: av ekspertgruppens 358
    borte-rader er 318 et helt FELT som forsvant fra rapportserien, og at
    ekspertgruppen sluttet å bruke en metode er en ekte endring i hva
    kilden publiserer. Å merke dem `taushet` ville skjult den.

    `ogsaa_tidsaksen=True` tar med `borte` likevel. Den finnes fordi det
    gjenstår en svakhet der — for en kilde med hull er «borte» et HULL og
    ikke et fravær av verdi — men det er et annet spørsmål enn dette, og
    det skal avgjøres for seg. Se docs/KILDE-TRAFIKKLYSVEDTAK.md punkt 8.

    Rader den IKKE rører:
      * alt som ikke har `new_value = null`
      * `borte` (med mindre `ogsaa_tidsaksen`)
      * kilder som ikke står i `TAUSHETSKILDER` og som mangler domenet
      * rader der `domene` sier UTTOMMENDE — der ER fraværet en fjerning

    Alle fire lar raden stå. Å gjette ville snudd en ekte fjerning til en
    ikke-hendelse, og det er den motsatte feilen av den denne funksjonen
    finnes for.
    """
    from core import diff as diff_modul      # sent: unngår importsyklus

    if endringer.is_empty() or "change_type" not in endringer.columns:
        return endringer

    aktuelle = TAUSHETSKILDER if kilder is None else kilder
    har_domene = "domene" in endringer.columns

    gyldige = ({diff_modul.REVIDERT, "borte"} if ogsaa_tidsaksen
               else {diff_modul.REVIDERT})

    def merk(rad: dict) -> str:
        ct = str(rad["change_type"])
        if ct not in gyldige:
            return ct
        if rad.get("new_value") is not None:
            return ct
        if har_domene:
            sagt = _taushet_av_domenet(rad)
            if sagt is not None:
                return diff_modul.TAUSHET if sagt else ct
        return (diff_modul.TAUSHET
                if str(rad.get("source")) in aktuelle else ct)

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


def personentiteter() -> frozenset[tuple[str, str]]:
    """(kilde, entity_id) for hver entitet snapshotdøra fjerner.

    Spørsmålet stilles til `snapshot`, som EIER døra og er det ene
    stedet som leser rådata. En kopi av oppslaget her ville vært en
    andre lesevei, og `test_changelog_og_predictions_leser_ikke_raadata`
    nekter den — med rette: to dører som skal si det samme, er formen F6
    og F7 hadde.

    ## Hvorfor krysspeilingen, og ikke bare loggen selv

    18.09-notatet målte begge veier: en dør som bare leser loggens egne
    `organisasjonsform`- og `institusjonell_sektorkode`-rader fjerner
    376 av 379 og MISTER 3 — enkeltstående `endret`-rader uten et
    klassifiserende felt. «Skal alle 19 tas, må døra krysspeile
    snapshotene.» Den gjør det.
    """
    from core import snapshot

    return snapshot.personentiteter()


def fjern_personformer(endringer: pl.DataFrame) -> pl.DataFrame:
    """Changeloggens lesedør. Hele entiteten ut, ikke bare noen rader.

    ## Hvorfor den finnes fra 23.09.2026, og ikke før

    18.09-beslutningen lot de 381 radene ligge, og skrev ned hva som
    ville snudd valget: «En visning uten `entity_id`-filter — en
    oversiktsside, et søk, en 'endringer denne uka' på tvers av kilder,
    eller en CSV av loggen ved siden av sidene — fjerner vilkår 1 og 3
    samtidig.»

    Designrunden bygget nøyaktig det. `/endringer/<år>-<uke>/` er
    endringer denne uka på tvers av kilder, med CSV og JSON ved siden.
    MÅLT 23.09.2026 nådde én rad om en personform uke 39s side —
    `RØN GARD DA`, som `Ny i vårt utvalg` — og den hadde ikke noe navn
    på siden bare fordi entiteten var ute av snapshotet og oppslaget
    falt til en nøytral etikett. Det er ikke en beskyttelse; det er en
    tilfeldighet til.

    Notatet sa at valget skulle tas FØR visningen skrives. Det ble det
    ikke. Dette er alternativ 2, tatt etterpå.

    ## Den fjerner ikke historikken

    Radene blir liggende i `data/changelog/` som før — append-only
    gjelder. De forsvinner ved LESING, hver gang, som i
    `snapshot._les()`.
    """
    if endringer.is_empty() or "entity_id" not in endringer.columns:
        return endringer
    personer = personentiteter()
    if not personer:
        return endringer
    per_kilde: dict[str, set[str]] = {}
    for kilde, eid in personer:
        per_kilde.setdefault(kilde, set()).add(eid)

    behold = [
        str(e) not in per_kilde.get(str(k), ())
        for k, e in zip(endringer["source"].to_list(),
                        endringer["entity_id"].to_list())
    ]
    return endringer.filter(pl.Series(behold, dtype=pl.Boolean))


def les_alt(*, ufiltrert: bool = False) -> pl.DataFrame:
    """Hele endringsloggen, eldste først, gjennom lesedøra.

    Leser også den gamle samlefila hvis den finnes, så historikk fra før
    omleggingen ikke forsvinner. Analyselaget skal ikke måtte vite at
    formatet har endret seg.

    `ufiltrert=True` gir loggen slik den ligger på disk. Den finnes for
    revisjon — å måle hva døra fjerner krever å se begge sider — og skal
    ikke brukes av noe som skriver til nettstedet.
    """
    rammer = []

    if GAMMEL_FIL.exists():
        rammer.append(pl.read_parquet(GAMMEL_FIL))

    rammer.extend(pl.read_parquet(f) for f in _filer())

    if not rammer:
        from core.diff import CHANGE_SCHEMA

        return pl.DataFrame(schema=CHANGE_SCHEMA)

    alt = pl.concat(rammer, how="diagonal_relaxed").sort("observed_at")
    return alt if ufiltrert else fjern_personformer(alt)
