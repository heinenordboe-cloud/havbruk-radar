"""Biomasse-kilden. Ingen nett — rå CSV er etterlignet fra den faktiske
fila, se docs/KILDE-BIOMASSE.md.

Kolonnehodet under er kopiert ORDRETT fra en ekte respons 25.08.2026,
BOM og alle 23 kolonner inkludert. Det er med vilje: skriver man det av
på nytt fra hukommelsen, tester man sin egen antakelse om formatet i
stedet for formatet.
"""

import datetime as dt

import pytest

from core import runner, snapshot, utvalg as utvalg_modul
from sources import biomasse
from sources.biomasse import (Biomasse, Kolonnefeil, Maanedmangler,
                              maaned_av, maaned_med_etterslep, maaneder_i,
                              siste_dag, _les_csv, _po, _tall)

HODE = ("ÅR;MÅNED_KODE;MÅNED;PO_KODE;PO_NAVN;ARTSID;UTSETTSÅR;BEHFISK_STK;"
        "BIOMASSE_KG;UTSETT_SMOLT_STK;UTSETT_SMOLT_STK_MINDRE_ENN_500G;"
        "FORFORBRUK_KG;UTTAK_STK;UTTAK_KG;UTTAK_SLØYD_KG;UTTAK_HODEKAPPET_KG;"
        "UTTAK_RUNDVEKT_KG;DØDFISK_STK;UTKAST_STK;RØMMING_STK;ANDRE_STK;"
        "ANDRE_NY_STK;TELLEFEIL_STK")

PO_NAVN = {
    "1": "Svenskegrensen til Jæren", "2": "Ryfylket", "3": "Karmøy til Sotra",
    "4": "Nordhordland til Stadt", "5": "Stadt til Hustadvika",
    "6": "Nordmøre til Sør-Trøndelag", "7": "Nord-Trøndelag med Bindal",
    "8": "Helgeland til Bodø", "9": "Vestfjorden og Vesterålen",
    "10": "Andøya til Senja", "11": "Kvaløy til Loppa",
    "12": "Vest-Finnmark", "13": "Øst-Finnmark",
}


def _rad(po="1", art="LAKS", behfisk=1000, biomasse_kg="3000.500",
         aar=2026, mnd=4, utsettsaar=2025, dodfisk=10, romming=0,
         uttak=0, smolt=0, forbruk=500, navn=None):
    if navn is None:
        navn = "(null)" if po == "(null)" else PO_NAVN.get(po, "Ukjent")
    return (f"{aar};{mnd};APRIL;{po};{navn};{art};{utsettsaar};{behfisk};"
            f"{biomasse_kg};{smolt};{smolt};{forbruk};{uttak};0;0;0;0;"
            f"{dodfisk};0;{romming};0;0;0")


def _csv(*rader, bom=True, hode=HODE, linjeskift="\n"):
    return ("﻿" if bom else "") + linjeskift.join((hode,) + rader) + linjeskift


def _alle_po(aar=2026, mnd=4):
    """En hel måned: tretten produksjonsområder pluss (null)."""
    return tuple(_rad(po=po, aar=aar, mnd=mnd) for po in PO_NAVN) + (
        _rad(po="(null)", aar=aar, mnd=mnd),)


def _verdier(obs):
    return {(o.entity_id, o.field): o.value for o in obs}


# ---- formatet vi ikke eier -------------------------------------------

def test_bom_spises_slik_at_forste_kolonne_heter_aar():
    """Fila har BOM. Uten utf-8-sig heter kolonne én '\\ufeffÅR', og
    oppslaget bommer på nøyaktig den kolonnen som bærer året — så hver
    eneste måned blir udaterbar mens de 22 andre ser friske ut."""
    rader = _les_csv(_csv(_rad()))
    assert rader[0]["ÅR"] == "2026"
    assert "﻿ÅR" not in rader[0]


def test_manglende_kolonne_kaster_med_navns_nevnelse():
    hode = HODE.replace(";BEHFISK_STK", ";BEHOLDNING_STK")
    with pytest.raises(Kolonnefeil) as e:
        _les_csv(_csv(_rad(), hode=hode))
    assert "BEHFISK_STK" in str(e.value)


