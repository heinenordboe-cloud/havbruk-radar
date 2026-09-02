---
dato: 2026-09-02
tittel: Eierskapshistorikken hentes, og journalDate blir stående som «senest da»
status: gjeldende
commit: 8e64e13
---

## Hva som ble bestemt

Eierskapshistorikken backfilles fra `/licenses/{nr}/transfers`, ett kall
per tillatelse, med **ett snapshot per år** — `observed_at` er 31.12 i
journalføringsåret, og den eksakte datoen står i `journal_dato` på hver
rad. Samme mønster som de 106 månedlige biomasse-snapshotene: en
overføring hører til tidspunktet den skjedde, ikke til dagen vi hentet
den.

Historikken skrives til en **egen kilde**, `eierskap_historikk`, ikke inn
i den ukentlige `eierskap`-serien.

## journalDate — avklaringen, gjort FØR de 3029 kallene

### Det er den eneste datoen som finnes

Et overføringselement har nøyaktig fire felter. Målt over 45 overføringer
i 60 tillatelser, uten et eneste avvik:

    identityNr    organisasjonsnummer til MOTTAKER
    journalDate   journalføringsdato
    journalNr     saksnummer, «2022000164»
    officialName  mottakerens navn

Det finnes **ingen `validFrom`, ingen overdragelsesdato og ingen
avgiver**. Responsen har i tillegg en `ajourDate` på toppnivå, men den
varierte mellom 2026-08-31, 09-01 og 09-02 i samme uttrekk — den er
tjenestens «à jour per», altså deres hentetidspunkt, ikke en
utgivelsesdato for overføringen. Den brukes ikke. Samme skille som
Waybacks `Memento-Datetime` mot `X-Archive-Orig-Last-Modified` i 1b-7.

### Fiskeridirektoratet dokumenterer den ikke

`/pub-aqua/` serverer et Swagger UI-skall, men hver eneste spec-adresse
svarer 404: `/v3/api-docs`, `/api-docs`, `/openapi.json`,
`/swagger-config`, `/swagger-initializer.js`, `/v2/api-docs`.
API-katalogen på `api.fiskeridir.no/catalog/` er en SPA hvis
JavaScript-bundle ikke inneholder én eneste API-sti — bare `/catalog`
seg selv.

**Ingen offentlig kilde vi kan nå forklarer hva journalDate betyr.**

### Krysspeiling mot vår egen changelog er prøvd, og virker ikke

Hypotesen var at et eierskifte som endrer tillatelsestilknytning ville
gitt en dato i vår egen changelog. Den ble testet.

Vi har tre akvakultur-snapshots (17., 24. og 31.08.2026) og 11 endringer
i feltet `tillatelser`, alle i vinduet 24.–31.08. Ni distinkte
tillatelser flyttet mellom lokaliteter. **Ingen av de ni har en
overføring i det vinduet.** Den ene som overhodet har overføringer,
M-MD-0003, har sin nyeste 2026-04-29 — fire måneder tidligere.

Konklusjonen er et funn i seg selv: **tilknytningsendring og eierskifte
er to ULIKE hendelser.** Changeloggen vår ser at en tillatelse flytter
mellom lokaliteter; `transfers` ser at den skifter eier. De sammenfaller
ikke, og den ene kan derfor ikke datere den andre.

### Det som derimot lot seg måle: serien er internt konsistent

På 120 tilfeldige tillatelser:

| kontroll | resultat |
|---|---|
| journalDate kronologisk sortert | **120 / 120** |
| ingen overføring før `grantedTime` | **120 / 120** |
| siste overføring == dagens eier | 61 / 62 |
| uten overføringer: dagens eier == opprinnelig tildelt | 57 / 58 |

Kjeden er altså ekte og fullstendig nok til å bære en tidsserie. De to
avvikene (HE-R-1503 skiftet eier uten registrert overføring) sier at
`transfers` har små hull — omtrent 1,7 % — og det skal ikke skjules.

### Beslutningen

