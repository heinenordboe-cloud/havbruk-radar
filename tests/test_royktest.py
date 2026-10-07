"""Røyktesten etter publisering — mot en byggemappe og en attrapp-henter.

Prøvene her når ikke nettet. Det som prøves er at forventningene leses
av BYGGET (CSP-en fra `_headers`, uka, hvilke sider som har kart), og at
hver av de fire prøvene faktisk feller det den skal.
"""

from pathlib import Path

import pytest

import nettsted
import royktest

CSP = "default-src 'self'; object-src 'none'"
UKE = "2026-41"
ADRESSE = "kontakt@kystloggen.no"
# Bunnteksten står på hver side, kart eller ikke.
BUNN = f'<p><a href="mailto:{ADRESSE}">{ADRESSE}</a></p>'


def _bygg(rot: Path) -> Path:
    (rot / "endringer" / UKE).mkdir(parents=True)
    (rot / "_headers").write_text(
        f"# kommentar\n\n/*\n  Content-Security-Policy: {CSP}\n"
        f"  X-Content-Type-Options: nosniff\n\n/*.xml\n"
        f"  Content-Security-Policy: noe annet\n", encoding="utf-8")
    kart = f"<footer>{royktest.KARTVERKET}{BUNN}</footer>"
    (rot / "index.html").write_text(
        f'<title>Kystloggen</title><a href="/endringer/{UKE}/">uke</a>{kart}',
        encoding="utf-8")
    (rot / "endringer" / UKE / "index.html").write_text(
        f"<title>Endringer i uke 41, 2026 — Kystloggen</title>{BUNN}",
        encoding="utf-8")
    for nr, med_kart in (("9", True), ("10", False), ("100", True),
                         ("11", True)):
        (rot / "lokalitet" / nr).mkdir(parents=True)
        (rot / "lokalitet" / nr / "index.html").write_text(
            kart if med_kart else f"<p>ingen posisjon</p>{BUNN}",
            encoding="utf-8")
    for nr in ("2", "13"):
        (rot / "produksjonsomrade" / nr).mkdir(parents=True)
        (rot / "produksjonsomrade" / nr / "index.html").write_text(
            kart, encoding="utf-8")
    return rot


def _levende(mappe: Path, csp: str = CSP, overstyr: dict | None = None):
    """En henter som svarer med byggets filer — som et nettsted som er
    akkurat det bygget sier — med enkeltsider overstyrt."""
    overstyr = overstyr or {}

    def henter(url):
        sti = url.split("://", 1)[1].split("/", 1)[1]
        if sti in overstyr:
            return overstyr[sti]
        fil = mappe / sti / "index.html"
        return (200, {"content-security-policy": csp},
                fil.read_text(encoding="utf-8"), url)
    return henter


def test_kartverket_er_den_samme_setningen_som_bygget_skriver():
    assert royktest.KARTVERKET == nettsted.KARTVERKET


def test_csp_leses_fra_alle_siders_blokk(tmp_path):
    assert royktest.csp(_bygg(tmp_path)) == CSP


def test_utvalget_er_fem_sider_fra_bygget(tmp_path):
    sider = royktest.utvalg(_bygg(tmp_path), UKE)
    assert [s.sti for s in sider] == [
        "/", f"/endringer/{UKE}/",
        "/lokalitet/9/", "/lokalitet/100/",     # numerisk, bare med kart
        "/produksjonsomrade/2/"]
    assert sider[1].tittel == "Endringer i uke 41, 2026 — Kystloggen"
    assert sider[0].lenke == f"/endringer/{UKE}/"
    assert [s.kart for s in sider] == [True, False, True, True, True]


def test_uke_bygget_ikke_har_kan_ikke_proves(tmp_path):
    with pytest.raises(ValueError, match="2026-42"):
        royktest.utvalg(_bygg(tmp_path), "2026-42")


