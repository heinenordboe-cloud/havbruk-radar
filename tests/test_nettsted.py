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
from pathlib import Path

import pytest

import kart
import nettsted
import visningsord


def _visning(rader):
    """Fiksturens (felt, verdi)-par til malens fire ledd.

    Prøvene skriver den RÅ forma — `("kapasitet", "8000.0")` — fordi det
    er den kilden leverer og den som er lesbar i en prøve. Omregningen
    gjøres her med `visningsord` selv, ikke med håndskrevne strenger: en
    fikstur som stavet «8 680» for hånd ville sagt grønt om
    tusenskillet byttet tegn.

    Fjerde ledd er «sist observert» — `observed_at` fra changeloggen.
    Tom her, som den er for et felt som ikke har endret seg i loggen.
    """
    return [(f, visningsord.felt(f), visningsord.verdi(f, v), "")
            for f, v in rader]


def _endringsrader(rader):
    """Fiksturens rå endringsrader til den forma malene får.

    `etikett` er feltets, `fra`/`til` oversettes, og `felt` blir
    stående som kildens navn.

    `datoslag`/`datoord` sier HVA DATOEN ER — dagen vi hentet, eller
    uka raden handler om. Den utledes av kildens `partisjonering`, og
    fiksturen kaller `nettsted._endringsrad()` for å få den: en fikstur
    som satte ordet selv kunne sagt «Observert» om en `verden`-kilde
    uten at noe felte det."""
    return [nettsted._endringsrad(
        {"observed_at": r["dato"], "entity_id": r.get("entity_id", "31397"),
         "source": r["kilde"], "field": r["felt"],
         "old_value": r.get("fra", ""), "new_value": r.get("til", "")},
        r.get("loknr", "31397"))
        | {"gjelder": r.get("gjelder", "lokaliteten")}
        for r in rader]


def _stilark(undermappe: str) -> str:
    """Stilarkstien en side på `undermappe` ville fått.

    Regnes av `nettsted.stilsti()` framfor å skrives av: en fikstur med
    sin egen `"../../stil.css"` er en fikstur som sier grønt om koden
    har byttet hvordan stien bygges. Samme grunn som at
    `_po()` henter fargeklassen fra `FARGE_KLASSE`.
    """
    rot = Path("/ut")
    sti = rot / undermappe / "index.html" if undermappe else rot / "index.html"
    return nettsted.stilsti(sti, rot)


def _grunn(undermappe: str = "", **over) -> dict:
    """Nøklene `base.html.j2` krever, for en prøve som rendrer direkte.

    Speiler `nettsted._grunnkontekst()`. Den KAN ikke brukes her: den
    tar en `Felles`, og suiten har ingen data å bygge en av. Men de to
    skal kreve det samme, og `test_grunnkonteksten_dekker_grunnmalen`
    holder dem sammen — to steder som skal si det samme om hvilke
    nøkler malen trenger, er formen F6 og F7 hadde.
    """
    grunn = {
        "tittel": "T", "beskrivelse": "B", "jsonld": "{}",
        "attribusjon": ["Kilde: Fiskeridirektoratet"],
        "stilark": _stilark(undermappe),
        "bygget": "2026-09-20",
        "bygget_vist": "20. september 2026",
        "proveniens": "Bygget fra øyeblikksbildet for uke 38, 2026.",
        "repo": "https://github.com/heinenordboe-cloud/havbruk-radar",
        "kontakt": "",
        "meny_aktiv": "",
        "feed": "",
        "feed_tittel": "",
        "main_klasse": "",
        "side_skript": "",
    }
    grunn.update(over)
    return grunn


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
        # `_visning()` under gjør de to leddene til fire: feltnavn,
        # etikett, oversatt verdi og «sist observert».
        "tillatelser": [{
            "nr": "T-D-0009", "eier_navn": "SALMAR OPPDRETT AS",
            "eier_felt": "eier_navn",
            "eier_orgnr": "928957489", "type": "KOMM-MATF",
            "kapasitet": "1022.0", "kapasitet_enhet": "TN",
            "tildelt_dato": "2004-09-29", "tildelt_navn": "SALMAR NORD AS",
        }],
        # Standarden er ENIGE kilder: alle tillatelser akvakultur oppgir
        # er gjort rede for i eierskap. Testene under overstyrer.
        "tillatelser_oppgitt": 1,
        "tillatelser_uten_eier": 0,
        "eier_ukjent": nettsted.EIER_UKJENT,
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
        "lusetall_snapshots": 765,
        "csv_filnavn": nettsted.CSV_FILNAVN,
        "endringer": [{
            "dato": "2026-08-31", "gjelder": "lokaliteten",
            "kilde": "akvakultur", "felt": "tillatelser_antall",
            "fra": "11", "til": "10",
        }],
        "maaleserie_rader": 1284,
        "dekning_fra": [{"kilde": "akvakultur", "fra": "2026-08-17"}],

        # ---- overskriften ----
        "tittelnavn": "Oterneset",
        "akva_hentet": "2026-09-14T04:00:00+00:00",
        "status": "gul", "status_klasse": "lys-gul",
        "arter": "laks", "klareringstype": "permanent",
        "vanntype": "saltvann", "plassering": "i sjø",
        "kapasitet": "8 000 tonn", "kapasitet_midlertidig": "8 000 tonn",
        "selskap": {"navn": "SALMAR OPPDRETT AS", "orgnr": "928957489",
                    "url": "/selskap/928957489/", "siden": "2022-12-30",
                    "antall": 1, "flere": 0, "personform": False},
        "lusegraf": None,
        "posisjonskart": kart.posisjonskart("68.9288", "16.701367"),
        "biolag": nettsted._biolagstripe(
            [{"dato": "2026-09-15", "har_fisk": "Ja",
              "arter_tilstede": "Laks", "antall_arter": "1",
              "siste_rapport": "2026-08-31", "lokalitet_status": "AKTIV"}],
            ["2026-09-15"]),
        "siter": {"url": "https://kystloggen.no/lokalitet/31397/",
                  "uke": "uke 38, 2026", "dato": "14. september 2026",
                  "aar": "2026", "sjekksum": "efe1c0884c4e39d20b7d775a363d"},
    }
    lok.update(overstyr)
    # DE TO HISTORIKKENE regnes av de samme listene siden viser, ikke
    # skrives ved siden av dem. Et `overstyr` som bytter endringene skal
    # bytte tidsaksen med dem — to felter som beskriver det samme og kan
    # sies hver for seg, er formen F6 og F7 hadde.
    lok.setdefault("observert", nettsted._observert_historikk(
        _endringsrader(lok["endringer"]), lok["dekning_fra"], None))
    lok.setdefault("oppgitt", nettsted._oppgitt_historikk(
        {"forste_klarering": "2010-11-10T23:00:00Z"},
        lok["tillatelser"], lok["overforinger"]))
    # GRAFEN REGNES AV `lus_serie`, ikke skrevet inn ved siden av. Et
    # `overstyr` som bytter serien skal bytte grafen med den — to
    # felter som beskriver samme uker og kan sies hver for seg, er
    # formen på F6 og F7.
    lok.setdefault("lusegraf", nettsted.lusegraf(lok["lus_serie"]))
    lok["register"] = _visning(lok["register"])
    lok["endringer"] = _endringsrader(lok["endringer"])
    for t_ in lok["tillatelser"]:
        if "kapasitet_enhet" in t_:
            t_["kapasitet"] = visningsord.maalt(t_.pop("kapasitet"),
                                                t_.pop("kapasitet_enhet"))
    return nettsted._miljo().get_template("lokalitet.html.j2").render(
        lok=lok,
        **_grunn("lokalitet/31397", bygget="2026-09-16",
                 jsonld=nettsted.jsonld(lok),
                 attribusjon=nettsted.attribusjon(nettsted.SIDENS_KILDER)),
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
            lok={"loknr": "1"},
            **_grunn("lokalitet/31397", bygget="2026-09-16", attribusjon=[]))

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
    # Fra 22.09.2026: biomasselaget, altså om det står fisk på
    # lokaliteten. `<kilde>-<hva>`, som de andre.
    "biomasselag-uke",
}


def test_hvert_anker_finnes_fortsatt_paa_sida():
    """Ankerne er kontrakten mot enhver som siterer siden. De er utledet
    av kildenavnet og feltvokabularet — ikke av rekkefølgen på siden og
    ikke av overskriftsteksten. Se
    docs/beslutninger/2026-09-16-url-struktur.md.

    PRØVEN SPØR OM `id`, IKKE OM `<table id>`. Fra 22.09.2026 er
    `#endringer-register` en `<section>` med en loddrett tidsakse og
    ikke en tabell — endringene er de samme, formen er ny. Ankeret er
    en URL, og en designrunde flytter ikke en adresse: hadde prøven
    fortsatt krevd en `<table>`, ville den tvunget fram enten en tabell
    ingen ville ha, eller et nytt ankernavn som brøt hver eksisterende
    lenke.

    Endres ett av navnene under, er det en brutt lenke for alle som har
    lenket dit. Denne testen er stedet man møter det."""
    html = _side()
    ider = set(re.findall(r'<(?:table|section)\b[^>]*?\bid="([^"]+)"', html))
    mangler = ANKERE - ider
    assert not mangler, f"ankere som ikke finnes lenger: {sorted(mangler)}"


def test_hver_tabell_har_en_id():
    """Markupkontraktens punkt 3, håndhevet på det RENDREDE utputtet.
    `test_markupkontrakt` leser malene; denne ser hva som faktisk kom
    ut."""
    for m in re.finditer(r"<table\b([^>]*)>", _side()):
        assert 'id="' in m.group(1), m.group(0)


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
        # `<caption` og ikke `<caption>`: fra 20.09.2026 bærer hver
        # caption en `id`, som scrollramma peker på med
        # `aria-labelledby`. Prøven skal si at tabellen HAR en caption,
        # ikke hvilke attributter den har.
        assert "<caption" in tabell
        assert "<thead>" in tabell and "<tbody>" in tabell
        assert 'scope="col"' in tabell


def test_datoer_er_time_elementer():
    """En dato i løpende tekst er en streng. En i `<time datetime>` er en
    dato en maskin kan lese — og en leser kan kopiere uten å gjette
    formatet."""
    html = _side()
    assert '<time datetime="2026-08-10">2026-08-10</time>' in html
    assert '<time datetime="2018-03-13">2018-03-13</time>' in html


