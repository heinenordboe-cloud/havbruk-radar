"""Vakten på generert output, før noe publiseres.

`core/persondata.py` beskytter dataene to steder. Ingen av dem beskytter
en GENERATOR: en funksjon som leser et filtrert snapshot og skriver HTML
kan sette sammen felter på en måte ingen av filtrene ser.

Testene her er av to slag, og skillet er viktig:

  * De fleste prøver VAKTEN — at den fanger hver av de tre klassene, og
    at den ikke fyrer på det som er gjort rede for. De kjører uten data
    og uten nett, som resten av suiten.

  * `test_porten_kan_ikke_vaere_en_pytest_test` dokumenterer hvorfor
    selve PORTEN ikke ligger her. `conftest.py` peker `HAVBRUK_DATA_DIR`
    til en engangsmappe, så hvitelista er tom inne i suiten, og en port
    bygget på den ville felt hver publisering. Porten er en kommando:
    `python publiseringsvakt.py <mappe>`, exit 1 ved funn.

Den viktigste testen er `test_hvitelista_bygges_gjennom_doren`. Bygges
hvitelista med `pl.read_parquet()` i stedet for `snapshot._les()`,
inneholder den nøyaktig de orgnumrene og navnene vakten finnes for å
stoppe — og vakten godkjenner dem. Den feilen ville vært usynlig: en
grønn vakt over et utputt med persondata i.
"""

import os
import sys
from pathlib import Path

import polars as pl
import pathlib

import pytest

import publiseringsvakt as vakt
from core import persondata, snapshot
from core.contract import Observation


# ---- oppsett ----------------------------------------------------------

def _obs(entity_id, field, value, source="enhetsregisteret"):
    return Observation(
        entity_id=entity_id, entity_type="selskap", entity_name="",
        field=field, value=value, source=source, observed_at="2026-09-15",
    )


@pytest.fixture
def snapshotmappe(tmp_path, monkeypatch):
    """Et lite, ekte snapshot: ett AS og ett ENK.

    ENK-et SKRIVES til fila — det er poenget. Snapshots fra før
    22.08.2026 inneholder 34 av dem, og hele spørsmålet er om vakten
    leser gjennom døra som fjerner dem.
    """
    # Snapshotene i sin egen mappe, ADSKILT fra det som granskes. Deler
    # de rot, vil `_snapshotrammer()` forsøke å lese utputtet som om det
    # var en kilde — og en falsk .parquet der feller hvitelistebyggingen
    # i stedet for granskningen.
    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)

    rader = [
        _obs("912345678", "navn", "Nordlaks Oppdrett"),
        _obs("912345678", "organisasjonsform", "AS"),
        _obs("998877665", "navn", "Kari Nordmann"),
        _obs("998877665", "organisasjonsform", "ENK"),
    ]
    mappe = rot / "enhetsregisteret"
    mappe.mkdir(parents=True)
    pl.DataFrame([o.as_dict() for o in rader]).write_parquet(
        mappe / "2026-09-15.parquet")
    return rot


@pytest.fixture
def lister(snapshotmappe):
    return vakt.hviteliste()


def _side(kropp: str) -> str:
    return f"<html><body>{kropp}</body></html>"


# ---- hvitelista, og hvorfor veien betyr noe ---------------------------

def test_hvitelista_bygges_gjennom_doren(snapshotmappe, lister):
    """ENK-et står i FILA og skal IKKE stå i hvitelista.

    Dette er hele konstruksjonen. `snapshot._les()` kjører
    `fjern_personformer()`, så orgnummeret og navnet til ENK-et finnes
    ikke i lista — og et utputt som viser dem blir dermed et funn.

    Bygges lista med `pl.read_parquet()`, kommer begge med, og vakten
    godkjenner nøyaktig det den finnes for å stoppe.
    """
    orgnr, navn = lister
    assert "912345678" in orgnr, "AS-et skal være gjort rede for"
    assert "Nordlaks Oppdrett" in navn

    assert "998877665" not in orgnr, (
        "ENK-ets orgnummer står i parquet-fila. Er det i hvitelista, "
        "er lista bygget utenom snapshot._les() og vakten er blind."
    )
    assert "Kari Nordmann" not in navn

    # Kontrollen av kontrollen: fila inneholder dem faktisk.
    fil = snapshotmappe / "enhetsregisteret" / "2026-09-15.parquet"
    rå = pl.read_parquet(fil)
    assert "998877665" in rå["entity_id"].to_list()


# ---- prøve 1: ni-sifrede tall -----------------------------------------

def test_ukjent_orgnummer_felles(lister):
    """Et orgnummer som ikke kom gjennom døra har ingen proveniens."""
    orgnr, navn = lister
    funn = vakt.gransk_tekst(_side("<td>998877665</td>"), orgnr, navn)
    assert [f.slag for f in funn] == ["ukjent_orgnr"]


def test_kjent_orgnummer_slipper_gjennom(lister):
    """Prøven er en HVITELISTE. Et forbud mot \\b\\d{9}\\b ville felt hver
    side som viser ett eneste selskap — målt 15.09.2026: 1807 entity_id
    i enhetsregisteret, 2953 eier_orgnr i eierskap. Et forbud som må slås
    av for å publisere, blir slått av."""
    orgnr, navn = lister
    assert vakt.gransk_tekst(_side("<td>912345678</td>"), orgnr, navn) == []


def test_ni_siffer_som_ikke_er_orgnummer_felles_ogsaa(lister):
    """`aksjekapital` og `antall_aksjer` har ni siffer i 58 tilfeller uten
    å være orgnumre. De felles her, og det er riktig: vakten kan ikke
    vite at et ukjent nisiffer er ufarlig, og en generator som skriver
    tall den ikke kan gjøre rede for skal si fra."""
    orgnr, navn = lister
    funn = vakt.gransk_tekst(_side("<td>100000000</td>"), orgnr, navn)
    assert [f.slag for f in funn] == ["ukjent_orgnr"]


def test_desimaltall_er_ikke_et_orgnummer(lister):
    """MÅLT mot ekte utputt 15.09.2026.

    `oversikt.html` inneholder biomasse i kilo — «96697320.109» og
    «123456789.289». Med `\\b\\d{9}\\b` traff prøven heltallsdelen og meldte
    et orgnummer som ikke fantes: ett funn i den eneste genererte fila vi
    har, og det var falskt. En vakt som fyrer på hver biomasseverdi blir
    slått av."""
    orgnr, navn = lister
    for desimal in ("123456789.289", "96697320.109", "1234567890",
                    "12345678912"):
        assert vakt.gransk_tekst(_side(f"<td>{desimal}</td>"),
                                 orgnr, navn) == [], desimal


def test_orgnummer_som_desimaltall_er_et_kjent_hull(lister):
    """Prisen for testen over, skrevet ned framfor oppdaget senere.

    Et orgnummer formatert som «912345678.0» — ut av en pandas-runde —
    blir ikke sett. Ingen generator her gjør det i dag. Testen står som
    dokumentasjon av hullet, ikke som ønsket oppførsel: endres den, skal
    det være fordi noen har bestemt at hullet skal lukkes."""
    orgnr, navn = lister
    assert vakt.gransk_tekst(_side("<td>998877665.0</td>"), orgnr, navn) == []


