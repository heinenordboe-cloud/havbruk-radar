"""Fasiten: de forseglede anslagene på nettstedet.

Anslagene for havbruksfondet ligger under /fasiten/ som kopier av filene
som ble forseglet, med stempelet ved siden av, og en side som forklarer
dem. Prøvene her holder tre ting:

  1. Kopien er fila som ble forseglet. Summene under er skrevet av fra
     forseglingen (12.10.2026 og 09.11.2026), ikke lest av koden, så en
     endring i `havbruksfond.FORSEGLINGER` også må endres her.
  2. Bygget og porten stopper en kopi som ikke er det. Hver av dem prøves
     med en feil laget med vilje.
  3. Siden sier det filene sier.

De siste prøvene trenger et bygget nettsted (`HAVBRUK_NETTSTED`) og
kjøres i porten, som de andre nettstedsprøvene.
"""
import hashlib
import os
import shutil
from pathlib import Path

import pytest

import havbruksfond as h
import nettsted
import publiseringsvakt as v

# SUMMENE SOM BLE FORSEGLET. Den første står i .ots-fila fra 12.10.2026,
# den andre i den fra 09.11.2026.
SEGL = {
    "2026-10-12": "de9ba03432837c0cfc2fd0b2b145bfdad2e7ebcf47dea4a6addb626e38387002",
    "2026-11-09": "ccb451bdde451430d48c7a3f62ec037d98a0c91b2ae4b631cd2165bbc69701a0",
}

# FØRSTE BITCOIN-BLOKK SOM BEKREFTER HVERT STEMPEL. MÅLT 16.11.2026 med
# `fasit_havbruksfond.bitcoin()`: merkleroten stempelet regner seg fram
# til, er den blockstream.info og mempool.space oppgir for blokka. 971138
# er fra 12.10.2026 kl. 20.36 UTC, 975211 fra 09.11.2026 kl. 19.42 UTC.
# opentimestamps.org viste de samme to 10.11.2026.
BLOKK = {"2026-10-12": 971138, "2026-11-09": 975211}

MAPPE = "fasiten/havbruksfondet-2026"
NAVN = {dato: f"havbruksfondet-2026-forseglet-{dato}.md" for dato in SEGL}


# --------------------------------------------------- navnene og summene


def test_kopiene_heter_etter_forseglingsdatoen():
    """Fila og stempelet per forsegling, med datoen i navnet. Stempelet
    heter som fila med `.ots` bak: slik finner `ots verify` fila det
    gjelder. «Pakke» er vårt ord og står ikke i navnet."""
    kopier = h.forseglede_kopier()
    assert [k["sti"] for k in kopier] == [
        f"{MAPPE}/{NAVN['2026-10-12']}", f"{MAPPE}/{NAVN['2026-10-12']}.ots",
        f"{MAPPE}/{NAVN['2026-11-09']}", f"{MAPPE}/{NAVN['2026-11-09']}.ots"]
    assert [k["ots"] for k in kopier] == [False, True, False, True]
    assert not [k["sti"] for k in kopier if "pakke" in k["sti"]]
    assert h.FASITMAPPE == MAPPE


def test_filene_i_repoet_er_de_som_ble_forseglet():
    """Summen av hver fil, og summen hvert stempel er stemplet for."""
    for k in h.forseglede_kopier():
        assert k["sha256"] == SEGL[k["forseglet"]], k["sti"]
        data = k["kilde"].read_bytes()
        sum_ = h.ots_sum(data) if k["ots"] else hashlib.sha256(data).hexdigest()
        assert sum_ == SEGL[k["forseglet"]], k["kilde"]


# ------------------------------------------- blokkene, lest av stempelet


def _stempel(*grener: bytes) -> bytes:
    """Et OpenTimestamps-stempel for en sum av bare nuller, med grenene
    gitt. Alle uten den siste får 0xff foran, som i formatet."""
    tre = b"".join(b"\xff" + g for g in grener[:-1]) + grener[-1]
    return h._OTS_HODE + b"\x01\x08" + bytes(32) + tre


