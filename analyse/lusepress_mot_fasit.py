"""Første utforskning: skiller lusetallene ekspertgruppens kategorier?

    python analyse/lusepress_mot_fasit.py
    python analyse/lusepress_mot_fasit.py --biomasse-versjon forste \
        --logg analyse/ut/lusepress-bio-forste.kjoring.log
    python analyse/lusepress_mot_fasit.py --vindu 14-26 --fra-aar 2020
    python analyse/lusepress_mot_fasit.py --akvakultur-versjon 1

Leser snapshots fra HAVBRUK_DATA_DIR, kobler mot fasiten i
analyse/fasit/ og skriver tall til stdout + plott til analyse/ut/.

## Kjøringsloggen

Hver kjøring skriver `analyse/ut/lusepress.kjoring.log` med ALLE valg
som påvirket tallene — avgrensning, vindu, mål, fasitens innholds-hash,
PERSONFORMER-lista, git-commit, og hvilken snapshot-FIL hver dato ble
lest fra, med løpenummer og `published_at`.

Grunnen er at `rho = +0,761` ikke er en egenskap ved dataene alene. Det
er en egenskap ved dataene og ved et dusin valg som ikke sto noe sted
før 26.08.2026, og som ingen kunne rekonstruere tre måneder senere. Se
`analyse/kjoringslogg.py`.

Snapshotene leses derfor gjennom loggen og ikke gjennom
`snapshot.les_mellom()` direkte: en logg som skrives ved siden av
lesingen er en påstand om den, en logg som skrives AV lesingen er en
beskrivelse av den. To tellere for samme sak er formen F6, F7 og F8
hadde.

Dette er utforskning. Ingen modell, ingen regresjon, ingen konklusjon
om at noe virker. Ingenting i core/ røres.

Avgrensning 2018-2026: rapporteringsdekningen steg fra 80,7 % (2012)
til 99,2 % (2026) og PO-dekningen fra 78,1 % til 95,6 %. En stigende
trend i et aggregat over hele serien kan være ren dekningsvekst.
Produksjonsområdene ble innført 2017, så PO-kartet er heller ikke
retroaktivt gyldig før det. Dekning per år rapporteres, slik at
avgrensningen kan etterprøves.

## Tre valg som ble FLAGG 26.08.2026

`--biomasse-versjon`, `--vindu` og `--fra-aar`. De tre er ulike i art,
og bare den første er teknisk:

- **Biomasseversjonen er ANALYTISK.** 81 av 103 måneder finnes i to
  påstander — basefila hentet 25.08.2026 og Wayback-kopien utgitt
  20.07.2024 — og de er uenige om 21,9 % av PO-månedene. Hvilken av dem
  et `N_fisk` kommer fra, er ikke en detalj om filhåndtering; det er
  hvilken av Fiskeridirektoratets to meninger om fortiden tallet hviler
  på. Standard er `gjeldende`, som for denne kilden er basefila.
- **Vinduet og startåret er TOLKNINGER.** Uke 16-24 er valgt fordi det
  grovt er utvandringsvinduet for villakssmolt, ikke fordi noe er målt
  til å begynne i uke 16. 2018 er valgt av dekningshensyn. Begge er
  forsvarlige og ingen av dem er utledet av data.

Grunnen til at de er argumenter og ikke konstanter er punkt 4 i
kjøringsloggens begrunnelse: endrer du en konstant, endrer du også
`git.commit` og `git.rent_arbeidstre` i loggen, og da skiller to logger
seg på tre linjer der ett valg ble endret. En følsomhetssjekk skal
etterlate en logg som skiller seg på NØYAKTIG det valget.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import statistics as st
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Snapshots leses gjennom `snapshot.les_mellom()`, ikke med
# `pl.read_parquet()` på en glob. Det er ikke en stilpreferanse:
# persondatafilteret ligger i `snapshot._les()`, og snapshotene fra
# 16.-17.08.2026 inneholder 34 enkeltpersonforetak hver som er
# append-only og blir stående. En analyse som globber selv, leser dem —
# og `test_ingen_leser_snapshots_utenom_les()` feller den for det.
from core import snapshot                # noqa: E402
from analyse import kjoringslogg          # noqa: E402

FASIT = ROOT / "analyse" / "fasit" / "ekspertgruppen-po-kategori.csv"
UT = ROOT / "analyse" / "ut"
LOGGFIL = UT / "lusepress.kjoring.log"

STANDARD_FRA_AAR, TIL_AAR = 2018, 2026
STANDARD_VINDU = (16, 24)        # utgangspunkt: grovt utvandringsvinduet
STANDARD_VINDU_VID = (14, 26)    # følsomhetssjekk
KATEGORIER = ["lav", "moderat", "hoy"]
RANG = {"lav": 0, "moderat": 1, "hoy": 2}

# Stien mfl. 2005, hele formelen:
#
#     klekte nauplier = N_fisk × N_hunnlus × 0,17 × (T + 4,28)²
#
# Begge konstantene er DERES og står som navngitte tall, ikke inne i et
# uttrykk. 0,17 var utelatt fram til 26.08.2026 med den begrunnelsen at
# en ren skalering ikke endrer noen rangkorrelasjon. Det er fortsatt
# sant for rho — men ikke for tallets STØRRELSE, og fra og med denne
# kjøringen skrives absolutte naupliitall ut. Da er en utelatt faktor
# på 0,17 en påstand om verden som er nesten seks ganger for stor.
STIEN_T0 = 4.28
STIEN_K = 0.17


# ------------------------------------------------------------- avgrensning

@dataclass(frozen=True)
class Avgrensning:
    """Hvilke observasjoner som teller. ETT sted, sendt inn overalt.

    Fram til 26.08.2026 lå `FRA_AAR` og `UTVANDRING` som modulkonstanter
    og ble slått opp direkte av åtte funksjoner. Det er samme form som
    F6/F7 i miniatyr — ikke fordi to oppslag kunne svart ulikt (en
    konstant kan ikke det), men fordi et VALG som ikke reiser gjennom
    kallkjeden heller ikke kan varieres uten å redigere fila. Og et valg
    som krever en redigering, skitner arbeidstreet og gjør at to
    kjøringslogger skiller seg på `git.commit` i tillegg til på valget.

    `vindu_vid` ligger her sammen med `vindu` fordi følsomhetssjekken
    må flytte seg med hovedvinduet. Sto den fast på 14-26 mens vinduet
    ble satt til 20-30, ville «følsomhet for vinduet» sammenlignet to
    vinduer som ikke lenger har noe med hverandre å gjøre.
    """

    fra_aar: int
    til_aar: int
    vindu: tuple[int, int]
    vindu_vid: tuple[int, int]

    @property
    def forkastningsgrunn(self) -> str:
        return f"ISO-år utenfor [{self.fra_aar}, {self.til_aar}]"

    def i_iso_aar(self, dato_tekst: str) -> bool:
        """Ligger denne ukas snapshot innenfor årsavgrensningen?

        Datointervallet i `logg.les()` er KALENDERDATOER, avgrensningen er
        ISO-ÅR, og de to spriker rundt nyttår: 2018-12-31 er uke 1 i
        ISO-året 2019. Intervallet er derfor med vilje en dag vidt i hver
        ende, og denne prøven skjærer av resten.

        Den er én navngitt metode fordi den brukes to steder — lusetall
        og sjøtemperatur — og de to MÅ avgrense likt. Gjorde de det ikke,
        ville en prediktor hvilt på et annet utvalg uker enn den andre,
        og en forskjell mellom dem kunne vært avgrensningen framfor
        variabelen.
        """
        aar = dt.date.fromisoformat(dato_tekst).isocalendar().year
        return self.fra_aar <= aar <= self.til_aar

    def i_vindu(self, uke: int) -> bool:
        return self.vindu[0] <= uke <= self.vindu[1]

    @property
    def aar(self) -> range:
        return range(self.fra_aar, self.til_aar + 1)


def les_fasit() -> dict[tuple[int, int], dict]:
    """(po, aar) -> rad. `ukjent` beholdes som rad; den er en opplysning."""
    ut = {}
    with FASIT.open(encoding="utf-8") as f:
        rader = csv.DictReader(r for r in f if not r.startswith("#"))
        for r in rader:
            ut[(int(r["po"]), int(r["aar"]))] = {
                "kategori": r["kategori"],
                "kilde": r["kilde"],
                "sikkerhet": r["sikkerhet"],
            }
    return ut


def akvakultur_naa(logg: kjoringslogg.Kjoringslogg,
                   versjonsvalg) -> pl.DataFrame:
    """Det akvakultursnapshotet analysen bruker — lest PÅ ETT STED.

    `po_kart()` og `bredde_kart()` slo begge opp «nyeste dato» og leste
    fila hver for seg. To oppslag som kan svare ulikt er formen F6, F7 og
    F8 hadde, og her er den ikke teoretisk: kjører den ukentlige jobben
    mellom de to kallene, får PO-kartet én dato og breddegradene en
    annen — og geografikontrollen sammenligner da to registre.

    Hvilken DATO som er nyeste avgjøres av filnavnene. Hvilken PÅSTAND om
    den datoen som gjelder, avgjør `versjonsvalg`: 2026-08-24 finnes i
    fire versjoner, og loggen fører hvilken som ble lest.
    """
    siste = snapshot.siste_dato("akvakultur")
    if siste is None:
        raise SystemExit("fant ingen akvakultursnapshots")
    ramme = logg.les_dato("akvakultur", siste, versjonsvalg=versjonsvalg)
    if ramme is None:
        raise SystemExit(
            f"akvakultur {siste} finnes ikke i versjon {versjonsvalg!r}")
    return ramme


def po_kart(akva: pl.DataFrame) -> dict[str, int]:
    """localityNo -> produksjonsområde, fra akvakultursnapshotet.

    ADVARSEL, og den gjelder hele analysen: dette er dagens PO-tilhørighet
    påført historiske uker. En lokalitet flytter seg ikke, så koden er
    stabil for lokaliteter som fortsatt finnes — men en lokalitet som ble
    slettet fra registeret før i dag har ingen kode i det hele tatt, og
    faller ut. Det er hele grunnen til at PO-dekning rapporteres per år.
    """
    par = akva.filter(pl.col("field") == "prodomraade_kode").select("entity_id", "value")
    return {e: int(v) for e, v in par.iter_rows() if v not in (None, "")}


def bredde_kart(akva: pl.DataFrame) -> dict[str, float]:
    """localityNo -> breddegrad, fra det SAMME akvakultursnapshotet.

    Samme forbehold som po_kart(): dagens register påført historiske uker.
    Brukes bare til KONTROLLEN — om temperaturen forklarer noe utover
    geografi — og ikke som prediktor.
    """
    par = akva.filter(pl.col("field") == "breddegrad").select("entity_id", "value")
    ut = {}
    for e, v in par.iter_rows():
        try:
            ut[e] = float(v)
        except (TypeError, ValueError):
            continue
    return ut


def les_temp(logg: kjoringslogg.Kjoringslogg,
             avg: Avgrensning) -> dict[tuple[str, int, int], float]:
    """(lok, iso-år, iso-uke) -> sjøtemperatur.

    Samme ukeakse og samme etterslep som lusetall — det ER den samme
    rapporten, hentet fra CSV-eksporten i stedet for ukeendepunktet. Se
    docs/KILDE-SJOTEMPERATUR.md; de to er krysset mot hverandre på tolv
    lokaliteter i uke 30/2018 og gir samme verdi.

    `temperatur_er_rapportert` leses ikke her: en rad uten temperatur har
    ingen `sjotemperatur`-observasjon i det hele tatt, så fraværet i denne
    ordboka ER flagget. Det som IKKE gjøres er å lese en manglende verdi
    som 0 grader — 0,0 forekommer 622 ganger i historikken som en ekte
    måling, og med (T + 4,28)^2 er forskjellen på «ukjent» og «0» et
    faktisk tall på smittepresset.
    """
    ut: dict[tuple[str, int, int], float] = {}
    for dato_tekst, df in logg.les(
            "sjotemperatur", f"{avg.fra_aar - 1}-12-01", f"{avg.til_aar + 1}-01-31",
            behold=avg.i_iso_aar, forkastningsgrunn=avg.forkastningsgrunn):
        iso = dt.date.fromisoformat(dato_tekst).isocalendar()
        t = df.filter(pl.col("field") == "sjotemperatur").select("entity_id", "value")
        for e, v in t.iter_rows():
            try:
                ut[(e, iso.year, iso.week)] = float(v)
            except (TypeError, ValueError):
                continue
    return ut


def les_uker(logg: kjoringslogg.Kjoringslogg, avg: Avgrensning,
             kart: dict[str, int],
             temp: dict[tuple[str, int, int], float]) -> list[dict]:
    """Én rad per lokalitet-uke, for uker i [fra_aar, til_aar].

    `maaned` er MÅNEDEN I SNAPSHOTETS EGEN DATO, ikke en måned vi regner
    ut av ISO-uka. Lusetall daterer uka med mandagen, og den datoen er
    kildens egen påstand om hvilket tidspunkt raden handler om
    (`observed_at`). Å utlede måneden på nytt — av torsdagen, av
    ukemidten — ville vært et andre oppslag av et tidspunkt kilden
    allerede har svart på, og det er formen F7 hadde.

    Konsekvensen skal stå tydelig: en uke som krysser et månedsskifte
    havner i mandagens måned. Uke 18/2021 begynner 3. mai og teller som
    mai; uke 17/2021 begynner 26. april og teller som april, selv om
    fire av dens sju dager er i mai. Koblingen mot biomasse er dermed
    grovere enn en dag-for-dag-vekting ville vært, og det er et valg
    som føres i loggen.
    """
    rader = []
    # Intervallet er kalenderdatoer, mens avgrensningen er ISO-år. De to
    # spriker rundt nyttår, så vinduet er med vilje en dag vidt i hver
    # ende og ISO-året avgjøres av `avg.i_iso_aar` — som `logg.les()` fører
    # som en FORKASTNING og ikke som et hull. Se kjoringslogg.Forkastet:
    # «uke 52/2017 ble lest» og «uke 52/2017 ble valgt bort» gir ulike
    # tall, og bare det andre er et valg noen har tatt.
    for dato_tekst, df in logg.les(
            "lusetall", f"{avg.fra_aar - 1}-12-01", f"{avg.til_aar + 1}-01-31",
            behold=avg.i_iso_aar, forkastningsgrunn=avg.forkastningsgrunn):
        iso = dt.date.fromisoformat(dato_tekst).isocalendar()
        bred = df.pivot(values="value", index="entity_id", on="field",
                        aggregate_function="first")
        for r in bred.iter_rows(named=True):
            lus = r.get("voksne_hunnlus")
            rader.append({
                "lok": r["entity_id"],
                "aar": iso.year,
                "uke": iso.week,
                "maaned": dato_tekst[:7],
                "po": kart.get(r["entity_id"]),
                "brakklagt": r.get("brakklagt") == "True",
                "rapportert": r.get("lus_er_rapportert") == "True",
                "lus": float(lus) if lus not in (None, "") else None,
                "rensefisk": r.get("har_rensefisk") == "True",
                "mekanisk": r.get("har_mekanisk_fjerning") == "True",
                "medikament": r.get("har_medikamentell_behandling") == "True",
                "temp": temp.get((r["entity_id"], iso.year, iso.week)),
            })
    return rader


# -------------------------------------------------------------- N_fisk

# Feltet er `BEHFISK_STK` slik Fiskeridirektoratet definerer det:
# «Beholdning av fisk ved månedslutt, målt i antall stk.» Det er det
# INNRAPPORTERTE tallet; biomassen i kg er det avledede. Se
# docs/KILDE-BIOMASSE.md punkt 2 — det er grunnen til at Stiens N_fisk
# kan leses direkte i stedet for å regnes ut av tonn og snittvekt.
FISK_FELT = "beholdning_antall"
ANDEL_FELT = "andel_av_beholdning"
UTEN_PO = "uten_po"


@dataclass(frozen=True)
class Biomasse:
    """N_fisk per produksjonsområde per måned, og nevneren som mangler.

    `uten_po` og `andel_uten_po` ligger her og ikke i en egen lesing av
    samme fil: de er den samme lesingen, og et andre oppslag av samme
    tall er formen dette repoet har betalt for fire ganger. De er også
    det som gjør nevneren SYNLIG — 0,96-4,57 % av all fisk har ingen
    PO-kode og faller ut av enhver PO-summering. Se KILDE-BIOMASSE
    punkt 6: en nevner som forsvinner stille er verre enn en som er rar.
    """

    fisk: dict[tuple[int, str], int]     # (po, "YYYY-MM") -> antall fisk
    uten_po: dict[str, int]              # "YYYY-MM"       -> antall fisk
    andel_uten_po: dict[str, float]      # "YYYY-MM"       -> andel av alt
    maaneder: tuple[str, ...]            # månedene som faktisk ble lest


def les_fisk(logg: kjoringslogg.Kjoringslogg, avg: Avgrensning,
             versjonsvalg) -> Biomasse:
    """N_fisk fra biomassesnapshotene, gjennom den samme loggfasaden.

    Dette er den ENESTE kilden i analysen der versjonsvalget har noe å
    skille: 81 av 103 måneder finnes både som basefila (hentet
    25.08.2026, utgivelse ukjent) og som Wayback-kopien (utgitt
    20.07.2024), og de er uenige om 21,9 % av PO-månedene. `gjeldende`
    gir basefila, `forste` gir 2024-påstanden der den finnes.

    `observed_at` er siste dag i måneden — ikke en pyntedato, men fordi
    `BEHFISK_STK` ER beholdningen ved månedslutt. Måneden leses derfor
    av snapshotdatoen og regnes ikke ut på nytt.

    Manglende og utolkbare verdier UTELATES, aldri leses som 0. Et
    produksjonsområde uten oppgitt beholdning og ett med null fisk er
    ikke det samme, og med N_fisk som en MULTIPLIKATOR i Stien-formelen
    ville en feillest null gjort hele naupliitallet til null — altså den
    sterkeste mulige påstanden om at det ikke er smittepress der.
    """
    fisk: dict[tuple[int, str], int] = {}
    uten: dict[str, int] = {}
    andel: dict[str, float] = {}
    maaneder: list[str] = []

    for dato_tekst, ramme in logg.les(
            "biomasse", f"{avg.fra_aar}-01-01", f"{avg.til_aar}-12-31",
            versjonsvalg=versjonsvalg):
        maaned = dato_tekst[:7]
        maaneder.append(maaned)
        rader = ramme.filter(pl.col("field").is_in([FISK_FELT, ANDEL_FELT]))
        for eid, felt, verdi in rader.select("entity_id", "field", "value").iter_rows():
            if felt == FISK_FELT:
                try:
                    n = int(verdi)
                except (TypeError, ValueError):
                    continue
                if eid == UTEN_PO:
                    uten[maaned] = n
                else:
                    fisk[(int(eid), maaned)] = n
            elif felt == ANDEL_FELT and eid == UTEN_PO:
                # Kildens eget avledede felt, ikke vår egen divisjon.
                # Det ligger i snapshotet nettopp for at en konsument
                # ikke skal regne nevneren ut på nytt og få et annet
                # tall — se KILDE-BIOMASSE punkt 6.
                try:
                    andel[maaned] = float(verdi)
                except (TypeError, ValueError):
                    continue

    return Biomasse(fisk=fisk, uten_po=uten, andel_uten_po=andel,
                    maaneder=tuple(maaneder))


# Hvordan et månedlig N_fisk settes sammen med et ukentlig lusetall.
# Se `nfisk_for_uke` for hvorfor det er to og ikke ett.
AGG_MAANED = "maaned"          # uka får sin egen måneds beholdning
AGG_VINDUSNITT = "vindusnitt"  # hele vinduet får snittet av månedene


# ---------------------------------------------------------------- dekning

def dekning(rader: list[dict]) -> None:
    print(seksjon("1. DEKNING PER ÅR — grunnlaget for avgrensningen"))
    print(f"{'år':>5} {'lok-uker':>9} {'aktive':>8} {'rapp.':>8} {'rapp/aktiv':>11}"
          f" {'m/PO':>7} {'PO-dekn.':>9} {'uker':>5}")
    per_aar = defaultdict(list)
    for r in rader:
        per_aar[r["aar"]].append(r)
    for aar in sorted(per_aar):
        rs = per_aar[aar]
        aktive = [r for r in rs if not r["brakklagt"]]
        rapp = [r for r in aktive if r["rapportert"]]
        med_po = [r for r in rapp if r["po"] is not None]
        uker = len({r["uke"] for r in rs})
        print(f"{aar:>5} {len(rs):>9} {len(aktive):>8} {len(rapp):>8}"
              f" {len(rapp)/max(len(aktive),1):>10.1%}"
              f" {len(med_po):>7} {len(med_po)/max(len(rapp),1):>8.1%} {uker:>5}")
    print("\n  rapp/aktiv = andel ikke-brakklagte lokaliteter som rapporterte lus.")
    print("  PO-dekn.   = andel av de rapporterende som har en PO-kode i dagens")
    print("               akvakulturregister. Resten er lokaliteter som er slettet")
    print("               fra registeret siden, eller som aldri hadde PO (landbaserte).")
    print()
    print("  MERK: PO-dekningen for 2018 og 2019 er 90,3 % og 91,0 %, ikke over 92 %")
    print("  som avgrensningen antok. Tallet passerer 92 % først i 2021. Nevneren er")
    print("  sjekket: andel av AKTIVE gir 90,1 %, andel av ALLE lok-uker gir 51,0 %,")
    print("  og andel innen uke 16-24 gir 89,8 %. Ingen av dem gir 92 % for 2018.")
    print("  Avgrensningen står — 90 % er langt over 78 % i 2012, og forskjellen på")
    print("  90 og 92 er små i forhold til det avgrensningen skal beskytte mot — men")
    print("  premisset var ikke helt riktig, og da skal det stå at det ikke var det.")


# ---------------------------------------------------------------- prediktorer

def hvilke_inngangsdata(rader: list[dict], bio: Biomasse,
                        pred: dict, avg: Avgrensning) -> None:
    print(seksjon("2. EKSPERTGRUPPENS TRE INNGANGSDATA — nå har vi alle tre"))
    n_lus = sum(1 for r in rader if r["lus"] is not None)
    n_temp = sum(1 for r in rader if r["temp"] is not None)
    n_fisk = len(bio.fisk)
    print(f"  antall lus     JA   — `voksne_hunnlus`, snitt voksne hunnlus per fisk")
    print(f"                        per lokalitet per uke. {n_lus} verdier "
          f"{avg.fra_aar}-{avg.til_aar}.")
    print(f"  sjøtemperatur  JA   — `sjotemperatur` fra CSV-eksporten av den SAMME")
    print(f"                        ukerapporten. Samme ukeakse, samme etterslep.")
    print(f"                        {n_temp} verdier.")
    print(f"  antall fisk    JA   — `beholdning_antall` (`BEHFISK_STK`) fra")
    print(f"                        Fiskeridirektoratets biomassestatistikk, per")
    print(f"                        PRODUKSJONSOMRÅDE per MÅNED. {n_fisk} PO-måneder")
    print(f"                        over {len(set(bio.maaneder))} måneder.")
    print()
    print("  Dette er endringen siden forrige kjøring. Da sto det NEI på det")
    print("  tredje leddet, og `stien_delvis` var et navn på et mellomledd.")
    print("  Nå kan formelen fra Stien mfl. 2005 skrives ut i sin helhet:")
    print()
    print("      klekte nauplier = N_fisk × N_hunnlus × 0,17 × (T + 4,28)²")
    print()
    print("  MEN LEDDENE HAR IKKE SAMME OPPLØSNING, og det er ikke en detalj.")
    print("  Lus og temperatur er per LOKALITET per UKE. N_fisk er per")
    print("  PRODUKSJONSOMRÅDE per MÅNED. Det som regnes ut er derfor")
    print()
    print("      nauplier_PO_uke = N_fisk_PO × middel_lok(lus × (T+4,28)²) × 0,17")
    print()
    print("  altså områdets samlede beholdning ganget med det gjennomsnittlige")
    print("  lusepresset per fisk der. Det er IKKE summen av anleggenes egne")
    print("  produkter. Forskjellen er målt i seksjon 11 og skal leses sammen")
    print("  med hvert eneste naupliitall i denne utskriften.")
    print()
    print("  Biomasse per LOKALITET publiseres ikke åpent — verken i ArcGIS-")
    print("  tjenestene, i produksjonsintensitetslaget eller i noen nedlastbar")
    print("  fil (docs/KILDE-BIOMASSE.md punkt 9). Skjevheten kan derfor ikke")
    print("  kodes bort. Den kan bare måles og oppgis.")
    print()
    print("  `kapasitet` (MTB i tonn) finnes per lokalitet i Akvakulturregisteret,")
    print("  men er et TAK og ikke en beholdning: en lokalitet med 3600 tonn MTB")
    print("  kan stå tom. Den brukes derfor IKKE som N_fisk. Den brukes i seksjon")
    print("  11 til det den duger til — å RANGERE anleggsstørrelse innen et PO.")


def dekning_tre_ledd(pred: dict, fasit: dict, avg: Avgrensning,
                     bio: Biomasse) -> None:
    """Hvor mange (po, aar)-celler har alle tre leddene?

    Skilt fra dekningstabellen i seksjon 1: den måler lokalitet-uker og
    rapporteringsgrad, denne måler CELLER i den tabellen analysen
    faktisk regner på. En celle uten N_fisk er ikke en celle med dårlig
    N_fisk — den finnes ikke i naupliitallet i det hele tatt, og et
    gjennomsnitt over «de cellene som var med» er et annet utvalg enn
    gjennomsnittet over lusecellene.
    """
    print(seksjon("2b. DEKNING AV DE TRE LEDDENE PER (PO, ÅR)"))
    print(f"{'år':>5} {'celler':>7} {'m/lus':>7} {'m/temp':>7} {'m/N_fisk':>9}"
          f" {'alle tre':>9} {'m/fasit':>8} {'alle tre + fasit':>17}")
    for aar in avg.aar:
        celler = [k for k in pred if k[1] == aar]
        if not celler:
            continue
        lus = [k for k in celler if pred[k]["snitt_uvektet"] is not None]
        tmp = [k for k in celler if pred[k]["temp_snitt"] is not None]
        fsk = [k for k in celler if pred[k]["n_fisk"] is not None]
        tre = [k for k in celler if pred[k]["nauplier"] is not None]
        fas = [k for k in celler if fasit.get(k, {}).get("kategori") in RANG]
        begge = [k for k in tre if k in fas]
        print(f"{aar:>5} {len(celler):>7} {len(lus):>7} {len(tmp):>7} {len(fsk):>9}"
              f" {len(tre):>9} {len(fas):>8} {len(begge):>17}")
    tre_alle = [k for k in pred if pred[k]["nauplier"] is not None]
    med_fasit = [k for k in tre_alle if fasit.get(k, {}).get("kategori") in RANG]
    print(f"\n  {len(tre_alle)} av {len(pred)} (po, år)-celler har alle tre leddene.")
    print(f"  {len(med_fasit)} av dem har også en kjent kategori fra ekspertgruppen.")
    print(f"  Det er de {len(med_fasit)} som bærer hvert rho-tall for FULL Stien-proxy.")

    mangler = sorted(k for k in pred if pred[k]["nauplier"] is None)
    if mangler:
        per_aar = defaultdict(list)
        for po, aar in mangler:
            per_aar[aar].append(po)
        print("\n  Celler UTEN naupliitall, og hvorfor:")
        for aar in sorted(per_aar):
            po_er = sorted(per_aar[aar])
            maaneder = sorted({m for k in pred if k[1] == aar
                               for m in pred[k]["maaneder_i_vindu"]})
            har = sorted({m for m in maaneder
                          if any((po, m) in bio.fisk for po in po_er)})
            savnet = [m for m in maaneder if m not in har]
            print(f"    {aar}: PO {po_er} — vinduet berører {maaneder}, "
                  f"biomasse mangler {savnet or '(ingen)'}")
        print("\n  Biomasse er skrevet til og med "
              f"{max(bio.maaneder) if bio.maaneder else '(ingen)'}; fila publiseres "
              f"den 20. hver måned\n  og kilden henter med fire måneders etterslep "
              "(docs/KILDE-BIOMASSE.md punkt 4).")


def aggregeringsvariantene(a: dict, b: dict, fasit: dict) -> None:
    """De to måtene å sette et månedlig N_fisk sammen med et ukentlig lusetall.

    Valget er reelt tvilsomt — se `nfisk_for_uke` — så begge kjøres og
    begge står her. Skiller de seg lite, er valget uten betydning og det
    er verdt å vite. Skiller de seg mye, er det et valg som må oppgis
    sammen med tallet.
    """
    print(seksjon("2c. AGGREGERING — de to variantene side om side"))
    print(f"  {AGG_MAANED:>12}: uka ganges med beholdningen ved slutten av sin egen måned")
    print(f"  {AGG_VINDUSNITT:>12}: hele vinduet ganges med snittet over månedene "
          f"vinduet berører")
    felles = [k for k in a if k in b
              and a[k]["nauplier"] is not None and b[k]["nauplier"] is not None]
    if not felles:
        print("\n  Ingen celle har naupliitall i begge variantene.")
        return
    # Et PO-år der HVER rapporterende lokalitet meldte null voksne hunnlus
    # gir nauplier = 0 i begge variantene. Det er en ekte måling og ikke
    # et hull — men en relativ forskjell har ingen mening der, og en
    # divisjon ville felt kjøringen. Cellene telles og utelates fra
    # prosentene; Spearman under bruker fortsatt alle.
    nuller = [k for k in felles if a[k]["nauplier"] == 0]
    med_rel = [k for k in felles if a[k]["nauplier"] != 0]
    rel = [(b[k]["nauplier"] - a[k]["nauplier"]) / a[k]["nauplier"] for k in med_rel]
    print(f"\n  {len(felles)} PO-år har naupliitall i begge.")
    if nuller:
        print(f"  {len(nuller)} av dem er nøyaktig 0 i begge (alle lokaliteter "
              f"meldte null voksne hunnlus)\n  og utelates fra prosentene under: "
              f"{', '.join(f'PO{po}/{aar}' for po, aar in sorted(nuller))}")
    if not rel:
        print("  Ingen celle har et naupliitall over null å regne relativ "
              "forskjell av.")
        return
    print(f"  Median relativ forskjell ({AGG_VINDUSNITT} mot {AGG_MAANED}): "
          f"{st.median(rel):+.2%}")
    print(f"  Spenn: {min(rel):+.2%} til {max(rel):+.2%}")
    ra = [a[k]["nauplier"] for k in felles]
    rb = [b[k]["nauplier"] for k in felles]
    print(f"  Spearman mellom de to variantene: {spearman(ra, rb):+.4f}")
    for navn, pr in [(AGG_MAANED, a), (AGG_VINDUSNITT, b)]:
        n = sum(1 for k in pr if pr[k]["nauplier"] is not None
                and fasit.get(k, {}).get("kategori") in RANG)
        print(f"  rho mot kategori, {navn:>12}: "
              f"{_rho(pr, fasit, 'nauplier'):+.3f} (n = {n})")
    verste = max(med_rel, key=lambda k: abs(
        (b[k]["nauplier"] - a[k]["nauplier"]) / a[k]["nauplier"]))
    print(f"  Største enkeltavvik: PO{verste[0]} {verste[1]}, "
          f"{(b[verste]['nauplier'] - a[verste]['nauplier']) / a[verste]['nauplier']:+.2%}")


def nfisk_for_uke(bio: Biomasse, po: int, maaneder_i_vindu: list[str],
                  maaned: str, aggregering: str) -> int | None:
    """N_fisk som skal gange denne ukas lusepress. `None` = ikke dekket.

    ## Hvorfor det er to måter, og hvorfor begge kjøres

    Lus og temperatur er UKENTLIGE, N_fisk er MÅNEDLIG og er dessuten
    beholdningen ved MÅNEDSLUTT. Vinduet uke 16-24 spenner grovt april
    til juni. Det finnes ikke ett åpenbart riktig svar på hvilket
    månedstall som hører til uke 19, og valget er derfor reelt tvilsomt
    i oppgavens forstand — begge kjøres, og begge står i loggen.

        AGG_MAANED       uka ganges med beholdningen ved slutten av
                         SIN EGEN måned. Nærmest i tid, og følger
                         vekstkurven gjennom vinduet: en PO har mer fisk
                         stående i juni enn i april, og formelen sier at
                         det gir flere nauplier.

        AGG_VINDUSNITT   hele vinduet ganges med SNITTET over månedene
                         vinduet berører. Ett tall per PO-år, som er
                         nivået fasiten ligger på, og ufølsomt for at
                         mandagen tilfeldigvis falt på den ene eller
                         andre siden av et månedsskifte.

    Ingen av dem er «beholdningen i uke 19». Den finnes ikke i noen åpen
    kilde (KILDE-BIOMASSE punkt 9), og en interpolasjon mellom to
    månedslutt ville vært et tall vi fant på. Det gjøres ikke.

    ## Hele vinduet må være dekket, ellers ingenting

    Mangler én av vinduets måneder for dette produksjonsområdet, faller
    HELE PO-året ut i stedet for å regnes på de månedene som finnes. Med
    AGG_VINDUSNITT ville et snitt over to av tre måneder vært et annet
    mål enn et snitt over tre, og med AGG_MAANED ville de dekkede ukene
    blitt stående alene og gjort vinduet kortere for noen PO-år enn for
    andre. Begge deler er den samme feilen: et tall som ser
    sammenlignbart ut og ikke er det.

    Det er ikke teoretisk. Biomasse er skrevet til og med 2026-04, så
    2026 har april og mangler mai og juni. Hele 2026 faller ut av
    naupliitallet, og det skal SES i dekningstabellen framfor å bli et
    tynnere tall ingen legger merke til.
    """
    if any((po, m) not in bio.fisk for m in maaneder_i_vindu):
        return None
    if aggregering == AGG_MAANED:
        return bio.fisk.get((po, maaned))
    return int(st.mean([bio.fisk[(po, m)] for m in maaneder_i_vindu]))


def per_po_aar(rader: list[dict], vindu: tuple[int, int],
               bio: Biomasse | None = None,
               aggregering: str = AGG_MAANED) -> dict:
    """(po, aar) -> prediktorer. Bare rapporterende lokaliteter med PO."""
    lav, hoy = vindu
    bøtte = defaultdict(lambda: defaultdict(list))   # (po,aar) -> uke -> [lus]
    t_bøtte = defaultdict(lambda: defaultdict(list))  # (po,aar) -> uke -> [temp]
    s_bøtte = defaultdict(lambda: defaultdict(list))  # (po,aar) -> uke -> [delvis]
    m_uke: dict[tuple[int, int], dict[int, str]] = defaultdict(dict)
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not (lav <= r["uke"] <= hoy):
            continue
        bøtte[(r["po"], r["aar"])][r["uke"]].append(r["lus"])
        # Uka -> måneden, tatt fra snapshotdatoen og ikke regnet ut. Se
        # les_uker(): den datoen er kildens egen påstand om hvilket
        # tidspunkt raden handler om.
        m_uke[(r["po"], r["aar"])][r["uke"]] = r["maaned"]

        # Temperaturen aggregeres over de samme lokalitet-ukene som
        # lusetallet, ikke over alle lokaliteter som målte temperatur.
        # Ellers ville de to prediktorene hvilt på ulike utvalg, og en
        # forskjell mellom dem kunne vært utvalget og ikke variabelen.
        if r["temp"] is not None:
            t_bøtte[(r["po"], r["aar"])][r["uke"]].append(r["temp"])
            # DELVIS Stien-proxy, regnet PER LOKALITET-UKE fordi det er
            # der formelen bor. Å gange et PO-snitt av lus med et PO-snitt
            # av temperatur ville vært en annen størrelse: E[x]·E[y] er
            # ikke E[x·y] med mindre de er ukorrelerte, og her er de det
            # nettopp ikke.
            s_bøtte[(r["po"], r["aar"])][r["uke"]].append(
                r["lus"] * (r["temp"] + STIEN_T0) ** 2)

    ut = {}
    for nøkkel, per_uke in bøtte.items():
        alle = [x for v in per_uke.values() for x in v]
        if not alle:
            continue
        ukesnitt = [st.mean(v) for v in per_uke.values() if v]
        t_uker = t_bøtte.get(nøkkel, {})
        s_uker = s_bøtte.get(nøkkel, {})
        t_alle = [x for v in t_uker.values() for x in v]
        ut[nøkkel] = {
            # Uvektet på samme måte som lusetallet: snitt av ukesnitt.
            "temp_snitt": (st.mean([st.mean(v) for v in t_uker.values() if v])
                           if t_uker else None),
            "stien_delvis": (st.mean([st.mean(v) for v in s_uker.values() if v])
                             if s_uker else None),
            "n_temp": len(t_alle),
            "temp_dekning": len(t_alle) / len(alle) if alle else 0.0,
            # Uvektet: hver uke teller likt, uansett hvor mange lokaliteter
            # som rapporterte den uka. Vektet: hver lokalitet-uke teller likt,
            # så uker med mange rapporterende drar mer.
            "snitt_uvektet": st.mean(ukesnitt),
            "snitt_vektet": st.mean(alle),
            "maks": max(alle),
            "p95": persentil(alle, 0.95),
            "median": st.median(alle),
            "n_lokuker": len(alle),
            "n_lok": len({0 for _ in alle}) if False else None,
            "n_uker": len(per_uke),
            # Det tredje leddet. `None` inntil biomasse er koblet på;
            # `None` også der vinduet ikke er fullt dekket.
            "n_fisk": None,
            "nauplier": None,
            "nauplier_per_lok": None,
            "maaneder_i_vindu": sorted(set(m_uke[nøkkel].values())),
        }
    # antall unike rapporterende lokaliteter, som kontrollvariabel
    lok = defaultdict(set)
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not (lav <= r["uke"] <= hoy):
            continue
        lok[(r["po"], r["aar"])].add(r["lok"])
    for k in ut:
        ut[k]["n_lok"] = len(lok[k])

    if bio is not None:
        _legg_paa_nfisk(ut, s_bøtte, m_uke, bio, aggregering)
    return ut


def _legg_paa_nfisk(ut: dict, s_bøtte: dict, m_uke: dict,
                    bio: Biomasse, aggregering: str) -> None:
    """Det tredje leddet, ganget på DER FORMELEN BOR — per uke.

    Stien mfl. 2005 gjelder per anlegg per døgn:

        nauplier = N_fisk × N_hunnlus × 0,17 × (T + 4,28)²

    Vi har `N_hunnlus` og `T` per LOKALITET og `N_fisk` bare per
    PRODUKSJONSOMRÅDE. Det som regnes ut her er derfor

        nauplier_PO_uke = N_fisk_PO × middel_lok(lus × (T + 4,28)²) × 0,17

    altså PO-ets samlede fiskebeholdning ganget med det GJENNOMSNITTLIGE
    lusepresset per fisk i området. Det er ikke det samme som summen av
    anleggenes egne produkter — se seksjon 2 i utskriften. Forskjellen
    er kovariansen mellom anleggsstørrelse og lusenivå innen området,
    og den er MÅLT der, ikke antatt bort her.

    Merk hva som IKKE gjøres: `stien_delvis` er allerede snittet av
    produktet per lokalitet-uke, ikke produktet av to snitt. Den delen
    av formelen bor fortsatt på lokalitetsnivå, og bare N_fisk-leddet er
    løftet til PO. Skjevheten er dermed avgrenset til nøyaktig ett ledd.
    """
    for nøkkel, p in ut.items():
        po, _aar = nøkkel
        uker = s_bøtte.get(nøkkel, {})
        maaneder = p["maaneder_i_vindu"]
        if not uker or not maaneder:
            continue

        per_uke_nauplier, per_uke_fisk = [], []
        for uke, verdier in uker.items():
            if not verdier:
                continue
            n_fisk = nfisk_for_uke(bio, po, maaneder, m_uke[nøkkel][uke],
                                   aggregering)
            if n_fisk is None:
                per_uke_nauplier = []
                break
            per_uke_fisk.append(n_fisk)
            per_uke_nauplier.append(n_fisk * st.mean(verdier) * STIEN_K)

        if not per_uke_nauplier:
            continue
        # Uvektet snitt over uker, samme vekting som `snitt_uvektet` og
        # `stien_delvis`. Tallet er da en DØGNRATE i vinduet — «så mange
        # nauplier klekkes per døgn i en typisk uke i utvandringen» — og
        # ikke en sum over vinduet. En sum ville vært like forsvarlig,
        # men ikke sammenlignbar med de andre målene i tabellen.
        p["n_fisk"] = int(st.mean(per_uke_fisk))
        p["nauplier"] = st.mean(per_uke_nauplier)
        p["nauplier_per_lok"] = p["nauplier"] / p["n_lok"] if p["n_lok"] else None


def _kort(v: float, fortegn: bool = False) -> str:
    """Ett tall, lesbart, uansett om det er 0,08 lus eller 1,4 billioner nauplier.

    Tabellene i seksjon 8b-8g viser samme kolonne for seks prediktorer
    som spenner fjorten størrelsesordener. En fast `.3f` gjorde
    naupliitallene til tjue siffer og skjøv resten av raden ut av skjermen.
    """
    tegn = "+" if fortegn else ""
    a = abs(v)
    if a >= 1e12:
        return f"{v / 1e12:{tegn}.3f} bill."
    if a >= 1e9:
        return f"{v / 1e9:{tegn}.3f} mrd."
    if a >= 1e6:
        return f"{v / 1e6:{tegn}.3f} mill."
    if a >= 1000:
        return f"{v:{tegn},.0f}".replace(",", " ")
    return f"{v:{tegn}.3f}"


def persentil(xs: list[float], p: float) -> float:
    """Lineær interpolasjon. Ingen numpy i dette repoet."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    i = p * (len(s) - 1)
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