def test_rapporten_er_ikke_selv_en_lekkasje(lister):
    """Vakten kjører i en byggejobb, og byggelogger i et offentlig repo
    er offentlige. En vakt som skriver det lekkede navnet eller nummeret
    til loggen har FLYTTET lekkasjen, ikke stoppet den — samme feil som
    changeloggen gjorde da kildefilteret kom uten lesefilteret.

    Fanget av verifiseringen mot en EKTE lekkasje 15.09.2026: første
    utkast forkortet navnet til 18 tegn, og et navn på 15 tegn gikk
    uavkortet i rapporten."""
    orgnr, navn = lister
    side = _side('<td>998877665</td><td class="eier">Kari Nordmann</td>')
    rapport = "\n".join(str(f) for f in vakt.gransk_tekst(side, orgnr, navn))

    assert "998877665" not in rapport
    assert "…7665" in rapport
    assert "Kari Nordmann" not in rapport
    assert "Kari" not in rapport and "Nordmann" not in rapport
    # ... men nok til å finne den igjen
    assert "«W W»" in rapport and "13 tegn" in rapport


# ---- prøve 2: organisasjonsform ---------------------------------------

def test_personform_felles(lister):
    orgnr, navn = lister
    funn = vakt.gransk_tekst(_side("<td>ENK</td>"), orgnr, navn)
    assert [f.slag for f in funn] == ["personform"]


def test_personform_leses_fra_persondata_ikke_skrevet_av(lister, monkeypatch):
    """Lista over hvem vi nekter å publisere om skal finnes ETT sted. To
    lister er to steder å glemme den ene."""
    orgnr, navn = lister
    monkeypatch.setattr(persondata, "PERSONFORMER", frozenset({"ENK", "ZZZ"}))
    funn = vakt.gransk_tekst(_side("<td>ZZZ</td>"), orgnr, navn)
    assert [f.slag for f in funn] == ["personform"], (
        "vakten har sin egen kopi av PERSONFORMER"
    )


def test_personform_fyrer_ikke_paa_ord_som_inneholder_koden(lister):
    """«ENKELTVEDTAK» og «Enkelt» er ikke organisasjonsformer. En vakt
    som fyrer på dem blir slått av."""
    orgnr, navn = lister
    for ufarlig in ("ENKELTVEDTAK", "Enkeltmannsforetakene", "SENKING"):
        side = _side(f"<p>{ufarlig}</p>")
        assert vakt.gransk_tekst(side, orgnr, navn) == [], ufarlig


# ---- prøve 2b: kodene som også betyr noe annet ------------------------
#
# Grensa flyttet til sektor 2300 16.09.2026, og DA kom inn i
# PERSONFORMER. «DA» er også dekar: 748 rader `kapasitet_enhet` i
# akvakultur og eierskap. Den brede prøven meldte fire funn på den ene
# ekte genererte fila vi har, og alle fire var falske.


def test_tvetydig_kode_feller_ikke_som_arealenhet(lister):
    """`kapasitet_enhet: DA` er dekar. En blokkerende vakt som fyrer på
    hver arealangivelse blir slått av — og da har den gjort skade."""
    orgnr, navn = lister
    side = _side('<td>kapasitet_enhet</td><td>DA</td>')
    assert vakt.gransk_tekst(side, orgnr, navn, tvetydige={"DA"}) == []


def test_tvetydig_kode_feller_i_organisasjonsform_sammenheng(lister):
    """Samme tre bokstaver, men noen har sagt hva de betyr. Da er det et
    funn — ordrett formen `oversikt.html` hadde 16.09.2026."""
    orgnr, navn = lister
    side = _side('{"felt": "organisasjonsform", "distinkte": 5, '
                 '"eksempler": ["AS", "DA", "KBO"]}')
    funn = vakt.gransk_tekst(side, orgnr, navn, tvetydige={"DA"})
    assert [f.slag for f in funn] == ["personform"]


def test_entydig_kode_feller_uten_sammenheng(lister):
    """ENK betyr ikke noe annet noe sted, og skal fortsatt felles som
    bart ord. Innstrammingen gjelder bare de målt tvetydige."""
    orgnr, navn = lister
    funn = vakt.gransk_tekst(_side("<td>ENK</td>"), orgnr, navn,
                             tvetydige={"DA"})
    assert [f.slag for f in funn] == ["personform"]


def test_tvetydighet_maales_av_dataene_ikke_skrives_av():
    """Lista over tvetydige koder er MÅLT mot snapshotene, ikke listet i
    vakten. En ny kilde som bruker `ANS` som enhetskode skal dempe
    prøven av seg selv — og en som slutter, skal skjerpe den igjen."""
    ramme = pl.DataFrame({
        "entity_id": ["1", "2", "3"],
        "field": ["kapasitet_enhet", persondata.FORM_FELT, "navn"],
        "value": ["DA", "ENK", "Testlaks AS"],
    })
    # DA er en lovlig verdi i et ANNET felt -> tvetydig.
    # ENK står i selve formfeltet -> det er ikke tvetydighet, det er et
    # snapshot som bærer en personform, og det er vaktens jobb å melde.
    assert vakt.tvetydige_koder([ramme]) == {"DA"}


# ---- prøve 3: navn i eierfelt -----------------------------------------

