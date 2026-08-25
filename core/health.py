"""Helsesjekk mellom kjøringer.

Det farligste feilmodus i dette systemet er ikke at noe krasjer.
Det er at én kilde slutter å levere, feilen isoleres pent, jobben
går grønt, og du oppdager i februar at du mangler ni uker med data.

Derfor: vi husker forrige kjøring, og så lenge en aktiv kilde feiler,
avsluttes jobben med feilkode. Hver uke, ikke bare den første. Da
sender GitHub deg e-post helt til det er fikset.

Det gjelder også en kilde som aldri har lykkes. Regelen het tidligere
"har fungert før, feiler nå", med den begrunnelsen at en nyskrevet
kilde er en du sitter og ser på. Den antakelsen falt i det øyeblikket
kilder kunne legges til uten at noen satt ved tastaturet når cron
fyrte: en kilde som aldri kom i drift feilet da i det uendelige med
exit 0. Meldingen skiller mellom de to, konsekvensen gjør ikke.

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

Referansen er derfor et HØYVANNSMERKE: et friskt volum over referansen
løfter den med seg, men et volum under den senker den aldri — heller
ikke når det er innenfor terskelen. Senket den seg, ville et fall på
8 % i uka passert hver gang, og kilden kunne drive til 43 % av
opprinnelig volum uten ett varsel. Eneste vei ned er godta_volum().

Tredje stille feil, og den dyreste så langt: feltvakten under teller
RADER per felt. Den fanger at et felt slutter å komme. Den fanger ikke
at feltet fortsetter å komme og slutter å si noe. `har_rensefisk`
leverte 1777 rader hver uke fra 2023-04-24 og var `False` i hver eneste
én — 171 uker, uten et pip. `har_medikamentell_behandling`: 89 uker.

Derfor _vurder_innhold() ved siden av _vurder_felter(). Den måler hvor
mange rader som IKKE har feltets vanligste verdi, mot en normal bygget
av hele historikken og lagret append-only utenfor denne fila. Se
core/feltnormal.py — også for hvorfor normalen IKKE kan bo her: en
referanse som skrives om hver kjøring var nettopp det som festet
dødsleiet til har_rensefisk som normaltilstand.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from core import config
from core import feltnormal
from core.paths import HEALTH_PATH  # noqa: F401

if TYPE_CHECKING:                       # pragma: no cover
    # Kun for typene. Importeres den på ekte, blir det importsyklus:
    # runner må lese health.json for å vite når en kilde sist lyktes
    # (se dager_siden_ok), og health importerte runner for ett
    # annoteringsnavn. `from __future__ import annotations` gjør
    # annoteringene til strenger, så navnet trengs aldri ved kjøring.
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

    # Friskt. Referansen er et HØYVANNSMERKE: den følger med opp, men
    # aldri ned. `max` er hele forskjellen på en vakt og et rullende
    # snitt.
    #
    # Uten max blir siste friske verdi den nye referansen, også når den
    # er lavere. Da måles neste uke mot et allerede senket nivå, og en
    # kilde som mister 8 % i uka passerer terskelen hver eneste gang:
    # målt over ti uker havnet den på 43 % av opprinnelig volum uten ett
    # varsel. Det er nøyaktig degraderingen i sakte film som docstringen
    # over sier vakten ikke skal tillate.
    #
    # Skal referansen ned, er det --godta-volum som gjør det. Det er
    # også den eneste veien ned, og det er meningen.
    return max(antall, referanse), 0, None


def _vurder_felter(
    kilde: str, felt_naa: dict[str, int], gammel: dict
) -> tuple[dict, str | None]:
    """Returnerer (ny feltreferanse, varsel eller None).

    Volumvakten måler totalen per kilde, og det er for grovt til å se et
    enkelt felt forsvinne. Målt på akvakultur 17.08.2026: 29 felter,
    største enkeltfelt 1779 av 48236 rader = 3,7 %. Terskelen er 10 %, så
    INGEN enkeltfelt kan utløse volumvakten — et felt kan slutte å komme
    hver uke i det uendelige mens jobben er grønn. Det er SCHEMA-buggen i
    mindre skala, og SCHEMA-buggen er grunnen til at vakten finnes.

    Bevisst smal: varsler kun når et felt som FANTES i referansen har null
    rader nå. Ingen prosentterskel per felt — det finnes ingen ukesvarians
    å kalibrere mot ennå, og felt varierer legitimt (prodomraade_* finnes
    for 970 av 1779 lokaliteter).

    Referansen er et høyvannsmerke, som volumreferansen: den stiger med
    nye og voksende felter, men et felt som forsvinner beholder tallet
    sitt. Derfor fyrer varselet på nytt hver uke til feltet er tilbake
    eller kvittert med godta_felt().
    """
    referanse = dict(gammel.get("felt_referanse") or {})

    # Ingen observasjoner denne kjøringen: ikke rør referansen. Kilden er
    # enten nede eller tom, og begge deler er volumvaktens bord. Uten
    # dette ville hvert eneste felt blitt meldt borte samtidig.
    if not felt_naa:
        return referanse, None

    borte = sorted(
        felt for felt, antall in referanse.items()
        if antall > 0 and felt_naa.get(felt, 0) == 0
    )

    for felt, antall in felt_naa.items():
        referanse[felt] = max(antall, referanse.get(felt, 0))

    if borte:
        return referanse, (
            f"{kilde} (felt borte: {', '.join(borte)} — fantes forrige "
            f"kjøring, null rader nå)"
        )
    return referanse, None


def _vurder_innhold(
    kilde: str, innhold_naa: dict[str, dict], gammel: dict, normal: dict
) -> tuple[dict, list[str]]:
    """Returnerer (nye nullstrekk, varsler). Ser INNHOLD, ikke levering.

    `_vurder_felter` over spør «kom feltet». Denne spør «sa det noe».
    De to er ikke samme spørsmål, og forskjellen kostet 171 uker:
    `har_rensefisk` leverte 1777 rader hver uke fra 2023-04-24 og var
    `False` i hver eneste én. Radetellingen så en full kolonne.

    Målet er `minoritet` — rader som ikke har feltets vanligste verdi.
    Se core/feltnormal.py for hvorfor det og ikke «antall True».

    To uavhengige prøver, og de fanger ulike ting:

    * **Under gulvet.** Feltet bærer mindre innhold enn det noen gang
      har gjort i historikken normalen ble bygget av. Fyrer straks.
    * **Nullstrekk.** Feltet har vært helt tomt i flere kjøringer på rad
      enn terskelen. Nødvendig fordi null er en HELT normal uke for et
      lite felt — `har_ila` har 22 nulluker i historikken, `har_pd` 33.
      Det er strekket, ikke uka, som skiller en stille uke fra et dødt
      felt.

      Grensa er flat og bruker IKKE feltets eget `normalt_nullstrekk`
      som unntak, selv om tallet lagres. Grunnen er målt: hvert eneste
      nullstrekk over 13 uker i 761 uker historikk er enten en oppstart
      (har_pd 33 uker i 2012, har_ila 22 uker i 2012–13) eller et
      dødsfall. Ingen av dem er «normalt». Verre: `har_medikamentell_
      behandling` har et 45-ukers strekk i historikken som ER dødsfallet,
      og et unntak utledet av det ville gjort vakten blind for nettopp
      den feilen den finnes for. Tallet står i normalen som kontekst til
      den som leser alarmen, ikke som fribillett.

    Uten en etablert normal gjøres ingenting. En alarm på et grunnlag vi
    ikke har er støy, og støy er det som får folk til å slutte å lese
    alarmer. `--bygg-feltnormal` etablerer grunnlaget.
    """
    strekk = dict(gammel.get("innhold_nullstrekk") or {})
    if not innhold_naa:
        return strekk, []            # kilden er nede: volumvaktens bord

    felter = (normal.get("kilder") or {}).get(kilde) or {}
    grense = config.get(f"kilder.{kilde}.maks_nullstrekk",
                        normal.get("maks_nullstrekk",
                                   feltnormal.STANDARD_MAKS_NULLSTREKK))

    varsler = []
    for felt, tall in sorted(innhold_naa.items()):
        n = felter.get(felt)
        minoritet = tall.get("minoritet", 0)

        # Strekket telles for ALLE felter, også de normalen ikke kjenner.
        # Da er tallet klart den dagen normalen bygges, i stedet for å
        # starte på null da.
        #
        # Første gang et felt telles, arves strekket fra normalens
        # `dodt_naa`. Uten det ville et felt som har vært tomt i 171 uker
        # begynt på null når vakten ble tatt i bruk, og trengt 13 nye uker
        # på å si fra om noe som har vart i tre år.
        forrige_strekk = strekk.get(felt, n.get("dodt_naa", 0) if n else 0)
        strekk[felt] = forrige_strekk + 1 if minoritet == 0 else 0

        if n is None:
            continue                 # ingen normal for dette feltet ennå

        if minoritet < n.get("gulv", 0):
            varsler.append(
                f"{kilde}.{felt} (innhold {minoritet} under gulvet "
                f"{n['gulv']} — laveste på {n.get('uker', '?')} uker; "
                f"{tall['rader']} rader leveres fortsatt)")
        elif strekk[felt] >= grense:
            varsler.append(
                f"{kilde}.{felt} (tomt {strekk[felt]} kjøringer på rad, "
                f"grense {grense}; {tall['rader']} rader leveres fortsatt, "
                f"alle «{tall['toppverdi']}»)")

    return strekk, varsler


def godta_felt(kilde: str) -> tuple[bool, str]:
    """Godta kildens nåværende feltsett som det nye normale.

    Egen kvittering, uavhengig av godta_volum(). De to besvarer ulike
    spørsmål: «totalen er legitimt lavere» er ikke «dette feltet finnes
    legitimt ikke lenger». Slår man dem sammen, blir den ene en stille
    aksept av den andre — og et felt som forsvant i samme uke som et
    legitimt volumfall ville blitt svelget med i kjøpet.
    """
    tilstand = les()
    post = tilstand.get(kilde)
    if post is None:
        kjente = ", ".join(sorted(tilstand)) or "(ingen)"
        return False, f"Ukjent kilde '{kilde}'. Kjente kilder: {kjente}"

    sist = post.get("felt_sist")
    if not sist:
        return False, f"'{kilde}' har ikke noe registrert feltsett å godta ennå."

    fjernet = sorted(set(post.get("felt_referanse") or {}) - set(sist))
    post["felt_referanse"] = dict(sist)

    # Innholdsalarmen kvitteres ut sammen med feltalarmen. De to er
    # samme sak sett fra to sider — «feltet er borte» og «feltet er tomt»
    # — og en kvittering som bare tok den ene ville latt jobben stå rød
    # på den andre uten at noe mer kunne gjøres herfra.
    #
    # Strekket nullstilles. GULVET i feltnormalen røres IKKE: det ligger
    # append-only i data/feltnormal/ og skal bygges på nytt bevisst, med
    # en begrunnelse som blir stående. Se core/feltnormal.py.
    tomme = sorted(f for f, v in (post.get("innhold_nullstrekk") or {}).items() if v)
    post["innhold_nullstrekk"] = {}
    skriv(tilstand)

    biter = []
    if fjernet:
        biter.append(f"godtok at {', '.join(fjernet)} er borte")
    if tomme:
        biter.append(f"nullstilte innholdsstrekket for {', '.join(tomme)}")
    if not biter:
        return True, f"{kilde}: feltreferansen er allerede lik dagens feltsett."
    return True, (
        f"{kilde}: {'; '.join(biter)}. "
        f"Commit health.json i datarepoet for å feste kvitteringen."
    )


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


def dager_siden_ok(kilde: str, i_dag: str,
                   tilstand: dict | None = None) -> int | None:
    """Dager siden kilden sist ble hentet MED HELL. None = vet ikke.

    Dette er spørsmålet frekvensvakten faktisk stiller. Den spurte før
    snapshot.dager_siden_observasjon(), som svarer på noe annet: hvor
    gammel den nyeste observasjonen er. For en kilde uten etterslep er
    de like. For lusetall med uker_etterslep=4 er de det aldri — nyeste
    fil er ALLTID datert fire uker tilbake, også når kilden kjører
    perfekt, så vakten leste permanent 28 dager (F4).

    Deretter spurte den `sist_forsok`, og det var F8: et FORSØK er ikke
    et RESULTAT. Lusetall feilet tre ganger 24.08 med invalid_client —
    `sist_ok=null`, `feil_paa_rad=3` — og vakten svarte «hentet i dag,
    går hver 7. dag». Kilden ble forsøkt, ikke hentet. Karantenen som
    fulgte var syv dager, og uke 31 måtte hentes med --tving.

    Konsekvensen hvis den regelen står: en kilde som feiler i mandagens
    cron er i karantene til neste mandag. Da er uka forbi, og en uke
    som er forbi kan ikke hentes. Det er nøyaktig den irreversible
    feilen systemet finnes for å hindre.

    `sist_ok` og ikke `feil_paa_rad > 0`: begge ville løst dagens sak,
    men de spør ulike spørsmål. `feil_paa_rad` svarer «gikk det galt
    etter forrige suksess» — et tall som KORRELERER med det vi vil
    vite, og som må holdes i takt med `sist_ok` for å fortsette å
    korrelere. To felt som kan svare ulikt er hele mønsteret fra F6 og
    F7. `sist_ok` svarer direkte på det vakten skal vite: når har vi
    sist noe å vise til. Ett felt, ett oppslag, ingen avstand mellom
    spørsmålet og målingen.

    Følgen er at vakten nå måler alderen på det vi HAR, ikke på det vi
    prøvde. Et forsøk som feiler rett etter en fersk suksess gir ikke
    hastverk: lyktes vi i går, ligger gårsdagens data på disk, og
    ingenting er i fare. Men i det øyeblikket en periode faktisk står
    på spill — ukas cron feiler, og `sist_ok` er syv dager gammel — er
    kilden forfalt ved neste kjøring, ikke om syv dager til.

    Ikke `fetched_at` fra proveniensen: health.json er én liten fil som
    allerede leses hver kjøring, mens proveniensen krever å åpne
    parquet-filer. (F4s andre argument — at en feilende kilde ikke
    skriver parquet — gjelder ikke lenger her, for det er nettopp de
    vellykkede kjøringene vi spør om nå. Lesekostnaden avgjør alene.)

    None returneres når vi ikke VET når kilden sist lyktes: kilden
    mangler i health.json, eller posten mangler `sist_ok` — inkludert
    `sist_ok: null`, som er det en kilde som ALDRI har lykkes har
    stående. Kalleren behandler None som forfalt. Fallback-oppførselen
    skal være å kjøre: en kilde som aldri hentes fordi vi ikke vet når
    den sist ble hentet er verre enn en som hentes for ofte. Det første
    er tapt historikk og kan ikke rettes i etterkant; det andre er en
    ekstra fil med løpenummer.

    Dette er ikke en teoretisk gren. `lusetall` sto i nøyaktig den
    tilstanden i produksjon 24.08: posten fantes, `sist_ok` var null.
    """
    post = (tilstand if tilstand is not None else les()).get(kilde)
    if not post:
        return None

    sist = post.get("sist_ok")
    if not sist:
        return None

    try:
        return (date.fromisoformat(i_dag) - date.fromisoformat(sist)).days
    except ValueError:
        return None   # ulesbar dato: vet ikke -> kjør


def _felt_per_kilde(observasjoner) -> dict[str, dict[str, int]]:
    """{kilde: {felt: antall}} fra observasjonsrammen.

    Kjernen teller selv. En kilde trenger ikke vite at feltvakten finnes
    — dette er tall kjøringen allerede har i hånda.
    """
    if observasjoner is None or observasjoner.is_empty():
        return {}
    telling: dict[str, dict[str, int]] = {}
    for rad in observasjoner.group_by(["source", "field"]).len().iter_rows():
        kilde, felt, antall = rad
        telling.setdefault(str(kilde), {})[str(felt)] = int(antall)
    return telling


def oppdater(
    resultater: list[Result], observed_at: str, observasjoner=None,
    historisk: bool = False,
) -> tuple[dict, list[str]]:
    """Returnerer ny helsetilstand og liste over kilder som trenger tilsyn.

    Tre uavhengige grunner havner i samme liste, med samme konsekvens
    (rød jobb): kilden er "nede" (har fungert minst én gang før, feiler
    nå), kilden har ALDRI fungert, eller kilden leverte men med et
    volumfall over terskelen.

    De to første skilles i teksten, ikke i konsekvensen. "Nede" betyr at
    noe som virket har sluttet å virke; "har aldri levert" betyr at
    kilden aldri har vært i drift. Det er to helt ulike oppgaver for den
    som leser meldingen, og de skal ikke se like ut.

    `historisk=True` for backfill: tilstanden røres ikke i det hele tatt.
    Volum- og feltreferansen er høyvannsmerker mot FORRIGE KJØRING, og
    hundrevis av historiske uker skrevet etter hverandre ville enten fyrt
    alarmen konstant eller løftet referansen til et nivå ingen ukentlig
    kjøring kan møte. Helsetilstanden handler om om innsamlingen virker
    nå, ikke om hvordan registeret så ut i 2014.
    """
    if historisk:
        return les(), []

    forrige = les()
    normal = feltnormal.les()
    innhold_per_kilde = feltnormal.mål_ramme(observasjoner)

    # Kilder som IKKE kjørte i dag (fordi de ikke var forfalt) skal beholde
    # tilstanden sin. Bygde vi dicten fra bare dagens resultater, forsvant
    # `sist_ok` for dem — og da ville alarmen "har fungert før, er nede nå"
    # aldri kunne utløses for en kilde som hoppes over en uke.
    ny: dict = dict(forrige)
    nede: list[str] = []
    felt_per_kilde = _felt_per_kilde(observasjoner)

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

        # Feltvakt: kun når kilden faktisk leverte. En nede kilde har
        # ingen felter, og skal ikke få referansen sin rasert.
        felt_varsel = None
        innhold_varsler: list[str] = []
        if r.ok:
            felt_naa = felt_per_kilde.get(r.source, {})
            felt_referanse, felt_varsel = _vurder_felter(r.source, felt_naa, gammel)
            ny[r.source]["felt_referanse"] = felt_referanse
            if felt_naa:
                ny[r.source]["felt_sist"] = felt_naa
            elif gammel.get("felt_sist"):
                ny[r.source]["felt_sist"] = gammel["felt_sist"]

            # Innholdsvakt. Egen prøve, ikke en utvidelse av den over:
            # «kom feltet» og «sa det noe» er to spørsmål, og et felt kan
            # svare ja på det første i 171 uker mens svaret på det andre
            # er nei. Se _vurder_innhold.
            innhold_naa = innhold_per_kilde.get(r.source, {})
            nullstrekk, innhold_varsler = _vurder_innhold(
                r.source, innhold_naa, gammel, normal)
            # Bare strekket lagres, ikke selve målingene. Målt: `innhold_sist`
            # for alle 72 felter ville tatt health.json fra 5,4 til 19,9 kB —
            # nesten firedoblet en fil som skrives om hver uke, med tall som
            # kan regnes ut fra snapshotet på nytt når som helst. Strekket
            # kan ikke det: det er tilstand som bygges opp over tid.
            ny[r.source]["innhold_nullstrekk"] = {
                f: v for f, v in nullstrekk.items() if v
            }
        else:
            if gammel.get("felt_referanse"):
                ny[r.source]["felt_referanse"] = gammel["felt_referanse"]
            if gammel.get("felt_sist"):
                ny[r.source]["felt_sist"] = gammel["felt_sist"]
            # Nede kilde: strekket står stille. Et felt som ikke ble hentet
            # har ikke vært tomt — det har ikke vært spurt.
            if gammel.get("innhold_nullstrekk"):
                ny[r.source]["innhold_nullstrekk"] = gammel["innhold_nullstrekk"]

        # En aktiv kilde som feiler skal ALLTID rapporteres. De to
        # tilfellene betyr ikke det samme for den som leser meldingen, og
        # skilles derfor i teksten — men begge feller jobben.
        #
        # Den gamle regelen krevde `sist_ok`, altså at kilden hadde
        # lykkes minst én gang før. Antakelsen var at en ny kilde er en du
        # sitter og ser på mens du skriver den. Den holder ikke: legges
        # kilden til av en agent og cron fyrer fem dager senere, feiler
        # den i det uendelige med exit 0, og ingen får vite det.
        if not r.ok:
            if gammel.get("sist_ok"):
                nede.append(f"{r.source} (nede, uke {strekk})")
            else:
                nede.append(
                    f"{r.source} (har ALDRI levert — feilet {strekk} "
                    f"kjøring(er) på rad, sist: "
                    f"{ny[r.source]['siste_feil'] or 'ukjent feil'})"
                )

        # Leverte, men mistenkelig lite av det -> samme alarm, annen årsak.
        # Fyrer hver uke så lenge nivået er brutt, ikke bare uka det skjedde.
        if volum_varsel:
            nede.append(volum_varsel)

        # Et felt som forsvant er egen sak, med egen kvittering.
        if felt_varsel:
            nede.append(felt_varsel)

        # Et felt som kom, men sluttet å si noe, er en tredje sak.
        nede.extend(innhold_varsler)

    return ny, nede


def skriv(tilstand: dict) -> None:
    HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_PATH.write_text(
        json.dumps(tilstand, indent=2, ensure_ascii=False), encoding="utf-8"
    )
