"""Nedlastingene: regnearket og datapakken.

To former av ETT datasett, og de skal si det samme. Testene leser
regnearket med portens egen leser (`publiseringsvakt.xlsx_ark()`), som
leser XML-en og ikke tolker den — så det som prøves er det som står i
fila, ikke et biblioteks lesning av den.
"""

import csv
import hashlib
import io
import json
import zipfile

import pytest

import nedlasting
import nettsted
import publiseringsvakt as vakt
from tests.test_nettsted import datamappe  # noqa: F401 — fiksturen


def _ds(**overstyr) -> nedlasting.Datasett:
    grunn = dict(
        stamme="test",
        tittel="Testdata",
        beskrivelse="Tre rader.",
        kolonner=(
            nedlasting.Kolonne("id", "string", "Et nummer som identifiserer."),
            nedlasting.Kolonne("dato", "date", "Mandagen."),
            nedlasting.Kolonne("uke", "integer", "Ukenummeret."),
            nedlasting.Kolonne("tall", "decimal", "Et tall.", "Ikke oppgitt."),
            nedlasting.Kolonne("flagg", "boolean", "Sant eller usant.",
                               "Ikke oppgitt."),
            nedlasting.Kolonne("navn", "string", "Et navn.", "Ukjent."),
        ),
        rader=[
            {"id": "20797", "dato": "2012-01-02", "uke": "01", "tall": "0.12",
             "flagg": "True", "navn": "URDVIKA"},
            {"id": "20797", "dato": "2012-01-09", "uke": "02", "tall": "",
             "flagg": "False", "navn": ""},
            # Det som IKKE lar seg lese som kolonnens type, og en streng
            # som ville vært en formel om noen lot biblioteket gjette.
            {"id": "00042", "dato": "2012-01-16", "uke": "03",
             "tall": "ikke tall", "flagg": "true", "navn": "=1+1"},
        ],
        kilder=[("BarentsWatch", "NLOD", "https://example.org/vilkar")],
        attribusjon=["Data levert av BarentsWatch"],
        hentet=["Hentet fra BarentsWatch 5. oktober 2026 kl. 04.12 UTC."],
        bygget="2026-10-07",
        merknader=["En merknad."],
        nokkel=("id", "dato"),
    )
    grunn.update(overstyr)
    return nedlasting.Datasett(**grunn)


def _ark(ds) -> dict[str, list[list[str]]]:
    return dict(vakt.xlsx_ark(nedlasting.xlsx_bytes(ds)))


def _celletyper(ds) -> dict[str, str]:
    """{cellereferanse: t-attributtet} for arket «Data»."""
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(io.BytesIO(nedlasting.xlsx_bytes(ds)))
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rot = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    return {c.get("r"): c.get("t", "n") for c in rot.iter(f"{ns}c")}


def _pakke(ds) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(nedlasting.zip_bytes(ds)))


# ---- regnearket --------------------------------------------------------

def test_regnearket_har_to_ark_data_og_om_dataene():
    assert list(_ark(_ds())) == ["Data", "Om dataene"]


def test_datoer_er_datoer_og_tall_er_tall():
    """Bestillingen: «Datoer som ekte datoer, tall som tall.» En dato er
    et serietall med datoformat, ikke teksten «2012-01-02»."""
    data = _ark(_ds())["Data"]
    typer = _celletyper(_ds())
    assert data[1][1] == "40910"            # 2012-01-02 som Excel-serietall
    assert typer["B2"] == "n"
    assert data[1][2] == "1" and typer["C2"] == "n"      # «01» -> 1
    assert data[1][3] == "0.12" and typer["D2"] == "n"
    assert typer["E2"] == "b" and data[1][4] == "1"      # True
    assert typer["E3"] == "b" and data[2][4] == "0"      # False


def test_et_nummer_som_identifiserer_er_tekst():
    """`00042` som tall er 42. Et lokalitetsnummer regnes ikke med."""
    data = _ark(_ds())["Data"]
    assert data[3][0] == "00042"
    assert _celletyper(_ds())["A4"] == "s"


def test_en_verdi_som_ikke_er_typen_skrives_som_den_staar():
    """Kildens verdi forsvinner aldri. «true» i små bokstaver er ikke
    kildens skrivemåte, og blir stående som tekst — samme regel som
    `JANEI` i nettsted.py."""
    data = _ark(_ds())["Data"]
    typer = _celletyper(_ds())
    assert data[3][3] == "ikke tall" and typer["D4"] == "s"
    assert data[3][4] == "true" and typer["E4"] == "s"


