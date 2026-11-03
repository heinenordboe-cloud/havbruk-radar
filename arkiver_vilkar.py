"""Arkiverer vilkårssidene kildene våre gis ut under, som kropper med hash.

    python arkiver_vilkar.py                 # arkiver det som finnes nå
    python arkiver_vilkar.py --torrkjor      # si hva som ville skjedd

Kjøres månedlig av `vilkar.yml` i datarepoet.

## Hvorfor

`docs/LISENSKJEDE.md` siterer vilkårene ordrett, med datoen de ble lest.
Fram til 06.10.2026 lå ingen av sidene i arkivet: sitatene var lest, men
ikke tatt vare på, og en påstand om hva en tredjepart skrev en gitt dag
kunne ikke etterprøves mot det som faktisk sto der. Vilkår endres uten at
noe i dataene beveger seg (LISENSKJEDE.md, ingressen), og den forrige
versjonen finnes ikke hos utgiveren når den nye er lagt ut. Samme
argument som CLAUDE.md 1b-5 punkt 2, for en annen slags kropp.

## Hva som lagres

Kroppen slik den kom, gzippet, i `data/arkiv/vilkar-<part>/`, gjennom
`raw.arkiver_ny()`: en kropp som er byte-identisk med en som allerede
ligger der, skrives ikke på nytt. Hashen er sha256 av de ukomprimerte
bytene, som for alle andre arkivkropper.

HTML-sider bærer ofte markup som endrer seg uten at teksten gjør det
(skript-hasher, tokens). Loggfila har derfor også `tekst_sha256`: hashen
av den synlige teksten, så en leser kan se om VILKÅRENE endret seg eller
bare sida rundt dem. Det er en hjelp til å lese, ikke en erstatning for
kroppen.

`published_at` leses fra `Last-Modified` der tjenesten sender den, og
står ellers tom — aldri hentetidspunktet (CLAUDE.md 1b-7).

En kropp som er kortere enn halvparten av forrige versjon, eller som
mangler partens kjennetegn, går i karantene (`regler()`, core/karantene.py)
i stedet for inn i serien, og kjøringen ender rød.

## Hvorfor dette ikke er en kilde

En vilkårsside er ikke data om havbruk, og den gir ingen `Observation`.
Den arkiveres som `arkiver_auksjon.py` gjør: kroppen først, og et
eventuelt uttrekk senere av noe som er skrevet mot en kropp som finnes.

## Kodeproveniens

Fra 06.10.2026, som de andre arkiverte kroppene. Før noe hentes, kaller
skriptet `kodeproveniens.krev_sporbar()`, samme sperre som `run.py`:
arbeidstreet må være rent og HEAD må finnes på origin/main, ellers
stopper det med `::error::` og exit 1. Hver arkivert kropp får
`kode_commit`, `kode_rent` og `fetched_at` i dagens loggfil, ved siden
av sha256-en. Loggfila er sidevogna: én per kjøring, ikke én per kropp.
`--torrkjor` skriver ingen fil og er unntatt, som i run.py. Logger
skrevet før 06.10.2026 har ikke feltene, og de fylles ikke inn i
ettertid (CLAUDE.md regel 2). Se
docs/beslutninger/2026-10-06-arkivkropper-kodeproveniens.md.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys

import httpx

from core import karantene
from core import kodeproveniens
from core import raw as raw_arkiv
from core.karantene import synlig_tekst
from sources import _http

# Én mappe per part, så `arkiver_ny()` sammenligner hver side bare med
# sine egne tidligere kropper. Adressene er de LISENSKJEDE.md siterer.
SIDER = {
    "barentswatch": "https://www.barentswatch.no/artikler/api-vilkar",
    "fiskeridir": ("https://www.fiskeridir.no/statistikk-tall-og-analyse/"
                   "lisens-for-bruk-av-fiskeridirektoratets-data"),
    # FLYTTET. LISENSKJEDE.md siterte `/bruk-av-data-fra-bronnoysund-
    # registrene/apne-data/` (lest 14.09.2026). MÅLT 06.10.2026: den gir
    # 404, og Brregs egen gamle adresse `/produkter-og-tjenester/apne-data/`
    # videresender hit. Lisenssetningen står ordrett på denne siden.
    "brreg": ("https://www.brreg.no/bruke-data-fra-bronnoysundregistrene/"
              "datasett-og-api/"),
    "lovdata": "https://lovdata.no/info/brukeravtale",
    # Fra 09.10.2026: vilkåret `unntaksvekst` og analysesiden for
    # unntaksvekst bygger på. Se sources/unntaksvekst.py, `attribusjon`.
    "mattilsynet": ("https://www.mattilsynet.no/om-mattilsynet/"
                    "vil-du-bruke-innhold-fra-mattilsynet"),
    # Fra 03.11.2026 (docs/MALING-NYE-KILDER.md). NMDCs landingsside for
    # regomr.geojson, som utgivelsesvakt.py arkiverer: CC BY 4.0 står her
    # (LISENSKJEDE merknad D). DOI-en videresender hit.
    "nmdc": ("https://metadata.nmdc.no/metadata-api/landingpage/"
             "cf16c4a384162756a63ab26c9380e000"),
    # Bransjemedia, kandidat c. Arkivert fordi de er grunnen til at RSS-
    # fangsten IKKE bygges: Fiskeribladet og Intrafish krever avtale for
    # «skraping, crawling, indeksering, tekst/datautvinning», og Kyst.no
    # har bare abonnementsvilkår. iLaks har ingen vilkårsside å arkivere.
    "fiskeribladet": "https://www.fiskeribladet.no/vilkar",
    "intrafish": "https://www.intrafish.no/vilkar",
    "kyst": ("https://www.oceanspacemedia.com/"
             "oceanspace-media-generelle-abonnementsvilkar/1583266"),
}

LOGG_KILDE = "vilkar"

# ## Når en kropp er mistenkt (MALING-DRIFT F1.1, fra 03.11.2026)
#
# Til 03.11.2026 lagret skriptet alt som kom med status 200: en feilside,
# en tom liste og en halv kropp ble fem nye kropper hver, og kjøringen var
# grønn. Nå går en mistenkt kropp i karantene (core/karantene.py), og
# kjøringen ender rød.
#
# Mot forrige versjon av samme vilkår:
#   * synlig tekst minst HALVPARTEN av forrige versjons, og
#   * kjennetegnet under i den synlige teksten.
# Første versjon av et vilkår har ingen forrige, og ikke noe målt
# kjennetegn: der gjelder bare minstelengden.
#
# KJENNETEGNET er målt i arkivet 03.11.2026, i hver kropp som lå der (2–3
# per part, analyse/drift/kjennetegn.txt). Fire av sidene nevner lisensen
# de er arkivert for, NLOD; Mattilsynets side nevner den ikke, men hviler
# på opphavsretten. Forsvinner ordet, er det enten ikke vilkårssiden
# lenger, eller så har vilkåret endret seg — begge deler skal en leser se
# før kroppen blir forrige versjon.
KJENNETEGN = {
    "barentswatch": "NLOD",
    "fiskeridir": "NLOD",
    "brreg": "NLOD",
    "lovdata": "NLOD",
    "mattilsynet": "opphavsrett",
    # Fra 03.11.2026, målt i den synlige teksten på sidene slik de ble
    # hentet den dagen (docs/MALING-NYE-KILDER.md, c og e). NMDC: lisensen
    # utgivelsesvakten hviler på. Fiskeribladet og Intrafish: ordet i
    # forbudet som er grunnen til at RSS-fangsten ikke bygges. Kyst.no:
    # utgiveren, fordi sida ikke sier noe om gjenbruk å kjenne den igjen på.
    "nmdc": "CC BY 4.0",
    "fiskeribladet": "datautvinning",
    "intrafish": "datamining",
    "kyst": "Oceanspace Media",
}
# Halvparten av den korteste synlige teksten i arkivet, vilkar-brreg med
# 1 480 tegn (analyse/drift/kjennetegn.txt). Samme halvering som regelen
# mot forrige versjon; feilsiden i MALING-DRIFT har 62.
MINSTE_TEKST = 740
ANDEL_AV_FORRIGE = 0.5


def kilde(part: str) -> str:
    return f"vilkar-{part}"


def regler(part: str) -> list:
    """Reglene for en ny kropp for `part`, mot det som ligger i serien."""
    tidligere = raw_arkiv.kropper(kilde(part))
    if not tidligere:
        return [karantene.ikke_tom, karantene.minst_tekst(MINSTE_TEKST)]
    with gzip.open(tidligere[-1], "rb") as f:
        forrige = f.read()
    ut = [karantene.ikke_tom, karantene.andel_av_forrige(forrige, ANDEL_AV_FORRIGE)]
    if part in KJENNETEGN:
        ut.append(karantene.nevner(KJENNETEGN[part]))
    else:
        print(f"::warning::Vilkårsarkivering: {part} har ingen målt KJENNETEGN. "
              f"Mål det i arkivet (analyse/drift/kjennetegn.py) og før det opp.")
    return ut


def _hent(klient: httpx.Client, url: str) -> tuple[bytes, str]:
    r = _http.get(klient, url, hva=f"vilkårsarkiv {url}")
    return r.content, r.headers.get("Last-Modified", "")


def arkiver(klient: httpx.Client, part: str, url: str, dato: str,
            torr: bool) -> dict:
    try:
        kropp, utgitt = _hent(klient, url)
    except Exception as e:
        print(f"::error::Vilkårsarkivering: {url} kunne ikke hentes: {e}")
        return {"part": part, "url": url, "feil": str(e)}

    tekst_sha = hashlib.sha256(synlig_tekst(kropp).encode("utf-8")).hexdigest()
    post = {"part": part, "url": url, "byte": len(kropp),
            "tekst_sha256": tekst_sha, "published_at": utgitt}
    grunner = karantene.vurder(kropp, regler(part))
    if torr:
        print(f"  {'ville satt i karantene' if grunner else 'ville arkivert'}  "
              f"{len(kropp):>7} B  {url}" + (f"  ({'; '.join(grunner)})" if grunner else ""))
        return dict(post, torrkjoring=True, grunn=grunner)

    # Når VI hentet kroppen (CLAUDE.md 1b-7: OSS, ikke kilden).
    hentet = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if grunner:
        return dict(post, **karantene.sett_inn(
            kilde(part), dato, kropp, grunner, jobb="vilkar", fetched_at=hentet,
            url=url, published_at=utgitt, tekst_sha256=tekst_sha))
    sha, ny = raw_arkiv.arkiver_ny(kilde(part), dato, kropp)
    print(f"  {'NY' if ny else 'uendret':<8} {len(kropp):>7} B  "
          f"{sha[:16]}…  tekst {tekst_sha[:12]}…  {url}")
    return dict(post, sha256=sha, ny=ny, fetched_at=hentet)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--torrkjor", action="store_true")
    p.add_argument("--dato", default="",
                   help="observed_at for arkivfilene. Standard: i dag. "
                        "Sendes inn og leses ikke av noen underfunksjon (1b).")
    a = p.parse_args(argv)

    dato = a.dato or dt.date.today().isoformat()
    print(f"Vilkårsarkivering {dato}" + ("  (TØRRKJØRING)" if a.torrkjor else ""))

    # KAN KJØRINGEN GJØRES REDE FOR? Spurt før noe hentes. Se modulens
    # docstring, «Kodeproveniens».
    proveniens: dict = {}
    if not a.torrkjor:
        try:
            sha, tilstand = kodeproveniens.krev_sporbar()
        except kodeproveniens.IkkeSporbar as e:
            print(f"::error::Vilkårsarkiveringen startet ikke: {e}")
            return 1
        proveniens = {"kode_commit": sha, "kode_rent": tilstand}
        print(f"  kode        {sha[:12]}  rent, på origin/main")

    # Ingen egen User-Agent: `sources/_http.py` setter den for alle kall,
    # med kontaktadressen fra HAVBRUK_KONTAKT, og overstyrer kallerens.
    with httpx.Client(timeout=60.0, follow_redirects=True) as klient:
        logg = [arkiver(klient, part, url, dato, a.torrkjor)
                for part, url in SIDER.items()]

    for r in logg:
        if "sha256" in r:
            r.update(proveniens)

    nye = sum(1 for r in logg if r.get("ny"))
    feil = sum(1 for r in logg if "feil" in r)
    # En tørrkjøring som ville satt noe i karantene, er like rød som den
    # ekte ville vært: det er det den finnes for å si.
    karantenert = sum(1 for r in logg if r.get("status") == karantene.STATUS
                      or (r.get("torrkjoring") and r.get("grunn")))
    print(f"\n{len(logg)} side(r), {nye} ny(e) kropp(er), {feil} feil, "
          f"{karantenert} i karantene.")

    if not a.torrkjor:
        mappe = raw_arkiv.ARKIV_DIR / LOGG_KILDE
        mappe.mkdir(parents=True, exist_ok=True)
        sti = mappe / f"{dato}.logg.json"
        if not sti.exists():
            sti.write_text(json.dumps(logg, indent=2, ensure_ascii=False))
            print(f"Logg: {sti}")

    # RØD ved én eneste feil. Kjøringen er månedlig, og en vilkårsside som
    # ikke kan hentes er en måned uten belegg for den parten. De andre
    # sidene er arkivert uansett. En kropp i karantene er det samme: den
    # er tatt vare på, men parten har ingen ny versjon i serien.
    return 1 if feil or karantenert else 0


if __name__ == "__main__":
    sys.exit(main())
