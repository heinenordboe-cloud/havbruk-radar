"""Stiens kildeledd som ukentlig tidsserie per produksjonsområde.

    python kildeledd.py
    python kildeledd.py --fra 2017 --til 2026-08-31

Beregner formelen fra Stien mfl. 2005 på offentlige data:

    klekte nauplier = N_fisk × N_hunnlus × 0,17 × (T + 4,28)²

Dette er IKKE en analyse. Det er en beregning av en offentlig erklært
formel på offentlige registerdata, og den er hovedleveransen: HI regner
det samme leddet som inngang til lusemodellen sin, men publiserer det
ikke som serie. Ingen korrelasjon kjøres her, og `analyse/` er ikke
involvert utover `kjoringslogg` — som er lesedøra, ikke en analyse.

## To serier, ikke én

Den bindende begrensningen er N_fisk. Lus og temperatur er UKENTLIGE
fra 2012; N_fisk er MÅNEDLIG og finnes først fra oktober 2017. Det gir
to serier som IKKE er samme størrelse, og de holdes derfor i hver sin
fil med hvert sitt navn:

    FULL     2017-10 ->   N_fisk × middel_lok(lus × (T+4,28)²) × 0,17
                          Kildeleddet. Klekte nauplier per time.

    DELVIS   2012    ->   middel_lok(lus × (T+4,28)²)
                          IKKE kildeleddet. Lus × temperatur, uten
                          N_fisk og uten 0,17. Enheten er ikke nauplier
                          og tallene er ikke sammenlignbare med FULL.

N_fisk ekstrapoleres IKKE bakover før 2017-10, og hull fylles ikke med
gjennomsnitt. En uke uten dekket måned mangler i FULL-serien, og det
skal SES framfor å bli et tynnere tall ingen legger merke til.

## Hva et tall her ikke er

Σᵢ(N_fiskᵢ × lusᵢ) ≠ N_fisk_PO × middel(lus).

HI regner kildeleddet PER LOKALITET og summerer. Vi har N_fisk bare per
produksjonsområde, og ganger derfor et PO-aggregat med et PO-middel. De
to er ulike størrelser med mindre lus og fisk er ukorrelert innen
området, og det er de ikke. Dette er en dokumentert tilnærming, ikke en
feil — se docs/beslutninger/2026-08-31-hypotesen-omdefineres.md, og
merk at forbeholdet ikke kan elimineres med offentlige data i dag.

Forbeholdet stemples på HVER RAD i utdataene. Regel 1b-3: en verdi som
avgjør hva dataene BETYR, lagres SAMMEN med dem. En parquet som havner
på en annen maskin om fire måneder skal bære sin egen begrensning.
"""

from __future__ import annotations

import argparse
import datetime as dt
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROT))

from analyse import kjoringslogg              # noqa: E402  (lesedøra, ikke analyse)
from core.paths import DATA_DIR               # noqa: E402

# Stien mfl. 2005. Begge konstantene er DERES og står som navngitte tall,
# ikke inne i et uttrykk — samme form som i analyse/lusepress_mot_fasit.py,
# og med vilje det samme tallet: to steder som regner «det samme leddet»
# med hver sin konstant er formen dette repoet har betalt for flere ganger.
STIEN_T0 = 4.28
STIEN_K = 0.17

FISK_FELT = "beholdning_antall"       # BEHFISK_STK, beholdning ved månedslutt
LUS_FELT = "voksne_hunnlus"
TEMP_FELT = "sjotemperatur"

UT_DIR = DATA_DIR / "kildeledd"
LOGG = UT_DIR / "kildeledd.kjoring.log"

# Valget som må logges, som navn og ikke som en if-setning.
#
# BAER_MAANED  uka ganges med beholdningen ved slutten av SIN EGEN måned,
#              der «sin egen» er måneden i mandagens dato — kildens egen
#              `observed_at`, ikke en måned vi regner ut på nytt.
#
# INTERPOLER   finnes ikke her, og fraværet er valget. Se `_n_fisk`.
BAER_MAANED = "baer_maaned"

FORBEHOLD = (
    "PO-aggregering: N_fisk_PO x middel_lok(lus x (T+4,28)^2) er ikke "
    "sum_lok(N_fisk_lok x lus_lok). N_fisk publiseres bare per "
    "produksjonsomraade. Dokumentert tilnaerming, se "
    "docs/beslutninger/2026-08-31-hypotesen-omdefineres.md"
)

