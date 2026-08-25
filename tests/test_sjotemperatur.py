"""Sjøtemperatur-kilden. Ingen nett — rå CSV er etterlignet fra den
faktiske eksporten, se docs/KILDE-SJOTEMPERATUR.md.

Kolonnenavnene under er kopiert ordrett fra en ekte respons 24.08.2026,
BOM inkludert. Det er med vilje: skriver man dem av på nytt fra
hukommelsen, tester man sin egen antakelse om formatet i stedet for
formatet.
"""

import pytest

from core import runner, snapshot, utvalg as utvalg_modul
from sources import sjotemperatur
from sources.sjotemperatur import (Kolonnefeil, Sjotemperatur, mandag,
                                   rapportert_andel, _les_csv, _tall,
                                   _vurder_rapportering)

HODE = ("Uke,År,Lokalitetsnummer,Lokalitetsnavn,Voksne hunnlus,"
        "Lus i bevegelige stadier,Fastsittende lus,Trolig uten fisk,"
        "Har telt lakselus,Kommunenummer,Kommune,Fylkesnummer,Fylke,Lat,Lon,"
        "Lusegrense uke,Over lusegrense uke,Sjøtemperatur,"
        "ProduksjonsområdeId,Produksjonsområde")


def _rad(nr, temp="14.07", brakk="Nei", telt="Ja", aar=2026, uke=30):
    return (f"{uke},{aar},{nr},Lokalitet {nr},0.45,0.6,0.03,{brakk},{telt},"
            f"1219,BØMLO,12,Hordaland,59.8451,5.261367,0.5,Nei,{temp},"
            f"3,Karmøy til Sotra")


def _csv(*rader, bom=True):
    return ("﻿" if bom else "") + "\n".join((HODE,) + rader) + "\n"


# ---- formatet vi ikke eier -------------------------------------------

def test_bom_spises_slik_at_forste_kolonne_heter_uke():
    """Eksporten har BOM. Uten utf-8-sig heter kolonne én '\\ufeffUke',
    og oppslaget bommer på nøyaktig én kolonne — stille."""
    rader = _les_csv(_csv(_rad(10029)))
    assert rader[0]["Uke"] == "30"
    assert "﻿Uke" not in rader[0]


def test_manglende_kolonne_kaster_med_navns_nevnelse():
    """En stille omdøping ville gitt tomme uker som ser vellykkede ut."""
    hode = HODE.replace("Sjøtemperatur", "Sjotemperatur")
    tekst = "﻿" + hode + "\n" + _rad(10029) + "\n"
    with pytest.raises(Kolonnefeil, match="Sjøtemperatur"):
        _les_csv(tekst)


def test_tom_csv_er_ikke_en_feil_men_en_tom_uke():
    """2010 og 2011 gir 200 OK med tom liste. Backfillens stoppvilkår
    teller rader, så tomt skal gi tomt — ikke en exception."""
    assert _les_csv(_csv()) == []
    assert list(Sjotemperatur().parse(_csv(), "2026-08-24")) == []


def test_komma_som_desimalskilletegn_leses():
    assert _tall("14,07") == 14.07
    assert _tall("14.07") == 14.07
    assert _tall("") is None
    assert _tall(None) is None
    assert _tall("  ") is None
    assert _tall("ikke et tall") is None


# ---- gyldighetsdato ---------------------------------------------------

def test_observed_at_er_uka_ikke_hentedagen():
    """Kjernen sender inn hentedagen; kilden vet at dataene gjelder uka.
    Datoen utledes av Uke/År i DATAENE, ikke av en klokke (F6, F7)."""
    obs = list(Sjotemperatur().parse(_csv(_rad(10029)), "2026-08-24"))
    assert obs
    assert {o.observed_at for o in obs} == {"2026-07-20"}   # uke 30/2026


def test_gjelder_for_er_ukas_mandag_fire_uker_tilbake():
    """24.08.2026 er ISO-uke 35. Fire uker tilbake er uke 31, mandag 27.07."""
    assert Sjotemperatur().gjelder_for("2026-08-24") == "2026-07-27"


def test_gjelder_for_og_parse_er_enige_om_uka():
    """F7 i klartekst: filnavnet og innholdet skal komme fra samme uke.

    gjelder_for() regner uka ut fra kjøredatoen; parse() leser den ut av
    dataene. De to må lande likt, ellers får fila navn etter én uke og
    innhold fra en annen.
    """
    kilde = Sjotemperatur()
    kjoredato = "2026-08-24"
    aar, uke = kilde._uke_naa(kjoredato)
    obs = list(kilde.parse(_csv(_rad(10029, aar=aar, uke=uke)), kjoredato))
    assert {o.observed_at for o in obs} == {kilde.gjelder_for(kjoredato)}


def test_flere_uker_i_samme_eksport_kaster():
    """Et snapshot bærer én dato. To uker i én fil ville datert den ene
    feil — stille, og permanent siden filene er append-only."""
    tekst = _csv(_rad(10029, uke=30), _rad(10030, uke=31))
    with pytest.raises(ValueError, match="ulike uker"):
        list(Sjotemperatur().parse(tekst, "2026-08-24"))


