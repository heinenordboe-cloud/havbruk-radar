---
dato: 2026-09-09
tittel: HIs 28 reguleringsområder hentes som kilde — grensetallene arkiveres uten å bli det
status: utkast
commit: [fylles inn]
---

## Hva som ble bestemt

HIs forslag om å dele de 13 produksjonsområdene i **28
reguleringsområder** hentes som en KILDE med vanlig kildekontrakt:
`sources/reguleringsomraader.py`, rå-arkiv før parse, `published_at`
lest av kroppen. Ett snapshot, `observed_at = 2026-06-29`, 28 entiteter,
224 rader.

Kilden henter **begge framstillingene** — geojson-fila hos NMDC og
WKT-en i rapportens appendiks 7.1 — og sammenligner dem. Geojson lagres;
appendikset er kontrollen.

Hver rad bærer **`status = "forslag"`**.

Rapportene **2026-36** og **2026-37**, som inneholder selve
grensetallene, hentes og arkiveres i samme kropp, men blir **aldri
observasjoner**.

Tilordningen av lokaliteter til områder er en ANALYSE
(`analyse/reguleringsomraader.py`), ikke en kilde. Se
docs/ANALYSE-REGULERINGSOMRAADER.md.

## Hvorfor en kilde og ikke en engangsfil

Fordi det er BEVEGELSEN som er interessant, ikke polygonet.

Et forslag til NFD kan bli vedtatt, endret eller forkastet. Blir det
vedtatt, går `status` fra `forslag` til noe annet, og da ligger begge
tilstandene i historikken med hver sin `observed_at`. Blir det endret,
er de nye grensene en endringsrad ved siden av de gamle. Blir det
forkastet, står 2026-06-29-snapshotet igjen som det eneste stedet
forslaget finnes i den formen det hadde.

En engangsfil kan svare på hvordan grensene ser ut nå. Den kan ikke
svare på hva som ble foreslått og hva som ble vedtatt, og det er den
forskjellen hele prosjektet hviler på. CLAUDE.md regel 5: snapshotet fra
en gitt dato lar seg ikke hente i etterkant.

Og det er ikke en teoretisk risiko. Datasettet heter allerede
`regomr_v3` i sitt eget lagnavn. Det har vært to versjoner før denne.

## `status = "forslag"` er en 1b-3-verdi

Regel 1b-3: en verdi som avgjør hva dataene BETYR, lagres SAMMEN med
dem.

En grense som er et råd og en grense som er forskrift er identiske som
polygoner. Ingenting i geometrien, i navnet eller i koordinatene skiller
dem. Lå `forslag` bare i `config.yml`, i denne fila eller i git, kunne
et snapshot fortelle hvor grensene GÅR, men ikke hva de ER — og da kan
ingen sammenligning av to snapshots skille «HI flyttet en strek i
forslaget sitt» fra «departementet vedtok noe annet enn det HI foreslo».

Prøven fra 1b-3 stilt på dette feltet: **kan et snapshot alene svare på
hva denne verdien var da raden ble skrevet?** Uten feltet: nei. Derfor
står det på raden, sammen med `datasett_versjon` og
`geometri_bekreftet`, som er der av samme grunn.

Det er samme feilmodus som F9 (`utvalg`): en innstilling som avgjør hva
dataene betyr, lagret et sted som skrives om.

## Hvorfor 2026-36 og 2026-37 arkiveres uten å bli kilde

De inneholder grensetallene — akseptabelt utslippsnivå per område i
millioner voksne hunnlus. Det er tallene alt dette til slutt handler om,
og de blir likevel ikke en kilde. Tre grunner, i rekkefølge:

1. **Det er ikke ett tall.** 2026-37 tabell 3 oppgir antall voksne
   hunnlus beregnet med **tre ulike metoder** (skalering av historisk
   lusepress, og to til), for **to modeller** (ROC og VPS), for både PO
   og RO. 2026-36 tabell 1 og 2 oppgir akseptabelt lusenivå som et
   **intervall** — høyeste og laveste verdi over 2022–2025 — og tabell 3
   som median med 25- og 75-persentil. En kilde måtte valgt metode,
   modell og punktestimat på HIs vegne, og det valget er
   departementets, ikke vårt.

2. **Det er et råd, ikke en grense.** Ingen vet hvilken form det som
   eventuelt vedtas får: om det blir ett tall per område, et intervall,
   en formel, eller om grensetallene forsvinner til fordel for noe helt
   annet. En kilde bygget på rådets form måtte rives den dagen
   forskriften kom, og da ville historikken bestått av én kilde som
   aldri fikk et andre snapshot.

3. **Å arkivere kroppen koster ingenting og bevarer utgangspunktet.**
   Regel 1b-5 punkt 2: behold hele svaret i arkivet, ikke bare skiven du
   skriver. Blir grensetallene en kilde senere, er kroppen der å
   re-parse, med `raw_hash` og `published_at` på plass.

De hentes i `reguleringsomraader.fetch()` og ikke av et eget skript, med
vilje: da får de proveniens gjennom det vanlige maskineriet, uten en
linje ny kode i `core/`. De er samme bestilling, samme dato og samme
forfattermiljø som 2026-28, og 2026-37 tabell 1 og 3 er oppgitt **per
reguleringsområde** — de er den samme leveransen.

