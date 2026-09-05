"""Vedtakskilden. Ingen nett og ingen ekte lovdata-sider.

HTML-fragmentene under er bygget av teksten slik `_tekst()` faktisk ser
den på de arkiverte kroppene 05.09.2026 — samme ordlyd, samme tegnsetting,
samme punktmarkører. Det er med vilje: skriver man dem av på nytt «pent»,
tester man sin egen antakelse om formatet i stedet for formatet.

De to viktigste testene her er `test_vaktene_*`. Uttrekk fra offentlige
dokumenter i dette repoet har feilet STILLE fire ganger, hver gang med
riktig form og feil tall, og vaktene er det eneste som gjør en slik feil
høylytt.
"""

import pytest

from sources import trafikklysvedtak as tv
from sources.trafikklysvedtak import (Forskriftsfeil, Rundemangler,
                                      Trafikklysvedtak, runde_av, siste_dag)


# ---- kropper, bygget av den faktiske ordlyden -------------------------

def _side(forskrift_id: str, ikraft: str, tittel: str, kropp: str) -> bytes:
    """Én lovdata-side: meny, metadatablokk, brødtekst.

    Menyen er med fordi den er der i virkeligheten, og fordi
    `_forskriftstekst()` finnes nettopp for å kutte den bort.
    """
    return (
        "<html><head><title>x</title></head><body>"
        "<nav>Til hovedinnhold Rettskilder Lover Norsk Lovtidend</nav>"
        f"<h1>{tittel}</h1>"
        # Innholdsfortegnelsen, som gjentar paragrafoverskriftene FØR
        # brødteksten. Et snitt over hele siden ville truffet disse.
        "<div class='toc'>§ 3. Produksjonsområder og justering av "
        "tillatelseskapasitet § 4. Utnyttelse § 5. Virkningstidspunkt</div>"
        f"<dl>Dato {forskrift_id} Departement Nærings- og fiskeridepartementet "
        f"Ikrafttredelse {ikraft} Gjelder for Norge</dl>"
        "<div>Hjemmel: Fastsatt av Nærings- og fiskeridepartementet med "
        "hjemmel i lov 17. juni 2005 nr. 79 om akvakultur (akvakulturloven) "
        "§ 5 og forskrift 16. januar 2017 nr. 61 om produksjonsområder for "
        "akvakultur av matfisk i sjø av laks, ørret og regnbueørret "
        "(produksjonsområdeforskriften) § 11 og § 12 ."
        f"{kropp}</div></body></html>"
    ).encode("utf-8")


TITTEL_2018 = ("Forskrift om kapasitetsøkning for tillatelser til "
               "akvakultur med matfisk i sjø av laks, ørret og "
               "regnbueørret i 2017-2018")
TITTEL_2020 = ("Forskrift om kapasitetsjusteringer for tillatelser til "
               "akvakultur med matfisk i sjø av laks, ørret og "
               "regnbueørret i 2020")
TITTEL_2022 = TITTEL_2020.replace("i 2020", "i 2022")
TITTEL_2024 = TITTEL_2020.replace("i 2020", "i 2024")


# 2018: «Kapittel 2 OM ØKT KAPASITET … gjelder», punktmarkør «a)», og
# INTET punktum etter det siste områdenavnet.
KROPP_2018 = (
    "Kapittel 1. Innledende bestemmelser "
    "§ 1. Formål Forskriften skal fremme … "
    "§ 3. Produksjonsområder og økning av kapasitet "
    "Kapittel 2 om økt kapasitet på eksisterende tillatelser gjelder "
    "tillatelse hjemmehørende i følgende produksjonsområder: "
    "a) Område 1: Svenskegrensen til Jæren "
    "b) Område 7: Nord-Trøndelag med Bindal "
    "c) Område 13: Øst-Finnmark "
    "Kapittel 3 gjelder i alle produksjonsområder. "
    "Kapittel 2. Tilbud om økt produksjonskapasitet på eksisterende "
    "tillatelser "
    "§ 4. Virkeområde Dette kapitlet gjelder tilbud om å øke maksimalt "
    "tillatt biomasse med 2 pst. "
    "§ 5. Kunngjøring av tilbud Tilbudet skal offentliggjøres …"
)

