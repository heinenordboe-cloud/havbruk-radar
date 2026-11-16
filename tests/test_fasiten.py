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


# ------------------------------------------------------------ siden
#
# /fasiten/havbruksfondet-2026/ og /fasiten/. Siden trenger ikke
# datarepoet: alt den viser, står i de forseglede filene, og uten arkivet
# er fordelingen «ikke publisert».

import html
import re

SIDE = f"{MAPPE}/index.html"


def _tekst(markup: str) -> str:
    """Teksten slik avsnittsvakten leser den, med vanlig mellomrom der
    siden har et hardt (mellom tall og enhet)."""
    uten = html.unescape(re.sub(r"<[^>]+>", "", markup))
    return " ".join(uten.split())            # split() tar også det harde mellomrommet


def _main(side: str) -> str:
    return re.search(r"<main\b.*?</main>", side, re.S).group(0)


@pytest.fixture(scope="module")
def fasitsider(tmp_path_factory):
    ut = tmp_path_factory.mktemp("fasiten")
    assert nettsted.skriv_fasiten(ut) == ["/fasiten/", f"/{MAPPE}/"]
    return ut


# TEKSTEN HEINE GODKJENTE 16.11.2026, i den rekkefølgen den står på siden.
# Hver linje skal stå ordrett. Ingressens første setning og «Feil hvis»
# står i flere avsnitt på siden (110-grensa); her er de én linje, for det
# er ordene som er godkjent.
TEKSTEN = [
    "Havbruksfondet 2026: anslagene våre, forseglet før fordelingen",
    "Vi regnet ut fordelingen fra Akvakulturregisteret og forseglet anslagene "
    "før Fiskeridirektoratet publiserte den. Når fordelingen kommer, står "
    "fasiten her, også der vi bommer.",
    "Fordelingen for 2026 er ikke publisert ennå. Andelen sier hvor stor del av "
    "utbetalingen hver kommune får, ikke hvor mye. Beløpet avhenger av hva "
    "staten har fått inn, og det anslår vi ikke.",
    "Forseglet 12.10.2026 · Bitcoin-blokk 971138",
    "Andelen for hver av de 143 kommunene og 8 fylkeskommunene, regnet ut fra "
    "registeret 31.08 og 07.09.2026.",
    "Påstanden: Alle ligger innenfor 0,05 prosentpoeng av Fiskeridirektoratets andel.",
    "Feil hvis: én kommune eller fylkeskommune bommer med mer, kommunene ikke er "
    "de samme 143, eller noen kommune får en ekstra del for ny kapasitet.",
    "Konfidens 75 % · Venter på fordelingen",
    f"Fingeravtrykk (sha256): {SEGL['2026-10-12']} Anslaget Stempelet",
    "Forseglet 09.11.2026 · Bitcoin-blokk 975211",
    "Ni skarpere påstander, som hver kan avgjøres for seg.",
    "Nr. Påstanden Konfidens Status",
    "1 De 89 kommunene der ingenting er endret siden 2025, har samme MTB som i "
    "2025, ±1 tonn 90 % Venter på fordelingen",
    "2 De 26 kommunene med nye, borte eller endrede lokaliteter har den MTB-en "
    "vi har regnet ut, ±1 tonn 80 % Venter på fordelingen",
    "3 Havbruksstasjonen i Tromsøs to lokaliteter (650 t og 975 t) er med, som i "
    "2024 og 2025 75 % Venter på fordelingen",
    "4 HØGÅS i Strand (780 t) er med igjen 85 % Venter på fordelingen",
    "5 De ni lokalitetene som bare har tillatelse for andre arter enn laks, "
    "ørret og regnbueørret, er ikke med 90 % Venter på fordelingen",
    "6 De ti lokalitetene som deles mellom to kommuner, deles som i 2025 "
    "(innenfor 0,001), og Persflua deles ikke 70 % Venter på fordelingen",
    "7 Alle 8 fylkeskommuner ligger innenfor 0,005 prosentpoeng av vår andel "
    "55 % Venter på fordelingen",
    "8 Alle 143 kommuner ligger innenfor 0,005 prosentpoeng, ti ganger smalere "
    "enn 12.10 35 % Venter på fordelingen",
    "9 Fylkeskommunene får 20 % av utbetalingen, ±0,001 prosentpoeng 95 % "
    "Venter på fordelingen",
    "Konfidensen er hvor sikre vi var da vi forseglet. En påstand på 35 % skal "
    "bomme oftere enn den treffer.",
    "Ved uenighet gjelder den forseglede fila.",
    f"Fingeravtrykk (sha256): {SEGL['2026-11-09']} Påstandene Stempelet",
    "Slik sjekker du oss",
    "Last ned anslaget og stempelet (lenkene over).",
    "Slipp begge på opentimestamps.org. Den viser datoen fila ble forseglet, "
    "bekreftet i Bitcoin.",
    "I terminalen: ots verify.",
]


