"""Tidsaksen: én rad per lokalitet og ISO-uke, med alle lagene.

    python tidsakse.py                                   # til data/tidsakse/
    python tidsakse.py --ut <mappe>
    python tidsakse.py --kjent-til 2026-11-04T06:00:00+00:00

Hendelsesvarselet, syklusstripa, anslagene og forsprangsloggen skal være
spørsmål mot denne tabellen, ikke hver sin lesing av snapshotene.
`analyse/maling_okt/p4_panel.py` gjorde det samme for PO 4 og to lag;
dette er den generelle. Målingen bak står i docs/MALING-TIDSAKSE.md.

## Hvor den bor

Tidsaksen er AVLEDET: en ren funksjon av snapshotene (og to arkivkropper
der det ikke finnes snapshot), bygget på nytt hver gang. Den skrives
derfor ikke i `data/raw/` og committes ikke, men legges i
`data/tidsakse/` ved siden av `data/kildeledd/` og `data/nettsted/`, som
er ignorert i datarepoet av samme grunn: en fil som skrives om ved hver
bygging, får git til å vokse kvadratisk (ARKITEKTUR.md, «Append-only»).
Koden står i rota ved siden av kildeledd.py, ikke i `core/`: den leser
gjennom `analyse.kjoringslogg` og bruker reglene i `paastand.py` og
`nettsted.py`, og kjernen skal ikke avhenge av noen av dem.

## Tre filer

    tidsakse.parquet    én rad per (lokalitet, uke): lagenes verdier
    hendelser.parquet   det som ENDRET seg, med første fil og stempeltid:
                        forsprangsloggen, adskilt fra måleseriene
    konflikter.parquet  to kilder uenige om samme lokalitet og uke

og `tidsakse.kjoring.log`, som sier hva som ble lest.

## En celle er verdi, kilde og gjelder-dato

Hvert lag har kolonnene `<lag>__<felt>` (verdien, ordrett som tekst,
slik snapshotene lagrer den), `<lag>__kilde` og `<lag>__gjelder`. Det er
de tre leddene i `paastand.Paastand`, og `paastand_for()` gjør en celle
om til en: nivået står i `FELTER`, ikke på hver rad, fordi det er en
egenskap ved feltet og ikke ved uka. `gjelder` handler om VERDEN
(CLAUDE.md 1b-7): mandagen for en lusetalluke, månedsslutten for en
biomasserapport, ikrafttredelsen for et vedtak, snapshotdagen for et
registerfelt.

## Tomt er tomt

En uke der laget ikke finnes, er tom (null): ikke «0», ikke «nei», og
ikke forrige ukes verdi. Det gjelder også ukene inne i et lag:

  * eierskap mangler uke 37/2026, og den uka er tom selv om uka før og
    etter har samme eier,
  * biomasselaget står bare i uka med månedsslutten,
  * behandling står bare i uker der begge flaggene lever (R8, og
    `dodt_fra` i config.yml): 2012–2023, tom etter, ikke «nei»,
  * sykdom står fra uke 48/2024 (R5 F2.2), tom før,
  * eierkoblingen finnes fra 17.08.2026 og fylles aldri bakover (M25).

## Konflikter

Følger parene i R2 (havbruk-analyse analyse/a2-uenige-registre/):
P1 eier mot Enhetsregisteret, P2 tillatelsene på lokaliteten, P3
biomasselaget mot BarentsWatch (`paastand.konflikt`, samme periode og
arter). P4–P6 kan ikke oppstå her: snapshotene har én eier per felt for
koordinater, kommune og PO (MALING-TIDSAKSE F12.1). I tillegg sykdom
mot registeret: en åpen sak på en lokalitet som ingen av registrene har
den uka. En konflikt slås aldri sammen: begge verdiene står i hvert sitt
lag, og `konflikt` på raden sier hvilke par som er uenige.

## Hendelser

Typene R9 trenger (havbruk-analyse revisjon/2026-11-09-varsel-segment1/),
med R9-nummeret ved siden av. Hver hendelse har FØRSTE fil som viste den,
når vi hentet den, og manifestet som stemplet den (`data/stempler/`).
Første omtale er UBELAGT til omtalearkivet finnes: ingen gjetning.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

ROT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROT))

import paastand                                   # noqa: E402
from analyse import kjoringslogg                  # noqa: E402  (lesedøra)
from core import config, feltnormal, paths, snapshot  # noqa: E402

OSLO = ZoneInfo("Europe/Oslo")

# Første uke på aksen: mandag i uke 1/2012, der den ukentlige grunnen
# (lusetall) begynner. Biomasselagets 23 påstander fra før står utenfor
# aksen (MALING-TIDSAKSE F7.1).
AKSE_START = "2012-01-02"

# Koblingen lokalitet–tillatelse–innehaver finnes fra denne dagen og
# fylles aldri bakover (M25, havbruk-analyse revisjon/2026-11-10-slakteanslag/).
EIERKOBLING_FRA = "2026-08-17"

# Sykdom: Mattilsynets kropp, og uka den er hel fra (R5 F2.2, beslutningen).
SYKDOM_KROPP = "maling-ilapd/2026-11-04.json.gz"
SYKDOM_LOGG = "maling-ilapd/2026-11-04.i2.logg.json"
SYKDOM_SHA256 = "890117f9a349175a61885ecd5505350b99fc57ef52b2907ecd5cee9f63a3407a"
SYKDOM_FRA = "2024-11-25"
ILA, PD = "INFEKSIØS_LAKSEANEMI", "PANKREASSYKDOM"
# Mattilsynets stedfortreder for ukjent dato (R5 F1.1, tillegg 1.1).
UKJENT_DATO = "1959-12-31T23:00:00Z"

# Trafikklyset for de sju 2026-cellene: forskriftens ord, ikke en farge
# (beslutningen; MALING-TIDSAKSE F6.2). Setningen LESES av kroppen ved
# hver bygging (`ordlyd_2026()`); konstanten er det den skal si.
TRAFIKKLYS_KROPP = "trafikklysvedtak/2026-12-31.bin.gz"
TRAFIKKLYS_SHA256 = "08b6090d993b96444ba54043079382de2a25750f571b7b98414158bc7abc4cd8"
FORSKRIFT_2026 = "FOR-2026-08-20-1764 § 4"
ORDLYD_2026 = ("Tillatelser hjemmehørende i øvrige produksjonsområder kan "
               "utnyttes 100 prosent.")

UBELAGT = "UBELAGT"

UT_DIR = paths.DATA_DIR / "tidsakse"
TABELL, HENDELSER, KONFLIKTER = ("tidsakse.parquet", "hendelser.parquet",
                                 "konflikter.parquet")
LOGGNAVN = "tidsakse.kjoring.log"


# ------------------------------------------------------------------ lagene
#
# (lag, felt) -> (nivå, periode). Nivået er paastand.py sitt. Kolonnen i
# tabellen er `<lag>__<felt>`. Navn på lokaliteter og selskaper står ikke
# her med vilje: tidsaksen bærer nummer og orgnr (MALING-TIDSAKSE F12.2).

O, R, V = paastand.OPPGITT, paastand.REGNET, paastand.VURDERT
DAG, UKE = paastand.DAG, paastand.UKE

REGISTERFELT = ("kapasitet", "kapasitet_midlertidig", "kapasitet_enhet",
                "versjon_status", "versjon_gyldig_fra", "versjon_aarsak",
                "klareringstype", "forste_klarering",
                "har_kommersiell_aktivitet", "arter", "breddegrad",
                "lengdegrad", "plasseringstype", "vanntype", "er_slakteri",
                "har_samdrift", "har_samlokalisering", "tillatelser",
                "tillatelser_trukket")
STEDFELT = ("prodomraade_kode", "kommunenummer", "fylkesnummer")
LUSFELT = ("brakklagt", "har_laksefisk", "er_landbasert", "er_slaktemerd",
           "lus_er_rapportert", "voksne_hunnlus", "har_mekanisk_fjerning",
           "har_medikamentell_behandling", "har_rensefisk")
BEHANDLINGSFLAGG = ("har_mekanisk_fjerning", "har_medikamentell_behandling")
SJOFELT = ("lusegrense", "sjotemperatur", "temperatur_er_rapportert")
BIOFELT = ("har_fisk", "arter_tilstede", "lokalitet_status", "hentet")
SELSKAPSFELT = ("organisasjonsform", "er_i_konsern", "konkurs",
                "under_avvikling", "under_tvangsavvikling", "naeringskode")

FELTER: dict[tuple[str, str], tuple[str, str]] = {}
for _f in REGISTERFELT:
    FELTER[("register", _f)] = (O, DAG)
for _f in STEDFELT:
    FELTER[("sted", _f)] = (O, DAG)
for _f in ("omraade", "datasett", "status"):
    FELTER[("regomr", _f)] = (R, DAG)
for _f in ("runde", "farge", "lesemaate", "kapasitetsjustering", "forskrift"):
    FELTER[("trafikklys", _f)] = (O, DAG)
for _f in ("tillatelser", "eier_orgnr", "antall_eiere"):
    FELTER[("eierskap", _f)] = (O, DAG)
for _f in ("selskap_orgnr", "mtb_tn", "personform_utelatt"):
    FELTER[("eierskap", _f)] = (R, DAG)
for _f in SELSKAPSFELT:
    FELTER[("selskap", _f)] = (O, DAG)
for _f in BIOFELT:
    FELTER[("biomasselag", _f)] = (O, DAG)
for _f in LUSFELT:
    # BarentsWatchs «brakklagt» er «Trolig uten fisk»: kildens egen
    # slutning, ikke en innrapportering (paastand.py, VURDERT).
    FELTER[("lus", _f)] = (V if _f == "brakklagt" else O, UKE)
for _f in SJOFELT:
    FELTER[("sjo", _f)] = (O, UKE)
for _f in ("grunn", "grunn_ukjent", "lus", "behandling", "sykdom"):
    FELTER[("stripe", _f)] = (R, UKE)
for _f in ("ila", "ila_gjelder", "pd", "pd_gjelder", "per_hentedato"):
    FELTER[("sykdom", _f)] = (R, UKE)
for _f in ("resultat", "kobling", "saksnummer"):
    FELTER[("unntaksvekst", _f)] = (O, DAG)
for _f in ("nokkel", "tonn", "kommuner"):
    FELTER[("havbruksfond", _f)] = (R, DAG)

LAG = tuple(dict.fromkeys(lag for lag, _ in FELTER))


def kolonne(lag: str, felt: str) -> str:
    return f"{lag}__{felt}"


# ------------------------------------------------------------- tid og uker


def mandag_av(dato: str) -> str:
    d = dt.date.fromisoformat(dato[:10])
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def uke_av(dato: str) -> str:
    aar, nr, _ = dt.date.fromisoformat(dato[:10]).isocalendar()
    return f"{aar}-W{nr:02d}"


def mandager(fra: str, til: str) -> list[str]:
    a, b = dt.date.fromisoformat(mandag_av(fra)), dt.date.fromisoformat(mandag_av(til))
    ut = []
    while a <= b:
        ut.append(a.isoformat())
        a += dt.timedelta(days=7)
    return ut


def oslodag(tid: str | None) -> str | None:
    """Kalenderdagen i Europe/Oslo for et UTC-tidspunkt, som R5 leser
    Mattilsynets datoer og R8 `firstClearanceTime`. None for ukjent."""
    if not tid or tid == UKJENT_DATO:
        return None
    t = dt.datetime.fromisoformat(tid.replace("Z", "+00:00"))
    return t.astimezone(OSLO).date().isoformat()


def _tid(tid: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(tid.replace("Z", "+00:00")) if tid else None


def _lokkey(x: str) -> tuple:
    return (0, int(x), "") if x.isdigit() else (1, 0, x)


# ---------------------------------------------------------------- lesingen


@dataclass(frozen=True)
class Snap:
    """Ett snapshot slik det gikk inn: kilde, dato, løpenummer, ramme."""
    kilde: str
    dato: str
    nr: int
    ramme: pl.DataFrame

    @property
    def fil(self) -> str:
        return f"{self.dato}.parquet" if self.nr == 1 else f"{self.dato}.{self.nr}.parquet"

    @property
    def hentet(self) -> str:
        """`fetched_at`: når VI hentet det (1b-7), tom når radene spriker."""
        return snapshot.fetched_at_i(self.ramme) or ""


def les(logg: kjoringslogg.Kjoringslogg, kilde: str,
        kjent_til: str | None, alle: bool = False) -> list[Snap]:
    """Gjeldende snapshot per dato, gjennom døra, hentet senest `kjent_til`.

    «Gjeldende» som `snapshot.gjeldende()`: nyeste hele versjon, ellers
    nyeste. `alle=True` gir hver versjon, eldst utgitt først, for kilder der
    en nyere versjon bare uttaler seg om en del av datoen (trafikklysets
    eldre runder, eierskapshistorikkens årsfiler). Med `kjent_til` velges blant versjonene vi HADDE da, slik at
    tidsaksen kan bygges som den ville sett ut på et tidspunkt — det er
    spørsmålet M25s look-ahead handlet om.
    """
    grense = _tid(kjent_til)
    foer = len(logg.lesinger)
    lest = logg.les(kilde, "0001-01-01", "9999-12-31",
                    versjonsvalg=kjoringslogg.ALLE)
    nye = logg.lesinger[foer:]
    if len(nye) != len(lest):
        raise RuntimeError(f"{kilde}: loggen og lesingen er ulike lange")
    per: dict[str, list[tuple[int, pl.DataFrame]]] = defaultdict(list)
    for (dato, ramme), lesing in zip(lest, nye):
        hentet = _tid(snapshot.fetched_at_i(ramme))
        if grense is not None and (hentet is None or hentet > grense):
            continue
        per[dato].append((lesing.versjon, ramme))
    ut = []
    for dato in sorted(per):
        versjoner = per[dato]
        if alle:
            # Eldst utgitt først, som `snapshot.versjoner()` leverer dem.
            ut += [Snap(kilde, dato, nr, ramme) for nr, ramme in versjoner]
            continue
        hele = [v for v in versjoner if not snapshot.ufullstendig_i(v[1])]
        nr, ramme = (hele or versjoner)[-1]
        ut.append(Snap(kilde, dato, nr, ramme))
    return ut


def bred(snaps: list[Snap], felter: tuple[str, ...]) -> pl.DataFrame:
    """Snapshotene som én bred ramme: entity_id, dato, fil, fetched_at, felt…"""
    skjema = {"entity_id": pl.Utf8, "dato": pl.Utf8, "fil": pl.Utf8,
              "fetched_at": pl.Utf8, **{f: pl.Utf8 for f in felter}}
    deler = []
    for s in snaps:
        r = (s.ramme.filter(pl.col("field").is_in(list(felter)))
             .select("entity_id", "field", "value"))
        if r.is_empty():
            continue
        # Samme felt to ganger for én entitet: like verdier slås sammen
        # (MÅLT 11.11.2026 i enhetsregisteret 16.–17.08.2026: 134 og 471 par,
        # alle med samme verdi). Ulike verdier er to påstander om én ting,
        # og da finnes ingen ÉN verdi å sette i cellen.
        r = r.unique(maintain_order=True)
        dobbel = r.group_by("entity_id", "field").len().filter(pl.col("len") > 1)
        if not dobbel.is_empty():
            raise ValueError(f"{s.kilde}/{s.fil}: ulike verdier i samme felt for én entitet")
        deler.append(r.with_columns(pl.lit(s.dato).alias("dato"),
                                    pl.lit(s.fil).alias("fil"),
                                    pl.lit(s.hentet).alias("fetched_at")))
    if not deler:
        return pl.DataFrame(schema=skjema)
    lang = pl.concat(deler)
    ut = lang.pivot(on="field", index=["entity_id", "dato", "fil", "fetched_at"],
                    values="value", aggregate_function="first")
    for f in felter:
        if f not in ut.columns:
            ut = ut.with_columns(pl.lit(None, dtype=pl.Utf8).alias(f))
    return ut.select(list(skjema)).cast(skjema)


MANDAG_AV_DATO = (pl.col("dato").str.slice(0, 10).str.to_date().dt.truncate("1w")
                  .dt.strftime("%Y-%m-%d"))


def per_uke(ramme: pl.DataFrame) -> pl.DataFrame:
    """Én rad per (entitet, ISO-uke): den SISTE datoen i uka.

    Målt 11.11.2026: ingen ukentlig kilde har to datoer i samme uke
    (MALING-TIDSAKSE F1.1). Regelen står for den dagen det skjer.
    """
    return (ramme.with_columns(MANDAG_AV_DATO.alias("mandag"))
            .sort("dato")
            .group_by("entity_id", "mandag", maintain_order=True).last())


def lag_ramme(lag: str, ramme: pl.DataFrame, kilde: str | pl.Expr,
              gjelder: pl.Expr, felter: tuple[str, ...],
              nokkel: str = "entity_id") -> pl.DataFrame:
    """(lokalitet, mandag, <lag>__kilde, <lag>__gjelder, <lag>__<felt>…)."""
    kilde_e = pl.lit(kilde) if isinstance(kilde, str) else kilde
    return ramme.select(
        pl.col(nokkel).alias("lokalitet"), "mandag",
        kilde_e.cast(pl.Utf8).alias(kolonne(lag, "kilde")),
        gjelder.cast(pl.Utf8).alias(kolonne(lag, "gjelder")),
        *[pl.col(f).cast(pl.Utf8).alias(kolonne(lag, f)) for f in felter])


# ------------------------------------------------------- R8: flagg som lever


def levende_uker(lus: pl.DataFrame, felt: str, maks: int,
                 dodt_fra: str | None) -> set[str]:
    """Ukene flagget lever i, etter R8 (havbruk-analyse
    revisjon/2026-11-09-syklusstripe/, B) og config.yml `dodt_fra`.

    Et flagg er dødt i et strekk på OVER `maks` uker der ingen lokalitet i
    universet har det `True`. `dodt_fra` er repoets kvittering for et
    dødsfall målt utenfra; uker fra og med den datoen er døde uansett.
    Uten den ville R8s regel alene gitt 2024-11-11 som levende for
    medikamentflagget (R8 F2.2, MALING-TIDSAKSE F8.2).
    """
    univ = lus.filter((pl.col("har_laksefisk") == "True")
                      & (pl.col("er_landbasert") == "False")
                      & (pl.col("er_slaktemerd") == "False"))
    sann = set(univ.filter(pl.col(felt) == "True")["mandag"].unique().to_list())
    uker = sorted(lus["mandag"].unique().to_list())
    dode: set[str] = set()
    i = 0
    while i < len(uker):
        if uker[i] in sann:
            i += 1
            continue
        j = i
        while j < len(uker) and uker[j] not in sann:
            j += 1
        if j - i > maks:
            dode.update(uker[i:j])
        i = j
    return {u for u in uker if u not in dode and (not dodt_fra or u < dodt_fra)}


# ------------------------------------------------------------- R5: sykdom


@dataclass(frozen=True)
class Tilfelle:
    lokalitet: str
    sykdom: str              # "ila" | "pd"
    mistanke: str | None
    diagnose: str | None
    avsluttet: str | None

    def status(self, dag: str) -> str | None:
        """R5 tillegg 1.1: status ved slutten av `dag` (Oslo)."""
        starter = [d for d in (self.mistanke, self.diagnose) if d]
        if self.avsluttet and starter and self.avsluttet < min(starter):
            return "uavklart"
        if self.avsluttet and self.avsluttet <= dag:
            return "avsluttet"
        if self.diagnose and self.diagnose <= dag:
            return "påvist"
        if self.mistanke and self.mistanke <= dag:
            return "mistanke"
        return None

    def siden(self, stadium: str) -> str:
        return (self.diagnose if stadium == "påvist" else self.mistanke) or ""


def les_sykdom(kjent_til: str | None) -> tuple[list[Tilfelle], dict] | None:
    """Mattilsynets tilfeller, eller None hvis kroppen ikke finnes i arkivet
    eller ikke var hentet ennå (`kjent_til`). Da er sykdomslaget tomt."""
    fil = paths.ARKIV_DIR / SYKDOM_KROPP
    if not fil.exists():
        return None
    rå = gzip.open(fil, "rb").read()
    sha = hashlib.sha256(rå).hexdigest()
    if sha != SYKDOM_SHA256:
        raise ValueError(f"{SYKDOM_KROPP} har sha256 {sha}, ikke R5s {SYKDOM_SHA256}")
    logg = json.loads((paths.ARKIV_DIR / SYKDOM_LOGG).read_text(encoding="utf-8"))
    hentet = logg[0]["fetched_at"]
    if kjent_til and _tid(hentet) > _tid(kjent_til):
        return None
    ut = []
    for t in json.loads(rå):
        if t.get("ugyldiggjøringsdato"):
            continue
        sykdom = {ILA: "ila", PD: "pd"}.get(t.get("sykdomstype"))
        if not sykdom:
            continue
        ut.append(Tilfelle(str(t["lokalitetsnummer"]), sykdom,
                           oslodag(t.get("kvalitetssikretMistankedato")),
                           oslodag(t.get("diagnosedato")),
                           oslodag(t.get("avslutningsdato"))))
    ut.sort(key=lambda x: (_lokkey(x.lokalitet), x.sykdom, x.mistanke or "",
                           x.diagnose or "", x.avsluttet or ""))
    return ut, {"fil": SYKDOM_KROPP, "sha256": sha, "hentet": hentet,
                "hentedag": oslodag(hentet)}


def sykdom_per_uke(tilf: list[Tilfelle], meta: dict) -> pl.DataFrame:
    """(lokalitet, mandag, ila, ila_gjelder, pd, pd_gjelder, per_hentedato)
    for hver uke fra uke 48/2024 til hentingsuka, for lokaliteter med en sak.

    «Ingen aktiv sak» for lokaliteter uten sak legges på etterpå, og bare
    der et register har lokaliteten den uka (R5: fravær betyr «ingen aktiv
    sak» for lokaliteter i registeret, og det er en antakelse).
    """
    hentedag = meta["hentedag"]
    uker = mandager(SYKDOM_FRA, hentedag)
    per: dict[tuple[str, str], list[Tilfelle]] = defaultdict(list)
    for t in tilf:
        per[(t.lokalitet, t.sykdom)].append(t)
    rader = []
    for lok in sorted({t.lokalitet for t in tilf}, key=_lokkey):
        for m in uker:
            sondag = (dt.date.fromisoformat(m) + dt.timedelta(days=6)).isoformat()
            per_hentedato = sondag >= hentedag
            dag = hentedag if per_hentedato else sondag
            rad = {"lokalitet": lok, "mandag": m,
                   "per_hentedato": hentedag if per_hentedato else None}
            for sykdom in ("ila", "pd"):
                aktive = [(t, s) for t in per.get((lok, sykdom), [])
                          if (s := t.status(dag)) in ("mistanke", "påvist", "uavklart")]
                stadier = {s for _, s in aktive}
                if not aktive:
                    rad[sykdom], rad[f"{sykdom}_gjelder"] = "ingen aktiv sak", dag
                elif len(stadier) == 1 and stadier != {"uavklart"}:
                    s = stadier.pop()
                    rad[sykdom] = s
                    rad[f"{sykdom}_gjelder"] = max(t.siden(s) for t, _ in aktive)
                else:
                    rad[sykdom], rad[f"{sykdom}_gjelder"] = "uavklart", dag
            rader.append(rad)
    skjema = {k: pl.Utf8 for k in ("lokalitet", "mandag", "per_hentedato", "ila",
                                   "ila_gjelder", "pd", "pd_gjelder")}
    return pl.DataFrame(rader, schema=skjema)


AKTIV = ("mistanke", "påvist", "uavklart")


# ------------------------------------------------------------- stempler


class Stempler:
    """Første manifest som fører en fil, og om det er forankret.

    Regelen er `nettsted._stempelindeks()`: står fila i flere manifester,
    gjelder det første. Summen er over FILAS bytes, som i manifestene.
    """

    def __init__(self) -> None:
        import nettsted
        self.indeks = nettsted._stempelindeks()
        self._sha: dict[Path, str] = {}

    def __call__(self, fil: Path, sti: str) -> tuple[str, str]:
        if not fil.exists():
            return "", ""
        if fil not in self._sha:
            self._sha[fil] = hashlib.sha256(fil.read_bytes()).hexdigest()
        return self.indeks.get((self._sha[fil], sti), ("", ""))


def _manifeststi(rel: str) -> str:
    return f"havbruk-radar-data/data/{rel}"


# ------------------------------------------------------------- byggingen


@dataclass
class Resultat:
    tabell: pl.DataFrame
    hendelser: pl.DataFrame
    konflikter: pl.DataFrame
    logg: kjoringslogg.Kjoringslogg


def bygg(kjent_til: str | None = None,
         logg: kjoringslogg.Kjoringslogg | None = None) -> Resultat:
    """Hele tidsaksen. Ren funksjon av snapshotene og de to kroppene."""
    import nettsted
    from sources import reguleringsomraader as regomr_kilde
    from sources.eierskap import FORM_KART

    logg = logg or kjoringslogg.Kjoringslogg("tidsakse", UT_DIR / LOGGNAVN)
    logg.valg("akse.start", AKSE_START)
    logg.valg("kjent_til", kjent_til or "(ingen grense)")
    maks = int(config.get("kilder.lusetall.maks_nullstrekk",
                          feltnormal.STANDARD_MAKS_NULLSTREKK))
    dodt_fra = config.get("kilder.lusetall.dodt_fra", {}) or {}
    logg.valg("behandling.maks_nullstrekk", maks)
    logg.valg("behandling.dodt_fra", [f"{k} {v}" for k, v in sorted(dodt_fra.items())])

    snaps = {k: les(logg, k, kjent_til, alle=k in ("trafikklysvedtak", "eierskap_historikk"))
             for k in ("akvakultur", "eierskap", "eierskap_historikk", "enhetsregisteret",
                       "biomasselag", "lusetall", "sjotemperatur", "trafikklysvedtak",
                       "reguleringsomraader", "unntaksvekst")}

    # ---------------------------------------------------------- grunnlag
    akva = per_uke(bred(snaps["akvakultur"], REGISTERFELT + STEDFELT))
    lus = per_uke(bred(snaps["lusetall"], LUSFELT))
    sjo = per_uke(bred(snaps["sjotemperatur"], SJOFELT))
    eier_t = per_uke(bred(snaps["eierskap"], (
        "eier_orgnr", "eier_navn", "eier_type", "organisasjonsform",
        "lokaliteter", "kapasitet", "kapasitet_enhet", "kapasitet_type")))
    er = per_uke(bred(snaps["enhetsregisteret"], SELSKAPSFELT + ("navn",)))
    unv = per_uke(bred(snaps["unntaksvekst"], (
        "lokalitet_nr", "resultat", "lokalitet_kobling", "saksnummer")))

    akva_uker = sorted(akva["mandag"].unique().to_list())
    lus_uker = sorted(lus["mandag"].unique().to_list())

    # ------------------------------------------------------------ sykdom
    sykdom = les_sykdom(kjent_til)
    if sykdom is not None:
        tilfeller, smeta = sykdom
        logg.fil("sykdom", paths.ARKIV_DIR / SYKDOM_KROPP)
        logg.valg("sykdom.kropp", f"{smeta['fil']} {smeta['sha256']} hentet {smeta['hentet']}")
        logg.valg("sykdom.fra", SYKDOM_FRA)
        syk = sykdom_per_uke(tilfeller, smeta)
    else:
        tilfeller, smeta = [], {}
        logg.valg("sykdom.kropp", "ikke i arkivet, eller ikke hentet før kjent_til")
        syk = sykdom_per_uke([], {"hentedag": SYKDOM_FRA})

    # ------------------------------------------------------- biomasselag
    # Én påstand per (lokalitet, månedsslutt): den siste snapshoten som
    # bar den månedsslutten (R2 P3, «samme periode»). Den står i uka med
    # månedsslutten, og bare der.
    bio = bred(snaps["biomasselag"], ("har_fisk", "arter_tilstede",
                                      "lokalitet_status", "siste_rapport"))
    bio = (bio.filter(pl.col("siste_rapport").is_not_null())
           .sort("dato").group_by("entity_id", "siste_rapport", maintain_order=True).last()
           .filter(pl.col("siste_rapport") >= AKSE_START)
           .with_columns(pl.col("siste_rapport").str.to_date().dt.truncate("1w")
                         .dt.strftime("%Y-%m-%d").alias("mandag"),
                         pl.col("dato").alias("hentet"))
           # To månedsslutter i samme uke kan ikke skje (de er minst 28
           # dager fra hverandre), men om en lokalitet har to, er den
           # nyeste den som gjelder uka.
           .sort("siste_rapport").group_by("entity_id", "mandag", maintain_order=True).last())

    # ---------------------------------------------------------- universet
    ider = set(lus["entity_id"].to_list()) | set(akva["entity_id"].to_list())
    ider |= set(bio["entity_id"].to_list())
    ider |= {t.lokalitet for t in tilfeller}
    ider |= set(unv["lokalitet_nr"].drop_nulls().to_list())
    # Eierskapets lokaliteter bare fra eierkoblingen: et eldre snapshot gir
    # ingen celle, og da er lokaliteten heller ikke en rad.
    for v in (eier_t.filter(pl.col("mandag") >= mandag_av(EIERKOBLING_FRA))
              ["lokaliteter"].drop_nulls().to_list()):
        ider |= {x.strip() for x in v.split(";") if x.strip()}
    lokaliteter = sorted(ider, key=_lokkey)

    siste_uker = [m for m in (lus_uker[-1:] + akva_uker[-1:]) if m]
    siste_uker += sorted(eier_t["mandag"].unique().to_list())[-1:]
    siste_uker += sorted(er["mandag"].unique().to_list())[-1:]
    siste_uker += sorted(unv["mandag"].unique().to_list())[-1:]
    siste_uker += sorted(bio["mandag"].unique().to_list())[-1:]
    if smeta:
        siste_uker.append(mandag_av(smeta["hentedag"]))
    slutt = max(siste_uker)
    uker = mandager(AKSE_START, slutt)
    logg.valg("akse.slutt", slutt)
    logg.valg("akse.uker", len(uker))
    logg.valg("akse.lokaliteter", len(lokaliteter))

    akse = (pl.DataFrame({"lokalitet": lokaliteter})
            .join(pl.DataFrame({"mandag": uker,
                                "uke": [uke_av(m) for m in uker]}), how="cross"))

    deler: list[pl.DataFrame] = []

    # ----------------------------------------------------- register, sted
    deler.append(lag_ramme("register", akva, "akvakultur", pl.col("dato"), REGISTERFELT))
    deler.append(lag_ramme("sted", akva, "akvakultur", pl.col("dato"), STEDFELT))

    # -------------------------------------------------- reguleringsområde
    rsnaps = snaps["reguleringsomraader"]
    if rsnaps:
        rr = rsnaps[-1].ramme
        geo = dict(zip(*rr.filter(pl.col("field") == "geometri")
                       .select("entity_id", "value").to_dict(as_series=False).values()))
        vers = sorted(set(rr.filter(pl.col("field") == "datasett_versjon")["value"].to_list()))
        stat = sorted(set(rr.filter(pl.col("field") == "status")["value"].to_list()))
        polygon = {e: _wkt_punkter(w) for e, w in sorted(geo.items())}
        logg.valg("regomr.datasett", f"{rsnaps[-1].fil} {', '.join(vers)} {', '.join(stat)}")
        rad = []
        for e, m, d, b, l in akva.select("entity_id", "mandag", "dato", "breddegrad",
                                         "lengdegrad").iter_rows():
            if b is None or l is None:
                continue
            inne = [o for o, p in polygon.items()
                    if regomr_kilde.inneholder(p, float(l), float(b))]
            rad.append({"entity_id": e, "mandag": m, "dato": d,
                        "omraade": ";".join(inne) if inne else "utenfor",
                        "datasett": ", ".join(vers), "status": ", ".join(stat)})
        regomr = pl.DataFrame(rad, schema={k: pl.Utf8 for k in (
            "entity_id", "mandag", "dato", "omraade", "datasett", "status")})
        deler.append(lag_ramme("regomr", regomr, "reguleringsomraader+akvakultur",
                               pl.col("dato"), ("omraade", "datasett", "status")))

    # ------------------------------------------------------------ trafikklys
    deler.append(_trafikklys(snaps["trafikklysvedtak"], akva, logg))

    # ---------------------------------------------------- eierskap, selskap
    eier_lok, konflikt_p2, konflikt_p1 = _eierskap(akva, eier_t, er, FORM_KART)
    deler.append(eier_lok)
    sel = eier_lok.select("lokalitet", "mandag", kolonne("eierskap", "selskap_orgnr")).join(
        er.select(pl.col("entity_id").alias(kolonne("eierskap", "selskap_orgnr")), "mandag",
                  "dato", *SELSKAPSFELT),
        on=[kolonne("eierskap", "selskap_orgnr"), "mandag"], how="inner")
    deler.append(sel.select(
        "lokalitet", "mandag",
        pl.lit("enhetsregisteret").alias(kolonne("selskap", "kilde")),
        pl.col("dato").alias(kolonne("selskap", "gjelder")),
        *[pl.col(f).alias(kolonne("selskap", f)) for f in SELSKAPSFELT]))

    # ---------------------------------------------------------- biomasselag
    deler.append(lag_ramme("biomasselag", bio, "biomasselag", pl.col("siste_rapport"),
                           BIOFELT))

    # ---------------------------------------------------------- lus og sjø
    lev = {f: levende_uker(lus, f, maks, dodt_fra.get(f)) for f in LUSFELT
           if f in BEHANDLINGSFLAGG or f == "har_rensefisk"}
    lus_lev = lus.with_columns(*[
        pl.when(pl.col("mandag").is_in(sorted(lev[f]))).then(pl.col(f)).otherwise(None).alias(f)
        for f in lev])
    deler.append(lag_ramme("lus", lus_lev, "lusetall", pl.col("mandag"), LUSFELT))
    deler.append(lag_ramme("sjo", sjo, "sjotemperatur", pl.col("mandag"), SJOFELT))
    b_periode = sorted(set.intersection(*(lev[f] for f in BEHANDLINGSFLAGG)))
    logg.valg("behandling.periode", f"{b_periode[0]} .. {b_periode[-1]} ({len(b_periode)} uker)"
              if b_periode else "(ingen)")

    # -------------------------------------------------------------- sykdom
    reg_uke = (pl.concat([lus.select("entity_id", "mandag"),
                          akva.select("entity_id", "mandag")]).unique()
               .rename({"entity_id": "lokalitet"}))
    sykdom_alle = _sykdom_alle(syk, reg_uke)
    deler.append(sykdom_alle.select(
        "lokalitet", "mandag",
        pl.lit("mattilsynet").alias(kolonne("sykdom", "kilde")),
        pl.coalesce("ila_gjelder", "pd_gjelder").alias(kolonne("sykdom", "gjelder")),
        *[pl.col(f).alias(kolonne("sykdom", f))
          for f in ("ila", "ila_gjelder", "pd", "pd_gjelder", "per_hentedato")]))

    # --------------------------------------------------------- unntaksvekst
    unv_l = (unv.filter(pl.col("lokalitet_nr").is_not_null())
             .group_by("lokalitet_nr", "mandag").agg(
                 pl.col("dato").max(),
                 pl.col("resultat").sort().str.join(";"),
                 pl.col("lokalitet_kobling").sort().str.join(";").alias("kobling"),
                 pl.col("saksnummer").sort().str.join(";")))
    deler.append(lag_ramme("unntaksvekst", unv_l, "unntaksvekst", pl.col("dato"),
                           ("resultat", "kobling", "saksnummer"), nokkel="lokalitet_nr"))

    # --------------------------------------------------------- havbruksfond
    hf = _havbruksfond(kjent_til, logg)
    if hf is not None:
        deler.append(hf)

    # ------------------------------------------------------ sett sammen
    tabell = akse
    for d in deler:
        tabell = tabell.join(d, on=["lokalitet", "mandag"], how="left")

    # ------------------------------------------------------ R8-stripa
    tabell = _stripe(tabell, akva, lus, b_periode, nettsted._over_grensen, lus_uker)

    # ----------------------------------------------------------- P3 og sykdom
    konflikt_p3 = _p3(tabell)
    konflikt_syk = _sykdom_uten_lokalitet(tabell, set(akva_uker), set(lus_uker))
    konflikter = (pl.concat([konflikt_p1, konflikt_p2, konflikt_p3, konflikt_syk])
                  .sort("lokalitet_n", "mandag", "par", "a_verdi", "b_verdi")
                  .drop("lokalitet_n"))
    per_celle = (konflikter.group_by("lokalitet", "mandag")
                 .agg(pl.col("par").unique().sort().str.join(";").alias("konflikt")))
    tabell = tabell.join(per_celle, on=["lokalitet", "mandag"], how="left")

    # ------------------------------------------------------------ ordne
    kolonner = ["lokalitet", "uke", "mandag", "konflikt"]
    for lag in LAG:
        kolonner += [kolonne(lag, "kilde"), kolonne(lag, "gjelder")]
        kolonner += [kolonne(lag, f) for (l_, f) in FELTER if l_ == lag]
    for k in kolonner:
        if k not in tabell.columns:
            tabell = tabell.with_columns(pl.lit(None, dtype=pl.Utf8).alias(k))
    tabell = (tabell.with_columns(pl.col("lokalitet").map_elements(
                  lambda x: _lokkey(x)[1], return_dtype=pl.Int64).alias("_n"))
              .sort("_n", "lokalitet", "mandag").select(kolonner))

    # ----------------------------------------------------------- hendelser
    hendelser = _hendelser(tabell, snaps, akva, eier_t, tilfeller, smeta, logg)

    logg.valg("tabell.rader", tabell.height)
    logg.valg("hendelser", hendelser.height)
    logg.valg("konflikter", konflikter.height)
    return Resultat(tabell, hendelser, konflikter, logg)


def ordlyd_2026() -> str:
    """Setningen i § 4 av FOR-2026-08-20-1764, lest av den arkiverte kroppen.

    Med kildens egne `_tekst()`, `_forskriftstekst()` og `_paragraf()`, og
    bare hvis kroppen er den målingen holdt den mot og setningen står der
    nøyaktig én gang. Ellers kaster den: en ordlyd vi ikke har lest, skal
    ikke stå i en celle med forskriften som kilde.
    """
    from sources import trafikklysvedtak as tlv
    rå = gzip.open(paths.ARKIV_DIR / TRAFIKKLYS_KROPP, "rb").read()
    sha = hashlib.sha256(rå).hexdigest()
    if sha != TRAFIKKLYS_SHA256:
        raise ValueError(f"{TRAFIKKLYS_KROPP} har sha256 {sha}, ikke {TRAFIKKLYS_SHA256}")
    par4 = tlv._paragraf(tlv._forskriftstekst(tlv._tekst(rå)), "4", "5")
    if par4.count(ORDLYD_2026) != 1:
        raise ValueError(f"§ 4 har ikke «{ORDLYD_2026}» nøyaktig én gang")
    return ORDLYD_2026


def _wkt_punkter(wkt: str) -> list[tuple[float, float]]:
    """Ytre ring i en WKT-POLYGON, som `analyse/reguleringsomraader._wkt_punkter`
    leser den: tallpar i rekkefølge."""
    import re
    tall = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", wkt)]
    return list(zip(tall[0::2], tall[1::2]))


def _trafikklys(tsnaps: list[Snap], akva: pl.DataFrame,
                logg: kjoringslogg.Kjoringslogg) -> pl.DataFrame:
    """Vedtaket for lokalitetens PO, for runden som gjelder ved søndagens slutt.

    En runde gjelder fra `published_at` (ikrafttredelsen) og høyst til
    `observed_at`, rundens etikett (`trafikklysvedtak.siste_dag()`). Per PO
    gjelder siste utgitte påstand om runden (`kjoringslogg.ALLE`: en
    revisjon som ikke nevner et felt, har ikke trukket det tilbake). De
    sju 2026-cellene uten farge får forskriftens ordlyd, ikke en farge.
    """
    runder: dict[int, dict] = {}
    for s in tsnaps:
        runde = int(s.dato[:4])
        pub = (snapshot.published_at_i(s.ramme) or "")[:10]
        farger = dict(s.ramme.filter(pl.col("field") == "farge")
                      .select("entity_id", "value").iter_rows())
        lesemaate = dict(s.ramme.filter(pl.col("field") == "farge__lesemaate")
                         .select("entity_id", "value").iter_rows())
        r = runder.setdefault(runde, {"fra": pub, "til": s.dato, "farge": {}})
        r["fra"] = min(r["fra"], pub) if r["fra"] else pub
        for po in farger:
            r["farge"][po] = (farger[po], lesemaate.get(po, ""), pub)
    ordlyd = None
    from sources.trafikklysvedtak import ANTALL_PO
    if 2026 in runder and len(runder[2026]["farge"]) < ANTALL_PO:
        ordlyd = ordlyd_2026()
        logg.fil("trafikklys.2026", paths.ARKIV_DIR / TRAFIKKLYS_KROPP)
        logg.valg("trafikklys.2026.ordlyd", f"{FORSKRIFT_2026}: {ordlyd}")
    rad = []
    for e, m, d, po in akva.select("entity_id", "mandag", "dato",
                                   "prodomraade_kode").iter_rows():
        if not po:
            continue
        sondag = (dt.date.fromisoformat(m) + dt.timedelta(days=6)).isoformat()
        gjeldende = [k for k, r in runder.items() if r["fra"] <= sondag <= r["til"]]
        if not gjeldende:
            continue
        runde = max(gjeldende)
        r = runder[runde]
        if po in r["farge"]:
            farge, lese, pub = r["farge"][po]
            rad.append({"entity_id": e, "mandag": m, "gjelder": pub, "runde": str(runde),
                        "farge": farge, "lesemaate": lese, "kapasitetsjustering": None,
                        "forskrift": None})
        elif runde == 2026:
            rad.append({"entity_id": e, "mandag": m, "gjelder": r["fra"], "runde": "2026",
                        "farge": None, "lesemaate": None,
                        "kapasitetsjustering": ordlyd, "forskrift": FORSKRIFT_2026})
    skjema = {k: pl.Utf8 for k in ("entity_id", "mandag", "gjelder", "runde", "farge",
                                   "lesemaate", "kapasitetsjustering", "forskrift")}
    ramme = pl.DataFrame(rad, schema=skjema)
    return lag_ramme("trafikklys", ramme, "trafikklysvedtak", pl.col("gjelder"),
                     ("runde", "farge", "lesemaate", "kapasitetsjustering", "forskrift"))


def _norm(navn: str | None) -> str:
    return " ".join((navn or "").upper().split())


def _eierskap(akva: pl.DataFrame, eier_t: pl.DataFrame, er: pl.DataFrame,
              form_kart: dict) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Eierleddet per lokalitet og uke, og konfliktene P1 og P2 (R2).

    Bare uker der eierskap har et snapshot, og aldri før EIERKOBLING_FRA.
    Innehaveren står som orgnr. `selskap_orgnr` er den som eier flest av
    tillatelsene på lokaliteten, likhet til høyeste orgnr — regelen i
    `nettsted._lokalitetens_selskap`.

    ## Personformen spørres om her også

    Døra tar rader med personform i `organisasjonsform`. Den kan ikke se en
    tillatelse som bare bærer personformen i `eier_type`, fordi parseren
    som skrev raden ikke kjente typen (CLAUDE.md § 7, F15; R2 F6.1). MÅLT
    11.11.2026 av prøven i tests/test_tidsakse.py: ett partrederi på én
    lokalitet i snapshotene 02.09, 14.09 og 21.09.2026. Det er samme
    spørsmål `nettsted._lokalitetens_selskap` stiller, med samme funksjon
    (`sources.eierskap.er_person`), og av samme grunn: en ny vei til
    eieren uten spørsmålet er en ny lekkasje. Tillatelsen står, eieren står
    ikke, og `personform_utelatt` teller hvor mange tillatelser på
    lokaliteten som har en eier vi ikke fører.
    """
    from sources.eierskap import er_person
    eier_t = eier_t.filter(pl.col("mandag") >= mandag_av(EIERKOBLING_FRA))
    rad, p2, p1 = [], [], []
    akva_per = defaultdict(dict)
    for e, m, t in akva.select("entity_id", "mandag", "tillatelser").iter_rows():
        akva_per[m][e] = {x.strip() for x in (t or "").split(";") if x.strip()}
    er_per = defaultdict(dict)
    for e, m, navn, form in er.select("entity_id", "mandag", "navn",
                                      "organisasjonsform").iter_rows():
        er_per[m][e] = (navn, form)

    for m in sorted(eier_t["mandag"].unique().to_list()):
        uka = eier_t.filter(pl.col("mandag") == m)
        dato = uka["dato"].max()
        per_lok: dict[str, list[tuple[str, str, float | None, bool]]] = defaultdict(list)
        eier_av: dict[str, str] = {}
        personlige: set[str] = set()
        for t, orgnr, lok, kap, enh, typ, etype, form in uka.select(
                "entity_id", "eier_orgnr", "lokaliteter", "kapasitet",
                "kapasitet_enhet", "kapasitet_type", "eier_type",
                "organisasjonsform").iter_rows():
            person = er_person(etype) or er_person(form)
            if person:
                personlige.add(orgnr or "")
            eier_av[t] = "" if person else (orgnr or "")
            tonn = (float(kap) if kap and enh == "TN" and typ == "MTK" else None)
            for l_ in {x.strip() for x in (lok or "").split(";") if x.strip()}:
                per_lok[l_].append((t, eier_av[t], tonn, person))
        for l_, tl in per_lok.items():
            teller = Counter(o for _, o, _, _ in tl if o)
            selskap = max(teller, key=lambda o: (teller[o], o)) if teller else None
            tonn = [x for _, _, x, _ in tl if x is not None]
            rad.append({"lokalitet": l_, "mandag": m, "dato": dato,
                        "tillatelser": ";".join(sorted(t for t, _, _, _ in tl)),
                        "eier_orgnr": ";".join(sorted(teller)) or None,
                        "antall_eiere": str(len(teller)),
                        "selskap_orgnr": selskap,
                        "mtb_tn": _tall(sum(tonn)) if tonn else None,
                        "personform_utelatt": str(sum(1 for *_, p in tl if p))})

        # P2: (lokalitet, tillatelse) på bare den ene siden. Tillatelser som
        # ikke står i eierskap, er tatt av vårt eget persondatafilter og
        # telles ikke (R2 REGLER, P2).
        a = akva_per.get(m)
        if a is not None:
            kjente = set(eier_av)
            ka = {(l_, t) for l_, ts in a.items() for t in ts if t in kjente}
            kb = {(l_, t) for l_, tl in per_lok.items() for t, _, _, _ in tl}
            for l_ in sorted({x for x, _ in (ka - kb) | (kb - ka)}, key=_lokkey):
                bare_a = sorted(t for x, t in ka - kb if x == l_)
                bare_b = sorted(t for x, t in kb - ka if x == l_)
                p2.append(_konflikt("P2", l_, m, "akvakultur",
                                    "bare akvakultur: " + (",".join(bare_a) or "-"),
                                    a_gjelder=m, b_kilde="eierskap",
                                    b_verdi="bare eierskap: " + (",".join(bare_b) or "-"),
                                    b_gjelder=dato))
        # P1: navn eller form ulik hos Enhetsregisteret, samme uke. Navnene
        # sammenlignes her og skrives ikke (MALING-TIDSAKSE F12.2).
        e = er_per.get(m)
        if e is not None:
            uenige: dict[str, str] = {}
            for orgnr, navn, typ in uka.select("eier_orgnr", "eier_navn",
                                               "eier_type").unique().iter_rows():
                if not orgnr or orgnr not in e or orgnr in personlige:
                    continue
                er_navn, er_form = e[orgnr]
                hva = []
                if _norm(navn) != _norm(er_navn):
                    hva.append("navn ulikt")
                form = form_kart.get(str(typ))
                if form and form != er_form:
                    hva.append(f"form {form} mot {er_form}")
                if hva:
                    uenige[orgnr] = "; ".join(hva)
            for l_, tl in per_lok.items():
                for orgnr in sorted({o for _, o, _, _ in tl if o in uenige}):
                    p1.append(_konflikt("P1", l_, m, "eierskap", f"{orgnr}: {uenige[orgnr]}",
                                        a_gjelder=dato, b_kilde="enhetsregisteret",
                                        b_verdi=f"{orgnr}: {uenige[orgnr]}", b_gjelder=m))

    skjema = {k: pl.Utf8 for k in ("lokalitet", "mandag", "dato", "tillatelser",
                                   "eier_orgnr", "antall_eiere", "selskap_orgnr", "mtb_tn",
                                   "personform_utelatt")}
    ramme = pl.DataFrame(rad, schema=skjema)
    felter = ("tillatelser", "eier_orgnr", "antall_eiere", "selskap_orgnr", "mtb_tn",
              "personform_utelatt")
    return (lag_ramme("eierskap", ramme, "eierskap", pl.col("dato"), felter,
                      nokkel="lokalitet"),
            _konfliktramme(p2), _konfliktramme(p1))


