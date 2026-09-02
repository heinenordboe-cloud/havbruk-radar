"""Eierskapskjeden: tillatelse -> juridisk enhet.

Endepunkt: https://api.fiskeridir.no/pub-aqua/api/v1/licenses
           https://api.fiskeridir.no/pub-aqua/api/v1/entities

Verifisert mot levende tjeneste 02.09.2026. Ingen nøkkel, ingen
registrering, ingen autentisering — samme NLOD-vilkår som `akvakultur`,
og attribusjon «Kilde: Fiskeridirektoratet» kreves av enhver
sammenstilling som bruker tallene.

## Leddet som manglet

Repoet har lagret `tillatelser` per lokalitet ukentlig siden uke 1
(`akvakultur`), og selskaper for seg (`enhetsregisteret`). De to har
aldri vært koblet. Denne kilden lukker kjeden:

    lokalitet --(akvakultur.tillatelser)--> tillatelse --(HER)--> selskap

Entiteten er derfor TILLATELSEN og ikke lokaliteten. Det er ikke et
vilkårlig valg: en tillatelse kan henge på mange lokaliteter og en
lokalitet kan bære mange tillatelser, så en rad per lokalitet ville
måttet slå sammen flere eiere til én verdi og miste hvem som eier hva.
Tillatelsen er det ene leddet der forholdet er 1:1 mot en eier.

## Hvorfor /licenses og ikke /entities er ryggraden

Målt 02.09.2026, begge endepunkter, hele svaret:

    /licenses    3036 rader, 31 kall     bærer licenseNr, eier OG
                                         connections[] -> siteNr
    /entities     542 rader,  6 kall     bærer navn, type og ADRESSER,
                                         men INGEN kobling til lokalitet

`/entities` kan ikke være ryggraden fordi den ikke inneholder leddet vi
mangler. `/licenses` bærer hele kjeden i ett endepunkt.

`/entities` hentes likevel, til nøyaktig ÉN ting: organisasjonsformen,
som er det eneste stedet man kan se om eieren er et menneske. Se under.

## PERSONVERN — den harde grensen, og hvorfor ni siffer ikke holder

Forutsetningen da denne kilden ble bestilt var at `openLegalEntityNr`
kunne være et FØDSELSNUMMER, og at en ni-siffer-test derfor ville skille
selskap fra person. **Begge deler ble målt, og bildet er et annet.**

Målt over alle 3036 tillatelser, alle 3036 `grantInformation`, alle 542
enheter og 216 overføringer:

    ellevesifrede numre:  0    (i alle fire feltene)
    nisifrede:         2974 / 2965 / 499 / 214
    TOMME:               62 /   71 /  43 /   2

Fiskeridirektoratet publiserer altså ikke fødselsnummer i det hele tatt.
For fysiske personer er nummeret TOMT — og navnet står likevel:
«HOELFELDT LUND, PER CHRISTIAN», «LYSEN ANNE».

**Og verre: ni siffer skiller ikke person fra selskap.** Av de 542
enhetene er 8 `SoleProprietorship` — enkeltpersonforetak — og

    8 av 8 ENK har NI SIFFER og ville passert filteret.

Det er ordrett feilen CLAUDE.md regel 3 er skrevet om: «åpningen 16.08
ble begrunnet med at alle entity_id var ni siffer, og et ENK har ni
siffer akkurat som et AS». Et ENK er ikke et eget rettssubjekt;
foretaket ER innehaveren.

Derfor filtreres det på TYPE og ikke på sifferlengde. Sifferprøven er
beholdt som et ANDRE vilkår, ikke som det bærende — den fanger de 43
privatpersonene, som har tomt nummer.

`/entities` bærer dessuten `addresses` med type `ResidentialLocation` og
`officialSourceType: "FREG"` — altså BOSTEDSADRESSER fra Folkeregisteret,
43 av dem. De hentes inn i minnet og forlater aldri `fetch()`: kroppen
som arkiveres er den FILTRERTE, av samme grunn som `enhetsregisteret`
filtrerer før arkivering. Se `docs/beslutninger/2026-09-02-eierskapskjeden.md`.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

STANDARD_BASE = "https://api.fiskeridir.no/pub-aqua/api/v1"

# Tjenesten avviser range-spenn over 100 med 400. Målt: 0-99 gir 100
# rader, 0-499 gir 400 Bad Request.
SPENN = 100

# Taket finnes av samme grunn som i `akvakultur`: en paginering uten tak
# er en uendelig løkke den dagen tjenesten slutter å telle ned.
MAKS_SIDER = 400

# ---------------------------------------------------------------------
# Hvem er et MENNESKE
#
# pub-aqua bruker sitt eget vokabular, ikke Brregs koder. Lista er MÅLT
# på hele /entities 02.09.2026, ikke lest ut av dokumentasjon:
#
#     LimitedLiabilityCompany     469      PublicLimitedCompany       2
#     Person                       43      UnlimitedLiabilityCompany  2
#     OrganizationalSection         8      Association                1
#     SoleProprietorship            8      CoopCompany                1
#     Foundation                    3      Municipality               1
#     JointLiabilityCompany         3      JointlyOwnedShippingCompany 1
#
# `Person` er en fysisk person (typeName «Privatperson», adresse fra
# FREG). `SoleProprietorship` er enkeltpersonforetak — regel 3 og
# core/persondata.PERSONFORMER sier at foretaket ER innehaveren.
#
# DA, ANS og partrederi står IKKE her, og det er samme vurdering som i
# core/persondata.py: de er egne rettssubjekter med eget
# organisasjonsnummer og egen partsevne.
PERSONTYPER = frozenset({"Person", "SoleProprietorship"})

# pub-aqua-type -> Brreg-kode. VERIFISERT ved å krysse eiernes
# organisasjonsnummer mot vårt eget enhetsregister-snapshot 02.09.2026:
# 367 enheter overlappet, og de fem parene under stemte 1:1 uten et
# eneste avvik.
#
# Merk at de to ansvarlige selskapsformene ligger MOTSATT av hva navnene
# antyder — JointLiabilityCompany er DA og UnlimitedLiabilityCompany er
# ANS. Det er nettopp derfor kartet er målt og ikke gjettet.
#
# Formene uten overlapp (Foundation, Municipality, Association,
# JointlyOwnedShippingCompany, OrganizationalSection) står BEVISST ikke
# her: vi har ikke Brregs ord for dem, og en gjettet kode ville vært en
# påstand på en tredjeparts vegne. De får `eier_type` ordrett i stedet.
FORM_KART = {
    "LimitedLiabilityCompany": "AS",
    "PublicLimitedCompany": "ASA",
    "JointLiabilityCompany": "DA",
    "UnlimitedLiabilityCompany": "ANS",
    "CoopCompany": "SA",
    # Juridisk sikkert, ikke målt: et enkeltpersonforetak ER et ENK.
    # Står her for at core/snapshot.py sin vakt skal ha noe å bite på
    # dersom en slik rad noen gang overlever begge filtrene.
    "SoleProprietorship": "ENK",
}

_NI_SIFFER = re.compile(r"^\d{9}$")


def er_organisasjonsnummer(nr: object) -> bool:
    """Nøyaktig ni siffer. Tåler None og tall like godt som streng.

    Dette er det ANDRE vilkåret, ikke det bærende. Det fanger de 43
    privatpersonene, som har TOMT nummer — men det kan ikke skille et
    enkeltpersonforetak fra et aksjeselskap, for begge har ni siffer.
    Se modulens docstring.
    """
    if nr is None:
        return False
    return bool(_NI_SIFFER.match(str(nr).strip()))


def er_person(type_verdi: object) -> bool:
    """Sant hvis eiertypen betyr «denne eieren er et menneske»."""
    return isinstance(type_verdi, str) and type_verdi.strip() in PERSONTYPER


def _tillat(eier_type: object, orgnr: object) -> bool:
    """Alle tre vilkårene. Én linje, ett sted, brukt i både fetch og parse.

    1. Typen må være KJENT. En tillatelse hvis eier ikke finnes i
       `/entities` har ingen type, og da vet vi ikke om eieren er et
       menneske. «Vet ikke» skal ikke bety «slipp gjennom».

       Dette er MOTSATT fallback av frekvensvakten, og forskjellen er
       tilsiktet: der er kostnaden ved å ta feil en ekstra fil med
       løpenummer, her er den et personregister i en append-only
       historikk. Fallbacken skal peke mot den billigste feilen, og det
       er ikke den samme retningen i de to tilfellene.

       Målt 02.09.2026 koster vilkåret ingenting: alle 536 distinkte
       eier-ID-er i `/licenses` finnes i `/entities`.

    2. Typen må ikke være en personform. Dette er prøven som svarer på
       spørsmålet vi faktisk stiller.

    3. Nummeret må være ni siffer. En ekstra lås, ikke hovedregelen —
       den kan ikke skille ENK fra AS. Se modulens docstring.
    """
    if not isinstance(eier_type, str) or not eier_type.strip():
        return False
    return not er_person(eier_type) and er_organisasjonsnummer(orgnr)


# ---------------------------------------------------------------- felter
#
# Feltnavn er en kontrakt mot historikken (se `akvakultur`). ADRESSER er
# bevisst ikke med — verken forretnings- eller bostedsadresse. Regel 3.
FELTER: dict[str, Any] = {
    "eier_orgnr": lambda l, e: l.get("openLegalEntityNr"),
    "eier_navn": lambda l, e: l.get("legalEntityName"),
    # Kildens EGET ord om eierformen, ordrett. Se FORM_KART for hvorfor
    # oversettelsen til Brreg-kode bare gjøres der den er verifisert.
    "eier_type": lambda l, e: (e or {}).get("typeValue"),
    "tillatelse_type": lambda l, e: (l.get("type") or {}).get("tag"),
    "tillatelse_formal": lambda l, e: (l.get("type") or {}).get("intentionValue"),
    "produksjonsstadium": lambda l, e: (l.get("type") or {}).get("productionStageValue"),
    "kapasitet": lambda l, e: (l.get("capacity") or {}).get("current"),
    "kapasitet_enhet": lambda l, e: (l.get("capacity") or {}).get("unit"),
    "kapasitet_type": lambda l, e: (l.get("capacity") or {}).get("type"),
    "prodomraade_kode": lambda l, e: (l.get("placement") or {}).get("prodAreaCode"),
    "prodomraade_navn": lambda l, e: (l.get("placement") or {}).get("prodAreaName"),
    "kommunenummer": lambda l, e: (l.get("placement") or {}).get("municipalityCode"),
    "portefoljetype": lambda l, e: (l.get("portfolioType") or {}).get("value"),
    # Hvem tillatelsen OPPRINNELIG ble tildelt. Skiller den seg fra
    # `eier_orgnr`, har tillatelsen skiftet hender — og det er hele
    # spørsmålet denne kilden finnes for.
    "tildelt_orgnr": lambda l, e: (l.get("grantInformation") or {}).get("openLegalEntityNr"),
    "tildelt_navn": lambda l, e: (l.get("grantInformation") or {}).get("legalEntityName"),
    "tildelt_tid": lambda l, e: (l.get("grantInformation") or {}).get("grantedTime"),
}


def _lokaliteter(lisens: dict) -> list[str]:
    """AKTIVE lokalitetsnumre, sortert. Utgåtte koblinger holdes utenfor.

    `connections` bærer både aktive og avsluttede koblinger, med
    `validUntil` satt til år 9999 for de aktive. Vi lagrer de aktive:
    en avsluttet kobling er historikk, og historikken vår er
    snapshot-rekka — ikke et felt som vokser i hver rad.
    """
    ut = {str(k.get("siteNr")) for k in (lisens.get("connections") or [])
          if k.get("active") and k.get("siteNr")}
    return sorted(ut)


class Eierskap(Source):
    name = "eierskap"
    entity_type = "tillatelse"
    version = "1"

    # UKENTLIG, som systemets kadens. Eierskap endres sjeldnere enn
    # lusetall — målt på 250 tillatelser spenner overføringene fra 2006
    # til 2026, med 9-65 i året — men et eierskifte er en HENDELSE med
    # høy verdi, og changeloggen fanger den bare hvis vi har to snapshots
    # rundt den.
    #
    # Kostnaden er 37 kall i uka (31 for tillatelser, 6 for enheter) mot
    # et endepunkt uten nøkkel og uten rate limit vi har sett. Å hente
    # sjeldnere ville spart ingenting som er verdt å spare, og ville
    # gjort hvert eierskifte upresist datert med opptil en måned.
    min_dager_mellom = 7

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.eierskap.aktiv", False))

    # ---- henting -------------------------------------------------------

    def _side(self, c: httpx.Client, sti: str, start: int) -> list[dict]:
        base = get("kilder.eierskap.base_url", STANDARD_BASE).rstrip("/")
        svar = _http.get(c, f"{base}{sti}",
                         params={"range": f"{start}-{start + SPENN - 1}"},
                         hva=f"eierskap {sti} {start}")
        d = svar.json()
        return d if isinstance(d, list) else []

    def _alt(self, c: httpx.Client, sti: str) -> list[dict]:
        ut: list[dict] = []
        for i in range(MAKS_SIDER):
            d = self._side(c, sti, i * SPENN)
            ut += d
            if len(d) < SPENN:
                return ut
        raise RuntimeError(
            f"eierskap{sti}: over {MAKS_SIDER} sider à {SPENN}. Tjenesten "
            f"slutter ikke å telle ned — pagineringen er endret, eller "
            f"filteret vårt treffer ikke."
        )

    def fetch(self, kjoredato: str) -> dict:
        """Tillatelser med eier, FILTRERT før den arkiveres.

        Det arkiverte er ikke det tjenesten sendte, og det er et bevisst
        brudd på hovedregelen om at `fetch()` returnerer råsvaret. Grunnen
        er at råsvaret inneholder BOSTEDSADRESSER fra Folkeregisteret for
        43 navngitte privatpersoner, og rå-arkivet ligger i git —
        append-only, altså uopprettelig. Samme avveining og samme
        løsning som `enhetsregisteret` gjorde 22.08.2026.

        `utvalg` er `{}` og ikke ukjent: vi ber om alle tillatelser og
        får alle tillatelser. At personeide faller fra er VÅR filtrering,
        og den står i `utvalg` slik at et snapshot alene kan svare på hva
        vi lette etter (regel 1b-3).

        `published_at` settes IKKE. Verifisert 02.09.2026: verken
        `/licenses` eller `/entities` sender `Last-Modified` eller
        `ETag`. Regel 1b-7 er tydelig — standarden er «vet ikke», aldri
        hentetidspunktet.
        """
        self.utvalg = {"utelatt": sorted(PERSONTYPER)}

        c = httpx.Client(timeout=120.0, follow_redirects=True)
        try:
            enheter = self._alt(c, "/entities")
            lisenser = self._alt(c, "/licenses")
        finally:
            c.close()

        # LAG 1. Enhetene reduseres til de tre feltene vi faktisk bruker,
        # og personene forsvinner her. `addresses` kopieres aldri videre.
        type_per_id: dict[str, str] = {}
        slanke: list[dict] = []
        for e in enheter:
            if er_person(e.get("typeValue")) or not er_organisasjonsnummer(e.get("openNr")):
                continue
            type_per_id[str(e.get("id"))] = str(e.get("typeValue") or "")
            slanke.append({"id": e.get("id"), "openNr": e.get("openNr"),
                           "typeValue": e.get("typeValue"),
                           "name": e.get("name")})

        beholdt, fjernet = [], 0
        for l in lisenser:
            t = type_per_id.get(str(l.get("legalEntityNrId")))
            if not _tillat(t, l.get("openLegalEntityNr")):
                fjernet += 1
                continue
            beholdt.append(l)

        advarsler: list[str] = []
        if not fjernet:
            # Et filter som aldri fjerner noe er et filter ingen har
            # prøvd mot virkeligheten. Si fra framfor å la det stå stille.
            advarsler.append(
                "eierskap: personfilteret fjernet 0 tillatelser. Enten har "
                "kilden sluttet å publisere personeide tillatelser, eller "
                "så treffer ikke filteret lenger. Undersøk før tallet "
                "brukes som bevis på at ingen persondata kom inn.")
        self.advarsler = advarsler
        self.fjernet_antall = fjernet

        return {"tillatelser": beholdt, "enheter": slanke,
                "personer_fjernet": fjernet}

    def gjelder_for(self, kjoredato: str) -> str:
        """Registeret sier hva som gjelder NÅ. Ingen etterslep, som
        `akvakultur` og `enhetsregisteret`."""
        return kjoredato

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: Any, observed_at: str) -> Iterable[Observation]:
        """LAG 2. Filtreringen gjentas, og det er ikke belte og bukseseler.

        `parse()` er veien en ARKIVERT kropp kommer inn igjen på. Skulle
        en kropp fra før filteret — eller fra en framtidig versjon der
        `fetch()` er endret — spilles av på nytt, er dette laget det
        eneste som står mellom den og disken.

        Samme begrunnelse som `enhetsregisteret.parse()`, og samme form.
        """
        lisenser = (raw or {}).get("tillatelser") or []
        enheter = {str(e.get("id")): e for e in (raw or {}).get("enheter") or []}

        for l in lisenser:
            e = enheter.get(str(l.get("legalEntityNrId")))
            eier_type = (e or {}).get("typeValue")
            orgnr = l.get("openLegalEntityNr")
            if not _tillat(eier_type, orgnr):
                continue

            nr = l.get("licenseNr")
            if not nr:
                continue

            felles = dict(entity_id=str(nr), entity_type=self.entity_type,
                          entity_name=str(nr), source=self.name,
                          observed_at=observed_at)

            for felt, hent in FELTER.items():
                verdi = hent(l, e)
                if verdi is None or verdi == "":
                    continue
                yield Observation(field=felt, value=str(verdi), **felles)

            # Brreg-koden, bare der kartet er verifisert. Uten den ville
            # core/snapshot.py sin personvakt ikke hatt noe å lese.
            form = FORM_KART.get(str(eier_type))
            if form:
                yield Observation(field="organisasjonsform", value=form,
                                  **felles)

            lok = _lokaliteter(l)
            if lok:
                # Semikolon som i `akvakultur.tillatelser` — samme
                # lesemåte for den samme typen liste.
                yield Observation(field="lokaliteter",
                                  value="; ".join(lok), **felles)
                yield Observation(field="lokaliteter_antall",
                                  value=str(len(lok)), **felles)
