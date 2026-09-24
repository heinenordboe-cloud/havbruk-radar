#!/usr/bin/env python3
"""Publiser Kystloggen til Cloudflare Pages.

    python publiser.py                  # forhåndsvisning
    python publiser.py --produksjon     # kystloggen.no

## Hvorfor dette er et skript og ikke seks kommandoer i RUNBOOK

Fordi rekkefølgen er hele poenget, og fordi ett av stegene er et
spørsmål til et menneske. En liste med seks kommandoer blir til fem
kommandoer den dagen noen har det travelt, og det er alltid den samme
som ryker: porten.

## Stegene, og hva hvert av dem verner mot

    1  sporbarhet   begge repoene rene og pushet. F15, to ganger:
                    en publisering fra kode ingen kan finne igjen er
                    en påstand ingen kan etterprøve.
    2  bygg         fra det som ligger på disk, ikke fra en cache
    3  porten       ETT ukvittert funn stopper. Ingen overstyring.
    4  ukas tall    skrevet ut, og du må skrive «ja». Mangler søket,
                    nektes produksjon; forhåndsvisning advares.
    5  wrangler     forhåndsvisning med mindre --produksjon
    6  logg         én linje i datarepoet: hva som ble lagt ut, når,
                    fra hvilken kode og hvilke data. Skriptet commiter
                    og pusher den selv — en logglinje ingen pushet
                    stopper NESTE publisering i steg 1.

## Ingen nøkler her

`wrangler` autentiserer i nettleseren (`npx wrangler login`) og lagrer
sin egen tilstand under `~/.config/.wrangler`. Dette skriptet leser
den ikke, skriver den ikke, og ber ikke om den. Kjører du uten å være
logget inn, sier wrangler fra selv.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROT))

from core.paths import DATA_DIR                            # noqa: E402

DATAREPO = DATA_DIR.parent
UT = DATA_DIR / "nettsted"
LOGG = DATAREPO / "docs" / "publiseringslogg.tsv"

PROSJEKT = "kystloggen"

# GRENENE HOS CLOUDFLARE PAGES, og de er ikke det samme som grenene i
# git — de er etiketter på en utrulling. Pages behandler ÉN av dem som
# produksjon; alt annet blir en forhåndsvisning med sin egen adresse.
#
# ## Hvorfor produksjonsgrenen står her og ikke utelates
#
# Fram til 23.09.2026 sendte `--produksjon` ingen `--branch` i det hele
# tatt, og lot wrangler utlede den av git. Det virker — helt til noen
# publiserer fra en annen gren enn `main`, og da går utrullingen til en
# forhåndsvisning UTEN at noe sier fra. En publisering som stille blir
# noe annet enn det den ba om, er verre enn en som feiler.
#
# Navnet «main» er valgt fordi det er grenen koden utgis fra, og fordi
# `kodeproveniens.krev_sporbar()` allerede krever at HEAD finnes på
# `origin/main`. To steder som sier «main» om samme gren er greit; to
# steder som KAN si ulike ting er det ikke — derfor står den her, som
# én konstant.
PRODUKSJONSGREN = "main"
FORHANDSGREN = "forhandsvisning"

# En forhåndsvisning som lander i produksjon er den ene feilen dette
# skriptet ikke kan oppdage i ettertid.
assert FORHANDSGREN != PRODUKSJONSGREN

# STEGET PORTEN KJØRER I, ett sted fordi det sies to steder: i
# overskriften over steg 3, og i beskjeden bygget skriver om hvem som
# kjører porten. Flyttes porten til et annet steg, skal ikke den andre
# av de to kunne fortsette å si «steg 3».
PORTSTEG = 3


class Stopp(SystemExit):
    """Publiseringen stanset. Meldingen sier hvor og hvorfor."""


def kjor(*args: str, mappe: Path = ROT, vis: bool = False) -> str:
    """Kjør en kommando. `Stopp` ved feil, med kommandoens egen melding."""
    try:
        ut = subprocess.run(args, cwd=mappe, text=True,
                            capture_output=not vis)
    except FileNotFoundError:
        # En kommando som ikke finnes skal si HVA som mangler, ikke
        # vise et spor fra subprocess. Dette rammer `npx` på en maskin
        # uten Node, og da er svaret å installere Node — ikke å lese
        # en stakktrace.
        raise Stopp(
            f"\n  STOPPET: kommandoen «{args[0]}» finnes ikke.\n"
            + ("  Installer Node.js (som gir npx), og kjør\n"
               "    npx wrangler login\n"
               "  én gang før første publisering."
               if args[0] == "npx" else ""))
    if ut.returncode != 0:
        melding = (ut.stderr or ut.stdout or "").strip() if not vis else ""
        raise Stopp(f"\n  STOPPET i {mappe.name}: {' '.join(args)}\n"
                    f"  {melding}")
    return (ut.stdout or "").strip() if not vis else ""


def prov(*args: str, mappe: Path) -> str:
    """Kjør en kommando. Tom streng når den gikk, ellers dens egen klage.

    Som `kjor()`, men uten `Stopp`. Brukes det ene stedet der en feil
    ikke skal stanse noe som helst, fordi det som kunne vært stanset
    allerede har skjedd — se `bokfor()`.
    """
    try:
        ut = subprocess.run(args, cwd=mappe, text=True, capture_output=True)
    except FileNotFoundError:
        return f"kommandoen «{args[0]}» finnes ikke"
    if ut.returncode != 0:
        return ((ut.stderr or ut.stdout or "").strip()
                or f"{' '.join(args)} ga {ut.returncode}")
    return ""


def git(*args: str, mappe: Path) -> str:
    return kjor("git", *args, mappe=mappe)


# ------------------------------------------------------------ steg 1

def krev_sporbar(mappe: Path, navn: str) -> str:
    """Rent tre, ingenting upushet. Returnerer commit-sha.

    ## Hvorfor BEGGE repoene

    Nettstedet er en funksjon av to ting: koden som bygger og dataene
    som bygges. En publisering der ett av dem ikke kan gjøres rede for,
    er en side ingen kan bygge på nytt — og da er sjekksummen i
    arkivlinja en påstand uten dekning.

    Dette er den samme regelen som `core/kodeproveniens.py` håndhever
    for innsamlingen, av samme grunn: F15 skjedde to ganger.
    """
    urent = git("status", "--porcelain", mappe=mappe)
    if urent:
        raise Stopp(
            f"\n  STOPPET: {navn} har et urent arbeidstre.\n\n{urent}\n\n"
            f"  Commit eller still tilbake. En publisering fra et tre "
            f"ingen kan gjenskape, er en side ingen kan bygge på nytt.")

    git("fetch", "--quiet", "origin", mappe=mappe)
    upushet = git("log", "origin/main..HEAD", "--oneline", mappe=mappe)
    if upushet:
        raise Stopp(
            f"\n  STOPPET: {navn} har commits som ikke er pushet.\n\n"
            f"{upushet}\n\n  Push først. CLAUDE.md regel 7.")

    return git("rev-parse", "HEAD", mappe=mappe)


# ------------------------------------------------------------ steg 2

def byggkommando() -> list[str]:
    """Kommandoen steg 2 kjører.

    Her og ikke inline, fordi den bærer ÉN opplysning på tvers av to
    filer: at porten kjøres av dette skriptet, i steg `PORTSTEG`.
    `nettsted.py` kan ikke vite det selv — og gjettet den, ville den
    gjettet feil hver gang bygget kjøres for hånd.
    """
    return [sys.executable, "nettsted.py", "--alle",
            "--vakt-kjores-av", f"{Path(__file__).name} steg {PORTSTEG}"]


# ------------------------------------------------------------ steg 4

# MODULEN NETTLESEREN LASTER. `maler/sok.js` henter den ved første
# tastetrykk; er den ikke der, svarer søkefeltet ingenting uansett hvor
# komplett resten av indeksen er.
SOKEMODUL = "pagefind/pagefind.js"


def sokeindeks(ut: Path) -> tuple[str, str]:
    """(mangel, linje) for søket i det som er i ferd med å bli lastet opp.

    `mangel` er tom streng når søket svarer, ellers grunnen til at det
    ikke gjør det.

    MÅLT PÅ DISK, ikke lest av byggerapporten. Byggets rapport sier at
    vi PRØVDE å bygge en indeks; filene under `ut/pagefind/` sier at den
    er der. Det er skillet i CLAUDE.md 1b-2, og her har det to følger
    som begge er reelle: `--uten-bygg` laster opp en mappe dette
    skriptet ikke har bygget og ikke har noen rapport fra, og en indeks
    kan være halv eller slettet lenge etter at rapporten ble skrevet.

    Prøven er Pagefinds egen bokføring mot filene: `pagefind-entry.json`
    oppgir hvor mange sider som er indeksert, og det skal finnes ett
    tekstutdrag per side. Er de to ULIKE, er det porten i steg
    `PORTSTEG` som eier funnet (`ugranska`) — den sier at ordtabellene
    kan være bygget av noe ingen har lest. Her spørs det bare om det
    finnes en indeks i det hele tatt.

    ## HVA DENNE PRØVEN IKKE SVARER PÅ

    Om indeksen er over DISSE sidene. Den svarer på om det finnes en
    indeks, og det er et annet spørsmål — nøyaktig den formen CLAUDE.md
    1b-2 advarer mot, så den skal stå skrevet her framfor å bli oppdaget.

    `skriv_sokeindeks()` tømmer katalogen før hver kjøring, så et bygg
    kan ikke etterlate en gammel indeks. `--uten-bygg` kan: da lastes
    mappa opp som den ligger, og en indeks fra et tidligere bygg ville
    passert her. MÅLT 23.09.2026: utputtmappa BAR en pagefind-indeks fra
    et tidligere bygg (2349 sider, annen språkhash enn dagens), skrevet
    av en binær som ikke lenger fantes på `PATH`. Den var trolig i orden
    — men ingenting i denne prøven ville sagt fra om den ikke var det.

    Å lukke det krever et stempel som knytter indeksen til sidene den ble
    bygget fra. Det finnes ikke i dag, og det er en åpen sak, ikke en
    utelatelse.
    """
    import publiseringsvakt

    sider, utdrag = publiseringsvakt.utdrag_dekker_indeksen(ut / "pagefind")
    linje = f"søkeindeks: {sider} sider, {utdrag} tekstutdrag"
    if sider <= 0 or utdrag == 0:
        return (f"søkeindeksen er ikke bygget — {ut / 'pagefind'} har "
                f"ingen lesbar pagefind-entry.json eller ingen "
                f"tekstutdrag"), linje
    if not (ut / SOKEMODUL).exists():
        return (f"{SOKEMODUL} mangler — søkefeltet laster aldri motoren, "
                f"og de {utdrag} tekstutdragene blir liggende ubrukt"), linje
    return "", linje


def krev_sokeindeks(ut: Path, produksjon: bool) -> list[str]:
    """Linjene som skrives om søket. `Stopp` når produksjon mangler det.

    ## Hvorfor produksjon NEKTES og forhåndsvisning bare advares

    Fordi de to svarer på hver sin ting. En forhåndsvisning ses av den
    som ba om den, og et søkefelt som ikke svarer der er en mangel
    vedkommende selv oppdager i samme time. Produksjon ses av alle andre,
    og et søkefelt som tar imot tastetrykk og svarer ingenting er
    nøyaktig formen på feilene i CLAUDE.md 1b: stille, og usynlig for den
    som ikke visste at det skulle kommet et svar.

    Nektelsen kommer FØR spørsmålet i steg 4. Å spørre et menneske om lov
    til noe vi like etter vil nekte, er å lære vedkommende at «ja» ikke
    betyr noe.
    """
    mangel, linje = sokeindeks(ut)
    if not mangel:
        return [f"  {linje}"]
    if produksjon:
        raise Stopp(
            f"\n  STOPPET: {mangel}\n\n"
            f"  Produksjon krever et søk som svarer. Installer pagefind\n"
            f"  (se requirements-verktoy.md), bygg på nytt — eller legg\n"
            f"  ut til forhåndsvisning i mellomtiden.\n"
            f"  Ingenting er lastet opp.")
    return [f"  {linje}",
            f"\n  ADVARSEL: {mangel}",
            f"  Forhåndsvisningen legges ut uten søk. Produksjon nektes."]


def ukas_tall() -> tuple[str, list[str]]:
    """(ukeslug, linjer) — hva som ligger i den ferskeste uka.

    Leses av det som NETTOPP ble bygget, ikke av changeloggen på nytt:
    spørsmålet er «hva er det jeg er i ferd med å legge ut», og det
    svares bare av utputtet.
    """
    import collections

    import nettsted

    felles = nettsted.les_felles()
    uker = nettsted.les_endringsuker(felles)
    if not uker:
        return "", ["Ingen endringsuker."]

    u = uker[0]
    linjer = [
        f"  {u['vist']} ({u['spenn']})",
        f"  {u['antall']} endringer · {u['antall_egen_del']} selskapsdata "
        f"· {u['utenfor_tellingen']} felt som kom eller gikk "
        f"· {u['antall_rader']} rader i alt",
        "",
        "  per type:",
    ]
    for k in u["typer"]:
        if k["antall"]:
            merke = "" if k.get("teller", True) else "   (telles ikke)"
            linjer.append(f"    {k['antall']:>6}  {k['navn']}{merke}")

    linjer += ["", "  per kilde:"]
    for kilde, n in collections.Counter(
            h["kilde"] for h in u["hendelser"]).most_common():
        linjer.append(f"    {n:>6}  {kilde}")
    return u["slug"], linjer


def spor(tekst: str) -> None:
    """Krev «ja». Alt annet stopper.

    Ikke «y», ikke enter, ikke «ja» med stor J som feiler stille. Et
    spørsmål som kan besvares ved et uhell er ikke et spørsmål.
    """
    try:
        svar = input(tekst).strip().lower()
    except EOFError:
        # Ingen å spørre. Da er svaret nei — et spørsmål uten et
        # menneske er ikke besvart, og en publisering som gikk gjennom
        # fordi stdin var lukket ville vært den verste varianten:
        # stille, og uten at noen hadde sett tallene.
        raise Stopp("\n\n  STOPPET: ingen å spørre (stdin er lukket). "
                    "Kjør fra et terminalvindu.")
    if svar != "ja":
        raise Stopp("\n  Avbrutt. Ingenting er lastet opp.")


# ------------------------------------------------------------ steg 6

def skriv_logg(kode: str, data: str, miljo: str, uke: str) -> None:
    """Én linje per publisering, i DATAREPOET.

    Der og ikke i koderepoet: en publisering er en hendelse i
    historikken, og historikken bor der dataene bor. Linja er
    append-only som alt annet der.
    """
    LOGG.parent.mkdir(parents=True, exist_ok=True)
    ny = not LOGG.exists()
    with LOGG.open("a", encoding="utf-8") as f:
        if ny:
            f.write("tidspunkt\tmiljo\tkode_commit\tdata_commit\tuke\n")
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()}\t"
                f"{miljo}\t{kode}\t{data}\t{uke}\n")


def loggmelding(kode: str, data: str, miljo: str) -> str:
    """Commit-meldingen for logglinja.

    Den navngir MILJØET og BEGGE commitene, fordi det er nettopp de
    opplysningene linja legger til: hva som ble lagt ut hvor, og fra
    hvilken kode og hvilke data. `git log` på datarepoet skal kunne
    svare på det uten at noen åpner tsv-fila.

    Merk hvilken `data` det er: commiten datarepoet STO PÅ da steg 1
    målte det, ikke denne commiten, som er barnet av den. Det er
    riktig vei — raden sier hvilke data siden ble bygget av, og
    bokføringen av publiseringen kan umulig være en del av dem.
    """
    return (f"Publiseringslogg: {miljo} — kode {kode[:12]}, "
            f"data {data[:12]}")


def bokfor(kode: str, data: str, miljo: str,
           uke: str) -> tuple[str, list[str]]:
    """Skriv logglinja, og commit og push AKKURAT den fila.

    `("", [])` når linja står på `origin/main`. Ellers (grunnen til at
    den ikke gjør det, kommandoene som gjenstår for hånd).

    ## Hvorfor skriptet bokfører selv

    Fram til 23.09.2026 skrev steg 6 linja og ba mennesket om å commite
    den. Én glemt commit er nok til at NESTE publisering stopper i steg
    1 på et urent tre — og den som da har det travelt, commiter loggen
    sammen med hva som ellers måtte ligge i treet. Loggen er
    maskinskrevet og append-only; da er det maskinen som skal føre den.

    ## Hvorfor pathspec på commiten

    `git commit --only -- <sti>` commiter DEN fila fra arbeidstreet og
    lar resten av indeksen ligge. Steg 1 har allerede krevd et rent
    tre, så noe annet skal ikke finnes — men «skal ikke» er ikke «kan
    ikke», og en publisering skal ikke kunne dra en halvferdig endring
    i datarepoet med seg på lasset. `git add` må stå foran likevel:
    første gang er fila usporet, og pathspec matcher da ingenting.

    ## Hvorfor en feil her ikke er `Stopp`

    Fordi steg 5 allerede har lastet opp. Alt annet i dette skriptet
    kan stanses fordi det står FORAN opplastingen; dette står bak den,
    og der finnes ikke valget mellom å gjøre det og å la være. Svaret
    er å si høyt hva som mangler, ikke å late som om ingenting skjedde.
    """
    skriv_logg(kode, data, miljo, uke)
    sti = str(LOGG.relative_to(DATAREPO))
    melding = loggmelding(kode, data, miljo)

    feil = (prov("git", "add", "--", sti, mappe=DATAREPO)
            or prov("git", "commit", "--only", "--message", melding,
                    "--", sti, mappe=DATAREPO))
    if feil:
        return (f"logglinja er skrevet, men ikke committet:\n    {feil}",
                [f"git add -- {sti}",
                 f"git commit --only -m {melding!r} -- {sti}",
                 "git push origin HEAD:main"])

    # HEAD:main OG IKKE BARE `git push`: steg 1 målte `origin/main..HEAD`,
    # så `origin/main` er grenen dette repoet er gjort rede for mot. Lot
    # vi push velge selv, kunne linja lande et sted neste kjøring ikke
    # leter — og da er den upushet uten at noe sier fra.
    feil = prov("git", "push", "--quiet", "origin", "HEAD:main",
                mappe=DATAREPO)
    if feil:
        return (f"logglinja er committet, men ikke pushet:\n    {feil}",
                ["git pull --rebase    # om origin har flyttet seg",
                 "git push origin HEAD:main"])
    return "", []


# ------------------------------------------------------------ hoved

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--produksjon", action="store_true",
                    help="legg ut på kystloggen.no. Uten denne går "
                         "publiseringen til forhåndsvisningen.")
    ap.add_argument("--uten-bygg", action="store_true",
                    help="hopp over byggingen og bruk mappa som den er. "
                         "Porten kjøres uansett.")
    args = ap.parse_args()

    miljo = "produksjon" if args.produksjon else "forhandsvisning"
    print(f"\nKystloggen → {miljo}")

    # 1. Kan denne publiseringen gjøres rede for?
    print("\n[1/6] sporbarhet")
    git("pull", "--ff-only", "--quiet", mappe=DATAREPO)
    kode = krev_sporbar(ROT, "koderepoet")
    data = krev_sporbar(DATAREPO, "datarepoet")
    print(f"      kode {kode[:12]}  ·  data {data[:12]}  ·  begge rene "
          f"og pushet")

    # 2. Bygg.
    if args.uten_bygg:
        print("\n[2/6] bygg — hoppet over (--uten-bygg)")
    else:
        print("\n[2/6] bygg")
        kjor(*byggkommando(), vis=True)

    if not UT.is_dir():
        raise Stopp(f"\n  STOPPET: {UT} finnes ikke.")

    # 3. Porten. Egen kjøring, også når bygget nettopp kjørte den:
    #    `--uten-bygg` skal ikke kunne hoppe over den.
    print(f"\n[{PORTSTEG}/6] publiseringsvakten")
    import publiseringsvakt

    funn = publiseringsvakt.gransk(UT)
    igjen = publiseringsvakt.ukvittert(funn)
    kvitterte = [f for f in funn if f.kvittert]
    for f in publiseringsvakt.kodeproveniens_ukjente():
        print(f"      {f}")
    if igjen:
        for f in igjen:
            print(f"      {f}")
        raise Stopp(f"\n  STOPPET: {len(igjen)} ukvitterte funn. "
                    f"Ingenting er lastet opp.")
    print(f"      rent — {len(kvitterte)} kvitterte funn står")

    # 4. Hva er det jeg legger ut?
    print("\n[4/6] ukas endringer")
    uke, linjer = ukas_tall()
    print("\n".join(linjer))
    filer = sum(1 for p in UT.rglob("*") if p.is_file())
    bytes_ = sum(p.stat().st_size for p in UT.rglob("*") if p.is_file())
    print(f"\n  {filer} filer, {bytes_ / 1e6:.1f} MB → {miljo}")
    for linje in krev_sokeindeks(UT, args.produksjon):
        print(linje)
    spor(f'\n  Skriv «ja» for å laste opp til {miljo}: ')

    # 5. Ut.
    # GRENEN OPPGIS ALLTID, også for produksjon. Se `PRODUKSJONSGREN`.
    gren = PRODUKSJONSGREN if args.produksjon else FORHANDSGREN
    print(f"\n[5/6] wrangler → {miljo} (gren {gren})")
    wrangler = ["npx", "wrangler", "pages", "deploy", str(UT),
                "--project-name", PROSJEKT, "--branch", gren]
    kjor(*wrangler, vis=True)

    # 6. Logg.
    print("\n[6/6] logg")
    sti = LOGG.relative_to(DATAREPO)
    problem, gjenstaar = bokfor(kode, data, miljo, uke)
    if problem:
        # IKKE `Stopp`. Hver eneste Stopp-melding i dette skriptet ender
        # på at ingenting er lastet opp, og her er det motsatte sant.
        # Låner denne formen den, blir den utrygg alle de andre stedene.
        print(f"\n  SIDEN ER UTE — steg 5 lastet opp til {miljo}, og det\n"
              f"  står ved lag. Det er BOKFØRINGEN som mangler:\n\n"
              f"  {problem}\n\n"
              f"  Fullfør for hånd i {DATAREPO}:\n"
              + "\n".join(f"    {k}" for k in gjenstaar)
              + "\n\n  Står linja upushet, stopper neste publisering i "
                "steg 1.\n  CLAUDE.md regel 7.\n")
        return 1
    print(f"      {sti} — committet og pushet")
    print(f"\nFerdig. {miljo}.\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stopp as e:
        print(e)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Avbrutt. Ingenting er lastet opp.")
        sys.exit(1)