def _tall(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".")


KONFLIKTSKJEMA = {k: pl.Utf8 for k in ("par", "lokalitet", "mandag", "uke", "a_kilde",
                                       "a_verdi", "a_gjelder", "b_kilde", "b_verdi",
                                       "b_gjelder", "merknad")}


def _konflikt(par, lok, m, a_kilde, a_verdi, a_gjelder, b_kilde, b_verdi, b_gjelder,
              merknad=""):
    return {"par": par, "lokalitet": lok, "mandag": m, "uke": uke_av(m),
            "a_kilde": a_kilde, "a_verdi": a_verdi, "a_gjelder": a_gjelder,
            "b_kilde": b_kilde, "b_verdi": b_verdi, "b_gjelder": b_gjelder,
            "merknad": merknad}


def _konfliktramme(rader: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rader, schema=KONFLIKTSKJEMA).with_columns(
        pl.col("lokalitet").map_elements(lambda x: _lokkey(x)[1], return_dtype=pl.Int64)
        .alias("lokalitet_n"))


def _sykdom_alle(syk: pl.DataFrame, reg_uke: pl.DataFrame) -> pl.DataFrame:
    """Sakene, og «ingen aktiv sak» for lokaliteter et register har den uka."""
    if syk.is_empty():
        return syk
    uker = sorted(syk["mandag"].unique().to_list())
    hentedato = syk.filter(pl.col("per_hentedato").is_not_null())["per_hentedato"].max()
    uten = (reg_uke.filter(pl.col("mandag").is_in(uker))
            .join(syk.select("lokalitet", "mandag"), on=["lokalitet", "mandag"], how="anti"))
    sondag = (pl.col("mandag").str.to_date() + pl.duration(days=6)).dt.strftime("%Y-%m-%d")
    per_hd = pl.when(sondag >= hentedato).then(pl.lit(hentedato)).otherwise(None)
    dag = pl.when(sondag >= hentedato).then(pl.lit(hentedato)).otherwise(sondag)
    uten = uten.with_columns(
        per_hd.alias("per_hentedato"),
        pl.lit("ingen aktiv sak").alias("ila"), dag.alias("ila_gjelder"),
        pl.lit("ingen aktiv sak").alias("pd"), dag.alias("pd_gjelder"))
    return pl.concat([syk, uten.select(syk.columns)])


