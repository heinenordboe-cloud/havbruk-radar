"""MALING-DRIFT, etterskrift 03.11.2026 (økt 4b, punkt 4): stille hopp.

    .venv/bin/python analyse/drift/stille_hopp.py ../havbruk-radar-data \
        > analyse/drift/stille_hopp.txt

Fram til 4b8019b skrev arkiver_vilkar.py ingen logg når dagens logg
fantes (`if not sti.exists()`), og kjøringen endte likevel grønn. Det
samme mønsteret står i arkiver_auksjon.py. Et hopp etterlater to slags
spor, og skriptet leter etter begge:

  A. en kropp i arkivet som ingen logg har en rad med `ny` for
     (kjøringen hentet og skrev kroppen, men loggen med fetched_at og
     kode_commit ble hoppet over). En senere kjøring som fant de samme
     bytene, fører dem som `uendret`; det sier at bytene fantes da, ikke
     når de ble hentet første gang;
  B. en Actions-kjøring som endte `success` uten at en logg fra den
     ligger i git (kjøringen hentet, men det står ingenting om det).

Logg «fra kjøringen» er en loggfil lagt til i en commit fra
`havbruk-radar` mellom kjøringens start og 15 minutter etter slutt.

Kjøringene leses med `gh run list` (bare lesing). Kroppene hashes
utpakket, som `raw.arkiver_ny` gjør.
"""

import datetime as dt
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

DATA = Path(sys.argv[1]).resolve()
ARKIV = DATA / "data" / "arkiv"
REPO = "heinenordboe-cloud/havbruk-radar-data"

JOBBER = {
    # workflow: (loggmappe, kroppsmapper)
    "vilkar.yml": ("vilkar", sorted(p.name for p in ARKIV.glob("vilkar-*") if p.is_dir())),
    "auksjon.yml": ("auksjon", ["auksjon"]),
}


def sh(*a: str) -> str:
    return subprocess.run(a, cwd=DATA, check=True, capture_output=True, text=True).stdout


def lagt_til(sti: str) -> tuple[str, str]:
    """Commiten som la til fila: (kort hash, forfatterdato UTC)."""
    ut = sh("git", "log", "--diff-filter=A", "--format=%h %aI", "--", sti).split()
    if not ut:
        return ("—", "")
    t = dt.datetime.fromisoformat(ut[-1]).astimezone(dt.timezone.utc)
    return ut[-2], t.isoformat(timespec="seconds")


def loggrader(mappe: Path) -> dict[str, list[tuple[str, bool]]]:
    """sha256 -> [(loggfil, ny)]. En rad med `ny` sier at DEN kjøringen
    skrev kroppen; en rad uten sier bare at bytene fantes da."""
    rader: dict[str, list[tuple[str, bool]]] = {}
    for f in sorted(mappe.glob("*.logg.json")):
        for r in json.loads(f.read_text()):
            if r.get("sha256"):
                rader.setdefault(r["sha256"], []).append((f.name, bool(r.get("ny"))))
    return rader


def commits_med_logg(loggmappe: str) -> list[tuple[dt.datetime, str, str, str]]:
    ut = sh("git", "log", "--diff-filter=A", "--name-only", "--format=@%h %aI %an",
            "--", f"data/arkiv/{loggmappe}/*.logg.json")
    res, cur = [], None
    for linje in ut.splitlines():
        if linje.startswith("@"):
            h, t, *navn = linje[1:].split(" ")
            cur = (dt.datetime.fromisoformat(t).astimezone(dt.timezone.utc), h, " ".join(navn))
        elif linje.strip() and cur:
            res.append((*cur, Path(linje).name))
    return res


def main() -> None:
    print(f"Datarepo {DATA.name} på {sh('git', 'rev-parse', '--short', 'HEAD').strip()}, "
          f"kjørt {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\n")
    for wf, (loggmappe, kroppsmapper) in JOBBER.items():
        rader = loggrader(ARKIV / loggmappe)
        print(f"== {wf}  logger i {loggmappe}/: "
              f"{len(list((ARKIV / loggmappe).glob('*.logg.json')))}")

        print("\nA. Kropper uten en loggrad med «ny» (første logg med samme bytene)")
        n_kropp = n_uten = 0
        for m in kroppsmapper:
            for f in sorted((ARKIV / m).glob("*.gz")):
                if "karantene" in f.parts[-2]:
                    continue
                n_kropp += 1
                sha = hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest()
                if not any(ny for _, ny in rader.get(sha, [])):
                    n_uten += 1
                    h, t = lagt_til(str(f.relative_to(DATA)))
                    senere = [navn for navn, _ in rader.get(sha, [])]
                    print(f"   {m}/{f.name:<22} {sha[:16]}  lagt til {h} {t}  "
                          f"{'uendret i ' + senere[0] if senere else 'ingen rad'}")
        print(f"   {n_uten} av {n_kropp} kropper har ingen rad med «ny» i noen logg.")

        print("\nB. Actions-kjøringer og loggen de etterlot")
        kjor = json.loads(sh("gh", "run", "list", "-R", REPO, "--workflow", wf,
                             "--limit", "500", "--json",
                             "databaseId,createdAt,updatedAt,conclusion,event"))
        logger = commits_med_logg(loggmappe)
        uten = 0
        for k in sorted(kjor, key=lambda k: k["createdAt"]):
            fra = dt.datetime.fromisoformat(k["createdAt"].replace("Z", "+00:00"))
            til = dt.datetime.fromisoformat(k["updatedAt"].replace("Z", "+00:00")) \
                + dt.timedelta(minutes=15)
            treff = [f"{h} {navn}" for t, h, an, navn in logger
                     if fra <= t <= til and an == "havbruk-radar"]
            if not treff and k["conclusion"] == "success":
                uten += 1
            print(f"   {k['databaseId']} {k['createdAt']} {k['conclusion'] or '—':<9} "
                  f"{k['event']:<17} {', '.join(treff) or 'INGEN LOGG'}")
        print(f"   {len(kjor)} kjøringer, {uten} grønne uten logg.\n")


if __name__ == "__main__":
    main()
