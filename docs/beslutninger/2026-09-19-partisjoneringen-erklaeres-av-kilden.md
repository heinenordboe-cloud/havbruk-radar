---
dato: 2026-09-19
tittel: Hvitelista leser datoene kilden erklærer — og kilden filtrerer det døra ikke ser
status: besluttet
commit: [fylles inn]
---

# Hvitelista leser datoene kilden erklærer

**Bestemt:** `publiseringsvakt.hviteliste()` leser **ALLE** datoer for en
kilde partisjonert på når noe gjaldt i verden, og **NYESTE** dato for en
kilde partisjonert på når vi hentet. Kilden erklærer selv hvilken type
den er — `Source.partisjonering` — og erklæringen etterprøves mot
dataene ved hver portkjøring.

Vedhenget er ikke valgfritt: **kilden spørres i tillegg til lesedøra**
(`Source.fjern_egne_personer()`), både av porten og av generatoren. Uten
det hvitelister regelen de personformede mottakerne i de eldre
partisjonene i stedet for å filtrere dem — stillhet kjøpt for sikkerhet.

Dette er alternativ 3 med vedheng, av de fire som ble lagt fram 18.09 for
kategori 1. Grunnlaget er målt i
[docs/MALING-PARTISJONERING.md](../MALING-PARTISJONERING.md) og skrevet
ned FØR koden.

    976 funn  ->  15 funn
    ukjent_navn    753 -> 0
    ukjent_orgnr   208 -> 0
    personform      15 -> 15   (kategori 2, åpen beslutning)
    grunnlagsfunn    –  -> 0

---

## 1. Hvorfor erklæringen ligger på kilden

Sjette utgave av samme resonnement i `core/contract.py`. `utvalg`,
`published_at`, `domene`, `startdatofelt` og `attribusjon` ligger alle på
kilden fordi kilden er den eneste som VET, og fordi et andre sted å slå
det opp er et sted de to kan svare ulikt (F6, F7, F8).

En liste i `core/` over hvilke kilder som er hva ville i tillegg brutt
regel 1: en ny revisjonskilde ville krevd en endring i kjernen for å bli
lest riktig.

Dette er 1b-7 gjort til en egenskap ved kilden. `observed_at` handler om
VERDEN og `fetched_at` om OSS — men hvilken av de to som BESTEMMER
PARTISJONEN kan kjernen ikke slutte seg til, for begge ser like ut i en
parquet-fil.

### Per navn, fordi én klasse kan skrive to serier

`eierskap` er den ene kilden som trenger dict-formen: ukentlig uttrekk
under sitt eget navn, backfill etter journalføringsår under
`eierskap_historikk`. Er erklæringen en dict, må hvert navn kilden
skriver under stå der — `erklaert_partisjonering()` kaster på et
manglende navn framfor å falle tilbake på en standard, fordi den glemte
aliasen er nettopp den feilen som ellers blir stille: 20 av 21 årganger
usett, som er hele problemet regelen skal løse.

## 2. Klassifiseringen, og premisset som ikke holdt

Målt som `observed_at` mot `fetched_at` over HVERT snapshot:

    henting   akvakultur, biomasselag, eierskap, enhetsregisteret
              0 dagers avvik i hvert enkelt snapshot — min og maks
    verden    biomasse, eierskap_historikk, ekspertgruppen, lusetall,
              reguleringsomraader, romming, sjotemperatur, trafikklysvedtak
              median mellom −77 og −3532 dager

**Premisset da regelen ble formulert var at «lusetall og de ukentlige» var
henting-typen. Det holdt ikke.** `lusetall` har 764 datoer fra 2012-01-02
og median 2669 dager mellom uka raden gjelder for og dagen vi hentet
den — datoen i filnavnet er ISO-uka, som er rettelsen av F6. Regelen
klassifiserer **8 av 12** kilder som «verden», ikke 2.

`romming` er målt BLANDET og erklæringen sier det: elleve årsfiler fra
backfillen og to kjøredatoer fra den ukentlige veien, der `gjelder_for()`
returnerer kjøredatoen. Erklæringen følger serien slik den er bæreverdig.

### Innstrammingen er ikke gitt opp, den er gjort presis