def _stripe(tabell: pl.DataFrame, akva: pl.DataFrame, lus: pl.DataFrame,
            b_periode: list[str], over_grensen, lus_uker: list[str]) -> pl.DataFrame:
    """Tilstandene i R8 (havbruk-analyse revisjon/2026-11-09-syklusstripe/,
    FORHANDSREGISTRERING, med tillegg 1 og 2), regnet én gang, her.

    grunn         fisk | brakk | utenfor | ukjent (U1), tom utenfor spennet
    grunn_ukjent  hull | felt_mangler | klarert_ikke_i_kilden |
                  i_registeret_borte_fra_kilden
    lus           over | under | ikke_talt (over gjelder uansett grunn,
                  tillegg 1.1; under og ikke_talt bare i fiskeuker)
    behandling    ja | nei | ukjent, bare i B-perioden
    sykdom        aktiv | ingen | ukjent (uavklart), fra uke 48/2024

    Spennet S(l): fra første uke hos BarentsWatch — eller klareringsuka
    når den er før og etter 2012-01-02 (tillegg 1.3) — til siste uke hos
    BarentsWatch, eller til siste lusetalluke for en lokalitet som står i
    nyeste akvakultursnapshot. Utenfor spennet er stripa tom (U2, U3).
    """
    if not lus_uker:
        return tabell
    siste_lus = lus_uker[-1]
    nyeste = akva.filter(pl.col("dato") == akva["dato"].max()) if not akva.is_empty() else akva
    i_reg = set(nyeste["entity_id"].to_list()) if not nyeste.is_empty() else set()
    klarering = {}
    if not nyeste.is_empty():
        for e, k in nyeste.select("entity_id", "forste_klarering").iter_rows():
            d = oslodag(k)
            if d:
                klarering[e] = mandag_av(d)
    spenn = {}
    for e, fra, til in (lus.group_by("entity_id").agg(pl.col("mandag").min().alias("fra"),
                                                       pl.col("mandag").max().alias("til"))
                        .iter_rows()):
        start = fra
        k = klarering.get(e)
        if k is not None and k < fra:
            start = max(AKSE_START, k)
        slutt = siste_lus if e in i_reg else til
        spenn[e] = (start, fra, til, slutt)
    sp = pl.DataFrame([{"lokalitet": e, "_start": s[0], "_bw_fra": s[1], "_bw_til": s[2],
                        "_slutt": s[3]} for e, s in spenn.items()],
                      schema={k: pl.Utf8 for k in ("lokalitet", "_start", "_bw_fra",
                                                   "_bw_til", "_slutt")})
    t = tabell.join(sp, on="lokalitet", how="left")
    i_spenn = (pl.col("_start").is_not_null() & (pl.col("mandag") >= pl.col("_start"))
               & (pl.col("mandag") <= pl.col("_slutt")))
    har_rad = pl.col("lus__kilde").is_not_null()
    felt_mangler = pl.any_horizontal(*[pl.col(f"lus__{f}").is_null() for f in (
        "brakklagt", "har_laksefisk", "er_landbasert", "er_slaktemerd")])
    univers = ((pl.col("lus__har_laksefisk") == "True")
               & (pl.col("lus__er_landbasert") == "False")
               & (pl.col("lus__er_slaktemerd") == "False"))
    grunn = (pl.when(~i_spenn).then(None)
             .when(~har_rad).then(pl.lit("ukjent"))
             .when(felt_mangler).then(pl.lit("ukjent"))
             .when(~univers).then(pl.lit("utenfor"))
             .when(pl.col("lus__brakklagt") == "True").then(pl.lit("brakk"))
             .when(pl.col("lus__brakklagt") == "False").then(pl.lit("fisk"))
             .otherwise(pl.lit("ukjent")))
    grunn_ukjent = (pl.when(~i_spenn | har_rad & ~felt_mangler).then(None)
                    .when(har_rad & felt_mangler).then(pl.lit("felt_mangler"))
                    .when(pl.col("mandag") < pl.col("_bw_fra")).then(pl.lit("klarert_ikke_i_kilden"))
                    .when(pl.col("mandag") > pl.col("_bw_til"))
                    .then(pl.lit("i_registeret_borte_fra_kilden"))
                    .otherwise(pl.lit("hull")))
    t = t.with_columns(grunn.alias("stripe__grunn"), grunn_ukjent.alias("stripe__grunn_ukjent"))

    # Lus: BarentsWatchs «Over lusegrense uke» lagres ikke; den regnes
    # med BarentsWatchs egen regel (`nettsted._over_grensen`, MÅLT
    # 409 118 av 409 118 mot flagget, KILDE-SJOTEMPERATUR).
    par = t.select("lus__voksne_hunnlus", "sjo__lusegrense").unique().drop_nulls()
    over = pl.DataFrame(
        [{"lus__voksne_hunnlus": a, "sjo__lusegrense": b, "_over": over_grensen(a, b)}
         for a, b in par.iter_rows()],
        schema={"lus__voksne_hunnlus": pl.Utf8, "sjo__lusegrense": pl.Utf8, "_over": pl.Boolean})
    t = t.join(over, on=["lus__voksne_hunnlus", "sjo__lusegrense"], how="left")
    lusstate = (pl.when(~i_spenn).then(None)
                .when(pl.col("_over") == True).then(pl.lit("over"))   # noqa: E712
                .when(pl.col("stripe__grunn") != "fisk").then(None)
                .when((pl.col("_over") == False)                      # noqa: E712
                      & (pl.col("lus__lus_er_rapportert") == "True")
                      & pl.col("lus__voksne_hunnlus").is_not_null()).then(pl.lit("under"))
                .otherwise(pl.lit("ikke_talt")))
    i_b = pl.col("mandag").is_in(b_periode)
    mek, med = pl.col("lus__har_mekanisk_fjerning"), pl.col("lus__har_medikamentell_behandling")
    behandling = (pl.when(~i_spenn | ~i_b).then(None)
                  .when((mek == "True") | (med == "True")).then(pl.lit("ja"))
                  .when((mek == "False") & (med == "False")).then(pl.lit("nei"))
                  .otherwise(pl.lit("ukjent")))
    ila, pd_ = pl.col("sykdom__ila"), pl.col("sykdom__pd")
    syk = (pl.when(~i_spenn | (ila.is_null() & pd_.is_null())).then(None)
           .when(ila.is_in(["mistanke", "påvist"]) | pd_.is_in(["mistanke", "påvist"])
                 | (ila == "uavklart") | (pd_ == "uavklart")).then(pl.lit("aktiv"))
           .when((ila == "ingen aktiv sak") & (pd_ == "ingen aktiv sak")).then(pl.lit("ingen"))
           .otherwise(pl.lit("ukjent")))
    t = t.with_columns(lusstate.alias("stripe__lus"), behandling.alias("stripe__behandling"),
                       syk.alias("stripe__sykdom"))
    t = t.with_columns(
        pl.when(i_spenn).then(pl.lit("lusetall, sjotemperatur, mattilsynet (R8)"))
        .otherwise(None).alias("stripe__kilde"),
        pl.when(i_spenn).then(pl.col("mandag")).otherwise(None).alias("stripe__gjelder"))
    return t.drop("_start", "_bw_fra", "_bw_til", "_slutt", "_over")