**journalDate brukes som tidsakse, med forbeholdet båret PÅ HVER RAD.**

Feltet `dato_forbehold` står på hver eneste overføringsrad, ikke bare i
kjøringsloggen — samme krav og samme begrunnelse som
`aggregering = "baer_maaned"` i kildeledd (regel 1b-3). Ordlyden sier at
datoen skal leses som **«senest da»**, ikke «akkurat da»: den faktiske
overdragelsen kan ligge foran journalføringen.

Alternativet — å utsette til datoen er avklart — ble forkastet. Regel 5
gjelder: endepunktet kan forsvinne, og en tidsserie med et dokumentert
forbehold er uendelig mye mer verdt enn ingen tidsserie. Forbeholdet kan
fjernes senere hvis Fiskeridirektoratet dokumenterer feltet; dataene kan
ikke hentes senere hvis endepunktet forsvinner.

## Personvernfilteret er GJENBRUKT, ikke kopiert

`parse_overforinger()` kaller `_tillat()` — den samme funksjonen den
ukentlige kilden bruker. Det er ikke en detalj: to filtre som skal si det
samme, men er skrevet hver for seg, er nøyaktig formen F6, F7 og F8
hadde. De holder helt til den ene endres.

Funksjonen var gjenbrukbar som den sto. Det eneste som måtte bygges nytt
er OPPSLAGET den trenger: `transfers` oppgir bare `identityNr`, ikke
entitets-ID-en, så `eiertyper()` bygger et kart fra organisasjonsnummer
til selskapstype. Personer er allerede borte når kartet er ferdig.

De tre vilkårene er uendret fra forrige økt:

1. **Typen må være kjent.** En mottaker som ikke finnes i kartet har
   ukjent type, og blir stoppet.
2. **Typen må ikke være en personform.** `Person` og
   `SoleProprietorship` — ENK er innehaveren, og har ni siffer.
3. **Nummeret må være ni siffer.** Andre lås, ikke hovedregelen.

### «Vet ikke» koster her, og prisen betales med åpne øyne

I den ukentlige kilden kostet vilkår 1 ingenting: alle 536 eier-ID-er
fantes i `/entities`. I historikken er det annerledes. En mottaker fra
2006 kan være oppløst for lengst og finnes ikke i dagens entitetsregister
— og da stoppes overføringen selv om mottakeren var et aksjeselskap.

Det er en reell kostnad i tapt historikk, og den er akseptert bevisst.
Regelen står fast: **«vet ikke» kan aldri bety «slipp gjennom» i et
personvernfilter.** Kostnaden ved å ta feil den andre veien er et
personregister i en append-only historikk, og det kan ikke rettes.

Tallet rapporteres i «Hva som faktisk kom ut» nedenfor, slik at prisen
er synlig og kan revurderes hvis noen finner en kilde til historiske
selskapstyper.

## Hvorfor egen kilde og ikke samme serie

`eierskap_historikk` skriver til sin egen snapshot-mappe. Blandet man dem
inn i `eierskap`, ville feltvakten sett nitten felter forsvinne og seks
nye dukke opp mellom to snapshots av «samme» kilde — F10s mønster
nøyaktig. Kadensen er også en annen: den ukentlige serien er én rad per
tillatelse per uke, historikken er én rad per overføring per år.

Ingen endring i `core/` var nødvendig. `snapshot.write()` grupperer på
`source` og skriver til `RAW_DIR/{source}`, så en kilde kan skrive under
et annet navn enn sitt eget uten at kjernen vet om det — og
personvernvakten i `write()` gjelder like fullt, per gruppe.

## Backfillen: fremdrift og idempotens er samme mekanisme

Arkivfila **er** fremdriftsloggen. Hver tillatelse arkiveres under sitt
eget nummer i `data/arkiv/eierskap-overforinger/`, og en tillatelse som
allerede har en fil hoppes over uten et kall. Et avbrudd etter 2000 kall
koster 1029 kall å gjenoppta, ikke 3029.