# ---- skillet mellom null grader og ingen måling -----------------------

def test_null_grader_er_en_verdi_ikke_et_hull():
    """0,0 grader forekommer 675 ganger i historikken. Blander man den
    med «ikke rapportert», blir et hull til et tall i enhver analyse — og
    med (T + 4,28)^2 er det et tall som ser troverdig ut."""
    obs = list(Sjotemperatur().parse(_csv(_rad(10029, temp="0.0")),
                                     "2026-08-24"))
    felter = {o.field: o.value for o in obs}
    assert felter["sjotemperatur"] == "0.0"
    assert felter["temperatur_er_rapportert"] == "True"


def test_manglende_maling_gir_flagg_ikke_stillhet():
    obs = list(Sjotemperatur().parse(_csv(_rad(10029, temp="", brakk="Ja",
                                               telt="Nei")), "2026-08-24"))
    felter = {o.field: o.value for o in obs}
    assert felter["temperatur_er_rapportert"] == "False"
    assert "sjotemperatur" not in felter


def test_uteligger_lagres_som_rapportert():
    """196,18 grader er en tastefeil hos innrapportør, og den lagres.
    Kilden redigerer ikke virkeligheten — analysen filtrerer."""
    obs = list(Sjotemperatur().parse(_csv(_rad(10029, temp="196.18")),
                                     "2026-08-24"))
    felter = {o.field: o.value for o in obs}
    assert felter["sjotemperatur"] == "196.18"
    assert felter["temperatur_er_rapportert"] == "True"


def test_rad_uten_lokalitetsnummer_hoppes_over():
    obs = list(Sjotemperatur().parse(_csv(_rad("")), "2026-08-24"))
    assert obs == []


# ---- feltvalg: hva kilden IKKE eier -----------------------------------

def test_emitter_bare_temperatur_ikke_naboenes_felter():
    """`akvakultur` eier navn, kommune, fylke, breddegrad og
    produksjonsområde; `lusetall` eier lusetallene. To kilder som skriver
    samme felt med hver sin skrivemåte legger igjen en permanent falsk
    forskjell."""
    obs = list(Sjotemperatur().parse(_csv(_rad(10029)), "2026-08-24"))
    assert {o.field for o in obs} == {"sjotemperatur",
                                      "temperatur_er_rapportert"}


def test_lokalitetsnummeret_er_nokkelen_navnet_folger_med_som_etikett():
    obs = list(Sjotemperatur().parse(_csv(_rad(10029)), "2026-08-24"))
    assert {o.entity_id for o in obs} == {"10029"}
    assert {o.entity_type for o in obs} == {"lokalitet"}
    assert {o.entity_name for o in obs} == {"Lokalitet 10029"}


# ---- vakten mot en fersk uke ------------------------------------------

def test_nevneren_er_ikke_brakklagte():
    """Mot totalen ville andelen vært ~55 % hver uke, fordi to tredeler
    er brakklagte og ikke skal måle noe. Da ville vakten fyrt alltid."""
    rader = _les_csv(_csv(
        _rad(1, temp="12.0"), _rad(2, temp="11.0"),
        _rad(3, temp="", brakk="Ja", telt="Nei"),
        _rad(4, temp="", brakk="Ja", telt="Nei"),
    ))
    aktive, med, andel = rapportert_andel(rader)
    assert (aktive, med) == (2, 2)
    assert andel == 1.0


def test_fersk_uke_gir_advarsel_ikke_exception():
    """Snapshotet skal skrives, men kjøringen skal bli rød. En uke som
    kastes er en uke som aldri blir hentet."""
    rader = _les_csv(_csv(
        _rad(1, temp="12.0"),
        *[_rad(n, temp="") for n in range(2, 11)],
    ))
    advarsler = _vurder_rapportering(rader, 2026, 34)
    assert len(advarsler) == 1
    assert "10,0 %" in advarsler[0] or "10.0%" in advarsler[0]
    assert "uke 34/2026" in advarsler[0]


def test_ferdig_uke_tier():
    rader = _les_csv(_csv(*[_rad(n, temp="12.0") for n in range(1, 11)]))
    assert _vurder_rapportering(rader, 2026, 30) == []


def test_andel_over_dem_som_telte_lus_ville_aldri_fyrt():
    """F10-formen, gjort eksplisitt: «av dem som telte lus, hvor mange
    har temperatur» er 100 % i hver eneste uke 2012-2026 — også i en uke
    der åtte lokaliteter har rapportert. Denne testen dokumenterer at
    vakten IKKE bruker det målet.

    En fersk uke der de få som har rapportert har temperatur skal
    fortsatt gi advarsel.
    """
    rader = _les_csv(_csv(
        _rad(1, temp="12.0", telt="Ja"),
        *[_rad(n, temp="", telt="Nei") for n in range(2, 21)],
    ))
    telt = [r for r in rader if r["Har telt lakselus"] == "Ja"]
    med_temp = [r for r in telt if r["Sjøtemperatur"]]
    assert len(med_temp) == len(telt)          # 100 %, målet som lyver
    assert _vurder_rapportering(rader, 2026, 35)   # vakten fyrer likevel


