# Akvakulturregisteret — kildespesifikasjon

Alt i dette notatet er **målt** mot snapshotene i `data/raw/akvakultur/`
og rå-kroppene i `data/arkiv/akvakultur/` 14.09.2026. Der noe bare er
lest og ikke verifisert, står det uttrykkelig.

**Kilde: Fiskeridirektoratet.** NLOD, og attribusjonen er et vilkår —
se punkt 7.

Kildefila heter `sources/akvakultur.py`, og kildens `name` er
`akvakultur`. Det er navnet som står i snapshots og commit-meldinger.

---

## 1. Endepunktet

    https://api.fiskeridir.no/pub-aqua/api/v1/sites

Åpent, ingen nøkkel, ingen registrering.

**`range` er et INKLUSIVT intervall, ikke side/størrelse.** `0-99` gir de
hundre første. Fallgruven er at et spenn over 100 ikke gir feilmelding —
det gir stille ÉN rad. `range=0-999` returnerte 1 lokalitet, ikke 1000.
Uoppdaget ville det betydd én lokalitet i uka i historikken, synlig først
den dagen noen prøvde å bruke dataene. Derfor er spennet en konstant, og
derfor sjekker `fetch()` at et fullt kall faktisk gir fulle sider.

**`entity_id` er `siteNr`, ikke `siteId`.** Lokalitetsnummeret næringa
bruker, lesbart i en diff, og mulig å slå opp hos Fiskeridirektoratet.
`siteId` er en intern nøkkel, og `versionId` endres ved hver versjonering
— begge er dårlige ankere for en historikk mennesker skal lese.

## 2. Volum per kjøring

Målt over alle snapshots på disk. Duplikater med løpenummer er utelatt.

| dato | rader | lokaliteter | felter |
|---|---|---|---|
| 2026-08-17 | 48 236 | 1 779 | 29 |
| 2026-08-24 | 48 236 | 1 779 | 29 |
| 2026-08-31 | 48 235 | 1 779 | 29 |
| 2026-09-07 | 48 235 | 1 779 | 29 |
| 2026-09-14 | **48 310** | **1 782** | 29 |

Størrelsesorden: **ca. 48 300 observasjoner og ca. 1 780 lokaliteter per
kjøring.** Feltantallet har ikke beveget seg.

## 3. Feltene, og hva de dekker

29 felter. Kolonnen er antall lokaliteter feltet faktisk har en verdi
for, målt 14.09.2026 mot 1 782 lokaliteter.

| felt | lokaliteter | dekning |
|---|---|---|
| `navn`, `kommune`, `kommunenummer`, `fylke`, `fylkesnummer` | 1 782 | 100 % |
| `breddegrad`, `lengdegrad` | 1 782 | 100 % |
| `kapasitet`, `kapasitet_enhet`, `kapasitet_midlertidig` | 1 782 | 100 % |
| `arter`, `artsbegrensninger_antall` | 1 782 | 100 % |
| `plasseringstype`, `klareringstype`, `vanntype` | 1 782 | 100 % |
| `er_slakteri`, `har_samlokalisering`, `har_samdrift` | 1 782 | 100 % |
| `har_kommersiell_aktivitet`, `forste_klarering` | 1 782 | 100 % |
| `versjon_status`, `versjon_aarsak`, `versjon_gyldig_fra` | 1 782 | 100 % |
| `tillatelser_antall` | 1 782 | 100 % |
| `tillatelser` | 1 779 | 99,8 % |
| **`prodomraade_kode` / `-navn` / `-status`** | **969** | **54,4 %** |
| **`tillatelser_trukket`** | **856** | **48,0 %** |

24 av 29 felter står på hver eneste lokalitet. Et felt uten verdi hoppes
over framfor å skrives som tom — derfor varierer observasjonstallet per
felt, og **det er ikke datatap.**

### Det høyest verdsatte feltet

`prodomraade_status` er trafikklyset — rød, gul eller grønn — som styrer
om aktører i området kan vokse. Et forvaltningsvedtak med direkte
økonomisk konsekvens, og det finnes ingen historisk serie over det noe
annet sted. Se `docs/KILDE-TRAFIKKLYSVEDTAK.md` for vedtakssiden.

