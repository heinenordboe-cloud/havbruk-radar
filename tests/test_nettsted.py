"""Generatoren for den publiserte nettsiden.

Testene her er av to slag, og skillet er det samme som i
`test_publiseringsvakt.py`:

  * De fleste prøver MARKUPEN og VILKÅRENE på en konstruert side. De
    kjører uten data og uten nett, som resten av suiten.

  * Ingen av dem prøver PORTEN. `conftest.py` peker `HAVBRUK_DATA_DIR`
    til en engangsmappe, så hvitelista er tom her, og en port bygget på
    den ville felt hver publisering. Porten er en kommando:
    `python nettsted.py`, exit 1 ved funn. Se
    `docs/beslutninger/2026-09-15-publiseringsvakten.md`.

Den viktigste testen er `test_ubelagt_kilde_kan_ikke_publiseres`.
`docs/LISENSKJEDE.md` sier at udokumentert lisens er UBELAGT og ikke
antatt greit; uten en test er den setningen en hensikt.
"""

import json
import re

import pytest

import nettsted


# ---- vilkårene --------------------------------------------------------

def test_attribusjonen_bygges_av_kildene_siden_bruker():
    """Ikke en fast bunntekst. En side som ikke viser lusetall skal ikke
    påstå at den inneholder data fra Mattilsynet."""
    bare_register = nettsted.attribusjon(["akvakultur"])
    assert bare_register == ["Kilde: Fiskeridirektoratet"]

    med_lus = nettsted.attribusjon(["akvakultur", "lusetall"])
    assert "Data levert av BarentsWatch" in med_lus
    assert any("Mattilsynet" in s for s in med_lus)


def test_begge_barentswatch_setningene_er_med():
    """Dataeierattribusjonen er ikke valgfri. Den trengs NETTOPP fordi vi
    henter fra BarentsWatch og ikke fra Mattilsynet — se
    docs/LISENSKJEDE.md merknad F."""
    setninger = nettsted.attribusjon(["lusetall"])
    assert setninger == [
        "Data levert av BarentsWatch",
        "Opplysninger om lakselus, rensefisk og medikamentbruk er hentet "
        "fra Mattilsynet.",
    ]


def test_attribusjonen_dedupliserer_med_rekkefolgen_intakt():
    """`eierskap` og `eierskap_historikk` krever de samme to setningene.
    Den som leser bunnteksten skal ikke lure på hvorfor det står to
    like."""
    setninger = nettsted.attribusjon(["eierskap", "eierskap_historikk"])
    assert len(setninger) == len(set(setninger)) == 2
    assert setninger[0] == "Kilde: Fiskeridirektoratet"


def test_ubelagt_kilde_kan_ikke_publiseres():
    """`ekspertgruppen` er UBELAGT: vilkåret er lett etter 14.09.2026 og
    ikke funnet. UBELAGT betyr «vi vet ikke», ikke «fritt».

    Dette er docs/beslutninger/2026-09-12-lisenskjeden.md utført i kode.
    Faller denne, kan en side publisere data vi ikke har hjemmel for å
    republisere, og den ville gjort det STILLE — en tom liste ville
    bare gitt en bunntekst uten den ene setningen."""
    with pytest.raises(nettsted.UbelagtKilde, match="ekspertgruppen"):
        nettsted.attribusjon(["akvakultur", "ekspertgruppen"])


def test_ukjent_kilde_stoppes_ogsaa():
    """Et kildenavn ingen Source skriver under er samme sak som en
    UBELAGT: ingen har sagt hva vilkåret er."""
    with pytest.raises(nettsted.UbelagtKilde, match="nykilde"):
        nettsted.attribusjon(["nykilde"])


def test_hver_kilde_med_utgiver_har_ogsaa_attribusjon():
    """Vaktposten mot en halvferdig rad: en kilde med attribusjon men
    uten utgiver er greit (Lovdata bærer utgiveren i setningen), men en
    utgiver uten attribusjon er en rad noen har begynt på."""
    indeks = nettsted.kildevilkaar()
    for kilde in nettsted.UTGIVER:
        assert kilde in indeks, kilde
        assert indeks[kilde], f"{kilde} har utgiver men ingen setning"


def test_attribusjonen_kommer_fra_kilden_og_ikke_fra_nettsted():
    """Flyttingen 16.09.2026, håndhevet.

    Sto lista i `nettsted.py` igjen, ville en ny kilde kunne legges til
    uten at attribusjonen fulgte med — og den manglende setningen ville
    vist seg først den dagen noen publiserte. Se
    docs/beslutninger/2026-09-16-attribusjon-folger-kilden.md."""
    from core import registry
    from core.contract import erklaert_attribusjon

    kilder = {k.name: k for k in registry.discover()}
    assert erklaert_attribusjon(kilder["lusetall"]) == tuple(
        nettsted.attribusjon(["lusetall"]))
    assert not hasattr(nettsted, "KILDEVILKAAR"), (
        "tabellen er flyttet til Source.attribusjon — to lister som skal si "
        "det samme er formen F6 og F7 hadde")


