"""Ekspertgruppe-kilden. Ingen nett og ingen ekte PDF-er.

Tabellinjene under er kopiert ORDRETT fra `extraction_mode="layout"` på
de faktiske kroppene 27.08.2026 — mellomrom for mellomrom, superskript
på egen linje der PDF-en la dem der. Det er med vilje: skriver man dem
av på nytt «pent», tester man sin egen antakelse om formatet i stedet
for formatet.
"""

import datetime as dt
import io

import pypdf
import pytest

from sources import ekspertgruppen as eg
from sources.ekspertgruppen import (Aarmangler, Ekspertgruppen, Rapportfeil,
                                    aar_av, siste_dag)


# ---- tabellen fra 2020-kroppen, ordrett -------------------------------

TABELL_2020 = "\n".join([
    "    2020            Trål         Ruse/garn            Bur         HI smitte           HI VS            VI VS         SINTEF VS          Hovedk.",
    "      1                              Lavlit                          Lavlit           Lavlit           Lavlit                             Lavlit",
    "      2           Høymid            Høymid                          Høymid           Høymid           Lavstor          Modlit            Høymid",
    "      3            Høylit         Modstor↑          Høy mid       Modstor↑            Høylit         Modmid↑          Modstor↑           Høymid",
    "      4          Modmid↑            Høylit                        Modmid↑          Modmid↑            Lavstor          Lavstor         Modmid↑",
    "      5            Lavstor        Modmid↓                            Lavlit        Modstor↓           Lavmid           Lavmid            Lavmid",
    "      6            Lavstor        Modstor↑                          Lavmid         Modmid↑            Lavstor          Lavstor           Lavstor",
    "      7                            Høystor                        Modstor↓         Modstor↓           Lavstor         Modstor↓         Modstor↓",
    "      8                             Lavstor                          Lavlit          Lavmid           Lavstor                            Lavmid",
    "      9                             Lavstor                          Lavlit           Lavlit          Lavmid                              Lavlit",
    "     10                             Lavstor                         Lavstor          Lavmid           Lavmid                             Lavstor",
    "     11                              Lavlit                          Lavlit           Lavlit          Lavmid                              Lavlit",
    "                        lit              mid                             lit               lit              lit                                lit",
    "     12             Lav             Lav                              Lav              Lav              Lav                                Lav",
    "     13                              Lavlit                          Lavlit           Lavlit           Lavlit                             Lavlit",
])

ETIKETTER_2020 = ["2020", "Trål", "Ruse/garn", "Bur", "HI smitte", "HI VS",
                  "VI VS", "SINTEF VS", "Hovedk."]

# 2018-kroppen: hodet går over TO linjer, og «Vaktbur» står på den andre.
TABELL_2018 = "\n".join([
    " Prod.                Trål-         Sjøørret                         HI              HI             VI          Konklusj",
    " omr.                 fangst          ruse        Vaktbur         Smitte-         Virtuell        Smolt            on1",
    "                                                                    press          smolt          modell",
    "        1                             Lav                           Lav             Lav            Lav            Lav",
    "        2          Mod/Lav            Høy           Mod             Høy             Mod           Lav**           Mod",
    "        3             Mod             Høy           Mod         Mod/Høy             Høy           Lav**           Høy",
    "        4             Mod             Høy           Mod            Mod              Mod           Lav**           Mod",
    "        5              Lav            Mod            Lav            Lav             Mod           Lav*            Mod",
    "        6              Lav            Mod            Lav            Lav             Mod           Lav**           Lav",
    "        7                             Mod           Mod            Mod              Lav           Lav**           Mod",
    "        8                             Lav                           Lav             Lav           Lav**           Lav",
    "        9                             Lav                           Lav             Lav           Lav*            Lav",
    "       10                             Lav                           Lav             Lav           Lav*            Lav",
    "       11                             Lav                           Lav             Lav            Lav            Lav",
    "       12              Lav            Lav            Lav            Lav             Lav            Lav            Lav",
    "       13                             Lav                           Lav             Lav            Lav            Lav",
])

ETIKETTER_2018 = ["Prod.", "Trål-", "Sjøørret", "Vaktbur", "HI", "HI", "VI",
                  "Konklusj"]


# ---- gyldighetsdatoen -------------------------------------------------

def test_observed_at_er_arets_siste_dag():
    assert siste_dag(2020) == "2020-12-31"
    assert aar_av("2020-12-31") == 2020