def test_ukjent_navn_i_eierfelt_felles(lister):
    orgnr, navn = lister
    side = _side('<td class="eier">Kari Nordmann</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn)
    assert [f.slag for f in funn] == ["ukjent_navn"]


def test_kjent_navn_i_eierfelt_slipper_gjennom(lister):
    orgnr, navn = lister
    side = _side('<td class="eier">Nordlaks Oppdrett</td>')
    assert vakt.gransk_tekst(side, orgnr, navn) == []


def test_navneproven_ser_bare_det_generatoren_MERKER(lister):
    """En reell grense, og den står i modulens docstring.

    Skriver generatoren eiernavnet som løpende tekst uten merking, finner
    ikke prøven det. Alternativet — å gjette hva som er et navn — ville
    fyrt på hvert stedsnavn i datasettet, og en vakt som alltid fyrer
    blir slått av. Testen dokumenterer hullet framfor å late som det
    ikke finnes.
    """
    orgnr, navn = lister
    umerket = _side("<p>Anlegget drives av Kari Nordmann.</p>")
    assert vakt.gransk_tekst(umerket, orgnr, navn) == []


def test_html_escapet_navn_sammenlignes_avkodet(snapshotmappe, monkeypatch,
                                                tmp_path):
    """Hvitelista har `&`, HTML-en har `&amp;`, og det er samme navn.

    MÅLT 18.09.2026 på `data/nettsted`: `ukjent_navn` meldte 54 funn på
    ett eneste navn — et AS som ligger i hvitelista — fordi cellen ble
    sammenlignet escapet mot en uescapet liste. Alle 54 var falske, og en
    vakt som feiler feil blir slått av.
    """
    rader = [_obs("912345678", "navn", "Egil & Sønner")]
    mappe = snapshotmappe / "eierskap"
    mappe.mkdir(parents=True)
    pl.DataFrame([o.as_dict() for o in rader]).write_parquet(
        mappe / "2026-09-15.parquet")

    orgnr, navn = vakt.hviteliste()
    assert "Egil & Sønner" in navn

    side = _side('<td class="eier">Egil &amp; Sønner</td>')
    assert vakt.gransk_tekst(side, orgnr, navn) == []

    # Og kontrollen av kontrollen: et ANNET escapet navn felles fortsatt.
    ukjent = _side('<td class="eier">Kari &amp; Nordmann</td>')
    assert [f.slag for f in vakt.gransk_tekst(ukjent, orgnr, navn)] \
        == ["ukjent_navn"]


# ---- merkingen er FELTVOKABULARET, ikke en attributtliste --------------
#
# En felt-verdi-tabell kan ikke merkes med en statisk klasse: samme <td>
# bærer `siste_rapport` i én rad og `eier_navn` i neste. Merkingen er
# derfor `data-felt="<feltnavn>"`, og prøven leser den mot NAVNEFELT —
# samme regel `gransk_csv` har for en kolonneoverskrift.

def test_feltmerket_navn_utenfor_hvitelista_felles(lister):
    orgnr, navn = lister
    side = _side('<td data-felt="eier_navn">Kari Nordmann</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn)
    assert [f.slag for f in funn] == ["ukjent_navn"]


def test_feltmerket_navn_i_hvitelista_slipper_gjennom(lister):
    orgnr, navn = lister
    side = _side('<td data-felt="eier_navn">Nordlaks Oppdrett</td>')
    assert vakt.gransk_tekst(side, orgnr, navn) == []


def test_merkingen_leses_mot_NAVNEFELT_og_ikke_mot_attributtnavnet(lister):
    """Det er FELTET som avgjør, ikke at cellen er merket.

    En `kapasitet`-celle med en navnelignende verdi er ikke et navn, og
    en vakt som fyrte på den ville fyrt på hver verdi i registertabellen
    — 29 merkede celler på én ekte side. Motsatt vei må et hvilket som
    helst felt i `NAVNEFELT` felles, også et vi ikke har tenkt på her:
    lista er ett sted, og prøven spør den.
    """
    orgnr, navn = lister
    fritt = _side('<td data-felt="kapasitet">Kari Nordmann</td>')
    assert vakt.gransk_tekst(fritt, orgnr, navn) == []

    for felt in vakt.NAVNEFELT:
        side = _side(f'<td data-felt="{felt}">Kari Nordmann</td>')
        assert [f.slag for f in vakt.gransk_tekst(side, orgnr, navn)] \
            == ["ukjent_navn"], f"{felt} står i NAVNEFELT og skal felles"


def test_feltmerket_organisasjonsform_felles_uten_tekstvinduet(lister):
    """`DA` er dekar i 748 rader, og felles ellers bare nær feltnavnet.

    Med merkingen trengs ikke vinduet: cellen SIER at feltet er
    organisasjonsform. Det er den samme skjerpingen `gransk_csv` fikk av
    kolonneoverskriften 16.09.
    """
    orgnr, navn = lister
    side = _side('<td data-felt="organisasjonsform">DA</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn, tvetydige={"DA"})
    assert "personform" in [f.slag for f in funn]

    # Samme verdi i et annet felt er en arealenhet og skal ikke felle.
    areal = _side('<td data-felt="kapasitet_enhet">DA</td>')
    assert vakt.gransk_tekst(areal, orgnr, navn, tvetydige={"DA"}) == []


def test_feltmerket_sektorkode_felles_ogsaa(lister):
    orgnr, navn = lister
    side = _side('<td data-felt="institusjonell_sektorkode">2300</td>')
    assert "personform" in [
        f.slag for f in vakt.gransk_tekst(side, orgnr, navn)]


def test_feltmerket_tom_celle_er_ikke_et_funn(lister):
    """Fravær er ikke en verdi. En tom celle i endringstabellen betyr at
    feltet ikke fantes før — `_endringsrad()` skriver tom streng der."""
    orgnr, navn = lister
    side = _side('<td data-felt="eier_navn"></td>'
                 '<td data-felt="eier_navn">   </td>')
    assert vakt.gransk_tekst(side, orgnr, navn) == []
    assert vakt.felt_verdier(side) == []


def test_samme_feltmerkede_navn_i_mange_rader_gir_ETT_funn(lister):
    """En endringstabell kan bære samme navn i mange rader. Én funnrad
    per navn, med antallet — samme form som CSV-prøven, og av samme
    grunn: 764 like funn er en rapport ingen leser."""
    orgnr, navn = lister
    side = _side('<td data-felt="eier_navn">Kari Nordmann</td>' * 5)
    funn = vakt.gransk_tekst(side, orgnr, navn)
    assert len(funn) == 1
    assert funn[0].antall == 5


def test_dobbeltmerket_celle_meldes_en_gang(lister):
    """Bærer en celle både den gamle og den nye merkingen, er det ett
    navn og skal være én funnrad. To rader om samme navn i samme fil er
    støy, ikke informasjon."""
    orgnr, navn = lister
    side = _side('<td class="eier" data-felt="eier_navn">Kari Nordmann</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn)
    assert [f.slag for f in funn] == ["ukjent_navn"]


# ---- filer vakten ikke kan lese ---------------------------------------

def test_ulesbar_fil_rapporteres_ikke_antas_trygg(tmp_path,
                                                 snapshotmappe):
    """En .parquet ved siden av sida er like publisert som HTML-en."""
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "data.parquet").write_bytes(b"PAR1binaertsoppel")
    funn = vakt.gransk(ut)
    assert [f.slag for f in funn] == ["ugranska"]


def test_pinnet_binaerfil_slipper_gjennom(tmp_path, snapshotmappe):
    """Fonten er sett i én gang, og kvitteringen gjelder INNHOLDET."""
    ut = tmp_path / "ut"
    ut.mkdir()
    font = pathlib.Path(vakt.__file__).parent / "maler" / "newsreader.woff2"
    (ut / "newsreader.woff2").write_bytes(font.read_bytes())
    assert vakt.gransk(ut) == []


def test_endret_binaerfil_faller_tilbake_til_ugranska(tmp_path, snapshotmappe):
    """Nøkkelen er summen og ikke navnet. Byttes fonten ut — nytt
    subsett, en annen font med samme filnavn — er den ikke lenger fila
    som ble inspisert, og vakten sier fra."""
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "newsreader.woff2").write_bytes(b"wOF2 noe annet enn fonten")
    funn = vakt.gransk(ut)
    assert [f.slag for f in funn] == ["ugranska"]


def test_hver_pinnet_sum_finnes_som_fil_i_maler(tmp_path):
    """Driftvakten. En pinning som ikke lenger svarer til noen fil er en
    kvittering for noe som ikke finnes — og da er den bare støy som
    skjuler at den ekte fila er ukvittert."""
    import hashlib
    maler = pathlib.Path(vakt.__file__).parent / "maler"
    paa_disk = {hashlib.sha256(f.read_bytes()).hexdigest()
                for f in maler.iterdir() if f.is_file()}
    for sum_, hva in vakt.BINAERFILER.items():
        assert sum_ in paa_disk, f"pinnet sum uten fil i maler/: {hva}"


def test_ren_mappe_gir_ingen_funn(tmp_path, snapshotmappe):
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "index.html").write_text(
        _side('<td class="eier">Nordlaks Oppdrett</td>'
              '<td>912345678</td><td>AS</td>'), encoding="utf-8")
    assert vakt.gransk(ut) == []


def test_alle_tre_klassene_fanges_i_samme_kjoring(tmp_path, snapshotmappe):
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "lekk.html").write_text(
        _side('<td class="eier">Kari Nordmann</td>'
              '<td>998877665</td><td>ENK</td>'), encoding="utf-8")
    assert {f.slag for f in vakt.gransk(ut)} == {
        "ukjent_orgnr", "personform", "ukjent_navn"}