# Forbeholdet om NEVNEREN. Står på hver rad av samme grunn som
# FORBEHOLD og `aggregering`: en parquet som havner et annet sted skal
# bære sin egen begrensning (CLAUDE.md 1b-3).
NEVNERFORBEHOLD = (
    "verdi er et MIDDEL over rapporterende lokaliteter. Slutter en gruppe "
    "lokaliteter å rapportere — utslakting, brakklegging eller manglende "
    "innrapportering — endres middelet uten at lusepresset i sjøen har "
    "endret seg. Les n_rapporterende SAMMEN med verdi: et fall i begge "
    "samtidig er ikke et fall i lusepress. n_i_po er alle lokaliteter i "
    "PO-et den uka, n_brakklagt de som er markert brakklagt (isFallow). "
    "n_i_po - n_brakklagt - n_rapporterende er aktive anlegg som IKKE "
    "rapporterte."
)

FORMEL_FULL = "N_fisk_PO * middel_lok(lus * (T + 4,28)^2) * 0,17"
FORMEL_DELVIS = "middel_lok(lus * (T + 4,28)^2)  [UTEN N_fisk, UTEN 0,17]"

# Skjemaet står EKSPLISITT, ikke utledet av de første radene. Uten det
# leser polars `n_fisk` som Null — de 296 første ukene er DELVIS-rader
# uten N_fisk — og faller så over den første i64-en den møter i 2017.
# En utledet type er dessuten en egenskap ved RADREKKEFØLGEN, og en
# leveranse skal ha samme kolonnetyper uansett hvilket år den starter i.
SKJEMA = {
    "serie": pl.Utf8,
    "po": pl.Int64,
    "po_navn": pl.Utf8,
    "uke_mandag": pl.Utf8,
    "iso_aar": pl.Int64,
    "iso_uke": pl.Int64,
    "n_lokaliteter": pl.Int64,
    # Dekningen bak middelet. Se `bygg` og NEVNERFORBEHOLD: uten disse
    # kan ingen skille «lus falt» fra «anleggene med mest lus ble tømt»,
    # og de to ser IDENTISKE ut i kurven.
    "n_i_po": pl.Int64,
    "n_rapporterende": pl.Int64,
    "n_brakklagt": pl.Int64,
    "lus_middel": pl.Float64,
    "temp_middel": pl.Float64,
    "n_fisk": pl.Int64,
    "n_fisk_maaned": pl.Utf8,
    "verdi": pl.Float64,
    "enhet": pl.Utf8,
    "formel": pl.Utf8,
    "stien_k": pl.Float64,
    "stien_t0": pl.Float64,
    "aggregering": pl.Utf8,
    "forbehold": pl.Utf8,
}


# --------------------------------------------------------------- lesing

def po_kart(logg: kjoringslogg.Kjoringslogg) -> tuple[dict[str, int],
                                                      dict[int, str]]:
    """lokalitetsnummer -> produksjonsområde, fra SISTE akvakultursnapshot.

    ADVARSEL, og den følger med hele serien: dette er DAGENS
    PO-tilhørighet påført historiske uker. En lokalitet flytter seg ikke,
    så koden er stabil for lokaliteter som fortsatt står i registeret —
    men en lokalitet som ble slettet før i dag har ingen kode i det hele
    tatt og faller ut av alle uker, også de den var i drift.

    Antallet lokaliteter per uke skrives derfor ut i serien
    (`n_lokaliteter`), slik at en uke som hviler på få lokaliteter kan
    ses framfor å bli et middel med samme utseende som alle andre.

    SISTE, og ikke «siste før `--til`». Det er et valg: bundet til `--til`
    ville PO-kartet endret seg stille når noen smalnet datointervallet,
    og to kjøringer med ulikt intervall ville skilt seg på mer enn
    intervallet. Kartet er en egenskap ved REGISTERET slik det står nå,
    ikke ved perioden vi regner på. Loggen fører hvilken dato som ble
    lest, så valget er etterprøvbart.
    """
    from core import snapshot
    dato = snapshot.siste_dato("akvakultur")
    if dato is None:
        raise SystemExit("Ingen akvakultursnapshot å hente PO-kartet fra.")
    ramme = logg.les_dato("akvakultur", dato)
    if ramme is None:
        raise SystemExit(f"akvakultur {dato} kunne ikke leses.")

    bred = ramme.pivot(values="value", index="entity_id", on="field",
                       aggregate_function="first")
    kart: dict[str, int] = {}
    navn: dict[int, str] = {}
    for r in bred.iter_rows(named=True):
        kode = r.get("prodomraade_kode")
        if kode in (None, ""):
            continue
        po = int(kode)
        kart[r["entity_id"]] = po
        if po not in navn and r.get("prodomraade_navn"):
            navn[po] = r["prodomraade_navn"]
    return kart, navn


