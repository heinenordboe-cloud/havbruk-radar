"""Reguleringsområdekilden. Ingen nett og ingen ekte NMDC- eller hi.no-svar.

Kroppene under er bygget av den faktiske formen slik kilden så den
09.09.2026 — samme geojson-struktur (MultiPolygon med én ring,
egenskapene `regomr`/`prodomr`/`numregomr`), og samme ikke-standard
WKT som appendiks 7.1 faktisk skriver: `POLYGON((x, y), (x, y), ...)`.

Det er med vilje. Skriver man WKT-en av «riktig» på nytt, tester man
sin egen antakelse om formatet i stedet for formatet — og det er
nøyaktig den feilen dette repoet har gjort fire ganger.

De viktigste testene her er `test_nekter_*`. En stille revisjon hos HI
ser ut som en vellykket kjøring; det eneste som gjør den høylytt er at
kroppen må BEKREFTE datoen og versjonen snapshotet skal hete.
"""

import json

import pytest

from sources import reguleringsomraader as ro
from sources.reguleringsomraader import (Formatfeil, Nyutgivelse,
                                         Reguleringsomraader)


# ---- kropper ----------------------------------------------------------

# Et kvadrat rundt (6,0 Ø, 62,0 N) — i sjøen utenfor Møre, slik at
# «kjent posisjon»-testen har noe å treffe.
RUTE = [(5.0, 61.0), (7.0, 61.0), (7.0, 63.0), (5.0, 63.0), (5.0, 61.0)]


def _feature(navn: str, po: int, nr: int, ring=RUTE) -> dict:
    return {
        "type": "Feature",
        "properties": {"regomr": navn, "prodomr": po, "numregomr": nr},
        "geometry": {"type": "MultiPolygon", "coordinates": [[list(
            [list(p) for p in ring])]]},
    }


def _geojson(features=None, navn: str = "regomr_v3") -> str:
    """Alle 28 områdene, med samme rute om ikke annet er sagt."""
    if features is None:
        features = [
            _feature(n, int(n[:-1]), int(n[:-1]) * 10 + (ord(n[-1]) - 64))
            for n in ro.OMRAADER
        ]
    return json.dumps(
        {"type": "FeatureCollection", "name": navn, "features": features}
    )


def _wkt_avsnitt(navn: str, ring=RUTE, dupliser: bool = True) -> str:
    """Appendiksets egen form: punkt i parentes, komma mellom x og y.

    `dupliser` gjengir at WKT-en i rapporten gjentar sluttpunktet én gang
    for mye — målt på 28 av 28 områder 09.09.2026.
    """
    punkter = list(ring) + ([ring[-1]] if dupliser else [])
    ledd = ", ".join(f"({x:.5f}, {y:.5f})" for x, y in punkter)
    return (f"<p><b>Reguleringsområde {navn}:</b> POLYGON({ledd})</p>")


def _rapport(dato: str = "29.06.2026", avsnitt=None) -> str:
    if avsnitt is None:
        avsnitt = [_wkt_avsnitt(n) for n in ro.OMRAADER]
    return (
        "<html><body>"
        f"<div class='articleinfo'>Publisert: <em>{dato}</em></div>"
        "<h3 id=\"sec-7-1\">7.1 - Koordinater for reguleringsomr&aring;der</h3>"
        + "".join(avsnitt)
        + "</body></html>"
    )


def _raw(**overstyr) -> dict:
    """Råsvaret slik `hent_begge()` bygger det: tre kropper og en header.

    Grensetallrapportene er MED som standard, fordi de er med i
    virkeligheten. En testkropp som utelater dem ville latt en advarsel
    om at de mangler gå upåaktet hen i hver eneste test.
    """
    raw = {"geojson": _geojson(), "rapport": _rapport(),
           "geojson_last_modified": "Fri, 28 Aug 2026 05:00:09 GMT",
           "grensetall_2026-36": _rapport(avsnitt=[]),
           "grensetall_2026-37": _rapport(avsnitt=[])}
    raw.update(overstyr)
    return raw


# ---- det som skal virke -----------------------------------------------

def test_28_omraader_med_alle_felt():
    obs = list(Reguleringsomraader().parse(_raw(), "2026-06-29"))
    assert len({o.entity_id for o in obs}) == 28
    felt = {o.field for o in obs}
    assert felt == {"status", "produksjonsomraade", "omraadenummer",
                    "geometri", "punkter", "bbox", "geometri_bekreftet",
                    "datasett_versjon"}
    assert len(obs) == 28 * len(felt)