def test_alias_arver_kildens_attribusjon():
    """`eierskap_historikk` skrives av `sources/eierskap.py` under et
    eget navn. Uten `skriver_ogsaa` slår navnet opp til ingenting, og
    ingenting leses som UBELAGT — altså en side som nekter å bygge av
    feil grunn."""
    indeks = nettsted.kildevilkaar()
    assert indeks["eierskap_historikk"] == indeks["eierskap"]


# ---- markupen ---------------------------------------------------------

def _side(**overstyr) -> str:
    """En rendret lokalitetsside av konstruerte data.

    Konstruerte og ikke ekte: suiten skal aldri lese datarepoet. Formen
    er den `bygg_lokalitet()` returnerer, og avviker den, feller
    `test_malen_krever_alle_feltene_bygg_lokalitet_lager` det.
    """
    lok = {
        "loknr": "31397", "navn": "OTERNESET", "kommune": "HARSTAD",
        "fylke": "TROMS", "po_kode": "10", "po_navn": "Andøya til Senja",
        "breddegrad": "68.9288", "lengdegrad": "16.701367",
        "akva_dato": "2026-09-14", "eierskap_dato": "2026-09-14",
        "register": [("navn", "OTERNESET"), ("kapasitet", "8000.0")],
        "tillatelser": [{
            "nr": "T-D-0009", "eier_navn": "SALMAR OPPDRETT AS",
            "eier_orgnr": "928957489", "type": "KOMM-MATF",
            "kapasitet": "1022.0", "kapasitet_enhet": "TN",
            "tildelt_dato": "2004-09-29", "tildelt_navn": "SALMAR NORD AS",
        }],
        "overforinger": [{
            "dato": "2018-03-13", "tillatelse": "T-D-0009",
            "mottaker_navn": "SALMAR FARMING AS",
            "mottaker_orgnr": "966840528", "rekkefolge": "1",
        }],
        "lus": [{
            "uke": "2026 uke 33", "dato": "2026-08-10",
            "voksne_hunnlus": "0.0045454544", "lus_er_rapportert": "ja",
            "har_laksefisk": "ja", "brakklagt": "nei",
            "har_medikamentell_behandling": "nei",
            "har_mekanisk_fjerning": "nei", "har_rensefisk": "nei",
        }],
        "lus_fra": "2012-01-02", "lus_til": "2026-08-17",
        "lus_uker": 764, "lus_uten_tall": 207,
        "endringer": [{
            "dato": "2026-08-31", "gjelder": "lokaliteten",
            "kilde": "akvakultur", "felt": "tillatelser_antall",
            "fra": "11", "til": "10",
        }],
        "maaleserie_rader": 1284,
        "dekning_fra": [{"kilde": "akvakultur", "fra": "2026-08-17"}],
    }
    lok.update(overstyr)
    return nettsted._miljo().get_template("lokalitet.html.j2").render(
        lok=lok, tittel="T", beskrivelse="B",
        jsonld=nettsted.jsonld(lok),
        attribusjon=nettsted.attribusjon(nettsted.SIDENS_KILDER),
        bygget="2026-09-16",
    )


def test_malen_krever_alle_feltene_bygg_lokalitet_lager():
    """`StrictUndefined` gjør en manglende nøkkel til en FEIL i stedet
    for en tom celle. En side med et manglende tall ser riktig ut, og
    det er den feilen som er dyrest å oppdage sent."""
    from jinja2 import UndefinedError

    # Hele lok-dicten mangler nesten alt: malen skal stoppe, ikke rendre
    # en side full av tomme celler.
    with pytest.raises(UndefinedError):
        nettsted._miljo().get_template("lokalitet.html.j2").render(
            lok={"loknr": "1"}, tittel="T", beskrivelse="B", jsonld="{}",
            attribusjon=[], bygget="2026-09-16")

    # Og på radnivå, som er der det ville gjort minst støy: en uke uten
    # `voksne_hunnlus` skal felle malen og ikke gi en tom celle. Det er
    # nettopp denne som fanget at 207 av OTERNESETs 764 uker ikke har
    # feltet i det hele tatt.
    with pytest.raises(UndefinedError):
        _side(lus=[{"uke": "2026 uke 29", "dato": "2026-07-13",
                    "lus_er_rapportert": "nei", "har_laksefisk": "ja",
                    "brakklagt": "ja", "har_medikamentell_behandling": "nei",
                    "har_mekanisk_fjerning": "nei", "har_rensefisk": "nei"}])


