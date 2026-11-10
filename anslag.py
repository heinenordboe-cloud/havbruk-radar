"""Maskinanslagene: ukas anslag per produksjonsområde, forseglet.

    python anslag.py                  # ukas anslag til predictions/maskin/<år>-<uke>.yml
    python anslag.py --forsegl        # ... og stemple fila med OpenTimestamps
    python anslag.py --torrkjor       # skriv fila til stdout, ikke til disk
    python anslag.py --uke 2026-W46 --torrkjor
                                      # en tidligere uke, bare til stdout

Hva som anslås, og hvorfor bare K2 og K6, står i
`predictions/maskin/FORHANDSREGISTRERING.md`, stemplet og committet før
første anslag (d469d8c). K6 er en PRØVETYPE, og fila sier det ved hvert
anslag. Utfallet og trefflista skriver `skaar_anslag.py`.

## R6s modell, importert og ikke kopiert

Modellen er skriptet fra backtesten R6, lagt inn uendret som
`analyse/anslag/anslag_backtest.py`. `R6_SHA256` er summen av fila som
laget backtesten, og `modulen()` nekter å regne hvis fila er en annen.
Denne fila regner ikke ut noe av modellen selv: den leser panelene,
kaller R6s `k_hasard()` og `k_sesong()` med siste uke satt slik at uke T
kommer med, og tar ut radene for T. Det er de samme funksjonene, med de
samme konstantene, som ga tallene i backtesten.

Lesingen er det eneste som er skrevet her, og den skiller seg fra R6s
`les_alt()` på to punkter:

  * Den leser til og med uke T−4 og ikke lenger. `les_alt()` leser alt
    som finnes, og årene står fast i koden (2012–2026). I 2027 ville den
    stille ha mistet årets uker, og K2 ville anslått null overalt.
  * PO-koblingen er siste akvakultur-snapshot til og med
    utstedelsesmandagen, ikke siste som finnes. Samme uke regnet ut på
    nytt senere skal gi det samme anslaget.

Versjonsvalget, feltene og sammenslåingen er R6s, med R6s egne hjelpere
(`_slaa_sammen`, `_bred`).

## Fila røres aldri etter stempelet

`--forsegl` kjører `ots stamp` på ukefila og fører tidspunktet i
`forseglinger.tsv`. Finnes ukefila fra før, lages den ikke på nytt: den
stemples hvis den ikke er stemplet, ellers skjer ingenting. Fristen er
søndag i uke T (FORHANDSREGISTRERING.md, «Frist»), og etter den nekter
kommandoen både å lage og å stemple.

## Bare pushet kode lager et anslag

Før ukefila skrives, kreves det samme som før innsamlingen
(`kodeproveniens.krev_sporbar()`): rent arbeidstre og HEAD på
origin/main. `kode` i ukefila er da en commit alle kan hente, og som
gir det samme anslaget av de samme dataene.

## Klokka

`main()` slår opp tiden én gang (CLAUDE.md 1b) og sender den videre. Uka
anslaget gjelder, fristen og tidspunktet i forseglinger.tsv regnes av
den. Kjøringen starter sekunder før stempelet lages; tidspunktet er
kjøringens, og blokken i det oppgraderte stempelet er beviset.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
from pathlib import Path

import polars as pl
import yaml

import havbruksfond
import stempel
from analyse import kjoringslogg as kl
from analyse.anslag import anslag_backtest as r6
from core import kodeproveniens, paths, snapshot
from core.config import get

MASKIN_DIR = paths.ROT / "predictions" / "maskin"
FORSEGLINGER = MASKIN_DIR / "forseglinger.tsv"
FORSEGLINGER_HODE = "uke\tfil\tsha256\tstemplet\tots_sha256\n"
UKEFIL = re.compile(r"^(\d{4})-(\d{2})\.yml$")

# Summen av R6s skript slik det laget backtesten (havbruk-analyse 7d258f7,
# revisjon/2026-11-09-anslag-backtest/anslag_backtest.py). Står også i
# FORHANDSREGISTRERING.md. Endres fila, er modellen ikke den registrerte.
R6_STI = paths.ROT / "analyse" / "anslag" / "anslag_backtest.py"
R6_SHA256 = "0b8f7eec13499506604fb628a3a0850d07deed6283ea2d17f99eb633e221d2d7"

# Informasjonen ved utstedelse: til og med uke T−4. Registrert, ikke
# lest av config.yml: modellen er backtestet med akkurat dette etterslepet,
# også om innsamlingen en dag henter fortere.
INFO_UKER = 4
FORSTE = "2012-01-01"
# Feltene R6s `les_alt()` leser, i samme rekkefølge.
LUSEFELT = ["voksne_hunnlus", "lus_er_rapportert", "brakklagt", "har_pd"]
SJOFELT = ["lusegrense", "sjotemperatur", "temperatur_er_rapportert"]

DESIMALER = 4

TYPER = {
    "K2": {
        "klasse": "hovedtype",
        "kilde": "lusetall",
        "felt": "brakklagt",
        "grunnlag": (
            "Hasarden for brakklegging fire til sju uker fram stiger med hvor "
            "lenge lokaliteten har vært aktiv, fra 1,4 % etter 1–26 uker til "
            "30 % etter 79–91 uker (trening 2017–2022). Anslaget er summen av "
            "hasarden over lokalitetene som var aktive i uke T−4. Ingen av de "
            "naive referansene vet hvor langt i produksjonsløpet lokalitetene er."),
        "feil_hvis": (
            "MAE for modellen over de forseglede ukene er ikke lavere enn MAE "
            "for siste verdi og for samme periode i fjor."),
    },
    "K6": {
        "klasse": "PRØVETYPE",
        "kilde": "lusetall",
        "felt": "voksne_hunnlus",
        "grunnlag": (
            "Lusenivået i et produksjonsområde følger årstiden. Anslaget er "
            "snittet i uke T−4 pluss den vanlige endringen fra den ISO-uka "
            "til måluka i 2017–2022, for samme PO."),
        "feil_hvis": (
            "MAE for modellen over de forseglede ukene er ikke lavere enn MAE "
            "for siste verdi og for samme uke i fjor."),
    },
}


# ------------------------------------------------------------------ uker

def mandag(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())


def isouke(d: dt.date) -> str:
    aar, uke, _ = d.isocalendar()
    return f"{aar}-W{uke:02d}"


def fra_isouke(tekst: str) -> dt.date:
    m = re.fullmatch(r"(\d{4})-W(\d{2})", tekst.strip())
    if not m:
        raise ValueError(f"uke må skrives ÅÅÅÅ-Wnn, ikke {tekst!r}")
    return dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)


def filnavn(T: dt.date) -> str:
    aar, uke, _ = T.isocalendar()
    return f"{aar}-{uke:02d}.yml"


def uke_fra_filnavn(navn: str) -> dt.date | None:
    m = UKEFIL.match(navn)
    return dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1) if m else None


def frist(T: dt.date) -> dt.datetime:
    """Søndag i uke T, 24:00 UTC."""
    return dt.datetime.combine(T + dt.timedelta(days=7), dt.time(), dt.timezone.utc)


def vindu(type_: str, T: dt.date) -> tuple[dt.date, dt.date]:
    """Målukene: K2 uke T … T+3, K6 uke T+4."""
    if type_ == "K2":
        return T, T + dt.timedelta(days=27)
    return T + dt.timedelta(weeks=4), T + dt.timedelta(weeks=4, days=6)


def aapningsdato(type_: str, T: dt.date) -> dt.date:
    """Mandagen da siste måluke etter planen står i våre snapshots."""
    etterslep = int(get("kilder.lusetall.uker_etterslep", 4))
    siste = vindu(type_, T)[1]
    return mandag(siste) + dt.timedelta(weeks=etterslep)


def sha256(sti: Path) -> str:
    return hashlib.sha256(sti.read_bytes()).hexdigest()


def vis(sti: Path) -> str:
    """Stien slik repoet og fasiten.json oppgir den."""
    return f"predictions/maskin/{sti.name}"


# ------------------------------------------------------------------ R6

def modulen():
    """R6s modul, men bare hvis den er fila backtesten ble laget med."""
    naa = sha256(R6_STI)
    if naa != R6_SHA256:
        raise SystemExit(
            f"STOPP: {R6_STI.relative_to(paths.ROT)} har sha256 {naa}, ikke "
            f"{R6_SHA256}. Modellen er ikke den som er registrert og backtestet.")
    return r6


# ---------------------------------------------------------------- lesing

def akvakultur_dato(T: dt.date) -> str:
    """Siste akvakultur-snapshot til og med utstedelsesmandagen."""
    datoer = [d for d in snapshot.datoer("akvakultur") if d <= T.isoformat()]
    if not datoer:
        raise SystemExit(f"STOPP: ingen akvakultur-snapshot til og med {T}.")
    return datoer[-1]


def les_panel(logg: kl.Kjoringslogg, fra: str, til: str, akv_dato: str) -> dict:
    """R6s panel for `lusetall` og `sjotemperatur` i [fra, til], og
    PO-koblingen fra `akvakultur` `akv_dato`. Samme versjonsvalg, felt og
    sammenslåing som `les_alt()`, ett kall per kilde og år."""
    lus, sjo = [], []
    for aar in range(int(fra[:4]), int(til[:4]) + 1):
        start, slutt = max(f"{aar}-01-01", fra), min(f"{aar}-12-31", til)
        lus.append(r6._slaa_sammen(
            logg.les("lusetall", start, slutt, versjonsvalg=kl.GJELDENDE), LUSEFELT))
        sjo.append(r6._slaa_sammen(
            logg.les("sjotemperatur", start, slutt, versjonsvalg=kl.ALLE), SJOFELT))
    akv = logg.les("akvakultur", akv_dato, akv_dato, versjonsvalg=kl.GJELDENDE)
    kobling = (akv[-1][1].filter(pl.col("field") == "prodomraade_kode")
               .select(["entity_id", "value"]).iter_rows())
    return {"lus": r6._bred(pl.concat(lus)), "sjo": r6._bred(pl.concat(sjo)),
            "lok_po": {str(k): str(v).strip() for k, v in kobling}}


def inndata_sha256(logg: kl.Kjoringslogg) -> str:
    """Én sum over filene som ble lest: sha256 over linjene
    «kilde observed_at versjon sha256(fil)», sortert. Den som har
    datarepoet, kan regne den ut på nytt og se at inndataene er de samme."""
    linjer = []
    for l in logg._lesinger:
        navn = f"{l.observed_at}.parquet" if l.versjon == 1 else f"{l.observed_at}.{l.versjon}.parquet"
        linjer.append(f"{l.kilde} {l.observed_at} {l.versjon} "
                      f"{sha256(snapshot.RAW_DIR / l.kilde / navn)}")
    return hashlib.sha256("\n".join(sorted(linjer)).encode("utf-8")).hexdigest()


# -------------------------------------------------------------- regningen

def regn_ut(data: dict, T: dt.date) -> dict[str, dict[str, dict]]:
    """{type: {po: rad}} for uke T, regnet ut av R6s funksjoner.

    `k_hasard()` gir rader for utstedelsene til og med siste_wi − 3, og
    `k_sesong()` for mål til og med siste_wi. Siste_wi settes derfor til
    T+3 og T+4, så uke T kommer med. Utfallet (`y`) i de radene er ikke
    kjent og brukes ikke: K2 teller null hendelser i uker som ikke finnes,
    og K6 har None."""
    m6 = modulen()
    t = m6.wi(T)
    p = m6.lokalitetspanel(data)
    serie = m6.po_ukeserie(p)
    k2, _ = m6.k_hasard(p, t + 3)
    k6, _ = m6.k_sesong(serie, "K6", t + 4, 8, (0.0, None))

    K = t - INFO_UKER
    aktive = dict(p.filter((pl.col("wi") == K) & pl.col("po").is_in(m6.PO_ER)
                           & (pl.col("brakklagt") == "False"))
                  .group_by("po").len().iter_rows())
    n_lus = {po: n for po, w, n in serie.select(["po", "wi", "n_lus"]).iter_rows()
             if w == K and n is not None}

    ut: dict[str, dict[str, dict]] = {"K2": {}, "K6": {}}
    for type_, rader, n in (("K2", k2, aktive), ("K6", k6, n_lus)):
        for r in rader:
            if r["i"] == t:
                ut[type_][r["po"]] = {"m": r["m"], "a": r["a"], "b": r["b"],
                                      "lokaliteter": int(n.get(r["po"], 0))}
    return ut


def _tall(x):
    if x is None:
        return None
    if isinstance(x, float):
        return round(x, DESIMALER)
    return int(x)


def _merknad(type_: str, rad: dict) -> str:
    mangler = [navn for navn, k in (("anslaget", "m"), ("referanse a", "a"),
                                     ("referanse b", "b")) if rad[k] is None]
    if not mangler:
        return ""
    grunn = (" (færre enn 5 lokaliteter med lusetall og lusegrense i uka, "
             "eller ingen sesongverdi)") if type_ == "K6" else ""
    return f"skåres ikke: {', '.join(mangler)} mangler{grunn}"


# ---------------------------------------------------------------- fila

def ukefil(T: dt.date, res: dict, *, akv_dato: str, kode: str, data: str,
           inndata: str) -> str:
    """Ukefila som tekst. Feltene følger MAL.yaml der de passer."""
    K = T - dt.timedelta(weeks=INFO_UKER)
    u = isouke
    beskrivelse = {
        "K2": {
            "anslag": f"antall brakklegginger i PO-en i uke {u(T)} … {u(T + dt.timedelta(weeks=3))}",
            "referanse_a": f"siste verdi: antall i uke {u(T - dt.timedelta(weeks=7))} … {u(K)}",
            "referanse_b": (f"samme periode i fjor: antall i uke "
                            f"{u(T - dt.timedelta(weeks=52))} … {u(T - dt.timedelta(weeks=49))}"),
        },
        "K6": {
            "anslag": f"snitt voksne hunnlus i PO-en i uke {u(T + dt.timedelta(weeks=4))}",
            "referanse_a": f"siste verdi: snitt i uke {u(K)}",
            "referanse_b": f"samme uke i fjor: snitt i uke {u(T - dt.timedelta(weeks=48))}",
        },
    }
    typer = {}
    for type_, meta in TYPER.items():
        fra, til = vindu(type_, T)
        typer[type_] = {
            "klasse": meta["klasse"],
            **beskrivelse[type_],
            "vindu": {"fra": fra.isoformat(), "til": til.isoformat()},
            "aapningsdato": aapningsdato(type_, T).isoformat(),
            "grunnlag": meta["grunnlag"],
            "feil_hvis": meta["feil_hvis"],
        }
    aar, uke, _ = T.isocalendar()
    prediksjoner = []
    for type_, meta in TYPER.items():
        for po in r6.PO_ER:
            rad = res[type_].get(po, {"m": None, "a": None, "b": None, "lokaliteter": 0})
            p = {"id": f"{aar}-{uke:02d}-{type_}-PO{po}", "type": type_,
                 "klasse": meta["klasse"], "entitet": f"PO{po}",
                 "kilde": meta["kilde"], "felt": meta["felt"],
                 "anslag": _tall(rad["m"]), "referanse_a": _tall(rad["a"]),
                 "referanse_b": _tall(rad["b"]), "lokaliteter": rad["lokaliteter"]}
            if merknad := _merknad(type_, rad):
                p["merknad"] = merknad
            prediksjoner.append(p)
    innhold = {
        "uke": isouke(T),
        "utstedt": T.isoformat(),
        "informasjon_til": K.isoformat(),
        "po_kobling": f"akvakultur {akv_dato}",
        "kode": kode,
        "data": data,
        "inndata_sha256": inndata,
        "modell": f"{R6_STI.relative_to(paths.ROT).as_posix()} sha256 {R6_SHA256}",
        "typer": typer,
        "prediksjoner": prediksjoner,
    }
    hode = (
        f"# MASKINANSLAG FOR UKE {isouke(T)}. K6 ER EN PRØVETYPE.\n"
        "#\n"
        f"# Forseglet: {filnavn(T)}.ots stempler sha256 av denne fila. Fila\n"
        "# røres aldri etter stempelet, og utfallet skrives aldri her. Det står\n"
        "# i fasiten.json, og den løpende trefflista i treffliste.md.\n"
        "#\n"
        "# Registrert i FORHANDSREGISTRERING.md før første anslag. Laget av\n"
        "# anslag.py med R6s modell uendret. Bare PO-nivå.\n"
        "#\n"
        "# Feltene følger MAL.yaml der de passer: id, type, entitet, kilde,\n"
        "# felt, vindu, grunnlag og feil_hvis. konfidens og utfall er ikke med.\n"
        "# Et punktanslag har ingen sannsynlighet å kalibrere, og utfallet kan\n"
        "# ikke skrives i en fil som er stemplet.\n"
        "\n")
    return hode + yaml.safe_dump(innhold, allow_unicode=True, sort_keys=False,
                                 default_flow_style=False, width=78)


# ------------------------------------------------------------- forsegling

def forsegl(sti: Path, T: dt.date, naa: dt.datetime) -> int:
    """`ots stamp` på ukefila, og en linje i forseglinger.tsv."""
    ots = Path(f"{sti}.ots")
    sha = sha256(sti)
    if ots.exists():
        stemplet = havbruksfond.ots_sum(ots.read_bytes(), ots.name)
        if stemplet != sha:
            print(f"::error::{ots.name} er stemplet for {stemplet}, ikke for fila ({sha}).")
            return 2
        print(f"  {sti.name} er allerede forseglet")
        return 0
    if naa >= frist(T):
        print(f"::error::Fristen for {isouke(T)} gikk ut {frist(T).isoformat()}. "
              f"Uka er tapt og stemples ikke (FORHANDSREGISTRERING.md, «Frist»).")
        return 2
    r = stempel.ots("stamp", str(sti))
    if r.returncode != 0 or not ots.exists():
        print(f"::error::ots stamp {sti.name} feilet (exit {r.returncode}): "
              f"{(r.stderr or r.stdout).strip()[-400:]}")
        return 1
    stemplet = havbruksfond.ots_sum(ots.read_bytes(), ots.name)
    if stemplet != sha:
        print(f"::error::{ots.name} er stemplet for {stemplet}, ikke for fila ({sha}).")
        return 2
    ny = not FORSEGLINGER.exists()
    with FORSEGLINGER.open("a", encoding="utf-8") as fh:
        if ny:
            fh.write(FORSEGLINGER_HODE)
        fh.write(f"{isouke(T)}\t{sti.name}\t{sha}\t"
                 f"{naa.strftime('%Y-%m-%dT%H:%M:%SZ')}\t{sha256(ots)}\n")
    print(f"  forseglet {sti.name}  sha256 {sha}")
    return 0


# -------------------------------------------------------------------- cli

def main(argv: list[str] | None = None, naa: dt.datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uke", default="",
                    help="ISO-uke, f.eks. 2026-W46. Standard: uka i dag (UTC).")
    ap.add_argument("--forsegl", action="store_true",
                    help="stemple ukefila med OpenTimestamps")
    ap.add_argument("--torrkjor", action="store_true",
                    help="skriv ukefila til stdout, ikke til disk")
    a = ap.parse_args(argv)
    naa = naa or dt.datetime.now(dt.timezone.utc)   # ETT oppslag, CLAUDE.md 1b

    modulen()
    T = fra_isouke(a.uke) if a.uke else mandag(naa.date())
    K = T - dt.timedelta(weeks=INFO_UKER)
    sti = MASKIN_DIR / filnavn(T)
    print(f"Maskinanslag {isouke(T)} (utstedt {T}, informasjon til og med {K})"
          + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    if not a.torrkjor:
        start = dt.datetime.combine(T, dt.time(), dt.timezone.utc)
        if not (start <= naa < frist(T)):
            print(f"::error::{isouke(T)} er ikke denne uka ({isouke(naa.date())}). "
                  f"Et anslag lages og stemples bare i uka det gjelder.")
            return 2
        if sti.exists():
            print(f"  {sti.name} finnes; den lages aldri på nytt")
            return forsegl(sti, T, naa) if a.forsegl else 0

    for kilde in ("lusetall", "sjotemperatur"):
        if K.isoformat() not in snapshot.datoer(kilde):
            print(f"::error::Uke {isouke(K)} ({K}) står ikke i {kilde} ennå. "
                  f"Anslaget for {isouke(T)} bygger på den.")
            return 2

    if a.torrkjor:
        kode = stempel.head(paths.ROT)
    else:
        try:
            kode, _ = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Koden kan ikke gjøres rede for, og lager ikke anslag: {e}")
            return 2

    akv = akvakultur_dato(T)
    # Loggen skrives ikke: inndataene står som inndata_sha256 i ukefila.
    logg = kl.Kjoringslogg("anslag", MASKIN_DIR / "anslag.kjoring.log")
    data = les_panel(logg, FORSTE, K.isoformat(), akv)
    res = regn_ut(data, T)
    tekst = ukefil(T, res, akv_dato=akv,
                   kode=kode, data=stempel.head(paths.DATA_DIR.parent),
                   inndata=inndata_sha256(logg))

    for type_ in TYPER:
        verdier = ", ".join(f"PO{po} {_tall(r['m'])}" for po, r in sorted(
            res[type_].items(), key=lambda x: int(x[0])))
        print(f"  {type_} ({TYPER[type_]['klasse']}): {verdier}")

    if a.torrkjor:
        print(tekst, end="")
        return 0
    MASKIN_DIR.mkdir(parents=True, exist_ok=True)
    sti.write_text(tekst, encoding="utf-8")
    print(f"  skrevet {vis(sti)}  sha256 {sha256(sti)}")
    return forsegl(sti, T, naa) if a.forsegl else 0


if __name__ == "__main__":
    sys.exit(main())
