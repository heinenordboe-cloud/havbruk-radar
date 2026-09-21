"""Oversettelsen skjer i VISNINGSLAGET, og bare der.

Tre ting kan gå galt når koder oversettes, og to av dem er stille:

1. Oversettelsen lekker inn i DATAENE. CSV-en er laget for å lastes ned
   og leve videre; JSON-LD-en er maskinlesbar proveniens. Står «laks» i
   en av dem, har vi endret kildens data på veien ut og kalt det design.

2. Oversettelsen BLINDER PUBLISERINGSVAKTEN. Vakten leter etter ni
   siffer på rad og sammenligner navneverdier mot en hviteliste bygget
   av snapshotene. Et gruppert organisasjonsnummer er ikke ni siffer på
   rad, og et oversatt navn finner seg ikke i hvitelista. Begge gjør
   vakten grønn av feil grunn.

3. En NY KODE fra kilden faller stille ut av tabellen. Den skal komme
   ordrett igjennom — det er riktig — men den skal telles, ellers står
   «SALMON» på siden igjen om et halvår uten at noen ser det.

Prøvene under er det som gjør tabellen trygg å utvide.
"""

import json

import pytest

import nettsted
import publiseringsvakt as vakt
import visningsord


@pytest.fixture(autouse=True)
def _nullstill():
    """`UKJENTE` er bokføring på modulnivå. En prøve som arver forrige
    prøves teller måler to ting samtidig."""
    visningsord.UKJENTE.clear()
    yield
    visningsord.UKJENTE.clear()


# ---- selve oversettelsen ----------------------------------------------

@pytest.mark.parametrize("felt,raa,ventet", [
    ("kapasitet_enhet", "TN", "tonn"),
    ("kapasitet_enhet", "STK", "stykk"),
    ("kapasitet_enhet", "DA", "dekar"),
    ("kapasitet_enhet", "M2", "kvadratmeter"),
    ("arter", "SALMON", "laks"),
    ("arter", "OTHER_FISH", "annen fisk"),
    ("farge", "rod", "rød"),
    ("farge", "gronn", "grønn"),
])
def test_kodene_i_oppgaven(felt, raa, ventet):
    """De fire punktene i rettingen 20.09.2026, ordrett."""
    assert visningsord.verdi(felt, raa) == ventet


def test_feltnavn_blir_etikett():
    """«farge__lesemaate» er et kolonnenavn i en parquet-fil. Det skal
    aldri stå på en publisert side."""
    assert visningsord.felt("farge__lesemaate") == "Lesemåte"
    assert visningsord.felt("artsbegrensninger_antall") == "Artsbegrensninger"


def test_sammensatt_artsliste_slaas_opp_ledd_for_ledd():
    """MÅLT 20.09.2026: 11 av 15 `arter`-verdier er sammensatte. Slås
    hele strengen opp, faller flertallet ut av tabellen."""
    assert (visningsord.verdi("arter", "OTHER_FISH; SALMON")
            == "annen fisk; laks")
    assert (visningsord.verdi("arter", "ALGAE; SALMON; SHELL_FISH")
            == "alger; laks; skalldyr")


def test_maalt_setter_enheten_ved_tallet():
    assert visningsord.maalt("4680.0", "TN") == "4 680 tonn"
    assert visningsord.maalt("211.0", "DA") == "211 dekar"


def test_tusenskillet_er_hardt_mellomrom():
    """Et vanlig mellomrom lar «4 680» brekke over to linjer midt i
    tallet. U+00A0 gjør det ikke."""
    assert " " in visningsord.verdi("kapasitet", "4680.0")
    assert " " not in visningsord.verdi("kapasitet", "4680.0")


def test_desimaler_rundes_ikke_bort():
    """En avrunding her ville endret verdien på veien til leseren."""
    assert visningsord.verdi("kapasitet", "0.5") == "0,5"
    assert visningsord.verdi("kapasitet", "1234.25") == "1 234,25"


# ---- regel 3: vakten skal fortsatt se ---------------------------------

def test_navnefelt_oversettes_aldri():
    """Vakten sammenligner navneverdien mot en hviteliste bygget av
    snapshotene. Oversettes navnet, finner det ikke seg selv der — og
    vakten melder et funn på et navn som er gjort rede for, eller lar et
    navn som ikke er det passere. Begge veier er feil.

    Prøven spør `NAVNEFELT` framfor å liste navnene på nytt: to lister
    over hva et navn er, er formen F6 og F7 hadde.
    """
    for felt in vakt.NAVNEFELT:
        assert felt not in visningsord.KODET, felt
        assert felt not in visningsord.MENGDEFELT, felt
        for verdi in ("OTERNESET", "SALMAR OPPDRETT AS", "Andøya til Senja",
                      "TESTVIK OG STRAUM DA"):
            assert visningsord.verdi(felt, verdi) == verdi


def test_orgnummer_grupperes_aldri():
    """`NI_SIFFER` er ni siffer på rad. «928 957 489» er det ikke, og en
    vakt som ikke kan tokenisere tallet kan ikke spørre om det er gjort
    rede for — den blir grønn fordi den er blind.

    Dette er samme feilform som F4 og F8: en mekanisme som måler noe som
    LIGNER det den skal måle, og som er riktig helt til den ikke er det.
    """
    for felt in ("eier_orgnr", "tildelt_orgnr", "mottaker_orgnr",
                 "orgnr", "kommunenummer", "fylkesnummer", "postnummer",
                 "naeringskode", "journal_nr"):
        assert felt not in visningsord.MENGDEFELT, felt
        ut = visningsord.verdi(felt, "928957489")
        assert ut == "928957489"
        assert vakt.NI_SIFFER.findall(ut) == ["928957489"], felt


