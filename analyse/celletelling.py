"""Teller hvilke (runde, PO)-celler `sources/trafikklysvedtak.py` FAKTISK
emitterer, og med hvilken lesemåte.

Kilden er skrevet med fravær framfor gjetning: en forskrift som ikke sier
noe om et produksjonsområde gir ingen rad, og «verken grønn eller rød»
utledes ikke til gul. Følgen er at rutenettet runder x 13 har hull, og
dette steget måler hvor de er.

Steget TELLER. Det tolker ikke, regner ingen prosent og rangerer ingen
runde mot en annen. Hullene har flere mulige forklaringer — forskriften
nevner ikke området, uttrekket når ikke fram, området fikk ikke vedtak —
og å velge mellom dem av en telling ville vært å lese kilden med
konklusjonen i hånd.

## Grunnlaget er ARKIVET, ikke nettet

Kroppene leses av `data/arkiv/trafikklysvedtak/` gjennom
`backfill._arkivert_kropp`, som er den samme veien `--reparse` går. Den
lar kroppen selv si hvilken forskrift den er (`gjenkjenn_kropp`) i stedet
for å stole på filnavnet, og en analyse skal ikke ha sin egen, andre
lesemåte av det spørsmålet.

Uttrekket kjøres gjennom `Trafikklysvedtak.parse()`, ikke ved å kalle
`_uttrekk_*` direkte. `parse()` er der vaktene står — `_krev_runder`,
`_krev_alle_tabellrader`, dublettkontrollen på PO — og et tall som skal
si hva kilden emitterer må komme ut av den samme døra som produksjonen.

## Én celle kan emitteres av FLERE kropper, og de kan lese den ULIKT

`FORSKRIFTER` overlapper med vilje: 2024-kroppen restaterer rundene 2020
og 2022 i § 4-tabellen. Da blir (2020, PO4) emittert tre ganger — én gang
per kropp som nevner den.

Det gir to forskjellige tall, og begge står i rapporten:

    emisjoner          hver (forskrift, runde, PO) for seg
    distinkte celler   hver (runde, PO) én gang, uansett hvor mange
                       kropper som nevner den

Det er det andre tallet oppgaven spør om. Men lesemåten kan sprike
mellom kroppene for den SAMME cellen — 2020-kroppen leser PO4 og PO5 av
en kapitteloverskrift, mens 2022- og 2024-kroppene sier «rødt lys i 2020»
ordrett. En celle med to lesemåter er derfor ikke slått sammen til én
verdi her; den telles for seg og listes opp. Å velge den ene ville vært
et valg, og valget hører hjemme i lesingen.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backfill                                              # noqa: E402
from sources.trafikklysvedtak import (ANTALL_PO,             # noqa: E402
                                      FORSKRIFTER, F_FARGE,
                                      KAPITTELHJEMMEL, LESEMAATE_SUFFIKS,
                                      Trafikklysvedtak, siste_dag)

UT_FIL = Path(__file__).resolve().parent / "fasit" / "celletelling.md"

ALLE_PO = tuple(str(n) for n in range(1, ANTALL_PO + 1))


def emisjoner() -> list[tuple[str, int, str, str, str]]:
    """Kjør kilden over alle arkiverte kropper.

    -> [(forskrift_id, runde, po, farge, lesemåte)], i den rekkefølgen
    `FORSKRIFTER` og `parse()` gir dem.
    """
    kilde = Trafikklysvedtak()
    ut: list[tuple[str, int, str, str, str]] = []

    for forskrift in FORSKRIFTER:
        rå = backfill._arkivert_kropp(kilde, forskrift)
        for runde in forskrift.aar:
            farge: dict[str, str] = {}
            lesemaate: dict[str, str] = {}
            for obs in kilde.parse(rå, siste_dag(runde)):
                if obs.field == F_FARGE:
                    farge[obs.entity_id] = obs.value
                elif obs.field == F_FARGE + LESEMAATE_SUFFIKS:
                    lesemaate[obs.entity_id] = obs.value
            for po in sorted(farge, key=int):
                ut.append((forskrift.forskrift_id, runde, po,
                           farge[po], lesemaate[po]))
    return ut


def main() -> int:
    rader = emisjoner()

    runder = sorted({runde for f in FORSKRIFTER for runde in f.aar})
    maks = len(runder) * ANTALL_PO

    # (runde, po) -> lesemåtene kroppene ga den, i emisjonsrekkefølge
    celler: dict[tuple[int, str], list[str]] = defaultdict(list)
    per_forskrift: dict[tuple[str, int], list[str]] = defaultdict(list)
    for forskrift_id, runde, po, _farge, lesemaate in rader:
        celler[(runde, po)].append(lesemaate)
        per_forskrift[(forskrift_id, runde)].append(po)

    # KAPITTELHJEMMEL vs øvrige, på DISTINKTE celler. En celle med både
    # kapittelhjemmel og en annen lesemåte telles for seg — se docstring.
    bare_hjemmel = sorted(c for c, l in celler.items()
                          if set(l) == {KAPITTELHJEMMEL})
    bare_ovrige = sorted(c for c, l in celler.items()
                         if KAPITTELHJEMMEL not in l)
    blandet = sorted(c for c, l in celler.items()
                     if KAPITTELHJEMMEL in l and set(l) != {KAPITTELHJEMMEL})
    flere_lesemaater = sorted(c for c, l in celler.items() if len(set(l)) > 1)

    linjer: list[str] = [
        "# Celletelling: trafikklysvedtak",
        "",
        "Hvilke (runde, produksjonsområde)-celler `sources/trafikklys"
        "vedtak.py`",
        "faktisk emitterer, kjørt gjennom `parse()` over de arkiverte",
        "forskriftskroppene. Bare tall — ingen tolkning, ingen prosent.",
        "",
        "Generert av `analyse/celletelling.py`.",
        "",
        "## Runder",
        "",
        f"- Forskrifter i `FORSKRIFTER`: **{len(FORSKRIFTER)}**",
        f"- Distinkte runder de uttaler seg om: **{len(runder)}** — "
        f"{', '.join(str(r) for r in runder)}",
        f"- Teoretisk maksimum: {len(runder)} runder x {ANTALL_PO} PO = "
        f"**{maks}** celler",
        "",
        "## Emittert",
        "",
        f"- Emisjoner (forskrift, runde, PO): **{len(rader)}**",
        f"- Distinkte (runde, PO): **{len(celler)}** av {maks}",
        f"- Celler uten emisjon: **{maks - len(celler)}**",
        "",
        "## Hjemmelstype, på distinkte celler",
        "",
        "| lesemåte | celler |",
        "| --- | ---: |",
        f"| bare `{KAPITTELHJEMMEL}` | {len(bare_hjemmel)} |",
        f"| bare øvrige (`ordrett`, `kapitteloverskrift`) | "
        f"{len(bare_ovrige)} |",
        f"| både `{KAPITTELHJEMMEL}` og øvrige | {len(blandet)} |",
        f"| **sum** | **{len(celler)}** |",
        "",
        "## Per runde",
        "",
        f"| runde | emittert av {ANTALL_PO} | PO uten emisjon |",
        "| --- | ---: | --- |",
    ]

    for runde in runder:
        har = {po for (r, po) in celler if r == runde}
        mangler = [po for po in ALLE_PO if po not in har]
        linjer.append(
            f"| {runde} | {len(har)} | "
            f"{', '.join('PO' + po for po in mangler) if mangler else '—'} |")

    linjer += [
        "",
        "## Per forskrift (grunnlaget for unionen over)",
        "",
        "| forskrift | runde | PO emittert | antall |",
        "| --- | ---: | --- | ---: |",
    ]
    for forskrift in FORSKRIFTER:
        for runde in forskrift.aar:
            po = per_forskrift[(forskrift.forskrift_id, runde)]
            linjer.append(
                f"| {forskrift.forskrift_id} | {runde} | "
                f"{', '.join('PO' + p for p in po)} | {len(po)} |")

    linjer += ["", "## Celler med mer enn én lesemåte", ""]
    if not flere_lesemaater:
        linjer.append("Ingen.")
    else:
        linjer += ["| runde | PO | lesemåter, i emisjonsrekkefølge |",
                   "| --- | --- | --- |"]
        for runde, po in flere_lesemaater:
            linjer.append(f"| {runde} | PO{po} | "
                          f"{', '.join(celler[(runde, po)])} |")
    linjer.append("")

    UT_FIL.parent.mkdir(parents=True, exist_ok=True)
    UT_FIL.write_text("\n".join(linjer) + "\n", encoding="utf-8")

    print(f"\nforskrifter i FORSKRIFTER : {len(FORSKRIFTER)}")
    print(f"distinkte runder          : {len(runder)} "
          f"({', '.join(str(r) for r in runder)})")
    print(f"teoretisk maksimum        : {len(runder)} x {ANTALL_PO} = {maks}")
    print(f"emisjoner                 : {len(rader)}")
    print(f"distinkte (runde, PO)     : {len(celler)}")
    print(f"uten emisjon              : {maks - len(celler)}")
    print(f"\nbare {KAPITTELHJEMMEL:<18}: {len(bare_hjemmel)}")
    print(f"bare øvrige               : {len(bare_ovrige)}")
    print(f"både og                   : {len(blandet)}")
    print(f"\n{'runde':<8}{'av ' + str(ANTALL_PO):>7}   mangler")
    print("-" * 50)
    for runde in runder:
        har = {po for (r, po) in celler if r == runde}
        mangler = [po for po in ALLE_PO if po not in har]
        print(f"{runde:<8}{len(har):>7}   "
              f"{', '.join('PO' + po for po in mangler) if mangler else '—'}")
    print(f"\nSkrevet: {UT_FIL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