def test_kolonne_vi_ikke_leser_kan_mangle_uten_aa_felle_maaneden():
    """Skjemaet vokste fra 21 til 23 kolonner i 2024. Vi leser ingen av
    de to nye, og en kolonne til skal ikke kunne stoppe innsamlingen."""
    hode = HODE.replace(";ANDRE_NY_STK;TELLEFEIL_STK", "")
    rad = _rad().rsplit(";", 2)[0]
    assert _les_csv(_csv(rad, hode=hode))[0]["BEHFISK_STK"] == "1000"


def test_crlf_gir_samme_resultat_som_lf():
    """Tjenesten svarer med CRLF. Verifisert 25.08.2026: 5200 \\r i
    svaret. En \\r som blir hengende igjen i siste kolonne ville vært
    usynlig helt til noen leste den kolonnen."""
    k = Biomasse()
    lf = k.parse(_csv(*_alle_po()), "2026-04-30")
    crlf = k.parse(_csv(*_alle_po(), linjeskift="\r\n"), "2026-04-30")
    assert list(lf) == list(crlf)


def test_tom_fil_er_tom_liste_ikke_krasj():
    assert _les_csv("") == []
    assert _les_csv(_csv()) == []


def test_tom_celle_i_en_kolonne_som_summeres_kaster():
    """Motsatt av sjotemperatur, der en ulesbar celle koster raden. Her
    SUMMERES verdiene, og en celle som stilltiende ble null ville gitt et
    produksjonsområde med færre fisk enn det har."""
    with pytest.raises(Kolonnefeil):
        _tall("")
    with pytest.raises(Kolonnefeil):
        _tall(None)


# ---- PO-koden, som har byttet format ---------------------------------

def test_nullpadet_og_upadet_po_kode_gir_samme_entitet():
    """`01` i 2024-kopien, `1` i dag. Uten normaliseringen ville PO 1
    vært to entiteter, og hver av dem sett ut som «ny» den dagen
    formatet snudde."""
    assert _po({"PO_KODE": "01"}) == _po({"PO_KODE": "1"}) == "1"
    assert _po({"PO_KODE": "013"}) == "13"


def test_null_blir_uten_po_ikke_tomt():
    assert _po({"PO_KODE": "(null)"}) == biomasse.UTEN_PO


def test_ukjent_po_kode_kaster_framfor_aa_bli_sin_egen_entitet():
    """Et stille fjortende produksjonsområde ville lagt seg ved siden av
    de tretten og telt med i nevneren uten at noen så det."""
    with pytest.raises(Kolonnefeil) as e:
        _po({"PO_KODE": "PO-5"})
    assert "PO-5" in str(e.value)


def test_koblingen_mot_akvakultur_er_direkte():
    """`prodomraade_kode` i akvakultursnapshotene er '1'..'13' — målt mot
    siste snapshot 25.08.2026. Normaliseringen skal treffe nøyaktig de
    strengene, ikke noe som ligner."""
    obs = list(Biomasse().parse(_csv(*_alle_po()), "2026-04-30"))
    ekte = {o.entity_id for o in obs} - {biomasse.UTEN_PO}
    assert ekte == {str(n) for n in range(1, 14)}


# ---- kalenderen ------------------------------------------------------

def test_gjelder_for_er_siste_dag_i_maaneden_fire_tilbake():
    k = Biomasse()
    assert k.gjelder_for("2026-08-25") == "2026-04-30"
    assert k.gjelder_for("2026-01-03") == "2025-09-30"


def test_maanedsregningen_taaler_arsskiftet():
    assert maaned_med_etterslep(dt.date(2026, 1, 15), 4) == (2025, 9)
    assert maaned_med_etterslep(dt.date(2026, 3, 1), 4) == (2025, 11)
    assert maaned_med_etterslep(dt.date(2026, 12, 31), 4) == (2026, 8)


def test_siste_dag_treffer_skuddar_og_desember():
    assert siste_dag(2024, 2) == "2024-02-29"
    assert siste_dag(2026, 2) == "2026-02-28"
    assert siste_dag(2026, 12) == "2026-12-31"


