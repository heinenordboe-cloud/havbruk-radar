# Enhetsregisteret — kildespesifikasjon

Alt i dette notatet er **målt** mot snapshotene i
`data/raw/enhetsregisteret/` 14.09.2026, og mot et levende kall til
Brreg samme dag der snapshotet ikke kan svare. Der noe bare er lest og
ikke verifisert, står det uttrykkelig.

**Kilde: Brønnøysundregistrene.** NLOD 2.0, og attribusjonen er et
vilkår — se punkt 7.

---

## 1. Endepunktet og utvalget

    https://data.brreg.no/enhetsregisteret/api/enheter

Åpent, ingen nøkkel, ingen registrering. Paginert; standard sidestørrelse
er 20, konfigurert til 100. Utvalget er en filtrering på næringskode.

**NI næringskoder, lest av `utvalg`-kolonnen i snapshotet 14.09.2026:**

    03.211   havbruk med fisk, hav og fjord
    03.212   havbruk med skalldyr
    03.221   ferskvannsbasert fiskeoppdrett
    03.222   ferskvannsbasert skalldyrsoppdrett
    03.300   tjenester tilknyttet fiske og fangst
    10.201   produksjon av saltfisk, tørrfisk og klippfisk
    10.202   frysing av fisk og fiskevarer
    10.203   produksjon av annen bearbeidet fisk
    10.912   produksjon av fiskefôr

**`10.209` er IKKE i bruk, og har aldri bidratt med en rad.** Koden er
utgått i gjeldende SN2007 — innholdet ligger nå i `10.202` og `10.203` —
og en utgått kode svarer `200 OK` med tom liste, ikke med en feil. Den
sto i `config.yml` i to dager (15.–17.08.2026) og ga null treff hele
tiden. Fjernet 17.08 22:07, samtidig som `03.222` og `10.203` kom inn.

Et notat utenfor repoet lister seks koder med `10.209` blant dem. **Den
lista var riktig 15.08 og er utdatert fra 17.08** — samme forhold som
dekningstallene i `docs/KILDE-AKVAKULTUR.md` punkt 4.2. Historikken står
i `docs/beslutninger/2026-08-24-utvalgsutvidelse-er-ikke-endring.md`.

At 10.209 kunne stå i to dager uten at noe sa fra, er grunnen til at
`_varsle_tomme_sok()` finnes: volumvakten måler totalen per KILDE og ser
ikke enkeltsøk, så ett av ni søk kan falle til null mens totalen holder
seg innenfor terskelen.

At listen ligger i `utvalg`-kolonnen og ikke bare i `config.yml`, er
CLAUDE.md 1b-3: et snapshot skal alene kunne svare på hva vi LETTE ETTER,
ikke bare hva vi fant. Uten det kan ingen sammenligning skille «ny i
bransjen» fra «ny i vårt utvalg» — utvidelsen 17.08 ga 25 804 av 26 673
endringer (96,7 %) før merkingen kom på plass. Se
`docs/beslutninger/2026-08-24-utvalgsutvidelse-er-ikke-endring.md`.

## 2. Volum per kjøring

| dato | rader | foretak | felter | kolonner |
|---|---|---|---|---|
| 2026-08-16 | 7 960 | 938 | 9 | 7 |
| 2026-08-17 | 27 074 | 938 | 32 | 7–10 |
| 2026-08-24 | 51 622 | 1 810 | 32 | 10 |
| 2026-08-31 | 51 616 | 1 810 | 32 | 12 |
| 2026-09-07 | 51 558 | 1 808 | 32 | 12 |
| 2026-09-14 | **51 524** | **1 807** | 32 | 12 |

Størrelsesorden: **ca. 51 500 observasjoner og ca. 1 807 foretak per
kjøring.** Fallet siden 24.08 er målt og forklart — se punkt 5.2.

**Et notat utenfor repoet oppgir «ca. 53 000». Målt er 51 524 —
overdrevet med ca. 1 500, altså 2,9 %.** Serien har dessuten falt hver
uke siden 24.08 (51 622 → 51 524), så avviket vokser. Bruk målingen.

