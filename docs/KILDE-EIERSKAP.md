# Eierskap og eierskapshistorikk — verifiseringsnotat

Alt i dette notatet er **målt** mot levende tjenester 02.–03.09.2026.
Der noe bare er lest og ikke verifisert, står det uttrykkelig.

**Kilde: Fiskeridirektoratet** (pub-aqua) og **Brønnøysundregistrene**
(Enhetsregisteret). NLOD for begge; attribusjonen er et vilkår.

To kilder, ikke én:

| kilde | entitet | kadens | hva |
|---|---|---|---|
| `eierskap` | tillatelse | ukentlig | hvem eier hva NÅ |
| `eierskap_historikk` | overføring | backfill | journalførte overføringer 2006– |

---

## 1. Versjonene av `eierskap_historikk` — LES DETTE FØRST

Snapshotene finnes i **to versjoner per år**, og de er ikke likeverdige.

| | overføringer | skrevet |
|---|---|---|
| `<år>-12-31.parquet` (v1) | **1934** totalt | 02.09.2026 19:31 UTC |
| `<år>-12-31.2.parquet` (v2) | **2611** totalt | 02.09.2026 19:43 UTC |

**v1 er kjent UNDERFILTRERT.** Personvernfilteret krevde at mottakerens
selskapstype var kjent, og hentet den bare fra pub-aquas `/entities`.
Historiske mottakere som er oppløst finnes ikke der, så 677 overføringer
ble stoppet — fortrinnsvis de OPPKJØPTE selskapene, altså nøyaktig
hendelsene serien finnes for. Se
`docs/beslutninger/2026-09-03-organisasjonsform-fra-brreg.md`.

**v2 er den gjeldende.** Den slår opp organisasjonsformen hos Brreg for
de 110 mottakerne pub-aqua ikke kjenner.

### Den eneste riktige lesemåten

```python
logg.les("eierskap_historikk", fra, til, versjonsvalg=kjoringslogg.ALLE)
# og deretter: slå sammen per (år, entity_id, felt) på seneste published_at
```

Verifisert 03.09.2026 ved å lese dataene:

    GJELDENDE   21 filer   20888 rader   2611 overføringer
    FORSTE      21 filer   15472 rader   1934 overføringer   <- FEIL
    ALLE        42 filer   36360 rader   2611 overføringer   <- riktig

En leser som tar `<dato>.parquet` uten løpenummer — eller `FORSTE` —
får **1934 og ikke 2611**. Det er 25,9 % av serien som forsvinner
stille, og det er nøyaktig samme felle som senket n med 20 % i
hypotesetesten 01.09.

`GJELDENDE` gir riktig svar her, men **bare tilfeldigvis**: v2 er en ekte
overmengde av v1, så «siste utgitte fil» inneholder alt. Den dagen en
versjon restaterer bare en DEL — som 2025-rapporten gjorde for
ekspertgruppens 2024 — gir `GJELDENDE` feil svar igjen. `ALLE` med
sammenslåing er den eneste lesemåten som er robust mot begge tilfellene.

### Kjent defekt: versjonene er ikke skillbare i dataene

Begge filene bærer **`source_version = "1"`**. Da de ble skrevet var
versjonsfeltet ikke bumpet, så det eneste som skiller dem er
`fetched_at` — elleve minutter fra hverandre.

Det er et brudd på CLAUDE.md 1b-3: et snapshot skal alene kunne svare på
hva som gjaldt da raden ble skrevet, og her kan det ikke svare på hvilket
filter som skrev det.

Defekten kan **ikke rettes på plass** — filene er append-only.
`Eierskap.version` er bumpet til `"2"` fra 03.09.2026, så enhver
FRAMTIDIG skriving er skillbar. Vil man ha dagens data selvbeskrivende,
må de re-parses en gang til som `.3` med versjon 2; det er en egen
beslutning og er ikke gjort.

Merk følgen for revisjonsaksen: `diff.revisjon()` ville IKKE kastet
`Grunnlagssprik` mellom v1 og v2, siden `source_version` er lik. Den
ville i stedet rapportert 677 «revisjoner» — og det ville vært en
påstand om at **Fiskeridirektoratet** ombestemte seg. Se punkt 2.

## 2. Hvorfor dette IKKE er samme sak som ekspertgruppen

