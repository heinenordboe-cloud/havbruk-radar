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
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import arkiver_lovdata
from core import paths


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
                "nr. 1 gjør; rekka regnes over hele perioden."),
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


def main() -> int:
    _skriv_vilkaar(vilkaar())
    _skriv_kapasitet()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