Tre sprang i tabellen er strukturelle og ikke bevegelse i bransjen:

* **16.→17.08:** feltvalget gikk fra 9 til 32 felter.
* **17.→24.08:** næringskodelista ble utvidet. 938 → 1 810 foretak.
* **kolonnetallet 7 → 10 → 12:** `utvalg` og `published_at` kom til.
  Skjemautvidelser, ikke hendelser — `diff.compare()` undertrykker dem.

## 3. Feltene

32 felter per foretak.

    navn                              organisasjonsform
    naeringskode                      naeringskode2
    naeringskode3                     aktivitet
    antall_ansatte                    ansatte_er_registrert
    kommune                           kommunenummer
    postnummer                        poststed
    landkode
    konkurs                           under_avvikling
    under_tvangsavvikling
    registreringsdato                 stiftelsesdato
    vedtektsdato                      vedtektsfestet_formaal_hash
    aksjekapital                      antall_aksjer
    kapital_valuta                    kapital_innfort_dato
    registrert_i_foretaksregisteret   registrert_i_mvaregisteret
    mva_registreringsdato             siste_innsendte_aarsregnskap
    institusjonell_sektorkode         er_i_konsern
    historiske_navn_antall            paategninger_antall

**`ansatte_er_registrert` er ikke pynt.** Det skiller «null ansatte» fra
«ikke rapportert». Uten flagget blir en manglende rapportering til en
null i enhver analyse, og det er feil på den farlige måten. Samme skille
som `lus_er_rapportert` og `temperatur_er_rapportert`.

### Tre ting holdes bevisst utenfor

* **Roller** — styre, daglig leder, innehaver. Eget endepunkt, ikke rørt.
  Navn og fødselsdato på privatpersoner ville gjort repoet til et
  personregister med behandlingsansvar etter GDPR.
* **Gateadresse.** `postnummer` og `poststed` gir geografien uten å bygge
  et boligregister.
* **Telefon og målform.** Kontaktdata uten tolkningsverdi over tid.

Grensen mot det autoriserte API-et — roller inklusive fødselsnummer,
sikret med Maskinporten — er den CLAUDE.md regel 3 forbyr oss å krysse.
Vi bruker utelukkende det frie nivået. Se `docs/LISENSKJEDE.md`
merknad B.

## 4. Personlige foretak filtreres bort — 265 per kjøring

**Målt 16.09.2026 ved å kjøre kildens egen `fetch()`:**

    265 foretak filtrert bort som fysisk person (ANS 31, DA 32, ENK 201, PRE 1)

201 av dem er `ENK`. De 64 øvrige kom til 16.09.2026, da grensa ble
flyttet fra formen ENK til **SSB-sektor 8200 og 2300** — husholdninger og
personlige foretak. Se
`docs/beslutninger/2026-09-16-grensa-gaar-ved-sektor-2300.md`.
Tallet var 201 ved forrige måling (14.09.2026).

**Hvorfor det må gjøres.** Et ENK er ikke et eget rettssubjekt —
foretaket ER innehaveren. Selv uten gateadressen er navn, kommune,
postnummer, næring og konkursflagg opplysninger om en identifiserbar
fysisk person, og omtrent tjue av dem bærer innehaverens navn som
foretaksnavn.

For DA, ANS og partrederi er rettssubjektet et annet — selskapet er sitt
eget — men FELTSETTET er det samme, og deltakerne hefter personlig. Det
avgjørende er ikke hva foretaket er, men om raden peker på et navngitt
menneske.

**Prøven spør om to felter, aldri om navnet.** `organisasjonsform` mot
`PERSONFORMER`, og `institusjonellSektorkode` mot `PERSONSEKTORER`. Det
andre leddet er det eneste som kan fange en form ingen har ført opp; det
første er det eneste som virker for `KBO` og `NUF`, som mangler
sektorkode. En navneprøve ble målt verdiløs: to-tre ord uten bedriftsord
treffer 1278 av 1807 entiteter, hvorav 1196 er AS.

**To lag, med hver sin grunn:**

