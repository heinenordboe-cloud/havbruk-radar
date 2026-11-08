"""Personopplysninger i rålaget, per arkivmappe — og om noen av dem er publisert.

    python3 -I analyse/persondata_raalag/maal.py \\
        ../havbruk-radar-data/data <bygget nettsted> > analyse/persondata_raalag/utskrift.txt

Økt 4e punkt 5 (R4 punkt 7). Skriver BARE tall og sha256, aldri et navn,
et nummer eller en adresse: kodrepoet er offentlig, og en måling av
personopplysninger som gjengir dem, er selv en behandling.

Hva som telles, per mappe (docs/MALING-PERSONDATA-RAALAG.md har
definisjonene og «Feil hvis»):

  A  Brreg-kropper (enhetsregisteret, enhetsregisteret_oppslag,
     eierskap-brreg): enheter med en personform (core/persondata.
     PERSONFORMER) og enheter med kontaktfelt (epostadresse, telefon,
     mobil), uansett form.
  B  JSON-kropper med et navn og et tomt identitetsnummer
     (`identityNr` null eller ""): eierskapsoverføringer og
     tillatelseseiere. At navnet er en person, er en ANTAKELSE (R4 F2).
  C  eierskap: enheter hvis `typeValue` er en person eller en personform
     (PERSON_TYPER).
  D  akvakultur-soknader: søknader med navn og uten organisasjonsnummer.
  E  e-postadresser i alle tekstkropper (json, html, txt), der
     lokaldelen ikke er en funksjonsadresse (post@, kontakt@ …).

Til slutt: hver identifikator fra A–E holdes mot det bygde nettstedet
(synlig tekst for .html, rå tekst ellers). Treff telles, ikke vises.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PERSONFORMER = {"ENK", "DA", "ANS", "PRE"}       # core/persondata.py:104
BRREG = ("enhetsregisteret", "enhetsregisteret_oppslag", "eierskap-brreg")
KONTAKT = ("epostadresse", "telefon", "mobil")
# pub-aquas ord for personene og personformene: sources/eierskap.py,
# PERSONTYPER og oversettelsen til DA/ANS/PRE (linje 134 og 159–166).
PERSON_TYPER = {"Person", "SoleProprietorship", "JointLiabilityCompany",
                "UnlimitedLiabilityCompany", "JointlyOwnedShippingCompany"}
FUNKSJON = re.compile(r"^(post|postmottak|kontakt|support|info|firmapost|"
                      r"servicesenter|presse|nyheter|personvern|noreply|no-reply|"
                      r"webmaster|redaksjonen|kundeservice|abonnement|firmapost)\b")
EPOST = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def kropper(arkiv: Path):
    for mappe in sorted(p for p in arkiv.iterdir() if p.is_dir()):
        for f in sorted(mappe.rglob("*")):
            if f.is_file() and f.suffix == ".gz" and "karantene" not in f.parts:
                yield mappe.name, f


def les(f: Path) -> bytes:
    try:
        return gzip.open(f).read()
    except OSError:
        return b""


def json_av(b: bytes):
    try:
        return json.loads(b)
    except (ValueError, UnicodeDecodeError):
        return None


def gaa(o):
    """Hver dict i en JSON-struktur."""
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from gaa(v)
    elif isinstance(o, list):
        for v in o:
            yield from gaa(v)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(data: Path, bygg: Path) -> None:
    arkiv = data / "arkiv"
    a_kropper = defaultdict(lambda: {"kropper": 0, "med_personform": 0, "med_kontakt": 0})
    a_person, a_kontakt = defaultdict(set), defaultdict(set)
    b_navn, b_rader, b_filer = defaultdict(set), Counter(), defaultdict(set)
    c_typer, c_ikke = Counter(), defaultdict(set)
    d_navn = set()
    e_adr = defaultdict(set)
    ident: dict[str, set[str]] = defaultdict(set)     # kategori -> identifikatorer
    eksempel_sha: dict[str, list[str]] = defaultdict(list)

    for mappe, f in kropper(arkiv):
        b = les(f)
        if not b:
            continue
        d = json_av(b) if f.name.endswith(".json.gz") or b[:1] in (b"{", b"[") else None

        if mappe in BRREG and d is not None:
            enheter = [e for e in gaa(d) if "organisasjonsnummer" in e and "navn" in e]
            pf = [e for e in enheter
                  if (e.get("organisasjonsform") or {}).get("kode") in PERSONFORMER]
            kt = [e for e in enheter if any(e.get(k) for k in KONTAKT)]
            s = a_kropper[mappe]
            s["kropper"] += 1
            s["med_personform"] += bool(pf)
            s["med_kontakt"] += bool(kt)
            for e in pf:
                a_person[mappe].add(e["organisasjonsnummer"])
                ident["A orgnr med personform"].add(e["organisasjonsnummer"])
                ident["A navn med personform"].add(e["navn"])
            for e in kt:
                a_kontakt[mappe].add(e["organisasjonsnummer"])
                for k in KONTAKT:
                    if e.get(k):
                        ident["A kontaktfelt"].add(str(e[k]))
            if pf:
                eksempel_sha[f"A {mappe}"].append(f"{f.relative_to(arkiv)} {sha(b)}")

        if d is not None:
            for e in gaa(d):
                if "identityNr" in e and not e.get("identityNr"):
                    navn = e.get("officialName") or e.get("name") or ""
                    if navn:
                        b_navn[mappe].add(navn)
                        b_rader[mappe] += 1
                        b_filer[mappe].add(f"{f.relative_to(arkiv)} {sha(b)}")
                        ident["B navn uten identitetsnummer"].add(navn)

        if mappe == "eierskap" and d is not None:
            for e in gaa(d):
                if "typeValue" in e:
                    c_typer[e["typeValue"]] += 1
                    if e["typeValue"] in PERSON_TYPER and e.get("name"):
                        c_ikke[e["typeValue"]].add(e.get("openNr") or e["name"])
                        ident["C eier med personform"].add(e["name"])
                        if e.get("openNr"):
                            ident["C eier med personform"].add(e["openNr"])

        if mappe == "akvakultur-soknader" and d is not None:
            for e in gaa(d):
                if "applicantorganisationname" in e and e.get("applicantorganisationname") \
                        and not e.get("applicantorganisationnumber"):
                    d_navn.add(e["applicantorganisationname"])
                    ident["D søker uten orgnr"].add(e["applicantorganisationname"])

        if f.name.endswith((".json.gz", ".html.gz")) or b[:1] in (b"{", b"[", b"<"):
            tekst = html.unescape(b.decode("utf-8", "replace"))
            for adr in set(EPOST.findall(tekst)):
                lokal = adr.split("@")[0].lower()
                if not FUNKSJON.match(lokal) and not adr.lower().endswith(
                        (".png", ".jpg", ".svg", ".gif", ".webp")):
                    e_adr[mappe].add(adr.lower())
                    ident["E personlig e-postadresse"].add(adr.lower())

    print("A  Brreg-kropper: enheter med personform og med kontaktfelt")
    print(f"   {'mappe':28} {'kropper':>7} {'m/personform':>12} {'m/kontakt':>9} "
          f"{'enh. personform':>15} {'enh. kontakt':>12}")
    for m in BRREG:
        s = a_kropper[m]
        print(f"   {m:28} {s['kropper']:>7} {s['med_personform']:>12} {s['med_kontakt']:>9} "
              f"{len(a_person[m]):>15} {len(a_kontakt[m]):>12}")
    print("\nB  JSON-kropper: navn med tomt identityNr")
    for m in sorted(b_navn):
        print(f"   {m:28} {len(b_filer[m]):>5} kropper  {b_rader[m]:>5} rader  "
              f"{len(b_navn[m]):>4} ulike navn")
    if not b_navn:
        print("   ingen")
    print("\nC  eierskap: typeValue over alle kropper (rader)")
    for t, n in c_typer.most_common():
        print(f"   {t:40} {n:>7}   ulike med personform: {len(c_ikke.get(t, ()))}")
    print(f"\nD  akvakultur-soknader: søkere med navn og uten orgnr: {len(d_navn)} ulike")
    print("\nE  personlige e-postadresser (ulike), per mappe")
    for m in sorted(e_adr):
        print(f"   {m:40} {len(e_adr[m]):>4}")
    if not e_adr:
        print("   ingen")

    print("\nKropper med funn i A og B (sti, sha256 over utpakket kropp):")
    for k in sorted(eksempel_sha):
        for linje in eksempel_sha[k]:
            print(f"   {k:28} {linje}")
    for m in sorted(b_filer):
        for linje in sorted(b_filer[m]):
            print(f"   B {m:26} {linje}")

    # ------------------------------------------------ publisert?
    filer = [p for p in bygg.rglob("*")
             if p.suffix in (".html", ".xml", ".json", ".csv", ".txt")]
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from core.karantene import synlig_tekst
    tekster = []
    for p in filer:
        raa = p.read_bytes()
        tekster.append(" ".join((synlig_tekst(raa) if p.suffix == ".html"
                                 else raa.decode("utf-8", "replace")).split()).lower())
    alt = "\n".join(tekster)
    # Oppslagstabeller i stedet for et søk per identifikator i hele bygget:
    # sifferfølger (orgnr, telefon uten mellomrom) og e-postadresser.
    sifre = set(re.findall(r"\d+", alt)) | set(re.findall(r"\d[\d ]{6,}\d", alt))
    sifre |= {s.replace(" ", "") for s in sifre}
    adresser = set(EPOST.findall(alt))

    def varianter(s: str) -> set[str]:
        s = " ".join(s.split()).lower()
        ut = {s}
        if "," in s:                          # «Etternavn, Fornavn» -> «Fornavn Etternavn»
            et, _, fo = s.partition(",")
            ut.add(f"{fo.strip()} {et.strip()}")
        return ut

    print(f"\nPUBLISERT? {len(filer)} filer i bygget {bygg.name}")
    for kat in sorted(ident):
        treff = 0
        for s in ident[kat]:
            for v in varianter(s):
                if len(v) < 5:
                    continue
                kompakt = re.sub(r"[ +]", "", v)
                if kompakt.isdigit():
                    funnet = kompakt in sifre or kompakt[-8:] in sifre
                elif "@" in v:
                    funnet = v in adresser
                else:
                    funnet = v in alt
                if funnet:
                    treff += 1
                    break
        print(f"   {kat:34} {len(ident[kat]):>6} identifikatorer   {treff:>4} funnet i bygget")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
