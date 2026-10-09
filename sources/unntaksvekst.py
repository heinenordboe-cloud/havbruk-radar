"""Unntaksvekst 2025/2026 — Mattilsynets oversikt over søknader og vedtak.

Side: https://mattilsynet.no/fisk-og-akvakultur/
      kapasitetsokning-2025-2026-oversikt-over-soknader

Målt 09.10.2026, se docs/MALING-UNNTAKSVEKST.md. Kildens egen
dokumentasjon er docs/KILDE-UNNTAKSVEKST.md.

## Hvorfor lista hentes ukentlig

Siden er en håndskrevet HTML-tabell som oppdateres løpende, og den er
ikke arkivert noe sted. Den finnes ikke i Mattilsynets åpne API.
Versjonen vi ikke henter, er borte (regel 5).

## CDN-et kan gi oss en gammel kopi

Kroppen kom fra Googles CDN med `age: 34394` og
`s-maxage=31536000` da den ble målt. Det vi får, kan være timer — i
prinsippet måneder — gammelt, og hvor fort en endring slår igjennom er
UBELAGT. `Date`, `Age`, `X-Cache-Hit` og `Cache-Control` skrives derfor
i kjøringsloggen OG i det arkiverte svaret, slik at en uke der lista
står stille kan skilles fra en uke der vi fikk et gammelt eksemplar.

`published_at` settes IKKE. Siden sender ingen `Last-Modified`, og
`Date - Age` er da CDN-et hentet kroppen fra opphavet — dets
`fetched_at`, ikke Mattilsynets utgivelse. Samme skille som 1b-7 gjør
for Waybacks `Memento-Datetime`.

## PERSONVERN: søkernavnet slippes bare gjennom med et orgnr

Lista har ingen organisasjonsnummer, bare et søkernavn skrevet for hånd
(«Lingalaks», «Marø Havbruk og E. Karstensen Fiskeoppdrett»). Et navn
uten nummer kan være et enkeltpersonforetak, og da er det et menneske.

Navnet tas bare med når det kobles ENTYDIG til et organisasjonsnummer
med selskapsform, slik:

  * Kandidatene er ALLE enheter i Fiskeridirektoratets `/entities` —
    også personene. De brukes i minnet for å avgjøre om navnet er
    entydig, og forlater aldri `fetch()`.
  * Navnet sammenlignes ETTER normalisering (store bokstaver, mellomrom,
    selskapsformen i enden strøket). Ingen likhetsgrad, ingen prefiks:
    «Sjøtroll Havbruk» er ikke «SJØTROLL HAVBRUK SJØ AS».
  * Nøyaktig ÉN kandidat, og den skal ha ni siffer og en form som
    `sources/eierskap.FORM_KART` oversetter til noe som IKKE er en
    personform. Oversettelsen og personprøven importeres derfra, ikke
    kopieres: to lister som skal si det samme er formen F6/F7 hadde.

Alt annet — ingen treff, flere treff, personform, ukjent form — betyr
at søkeren UTELATES. «Vet ikke» betyr filtrer ut. Raden beholdes med
lokalitet, PO, resultat og saksnummer, og `soker_utelatt = ja`.

Filtreringen skjer i `fetch()`, FØR arkivering. Rå-arkivet ligger i git
og er append-only; et navn på et enkeltpersonforetak som kommer inn der,
kan ikke fjernes igjen. Det arkiverte er derfor IKKE HTML-kroppen, men
tabellen etter filteret, med kroppens sha256 og størrelse ved siden av.
Samme brudd på hovedregelen og samme presedens som `enhetsregisteret`,
`eierskap` og `romming`.

## Lokalitetsnummer: koblingsregelen fra målingen

Lista har ikke lokalitetsnummer. Det slås opp i Akvakulturregisteret
(`/sites`) på navn + produksjonsområde, og hver rad merkes med HVORDAN:

    entydig       nøyaktig ett register-navn i oppgitt PO
    via_soker     flere like navn i PO, og nøyaktig én av dem bærer en
                  tillatelse eid av søkerens orgnr
    usikker       navnet finnes ikke i PO, men nøyaktig én lokalitet i
                  PO er en skrivevariant — se `_skrivevariant()`.
                  Nummeret står, MERKET; det er ikke bekreftet
    flertydig     flere kandidater som ikke lar seg skille
    annen_po      navnet finnes, men ikke i oppgitt PO
    ikke_funnet   ingen kandidat

Bare `entydig` og `via_soker` er koblinger. `usikker` er et forslag.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from html.parser import HTMLParser
from typing import Any, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from core.domene import UTTOMMENDE
from core import persondata
from sources import _http
from sources.eierskap import FORM_KART, er_organisasjonsnummer, er_person

STANDARD_URL = ("https://mattilsynet.no/fisk-og-akvakultur/"
                "kapasitetsokning-2025-2026-oversikt-over-soknader")
PUBAQUA_BASE = "https://api.fiskeridir.no/pub-aqua/api/v1"

# pub-aqua: inklusivt `range`, tak 100. Se sources/akvakultur.py.
SPENN = 100
MAKS_SIDER = 400

# Kolonnene slik de står i tabellhodet, MÅLT 09.10.2026. Endres hodet,
# kaster `les_tabell()` — en kolonne som har byttet plass ville ellers
# lagt resultatet i saksnummerfeltet uten at noen så det.
KOLONNER = ("Søker", "Lokalitet", "Prod.område", "Resultat", "Saksnummer")

# Headerne som sier noe om HVOR GAMMEL kopien er. Se modulens docstring.
CACHE_HEADERE = ("date", "age", "x-cache-hit", "cache-control",
                 "last-modified", "etag")

# Selskapsformer som strykes i enden av et navn før sammenligning.
# Bare formene, aldri bransjeord: «Fiskeoppdrett» er en del av navnet.
_FORM_SUFFIKS = re.compile(r"\s+(AS|ASA|SA|DA|ANS|ENK|BA)$")

# Retningsord Mattilsynet skriver ut og registeret forkorter.
_RETNING = {"VEST": "V", "AUST": "Ø", "ØST": "Ø", "NORD": "N", "SØR": "S"}

# Terskel for skrivevariant. Valgt mot målingens ti varianter: den
# laveste av dem (GOURTESJOKAH/GOURTESJOUKA) har 0,92 etter
# normalisering, ØKSENGÅRDEN/ØKSENGÅRD 0,9. Det er en markering, ikke en
# kobling — se `_skrivevariant()`.
LIKHET = 0.85


# ------------------------------------------------------------ tabellen

class _Tabell(HTMLParser):
    """Rader i sidens tabeller. `<br>` blir linjeskift i cella."""

    def __init__(self) -> None:
        super().__init__()
        self.tabeller: list[list[list[str]]] = []
        self._rad: list[str] | None = None
        self._celle: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tabeller.append([])
        elif tag == "tr" and self.tabeller:
            self._rad = []
        elif tag in ("td", "th") and self._rad is not None:
            self._celle = []
        elif tag == "br" and self._celle is not None:
            self._celle.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._celle is not None:
            self._rad.append("".join(self._celle))
            self._celle = None
        elif tag == "tr" and self._rad is not None:
            self.tabeller[-1].append(self._rad)
            self._rad = None

    def handle_data(self, data):
        if self._celle is not None:
            self._celle.append(data)


def _ren(tekst: str) -> str:
    return " ".join(str(tekst or "").split())


def saksnumre(celle: str) -> list[str]:
    """Saksnumrene i én celle, sortert. Tåler komma OG linjeskift —
    målingen fant begge (Gnarnesvika har linjeskift, to andre komma)."""
    return sorted({s for s in re.split(r"[,\s]+", celle or "") if s})


def les_tabell(html: str) -> list[dict]:
    """Tabellen som lister med kildens egne ord, ingen tolkning.

    Kaster hvis det ikke finnes nøyaktig én tabell med de fem kjente
    kolonnene, eller hvis den er tom. En side som er bygget om skal
    stoppe kilden, ikke gi et tomt snapshot som leses som at alle
    søknadene er trukket.
    """
    p = _Tabell()
    p.feed(html)
    treff = [t for t in p.tabeller
             if t and tuple(_ren(c) for c in t[0]) == KOLONNER]
    if len(treff) != 1:
        hoder = [tuple(_ren(c) for c in t[0]) for t in p.tabeller if t]
        raise ValueError(
            f"unntaksvekst: fant {len(treff)} tabeller med kolonnene "
            f"{KOLONNER}, ventet 1. Tabellhoder på siden: {hoder}")
    rader = []
    for celler in treff[0][1:]:
        if len(celler) != len(KOLONNER):
            raise ValueError(
                f"unntaksvekst: rad med {len(celler)} celler, ventet "
                f"{len(KOLONNER)}: {celler!r}")
        soker, lok, po, res, saks = celler
        rader.append({"soker": _ren(soker), "lokalitet": _ren(lok),
                      "po": _ren(po), "resultat": _ren(res),
                      "saksnumre": saksnumre(saks)})
    if not rader:
        raise ValueError("unntaksvekst: tabellen har ingen rader.")
    return rader


# ------------------------------------------------------------- søkeren

def _navnenokkel(navn: str) -> str:
    """Store bokstaver, ett mellomrom, selskapsformen i enden strøket."""
    return _FORM_SUFFIKS.sub("", _ren(navn).upper())


def koble_soker(soker: str, enheter: list[dict]) -> dict | None:
    """{orgnr, organisasjonsform, registernavn} eller None.

    None betyr «søkeren skal ikke lagres». Se modulens docstring for de
    tre vilkårene. `enheter` er HELE `/entities`, med personene — en
    person med samme navn som et AS gjør navnet flertydig, og det er
    nettopp det tilfellet der et feilaktig treff ville vært verst.
    """
    nokkel = _navnenokkel(soker)
    if not nokkel:
        return None
    treff = [e for e in enheter if _navnenokkel(e.get("name") or "") == nokkel]
    if len(treff) != 1:
        return None
    e = treff[0]
    type_verdi = str(e.get("typeValue") or "")
    form = FORM_KART.get(type_verdi, "")
    orgnr = str(e.get("openNr") or "").strip()
    if (not form or er_person(type_verdi) or persondata.er_personform(form)
            or not er_organisasjonsnummer(orgnr)):
        return None
    return {"orgnr": orgnr, "organisasjonsform": form,
            "registernavn": str(e.get("name") or "")}


# ---------------------------------------------------------- lokaliteten

def _lokalitetsnokkel(navn: str) -> str:
    return _ren(navn).upper()


def _variantform(navn: str) -> str:
    """Navnet med retningsord forkortet, for skrivevariant-prøven."""
    ord_ = _lokalitetsnokkel(navn).split(" ")
    return " ".join(_RETNING.get(o, o) for o in ord_)


def _skrivevariant(a: str, b: str) -> bool:
    """Er `a` og `b` sannsynligvis samme lokalitet skrevet ulikt?

    To prøver, og begge er SVAKE med vilje — treffet merkes `usikker`
    og telles ikke som koblet:

      * det ene navnet er det andre pluss ett ord til slutt
        (HAMNSUNDET / HAMNSUNDET I, KVALØY / KVALØY Ø)
      * tegnlikhet minst `LIKHET` etter at retningsord er forkortet
        (SKYSSELVIKA VEST / SKYSSELVIKA V, HUNDSHOLMEN / HUNDHOLMEN)
    """
    x, y = _variantform(a), _variantform(b)
    if x == y:
        return True
    kort, lang = sorted((x, y), key=len)
    if lang.startswith(kort + " ") and " " not in lang[len(kort) + 1:]:
        return True
    return difflib.SequenceMatcher(None, x, y).ratio() >= LIKHET


def koble_lokalitet(navn: str, po: str, lokaliteter: list[dict],
                    eiere_per_lok: dict[str, set[str]],
                    soker_orgnr: str = "") -> dict:
    """{kobling, lokalitet_nr, kandidater} etter koblingsregelen.

    `lokaliteter` er [{nr, navn, po}], `eiere_per_lok` er
    {lokalitetsnummer: {orgnr for aktive tillatelser}}.
    """
    nokkel = _lokalitetsnokkel(navn)
    i_po = [l for l in lokaliteter if l["po"] == po]
    like = [l for l in i_po if _lokalitetsnokkel(l["navn"]) == nokkel]

    if len(like) == 1:
        return {"kobling": "entydig", "lokalitet_nr": like[0]["nr"],
                "kandidater": [like[0]["nr"]]}
    if len(like) > 1:
        kand = sorted(l["nr"] for l in like)
        if soker_orgnr:
            hans = [n for n in kand if soker_orgnr in eiere_per_lok.get(n, set())]
            if len(hans) == 1:
                return {"kobling": "via_soker", "lokalitet_nr": hans[0],
                        "kandidater": kand}
        return {"kobling": "flertydig", "lokalitet_nr": "", "kandidater": kand}

    varianter = sorted(l["nr"] for l in i_po if _skrivevariant(navn, l["navn"]))
    if len(varianter) == 1:
        return {"kobling": "usikker", "lokalitet_nr": varianter[0],
                "kandidater": varianter}
    if len(varianter) > 1:
        return {"kobling": "flertydig", "lokalitet_nr": "",
                "kandidater": varianter}

    andre = sorted(l["nr"] for l in lokaliteter
                   if _lokalitetsnokkel(l["navn"]) == nokkel)
    if andre:
        return {"kobling": "annen_po", "lokalitet_nr": "", "kandidater": andre}
    return {"kobling": "ikke_funnet", "lokalitet_nr": "", "kandidater": []}


KOBLET = frozenset({"entydig", "via_soker"})


def bygg_rader(tabell: list[dict], enheter: list[dict],
               lokaliteter: list[dict],
               eiere_per_lok: dict[str, set[str]]) -> list[dict]:
    """Tabellen FILTRERT og koblet. Dette er det som arkiveres.

    Søkernavnet står bare på rader der `koble_soker()` lyktes. Ingen
    annen opplysning om søkeren — heller ikke at navnet fantes — går
    videre.
    """
    ut = []
    for r in tabell:
        soker = koble_soker(r["soker"], enheter)
        lok = koble_lokalitet(r["lokalitet"], r["po"], lokaliteter,
                              eiere_per_lok, soker["orgnr"] if soker else "")
        rad = {"lokalitet": r["lokalitet"], "po": r["po"],
               "resultat": r["resultat"], "saksnumre": r["saksnumre"],
               **lok}
        if soker:
            rad.update(soker=r["soker"], soker_orgnr=soker["orgnr"],
                       organisasjonsform=soker["organisasjonsform"],
                       soker_registernavn=soker["registernavn"])
        ut.append(rad)
    return ut


def nokkel(rad: dict) -> str:
    """entity_id: saksnummer + lokalitetsnavn + PO.

    Raden er søker × lokalitet (målingen punkt 3). Saksnummeret skiller
    søkerne — tre søkere på Andal har tre saksnummer — og står uansett
    om søkeren gjør det. Navnet er Mattilsynets, ikke registerets, så
    nøkkelen flytter seg ikke om koblingen endres.
    """
    return (f"{'+'.join(rad['saksnumre'])}|"
            f"{_lokalitetsnokkel(rad['lokalitet'])}|PO{rad['po']}")


class Unntaksvekst(Source):
    name = "unntaksvekst"
    entity_type = "soknad_lokalitet"
    version = "1"

    # UBELAGT. Mattilsynets API er NLOD 2.0 (målingen punkt 2), men
    # lista ligger ikke der, og vilkårene for nettsidens innhold er ikke
    # lest. Det holder også kilden ute av nettstedet, som bestilt — se
    # `nettsted.ubelagte()`.
    attribusjon = None

    # Lista sier hva som er søkt og avgjort NÅ. En ny henting erstatter
    # den forrige som svar på det.
    partisjonering = "henting"
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.unntaksvekst.aktiv", False))

    # ---- henting -------------------------------------------------------

    def _pubaqua(self, c: httpx.Client, sti: str) -> list[dict]:
        base = get("kilder.unntaksvekst.pubaqua_url", PUBAQUA_BASE).rstrip("/")
        ut: list[dict] = []
        for i in range(MAKS_SIDER):
            d = _http.get(c, f"{base}{sti}", hva=f"unntaksvekst {sti} {i}",
                          params={"range": f"{i * SPENN}-{i * SPENN + SPENN - 1}"}
                          ).json()
            if not isinstance(d, list):
                raise ValueError(f"unntaksvekst: {sti} ga ikke en liste")
            ut += d
            if len(d) < SPENN:
                return ut
        raise RuntimeError(f"unntaksvekst: {sti} over {MAKS_SIDER} sider")

    def fetch(self, kjoredato: str) -> dict:
        """Lista, FILTRERT og koblet, med kroppens hash og cacheheaderne.

        `kjoredato` brukes ikke: lista sier hva som gjelder nå.

        `utvalg` er `{}`: vi henter hele lista. At søkernavn faller fra,
        står på hver rad (`soker_utelatt`), ikke i utvalget — det er
        ikke et søkekriterium, det er hva vi lagrer.
        """
        url = get("kilder.unntaksvekst.url", STANDARD_URL)
        self.utvalg = {}
        self.endepunkt = url
        self.advarsler = []

        with httpx.Client(timeout=120.0, follow_redirects=True,
                          headers={"Accept": "application/json"}) as c:
            svar = _http.get(c, url, hva="unntaksvekst side",
                             headers={"Accept": "text/html"})
            kropp = svar.content
            headere = {h: svar.headers[h] for h in CACHE_HEADERE
                       if h in svar.headers}
            print(f"    [unntaksvekst] sha256 {hashlib.sha256(kropp).hexdigest()[:12]} "
                  + " ".join(f"{h}={headere.get(h, '-')!r}"
                             for h in ("date", "age", "x-cache-hit")))

            tabell = les_tabell(kropp.decode(svar.encoding or "utf-8"))

            enheter = self._pubaqua(c, "/entities")
            sites = self._pubaqua(c, "/sites")
            lisenser = self._pubaqua(c, "/licenses")

        lokaliteter = [{"nr": str(s.get("siteNr")), "navn": str(s.get("name") or ""),
                        "po": str((s.get("placement") or {}).get("prodAreaCode") or "")}
                       for s in sites if s.get("siteNr") is not None]
        eiere: dict[str, set[str]] = {}
        for l in lisenser:
            orgnr = str(l.get("openLegalEntityNr") or "").strip()
            for k in l.get("connections") or []:
                if k.get("active") and k.get("siteNr") and orgnr:
                    eiere.setdefault(str(k["siteNr"]), set()).add(orgnr)

        rader = bygg_rader(tabell, enheter, lokaliteter, eiere)

        koblet = sum(r["kobling"] in KOBLET for r in rader)
        med_soker = sum("soker" in r for r in rader)
        print(f"    [unntaksvekst] {len(rader)} rader, {koblet} med entydig "
              f"lokalitet, {med_soker} med søker")
        if not headere.get("age") and headere.get("x-cache-hit") is None:
            self.advarsler = [
                "unntaksvekst: verken Age eller X-Cache-Hit i svaret. CDN-et "
                "er byttet eller fjernet, og kopiens alder kan ikke lenger "
                "leses av headerne — se docs/KILDE-UNNTAKSVEKST.md."]

        return {"url": str(svar.url), "status": svar.status_code,
                "sha256": hashlib.sha256(kropp).hexdigest(),
                "bytes": len(kropp), "headere": headere, "rader": rader}

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: dict, observed_at: str) -> Iterable[Observation]:
        """LAG 2. Søkeren slippes bare gjennom med orgnr og selskapsform,
        også om en arkivert kropp skulle bære den uten."""
        self.domene = UTTOMMENDE

        sett: set[str] = set()
        for rad in (raw or {}).get("rader") or []:
            eid = nokkel(rad)
            if eid in sett:
                raise ValueError(
                    f"unntaksvekst: nøkkelen {eid!r} står to ganger. "
                    f"`snapshot.NOKKEL` ville beholdt den ene stille.")
            sett.add(eid)

            felles = dict(entity_id=eid, entity_type=self.entity_type,
                          entity_name=rad["lokalitet"], source=self.name,
                          observed_at=observed_at)
            felt: dict[str, Any] = {
                "lokalitet_navn": rad["lokalitet"],
                "prodomraade_kode": rad["po"],
                "resultat": rad["resultat"],
                "saksnummer": "; ".join(rad["saksnumre"]),
                "lokalitet_kobling": rad["kobling"],
                "lokalitet_nr": rad.get("lokalitet_nr") or "",
                "lokalitet_kandidater": "; ".join(rad.get("kandidater") or []),
            }
            form = str(rad.get("organisasjonsform") or "")
            orgnr = str(rad.get("soker_orgnr") or "")
            if (rad.get("soker") and form and not persondata.er_personform(form)
                    and er_organisasjonsnummer(orgnr)):
                felt.update(soker=rad["soker"], soker_orgnr=orgnr,
                            organisasjonsform=form, soker_utelatt="nei")
            else:
                felt["soker_utelatt"] = "ja"

            for f, v in felt.items():
                if v is None or v == "":
                    continue
                yield Observation(field=f, value=str(v), **felles)