def test_javascript_er_en_forbedring_og_ikke_en_avhengighet():
    """Regelen er ikke «ingen JavaScript» — den er at TALLENE SKAL STÅ I
    KILDEKODEN. En side som tegnes av et skript kan ikke siteres, ikke
    arkiveres av Wayback, og ikke leses av noen som har slått det av.

    Fra 22.09.2026 har nettstedet ett skript, og det legger ikke til én
    verdi: kopierknappen, søket i et område og filteret på
    endringssiden. Alle tre har en variant som virker uten. Prøven
    håndhever formen skriptet må ha — én egen fil, hostet av oss, med
    `defer`, og ingen innebygd kode noe sted."""
    html = _side()
    skript = re.findall(r"<script[^>]*>", html)
    assert skript == ['<script type="application/ld+json">',
                      '<script src="/kystloggen.js" defer>'], skript

    # INGEN INNEBYGD KODE. En `<script>` med kropp (utenom JSON-LD-en)
    # ville vært kode ingen kan pinne en sha256 på, og den ville kjørt
    # før `defer`-fila.
    innebygd = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                          html, re.S)
    assert len(innebygd) == 1, "bare JSON-LD-en skal være innebygd"

    # INGEN HENDELSESATTRIBUTTER. `onclick` i markupen er kode som ikke
    # kan slås av og ikke kan granskes som en fil.
    for attributt in ("onclick", "onload", "onchange", "oninput",
                      "onsubmit", "onerror"):
        assert attributt not in html.lower(), attributt

    # INGEN TREDJEPART. Skriptet er vårt, på vår adresse.
    assert 'src="/kystloggen.js"' in html
    assert "//" not in html.split('src="')[1].split('"')[0]


def test_tallene_staar_i_kildekoden():
    html = _side()
    assert "0.0045454544" in html          # lusetallet, kildens egen verdi
    assert "928957489" in html             # eierens orgnr
    # Endringen fra/til. Står i den loddrette tidsaksen fra 22.09.2026,
    # ikke i en tabellcelle — men de står, og det er kravet.
    assert ">11</span>" in html and ">10</span>" in html


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

    # NAVNET er UENDRET. Det er ikke en detalj: vakten sammenligner
    # navneverdien mot hvitelista bygget av snapshotene, og en oversatt
    # verdi ville ikke funnet seg selv der. `visningsord` rører ingen
    # NAVNEFELT — håndhevet av `test_navnefelt_oversettes_aldri`.
    assert ("navn", "OTERNESET") in merket

    # KAPASITETEN er formatert, og vakten ser det som STÅR PÅ SIDA. Fram
    # til 20.09.2026 sto «8000.0» der. At prøven leser «8 000» nå er
    # riktig vei: merkingen skal peke på verdien leseren ser, ikke på en
    # verdi som bare finnes i parquet-fila.
    assert ("kapasitet", visningsord.verdi("kapasitet", "8000.0")) in merket


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
        maaleserierader={}, sist_endret={})
    rader, _, _ = nettsted._endringer_av_indeks("10001", ["N-T-0001"], felles)
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

    # Enhetsregisteret: eieren av N-T-0001. `les_felles()` krever et
    # snapshot her fra 20.09.2026, da selskapssidene kom til — en kilde
    # som mangler skal kaste, ikke gi en tom dict i stillhet.
    snap.write([
        Observation(entity_id="912345678", entity_type="selskap",
                    entity_name="TESTLAKS AS", field=felt, value=verdi,
                    source="enhetsregisteret", observed_at="2026-09-14")
        for felt, verdi in (("navn", "TESTLAKS AS"),
                            ("organisasjonsform", "AS"),
                            ("kommune", "BODØ"),
                            ("naeringskode", "03.211"),
                            ("konkurs", "False"))
    ], "2026-09-14")

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
    # Én fase per sidetype, og hver fase MÅLES. En fase som ikke måles
    # er en fase ingen ser vokse.
    assert set(tider) == {"felleslesing", "malkompilering",
                          "rendring_og_skriving", "produksjonsomraader",
                          "selskaper", "forside", "indekser",
                          "endringssider", "feeder", "maskinfiler",
                          "sokeindeks"}
    for fil in ("sitemap.xml", "robots.txt", "llms.txt", "om/index.html"):
        assert (ut / fil).is_file(), fil
    assert logg.indekssider == 3
    for sti in ("lokalitet", "produksjonsomrade", "selskap"):
        assert (ut / sti / "index.html").is_file()
    assert (ut / "index.html").is_file()
    # Fiksturen har én eier med én tillatelse.
    assert logg.selskapssider == 1
    assert (ut / "selskap" / "912345678" / "index.html").is_file()
    # Fiksturen har ingen lokalitet med produksjonsområde, så det skal
    # ikke bli noen PO-side — og det er en ekte prøve på at lista bygges
    # av dataene og ikke av tretten hardkodede numre.
    assert logg.po_sider == 0
    # INDEKSEN finnes likevel — en tom liste er et svar, og en
    # manglende indeks ville gitt 404 på en lenke forsiden alltid har.
    # Det som ikke skal finnes, er en nummerert områdeside.
    assert (ut / "produksjonsomrade" / "index.html").is_file()
    assert [m.name for m in (ut / "produksjonsomrade").iterdir()] == ["index.html"]


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
        "lusetall_snapshots": 765,
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
    assert nettsted.MAALESERIER == {"lusetall", "sjotemperatur", "biomasse"}
    assert "akvakultur" not in nettsted.MAALESERIER
    assert "eierskap" not in nettsted.MAALESERIER

    # `biomasse` kom inn 20.09.2026 med produksjonsområdesidene: månedlige
    # beholdningstall per område, MÅLT 10 990 changelog-rader mot
    # trafikklysvedtakets 47. Den endrer ingenting for lokalitetssidene —
    # biomasse har 14 entity_id-er i changeloggen (1-13 og `uten_po`), og
    # ingen av dem er et lokalitetsnummer.
    assert "trafikklysvedtak" not in nettsted.MAALESERIER


def test_siden_sier_hvor_mange_maaleserierader_som_er_holdt_utenfor():
    """Et utvalg som ikke sier at det er et utvalg, lyver ved
    utelatelse."""
    assert "1284" in _side()


# ---- når kildene er uenige --------------------------------------------
#
# `akvakultur` oppgir hvilke tillatelser som ligger på lokaliteten;
# `eierskap` oppgir hvem som eier en tillatelse. MÅLT 19.09.2026: de er
# uenige om 84 tillatelsesnumre på 65 lokaliteter, 62 av dem der INGEN av
# tillatelsene finnes i eierskap.
#
# Uenigheten er vår egen: alle 84 finnes hos Fiskeridirektoratet med 200
# OK, og for TRETTØY (11517) er alle 14 AKTIVE. Det som mangler er
# EIEREN — 55 fordi kilden ikke oppgir organisasjonsnummer for
# privatpersoner, 29 fordi eieren ikke finnes i /entities. Se
# docs/REGEL-UENIGE-KILDER.md.


def test_uten_eier_er_det_akvakultur_oppgir_og_eierskap_ikke_kjenner():
    oppgitt = ["H-SO-0318", "H-SO-0341", "T-D-0009"]
    eierskap = {"T-D-0009": {"eier_navn": "SALMAR OPPDRETT AS"}}
    assert nettsted._uten_eier(oppgitt, eierskap) == ["H-SO-0318", "H-SO-0341"]


def test_raden_STÅR_med_eieren_merket_ukjent():
    """Regelen: en lokalitet der vi ikke vet hvem som eier tillatelsene
    sier DET. Den utelater ikke raden, og den viser ikke tom celle."""
    rader = nettsted._tillatelsesrader({}, ["H-SO-0318"])
    assert len(rader) == 1
    assert rader[0]["nr"] == "H-SO-0318"
    assert rader[0]["eier_navn"] == nettsted.EIER_UKJENT
    assert nettsted.EIER_UKJENT not in ("", None)


def test_ukjent_eier_merkes_med_ET_ANNET_FELT_enn_eier_navn():
    """Verdien er VÅR setning om fravær, ikke et navn fra kilden.

    Merket den som `eier_navn`, ville porten lett etter «ikke oppgitt av
    kilden» i hvitelista over navn og meldt den som `ukjent_navn` — et
    funn om vår egen forklaring."""
    import publiseringsvakt as vakt

    ukjent = nettsted._tillatelsesrader({}, ["H-SO-0318"])[0]
    assert ukjent["eier_felt"] == nettsted.EIER_UKJENT_FELT
    assert nettsted.EIER_UKJENT_FELT != "eier_navn"
    assert nettsted.EIER_UKJENT_FELT not in vakt.NAVNEFELT


def test_kjente_og_ukjente_staar_i_SAMME_tabell_sortert():
    """En egen tabell for de ukjente ville gjort fraværet til noe man kan
    overse."""
    kjent = {"T-D-0009": {"eier_navn": "SALMAR OPPDRETT AS",
                          "eier_orgnr": "928957489"}}
    rader = nettsted._tillatelsesrader(kjent, ["H-SO-0318", "Z-Z-0001"])
    assert [r["nr"] for r in rader] == ["H-SO-0318", "T-D-0009", "Z-Z-0001"]


def test_sida_SIER_at_eieren_mangler(monkeypatch):
    """Ende til ende i markupen: tallene, grunnen, og ingen tom tabell."""
    import publiseringsvakt as vakt

    html = _side(tillatelser=nettsted._tillatelsesrader(
                     {}, ["H-SO-0318", "H-SO-0329"]),
                 tillatelser_oppgitt=2, tillatelser_uten_eier=2)

    # Mellomrom normaliseres: captionteksten er FRI (se
    # docs/beslutninger/2026-09-19-markup-er-en-kontrakt.md), og en test
    # som låser linjeskiftene feller neste ombrekking uten grunn.
    flat = " ".join(html.split())
    assert "For 2 av 2 tillatelser vet vi ikke hvem eieren er" in flat
    assert "privatpersoner" in flat
    assert "H-SO-0318" in flat and "H-SO-0329" in flat

    # Merkingen: verdien står som `eier_ukjent`, ikke som et navn.
    merket = vakt.felt_verdier(html)
    assert (nettsted.EIER_UKJENT_FELT, nettsted.EIER_UKJENT) in merket
    assert not any(f == "eier_navn" for f, _v in merket)

    # OG den gamle merkingen må slippe cellen. `class="eier"` er det
    # `navn_i()` leser, og med den på plass meldte porten vår EGEN
    # forklaring som `ukjent_navn` — målt på 12 sider 19.09.2026 før
    # klassen ble gjort betinget. Klassen er fri, merkingen er ikke.
    assert nettsted.EIER_UKJENT not in vakt.navn_i(html)


def test_sida_sier_INGENTING_naar_kildene_er_enige():
    """1714 av 1779 lokaliteter er enige. De skal ikke bære en forklaring
    på et avvik som ikke finnes."""
    html = _side()
    assert "vet vi ikke hvem eieren er" not in html
    assert nettsted.EIER_UKJENT not in html


# ---- produksjonsområdesiden -------------------------------------------
#
# Trettten områder, fem fastsatte runder, og MÅLT 19 av 65 celler som
# ikke kan leses av forskriftsteksten. En slik celle SIER det.