def test_etterslepet_gir_alder_minst_to_uansett_dag_i_maaneden():
    """Hele begrunnelsen for fire og ikke tre.

    Revisjonsandelen faller 28,8 % -> 19,2 % -> 11,3 % med månedens
    alder og flater ut ved to. Publiseringen skjer den 20., så ferskeste
    tilgjengelige måned er kjøremåneden minus 1 fra og med den 20., og
    minus 2 før den. Grensen skal ikke avhenge av hvilken ukedag cron
    traff, så den må holde for BEGGE.
    """
    k = Biomasse()
    for aar in (2025, 2026):
        for mnd in range(1, 13):
            for dag in (1, 19, 20, 28):
                kjoredato = f"{aar}-{mnd:02d}-{dag:02d}"
                skrives = maaned_av(k.gjelder_for(kjoredato))
                # Ferskeste måned fila bærer denne dagen.
                ferskeste = maaned_med_etterslep(
                    dt.date.fromisoformat(kjoredato), 1 if dag >= 20 else 2)
                alder = ((ferskeste[0] * 12 + ferskeste[1])
                         - (skrives[0] * 12 + skrives[1]))
                assert alder >= 2, (kjoredato, skrives, ferskeste, alder)


def test_observed_at_som_ikke_er_manedsslutt_kaster():
    """Ett snapshot er ett tidspunkt, og filnavnet er det eneste alt
    nedstrøms leser datoen fra. Beholdningen måles ved månedslutt."""
    with pytest.raises(ValueError) as e:
        maaned_av("2026-04-15")
    assert "2026-04-30" in str(e.value)


def test_maaneder_i_leser_fila_ikke_kalenderen():
    rader = _les_csv(_csv(*_alle_po(2026, 3), *_alle_po(2026, 4)))
    assert maaneder_i(rader) == [(2026, 3), (2026, 4)]


# ---- tolkningen ------------------------------------------------------

def test_maaneden_velges_av_observed_at_og_bekreftes_av_fila():
    k = Biomasse()
    rå = _csv(*_alle_po(2026, 3), *_alle_po(2026, 4))
    mars = list(k.parse(rå, "2026-03-31"))
    april = list(k.parse(rå, "2026-04-30"))
    assert {o.observed_at for o in mars} == {"2026-03-31"}
    assert {o.observed_at for o in april} == {"2026-04-30"}
    assert len(mars) == len(april) == 140


def test_maaned_som_mangler_i_fila_kaster_framfor_aa_skrive_tomt():
    """Et tomt snapshot ville sett vellykket ut, låst måneden mot senere
    henting via finnes_allerede(), og gjort hullet permanent i en
    append-only-serie."""
    k = Biomasse()
    with pytest.raises(Maanedmangler) as e:
        list(k.parse(_csv(*_alle_po(2026, 4)), "2026-05-31"))
    assert "2026-04" in str(e.value)


def test_utsettsaar_summeres_bort():
    """Fila har én rad per (PO, art, utsettsår). Kilden emitter én verdi
    per PO."""
    k = Biomasse()
    rå = _csv(_rad(po="1", behfisk=1000, utsettsaar=2024),
              _rad(po="1", behfisk=250, utsettsaar=2025))
    assert _verdier(k.parse(rå, "2026-04-30"))[("1", "beholdning_antall")] == "1250"


def test_art_som_mangler_gir_null_ikke_ingenting():
    """903 av 1484 PO-måneder har bare laks. Registeret skriver
    eksplisitte nuller (250 rader med BEHFISK_STK = 0), så en kohort som
    ikke finnes har ingen fisk — det er null, ikke «vet ikke».

    Motsatt valg ville gitt et felt som forsvinner og kommer tilbake alt
    etter hvilke arter som står i sjøen, og feltvakten i health.py er
    bygget for å reagere på nettopp det."""
    k = Biomasse()
    v = _verdier(k.parse(_csv(_rad(po="1", art="LAKS", behfisk=900)),
                         "2026-04-30"))
    assert v[("1", "beholdning_antall_laks")] == "900"
    assert v[("1", "beholdning_antall_regnbueorret")] == "0"


def test_artene_summerer_til_totalen():
    k = Biomasse()
    v = _verdier(k.parse(
        _csv(_rad(po="3", art="LAKS", behfisk=700),
             _rad(po="3", art="REGNBUEØRRET", behfisk=300)), "2026-04-30"))
    assert v[("3", "beholdning_antall")] == "1000"
    assert v[("3", "beholdning_antall_laks")] == "700"
    assert v[("3", "beholdning_antall_regnbueorret")] == "300"


