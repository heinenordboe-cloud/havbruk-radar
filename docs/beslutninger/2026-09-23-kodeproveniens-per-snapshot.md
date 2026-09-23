---
dato: 2026-09-23
tittel: Hvert snapshot bærer koden som skrev det
status: utkast
commit: [fylles inn]
---

# Kodeproveniens per øyeblikksbilde

**UTKAST.** Hva som ble bestemt står under, med målingene.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Hva som fantes fra før: ingenting

Et snapshot bar tretten felt. Fire av dem er proveniens:

    fetched_at       når vi spurte
    source_version   kildens egen versjonsteller, satt for hånd
    raw_hash         sha256 av kroppen kilden sendte
    utvalg           hva kilden ba om

**Ingen av dem sier hvilken kode som kjørte.** `source_version` er nærmest
og duger ikke: den er et heltall en menneskehånd øker, og kilden hadde
selv skrevet ned symptomet før symptomet:

> «snapshotene som alt ligger på disk er skrevet av to ulike filtre og
> bærer BEGGE `source_version = "1"`. De er ikke til å skille fra
> hverandre i dataene, bare på `fetched_at`.»
> — `sources/eierskap.py`

## F15, to ganger

**21.09.2026.** 47 commits lå ucommitet-men-upushet i to uker. Den
ukentlige innsamlingen kjører fra det som er PUSHET, og kjørte derfor
kode fra før 16.09. Grensa ved SSB-sektor 2300 var ikke aktiv, og
mandagens snapshot ble skrevet med personformer i seg. CLAUDE.md regel 7
er skrevet om den.

**23.09.2026.** `eierskap.fjern_egne_personer()` utelot `eier_type`
fordi «raden forsvinner fra neste snapshot av seg selv». MÅLT: `parse()`
dropper H-FJ-0018 fra arkivkroppene både 14.09 og 21.09 — men snapshotet
21.09 har den likevel. Samme rotårsak, og igjen usynlig i dataene.

## Bestemt 1: to felt, stemplet av `write()`

    kode_commit   sha for HEAD da fila ble skrevet
    kode_rent     «ja» om arbeidstreet var rent, «nei» ellers

CLAUDE.md 1b-3 avgjør plasseringen: kan et snapshot ALENE svare på hva
verdien var da raden ble skrevet? Kan det ikke det, skal verdien stemples
på raden. Hvilken kode som kjørte avgjør hva dataene BETYR — samme kropp
gir 1934 eller 2611 overføringer alt etter hvilket filter som leste den.

Stemplet settes i `snapshot.write()`, den ene veien alt går gjennom.
Ikke i hver kilde: en verdi som gjelder hele kjøringen skal ikke være noe
tolv kildeforfattere må huske.

Feltene står med vilje IKKE på `Observation`. Et felt på dataklassen er
et felt en kilde kan fylle, og en kilde som oppga sin egen commit ville
kunnet oppgi feil.

## Bestemt 2: `write()` stempler, `run.py` nekter

`write()` skriver det som er SANT, også «urent». En fil som sier at treet
var skittent er uendelig mye mer verdt enn en fil som tier.

Å NEKTE er innsamlingens jobb, før den henter noe.
`kodeproveniens.krev_sporbar()` krever tre ting:

1. git svarer
2. arbeidstreet er rent (`status --porcelain`, usporede filer med)
3. HEAD finnes på `origin/main` (`merge-base --is-ancestor`)

Vilkår 3 er det som fanger F15.

**Ingen escape-flagg.** Et flagg for å hoppe over dette ville stått i
cron-jobben om et halvt år, og `test_run_py_har_ingen_vei_rundt_
kodeproveniensen` holder det.

`--torrkjor` er unntatt, og bare den: den skriver ingen fil, så det
finnes ingen fil som kan bli uetterprøvbar.

Sjekken kommer ETTER nøkkelsjekken. En manglende secret er en feil i
oppsettet som skal meldes den dagen den oppstår, uansett hva
arbeidstreet ser ut som.

## Bestemt 3: porten spør om det som kan endre seg

Tre utfall, to av dem funn:

| fila | utfall |
|---|---|
| har ikke feltet | `kodeproveniens_ukjent` — rapporteres, blokkerer ikke |
| har feltet, tomt eller urent | funn |
| hash ikke på `origin/main` | funn |

**Om en commit er pushet, lagres ikke i fila.** Det kan endre seg etter
at fila ble skrevet — en commit kan pushes i morgen — og det er en
opplysning om verden nå, ikke om raden. CLAUDE.md 1b-7. Porten spør git
på nytt hver gang.

Skillet mellom de to første krever at man vet om KOLONNEN fantes, ikke
bare om den er tom. Lesedøra fyller manglende kolonner, så
`_les_med_tall()` returnerer nå også filas egne kolonner.

Lesingen bor i `core/snapshot.py`, fordi
`test_ingen_leser_snapshots_utenom_les` nekter enhver annen modul å
kombinere `RAW_DIR` med en parquet-lesing — og den har rett: en andre
lesevei er en vei rundt persondatafilteret. MÅLT: 1 833 filer på 3,4 s.

## Bestemt 4: de gamle filene merkes, ikke rettes

**1 833 filer, alle 12 kildene, har ingen kodeproveniens.** De blir
stående. Et stempel satt i ettertid ville påstått at fila ble skrevet av
kode som ikke fantes da — og append-only er append-only.

De rapporteres per kilde HVER kjøring, av samme grunn som
`filtrert_bort()` finnes: et aggregat ingen ser er det samme som ingen
kontroll. Tallet skal synke, én uke om gangen.

    data/raw/lusetall           765
    data/raw/sjotemperatur      765
    data/raw/biomasse           185
    data/raw/eierskap_historikk  42
    data/raw/ekspertgruppen      24
    data/raw/romming             14
    data/raw/enhetsregisteret    13
    data/raw/akvakultur          12
    data/raw/trafikklysvedtak     7
    data/raw/eierskap             3
    data/raw/biomasselag          2
    data/raw/reguleringsomraader  1

## En bivirkning verdt å nevne

Testsuiten kjørte git for å stemple, og da avhenger testene av
utviklerens arbeidstre: samme test grønn med rent tre, rød med urent.
`tests/conftest.py` gir dem et fast svar, som den allerede gjør for
datamappa. Den ekte oppførselen prøves av testene som selv setter
verdiene.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