def _po(**overstyr) -> str:
    po = {
        "nr": "4", "navn": "Nordhordland til Stadt", "status": "RØD",
        "akva_dato": "2026-09-14",
        "runder": [
            # `farge_klasse` er presentasjonskroken malen henger
            # fargeruta på, og den hentes fra `FARGE_KLASSE` framfor å
            # skrives av: en fikstur med sine egne strenger er en
            # fikstur som sier grønt om koden har byttet vokabular.
            # Den manglende fargen har INGEN klasse — det er den
            # tomme ruta, og den er stiplet, ikke fylt.
            {"aar": "2018", "farge": nettsted.FARGE_MANGLER,
             "farge_felt": nettsted.FARGE_MANGLER_FELT, "farge_klasse": "",
             "lesemaate": "", "lesemaate_tekst": "ingen bestemmelse å lese"},
            {"aar": "2020", "farge": "rød", "farge_felt": "farge",
             "farge_klasse": nettsted.FARGE_KLASSE["rod"],
             "lesemaate": "ordrett",
             "lesemaate_tekst": nettsted.LESEMAATE["ordrett"]},
            {"aar": "2022", "farge": "grønn", "farge_felt": "farge",
             "farge_klasse": nettsted.FARGE_KLASSE["gronn"],
             "lesemaate": "kapittelhjemmel",
             "lesemaate_tekst": nettsted.LESEMAATE["kapittelhjemmel"]},
        ],
        "lokaliteter": [{"loknr": "31397", "navn": "Oterneset",
                         "original": "OTERNESET",
                         "kommune": "HARSTAD", "kapasitet": "8000.0",
                         "kapasitet_enhet": "TN", "arter": "SALMON",
                         "status": "godkjent", "sist_endret": "2026-09-14",
                         "sok": "31397 oterneset harstad",
                         "selskap": {"navn": "SALMAR OPPDRETT AS",
                                     "orgnr": "928957489",
                                     "url": "/selskap/928957489/",
                                     "siden": "", "antall": 1, "flere": 0,
                                     "personform": False}}],
        "lokaliteter_antall": 1,
        "selskaper_antall": 1,
        "uten_kjent_eier": 0,
        "akva_hentet": "2026-09-14T04:00:00+00:00",
        "naa": {"farge": "gul", "klasse": nettsted.FARGE_KLASSE["gul"],
                "uenig": ""},
        "endringer": [{"dato": "2026-12-31", "gjelder": "lokaliteten",
                       "kilde": "trafikklysvedtak", "felt": "farge",
                       "fra": "rod", "til": "gul"}],
        "i_omraadet": [],
        "endringsuker": 12,
        # BIOMASSEN, flyttet hit fra lokalitetssiden (avvik 1).
        "biomasse": None,
        "biomasse_rader": [],
        "biomasse_maaneder": 0,
        "biomasse_utgitt": "",
        "maaleserie_rader": 941,
        "ubelagte_rader": 56,
        "ubelagte_kilder": ["ekspertgruppen"],
        "siter": {"url": "https://kystloggen.no/produksjonsomrade/4/",
                  "uke": "uke 38, 2026", "dato": "14. september 2026",
                  "aar": "2026", "sjekksum": "efe1c0884c4e39d20b7d775a363d"},
    }
    po.update(overstyr)
    po["endringer"] = _endringsrader(po["endringer"])
    # `runder` bærer forskriftsopplysningene fra 22.09.2026. De leses av
    # kilden (`sources/trafikklysvedtak.FORSKRIFTER`), ikke skrevet av
    # her: en fikstur med sine egne URL-er er en fikstur som sier grønt
    # om lenka i koden peker et annet sted.
    po["runder"] = [dict(r, forskrift=nettsted.forskrift_for_runde(r["aar"]))
                    for r in po["runder"]]
    for l_ in po["lokaliteter"]:
        if "kapasitet_enhet" in l_:
            l_["kapasitet"] = visningsord.maalt(l_.pop("kapasitet"),
                                                l_.pop("kapasitet_enhet"))
        l_["arter"] = visningsord.verdi("arter", l_.get("arter", ""))
    return nettsted._miljo().get_template("produksjonsomrade.html.j2").render(
        po=po,
        **_grunn("produksjonsomrade/4", main_klasse="fullbredde",
                 jsonld=nettsted.jsonld_po(po, nettsted.kildevilkaar()),
                 attribusjon=nettsted.attribusjon(nettsted.PO_KILDER)))


def test_celle_uten_farge_SIER_det():
    """19 av 65 celler kan ikke leses av forskriftsteksten. En tom celle
    ville latt leseren gjette at området ikke var med i ordningen."""
    html = _po()
    assert nettsted.FARGE_MANGLER in html
    # KORT celle, samme form som «rød»/«gul»/«grønn». Setningen som
    # forklarer hva fraværet betyr står i noten under tabellen — den
    # gjelder alle radene, og hadde den stått i hver celle ville én
    # celle satt bredden på hele kolonnen. MÅLT: den gjorde det.
    assert nettsted.FARGE_MANGLER == "ikke oppgitt"
    assert len(nettsted.FARGE_MANGLER) < 20, "cellen setter kolonnebredden"


def test_manglende_farge_merkes_med_ET_ANNET_FELT_enn_farge():
    """Samme konstruksjon som `eier_ukjent`: verdien er VÅR setning om
    fravær, ikke en farge fra forskriften. Blandes de to i markupen, kan
    ingen maskin skille «rød» fra «ikke oppgitt»."""
    import publiseringsvakt as vakt

    # PAR og ikke dict: `farge` står både i fargetabellen og som feltnavn
    # i endringstabellen, og en dict ville latt den ene skjule den andre.
    # Samme egenskap som `kapasitet` har på lokalitetssiden — se
    # docs/beslutninger/2026-09-19-markup-er-en-kontrakt.md.
    merket = vakt.felt_verdier(_po())
    assert nettsted.FARGE_MANGLER_FELT != "farge"
    assert (nettsted.FARGE_MANGLER_FELT, nettsted.FARGE_MANGLER) in merket
    assert ("farge", "rød") in merket and ("farge", "grønn") in merket


def test_lesemaaten_staar_paa_siden_og_forklares():
    """To grader av belegg. `ordrett` og `kapittelhjemmel` er ikke like
    sterke, og en side som viste dem likt ville påstått et belegg den
    ikke har."""
    html = _po()
    assert "ordrett" in html and "kapittelhjemmel" in html
    assert nettsted.LESEMAATE["kapittelhjemmel"] in html


def test_maaleserier_og_ubelagte_telles_paa_po_siden():
    """Begge utelatelsene er SAGT. Biomasse er 941 rader mot 1
    registerendring, og ekspertgruppen er UBELAGT — antallet står slik at
    utelatelsen ikke er stille."""
    html = " ".join(_po().split())
    # TALLET og KILDEN, ikke setningen rundt dem. Prøven het på en
    # ordrett formulering fram til 20.09.2026 og falt da noten ble
    # skrevet om — den målte prosaen, ikke at utelatelsen var sagt.
    assert "941" in html, "måleserieraden er ikke telt"
    assert "56" in html and "UBELAGT" in html, "utelatelsen er stille"
    assert "ekspertgruppen" in html, "kilden er ikke navngitt"


def test_po_siden_lenker_til_hver_lokalitet():
    assert '<a href="/lokalitet/31397/">31397</a>' in _po()


def test_po_siden_sier_at_inndelingen_er_dagens():
    """Området er en regulatorisk inndeling som kan tas om igjen, ikke
    en naturgitt grense. Siden sier hva inndelingen var PÅ EN DATO, og
    at et område som endrer grenser eller nummer er et annet område."""
    flat = " ".join(_po().split())
    assert "regulatorisk inndeling, ikke en naturgitt grense" in flat
    assert "Siden sier hva inndelingen var på datoen over" in flat
    assert "2026-09-14" in flat
    assert "2026-09-14" in flat
    assert "regulatorisk inndeling" in flat
    assert "ikke en naturgitt grense" in flat


def test_po_siden_bruker_ikke_UBELAGT_kilde_i_bunnteksten():
    """`ekspertgruppen` er UBELAGT. Sto den i PO_KILDER, ville
    `attribusjon()` kastet — og gjorde den ikke det, ville siden påstått
    et vilkår ingen har gått god for."""
    assert "ekspertgruppen" not in nettsted.PO_KILDER
    assert set(nettsted.PO_KILDER).isdisjoint(
        nettsted.ubelagte(nettsted.kildevilkaar()))


def test_ubelagte_utledes_av_kilden_ikke_listet():
    """En liste her ville vært et andre sted sannheten kan bli gammel."""
    assert nettsted.ubelagte(nettsted.kildevilkaar()) == {"ekspertgruppen"}
    assert nettsted.ubelagte({"a": None, "b": ("x",)}) == {"a"}


# ---- selskapssiden ----------------------------------------------------
#
# Én side per organisasjonsnummer som eier minst én tillatelse. MÅLT
# 20.09.2026: 482 eiere, 360 med registerdata og 122 uten.

def _selskap(**overstyr) -> str:
    sel = {
        "orgnr": "912345678", "navn": "TESTLAKS AS",
        "har_registerdata": True,
        "register": [("navn", "TESTLAKS AS"), ("organisasjonsform", "AS")],
        "uten_registerdata_tekst": nettsted.UTEN_REGISTERDATA,
        "enhet_dato": "2026-09-14", "eierskap_dato": "2026-09-14",
        "akva_dato": "2026-09-14",
        "tillatelser": nettsted._tillatelsesrader(
            {"N-T-0001": {"eier_navn": "TESTLAKS AS",
                          "eier_orgnr": "912345678",
                          "tillatelse_type": "KOMM-MATF",
                          "kapasitet": "780.0", "kapasitet_enhet": "TN",
                          "tildelt_tid": "2004-09-29T00:00:00Z",
                          "tildelt_navn": "TESTLAKS AS"}}, []),
        "tillatelser_antall": 1,
        "lokaliteter": [{"loknr": "10001", "navn": "Testholmen",
                         "original": "TESTHOLMEN",
                         "kommune": "BODØ", "po_kode": "8",
                         "po_navn": "Helgeland til Bodø",
                         "status": "gul",
                         "status_klasse": nettsted.FARGE_KLASSE["gul"],
                         "kapasitet": "780 tonn", "siden": "2018-03-13",
                         "tillatelser": ["N-T-0001"]}],
        "lokaliteter_antall": 1,
        "overforinger": [{"dato": "2018-03-13", "tillatelse": "N-T-0001",
                          "rekkefolge": "1"}],
        "enhetsregisteret_url":
            "https://virksomhet.brreg.no/nb/oppslag/enheter/912345678",
        "samlet_kapasitet": "780 tonn", "kapasitetsenheter": 1,
        "i_arkivet_siden": "2018-03-13",
        # «Gikk ut» er UTLEDET — registeret journalfører bare ankomster.
        # Se `bygg_selskap()`.
        "eierskapslinje": [
            {"dato": "2018-03-13", "tillatelse": "N-T-0001", "navn": "",
             "navn_felt": "", "retning": "inn", "slag": "Kom til",
             "hva": "N-T-0001 overført hit",
             "presisjon": "journalført senest denne datoen"}],
        "kom_til": 1, "gikk_ut": 0,
        "siter": {"url": "https://kystloggen.no/selskap/912345678/",
                  "uke": "uke 38, 2026", "dato": "14. september 2026",
                  "aar": "2026", "sjekksum": "efe1c0884c4e39d20b7d775a363d"},
    }
    sel.update(overstyr)
    jsonld_raa = dict(sel)          # JSON-LD leser KILDENS verdier
    sel["register"] = _visning(sel["register"])
    for t_ in sel["tillatelser"]:
        if "kapasitet_enhet" in t_:
            t_["kapasitet"] = visningsord.maalt(t_.pop("kapasitet"),
                                                t_.pop("kapasitet_enhet"))
        t_.setdefault("siden", "2018-03-13")
    return nettsted._miljo().get_template("selskap.html.j2").render(
        sel=sel,
        **_grunn("selskap/928957489", main_klasse="fullbredde",
                 jsonld=nettsted.jsonld_selskap(jsonld_raa,
                                                nettsted.kildevilkaar()),
                 attribusjon=nettsted.attribusjon(nettsted.SELSKAPSKILDER)))


