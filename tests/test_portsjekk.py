"""Porten: avsnitt over tre linjer, og påstander uten kilde og dato.

Tekstreglene fra 20.10.2026 (docs/design/BRIEF.md). Prøvene går gjennom
`tekstfunn()`, den ene døra porten sender hver fil gjennom: fjernes
koblingen i porten, feiler de. Sidene er konstruerte, ikke bygget.
"""

import publiseringsvakt as vakt

LOK = "lokalitet/10204/index.html"


def _funn(html: str, rel: str = LOK, slag: str | None = None) -> list:
    funn = vakt.tekstfunn(rel, ".html", f"<html><body>{html}</body></html>",
                          set(), set())
    return [f for f in funn if slag is None or f.slag == slag]


def _herkomst(dato="2026-09-30", kort="Fiskeridir."):
    return (f'<span class="herkomst">{kort} · '
            f'<time datetime="{dato}">30.09.2026</time></span>')


GOD = (f'<section><div data-kilde="biomasselag" data-gjelder="2026-09-30" '
       f'data-nivaa="oppgitt"><span data-felt="har_fisk">ja</span>'
       f'{_herkomst()}</div></section>')


# ---- avsnittene ---------------------------------------------------------

def test_et_avsnitt_over_grensa_feller_porten():
    assert _funn("<p>" + "a" * 111 + "</p>", slag="avsnitt")
    assert not _funn("<p>" + "a" * 110 + "</p>", slag="avsnitt")


def test_grensa_gjelder_ogsaa_bak_et_klikk():
    lang = "<p>" + "ord " * 40 + "</p>"
    assert _funn(f"<details><summary>Mer</summary>{lang}</details>",
                 rel="om/index.html", slag="avsnitt")


def test_hver_sidetype_proves_ikke_bare_lokaliteten():
    for rel in ("index.html", "om/index.html", "selskap/1/index.html",
                "produksjonsomrade/4/index.html", "endringer/2026-43/index.html"):
        assert _funn("<li>" + "b" * 200 + "</li>", rel=rel, slag="avsnitt"), rel


def test_den_innerste_blokken_eier_teksten_sin():
    """En <p> i en <li> måles for seg; lia måles uten den."""
    html = "<li>kort <p>" + "c" * 100 + "</p></li>"
    assert not _funn(html, slag="avsnitt")


def test_siteringen_og_kildens_egen_tekst_kortes_ikke():
    lang = "d" * 200
    assert not _funn(f'<p class="siterbar">{lang}</p>', slag="avsnitt")
    assert not _funn(f'<blockquote data-felt="beslutningssitat">{lang}</blockquote>',
                     slag="avsnitt")


def test_en_verdi_i_en_div_er_ikke_lias_avsnitt():
    """Tidslinjeposten: overskrift i <p>, verdien — en liste tillatelser —
    i <div>. Verdien er data, ikke prosa."""
    html = '<li><p>kort</p><div class="tidsakse-verdi">' + "H-K-0034, " * 20 + "</div></li>"
    assert not _funn(html, slag="avsnitt")


def test_skript_og_svg_teller_ikke():
    assert not _funn("<p><script>" + "x" * 300 + "</script>kort</p>", slag="avsnitt")


# ---- påstandene ---------------------------------------------------------

def test_en_merket_paastand_med_herkomst_slipper_gjennom():
    assert not _funn(GOD, slag="paastand")


def test_en_verdi_uten_kilde_og_gjelder_dato_feller_porten():
    funn = _funn('<section><span data-felt="har_fisk">ja</span></section>',
                 slag="paastand")
    assert funn and "uten kilde og gjelder-dato" in funn[0].utdrag


def test_gjelder_maa_vaere_en_dato():
    html = GOD.replace('data-gjelder="2026-09-30"', 'data-gjelder="september"')
    assert _funn(html, slag="paastand")


def test_datoen_maa_staa_paa_siden():
    html = GOD.replace(_herkomst(), '<span class="herkomst">Fiskeridir.</span>')
    funn = _funn(html, slag="paastand")
    assert funn and "datoen står ikke" in funn[0].utdrag


def test_kilden_maa_staa_i_en_herkomstlinje():
    html = GOD.replace(_herkomst(), '<time datetime="2026-09-30">30.09.2026</time>')
    funn = _funn(html, slag="paastand")
    assert funn and "Fiskeridir." in funn[0].utdrag


def test_seksjonens_herkomstlinje_dekker_radene_i_den():
    """Registerfeltene deler én grå linje: dato og utgiver i seksjonen."""
    html = ('<section><span class="herkomst">Fiskeridir. · '
            '<time datetime="2026-10-19">19.10.2026</time></span>'
            '<div data-kilde="akvakultur" data-gjelder="2026-10-19">'
            '<dd data-felt="kommune">Averøy</dd></div></section>')
    assert not _funn(html, slag="paastand")


def test_en_indikasjon_vises_aldri():
    html = GOD.replace('data-nivaa="oppgitt"', 'data-nivaa="indikasjon"')
    assert _funn(html, slag="paastand")


def test_paastandsprøven_gjelder_lokalitetssidene():
    """Påstandsmodellen er bygget for lokalitetssiden; de andre sidetypene
    har ennå ikke merkingen, og prøven melder dem ikke."""
    html = '<section><span data-felt="har_fisk">ja</span></section>'
    assert not _funn(html, rel="selskap/1/index.html", slag="paastand")
