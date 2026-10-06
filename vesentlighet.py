"""Vesentlig eller teknisk: ÉN regel for hver endring i registerkildene.

Lokalitetssiden viser de vesentlige øverst og samler de tekniske. Ukesiden
teller dem. En rapportmotor skal kunne gjøre det samme uten å gå veien om
nettstedet, og derfor står regelen her, i en modul som bare kjenner
changelog-raden, og ikke i `nettsted.py`.

## Inndata

Rader i changeloggens form, slik `changelog.les_alt()` gir dem gjennom
døra: `source`, `field`, `change_type`, `old_value`, `new_value`,
`entity_id`, `observed_at`, og `forrige_observed_at` der den finnes.
`klassifiser()` tar HELE lista på én gang, fordi to av reglene ser på
andre rader: koordinatene leses i par, og «gjentar fisk til stede» spør
om en annen rad samme uke.

## Reglene, i den rekkefølgen de prøves

    ILA/PD           vesentlig når «satt» står på en av sidene
                     teknisk når flagget bare går mellom tomt og ikke satt
    ny / borte       vesentlig: en tillatelse eller lokalitet kom eller gikk
    koordinater      vesentlig fra KOORDINAT_TERSKEL_M og opp, ellers teknisk
    felt kom/gikk    teknisk når det gjentar en fisk-til-stede-endring samme uke
    avledet felt     teknisk når grunnfeltet endret seg i samme par
    tekniske felt    versjon gyldig fra, versjonsårsak, artsbegrensninger
    alt annet        vesentlig

DET SISTE ER MED VILJE. Et felt ingen regel nevner, vises øverst. En
endring som ble skjøvet ned fordi ingen hadde tenkt på feltet, er en
stille utelatelse, og den er dyrere enn en linje for mye.
"""

from __future__ import annotations

import datetime as _dt
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache

VESENTLIG = "vesentlig"
TEKNISK = "teknisk"

# TERSKELEN ER VALGT, IKKE MÅLT — og det står her fordi den ellers ser ut
# som en måling.
#
# MÅLT 06.10.2026 over hele changeloggen: seks flyttinger på sju uker,
# alle med `versjon_aarsak = COORDINATES` hos registeret.
#
#     19,4   22,5   24,2   31,4   |   152,7   190,5   meter
#
# Ingenting mellom 32 og 152. Seks punkter er ikke en fordeling, og
# CLAUDE.md 1b-4 sier at en terskel skal måles når det finnes data. Det
# gjør det nesten ikke ennå. 100 m ble valgt av Heine 06.10.2026, midt i
# det tomme feltet. Den flytter seg ikke av seg selv: endres den, er det
# fordi noen har målt på nytt. Målingen står i
# docs/beslutninger/2026-10-06-vesentlig-og-teknisk.md.
KOORDINAT_TERSKEL_M = 100.0

KOORDINATER = ("breddegrad", "lengdegrad")
KOORDINATKILDE = "akvakultur"

SYKDOMSFLAGG = frozenset({("lusetall", "har_ila"), ("lusetall", "har_pd")})

# Fisk til stede, og feltet som gjentar den. MÅLT 06.10.2026: hver
# `arter_tilstede` som kom eller gikk (77 rader) sto samme dag som en
# `har_fisk`-endring på samme lokalitet. «Fisk: Ja -> Nei» og «Arter:
# borte Laks» er én ting, sagt to ganger.
FISK = ("biomasselag", "har_fisk")
GJENTAR_FISK = frozenset({("biomasselag", "arter_tilstede")})

TEKNISKE_FELT = frozenset({
    ("akvakultur", "versjon_gyldig_fra"),
    # Ikke en hendelse, men registerets egen forklaring av den nye
    # versjonen. Lokalitetssiden viser den som forklaring på endringen
    # samme dag — se `nettsted._med_versjonsaarsak()`.
    ("akvakultur", "versjon_aarsak"),
    ("akvakultur", "artsbegrensninger_antall"),
})

NY_ELLER_BORTE = frozenset({"ny", "borte"})
FELT_KOM_ELLER_GIKK = frozenset({"felt_ny", "felt_borte"})


@dataclass(frozen=True)
class Klasse:
    """Klassen og GRUNNEN. Grunnen er for prøvene og for rapporten: en
    klassifisering ingen kan etterprøve er en påstand uten belegg."""
    klasse: str
    grunn: str

    @property
    def vesentlig(self) -> bool:
        return self.klasse == VESENTLIG


@lru_cache(maxsize=1)
def avledede_felt() -> dict[tuple[str, str], str]:
    """{(kilde, avledet felt): grunnfelt}, kildenes egen erklæring.

    Samme kilde som `nettsted._avledede_felt()`: `Source.avledet_av`.
    Lest her og ikke importert derfra, så modulen ikke trenger nettstedet.
    """
    from core import registry
    from core.contract import erklaert_avledning

    ut: dict[tuple[str, str], str] = {}
    for kilde in registry.discover():
        ut.update(erklaert_avledning(kilde))
    return ut


