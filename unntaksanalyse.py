"""Unntaksvekst 2025/2026, fra søknad til drift. Lest av arkivet.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \\
        .venv/bin/python unntaksanalyse.py

Spørsmålet (docs/ANALYSE-UNNTAKSVEKST.md): for hver lokalitet
Mattilsynet godkjente eller avslo — fikk tillatelsene på lokaliteten mer
kapasitet i registeret, og hvordan har lokaliteten driftet målt mot
vilkårene for unntaksvekst?

Modulen henter INGENTING. Den leser kropper som ligger i `data/arkiv/`,
og hver påstand den leverer bærer kroppens sha256. Det som skal hentes,
hentes av `arkiver_lovdata.py` og `arkiver_mattilsynet.py` — som må være
pushet før de kjøres (kodeproveniens), og derfor ikke kan være en del av
en side som bygges.

## 1. Vilkårene

Står i produksjonsområdeforskriften (FOR-2017-01-16-61) § 12 første ledd
bokstav b nr. 1–6 og annet ledd, med søknadsfrist og
kvalifikasjonsperiode i § 12a. Teksten leses ORDRETT av den arkiverte
kroppen ved hver kjøring, og aldri av en kopi i koden: en forskrift som
endres, skal felle analysen, ikke stå sitert slik den var.

`vilkaar()` holder den gjeldende teksten (SF) mot endringsforskriften
FOR-2023-09-28-1520 (LTI), som ga § 12 dagens ordlyd. Er de like, gjaldt
ordlyden i hele kvalifikasjonsperioden 2023–2025, som begynte uke 40/2023
— fire dager etter at endringen trådte i kraft.

## 2. Søknad → lokalitet → tillatelser → kapasitet

Søknadene er kildens: `data/arkiv/unntaksvekst/`, skrevet av
`Unntaksvekst.fetch()`, med kildens søkerfilter og lokalitetskobling.
Analysen kobler ingenting om. Den deler radene i tre, etter kildens
`kobling`:

    sikre      entydig, via_soker — lokalitetsnummeret er kildens svar
    usikre     usikker — kildens FORSLAG; vises for seg, telles aldri
               sammen med de sikre
    uløste     flertydig, annen_po, ikke_funnet — uten nummer

Tillatelsene på en lokalitet er dem med en AKTIV tilknytning til
lokalitetsnummeret i eierskapskroppen (`connections[].active`), lest for
HVER kropp for seg: en tillatelse som flyttes inn eller ut, er en
hendelse, ikke en ny lokalitet. Kapasiteten er `capacity.current`.

Datoen på en endring er kroppen den ble SETT i. Registeret oppgir ikke
når kapasiteten ble endret, så «mellom 28.09 og 05.10» er alt som kan
sies — samme skille som `nettsted.py` gjør mellom observert og oppgitt
historikk.

## 3. Drift: Mattilsynets rapporter, BarentsWatchs perioder

Lus og behandlinger er Mattilsynets, fra `data/arkiv/mattilsynet-
lakselus/<lokalitet>/`, skrevet av `arkiver_mattilsynet.py lakselus`.
Tiltaksgrensa og periodegrensa er BarentsWatchs, fra snapshotene
`sjotemperatur.lusegrense` og `lusetall.brakklagt`: en produksjons-
periode er det `nettsted.del_i_perioder()` sier, og den bygger på
BarentsWatchs vurdering «trolig uten fisk» (docs/MALING-FUNN-OKTOBER.md
F4.2). Det står på siden.

TRE REGLER VI HAR VALGT, og som står fordi et annet valg gir andre tall:

  * ÉN VERDI PER UKE. 4 533 (lokalitet, uke)-par har mer enn én rapport
    i hele API-et (MÅLT 09.10.2026); ved samdrift rapporterer hver
    innehaver. Lusetallet for uka er det HØYESTE rapporterte, og en
    behandling som står likt i to rapporter, telles én gang.
  * En rapport for en uke som ligger ETTER uka den ble levert i, kan ikke
    være en telling av den uka. Den holdes utenfor og listes.
  * 0,10 og 0,17 sammenlignes med tallet slik Mattilsynet oppgir det,
    uten avrunding: «færre enn 0,1». Tiltaksgrensa sammenlignes slik
    BarentsWatch gjør, med halv-opp til to desimaler
    (`nettsted._over_grensen`).
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import polars as pl

import arkiver_lovdata
from core import paths, snapshot


# ---------------------------------------------------------------- kropper

@dataclass(frozen=True)
class Kropp:
    """En arkivert kropp: hvor den ligger, hva den inneholder, og hashen.

    `sha256` er av de UKOMPRIMERTE bytene, som `raw_hash` på en
    Observation og som i `core/raw.py`.
    """
    sti: Path
    sha256: str
    data: bytes

    @property
    def navn(self) -> str:
        """Stien under `data/arkiv/`, slik dokumentasjonen skriver den."""
        return self.sti.relative_to(paths.ARKIV_DIR).as_posix()


def les_kropp(sti: Path) -> Kropp:
    data = gzip.open(sti, "rb").read()
    return Kropp(sti, hashlib.sha256(data).hexdigest(), data)


def siste_kropp(mappe: str) -> Kropp:
    """Nyeste arkivfil i `data/arkiv/<mappe>/`, etter filnavnets dato og
    løpenummer. Kaster når mappa er tom: en analyse uten grunnlag skal
    stoppe, ikke svare tomt."""
    filer = sorted((paths.ARKIV_DIR / mappe).glob("*.gz"), key=_arkivorden)
    if not filer:
        raise FileNotFoundError(
            f"ingen arkivert kropp i {paths.ARKIV_DIR / mappe}. Kjør "
            f"arkivskriptet først (se modulens docstring).")
    return les_kropp(filer[-1])


def _arkivorden(sti: Path) -> tuple[str, int]:
    """(dato, løpenummer): `2026-10-09.bin.gz` før `2026-10-09.2.bin.gz`."""
    deler = sti.name.split(".")
    nr = int(deler[1]) if len(deler) > 3 and deler[1].isdigit() else 1
    return deler[0], nr


# ------------------------------------------------------- lovdata-paragraf

@dataclass(frozen=True)
class Ledd:
    """Én blokk i en paragraf, slik Lovdata setter den: et avsnitt
    (`nummer` tomt, `nivaa` 0) eller et listepunkt («a.», «1.») på sitt
    nivå."""
    nivaa: int
    nummer: str
    tekst: str


class _Paragraf(HTMLParser):
    """Blokkene i `<div id="PARAGRAF_<nr>">` i et Lovdata-dokument.

    MÅLT 09.10.2026 på SF-teksten av FOR-2017-01-16-61 og LTI-teksten av
    FOR-2023-09-28-1520: et avsnitt er `<p class="… avsnitt">`, et
    listepunkt er `<table class="… listeItem …" data-level="N">` med
    nummeret i første celle. Fotnoten («Endret ved …») er også en tabell
    med `avsnitt` i klassen, men uten `listeItem`, og samles for seg.
    """

    def __init__(self, nr: str) -> None:
        super().__init__(convert_charrefs=True)
        self.id = f"PARAGRAF_{nr}"
        self.blokker: list[Ledd] = []
        self.fotnote: list[str] = []
        self._dybde = 0           # div-dybde inne i paragrafen, 0 = utenfor
        self._ferdig = False
        self._hva = ""            # "p", "liste", "fotnote"
        self._nivaa = 0
        self._celler: list[list[str]] = []
        self._buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        klasse = a.get("class") or ""
        if self._ferdig:
            return
        if tag == "div":
            if self._dybde:
                self._dybde += 1
            elif a.get("id") == self.id:
                self._dybde = 1
            return
        if not self._dybde:
            return
        if tag == "p" and "avsnitt" in klasse.split():
            self._hva, self._buf = "p", []
        elif tag == "table" and "listeItem" in klasse.split():
            self._hva, self._celler = "liste", []
            self._nivaa = int(a.get("data-level") or 1)
        elif tag == "table" and "fotnote" in klasse.split():
            self._hva, self._celler = "fotnote", []
        elif tag == "td" and self._hva in ("liste", "fotnote"):
            self._buf = []

    def handle_endtag(self, tag):
        if self._ferdig or not self._dybde:
            return
        if tag == "div":
            self._dybde -= 1
            if not self._dybde:
                self._ferdig = True
        elif tag == "p" and self._hva == "p" and self._buf is not None:
            self.blokker.append(Ledd(0, "", _ren("".join(self._buf))))
            self._hva, self._buf = "", None
        elif tag == "td" and self._buf is not None:
            self._celler.append(_ren("".join(self._buf)))
            self._buf = None
        elif tag == "table" and self._hva == "liste":
            if len(self._celler) != 2:
                raise ValueError(
                    f"{self.id}: listepunkt med {len(self._celler)} celler, "
                    f"ventet nummer og tekst: {self._celler!r}")
            self.blokker.append(Ledd(self._nivaa, *self._celler))
            self._hva = ""
        elif tag == "table" and self._hva == "fotnote":
            self.fotnote.append(" ".join(c for c in self._celler[1:]))
            self._hva = ""

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)


def _ren(tekst: str) -> str:
    return " ".join(tekst.split())


def paragraf(kropp: bytes, nr: str) -> tuple[list[Ledd], list[str]]:
    """(blokker, fotnoter) for § `nr`. Kaster når paragrafen ikke finnes."""
    p = _Paragraf(nr)
    p.feed(kropp.decode("utf-8"))
    if not p.blokker:
        raise ValueError(f"fant ikke § {nr} (id PARAGRAF_{nr}) i kroppen")
    return p.blokker, p.fotnote


# ---------------------------------------------------------------- vilkår

# Forskriftene i arkivet, med mappa de ligger i. Kapasitetsjusterings-
# forskriften for 2026 er hentet av `trafikklysvedtak` og ligger der.
PRODUKSJONSOMRAADEFORSKRIFTEN = "produksjonsomradeforskriften"
ENDRING_2023 = "produksjonsomradeforskriften-endring-2023"
LAKSELUSFORSKRIFTEN = "lakselusforskriften"
KAPASITETSJUSTERING_2026 = ("trafikklysvedtak", "2026-12-31")

# Starten på hvert vilkår slik det står i § 12 i dag. Teksten leses av
# kroppen; dette er bare prøven på at det er SAMME tekst som analysen er
# skrevet mot. Endres ordlyden, kaster `vilkaar()` — og da skal
# analysen leses på nytt av et menneske, ikke av et regex.
FORVENTET_12 = (
    (0, "", "Uavhengig av miljøstatus i produksjonsområdet"),
    (1, "a.", "der lakseluslarver ikke slippes ut"),
    (1, "b.", "som i vesentlig mindre grad enn andre"),
    (2, "1.", "Det var færre enn 0,1 voksne hunnlus"),
    (2, "2.", "Grensene i forskrift 5. desember 2012 nr. 1140"),
    (2, "3.", "Det kan dokumenteres at det har vært gjennomført maksimalt "
              "én medikamentell behandling"),
    (2, "4.", "Det kan dokumenteres at det har vært gjennomført maksimalt "
              "seks ikke-medikamentelle behandlinger"),
    (2, "5.", "Det har blitt avsluttet et utsett ved å slakte fisken"),
    (2, "6.", "Det er ikke fattet vedtak om midlertidig biomassereduksjon"),
    (0, "", "Selv om det observerte lusenivået"),
    (1, "a.", "ikke har hatt 0,17 eller flere voksne hunnlus"),
    (1, "b.", "ikke har hatt 0,10 eller flere voksne hunnlus"),
)

# HVA SOM MÅLES, per vilkår. Nøkkelen er (nivå, nummer) i rekkefølgen
# over, med «ledd2» for annet ledd. `merke` er dokumentets merke:
#
#   MÅLBAR        regnet av arkiverte kropper, med en regel vi har valgt
#                 og som står her
#   DELVIS        bare en del av vilkåret kan regnes; delen står
#   IKKE MÅLBAR   ingen kilde vi har, sier noe om det
#
# Ingen rad sier om et vilkår er OPPFYLT. Den sier hvilket tall som står
# ved siden av det.
MAALING = {
    "b.1": ("DELVIS",
            "Tellinger med 0,10 eller flere voksne hunnlus i uke 13–39, fra "
            "Mattilsynets lakselusrapporter. Alternativet om utslipp av egg "
            "og frittsvømmende stadier kan ikke regnes av noen kilde vi har."),
    "b.2": ("DELVIS",
            "Tellinger på eller over tiltaksgrensa i uke 40–12. Grensa er "
            "BarentsWatchs «Lusegrense uke» for lokaliteten. At en telling "
            "ligger over, er ikke det samme som at grensa er «brutt» i "
            "forskriftens forstand, og særskilte vilkår i den enkelte "
            "tillatelsen er ikke lest."),
    "b.3": ("DELVIS",
            "Oppføringer av medikamentell behandling i ukesrapportene, per "
            "lokalitet. En oppføring er ikke nødvendigvis det forskriften "
            "kaller én behandling, og alternativet «per fisk fra fisken "
            "settes i sjø» kan ikke regnes uten å følge fiskegruppene."),
    "b.4": ("DELVIS",
            "Oppføringer av ikke-medikamentell behandling i ukesrapportene, "
            "per lokalitet. Samme forbehold som nr. 3."),
    "b.5": ("DELVIS",
            "Om en produksjonsperiode endte i kvalifikasjonsperioden. "
            "Periodegrensa er BarentsWatchs vurdering «trolig uten fisk», "
            "ikke en innrapportert slakting."),
    "b.6": ("IKKE MÅLBAR",
            "Vedtak om midlertidig biomassereduksjon står ikke i noen kilde "
            "vi henter."),
    "a.": ("IKKE MÅLBAR",
           "Bokstav a gjelder lokaliteter der lakseluslarver ikke slippes "
           "ut. Ingen kilde vi har, sier hvilke det er."),
    "ledd2.a": ("MÅLBAR",
                "Tellinger med 0,17 eller flere voksne hunnlus i uke 13–39, "
                "per kalenderår i kvalifikasjonsperioden."),
    "ledd2.b": ("DELVIS",
                "Lengste rekke av påfølgende tellinger med 0,10 eller flere. "
                "Forskriften sier ikke om bokstav b gjelder uke 13–39 slik "
                "bokstav a og nr. 1 gjør. Rekka regnes BEGGE veier — over hele "
                "perioden og innen uke 13–39 — og begge står."),
}


_ENDRINGSINSTRUKS = re.compile(r"^(Ny )?§ \S+ skal lyde:$")


class VilkaarEndret(Exception):
    """Ordlyden i den arkiverte forskriften er ikke den analysen er
    skrevet mot. Kastes i stedet for å regne videre på feil tekst."""


def _krev_ordlyd(blokker: list[Ledd], forventet, hva: str) -> None:
    faktisk = [(b.nivaa, b.nummer, b.tekst) for b in blokker]
    if len(faktisk) != len(forventet) or any(
            (n, nr) != (fn, fnr) or not t.startswith(start)
            for (n, nr, t), (fn, fnr, start) in zip(faktisk, forventet)):
        raise VilkaarEndret(
            f"{hva}: ordlyden er ikke den analysen er skrevet mot. "
            f"Ventet {len(forventet)} blokker som begynner "
            f"{[f[2][:30] for f in forventet]}, fikk "
            f"{[(f[1], f[2][:30]) for f in faktisk]}. Les forskriften på "
            f"nytt før analysen kjøres.")


def vilkaar() -> dict:
    """Vilkårene ORDRETT av de arkiverte kroppene, med kilde og hash.

    Returnerer
        paragraf12      [Ledd], gjeldende tekst (SF)
        paragraf12a     [Ledd]
        endret_ved      fotnoten under § 12, ordrett
        lik_2023        True når § 12 i SF er ordlik § 12 i
                        FOR-2023-09-28-1520 (LTI)
        lakselus8       [Ledd], lakselusforskriften § 8
        kilder          {dokument: Kropp} for de tre Lovdata-kroppene og
                        kapasitetsjusteringsforskriften 2026
        url             {dokument: adressen kroppen ble hentet fra}

    Kaster `VilkaarEndret` når § 12 ikke lenger er teksten over.
    """
    sf = siste_kropp(arkiver_lovdata.kilde(PRODUKSJONSOMRAADEFORSKRIFTEN))
    lti = siste_kropp(arkiver_lovdata.kilde(ENDRING_2023))
    lus = siste_kropp(arkiver_lovdata.kilde(LAKSELUSFORSKRIFTEN))
    mappe, dato = KAPASITETSJUSTERING_2026
    kap = les_kropp(paths.ARKIV_DIR / mappe / f"{dato}.bin.gz")

    p12, fotnote = paragraf(sf.data, "12")
    _krev_ordlyd(p12, FORVENTET_12, "produksjonsområdeforskriften § 12")
    p12a, _ = paragraf(sf.data, "12a")
    # Endringsforskriften setter instruksen for NESTE paragraf inne i
    # samme div: «Ny § 12a skal lyde:» står som siste avsnitt i § 12.
    # MÅLT 09.10.2026; den er Lovdatas redigering, ikke ordlyden.
    p12_2023 = [b for b in paragraf(lti.data, "12")[0]
                if not _ENDRINGSINSTRUKS.match(b.tekst)]
    lus8, _ = paragraf(lus.data, "8")

    return {
        "paragraf12": p12,
        "paragraf12a": p12a,
        "endret_ved": fotnote,
        "lik_2023": [(b.nivaa, b.nummer, b.tekst) for b in p12]
                    == [(b.nivaa, b.nummer, b.tekst) for b in p12_2023],
        "lakselus8": lus8,
        "kilder": {PRODUKSJONSOMRAADEFORSKRIFTEN: sf, ENDRING_2023: lti,
                   LAKSELUSFORSKRIFTEN: lus, "kapasitetsjustering-2026": kap},
        "url": {**arkiver_lovdata.DOKUMENTER,
                "kapasitetsjustering-2026":
                    "https://lovdata.no/dokument/LTI/forskrift/2026-08-20-1764"},
    }


# --------------------------------------------- 2. søknadene og kapasiteten

SIKRE = frozenset({"entydig", "via_soker"})
USIKRE = frozenset({"usikker"})


def soknader() -> tuple[Kropp, dict]:
    """(kropp, svar) fra nyeste arkiverte `unntaksvekst`.

    Svaret er det `Unntaksvekst.fetch()` returnerte: `rader` med kildens
    kobling, og `sha256`/`headere` for HTML-kroppen slik den kom."""
    k = siste_kropp("unntaksvekst")
    return k, json.loads(k.data)


def del_rader(rader: list[dict]) -> dict[str, list[dict]]:
    """{sikre, usikre, uloste} etter kildens `kobling`. Kaster på en
    kobling analysen ikke kjenner: en ny verdi hos kilden skal ikke falle
    stille i en av de tre."""
    ut: dict[str, list[dict]] = {"sikre": [], "usikre": [], "uloste": []}
    kjente = SIKRE | USIKRE | {"flertydig", "annen_po", "ikke_funnet"}
    for r in rader:
        k = r.get("kobling")
        if k not in kjente:
            raise ValueError(f"ukjent kobling {k!r} i unntaksvekst-raden "
                             f"{r.get('lokalitet')!r}")
        ut["sikre" if k in SIKRE else "usikre" if k in USIKRE
           else "uloste"].append(r)
    return ut


def eierskapskropper() -> list[tuple[str, Kropp, dict]]:
    """[(dato, kropp, {tillatelsesnummer: tillatelse})], eldst først.

    Én per dato: står det flere versjoner av samme dato, brukes den
    siste, som `snapshot.versjoner()[-1]` ellers i repoet."""
    per_dato: dict[str, Path] = {}
    for sti in sorted((paths.ARKIV_DIR / "eierskap").glob("*.json.gz"),
                      key=_arkivorden):
        per_dato[_arkivorden(sti)[0]] = sti
    ut = []
    for dato in sorted(per_dato):
        k = les_kropp(per_dato[dato])
        d = json.loads(k.data)
        ut.append((dato, k, {str(t.get("licenseNr")): t
                             for t in d.get("tillatelser") or []}))
    return ut


def _tilknyttet(tillatelser: dict, loknr: str) -> dict[str, dict]:
    return {nr: t for nr, t in tillatelser.items()
            if any(c.get("active") and str(c.get("siteNr")) == loknr
                   for c in t.get("connections") or [])}


def _kap(t: dict):
    return (t.get("capacity") or {}).get("current")


def kapasitet(loknr: str, kropper: list[tuple[str, Kropp, dict]]) -> dict:
    """Tillatelsene på lokaliteten og hver kapasitetsendring, kropp for kropp.

        tillatelser   i nyeste kropp: [{nr, kapasitet, enhet, eier_orgnr}]
        endringer     [{fra, til, tillatelse, gammel, ny, endring,
                        en_prosent}] — `en_prosent` er True når ny er
                      nøyaktig round(gammel × 1,01), aritmetikken i
                      kapittel 3 i FOR-2026-08-20-1764 (§ 7)
        inn, ut       tillatelser som fikk eller mistet en aktiv
                      tilknytning: [{fra, til, tillatelse}]
        sum_endring   summen av `endring`, per enhet
        fra, til      første og siste kroppsdato
    """
    endringer, inn, ut_ = [], [], []
    forrige = None
    for dato, _k, tillatelser in kropper:
        her = _tilknyttet(tillatelser, loknr)
        if forrige is not None:
            fdato, fher = forrige
            for nr in sorted(set(fher) | set(her)):
                if nr not in fher:
                    inn.append({"fra": fdato, "til": dato, "tillatelse": nr})
                elif nr not in her:
                    ut_.append({"fra": fdato, "til": dato, "tillatelse": nr})
                elif _kap(fher[nr]) != _kap(her[nr]):
                    g, n = _kap(fher[nr]), _kap(her[nr])
                    endringer.append({
                        "fra": fdato, "til": dato, "tillatelse": nr,
                        "gammel": g, "ny": n,
                        "endring": (n - g) if None not in (g, n) else None,
                        "enhet": (her[nr].get("capacity") or {}).get("unit"),
                        "en_prosent": None not in (g, n)
                                      and _halv_opp(g * 1.01) == n})
        forrige = (dato, her)
    siste = forrige[1] if forrige else {}
    summer: dict[str, float] = {}
    for e in endringer:
        if e["endring"] is not None:
            summer[e["enhet"] or ""] = summer.get(e["enhet"] or "", 0) + e["endring"]
    return {
        "tillatelser": [{"nr": nr, "kapasitet": _kap(t),
                         "enhet": (t.get("capacity") or {}).get("unit"),
                         "eier_orgnr": str(t.get("openLegalEntityNr") or "")}
                        for nr, t in sorted(siste.items())],
        "endringer": endringer, "inn": inn, "ut": ut_, "sum_endring": summer,
        "fra": kropper[0][0] if kropper else "",
        "til": kropper[-1][0] if kropper else "",
    }


def _halv_opp(x: float) -> float:
    """Avrunding til hele tonn, halv opp — «avrundes til nærmeste hele
    tonn» (FOR-2026-08-20-1764 § 7). Pythons round() runder halv til
    partall."""
    return float(int(x + 0.5))


# ------------------------------------------------- 3. drift per lokalitet

# Kvalifikasjonsperioden for søknadene i lista: uke 40/2023 til og med
# uke 39/2025. LEST, ikke valgt: § 12 b sier «fra og med uke 40 i et
# oddetallsår til og med uke 39 i neste oddetallsår», § 12a sier at
# søknaden sendes «innen 1. september i oddetallsår», og lista er runden
# «2025/2026». Kapasitetsjusteringsforskriften 2026 § 20 regner vekst
# over «1. oktober 2023–30. september 2025» — samme to år, fra en annen
# kropp.
KVALIFIKASJON = ((2023, 40), (2025, 39))
ETTER = ((2025, 40), (9999, 53))

GRENSE_01 = Decimal("0.1")
GRENSE_017 = Decimal("0.17")


@dataclass
class Uke:
    """Én lokalitetsuke hos Mattilsynet, slått sammen over rapportene."""
    aar: int
    uke: int
    lus: Decimal | None = None
    medikamentelle: int = 0
    ikke_medikamentelle: int = 0
    rapporter: int = 0
    ulike: bool = False

    @property
    def dato(self) -> str:
        """Mandagen i ISO-uka — samme dato som lusetall bruker."""
        return dt.date.fromisocalendar(self.aar, self.uke, 1).isoformat()


def _behandlinger(r: dict) -> tuple[Counter, Counter]:
    med = Counter(json.dumps(b, sort_keys=True)
                  for b in r.get("medikamentelleBehandlinger") or [])
    ikke = Counter(json.dumps(b, sort_keys=True)
                   for b in r.get("ikkeMedikamentelleBehandlinger") or [])
    for k in r.get("kombinasjonsbehandlinger") or []:
        med += Counter(json.dumps(b, sort_keys=True)
                       for b in k.get("medikamentelleBehandlinger") or [])
        ikke += Counter(json.dumps(b, sort_keys=True)
                        for b in k.get("ikkeMedikamentelleBehandlinger") or [])
    return med, ikke


def mattilsynet_uker(loknr: str) -> tuple[Kropp, dict, list[dict]]:
    """(kropp, {(år, uke): Uke}, holdt_utenfor) for én lokalitet."""
    k = siste_kropp(f"mattilsynet-lakselus/{loknr}")
    post = json.loads(k.data)
    grupper: dict[tuple[int, int], list[dict]] = {}
    utenfor = []
    for r in post["rapporter"]:
        aar, uke = int(r["år"]), int(r["uke"])
        levert = dt.date.fromisoformat(r["rapporteringstidspunkt"][:10])
        if (aar, uke) > tuple(levert.isocalendar()[:2]) or aar < 2000:
            utenfor.append({"aar": aar, "uke": uke,
                            "levert": levert.isoformat()})
            continue
        grupper.setdefault((aar, uke), []).append(r)

    uker = {}
    for (aar, uke), rr in grupper.items():
        u = Uke(aar, uke, rapporter=len(rr))
        verdier = [Decimal(str(r["lusetelling"]["voksneHunnlus"]))
                   for r in rr if (r.get("lusetelling") or {})
                   .get("voksneHunnlus") is not None]
        u.lus = max(verdier) if verdier else None
        med, ikke = Counter(), Counter()
        for r in rr:
            m, i = _behandlinger(r)
            med |= m           # samme oppføring i to rapporter: én gang
            ikke |= i
        u.medikamentelle = sum(med.values())
        u.ikke_medikamentelle = sum(ikke.values())
        u.ulike = len({json.dumps({k_: r.get(k_) for k_ in (
            "lusetelling", "medikamentelleBehandlinger",
            "ikkeMedikamentelleBehandlinger", "kombinasjonsbehandlinger")},
            sort_keys=True) for r in rr}) > 1
        uker[(aar, uke)] = u
    return k, uker, utenfor


def barentswatch_uker(numre, fra: str) -> dict[str, dict[str, dict]]:
    """{lokalitet: {mandag: {brakklagt, lusegrense}}} fra snapshotene.

    Leser hver ukesfil fra `fra` én gang, siste versjon av datoen, og
    plukker lokalitetene i `numre`."""
    numre = set(numre)
    ut: dict[str, dict[str, dict]] = {n: {} for n in numre}
    for kilde, felt in (("lusetall", "brakklagt"),
                        ("sjotemperatur", "lusegrense")):
        for dato in snapshot.datoer(kilde):
            if dato < fra:
                continue
            for _nr, ramme in snapshot.versjoner(kilde, dato)[-1:]:
                sub = ramme.filter((pl.col("field") == felt)
                                   & pl.col("entity_id").is_in(sorted(numre)))
                for eid, verdi in sub.select(["entity_id", "value"]).iter_rows():
                    ut[str(eid)].setdefault(dato, {"dato": dato})[felt] = str(verdi)
    return ut


def _i_uker(uke: int, fra: int, til: int) -> bool:
    """Uke i et ukevindu som kan gå over nyttår (40–12)."""
    return fra <= uke <= til if fra <= til else (uke >= fra or uke <= til)


def _lengste_rekke(uker: list[Uke], grense: Decimal) -> int:
    """Lengste rekke påfølgende ISO-uker med telling ≥ grense. En uke
    uten telling bryter rekka."""
    beste = n = 0
    forrige = None
    for u in sorted(uker, key=lambda x: (x.aar, x.uke)):
        paa_rad = forrige is not None and (
            dt.date.fromisoformat(u.dato)
            - dt.date.fromisoformat(forrige.dato)).days == 7
        if u.lus is not None and u.lus >= grense:
            n = n + 1 if paa_rad and forrige.lus is not None \
                and forrige.lus >= grense else 1
            beste = max(beste, n)
        else:
            n = 0
        forrige = u
    return beste


def maal(uker: list[Uke], bw: dict[str, dict], perioder: list[list[dict]],
         siste_bw: str) -> dict:
    """Tallene ved siden av vilkårene, for ukene i ett vindu.

    Nøklene følger `MAALING`. Ingen av dem sier OPPFYLT.
    """
    from nettsted import _over_grensen

    talte = [u for u in uker if u.lus is not None]
    i_13_39 = [u for u in talte if _i_uker(u.uke, 13, 39)]
    per_aar: dict[int, int] = {}
    for u in i_13_39:
        if u.lus >= GRENSE_017:
            per_aar[u.aar] = per_aar.get(u.aar, 0) + 1
    over = uten_grense = over_40_12 = uten_grense_40_12 = 0
    for u in talte:
        grense = (bw.get(u.dato) or {}).get("lusegrense", "")
        o = _over_grensen(str(u.lus), grense)
        if o is None:
            uten_grense += 1
            uten_grense_40_12 += _i_uker(u.uke, 40, 12)
        elif o:
            over += 1
            over_40_12 += _i_uker(u.uke, 40, 12)
    datoer = {u.dato for u in uker}
    sluttet = [p for p in perioder
               if p[-1]["dato"] in datoer and p[-1]["dato"] < siste_bw
               and _neste_er_brakk(p[-1]["dato"], bw)]
    return {
        "uker": len(uker), "talte": len(talte),
        "maks": max((u.lus for u in talte), default=None),
        "b1_over_01": sum(1 for u in i_13_39 if u.lus >= GRENSE_01),
        "b1_talte": len(i_13_39),
        "b1_maks": max((u.lus for u in i_13_39), default=None),
        "ledd2a_017_per_aar": per_aar,
        "ledd2b_rekke": _lengste_rekke(uker, GRENSE_01),
        "ledd2b_rekke_13_39": _lengste_rekke(
            [u for u in uker if _i_uker(u.uke, 13, 39)], GRENSE_01),
        "b2_over": over_40_12, "b2_uten_grense": uten_grense_40_12,
        "over": over, "uten_grense": uten_grense,
        "b3_medikamentelle": sum(u.medikamentelle for u in uker),
        "b3_uker": sum(1 for u in uker if u.medikamentelle),
        "b4_ikke_medikamentelle": sum(u.ikke_medikamentelle for u in uker),
        "b5_sluttet": len(sluttet),
        "ulike_uker": sum(1 for u in uker if u.ulike),
    }


def _neste_er_brakk(dato: str, bw: dict[str, dict]) -> bool:
    neste = (dt.date.fromisoformat(dato) + dt.timedelta(weeks=1)).isoformat()
    return (bw.get(neste) or {}).get("brakklagt") == "True"


@dataclass
class Drift:
    """Alt analysen vet om driften på én lokalitet."""
    loknr: str
    kropp: Kropp
    uker: dict
    utenfor: list
    perioder: list = field(default_factory=list)
    kvalifikasjon: dict = field(default_factory=dict)
    etter: dict = field(default_factory=dict)
    per_periode: list = field(default_factory=list)
    etter_bw: dict = field(default_factory=dict)


def drift(loknr: str, bw: dict[str, dict], siste_bw: str) -> Drift:
    """Driften i kvalifikasjonsperioden, etter den, og per periode."""
    from nettsted import del_i_perioder

    k, uker, utenfor = mattilsynet_uker(loknr)
    serie = [bw[d] for d in sorted(bw) if "brakklagt" in bw[d]]
    perioder = del_i_perioder(serie)

    def vindu(fra, til, liste=None):
        return [u for u in (liste or uker.values())
                if fra <= (u.aar, u.uke) <= til]

    d = Drift(loknr, k, uker, utenfor, perioder)
    d.kvalifikasjon = maal(vindu(*KVALIFIKASJON), bw, perioder, siste_bw)
    d.etter = maal(vindu(*ETTER), bw, perioder, siste_bw)
    fra_kval = dt.date.fromisocalendar(*KVALIFIKASJON[0], 1).isoformat()
    for p in perioder:
        if p[-1]["dato"] < fra_kval:
            continue
        datoer = {u["dato"] for u in p}
        i_p = [u for u in uker.values() if u.dato in datoer]
        m = maal(i_p, bw, [p], siste_bw)
        d.per_periode.append({
            "fra": p[0]["dato"], "til": p[-1]["dato"], "bw_uker": len(p),
            "aapen": p[-1]["dato"] == siste_bw, **m})
    etter_siste = [u for u in uker.values() if u.dato > siste_bw]
    d.etter_bw = maal(etter_siste, bw, [], siste_bw)
    return d


# ------------------------------------------------------------------ CLI

def _skriv_vilkaar(v: dict) -> None:
    print("VILKÅRENE — produksjonsområdeforskriften § 12, ordrett")
    for dok, k in v["kilder"].items():
        print(f"  {dok:44} {k.navn}  sha256 {k.sha256}")
    print(f"  § 12 ordlik i FOR-2023-09-28-1520: {'ja' if v['lik_2023'] else 'NEI'}")
    print(f"  fotnote: {' | '.join(v['endret_ved'])}")
    for b in v["paragraf12"]:
        print(f"  {'   ' * b.nivaa}{b.nummer} {b.tekst}")
    print("  § 12a:")
    for b in v["paragraf12a"]:
        print(f"    {b.tekst}")
    print("  lakselusforskriften § 8:")
    for b in v["lakselus8"]:
        print(f"    {b.tekst}")


def _skriv_kapasitet() -> None:
    k, svar = soknader()
    deler = del_rader(svar["rader"])
    kropper = eierskapskropper()
    print(f"\nSØKNADENE — {k.navn}  sha256 {k.sha256}")
    print(f"  HTML-kroppen: sha256 {svar['sha256']}, {svar['bytes']} byte, "
          f"headere {svar['headere']}")
    for navn, rader in deler.items():
        print(f"  {navn:7} {len(rader):>3} rader, "
              f"{len({r.get('lokalitet_nr') for r in rader if r.get('lokalitet_nr')})}"
              f" lokalitetsnummer")
    print("\nKAPASITET — eierskapskroppene")
    for dato, kr, _ in kropper:
        print(f"  {dato}  {kr.navn}  sha256 {kr.sha256}")
    for navn in ("sikre", "usikre"):
        sett: dict[str, set] = {}
        for r in deler[navn]:
            sett.setdefault(r["lokalitet_nr"], set()).add(r["resultat"])
        for nr in sorted(sett, key=int):
            kap = kapasitet(nr, kropper)
            if kap["endringer"] or kap["inn"] or kap["ut"]:
                print(f"  [{navn}] {nr} {sorted(sett[nr])}: "
                      f"{len(kap['tillatelser'])} tillatelser, "
                      f"sum {kap['sum_endring']}, "
                      f"{sum(e['en_prosent'] for e in kap['endringer'])}"
                      f"/{len(kap['endringer'])} lik round(x*1,01), "
                      f"inn {[i['tillatelse'] for i in kap['inn']]}, "
                      f"ut {[i['tillatelse'] for i in kap['ut']]}")


def _skriv_drift() -> None:
    _k, svar = soknader()
    deler = del_rader(svar["rader"])
    numre = sorted({r["lokalitet_nr"] for n in ("sikre", "usikre")
                    for r in deler[n]}, key=int)
    fra = dt.date.fromisocalendar(*KVALIFIKASJON[0], 1).isoformat()
    bw = barentswatch_uker(numre, fra)
    siste_bw = max(d for s in bw.values() for d in s)
    print(f"\nDRIFT — {len(numre)} lokaliteter, BarentsWatch {fra} – {siste_bw}")
    for navn in ("sikre", "usikre"):
        res: dict[str, set] = {}
        for r in deler[navn]:
            res.setdefault(r["lokalitet_nr"], set()).add(r["resultat"])
        for nr in sorted(res, key=int):
            d = drift(nr, bw[nr], siste_bw)
            kv, et = d.kvalifikasjon, d.etter
            print(f"  [{navn}] {nr:>5} {'/'.join(sorted(res[nr])):8} "
                  f"KV: {kv['talte']:>3}t b1 {kv['b1_over_01']:>2}/{kv['b1_talte']:<3}"
                  f" 2a {max(kv['ledd2a_017_per_aar'].values(), default=0)}"
                  f" 2b {kv['ledd2b_rekke']}/{kv['ledd2b_rekke_13_39']} b2 {kv['b2_over']}"
                  f" med {kv['b3_medikamentelle']} ikke {kv['b4_ikke_medikamentelle']}"
                  f" slutt {kv['b5_sluttet']} | ETTER: {et['talte']:>3}t"
                  f" ≥0,1(13–39) {et['b1_over_01']} over {et['over']}"
                  f" (u/gr {et['uten_grense']}) med {et['b3_medikamentelle']}"
                  f" ikke {et['b4_ikke_medikamentelle']}"
                  f"  perioder {len(d.per_periode)}  utenfor {d.utenfor}")


def main() -> int:
    _skriv_vilkaar(vilkaar())
    _skriv_kapasitet()
    _skriv_drift()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