def test_observed_at_midt_i_aaret_avvises():
    """Filnavnet er det eneste alt nedstrøms leser datoen fra (F6)."""
    with pytest.raises(ValueError, match="ikke årets siste dag"):
        aar_av("2020-06-15")


# ---- tabellesing ------------------------------------------------------

def test_tabellrader_leser_alle_tretten():
    rader = eg._tabellrader(TABELL_2020, "2020", ETIKETTER_2020)
    assert sorted(rader, key=int) == [str(n) for n in range(1, 14)]


def test_tomme_celler_forskyver_ikke_kolonnene():
    """PO1 har verken trål, bur eller SINTEF.

    Uten layout-ekstraksjon ville de fem tokenene blitt lest som de fem
    første kolonnene, og «Lavlit» for ruse havnet under trål.
    """
    rader = eg._tabellrader(TABELL_2020, "2020", ETIKETTER_2020)
    trål, ruse, bur, hi_smitte, hi_vs, vi_vs, sintef, hoved = rader["1"][1:]
    assert trål == "" and bur == "" and sintef == ""
    assert ruse == hi_smitte == hi_vs == vi_vs == hoved == "Lavlit"


def test_superskript_paa_egen_linje_slaas_sammen():
    """PO12 i 2020-kroppen har «lit»/«mid» på linja OVER «Lav»."""
    rader = eg._tabellrader(TABELL_2020, "2020", ETIKETTER_2020)
    assert rader["12"][1] == "Lavlit"
    assert rader["12"][2] == "Lavmid"
    assert rader["12"][-1] == "Lavlit"


def test_celle_med_mellomrom_slaas_sammen():
    """«Høy mid» (PO3, Bur) er én celle brutt av ordelingen."""
    rader = eg._tabellrader(TABELL_2020, "2020", ETIKETTER_2020)
    assert eg._les_celle(rader["3"][3]) == ("hoy", "middels", "")


def test_tabellhode_over_to_linjer():
    """2018-kroppen har «Vaktbur» på hodets ANDRE linje."""
    rader = eg._tabellrader(TABELL_2018, "Prod.", ETIKETTER_2018)
    assert len(rader) == 13
    assert eg._les_celle(rader["2"][3]) == ("moderat", "", "")   # Vaktbur


def test_ufullstendig_tabell_kaster():
    kuttet = "\n".join(TABELL_2020.split("\n")[:6])
    with pytest.raises(Rapportfeil, match="av 13 produksjonsområder"):
        eg._tabellrader(kuttet, "2020", ETIKETTER_2020)


# ---- celleformen ------------------------------------------------------

@pytest.mark.parametrize("tekst, ventet", [
    ("Lavlit", ("lav", "liten", "")),
    ("Modstor↑", ("moderat", "stor", "opp")),
    ("Mod↑stor", ("moderat", "stor", "opp")),          # 2021 flyttet pila
    ("Mod↕Stor", ("moderat", "stor", "begge")),        # ny form i 2021
    ("Modliten", ("moderat", "liten", "")),
    ("HøyMid", ("hoy", "middels", "")),
    ("Lav", ("lav", "", "")),                          # 2018: ingen usikkerhet
    ("Lav**", ("lav", "", "")),                        # VIs scenariomarkør
])
def test_celleformer_vi_har_sett(tekst, ventet):
    assert eg._les_celle(tekst) == ventet


def test_pilens_plassering_gir_samme_verdi():
    """2020 skriver «Modstor↑», 2021 «Mod↑stor». Samme utsagn.

    Uten normaliseringen ville hele 2020-tabellen sett revidert ut i
    2021-rapporten, og de tolv EKTE revisjonene druknet.
    """
    assert eg._les_celle("Modstor↑") == eg._les_celle("Mod↑stor")


def test_sammensatt_celle_beholdes_sammensatt():
    """«Mod/Lav» i 2018 er kildens egen tvetydighet."""
    assert eg._les_celle("Mod/Lav") == ("moderat/lav", "", "")


def test_ukjent_celleform_kaster():
    with pytest.raises(Rapportfeil, match="ikke en form vi kjenner"):
        eg._les_celle("Ekstremsvært")


def test_tom_celle_er_none():
    assert eg._les_celle("   ") is None


# ---- ulikheter --------------------------------------------------------

