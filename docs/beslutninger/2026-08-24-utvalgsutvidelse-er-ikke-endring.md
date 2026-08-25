---
dato: 2026-08-24
tittel: Utvalgsutvidelse er ikke endring
status: utkast
commit:
---

# Utvalgsutvidelse er ikke endring

> **UTKAST.** Skrevet ut fra kartleggingen og målingene under. Avsnittene
> «Prisen» og «Ville snudd det» er skisser og skal skrives om for hånd.

**Bestemt:** hvert snapshot bærer med seg hva kilden BA OM
(`utvalg`-kolonnen, kanonisk JSON fra `core/utvalg.py`).
`diff.compare()` merker rader som `utvalgsutvidelse` når en entitet er
ny OG utvalget er utvidet siden forrige snapshot. Radene beholdes, men
teller ikke som bevegelse og treffer ingen signalregel. Signalregelen
«Nytt selskap i bransjen» krever i tillegg at selskapets egen
`registreringsdato` ligger etter datoen vi sammenlignet mot.

**Skillet:** «ny i verden» er ikke «ny i vårt utvalg». Utvider du
søket, er de to umulige å skille — med mindre snapshotet vet hva det ba
om.

## Tallene

Kjøringen 24.08.2026 ga 26673 endringer, fordelt på to changelog-filer
fordi kildene har hver sin gyldighetsdato:

    changelog/2026-08-24.parquet   akvakultur + enhetsregisteret   26045
    changelog/2026-07-27.parquet   lusetall (uke N-4)                628

Delt på om entiteten fantes i forrige snapshot:

    entity_id som IKKE fantes    25804   96,7 %
    eksisterende enheter           869    3,3 %

    akvakultur         121 endringer      0 nye enheter   121 eksisterende
    enhetsregisteret 25924 endringer  25804 nye enheter   120 eksisterende
    lusetall           628 endringer      0 nye enheter   628 eksisterende

De 25804 er **908 selskaper × ~28 felter**. Utvalget gikk fra 904 til
1810 lesbare enheter: 908 inn, 2 ut.

### Hvor de 908 kom fra

Næringskodelista i `config.yml`:

| commit | tidspunkt | aktive koder |
|---|---|---|
| `870b317` | 15.08 21:18 | 6: 03.211, 03.212, 03.221, 10.201, 10.202, 10.209 |
| `c1f4343` | **17.08 22:07** | 7: −10.209, +03.222, +10.203 |
| `95938d7` | **17.08 22:14** | **9: +03.300, +10.912** |

Siste 17.08-snapshot ble hentet `2026-08-17T19:33:53Z`. De to
config-commitene er fra `02:07` og `02:14 UTC` 18.08 — **6½ time etter**.
Kodene rakk aldri å påvirke 17.08-snapshotet, og første innsamling med
den nye lista var 24.08.

Fordelingen bekrefter det:

    03.300   433  <- lagt til 17.08 kveld
    10.203   329  <- lagt til 17.08 kveld
    03.222   114  <- lagt til 17.08 kveld
    10.912    17  <- lagt til 17.08 kveld
    -------------
             893  (98,3 % av 908)
    + 13 til treffer en ny kode via naeringskode2/3
    -------------
             906 av 908

De to siste (`RØN GARD AS`, `DOMSTEIN SERVICE AS`) har koder som lå i
søket også 17.08, og finnes ikke i 17.08-rådataene i det hele tatt —
heller ikke før persondatafilteret. Enten byttet de næringskode, eller
Brreg indekserte dem sent. Ingen av dem er nyregistrert.

### Hva signalet gjorde

Av 912 scorede signaler 24.08:

    908  Nytt selskap i bransjen
      3  Aksjekapital økt
      1  Endret vedtektsfestet formål

Registreringsdato for alle 908:

      0  registrert etter forrige snapshot (2026-08-17)
      1  registrert i august 2026
     26  registrert i 2026
    107  registrert i 1995
        eldste 1995-02-19, nyeste 2026-08-04

Regelen fyrte 908 ganger og hadde rett **null** ganger.

## Rotårsaken: en tilstand som ikke lå i dataene

