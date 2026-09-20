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

def _uke_raa(**overstyr) -> dict:
    """Én uke slik `_lusserie()` returnerer den: kildens egne verdier.

    `True`/`False` og ikke `ja`/`nei`, tom streng og ikke «–». Skillet
    er hele grunnen til at `til_visning()` finnes — CSV-en bærer det
    kilden sa, HTML-en det et menneske leser."""
    uke = {
        "dato": "2026-08-10", "iso_aar": "2026", "iso_uke": "33",
        "voksne_hunnlus": "0.0045454544", "lus_er_rapportert": "True",
        "har_laksefisk": "True", "brakklagt": "False",
        "har_medikamentell_behandling": "False",
        "har_mekanisk_fjerning": "False", "har_rensefisk": "False",
    }
    uke.update(overstyr)
    return uke


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
        # RÅSERIEN, slik `_lusserie()` gir den: kildens egne verdier og
        # tom streng for fravær. `lus` er den samme raden kjørt gjennom
        # `til_visning()`, og at de to bygges av SAMME liste her er
        # poenget — CSV-en og tabellen kan ikke bli uenige.
        "lus_serie": [_uke_raa()],
        "lus": nettsted.til_visning([_uke_raa()]),
        "lus_fra": "2012-01-02", "lus_til": "2026-08-17",
        "lus_uker": 764, "lus_uten_tall": 207,
        "csv_filnavn": nettsted.CSV_FILNAVN,
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
    mangler = {k: v for k, v in nettsted.til_visning([_uke_raa()])[0].items()
               if k != "voksne_hunnlus"}
    with pytest.raises(UndefinedError):
        _side(lus=[mangler])


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


def test_endringstabellen_merker_verdicellene_med_feltnavnet():
    """Fra- og til-cellene bærer changeloggens `old_value`/`new_value`,
    altså verdier fra ELDRE snapshots enn dem hvitelista er bygget av.

    MÅLT 18.09.2026: 24 navneverdier sto i disse cellene uten at
    `ukjent_navn` kunne se én av dem, fordi cellene var umerkede. En
    statisk klasse duger ikke — samme `<td>` bærer `siste_rapport` i én
    rad og `eier_navn` i neste — så merkingen er radens felt.
    """
    import publiseringsvakt as vakt

    side = _side(endringer=[{
        "dato": "2026-09-17", "gjelder": "tillatelse N-T-0001",
        "kilde": "eierskap", "felt": "eier_navn",
        "fra": "TESTVIK OG STRAUM DA", "til": "TESTLAKS AS",
    }])
    assert ("eier_navn", "TESTVIK OG STRAUM DA") in vakt.felt_verdier(side)
    assert ("eier_navn", "TESTLAKS AS") in vakt.felt_verdier(side)


def test_registertabellen_merker_verdicellene_med_feltnavnet():
    import publiseringsvakt as vakt

    side = _side(register=[("navn", "OTERNESET"), ("kapasitet", "8000.0")])
    # PAR og ikke dict: samme feltnavn kan stå i to tabeller med hver sin
    # betydning. Fra 19.09.2026 bærer både registertabellen og
    # eierskapstabellen `data-felt="kapasitet"` — lokalitetens kapasitet
    # og tillatelsens — og begge er riktige, for begge kildene kaller
    # feltet det. En dict her ville skjult den ene bak den andre.
    merket = vakt.felt_verdier(side)
    assert ("navn", "OTERNESET") in merket
    assert ("kapasitet", "8000.0") in merket