@pytest.mark.parametrize("tekst, ventet", [
    ("utgjør 34 % av", "34"),
    ("utgjør < 1 % av", "<1"),
    ("var under 1 % samtlige", "<1"),
    ("over 30 %", ">30"),
    ("er 2,5 %", "2.5"),
])
def test_prosent_beholder_relasjonen(tekst, ventet):
    assert eg._prosent(tekst) == ventet


def test_ulikhet_kan_ikke_bli_flyttall():
    """`float("<1")` skal kaste. Det er hele poenget med lagringsformen."""
    with pytest.raises(ValueError):
        float(eg._prosent("utgjør < 1 % av"))


# ---- utvandringsvinduet ----------------------------------------------

def test_vindu_leses_som_datoer():
    seksjon = ("Produksjonsområde 1: ... Antatt tidspunkt for utvandring: "
               "24. april – 5. juni, med 50 % utvandring satt til 17. mai "
               "(uke 20). Resultater 2020")
    assert eg._vindu(seksjon, 2020) == {
        "utvandring_start": "2020-04-24",
        "utvandring_slutt": "2020-06-05",
        "utvandring_median": "2020-05-17",
        "utvandring_median_uke": "20",
    }


def test_vindu_uten_treff_er_fravaerende():
    """2016/2017-, 2018-, 2021- og 2022-kroppene har det ikke."""
    assert eg._vindu("Produksjonsområde 1: ingenting om utvandring.", 2020) is None


def test_vindusdatoen_faar_vurderingsaaret():
    """Samme dato faller i ulik ISO-uke fra år til år, så uketallet for
    start og slutt er analyselagets regnestykke — ikke kildens."""
    seksjon = ("Antatt tidspunkt for utvandring: 27. juni – 27. juli, med "
               "dato for 50 % utvandring beregnet til 9. juli (uke 28).")
    assert eg._vindu(seksjon, 2020)["utvandring_start"] == "2020-06-27"
    assert eg._vindu(seksjon, 2018)["utvandring_start"] == "2018-06-27"


# ---- published_at -----------------------------------------------------

def _pdf(created: str | None) -> bytes:
    """Minimal PDF med (eller uten) `/CreationDate`."""
    skriver = pypdf.PdfWriter()
    skriver.add_blank_page(width=200, height=200)
    if created:
        skriver.add_metadata({"/CreationDate": created})
    ut = io.BytesIO()
    skriver.write(ut)
    return ut.getvalue()


def test_published_at_leses_av_creationdate():
    advarsler: list[str] = []
    utgitt = eg._utgitt(_pdf("D:20201123130644+01'00'"), 2020, advarsler)
    assert utgitt == "2020-11-23T12:06:44+00:00"
    assert advarsler == []


def test_utgitt_normaliserer_til_utc():
    """Kroppene er stemplet i +01:00 (norsk vintertid).

    `published_at` sammenlignes LEKSIKOGRAFISK i `snapshot.publisert()` og
    `diff.revisjon()`. Et annet offset gir feil rekkefølge uten å feile,
    og det er derfor `test_ingen_kilde_setter_published_at_uten_a_normalisere`
    krever at verdien går gjennom nettopp denne funksjonen.
    """
    utgitt = eg._utgitt(_pdf("D:20211111154825+01'00'"), 2021, [])
    assert utgitt.endswith("+00:00")
    naar = dt.datetime.fromisoformat(utgitt)
    assert naar.utcoffset() == dt.timedelta(0)
    assert naar.hour == 14                      # 15:48 +01:00 er 14:48 UTC


def test_creationdate_utenfor_vinduet_gir_tom_published_at():
    """En re-eksport er ikke en utgivelse.

    2016/2017-kroppen er kjørt gjennom Quartz PDFContext. Skulle en slik
    re-eksport skje i 2026, ville datoen vært 2026 — og brukt som
    `published_at` ville den lest revisjonsaksen baklengs.
    """
    advarsler: list[str] = []
    assert eg._utgitt(_pdf("D:20260401120000Z"), 2020, advarsler) == ""
    assert "RE-EKSPORTTIDSPUNKT" in advarsler[0]


def test_manglende_creationdate_gir_tom_published_at_ikke_klokka():
    advarsler: list[str] = []
    assert eg._utgitt(_pdf(None), 2020, advarsler) == ""
    assert "gjettet dato er verre" in advarsler[0]