`diff.compare()` hadde allerede begrepet «dette er en utvidelse, ikke en
hendelse» — skjemautvidelsesfilteret, som undertrykker rader når et
FELTNAVN er nytt. Målt 17.08: den regelen fjernet **18687 rader** da
Enhetsregisteret gikk fra 9 til 32 felter, og gjorde at dagen ble
rapportert som 0 endringer i stedet for 18687.

Utvalgsutvidelse er samme klasse hendelse med samme klasse støy, og
hadde ingen behandling. Forskjellen var ikke prinsipiell — den var at
den ene tilstanden lå i dataene og den andre ikke:

    nytt FELTNAVN     etterprøvbart fra de to snapshotene alene
    ny ENTITET        krever å vite hva vi ba om, og det sto i config.yml

Dette er regel 1b i `CLAUDE.md`, med utvalget i stedet for tiden: en
tilstand som avgjør hva dataene BETYR, som ikke ligger i dataene. Et
snapshot kunne fortelle hva vi fant, men ikke hva vi lette etter — og
da kan ingen sammenligning av to snapshots skille de to slags «ny» uten
å lese git ved siden av.

## Løsningen i fire deler

### 1. Utvalget lagres per snapshot

`Observation.utvalg` — kanonisk JSON, én kolonne i parquet, stemplet av
`runner.stempl()` sammen med `fetched_at`, `source_version` og
`raw_hash`. Kilden setter `self.utvalg` **inne i `fetch()`**, som med
`advarsler`.

At det settes av `fetch()` og ikke er en egen metode er hele poenget. En
`utvalg(kjoredato)`-metode ville vært et ANDRE oppslag mot config, og to
oppslag som kan svare ulikt om samme sak er mønsteret fra F6, F7 og F8.
Setter `fetch()` den mens den henter, beskriver den nødvendigvis det
kallet som faktisk ble gjort.

**Per rad og ikke i en sidecar-fil.** En `<dato>.utvalg.json` ved siden
av parquet-fila hadde vært lettere å lese i git, men det er to filer som
kan komme fra hverandre — og «filnavnet løy om innholdet» er F6.
Kolonnen kan ikke drifte fra radene den beskriver. Kostnaden er nær null i
praksis: verdien er lik for hver rad, så parquet ordbok-koder den bort.
Målt på enhetsregisteret 24.08 — 51623 rader, 100 tegn utvalg — er
tillegget 1156 bytes, 0,53 % av fila.

**Ikke parquet-metadata.** Polars 1.36 støtter `write_parquet(metadata=)`,
men den er usynlig i `git diff`, krever et eget kall for å lese, og
forsvinner stille hvis fila noen gang skrives om av et verktøy som ikke
kjenner den. Stille tap er den ene feilmodusen dette repoet er bygget
mot.

**Bare lister.** `normaliser()` avviser skalarer. `sidestorrelse: 100`
avgjør hvor mange kall det tar, ikke hvilke selskaper vi får, og et felt
som ikke endrer utvalget skal ikke kunne utløse en utvalgsutvidelse.

### 2. diff.compare() merker, den sletter ikke

Ny `change_type`-verdi `utvalgsutvidelse`, ikke en boolsk kolonne ved
siden av `ny`. Enhver leser som forgrener på `change_type` må da
forholde seg til den eksplisitt i stedet for å svelge den som bevegelse
— og signalreglene, som matcher på `endringstype: ny|endret|borte`,
slutter å treffe uten at én linje i `signals.yml` måtte endres.

Radene BEHOLDES. Skjemautvidelsen slettes fordi påstanden er sikker;
denne merkes fordi påstanden hviler på et felt som kan være tomt. En
undertrykt rad er en hendelse ingen får se.

`diff.bevegelse()` er den ene funksjonen som svarer «hvor mye skjedde
denne uka». Ett spørsmål, ett svar, ett sted å glemme det.

### 3. Unntaket: en ekte nyregistrering overlever utvidelsesuka

Første versjon merket ALLE nye entiteter i en utvidelsesuke. Den ble
kjørt gjennom hele løypa, og resultatet avslørte feilen: et selskap
registrert etter forrige snapshot ble merket sammen med de gamle, og
«Nytt selskap i bransjen» fyrte null ganger — også for det som faktisk
var nytt. Det er samme tap som utvidelsen selv skaper, bare med motsatt
fortegn.