# ---- telleren som ikke feller -----------------------------------------

def test_personeksponert_krever_BÅDE_form_og_navn():
    """Navneprøven alene er verdiløs, og det er MÅLT.

    To-tre ord uten bedriftsord treffer 1278 av 1807 entiteter, hvorav
    1196 er AS — Brreg skriver navn i VERSALER, så «NORDLAKS OPPDRETT
    AS» og «HANSEN OG OLSEN DA» har samme form. Det er signalet fra
    organisasjonsformen som bærer, ikke navnet.

    `core/persondata.py` sa det på forhånd: å filtrere PÅ NAVNET er
    samme feil som ni-siffer-testen fra 16.08."""
    assert vakt.personeksponert("HANSEN OG OLSEN", "DA")
    assert vakt.personeksponert("BERG NILSEN", "ANS")

    # samme navneform, men et aksjeselskap: ikke eksponert
    assert not vakt.personeksponert("HANSEN OG OLSEN", "AS")
    assert not vakt.personeksponert("NORDLAKS OPPDRETT", "AS")
    # riktig form, men et navn som ikke navngir noen
    assert not vakt.personeksponert("NORDLAKS OPPDRETT HAVBRUK NORD", "DA")


def test_personeksponert_feller_ingenting():
    """Telleren er ikke koblet til noen av de tre prøvene.

    Den fanger ikke DA-en her — det gjør `personform`- og
    `ukjent_navn`-prøvene, hver av sin grunn. Telleren teller bare.

    `tvetydige={"DA"}` fordi det er det målte tilfellet: navnet står i
    en eier-celle og ikke i en organisasjonsform-sammenheng, så den
    smale prøven lar den stå. Navnet er med i hvitelista her, som det
    ville vært i et snapshot skrevet før 16.09.2026."""
    slag = {f.slag for f in vakt.gransk_tekst(
        _side('<td class="eier">HANSEN OG OLSEN DA</td>'),
        {"1"}, {"HANSEN OG OLSEN DA"}, tvetydige={"DA"})}
    assert slag == set()


def test_personeksponert_er_null_naar_doren_virker(snapshotmappe):
    """Fra 16.09.2026 skal telleren lese 0, og et tall over 0 betyr at
    noe kom inn utenom `snapshot._les()`.

    Snapshotet i fixturen har ett AS og ett ENK, og ENK-et forsvinner i
    døra. Ingen entitet med personform OG personnavn skal da stå igjen.
    """
    assert vakt.personeksponerte() == {}


# ---- CSV: kolonneoverskriften ER merkingen ---------------------------
#
# En .csv ved siden av sida er ikke mindre publisert enn HTML-en — den er
# verre, fordi den er laget for å lastes ned og leve videre. Fra
# 16.09.2026 ligger hele lusetallserien der, og vakten må se INN i den.


def _csv(*rader: str) -> str:
    return "\n".join(rader) + "\n"


def test_navn_i_navnekolonne_felles(lister):
    """Prøven som IKKE fantes før 16.09.2026.

    `ukjent_navn` leter etter en HTML-merking (`data-navn`,
    `class="eier"`), og en CSV har ingen. Målt på en konstruert fil: et
    navn i en `navn`-kolonne ga null funn. I en CSV er
    KOLONNEOVERSKRIFTEN merkingen — generatorens egen, fra det samme
    feltvokabularet."""
    orgnr, navn = lister
    tekst = _csv("navn,kommune", "Kari Nordmann,BODØ")
    funn = vakt.gransk_csv(tekst, orgnr, navn, "x.csv")
    assert [f.slag for f in funn] == ["ukjent_navn"]
    assert "Kari" not in str(funn[0]) and "Nordmann" not in str(funn[0])


def test_kjent_navn_i_navnekolonne_felles_ikke(lister):
    orgnr, navn = lister
    tekst = _csv("navn,kommune", "Testlaks AS,BODØ")
    assert vakt.gransk_csv(tekst, orgnr, navn | {"Testlaks AS"}, "x.csv") == []


def test_orgnummer_i_csv_celle_felles(lister):
    """MÅLT retting 16.09.2026.

    `NI_SIFFER` krever at tallet ikke har komma på noen av sidene —
    regelen ble satt for HTML, der et komma betyr desimaltall. I en CSV
    er kommaet DELIMITEREN, så `999888777,Kari` ga null funn. Et
    orgnummer i en CSV-kolonne var usynlig for vakten, i nøyaktig den
    filtypen som er laget for å lastes ned."""
    orgnr, navn = lister
    tekst = _csv("orgnr,navn", "999888777,Testlaks AS")
    funn = vakt.gransk_csv(tekst, orgnr, navn | {"Testlaks AS"}, "x.csv")
    assert [f.slag for f in funn] == ["ukjent_orgnr"]
    assert funn[0].utdrag == "…8777"


def test_desimaltall_i_csv_celle_felles_ikke(lister):
    """Og den andre halvdelen: rettingen skal ikke gjeninnføre den
    falske alarmen den erstattet. «96697320.109» er biomasse i kilo."""
    orgnr, navn = lister
    tekst = _csv("loknr,biomasse", "31397,96697320.109")
    assert vakt.gransk_csv(tekst, orgnr, navn, "x.csv") == []


def test_personform_leses_av_kolonnen_og_ikke_av_teksten(lister):
    """I en CSV ligger overskriften en hel rad fra verdien, og
    nabokolonnen ett tegn unna. Tekstvinduet HTML-prøven bruker treffer
    derfor feil i begge retninger.

    `kapasitet_enhet: DA` er dekar. `organisasjonsform: ENK` er en
    person."""
    orgnr, navn = lister
    tekst = _csv("organisasjonsform,kapasitet_enhet",
                 "AS,DA")
    assert vakt.gransk_csv(tekst, orgnr, navn, "x.csv") == []

    tekst = _csv("organisasjonsform,kapasitet_enhet", "ENK,DA")
    funn = vakt.gransk_csv(tekst, orgnr, navn, "x.csv")
    assert [f.slag for f in funn] == ["personform"]
    assert funn[0].utdrag == "['ENK']"


def test_personform_i_en_DA_kolonne_felles(lister):
    """Og DA felles når den står i formkolonnen, der den betyr «delt
    ansvar» og ikke dekar."""
    orgnr, navn = lister
    funn = vakt.gransk_csv(_csv("organisasjonsform", "DA"), orgnr, navn, "x.csv")
    assert [f.slag for f in funn] == ["personform"]


def test_sektorkolonnen_felles_ogsaa(lister):
    """Det andre leddet i personprøven virker også i en CSV. En form
    ingen har ført opp stoppes av sektoren — se core/persondata.py."""
    orgnr, navn = lister
    tekst = _csv("organisasjonsform,institusjonell_sektorkode", "ZZZ,2300")
    funn = vakt.gransk_csv(tekst, orgnr, navn, "x.csv")
    assert [f.slag for f in funn] == ["personform"]


def test_kommentarhodet_granskes_som_tekst(lister):
    """Vår egen CSV bærer attribusjonen i `#`-linjer. En annen
    generators kan bære hva som helst."""
    orgnr, navn = lister
    tekst = _csv("# organisasjonsform ENK", "dato,verdi", "2026-01-01,1")
    funn = vakt.gransk_csv(tekst, orgnr, navn, "x.csv")
    assert [f.slag for f in funn] == ["personform"]