# ---------------------------------------------------------------- utskrift

def seksjon(t: str) -> str:
    return f"\n{'=' * 74}\n {t}\n{'=' * 74}"


def tabell_prediktorer(pred: dict, fasit: dict, vindu: tuple[int, int]) -> None:
    print(seksjon(f"3. PREDIKTORER PER PO PER ÅR — uke {vindu[0]}-{vindu[1]}"))
    print(f"{'PO':>3} {'år':>5} {'kategori':>9} {'snitt_uv':>9} {'p95':>6}"
          f" {'temp':>6} {'t-dekn':>7} {'delvis':>8} {'N_fisk':>14}"
          f" {'nauplier/døgn':>16} {'per lok':>14} {'n_lok':>6} {'n_uker':>7}")
    for (po, aar) in sorted(pred):
        p = pred[(po, aar)]
        kat = fasit.get((po, aar), {}).get("kategori", "—")
        t_ = f"{p['temp_snitt']:.2f}" if p["temp_snitt"] is not None else "—"
        d = f"{p['stien_delvis']:.2f}" if p["stien_delvis"] is not None else "—"
        n = f"{p['n_fisk']:,}".replace(",", " ") if p["n_fisk"] is not None else "—"
        nau = f"{p['nauplier']:,.0f}".replace(",", " ") if p["nauplier"] is not None else "—"
        pl_ = (f"{p['nauplier_per_lok']:,.0f}".replace(",", " ")
               if p["nauplier_per_lok"] is not None else "—")
        print(f"{po:>3} {aar:>5} {kat:>9} {p['snitt_uvektet']:>9.3f}"
              f" {p['p95']:>6.2f} {t_:>6} {p['temp_dekning']:>6.1%}"
              f" {d:>8} {n:>14} {nau:>16} {pl_:>14}"
              f" {p['n_lok']:>6} {p['n_uker']:>7}")
    print("\n  temp     = snitt sjøtemperatur i vinduet, uvektet over uker.")
    print("  delvis   = DELVIS Stien-proxy: lus × (T + 4,28)², uten N_fisk.")
    print("  N_fisk   = beholdning ved månedslutt, hele produksjonsområdet.")
    print("  nauplier = FULL Stien-proxy: N_fisk × delvis × 0,17. Antall klekte")
    print("             nauplier PER DØGN i en typisk uke i vinduet — ikke en sum")
    print("             over vinduet, og ikke korrigert for skjevheten i seksjon 11.")
    print("  per lok  = samme, delt på antall rapporterende lokaliteter.")
    print("  «—» i N_fisk-kolonnene betyr at vinduet ikke er fullt dekket av")
    print("  biomassefila. Se seksjon 2b.")


