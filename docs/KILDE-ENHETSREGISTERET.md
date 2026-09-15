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

**`10.209` er IKKE i bruk.** Den sto i en tidligere liste og ble tatt ut
17.08.2026 samtidig som `03.222` og `10.203` kom inn. Et notat utenfor
repoet lister seks koder med `10.209` blant dem; den listen er feil på to
måter — feil kode med, og tre koder manglende.

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
kjøring.**

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

## 4. Enkeltpersonforetak filtreres bort — 201 per kjøring

**Målt 14.09.2026 ved å kjøre kildens egen `fetch()`:**

    201 foretak filtrert bort som fysisk person (ENK 201)

Alle 201 er organisasjonsformen `ENK`. Et notat utenfor repoet oppgir
203; målingen er 201.

**Hvorfor det må gjøres.** Et ENK er ikke et eget rettssubjekt —
foretaket ER innehaveren. Selv uten gateadressen er navn, kommune,
postnummer, næring og konkursflagg opplysninger om en identifiserbar
fysisk person, og omtrent tjue av dem bærer innehaverens navn som
foretaksnavn.

**To lag, med hver sin grunn:**

1. **I `fetch()`, før noe arkiveres.** Rå-arkivet lagrer hele API-svaret,
   og der lå gateadressen til hvert eneste ENK. Feltvalget gjelder bare
   snapshotet, ikke arkivet. Data som aldri hentes inn kan ikke lekke.
2. **I `parse()`**, fordi arkivfiler fra før 22.08.2026 fortsatt
   inneholder dem. En re-parse av et gammelt arkiv skal ikke føre dem
   inn igjen.

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

Tallet skrives til kjøringsloggen fordi filtreringen er stille av natur:
en enhet som aldri blir en observasjon etterlater seg ingen rad å savne,
og et hopp fra 201 til 900 ville ellers bety at søket har endret seg uten
at noe sa fra.

## 5. Forbehold

### 5.1 Utvalget er vårt, ikke bransjens

De 1 807 foretakene er de som har en av ni næringskoder registrert. Et
oppdrettsselskap med feil eller manglende næringskode finnes ikke for
oss. Dekningen mot «alle selskaper i havbruk» er ukjent og ikke målt.

### 5.2 Volumet faller, og årsaken er ikke målt

51 622 → 51 524 over tre uker. Om det er avviklinger, omklassifiseringer
eller endret rapportering hos Brreg er **ikke** undersøkt. Volumvakten
måler mot et høyvannsmerke og har ikke fyrt.

### 5.3 Pagineringstaket merkes ikke i dataene

Avkortning ved taket gir en advarsel i loggen, ikke et merke på raden.
Det er et kjent brudd på 1b-3, med vitende og vilje. Se beslutningen fra
24.08.2026.

### 5.4 `PERSONFORMER` virker ved LESING

Lista i `core/persondata.py` brukes også i `parse()`, så en endring i den
endrer hva et gammelt snapshot inneholder ved re-parse. Også et kjent
1b-3-brudd, også med vitende og vilje.

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