def _p3(tabell: pl.DataFrame) -> pl.DataFrame:
    """Biomasselaget mot BarentsWatch i samme uke, med `paastand.konflikt()`
    slik `nettsted.fisk_mot_lus()` bygger påstandene."""
    kand = tabell.filter(pl.col("biomasselag__har_fisk").is_not_null()
                         & pl.col("lus__brakklagt").is_not_null())
    rader = []
    for (lok, m, hf, arter, sr, brakk, laks, land, slakt) in kand.select(
            "lokalitet", "mandag", "biomasselag__har_fisk", "biomasselag__arter_tilstede",
            "biomasselag__gjelder", "lus__brakklagt", "lus__har_laksefisk",
            "lus__er_landbasert", "lus__er_slaktemerd").iter_rows():
        art = frozenset(a.strip() for a in (arter or "").split(";") if a.strip())
        fisk = paastand.Paastand("fisk", "biomasselag", sr, hf, felt="har_fisk",
                                 arter=(art or None) if hf == "Ja" else None)
        univers = laks == "True" and land == "False" and slakt == "False"
        b = paastand.Paastand("brakklagt", "lusetall", m, brakk, nivaa=paastand.VURDERT,
                              felt="brakklagt", periode=paastand.UKE,
                              arter=paastand.LAKSEFISK if univers else frozenset())
        if paastand.konflikt(fisk, b):
            retning = "fisk/brakk" if hf == "Ja" else "tom/drift"
            rader.append(_konflikt("P3", lok, m, "biomasselag",
                                   f"har_fisk {hf}" + (f" ({';'.join(sorted(art))})" if art else ""),
                                   sr, "lusetall", f"brakklagt {brakk}", m, retning))
    return _konfliktramme(rader)