def fordeling_per_kategori(pred: dict, fasit: dict, vindu: tuple[int, int],
                           bare_verifisert: bool = False) -> None:
    tittel = "4. FORDELING PER KATEGORI — overlapper de?"
    if bare_verifisert:
        tittel = "4b. SAMME, UTEN 2024 (som er utledet, ikke lest)"
    print(seksjon(tittel + f"  [uke {vindu[0]}-{vindu[1]}]"))
    for navn in ["snitt_uvektet", "snitt_vektet", "p95", "maks", "n_lok"]:
        grupper = defaultdict(list)
        for (po, aar), p in pred.items():
            f = fasit.get((po, aar))
            if not f or f["kategori"] == "ukjent":
                continue
            if bare_verifisert and f["sikkerhet"] != "verifisert":
                continue
            grupper[f["kategori"]].append(p[navn])
        print(f"\n  {navn}")
        print(f"    {'kategori':>9} {'n':>3} {'min':>7} {'p25':>7} {'median':>7}"
              f" {'p75':>7} {'maks':>7}")
        for kat in KATEGORIER:
            v = grupper.get(kat, [])
            if not v:
                continue
            print(f"    {kat:>9} {len(v):>3} {min(v):>7.3f} {persentil(v,0.25):>7.3f}"
                  f" {st.median(v):>7.3f} {persentil(v,0.75):>7.3f} {max(v):>7.3f}")
        overlapp_dom(grupper)


def overlapp_dom(grupper: dict) -> None:
    """Overlapper lav og hoy i det hele tatt? Og er det ETT tall som skiller?"""
    lav, hoy = grupper.get("lav", []), grupper.get("hoy", [])
    if not lav or not hoy:
        return
    if max(lav) < min(hoy):
        print(f"    -> lav og hoy er ADSKILT (lav maks {max(lav):.3f} < "
              f"hoy min {min(hoy):.3f})")
    else:
        # hvor mange lav-verdier ligger over den laveste hoy-verdien
        n = sum(1 for x in lav if x >= min(hoy))
        print(f"    -> OVERLAPP: {n} av {len(lav)} lav-år ligger over laveste "
              f"hoy-år ({min(hoy):.3f}); lav maks {max(lav):.3f}")


def rangkorrelasjon(pred: dict, fasit: dict) -> None:
    """Spearman uten scipy: rangér begge, Pearson på rangene.

    Dette er en beskrivelse av samvariasjon, ikke en modell og ikke en
    test. Ingen p-verdi — 43 observasjoner over 13 områder er ikke
    uavhengige, og en p-verdi ville lovet mer enn tallet holder.
    """
    print(seksjon("5. SAMVARIASJON MED KATEGORIRANG (Spearman, beskrivende)"))
    for navn in ["snitt_uvektet", "snitt_vektet", "median", "p95", "maks",
                 "n_lok", "temp_snitt", "stien_delvis",
                 "n_fisk", "nauplier", "nauplier_per_lok"]:
        par = [(p[navn], RANG[fasit[(po, aar)]["kategori"]])
               for (po, aar), p in pred.items()
               if fasit.get((po, aar), {}).get("kategori") in RANG
               and p.get(navn) is not None]
        if len(par) < 5:
            continue
        r = spearman([a for a, _ in par], [b for _, b in par])
        print(f"  {navn:>14}  rho = {r:+.3f}   (n = {len(par)})")


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(ranger(xs), ranger(ys))