# 2020: tre kapittelledd, og fargeordet BARE i kapittel 4s overskrift.
KROPP_2020 = (
    "Kapittel 1. Innledende bestemmelser "
    "§ 1. Formål Forskriften skal fremme … "
    "§ 3. Produksjonsområder og justering av tillatelseskapasitet "
    "Kapittel 2 gjelder tillatelser hjemmehørende i følgende "
    "produksjonsområder: "
    "a. Område 1: Svenskegrensen til Jæren "
    "b. Område 2: Ryfylke. "
    "Kapittel 3 gjelder tillatelser hjemmehørende i alle "
    "produksjonsområder. "
    "Kapittel 4 gjelder tillatelser hjemmehørende i følgende "
    "produksjonsområder: "
    "a. Område 4: Nordhordland til Stadt "
    "b. Område 5: Stadt til Hustadvika. "
    "Kapittel 2. Tilbud om økt tillatelseskapasitet på eksisterende "
    "tillatelser "
    "§ 4. Virkeområde Dette kapitlet gjelder tilbud om å øke "
    "tillatelseskapasiteten med 1 prosent. "
    "§ 5. Kunngjøring av tilbud Tilbudet skal offentliggjøres … "
    "Kapittel 4. Nedjustering av tillatelseskapasitet i røde "
    "produksjonsområder "
    "§ 21. Utnyttelse av tillatelseskapasitet i produksjonsområder med "
    "uakseptabel miljøpåvirkning Tillatelser …"
)


def _kropp_tabell(gronne: str, rader: str, ekstra: str = "") -> str:
    return (
        "Kapittel 1. Innledende bestemmelser "
        "§ 1. Formål Forskriften skal fremme … "
        "§ 3. Produksjonsområder og justering av tillatelseskapasitet "
        "Kapitlene 1, 2, 4 og 5 gjelder tillatelser hjemmehørende i alle "
        "produksjonsområder. "
        "Kapittel 3 gjelder for følgende (grønne) produksjonsområder: "
        f"{gronne} "
        "Kapittel 2. Utnyttelse av tillatelser og registrering "
        "§ 4. Utnyttelse og justering av utnyttelse av tillatelseskapasitet "
        "Tillatelser som er omfattet av denne forskriften kan utnyttes slik: "
        "Produksjonsområde Justering Tidligere generell kapasitet Ny "
        f"generell kapasitetsutnyttelse {rader} "
        "Tillatelser hjemmehørende i øvrige produksjonsområder kan utnyttes "
        f"100 prosent. {ekstra}"
        "§ 5. Virkningstidspunkt for justering av kapasitet Tilbakestilling …"
        "Kapittel 3. Tilbud om økt tillatelseskapasitet på eksisterende "
        "tillatelser § 7. Virkeområde …"
    )


KROPP_2022 = _kropp_tabell(
    "a. Område 1: Svenskegrensen til Jæren b. Område 13: Øst-Finnmark.",
    "a. Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022) Ned 6 pst. "
    "100 pst. 94 pst. "
    "b. Produksjonsområde 5 (rødt lys i 2020, gult lys i 2022) Ingen "
    "justering 94 pst. 94 pst.",
)

KROPP_2024 = _kropp_tabell(
    "a. Område 1: Svenskegrensen til Jæren b. Område 13: Øst-Finnmark.",
    "a. Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022, rødt lys i "
    "2024) Ned 6 pst. 94 pst. 88,36 pst. "
    "b. Produksjonsområde 5 (rødt lys i 2020, gult lys i 2022, gult lys i "
    "2024) Ingen justering 94 pst. 94 pst.",
    # Prosaomtalen med LITEN forbokstav, som tabellvakten ikke skal lese
    # som en rad. Se docs/KILDE-TRAFIKKLYSVEDTAK.md punkt 5.
    "Tillatelser i produksjonsområde 3 og 4 som har fått fastsatt sin "
    "tillatelseskapasitet etter forskrift 7. juni 2022 nr. 972 kapittel 4 , "
    "får utnyttelsesgraden redusert med 6 prosent. ",
)


