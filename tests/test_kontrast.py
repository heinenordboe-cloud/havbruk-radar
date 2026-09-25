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

Fargene leses ut av `maler/stil.css` — kilden, ikke en kopi. (Fram til
22.09.2026 leste den også `maler/tokens.css`; den fila finnes ikke
lenger, se stilarkets egen innledning.) Parene under er skrevet ned, og
det er grensa: prøven vet
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

    Følger `var()`-kjeden: `--farge-tekst` peker på `--ink`, som peker
    på en hex. Løses den ikke opp, måler prøven på strengen «var(--…)»
    og er grønn uansett."""
    ut: dict[str, str] = {}
    lys_del, mork_del = _blokker(STIL.read_text(encoding="utf-8"))
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
    # ---- PAPIR ----
    # Det er ikke lenger et hvitt ark under innholdet (se stilarkets
    # avsnitt 2). Innholdet står på papiret, og den innfelte flata
    # `--papir2` er siteringsboksen, arkivlinja og skjemafeltene.
    ("--farge-tekst", "--papir", AA_TEKST, "brødtekst på papir", 1.0),
    ("--farge-tekst", "--papir2", AA_TEKST, "brødtekst i innfelt boks", 1.0),

    # Dempet tekst er de mest utsatte parene på hele siden, og den er
    # en HEKSVERDI og ikke en alfa nettopp derfor — se AVVIK 1.
    ("--farge-tekst-svak", "--papir", AA_TEKST, "dempet på papir", 1.0),
    ("--farge-tekst-svak", "--papir2", AA_TEKST, "dempet i innfelt boks", 1.0),

    # Lenker, i alle tre tilstandene og på begge papirflater.
    ("--farge-lenke", "--papir", AA_TEKST, "lenke på papir", 1.0),
    ("--farge-lenke", "--papir2", AA_TEKST, "lenke i innfelt boks", 1.0),
    ("--farge-lenke-besokt", "--papir", AA_TEKST, "besøkt lenke", 1.0),
    ("--farge-lenke-aktiv", "--papir", AA_TEKST, "lenke under peker", 1.0),

    # Grafikk og kanter: 3:1. Ringen rundt trafikklysruta står på to
    # flater, og det er den som bærer at en GUL rute er synlig — gul
    # kan ikke nå 3:1 mot L*88-papir og slutte å være gul (AVVIK 3).
    ("--farge-kant", "--papir", AA_GRAFIKK, "ring rundt fargerute", 1.0),
    ("--farge-kant", "--papir2", AA_GRAFIKK, "ring, innfelt boks", 1.0),
    ("--farge-kant-sterk", "--papir", AA_GRAFIKK, "streken under tabellhodet", 1.0),
    ("--farge-fokus", "--papir", AA_GRAFIKK, "fokusmarkør", 1.0),

    # Kartet og grafene, med fyllet de faktisk har.
    ("--farge-kart-punkt", "--papir", AA_GRAFIKK, "kartpunkt (60 % fyll)", 0.6),
    ("--kart-gitter", "--papir", AA_GRAFIKK, "gradnettets linjer", 1.0),
    ("--kart-kyst", "--kart-land", AA_GRAFIKK, "kystlinja mot landflata", 1.0),
    ("--farge-tekst-svak", "--papir", AA_TEKST, "gradnettets etiketter", 1.0),
    ("--graf-linje", "--papir", AA_GRAFIKK, "lusekurven", 1.0),
    ("--graf-linje", "--graf-brakk", AA_GRAFIKK, "kurven over et brakkbånd", 1.0),
    ("--hav5", "--papir", AA_GRAFIKK, "søyler i lus- og biomassegrafen", 1.0),
    # Ukestripa på lokalitetssiden fyller ruta med søylefargen og setter
    # tekst oppå. `--hav5` er MØRK i lys modus og LYS i mørk, så teksten
    # må snu med den — samme felle som knappeteksten gikk i.
    ("--soyle-tekst", "--hav5", AA_TEKST, "tekst i en fylt ukerute", 1.0),

    # ---- MØRK FLATE ----
    # Heroen, headeren på undersidene, kystseksjonen og bunnteksten.
    # `--hav-tittel` og ikke `--farge-tekst`: på hav er blekk 1,2:1.
    ("--hav-tittel", "--hav9", AA_STOR, "H1 og nøkkeltall på mørk flate", 1.0),
    ("--hav-tegn", "--hav9", AA_TEKST, "brødtekst på mørk flate", 1.0),
    ("--hav-sekundaer", "--hav9", AA_TEKST, "sekundærtekst på mørk flate", 1.0),
    ("--hav3", "--hav9", AA_TEKST, "brødsmule og etikett på mørk flate", 1.0),
    ("--rust-lys", "--hav9", AA_TEKST, "lenke og etikett på mørk flate", 1.0),
    ("--rust-lys", "--hav9", AA_GRAFIKK, "ordmerkets linjal på mørk flate", 1.0),

    # Knappen. Teksten i den er `--knapp-tekst` og ikke `--papir`:
    # knappen er mørk i BEGGE moduser, papiret er det ikke.
    ("--knapp-tekst", "--knapp-flate", AA_TEKST, "tekst i primærknapp", 1.0),
    ("--knapp-tekst", "--knapp-flate-pa", AA_TEKST, "tekst i knapp under peker", 1.0),
]

# BÅNDET MOT SIDEN RUNDT. Ikke et WCAG-krav — en flate som er utydelig
# er ikke utilgjengelig — men den bærer hele identiteten, og i mørk
# modus var den 1,04:1 og dermed ikke en flate i det hele tatt. Tallet
# står her framfor i en kommentar, fordi et tall ingen måler er et tall
# som driver.
BAND_MOT_SIDE = 1.25

# Trafikklysrutene måles for seg. De har INGEN terskel som tekst, fordi
# de ikke er tekst: ordet «gul» står i cellen i vanlig tekstfarge, og
# ruta er en `::before` som bare finnes i CSS-en. Tallene står her fordi
# et tall man ikke ser normalverdien til er et tall ingen kan vurdere —
# ikke fordi en av dem skal passere 4,5.
RUTER = ["--lys-rod", "--lys-gul", "--lys-gronn"]

# Digdirs egne status-farger. IKKE variabler noe sted, og fra
# 22.09.2026 ikke i noen fil i repoet heller — `tokens.css` er borte.
# De står som literaler HER, som målestokken trafikklyset måles mot:
# hvor langt en datafarge ligger fra en varselfarge.
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
def test_baandet_er_en_flate_i_begge_moduser(mork):
    """Hero-båndet er den eneste mettede flaten på nettstedet, og en
    flate ingen ser er ingen flate. I lys modus er havet mørkere enn
    papiret; i mørk modus må det være LYSERE, ellers forsvinner det i
    bunnen. Forholdet måles, retningen ikke."""
    p = palett(mork)
    k = kontrast(p["--hav9"], p["--papir"])
    assert k >= BAND_MOT_SIDE, (
        f"båndet {p['--hav9']} mot siden {p['--papir']} = {k:.2f}:1")


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


# ==================================== heroen over et bilde med snø
#
# Flata under teksten i heroen er et FOTO, ikke en farge, og et foto kan
# ikke leses av `palett()`. MÅLT 24.09.2026 med Chromium på
# `maler/bilde/hero-1600.jpg`: bildet inneholder RENE HVITE piksler
# (255,255,255), både i øverste fjerdedel der menyen står og i nederste
# der tagline og løsen står.
#
# `--papir` #e7dbd0 over hvitt er 1,36:1. Toningen er derfor ikke
# stemning — den er det eneste som gjør teksten lesbar, og alfaen er
# regnet ut her og ikke valgt.

HERO_TONING = re.compile(r"\.hero-(?:meny|bunn)\s*\{([^}]*)\}", re.S)
RGBA = re.compile(r"rgba\(\s*6,\s*22,\s*29,\s*([\d.]+)\s*\)")


def test_toningen_bak_heroteksten_holder_45_mot_hvitt():
    """Gulvet er målt, ikke valgt: 0,65 gir 4,24:1 og 0,70 gir 5,07:1.

    Prøven leser alfaene ut av stilarket og krever at hver av dem som
    IKKE er en utfasing (0) holder 4,5:1 mot hvitt. Faller den, er det
    fordi noen dempet toningen — og da er teksten uleselig over snøen
    uten at noe annet endrer seg.
    """
    css = STIL.read_text(encoding="utf-8")
    # `.hero-meny, .hero-bunn { position: relative }` treffer også, og
    # den har ingen toning. Vi vil ha blokkene som HAR en.
    blokker = [b for b in HERO_TONING.findall(css) if "rgba" in b]
    assert len(blokker) == 2, "fant ikke begge toningene"

    alfaer = [float(a) for b in blokker for a in RGBA.findall(b)]
    assert alfaer, "ingen rgba-stopp i toningen"
    for alfa in alfaer:
        if alfa == 0:
            continue                     # utfasingen mot bildet
        flate = over("#06161d", "#ffffff", alfa)
        assert kontrast("#e7dbd0", flate) >= 4.5, (
            f"alfa {alfa} gir {kontrast('#e7dbd0', flate):.2f}:1 mot hvitt")


def test_soekefeltet_har_egen_ugjennomsiktig_bunn():
    """Feltet er ikke tekst på et foto — det er en lys boks med mørk
    tekst. Ble bunnen gjennomsiktig, ville bildet skint gjennom, og da
    er det toningen som måtte båret den også."""
    css = STIL.read_text(encoding="utf-8")
    blokk = re.search(r"\n\.sok \{([^}]*)\}", css).group(1)
    assert "background: var(--papir)" in blokk
    assert "rgba" not in blokk, "en gjennomsiktig bunn slipper bildet gjennom"
