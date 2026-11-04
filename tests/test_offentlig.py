"""Kodrepoet er offentlig: kode og metode, ikke funn (økt 3c, punkt 3).

Porttesten stopper en commit med et 9-sifret organisasjonsnummer eller et
AS/ASA-navn i docs/, analyse/ og predictions/. Et funn, en analyse eller
et anslag som navngir selskaper, skrives i det private `havbruk-analyse`
med samme sti (RUNBOOK, «Offentlig og privat»).

To lister slipper gjennom:

  KILDEBESKRIVELSER  hele filer, fordi en kildebeskrivelse viser feltene
                     kilden leverer, og et orgnr er et av dem.
  UNNTAK             hvert enkelt navn og nummer i en fil som ikke er en
                     kildebeskrivelse, med grunnen. Et NYTT navn i samme
                     fil stopper porten, og et navn som ikke lenger står
                     der, gjør det også: lista skal være sann, ikke bare
                     romslig.

Et orgnr er ni siffer som begynner på 8 eller 9 og har riktig
kontrollsiffer (modulus 11, Brønnøysundregistrene). Det er spørsmålet vi
vil ha svar på (CLAUDE.md 1b-2): «ni siffer» alene treffer sha-er,
MMSI-er og beløp.

MÅLT 04.11.2026, før flyttingen: 34 av 574 filer hadde et treff. Tre av
dem var funn (MALING-FUNN-OKTOBER, MALING-UKE-39, MALING-PANTEKSPONERING)
og ble flyttet; resten står under.
"""
import re
import subprocess
from fnmatch import fnmatchcase
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
MAPPER = ("docs", "analyse", "predictions")

ORGNR = re.compile(r"(?<![0-9A-Za-z])([89]\d{2}) ?(\d{3}) ?(\d{3})(?![0-9A-Za-z])")
NAVN = re.compile(r"\b[A-ZÆØÅ][\wÆØÅæøå&.-]*(?: [A-ZÆØÅ0-9][\wÆØÅæøå&.-]*){0,5} (?:AS|ASA)\b")

KILDEBESKRIVELSER = {
    "docs/KILDE-*.md": "kildebeskrivelser: eksempler på feltene kilden leverer",
}

KILDE = "en kilde beskrevet i en måling (utgiver, eller hvordan radene knyttes), ikke et funn"
SIDE = "adressen til en publisert side i bygget"
RUNBOOK = "eksempel på nyhetsbrevets form"
BESLUTNING = "eksempel i en beslutning om metode (format, utvalg, filter), eller oppdiktet"
DESIGN = "en publisert side brukt som eksempel i design og visning"
OVERLEVERING = "designoverleveringen: plassholdere (Selskap A AS) og eksempeldata"

