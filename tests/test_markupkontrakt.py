"""Markupkontrakten: CSS er fritt, markup er en kontrakt.

Denne fila gransker MALENE, ikke en rendret side, og det er hele poenget.
Fire nye sidetyper skal bygges, og en test som bare kjenner
`lokalitet.html.j2` ville sagt grønt om alle fire brøt kontrakten. Prøven
går over `maler/*.html.j2` — en ny mal er dekket i det den legges der,
uten at noen husker å utvide en liste.

Hva kontrakten er, og hvorfor hver del står der, er begrunnet i
docs/beslutninger/2026-09-19-markup-er-en-kontrakt.md.

## Grensa mellom fritt og bundet

    fritt     klassenavn, rekkefølge på kolonner, tekst i captions,
              farger, mellomrom, hvilke tabeller som finnes
    bundet    data-felt på verdiceller, <table>/<caption>/<thead>/
              <th scope>, tabell-id-er, <time datetime>

Det bundne er det maskiner leser: publiseringsvakten leser `data-felt`
for å vite hvilket felt en verdi kom fra, ankrene er URL-er noen kan
lenke til, og `<time datetime>` er det eneste som gjør en dato maskinlesbar.
En designrunde kan endre alt i venstre kolonne. Høyre kolonne endres bare
av en beslutning med sin egen test.
"""

import re
from pathlib import Path

import pytest

MALER = Path(__file__).resolve().parent.parent / "maler"

# Jinja-kommentarer fjernes FØR granskningen. En kommentar som forklarer
# kontrakten inneholder gjerne `<td>` som eksempel, og en prøve som leste
# den ville meldt sin egen dokumentasjon som brudd. Målt: det skjedde.
JINJA_KOMMENTAR = re.compile(r"\{#.*?#\}", re.S)

VERDICELLE = re.compile(r"<td\b([^>]*)>(.*?)</td>", re.S)
TABELL = re.compile(r"<table\b([^>]*)>(.*?)</table>", re.S)

# ET MERKET BARN teller som merking av verdien sitt.
#
# Kravet er at ingen VERDI står umerket, og `data-felt` på cella er den
# vanlige måten å oppfylle det. Den holder så lenge cella bærer ÉN verdi.
#
# En celle med TO verdier kan ikke merkes på cella: porten leser hele
# celleteksten som én verdi, og «912345678 (i dag: MOWI ASA)» slås da opp
# i hvitelista som ett navn. Den står ikke der, og MÅLT 22.09.2026
# stoppet nettopp den formen publiseringen med 341 funn. Se
# `nettsted._oppgitt_historikk()`.
#
# Da merkes hver verdi på sitt eget element, og cella slipper. Prøven
# under krever at ALLE `{{ }}` i cella ligger inne i et slikt element —
# én umerket verdi ved siden av to merkede er fortsatt et brudd.
MERKET_BARN = re.compile(r"<(\w+)\b[^>]*\bdata-felt=[^>]*>.*?</\1>", re.S)


def _uten_kommentarer(mal: str) -> str:
    return JINJA_KOMMENTAR.sub("", mal)


def markupbrudd(mappe: Path) -> list[str]:
    """Brudd på markupkontrakten i hver `*.html.j2` under `mappe`.

    Returnerer en liste med lesbare brudd, tom liste = kontrakten holder.
    En liste framfor et kast: en ny mal kan bryte flere ting samtidig, og
    den som retter skal se alle i én kjøring.
    """
    brudd: list[str] = []
    for sti in sorted(mappe.glob("*.html.j2")):
        mal = _uten_kommentarer(sti.read_text(encoding="utf-8"))

        # 1. VERDICELLER. En <td> som skriver ut en verdi må si hvilket
        #    felt verdien kom fra. `<th scope="row">` er nøkkelen og ikke
        #    verdien, og er derfor ikke med.
        for m in VERDICELLE.finditer(mal):
            attributter, kropp = m.group(1), m.group(2)
            if "{{" not in kropp:
                continue
            # Hvert merkede barn fjernes. Står det ingen verdi igjen, er
            # alle verdiene i cella merket — se `MERKET_BARN`.
            if "{{" not in MERKET_BARN.sub("", kropp):
                continue
            if "data-felt" not in attributter:
                brudd.append(
                    f"{sti.name}: verdicelle uten data-felt: "
                    f"<td{attributter}>{' '.join(kropp.split())[:50]}")

        # 2. TABELLER. Ankeret er en URL, og de tre andre er det som gjør
        #    en tabell lesbar for en skjermleser og for en parser.
        for m in TABELL.finditer(mal):
            attributter, kropp = m.group(1), m.group(2)
            navn = re.search(r'id="([^"]+)"', attributter)
            hvem = navn.group(1) if navn else "(uten id)"
            if not navn:
                brudd.append(f"{sti.name}: <table> uten id — ankeret er en URL")
            for krav, hva in (("<caption", "caption"), ("<thead", "thead"),
                              ("scope=", "th scope")):
                if krav not in kropp:
                    brudd.append(f"{sti.name}: tabell {hvem} mangler {hva}")
    return brudd


# ---- dagens maler ------------------------------------------------------

def test_dagens_maler_holder_kontrakten():
    """Faller denne, er kontrakten brutt av noe som alt er skrevet — og
    da skal malen rettes, ikke prøven."""
    assert markupbrudd(MALER) == []


def test_prøven_finner_alle_maler():
    """Kontrollen av kontrollen: en prøve som leste null filer ville vært
    grønn for alltid."""
    assert len(list(MALER.glob("*.html.j2"))) >= 2


# ---- plantede brudd ----------------------------------------------------

def _mal(tmp_path, kropp, navn="selskap.html.j2"):
    """En NY sidetype, ikke lokalitetssiden. Det er den som skal fanges."""
    (tmp_path / navn).write_text(kropp, encoding="utf-8")
    return tmp_path


