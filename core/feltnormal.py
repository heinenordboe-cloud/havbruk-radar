"""Hva et felt normalt INNEHOLDER — ikke bare at det leveres.

Feltvakten i `health.py` teller rader per felt. Den fanger at et felt
slutter å komme. Den fanger ikke at feltet fortsetter å komme og slutter
å si noe.

Målt i produksjon 24.08.2026, over 761 uker med lusetall:

    har_rensefisk                 siste True 2023-04-17, deretter 171
                                  uker med eksakt null. Nivået før:
                                  46,5 lokaliteter/uke.
    har_medikamentell_behandling  død fra 2024-01-01 (én enkelt True
                                  2024-11-11), deretter 89 uker null.
                                  Nivået før: 44,6 lokaliteter/uke.

Begge leverte 1777 rader hver eneste uke gjennom hele nullperioden.
Feltreferansen i health.json sto på 1777 for begge, og vakten så to
fulle kolonner og tidde. Referansen ble dessuten satt sommeren 2026,
da begge for lengst var døde — den festet dødsleiet som normalen.

## Målet: minoritet

Ett tall, ikke ett per datatype: **hvor mange rader har IKKE feltets
vanligste verdi denne uka.**

    har_rensefisk    1777 rader, alle False    -> minoritet 0
    har_laksefisk    1360 True, 417 False      -> minoritet 417
    voksne_hunnlus   571 rader, 193 verdier    -> minoritet 479
    kapasitet_enhet  1346 TN, 433 andre        -> minoritet 433

Grunnen til at det er dette tallet og ikke «antall True»: et boolsk felt
kan dø i begge retninger. `har_laksefisk` er True for 1360 av 1777 —
skulle det fryse til bare True, ville «antall True» STEGET, og en vakt
som teller True-verdier ville sett vekst i det øyeblikket feltet sluttet
å skille noe fra noe. Minoriteten faller uansett hvilken verdi feltet
fryser til, og den trenger ikke vite om feltet er boolsk, numerisk eller
kategorisk.

`sanne`, `ikke_null` og kvartilene lagres ved siden av — de er det et
menneske leser når alarmen går. De styrer den ikke.

## Terskelen er målt, ikke gjettet

760 uker lusetall ga tallene under. Et prosentfall duger ikke: de små
feltene faller legitimt 70–90 % fra uke til uke (`har_ila` verste 0,17,
`har_rensefisk` 0,08), og null er en helt normal uke for dem —
`har_ila` har 22 nulluker, `har_pd` 33, `har_mekanisk_fjerning` 24.

Det som skiller en død uke fra et dødt felt er STREKKET. Lengste
lovlige nullstrekk i steady state (2014–2022) er 7 uker. De to som døde
ligger på 171 og 89.

Simulert over alle 761 uker:

    N= 8 uker  ->  5 alarmer   (2 fra oppstarten i 2012, 3 ekte)
    N=13 uker  ->  5 alarmer   (samme)
    N=26 uker  ->  4 alarmer

13 uker — et kvartal — er valgt. Null alarmer i 2014–2022, og de to
dødsfallene fanges 13 uker etter at de inntraff. De to fra 2012 er
`har_pd` og `har_ila` før BarentsWatch begynte å rapportere dem, altså
riktige varsler om at feltet ikke bar innhold ennå.

## Gulvet er et LAVVANNSMERKE

Speilbildet av volumreferansen. `volum_referanse` er et høyvannsmerke
som aldri synker av seg selv; `gulv` er en bunn som aldri heves av seg
selv. Begge har samme grunn: en referanse som følger med dataene er et
rullende snitt, og et rullende snitt godtar degradering i sakte film.

Gulvet settes til det LAVESTE feltet har vært i hele historikken. Da er
antall historiske falske alarmer null per konstruksjon, og en ny alarm
betyr bokstavelig «lavere enn feltet noen gang har vært». Eneste vei ned
er `godta_felt()`.

## Hvorfor ikke i health.json

health.json overskrives i sin helhet hver kjøring. Den er riktig sted
for tilstand som endrer seg ukentlig — `sist_ok`, `feil_paa_rad`,
strekkene. Den er feil sted for en NORMAL utledet av 760 uker
historikk, av to grunner:

1. En fil som skrives om hver uke kan ikke svare på «hva var normalen i
   uke X». Det svaret finnes da bare i git-loggen til datarepoet, og en
   analyse leser ikke git. Det er samme mangel som utvalgsutvidelsen
   (CLAUDE.md 1b-3).
2. Normalen skal ikke kunne endres av en ukentlig kjøring i det hele
   tatt. Det var nettopp en automatisk oppdatert referanse som festet
   dødsleiet til `har_rensefisk` som normaltilstand.

Derfor: én fil per gang normalen etableres eller kvitteres, aldri rørt
igjen, i `data/feltnormal/<dato>.json`. Nyeste fil gjelder. Append-only
som rådata og changelog (CLAUDE.md regel 2).
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from core.paths import FELTNORMAL_DIR  # noqa: F401

# Antall kjøringer på rad med tomt innhold før vakten sier fra.
# Målt, ikke gjettet — se modulens docstring. Overstyres per kilde i
# config.yml (kilder.<navn>.maks_nullstrekk).
STANDARD_MAKS_NULLSTREKK = 13

# Hvor mange ULIKE observasjonsdatoer et felt må hvile på før gulvet
# etableres i det hele tatt. Under dette blir `gulv` None, som leses
# «vet ikke ennå» — og gulvvakten hopper over feltet.
#
# Målt, ikke gjettet. Andelen vinduer der feltet står helt stille
# (maks == min, altså «gulvet er dagens verdi») over lusetall og
# sjotemperatur, 763 felt-vinduer per k:
#
#     k=1  100,0 %     k=6   14,1 %     k=16   8,9 %
#     k=2   31,0 %     k=8   12,1 %     k=20   8,0 %
#     k=3   22,0 %     k=10  11,0 %     k=26   7,0 %
#     k=4   18,0 %     k=13   9,8 %     k=52   4,1 %
#
# Kurven har kneet ved 13. Etter det er fallet marginalt — de neste 13
# ukene kjøper 2,7 prosentpoeng — og resten er felter som FAKTISK står
# stille (lusetalls døde felter er konstant 0 gjennom hele historikken).
# Det er forskjellen som betyr noe: under 13 datoer vet vi ikke om
# stillheten er feltets natur eller vår egen mangel på observasjoner.
#
# Tallet er det samme som STANDARD_MAKS_NULLSTREKK, og det er tilfeldig.
# De er målt hver for seg på hvert sitt spørsmål — dette på hvor lenge
# et gulv er en kopi, det andre på hvor lange nullstrekk som finnes
# legitimt. At begge landet på 13 er ikke en begrunnelse for noen av dem.
MIN_DATOER_FOR_GULV = 13

SANNHETSVERDIER = {"true", "false"}


def _tall(serie: pl.Series) -> pl.Series:
    return serie.cast(pl.Float64, strict=False).drop_nulls()


def mål(verdier: pl.Series) -> dict:
    """Innholdsmålene for ett felt i én kjøring.

    `minoritet` er tallet vakten bruker. Resten er for den som leser
    alarmen: `sanne` for boolske felter, `ikke_null` og kvartilene for
    numeriske. De lagres fordi «minoritet falt fra 46 til 0» ikke sier
    hva slags felt det var.
    """
    n = verdier.len()
    if n == 0:
        return {"rader": 0, "distinkte": 0, "minoritet": 0, "toppverdi": None,
                "type": "tom"}

    vc = verdier.value_counts().sort("count", descending=True)
    topp_verdi = vc[verdier.name][0]
    ut = {
        "rader": n,
        "distinkte": vc.height,
        "minoritet": n - vc["count"][0],
        "toppverdi": str(topp_verdi),
    }

    unike = {str(v).strip().lower() for v in verdier.unique().to_list()}
    if unike <= SANNHETSVERDIER:
        ut["type"] = "boolsk"
        ut["sanne"] = int(verdier.str.strip_chars().str.to_lowercase()
                          .eq("true").sum())
        return ut

    tall = _tall(verdier)
    if tall.len() == n:
        ut["type"] = "numerisk"
        ut["ikke_null"] = int((tall != 0).sum())
        ut["median"] = float(tall.median()) if tall.len() else None
        ut["p95"] = float(tall.quantile(0.95)) if tall.len() else None
        return ut

    ut["type"] = "kategorisk"
    return ut


def mål_ramme(ramme: pl.DataFrame) -> dict[str, dict[str, dict]]:
    """{kilde: {felt: mål}} for en observasjonsramme.

    Kjernen måler selv, som `health._felt_per_kilde()`. En kilde skal
    ikke vite at innholdsvakten finnes.
    """
    if ramme is None or ramme.is_empty():
        return {}
    ut: dict[str, dict[str, dict]] = {}
    for (kilde, felt), g in ramme.group_by(["source", "field"]):
        ut.setdefault(str(kilde), {})[str(felt)] = mål(g["value"])
    return ut


def bygg(historikk: list[tuple[str, pl.DataFrame]]) -> dict[str, dict]:
    """Normalen for én kilde, utledet av hele historikken.

    `historikk` er (dato, ramme) eldst først — det `snapshot.les_mellom()`
    gir. For hvert felt regnes:

      gulv                laveste minoritet feltet har hatt. Alarmen går
                          under dette, så null historiske uker ville
                          utløst den. None når grunnlaget er for tynt til
                          at tallet betyr noe — se `MIN_DATOER_FOR_GULV`.
      normalt_nullstrekk  lengste sammenhengende rekke uker med tomt
                          innhold, UTENOM et strekk som fortsatt pågår.
                          Det pågående strekket er nettopp det som skal
                          etterforskes, ikke normaliseres.
      dodt_naa            antall uker det pågående nullstrekket har vart.

    Et felt som er tomt i det øyeblikket normalen bygges får `gulv: 0` og
    et `dodt_naa` som sier hvor lenge. Da kan vakten ikke fyre på gulvet,
    men strekkvakten kan — og det er riktig fordeling: gulvet sier «under
    det laveste noensinne», strekket sier «har ikke sagt noe på lenge».

    ## Én DATO er én observasjon, ikke én fil

    `les_mellom()` gir flere innslag for samme dato når det finnes
    løpenummerfiler, og det er riktig for den som leser forløp. Her ville
    det telt den samme innsamlingen flere ganger: akvakultur hadde åtte
    filer fra to datoer 25.08.2026, og normalen så ut til å hvile på åtte
    observasjoner mens den hvilte på to. Både gulvet og nullstrekket ble
    målt i filer der enheten skulle vært en innsamling.

    Derfor kollapses historikken til én ramme per dato — den siste, som
    er den med høyest løpenummer. Da betyr «13» det samme for en kilde
    som er kjørt om igjen fire ganger på en dag som for en som ikke er
    det.
    """
    per_dato: dict[str, pl.DataFrame] = {}
    for dato, ramme in historikk:
        per_dato[dato] = ramme          # siste vinner: høyest løpenummer

    serier: dict[str, list[int]] = {}
    typer: dict[str, str] = {}
    for dato in sorted(per_dato):
        m = mål_ramme(per_dato[dato])
        for felter in m.values():
            for felt, tall in felter.items():
                serier.setdefault(felt, []).append(tall["minoritet"])
                typer[felt] = tall.get("type", "kategorisk")

    ut: dict[str, dict] = {}
    for felt, v in serier.items():
        etterfolgende = 0
        for x in reversed(v):
            if x == 0:
                etterfolgende += 1
            else:
                break
        kropp = v[: len(v) - etterfolgende] if etterfolgende else v
        strekk = best = 0
        for x in kropp:
            strekk = strekk + 1 if x == 0 else 0
            best = max(best, strekk)
        # Gulvet etableres bare når det hviler på nok observasjoner.
        # Under det er «laveste vi har sett» det samme som «det vi ser
        # nå», og en referanse som er en kopi av dagens verdi gjør
        # enhver normal svingning til en alarm.
        ut[felt] = {
            "gulv": min(v) if len(v) >= MIN_DATOER_FOR_GULV else None,
            # Alltid det som FAKTISK ble observert, også når gulvet er
            # None. Fila skal beskrive historikken; vakten avgjør hva den
            # tør stole på. Uten dette kunne ingen se hva et tynt
            # grunnlag inneholdt, og en senere vurdering måtte lese alle
            # snapshotene på nytt.
            "laveste_sett": min(v),
            "median": int(pl.Series(v).median()),
            "normalt_nullstrekk": best,
            "dodt_naa": etterfolgende,
            "uker": len(v),
            "type": typer[felt],
        }
    return ut


def _dato_og_versjon(stem: str) -> tuple[str, int]:
    """'2026-08-25.2' -> ('2026-08-25', 2). Uten løpenummer: versjon 1.

    Samme funksjon og samme grunn som i snapshot.py: alfabetisk sortering
    setter '2026-08-25.2.json' FØR '2026-08-25.json', fordi '2' < 'j'.
    Nyeste fil ville da vært den eldste, og les() ville servert en normal
    som var kvittert ut. Fanget av en test, ikke av lesing.
    """
    dato, _, versjon = stem.partition(".")
    return dato, int(versjon) if versjon else 1


def _filer() -> list[Path]:
    if not FELTNORMAL_DIR.exists():
        return []
    return sorted(FELTNORMAL_DIR.glob("*.json"),
                  key=lambda p: _dato_og_versjon(p.stem))


def les() -> dict:
    """Nyeste normal. Tom dict når ingen er etablert.

    Tom betyr «vet ikke», og kalleren skal da IKKE varsle. Motsatt av
    frekvensvaktens fallback, og av samme grunn som utvalgsutvidelsen
    merkes framfor å slettes: en alarm på et grunnlag vi ikke har er
    støy, og støy er det som får folk til å slutte å lese alarmer.
    """
    filer = _filer()
    if not filer:
        return {}
    return json.loads(filer[-1].read_text(encoding="utf-8"))


def skriv(normal: dict, dato: str, begrunnelse: str) -> Path:
    """Ny normal som EGEN fil. Skriver aldri om en som finnes.

    Kolliderer datoen med en fil som ligger der, får den løpenummer —
    samme mønster som `snapshot._ledig_sti()`. Grunnen er den samme:
    «hva var normalen i uke X» skal kunne besvares av dataene, og en fil
    som skrives om kan ikke svare på det.
    """
    FELTNORMAL_DIR.mkdir(parents=True, exist_ok=True)
    sti = FELTNORMAL_DIR / f"{dato}.json"
    n = 2
    while sti.exists():
        sti = FELTNORMAL_DIR / f"{dato}.{n}.json"
        n += 1

    sti.write_text(json.dumps({
        "etablert": dato,
        "begrunnelse": begrunnelse,
        "maks_nullstrekk": STANDARD_MAKS_NULLSTREKK,
        "kilder": normal,
    }, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return sti


def sammendrag(normal: dict) -> list[str]:
    """Linjer for konsollen når normalen bygges."""
    linjer = []
    for kilde in sorted(normal.get("kilder", {})):
        felter = normal["kilder"][kilde]
        dode = {f: v for f, v in felter.items() if v.get("dodt_naa", 0) > 0}
        linjer.append(f"  {kilde}: {len(felter)} felt, "
                      f"{len(dode)} uten innhold nå")
        for f, v in sorted(dode.items(), key=lambda kv: -kv[1]["dodt_naa"]):
            linjer.append(
                f"      {f:<30} tomt i {v['dodt_naa']} uker "
                f"(normalt maks {v['normalt_nullstrekk']}, median {v['median']})")
    return linjer

