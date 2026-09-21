"""Kontrasten på de fargeparene som FAKTISK brukes. WCAG 2.2 AA.

En palett er en tredjeparts verdier satt sammen på vår måte, og begge
halvdeler kan endre seg: Digdir kan justere `neutral-text-subtle` i en
ny tagg, og vi kan bytte hvilken flate en dempet tekst står på. Ingen
av de to endringene ser ut som noe i en diff. Derfor måles forholdet
her framfor å antas.

Prøven KJØRER regnestykket framfor å sjekke tall noen har skrevet ned.
`kontrast()` er WCAG-formelen, verifisert mot to kjente fasiter i
`test_formelen_stemmer`; en prøve som sammenlignet med en tabell av
forhåndsregnede verdier ville bare målt at noen hadde kopiert riktig.

## Hva som måles, og hva som ikke kan måles her

Fargene leses ut av `maler/tokens.css` og `maler/stil.css` — kildene,
ikke en kopi. Parene under er skrevet ned, og det er grensa: prøven vet
hvilke par som finnes fordi et menneske har fortalt den det, ikke fordi
den har rendret siden. Settes en dempet tekst på en ny flate uten at
lista utvides, er prøven grønn og blind der.

Det er samme slaget grense som markupkontrakten har (den ser `{{ }}` i
malen, ikke verdier i utputtet), og den er skrevet ned av samme grunn.
`test_hvert_navn_i_lista_finnes_i_css` fanger den motsatte driften: et
par som viser til en variabel som er slettet.

## Terskler

    4.5:1   vanlig tekst              WCAG 1.4.3 AA
    3:1     stor tekst (>=24px)       WCAG 1.4.3 AA
    3:1     grafikk og kanter         WCAG 1.4.11 AA
"""

import re
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
TOKENS = ROT / "maler" / "tokens.css"
STIL = ROT / "maler" / "stil.css"

AA_TEKST = 4.5
AA_STOR = 3.0
AA_GRAFIKK = 3.0


# ---- formelen ---------------------------------------------------------