def test_en_ukjent_art_teller_i_totalen_men_ikke_i_artsfeltene():
    """Kommer det en tredje art, skal totalen fortsatt være totalen.
    Artsfeltene er navngitte og kjenner bare de to vi har sett."""
    k = Biomasse()
    v = _verdier(k.parse(
        _csv(_rad(po="3", art="LAKS", behfisk=700),
             _rad(po="3", art="TORSK", behfisk=300)), "2026-04-30"))
    assert v[("3", "beholdning_antall")] == "1000"
    assert v[("3", "beholdning_antall_laks")] == "700"
    assert v[("3", "beholdning_antall_regnbueorret")] == "0"


def test_kilo_avrundes_stabilt_slik_at_diffen_ikke_finner_pa_endringer():
    """Uten avrunding gir flyttallsummen 3615930.4530000002 den ene
    kjøringen og 3615930.453 den neste, og diffen rapporterer en endring
    som ikke har skjedd."""
    k = Biomasse()
    rå = _csv(_rad(po="1", biomasse_kg="3615930.453"),
              _rad(po="1", biomasse_kg="0.001", utsettsaar=2024))
    assert _verdier(k.parse(rå, "2026-04-30"))[("1", "biomasse_kg")] == "3615930.454"


# ---- (null)-kategorien -----------------------------------------------

def test_uten_po_lagres_som_egen_entitet_ikke_filtreres_bort():
    """0,96-4,57 % av all fisk. En nevner som forsvinner stille er verre
    enn en nevner som er rar."""
    obs = list(Biomasse().parse(_csv(*_alle_po()), "2026-04-30"))
    uten = [o for o in obs if o.entity_id == biomasse.UTEN_PO]
    assert uten and {o.entity_name for o in uten} == {biomasse.UTEN_PO_NAVN}


def test_andelen_emitteres_for_alle_entiteter_ikke_bare_for_uten_po():
    """Et felt med ÉN rad har per konstruksjon null minoritet, og
    health._vurder_innhold() ville lest det som et dødt felt og fyrt hver
    måned i det uendelige. Fjorten rader gir minoritet 13."""
    obs = list(Biomasse().parse(_csv(*_alle_po()), "2026-04-30"))
    med_andel = {o.entity_id for o in obs if o.field == "andel_av_beholdning"}
    assert med_andel == {o.entity_id for o in obs}
    assert len(med_andel) == 14


def test_uten_po_teller_med_i_nevneren():
    """Hele poenget med feltet: en konsument som har droppet uten_po får
    et tall som ikke stemmer med vårt, i stedet for et som ser riktig ut."""
    k = Biomasse()
    v = _verdier(k.parse(_csv(_rad(po="1", behfisk=900),
                              _rad(po="(null)", behfisk=100)), "2026-04-30"))
    assert v[("1", "andel_av_beholdning")] == "0.900000"
    assert v[(biomasse.UTEN_PO, "andel_av_beholdning")] == "0.100000"


def test_andelene_summerer_til_en():
    obs = list(Biomasse().parse(_csv(*_alle_po()), "2026-04-30"))
    sum_andel = sum(float(o.value) for o in obs
                    if o.field == "andel_av_beholdning")
    assert abs(sum_andel - 1.0) < 1e-5


def test_ingen_fisk_i_det_hele_tatt_gir_null_andel_ikke_deling_paa_null():
    k = Biomasse()
    v = _verdier(k.parse(_csv(_rad(po="1", behfisk=0)), "2026-04-30"))
    assert v[("1", "andel_av_beholdning")] == "0.000000"


# ---- kontrakten mot kjernen ------------------------------------------

def test_en_verdi_per_entitet_og_felt():
    """Invarianten i observasjonsformatet. Dedupliseringen i to_frame()
    skal ikke ha noe å gjøre."""
    obs = list(Biomasse().parse(_csv(*_alle_po()), "2026-04-30"))
    assert snapshot.to_frame(obs).height == len(obs) == 140


def test_snapshot_write_godtar_maaneden(tmp_path, monkeypatch):
    """write() håndhever at filnavnet stemmer med radenes observed_at.
    Det er den kontrollen F6 etterlot seg, og den skal passere her."""
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)
    obs = list(Biomasse().parse(_csv(*_alle_po()), "2026-04-30"))
    filer = snapshot.write(obs, "2026-04-30")
    assert [p.name for p in filer] == ["2026-04-30.parquet"]


