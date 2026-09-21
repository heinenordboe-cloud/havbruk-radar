"""Kildens koder og feltnavn på norsk. VISNINGSLAGET, og bare der.

`TN`, `SALMON`, `rod`, `farge__lesemaate` og `4680.0` er kildens eget
vokabular. Det er riktig i dataene og feil på en side: en oppdretter som
ser «4680.0 TN» ser at hun leser noe som er dumpet, ikke noe som er
skrevet, og slutter å stole på tallet ved siden av.

## Hvorfor en egen modul, og ikke `core/` eller `nettsted.py`

**Ikke `core/`.** Der ligger kontrakten mellom en kilde og lageret, og en
norsk etikett er ikke en del av den. Lå tabellen der, ville en kilde før
eller siden skrevet «tonn» inn i `Observation.value` framfor `TN` — og da
er oversettelsen i dataene, som er nøyaktig det som ikke skal skje.
Regel 1 i CLAUDE.md sier at `core/` ikke endres for en kilde; dette er
den samme grensa fra motsatt side.

**Ikke `nettsted.py`.** To grunner. Tabellen vokser med hvert kodede felt
en ny kilde tar med seg, og den trenger sin egen prøve. Og `vis.py`
skriver `oversikt.html` av de samme snapshotene: to steder som staver
«tonn» hver for seg er formen F6 og F7 hadde.

## Tre regler

1. **Dataene røres ikke.** `data/raw/`, changeloggen, lusetall-CSV-en og
   JSON-LD-en bærer kildens egne verdier. Denne modulen leses bare av en
   mal som skal leses av et menneske. `test_visningsord` holder CSV-en og
   JSON-LD-en utenfor, og det er den prøven som gjør tabellen trygg å
   utvide.

2. **En ukjent kode slipper igjennom UENDRET, og telles.** Faller en ny
   kode ut av tabellen, er det riktige å vise kildens verdi framfor å
   skjule den eller finne på en oversettelse. Men en stille fallthrough
   er hvordan «SALMON» står på siden igjen om et halvår uten at noen ser
   det, så `UKJENTE` teller hver gang det skjer og byggerapporten skriver
   tallet. Samme begrunnelse som at `filtrert_bort()` skrives hver
   kjøring: et tall man bare ser når det er galt, er et tall ingen
   kjenner normalverdien til.

3. **ORGANISASJONSNUMMER GRUPPERES ALDRI.** Publiseringsvaktens
   `NI_SIFFER` er `(?<![\\d.,])\\d{9}(?![\\d.,])` — ni siffer på rad.
   «928 957 489» er ikke ni siffer på rad, og en vakt som ikke kan
   tokenisere tallet kan ikke spørre om det er gjort rede for. Derfor er
   `MENGDEFELT` en OPT-IN-liste: et felt grupperes bare hvis det står
   der. Se `test_orgnummer_grupperes_aldri`.

## Oversettelsene er ORDRETTE, ikke tolkninger

`SALMON` blir «laks», ikke «laks og ørret». Fiskeridirektoratet
dokumenterer ikke hvilke arter kodene omfatter — hverken i
`docs/KILDE-AKVAKULTUR.md` eller i responsen vi arkiverer — og en side
som skrev «laks og ørret» ville lagt til en påstand kilden ikke har gjort.
Regel 4 i CLAUDE.md: skill mellom bekreftet og antatt.
"""

from __future__ import annotations

import collections

# Hver gang en kode faller ut av tabellen: {(felt, kode): antall}.
# Bokføring for byggerapporten, ikke tilstand som påvirker utputtet —
# `verdi()` svarer likt enten telleren er tom eller full.
UKJENTE: collections.Counter = collections.Counter()


# ---------------------------------------------------------------- koder
#
# Nøkkelen er kildens verdi ORDRETT, med kildens egen bruk av store og
# små bokstaver. `akvakultur` skriver enhetene i store bokstaver og
# vanntypen i blandede, og tabellen speiler det framfor å normalisere:
# normaliserer vi, må vi også normalisere ved oppslag, og da er det to
# steder å glemme det ene.