En hi.no-side som er nede feller ikke kilden: feilteksten arkiveres i
stedet for kroppen. Rangeringen er bevisst — 2026-28 bærer radene som
skrives, disse to skal bare ikke gå tapt.

## Hva som ble målt, og som ikke er åpenbart av koden

**De to framstillingene er identiske.** Alle 28 polygonene stemmer
hjørne for hjørne mellom geojson og appendiks, når to FORMATforskjeller
er regnet inn: WKT-en er avrundet til fem desimaler, og den gjentar
sluttpunktet én gang for mye (28 av 28 — altså formatet, ikke en feil).
Null avvik etter det. Kontrollen står på hver rad som
`geometri_bekreftet`, ikke bare i en logglinje.

**NMDC-verten er målt for første gang.** `ftp.nmdc.no` er
`Apache/2.4.6 (CentOS)` og svarer `Last-Modified: Fri, 28 Aug 2026
05:00:09 GMT`. Det er **to måneder etter** at rapporten ble utgitt.
Headeren brukes derfor ikke som `published_at` — den sier når fila sist
ble skrevet på den serveren, ikke når HI utga grensene. Verdien er
bevart i arkivkroppen som `geojson_last_modified`. Om de to månedene er
en re-opplasting av samme innhold eller en stille revisjon, er **ikke
fastslått**.

Det er den tredje verten som bekrefter kandidat 1 i
`docs/REVISJON-2026-09-09.md`: `Last-Modified` er en kandidat, ikke en
kilde. hi.no sender den ikke i det hele tatt for disse tre sidene.

**`published_at` leses av rapportens egen «Publisert:»-blokk** og er en
ren ISO-DATO uten klokkeslett, fordi det er en dato kilden oppgir. Å
skrive `T00:00:00+00:00` ville vært å finne på et klokkeslett ingen har
oppgitt. `publisert_i` er ført inn i `SKRIVERE_AV_PUBLISHED_AT` i
`tests/test_tidssoner.py` med tre oppførselstester, slik den testen selv
krever.

**Koordinatrekkefølgen er verifisert, ikke antatt**, med to uavhengige
prøver: verdiområdet (71 °Ø er Ural) og en kjent posisjon (Ålesund havn
faller i 5A; det samme punktet snudd faller utenfor alt). Den tredje
prøven er analysens: 969 av 969 lokaliteter med produksjonsområdekode
havner i et reguleringsområde med samme tall. Null avvik.

**Det ene som IKKE stemmer** er HIs egen påstand om at 1A og 12D hadde
null anlegg med produksjon i utvandringsperioden 2022–2025. 13A er
faktisk tomt. 1A har to sjøanlegg og 12D fire, med til sammen 23 025
tonn MTB i Laksefjord, alle med laksefisk rapportert i hver eneste
utvandringsperiode. Hvorfor HI oppgir null er ikke fastslått og skal
ikke gjettes — se docs/ANALYSE-REGULERINGSOMRAADER.md punkt 4.

## Hva kilden NEKTER å gjøre

`gjelder_for()` velger datoen, kroppen bekrefter den. `parse()` kaster
`Nyutgivelse` hvis rapporten oppgir en annen utgivelsesdato enn
`UTGITT`, hvis geojson-laget heter noe annet enn `regomr_v3`, eller hvis
navnene ikke er de 28 kjente. Kroppen er arkivert av kjernen før
`parse()` kalles, så et slikt stopp koster en re-parse og ikke
historikk.

Den kaster `Formatfeil` hvis et polygon har hull eller flere ringer — et
hull som ties i hjel gjør punkt-i-polygon USANT, ikke unøyaktig — og
hvis tallet i et områdenavn er uenig med `prodomr`-egenskapen i samme
feature.

## Hva som ville snudd dette

- **NFD vedtar en annen inndeling enn HIs forslag.** Da er
  2026-06-29-snapshotet fortsatt riktig som et bilde av forslaget, men
  kilden må hente vedtaket i stedet — sannsynligvis fra en forskrift på
  lovdata, altså med samme form som `trafikklysvedtak`. `status` blir da
  det feltet som skiller de to seriene.
- **HI publiserer en revidert versjon.** `regomr_v4` feller `parse()`
  med vilje. Da er avgjørelsen om den nye versjonen skal skrives som en
  ny `observed_at` ved siden av v3, eller om v3 var feil hele tiden — og
  det er ikke en avgjørelse kilden skal ta.
- **Produksjonsområdeforskriften erstattes helt.** Da er
  `produksjonsomraade`-feltet, som er utledet av navnet, ikke lenger en
  peker til noe som finnes. Feltet blir da historikk og ikke en nøkkel,
  og krysskontrollen i punkt 3 av analysen kan ikke kjøres på nytt.
- **Grensetallene vedtas i en form som gjør dem til en kilde** — ett
  tall eller ett intervall per område, fastsatt, uten valg mellom tre
  beregningsmetoder. Da er kroppene allerede i arkivet, og det er en
  re-parse og ikke en ny innsamling. Det er hele grunnen til at de ble
  arkivert.
- **Sammenligningen slutter å stemme.** Er geojson og appendiks uenige
  ved en senere henting, er det et funn og ikke noe å utligne.
  `geometri_bekreftet` bærer det på raden.
