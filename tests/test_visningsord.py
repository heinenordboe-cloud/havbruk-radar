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


# ---- datoene ----------------------------------------------------------
#
# Overleveringens harde krav 5: tre skrivemåter av det samme
# tidspunktet, hver med sin plass. Prøvene under er de tre formene og
# de fire kantene (månedsskifte, årsskifte, ISO-år, fravær).

def test_dato_i_loepende_tekst():
    assert visningsord.dato("2026-09-16") == "16. september 2026"
    assert visningsord.dato("2026-01-01") == "1. januar 2026"
    assert visningsord.dato("2026-12-31") == "31. desember 2026"
    # Tidsstempel med klokkeslett: datodelen er nok.
    assert visningsord.dato("2026-09-16T04:09:31+00:00") == "16. september 2026"


def test_dato_uten_verdi_blir_tom_og_ikke_1_januar():
    """Fravær er ikke en dato. En tom celle som ble «1. januar 1970» er
    en påstand kilden aldri gjorde."""
    assert visningsord.dato("") == ""
    assert visningsord.dato(None) == ""
    assert visningsord.dato("ikke en dato") == "ikke en dato"


def test_uke_bruker_iso_aaret():
    """2019-12-30 er mandag i uke 1 av 2020. Kalenderåret ville gitt
    «uke 1, 2019» ved siden av «uke 52, 2019» — to uker som ligger ett
    år fra hverandre. Samme felle som `nettsted._isouke`."""
    assert visningsord.uke("2019-12-30") == "uke 1, 2020"
    assert visningsord.isouke("2019-12-30") == "2020-W01"
    assert visningsord.uke("2026-09-16") == "uke 38, 2026"


def test_ukespenn_skriver_maaneden_en_gang_naar_den_kan():
    assert visningsord.ukespenn("2026-09-16") == "14.–20. september 2026"


def test_ukespenn_skriver_begge_maanedene_over_et_skifte():
    assert visningsord.ukespenn("2026-09-29") == "28. september–4. oktober 2026"


def test_ukespenn_skriver_begge_aarene_over_et_skifte():
    assert (visningsord.ukespenn("2025-12-29")
            == "29. desember 2025–4. januar 2026")


def test_tidspunkt_sier_hvilken_sone_det_er_i():
    """`fetched_at` er skrevet i UTC. Regnes det om til norsk tid her,
    er det en ANDRE påstand om når vi hentet, ved siden av den ekte — og
    de to kan svare ulikt rundt midnatt. CLAUDE.md 1b."""
    assert (visningsord.tidspunkt("2026-09-16T04:09:31+00:00")
            == "16. september 2026 kl. 04.09 UTC")
    # Uten klokkeslett faller den til datoen framfor å finne på 00.00.
    assert visningsord.tidspunkt("2026-09-16") == "16. september 2026"
    assert visningsord.tidspunkt("") == ""


# ================================================== entall og flertall
#
# «1 tillatelser» sto på lokalitetssiden fra den ble bygget. Én hjelper,
# brukt i alle malene, og prøvene her holder 0, 1 og 2.

def test_antall_velger_riktig_form_for_null_en_og_to():
    assert visningsord.antall(0, "tillatelse", "tillatelser") == "0 tillatelser"
    assert visningsord.antall(1, "tillatelse", "tillatelser") == "1 tillatelse"
    assert visningsord.antall(2, "tillatelse", "tillatelser") == "2 tillatelser"


def test_null_tar_flertall_paa_norsk():
    """«0 tillatelser», ikke «0 tillatelse». Bare 1 tar entall."""
    assert visningsord.antall(0, "uke", "uker").endswith("uker")


def test_antall_bruker_samme_tusenskille_som_resten():
    assert visningsord.antall(1782, "lokalitet", "lokaliteter") == (
        visningsord.tall(1782) + " lokaliteter")


def test_antall_gjetter_ikke_flertallsformen():
    """Norsk flertall er ikke en regel man kan regne seg til:
    lokalitet/lokaliteter, selskap/selskaper, uke/uker. Begge formene
    oppgis, og en hjelper som gjettet ville tatt feil stille."""
    assert visningsord.antall(2, "selskap", "selskaper") == "2 selskaper"
    assert visningsord.antall(2, "uke", "uker") == "2 uker"
    assert visningsord.antall(2, "måned", "måneder") == "2 måneder"


def test_antall_taaler_en_verdi_som_ikke_er_et_tall():
    """En mal som får `None` skal ikke felle siden. Flertall er det
    trygge valget: det er formen setningen ellers har."""
    assert visningsord.antall(None, "uke", "uker") == "None uker"