ENHET = {
    "TN": "tonn",
    "KG": "kilo",
    "STK": "stykk",
    "DA": "dekar",
    "M2": "kvadratmeter",
    "M3": "kubikkmeter",
    # MÅLT 20.09.2026: 2 rader i `eierskap`, én tillatelse — NT-LV-0302,
    # `KOMM-AKLIV` (akvakulturdyr i tidlige livsstadier), 5 500 L. Et
    # kulturvolum for levendefôr, og L er SI-symbolet. Koden sto ikke i
    # nyeste akvakultur-snapshot og ble funnet av `UKJENTE` ved første
    # bygg — som er hele grunnen til at telleren finnes.
    "L": "liter",
}

ART = {
    "SALMON": "laks",
    "OTHER_FISH": "annen fisk",
    "SHELL_FISH": "skalldyr",
    "ALGAE": "alger",
}

FARGE = {"rod": "rød", "gul": "gul", "gronn": "grønn"}

VANNTYPE = {
    "Salt": "saltvann",
    "Fresh": "ferskvann",
    "Brackish": "brakkvann",
    "Mixed": "blandet",
}

PLASSERING = {
    "Offshore": "i sjø",
    "Onshore": "på land",
    "Ocean": "åpent hav",
}

KLARERING = {"PERMANENT": "permanent", "TEMPORARY": "midlertidig"}

# Tre, ikke to. `kapitteloverskrift` står ikke i nyeste vedtak, men i
# changeloggen: 4 rader fra 2020-12-31, PO 4 og PO 5. Ordene er kildens
# egne og oversettes ikke — de er termer med en definisjon i
# `sources/trafikklysvedtak.py`, og en omskriving her ville vært en ny
# definisjon ved siden av den.
LESEMAATE = {
    "ordrett": "ordrett",
    "kapitteloverskrift": "kapitteloverskrift",
    "kapittelhjemmel": "kapittelhjemmel",
}

JANEI = {"True": "ja", "False": "nei", "true": "ja", "false": "nei"}

# Hvilket felt som slår opp i hvilken tabell. Et felt som ikke står her,
# vises ordrett — og det er standarden, ikke et uhell.
KODET: dict[str, dict[str, str]] = {
    "kapasitet_enhet": ENHET,
    "arter": ART,
    "farge": FARGE,
    "vanntype": VANNTYPE,
    "plasseringstype": PLASSERING,
    "klareringstype": KLARERING,
    "farge__lesemaate": LESEMAATE,
    "prodomraade_status": {k.upper(): v for k, v in FARGE.items()}
                          | {"RØD": "rød", "GUL": "gul", "GRØNN": "grønn"},
    "er_slakteri": JANEI,
    "har_samdrift": JANEI,
    "har_samlokalisering": JANEI,
    "har_kommersiell_aktivitet": JANEI,
    "konkurs": JANEI,
    "under_avvikling": JANEI,
    "under_tvangsavvikling": JANEI,
    "er_i_konsern": JANEI,
    "ansatte_er_registrert": JANEI,
    "registrert_i_foretaksregisteret": JANEI,
    "registrert_i_mvaregisteret": JANEI,
}

# `arter` kommer som en liste: «OTHER_FISH; SALMON». Hvert ledd slås opp
# for seg, og skilletegnet er kildens eget.
LISTEFELT = {"arter": "; "}

# Feltene der verdien er en MENGDE og skal ha tusenskille. OPT-IN, og det
# er regel 3 i modulens docstring: `kommunenummer` 5503 er ikke 5 503,
# `breddegrad` 68.9288 er ikke 68 928,8, og et organisasjonsnummer som
# grupperes gjør publiseringsvakten blind for seg selv.
MENGDEFELT = frozenset({
    "kapasitet", "kapasitet_midlertidig",
    "tillatelser_antall", "lokaliteter_antall", "artsbegrensninger_antall",
    "antall_ansatte", "antall_aksjer", "aksjekapital",
    "historiske_navn_antall", "paategninger_antall",
})

# U+00A0. Et vanlig mellomrom lar «4 680» brekke over to linjer midt i
# tallet; det gjør ikke dette.
TUSENSKILLE = " "


# ------------------------------------------------------------ feltnavn
#
# Etiketten som står i «Felt»-kolonnen og i registertabellen. Kildens
# feltnavn blir værende i `data-felt` — det er markupkontrakten, og det
# er den maskiner leser. Dette er det mennesker leser.

