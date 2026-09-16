"""Hvilke (entity_id, field)-par en kropp UTTALER SEG OM.

`utvalg` sier hva vi BA OM. Dette sier hva kilden SVARTE OM. De er ikke
det samme, og forskjellen er det eneste som skiller to setninger som ser
identiske ut i et snapshot:

    kilden sa ingenting om PO9          -> taushet
    kilden sa at PO9 ikke har en verdi  -> fjerning

Fram til 15.09.2026 kunne `diff` ikke skille dem. Begge ble en rad med
`new_value = null`, og den raden leses som en tilbaketrekking. Målt over
hele changeloggen: 36 av 1873 revisjonsrader (1,9 %) — men 34 av
trafikklysvedtaks 38, og hver eneste én usann. Ingen forskrift har
noensinne trukket tilbake en farge; § 4-tabellen har bare tre rader.
Se docs/beslutninger/2026-09-15-taushet-er-ikke-tilbaketrekking.md.

## Fire tilstander, ikke tre

`utvalg` har tre. Denne har fire, fordi «uttømmende» og «ukjent» oppfører
seg likt men betyr forskjellige ting, og fordi et domene kan være større
enn det som faktisk kom ut:

    på disk   betyr                                  fravær av en verdi er
    -------   ------------------------------------   ---------------------
    ""        ukjent — kilden sa ingenting           FJERNING (som før)
    "*"       uttømmende — kroppen dekker alt        FJERNING
    "{}"      domenet er nøyaktig det som ble emittert   TAUSHET
    [[e,f]…]  domenet er det emitterte PLUSS disse   TAUSHET, unntatt disse

Standarden er `""` og ikke `"*"`. Sto det siste der, ville hver kilde som
aldri har tenkt på spørsmålet automatisk PÅSTÅTT at kroppen dekker alt —
og påstanden ville vært usann i nøyaktig det tilfellet feltet finnes for.
Samme skille som `utvalg` gjør mellom «vet ikke» og «vet»: tom streng er
ikke en verdi, den er fraværet av en.

At `""` og `"*"` gir samme oppførsel er med vilje. Feltet ble innført
etter at 1873 revisjonsrader alt var skrevet, og et gammelt snapshot skal
lese som det gjorde i går — ikke få en ny betydning fordi vi la til en
kolonne. `"*"` finnes likevel, fordi en kilde som HAR tenkt på spørsmålet
og svart «jeg dekker alt» sier noe en tom streng ikke sier.

## Hvorfor bare DIFFERANSEN lagres

Snapshotet bærer allerede hvilke par som kom ut. Det eneste det ikke kan
svare på, er hvilke par kroppen uttalte seg om UTEN å gi en verdi — og
det er nettopp de parene som skiller taushet fra fjerning.

Å lagre hele domenet på hver rad ble målt og forkastet 15.09.2026:
ekspertgruppens største snapshot (490 rader, 13 entiteter, 60 felter) har
490 par, og en full parliste på hver rad tar fila fra 6 914 til 166 505
byte — **24 ganger**. Differansen tar den til 7 202 byte, 1,04 ganger.

Det er ikke en optimalisering. Et repo som vokser 24x per snapshot er et
repo ingen kjører ukentlig, og CLAUDE.md regel 2 finnes fordi filstørrelse
i git er en reell grense.

## Domenet ERKLÆRES, det utledes ikke

`serialiser()` krever at det erklærte domenet inneholder hvert par som
faktisk ble emittert, og kaster ellers. Den kontrollen er hele poenget
med at feltet finnes.

For hver kilde i repoet i dag er domenet nøyaktig lik emisjonene, så et
uttrekk som bare returnerte «det jeg emitterte» ville bestått hver eneste
test. Det er formen CLAUDE.md 1b-2 navngir: en mekanisme som er riktig i
akkurat de tilfellene der to ting faller sammen, og stille når de slutter.
Den dagen en forskrift skriver «Produksjonsområde 9: ingen justering»,
uttaler kroppen seg om PO9 uten å gi en farge — og et utledet domene ville
kalt det taushet og undertrykt en ekte fjerning.

Se `test_erklaert_domene_vinner_over_emisjonene` i tests/test_domene.py.
"""

from __future__ import annotations

import json

# Kroppen dekker hele nøkkelrommet sitt: er et par borte, er det fjernet.
# En sentinel og ikke `None`, fordi `None` alt betyr «vet ikke» — og de to
# er de samme to som `utvalg` holder fra hverandre med `er_ukjent()`.
UTTOMMENDE = "*"

Par = tuple[str, str]


def er_ukjent(domene: object) -> bool:
    """Sa kilden ingenting om hva kroppen uttaler seg om?

    Finnes som funksjon og ikke som `if not domene:` av samme grunn som
    `utvalg.er_ukjent()`: `None` og et tomt sett er begge usanne i Python
    og betyr motsatte ting. `None` er fraværet av en påstand, et tomt sett
    er påstanden «denne kroppen uttalte seg om ingenting».
    """
    return domene is None


def er_uttommende(domene: object) -> bool:
    """Sa kilden uttrykkelig at kroppen dekker hele nøkkelrommet?"""
    return domene == UTTOMMENDE