def les_temp(logg: kjoringslogg.Kjoringslogg, aar: int) -> dict[tuple[str, str], float]:
    """(lokalitet, ukedato) -> sjøtemperatur, for ett kalenderår.

    Nøkkelen er SNAPSHOTETS EGEN DATO og ikke (iso-år, iso-uke). De to
    er den samme uka, men datoen er kildens `observed_at` og ukenummeret
    er noe vi regner ut — og et andre oppslag av et tidspunkt kilden
    allerede har svart på, er formen F7 hadde (CLAUDE.md 1b).

    `temperatur_er_rapportert` leses ikke: en lokalitet uten måling har
    ingen `sjotemperatur`-rad i det hele tatt, så fraværet i denne
    ordboka ER flagget. Det som IKKE gjøres er å lese en manglende verdi
    som 0 grader — 0,0 finnes som ekte måling, og med (T + 4,28)² er
    forskjellen på «ukjent» og «0» et faktisk tall på smittepresset.
    """
    ut: dict[tuple[str, str], float] = {}
    for dato, df in logg.les("sjotemperatur", f"{aar}-01-01", f"{aar}-12-31"):
        t = df.filter(pl.col("field") == TEMP_FELT).select("entity_id", "value")
        for e, v in t.iter_rows():
            try:
                ut[(e, dato)] = float(v)
            except (TypeError, ValueError):
                continue
    return ut


def les_biomasse(logg: kjoringslogg.Kjoringslogg,
                 til: str) -> tuple[dict[tuple[int, str], int], dict[str, int]]:
    """(po, "YYYY-MM") -> N_fisk, og fisken uten PO-kode per måned.

    Nevneren som forsvinner skal være synlig. 0,96–4,57 % av all fisk har
    ingen PO-kode og faller ut av enhver PO-summering (KILDE-BIOMASSE
    punkt 6); det tallet står i kjøringsloggen framfor å bli oppdaget av
    den neste som lurer på hvorfor summen ikke stemmer.
    """
    fisk: dict[tuple[int, str], int] = {}
    uten_po: dict[str, int] = {}
    for dato, df in logg.les("biomasse", "2000-01-01", til):
        maaned = dato[:7]
        rader = df.filter(pl.col("field") == FISK_FELT).select("entity_id", "value")
        for e, v in rader.iter_rows():
            try:
                antall = int(float(v))
            except (TypeError, ValueError):
                continue
            if e in (None, "", "0"):
                uten_po[maaned] = uten_po.get(maaned, 0) + antall
                continue
            try:
                fisk[(int(e), maaned)] = antall
            except ValueError:
                uten_po[maaned] = uten_po.get(maaned, 0) + antall
    return fisk, uten_po


# ------------------------------------------------------------- beregning