def _mangler(tekst: str, linjer: list[str]) -> list[str]:
    """Linjene som ikke står i `tekst`, i rekkefølge etter den forrige."""
    pos, ute = 0, []
    for linje in linjer:
        her = tekst.find(linje, pos)
        if her < 0:
            ute.append(linje)
        else:
            pos = her + len(linje)
    return ute


def test_siden_har_teksten_ordrett(fasitsider):
    tekst = _tekst(_main((fasitsider / SIDE).read_text("utf-8")))
    assert _mangler(tekst, TEKSTEN) == []
    # Og prøven ser en endring: ett ord byttet, og linja mangler.
    assert _mangler(tekst.replace("også der vi bommer", "også der vi treffer"),
                    TEKSTEN) == [TEKSTEN[1]]


def test_tallene_i_paastandene_er_de_forseglede_filenes():
    """Hvert tall i teksten, hentet ut av filene og satt inn i setningen
    det står i. Er et tall i TEKSTEN et annet enn filas, feiler linja."""
    a, p1, p2 = h.anslaget(), h.paastand1(), h.pakke2()
    ps = p2["paastander"]
    ord_ = {9: "ni", 10: "ti"}

    def tall(monster: str, tekst: str) -> str:
        m = re.search(monster, tekst)
        assert m, (monster, tekst)
        return m.group(1)

    lok = {pid: [x for x in p2["lokaliteter"] if x["paastand"] == pid]
           for pid in ("P2-3", "P2-4", "P2-5", "P2-6")}
    delte = [x for x in lok["P2-6"] if x["deling"]]
    udelt = [x for x in lok["P2-6"] if not x["deling"]]
    assert [x["forventet"] for x in udelt] == ["ikke delt"]
    assert {x["forventet"] for x in lok["P2-3"] + lok["P2-4"]} == {"med"}
    assert {x["forventet"] for x in lok["P2-5"]} == {"ute"}
    assert all(len(x["kommuner"]) == 2 for x in delte)
    hogas = lok["P2-4"][0]
    strand = p2["kommuner"][hogas["kommuner"][0]]["navn"].capitalize()
    margin1 = tall(r"A2-andel − (0,\d+) prosentpoeng", p1["verdi_min"])
    margin8 = tall(r"− (0,\d+) prosentpoeng", ps[7]["verdi_min"])
    assert float(margin1.replace(",", ".")) / float(margin8.replace(",", ".")) == 10
    aar = h.FORRIGE_AAR
    ventet = [
        f"Andelen for hver av de {len(a['kommuner'])} kommunene og {len(a['fylker'])} "
        f"fylkeskommunene, regnet ut fra registeret {h.FOR[8:]}.{h.FOR[5:7]} og "
        f"{h.ETTER[8:]}.{h.ETTER[5:7]}.{h.ETTER[:4]}.",
        f"Påstanden: Alle ligger innenfor {margin1} prosentpoeng av "
        f"Fiskeridirektoratets andel.",
        f"kommunene ikke er de samme {len(a['kommuner'])},",
        f"Konfidens {p1['konfidens']} % ·",
        f"De {len(p2['grupper']['U'])} kommunene der ingenting er endret siden {aar}, "
        f"har samme MTB som i {aar}, ±{tall(r'− (\d+) t,', ps[0]['verdi_min'])} tonn "
        f"{ps[0]['konfidens']} %",
        f"De {len(p2['grupper']['E'])} kommunene med nye, borte eller endrede "
        f"lokaliteter har den MTB-en vi har regnet ut, "
        f"±{tall(r'− (\d+) t,', ps[1]['verdi_min'])} tonn {ps[1]['konfidens']} %",
        f"Havbruksstasjonen i Tromsøs to lokaliteter ({lok['P2-3'][0]['mtb']:.0f} t og "
        f"{lok['P2-3'][1]['mtb']:.0f} t) er med, som i {aar - 1} og {aar} "
        f"{ps[2]['konfidens']} %",
        f"{hogas['navn']} i {strand} ({hogas['mtb']:.0f} t) er med igjen "
        f"{ps[3]['konfidens']} %",
        f"De {ord_[len(lok['P2-5'])]} lokalitetene som bare har tillatelse for andre "
        f"arter enn laks, ørret og regnbueørret, er ikke med {ps[4]['konfidens']} %",
        f"De {ord_[len(delte)]} lokalitetene som deles mellom to kommuner, deles som i "
        f"{aar} (innenfor {tall(r'± (0,\d+);', ps[5]['verdi_min'])}), og "
        f"{udelt[0]['navn'].capitalize()} deles ikke {ps[5]['konfidens']} %",
        f"Alle {len(p2['fylker'])} fylkeskommuner ligger innenfor "
        f"{tall(r'− (0,\d+) prosentpoeng', ps[6]['verdi_min'])} prosentpoeng av vår "
        f"andel {ps[6]['konfidens']} %",
        f"Alle {len(p2['kommuner'])} kommuner ligger innenfor {margin8} prosentpoeng, "
        f"ti ganger smalere enn 12.10 {ps[7]['konfidens']} %",
        f"Fylkeskommunene får {tall(r'^(\d+ %) −', ps[8]['verdi_min'])} av "
        f"utbetalingen, ±{tall(r'− (0,\d+) prosentpoeng', ps[8]['verdi_min'])} "
        f"prosentpoeng {ps[8]['konfidens']} %",
        f"En påstand på {min(p['konfidens'] for p in ps)} % skal bomme oftere enn "
        f"den treffer.",
    ]
    godkjent = " ".join(TEKSTEN)
    assert [linje for linje in ventet if linje not in godkjent] == []
    assert len(ps) == 9 and "Ni skarpere påstander" in godkjent
    # Tromsø-lokalitetene sto på listene begge årene påstanden nevner, og
    # den første forseglingen er den påstand 8 måler seg mot.
    assert "både per 01.09.2024 og per 01.09.2025" in " ".join(ps[2]["grunnlag"].split())
    assert h.FORSEGLINGER[0]["forseglet"][5:] == "10-12"


