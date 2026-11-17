"""MALING-UKEJOBB 0a og 0c: tabellene, regnet av den arkiverte kroppen.

    .venv/bin/python analyse/ukejobb/u2_tabeller.py \
        ../havbruk-radar-data/data/arkiv/maling-ukejobb/2026-11-17.json.gz \
        2026-10-18 2026-11-16 > analyse/ukejobb/u2_tabeller.txt

Argumentene er kroppen u1_hent.py arkiverte, og første og siste dag (UTC)
i vinduet for 0a. Ingenting hentes og ingen klokke leses: utskriften er en
ren funksjon av kroppen og de to datoene.

## Minuttene er et anslag etter GitHubs regel, ikke regningen

API-et oppgir ikke fakturerte minutter for dette repoet: `billable` i
`/actions/runs/<id>/timing` var 0 for alle tre kjøringene som ble spurt
17.11.2026, og faktureringsendepunktene svarte 403 for tokenet. Det som
står i kroppen, er når hver jobb startet og ble ferdig, i hele sekunder.

Regelen som brukes her er den GitHub beskriver for private repo: hver
jobb regnes for seg og rundes opp til hele minutter. En jobb som er
hoppet over, teller ikke. Regelen er lest i dokumentasjonen, ikke holdt
mot en regning.
"""

import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Cron per workflow, fra datarepoets .github/jobber.yml 17.11.2026
# (`utloser.schedule`). (ukedag eller None, time, minutt); ukedag 1 = mandag.
CRON = {
    "samle.yml": [(1, 5, 0), (2, 19, 0)],
    "tilsyn.yml": [(None, 6, 0)],
    "daglig.yml": [(None, 5, 23)],
    "luseinnkomst.yml": [(None, 4, 41)],
    "ais-manifest.yml": [(None, 8, 17)],
    "auksjon.yml": [(None, 6, 17)],
    "havbruksfond.yml": [(None, 6, 41), (None, 14, 41), (None, 20, 41)],
    "oppslag.yml": [(3, 6, 0)],
    "speil.yml": [(1, 7, 0), (2, 21, 0)],
    "stempel.yml": [(7, 3, 0)],
}
UKEDAG = ["", "man", "tir", "ons", "tor", "fre", "lør", "søn"]


