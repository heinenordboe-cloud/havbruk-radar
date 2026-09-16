---
dato: 2026-09-16
tittel: Grensa går ved SSB-sektor 2300, ikke ved formen ENK
status: besluttet
commit: [fylles inn]
---

# Grensa går ved SSB-sektor 2300, ikke ved formen ENK

**Bestemt:** Enheter i SSBs institusjonelle sektor **8200** (husholdninger)
og **2300** (personlige foretak) hentes ikke inn. I dagens registre er det
organisasjonsformene `ENK`, `DA`, `ANS` og `PRE`. De filtreres i kilden før
observasjoner opprettes og før rådataene arkiveres, de forsvinner ved
lesing av gamle snapshots, og `core/snapshot.py` nekter å skrive et
snapshot som likevel inneholder dem.

Dette lukker `[din vurdering]`-punktet i
[2026-08-22-enk-filtreres-i-kilden.md](2026-08-22-enk-filtreres-i-kilden.md),
som lot det stå åpent om grensa skulle gå ved formen eller ved sektoren.

---

## 1. Hvorfor formen ENK ikke var riktig grense

Beslutningen 22.08 skilte på RETTSSUBJEKTET: et enkeltpersonforetak ER
innehaveren, mens et ansvarlig selskap er et eget rettssubjekt med eget
organisasjonsnummer, egen adresse og partsevne. Deltakerne står bare i
rolleregisteret som pipelinen aldri spør etter, og selskapsdata om en
juridisk person er ikke personopplysninger (GDPR fortalepunkt 14).

Den analysen er fortsatt riktig om rettssubjektet. Den svarer bare ikke
på spørsmålet vi faktisk stiller, som er om **raden vi lagrer peker på et
navngitt menneske.**

Feltene vi lagrer om et DA er de samme som gjorde de 34 ENK-ene til
persondata: navn, kommune, postnummer, næringskode, registreringsår,
`konkurs`, `under_tvangsavvikling`. Deltakerne hefter personlig med hele
sin formue. At de står i et register vi ikke spør i, gjør dem ikke
uidentifiserbare — det gjør bare at vi ikke er den som slår dem opp.

SSB trekker den samme grensa uavhengig av dette resonnementet, og den er
etterprøvbar i et felt vi allerede lagrer:

| sektor | betydning | former (målt) |
|---|---|---|
| 8200 | husholdninger | ENK |
| 2300 | personlige foretak | DA, ANS, PRE |
| 2100 | private aksjeselskaper | AS, ASA, SA |

## 2. ALLE 64, ikke bare de 46 med personnavn

Spørsmålet kunne vært avgjort snevrere: ta bare de DA/ANS-ene som HAR et
personnavn — «Hansen og Olsen DA» — og la «Nordlaks Havbruk Nord DA»
stå. Den veien er stengt, og den er stengt med et tall.

**Målt 15.09.2026 på enhetsregisteret-snapshotet:** en navneprøve — to
eller tre ord, ingen bedriftsord — treffer **1278 av 1807** entiteter, og
**1196 av dem er AS**. Brreg skriver navn i VERSALER (1795 av 1807), så
«NORDLAKS OPPDRETT AS» og «HANSEN OG OLSEN DA» har nøyaktig samme form.

Navneprøven er altså ikke upresis — den er verdiløs alene. Og en regel
som avhenger av hvordan et navn SER UT, er ikke en regel: det er samme
feil som ni-siffer-prøven fra 16.08, en syntaktisk prøve der spørsmålet
er semantisk. `core/persondata.py` sa det på forhånd; målingen gir det et
tall.

Derfor filtreres alle 64, ikke de 46 som tilfeldigvis også ser slik ut.
`publiseringsvakt.personeksponert()` beholder navneleddet, men bare som
TELLER — en teller felles ikke av å ta feil.

## 3. Filteret spør om to felter, og aldri om navnet

`core/persondata.py` har fra i dag to uavhengige ledd:

    er_personform(kode)      organisasjonsform mot PERSONFORMER
    er_personsektor(kode)    institusjonell_sektorkode mot PERSONSEKTORER

Begge trengs, og det er målt hvorfor:

- **Sektorleddet** er det eneste som kan fange en form ingen har ført
  opp. En liste er en oppregning noen må huske å utvide; sektoren er et
  felt registeret selv fyller ut.
- **Formleddet** er det eneste som virker der sektoren mangler. `KBO`
  (31 enheter) og `NUF` (21) oppgir ingen sektorkode i det hele tatt.

I dag peker de to på nøyaktig samme enheter. Det er ikke overflødighet —
det er referansepunktet: den dagen de peker ulikt, er det fordi
registeret har fått noe vi ikke kjente.

**To lag, som før:** `fetch()` holder personene ute av rå-arkivet,
`parse()` holder dem ute ved re-parse av gamle arkivfiler, og
`snapshot._les()` holder dem ute av alt som leses. Vakten i
`snapshot.write()` leser nå begge feltene.

### `eierskap` måtte oversette, ellers hadde utvidelsen vært verre enn virkningsløs

