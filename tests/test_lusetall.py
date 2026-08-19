"""Lusetall-kilden. Ingen nett — rå respons er etterlignet fra den
faktiske strukturen, se docs/BARENTSWATCH-FUNN.md."""

import datetime as dt

from core import snapshot
from sources.lusetall import (Lusetall, mandag, rapportert_andel,
                              uke_med_etterslep, _vurder_rapportering)


def _lok(nr, rapportert=True, brakk=False, lus=0.2):
    return {
        "localityNo": nr, "name": f"Lokalitet {nr}",
        "hasReportedLice": rapportert, "isFallow": brakk,
        "avgAdultFemaleLice": lus if rapportert else None,
        "hasCleanerfishDeployed": False, "hasMechanicalRemoval": False,
        "hasSubstanceTreatments": False, "hasPd": False, "hasIla": False,
        "isOnLand": False, "hasSalmonoids": True,
        "isSlaughterHoldingCage": False,
        "municipalityNo": "1149", "municipality": "Karmøy",
        "lat": 59.37, "lon": 5.21,
    }


def _uke(lokaliteter, aar=2026, uke=30):
    return {"year": aar, "week": uke, "localities": lokaliteter}


def test_mandag_i_iso_uka():
    """Valget står for alltid i filnavnene. Uke 30/2026 er 20. juli."""
    assert mandag(2026, 30) == "2026-07-20"
    assert mandag(2026, 34) == "2026-08-17"
    assert mandag(2012, 1) == "2012-01-02"      # årsskifte
    assert dt.date.fromisoformat(mandag(2026, 1)).weekday() == 0


def test_etterslep_regnes_i_uker():
    # 18.08.2026 er ISO-uke 34. Fire uker tilbake er uke 30.
    assert uke_med_etterslep(dt.date(2026, 8, 18), 4) == (2026, 30)
    assert uke_med_etterslep(dt.date(2026, 8, 18), 0) == (2026, 34)


def test_observed_at_er_uka_ikke_hentedagen():
    """Kjernen sender inn hentedagen; kilden vet at dataene gjelder uka."""
    obs = list(Lusetall().parse(_uke([_lok(10029)]), "2026-08-18"))
    assert obs
    assert {o.observed_at for o in obs} == {"2026-07-20"}


def test_ikke_rapportert_gir_rad_ikke_hull():
    """Skillet mellom «rapportert null» og «ikke rapportert» må overleve.
    Uten det blir en manglende rapport til en null i enhver analyse."""
    obs = list(Lusetall().parse(_uke([_lok(1, rapportert=False, brakk=True)]),
                                "2026-08-18"))
    felter = {o.field: o.value for o in obs}

    assert felter["lus_er_rapportert"] == "False"
    assert felter["brakklagt"] == "True"
    # Ingen luseverdi når ingenting er rapportert — det er riktig, og
    # lus_er_rapportert er det som gjør hullet lesbart.
    assert "voksne_hunnlus" not in felter


def test_rapportert_null_lus_er_ikke_manglende_rapport():
    obs = list(Lusetall().parse(_uke([_lok(1, rapportert=True, lus=0.0)]),
                                "2026-08-18"))
    felter = {o.field: o.value for o in obs}

    assert felter["lus_er_rapportert"] == "True"
    assert felter["voksne_hunnlus"] == "0.0"


def test_navn_emittes_ikke():
    """Akvakultur eier lokalitetsnavnet. To kilder med ulik skrivemåte
    ville lagt igjen en permanent falsk forskjell."""
    obs = list(Lusetall().parse(_uke([_lok(10029)]), "2026-08-18"))
    assert "navn" not in {o.field for o in obs}
    assert obs[0].entity_name == "Lokalitet 10029"   # men navnet følger med


def test_andel_maales_mot_aktive_ikke_totalen():
    """Mot totalen ville tallet vært rundt 32 % fordi to tredeler er
    brakklagte. Det ville gjort vakten meningsløs."""
    lok = ([_lok(i, rapportert=True) for i in range(9)]
           + [_lok(100, rapportert=False)]
           + [_lok(200 + i, rapportert=False, brakk=True) for i in range(90)])
    aktive, rapportert, andel = rapportert_andel(_uke(lok))

    assert (aktive, rapportert) == (10, 9)
    assert andel == 0.9


def test_lav_rapportering_gir_advarsel_ikke_exception():
    """Uka skal fortsatt skrives, men jobben skal bli rød."""
    lav = _uke([_lok(i, rapportert=(i < 2)) for i in range(10)], uke=34)
    varsler = _vurder_rapportering(lav)
    assert len(varsler) == 1 and "20.0%" in varsler[0]

    hoy = _uke([_lok(i, rapportert=(i < 9)) for i in range(10)])
    assert _vurder_rapportering(hoy) == []


def test_entity_id_er_localityno_som_tekst():
    """Koblingen mot akvakultur er på nummer, og entity_id er tekst der."""
    obs = list(Lusetall().parse(_uke([_lok(10029)]), "2026-08-18"))
    assert {o.entity_id for o in obs} == {"10029"}


def test_hele_uka_blir_en_ramme(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path)
    lok = [_lok(i, rapportert=(i % 2 == 0)) for i in range(50)]

    obs = list(Lusetall().parse(_uke(lok), "2026-08-18"))
    ramme = snapshot.to_frame(obs)

    assert ramme["entity_id"].n_unique() == 50
    assert ramme["observed_at"].unique().to_list() == ["2026-07-20"]
    # Alle får flaggene; bare de rapporterende får luseverdi.
    assert ramme.filter(ramme["field"] == "lus_er_rapportert").height == 50
    assert ramme.filter(ramme["field"] == "voksne_hunnlus").height == 25