def test_et_navn_i_endringstabellen_felles_av_porten(tmp_path):
    """Hele veien, av den rendrede sida: et personformnavn i en
    changelog-verdi skal bli et funn, og det skal IKKE bli et funn hvis
    merkingen fjernes. Det andre leddet er poenget — uten det måler
    testen at porten fyrer, ikke at merkingen er grunnen.
    """
    import re

    import publiseringsvakt as vakt

    side = _side(endringer=[{
        "dato": "2026-09-17", "gjelder": "tillatelse N-T-0001",
        "kilde": "eierskap", "felt": "eier_navn",
        "fra": "TESTVIK OG STRAUM DA", "til": "TESTLAKS AS",
    }])
    # Hvitelista som om alt annet på sida var gjort rede for.
    navn_ok = {n for _f, n in vakt.felt_verdier(side)} | set(vakt.navn_i(side))
    navn_ok.discard("TESTVIK OG STRAUM DA")
    orgnr_ok = set(vakt.NI_SIFFER.findall(side))

    # TO funn fra 19.09.2026, og det er en SKJERPING: `DA` er målt
    # tvetydig i dataene — 748 rader `kapasitet_enhet` er dekar — så
    # tekstprøven fyrer ikke på endelsen. Men `DA` som siste ord i en
    # celle merket `data-felt="eier_navn"` er delt ansvar, og merkingen
    # sier hvilket av de to det er. Fram til 19.09 meldte denne bare
    # `ukjent_navn`.
    funn = vakt.gransk_tekst(side, orgnr_ok, navn_ok, fil="index.html",
                             tvetydige={"DA"})
    assert sorted(f.slag for f in funn) == ["personform", "ukjent_navn"]

    # Og personform-funnet er ATTRIBUERT, altså kvitterbart: nøkkelen er
    # feltet og verdien, ikke slaget.
    pf = [f for f in funn if f.slag == "personform"][0]
    assert pf.noekkel.startswith("eier_navn/")
    assert "TESTVIK" not in str(pf)

    # Andre halvdel, og poenget: uten merkingen ser porten ingenting.
    # Begge funnene forsvinner, ikke bare det ene.
    umerket = re.sub(r'\s*data-felt="[^"]*"', "", side)
    assert vakt.gransk_tekst(umerket, orgnr_ok, navn_ok,
                             tvetydige={"DA"}) == []


# ---- eierskap_historikk vises IKKE i endringstabellen ------------------

def test_eierskap_historikk_er_uttrykkelig_utelatt():
    """En tilsiktet utelatelse som ser ut som en feil blir rettet.

    Fram til 18.09.2026 sto kilden i filteret og var DØD KODE: MÅLT har
    30 104 av 30 104 rader `entity_id` på formen `F-A-0034|2007000034`,
    så `entity_id in tillatelser` kunne treffe 0. Å «rette» det er en
    publiseringsbeslutning og ikke en opprydding — to av radene bærer
    navnet på et DA i sektor 2300, og lesedøra kan ikke se dem.

    Faller denne, er valget endret — og da skal beslutningen endres med
    den. Se docs/beslutninger/2026-09-18-changeloggens-persondata-ligger-stille.md
    """
    assert "eierskap_historikk" in nettsted.ENDRINGER_UTELATT
    assert "eierskap_historikk" not in nettsted.ENDRINGER_VIA_TILLATELSE
    assert not (nettsted.ENDRINGER_UTELATT & nettsted.ENDRINGER_VIA_TILLATELSE)


def test_utelatt_kilde_naar_ikke_endringstabellen():
    """Oppførselen, ikke bare konstanten: en rad fra den utelatte kilden
    på en tillatelse vi VISER, skal ikke bli en tabellrad."""
    from types import SimpleNamespace

    def rad(kilde):
        return {"entity_id": "N-T-0001", "source": kilde,
                "field": "mottaker_navn", "old_value": "", "new_value": "X",
                "observed_at": "2026-09-17", "change_type": "ny"}

    felles = SimpleNamespace(
        registerendringer={"N-T-0001": [rad("eierskap"),
                                        rad("eierskap_historikk")]},
        maaleserierader={})
    rader, _ = nettsted._endringer_av_indeks("10001", ["N-T-0001"], felles)
    assert [r["kilde"] for r in rader] == ["eierskap"]


# ---- rendringen av fravær ---------------------------------------------