def _sykdom_uten_lokalitet(tabell: pl.DataFrame, akva_uker: set[str],
                           lus_uker: set[str]) -> pl.DataFrame:
    """En åpen sak hos Mattilsynet på en lokalitet som ingen av registrene
    har den uka, i en uke der minst ett av dem har et snapshot.

    Det er de fire PD-lokalitetene (MALING-TIDSAKSE F9.2), og beslutningen
    er at de står som konflikt, ikke faller ut som «ikke koblet» (R5 T2).
    """
    kand = tabell.filter((pl.col("sykdom__ila").is_in(AKTIV) | pl.col("sykdom__pd").is_in(AKTIV))
                         & pl.col("register__kilde").is_null() & pl.col("lus__kilde").is_null()
                         & (pl.col("mandag").is_in(sorted(akva_uker | lus_uker))))
    rader = []
    for lok, m, ila, ilag, pd_, pdg in kand.select(
            "lokalitet", "mandag", "sykdom__ila", "sykdom__ila_gjelder", "sykdom__pd",
            "sykdom__pd_gjelder").iter_rows():
        for navn, st, g in (("ILA", ila, ilag), ("PD", pd_, pdg)):
            if st in AKTIV:
                hvem = [k for k, u in (("akvakultur", akva_uker), ("lusetall", lus_uker))
                        if m in u]
                rader.append(_konflikt("sykdom", lok, m, "mattilsynet", f"{navn} {st}", g,
                                       "+".join(hvem), "lokaliteten finnes ikke", m))
    return _konfliktramme(rader)


