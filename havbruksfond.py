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

import gzip
import hashlib
import json
import re
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
                                              "navn": k["fylke"], "mtb": 0.0})
        f["mtb"] += k["mtb"]
    for f in fylker.values():
        f["andel"] = f["mtb"] / total

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


def segl(sti: Path = ANSLAG) -> dict:
    """Er anslaget det som ble forseglet? Summen i .ots-fila mot fila.

    OpenTimestamps-fila begynner med et fast hode, versjonen, operasjonen
    (0x08 = sha256) og summen av fila som ble stemplet.
    """
    hode = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
    ots = Path(str(sti) + ".ots").read_bytes()
    if not ots.startswith(hode) or ots[len(hode) + 1] != 0x08:
        raise ValueError(f"{sti.name}.ots er ikke en sha256-stemplet OTS-fil")
    i = len(hode) + 2
    stemplet = ots[i:i + 32].hex()
    naa = hashlib.sha256(sti.read_bytes()).hexdigest()
    return {"fil": sti.relative_to(ROT).as_posix(), "sha256": naa,
            "stemplet": stemplet, "uendret": naa == stemplet}