def test_manglende_lusetall_er_ikke_null():
    """«gikk til null» og «sluttet å rapportere» betyr helt forskjellige
    ting. Målt på OTERNESET: 207 av 764 uker har ingen
    `voksne_hunnlus`-rad, og i alle 207 er `lus_er_rapportert` False.

    En 0 i cellen ville vært en påstand kilden ikke har gjort; en tom
    celle ville latt leseren gjette."""
    assert nettsted.INGEN_VERDI not in ("0", "", None)

    # Gjennom `til_visning()` og ikke med ferdigrendrede verdier: det er
    # oversettelsen som skal prøves, ikke om malen kan skrive ut en
    # streng den fikk servert.
    brakklagt = _uke_raa(voksne_hunnlus="", lus_er_rapportert="False",
                         brakklagt="True")
    html = _side(lus_serie=[brakklagt],
                 lus=nettsted.til_visning([brakklagt]))

    # Cellen finnes via MERKINGEN og ikke via en attributtstreng: hvilke
    # klasser en celle har er fritt (se docs/beslutninger/
    # 2026-09-19-markup-er-en-kontrakt.md), og en test som låste
    # `class="tall"` ville felt neste designrunde uten grunn.
    import publiseringsvakt as vakt

    merket = vakt.felt_verdier(html)
    assert ("voksne_hunnlus", nettsted.INGEN_VERDI) in merket
    assert ("voksne_hunnlus", "0") not in merket
    # Og raden bærer fortsatt det som GJØR fraværet lesbart.
    assert ("lus_er_rapportert", "nei") in merket


def test_janei_har_ingen_standardverdi():
    """«nei» og «–» er ikke det samme, og kartet har derfor ingen
    fallback: en verdi kilden ikke har sendt skal ikke bli til «nei»."""
    assert nettsted.JANEI == {"True": "ja", "False": "nei"}
    assert nettsted.JANEI.get("kanskje") is None


# ---- batchen: 1782 sider, og de to veiene til samme side --------------
#
# `bygg_lokalitet()` er skrevet for ÉN side og leser da alt selv. Målt
# 17.09.2026 koster ett kall 9,06 s — 6,4 s changelog, 2,6 s alle 764
# lusetallsnapshots — og naivt over 1782 sider er det 4,5 timer.
#
# `les_felles()` gjør de samme lesingene én gang. Det er forskjellen på
# en byggejobb som kan kjøre og en som ikke kan, og den er bare trygg så
# lenge de to veiene gir NØYAKTIG samme side.


@pytest.fixture
def datamappe(tmp_path, monkeypatch):
    """Et lite, ekte snapshotsett: to lokaliteter, én med lusetall.

    Bygget av `snapshot.write()` og ikke av håndskrevne parquet-filer:
    da går dataene gjennom den samme døra og de samme vaktene som i
    drift, og testen måler generatoren framfor sin egen fikstur.
    """
    from core import snapshot as snap
    from core.contract import Observation

    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snap, "RAW_DIR", rot)

    def obs(eid, felt, verdi, kilde, dato, navn=""):
        return Observation(entity_id=eid, entity_type="lokalitet",
                           entity_name=navn, field=felt, value=verdi,
                           source=kilde, observed_at=dato)

    # To lokaliteter. 10001 har alt; 10002 har verken eier eller lusetall.
    akva = []
    for eid, navn in (("10001", "TESTHOLMEN"), ("10002", "TOMHOLMEN")):
        for felt, verdi in (("navn", navn), ("kommune", "BODØ"),
                            ("fylke", "NORDLAND"), ("breddegrad", "67.1"),
                            ("lengdegrad", "14.2"), ("kapasitet", "780.0")):
            akva.append(obs(eid, felt, verdi, "akvakultur", "2026-09-14", navn))
    akva.append(obs("10001", "tillatelser", "N-T-0001", "akvakultur",
                    "2026-09-14", "TESTHOLMEN"))
    snap.write(akva, "2026-09-14")

    eierskap = [
        Observation(entity_id="N-T-0001", entity_type="tillatelse",
                    entity_name="N-T-0001", field=felt, value=verdi,
                    source="eierskap", observed_at="2026-09-14")
        for felt, verdi in (("eier_navn", "TESTLAKS AS"),
                            ("eier_orgnr", "912345678"),
                            ("organisasjonsform", "AS"),
                            ("lokaliteter", "10001"))
    ]
    snap.write(eierskap, "2026-09-14")

    for dato, lus in (("2026-08-10", "0.12"), ("2026-08-17", "")):
        rader = [obs("10001", "lus_er_rapportert",
                     "True" if lus else "False", "lusetall", dato, "TESTHOLMEN")]
        if lus:
            rader.append(obs("10001", "voksne_hunnlus", lus, "lusetall",
                             dato, "TESTHOLMEN"))
        snap.write(rader, dato)
    return rot