KROPPER = {
    "FOR-2017-12-20-2397": _side("FOR-2017-12-20-2397", "20.12.2017",
                                 TITTEL_2018, KROPP_2018),
    "FOR-2020-02-04-105": _side("FOR-2020-02-04-105", "04.02.2020",
                                TITTEL_2020, KROPP_2020),
    "FOR-2022-06-07-972": _side("FOR-2022-06-07-972", "07.06.2022",
                                TITTEL_2022, KROPP_2022),
    "FOR-2024-03-22-515": _side("FOR-2024-03-22-515", "22.03.2024",
                                TITTEL_2024, KROPP_2024),
}


def _farger(rå: bytes, dato: str) -> dict[str, str]:
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    return {o.entity_id: o.value for o in kilde.parse(rå, dato)
            if o.field == tv.F_FARGE}


def _lesemaater(rå: bytes, dato: str) -> dict[str, str]:
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    return {o.entity_id: o.value for o in kilde.parse(rå, dato)
            if o.field.endswith(tv.LESEMAATE_SUFFIKS)}


# ---- kalender ---------------------------------------------------------

def test_siste_dag_og_runde_av():
    assert siste_dag(2024) == "2024-12-31"
    assert runde_av("2024-12-31") == 2024


def test_runde_av_nekter_annen_dato():
    """Et snapshot som het 2024-03-22 ville påstått at departementet
    fargela «22. mars» og ikke tildelingsrunden."""
    with pytest.raises(ValueError, match="ikke årets siste dag"):
        runde_av("2024-03-22")


# ---- published_at -----------------------------------------------------

def test_published_at_er_ikrafttredelsen():
    for forskrift_id, ventet in (("FOR-2017-12-20-2397", "2017-12-20"),
                                 ("FOR-2020-02-04-105", "2020-02-04"),
                                 ("FOR-2022-06-07-972", "2022-06-07"),
                                 ("FOR-2024-03-22-515", "2024-03-22")):
        ut = tv._utgitt(tv._tekst(KROPPER[forskrift_id]))
        assert ut.startswith(ventet), (forskrift_id, ut)


def test_published_at_tom_naar_ikrafttredelse_ikke_er_fastsettelsen():
    """En utsatt eller tilbakevirkende ikrafttredelse svarer på et annet
    spørsmål enn published_at stiller. Da skal feltet bli TOMT, ikke
    gjettet — samme valg som ekspertgruppens vakt mot re-eksport."""
    rå = _side("FOR-2020-02-04-105", "01.09.2020", TITTEL_2020, KROPP_2020)
    advarsler: list[str] = []
    assert tv._utgitt(tv._tekst(rå), advarsler) == ""
    assert advarsler and "tilbakevirkende" in advarsler[0]


def test_published_at_bruker_ikke_hentetidspunktet():
    """Standarden er «vet ikke», aldri fetched_at. Uten et lesbart
    ikrafttredelsesfelt skal feltet være tomt — se
    Observation.published_at."""
    rå = _side("FOR-2020-02-04-105", "", TITTEL_2020, KROPP_2020)
    assert b"Ikrafttredelse" in rå and b"04.02.2020" not in rå
    advarsler: list[str] = []
    assert tv._utgitt(tv._tekst(rå), advarsler) == ""
    assert advarsler


# ---- gjenkjenning -----------------------------------------------------

def test_gjenkjenn_leser_dokumentet_ikke_rekkefolgen():
    for forskrift_id, rå in KROPPER.items():
        assert tv.gjenkjenn(tv._tekst(rå)).forskrift_id == forskrift_id


def test_gjenkjenn_krever_at_id_og_tittel_er_enige():
    """To uavhengige lesninger. Er de uenige, er det ikke avgjort hvilken
    forskrift kroppen er, og en kropp tolket som feil forskrift ville
    fått riktig form og feil runde."""
    rå = _side("FOR-2024-03-22-515", "22.03.2024", TITTEL_2022, KROPP_2024)
    with pytest.raises(Forskriftsfeil, match="uenige"):
        tv.gjenkjenn(tv._tekst(rå))