def _n_fisk(fisk: dict[tuple[int, str], int], po: int, maaned: str) -> int | None:
    """N_fisk for uka. `None` = måneden er ikke dekket, og uka faller ut.

    ## Valget, og hvorfor det ble dette

    Lus og temperatur er ukentlige. N_fisk er månedlig, og er dessuten
    BEHOLDNINGEN VED MÅNEDSLUTT — et øyeblikksbilde, ikke et månedssnitt.
    Da finnes det to forsvarlige måter å sette dem sammen:

        BAER FLATT     uka ganges med beholdningen ved slutten av sin
                       egen måned. Hver ukeverdi peker tilbake på
                       nøyaktig ETT publisert tall.

        INTERPOLER     mellom to månedsmidtpunkter. Glattere kurve, og
                       ingen sprang ved månedsskiftet.

    **Valgt: bær flatt.** Tre grunner, i rekkefølge etter vekt:

    1. `BEHFISK_STK` er en BEHOLDNING på et tidspunkt, ikke en rate over
       en periode. En interpolasjon mellom to månedslutt antar at
       bestanden vokser jevnt gjennom måneden. Den gjør den ikke:
       utsett og slakt er klumpete hendelser, og `utsett_smolt_antall`
       og `uttak_antall` i den samme fila er MÅNEDSSUMMER — de sier hvor
       mye som skjedde, ikke når i måneden det skjedde. En glatt kurve
       ville påstått en tidsprofil ingen kilde har oppgitt.

    2. Hver ukeverdi skal kunne spores til ett publisert tall. Med
       interpolasjon er hver ukeverdi et tall vi fant på, som ikke
       finnes hos Fiskeridirektoratet, og en leser som slår opp fila
       finner ikke igjen noe.

    3. Presedens i repoet. `analyse/lusepress_mot_fasit.nfisk_for_uke`
       avviser allerede interpolasjon med samme begrunnelse («en
       interpolasjon mellom to månedslutt ville vært et tall vi fant
       på»). To steder som regner det samme leddet skal ikke velge hver
       sin vei.

    Prisen står i output og skal ikke bortforklares: serien får SPRANG
    ved månedsskiftene. Et sprang i FULL-serien som ikke finnes i
    DELVIS-serien er et månedsskifte i N_fisk, ikke en hendelse i sjøen.

    ## Måneden er mandagens måned

    Uka dateres med mandagen — kildens egen `observed_at` — og måneden
    leses av den datoen framfor å regnes ut av ukemidten. En uke som
    krysser et månedsskifte havner derfor i mandagens måned: uke 18/2021
    begynner 3. mai og teller som mai, uke 17/2021 begynner 26. april og
    teller som april selv om fire av dens sju dager er i mai.
    """
    return fisk.get((po, maaned))


