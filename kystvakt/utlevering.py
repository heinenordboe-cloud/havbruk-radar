"""Utleveringen: det eneste GitHub får se av kystvakt-1.

Tvungen kommando for brukeren `utlevering` (authorized_keys med
`restrict,command="..."`). Hva klienten ber om, ignoreres: ssh-kommando,
scp, sftp og portvideresending gir alle den samme JSON-en på stdout, og
ingenting annet. Serveren får ingen skrivetilgang til noe repo; GitHub
henter, og ais_manifest.py i kodrepoet skriver.

    {"skrevet": UTC,
     "disk": {"brukt_prosent", "ledig_bytes"},           /srv
     "kopi_sist_ok": UTC | null,                          kopi.py
     "regnskap": {kilde: {"timer", "tomme", "mangler"}},  siste 24 timer
     "manifester": [{"kilde", "dato", "innhold"}]}        lukkede døgn

Et regnskap er tomt når `meldinger` er 0, og det mangler når timen er
ferdig regnet (tre timer siden: én time, to timers venting på den andre
kilden, ti minutter) uten at fila finnes.

Et døgn er lukket for lytterne når UTC-datoen er forbi. For hulljegeren
først etter 15 døgn: den kan legge nye filer i et døgn så lenge
historikk-API-et har det (14 døgn).
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRV = Path(os.environ.get("AIS_SRV", "/srv"))  # miljøvariabel bare for prøvene
ROTER = {"bw": "ais/bw", "bw-etterhentet": "ais/bw/etterhentet", "5632": "ais5632/raa"}
LUKKET_ETTER = {"bw": 1, "bw-etterhentet": 15, "5632": 1}
REGNSKAP = ("bw", "5632")
MANIFEST_DOGN = 30
DATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def regnskap(rot: Path, naa: datetime) -> dict:
    siste = (naa - timedelta(hours=3, minutes=10)).replace(minute=0, second=0, microsecond=0)
    timer = [siste - timedelta(hours=i) for i in range(24)][::-1]
    tomme, mangler = [], []
    for t in timer:
        navn = t.strftime("%Y-%m-%dT%HZ")
        sti = rot / navn[:10] / f"{navn}.regnskap.json"
        if not sti.exists():
            mangler.append(navn)
        elif json.loads(sti.read_text()).get("meldinger", 0) == 0:
            tomme.append(navn)
    return {"timer": [timer[0].strftime("%Y-%m-%dT%HZ"), timer[-1].strftime("%Y-%m-%dT%HZ")],
            "tomme": tomme, "mangler": mangler}


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


def status(naa: datetime) -> dict:
    st = os.statvfs(SRV)
    brukt = 1 - st.f_bavail / st.f_blocks
    sist = SRV / "ais/kopi/SIST_OK"
    return {
        "skrevet": naa.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disk": {"brukt_prosent": round(100 * brukt, 1), "ledig_bytes": st.f_bavail * st.f_frsize},
        "kopi_sist_ok": sist.read_text().strip() if sist.exists() else None,
        "regnskap": {k: regnskap(SRV / ROTER[k], naa) for k in REGNSKAP},
        "manifester": manifester(naa),
    }


def main() -> None:
    naa = datetime.now(timezone.utc)
    json.dump(status(naa), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
