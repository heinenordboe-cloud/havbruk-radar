"""Revisjonsaksen: to utsagn om SAMME tidspunkt, fra hver sin henting.

`compare()` går langs tida — hva sier kilden i dag som den ikke sa sist.
`revisjon()` går langs hentingene — hva sier kilden i dag om et tidspunkt
den allerede har uttalt seg om.

Testene her holder de to fra hverandre, fordi det er hele poenget: en
revisjon som lekker ut som "endret" er en påstand om at noe skjedde i
sjøen, og det gjorde det ikke.

Den siste testen kjører mot EKTE data — Fiskeridirektoratets biomassefil
slik den så ut 07.08.2024 mot slik den ser ut i dag — og er den eneste
som beviser at aksen fanger det den ble bygget for.
"""

from pathlib import Path

import polars as pl
import pytest

from core import changelog, diff, signals, snapshot
from core import raw as raw_arkiv
from core.contract import Observation


# ---- oppsett ---------------------------------------------------------

@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path


def _obs(entity_id="1", field="beholdning_antall", value="100",
         observed_at="2018-03-31", source="biomasse", navn="Ryfylket"):
    return Observation(
        entity_id=entity_id, entity_type="produksjonsomraade",
        entity_name=navn, field=field, value=value, source=source,
        observed_at=observed_at,
    )


def _skriv(observasjoner, observed_at, fetched_at="2024-08-07T00:00:00+00:00",
           source_version="1", utvalg="{}"):
    """Skriver et snapshot med eksplisitt proveniens. Returnerer stien."""
    from dataclasses import replace
    stemplet = [replace(o, fetched_at=fetched_at,
                        source_version=source_version, raw_hash="h",
                        utvalg=utvalg) for o in observasjoner]
    return snapshot.write(stemplet, observed_at)[0]


def _ramme(observasjoner, fetched_at="2026-08-25T00:00:00+00:00",
           source_version="1", utvalg="{}"):
    from dataclasses import replace
    return snapshot.to_frame([
        replace(o, fetched_at=fetched_at, source_version=source_version,
                raw_hash="h2", utvalg=utvalg) for o in observasjoner])


# ---- snapshot.forrige_versjon ----------------------------------------

def test_forrige_versjon_finner_samme_dato_ikke_forrige_dato(isolert):
    """Forskjellen på previous() og forrige_versjon() i én test.

    previous() ville gitt februar. Det er industriens bevegelse, ikke
    kildens revisjon.
    """
    _skriv([_obs(value="10", observed_at="2018-02-28")], "2018-02-28")
    _skriv([_obs(value="20", observed_at="2018-03-31")], "2018-03-31")

    forrige_dato = snapshot.previous("biomasse", before="2018-03-31")
    samme_dato = snapshot.forrige_versjon("biomasse", "2018-03-31")

    assert forrige_dato["observed_at"].to_list() == ["2018-02-28"]
    assert samme_dato["observed_at"].to_list() == ["2018-03-31"]


def test_forrige_versjon_velger_hoyeste_lopenummer(isolert):
    """`.10` sorterer etter `.2` tallmessig, ikke alfabetisk. Regelen
    finnes i _dato_og_versjon og skal ikke gjettes på nytt her."""
    for n, verdi in enumerate(["1", "2", "3"], start=1):
        _skriv([_obs(value=verdi)], "2018-03-31")

    filer = sorted(p.name for p in (snapshot.RAW_DIR / "biomasse").glob("*"))
    assert filer == ["2018-03-31.2.parquet", "2018-03-31.3.parquet",
                     "2018-03-31.parquet"]
    assert snapshot.forrige_versjon("biomasse", "2018-03-31")["value"][0] == "3"


def test_forrige_versjon_er_none_for_en_dato_som_ikke_finnes(isolert):
    """Ikke en revisjon — en førstegangsskriving, og den hører til
    compare()."""
    _skriv([_obs(observed_at="2018-02-28")], "2018-02-28")
    assert snapshot.forrige_versjon("biomasse", "2018-03-31") is None
    assert snapshot.forrige_versjon("finnesikke", "2018-03-31") is None