def bygg(logg: kjoringslogg.Kjoringslogg, fra_aar: int, til: str) -> pl.DataFrame:
    """Én rad per (PO, uke). Begge seriene i samme ramme, skilt av `serie`."""
    kart, po_navn = po_kart(logg)
    fisk, uten_po = les_biomasse(logg, til)

    logg.valg("po_kart.kilde", "akvakultur.prodomraade_kode, siste snapshot")
    logg.valg("po_kart.valg", "siste snapshot, IKKE siste før --til")
    logg.valg("po_kart.lokaliteter", len(kart))
    logg.valg("po_kart.forbehold",
              "dagens PO-tilhørighet påført historiske uker; slettede "
              "lokaliteter har ingen kode og faller ut")
    logg.valg("biomasse.maaneder", len(set(m for _, m in fisk)))
    logg.valg("biomasse.forste_maaned", min((m for _, m in fisk), default="(ingen)"))
    logg.valg("biomasse.siste_maaned", max((m for _, m in fisk), default="(ingen)"))
    if uten_po:
        andeler = []
        for m in sorted(uten_po):
            i_po = sum(v for (p, mm), v in fisk.items() if mm == m)
            if i_po:
                andeler.append(uten_po[m] / (i_po + uten_po[m]))
        if andeler:
            logg.valg("biomasse.andel_uten_po",
                      f"{min(andeler):.2%} – {max(andeler):.2%} av all fisk "
                      f"mangler PO-kode og faller ut av PO-summeringen")

    rader: list[dict] = []
    aar_til = int(til[:4])

    for aar in range(fra_aar, aar_til + 1):
        temp = les_temp(logg, aar)
        # (po, ukedato) -> lister å ta middel av. Ett pass, ikke to:
        # «hvor mange lokaliteter» og «hva er middelet» er det samme
        # oppslaget, og to tellere for samme sak er formen F6/F7/F8 hadde.
        # Tellerne bor i SAMME bøtte som middelet, ikke i en egen
        # struktur ved siden av. To passeringer over de samme radene
        # ville vært to tellere for samme sak — formen F6, F7 og F8
        # hadde — og de ville kunnet svare ulikt den dagen et filter
        # endres i det ene passet og ikke i det andre.
        bøtte: dict[tuple[int, str], dict[str, list]] = defaultdict(
            lambda: {"delvis": [], "lus": [], "temp": [],
                     "i_po": 0, "rapporterende": 0, "brakklagt": 0})

        for dato, df in logg.les("lusetall", f"{aar}-01-01", min(f"{aar}-12-31", til)):
            bred = df.pivot(values="value", index="entity_id", on="field",
                            aggregate_function="first")
            for r in bred.iter_rows(named=True):
                lok = r["entity_id"]
                po = kart.get(lok)
                if po is None:
                    continue

                # Telles FØR filtrene under. Det er hele poenget: de
                # lokalitetene som faller ut av middelet er nettopp dem
                # ingen kan se i kurven.
                b = bøtte[(po, dato)]
                b["i_po"] += 1
                rapporterte = r.get("lus_er_rapportert") == "True"
                b["rapporterende"] += rapporterte
                b["brakklagt"] += r.get("brakklagt") == "True"

                if not rapporterte:
                    continue
                lus = r.get(LUS_FELT)
                if lus in (None, ""):
                    continue
                t = temp.get((lok, dato))
                if t is None:
                    continue
                lus = float(lus)
                b["delvis"].append(lus * (t + STIEN_T0) ** 2)
                b["lus"].append(lus)
                b["temp"].append(t)

        for (po, dato), b in bøtte.items():
            # Bøtta finnes nå for hvert (po, uke) der PO-et hadde en
            # lokalitet i det hele tatt — også der ingen rapporterte.
            # Uten dette ville st.mean() fått en tom liste.
            if not b["delvis"]:
                continue
            iso = dt.date.fromisoformat(dato).isocalendar()
            delvis = st.mean(b["delvis"])
            maaned = dato[:7]
            n = _n_fisk(fisk, po, maaned)

            felles = {
                "po": po,
                "po_navn": po_navn.get(po, ""),
                "uke_mandag": dato,
                "iso_aar": iso.year,
                "iso_uke": iso.week,
                "n_lokaliteter": len(b["delvis"]),
                # n_lokaliteter er de som kom INN i middelet — de måtte
                # også ha temperatur. n_rapporterende er de som leverte
                # lusetall. Differansen er lokaliteter vi mistet på
                # temperatur, ikke på rapportering, og de to skal kunne
                # skilles.
                "n_i_po": b["i_po"],
                "n_rapporterende": b["rapporterende"],
                "n_brakklagt": b["brakklagt"],
                "lus_middel": st.mean(b["lus"]),
                "temp_middel": st.mean(b["temp"]),
                # Regel 1b-3: verdiene som avgjør hva raden BETYR, står
                # PÅ raden. En parquet på en annen maskin om fire måneder
                # skal bære sin egen formel og sitt eget forbehold.
                "stien_k": STIEN_K,
                "stien_t0": STIEN_T0,
                "aggregering": BAER_MAANED,
                "forbehold": FORBEHOLD + " || " + NEVNERFORBEHOLD,
            }

            rader.append({**felles,
                          "serie": "delvis",
                          "verdi": delvis,
                          "enhet": "lus x (grader C + 4,28)^2 (ikke nauplier)",
                          "formel": FORMEL_DELVIS,
                          "n_fisk": None,
                          "n_fisk_maaned": None})

            # FULL bare der måneden faktisk er dekket. Ingen ekstrapolering
            # bakover, ingen utfylling med gjennomsnitt: en uke uten dekket
            # måned MANGLER, og det skal ses.
            if n is not None:
                rader.append({**felles,
                              "serie": "full",
                              "verdi": n * delvis * STIEN_K,
                              "enhet": "klekte nauplier per time",
                              "formel": FORMEL_FULL,
                              "n_fisk": n,
                              "n_fisk_maaned": maaned})

    return pl.DataFrame(rader, schema=SKJEMA).sort("serie", "po", "uke_mandag")


# ------------------------------------------------------------------ ut

def skriv(ramme: pl.DataFrame, serie: str) -> Path:
    """Én fil per serie, med stabilt navn.

    Overskriver med vilje, som changelog gjør (CLAUDE.md regel 2). Serien
    er AVLEDET — en ren funksjon av snapshots som alle er append-only —
    og kan regnes ut igjen når som helst. En ny fil per kjøring ville
    latt en regenerering vokse repoet kvadratisk uten å bevare noe som
    ikke allerede er bevart. Rådataene er urørt; det er de som ikke kan
    hentes igjen.
    """
    UT_DIR.mkdir(parents=True, exist_ok=True)
    sti = UT_DIR / f"kildeledd-{serie}.parquet"
    ramme.filter(pl.col("serie") == serie).write_parquet(sti)
    return sti


