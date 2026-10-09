"""Unntaksvekst — søkerfilteret, koblingsregelen og tabellparseren.

Søkernavnet er det eneste i lista som kan peke på et menneske. Testene
passer på at det bare slipper gjennom med et entydig orgnr og en
selskapsform, i BEGGE lag.
"""

import pytest

from sources import unntaksvekst as u
from sources.unntaksvekst import Unntaksvekst

HTML = """<html><body><p>Mattilsynet mottok 4 søknader</p>
<table class="x"><thead><tr><th>Søker</th><th>Lokalitet</th>
<th>Prod.område</th><th>Resultat</th><th>Saksnummer</th></tr></thead>
<tbody>
<tr><td>Lingalaks</td><td>Andal</td><td>3</td><td>Avslag</td><td>2025/216602</td></tr>
<tr><td>Marø Havbruk og E. Karstensen Fiskeoppdrett</td><td>Gnarnesvika</td>
<td>4</td><td>Godkjent</td><td>2025/267293<br>2025/267015</td></tr>
<tr><td>Hansen Fisk</td><td>Hamnsundet</td><td>8</td><td>Godkjent</td><td>2025/1, 2025/2</td></tr>
<tr><td>Sjøtroll Havbruk</td><td>Djupevika</td><td>3</td><td>Godkjent</td><td>2025/284150</td></tr>
</tbody></table></body></html>"""

ENHETER = [
    {"name": "LINGALAKS AS", "typeValue": "LimitedLiabilityCompany", "openNr": "960900626"},
    {"name": "HANSEN FISK", "typeValue": "SoleProprietorship", "openNr": "999999999"},
    {"name": "SJØTROLL HAVBRUK AS", "typeValue": "LimitedLiabilityCompany", "openNr": "929363833"},
]

LOKALITETER = [
    {"nr": "1", "navn": "ANDAL", "po": "3"},
    {"nr": "2", "navn": "GNARNESVIKA", "po": "4"},
    {"nr": "3", "navn": "HAMNSUNDET I", "po": "8"},
    {"nr": "4", "navn": "DJUPEVIKA", "po": "3"},
    {"nr": "5", "navn": "DJUPEVIKA", "po": "3"},
    {"nr": "6", "navn": "ANDAL", "po": "9"},
]


def _rader(eiere=None):
    return u.bygg_rader(u.les_tabell(HTML), ENHETER, LOKALITETER, eiere or {})


# ---------------------------------------------------------- tabellen

def test_tabellen_leses_med_begge_saksnummerformer():
    t = u.les_tabell(HTML)
    assert len(t) == 4
    assert t[1]["saksnumre"] == ["2025/267015", "2025/267293"]
    assert t[2]["saksnumre"] == ["2025/1", "2025/2"]


def test_endret_tabellhode_kaster():
    with pytest.raises(ValueError, match="tabeller med kolonnene"):
        u.les_tabell(HTML.replace("<th>Resultat</th>", "<th>Vedtak</th>"))


def test_tom_tabell_kaster_i_stedet_for_tomt_snapshot():
    tom = HTML.split("<tbody>")[0] + "<tbody></tbody></table>"
    with pytest.raises(ValueError, match="ingen rader"):
        u.les_tabell(tom)


# ------------------------------------------------------------ søkeren

def test_entydig_aksjeselskap_beholdes():
    assert u.koble_soker("Lingalaks", ENHETER)["orgnr"] == "960900626"


def test_enkeltpersonforetak_utelates():
    assert u.koble_soker("Hansen Fisk", ENHETER) is None


def test_ukjent_navn_utelates():
    assert u.koble_soker("Marø Havbruk og E. Karstensen Fiskeoppdrett",
                         ENHETER) is None


def test_navn_som_deles_med_en_person_er_flertydig_og_utelates():
    """Personen står i kandidatlista nettopp for dette."""
    enheter = ENHETER + [{"name": "Lingalaks", "typeValue": "Person",
                          "openNr": None}]
    assert u.koble_soker("Lingalaks", enheter) is None