def test_en_streng_som_ligner_en_formel_blir_ikke_en_formel():
    """Navnene er fra registre vi ikke kontrollerer."""
    assert _ark(_ds())["Data"][3][5] == "=1+1"
    assert _celletyper(_ds())["F4"] == "s"
    raa = zipfile.ZipFile(io.BytesIO(nedlasting.xlsx_bytes(_ds())))
    assert b"<f>" not in raa.read("xl/worksheets/sheet1.xml")


def test_tom_celle_er_tom_og_ikke_null():
    data = _ark(_ds())["Data"]
    assert data[2][3] == ""
    assert "D3" not in _celletyper(_ds()) or _celletyper(_ds())["D3"] == "n"


def test_om_dataene_har_alt_bestillingen_nevner():
    """Kilde, lisens, hentetidspunkt, sjekksum, forklaring per kolonne,
    og hva tom celle betyr."""
    ds = _ds()
    om = _ark(ds)["Om dataene"]
    ledd = {rad[0] for rad in om if rad}
    assert {"Kilde", "Lisens", "Hentet", "Sjekksum", "Tom celle",
            "Attribusjon"} <= ledd
    tekst = "\n".join(" | ".join(r) for r in om)
    assert nedlasting.sjekksum_vist(ds) in tekst
    assert "NLOD — https://example.org/vilkar" in tekst
    assert "Hentet fra BarentsWatch 5. oktober 2026" in tekst
    # Én rad per kolonne, med forklaring og hva tom betyr.
    hode = om.index(["Kolonne", "Datatype", "Forklaring", "Tom celle betyr"])
    assert [r[0] for r in om[hode + 1:]] == [k.navn for k in ds.kolonner]
    assert om[hode + 4][1:] == ["desimaltall", "Et tall.", "Ikke oppgitt."]
    assert om[hode + 1][3] == "Er aldri tom."


# ---- datapakken --------------------------------------------------------

def test_pakken_har_csv_metadata_og_readme():
    assert _pakke(_ds()).namelist() == ["test.csv", "metadata.json",
                                        "README.txt"]


def test_csv_en_i_pakken_er_uten_kommentarer_utf8_lf_og_ett_hode():
    raa = _pakke(_ds()).read("test.csv")
    tekst = raa.decode("utf-8")
    assert not raa.startswith(b"\xef\xbb\xbf"), "ingen BOM"
    assert "\r" not in tekst
    assert not any(l.startswith("#") for l in tekst.splitlines())
    rader = list(csv.reader(io.StringIO(tekst)))
    assert rader[0] == ["id", "dato", "uke", "tall", "flagg", "navn"]
    assert len(rader) == 4
    # KILDENS VERDIER, som tekst og uendret.
    assert rader[1] == ["20797", "2012-01-02", "01", "0.12", "True", "URDVIKA"]


def test_sjekksummen_er_summen_av_csv_en_i_pakken():
    """Den som pakker ut, kan etterprøve den."""
    ds = _ds()
    assert nedlasting.sjekksum(ds) == hashlib.sha256(
        _pakke(ds).read("test.csv")).hexdigest()


def test_readme_sier_det_samme_som_om_arket():
    """ÉN kilde for begge. README.txt og «Om dataene» skrevet hver for
    seg ville vært to steder som skal si det samme."""
    ds = _ds()
    readme = _pakke(ds).read("README.txt").decode("utf-8")
    for ledd, tekst in nedlasting.om_rader(ds):
        assert tekst in readme, ledd
    for navn, datatype, forklaring, tom in nedlasting.kolonnerader(ds):
        assert f"{navn} ({datatype})" in readme
        assert forklaring in readme and f"Tom celle: {tom}" in readme


def test_metadata_er_csvw():
    ds = _ds()
    m = json.loads(_pakke(ds).read("metadata.json"))
    assert m["@context"][0] == "http://www.w3.org/ns/csvw"
    assert m["url"] == "test.csv"
    assert m["dialect"]["lineTerminators"] == ["\n"]
    assert m["dialect"]["header"] is True
    kol = m["tableSchema"]["columns"]
    assert [k["name"] for k in kol] == [k.navn for k in ds.kolonner]
    typer = {k["name"]: k["datatype"] for k in kol}
    assert typer["dato"] == "date" and typer["tall"] == "decimal"
    assert typer["flagg"] == {"base": "boolean", "format": "True|False"}
    assert {k["name"]: k["required"] for k in kol}["id"] is True
    assert {k["name"]: k["required"] for k in kol}["tall"] is False
    assert m["tableSchema"]["primaryKey"] == ["id", "dato"]
    assert m["dc:source"][0]["dc:license"] == "NLOD"
    assert any(nedlasting.sjekksum_vist(ds) in c for c in m["rdfs:comment"])