@pytest.mark.parametrize("tekst, ventet", [
    ("D:20171006061014Z00'00'", dt.datetime(2017, 10, 6, 6, 10, 14,
                                            tzinfo=dt.timezone.utc)),
    ("D:20221201103434+01'00'", dt.datetime(
        2022, 12, 1, 10, 34, 34,
        tzinfo=dt.timezone(dt.timedelta(hours=1)))),
])
def test_pdf_datoformatet(tekst, ventet):
    assert eg._les_pdf_dato(tekst) == ventet


@pytest.mark.parametrize("tekst", ["i går", "20201123", ""])
def test_ugyldig_pdf_dato_er_none(tekst):
    assert eg._les_pdf_dato(tekst) is None


def test_delvis_dato_nektes_selv_om_standarden_tillater_den():
    """ISO 32000 lar alt etter årstallet utelates. Vi tar det ikke.

    Ingen av de fem kroppene har en slik dato, så å støtte formen ville
    vært å anta noe om et format vi ikke har sett (CLAUDE.md regel 4). Og
    tolkningen ville uansett vært et gjett: `D:2020` som 1. januar
    daterer en novemberrapport ti måneder for tidlig, i et felt som
    sammenlignes leksikografisk.
    """
    assert eg._les_pdf_dato("D:2020") is None
    assert eg._les_pdf_dato("D:202011") is None
    # Dagen holder; klokkeslettet er valgfritt.
    assert eg._les_pdf_dato("D:20201123") == dt.datetime(
        2020, 11, 23, tzinfo=dt.timezone.utc)


# ---- gjenkjenning og årsvalg -----------------------------------------

def test_kroppen_gjenkjennes_av_forsiden_ikke_av_filnavnet():
    forside = ("Vurdering av lakselusindusert villfiskdødelighet per "
               "produksjonsområde i 2020 Ekspertgruppens leder Knut W. Vollset")
    assert eg.gjenkjenn(forside).aar == (2020,)


def test_ukjent_forside_kaster():
    with pytest.raises(Rapportfeil, match="matcher ingen kjent rapport"):
        eg.gjenkjenn("Årsrapport for noe helt annet")


def test_rapportene_staar_i_utgivelsesrekkefolge():
    """`backfill.py --rapporter` hviler på den rekkefølgen: hvert år må
    først skrives av den eldste kroppen og deretter revideres."""
    nyeste = [r.aar[-1] for r in eg.RAPPORTER]
    assert nyeste == sorted(nyeste)


def test_nyeste_aar_utledes_av_tabellen():
    assert eg.NYESTE_AAR == max(a for r in eg.RAPPORTER for a in r.aar)


def test_gjelder_for_er_nyeste_leste_aar_ikke_kjoreaaret():
    kilde = Ekspertgruppen()
    assert kilde.gjelder_for("2026-08-27") == siste_dag(eg.NYESTE_AAR)
    # Kjøredatoen skal ikke kunne flytte den.
    assert kilde.gjelder_for("2030-01-01") == kilde.gjelder_for("2026-08-27")


def test_kilden_leser_aldri_klokka():
    kilde = Ekspertgruppen()
    assert kilde.gjelder_for("2026-01-01") == kilde.gjelder_for("2026-12-31")


# ---- kryssjekken ------------------------------------------------------

def test_kryssjekk_slipper_gjennom_enighet():
    eg._kryssjekk({"1": "lav", "2": "hoy"}, {"1": "lav", "2": "hoy"}, "test")


def test_kryssjekk_feller_sprik():
    """To lesinger av samme kropp som er uenige betyr at kolonnene er
    tilordnet feil — ikke at kilden har to meninger."""
    with pytest.raises(Rapportfeil, match="uenige om 1 produksjonsområde"):
        eg._kryssjekk({"1": "lav"}, {"1": "hoy"}, "test")


def test_kryssjekk_krever_ikke_full_dekning():
    """Et avsnitt uten konklusjonssetning er et fravær, ikke et sprik."""
    eg._kryssjekk({"1": "lav", "2": "hoy"}, {"1": "lav"}, "test")


# ---- kategorilister i prosa ------------------------------------------