## 4. Forbehold

### 4.1 Produksjonsområde finnes for litt over halvparten

`prodomraade_*` dekker **969 av 1 782 (54,4 %)**. Landbaserte anlegg og
ferskvannslokaliteter har ikke produksjonsområde, og det er ikke et hull
— det er hva registeret er.

Men det betyr at **enhver PO-aggregering utelater 46 % av lokalitetene**,
og de er ikke tilfeldig fordelt. Tallet skal stå ved siden av hver
analyse som summerer per produksjonsområde.

### 4.2 Tallene beveger seg, og notatet daterer seg

Dekningen er ikke konstant. Målt over serien:

    17.–24.08.2026    prodomraade 970    trukne 853    tillatelser 1777
    31.08.–14.09      prodomraade 969    trukne 856    tillatelser 1776–1779

Et notat utenfor repoet oppga 970 og 853 med 1 779 lokaliteter. **Det var
riktig da det ble skrevet** — det er tallene for 17.–24.08 — og er nå
utdatert med én, tre og tre. Det er grunn til å måle mot dataene og ikke
mot et notat, og grunn til at denne tabellen har datoer.

### 4.3 Kilden gir IKKE innehaver

Verifisert mot rå-kroppen 14.09.2026: ingen av de **28 toppnivånøklene** i
`/sites` inneholder organisasjonsnummer eller innehaver. Søk i hele
kroppen ga **0 treff** på `organisasjonsnummer`, `orgNr`,
`organizationNumber`, `identityNr`, `owner`, `holder` og `legalEntity`,
og **0 ni-sifrede tall** som begynner på 9.

`connections` har bare `licenseNr`, `siteNr`, datoer og status.

Koblingen lokalitet → selskap kommer fra `eierskap`, ikke herfra. Se
`docs/KILDE-EIERSKAP.md` punkt 8 for hvor langt den rekker.

### 4.4 Persondata

Kilden er fri for persondata av konstruksjon, ikke av filtrering: det
finnes ingenting å filtrere. Innehaveridentitet ligger på `/licenses`,
som er en egen kilde med en egen vurdering (CLAUDE.md regel 3).

## 5. Frekvens

Ukentlig, `min_dager_mellom = 7`. **Ingen etterslep** — registeret sier
hva som gjelder NÅ, og `gjelder_for()` returnerer kjøredatoen.

Det skiller kilden fra `lusetall` og `sjotemperatur`, som begge ligger
28 dager bak. En analyse som joiner akvakultur mot lusetall på
`observed_at` må vite det.

## 6. Det som IKKE er bygget

* **Historikk før 17.08.2026.** Registeret har ingen tidsakse, og
  snapshotet fra en gitt dato lar seg ikke hente i etterkant.
  CLAUDE.md regel 5.
* **`obsoleteConnections` som egen akse.** Feltet finnes i kroppen og
  leses inn som `tillatelser_trukket` (et antall), ikke som en liste med
  datoer. Kroppen er arkivert; det er en re-parse.
* **`speciesLimitations` i sin helhet.** Bare antallet emitteres.

## 7. Lisens og attribusjon

NLOD — Norsk lisens for offentlige data. Fra
`fiskeridir.no/statistikk-tall-og-analyse/lisens-for-bruk-av-fiskeridirektoratets-data`,
lest 25.08.2026:

> «Den som tar i bruk data fra Fiskeridirektoratet godtar automatisk
> lisensen.»

**Ingen registrering, ingen avtale, ingen søknad, ingen nøkkel.**

Vilkåret er attribusjon. Godkjente former er «Kilde:
Fiskeridirektoratet», «Kilde rådata: Fiskeridirektoratet» eller «Kilde
for rådata som vi har benyttet i vår sammenstilling:
Fiskeridirektoratet». Attribusjonen skal ikke fremstilles som om
Fiskeridirektoratet anbefaler eller går god for vår sammenstilling.

**Enhver visning, rapport eller publisering som bruker disse tallene må
bære attribusjonen.** Det er et lisensvilkår, ikke en høflighet.

Kommersiell bruk er tillatt. Hele kjeden står i `docs/LISENSKJEDE.md`.