def test_selskap_uten_registerdata_SIER_det():
    """121 av 481 (målt 22.09.2026). En tom registertabell ville latt
    leseren tro at selskapet ikke finnes, når det er UTVALGET vårt som
    ikke når det."""
    html = " ".join(_selskap(har_registerdata=False, register=[]).split())
    assert "Vi har ingen registerdata for dette selskapet" in html
    assert nettsted.UTEN_REGISTERDATA in html
    assert "121 av 481" in html


def test_manglende_registerdata_merkes_som_eget_felt():
    import publiseringsvakt as vakt

    merket = vakt.felt_verdier(_selskap(har_registerdata=False, register=[]))
    assert ("registerdata_mangler", nettsted.UTEN_REGISTERDATA) in merket


def test_selskap_med_registerdata_sier_ingenting_om_fravaer():
    html = " ".join(_selskap().split())
    assert "Vi har ingen registerdata" not in html


def test_selskapssiden_bruker_SAMME_radbygger_som_lokalitetssiden():
    """`_tillatelsesrader()` er den ene veien en tillatelsesrad blir til.
    To veier som skal si det samme om hvem som eier hva, er formen F6 og
    F7 hadde — og her bærer raden nettopp det."""
    rader = nettsted._tillatelsesrader(
        {"N-T-0001": {"eier_navn": "TESTLAKS AS"}}, [])
    assert rader[0]["eier_felt"] == "eier_navn"
    assert "N-T-0001" in _selskap()


def test_en_tillatelse_uten_eier_kan_ikke_havne_paa_en_selskapsside():
    """Invarianten uenighetsregelen hviler på: en lokalitet der eieren
    ikke er oppgitt skal ikke dukke opp under et selskap som ikke eier
    den.

    Den følger av konstruksjonen — sidens tillatelser er de som har
    DETTE orgnummeret i `eier_orgnr`, og en tillatelse uten eier har
    ingen — men en invariant uten test er en hensikt."""
    from types import SimpleNamespace

    felles = SimpleNamespace(
        tillatelser_per_eier={"912345678": ["N-T-0001"]},
        eierskap={"N-T-0001": {"eier_navn": "TESTLAKS AS",
                               "eier_orgnr": "912345678",
                               "lokaliteter": "10001"},
                  # Uten eier: står i eierskap-indeksen for INGEN.
                  "H-SO-0318": {"lokaliteter": "11517"}},
        enhet={}, enhet_dato="2026-09-14", eierskap_dato="2026-09-14",
        akva_dato="2026-09-14",
        akva={"10001": {"navn": "TESTHOLMEN"}, "11517": {"navn": "TRETTØY"}},
        overforinger_per_tillatelse={})

    sel = nettsted.bygg_selskap("912345678", felles)
    numre = [t["nr"] for t in sel["tillatelser"]]
    assert numre == ["N-T-0001"]
    assert "H-SO-0318" not in numre
    assert [l["loknr"] for l in sel["lokaliteter"]] == ["10001"]
    assert "11517" not in [l["loknr"] for l in sel["lokaliteter"]]


def test_selskapssiden_lenker_til_lokalitet_og_produksjonsomrade():
    html = _selskap()
    assert '<a href="/lokalitet/10001/">10001</a>' in html
    assert '/produksjonsomrade/8/' in html


def test_selskapssiden_sier_at_den_ikke_viser_konsern():
    """Rolledata er persondata og hentes ikke. At det er et VALG og ikke
    en mangel, skal stå på siden."""
    assert "Ingenting om konsern" in _selskap()


def test_en_eier_kilden_kaller_person_faar_ingen_side():
    """MÅLT 20.09.2026: porten fant tre funn på `/selskap/954744469/` —
    partrederiet som eier H-FJ-0018. Lesedøra er blind for det, fordi
    snapshotet bare bærer pub-aquas eget ord (`eier_type`) og ingen
    oversatt `organisasjonsform`. Se sektornotatets punkt 7.2.

    På en lokalitetsside er følgen én rad. På en selskapsside er følgen
    en hel side om navngitte mennesker, og et URL-rom er en liste over
    hvem som finnes selv om siden er tom."""
    from types import SimpleNamespace

    felles = SimpleNamespace(
        tillatelser_per_eier={"954744469": ["H-FJ-0018"],
                              "912345678": ["N-T-0001"]},
        eierskap={"H-FJ-0018": {"eier_type": "JointlyOwnedShippingCompany"},
                  "N-T-0001": {"eier_type": "LimitedLiabilityCompany"}})

    assert nettsted.personeier("954744469", felles) is True
    assert nettsted.personeier("912345678", felles) is False


def test_personeier_spor_KILDEN_og_ikke_en_egen_liste():
    """Oversettelsen mellom pub-aquas ord og Brregs koder bor i
    `sources/eierskap.FORM_KART`. En kopi her ville vært to lister som
    skal si det samme — formen F6 og F7 hadde."""
    import inspect

    from sources.eierskap import er_person

    assert er_person("JointlyOwnedShippingCompany") is True
    kilde = inspect.getsource(nettsted.personeier)
    assert "from sources.eierskap import er_person" in kilde
    assert "FORM_KART" not in kilde.split('"""')[-1]


# ---- forsiden og kartet -----------------------------------------------
#
# Statisk SVG, generert ved bygging. MÅLT 20.09.2026: 1782 punkter,
# 82 kB, 0 lokaliteter uten koordinater.

def _akva(**lok):
    return {k: v for k, v in lok.items()}


def test_kartet_projiserer_med_breddekorreksjon():
    """Uten `cos(lat)` blir Finnmark dobbelt så bredt som det er.
    Korreksjonen tas på MIDTBREDDEN: én per punkt ville krummet kysten,
    altså vært en annen projeksjon enn den siden sier den bruker."""
    akva = {
        "1": {"breddegrad": "58.0", "lengdegrad": "5.0"},
        "2": {"breddegrad": "71.0", "lengdegrad": "5.0"},
        "3": {"breddegrad": "58.0", "lengdegrad": "31.0"},
    }
    punkter, uten, hoyde, _g = nettsted.kartpunkter(akva)
    assert uten == []
    px = {p["loknr"]: p for p in punkter}
    # Samme lengdegrad -> samme x, uansett breddegrad.
    assert px["1"]["x"] == px["2"]["x"]
    # Nordligst -> minst y (y vokser nedover i SVG).
    assert px["2"]["y"] < px["1"]["y"]
    # Bredden er klemt sammen: 26 lengdegrader gir mindre enn 26 * skala.
    assert px["3"]["x"] - px["1"]["x"] < nettsted.KART_BREDDE
    assert hoyde > 0


def test_lokalitet_uten_koordinater_utelates_men_forsvinner_ikke():
    """Et punkt som mangler skal ikke bare forsvinne.
    Uenighetsregelen i et annet format."""
    akva = {
        "10001": {"breddegrad": "60.0", "lengdegrad": "5.0"},
        "10002": {"breddegrad": "", "lengdegrad": "5.0"},
        "10003": {"lengdegrad": "5.0"},
    }
    punkter, uten, _h, _g = nettsted.kartpunkter(akva)
    assert [p["loknr"] for p in punkter] == ["10001"]
    assert uten == ["10002", "10003"]


def _forside(**overstyr) -> str:
    """Forsiden rendret av en fikstur.

    NØKLENE MÅ FØLGE `bygg_forside`: malen kjører med `StrictUndefined`,
    så en nøkkel som mangler her feller prøvene framfor å rendre et
    hull. Det er meningen — da er det denne fila som må rettes når
    forsiden får en ny verdi, og ikke utputtet som blir stille feil.
    """
    omraade = {
        "nr": "4", "navn": "Nordhordland til Stadt", "lokaliteter": 137,
        "farge": "gul", "farge_klasse": "lys-gul", "uenig": "",
        "stripe": [{"aar": "2024", "farge": "rød", "klasse": "lys-rod",
                    "tittel": "2024: rød"},
                   {"aar": "2026", "farge": "gul", "klasse": "lys-gul",
                    "tittel": "2026: gul"}],
        "historie": "rød → gul",
    }
    hendelse = {
        "dato": "2026-09-21", "uke": "2026-39", "type": "trafikklys",
        "type_navn": "Trafikklys", "kilde": "akvakultur",
        "entity_id": "31397", "felt": "prodomraade_status",
        "etikett": "Trafikklysfarge", "fra": "rød", "til": "gul",
        "fra_klasse": "lys-rod", "til_klasse": "lys-gul", "er_farge": True,
        "gjelder": "Oterneset", "gjelder_url": "/lokalitet/31397/",
        "gjelder_felt": "entity_name", "identitet": "31397",
        "gjelder_slag": "lokalitet", "lokalitet": "Oterneset",
        "lokalitet_url": "/lokalitet/31397/", "kommune": "HARSTAD",
        "po": "4", "po_navn": "Nordhordland til Stadt",
        "fra_felt": "prodomraade_status", "til_felt": "prodomraade_status",
        "anonym": False,
    }
    uke = {
        "slug": "2026-39", "aar": "2026", "ukenr": "39",
        "vist": "uke 39, 2026", "spenn": "21.–27. september 2026",
        "datoer": ["2026-09-21"], "forste_dato": "2026-09-21",
        "siste_dato": "2026-09-21", "hendelser": [hendelse], "antall": 812,
        "typer": [dict(k, antall=(362 if k["id"] == "trafikklys" else 0))
                  for k in nettsted.ENDRINGSTYPER],
        "utenfor_uka": 32979,
    }
    f = {
        "lokaliteter": 1782, "produksjonsomraader": 13, "selskaper": 481,
        "tillatelser": 2945, "luke_uker": 764,
        "lus_fra": "2012-01-02", "lus_til": "2026-08-17",
        "akva_dato": "2026-09-21", "akva_hentet": "2026-09-21T04:00:00+00:00",
        "eierskap_dato": "2026-09-21",

        "uke": uke,
        "sammendrag": ["812 endringer observert i uke 39, 2026."],
        "forskriftslinje": None,
        "rader": [hendelse],
        "flere_rader": 804,
        "forrige_uke": "2026-38", "forrige_uke_vist": "uke 38, 2026",
        "uker_totalt": 5,

        "snapshots": 6, "forste_snapshot": "2026-08-17",
        "siste_snapshot": "2026-09-21",
        "sjekksum": "efe1c0884c4e39d20b7d775a363dfe1fc55b21ce0bcda9a9c2e2",

        "omraader": [omraade],
        "kart": {"bredde": 760, "hoyde": 870.4,
                 "omraader": [{"nr": "4", "navn": "Nordhordland til Stadt",
                               "farge_klasse": "lys-gul", "farge": "gul",
                               "antall": 137, "baner": ["M10 10L20 20Z"]}],
                 "mangler_geometri": [],
                 "land": ["M0 0L5 5L5 0Z"],
                 "gitter": {"bredde": [{"y": 200.0, "grad": 65,
                                        "etikett": "65°N",
                                        "etikett_x": 754, "etikett_y": 195.0}],
                            "lengde": [{"x": 300.0, "grad": 10,
                                        "etikett": "10°Ø",
                                        "etikett_x": 306.0,
                                        "etikett_anker": "start"}],
                            "etikett_y_bunn": 862.4, "etiketter": True}},
        "i_omraade": 969,
        "runder": ["2018", "2020", "2022", "2024", "2026"],

        "uten_koordinater_antall": 0,
    }
    f.update(overstyr)
    return nettsted._miljo().get_template("forside.html.j2").render(
        f=f,
        **_grunn(jsonld=nettsted.jsonld_forside(f, nettsted.kildevilkaar()),
                 attribusjon=nettsted.attribusjon(nettsted.FORSIDEKILDER),
                 main_klasse="fullbredde"))


