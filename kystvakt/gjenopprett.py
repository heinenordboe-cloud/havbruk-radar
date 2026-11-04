"""Månedlig gjenopprettingsprøve: én tilfeldig AIS-fil tilbake fra Storage Box.

    python3 gjenopprett.py <kvitteringsmappe> <rot>...
    python3 gjenopprett.py --forvent <sha256> --ut <fil> <kvitteringsmappe> <rot>...

kopi.py har sendt hver ferdige fil til boksen og fått BOKSENS sha256
tilbake (`<kvitteringsmappe>/<rot relativt til /srv>/<dato>.bekreftet`).
Det sier at boksen har en fil med de bytene. Det sier ikke at vi får den
TILBAKE: summen er regnet der, av boksen. En backup ingen har lest
tilbake, er en påstand om en backup (samme skille som speil.yml).

Denne trekker én datafil blant alle som står både i en kvittering og i
dagsmappens SHA256SUMS, henter bytene med rsync til en midlertidig mappe
HER, og regner sha256 her. Fila er gjenopprettet når summen er lik
manifestets linje, den lytteren skrev da fila ble lukket. Trekningen er
tilfeldig (SystemRandom) over alle røtter og døgn, så prøvene dekker over
tid mer enn den samme fila. Ingenting skrives eller slettes på boksen.

Resultatet skrives til `<kvitteringsmappe>/GJENOPPRETTING.json`, som
utlevering.py leverer til GitHub, og ais_manifest.py holder summen mot
manifestet i datarepoet:

    {"tidspunkt": UTC, "kilde", "dato", "fil", "bytes",
     "sha256": regnet her, "manifest": linja i SHA256SUMS,
     "ok": true|false, "grunn": tekst}

Exit 1 når prøven feiler.

FEILEN MED VILJE (CLAUDE.md §8): `--forvent` holder fila mot en oppgitt
sum i stedet for manifestets, og `--ut` skriver resultatet et annet sted
enn kvitteringsmappa. En sum som ikke stemmer, skal gi `ok: false` og
exit 1, uten at tilsynet blir rødt av at noen prøvde varselet.
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kopi  # noqa: E402
from utlevering import ROTER  # noqa: E402

RESULTAT = "GJENOPPRETTING.json"
KILDE = {rel: kilde for kilde, rel in ROTER.items()}


def kandidater(kvittering: Path, rot: Path) -> list[tuple[str, str, str]]:
    """(dato, fil, manifestets sha256) for datafilene i roten som både
    står i dagens SHA256SUMS og er bekreftet på boksen med samme sum."""
    ut = []
    rel = rot.relative_to(kopi.SRV)
    for kv in sorted((kvittering / rel).glob("*.bekreftet")):
        dato = kv.name.removesuffix(".bekreftet")
        manifest = kopi.les_manifest(rot / dato / "SHA256SUMS")
        bekreftet = kopi.les_manifest(kv)
        ut += [(dato, n, s) for n, s in sorted(manifest.items()) if bekreftet.get(n) == s]
    return ut


def hent(rel: str, mappe: Path) -> Path:
    """Bytene fra boksen til `mappe`, med samme filnavn."""
    subprocess.run(["rsync", "-a", "--timeout=300", f"{kopi.BOKS}:{kopi.FJERN_ROT}/{rel}",
                    f"{mappe}/"], check=True, timeout=3600)
    return mappe / Path(rel).name


def prove(kvittering: Path, rotter: list[Path], forvent: str | None = None,
          trekk=random.SystemRandom().choice) -> dict:
    naa = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        alle = [(rot, *k) for rot in rotter for k in kandidater(kvittering, rot)]
    except (ValueError, OSError) as e:
        return {"tidspunkt": naa, "ok": False, "grunn": f"kvittering eller manifest: {e}"[:300]}
    if not alle:
        return {"tidspunkt": naa, "ok": False,
                "grunn": "ingen bekreftet datafil å hente i noen kvittering"}
    rot, dato, fil, manifest = trekk(alle)
    rel = rot.relative_to(kopi.SRV).as_posix()
    ut = {"tidspunkt": naa, "kilde": KILDE.get(rel, rel), "dato": dato, "fil": fil,
          "manifest": manifest}
    with tempfile.TemporaryDirectory(prefix="gjenopprett-") as mappe:
        try:
            sti = hent(f"{rel}/{dato}/{fil}", Path(mappe))
            ut["bytes"] = sti.stat().st_size
            ut["sha256"] = kopi.sha(sti)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            return {**ut, "ok": False, "grunn": f"boksen leverte ikke fila: {e}"[:300]}
    mot = forvent or manifest
    if ut["sha256"] != mot:
        hva = "den oppgitte summen (--forvent)" if forvent else "manifestets linje"
        return {**ut, "ok": False,
                "grunn": f"sha256 for fila fra boksen er {ut['sha256']}, ikke {hva} {mot}"}
    return {**ut, "ok": True, "grunn": "lik manifestet"}


def main(argv: list[str]) -> int:
    forvent = ut_fil = None
    while argv and argv[0] in ("--forvent", "--ut"):
        flagg, verdi, argv = argv[0], argv[1], argv[2:]
        if flagg == "--forvent":
            forvent = verdi
        else:
            ut_fil = Path(verdi)
    kvittering, rotter = Path(argv[0]), [Path(r) for r in argv[1:]]
    if forvent and not ut_fil:
        kopi.logg("[stopp] --forvent krever --ut: en prøve med vilje skal ikke stå "
                  "som månedens resultat")
        return 2
    r = prove(kvittering, rotter, forvent)
    maal = ut_fil or kvittering / RESULTAT
    tmp = maal.with_name(f".{maal.name}.ny")
    tmp.write_text(json.dumps(r, ensure_ascii=False) + "\n")
    os.chmod(tmp, 0o644)
    tmp.replace(maal)
    kopi.logg(f"[{'ok' if r['ok'] else 'FEIL'}] {r.get('kilde', '?')}/{r.get('dato', '?')}/"
              f"{r.get('fil', '?')}: {r['grunn']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
