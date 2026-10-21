"""Kvalitetsrapporten: hva hvert bygg påstår, og hvordan teksten står seg.

To halvdeler, regnet på to steder og av to grunner:

    påstandene  telt MENS sidene bygges, av de samme påstandene som vises
                (`lokalitet()` kalles med lok-dicten fra `bygg_lokalitet`).
                Tellingen kan da ikke bli uenig med sidene.
    teksten     målt ETTER at sidene er skrevet, av den ferdige HTML-en,
                med den samme leseren porten bruker
                (`publiseringsvakt._tre`). Synlige ord per sidetype, og
                avsnitt over grensa.

Rapporten er `kvalitet.json` i byggets rot og en kort side, `/kvalitet/`.
Den feller ingenting — det gjør porten. Den sier hvor bygget står, slik at
neste bygg kan sammenlignes med dette: tekstreglene fra 20.10.2026 sier at
sidene skal bli kortere, og et tall man ikke måler, vokser i stillhet.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import publiseringsvakt


def sidetype(rel: str) -> str:
    """Sidetypen ut fra stien i bygget. Samme inndeling som målingene."""
    deler = rel.split("/")
    if rel == "index.html":
        return "forside"
    if rel == "404.html":
        return "404"
    topp = deler[0]
    tall = len(deler) == 3 and deler[1].isdigit()
    if topp == "lokalitet":
        return "lokalitet" if tall else "indeks-lokalitet"
    if topp == "produksjonsomrade":
        return "område" if tall else "indeks-område"
    if topp == "selskap":
        return "selskap" if tall else "indeks-selskap"
    if topp == "endringer":
        return {2: "endringer-indeks", 3: "endringer-uke"}.get(
            len(deler), "endringer-type")
    if topp == "om":
        return "metode"
    return topp


# Navnet på siden. JSON-en beholder nøklene over; siden viser disse.
SIDETYPENAVN = {
    "forside": "Forsiden",
    "404": "Fant ikke siden",
    "lokalitet": "Lokalitet",
    "indeks-lokalitet": "Lokalitetslista",
    "område": "Område",
    "indeks-område": "Områdelista",
    "selskap": "Selskap",
    "indeks-selskap": "Selskapslista",
    "endringer-indeks": "Endringer",
    "endringer-uke": "Endringer, uke",
    "endringer-type": "Endringer, type",
    "metode": "Om",
    "sok": "Søk",
}


@dataclass
class Kvalitet:
    """Tellingene for ett bygg. Se modulens docstring."""

    lokalitetssider: int = 0
    # (tema, utfall) -> antall sider: ("fisk", "vist"), ("fisk", "ukjent") ...
    tilstand: Counter = field(default_factory=Counter)
    # (kilde, nivå) -> antall påstander i tilstanden
    per_kilde: Counter = field(default_factory=Counter)
    hull: Counter = field(default_factory=Counter)
    ord_per_type: dict[str, list[int]] = field(
        default_factory=lambda: defaultdict(list))
    avsnitt_over: Counter = field(default_factory=Counter)
    paastand_uten: Counter = field(default_factory=Counter)

    def lokalitet(self, lok: dict) -> None:
        """Én lokalitetsside: påstandene i tilstanden, og hullene a–g."""
        self.lokalitetssider += 1
        ps = lok.get("paastander") or {}
        for tema, p in ps.items():
            if not p:
                continue
            self.tilstand[(tema, "vist")] += 1
            if p.get("utgaatt"):
                self.tilstand[(tema, "ukjent")] += 1
            self.per_kilde[(p["herkomst"]["kilde"], p["nivaa"])] += 1
        fisk = ps.get("fisk")
        # a: en fiskepåstand «Ja» eldre enn grensa, og om den vises som ja.
        if fisk and fisk["verdi"] == "Ja" and fisk["utgaatt"]:
            self.hull["a_ja_eldre_enn_grensa"] += 1
            if fisk["vist"] != "ukjent":
                self.hull["a_vist_som_ja"] += 1
        # b: uenige kilder om samme periode.
        mot = lok.get("fisk_mot_lus") or []
        konflikter = sum(1 for x in mot if x.get("konflikt"))
        if konflikter:
            self.hull["b_sider_med_uenige_maaneder"] += 1
            self.hull["b_uenige_maaneder"] += konflikter
        if ps.get("uenige"):
            self.hull["b_uenige_i_tilstanden"] += 1
        # c: to kapasiteter.
        kap, mtb = ps.get("kapasitet"), ps.get("mtb")
        if kap and mtb:
            self.hull["c_begge_kapasiteter"] += 1
            if kap["verdi"] != mtb["verdi"]:
                self.hull["c_ulike"] += 1
        if ps.get("midlertidig"):
            self.hull["c_midlertidig_ulik_ordinaer"] += 1
        # g: delt posisjon, ingen tillatelser.
        if lok.get("samme_posisjon"):
            self.hull["g_delt_posisjon"] += 1
        if not lok.get("tillatelser_oppgitt"):
            self.hull["g_uten_tillatelser"] += 1

    def tekst(self, rot: Path) -> None:
        """Synlige ord og avsnitt over grensa, over hver ferdig side."""
        for sti in sorted(rot.rglob("*.html")):
            rel = sti.relative_to(rot).as_posix()
            if rel.startswith("pagefind/"):
                continue
            tekst = sti.read_text(encoding="utf-8")
            tre = publiseringsvakt._tre(tekst.split("<body", 1)[-1])
            st = sidetype(rel)
            self.ord_per_type[st].append(publiseringsvakt.synlige_ord(tre))
            for f in publiseringsvakt.avsnittsfunn(rel, tre):
                self.avsnitt_over[st] += 1
            if publiseringsvakt.LOKALITETSSIDE.match(rel):
                self.paastand_uten[st] += len(
                    publiseringsvakt.paastandsfunn(rel, tre))

    def som_json(self, *, bygget: str, data: dict[str, str]) -> dict:
        tilstand: dict[str, dict[str, int]] = defaultdict(dict)
        for (tema, utfall), n in sorted(self.tilstand.items()):
            tilstand[tema][utfall] = n
        return {
            "bygget": bygget,
            "data": data,
            "lokalitetssider": self.lokalitetssider,
            "tilstand": dict(tilstand),
            "paastander_per_kilde": {f"{k} ({niv})": n for (k, niv), n
                                     in sorted(self.per_kilde.items())},
            "hull": dict(sorted(self.hull.items())),
            "tekst": {
                "avsnittsgrense_tegn": publiseringsvakt.AVSNITTSGRENSE,
                "synlige_ord": {
                    st: {"sider": len(v), "median": statistics.median(v),
                         "sum": sum(v)}
                    for st, v in sorted(self.ord_per_type.items())},
                "avsnitt_over_grensa": sum(self.avsnitt_over.values()),
                "avsnitt_over_grensa_per_type": dict(sorted(self.avsnitt_over.items())),
                "paastander_uten_kilde_eller_dato": sum(self.paastand_uten.values()),
            },
        }