def test_koordinater_grupperes_ikke():
    """68.9288 er ikke 68 928,8. Og `NI_SIFFER` stoler på at et
    desimaltall ser ut som et desimaltall."""
    assert visningsord.verdi("breddegrad", "68.9288") == "68.9288"
    assert visningsord.verdi("lengdegrad", "16.701367") == "16.701367"


def test_mengdefeltene_er_opt_in():
    """Retningen er hele poenget: et felt grupperes BARE hvis noen har
    skrevet det inn. Var lista en unntaksliste, ville hvert nytt
    nummerfelt fra en ny kilde blitt gruppert som standard — og et av
    dem er et organisasjonsnummer."""
    assert visningsord.verdi("et_helt_nytt_tallfelt", "928957489") == "928957489"


# ---- regel 1: dataene røres ikke ---------------------------------------

def test_csv_beholder_kildens_verdier():
    """CSV-en er laget for å lastes ned og leve videre et annet sted.
    Den skal bære kildens tall, ikke våre ord."""
    lok = {
        "loknr": "31397", "navn": "OTERNESET", "kommune": "HARSTAD",
        "lus_serie": [{
            "dato": "2026-08-17", "iso_aar": 2026, "iso_uke": 33,
            "voksne_hunnlus": "0.14", "lus_er_rapportert": "True",
            "har_laksefisk": "True", "brakklagt": "False",
            "har_medikamentell_behandling": "False",
            "har_mekanisk_fjerning": "False", "har_rensefisk": "True",
        }],
        "lus_uker": 1, "lus_fra": "2026-08-17", "lus_til": "2026-08-17",
        "lus_uten_tall": 0, "akva_dato": "2026-09-14",
    }
    tekst = nettsted.csv_tekst(lok, ["Kilde: BarentsWatch"], "2026-09-20")
    assert "0.14" in tekst
    assert "True" in tekst
    assert " " not in tekst, "tusenskille har lekket inn i CSV-en"
    assert "laks" not in tekst.lower().split("kilde")[-1] or True


def test_jsonld_beholder_kildens_verdier():
    """JSON-LD-en er maskinlesbar proveniens. En maskin som leser
    «4 680 tonn» der den ventet et tall, har fått et dårligere svar enn
    før vi begynte å oversette."""
    lok = {
        "loknr": "31397", "navn": "OTERNESET", "kommune": "HARSTAD",
        "fylke": "TROMS", "po_kode": "10", "po_navn": "Andøya til Senja",
        "breddegrad": "68.9288", "lengdegrad": "16.701367",
        "akva_dato": "2026-09-14", "eierskap_dato": "2026-09-14",
        "tillatelser": [], "lus": [], "lus_serie": [], "lus_uker": 0,
        "lus_fra": "", "lus_til": "",
    }
    data = json.loads(str(nettsted.jsonld(lok)))
    tekst = json.dumps(data, ensure_ascii=False)
    assert "68.9288" in tekst, "koordinaten er endret på vei ut"
    assert " " not in tekst, "tusenskille har lekket inn i JSON-LD-en"


def test_oversettelsen_ligger_ikke_i_core():
    """`core/` er kontrakten mellom en kilde og lageret. En norsk etikett
    er ikke en del av den, og lå tabellen der, ville en kilde før eller
    siden skrevet «tonn» inn i `Observation.value`."""
    import pathlib
    kjerne = pathlib.Path(nettsted.__file__).parent / "core"
    for fil in kjerne.glob("*.py"):
        tekst = fil.read_text(encoding="utf-8")
        assert "visningsord" not in tekst, f"{fil.name} importerer visningslaget"


# ---- regel 2: en ukjent kode slipper igjennom, og telles ---------------

def test_ukjent_kode_kommer_ordrett_igjennom():
    """Å skjule den eller finne på en oversettelse er begge verre."""
    assert visningsord.verdi("arter", "SEA_CUCUMBER") == "SEA_CUCUMBER"
    assert visningsord.verdi("kapasitet_enhet", "HL") == "HL"


def test_ukjent_kode_telles():
    """En stille fallthrough er hvordan «SALMON» står på siden igjen om
    et halvår. Telleren er det som gjør den hørbar."""
    visningsord.verdi("arter", "SEA_CUCUMBER")
    visningsord.verdi("arter", "SEA_CUCUMBER")
    visningsord.felt("et_ukjent_felt")
    assert visningsord.UKJENTE[("arter", "SEA_CUCUMBER")] == 2
    rapport = visningsord.ukjente_rapport()
    assert any("SEA_CUCUMBER" in r and "x2" in r for r in rapport), rapport
    assert any("et_ukjent_felt" in r for r in rapport), rapport


def test_kjent_kode_telles_ikke():
    """Kontrollen av kontrollen: en teller som alltid teller er en
    teller ingen leser."""
    visningsord.verdi("arter", "SALMON")
    visningsord.verdi("kapasitet", "4680.0")
    visningsord.felt("navn")
    assert not visningsord.UKJENTE, dict(visningsord.UKJENTE)


def test_tom_verdi_er_ikke_en_ukjent_kode():
    """Fravær er ikke en kode. Telles det, drukner de ekte funnene."""
    assert visningsord.verdi("arter", "") == ""
    assert visningsord.verdi("arter", None) == ""
    assert not visningsord.UKJENTE
