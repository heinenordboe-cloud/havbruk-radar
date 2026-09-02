"""Eierskapskjeden — og personvernfilteret, som er hele grunnen til at
denne fila er lang.

Kilden henter navn på juridiske enheter fra et register der noen av
enhetene er MENNESKER. Havner et personnummer eller en bostedsadresse i
git, er det uopprettelig: rå-arkivet er append-only, og historikken kan
ikke skrives om uten å skrive om hele repoet.

Derfor testes filteret i BEGGE lag hver for seg, med konstruerte rader
som ikke finnes i den ekte responsen.
"""

import pytest

from core import persondata
from sources import eierskap
from sources.eierskap import Eierskap


# ---------------------------------------------------- de to vilkårene

@pytest.mark.parametrize("nr, ventet", [
    ("969159570", True),      # ekte organisasjonsnummer
    (969159570, True),        # tall, ikke streng
    (" 969159570 ", True),    # mellomrom rundt
    ("12345678901", False),   # ELLEVE siffer — fødselsnummer
    ("", False),              # tomt: privatperson hos Fiskeridirektoratet
    (None, False),
    ("96915957", False),      # åtte
    ("96915957O", False),     # bokstav forkledd som null
])
def test_ni_siffer_prover(nr, ventet):
    assert eierskap.er_organisasjonsnummer(nr) is ventet


def test_ellevesifret_nummer_er_ikke_organisasjonsnummer():
    """Kravet ordrett: et ellevesifret nummer skal ALDRI passere."""
    assert eierskap.er_organisasjonsnummer("12345678901") is False


@pytest.mark.parametrize("t", ["Person", "SoleProprietorship"])
def test_persontyper_kjennes_igjen(t):
    assert eierskap.er_person(t) is True


@pytest.mark.parametrize("t", [
    "LimitedLiabilityCompany", "PublicLimitedCompany",
    "JointLiabilityCompany", "UnlimitedLiabilityCompany",
    "Foundation", "Municipality", None, "",
])
def test_selskapsformer_slipper_gjennom(t):
    assert eierskap.er_person(t) is False


def test_enk_stoppes_selv_med_gyldig_organisasjonsnummer():
    """KJERNEN i hele filteret, og grunnen til at det ikke er en
    sifferprøve.

    Målt 02.09.2026: 8 av 8 enkeltpersonforetak i registeret har NI
    SIFFER. En ren sifferprøve ville sluppet hvert eneste av dem
    gjennom. Det er ordrett feilen CLAUDE.md regel 3 er skrevet om.
    """
    assert eierskap.er_organisasjonsnummer("985937028") is True
    assert eierskap._tillat("SoleProprietorship", "985937028") is False


def test_privatperson_stoppes_av_begge_vilkaar():
    assert eierskap._tillat("Person", "") is False
    # Og selv om nummeret hadde vært der, stopper typen den.
    assert eierskap._tillat("Person", "969159570") is False


def test_selskap_slipper_gjennom():
    assert eierskap._tillat("LimitedLiabilityCompany", "969159570") is True


def test_enk_er_samme_vurdering_som_kjernens():
    """Kildens PERSONTYPER og core/persondata.PERSONFORMER skal si det
    samme om det samme. To lister som kan svare ulikt er formen F6/F7."""
    assert eierskap.FORM_KART["SoleProprietorship"] in persondata.PERSONFORMER
    for t in eierskap.PERSONTYPER:
        kode = eierskap.FORM_KART.get(t)
        if kode:
            assert persondata.er_personform(kode)


# ------------------------------------------------- lag 1: fetch()

def _svar(monkeypatch, enheter, lisenser):
    """Lar fetch() kjøre uten nett."""
    def falsk(self, c, sti):
        return enheter if sti == "/entities" else lisenser
    monkeypatch.setattr(Eierskap, "_alt", falsk)
    monkeypatch.setattr("httpx.Client", lambda **k: type(
        "C", (), {"close": lambda s: None})())


ENHET_AS = {"id": "AAA", "openNr": "969159570",
            "typeValue": "LimitedLiabilityCompany", "name": "EKTE LAKS AS",
            "addresses": [{"type": "Location", "value": "Havnegata 1"}]}
ENHET_PERSON = {"id": "BBB", "openNr": "", "typeValue": "Person",
                "name": "NORDMANN, OLA",
                "addresses": [{"type": "ResidentialLocation",
                               "value": "Hjemmeveien 3", "zipCode": "5419",
                               "officialSourceType": "FREG"}]}
ENHET_ENK = {"id": "CCC", "openNr": "985937028",
             "typeValue": "SoleProprietorship", "name": "LYSEN ANNE",
             "addresses": []}
# Konstruert: et ELLEVESIFRET nummer, som kravet ber om.
ENHET_FNR = {"id": "DDD", "openNr": "12345678901",
             "typeValue": "LimitedLiabilityCompany", "name": "MISTENKELIG",
             "addresses": []}


def _lisens(nr, eier_id, orgnr):
    return {"licenseNr": nr, "legalEntityNrId": eier_id,
            "openLegalEntityNr": orgnr, "legalEntityName": "X",
            "connections": [{"siteNr": "10001", "active": True}]}


def test_lag1_slipper_bare_selskapet_gjennom(monkeypatch):
    _svar(monkeypatch,
          [ENHET_AS, ENHET_PERSON, ENHET_ENK, ENHET_FNR],
          [_lisens("A-A-0001", "AAA", "969159570"),
           _lisens("A-A-0002", "BBB", ""),
           _lisens("A-A-0003", "CCC", "985937028"),
           _lisens("A-A-0004", "DDD", "12345678901")])

    raa = Eierskap().fetch("2026-09-02")
    nr = [l["licenseNr"] for l in raa["tillatelser"]]
    assert nr == ["A-A-0001"]
    assert raa["personer_fjernet"] == 3