def avstand_m(fra: tuple[float, float], til: tuple[float, float]) -> float:
    """Storsirkelavstand i meter (haversine, middelradius 6 371 008,8 m)."""
    la1, lo1, la2, lo2 = map(math.radians, (*fra, *til))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


def _tall(v: object) -> float | None:
    try:
        return float(str(v))
    except (TypeError, ValueError):
        return None


def _dato(r: Mapping) -> str:
    return str(r.get("observed_at") or "")[:10]


def _uke(r: Mapping) -> tuple[int, int] | None:
    try:
        d = _dt.date.fromisoformat(_dato(r))
    except ValueError:
        return None
    aar, uke, _ = d.isocalendar()
    return aar, uke


def _flytting(rader: list[Mapping]) -> dict[tuple[str, str], float | None]:
    """{(entitet, dato): meter} for koordinatene som endret seg.

    Bredde og lengde er to rader i loggen og ÉN flytting. Endret bare den
    ene, regnes avstanden med den andre holdt fast. Lengdegrad alene må
    da regnes uten breddegraden den står på, og den regnes ved ekvator:
    det gir den LENGSTE avstanden et lengdegradsavvik kan bety, så en
    usikker flytting havner heller over terskelen enn under.
    """
    par: dict[tuple[str, str], dict[str, tuple]] = {}
    for r in rader:
        if (str(r.get("source")) == KOORDINATKILDE
                and str(r.get("field")) in KOORDINATER
                and str(r.get("change_type")) == "endret"):
            par.setdefault((str(r.get("entity_id")), _dato(r)), {})[
                str(r["field"])] = (_tall(r.get("old_value")),
                                    _tall(r.get("new_value")))
    ut: dict[tuple[str, str], float | None] = {}
    for nokkel, p in par.items():
        b, l = p.get("breddegrad"), p.get("lengdegrad")
        if b and None in b or l and None in l:
            ut[nokkel] = None
        elif b and l:
            ut[nokkel] = avstand_m((b[0], l[0]), (b[1], l[1]))
        elif b:
            ut[nokkel] = avstand_m((b[0], 0.0), (b[1], 0.0))
        else:
            ut[nokkel] = avstand_m((0.0, l[0]), (0.0, l[1]))
    return ut


def klassifiser(rader: Iterable[Mapping],
                avledede: Mapping[tuple[str, str], str] | None = None
                ) -> list[Klasse]:
    """Én `Klasse` per rad, i samme rekkefølge som radene.

    `avledede` kan sendes inn (prøvene gjør det). Standard er kildenes
    egen erklæring.
    """
    rader = list(rader)
    avledede = avledet_av = avledede if avledede is not None else avledede_felt()
    flytting = _flytting(rader)

    fisk_uker = {(str(r.get("entity_id")), _uke(r)) for r in rader
                 if (str(r.get("source")), str(r.get("field"))) == FISK}
    # Grunnfeltene som endret seg, per (kilde, entitet, felt, par).
    grunn_endret = {(str(r.get("source")), str(r.get("entity_id")),
                     str(r.get("field")), _dato(r),
                     str(r.get("forrige_observed_at") or ""))
                    for r in rader}

    ut: list[Klasse] = []
    for r in rader:
        kilde, felt = str(r.get("source")), str(r.get("field"))
        endring = str(r.get("change_type"))
        eid = str(r.get("entity_id"))

        if (kilde, felt) in SYKDOMSFLAGG:
            satt = "True" in (str(r.get("old_value")), str(r.get("new_value")))
            ut.append(Klasse(VESENTLIG, "flagget satt eller opphevet") if satt
                      else Klasse(TEKNISK, "flagget gikk mellom tomt og ikke satt"))
            continue

        if endring in NY_ELLER_BORTE:
            ut.append(Klasse(VESENTLIG, "ny eller borte"))
            continue

        if kilde == KOORDINATKILDE and felt in KOORDINATER:
            m = flytting.get((eid, _dato(r)))
            if m is None:
                ut.append(Klasse(VESENTLIG, "koordinat uten avstand"))
            elif m >= KOORDINAT_TERSKEL_M:
                ut.append(Klasse(VESENTLIG, f"flyttet {m:.0f} m"))
            else:
                ut.append(Klasse(TEKNISK, f"flyttet {m:.0f} m"))
            continue

        if (endring in FELT_KOM_ELLER_GIKK and (kilde, felt) in GJENTAR_FISK
                and (eid, _uke(r)) in fisk_uker):
            ut.append(Klasse(TEKNISK, "gjentar fisk til stede"))
            continue

        grunnfelt = avledet_av.get((kilde, felt))
        if grunnfelt and (kilde, eid, grunnfelt, _dato(r),
                          str(r.get("forrige_observed_at") or "")) in grunn_endret:
            ut.append(Klasse(TEKNISK, f"følger av {grunnfelt}"))
            continue

        if (kilde, felt) in TEKNISKE_FELT:
            ut.append(Klasse(TEKNISK, "teknisk felt"))
            continue

        ut.append(Klasse(VESENTLIG, "ingen regel gjør den teknisk"))
    return ut
