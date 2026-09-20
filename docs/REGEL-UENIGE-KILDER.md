# Regel: når to kilder er uenige, sier siden det

**Målt 19.09.2026.** `akvakultur` oppgir hvilke tillatelser som ligger på
en lokalitet. `eierskap` oppgir hvem som eier en tillatelse. De er uenige
om **84 tillatelsesnumre på 65 lokaliteter** — 62 av dem der INGEN av
tillatelsene finnes i `eierskap`.

Selskapssider og områdesider skal vise tillatelser. Bygges de uten en
regel, arver de uenigheten, og fire sidetyper løser den fire ganger.

**Regelen:** en lokalitet der vi ikke vet hvem som eier tillatelsene
**sier det**. Den viser ikke en tom tabell, den utelater ikke raden, og
den later ikke som tallene stemmer.

---

## 1. Hva uenigheten er

| | |
|---|---:|
| lokaliteter med tillatelser i `akvakultur` | 1779 |
| alle tillatelser finnes i `eierskap` | **1714** |
| noen finnes | 3 |
| **ingen finnes** | **62** |
| distinkte tillatelsesnumre i `akvakultur` | 2989 |
| av dem ukjent i `eierskap` | **84** |

De 62 er ikke én art og ikke én region: 24 SHELL_FISH, **21 SALMON**, 12
OTHER_FISH, 5 blandet; 39 Salt og 23 Fresh; 40 Offshore og 22 Onshore.
Elleve tillatelsesprefikser finnes BARE blant de manglende (`HE-E`,
`HE-ED`, `I-GR`, `OP-NA`, `OP-SL`, `R-BR`, `TF-D`, `TK-D`, `TK-V`, `Ø-H`,
`Ø-HD`) — altså innlandsfylker.

**Bare 3 av de 84 står som trukket** noe sted i `tillatelser_trukket`. De
er altså ikke utgåtte tillatelser.

## 2. Hvilken kilde har rett? BEGGE.

Spurt hos kilden, ett kall per nummer, alle 84:

    statuskoder: {200: 84}
      finnes i /licenses med TOMT openLegalEntityNr: 55
      finnes med et organisasjonsnummer:             29
      finnes ikke / feilet:                           0

**Alle 84 finnes hos Fiskeridirektoratet.** `akvakultur` har altså rett:
tillatelsene er der. For TRETTØY (11517) kontrollert i detalj —
`GET /pub-aqua/api/v1/sites/11517` — er **alle 14 `status: ACTIVE`,
`statusValue: AKTIV`, og `obsoleteConnections` er tom.**

To av de 21 laksetilfellene, kontrollert på samme måte:

    OP-NA-0505  (10364 NORAKER GÅRD, Nord-Aurdal)  openLegalEntityNr = ""
    HE-ED-0503  (10850 VALDALEN, Engerdal)         openLegalEntityNr = ""
    N-BR-0023   (10856 FUGLLIELVA, Brønnøy)        openLegalEntityNr = ""

`eierskap` har også rett — den kan ikke navngi eieren:

- **55 av 84: `openLegalEntityNr` er tom.** Feltnavnet er kildens eget
  hint, og `sources/akvakultur.py` leste det riktig allerede 17.08: «At
  det ene feltet heter *open* tyder på at innehavere som er
  privatpersoner ikke får nummeret publisert.» Eieren er en fysisk
  person, og `_tillat()` krever ni siffer. **CLAUDE.md regel 3 forbyr oss
  å lagre den uansett.**
- **29 av 84: nummeret finnes, men eieren gjør ikke.** Eier-ID-en står
  ikke i `/entities` (487 enheter), så typen er ukjent — og `_tillat()`
  vilkår 1 sier at «vet ikke» ikke kan bety «slipp gjennom» i et
  personvernfilter. Kontrollert for to av dem mot vår egen arkivkropp:
  begge eier-ID-er mangler i `enheter`.

Den arkiverte kroppen fra 14.09 inneholder **0** av hver kategori — de
ble filtrert i `fetch()` før arkivering, som kilden er skrevet for å
gjøre.

**Konklusjonen: dette er ikke en datafeil, og ikke kildens uenighet. Det
er vårt eget personvernfilter, sett fra lokalitetssiden.** Det er også
grunnen til at det ikke kan «rettes»: rettelsen ville vært å lagre
identiteten til 55 privatpersoner.

