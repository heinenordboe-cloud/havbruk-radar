"""Helsesjekk mellom kjøringer.

Det farligste feilmodus i dette systemet er ikke at noe krasjer.
Det er at én kilde slutter å levere, feilen isoleres pent, jobben
går grønt, og du oppdager i februar at du mangler ni uker med data.

Derfor: vi husker forrige kjøring, og så lenge en kilde som HAR
fungert er nede, avsluttes jobben med feilkode. Hver uke, ikke bare
den første. Da sender GitHub deg e-post helt til det er fikset.

Alternativet — å varsle kun ved overgangen fungerte->feiler — gir
nøyaktig feilmodusen beskrevet over, bare forskjøvet én uke: mister
du den ene e-posten, er alt grønt igjen mens datatapet fortsetter.

Nedetid er ikke den eneste stille feilen. Endrer kilden et feltnavn,
finner parse() det ikke, og returnerer 20 % av observasjonene den
pleier — ingen exception, r.ok forblir True, jobben er grønn. Derfor
måler volumvakten nedenfor antall observasjoner mot et REFERANSENIVÅ,
og bruker samme "nede"-mekanisme til å felle jobben ved et stort fall.

Referansenivået er det siste volumet som ble godkjent som friskt, og
det lagres her i health.json — ikke i forrige snapshot. Grunnen er
avsnittet over: sammenlignet vakten mot forrige snapshot, ville det
ødelagte tallet blitt neste ukes normal, alarmen ville fyrt én uke og
så tiet mens datatapet fortsatte. Referansen står stille til noen
bevisst godtar et nytt nivå (se godta_volum), så alarmen holder seg
rød hver uke til nivået er tilbake eller kvittert ut.

Av samme grunn er referansen IKKE et rullende snitt. Et snitt lar en
gradvis degradering flytte referansen nedover med seg — samme feil i
sakte film, bare vanskeligere å få øye på.

Bevisst asymmetrisk: en ØKNING varsler ikke her. Den sletter ingen
historikk (det er tapet av historikk denne fila finnes for å hindre),
og er allerede synlig andre steder — diff.compare() flagger hver ny
entitet, og endringer.height havner i commit-tittelen du leser på
telefonen. En stille dobling fins ikke; en stille halvering gjør.
Et friskt volum over referansen løfter referansen med seg, slik at
neste ukes fall måles mot det nye, høyere nivået.
"""

import json

from core import config
from core.paths import HEALTH_PATH  # noqa: F401
from core.runner import Result

# Aksepter opptil 10 % fall fra referansenivået før jobben felles.
# Ikke utledet fra reell uke-til-uke-varians — vi har bare fem
# kjøringer fra samme dag, og de sier 0 % (ventet: registrene beveger
# seg ikke i løpet av noen timer). Tallet er en start, ikke en måling
# — juster når ekte ukesvarians er observert.
STANDARD_MIN_ANDEL = 0.90


def _min_andel(kilde: str) -> float:
    """Terskel per kilde fra config.yml, med STANDARD_MIN_ANDEL som fallback.

    Ingen kilde har i dag en egen verdi — akvakultur (48k) og
    enhetsregisteret (27k) kan ha ulik naturlig varians, men det
    finnes ingen data ennå til å begrunne ulike tall. Overstyr i
    config.yml (kilder.<navn>.min_observasjoner_andel) den dagen det
    faktisk viser seg nødvendig.
    """
    return config.get(f"kilder.{kilde}.min_observasjoner_andel", STANDARD_MIN_ANDEL)


def _vurder_volum(kilde: str, antall: int, gammel: dict) -> tuple[int, int, str | None]:
    """Returnerer (ny referanse, ny lav-strekk, varsel eller None).

    Referansen står stille så lenge volumet er for lavt. Det er hele
    poenget: da måles neste uke mot det samme friske nivået, og
    alarmen fyrer på nytt i stedet for å godta det ødelagte tallet
    som normal.
    """
    referanse = gammel.get("volum_referanse")
    strekk = gammel.get("volum_lavt_paa_rad", 0)

    # Første kjøring for kilden: etabler nivået, ikke varsle. Det finnes
    # ikke noe å sammenligne mot, og et varsel her ville bare vært støy
    # i den ene situasjonen du uansett sitter og ser på skjermen.
    if not referanse:
        return antall, 0, None

    andel = antall / referanse
    if andel < _min_andel(kilde):
        strekk += 1
        return referanse, strekk, (
            f"{kilde} (volum {andel:.0%} av referanse {referanse}: "
            f"{antall} observasjoner, uke {strekk})"
        )

    # Friskt. Nivået følger med opp, slik at neste ukes fall måles mot
    # det som faktisk er normalen nå.
    return antall, 0, None