def test_forsiden_svarer_paa_de_tre_tingene():
    """Hva er dette, hva har skjedd, kan jeg stole på det."""
    html = " ".join(_forside().split())
    assert "Registrene viser nå. Vi tar vare på før." in html
    assert "Et uavhengig, åpent arkiv over offentlige data" in html
    assert "Heine Valø Nordbøe" in html
    assert "github.com/heinenordboe-cloud/havbruk-radar" in html
    for lenke in ("/lokalitet/", "/produksjonsomrade/", "/selskap/",
                  "/om/", "/endringer/"):
        assert f'href="{lenke}"' in html


def test_forsiden_leder_med_uka_og_ikke_med_seg_selv():
    """Bevegelsen er produktet. «Denne uka» skal stå FØR alt annet
    innhold, over bretten på 1440x900."""
    html = _forside()
    assert html.index('id="uka"') < html.index('id="kysten"')
    assert html.index('id="uka"') < html.index('arkivlinje')
    flat = " ".join(html.split())
    assert "812 endringer observert i uke 39, 2026." in flat
    assert "Alle 812 endringene i uke 39, 2026" in flat


def test_alle_endringstyper_vises_ogsaa_de_med_null():
    """Et tall man bare ser når det er noe der, er et tall ingen
    kjenner normalverdien til. Overleveringens krav: typer med 0 er
    dempet, men vises alltid."""
    html = _forside()
    for slag in nettsted.ENDRINGSTYPER:
        assert f'/endringer/2026-39/{slag["id"]}/' in html, slag["id"]
    # De dempede er merket som dempet, ikke utelatt.
    assert "typemerke--tom" in html


def test_typelenkene_er_stier_og_ikke_sporrestrenger():
    """En spørrestreng gjør identiteten til et argument, og en statisk
    side har ingenting som leser den. Se 2026-09-16-url-struktur.md."""
    html = _forside()
    assert "?type=" not in html
    assert "?uke=" not in html
    assert "?q=" not in html


def test_kartet_er_statisk_uten_tjeneste_og_uten_js():
    """Kartet skal virke om ti år uten at noen fornyer en nøkkel."""
    html = _forside()
    assert "<svg" in html and "viewBox" in html
    # JSON-LD-en og det ene skriptet — se
    # `test_javascript_er_en_forbedring_og_ikke_en_avhengighet`.
    # KARTET tegnes ikke av noen av dem: hver koordinat står i `d`.
    assert html.count("<script") == 2
    assert 'type="application/ld+json"' in html
    assert 'src="/kystloggen.js" defer' in html
    for forbudt in ("tile", "mapbox", "openstreetmap", "leaflet",
                    "googleapis", "unpkg", "http://", "fetch("):
        assert forbudt not in html.lower(), forbudt


def test_herobildet_hostes_av_oss_og_aldri_av_unsplash():
    """En `images.unsplash.com`-URL i markupen ville fortalt dem hvem
    som leser siden, og gjort forsidens hovedbilde avhengig av at en
    tredjepart svarer."""
    html = _forside()
    assert "unsplash" not in html.lower()
    for bredde in (800, 1600, 2400):
        assert f"/bilde/hero-{bredde}.jpg" in html


def test_kartet_har_tittel_og_beskrivelse_for_skjermleser():
    html = _forside()
    assert 'role="img"' in html
    assert '<title id="kysttittel">' in html
    assert '<desc id="kystbeskrivelse">' in html


def test_omradene_er_lenker_i_kartet_ogsaa_uten_js():
    """Uten JavaScript er kartet et bilde. `<a>` inne i SVG-en gjør det
    til navigasjon uansett."""
    html = _forside()
    assert '<a href="/produksjonsomrade/4/"' in html
    assert 'aria-label="Produksjonsområde 4 Nordhordland til Stadt, gul' in html


def test_antallet_uten_koordinater_staar_ogsaa_naar_det_er_null():
    """Et tall man bare ser når det er galt, er et tall ingen kjenner
    normalverdien til."""
    flat = " ".join(_forside().split())
    assert "0 av 1782 lokaliteter mangler koordinater" in flat
    assert 'href="/lokalitet/#akvakultur-uten-koordinater"' in flat


def test_arkivtallet_skjuler_ikke_at_det_er_lite():
    """Seks øyeblikksbilder er seks uker, og et arkiv som later som det
    er eldre enn det er, er verdiløst den dagen noen sjekker."""
    flat = " ".join(_forside().split())
    assert "6</strong> ukentlige øyeblikksbilder siden" in flat
    assert "17. august 2026" in flat
    assert "sjekksum" in flat


def test_ukesbrevskjemaet_er_ikke_bygget_og_star_derfor_ikke_der():
    """Et skjema som poster til en adresse ingen lytter på, er verre
    enn ingen: det ser ut som en vei inn."""
    html = _forside()
    assert "/ukesbrev/" not in html
    assert 'method="post"' not in html.lower()
    # Feedene er det som FAKTISK finnes, og de står.
    assert "/endringer/feed.xml" in html


# ---- indekssidene -----------------------------------------------------
#
# Flate lister, ingen paginering: dette er sidene en crawler og en
# språkmodell følger for å finne alt annet, og en paginert liste er en
# liste der side 14 aldri blir lest.

def test_selskapsindeksen_utelater_personeier_MEN_sier_det():
    """Utelatelsen er aldri stille. Se `personeier()`."""
    from types import SimpleNamespace

    felles = SimpleNamespace(
        tillatelser_per_eier={"954744469": ["H-FJ-0018"],
                              "912345678": ["N-T-0001"]},
        eierskap={"H-FJ-0018": {"eier_type": "JointlyOwnedShippingCompany",
                                "eier_navn": "NOE ANS", "lokaliteter": "11593"},
                  "N-T-0001": {"eier_type": "LimitedLiabilityCompany",
                               "eier_navn": "TESTLAKS AS",
                               "lokaliteter": "10001"}},
        enhet={"912345678": {}}, eierskap_dato="2026-09-14")

    d = nettsted.bygg_selskapsindeks(felles)
    assert [r["orgnr"] for r in d["rader"]] == ["912345678"]
    assert d["personeiere"] == 1

    html = nettsted._miljo().get_template("indeks-selskap.html.j2").render(
        d=d, **_grunn("lokalitet"))
    flat = " ".join(html.split())
    assert "1 eier(e) står ikke i lista og har ingen side" in flat
    assert "personregister" in flat
    assert "954744469" not in html


def test_indeksene_er_flate_uten_paginering():
    """En paginert liste er en liste der de siste sidene ikke blir
    lest."""
    from types import SimpleNamespace

    felles = SimpleNamespace(
        akva={str(10000 + i): {"navn": f"L{i}", "kommune": "K",
                               "fylke": "F", "prodomraade_kode": "",
                               "arter": "SALMON",
                               "breddegrad": f"{60 + i / 100:.2f}",
                               "lengdegrad": "5.0"} for i in range(50)},
        akva_dato="2026-09-14")
    d = nettsted.bygg_lokalitetsindeks(felles)
    assert d["antall"] == 50
    assert d["uten_po"] == 50

    html = nettsted._miljo().get_template("indeks-lokalitet.html.j2").render(
        d=d, **_grunn("lokalitet"))
    # RADLENKENE, ikke alle lenker til /lokalitet/. Fra 20.09.2026 har
    # hver side en topplinje som også lenker dit, og en telling av
    # prefikset ga 51. Mønsteret spør om det prøven faktisk vil vite:
    # én lenke per lokalitetsnummer.
    assert len(re.findall(r'<a href="/lokalitet/\d+/"', html)) == 50
    assert d["uten_koordinater_antall"] == 0


def test_lokaliteter_uten_koordinater_star_paa_indeksen():
    """Lista lå på forsiden ved siden av punktkartet den forklarte.
    Kartet er byttet ut med områdekartet, og et punkt som mangler skal
    fortsatt ikke bare forsvinne — se docs/REGEL-UENIGE-KILDER.md.

    ANKERET ER DET SAMME som før flyttingen. Et anker er en URL, og den
    flytter ikke på seg fordi siden gjorde det."""
    from types import SimpleNamespace

    felles = SimpleNamespace(
        akva={"10001": {"navn": "MED", "kommune": "K", "fylke": "F",
                        "prodomraade_kode": "", "arter": "SALMON",
                        "breddegrad": "60.0", "lengdegrad": "5.0"},
              "10002": {"navn": "UTEN", "kommune": "K", "fylke": "F",
                        "prodomraade_kode": "", "arter": "SALMON",
                        "breddegrad": "", "lengdegrad": "5.0"}},
        akva_dato="2026-09-14")
    d = nettsted.bygg_lokalitetsindeks(felles)
    assert d["uten_koordinater_antall"] == 1
    assert [r["loknr"] for r in d["uten_koordinater"]] == ["10002"]

    html = nettsted._miljo().get_template("indeks-lokalitet.html.j2").render(
        d=d, **_grunn("lokalitet"))
    assert 'id="akvakultur-uten-koordinater"' in html
    assert "slik at et punkt som mangler ikke bare forsvinner" in \
        " ".join(html.split())
    # Prøven ser etter pagineringsKONTROLLER, ikke etter ordet: sida
    # forklarer selv at den IKKE er paginert, og en prøve på ordet felte
    # sin egen begrunnelse.
    for kontroll in ('rel="next"', 'rel="prev"', "?side=", "?page=",
                     "&side=", "&page="):
        assert kontroll not in html.lower(), kontroll


# ---- om-siden ---------------------------------------------------------
#
# Den eneste siden som skrives for et menneske som lurer på om det kan
# stole på dette. Den svarer med tall og datoer, ikke med forsikringer.