# ---- utvalg -----------------------------------------------------------

def test_utvalget_stemples_paa_raden():
    """Regel 1b-3: en verdi som avgjør hva dataene BETYR lagres SAMMEN
    med dem. Ber noen senere også om `Disease`, kommer det inn
    lokaliteter som er nye i utvalget og ikke i verden."""
    kilde = Sjotemperatur()
    kilde.utvalg = {"rapporttype": ["Lice"]}
    obs = runner.stempl(kilde.parse(_csv(_rad(10029)), "2026-08-24"),
                        source_version="1", raw_hash="abc",
                        utvalg=kilde.utvalg)
    assert obs
    assert {o.utvalg for o in obs} == {'{"rapporttype":["Lice"]}'}
    assert utvalg_modul.les(obs[0].utvalg) == {"rapporttype": ["Lice"]}


# ---- kontrakten mot resten av systemet --------------------------------

def test_en_verdi_per_entitet_og_felt():
    """snapshot.to_frame() dedupliserer på (entity_id, field, source).
    Leverer kilden to rader for samme par, forsvinner den ene stille."""
    obs = list(Sjotemperatur().parse(
        _csv(_rad(1, temp="12.0"), _rad(2, temp="13.0")), "2026-08-24"))
    ramme = snapshot.to_frame(runner.stempl(obs, "1", ""))
    assert ramme.height == len(obs)


def test_mandag_i_iso_uka_er_den_samme_som_lusetalls():
    """De to kildene skal gi samme filnavn for samme uke. Er de uenige,
    ligger to snapshots av samme uke på hver sin dato."""
    from sources.lusetall import mandag as lusetall_mandag
    for aar, uke in [(2012, 1), (2026, 30), (2026, 34), (2020, 53)]:
        assert mandag(aar, uke) == lusetall_mandag(aar, uke)


# ---- rå-arkivet skal alltid rekke disken -----------------------------

def test_kolonnefeil_feller_ikke_fetch(monkeypatch):
    """Kjernen arkiverer det fetch() RETURNERER. Kaster fetch(), når
    rå-CSV-en aldri disk, og en omdøpt kolonne oppdaget om et halvt år er
    permanent datatap i stedet for en re-parse.

    Feilen skal likevel ikke forsvinne: parse() kaster den, etter at
    arkiveringen er unnagjort.
    """
    hode = HODE.replace("Sjøtemperatur", "Havtemperatur")
    tekst = "﻿" + hode + "\n" + _rad(10029) + "\n"

    kilde = Sjotemperatur()
    monkeypatch.setattr(kilde, "hent_uke", lambda aar, uke, client=None: tekst)

    rå = kilde.fetch("2026-08-24")           # kommer helskinnet tilbake
    assert rå == tekst                       # uendret, klar for arkivet
    assert kilde.advarsler                   # men den sier fra
    assert "Sjøtemperatur" in kilde.advarsler[0]

    with pytest.raises(Kolonnefeil):         # og feilen er ikke borte
        list(kilde.parse(rå, "2026-08-24"))


def test_fetch_returnerer_uendret_tekst_for_arkivering(monkeypatch):
    """Det som arkiveres skal være det tjenesten faktisk sendte."""
    tekst = _csv(_rad(10029), _rad(10030, temp=""))
    kilde = Sjotemperatur()
    monkeypatch.setattr(kilde, "hent_uke", lambda aar, uke, client=None: tekst)
    assert kilde.fetch("2026-08-24") == tekst


def test_utvalget_settes_i_hent_uke_ikke_i_fetch(monkeypatch):
    """Begge veier inn i kilden skal bære utvalget — regel 1b-3.

    Backfillen kaller hent_uke() direkte og ser aldri fetch(). Sto
    tilordningen i fetch(), ville 389 206 backfillede rader hatt tomt
    utvalg og ikke kunnet svare på hva vi lette etter. Det var nøyaktig
    det som skjedde 24.08.2026.
    """
    tekst = _csv(_rad(10029))

    class FalsktSvar:
        content = tekst.encode("utf-8-sig")

    kilde = Sjotemperatur()
    monkeypatch.setattr(kilde._tilgang, "klient", lambda accept=None: _LukkbarKlient())
    monkeypatch.setattr(sjotemperatur._http, "get",
                        lambda c, url, hva=None, **kw: FalsktSvar())

    # Veien backfillen går: hent_uke() alene, ingen fetch().
    assert kilde.hent_uke(2026, 30) == tekst
    assert kilde.utvalg == {"rapporttype": ["Lice"]}

    # Og veien ukejobben går, som ender i den samme hent_uke().
    frisk = Sjotemperatur()
    monkeypatch.setattr(frisk._tilgang, "klient", lambda accept=None: _LukkbarKlient())
    assert frisk.fetch("2026-08-24") == tekst
    assert frisk.utvalg == {"rapporttype": ["Lice"]}


class _LukkbarKlient:
    def close(self):
        pass