TABELLHODE = ('<table id="selskap-tillatelser">\n'
              '  <caption>Tekst.</caption>\n'
              '  <thead><tr><th scope="col">Felt</th></tr></thead>\n'
              '  <tbody><tr>')


def test_verdicelle_uten_data_felt_felles(tmp_path):
    """Kjernen i kontrakten. Uten merkingen er porten blind for verdien,
    og blindheten kommer uten at noe feiler — som er nøyaktig det som ble
    målt 18.09.2026: 24 navneverdier i endringstabellen som
    `ukjent_navn` ikke kunne se."""
    mappe = _mal(tmp_path, TABELLHODE +
                 "<td>{{ s.eier_navn }}</td></tr></tbody></table>")
    brudd = markupbrudd(mappe)
    assert len(brudd) == 1
    assert "verdicelle uten data-felt" in brudd[0]
    assert "selskap.html.j2" in brudd[0]


def test_samme_celle_MED_data_felt_passerer(tmp_path):
    mappe = _mal(tmp_path, TABELLHODE +
                 '<td data-felt="eier_navn">{{ s.eier_navn }}</td>'
                 "</tr></tbody></table>")
    assert markupbrudd(mappe) == []


def test_celle_uten_verdi_krever_ingen_merking(tmp_path):
    """En `<td>` med fast tekst er ikke en verdicelle. Krevde prøven
    merking der, ville den fyrt på hver mellomromscelle og blitt slått
    av."""
    mappe = _mal(tmp_path, TABELLHODE + "<td>—</td></tr></tbody></table>")
    assert markupbrudd(mappe) == []


def test_radnøkkel_i_th_krever_ingen_merking(tmp_path):
    """`<th scope="row">{{ s.nr }}</th>` er nøkkelen, ikke verdien."""
    mappe = _mal(tmp_path, TABELLHODE +
                 '<th scope="row">{{ s.nr }}</th></tr></tbody></table>')
    assert markupbrudd(mappe) == []


@pytest.mark.parametrize("fjern,ventet", [
    ('<caption>Tekst.</caption>\n', "caption"),
    ('<thead><tr><th scope="col">Felt</th></tr></thead>\n', "thead"),
])
def test_tabell_uten_semantikk_felles(tmp_path, fjern, ventet):
    kropp = (TABELLHODE + '<td data-felt="navn">{{ s.navn }}</td>'
             "</tr></tbody></table>").replace(fjern, "")
    brudd = markupbrudd(_mal(tmp_path, kropp))
    assert any(ventet in b for b in brudd), brudd


def test_tabell_uten_id_felles(tmp_path):
    """Ankeret er en URL. Uten id kan ingen lenke til tabellen, og en
    som lenket i går får 404 på fragmentet i dag."""
    kropp = (TABELLHODE.replace(' id="selskap-tillatelser"', "")
             + '<td data-felt="navn">{{ s.navn }}</td></tr></tbody></table>')
    brudd = markupbrudd(_mal(tmp_path, kropp))
    assert any("uten id" in b for b in brudd), brudd


def test_en_ny_sidetype_er_dekket_uten_at_noen_utvider_prøven(tmp_path):
    """Grunnen til at prøven globber framfor å liste.

    Fire sidetyper legges til i morgen. Ingen av dem nevnes her, og alle
    fire granskes."""
    for navn in ("selskap.html.j2", "omraade.html.j2",
                 "art.html.j2", "kommune.html.j2"):
        _mal(tmp_path, TABELLHODE + "<td>{{ x.navn }}</td></tr></tbody></table>",
             navn=navn)
    brudd = markupbrudd(tmp_path)
    assert len(brudd) == 4
    for navn in ("selskap", "omraade", "art", "kommune"):
        assert any(navn in b for b in brudd), navn


def test_kommentarer_granskes_ikke(tmp_path):
    """En kommentar som FORKLARER kontrakten inneholder `<td>` som
    eksempel. Første utgave av prøven meldte sin egen dokumentasjon som
    brudd — målt på lokalitet.html.j2."""
    mappe = _mal(tmp_path, TABELLHODE +
                 '<td data-felt="navn">{{ s.navn }}</td></tr></tbody></table>'
                 "\n{# slik: <td>{{ verdi }}</td> uten merking #}")
    assert markupbrudd(mappe) == []


def test_to_merkede_verdier_i_en_celle_er_ikke_brudd(tmp_path):
    """En celle med to verdier merkes på verdiene, ikke på cella.

    `nettsted._oppgitt_historikk()` skriver organisasjonsnummeret og
    dagens navn på det i samme celle. Merket cella dem samlet, ville
    porten slått opp «912345678 (i dag: MOWI ASA)» i hvitelista som ett
    navn — og MÅLT 22.09.2026 stoppet nettopp den formen publiseringen.
    """
    mappe = _mal(tmp_path, TABELLHODE + (
        '<td><span data-felt="tildelt_orgnr">{{ o.orgnr }}</span>'
        '<span data-felt="tildelt_navn">{{ o.navn }}</span></td>'
        "</tr></tbody></table>"))
    assert markupbrudd(mappe) == []


def test_en_umerket_verdi_ved_siden_av_en_merket_er_fortsatt_brudd(tmp_path):
    """Unntaket gjelder celler der ALT er merket. Ellers ville en celle
    med ett merket barn dekket over hver umerket verdi ved siden av."""
    mappe = _mal(tmp_path, TABELLHODE + (
        '<td><span data-felt="tildelt_orgnr">{{ o.orgnr }}</span>'
        "{{ o.navn }}</td></tr></tbody></table>"))
    assert len(markupbrudd(mappe)) == 1
