"""Reproduserbarhet: kan noen svare på hva et analysetall hvilte på?

En analyse er ikke ferdig når tallet er riktig. Den er ferdig når noen
tre måneder senere kan si om et nytt tall er et nytt FUNN eller et endret
VALG. `rho = +0,761` er en egenskap ved dataene OG ved et dusin valg som
ikke sto noe sted før 26.08.2026.

Tre krav testes her, og de er de tre loggen finnes for:

  1. To kjøringer uten endring gir IDENTISKE logger, bortsett fra
     tidspunktet for selve kjøringen.
  2. Endres ett valg, skiller loggene seg på NØYAKTIG det valget.
  3. Versjonsvalget er et VALG. Der en dato finnes i flere versjoner med
     ulikt utgivelsestidspunkt, sier loggen hvilken påstand tallet
     hviler på — med løpenummer OG `published_at`, fordi de to sluttet å
     være samme opplysning 26.08.2026 (F14).
"""

from dataclasses import replace

import pytest

from analyse import kjoringslogg
from core import snapshot
from core.contract import Observation


@pytest.fixture
def isolert(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    return tmp_path


def _skriv(observed_at, verdi, *, fetched_at, published_at="",
           source_version="1", kilde="biomasse"):
    obs = Observation(
        entity_id="1", entity_type="produksjonsomraade", entity_name="Ryfylket",
        field="beholdning_antall", value=str(verdi), source=kilde,
        observed_at=observed_at)
    return snapshot.write([replace(obs, fetched_at=fetched_at,
                                   published_at=published_at,
                                   source_version=source_version,
                                   raw_hash="h", utvalg="{}")], observed_at)[0]


def _wayback_oppsettet(tmp_path):
    """To versjoner av samme måned, der HØYESTE LØPENUMMER ER ELDST.

    Dette er situasjonen på disk etter 26.08.2026, gjengitt i det små:
    basefila er hentet 25.08.2026 og har ukjent utgivelse,
    Wayback-kopien er skrevet som `.2` og oppgir at Fiskeridirektoratet
    utga den 20.07.2024. Løpenummeret peker én vei, kronologien den
    andre.
    """
    _skriv("2017-10-31", 100, fetched_at="2026-08-25T21:51:20+00:00")
    _skriv("2017-10-31", 90, fetched_at="2026-08-26T05:20:31+00:00",
           published_at="2024-07-20T04:40:53+00:00")


def _verdier(lest):
    return [r["value"][0] for _, r in lest]


def _uten_tidspunkt(linjer):
    return [rad for rad in linjer if not rad.startswith("kjort_at")]


# ---- 1. to like kjøringer --------------------------------------------

def test_to_kjoringer_uten_endring_gir_identiske_logger(isolert, tmp_path):
    """Punkt 4, første halvdel.

    Faller denne, er loggen ikke en logg over valg — den er en logg over
    valg PLUSS noe uspesifisert som varierer mellom kjøringer, og da kan
    en forskjell mellom to logger ikke leses som et endret valg.
    """
    _wayback_oppsettet(tmp_path)

    def kjor():
        logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "proeve.log")
        logg.valg("avgrensning.fra_aar", 2018)
        logg.les("biomasse", "2017-01-01", "2018-01-01")
        return logg.linjer()

    a, b = kjor(), kjor()
    assert _uten_tidspunkt(a) == _uten_tidspunkt(b)
    # ... og tidspunktet SKAL være der. En logg uten det kan ikke si
    # hvilken av to kjøringer som var sist.
    assert any(rad.startswith("kjort_at") for rad in a)


def test_kjort_at_slaas_opp_en_gang(isolert, tmp_path):
    """Klokka leses i __init__ og ingen andre steder.

    To oppslag i samme kjøring er F7 i miniatyr: to tall som kan svare
    ulikt, her om når analysen ble kjørt.
    """
    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    forst = [rad for rad in logg.linjer() if rad.startswith("kjort_at")]
    logg.valg("noe", 1)
    etterpaa = [rad for rad in logg.linjer() if rad.startswith("kjort_at")]
    assert forst == etterpaa == [f"{'kjort_at':<40} {logg.kjort_at}"]


