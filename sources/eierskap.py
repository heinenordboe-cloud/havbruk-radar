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
from core import persondata
from core.contract import Observation, Source
from sources import _http

STANDARD_BASE = "https://api.fiskeridir.no/pub-aqua/api/v1"

# Brregs enhetsregister. Brukes KUN til å slå opp organisasjonsform for
# historiske organisasjonsnumre — se `brreg_form`. Ingen søk, ingen
# lister, ingen adresser.
BRREG_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"

# Pause mellom Brreg-kall. Samme begrunnelse som PAUSE_S: en offentlig
# etat, ikke en CDN.
BRREG_PAUSE_S = 0.3

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
# `Person` står her og ikke i `core/persondata.py`, fordi det er en
# pub-aqua-type uten Brreg-motstykke: en privatperson har ikke
# organisasjonsform. Resten av spørsmålet stilles til `persondata` via
# `FORM_KART` — se `er_person()`. Det er derfor DA, ANS og partrederi
# IKKE står her selv om de filtreres fra 16.09.2026: én liste, ett sted.
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
# OrganizationalSection) står BEVISST ikke her: vi har ikke Brregs ord
# for dem, og en gjettet kode ville vært en påstand på en tredjeparts
# vegne. De får `eier_type` ordrett i stedet.
#
# `JointlyOwnedShippingCompany` sto i den lista fram til 16.09.2026, og
# flyttet ned i kartet fordi den ble MÅLT den dagen: registerets eneste
# enhet av typen, `954744469`, slås opp hos Brreg til organisasjonsform
# `PRE` (Partrederi) i sektor 2300. Det er 1 av 1, ikke 367 av 367 som
# de fem over — men det er hele populasjonen, og det er et oppslag og
# ikke en slutning fra navnelikhet.
FORM_KART = {
    "LimitedLiabilityCompany": "AS",
    "PublicLimitedCompany": "ASA",
    "JointLiabilityCompany": "DA",
    "UnlimitedLiabilityCompany": "ANS",
    "CoopCompany": "SA",
    "JointlyOwnedShippingCompany": "PRE",
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
    """Sant hvis eiertypen betyr «denne eieren er et menneske».

    Tåler TO vokabularer, og det er nødvendig fra 03.09.2026:

      * pub-aquas egne ord  — `Person`, `SoleProprietorship`
      * Brregs koder        — `ENK`, `DA`, `ANS`, `PRE`, via
        core/persondata.PERSONFORMER

    Historiske mottakere som er oppløst finnes ikke i pub-aquas
    `/entities`, og typen deres hentes fra Brreg i stedet. Uten dette
    leddet ville en Brreg-`ENK` sluppet rett gjennom, fordi `ENK` ikke
    står i `PERSONTYPER` — og da hadde vi bygget nøyaktig det
    personregisteret filteret finnes for å hindre.

    ## Pub-aqua-typen OVERSETTES før spørsmålet stilles

    Fra 16.09.2026 filtreres DA, ANS og partrederi (sektor 2300). Den
    utvidelsen ligger i `persondata`, og den ville vært virkningsløs her
    uten oversettelsen: pub-aqua sier `JointLiabilityCompany`, ikke
    `DA`, så `er_personform("JointLiabilityCompany")` er usant uansett
    hva lista inneholder.

    Verre enn virkningsløs, faktisk. Snapshotet bærer den OVERSATTE
    koden — `organisasjonsform = DA` via `FORM_KART` — så vakten i
    `snapshot.write()` ville felt hele eierskaps-snapshotet mens filteret
    slapp de samme radene gjennom. Kilden og vakten må stille spørsmålet
    i samme vokabular.

    `persondata` er den autoritative lista for Brreg-siden. Den kopieres
    ikke hit: to lister som skal si det samme er formen F6/F7 hadde.
    `FORM_KART` er oversettelsen mellom vokabularene, ikke en andre liste
    over hvem som er en person.
    """
    if not isinstance(type_verdi, str):
        return False
    t = type_verdi.strip()
    return (t in PERSONTYPER
            or persondata.er_personform(t)
            or persondata.er_personform(FORM_KART.get(t, "")))


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


# ------------------------------------------------------------ historikk
#
# `/licenses/{nr}/transfers` gir EIERSKAPSKJEDEN for én tillatelse, og
# den rekker tilbake til 2006. Verifisert 02.09.2026.
#
# ## journalDate er den ENESTE datoen, og den er udokumentert
#
# Et overføringselement har nøyaktig fire felter, målt over 45
# overføringer i 60 tillatelser:
#
#     identityNr    organisasjonsnummer til MOTTAKER
#     journalDate   journalføringsdato
#     journalNr     saksnummer, «2022000164»
#     officialName  mottakerens navn
#
# Det finnes ingen `validFrom`, ingen overdragelsesdato og ingen
# avgiver. Fiskeridirektoratets Swagger-skall på /pub-aqua/ svarer 404
# på hver eneste spec-adresse vi har prøvd, og API-katalogen er en SPA
# som ikke leverer maskinlesbar dokumentasjon. **Ingen offentlig kilde
# forklarer hva journalDate betyr.**
#
# Krysspeiling mot vår egen changelog er PRØVD og virker ikke: de ni
# tillatelsene som flyttet mellom lokaliteter i vinduet 24.-31.08.2026
# har ingen overføring i det vinduet. Tilknytningsendring og eierskifte
# er to ULIKE hendelser, og changeloggen vår ser bare den første.
#
# Det som derimot lot seg måle er at serien er INTERNT konsistent, på
# 120 tillatelser:
#
#     journalDate kronologisk sortert            120/120
#     ingen overføring før grantedTime           120/120
#     siste overføring == dagens eier             61/62
#     uten overføringer: dagens eier == tildelt   57/58
#
# Kjeden er altså ekte og fullstendig nok til å bære en tidsserie, men
# datoen er journalføring og ikke nødvendigvis overdragelse. Derfor
# bæres forbeholdet PÅ HVER RAD (`dato_forbehold`), ikke bare i loggen —
# samme mønster som `aggregering = "baer_maaned"` i kildeledd.
DATO_FORBEHOLD = (
    "journalDate er JOURNALFØRINGSDATO, ikke bekreftet overdragelsesdato. "
    "Det er den eneste datoen endepunktet oppgir, og Fiskeridirektoratet "
    "dokumenterer ikke betydningen. Den faktiske overdragelsen kan ligge "
    "foran journalføringen. Serien er internt konsistent (kronologisk, "
    "etter tildeling, ender på dagens eier), men datoen skal leses som "
    "«senest da» og ikke som «akkurat da»."
)

# Kilden overføringene skrives under. EGEN serie, ikke `eierskap`, og
# det er ikke kosmetikk: den ukentlige eierskapskilden har helt andre
# felter og en helt annen kadens. Blandet man dem, ville feltvakten sett
# nitten felter forsvinne og seks nye dukke opp mellom to snapshots av
# «samme» kilde — nøyaktig F10s mønster.
HISTORIKK_KILDE = "eierskap_historikk"

# Sekunder mellom kall. Fiskeridirektoratet er en offentlig etat, ikke
# en CDN: 3036 kall skal ta en halvtime og ikke felle noen andres
# oppslag. Tallet er ikke målt mot en rate limit — vi har ikke sett
# noen — det er valgt for å være åpenbart høflig.
PAUSE_S = 0.5


class Eierskap(Source):
    name = "eierskap"

    # TO lisensgivere, og de krever hver sin setning. Tillatelsene kommer
    # fra Fiskeridirektoratets pub-aqua; organisasjonsformen for
    # historiske mottakere slås opp hos Brreg (`brreg_form`), og da er
    # Brregs data med i det som publiseres.
    #
    # Brreg oppgir ingen egen attribusjonsform, så setningen er NLOD 2.0
    # punkt 5 sin foreskrevne form med lisensgiver satt inn. Lest
    # 14.09.2026 — se docs/LISENSKJEDE.md merknad B.
    attribusjon = (
        "Kilde: Fiskeridirektoratet",
        "Inneholder data under Norsk lisens for offentlige data (NLOD) "
        "tilgjengeliggjort av Brønnøysundregistrene",
    )

    # Overføringene skrives under et EGET kildenavn, og det navnet må
    # kunne slås opp til denne attribusjonen. Se `HISTORIKK_KILDE` og
    # `Source.skriver_ogsaa`.
    skriver_ogsaa = (HISTORIKK_KILDE,)
    entity_type = "tillatelse"
    # Bumpet til "2" 03.09.2026: personvernfilteret leser nå Brregs
    # koder i tillegg til pub-aquas ord (`er_person`), og historiske
    # mottakere får organisasjonsformen slått opp hos Brreg. Uttrekket
    # gir dermed et ANNET resultat av samme kropp — 1934 overføringer
    # ble til 2611.
    #
    # Merk hva bumpen IKKE retter: snapshotene som alt ligger på disk er
    # skrevet av to ulike filtre og bærer BEGGE `source_version = "1"`.
    # De er ikke til å skille fra hverandre i dataene, bare på
    # `fetched_at`. Se docs/KILDE-EIERSKAP.md — det er en kjent defekt
    # som ikke kan rettes på plass, fordi filene er append-only.
    version = "2"

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

    # ---- eierskapshistorikk --------------------------------------------
    #
    # Egen inngang, ikke en del av den ukentlige `fetch()`. Backfillen
    # dispatcher på at `overforinger()` finnes — samme egenskapsbaserte
    # utvelgelse som `utgivelser()` og `hent_alt()`, og av samme grunn:
    # kilden vet hvilken form den har.

    def tillatelsesnumre(self, c: httpx.Client) -> list[str]:
        """Alle tillatelsesnumre, sortert. Én liste å iterere over."""
        return sorted({str(l["licenseNr"]) for l in self._alt(c, "/licenses")
                       if l.get("licenseNr")})

    def eiertyper(self, c: httpx.Client) -> dict[str, str]:
        """{organisasjonsnummer: typeValue} for IKKE-personer.

        Dette er oppslaget personvernfilteret trenger for overføringene.
        `transfers` oppgir bare `identityNr`, ikke entitets-ID-en, så
        kartet går på organisasjonsnummer.

        Personer er allerede borte når kartet er bygget: en mottaker som
        ikke finnes her har UKJENT type, og blir stoppet av `_tillat()`.
        Det er samme retning som i den ukentlige kilden — «vet ikke» kan
        ikke bety «slipp gjennom» i et personvernfilter.
        """
        ut: dict[str, str] = {}
        for e in self._alt(c, "/entities"):
            if er_person(e.get("typeValue")):
                continue
            nr = str(e.get("openNr") or "").strip()
            if er_organisasjonsnummer(nr):
                ut[nr] = str(e.get("typeValue") or "")
        return ut

    # Backfillen spør kilden, ikke modulen: den skal kunne kjøre mot en
    # hvilken som helst kilde med `overforinger()` uten å importere
    # nettopp denne fila.
    er_organisasjonsnummer = staticmethod(er_organisasjonsnummer)
    PAUSE_S = PAUSE_S
    BRREG_PAUSE_S = BRREG_PAUSE_S

    def brreg_form(self, orgnr: str, c: httpx.Client) -> dict:
        """Organisasjonsform fra Brreg for ETT organisasjonsnummer.

        Finnes for å rette en MÅLT skjevhet, ikke for å utvide utvalget.
        Historiske mottakere som er oppløst mangler i pub-aquas
        `/entities`, og uten typen deres stoppes overføringen — noe som
        rammet 677 av 694 filtrerte overføringer, fortrinnsvis de
        oppkjøpte selskapene. Se
        docs/beslutninger/2026-09-03-organisasjonsform-fra-brreg.md.

        ## Kroppen REDUSERES før den forlater funksjonen

        Verifisert 03.09.2026: en AKTIV enhet svarer med
        `forretningsadresse`, `postadresse`, `epostadresse`, `telefon` og
        `mobil`. For et enkeltpersonforetak er forretningsadressen i
        praksis hjemmeadressen, og mobilnummeret er personens eget —
        `985937028` svarer med gateadresse og mobil.

        Rå-arkivet ligger i git og er append-only. Derfor returneres bare
        tre felter, og NAVNET er ikke blant dem: `officialName` fra
        overføringen dekker behovet, og et navn fra Brreg ville vært en
        personopplysning for hver personform.

        ## Statusene, og at ingen av dem betyr «slipp gjennom»

            ok            kjent, ikke-personlig form  -> brukes
            personform    ENK e.l.                    -> stoppes
            ikke_funnet   404                         -> stoppes
            fjernet       410 Gone (juridisk fjernet) -> stoppes

        En SLETTET enhet svarer 200 med `respons_klasse: "SlettetEnhet"`
        og beholder `organisasjonsform` — det er hele grunnen til at
        veien er farbar. En FJERNET enhet svarer 410 og oppgir ingenting;
        den behandles som «vet ikke», altså stoppes, uendret regel.
        """
        r = c.get(f"{BRREG_URL}/{orgnr}",
                  headers={"Accept": "application/json"})
        if r.status_code == 410:
            return {"organisasjonsnummer": orgnr, "status": "fjernet"}
        if r.status_code == 404:
            return {"organisasjonsnummer": orgnr, "status": "ikke_funnet"}
        r.raise_for_status()
        d = r.json()
        kode = ((d.get("organisasjonsform") or {}).get("kode") or "").strip()
        if not kode:
            return {"organisasjonsnummer": orgnr, "status": "ikke_funnet"}
        if er_person(kode):
            # Arkiveres IKKE av kalleren. Se `_brreg_typer` i backfill.py:
            # «fraværende» og «person» gir begge STOPP, så et arkiv uten
            # personformene oppfører seg identisk — og inneholder da
            # ingen opplysning om at et gitt nummer tilhører et menneske.
            return {"organisasjonsnummer": orgnr, "status": "personform",
                    "organisasjonsform": kode}
        return {"organisasjonsnummer": orgnr,
                "organisasjonsform": kode,
                "slettedato": d.get("slettedato") or "",
                "status": "ok"}

    def overforinger(self, nr: str, c: httpx.Client) -> dict:
        """Rå transfers-respons for ÉN tillatelse.

        Returnerer kroppen slik tjenesten sendte den. Den arkiveres per
        tillatelse, og filnavnet er tillatelsesnummeret — det er også
        backfillens fremdriftslogg: finnes fila, er tillatelsen hentet.
        """
        base = get("kilder.eierskap.base_url", STANDARD_BASE).rstrip("/")
        return _http.get(c, f"{base}/licenses/{nr}/transfers",
                         hva=f"eierskap overføringer {nr}").json()

    def parse_overforinger(self, kropper: dict[str, dict],
                           typer: dict[str, str],
                           observed_at: str) -> Iterable[Observation]:
        """LAG 2 for historikken. Ett år av gangen.

        `kropper` er {tillatelsesnr: rå transfers-respons}, `typer` er
        kartet fra `eiertyper()`. Bare overføringer med journalDate i
        `observed_at`s år kommer ut — resten hører til et annet snapshot.

        Filteret er DET SAMME som den ukentlige kilden bruker
        (`_tillat`), ikke en kopi. En mottaker uten kjent selskapstype
        eller uten niifret nummer slippes ikke gjennom.
        """
        aar = observed_at[:4]
        for nr, kropp in sorted(kropper.items()):
            for i, t in enumerate((kropp or {}).get("transfers") or []):
                dato = str(t.get("journalDate") or "")
                if dato[:4] != aar:
                    continue
                orgnr = str(t.get("identityNr") or "").strip()
                if not _tillat(typer.get(orgnr), orgnr):
                    continue
                jnr = str(t.get("journalNr") or "").strip()
                if not jnr:
                    continue

                # Nøkkelen må være unik PER OVERFØRING, ikke per
                # tillatelse: SF-SU-0004 ble overført to ganger i 2006,
                # og med tillatelsesnummeret som entity_id ville den ene
                # raden stilltiende overskrevet den andre i
                # `snapshot.NOKKEL`.
                felles = dict(entity_id=f"{nr}|{jnr}",
                              entity_type="overforing",
                              entity_name=f"{nr} {dato}",
                              source=HISTORIKK_KILDE,
                              observed_at=observed_at)
                for felt, verdi in (
                        ("tillatelse_nr", nr),
                        ("mottaker_orgnr", orgnr),
                        ("mottaker_navn", t.get("officialName")),
                        ("mottaker_type", typer.get(orgnr)),
                        ("journal_dato", dato),
                        ("journal_nr", jnr),
                        ("rekkefolge", i + 1),
                        # Regel 1b-3: verdien som avgjør hva raden BETYR
                        # står PÅ raden. En parquet på en annen maskin om
                        # fire måneder skal bære sitt eget forbehold.
                        ("dato_forbehold", DATO_FORBEHOLD)):
                    if verdi is None or verdi == "":
                        continue
                    yield Observation(field=felt, value=str(verdi), **felles)

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