def _varuint(n: int) -> bytes:
    ut = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        ut.append(b | (0x80 if n else 0))
        if not n:
            return bytes(ut)


def _bitcoin(hoyde: int) -> bytes:
    innhold = _varuint(hoyde)
    return b"\x00" + h._OTS_BITCOIN + _varuint(len(innhold)) + innhold


def _venter(adresse: bytes = b"https://kalender.example") -> bytes:
    innhold = _varuint(len(adresse)) + adresse
    return (b"\x00" + bytes.fromhex("83dfe30d2ef90c8e")
            + _varuint(len(innhold)) + innhold)


def test_blokkene_i_de_to_stemplene():
    """Den laveste blokka i hvert stempel er den som ble målt."""
    for k in h.forseglede_kopier():
        if k["ots"]:
            blokker = h.ots_blokker(k["kilde"].read_bytes(), k["kilde"].name)
            assert blokker and blokker == sorted(blokker), k["kilde"]
            assert blokker[0] == BLOKK[k["forseglet"]], (k["kilde"], blokker)


def test_blokkleseren_paa_konstruerte_stempler():
    """Formatet, uten de ekte filene: en gren per kalender, operasjoner
    med og uten argument foran attestasjonen, og høyder over 127 (to byte
    i tallet). Et stempel som bare venter, har ingen blokk."""
    assert h.ots_blokker(_stempel(_venter())) == []
    assert h.ots_blokker(_stempel(_bitcoin(975211))) == [975211]
    legg_til = b"\xf0" + _varuint(4) + b"\xde\xad\xbe\xef"
    foran = b"\xf1" + _varuint(200) + bytes(200)
    assert h.ots_blokker(_stempel(
        legg_til + b"\x08" + _bitcoin(971140),
        _venter(),
        foran + b"\x08\x08" + b"\xff" + _bitcoin(971138) + _venter(),
    )) == [971138, 971140]


def test_blokkleseren_kaster_paa_det_som_ikke_er_et_stempel():
    """Avkortet, med noe bak, med en ukjent operasjon, eller en annen fil.
    Et stempel leseren ikke forstår, skal ikke gi «ingen blokk»."""
    hel = _stempel(b"\x08" + _bitcoin(971138))
    assert h.ots_blokker(hel) == [971138]
    for odelagt in (hel[:-1], hel[:-3], hel + b"\x00",
                    _stempel(b"\x55" + _bitcoin(1)), b"ikke et stempel"):
        with pytest.raises(ValueError):
            h.ots_blokker(odelagt)
    ekte = next(k["kilde"] for k in h.forseglede_kopier() if k["ots"]).read_bytes()
    for kutt in (len(ekte) - 1, len(ekte) // 2, 80):
        with pytest.raises(ValueError):
            h.ots_blokker(ekte[:kutt])


# --------------------------------------------- bygget skriver kopiene


def test_bygget_skriver_kopiene_byte_for_byte(tmp_path):
    skrevet = nettsted.skriv_forseglede(tmp_path)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in skrevet) == sorted(
        k["sti"] for k in h.forseglede_kopier())
    for k in h.forseglede_kopier():
        kopi = (tmp_path / k["sti"]).read_bytes()
        assert kopi == k["kilde"].read_bytes(), k["sti"]
        if not k["ots"]:
            assert hashlib.sha256(kopi).hexdigest() == SEGL[k["forseglet"]]


@pytest.fixture
def falskt_repo(tmp_path, monkeypatch):
    """En kopi av predictions/ som kan ødelegges, og `forseglede_kopier()`
    pekt dit. Filene i repoet røres ikke."""
    rot = tmp_path / "repo"
    (rot / "predictions").mkdir(parents=True)
    for k in h.forseglede_kopier():
        shutil.copy2(k["kilde"], rot / "predictions" / k["kilde"].name)
    ekte = h.forseglede_kopier
    monkeypatch.setattr(h, "forseglede_kopier", lambda r=rot: ekte(r))
    return rot