def ranger(xs: list[float]) -> list[float]:
    par = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(par):
        j = i
        while j + 1 < len(par) and xs[par[j + 1]] == xs[par[i]]:
            j += 1
        snitt = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[par[k]] = snitt
        i = j + 1
    return r


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = st.mean(xs), st.mean(ys)
    tel = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    nev = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return tel / nev if nev else 0.0


def foelsomhet(p16: dict, p14: dict, fasit: dict) -> None:
    print(seksjon("6. FØLSOMHET FOR VINDUET — uke 16-24 mot 14-26"))
    print(f"{'PO':>3} {'år':>5} {'16-24':>8} {'14-26':>8} {'endring':>9}")
    diffs = []
    for k in sorted(p16):
        if k not in p14:
            continue
        a, b = p16[k]["snitt_uvektet"], p14[k]["snitt_uvektet"]
        diffs.append((b - a) / a if a else 0.0)
        if abs((b - a) / a if a else 0) > 0.15:
            print(f"{k[0]:>3} {k[1]:>5} {a:>8.3f} {b:>8.3f} {(b-a)/a:>+8.1%}")
    print(f"\n  {len(diffs)} PO-år sammenlignet. Median relativ endring: "
          f"{st.median(diffs):+.1%}. Rader over vises bare når endringen er "
          f"større enn 15 %.")
    r16 = [(k, p16[k]["snitt_uvektet"]) for k in sorted(p16) if k in p14]
    r14 = [(k, p14[k]["snitt_uvektet"]) for k in sorted(p16) if k in p14]
    print(f"  Spearman mellom de to vinduene: "
          f"{spearman([v for _, v in r16], [v for _, v in r14]):+.3f}")
    for navn, pr in [("16-24", p16), ("14-26", p14)]:
        par = [(p["snitt_uvektet"], RANG[fasit[k]["kategori"]])
               for k, p in pr.items() if fasit.get(k, {}).get("kategori") in RANG]
        print(f"  rho mot kategori, vindu {navn}: "
              f"{spearman([a for a,_ in par],[b for _,b in par]):+.3f} (n={len(par)})")


def spesifikke_sporsmaal(pred: dict, fasit: dict, avg: Avgrensning) -> None:
    print(seksjon("7. DE FIRE SPESIFIKKE SPØRSMÅLENE"))

    print("\n  a) PO3 og PO4 har aldri vært lav. Skiller de seg i tallene?")
    aldri_lav = {3, 4}
    a = [p["snitt_uvektet"] for (po, aar), p in pred.items() if po in aldri_lav]
    b = [p["snitt_uvektet"] for (po, aar), p in pred.items() if po not in aldri_lav]
    print(f"     PO3+PO4  n={len(a):>3}  median {st.median(a):.3f}  "
          f"spenn {min(a):.3f}-{max(a):.3f}")
    print(f"     øvrige   n={len(b):>3}  median {st.median(b):.3f}  "
          f"spenn {min(b):.3f}-{max(b):.3f}")
    print(f"     Andel av øvrige som ligger over PO3+PO4s median: "
          f"{sum(1 for x in b if x > st.median(a))/len(b):.1%}")

    print("\n  b) PO2 gikk hoy -> lav -> moderat i 2020-2022. Synlig i lusetallene?")
    print(f"     {'år':>5} {'kategori':>9} {'snitt_uv':>9} {'snitt_v':>8} {'p95':>6} {'n_lok':>6}")
    for aar in avg.aar:
        p = pred.get((2, aar))
        if not p:
            continue
        kat = fasit.get((2, aar), {}).get("kategori", "—")
        print(f"     {aar:>5} {kat:>9} {p['snitt_uvektet']:>9.3f} "
              f"{p['snitt_vektet']:>8.3f} {p['p95']:>6.2f} {p['n_lok']:>6}")

    print("\n  c) Toårige mønstre (sonestyrt, toårig produksjon)?")
    print("     Korrelasjon mellom årets og fjorårets snitt (lag 1), og mot")
    print("     året før det (lag 2), per PO. Et toårig mønster gir negativ")
    print("     lag-1 og positiv lag-2.")
    print(f"     {'PO':>3} {'n_år':>5} {'lag1':>7} {'lag2':>7}")
    lag1_alle, lag2_alle = [], []
    for po in range(1, 14):
        serie = [(aar, pred[(po, aar)]["snitt_uvektet"])
                 for aar in avg.aar if (po, aar) in pred]
        if len(serie) < 5:
            continue
        v = [x for _, x in serie]
        l1 = pearson(v[:-1], v[1:]) if len(v) > 2 else float("nan")
        l2 = pearson(v[:-2], v[2:]) if len(v) > 3 else float("nan")
        lag1_alle.append(l1)
        lag2_alle.append(l2)
        print(f"     {po:>3} {len(v):>5} {l1:>+7.2f} {l2:>+7.2f}")
    print(f"     median lag1 {st.median(lag1_alle):+.2f}, "
          f"lag2 {st.median(lag2_alle):+.2f}")


def baseline(fasit: dict) -> None:
    print(seksjon("8. BASELINE — regelen enhver modell må slå"))
    par = []
    for (po, aar), f in fasit.items():
        forrige = fasit.get((po, aar - 1))
        if not forrige or f["kategori"] == "ukjent" or forrige["kategori"] == "ukjent":
            continue
        par.append((po, aar, forrige["kategori"], f["kategori"]))
    par.sort()
    n = len(par)
    lik = sum(1 for *_, a, b in par if a == b)
    lik_eller_opp = sum(1 for *_, a, b in par if RANG[b] - RANG[a] in (0, 1))
    print(f"  Sammenlignbare år-par (begge kjent): {n}")
    print(f"  «samme som i fjor»            : {lik:>3}/{n} = {lik/n:.1%}")
    print(f"  «samme som i fjor, eller ett hakk opp»: {lik_eller_opp:>3}/{n} = "
          f"{lik_eller_opp/n:.1%}")
    alltid = defaultdict(int)
    for *_, b in par:
        alltid[b] += 1
    for kat in KATEGORIER:
        print(f"  «alltid {kat}»{'':>{max(0,20-len(kat))}}: {alltid[kat]:>3}/{n} = "
              f"{alltid[kat]/n:.1%}")
    print("\n  Endringene som faktisk skjedde:")
    for po, aar, a, b in par:
        if a != b:
            print(f"    PO{po:<3} {aar-1}->{aar}  {a} -> {b}")


def retning_ved_skifte(pred: dict, fasit: dict,
                       felt: str = "snitt_uvektet", merkelapp: str = "lusetallet",
                       nr: str = "8b") -> tuple[int, int]:
    """De 11 gangene kategorien FAKTISK endret seg — beveget prediktoren seg
    samme vei? Dette er ikke en modell; det er å telle fortegn."""
    print(seksjon(f"{nr}. BEVEGET {merkelapp.upper()} SEG SAMME VEI SOM KATEGORIEN?"))
    print(f"{'PO':>4} {'skifte':>12} {'retning':>8} {felt[:20]:>21}"
          f" {'endring':>10} {'p95':>17} {'enig':>6}")
    enige = 0
    n = 0
    for (po, aar), f in sorted(fasit.items()):
        forrige = fasit.get((po, aar - 1))
        if not forrige or "ukjent" in (f["kategori"], forrige["kategori"]):
            continue
        if f["kategori"] == forrige["kategori"]:
            continue
        a, b = pred.get((po, aar - 1)), pred.get((po, aar))
        if not a or not b or a.get(felt) is None or b.get(felt) is None:
            continue
        n += 1
        opp = RANG[f["kategori"]] > RANG[forrige["kategori"]]
        d = b[felt] - a[felt]
        enig = (d > 0) == opp
        enige += enig
        print(f"{po:>4} {forrige['kategori'][:3]+'->'+f['kategori'][:3]:>12}"
              f" {'opp' if opp else 'ned':>8}"
              f" {_kort(a[felt]):>10}->{_kort(b[felt]):<10}"
              f" {_kort(d, fortegn=True):>10} {a['p95']:>7.2f}->{b['p95']:<7.2f}"
              f" {'ja' if enig else 'NEI':>6}")
    print(f"\n  {enige} av {n} skifter har {merkelapp} på riktig side. "
          f"Myntkast gir {n/2:.1f}.")
    print("  Dette er ikke en test — få skifter, avhengige av hverandre innen PO.")
    print("  Det er tellingen av fortegn, og den står som den er.")
    return enige, n


def bredde_per_po(rader: list[dict], bredde: dict[str, float],
                  avg: Avgrensning) -> dict:
    """(po, aar) -> snittbreddegrad for lokalitetene som faktisk bidro.

    Ett sted, brukt av både kontrollen og plottet. To utregninger som kan
    svare ulikt er mønsteret repoet har betalt for fire ganger — og
    `bredde` kommer inn av samme grunn: kartet slås opp én gang, i main().
    """
    lok_per = defaultdict(set)
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not avg.i_vindu(r["uke"]):
            continue
        lok_per[(r["po"], r["aar"])].add(r["lok"])
    ut = {}
    for k, lokker in lok_per.items():
        b = [bredde[l] for l in lokker if l in bredde]
        if b:
            ut[k] = st.mean(b)
    return ut


def variansforhold(pred: dict, felt: str) -> tuple[float, float, float] | None:
    """Er variasjonen MELLOM produksjonsområder større enn den INNEN ett?

    Returnerer (std mellom PO-snittene, median std innen ett PO over år,
    forholdet). Stort forhold = variabelen er først og fremst HVOR
    området ligger, og bare i liten grad hvilket år det er.

    ## Std mot std, og hvorfor det står som en egen funksjon

    Første utkast av temperaturkontrollen sammenlignet standardavviket
    MELLOM produksjonsområder med SPENNET innen ett — og et spenn er
    alltid større enn et standardavvik for de samme tallene. Det ga 1,80
    mot 1,63, altså «omtrent like store», og konklusjonen ble at
    temperaturen bar årsvariasjon. Med std i begge ender: 1,80 mot 0,46,
    forhold 3,9 — motsatt konklusjon.

    Feilen kan ikke gjentas for N_fisk nå, fordi begge går gjennom denne
    ene funksjonen. Det er hele grunnen til at den ikke er skrevet to
    ganger med hver sin variabel.
    """
    serier = {}
    for po in range(1, 14):
        v = [pred[k][felt] for k in pred if k[0] == po and pred[k].get(felt) is not None]
        if v:
            serier[po] = v
    mellom = [st.mean(v) for v in serier.values()]
    innen = [st.pstdev(v) for v in serier.values() if len(v) > 1]
    if not mellom or not innen or len(mellom) < 2:
        return None
    s_mellom, s_innen = st.pstdev(mellom), st.median(innen)
    return s_mellom, s_innen, (s_mellom / s_innen if s_innen else float("inf"))


def variansforhold_relativt(pred: dict, felt: str) -> float | None:
    """Samme spørsmål, men på RELATIV skala.

    Finnes fordi temperatur og N_fisk ikke er samme slags tall.
    Temperatur er en intervallskala med et lite spenn (8-16 grader), og
    et standardavvik i grader er direkte sammenlignbart mellom to
    produksjonsområder. N_fisk er en TELLING som spenner to
    størrelsesordener mellom det minste og det største området, og da
    er et absolutt standardavvik nesten en funksjon av områdets
    størrelse alene: et stort PO har stort std i fisk fordi det har mye
    fisk, ikke fordi det svinger mer.

    Derfor divideres hver PO-serie på sitt eget snitt før spredningen
    måles (variasjonskoeffisient). Det ABSOLUTTE forholdet rapporteres
    ved siden av, fordi det er det som er sammenlignbart med
    temperaturens 3,9 — og fordi å bytte mål midt i en kontroll og bare
    vise det nye er nettopp hvordan man konkluderer motsatt uten at noen
    ser det.
    """
    serier = {}
    for po in range(1, 14):
        v = [pred[k][felt] for k in pred if k[0] == po and pred[k].get(felt) is not None]
        if len(v) > 1 and st.mean(v):
            serier[po] = v
    if len(serier) < 2:
        return None
    mellom = [st.mean(v) for v in serier.values()]
    if not st.mean(mellom):
        return None
    cv_mellom = st.pstdev(mellom) / st.mean(mellom)
    cv_innen = st.median([st.pstdev(v) / st.mean(v) for v in serier.values()])
    return cv_mellom / cv_innen if cv_innen else float("inf")


def rho_innen_po(pred: dict, fasit: dict, hent) -> list[float]:
    """Spearman mot kategorirang INNEN hvert PO for seg, ett tall per PO.

    Geografien er konstant innen et produksjonsområde. Blir rho borte
    her, var det geografi og ikke variabelen som bar samvariasjonen.

    Minst tre år OG minst to ulike kategorier kreves — ellers er rangen
    konstant og korrelasjonen udefinert (eller 0 per konstruksjon).
    """
    ut = []
    for po in range(1, 14):
        par = [(hent(k, pred[k]), RANG[fasit[k]["kategori"]])
               for k in sorted(pred)
               if k[0] == po and fasit.get(k, {}).get("kategori") in RANG
               and hent(k, pred[k]) is not None]
        if len(par) < 3 or len({b for _, b in par}) < 2:
            continue
        ut.append(spearman([a for a, _ in par], [b for _, b in par]))
    return ut


def prediktorene(bredde_po: dict) -> list[tuple[str, object]]:
    """Prediktorene og kontrollvariablene, i ÉN liste.

    Tabellene i seksjon 10 og 11 skal vise nøyaktig samme variabler i
    samme rekkefølge. Sto lista tre steder, ville en variabel som ble
    lagt til ett sted manglet i de to andre — og en leser som sammenligner
    «rho totalt» med «rho innen PO» ville sammenlignet to ulike utvalg
    variabler uten å se det.
    """
    return [
        ("lusetall (snitt_uv)", lambda k, p: p["snitt_uvektet"]),
        ("temperatur", lambda k, p: p["temp_snitt"]),
        ("DELVIS Stien-proxy", lambda k, p: p["stien_delvis"]),
        ("N_fisk (PO-beholdning)", lambda k, p: p["n_fisk"]),
        ("FULL Stien-proxy", lambda k, p: p["nauplier"]),
        ("FULL Stien per lokalitet", lambda k, p: p["nauplier_per_lok"]),
        ("breddegrad", lambda k, p: bredde_po.get(k)),
        ("PO-nummer (ren geografi)", lambda k, p: float(k[0])),
        ("n_lok (kontrollvariabel)", lambda k, p: float(p["n_lok"])),
    ]