`hviteliste()` leste nyeste dato for ALLE kilder fram til i dag, med
begrunnelsen at «en generator som viser et selskap som forsvant ut av
registeret for et år siden henter fra et sted vakten ikke kjenner». Den
begrunnelsen er riktig om `enhetsregisteret` og feil om
`eierskap_historikk`, der 2009-årgangen er et annet tidsrom og ikke en
utdatert versjon av 2026.

Målt hva presiseringen beholder: forskjellen mellom regelen og «alle
datoer for alt» er **13 navn og 5 orgnumre** — de eldre partisjonene til
henting-kildene. Lite, men det er nøyaktig den innstrammingen som fantes,
og en regel som leste alle datoer for alt ville gitt den bort.

Kostnaden er 7,17–7,54 s mot 0,07–0,08 s, og lusetall er 5 av de 7
sekundene. Porten kjører ved publisering, og bygget av de 1782 sidene tar
20 s.

## 3. Vedhenget: kilden filtrerer det døra ikke ser

At hvitelista leser de eldre partisjonene betyr at
`persondata.fjern_personformer()` kjører på dem. **Målt fjerner den 0 av
36 360 rader** fra `eierskap_historikk`, fordi kilden skriver 0 rader
`organisasjonsform` og 0 `institusjonell_sektorkode`. Formen står i
`mottaker_type`, i pub-aquas vokabular.

Uten et tillegg ville regelen altså gjort de fire personformede
mottakerne REDE FOR i stedet for å filtrere dem, og porten ville sagt
grønt om en side som viste dem.

16.09-notatet avviste å lukke dette med at «`core/` kjenner en kildes
vokabular — to lister som skal si det samme, altså formen F6 og F7
hadde». **Innvendingen gjelder en LISTE, ikke en DELEGERING:**
oversettelsen finnes på ett sted, `sources/eierskap.FORM_KART`, og
kjernen spør den som eier den. Kjernen lærer ingen koder.

Filteret spør `er_person()` og ikke kartet, og det er målt hvorfor:
`mottaker_type` finnes på 2611 av 2611 overføringer, og av de fire
treffene bærer TRE Brreg-koden `DA` mens én bærer
`JointLiabilityCompany`. `FORM_KART.get("DA")` er `None` — kartet
oversetter FRA pub-aquas navn — så en implementasjon som slo opp i kartet
ville tatt **1 av 4** og sett riktig ut.

**Porten og generatoren leser LIKT.** Begge kaller hooken; to lesemåter
av samme kilde som kan svare ulikt er formen F6 og F7 hadde. Målt effekt:
hooken fjerner 40 rader fra de 21 årgangene, holder 7 navn og 3 orgnumre
ute av hvitelista, og etter regenerering står **0 personformnavn i
overføringstabellene** mot 2 før. Serien står: 12 700 overføringsrader i
utputtet.

Den ukentlige seriens `eier_type` står uttrykkelig IKKE i hooken, med en
test som feller en utvidelse. En slik rad forsvinner fra neste snapshot
av seg selv — `fetch()` og `parse()` stopper den, målt på arkivkroppen
fra 14.09 — mens de 21 årgangene aldri parses på nytt. Å ta den med ville
vært B1 fra 18.09, som ble vurdert og ikke valgt.

## 4. `feilerklaert_partisjon` — sikringen mot den stille retningen

De to feilretningene er ikke like, og det er hele grunnen til at porten
etterprøver erklæringen:

| feil | følge | hvordan det merkes |
|---|---|---|
| «verden» erklært som «henting» | hvitelista blir for LITEN | hvert navn i historikken meldes som `ukjent_navn`. Høyt, irriterende, ufarlig. |
| «henting» erklært som «verden» | hvitelista blir for STOR | et navn som forsvant ut av registeret for et år siden er gjort rede for, og en visning som viser det PASSERER. **Stille.** |

En vakt som bare kan felle den støyende retningen er ikke en vakt mot den
stille. Prøven er MÅLT mulig, og det er forutsetningen for at den kan
stå: de fire henting-kildene har 0 dagers avvik i HVERT snapshot, de åtte
andre median −77 til −3532. Skillet er ikke gradvist.

