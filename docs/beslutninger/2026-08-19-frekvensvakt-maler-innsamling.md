---
dato: 2026-08-19
tittel: Frekvensvakten måler innsamlingstidspunkt, ikke observasjonsalder
status: utkast
korrigert: 2026-08-24
commit: 
---

# Frekvensvakten måler innsamling, ikke observasjon

> **UTKAST.** Skrevet ut fra diffen og reproduksjonen, ikke som ferdig
> vurdering. Avsnittene «Prisen» og «Ville snudd det» er skisser og skal
> skrives om for hånd.

> **KORRIGERT 24.08.2026.** Feltet valgt her — `sist_forsok` — var feil.
> Retningen står: vakten skal måle innsamlingen, ikke observasjonen.
> Men et FORSØK er ikke en INNSAMLING, og forskjellen kostet en uke.
> Se [Korreksjonen: sist_forsok var feil felt](#korreksjonen-sist_forsok-var-feil-felt)
> nederst. Alt over det avsnittet er teksten slik den sto 19.08, og
> `dager_siden_kjoring()` heter i dag `dager_siden_ok()`.

**Bestemt:** Frekvensvakten spør `health.dager_siden_kjoring()`, som
leser `sist_forsok` fra `health.json`. Den spurte før
`snapshot.dager_siden()`, som er døpt om til
`dager_siden_observasjon()` for å si hva den faktisk måler.

**Skillet:** «Når samlet vi sist inn» er ikke «hvor gammel er nyeste
observasjon». For en kilde uten etterslep er de to like, og forskjellen
er usynlig. For en kilde med etterslep er de aldri like.

## Tallene

Lusetall henter uke N-4 og skriver fila under mandagen i den uka.
Nyeste fil er derfor alltid datert fire uker tilbake — også når kilden
kjører helt som den skal. Reproduksjon, kilden kjørt samme dag:

    F4  health.sist_forsok = 2026-08-19  (i dag)
    F4  nyeste snapshot    = 2026-07-22  (uke N-4)
    F4  forfalt=['lusetall']  venter=[]
    F4  `if not kilder:` kan fyre? NEI — permanent forfalt

`dager_siden` ble permanent 28, alltid over terskelen på 7, så
`kilder` var aldri tom og `if not kilder:` i `run.py` kunne ikke fyre.
Vakten fra [stille cron-svikt](2026-08-17-stille-cron-svikt.md) var død
kode for denne kilden.

Etter endringen, samme oppsett:

    forfalt=[]  venter=[('falsk', 0)]

Verifisert mot faktisk produksjons-`health.json` for mandag 24.08:

    akvakultur         sist_forsok=2026-08-17   dager=7      min_dager_mellom=7
    enhetsregisteret   sist_forsok=2026-08-17   dager=7      min_dager_mellom=7
    lusetall           sist_forsok=(mangler)    dager=None   min_dager_mellom=7

    forfalt 2026-08-24: ['akvakultur', 'enhetsregisteret', 'lusetall']

## Ikke et backfill-artefakt

Feilen så ut som noe backfillen dro med seg, siden det var backfillen
som fylte mappa med filer datert 2012–2013. Det er den ikke. Den oppsto
da lusetall ble lagt til som kilde, med `uker_etterslep = 4`, og den
ville aldri gått over av seg selv: N-4 er kildens normaltilstand, ikke
en overgangsfase. En tom backfill-mappe hadde gitt nøyaktig samme
resultat den første uka kilden kjørte.

## Hvorfor sist_forsok og ikke fetched_at

> Dette avsnittet er **overstyrt 24.08**. Argumentene under er ikke
> gale — de er svar på et spørsmål vakten ikke skulle stilt. Se
> korreksjonen nederst.

Begge kunne svart. `sist_forsok` valgt fordi `health.json` er én liten
fil som allerede leses hver kjøring, mens proveniensen krever å åpne
parquet-filer.

Det avgjørende er likevel et annet: **en kilde som feiler skriver ingen
parquet.** Proveniensen kan derfor ikke svare på «når forsøkte vi
sist», bare på «når lyktes vi sist». Å utlede forsøket fra de
vellykkede kjøringene er nøyaktig samme sirkularitet som F1 — kilden
som aldri har lykkes faller ut av regnestykket og blir usynlig.

## Fallback: vet vi ikke, så kjører vi

`dager_siden_kjoring()` returnerer `None` når kilden mangler i
`health.json`, eller når posten mangler `sist_forsok`. Kalleren
behandler `None` som forfalt. *(Feltet er `sist_ok` fra 24.08. Regelen
er uendret, og den ble bredere: `sist_ok: null` — en kilde som er
forsøkt, men aldri har lykkes — faller nå inn under den.)*

Dette er forutsetningen for at fiksen ikke innfører en ny stille feil.
Behandles «ukjent» som «fersk», blir resultatet en kilde som aldri
hentes fordi vi ikke vet når den sist ble hentet — samme klasse feil som
den vi nettopp fjernet, bare med motsatt fortegn. Tapt historikk kan
ikke rettes i etterkant; en unødvendig henting koster en ekstra fil med
løpenummer.

Ikke hypotetisk: `lusetall` sto i nøyaktig denne tilstanden da fiksen
ble skrevet. `health.json` i produksjon kjente bare `akvakultur` og
`enhetsregisteret`.

## Mønsteret, som er verdt mer enn korreksjonen

Beslutningen fra 18.08 innførte selve begrepsskillet denne posten
handler om — `observed_at` handler om verden, `fetched_at` om oss — og
konkluderte i samme tekst med at `dager_siden()` «gjør allerede det
riktige». Skillet ble altså innført ett sted og ikke fulgt til alle
konsekvenser. Frekvensvakten leste `observed_at` og trodde den leste
`fetched_at`, og det var den nye definisjonen som gjorde de to til
forskjellige ting.

Selve korreksjonen er triviell: ett oppslag byttet ut, ett navn rettet.
Mønsteret er ikke. Når et begrepsskille innføres, er spørsmålet ikke om
skillet er riktig, men hvor mange steder i koden som allerede stod på
at de to var samme ting. Posten fra 18.08 listet opp tre ting som måtte
endres i kode. Frekvensvakten var en fjerde, og den sto omtalt i samme
avsnitt som den listen — som eksempel på noe som *ikke* trengte endring.

## Prisen

*(skisse — skrives om)* En frekvensvakt som ikke lenger kan utledes fra
det som ligger på disk. `health.json` blir en fil systemet er avhengig
av for å vite hva det skal gjøre, ikke bare for å rapportere hva som
skjedde. Fallback-regelen gjør konsekvensen av å miste den utvetydig,
men ikke gratis.

## Ville snudd det

*(skisse — skrives om)*

- At fallback-regelen viser seg å gi gjentatte unødvendige hentinger i
  praksis — altså at `health.json` oftere er ufullstendig enn antatt.
  Da er svaret å finne ut hvorfor den er ufullstendig, ikke å gjøre
  ukjent til fersk.
- At en kilde trenger å hentes på nytt fordi *dataene* er for gamle, og
  ikke fordi det er lenge siden vi kjørte. Da er `dager_siden_observasjon()`
  riktig spørsmål, men til en annen vakt enn denne.

---

## Korreksjonen: sist_forsok var feil felt

*(24.08.2026 — F8.)*

**Bestemt:** vakten leser `sist_ok`. Funksjonen heter `dager_siden_ok()`.

### Hva som skjedde

Lusetall feilet tre ganger på rad 24.08 med `invalid_client` fra
BarentsWatch. Posten i produksjons-`health.json` etter siste forsøk:

    "lusetall": {
      "sist_ok": null,
      "sist_forsok": "2026-08-24",
      "feil_paa_rad": 3,
      "antall_sist": 0,
      "siste_feil": "RuntimeError: 400 fra token-endepunktet ({\"error\":\"invalid_client\"}) …"
    }

Null rader hentet, aldri en vellykket kjøring. Neste kjøring sa likevel:

    [vent] lusetall    hentet i dag, går hver 7. dag

Regnet ut fra den faktiske fila, med `sist_forsok` som målepunkt:

    2026-08-24   dager=0   venter
    2026-08-25   dager=1   venter
    2026-08-30   dager=6   venter
    2026-08-31   dager=7   forfalt

Syv dagers karantene, utløst av tre mislykkede forsøk. Uke 31 måtte
hentes med `--tving`.

### Hvorfor det er den irreversible feilen

Cron går mandag 05:00. Feiler en kilde der, er neste anledning
mandagen etter — og da er uka forbi. En uke som er forbi kan ikke
hentes senere (regel 5 i `CLAUDE.md`). Vakten som finnes for å hindre
at vi kjører for ofte, hadde blitt mekanismen som sikrer at vi ikke
kjører når det gjelder.

Fortegnet er verdt å merke seg: F4 gjorde lusetall PERMANENT forfalt —
en kilde som alltid kjørte. F8 gjorde den permanent fersk. Samme
mekanisme, samme klasse feil, motsatt utslag. Den ufarlige varianten
kom først.

### Hvorfor sist_ok og ikke feil_paa_rad > 0

Begge oppfyller kravet «en kilde som feilet skal forsøkes igjen ved
neste kjøring». Valget står likevel, fordi de spør ulike spørsmål.

`feil_paa_rad > 0` svarer «gikk noe galt etter forrige suksess». Det
KORRELERER med det vakten vil vite, og det er nøyaktig formen på
feilen regel 3 i `CLAUDE.md` beskriver: kontrollen som ble begrunnet
med at alle `entity_id` var ni siffer, når spørsmålet var
organisasjonsform. En korrelasjon holder helt til den ikke gjør det.

Det praktiske utslaget: `feil_paa_rad` er et andre felt som må holdes
i takt med `sist_ok` for å fortsette å korrelere. To felt som kan svare
ulikt om samme sak er hele mønsteret fra F6 og F7. Nullstilles det ene
uten det andre — av en migrering, en manuell redigering, en
`godta_*`-kvittering som vokser seg større — er vakten stille tilbake
i F8.

`sist_ok` svarer direkte: når har vi sist noe å vise til. Ett felt, ett
oppslag, ingen avstand mellom spørsmålet og målingen. Det er også
feltet `oppdater()` allerede skriver og allerede lar stå urørt når en
kilde feiler — regelen finnes i dataene fra før, den var bare ikke båret
over i kontrollen som skulle håndheve den.

### Følgen: vakten måler det vi HAR, ikke det vi prøvde

En kilde som lyktes i går og feiler i dag, venter fortsatt. Det er med
vilje: gårsdagens data ligger på disk, ingen periode er i fare, og en
henting til ville vært en `.2`-fil uten nytt innhold. Karantenen
begynner å telle fra suksessen, ikke fra forsøket.

I det øyeblikket noe faktisk står på spill — ukas cron feiler, og
`sist_ok` dermed er syv dager gammel — er kilden forfalt ved neste
kjøring, hva enn `sist_forsok` sier. Det er kravet, og det følger av
målingen i stedet for å være et unntak lagt oppå den.

### Hva F4-argumentet svarte på

Avsnittet «Hvorfor sist_forsok og ikke fetched_at» over er ikke galt.
«En kilde som feiler skriver ingen parquet, så proveniensen kan ikke
svare på når vi forsøkte sist» stemmer fortsatt.

Men det svarte på feil spørsmål. Vakten skal ikke vite når vi sist
forsøkte. Den skal vite når vi sist LYKTES — og det er nettopp det
proveniensen kunne svart på. Argumentet valgte riktig FIL av feil
grunn: `health.json` vinner fordi den er én liten fil som allerede
leses hver kjøring, ikke fordi parquet-filene mangler noe.

Sirkularitetsinnvendingen fra F1 gjelder heller ikke lenger. «Kilden
som aldri har lykkes forsvinner ut av regnestykket» var faren ved å
utlede forsøk fra suksesser. Her er fraværet av suksess selve svaret:
`sist_ok: null` gir `None`, og `None` er forfalt. Kilden som aldri har
lykkes blir den som alltid velges.

### Verifisert

Mot faktisk produksjons-`health.json`, begge tilstander:

    FØR fiksen (3ff42fd, lusetall nede)      kjøredato 2026-08-24
      akvakultur         sist_ok=2026-08-24  sist_forsok=2026-08-24  dager=0
      enhetsregisteret   sist_ok=2026-08-24  sist_forsok=2026-08-24  dager=0
      lusetall           sist_ok=None        sist_forsok=2026-08-24  dager=None
      forfalt=['lusetall']  venter=[('akvakultur', 0), ('enhetsregisteret', 0)]

    Samme tilstand, dagen etter               kjøredato 2026-08-25
      lusetall           dager=None
      forfalt=['lusetall']

    NÅ (origin/main, alt grønt)               kjøredato 2026-08-24
      alle tre           sist_ok=2026-08-24  dager=0
      forfalt=[]  venter=[akvakultur 0, enhetsregisteret 0, lusetall 0]

    NÅ, neste mandag                          kjøredato 2026-08-31
      alle tre           dager=7
      forfalt=['akvakultur', 'enhetsregisteret', 'lusetall']  venter=[]

Lusetall er forfalt hver dag så lenge den ikke har lykkes — ingen
karantene. De to friske kildene venter, og hele settet er forfalt igjen
neste mandag.

Og hele veien gjennom `run.py`, med `HAVBRUK_DATA_DIR` pekt på en kopi
av hver av de to tilstandene. FØR-tilstanden, den som ga bugrapporten:

    Kjøring 2026-08-24
      [vent] akvakultur           hentet i dag, går hver 7. dag
      [vent] enhetsregisteret     hentet i dag, går hver 7. dag
      [ok  ] lusetall              18341 observasjoner

Tre `[vent]`-linjer før fiksen, to nå — og uke 31 hentet uten `--tving`.
Nåtilstanden, der alle tre faktisk lyktes i dag:

    Kjøring 2026-08-24
      [vent] akvakultur           hentet i dag, går hver 7. dag
      [vent] enhetsregisteret     hentet i dag, går hver 7. dag
      [vent] lusetall             hentet i dag, går hver 7. dag

      Ingen kilder er forfalt. --tving overstyrer.

Samme linje, to ulike tilstander. Forskjellen er at ordet «hentet» nå
er sant i begge.

Fire tester dekker regelen, og alle fire feiler hvis oppslaget byttes
tilbake til `sist_forsok` (`tests/test_pipeline.py`):

    test_kilde_som_aldri_har_lykkes_er_forfalt
    test_kilde_som_feilet_i_gaar_velges_i_dag
    test_feilet_i_dag_med_gammel_suksess_velges
    test_feilet_forsok_forkorter_ikke_karantenen

Den siste er den bevisste følgen, ikke kravet: den fester at et feilet
forsøk heller ikke FORKORTER karantenen etter en fersk suksess.

### Mønsteret, sjette gang

Avsnittet «Mønsteret, som er verdt mer enn korreksjonen» over handlet om
et begrepsskille innført ett sted og ikke fulgt til alle konsekvenser.
Denne posten er samme tekst én runde til, og den ble skrevet av den
posten selv: `sist_forsok` ble valgt her, 19.08, i teksten som advarte
mot nøyaktig denne feilen.

Skillet er ikke lenger bare tid. `observed_at` mot `fetched_at` er
verden mot oss; `sist_forsok` mot `sist_ok` er forsøk mot resultat. Det
er to instanser av samme form: en mekanisme som måler noe som LIGNER
det den skal måle, og som er riktig i det ene tilfellet der de to faller
sammen — kilden uten etterslep, kjøringen som lykkes. `CLAUDE.md` regel
1b er utvidet til å si begge deler.
