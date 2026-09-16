"""Taushet mot tilbaketrekking.

`diff` kunne ikke skille «kilden uttaler seg ikke om denne cellen» fra
«kilden har fjernet verdien» fram til 15.09.2026. Begge ble en rad med
`new_value = null`, og den raden leses som en tilbaketrekking. Målt over
hele changeloggen: 36 av 1873 revisjonsrader, og 34 av dem hos
trafikklysvedtak, der ingen forskrift noensinne har trukket tilbake en
farge.

Den viktigste testen her er `test_erklaert_domene_vinner_over_emisjonene`.
For hver kilde i repoet i dag er domenet nøyaktig lik det som ble
emittert, så et uttrekk som bare returnerte «det jeg emitterte» ville
bestått alle de andre testene. Den ene konstruerer tilfellet der de to
skiller lag, og er det eneste som holder regelen i live.
"""

import polars as pl
import pytest

from core import changelog, diff, domene, snapshot
from core import raw as raw_arkiv
from core.contract import Observation, Source
from core.runner import stempl


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(changelog, "CHANGELOG_DIR", tmp_path / "changelog")
    monkeypatch.setattr(raw_arkiv, "ARKIV_DIR", tmp_path / "arkiv")
    return tmp_path


def _obs(entity_id, field="farge", value="gronn",
         observed_at="2024-12-31", source="vedtak"):
    return Observation(
        entity_id=entity_id, entity_type="produksjonsomraade",
        entity_name="", field=field, value=value, source=source,
        observed_at=observed_at,
    )


class _Erklaerer(Source):
    """Bærer en ferdig erklæring. `stempl()` tar KILDEN og ikke verdien,
    så selv en syntetisk test må gå gjennom den samme døra."""

    name = "vedtak"

    def __init__(self, dom):
        self.domene = dom


def _ramme(observasjoner, dom, utgitt="2026-08-20T12:00:00+00:00"):
    """Et snapshot med domenet stemplet på, slik kjernen gjør det."""
    return snapshot.to_frame(stempl(
        observasjoner, source_version="1", raw_hash="x",
        fetched_at="2026-09-15T00:00:00+00:00", published_at=utgitt,
        kilde=_Erklaerer(dom),
    ))


# ---- den som holder regelen i live ------------------------------------

def test_erklaert_domene_vinner_over_emisjonene():
    """Domenet skal ERKLÆRES av uttrekket, aldri utledes av `parse()`.

    Kroppen her uttaler seg om PO3, PO4 OG PO5, men gir bare verdi for
    PO3 og PO4. PO5 er tilfellet «Produksjonsområde 5: ingen justering» —
    kroppen har omtalt området og latt være å gi det en farge, og det er
    en EKTE fjerning.

    Utledet man domenet av emisjonene, ville PO5 falt utenfor, fraværet
    blitt lest som taushet, og raden forsvunnet. Da er en ekte hendelse
    undertrykt av en mekanisme som er riktig i akkurat de tilfellene der
    erklæring og emisjon faller sammen — og det gjør de for hver kilde i
    repoet i dag. CLAUDE.md 1b-2.
    """
    eldre = _ramme([_obs("3"), _obs("4"), _obs("5")],
                   dom=domene.UTTOMMENDE,
                   utgitt="2024-03-22T12:00:00+00:00")

    # Erklærer TRE par, emitterer TO. PO5 ble omtalt uten å få verdi.
    nyere = _ramme([_obs("3", value="rod"), _obs("4")],
                   dom={("3", "farge"), ("4", "farge"), ("5", "farge")})

    endr = diff.revisjon_mellom(eldre, nyere, "2024-12-31")
    typer = dict(zip(endr["entity_id"], endr["change_type"]))

    assert typer.get("3") == diff.REVIDERT      # gronn -> rod, ekte endring
    assert "5" in typer, (
        "PO5 ble ERKLÆRT omtalt uten å få en verdi. Det er en ekte "
        "fjerning, og raden skal overleve. Forsvant den, er domenet "
        "utledet av emisjonene i stedet for lest av kroppen."
    )
    assert endr.filter(pl.col("entity_id") == "5")["new_value"][0] is None