def godta_volum(kilde: str) -> tuple[bool, str]:
    """Godta kildens siste volum som det nye friske nivået.

    Kvitteringen for et REELT fall. Halveres en kilde fordi etaten
    faktisk avviklet halve registeret, er alarmen riktig første gang og
    støy alle uker etterpå. Løsningen er den samme som ellers i dette
    repoet: fiks kilden, eller ta et bevisst valg og skriv det ned —
    ikke skru av vakten.

    Skriver health.json og returnerer (ok, melding). Selve kvitteringen
    er commiten av health.json i datarepoet: git log viser når nivået
    ble godtatt, og commit-meldingen sier hvorfor.
    """
    tilstand = les()
    post = tilstand.get(kilde)
    if post is None:
        kjente = ", ".join(sorted(tilstand)) or "(ingen)"
        return False, f"Ukjent kilde '{kilde}'. Kjente kilder: {kjente}"

    nytt = post.get("antall_sist")
    if not nytt:
        return False, f"'{kilde}' har ikke noe registrert volum å godta ennå."

    gammelt = post.get("volum_referanse")
    post["volum_referanse"] = nytt
    post["volum_lavt_paa_rad"] = 0
    skriv(tilstand)

    return True, (
        f"{kilde}: volumreferanse {gammelt} -> {nytt}. "
        f"Commit health.json i datarepoet for å feste kvitteringen."
    )


def les() -> dict:
    if not HEALTH_PATH.exists():
        return {}
    return json.loads(HEALTH_PATH.read_text(encoding="utf-8"))


def oppdater(resultater: list[Result], observed_at: str) -> tuple[dict, list[str]]:
    """Returnerer ny helsetilstand og liste over kilder som trenger tilsyn.

    To uavhengige grunner havner i samme liste, med samme konsekvens
    (rød jobb): kilden er "nede" (har fungert minst én gang før, feiler
    nå), eller kilden leverte men med et volumfall over terskelen. En
    kilde som aldri har levert (nyskrevet, ikke ferdig) varsler ikke for
    noen av delene — den ser du på skjermen mens du jobber med den.
    """
    forrige = les()

    # Kilder som IKKE kjørte i dag (fordi de ikke var forfalt) skal beholde
    # tilstanden sin. Bygde vi dicten fra bare dagens resultater, forsvant
    # `sist_ok` for dem — og da ville alarmen "har fungert før, er nede nå"
    # aldri kunne utløses for en kilde som hoppes over en uke.
    ny: dict = dict(forrige)
    nede: list[str] = []

    for r in resultater:
        gammel = forrige.get(r.source, {})
        strekk = 0 if r.ok else gammel.get("feil_paa_rad", 0) + 1

        # En kilde som er nede leverte ingenting, og 0 observasjoner skal
        # ikke få lov til å ødelegge referansenivået. Da beholdes både
        # referansen og lav-strekken urørt til kilden er oppe igjen.
        if r.ok:
            referanse, volum_strekk, volum_varsel = _vurder_volum(
                r.source, r.count, gammel
            )
        else:
            referanse = gammel.get("volum_referanse")
            volum_strekk = gammel.get("volum_lavt_paa_rad", 0)
            volum_varsel = None

        ny[r.source] = {
            "sist_ok": observed_at if r.ok else gammel.get("sist_ok"),
            "sist_forsok": observed_at,
            "feil_paa_rad": strekk,
            "antall_sist": r.count,
            "siste_feil": "" if r.ok else r.error.strip().splitlines()[-1][:300],
            "volum_referanse": referanse,
            "volum_lavt_paa_rad": volum_strekk,
        }

        # Har fungert før, er nede nå -> dette skal vekke deg. Hver uke.
        if not r.ok and gammel.get("sist_ok"):
            nede.append(f"{r.source} (uke {strekk})")

        # Leverte, men mistenkelig lite av det -> samme alarm, annen årsak.
        # Fyrer hver uke så lenge nivået er brutt, ikke bare uka det skjedde.
        if volum_varsel:
            nede.append(volum_varsel)

    return ny, nede


def skriv(tilstand: dict) -> None:
    HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_PATH.write_text(
        json.dumps(tilstand, indent=2, ensure_ascii=False), encoding="utf-8"
    )