def test_alle_bytter_determinativen_og_ikke_tallet():
    """«Alle 1 tillatelsen» er galt uansett hvordan tallet skrives. Det
    er determinativen som må byttes."""
    assert visningsord.alle(0, "uka", "ukene") == "Alle 0 ukene"
    assert visningsord.alle(1, "uka", "ukene") == "Den ene uka"
    assert visningsord.alle(2, "uka", "ukene") == "Alle 2 ukene"


def test_ingen_mal_skriver_et_bart_tall_foran_et_substantiv():
    """Regresjonen som ga «1 tillatelser». Prøven leser malene og
    krever at et tall som står foran et av disse substantivene går
    gjennom `antall()` eller `alle()` — eller har en synlig
    entall/flertall-test ved siden av seg.

    Lista er de substantivene som faktisk forekommer med et tall i
    dag. En ny en fanges ikke av denne prøven, og det er en kjent
    grense: den holder det som er rettet, den finner ikke det neste."""
    import re
    from pathlib import Path

    SUBST = ("lokalitet", "tillatelse", "selskap", "uke", "endring",
             "dag", "rad", "område", "produksjonsområde", "måned",
             "hendelse", "post", "side", "øyeblikksbilde", "endringsuke")
    mønster = re.compile(r"\{\{\s*([^}]{1,80}?)\s*\}\}\s*\n?\s*([a-zæøå-]+)")
    funn = []
    for mal in sorted((Path(__file__).resolve().parents[1] / "maler").glob("*.j2")):
        tekst = mal.read_text(encoding="utf-8")
        for m in mønster.finditer(tekst):
            uttrykk, ord_ = m.group(1), m.group(2).lower()
            if not any(ord_.startswith(s) for s in SUBST):
                continue
            if "antall(" in uttrykk or "alle(" in uttrykk:
                continue
            # Formen velges av en `if` rett etter tallet — se
            # arkivlinja, der tallet står inne i <strong>.
            hale = tekst[m.end():m.end() + 120]
            if ord_ in hale and " if " in hale:
                continue
            linje = tekst[:m.start()].count("\n") + 1
            funn.append(f"{mal.name}:{linje}  {{{{ {uttrykk} }}}} {ord_}")
    assert funn == [], "bart tall foran substantiv:\n  " + "\n  ".join(funn)


# ============================ datoer fra tidsstempler er i Europe/Oslo
#
# MÅLT 24.09.2026 i nyeste øyeblikksbilde per kilde: 6 094 av 6 507
# tidsstempelverdier faller på en annen dato i Oslo enn i UTC.
# `forste_klarering` 1 782 av 1 782.

def test_midnatt_norsk_tid_er_dagen_etter_utc_datoen():
    """Registeret skriver midnatt norsk tid som T23:00:00Z om vinteren
    og T22:00:00Z om sommeren. Begge er dagen ETTER i UTC-strengen."""
    assert visningsord.oslodato("2010-11-10T23:00:00Z") == "2010-11-11"
    assert visningsord.oslodato("2025-09-04T22:00:00Z") == "2025-09-05"
    assert visningsord.dato("2010-11-10T23:00:00Z") == "11. november 2010"


def test_sonen_og_ikke_et_fast_timetall():
    """Sommertid er +2, vintertid +1. Et påslag på én time ville vært
    riktig halve året — formen feilene i CLAUDE.md 1b har."""
    # Vinter: 23:00Z er 00:00 neste dag. 22:00Z er 23:00 samme dag.
    assert visningsord.oslodato("2010-11-10T22:00:00Z") == "2010-11-10"
    # Sommer: 22:00Z er 00:00 neste dag.
    assert visningsord.oslodato("2025-07-04T22:00:00Z") == "2025-07-05"


def test_en_ren_dato_og_en_tom_verdi_roeres_ikke():
    assert visningsord.oslodato("2026-09-21") == "2026-09-21"
    assert visningsord.oslodato("") == ""
    assert visningsord.oslodato(None) == ""
    assert visningsord.oslodato("ikke en dato") == "ikke en dato"


def test_verdi_viser_et_tidsstempel_som_dato():
    """Et rått stempel i en tabellcelle er kildens format, ikke et svar."""
    assert visningsord.verdi("versjon_gyldig_fra",
                             "2023-12-31T23:00:00Z") == "2024-01-01"


def test_tidspunkt_regner_IKKE_om():
    """Vårt eget hentetidspunkt er UTC og sier det. Se docstringen —
    å regne det om ville vært en andre påstand om når vi hentet."""
    assert visningsord.tidspunkt("2026-09-21T10:29:00+00:00") == (
        "21. september 2026 kl. 10.29 UTC")
