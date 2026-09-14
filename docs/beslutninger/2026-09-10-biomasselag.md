---
dato: 2026-09-10
tittel: Biomasselaget som kilde — ja/nei per lokalitet, fordi antallet aldri blir åpent
status: utkast
commit:
---

## Hva som ble bestemt

`sources/biomasselag.py` henter Fiskeridirektoratets Biomasse-lag
ukentlig: **står det fisk på lokaliteten, og hvilken art**, ved siste
innsendte månedsrapport fra oppdretter.

**1127 rader, 1117 lokaliteter**, målt 10.09.2026. Ett snapshot per uke,
`observed_at` = kjøredato. Kilden kjøres av `run.py` sammen med
`akvakultur`.

## Hvorfor ja/nei er verdt å samle når antallet aldri blir tilgjengelig

Biomassedatabasen etter **akvakulturdriftsforskriften § 44** — antall
fisk og biomasse per anlegg per måned — er børssensitiv og ikke
offentlig. **Bekreftet av Havforskningsinstituttet 09.09.2026.** Vi får
aldri `N_fisk` per lokalitet, og det er ikke en tilgang som kan
forhandles fram med et bedre argument.

Det stengte er MENGDEN. Ja/nei er ikke stengt, og det er publisert i et
lag ingen later til å bruke som tidsserie. Tre grunner til at det holder:

1. **Det er HIs eget kriterium for «aktivt anlegg».** Fram til i går
   kunne vi ikke etterprøve det: `lusetall.brakklagt` var den eneste
   proxyen vi hadde, og en proxy kan ikke kontrollere seg selv. Nå
   finnes to uavhengige felter som skal måle det samme. Kontrollen under
   viser at de er uenige om 102 lokaliteter, og den uenigheten er selve
   gevinsten — den var usynlig med ett felt.
2. **Ja/nei per lokalitet slår aggregert mengde per område** for det
   meste vi vil spørre om. `biomasse` (den andre kilden, ikke denne) har
   antall fisk, men bare per produksjonsområde per måned. Å vite HVILKE
   lokaliteter som stod med fisk er en finere oppløsning enn den, selv
   uten et tall.
3. **Arten er med, ordrett.** Laks, Regnbueørret, Torsk, Kveite, Røye.
   Torskeoppdrettet er i en oppbyggingsfase der hvem som står med torsk
   HVOR er et spørsmål i seg selv.

## Verdien er null i dag og vokser med kalendertid

Laget bærer **én tilstand**: siste innsendte rapport per lokalitet. Det
finnes ingen `?dato=`-parameter, ingen historisk API-variant og ingen
arkivkopi hos Fiskeridirektoratet. Forrige ukes tilstand finnes ikke noe
sted etter at den er overskrevet.

Et snapshot herfra er derfor verdiløst alene. To snapshots er en
endring. Hundre er en serie ingen andre har, om hvilke lokaliteter som
stod med fisk uke for uke — og den serien kan ikke kjøpes, hentes eller
rekonstrueres i ettertid, uansett budsjett.

Dette er begrunnelsen hele prosjektet hviler på (CLAUDE.md regel 5), og
den står eksplisitt her fordi den vanligvis er implisitt. For de fleste
kildene er den et argument om prioritering: en uke uten innsamling er en
uke tapt historikk, men grunnserien overlever. For denne kilden er den
**hele kilden**. Det finnes ingenting annet her enn tid.

Konsekvensen er en rangering som ellers ville sett feil ut: denne kilden
ble bygget før Vannmiljø, før analysearbeid og før forbedringer av det
som allerede virker. Ikke fordi den er viktigst, men fordi den er den
eneste som blir dårligere av å vente.

## Laget, målt før noe ble bygget

    https://gis.fiskeridir.no/server/rest/services/
        Yggdrasil/Biomasse/MapServer/0/query

Funnet ved å liste tjenestekatalogen (`Yggdrasil?f=json`), ikke ved å
konstruere en URL fra antakelse. Samme katalog og samme vilkår som
`romming`.

