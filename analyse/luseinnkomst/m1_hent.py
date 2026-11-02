"""MALING-LUSEINNKOMST, steg 1: hent uke N til N-4, eldre uker og spesifikasjonen.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/luseinnkomst/m1_hent.py 2026-11-02

Datoen er kjøredatoen og gis inn (CLAUDE.md 1b). Skriver:

  * hver kropp for uke N..N-4 til data/arkiv/lusetall-innkomst/<mandag>.json.gz
    med `raw.arkiver_ny` — samme serialisering som innsamlingen, så sha256
    kan sammenlignes med data/arkiv/lusetall/;
  * uke N-4 hentet én gang til rett etter, for å se om svaret er stabilt;
  * eldre uker (N-5..N-8 og uke N-4 i 2025, 2024, 2020, 2016): kroppen
    arkiveres i lusetall-innkomst BARE hvis den avviker fra innsamlingens;
  * OpenAPI-spesifikasjonen og ett per-lokalitet-svar, for spørsmål b;
  * én logg, data/arkiv/lusetall-innkomst/<dato>.maling.logg.json, med URL,
    status, headere, bytes over linja og utpakket, sha256 og fetched_at
    for hvert kall.

Ingen snapshot, ingen changelog.
"""

import datetime as dt
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402
from sources import _barentswatch  # noqa: E402
from sources._barentswatch import mandag, uke_med_etterslep  # noqa: E402

MAPPE = "lusetall-innkomst"
BASE = "https://www.barentswatch.no/bwapi"


def naa() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def main() -> None:
    kjoredato = dt.date.fromisoformat(sys.argv[1])
    tilgang = _barentswatch.Tilgang("lusetall")
    klient = tilgang.klient()
    logg: list[dict] = []

    def kall(url: str, hva: str) -> tuple[dict | None, bytes]:
        hentet = naa()
        t0 = time.monotonic()
        svar = tilgang.get(klient, url, hva=hva)
        sek = time.monotonic() - t0
        kropp = svar.content
        post = {
            "hva": hva, "url": url, "status": svar.status_code,
            "fetched_at": hentet, "sekunder": round(sek, 3),
            "byte_linje": svar.num_bytes_downloaded,
            "byte_utpakket": len(kropp),
            "sha256_utpakket": hashlib.sha256(kropp).hexdigest(),
            "headere": {k: v for k, v in svar.headers.items()
                        if k.lower() not in ("set-cookie",)},
        }
        logg.append(post)
        time.sleep(_barentswatch.PAUSE_S)
        try:
            return svar.json(), kropp
        except ValueError:
            return None, kropp

    def uke(aar: int, nr: int, hva: str, arkiver: str) -> None:
        data, _ = kall(f"{BASE}/v1/geodata/fishhealth/locality/{aar}/{nr}", hva)
        ser, _ = raw._serialiser(data)
        sha = hashlib.sha256(ser).hexdigest()
        post = logg[-1]
        post.update({"aar": aar, "uke": nr, "observed_at": mandag(aar, nr),
                     "sha256_kanonisk_json": sha})
        innsamlet = ARKIV_DIR / "lusetall" / f"{mandag(aar, nr)}.json.gz"
        if innsamlet.exists():
            with gzip.open(innsamlet, "rb") as f:
                post["innsamlingens"] = {
                    "fil": f"lusetall/{innsamlet.name}",
                    "sha256": hashlib.sha256(f.read()).hexdigest()}
        lik = post.get("innsamlingens", {}).get("sha256") == sha
        if arkiver == "alltid" or (arkiver == "ved_avvik" and not lik):
            skrevet_sha, ny = raw.arkiver_ny(MAPPE, mandag(aar, nr), data)
            assert skrevet_sha == sha
            post["arkivert"] = {"mappe": MAPPE, "ny": ny}
        print(f"  {hva:<28} {post['status']}  {post['byte_linje']:>8} B linje "
              f"{post['byte_utpakket']:>8} B  {sha[:12]}  "
              f"lik innsamlingens: {lik if 'innsamlingens' in post else '—'}")

    # a, c, d: uke N..N-4, og N-4 en gang til
    for k in range(0, 5):
        aar, nr = uke_med_etterslep(kjoredato, k)
        uke(aar, nr, f"N-{k} ({nr}/{aar})", "alltid")
    aar, nr = uke_med_etterslep(kjoredato, 4)
    uke(aar, nr, f"N-4 igjen ({nr}/{aar})", "alltid")

    # c: eldre uker mot innsamlingens kropper
    for k in range(5, 9):
        aar, nr = uke_med_etterslep(kjoredato, k)
        uke(aar, nr, f"N-{k} ({nr}/{aar})", "ved_avvik")
    for aar_tilbake in (1, 2, 6, 10):
        aar, nr = uke_med_etterslep(kjoredato, 4)
        uke(aar - aar_tilbake, nr, f"uke {nr}/{aar - aar_tilbake}", "ved_avvik")

    # b: spesifikasjonen og ett per-lokalitet-svar
    spes, spes_kropp = kall(f"{BASE}/openapi/fishhealth/openapi.json", "openapi")
    sha, ny = raw.arkiver_ny(MAPPE + "-openapi", kjoredato.isoformat(), spes)
    logg[-1]["arkivert"] = {"mappe": MAPPE + "-openapi", "ny": ny,
                            "sha256": sha}
    aar, nr = uke_med_etterslep(kjoredato, 1)
    lok, lok_kropp = kall(
        f"{BASE}/v1/geodata/fishhealth/locality/10029/{aar}/{nr}",
        f"lokalitet 10029 uke {nr}/{aar}")
    sha, ny = raw.arkiver_ny(MAPPE + "-lokalitet", kjoredato.isoformat(), lok)
    logg[-1]["arkivert"] = {"mappe": MAPPE + "-lokalitet", "ny": ny,
                            "sha256": sha}
    klient.close()

    ut = ARKIV_DIR / MAPPE / f"{kjoredato.isoformat()}.maling.logg.json"
    assert not ut.exists(), ut
    ut.write_text(json.dumps(logg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(logg)} kall (pluss tokenkall). Logg: {ut}")


if __name__ == "__main__":
    main()