def test_datoer_teller_perioder_ikke_filer(isolert):
    _skriv([_obs(observed_at="2018-02-28")], "2018-02-28")
    _skriv([_obs()], "2018-03-31")
    _skriv([_obs(value="99")], "2018-03-31")
    assert snapshot.datoer("biomasse") == ["2018-02-28", "2018-03-31"]


def test_versjon_av_leser_lopenummeret(isolert):
    assert snapshot.versjon_av(Path("2018-03-31.parquet")) == 1
    assert snapshot.versjon_av(Path("2018-03-31.2.parquet")) == 2
    assert snapshot.versjon_av(Path("a/b/2018-03-31.10.parquet")) == 10


def test_proveniens_er_none_naar_radene_spriker(isolert):
    """Ett snapshot er ett kall. Spriker feltene, er rammen satt sammen —
    og da skal svaret være «vet ikke», ikke den første av flere."""
    from dataclasses import replace
    a = replace(_obs(), fetched_at="A", source_version="1")
    b = replace(_obs(entity_id="2"), fetched_at="B", source_version="2")
    blandet = snapshot.to_frame([a, b])
    assert snapshot.fetched_at_i(blandet) is None
    assert snapshot.source_version_i(blandet) is None

    ren = snapshot.to_frame([a, replace(b, fetched_at="A", source_version="1")])
    assert snapshot.fetched_at_i(ren) == "A"
    assert snapshot.source_version_i(ren) == "1"


# ---- diff.revisjon ---------------------------------------------------

def test_endret_verdi_samme_dato_blir_revidert(isolert):
    _skriv([_obs(value="18613010")], "2018-03-31",
           fetched_at="2024-08-07T00:00:00+00:00")

    rev = diff.revisjon(_ramme([_obs(value="17190233")]), "2018-03-31")

    assert rev.height == 1
    rad = rev.to_dicts()[0]
    assert rad["change_type"] == diff.REVIDERT
    assert (rad["old_value"], rad["new_value"]) == ("18613010", "17190233")
    # Samme dato på begge sider. Det ER revisjonen.
    assert rad["observed_at"] == rad["forrige_observed_at"] == "2018-03-31"
    # Og det eneste som skiller de to påstandene.
    assert rad["forrige_fetched_at"] == "2024-08-07T00:00:00+00:00"


def test_uendret_gir_ingen_revisjon(isolert):
    _skriv([_obs(value="100")], "2018-03-31")
    assert diff.revisjon(_ramme([_obs(value="100")]), "2018-03-31").is_empty()


def test_ingen_tidligere_versjon_gir_ingen_revisjon(isolert):
    """Førstegangsskriving er compare()s bord, ikke revisjonens."""
    assert diff.revisjon(_ramme([_obs()]), "2018-03-31").is_empty()


def test_nytt_feltnavn_er_var_skjemaendring_ikke_kildens_revisjon(isolert):
    """Legger vi til en kolonne i parseren, ville hver eneste måned fått
    en «revidert»-rad for det nye feltet — en påstand om at
    Fiskeridirektoratet endret noe VI endret."""
    _skriv([_obs(field="beholdning_antall", value="100")], "2018-03-31")

    rev = diff.revisjon(_ramme([
        _obs(field="beholdning_antall", value="100"),
        _obs(field="romming_antall", value="7"),
    ]), "2018-03-31")

    assert rev.is_empty()


def test_fjernet_feltnavn_er_ogsa_vart(isolert):
    """Symmetrisk: et felt vi sluttet å emitte er ikke kilden som
    slettet det."""
    _skriv([_obs(field="beholdning_antall", value="100"),
            _obs(field="forforbruk_kg", value="5.000")], "2018-03-31")

    rev = diff.revisjon(_ramme([_obs(field="beholdning_antall", value="100")]),
                        "2018-03-31")

    assert rev.is_empty()


