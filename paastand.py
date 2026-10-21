"""Påstandsmodellen: ÉN form for alt lokalitetssiden påstår.

## Vi går ikke god for fisken

Siden sier aldri at det står fisk i merdene. Den sier at en KILDE sa det,
om et TIDSPUNKT. Fram til 20.10.2026 sto «Fisk til stede» øverst på
Hendneset (10204) fordi biomasselaget sa «Ja» — i en månedsrapport fra
desember 2025, ti måneder før siden ble bygget. Stripa under talte «7 av
7 observerte uker med fisk», og alle sju var den samme rapporten sett på
nytt. Det er F4 og F6 i en ny drakt: et tidspunkt som handler om OSS
(uka vi hentet) brukt som om det handlet om VERDEN (måneden rapporten
gjelder).

## Fire ledd, og hvorfor akkurat de

    kilde    hvem som sier det: kildenavnet i data/raw/
    gjelder  når påstanden GJELDER, ikke når vi hentet den (CLAUDE.md 1b-7)
    verdi    det kilden sa, uoversatt
    nivaa    hva slags påstand det er, se under

`tema` sier hva den handler om («fisk», «brakklagt»), og er det to
påstander sammenlignes på. `felt` er kildens feltnavn, til `data-felt`.

## Nivåene

    oppgitt     kilden oppgir verdien selv: et registerfelt, en
                innrapportert månedsrapport, et lusetall
    regnet      vi har regnet den av oppgitte verdier, og regnestykket kan
                gjøres om av hvem som helst: summen av tillatelsenes MTB
    vurdert     kildens EGEN slutning, ikke en innrapportering:
                BarentsWatchs «Trolig uten fisk» (`isFallow`), se
                docs/MALING-FUNN-OKTOBER.md F4.2
    indikasjon  VÅR slutning, som «trolig slakting». Nivået finnes bare for
                å kunne nektes: `vis()` kaster, og porten feller en side
                som bærer det. Det går aldri på nettstedet.

## Alder

En påstand eldre enn kildens grense vises som «ukjent», med datoen for
siste rapport — aldri som «Ja». Grensa er to rapporteringsperioder, målt
per kilde og satt i config.yml (`nettsted.aldersgrense`). Alderen regnes
fra sidens REFERANSEDATO, som er datoen til de nyeste dataene siden er
bygget av, ikke klokka: samme side bygget to dager senere skal si det
samme (CLAUDE.md 1b, og `endringsvindu()` i nettsted.py gjør det samme).

Et etterslep VI har valgt trekkes fra før grensa prøves. Lusetall hentes
fire uker på etterskudd med vilje (`kilder.lusetall.uker_etterslep`), og
uten fradraget ville hver lusepåstand vært utgått den dagen den ble
hentet. Etterslepet står ett sted, i kildens egen konfigurasjon.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

import visningsord

OPPGITT = "oppgitt"
REGNET = "regnet"
VURDERT = "vurdert"
INDIKASJON = "indikasjon"
NIVAAER = (OPPGITT, REGNET, VURDERT, INDIKASJON)

# HVOR LANG TID `gjelder` DEKKER. En lusetallsuke er mandag til søndag,
# og datoen er mandagen (docs/KILDE-LUSETALL.md). En månedsrapport i
# biomasselaget er datert til månedens siste dag og gjelder den dagen —
# beholdningen ved månedsslutt, slik oppdraget 20.10.2026 leser den. Et
# registerfelt gjelder dagen vi så det.
DAG = "dag"
UKE = "uke"
PERIODER = (DAG, UKE)

class Indikasjon(ValueError):
    """En påstand på nivået `indikasjon` ble bedt vist."""


class UkjentAldersgrense(KeyError):
    """Kilden har ingen aldersgrense i config.yml, og alderen kan ikke prøves."""


@dataclass(frozen=True)
class Paastand:
    tema: str
    kilde: str
    gjelder: str
    verdi: str
    nivaa: str = OPPGITT
    felt: str = ""
    periode: str = DAG
    def __post_init__(self):
        if self.nivaa not in NIVAAER:
            raise ValueError(f"ukjent nivå {self.nivaa!r}")
        if self.periode not in PERIODER:
            raise ValueError(f"ukjent periode {self.periode!r}")
        if not self.kilde:
            raise ValueError("en påstand uten kilde er ikke en påstand")
        _dato(self.gjelder)            # kaster på noe som ikke er en dato


def _dato(iso: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(str(iso)[:10])
    except ValueError:
        raise ValueError(f"gjelder er ikke en ISO-dato: {iso!r}") from None


# ------------------------------------------------------------------ alder


def aldersgrense(kilde: str) -> int | None:
    """Dager en påstand fra kilden står seg. None: den foreldes ikke.

    Fra config.yml, `nettsted.aldersgrense.<kilde>`. En kilde som ikke
    står der KASTER: en påstand vi ikke kan aldersprøve, kan vi heller
    ikke vise som gjeldende, og en standardverdi her ville vært et gjett
    om en rytme ingen har målt.
    """
    from core import config

    grenser = config.get("nettsted.aldersgrense", {}) or {}
    if kilde not in grenser:
        raise UkjentAldersgrense(
            f"{kilde} har ingen aldersgrense i config.yml "
            f"(nettsted.aldersgrense). Mål rytmen og sett den der.")
    verdi = grenser[kilde]
    return None if verdi is None else int(verdi["dager"])


def etterslep(kilde: str) -> int:
    """Dager vi henter på etterskudd MED VILJE. Bare lusetall har det i dag."""
    from core import config

    uker = config.get(f"kilder.{kilde}.uker_etterslep")
    return int(uker) * 7 if uker else 0


def alder(p: Paastand, referanse: str) -> int:
    """Dager fra påstandens gjelder-dato til referansen, minus etterslepet."""
    return (_dato(referanse) - _dato(p.gjelder)).days - etterslep(p.kilde)


def utgaatt(p: Paastand, referanse: str) -> bool:
    """Er påstanden eldre enn kildens grense? Da er svaret «ukjent»."""
    grense = aldersgrense(p.kilde)
    return grense is not None and alder(p, referanse) > grense


# ----------------------------------------------------------------- visning


def herkomst(p: Paastand) -> dict:
    """Den grå linja: «Fiskeridir. · 30.09.2026», i biter malen kan merke."""
    return {"kilde": p.kilde,
            "kort": visningsord.kilde_kort(p.kilde),
            "gjelder": p.gjelder[:10],
            "vist": (visningsord.uke(p.gjelder) if p.periode == UKE
                     else visningsord.kortdato(p.gjelder))}


def vis(p: Paastand, referanse: str, vist: str = "") -> dict:
    """Det malen trenger for ÉN påstand. `vist` er verdien i menneskelig form.

    Utgått: verdien er «ukjent», og herkomsten er datoen for siste
    rapport — leseren ser hvor gammel den er, ikke en gjetning om i dag.
    """
    if p.nivaa == INDIKASJON:
        raise Indikasjon(f"{p.tema} fra {p.kilde} er en indikasjon og vises ikke")
    gammel = utgaatt(p, referanse)
    return {"tema": p.tema, "felt": p.felt, "nivaa": p.nivaa,
            "verdi": p.verdi,
            "vist": "ukjent" if gammel else (vist or p.verdi),
            "utgaatt": gammel,
            "herkomst": herkomst(p)}