def geografikontrollen(rader: list[dict], pred: dict, fasit: dict,
                       bredde_po: dict, bredde: dict[str, float],
                       avg: Avgrensning) -> None:
    """DEN VIKTIGE KONTROLLEN.

    Temperaturen faller monotont med breddegrad — det er målt over hele
    serien: augustmedianen går fra 16,6 grader ved 58-59°N til 10,1 ved
    70-71°N. Produksjonsområdene er også geografiske, nummerert sørfra.
    Så en variabel som «forklarer» kategorien kan gjøre det utelukkende
    fordi den er en omskrivning av HVOR området ligger.

    Prøven: hvis rho(temperatur, kategori) og rho(breddegrad, kategori)
    er like store, og temperatur og breddegrad henger tett sammen, så
    forklarer temperaturen ingenting utover geografi. Da er den ikke en
    tredje prediktor — den er PO-identitet med en annen enhet.

    N_fisk går gjennom NØYAKTIG samme batteri, og det er poenget med
    denne kjøringen: det er det eneste leddet i Stien-formelen som i
    prinsippet ikke er geografi. Antall fisk i et område er et
    driftsvalg og en konsesjonsgrense, ikke en breddegrad. Om det
    likevel oppfører seg som geografi i tallene, er det en måling og
    ikke en antakelse.
    """
    print(seksjon("10. GEOGRAFIKONTROLLEN — er prediktorene bare breddegrad?"))

    print("\n  a) Samvariasjon med kategorirang, side om side:")
    for navn, hent in prediktorene(bredde_po):
        par = [(hent(k, p), RANG[fasit[k]["kategori"]])
               for k, p in pred.items()
               if fasit.get(k, {}).get("kategori") in RANG and hent(k, p) is not None]
        if len(par) < 5:
            print(f"       {navn:>26}  {'—':>12}   (n = {len(par)}, for få)")
            continue
        r = spearman([a for a, _ in par], [b for _, b in par])
        print(f"       {navn:>26}  rho = {r:+.3f}   (n = {len(par)})")

    print("\n  b) Henger prediktorene og breddegrad sammen?")
    for navn, felt in [("temperatur", "temp_snitt"), ("N_fisk", "n_fisk"),
                       ("FULL Stien-proxy", "nauplier")]:
        felles = [k for k in pred if k in bredde_po and pred[k].get(felt) is not None]
        if len(felles) < 5:
            continue
        v = [pred[k][felt] for k in felles]
        b = [bredde_po[k] for k in felles]
        print(f"       {navn:>20}  Spearman(x, breddegrad) = {spearman(v, b):+.3f}"
              f"   PO-nummer: {spearman(v, [float(k[0]) for k in felles]):+.3f}"
              f"   (n = {len(felles)})")

    lok_temp = defaultdict(list)
    for r in rader:
        if r["temp"] is None or r["lok"] not in bredde:
            continue
        if not avg.i_vindu(r["uke"]):
            continue
        lok_temp[r["lok"]].append(r["temp"])
    if lok_temp:
        lt = [st.mean(v) for v in lok_temp.values()]
        lb = [bredde[l] for l in lok_temp]
        print(f"       {'temperatur':>20}  lokalitetsnivå: "
              f"Spearman(temp, breddegrad) = {spearman(lt, lb):+.3f}"
              f"  (n = {len(lt)} lokaliteter)")
    print("       N_fisk har ingen lokalitetsrad å måle — den finnes bare per PO.")

    print("\n  c) Per PO — hvor mye er bare hvor området ligger?")
    print(f"       {'PO':>3} {'breddegrad':>11} {'temp snitt':>11}"
          f" {'N_fisk snitt':>15} {'N_fisk spenn':>33} {'n år':>5}")
    for po in range(1, 14):
        aar_t = [k for k in pred if k[0] == po and pred[k]["temp_snitt"] is not None]
        aar_f = [k for k in pred if k[0] == po and pred[k]["n_fisk"] is not None]
        if not aar_t:
            continue
        t = [pred[k]["temp_snitt"] for k in aar_t]
        b = [bredde_po[k] for k in aar_t if k in bredde_po]
        f = [pred[k]["n_fisk"] for k in aar_f]
        fs = (f"{min(f):>15,}-{max(f):<15,}".replace(",", " ") if f else f"{'—':>31}")
        print(f"       {po:>3} {st.mean(b) if b else float('nan'):>11.2f}"
              f" {st.mean(t):>11.2f}"
              f" {(f'{int(st.mean(f)):,}'.replace(',', ' ') if f else '—'):>15}"
              f" {fs} {len(aar_t):>5}")

    print("\n       Spennet innen ett PO er variasjonen MELLOM ÅR på samme sted.")
    print("       Er det lite mot forskjellen mellom PO-er, bærer variabelen")
    print("       nesten bare geografi og nesten ingen årsvariasjon.")

    print("\n     Variansdekomponering — std MELLOM PO mot median std INNEN ett PO:")
    print(f"     {'variabel':>26} {'std mellom':>14} {'median std innen':>18}"
          f" {'forhold':>9} {'forhold (CV)':>13}")
    for navn, felt in [("temperatur (°C)", "temp_snitt"),
                       ("lusetall (snitt_uv)", "snitt_uvektet"),
                       ("N_fisk (antall)", "n_fisk"),
                       ("FULL Stien-proxy", "nauplier"),
                       ("FULL Stien per lok.", "nauplier_per_lok")]:
        v = variansforhold(pred, felt)
        if v is None:
            continue
        mellom, innen, forhold = v
        rel = variansforhold_relativt(pred, felt)
        print(f"     {navn:>26} {mellom:>14.4g} {innen:>18.4g} {forhold:>8.1f}x"
              f" {(f'{rel:.1f}x' if rel is not None else '—'):>13}")
    print("\n     Kolonnen «forhold» er absolutt og er den som kan sammenlignes")
    print("     med temperaturens tall. «forhold (CV)» deler hver PO-serie på")
    print("     sitt eget snitt først, og er den rimelige for en TELLING som")
    print("     spenner to størrelsesordener mellom minste og største område.")

    print("\n  d) INNEN ETT PO — forklarer prediktorene årsvariasjonen?")
    print("     Geografien er konstant innen et PO. Blir rho borte her, var")
    print("     det geografi og ikke variabelen som bar samvariasjonen.")
    print(f"     {'prediktor':>26} {'median rho':>11} {'PO-er':>6}  fordeling per PO")
    for navn, hent in prediktorene(bredde_po):
        if navn.startswith(("breddegrad", "PO-nummer")):
            continue   # konstant innen et PO — rho er udefinert per konstruksjon
        rhoer = rho_innen_po(pred, fasit, hent)
        if not rhoer:
            print(f"     {navn:>26} {'—':>11} {0:>6}  (ingen PO med nok variasjon)")
            continue
        fordeling = " ".join(f"{r:+.2f}" for r in sorted(rhoer))
        print(f"     {navn:>26} {st.median(rhoer):>+11.3f} {len(rhoer):>6}  {fordeling}")



def kapasitet_kart(akva: pl.DataFrame) -> dict[str, float]:
    """localityNo -> kapasitet (MTB i tonn), fra SAMME akvakultursnapshot.

    Samme snapshot som `po_kart()` og `bredde_kart()` — det er hele
    grunnen til at `akvakultur_naa()` finnes. Tre oppslag av «nyeste
    dato» kunne gitt tre ulike registre hvis den ukentlige jobben kjørte
    imellom.

    MTB er et TAK, ikke en beholdning. Den brukes her utelukkende som en
    RANGERING av anleggsstørrelse innen et produksjonsområde, og aldri
    som et antall fisk.
    """
    par = akva.filter(pl.col("field") == "kapasitet").select("entity_id", "value")
    ut = {}
    for e, v in par.iter_rows():
        try:
            k = float(v)
        except (TypeError, ValueError):
            continue
        if k > 0:
            ut[e] = k
    return ut


def skjevhetens_fortegn(rader: list[dict], kapasitet: dict[str, float],
                        avg: Avgrensning) -> None:
    """FORTEGNET på skjevheten i PO-produktet. Ikke størrelsen.

    Stien er per anlegg. Vi har N_fisk bare per produksjonsområde:

        Σᵢ (N_fiskᵢ × lusᵢ)   mot   N_fisk_PO × middel(lus)

    De to er like NØYAKTIG når anleggsstørrelse og lusenivå er
    ukorrelerte innen området. Algebraisk:

        Σᵢ Nᵢ·xᵢ = N_PO · middel(x) + n · kovarians(N, x)

    Er kovariansen positiv — store anlegg har systematisk mer lus —
    UNDERVURDERER PO-produktet det sanne naupliitallet. Er den negativ,
    overvurderer det.

    Vi kan ikke måle kovariansen, fordi vi ikke har Nᵢ. Vi kan måle
    FORTEGNET, fordi kapasiteten rangerer anleggene etter størrelse selv
    om den ikke teller fisken deres. En rangkorrelasjon er ufølsom for
    at MTB er et tak: så lenge et større tak i snitt betyr mer fisk,
    peker rangeringen samme vei.

    Det den IKKE gir, og som ikke skal stå noe annet sted i utskriften
    enn som en begrensning: hvor STOR skjevheten er. Til det trengs Nᵢ,
    altså biomasse per lokalitet, som ikke publiseres.
    """
    print(seksjon("11. DEN KJENTE SKJEVHETEN — fortegn, ikke størrelse"))
    print("     Σᵢ(N_fiskᵢ × lusᵢ)  ≠  N_fisk_PO × middel(lus)")
    print("     Σᵢ Nᵢ·xᵢ = N_PO·middel(x) + n·kovarians(N, x)")
    print()
    print("     kovarians > 0  (store anlegg har mer lus)  -> vårt tall er FOR LAVT")
    print("     kovarians < 0  (store anlegg har mindre lus) -> vårt tall er FOR HØYT")
    print()
    print("     Kapasitet (MTB, tonn) er ikke Nᵢ. Som RANGERING av")
    print("     anleggsstørrelse innen ett PO er den brukbar, og en rangkorrelasjon")
    print("     er ufølsom for at et tak ikke er en beholdning.")

    # Per lokalitet: snitt lus i vinduet over alle år, og kapasiteten.
    lus_per_lok: dict[str, list[float]] = defaultdict(list)
    po_for_lok: dict[str, int] = {}
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not avg.i_vindu(r["uke"]):
            continue
        lus_per_lok[r["lok"]].append(r["lus"])
        po_for_lok[r["lok"]] = r["po"]

    print(f"\n  a) Innen hvert PO, over lokaliteter (alle år slått sammen):")
    print(f"     {'PO':>3} {'n lok':>6} {'rho(kapasitet, lus)':>21}"
          f" {'median MTB':>12} {'MTB-spenn':>22}")
    rhoer = []
    for po in range(1, 14):
        lokker = [l for l, v in lus_per_lok.items()
                  if po_for_lok[l] == po and l in kapasitet and v]
        if len(lokker) < 5:
            continue
        k = [kapasitet[l] for l in lokker]
        x = [st.mean(lus_per_lok[l]) for l in lokker]
        r = spearman(k, x)
        rhoer.append(r)
        print(f"     {po:>3} {len(lokker):>6} {r:>+21.3f} {st.median(k):>12,.0f}"
              f" {min(k):>10,.0f}-{max(k):<10,.0f}".replace(",", " "))
    if rhoer:
        pos = sum(1 for r in rhoer if r > 0)
        print(f"\n     median rho = {st.median(rhoer):+.3f} over {len(rhoer)} PO-er, "
              f"{pos} positive / {len(rhoer) - pos} negative")
        print(f"     spredning: {min(rhoer):+.3f} til {max(rhoer):+.3f}")

    # Per (po, aar), slik at et enkeltår ikke drukner i tiårssnittet.
    print(f"\n  b) Innen hvert (PO, år) for seg — samme korrelasjon, år for år:")
    per_aar: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    for r in rader:
        if r["po"] is None or not r["rapportert"] or r["lus"] is None:
            continue
        if not avg.i_vindu(r["uke"]) or r["lok"] not in kapasitet:
            continue
        per_aar[(r["po"], r["aar"])].append((kapasitet[r["lok"]], r["lus"], r["lok"]))
    aars_rho = []
    for k in sorted(per_aar):
        # Ett punkt per LOKALITET, ikke per lokalitet-uke: samme anlegg
        # ville ellers telt ni ganger og gjort korrelasjonen til en
        # påstand om uker framfor om anlegg.
        per_lok: dict[str, list[float]] = defaultdict(list)
        kap: dict[str, float] = {}
        for kapasiteten, lus, lok in per_aar[k]:
            per_lok[lok].append(lus)
            kap[lok] = kapasiteten
        if len(per_lok) < 5:
            continue
        lokker = sorted(per_lok)
        aars_rho.append(spearman([kap[l] for l in lokker],
                                 [st.mean(per_lok[l]) for l in lokker]))
    if aars_rho:
        pos = sum(1 for r in aars_rho if r > 0)
        print(f"     {len(aars_rho)} (PO, år)-celler med minst 5 lokaliteter.")
        print(f"     median rho = {st.median(aars_rho):+.3f}, "
              f"{pos} positive / {len(aars_rho) - pos} negative "
              f"({pos / len(aars_rho):.1%} positive)")
        print(f"     spredning: {min(aars_rho):+.3f} til {max(aars_rho):+.3f}, "
              f"p25 {persentil(aars_rho, 0.25):+.3f}, p75 {persentil(aars_rho, 0.75):+.3f}")

    print("\n  DETTE GIR FORTEGNET, IKKE STØRRELSEN. Hvor mye PO-produktet bommer")
    print("  krever Nᵢ per lokalitet, altså biomasse per anlegg, som ikke")
    print("  publiseres åpent (docs/KILDE-BIOMASSE.md punkt 9). Ingen tall i")
    print("  denne utskriften korrigerer for skjevheten, og ingen av dem kan.")


def null_kategorien(bio: Biomasse, avg: Avgrensning) -> None:
    """Fisken uten produksjonsområde. Den faller ut av nevneren uansett.

    Den skal likevel stå: en analyse som summerer PO 1-13 og kaller det
    «Norge» tar systematisk feil, og ville ikke merket det. Se
    docs/KILDE-BIOMASSE.md punkt 6 — snittvekten i `(null)`-radene er
    2,02 kg mot 1,86 kg i PO-radene, så den opplagte forklaringen
    (settefisk og landanlegg) holder ikke. Årsaken er UKJENT og skal stå
    som ukjent.
    """
    print(seksjon("12. (null)-KATEGORIEN — fisk uten produksjonsområde"))
    print(f"{'år':>6} {'måneder':>8} {'andel snitt':>12} {'min':>8} {'maks':>8}"
          f" {'fisk uten PO, snitt':>21}")
    per_aar: dict[str, list[float]] = defaultdict(list)
    fisk_per_aar: dict[str, list[int]] = defaultdict(list)
    for maaned, andel in bio.andel_uten_po.items():
        per_aar[maaned[:4]].append(andel)
        if maaned in bio.uten_po:
            fisk_per_aar[maaned[:4]].append(bio.uten_po[maaned])
    for aar in sorted(per_aar):
        v = per_aar[aar]
        f = fisk_per_aar.get(aar, [])
        snitt_f = f"{int(st.mean(f)):,}".replace(",", " ") if f else "—"
        print(f"{aar:>6} {len(v):>8} {st.mean(v):>11.2%} {min(v):>7.2%}"
              f" {max(v):>7.2%} {snitt_f:>21}")
    alle = [a for v in per_aar.values() for a in v]
    if alle:
        print(f"\n  Over alle {len(alle)} månedene: {min(alle):.2%} til {max(alle):.2%}, "
              f"snitt {st.mean(alle):.2%}.")
    print("\n  Andelen er kildens EGET felt `andel_av_beholdning`, ikke vår divisjon.")
    print("  Den ligger i snapshotet nettopp for at en konsument som har droppet")
    print("  `uten_po` skal få et tall som ikke stemmer med vårt, i stedet for et")
    print("  tall som ser riktig ut.")
    print()
    print("  KONSEKVENS FOR NAUPLIITALLET: disse fiskene har ingen PO og inngår")
    print("  ikke i noe N_fisk_PO. Hvert naupliitall i denne utskriften mangler")
    print("  altså bidraget fra dem — og siden lusetallet deres heller ikke er")
    print("  knyttet til et PO, mangler de i begge ender. Årsaken til at de er")
    print("  uten kode er UKJENT og skal ikke gjettes.")


