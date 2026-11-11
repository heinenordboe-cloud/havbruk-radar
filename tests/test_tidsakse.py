"""Tidsaksen: prøvene som må holde (økt 7, punkt 3).

To slag. De SYNTETISKE bygger aksen av noen få snapshots skrevet med
`snapshot.write()` i en tom mappe, og kjører overalt. Prøvene MOT
DATAREPOET bygger hele aksen av de ekte snapshotene og holder den mot R2
(havbruk-analyse analyse/a2-uenige-registre/) og beslutningene for økta;
de hoppes over uten datarepoet ved siden av (Actions), som
tests/test_havbruksfond.py.

Oppdragets prøver, og hvor de står:

    antall rader = lokaliteter × uker       test_rutenettet_*
    71/26 kommer ut som konflikter, eller
    avviket er forklart                     test_71_26_*
    Hendneset (10204) og Hillersvik (10300) test_hendneset_*, test_hillersvik_*
    ingen uke før 17.08.2026 har eierkobling test_ingen_eierkobling_*
    de sju 2026-cellene: ordlyd og kilde     test_de_sju_2026_cellene_*
    ingen personnavn i noen kolonne          test_ingen_personnavn_*
    samme input gir samme sha256             test_samme_input_*

Prøvene mot R2 bygger aksen slik vi kjente den 04.11.2026 06:00 UTC
(`kjent_til`), R2s datagrunnlag. Da kan en ny henting ikke felle dem av
en riktig grunn, og en endring i koden kan ikke skjule seg bak ny data.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import polars as pl
import pytest

import paastand
import publiseringsvakt
import tidsakse
from analyse import kjoringslogg
from core import paths, snapshot
from core.contract import Observation

DATAREPO = Path(__file__).resolve().parent.parent.parent / "havbruk-radar-data" / "data"
trenger_data = pytest.mark.skipif(
    not (DATAREPO / "raw" / "lusetall").exists()
    or not (DATAREPO / "arkiv" / tidsakse.SYKDOM_KROPP).exists(),
    reason="datarepoet ligger ikke ved siden av")

R2_KJENT_TIL = "2026-11-04T06:00:00+00:00"


# ------------------------------------------------------------ syntetisk


@pytest.fixture
def tom(tmp_path, monkeypatch):
    import nettsted
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(paths, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(nettsted, "DATA_DIR", tmp_path)
    return tmp_path


def _skriv(kilde: str, dato: str, rader: dict[str, dict[str, object]],
           typ: str = "lokalitet") -> None:
    obs = [Observation(entity_id=e, entity_type=typ, entity_name="", field=f,
                       value=str(v), source=kilde, observed_at=dato,
                       fetched_at=f"{dato}T12:00:00+00:00", source_version="1",
                       raw_hash="h", utvalg="{}")
           for e, felt in rader.items() for f, v in felt.items()]
    snapshot.write(obs, dato)


def _lus(brakk: bool, lus: str | None = None) -> dict[str, object]:
    rad = {"brakklagt": brakk, "har_laksefisk": True, "er_landbasert": False,
           "er_slaktemerd": False, "lus_er_rapportert": lus is not None,
           "har_mekanisk_fjerning": False, "har_medikamentell_behandling": False,
           "har_rensefisk": False}
    if lus is not None:
        rad["voksne_hunnlus"] = lus
    return rad


UKER = ("2012-01-02", "2012-01-09", "2012-01-16")


def _tre_uker() -> None:
    """10001 mangler i uke 2. 10002 er brakklagt i uke 3. 10003 står bare i
    eierskap, i et snapshot fra før eierkoblingen fantes, og blir derfor
    ingen rad."""
    _skriv("lusetall", UKER[0], {"10001": _lus(False, "0.1"), "10002": _lus(False, "0.6")})
    _skriv("lusetall", UKER[1], {"10002": _lus(False, "0.2")})
    _skriv("lusetall", UKER[2], {"10001": _lus(True), "10002": _lus(True)})
    for u in UKER:
        # Samme uker som lusetall: BarentsWatch-eksporten mangler 10001 i
        # uke 2 også.
        _skriv("sjotemperatur", u, {lok: {"lusegrense": "0.5"} for lok in ("10001", "10002")
                                    if not (lok == "10001" and u == UKER[1])})
    _skriv("eierskap", UKER[1], {"T-1": {"eier_orgnr": "999999999", "lokaliteter": "10003",
                                         "eier_type": "LimitedLiabilityCompany"}},
           typ="tillatelse")


def _bygg(ut: Path, kjent_til: str | None = None) -> tidsakse.Resultat:
    return tidsakse.bygg(kjent_til=kjent_til,
                         logg=kjoringslogg.Kjoringslogg("tidsakse", ut / tidsakse.LOGGNAVN))


def test_rutenettet_er_lokaliteter_ganger_uker_syntetisk(tom):
    _tre_uker()
    t = _bygg(tom / "ut").tabell
    assert sorted(t["lokalitet"].unique().to_list()) == ["10001", "10002"]
    assert t["mandag"].unique().sort().to_list() == list(UKER)
    assert t.height == 2 * 3
    assert t.group_by("mandag").len()["len"].to_list() == [2, 2, 2]
    assert t.select("lokalitet", "mandag").is_unique().all()


def test_en_uke_uten_laget_er_tom_ikke_fylt(tom):
    """10001 mangler i uke 2: lusecellene er tomme, ikke uke 1 eller 3, og
    stripa sier «ukjent», hull — innenfor spennet."""
    _tre_uker()
    t = _bygg(tom / "ut").tabell
    rad = t.filter((pl.col("lokalitet") == "10001") & (pl.col("mandag") == UKER[1])).row(0, named=True)
    assert rad["lus__kilde"] is None and rad["lus__brakklagt"] is None
    assert rad["lus__voksne_hunnlus"] is None and rad["sjo__lusegrense"] is None
    assert (rad["stripe__grunn"], rad["stripe__grunn_ukjent"]) == ("ukjent", "hull")


def test_cellen_har_verdi_kilde_og_gjelder(tom):
    _tre_uker()
    t = _bygg(tom / "ut").tabell
    rad = t.filter((pl.col("lokalitet") == "10002") & (pl.col("mandag") == UKER[0])).row(0, named=True)
    assert (rad["lus__voksne_hunnlus"], rad["lus__kilde"], rad["lus__gjelder"]) == (
        "0.6", "lusetall", UKER[0])
    p = tidsakse.paastand_for(rad, "lus", "brakklagt")
    assert p == paastand.Paastand("brakklagt", "lusetall", UKER[0], "False",
                                  nivaa=paastand.VURDERT, felt="brakklagt",
                                  periode=paastand.UKE)
    assert tidsakse.paastand_for(rad, "register", "kapasitet") is None


def test_fravaer_er_ikke_brakklegging(tom):
    """10002 går fra drift til brakk i uke 3: én hendelse. 10001 mangler i
    uke 2 og er brakklagt i uke 3: ingen, for uka før er ikke «drift»."""
    _tre_uker()
    h = _bygg(tom / "ut").hendelser
    brakk = h.filter(pl.col("r9") == "H3")
    assert brakk.select("lokalitet", "mandag").rows() == [("10002", UKER[2])]
    over = h.filter(pl.col("r9") == "H2")
    assert over.select("lokalitet", "mandag").rows() == [("10002", UKER[0])]
    assert set(h["forste_omtale"].to_list()) == {tidsakse.UBELAGT}


def test_ingen_eierkobling_foer_17_08_2026_syntetisk(tom):
    """Et eierskapssnapshot fra 2012 gir ingen eier i tidsaksen."""
    _tre_uker()
    t = _bygg(tom / "ut").tabell
    assert t["eierskap__eier_orgnr"].drop_nulls().is_empty()
    assert t["eierskap__kilde"].drop_nulls().is_empty()


def test_samme_input_gir_samme_sha256_syntetisk(tom):
    _tre_uker()
    a = tidsakse.skriv(_bygg(tom / "a"), tom / "a")
    b = tidsakse.skriv(_bygg(tom / "b"), tom / "b")
    assert a == b


def test_kjent_til_tar_bare_det_vi_hadde(tom):
    """Uke 3 hentet 16.01 kl. 12: kjent til 16.01 kl. 11 har den ikke."""
    _tre_uker()
    t = _bygg(tom / "ut", kjent_til="2012-01-16T11:00:00+00:00").tabell
    assert t["mandag"].max() == UKER[1]


# ------------------------------------------------------- mot datarepoet


def _monkeypatch_datarepo(mp: pytest.MonkeyPatch) -> None:
    import nettsted
    mp.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
    mp.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
    mp.setattr(nettsted, "DATA_DIR", DATAREPO)


@pytest.fixture(scope="module")
def ekte(tmp_path_factory):
    """Hele tidsaksen av datarepoet slik det står, skrevet til disk."""
    mp = pytest.MonkeyPatch()
    _monkeypatch_datarepo(mp)
    ut = tmp_path_factory.mktemp("tidsakse")
    res = _bygg(ut)
    summer = tidsakse.skriv(res, ut)
    yield res, summer, ut
    mp.undo()


@pytest.fixture(scope="module")
def r2(tmp_path_factory):
    """Tidsaksen slik vi kjente den 04.11.2026 06:00 UTC, R2s grunnlag."""
    mp = pytest.MonkeyPatch()
    _monkeypatch_datarepo(mp)
    ut = tmp_path_factory.mktemp("tidsakse-r2")
    res = _bygg(ut, kjent_til=R2_KJENT_TIL)
    yield res
    mp.undo()


@trenger_data
def test_rutenettet_er_lokaliteter_ganger_uker(ekte):
    """Én rad per (lokalitet, uke), og hver uke på aksen har alle
    lokalitetene — også ukene der et lag ikke finnes."""
    t = ekte[0].tabell
    n_lok, n_uke = t["lokalitet"].n_unique(), t["mandag"].n_unique()
    assert t.height == n_lok * n_uke
    assert set(t.group_by("mandag").len()["len"].to_list()) == {n_lok}
    assert t.select("lokalitet", "mandag").is_unique().all()
    forventet = tidsakse.mandager(tidsakse.AKSE_START, t["mandag"].max())
    assert t["mandag"].unique().sort().to_list() == forventet
    # Hvert lag står bare i uker på aksen, og hver uke laget finnes, har
    # rutenettet alle lokalitetene, ikke bare dem laget har.
    for lag in tidsakse.LAG:
        uker = t.filter(pl.col(tidsakse.kolonne(lag, "kilde")).is_not_null())["mandag"].unique()
        assert set(uker.to_list()) <= set(forventet), lag
        assert set(t.filter(pl.col("mandag").is_in(uker.to_list()))
                   .group_by("mandag").len()["len"].to_list()) <= {n_lok}, lag


def _felt(ramme: pl.DataFrame, navn: str) -> dict[str, str]:
    r = ramme.filter(pl.col("field") == navn)
    return dict(zip(r["entity_id"].to_list(), r["value"].to_list()))


@trenger_data
def test_71_26_er_forklart_som_i_r2(r2):
    """71/26 er ikke konflikter, og tidsaksen viser hvorfor (R2 F1.1, F1.2).

    Talt som 14.10 (lusetallsuke 38 mot biomasselaget 12.10, uten univers
    og art) er det 71 «fisk/brakk» og 26 «tom/drift». I tidsaksen står
    en biomasserapport i uka med månedsslutten, og uke 38 har ingen. De
    71 deler seg som R2 delte dem: 42 utenfor BarentsWatchs univers, 13 i
    konflikt også i samme periode, 13 enige da, og 3 med rapport fra før
    uke 34. Konfliktene i samme periode er R2s 22 og 16.
    """
    mp = pytest.MonkeyPatch()
    _monkeypatch_datarepo(mp)
    try:
        lus = snapshot.versjoner("lusetall", "2026-09-14")[-1][1]
        bio = snapshot.versjoner("biomasselag", "2026-10-12")[-1][1]
    finally:
        mp.undo()
    brakk, fisk = _felt(lus, "brakklagt"), _felt(bio, "har_fisk")
    rapport, arter = _felt(bio, "siste_rapport"), _felt(bio, "arter_tilstede")
    begge = set(brakk) & set(fisk)
    fb = sorted(s for s in begge if fisk[s] == "Ja" and brakk[s] == "True")
    td = sorted(s for s in begge if fisk[s] == "Nei" and brakk[s] == "False")
    assert (len(begge), len(fb), len(td)) == (1073, 71, 26)

    t, k = r2.tabell, r2.konflikter
    # Uke 38 har ingen P3-konflikt: biomasselaget har ingen påstand i uka.
    # De eneste konfliktene der er de fire PD-lokalitetene (sykdom).
    assert k.filter((pl.col("uke") == "2026-W38") & (pl.col("par") == "P3")).is_empty()
    assert sorted(t.filter(pl.col("uke") == "2026-W38")["konflikt"].drop_nulls().to_list()) == [
        "sykdom"] * 4
    grunn38 = dict(t.filter(pl.col("uke") == "2026-W38").select("lokalitet", "stripe__grunn").rows())
    p3 = {(a, b) for a, b in k.filter(pl.col("par") == "P3").select("lokalitet", "mandag").rows()}
    sammenlignbar = {(a, b) for a, b in t.filter(
        pl.col("biomasselag__kilde").is_not_null() & pl.col("lus__kilde").is_not_null()
        & (pl.col("stripe__grunn") != "utenfor")).select("lokalitet", "mandag").rows()}
    r2_ukene = {"2026-08-31", "2026-09-28"}       # månedsslutter i uke 34–41
    deler = Counter()
    for s in fb:
        art = frozenset(a.strip() for a in (arter.get(s) or "").split(";") if a.strip())
        mandag = tidsakse.mandag_av(rapport[s])
        if grunn38.get(s) == "utenfor":
            deler["utenfor universet"] += 1
        elif not art & paastand.LAKSEFISK:
            deler["art ikke laksefisk"] += 1
        elif mandag in r2_ukene:
            deler["konflikt også da" if (s, mandag) in p3 else
                  "enige da" if (s, mandag) in sammenlignbar else "ikke sammenlignbar"] += 1
        elif mandag < tidsakse.mandag_av("2026-08-17"):
            deler["rapport før uke 34"] += 1
        else:
            deler["uke uten lusetall"] += 1
    assert deler == {"utenfor universet": 42, "konflikt også da": 13,
                     "enige da": 13, "rapport før uke 34": 3}

    per_uke = Counter(k.filter(pl.col("par") == "P3").select("uke", "merknad").rows())
    assert (per_uke[("2026-W36", "fisk/brakk")], per_uke[("2026-W36", "tom/drift")]) == (19, 3)
    assert (per_uke[("2026-W40", "fisk/brakk")], per_uke[("2026-W40", "tom/drift")]) == (15, 1)


@trenger_data
def test_hendneset_er_ja_kveite_ved_brakklagt_uke_1_uten_konflikt(r2):
    """R2 F1.2 og F6.3: «Ja, Kveite» 31.12.2025 står i uke 1/2026 ved
    BarentsWatchs «brakklagt», og er ingen konflikt: BarentsWatch uttaler
    seg ikke om kveite på land."""
    rad = r2.tabell.filter((pl.col("lokalitet") == "10204")
                           & (pl.col("uke") == "2026-W01")).row(0, named=True)
    assert (rad["biomasselag__har_fisk"], rad["biomasselag__arter_tilstede"],
            rad["biomasselag__gjelder"]) == ("Ja", "Kveite", "2025-12-31")
    assert rad["lus__brakklagt"] == "True"
    assert (rad["lus__har_laksefisk"], rad["lus__er_landbasert"]) == ("False", "True")
    assert rad["stripe__grunn"] == "utenfor"
    assert rad["konflikt"] is None
    assert r2.konflikter.filter(pl.col("lokalitet") == "10204").is_empty()


@trenger_data
def test_hillersvik_er_uenig_i_uke_40_og_ikke_i_uke_36(r2):
    """R2 F1.2, F1.3 og F6.3: «Ja, Laks» 30.09 mot «brakklagt» i uke 40 er
    en konflikt. Ved 31.08 er de enige."""
    t = r2.tabell.filter(pl.col("lokalitet") == "10300")
    u40 = t.filter(pl.col("uke") == "2026-W40").row(0, named=True)
    assert (u40["biomasselag__har_fisk"], u40["biomasselag__arter_tilstede"],
            u40["biomasselag__gjelder"], u40["lus__brakklagt"]) == (
        "Ja", "Laks", "2026-09-30", "True")
    assert u40["stripe__grunn"] == "brakk" and u40["konflikt"] == "P3"
    k = r2.konflikter.filter(pl.col("lokalitet") == "10300")
    assert k.select("par", "uke", "merknad", "b_kilde").rows() == [
        ("P3", "2026-W40", "fisk/brakk", "lusetall")]
    u36 = t.filter(pl.col("uke") == "2026-W36").row(0, named=True)
    assert u36["biomasselag__gjelder"] == "2026-08-31" and u36["konflikt"] is None


@trenger_data
def test_ingen_eierkobling_foer_17_08_2026(ekte):
    """M25: koblingen lokalitet–tillatelse–innehaver finnes fra 17.08.2026,
    og ingen uke før har den — verken innehaveren, tillatelsene på
    lokaliteten eller selskapet bak."""
    t = ekte[0].tabell.filter(pl.col("mandag") < tidsakse.mandag_av(tidsakse.EIERKOBLING_FRA))
    assert t.height > 0
    for kol in ("eierskap__kilde", "eierskap__eier_orgnr", "eierskap__selskap_orgnr",
                "eierskap__tillatelser", "register__tillatelser", "selskap__kilde"):
        assert t[kol].drop_nulls().is_empty(), kol
    assert ekte[0].hendelser.filter((pl.col("r9") == "H9")
                                    & (pl.col("forste_fil") < "raw/eierskap/2026-08-17")).is_empty()


@trenger_data
def test_de_sju_2026_cellene_har_ordlyd_og_kilde_ingen_farge(ekte):
    """Beslutningen: PO 2 og 6–11 i runde 2026 får ingen farge, men
    forskriftens ordlyd som kapasitetsjustering, med forskriften som kilde.
    De seks andre har fargen forskriften gir."""
    t = ekte[0].tabell.filter(pl.col("trafikklys__runde") == "2026")
    per_po = {po: rader for po, rader in t.group_by("sted__prodomraade_kode")}
    celler = t.select("sted__prodomraade_kode", "trafikklys__farge",
                      "trafikklys__kapasitetsjustering", "trafikklys__forskrift",
                      "trafikklys__kilde", "trafikklys__gjelder").unique()
    sju = celler.filter(pl.col("sted__prodomraade_kode").is_in(["2", "6", "7", "8", "9", "10", "11"]))
    assert sorted(sju["sted__prodomraade_kode"].to_list(), key=int) == ["2", "6", "7", "8", "9", "10", "11"]
    assert sju["trafikklys__farge"].null_count() == 7
    assert set(sju["trafikklys__kapasitetsjustering"].to_list()) == {tidsakse.ORDLYD_2026}
    assert set(sju["trafikklys__forskrift"].to_list()) == {tidsakse.FORSKRIFT_2026}
    assert set(sju["trafikklys__kilde"].to_list()) == {"trafikklysvedtak"}
    assert set(sju["trafikklys__gjelder"].to_list()) == {"2026-08-20"}
    seks = dict(celler.filter(~pl.col("sted__prodomraade_kode").is_in(sju["sted__prodomraade_kode"].to_list()))
                .select("sted__prodomraade_kode", "trafikklys__farge").rows())
    assert seks == {"1": "gronn", "3": "rod", "4": "gul", "5": "gul", "12": "gronn", "13": "gronn"}
    assert len(per_po) == 13
    # Registerets «GUL» for de sju står ikke noe sted i tidsaksen.
    assert not [k for k in ekte[0].tabell.columns if "prodomraade_status" in k]
    # Ordlyden er LEST av kroppen, ikke bare en konstant.
    assert tidsakse.ordlyd_2026() == tidsakse.ORDLYD_2026


@trenger_data
def test_ingen_personnavn_i_noen_kolonne(ekte):
    """Ingen kolonne heter noe med navn, ingen verdi har formen
    «ETTERNAVN, FORNAVN» eller ender på en personform, og ingen orgnr i
    tidsaksen tilhører en personform hos noen av kildene.

    Navnereglene er publiseringsvaktens (`PERSONNAVN` mot hele cellen,
    `personform_i_navn`), prøvd på hver ulike verdi i hver tekstkolonne
    i alle tre filene.
    """
    res = ekte[0]
    for ramme in (res.tabell, res.hendelser, res.konflikter):
        assert not [k for k in ramme.columns if "navn" in k or "name" in k]
        for kol in ramme.columns:
            if ramme[kol].dtype != pl.Utf8:
                continue
            for v in ramme[kol].drop_nulls().unique().to_list():
                assert not publiseringsvakt.PERSONNAVN.fullmatch(v), (kol, "personnavn")
                assert not publiseringsvakt.personform_i_navn(v), (kol, "personform")

    from sources.eierskap import er_person
    mp = pytest.MonkeyPatch()
    _monkeypatch_datarepo(mp)
    try:
        former: dict[str, set[str]] = {}
        for kilde, felt in (("enhetsregisteret", "organisasjonsform"),
                            ("eierskap", "eier_type"), ("eierskap", "organisasjonsform")):
            for dato in snapshot.datoer(kilde):
                for _, r in snapshot.versjoner(kilde, dato):
                    nokkel = "entity_id" if kilde == "enhetsregisteret" else "eier"
                    if nokkel == "eier":
                        eier = _felt(r, "eier_orgnr")
                        for t, form in _felt(r, felt).items():
                            former.setdefault(eier.get(t, ""), set()).add(form)
                    else:
                        for o, form in _felt(r, felt).items():
                            former.setdefault(o, set()).add(form)
    finally:
        mp.undo()
    orgnr = set()
    for kol in ("eierskap__eier_orgnr", "eierskap__selskap_orgnr"):
        for v in res.tabell[kol].drop_nulls().unique().to_list():
            orgnr |= set(v.split(";"))
    assert orgnr
    personlige = sorted(o for o in orgnr if any(er_person(f) for f in former.get(o, ())))
    assert personlige == []


@trenger_data
def test_samme_input_gir_samme_sha256(ekte, tmp_path):
    """To bygginger av samme datarepo gir byte for byte samme filer."""
    _res, summer, _ut = ekte
    mp = pytest.MonkeyPatch()
    _monkeypatch_datarepo(mp)
    try:
        andre = tidsakse.skriv(_bygg(tmp_path), tmp_path)
    finally:
        mp.undo()
    assert andre == summer
    for navn, sha in summer.items():
        assert hashlib.sha256((tmp_path / navn).read_bytes()).hexdigest() == sha


@trenger_data
def test_sykdom_er_tom_foer_uke_48_2024_og_de_fire_er_konflikt(ekte):
    """Beslutningen for sykdom: dekning fra 26.11.2024, ukene før tomme,
    og de fire PD-lokalitetene står som konflikt fra de forsvant."""
    t, k = ekte[0].tabell, ekte[0].konflikter
    foer = t.filter(pl.col("mandag") < tidsakse.SYKDOM_FRA)
    assert foer["sykdom__kilde"].drop_nulls().is_empty()
    assert foer["stripe__sykdom"].drop_nulls().is_empty()
    syk = k.filter(pl.col("par") == "sykdom")
    assert sorted(syk["lokalitet"].unique().to_list()) == ["24456", "24696", "30437", "31959"]
    assert syk["uke"].min() == "2026-W11"
    assert set(syk["a_verdi"].str.slice(0, 2).to_list()) == {"PD"}


@trenger_data
def test_behandling_er_tom_etter_2023_ikke_nei(ekte):
    """R8 og `dodt_fra`: behandling lever 2012-01-02–2023-12-25. Etter er
    stripa tom, og medikamentflagget er tomt — ikke «nei», ikke False."""
    t = ekte[0].tabell
    etter = t.filter(pl.col("mandag") >= "2024-01-01")
    assert etter["stripe__behandling"].drop_nulls().is_empty()
    assert etter["lus__har_medikamentell_behandling"].drop_nulls().is_empty()
    foer = t.filter(pl.col("mandag") <= "2023-12-25")
    assert set(foer["stripe__behandling"].drop_nulls().unique().to_list()) == {"ja", "nei", "ukjent"}
    assert t.filter(pl.col("stripe__behandling").is_not_null())["mandag"].max() == "2023-12-25"