def test_kategoriliste_taaler_orddelingsmellomrom():
    """2018-kroppen skriver «hø y risiko» og «dødel ighet».

    Uten slakk fant lesingen bare 11 av 13 områder for 2017 — og de to
    som falt ut var nettopp de to i høy-kategorien.
    """
    avsnitt = ("For 2017 konkluderte ekspertgruppen med lav risiko for "
               "lakselusindusert dødelighet i ti produksjonsområder "
               "(1, 2, 6, 7, 8, 9, 10, 11, 12 og 13), moderat risiko for "
               "lakselusindusert dødelighet i ett produksjonsområde (5) og "
               "hø y risiko for lakselusindusert dødel ighet i to områder "
               "(3, 4).")
    lister = eg._kategorilister(avsnitt)
    assert len(lister) == 13
    assert lister["3"] == "hoy" and lister["4"] == "hoy"
    assert lister["5"] == "moderat"
    assert lister["13"] == "lav"


def test_aarsavsnitt_renner_ikke_over_i_neste_aar():
    """De to årene står i samme avsnitt. Et vindu på faste tegn blandet
    2016-listen med 2017-listen, og PO2 fikk feil kategori."""
    flat = ("Ekspertgruppen har for 2016 konkludert med lav risiko i syv "
            "produksjonsområder (1, 8, 9, 10, 11, 12, 13), moderat risiko i "
            "fem produksjonsområder (2, 4, 5, 6, 7) og høy risiko i ett "
            "produksjonsområde (3). For 2017 konkluderte ekspertgruppen med "
            "lav risiko i ti produksjonsområder (1, 2, 6, 7, 8, 9, 10, 11, "
            "12 og 13), moderat risiko i ett produksjonsområde (5) og høy "
            "risiko i to områder (3, 4).")
    for_2016 = eg._kategorilister(eg._aarsavsnitt(flat, 2016))
    for_2017 = eg._kategorilister(eg._aarsavsnitt(flat, 2017))
    assert for_2016["2"] == "moderat"
    assert for_2017["2"] == "lav"
    assert for_2016["4"] == "moderat" and for_2017["4"] == "hoy"


# ---- seksjonsoppdelingen ---------------------------------------------

def test_seksjoner_tar_den_ekte_overskriften_ikke_innholdsfortegnelsen():
    """Innholdsfortegnelsen har samme ordlyd og står FØRST.

    For det siste produksjonsområdet strekker innholdsfortegnelsens
    utsnitt seg over hele brødteksten, så «lengste vinner» pekte
    konsekvent på feil utsnitt — og bare for PO13.
    """
    flat = ("Innhold Produksjonsområde 1: Svenskegrensa 12 "
            "Produksjonsområde 2: Ryfylke 20 "
            "... mye brødtekst ... "
            "Produksjonsområde 1: Svenskegrensa Konklusjon: Lav "
            "lakselusindusert villfiskdødelighet i 2020. "
            "Produksjonsområde 2: Ryfylke Konklusjon: Høy "
            "lakselusindusert villfiskdødelighet i 2020.")
    seksjoner = eg._seksjoner(flat)
    assert "Konklusjon" in seksjoner["2"]
    assert eg._kategori_i_prosa(seksjoner["1"], 2020) == "lav"
    assert eg._kategori_i_prosa(seksjoner["2"], 2020) == "hoy"


def test_po_navn_uten_sidetall():
    sider = ["Produksjonsområde 4: Nordhordland til Stadt 35\n",
             "Produksjonsområde 4: Nordhordland til Stadt\n"]
    assert eg._po_navn(sider)["4"] == "Nordhordland til Stadt"


# ---- konklusjonsformene ----------------------------------------------

@pytest.mark.parametrize("setning, aar, ventet", [
    ("Konklusjon: Lav lakselusindusert villfiskdødelighet i 2020.",
     2020, "lav"),
    ("Konklusjon: Moderat risiko for lakselusindusert villfiskdødelighet "
     "i 2018.", 2018, "moderat"),
    ("Konklusjon: Lav risiko for lakselusindusert villfiskdødelighet både "
     "i 2016 og 2017.", 2016, "lav"),
    ("Konklusjon: Lav risiko for lakselusindusert villfiskdødelighet både "
     "i 2016 og 2017.", 2017, "lav"),
    ("Kategori med høyest sannsynlighet: Moderat lakselusindusert "
     "villfiskdødelighet i 2022", 2022, "moderat"),
])
def test_konklusjonsformene_vi_har_sett(setning, aar, ventet):
    assert eg._kategori_i_prosa(setning, aar) == ventet