## 3. Regelen

En visning som viser tillatelser skal skille tre tilstander, og aldri
blande dem:

    KJENT        tillatelsen finnes i eierskap. Eieren navngis.
    UGJORT REDE  tillatelsen finnes i akvakultur, ikke i eierskap. Raden
                 STÅR, med «ikke oppgitt av kilden» i eiercellen.
    IKKE DER     tillatelsen finnes ikke i akvakultur. Ingen rad.

Fire krav, og hvert av dem er der fordi alternativet er en stille løgn:

1. **Raden står.** En utelatt rad gjør fraværet usynlig, og
   `tillatelser_antall` på samme side ville motsagt tabellen.
2. **Samme tabell.** En egen tabell for de ugjorte rede for gjør fraværet
   til noe man kan overse.
3. **Cellen har en VERDI, ikke tom streng.** «ikke oppgitt av kilden» er
   et svar; en tom celle lar leseren gjette. Samme skille som
   `INGEN_VERDI` gjør for et lusetall som ikke er rapportert.
4. **Tallene og GRUNNEN står i captionen.** «For 2 av 14 tillatelser vet
   vi ikke hvem eieren er» — og hvorfor. En leser som ser ett navn av
   fjorten skal ikke måtte lure på om resten er en feil hos oss.

### Merkingen er `eier_ukjent`, ikke `eier_navn`

Verdien i cellen er VÅR setning om fravær, ikke et navn fra kilden.
Merket den `data-felt="eier_navn"`, ville publiseringsvakten lett etter
«ikke oppgitt av kilden» i hvitelista over navn og meldt den som
`ukjent_navn` — et funn om vår egen forklaring. `eier_ukjent` står ikke i
`NAVNEFELT`, og porten går derfor forbi den. Håndhevet av
`test_ukjent_eier_merkes_med_ET_ANNET_FELT_enn_eier_navn`.

## 4. Hva regelen IKKE kan i dag

**Den kan ikke si hvilken av de to grunnene som gjelder for en gitt
tillatelse.** Snapshotet inneholder ikke de filtrerte radene i det hele
tatt, så generatoren kan bare se at nummeret mangler — ikke hvorfor.
Captionen oppgir derfor begge grunnene.

Å gjøre det presist per tillatelse krever at kilden STEMPLER grunnen —
`sources/eierskap.py` vet hvilken av de to som slo til, i det øyeblikket
den filtrerer. Det er regel 1b-3: verdien som avgjør hva dataene betyr,
lagres sammen med dem. Et felt som `eier_utelatt_grunn` på en rad
`eierskap` likevel skriver, eller en egen aggregat-rad per lokalitet,
ville lukket det. **Ikke bygget i dag**, fordi det er en kildeendring med
sin egen måling, og fordi de 55 uansett ikke kan navngis.

## Hva som ville snudd regelen

- **At Fiskeridirektoratet begynner å oppgi organisasjonsnummer for de
  55.** Da er de ikke privatpersoner lenger, eller kilden har endret
  personvernpraksis. Første ledd ville løst 55 av 84; andre ledd (de 29
  uten kjent type) står uansett.
- **At `/entities` blir komplett.** De 29 er der fordi eieren ikke finnes
  i entitetslista. En kilde til historiske og oppløste selskapsformer —
  samme tråd som `2026-09-02-eierskapshistorikk-backfill.md` peker på for
  de 677 overføringene — ville gjort typen kjent og sluppet dem gjennom
  på ordinært vis.
- **At andelen vokser vesentlig.** 84 av 2989 er 2,8 %. Blir det 30 %, er
  «eier ukjent» ikke lenger et unntak en caption kan forklare, og da er
  spørsmålet om eierskapstabellen i det hele tatt skal stå på en
  lokalitetsside — ikke hvordan fraværet formuleres.
- **At noen leser captionen som at TILLATELSEN er usikker.** Den er ikke
  det: tillatelsen er aktiv og verifisert hos kilden. Er ordlyden
  misforståelig, skal den skrives om — teksten er fri, regelen er ikke.

**Ville IKKE snudd den:** at tabellen blir lengre eller mindre pen av
rader uten eier. En side som viser fjorten tillatelser og navngir én, har
sagt noe sant. En side som viser én, har ikke.