def absolutt_eller_normalisert(pred: dict, fasit: dict) -> None:
    """Stien gir et ABSOLUTT antall. Er det det vi vil sammenligne?

    Absolutt N_fisk per produksjonsområde er i stor grad bare områdets
    STØRRELSE, og størrelse er igjen nær geografi: PO 3 og PO 6 er store
    fordi kysten der er lang og skjermet. En rho mot kategori som
    kommer av at store områder er store, er ikke et funn.
    """
    print(seksjon("13. ABSOLUTT ELLER NORMALISERT"))
    print("  rho mot kategorirang, tre måter å skrive det samme tallet:")
    for navn, felt, forklaring in [
            ("FULL Stien, absolutt", "nauplier",
             "N_fisk_PO × middel(lus × (T+4,28)²) × 0,17 — døgnrate i vinduet"),
            ("FULL Stien per lokalitet", "nauplier_per_lok",
             "samme, delt på antall rapporterende lokaliteter"),
            ("DELVIS Stien (per fisk)", "stien_delvis",
             "nauplier / N_fisk / 0,17 — N_fisk-leddet faller ut igjen"),
    ]:
        r = _rho(pred, fasit, felt)
        n = sum(1 for k, p in pred.items()
                if p.get(felt) is not None
                and fasit.get(k, {}).get("kategori") in RANG)
        print(f"    {navn:>26}  rho = {r:+.3f}  (n = {n})")
        print(f"    {'':>26}  {forklaring}")

    print("\n  Merk identiteten i den tredje: å normalisere naupliitallet PER FISK")
    print("  fjerner nøyaktig det leddet denne kjøringen la til. `nauplier` delt")
    print("  på `N_fisk` er `stien_delvis × 0,17`. En «normalisering» kan altså")
    print("  spise hele det nye leddet, og hvilken nevner man velger er derfor")
    print("  ikke en presentasjonsdetalj.")

    print("\n  PER AREAL: ikke regnet ut. Produksjonsområdenes areal finnes ikke i")
    print("  noe snapshot dette repoet har, og et areal hentet fra hukommelsen")
    print("  eller anslått fra breddegrad ville vært et tall vi fant på. Skal det")
    print("  med, må arealene inn som en kilde eller som en fasitfil med")
    print("  proveniens, på samme måte som ekspertgruppens kategorier.")

    print("\n  HVA EKSPERTGRUPPEN SELV BRUKER — lest 26.08.2026 i")
    print("  «Modellert påvirkning av lakselus på vill laksefisk», Rapport fra")
    print("  havforskningen 2023-57 (HI), og i modellvedlegget til")
    print("  trafikklyssystemet:")
    print()
    print("    - Naupliiproduksjonen går inn som et ABSOLUTT antall larver per")
    print("      anlegg per døgn. Det er nøyaktig formelen over, og den er ikke")
    print("      normalisert av noe i det steget.")
    print("    - Det absolutte utslippet spres deretter av en HYDRODYNAMISK MODELL,")
    print("      og det er spredningen som gjør det om til en tetthet i vannet.")
    print("    - Kategorien lav/moderat/høy hviler til slutt på hvor mange lus en")
    print("      virtuell smolt får på seg langs en utvandringsrute — «>6, 2-6 og")
    print("      <2 lus per fisk» etter 30 dager i ROC-metoden.")
    print()
    print("  SVARET PÅ SPØRSMÅLET, OG BARE DET: det er den ABSOLUTTE varianten")
    print("  som svarer til deres inngangsdata. Normaliseringen deres skjer ved")
    print("  spredning i vann og langs smoltens rute — ikke ved å dele på antall")
    print("  lokaliteter. `nauplier_per_lok` svarer ikke på deres spørsmål; den")
    print("  svarer på «hvor mye slipper et typisk anlegg her ut».")
    print()
    print("  Og det som IKKE følger av dette: at den absolutte varianten dermed")
    print("  er den beste prediktoren. Vårt absolutte tall er et PO-aggregat uten")
    print("  spredningsmodell, uten utvandringsruter og uten geografi mellom")
    print("  anlegg og smolt. Det er deres INNGANGSDATA summert til PO, ikke")
    print("  deres RESULTAT. Valget mellom de to hører ekspertgruppen til.")


def det_egentlige_sporsmaalet(pred: dict, fasit: dict, bredde_po: dict,
                              treff: dict[str, tuple[int, int]]) -> None:
    """Forklarer FULL Stien-proxy noe UTOVER breddegrad og PO-identitet?

    Ikke «korrelerer proxyen med kategorien» — det gjør geografi også,
    og omtrent like godt. Tallene samles her, rått, uten at det trekkes
    en konklusjon om at noe virker.
    """
    print(seksjon("14. DET EGENTLIGE SPØRSMÅLET"))

    print("\n  a) rho mot kategorirang — proxyen mot ren geografi:")
    rader = []
    for navn, hent in prediktorene(bredde_po):
        par = [(hent(k, p), RANG[fasit[k]["kategori"]])
               for k, p in pred.items()
               if fasit.get(k, {}).get("kategori") in RANG and hent(k, p) is not None]
        if len(par) < 5:
            continue
        r = spearman([a for a, _ in par], [b for _, b in par])
        rader.append((navn, r, len(par)))
        print(f"     {navn:>26}  rho = {r:+.3f}   (n = {len(par)})")
    geo = max((abs(r) for navn, r, _ in rader
               if navn.startswith(("breddegrad", "PO-nummer"))), default=0.0)
    full = next((r for navn, r, _ in rader if navn == "FULL Stien-proxy"), None)
    if full is not None:
        print(f"\n     Beste rene geografivariabel: |rho| = {geo:.3f}")
        print(f"     FULL Stien-proxy:              |rho| = {abs(full):.3f}")
        print(f"     Differanse:                    {abs(full) - geo:+.3f}")

    print("\n  b) INNEN ETT PO, der geografien er konstant:")
    for navn, hent in prediktorene(bredde_po):
        if navn.startswith(("breddegrad", "PO-nummer")):
            continue
        rhoer = rho_innen_po(pred, fasit, hent)
        if not rhoer:
            print(f"     {navn:>26}  —  (ingen PO med nok variasjon)")
            continue
        print(f"     {navn:>26}  median {st.median(rhoer):+.3f}  "
              f"spenn {min(rhoer):+.3f} til {max(rhoer):+.3f}  ({len(rhoer)} PO-er)")

    print("\n  c) De faktiske kategoriskiftene — traff proxyen bedre enn 6-7 av 11?")
    print(f"     {'prediktor':>26} {'treff':>10} {'myntkast':>10}")
    for navn, (enige, n) in treff.items():
        if n:
            print(f"     {navn:>26} {f'{enige}/{n}':>10} {n / 2:>10.1f}")

    print("\n  d) SVARET, RÅTT:")
    if full is None:
        print("     FULL Stien-proxy har ikke nok celler med kjent kategori til at")
        print("     spørsmålet kan stilles. Det er i seg selv svaret denne gangen.")
        return
    innen = rho_innen_po(pred, fasit, lambda k, p: p["nauplier"])
    innen_med = st.median(innen) if innen else float("nan")
    fullt_treff = treff.get("FULL Stien-proxy", (0, 0))

    print("     GEOGRAFI ER TO TING, og N_fisk svarer ulikt på dem:")
    for navn, felt in [("temperatur", "temp_snitt"), ("N_fisk", "n_fisk"),
                       ("FULL Stien-proxy", "nauplier")]:
        felles = [k for k in pred if k in bredde_po and pred[k].get(felt) is not None]
        if len(felles) < 5:
            continue
        v = [pred[k][felt] for k in felles]
        rb = spearman(v, [bredde_po[k] for k in felles])
        vf = variansforhold(pred, felt)
        if vf is None:
            continue
        print(f"       {navn:>18}  rho(x, breddegrad) = {rb:+.3f}"
              f"   MELLOM/INNEN PO = {vf[2]:.1f}x")
    print()
    print("       De to kolonnene måler ikke det samme, og for N_fisk peker de")
    print("       hver sin vei. En rangkorrelasjon mot breddegrad fanger bare en")
    print("       MONOTON nord-sør-gradient. Variansdekomponeringen fanger et")
    print("       FAST NIVÅ per produksjonsområde, uansett rekkefølge.")
    print("       N_fisk har ingen gradient (rho ≈ 0) og et sterkt fast nivå.")
    print("       Den er altså ikke BREDDEGRAD, men den er i stor grad")
    print("       PO-IDENTITET — hvor stort området er. Det er en annen")
    print("       innvending enn den temperaturen møtte, og den står ubesvart.")
    print()
    print(f"     Utover geografi:  {abs(full) - geo:+.3f} i |rho|. Den beste rene")
    print(f"                       geografivariabelen oppnår {geo:.3f} uten å vite")
    print(f"                       noe som helst om lus, temperatur eller fisk.")
    if innen:
        print(f"     Innen PO:         median rho {innen_med:+.3f} over {len(innen)} PO-er, "
              f"spenn {min(innen):+.3f} til {max(innen):+.3f}.")
    if fullt_treff[1]:
        print(f"     Kategoriskiftene: {fullt_treff[0]} av {fullt_treff[1]} på riktig side "
              f"(myntkast {fullt_treff[1] / 2:.1f}).")
    print()
    print("     Ingen modell er tilpasset, ingen terskel er justert, og ingen av")
    print("     tallene over er en test. Tolkningen står igjen til leseren; det")
    print("     eneste denne seksjonen påstår er at tallene er de som står her.")


def notert_ikke_rettet() -> None:
    """Ting kjøringen så, som ikke skal røres i denne økta.

    Skilt fra seksjon 9 («ting som ser rart ut») fordi de tingene er
    funn i DATAENE. Dette er funn i PROVENIENSEN — i hva snapshotene sier
    om seg selv — og de rettes ikke ved å endre en analyse.
    """
    print(seksjon("15. NOTERT, IKKE RETTET"))
    print("  lusetall har `utvalg` = (ukjent) i alle 448 snapshots, mens")
    print("  sjotemperatur har {\"rapporttype\":[\"Lice\"]} i alle sine 448.")
    print("  Det er samme rapport fra samme tjeneste.")
    print()
    print("  ETTERGÅTT I DENNE KJØRINGEN, og forklaringen er ikke den nærliggende:")
    print("  `sources/lusetall.py` SETTER `self.utvalg = {}` i `hent_uke()` — altså")
    print("  «kjent: ingen filtrering», som er riktig for `/locality/{år}/{uke}`.")
    print("  Kilden mangler det ikke.")
    print()
    print("  Forskjellen er KRONOLOGI, ikke kunnskap:")
    print()
    print("    lusetall-snapshotene    fetched_at til 2026-08-24T19:48Z")
    print("    commit 33f4769          2026-08-25T12:42Z  «Utvalget skiller")
    print("                            \u00abvet ikke\u00bb fra \u00abba om alt\u00bb»")
    print("    sjotemperatur-snapshot. fetched_at fra 2026-08-25T13:02Z")
    print()
    print("  Sjøtemperatur ble backfillet TJUE MINUTTER etter at skillet ble")
    print("  innført; lusetall ble backfillet dagen før. Asymmetrien i loggen er")
    print("  et avtrykk av når de to jobbene kjørte, ikke av hva de visste.")
    print()
    print("  Og den kan ikke rettes: data skrives én gang (CLAUDE.md regel 2).")
    print("  De 448 lusetall-snapshotene vil for alltid lese «vet ikke» om et")
    print("  utvalg vi nå vet var «ingen filtrering». Neste ukentlige kjøring")
    print("  skriver riktig verdi, og da vil serien ha et skille midt i seg som")
    print("  ser ut som en endring i utvalget og ikke er det.")
    print()
    print("  IKKE RETTET I DENNE ØKTA. Notert her, i utskriften analysen selv")
    print("  skriver, fordi det er en opplysning om hvor mye loggens")
    print("  `lesing.lusetall.utvalg`-linje er verdt.")


def uro(rader: list[dict], pred: dict, avg: Avgrensning) -> None:
    """Ting som ser rart ut. Like verdifullt som svaret."""
    print(seksjon("9. TING SOM SER RART UT"))

    # tomme PO-år
    manglende = [(po, aar) for po in range(1, 14)
                 for aar in avg.aar if (po, aar) not in pred]
    if manglende:
        print(f"  PO-år uten data i uke {avg.vindu[0]}-{avg.vindu[1]}: {manglende}")

    # PO-år med svært få lokaliteter
    tynne = sorted(((p["n_lok"], po, aar) for (po, aar), p in pred.items()))[:8]
    print("\n  Tynneste PO-år (antall rapporterende lokaliteter i vinduet):")
    for n_lok, po, aar in tynne:
        print(f"    PO{po:<3} {aar}  n_lok={n_lok:<4} "
              f"snitt {pred[(po,aar)]['snitt_uvektet']:.3f}")

    # rapporterte lus uten rapporteringsflagg og omvendt
    a = sum(1 for r in rader if r["lus"] is not None and not r["rapportert"])
    b = sum(1 for r in rader if r["lus"] is None and r["rapportert"])
    print(f"\n  Lok-uker med lusetall, men lus_er_rapportert=False: {a}")
    print(f"  Lok-uker med lus_er_rapportert=True, men uten lusetall: {b}")

    # ekstremverdier
    ekstreme = sorted((r for r in rader if r["lus"] is not None),
                      key=lambda r: -r["lus"])[:5]
    print("\n  Høyeste enkeltmålinger 2018-2026:")
    for r in ekstreme:
        print(f"    lok {r['lok']:>7}  {r['aar']} uke {r['uke']:>2}  "
              f"PO{str(r['po']):<5} {r['lus']:.2f} voksne hunnlus")

    # 2026 er et delår
    n26 = sum(1 for r in rader if r["aar"] == 2026)
    uker26 = sorted({r["uke"] for r in rader if r["aar"] == 2026})
    print(f"\n  2026 er et DELÅR: uker {uker26[0]}-{uker26[-1]} "
          f"({len(uker26)} uker, {n26} lok-uker). Serien slutter uke "
          f"{uker26[-1]} fordi kilden henter med fire ukers etterslep.")

    # feltnormal-fellen fra CLAUDE.md 1b-4: kom feltet, eller sa det noe?
    print("\n  Kontroll av felt som «kom» men kanskje ikke «sa noe» (jf. F10):")
    for felt in ["rensefisk", "mekanisk", "medikament"]:
        pr_aar = defaultdict(lambda: [0, 0])
        for r in rader:
            pr_aar[r["aar"]][0] += 1
            pr_aar[r["aar"]][1] += 1 if r[felt] else 0
        andeler = " ".join(f"{aar}:{n/max(t,1):.1%}" for aar, (t, n) in sorted(pr_aar.items()))
        print(f"    {felt:<12} {andeler}")


# ---------------------------------------------------------------- plott