ANKERE = {
    "akvakultur-register",
    "eierskap-tillatelser",
    "eierskap_historikk-overforinger",
    "lusetall-uke",
    "endringer-register",
}


def test_hver_tabell_har_sitt_stabile_anker():
    """Ankerne er kontrakten mot enhver som siterer siden. De er utledet
    av kildenavnet og feltvokabularet — ikke av rekkefølgen på siden og
    ikke av overskriftsteksten. Se
    docs/beslutninger/2026-09-16-url-struktur.md.

    Endres ett av navnene under, er det en brutt lenke for alle som har
    lenket til den tabellen. Denne testen er stedet man møter det."""
    funnet = set(re.findall(r'<table id="([^"]+)"', _side()))
    assert funnet == ANKERE


def test_ankerne_er_ascii_og_smaa_bokstaver():
    """`#produksjonsområde` er lovlig i en URL, men blir prosentkodet når
    den kopieres, og den strengen overlever ikke å bli limt inn i en
    e-post og ut igjen."""
    for anker in ANKERE:
        assert anker.isascii(), anker
        assert anker == anker.lower(), anker
        assert " " not in anker, anker


def test_ingen_tabell_har_et_posisjonsanker():
    """`#tabell-3` fortsetter å FUNGERE når noen setter inn en tabell
    foran den — den peker bare på noe annet. En lenke som går til feil
    sted er verre enn en som er død, fordi ingen får vite det."""
    for anker in ANKERE:
        assert not re.fullmatch(r"(tabell|seksjon|del)-\d+", anker), anker


def test_semantisk_tabell():
    html = _side()
    for tabell in re.findall(r"<table id=.*?</table>", html, re.S):
        assert "<caption>" in tabell
        assert "<thead>" in tabell and "<tbody>" in tabell
        assert 'scope="col"' in tabell


def test_datoer_er_time_elementer():
    """En dato i løpende tekst er en streng. En i `<time datetime>` er en
    dato en maskin kan lese — og en leser kan kopiere uten å gjette
    formatet."""
    html = _side()
    assert '<time datetime="2026-08-10">2026-08-10</time>' in html
    assert '<time datetime="2018-03-13">2018-03-13</time>' in html


def test_ingen_javascript():
    """Tallene skal finnes i kildekoden, ikke tegnes. En side som tegnes
    av et skript kan ikke siteres, ikke arkiveres av Wayback, og ikke
    leses av noen som har slått det av."""
    html = _side()
    skript = re.findall(r"<script[^>]*>", html)
    assert skript == ['<script type="application/ld+json">'], skript
    assert "onclick" not in html and "onload" not in html


def test_tallene_staar_i_kildekoden():
    html = _side()
    assert "0.0045454544" in html          # lusetallet
    assert "928957489" in html             # eierens orgnr
    assert ">11</td>" in html and ">10</td>" in html   # endringen fra/til


def test_attribusjonen_staar_i_den_genererte_html_en():
    """Kravet er synlighet for den som LESER, ikke for den som kjører.
    En setning i en docstring er ikke attribusjon."""
    html = _side()
    assert "Data levert av BarentsWatch" in html
    assert ("Opplysninger om lakselus, rensefisk og medikamentbruk er "
            "hentet fra Mattilsynet.") in html
    assert "Kilde: Fiskeridirektoratet" in html
    assert "Brønnøysundregistrene" in html


# ---- JSON-LD ----------------------------------------------------------

def _jsonld_av(html: str) -> dict:
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                  html, re.S)
    assert m, "ingen JSON-LD i <head>"
    return json.loads(m.group(1))


def test_jsonld_er_gyldig_json_og_ikke_html_escapet():
    """Regresjonstesten for en MÅLT feil, 16.09.2026.

    Første utkast skrev `{{ jsonld }}` med autoescaping på, og hvert
    anførselstegn ble `&#34;`. Innholdet i en `<script>` er raw text i
    HTML — entiteter dekodes ikke der — så JSON-LD-en var ugyldig for
    enhver parser. Siden så helt riktig ut i nettleseren, fordi
    ingenting av dette vises."""
    raa = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                    _side(), re.S).group(1)
    assert "&#34;" not in raa and "&amp;" not in raa
    assert json.loads(raa)["@type"] == "Dataset"


def test_jsonld_kan_ikke_bryte_ut_av_script_taggen():
    """Og den andre halvdelen: `|safe` alene ville vært et hull.
    `json.dumps` escaper ikke `<`, så et navn med `</script>` i ville
    avsluttet taggen. `\\u003c` er gyldig JSON og betyr fortsatt `<`,
    men HTML-parseren ser ingen tagg."""
    html = _side(navn="OTER</script><img onerror=x>NESET")
    raa = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                    html, re.S).group(1)
    assert "</script>" not in raa
    assert "\\u003c" in raa
    assert json.loads(raa)["name"].startswith("Lokalitet 31397 OTER</script>")