def _om(**overstyr) -> str:
    om = {
        "lokaliteter": 1782, "med_eier": 1717, "dekning": 96.35,
        "uten_eier": 65, "uten_eier_med_tillatelse": 62,
        "uten_tillatelse_noe_sted": 3,
        "kilder": [
            {"navn": "akvakultur", "lisens": "NLOD",
             "hjemmel": "fiskeridir.no", "lest": "25.08.2026",
             "attribusjon": ["Kilde: Fiskeridirektoratet"],
             "ubelagt": False, "publiseres": True},
            {"navn": "ekspertgruppen", "lisens": "UBELAGT",
             "hjemmel": "ingen funnet", "lest": "14.09.2026 (søkt)",
             "attribusjon": [], "ubelagt": True, "publiseres": False},
        ],
        "ubelagte": ["ekspertgruppen"],
        "akva_dato": "2026-09-14", "eierskap_dato": "2026-09-14",
        "enhet_dato": "2026-09-14", "lusetall_uker": 764,
        "lus_fra": "2012-01-02", "lus_til": "2026-08-17",
        "kontakt": "", "repo": "https://github.com/heinenordboe-cloud/havbruk-radar",
        "forfatter": "Heine Valø Nordbøe", "bygget": "2026-09-20",
    }
    om.update(overstyr)
    return nettsted._miljo().get_template("om.html.j2").render(
        om=om, laan=nettsted.VAART_LAAN,
        **_grunn("om", bygget=om["bygget"],
                 attribusjon=nettsted.attribusjon(nettsted.OM_KILDER)))


def test_om_siden_oppgir_dekning_og_hvem_som_er_utelatt():
    flat = " ".join(_om().split())
    assert "1717 av 1782 lokaliteter (96.35 %)" in flat
    assert "sektor 8200" in flat and "2300" in flat
    assert "personregister" in flat
    # Skjevheten skal stå, ikke bare tallet.
    assert "små, personeide anlegg" in flat


def test_om_siden_merker_UBELAGT_kilde_som_ikke_vist():
    html = _om()
    flat = " ".join(html.split())
    assert "UBELAGT — ingen setning å gjengi" in flat
    assert "udokumentert lisens er UBELAGT, ikke antatt greit" in flat
    # Og den står i tabellen med «nei» i «vises her».
    assert "ekspertgruppen" in html


def test_om_siden_har_ferdig_formatert_sitering():
    flat = " ".join(_om().split())
    assert "Heine Valø Nordbøe (2026)" in flat
    assert "Kystloggen: sammenstilte registerdata om norsk akvakultur" in flat
    assert "Bygget 2026-09-20" in flat
    # Kildenes egen attribusjon er ikke valgfri, og det skal stå.
    assert "må kildenes egen attribusjon følge med" in flat


def test_kontaktadressen_er_ikke_hardkodet():
    """Samme valg som `_http.brukeragent()`: adressen havner i hver
    forespørsel til fire etater, og hvilken adresse som tåler det er
    ikke et kodevalg."""
    uten = " ".join(_om(kontakt="").split())
    assert "Kontakt går via GitHub" in uten
    assert "HAVBRUK_KONTAKT" in uten
    assert "mailto:" not in uten

    med = _om(kontakt="noen@eksempel.no")
    assert 'mailto:noen@eksempel.no' in med


def test_om_siden_sier_hva_som_bevisst_ikke_hentes():
    flat = " ".join(_om().split())
    assert "Ingen roller" in flat
    assert "konsernstruktur" in flat


# ---- maskinfilene -----------------------------------------------------
#
# sitemap.xml, robots.txt, llms.txt. Domenet er ikke avgjort, og ingen av
# dem finner på ett — se docs/beslutninger/2026-09-16-url-struktur.md.

@pytest.fixture
def smaafelles():
    from types import SimpleNamespace
    return SimpleNamespace(
        akva={"10001": {"navn": "A", "tillatelser": "N-T-0001",
                        "breddegrad": "60.0", "lengdegrad": "5.0"}},
        po_navn={"8": "Helgeland til Bodø"},
        lokaliteter_per_po={"8": ["10001"]},
        tillatelser_per_eier={"912345678": ["N-T-0001"],
                              "954744469": ["H-FJ-0018"]},
        eierskap={"N-T-0001": {"eier_type": "LimitedLiabilityCompany",
                               "eier_navn": "TESTLAKS AS",
                               "lokaliteter": "10001"},
                  "H-FJ-0018": {"eier_type": "JointlyOwnedShippingCompany",
                                "lokaliteter": "11593"}},
        tillatelser_per_lokalitet={"10001": {"N-T-0001"}},
        enhet={}, enhet_dato="2026-09-14", eierskap_dato="2026-09-14",
        akva_dato="2026-09-14", lusetall_snapshots=["2012-01-02", "2026-08-17"],
        vilkaar=nettsted.kildevilkaar())


def test_sitemap_bruker_nettstedets_eget_domene(tmp_path, smaafelles,
                                                monkeypatch):
    """Domenet er avgjort 21.09.2026. En usatt variabel betyr nå
    «bygg for kystloggen.no», ikke «vi vet ikke hvor dette skal
    ligge»."""
    monkeypatch.delenv("HAVBRUK_BASEURL", raising=False)
    tekst = nettsted.skriv_sitemap(tmp_path, smaafelles).read_text("utf-8")

    assert "<loc>https://kystloggen.no/lokalitet/10001/</loc>" in tekst
    assert "RELATIVE" not in tekst


def test_tom_baseurl_er_noe_annet_enn_usatt(tmp_path, smaafelles,
                                            monkeypatch):
    """Skillet er med vilje. «Jeg vet ikke hvor denne kopien skal
    ligge» er en tilstand som fortsatt finnes — en forhåndsvisning
    skal ikke fortelle en crawler at den er originalen."""
    monkeypatch.setenv("HAVBRUK_BASEURL", "")
    tekst = nettsted.skriv_sitemap(tmp_path, smaafelles).read_text("utf-8")

    assert "<loc>/lokalitet/10001/</loc>" in tekst
    assert "RELATIVE" in tekst
    assert "kystloggen.no" not in tekst


def test_sitemap_med_domene_er_absolutt(tmp_path, smaafelles, monkeypatch):
    monkeypatch.setenv("HAVBRUK_BASEURL", "https://eksempel.no/")
    tekst = nettsted.skriv_sitemap(tmp_path, smaafelles).read_text("utf-8")

    assert "<loc>https://eksempel.no/lokalitet/10001/</loc>" in tekst
    assert "HAVBRUK_BASEURL er ikke satt" not in tekst


def test_sitemap_utelater_personeier(tmp_path, smaafelles, monkeypatch):
    """Et URL-rom er en liste over hvem som finnes. Eieren kilden kaller
    person skal ikke stå i den heller."""
    monkeypatch.setenv("HAVBRUK_BASEURL", "")
    tekst = nettsted.skriv_sitemap(tmp_path, smaafelles).read_text("utf-8")

    assert "/selskap/912345678/" in tekst
    assert "954744469" not in tekst


def test_llms_peker_paa_indeksene_ikke_paa_hver_side(tmp_path, smaafelles,
                                                     monkeypatch):
    """En fil med 1782 lenker ville vært den samme lista som
    sitemap.xml, bare dårligere."""
    monkeypatch.setenv("HAVBRUK_BASEURL", "")
    tekst = nettsted.skriv_llms(tmp_path, smaafelles).read_text("utf-8")

    for indeks in ("/lokalitet/", "/produksjonsomrade/", "/selskap/", "/om/"):
        assert f"]({indeks})" in tekst
    assert "/lokalitet/10001/" not in tekst
    assert tekst.startswith("# Kystloggen")
    assert "\n> " in tekst          # sammendraget som blockquote
    assert "Heine Valø Nordbøe" in tekst


def test_robots_aapner_alt_og_peker_paa_sitemapet(tmp_path, monkeypatch):
    monkeypatch.delenv("HAVBRUK_BASEURL", raising=False)
    tekst = nettsted.skriv_robots(tmp_path).read_text("utf-8")
    assert "Allow: /" in tekst
    assert "Disallow" not in tekst
    assert "Sitemap: https://kystloggen.no/sitemap.xml" in tekst

    # Tom streng: kopien vet ikke hvor den ligger, og sier det.
    monkeypatch.setenv("HAVBRUK_BASEURL", "")
    tekst = nettsted.skriv_robots(tmp_path).read_text("utf-8")
    assert tekst.count("Sitemap:") == 1      # den er kommentert ut
    assert "# Sitemap:" in tekst

    monkeypatch.setenv("HAVBRUK_BASEURL", "https://eksempel.no")
    tekst = nettsted.skriv_robots(tmp_path).read_text("utf-8")
    assert "Sitemap: https://eksempel.no/sitemap.xml" in tekst


# ---- fontene ----------------------------------------------------------
#
# Stilarket viser til tre woff2-filer. Kommer en av dem ikke ut, er
# `@font-face` en død lenke og skriften faller til en reserve — en feil
# som ikke gir noen feilmelding og som ingen ser før de ser på siden.
# Prøvene under er de tre måtene den kan oppstå på.

def test_fontene_og_lisensene_kopieres_ut(tmp_path):
    skrevet = nettsted.skriv_fonter(tmp_path)
    navn = {s.name for s in skrevet}
    assert navn == {"newsreader.woff2", "newsreader-OFL.txt",
                    "ibmplexsans.woff2", "ibmplexmono.woff2",
                    "ibmplex-OFL.txt"}
    for font in ("newsreader.woff2", "ibmplexsans.woff2", "ibmplexmono.woff2"):
        assert (tmp_path / font).stat().st_size > 10_000, font
    # OFL 1.1 krever at lisensteksten følger fonten. Den skal være
    # lisensen, ikke en lenke til den. Begge Plex-familiene ligger under
    # den samme fila — se docs/design/IBM-PLEX.md.
    for lisensfil in ("newsreader-OFL.txt", "ibmplex-OFL.txt"):
        lisens = (tmp_path / lisensfil).read_text("utf-8")
        assert "SIL OPEN FONT LICENSE Version 1.1" in lisens, lisensfil


def test_manglende_font_stopper_byggingen(tmp_path, monkeypatch):
    """Stille fallback er verre enn et kast. En side som rendrer i
    reservefonten ser ut som et designvalg."""
    monkeypatch.setattr(nettsted, "MALER", tmp_path / "tom")
    with pytest.raises(FileNotFoundError):
        nettsted.skriv_fonter(tmp_path / "ut")


def test_stilarket_viser_til_en_fil_som_faktisk_sendes_ut():
    """Driftvakten. Byttes fonten i `@font-face` uten at `FONTFILER`
    følger med, peker CSS-en på noe som ikke finnes i rota."""
    vist_til = set(re.findall(r'url\("([^"]+\.woff2)"\)', nettsted.stilark()))
    assert vist_til, "@font-face uten url(...woff2) — er fonten fjernet?"
    assert vist_til <= set(nettsted.FONTFILER)
    # Og andre veien: en font som SENDES UT uten at noe viser til den,
    # er 35 kB hver leser laster ned for ingenting.
    assert {f for f in nettsted.FONTFILER if f.endswith(".woff2")} == vist_til