FELTNAVN = {
    # akvakultur
    "arter": "Arter",
    "artsbegrensninger_antall": "Artsbegrensninger",
    "breddegrad": "Breddegrad",
    "er_slakteri": "Slakteri",
    "forste_klarering": "Første klarering",
    "fylke": "Fylke",
    "fylkesnummer": "Fylkesnummer",
    "har_kommersiell_aktivitet": "Kommersiell aktivitet",
    "har_samdrift": "Samdrift",
    "har_samlokalisering": "Samlokalisering",
    "kapasitet": "Kapasitet",
    "kapasitet_enhet": "Kapasitetsenhet",
    "kapasitet_midlertidig": "Midlertidig kapasitet",
    "klareringstype": "Klareringstype",
    "kommune": "Kommune",
    "kommunenummer": "Kommunenummer",
    "lengdegrad": "Lengdegrad",
    "navn": "Navn",
    "plasseringstype": "Plassering",
    "prodomraade_kode": "Produksjonsområde",
    "prodomraade_navn": "Produksjonsområdets navn",
    "prodomraade_status": "Trafikklysfarge",
    "tillatelser": "Tillatelser",
    "tillatelser_antall": "Antall tillatelser",
    "tillatelser_trukket": "Trukne tillatelser",
    "vanntype": "Vanntype",
    "versjon_aarsak": "Versjonsårsak",
    "versjon_gyldig_fra": "Versjon gyldig fra",
    "versjon_status": "Versjonsstatus",
    # eierskap
    "eier_navn": "Eier",
    "eier_orgnr": "Eiers organisasjonsnummer",
    "eier_type": "Eiertype",
    "kapasitet_type": "Kapasitetstype",
    "lokaliteter": "Lokaliteter",
    "lokaliteter_antall": "Antall lokaliteter",
    "organisasjonsform": "Organisasjonsform",
    "portefoljetype": "Porteføljetype",
    "produksjonsstadium": "Produksjonsstadium",
    "tildelt_navn": "Tildelt til",
    "tildelt_orgnr": "Tildelt til, organisasjonsnummer",
    "tildelt_tid": "Tildelt",
    "tillatelse_formal": "Tillatelsens formål",
    "tillatelse_type": "Tillatelsestype",
    # eierskap_historikk
    "dato_forbehold": "Datoforbehold",
    "journal_dato": "Journalført",
    "journal_nr": "Journalnummer",
    "mottaker_navn": "Mottaker",
    "mottaker_orgnr": "Mottakers organisasjonsnummer",
    "mottaker_type": "Mottakertype",
    "rekkefolge": "Nr. i rekka",
    "tillatelse_nr": "Tillatelse",
    # trafikklysvedtak
    "farge": "Farge",
    "farge__lesemaate": "Lesemåte",
    # enhetsregisteret
    "aksjekapital": "Aksjekapital",
    "aktivitet": "Aktivitet",
    "ansatte_er_registrert": "Ansatte er registrert",
    "antall_aksjer": "Antall aksjer",
    "antall_ansatte": "Antall ansatte",
    "er_i_konsern": "I konsern",
    "historiske_navn_antall": "Historiske navn",
    "institusjonell_sektorkode": "Institusjonell sektorkode",
    "kapital_innfort_dato": "Kapital innført",
    "kapital_valuta": "Kapitalvaluta",
    "konkurs": "Konkurs",
    "landkode": "Landkode",
    "mva_registreringsdato": "Registrert i mva-registeret",
    "naeringskode": "Næringskode",
    "naeringskode2": "Næringskode 2",
    "naeringskode3": "Næringskode 3",
    "postnummer": "Postnummer",
    "poststed": "Poststed",
    "registreringsdato": "Registrert",
    "registrert_i_foretaksregisteret": "I Foretaksregisteret",
    "registrert_i_mvaregisteret": "I mva-registeret",
    "siste_innsendte_aarsregnskap": "Siste innsendte årsregnskap",
    "stiftelsesdato": "Stiftet",
    "vedtektsdato": "Vedtektsdato",
    "under_avvikling": "Under avvikling",
    "under_tvangsavvikling": "Under tvangsavvikling",
    "vedtektsfestet_formaal_hash": "Vedtektsfestet formål (hash)",
    # biomasselag og romming. Feltene når en leser gjennom
    # changeloggen selv om ingen av kildene har egen tabell ennå —
    # `UKJENTE` fant dem ved første bygg, med 384 og 66 treff.
    "siste_rapport": "Siste månedsrapport",
    "arter_tilstede": "Arter til stede",
    "antall_arter": "Antall arter til stede",
    "har_fisk": "Fisk til stede",
    "arts_forbehold": "Forbehold om artsfeltet",
    "lokalitet_status": "Lokalitetsstatus",
    # changeloggens egne kolonner
    "observed_at": "Gjelder dato",
    "fetched_at": "Hentet",
    "published_at": "Utgitt av kilden",
    "source": "Kilde",
}