# ---- 2. ett endret valg ----------------------------------------------

def test_ett_endret_valg_gir_forskjell_pa_nettopp_det(isolert, tmp_path):
    """Punkt 4, andre halvdel.

    Endres `fra_aar`, skal `avgrensning.fra_aar` være den ENESTE linja
    som skiller seg. En logg der ett valg forplanter seg til fem linjer
    kan ikke brukes til å finne ut hva som endret seg.
    """
    _wayback_oppsettet(tmp_path)

    def kjor(fra_aar):
        logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "proeve.log")
        logg.valg("avgrensning.fra_aar", fra_aar)
        logg.les("biomasse", "2017-01-01", "2018-01-01")
        return _uten_tidspunkt(logg.linjer())

    a, b = kjor(2018), kjor(2019)
    ulike = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(a) == len(b)
    assert len(ulike) == 1
    assert ulike[0][0].startswith("avgrensning.fra_aar")


def test_endret_versjonsvalg_skiller_seg_bare_pa_versjonslinjene(isolert, tmp_path):
    """Samme krav for det valget som er nytt: versjonen.

    Alle linjer som skiller seg skal handle om hvilken versjon som ble
    lest. Ingen av dem skal handle om avgrensning, mål eller fasit — de
    valgene ble ikke rørt.
    """
    _wayback_oppsettet(tmp_path)

    def kjor(versjonsvalg):
        logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "proeve.log")
        logg.valg("avgrensning.fra_aar", 2018)
        logg.les("biomasse", "2017-01-01", "2018-01-01",
                 versjonsvalg=versjonsvalg)
        return _uten_tidspunkt(logg.linjer())

    a = kjor(kjoringslogg.GJELDENDE)
    b = kjor(kjoringslogg.FORSTE)
    ulike = [x for x, y in zip(a, b) if x != y]
    assert ulike, "versjonsvalget kom ikke fram i loggen i det hele tatt"
    for rad in ulike:
        assert ("versjonsvalg" in rad or "lopenummer" in rad
                or "published_at" in rad or "fetched_at" in rad
                or rad.lstrip().startswith("biomasse")), rad


# ---- 3. versjonsvalget er et valg -------------------------------------

def test_gjeldende_er_sist_utgitt_ikke_hoyeste_lopenummer(isolert, tmp_path):
    """F14 i analyselaget.

    `.2` er Wayback-kopien og TO ÅR ELDRE enn basefila. En analyse som
    leste «høyeste løpenummer» ville brukt 2024-påstanden som om den var
    den gjeldende. Dette er den samme feilen `previous()` og
    `les_mellom()` hadde, én etasje opp.
    """
    _wayback_oppsettet(tmp_path)
    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")

    gjeldende = logg.les("biomasse", "2017-01-01", "2018-01-01")
    assert _verdier(gjeldende) == ["100"], "gjeldende skal være basefila"

    logg2 = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p2.log")
    forste = logg2.les("biomasse", "2017-01-01", "2018-01-01",
                       versjonsvalg=kjoringslogg.FORSTE)
    assert _verdier(forste) == ["90"], "først utgitt skal være Wayback-kopien"


def test_loggen_forer_lopenummer_og_published_at_per_fil(isolert, tmp_path):
    """Punkt 2: datoen alene er ikke nok.

    «2017-10-31» navngir en MÅNED. Hvilken PÅSTAND om den måneden tallet
    hviler på, avgjøres av versjonen — og de to skilles bare av
    løpenummeret og utgivelsestidspunktet sammen.
    """
    _wayback_oppsettet(tmp_path)
    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    logg.les("biomasse", "2017-01-01", "2018-01-01",
             versjonsvalg=kjoringslogg.FORSTE)

    fillinjer = [rad for rad in logg.linjer()
                 if rad.lstrip().startswith("biomasse  2017-10-31")]
    assert len(fillinjer) == 1
    assert ".2" in fillinjer[0]
    assert "utgitt=2024-07-20T04:40:53+00:00" in fillinjer[0]
    assert "hentet=2026-08-26T05:20:31+00:00" in fillinjer[0]


