---
dato: 2026-09-02
tittel: Fravær av kjøring er en egen feilklasse, og ingen eksisterende vakt dekker den
status: gjeldende
commit: 9389366
---

## Hva som ble bestemt

To ting, begge i datarepoet:

1. **En dead man's switch** — `.github/workflows/tilsyn.yml` med logikken i
   `.github/tilsyn.py` — som kjører onsdag morgen og **feiler når det ikke
   finnes en vellykket innsamling de siste tre dagene**.
2. **En gjenkjøring samme uke** — en andre cron-utløser på `samle.yml`,
   tirsdag 19:00 UTC, som er idempotent og stille når mandagen gikk bra.

## Hvorfor dette er en egen feilklasse

Hver eneste vakt i dette systemet fanger en feil **inni** en kjøring:

| vakt | fanger |
|---|---|
| volumvakten | kilden leverte for få rader |
| feltvakten | et felt sluttet å bli levert |
| frekvensvakten | kilden er ikke hentet på for lenge |
| nedetidsalarmen | kilden har feilet flere ganger på rad |
| `Grunnlagssprik` | to snapshots kan ikke sammenlignes |
| ENK-vakten | et personregister er i ferd med å bli skrevet |

**Alle sammen forutsetter at kjøringen skjedde.** De er kode som kjører
inne i `run.py`. Uteblir `run.py`, kjører ingen av dem, og ingen av dem
kan rapportere sitt eget fravær.

GitHub Actions' cron er dokumentert som «best effort», ikke en garanti:
planlagte workflows kan forsinkes eller droppes ved høy last. En workflow
som aldri startet lager **ingen rød kjøring, ingen logg, ingen e-post**.
I Actions-oversikten ser uka nøyaktig ut som en uke der ingenting var
galt — for det finnes ingen kjøring å se på.

Skjer det en mandag, er den uka tapt for alltid. Det er CLAUDE.md regel
5, og den er ikke en formalitet: snapshotet fra en gitt dato lar seg ikke
hente i etterkant selv om registrene er åpne.

Det er den **stilleste** feilen systemet kan ha, og repoets bærende
prinsipp er at stille feil er farligere enn høylytte. Dette er det ene
stedet der **fravær av signal ER feiltilstanden**.

## Hva den leser, og hvorfor

### `health.json`, ikke `siste_kjoring.txt`

`data/siste_kjoring.txt` bærer en dato i første linje, men den er en
**commit-melding** — nyhetsbrevet som leses på telefonen — ikke et
tidsstempel. Den skrives av `run.py` og kan bli stående fra FORRIGE
kjøring hvis kjøringen dør underveis; `samle.yml` sier det uttrykkelig i
sin egen kommentar. Å måle alder på den ville vært å måle alderen på en
tekst som kan lyve om sin egen dato.

`data/health.json` bærer `sist_ok` og `sist_forsok` per kilde, satt av
`health.oppdater(resultater, kjoredato, naa)` der `kjoredato` er
kjøredagen. Den er ett lite JSON-oppslag, allerede committet i
datarepoet.

### `sist_ok`, ikke `sist_forsok`

Dette er **F8** ordrett: et FORSØK er ikke et RESULTAT.

`sist_forsok` sier at workflowen kjørte. `sist_ok` sier at den fikk data.
En cron som starter hver mandag og feiler hver mandag ville holdt
`sist_forsok` fersk for alltid, og alarmen ville tiet mens hver uke gikk
tapt.

Det er ikke hypotetisk. 24.08.2026 sto `lusetall` med `sist_ok: null` og
`sist_forsok` satt samme dag, etter tre `invalid_client`-feil. En alarm
på `sist_forsok` ville sagt «alt i orden» om en kilde som aldri hadde
levert en rad.

Verifisert: med `sist_forsok = 2026-08-31` og `sist_ok = 2026-08-24`
fyrer alarmen på 9 dager.

### MAKS over kildene, ikke MINSTE

Spørsmålet er **«kjørte innsamlingen i det hele tatt»**, ikke «er hver
kilde frisk». Det siste har allerede sine egne alarmer, og de er bedre
til det.

Med MINSTE ville én kilde som ligger nede permanent holdt denne alarmen
rød i det uendelige. Da blir den mutet — og **en mutet dead man's switch
er verre enn ingen**, fordi den gir dekning den ikke har. MAKS svarer
presist på det ene denne alarmen skal svare på: når hentet vi sist noe
som helst med hell.

## Terskelen: 3 dager

Kadensen alarmen måles mot:

    mandag 05:00 UTC    innsamling      (samle.yml, --planlagt)
    tirsdag 19:00 UTC   gjenkjøring     (samle.yml, idempotent)
    onsdag 06:00 UTC    tilsynet