# ---- gradnettet -------------------------------------------------------
#
# Kartet har ingen kystlinje (ingen lisens), og gradnettet er derfor den
# eneste referansen en leser har. Er det feil plassert, er det verre enn
# ingen referanse: da peker det på noe.

def test_gradnettet_ligger_der_punktene_ligger():
    """Invarianten som bærer hele nettet: en lokalitet på nøyaktig 65
    grader nord skal ha samme y som 65-gradslinja, regnet ut av samme
    projeksjon. Faller de fra hverandre, viser nettet feil sted."""
    akva = {
        "1": {"breddegrad": "58.0", "lengdegrad": "5.0"},
        "2": {"breddegrad": "71.0", "lengdegrad": "31.0"},
        "3": {"breddegrad": "65.0", "lengdegrad": "10.0"},
    }
    punkter, _uten, _hoyde, gitter = nettsted.kartpunkter(akva)
    px = {p["loknr"]: p for p in punkter}
    lat65 = next(l for l in gitter["bredde"] if l["grad"] == 65)
    lon10 = next(l for l in gitter["lengde"] if l["grad"] == 10)
    assert px["3"]["y"] == pytest.approx(lat65["y"], abs=0.1)
    assert px["3"]["x"] == pytest.approx(lon10["x"], abs=0.1)


def test_gradnettet_gaar_ikke_utenfor_utstrekningen():
    """En linje utenfor dataene sier at nettet dekker noe kartet ikke
    gjør. Utstrekningen her er 58,0-71,0 nord: 55 og 75 skal ikke med."""
    akva = {
        "1": {"breddegrad": "58.0", "lengdegrad": "5.0"},
        "2": {"breddegrad": "71.0", "lengdegrad": "31.0"},
    }
    _p, _u, _h, gitter = nettsted.kartpunkter(akva)
    assert [l["grad"] for l in gitter["bredde"]] == [60, 65, 70]
    assert [l["grad"] for l in gitter["lengde"]] == [5, 10, 15, 20, 25, 30]


def test_kart_uten_punkter_gir_tomt_gradnett():
    """Ingen koordinater, ingen utstrekning, ingen linjer. Et nett uten
    kart ville vært et koordinatsystem uten noe i seg."""
    _p, uten, hoyde, gitter = nettsted.kartpunkter(
        {"1": {"breddegrad": "", "lengdegrad": ""}})
    assert uten == ["1"] and hoyde == 0.0
    assert gitter["bredde"] == [] and gitter["lengde"] == []


def test_etikettene_klippes_ikke_av_viewboxen():
    """Den siste lengdegraden ligger få piksler fra kanten. Står
    etiketten til høyre for linja si, er den utenfor bildet."""
    akva = {
        "1": {"breddegrad": "58.0", "lengdegrad": "5.0"},
        "2": {"breddegrad": "71.0", "lengdegrad": "31.0"},
    }
    _p, _u, _h, gitter = nettsted.kartpunkter(akva)
    sist = gitter["lengde"][-1]
    assert sist["etikett_anker"] == "end"
    assert sist["etikett_x"] < sist["x"]
    assert all(l["etikett_anker"] == "start" for l in gitter["lengde"][:-1])
    # Breddegradene står til HØYRE, der kartet er tomt. Ved venstre kant
    # ligger kysten, og «60°N» havnet midt i klyngen i Rogaland.
    assert all(l["etikett_x"] > nettsted.KART_BREDDE / 2
               for l in gitter["bredde"])


def test_lagdelingen_i_kartet_er_rekkefolgen_i_markupen():
    """SVG har ingen z-indeks. Rekkefølgen ER lagdelingen: gradnettet
    under områdene, kystlinja over dem — en kystlinje tegnet først ville
    ligget under tretten fylte flater og ikke vært synlig i det hele
    tatt."""
    html = _forside()
    assert (html.index('class="kart-gitter"')
            < html.index('class="kart-omraader"')
            < html.index('class="kart-land"'))


# ---- lusegrafen -------------------------------------------------------
#
# Grafen legger ikke til én verdi; den er `lus_serie` tegnet. Prøvene
# her handler derfor ikke om utseende, men om at tegningen sier det
# samme som lista — og særlig om det ene den ikke får lov å si.

def _uker(*verdier, brakk=()):
    """Én uke per verdi. `None` = kilden oppgir ingenting."""
    return [{"voksne_hunnlus": "" if v is None else str(v),
             "brakklagt": "True" if i in brakk else "False",
             "iso_aar": "2020", "iso_uke": f"{i + 1:02d}",
             "dato": f"2020-01-{i + 1:02d}"}
            for i, v in enumerate(verdier)]


def test_hullet_faar_ingen_soyle():
    """Den ene feilen grafen ikke får gjøre. Et hull er ikke null, og
    hele tabellen under sier at «–» betyr at kilden ikke oppgir noe
    tall.

    MED SØYLER FALLER PROBLEMET BORT AV SEG SELV. Fram til 22.09.2026
    var dette en kurve, og den måtte BRYTES ved hvert hull for å slippe
    å påstå noe om uka imellom. En uke uten tall har ingen søyle, og et
    tomrom ligner ikke på en null."""
    g = nettsted.lusegraf(_uker(0.4, 0.5, None, 0.6, 0.7))
    assert len(g["soyler"]) == 4, "bare uker med tall får søyle"
    assert g["uten_tall"] == 1 and g["uker_med_tall"] == 4


def test_en_enslig_uke_mellom_to_hull_forsvinner_ikke():
    """En kurve trengte en egen sirkel for en uke mellom to hull, fordi
    en `<polyline>` med ett punkt tegner ingenting. En søyle trenger
    ingen slik reserve — den står der."""
    g = nettsted.lusegraf(_uker(None, 0.9, None))
    assert len(g["soyler"]) == 1
    assert g["soyler"][0]["verdi"] == "0,9"


def test_en_maalt_null_er_en_soyle_og_ikke_ingenting():
    """`y(0)` er nullinja, og en `<rect>` med høyde 0 tegner ikke en
    piksel. Uten et gulv ville «telt til null lus» og «ingen telling»
    sett nøyaktig like ut — som er den samme feilen som over, bare
    andre veien.

    MÅLT på OTERNESET: 124 av 558 uker med tall har verdien 0."""
    g = nettsted.lusegraf(_uker(0.0, 0.5, None))
    assert len(g["soyler"]) == 2
    null = g["soyler"][0]
    assert null["h"] > 0, "en målt null må tegne noe"
    assert null["h"] < 2, "og den må ikke ligne på en verdi"
    assert g["nuller"] == 1


def test_grafen_finnes_ikke_naar_det_ikke_er_noe_aa_tegne():
    """En akse uten en eneste verdi er en ramme som later som om den
    har et innhold."""
    assert nettsted.lusegraf([]) is None
    assert nettsted.lusegraf(_uker(None, None)) is None


def test_ingen_tiltaksgrense_er_tegnet():
    """Grensa står i lakselusforskriften, varierer med sesong og med
    vedtak per lokalitet, og er IKKE samlet inn. En strek på 0,5 tegnet
    av oss ville vært en påstand om regelverket, ikke en gjengivelse av
    en kilde — og en søyle farget rust fordi den er over en strek vi
    fant på, ville vært en vurdering forkledd som data.

    Se avvik 2 i oppdraget og docs/APNE-SPORSMAL.md."""
    g = nettsted.lusegraf(_uker(0.1, 0.9))
    assert "tiltaksgrense" not in g
    # Og ingen søyle bærer en egen farge.
    assert all(set(s) == {"x", "y", "h", "uke", "verdi"} for s in g["soyler"])
    html = _side(lusegraf=g)
    assert "tiltaksgrense" not in html.lower() or \
        "Ingen tiltaksgrense er tegnet" in html


def test_baandene_dekker_brakklagte_uker_og_bare_dem():
    g = nettsted.lusegraf(_uker(0.1, None, None, 0.2, None, brakk=(1, 2)))
    assert len(g["baand"]) == 1
    assert g["brakklagt"] == 2
    # 3 hull, 2 forklart av brakklegging, 1 uforklart. Regnestykket står
    # i bildeteksten, framfor at båndene ser ut som om de dekker alt.
    assert (g["uten_tall"], g["hull_forklart"], g["hull_uforklart"]) == (3, 2, 1)


def test_kurven_holder_seg_innenfor_plottet():
    """Taket rundes opp til et pent trinn, aldri ned: en verdi over
    taket ville blitt tegnet utenfor ramma."""
    g = nettsted.lusegraf(_uker(0.0, 1.54, 0.3))
    assert g["tak"] >= 1.54
    for s in g["soyler"]:
        assert s["y"] >= g["plott_y"] - 0.05, s
        assert s["y"] + s["h"] <= g["bunn"] + 0.05, s


def test_y_aksen_bruker_pene_trinn():
    """0,4 leses som fire tideler. 0,37 leses ikke som noe."""
    # 0,13 -> 0,15 og ikke 0,20: trinnet er 0,05, og linjene blir
    # 0 / 0,05 / 0,10 / 0,15. Taket er nærmeste trinn OVER verdien, ikke
    # nærmeste runde tall.
    for maks, ventet_tak in ((0.13, 0.15), (1.54, 2.0), (0.04, 0.05), (9.0, 10.0)):
        g = nettsted.lusegraf(_uker(0.0, maks))
        assert g["tak"] == pytest.approx(ventet_tak), maks
        assert g["linjer"][0]["etikett"] == "0"


def test_grafen_og_tabellen_teller_de_samme_ukene():
    """To tall om samme uker, sagt hver for seg, er formen F6 og F7
    hadde. Grafen regnes av `lus_serie` — den samme lista tabellen og
    CSV-en bygges av — og da KAN de ikke bli uenige."""
    serie = _uker(0.1, None, 0.3, None, None, brakk=(3,))
    g = nettsted.lusegraf(serie)
    assert g["uker"] == len(serie)
    assert g["uten_tall"] == sum(1 for u in serie if u["voksne_hunnlus"] == "")


def test_grafen_rendres_med_aksen_under_soylene():
    """SVG har ingen z-indeks. Rekkefølgen i markupen ER lagdelingen:
    aksen under søylene, og brakkleggingsstripa sist fordi den ligger
    UNDER nullinja og ikke kan dekke noe.

    Brakkleggingsstripa er lav og under aksen fra 22.09.2026. Et bånd
    over hele plottet, som det var før, leses som en verdi på y-aksen —
    og brakklegging er ikke en luseverdi."""
    serie = _uker(0.1, 0.2, None, 0.3, 0.4, brakk=(2,))
    html = _side(lus_serie=serie, lusegraf=nettsted.lusegraf(serie))
    assert html.index('class="akse"') < html.index('class="soyler"')
    assert html.index('class="soyler"') < html.index('class="brakk"')
    # Fire uker med tall gir fire søyler; hullet gir ingen.
    assert html.count("<rect") == 4 + 1      # fire søyler + ett brakkbånd


def test_siden_uten_lusetall_beholder_TABELLEN():
    """Grafen er en TEGNING av tabellen, ikke en forutsetning for den.
    Første utkast la tabellen inne i `{% if lok.lusegraf %}`, og en
    lokalitet uten tegnbar graf mistet tallene også."""
    html = _side(lus_serie=[], lusegraf=None)
    assert 'id="lusetall-uke"' in html
    assert "0.0045454544" in html