def test_den_viste_summen_er_summen_i_grupper_og_aldri_ni_siffer():
    """MÅLT 07.10.2026: 11,7 % av tilfeldige sha256-summer har en rekke
    på ni siffer som porten leser som et organisasjonsnummer. Gruppert i
    åtte kan den ikke ha det, og summen er den samme."""
    def variant(i):
        return _ds(rader=[dict(_ds().rader[0], navn=f"variant {i}")])

    for i in range(300):
        ds = variant(i)
        vist = nedlasting.sjekksum_vist(ds)
        assert vist.replace(" ", "") == nedlasting.sjekksum(ds)
        assert not vakt.NI_SIFFER.search(vist)
    # Og at prøven over faktisk ville truffet noe uten grupperingen:
    treff = sum(bool(vakt.NI_SIFFER.search(
        nedlasting.sjekksum(variant(i))))
        for i in range(300))
    assert treff > 0


def test_samme_data_gir_samme_bytes():
    """Ingen klokke i filene: byggedatoen kommer inn. To bygg av de
    samme dataene skal gi samme sha256 over byggemappa."""
    assert nedlasting.xlsx_bytes(_ds()) == nedlasting.xlsx_bytes(_ds())
    assert nedlasting.zip_bytes(_ds()) == nedlasting.zip_bytes(_ds())
    assert nedlasting.zip_bytes(_ds()) != nedlasting.zip_bytes(
        _ds(bygget="2026-10-08"))


def test_ukjent_datatype_kaster():
    with pytest.raises(ValueError):
        _ds(kolonner=(nedlasting.Kolonne("x", "tid", "?"),))


def test_tomt_datasett_gir_hode_og_null_rader():
    """«Vi har sett etter og ikke funnet noe» er et svar."""
    ds = _ds(rader=[])
    assert _ark(ds)["Data"] == [[k.navn for k in ds.kolonner]]
    assert _pakke(ds).read("test.csv").decode().count("\n") == 1


def test_porten_finner_ingenting_i_rene_filer(tmp_path, monkeypatch):
    """Det nedlasting.py skriver, skal porten kunne lese uten funn — også
    `_rels/.rels` og de andre delene XlsxWriter legger i pakken."""
    raw = tmp_path / "raw"
    raw.mkdir()
    monkeypatch.setattr(vakt, "RAW_DIR", raw)
    from core import snapshot
    monkeypatch.setattr(snapshot, "RAW_DIR", raw)
    ut = tmp_path / "ut"
    ut.mkdir()
    ds = _ds(rader=_ds().rader[:2])
    (ut / "a.xlsx").write_bytes(nedlasting.xlsx_bytes(ds))
    (ut / "a.zip").write_bytes(nedlasting.zip_bytes(ds))
    # `navn` STÅR i NAVNEFELT, og URDVIKA er ikke i en tom hviteliste:
    # det funnet er porten som virker. Alt annet skal være rent — også
    # sjekksummen, se `sjekksum_vist()`.
    assert sorted((f.fil, f.slag) for f in vakt.gransk(ut)) == [
        ("a.xlsx!/Data", "ukjent_navn"), ("a.zip!/test.csv", "ukjent_navn")]


# ---- lusetallene -------------------------------------------------------

def test_lusekolonnene_er_csv_kolonnene():
    """Regnearket, pakken og den gamle `lusetall.csv` har de samme
    kolonnene i samme rekkefølge."""
    assert tuple(k.navn for k in nettsted.LUSEKOLONNER) == \
        nettsted.CSV_KOLONNER


def test_ukekolonnene_staar_stille():
    """Rekkefølgen ukesfilene har hatt siden 16.09.2026."""
    assert [k.navn for k in nettsted.UKEKOLONNER] == [
        "observert", "uke", "type", "kilde", "entity_id", "entity_name",
        "felt", "fra", "til", "kommune", "prodomraade_kode",
        "prodomraade_navn"]


def test_hver_kilde_i_en_nedlasting_har_en_lisenslinje():
    for kilde in ("lusetall",) + nettsted.ENDRINGSKILDER:
        assert nettsted.kildelisens([kilde])
    with pytest.raises(nettsted.UbelagtKilde):
        nettsted.kildelisens(["ekspertgruppen"])


