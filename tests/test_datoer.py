"""Datoer som eldes: byggedatoen og «sist lest» slås opp ett sted, og to
sider i samme bygg oppgir ikke ulik dato for samme ting.

/kommune/ sa «Fiskeridirektoratets side sist lest 10.11.2026» mens
arkivjobben leser den tre ganger i døgnet. Datoen var riktig da siden ble
bygget og ble eldre for hver dag til neste bygg, uten at siden sa hva den
var. Byggedatoen («Oppdatert») ble slått opp sju steder med
`date.today()`, i lokal tid.

MÅLT 23.11.2026 på bygget av f2c2896: /kommune/ (144 sider) oppga
«Data hentet 31. august 2026» om akvakultursnapshotet 2026-08-31, og
/fasiten/ (2 sider) «Data fra uke 36, 2026» uten hentetidspunkt om det
samme snapshotet. To oppslag for samme kilde.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
hoppes over uten.
"""
import datetime as dt
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import pytest

import nettsted


# ------------------------------------------------------- ett oppslag

def test_byggedatoen_er_utc_og_samme_hele_bygget(monkeypatch):
    class Klokke(dt.datetime):
        svar = [dt.datetime(2026, 11, 24, 0, 30, tzinfo=dt.timezone.utc),
                dt.datetime(2026, 11, 25, 0, 30, tzinfo=dt.timezone.utc)]

        @classmethod
        def now(cls, tz=None):
            return cls.svar.pop(0)

    monkeypatch.setattr(nettsted.dt, "datetime", Klokke)
    nettsted.nytt_bygg()
    assert nettsted.byggedato() == "2026-11-24"
    # Klokka har gått videre, men bygget er det samme.
    assert nettsted.byggedato() == "2026-11-24"
    nettsted.nytt_bygg()
    assert nettsted.byggedato() == "2026-11-25"


def test_ingen_side_slaar_opp_klokka_selv():
    kilde = (Path(nettsted.__file__)).read_text(encoding="utf-8")
    kode = "\n".join(l for l in kilde.splitlines() if not l.lstrip().startswith("#"))
    assert "date.today()" not in kode
    assert kode.count("datetime.now(") == 1   # i byggedato()


def test_sist_lest_slaas_opp_en_gang_per_bygg(monkeypatch):
    svar = iter([{"publisert": False, "lest": "2026-11-20"},
                 {"publisert": False, "lest": "2026-11-23"}])
    monkeypatch.setattr(nettsted, "_les_fordeling_status", lambda: next(svar))
    nettsted.nytt_bygg()
    assert nettsted._fordeling_status()["lest"] == "2026-11-20"
    assert nettsted._fordeling_status()["lest"] == "2026-11-20"
    nettsted.nytt_bygg()
    assert nettsted._fordeling_status()["lest"] == "2026-11-23"


def test_proveniens_baerer_kilde_snapshot_og_hentet():
    p = nettsted.proveniens("2026-08-31", "2026-08-31T04:09:31+00:00",
                            kilde="akvakultur")
    assert (p.kilde, p.gjelder, p.hentet) == (
        "akvakultur", "2026-08-31", "2026-08-31T04:09:31+00:00")
    assert str(p) == "Data hentet 31. august 2026 kl. 04.09 UTC (uke 36)."


# ------------------------------------------------------- bunnlinja

@pytest.mark.parametrize("observert,hentet,ventet", [
    # Heines eksempel, 23.11.2026.
    ("2026-11-16", "2026-11-16T13:26:41+00:00",
     "Data hentet 16. november 2026 kl. 13.26 UTC (uke 47)."),
    # Uka i et annet ISO-år enn hentedatoen: året står.
    ("2026-12-28", "2027-01-02T10:00:00+00:00",
     "Data hentet 2. januar 2027 kl. 10.00 UTC (uke 53, 2026)."),
    ("2025-12-29", "2025-12-30T01:00:00+00:00",
     "Data hentet 30. desember 2025 kl. 01.00 UTC (uke 1, 2026)."),
    # Uten hentetidspunkt sier linja ingenting om det, som før.
    ("2026-11-16", "", "Data fra uke 47, 2026."),
])
def test_bunnlinja_har_uka_i_parentes(observert, hentet, ventet):
    assert str(nettsted.proveniens(observert, hentet)) == ventet


