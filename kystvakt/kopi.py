"""Nattlig kopi av AIS-rådataene på kystvakt-1 til Storage Box.

    python3 kopi.py <kvitteringsmappe> <rot>...

Hver <rot> er en mappe under /srv (/srv/ais/bw, /srv/ais/bw/etterhentet,
/srv/ais5632/raa), og den samme relative stien brukes på boksen:
/srv/ais/bw/2026-10-29/x.txt.zst blir ais/bw/2026-10-29/x.txt.zst under
underkontoens hjemmemappe. Boksen er ssh-verten `boks` i ~/.ssh/config.

Hva som kopieres, per dagsmappe:

    filene som står i SHA256SUMS     ferdige, 0444, røres aldri igjen
    *.regnskap.json                  ferdige, 0444
    SHA256SUMS                       manifestet, som bare vokser

En .delvis står aldri i manifestet og kopieres derfor aldri.

Dataene kopieres med `rsync --ignore-existing`: en fil som finnes på
boksen, skrives ikke over, og ingenting slettes der (aldri `--delete`).
Rsync skriver til et midlertidig navn og døper om når fila er hel, så
et brudd midt i etterlater ikke en halv fil under det ekte navnet.

Så spør vi BOKSEN (1b-1): `sha256sum` kjøres der, mot filene slik de
ligger på dens disk. En fil er bekreftet når boksens sum er lik den
lokale fila sin og, for datafilene, lik linja i SHA256SUMS. Bekreftede
filer føres i

    <kvitteringsmappe>/<rot relativt til /srv>/<dato>.bekreftet

med boksens egen utskrift. Er én sum ulik, eller svarer ikke boksen:
ingen kvittering for den dagen, en logglinje, og kjøringen stopper der
med exit 1. Ryddejobben (rydd.py) leser ikke kvitteringene; den spør
boksen selv før den sletter. Kvitteringene er for tilsynet.

    <kvitteringsmappe>/SIST_OK       UTC-tid for siste kjøring uten feil
"""
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SRV = Path(os.environ.get("AIS_SRV", "/srv"))  # miljøvariabel bare for prøvene
BOKS = "boks"
DATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def logg(*a):
    print(*a, file=sys.stderr, flush=True)


def sha(sti: Path) -> str:
    h = hashlib.sha256()
    with open(sti, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def les_manifest(sti: Path) -> dict[str, str]:
    """navn -> sha256. En linje som ikke kan leses, er en feil, ikke støy."""
    ut = {}
    if not sti.exists():
        return ut
    for linje in sti.read_text().splitlines():
        s, _, navn = linje.partition("  ")
        if not re.fullmatch(r"[0-9a-f]{64}", s) or not navn:
            raise ValueError(f"{sti}: uleselig linje {linje!r}")
        ut[navn] = s
    return ut


def dagsmapper(rot: Path):
    return sorted(d for d in rot.iterdir() if d.is_dir() and DATO.match(d.name))


def filer_i(dag: Path) -> tuple[dict[str, str], list[str]]:
    """(datafiler fra manifestet, regnskapsfiler) i en dagsmappe."""
    manifest = les_manifest(dag / "SHA256SUMS")
    regnskap = sorted(p.name for p in dag.glob("*.regnskap.json"))
    return manifest, regnskap


def rsync(relative: list[str], ignorer_eksisterende: bool) -> None:
    """Sender stier relativt til SRV, med samme relative sti på boksen."""
    if not relative:
        return
    cmd = ["rsync", "-a", "--relative", "--from0", "--files-from=-", "--timeout=300"]
    if ignorer_eksisterende:
        cmd.append("--ignore-existing")
    else:
        cmd.append("--checksum")
    subprocess.run([*cmd, f"{SRV}/", f"{BOKS}:"], input="\0".join(relative).encode(),
                   check=True, timeout=6 * 3600)


def fjern_sha256(relative: list[str]) -> dict[str, str]:
    """sha256 slik boksen regner den. En fil boksen ikke har, mangler i svaret."""
    if not relative:
        return {}
    r = subprocess.run(["ssh", BOKS, "sha256sum", *relative], capture_output=True,
                       timeout=3600)
    ut = {}
    for linje in r.stdout.decode().splitlines():
        s, _, navn = linje.partition("  ")
        if re.fullmatch(r"[0-9a-f]{64}", s):
            ut[navn] = s
    return ut


class Stopp(Exception):
    pass


def kopier_rot(rot: Path, kvittering: Path) -> None:
    """Kopierer og bekrefter én rot. Første feil stopper alt (Stopp)."""
    rel_rot = rot.relative_to(SRV)
    for dag in dagsmapper(rot):
        try:
            manifest, regnskap = filer_i(dag)
        except ValueError as e:
            raise Stopp(str(e))
        kv = kvittering / rel_rot / f"{dag.name}.bekreftet"
        bekreftet = les_manifest(kv)
        lokal = {}
        for n in [*manifest, *regnskap, "SHA256SUMS"]:
            if not (dag / n).exists():
                # Ryddet bort lokalt (rydd.py) etter at boksen bekreftet den.
                if n in manifest and bekreftet.get(n) != manifest[n]:
                    raise Stopp(f"{dag / n}: står i manifestet, men finnes ikke")
                continue
            s = sha(dag / n)
            if n in manifest and s != manifest[n]:
                # Lokal fil og manifest er uenige: det er ikke en kopi vi
                # kan bekrefte, uansett hva boksen sier.
                raise Stopp(f"{dag / n}: lokal sha256 {s} ≠ manifestets {manifest[n]}")
            if bekreftet.get(n) != s:
                lokal[n] = s
        if not lokal:
            continue
        rel = {n: str(rel_rot / dag.name / n) for n in lokal}
        data = [r for n, r in rel.items() if n != "SHA256SUMS"]
        try:
            rsync(data, ignorer_eksisterende=True)
            if "SHA256SUMS" in rel:
                rsync([rel["SHA256SUMS"]], ignorer_eksisterende=False)
            fjern = fjern_sha256(list(rel.values()))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            raise Stopp(f"{dag}: {e}")
        for n, s in lokal.items():
            if fjern.get(rel[n]) != s:
                raise Stopp(f"{rel[n]}: boksen sier {fjern.get(rel[n], 'mangler')}, lokal {s}")
        kv.parent.mkdir(parents=True, exist_ok=True)
        with open(kv, "a") as f:
            f.writelines(f"{s}  {n}\n" for n, s in lokal.items())
        logg(f"[ok] {rel_rot}/{dag.name}: {len(lokal)} bekreftet på boksen")


def main() -> None:
    kvittering = Path(sys.argv[1])
    try:
        for r in sys.argv[2:]:
            kopier_rot(Path(r), kvittering)
    except Stopp as e:
        logg(f"[stopp] {e}")
        logg("[stopp] resten er ikke kopiert; ingenting er slettet")
        sys.exit(1)
    tmp = kvittering / ".SIST_OK.ny"
    tmp.write_text(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    tmp.replace(kvittering / "SIST_OK")


if __name__ == "__main__":
    main()