def normaliser(par: object) -> list[list[str]]:
    """Et sett med par til kanonisk form: sorterte, unike tostrengslister.

    Kanonisk betyr at to like domener alltid serialiserer likt. Uten det
    ville rekkefølgen et uttrekk tilfeldigvis bygget settet i gitt en ny
    kolonneverdi — og dermed en ny parquet-fil i git — uten at noe faktisk
    var endret. Samme grunn som `utvalg.normaliser()` og `maintain_order`
    i `snapshot.to_frame()`.
    """
    if not par:
        return []
    ut: set[tuple[str, str]] = set()
    for p in par:
        if isinstance(p, (str, bytes)) or len(tuple(p)) != 2:
            raise ValueError(
                f"domene inneholder {p!r}, som ikke er et "
                f"(entity_id, field)-par. Granulariteten er PAR og ikke "
                f"entitet: ekspertgruppen tier om ETT felt for PO6 mens "
                f"den svarer for de andre, og et domene på entitetsnivå "
                f"ville latt de to radene stå usanne."
            )
        e, f = tuple(p)
        ut.add((str(e), str(f)))
    return [[e, f] for e, f in sorted(ut)]


def serialiser(domene: object, emittert: object) -> str:
    """Kanonisk JSON for raden. `emittert` er parene som faktisk kom ut.

    Lagrer BARE differansen — parene kroppen uttalte seg om uten å gi en
    verdi. Se modulens docstring for hvorfor, og for målingen som
    forkastet alternativet.

    KASTER hvis kilden emitterte et par den ikke erklærte. Det er ikke en
    formalitet: uten den kontrollen kan et uttrekk erklære et tomt domene
    og likevel levere rader, og da ville `diff` lest hver eneste av dem
    som taushet. Erklæringen skal dekke det som faktisk ble sagt.
    """
    if er_ukjent(domene):
        return ""
    if er_uttommende(domene):
        return UTTOMMENDE

    erklart = {(e, f) for e, f in normaliser(domene)}
    emit = {(str(e), str(f)) for e, f in emittert}

    udekket = sorted(emit - erklart)
    if udekket:
        raise ValueError(
            f"{len(udekket)} par ble emittert uten å stå i det erklærte "
            f"domenet, f.eks. {udekket[:3]}. Domenet skal si hva kroppen "
            f"UTTALER SEG OM, og en verdi som kom ut er per definisjon "
            f"uttalt. Enten mangler uttrekkets erklæring noe, eller så "
            f"emitterer parse() noe uttrekket ikke vet om — begge deler "
            f"skal rettes mot kroppen, ikke rundes av."
        )

    delta = normaliser(erklart - emit)
    if not delta:
        return "{}"
    return json.dumps(delta, ensure_ascii=False, separators=(",", ":"))


def les(tekst: str | None) -> object:
    """Tilbake fra disk. `None` = ukjent, `UTTOMMENDE`, eller en parliste.

    Ulesbar tekst gir `None` og ikke en exception. Samme grunn som i
    `utvalg.les()` og `health.dager_siden_ok()`: dette er inndata fra en
    fil på disk som kan være skrevet av en eldre versjon, og en leser som
    kaster på en gammel fil gjør historikken uleselig i stedet for uskarp.
    """
    if not tekst:
        return None
    if tekst == UTTOMMENDE:
        return UTTOMMENDE
    try:
        d = json.loads(tekst)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(d, dict) and not d:
        return []          # "{}" — domenet er nøyaktig det emitterte
    if not isinstance(d, list):
        return None
    try:
        return normaliser(d)
    except ValueError:
        return None


def uttaler_seg_om(tekst: str | None, emittert: object, par: Par) -> bool:
    """Uttalte denne kroppen seg om dette paret?

    Spørsmålet `diff` stiller før den skriver en rad om at noe forsvant.
    Svarer den nei, er fraværet TAUSHET og raden skal ikke skrives.

    `emittert` er parene i kroppens eget snapshot. Fallbacken for ukjent
    domene er **sant** — altså dagens oppførsel — og den går den veien
    med vilje. 1873 revisjonsrader er alt skrevet uten feltet, og en
    fallback som sa «nei» ville stilltiende undertrykt dem alle, inkludert
    biomasses 1809 ekte. Der `utvalg.er_utvidet()` faller mot «ikke
    undertrykk», faller denne samme vei og av samme grunn: en undertrykt
    rad er en hendelse ingen får se.
    """
    d = les(tekst)
    if d is None or d == UTTOMMENDE:
        return True
    e, f = str(par[0]), str(par[1])
    if (e, f) in {(str(a), str(b)) for a, b in emittert}:
        return True
    return [e, f] in d


def par_i(frame) -> set[Par]:
    """(entity_id, field)-parene en ramme faktisk inneholder.

    Ligger her og ikke hos hver kaller fordi `diff`, `runner` og
    lesefunksjonen i `changelog` trenger nøyaktig det samme settet, og tre
    utregninger av samme sak er formen F6 og F7 hadde.
    """
    if frame.is_empty() or not {"entity_id", "field"} <= set(frame.columns):
        return set()
    return {(str(e), str(f))
            for e, f in frame.select(["entity_id", "field"]).iter_rows()}
