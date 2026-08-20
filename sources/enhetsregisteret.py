"""Enhetsregisteret (Brønnøysund).

Åpent API, ingen nøkkel, ingen registrering. Dette er kilden som skal
kjøre fra dag én — den er stabil og krever ingenting av deg.

Docs: https://data.brreg.no/enhetsregisteret/api/dokumentasjon
Lisens: NLOD, se README.

## Om feltvalget

API-et returnerer langt mer enn vi lagret opprinnelig. Alt som hentes én
gang i uka og kastes, er tapt for godt — derfor lagres alt som er
selskapsdata og har en tenkelig tolkning over tid.

Tre ting holdes bevisst utenfor:

- **Roller** (styre, daglig leder, innehaver). Eget endepunkt, ikke rørt.
  Navn og fødselsdato på privatpersoner gjør repoet til et personregister
  med behandlingsansvar etter GDPR.
- **Gateadresse** (`forretningsadresse.adresse`). For de 34 enkeltperson-
  foretakene i utvalget er dette i praksis innehaverens hjemmeadresse.
  Postnummer og poststed gir geografien uten å bygge et boligregister.
- **Telefon og målform.** Kontaktdata uten tolkningsverdi over tid.

## Om klassifisering

To feltnavn som ser like ut kan bety forskjellige ting, og forskjellen må
være synlig i dataene, ikke i hodet til den som leser dem:

`antall_ansatte` mangler for 620 av 954 selskaper. Det er ikke støy —
`harRegistrertAntallAnsatte` sier eksplisitt om tallet er rapportert.
Derfor lagres `ansatte_er_registrert` som eget felt. Uten det kan ikke
diffen skille "gikk fra 12 ansatte til null" fra "sluttet å rapportere",
og de to betyr helt forskjellige ting.

Samme prinsipp: `konkurs` og `under_tvangsavvikling` er ulike flagg med
ulik alvorlighet, og lagres hver for seg.
"""

import hashlib
from typing import Any, Callable, Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _http

BASE = "https://data.brreg.no/enhetsregisteret/api/enheter"

# Brreg avviser page*size over 10 000. Med sidestorrelse 100 er taket
# side 100. Vi ligger langt under i dag, men en bredere NACE-kode kan
# treffe det, og da skal du få vite det i stedet for en 400 midt i en
# kjøring.
MAKS_DYBDE = 10_000


def _nested(*nokler: str) -> Callable[[dict], Any]:
    """Henter nøstet verdi trygt: _nested("kapital", "belop")."""

    def hent(enhet: dict) -> Any:
        node: Any = enhet
        for nokkel in nokler:
            if not isinstance(node, dict):
                return None
            node = node.get(nokkel)
        return node

    return hent


def _liste(nokkel: str) -> Callable[[dict], Any]:
    """Slår sammen en liste av strenger. Tom liste blir None, ikke tom streng."""

    def hent(enhet: dict) -> Any:
        verdi = enhet.get(nokkel)
        if not isinstance(verdi, list) or not verdi:
            return None
        return "; ".join(str(v) for v in verdi)

    return hent


def _hash_av_liste(nokkel: str) -> Callable[[dict], Any]:
    """Kort hash av en tekstliste.

    Brukt på vedtektsfestet formål: teksten er lang nok til å mangedoble
    snapshotstørrelsen, men en ENDRING i formålet er et reelt signal om
    strategisk skifte. Hashen fanger at noe endret seg for 12 tegn i
    stedet for flere hundre. Vil du se hva som endret seg, slår du opp
    orgnr hos Brreg — endringen har en dato i loggen.
    """

    def hent(enhet: dict) -> Any:
        verdi = enhet.get(nokkel)
        if not isinstance(verdi, list) or not verdi:
            return None
        tekst = " ".join(str(v) for v in verdi)
        return hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:12]

    return hent


def _antall(nokkel: str) -> Callable[[dict], Any]:
    """Antall elementer i en liste. Endring i antall er hendelsen."""

    def hent(enhet: dict) -> Any:
        verdi = enhet.get(nokkel)
        return len(verdi) if isinstance(verdi, list) else None

    return hent