def test_skriv_alle_legger_regneark_og_pakke_ved_hver_lokalitet(
        datamappe, tmp_path):
    ut = tmp_path / "nettsted"
    nettsted.skriv_alle(ut)
    for loknr in ("10001", "10002"):
        mappe = ut / "lokalitet" / loknr
        for navn in (nettsted.CSV_FILNAVN, nettsted.XLSX_FILNAVN,
                     nettsted.ZIP_FILNAVN):
            assert (mappe / navn).is_file(), (loknr, navn)

    mappe = ut / "lokalitet" / "10001"
    data = dict(vakt.xlsx_ark((mappe / nettsted.XLSX_FILNAVN).read_bytes()))
    assert [r[1] for r in data["Data"][1:]] == ["46244", "46251"]
    pakket = zipfile.ZipFile(mappe / nettsted.ZIP_FILNAVN)
    csv_navn = [n for n in pakket.namelist() if n.endswith(".csv")]
    rader = list(csv.reader(io.StringIO(pakket.read(csv_navn[0]).decode())))
    # SAMME RADER som den gamle CSV-en, uten kommentarhodet.
    gammel = [l for l in (mappe / nettsted.CSV_FILNAVN).read_text()
              .splitlines() if l and not l.startswith("#")]
    assert [",".join(r) for r in rader] == gammel
    readme = pakket.read("README.txt").decode()
    assert "Data levert av BarentsWatch" in readme
    assert "Opplysninger om lakselus" in readme


# ---- ukesfilene --------------------------------------------------------

def _uke() -> dict:
    def h(**k):
        rad = {"dato": "2026-10-05", "type": "lokalitet",
               "kilde": "akvakultur", "identitet": "16281",
               "gjelder": "Kastevika", "gjelder_felt": "entity_name",
               "felt": "kapasitet", "fra": "1 261", "til": "1 274",
               "kommune": "BØMLO", "po": "3", "po_navn": "Karmøy til Sotra"}
        rad.update(k)
        return rad
    return {"slug": "2026-41", "vist": "uke 41, 2026",
            "merke": "Observert 5. oktober 2026", "antall_fil": 2,
            "datoer": ["2026-10-05"],
            "hendelser": [h(), h(kilde="eierskap", identitet="",
                              gjelder="Tillatelse H-B-0040",
                              gjelder_felt="gjelder", kommune="", po="",
                              po_navn="")]}


def test_ukesfila_har_de_samme_radene_som_csv_en():
    uke = _uke()
    ds = nettsted.endringer_datasett(uke, bygget="2026-10-07")
    pakket = zipfile.ZipFile(io.BytesIO(nedlasting.zip_bytes(ds)))
    ny = pakket.read(ds.csv_navn).decode()
    gammel = "\n".join(l for l in nettsted._ukens_csv(uke).splitlines()
                       if not l.startswith("#")) + "\n"
    assert ny == gammel


def test_en_hendelse_vi_ikke_navngir_har_tom_identitet_i_regnearket():
    """Samme regel som i CSV-en: «Tillatelse H-B-0040» er vår etikett,
    ikke kildens navn, og står ikke i `entity_name`."""
    ds = nettsted.endringer_datasett(_uke(), bygget="2026-10-07")
    data = dict(vakt.xlsx_ark(nedlasting.xlsx_bytes(ds)))["Data"]
    assert data[2][4:6] == ["", ""]
    assert "Tillatelse H-B-0040" not in str(data)
    assert data[1][4:6] == ["16281", "Kastevika"]


def test_ukesfila_bærer_alle_kildenes_attribusjon_og_lisens():
    ds = nettsted.endringer_datasett(_uke(), bygget="2026-10-07")
    tekst = "\n".join(t for _, t in nedlasting.om_rader(ds))
    assert "Kilde: Fiskeridirektoratet" in tekst
    assert "Brønnøysundregistrene" in tekst
    assert "NLOD 2.0 — https://data.norge.no/nlod/no/2.0" in tekst
    # Typene forklart, så kolonnen `type` kan leses uten siden.
    assert "tillatelse:" in tekst and "felt_ny:" in tekst


def test_ukesfilas_hentetidspunkt_er_ukas_eget(monkeypatch):
    """Ikke `akva_hentet`, som er det nyeste øyeblikksbildets. For en
    eldre uke ville det vært en annen henting enn den raden kom fra."""
    stemplet = {("akvakultur", "2026-10-05"): "2026-10-05T04:12:31+00:00",
                ("eierskap", "2026-10-05"): "2026-10-05T04:20:00+00:00"}
    monkeypatch.setattr(nettsted, "_hentet_snapshot",
                        lambda k, d: stemplet.get((k, d), ""))
    ds = nettsted.endringer_datasett(_uke(), bygget="2026-10-07")
    assert ds.hentet == [
        "Hentet fra akvakultur 5. oktober 2026 kl. 04.12 UTC.",
        "Hentet fra eierskap 5. oktober 2026 kl. 04.20 UTC."]