def test_porten_har_ingenting_aa_innvende_mot_sidene(fasitsider):
    """Avsnitt over 110 tegn, repo-stier, rå tidsstempler og JSON-LD."""
    for rel in ("fasiten/index.html", SIDE):
        side = (fasitsider / rel).read_text("utf-8")
        assert v.tekstfunn(rel, ".html", side, set(), set()) == [], rel
    assert v.jsonldfunn(fasitsider) == []
    assert v.forseglingsfunn(fasitsider)[0] == []


def test_ingen_lenke_til_kodrepoet_og_ingen_interne_ord(fasitsider):
    """En leser skal ikke måtte til kodrepoet. Hver lenke i innholdet går
    til nettstedet selv, til en fil ved siden av, eller til
    opentimestamps.org. «Pakke 1» og «pakke 2» er våre ord."""
    for rel in ("fasiten/index.html", SIDE):
        main = _main((fasitsider / rel).read_text("utf-8"))
        assert "github.com" not in main, rel
        lenker = re.findall(r'href="([^"]+)"', main)
        fremmede = [l for l in lenker if "://" in l and l != "https://opentimestamps.org/"]
        assert lenker and fremmede == [], (rel, fremmede)
        assert not re.findall(r"(?i)\bpakke\s*\d|sources/|FINNES IKKE", _tekst(main)), rel


