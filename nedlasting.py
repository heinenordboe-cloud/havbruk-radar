"""Nedlastingene: ett regneark og én datapakke av de SAMME radene.

Fram til 07.10.2026 hadde lusetallserien og ukesfilene én nedlasting
hver, en CSV med attribusjonen i et `#`-hode. Den er laget for verktøy
som kan hoppe over kommentarlinjer, og den er det vi siterer — men den
åpnes dårlig i et regneark, og en CSV-leser som ikke kjenner `#` får
hodet som datarader.

Her lages to former av ETT `Datasett`:

  * **Excel (.xlsx)** — arket «Data» med radene, og arket «Om dataene»
    med kilde, lisens, hentetidspunkt, sjekksum og hva hver kolonne og en
    tom celle betyr. Datoer er ekte datoer og tall er tall.
  * **Data (.zip)** — CSV-en UTEN kommentarlinjer (UTF-8, LF, én
    overskriftsrad), `metadata.json` etter W3C CSVW, og `README.txt` med
    det samme som arket «Om dataene».

## Hvorfor én modul og ett datasett

«Om dataene», `README.txt` og `metadata.json` sier det samme tre
steder. Skrevet hver for seg, er det formen F6 og F7 hadde: tre steder
som skal si det samme, og som en dag svarer ulikt. Her bygges alle tre
av `om_rader()` og `Datasett.kolonner`, og sjekksummen regnes av de
samme bytene som legges i pakken.

## Kildens verdier, i en annen beholder

BarentsWatch-vilkåret sier at datainnholdet ikke skal endres
(docs/LISENSKJEDE.md merknad F). CSV-en i pakken har kildens strenger
uendret — `True`, `0.12`, tom. I regnearket er det de SAMME verdiene,
lagret som typen de er: `True` som en logisk verdi, `0.12` som et tall.
En verdi som ikke lar seg lese som typen kolonnen oppgir, skrives som
tekst slik den står, og forsvinner aldri. Samme regel som `JANEI` i
nettsted.py: et kart som ikke kjenner verdien, slipper den gjennom.

## Ingen klokke her

Byggedatoen kommer inn som argument. Arket, ZIP-medlemmene og
`metadata.json` dateres alle av den, så to bygg av de samme dataene på
samme dag gir de samme bytene. Se CLAUDE.md 1b.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field

import xlsxwriter


@dataclass(frozen=True)
class Kolonne:
    """Én kolonne, og det en leser trenger for å bruke den.

    `datatype` er CSVW-ens navn (`string`, `date`, `decimal`, `integer`,
    `boolean`) og styrer både cellentypen i regnearket og `datatype` i
    `metadata.json`. `tom` er hva en tom celle BETYR — ikke at den kan
    være tom, men hvorfor. Tom streng her betyr at kolonnen aldri er tom.
    """

    navn: str
    datatype: str
    forklaring: str
    tom: str = ""


DATATYPER = ("string", "date", "decimal", "integer", "boolean")

# Ordet et menneske leser i «Om dataene». CSVW-navnet står i
# metadata.json, der det er en maskin som leser.
DATATYPE_ORD = {
    "string": "tekst",
    "date": "dato",
    "decimal": "desimaltall",
    "integer": "heltall",
    "boolean": "sann/usann",
}

# Kildens boolske verdier, eksakt. Se `JANEI` i nettsted.py.
BOOLSK = {"True": True, "False": False}


@dataclass
class Datasett:
    """Radene og alt som skal stå om dem. Se modulens docstring.

    `stamme` er filnavnet uten endelse, og er det SAMME for regnearket,
    pakken og CSV-en i pakken. `rader` er kildens verdier som strenger,
    med kolonnenavnet som nøkkel.
    """

    stamme: str
    tittel: str
    beskrivelse: str
    kolonner: tuple[Kolonne, ...]
    rader: list[dict]
    # (utgiver, lisens, lenke til vilkårene) per kilde.
    kilder: list[tuple[str, str, str]]
    attribusjon: list[str]
    # Setninger om når VI hentet dataene. Leses fra snapshotene, aldri
    # utledet av byggedatoen.
    hentet: list[str]
    bygget: str
    merknader: list[str] = field(default_factory=list)
    # Nøkkelen en rad er unik på, for `primaryKey` i metadata.json.
    nokkel: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for k in self.kolonner:
            if k.datatype not in DATATYPER:
                raise ValueError(f"{k.navn}: ukjent datatype {k.datatype!r}")

    @property
    def csv_navn(self) -> str:
        return f"{self.stamme}.csv"

    @property
    def xlsx_navn(self) -> str:
        return f"{self.stamme}.xlsx"

    @property
    def zip_navn(self) -> str:
        return f"{self.stamme}.zip"


# ------------------------------------------------------------- CSV

def csv_bytes(ds: Datasett) -> bytes:
    """CSV-en i pakken: UTF-8 uten BOM, LF, én overskriftsrad, ingen `#`.

    LF og ikke CRLF, i motsetning til den gamle `lusetall.csv`: den ble
    skrevet med `csv`-modulens standard, og formatet for pakken er
    bestilt som LF. CSVW-dialekten i metadata.json sier hvilket.
    """
    ut = io.StringIO()
    skriver = csv.writer(ut, lineterminator="\n")
    skriver.writerow([k.navn for k in ds.kolonner])
    for rad in ds.rader:
        skriver.writerow([rad.get(k.navn, "") or "" for k in ds.kolonner])
    return ut.getvalue().encode("utf-8")


def sjekksum(ds: Datasett) -> str:
    """sha256 over CSV-en i pakken. Regnearket kan ikke bære sin egen
    sum; CSV-en er de samme radene, og den kan etterprøves av den som
    pakker ut."""
    return hashlib.sha256(csv_bytes(ds)).hexdigest()


def sjekksum_vist(ds: Datasett) -> str:
    """Summen i grupper på åtte tegn: «692dfd8d a86625ae …».

    ## Hvorfor ikke de 64 tegnene i ett

    Fordi porten leser dem som et organisasjonsnummer. `NI_SIFFER` ser
    etter ni siffer på rad uten siffer, punktum eller komma rundt, og en
    heksadesimal sum har bokstaver der. MÅLT 07.10.2026 over 200 000
    tilfeldige summer: 11,7 % inneholder en slik rekke — rundt 200 av
    1 782 lokaliteter, hver uke, og alle falske.

    De to andre veiene var å løsne `NI_SIFFER` for alt som ligner en
    sum, eller å vise en forkortet sum som sidene gjør. Den første gjør
    vakten blind for et nummer som står inntil bokstaver; den andre kan
    ikke etterprøves. En gruppe på åtte kan ikke inneholde ni siffer, og
    `sha256sum` sin utskrift sammenlignes like godt gruppe for gruppe.
    """
    hel = sjekksum(ds)
    return " ".join(hel[i:i + 8] for i in range(0, len(hel), 8))


# ------------------------------------------------------- «Om dataene»

def om_rader(ds: Datasett) -> list[tuple[str, str]]:
    """(ledd, tekst) — det som står i arket «Om dataene» og i README.txt.

    ÉN liste for begge. Se modulens docstring.
    """
    rader: list[tuple[str, str]] = [
        ("Tittel", ds.tittel),
        ("Innhold", ds.beskrivelse),
        ("Rader", f"{len(ds.rader)}"),
    ]
    for utgiver, lisens, lenke in ds.kilder:
        rader.append(("Kilde", utgiver))
        rader.append(("Lisens", f"{lisens} — {lenke}" if lenke else lisens))
    for setning in ds.attribusjon:
        rader.append(("Attribusjon", setning))
    for setning in ds.hentet:
        rader.append(("Hentet", setning))
    rader.append(("Bygget", f"{ds.bygget} av Kystloggen"))
    rader.append(("Sjekksum", f"SHA-256 av {ds.csv_navn} i datapakken, i "
                              f"grupper på åtte tegn: {sjekksum_vist(ds)}"))
    tomme = [k for k in ds.kolonner if k.tom]
    rader.append((
        "Tom celle",
        "En tom celle er ikke null og ikke «nei». Den betyr at det ikke "
        "finnes noen verdi — hva det betyr for hver kolonne står i "
        "kolonnelista under." if tomme else
        "Ingen kolonne i denne fila har tomme celler."))
    for merknad in ds.merknader:
        rader.append(("Merknad", merknad))
    rader.append((
        "Formatene",
        f"{ds.xlsx_navn} og {ds.zip_navn} har de samme radene. CSV-en i "
        f"pakken har kildens verdier som tekst, slik de kom; regnearket "
        f"har de samme verdiene lagret som dato, tall eller sann/usann. "
        f"metadata.json i pakken beskriver CSV-en etter W3C CSVW."))
    return rader


def kolonnerader(ds: Datasett) -> list[tuple[str, str, str, str]]:
    """(kolonne, datatype, forklaring, tom celle betyr) per kolonne."""
    return [(k.navn, DATATYPE_ORD[k.datatype], k.forklaring,
             k.tom or "Er aldri tom.") for k in ds.kolonner]


def readme(ds: Datasett) -> bytes:
    """README.txt: det samme som arket «Om dataene», som ren tekst."""
    linjer = [ds.tittel, "=" * len(ds.tittel), ""]
    bredde = max(len(l) for l, _ in om_rader(ds))
    for ledd, tekst in om_rader(ds):
        linjer.append(f"{ledd + ':':<{bredde + 1}} {tekst}")
    linjer += ["", "Kolonner", "--------", ""]
    for navn, datatype, forklaring, tom in kolonnerader(ds):
        linjer += [f"{navn} ({datatype})", f"  {forklaring}",
                   f"  Tom celle: {tom}", ""]
    return ("\n".join(linjer).rstrip("\n") + "\n").encode("utf-8")


# ------------------------------------------------------- metadata.json

def _csvw_datatype(k: Kolonne):
    if k.datatype == "boolean":
        # Kildens skrivemåte, ikke CSVWs standard «true|false».
        return {"base": "boolean", "format": "True|False"}
    return k.datatype


def metadata(ds: Datasett) -> bytes:
    """`metadata.json` etter W3C CSVW («Metadata Vocabulary for Tabular
    Data»), der det passer.

    Det som IKKE passer, sagt rett ut: CSVW har ingen egenskap for «hva
    en tom celle betyr». `null: ""` sier at tom er fravær; MENINGEN står
    i `dc:description` per kolonne. Hentetidspunktene står som tekst i
    `rdfs:comment`, med samme ordlyd som i README.txt — et maskinlesbart
    tidsstempel her er ikke noe porten skiller fra et rått tidsstempel i
    synlig tekst, og datoen i `dc:modified` er den som er ment for maskin.
    """
    data = {
        "@context": ["http://www.w3.org/ns/csvw", {"@language": "nb"}],
        "url": ds.csv_navn,
        "dc:title": ds.tittel,
        "dc:description": ds.beskrivelse,
        "dc:creator": "Kystloggen",
        "dc:modified": {"@value": ds.bygget, "@type": "xsd:date"},
        "dc:source": [
            {"schema:name": utgiver, "dc:license": lisens,
             **({"schema:url": {"@id": lenke}} if lenke else {})}
            for utgiver, lisens, lenke in ds.kilder],
        "dc:rights": list(ds.attribusjon),
        # SJEKKSUMMEN SOM TEKST, i grupper. CSVW har ingen egenskap for
        # den, og SPDX sin `checksumValue` krever de 64 tegnene i ett —
        # som porten leser som organisasjonsnumre. Se `sjekksum_vist()`.
        "rdfs:comment": (list(ds.hentet) + list(ds.merknader)
                         + [f"SHA-256 av {ds.csv_navn}, i grupper på åtte "
                            f"tegn: {sjekksum_vist(ds)}"]),
        "dialect": {
            "encoding": "utf-8",
            "lineTerminators": ["\n"],
            "header": True,
            "headerRowCount": 1,
            "delimiter": ",",
            "doubleQuote": True,
        },
        "tableSchema": {
            "columns": [
                {"name": k.navn, "titles": k.navn,
                 "datatype": _csvw_datatype(k),
                 "null": "",
                 "required": not k.tom,
                 "dc:description": (f"{k.forklaring} Tom celle: {k.tom}"
                                    if k.tom else k.forklaring)}
                for k in ds.kolonner],
            **({"primaryKey": list(ds.nokkel)} if ds.nokkel else {}),
        },
    }
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# ------------------------------------------------------------- XLSX

def _celle(ark, rad: int, kol: int, k: Kolonne, verdi: str, fmt: dict) -> None:
    """Én celle, med typen kolonnen oppgir — eller som tekst.

    `write_string` og ikke `write`: `write` gjetter, og et lokalitetsnavn
    som begynner med «=» ville blitt en formel. Navnene er fra registre
    vi ikke kontrollerer — samme grunn som `autoescape` i nettsted.py.
    """
    if verdi == "":
        ark.write_blank(rad, kol, None)
        return
    try:
        if k.datatype == "date":
            ark.write_datetime(rad, kol, dt.datetime.fromisoformat(verdi),
                               fmt["dato"])
            return
        if k.datatype == "decimal":
            ark.write_number(rad, kol, float(verdi))
            return
        if k.datatype == "integer":
            ark.write_number(rad, kol, int(verdi))
            return
        if k.datatype == "boolean" and verdi in BOOLSK:
            ark.write_boolean(rad, kol, BOOLSK[verdi])
            return
    except ValueError:
        pass
    ark.write_string(rad, kol, verdi)


def xlsx_bytes(ds: Datasett) -> bytes:
    """Regnearket: «Data» og «Om dataene». Se modulens docstring."""
    buf = io.BytesIO()
    bok = xlsxwriter.Workbook(buf, {
        "in_memory": True,
        # Ingen gjetting på strenger: verdiene skrives med typen
        # kolonnen oppgir, og bare den.
        "strings_to_numbers": False,
        "strings_to_formulas": False,
        "strings_to_urls": False,
    })
    # DATERT AV BYGGET, ikke av klokka. Uten `created` setter
    # XlsxWriter tidspunktet nå, og to like bygg gir ulike bytes.
    bygget = dt.datetime.fromisoformat(ds.bygget)
    bok.set_properties({"title": ds.tittel, "author": "Kystloggen",
                        "created": bygget})
    fmt = {
        "dato": bok.add_format({"num_format": "yyyy-mm-dd"}),
        "hode": bok.add_format({"bold": True, "bottom": 1}),
        "ledd": bok.add_format({"bold": True, "valign": "top"}),
        "tekst": bok.add_format({"text_wrap": True, "valign": "top"}),
    }

    data = bok.add_worksheet("Data")
    for kol, k in enumerate(ds.kolonner):
        data.write_string(0, kol, k.navn, fmt["hode"])
        bredde = max([len(k.navn)] + [len(str(r.get(k.navn, "") or ""))
                                      for r in ds.rader[:200]])
        data.set_column(kol, kol, min(max(bredde + 2, 10), 50))
    for i, r in enumerate(ds.rader, 1):
        for kol, k in enumerate(ds.kolonner):
            _celle(data, i, kol, k, str(r.get(k.navn, "") or ""), fmt)
    data.freeze_panes(1, 0)
    if ds.rader:
        data.autofilter(0, 0, len(ds.rader), len(ds.kolonner) - 1)

    om = bok.add_worksheet("Om dataene")
    om.set_column(0, 0, 18)
    om.set_column(1, 1, 90)
    om.set_column(2, 3, 60)
    rad = 0
    for ledd, tekst in om_rader(ds):
        om.write_string(rad, 0, ledd, fmt["ledd"])
        om.write_string(rad, 1, tekst, fmt["tekst"])
        rad += 1
    rad += 1
    for kol, hode in enumerate(("Kolonne", "Datatype", "Forklaring",
                                "Tom celle betyr")):
        om.write_string(rad, kol, hode, fmt["hode"])
    for verdier in kolonnerader(ds):
        rad += 1
        for kol, tekst in enumerate(verdier):
            om.write_string(rad, kol, tekst, fmt["tekst"])

    bok.close()
    return buf.getvalue()


# -------------------------------------------------------------- ZIP

def zip_bytes(ds: Datasett) -> bytes:
    """Datapakken: CSV-en, metadata.json og README.txt.

    Medlemmene dateres av bygget, ikke av klokka, og skrives i fast
    rekkefølge — samme data gir samme bytes.
    """
    aar, mnd, dag = (int(x) for x in ds.bygget.split("-"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for navn, innhold in ((ds.csv_navn, csv_bytes(ds)),
                              ("metadata.json", metadata(ds)),
                              ("README.txt", readme(ds))):
            info = zipfile.ZipInfo(navn, date_time=(aar, mnd, dag, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, innhold)
    return buf.getvalue()