def test_ingen_prefiks_eller_likhet_i_soekerkoblingen():
    """«Sjøtroll Havbruk» er ikke «SJØTROLL HAVBRUK SJØ AS»."""
    enheter = [{"name": "SJØTROLL HAVBRUK SJØ AS",
                "typeValue": "LimitedLiabilityCompany", "openNr": "111111111"}]
    assert u.koble_soker("Sjøtroll Havbruk", enheter) is None


def test_lag1_arkivet_baerer_ikke_utelatte_navn():
    t = repr(_rader())
    assert "Hansen" not in t
    assert "Karstensen" not in t
    assert "Lingalaks" in t


def test_lag2_stopper_soeker_uten_selskapsform_i_arkivert_kropp():
    """En kropp arkivert før filteret, eller med en personform, skal
    ikke slippe søkeren gjennom parse()."""
    rader = _rader()
    rader[2].update(soker="Hansen Fisk", soker_orgnr="999999999",
                    organisasjonsform="ENK")
    rader[1].update(soker="Marø Havbruk og E. Karstensen Fiskeoppdrett")
    obs = list(Unntaksvekst().parse({"rader": rader}, "2026-10-12"))
    t = repr(obs)
    assert "Hansen" not in t and "Karstensen" not in t
    utelatt = {o.entity_id: o.value for o in obs if o.field == "soker_utelatt"}
    assert sorted(utelatt.values()) == ["ja", "ja", "nei", "nei"]


# --------------------------------------------------------- lokaliteten

def test_koblingsregelen():
    k = {r["lokalitet"]: r for r in _rader()}
    assert (k["Andal"]["kobling"], k["Andal"]["lokalitet_nr"]) == ("entydig", "1")
    assert (k["Hamnsundet"]["kobling"], k["Hamnsundet"]["lokalitet_nr"]) == ("usikker", "3")
    assert k["Djupevika"]["kobling"] == "flertydig"
    assert k["Djupevika"]["lokalitet_nr"] == ""


def test_flertydig_loeses_via_soekerens_tillatelse():
    k = {r["lokalitet"]: r for r in _rader({"5": {"929363833"}})}
    assert (k["Djupevika"]["kobling"], k["Djupevika"]["lokalitet_nr"]) == ("via_soker", "5")


def test_navn_i_annen_po_kobles_ikke():
    r = u.koble_lokalitet("Andal", "4", LOKALITETER, {})
    assert r["kobling"] == "annen_po" and r["lokalitet_nr"] == ""


@pytest.mark.parametrize("a,b", [
    ("Skysselvika Vest", "SKYSSELVIKA V"), ("Øksengården", "ØKSENGÅRD"),
    ("Gourtesjokah", "GOURTESJOUKA"), ("Hundsholmen", "HUNDHOLMEN"),
    ("Kvaløy", "KVALØY Ø"), ("Teigland", "TEIGLAND I"),
])
def test_maalingens_skrivevarianter_gjenkjennes(a, b):
    assert u._skrivevariant(a, b)


def test_saltkjelen_1_er_flertydig_ikke_gjettet():
    lok = [{"nr": "12973", "navn": "SALTKJELEN I", "po": "3"},
           {"nr": "12019", "navn": "SALTKJELEN II", "po": "3"}]
    assert u.koble_lokalitet("Saltkjelen 1", "3", lok, {})["kobling"] == "flertydig"


# ------------------------------------------------------------- parse

def test_parse_gir_unike_noekler_og_ingen_published_at():
    k = Unntaksvekst()
    obs = list(k.parse({"rader": _rader()}, "2026-10-12"))
    assert len({o.entity_id for o in obs}) == 4
    assert k.published_at == ""
    felt = {(o.entity_id, o.field): o.value for o in obs}
    eid = "2025/216602|ANDAL|PO3"
    assert felt[(eid, "soker_orgnr")] == "960900626"
    assert felt[(eid, "organisasjonsform")] == "AS"
    assert felt[(eid, "lokalitet_nr")] == "1"


def test_dobbel_noekkel_kaster():
    rader = _rader()
    with pytest.raises(ValueError, match="to ganger"):
        list(Unntaksvekst().parse({"rader": rader + rader[:1]}, "2026-10-12"))