def test_lenkene_gaar_til_fila_og_stempelet_ved_siden_av(fasitsider):
    """«Anslaget», «Påstandene» og «Stempelet» er nedlastinger av kopiene i
    samme mappe, og kopiene er de forseglede."""
    main = _main((fasitsider / SIDE).read_text("utf-8"))
    lenker = re.findall(r'<a class="handling" href="([^"]+)" download>([^<]+)</a>', main)
    assert lenker == [
        (NAVN["2026-10-12"], "Anslaget"), (NAVN["2026-10-12"] + ".ots", "Stempelet"),
        (NAVN["2026-11-09"], "Påstandene"), (NAVN["2026-11-09"] + ".ots", "Stempelet")]
    for (navn, _), dato in zip(lenker, ("2026-10-12", "2026-10-12", "2026-11-09", "2026-11-09")):
        data = (fasitsider / MAPPE / navn).read_bytes()
        sum_ = h.ots_sum(data) if navn.endswith(".ots") else hashlib.sha256(data).hexdigest()
        assert sum_ == SEGL[dato], navn
    # Hver forsegling har et anker andre sider kan lenke til.
    for dato in SEGL:
        assert f'id="forseglet-{dato}"' in main


def test_oversikten_lister_siden(fasitsider):
    main = _main((fasitsider / "fasiten" / "index.html").read_text("utf-8"))
    assert f'<a href="/{MAPPE}/">Havbruksfondet 2026</a>' in main
    assert _mangler(_tekst(main), [
        "Fasiten", "Anslag vi har forseglet før svaret var kjent, og hvordan det gikk.",
        "Havbruksfondet 2026 12.10.2026 og 09.11.2026 Venter på fordelingen"]) == []


def _fasit(utfall1: str, utfall2: list[str]) -> dict:
    """Det siden leser av en fasit: utfallet per påstand og hvor tabellen
    kom fra. Resten av fasitfila står i tests/test_fasit_havbruksfond.py."""
    return {"aar": 2026,
            "tabell": {"form": "regneark", "sha256": "ab" * 32,
                       "url": "https://www.fiskeridir.no/akvakultur/havbruksfondet",
                       "hentet": "2026-11-20T08:00:00+00:00"},
            "sider": {"kommuner": {}, "fylker": {}},
            "pakke1": {"id": "2026-10-12-1", "utfall": utfall1},
            "pakke2": [{"id": f"2026-11-09-{n}", "utfall": u}
                       for n, u in enumerate(utfall2, 1)]}


def _statuser(side: str) -> list[str]:
    """Statusen per påstand: den første forseglingens ene, så de ni.
    Cellene får `data-label` ved bygging, så attributtene leses fritt."""
    return [_tekst(m.group(2)) for m in re.finditer(
        r'<(td|span)\b[^>]*\bdata-felt="utfall"[^>]*>(.*?)</\1>', _main(side), re.S)]