| | |
|---|---|
| autentisering | **ingen** |
| `copyrightText` | Fiskeridirektoratet — NLOD, attribusjon er vilkår |
| rader | **1127** i ett kall (`exceededTransferLimit` ikke satt) |
| lokaliteter | **1117** — ti har to arter |
| `maxRecordCount` | 2000 (vi ber om 1000 og pagineres) |
| `status_lokalitet` | **AKTIV på alle 1127** |
| `Last-Modified` | **sendes ikke** |
| geometri | punkt; hentes ikke |

Tjenestens egen beskrivelse, ordrett: «Viser status (om det stod fisk og
hvilken art) på lokalitet ved siste innsendte månedsrapport fra
oppdretter.»

Verdiene, alle som forekommer 10.09.2026:

| `har_fisk` | `art` | n |
|---|---|---|
| Ja | Laks | 548 |
| Nei | (null) | 487 |
| Ja | Regnbueørret | 54 |
| Ja | Torsk | 20 |
| Ja | Kveite | 17 |
| Ja | Røye | 1 |

`har_fisk = "Nei"` medfører `art = null`, uten unntak.

## Beslutning 1: artene slås sammen, NOKKEL utvides ikke

Laget har én rad per *(lokalitet, art)*. Ti lokaliteter har to arter —
9 × (Laks, Regnbueørret) og 1 × (Kveite, Torsk) — og de doble radene er
kontrollert felt for felt **identiske i alt unntatt `art`**.

`snapshot.NOKKEL` er `(entity_id, field, source)`. Med `loknr` som
entitet og `art` som felt ville den ene arten falt bort i
`unique(keep="first")` — **uten feilmelding**. Det er samme feilklasse
som F14 og som Områdene?-treffet: en mekanisme som er riktig i akkurat
de tilfellene der to ting faller sammen, og stille når de ikke gjør det.
Her ville den vært riktig for 1107 lokaliteter og feil for ti.

To utveier ble vurdert:

**Utvide NOKKEL med et fjerde ledd.** Forkastet. Nøkkelen bærer
`diff.compare()`, `diff.revisjon()`, `changelog.les_alt()` og hele
historikken som allerede er skrevet. Å endre den for én kildes skyld er
nøyaktig det CLAUDE.md regel 1 forbyr — og den ville kostet en migrering
av alt som finnes, for å løse et problem ti rader har.

**Slå artene sammen til én verdi.** Valgt.

    arter_tilstede  "Laks;Regnbueørret"     sortert, kildens verdier
    antall_arter    "2"

Sorteringen er ikke kosmetikk: uten den ville en omstokking hos
tjenesten sett ut som en endring i changeloggen. `antall_arter` står ved
siden av fordi en leser da slipper å parse strengen for å telle, og
fordi en lokalitet som går fra én til to arter blir en synlig hendelse
på et felt som er et tall.

Separatoren `;` er VÅR. Verdiene på hver side er kildens, ordrett — og
ingen av de fem artsnavnene inneholder tegnet, så `value.split(";")`
reverserer sammenslåingen fullstendig. Ingenting forsvinner stille, og
ingenting normaliseres: «Ja»/«Nei» blir ikke bool, og artsnavnene blir
ikke egne kategorier. Skifter Fiskeridirektoratet fra «Regnbueørret» til
«Regnbueaure», er det en endring vi vil SE i changeloggen — ikke noe en
oversettelsestabell skal spise.

## Beslutning 2: `siste_rapport` er IKKE `observed_at`

Dette var det viktigste spørsmålet, og svaret er motsatt av det
førsteinntrykket.

`siste_rapport` er et ekte `esriFieldTypeDate`, og det så ut som en
gyldighetsdato. Det er det ikke: **feltet er per rad, ikke per lag.**
Målt over alle 1127 rader er det **112 distinkte verdier, fra
2005-04-30 til 2026-08-31**. Det sier når DEN lokaliteten sist sendte
månedsrapport — ikke hvilken måned laget som helhet gjelder for.

