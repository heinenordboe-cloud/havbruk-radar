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


# ---- filer vakten ikke kan lese ---------------------------------------

def test_ulesbar_fil_rapporteres_ikke_antas_trygg(tmp_path,
                                                 snapshotmappe):
    """En .parquet ved siden av sida er like publisert som HTML-en."""
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "data.parquet").write_bytes(b"PAR1binaertsoppel")
    funn = vakt.gransk(ut)
    assert [f.slag for f in funn] == ["ugranska"]


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