def test_et_nettsted_som_er_bygget_er_rent(tmp_path):
    m = _bygg(tmp_path)
    assert royktest.kontakt(m) == ADRESSE
    assert royktest.kjor("https://x.test", royktest.utvalg(m, UKE), CSP,
                         forsok=1, pause=0, henter=_levende(m),
                         adresse=ADRESSE) == []


# Slik Cloudflare skrev om forsiden, MÅLT 07.10.2026.
OBFUSKERT = ('<a href="/cdn-cgi/l/email-protection#6e0501001a0f051a2e05171d'
             '1a020109090b00400001">[email&#160;protected]</a>'
             '<script src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/'
             'email-decode.min.js"></script>')


def test_obfuskert_adresse_er_rod(tmp_path):
    """Heine har slått av Email Address Obfuscation. Står den på igjen,
    skal røyktesten si det — og si hvor den slås av."""
    m = _bygg(tmp_path)
    forside = (m / "index.html").read_text(encoding="utf-8")
    levende = forside.replace(BUNN, f"<p>{OBFUSKERT}</p>")
    feil = royktest.kjor(
        "https://x.test", royktest.utvalg(m, UKE), CSP, forsok=1, pause=0,
        henter=_levende(m, overstyr={"": (
            200, {"content-security-policy": CSP}, levende,
            "https://x.test/")}), adresse=ADRESSE)
    assert any("står ikke som klartekst" in f for f in feil), feil
    assert any("Email Address Obfuscation" in f for f in feil), feil
    assert all(f.startswith("/:") for f in feil), feil


def test_en_annen_adresse_enn_bygget_er_rod(tmp_path):
    m = _bygg(tmp_path)
    feil = royktest.kjor("https://x.test", royktest.utvalg(m, UKE), CSP,
                         forsok=1, pause=0, henter=_levende(m),
                         adresse="noen@eksempel.no")
    assert len(feil) == 5, feil                 # alle fem sidene


def test_main_er_rod_naar_bygget_ikke_har_en_adresse(tmp_path, capsys):
    m = _bygg(tmp_path / "m")
    forside = m / "index.html"
    forside.write_text(forside.read_text(encoding="utf-8").replace(BUNN, ""),
                       encoding="utf-8")
    k = tmp_path / "k.json"
    k.write_text(f'{{"uke": "{UKE}"}}', encoding="utf-8")
    assert royktest.main(["--mappe", str(m), "--kvittering", str(k),
                          "--forsok", "1", "--pause", "0"]) == 1
    assert "ingen mailto:-lenke" in capsys.readouterr().out


@pytest.mark.parametrize("hva,overstyr,csp,ventet", [
    ("status", {"lokalitet/9/": (404, {}, "", "")}, CSP, "status 404"),
    ("csp mangler", {}, "", "ingen Content-Security-Policy"),
    ("csp annen", {}, "default-src *", "ikke den _headers oppgir"),
    ("kart", {"produksjonsomrade/2/": (
        200, {"content-security-policy": CSP}, "<p>uten</p>",
        "https://x.test/produksjonsomrade/2/")}, CSP, "kartattribusjonen"),
    ("gammel forside", {"": (
        200, {"content-security-policy": CSP},
        f'<a href="/endringer/2026-40/">x</a>{royktest.KARTVERKET}',
        "https://x.test/")}, CSP, "lenker ikke til nyeste uke"),
    ("gammel ukeside", {f"endringer/{UKE}/": (
        200, {"content-security-policy": CSP},
        "<title>Endringer i uke 40, 2026 — Kystloggen</title>",
        f"https://x.test/endringer/{UKE}/")}, CSP, "tittelen er"),
])
def test_hver_proeve_feller_det_den_skal(tmp_path, hva, overstyr, csp,
                                         ventet):
    m = _bygg(tmp_path)
    feil = royktest.kjor("https://x.test", royktest.utvalg(m, UKE), CSP,
                         forsok=1, pause=0,
                         henter=_levende(m, csp=csp, overstyr=overstyr))
    assert any(ventet in f for f in feil), feil


