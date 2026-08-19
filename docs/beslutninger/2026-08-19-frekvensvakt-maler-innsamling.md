---
dato: 2026-08-19
tittel: Frekvensvakten måler innsamlingstidspunkt, ikke observasjonsalder
status: utkast
commit: 
---

# Frekvensvakten måler innsamling, ikke observasjon

> **UTKAST.** Skrevet ut fra diffen og reproduksjonen, ikke som ferdig
> vurdering. Avsnittene «Prisen» og «Ville snudd det» er skisser og skal
> skrives om for hånd.

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
behandler `None` som forfalt.

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
