"""Låser antakelsen ISO-sammenligningene hviler på: alt er +00:00.

`snapshot.publisert()` returnerer en STRENG, og `versjoner()`,
`forrige_versjon()`, `les_mellom()` og `diff.revisjon()` sorterer og
sammenligner den leksikografisk. `ute_naa < ute_foer` i `revisjon()` er
en strengsammenligning, ikke en tidssammenligning.

Det holder — så lenge hver eneste skriver normaliserer til UTC. Gjør én
av dem ikke det, sorterer to påstander om samme måned etter tegnverdi og
ikke etter tid, og revisjonsaksen leser baklengs uten å si fra.

## Hvorfor ikke bare normalisere ved sammenligning

Fordi det ville SKJULT antakelsen framfor å oppfylle den.

En `publisert()` som parset strengen til et tidspunkt før den
sammenlignet, ville tatt imot hva som helst og gitt riktig svar — og da
ville et snapshot med `+02:00` ligget på disk i årevis uten at noen så
det. Neste leser som sorterte på strengen (en analyse, et skript, en
`ORDER BY` i noe annet) ville fått feil svar, og feilen ville vært
usynlig helt til den ikke var det. Det er formen alle feilene i CLAUDE.md
1b har.

Antakelsen skal være SYNLIG. Derfor:

  1. `test_leksikografisk_rekkefolge_er_ikke_kronologisk` viser hva som
     går galt, i klartekst.
  2. `test_versjoner_sorterer_feil_med_annet_offset` viser at det slår
     gjennom helt til `snapshot.versjoner()`.
  3. Resten FEILER hvis en skriver i dette repoet slutter å normalisere.
"""

import ast
import datetime as dt
from dataclasses import replace
from pathlib import Path

import pytest

from core import runner, snapshot
from core.contract import Observation
from sources.biomasse import _utgitt
from sources.reguleringsomraader import publisert_i

ROT = Path(__file__).resolve().parent.parent

# Modulene som kan komme til å skrive et tidsstempel inn i dataene.
SKRIVENDE = ([ROT / "run.py", ROT / "backfill.py"]
             + sorted((ROT / "core").glob("*.py"))
             + sorted((ROT / "sources").glob("*.py")))

# Funksjonene som har lov til å produsere en `published_at`.
#
# Lista er kort med vilje. Skal en ny kilde sette `self.published_at`,
# skal den gå gjennom en funksjon som NORMALISERER til UTC — og navnet
# skal føres her sammen med en oppførselstest rett under, slik `_utgitt`
# har. Å utvide lista uten testen er å flytte antakelsen tilbake til der
# ingen ser den.
#
# `publisert_i` løser oppgaven på den andre måten: den produserer en ISO-
# DATO uten klokkeslett, fordi kilden den leser (HIs rapportside) bare
# oppgir en dato. Da finnes det ikke noe offset å normalisere feil — og
# det er nettopp derfor den er trygg. Å skrive `T00:00:00+00:00` på den
# ville vært å finne på et klokkeslett ingen har oppgitt, som er den
# samme feilen 1b-7 punkt 1 forbyr ett hakk lenger opp.
SKRIVERE_AV_PUBLISHED_AT = {"_utgitt", "publisert_i"}


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    return tmp_path


def _skriv(observed_at, verdi, *, fetched_at, published_at=""):
    obs = Observation(
        entity_id="1", entity_type="produksjonsomraade", entity_name="Ryfylket",
        field="beholdning_antall", value=str(verdi), source="biomasse",
        observed_at=observed_at)
    return snapshot.write([replace(obs, fetched_at=fetched_at,
                                   published_at=published_at,
                                   source_version="1", raw_hash="h",
                                   utvalg="{}")], observed_at)[0]


# ---- 1. antakelsen, sagt høyt -----------------------------------------