def test_status_er_forslag_paa_hver_rad():
    """1b-3: verdien som avgjør hva dataene BETYR ligger PÅ radene.

    Et forslag og en forskrift ser identiske ut som polygoner. Uten dette
    feltet kan et snapshot ikke svare på hvilken av dem det beskriver.
    """
    obs = list(Reguleringsomraader().parse(_raw(), "2026-06-29"))
    status = [o for o in obs if o.field == "status"]
    assert len(status) == 28
    assert {o.value for o in status} == {"forslag"}


def test_produksjonsomraade_utledes_av_navnet():
    obs = list(Reguleringsomraader().parse(_raw(), "2026-06-29"))
    po = {o.entity_id: o.value for o in obs if o.field == "produksjonsomraade"}
    assert po["4A"] == "4" and po["4D"] == "4"
    assert po["13B"] == "13"
    assert po["9A"] == "9"
    # Aggregerbart tilbake til PO-nivå: 13 distinkte, ingen «1» fra «13».
    assert len(set(po.values())) == 13


def test_entity_type_er_ikke_produksjonsomraade():
    """`4A` og `4` skal ikke kunne joines på hverandre ved et uhell."""
    obs = list(Reguleringsomraader().parse(_raw(), "2026-06-29"))
    assert {o.entity_type for o in obs} == {"reguleringsomraade"}


def test_publisert_leses_av_rapporten():
    assert ro.publisert_i(_rapport()) == "2026-06-29"
    # Ikke funnet er tom streng — «vet ikke», ikke hentetidspunktet.
    assert ro.publisert_i("<html>ingen dato</html>") == ""


# ---- kontrollen mot appendikset ----------------------------------------

def test_wkt_og_geojson_enige_tross_avrunding_og_duplikat():
    """De to formatforskjellene er FORMAT, ikke uenighet.

    WKT-en er avrundet til fem desimaler og gjentar sluttpunktet. Begge
    er målt på 28 av 28. En kontroll som ikke regnet dem inn ville meldt
    28 falske avvik og gjort seg selv verdiløs.
    """
    ring = [(5.123456789, 61.987654321), (7.0, 61.0), (7.0, 63.0),
            (5.123456789, 61.987654321)]
    _, omr = ro.les_geojson(_geojson([_feature(n, int(n[:-1]), 1, ring)
                                      for n in ro.OMRAADER]))
    wkt = ro.les_wkt(_rapport(avsnitt=[_wkt_avsnitt(n, ring)
                                       for n in ro.OMRAADER]))
    assert set(ro.sammenlign(omr, wkt).values()) == {"wkt+geojson"}


def test_sprik_rapporteres_og_utlignes_ikke():
    """Uenighet er et FUNN. Geojson lagres uansett — men merket."""
    annen = [(5.0, 61.0), (7.5, 61.0), (7.0, 63.0), (5.0, 61.0)]
    kilde = Reguleringsomraader()
    obs = list(kilde.parse(_raw(rapport=_rapport(
        avsnitt=[_wkt_avsnitt("1A", annen)]
        + [_wkt_avsnitt(n) for n in ro.OMRAADER[1:]])), "2026-06-29"))

    merke = {o.entity_id: o.value
             for o in obs if o.field == "geometri_bekreftet"}
    assert "sprik" in merke["1A"]
    assert merke["1B"] == "wkt+geojson"
    assert any("1A" in a for a in kilde.advarsler)

    # Utlignet ingenting: geometrien som lagres er fortsatt geojsons.
    geo = {o.entity_id: o.value for o in obs if o.field == "geometri"}
    assert "7.500000" not in geo["1A"]


def test_manglende_appendiks_merkes_som_ukontrollert():
    kilde = Reguleringsomraader()
    obs = list(kilde.parse(_raw(rapport=""), "2026-06-29"))
    merker = {o.value for o in obs if o.field == "geometri_bekreftet"}
    assert merker == {"ukontrollert"}
    assert any("ukontrollert" in a for a in kilde.advarsler)


# ---- det som skal NEKTE ------------------------------------------------

def test_nekter_ny_utgivelsesdato():
    """Kroppen BEKREFTER datoen. Er den en annen, er dette en ny utgave."""
    with pytest.raises(Nyutgivelse, match="2026-11-01"):
        list(Reguleringsomraader().parse(
            _raw(rapport=_rapport("01.11.2026")), "2026-06-29"))


def test_nekter_ny_datasettversjon():
    """`regomr_v4` er en stille revisjon. Den skal ikke bli en endringsrad."""
    with pytest.raises(Nyutgivelse, match="regomr_v4"):
        list(Reguleringsomraader().parse(
            _raw(geojson=_geojson(navn="regomr_v4")), "2026-06-29"))


def test_nekter_annet_antall_omraader():
    fs = [_feature(n, int(n[:-1]), 1) for n in ro.OMRAADER[:-1]]
    with pytest.raises(Nyutgivelse, match="13B"):
        list(Reguleringsomraader().parse(_raw(geojson=_geojson(fs)),
                                         "2026-06-29"))


