"""Ryddejobben: sletter lokale AIS-filer som boksen har, og som er gamle nok.

    python3 rydd.py [--torrkjor] <dager> <rot>...

`--torrkjor` stiller boksen de samme spørsmålene og skriver
`[ville slettet]` der den ellers ville slettet. Ingenting fjernes.

Kjøres som `ais` for /srv/ais/bw og /srv/ais/bw/etterhentet. 5632 ryddes
ikke: den leverer lite, og ryddingen skulle da trengt skrivetilgang til
en annen kildes mapper (avgjort 29.10.2026).

En fil slettes bare når ALT dette holder:

  - den står i dagsmappens SHA256SUMS (en datafil, ferdig skrevet)
  - lokal sha256 er lik manifestets
  - BOKSEN svarer nå, ved denne kjøringen, med samme sha256
  - den ble skrevet her for mer enn <dager> døgn siden

Det siste er fila sin mtime, ikke datoen i mappenavnet. Spørsmålet er
hvor lenge VI har hatt en lokal kopi i reserve (1b-1), ikke hvilket døgn
i verden fila handler om: hulljegeren legger inn timer som er 13 døgn
gamle samme natt den henter dem, og de skal få like lang reserve som
alle andre. Veggklokke, fordi den sammenlignes med et tidsstempel på
disken.

Kopijobbens kvitteringer leses ikke. En kvittering sier at boksen hadde
fila DA; ryddingen trenger å vite at den har den NÅ.

Regnskap, manifester og .delvis røres aldri.

En fil boksen ikke bekrefter, blir liggende, og jobben ender med exit 1
hver natt til noen har sett på det. Kopijobben sender ikke en fil den
alt har bekreftet på nytt: at boksen har mistet noe, er en hendelse,
ikke noe en nattjobb skal reparere i det stille.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kopi  # noqa: E402

sys.path.pop(0)


def rydd_rot(rot: Path, dager: float, naa: float, torrkjor: bool = False) -> tuple[int, int]:
    """(slettet, beholdt fordi boksen ikke bekreftet). I tørrkjøring er
    «slettet» det som ville blitt slettet."""
    slettet = beholdt = 0
    rel_rot = rot.relative_to(kopi.SRV)
    for dag in kopi.dagsmapper(rot):
        manifest = kopi.les_manifest(dag / "SHA256SUMS")
        gamle = {n: s for n, s in manifest.items()
                 if (dag / n).exists() and naa - (dag / n).stat().st_mtime > dager * 86400}
        if not gamle:
            continue
        rel = {n: str(rel_rot / dag.name / n) for n in gamle}
        fjern = kopi.fjern_sha256(list(rel.values()))
        for n, s in gamle.items():
            lokal = kopi.sha(dag / n)
            if lokal != s:
                kopi.logg(f"[beholdt] {dag / n}: lokal sha256 ≠ manifestet")
                beholdt += 1
            elif fjern.get(rel[n]) != s:
                kopi.logg(f"[beholdt] {dag / n}: boksen sier {fjern.get(rel[n], 'mangler')}")
                beholdt += 1
            elif torrkjor:
                kopi.logg(f"[ville slettet] {dag / n}")
                slettet += 1
            else:
                (dag / n).unlink()
                kopi.logg(f"[slettet] {dag / n}")
                slettet += 1
    return slettet, beholdt


def main() -> None:
    a = sys.argv[1:]
    torrkjor = a[:1] == ["--torrkjor"]
    if torrkjor:
        a = a[1:]
    dager = float(a[0])
    naa = time.time()
    slettet = beholdt = 0
    for r in a[1:]:
        s, b = rydd_rot(Path(r), dager, naa, torrkjor)
        slettet, beholdt = slettet + s, beholdt + b
    kopi.logg(f"[ferdig] {slettet} {'ville blitt slettet (tørrkjøring)' if torrkjor else 'slettet'}, "
              f"{beholdt} beholdt fordi boksen ikke bekreftet")
    sys.exit(1 if beholdt else 0)


if __name__ == "__main__":
    main()