def test_leksikografisk_rekkefolge_er_ikke_kronologisk():
    """To strenger om samme øyeblikk sorterer ulikt. Det er hele saken.

    Ingen normalisering her: testen SKAL vise sprekken, ikke tette den.
    """
    utc = "2026-08-20T04:38:18+00:00"
    samme_oyeblikk_i_oslo = "2026-08-20T06:38:18+02:00"

    # Samme øyeblikk i verden ...
    assert (dt.datetime.fromisoformat(utc)
            == dt.datetime.fromisoformat(samme_oyeblikk_i_oslo))
    # ... men ikke samme streng, og ikke samme plass i en sortering.
    assert utc != samme_oyeblikk_i_oslo
    assert utc < samme_oyeblikk_i_oslo

    # Og verre: en ELDRE utgivelse i +02:00 sorterer SIST.
    eldre_i_oslo = "2026-08-20T05:00:00+02:00"        # = 03:00 UTC
    assert dt.datetime.fromisoformat(eldre_i_oslo) < dt.datetime.fromisoformat(utc)
    assert eldre_i_oslo > utc, (
        "Dette er antakelsen: strengen sier «senere», tida sier «tidligere». "
        "Alt som sorterer på published_at hviler på at det aldri skjer."
    )


def test_versjoner_sorterer_feil_med_annet_offset(isolert):
    """Sprekken slår gjennom helt til `snapshot.versjoner()`.

    Karakteriserende, ikke ønsket: dette er hva som VILLE skjedd om en
    kilde skrev `+02:00`. Testene under er de som passer på at ingen gjør
    det.
    """
    # Utgitt 03:00 UTC, skrevet med Oslo-offset.
    _skriv("2018-03-31", 10, fetched_at="2026-01-01T00:00:00+00:00",
           published_at="2018-04-20T05:00:00+02:00")
    # Utgitt 04:38 UTC — altså SENERE — skrevet i UTC.
    _skriv("2018-03-31", 20, fetched_at="2026-01-02T00:00:00+00:00",
           published_at="2018-04-20T04:38:18+00:00")

    rekkefolge = [r["value"][0] for _, r in snapshot.versjoner("biomasse", "2018-03-31")]

    # Kronologisk skulle "20" vært sist. Den er først.
    assert rekkefolge == ["20", "10"], (
        "Om denne endrer seg, er sorteringen lagt om — og da skal denne "
        "testen skrives om, ikke slettes."
    )
    assert snapshot.forrige_versjon("biomasse", "2018-03-31")["value"][0] == "10", (
        "«Gjeldende» ble den ELDSTE påstanden. Det er F14 om igjen, med "
        "tidssonen i stedet for løpenummeret."
    )


def test_versjoner_sorterer_riktig_nar_alt_er_utc(isolert):
    """Samme oppsett, begge i UTC: da stemmer rekkefølgen."""
    _skriv("2018-03-31", 10, fetched_at="2026-01-01T00:00:00+00:00",
           published_at="2018-04-20T03:00:00+00:00")
    _skriv("2018-03-31", 20, fetched_at="2026-01-02T00:00:00+00:00",
           published_at="2018-04-20T04:38:18+00:00")

    rekkefolge = [r["value"][0] for _, r in snapshot.versjoner("biomasse", "2018-03-31")]
    assert rekkefolge == ["10", "20"]
    assert snapshot.forrige_versjon("biomasse", "2018-03-31")["value"][0] == "20"


# ---- 2. skriverne av published_at -------------------------------------