def test_utvalget_settes_i_hent_alt_ikke_i_fetch(monkeypatch):
    """Samme felle som kostet sjotemperatur 389 206 rader med tomt
    utvalg: backfill går utenom fetch(), så utvalget må settes der begge
    veier møtes."""
    k = Biomasse()
    monkeypatch.setattr(biomasse._http, "get", lambda *a, **kw: _Svar(_csv()))
    assert k.utvalg is None
    k.hent_alt()
    assert k.utvalg == {}
    assert utvalg_modul.henter_alt(k.utvalg)


def test_backfillede_rader_baerer_utvalg(monkeypatch):
    k = Biomasse()
    monkeypatch.setattr(biomasse._http, "get",
                        lambda *a, **kw: _Svar(_csv(*_alle_po())))
    rå = k.hent_alt()
    obs = runner.stempl(k.parse(rå, "2026-04-30"), source_version="1",
                        raw_hash="x", utvalg=k.utvalg)
    assert {o.utvalg for o in obs} == {utvalg_modul.serialiser({})}


class _Svar:
    def __init__(self, tekst, headere=None):
        self.content = tekst.encode("utf-8-sig")
        # Ekte header fra tjenesten 25.08.2026. Den 20., ~04:40 UTC — samme
        # mønster som Wayback-kopien fra 2024 bærer.
        self.headers = {"Last-Modified": "Thu, 20 Aug 2026 04:38:18 GMT"} \
            if headere is None else headere


def test_fetch_returnerer_hele_fila_uendret_for_arkivering(monkeypatch):
    """Kjernen arkiverer det fetch() RETURNERER. Returnerte den bare
    måneden vi skriver, ville revisjonshistorikken — den eneste kopien
    som finnes av hva Fiskeridirektoratet sa om fortiden — vært borte."""
    k = Biomasse()
    rå = _csv(*_alle_po(2026, 3), *_alle_po(2026, 4))
    monkeypatch.setattr(k, "hent_alt", lambda: rå)
    assert k.fetch("2026-08-25") == rå
    assert maaneder_i(_les_csv(k.fetch("2026-08-25"))) == [(2026, 3), (2026, 4)]


def test_kolonnefeil_feller_ikke_fetch(monkeypatch):
    """En exception i fetch() betyr at rå-CSV-en aldri når disk, og da er
    en omdøpt kolonne oppdaget om et halvt år permanent datatap i stedet
    for en re-parse. Feilen forsvinner ikke — parse() kaster."""
    k = Biomasse()
    ødelagt = _csv(_rad(), hode=HODE.replace("BEHFISK_STK", "BEHOLDNING"))
    monkeypatch.setattr(k, "hent_alt", lambda: ødelagt)

    assert k.fetch("2026-08-25") == ødelagt
    assert k.advarsler and "BEHFISK_STK" in k.advarsler[0]
    with pytest.raises(Kolonnefeil):
        list(k.parse(ødelagt, "2026-04-30"))


# ---- vaktene ---------------------------------------------------------

def test_full_maaned_tier():
    k = Biomasse()
    assert k._vurder(_les_csv(_csv(*_alle_po())), 2026, 4) == []


def test_manglende_produksjonsomraade_gir_advarsel():
    """Målt: alle tretten er til stede i hver eneste av 106 måneder. Er
    de plutselig ikke det, er nevneren i enhver aggregering endret."""
    k = Biomasse()
    rader = _les_csv(_csv(*_alle_po()[:5]))
    varsler = k._vurder(rader, 2026, 4)
    assert varsler and "5 produksjonsområder i fila, ventet 13" in varsler[0]


def test_forsinket_publisering_gir_advarsel_ikke_exception(monkeypatch):
    """Advarselen skal ikke felle fetch() — arkivering først. Måneden
    felles i parse(), etter at fila ligger på disk."""
    k = Biomasse()
    rå = _csv(*_alle_po(2026, 3))
    monkeypatch.setattr(k, "hent_alt", lambda: rå)
    assert k.fetch("2026-08-25") == rå
    assert k.advarsler and "ligger ikke i fila" in k.advarsler[0]


def test_tom_fil_gir_advarsel(monkeypatch):
    k = Biomasse()
    monkeypatch.setattr(k, "hent_alt", lambda: _csv())
    k.fetch("2026-08-25")
    assert k.advarsler == ["biomasse: fila er tom."]


