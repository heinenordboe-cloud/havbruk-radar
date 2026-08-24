"""Inngangspunkt. Én kjøring, elleve steg.

    python run.py                 # alle kilder som er forfalt
    python run.py --bare enhetsregisteret
    python run.py --torrkjor      # hent og vis alt, skriv ingenting
    python run.py --tving         # kjør selv om kilden ble hentet nylig
    python run.py --planlagt      # den ukentlige cron-kjøringen
    python run.py --fasit         # treffrate på avgjorte prediksjoner

Hver kilde har sin egen `min_dager_mellom`. Kjøringen henter bare de som
er forfalt, slik at en ny kilde kan aktiveres midt i uka uten å skrive
dagens snapshot for de andre på nytt.

`--torrkjor` hopper over forfallssjekken med vilje: en tørrkjøring er til
for å inspisere data, og da vil du se alt.

`--planlagt` er for workflowen, ikke for deg ved tastaturet. En manuell
kjøring som ikke finner noe forfalt skal være stille — det er riktig at
en kilde hentet i går ikke hentes på nytt. Men den SAME hendelsen på den
ukentlige cron-kjøringen betyr at uka gikk uten et snapshot, usynlig for
alt annet enn denne linjen. `--planlagt` gjør det skillet eksplisitt:
null forfalte kilder er da en feil, ikke en stille exit.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))   # så run.py virker uansett hvor du står

from core import (  # noqa: E402
    changelog, diff, health, miljo, paths, predictions, registry, runner,
    signals, snapshot,
)


def bygg_commitmelding(kjoredato: str, resultater, endringer, scoret,
                       fasit=None) -> str:
    """Commit-meldingen er nyhetsbrevet ditt de neste fire månedene.

    Du leser den i GitHub-appen på telefonen. Ingen nettside nødvendig.
    """
    # `scoret` er nå ALLE endringer, ikke bare treffene. Overskriften sier
    # begge tall: uklassifiserte er den ærlige målingen av blindsonen, og
    # den skal stå i nyhetsbrevet, ikke bare i loggen.
    traff = signals.treff(scoret)
    uklassifisert = scoret.height - traff.height

    linjer = [
        f"Snapshot {kjoredato} — {endringer.height} endringer, "
        f"{traff.height} scoret, {uklassifisert} uklassifiserte",
        "",
    ]

    for rad in traff.head(10).iter_rows(named=True):
        navn = rad["entity_name"] or rad["entity_id"]
        linjer.append(
            f"* {navn}: {rad['field']} {rad['old_value']} -> {rad['new_value']}"
            f" [{rad['signal']}]"
        )

    if traff.height == 0 and endringer.height:
        linjer.append("* ingen endringer traff en signalregel")

    # Hvilke felter blindsonen består av. Dette er lista over regler som
    # mangler, sortert etter hvor mye de ville fanget.
    topp_uten = signals.uklassifiserte_felter(scoret)
    if topp_uten:
        linjer.append("")
        linjer.append("Uklassifisert, vanligste felter:")
        for felt, antall in topp_uten:
            linjer.append(f"* {felt}: {antall}")

    # Fasit på anslag som forfalt denne uka. Dette er den eneste delen av
    # meldingen som sier noe om DEG og ikke om registrene.
    if fasit is not None and fasit.height:
        linjer.append("")
        linjer.append(f"Prediksjoner avgjort: {fasit.height}")
        for rad in fasit.iter_rows(named=True):
            merke = {"traff": "TRAFF", "bom": "bom  "}.get(rad["utfall"], "?    ")
            linjer.append(
                f"* [{merke}] {rad['id']} {rad['entitet']}.{rad['felt']}"
                f" — {rad['begrunnelse']}"
            )

    # Gyldighetsdatoen står per kilde, ikke bare kjøredatoen i toppen.
    # Uten den ser en lusetall-linje i uke 34 ut som om den handler om
    # uke 34, og det gjør den ikke — den handler om uke 30.
    linjer.append("")
    for r in resultater:
        gjelder = f" (gjelder {r.gjelder_for})" if r.gjelder_for != kjoredato else ""
        linjer.append(f"{'ok  ' if r.ok else 'FEIL'} {r.source}: {r.count}{gjelder}")

    return "\n".join(linjer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bare", help="kjør kun én kilde")
    parser.add_argument("--torrkjor", action="store_true", help="ikke skriv filer")
    parser.add_argument("--tving", action="store_true",
                        help="kjør selv om dagens snapshot finnes (skriver ny fil med løpenummer)")
    parser.add_argument("--planlagt", action="store_true",
                        help="dette er den ukentlige cron-kjøringen: null forfalte "
                             "kilder er en feil, ikke en stille exit")
    parser.add_argument("--godta-felt", metavar="KILDE",
                        help="godta kildens nåværende feltsett som nytt normalt, "
                             "og avslutt. Kvitteringen for et felt som legitimt "
                             "er borte — uavhengig av --godta-volum")
    parser.add_argument("--godta-volum", metavar="KILDE",
                        help="godta kildens siste volum som nytt friskt nivå, og "
                             "avslutt. Kvitteringen for et reelt fall — bruk den "
                             "når volumvarselet er riktig, ikke for å dempe det")
    parser.add_argument("--fasit", action="store_true",
                        help="vis treffrate for avgjorte prediksjoner, og avslutt")
    args = parser.parse_args()

    # Lesing, ikke innsamling: viser fasit og avslutter.
    if args.fasit:
        feil = predictions.valider()
        for f in feil:
            print(f"  FORMATFEIL {f}")
        rate = predictions.treffrate()
        if rate.height == 0:
            print("Ingen avgjorte prediksjoner ennå.")
        else:
            print(rate)
        return 1 if feil else 0

    # Kvittering, ikke innsamling: skriver health.json og avslutter.
    if args.godta_volum:
        ok, melding = health.godta_volum(args.godta_volum)
        print(melding)
        return 0 if ok else 1

    # Egen kvittering med vilje: at totalen legitimt er lavere er ikke
    # det samme som at et felt legitimt er borte.
    if args.godta_felt:
        ok, melding = health.godta_felt(args.godta_felt)
        print(melding)
        return 0 if ok else 1

    # Dagen VI kjører. Ikke det samme som datoen dataene gjelder for —
    # den spør vi hver kilde om under, med gjelder_for(). Alt som handler
    # om oss (frekvensvakt, helsetilstand, prediksjonsvindu) måles mot
    # denne; alt som handler om verden måles mot kildens egen dato.
    kjoredato = datetime.now(timezone.utc).date().isoformat()

    # 1. Finn kilder
    kilder = registry.discover()
    if args.bare:
        kilder = [k for k in kilder if k.name == args.bare]
    if not kilder:
        print("Ingen aktive kilder funnet.")
        return 1

    print(f"\nKjøring {kjoredato}")

    # 1b. Har de aktive kildene nøklene sine? Spurt NÅ, samlet, for alle.
    #
    # FØR frekvensvakten, ikke etter. Det er ikke en detalj: lørdagens
    # test-dispatch hoppet over lusetall via finnes_allerede() og gikk
    # grønt med en secret som ikke fantes. Hullet sto åpent fra 18.08 og
    # ble oppdaget mandag 24.08 05:00 — av cron, som er den ene kjøringen
    # der en tapt uke faktisk koster en uke. Sjekken kjøres derfor på en kilde
    # som skal hoppes over i dag også: en manglende nøkkel er feil i
    # oppsettet, ikke i denne kjøringen, og den skal si fra den dagen
    # den oppstår framfor den dagen den rammer.
    #
    # Meldingen navngir ALLE manglende variabler. Én om gangen ville med
    # ukentlig cron blitt én uke per nøkkel.
    mangler = miljo.manglende(kilder)
    if mangler:
        print()
        print(miljo.forklar(mangler))
        print(f"\n::error::Innsamlingen startet ikke: "
              f"{', '.join(sorted(mangler))} er ikke satt.")
        return 1

    # 2. Hopp over kilder som ble hentet nylig nok
    #
    # «hentet» betyr HENTET, ikke forsøkt. Linja under sa «hentet i dag»
    # om lusetall 24.08, som hadde feilet tre ganger samme dag og aldri
    # levert en rad — se F8 i health.dager_siden_ok. Vakten måler nå
    # sist_ok, så ordet i utskriften og tallet bak det er samme sak.
    if not args.torrkjor and not args.tving:
        kilder, venter = runner.velg_forfalte(kilder, kjoredato)
        for kilde, dager in venter:
            nar = "i dag" if dager == 0 else f"for {dager} dag(er) siden"
            print(f"  [vent] {kilde.name:<20} hentet {nar}, "
                  f"går hver {kilde.min_dager_mellom}. dag")

        if not kilder:
            if args.planlagt:
                print("\n::error::Planlagt kjøring samlet ingenting — alle kilder "
                      "ble hoppet over av frekvensvakten. Uka er tapt hvis dette "
                      "ikke undersøkes.")
                return 1
            print("\n  Ingen kilder er forfalt. --tving overstyrer.")
            return 0

    # 2b. Hopp over uker som allerede ligger skrevet.
    #
    # Frekvensvakten spør «er det lenge siden sist», denne spør «finnes
    # denne uka allerede». For en kilde uten etterslep er de nesten det
    # samme spørsmålet. For lusetall er de det ikke: kjører du to ganger
    # i samme uke, peker begge kjøringene på SAMME gyldighetsdato, og
    # uten denne vakten blir den andre en .2-fil ved siden av den første.
    #
    # Sjekken skjer før hentingen, som i backfill.py: en uke som er
    # ferdig skal ikke koste et API-kall for å oppdages.
    #
    # --tving overstyrer. Det er hele poenget med flagget, og løpenummeret
    # finnes nettopp for det tilfellet der du vet hva du gjør.
    if not args.torrkjor and not args.tving:
        ferdige = [k for k in kilder
                   if k.name in snapshot.finnes_allerede(k.gjelder_for(kjoredato))]
        for kilde in ferdige:
            print(f"  [har]  {kilde.name:<20} {kilde.gjelder_for(kjoredato)} "
                  f"ligger skrevet fra før")
        kilder = [k for k in kilder if k not in ferdige]

        if not kilder:
            if args.planlagt:
                print("\n::error::Planlagt kjøring samlet ingenting — alle kilder "
                      "hadde allerede skrevet snapshotet sitt. Undersøk om "
                      "jobben kjørte to ganger.")
                return 1
            print("\n  Alle kilder har allerede skrevet. --tving overstyrer.")
            return 0

    # 3. Kjør dem, isoler feil
    observasjoner, resultater = runner.run_all(
        kilder, kjoredato, arkiver=not args.torrkjor
    )
    for r in resultater:
        print(f"  [{'ok  ' if r.ok else 'FEIL'}] {r.source:<20} {r.count:>6} observasjoner")
        if not r.ok:
            print(f"         {r.error.strip().splitlines()[-1]}")

    if args.torrkjor:
        print(f"\nTørrkjøring — {len(observasjoner)} observasjoner, ingenting skrevet.")
        return 0

    # 4 og 5. Diff og skriv, PER KILDE og på kildens egen dato.
    #
    # Én dato for hele kjøringen var feilen: lusetall henter uke N-4, så
    # kjøredatoen ligger fire uker etter uka dataene gjelder for. Fila
    # het da 2026-08-24 mens radene i den var observert 2026-07-27, og
    # backfillen av den samme uka skrev 2026-07-27 — samme uke, to
    # filnavn, en skjøt midt i serien.
    #
    # Diffen må fortsatt skje FØR skrivingen for hver kilde, ellers
    # finner previous() kildens egen ferske fil og diffen blir tom.
    naa = snapshot.to_frame(observasjoner)
    endringsdeler = []
    filer = []

    for r in resultater:
        if not r.ok:
            continue
        egne = [o for o in observasjoner if o.source == r.source]
        if not egne:
            continue
        endringsdeler.append(diff.compare(snapshot.to_frame(egne), r.gjelder_for))
        filer += snapshot.write(egne, r.gjelder_for)

    endringer = diff.slaa_sammen(endringsdeler)

    # 6. Scor endringene
    scoret = signals.score(endringer)

    # 7. Legg til i endringsloggen (egen fil per dato, aldri omskriving)
    changelog.skriv_per_dato(endringer)

    # 8. Oppdater helsetilstand
    #
    # KJØREDATOEN, ikke gyldighetsdatoen. health.json svarer på «når
    # forsøkte vi sist», og det er et spørsmål om oss. Sendes kildens
    # gyldighetsdato hit, tror frekvensvakten at lusetall sist kjørte for
    # fire uker siden hver eneste uke — nøyaktig feilen F4 rettet.
    #
    # `naa` sendes med: feltvakten teller rader per (kilde, felt) og ser
    # et felt forsvinne som volumvakten er for grovkornet til å merke.
    tilstand, nede = health.oppdater(resultater, kjoredato, naa)
    health.skriv(tilstand)

    # 9. Avgjør prediksjoner hvis vinduet er ute
    #
    # REKKEFØLGE: må skje ETTER snapshot.write(). Et anslag med vindu som
    # lukker i dag skal se dagens observasjon. Flyttes dette opp foran
    # skrivingen, dømmes anslaget på forrige ukes tall og taper en uke —
    # stille, fordi utfallet blir et fullt gyldig "bom".
    #
    # Et formatavvik felles IKKE kjøringen. Innsamlingen er viktigere enn
    # prediksjonene: mister du uka, kan den ikke hentes igjen, mens en
    # feilskrevet YAML kan rettes i morgen. Avviket går i tilsyn-lista og
    # gjør jobben rød i stedet.
    #
    # KJØREDATOEN: «er vinduet ute nå» er et spørsmål om kalenderen, ikke
    # om hvilken uke en enkelt kilde gjelder for. Et anslag med frist
    # 24.08 forfaller 24.08, uansett hvor stort etterslep kilden det
    # måles mot har.
    formatfeil = predictions.valider()
    fasit = predictions.evaluer(kjoredato)
    predictions.skriv(fasit, kjoredato)

    # 10. Skriv commit-melding
    melding = bygg_commitmelding(kjoredato, resultater, endringer, scoret, fasit)
    paths.COMMIT_MSG_PATH.parent.mkdir(parents=True, exist_ok=True)
    paths.COMMIT_MSG_PATH.write_text(melding, encoding="utf-8")

    # 11. Oppsummer
    traff = signals.treff(scoret)
    uklassifisert = scoret.height - traff.height

    print(f"\n  {len(filer)} snapshot skrevet")
    print(f"  {endringer.height} endringer, {traff.height} scoret, "
          f"{uklassifisert} uklassifiserte")

    # Den ene summen som ikke kan stemme ved et sammentreff. Går den ikke
    # opp, teller scoringen feil, og da er alt under her upålitelig.
    if scoret.height != endringer.height:
        print(f"::error::Scoringen mistet rader: {scoret.height} ut mot "
              f"{endringer.height} inn. Se docs/SIGNALREGLER.md punkt 0.")

    if fasit.height:
        print(f"  {fasit.height} prediksjon(er) avgjort:")
        for rad in fasit.iter_rows(named=True):
            print(f"    · [{rad['utfall']}] {rad['id']} — {rad['begrunnelse']}")

    for rad in traff.head(15).iter_rows(named=True):
        print(f"    · {rad['entity_name']}: {rad['field']} "
              f"{rad['old_value']} → {rad['new_value']}  [{rad['signal']}]")

    # Blindsonen, med navn. Uten denne lista vet du ikke hva du ikke ser.
    topp_uten = signals.uklassifiserte_felter(scoret)
    if topp_uten:
        print("  uklassifisert, vanligste felter:")
        for felt, antall in topp_uten:
            print(f"    · {felt}: {antall}")

    # Tre ulike årsaker havner i samme liste, med samme konsekvens:
    # kilden er nede (har fungert før, feiler nå), den leverte for lite
    # (volumvakten), eller den leverte men ba om tilsyn (Source.advarsler,
    # f.eks. et NACE-søk uten treff). Meldingen sier derfor ikke lenger
    # "leverer ikke" — to av tre tilfeller leverte. Hver enkelt streng
    # sier hvilken det er.
    tilsyn = (nede
              + [a for r in resultater for a in r.advarsler]
              + [f"prediksjonsformat: {f}" for f in formatfeil])

    if tilsyn:
        print(f"\n  KREVER TILSYN: {', '.join(tilsyn)}")
        return 1   # -> rød jobb -> e-post fra GitHub, hver uke til det er fikset

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