To ting følger, og bare det andre er åpenbart:

1. Det finnes ingen felles dato å sette. Feltet brukt som `observed_at`
   ville gitt 112 snapshots per henting og brutt `run.py`s invariant om
   ett snapshot per kilde per kjøring — den invarianten som bærer
   frekvensvakten, `finnes_allerede()` og feilisoleringen.
2. Verre: det ville vært en **oppdiktet proveniens**. Raden med
   `siste_rapport = 2010-01-31` er ikke en observasjon vi gjorde i 2010.
   Den er en påstand laget gjør I DAG om at siste rapport kom i 2010.
   `observed_at = 2010-01-31` ville sagt at vi så dette i 2010.

Valgt: `observed_at` = kjøredato. `siste_rapport` bæres som felt per
rad, og `dato_forbehold` sier på hver eneste rad at datoen er
hentetidspunkt og ikke rapporteringstidspunkt (CLAUDE.md 1b-3). Alderen
på hver påstand blir da et regnestykke en leser kan gjøre av raden
alene: `observed_at − siste_rapport`.

`published_at` settes **ikke**. Verten sender ingen `Last-Modified` —
bare `etag: "c5b049c3"`, som ikke er et tidspunkt. Etter 1b-7 er
standarden «vet ikke», aldri hentetidspunktet. Headeren leses likevel i
tilfelle tjenesten begynner å sende den; den utledes bare ikke.

## Beslutning 3: feltlåsen mot arkivet

Vi ber om en eksplisitt feltliste (`outFields=objectid,loknr,...`), ikke
`outFields=*`.

Laget har i dag **ingen persondata** — ingen innehaver, ingen adresse,
ingen fritekst. Det er lest fra tjenestens egen metadata, ikke fra
dokumentasjon, og det er den motsatte situasjonen av `romming`. Låsen
finnes likevel, fordi rå-arkivet ligger i git og er append-only: et felt
Fiskeridirektoratet legger til i morgen ville med `*` havnet i arkivet
før noe menneske hadde sett det, og der kan det ikke fjernes igjen.

Prisen er at et nytt og NYTTIG felt blir usynlig. Den prisen betales
ikke: `fetch()` leser lagets feltliste ved hver henting og **advarer**
om felter tjenesten har som vi verken henter eller har valgt bort. Da
ser vi endringen uten å arkivere den.

## Beslutning 4: syv felter hentes ikke, fordi de er FRYST

`fylke`, `kommune`, `kapasitet_lok`, `aktuell_kapasitet`, `plassering`,
`vannmiljo` og `produksjonsomraade` finnes alle fra før i `akvakultur`.
Vanlig begrunnelse ville vært `romming`s: to kilder til samme opplysning
er to tellere for samme sak.

Her er begrunnelsen sterkere, og den er målt. **Hele raden er fryst ved
siste rapport, ikke bare fiskestatusen.** Fylkesnavnet «TROMS OG
FINNMARK» — et fylke som opphørte 01.01.2024 — står på **18 rader**.
Alle 18 har `har_fisk = "Nei"`, og alle har `siste_rapport` i 2023 eller
tidligere. «VIKEN», som opphørte samme dag, står på én. De 193 radene
med «TROMS» eller «FINNMARK» har rapporter helt fram til 2026.

Hentet vi `fylke` herfra, ville vi altså skrevet ned et fylke som ikke
finnes, for lokaliteter `akvakultur` har det riktige fylket for. Det er
ikke duplisering — det er en dårligere kopi.

## Kontrollen: laget mot `lusetall.brakklagt`

Biomasselaget hentet 10.09.2026, mot lusetall uke `2026-08-03` (den
ferskeste vi har; lusetall har fire ukers etterslep). 1073 felles
lokaliteter.

| | n | |
|---|---|---|
| `brakklagt=True` & `har_fisk=Nei` | 418 | enige — tom |
| `brakklagt=False` & `har_fisk=Ja` | 553 | enige — fisk |
| `brakklagt=True` & `har_fisk=Ja` | **77** | uenige — laget sier fisk |
| `brakklagt=False` & `har_fisk=Nei` | **25** | uenige — laget sier tomt |