def test_domenet_kan_ikke_vaere_smalere_enn_emisjonene():
    """Emitteres et par som ikke er erklært, er erklæringen feil.

    Uten denne kontrollen kunne et uttrekk erklære et tomt domene og
    likevel levere rader, og da ville hvert eneste fravær blitt lest som
    taushet.
    """
    with pytest.raises(ValueError, match="uten å stå i det erklærte"):
        domene.serialiser({("3", "farge")},
                          {("3", "farge"), ("4", "farge")})


# ---- de fire tilstandene ----------------------------------------------

def test_de_fire_tilstandene_serialiseres_hver_for_seg():
    assert domene.serialiser(None, {("1", "a")}) == ""
    assert domene.serialiser(domene.UTTOMMENDE, {("1", "a")}) == "*"
    assert domene.serialiser({("1", "a")}, {("1", "a")}) == "{}"
    assert domene.serialiser({("1", "a"), ("2", "b")},
                             {("1", "a")}) == '[["2","b"]]'


def test_bare_differansen_lagres():
    """Hele domenet på hver rad ble målt til 24x filstørrelse hos
    ekspertgruppen og forkastet. Snapshotet bærer alt hva som kom ut."""
    stort = {(str(n), f) for n in range(1, 14)
             for f in ("kategori", "usikkerhet", "retning")}
    assert domene.serialiser(stort, stort) == "{}"


def test_ukjent_domene_oppforer_seg_som_for():
    """1873 revisjonsrader er skrevet uten feltet. Fallbacken skal være
    dagens oppførsel, ikke stille undertrykking."""
    assert domene.uttaler_seg_om("", set(), ("9", "farge")) is True
    assert domene.uttaler_seg_om(None, set(), ("9", "farge")) is True


def test_uttommende_kropp_beholder_fjerningene():
    """biomasse har 1809 revisjonsrader og null taushet. En kropp som
    dekker hele nøkkelrommet skal fortsatt kunne si at noe forsvant."""
    assert domene.uttaler_seg_om("*", set(), ("9", "farge")) is True

    eldre = _ramme([_obs("3"), _obs("9")], dom=domene.UTTOMMENDE,
                   utgitt="2024-03-22T12:00:00+00:00")
    nyere = _ramme([_obs("3")], dom=domene.UTTOMMENDE)
    endr = diff.revisjon_mellom(eldre, nyere, "2024-12-31")
    assert "9" in list(endr["entity_id"])


def test_ulesbart_domene_gir_ukjent_og_ikke_unntak():
    """Inndata fra en fil på disk som kan være skrevet av en eldre
    versjon. En leser som kaster gjør historikken uleselig."""
    assert domene.les("{ikke json") is None
    assert domene.uttaler_seg_om("{ikke json", set(), ("1", "a")) is True


def test_domenet_krever_par_og_ikke_entiteter():
    """Granulariteten er (entity_id, field). Ekspertgruppen tier om ETT
    felt for PO6 mens den svarer for de andre — et domene på entitetsnivå
    ville latt de to radene stå usanne."""
    with pytest.raises(ValueError, match="ikke er et"):
        domene.normaliser(["6", "7"])


# ---- aksene ------------------------------------------------------------

def test_taushet_undertrykkes_paa_revisjonsaksen():
    """Det som var de 34 radene: en nyere kropp som ikke gjentar en
    celle, har ikke trukket den tilbake."""
    eldre = _ramme([_obs("1"), _obs("3"), _obs("9")],
                   dom=domene.UTTOMMENDE,
                   utgitt="2024-03-22T12:00:00+00:00")
    nyere = _ramme([_obs("3", value="rod")],
                   dom={("3", "farge")})

    endr = diff.revisjon_mellom(eldre, nyere, "2024-12-31")
    assert list(endr["entity_id"]) == ["3"]
    assert endr["change_type"][0] == diff.REVIDERT