def test_nekter_navn_som_er_uenig_med_prodomr():
    """Gratis kryssjekk: to utsagn om samme ting, i samme fil."""
    fs = [_feature(n, int(n[:-1]), 1) for n in ro.OMRAADER]
    fs[0]["properties"]["prodomr"] = 7        # heter 1A
    with pytest.raises(Formatfeil, match="1A"):
        list(Reguleringsomraader().parse(_raw(geojson=_geojson(fs)),
                                         "2026-06-29"))


def test_nekter_hull_i_polygonet():
    """Et hull som ties i hjel gjør punkt-i-polygon usant, ikke unøyaktig."""
    fs = [_feature(n, int(n[:-1]), 1) for n in ro.OMRAADER]
    fs[0]["geometry"]["coordinates"][0].append(
        [[5.5, 61.5], [6.0, 61.5], [6.0, 62.0], [5.5, 61.5]])
    with pytest.raises(Formatfeil, match="ringer"):
        list(Reguleringsomraader().parse(_raw(geojson=_geojson(fs)),
                                         "2026-06-29"))


def test_nekter_navn_uten_tall():
    with pytest.raises(Formatfeil, match="Nord"):
        ro.produksjonsomraade("Nord")


# ---- geometrien --------------------------------------------------------

def test_koordinatrekkefolgen_er_lengde_saa_bredde():
    """Snudd rekkefølge feiler STILLE for alle punkter. Derfor testes den.

    Ålesund havn ligger i ruta; det samme punktet med koordinatene byttet
    om ligger i Indiahavet.
    """
    _, omr = ro.les_geojson(_geojson())
    treff = [o.navn for o in omr
             if ro.inneholder(o.punkter, 6.1495, 62.4722)]
    assert len(treff) == 28          # alle testområdene deler rute
    snudd = [o.navn for o in omr
             if ro.inneholder(o.punkter, 62.4722, 6.1495)]
    assert snudd == []


def test_punkt_utenfor_treffer_ingen():
    _, omr = ro.les_geojson(_geojson())
    assert not any(ro.inneholder(o.punkter, 10.0, 70.0) for o in omr)


def test_wkt_er_standard_wkt_og_stabil():
    """Formatet er en kontrakt mot historikken, som feltnavnet er det."""
    w = ro.wkt_av([(5.0, 61.0), (7.0, 61.0), (5.0, 61.0)])
    assert w == ("POLYGON((5.000000 61.000000, 7.000000 61.000000, "
                 "5.000000 61.000000))")
    assert ro.wkt_av(RUTE) == ro.wkt_av(RUTE)


def test_bbox_er_vest_sor_ost_nord():
    assert ro.bbox_av(RUTE) == "5.000000,61.000000,7.000000,63.000000"


# ---- kontrakten --------------------------------------------------------

def test_gjelder_for_er_utgivelsen_og_ikke_kjoredatoen():
    k = Reguleringsomraader()
    assert k.gjelder_for("2026-09-09") == "2026-06-29"
    assert k.gjelder_for("2027-01-01") == "2026-06-29"


def test_parse_nekter_gammel_arkivform():
    with pytest.raises(Formatfeil, match="geojson"):
        list(Reguleringsomraader().parse("bare en streng", "2026-06-29"))


# ---- grensetallrapportene: bevart, aldri lest --------------------------

def test_grensetall_blir_ikke_observasjoner():
    """2026-36 og -37 skal ARKIVERES, ikke bli en kilde.

    De ligger i råsvaret og dermed i arkivfila, med samme `raw_hash` og
    `published_at` som de 28 grensene. Ingen rad skal komme ut av dem.
    """
    kilde = Reguleringsomraader()
    obs = list(kilde.parse(_raw(), "2026-06-29"))
    assert len(obs) == 224
    assert {o.entity_id for o in obs} == set(ro.OMRAADER)
    assert kilde.advarsler == []


def test_grensetall_som_ikke_ble_hentet_sier_fra_men_feller_ikke():
    """En hi.no-side som er nede skal ikke koste oss de 28 grensene."""
    kilde = Reguleringsomraader()
    obs = list(kilde.parse(
        _raw(**{"grensetall_2026-36": "__IKKE_HENTET__ HTTPStatusError: 503"}),
        "2026-06-29"))
    assert len(obs) == 224
    assert any("2026-36" in a and "503" in a for a in kilde.advarsler)


def test_grensetall_med_annen_dato_sier_fra():
    """Alle tre ligger under ÉN dato. Da må alle tre oppgi den."""
    kilde = Reguleringsomraader()
    list(kilde.parse(
        _raw(**{"grensetall_2026-36": _rapport("01.11.2026", avsnitt=[])}),
        "2026-06-29"))
    assert any("2026-11-01" in a for a in kilde.advarsler)
