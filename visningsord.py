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
import datetime as _dt
import re as _re

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


# --------------------------------------------------------------- DATOER
#
# Overleveringens harde krav 5, ordrett:
#
#     Datoer: i løpende tekst «16. september 2026». I tabeller brukes
#     ISO («2026-09-16»). Uker skrives «uke 38, 2026». ISO-uke
#     (`2026-W38`) står bare i filer, URL-er og `title`/hover.
#
# Det er tre skrivemåter av det samme tidspunktet, og de ligger her av
# samme grunn som «tonn»: to steder som staver september hver for seg er
# formen F6 og F7 hadde. ISO-formen står IKKE her — den er kildens verdi
# og skrives uendret, som alt annet i dataene.
#
# MÅNEDSNAVNENE ER EN LISTE, ikke `locale`. `locale.setlocale(LC_TIME,
# "nb_NO")` avhenger av hvilke lokaliteter som er installert på maskinen
# som bygger, og en byggejobb som gir «September» på én maskin og
# «september» på en annen er en side som endrer seg uten at noen rørte
# den. Tolv strenger er billigere enn den avhengigheten.
MAANEDER = ("januar", "februar", "mars", "april", "mai", "juni", "juli",
            "august", "september", "oktober", "november", "desember")


def _dagen(iso: object) -> tuple[str, _dt.date | None]:
    """(teksten uendret, datoen den er — eller None).

    KUTTER IKKE PÅ TEGN 10. Et førsteutkast gjorde `str(iso)[:10]`, og
    «ikke en dato» kom da ut som «ikke en da» — en verdi som ikke er en
    dato ble til en annen verdi som heller ikke er en dato, og som
    dessuten er feil. Regel 2 i denne modulen sier at det som ikke
    kjennes igjen skal komme UENDRET igjennom.

    Tidsstempel deles på «T» fordi det er ISO-8601s eget skille, ikke
    fordi datoen tilfeldigvis er ti tegn lang.
    """
    tekst = "" if iso is None else str(iso).strip()
    try:
        return tekst, _dt.date.fromisoformat(tekst.partition("T")[0])
    except ValueError:
        return tekst, None


def dato(iso: object) -> str:
    """«2026-09-16» -> «16. september 2026». For LØPENDE TEKST.

    Det som ikke er en ISO-dato kommer uendret ut. En tom streng blir
    tom: fravær er ikke 1. januar.
    """
    tekst, d = _dagen(iso)
    if d is None:
        return tekst
    return f"{d.day}. {MAANEDER[d.month - 1]} {d.year}"


def uke(iso: object) -> str:
    """«2026-09-16» -> «uke 38, 2026». ISO-uke og ISO-år.

    ISO-ÅRET, ikke kalenderåret: 2019-12-30 er mandag i uke 1 av 2020,
    og «uke 1, 2019» ved siden av «uke 52, 2019» er to uker som ligger
    ett år fra hverandre. Samme regel som `nettsted._isouke`.
    """
    tekst, d = _dagen(iso)
    if d is None:
        return tekst
    aar, ukenr, _ = d.isocalendar()
    return f"uke {ukenr}, {aar}"


def isouke(iso: object) -> str:
    """«2026-09-16» -> «2026-W38». Bare i filer, URL-er og `title`."""
    tekst, d = _dagen(iso)
    if d is None:
        return tekst
    aar, ukenr, _ = d.isocalendar()
    return f"{aar}-W{ukenr:02d}"


def ukespenn(iso: object) -> str:
    """Datoen -> «14.–20. september 2026», uka den ligger i.

    Spennet er mandag til søndag i ISO-uka, og måneds- og årsnavnet
    skrives bare én gang når begge endene ligger i samme måned. Går uka
    over et månedsskifte, står måneden på begge: «29. september–5.
    oktober 2026». Over et årsskifte står året også.
    """
    tekst, d = _dagen(iso)
    if d is None:
        return tekst
    mandag = d - _dt.timedelta(days=d.weekday())
    sondag = mandag + _dt.timedelta(days=6)
    if mandag.year != sondag.year:
        return (f"{mandag.day}. {MAANEDER[mandag.month - 1]} {mandag.year}"
                f"–{sondag.day}. {MAANEDER[sondag.month - 1]} {sondag.year}")
    if mandag.month != sondag.month:
        return (f"{mandag.day}. {MAANEDER[mandag.month - 1]}"
                f"–{sondag.day}. {MAANEDER[sondag.month - 1]} {sondag.year}")
    return (f"{mandag.day}.–{sondag.day}. "
            f"{MAANEDER[sondag.month - 1]} {sondag.year}")