1. **I `fetch()`, før noe arkiveres.** Rå-arkivet lagrer hele API-svaret,
   og der lå gateadressen til hvert eneste ENK. Feltvalget gjelder bare
   snapshotet, ikke arkivet. Data som aldri hentes inn kan ikke lekke.
2. **I `parse()`**, fordi arkivfiler fra før 22.08.2026 (ENK) og før
   16.09.2026 (DA, ANS, PRE) fortsatt inneholder dem. En re-parse av et
   gammelt arkiv skal ikke føre dem inn igjen.

**Filteret teller ORGNUMRE, ikke treff.** Kilden søker på ni
næringskoder, og samme foretak kan komme i retur fra flere — 15 selskaper
gjorde det 17.08.2026. En teller ville rapportert samme ENK én gang per
kode, og tallet ville hoppet av at en næringskode ble lagt til, ikke av
at flere personer kom inn i utvalget.

**Kontrollen som sviktet, og hvorfor tallet står her.** Åpningen 16.08
ble begrunnet med at alle `entity_id` var ni siffer — og et ENK har ni
siffer akkurat som et AS. 34 ENK lå i hvert snapshot i fem dager.
Skillet fantes i dataene (`organisasjonsform`), men ble ikke båret over i
kontrollen. Se
`docs/beslutninger/2026-08-22-enk-filtreres-i-kilden.md`.

Tallet skrives **to steder** fordi filtreringen er stille av natur: en
enhet som aldri blir en observasjon etterlater seg ingen rad å savne, og
et hopp fra 201 til 900 ville ellers bety at søket har endret seg uten at
noe sa fra.

1. **Til kjøringsloggen**, som en linje et menneske leser mandag morgen.
2. **Inn i arkivkroppen** som en `meta`-post, fra 14.09.2026. Det er den
   som varer — stdout er borte når Actions-loggen utløper, og det er
   arkivet som skal kunne svare i ettertid. Se punkt 5.2.

## 5. Forbehold

### 5.1 Utvalget er vårt, ikke bransjens

De 1 807 foretakene er de som har en av ni næringskoder registrert. Et
oppdrettsselskap med feil eller manglende næringskode finnes ikke for
oss. Dekningen mot «alle selskaper i havbruk» er ukjent og ikke målt.

### 5.2 Volumet faller — MÅLT: slettede foretak, ikke vår parse

51 622 → 51 524 over tre uker, 0,19 %. Målt 14.09.2026. **Fallet er
ekte, riktig, og skal ikke rettes.**

#### Råsvaret krymper i takt med snapshotet

Runbookens prosedyre for volumvarsel: krymper råsvaret, har registeret
endret seg; er råsvaret uendret, er det vår parse. Målt mot
`data/arkiv/enhetsregisteret/`:

| dato | råsvar (byte) | enheter i svaret | unike orgnr | snapshot foretak |
|---|---|---|---|---|
| 2026-08-24 | 3 969 755 | 1 857 | 1 810 | 1 810 |
| 2026-08-31 | 3 969 681 | 1 857 | 1 810 | 1 810 |
| 2026-09-07 | 3 965 202 | 1 855 | 1 808 | 1 808 |
| 2026-09-14 | 3 962 238 | 1 854 | 1 807 | 1 807 |

**Unike orgnr i råsvaret er identisk med foretak i snapshotet, hver
eneste uke.** Parsen taper ingenting.

Radregnskapet sier det samme. De 98 radene fordeler seg eksakt:

    rader 24.08                              51 622
      − rader fra 5 foretak som forsvant       −141
      + rader fra 2 nye foretak                 +42
      ± endring blant de 1 805 felles            +1
    rader 14.09                              51 524   ✔

**+1 rad over tre uker fordelt på 1 805 foretak.** Et felt som sluttet å
bli parset ville gitt et tall i hundretallsklassen her.

#### Hvem som forsvinner: slettede aksjeselskaper

Alle fem er `AS`, og alle fem har fått `slettedato` hos Brreg innenfor
vinduet. Slått opp mot `data.brreg.no/enhetsregisteret/api/enheter/`
14.09.2026:

    832072842   slettet 2026-08-25   sto som under_avvikling
    916784430   slettet 2026-09-05
    916586124   slettet 2026-09-07   sto som under_avvikling
    923584609   slettet 2026-09-08   sto som konkurs
    912479943   slettet 2026-09-10   sto som konkurs