def test_batch_gir_samme_side_som_enkelt(datamappe):
    """Den ene invarianten hele batchen hviler på.

    To veier til samme side som kan svare ulikt, er formen F6 og F7
    hadde: et andre oppslag som i visse tilfeller gir noe annet enn det
    første. Her ville følgen vært at en side bygget alene og den samme
    sida bygget i batch viste ulike tall — og ingen av dem ville sagt fra."""
    felles = nettsted.les_felles()
    for loknr in ("10001", "10002"):
        assert nettsted.bygg_lokalitet(loknr) == \
            nettsted.bygg_lokalitet(loknr, felles)


def test_skriv_alle_gir_en_mappe_med_side_og_csv_per_lokalitet(datamappe, tmp_path):
    ut = tmp_path / "nettsted"
    logg, tider = nettsted.skriv_alle(ut)

    assert logg.sider == 2
    assert logg.feilet == []
    for loknr in ("10001", "10002"):
        assert (ut / "lokalitet" / loknr / "index.html").is_file()
        assert (ut / "lokalitet" / loknr / nettsted.CSV_FILNAVN).is_file()
    assert set(tider) == {"felleslesing", "malkompilering", "rendring_og_skriving"}


def test_byggelogget_teller_det_som_ikke_gikk_rent(datamappe, tmp_path):
    """Et bygg som bare sier «ferdig» skjuler nøyaktig det man trenger å
    vite. Kategoriene skrives også når de er null — et tall man bare ser
    når det er galt, er et tall ingen kjenner normalverdien til."""
    logg, _ = nettsted.skriv_alle(tmp_path / "nettsted")

    assert logg.uten_eier == ["10002"]
    assert logg.uten_tillatelser == ["10002"]
    assert logg.uten_lusetall == ["10002"]
    assert logg.uten_koordinater == []
    assert sorted(logg.uten_prodomraade) == ["10001", "10002"]


def test_en_feilende_side_feller_ikke_de_andre(datamappe, tmp_path, monkeypatch):
    """Samme regel som `runner.run_all()`: én knekt ting koster én ting.

    Feilen føres med lokalitetsnummer og melding, og byggingen ender
    rødt — den forsvinner ikke."""
    ekte = nettsted.bygg_lokalitet

    def sprekk(loknr, felles=None):
        if loknr == "10001":
            raise ValueError("konstruert feil")
        return ekte(loknr, felles)

    monkeypatch.setattr(nettsted, "bygg_lokalitet", sprekk)
    logg, _ = nettsted.skriv_alle(tmp_path / "nettsted")

    assert logg.sider == 1
    assert logg.feilet == [("10001", "ValueError: konstruert feil")]
    assert (tmp_path / "nettsted" / "lokalitet" / "10002" / "index.html").is_file()


def test_lokalitet_uten_lusetall_gir_ingen_tom_datetime(datamappe, tmp_path):
    """MÅLT 17.09.2026 over alle 1782 sider: 4 lokaliteter finnes ikke i
    noe lusetallsnapshot, og de fikk `<time datetime=""></time>` og
    «siste 0 uker … 0 av 0 uker, og i alle sammen står Rapportert: nei».

    `datetime=""` er ugyldig HTML, og setningen er en påstand om uker som
    ikke finnes. INGENTING KASTET: `StrictUndefined` fanger en manglende
    NØKKEL, ikke en tom VERDI. Det ble funnet ved å lese utputtet, ikke
    ved at bygget ble rødt — og det er derfor denne testen finnes."""
    ut = tmp_path / "nettsted"
    nettsted.skriv_alle(ut)
    html = (ut / "lokalitet" / "10002" / "index.html").read_text()

    assert 'datetime=""' not in html
    assert "Ingen lusetall for denne lokaliteten." in html
    assert "siste 0 uker" not in html
    # ...og ankeret står, så en lenke til tabellen ikke dør av at den er tom
    assert '<table id="lusetall-uke">' in html