**971 av 1073 = 90,5 % enige. 102 uenige, og uenigheten er skjev: tre
ganger så mange i retning «laget ser fisk der lusetall ser brakklegging».**

Tallet er ikke utlignet og ingen vinner er kåret. Men spriket er testet
mot ni lusetallsuker for å skille TID fra ekte uenighet:

| lusetallsuke | enige | laget-fisk / lus-brakk | lus-drift / laget-tom |
|---|---|---|---|
| 2026-06-08 | 80,4 % | 128 | 83 |
| 2026-06-29 | 85,9 % | 97 | 54 |
| 2026-07-20 | 90,9 % | 73 | 25 |
| 2026-07-27 | **91,2 %** | 74 | 20 |
| 2026-08-03 | 90,5 % | 77 | 25 |

Enigheten stiger monotont mot den ferskeste uka og **flater ut rundt
91 %**. De resterende ~9 % er altså ikke et tidsartefakt. To felter som
skal måle det samme er uenige om omtrent hundre lokaliteter, og det
tallet står som et funn — ikke som noe som skal forklares bort.

## Funn: «Ja» er nåtid, «Nei» er det ikke

Alderen `2026-09-10 − siste_rapport` i måneder, over de 1117:

| | n | median | >3 mnd | >12 mnd | >60 mnd | maks |
|---|---|---|---|---|---|---|
| alle | 1117 | 2,0 | 34,6 % | 17,8 % | 7,2 % | 257 |
| `har_fisk=Ja` | 630 | 2,0 | **1,1 %** | 0,0 % | 0,0 % | 10 |
| `har_fisk=Nei` | 487 | 9,0 | **78,0 %** | 40,9 % | 16,4 % | 257 |

De to halvdelene er ikke samme slags påstand:

- **`har_fisk = "Ja"`** er fersk. 623 av 630 innen tre måneder, ingen
  eldre enn ti. En påstand om nåtid.
- **`har_fisk = "Nei"`** er en **absorberende tilstand**. Fire av ti er
  over et år gamle, én av seks over fem år, den eldste fra 2005-04-30.
  Meldeplikten i § 44 følger fisken: en lokalitet som tømmes slutter å
  rapportere, og raden fryser på siste melding om at det var tomt.

Dette endrer hva kilden kan brukes til, og det er derfor det står her og
ikke bare i koden. **`har_fisk = "Nei"` betyr ikke «tom nå». Den betyr
«ikke meldt fisk siden `siste_rapport`».** En telling av tomme
lokaliteter som ikke leser `siste_rapport` ved siden av, teller feil.

For `har_fisk = "Ja"` gjelder forbeholdet knapt: laget ER et bilde av
nåtid for den halvdelen, og det er den halvdelen HIs kriterium for
«aktivt anlegg» handler om.

Merk hvordan dette farger kontrollen over: av de 25 der lusetall ser
drift og laget sier tomt, er medianalderen 4 måneder — det er
sannsynligvis etterslep. Av de 77 i motsatt retning er medianalderen
**1 måned**. De er ferske, og de er ekte uenighet.

## De 43 uten treff i `akvakultur` — forklart

43 av 1117 `loknr` finnes ikke i akvakultursnapshotet fra 2026-08-31
(1074 av 1117 = 96,2 % treff). De er ikke tilfeldige:

**Alle 43 har `har_fisk = "Nei"` og `art = null`**, alle er `SALTVANN`,
42 av 43 `SJØ`, og `siste_rapport` spenner 2011–2025 med tyngdepunkt
2016–2022. Ti av dem mangler produksjonsområde helt.

Forklaringen i én setning: **det er lokaliteter som er ute av
Akvakulturregisteret — tillatelsen er bortfalt eller trukket — men som
biomasselaget fortsatt bærer, fryst på siste rapport, med et
`status_lokalitet = "AKTIV"` som er like foreldet som resten av raden.**