def test_samme_navn_i_mange_rader_gir_ETT_funn(lister):
    """En CSV med 764 rader kan bære samme navn i hver. 764 like funn er
    en rapport ingen leser."""
    orgnr, navn = lister
    tekst = _csv("navn", *["Kari Nordmann"] * 50)
    funn = vakt.gransk_csv(tekst, orgnr, navn, "x.csv")
    assert len(funn) == 1 and funn[0].antall == 50


def test_tsv_avgrenses_av_tabulator_og_ikke_av_komma(tmp_path, lister,
                                                     monkeypatch):
    """MÅLT feil 17.09.2026, i vaktens EGEN dekningspåstand.

    `KOLONNETYPER` var et sett med `.csv` og `.tsv`, og `csv.reader`
    brukte standardavgrenseren — komma — for begge. Hele overskriftsrada
    i en TSV ble da ÉN kolonne som het `navn\tkommune`, som ikke står i
    NAVNEFELT, og et navn i navnekolonnen var usynlig.

    Vakten sa at den dekket `.tsv`. Den gjorde det ikke."""
    orgnr, navn = lister
    monkeypatch.setattr(vakt, "hviteliste", lambda: (orgnr, navn))
    monkeypatch.setattr(vakt, "_snapshotrammer", lambda: iter(()))
    (tmp_path / "serie.tsv").write_text(
        "navn\tkommune\nKari Nordmann\tBODØ\n", encoding="utf-8")

    funn = [f for f in vakt.gransk(tmp_path) if f.fil == "serie.tsv"]
    assert [f.slag for f in funn] == ["ukjent_navn"]


def test_avgrenseren_staar_sammen_med_filtypen():
    """Ikke gjettet, ikke sniffet. En avgrenser som utledes av innholdet
    kan utledes feil av en fil med ett komma i et navn."""
    assert vakt.KOLONNETYPER == {".csv": ",", ".tsv": "\t"}


def test_gransk_dispatcher_csv_til_kolonneproven(tmp_path, lister, monkeypatch):
    """Hele veien: `gransk()` skal velge kolonneprøven for .csv.

    Uten dispatchen ville CSV-en gått gjennom tekstprøvene, og navnet i
    navnekolonnen vært usynlig."""
    orgnr, navn = lister
    monkeypatch.setattr(vakt, "hviteliste", lambda: (orgnr, navn))
    monkeypatch.setattr(vakt, "_snapshotrammer", lambda: iter(()))
    (tmp_path / "serie.csv").write_text(
        _csv("navn,verdi", "Kari Nordmann,1"), encoding="utf-8")

    funn = [f for f in vakt.gransk(tmp_path) if f.fil == "serie.csv"]
    assert [f.slag for f in funn] == ["ukjent_navn"]


# ---- porten hører IKKE hjemme her, og det er målt --------------------

def test_porten_kan_ikke_vaere_en_pytest_test():
    """Suiten er med VILJE blind for ekte data. Porten kan ikke være det.

    `tests/conftest.py` setter `HAVBRUK_DATA_DIR` til en engangsmappe før
    pytest importerer noen testmodul — sikkerhetsnettet som gjør det
    umulig for en test å skrive til datarepoet. Følgen er at `RAW_DIR`
    er TOM inne i suiten.

    Et forsøk på å legge porten her ble kjørt 15.09.2026 mot ekte
    `oversikt.html`: hvitelista ble bygget av en tom mappe, og hvert
    eneste orgnummer i fila meldte seg som `ukjent_orgnr`. Porten var
    ikke streng — den var blind, og ville felt hver publisering.

    De to kravene er uforenlige, og begge er riktige:

      * suiten skal ALDRI kunne lese eller skrive ekte data
      * porten skal ALLTID lese ekte data

    Derfor er porten en kommando og ikke en test:

        python publiseringsvakt.py <mappe>     # exit 1 ved funn

    Denne testen står som en sperre mot at noen legger den inn igjen.
    """
    import tests.conftest as conftest

    assert conftest._TEST_DATA_DIR, "conftest skal peke bort fra ekte data"
    assert os.environ["HAVBRUK_DATA_DIR"] == conftest._TEST_DATA_DIR

    # ... og konsekvensen, målt her og ikke antatt:
    orgnr, navn = vakt.hviteliste()
    assert not orgnr and not navn, (
        "hvitelista er ikke tom inne i suiten. Da har conftest sluttet å "
        "isolere, eller vakten leser utenom RAW_DIR — begge deler skal "
        "undersøkes før porten flyttes hit."
    )


def test_kommandolinja_returnerer_1_ved_funn(tmp_path, snapshotmappe, capsys):
    """Exit-koden ER porten. En byggejobb stopper på den."""
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "lekk.html").write_text(
        _side('<td>998877665</td><td>ENK</td>'), encoding="utf-8")

    monkey = pytest.MonkeyPatch()
    monkey.setattr(sys, "argv", ["publiseringsvakt.py", str(ut)])
    try:
        assert vakt.main() == 1
    finally:
        monkey.undo()
    assert "PUBLISERING STOPPET" in capsys.readouterr().out


def test_kommandolinja_returnerer_0_paa_rent_utputt(tmp_path, snapshotmappe):
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "ok.html").write_text(
        _side('<td>912345678</td><td>AS</td>'), encoding="utf-8")

    monkey = pytest.MonkeyPatch()
    monkey.setattr(sys, "argv", ["publiseringsvakt.py", str(ut)])
    try:
        assert vakt.main() == 0
    finally:
        monkey.undo()


# ---- regelen: hvilke datoer hvitelista leser ---------------------------
#
# Erklært av KILDEN (`Source.partisjonering`), ikke valgt av vakten.
# Fram til 19.09.2026 leste hvitelista nyeste dato for alle kilder, og
# det ga 961 av 1030 portfunn: generatoren leser alle 21 årgangene av
# `eierskap_historikk`, hvitelista bare 2026-fila.


def _flerdato(rot, kilde, datoer_og_navn, partisjonering="verden"):
    """Skriver ett snapshot per (dato, navn) og erklærer partisjonen."""
    from core.contract import Source

    mappe = rot / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    for dato, navn in datoer_og_navn:
        rader = [Observation(
            entity_id="912345678", entity_type="selskap", entity_name="",
            field="navn", value=navn, source=kilde, observed_at=dato,
            fetched_at=f"{dato}T10:00:00+00:00")]
        pl.DataFrame([o.as_dict() for o in rader]).write_parquet(
            mappe / f"{dato}.parquet")

    class Kilden(Source):
        name = kilde
    Kilden.partisjonering = partisjonering
    return Kilden()


def test_verden_kilde_leses_over_ALLE_datoer(tmp_path, monkeypatch):
    """21 årganger er 21 tidsrom som gjelder samtidig, ikke 20 utdaterte."""
    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    kilde = _flerdato(rot, "historikk", [("2009-12-31", "Gammelt Navn AS"),
                                         ("2026-12-31", "Nytt Navn AS")])
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"historikk": "verden"}, {"historikk": kilde}))

    _orgnr, navn = vakt.hviteliste()
    assert {"Gammelt Navn AS", "Nytt Navn AS"} <= navn