**Verifisert ved å plante en feil erklæring**, mot ekte data:

    som erklært i fila                            0 grunnlagsfunn

    enhetsregisteret erklærer «verden»             1 funn
      feilerklaert_partisjon — «erklært «verden», men alle 5 snapshots er
      datert dagen de ble hentet. Er kilden «henting», hvitelister vi navn
      som ikke gjelder lenger»
      → og det ville kostet: hvitelista for kilden vokser fra 1742 til
        1749 navn, altså 7 navn som ikke gjelder lenger

    lusetall erklærer «henting»                    1 funn
      feilerklaert_partisjon — «764 av 764 snapshots gjelder for et annet
      tidsrom enn hentingen (2012-01-02: −5343 dager)»

    enhetsregisteret erklærer ingenting            1 funn
      ukjent_partisjon — «Source.partisjonering er ikke satt»

    tilbake til erklæringen i fila                0 grunnlagsfunn

Tre valg i prøven er verdt å navngi:

1. **«henting» motbevises av ETT snapshot.** Påstanden er at datoene
   ALLTID faller sammen, så ett avvik er nok. Ingen terskel.
2. **«verden» krever TO snapshots for å motbevises.** Med ett snapshot er
   0 dagers avvik uinformativt: en kilde hentet samme dag som tidsrommet
   den gjelder for ser ut som en henting-kilde, og det er fravær av
   grunnlag — ikke en feil erklæring. En vakt som felte på det ville felt
   enhver ny kilde på dens første kjøring.
3. **Snapshots uten `fetched_at` feller ingenting.** `enhetsregisteret`
   har ett slikt (2026-08-16, fra før feltet fantes). Fravær av et
   tidsstempel er ikke en feil erklæring.

`ukjent_partisjon` gjør stillhet til et funn, altså en blokkering: en ny
kilde som glemmer erklæringen stopper publiseringen, akkurat som en
UBELAGT attribusjon gjør. Grunnlagsfunnene ligger i samme liste som de
tre utputtprøvene, fordi følgen er den samme — en hviteliste bygget på en
feil erklæring gjør rede for noe den ikke har sett, og et grønt bygg på
den er verre enn et rødt.

## 5. Hva som står igjen

**15 funn, alle `personform`, alle ekte.** Det er kategori 2 fra 18.09:
14 sider viser en ANS fra 1978 som `tildelt_navn`, og 11593 viser et
partrederi som dagens eier. Personformfilteret fjerner ENTITETER, og
navnet på en personform overlever som VERDI på en annen entitets rad.

Den beslutningen er åpen, og den er ikke berørt her. Porten gir exit 1, og
ingenting publiseres før den er tatt.

## Hva som ville snudd det

- **At en kilde erklærer feil type.** Dette er den viktigste, og den er
  grunnen til at punkt 4 finnes framfor å være en TODO. Den STILLE
  retningen — «henting» erklært som «verden» — er den som må fanges av en
  måling og ikke av at noen leser en diff, fordi følgen er at porten sier
  grønt. Prøven fanger den så lenge kilden har to snapshots og bærer
  `fetched_at`. Faller en av de forutsetningene bort, er prøven svakere
  enn den ser ut, og da skal den skrives om — ikke slås av.
- **At en kilde blir BLANDET uten å si det.** `romming` er blandet i dag
  og erklæringen sier det. En kilde som begynner å skrive begge slags
  datoer i samme mappe uten at erklæringen endres, gir ingen
  grunnlagsfunn: «verden» tåler at noen snapshots har 0 avvik. Det er en
  kjent grense, og den nærmeste tråden hvis prøven skal skjerpes.
- **At kostnaden vokser vesentlig.** 7 sekunder for hvitelista er greit
  når bygget tar 20. Blir lusetallserien fem ganger lengre, er det 25
  sekunder for én prøve, og da er spørsmålet om hvitelista skal bufres
  mellom kjøringer — med alt det medfører av å lese en buffer i stedet
  for dataene.
- **At `fjern_egne_personer()` blir brukt av flere kilder enn én.** Hooken
  er i dag én overstyring, målt nødvendig. Blir den tre eller fire, er
  spørsmålet om det egentlig er et felt kildene burde skrevet på raden i
  stedet — altså regel 1b-3: verdien som avgjør hva raden betyr, lagret
  sammen med den. Det ville vært en bedre løsning enn en hook, og den er
  bare stengt fordi de 21 årgangene er append-only.

**Ville IKKE snudd det:** at `lusetall` koster 5 sekunder for 0
orgnumre og 2684 lokalitetsnavn. Prøven skal ikke vite hvilke kilder som
«plejer» å bære persondata — det er nøyaktig formen 1b-2 advarer mot.