Et slettet foretak mister næringskoden sin, og faller derfor ut av
søket. Det er ikke omklassifisering og ikke endret rapportering — det er
sletting etter avvikling eller konkurs.

Changeloggen er enig, uavhengig målt: `data/changelog/enhetsregisteret/`
har for de tre ukene **fem entiteter med 28–29 `borte`-rader hver** —
altså hele entiteten, ikke enkeltfelter. De øvrige `borte`-radene er
enkeltfelter som ble tomme.

#### Og det går begge veier

To nye foretak kom inn i samme vindu, begge med organisasjonsform
**`KBO` — konkursbo**, registrert 27.08 og 08.09.

Det er samme prosess sett fra den andre enden: et selskap går konkurs,
boet registreres som egen enhet med næringskode, og selskapet slettes
etter hvert. **Serien er en fødsels- og dødsprosess, ikke en lekkasje.**

| uke | foretak | ut | inn | netto |
|---|---|---|---|---|
| 2026-08-31 | 1 810 | 1 | 1 | ±0 |
| 2026-09-07 | 1 808 | 2 | 0 | −2 |
| 2026-09-14 | 1 807 | 2 | 1 | −1 |

Brutto omsetning over tre uker: 7 av 1 810 = **0,39 %**, mot netto
0,17 %. Mer enn dobbelt så mye beveger seg som nettotallet viser.

#### Kan trenden ekstrapoleres? NEI

«0,2 % i uka blir 10 % på et år» forutsetter at fallet er ensrettet
drift. Det er det ikke — og serien er uansett for kort til å svare:

* **Fire punkter, tre differanser.** Alt før 24.08 er uforlignbart:
  næringskodelista ble utvidet 17.08 og foretakstallet gikk 938 → 1 810.
  Serien med dagens utvalg begynner 24.08.
* **Radtallet faller monotont** (−6, −58, −34), **men foretakstallet gjør
  det ikke** — 1 810, 1 810, 1 808, 1 807. Én av tre uker er flat.
* Tre negative differanser på rad har sannsynlighet 1/8 under ren støy.
  Det er ikke et signal.

**UBELAGT: om nivået fortsetter å falle.** Det krever flere uker. Det som
måtte måles er om slettingene overstiger nyregistreringene over et år —
og svaret er en egenskap ved bransjen, ikke ved innsamlingen.

#### Luken i målingen — LUKKET fra 14.09.2026, åpen bakover

Rå-arkivet skrives **etter** ENK-filteret (punkt 4). En uke der flere
foretak ble omklassifisert til ENK ser derfor byte for byte ut som en
uke der foretak ble slettet: begge gir færre orgnumre i arkivet, og
begge ser ut som et volumfall.

**Fra 14.09.2026 bærer kroppen antallet selv.** Siste post i arkivfila
er en `meta`-post etter samme mønster som `eierskap` sitt
`personer_fjernet`:

    {"meta": {"antall_filtrert": 201,
              "filtrert_per_form": {"ENK": 201}}}

Bare aggregatet. Ingen organisasjonsnumre, ingen navn, ingen markør på
en enkeltenhet — et ENK ER innehaveren (regel 3), så en rad som sa «her
sto en fysisk person» ville vært nøyaktig den opplysningen filteret
finnes for å unngå.

Dermed kan et snapshot fra og med denne datoen alene svare på om et fall
kom av sletting eller av omklassifisering: falt orgnr-tallet mens
`antall_filtrert` steg tilsvarende, er foretakene fortsatt der og bare
flyttet over på den andre siden av filteret. Det er prøven i regel 1b-3,
og svaret var nei fram til nå.

**Luken står åpen for de tre ukene som allerede er målt.**
Arkivfilene for **24.08, 31.08, 07.09 og 14.09** har ingen `meta`-post og
får den aldri — append-only, regel 2. For dem finnes tallet ikke, og det
kan ikke rekonstrueres: et gammelt arkiv er allerede filtrert, og hvem
som ble filtrert bort er ikke bevart noe sted.