def test_to_aar_i_samme_setning_gir_ulikt_svar():
    """2016/2017-kroppen: «Moderat risiko i 2016 og lav risiko i 2017».

    Det er KILDEN som fordeler årene, ikke vi.
    """
    setning = ("Konklusjon: Moderat risiko i 2016 og lav risiko i 2017 for "
               "lakselusindusert villfiskdødelighet.")
    assert eg._kategori_i_prosa(setning, 2016) == "moderat"
    assert eg._kategori_i_prosa(setning, 2017) == "lav"


def test_kategori_for_et_annet_aar_er_none():
    setning = "Konklusjon: Lav lakselusindusert villfiskdødelighet i 2020."
    assert eg._kategori_i_prosa(setning, 2021) is None


# ---- HI-avsnittene ----------------------------------------------------

def test_hi_virtuell_smolt_vektet_og_uvektet():
    seksjon = ("HI Virtuell smolt: Den gjennomsnittlige estimerte "
               "dødeligheten for normal utvandring, varierte mellom 2 og "
               "32 % i perioden 2012 – 2020. Gjennomsnittet vektet (22 %) "
               "etter elvenes potensielle smoltproduksjon var lavere enn "
               "det uvektede snittet (32 %) i 2020.")
    assert dict(eg._hi_virtuell_smolt(seksjon)) == {
        "hi_virtuell_smolt_vektet": "22",
        "hi_virtuell_smolt_uvektet": "32",
    }


def test_seriens_spenn_leses_ikke_som_aarets_verdi():
    """Ni av tretten områder oppgir BARE spennet over 2012-2020.

    Det er en annen størrelse om et annet tidsrom. Å lese den som årets
    verdi ville vært riktig form og feil tall.
    """
    seksjon = ("HI virtuell smolt: Den gjennomsnittlige estimerte "
               "dødeligheten, både uvektet og vektet etter elvas "
               "potensielle smoltproduksjon varierte mellom 5 og 20 % i "
               "perioden 2012 – 2020.")
    assert eg._hi_virtuell_smolt(seksjon) == []


def test_begge_under_terskel_gir_ulikhet_paa_begge():
    seksjon = ("HI virtuell smolt: Den gjennomsnittlige estimerte "
               "dødeligheten, både uvektet og vektet etter elvas "
               "potensielle smoltproduksjon, var under 1 % samtlige år i "
               "perioden 2012 – 2020.")
    assert dict(eg._hi_virtuell_smolt(seksjon)) == {
        "hi_virtuell_smolt_vektet": "<1",
        "hi_virtuell_smolt_uvektet": "<1",
    }


def test_roc_leses_ogsaa_uten_ord_foran_tallet():
    """«er 27 %» mot «er moderat (33 %)» — to former, samme opplysning.

    Den første formen falt stille bort i første utkast: den valgfrie
    ordgruppa `(?:\\w+\\s*)?` slukte sifrene. To av 22 verdier forsvant,
    én i hver av 2021- og 2022-kroppene, og begge var blant de høyeste i
    sitt år.
    """
    bar = "HI smittepress: Indeksen for risiko for høy påvirkning er 27 %."
    med_ord = ("HI smittepress: Indeksen for risiko for høy påvirkning er "
               "moderat (33 %).")
    med_aar = ("HI smittepress: Indeksen for risiko for høy påvirkning er "
               "moderat i 2022 (15 %).")
    orddelt = ("HI smittepress: Indeksen for ris iko for høy påvirkning er "
               "33 %.")
    assert dict(eg._hi_smittepress(bar))["hi_smittepress_roc_indeks"] == "27"
    assert dict(eg._hi_smittepress(med_ord))["hi_smittepress_roc_indeks"] == "33"
    assert dict(eg._hi_smittepress(med_aar))["hi_smittepress_roc_indeks"] == "15"
    assert dict(eg._hi_smittepress(orddelt))["hi_smittepress_roc_indeks"] == "33"


@pytest.mark.parametrize("setning, ventet", [
    # PDF-en deler ord i justerte linjer.
    ("Indeksen for risiko for høy påv irkning er moderat (11 %).", "11"),
    ("Indeksen for ris iko for høy påvirkning er 33 %.", "33"),
    # ... og skyter inn ledd mellom størrelsen og verbet.
    ("Indeksen for risiko for høy påvirkning for hele produksjons"
     "området er moderat (25 %).", "25"),
])
def test_roc_taaler_orddeling_og_innskudd(setning, ventet):
    """PO7 falt ut av BÅDE 2021 og 2022 på disse to formene.

    11 % og 25 % — midt i fordelingen, ikke ytterpunkter, så tapet var
    usynlig i et sammendrag. Med rettingen dekker HI smittekart 39 av 39
    (po, år)-celler.
    """
    tekst = "HI smittepress: " + setning
    assert dict(eg._hi_smittepress(tekst))["hi_smittepress_roc_indeks"] == ventet