def test_csv_uten_uker_paastaar_ikke_et_spenn(datamappe, tmp_path):
    """Første utgave skrev «Ukentlig serie  til , 0 uker» — to tomme
    spenn og en påstand om en serie som ikke finnes.

    Fila skrives likevel: «vi har sett etter og ikke funnet noe» er et
    svar, og 404 er det ikke."""
    ut = tmp_path / "nettsted"
    nettsted.skriv_alle(ut)
    csv = (ut / "lokalitet" / "10002" / nettsted.CSV_FILNAVN).read_text()

    assert "Ukentlig serie  til" not in csv
    assert "INGEN UKER" in csv
    assert "Data levert av BarentsWatch" in csv
    assert csv.strip().splitlines()[-1].startswith("lokalitetsnummer,")


# ---- den siterbare CSV-en ---------------------------------------------
#
# Tabellen viser 52 uker, serien er 764. Hele den skal kunne siteres, og
# da må den ligge på en adresse noen kan lenke til. Se
# docs/beslutninger/2026-09-16-url-struktur.md punkt 8.


def _csv(**overstyr) -> str:
    lok = {
        "loknr": "31397", "navn": "OTERNESET", "kommune": "HARSTAD",
        "lus_fra": "2012-01-02", "lus_til": "2026-08-17",
        "lus_uker": 764, "lus_uten_tall": 207,
        "lus_serie": [_uke_raa()],
    }
    lok.update(overstyr)
    return nettsted.csv_tekst(lok, nettsted.attribusjon(["lusetall"]),
                              "2026-09-16")


def _datarader(tekst: str) -> list[str]:
    return [l for l in tekst.splitlines() if l and not l.startswith("#")]


def test_csv_bærer_attribusjonen_i_fila():
    """Ikke i en sidecar. En sidecar er borte i det øyeblikket noen
    laster ned CSV-en alene, som er nøyaktig det man gjør med en CSV —
    og BarentsWatch krever synlighet for SLUTTBRUKER, ikke for den som
    fant begge filene."""
    tekst = _csv()
    assert "# Data levert av BarentsWatch" in tekst
    assert ("# Opplysninger om lakselus, rensefisk og medikamentbruk er "
            "hentet fra Mattilsynet.") in tekst


def test_csv_attribusjonen_hentes_fra_kilden():
    """Samme indeks som bunnteksten på siden bruker, så de to kan ikke
    bli uenige. Skrevet av her, ville CSV-en blitt stående med gammel
    ordlyd den dagen vilkåret endres."""
    for setning in nettsted.attribusjon(["lusetall"]):
        assert f"# {setning}" in _csv()


def test_csv_bærer_BARE_lusetallkildens_attribusjon():
    """Fila inneholder bare lusetall. Å legge alle fire kildenes
    setninger i hodet ville vært en påstand om at Fiskeridirektoratet har
    levert noe her."""
    tekst = _csv()
    assert "Kilde: Fiskeridirektoratet" not in tekst
    assert "Brønnøysundregistrene" not in tekst


def test_csv_sier_hvordan_den_skal_leses():
    """RFC 4180 kjenner ingen kommentarsyntaks. En leser som ikke hopper
    over `#`-linjene får den første som kolonneoverskrifter — og derfor
    står lesemåten i fila og ikke bare i et notat."""
    assert 'comment_prefix="#"' in _csv()


def test_csv_har_hele_serien_ikke_utsnittet():
    """Hele poenget. Tabellen viser slutten av serien; fila er serien."""
    uker = [_uke_raa(dato=f"2026-0{m}-01", iso_uke=f"{m:02d}")
            for m in range(1, 10)]
    rader = _datarader(_csv(lus_serie=uker, lus_uker=len(uker)))
    assert len(rader) == 1 + len(uker)          # overskrift + radene


def test_csv_har_kildens_egne_verdier_uoversatt():
    """BarentsWatch-vilkåret sier uttrykkelig at datainnholdet ikke skal
    endres. `ja`/`nei` og «–» er VÅR lesning, og de hører hjemme i
    HTML-en."""
    rad = _datarader(_csv())[1]
    assert "True" in rad and "ja" not in rad
    assert nettsted.INGEN_VERDI not in rad