# ---- published_at: LEST, ikke gjettet --------------------------------

def test_utgitt_leses_av_last_modified():
    """Ekte header fra tjenesten 25.08.2026. Den 20., ~04:40 UTC — som er
    dagen fila publiseres på nytt."""
    assert biomasse._utgitt({"Last-Modified": "Thu, 20 Aug 2026 04:38:18 GMT"}) \
        == "2026-08-20T04:38:18+00:00"


def test_utgitt_faller_tilbake_paa_waybacks_bevarte_header():
    """`X-Archive-Orig-Last-Modified` er DEN SAMME headeren, bevart av
    Internet Archive. Ekte verdi fra kopien av 07.08.2024."""
    assert biomasse._utgitt(
        {"X-Archive-Orig-Last-Modified": "Sat, 20 Jul 2024 04:40:53 GMT"}
    ) == "2024-07-20T04:40:53+00:00"


def test_waybacks_egen_fangstdato_brukes_IKKE():
    """`Memento-Datetime` er da ARKIVET hentet kroppen — deres fetched_at,
    ikke Fiskeridirektoratets published_at. For 2024-kopien ligger de 18
    dager fra hverandre, og å bruke feil ville datert en publisering etter
    at den skjedde."""
    assert biomasse._utgitt(
        {"Memento-Datetime": "Wed, 07 Aug 2024 22:13:45 GMT"}) == ""


def test_manglende_eller_ulesbar_header_gir_tom_streng_ikke_klokka():
    """Tom streng er «vet ikke». Å falle tilbake på klokka ville datert en
    tredjeparts publisering etter når VI ringte."""
    assert biomasse._utgitt({}) == ""
    assert biomasse._utgitt({"Last-Modified": ""}) == ""
    assert biomasse._utgitt({"Last-Modified": "i går"}) == ""


def test_hent_alt_setter_published_at(monkeypatch):
    k = Biomasse()
    assert k.published_at == ""
    monkeypatch.setattr(biomasse._http, "get", lambda *a, **kw: _Svar(_csv()))
    k.hent_alt()
    assert k.published_at == "2026-08-20T04:38:18+00:00"


def test_published_at_stemples_paa_raden(monkeypatch):
    k = Biomasse()
    monkeypatch.setattr(biomasse._http, "get",
                        lambda *a, **kw: _Svar(_csv(*_alle_po())))
    rå = k.hent_alt()
    obs = runner.stempl(k.parse(rå, "2026-04-30"), source_version="1",
                        raw_hash="x", published_at=k.published_at,
                        utvalg=k.utvalg)
    assert {o.published_at for o in obs} == {"2026-08-20T04:38:18+00:00"}


def test_kilde_uten_header_gir_tomt_felt_ikke_hentetidspunktet(monkeypatch):
    k = Biomasse()
    monkeypatch.setattr(biomasse._http, "get",
                        lambda *a, **kw: _Svar(_csv(*_alle_po()), headere={}))
    rå = k.hent_alt()
    obs = runner.stempl(k.parse(rå, "2026-04-30"), source_version="1",
                        raw_hash="x", published_at=k.published_at)
    assert {o.published_at for o in obs} == {""}
    assert {o.fetched_at for o in obs} != {""}


def test_url_kan_overstyres_for_arkivkopi(monkeypatch):
    """En Wayback-kopi er samme fil på en annen adresse — ikke et
    særtilfelle i parsingen."""
    sett = []
    monkeypatch.setattr(biomasse._http, "get",
                        lambda c, url, **kw: (sett.append(url), _Svar(_csv()))[1])
    k = Biomasse()
    k.hent_alt()
    k.hent_alt(url="https://web.archive.org/web/x/https://register…/fil.csv")
    assert sett[0] == biomasse.STANDARD_URL
    assert sett[1].startswith("https://web.archive.org/")


def test_maaneder_lar_kroppen_svare_selv():
    """Arkivmodusen må vite hvilke perioder en kopi dekker uten å kjenne
    CSV-formatet."""
    k = Biomasse()
    rå = _csv(*_alle_po(2026, 3), *_alle_po(2026, 4))
    assert k.maaneder(rå) == ["2026-03-31", "2026-04-30"]