# Feltnavn er en kontrakt mot historikken. Døper du om et felt senere,
# ser diffen det som at det gamle forsvant og et nytt oppsto.
FELTER: dict[str, Callable[[dict], Any]] = {
    # --- identitet og form ---
    "navn": lambda e: e.get("navn"),
    "organisasjonsform": _nested("organisasjonsform", "kode"),
    "institusjonell_sektorkode": _nested("institusjonellSektorkode", "kode"),
    "historiske_navn_antall": _antall("historiskeNavn"),

    # --- næring ---
    "naeringskode": _nested("naeringskode1", "kode"),
    "naeringskode2": _nested("naeringskode2", "kode"),
    "naeringskode3": _nested("naeringskode3", "kode"),
    "aktivitet": _liste("aktivitet"),
    "vedtektsfestet_formaal_hash": _hash_av_liste("vedtektsfestetFormaal"),

    # --- geografi (uten gateadresse, se docstring) ---
    "kommune": _nested("forretningsadresse", "kommune"),
    "kommunenummer": _nested("forretningsadresse", "kommunenummer"),
    "postnummer": _nested("forretningsadresse", "postnummer"),
    "poststed": _nested("forretningsadresse", "poststed"),
    "landkode": _nested("forretningsadresse", "landkode"),

    # --- bemanning ---
    # Se docstring: flagget må lagres, ellers kan ikke "null ansatte"
    # skilles fra "ikke rapportert".
    "ansatte_er_registrert": lambda e: e.get("harRegistrertAntallAnsatte"),
    "antall_ansatte": lambda e: e.get("antallAnsatte"),

    # --- kapital: investeringsbeslutning med dato ---
    "aksjekapital": _nested("kapital", "belop"),
    "antall_aksjer": _nested("kapital", "antallAksjer"),
    "kapital_valuta": _nested("kapital", "valuta"),
    "kapital_innfort_dato": _nested("kapital", "innfortDato"),

    # --- konsern ---
    # Boolean, ikke hvilket konsern. Brreg oppgir ikke morselskap her.
    "er_i_konsern": lambda e: e.get("erIKonsern"),

    # --- status og risiko ---
    "konkurs": lambda e: e.get("konkurs"),
    "under_avvikling": lambda e: e.get("underAvvikling"),
    "under_tvangsavvikling": lambda e: e.get(
        "underTvangsavviklingEllerTvangsopplosning"
    ),
    "slettedato": lambda e: e.get("slettedato"),
    "paategninger_antall": _antall("paategninger"),

    # --- tidslinje: stiftet -> registrert -> mva-pliktig ---
    # Avstanden mellom disse er hvor lenge et selskap lå i skuffen før
    # det ble drift.
    "stiftelsesdato": lambda e: e.get("stiftelsesdato"),
    "registreringsdato": lambda e: e.get("registreringsdatoEnhetsregisteret"),
    "registrert_i_foretaksregisteret": lambda e: e.get(
        "registrertIForetaksregisteret"
    ),
    "registrert_i_mvaregisteret": lambda e: e.get("registrertIMvaregisteret"),
    "mva_registreringsdato": lambda e: e.get(
        "registreringsdatoMerverdiavgiftsregisteret"
    ),
    "vedtektsdato": lambda e: e.get("vedtektsdato"),

    # --- regnskapsinnlevering ---
    # Et selskap som slutter å levere er et distress-signal i seg selv,
    # uten at Regnskapsregisteret er koblet på.
    "siste_innsendte_aarsregnskap": lambda e: e.get("sisteInnsendteAarsregnskap"),
}


def _enheter(raw: list[dict]) -> Iterable[dict]:
    """Pakker ut enheter fra arkivet, uansett hvilket format det har.

    To formater finnes i arkivet, og begge må kunne re-parses — det er
    hele grunnen til at arkivet eksisterer:

    - NYTT (fra 17.08.2026): én post per SIDE, med konvolutten intakt og
      hvilken næringskode søket gjaldt. Se fetch().
    - GAMMELT: en flat liste av enheter, der konvolutten allerede var
      strippet før arkivering.

    Diskriminatoren er `svar`-nøkkelen. En enhet fra Brreg har aldri et
    felt som heter det.
    """
    for post in raw:
        if isinstance(post, dict) and "svar" in post:
            yield from post["svar"].get("_embedded", {}).get("enheter", [])
        else:
            yield post