def tid(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def fil(k: dict) -> str:
    return k["path"].rsplit("/", 1)[-1]


def sekunder(j: dict) -> int | None:
    """Jobbens varighet, eller None for en jobb som ikke kjørte."""
    if j["conclusion"] == "skipped" or not j["started_at"] or not j["completed_at"]:
        return None
    return max(0, int((tid(j["completed_at"]) - tid(j["started_at"])).total_seconds()))


def minutter(s: int | None) -> int:
    return 0 if s is None else max(1, math.ceil(s / 60))


def tabell(hode: list[str], rader: list[list]) -> None:
    print("| " + " | ".join(hode) + " |")
    print("|" + "|".join("---" for _ in hode) + "|")
    for r in rader:
        print("| " + " | ".join(str(c) for c in r) + " |")
    print()


def siste_cron(fil_: str, t: dt.datetime) -> dt.datetime | None:
    """Siste cron-tidspunkt for workflowen til og med `t`."""
    beste = None
    for ukedag, time_, minutt in CRON.get(fil_, []):
        d = t.replace(hour=time_, minute=minutt, second=0, microsecond=0)
        for _ in range(8):
            if d <= t and (ukedag is None or d.isoweekday() == ukedag):
                break
            d -= dt.timedelta(days=1)
        else:
            continue
        beste = d if beste is None or d > beste else beste
    return beste


def t1(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def main() -> None:
    sti, fra, til = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    data = gzip.decompress(sti.read_bytes())
    kropp = json.loads(data)
    kjoringer = {k["id"]: k for k in kropp["kjoringer"]}
    jobber = defaultdict(list)
    for j in kropp["jobber"]:
        jobber[j["run_id"]].append(j)

    print(f"Kropp: {sti.parent.name}/{sti.name}, {len(data)} B utpakket, "
          f"sha256 {hashlib.sha256(data).hexdigest()}")
    print(f"  kjøringer opprettet {kropp['opprettet_fra']} … {kropp['opprettet_til']}: "
          f"{len(kjoringer)}, jobber (alle forsøk): {len(kropp['jobber'])}")
    uten = [i for i in kjoringer if i not in jobber]
    print(f"  kjøringer uten jobber i kroppen: {len(uten)}")
    aapne = [k["id"] for k in kjoringer.values() if k["status"] != "completed"]
    print(f"  kjøringer som ikke var ferdige ved hentingen: {len(aapne)}")
    print()

    # ---------------------------------------------------------------- 0a
    vindu = [k for k in kjoringer.values() if fra <= k["created_at"][:10] <= til]
    dager = (dt.date.fromisoformat(til) - dt.date.fromisoformat(fra)).days + 1
    print(f"### 0a. Jobbtid per workflow, kjøringer opprettet {fra} … {til} ({dager} døgn)")
    print()
    per = defaultdict(lambda: {"kjoringer": 0, "jobber": 0, "hoppet": 0, "sek": 0, "min": 0,
                               "varighet": []})
    for k in vindu:
        p = per[fil(k)]
        p["kjoringer"] += 1
        for j in jobber.get(k["id"], []):
            s = sekunder(j)
            if s is None:
                p["hoppet"] += 1
                continue
            p["jobber"] += 1
            p["sek"] += s
            p["min"] += minutter(s)
            p["varighet"].append(s)
    sum_min = sum(p["min"] for p in per.values())
    rader = []
    for f, p in sorted(per.items(), key=lambda x: -x[1]["min"]):
        v = sorted(p["varighet"])
        rader.append([f, p["kjoringer"], p["jobber"], p["hoppet"],
                      t1(p["sek"] / 60), p["min"],
                      f"{100 * p['min'] / sum_min:.1f}".replace(".", ",") + " %",
                      int(statistics.median(v)) if v else "–", v[-1] if v else "–"])
    rader.append(["**sum**", sum(p["kjoringer"] for p in per.values()),
                  sum(p["jobber"] for p in per.values()),
                  sum(p["hoppet"] for p in per.values()),
                  t1(sum(p["sek"] for p in per.values()) / 60), sum_min, "100,0 %", "", ""])
    tabell(["workflow", "kjøringer", "jobber som kjørte", "hoppet over",
            "jobbtid, minutter", "minutter rundet opp per jobb", "andel",
            "median jobb, s", "lengste jobb, s"], rader)
    print(f"Sum rundet opp per jobb: {sum_min} minutter på {dager} døgn. "
          f"Per 30 døgn: {round(sum_min * 30 / dager)}.")
    forsok = sum(1 for k in vindu if (k["run_attempt"] or 1) > 1)
    print(f"Kjøringer i vinduet med mer enn ett forsøk: {forsok}.")
    print(f"Kjøringer i vinduet uten jobber i kroppen: "
          f"{sum(1 for k in vindu if k['id'] not in jobber)}.")
    for a, b in (("2026-11-01", til),):
        if fra <= a <= b:
            m = sum(minutter(sekunder(j)) for k in vindu if a <= k["created_at"][:10] <= b
                    for j in jobber.get(k["id"], []))
            n = (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days + 1
            print(f"Av dette opprettet {a} … {b}: {m} minutter på {n} døgn. "
                  f"I samme takt per 30 døgn: {round(m * 30 / n)}.")
    print()

    per_uke = defaultdict(int)
    for k in vindu:
        aar, uke, _ = tid(k["created_at"]).isocalendar()
        per_uke[f"{aar}-W{uke:02d}"] += sum(minutter(sekunder(j)) for j in jobber.get(k["id"], []))
    tabell(["ISO-uke", "minutter rundet opp per jobb"],
           [[u, m] for u, m in sorted(per_uke.items())])

    # ------------------------------------------- stegene den nye jobben deler
    print("### 0a. Stegene ukejobben har felles med innsamlingen og tidsstemplingen")
    print()
    steg = defaultdict(list)
    hele = defaultdict(list)
    for k in vindu:
        if fil(k) not in ("samle.yml", "stempel.yml") or k["conclusion"] != "success":
            continue
        for j in jobber.get(k["id"], []):
            s = sekunder(j)
            if s is None:
                continue
            hele[fil(k)].append(s)
            for st in j["steps"]:
                if st["started_at"] and st["completed_at"] and st["conclusion"] == "success":
                    steg[(fil(k), st["name"])].append(
                        int((tid(st["completed_at"]) - tid(st["started_at"])).total_seconds()))
    rader = []
    for (f, navn), v in sorted(steg.items(), key=lambda x: (x[0][0], -statistics.median(x[1]))):
        v = sorted(v)
        rader.append([f, navn, len(v), int(statistics.median(v)), v[-1]])
    tabell(["workflow", "steg", "kjøringer", "median, s", "lengste, s"], rader)
    for f, v in sorted(hele.items()):
        v = sorted(v)
        print(f"Hele jobben i {f}, grønne kjøringer: {len(v)}, median {int(statistics.median(v))} s, "
              f"lengste {v[-1]} s.")
    felles = [("samle.yml", "Set up job"),
              ("samle.yml", "Hent datarepoet (her havner snapshotene)"),
              ("samle.yml", "Hent koden fra kodrepoet"), ("samle.yml", "Sett opp Python"),
              ("samle.yml", "Installer avhengigheter"),
              ("stempel.yml", "Installer OpenTimestamps-klienten"),
              ("stempel.yml", "Stemple"), ("stempel.yml", "Commit stemplene")]
    print(f"Sum av medianene for de {len(felles)} stegene ukejobben også har "
          f"(oppsett, begge repoene, Python, pakkene, klienten, et stempel, en commit): "
          f"{sum(int(statistics.median(steg[s])) for s in felles)} s. "
          f"Sum av de lengste: {sum(max(steg[s]) for s in felles)} s.")
    print()

    # -------------------------------------------------- hvor ofte den starter
    print("### 0a. Hvor ofte ukejobben ville startet: ferdige kjøringer av innsamlingen")
    print()
    samle = sorted((k for k in vindu if fil(k) == "samle.yml"), key=lambda k: k["created_at"])
    tabell(["opprettet (UTC)", "ukedag", "hendelse", "utfall", "jobb, s"],
           [[k["created_at"], UKEDAG[tid(k["created_at"]).isoweekday()], k["event"],
             k["conclusion"],
             "+".join(str(sekunder(j)) for j in jobber.get(k["id"], []))] for k in samle])
    print(f"Kjøringer av samle.yml i vinduet: {len(samle)} på {dager} døgn.")
    print()

    # ---------------------------------------------------------------- 0c
    print("### 0c. Mandagens innsamling og tirsdagens gjenkjøring: når de startet")
    print()
    alle_samle = sorted((k for k in kjoringer.values()
                         if fil(k) == "samle.yml" and k["event"] == "schedule"),
                        key=lambda k: k["created_at"])
    rader = []
    for k in alle_samle:
        t = tid(k["created_at"])
        c = siste_cron("samle.yml", t)
        aar, uke, _ = c.isocalendar()
        ferdig = max((tid(j["completed_at"]) for j in jobber.get(k["id"], [])
                      if j["completed_at"]), default=None)
        rader.append([f"{aar}-W{uke:02d}", f"{UKEDAG[c.isoweekday()]} {c:%d.%m %H:%M}",
                      f"{UKEDAG[t.isoweekday()]} {t:%d.%m %H:%M:%S}",
                      t1((t - c).total_seconds() / 3600),
                      f"{ferdig:%H:%M:%S}" if ferdig else "–", k["conclusion"], k["id"]])
    tabell(["ISO-uke", "cron (UTC)", "opprettet (UTC)", "timer etter cron", "jobben ferdig",
            "utfall", "kjøring"], rader)

    print("### 0c. Tilsynet: når den planlagte kjøringen startet, per ukedag")
    print()
    per_dag = defaultdict(list)
    for k in kjoringer.values():
        if fil(k) == "tilsyn.yml" and k["event"] == "schedule":
            t = tid(k["created_at"])
            per_dag[t.isoweekday()].append(t)
    rader = []
    for d in sorted(per_dag):
        v = sorted(per_dag[d], key=lambda t: (t.hour, t.minute, t.second))
        rader.append([UKEDAG[d], len(v), f"{v[0]:%H:%M}", f"{v[-1]:%H:%M}",
                      ", ".join(f"{t:%d.%m %H:%M}" for t in sorted(v))])
    tabell(["ukedag", "kjøringer", "tidligst", "senest", "hver kjøring (UTC)"], rader)

    print("### 0c. Forsinkelsen etter cron, alle planlagte kjøringer med kjent cron")
    print()
    # En workflow med flere cron-tider samme døgn kan ikke måles slik: en
    # kjøring som er mer forsinket enn avstanden til neste cron-tid, ville
    # blitt ført på den neste med en forsinkelse nær null.
    flere = sorted(f for f, c in CRON.items()
                   if len(c) > 1 and all(u is None for u, _, _ in c))
    print(f"Ikke med, fordi de har flere cron-tider per døgn: {', '.join(flere)}.")
    print()
    forsinket = defaultdict(list)
    for k in kjoringer.values():
        if k["event"] != "schedule" or fil(k) not in CRON or fil(k) in flere:
            continue
        t = tid(k["created_at"])
        c = siste_cron(fil(k), t)
        if c is not None:
            forsinket[(fil(k), f"{c:%H:%M}")].append((t - c).total_seconds() / 3600)
    rader = []
    for (f, c), v in sorted(forsinket.items(), key=lambda x: x[0][1]):
        v = sorted(v)
        rader.append([c, f, len(v), t1(v[0]), t1(statistics.median(v)), t1(v[-1])])
    tabell(["cron (UTC)", "workflow", "kjøringer", "minst, timer", "median, timer",
            "mest, timer"], rader)


if __name__ == "__main__":
    main()