def test_utfallet_staar_per_paastand_naar_fasiten_er_kvittert(tmp_path):
    """På fasitdagen: «Traff», «Bom» eller «Venter på regnearket» der det
    sto «Venter på fordelingen», påstand for påstand, også der vi bommet.
    Første setning sier at fordelingen er publisert, med kilden."""
    uten = tmp_path / "uten"
    nettsted.skriv_fasiten(uten)
    assert _statuser((uten / SIDE).read_text("utf-8")) == ["Venter på fordelingen"] * 10

    f = _fasit("bom", ["traff", "traff", "bom", "traff", "traff", "venter",
                       "bom", "bom", "traff"])
    med = tmp_path / "med"
    nettsted.skriv_fasiten(med, fasit=f)
    side = (med / SIDE).read_text("utf-8")
    assert _statuser(side) == ["Bom", "Traff", "Traff", "Bom", "Traff", "Traff",
                               "Venter på regnearket", "Bom", "Bom", "Traff"]
    tekst = _tekst(_main(side))
    assert "Fiskeridirektoratet har publisert fordelingen for 2026." in tekst
    assert "ikke publisert ennå" not in tekst and "Venter på fordelingen" not in tekst
    assert "Fiskeridir. · regnearket · hentet 20.11.2026" in tekst
    # Det som ikke er fasiten, står som før.
    assert _mangler(tekst, [l for l in TEKSTEN if "Venter på" not in l
                            and "ikke publisert" not in l]) == []
    oversikt = _tekst(_main((med / "fasiten" / "index.html").read_text("utf-8")))
    assert "5 treff og 4 bom av 10 påstander, 1 ikke avgjort" in oversikt
    assert v.tekstfunn(SIDE, ".html", side, set(), set()) == []


def test_arkivert_men_ikke_kvittert_er_ikke_avgjort(tmp_path, monkeypatch):
    """Regnearket er arkivert, fasiten er ikke lest ennå. Da venter ikke
    påstandene på fordelingen, og siden sier ikke at de gjør det."""
    monkeypatch.setattr(nettsted, "_fordeling_status",
                        lambda: {"publisert": True, "lest": "2026-11-20"})
    nettsted.skriv_fasiten(tmp_path)
    side = (tmp_path / SIDE).read_text("utf-8")
    assert _statuser(side) == ["Ikke avgjort ennå"] * 10
    assert "Fiskeridirektoratet har publisert fordelingen for 2026." in _tekst(_main(side))


def test_en_paastand_fasiten_ikke_har_er_ikke_avgjort(tmp_path):
    """En fasit uten utfall for en påstand gir ikke «Venter på
    fordelingen» om en fordeling som er kommet."""
    nettsted.skriv_fasiten(tmp_path, fasit=_fasit("traff", ["traff"] * 3))
    assert _statuser((tmp_path / SIDE).read_text("utf-8")) == (
        ["Traff"] * 4 + ["Ikke avgjort ennå"] * 6)


@trenger_bygg
def test_portens_bygg_har_sidene_i_sitemapen_og_llms():
    assert _mangler(_tekst(_main((NETTSTED / SIDE).read_text("utf-8"))),
                    [l for l in TEKSTEN if "Venter på" not in l
                     and "ikke publisert" not in l]) == []
    sitemap = (NETTSTED / "sitemap.xml").read_text("utf-8")
    assert "/fasiten/</loc>" in sitemap and f"/{MAPPE}/</loc>" in sitemap
    assert "/fasiten/)" in (NETTSTED / "llms.txt").read_text("utf-8")
    for rel in ("fasiten/index.html", SIDE):
        assert "github.com" not in _main((NETTSTED / rel).read_text("utf-8")), rel


def test_tall_og_enhet_holder_sammen_paa_siden(fasitsider):
    """Hardt mellomrom mellom tall og enhet i hver celle, som på
    kommunesidene: «650 t» skal ikke brytes over to linjer i et kort."""
    from tests.test_havbruksfond import _brutte_enheter
    for rel in ("fasiten/index.html", SIDE):
        assert _brutte_enheter((fasitsider / rel).read_text("utf-8")) == [], rel