def _kanal(c: int) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminans(hex_: str) -> float:
    r, g, b = (_kanal(c) for c in rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(a: str, b: str) -> float:
    la, lb = luminans(a), luminans(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def over(forgrunn: str, bakgrunn: str, alfa: float) -> str:
    """Forgrunnen lagt over bakgrunnen med gjennomsiktighet.

    Kartpunktene har `fill-opacity: 0.6`. Kontrasten gjelder det ØYET
    ser, altså blandingen — måles fyllfargen alene, måler vi en farge
    som ikke står noe sted på siden."""
    f, b = rgb(forgrunn), rgb(bakgrunn)
    return "#" + "".join(f"{round(alfa * f[i] + (1 - alfa) * b[i]):02x}"
                         for i in range(3))


# ---- fargene, lest ut av CSS-en ---------------------------------------

def _blokker(tekst: str) -> tuple[str, str]:
    """(lys, mørk) — teksten utenfor og inne i prefers-color-scheme.

    SLUTTEN TELLES MED KLAMMER, ikke søkes etter som tekst. Fram til
    21.09.2026 lette denne etter strengen `\n}\n}` — mediespørringens
    slutt slik den tilfeldigvis var skrevet. Da `stil.css` fikk et
    innrykk (`\n  }\n}`), fant `find` ingenting og returnerte -1:

        lys  = tekst[:i] + tekst[-1:]     alt ETTER blokka forsvant
        mørk = tekst[i:-1]                alt etter blokka ble MØRKT

    Følgen var stille og nøyaktig gal vei. Aliasene `--farge-*` lå
    etter mediespørringen; i lys modus fantes de ikke, og prøven falt
    med KeyError framfor å måle. Hadde de ligget før, ville prøven vært
    grønn og samtidig målt mørke verdier som lyse.

    Det er samme feilform som CLAUDE.md 1b-2 beskriver: en mekanisme
    som måler noe som LIGNER det den skal måle, og som er riktig helt
    til formateringen endrer seg."""
    i = tekst.find("@media (prefers-color-scheme: dark)")
    if i < 0:
        return tekst, ""
    dybde = 0
    for j in range(tekst.index("{", i), len(tekst)):
        if tekst[j] == "{":
            dybde += 1
        elif tekst[j] == "}":
            dybde -= 1
            if dybde == 0:
                slutt = j + 1
                break
    else:
        raise AssertionError("mediespørringen lukkes aldri")
    return tekst[:i] + tekst[slutt:], tekst[i:slutt]


def _deklarasjoner(tekst: str) -> dict[str, str]:
    return dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", tekst))


def palett(mork: bool) -> dict[str, str]:
    """Hvert variabelnavn løst helt ned til en hex-verdi.

    Leser BEGGE filene og følger `var()`-kjeden: `--farge-tekst` peker
    på `--ds-color-neutral-text-default`, som peker på en hex. Løses den
    ikke opp, måler prøven på strengen «var(--…)» og er grønn uansett."""
    ut: dict[str, str] = {}
    for sti in (TOKENS, STIL):
        lys_del, mork_del = _blokker(sti.read_text(encoding="utf-8"))
        ut.update(_deklarasjoner(lys_del))
        if mork:
            ut.update(_deklarasjoner(mork_del))

    def los(navn: str, dybde: int = 0) -> str:
        verdi = ut[navn].strip()
        m = re.fullmatch(r"var\((--[a-z0-9-]+)\)", verdi)
        if m:
            assert dybde < 10, f"var()-løkke på {navn}"
            return los(m.group(1), dybde + 1)
        return verdi

    return {navn: los(navn) for navn in ut
            if re.fullmatch(r"(var\(--[a-z0-9-]+\)|#[0-9a-f]{6})",
                            ut[navn].strip())}


# ---- parene som faktisk brukes ----------------------------------------
#
# (forgrunn, bakgrunn, terskel, hvor det står). Alfa der forgrunnen er
# gjennomsiktig.

PAR = [
    # Brødtekst. Arket er hvitt, stripa er annenhver tabellrad, bunnen
    # er flata bunnteksten ligger på utenfor arket.
    ("--farge-tekst", "--farge-ark", AA_TEKST, "brødtekst på ark", 1.0),
    ("--farge-tekst", "--farge-stripe", AA_TEKST, "tabellrad, tonet", 1.0),
    ("--farge-tekst", "--farge-hode", AA_TEKST, "tabellhode", 1.0),
    ("--farge-tekst", "--farge-bunn", AA_TEKST, "tekst utenfor arket", 1.0),

    # Dempet tekst: captionens plass er full farge, men bunnteksten,
    # «ikke oppgitt av kilden» og «forskriften oppgir ikke farge» er
    # dempet. De er de mest utsatte parene på hele siden.
    ("--farge-tekst-svak", "--farge-ark", AA_TEKST, "dempet på ark", 1.0),
    ("--farge-tekst-svak", "--farge-stripe", AA_TEKST, "dempet i tonet rad", 1.0),
    ("--farge-tekst-svak", "--farge-bunn", AA_TEKST, "bunnteksten", 1.0),

    # Lenker, i alle tre tilstandene og på hver flate de står på.
    ("--farge-lenke", "--farge-ark", AA_TEKST, "lenke på ark", 1.0),
    ("--farge-lenke", "--farge-stripe", AA_TEKST, "lenke i tonet rad", 1.0),
    ("--farge-lenke", "--farge-bunn", AA_TEKST, "lenke i bunnteksten", 1.0),
    ("--farge-lenke-besokt", "--farge-ark", AA_TEKST, "besøkt lenke", 1.0),
    ("--farge-lenke-besokt", "--farge-stripe", AA_TEKST, "besøkt, tonet rad", 1.0),
    ("--farge-lenke-aktiv", "--farge-ark", AA_TEKST, "lenke under peker", 1.0),

    # Grafikk og kanter: 3:1. Ringen rundt trafikklysruta står på tre
    # ulike flater, og det er den som bærer at en GUL rute er synlig —
    # gul kan ikke nå 3:1 mot hvitt og slutte å være gul.
    ("--farge-kant", "--farge-ark", AA_GRAFIKK, "ring rundt fargerute", 1.0),
    ("--farge-kant", "--farge-stripe", AA_GRAFIKK, "ring, tonet rad", 1.0),
    ("--farge-kant", "--farge-hode", AA_GRAFIKK, "ring i tabellhode", 1.0),
    ("--farge-kant-sterk", "--farge-hode", AA_GRAFIKK, "streken under hodet", 1.0),
    ("--farge-fokus", "--farge-ark", AA_GRAFIKK, "fokusmarkør", 1.0),

    # Kartpunktene, med fyllet de faktisk har.
    ("--farge-kart-punkt", "--farge-ark", AA_GRAFIKK, "kartpunkt (60 % fyll)", 0.6),
]

# Trafikklysrutene måles for seg. De har INGEN terskel som tekst, fordi
# de ikke er tekst: ordet «gul» står i cellen i vanlig tekstfarge, og
# ruta er en `::before` som bare finnes i CSS-en. Tallene står her fordi
# et tall man ikke ser normalverdien til er et tall ingen kan vurdere —
# ikke fordi en av dem skal passere 4,5.
RUTER = ["--lys-rod", "--lys-gul", "--lys-gronn"]

# Digdirs egne status-farger. IKKE variabler noe sted — de står i en
# kommentar i tokens.css nettopp for at de ikke skal kunne brukes. Her
# er de målestokken: hvor langt trafikklyset ligger fra dem.
DS_STATUS = {
    False: {"--lys-rod": "#c01b1b", "--lys-gul": "#ea9b1b",
            "--lys-gronn": "#068718"},
    True: {"--lys-rod": "#d76e6e", "--lys-gul": "#60400b",
           "--lys-gronn": "#138d24"},
}


# ---- prøvene ----------------------------------------------------------

def test_formelen_stemmer():
    """Kontrollen av kontrollen. Feiler denne, er hvert tall under feil
    på samme måte, og alle prøvene er grønne likevel."""
    assert round(kontrast("#000000", "#ffffff"), 2) == 21.0
    assert round(kontrast("#777777", "#ffffff"), 2) == 4.48
    assert round(kontrast("#ffffff", "#ffffff"), 2) == 1.0


def test_blandingen_stemmer():
    assert over("#000000", "#ffffff", 0.5) == "#808080"
    assert over("#000000", "#ffffff", 1.0) == "#000000"
    assert over("#123456", "#ffffff", 0.0) == "#ffffff"


def test_blokkdelingen_taaler_innrykk():
    """Driftvakten for `_blokker`. En variabel som står ETTER
    mediespørringen skal havne i lys-halvdelen uansett hvordan blokka
    er rykket inn — det var nøyaktig det som sviktet 21.09.2026."""
    css = ("""\
:root { --a: #111111; }
@media (prefers-color-scheme: dark) {
  :root {
    --a: #eeeeee;
  }
}
:root { --b: var(--a); }
""")
    lys, mork = _blokker(css)
    assert "--b" in lys, "variabel etter mediespørringen falt ut av lys modus"
    assert "--b" not in mork, "variabel etter mediespørringen ble lest som mørk"
    assert "#eeeeee" in mork and "#eeeeee" not in lys


def test_hvert_navn_i_lista_finnes_i_css():
    """Driftvakten. Et par som viser til en variabel som er slettet,
    skal felle — ikke hoppes stille over."""
    p = palett(mork=False)
    for navn in {n for par in PAR for n in par[:2]} | set(RUTER):
        assert navn in p, f"{navn} finnes ikke i CSS-en lenger"


@pytest.mark.parametrize("mork", [False, True], ids=["lys", "mørk"])
def test_aa_paa_hvert_par(mork):
    p = palett(mork)
    feil = []
    for fg, bg, krav, hvor, alfa in PAR:
        farge = over(p[fg], p[bg], alfa) if alfa < 1 else p[fg]
        k = kontrast(farge, p[bg])
        if k < krav:
            feil.append(f"{hvor}: {p[fg]} på {p[bg]} = {k:.2f}:1, krever {krav}")
    assert not feil, "\n".join(feil)


@pytest.mark.parametrize("mork", [False, True], ids=["lys", "mørk"])
def test_rutene_skilles_fra_hverandre_i_lyshet(mork):
    """Rød og grønn er den klassiske forvekslingen. Ordet står i cellen
    og bærer betydningen uansett — men to ruter som er like LYSE er to
    ruter ingen kan skille i gråtone heller. Luminansen skal skille."""
    p = palett(mork)
    lys = sorted(luminans(p[r]) for r in RUTER)
    for a, b in zip(lys, lys[1:]):
        forhold = (b + 0.05) / (a + 0.05)
        assert forhold >= 1.5, f"to ruter ligger {forhold:.2f}:1 fra hverandre"


def test_rapport(capsys):
    """Ikke en terskel — en måling som skrives hver kjøring.

        pytest tests/test_kontrast.py -k rapport -s
    """
    linjer = []
    for mork in (False, True):
        p = palett(mork)
        linjer.append(f"\n=== {'MØRK' if mork else 'LYS'} MODUS ===")
        linjer.append(f"{'par':34} {'forgrunn':9} {'bakgrunn':9} {'målt':>7}  krav")
        for fg, bg, krav, hvor, alfa in PAR:
            farge = over(p[fg], p[bg], alfa) if alfa < 1 else p[fg]
            k = kontrast(farge, p[bg])
            merke = "ok " if k >= krav else "FEIL"
            linjer.append(f"{hvor:34} {farge:9} {p[bg]:9} {k:6.2f}:1  "
                          f"{krav} {merke}")
        linjer.append(f"\n{'trafikklysrute':34} {'verdi':9} {'mot ark':>9} "
                      f"{'L':>7}  avstand til Digdirs status")
        for r in RUTER:
            linjer.append(
                f"{r:34} {p[r]:9} {kontrast(p[r], p['--farge-ark']):6.2f}:1 "
                f"{luminans(p[r]):7.3f}  "
                f"{kontrast(p[r], DS_STATUS[mork][r]):.2f}:1 mot "
                f"{DS_STATUS[mork][r]}")
    print("\n".join(linjer))
    assert capsys.readouterr().out