def _havbruksfond(kjent_til: str | None, logg) -> pl.DataFrame | None:
    """Nøkkelen per lokalitet ved måledatoen, fra `havbruksfond.fordeling()`
    — den ene veien til tallene. Én uke: den med 01.09.2026."""
    import havbruksfond as h
    try:
        f = h.fordeling()
    except FileNotFoundError:
        logg.valg("havbruksfond", "grunnlaget mangler")
        return None
    # Nøkkelen kunne tidligst regnes dagen ETTER at siste kropp den hviler
    # på var hentet (regnearket for 2025 er fra 12.10.2026). Før det fantes
    # den ikke, og en tidsakse «kjent til» da skal ikke ha den.
    grunnlag = max((k.hentet or k.dato)[:10] for k in f["kropper"])
    if kjent_til and kjent_til[:10] <= grunnlag:
        logg.valg("havbruksfond", f"ikke kjent før etter {grunnlag}")
        return None
    med: dict[str, list] = defaultdict(list)
    ute: set[str] = set()
    for komnr, k in f["kommuner"].items():
        for p in k["lokaliteter"]:
            med[p.nr].append((komnr, p.tonn))
        ute |= set(k["ute"])
    m = mandag_av(h.MAALEDATO)
    rad = []
    for nr in sorted(set(med) | ute, key=_lokkey):
        if nr in med:
            rad.append({"lokalitet": nr, "mandag": m, "nokkel": "med",
                        "tonn": _tall(sum(t for _, t in med[nr])),
                        "kommuner": ";".join(sorted(k for k, _ in med[nr]))})
        else:
            rad.append({"lokalitet": nr, "mandag": m, "nokkel": "ute",
                        "tonn": None, "kommuner": None})
    logg.valg("havbruksfond", f"måledato {h.MAALEDATO}, med {len(med)}, ute {len(ute)}")
    ramme = pl.DataFrame(rad, schema={k: pl.Utf8 for k in (
        "lokalitet", "mandag", "nokkel", "tonn", "kommuner")})
    return lag_ramme("havbruksfond", ramme, "havbruksfond", pl.lit(h.MAALEDATO),
                     ("nokkel", "tonn", "kommuner"), nokkel="lokalitet")