UNNTAK = {
    'docs/LANSERING.md': (SIDE, {'921668236'}),
    'docs/MALING-NYE-KILDER.md': (KILDE, {'DN Media Group Global AS'}),
    'docs/MALING-UNNTAKSVEKST.md': (KILDE, {'SJØTROLL HAVBRUK SJØ AS', 'VEST SJØ AS'}),
    'docs/RUNBOOK.md': (RUNBOOK, {'NORDLAKS OPPDRETT AS', 'SALMAR FARMING AS'}),
    'docs/beslutninger/2026-08-22-enk-filtreres-i-kilden.md': (BESLUTNING, {'Ola Nordmann AS'}),
    'docs/beslutninger/2026-08-24-utvalgsutvidelse-er-ikke-endring.md': (BESLUTNING, {'DOMSTEIN SERVICE AS', 'Helt Fersk AS', 'Innhentet AS', 'RØN GARD AS'}),
    'docs/beslutninger/2026-09-02-eierskapshistorikk-backfill.md': (BESLUTNING, {'AQUA FARMS AS', 'MARINE HARVEST LABRUS AS', 'MOWI NORWAY AS', 'PAN FISH NORWAY AS', 'SALMAR FINNMARK AS'}),
    'docs/beslutninger/2026-09-03-organisasjonsform-fra-brreg.md': (BESLUTNING, {'929706331', '959352887', '985937028', 'AQUA FARMS AS', 'FRØY HAVBRUK AS', 'GRIEG SEAFOOD ROGALAND SJØ AS', 'GÅSØ NÆRINGSUTVIKLING AS', 'MARINE HARVEST LABRUS AS', 'MARINE HARVEST NORWAY AS', 'MOWI NORWAY AS', 'NORWAY AS', 'PAN FISH NORWAY AS', 'SALMAR FINNMARK AS'}),
    'docs/beslutninger/2026-09-03-romming.md': (BESLUTNING, {'Geodata AS', 'LERØY MIDT AS', 'MÅSØVAL AS', 'Måsøval Fiskeoppdrett AS'}),
    'docs/beslutninger/2026-09-15-publiseringsvakten.md': (BESLUTNING, {'NORDLAKS OPPDRETT AS'}),
    'docs/beslutninger/2026-09-16-grensa-gaar-ved-sektor-2300.md': (BESLUTNING, {'NORDLAKS OPPDRETT AS'}),
    'docs/beslutninger/2026-09-16-url-struktur.md': (BESLUTNING, {'928957489'}),
    'docs/design/BRIEF.md': (DESIGN, {'Kun AS'}),
    'docs/design/STILGUIDE.md': (DESIGN, {'Villa Smolt AS'}),
    'docs/design/implementert/2026-09-24/MANIFEST.md': (DESIGN, {'921707134', '964118191', 'MOWI ASA'}),
    'docs/design/implementert/2026-10-08/RAPPORT.md': (DESIGN, {'921668236', 'Mowi Seawater Norway AS'}),
    'docs/design/implementert/README.md': (DESIGN, {'964118191', 'MOWI ASA'}),
    'docs/design/overlevering/Kystloggen - Forsiden v2.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap B AS'}),
    'docs/design/overlevering/Kystloggen - Forsiden.dc.html': (OVERLEVERING, {'LERØY SEAFOOD GROUP ASA', 'MOWI ASA', 'SALMAR ASA'}),
    'docs/design/overlevering/Kystloggen - Lokalitet v2.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap AS'}),
    'docs/design/overlevering/Kystloggen - Lokalitet.dc.html': (OVERLEVERING, {'Mowi ASA', 'Sjøvik Havbruk AS'}),
    'docs/design/overlevering/Kystloggen - Område.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap AS', 'Selskap B AS'}),
    'docs/design/overlevering/Kystloggen - Selskap.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap AS', 'Selskap B AS', 'Selskap C AS', 'Selskap D AS'}),
    'docs/design/overlevering/design_handoff_kystloggen/README.md': (OVERLEVERING, {'B AS', 'Selskap A AS', 'Selskap AS'}),
    'docs/design/overlevering/design_handoff_kystloggen/design/Kystloggen - Forsiden v2.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap B AS'}),
    'docs/design/overlevering/design_handoff_kystloggen/design/Kystloggen - Lokalitet v2.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap AS'}),
    'docs/design/overlevering/design_handoff_kystloggen/design/Kystloggen - Område.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap AS', 'Selskap B AS'}),
    'docs/design/overlevering/design_handoff_kystloggen/design/Kystloggen - Selskap.dc.html': (OVERLEVERING, {'Selskap A AS', 'Selskap AS', 'Selskap B AS', 'Selskap C AS', 'Selskap D AS'}),
}


def mod11(s: str) -> bool:
    v = sum(int(a) * b for a, b in zip(s[:8], (3, 2, 7, 6, 5, 4, 3, 2)))
    k = 11 - v % 11
    return k != 10 and (0 if k == 11 else k) == int(s[8])


def treff(tekst: str) -> set[str]:
    o = {"".join(m.groups()) for m in ORGNR.finditer(tekst)}
    return {x for x in o if mod11(x)} | set(NAVN.findall(tekst))


def _filer() -> list[str]:
    r = subprocess.run(["git", "-C", str(ROT), "ls-files", "-z", *MAPPER],
                       capture_output=True, text=True, check=True)
    return [f for f in r.stdout.split("\0") if f]


def test_ingen_funn_om_navngitte_selskaper_i_det_offentlige_repoet():
    funn, foreldet = [], []
    for f in _filer():
        if any(fnmatchcase(f, g) for g in KILDEBESKRIVELSER):
            continue
        try:
            t = (ROT / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        tillatt = UNNTAK.get(f, (None, set()))[1]
        if ny := treff(t) - tillatt:
            funn.append(f"{f}: {sorted(ny)[:5]}")
        if borte := tillatt - treff(t):
            foreldet.append(f"{f}: {sorted(borte)}")
    assert not funn, ("Orgnr eller AS/ASA-navn i det offentlige repoet. Er det et funn, "
                      "en analyse eller et anslag, hører det i havbruk-analyse (samme sti; "
                      "RUNBOOK, «Offentlig og privat»). Er det en kildebeskrivelse eller et "
                      "eksempel, før det opp i UNNTAK med grunnen:\n  " + "\n  ".join(funn))
    assert not foreldet, "Står i UNNTAK, men ikke lenger i fila:\n  " + "\n  ".join(foreldet)


def test_unntakene_finnes_og_har_grunn():
    filer = set(_filer())
    for f, (grunn, navn) in UNNTAK.items():
        assert f in filer, f
        assert grunn and navn, f


def test_kontrollen_ser_det_den_skal():
    assert treff("eies av MOWI NORWAY AS") == {"MOWI NORWAY AS"}
    assert treff("Lerøy Seafood Group ASA") == {"Lerøy Seafood Group ASA"}
    assert treff("orgnr 921 668 236 og 921668236") == {"921668236"}
    # Feil kontrollsiffer, sha-er, MMSI og beløp er ikke orgnr.
    assert not treff("921668237 a821949917e 257123456 939 080 537")