def test_tidsaksen_beholder_borte():
    """`compare()` sammenligner TO ULIKE observed_at. «PO9 har ingen
    farge i 2026» er sant om 2026 uansett hvorfor kroppen tidde, og av
    ekspertgruppens 358 borte-rader er 318 et helt felt som forsvant fra
    rapportserien. Det ER en endring i hva kilden publiserer."""
    from core import diff as d
    eldre = _ramme([_obs("1"), _obs("9")],
                   dom={("1", "farge"), ("9", "farge")},
                   utgitt="2024-03-22T12:00:00+00:00")
    nyere = _ramme([_obs("1", observed_at="2026-12-31")],
                   dom={("1", "farge")})
    endr = d.revisjon_mellom(eldre, nyere, "2026-12-31")
    # revisjonsaksen undertrykker
    assert "9" not in list(endr["entity_id"])
    # men selve `borte`-oppførselen i compare() er urørt — se
    # test_pipeline for den; her holder det at TAUSHET ikke er i
    # compare()s ordforråd.
    assert d.TAUSHET in d.IKKE_BEVEGELSE


# ---- lesing av det som alt er skrevet ---------------------------------

def _frossen(source, change_type, entity_id="1", field="farge",
             dom=None, observed_at="2020-12-31"):
    rad = {
        "entity_id": entity_id, "entity_type": "produksjonsomraade",
        "entity_name": "", "field": field, "old_value": "gronn",
        "new_value": None, "change_type": change_type, "source": source,
        "observed_at": observed_at, "forrige_observed_at": observed_at,
        "forrige_fetched_at": "", "published_at": "2022-06-07T12:00:00+00:00",
        "forrige_published_at": "2020-02-04T12:00:00+00:00",
    }
    if dom is not None:
        rad["domene"] = dom
    return pl.DataFrame([rad], schema_overrides={"new_value": pl.Utf8})


def test_merk_taushet_tar_de_frosne_radene():
    """De 34 er append-only og kan ikke rettes. De merkes ved LESING,
    samme form som merk_utvalgsutvidelse()."""
    f = _frossen("trafikklysvedtak", diff.REVIDERT)
    assert changelog.merk_taushet(f)["change_type"][0] == diff.TAUSHET


def test_merk_taushet_rorer_ikke_andre_kilder():
    """lusetall har 35587 borte-rader og sjotemperatur 12220, og de er
    entiteter som FAKTISK forsvant fra et register."""
    for kilde in ("biomasse", "lusetall", "sjotemperatur", "romming"):
        f = _frossen(kilde, diff.REVIDERT)
        assert changelog.merk_taushet(f)["change_type"][0] == diff.REVIDERT


def test_radens_eget_domene_slaar_kildelista():
    """Bærer raden et domene, er det presist og skal vinne over
    TAUSHETSKILDER — også når det sier at fraværet ER en fjerning."""
    f = _frossen("trafikklysvedtak", diff.REVIDERT, dom=domene.UTTOMMENDE)
    assert changelog.merk_taushet(f)["change_type"][0] == diff.REVIDERT

    f = _frossen("biomasse", diff.REVIDERT, dom="{}")
    assert changelog.merk_taushet(f)["change_type"][0] == diff.TAUSHET


def test_merk_taushet_lar_tidsaksen_staa_som_standard():
    f = _frossen("ekspertgruppen", "borte")
    assert changelog.merk_taushet(f)["change_type"][0] == "borte"
    assert changelog.merk_taushet(
        f, ogsaa_tidsaksen=True)["change_type"][0] == diff.TAUSHET


def test_merk_taushet_rorer_ingen_fil(isolert):
    f = _frossen("trafikklysvedtak", diff.REVIDERT)
    changelog.merk_taushet(f)
    assert f["change_type"][0] == diff.REVIDERT      # originalen urørt


