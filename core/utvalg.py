"""Hva kilden BA OM — lagret sammen med det den fikk.

En kilde henter sjelden alt som finnes. Enhetsregisteret spør på en
liste næringskoder; endrer den lista seg, endrer utvalget seg, og da
dukker det opp entiteter som ikke er nye i verden — bare nye for oss.

Fram til 24.08.2026 sto den lista bare i `config.yml` og i
git-historikken. Konsekvensen er målt: kjøringen 24.08 ga 26673
endringer, og 25804 av dem (96,7 %) var 908 selskaper som kom inn fordi
fire næringskoder ble lagt til kvelden 17.08 — etter at den dagens
snapshot var hentet. Ingen av de 908 var registrert siden forrige
snapshot; den nyeste var registrert 04.08, den eldste i 1995.

Det avgjørende er ikke at tallet var stort. Det er at et snapshot ikke
kunne SVARE på spørsmålet. Ligger utvalget i config, forteller
snapshotet hva vi fant, men ikke hva vi lette etter — og da kan ingen
sammenligning av to snapshots skille «ny i bransjen» fra «ny i vårt
utvalg» uten å lese git ved siden av.

Dette er samme klasse feil som regel 1b i CLAUDE.md: en tilstand som
avgjør hva dataene BETYR, som ikke ligger i dataene. Der var det
tidspunktet, her er det utvalget.

Sidestykket finnes allerede og virker: diff.compare() undertrykker rader
når et FELTNAVN er nytt, fordi en skjemautvidelse ikke er en hendelse.
Den regelen sparte 18687 støyrader 17.08. Utvalgsutvidelse er samme
klasse hendelse med samme klasse støy, og skal behandles likt.

## Formatet

`{"naeringskoder": ["03.211", "03.212", ...]}` — nøkkel til liste.

Hver verdi leses som et SETT av kriterier. Det er den eneste antakelsen
kjernen gjør, og den er nødvendig for å kunne svare på «ble dette
bredere» uten å vite hva en næringskode er. Kilden bestemmer nøklene;
`core/` bestemmer ingenting om innholdet.

Skalarer hører ikke hjemme her. `sidestorrelse: 100` avgjør ikke HVILKE
entiteter vi får, bare hvor mange kall det tar å hente dem — og et felt
som ikke endrer utvalget skal ikke kunne utløse en utvalgsutvidelse.
`normaliser()` avviser derfor alt som ikke er en liste.

## TRE tilstander, ikke to

Fram til 25.08.2026 fantes bare to: «her er utvalget» og tomt. Tomt
måtte da bety både «vi vet ikke hva vi ba om» og «vi ba om alt», og de
er ikke det samme.

For `lusetall` var sammenblandingen direkte gal.
`/locality/{år}/{uke}` tar ingen utvalgsparametre og returnerer alle
lokaliteter. Det er ikke fravær av kunnskap, det er kunnskap om fravær
av filtrering — og et snapshot som sier «vet ikke» om noe vi vet, sier
noe usant om seg selv.

Det er samme skille som `lus_er_rapportert`: en lokalitet uten
rapportering og en med null lus er ikke det samme, og prosjektet hadde
allerede det riktig der og galt her.

    kilde.utvalg      på disk     les()      betyr
    ---------------------------------------------------------------
    {"n": [...]}      {"n":[…]}   {"n":[…]}  kjent utvalg
    {}                "{}"        {}         kjent: ingen filtrering
    None              ""          None       ukjent

`Source.utvalg` er derfor `None` som standard og ikke `{}`. Sto den som
`{}`, ville enhver kilde som ALDRI har tenkt på spørsmålet automatisk
påstått at den henter alt — en påstand ingen har gått god for. En
kilde må si det selv for at det skal stå i dataene.

De to falske vennene er `{}` og `None`, som begge er usanne i Python.
`if not utvalg:` behandler dem likt og er nesten alltid feil her. Spør
med `er_ukjent()` og `henter_alt()` i stedet — de finnes for at den
forskjellen skal være tungvint å overse.
"""

from __future__ import annotations

import json


def normaliser(utvalg: dict | None) -> dict[str, list[str]]:
    """Kilden si dict til kanonisk form: sorterte, unike strenglister.

    Kanonisk betyr at to like utvalg alltid serialiserer likt. Uten det
    ville rekkefølgen på `naeringskoder` i config.yml gitt en ny
    kolonneverdi — og dermed en ny parquet-fil i git — uten at noe
    faktisk var endret. Samme grunn som `maintain_order` i
    snapshot.to_frame().
    """
    if not utvalg:
        return {}

    ut: dict[str, list[str]] = {}
    for nokkel, verdi in utvalg.items():
        if isinstance(verdi, (str, bytes)) or not isinstance(verdi, (list, tuple, set)):
            raise ValueError(
                f"utvalg[{nokkel!r}] er {type(verdi).__name__}, ikke en liste. "
                f"Utvalget beskriver HVILKE entiteter vi ba om, og hvert "
                f"kriterium må være et sett med verdier. En skalar som "
                f"sidestørrelse hører ikke hjemme her — den endrer ikke "
                f"utvalget."
            )
        ut[str(nokkel)] = sorted({str(v) for v in verdi})
    return ut


def er_ukjent(utvalg: dict | None) -> bool:
    """Sa kilden ingenting om hva den ba om?

    Finnes som funksjon og ikke som `if not utvalg:` fordi `{}` og `None`
    begge er usanne, og de betyr motsatte ting: `{}` er en PÅSTAND om at
    ingenting ble filtrert bort, `None` er fraværet av en påstand.
    """
    return utvalg is None