def test_siden_uten_lusetall_far_ingen_graf():
    html = _side(lus_serie=[], lus=[], lus_uker=0, lus_fra="", lus_til="",
                 lusegraf=None, lusetall_snapshots=764)
    assert "<svg class=\"lusegraf\"" not in html
    assert "Ingen lusetall rapportert" in html
    # Men tabellen står, med hode og null rader.
    assert 'id="lusetall-uke"' in html


def test_om_siden_lenker_til_fontlisensen():
    """OFL 1.1 krever at lisensteksten følger fonten. `skriv_fonter()`
    legger den på /newsreader-OFL.txt, men en fil ingen vet om er en
    fil ingen finner — og da er plikten oppfylt på papiret bare."""
    flat = " ".join(_om().split())
    assert "SIL Open Font License 1.1" in flat
    assert 'href="/newsreader-OFL.txt"' in flat
    assert "Newsreader" in flat


def test_laanelista_peker_paa_filer_som_faktisk_skrives(tmp_path):
    """En lenke i lisenstabellen som gir 404 er verre enn ingen lenke:
    den sier at teksten finnes."""
    nettsted.skriv_stil(tmp_path)
    nettsted.skriv_fonter(tmp_path)
    nettsted.skriv_bilder(tmp_path)
    for l in nettsted.VAART_LAAN:
        # TOM STI BETYR at lisensen ikke krever at teksten følger med.
        # Raden står likevel — se docs/LISENSKJEDE.md merknad G — og
        # prøven skal ikke kreve en fil som ikke skal finnes.
        if not l["sti"]:
            continue
        assert (tmp_path / l["sti"].lstrip("/")).exists(), l["sti"]


# ---- eiere kilden kaller personer -------------------------------------
#
# Tre ledd stiller SAMME spørsmål til kilden: `fetch()` lar være å
# hente raden, `personeier()` lar være å lage en selskapsside, og
# `_eierrad()` lar være å skrive navnet. Leddene finnes fordi et
# snapshot skrives én gang og leses i årevis — et gammelt snapshot kan
# bære en rad dagens kode aldri ville hentet.

def _till(**over):
    d = {"eier_navn": "SALMAR OPPDRETT AS", "eier_orgnr": "928957489",
         "eier_type": "LimitedLiabilityCompany", "tillatelse_type": "KOMM-MATF",
         "kapasitet": "1022.0", "kapasitet_enhet": "TN",
         "tildelt_tid": "2004-09-29T00:00:00Z", "tildelt_navn": "SALMAR NORD AS"}
    d.update(over)
    return d


def test_eier_som_er_personform_faar_ikke_navnet_sitt_skrevet():
    """MÅLT 21.09.2026: H-FJ-0018 er et partrederi (PRE). Mandagens
    snapshot ble skrevet av kode fra før 16.09 og har ingen
    `organisasjonsform`-rad for den, så lesedøra har ingenting å bite
    i. `eier_type` har den, og det er kildens felt."""
    rad = nettsted._eierrad("H-FJ-0018", _till(
        eier_type="JointlyOwnedShippingCompany",
        eier_navn="PARTREDERIET NOEN NAVNGITTE MENNESKER ANS",
        tildelt_navn="PARTREDERIET NOEN NAVNGITTE MENNESKER ANS",
        eier_orgnr="954744469"))
    assert rad["eier_navn"] == nettsted.EIER_PERSONFORM
    assert rad["eier_felt"] == nettsted.EIER_PERSONFORM_FELT
    assert rad["eier_orgnr"] == ""
    assert rad["tildelt_navn"] == ""
    # Tillatelsen forsvinner IKKE. En utelatt rad ville vist 9 av 10
    # tillatelser uten å si det.
    assert rad["nr"] == "H-FJ-0018"
    assert rad["type"] == "KOMM-MATF"


def test_vanlig_eier_er_uberoert():
    rad = nettsted._eierrad("T-D-0009", _till())
    assert rad["eier_navn"] == "SALMAR OPPDRETT AS"
    assert rad["eier_felt"] == "eier_navn"
    assert rad["tildelt_navn"] == "SALMAR NORD AS"


def test_alle_personformene_treffer_samme_ledd():
    """Lista er kildens, ikke vår. Kopieres den hit, er det to lister
    som skal si det samme — formen F6 og F7 hadde."""
    from sources.eierskap import FORM_KART
    from core import persondata
    for type_, kode in FORM_KART.items():
        rad = nettsted._eierrad("X", _till(eier_type=type_))
        skjult = rad["eier_navn"] == nettsted.EIER_PERSONFORM
        assert skjult == persondata.er_personform(kode), (type_, kode)


def test_navnet_staar_ikke_paa_sida(tmp_path):
    """Porten leser utputtet. Denne leser malen — samme spørsmål, ett
    ledd tidligere, slik at et brudd har et navn før det har et funn."""
    html = _side(tillatelser=[nettsted._eierrad("H-FJ-0018", _till(
        eier_type="JointlyOwnedShippingCompany",
        eier_navn="PARTREDERIET HEMMELIG ANS",
        tildelt_navn="PARTREDERIET HEMMELIG ANS"))])
    assert "PARTREDERIET HEMMELIG" not in html
    assert nettsted.EIER_PERSONFORM in html
    assert "H-FJ-0018" in html


# ---- blokkene i grunnmalen ---------------------------------------------
#
# Jinja IGNORERER en `{% block %}` som grunnmalen ikke har. Det er ikke
# en feil i Jinja — en mal kan arve fra flere — men følgen her er stille
# og stor: da `hero` ble til `toppinnhold` 22.09.2026, rendret forsiden
# fortsatt, bare uten heroen. Ingenting kastet, og bygget var grønt.

def test_malene_bruker_bare_blokker_grunnmalen_har():
    """Driftvakten. En blokk som ikke finnes i grunnmalen rendres ikke,
    og den som skrev den får ingen beskjed — hele seksjonen forsvinner
    bare. MÅLT: det skjedde med forsidens hero."""
    kommentar = re.compile(r"\{#.*?#\}", re.S)
    blokk = re.compile(r"\{%-?\s*block\s+([a-z_]+)")

    grunn = kommentar.sub("", (nettsted.MALER / "base.html.j2")
                          .read_text(encoding="utf-8"))
    tillatt = set(blokk.findall(grunn))
    assert tillatt, "grunnmalen har ingen blokker — er arven byttet ut?"

    feil = []
    for sti in sorted(nettsted.MALER.glob("*.html.j2")):
        tekst = kommentar.sub("", sti.read_text(encoding="utf-8"))
        if "{% extends" not in tekst:
            continue
        for navn in blokk.findall(tekst):
            if navn not in tillatt:
                feil.append(f"{sti.name}: {{% block {navn} %}} finnes ikke "
                            f"i base.html.j2 — innholdet rendres aldri")
    assert not feil, "\n".join(feil)


# ---- de to lekkasjene porten fant 22.09.2026 ---------------------------
#
# Begge ble innført av designrunden, og begge ble stoppet av
# publiseringsvakten før noe gikk ut. Prøvene under er der for at de
# ikke skal kunne komme tilbake stille.

def test_en_personform_navngis_ikke_i_overskriften():
    """MÅLT: porten stoppet publiseringen på lokalitet 11593, der
    «PARTREDERIET BRØDRENE SIGLEN ANS» sto i det nye
    «Innehaver»-feltet i overskriften mens tabellraden under sa
    «eieren er en personform».

    `_eierrad()` stilte spørsmålet; den nye veien til det samme navnet
    gjorde ikke. To steder som skal si det samme om hvem vi ikke
    navngir, er formen F6 og F7 hadde — og her er prisen et navngitt
    menneske på en offentlig side. Regel 3."""
    # `UnlimitedLiabilityCompany` er pub-aquas ord for ANS, og
    # `FORM_KART` oversetter det. Verdien er kildens egen, ikke en vi
    # fant på: det var nøyaktig denne som sto på lokalitet 11593.
    person = {"N-T-0001": {"eier_navn": "PARTREDERIET BRØDRENE X ANS",
                           "eier_orgnr": "912345678",
                           "eier_type": "UnlimitedLiabilityCompany"}}
    sel = nettsted._lokalitetens_selskap(person, [], person)
    assert sel["personform"] is True
    assert sel["navn"] == nettsted.EIER_PERSONFORM
    assert "PARTREDERIET" not in sel["navn"]
    assert sel["url"] == "" and sel["orgnr"] == ""
    # Og antallet forsvinner ikke: raden står, navnet gjør ikke.
    assert sel["antall"] == 1

    html = _side(selskap=sel)
    assert "PARTREDERIET" not in html
    assert nettsted.EIER_PERSONFORM in html


def test_en_tankestrek_er_ikke_et_navn():
    """MÅLT: porten stoppet fire lokalitetssider med
    `ukjent_navn — «W» 1 tegn`. Verdien var tankestreken, i en celle
    merket `data-felt="eier_navn"` fordi changelog-raden gjaldt det
    feltet og den gamle verdien var tom.

    En tankestrek er ikke et ukjent selskap; den er fraværet av et.
    Samme regel som `EIER_UKJENT_FELT` har hatt siden 19.09."""
    assert nettsted.feltmerke("SALMAR AS", "eier_navn") == "eier_navn"
    assert nettsted.feltmerke("", "eier_navn") == nettsted.VERDI_MANGLER_FELT
    assert nettsted.feltmerke(None, "eier_navn") == nettsted.VERDI_MANGLER_FELT
    assert nettsted.feltmerke("  ", "eier_navn") == nettsted.VERDI_MANGLER_FELT

    poster = nettsted._observert_historikk(
        _endringsrader([{"dato": "2026-09-14", "felt": "eier_navn",
                         "fra": "", "til": "SALMAR AS",
                         "kilde": "eierskap"}]),
        [{"kilde": "eierskap", "fra": "2026-09-02"}], None)
    assert poster[0]["fra_felt"] == nettsted.VERDI_MANGLER_FELT
    assert poster[0]["til_felt"] == "eier_navn"


def test_porten_ser_ikke_tankestreken_som_et_ukjent_navn():
    """Oppførselen, ikke bare funksjonen: den rendrede siden skal ikke
    gi `ukjent_navn` på en tom verdi."""
    import publiseringsvakt as vakt

    html = _side(endringer=[{
        "dato": "2026-09-14", "gjelder": "lokaliteten", "kilde": "eierskap",
        "felt": "eier_navn", "fra": "", "til": "SALMAR OPPDRETT AS",
    }])
    navn_ok = {vakt.navnenoekkel(n) for n in
               ("OTERNESET", "SALMAR OPPDRETT AS", "SALMAR NORD AS",
                "SALMAR FARMING AS")}
    orgnr_ok = {"928957489", "966840528"}
    funn = [f for f in vakt.gransk_tekst(html, orgnr_ok, navn_ok)
            if f.slag == "ukjent_navn"]
    assert funn == [], funn
