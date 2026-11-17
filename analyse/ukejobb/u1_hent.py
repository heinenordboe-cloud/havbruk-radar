"""MALING-UKEJOBB 0a og 0c: Actions-kjøringene i datarepoet, hentet og arkivert.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/ukejobb/u1_hent.py 2026-11-17 2026-10-12 2026-11-17 \
        > analyse/ukejobb/u1_hent.txt

Argumentene er datoen i filnavnet og første og siste dag (UTC) kjøringene
skal være opprettet. Datoen kommer inn, den slås ikke opp her (CLAUDE.md
1b); klokka leses bare for `fetched_at` i loggen.

Henter med `gh api` (innlogget, bare GET) fra GitHubs REST-API:

    /repos/<datarepoet>/actions/runs?created=<dag>      én gang per dag
    /repos/<datarepoet>/actions/runs/<id>/jobs?filter=all   én gang per kjøring

Hva som arkiveres, og hva som ikke gjør det:

  * svarene slik de kom: IKKE arkivert. De har `actor`,
    `triggering_actor` og `head_commit` (navn og e-post på den som
    committet, og commit-meldingen, som for innsamlingen siterer
    endringsloggen). Loggen fører sha256 og lengde for hvert svar;
  * én redusert kropp: arkivert i `maling-ukejobb/`. For hver kjøring og
    hver jobb bare feltene i KJORING og JOBB under: id-er, navn på
    workflow og jobb, hendelse, utfall, tidspunktene og stegene. Tallene
    i MALING-UKEJOBB er regnet av den kroppen (u2_tabeller.py).

Loggen er `maling-ukejobb/<dato>.u1.logg.json`, samme form som
analyse/soknader/s1_mal.py.
"""

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import raw  # noqa: E402
from core.paths import ARKIV_DIR  # noqa: E402

MAPPE = "maling-ukejobb"
REPO = "heinenordboe-cloud/havbruk-radar-data"
KJORING = ("id", "name", "path", "event", "status", "conclusion", "created_at",
           "run_started_at", "updated_at", "run_attempt", "run_number", "head_sha")
JOBB = ("id", "run_id", "run_attempt", "name", "status", "conclusion", "created_at",
        "started_at", "completed_at", "labels")
STEG = ("number", "name", "status", "conclusion", "started_at", "completed_at")


def gh(sti: str, logg: list[dict], hva: str) -> dict:
    r = subprocess.run(["gh", "api", sti], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"STOPP: gh api {sti} feilet: {r.stderr.decode()[:300]}")
    logg.append({"hva": hva, "url": f"https://api.github.com/{sti}", "status": 200,
                 "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "byte": len(r.stdout), "sha256": hashlib.sha256(r.stdout).hexdigest(),
                 "arkivert": False})
    return json.loads(r.stdout)


def dager(fra: dt.date, til: dt.date):
    d = fra
    while d <= til:
        yield d
        d += dt.timedelta(days=1)


def main() -> None:
    dato, fra, til = sys.argv[1], dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3])
    logg: list[dict] = []
    kjoringer: list[dict] = []
    for dag in dager(fra, til):
        side, sett = 1, 0
        while True:
            svar = gh(f"repos/{REPO}/actions/runs?created={dag}&per_page=100&page={side}",
                      logg, f"kjøringer opprettet {dag}, side {side}")
            kjoringer += [{k: k_.get(k) for k in KJORING} for k_ in svar["workflow_runs"]]
            sett += len(svar["workflow_runs"])
            if sett >= svar["total_count"] or not svar["workflow_runs"]:
                break
            side += 1
        if sett != svar["total_count"]:
            raise SystemExit(f"STOPP: {dag}: {sett} kjøringer lest, API-et sier {svar['total_count']}")
    id_er = [k["id"] for k in kjoringer]
    if len(set(id_er)) != len(id_er):
        raise SystemExit("STOPP: samme kjøring kom to ganger")

    jobber: list[dict] = []
    for k in sorted(kjoringer, key=lambda k: k["id"]):
        side, sett = 1, 0
        while True:
            svar = gh(f"repos/{REPO}/actions/runs/{k['id']}/jobs?filter=all&per_page=100&page={side}",
                      logg, f"jobbene i kjøring {k['id']}, side {side}")
            for j in svar["jobs"]:
                rad = {f: j.get(f) for f in JOBB}
                rad["steps"] = [{f: s.get(f) for f in STEG} for s in j.get("steps") or []]
                jobber.append(rad)
            sett += len(svar["jobs"])
            if sett >= svar["total_count"] or not svar["jobs"]:
                break
            side += 1
        if sett != svar["total_count"]:
            raise SystemExit(f"STOPP: kjøring {k['id']}: {sett} jobber lest, "
                             f"API-et sier {svar['total_count']}")

    kropp = {"repo": REPO, "opprettet_fra": fra.isoformat(), "opprettet_til": til.isoformat(),
             "felt": {"kjoring": list(KJORING), "jobb": list(JOBB), "steg": list(STEG)},
             "kjoringer": sorted(kjoringer, key=lambda k: k["id"]),
             "jobber": sorted(jobber, key=lambda j: (j["run_id"], j["id"]))}
    sti = raw._ledig_sti(MAPPE, dato, "json")
    sha, ny = raw.arkiver_ny(MAPPE, dato, kropp)
    if not ny:
        raise SystemExit(f"STOPP: kroppen {sha} ligger alt i {MAPPE}/")
    data, _ = raw._serialiser(kropp)
    grunnlag = hashlib.sha256("\n".join(
        f"{p['url']} {p['sha256']}" for p in logg).encode("utf-8")).hexdigest()
    logg.append({"hva": "redusert kropp: feltene i `felt`, ingen navn og ingen commit-meldinger",
                 "url": "avledet", "status": "avledet",
                 "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "byte_utpakket": len(data), "sha256_utpakket": sha, "sha256": sha,
                 "fil": sti.name, "arkivert": True,
                 "sha256_over_svarene": grunnlag})
    loggsti = ARKIV_DIR / MAPPE / f"{dato}.u1.logg.json"
    if loggsti.exists():
        raise SystemExit(f"STOPP: {loggsti} finnes")
    loggsti.write_text(json.dumps(logg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"Actions-kjøringer i {REPO}, opprettet {fra} … {til} (UTC)")
    print(f"  API-kall: {len(logg) - 1} (ingen svar arkivert; sha256 per svar i loggen)")
    print(f"  sha256 over svarene (linjer «url sha256», i hentet rekkefølge): {grunnlag}")
    print(f"  kjøringer: {len(kjoringer)}   jobber (alle forsøk): {len(jobber)}")
    print(f"  redusert kropp: {MAPPE}/{sti.name}, {len(data)} B utpakket, sha256 {sha}")
    print(f"  logg: {MAPPE}/{loggsti.name}")


if __name__ == "__main__":
    main()