def test_ukjent_forskrift_kastes():
    rå = _side("FOR-2026-08-01-1600", "01.08.2026",
               TITTEL_2024.replace("2024", "2026"), KROPP_2024)
    with pytest.raises(Forskriftsfeil, match="egen uttrekksfunksjon"):
        tv.gjenkjenn(tv._tekst(rå))


# ---- uttrekkene -------------------------------------------------------

def test_2018_gir_gronn_av_kapittelhjemmel():
    """Kroppen har ingen fargeord. Grønt er utledet av at kapittel 2 er
    § 11-kapittelet, og lesemåten sier nettopp det."""
    rå = KROPPER["FOR-2017-12-20-2397"]
    assert _farger(rå, "2018-12-31") == {"1": "gronn", "7": "gronn",
                                         "13": "gronn"}
    assert set(_lesemaater(rå, "2018-12-31").values()) == {"kapittelhjemmel"}


def test_2018_navn_stopper_paa_kapittel_ikke_paa_punktum():
    """Det siste områdenavnet i 2018-kroppen har INTET punktum etter seg.
    Uten stoppet på «Kapit» ville navnet blitt «Øst-Finnmark Kapittel 3
    gjelder i alle»."""
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    navn = {o.entity_id: o.entity_name
            for o in kilde.parse(KROPPER["FOR-2017-12-20-2397"], "2018-12-31")}
    assert navn["13"] == "Øst-Finnmark"


def test_2020_skiller_kapitteloverskrift_fra_kapittelhjemmel():
    rå = KROPPER["FOR-2020-02-04-105"]
    assert _farger(rå, "2020-12-31") == {"1": "gronn", "2": "gronn",
                                         "4": "rod", "5": "rod"}
    assert _lesemaater(rå, "2020-12-31") == {
        "1": "kapittelhjemmel", "2": "kapittelhjemmel",
        "4": "kapitteloverskrift", "5": "kapitteloverskrift"}


def test_2022_leser_baade_gronn_liste_og_tabell():
    rå = KROPPER["FOR-2022-06-07-972"]
    assert _farger(rå, "2022-12-31") == {"1": "gronn", "13": "gronn",
                                         "3": "rod", "5": "gul"}
    assert set(_lesemaater(rå, "2022-12-31").values()) == {"ordrett"}


def test_2022_uttaler_seg_om_2020():
    """Tabellraden bærer to runder. 2020-halvdelen er en påstand om en
    runde en annen kropp allerede har skrevet."""
    assert _farger(KROPPER["FOR-2022-06-07-972"], "2020-12-31") == {
        "3": "gul", "5": "rod"}


def test_2024_uttaler_seg_om_tre_runder():
    rå = KROPPER["FOR-2024-03-22-515"]
    assert _farger(rå, "2020-12-31") == {"3": "gul", "5": "rod"}
    assert _farger(rå, "2022-12-31") == {"3": "rod", "5": "gul"}
    assert _farger(rå, "2024-12-31") == {"1": "gronn", "13": "gronn",
                                         "3": "rod", "5": "gul"}


def test_2024_leser_ikke_prosaomtale_som_tabellrad():
    """§ 4 i 2024-kroppen omtaler «produksjonsområde 3 og 4» med LITEN
    forbokstav. Leses den som en tabellrad, krever tabellvakten en farge
    for PO4 som ikke finnes, og uttrekket faller på sin egen vakt."""
    assert "4" not in _farger(KROPPER["FOR-2024-03-22-515"], "2024-12-31")


def test_uttrekkene_er_fire_ulike_funksjoner():
    """Én uttrekker per forskriftsår. Deler to årganger funksjon, er
    antakelsen om likt format skrevet inn i koden i stedet for prøvd mot
    kroppen — CLAUDE.md 1b-2."""
    funksjoner = [f.uttrekk for f in tv.FORSKRIFTER]
    assert len(set(id(f) for f in funksjoner)) == len(tv.FORSKRIFTER)