def test_jsonld_paastaar_ingen_url_og_ingen_ugyldig_lisens():
    """Domenet finnes ikke ennå. En absolutt URL med et påfunnet
    vertsnavn ville vært en påstand om noe som ikke er avgjort — og
    `license` på toppnivå ville skjult at kildene har hver sin
    lisensgiver."""
    d = _jsonld_av(_side())
    assert "url" not in d
    assert "license" not in d
    assert d["identifier"]["value"] == "31397"
    assert "siteNr" in d["identifier"]["propertyID"]


def test_jsonld_oppgir_lisensversjon_bare_der_den_er_belagt():
    """Fiskeridirektoratets lisensside sier «NLOD» uten versjon. En lenke
    til 2.0 for den kilden ville påstått en versjon ingen har gått god
    for — se docs/LISENSKJEDE.md merknad A mot merknad B."""
    d = _jsonld_av(_side())
    per_kilde = {k["name"]: k for k in d["isBasedOn"]}
    assert "license" not in per_kilde["akvakultur"]
    assert per_kilde["eierskap"]["license"] == "https://data.norge.no/nlod/no/2.0"


def test_jsonld_har_en_kilde_per_kilde_siden_bruker():
    d = _jsonld_av(_side())
    assert [k["name"] for k in d["isBasedOn"]] == list(nettsted.SIDENS_KILDER)


# ---- merkekonvensjonen ------------------------------------------------

def test_navn_er_merket_slik_publiseringsvakten_kan_se_dem():
    """Avtalen med `publiseringsvakt.navn_i()`: vakten ser bare navn en
    generator har MERKET. Det sto som et åpent punkt i beslutningen
    15.09 — konvensjonen måtte bestemmes FØR generatoren ble skrevet.

    Faller denne, er vakten blind for navnene på siden uten at noe annet
    endrer seg, og `ukjent_navn`-prøven blir en prøve som alltid sier
    ja."""
    import publiseringsvakt as vakt

    funnet = set(vakt.navn_i(_side()))
    assert "SALMAR OPPDRETT AS" in funnet
    assert "SALMAR NORD AS" in funnet
    assert "SALMAR FARMING AS" in funnet


def test_lokalitetsnavnet_er_merket():
    assert "<span data-navn>" in _side()


# ---- rendringen av fravær ---------------------------------------------

def test_manglende_lusetall_er_ikke_null():
    """«gikk til null» og «sluttet å rapportere» betyr helt forskjellige
    ting. Målt på OTERNESET: 207 av 764 uker har ingen
    `voksne_hunnlus`-rad, og i alle 207 er `lus_er_rapportert` False.

    En 0 i cellen ville vært en påstand kilden ikke har gjort; en tom
    celle ville latt leseren gjette."""
    assert nettsted.INGEN_VERDI not in ("0", "", None)
    html = _side(lus=[{
        "uke": "2026 uke 29", "dato": "2026-07-13",
        "voksne_hunnlus": nettsted.INGEN_VERDI, "lus_er_rapportert": "nei",
        "har_laksefisk": "ja", "brakklagt": "ja",
        "har_medikamentell_behandling": "nei",
        "har_mekanisk_fjerning": "nei", "har_rensefisk": "nei",
    }])
    assert f'<td class="tall">{nettsted.INGEN_VERDI}</td>' in html
    assert '<td class="tall">0</td>' not in html


def test_janei_har_ingen_standardverdi():
    """«nei» og «–» er ikke det samme, og kartet har derfor ingen
    fallback: en verdi kilden ikke har sendt skal ikke bli til «nei»."""
    assert nettsted.JANEI == {"True": "ja", "False": "nei"}
    assert nettsted.JANEI.get("kanskje") is None


# ---- hva som telles som en endring ------------------------------------

def test_maaleserier_telles_ikke_som_registerendringer():
    """Skillet er en LISTE og ikke en heuristikk, av samme grunn som
    `changelog.TAUSHETSKILDER` er det: en kilde som ikke står der
    behandles som en registerkilde, altså VISES, og usikkerhet ser ut
    som usikkerhet framfor å forsvinne."""
    assert nettsted.MAALESERIER == {"lusetall", "sjotemperatur"}
    assert "akvakultur" not in nettsted.MAALESERIER
    assert "eierskap" not in nettsted.MAALESERIER


def test_siden_sier_hvor_mange_maaleserierader_som_er_holdt_utenfor():
    """Et utvalg som ikke sier at det er et utvalg, lyver ved
    utelatelse."""
    assert "1284" in _side()