def plott_geografi(pred: dict, fasit: dict, bredde_po: dict,
                   felt: str = "temp_snitt", tittel: str = "", enhet: str = "°C",
                   fotnote: str = "") -> str:
    """Kontrollen som SVG: en prediktor mot breddegrad, farget etter kategori.

    Ligger et punkt langt fra linja, er variabelen det ÅRET noe annet enn
    hvor området ligger. Ligger alle på linja, er den ikke det.

    `felt` er et argument og ikke fast `temp_snitt`, fordi N_fisk skal
    gjennom NØYAKTIG samme kontroll som temperaturen. To nesten like
    plottefunksjoner ville før eller siden fått hver sin akseskalering
    eller hver sin regresjonslinje, og da ville forskjellen mellom de to
    bildene delvis vært tegningen.
    """
    farge = {"lav": "#2f7d32", "moderat": "#c98a00", "hoy": "#b3261e",
             "ukjent": "#bbbbbb"}
    pkt = [(bredde_po[k], pred[k][felt],
            fasit.get(k, {}).get("kategori", "ukjent"), k)
           for k in sorted(pred)
           if k in bredde_po and pred[k].get(felt) is not None]
    if len(pkt) < 3:
        return ""
    B, H, MV, MH, MT, MB = 900, 420, 80, 20, 34, 58
    bx = [a for a, *_ in pkt]; by = [b for _, b, *_ in pkt]
    put = (max(bx) - min(bx)) * 0.04 or 0.3
    puty = (max(by) - min(by)) * 0.06 or 0.4
    x0, x1 = min(bx) - put, max(bx) + put
    y0, y1 = min(by) - puty, max(by) + puty
    def X(v): return MV + (v - x0) / (x1 - x0) * (B - MV - MH)
    def Y(v): return H - MB - (v - y0) / (y1 - y0) * (H - MT - MB)
    def merk(v):
        if enhet == "°C":
            return f"{v:.0f}°C"
        return f"{v / 1e6:.0f} mill."

    s = [f'<svg viewBox="0 0 {B} {H}" width="100%" font-family="system-ui" font-size="11">']
    s.append(f'<text x="{MV}" y="18" font-size="13" font-weight="600">'
             f'{tittel or "Kontrollen: prediktor mot breddegrad, ett punkt per PO-år"}'
             f'</text>')
    for i in range(6):
        v = y0 + (y1 - y0) * i / 5
        s.append(f'<line x1="{MV}" y1="{Y(v):.1f}" x2="{B-MH}" y2="{Y(v):.1f}" stroke="#eee"/>')
        s.append(f'<text x="{MV-8}" y="{Y(v)+4:.1f}" text-anchor="end" fill="#666">'
                 f'{merk(v)}</text>')
    for b in range(int(x0) + 1, int(x1) + 1, 2):
        s.append(f'<text x="{X(b):.1f}" y="{H-MB+18:.1f}" text-anchor="middle" '
                 f'fill="#666">{b}°N</text>')
    # minste kvadraters linje, bare som visuell referanse
    mx, my = st.mean(bx), st.mean(by)
    nev = sum((a - mx) ** 2 for a in bx)
    if nev:
        hell = sum((a - mx) * (b - my) for a, b in zip(bx, by)) / nev
        s.append(f'<line x1="{X(x0):.1f}" y1="{Y(my + hell*(x0-mx)):.1f}" '
                 f'x2="{X(x1):.1f}" y2="{Y(my + hell*(x1-mx)):.1f}" '
                 f'stroke="#888" stroke-dasharray="5 4"/>')
    for bb, tt, kat, k in pkt:
        s.append(f'<circle cx="{X(bb):.1f}" cy="{Y(tt):.1f}" r="4.5" '
                 f'fill="{farge[kat]}" fill-opacity="0.8"><title>PO{k[0]} {k[1]}: '
                 f'{tt:,.2f} ved {bb:.2f}°N ({kat})</title></circle>'.replace(",", " "))
    s.append(f'<text x="{MV}" y="{H-8}" fill="#666">'
             f'Spearman = {spearman(bx, by):+.3f}. '
             f'{fotnote}</text>')
    s.append('</svg>')
    return "".join(s)


def plott_proxy(pred: dict, fasit: dict, felt: str = "stien_delvis",
                tittel: str = "", fotnote: str = "") -> str:
    """Én prediktor per kategori, samme form som lusefordelingen.

    Samme grunn til å ta `felt` som argument som i `plott_geografi()`:
    DELVIS og FULL proxy skal tegnes likt for at forskjellen mellom
    bildene skal være tallene og ikke tegningen.
    """
    farge = {"lav": "#2f7d32", "moderat": "#c98a00", "hoy": "#b3261e"}
    grupper = defaultdict(list)
    for k, p in pred.items():
        f = fasit.get(k)
        if f and f["kategori"] != "ukjent" and p.get(felt) is not None:
            grupper[f["kategori"]].append(p[felt])
    if not grupper:
        return ""
    B, H = 900, 270
    m = max(x for v in grupper.values() for x in v)
    def X(v): return 70 + (v / m) * (B - 190)
    # Samme tallformat som tabellene i seksjon 8b-8g. Ett sted, så et
    # naupliitall ikke leses som «0,18 mrd.» i plottet og «180 mill.» i
    # tabellen — samme tall skrevet på to måter er en unødig anledning
    # til å tro at det er to tall.
    def vis(v): return _kort(v) if m >= 1000 else f"{v:.2f}"
    s = [f'<svg viewBox="0 0 {B} {H}" width="100%" font-family="system-ui" font-size="11">']
    s.append(f'<text x="70" y="18" font-size="13" font-weight="600">'
             f'{tittel or "DELVIS Stien-proxy: lus × (T + 4,28)² — UTEN antall fisk"}</text>')
    for i, kat in enumerate(KATEGORIER):
        v = sorted(grupper.get(kat, []))
        if not v:
            continue
        yy = 58 + i * 62
        s.append(f'<text x="62" y="{yy+4}" text-anchor="end" font-weight="600" '
                 f'fill="{farge[kat]}">{kat}</text>')
        s.append(f'<line x1="{X(min(v)):.1f}" y1="{yy}" x2="{X(max(v)):.1f}" y2="{yy}" '
                 f'stroke="{farge[kat]}" stroke-width="2" stroke-opacity="0.35"/>')
        s.append(f'<line x1="{X(st.median(v)):.1f}" y1="{yy-12}" '
                 f'x2="{X(st.median(v)):.1f}" y2="{yy+12}" '
                 f'stroke="{farge[kat]}" stroke-width="2"/>')
        for val in v:
            s.append(f'<circle cx="{X(val):.1f}" cy="{yy}" r="4" fill="{farge[kat]}" '
                     f'fill-opacity="0.55"><title>{vis(val)}</title></circle>')
        s.append(f'<text x="{B-20}" y="{yy+4}" text-anchor="end" fill="#666">'
                 f'n={len(v)}, median {vis(st.median(v))}</text>')
    standard = ("To av tre ledd er ikke formelen. N_fisk mangler, og det er "
                "antall verter.")
    s.append(f'<text x="70" y="{H-10}" fill="#666">{fotnote or standard}</text>')
    s.append('</svg>')
    return "".join(s)