def test_taushet_er_ikke_bevegelse():
    """Som utvalgsutvidelse og revidert: ingenting skjedde i sjøen."""
    f = _frossen("trafikklysvedtak", diff.REVIDERT)
    assert diff.bevegelse(changelog.merk_taushet(f)).is_empty()


# ---- kontrakten --------------------------------------------------------

def test_standarden_er_ukjent_og_ikke_uttommende():
    """En kilde som aldri har tenkt på spørsmålet skal ikke automatisk
    påstå at kroppen dekker alt. Samme skille som utvalg gjør."""
    assert Source.domene is None
    assert Observation(
        "1", "t", "", "f", "v", "s", "2026-01-01").domene == ""


def test_kjernen_stempler_domenet_ikke_kilden():
    """Kilden oppgir det, kjernen stempler det — som utvalg og
    published_at. En kilde som satte feltet selv ville kunne glemme det
    på en rad."""
    obs = stempl([_obs("3")], source_version="1", raw_hash="x",
                 kilde=_Erklaerer({("3", "farge")}))
    assert obs[0].domene == "{}"


def test_domenet_kan_ikke_leses_for_parse_har_kjort():
    """Rekkefølgefella er LUKKET, og dette er verifiseringen.

    Fram til 15.09.2026 tok `stempl()` domenet som en VERDI. `domene`
    settes av `parse()` mens den leser kroppen, og kallerens argumenter
    evalueres før en generators kropp kjører — så
    `stempl(kilde.parse(...), domene=kilde.domene)` leste verdien fra
    forrige kall, eller None på det første. Den ble holdt i sjakk av at
    hvert av de sju kallstedene skrev `list(kilde.parse(...))`: en regel
    ingen kan SE ved lesing, og som et åttende kallsted ikke ville
    arvet.

    Nå tar `stempl()` KILDEN. Strømmen materialiseres inni, og
    erklæringen leses etterpå. Testen sender derfor generatoren rett inn
    — nøyaktig kallformen som FØR ga tom streng — og krever at domenet
    likevel er riktig.

    Den gamle testen kunne vise at den feilaktige veien feilet. Den
    veien finnes ikke lenger å uttrykke: `domene` er ikke et argument,
    så et kallsted KAN ikke lese det for tidlig. Det som kan sjekkes er
    at den tidligere ødelagte formen nå er riktig, og det er dette.
    """
    class Sen(Source):
        name = "sen"

        def fetch(self, kjoredato):
            return [("3", "farge"), ("4", "farge")]

        def parse(self, raw, observed_at):
            self.domene = set(raw)
            for eid, felt in raw:
                yield Observation(eid, "po", "", felt, "gronn",
                                  self.name, observed_at)

    kilde = Sen()
    rå = kilde.fetch("2026-01-01")
    assert kilde.domene is None, "parse() har ikke kjørt ennå"

    # Generatoren rett inn — den formen som FØR leste domenet for tidlig.
    obs = stempl(kilde.parse(rå, "2026-01-01"), source_version="1",
                 raw_hash="x", kilde=kilde)

    assert {o.domene for o in obs} == {"{}"}, (
        "domenet skal beskrive DETTE kallet. Er det tomt, leses "
        "erklæringen før parse() har satt den."
    )


def test_stempl_krever_kilden():
    """Nøkkelordkrav og ikke standardverdi. En standard ville gjort et
    glemt argument usynlig — og usynlig er nøyaktig det den gamle
    list()-regelen var."""
    with pytest.raises(TypeError, match="kilde"):
        stempl([_obs("3")], source_version="1", raw_hash="x")


def test_kilde_uten_erklaering_gir_ukjent():
    """En kilde som aldri har tenkt på spørsmålet skal lese som «vet
    ikke», ikke som en påstand."""
    obs = stempl([_obs("3")], source_version="1", raw_hash="x",
                 kilde=Source())
    assert obs[0].domene == ""