def test_en_kilde_kan_ikke_leses_med_to_versjonsvalg(isolert, tmp_path):
    """Halve resultatet på én påstand og halve på en annen er ikke en
    analyse — det er to analyser lagt oppå hverandre, og loggen kan ikke
    si hvilken halvdel som er hvilken."""
    _wayback_oppsettet(tmp_path)
    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    logg.les("biomasse", "2017-01-01", "2018-01-01")
    with pytest.raises(ValueError, match="versjonsvalg"):
        logg.les("biomasse", "2017-01-01", "2018-01-01",
                 versjonsvalg=kjoringslogg.FORSTE)


def test_pinnet_lopenummer_som_mangler_forkastes_synlig(isolert, tmp_path):
    """En dato uten den etterspurte versjonen skal FØRES, ikke forsvinne.

    Stille bortfall er verre enn en feil: tallet blir mindre og ingenting
    sier hvorfor. Samme grunn som at `diff.compare()` MERKER en
    utvalgsutvidelse framfor å slette radene (1b-3).
    """
    _wayback_oppsettet(tmp_path)
    _skriv("2017-11-30", 200, fetched_at="2026-08-25T21:51:20+00:00")

    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    lest = logg.les("biomasse", "2017-01-01", "2018-01-01", versjonsvalg=2)

    assert [d for d, _ in lest] == ["2017-10-31"]
    tekst = "\n".join(logg.linjer())
    assert "lesing.biomasse.forkastet" in tekst
    assert "2017-11-30" in tekst
    assert "løpenummer 2" in tekst


def test_behold_skiller_valgt_bort_fra_fantes_ikke(isolert, tmp_path):
    """En dato analysen VALGTE BORT skal stå i loggen med grunnen.

    ISO-årsavgrensningen i lusepress_mot_fasit forkaster fire
    desemberuker i 2017 fordi de tilhører ISO-året 2018. Det er et valg,
    ikke et hull, og de to gir ulike tall.
    """
    _wayback_oppsettet(tmp_path)
    _skriv("2017-11-30", 200, fetched_at="2026-08-25T21:51:20+00:00")

    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    logg.les("biomasse", "2017-01-01", "2018-01-01",
             behold=lambda d: d != "2017-11-30",
             forkastningsgrunn="ISO-år utenfor [2018, 2026]")

    tekst = "\n".join(logg.linjer())
    assert "ISO-år utenfor [2018, 2026]: 2017-11-30" in tekst


# ---- loggens innhold --------------------------------------------------

def test_loggen_forer_personformer_uten_at_kalleren_ber_om_det(isolert, tmp_path):
    """Lista virker ved LESING, i `snapshot._les()`. Da skal den føres av
    den som leser, ikke av hver analyse for seg — en analyse som glemmer
    det gir en logg som ser komplett ut."""
    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    tekst = "\n".join(logg.linjer())
    assert "personformer" in tekst
    assert "ENK" in tekst


def test_fasitens_innhold_hashes_ikke_bare_banen(isolert, tmp_path):
    """En CSV kan redigeres uten at noe annet endrer seg. Da er banen den
    samme og tallet et annet, og bare innholds-hashen fanger det."""
    fasit = tmp_path / "fasit.csv"
    fasit.write_text("po,aar\n1,2020\n", encoding="utf-8")

    def kjor():
        logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
        logg.fil("fasit", fasit)
        return [rad for rad in logg.linjer() if rad.startswith("fasit.sha256")]

    forst = kjor()
    fasit.write_text("po,aar\n1,2021\n", encoding="utf-8")
    assert kjor() != forst