def plott(pred: dict, fasit: dict, bredde_po: dict, avg: Avgrensning,
          logg: kjoringslogg.Kjoringslogg) -> Path:
    """To enkle plott som SVG i én HTML-fil. Ingen matplotlib i repoet,
    og en ny avhengighet er ikke verdt en utforskning.

    `logg` er med for PEKEREN, ikke for å skrive noe: resultatfila skal
    kunne si hvilke valg den hvilte på uten at leseren må lete i git
    eller i en terminalhistorikk som er borte. Se punkt 3 — en analyse
    leser ikke git, og et plott som ikke peker på loggen sin er et tall
    uten proveniens.
    """
    UT.mkdir(exist_ok=True)
    farge = {"lav": "#2f7d32", "moderat": "#c98a00", "hoy": "#b3261e",
             "ukjent": "#bbbbbb"}

    # --- plott 1: snitt per PO-år, punkt farget etter kategori -----------
    punkter = [(po, aar, p["snitt_uvektet"],
                fasit.get((po, aar), {}).get("kategori", "ukjent"))
               for (po, aar), p in pred.items()]
    maks = max(v for *_, v, _ in punkter)
    B, H, MV, MH, MT, MB = 900, 380, 55, 20, 30, 55
    def x(po): return MV + (po - 0.5) * (B - MV - MH) / 13
    def y(v): return H - MB - (v / maks) * (H - MT - MB)

    s = [f'<svg viewBox="0 0 {B} {H}" width="100%" font-family="system-ui" font-size="11">']
    s.append(f'<text x="{MV}" y="18" font-size="13" font-weight="600">Snitt voksne '
             f'hunnlus per rapporterende lokalitet, uke {avg.vindu[0]}-{avg.vindu[1]}'
             f' — farget etter ekspertgruppens kategori</text>')
    for t in [0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        if t > maks: break
        s.append(f'<line x1="{MV}" y1="{y(t):.1f}" x2="{B-MH}" y2="{y(t):.1f}" '
                 f'stroke="#e5e5e5"/>')
        s.append(f'<text x="{MV-8}" y="{y(t)+4:.1f}" text-anchor="end" '
                 f'fill="#666">{t:.1f}</text>')
    s.append(f'<line x1="{MV}" y1="{y(0.5):.1f}" x2="{B-MH}" y2="{y(0.5):.1f}" '
             f'stroke="#b3261e" stroke-dasharray="4 3"/>'
             if 0.5 <= maks else '')
    for po in range(1, 14):
        s.append(f'<text x="{x(po):.1f}" y="{H-MB+18}" text-anchor="middle" '
                 f'fill="#333">PO{po}</text>')
    spenn = avg.til_aar - avg.fra_aar
    for po, aar, v, kat in punkter:
        dx = ((aar - avg.fra_aar) / spenn - 0.5) * ((B - MV - MH) / 13 - 12)
        s.append(f'<circle cx="{x(po)+dx:.1f}" cy="{y(v):.1f}" r="4" '
                 f'fill="{farge[kat]}" fill-opacity="0.85"><title>PO{po} {aar}: '
                 f'{v:.3f} ({kat})</title></circle>')
    s.append(f'<text x="{MV}" y="{H-8}" fill="#666">Hvert punkt er ett PO-år; '
             f'x-posisjon innen kolonnen går fra {avg.fra_aar} (venstre) til '
             f'{avg.til_aar} (høyre). Grå = år uten fasit.</text>')
    s.append('</svg>')
    p1 = "".join(s)

    # --- plott 2: fordeling per kategori ---------------------------------
    grupper = defaultdict(list)
    for (po, aar), p in pred.items():
        f = fasit.get((po, aar))
        if f and f["kategori"] != "ukjent":
            grupper[f["kategori"]].append(p["snitt_uvektet"])
    B2, H2 = 900, 260
    m2 = max(x for v in grupper.values() for x in v)
    def x2(v): return 70 + (v / m2) * (B2 - 110)
    s = [f'<svg viewBox="0 0 {B2} {H2}" width="100%" font-family="system-ui" font-size="11">']
    s.append('<text x="70" y="18" font-size="13" font-weight="600">Fordeling av '
             'samme snitt, per kategori. Overlapper de?</text>')
    for i, kat in enumerate(KATEGORIER):
        v = sorted(grupper.get(kat, []))
        if not v:
            continue
        yy = 55 + i * 62
        s.append(f'<text x="62" y="{yy+4}" text-anchor="end" font-weight="600" '
                 f'fill="{farge[kat]}">{kat}</text>')
        s.append(f'<line x1="{x2(min(v)):.1f}" y1="{yy}" x2="{x2(max(v)):.1f}" '
                 f'y2="{yy}" stroke="{farge[kat]}" stroke-width="2" '
                 f'stroke-opacity="0.35"/>')
        s.append(f'<line x1="{x2(st.median(v)):.1f}" y1="{yy-12}" '
                 f'x2="{x2(st.median(v)):.1f}" y2="{yy+12}" '
                 f'stroke="{farge[kat]}" stroke-width="2"/>')
        for val in v:
            s.append(f'<circle cx="{x2(val):.1f}" cy="{yy}" r="4" '
                     f'fill="{farge[kat]}" fill-opacity="0.55"><title>{val:.3f}'
                     f'</title></circle>')
        s.append(f'<text x="{B2-30}" y="{yy+4}" text-anchor="end" fill="#666">'
                 f'n={len(v)}, median {st.median(v):.3f}</text>')
    for t in [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
        if t > m2: break
        s.append(f'<line x1="{x2(t):.1f}" y1="35" x2="{x2(t):.1f}" y2="{H2-40}" '
                 f'stroke="#eee"/>')
        s.append(f'<text x="{x2(t):.1f}" y="{H2-24}" text-anchor="middle" '
                 f'fill="#666">{t:.2f}</text>')
    s.append('</svg>')
    p2 = "".join(s)

    p3 = plott_geografi(
        pred, fasit, bredde_po, "temp_snitt",
        "Kontrollen I: sjøtemperatur mot breddegrad, ett punkt per PO-år", "°C",
        "Punktene ligger nesten på en linje: temperaturen i et PO-år er i "
        "hovedsak hvor området ligger.")
    p4 = plott_proxy(pred, fasit)
    p5 = plott_geografi(
        pred, fasit, bredde_po, "n_fisk",
        "Kontrollen II: N_fisk mot breddegrad — det eneste leddet som ikke er "
        "geografi", "fisk",
        "N_fisk er et driftsvalg, ikke en breddegrad. Ligger punktene like "
        "tett på linja som temperaturens, gjelder samme forbehold.")
    p6 = plott_proxy(
        pred, fasit, "nauplier",
        "FULL Stien-proxy: N_fisk × lus × 0,17 × (T + 4,28)² — alle tre leddene",
        "Klekte nauplier per døgn i en typisk uke i vinduet. PO-produktet, ikke "
        "summen av anleggenes egne — se seksjon 11 om fortegnet på skjevheten.")

    ut = UT / "lusepress.html"
    ut.write_text(
        "<meta charset='utf-8'><title>Lusepress mot ekspertgruppen</title>"
        "<style>body{font-family:system-ui;max-width:960px;margin:2rem auto;"
        "padding:0 1rem;color:#222}p{color:#555;line-height:1.5}"
        ".logg{background:#f6f6f4;border-left:3px solid #999;padding:.8rem 1rem;"
        "font-size:.92rem}</style>"
        "<h1>Lusepress mot ekspertgruppens kategorier</h1>"
        "<p>Utforskning, ikke modell. Snitt voksne hunnlus per rapporterende "
        f"lokalitet i utvandringsvinduet uke {avg.vindu[0]}–{avg.vindu[1]}, "
        f"{avg.fra_aar}–{avg.til_aar}. "
        "Fasit for 2020–2024; øvrige år er grå fordi kategorien ikke er kjent.</p>"
        + pekeren(logg)
        + p1 + p2
        + "<h2>Sjøtemperatur som tredje prediktor</h2>"
        "<p>Temperaturen kommer fra den samme ukerapporten som lusetallet — "
        "samme ukeakse, samme etterslep. Plottet under er KONTROLLEN: hvis "
        "temperaturen i et PO-år bare er hvor området ligger, forklarer den "
        "ingenting utover geografi.</p>"
        + p3 + p4
        + "<h2>N_fisk — det tredje leddet, og samme kontroll</h2>"
        "<p>Antall fisk per produksjonsområde per måned kommer fra "
        "Fiskeridirektoratets biomassestatistikk (<code>BEHFISK_STK</code>). "
        "Det er det eneste leddet i Stien-formelen som i prinsippet ikke er "
        "geografi — et driftsvalg og en konsesjonsgrense, ikke en breddegrad. "
        "Første plott under stiller nøyaktig samme spørsmål til N_fisk som "
        "kontrollen over stilte til temperaturen.</p>"
        "<p><strong>Forbeholdet som følger hvert naupliitall:</strong> "
        "N_fisk finnes bare per produksjonsområde, lus og temperatur per "
        "lokalitet. Σᵢ(N_fiskᵢ × lusᵢ) er ikke N_fisk_PO × middel(lus), og "
        "forskjellen er kovariansen mellom anleggsstørrelse og lusenivå innen "
        "området. Biomasse per lokalitet publiseres ikke åpent, så skjevheten "
        "kan måles i fortegn, ikke i størrelse.</p>"
        + p5 + p6
        + "<p>Kilde rådata: Fiskeridirektoratet (NLOD) og BarentsWatch. "
        "Attribusjonen er et lisensvilkår, ikke en høflighet.</p>"
        + pekeren(logg), encoding="utf-8")
    return ut


def pekeren(logg: kjoringslogg.Kjoringslogg) -> str:
    """Blokka som knytter et tall til valgene bak det.

    Står både øverst og nederst i fila. Det er ikke pynt: en leser som
    scroller til et plott og stopper der, skal ikke kunne unngå å se at
    tallene har en logg — og hvilken.

    Løpenummeret og utgivelsestidspunktet for hver leste fil står i
    LOGGEN og ikke her. Det som står her, er nok til å finne den:
    filnavnet, committen og kjøretidspunktet.
    """
    lenke = logg.peker_fra(UT)
    return (
        f'<p class="logg"><strong>Kjøringslogg:</strong> '
        f'<a href="{lenke}">{lenke}</a> — alle valg som påvirket '
        f'tallene på denne sida: avgrensning, vindu, mål, fasitens '
        f'innholds-hash, PERSONFORMER-lista, og hvilken snapshot-fil hver '
        f'dato ble lest fra, med løpenummer og <code>published_at</code>.<br>'
        f'Kjørt {logg.kjort_at}.</p>')


# ---------------------------------------------------------------- hoved

def versjonsvalg_av(tekst: str):
    """`"3"` -> `3`, `"gjeldende"` -> `"gjeldende"`.

    Løpenummeret er et TALL og ikke en streng her, fordi
    `kjoringslogg._velg()` sammenligner det med løpenummeret på fila. En
    streng «3» ville aldri matchet, og analysen ville stilltiende lest
    ingenting for den datoen.
    """
    return int(tekst) if tekst.isdigit() else tekst


def vindu_av(tekst: str) -> tuple[int, int]:
    """`"16-24"` -> `(16, 24)`. Kaster på alt annet.

    Kaster og faller ikke tilbake på standarden: en skrivefeil i et
    vindusargument skal stoppe kjøringen, ikke gi den stille et annet
    vindu enn det som står i kommandolinja mens loggen fører det
    riktige. Det ville vært den samme klassen feil hele dette repoet
    er bygget rundt — en verdi utenfor dataene som avgjør hva de betyr,
    og som ingen kan lese ut av resultatet.
    """
    biter = tekst.split("-")
    if len(biter) != 2:
        raise argparse.ArgumentTypeError(
            f"vindu må være «fra-til», f.eks. 16-24 — fikk {tekst!r}")
    try:
        lav, hoy = int(biter[0]), int(biter[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"vindu må være to ISO-ukenumre, f.eks. 16-24 — fikk {tekst!r}")
    if not (1 <= lav <= hoy <= 53):
        raise argparse.ArgumentTypeError(
            f"vindu {tekst!r} er ikke et gyldig ISO-ukespenn i [1, 53]")
    return lav, hoy


def argumenter(argv: list[str] | None = None) -> argparse.Namespace:
    """Bare valg som SKAL kunne endres uten å redigere fila.

    Grunnen til at de er argumenter og ikke konstanter: endrer du en
    konstant, endrer du også `git.commit` og `git.rent_arbeidstre` i
    loggen — og da skiller to logger seg på tre linjer der ett valg ble
    endret. Punkt 4 i kjøringsloggens begrunnelse krever at loggen
    skiller seg på NØYAKTIG det valget, og det krever at valget kan
    endres uten å røre arbeidstreet.

    De fire er ikke av samme slag, og det står i hjelpeteksten:
    versjonsvalgene er ANALYTISKE (hvilken påstand om fortiden), vinduet
    og startåret er TOLKNINGER (hva vi mener med «utvandringen» og «god
    nok dekning»).
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--akvakultur-versjon", default=kjoringslogg.GJELDENDE,
        help="hvilken VERSJON av akvakultursnapshotet PO-kartet, "
             "breddegradene og kapasitetene leses fra: 'gjeldende' (sist "
             "utgitte, standard), 'forste', eller et løpenummer. "
             "2026-08-24 finnes i fire versjoner.")
    ap.add_argument(
        "--biomasse-versjon", default=kjoringslogg.GJELDENDE,
        help="ANALYTISK VALG. Hvilken av Fiskeridirektoratets påstander om "
             "hver måned N_fisk leses fra. 'gjeldende' (standard) er "
             "basefila hentet 25.08.2026; 'forste' er Wayback-kopien utgitt "
             "20.07.2024 der den finnes; '2' er strengt løpenummer 2, som "
             "bare 81 av 103 måneder har. De to påstandene er uenige om "
             "21,9 %% av PO-månedene.")
    ap.add_argument(
        "--vindu", default="%d-%d" % STANDARD_VINDU, type=vindu_av,
        help="TOLKNING. ISO-ukene som regnes som utvandringsvinduet. "
             "Standard 16-24, valgt fordi det grovt er utvandringsvinduet "
             "for villakssmolt — ikke fordi noe er målt til å begynne i "
             "uke 16.")
    ap.add_argument(
        "--vindu-vid", default="%d-%d" % STANDARD_VINDU_VID, type=vindu_av,
        help="vinduet følsomhetssjekken i seksjon 6 sammenligner med. "
             "Standard 14-26. Flyttes hovedvinduet langt, bør denne flyttes "
             "med — ellers sammenlignes to vinduer som ikke har noe med "
             "hverandre å gjøre.")
    ap.add_argument(
        "--fra-aar", default=STANDARD_FRA_AAR, type=int,
        help="TOLKNING. Første ISO-år som teller. Standard 2018, valgt av "
             "dekningshensyn: rapporteringsdekningen steg fra 80,7 %% i 2012 "
             "til 99,2 %% i 2026, og en stigende trend i et aggregat over "
             "hele serien kan være ren dekningsvekst.")
    ap.add_argument(
        "--logg", default=str(LOGGFIL),
        help="hvor kjøringsloggen skrives. Endres bare når to kjøringer "
             "skal sammenlignes.")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = argumenter(argv)
    akva_versjon = versjonsvalg_av(args.akvakultur_versjon)
    bio_versjon = versjonsvalg_av(args.biomasse_versjon)
    avg = Avgrensning(fra_aar=args.fra_aar, til_aar=TIL_AAR,
                      vindu=args.vindu, vindu_vid=args.vindu_vid)

    logg = kjoringslogg.Kjoringslogg("lusepress_mot_fasit", Path(args.logg))

    # Avgrensningen. Alt som avgjør HVILKE observasjoner som teller.
    logg.valg("avgrensning.fra_aar", avg.fra_aar)
    logg.valg("avgrensning.til_aar", avg.til_aar)
    logg.valg("avgrensning.aarsakse", "ISO-år, ikke kalenderår")
    logg.valg("avgrensning.vindu", f"uke {avg.vindu[0]}-{avg.vindu[1]}")
    logg.valg("avgrensning.vindu_folsomhet",
              f"uke {avg.vindu_vid[0]}-{avg.vindu_vid[1]}")
    logg.valg("avgrensning.vindu_er_tolkning",
              "uke 16-24 er valgt som grovt utvandringsvindu, ikke målt")
    logg.valg("avgrensning.po", "1-13, fra prodomraade_kode i akvakultur")
    logg.valg("avgrensning.arter",
              "ingen artsavgrensning — lusetall skiller ikke art")
    logg.valg("avgrensning.rader",
              "rapportert=True, lus ikke tom, po kjent. Brakklagte inngår "
              "bare i dekningstabellen.")

    # Målet og vektingen. Det som avgjør HVA som regnes ut av dem.
    logg.valg("maal.hoved", "snitt_uvektet")
    logg.valg("maal.aggregering",
              "lokalitet-uke -> ukesnitt per PO -> uvektet snitt over uker")
    logg.valg("maal.vektet_alternativ",
              "snitt_vektet = snitt over alle lokalitet-uker")
    logg.valg("maal.ovrige", ["median", "p95", "maks", "n_lok",
                             "temp_snitt", "stien_delvis",
                             "n_fisk", "nauplier", "nauplier_per_lok"])
    logg.valg("maal.stien_t0", STIEN_T0)
    logg.valg("maal.stien_k", STIEN_K)
    logg.valg("maal.stien_delvis",
              "lus × (T + 4,28)² per lokalitet-uke — UTEN N_fisk og "
              "uten 0,17")
    logg.valg("maal.stien_full",
              "N_fisk_PO × middel_lok(lus × (T + 4,28)²) × 0,17 per PO-uke, "
              "så uvektet snitt over uker. Døgnrate, ikke sum over vinduet.")
    logg.valg("maal.stien_full_skjevhet",
              "N_fisk er PO-nivå, lus er lokalitetsnivå: Σᵢ(Nᵢ×lusᵢ) ≠ "
              "N_PO×middel(lus). Fortegn måles i seksjon 11, størrelse "
              "kan ikke måles.")
    logg.valg("maal.nfisk_felt", f"{FISK_FELT} (BEHFISK_STK, beholdning ved "
                                 f"månedslutt)")
    logg.valg("maal.nfisk_maanedskobling",
              "uka får måneden fra sin egen snapshotdato (mandagen); "
              "ingen interpolasjon mellom månedslutt")
    logg.valg("maal.nfisk_dekningskrav",
              "hele vinduets månedssett må finnes for PO-et, ellers faller "
              "PO-året ut av naupliitallet")
    logg.valg("maal.manglende_temperatur",
              "utelates; leses ALDRI som 0 grader")
    logg.valg("maal.manglende_fisk",
              "utelates; leses ALDRI som 0 fisk — N_fisk er en multiplikator")
    logg.valg("maal.korrelasjon", "Spearman, ranger med gjennomsnittsrang")
    logg.valg("kategorier", KATEGORIER)

    logg.fil("fasit", FASIT)
    fasit = les_fasit()
    logg.valg("fasit.rader", len(fasit))
    ukjente = sorted(k for k, v in fasit.items() if v["kategori"] == "ukjent")
    logg.valg("fasit.ukjent.antall", len(ukjente))
    logg.valg("fasit.ukjent",
              ", ".join(f"PO{po}/{aar}" for po, aar in ukjente) or "(ingen)")
    logg.valg("fasit.sikkerhet",
              _tell_sikkerhet(fasit))

    akva = akvakultur_naa(logg, akva_versjon)
    kart = po_kart(akva)
    bredde = bredde_kart(akva)
    kapasitet = kapasitet_kart(akva)
    temp = les_temp(logg, avg)
    rader = les_uker(logg, avg, kart, temp)
    bio = les_fisk(logg, avg, bio_versjon)
    logg.valg("resultat.lokalitet_uker", len(rader))
    logg.valg("resultat.po_maaneder_biomasse", len(bio.fisk))
    print(f"Leste {len(rader)} lokalitet-uker, {avg.fra_aar}-{avg.til_aar}, "
          f"og {len(bio.fisk)} PO-måneder biomasse.")

    dekning(rader)

    # Hovedtabellen bruker AGG_MAANED; AGG_VINDUSNITT regnes ut ved siden
    # av og sammenlignes i seksjon 2c. Begge kjøres fordi valget er reelt
    # tvilsomt — se `nfisk_for_uke`.
    pred = per_po_aar(rader, avg.vindu, bio, AGG_MAANED)
    pred_vs = per_po_aar(rader, avg.vindu, bio, AGG_VINDUSNITT)
    p14 = per_po_aar(rader, avg.vindu_vid, bio, AGG_MAANED)
    logg.valg("resultat.po_aar", len(pred))
    logg.valg("resultat.po_aar_med_nauplier",
              sum(1 for p in pred.values() if p["nauplier"] is not None))

    hvilke_inngangsdata(rader, bio, pred, avg)
    dekning_tre_ledd(pred, fasit, avg, bio)
    aggregeringsvariantene(pred, pred_vs, fasit)

    tabell_prediktorer(pred, fasit, avg.vindu)
    fordeling_per_kategori(pred, fasit, avg.vindu)
    fordeling_per_kategori(pred, fasit, avg.vindu, bare_verifisert=True)
    rangkorrelasjon(pred, fasit)
    foelsomhet(pred, p14, fasit)
    spesifikke_sporsmaal(pred, fasit, avg)
    baseline(fasit)

    treff = {}
    for felt, merkelapp, nr, navn in [
            ("snitt_uvektet", "lusetallet", "8b", "lusetall (snitt_uv)"),
            ("temp_snitt", "temperaturen", "8c", "temperatur"),
            ("stien_delvis", "den delvise proxyen", "8d", "DELVIS Stien-proxy"),
            ("n_fisk", "N_fisk alene", "8e", "N_fisk (PO-beholdning)"),
            ("nauplier", "den FULLE Stien-proxyen", "8f", "FULL Stien-proxy"),
            ("nauplier_per_lok", "FULL Stien per lokalitet", "8g",
             "FULL Stien per lokalitet"),
    ]:
        treff[navn] = retning_ved_skifte(pred, fasit, felt, merkelapp, nr)

    uro(rader, pred, avg)
    bredde_po = bredde_per_po(rader, bredde, avg)
    geografikontrollen(rader, pred, fasit, bredde_po, bredde, avg)
    skjevhetens_fortegn(rader, kapasitet, avg)
    null_kategorien(bio, avg)
    absolutt_eller_normalisert(pred, fasit)
    det_egentlige_sporsmaalet(pred, fasit, bredde_po, treff)
    notert_ikke_rettet()

    # Hovedtallene føres i loggen selv. Et resultat som ligger i en logg
    # over sine egne forutsetninger kan sammenlignes med neste kjøring
    # uten å lete i stdout — og det er nettopp det følsomhetskjøringen
    # med et annet `--biomasse-versjon` skal sammenlignes på.
    for felt in ["snitt_uvektet", "temp_snitt", "stien_delvis",
                 "n_fisk", "nauplier", "nauplier_per_lok"]:
        logg.valg(f"resultat.rho.{felt}", f"{_rho(pred, fasit, felt):+.3f}")
    logg.valg("resultat.rho.nauplier_vindusnitt",
              f"{_rho(pred_vs, fasit, 'nauplier'):+.3f}")
    for navn, (enige, n) in treff.items():
        logg.valg(f"resultat.skifter.{navn}", f"{enige}/{n}")

    sti = plott(pred, fasit, bredde_po, avg, logg)
    loggsti = logg.skriv()
    print(seksjon("PLOTT OG KJØRINGSLOGG"))
    print(f"  plott:        {sti}")
    print(f"  kjøringslogg: {loggsti}")
    print("\n  Loggen bærer alle valg som påvirket tallene over — vindu,")
    print("  avgrensning, mål, fasitens innholds-hash, PERSONFORMER, og")
    print("  hvilken snapshot-FIL hver dato ble lest fra, med løpenummer")
    print("  og published_at. Uten den er ingen av tallene reproduserbare.")
    print()
    print("  FØLSOMHET FOR BIOMASSEVERSJONEN kjøres som en EGEN kjøring, ikke")
    print("  som en variant inne i denne. `Kjoringslogg` nekter å lese samme")
    print("  kilde med to versjonsvalg i én kjøring — ellers ville halve")
    print("  resultatet hvilt på én påstand om fortiden og halve på en annen,")
    print("  uten at loggen kunne si hvilken halvdel som er hvilken:")
    print()
    print("    python analyse/lusepress_mot_fasit.py --biomasse-versjon forste \\")
    print("        --logg analyse/ut/lusepress-bio-forste.kjoring.log")
    print()
    print("  Sammenlign så `resultat.rho.*` i de to loggene.")
    return 0


def _tell_sikkerhet(fasit: dict) -> str:
    """`verifisert×43, utledet×13` — determinstisk, sortert."""
    antall: dict[str, int] = {}
    for v in fasit.values():
        antall[v["sikkerhet"]] = antall.get(v["sikkerhet"], 0) + 1
    return ", ".join(f"{k}×{n}" for k, n in sorted(antall.items()))


def _rho(pred: dict, fasit: dict, felt: str) -> float:
    """Samme regnestykke som seksjon 5, ett sted.

    Ligger her og ikke inne i `rangkorrelasjon()` fordi tallet skal både
    printes og føres i loggen, og to utregninger av samme tall kan svare
    ulikt. Det er formen F6, F7 og F8 hadde, i miniatyr.
    """
    par = [(p[felt], RANG[fasit[k]["kategori"]])
           for k, p in pred.items()
           if fasit.get(k, {}).get("kategori") in RANG and p.get(felt) is not None]
    return spearman([a for a, _ in par], [b for _, b in par]) if par else float("nan")


if __name__ == "__main__":
    raise SystemExit(main())
