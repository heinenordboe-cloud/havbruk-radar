"""Forsegler prediksjonsloggen: validerer, hasher, og skriver et segl.

    python forsegl.py            # validerer og skriver predictions/SEGL.txt
    python forsegl.py --sjekk    # verifiserer dagens filer mot seglet
    python forsegl.py --vis      # skriver seglet til stdout uten å røre disk

## Hva dette verktøyet løser, og hva det ikke løser

Prediksjonsloggen skal kunne bevise tre ting overfor noen som ikke stoler
på oss:

    a) anslaget ble skrevet FØR utfallet var kjent
    b) det er ikke endret i etterkant
    c) bommene står der sammen med treffene

Git alene beviser ingen av dem. `GIT_AUTHOR_DATE` og `GIT_COMMITTER_DATE`
kan settes til hva som helst av den som committer, og en historikk kan
skrives om i sin helhet med `filter-branch` og tvinges ut på nytt. En
tidslinje som eieren kan redigere er ikke et bevis for eieren.

Det som mangler er et ANKER UTENFOR REPOET: en hash publisert et sted vi
ikke kontrollerer, på en dato vi ikke kan flytte. Ankeret er brukerens
jobb — se `predictions/README.md`. Denne fila lager tallet som skal
forankres, og gjør det etterprøvbart at tallet hører til filene.

## To hasher per anslag, og hvorfor

Et anslag som er avgjort skal ha utfallet skrevet inn ved siden av seg —
krav (c). Men da endres fila etter at den ble forseglet, og en enkelt
filhash ville brutt krav (b) hver gang et anslag ble avgjort. Da er
seglet verdiløst nøyaktig når det trengs.

Derfor to nivåer:

  `filhash`    SHA-256 over filas rå bytes. Verifiseres av hvem som helst
               med `shasum -a 256 predictions/2026-08-18.yml`, uten dette
               verktøyet og uten å stole på det. Den ENDRES når utfallet
               skrives inn, og det er meningen: den beviser at fila er
               uendret, ikke at PÅSTANDEN er det.

  `kjernehash` SHA-256 over påstandsfeltene alene, kanonisert. Utfall,
               utfallsdato og kommentarer er utelatt. Den ENDRES IKKE når
               utfallet skrives inn, og det er den som skal forankres:
               den beviser at påstanden er den samme som ble gjort.

En skeptiker som lurer på om påstanden er strammet inn i ettertid, sjekker
kjernehashen mot ankeret. En som lurer på om noe annet i fila er rørt,
sjekker filhashen mot git. De to spørsmålene er ulike, og et segl som bare
svarte på det ene ville vært en snarvei av samme slag som CLAUDE.md 1b-2
advarer mot.

## Hva kjernehashen IKKE dekker

`grunnlag` er med i kjernen. Det er et valg: en begrunnelse som kan
omskrives i etterkant lar et bomskudd fortelles om til et treff av andre
grunner enn det påsto. Kommentarer i YAML-en er IKKE med — de er ikke
data, og en rettet skrivefeil skal ikke se ut som en forfalskning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from core import predictions
from core.predictions import PREDIKSJON_DIR

SEGL_PATH = PREDIKSJON_DIR / "SEGL.txt"

# Felter som beskriver UTFALLET, ikke påstanden. De holdes utenfor
# kjernehashen slik at et avgjort anslag kan få utfallet skrevet inn uten
# at ankeret brytes. Utvides denne lista, svekkes seglet — hvert felt som
# flyttes hit er ett felt som kan endres i ettertid uten at det synes.
UTFALLSFELTER = frozenset({"utfall", "utfall_dato", "utfall_kilde", "utfall_note"})

# Felter `core.predictions.last()` stempler på i minnet. De står ikke i
# fila og skal ikke telle med.
INTERNE = frozenset({"_fil", "_fildato"})

# Felter som MÅ finnes i hver prediksjon, utover det `core.predictions`
# alt krever. Kravene her er dette verktøyets, ikke kjørejobbens: en fil
# uten `konfidens` er fullt kjørbar, men den kan ikke forsegles, fordi en
# logg uten kalibrering ikke kan etterprøves som annet enn anekdoter.
EKSTRA_PAAKREVD = ("konfidens", "feil_hvis")

# Fra og med denne datoen kreves feltene over. Filer skrevet FØR den
# forsegles med det de har.
#
# Dette er ikke en slapphet, det er CLAUDE.md 1b-7 anvendt: gamle
# snapshots har ikke `published_at`, og de fylles ikke inn retroaktivt,
# fordi en verdi vi finner på i dag ville PÅSTÅTT noe ingen har gått god
# for. Samme her. Skulle `2026-08-18.yml` fått en `konfidens` nå, ville
# tallet vært satt etter at to av tre vinduer alt hadde begynt å bevege
# seg — og en kalibreringskurve bygget på et slikt tall måler ingenting.
#
# Prisen er at de tre første anslagene ikke kan telle med i kalibreringen.
# Den prisen er riktig: de var uansett utledet av Claude fra offentlige
# vedtak, ikke av en bransjevurdering, og beslutningen fra 18.08 sier det
# selv.
FORMAT_FRA = date(2026, 9, 3)


def _filer() -> list[Path]:
    """Prediksjonsfilene, i samme utvalg som `core.predictions._filer()`.

    Mønsteret er `*.yml` begge steder med vilje. Endres det ene uten det
    andre, forsegler dette verktøyet et annet sett enn kjørejobben leser,
    og seglet slutter å si noe om det som faktisk evalueres.

    Merk hva som IKKE fanges: `MAL.yaml` er en mal og ikke et anslag, og
    den ligger utenfor mønsteret nettopp derfor.
    """
    if not PREDIKSJON_DIR.exists():
        return []
    return sorted(PREDIKSJON_DIR.glob("*.yml"))


# ------------------------------------------------------------- validering


def _valider_ekstra(prediksjoner: list[dict]) -> list[str]:
    """Kravene forseglingen legger på toppen av `core.predictions.valider()`."""
    feil: list[str] = []
    for p in prediksjoner:
        pid = p.get("id", "<uten id>")

        try:
            skrevet = date.fromisoformat(str(p.get("_fildato") or ""))
        except ValueError:
            skrevet = None
        if skrevet is not None and skrevet < FORMAT_FRA:
            continue        # førformat — se FORMAT_FRA

        for felt in EKSTRA_PAAKREVD:
            if not str(p.get(felt) or "").strip():
                feil.append(f"{pid}: mangler {felt}")

        # Konfidens er et tall i prosent. Uten den kan loggen si hvor ofte
        # den traff, men ikke om den var trygg når den burde vært det —
        # og en logg uten kalibrering måler flaks like godt som innsikt.
        k = p.get("konfidens")
        if k is not None and not (isinstance(k, (int, float)) and 0 < float(k) < 100):
            feil.append(
                f"{pid}: konfidens må være et tall mellom 0 og 100 (eksklusive), ikke {k!r}"
            )

        # `utfall` MÅ finnes som nøkkel, og skal stå tom til vinduet er
        # avgjort. Mangler nøkkelen helt, kan et utfall senere legges til
        # uten at noen ser at det kom til — feltet er sin egen kvittering.
        if "utfall" not in p:
            feil.append(f"{pid}: mangler nøkkelen utfall (skal stå tom til den er avgjort)")
        else:
            u = str(p.get("utfall") or "").strip()
            if u and u not in {"traff", "bom", "kan_ikke_avgjores"}:
                feil.append(
                    f"{pid}: utfall må være tom, traff, bom eller kan_ikke_avgjores, ikke {u!r}"
                )
            if u and not str(p.get("utfall_dato") or "").strip():
                feil.append(f"{pid}: utfall er satt til {u!r}, men utfall_dato mangler")

        # Et utfall som er skrevet inn FØR avgjørelsesdatoen er en gjetning
        # på egne vegne. Vinduet må ha lukket.
        u = str(p.get("utfall") or "").strip()
        ud = str(p.get("utfall_dato") or "").strip()
        til = str((p.get("vindu") or {}).get("til") or "")
        if u and ud and til:
            try:
                if date.fromisoformat(ud) < date.fromisoformat(til) and u == "bom":
                    feil.append(
                        f"{pid}: bom skrevet {ud}, før vinduet lukket {til} — "
                        "et vindu som ikke er ute kan ikke ha bommet"
                    )
            except ValueError:
                feil.append(f"{pid}: utfall_dato {ud!r} er ikke en ISO-dato")
    return feil


# ----------------------------------------------------------------- hashing


def _kanonisk(p: dict) -> str:
    """Påstanden som én linje kanonisk JSON, uten utfall og uten internt støv.

    Sorterte nøkler og `ensure_ascii=False` gjør at rekkefølgen i YAML-en,
    innrykk og sitattegn ikke påvirker hashen. Det er poenget: en
    reformatert fil er ikke en endret påstand, og et segl som brøt på
    whitespace ville blitt slått av etter tredje falske alarm.
    """
    kjerne = {
        k: v
        for k, v in p.items()
        if k not in UTFALLSFELTER and k not in INTERNE
    }
    return json.dumps(kjerne, sort_keys=True, ensure_ascii=False, default=str)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bygg_segl(prediksjoner: list[dict]) -> str:
    """Seglteksten. Ren funksjon av filene på disk — samme inn, samme ut."""
    linjer: list[str] = []
    linjer.append("# SEGL — havbruk-radar/predictions")
    linjer.append("#")
    linjer.append("# Generert av forsegl.py. Ikke rediger for hånd: hver linje er en")
    linjer.append("# hash av noe annet, og en rettet hash er ikke en rettelse.")
    linjer.append("#")
    linjer.append("# filhash    SHA-256 over filas rå bytes. Verifiser selv med:")
    linjer.append("#                shasum -a 256 predictions/<fil>")
    linjer.append("#            Endres når et utfall skrives inn. Det er meningen.")
    linjer.append("#")
    linjer.append("# kjernehash SHA-256 over påstandsfeltene alene. Endres IKKE når")
    linjer.append("#            utfallet skrives inn. Det er denne som forankres.")
    linjer.append("#")
    linjer.append("# rot        SHA-256 over alle linjene mellom BEGIN og END under.")
    linjer.append("#            Ett tall å publisere. Alt annet henger under det.")
    linjer.append("")
    linjer.append("BEGIN")

    per_fil: dict[str, list[dict]] = {}
    for p in prediksjoner:
        per_fil.setdefault(str(p.get("_fil")), []).append(p)

    for sti in _filer():
        linjer.append(f"fil        {sti.name}")
        linjer.append(f"filhash    {_sha(sti.read_bytes())}")
        for p in per_fil.get(sti.name, []):
            pid = str(p.get("id") or "<uten id>")
            kh = _sha(_kanonisk(p).encode("utf-8"))
            utfall = str(p.get("utfall") or "").strip() or "(åpen)"
            linjer.append(f"  anslag   {pid}")
            linjer.append(f"  kjerne   {kh}")
            linjer.append(f"  utfall   {utfall}")
            try:
                forformat = date.fromisoformat(str(p.get("_fildato") or "")) < FORMAT_FRA
            except ValueError:
                forformat = False
            if forformat:
                linjer.append("  merknad  førformat: skrevet før konfidens ble krevd, "
                              "teller ikke i kalibreringen")
        linjer.append("")

    linjer.append("END")

    kropp = "\n".join(linjer[linjer.index("BEGIN") + 1 : linjer.index("END")])
    rot = _sha(kropp.encode("utf-8"))

    linjer.append("")
    linjer.append(f"rot        {rot}")
    linjer.append("")
    linjer.append("# Forankre ROT-tallet over et sted du ikke kontrollerer, og noter")
    linjer.append("# hvor i predictions/README.md. Et segl som bare ligger i repoet")
    linjer.append("# beviser ingenting: det er skrevet av den det skal binde.")
    return "\n".join(linjer) + "\n"


# -------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validerer og forsegler prediksjonsloggen."
    )
    ap.add_argument("--sjekk", action="store_true",
                    help="verifiser filene mot eksisterende SEGL.txt, ikke skriv")
    ap.add_argument("--vis", action="store_true",
                    help="skriv seglet til stdout uten å røre disk")
    args = ap.parse_args(argv)

    # En YAML-syntaksfeil kommer ut av `last()` som et ParserError. Uten
    # dette blir svaret en stacktrace der brukeren skal ha en filplassering
    # og et linjenummer — og et verktøy som skal kjøres før hver commit må
    # si hva som er galt, ikke hvor i PyYAML det ble oppdaget.
    try:
        prediksjoner = predictions.last()
    except yaml.YAMLError as e:
        print("Kan ikke lese prediksjonsfilene — YAML-en er ikke gyldig:",
              file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        return 1

    if not prediksjoner:
        print(f"Ingen prediksjoner funnet i {PREDIKSJON_DIR}.", file=sys.stderr)
        return 1

    feil = predictions.valider(prediksjoner) + _valider_ekstra(prediksjoner)
    if feil:
        print(f"{len(feil)} formatfeil — ingenting forseglet:", file=sys.stderr)
        for f in feil:
            print(f"  {f}", file=sys.stderr)
        return 1

    segl = bygg_segl(prediksjoner)

    if args.vis:
        print(segl, end="")
        return 0

    if args.sjekk:
        if not SEGL_PATH.exists():
            print(f"{SEGL_PATH} finnes ikke — kjør forsegl.py først.", file=sys.stderr)
            return 2
        gammelt = SEGL_PATH.read_text(encoding="utf-8")
        if gammelt == segl:
            print(f"Seglet stemmer. {len(prediksjoner)} anslag i {len(_filer())} fil(er).")
            return 0

        # Et brutt segl kan bety to helt ulike ting, og det er verdt å si
        # hvilket. Endret kjernehash er alvorlig: en påstand er skrevet om.
        # Endret filhash alene er ventet hver gang et utfall føres inn.
        def kjerner(tekst: str) -> set[str]:
            return {l.strip() for l in tekst.splitlines() if l.strip().startswith("kjerne")}

        if kjerner(gammelt) != kjerner(segl):
            print("SEGLET ER BRUTT: en kjernehash har endret seg.", file=sys.stderr)
            print("En påstand er skrevet om etter at den ble forseglet.", file=sys.stderr)
            return 2
        print("Seglet er utdatert, men ingen påstand er endret "
              "(bare filhash/utfall). Kjør forsegl.py for å oppdatere.",
              file=sys.stderr)
        return 2

    SEGL_PATH.write_text(segl, encoding="utf-8")
    rot = [l for l in segl.splitlines() if l.startswith("rot ")][0].split()[1]
    print(f"Forseglet {len(prediksjoner)} anslag i {len(_filer())} fil(er).")
    print(f"  {SEGL_PATH}")
    print(f"  rot: {rot}")
    print()
    print("Forankre rot-tallet utenfor repoet — se predictions/README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