def test_siste_forsok_teller(tmp_path):
    """Utrullingen bruker noen sekunder. Et forsøk som feiler før den er
    framme skal ikke felle jobben når neste svarer."""
    m = _bygg(tmp_path)
    riktig = _levende(m)
    kall = {"n": 0}

    def treg(url):
        kall["n"] += 1
        if kall["n"] <= 5:                      # hele første runde
            return (503, {}, "", url)
        return riktig(url)

    assert royktest.kjor("https://x.test", royktest.utvalg(m, UKE), CSP,
                         forsok=2, pause=0, henter=treg) == []


def test_main_er_rod_naar_utvalget_ikke_kan_settes_sammen(tmp_path, capsys):
    m = _bygg(tmp_path / "m")
    k = tmp_path / "k.json"
    k.write_text('{"uke": "2026-42"}', encoding="utf-8")
    assert royktest.main(["--mappe", str(m), "--kvittering", str(k),
                          "--forsok", "1", "--pause", "0"]) == 1
    assert "::error::Røyktesten kunne ikke settes opp" in capsys.readouterr().out


# ---- www → apex ---------------------------------------------------------

def _www(svar: dict):
    """En henter for www-verten: sti → (status, location)."""
    def henter(url):
        sti = "/" + url.split("://", 1)[1].split("/", 1)[1]
        status, location = svar.get(sti, (301, "https://x.test" + sti))
        return (status, {"location": location} if location else {}, "", url)
    return henter


def test_www_stiene_er_roten_og_en_dyp_sti(tmp_path):
    sider = royktest.utvalg(_bygg(tmp_path), UKE)
    assert royktest.www_stier(sider) == ["/", "/lokalitet/9/"]


def test_www_med_301_til_samme_sti_er_rent(tmp_path):
    m = _bygg(tmp_path)
    assert royktest.kjor("https://x.test", royktest.utvalg(m, UKE), CSP,
                         forsok=1, pause=0, henter=_levende(m),
                         adresse=ADRESSE, www="https://www.x.test",
                         www_henter=_www({})) == []


@pytest.mark.parametrize("svar,ventet", [
    ({"/": (200, "")}, "www.x.test/: status 200, ikke 301"),
    ({"/": (308, "https://x.test/")}, "status 308"),
    ({"/": (302, "https://x.test/")}, "status 302"),
    # Alt til forsiden: svarer, men mister stien.
    ({"/lokalitet/9/": (301, "https://x.test/")},
     "www.x.test/lokalitet/9/: 301 til «https://x.test/»"),
    ({"/": (301, "https://www.x.test/")}, "301 til «https://www.x.test/»"),
])
def test_www_som_ikke_videresender_riktig_er_rod(tmp_path, svar, ventet):
    m = _bygg(tmp_path)
    feil = royktest.kjor("https://x.test", royktest.utvalg(m, UKE), CSP,
                         forsok=1, pause=0, henter=_levende(m),
                         adresse=ADRESSE, www="https://www.x.test",
                         www_henter=_www(svar))
    assert len(feil) == 1 and ventet in feil[0], feil


def test_www_sjekkes_bare_for_produksjonsadressen(monkeypatch, tmp_path):
    """En annen --base (en forhåndsvisning) har ingen www-vert."""
    m = _bygg(tmp_path / "m")
    k = tmp_path / "k.json"
    k.write_text(f'{{"uke": "{UKE}"}}', encoding="utf-8")
    sett = {}

    def kjor(*a, **kw):
        sett.update(kw)
        return []
    monkeypatch.setattr(royktest, "kjor", kjor)
    royktest.main(["--mappe", str(m), "--kvittering", str(k)])
    assert sett["www"] == royktest.WWW
    royktest.main(["--mappe", str(m), "--kvittering", str(k),
                   "--base", "https://forhandsvisning.kystloggen.pages.dev"])
    assert sett["www"] == ""
