"""Skåreren: Fiskeridirektoratets fordeling mot det forseglede anslaget.

    python skaar_havbruksfond.py                     # årets, når den er arkivert
    python skaar_havbruksfond.py --formatprove 2025 --ut ~/kystloggen-utkast/9

## Hva den gjør

Når `arkiver_havbruksfond.py --daglig` har arkivert Fiskeridirektoratets
regneark for 2026, leser skåreren det (`havbruksfond.regneark()`, kjent
på tittelen og ikke på filnavnet) og holder hver kommunes og hver
fylkeskommunes andel mot anslaget som ble forseglet 12.10.2026
(predictions/havbruksfond-2026.md). Andelen er Fiskeridirektoratets
TOTALT per kommune delt på summen for kommunene, og BELØP per
fylkeskommune delt på summen for fylkeskommunene — slik anslaget selv
sier at det skal avgjøres.

Den skriver avviket per kommune, den største feilen, og hvor mange som
traff innenfor ±0,05 prosentpoeng, terskelen i målingen. De fire
`feil_hvis`-leddene i anslaget skrives ut hver for seg, som tall. Om
anslaget holdt, avgjør Heine når han har lest resultatet; skåreren skriver
ikke et utfall.

## Hvor resultatet havner, og når det vises

`data/havbruksfond/skaring-<år>.json` og `.md` i datarepoet. Nettstedet
viser resultatet først når `data/havbruksfond/lest-<år>.json` finnes og
har summen av nøyaktig den skåringsfila (`nettsted.skaring_lest()`): en
kvittering for en KONKRET fil, ikke en bryter. Skrives fila på nytt med
et annet innhold, treffer ikke kvitteringen lenger.

Fila skrives én gang. Finnes den med et annet innhold (et rettet
regneark, for eksempel), skrives `skaring-<år>.2.json`, som ellers i
datarepoet.

## Seglet prøves først

Anslaget skåres bare når fila er den som ble stemplet: summen i
`.ots`-fila skal være summen av fila (`havbruksfond.segl()`). Er den
ikke det, stopper skåreren med exit 2. Et anslag som er endret etter
seglet, er ikke anslaget.

## Formatprøven

`--formatprove 2025` leser regnearket for 2025 SOM OM det var årets, så
formatet er kjent den dagen 2026 kommer. Den skriver til `--ut`, aldri
til datarepoet, og hver fil den skriver sier FORMATPRØVE øverst. Den er
ikke et treff: 2025 er et oddetallsår med en del for ny MTB, og anslaget
gjelder 2026.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import havbruksfond as h
from core import paths

TERSKEL_PP = 0.05
TERSKEL_VIST = "0,05"
FORMATPROVE = ("FORMATPRØVE — ikke et treff og ikke et utfall. "
               "Regnearket for {aar} er lest som om det var årets, "
               "og holdt mot anslaget for 2026.")


# --------------------------------------------------- Fiskeridirektoratet


def _kolonner(hode: list[str], navn: dict[str, tuple[str, ...]]) -> dict[str, int | None]:
    hode = [c.strip().upper() for c in hode]
    return {k: next((hode.index(n.upper()) for n in ns if n.upper() in hode), None)
            for k, ns in navn.items()}


def kommunetall(ark: dict[str, list[list[str]]]) -> dict[str, dict]:
    """{komnr: {navn, nyklarert, ordinar, totalt}} fra «Utbetalingsoversikt»."""
    rader = ark["Utbetalingsoversikt"]
    for i, hode in enumerate(rader[:5]):
        kol = _kolonner(hode, {"nr": ("KOMNR",), "navn": ("KOMMUNE",),
                               "ny": ("ANDEL NYKLARERT",),
                               "ordinar": ("ORDINÆR UTBETALING",),
                               "totalt": ("TOTALT",)})
        if kol["nr"] is None or kol["totalt"] is None:
            continue
        ut = {}
        for r in rader[i + 1:]:
            if len(r) <= kol["totalt"] or not r[kol["nr"]].strip().isdigit():
                continue

            def tall(k):
                j = kol[k]
                return float(r[j]) if j is not None and r[j].strip() else 0.0
            ut[r[kol["nr"]].strip()] = {"navn": r[kol["navn"]], "nyklarert": tall("ny"),
                                        "ordinar": tall("ordinar"), "totalt": tall("totalt")}
        return ut
    raise ValueError("fant ikke KOMNR og TOTALT i «Utbetalingsoversikt»")


def fylkestall(ark: dict[str, list[list[str]]]) -> dict[str, dict]:
    """{fylkesnr: {navn, belop}} fra «Fylkeskommuner»."""
    rader = ark["Fylkeskommuner"]
    for i, hode in enumerate(rader[:6]):
        kol = _kolonner(hode, {"nr": ("FYLKESNR",), "navn": ("FYLKE",),
                               "belop": ("BELØP", "ORDINÆR UTBET", "TOTALT")})
        if kol["nr"] is None or kol["belop"] is None:
            continue
        return {r[kol["nr"]].strip(): {"navn": r[kol["navn"]], "belop": float(r[kol["belop"]])}
                for r in rader[i + 1:]
                if len(r) > kol["belop"] and r[kol["nr"]].strip().isdigit()}
    raise ValueError("fant ikke FYLKESNR og BELØP i «Fylkeskommuner»")


# ------------------------------------------------------------ skåringen


def _rad(nr: str, navn: str, fasit: float, anslag: float | None) -> dict:
    avvik = None if anslag is None else (fasit - anslag) * 100
    return {"nr": nr, "navn": navn, "fasit_andel": fasit, "anslag_andel": anslag,
            "avvik_pp": avvik,
            "innenfor": avvik is not None and abs(avvik) <= TERSKEL_PP + 1e-12}


def skaar(aar: int) -> dict:
    """Regnearket for `aar` mot anslaget. Kaster når seglet ikke holder."""
    segl = h.segl()
    if not segl["uendret"]:
        raise ValueError(f"anslaget er ikke fila som ble stemplet: {segl}")
    anslag = h.anslaget()
    ark, kropp = h.regneark(aar)
    kom, fyl = kommunetall(ark), fylkestall(ark)
    sum_k = sum(k["totalt"] for k in kom.values())
    sum_f = sum(f["belop"] for f in fyl.values())

    kommuner = [_rad(nr, k["navn"], k["totalt"] / sum_k, anslag["kommuner"].get(nr))
                for nr, k in sorted(kom.items())]
    fylker = [_rad(nr, f["navn"], f["belop"] / sum_f, anslag["fylker"].get(nr))
              for nr, f in sorted(fyl.items())]
    skaaret = [r for r in kommuner if r["avvik_pp"] is not None]
    storst = max(skaaret, key=lambda r: abs(r["avvik_pp"]), default=None)
    fstorst = max((r for r in fylker if r["avvik_pp"] is not None),
                  key=lambda r: abs(r["avvik_pp"]), default=None)
    nyklarert = sorted(nr for nr, k in kom.items() if k["nyklarert"] > 0)
    bare_fasit = sorted(set(kom) - set(anslag["kommuner"]))
    bare_anslag = sorted(set(anslag["kommuner"]) - set(kom))

    return {
        "aar": aar,
        "terskel_pp": TERSKEL_PP,
        "regneark": {"sti": kropp.navn, "sha256": kropp.sha256},
        "anslag": segl,
        "kommuner_antall": len(kom),
        "innenfor": sum(r["innenfor"] for r in skaaret),
        "skaaret": len(skaaret),
        "storste_feil": storst,
        "middel_abs_avvik_pp": (sum(abs(r["avvik_pp"]) for r in skaaret) / len(skaaret)
                                if skaaret else None),
        "fylker_innenfor": sum(r["innenfor"] for r in fylker),
        "fylker_antall": len(fylker),
        "fylker_storste_feil": fstorst,
        # DE FIRE LEDDENE I `feil_hvis`, som tall. Utfallet skriver Heine.
        "feil_hvis": {
            "1_nyklarert_over_0": len(nyklarert),
            "2_kommunesett_ulikt": {"bare_i_fordelingen": bare_fasit,
                                    "bare_i_anslaget": bare_anslag},
            "3_kommuner_utenfor": sum(1 for r in skaaret if not r["innenfor"]),
            "4_fylker_utenfor": sum(1 for r in fylker
                                    if r["avvik_pp"] is not None and not r["innenfor"]),
        },
        "kommuner": sorted(kommuner, key=lambda r: -abs(r["avvik_pp"] or 0)),
        "fylker": fylker,
    }


def _pp(x: float | None) -> str:
    return "—" if x is None else f"{x:+.4f}".replace(".", ",").replace("-", "−")


def markdown(s: dict, formatprove: bool = False) -> str:
    linjer = []
    if formatprove:
        linjer += [f"**{FORMATPROVE.format(aar=s['aar'])}**", ""]
    linjer += [f"# Havbruksfondet {s['aar']}: fordelingen mot anslaget", "",
               f"Regnearket: `{s['regneark']['sti']}`, sha256 `{s['regneark']['sha256']}`.",
               f"Anslaget: `{s['anslag']['fil']}`, sha256 `{s['anslag']['sha256']}`, "
               f"lik summen i .ots-fila: {'ja' if s['anslag']['uendret'] else 'NEI'}.", "",
               f"- kommuner innenfor ±{TERSKEL_VIST} prosentpoeng: "
               f"**{s['innenfor']} av {s['skaaret']}** ({s['kommuner_antall']} i fordelingen)"]
    st = s["storste_feil"]
    if st:
        linjer.append(f"- største feil: {st['navn']} ({st['nr']}), {_pp(st['avvik_pp'])} "
                      f"prosentpoeng")
    if s["middel_abs_avvik_pp"] is not None:
        linjer.append(f"- gjennomsnittlig avvik (absolutt): "
                      f"{s['middel_abs_avvik_pp']:.4f} prosentpoeng".replace(".", ","))
    linjer.append(f"- fylkeskommuner innenfor: {s['fylker_innenfor']} av {s['fylker_antall']}")
    fh = s["feil_hvis"]
    linjer += ["", "## Leddene i `feil_hvis`, som tall", "",
               f"1. kommuner med ANDEL NYKLARERT over 0: {fh['1_nyklarert_over_0']}",
               f"2. bare i fordelingen: {fh['2_kommunesett_ulikt']['bare_i_fordelingen']}; "
               f"bare i anslaget: {fh['2_kommunesett_ulikt']['bare_i_anslaget']}",
               f"3. kommuner utenfor ±{TERSKEL_VIST}: {fh['3_kommuner_utenfor']}",
               f"4. fylkeskommuner utenfor ±{TERSKEL_VIST}: {fh['4_fylker_utenfor']}",
               "", "## Kommunene, største avvik først", "",
               "| komnr | kommune | fordelingen | anslaget | avvik (pp) | innenfor |",
               "|---|---|---:|---:|---:|---|"]
    for r in s["kommuner"]:
        linjer.append(f"| {r['nr']} | {r['navn']} | {r['fasit_andel']:.4%} | "
                      + (f"{r['anslag_andel']:.4%}" if r["anslag_andel"] is not None else "—")
                      + f" | {_pp(r['avvik_pp'])} | {'ja' if r['innenfor'] else 'nei'} |")
    linjer += ["", "## Fylkeskommunene", "",
               "| fylkesnr | fylke | fordelingen | anslaget | avvik (pp) | innenfor |",
               "|---|---|---:|---:|---:|---|"]
    for r in s["fylker"]:
        linjer.append(f"| {r['nr']} | {r['navn']} | {r['fasit_andel']:.4%} | "
                      + (f"{r['anslag_andel']:.4%}" if r["anslag_andel"] is not None else "—")
                      + f" | {_pp(r['avvik_pp'])} | {'ja' if r['innenfor'] else 'nei'} |")
    return "\n".join(linjer) + "\n"


# ------------------------------------------------------------- skrivingen


def _versjoner(mappe: Path, stamme: str) -> tuple[list[Path], Path]:
    """(filene som finnes, eldst først; neste ledige sti)."""
    finnes, n = [], 1
    while True:
        sti = mappe / (f"{stamme}.json" if n == 1 else f"{stamme}.{n}.json")
        if not sti.exists():
            return finnes, sti
        finnes.append(sti)
        n += 1


def skriv(s: dict, mappe: Path, formatprove: bool = False) -> list[Path]:
    """JSON og Markdown. Samme innhold som forrige fil: ingenting skrives."""
    mappe.mkdir(parents=True, exist_ok=True)
    stamme = (f"formatprove-{s['aar']}" if formatprove else f"skaring-{s['aar']}")
    data = dict(s)
    if formatprove:
        data = {"formatprove": FORMATPROVE.format(aar=s["aar"]), **data}
    tekst = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    finnes, sti = _versjoner(mappe, stamme)
    if finnes and finnes[-1].read_text("utf-8") == tekst:
        return []
    sti.write_text(tekst, encoding="utf-8")
    md = sti.with_suffix(".md")
    md.write_text(markdown(s, formatprove), encoding="utf-8")
    return [sti, md]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--formatprove", type=int, metavar="ÅR",
                    help="les regnearket for ÅR som om det var årets (skriver til --ut)")
    ap.add_argument("--ut", type=Path, help="mappe for formatprøven")
    a = ap.parse_args(argv)

    if a.formatprove:
        if not a.ut:
            ap.error("--formatprove krever --ut")
        ut = a.ut.expanduser().resolve()
        if ut == paths.DATA_DIR.resolve() or paths.DATA_DIR.resolve() in ut.parents:
            ap.error("formatprøven skrives aldri i datarepoet")
        aar = a.formatprove
    else:
        ut = h.skaringsmappe()
        aar = h.AAR

    try:
        s = skaar(aar)
    except FileNotFoundError as feil:
        print(f"Regnearket for {aar} er ikke arkivert ennå: {feil}")
        return 0
    except ValueError as feil:
        print(f"STOPPET: {feil}", file=sys.stderr)
        return 2
    skrevet = skriv(s, ut, formatprove=bool(a.formatprove))
    if a.formatprove:
        print(FORMATPROVE.format(aar=aar))
    st = s["storste_feil"]
    print(f"{s['innenfor']} av {s['skaaret']} kommuner innenfor ±{TERSKEL_VIST} pp; "
          f"største feil {st['navn']} {_pp(st['avvik_pp'])} pp" if st else "ingen skåret")
    print("\n".join(str(p) for p in skrevet) or "Uendret: ingenting skrevet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