# ---------------------------------------------------------------- hendelser

HENDELSESKJEMA = {k: pl.Utf8 for k in (
    "r9", "type", "lokalitet", "tillatelse", "uke", "mandag", "mellom", "gjelder",
    "kilde", "felt", "fra", "til", "forste_fil", "forste_hentet", "stempel_manifest",
    "stempel_status", "forste_omtale")}


def _hendelser(tabell: pl.DataFrame, snaps: dict[str, list[Snap]], akva: pl.DataFrame,
               eier_t: pl.DataFrame, tilfeller: list[Tilfelle], smeta: dict,
               logg: kjoringslogg.Kjoringslogg) -> pl.DataFrame:
    """H1–H9 fra R9, hver med første fil, hentetid og stempel."""
    stemple = Stempler()
    rader: list[dict] = []

    def legg(r9, typ, lok, m, gjelder, kilde, felt, fra, til, fil, hentet,
             tillatelse="", mellom=""):
        sti, fil_rel = fil
        manifest, status = stemple(sti, _manifeststi(fil_rel))
        rader.append({"r9": r9, "type": typ, "lokalitet": lok, "tillatelse": tillatelse,
                      "uke": uke_av(m) if m else "", "mandag": m or "", "mellom": mellom,
                      "gjelder": gjelder or "", "kilde": kilde, "felt": felt,
                      "fra": fra or "", "til": til or "", "forste_fil": fil_rel,
                      "forste_hentet": hentet, "stempel_manifest": manifest,
                      "stempel_status": status, "forste_omtale": UBELAGT})

    # H1: mistanke og påvist, Mattilsynets datoer, fra uke 48/2024.
    if smeta:
        for t in tilfeller:
            for stadium, dag in (("mistanke", t.mistanke), ("påvist", t.diagnose)):
                if dag and dag >= SYKDOM_FRA and dag <= smeta["hentedag"]:
                    legg("H1", "sykdom", t.lokalitet, mandag_av(dag), dag, "mattilsynet",
                         t.sykdom, "", stadium,
                         (paths.ARKIV_DIR / SYKDOM_KROPP, f"arkiv/{SYKDOM_KROPP}"),
                         smeta["hentet"])

    # H2–H5: BarentsWatch, uke u mot u−1, fra tabellen. Fravær er ikke en
    # verdi: en lokalitet som mangler i u−1, gir ingen brakklegging.
    lus_fil = {mandag_av(s.dato): (s.fil, s.hentet) for s in snaps["lusetall"]}
    b = (tabell.select("lokalitet", "mandag", "lus__brakklagt", "lus__har_mekanisk_fjerning",
                       "stripe__lus", "lus__kilde")
         .with_columns(pl.col("lus__brakklagt").shift(1).over("lokalitet").alias("_b1"),
                       pl.col("lus__har_mekanisk_fjerning").shift(1).over("lokalitet")
                       .alias("_m1"),
                       pl.col("stripe__lus").shift(1).over("lokalitet").alias("_l1"),
                       pl.col("mandag").shift(1).over("lokalitet").alias("_forrige"))
         .filter(pl.col("lus__kilde").is_not_null()))
    for lok, m, brakk, mek, lusst, _k, b1, m1, l1, forrige in b.iter_rows():
        fil, hentet = lus_fil.get(m, ("", ""))
        rel = (snapshot.RAW_DIR / "lusetall" / fil, f"raw/lusetall/{fil}")
        if lusst == "over" and l1 != "over":
            legg("H2", "over_lusegrensa", lok, m, m, "lusetall+sjotemperatur", "lus",
                 l1 or "", "over", rel, hentet)
        if b1 == "False" and brakk == "True":
            legg("H3", "brakklagt", lok, m, m, "lusetall", "brakklagt", b1, brakk, rel, hentet)
        if b1 == "True" and brakk == "False":
            legg("H4", "brakklegging_slutt", lok, m, m, "lusetall", "brakklagt", b1, brakk,
                 rel, hentet)
        # Mekanisk lever i hele serien (MALING-TIDSAKSE F8.2); flagget er
        # tomt i en død uke, og da blir det ingen hendelse.
        if m1 == "False" and mek == "True":
            legg("H5", "mekanisk_lusefjerning", lok, m, m, "lusetall",
                 "har_mekanisk_fjerning", m1, mek, rel, hentet)

    # H6–H8: registeret mellom to påfølgende snapshots.
    asn = snaps["akvakultur"]
    for forrige, neste in zip(asn, asn[1:]):
        a = akva.filter(pl.col("dato") == forrige.dato)
        n = akva.filter(pl.col("dato") == neste.dato)
        av = {r["entity_id"]: r for r in a.iter_rows(named=True)}
        nv = {r["entity_id"]: r for r in n.iter_rows(named=True)}
        m, mellom = _intervall(forrige.dato, neste.dato)
        rel = (snapshot.RAW_DIR / "akvakultur" / neste.fil, f"raw/akvakultur/{neste.fil}")
        for e in sorted(set(nv) - set(av), key=_lokkey):
            legg("H6", "ny_lokalitet", e, m, oslodag(nv[e]["forste_klarering"]) or "",
                 "akvakultur", "lokalitet", "", "ny", rel, neste.hentet, mellom=mellom)
        for e in sorted(set(av) - set(nv), key=_lokkey):
            legg("H7", "lokalitet_ut_eller_status", e, m, "", "akvakultur", "lokalitet",
                 "i registeret", "ut", rel, neste.hentet, mellom=mellom)
        for e in sorted(set(av) & set(nv), key=_lokkey):
            for felt in ("versjon_status", "klareringstype", "har_kommersiell_aktivitet"):
                if av[e][felt] != nv[e][felt]:
                    legg("H7", "lokalitet_ut_eller_status", e, m,
                         oslodag(nv[e]["versjon_gyldig_fra"]) or "", "akvakultur", felt,
                         av[e][felt], nv[e][felt], rel, neste.hentet, mellom=mellom)
            for felt in ("kapasitet", "kapasitet_midlertidig"):
                if _tallverdi(av[e][felt]) != _tallverdi(nv[e][felt]):
                    legg("H8", "kapasitet_endret", e, m,
                         oslodag(nv[e]["versjon_gyldig_fra"]) or "", "akvakultur", felt,
                         av[e][felt], nv[e][felt], rel, neste.hentet, mellom=mellom)

    # H9: eier_orgnr på en tillatelse ulik mellom to påfølgende snapshots.
    overf = defaultdict(list)
    for s in snaps["eierskap_historikk"]:
        r = bred([s], ("tillatelse_nr", "mottaker_orgnr", "journal_dato"))
        for t, o, d in r.select("tillatelse_nr", "mottaker_orgnr", "journal_dato").iter_rows():
            if t and o and d:
                overf[(t, o)].append(d)
    from sources.eierskap import er_person
    utelatt_h9 = 0
    esn = [s for s in snaps["eierskap"] if s.dato >= EIERKOBLING_FRA]
    for forrige, neste in zip(esn, esn[1:]):
        a = eier_t.filter(pl.col("dato") == forrige.dato)
        n = eier_t.filter(pl.col("dato") == neste.dato)
        av = {r["entity_id"]: r for r in a.iter_rows(named=True)}
        nv = {r["entity_id"]: r for r in n.iter_rows(named=True)}
        m, mellom = _intervall(forrige.dato, neste.dato)
        rel = (snapshot.RAW_DIR / "eierskap" / neste.fil, f"raw/eierskap/{neste.fil}")
        for t in sorted(set(av) & set(nv)):
            fra, til = av[t]["eier_orgnr"], nv[t]["eier_orgnr"]
            if fra == til:
                continue
            if any(er_person(r[f]) for r in (av[t], nv[t])
                   for f in ("eier_type", "organisasjonsform")):
                utelatt_h9 += 1
                continue
            datoer = sorted(d for d in overf.get((t, til or ""), []) if d <= neste.dato)
            lok = sorted({x.strip() for x in (nv[t]["lokaliteter"] or "").split(";")
                          if x.strip()}, key=_lokkey) or [""]
            for l_ in lok:
                legg("H9", "eierskifte", l_, m, datoer[-1] if datoer else "", "eierskap",
                     "eier_orgnr", fra, til, rel, neste.hentet, tillatelse=t, mellom=mellom)

    logg.valg("hendelser.H9.utelatt_regel3", utelatt_h9)
    ramme = pl.DataFrame(rader, schema=HENDELSESKJEMA)
    return (ramme.with_columns(pl.col("lokalitet").map_elements(
                lambda x: _lokkey(x)[1] if x else -1, return_dtype=pl.Int64).alias("_n"))
            .sort("mandag", "mellom", "r9", "_n", "lokalitet", "tillatelse", "felt", "til",
                  "gjelder")
            .drop("_n"))