def test_entitet_som_kommer_eller_gaar_ER_en_revisjon(isolert):
    """Filteret går på FELTNAVN, ikke på entiteter. At kilden flytter et
    produksjonsområde inn i eller ut av en måned er nettopp revisjonen —
    og old_value/new_value viser hvilken vei det gikk."""
    _skriv([_obs(entity_id="1", value="100"),
            _obs(entity_id="5", value="200")], "2018-03-31")

    rev = diff.revisjon(_ramme([
        _obs(entity_id="1", value="100"),
        _obs(entity_id="uten_po", value="200", navn="Uten produksjonsområde"),
    ]), "2018-03-31")

    per_entitet = {r["entity_id"]: r for r in rev.to_dicts()}
    assert set(per_entitet) == {"5", "uten_po"}
    assert all(r["change_type"] == diff.REVIDERT for r in per_entitet.values())
    assert per_entitet["5"]["new_value"] is None          # forsvant
    assert per_entitet["uten_po"]["old_value"] is None    # kom til


def test_ny_source_version_kaster_framfor_aa_anklage_kilden(isolert):
    """En forskjell kan da like gjerne være vår egen parser. Å skrive
    «kilden reviderte dette» ville vært feil om en tredjepart."""
    _skriv([_obs(value="100")], "2018-03-31", source_version="1")

    with pytest.raises(diff.Grunnlagssprik) as e:
        diff.revisjon(_ramme([_obs(value="200")], source_version="2"),
                      "2018-03-31")
    assert "source_version" in str(e.value)


def test_endret_utvalg_kaster_ogsa(isolert):
    _skriv([_obs(value="100")], "2018-03-31", utvalg='{"arter": ["LAKS"]}')

    with pytest.raises(diff.Grunnlagssprik) as e:
        diff.revisjon(_ramme([_obs(value="100"), _obs(entity_id="2")],
                             utvalg='{"arter": ["LAKS", "ORRET"]}'),
                      "2018-03-31")
    assert "utvalg" in str(e.value)


def test_sammenligner_mot_nyeste_versjon_ikke_den_forste(isolert):
    """Revisjonskjeden går fra ledd til ledd. Sammenlignet vi alltid mot
    basisfila, ville en revisjon blitt rapportert på nytt hver gang."""
    _skriv([_obs(value="10")], "2018-03-31")
    _skriv([_obs(value="20")], "2018-03-31",
           fetched_at="2025-01-01T00:00:00+00:00")

    rev = diff.revisjon(_ramme([_obs(value="30")]), "2018-03-31")

    rad = rev.to_dicts()[0]
    assert (rad["old_value"], rad["new_value"]) == ("20", "30")
    assert rad["forrige_fetched_at"] == "2025-01-01T00:00:00+00:00"


# ---- forholdet til resten av rørledningen -----------------------------

def test_revisjon_er_ikke_bevegelse(isolert):
    _skriv([_obs(value="10")], "2018-03-31")
    rev = diff.revisjon(_ramme([_obs(value="20")]), "2018-03-31")
    assert rev.height == 1
    assert diff.bevegelse(rev).is_empty()


def test_ingen_signalregel_treffer_en_revisjon(isolert):
    """Alle 24 reglene oppgir `endringstype`, så en ny verdi treffer
    ingen av dem før noen skriver en som ber om den. Samme mekanikk som
    utvalgsutvidelse — testen er her for at det skal FORBLI sant."""
    _skriv([_obs(field="kapasitet", value="1000")], "2018-03-31")
    rev = diff.revisjon(_ramme([_obs(field="kapasitet", value="5000")]),
                        "2018-03-31")

    scoret = signals.score(rev)
    assert scoret.height == rev.height          # ingen rader mistet
    assert signals.treff(scoret).is_empty()     # ingen regel traff


def test_compare_baerer_ogsa_forrige_fetched_at(isolert):
    """Feltet er nytt for hele skjemaet, ikke bare for revisjonsraden.
    Uten det kan to snapshots med samme observed_at ikke skilles."""
    _skriv([_obs(value="10", observed_at="2018-02-28")], "2018-02-28",
           fetched_at="2024-08-07T00:00:00+00:00")

    endr = diff.compare(_ramme([_obs(value="20")]), "2018-03-31")

    assert endr.to_dicts()[0]["forrige_fetched_at"] == \
        "2024-08-07T00:00:00+00:00"