def test_2026_staar_ikke_i_tabellen():
    """Fargeleggingen for 2026 er kunngjort i en pressemelding, men
    forskriften var ikke fastsatt 05.09.2026. En kilde skal ikke
    emittere for en runde den ikke har en lest kropp for."""
    assert 2026 not in {r for f in tv.FORSKRIFTER for r in f.aar}
    assert tv.NYESTE_RUNDE == 2024


# ---- vaktene ----------------------------------------------------------

def test_vakten_feller_omraade_uten_farge():
    """Nevner § 3 et «Område N:» uten at en farge kommer ut, skal
    uttrekket si fra.

    Feilen lages ved å fjerne NAVNET: kandidatvakten ankrer på
    «Område N:» og treffer fortsatt, mens `_OMRAADE` krever minst to
    tegn navn og faller ut. Det er nøyaktig asymmetrien vakten finnes
    for — et område som er nevnt og ikke lest."""
    kropp = KROPP_2020.replace("a. Område 1: Svenskegrensen til Jæren ",
                               "a. Område 1: ")
    rå = _side("FOR-2020-02-04-105", "04.02.2020", TITTEL_2020, kropp)
    with pytest.raises(Forskriftsfeil, match="uten at uttrekket fikk en farge"):
        _farger(rå, "2020-12-31")


def test_vakten_feller_tabellrad_uten_parentes():
    kropp = KROPP_2022.replace(
        "Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022)",
        "Produksjonsområde 3")
    rå = _side("FOR-2022-06-07-972", "07.06.2022", TITTEL_2022, kropp)
    with pytest.raises(Forskriftsfeil, match="uten at uttrekket fikk en farge"):
        _farger(rå, "2022-12-31")


def test_vakten_feller_tapt_runde_i_parentesen():
    """Den farligste feilen: et uttrekk som leser to av tre parenteser
    gir fortsatt riktig antall rader og riktig form — bare en runde
    mindre."""
    kropp = KROPP_2024.replace("gult lys i 2020, rødt lys i 2022, rødt lys "
                               "i 2024", "rødt lys i 2022, rødt lys i 2024")
    kropp = kropp.replace("rødt lys i 2020, gult lys i 2022, gult lys i 2024",
                          "gult lys i 2022, gult lys i 2024")
    rå = _side("FOR-2024-03-22-515", "22.03.2024", TITTEL_2024, kropp)
    with pytest.raises(Forskriftsfeil, match="uttaler seg om rundene"):
        _farger(rå, "2024-12-31")


def test_vakten_feller_manglende_gronnmerking():
    """Lesemåten `ordrett` PÅSTÅR at «(grønne)» står i teksten. Gjør den
    ikke det, er påstanden vår egen hukommelse om dokumentet."""
    kropp = KROPP_2022.replace("følgende (grønne) produksjonsområder",
                               "følgende produksjonsområder")
    rå = _side("FOR-2022-06-07-972", "07.06.2022", TITTEL_2022, kropp)
    with pytest.raises(Forskriftsfeil, match="forventet ordlyden"):
        _farger(rå, "2022-12-31")


def test_vakten_feller_manglende_rodmerking_i_kapittelhode():
    kropp = KROPP_2020.replace(
        "Kapittel 4. Nedjustering av tillatelseskapasitet i røde "
        "produksjonsområder",
        "Kapittel 4. Nedjustering av tillatelseskapasitet")
    rå = _side("FOR-2020-02-04-105", "04.02.2020", TITTEL_2020, kropp)
    with pytest.raises(Forskriftsfeil, match="forventet ordlyden"):
        _farger(rå, "2020-12-31")


def test_vakten_feller_manglende_paragraf_11_hjemmel():
    """Uten § 11-hjemmelen er «kapittelet for økt kapasitet» ikke lenger
    kapittelet for akseptabel miljøpåvirkning, og grønn kan ikke
    utledes."""
    rå = KROPPER["FOR-2017-12-20-2397"].replace(
        b"(produksjonsomr\xc3\xa5deforskriften) \xc2\xa7 11 og \xc2\xa7 12",
        b"(produksjonsomr\xc3\xa5deforskriften) \xc2\xa7 12")
    with pytest.raises(Forskriftsfeil, match="§ 11"):
        _farger(rå, "2018-12-31")