`raw.arkiver_ny()` brukes **ikke**. Den hasher hele arkivmappa ved hvert
kall for å finne duplikater, og med 3029 filer er det O(n²) — dens egen
docstring sier at den er for arkiver med «titalls filer, ikke titusener».
Her holder det å spørre om fila finnes.

Pausen mellom kall er 0,5 sekunder. Den er ikke målt mot en rate limit —
vi har ikke sett noen — den er valgt for å være åpenbart høflig mot en
offentlig etat. Hele backfillen tar da omtrent 25 minutter.

Feiler noen kall, skrives **ingen** snapshots. Et ufullstendig grunnlag
ville gitt årssnapshots som ser komplette ut, og et hull ville sett ut som
et år uten overføringer. Kjøringen sier fra og ber om en gjenkjøring.

## Hva som ville snudd det

- **Fiskeridirektoratet dokumenterer journalDate**, eller legger til et
  eget overdragelsesfelt. Da kan `dato_forbehold` fjernes — men bare fra
  nye rader; de gamle beholder sitt, for de ble skrevet under en annen
  kunnskap.
- **En kilde til historiske selskapsformer.** Da kan vilkår 1 slås opp
  mot et register som også kjenner oppløste selskaper, og overføringene
  som i dag stoppes på ukjent type kan hentes inn.
- **Endepunktet forsvinner.** Da er arkivet i `data/arkiv/` det eneste
  som finnes, og det er hele grunnen til at kroppene arkiveres rått før
  parse.

## Hva som faktisk kom ut

    arkiverte kropper        3029   (én per tillatelse, 0 feil)
    overføringer i rådata    2628   2006-2026
    beholdt etter filter     1934   (73,6 %)
    fjernet                   694   (26,4 %)
    årssnapshots               21
    observasjoner           15472

Per år, rådata: 2006:84, 2007:245, 2008:111, 2009:50, 2010:31, 2011:31,
2012:42, 2013:87, 2014:80, 2015:75, 2016:44, 2017:20, 2018:73,
**2019:328**, 2020:67, 2021:39, **2022:728**, 2023:121, 2024:135,
2025:146, 2026:91.

To år dominerer, og begge er kjente omstruktureringer: 2019 (Marine
Harvest → Mowi) og 2022 (konsernintern omorganisering).

### Dekning

    tillatelser MED overføringer     1496
    tillatelser UTEN                 1533   (50,6 %)

Halvparten av tillatelsene har aldri skiftet eier. Det er **dekning, ikke
feil**: 57 av 58 kontrollerte tillatelser uten overføringer har fortsatt
sin opprinnelige tildelte som eier.

    unike mottakere i rådata          335
    unike mottakere etter filter      225

### Hvor langt bakover rekker koblingen til lokalitet

    overføringer på tillatelse med kjent lokalitet   2541
    overføringer på tillatelse uten aktiv lokalitet    87
    overføringer der lokaliteten er ukjent for oss      0
    distinkte tillatelser uten lokalitetskobling       48

**Null overføringer peker på en lokalitet vi ikke kjenner.** Det var
spørsmålet verdt å stille, og svaret er godt: alle tillatelser som i dag
har en aktiv lokalitet, har en lokalitet vi har i
akvakulturregisteret. De 87 overføringene på 48 tillatelser henger på
tillatelser uten *aktiv* lokalitetskobling i dag — nedlagte anlegg eller
tillatelser i ventestilling.

Merk hva dette IKKE sier: koblingen lokalitet → selskap rekker bakover
bare så langt vår egen akvakultur-serie gjør det, og den har tre
snapshots (17., 24., 31.08.2026). Overføringene rekker til 2006, men
LOKALITETStilknytningen er dagens. En tillatelse som lå på en annen
lokalitet i 2012 vil bli tilskrevet dagens lokalitet. Det er en kjent
grense og skal oppgis sammen med enhver analyse som kobler de to.

## Prisen for «vet ikke betyr stopp», og den er høy