`Source.startdatofelt` løser det. Kilden oppgir navnet på feltet som
bærer entitetens egen fødselsdato (`registreringsdato` for Brreg), fordi
navnet er kildens og `core/` ikke skal kjenne Brregs ordforråd. Er
startdatoen etter `forrige_observed_at`, står raden som `ny`.

Verifisert i miniatyr, tre selskaper i én utvidelsesuke:

    1  kommune            Bodø -> Tromsø        [endret]              bevegelse
    2  navn               None -> Innhentet AS  [utvalgsutvidelse]    reg. 1998
    3  navn               None -> Helt Fersk AS [ny]                  reg. 2026-01-05

    signaltreff: [('Helt Fersk AS', 'Nytt selskap i bransjen')]

Tom `startdatofelt` er den strenge siden: uten en startdato finnes det
ingen grunn til å påstå at entiteten er ny i verden, og da merkes alle.

**Kjent kant:** startdatofeltet må finnes i FORRIGE snapshot også. Legger
en kilde til startdatofeltet sitt i samme uke som utvalget vokser, spiser
skjemautvidelsesfilteret datoen før noen rekker å lese den, og
utvidelsesuka har ingen fødselsdato å skille på. Fanget av en test.

### 4. forrige_observed_at på hver changelog-rad

Samme klasse mangel, oppdaget underveis: en changelog-rad sa hvilken
dato den gjaldt, men ikke hvilken dato den ble sammenlignet MOT. 26673
endringer over sju dager og over tretti dager så identisk ut i loggen.
Nå står baselinen på raden, og signalregelen `krev_dato_etter_forrige`
kan bruke den.

## Historikken: merkes ved lesing, aldri skrevet om

De 25804 radene i `changelog/2026-08-24.parquet` blir stående. Regel 2 i
`CLAUDE.md` gjelder, og en changelog som skrives om er ikke en changelog.

`changelog.merk_utvalgsutvidelse()` merker dem ved LESING, og
etterprøvbart:

> en entitet som er «ny» for oss, men hvis egen startdato ligger FØR
> snapshotet vi sammenlignet mot, kan ikke ha kommet inn fordi noe
> skjedde i verden. Den kom inn fordi vi begynte å se etter den.

Det er nøyaktig samme test som signalregelen bruker på ferske rader —
én definisjon av «ny i verden», brukt tre steder. Baselinen tas fra
raden når den finnes, ellers fra snapshotene, som fortsatt ligger der.

Testen er bredere enn årsaken den er navngitt etter. En utvidet
næringskodeliste er ett svar på «hvorfor ble vår luke større»; en rettet
paginering, et lettet filter eller et endepunkt som begynte å svare
fullstendig er andre. Alle er samme klasse hendelse.

Målt mot fila slik den ligger:

    rå på disk (URØRT)   26673 rader   ny 25816   endret 785   borte 72
    merket ved lesing    26673 rader   utvalgsutvidelse 25804
                                       endret 785   borte 72   ny 12
    bevegelse                            869 rader

De 12 som beholder «ny» er alle på entiteter vi allerede fulgte: 8
`lusetall.voksne_hunnlus`, 3 `siste_innsendte_aarsregnskap`, 1
`mva_registreringsdato`.

`vis.py` kaller den før den teller. Tallet skjules ikke — det står som
egen post, fordi uka utvalget vokser er den uka enhver senere
sammenligning må ta hensyn til.

Kilder uten et kjent startdatofelt røres ikke. `STARTDATOFELT` i
`changelog.py` er bevisst en frossen, endelig ordbok og ikke et oppslag
i kilderegisteret: den gjelder bare rader skrevet før 24.08.2026, og det
settet vokser aldri. Et oppslag i registeret ville dessuten gjort
historikken uleselig den dagen en kilde slås av.

## Verifisert mot levende data

Kartleggingstallene over er lest ut av produksjonsfilene. Selve fiksen er
kjørt mot Brreg to ganger, med et ekte utvalgsbytte mellom hentingene:

    uke 1  utvalg={"naeringskoder": ["03.211"]}
           16573 observasjoner, 584 selskaper
    uke 2  utvalg={"naeringskoder": ["03.211", "03.300"]}
           29187 observasjoner, 1026 selskaper

    diff:  12490 rader, alle utvalgsutvidelse
           bevegelse (diff.bevegelse):     0
           baseline stemplet:     2026-08-10
           442 selskaper kom inn, 0 registrert etter 2026-08-10
           signaltreff:                    0

