"""Utleveringen: det eneste GitHub får se av kystvakt-1.

Tvungen kommando for brukeren `utlevering` (authorized_keys med
`restrict,command="..."`). Hva klienten ber om, ignoreres: ssh-kommando,
scp, sftp og portvideresending gir alle den samme JSON-en på stdout, og
ingenting annet. Serveren får ingen skrivetilgang til noe repo; GitHub
henter, og ais_manifest.py i kodrepoet skriver.

    {"skrevet": UTC,
     "disk": {"brukt_prosent", "ledig_bytes"},           /srv
     "kopi_sist_ok": UTC | null,                          kopi.py
     "python": "3.14.4",                                  /usr/bin/python3
     "tjenester": {enhet: {"tilstand", "resultat"}},      systemctl
     "gjenoppretting": {...} | null,                      gjenopprett.py
     "regnskap": {kilde: {"timer", "tomme", "mangler",    siste 24 timer
                          "per_time"}},
     "manifester": [{"kilde", "dato", "innhold"}]}        lukkede døgn

Et regnskap er tomt når `meldinger` er 0, og det mangler når timen er
ferdig regnet (tre timer siden: én time, to timers venting på den andre
kilden, ti minutter) uten at fila finnes.

`per_time` er `meldinger` og `uten_mmsi` for hver time i vinduet som har
regnskap (fra 03.11.2026). Lytteren lagrer alt som kommer etter en 200
urørt, også en feilside, og tilsyn.py er rødt når andelen uten MMSI i en
time passerer grensen MALING-DRIFT 0c målte. Uten tallene her kan
tilsynet ikke se det.

`tjenester` er enhetene lyttere.sh slår på (TJENESTER), og tjenesten hver
timer starter, med `ActiveState` og `Result` fra systemd (fra 04.11.2026).
En timer kan stå «active» mens hver kjøring den starter, feiler; derfor
begge. tilsyn.py i datarepoet krever enhetene i TJENESTER «active» og
resultatet «success» for alle. Lista står her og ikke på GitHub-siden
fordi lyttere.sh installerer denne fila sammen med enhetene: et nytt
oppsett gir en ny liste i samme kjøring. Prøven i
tests/test_kystvakt_utlevering.py holder den lik skriptet.

`gjenoppretting` er siste månedlige prøve fra gjenopprett.py: én
tilfeldig fil hentet tilbake fra Storage Box og holdt mot manifestet
(fra 04.11.2026). null før første prøve.

`python` er versjonen til tolken som kjører denne fila, den samme
`/usr/bin/python3` som hver tjeneste starter. Tilsynet krever samme
versjon som i kodrepoet og i workflowene.

Et døgn er lukket for lytterne når UTC-datoen er forbi. For hulljegeren
først etter 15 døgn: den kan legge nye filer i et døgn så lenge
historikk-API-et har det (14 døgn).
"""
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRV = Path(os.environ.get("AIS_SRV", "/srv"))  # miljøvariabel bare for prøvene
ROTER = {"bw": "ais/bw", "bw-etterhentet": "ais/bw/etterhentet", "5632": "ais5632/raa"}
LUKKET_ETTER = {"bw": 1, "bw-etterhentet": 15, "5632": 1}
REGNSKAP = ("bw", "5632")
MANIFEST_DOGN = 30
DATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Enhetene lyttere.sh slår på (`systemctl enable`). ais-lytter.service
# (5631) installeres, men står av (stoppet av Heine 28.10.2026).
TJENESTER = ("ais-bw.service", "ais-5632.service", "ais-klokke.timer",
             "ais-regnskap-bw.timer", "ais-regnskap-5632.timer",
             "ais-kopi.timer", "ais-rydd.timer", "ais-hulljeger.timer",
             "ais-gjenopprett.timer")


def regnskap(rot: Path, naa: datetime) -> dict:
    siste = (naa - timedelta(hours=3, minutes=10)).replace(minute=0, second=0, microsecond=0)
    timer = [siste - timedelta(hours=i) for i in range(24)][::-1]
    tomme, mangler, per_time = [], [], {}
    for t in timer:
        navn = t.strftime("%Y-%m-%dT%HZ")
        sti = rot / navn[:10] / f"{navn}.regnskap.json"
        if not sti.exists():
            mangler.append(navn)
            continue
        r = json.loads(sti.read_text())
        per_time[navn] = {"meldinger": r.get("meldinger", 0),
                          "uten_mmsi": r.get("uten_mmsi", 0)}
        if per_time[navn]["meldinger"] == 0:
            tomme.append(navn)
    return {"timer": [timer[0].strftime("%Y-%m-%dT%HZ"), timer[-1].strftime("%Y-%m-%dT%HZ")],
            "tomme": tomme, "mangler": mangler, "per_time": per_time}


def manifester(naa: datetime) -> list[dict]:
    ut = []
    for kilde, rel in ROTER.items():
        rot = SRV / rel
        if not rot.is_dir():
            continue
        grense = (naa - timedelta(days=LUKKET_ETTER[kilde])).date().isoformat()
        eldst = (naa - timedelta(days=MANIFEST_DOGN)).date().isoformat()
        for dag in sorted(rot.iterdir()):
            if not (DATO.match(dag.name) and eldst <= dag.name <= grense):
                continue
            m = dag / "SHA256SUMS"
            if m.is_file():
                ut.append({"kilde": kilde, "dato": dag.name, "innhold": m.read_text()})
    return ut


def tjenester() -> dict:
    """{enhet: {"tilstand", "resultat"}} for TJENESTER og tjenesten hver
    timer starter. Svarer ikke systemd, får hver enhet tilstanden «ukjent»
    og feilen som resultat: tilsynet ser da hva som mangler, i stedet for
    at hele utleveringen faller."""
    enheter = [*TJENESTER, *(t.removesuffix(".timer") + ".service"
                             for t in TJENESTER if t.endswith(".timer"))]
    try:
        r = subprocess.run(["systemctl", "show", "-p", "Id,ActiveState,Result", *enheter],
                           capture_output=True, text=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError) as e:
        return {e_: {"tilstand": "ukjent", "resultat": f"{type(e).__name__}: {e}"[:200]}
                for e_ in enheter}
    ut = {}
    for blokk in r.stdout.strip().split("\n\n"):
        f = dict(linje.split("=", 1) for linje in blokk.splitlines() if "=" in linje)
        if f.get("Id") in enheter:
            ut[f["Id"]] = {"tilstand": f.get("ActiveState", ""), "resultat": f.get("Result", "")}
    for e_ in enheter:
        ut.setdefault(e_, {"tilstand": "ukjent", "resultat": "systemctl svarte ikke for enheten"})
    return ut


def status(naa: datetime) -> dict:
    st = os.statvfs(SRV)
    brukt = 1 - st.f_bavail / st.f_blocks
    sist = SRV / "ais/kopi/SIST_OK"
    prove = SRV / "ais/kopi/GJENOPPRETTING.json"
    return {
        "skrevet": naa.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disk": {"brukt_prosent": round(100 * brukt, 1), "ledig_bytes": st.f_bavail * st.f_frsize},
        "kopi_sist_ok": sist.read_text().strip() if sist.exists() else None,
        "python": platform.python_version(),
        "tjenester": tjenester(),
        "gjenoppretting": json.loads(prove.read_text()) if prove.exists() else None,
        "regnskap": {k: regnskap(SRV / ROTER[k], naa) for k in REGNSKAP},
        "manifester": manifester(naa),
    }


def main() -> None:
    naa = datetime.now(timezone.utc)
    json.dump(status(naa), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