def test_bunnlinja_har_ingen_annen_form_i_malene():
    """«, uke N, ÅÅÅÅ.» etter et tidspunkt skal ikke stå skrevet for hånd
    noe sted: linja kommer bare fra `proveniens()`."""
    maler = Path(nettsted.__file__).parent / "maler"
    for mal in maler.glob("*.j2"):
        assert not re.search(r"UTC, uke", mal.read_text(encoding="utf-8")), mal.name


# --------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").is_file() or not (NETTSTED / "kommune").is_dir(),
    reason="HAVBRUK_NETTSTED peker ikke på et fullt bygget nettsted")


def _sider():
    return [p for p in NETTSTED.rglob("*.html") if "pagefind" not in p.parts]


@trenger_bygg
def test_to_sider_i_samme_bygg_oppgir_ikke_ulik_dato_for_samme_ting():
    """Tre slags datoer, hver med én verdi i hele bygget:

      bygget        «Oppdatert» i bunnteksten, kvalitet.json og sitemapen
      sist lest     `<time data-lest="<kilde>">`, per kilde
      hentet        bunnlinjas hentetidspunkt, per (kilde, snapshot)

    Ulike snapshots av samme kilde kan ha ulikt hentetidspunkt:
    /kommune/ viser nøkkelen av 2026-08-31, forsiden registeret av i dag.
    """
    bygget, lest, hentet = set(), defaultdict(set), defaultdict(set)
    uten_oppdatert, merket = [], 0
    for fil in _sider():
        side = fil.read_text(encoding="utf-8")
        rel = fil.relative_to(NETTSTED).as_posix()
        if "<footer" in side:
            m = re.search(r"Oppdatert <time datetime=\"([\d-]+)\">", side)
            if m:
                bygget.add(m.group(1))
            else:
                uten_oppdatert.append(rel)
        for dato, kilde in re.findall(
                r'<time datetime="([\d-]+)" data-lest="([^"]+)"', side):
            lest[kilde].add(dato)
        p = re.search(r'data-proveniens-kilde="([^"]*)" data-proveniens-gjelder="([^"]*)" '
                      r'data-proveniens-hentet="([^"]*)"', side)
        if p:
            merket += 1
            hentet[(p.group(1), p.group(2))].add(p.group(3))
    kvalitet = json.loads((NETTSTED / "kvalitet.json").read_text(encoding="utf-8"))
    bygget.add(kvalitet["bygget"])
    sitemap = (NETTSTED / "sitemap.xml").read_text(encoding="utf-8")
    bygget |= set(re.findall(r"<lastmod>([\d-]+)</lastmod>", sitemap))

    assert not uten_oppdatert, uten_oppdatert[:5]
    assert len(bygget) == 1, f"byggedatoen: {sorted(bygget)}"
    assert all(len(v) == 1 for v in lest.values()), dict(lest)
    assert "havbruksfondet" in lest, "fant ikke «sist lest» på /kommune/"
    ulike = {k: sorted(v) for k, v in hentet.items() if len(v) > 1}
    assert not ulike, f"samme snapshot, ulikt hentetidspunkt: {ulike}"
    assert merket > 1000, f"bare {merket} sider oppgir kilde for bunnlinja"


@trenger_bygg
def test_kommunesiden_sier_hva_sist_lest_er():
    side = (NETTSTED / "kommune" / "index.html").read_text(encoding="utf-8")
    flat = " ".join(re.sub(r"<[^>]+>", "", side).split())
    oppdatert = re.search(r"Oppdatert <time datetime=\"([\d-]+)\">", side).group(1)
    vist = dt.date.fromisoformat(oppdatert).strftime("%d.%m.%Y")
    assert re.search(rf"Fiskeridirektoratets side sist lest \d\d\.\d\d\.\d{{4}}, "
                     rf"før siden ble oppdatert {vist}\.", flat), flat[:300]
