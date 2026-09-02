"""Revisjonshistorikken samlet: hvem ombestemmer seg, hvor mye, og hvor sent.

    .venv/bin/python analyse/revisjoner.py

Leser `change_type = "revidert"` fra changeloggen og svarer på tre
spørsmål per kilde per år:

    HVOR MANGE   rader er endret etter første publisering
    HVOR MYE     er de typisk endret
    HVOR SENT    kom revisjonen, målt fra opprinnelig utgivelse

Det siste leddet er det minst opplagte og det mest interessante: en
revisjon to uker etter er en korreksjon, en to år etter er noe annet.

## Hvorfor forsinkelsen ikke kan leses av changelog-raden alene

Den kan for ekspertgruppen og ikke for biomasse, og forskjellen er verdt
å forstå før tallene leses.

En revisjonsrad bærer `published_at` og `forrige_published_at`. Er begge
satt, ER forsinkelsen differansen mellom dem, og ingenting mer trengs.
Det gjelder alle 26 ekspertgruppe-radene: rapportene bærer
`/CreationDate`, så begge påstandene vet når de ble utgitt.

For biomasse er `published_at` TOM på hver eneste av de 1809 radene.
Ikke fordi noe mangler i changeloggen, men fordi den nyere påstanden er
et snapshot skrevet FØR `published_at` fantes som felt — og CLAUDE.md
1b-7 sier uttrykkelig at slike ikke fylles inn retroaktivt. Ville vi
gjort det, hadde 103 biomasse-snapshots PÅSTÅTT at Fiskeridirektoratet
utga tallene den dagen VI hentet dem.

Derfor leses forsinkelsen HER av `snapshot.publisert()`, som er repoets
egen regel for «når ble denne påstanden utgitt»: `published_at` der den
finnes, ellers `fetched_at` som ØVRE GRENSE. En forsinkelse regnet med
den reserven er da også en øvre grense, og den merkes som det framfor å
bli oppgitt som et punkt.

## Løpenummeret er ikke rekkefølgen

Dette er F14 i praksis, og det er derfor versjonene sorteres på
`publisert()` og aldri på filnavn. For biomasse 2017-10-31:

    v2  (.2.parquet)   publisert 2024-07-20   <- ELDST
    v1  (.parquet)     publisert 2026-08-25   <- NYEST

Wayback-kopien har det høyeste løpenummeret og den eldste påstanden.
Sorterer man på filnavn, går forsinkelsen baklengs og blir negativ.
"""

from __future__ import annotations

import datetime as dt
import statistics as st
import sys
from pathlib import Path

import polars as pl

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from core import changelog, diff, snapshot        # noqa: E402

REVIDERT = diff.REVIDERT