Samme data gjennom den GAMLE oppførselen — regelen uten
`krev_dato_etter_forrige`, og `utvalgsutvidelse` skrevet om til `ny`:

    442 x "Nytt selskap i bransjen"
    12490 rader talt som bevegelse

Mot changeloggen som ligger på disk (fila er ikke rørt):

    rå på disk            26673 rader   ny 25816   endret 785   borte 72
    merket ved lesing     26673 rader   utvalgsutvidelse 25804
                                        endret 785   borte 72   ny 12
    bevegelse                             869 rader
    signaltreff                             4   (var 912)

Med baselinen satt til 2026-08-17, slik at datotesten faktisk kjører på
de 908 og ikke bare faller på et manglende felt: «Nytt selskap i
bransjen» treffer **0**. Flyttes registreringsdatoen for ett av dem til
2026-08-20, treffer den **1** — regelen er slått av for de gamle, ikke
slått av i det hele tatt.

211 tester grønne, hvorav 17 nye. Mutasjonssjekk: fjernes merkingen i
`diff.compare()`, feiler to av dem.

## Prisen

*(skisse — skrives om)*

- **En kolonne til i hvert snapshot.** Fri i lagring, men SCHEMA er en
  kontrakt mot historikken, og den er nå én ting lengre.
- **En fjerde `change_type`.** Alt som leser changeloggen må kjenne den.
  Det er valgt med vilje — en ukjent kategori er lettere å oppdage enn en
  boolsk kolonne som glemmes — men det er en kostnad for enhver leser
  skrevet før i dag.
- **`startdatofelt` er kildekunnskap i kontrakten.** Ikke Brregs feltnavn
  i `core/`, men et hull i abstraksjonen: kontrakten vet nå at entiteter
  kan ha en fødselsdato.
- **Merkingen er en påstand, ikke et faktum.** Den hviler på at kilden
  oppgir utvalget sitt riktig. En kilde som setter `self.utvalg` til noe
  annet enn det den faktisk spurte om, får løyet uimotsagt.

## Ville snudd det

*(skisse — skrives om)*

- At `er_utvidet()` viser seg for streng i praksis. Blandet inn og ut i
  samme uke — som faktisk skjedde 17.08, der 10.209 gikk ut mens 03.222
  og 10.203 kom inn — svarer i dag usant, og radene blir stående som
  endringer. Er det den vanlige formen for utvalgsendring, må det
  behandles, og svaret er en skrevet kvittering à la `godta_volum()` —
  ikke en løsere heuristikk.
- At `registreringsdato` viser seg upålitelig som fødselsdato. Da faller
  både signalregelen og den retroaktive merkingen samtidig, fordi de
  bruker samme test. Det er med vilje: én definisjon som kan ta feil ett
  sted er bedre enn to som kan ta feil hver for seg.
- At en kilde trenger å uttrykke utvalget sitt som noe annet enn sett av
  strenger — et datointervall, en geografisk boks. Da er `normaliser()`
  for smal, og `er_utvidet()` trenger en ordning per type.

## Mønsteret

Dette er sjuende gang samme form dukker opp i dette repoet, og andre
gang på samme dag. F8 om morgenen: frekvensvakten målte `sist_forsok`
der den skulle målt `sist_ok` — et forsøk er ikke et resultat. F9 nå:
diffen målte «finnes ikke i forrige snapshot» der den skulle målt
«finnes ikke i verden» — ny for oss er ikke ny i verden.

Begge er en mekanisme som måler noe som LIGNER det den skal måle, og som
er riktig i akkurat de tilfellene der de to faller sammen: kjøringen som
lykkes, uka utvalget står stille. Begge er stille når de tar feil.

Det nye her er hvor tilstanden lå. F4/F6/F7/F8 handlet alle om et
tidspunkt slått opp feil sted. F9 handler om en tilstand som ikke var
lagret i det hele tatt — den lå i `config.yml`, en fil som skrives om, og
i git-historikken, som ingen analyse leser. Regelen som følger står i
`CLAUDE.md` 1b-3: **en verdi som avgjør hva dataene betyr, skal lagres
sammen med dataene.**