def test_arealandel_taaler_orddeling():
    tekst = ("Smittepress HI: Modellert område med forhøyet p åvirkning "
             "utgjør 12 % av det kystnære arealet.")
    assert dict(eg._hi_smittepress(tekst))["hi_smittepress_arealandel"] == "12"


def test_arealandel_og_roc_er_to_felter():
    """2020 oppgir en arealandel, 2021/2022 en ROC-indeks.

    De KAN være samme størrelse og de kan la være. Regel 4: det som ikke
    er bekreftet skal ikke antas, og å slå dem sammen ville gjort et
    metodeskifte til en verdiendring.
    """
    fra_2020 = ("HI smittepress: Modellert område med forhøyet påvirkning "
                "utgjør 34 % av det kystnære arealet.")
    fra_2021 = ("HI smittepress: Indeksen for risiko for høy påvirkning "
                "er 27 %.")
    assert dict(eg._hi_smittepress(fra_2020)) == {
        "hi_smittepress_arealandel": "34"}
    assert dict(eg._hi_smittepress(fra_2021)) == {
        "hi_smittepress_roc_indeks": "27"}


def test_arealandelens_ulikhet_bevares():
    seksjon = ("Smittepress HI: Modellert område med forhøyet påvirkning "
               "utgjør < 1 % av det kystnære arealet.")
    assert dict(eg._hi_smittepress(seksjon)) == {
        "hi_smittepress_arealandel": "<1"}


# ---- parse() ----------------------------------------------------------

def test_parse_avviser_et_aar_kroppen_ikke_dekker(monkeypatch):
    """Et tomt snapshot ville sett vellykket ut og LÅST året."""
    kilde = Ekspertgruppen()
    monkeypatch.setattr(eg, "_sider", lambda rå, layout: [
        "Vurdering av lakselusindusert villfiskdødelighet per "
        "produksjonsområde i 2020"])
    with pytest.raises(Aarmangler, match="ikke om 2019"):
        list(kilde.parse(b"", "2019-12-31"))


def test_hver_verdi_faar_et_sikkerhetsfelt(monkeypatch):
    kilde = Ekspertgruppen()
    forside = ("Vurdering av lakselusindusert villfiskdødelighet per "
               "produksjonsområde i 2020")
    monkeypatch.setattr(eg, "_sider", lambda rå, layout: [forside])
    monkeypatch.setattr(eg, "_po_navn", lambda sider: {"1": "Sør"})
    monkeypatch.setattr(
        eg, "_uttrekk_2020",
        lambda sider, flat, aar: [eg.Celle("1", "kategori", "lav", "tabell")])
    # RAPPORTER holder funksjonen direkte, så tabellen må peke på den nye.
    monkeypatch.setattr(eg, "RAPPORTER", tuple(
        r._replace(uttrekk=eg._uttrekk_2020) if 2020 in r.aar else r
        for r in eg.RAPPORTER))

    obs = list(kilde.parse(b"", "2020-12-31"))
    assert [(o.field, o.value) for o in obs] == [
        ("kategori", "lav"),
        ("kategori" + eg.SIKKERHET_SUFFIKS, "tabell"),
    ]
    assert all(o.entity_id == "1" and o.entity_name == "Sør" for o in obs)
    assert all(o.observed_at == "2020-12-31" for o in obs)


def test_tomt_uttrekk_kaster(monkeypatch):
    kilde = Ekspertgruppen()
    monkeypatch.setattr(eg, "_sider", lambda rå, layout: [
        "Vurdering av lakselusindusert villfiskdødelighet per "
        "produksjonsområde i 2020"])
    monkeypatch.setattr(eg, "RAPPORTER", tuple(
        r._replace(uttrekk=lambda sider, flat, aar: []) if 2020 in r.aar else r
        for r in eg.RAPPORTER))
    with pytest.raises(Rapportfeil, match="fant ingenting"):
        list(kilde.parse(b"", "2020-12-31"))


def test_kilden_setter_utvalg_og_entitetstype():
    kilde = Ekspertgruppen()
    assert kilde.entity_type == "produksjonsomraade"   # joiner mot biomasse
    assert kilde.name == "ekspertgruppen"