Av de 694 fjernede overføringene:

    677   ukjent selskapstype (mottaker ikke i dagens /entities)
     17   tomt identityNr (privatperson)

**De 677 er ikke personer. De er selskaper som ikke finnes lenger.**

De 110 distinkte ukjente mottakerne er nesten uten unntak
aksjeselskaper — 106 av 110 har selskapsendelse — og de mest frekvente
er selve konsolideringshistorien:

    182x  MOWI NORWAY AS            16x  PAN FISH NORWAY AS
     43x  CERMAQ FINNMARK FARMING   15x  AQUA FARMS AS
     25x  SALMAR FINNMARK AS        12x  MARINE HARVEST LABRUS AS

Dette er ubehagelig, og det skal stå ubehagelig: **filteret fjerner
fortrinnsvis de oppkjøpte selskapene, altså nøyaktig de hendelsene
serien finnes for å dokumentere.** Et selskap som ble fusjonert inn i et
større er borte fra dagens entitetsregister, og da kan vi ikke slå opp
typen.

Regelen står likevel. `Person` og `SoleProprietorship` har også tomt
eller nisifret nummer, og uten typen kan vi ikke skille dem fra et
oppløst AS. Å slippe gjennom på «navnet slutter på AS» er den samme
syntaktiske prøven på et semantisk spørsmål som `core/persondata.py`
uttrykkelig advarer mot: «å filtrere PÅ NAVNET er nøyaktig samme feil som
ni-siffer-testen fra 16.08».

### Hvor mye kan gjenvinnes, og hvordan

Målt mot vårt eget enhetsregister-snapshot:

    ukjente mottakere                     110   (677 overføringer)
    finnes i VÅRT enhetsregister           14   ( 57 overføringer)  alle AS
    finnes ingen steder hos oss            96   (620 overføringer)

Et oppslag mot vår egen enhetsregisterkilde gjenvinner altså bare 57 av
677. De øvrige 96 selskapene er ikke i vårt næringskodeutvalg — mange er
oppløst før utvalget ble satt.

**Den ekte veien er et Brreg-oppslag på organisasjonsform for historiske
organisasjonsnumre.** Brreg beholder oppløste enheter. Det er en ny
kilde eller en ny oppslagsfunksjon, og det er en egen beslutning — ikke
noe som skal snikes inn i denne backfillen. Til den er tatt, er serien
komplett for 73,6 % av overføringene og har et dokumentert, målt hull på
resten.

## En feil i `core/diff.py` som denne kilden avdekket

Skrivefasen krasjet første gang, og årsaken lå ikke i kilden:

    ComputeError: could not append value: "journalDate er
    JOURNALFØRINGSDATO…" of type: str to the builder

`diff.compare()` bygget rammen med `pl.DataFrame(changes)`, altså med
polars' standard `infer_schema_length=100`. Er de 100 første radene
«ny», er `old_value` `None` i alle sammen, kolonnen utledes som `Null`,
og den første «borte»-raden med en streng feller hele byggingen.

Feilen er **latent siden changeloggen ble skrevet**, og har aldri fyrt
fordi hver eksisterende kilde blander ny, endret og borte innenfor de
første hundre radene. `eierskap_historikk` gjør ikke det: to nabosnapshots
deler ingen entiteter i det hele tatt, så alle «ny» kommer først.

Rettet på begge stedene (`compare` og `revisjon_mellom`) med
`infer_schema_length=None`. Dette er en endring i `core/`, og den er
gjort med åpne øyne: den utvider ikke kontrakten og legger ikke til noe
for denne kildens skyld — den retter en defekt som gir krasj for
kontraktsriktige data fra en hvilken som helst kilde. Regresjonstest i
`tests/test_revisjon.py`, verifisert til å feile uten rettelsen.

Hadde kilden i stedet sluttet å skrive `dato_forbehold` for å komme
utenom, ville feilen ligget der til neste gang — og den neste ville
truffet den uten å vite hvorfor.