# ------------------------------------------------------------- oppslag

def felt(navn: str) -> str:
    """Feltnavnet som etikett. Ukjent navn kommer ordrett igjennom.

    Ingen automatisk forskjønning (ingen `.replace("_", " ").title()`):
    den ville gjort `farge__lesemaate` til «Farge  Lesemaate» og
    `prodomraade_kode` til «Prodomraade Kode», altså gjettet, og gjettet
    feil, uten at noen kunne se at det var et gjett. Lista er skrevet av
    et menneske eller så står kildens navn der.
    """
    if navn in FELTNAVN:
        return FELTNAVN[navn]
    UKJENTE[("(feltnavn)", navn)] += 1
    return navn


def verdi(navn: str, raa: object) -> str:
    """Verdien på norsk. Ukjent kode kommer ordrett igjennom og telles."""
    tekst = "" if raa is None else str(raa).strip()
    if not tekst:
        return tekst

    if navn in LISTEFELT:
        # «OTHER_FISH; SALMON» er to koder, ikke én. Slås hele strengen
        # opp, faller den ut av tabellen og telles som ukjent — og
        # MÅLT 20.09.2026 er 11 av 15 `arter`-verdier sammensatte, så
        # det ville vært flertallet.
        skille = LISTEFELT[navn]
        ledd = [_kode(navn, d) for d in tekst.split(skille.strip()) if d.strip()]
        return skille.join(ledd)

    if navn in MENGDEFELT:
        return tall(tekst)

    return _kode(navn, tekst)


def _kode(navn: str, raa: str) -> str:
    raa = raa.strip()
    tabell = KODET.get(navn)
    if tabell is None:
        return raa
    if raa in tabell:
        return tabell[raa]
    UKJENTE[(navn, raa)] += 1
    return raa


def tall(raa: object) -> str:
    """«4680.0» -> «4 680». Det som ikke er et tall kommer uendret ut.

    Desimaler beholdes når de finnes: 0.5 tonn er et halvt tonn, og en
    avrunding her ville vært en endring av verdien på veien til leseren.
    MÅLT 20.09.2026: hver `kapasitet` i nyeste snapshot har `.0`, så i
    praksis er grenen tom i dag — men en kilde som en dag leverer 0.5
    skal ikke få den rundet bort i stillhet.
    """
    tekst = "" if raa is None else str(raa).strip()
    try:
        x = float(tekst)
    except ValueError:
        return tekst
    if x != x or x in (float("inf"), float("-inf")):
        return tekst
    heltall, _, desimal = f"{x:,.10f}".rstrip("0").rstrip(".").partition(".")
    heltall = heltall.replace(",", TUSENSKILLE)
    return f"{heltall},{desimal}" if desimal else heltall


def maalt(mengde: object, enhet: object) -> str:
    """«4680.0», «TN» -> «4 680 tonn». Enheten står ALLTID ved tallet.

    Den varierer mellom tonn, stykk, dekar, kvadratmeter, kubikkmeter og
    kilo i det samme snapshotet, og et tall uten enhet er ubrukelig —
    det sto i captionen fra før, og her er det håndhevet.
    """
    m = tall(mengde)
    e = verdi("kapasitet_enhet", enhet)
    if not m:
        return ""
    return f"{m} {e}" if e else m


def ukjente_rapport() -> list[str]:
    """Én linje per kode som falt ut av tabellen, mest brukte først."""
    return [f"{felt_}: «{kode}» x{antall}"
            for (felt_, kode), antall in UKJENTE.most_common()]