def henter_alt(utvalg: dict | None) -> bool:
    """Sa kilden uttrykkelig at den ikke filtrerer?

    Sant bare for `{}`. `None` er ukjent og gir usant — vi vet ikke at
    den henter alt, vi vet ikke noe.
    """
    return utvalg is not None and len(utvalg) == 0


def serialiser(utvalg: dict | None) -> str:
    """Kanonisk JSON. `"{}"` for «ingen filtrering», `""` for ukjent.

    De to er forskjellige med vilje, og forskjellen ligger i STRENGEN
    fordi det er strengen som havner på raden og overlever til neste år.
    Kollapset de to — som de gjorde fram til 25.08.2026 — kunne et
    snapshot aldri si at det hentet alt, bare at det ikke sa noe.
    """
    if utvalg is None:
        return ""
    n = normaliser(utvalg)
    if not n:
        return "{}"
    return json.dumps(n, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def les(tekst: str | None) -> dict[str, list[str]] | None:
    """Tilbake til dict. None = ukjent, `{}` = kjent ingen filtrering.

    Tom streng er ukjent, `"{}"` er «kilden hentet alt». Snapshots skrevet
    før 25.08.2026 har tom streng uansett hva kilden faktisk gjorde, og
    skal leses som ukjent — vi visste ikke da vi skrev dem. Se
    docs/beslutninger/2026-08-25-utvalg-skiller-ukjent-fra-ingen-filtrering.md.

    Ulesbar tekst gir None og ikke en exception. Grunnen er den samme som
    i `health.dager_siden_ok()`: dette er inndata fra en fil på disk som
    kan være skrevet av en eldre versjon, og en leser som kaster på en
    gammel fil gjør historikken uleselig i stedet for uskarp.
    """
    if not tekst:
        return None
    try:
        d = json.loads(tekst)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict):
        return None
    try:
        return normaliser(d)
    except ValueError:
        return None


def er_utvidet(fra: dict | None, til: dict | None) -> bool:
    """Ble utvalget BREDERE fra `fra` til `til`?

    Sann bare når vi VET det. Mangler ett av utvalgene, er svaret usant —
    ikke fordi ingenting ble utvidet, men fordi ingen kan påstå at det
    ble det. Fallbacken går motsatt vei av `dager_siden_ok()`, og med
    vilje: der er «vet ikke» -> kjør, fordi tapt historikk ikke kan
    rettes. Her er «vet ikke» -> ikke undertrykk, fordi en undertrykt
    rad er en hendelse ingen får se. Begge faller mot den siden der
    feilen er synlig.

    Utvidet = hvert kriterium i `fra` finnes fortsatt i `til`, og minst
    ett sted er `til` strengt større. En NY nøkkel teller som utvidelse:
    et kriterium som ikke fantes er et vi ikke søkte på.

    Blandet inn og ut i samme uke — 10.209 ut, 03.222 og 10.203 inn,
    slik det faktisk skjedde 17.08 — er IKKE en ren utvidelse etter
    denne definisjonen, og svaret blir usant. Det er strengt med vilje:
    når utvalget både vokser og krymper, kan en ny entitet skyldes
    begge deler, og da skal radene stå som endringer og bli SETT.
    Vil du undertrykke en slik uke, er det `godta`-veien som gjelder —
    en skrevet kvittering, ikke en heuristikk. Se docs/beslutninger/
    2026-08-24-utvalgsutvidelse-er-ikke-endring.md.
    """
    if fra is None or til is None:
        return False

    # «Ingen filtrering» er ytterpunktene, og de må håndteres før den
    # generelle regelen — den er skrevet for to kriteriesett og leser
    # et tomt sett som «ingen kriterier», ikke som «alle entiteter».
    if henter_alt(fra):
        # Bredere enn alt finnes ikke. Uten denne ville en overgang fra
        # alt til et filter blitt lest som utvidelse (ny nøkkel i `til`),
        # og radene som forsvant blitt merket som noe som kom til.
        return False
    if henter_alt(til):
        # Fra et filter til alt ER den størst mulige utvidelsen. Den
        # generelle regelen ville sagt usant her, fordi kriteriene i
        # `fra` ikke finnes igjen i et tomt `til` — de er ikke fjernet,
        # de er blitt overflødige.
        return True

    strengt_storre = set(til) - set(fra) != set()
    for nokkel, gamle in fra.items():
        nye = set(til.get(nokkel, []))
        if not set(gamle) <= nye:
            return False        # noe forsvant: ikke en ren utvidelse
        if nye > set(gamle):
            strengt_storre = True
    return strengt_storre


def beskriv(fra: dict | None, til: dict | None) -> str:
    """Én linje om hva som kom til. For logg og commit-melding."""
    if fra is None or til is None:
        return "utvalg ukjent"
    if henter_alt(fra) and henter_alt(til):
        return "ingen filtrering"
    if henter_alt(fra):
        return "fra ingen filtrering til " + ", ".join(sorted(til))
    if henter_alt(til):
        return "fra " + ", ".join(sorted(fra)) + " til ingen filtrering"
    biter = []
    for nokkel in sorted(set(fra) | set(til)):
        lagt_til = sorted(set(til.get(nokkel, [])) - set(fra.get(nokkel, [])))
        fjernet = sorted(set(fra.get(nokkel, [])) - set(til.get(nokkel, [])))
        if lagt_til:
            biter.append(f"+{nokkel}: {', '.join(lagt_til)}")
        if fjernet:
            biter.append(f"-{nokkel}: {', '.join(fjernet)}")
    return "; ".join(biter) or "uendret"