def test_loggen_skrives_ved_siden_av_resultatet(isolert, tmp_path):
    """Punkt 3: en analyse leser ikke git. Pekeren fra resultatfila må gå
    til noe som ligger der resultatet ligger."""
    sti = tmp_path / "ut" / "lusepress.kjoring.log"
    logg = kjoringslogg.Kjoringslogg("proeve", sti)
    skrevet = logg.skriv()
    assert skrevet == sti and sti.exists()
    assert logg.peker == "lusepress.kjoring.log"
    assert sti.read_text(encoding="utf-8").startswith("# kjøringslogg")


# ==================================================== versjonsvalget ALLE

def _to_versjoner_av_2024():
    """2024 skrevet av 2024-rapporten, deretter revidert av 2025-rapporten.

    Revisjonen restaterer BARE kategorien — den nevner ikke ROC, og har
    dermed ikke trukket den tilbake.
    """
    def obs(felt, verdi):
        return Observation(
            entity_id="1", entity_type="produksjonsomraade", entity_name="PO1",
            field=felt, value=verdi, source="ekspertgruppen",
            observed_at="2024-12-31")

    for felt, verdi, utgitt in (("roc", "12", "2024-11-29T08:42:16+00:00"),
                                ("kategori", "moderat", "2025-11-20T15:51:48+00:00")):
        snapshot.write([replace(obs(felt, verdi), fetched_at="2026-09-01T00:00:00+00:00",
                                published_at=utgitt, source_version="3",
                                raw_hash="h", utvalg="{}")], "2024-12-31")


def test_alle_gir_hver_versjon_av_hver_dato(tmp_path, monkeypatch):
    """GJELDENDE gir én fil per dato og svarer på «hva sier kilden nå om
    denne DATOEN». For et enkelt FELT er det feil spørsmål når kilden har
    revidert bare deler av året.

    Målt 01.09.2026: 2025-rapporten reviderer 2024, men restaterer bare
    kategorien. En analyse som leste GJELDENDE mistet hele 2024s ROC og
    fikk n = 46 der disken har 58, uten at noe sa fra.
    """
    from analyse import kjoringslogg

    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    _to_versjoner_av_2024()

    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    lest = logg.les("ekspertgruppen", "2000-01-01", "2099-12-31",
                    versjonsvalg=kjoringslogg.ALLE)

    assert len(lest) == 2, "begge versjonene skal komme ut"
    felter = {r["field"][0] for _, r in lest}
    assert felter == {"roc", "kategori"}


def test_alle_foerer_hver_lesing_i_loggen(tmp_path, monkeypatch):
    """Loggen skrives fortsatt AV lesingen. Det er bredden som er valgt,
    ikke hvilken påstand som gjelder."""
    from analyse import kjoringslogg

    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    _to_versjoner_av_2024()

    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    logg.les("ekspertgruppen", "2000-01-01", "2099-12-31",
             versjonsvalg=kjoringslogg.ALLE)
    tekst = "\n".join(logg.linjer())

    assert tekst.count("2024-12-31") >= 2
    assert "2024-11-29" in tekst and "2025-11-20" in tekst


def test_alle_er_ett_valg_og_kan_ikke_blandes(tmp_path, monkeypatch):
    """Vakten mot blandede versjonsvalg gjelder ALLE som de andre — den
    ble ikke myket opp for å slippe dette igjennom."""
    from analyse import kjoringslogg

    monkeypatch.setattr(snapshot, "RAW_DIR", tmp_path / "raw")
    _to_versjoner_av_2024()

    logg = kjoringslogg.Kjoringslogg("proeve", tmp_path / "p.log")
    logg.les("ekspertgruppen", "2000-01-01", "2099-12-31",
             versjonsvalg=kjoringslogg.ALLE)
    with pytest.raises(ValueError, match="versjonsvalg"):
        logg.les("ekspertgruppen", "2000-01-01", "2099-12-31",
                 versjonsvalg=kjoringslogg.GJELDENDE)