@pytest.mark.parametrize("header, forventet", [
    # Slik Fiskeridirektoratet faktisk svarte 25.08.2026.
    ("Thu, 20 Aug 2026 04:38:18 GMT", "2026-08-20T04:38:18+00:00"),
    # Slik `X-Archive-Orig-Last-Modified` kom fra Wayback 26.08.2026.
    ("Sat, 20 Jul 2024 04:40:53 GMT", "2024-07-20T04:40:53+00:00"),
    # SAMME ØYEBLIKK som den første, oppgitt i norsk sommertid.
    ("Thu, 20 Aug 2026 06:38:18 +0200", "2026-08-20T04:38:18+00:00"),
    # Og vestover, for å fange et fortegn snudd feil vei.
    ("Wed, 19 Aug 2026 21:38:18 -0700", "2026-08-20T04:38:18+00:00"),
])
def test_utgitt_normaliserer_til_utc(header, forventet):
    """`sources/biomasse._utgitt()` er den ENESTE skriveren av
    `published_at` i repoet i dag.

    Feiler denne, er antakelsen bak all sortering på `published_at` brutt
    ved kilden, og en Wayback-kopi kan sorteres foran eller bak en
    ferskere henting etter hvilken tidssone tjenesten tilfeldigvis
    oppgav.
    """
    assert _utgitt({"Last-Modified": header}) == forventet
    assert _utgitt({"Last-Modified": header}).endswith("+00:00")


def test_utgitt_uten_header_er_tom_ikke_klokka():
    """«Vet ikke» skal se ut som «vet ikke». Se CLAUDE.md 1b-7 punkt 1."""
    assert _utgitt({}) == ""
    assert _utgitt({"Last-Modified": "ikke en dato"}) == ""



def test_publisert_i_gir_dato_uten_paafunnet_klokkeslett():
    """`sources/reguleringsomraader.publisert_i()` er den andre skriveren.

    Den leser «Publisert: 29.06.2026» fra HIs egen metadatablokk. Det
    kilden oppgir er en DATO, og det er en dato som skrives — ikke en dato
    med et klokkeslett vi har funnet på.

    Sorteringen i `snapshot.publisert()` er leksikografisk på ISO-strenger,
    og en ren dato sorterer foran ethvert tidsstempel på samme dag. Det er
    riktig vei: «senest denne datoen» er en øvre grense, som `fetched_at`
    er det for `published_at`.
    """
    ut = publisert_i("<div>Publisert: <em>29.06.2026</em></div>")
    assert ut == "2026-06-29"
    assert dt.date.fromisoformat(ut) == dt.date(2026, 6, 29)
    # Ingen tidssone å ta feil av, fordi det ikke er noe klokkeslett.
    assert "T" not in ut and "+" not in ut


def test_publisert_i_uten_dato_er_tom_ikke_klokka():
    """Samme regel som `_utgitt`: «vet ikke» skal se ut som «vet ikke»."""
    assert publisert_i("<html>ingen dato her</html>") == ""
    assert publisert_i("") == ""


def test_ren_dato_sorterer_foran_tidsstempel_samme_dag():
    """Antakelsen som gjør den rene datoen trygg, testet i stedet for trodd."""
    assert "2026-06-29" < "2026-06-29T00:00:00+00:00"
    assert "2026-06-29" < "2026-06-30"
    assert "2026-06-28T23:59:59+00:00" < "2026-06-29"


def test_stempl_skriver_fetched_at_i_utc():
    """`fetched_at` er RESERVEN for `published_at` i `snapshot.publisert()`.

    Den sammenlignes derfor mot ekte utgivelsestidspunkter i den samme
    leksikografiske sorteringen, og må bære samme offset.
    """
    obs = Observation(entity_id="1", entity_type="lokalitet", entity_name="X",
                      field="f", value="v", source="k", observed_at="2026-01-01")
    stemplet = runner.stempl([obs], source_version="1", raw_hash="h")
    assert stemplet[0].fetched_at.endswith("+00:00")
    # ... og det er et EKTE tidspunkt, ikke en streng som tilfeldigvis
    # slutter riktig.
    naar = dt.datetime.fromisoformat(stemplet[0].fetched_at)
    assert naar.utcoffset() == dt.timedelta(0)


# ---- 3. vaktene: feiler når en NY kilde bryter regelen -----------------

def _kildefiler():
    return [p for p in SKRIVENDE if p.exists()]