def test_en_endret_fil_stopper_bygget_og_ingenting_skrives(tmp_path, falskt_repo):
    """Én byte til i fila, og den er ikke den forseglede. Bygget kaster
    før noen kopi er skrevet, også de tre som er riktige."""
    fil = falskt_repo / "predictions" / "havbruksfond-2026.md"
    fil.write_bytes(fil.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="ikke fila som ble forseglet 2026-10-12"):
        nettsted.skriv_forseglede(tmp_path / "ut")
    assert not (tmp_path / "ut").exists()


def test_et_stempel_for_en_annen_fil_stopper_bygget(tmp_path, falskt_repo):
    p = falskt_repo / "predictions"
    shutil.copy2(p / "havbruksfond-2026.md.ots", p / "havbruksfond-2026-pakke2.md.ots")
    with pytest.raises(ValueError, match="ikke fila som ble forseglet 2026-11-09"):
        nettsted.skriv_forseglede(tmp_path / "ut")
    assert not (tmp_path / "ut").exists()


# ------------------------------------------------- porten holder seglet


@pytest.fixture
def bygg(tmp_path):
    ut = tmp_path / "bygg"
    nettsted.skriv_forseglede(ut)
    return ut


def test_porten_gjor_rede_for_de_fire_kopiene(bygg):
    funn, ok = v.forseglingsfunn(bygg)
    assert funn == []
    assert ok == {k["sti"] for k in h.forseglede_kopier()}


def test_porten_feller_en_fil_med_en_annen_sum(bygg):
    """Én byte er nok, og fila er da ikke lenger gjort rede for: den leses
    som tekst, som alt annet."""
    sti = f"{MAPPE}/{NAVN['2026-11-09']}"
    (bygg / sti).write_bytes((bygg / sti).read_bytes().replace(b"35", b"36", 1))
    funn, ok = v.forseglingsfunn(bygg)
    assert [(f.fil, f.slag) for f in funn] == [(sti, "forsegling")]
    assert "ikke summen som ble forseglet 2026-11-09" in funn[0].utdrag
    assert sti not in ok and len(ok) == 3


def test_porten_feller_et_stempel_som_avviker_fra_repoet(bygg):
    """Også når det er et gyldig stempel for samme fil: kopien skal være
    den i repoet, byte for byte."""
    sti = f"{MAPPE}/{NAVN['2026-10-12']}.ots"
    (bygg / sti).write_bytes((bygg / sti).read_bytes() + b"\x00")
    funn, ok = v.forseglingsfunn(bygg)
    assert [(f.fil, f.slag) for f in funn] == [(sti, "forsegling")]
    assert "avviker fra havbruksfond-2026.md.ots i kodrepoet" in funn[0].utdrag
    assert sti not in ok


def test_porten_feller_et_stempel_for_en_annen_fil(bygg, tmp_path):
    """Stempelet i repoet er byttet med det andre: kopien er lik repoet,
    men stemplet for en annen sum."""
    rot = tmp_path / "repo"
    (rot / "predictions").mkdir(parents=True)
    for k in h.forseglede_kopier():
        shutil.copy2(k["kilde"], rot / "predictions" / k["kilde"].name)
    andre = (rot / "predictions" / "havbruksfond-2026-pakke2.md.ots").read_bytes()
    (rot / "predictions" / "havbruksfond-2026.md.ots").write_bytes(andre)
    sti = f"{MAPPE}/{NAVN['2026-10-12']}.ots"
    (bygg / sti).write_bytes(andre)
    funn, ok = v.forseglingsfunn(bygg, rot)
    assert [(f.fil, f.slag) for f in funn] == [(sti, "forsegling")]
    assert "gjelder ikke fila som ble forseglet 2026-10-12" in funn[0].utdrag


def test_porten_krever_filene_naar_siden_er_bygget(bygg):
    """Siden lenker til fila og stempelet. Uten siden er en manglende fil
    ikke et funn: et bygg uten /fasiten/ har ingenting å love."""
    sti = f"{MAPPE}/{NAVN['2026-10-12']}.ots"
    (bygg / sti).unlink()
    assert v.forseglingsfunn(bygg)[0] == []
    (bygg / MAPPE / "index.html").write_text("<html></html>", encoding="utf-8")
    funn, ok = v.forseglingsfunn(bygg)
    assert [(f.fil, f.slag) for f in funn] == [(sti, "forsegling")]
    assert "mangler" in funn[0].utdrag and len(ok) == 3