Alderen på `sist_ok` når tilsynet kjører:

| tilstand | alder |
|---|---|
| normal uke, mandag OK | 2 dager |
| mandag uteble, tirsdagens gjenkjøring reddet den | 1 dag |
| begge uteble, uka etter en reddet uke | 8 dager |
| begge uteble | 9 dager |

Det er et **hull mellom 2 og 8**. Enhver terskel i 3..8 skiller de to
tilstandene. 3 er valgt fordi den fyrer tidligst og fortsatt har et helt
døgns slark mot en normal uke.

Grensen er verifisert i begge retninger: `sist_ok` 2 dager gammelt gir
exit 0, 3 dager gir exit 1.

Flyttes cron-tidene, skal regnestykket gjøres på nytt — **ikke tallet
justeres til alarmen slutter å fyre**.

## Hvorfor tilsynet går ONSDAG og ikke tirsdag

Dette er det ene punktet som avviker fra den opprinnelige skissen, og
grunnen er alarmfatigue.

Gjenkjøringen går tirsdag kveld. Kjørte tilsynet tirsdag morgen, ville
det fyrt på en mandag som systemet er i ferd med å reparere selv noen
timer senere. Da roper alarmen ulv på en tilstand som går over av seg
selv, og en alarm som roper ulv blir mutet.

Onsdag morgen har **begge** de automatiske forsøkene vært innom. Fyrer
den da, har systemet gjort alt det kan på egen hånd, og det som gjenstår
krever et menneske. Det er det eneste tidspunktet der et varsel både er
sant og handlingsbart.

Kostnaden er ett døgns forsinkelse i varselet. Den er akseptabel fordi
uka uansett ikke kan reddes automatisk på det tidspunktet — og fordi
alternativet er en alarm ingen ser på.

## Gjenkjøringen, og hvorfor den ikke har `--planlagt`

Den andre cron-utløseren er tirsdag og ikke torsdag fordi **ISO-uka må
være den samme**: kildene regner gyldighetsdatoen sin av kjøredatoen
(`gjelder_for`), så en gjenkjøring i uke N+1 henter en annen uke og
redder ingenting.

`--planlagt` utelates med vilje, og det er ikke en detalj. Gikk mandagen
bra, finner tirsdagen alt skrevet fra før, og `--planlagt` gjør nettopp
det til en feil:

> `::error::Planlagt kjøring samlet ingenting — alle kilder hadde
> allerede skrevet snapshotet sitt.`

Da ville jobben vært rød hver eneste tirsdag i en frisk uke — samme
alarmfatigue som avsnittet over. Skillet går på `github.event.schedule`,
som bærer cron-uttrykket som utløste kjøringen; `event_name` er
`"schedule"` for begge og kan ikke skille dem.

### Idempotensen er verifisert, ikke antatt

To kjøringer etter hverandre 02.09.2026:

    FØR       1751 snapshotfiler, 1718 changelogfiler
    kjøring 1 biomasse 2026-05-31 hentet — 140 observasjoner, 115 endringer
    ETTER 1   1752 snapshotfiler, 1719 changelogfiler
    kjøring 2 «Alle kilder har allerede skrevet», exit 0
    ETTER 2   1752 snapshotfiler, 1719 changelogfiler

Den andre kjøringen skrev **null** nye snapshots og **null** nye
changelog-rader. To vakter i `run.py` fanget den, i rekkefølge: steg 2
(frekvensvakten, `[vent]`) for de fem kildene som var hentet nylig, og
steg 2b (`[har]`) for ekspertgruppen, hvis gyldighetsdato allerede lå
skrevet.

Merk at kjøring 1 gjorde ekte arbeid — biomasse for 2026-05-31 var
forfalt. Det er nettopp poenget med en gjenkjøring: den skal hente det
som mangler og la resten være.

## Hva som ville snudd det

- **GitHub gir en garanti om cron-punktlighet.** Da er dette en alarm mot
  noe som ikke kan skje, og den kan gjøres sjeldnere. Ingenting i dagens
  dokumentasjon peker den veien.
- **Innsamlingen flyttes til en kjøreplan som selv rapporterer at den
  ikke kjørte** — en scheduler med heartbeat, eller en ekstern tjeneste
  som forventer et signal. Da er dette duplikat, og duplikate alarmer
  skal ikke stå.
- **Terskelen viser seg å fyre på friske uker.** Da er kadensen endret og
  regnestykket over skal gjøres på nytt — men tallet skal utledes av den
  nye kadensen, ikke justeres til alarmen tier.
- **Alarmen fyrer og ingen gjør noe.** Da er problemet ikke terskelen,
  men at varselet ikke når fram. En dead man's switch uten mottaker er
  en kommentar.