Det samme fryste fylkesnavnet bekrefter det: 18 av de 19 radene med et
opphørt fylkesnavn har `har_fisk = "Nei"`. Tre av de 43 har dessuten et
`navn` som finnes i akvakultur under et ANNET lokalitetsnummer (HELLAREN
10194 mot 11335, JUVIKA 12260 mot 29656, KVITNESET 12727 mot 10872) —
lokaliteter som er reetablert under nytt nummer, der laget beholdt den
gamle raden.

Konsekvens: `status_lokalitet` fra denne kilden er ikke en gyldig kilde
til om en lokalitet er aktiv. Det er `akvakultur`. Feltet lagres likevel,
fordi det er lagets egen påstand og fordi endringer i den er verdt å se.

## De fire i 12D

Uavhengig belegg for spørsmålet stilt til HI 09.09.2026. Biomasselaget
hentet 10.09.2026, lusetall uke 2026-08-03:

| loknr | navn | `har_fisk` | `art` | `siste_rapport` | lusetall `brakklagt` | `har_laksefisk` |
|---|---|---|---|---|---|---|
| 13143 | BONDEJORDA | **Ja** | Laks | 2026-08-31 | False | True |
| 13337 | HOVDENAKKEN | **Ja** | Laks | 2026-08-31 | False | True |
| 13813 | KVITELV | **Ja** | Laks | 2026-08-31 | False | True |
| 34697 | ØYRA | **Ja** | Laks | 2026-08-31 | False | True |

Alle fire står med laks, alle fire rapporterte for august 2026, og
**begge kildene er enige om alle fire**. Det er uavhengig belegg: laget
og lusetall er ulike innrapporteringsløyper (§ 44 via Altinn mot
BarentsWatch fiskehelse), og de faller ikke sammen andre steder — de er
uenige om 102 lokaliteter.

## Reverseringskriterier

**1. Fiskeridirektoratet publiserer historikken selv.** Da er kilden
overflødig fra publiseringsdatoen og framover, og vår serie blir en
kontroll mot deres. Den blir ikke verdiløs — vår serie starter
10.09.2026, deres starter der de velger — men innsamlingen kan legges
ned. *Prøve:* et endepunkt med en datoparameter, eller en nedlastbar
fil med `siste_rapport` per måned bakover.

**2. Laget slutter å oppdateres.** Da samler vi kopier av en frossen
tilstand og bruker et HTTP-kall i uka på ingenting. *Prøve:* ingen rad
får ny `siste_rapport` på tre påfølgende måneder. Merk at det ikke kan
måles på antall rader eller på `etag` — bare på om det NYESTE
rapporttidspunktet i laget flytter seg. Dette bør bli en vakt, og det er
ikke bygget ennå.

**3. § 44-databasen åpnes.** Da får vi antall fisk per lokalitet per
måned, og ja/nei er en avledning av det. Kilden legges ned samme dag —
men snapshotene beholdes: de bærer perioden før åpningen, og den
kommer ikke tilbake. *Prøve:* Fiskeridirektoratet eller HI publiserer
`BEHFISK_STK` på lokalitetsnivå.

Det som IKKE reverserer beslutningen: at kontrollen mot `brakklagt`
viser 9 % uenighet. Uenigheten er en grunn til å ha begge felter, ikke
en grunn til å velge ett.

## Det som ikke er gjort

- **Ingen vakt på at laget fortsatt oppdateres.** Reverseringskriterium
  2 er formulert, men ikke implementert. Kilden advarer i dag om nye
  feltverdier, nye felter og tomt svar — ikke om et lag som står
  stille. Det bør bygges før det trengs.
- **De 102 uenige lokalitetene er ikke undersøkt enkeltvis.** Tallet er
  målt og retningen er kjent; hvorfor de spriker er ikke.
- **`siste_rapport` er ikke koblet mot `biomasse`-kildens måneder.** De
  to burde kunne kontrollere hverandre på om en måned er komplett.