At fallet 24.08–14.09 likevel er MÅLT, skyldes en omvei som ikke er
tilgjengelig i sin alminnelighet: alle fem avgangene ble slått opp hos
Brreg i ettertid og hadde `slettedato`. Det virket fordi avgangene var
fem og fordi Brreg fortsatt svarer på slettede orgnumre. Ved tjue
avganger, eller for et register som ikke svarer på slettede enheter,
ville spørsmålet vært ubesvarlig.

Det er grunnen til at luken ble lukket nå og ikke ved neste fall:
tiltaket virker bare framover, og hver uke som går uten det er en uke
som aldri kan besvares.

### 5.3 Pagineringstaket merkes ikke i dataene

Avkortning ved taket gir en advarsel i loggen, ikke et merke på raden.
Det er et kjent brudd på 1b-3, med vitende og vilje. Se beslutningen fra
24.08.2026.

### 5.4 `PERSONFORMER` virker ved LESING

Lista i `core/persondata.py` brukes også i `parse()`, så en endring i den
endrer hva et gammelt snapshot inneholder ved re-parse. Også et kjent
1b-3-brudd, også med vitende og vilje.

Utvidelsen 16.09.2026 er den første gangen bruddet har fått en virkning:
snapshotene fra 17.08 til 14.09 leser fra da av uten sine 64 DA/ANS/PRE,
uten at noe i fila sier at de var der. `publiseringsvakt.py --rapport`
skriver tallet ved hver kjøring, og `analyse/kjoringslogg.py` fører både
`personformer` og `personsektorer` — men et gammelt RESULTAT vet fortsatt
ikke hvilken liste det ble regnet ut under. Se
`docs/FORSLAG-personformer-versjonering.md`.

## 6. Frekvens

Ukentlig, `min_dager_mellom = 7`. **Ingen etterslep** — registeret sier
hva som gjelder NÅ.

Registeret oppdateres i praksis daglig, men endringene som betyr noe —
kapasitet, eierskap, konkurs — beveger seg på måneders skala. Daglig ville
gitt 52 ganger mer data uten 52 ganger mer signal. Se
`docs/beslutninger/2026-08-16-ukentlig-innsamling.md`.

## 7. Lisens og attribusjon

**NLOD 2.0.** Fra
`brreg.no/bruk-av-data-fra-bronnoysundregistrene/apne-data/`, lest
14.09.2026:

> «Datasettene følger Norsk lisens for åpne data (NLOD). Det er ikke
> nødvendig å registrere seg for å ta datasettet i bruk.»

API-dokumentasjonen fester versjonen til NLOD 2.0 og lenker til
lisensteksten på `data.norge.no/nlod/no/2.0`.

**Brreg oppgir ingen egen attribusjonsform**, til forskjell fra
Fiskeridirektoratet. Da gjelder NLOD 2.0 punkt 5:

> «Hvis lisensgiver ikke spesifiserer hvordan navngivelse bør foretas,
> skal lisenstaker normalt oppgi følgende: "Inneholder data under Norsk
> lisens for offentlige data (NLOD) tilgjengeliggjort av [navnet på
> lisensgiver]".»

Setningen vår blir dermed:

> **«Inneholder data under Norsk lisens for offentlige data (NLOD)
> tilgjengeliggjort av Brønnøysundregistrene»**

NLOD 2.0 bruker ikke ordet «kommersiell». Retten følger av at lisensen er
«ikke-eksklusiv, vederlagsfri og uten tidsmessige eller geografiske
begrensninger» — ingen begrensning, ikke en uttrykkelig tillatelse.

**Lisensen gjelder det FRIE nivået.** Se punkt 3 og `docs/LISENSKJEDE.md`
merknad B.

Attribusjonen kan stå på en «Om»-side så lenge den ikke er «bortgjemt,
eller vanskelig å finne». Blandes dataene med BarentsWatch-kilder i samme
visning, gjelder deres strengere krav om synlighet for sluttbruker.