def test_hele_porten_leser_ikke_kopien_som_tekst_men_en_endret_fil(bygg):
    """`gransk()` med kopiene: ingen funn under /fasiten/. De forseglede
    filene nevner repo-stier og har et rått tidsstempel, og leses de som
    tekst, stopper porten på det (MÅLT 16.11.2026). Endres én byte, er
    fila ikke lenger gjort rede for: seglet er brutt, og teksten leses."""
    def under_fasiten():
        return sorted({f.slag for f in v.gransk(bygg) if f.fil.startswith("fasiten")})
    assert under_fasiten() == []
    sti = bygg / MAPPE / NAVN["2026-11-09"]
    sti.write_bytes(sti.read_bytes() + b"\n")
    assert under_fasiten() == ["forsegling", "raatt_tidsstempel", "reposti"]


def test_hele_porten_feller_et_ukjent_stempel(bygg):
    """En .ots som ikke er en av kopiene, er en binærfil ingen har sett i."""
    (bygg / MAPPE / "annet.md.ots").write_bytes(b"\x00OpenTimestamps")
    funn = [f for f in v.gransk(bygg) if f.fil.startswith("fasiten")]
    assert [(f.fil, f.slag) for f in funn] == [(f"{MAPPE}/annet.md.ots", "ugranska")]


# ----------------------------------------- Content-Type for stemplene


def test_stemplene_treffes_av_noeyaktig_en_content_type(bygg):
    """`.ots` er også OpenDocuments regnearkmal, og verten skal ikke gjette.
    Uten regelen feller porten bygget."""
    hoder = nettsted.skriv_vertsfiler(bygg)
    assert v.innholdstypefunn(bygg) == []
    regler = dict(v._hoderegler(hoder.read_text(encoding="utf-8")))
    assert regler["/fasiten/*.ots"] == {"content-type": "application/octet-stream"}
    # Fila ved siden av har ingen regel: Cloudflare svarer text/markdown
    # med tegnsett selv (MÅLT 16.11.2026).
    assert not [m for m in regler if m.endswith(".md")]

    uten = hoder.read_text(encoding="utf-8").replace(
        "/fasiten/*.ots\n  Content-Type: application/octet-stream\n", "")
    assert uten != hoder.read_text(encoding="utf-8")
    hoder.write_text(uten, encoding="utf-8")
    assert sorted(f.fil for f in v.innholdstypefunn(bygg)) == [
        f"{MAPPE}/{NAVN['2026-10-12']}.ots", f"{MAPPE}/{NAVN['2026-11-09']}.ots"]


# ------------------------------------------------- mot portens bygg

NETTSTED = Path(os.environ.get("HAVBRUK_NETTSTED", "") or "/finnes-ikke")
trenger_bygg = pytest.mark.skipif(
    not (NETTSTED / "index.html").exists(),
    reason="HAVBRUK_NETTSTED peker ikke på et bygget nettsted")


@trenger_bygg
def test_portens_bygg_har_de_forseglede_filene():
    """sha256 målt fra bygget, mot forseglingen; stempelet mot repoet."""
    for k in h.forseglede_kopier():
        kopi = (NETTSTED / k["sti"]).read_bytes()
        if k["ots"]:
            assert kopi == k["kilde"].read_bytes(), k["sti"]
            assert h.ots_sum(kopi) == SEGL[k["forseglet"]], k["sti"]
            assert h.ots_blokker(kopi)[0] == BLOKK[k["forseglet"]], k["sti"]
        else:
            assert hashlib.sha256(kopi).hexdigest() == SEGL[k["forseglet"]], k["sti"]
    assert v.forseglingsfunn(NETTSTED) == ([], {k["sti"] for k in h.forseglede_kopier()})
    andre = sorted(p.relative_to(NETTSTED).as_posix() for p in NETTSTED.rglob("*.ots"))
    assert andre == sorted(k["sti"] for k in h.forseglede_kopier() if k["ots"])