def tidspunkt(stempel: object) -> str:
    """«2026-09-16T04:09:31+00:00» -> «16. september 2026 kl. 04.09».

    PUNKTUM OG IKKE KOLON mellom time og minutt: det er norsk
    rettskriving, og et kolon i en klokkeslettangivelse midt i en
    setning leses som et innrykk.

    SONEN FØLGER MED I STRENGEN og regnes ikke om. Tidsstempelet er vårt
    eget `fetched_at`, og det er skrevet i UTC — se core/contract.py. Å
    regne det om til norsk tid her ville vært en andre påstand om når vi
    hentet, ved siden av den ekte, og de to kan svare ulikt rundt
    midnatt. Se CLAUDE.md 1b.
    """
    tekst = "" if stempel is None else str(stempel).strip()
    if not tekst:
        return ""
    dagen, _, klokka = tekst.partition("T")
    vist = dato(dagen)
    if not vist or len(klokka) < 5 or not klokka[:5].replace(":", "").isdigit():
        return vist
    return f"{vist} kl. {klokka[:2]}.{klokka[3:5]} UTC"


# ----------------------------------------------------------- TITTELFORM
#
# Akvakulturregisteret skriver lokalitetsnavn i VERSALER: «OTERNESET»,
# «TUHOLMANE Ø», «LISTA FLY- OG NÆRINGSPARK». MÅLT 22.09.2026: 1 744 av
# 1 782 navn er heilt i versaler.
#
# Versaler i en 88-piksels overskrift er ikke en opplysning om navnet —
# det er en egenskap ved registerets inntastingsfelt. Overleveringen ber
# derfor om tittelform i H1, og om at ORIGINALEN står i
# registerfelt-tabellen. Begge deler, og det er poenget: den ene er
# lesbar, den andre er etterprøvbar.
#
# ## Regelen er SMAL, og det er med vilje
#
# 1. Er navnet ikke heilt i versaler, RØRES DET IKKE. Registeret har da
#    alt tatt et valg om store og små bokstaver, og vi skal ikke gjette
#    at det er feil. (38 navn.)
# 2. Et ord med siffer i står uendret. «17B» er ikke «17b».
# 3. Romertall, himmelretningsforkortelser og en MÅLT liste over
#    initialord står i versaler.
# 4. Småord står med liten forbokstav når de ikke er først.
# 5. Alt annet får stor forbokstav og små resten.
#
# ## Grensa, sagt rett ut
#
# Et initialord som ikke står i lista blir «Vgs» framfor «VGS». Lista er
# MÅLT mot dagens 1 782 navn og dekker dem — men den er en liste, og en
# ny lokalitet med et nytt initialord er ikke dekket.
#
# Alternativet var å GJETTE på at korte ord i versaler er initialord, og
# det ville tatt «VAL», «MO», «TAU», «AGA», «ØYE» og «FLØ» med seg. Alle
# seks er ekte stedsnavn i registeret, og «VAL» framfor «Val» er en
# feil ingen kan se er en feil. En liste som er for kort gir en synlig
# skrivefeil; et gjett som er for bredt gir en usynlig.
#
# Originalen står uansett i registerfelt-tabellen, og den er den
# siterbare.

# De 16 himmelretningene, norske forkortelser. Står i versaler.
HIMMELRETNING = frozenset({
    "N", "NNØ", "NØ", "ØNØ", "Ø", "ØSØ", "SØ", "SSØ",
    "S", "SSV", "SV", "VSV", "V", "VNV", "NV", "NNV",
    # ONO er den engelsk-pregede skrivemåten for ØNØ, og den står i
    # registeret. Den er MÅLT, ikke antatt.
    "ONO", "NO",
})

# Initialord MÅLT i dagens navn. Se grensa over.
INITIALORD = frozenset({"VGS", "NFH", "HIB", "IMS", "NCMM"})

# Småord med liten forbokstav når de ikke står først.
SMAAORD = frozenset({"og", "i", "på", "til", "ved", "for", "av", "med",
                     "under", "over", "mot", "fra"})

_ROMERTALL = _re.compile(r"[IVXLC]+")
_ORDDELER = _re.compile(r"([^\W\d_]+)", _re.UNICODE)


def tittelform(navn: object) -> str:
    """«OTERNESET» -> «Oterneset». Rører ikke et navn som ikke er versaler."""
    tekst = "" if navn is None else str(navn).strip()
    if not tekst or tekst != tekst.upper() or not any(c.isalpha() for c in tekst):
        return tekst

    biter = _ORDDELER.split(tekst)
    ut, er_forste = [], True
    for i, bit in enumerate(biter):
        if i % 2 == 0:          # skilletegn og siffer
            ut.append(bit)
            continue
        if bit in HIMMELRETNING or bit in INITIALORD or _ROMERTALL.fullmatch(bit):
            ut.append(bit)
        elif not er_forste and bit.lower() in SMAAORD:
            ut.append(bit.lower())
        else:
            ut.append(bit[:1] + bit[1:].lower())
        er_forste = False
    return "".join(ut)