def _kall(node) -> str:
    """Navnet på det som kalles: `dt.datetime.now` -> `now`, `_utgitt` -> `_utgitt`."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def test_ingen_kilde_setter_published_at_uten_a_normalisere():
    """Skriver en kilde `self.published_at = <noe annet enn et normalisert
    kall>`, feller den denne.

    Dette er testen oppgaven ba om: den feiler hvis en kilde skriver et
    annet offset. Den kan ikke lese en HTTP-header som ikke er hentet
    ennå, så den prøver det den kan prøve — at verdien går gjennom en
    funksjon som er testet for å normalisere, og ikke rett inn fra en
    header, en config-verdi eller en `strptime()` uten tidssone.

    En ny kilde som trenger en annen normaliserer: skriv den, gi den en
    oppførselstest som `test_utgitt_normaliserer_til_utc`, og før navnet
    i `SKRIVERE_AV_PUBLISHED_AT`. Rekkefølgen er poenget.
    """
    brudd = []
    for fil in sorted((ROT / "sources").glob("*.py")):
        tre = ast.parse(fil.read_text(encoding="utf-8"))
        for node in ast.walk(tre):
            if not isinstance(node, ast.Assign):
                continue
            for mal in node.targets:
                if not (isinstance(mal, ast.Attribute)
                        and mal.attr == "published_at"):
                    continue
                if (isinstance(node.value, ast.Call)
                        and _kall(node.value) in SKRIVERE_AV_PUBLISHED_AT):
                    continue
                brudd.append(f"{fil.relative_to(ROT)}:{node.lineno}")
    assert not brudd, (
        f"published_at settes uten en kjent UTC-normaliserer: {brudd}. "
        f"Sorteringen i snapshot.publisert() og sammenligningen i "
        f"diff.revisjon() er LEKSIKOGRAFISK på ISO-strenger — et annet "
        f"offset gir feil rekkefølge uten å feile."
    )


def test_ingen_iso_streng_bygges_av_en_klokke_uten_tidssone():
    """`datetime.now().isoformat()` gir en streng UTEN offset.

    Den sorterer foran alt med `+00:00` (`'2'` < `'+'` er usant, men
    strengen er kortere og bryter av der de andre har `+`), og den er
    dessuten lokal tid utgitt som om den var absolutt. Begge deler er
    stille feil.

    Regelen er smal med vilje: den treffer bare tidspunkter som blir til
    ISO-STRENGER. `backfill.py` bruker `dt.datetime.now()` uten tidssone
    til et konsollprefiks, og det er ikke data.
    """
    klokker = {"now", "utcnow", "fromtimestamp", "today"}
    brudd = []
    for fil in _kildefiler():
        tre = ast.parse(fil.read_text(encoding="utf-8"))
        for node in ast.walk(tre):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "isoformat"):
                continue
            # Gå ned kjeden: .now(...).date().isoformat() osv.
            ledd = node.func.value
            while isinstance(ledd, ast.Call):
                navn = _kall(ledd)
                if navn in klokker:
                    if navn in ("utcnow", "today") or not ledd.args:
                        brudd.append(
                            f"{fil.relative_to(ROT)}:{ledd.lineno} ({navn})")
                    break
                ledd = (ledd.func.value if isinstance(ledd.func, ast.Attribute)
                        else None)
                if ledd is None:
                    break
    assert not brudd, (
        f"ISO-streng bygget av en klokke uten tidssone: {brudd}. "
        f"Send `timezone.utc` inn — alt som sammenlignes leksikografisk "
        f"må bære samme offset."
    )


def test_vakten_ville_sett_et_brudd():
    """Vakten over er verdiløs hvis den ikke kan felle noe.

    Den er syntaktisk, og en syntaktisk vakt som aldri er sett feile er
    en vakt ingen vet virker. Samme grunn som at volumvakten har en test
    med et volumfall i.
    """
    tre = ast.parse("import datetime as dt\nx = dt.datetime.now().isoformat()\n")
    funn = []
    for node in ast.walk(tre):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "isoformat"):
            ledd = node.func.value
            if isinstance(ledd, ast.Call) and _kall(ledd) == "now" and not ledd.args:
                funn.append(node.lineno)
    assert funn == [2]