def _tid(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _tall(s: str) -> float | None:
    """Verdien som tall, eller None. Tåler komma og prosentfortegn.

    Ikke alle felter ER tall — `kategori` er «moderat», `retning` er
    «opp». De faller ut av størrelsesmålet og telles for seg, framfor å
    bli tvunget til 0 og trekke medianen ned.
    """
    if s is None:
        return None
    t = s.strip().replace(" ", "").replace(" ", "").replace(",", ".")
    t = t.lstrip("<>").rstrip("%")
    try:
        return float(t)
    except ValueError:
        return None


class Tidslinje:
    """Utgivelsestidspunktene for hver (kilde, observed_at), eldst først.

    Slås opp én gang og gjenbrukes: `snapshot.versjoner()` leser
    parquetfiler fra disk, og revisjonsradene for én dato er mange.
    """

    def __init__(self) -> None:
        self._buffer: dict[tuple[str, str], list] = {}

    def versjoner(self, kilde: str, dato: str) -> list:
        n = (kilde, dato)
        if n not in self._buffer:
            par = [(snapshot.publisert(r), snapshot.published_at_i(r), v, r)
                   for v, r in snapshot.versjoner(kilde, dato)]
            # SORTERT PÅ publisert(), ikke på løpenummer. Se modulens
            # docstring — det er hele F14.
            self._buffer[n] = sorted(par, key=lambda p: p[0] or "")
        return self._buffer[n]

    def spenn(self, kilde: str, dato: str):
        """(eldste, nyeste, er_ovre_grense) for utgivelsene av én dato."""
        v = self.versjoner(kilde, dato)
        if len(v) < 2:
            return None
        eldst, nyest = v[0], v[-1]
        # Er den NYESTE påstandens utgivelse ukjent, er differansen en
        # øvre grense og ikke et punkt.
        return _tid(eldst[0]), _tid(nyest[0]), nyest[1] is None


def hent_revisjoner() -> pl.DataFrame:
    alle = changelog.les_alt()
    if alle.is_empty() or "change_type" not in alle.columns:
        return alle
    return alle.filter(pl.col("change_type") == REVIDERT)


def sammendrag(rev: pl.DataFrame, tid: Tidslinje | None = None) -> list[dict]:
    """Én rad per (kilde, år): antall, størrelse og forsinkelse."""
    if rev.is_empty():
        return []
    tid = tid or Tidslinje()
    rev = rev.with_columns(
        pl.col("observed_at").str.slice(0, 4).alias("aar"))

    ut = []
    for (kilde, aar), del_ in sorted(
            rev.group_by("kilde_aar" if False else ["source", "aar"]),
            key=lambda p: (p[0][0], p[0][1])):
        endringer, dager, grense = [], [], False
        for rad in del_.iter_rows(named=True):
            g, n = _tall(rad["old_value"]), _tall(rad["new_value"])
            if g is not None and n is not None and g != 0:
                endringer.append(abs(n - g) / abs(g))
            sp = tid.spenn(kilde, rad["observed_at"])
            if sp and sp[0] and sp[1]:
                dager.append((sp[1] - sp[0]).days)
                grense = grense or sp[2]
        ut.append({
            "kilde": kilde,
            "aar": aar,
            "rader": del_.height,
            "enheter": del_["entity_id"].n_unique(),
            "felter": del_["field"].n_unique(),
            "numeriske": len(endringer),
            "median_endring": st.median(endringer) if endringer else None,
            "storste_endring": max(endringer) if endringer else None,
            "dager_median": int(st.median(dager)) if dager else None,
            "dager_min": min(dager) if dager else None,
            "dager_maks": max(dager) if dager else None,
            "er_ovre_grense": grense,
        })
    return ut


def verifiser(rev: pl.DataFrame, antall: int = 5,
              tid: Tidslinje | None = None) -> list[dict]:
    """Spor N revisjonsrader tilbake til de to snapshotene de ligger mellom.

    Påstanden dette prosjektet hviler på er at ingen andre har tatt vare
    på de gamle versjonene. Den holder bare hvis hver revisjonsrad kan
    spores til de to snapshotene den ligger mellom — og det må LESES av
    dataene, ikke sluttes av koden som skrev dem.

    For hver rad: finn eldste og nyeste påstand om samme `observed_at`,
    og sjekk at `old_value` faktisk står i den FØRSTE og `new_value` i
    den ANDRE, for samme (entity_id, field).

    F14 er nettopp denne feilklassen: `previous()` og `les_mellom()`
    sorterte på filnavn framfor utgivelse, og 1805 changelog-rader
    oppga en to år gammel verdi som forrige måneds tall. En verifisering
    som SELV sorterte på filnavn ville bekreftet feilen.
    """
    tid = tid or Tidslinje()
    ut = []
    # Utvalget skal spenne over KILDENE og ikke bare over radene.
    # Biomasse har 1809 av 1835 rader, så et jevnt streifutvalg treffer
    # bare biomasse — og da er ekspertgruppens revisjonsakse uprøvd.
    # Hver kilde bidrar med minst én, resten fordeles.
    kilder = sorted(rev["source"].unique().to_list())
    per_kilde = []
    for kilde in kilder:
        d = rev.filter(pl.col("source") == kilde)
        steg = max(1, d.height // max(1, antall))
        per_kilde.append([d.row(i, named=True)
                          for i in range(0, d.height, steg)])
    # RUNDGANG mellom kildene, ikke kvote etter andel. En kvote etter
    # andel gir ekspertgruppen 26/1835 av fem rader, altså null, og da
    # er den ene aksen som faktisk bærer BEGGE utgivelsestidspunktene
    # aldri prøvd.
    plukk = []
    for i in range(max(len(k) for k in per_kilde)):
        for k in per_kilde:
            if i < len(k):
                plukk.append(k[i])
    for rad in plukk[:antall]:
        kilde, dato = rad["source"], rad["observed_at"]
        versjoner = tid.versjoner(kilde, dato)
        if len(versjoner) < 2:
            ut.append({**_kort(rad), "utfall": "FÆRRE ENN TO VERSJONER"})
            continue
        (p_eldst, _, v_eldst, r_eldst) = versjoner[0]
        (p_nyest, _, v_nyest, r_nyest) = versjoner[-1]

        def slaa_opp(ramme):
            t = ramme.filter((pl.col("entity_id") == rad["entity_id"])
                             & (pl.col("field") == rad["field"]))
            return None if t.is_empty() else t["value"][0]

        gammel_pa_disk = slaa_opp(r_eldst)
        ny_pa_disk = slaa_opp(r_nyest)
        # "null" i changeloggen betyr at feltet ikke fantes på den siden.
        forventet_gammel = None if rad["old_value"] == "null" else rad["old_value"]
        forventet_ny = None if rad["new_value"] == "null" else rad["new_value"]
        ok = (gammel_pa_disk == forventet_gammel
              and ny_pa_disk == forventet_ny)
        ut.append({
            **_kort(rad),
            "eldst_versjon": v_eldst, "eldst_publisert": p_eldst,
            "nyest_versjon": v_nyest, "nyest_publisert": p_nyest,
            "gammel_pa_disk": gammel_pa_disk,
            "ny_pa_disk": ny_pa_disk,
            "utfall": "OK" if ok else "AVVIK",
        })
    return ut


def _kort(rad: dict) -> dict:
    return {k: rad[k] for k in
            ("source", "entity_id", "entity_name", "field",
             "old_value", "new_value", "observed_at")}


def eksempel_po9() -> dict | None:
    """PO9, vurderingsåret 2024 — ett produksjonsområde, én verdi.

    2024-rapporten NEKTET å velge: PO9 sto som «Lav til moderat» i
    `kategori_ordrett`, og feltet `kategori` var tomt. 2025-rapportens
    kapittel 6.1 «Oppdaterte hovedkonklusjoner for 2024» avgjorde det til
    moderat, ett år senere.

    Det er hele prosjektet på ti sekunder: kilden uttalte seg om 2024 to
    ganger, med ett års mellomrom, og bare den som tok vare på den første
    påstanden kan se at den ble endret.
    """
    rev = hent_revisjoner()
    t = rev.filter((pl.col("source") == "ekspertgruppen")
                   & (pl.col("entity_id") == "9")
                   & (pl.col("field") == "kategori")
                   & (pl.col("observed_at").str.starts_with("2024")))
    if t.is_empty():
        return None
    rad = t.row(0, named=True)
    ordrett = None
    for _, ramme in snapshot.versjoner("ekspertgruppen", rad["observed_at"]):
        d = ramme.filter((pl.col("entity_id") == "9")
                         & (pl.col("field") == "kategori_ordrett"))
        if not d.is_empty():
            ordrett = d["value"][0]
            break
    gml, ny = _tid(rad["forrige_published_at"]), _tid(rad["published_at"])
    return {
        **_kort(rad),
        "kategori_ordrett_2024": ordrett,
        "utgitt_forst": rad["forrige_published_at"],
        "utgitt_revidert": rad["published_at"],
        "dager": (ny - gml).days if gml and ny else None,
    }


def main() -> int:
    rev = hent_revisjoner()
    print(f"\n{'='*76}\nRevisjonssammendrag\n{'='*76}")
    print(f"\n  revisjonsrader i changeloggen: {rev.height}")
    if rev.is_empty():
        print("  Ingen kilde har ombestemt seg ennå.")
        return 0

    tid = Tidslinje()
    print(f"\n{'-'*76}")
    print(f"  {'kilde':<16}{'år':<6}{'rader':>7}{'omr.':>6}{'felt':>6}"
          f"{'median endr.':>14}{'dager (min-median-maks)':>26}")
    print(f"{'-'*76}")
    for r in sammendrag(rev, tid):
        endr = ("—" if r["median_endring"] is None
                else f"{r['median_endring']*100:.2f} %")
        if r["dager_median"] is None:
            dager = "—"
        else:
            merke = " (≤)" if r["er_ovre_grense"] else ""
            dager = (f"{r['dager_min']}-{r['dager_median']}-"
                     f"{r['dager_maks']}{merke}")
        print(f"  {r['kilde']:<16}{r['aar']:<6}{r['rader']:>7}"
              f"{r['enheter']:>6}{r['felter']:>6}{endr:>14}{dager:>26}")
    print(f"{'-'*76}")
    print("  (≤) forsinkelsen er en ØVRE GRENSE: den nyere påstandens")
    print("      utgivelsestidspunkt er ukjent, og fetched_at brukes som")
    print("      grense. Se modulens docstring.")

    print(f"\n{'='*76}\nVerifisering — fem rader sporet til snapshotene\n{'='*76}")
    feil = 0
    sjekk = verifiser(rev, 5, tid)
    antall_sjekket = len(sjekk)
    for v in sjekk:
        print(f"\n  {v['source']} / {v['observed_at']} / "
              f"{v['entity_id']} / {v['field']}")
        print(f"      changelog sier : {v['old_value']!r} -> {v['new_value']!r}")
        if v["utfall"] == "FÆRRE ENN TO VERSJONER":
            print("      FÆRRE ENN TO VERSJONER PÅ DISK")
            feil += 1
            continue
        print(f"      eldste snapshot: v{v['eldst_versjon']} utgitt "
              f"{v['eldst_publisert']}  ->  {v['gammel_pa_disk']!r}")
        print(f"      nyeste snapshot: v{v['nyest_versjon']} utgitt "
              f"{v['nyest_publisert']}  ->  {v['ny_pa_disk']!r}")
        print(f"      {v['utfall']}")
        feil += v["utfall"] != "OK"
    print(f"\n  {antall_sjekket - feil}/{antall_sjekket} rader gjenfunnet "
          f"i snapshotene, lest av dataene og ikke av koden.")

    e = eksempel_po9()
    if e:
        print(f"\n{'='*76}\nEksempel: PO9, vurderingsåret 2024\n{'='*76}")
        print(f"  {e['entity_name']} (PO{e['entity_id']})")
        print(f"  2024-rapporten skrev  : kategori_ordrett = "
              f"{e['kategori_ordrett_2024']!r} — kilden valgte ikke")
        print(f"                          kategori = (tom)")
        print(f"  2025-rapporten skrev  : kategori = {e['new_value']!r}")
        print(f"  utgitt første gang    : {e['utgitt_forst']}")
        print(f"  utgitt revidert       : {e['utgitt_revidert']}")
        print(f"  forsinkelse           : {e['dager']} dager")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