def test_innholdsfortegnelsen_leses_ikke_som_brodtekst():
    """Lovdata gjentar paragrafoverskriftene FØR brødteksten. Uten
    kuttet på «Hjemmel: Fastsatt av» ville § 3-snittet truffet de to
    innholdslinjene og gitt en tom seksjon — riktig form, null data."""
    flat = tv._tekst(KROPPER["FOR-2022-06-07-972"])
    assert "§ 3. Produksjonsområder" in flat.split("Hjemmel: Fastsatt av")[0]
    assert _farger(KROPPER["FOR-2022-06-07-972"], "2022-12-31")


def test_kropp_uten_hjemmelslinje_kastes():
    rå = KROPPER["FOR-2022-06-07-972"].replace(b"Hjemmel: Fastsatt av",
                                               b"Fastsatt av")
    with pytest.raises(Forskriftsfeil, match="Hjemmel: Fastsatt av"):
        _farger(rå, "2022-12-31")


# ---- runde og snapshot ------------------------------------------------

def test_feil_runde_kaster_framfor_aa_skrive_tomt():
    """Et tomt snapshot ville sett vellykket ut, låst runden mot senere
    skriving via finnes_allerede(), og gjort hullet permanent."""
    with pytest.raises(Rundemangler, match="uttaler seg om rundene"):
        _farger(KROPPER["FOR-2020-02-04-105"], "2022-12-31")


def test_aar_i_gir_alle_runder_eldst_forst():
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    assert kilde.aar_i(KROPPER["FOR-2024-03-22-515"]) == [
        "2020-12-31", "2022-12-31", "2024-12-31"]


def test_gjelder_for_er_nyeste_fastsatte_runde_ikke_kjoreaaret():
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    assert kilde.gjelder_for("2026-09-05") == "2024-12-31"


def test_hver_farge_faar_en_lesemaate():
    """Verdien som avgjør hva dataene BETYR lagres SAMMEN med dem
    (CLAUDE.md 1b-3). En farge uten lesemåte er en farge ingen kan
    vurdere styrken av."""
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    for forskrift in tv.FORSKRIFTER:
        rå = KROPPER[forskrift.forskrift_id]
        for runde in forskrift.aar:
            obs = list(kilde.parse(rå, siste_dag(runde)))
            farger = [o for o in obs if o.field == tv.F_FARGE]
            lese = [o for o in obs if o.field.endswith(tv.LESEMAATE_SUFFIKS)]
            assert len(farger) == len(lese) > 0
            assert {o.entity_id for o in farger} == {o.entity_id for o in lese}


def test_alle_verdier_er_kjente_farger():
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    for forskrift in tv.FORSKRIFTER:
        for runde in forskrift.aar:
            for o in kilde.parse(KROPPER[forskrift.forskrift_id],
                                 siste_dag(runde)):
                if o.field == tv.F_FARGE:
                    assert o.value in (tv.GRONN, tv.GUL, tv.ROD), o
                else:
                    assert o.value in (tv.ORDRETT, tv.KAPITTELOVERSKRIFT,
                                       tv.KAPITTELHJEMMEL), o


def test_utvalg_settes_av_hentingen():
    """`{}` er «kilden filtrerer ikke», ikke «vet ikke». Vi ber om hele
    forskriften og får hele forskriften — se core/utvalg.py."""
    kilde = Trafikklysvedtak.__new__(Trafikklysvedtak)
    kilde.utgitt_av(KROPPER["FOR-2022-06-07-972"], tv.FORSKRIFTER[2])
    assert kilde.utvalg == {}


def test_forskriftene_staar_i_utgivelsesrekkefolge():
    """`backfill.py --rapporter` går gjennom dem i denne rekkefølgen.
    Motsatt vei ville hver eldre forskrift blitt en Feilrekkefolge mot en
    nyere påstand som alt lå der."""
    ider = [f.forskrift_id for f in tv.FORSKRIFTER]
    assert ider == sorted(ider)
    for f in tv.FORSKRIFTER:
        assert list(f.aar) == sorted(f.aar)
