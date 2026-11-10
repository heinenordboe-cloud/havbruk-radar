"""Havbruksfondet per kommune: fordelingsnøkkelen, regnet av registeret.

Kommunesidene (`nettsted.skriv_kommuner()`), skåreren
(`skaar_havbruksfond.py`) og andelstabellen (`python havbruksfond.py
tabell`) leser alle herfra. Det er ÉN vei til tallene: to lesemåter av
samme nøkkel som kunne svart ulikt, er formen F6 og F7 hadde.

Målingen bak står i docs/MALING-HAVBRUKSFOND.md (A1–A3). Der ble
filteret holdt mot Fiskeridirektoratets egen lokalitetsliste for 2025,
og tabellen A2 ble forseglet i predictions/havbruksfond-2026.md.
`tests/test_havbruksfond.py` holder tallene her mot den forseglede
tabellen, kommune for kommune.

## Hva som er fakta og metode, og hva som er tall

Instruksen fra Nærings- og fiskeridepartementet (27.09.2024) gir
måledatoen og nøkkelen. Den brukes som fakta og metode, med lenke, og
ingen tekst fra den gjengis (docs/LISENSKJEDE.md, merknad N og
bruk-kolonnen). Det samme gjelder pressemeldingen som daterer
fordelingen 2025. TALLENE er registerets og Fiskeridirektoratets:

  akvakultursnapshotene  31.08.2026 og 07.09.2026, på hver sin side av
                         måledatoen 01.09.2026 kl. 12.00
  eierskapskroppen       02.09.2026: artene på tillatelsene (ledd 2)
  regnearket 2025        Fiskeridirektoratets beregning: lokalitetene og
                         MTB per 01.09.2025, og delingen av lokaliteter
                         over en kommunegrense

## Filteret, uendret fra målingen

Ledd 1, feltene i akvakultursnapshotet: «SALMON» i `arter`, saltvann,
sjø (`plasseringstype` Offshore), kapasitet i tonn. Ledd 2,
eierskapskroppen: en lokalitet med aktive koblinger der INGEN av
tillatelsene har laks, ørret eller regnbueørret, holdes utenfor. Uten
aktive koblinger holdes den inne. Vekten er
`max(kapasitet, kapasitet_midlertidig)` — MÅLT for 954 av 954
lokaliteter mot Fiskeridirektoratets liste per 01.09.2025.

## Delte lokaliteter er MÅLBARE, ikke målte

Instruksen deler en lokalitet over en kommunegrense etter kartfestet
arealbeslag. Snapshotet har ett punkt per lokalitet. Delingen tas fra
Fiskeridirektoratets regneark for 2025 og merkes MÅLBAR: en grense eller
en lokalitet kan ha flyttet seg siden. Arealene i `akvakultur-flater`
er IKKE brukt. De er ikke målt mot regnearket, og vi har ingen
kommunegrenser å dele dem med.

## Ingen kronebeløp

Ingenting her regner kroner. Fordelingen 2026 har ikke kommet, og en
side med et beløp før den kommer, er et anslag. Skåreren leser
Fiskeridirektoratets tall når de er arkivert.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from core import paths, snapshot

ROT = Path(__file__).resolve().parent

AAR = 2026
FORRIGE_AAR = 2025
# MÅLEDATOEN etter instruksen: 1. september kl. 12.00 i utbetalingsåret,
# altså 10.00 UTC. Registeret har ingen tidsakse; de to snapshotene
# rundt den er det som finnes (CLAUDE.md regel 5).
MAALEDATO = "2026-09-01"
FOR, ETTER = "2026-08-31", "2026-09-07"
# Eneste eierskapskropp i nærheten (neste er 14.09).
EIERSKAP = "2026-09-02"
# Fiskeridirektoratets liste 2025 gjelder 01.09.2025 kl. 12.00. En
# lokalitet klarert første gang etter det kunne ikke stå på den.
FORRIGE_MAALING = "2025-09-01T10:00:00Z"

LAKSEARTER = {"071101": "Laks", "071301": "Ørret", "071401": "Regnbueørret"}

# FAKTA MED LENKE. Hvert tall her er holdt mot kroppen det kommer fra i
# `tests/test_havbruksfond.py`, og ingen tekst fra kroppene står her.
INSTRUKS = {
    "dato": "2024-09-27",
    "kropp": "havbruksfondet/2026-10-12.12.bin.gz",
    # Fiskeridirektoratets adresser svarer 404 (MALING A1). Wayback-
    # avtrykket er kopien vi har hentet.
    "url": ("https://web.archive.org/web/20241103064951/https://www.fiskeridir.no/"
            "Akvakultur/Tema/Havbruksfondet/Endring%20av%20instruks%20for%20"
            "utbetalinger%20gjennom%20Havbruksfondet.pdf/_/attachment/download/"
            "278368a3-b2c0-4f50-bdd4-5aaedc9a870b:4e1ba9181d7f93c46054bb1d5614c8360d58070e/"
            "Endring%20av%20instruks%20for%20utbetalinger%20gjennom%20Havbruksfondet.pdf"),
}
FISKERIDIR_SIDE = "https://www.fiskeridir.no/akvakultur/havbruksfondet"
# Fordelingen 2025 kom 10.11.2025. 2024 (21.10) står ikke her: den
# meldingen er ikke arkivert.
FORDELT = {
    2025: {"dato": "2025-11-10",
           "kropp": "regjeringen-pressemeldinger/2025-11-10.bin.gz",
           "url": "https://www.regjeringen.no/no/aktuelt/"
                  "milliardutbetaling-fra-havbruksfondet/id3138552/"},
}

ANSLAG = ROT / "predictions" / "havbruksfond-2026.md"
ANSLAG2 = ROT / "predictions" / "havbruksfond-2026-pakke2.md"

# DE TO FORSEGLINGENE, slik de ble gjort. Summen er fila som ble
# stemplet, og hver commit er et sted fila kan hentes ut av git og
# summeres på nytt (`fasit_havbruksfond.forseglinger()`). Pakke 2 ble
# skrevet og stemplet i det private havbruk-analyse og gjort offentlig
# her i e1efe15. Forseglingstidspunktet er stempelet, ikke den commiten.
#
# Commitene står eldst først. Kommunesidene lenker til den SISTE i
# kodrepoet for fila og for .ots-fila (`nettsted._forseglingene()`):
# pakke 1s .ots ble oppgradert med Bitcoin-beviset i 3154667, og lenken
# går dit (Heine, 10.11.2026). 04d91dd står fortsatt, og fasiten prøver
# begge.
FORSEGLINGER = (
    {"pakke": "pakke 1", "fil": "predictions/havbruksfond-2026.md",
     "sha256": "de9ba03432837c0cfc2fd0b2b145bfdad2e7ebcf47dea4a6addb626e38387002",
     "forseglet": "2026-10-12",
     "commits": (("havbruk-radar", "66016dd3e636a03ab4f13563c110125e1cfcc27d", "fil"),
                 ("havbruk-radar", "04d91ddc890279935d00639179d4192fc97890fd", "ots"),
                 ("havbruk-radar", "31546677baa01a34bf7c086b6d4a805bd60e4a0e", "ots"))},
    {"pakke": "pakke 2", "fil": "predictions/havbruksfond-2026-pakke2.md",
     "sha256": "ccb451bdde451430d48c7a3f62ec037d98a0c91b2ae4b631cd2165bbc69701a0",
     "forseglet": "2026-11-09",
     "commits": (("havbruk-analyse", "3ba12f8d5e6139ff10b03a2adbdd9adc1693fc49", "fil"),
                 ("havbruk-analyse", "4d3ac79ec477c20e6b71ce947252303aa8f4524a", "ots"),
                 ("havbruk-radar", "e1efe15f0b8bd6874411120fdd571f2b8c2807f4", "fil"),
                 ("havbruk-radar", "e1efe15f0b8bd6874411120fdd571f2b8c2807f4", "ots"))},
)


class Grunnlagssprik(ValueError):
    """De to snapshotene rundt måledatoen gir ulike nøkler."""


# ------------------------------------------------------------- kroppene


@dataclass(frozen=True)
class Kropp:
    """En fil nøkkelen er regnet av: hvor, sha256 av innholdet, og fila.

    `sha256` er av de UKOMPRIMERTE bytene, som `raw_hash` og som i
    målingen. `fil` er fila slik den ligger, for stempelet: manifestene
    har summen av fila, ikke av innholdet (`stempel.filer()`).
    """
    navn: str
    sha256: str
    fil: Path
    dato: str = ""
    hentet: str = ""


def _arkivkropp(rel: str) -> tuple[Kropp, bytes]:
    fil = paths.ARKIV_DIR / rel
    data = gzip.open(fil, "rb").read()
    return Kropp(rel, hashlib.sha256(data).hexdigest(), fil,
                 dato=rel.split("/")[-1][:10]), data


def lokaliteter(dato: str) -> tuple[dict[str, dict[str, str]], Kropp]:
    """{lokalitetsnummer: {felt: verdi}} i akvakultursnapshotet for `dato`.

    Gjennom snapshot-døra (`snapshot.versjoner`), nyeste versjon.
    """
    versjoner = snapshot.versjoner("akvakultur", dato)
    if not versjoner:
        raise FileNotFoundError(f"akvakultur har ikke snapshotet {dato}")
    nr, ramme = versjoner[-1]
    ut: dict[str, dict[str, str]] = {}
    for e, f, v in ramme.select(["entity_id", "field", "value"]).iter_rows():
        ut.setdefault(e, {}).setdefault(f, v)
    summer = ([v for v in ramme["raw_hash"].unique().to_list() if v]
              if "raw_hash" in ramme.columns else [])
    fil = snapshot.RAW_DIR / "akvakultur" / (
        f"{dato}.parquet" if nr == 1 else f"{dato}.{nr}.parquet")
    return ut, Kropp(f"akvakultur/{fil.name}",
                     summer[0] if len(summer) == 1 else "", fil, dato=dato,
                     hentet=snapshot.fetched_at_i(ramme) or "")


def mtb(r: dict[str, str]) -> float:
    """`max(kapasitet, kapasitet_midlertidig)`, i tonn."""
    verdier = []
    for f in ("kapasitet", "kapasitet_midlertidig"):
        try:
            verdier.append(float(r.get(f) or ""))
        except ValueError:
            pass
    return max(verdier, default=0.0)


def ledd1(r: dict[str, str]) -> bool:
    return ("SALMON" in (r.get("arter") or "")
            and r.get("vanntype") == "Salt"
            and r.get("plasseringstype") == "Offshore"
            and r.get("kapasitet_enhet") == "TN")


def lakselisenser(dato: str = EIERSKAP) -> tuple[dict[str, bool], Kropp]:
    """{lokalitetsnummer: har minst én aktiv laksetillatelse}. Fravær er
    ingen aktiv kobling."""
    kropp, data = _arkivkropp(f"eierskap/{dato}.json.gz")
    per: dict[str, bool] = {}
    for t in json.loads(data)["tillatelser"]:
        arter = {f["code"] for f in (t.get("species") or {}).get("fishCodes", [])}
        laks = bool(arter & set(LAKSEARTER))
        for c in t.get("connections", []):
            if c.get("active"):
                per[c["siteNr"]] = per.get(c["siteNr"], False) or laks
    return per, kropp


# -------------------------------------------------------- regnearkene


def regneark(aar: int) -> tuple[dict[str, list[list[str]]], Kropp]:
    """Fiskeridirektoratets beregningsregneark for `aar`, fra arkivet.

    Kjent på tittelen i første celle av «Utbetalingsoversikt», ikke på
    filnavnet: fiskeridir.no har kalt fila noe nytt hvert år. Nyeste
    arkiverte treff vinner, så et rettet regneark avløser det første.
    """
    from core import raw
    from publiseringsvakt import xlsx_ark
    tittel = f"Utbetalinger fra Havbruksfondet {aar}"
    mappe = paths.ARKIV_DIR / "havbruksfondet"
    treff = None
    for fil in sorted(mappe.glob("*.bin.gz"), key=raw.orden):
        data = gzip.open(fil, "rb").read()
        ark = xlsx_ark(data) if data[:2] == b"PK" else None
        if not ark:
            continue
        ark = dict(ark)
        forste = (ark.get("Utbetalingsoversikt") or [[""]])[0]
        if forste and forste[0].strip() == tittel:
            treff = (ark, Kropp(fil.relative_to(paths.ARKIV_DIR).as_posix(),
                                hashlib.sha256(data).hexdigest(), fil,
                                dato=fil.name[:10]))
    if treff is None:
        raise FileNotFoundError(f"fant ikke regnearket for {aar} i {mappe}")
    return treff


# Kolonnene i lokalitetsarket, slik de har HETT. 2024 og 2025 har samme
# innhold i ulik rekkefølge og med ulike navn; kolonnene finnes derfor av
# overskriften, ikke av plassen.
LOKKOLONNER = {
    "nr": ("LOK_NR", "LOKNR"),
    "navn": ("LOK_NAVN",),
    "komnr": ("LOK_KOMNR", "KOMMUNE_KODE"),
    "kommune": ("LOK_KOM", "KOMMUNE_NAVN"),
    "kap": ("LOK_KAP",),
    "andel": ("Andel i %",),
    "justert": ("Kapasitet justert",),
}


def lokalitetsark(ark: dict[str, list[list[str]]]) -> list[dict]:
    """Lokalitetslista i regnearket: én rad per (lokalitet, kommune)."""
    for navn, rader in ark.items():
        if not navn.startswith("Lok."):
            continue
        for i, hode in enumerate(rader[:5]):
            kol = {k: next((hode.index(h) for h in hs if h in hode), None)
                   for k, hs in LOKKOLONNER.items()}
            if None in kol.values():
                continue
            ut = []
            for r in rader[i + 1:]:
                if len(r) <= max(kol.values()) or not r[kol["nr"]].strip().isdigit():
                    continue
                ut.append({"nr": r[kol["nr"]].strip(), "navn": r[kol["navn"]],
                           "komnr": r[kol["komnr"]].strip(),
                           "kommune": r[kol["kommune"]],
                           "kap": float(r[kol["kap"]]),
                           "andel": float(r[kol["andel"]]),
                           "justert": float(r[kol["justert"]])})
            return ut
    raise ValueError("regnearket har ikke et lokalitetsark med kjente kolonner")


def delte(rader: list[dict]) -> dict[str, list[tuple[str, float]]]:
    """Lokalitetene som er delt mellom kommuner: {nr: [(komnr, andel)]}."""
    per: dict[str, list[tuple[str, float]]] = {}
    for r in rader:
        per.setdefault(r["nr"], []).append((r["komnr"], r["andel"]))
    return {k: v for k, v in per.items() if len(v) > 1}


# ------------------------------------------------------------ nøkkelen


@dataclass
class Plass:
    """En lokalitet slik den teller i ÉN kommune."""
    nr: str
    navn: str
    komnr: str
    mtb: float            # hele lokalitetens MTB
    del_: float           # andelen som teller i denne kommunen
    delt_med: list[str] = field(default_factory=list)

    @property
    def tonn(self) -> float:
        return self.mtb * self.del_


@dataclass
class Nokkel:
    dato: str
    kropp: Kropp
    plasser: dict[str, list[Plass]]      # komnr -> lokalitetene der
    ute: dict[str, dict[str, str]]       # holdt ute av ledd 2
    ledd1: int
    lok: dict[str, dict[str, str]]       # hele snapshotet

    @property
    def per_kommune(self) -> dict[str, float]:
        return {k: sum(p.tonn for p in ps) for k, ps in self.plasser.items()}

    @property
    def total(self) -> float:
        return sum(self.per_kommune.values())


def nokkel(dato: str, lisens=None, deling=None) -> Nokkel:
    """Nøkkelen etter snapshotet for `dato`: hvilke lokaliteter som
    teller, i hvilken kommune, med hvor mye."""
    lok, kropp = lokaliteter(dato)
    if lisens is None:
        lisens, _ = lakselisenser()
    if deling is None:
        deling = delte(lokalitetsark(regneark(FORRIGE_AAR)[0]))
    plasser: dict[str, list[Plass]] = {}
    ute, n1 = {}, 0
    for nr, r in lok.items():
        if not ledd1(r):
            continue
        n1 += 1
        if nr in lisens and not lisens[nr]:
            ute[nr] = r
            continue
        deler = deling.get(nr) or [(r.get("kommunenummer", ""), 1.0)]
        for komnr, andel in deler:
            plasser.setdefault(komnr, []).append(Plass(
                nr, r.get("navn", ""), komnr, mtb(r), andel,
                [k for k, _ in deler if k != komnr]))
    return Nokkel(dato, kropp, plasser, ute, n1, lok)


# ------------------------------------------------ skåringen, når lest
#
# `skaar_havbruksfond.py` skriver `data/havbruksfond/skaring-<år>.json`.
# Den vises først når Heine har lest den: `lest-<år>.json` i samme mappe,
#
#     {"dato": "2026-11-20", "lest_av": "Heine Nordboe",
#      "skaring": "skaring-2026.json", "sha256": "<summen av den fila>"}
#
# KVITTERINGEN GJELDER ÉN FIL, ikke året. Summen kontrolleres mot fila;
# skrives skåringen på nytt med et annet innhold, er den ikke lest, og
# den vises ikke. Samme form som `publiseringsvakt.kvitteringer()`.


def skaringsmappe() -> Path:
    return paths.DATA_DIR / "havbruksfond"


def _kvittert(kvittering: str, nokkel: str) -> dict | None:
    """Fila kvitteringen peker på, med kvitteringen under `lest`. None når
    kvitteringen mangler, peker ut av mappa, eller summen ikke er fila sin."""
    mappe = skaringsmappe()
    kv = mappe / kvittering
    if not kv.exists():
        return None
    k = json.loads(kv.read_text(encoding="utf-8"))
    fil = mappe / str(k.get(nokkel, ""))
    if not k.get(nokkel) or fil.parent != mappe or not fil.exists():
        return None
    data = fil.read_bytes()
    if hashlib.sha256(data).hexdigest() != k.get("sha256"):
        return None
    return {**json.loads(data), "lest": k}


def lest_skaring(aar: int = AAR) -> dict | None:
    """Skåringen for `aar` med kvitteringen, eller None når den ikke er
    skrevet, ikke kvittert, eller kvittert for en annen fil."""
    return _kvittert(f"lest-{aar}.json", "skaring")


# FASITEN (`fasit_havbruksfond.py`) har sin egen kvittering,
# `lest-fasit-<år>.json`, med samme form og samme regel:
#
#     {"dato": "2026-11-20", "lest_av": "Heine Nordboe",
#      "fasit": "fasit-2026.json", "sha256": "<summen av den fila>"}
#
# Den er det eneste som setter Fiskeridirektoratets beløp på
# kommunesidene. En egen fil, så en kvittering for skåringen fra økt 9
# verken skrives over eller leses som en kvittering for fasiten.


def lest_fasit(aar: int = AAR) -> dict | None:
    """Fasiten for `aar` med kvitteringen, eller None når den ikke er
    skrevet, ikke kvittert, eller kvittert for en annen fil."""
    return _kvittert(f"lest-fasit-{aar}.json", "fasit")


# -------------------------------------------------- ingen gjengivelse
#
# INSTRUKSENE OG PRESSEMELDINGENE BRUKES SOM FAKTA OG METODE, MED LENKE.
# De er UBELAGT i lisenskjeden, og UBELAGT stopper bare en kilde som
# gjengis (docs/LISENSKJEDE.md, bruk-kolonnen). Det er en påstand om
# sidene, og den holdes her: ingen side har et løp på `SKIVE` ord eller
# mer som også står i en av kroppene.
#
# SEKS ORD, MÅLT 09.11.2026. Artslista «laks, ørret og regnbueørret i» er
# fem ord og står i instruksen; den er et faktum, ikke en formulering, og
# sidene trenger den. Første utkast av metodeteksten hadde sju ord på rad
# fra instruksen, og grensa fanget det.
SKIVE = 6
IKKE_GJENGITT = (
    "havbruksfondet/2026-10-12.12.bin.gz",          # instruksen 27.09.2024
    "havbruksfondet/2026-10-12.13.bin.gz",          # instruksen 30.11.2022
    "havbruksfondet/2026-10-12.14.bin.gz",          # supplerende 2023
    "regjeringen-pressemeldinger/2024-06-06.bin.gz",  # fastpris 2024
    "regjeringen-pressemeldinger/2024-06-25.bin.gz",  # auksjon 2024
    "regjeringen-pressemeldinger/2025-11-10.bin.gz",  # fordelingen 2025
)
_ORD = re.compile(r"\w+")


def ordene(tekst: str) -> list[str]:
    return _ORD.findall(tekst.lower())


def skiver(tekst: str, n: int = SKIVE) -> set[tuple[str, ...]]:
    o = ordene(tekst)
    return {tuple(o[i:i + n]) for i in range(len(o) - n + 1)}


def kroppstekst(rel: str) -> str:
    """Den lesbare teksten i en arkivert kropp: PDF-teksten, eller den
    synlige teksten i en HTML-side."""
    _, data = _arkivkropp(rel)
    if data[:5] == b"%PDF-":
        import pypdf
        return " ".join(s.extract_text() or "" for s in pypdf.PdfReader(io.BytesIO(data)).pages)
    from core.karantene import synlig_tekst
    return synlig_tekst(data)


def kildeskiver() -> dict[str, set[tuple[str, ...]]]:
    return {rel: skiver(kroppstekst(rel)) for rel in IKKE_GJENGITT}


def gjengitt(tekst: str, kilder: dict[str, set[tuple[str, ...]]]
             ) -> list[tuple[str, str]]:
    """(kropp, ordene) for hvert løp på `SKIVE` ord i `tekst` som også står
    i en av kroppene. Tom liste: ingenting er gjengitt."""
    mine = skiver(tekst)
    return sorted({(rel, " ".join(s)) for rel, ks in kilder.items()
                   for s in mine & ks})


def _like(a: Nokkel, b: Nokkel) -> bool:
    def form(n):
        return {k: sorted((p.nr, p.mtb, p.del_) for p in ps)
                for k, ps in n.plasser.items()}
    return form(a) == form(b)


# ------------------------------------------------------- fordelingen


def fylkesnavn(nr: str, lok: dict[str, dict[str, str]]) -> str:
    for r in lok.values():
        if r.get("fylkesnummer") == nr and r.get("fylke"):
            return r["fylke"]
    return ""


def fordeling() -> dict:
    """Alt kommunesidene, skåreren og tabellen trenger.

    Kaster `Grunnlagssprik` når de to snapshotene rundt måledatoen gir
    ulike nøkler: da er andelen per 01.09 ikke lest, og en side som viste
    den ene, ville påstått noe ingen av dem sier alene.
    """
    lisens, eierskapskropp = lakselisenser()
    ark25, regnearkkropp = regneark(FORRIGE_AAR)
    liste25 = lokalitetsark(ark25)
    deling = delte(liste25)
    a = nokkel(FOR, lisens, deling)
    b = nokkel(ETTER, lisens, deling)
    if not _like(a, b):
        raise Grunnlagssprik(f"nøkkelen {FOR} og {ETTER} er ulik")

    total = a.total
    total25 = sum(r["justert"] for r in liste25)
    per25: dict[str, dict[str, float]] = {}
    navn25: dict[str, str] = {}
    for r in liste25:
        per25.setdefault(r["komnr"], {})
        per25[r["komnr"]][r["nr"]] = per25[r["komnr"]].get(r["nr"], 0) + r["justert"]
        navn25.setdefault(r["komnr"], r["kommune"])
    i_2025 = {r["nr"]: r for r in liste25}

    kommuner: dict[str, dict] = {}
    for komnr, plasser in a.plasser.items():
        regnr = [r for r in a.lok.values() if r.get("kommunenummer") == komnr]
        navn = regnr[0]["kommune"] if regnr else navn25.get(komnr, komnr)
        mtb26 = sum(p.tonn for p in plasser)
        mtb25 = sum(per25.get(komnr, {}).values())
        kommuner[komnr] = {
            "nr": komnr, "navn": navn,
            "fylkesnr": komnr[:2], "fylke": fylkesnavn(komnr[:2], a.lok),
            "mtb": mtb26, "andel": mtb26 / total,
            "mtb_2025": mtb25, "andel_2025": mtb25 / total25 if mtb25 else 0.0,
            "lokaliteter": sorted(plasser, key=lambda p: (-p.tonn, p.nr)),
            "ute": sorted((nr for nr, r in a.ute.items()
                           if r.get("kommunenummer") == komnr), key=int),
            "flytt": _flytt(komnr, plasser, per25.get(komnr, {}), a, i_2025),
        }
        k = kommuner[komnr]
        k["endring"] = k["andel"] - k["andel_2025"]
        # ENDRINGEN I TO LEDD, som summerer seg eksakt: kommunens egen MTB
        # over årets nevner, og at nevneren selv flyttet seg.
        k["fra_egne"] = (mtb26 - mtb25) / total
        k["fra_landet"] = mtb25 * (1 / total - 1 / total25)

    fylker: dict[str, dict] = {}
    for k in kommuner.values():
        f = fylker.setdefault(k["fylkesnr"], {"nr": k["fylkesnr"],
                                              "navn": k["fylke"], "mtb": 0.0,
                                              "mtb_2025": 0.0, "lokaliteter": 0,
                                              "delt": False})
        f["mtb"] += k["mtb"]
        f["mtb_2025"] += k["mtb_2025"]
    for nr, f in fylker.items():
        f["andel"] = f["mtb"] / total
        f["andel_2025"] = f["mtb_2025"] / total25
        f["endring"] = f["andel"] - f["andel_2025"]
        f["lokaliteter"] = len({p.nr for k in kommuner.values()
                                if k["fylkesnr"] == nr for p in k["lokaliteter"]})
        f["delt"] = any(p.del_ < 1 and any(d[:2] != nr for d in p.delt_med)
                        for k in kommuner.values() if k["fylkesnr"] == nr
                        for p in k["lokaliteter"])

    return {"aar": AAR, "maaledato": MAALEDATO, "for": a, "etter": b,
            "total": total, "total_2025": total25,
            "kommuner": kommuner, "fylker": fylker,
            "kropper": [a.kropp, b.kropp, eierskapskropp, regnearkkropp],
            "ledd1": a.ledd1, "ute": a.ute}


def _flytt(komnr: str, plasser: list[Plass], liste25: dict[str, float],
           a: Nokkel, i_2025: dict[str, dict]) -> list[dict]:
    """Lokalitetene som flyttet kommunens MTB siden 01.09.2025.

    Hver rad har tonnene 2025 og 2026 i DENNE kommunen og en grunn som er
    lest av snapshotet, ikke gjettet: ny lokalitet, ute av registeret,
    holdt utenfor av ledd 2, utenfor ledd 1, eller registrert i en annen
    kommune.
    """
    naa = {p.nr: p.tonn for p in plasser}
    ut = []
    for nr in sorted(set(naa) | set(liste25), key=int):
        t26, t25 = naa.get(nr, 0.0), liste25.get(nr, 0.0)
        if abs(t26 - t25) < 0.5:
            continue
        r = a.lok.get(nr)
        if nr not in liste25:
            fk = (r or {}).get("forste_klarering", "")
            if fk and fk >= FORRIGE_MAALING:
                grunn, dato = "ny", fk
            elif nr in i_2025:
                grunn, dato = "annen_kommune_2025", ""
            else:
                grunn, dato = "ikke_paa_lista_2025", ""
        elif nr not in naa:
            if r is None:
                grunn, dato = "ute_av_registeret", ""
            elif nr in a.ute:
                grunn, dato = "ledd2", ""
            elif not ledd1(r):
                grunn, dato = "ledd1", ""
            else:
                grunn, dato = "annen_kommune", ""
        else:
            grunn, dato = "endret", ""
        navn = (r or {}).get("navn") or (i_2025.get(nr) or {}).get("navn", "")
        ut.append({"nr": nr, "navn": navn, "t2025": t25, "t2026": t26,
                   "endring": t26 - t25, "grunn": grunn, "dato": dato,
                   "kommune_naa": (r or {}).get("kommunenummer", ""),
                   "i_registeret": r is not None})
    return sorted(ut, key=lambda x: (-abs(x["endring"]), int(x["nr"])))


# ------------------------------------------------- det forseglede anslaget


def anslaget(sti: Path = ANSLAG) -> dict[str, dict[str, float]]:
    """Tabellene i det forseglede anslaget: {"kommuner": {nr: andel},
    "fylker": {nr: andel}}, andelen som brøk (0.045836)."""
    tekst = sti.read_text(encoding="utf-8")
    ut: dict[str, dict[str, float]] = {"kommuner": {}, "fylker": {}}
    del_ = None
    for linje in tekst.splitlines():
        if linje.startswith("## Fylkeskommunene"):
            del_ = "fylker"
        elif linje.startswith("## Kommunene"):
            del_ = "kommuner"
        elif del_ and (m := re.match(r"\|\s*(\d{2,4})\s*\|[^|]*\|\s*([\d.]+)%\s*\|", linje)):
            ut[del_][m.group(1)] = float(m.group(2)) / 100
    return ut


def _tall(celle: str) -> float:
    """«72 548.2» -> 72548.2. Tusenskillet i tabellene er et mellomrom."""
    return float(re.sub(r"[\s ]", "", celle))


def pakke2(sti: Path = ANSLAG2) -> dict:
    """Pakke 2 slik den ble forseglet: de ni påstandene og tabellene.

        {"paastander": [{id, entitet, feil_hvis, konfidens, ...}],
         "fylker":      {nr: {navn, mtb, andel}},
         "kommuner":    {nr: {navn, gruppe, mtb, andel}},
         "lokaliteter": [{paastand, nr, navn, kommuner, mtb, forventet,
                          deling: {komnr: brøk}}],
         "grupper":     {"U": [komnr], "E": [...], "G": [...]}}

    Andelen er en brøk (0.045817), MTB er tonn. KASTER `ValueError` når
    fila ikke har det den ble forseglet med (9 påstander, 8 fylker, 143
    kommuner i tre grupper): da leses ikke anslaget, og ingenting skal
    avgjøres mot det.
    """
    import yaml
    tekst = sti.read_text(encoding="utf-8")
    blokk = re.search(r"```yaml\n(.*?)```", tekst, re.S)
    ut: dict = {"paastander": yaml.safe_load(blokk.group(1))["prediksjoner"] if blokk else [],
                "fylker": {}, "kommuner": {}, "lokaliteter": [], "grupper": {}}
    del_ = None
    for linje in tekst.splitlines():
        if linje.startswith("## "):
            del_ = next((v for p, v in (("## Fylkeskommunene", "fylker"),
                                        ("## Kommunene", "kommuner"),
                                        ("## Lokalitetene", "lokaliteter"))
                         if linje.startswith(p)), None)
            continue
        if m := re.match(r"Gruppe ([UEG]): (.*)\.$", linje):
            ut["grupper"][m.group(1)] = [x.strip() for x in m.group(2).split(",")]
            continue
        if not linje.startswith("|"):
            continue
        c = [x.strip() for x in linje.strip().strip("|").split("|")]
        if del_ == "fylker" and len(c) == 4 and c[0].isdigit():
            ut["fylker"][c[0]] = {"navn": c[1], "mtb": _tall(c[2]),
                                  "andel": float(c[3].rstrip("%")) / 100}
        elif del_ == "kommuner" and len(c) == 5 and c[0].isdigit():
            ut["kommuner"][c[0]] = {"navn": c[1], "gruppe": c[2], "mtb": _tall(c[3]),
                                    "andel": float(c[4].rstrip("%")) / 100}
        elif del_ == "lokaliteter" and len(c) == 6 and c[0].startswith("P2-"):
            ut["lokaliteter"].append({
                "paastand": c[0], "nr": c[1], "navn": c[2],
                "kommuner": [k.strip() for k in c[3].split("/")],
                "mtb": _tall(c[4]), "forventet": c[5],
                "deling": ({k: float(v) for k, v in re.findall(r"(\d{4}) ([\d.]+)", c[5])}
                           if c[5].startswith("delt:") else {})})
    grupper = {g: len(v) for g, v in ut["grupper"].items()}
    if (len(ut["paastander"]) != 9 or len(ut["fylker"]) != 8 or len(ut["kommuner"]) != 143
            or grupper != {"U": 89, "E": 26, "G": 28}
            or {k["gruppe"] for k in ut["kommuner"].values()} != {"U", "E", "G"}):
        raise ValueError(f"{sti.name} har ikke formen den ble forseglet med: "
                         f"{len(ut['paastander'])} påstander, {len(ut['fylker'])} fylker, "
                         f"{len(ut['kommuner'])} kommuner, grupper {grupper}")
    return ut


def segl(sti: Path = ANSLAG) -> dict:
    """Er anslaget det som ble forseglet? Summen i .ots-fila mot fila.

    OpenTimestamps-fila begynner med et fast hode, versjonen, operasjonen
    (0x08 = sha256) og summen av fila som ble stemplet.
    """
    stemplet = ots_sum(Path(str(sti) + ".ots").read_bytes(), f"{sti.name}.ots")
    naa = hashlib.sha256(sti.read_bytes()).hexdigest()
    return {"fil": sti.relative_to(ROT).as_posix(), "sha256": naa,
            "stemplet": stemplet, "uendret": naa == stemplet}


def ots_sum(ots: bytes, navn: str = "OTS-fila") -> str:
    """Summen en OTS-fil er stemplet for: det faste hodet, versjonen,
    operasjonen (0x08 = sha256) og de 32 bytene etter."""
    hode = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
    if not ots.startswith(hode) or ots[len(hode) + 1] != 0x08:
        raise ValueError(f"{navn} er ikke en sha256-stemplet OTS-fil")
    i = len(hode) + 2
    return ots[i:i + 32].hex()


# ------------------------------------------------------ andelstabellen
#
# ANDELSTABELLEN er fila andre skript leser, først prisberegningen i økt
# 13: `data/havbruksfond/andeler-2026.csv` i datarepoet, skrevet av
#
#     python havbruksfond.py tabell
#
# og lest av `les_andelstabell()`. Én rad per kommune og per
# fylkeskommune, skilt av `niva`. Andelen er en brøk med ti desimaler
# (summen er 1 per nivå), ikke prosent; prosentpoengene i `endring_pp`
# er prosent. Hodet (`#`-linjene) sier hva tallene er regnet av, med
# sha256, og hvilken kode som skrev dem.
#
# Fila skrives én gang. Gir en ny kjøring de samme radene, skrives
# ingenting; gir den andre rader, skrives `andeler-2026.2.csv`.

# `omraade` og ikke `navn`: porten leser en kolonne som heter `navn` som
# et selskapsnavn (`publiseringsvakt.NAVNEFELT`), og et kommunenavn er
# ikke et selskap.
TABELLKOLONNER = ("niva", "nr", "omraade", "fylkesnr", "fylke", "mtb_tonn",
                  "andel", "andel_2025", "endring_pp", "lokaliteter", "delt")
NIVAA = ("kommune", "fylkeskommune")
# FASITKOLONNENE, bare i nettstedets kopi (/kommune/andeler-2026.csv), med
# samme innhold som R7s ut/kommuner.csv har tomme: beløpet, andelen, MTB
# og avviket, og summen av tabellen de er lest av.
FASITKOLONNER = ("fasit_belop_kr", "fasit_andel", "fasit_avvik_pp", "fasit_mtb_tonn",
                 "fasit_kilde_sha256")


def tabellrader(f: dict) -> list[dict[str, str]]:
    """Kommunene størst først, så fylkeskommunene størst først."""
    def rad(niva, nr, navn, fylkesnr, fylke, x, lokaliteter, delt):
        return {"niva": niva, "nr": nr, "omraade": navn, "fylkesnr": fylkesnr,
                "fylke": fylke, "mtb_tonn": f"{x['mtb']:.3f}",
                "andel": f"{x['andel']:.10f}",
                "andel_2025": f"{x['andel_2025']:.10f}",
                "endring_pp": f"{(x['andel'] - x['andel_2025']) * 100:.6f}",
                "lokaliteter": str(lokaliteter), "delt": "ja" if delt else ""}
    rader = [rad("kommune", k["nr"], k["navn"], k["fylkesnr"], k["fylke"], k,
                 len(k["lokaliteter"]), any(p.del_ < 1 for p in k["lokaliteter"]))
             for k in sorted(f["kommuner"].values(), key=lambda k: (-k["mtb"], k["nr"]))]
    rader += [rad("fylkeskommune", x["nr"], x["navn"], x["nr"], x["navn"], x,
                  x["lokaliteter"], x["delt"])
              for x in sorted(f["fylker"].values(), key=lambda x: (-x["mtb"], x["nr"]))]
    return rader


def tabellhode(f: dict, kode: str = "", skrevet: str = "",
               nettsted: bool = False) -> list[str]:
    """`#`-linjene: hva tallene er, og hva de er regnet av. Nettstedets
    kopi har ikke linjene om repoet (stier og kode)."""
    linjer = [
        f"Havbruksfondet {AAR}: andelen av klarert lokalitets-MTB per "
        f"{MAALEDATO} kl. 12.00, per kommune og fylkeskommune.",
        "Kilde: Fiskeridirektoratet (Akvakulturregisteret og beregningen "
        f"for {FORRIGE_AAR}). Sammenstillingen er Kystloggens.",
        "andel: brøk, summen er 1 per niva. endring_pp: prosentpoeng fra "
        f"{FORRIGE_AAR}.",
        f"andel_{FORRIGE_AAR}: Fiskeridirektoratets egen nøkkel per "
        f"01.09.{FORRIGE_AAR}.",
        "delt=ja: minst én lokalitet er delt med Fiskeridirektoratets "
        f"andel fra {FORRIGE_AAR} (MÅLBAR, ikke målt i år).",
        (f"fasit_*: Fiskeridirektoratets fordeling {AAR}. Tomme til den er "
         "publisert og fasiten er lest; fasit_avvik_pp er fra andel."
         if nettsted else
         f"Ingen kronebeløp: fordelingen {AAR} er ikke en del av tabellen."),
    ]
    for k in f["kropper"]:
        linjer.append(f"grunnlag: {k.navn} sha256 {k.sha256}")
    if nettsted:
        return linjer
    s = segl()
    linjer.append(f"lik anslaget {s['fil']} (sha256 {s['sha256']}) "
                  f"på fire desimaler: se tests/test_havbruksfond.py")
    if kode:
        linjer.append(f"skrevet av havbruksfond.py tabell, kode {kode}"
                      + (f", {skrevet}" if skrevet else ""))
    return linjer


def fasitceller(rad: dict[str, str], fasit: dict | None) -> dict[str, str]:
    """`FASITKOLONNER` for én rad: tomme uten fasit, ellers
    Fiskeridirektoratets beløp, andel og MTB, og summen av tabellen de er
    lest av (`fasit_havbruksfond.py`)."""
    tom = dict.fromkeys(FASITKOLONNER, "")
    if not fasit:
        return tom
    x = fasit["sider"]["kommuner" if rad["niva"] == "kommune" else "fylker"].get(rad["nr"])
    if not x:
        return tom
    mtb = next((k.get("fasit_mtb") for k in fasit["avvik"]["kommuner"]
                if k["nr"] == rad["nr"]), None) if rad["niva"] == "kommune" else None
    return {"fasit_belop_kr": f"{x['belop']:.2f}", "fasit_andel": f"{x['andel']:.10f}",
            "fasit_avvik_pp": f"{(x['andel'] - float(rad['andel'])) * 100:.6f}",
            "fasit_mtb_tonn": "" if mtb is None else f"{mtb:.3f}",
            "fasit_kilde_sha256": fasit["tabell"]["sha256"]}


def tabelltekst(f: dict, hode: list[str], fasit: dict | None = None,
                nettsted: bool = False) -> str:
    """Tabellen som tekst. Nettstedets kopi har `FASITKOLONNER` i tillegg,
    tomme til fasiten er kvittert; datarepoets fil har dem ikke, fordi
    `les_andelstabell()` krever nøyaktig `TABELLKOLONNER`."""
    ut = io.StringIO()
    for linje in hode:
        ut.write(f"# {linje}\n")
    kolonner = TABELLKOLONNER + (FASITKOLONNER if nettsted else ())
    w = csv.DictWriter(ut, fieldnames=kolonner, lineterminator="\n")
    w.writeheader()
    w.writerows([{**r, **fasitceller(r, fasit)} if nettsted else r for r in tabellrader(f)])
    return ut.getvalue()


def _rader_i(tekst: str) -> str:
    return "".join(l for l in tekst.splitlines(keepends=True) if not l.startswith("#"))


def tabellsti(mappe: Path | None = None) -> list[Path]:
    """Andelstabellene som finnes, eldst skrevet først."""
    mappe = mappe or skaringsmappe()
    ut, n = [], 1
    while (mappe / (f"andeler-{AAR}.csv" if n == 1 else f"andeler-{AAR}.{n}.csv")).exists():
        ut.append(mappe / (f"andeler-{AAR}.csv" if n == 1 else f"andeler-{AAR}.{n}.csv"))
        n += 1
    return ut


def skriv_andelstabell(mappe: Path | None = None) -> Path | None:
    """Skriver tabellen i datarepoet. None når de samme radene står der."""
    import datetime as dt
    from core import kodeproveniens
    mappe = mappe or skaringsmappe()
    f = fordeling()
    kode = kodeproveniens.commit()
    if kode and kodeproveniens.rent() != kodeproveniens.RENT:
        kode += " (urent arbeidstre)"
    skrevet = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    tekst = tabelltekst(f, tabellhode(f, kode, skrevet))
    finnes = tabellsti(mappe)
    if finnes and _rader_i(finnes[-1].read_text(encoding="utf-8")) == _rader_i(tekst):
        return None
    mappe.mkdir(parents=True, exist_ok=True)
    n = len(finnes) + 1
    sti = mappe / (f"andeler-{AAR}.csv" if n == 1 else f"andeler-{AAR}.{n}.csv")
    sti.write_text(tekst, encoding="utf-8")
    return sti


class Tabellfeil(ValueError):
    """Andelstabellen har ikke formen `les_andelstabell()` lover."""


def les_andelstabell(sti: Path | None = None) -> dict[str, dict[str, dict]]:
    """{"kommune": {nr: rad}, "fylkeskommune": {nr: rad}}, med tallene som
    tall. Nyeste fil når `sti` ikke er gitt.

    KASTER `Tabellfeil` når kolonnene ikke er `TABELLKOLONNER`, når et nivå
    er ukjent, eller når andelene ikke summerer seg til 1 per nivå. En
    prisberegning skal stoppe på en ødelagt tabell, ikke regne på den.
    """
    if sti is None:
        filer = tabellsti()
        if not filer:
            raise FileNotFoundError(f"ingen andelstabell for {AAR} i {skaringsmappe()}")
        sti = filer[-1]
    leser = csv.DictReader(io.StringIO(_rader_i(sti.read_text(encoding="utf-8"))))
    if tuple(leser.fieldnames or ()) != TABELLKOLONNER:
        raise Tabellfeil(f"{sti.name}: kolonnene er {leser.fieldnames}")
    ut: dict[str, dict[str, dict]] = {n: {} for n in NIVAA}
    for r in leser:
        if r["niva"] not in ut:
            raise Tabellfeil(f"{sti.name}: ukjent niva {r['niva']!r}")
        ut[r["niva"]][r["nr"]] = {
            **r, "mtb_tonn": float(r["mtb_tonn"]), "andel": float(r["andel"]),
            "andel_2025": float(r["andel_2025"]),
            "endring_pp": float(r["endring_pp"]),
            "lokaliteter": int(r["lokaliteter"]), "delt": r["delt"] == "ja"}
    for niva, rader in ut.items():
        if not rader or abs(sum(r["andel"] for r in rader.values()) - 1) > 1e-6:
            raise Tabellfeil(f"{sti.name}: andelene for {niva} summerer ikke til 1")
    return ut


if __name__ == "__main__":
    if sys.argv[1:] != ["tabell"]:
        sys.exit("bruk: python havbruksfond.py tabell")
    sti = skriv_andelstabell()
    print(sti or f"Uendret: {tabellsti()[-1]} har de samme radene.")