def test_henting_kilde_leses_bare_paa_NYESTE_dato(tmp_path, monkeypatch):
    """Forrige ukes uttrekk er utdatert, ikke et annet tidsrom. Et navn
    som forsvant ut av registeret skal ikke være gjort rede for."""
    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    kilde = _flerdato(rot, "register", [("2026-09-07", "Forsvant AS"),
                                        ("2026-09-14", "Finnes AS")],
                      partisjonering="henting")
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"register": "henting"}, {"register": kilde}))

    _orgnr, navn = vakt.hviteliste()
    assert "Finnes AS" in navn
    assert "Forsvant AS" not in navn


def test_uerklaert_kilde_leses_som_den_STRENGESTE(tmp_path, monkeypatch):
    """«Vet ikke» gir nyeste dato alene — og et eget funn, se
    `test_uerklaert_partisjon_er_et_funn`."""
    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    kilde = _flerdato(rot, "taus", [("2026-09-07", "Gammel AS"),
                                    ("2026-09-14", "Ny AS")],
                      partisjonering="")
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"taus": ""}, {"taus": kilde}))

    _orgnr, navn = vakt.hviteliste()
    assert "Gammel AS" not in navn


def test_datoene_er_regelen_paa_ett_sted(tmp_path, monkeypatch):
    """Regelen er én funksjon, og den svarer på alle tre tilstandene.

    To steder som skal si det samme om hvilke datoer som leses, er formen
    F6 og F7 hadde — derfor spør både `_snapshotrammer()` og enhver
    framtidig leser denne."""
    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    _flerdato(rot, "kilde", [("2009-12-31", "A"), ("2026-12-31", "B")])

    assert vakt._datoene("kilde", "verden") == ["2009-12-31", "2026-12-31"]
    assert vakt._datoene("kilde", "henting") == ["2026-12-31"]
    assert vakt._datoene("kilde", "") == ["2026-12-31"]
    assert vakt._datoene("finnes_ikke", "verden") == []
    assert vakt._datoene("finnes_ikke", "henting") == []


# ---- kildens eget tillegg til døra -------------------------------------

def test_kildens_eget_filter_holdes_UTE_av_hvitelista(tmp_path, monkeypatch):
    """`fjern_egne_personer()` er tillegget for det døra ikke ser.

    MÅLT: døra fjerner 0 av 36 360 rader fra eierskap_historikk, fordi
    kilden skriver 0 `organisasjonsform` og 0 sektorkode. Uten tillegget
    ville hvitelista GJORT REDE FOR mottakerne i stedet for å filtrere
    dem — stillhet kjøpt for sikkerhet, og porten ville sagt grønt."""
    from core.contract import Source

    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    _flerdato(rot, "historikk", [("2009-12-31", "Hansen og Olsen DA")])

    class MedTillegg(Source):
        name = "historikk"
        partisjonering = "verden"

        def fjern_egne_personer(self, frame):
            return frame.filter(pl.col("value") != "Hansen og Olsen DA")

    kilde = MedTillegg()
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"historikk": "verden"}, {"historikk": kilde}))

    _orgnr, navn = vakt.hviteliste()
    assert "Hansen og Olsen DA" not in navn, (
        "kilden filtrerte raden, og hvitelista gjorde likevel rede for navnet")


def test_et_tillegg_som_LEGGER_TIL_rader_felles(tmp_path, monkeypatch):
    """Hooken er et tillegg til døra og kan bare fjerne. En hviteliste
    bygget av flere rader enn dataene har, gjør rede for noe som ikke er
    der."""
    from core.contract import Source

    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    _flerdato(rot, "historikk", [("2009-12-31", "Noe AS")])

    class Legger(Source):
        name = "historikk"
        partisjonering = "verden"

        def fjern_egne_personer(self, frame):
            return pl.concat([frame, frame])

    kilde = Legger()
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"historikk": "verden"}, {"historikk": kilde}))

    with pytest.raises(ValueError, match="filtrere, ikke legge til"):
        vakt.hviteliste()


# ---- grunnlaget: stemmer erklæringen med dataene? ---------------------
#
# Den viktigste prøven i denne fila, fordi den er den ENESTE som kan
# felle den stille feilretningen. En «verden»-kilde som erklærer seg
# «henting» gir støyende funn; en «henting»-kilde som erklærer seg
# «verden» gir en for stor hviteliste, og da PASSERER et navn som
# forsvant ut av registeret for et år siden.


def _medavvik(rot, kilde, par):
    """Snapshots med styrt avvik: (observed_at, fetched_at-dato)."""
    mappe = rot / kilde
    mappe.mkdir(parents=True, exist_ok=True)
    for observed, hentet in par:
        rader = [Observation(
            entity_id="912345678", entity_type="selskap", entity_name="",
            field="navn", value="Noe AS", source=kilde,
            observed_at=observed, fetched_at=f"{hentet}T10:00:00+00:00")]
        pl.DataFrame([o.as_dict() for o in rader]).write_parquet(
            mappe / f"{observed}.parquet")


@pytest.fixture
def grunnlag(tmp_path, monkeypatch):
    rot = tmp_path / "raw"
    rot.mkdir()
    monkeypatch.setattr(snapshot, "RAW_DIR", rot)
    monkeypatch.setattr(vakt, "RAW_DIR", rot)
    return rot


def test_henting_som_er_verden_felles(grunnlag, monkeypatch):
    """Den STØYENDE retningen. Ett snapshot som gjelder for et annet
    tidsrom enn hentingen motsier «henting» — ingen terskel trengs, for
    påstanden er at de ALLTID faller sammen."""
    _medavvik(grunnlag, "kilde", [("2026-09-14", "2026-09-14"),
                                  ("2012-01-02", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"kilde": "henting"}, {}))

    funn = vakt.grunnlagsfunn()
    assert [f.slag for f in funn] == ["feilerklaert_partisjon"]
    assert "erklært «henting»" in funn[0].utdrag


def test_verden_som_er_henting_felles(grunnlag, monkeypatch):
    """DEN STILLE RETNINGEN, og grunnen til at prøven finnes.

    Alle snapshots datert dagen de ble hentet — da er «verden» en påstand
    dataene ikke bærer, og hvitelista ville gjort rede for hvert navn
    kilden noensinne har hatt."""
    _medavvik(grunnlag, "kilde", [("2026-09-07", "2026-09-07"),
                                  ("2026-09-14", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"kilde": "verden"}, {}))

    funn = vakt.grunnlagsfunn()
    assert [f.slag for f in funn] == ["feilerklaert_partisjon"]
    assert "erklært «verden»" in funn[0].utdrag


def test_ETT_snapshot_kan_ikke_motbevise_verden(grunnlag, monkeypatch):
    """Med ett snapshot er 0 dagers avvik uinformativt: en kilde hentet
    samme dag som tidsrommet den gjelder for ser ut som en henting-kilde,
    og det er fravær av grunnlag — ikke en feil erklæring. En vakt som
    feller på det, feller en ny kilde på dens første kjøring."""
    _medavvik(grunnlag, "kilde", [("2026-09-14", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"kilde": "verden"}, {}))

    assert vakt.grunnlagsfunn() == []


def test_snapshot_uten_fetched_at_feller_ingenting(grunnlag, monkeypatch):
    """Snapshots skrevet før `fetched_at` fantes kan ikke måles. Fravær
    av et tidsstempel er ikke en feil erklæring — enhetsregisteret har
    ett slikt snapshot (2026-08-16), og det skal ikke felle noe."""
    mappe = grunnlag / "kilde"
    mappe.mkdir(parents=True)
    rader = [Observation(entity_id="912345678", entity_type="selskap",
                         entity_name="", field="navn", value="Noe AS",
                         source="kilde", observed_at="2026-09-14")]
    pl.DataFrame([o.as_dict() for o in rader]).write_parquet(
        mappe / "2026-09-14.parquet")
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"kilde": "henting"}, {}))

    assert vakt.grunnlagsfunn() == []