def _intervall(fra: str, til: str) -> tuple[str, str]:
    """(mandagen for uka endringen skjedde i, «fra/til»).

    To snapshots med én uke mellom: endringen skjedde i uka det første
    gjelder (R9 A2). Lengre mellom (eierskap mangler uke 37): uka er
    ukjent, og bare intervallet står. Ingen gjetning.
    """
    if (dt.date.fromisoformat(til) - dt.date.fromisoformat(fra)).days <= 7:
        return mandag_av(fra), f"{fra}/{til}"
    return "", f"{fra}/{til}"


def _tallverdi(x: str | None) -> float | None:
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


# --------------------------------------------------------------- påstand


def paastand_for(rad: dict, lag: str, felt: str) -> paastand.Paastand | None:
    """En celle som `paastand.Paastand`, med nivå og periode fra `FELTER`.

    None når cellen er tom: en tom uke er ingen påstand.
    """
    verdi = rad.get(kolonne(lag, felt))
    if verdi is None:
        return None
    nivaa, periode = FELTER[(lag, felt)]
    return paastand.Paastand(tema=felt, kilde=rad[kolonne(lag, "kilde")],
                             gjelder=rad[kolonne(lag, "gjelder")], verdi=verdi,
                             nivaa=nivaa, felt=felt, periode=periode)


# ---------------------------------------------------------------- skriving


def skriv(res: Resultat, ut: Path) -> dict[str, str]:
    """De tre filene, og sha256 over hver. Samme inndata gir samme bytes."""
    ut.mkdir(parents=True, exist_ok=True)
    summer = {}
    for navn, ramme in ((TABELL, res.tabell), (HENDELSER, res.hendelser),
                        (KONFLIKTER, res.konflikter)):
        sti = ut / navn
        ramme.write_parquet(sti, compression="zstd", compression_level=9,
                            statistics=True, row_group_size=262144)
        summer[navn] = hashlib.sha256(sti.read_bytes()).hexdigest()
        res.logg.valg(f"ut.{navn}", summer[navn])
    res.logg.sti = ut / LOGGNAVN
    res.logg.skriv()
    return summer


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ut", type=Path, default=UT_DIR)
    p.add_argument("--kjent-til", default=None,
                   help="bare snapshots hentet senest dette tidspunktet (ISO, UTC)")
    a = p.parse_args()
    res = bygg(kjent_til=a.kjent_til)
    summer = skriv(res, a.ut)
    print(f"tidsakse: {res.tabell.height} rader, {res.hendelser.height} hendelser, "
          f"{res.konflikter.height} konflikter -> {a.ut}")
    for navn, s in summer.items():
        print(f"  {navn} {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