Begge steder ligger det flere versjoner av samme dato på disk, og begge
steder er den nyeste den riktige. Likheten stopper der, og forskjellen
avgjør hva changeloggen har lov til å si.

| | ekspertgruppen | eierskap_historikk |
|---|---|---|
| hva endret seg | **KILDEN** ga en ny vurdering | **VÅRT FILTER** ble rettet |
| kroppen | en ny rapport, nytt innhold | byte for byte den SAMME |
| `Grunnlagssprik` er | riktig — to ulike parserversjoner | ville vært riktig, men fyrer ikke (se 1) |
| changelog-rader | `revidert` er sant | ville vært en LØGN |

For ekspertgruppen er `revidert` en sann påstand: rapporten for 2025
vurderte PO9 i 2024 på nytt og kom til noe annet. Kilden ombestemte seg.

For eierskapshistorikken **endret kilden ingenting**. De 677
overføringene har ligget i `transfers`-responsen hele tiden, uendret. Det
som skjedde er at vi endelig klarte å lese dem. En `revidert`-rad ville
sagt at Fiskeridirektoratet la til 677 overføringer i ettertid — en
anklage mot en tredjepart for noe vi gjorde selv.

Derfor ble v2 skrevet med `--reparse`, som skriver snapshotet og **ingen
changelog-rader**. Det er samme mekanikk som ekspertgruppens `--reparse`,
men av en annen grunn: der fordi sammenligningen er UBESVARLIG, her fordi
svaret er kjent og lyder «ingenting skjedde hos kilden».

De gamle filene slettes ikke. De er et ærlig spor av at filteret var for
aggressivt, og et repo som sletter sine egne feilspor kan ingen etterprøve.

## 3. Endepunktene

Verifisert 02.–03.09.2026. Ingen av dem krever autentisering.

| endepunkt | rader | kall | merknad |
|---|---|---|---|
| `pub-aqua/api/v1/licenses` | 3029 | 31 | `range` maks 100, 400 over |
| `pub-aqua/api/v1/entities` | 542 | 6 | bærer ADRESSER, se punkt 5 |
| `pub-aqua/api/v1/licenses/{nr}` | 1 | 1 | spørreparameter er `license-nr`, kebab |
| `pub-aqua/api/v1/licenses/{nr}/transfers` | 0–6 | 1 | eierskapskjeden |
| `data.brreg.no/.../enheter/{orgnr}` | 1 | 1 | organisasjonsform, også for slettede |

`/licenses` er ryggraden: den bærer hele kjeden — `licenseNr`, eier, og
`connections[] → siteNr`. `/entities` har ingen kobling til lokalitet og
kan derfor ikke være det.

## 4. `journalDate` er den eneste datoen, og den er udokumentert

Et overføringselement har nøyaktig fire felter: `identityNr`,
`journalDate`, `journalNr`, `officialName`. Ingen `validFrom`, ingen
overdragelsesdato, ingen avgiver.

Fiskeridirektoratet dokumenterer ikke hva `journalDate` betyr — alle seks
spec-adressene under `/pub-aqua/` svarer 404, og API-katalogen er en SPA
uten API-stier i bundelen.

Serien er internt konsistent (kronologisk 120/120, ingen overføring før
tildeling 120/120, siste overføring = dagens eier 61/62), men datoen skal
leses som **«senest da»**, ikke «akkurat da». Forbeholdet står som
`dato_forbehold` på hver eneste rad.

**Serien heter «journalførte overføringer av tillatelser», ikke
«eierskifter».** 2019 (328) og 2022 (728) er 40 % av alle overføringer og
er begge omstruktureringer, ikke oppkjøpsbølger.

## 5. Persondata i kildene — begge bar mer enn dokumentert

Dette er verdt å lese før noen legger til et felt.

**`/entities`** returnerer for de 43 `Person`-enhetene `addresses` med
`type: "ResidentialLocation"` og `officialSourceType: "FREG"` — altså
**bostedsadresser fra Folkeregisteret** for navngitte privatpersoner.
Ingenting i dokumentasjonen sa det.

**Brregs `/enheter/{orgnr}`** returnerer for en AKTIV enhet
`forretningsadresse`, `postadresse`, `epostadresse`, `telefon` og
`mobil`. For enkeltpersonforetaket `985937028` er det hjemmeadressen og
personens eget mobilnummer.