def test_lag1_arkiverer_ikke_bostedsadresser(monkeypatch):
    """Kroppen som arkiveres skal ikke inneholde FREG-adresser.

    Rå-arkivet ligger i git og er append-only. En bostedsadresse som
    kommer inn der, kan ikke fjernes igjen.
    """
    _svar(monkeypatch, [ENHET_AS, ENHET_PERSON],
          [_lisens("A-A-0001", "AAA", "969159570")])

    raa = Eierskap().fetch("2026-09-02")
    tekst = repr(raa)
    assert "Hjemmeveien" not in tekst
    assert "ResidentialLocation" not in tekst
    assert "FREG" not in tekst
    assert "NORDMANN, OLA" not in tekst
    # Og selskapet er heller ikke lagret med adresse.
    assert "Havnegata" not in tekst


def test_lag1_ellevesifret_stoppes(monkeypatch):
    _svar(monkeypatch, [ENHET_FNR], [_lisens("A-A-0004", "DDD", "12345678901")])
    raa = Eierskap().fetch("2026-09-02")
    assert raa["tillatelser"] == []
    assert "12345678901" not in repr(raa)


def test_lag1_sier_fra_naar_filteret_ikke_fjernet_noe(monkeypatch):
    """Et filter som aldri fjerner noe er et filter ingen har prøvd."""
    _svar(monkeypatch, [ENHET_AS], [_lisens("A-A-0001", "AAA", "969159570")])
    k = Eierskap()
    k.fetch("2026-09-02")
    assert any("0 tillatelser" in a for a in k.advarsler)


# ------------------------------------------------- lag 2: parse()

def test_lag2_stopper_det_lag1_slapp_forbi():
    """Lag 2 er det eneste som står mellom en ARKIVERT kropp og disken.

    Kroppen her er konstruert som om den kom fra et arkiv skrevet FØR
    filteret fantes — nøyaktig veien `enhetsregisteret` beskriver.
    """
    raa = {"enheter": [ENHET_AS, ENHET_PERSON, ENHET_ENK, ENHET_FNR],
           "tillatelser": [_lisens("A-A-0001", "AAA", "969159570"),
                           _lisens("A-A-0002", "BBB", ""),
                           _lisens("A-A-0003", "CCC", "985937028"),
                           _lisens("A-A-0004", "DDD", "12345678901")]}
    obs = list(Eierskap().parse(raa, "2026-09-02"))
    ider = {o.entity_id for o in obs}
    assert ider == {"A-A-0001"}


def test_lag2_ellevesifret_naar_aldri_en_observasjon():
    raa = {"enheter": [ENHET_FNR],
           "tillatelser": [_lisens("A-A-0004", "DDD", "12345678901")]}
    obs = list(Eierskap().parse(raa, "2026-09-02"))
    assert obs == []
    assert "12345678901" not in repr(obs)


def test_lag2_enk_naar_aldri_en_observasjon():
    raa = {"enheter": [ENHET_ENK],
           "tillatelser": [_lisens("A-A-0003", "CCC", "985937028")]}
    assert list(Eierskap().parse(raa, "2026-09-02")) == []


def test_ukjent_eier_slipper_ikke_gjennom():
    """En tillatelse hvis eier ikke finnes i /entities har INGEN type.

    Da vet vi ikke om eieren er et menneske, og «vet ikke» skal ikke
    bety «slipp gjennom». Motsatt fallback av frekvensvakten, og med
    vilje: der er kostnaden en ekstra fil, her er den et personregister.
    """
    raa = {"enheter": [], "tillatelser": [_lisens("A-A-0001", "XXX", "969159570")]}
    assert list(Eierskap().parse(raa, "2026-09-02")) == []


# ------------------------------------------------------- innholdet

def test_kjeden_kommer_ut():
    raa = {"enheter": [ENHET_AS],
           "tillatelser": [_lisens("A-A-0001", "AAA", "969159570")]}
    felt = {o.field: o.value for o in Eierskap().parse(raa, "2026-09-02")}
    assert felt["eier_orgnr"] == "969159570"
    assert felt["lokaliteter"] == "10001"
    assert felt["lokaliteter_antall"] == "1"
    assert felt["organisasjonsform"] == "AS"


def test_utgatte_koblinger_telles_ikke():
    l = _lisens("A-A-0001", "AAA", "969159570")
    l["connections"].append({"siteNr": "99999", "active": False})
    raa = {"enheter": [ENHET_AS], "tillatelser": [l]}
    felt = {o.field: o.value for o in Eierskap().parse(raa, "2026-09-02")}
    assert felt["lokaliteter"] == "10001"


def test_ingen_adressefelter_i_kontrakten():
    """Regel 3: gateadresser hentes bevisst ikke inn."""
    for felt in eierskap.FELTER:
        assert "adress" not in felt.lower()
        assert "postnummer" not in felt.lower()


def test_kilden_leser_aldri_klokka():
    """CLAUDE.md 1b: kilden får datoen inn."""
    kilde = eierskap.Eierskap()
    assert kilde.gjelder_for("2026-09-02") == "2026-09-02"
    assert kilde.gjelder_for("2020-01-01") == "2020-01-01"


def test_published_at_settes_ikke(monkeypatch):
    """Verifisert 02.09.2026: tjenesten sender verken Last-Modified
    eller ETag. Regel 1b-7 — standarden er «vet ikke»."""
    _svar(monkeypatch, [ENHET_AS], [_lisens("A-A-0001", "AAA", "969159570")])
    k = Eierskap()
    k.fetch("2026-09-02")
    assert getattr(k, "published_at", "") == ""