pub-aqua bruker sitt eget vokabular: `JointLiabilityCompany`, ikke `DA`.
`er_personform("JointLiabilityCompany")` er usant uansett hva lista
inneholder, så utvidelsen i `persondata` ville ikke virket i den kilden.

Verre enn ikke å virke: snapshotet bærer den OVERSATTE koden, fordi
`FORM_KART` skriver `organisasjonsform = DA`. Vakten i `snapshot.write()`
ville da felt hele eierskaps-snapshotet mens filteret slapp de samme
radene gjennom — kilden og vakten ville stilt spørsmålet i hvert sitt
vokabular. `er_person()` går derfor gjennom `FORM_KART` før den spør
`persondata`, og `test_form_kart_gjor_hver_personform_stoppbar` håndhever
at hver oversettelse til en personform faktisk stopper.

`JointlyOwnedShippingCompany` ble samtidig MÅLT inn i `FORM_KART`:
registerets eneste enhet av typen slås opp hos Brreg til
organisasjonsform `PRE` (Partrederi), sektor 2300. Det er 1 av 1 og ikke
367 av 367 som de fem andre parene — men det er hele populasjonen, og det
er et oppslag, ikke en slutning fra navnelikhet.

## 4. Hva som ble målt

Alt under er kjørt mot levende registre 16.09.2026, ikke mot testdata.

### Enhetsregisteret — kjøringen som ville skjedd

    265 foretak filtrert bort som fysisk person (ANS 31, DA 32, ENK 201, PRE 1)
    1750 entiteter i snapshotet
    0 i sektor 2300 eller 8200
    vakten i snapshot.write(): godtar

201 → 265. De 64 nye er hele DA/ANS/PRE-bestanden i utvalget.

### Eierskap — 93 tillatelser mot 84

    Person                              62
    SoleProprietorship                  22
    JointLiabilityCompany     (DA)       6     ny
    UnlimitedLiabilityCompany (ANS)      2     ny
    JointlyOwnedShippingCompany (PRE)    1     ny

De 9 nye fordeler seg på 5 eiere.

### Dekning på lokalitetsnivå — 96,63 % → 96,30 %

Målt med kildens egne kall og telling i minnet, prøven kjørt to ganger —
én gang med grensa slik den var, én gang slik den er:

    lokaliteter i akvakultur         1782
    med selskapskobling FØR          1722      96,63 %
    med selskapskobling ETTER        1716      96,30 %

**6 lokaliteter mistet sin eneste selskapskobling.** Oppdelingen av de 66
uten, og hvilke som er permanent utelukket:

| grunn | antall | permanent? |
|---|---|---|
| eier er privatperson eller ENK | 57 | **ja** |
| eier er DA, ANS eller partrederi (sektor 2300) | 6 | **ja, fra i dag** |
| ingen aktiv tillatelse i registeret | 3 | nei — tettes når registeret får en |

**63 permanent utelukket**, mot 57 før. Se `docs/KILDE-EIERSKAP.md`
punkt 8, som er oppdatert med målingen.

De 6 skiller seg fra de 57 på ett punkt: de er utelukket av en grense VI
satte, ikke av at eieren er en privatperson. Flyttes grensa tilbake,
kommer de tilbake.

### De andre kildene

`akvakultur`, `lusetall`, `sjotemperatur`, `biomasse`, `biomasselag`,
`romming`, `ekspertgruppen`, `trafikklysvedtak` og `reguleringsomraader`
har verken `organisasjonsform` eller `institusjonell_sektorkode` og går
urørt gjennom filteret. Det er verifisert ved at hele suiten kjører grønn
og ved at `vis.py` regenererer med uendrede entitetstall for dem.

### Testene

**780 passerer.** To tester sto omvendt fram til i dag og er snudd med
begrunnelse i koden:

| test | var | er |
|---|---|---|
| `test_da_og_ans_beholdes` | DA og ANS skal beholdes | `test_da_ans_og_partrederi_filtreres` |
| `test_selskapsformer_slipper_gjennom[JointLiabilityCompany]` | slipper gjennom | `test_sektor_2300_stoppes_i_pub_aquas_eget_vokabular` |

Den første bar denne setningen: «Faller denne, er valget endret — og da
skal beslutningen endres med den.» Den falt, og dette er beslutningen.

## 5. Det utvidelsen avdekket i publiseringsvakten

`publiseringsvakt.py` har en `personform`-prøve som leter etter kodene i
`PERSONFORMER` som hele ord. Den var riktig så lenge lista var `{"ENK"}`:
«ENK» betyr ikke noe annet noe sted.

**`DA` gjør det.** Målt over nyeste snapshot per kilde: `DA` er verdien
av `kapasitet_enhet` i **748 rader** — dekar, ikke delt ansvar. Kjørt mot
den ene ekte genererte fila vi har, meldte prøven fire funn, og alle fire
var arealenheten eller en feltoppsummering.

Det er CLAUDE.md 1b-2 en gang til: en kontroll som måler noe som LIGNER
det den skal måle, og som er riktig akkurat så lenge de to faller sammen.
En blokkerende vakt som fyrer på hver arealangivelse blir slått av.