def test_csv_lar_fravaer_vaere_tomt_og_ikke_null():
    """Samme skille som i HTML, uttrykt slik en parser leser det: en tom
    celle er ikke tallet 0. `lus_er_rapportert` på samme rad er det som
    gjør fraværet lesbart."""
    tomt = _uke_raa(voksne_hunnlus="", lus_er_rapportert="False")
    rad = _datarader(_csv(lus_serie=[tomt]))[1]
    felter = rad.split(",")
    kolonner = list(nettsted.CSV_KOLONNER)
    assert felter[kolonner.index("voksne_hunnlus")] == ""
    assert felter[kolonner.index("lus_er_rapportert")] == "False"


def test_csv_kan_leses_av_en_vanlig_parser():
    """Prøven som teller: går fila gjennom `csv`-modulen med
    kommentarlinjene hoppet over, og kommer tallene ut igjen?"""
    import csv as csvmodul

    tekst = _csv()
    rader = list(csvmodul.DictReader(_datarader(tekst)))
    assert len(rader) == 1
    assert rader[0]["lokalitetsnummer"] == "31397"
    assert rader[0]["voksne_hunnlus"] == "0.0045454544"
    assert rader[0]["iso_aar"] == "2026" and rader[0]["iso_uke"] == "33"


def test_csv_kolonnene_er_en_kontrakt():
    """Kolonnenavn er en kontrakt mot enhver som har lastet ned fila.
    Endres ett av dem, er det en brutt lesning for alle som har skrevet
    et skript mot den — samme klasse løfte som ankerne."""
    assert nettsted.CSV_KOLONNER == (
        "lokalitetsnummer", "dato", "iso_aar", "iso_uke",
        "voksne_hunnlus", "lus_er_rapportert", "har_laksefisk", "brakklagt",
        "har_medikamentell_behandling", "har_mekanisk_fjerning",
        "har_rensefisk")


def test_csv_filnavnet_staar_ett_sted():
    """Navnet står på disk, i lenka fra sida og i `contentUrl`. Tre
    strenger som skal si det samme er formen F6 og F7 hadde."""
    html = _side()
    assert f'href="{nettsted.CSV_FILNAVN}"' in html
    assert _jsonld_av(html)["distribution"][0]["contentUrl"] == \
        nettsted.CSV_FILNAVN


def test_jsonld_distribution_peker_paa_hele_serien():
    d = _jsonld_av(_side())
    [dist] = d["distribution"]
    assert dist["@type"] == "DataDownload"
    assert dist["encodingFormat"] == "text/csv"
    assert dist["creditText"] == "Data levert av BarentsWatch"
    assert "764 uker" in dist["description"]


def test_jsonld_contentUrl_er_relativ():
    """Domenet finnes ikke ennå. JSON-LD løser relative IRI-er mot
    dokumentets egen adresse, så «lusetall.csv» peker riktig uansett
    hvilket vertsnavn siden havner på — og et påfunnet domene ville vært
    en påstand om noe som ikke er avgjort."""
    url = _jsonld_av(_side())["distribution"][0]["contentUrl"]
    assert not url.startswith(("http://", "https://", "/"))


def test_siden_lenker_til_csv_en():
    """Fila er ikke siterbar hvis ingen finner den."""
    html = _side()
    assert f'<a href="{nettsted.CSV_FILNAVN}">' in html
    assert "764 uker" in html


def test_serien_og_tabellen_kommer_fra_samme_liste():
    """Det som gjør at CSV-en og tabellen ikke kan bli uenige.

    `bygg_lokalitet()` legger hele serien i `lus_serie` og viser slutten
    av den i `lus`. Leste de to hver sin kilde, kunne de sagt forskjellig
    om samme uke — og da ville fila og siden vært to påstander."""
    uker = [_uke_raa(dato=f"2026-0{m}-01", voksne_hunnlus=f"0.{m}")
            for m in range(1, 5)]
    vist = nettsted.til_visning(list(reversed(uker))[:2])
    html = _side(lus_serie=uker, lus=vist, lus_uker=len(uker))

    assert "0.4" in html and "0.3" in html      # de to viste ukene
    assert ">0.1</td>" not in html              # resten står i fila


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
