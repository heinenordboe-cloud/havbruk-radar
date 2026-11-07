"""Kontaktfelt ut av rå-arkivet (regel 3).

Fram til 09.11.2026 la `enhetsregisteret` hele Brreg-svaret i
`data/arkiv/`. Fila fra 02.11.2026 hadde 1 655 gateadresser, 455
telefonnumre, 332 mobilnumre og 439 e-postadresser. Testene under låser
de to halvdelene, slik testene for personformene gjør det:

  - filteret i kilden: `fetch()` tar feltene ut, og `parse()` gir de
    samme observasjonene av en kropp før og etter;
  - vakten i arkivskriveren: `raw.arkiver()`, `raw.arkiver_ny()` og
    `karantene.sett_inn()` nekter å skrive en kropp som har dem.

Verdiene er oppdiktet. Feltstiene er Brregs, målt på arkivet fra
02.11.2026 (73 stier i 1 805 enheter).
"""

import copy
import gzip
import hashlib
import json

import pytest

from core import karantene, persondata
from core import raw as raw_arkiv


def _enhet(orgnr: str = "922222222", form: str = "AS") -> dict:
    """En aktiv enhet med alle feltene et Brreg-svar har, også de
    sjeldne (påtegninger, kapital.innbetalt, tvangsoppløsning)."""
    return {
        "_links": {"self": {"href": f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"}},
        "aktivitet": ["Oppdrett av laks"],
        "antallAnsatte": 12,
        "epostadresse": "post@example.com",
        "erIKonsern": True,
        "forretningsadresse": {
            "adresse": ["Kaiveien 1"], "kommune": "FRØYA", "kommunenummer": "5014",
            "land": "Norge", "landkode": "NO", "postnummer": "7260",
            "poststed": "SISTRANDA"},
        "fravalgRevisjonBeslutningsDato": "2020-01-01",
        "fravalgRevisjonDato": "2020-01-02",
        "frivilligMvaRegistrertBeskrivelser": ["Utleie"],
        "harRegistrertAntallAnsatte": True,
        "historiskeNavn": [{"fraDato": "2001-01-01", "navn": "Gammel Laks AS",
                            "tilDato": "2010-01-01"}],
        "hjelpeenhetskode": {"beskrivelse": "x", "kode": "1"},
        "hjemmeside": "www.example.com",
        "institusjonellSektorkode": {"beskrivelse": "Private aksjeselskaper",
                                     "kode": "2100"},
        "kapital": {"antallAksjer": 100, "belop": 30000.0, "fulltInnbetalt": True,
                    "innbetalt": 30000.0, "innfortDato": "2001-01-01",
                    "type": "Aksjekapital", "valuta": "NOK"},
        "konkurs": False,
        "konkursdato": "2026-01-01",
        "maalform": "Bokmål",
        "mobil": "900 00 000",
        "naeringskode1": {"beskrivelse": "Hav- og kystbasert akvakultur",
                          "kode": "03.211"},
        "naeringskode2": {"beskrivelse": "y", "kode": "46.381"},
        "naeringskode3": {"beskrivelse": "z", "kode": "10.201"},
        "navn": "Testlaks AS",
        "organisasjonsform": {"_links": {"self": {"href": "x"}},
                              "beskrivelse": "Aksjeselskap", "kode": form},
        "organisasjonsnummer": orgnr,
        "paategninger": [{"infotype": "FADR", "innfoertDato": "2025-01-01",
                          "tekst": "Enhetsregisteret har grunn til å anta at "
                                   "forretningsadressen er feil."}],
        "postadresse": {
            "adresse": ["Postboks 1"], "kommune": "FRØYA", "kommunenummer": "5014",
            "land": "Norge", "landkode": "NO", "postnummer": "7261",
            "poststed": "SISTRANDA"},
        "registreringsdatoAntallAnsatteEnhetsregisteret": "2020-01-01",
        "registreringsdatoAntallAnsatteNAVAaregisteret": "2020-01-01",
        "registreringsdatoEnhetsregisteret": "2001-01-01",
        "registreringsdatoForetaksregisteret": "2001-01-01",
        "registreringsdatoFrivilligMerverdiavgiftsregisteret": "2002-01-01",
        "registreringsdatoMerverdiavgiftsregisteret": "2002-01-01",
        "registreringsdatoMerverdiavgiftsregisteretEnhetsregisteret": "2002-01-01",
        "registrertIForetaksregisteret": True,
        "registrertIFrivillighetsregisteret": False,
        "registrertIMvaregisteret": True,
        "registrertIPartiregisteret": False,
        "registrertIStiftelsesregisteret": False,
        "respons_klasse": "Enhet",
        "sisteInnsendteAarsregnskap": "2025",
        "stiftelsesdato": "2001-01-01",
        "telefon": "70 00 00 00",
        "tvangsopplostPgaMangelfulltStyreDato": "2026-01-01",
        "tvangsopplostPgaManglendeRegnskapDato": "2026-01-01",
        "tvangsopplostPgaManglendeRevisorDato": "2026-01-01",
        "underAvvikling": False,
        "underAvviklingDato": "2026-01-01",
        "underTvangsavviklingEllerTvangsopplosning": False,
        "vedtektsdato": "2001-01-01",
        "vedtektsfestetFormaal": ["Drive oppdrett av laks og ørret."],
    }


KONTAKTVERDIER = ("Kaiveien", "Postboks 1", "post@example.com",
                  "www.example.com", "900 00 000", "70 00 00 00")


def _side(*enheter: dict, total: int = 1) -> dict:
    return {"_embedded": {"enheter": list(enheter)},
            "_links": {"self": {"href": "https://data.brreg.no/x?page=0"}},
            "page": {"number": 0, "size": 100, "totalElements": len(enheter),
                     "totalPages": total}}


@pytest.fixture
def falsk_brreg(monkeypatch):
    """`fetch()` mot én næringskode, med `svar` som Brregs side. Svaret har
    bytene kilden hasher, slik et httpx-svar har."""
    from sources import _http
    from sources import enhetsregisteret as er

    monkeypatch.setattr(er, "get", lambda nokkel, standard=None: {
        "kilder.enhetsregisteret.naeringskoder": ["03.211"],
        "kilder.enhetsregisteret.sidestorrelse": 100,
        "kilder.enhetsregisteret.tillat_tomt": [],
    }.get(nokkel, standard))

    class Svar:
        def __init__(self, payload):
            self.content = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        def json(self):
            return json.loads(self.content)

    sendt = {}

    def sett(payload):
        sendt["svar"] = Svar(payload)

    monkeypatch.setattr(_http, "get", lambda *a, **kw: sendt["svar"])
    return sett


# ------------------------------------------------------------- filteret


def test_fetch_tar_kontaktfeltene_ut_og_beholder_geografien(falsk_brreg):
    from sources.enhetsregisteret import Enhetsregisteret

    falsk_brreg(_side(_enhet()))
    sider = Enhetsregisteret().fetch("2026-11-09")
    tekst = json.dumps(sider, ensure_ascii=False)

    for verdi in KONTAKTVERDIER:
        assert verdi not in tekst, verdi
    assert persondata.kontaktfelt_i(sider) == {}

    enhet = sider[0]["svar"]["_embedded"]["enheter"][0]
    assert enhet["forretningsadresse"] == {
        "kommune": "FRØYA", "kommunenummer": "5014", "land": "Norge",
        "landkode": "NO", "postnummer": "7260", "poststed": "SISTRANDA"}
    assert set(enhet["postadresse"]) == {"kommune", "kommunenummer", "land",
                                         "landkode", "postnummer", "poststed"}
    # Resten av enheten er urørt.
    assert enhet["navn"] == "Testlaks AS"
    assert enhet["paategninger"] == _enhet()["paategninger"]
    # Og konvolutten.
    assert sider[0]["svar"]["page"]["totalPages"] == 1


def test_fetch_lagrer_sha256_av_det_uredigerte_svaret(falsk_brreg):
    """Kroppen i arkivet er redigert, så den kan ikke selv bevise hva vi
    mottok. Hashen av de mottatte BYTENE kan."""
    from sources.enhetsregisteret import Enhetsregisteret

    payload = _side(_enhet())
    falsk_brreg(payload)
    sider = Enhetsregisteret().fetch("2026-11-09")

    mottatt = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert sider[0]["mottatt_sha256"] == hashlib.sha256(mottatt).hexdigest()
    # Og den er ikke hashen av det som arkiveres.
    redigert = json.dumps(sider[0]["svar"], ensure_ascii=False).encode("utf-8")
    assert sider[0]["mottatt_sha256"] != hashlib.sha256(redigert).hexdigest()


def test_fetch_teller_kontaktfeltene_i_meta(falsk_brreg):
    """Uten tallet kan ingen som leser kroppen skille «Brreg sluttet å
    sende telefon» fra «vi tok den ut»."""
    from sources.enhetsregisteret import Enhetsregisteret

    uten_telefon = _enhet("933333333")
    del uten_telefon["telefon"]
    falsk_brreg(_side(_enhet(), uten_telefon))
    sider = Enhetsregisteret().fetch("2026-11-09")

    meta = sider[-1]["meta"]
    assert {p["felt"]: p["antall"] for p in meta["kontaktfelt_fjernet"]} == {
        "epostadresse": 2, "forretningsadresse.adresse": 2, "hjemmeside": 2,
        "mobil": 2, "postadresse.adresse": 2, "telefon": 1}
    # Og kvitteringen stopper ikke kroppen i vakten.
    persondata.nekt_kontaktfelt("enhetsregisteret", sider)


def test_fetch_arkiveres_gjennom_vakten(falsk_brreg, tmp_path, monkeypatch):
    """Hele veien: det `fetch()` returnerer, slipper gjennom vakten, og
    fila på disk er uten feltene."""
    from sources.enhetsregisteret import Enhetsregisteret

    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    falsk_brreg(_side(_enhet()))
    raw_arkiv.arkiver("enhetsregisteret", "2026-11-09",
                      Enhetsregisteret().fetch("2026-11-09"))

    fil = tmp_path / "arkiv" / "enhetsregisteret" / "2026-11-09.json.gz"
    tekst = gzip.open(fil).read().decode("utf-8")
    for verdi in KONTAKTVERDIER:
        assert verdi not in tekst, verdi


def test_parse_gir_samme_observasjoner_foer_og_etter(falsk_brreg):
    """Et svar arkivert slik det ble før 09.11.2026 (hele svaret), og det
    samme svaret hentet gjennom dagens `fetch()`: parse() gir de samme
    observasjonene. FELTER leser ingen av feltene som er tatt ut."""
    from sources.enhetsregisteret import FELTER, Enhetsregisteret

    payload = _side(_enhet("922222222"), _enhet("944444444"),
                    _enhet("955555555", "ENK"))
    gammelt_arkiv = [{"naeringskode": "03.211", "side": 0,
                      "svar": copy.deepcopy(payload)},
                     {"meta": {"antall_filtrert": 0, "filtrert_per_form": {}}}]

    falsk_brreg(payload)
    nytt_arkiv = Enhetsregisteret().fetch("2026-11-09")

    def obs(raw):
        return sorted((o.entity_id, o.entity_name, o.field, o.value)
                      for o in Enhetsregisteret().parse(raw, "2026-11-09"))

    foer, etter = obs(gammelt_arkiv), obs(nytt_arkiv)
    assert foer == etter
    # Og prøven er ikke tom: alle feltene i FELTER som en aktiv enhet har,
    # er med. `slettedato` står bare på slettede enheter.
    assert {f for _, _, f, _ in foer} == set(FELTER) - {"slettedato"}
    assert {e for e, _, _, _ in foer} == {"922222222", "944444444"}


# --------------------------------------------------------------- vakten


@pytest.mark.parametrize("sti", sorted(
    list(persondata.KONTAKTFELT)
    + [f"{o}.{persondata.ADRESSELINJE}" for o in persondata.ADRESSEOBJEKTER]))
def test_arkiver_nekter_hvert_kontaktfelt(sti, tmp_path, monkeypatch):
    """Ett felt alene er nok. Kroppen ligger der kilden legger den, inne i
    en side, så vakten må lete i hele kroppen."""
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    enhet = {"organisasjonsnummer": "922222222"}
    if "." in sti:
        obj, linje = sti.split(".")
        enhet[obj] = {linje: ["Kaiveien 1"], "postnummer": "7260"}
    else:
        enhet[sti] = "noe"
    kropp = [{"naeringskode": "03.211", "side": 0, "svar": _side(enhet)}]

    with pytest.raises(ValueError, match=sti.replace(".", r"\.")):
        raw_arkiv.arkiver("enhetsregisteret", "2026-11-09", kropp)
    with pytest.raises(ValueError, match="kontaktfelt"):
        raw_arkiv.arkiver_ny("enhetsregisteret", "2026-11-09", kropp)

    # Ingenting er skrevet: en halvskrevet fil kan ikke tas tilbake.
    assert not (tmp_path / "arkiv" / "enhetsregisteret").exists() or \
        not list((tmp_path / "arkiv" / "enhetsregisteret").iterdir())


def test_arkiver_nekter_et_uredigert_brreg_svar(tmp_path, monkeypatch):
    """Det kroppen så ut som fram til 09.11.2026."""
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    kropp = [{"naeringskode": "03.211", "side": 0, "svar": _side(_enhet())}]

    with pytest.raises(ValueError) as e:
        raw_arkiv.arkiver("enhetsregisteret", "2026-11-09", kropp)
    for felt in ("telefon", "mobil", "epostadresse", "hjemmeside",
                 "forretningsadresse.adresse", "postadresse.adresse"):
        assert felt in str(e.value)
    # Feilmeldingen gjentar ikke verdiene.
    for verdi in KONTAKTVERDIER:
        assert verdi not in str(e.value)


def test_karantene_nekter_kropp_med_kontaktfelt(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    monkeypatch.setattr(karantene, "mappe_for",
                        lambda arkivmappe, merke="": tmp_path / "karantene")
    with pytest.raises(ValueError, match="kontaktfelt"):
        karantene.sett_inn("enhetsregisteret", "2026-11-09",
                           {"telefon": "70 00 00 00"}, "test")
    assert not (tmp_path / "karantene").exists()


def test_vakten_slipper_ren_kropp_og_tomme_felt(tmp_path, monkeypatch):
    """Et felt som står uten verdi bærer ingen opplysning, og en kropp som
    ikke er strukturert (PDF, HTML) prøves ikke."""
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    ren, _ = persondata.uten_kontaktfelt(_enhet())
    tomme = {"telefon": None, "mobil": "", "forretningsadresse": {"adresse": []}}

    raw_arkiv.arkiver("enhetsregisteret", "2026-11-09", [_side(ren), tomme])
    raw_arkiv.arkiver("vilkar-brreg", "2026-11-09", b'{"telefon": "70"}')
    assert len(list((tmp_path / "arkiv").rglob("*.gz"))) == 2


def test_uten_kontaktfelt_roerer_ikke_originalen():
    original = _enhet()
    ren, fjernet = persondata.uten_kontaktfelt(original)

    assert original == _enhet()
    assert sorted(fjernet) == ["epostadresse", "forretningsadresse.adresse",
                               "hjemmeside", "mobil", "postadresse.adresse",
                               "telefon"]
    assert persondata.kontaktfelt_i(ren) == {}