def les_serier() -> dict[str, pl.DataFrame]:
    """De to seriene fra disk, eller tom dict om de ikke er beregnet.

    Lesingen bor HER og ikke hos den som viser fram tallene. To grunner,
    og den andre er den viktige:

    1. Modulen som eier formatet eier begge veier gjennom det. Endres
       skjemaet, endres lesingen i samme fil.
    2. `tests/test_pipeline.test_ingen_leser_snapshots_utenom_les` feller
       enhver fil som kjenner BÅDE `RAW_DIR` og `read_parquet` — det er
       vakten mot en lesevei utenom persondatafilteret i
       `snapshot._les()` (CLAUDE.md regel 3). `vis.py` kjenner `RAW_DIR`,
       så en `read_parquet` der ville vært et brudd på formen selv om
       fila den leser er et PO-aggregat uten personopplysninger. Vakten
       er grovkornet med vilje, og den skal ikke dempes for et unntak
       som «egentlig går bra» — det er nøyaktig begrunnelsen ENK-åpningen
       16.08 hvilte på.
    """
    ut: dict[str, pl.DataFrame] = {}
    for serie in ("full", "delvis"):
        sti = UT_DIR / f"kildeledd-{serie}.parquet"
        if sti.exists():
            ut[serie] = pl.read_parquet(sti)
    return ut


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fra", type=int, default=2012, help="første kalenderår")
    p.add_argument("--til", default=dt.date.today().isoformat(),
                   help="siste dato som leses (YYYY-MM-DD)")
    args = p.parse_args()

    UT_DIR.mkdir(parents=True, exist_ok=True)
    logg = kjoringslogg.Kjoringslogg("kildeledd", LOGG)
    logg.valg("formel", "Stien mfl. 2005: N_fisk x N_hunnlus x 0,17 x (T + 4,28)^2")
    logg.valg("stien.k", STIEN_K)
    logg.valg("stien.t0", STIEN_T0)
    logg.valg("avgrensning.fra_aar", args.fra)
    logg.valg("avgrensning.til", args.til)
    logg.valg("aggregering.n_fisk", BAER_MAANED)
    logg.valg("aggregering.begrunnelse",
              "BEHFISK_STK er beholdning ved månedslutt, ikke en rate. "
              "Interpolasjon mellom månedslutt ville påstått en tidsprofil "
              "ingen kilde oppgir; flat bæring lar hver ukeverdi peke på ett "
              "publisert tall. Pris: sprang ved månedsskiftene.")
    logg.valg("aggregering.maaned_for_uke", "måneden i mandagens dato (observed_at)")
    logg.valg("forbehold.po_aggregering", FORBEHOLD)
    logg.valg("forbehold.nevner", NEVNERFORBEHOLD)
    logg.valg("dekning.felter", "n_i_po, n_rapporterende, n_brakklagt — "
                                "bæres på HVER rad, ikke bare her")
    logg.valg("dekning.brakklagt_kilde",
              "lusetall.brakklagt (BarentsWatch isFallow). Verifisert "
              "02.09.2026: 100 % dekning i alle 15 årganger, kun "
              "True/False, ingen null")
    logg.valg("ekstrapolering", "ingen — N_fisk føres ikke bakover før 2017-10, "
                                "og hull fylles ikke med gjennomsnitt")

    ramme = bygg(logg, args.fra, args.til)

    print(f"\nKildeleddet — Stien mfl. 2005, per produksjonsområde per uke\n")
    for serie in ("full", "delvis"):
        del_ = ramme.filter(pl.col("serie") == serie)
        if del_.is_empty():
            print(f"  {serie:<7} ingen rader")
            continue
        sti = skriv(ramme, serie)
        logg.valg(f"ut.{serie}.rader", del_.height)
        logg.valg(f"ut.{serie}.uker", del_["uke_mandag"].n_unique())
        logg.valg(f"ut.{serie}.po", del_["po"].n_unique())
        print(f"  {serie:<7} {del_.height:>6} rader, "
              f"{del_['uke_mandag'].n_unique():>3} uker, "
              f"{del_['po'].n_unique():>2} PO, "
              f"{del_['uke_mandag'].min()} .. {del_['uke_mandag'].max()}")
        print(f"          {sti}")

    sti = logg.skriv()
    print(f"\n  kjøringslogg: {sti}")
    print(f"\n  Forbehold som følger med hver rad:\n    {FORBEHOLD}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
