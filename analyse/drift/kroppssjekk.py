"""MALING-DRIFT: hva skjer når kilden svarer 200 med noe annet enn dataene?

    .venv/bin/python analyse/drift/kroppssjekk.py > analyse/drift/kroppssjekk.txt
    .venv/bin/python analyse/drift/kroppssjekk.py --med-arkiv > analyse/drift/kroppssjekk.etter.txt

Fra 03.11.2026 (økt 3b) skiller utskriften `lagret` (i serien) fra
`karantene` (data/arkiv/<mappe>/karantene*/, core/karantene.py). Med
`--med-arkiv` kjøres i tillegg vilkar, havbruksfond, auksjon og
luseinnkomst med en KOPI av jobbens egne mapper i arkivet, så reglene
som sammenligner med forrige kropp, har en forrige kropp — slik de har i
drift. kroppssjekk.txt er utskriften fra 02.11.2026 og står uendret.

Fire kropper, hver med status 200, mot hver jobb som fanger data:

    feilside    en HTML-side («Tjenesten er midlertidig utilgjengelig»)
    tom_liste   `[]`, application/json
    tom_kropp   null byte
    halv        første halvdel av en ekte arkivert kropp for jobben
                (sti og sha256 står i utskriften)

Hvert tilfelle kjøres i en EGEN prosess med HAVBRUK_DATA_DIR pekt til en
tom mappe, så ingenting skrives i datarepoet. Nettet er byttet ut med en
falsk httpx-transport som svarer kroppen på hvert kall — bortsett fra
BarentsWatchs token-endepunkt, som får et gyldig token, så det er DATA-
kallet som prøves. Kodeproveniensen er satt til en fast sha.

Det som telles, er filene jobben etterlot under data/ (logger for seg),
og exit-koden. «lagret» betyr at en fil med kroppen eller rader fra den
ble skrevet — det er det spørsmålet målingen stiller.

Lytterne (kystvakt/lytter.py) prøves med prøveserveren fra
tests/test_kystvakt_lytter.py, og regnskapet kjøres på det de skrev.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROT = Path(__file__).resolve().parents[2]
DATAREPO = ROT.parent / "havbruk-radar-data" / "data"

FEILSIDE = (b"<!DOCTYPE html><html><head><title>Feil</title></head><body>"
            b"<h1>Tjenesten er midlertidig utilgjengelig</h1>"
            b"<p>Pr\xc3\xb8v igjen senere.</p></body></html>")

# Ekte kropp per jobb (og per kilde i samle), halvert.
HALV = {
    "daglig": "akvakultur/2026-11-02.json.gz",
    "luseinnkomst": "lusetall-innkomst/2026-11-02.json.gz",
    "auksjon": "auksjon/2026-10-29.bin.gz",
    "havbruksfond": "havbruksfondet/2026-10-28.bin.gz",
    "vilkar": "vilkar-lovdata/2026-11-02.bin.gz",
}
TYPE = {".json": "application/json", ".txt": "text/plain", ".bin": "text/html"}

KROPPER = ("feilside", "tom_liste", "tom_kropp", "halv")


def ekte(rel: str) -> tuple[bytes, str]:
    sti = DATAREPO / "arkiv" / rel
    with gzip.open(sti, "rb") as f:
        data = f.read()
    return data, hashlib.sha256(data).hexdigest()


def siste_kropp(kilde: str) -> str | None:
    """Siste ukentlige kropp for en kilde i samle (ikke .daglig.)."""
    mappe = DATAREPO / "arkiv" / kilde
    if not mappe.is_dir():
        return None
    filer = sorted(p.name for p in mappe.glob("*.gz")
                   if ".daglig." not in p.name and p.name[:4].isdigit())
    return f"{kilde}/{filer[-1]}" if filer else None


def kropp(hva: str, rel: str | None) -> tuple[bytes, str]:
    if hva == "feilside":
        return FEILSIDE, "text/html; charset=utf-8"
    if hva == "tom_liste":
        return b"[]", "application/json"
    if hva == "tom_kropp":
        return b"", "application/json"
    if rel is None:
        return b"", "application/octet-stream"
    data, _ = ekte(rel)
    ext = "." + rel.split(".")[-2]
    return data[: len(data) // 2], TYPE.get(ext, "application/octet-stream")


# ---------------------------------------------------------------- én prosess

def _installer(data: bytes, ctype: str) -> None:
    import time

    import httpx

    from core import kodeproveniens

    def svar(self, request):
        if "connect/token" in str(request.url):
            return httpx.Response(200, json={"access_token": "x", "expires_in": 3600,
                                             "token_type": "Bearer"}, request=request)
        return httpx.Response(200, content=data, headers={"Content-Type": ctype},
                              request=request)

    httpx.HTTPTransport.handle_request = svar
    kodeproveniens.krev_sporbar = lambda *a, **k: ("0" * 40, "rent")
    time.sleep = lambda *a: None


def en(jobb: str, hva: str, kilde: str | None) -> None:
    sys.path.insert(0, str(ROT))
    os.chdir(ROT)
    rel = siste_kropp(kilde) if jobb == "samle" else HALV.get(jobb)
    data, ctype = kropp(hva, rel)
    _installer(data, ctype)
    dato = "2026-11-02"
    if jobb == "samle":
        from core import registry, runner
        [k] = [k for k in registry.discover() if k.name == kilde]
        _, [r] = runner.run_all([k], dato)
        print(json.dumps({"ok": r.ok, "rader": r.count,
                          "feil": (r.error or "").strip().splitlines()[-1:] or [""],
                          "advarsler": r.advarsler}, ensure_ascii=False))
        return
    if jobb == "daglig":
        import arkiver_daglig as m
        sys.exit(m.main(["--dato", dato]))
    if jobb == "luseinnkomst":
        import arkiver_luseinnkomst as m
        sys.exit(m.main(["--dato", dato]))
    if jobb == "auksjon":
        import arkiver_auksjon as m
        sys.argv = ["arkiver_auksjon.py", "--fra", "20261101", "--dato", dato]
        sys.exit(m.main())
    if jobb == "havbruksfond":
        import arkiver_havbruksfond as m
        sys.exit(m.main(["--daglig", "--fra", "20261101", "--dato", dato]))
    if jobb == "vilkar":
        import arkiver_vilkar as m
        sys.exit(m.main(["--dato", dato]))
    raise SystemExit(f"ukjent jobb {jobb}")


# ---------------------------------------------------------------- utfall

# Jobbenes egne mapper i arkivet, for --med-arkiv.
ARKIVMAPPER = {
    "vilkar": ["vilkar", "vilkar-*"],
    "havbruksfond": ["havbruksfondet", "regjeringen-pressemeldinger"],
    "auksjon": ["auksjon"],
    "luseinnkomst": ["lusetall-innkomst"],
}


def _i_karantene(sti: str) -> bool:
    return any(d.startswith("karantene") for d in sti.split("/")[2:-1])


def filer(rot: Path, for_: frozenset = frozenset()) -> tuple[list[str], list[str]]:
    """(lagret i serien, logger). En kropp i karantene er ikke lagret i
    serien; se `karantene_filer()`. `for_` er det som lå i kopien av
    arkivet fra før (--med-arkiv), og det er ikke med."""
    alle = [p.relative_to(rot).as_posix() for p in rot.rglob("*") if p.is_file()]
    alle = [a for a in alle if a not in for_]
    logger = sorted(p for p in alle if p.endswith(".logg.json"))
    return sorted(set(alle) - set(logger) - {a for a in alle if _i_karantene(a)}), logger


def karantene_filer(rot: Path) -> list[str]:
    """Kroppene i karantene (ikke postene ved siden av)."""
    alle = [p.relative_to(rot).as_posix() for p in rot.rglob("*.gz") if p.is_file()]
    return sorted(a for a in alle if _i_karantene(a))


def kjor(jobb: str, hva: str, kilde: str | None = None, med_arkiv: bool = False) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        data.mkdir()
        for_: frozenset = frozenset()
        if med_arkiv:
            for mønster in ARKIVMAPPER.get(jobb, []):
                for m in (DATAREPO / "arkiv").glob(mønster):
                    shutil.copytree(m, data / "arkiv" / m.name)
            for_ = frozenset(p.relative_to(data).as_posix() for p in data.rglob("*")
                             if p.is_file())
        env = dict(os.environ, HAVBRUK_DATA_DIR=str(data),
                   BARENTSWATCH_CLIENT_ID="prove", BARENTSWATCH_CLIENT_SECRET="prove")
        r = subprocess.run([sys.executable, __file__, "--en", jobb, hva, kilde or ""],
                           env=env, capture_output=True, text=True, timeout=600)
        lagret, logger = filer(data, for_)
        ut = {"exit": r.returncode, "lagret": lagret, "logger": logger,
              "karantene": karantene_filer(data),
              "stdout": r.stdout, "stderr": r.stderr}
        # Det loggen sa om kroppen, når jobben skrev en.
        ut["loggstatus"] = []
        for l in logger:
            try:
                d = json.loads((data / l).read_text())
            except ValueError:
                continue
            for post in (d if isinstance(d, list) else [d]):
                if isinstance(post, dict):
                    ut["loggstatus"].append({k: post.get(k) for k in
                                             ("status", "byte", "feil", "advarsler")
                                             if post.get(k) not in (None, [], "")})
        return ut


def linje(ut: dict) -> str:
    lagret = [f for f in ut["lagret"]]
    feil = [l for l in (ut["stdout"] + ut["stderr"]).splitlines()
            if "::error::" in l or "Error" in l or "feilet" in l][-1:]
    return (f"exit {ut['exit']}, lagret {len(lagret)}"
            + (f" ({', '.join(lagret[:3])}{' …' if len(lagret) > 3 else ''})" if lagret else "")
            + f", karantene {len(ut['karantene'])}"
            + (f"; {feil[0].strip()[:150]}" if feil else ""))


def lyttere() -> None:
    """bw-lytteren mot en strøm som svarer 200 med en feilside og med en
    halv JSON-linje, og regnskapet på det den skrev."""
    sys.path.insert(0, str(ROT / "tests"))
    sys.path.insert(0, str(ROT / "kystvakt"))
    import test_kystvakt_lytter as t
    import regnskap
    for hva, linjer in (("feilside", [FEILSIDE + b"\n"]),
                        ("tom_liste", [b"[]\n"]),
                        ("halv", [b'{"type":"Position","mmsi":2570905\n'])):
        with tempfile.TemporaryDirectory() as tmp:
            srv, _ = t.bw_server(linjer, ["tok"])
            t.kjor_bw(Path(tmp), srv, 1.5)
            srv.shutdown()
            raa = Path(tmp) / "raa"
            ferdige = t.ferdige(raa)
            poster = [x for f in ferdige for x in t.poster(f)]
            meldinger = sum(1 for _ in poster)
            uten = sum(1 for _, l in poster if regnskap.les_bw(l)[0] is None)
            print(f"  lytter bw   {hva:<10} lagret {len(ferdige)} fil(er), "
                  f"{meldinger} linjer, {uten} uten MMSI i regnskapets lesing")


def ais_manifest() -> None:
    """ais_manifest.py leser utleveringens JSON fra stdin. Workflowen sjekker
    bare at stdin er gyldig JSON (`json.load` i steget før)."""
    status = (DATAREPO / "ais" / "status.json").read_bytes()
    gyldig = json.dumps({**json.loads(status), "manifester": []}).encode()
    for hva, inn in (("feilside", FEILSIDE), ("tom_liste", b"[]"),
                     ("tom_kropp", b""), ("halv", gyldig[: len(gyldig) // 2]),
                     ("tomme_felt", b'{"manifester": [], "skrevet": ""}')):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            r = subprocess.run([sys.executable, "ais_manifest.py"], input=inn, cwd=ROT,
                               env=dict(os.environ, HAVBRUK_DATA_DIR=str(data)),
                               capture_output=True, timeout=60)
            lagret, _ = filer(data)
            kar = karantene_filer(data)
            feil = next((l for l in reversed((r.stdout + r.stderr).decode().splitlines())
                         if "::error::" in l or "Error" in l), "")[:110]
            innhold = ""
            if (data / "ais" / "status.json").exists():
                innhold = (data / "ais" / "status.json").read_text().strip().replace("\n", " ")
            print(f"  ais-manifest {hva:<10} exit {r.returncode}, lagret {len(lagret)} "
                  f"{lagret}, karantene {len(kar)}  {feil}"
                  f"{'  status.json: ' + innhold[:80] if innhold else ''}")


def main(med_arkiv: bool = False) -> None:
    print("MALING-DRIFT kroppssjekk — fire kropper med status 200 mot hver jobb")
    print(f"datarepo: {DATAREPO}\n")
    print("Halve kropper (første halvdel av):")
    for jobb, rel in HALV.items():
        data, sha = ekte(rel)
        print(f"  {jobb:<13} data/arkiv/{rel}  {len(data)} B  sha256 {sha}")
    print()
    for jobb in HALV:
        for hva in KROPPER:
            print(f"  {jobb:<13} {hva:<10} {linje(kjor(jobb, hva))}")
        print()

    if med_arkiv:
        print("Med en kopi av jobbens egne mapper i arkivet (--med-arkiv):")
        for jobb in ARKIVMAPPER:
            for hva in KROPPER:
                print(f"  {jobb:<13} {hva:<10} "
                      f"{linje(kjor(jobb, hva, med_arkiv=True))}")
            print()

    sys.path.insert(0, str(ROT))
    os.chdir(ROT)
    from core import registry
    kilder = sorted(k.name for k in registry.discover())
    print(f"samle: {len(kilder)} aktive kilder, run_all() per kilde "
          f"(rå kropp arkiveres FØR parse, se core/runner.py)")
    for navn in kilder:
        rel = siste_kropp(navn)
        if rel:
            d, sha = ekte(rel)
            print(f"  halv for {navn}: data/arkiv/{rel}  {len(d)} B  sha256 {sha}")
        for hva in KROPPER:
            ut = kjor("samle", hva, navn)
            try:
                svar = json.loads(ut["stdout"].strip().splitlines()[-1])
            except (ValueError, IndexError):
                svar = {"ok": None, "rader": None,
                        "feil": [(ut["stderr"].strip().splitlines() or [""])[-1][:120]]}
            raa = [f for f in ut["lagret"] if f.startswith("arkiv/")]
            print(f"  samle {navn:<20} {hva:<10} ok={svar['ok']!s:<5} rader={svar['rader']!s:<6} "
                  f"rå arkivert={len(raa)} karantene={len(ut['karantene'])}  "
                  f"{svar['feil'][0][:110]}"
                  + (f"  advarsler={len(svar.get('advarsler') or [])}"
                     if svar.get("advarsler") else ""))
        print()
    lyttere()
    print()
    ais_manifest()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--en":
        en(sys.argv[2], sys.argv[3], sys.argv[4] or None)
    else:
        main(med_arkiv="--med-arkiv" in sys.argv)