def _varsle_tomme_sok(treff: dict[str, int], tillat_tomt: set[str]) -> list[str]:
    """Sier fra om næringskoder som ga null treff. Returnerer de uventede.

    Hvorfor dette trengs: en utgått NACE-kode gir 200 OK med tom liste,
    ikke en feil. `10.209` sto i config.yml i to dager og bidro med null
    enheter uten at noe sa fra. Volumvakten i health.py måler totalen per
    KILDE og ser ikke enkeltsøk — faller ett av syv søk til null mens de
    andre vokser litt, holder totalen seg innenfor terskelen.

    Hvorfor ikke exception: fetch() kaster ikke her med vilje. En feil
    kode ville da felt hele kilden, og ukas data for de seks andre kodene
    ville gått tapt for å straffe en skrivefeil. Regelen fra 16.08 om at
    én knekt ting koster én ting, ikke alt, gjelder også her.
    """
    tomme = sorted(k for k, n in treff.items() if n == 0 and k not in tillat_tomt)
    if not tomme:
        return []

    return [
        f"{kode}: næringskode uten treff — utgått, feilskrevet, eller "
        f"reelt tom. Verifiser mot SSB "
        f"(data.ssb.no/api/klass/v1/classifications/6) og fjern koden, "
        f"eller før den opp i kilder.enhetsregisteret.tillat_tomt"
        for kode in tomme
    ]


class Enhetsregisteret(Source):
    name = "enhetsregisteret"
    entity_type = "selskap"
    enabled = True

    def fetch(self, kjoredato: str) -> list[dict]:
        """Én post per SIDE, med pagineringskonvolutten intakt.

        Returnerer ikke en flat liste av enheter. Grunnen er arkivet:
        strippes konvolutten før arkivering, er `totalPages` og hvilket
        søk som fant hver enhet tapt for godt, og da kan verken en
        avkortet paginering eller et tomt søk oppdages i ettertid ved
        re-parse. Med sidene intakt er begge deler synlige i arkivet.

        parse() pakker ut igjen, og leser begge arkivformater.

        `kjoredato` brukes ikke: registeret har ingen etterslep. Argumentet
        står fordi kontrakten krever at en kilde FÅR tiden inn i stedet
        for å slå den opp — se Source.fetch.
        """
        koder = get("kilder.enhetsregisteret.naeringskoder", [])
        sidestorrelse = get("kilder.enhetsregisteret.sidestorrelse", 100)
        tillat_tomt = set(get("kilder.enhetsregisteret.tillat_tomt", []) or [])
        sider: list[dict] = []
        treff_per_kode: dict[str, int] = {}

        with httpx.Client(timeout=30, headers={"Accept": "application/json"}) as client:
            for kode in koder:
                antall = 0
                side = 0
                while True:
                    response = _http.get(client, BASE, params={
                        "naeringskode": kode,
                        "size": sidestorrelse,
                        "page": side,
                    }, hva=f"naeringskode {kode} side {side}")
                    payload = response.json()

                    # Hele svaret arkiveres, sammen med hvilket søk det kom fra.
                    sider.append({
                        "naeringskode": kode,
                        "side": side,
                        "svar": payload,
                    })

                    batch = payload.get("_embedded", {}).get("enheter", [])
                    antall += len(batch)

                    total_sider = payload.get("page", {}).get("totalPages", 1)
                    side += 1
                    if side >= total_sider or not batch:
                        break
                    if side * sidestorrelse >= MAKS_DYBDE:
                        print(f"    ADVARSEL: naeringskode {kode} har flere treff "
                              f"enn Brreg lar oss paginere gjennom "
                              f"({MAKS_DYBDE}). Del opp filteret.")
                        break

                treff_per_kode[kode] = antall

        # Sett, ikke append — se Source.advarsler.
        self.advarsler = _varsle_tomme_sok(treff_per_kode, tillat_tomt)
        return sider

    def parse(self, raw: list[dict], observed_at: str) -> Iterable[Observation]:
        for enhet in _enheter(raw):
            orgnr = enhet.get("organisasjonsnummer")
            navn = enhet.get("navn", "")
            if not orgnr:
                continue

            for felt, hent in FELTER.items():
                verdi = hent(enhet)
                if verdi is None:
                    continue
                yield Observation(
                    entity_id=str(orgnr),
                    entity_type=self.entity_type,
                    entity_name=str(navn),
                    field=felt,
                    value=str(verdi),
                    source=self.name,
                    observed_at=observed_at,
                )