def test_snapshot_uten_fetched_at_gir_tom_streng_ikke_krasj(isolert):
    """Snapshots fra før feltet fantes skal fortsatt kunne diffes."""
    from dataclasses import replace
    gammel = [replace(_obs(value="10", observed_at="2018-02-28"),
                      fetched_at="", source_version="1", utvalg="{}")]
    snapshot.write(gammel, "2018-02-28")

    endr = diff.compare(_ramme([_obs(value="20")]), "2018-03-31")
    assert endr.to_dicts()[0]["forrige_fetched_at"] == ""


# ---- changelog: to filer for samme dato -------------------------------

def test_revisjonen_far_egen_changelogfil_og_sletter_ikke_bevegelsen(isolert):
    """Uten løpenummeret ville revisjonsradene («mars mot mars») skrevet
    over bevegelsesradene («mars mot februar»). To ulike spørsmål, ett
    filnavn, og den førstes svar borte."""
    _skriv([_obs(value="10", observed_at="2018-02-28")], "2018-02-28")
    bevegelse = diff.compare(_ramme([_obs(value="20")]), "2018-03-31")
    changelog.skriv(bevegelse, "2018-03-31", versjon=1)

    _skriv([_obs(value="20")], "2018-03-31")
    rev = diff.revisjon(_ramme([_obs(value="30")]), "2018-03-31")
    changelog.skriv(rev, "2018-03-31", versjon=2)

    mappe = changelog.CHANGELOG_DIR / "biomasse"
    assert sorted(p.name for p in mappe.glob("*")) == [
        "2018-03-31.2.parquet", "2018-03-31.parquet"]

    alt = changelog.les_alt()
    assert sorted(alt["change_type"].to_list()) == ["endret", "revidert"]


# ---- mot EKTE data ---------------------------------------------------

BIOSTAT_HODE_2024 = (
    "ÅR;MÅNED_KODE;MÅNED;PO_KODE;PO_NAVN;ARTSID;UTSETTSÅR;BEHFISK_STK;"
    "BIOMASSE_KG;UTSETT_SMOLT_STK;UTSETT_SMOLT_STK_MINDRE_ENN_500G;"
    "FORFORBRUK_KG;UTTAK_STK;UTTAK_KG;UTTAK_SLØYD_KG;UTTAK_HODEKAPPET_KG;"
    "UTTAK_RUNDVEKT_KG;DØDFISK_STK;UTKAST_STK;RØMMING_STK;ANDRE_STK")

BIOSTAT_HODE_2026 = BIOSTAT_HODE_2024 + ";ANDRE_NY_STK;TELLEFEIL_STK"

# Radene er KOPIERT ORDRETT fra de to ekte filene — hver eneste kolonne,
# ikke bare de vi leser: PO 5 og `(null)` for oktober 2017, REGNBUEØRRET,
# utsettsår 2017. Speilparet der 1 422 777 fisk flyttet begge veier
# mellom de to hentingene.
#
# Tre ting i dem er ekte og ville vært lette å skrive feil fra
# hukommelsen:
#
#   - PO-koden er nullpadet (`05`) i 2024-kopien og ikke (`5`) i dag.
#     Det er grunnen til at _po() normaliserer.
#   - 2024-fila har 21 kolonner, 2026-fila 23.
#   - Tallet 63 står i ANDRE_STK i 2024 og i TELLEFEIL_STK i 2026. Vi
#     leser ingen av dem, og det er nettopp derfor de ikke skal kunne
#     felle noe.
RAD_2024 = (
    "2017;10;OKTOBER;(null);(null);REGNBUEØRRET;2017;310173;615724.696;"
    "25798;25798;146676;0;0;0;0;0;21417;0;0;63",
    "2017;10;OKTOBER;05;Stadt til Hustadvika;REGNBUEØRRET;2017;2553307;"
    "2952571.708;0;0;916015;0;0;0;0;0;21003;0;0;154",
)
RAD_2026 = (
    "2017;10;OKTOBER;(null);(null);REGNBUEØRRET;2017;1732950;1181080.042;"
    "25798;25798;391176;0;0;0;0;0;35249;0;0;0;0;63",
    "2017;10;OKTOBER;5;Stadt til Hustadvika;REGNBUEØRRET;2017;1130530;"
    "2387216.362;0;0;671515;0;0;0;0;0;7171;0;0;0;154;0",
)