Begge kropper **reduseres i `fetch()` før arkivering**. Rå-arkivet ligger
i git og er append-only; en adresse som kommer inn der, kan ikke fjernes.

### Filteret

Tre vilkår, i denne rekkefølgen:

1. **Typen må være KJENT.** «Vet ikke» betyr aldri «slipp gjennom».
2. **Typen må ikke være en personform** — `Person`,
   `SoleProprietorship` (pub-aqua) eller `ENK` (Brreg, via
   `core/persondata.PERSONFORMER`).
3. **Nummeret må være ni siffer.** Andre lås, ikke hovedregelen: 8 av 8
   enkeltpersonforetak i registeret har ni siffer.

Personformer fra Brreg **arkiveres ikke i det hele tatt**. Et arkiv som
sier «dette nummeret tilhører et ENK» er en opplysning om et menneske.
Det koster ingenting: fraværende og personform gir begge STOPP.

## 6. Konsernstruktur — en LUKKET vei for historikk

Samme status som HIs ukesstatus i
`2026-08-31-hypotesen-omdefineres.md`: undersøkt, målt, og **utelukket**.

Endepunktet finnes:
`data.brreg.no/enhetsregisteret/api/konsernstruktur/{orgnr}` — merk at
det ligger på rota og **ikke** under `/enheter/`, som er grunnen til at
første forsøk ga 404. Det kom til 24.06.2026, i JSON og CSV.

Det svarer rikt for levende enheter. Kallet på `929706331`
(FRØY HAVBRUK AS) gir øverste mor `GÅSØ NÆRINGSUTVIKLING AS` og et helt
tre av døtre med `nivaa`, `knytningsform` (`KDAT` «Konsern datter»),
`grunnlag` («100 %») og `dato`.

**Men skillet konserninternt / ekte eierskifte lar seg IKKE gjøre med
offentlige data i dag, og det løses ikke ved å bygge mer.** To målte
grunner:

1. **404 for slettede enheter.** `959352887` (MOWI NORWAY AS),
   `921668236` (MOWI SEAWATER NORWAY AS) og `930367931` (GRIEG SEAFOOD
   ROGALAND SJØ AS) gir alle 404. Det er nøyaktig de selskapene som
   utgjør 2019- og 2022-toppene — altså de eneste tilfellene spørsmålet
   er interessant for.
2. **`dato` er dagens.** Treet er konsernstrukturen NÅ (2026-02-19 i
   eksempelet), ikke slik den var da overføringen ble journalført. Selv
   der endepunktet svarer, kan det ikke si om en overføring i 2012 var
   konsernintern — konsernet så annerledes ut da.

Konsekvensen skal stå sammen med enhver visning av serien: **vi kan ikke
skille en konsernintern flytting fra et ekte oppkjøp.** Det er ikke en
mangel ved uttrekket; det er en grense i hva som er publisert.

### Det som ER mulig, og som ikke er bygget

En **tidsserie av konsernstrukturer bygget FRAMOVER fra i dag.** Hentes
strukturen for hver aktiv eier ukentlig eller månedlig, har vi om to år
et arkiv som kan svare på om en overføring i 2027 var konsernintern.

Det ville kreve:

- ett kall per aktiv eier (i dag 536, hvorav de som er `erIKonsern`)
- egen kilde med egen kadens; strukturen endres sjelden
- samme personvernfilter — treet inneholder navn og organisasjonsnumre
- en beslutning om at spørsmålet er verdt et arkiv som først gir svar
  om år

Det retter **ikke** historikken. 2006–2026 forblir «journalførte
overføringer» uten konsernskille, permanent.

## 7. Dekning

    tillatelser                      3029
    med minst én overføring          1496
    uten overføringer                1533   (50,6 %)

Halvparten har aldri skiftet eier. Det er dekning, ikke feil: 57 av 58
kontrollerte tillatelser uten overføringer har fortsatt sin opprinnelige
tildelte som eier.

    overføringer på tillatelse med kjent lokalitet   2541
    overføringer uten aktiv lokalitet i dag            87
    overføringer med lokalitet ukjent for oss           0

Lokalitetstilknytningen er **dagens**. Overføringene rekker til 2006,
men en tillatelse som lå på en annen lokalitet i 2012 blir tilskrevet
dagens. Vår akvakultur-serie har tre snapshots (17., 24., 31.08.2026), og
koblingen lokalitet → selskap rekker ikke lenger bakover enn det.
