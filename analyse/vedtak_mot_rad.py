"""Ekspertgruppens RÅD mot departementets VEDTAK, per (produksjonsområde,
tildelingsrunde).

    python analyse/vedtak_mot_rad.py

## Analysen stopper før treffraten, og det er resultatet

Bestillingen var å telle celler der råd og vedtak stemmer, celler der de
avviker, og retningen på avviket. Den tellingen krever en OVERSETTELSE
mellom to skalaer:

    ekspertgruppen   lav / moderat / høy   lakselusindusert
                                           villfiskdødelighet
    forskriften      grønn / gul / rød     kapasitetskonsekvens

Forutsetningen for oppdraget var at oversettelsen står i regelverket.
Den gjør den ikke. Målt 05.09.2026 på både den opprinnelig kunngjorte og
den gjeldende teksten av produksjonsområdeforskriften (FOR-2017-01-16-61):
ordene «dødelighet», «grønn», «rød», «trafikklys», «risiko» og
«ekspertgruppe» forekommer NULL ganger, og det finnes ingen
prosentterskler i forskriften.

Hele kjeden, med kilde for hvert ledd, står i
`analyse/FORBEHOLD-vedtak-mot-rad.md`. Kort:

  * FARGE -> MILJØSTATUS -> KONSEKVENS er definert. Produksjons-
    områdeforskriften §§ 8–11 kobler akseptabel/moderat/uakseptabel til
    vekst/uendret/nedjustering, og departementets høringsnotat 19.06.2026
    navngir fargene: «Er miljøpåvirkningen akseptabel (grønn) …
    moderat (gul) … uakseptabel (rød) …».

  * RISIKONIVÅ -> MILJØSTATUS er IKKE definert. § 8 annet ledd sier bare
    at «Departementet vurderer». Det nærmeste er trafikklysmeldingen
    (Meld. St. 16 (2014–2015)) kap. 8.3, som er en stortingsmelding, som
    sier «forutsigbart» uten å navngi hvilken farge som følger av hvilken
    kategori, og som uttrykkelig åpner for en helhetsvurdering med
    samfunnsøkonomiske hensyn.

  * Og vedtaket hviler på TO vurderingsår, ikke ett. Runde 2026 bygger på
    ekspertgruppens rapporter for 2024 og 2025; runde 2024 på 2022 og
    2023. En celle (PO, runde) har derfor to råd.

Derfor rapporterer dette skriptet DEKNING og SAMFOREKOMST, og beregner
INGEN treffrate og INGEN avviksretning. Å oppgi «X av Y stemmer» ville
vært å oppgi et tall om en oversettelse vi selv fant på — prosjektets
egen feilklasse (CLAUDE.md 1b-2), og denne gangen med en tredjepart som
gjenstand.

## Gjeldende verdi per celle er sist utgitte rad SOM FINNES

Begge kildene skriver flere versjoner av samme dato, og en nyere kropp
som ikke nevner en celle har ikke trukket den tilbake. Se
`analyse/ekspertgruppen_celler.les()` for feltvarianten av regelen og
`sources/trafikklysvedtak` sin docstring for entitetsvarianten.

Begge lesinger går gjennom `kjoringslogg.Kjoringslogg.les()` med
`versjonsvalg=ALLE`, og loggen fører hver fil som ble lest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analyse import kjoringslogg                          # noqa: E402
from sources.ekspertgruppen import F_KATEGORI             # noqa: E402
from sources.trafikklysvedtak import (F_FARGE,            # noqa: E402
                                      LESEMAATE_SUFFIKS,
                                      ANTALL_PO, GRONN, GUL, ROD)

UT = ROOT / "analyse" / "ut"
LOGG = UT / "vedtak_mot_rad.kjoring.log"
RAPPORT = UT / "vedtak-mot-rad.txt"

KILDE_RAD = "ekspertgruppen"
KILDE_VEDTAK = "trafikklysvedtak"

# Tildelingsrundene trafikklyset er fargelagt i. 2026 står med fordi
# FRAVÆRET av en fastsatt forskrift er en del av dekningsregnskapet — en
# runde som ikke telles i nevneren er en runde ingen ser mangler.
RUNDER = (2018, 2020, 2022, 2024, 2026)

# Hvilke vurderingsår hver runde bygger på. LEST av departementets egne
# dokumenter, ikke utledet av at rundene er toårige:
#
#   runde 2026  «ekspertgruppens rapporter og styringsgruppens vurderinger
#               fra årene 2024 og 2025» — høringsnotat 19.06.2026, kap. 2
#   runde 2024  ekspertgruppens rapporter for 2022 og 2023 — høringen til
#               kapasitetsjusteringsforskriften 2024 (regjeringen.no,
#               id3023357), der 2023-rapporten ble offentliggjort samme dag
#
# De tre eldste er IKKE bekreftet mot et departementsdokument vi har lest,
# og står derfor som `None`. Mønsteret (runde Y bygger på Y-2 og Y-1)
# stemmer med rapportenes egne årsintervaller, men et mønster som passer
# er ikke en lest kilde — CLAUDE.md regel 4.
GRUNNLAGSAAR: dict[int, tuple[int, ...] | None] = {
    2018: None,
    2020: None,
    2022: None,
    2024: (2022, 2023),
    2026: (2024, 2025),
}

# Kolonnerekkefølgen i samforekomsttabellen. Ordinal, fra minst til
# mest inngripende — ikke fordi rekkefølgen betyr noe for tallene,
# men fordi en tabell som skifter kolonneorden mellom kjøringer er
# vanskelig å sammenligne med forrige kjøring.
FARGER = (GRONN, GUL, ROD)


# ----------------------------------------------------------------- lesing

def _sist_utgitt(logg: kjoringslogg.Kjoringslogg, kilde: str, felt: str,
                 ) -> dict[tuple[int, str], dict]:
    """Sist utgitte rad SOM FINNES per (år, entity_id) for ett felt.

    Ikke «siste snapshot». Forskjellen er hele poenget: 2022-forskriften
    uttaler seg om runde 2020, men bare om tre av områdene, og et oppslag
    på siste snapshot ville gitt tre farger der det finnes tolv.

    Samme regel som `analyse/ekspertgruppen_celler.les()` bruker for
    felter. Her gjelder den entiteter, fordi det er entiteter som faller
    ut mellom to versjoner hos denne kilden.
    """
    ut: dict[tuple[int, str], dict] = {}
    for _, ramme in logg.les(kilde, "2000-01-01", "2099-12-31",
                             versjonsvalg=kjoringslogg.ALLE):
        for rad in ramme.filter(pl.col("field") == felt).iter_rows(named=True):
            nokkel = (int(rad["observed_at"][:4]), rad["entity_id"])
            forrige = ut.get(nokkel)
            # `published_at` er tom for gamle snapshots; da faller
            # rekkefølgen tilbake på hentetidspunktet, som er den øvre
            # grensen for utgivelsen (CLAUDE.md 1b-7 punkt 3).
            naa = rad["published_at"] or rad["fetched_at"]
            før = (forrige["published_at"] or forrige["fetched_at"]
                   ) if forrige else ""
            if forrige is None or naa >= før:
                ut[nokkel] = rad
    return ut


def les_vedtak(logg: kjoringslogg.Kjoringslogg,
               ) -> tuple[dict, dict]:
    """(farge, lesemåte) per (runde, po)."""
    return (_sist_utgitt(logg, KILDE_VEDTAK, F_FARGE),
            _sist_utgitt(logg, KILDE_VEDTAK, F_FARGE + LESEMAATE_SUFFIKS))


def les_rad(logg: kjoringslogg.Kjoringslogg) -> dict:
    """Kategori per (vurderingsår, po)."""
    return _sist_utgitt(logg, KILDE_RAD, F_KATEGORI)


# ------------------------------------------------------------ rapportering

def _linjer(vedtak: dict, lesemaate: dict, rad: dict) -> list[str]:
    L: list[str] = []
    ut = L.append

    ut("=" * 72)
    ut("RÅD MOT VEDTAK — dekning og samforekomst")
    ut("=" * 72)
    ut("")
    ut("Analysen beregner INGEN treffrate og INGEN avviksretning.")
    ut("Koblingen mellom ekspertgruppens RISIKONIVÅ og forskriftens FARGE")
    ut("er ikke definert i produksjonsområdeforskriften eller i noe annet")
    ut("regelverk vi har lest. Se modulens docstring og")
    ut("analyse/FORBEHOLD-vedtak-mot-rad.md.")
    ut("")

    # ---- 1. vedtakssiden ------------------------------------------------
    ut("-" * 72)
    ut("1. VEDTAK: farge per (produksjonsområde, tildelingsrunde)")
    ut("-" * 72)
    ut("")
    ut("     " + "".join(f"{r:>10}" for r in RUNDER))
    for po in range(1, ANTALL_PO + 1):
        rad_ut = f"PO{po:>2} "
        for runde in RUNDER:
            f = vedtak.get((runde, str(po)))
            if f is None:
                rad_ut += f"{'—':>10}"
            else:
                merke = {"ordrett": "", "kapitteloverskrift": "*",
                         "kapittelhjemmel": "**"}.get(
                    (lesemaate.get((runde, str(po))) or {}).get("value", ""), "?")
                rad_ut += f"{f['value'] + merke:>10}"
        ut(rad_ut)
    ut("")
    ut("  (uten merke) ordrett — fargeordet står i samme setning eller")
    ut("               tabellrad som områdenummeret")
    ut("  *            kapitteloverskrift — fargeordet står i overskriften")
    ut("               til kapittelet § 3 plasserer området i")
    ut("  **           kapittelhjemmel — UTLEDET: området står under")
    ut("               kapittelet som gjennomfører produksjonsområde-")
    ut("               forskriften § 11 (akseptabel miljøpåvirkning), og")
    ut("               kroppen inneholder ingen fargeord")
    ut("  —            forskriften sier ingenting om området i den runden")
    ut("")

    dekket = sum(1 for r in RUNDER for po in range(1, ANTALL_PO + 1)
                 if (r, str(po)) in vedtak)
    mulige = len(RUNDER) * ANTALL_PO
    ut(f"  Celler med vedtak:   {dekket:>3} av {mulige}")
    for lm, tekst in (("ordrett", "ordrett"),
                      ("kapitteloverskrift", "kapitteloverskrift"),
                      ("kapittelhjemmel", "kapittelhjemmel (UTLEDET)")):
        n = sum(1 for v in lesemaate.values() if v["value"] == lm)
        ut(f"    herav {tekst:<28} {n:>3}")
    ut("")
    ut("  `kapitteloverskrift` teller null her selv om 2020-forskriften")
    ut("  leser PO4 og PO5 slik. Grunnen er lesereglen over: begge cellene")
    ut("  restateres ORDRETT av 2022- og 2024-forskriften («rødt lys i")
    ut("  2020»), og den sist utgitte lesemåten er den som står. Det er")
    ut("  ikke tapt informasjon — begge snapshots ligger, og oppgraderingen")
    ut("  står som to revisjonsrader i changeloggen.")
    ut("")

    # ---- 2. hullene -----------------------------------------------------
    ut("-" * 72)
    ut("2. CELLER UTEN VEDTAK, med grunn")
    ut("-" * 72)
    ut("")
    for runde in RUNDER:
        mangler = [po for po in range(1, ANTALL_PO + 1)
                   if (runde, str(po)) not in vedtak]
        if not mangler:
            ut(f"  runde {runde}: ingen hull")
            continue
        ut(f"  runde {runde}: PO "
           + ", ".join(str(p) for p in mangler)
           + f"  ({len(mangler)} av {ANTALL_PO})")
    ut("")
    ut("  Grunnene, per runde:")
    ut("")
    ut("  2018  FOR-2017-12-20-2397 har intet kapittel om nedjustering og")
    ut("        inneholder ikke ett eneste fargeord. Fem områder er unevnt,")
    ut("        og et rødt område ser i det dokumentet nøyaktig ut som et")
    ut("        gult. Fargen kan ikke leses.")
    ut("  2020  PO10 er unevnt i FOR-2020-02-04-105 og restateres ikke av")
    ut("        noen senere forskrift. PO3 mangler i 2020-kroppen, men")
    ut("        hentes ordrett fra 2022-kroppens § 4-tabell.")
    ut("  2022  PO2 og PO7 står verken i den grønne lista eller i")
    ut("  2024  PO2, PO6, PO7 og PO8 likeså. «Verken grønn eller rød» peker")
    ut("        mot gul, men slutningen krever at forskriften er uttømmende")
    ut("        om farge, og 2018-kroppen viser at den ikke trenger å være")
    ut("        det. Utelukkelse emitteres derfor ikke.")
    ut("  2026  INGEN FASTSATT FORSKRIFT. Departementet kunngjorde")
    ut("        fargeleggingen i en pressemelding og sendte utkast til")
    ut("        forskrift på høring 19.06.2026 med frist 31.07.2026. Målt")
    ut("        05.09.2026 mot Norsk Lovtidend avdeling I finnes ingen")
    ut("        kapasitetsjusteringsforskrift for 2026. Det finnes altså")
    ut("        ikke noe vedtak å lese ennå.")
    ut("")

    # ---- 3. rådssiden ---------------------------------------------------
    ut("-" * 72)
    ut("3. RÅD: ekspertgruppens kategori per (produksjonsområde, år)")
    ut("-" * 72)
    ut("")
    aar = sorted({a for a, _ in rad})
    ut(f"  Vurderingsår med minst én kategori: {len(aar)} "
       f"({aar[0]}–{aar[-1]})" if aar else "  ingen")
    ut(f"  Celler i alt: {len(rad)}")
    ut("")

    # ---- 4. sammenstillingen --------------------------------------------
    ut("-" * 72)
    ut("4. SAMMENSTILLING")
    ut("-" * 72)
    ut("")
    ut("  Et vedtak i runde Y hviler på ekspertgruppens vurderinger for TO")
    ut("  år, ikke ett. Grunnlagsårene er bare LEST for de to nyeste")
    ut("  rundene; for de tre eldste er de ubekreftet og telles ikke.")
    ut("")

    sammenlignbare = 0
    tokolonne: dict[tuple[str, str], int] = {}
    uten_grunnlag = 0
    uten_rad = 0

    for runde in RUNDER:
        grunnlag = GRUNNLAGSAAR[runde]
        for po in range(1, ANTALL_PO + 1):
            v = vedtak.get((runde, str(po)))
            if v is None:
                continue
            if grunnlag is None:
                uten_grunnlag += 1
                continue
            kategorier = [rad[(a, str(po))]["value"]
                          for a in grunnlag if (a, str(po)) in rad]
            if not kategorier:
                uten_rad += 1
                continue
            sammenlignbare += 1
            # Sammenfallende råd begge år, eller ikke. Trafikklysmeldingen
            # kap. 8.3 skiller nettopp på det, og det er det eneste
            # skillet et dokument faktisk gjør.
            merke = (kategorier[0] if len(set(kategorier)) == 1
                     else "sprik:" + "/".join(kategorier))
            tokolonne[(merke, v["value"])] = \
                tokolonne.get((merke, v["value"]), 0) + 1

    ut(f"  Celler der BEGGE sider finnes og grunnlagsårene er lest:"
       f" {sammenlignbare:>3}")
    ut(f"  Celler med vedtak, men uten LEST grunnlagsår:            "
       f" {uten_grunnlag:>3}")
    ut(f"  Celler med vedtak og lest grunnlagsår, men uten råd:     "
       f" {uten_rad:>3}")
    ut(f"  Celler uten vedtak:                                     "
       f" {mulige - dekket:>3}")
    ut("")
    ut("  ANTALL DER RÅD OG VEDTAK «STEMMER»:  kan ikke beregnes.")
    ut("  ANTALL AVVIK, MED RETNING:           kan ikke beregnes.")
    ut("")
    ut("  Begge krever en ordinal oversettelse mellom risikonivå og farge.")
    ut("  Ingen slik oversettelse er definert i produksjonsområde-")
    ut("  forskriften, i kapasitetsjusteringsforskriftene eller i noe annet")
    ut("  regelverk vi har lest. Trafikklysmeldingen kap. 8.3 sier at")
    ut("  utfallet er «forutsigbart» når de to årene er sammenfallende, men")
    ut("  navngir ikke hvilken farge som følger av hvilken kategori, og")
    ut("  åpner uttrykkelig for en helhetsvurdering med samfunnsøkonomiske")
    ut("  hensyn. Se analyse/FORBEHOLD-vedtak-mot-rad.md.")
    ut("")

    if tokolonne:
        ut("  SAMFOREKOMST (beskrivende, IKKE et treffmål):")
        ut("")
        ut(f"    {'råd (begge grunnlagsår)':<28}" + "".join(f"{f:>8}" for f in FARGER))
        merker = sorted({m for m, _ in tokolonne})
        for m in merker:
            ut(f"    {m:<28}"
               + "".join(f"{tokolonne.get((m, f), 0):>8}" for f in FARGER))
        ut("")
        ut("    Tabellen sier hvor ofte en kategori og en farge OPPTRER")
        ut("    SAMMEN. Den sier ikke at diagonalen er «riktig»: hvilken")
        ut("    celle som skulle vært diagonalen er nettopp det som ikke er")
        ut("    definert. Et sammenfall er heller ikke årsak — se")
        ut("    forbeholdsfila.")
        ut("")

    return L


def main() -> int:
    UT.mkdir(parents=True, exist_ok=True)
    logg = kjoringslogg.Kjoringslogg("vedtak_mot_rad", LOGG)
    logg.valg("spoersmaal",
              "stemmer departementets farge med ekspertgruppens kategori "
              "per (produksjonsområde, tildelingsrunde)?")
    logg.valg("stoppregel",
              "koblingen risikonivå -> farge skal være definert i "
              "regelverket; er den ikke det, rapporteres funnet og "
              "treffraten beregnes IKKE")
    logg.valg("stoppregel.utfall", "IKKE DEFINERT — analysen stopper")
    logg.valg("stoppregel.maalt_paa",
              "FOR-2017-01-16-61, både LTI (opprinnelig kunngjort) og SF "
              "(gjeldende), 05.09.2026")
    logg.valg("stoppregel.funn",
              "«dødelighet», «grønn», «rød», «trafikklys», «risiko» og "
              "«ekspertgruppe» forekommer 0 ganger; ingen prosentterskler")
    logg.valg("lesing.versjoner",
              "ALLE, slått sammen per (år, po) på seneste published_at — "
              "en kropp som ikke gjentar en celle har ikke trukket den "
              "tilbake")
    logg.valg("grunnlagsaar.lest_for", "2024, 2026")
    logg.valg("grunnlagsaar.ubekreftet_for", "2018, 2020, 2022")
    logg.valg("beregner_treffrate", False)
    logg.valg("beregner_avviksretning", False)
    logg.valg("forbehold", "analyse/FORBEHOLD-vedtak-mot-rad.md")

    vedtak, lesemaate = les_vedtak(logg)
    rad = les_rad(logg)

    if not vedtak:
        print("Ingen snapshots for trafikklysvedtak. Kjør\n"
              "    python backfill.py --kilde trafikklysvedtak --rapporter")
        return 1
    if not rad:
        print("Ingen snapshots for ekspertgruppen. Kjør\n"
              "    python backfill.py --kilde ekspertgruppen --rapporter")
        return 1

    linjer = _linjer(vedtak, lesemaate, rad)
    tekst = "\n".join(linjer)
    print(tekst)

    RAPPORT.write_text(tekst + "\n" + logg.peker_fra(UT) + "\n",
                       encoding="utf-8")
    logg.fil("rapport", RAPPORT)
    logg.skriv()
    print(f"\nSkrevet {RAPPORT}")
    print(f"Kjøringslogg {LOGG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