Prøven er derfor delt, og delingen er MÅLT og ikke listet:

- **Entydige koder** (`ENK`, `ANS`, `PRE`) felles som hele ord, hvor som
  helst i fila.
- **Tvetydige koder** — de som også er en lovlig verdi et annet sted i
  dataene — felles bare der feltnavnet `organisasjonsform` står i
  nærheten. `tvetydige_koder()` måler settet mot snapshotene ved hver
  kjøring, så en ny kilde som tar `ANS` i bruk som enhetskode demper
  prøven av seg selv, og en som slutter, skjerper den igjen.

Etterprøvd mot ekte output: den STALE `oversikt.html` (generert før
grensa flyttet seg) felles med 2 funn, begge ekte — sida oppgir `DA` som
en levende verdi av `organisasjonsform`. Regenerert med `vis.py` etter
endringen er sida ren, og porten gir exit 0.

## 6. Prisen

**6 lokaliteter og 64 foretak, hver uke, for alltid.** Det er 0,33
prosentpoeng dekning på lokalitetsnivå og 3,5 % av lokalitetene som er
systematisk usynlige — opp fra 3,2 %.

Skjevheten peker samme vei hver gang: de som forsvinner er små,
personeide anlegg. En analyse som sier «X % av kapasiteten eies av de ti
største» regner på et utvalg der de minste eierne mangler per
konstruksjon, og differansen er nå litt større enn den var i går.

**Historikken røres ikke.** Snapshotene som allerede ligger i datarepoet
beholder sine 64 DA/ANS/PRE på disk — append-only, regel 2 — og de
forsvinner ved lesing i stedet, hver gang. `snapshot.filtrert_bort()`
teller dem, og `publiseringsvakt.py --rapport` skriver tallet ved hver
kjøring: 72 ved målingen i dag (64 fra enhetsregisteret, 8 fra eierskap).

## 7. Kjente hull, sagt rett ut

1. **`KBO` og `NUF` mangler sektorkode.** 31 + 21 enheter som ingen av de
   to leddene kan svare på. Et konkursbo etter et enkeltpersonforetak er
   utvilsomt knyttet til en fysisk person, og vi vet ikke hvor mange av de
   31 som er det. Det er ikke undersøkt, og det er den nærmeste tråden
   hvis grensa skal flyttes igjen.
2. **Én partrederi-rad står igjen i to eierskaps-snapshots.** Snapshotene
   02.09 og 14.09 bærer `eier_type = JointlyOwnedShippingCompany` uten en
   oversatt `organisasjonsform`-rad — `FORM_KART` kjente ikke typen da de
   ble skrevet. Lesedøra leser `organisasjonsform`, ikke pub-aquas
   vokabular, og kan derfor ikke se den. Målt: **1 tillatelse i 2 filer**,
   og eiernavnet har personform. Den forsvinner fra snapshots skrevet fra
   og med i dag. Å lukke den for de to gamle ville krevd at `core/`
   kjenner en kildes vokabular — to lister som skal si det samme, altså
   formen F6 og F7 hadde — eller at en append-only fil skrives om.
   **Ikke lukket, og det er et valg.**
3. **`PERSONFORMER` er fortsatt ikke versjonert.** Et gammelt resultat vet
   ikke hvilken liste det ble regnet ut under. Kjøringsloggen fører nå
   både `personformer` og `personsektorer`, men det gjelder framover. Se
   `docs/FORSLAG-personformer-versjonering.md`.
4. **Vakten i `snapshot.write()` ser bare to feltnavn.** `eierskap` oppgir
   formen for 2839 av 2953 tillatelser og sektoren for ingen. Vakten
   fanger at et kjent filter sviktet — ikke at listene er riktige.

## Ville snudd det

- **At sektor 2300 viser seg å inneholde former som ikke er personlige.**
  Grensa er begrunnet med at SSB plasserer personlige sammenslutninger
  der. Dukker det opp en form i 2300 der ingen fysisk person kan
  identifiseres, er sektoren feil instrument, og grensa må skrives om som
  noe annet enn en sektorprøve.
- **At dekningstapet vokser vesentlig.** 6 lokaliteter er en pris verdt å
  betale for at repoet ikke skal være et personregister. 60 ville vært et
  annet regnestykke, og da må spørsmålet stilles på nytt — men da som
  «skal vi publisere aggregater uten eier» og ikke som «skal vi lagre
  personopplysninger».
- **At Brreg slutter å oppgi `institusjonellSektorkode`.** Da faller det
  uavhengige leddet bort, og filteret er tilbake til en liste noen må
  huske å utvide. Formleddet ville fortsatt virket for de fire kjente
  kodene, men referansepunktet i punkt 3 ville vært borte.

**Ville IKKE snudd det:** at et DA har et navn som ikke ligner et
personnavn. Det er nettopp den prøven som er målt verdiløs, og å la den
avgjøre for de 18 ville vært å gjeninnføre den bakveien.