def test_ekte_speilpar_fra_biomassefila_blir_revidert(isolert):
    """Oktober 2017, PO 5 mot `(null)`, slik de to ekte filene faktisk
    ser ut.

    Dette er mekanismen hele aksen ble bygget for: ikke nye
    innrapporteringer, men lokaliteter som omklassifiseres mellom
    produksjonsområder i ettertid. Summen står stille, radene flytter seg.
    """
    from dataclasses import replace
    from sources.biomasse import Biomasse

    kilde = Biomasse()
    gammel_csv = "﻿" + "\n".join((BIOSTAT_HODE_2024,) + RAD_2024) + "\n"
    ny_csv = "﻿" + "\n".join((BIOSTAT_HODE_2026,) + RAD_2026) + "\n"

    gammel = [replace(o, fetched_at="2024-08-07T00:00:00+00:00",
                      source_version=kilde.version, raw_hash="a", utvalg="{}")
              for o in kilde.parse(gammel_csv, "2017-10-31")]
    snapshot.write(gammel, "2017-10-31")

    ny = snapshot.to_frame([
        replace(o, fetched_at="2026-08-25T00:00:00+00:00",
                source_version=kilde.version, raw_hash="b", utvalg="{}")
        for o in kilde.parse(ny_csv, "2017-10-31")])

    rev = diff.revisjon(ny, "2017-10-31")

    beholdning = {
        r["entity_id"]: (r["old_value"], r["new_value"])
        for r in rev.filter(pl.col("field") == "beholdning_antall").to_dicts()
    }
    assert beholdning["5"] == ("2553307", "1130530")
    assert beholdning["uten_po"] == ("310173", "1732950")

    # Speilparet: nøyaktig like mange fisk hver vei.
    ned = int(beholdning["5"][0]) - int(beholdning["5"][1])
    opp = int(beholdning["uten_po"][1]) - int(beholdning["uten_po"][0])
    assert ned == opp == 1_422_777

    # Og det avgjørende: dette er IKKE bevegelse i verden.
    assert set(rev["change_type"].to_list()) == {diff.REVIDERT}
    assert diff.bevegelse(rev).is_empty()
    assert set(rev["forrige_fetched_at"].to_list()) == \
        {"2024-08-07T00:00:00+00:00"}

    # Kolonnen som gikk fra 21 til 23 felter mellom de to filene rører
    # ikke noe: den ligger utenfor det kilden leser.
    assert set(rev["field"].to_list()) == {
        "beholdning_antall", "beholdning_antall_regnbueorret", "biomasse_kg",
        "forforbruk_kg", "dodfisk_antall", "andel_av_beholdning",
    }

    # NEVNEREN står stille mens andelene flytter seg. Det er kontrollen
    # på at `uten_po` faktisk telles med: fisken ble flyttet MELLOM de to
    # entitetene, så summen er den samme i begge hentingene — og nettopp
    # derfor må andelene bytte plass.
    assert (int(beholdning["5"][0]) + int(beholdning["uten_po"][0])
            == int(beholdning["5"][1]) + int(beholdning["uten_po"][1]))
    andel = {r["entity_id"]: (r["old_value"], r["new_value"])
             for r in rev.filter(
                 pl.col("field") == "andel_av_beholdning").to_dicts()}
    assert andel["5"] == ("0.891680", "0.394810")
    assert andel["uten_po"] == ("0.108320", "0.605190")
