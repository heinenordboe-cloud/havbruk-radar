"""Fasiten: Fiskeridirektoratets fordeling mot pakke 1 og pakke 2.

    python fasit_havbruksfond.py                 # fasitdagen
    python fasit_havbruksfond.py --kvitter       # når fasit-2026.md er lest
    python fasit_havbruksfond.py --torrkjor 2025 --ut ~/kystloggen-utkast/L/torrkjoring --sider

## Fasitdagen

`havbruksfond.yml` i datarepoet arkiverer Fiskeridirektoratets side,
hvert vedlegg den lenker, og pressemeldingene om fondet, tre ganger i
døgnet (MALING-HAVBRUKSFOND A6). Når fordelingen er blant kroppene, gjør
én kjøring av denne fila resten, i denne rekkefølgen:

1. FORSEGLINGENE FØRST. For pakke 1 og pakke 2: summen av fila mot summen
   som ble forseglet, summen i .ots-fila, og fila hentet ut av hver commit
   den ble forseglet i. Er én av dem feil, stopper kjøringen med exit 2:
   et anslag som er endret etter seglet, er ikke anslaget. Stempelet
   oppgraderes på en KOPI, som i `stempel.py`, og merkleroten for hver
   Bitcoin-blokk det peker på, holdes mot to blokkutforskere. `ots
   verify` prøves også. Uten en Bitcoin-node på maskinen stopper den der,
   og det står i fila.
2. TABELLEN fra arkivkroppen, med sti og sha256. Regnearket først, kjent
   på tittelen i «Utbetalingsoversikt»; pressemeldingen når regnearket
   ikke er arkivert. Finnes begge, holdes beløpene mot hverandre.
3. PAKKE 1 etter de fire leddene i `feil_hvis`, ordrett, og PAKKE 2 etter
   sine ni påstander. En påstand som trenger regnearket, venter når bare
   pressemeldingen er der.
4. AVVIKENE per kommune og fylkeskommune, hvert i én av tre grupper.
5. UTFALLET i en NY fil, `data/havbruksfond/fasit-<år>.json` og `.md`.
   Samme innhold gir ingen ny fil, et annet gir `fasit-<år>.2.json`.
   Ingen fil i predictions/ røres.
6. KOMMUNESIDENE viser Fiskeridirektoratets beløp, med kilde og dato, ved
   siden av registerets andel når fila er kvittert. `--kvitter` skriver
   `lest-fasit-<år>.json` med summen av nøyaktig den fila
   (`havbruksfond.lest_fasit()`), og neste bygg viser den.

Exit 0 når fasiten er skrevet eller ingenting er kommet, 2 når et segl
ikke holder, 3 når noe er kommet som ikke kan leses: et nytt vedlegg uten
den kjente tittelen, eller en tabell i en form vi ikke kjenner. Da skal et
menneske se på kroppen.

## De tre gruppene

Et avvik er en kommune der Fiskeridirektoratets MTB skiller seg fra den
pakke 2 forventet med mer enn 1 t, eller andelen med mer enn 0,005
prosentpoeng (tersklene i P2-1, P2-2 og P2-8). Avviket føres tilbake til
lokalitetene bak det, og hver lokalitet havner i én gruppe:

    grensetilfellene     lokalitetene pakke 2 navnga (P2-3 til P2-6). Der
                         avgjør Fiskeridirektoratets praksis, og det sa vi
                         på forhånd.
    registeret eller     tallet deres kan ikke komme ut av registeret slik
    Fiskeridirektoratets vi leste det 31.08 og 07.09: en lokalitet
    grunnlag             registeret ikke hadde, en annen kommune enn
                         registerets, en MTB som ikke står i noe felt.
    vår egen feil        resten: en lokalitet de tar med og filteret holdt
                         ute (eller omvendt), en MTB som er ett av feltene
                         men ikke det vi valgte, en lokalitet de deler og
                         vi ikke deler.

Kommunen får gruppen med flest tonn. Er avviket bare i andelen, kommer
det av nevneren, og kommunen får gruppen som flytter summen mest.

TVIL GÅR MOT OSS. «Registeret eller Fiskeridirektoratets grunnlag» er en
påstand om en tredjepart, og den skal kunne vises av kroppene (CLAUDE.md
1b-6). Uten lokalitetslista kan den ikke det. Da føres pakke 2s gruppe G
til grensetilfellene, U (samme tall som Fiskeridirektoratets egne per
01.09.2025) til grunnlaget og E til vår egen feil, og fila sier at
grupperingen er foreløpig.

## Tørrkjøringen

`--torrkjor 2025` kjører hele kjeden mot kroppene for 2025 (A3):
regnearket og pressemeldingen 10.11.2025, lest som om de var årets. Den
skriver til `--ut`, aldri i datarepoet, og hver fil sier TØRRKJØRING
øverst. Med `--sider` bygges kommunesidene med beløpene i
`--ut/nettsted/`, merket på hver side. Ingenting av det publiseres.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import havbruksfond as h
import skaar_havbruksfond as s
from core import paths

# Tersklene, slik pakkene sier dem.
P1_PP = 0.05          # pakke 1, ledd (3) og (4)
P2_MTB = 1.0          # P2-1 og P2-2, tonn
P2_PP = 0.005         # P2-7 og P2-8
P2_9_PP = 0.001       # P2-9, rundt 20 %
P2_DELING = 0.001     # P2-6, brøk
LIK_T = 0.5           # tonn: under dette er en lokalitet lik hos oss og dem
FLYT = 1e-9           # flyttall rundt en terskel

GRUPPER = {"G": "grensetilfellene",
           "R": "registeret eller Fiskeridirektoratets grunnlag",
           "V": "vår egen feil"}
# Ved likt antall tonn: oss først (se «TVIL GÅR MOT OSS»).
TVIL = ("V", "R", "G")

TORRKJORING = ("TØRRKJØRING — ikke en fasit. Kroppene for {aar} er lest som "
               "om de var årets, og holdt mot anslagene for 2026.")
UTFORSKERE = ("https://blockstream.info/api", "https://mempool.space/api")
# Vedleggene som lå på siden da sesongen begynte (A1, 12.10.2026). Et
# vedlegg som kommer etter, og som ikke har den kjente tittelen, er
# kanskje årets fordeling i en ny form.
SESONGSTART = "2026-10-12"


# ---------------------------------------------------------- forseglingene


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def _ots(*args: str) -> subprocess.CompletedProcess | None:
    """`ots`-klienten, med rotsertifikatene fra certifi (lokalt-miljo:
    Python fra python.org har dem ikke). None når klienten mangler."""
    env = dict(os.environ)
    if "SSL_CERT_FILE" not in env:
        try:
            import certifi
            env["SSL_CERT_FILE"] = certifi.where()
        except ImportError:
            pass
    try:
        return subprocess.run(["ots", *args], capture_output=True, text=True,
                              timeout=180, env=env)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# `ots --no-bitcoin verify` sier hva som må sjekkes når ingen node svarer:
# «To verify manually, check that Bitcoin block N has merkleroot X».
# Samme kjede som RUNBOOK, «Verifisere et stempel», punkt 2 og 3.
_MANUELT = re.compile(r"check that Bitcoin block (\d+) has merkleroot ([0-9a-f]{64})")


def merklerot(hoyde: int) -> dict[str, dict]:
    """Merkleroten og tiden for blokk `hoyde` hos hver blokkutforsker.
    En utforsker som ikke svarer, står med feilen."""
    import httpx
    ut = {}
    for base in UTFORSKERE:
        navn = base.split("/")[2]
        try:
            with httpx.Client(timeout=20.0) as k:
                r = k.get(f"{base}/block-height/{hoyde}")
                r.raise_for_status()
                b = k.get(f"{base}/block/{r.text.strip()}")
                b.raise_for_status()
                b = b.json()
            ut[navn] = {"merkle_root": b["merkle_root"],
                        "tid": dt.datetime.fromtimestamp(b["timestamp"], dt.timezone.utc)
                        .isoformat(timespec="seconds")}
        except Exception as e:                          # noqa: BLE001
            ut[navn] = {"feil": f"{type(e).__name__}: {e}"[:200]}
    return ut


def bitcoin(fil: Path) -> dict:
    """Stempelet for `fil`, oppgradert på en KOPI og holdt mot blokkene.

    Originalen røres aldri: `ots upgrade` flytter fila den får til `.bak`
    og skriver over navnet (stempel.py). `ots verify` prøves først; med
    en Bitcoin-node er den hele svaret. Uten en sier den det, og svaret
    står ordrett. Da gir `ots --no-bitcoin verify` blokkene og
    merklerøttene, og de holdes mot to blokkutforskere.
    """
    ut: dict = {"blokker": [], "ots_verify": "", "oppgradert": False}
    with tempfile.TemporaryDirectory() as t:
        kopi = Path(t) / (fil.name + ".ots")
        shutil.copy2(Path(str(fil) + ".ots"), kopi)
        r = _ots("upgrade", str(kopi))
        if r is None:
            ut["ots_verify"] = "ots-klienten finnes ikke på maskinen"
            return ut
        ut["oppgradert"] = "Timestamp complete" in (r.stdout + r.stderr)
        v = _ots("verify", "-f", str(fil), str(kopi))
        manuelt = _ots("--no-bitcoin", "verify", "-f", str(fil), str(kopi))
    if v is not None:
        linjer = [x for x in (v.stdout + v.stderr).splitlines() if x.strip()]
        ut["ots_verify"] = f"exit {v.returncode}: " + (linjer[-1] if linjer else "")
    for hoyde, rot in _MANUELT.findall(manuelt.stdout + manuelt.stderr if manuelt else ""):
        svar = merklerot(int(hoyde))
        lik = [n for n, x in svar.items() if x.get("merkle_root") == rot]
        ulik = [n for n, x in svar.items() if x.get("merkle_root") not in (None, rot)]
        ut["blokker"].append({"hoyde": int(hoyde), "merkle_root": rot, "lik_hos": lik,
                              "ulik_hos": ulik,
                              "tid": next((x["tid"] for x in svar.values() if "tid" in x), ""),
                              "svar": svar})
    ut["blokker"].sort(key=lambda b: b["hoyde"])
    return ut


def forseglinger(rot: Path = h.ROT, nett: bool = True) -> list[dict]:
    """Hver forsegling prøvd: summen nå, summen i .ots, fila i hver commit.

    `brutt` er det som stopper fasiten: en sum som ikke er den forseglede,
    en .ots for en annen fil, eller en commit der fila er en annen. En
    commit som ikke finnes her (havbruk-analyse er privat og ligger ikke
    i en runner), er ikke prøvd, og det står.
    """
    ut = []
    for f in h.FORSEGLINGER:
        sti = rot / f["fil"]
        naa = hashlib.sha256(sti.read_bytes()).hexdigest()
        ots = h.ots_sum(Path(str(sti) + ".ots").read_bytes(), f["fil"] + ".ots")
        r = {"pakke": f["pakke"], "fil": f["fil"], "forseglet": f["forseglet"],
             "sha256_forseglet": f["sha256"], "sha256": naa, "ots_sum": ots,
             "commits": [], "brutt": []}
        if naa != f["sha256"]:
            r["brutt"].append(f"{f['fil']} har sha256 {naa}, forseglet {f['sha256']}")
        if ots != f["sha256"]:
            r["brutt"].append(f"{f['fil']}.ots er stemplet for {ots}")
        for repo_navn, commit, hva in f["commits"]:
            # Kodrepoet er `rot` uansett hva mappa heter (`kode/` i en runner).
            repo = rot if repo_navn == "havbruk-radar" else rot.parent / repo_navn
            rel = f["fil"] + (".ots" if hva == "ots" else "")
            c = {"repo": repo_navn, "commit": commit, "fil": rel}
            blob = _git(repo, "cat-file", "blob", f"{commit}:{rel}") if repo.is_dir() else None
            if blob is None or blob.returncode != 0:
                c["prøvd"] = False
                c["merknad"] = ("repoet ligger ikke her" if blob is None
                                else "commiten eller fila finnes ikke her")
            else:
                sum_ = (h.ots_sum(blob.stdout, rel) if hva == "ots"
                        else hashlib.sha256(blob.stdout).hexdigest())
                c.update({"prøvd": True, "sum": sum_, "lik": sum_ == f["sha256"],
                          "tid": _git(repo, "show", "-s", "--format=%cI", commit)
                          .stdout.decode().strip()})
                pa = _git(repo, "merge-base", "--is-ancestor", commit, "origin/main")
                c["paa_origin_main"] = pa.returncode == 0
                if not c["lik"]:
                    r["brutt"].append(f"{repo_navn} {commit[:7]}:{rel} har summen {sum_}")
            r["commits"].append(c)
        if nett:
            r["bitcoin"] = bitcoin(sti)
        ut.append(r)
    return ut


# ------------------------------------------------------------- tabellen


@dataclass
class Tabell:
    """Fordelingen slik én kropp oppgir den."""
    form: str                          # "regneark" eller "pressemelding"
    kropp: h.Kropp
    logg: dict                         # posten i arkivloggen
    kommuner: dict[str, dict]          # komnr -> {navn, totalt, nyklarert, ordinar}
    fylker: dict[str, dict]            # fylkesnr -> {navn, belop}
    nyklarert_kolonne: bool | None     # None: formen viser det ikke
    kommune_mtb: dict[str, float] | None = None
    lokaliteter: list[dict] | None = None
    dato: str = ""                     # pressemeldingens egen dato
    merknader: list[str] = field(default_factory=list)


class Uleselig(ValueError):
    """Noe er arkivert som kan være fordelingen, men lar seg ikke lese."""


def loggpost(sha: str) -> dict:
    """Første post i arkivloggene for kroppen med summen `sha`: adressen,
    når vi hentet den, og `published_at` når kilden sa det."""
    for sti in sorted((paths.ARKIV_DIR / "havbruksfondet").glob("*.logg.json")):
        try:
            poster = json.loads(sti.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for p in poster:
            if p.get("sha256") == sha:
                return {k: p.get(k, "") for k in ("hva", "url", "observed_at",
                                                  "fetched_at", "published_at")}
    return {}


def _hode(rader: list[list[str]], *krav: tuple[str, ...], innen: int = 6
          ) -> tuple[int, dict[str, int]] | None:
    """(radnummer, {navn: kolonne}) for første rad som har ett navn fra hver
    gruppe i `krav`. Navnene sammenlignes uten store/små bokstaver."""
    for i, rad in enumerate(rader[:innen]):
        hode = [c.strip().upper() for c in rad]
        funnet = {}
        for navn in krav:
            j = next((hode.index(n.upper()) for n in navn if n.upper() in hode), None)
            if j is None:
                break
            funnet[navn[0]] = j
        else:
            return i, funnet
    return None


def kommune_mtb(ark: dict[str, list[list[str]]]) -> dict[str, float]:
    """MTB per kommune i arket «Kommuner»: «KAP REG» i 2025, «Kapasitet» i
    2024. Det er kolonnen P2-1 og P2-2 avgjøres mot."""
    rader = ark["Kommuner"]
    funn = _hode(rader, ("LOK_KOMNR", "KOMNR"), ("KAP REG", "KAPASITET", "KAP", "MTB"))
    if funn is None:
        raise ValueError("fant ikke LOK_KOMNR og kapasiteten i «Kommuner»")
    i, kol = funn
    nr, kap = kol["LOK_KOMNR"], kol["KAP REG"]
    return {r[nr].strip(): float(r[kap]) for r in rader[i + 1:]
            if len(r) > max(nr, kap) and r[nr].strip().isdigit() and r[kap].strip()}


def regneark(aar: int) -> Tabell:
    """Regnearket for `aar`. FileNotFoundError når det ikke er arkivert,
    `Uleselig` når kommune- eller fylkestabellen ikke kan leses. Det som
    mangler utover dem (MTB per kommune, lokalitetslista), står som en
    merknad, og påstandene som trenger det, venter."""
    ark, kropp = h.regneark(aar)
    try:
        kommuner = s.kommunetall(ark)
        fylker = s.fylkestall(ark)
    except (KeyError, ValueError, IndexError) as e:
        raise Uleselig(f"{kropp.navn}: {type(e).__name__}: {e}") from e
    t = Tabell("regneark", kropp, loggpost(kropp.sha256), kommuner, fylker,
               nyklarert_kolonne=_hode(ark["Utbetalingsoversikt"], ("KOMNR",),
                                       ("ANDEL NYKLARERT",)) is not None)
    try:
        t.kommune_mtb = kommune_mtb(ark)
    except (KeyError, ValueError) as e:
        t.merknader.append(f"MTB per kommune ikke lest: {e}")
    try:
        t.lokaliteter = h.lokalitetsark(ark)
    except (KeyError, ValueError) as e:
        t.merknader.append(f"lokalitetslista ikke lest: {e}")
    if t.lokaliteter and max(r["andel"] for r in t.lokaliteter) > 1.5:
        # «Andel i %» har vært en brøk (1 for en hel lokalitet). Står den
        # i prosent, deles den, og det sies.
        for r in t.lokaliteter:
            r["andel"] /= 100
        t.merknader.append("«Andel i %» står i prosent, ikke som brøk; delt på 100")
    return t


_TABELL = re.compile(r"Utbetalinger fra Havbruksfondet (\d{4})\s+KOMMUNE\s+TOTALT")
_PAR = re.compile(r"\s*(\D+?)\s+(\d{1,3}(?: \d{3})*)(?=\s+\D|\s*$)")


def pressemelding(aar: int, navn: dict[str, str], fylkesnavn: dict[str, str]) -> Tabell:
    """Pressemeldingen med fordelingen for `aar`, fra arkivet.

    Formen er den MÅLTE fra 10.11.2025 (A3): «Utbetalinger fra
    Havbruksfondet <år> KOMMUNE TOTALT», navn og beløp, så «Fylkeskommune
    Utbetaling» og «Totalt: … kroner». Navnene slås opp i pakke 2s
    tabell. NTB-formen er ikke sett med en tabell i (ingen kropp fra NTB
    er arkivert); har den en annen form, er den `Uleselig`, ikke tom.
    """
    from arkiver_havbruksfond import pressedato
    from core.karantene import synlig_tekst
    # Fordelingen har kommet om høsten hvert år (21.10.2024, 10.11.2025).
    # Meldingene om fondet fra våren og sommeren handler om salget, ikke
    # om fordelingen, og skal ikke gi «les for hånd» (målt: 19.06 og
    # 10.09.2026 ligger i arkivet). Filnavnet er meldingens egen dato.
    kandidater = sorted(
        [p for m in ("regjeringen-pressemeldinger", "ntb-pressemeldinger")
         for p in (paths.ARKIV_DIR / m).glob(f"{aar}-*.bin.gz")
         if p.name[:10] >= f"{aar}-10-01"], reverse=True)
    om_fondet = []
    for sti in kandidater:
        data = gzip.open(sti, "rb").read()
        tekst = synlig_tekst(data)
        if "havbruksfond" not in tekst.lower():
            continue
        m = _TABELL.search(tekst)
        if not m or m.group(1) != str(aar):
            om_fondet.append(sti)
            continue
        kropp = h.Kropp(sti.relative_to(paths.ARKIV_DIR).as_posix(),
                        hashlib.sha256(data).hexdigest(), sti, dato=sti.name[:10])
        try:
            fhode = "Fylkeskommune Utbetaling"
            kom_t = tekst[m.end():tekst.index(fhode)]
            fyl_t = tekst[tekst.index(fhode) + len(fhode):tekst.index("Totalt:")]
            totalt = int(re.search(r"Totalt:\s*([\d ]+?)\s*kroner", tekst).group(1).replace(" ", ""))
        except (ValueError, AttributeError) as e:
            raise Uleselig(f"{kropp.navn}: tabellen har ikke formen fra 2025 ({e})") from e
        nr = {v: k for k, v in navn.items()}
        fnr = {v: k for k, v in fylkesnavn.items()}
        t = Tabell("pressemelding", kropp, loggpost(kropp.sha256), {}, {},
                   nyklarert_kolonne=None, dato=pressedato(data))
        for n, b in _PAR.findall(kom_t):
            n = n.strip()
            t.kommuner[nr.get(n, f"?{n}")] = {"navn": n, "totalt": float(b.replace(" ", "")),
                                              "nyklarert": 0.0, "ordinar": 0.0}
        for n, b in _PAR.findall(fyl_t):
            t.fylker[fnr.get(n.strip(), f"?{n.strip()}")] = {
                "navn": n.strip(), "belop": float(b.replace(" ", ""))}
        if ukjente := [k for k in t.kommuner if k.startswith("?")]:
            t.merknader.append(f"navn uten treff i pakke 2: {ukjente}")
        sum_ = sum(k["totalt"] for k in t.kommuner.values()) + sum(
            f["belop"] for f in t.fylker.values())
        if abs(sum_ - totalt) > len(t.kommuner) + len(t.fylker):
            raise Uleselig(f"{kropp.navn}: radene summerer til {sum_:.0f}, «Totalt:» er {totalt}")
        return t
    if om_fondet:
        raise Uleselig(f"pressemelding(er) om fondet fra {aar} uten tabellen i kjent form: "
                       f"{[p.relative_to(paths.ARKIV_DIR).as_posix() for p in om_fondet]}")
    raise FileNotFoundError(f"ingen pressemelding med fordelingen for {aar} i arkivet")


def nye_vedlegg(aar: int, kjente: set[str]) -> list[dict]:
    """Vedlegg arkivert første gang etter `SESONGSTART` som ikke er en kjent
    kropp. Er årets regneark ikke funnet på tittelen, er det her det kan
    ligge."""
    ut, sett = [], set()
    for sti in sorted((paths.ARKIV_DIR / "havbruksfondet").glob("*.logg.json")):
        if sti.name[:10] <= SESONGSTART:
            continue
        for p in json.loads(sti.read_text(encoding="utf-8")):
            if (p.get("hva") == "vedlegg" and p.get("ny") and p.get("sha256")
                    and p["sha256"] not in kjente and p["sha256"] not in sett):
                sett.add(p["sha256"])
                ut.append({"url": p.get("url", ""), "sha256": p["sha256"],
                           "observed_at": p.get("observed_at", "")})
    return ut


def les_tabellen(aar: int, p2: dict) -> tuple[Tabell | None, Tabell | None, list[str]]:
    """(regnearket, pressemeldingen, det som ikke kunne leses)."""
    uleselig = []
    ark = pm = None
    try:
        ark = regneark(aar)
    except FileNotFoundError:
        if aar == h.AAR:
            for v in nye_vedlegg(aar, set()):
                uleselig.append(f"nytt vedlegg uten den kjente tittelen: {v['url']} "
                                f"(sha256 {v['sha256'][:16]}…, arkivert {v['observed_at']})")
    except Uleselig as e:
        uleselig.append(f"regnearket: {e}")
    try:
        pm = pressemelding(aar, {k: v["navn"] for k, v in p2["kommuner"].items()},
                           {k: v["navn"] for k, v in p2["fylker"].items()})
    except FileNotFoundError:
        pass
    except Uleselig as e:
        uleselig.append(f"pressemeldingen: {e}")
    return ark, pm, uleselig


def mot_hverandre(ark: Tabell, pm: Tabell) -> dict:
    """Pressemeldingen mot regnearket, som i A3: beløpene per kommune og
    fylkeskommune, avrundet til krone i meldingen."""
    k = sorted(nr for nr in set(ark.kommuner) | set(pm.kommuner)
               if abs(ark.kommuner.get(nr, {}).get("totalt", 0)
                      - pm.kommuner.get(nr, {}).get("totalt", 0)) >= 1)
    f = sorted(nr for nr in set(ark.fylker) | set(pm.fylker)
               if abs(ark.fylker.get(nr, {}).get("belop", 0)
                      - pm.fylker.get(nr, {}).get("belop", 0)) >= 1)
    return {"pressemelding": pm.kropp.navn, "sha256": pm.kropp.sha256, "dato": pm.dato,
            "kommuner_ulike": k, "fylker_ulike": f}


# ---------------------------------------------------------------- pakke 1


def _ledd(tekst: str) -> dict[int, str]:
    """De nummererte leddene i `feil_hvis`, ordrett, med linjeskiftene
    YAML-en har brettet bort."""
    return {int(m.group(1)): " ".join(m.group(2).split())
            for m in re.finditer(r"\((\d)\)\s*(.*?)(?=\s*\(\d\)|\s*Mekanismen|\Z)", tekst, re.S)}


def _andeler(t: Tabell) -> tuple[dict[str, float], dict[str, float]]:
    sk = sum(k["totalt"] for k in t.kommuner.values())
    sf = sum(f["belop"] for f in t.fylker.values())
    return ({nr: k["totalt"] / sk for nr, k in t.kommuner.items()},
            {nr: f["belop"] / sf for nr, f in t.fylker.items()})


def pakke1(t: Tabell, regneark_lest: bool) -> dict:
    """De fire leddene i `feil_hvis`, hvert for seg, og utfallet.

    Ett ledd som slår til, er nok (anslagets egne ord). Ledd 1 handler om
    en kolonne i regnearket og venter når bare pressemeldingen er lest.
    """
    import yaml
    tekst = h.ANSLAG.read_text(encoding="utf-8")
    p = yaml.safe_load(re.search(r"```yaml\n(.*?)```", tekst, re.S).group(1))["prediksjoner"][0]
    ordrett = _ledd(p["feil_hvis"])
    a2 = h.anslaget()
    andel_k, andel_f = _andeler(t)

    def avvik(fasit: dict, anslag: dict) -> list[dict]:
        return sorted(({"nr": nr, "fasit": fasit[nr], "anslag": anslag[nr],
                        "avvik_pp": (fasit[nr] - anslag[nr]) * 100}
                       for nr in set(fasit) & set(anslag)
                       if abs(fasit[nr] - anslag[nr]) * 100 > P1_PP + FLYT),
                      key=lambda r: -abs(r["avvik_pp"]))
    ny = sorted(nr for nr, k in t.kommuner.items() if (k.get("nyklarert") or 0) > 0)
    bare_fasit = sorted(set(t.kommuner) - set(a2["kommuner"]))
    bare_anslag = sorted(set(a2["kommuner"]) - set(t.kommuner))
    k_ut, f_ut = avvik(andel_k, a2["kommuner"]), avvik(andel_f, a2["fylker"])
    ledd = [
        {"ledd": 1, "ordrett": ordrett.get(1, ""),
         "slaar_til": (bool(t.nyklarert_kolonne and ny) if regneark_lest else None),
         "tall": {"kolonnen_finnes": t.nyklarert_kolonne, "kommuner_over_0": ny}},
        {"ledd": 2, "ordrett": ordrett.get(2, ""),
         "slaar_til": bool(bare_fasit or bare_anslag),
         "tall": {"bare_i_fordelingen": bare_fasit, "bare_i_anslaget": bare_anslag}},
        {"ledd": 3, "ordrett": ordrett.get(3, ""), "slaar_til": bool(k_ut),
         "tall": {"utenfor": len(k_ut), "av": len(set(andel_k) & set(a2["kommuner"])),
                  "storst": k_ut[:1]}},
        {"ledd": 4, "ordrett": ordrett.get(4, ""), "slaar_til": bool(f_ut),
         "tall": {"utenfor": len(f_ut), "av": len(set(andel_f) & set(a2["fylker"])),
                  "storst": f_ut[:1]}},
    ]
    if any(x["slaar_til"] for x in ledd):
        utfall = "bom"
    elif all(x["slaar_til"] is False for x in ledd):
        utfall = "traff"
    else:
        utfall = "venter"
    return {"id": p["id"], "konfidens": p.get("konfidens"), "utfall": utfall, "ledd": ledd,
            "kommuner_utenfor": k_ut, "fylker_utenfor": f_ut}


# ---------------------------------------------------------------- pakke 2


def _per_lok(rader: list[dict]) -> dict[str, dict[str, dict]]:
    """{lokalitet: {komnr: rad}} fra lokalitetslista."""
    ut: dict[str, dict[str, dict]] = {}
    for r in rader:
        ut.setdefault(r["nr"], {})[r["komnr"]] = r
    return ut


def pakke2(t: Tabell, p2: dict) -> list[dict]:
    """De ni påstandene, hver med utfall og tallene bak.

    `venter`: det påstanden avgjøres mot, er ikke lest ennå (regnearket,
    eller arket i det). Publiseres ikke regnearket innen 31.12.2026, kan
    P2-1 til P2-6 ikke avgjøres; det skriver Heine, ikke denne.
    """
    ps = {f"P2-{i}": x for i, x in enumerate(p2["paastander"], 1)}
    ut = []

    def svar(pid, utfall, hvorfor, avvik=()):
        ut.append({"paastand": pid, "id": ps[pid]["id"], "konfidens": ps[pid].get("konfidens"),
                   "entitet": ps[pid].get("entitet", ""), "utfall": utfall,
                   "hvorfor": hvorfor, "avvik": list(avvik)})

    mtb, mtb_kilde = None, ""
    if t.kommune_mtb:
        mtb, mtb_kilde = t.kommune_mtb, "MTB-kolonnen i «Kommuner»"
    elif t.lokaliteter:
        mtb, mtb_kilde = {}, "lokalitetslista summert per kommune (arket «Kommuner» ble ikke lest)"
        for r in t.lokaliteter:
            mtb[r["komnr"]] = mtb.get(r["komnr"], 0.0) + r["justert"]
    for pid, g in (("P2-1", "U"), ("P2-2", "E")):
        if mtb is None:
            svar(pid, "venter", "MTB per kommune er ikke lest (regnearket mangler)")
            continue
        av = [{"nr": nr, "navn": p2["kommuner"][nr]["navn"], "fasit_t": mtb.get(nr),
               "forventet_t": p2["kommuner"][nr]["mtb"],
               "avvik_t": None if nr not in mtb else mtb[nr] - p2["kommuner"][nr]["mtb"]}
              for nr in p2["grupper"][g]
              if nr not in mtb or abs(mtb[nr] - p2["kommuner"][nr]["mtb"]) > P2_MTB + FLYT]
        svar(pid, "bom" if av else "traff",
             f"{len(p2['grupper'][g]) - len(av)} av {len(p2['grupper'][g])} innenfor "
             f"±{P2_MTB:g} t ({mtb_kilde})", av)

    lok = _per_lok(t.lokaliteter) if t.lokaliteter else None
    grense = {pid: [x for x in p2["lokaliteter"] if x["paastand"] == pid]
              for pid in ("P2-3", "P2-4", "P2-5", "P2-6")}
    for pid in ("P2-3", "P2-4"):
        if lok is None:
            svar(pid, "venter", "lokalitetslista er ikke lest")
            continue
        av = []
        for x in grense[pid]:
            rader = lok.get(x["nr"], {})
            kap = sum(r["kap"] * r["andel"] for r in rader.values())
            if not rader or abs(kap - x["mtb"]) > 0.001:
                av.append({"nr": x["nr"], "navn": x["navn"], "forventet_t": x["mtb"],
                           "fasit_t": kap if rader else None,
                           "hvorfor": "mangler på listen" if not rader else "annen MTB"})
        svar(pid, "bom" if av else "traff",
             f"{len(grense[pid]) - len(av)} av {len(grense[pid])} med, med forventet MTB", av)

    if lok is None:
        svar("P2-5", "venter", "lokalitetslista er ikke lest")
        svar("P2-6", "venter", "lokalitetslista er ikke lest")
    else:
        av = [{"nr": x["nr"], "navn": x["navn"], "hvorfor": "står på listen",
               "fasit_t": sum(r["justert"] for r in lok[x["nr"]].values())}
              for x in grense["P2-5"] if x["nr"] in lok]
        svar("P2-5", "bom" if av else "traff",
             f"{len(grense['P2-5']) - len(av)} av {len(grense['P2-5'])} er ute", av)
        av = []
        for x in grense["P2-6"]:
            rader = lok.get(x["nr"], {})
            if not x["deling"]:                       # PERSFLUA: skal ikke være delt
                if len(rader) > 1:
                    av.append({"nr": x["nr"], "navn": x["navn"], "hvorfor": "delt",
                               "fasit": {k: r["andel"] for k, r in rader.items()}})
                continue
            if set(rader) != set(x["deling"]):
                av.append({"nr": x["nr"], "navn": x["navn"],
                           "hvorfor": "ikke delt" if len(rader) < 2 else "delt mellom andre kommuner",
                           "fasit": {k: r["andel"] for k, r in rader.items()},
                           "forventet": x["deling"]})
                continue
            if bort := {k: rader[k]["andel"] - b for k, b in x["deling"].items()
                        if abs(rader[k]["andel"] - b) > P2_DELING + FLYT}:
                av.append({"nr": x["nr"], "navn": x["navn"], "hvorfor": "annen brøk",
                           "fasit": {k: r["andel"] for k, r in rader.items()},
                           "forventet": x["deling"], "avvik": bort})
        svar("P2-6", "bom" if av else "traff",
             f"{len(grense['P2-6']) - len(av)} av {len(grense['P2-6'])} som forventet", av)

    andel_k, andel_f = _andeler(t)
    for pid, fasit, forventet, enhet in (
            ("P2-7", andel_f, {k: v["andel"] for k, v in p2["fylker"].items()}, "fylkeskommuner"),
            ("P2-8", andel_k, {k: v["andel"] for k, v in p2["kommuner"].items()}, "kommuner")):
        av = sorted(({"nr": nr, "fasit": fasit.get(nr), "forventet": forventet.get(nr),
                      "avvik_pp": (None if nr not in fasit or nr not in forventet
                                   else (fasit[nr] - forventet[nr]) * 100)}
                     for nr in set(fasit) | set(forventet)
                     if nr not in fasit or nr not in forventet
                     or abs(fasit[nr] - forventet[nr]) * 100 > P2_PP + FLYT),
                    key=lambda r: -abs(r["avvik_pp"] or 1))
        svar(pid, "bom" if av else "traff",
             f"{len(forventet) - len(av)} av {len(forventet)} {enhet} innenfor "
             f"±{str(P2_PP).replace('.', ',')} prosentpoeng", av)

    sk = sum(k["totalt"] for k in t.kommuner.values())
    sf = sum(f["belop"] for f in t.fylker.values())
    pst = sf / (sk + sf) * 100
    svar("P2-9", "bom" if abs(pst - 20) > P2_9_PP + FLYT else "traff",
         f"fylkeskommunene {sf:,.2f} av {sk + sf:,.2f} kr = {pst:.6f} %"
         .replace(",", " ").replace(".", ","))
    return ut


# -------------------------------------------------------------- gruppene


def forventet_per_lokalitet(nokkel: h.Nokkel, p2: dict) -> dict[str, dict[str, float]]:
    """Pakke 2s forventning per lokalitet og kommune: A2s nøkkel
    (snapshotet 31.08) med Havbruksstasjonens to lokaliteter (P2-3).

    KASTER `ValueError` når summen per kommune ikke er pakke 2s tabell:
    da regnes avvikene mot noe annet enn det som ble forseglet.
    """
    ut: dict[str, dict[str, float]] = {}
    for komnr, plasser in nokkel.plasser.items():
        for p in plasser:
            ut.setdefault(p.nr, {})[komnr] = ut.get(p.nr, {}).get(komnr, 0.0) + p.tonn
    for x in p2["lokaliteter"]:
        if x["paastand"] == "P2-3":
            ut.setdefault(x["nr"], {})[x["kommuner"][0]] = x["mtb"]
    per: dict[str, float] = {}
    for d in ut.values():
        for k, v in d.items():
            per[k] = per.get(k, 0.0) + v
    if sprik := {k: (per.get(k, 0), v["mtb"]) for k, v in p2["kommuner"].items()
                 if abs(per.get(k, 0) - v["mtb"]) > 0.11}:
        raise ValueError(f"forventet MTB lar seg ikke gjenskape fra snapshotet: "
                         f"{dict(list(sprik.items())[:5])}")
    return ut


def _grunn(nr: str, deres: dict[str, float], vaare: dict[str, float], lok31: dict,
           lok07: dict, ute: dict, grense: dict[str, str]) -> tuple[str, str]:
    """(gruppe, hvorfor) for én lokalitet der tallene skiller."""
    if nr in grense:
        return "G", f"grensetilfelle i {grense[nr]}"
    r = lok31.get(nr) or lok07.get(nr)
    if not vaare:
        if r is None:
            return "R", "på listen, men ikke i registeret 31.08 eller 07.09"
        if not h.ledd1(r):
            return "V", "på listen, men utenfor ledd 1 i filteret vårt"
        if nr in ute:
            return "V", "på listen, men holdt ute av ledd 2 (ingen laksetillatelse)"
        return "V", "på listen, men ikke i nøkkelen vår"
    if not deres:
        return "V", "i nøkkelen vår, men ikke på listen"
    if set(deres) != set(vaare):
        if len(deres) > 1:
            return "V", f"delt hos dem ({', '.join(sorted(deres))}), ikke hos oss"
        reg = (r or {}).get("kommunenummer", "")
        return "R", f"registeret sier kommune {reg}, listen {next(iter(deres))}"
    tonn = sum(deres.values())
    felt = {f: v for f in ("kapasitet", "kapasitet_midlertidig")
            for rad in (lok31.get(nr), lok07.get(nr)) if rad
            for v in [h.mtb({f: rad.get(f)})] if abs(v - tonn) < LIK_T}
    if felt:
        return "V", (f"listen har {tonn:.0f} t, som er feltet {next(iter(felt))}; "
                     f"vi brukte det høyeste av de to")
    return "R", f"listen har {tonn:.0f} t, som ikke står i noe felt i registeret"


def _storst(summer: dict[str, float]) -> str:
    return max(TVIL, key=lambda g: (round(abs(summer.get(g, 0.0)), 6), -TVIL.index(g)))


def grupper(t: Tabell, p2: dict, a2: dict, nokkel: h.Nokkel, lok07: dict) -> dict:
    """Avvikene per kommune og fylkeskommune, hvert i én av tre grupper."""
    andel_k, andel_f = _andeler(t)
    grense = {x["nr"]: x["paastand"] for x in p2["lokaliteter"]}
    lokaliteter, per_kom = [], {}
    foreloepig = t.lokaliteter is None
    if not foreloepig:
        vaar = forventet_per_lokalitet(nokkel, p2)
        deres: dict[str, dict[str, float]] = {}
        for r in t.lokaliteter:
            deres.setdefault(r["nr"], {})
            deres[r["nr"]][r["komnr"]] = deres[r["nr"]].get(r["komnr"], 0.0) + r["justert"]
        for nr in sorted(set(vaar) | set(deres), key=lambda x: int(x) if x.isdigit() else 0):
            d, v = deres.get(nr, {}), vaar.get(nr, {})
            forskjell = {k: d.get(k, 0.0) - v.get(k, 0.0) for k in set(d) | set(v)}
            if max(abs(x) for x in forskjell.values()) < LIK_T:
                continue
            g, hvorfor = _grunn(nr, d, v, nokkel.lok, lok07, nokkel.ute, grense)
            navn = ((nokkel.lok.get(nr) or lok07.get(nr) or {}).get("navn")
                    or next((r["navn"] for r in t.lokaliteter if r["nr"] == nr), ""))
            for k, x in forskjell.items():
                if abs(x) >= LIK_T:
                    per_kom.setdefault(k, {}).setdefault(g, 0.0)
                    per_kom[k][g] += x
                    lokaliteter.append({"nr": nr, "navn": navn, "komnr": k,
                                        "fasit_t": d.get(k, 0.0), "forventet_t": v.get(k, 0.0),
                                        "forskjell_t": x, "gruppe": g, "hvorfor": hvorfor})
    netto = {g: sum(x["forskjell_t"] for x in lokaliteter if x["gruppe"] == g) for g in GRUPPER}
    nevneren = _storst(netto) if any(abs(x) >= LIK_T for x in netto.values()) else None
    # EN NYKLARERT-DEL i tabellen flytter andelen til hver kommune uten at
    # en eneste lokalitet skiller (2025: 763 mill. kr av 1 128). Det står
    # i tabellen deres og kan vises, så andelen alene føres dit.
    nyklarert = sum((k.get("nyklarert") or 0) for k in t.kommuner.values())

    mtb = t.kommune_mtb
    if mtb is None and t.lokaliteter:
        mtb = {}
        for r in t.lokaliteter:
            mtb[r["komnr"]] = mtb.get(r["komnr"], 0.0) + r["justert"]
    kommuner = []
    for nr in sorted(set(p2["kommuner"]) | set(t.kommuner)):
        f = p2["kommuner"].get(nr)
        fa = andel_k.get(nr, 0.0)
        rad = {"nr": nr, "navn": (f or t.kommuner.get(nr, {})).get("navn", ""),
               "fasit_belop": t.kommuner.get(nr, {}).get("totalt"), "fasit_andel": fa,
               "p1_andel": a2["kommuner"].get(nr),
               "p1_avvik_pp": None if nr not in a2["kommuner"] else (fa - a2["kommuner"][nr]) * 100,
               "p2_andel": f["andel"] if f else None,
               "p2_avvik_pp": None if not f else (fa - f["andel"]) * 100,
               "fasit_mtb": None if mtb is None else mtb.get(nr, 0.0),
               "p2_mtb": f["mtb"] if f else None, "gruppe": None, "hvorfor": ""}
        rad["mtb_avvik"] = (None if rad["fasit_mtb"] is None or not f
                            else rad["fasit_mtb"] - f["mtb"])
        avvik = (not f or nr not in t.kommuner
                 or abs(rad["p2_avvik_pp"]) > P2_PP + FLYT
                 or (rad["mtb_avvik"] is not None and abs(rad["mtb_avvik"]) > P2_MTB + FLYT))
        if avvik:
            if foreloepig:
                g = {"G": "G", "U": "R", "E": "V"}.get((f or {}).get("gruppe"), "V")
                rad["hvorfor"] = (f"foreløpig, etter gruppe {(f or {}).get('gruppe', '–')} "
                                  f"i pakke 2: lokalitetslista er ikke lest")
            elif per_kom.get(nr):
                g = _storst(per_kom[nr])
                rad["hvorfor"] = "; ".join(
                    f"{x['nr']} {x['navn']} {x['forskjell_t']:+.0f} t" for x in lokaliteter
                    if x["komnr"] == nr)
            elif rad["mtb_avvik"] is not None and abs(rad["mtb_avvik"]) > P2_MTB + FLYT:
                g = "R"
                rad["hvorfor"] = "MTB i «Kommuner» er ikke summen av lokalitetslista deres"
            elif nyklarert > 0:
                g = "R"
                rad["hvorfor"] = (f"bare andelen: fordelingen har en nyklarert-del på "
                                  f"{_kr(nyklarert)} (pakke 1, ledd 1)")
            else:
                g = nevneren or "V"
                rad["hvorfor"] = "bare andelen: nevneren flyttet seg"
            rad["gruppe"] = g
        kommuner.append(rad)

    fylker = []
    for nr in sorted(set(p2["fylker"]) | set(t.fylker)):
        f = p2["fylker"].get(nr)
        fa = andel_f.get(nr, 0.0)
        rad = {"nr": nr, "navn": (f or t.fylker.get(nr, {})).get("navn", ""),
               "fasit_belop": t.fylker.get(nr, {}).get("belop"), "fasit_andel": fa,
               "p1_andel": a2["fylker"].get(nr),
               "p1_avvik_pp": None if nr not in a2["fylker"] else (fa - a2["fylker"][nr]) * 100,
               "p2_andel": f["andel"] if f else None,
               "p2_avvik_pp": None if not f else (fa - f["andel"]) * 100,
               "gruppe": None, "hvorfor": ""}
        if not f or nr not in t.fylker or abs(rad["p2_avvik_pp"]) > P2_PP + FLYT:
            her = {}
            for k in kommuner:
                if k["nr"][:2] == nr and k["gruppe"]:
                    if foreloepig:
                        her[k["gruppe"]] = her.get(k["gruppe"], 0.0) + abs(k["p2_avvik_pp"] or 0)
                    else:
                        for g, x in per_kom.get(k["nr"], {}).items():
                            her[g] = her.get(g, 0.0) + x
            if her and any(abs(x) >= LIK_T or foreloepig for x in her.values()):
                rad["gruppe"] = _storst(her)
                rad["hvorfor"] = "kommunene i fylket"
            else:
                rad["gruppe"] = nevneren or "V"
                rad["hvorfor"] = "bare andelen: nevneren flyttet seg"
        fylker.append(rad)

    return {"foreloepig": foreloepig, "kommuner": kommuner, "fylker": fylker,
            "lokaliteter": lokaliteter, "netto_t": netto,
            "antall": {g: sum(1 for k in kommuner if k["gruppe"] == g) for g in GRUPPER},
            "fylker_antall": {g: sum(1 for k in fylker if k["gruppe"] == g) for g in GRUPPER}}


# ---------------------------------------------------------- hele fasiten


def fasit(aar: int, nett: bool = True) -> dict:
    """Alt som skrives. Kaster `ValueError` når et segl er brutt, og
    `FileNotFoundError` når ingenting med fordelingen er arkivert."""
    tider: dict[str, float] = {}
    t0 = time.perf_counter()
    segl = forseglinger(nett=nett)
    if brutt := [b for x in segl for b in x["brutt"]]:
        raise ValueError("forseglingen holder ikke: " + "; ".join(brutt))
    tider["forseglingene"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    p2 = h.pakke2()
    ark, pm, uleselig = les_tabellen(aar, p2)
    t = ark or pm
    if t is None:
        if uleselig:
            raise Uleselig("; ".join(uleselig))
        raise FileNotFoundError(f"verken regnearket eller pressemeldingen for {aar} er arkivert")
    nokkel = h.nokkel(h.FOR)
    lok07, _ = h.lokaliteter(h.ETTER)
    tider["tabellen"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    p1 = pakke1(t, regneark_lest=ark is not None)
    p2u = pakke2(t, p2)
    g = grupper(t, p2, h.anslaget(), nokkel, lok07)
    tider["avgjort"] = time.perf_counter() - t0

    from core import kodeproveniens
    kode = kodeproveniens.commit()
    if kode and kodeproveniens.rent() != kodeproveniens.RENT:
        kode += " (urent arbeidstre)"
    andel_k, andel_f = _andeler(t)
    return {
        "aar": aar,
        "tabell": {"form": t.form, "sti": t.kropp.navn, "sha256": t.kropp.sha256,
                   "url": t.logg.get("url", ""), "hentet": t.logg.get("fetched_at", ""),
                   "publisert": t.logg.get("published_at", ""), "dato": t.dato,
                   "arkivdato": t.kropp.dato, "merknader": t.merknader},
        "pressemelding_mot_regnearket": mot_hverandre(ark, pm) if ark and pm else None,
        "uleselig": uleselig,
        "forseglinger": segl,
        "pakke1": p1,
        "pakke2": p2u,
        "avvik": g,
        # DET SIDENE VISER, når fila er kvittert: Fiskeridirektoratets
        # beløp og andel per kommune og fylkeskommune, og hvor de står.
        "sider": {"kommuner": {nr: {"belop": k["totalt"], "andel": andel_k[nr]}
                               for nr, k in t.kommuner.items() if nr[:1] != "?"},
                  "fylker": {nr: {"belop": f["belop"], "andel": andel_f[nr]}
                             for nr, f in t.fylker.items() if nr[:1] != "?"}},
        "kode": kode,
        "_tider": tider,
    }


# ------------------------------------------------------------ markdown


def _p(x: float | None, d: int = 4) -> str:
    return "—" if x is None else f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def _a(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.4f} %".replace(".", ",")


def _kr(x: float | None) -> str:
    return "—" if x is None else f"{x:,.0f} kr".replace(",", " ")


def _t(x: float | None) -> str:
    if x is None:
        return "—"
    return (f"{round(x, 1) + 0.0:,.1f} t".replace(",", " ").replace(".", ",")
            .replace("-", "−"))


UTFALL = {"traff": "TRAFF", "bom": "BOM", "venter": "VENTER"}


def markdown(f: dict, torrkjoring: bool = False) -> str:
    L = []
    if torrkjoring:
        L += [f"**{TORRKJORING.format(aar=f['aar'])}**", ""]
    tb = f["tabell"]
    L += [f"# Havbruksfondet {f['aar']}: fasiten for pakke 1 og pakke 2", "",
          f"Tabellen: {tb['form']} `{tb['sti']}`, sha256 `{tb['sha256']}`.",
          f"Adresse: {tb['url'] or '(ikke i loggen)'}. Hentet {tb['hentet'] or tb['arkivdato']}"
          + (f", publisert {tb['publisert']}" if tb["publisert"] else ", publisert: ukjent")
          + (f", meldingen datert {tb['dato']}" if tb["dato"] else "") + "."]
    for m in tb["merknader"]:
        L.append(f"- merknad: {m}")
    if mh := f["pressemelding_mot_regnearket"]:
        L.append(f"Pressemeldingen `{mh['pressemelding']}` (datert {mh['dato']}) mot regnearket: "
                 f"{len(mh['kommuner_ulike'])} kommuner og {len(mh['fylker_ulike'])} "
                 f"fylkeskommuner avviker med 1 kr eller mer.")
    for u in f["uleselig"]:
        L.append(f"- **ikke lest:** {u}")

    L += ["", "## Forseglingene", "",
          "| pakke | fil | sha256 nå | lik forseglet | .ots-summen | commits | Bitcoin | ots verify |",
          "|---|---|---|---|---|---|---|---|"]
    for x in f["forseglinger"]:
        commits = "; ".join(
            f"{c['repo']} {c['commit'][:7]} {c['fil'].rsplit('/', 1)[-1]}: "
            + (("lik" if c["lik"] else "ULIK") + (" (origin/main)" if c.get("paa_origin_main") else "")
               if c["prøvd"] else f"ikke prøvd, {c['merknad']}")
            for c in x["commits"])
        bc = x.get("bitcoin") or {}
        blokker = "; ".join(
            f"{b['hoyde']} ({b['tid'][:16].replace('T', ' ')} UTC): "
            + (f"lik hos {', '.join(b['lik_hos'])}" if b["lik_hos"] else "ikke bekreftet")
            + (f", ULIK hos {', '.join(b['ulik_hos'])}" if b["ulik_hos"] else "")
            for b in bc.get("blokker", [])) or "ikke prøvd"
        L.append(f"| {x['pakke']} ({x['forseglet']}) | `{x['fil']}` | `{x['sha256'][:16]}…` | "
                 f"{'ja' if x['sha256'] == x['sha256_forseglet'] else 'NEI'} | "
                 f"{'lik' if x['ots_sum'] == x['sha256_forseglet'] else 'ULIK'} | {commits} | "
                 f"{blokker} | {bc.get('ots_verify') or 'ikke kjørt'} |")

    p1 = f["pakke1"]
    L += ["", f"## Pakke 1: {UTFALL[p1['utfall']]}", "",
          f"`{p1['id']}`, konfidens {p1['konfidens']} %. Ett ledd er nok til at påstanden faller.", ""]
    for x in p1["ledd"]:
        st = {True: "SLÅR TIL", False: "slår ikke til", None: "venter på regnearket"}[x["slaar_til"]]
        L.append(f"{x['ledd']}. «{x['ordrett']}» **{st}.** "
                 + json.dumps(x["tall"], ensure_ascii=False))
    L += ["", f"## Pakke 2", "", "| påstand | konfidens | utfall | hvorfor |", "|---|---|---|---|"]
    for x in f["pakke2"]:
        L.append(f"| {x['paastand']} `{x['id']}` | {x['konfidens']} % | **{UTFALL[x['utfall']]}** | "
                 f"{x['hvorfor']} |")
    for x in f["pakke2"]:
        if x["avvik"]:
            L += ["", f"**{x['paastand']}**, avvik ({len(x['avvik'])}):", ""]
            L += [f"- {json.dumps(a, ensure_ascii=False)}" for a in x["avvik"][:40]]
            if len(x["avvik"]) > 40:
                L.append(f"- … og {len(x['avvik']) - 40} til (se JSON)")

    g = f["avvik"]
    L += ["", "## Avvikene, i tre grupper", "",
          "Avvik: MTB mer enn 1 t eller andelen mer enn 0,005 prosentpoeng fra pakke 2. "
          "Pakke 1-kolonnen er avviket fra A2."]
    if g["foreloepig"]:
        L.append("**Foreløpig:** lokalitetslista er ikke lest, så kommunene er gruppert etter "
                 "gruppen i pakke 2 (G, U → grunnlaget, E → vår egen feil).")
    L += ["", "| gruppe | kommuner | fylkeskommuner | netto tonn (lokalitetene) |", "|---|---:|---:|---:|"]
    for k, navn in GRUPPER.items():
        L.append(f"| {navn} | {g['antall'][k]} | {g['fylker_antall'][k]} | {_t(g['netto_t'][k])} |")
    for k, navn in GRUPPER.items():
        rader = [r for r in g["kommuner"] if r["gruppe"] == k]
        fyl = [r for r in g["fylker"] if r["gruppe"] == k]
        L += ["", f"### {navn[0].upper() + navn[1:]}", ""]
        if not rader and not fyl:
            L.append("Ingen.")
            continue
        L += ["| komnr | kommune | Fiskeridir. | beløp | pakke 1 | avvik pp | pakke 2 | avvik pp | MTB-avvik | hvorfor |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in sorted(rader, key=lambda r: -abs(r["p2_avvik_pp"] or 0)):
            L.append(f"| {r['nr']} | {r['navn']} | {_a(r['fasit_andel'])} | {_kr(r['fasit_belop'])} | "
                     f"{_a(r['p1_andel'])} | {_p(r['p1_avvik_pp'])} | {_a(r['p2_andel'])} | "
                     f"{_p(r['p2_avvik_pp'])} | {_t(r['mtb_avvik'])} | {r['hvorfor']} |")
        for r in fyl:
            L.append(f"| {r['nr']} | {r['navn']} (fylke) | {_a(r['fasit_andel'])} | {_kr(r['fasit_belop'])} | "
                     f"{_a(r['p1_andel'])} | {_p(r['p1_avvik_pp'])} | {_a(r['p2_andel'])} | "
                     f"{_p(r['p2_avvik_pp'])} | — | {r['hvorfor']} |")
    if g["lokaliteter"]:
        L += ["", "## Lokalitetene som skiller", "",
              "| lokalitet | kommune | Fiskeridir. | pakke 2 | forskjell | gruppe | hvorfor |",
              "|---|---|---:|---:|---:|---|---|"]
        for x in g["lokaliteter"]:
            L.append(f"| {x['nr']} {x['navn']} | {x['komnr']} | {_t(x['fasit_t'])} | "
                     f"{_t(x['forventet_t'])} | {_t(x['forskjell_t'])} | {GRUPPER[x['gruppe']]} | "
                     f"{x['hvorfor']} |")
    L += ["", "## Alle kommunene", "",
          "| komnr | kommune | Fiskeridir. | beløp | pakke 1 | avvik pp | pakke 2 | avvik pp | gruppe |",
          "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in g["kommuner"]:
        L.append(f"| {r['nr']} | {r['navn']} | {_a(r['fasit_andel'])} | {_kr(r['fasit_belop'])} | "
                 f"{_a(r['p1_andel'])} | {_p(r['p1_avvik_pp'])} | {_a(r['p2_andel'])} | "
                 f"{_p(r['p2_avvik_pp'])} | {GRUPPER[r['gruppe']] if r['gruppe'] else '—'} |")
    L += ["", f"Kode: {f['kode'] or 'ukjent'}."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------ skrivingen


def _uten_kode(tekst: str) -> dict:
    d = json.loads(tekst)
    d.pop("kode", None)
    return d


def skriv(f: dict, mappe: Path, torrkjoring: bool = False) -> list[Path]:
    """JSON og Markdown, én gang. Samme innhold som forrige fil (utenom
    koden som skrev den): ingenting skrives. Et annet: `.2`."""
    mappe.mkdir(parents=True, exist_ok=True)
    stamme = f"torrkjoring-{f['aar']}" if torrkjoring else f"fasit-{f['aar']}"
    data = {k: v for k, v in f.items() if not k.startswith("_")}
    if torrkjoring:
        data = {"torrkjoring": TORRKJORING.format(aar=f["aar"]), **data}
    tekst = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    finnes, sti = s._versjoner(mappe, stamme)
    if finnes and _uten_kode(finnes[-1].read_text("utf-8")) == _uten_kode(tekst):
        return []
    sti.write_text(tekst, encoding="utf-8")
    md = sti.with_suffix(".md")
    md.write_text(markdown(data, torrkjoring), encoding="utf-8")
    return [sti, md]


def kvitter(aar: int = h.AAR) -> Path:
    """`lest-fasit-<år>.json` for den nyeste fasitfila, med summen av den."""
    mappe = h.skaringsmappe()
    finnes, _ = s._versjoner(mappe, f"fasit-{aar}")
    if not finnes:
        raise FileNotFoundError(f"ingen fasit-{aar}.json i {mappe}")
    fil = finnes[-1]
    navn = subprocess.run(["git", "config", "user.name"], capture_output=True,
                          text=True).stdout.strip()
    kv = {"dato": dt.datetime.now(dt.timezone.utc).date().isoformat(), "lest_av": navn,
          "fasit": fil.name, "sha256": hashlib.sha256(fil.read_bytes()).hexdigest()}
    sti = mappe / f"lest-fasit-{aar}.json"
    sti.write_text(json.dumps(kv, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return sti


def sider(f: dict, ut: Path) -> int:
    """Kommunesidene med fasiten i `f`, uten kvittering, til `ut`. Bare for
    tørrkjøringen: hver side sier TØRRKJØRING øverst."""
    import nettsted
    felles = nettsted.les_felles()
    data = {k: v for k, v in f.items() if not k.startswith("_")}
    nr = nettsted.skriv_kommuner(ut, felles, fasit=data,
                                 torrkjoring=TORRKJORING.format(aar=f["aar"]))
    nettsted.skriv_stil(ut)
    nettsted.skriv_fonter(ut)
    nettsted.skriv_ikoner(ut)
    return len(nr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--torrkjor", type=int, metavar="ÅR",
                    help="hele kjeden mot kroppene for ÅR (skriver til --ut)")
    ap.add_argument("--ut", type=Path, help="mappe for tørrkjøringen")
    ap.add_argument("--sider", action="store_true",
                    help="med --torrkjor: bygg kommunesidene i --ut/nettsted")
    ap.add_argument("--kvitter", action="store_true",
                    help="skriv lest-fasit-<år>.json for nyeste fasitfil")
    ap.add_argument("--uten-nett", action="store_true",
                    help="ikke spør kalendrene og blokkutforskerne")
    a = ap.parse_args(argv)
    start = time.perf_counter()

    if a.kvitter:
        sti = kvitter()
        print(f"Kvittert: {sti}\nNeste bygg viser Fiskeridirektoratets beløp på kommunesidene.")
        return 0
    if a.torrkjor:
        if not a.ut:
            ap.error("--torrkjor krever --ut")
        ut = a.ut.expanduser().resolve()
        if ut == paths.DATA_DIR.resolve() or paths.DATA_DIR.resolve() in ut.parents:
            ap.error("tørrkjøringen skrives aldri i datarepoet")
        aar = a.torrkjor
    else:
        if a.sider:
            ap.error("--sider gjelder bare tørrkjøringen")
        ut, aar = h.skaringsmappe(), h.AAR

    try:
        f = fasit(aar, nett=not a.uten_nett)
    except FileNotFoundError as e:
        print(f"Fordelingen for {aar} er ikke arkivert ennå: {e}")
        return 0
    except Uleselig as e:
        print(f"LES FOR HÅND: {e}", file=sys.stderr)
        return 3
    except ValueError as e:
        print(f"STOPPET: {e}", file=sys.stderr)
        return 2

    tb = f["tabell"]
    if a.torrkjor:
        print(TORRKJORING.format(aar=aar))
    print(f"Tabellen: {tb['form']} {tb['sti']}\n  sha256 {tb['sha256']}")
    for x in f["forseglinger"]:
        blokker = [b["hoyde"] for b in (x.get("bitcoin") or {}).get("blokker", []) if b["lik_hos"]]
        print(f"Segl {x['pakke']}: sha256 {x['sha256'][:16]}… lik, .ots lik, "
              f"{sum(1 for c in x['commits'] if c['prøvd'])} av {len(x['commits'])} commits prøvd, "
              f"Bitcoin-blokker bekreftet: {blokker or 'ingen'}; "
              f"ots verify {(x.get('bitcoin') or {}).get('ots_verify') or 'ikke kjørt'}")
    print(f"Pakke 1: {UTFALL[f['pakke1']['utfall']]}  "
          + " ".join(f"({x['ledd']}) {'ja' if x['slaar_til'] else 'venter' if x['slaar_til'] is None else 'nei'}"
                     for x in f["pakke1"]["ledd"]))
    print("Pakke 2: " + "  ".join(f"{x['paastand']} {UTFALL[x['utfall']]}" for x in f["pakke2"]))
    print("Avvik: " + ", ".join(f"{n} {f['avvik']['antall'][k]} kommuner/"
                                f"{f['avvik']['fylker_antall'][k]} fylker"
                                for k, n in GRUPPER.items()))
    t0 = time.perf_counter()
    skrevet = skriv(f, ut, torrkjoring=bool(a.torrkjor))
    f["_tider"]["skrevet"] = time.perf_counter() - t0
    print("\n".join(str(p) for p in skrevet) or "Uendret: ingenting skrevet.")
    if a.sider:
        t0 = time.perf_counter()
        n = sider(f, ut / "nettsted")
        f["_tider"]["kommunesidene"] = time.perf_counter() - t0
        print(f"{n} kommunesider i {ut / 'nettsted' / 'kommune'}")
    print("Tid: " + ", ".join(f"{k} {v:.1f} s" for k, v in f["_tider"].items())
          + f"; i alt {time.perf_counter() - start:.1f} s")
    if not a.torrkjor and skrevet:
        print(f"\nLes {skrevet[1]}. Kvitter så sidene viser beløpene:\n"
              f"  .venv/bin/python fasit_havbruksfond.py --kvitter")
    return 3 if f["uleselig"] else 0


if __name__ == "__main__":
    sys.exit(main())