def test_uerklaert_partisjon_er_et_funn(grunnlag, monkeypatch):
    """Stillhet skal ikke belønnes. En ny kilde som glemmer erklæringen
    stopper publiseringen, akkurat som en UBELAGT attribusjon gjør."""
    _medavvik(grunnlag, "kilde", [("2026-09-14", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene", lambda: ({"kilde": ""}, {}))

    funn = vakt.grunnlagsfunn()
    assert [f.slag for f in funn] == ["ukjent_partisjon"]


def test_mappe_uten_kilde_er_ogsaa_ukjent_partisjon(grunnlag, monkeypatch):
    """En mappe i data/raw/ som ingen kilde skriver under kan ikke svare
    på spørsmålet i det hele tatt. Samme form som en attribusjon uten
    kilde: det er ingen som har gått god for noe."""
    _medavvik(grunnlag, "foreldrelos", [("2026-09-14", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene", lambda: ({}, {}))

    funn = vakt.grunnlagsfunn()
    assert [f.slag for f in funn] == ["ukjent_partisjon"]
    assert "ingen kilde" in funn[0].utdrag


def test_riktig_erklaering_gir_ingen_grunnlagsfunn(grunnlag, monkeypatch):
    _medavvik(grunnlag, "verden_kilde", [("2012-01-02", "2026-09-14"),
                                         ("2026-08-17", "2026-09-14")])
    _medavvik(grunnlag, "henting_kilde", [("2026-09-07", "2026-09-07"),
                                          ("2026-09-14", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"verden_kilde": "verden",
                                  "henting_kilde": "henting"}, {}))

    assert vakt.grunnlagsfunn() == []


def test_gransk_tar_grunnlagsfunnene_med(tmp_path, grunnlag, monkeypatch):
    """Exit-koden skal dekke begge: en hviteliste bygget på en feil
    erklæring gjør rede for noe den ikke har sett, og et grønt bygg på
    den er verre enn et rødt."""
    _medavvik(grunnlag, "kilde", [("2026-09-07", "2026-09-07"),
                                  ("2026-09-14", "2026-09-14")])
    monkeypatch.setattr(vakt, "_erklaeringene",
                        lambda: ({"kilde": "verden"}, {}))

    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "ren.html").write_text("<p>ingenting</p>", encoding="utf-8")

    funn = vakt.gransk(ut)
    assert [f.slag for f in funn] == ["feilerklaert_partisjon"]


# ---- kvitteringene -----------------------------------------------------
#
# En kvittering er en PÅSTAND om at funnet er forstått, ikke en bryter
# som gjør vakten stille. Samme form som `health.godta_volum()`: en verdi
# skrevet til en fil som committes, med begrunnelse, dato og hvem.
#
# Den kvitterer ut ETT FUNN — (felt, signaturen til verdien) — og aldri
# et SLAG. Kvitteres «personform» som helhet, passerer et femte navn i
# stillhet, og det er nøyaktig den feilen kvitteringen ikke skal kunne
# gjøre.

def _kvittering(tmp_path, monkeypatch, saker, dato="2026-09-19",
                av="Heine Nordboe", grunn="Målt, se notatet.",
                filnavn=None):
    import json

    mappe = tmp_path / "kvitteringer"
    mappe.mkdir(exist_ok=True)
    (mappe / (filnavn or f"{dato}.json")).write_text(json.dumps({
        "dato": dato, "kvittert_av": av, "begrunnelse": grunn,
        "saker": saker}), encoding="utf-8")
    monkeypatch.setattr(vakt, "KVITTERING_DIR", mappe)
    return mappe


def _sak(navn, felt="tildelt_navn", **resten):
    return {"felt": felt, "navn": navn,
            "navn_signatur": vakt._signatur(navn), **resten}


def test_kvittert_funn_staar_i_rapporten_men_feller_ikke(lister, tmp_path,
                                                         monkeypatch):
    """Begge halvdeler i én test, fordi det er de to sammen som er
    forskjellen på en kvittering og en bryter."""
    orgnr, navn = lister
    _kvittering(tmp_path, monkeypatch, [_sak("Hansen og Olsen ANS")])
    side = _side('<td data-felt="tildelt_navn">Hansen og Olsen ANS</td>')

    funn = vakt.gransk_tekst(side, orgnr, navn | {"Hansen og Olsen ANS"},
                             kvittert=vakt.kvitteringer())
    personform = [f for f in funn if f.slag == "personform"]
    assert len(personform) == 1, "funnet skal STÅ"
    assert personform[0].kvittert.startswith("2026-09-19")
    assert vakt.ukvittert(funn) == [], "og det skal ikke felle porten"


def test_en_FEMTE_verdi_i_samme_felt_feller_fortsatt(lister, tmp_path,
                                                     monkeypatch):
    """Hele grunnen til at nøkkelen er verdien og ikke slaget."""
    orgnr, navn = lister
    _kvittering(tmp_path, monkeypatch, [_sak("Hansen og Olsen ANS")])
    side = _side('<td data-felt="tildelt_navn">Hansen og Olsen ANS</td>'
                 '<td data-felt="tildelt_navn">Straumen og Vik ANS</td>')

    funn = vakt.gransk_tekst(side, orgnr,
                             navn | {"Hansen og Olsen ANS",
                                     "Straumen og Vik ANS"},
                             kvittert=vakt.kvitteringer())
    igjen = vakt.ukvittert(funn)
    assert [f.slag for f in igjen] == ["personform"]
    assert "#1" not in igjen[0].utdrag  # signaturen, ikke navnet
    assert igjen[0].kvittert == ""


def test_kvitteringen_gjelder_ETT_felt(lister, tmp_path, monkeypatch):
    """Samme verdi i et annet felt er et annet funn. `tildelt_navn` er en
    historisk tildelingsopplysning; `eier_navn` er dagens eier, og de to
    er ikke samme påstand om verden."""
    orgnr, navn = lister
    _kvittering(tmp_path, monkeypatch, [_sak("Hansen og Olsen ANS")])
    side = _side('<td data-felt="eier_navn">Hansen og Olsen ANS</td>')

    funn = vakt.gransk_tekst(side, orgnr, navn | {"Hansen og Olsen ANS"},
                             kvittert=vakt.kvitteringer())
    assert len(vakt.ukvittert(funn)) == 1


def test_ingen_kvitteringer_er_standarden(lister, tmp_path, monkeypatch):
    """En kaller som ikke har lest kvitteringene får dem ikke gratis."""
    orgnr, navn = lister
    _kvittering(tmp_path, monkeypatch, [_sak("Hansen og Olsen ANS")])
    side = _side('<td data-felt="tildelt_navn">Hansen og Olsen ANS</td>')

    funn = vakt.gransk_tekst(side, orgnr, navn | {"Hansen og Olsen ANS"})
    assert all(not f.kvittert for f in funn)


def test_kvittering_uten_begrunnelse_eller_navn_kaster(tmp_path, monkeypatch):
    """En kvittering uten hvem og hvorfor er et flagg. Da er den ikke en
    påstand noen har gått god for, og den skal ikke kunne leses."""
    for manglende in ("av", "grunn"):
        felter = {"av": "Noen", "grunn": "Fordi."}
        felter[manglende] = ""
        _kvittering(tmp_path, monkeypatch, [_sak("Hansen og Olsen ANS")],
                    **felter)
        with pytest.raises(ValueError, match="flagg, ikke en kvittering"):
            vakt.kvitteringer()


def test_signatur_som_ikke_horer_til_navnet_kaster(tmp_path, monkeypatch):
    """Fila er håndskrevet. En kvittering som oppgir navn A og signaturen
    til navn B ville kvittert ut et funn ingen har lest."""
    sak = _sak("Hansen og Olsen ANS")
    sak["navn_signatur"] = vakt._signatur("Et helt annet navn AS")
    _kvittering(tmp_path, monkeypatch, [sak])

    with pytest.raises(ValueError, match="hører ikke til"):
        vakt.kvitteringer()


def test_kvitteringen_kan_TREKKES_av_en_nyere_fil(tmp_path, monkeypatch):
    """Append-only: veien tilbake er en ny fil, ikke en sletting. En
    trukket kvittering skal kunne leses i ettertid."""
    import json

    mappe = _kvittering(tmp_path, monkeypatch, [_sak("Hansen og Olsen ANS")])
    assert len(vakt.kvitteringer()) == 1

    sak = _sak("Hansen og Olsen ANS")
    sak["status"] = "trukket"
    (mappe / "2026-09-26.json").write_text(json.dumps({
        "dato": "2026-09-26", "kvittert_av": "Heine Nordboe",
        "begrunnelse": "Trukket: Brreg-oppslaget gjorde spørsmålet målbart.",
        "saker": [sak]}), encoding="utf-8")

    assert vakt.kvitteringer() == {}


def test_lopenummer_sorteres_som_snapshotene(tmp_path, monkeypatch):
    """`.10` skal komme etter `.2`, ikke mellom `.1` og `.2`. Samme
    sortering som `snapshot.versjoner()`, og samme grunn: rekkefølgen
    avgjør hvilken kvittering som gjelder."""
    assert vakt._dato_og_nummer("2026-09-19") == ("2026-09-19", 1)
    assert vakt._dato_og_nummer("2026-09-19.2") == ("2026-09-19", 2)
    assert (vakt._dato_og_nummer("2026-09-19.10")
            > vakt._dato_og_nummer("2026-09-19.2"))


def test_personformkoden_attribueres_til_feltmerket_verdi(lister):
    """Attribusjonen er det som gjør et funn kvitterbart i det hele tatt.

    «fila inneholder ordet ANS» kan bare kvitteres som et SLAG. «denne
    verdien i dette feltet» kan kvitteres som ETT funn."""
    orgnr, navn = lister
    side = _side('<td data-felt="tildelt_navn">Hansen og Olsen ANS</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn | {"Hansen og Olsen ANS"})

    personform = [f for f in funn if f.slag == "personform"]
    assert len(personform) == 1
    assert personform[0].utdrag.startswith("tildelt_navn ")
    assert personform[0].noekkel == f"tildelt_navn/{vakt._signatur('Hansen og Olsen ANS')}"
    # Navnet står IKKE i rapporten.
    assert "Hansen" not in str(personform[0])


def test_tvetydig_kode_i_et_NAVNEFELT_felles(lister):
    """`DA` er dekar i en `kapasitet_enhet`-celle, og delt ansvar som
    siste ord i et navnefelt. Merkingen sier hvilket av de to det er, og
    da trengs ikke tekstvinduet."""
    orgnr, navn = lister
    side = _side('<td data-felt="tildelt_navn">Hansen og Olsen DA</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn | {"Hansen og Olsen DA"},
                             tvetydige={"DA"})
    assert [f.slag for f in funn] == ["personform"]

    areal = _side('<td data-felt="kapasitet_enhet">DA</td>')
    assert vakt.gransk_tekst(areal, orgnr, navn, tvetydige={"DA"}) == []


def test_attribuert_treff_telles_ikke_dobbelt(lister):
    """Koden inne i en merket verdi skal meldes ÉN gang, ikke både som
    attribuert funn og som løs kode i teksten."""
    orgnr, navn = lister
    side = _side('<td data-felt="tildelt_navn">Hansen og Olsen ANS</td>')
    funn = vakt.gransk_tekst(side, orgnr, navn | {"Hansen og Olsen ANS"})
    assert len([f for f in funn if f.slag == "personform"]) == 1


def test_umerket_personformkode_meldes_fortsatt_som_slag(lister):
    """Det som ikke kan attribueres, kan ikke kvitteres — og skal
    fortsatt meldes. Ellers ville merkingen blitt en vei til å gjøre et
    funn usynlig."""
    orgnr, navn = lister
    side = _side("<p>Foretaket er et ENK.</p>")
    funn = vakt.gransk_tekst(side, orgnr, navn)
    personform = [f for f in funn if f.slag == "personform"]
    assert personform and personform[0].utdrag == "['ENK']"
    assert personform[0].noekkel == ""


# ---- kassen ------------------------------------------------------------
#
# Fra 22.09.2026 står lokalitetsnavnet i tittelform i H1 mens snapshotet
# har det i versaler. Prøvene under er de to sidene av den endringen: at
# den ene skrivemåten møter den andre, og at det IKKE gjør et ukjent
# navn kjent.

def test_tittelform_i_h1_meldes_ikke_naar_versalen_staar_i_dataene():
    """Uten dette ville hver av de 1 782 lokalitetssidene meldt sitt
    eget navn. En vakt som feiler 1 782 ganger på noe som er gjort rede
    for, blir slått av — samme begrunnelse som `_celleverdi()`."""
    navn_ok = {vakt.navnenoekkel("OTERNESET")}
    html = '<h1>Lokalitet 31397 <span data-navn>Oterneset</span></h1>'
    assert vakt.gransk_tekst(html, set(), navn_ok) == []


def test_kassen_gjor_ikke_et_ukjent_navn_kjent():
    """Hullet dette ikke åpner. `casefold()` kan få to skrivemåter av
    den SAMME strengen til å møtes; det kan ikke føre en ny streng inn i
    hvitelista."""
    navn_ok = {vakt.navnenoekkel("OTERNESET")}
    for skrivemaate in ("Kari Nordmann", "KARI NORDMANN", "kari nordmann"):
        html = f'<td data-felt="eier_navn">{skrivemaate}</td>'
        funn = vakt.gransk_tekst(html, set(), navn_ok)
        assert [f.slag for f in funn] == ["ukjent_navn"], skrivemaate


def test_kassen_gjelder_i_csv_ogsaa():
    """To lesemåter av samme spørsmål som kan svare ulikt, er formen F6
    og F7 hadde. CSV-en bruker kolonneoverskriften som merking, men
    stiller det samme spørsmålet."""
    navn_ok = {vakt.navnenoekkel("OTERNESET")}
    csv_ = "navn,kommune\nOterneset,Gulen\n"
    assert vakt.gransk_csv(csv_, set(), navn_ok) == []
    csv_ukjent = "navn,kommune\nEt Annet Sted,Gulen\n"
    funn = vakt.gransk_csv(csv_ukjent, set(), navn_ok)
    assert [f.slag for f in funn] == ["ukjent_navn"]
