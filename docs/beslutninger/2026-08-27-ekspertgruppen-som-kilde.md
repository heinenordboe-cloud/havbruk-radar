---
dato: 2026-08-27
tittel: Ekspertgruppen er en kilde, ikke en fasitfil — og dekningsgevinsten ga ikke styrke
status: gjeldende
commit: [fylles inn]
---

## Hva som ble bestemt

Ekspertgruppens vurderinger hentes som en KILDE med samme kontrakt som
biomasse, lusetall og sjøtemperatur: rå-arkiv før parse, `raw_hash` per
observasjon, `published_at` lest av kroppen, revisjonsakse.
`sources/ekspertgruppen.py`, fem rapportkropper 2016–2022.

Den håndskrevne `analyse/fasit/ekspertgruppen-po-kategori.csv` beholdes,
men degraderes: den er nå en annen slags påstand enn kilden, og de to
holdes fra hverandre. Se «Fasiten beholdes» under.

**Og — dette er notatets tyngste punkt — dekningsgevinsten ga ikke
statistisk styrke.** Se «Hvorfor 13 celler flere ikke er 13 celler
flere».

## Hvorfor kilden måtte bygges

Fasiten hadde ingen proveniens. Et snapshot kunne fortelle hva vi
FANT, men ikke hvilket dokument det kom fra, hvilken side, eller når
dokumentet ble utgitt. Det er CLAUDE.md 1b-3 i måltallet: en verdi
utenfor dataene avgjorde hva de betyr, uten spor av hvor den kom fra.

Kontrollen som falt ut av arbeidet er verdt å notere: **håndfasiten og
maskinuttrekket er identiske på alle 39 cellene der begge har en verdi.**
Fasiten var altså riktig. Problemet var aldri tallene — det var at ingen
kunne etterprøve dem.

## Tre ting som ble målt, ikke antatt

### `published_at` leses av `/CreationDate`, ikke av `Last-Modified`

Biomasse tar `published_at` fra `Last-Modified`, som Fiskeridirektoratet
setter presist. Her er den samme headeren en CMS-migreringsdato, målt på
to uavhengige verter og tre kropper: hi.no sier 05.08.2022 om en rapport
fra november 2020, trafikklyssystemet.no sier 10.03.2022 om rapporter fra
oktober 2017 og november 2018 — de to siste tjue minutter fra hverandre.

Brukt som `published_at` ville den datert 2017-rapporten til 2022 og lest
revisjonsaksen baklengs for hele serien.

**Wayback løser ikke dette.** `X-Archive-Orig-Last-Modified` bevarer
opphavets header, og opphavets header er migreringsdatoen. Arkivet gir
tilgang til 2021- og 2022-kroppene som regjeringen.no nekter oss; det gir
ikke proveniens. Det var en feilslutning i første utkast til inventaret,
og den ble rettet før den kom inn i koden.

### Én uttrekksfunksjon per rapportår

Rapportene er fem forskjellige dokumenter. 2018 er 27 sider uten
modellavsnitt og med usikkerhet kodet som CELLEFARGE. 2020 er 107 sider
med metodetabell og utvandringsvindu. 2022 la om til SHELF-elisitering og
har ingen metodetabell i det hele tatt.

En generisk parser over den spredningen gir riktig FORM og feil TALL —
prosjektets egen feilklasse (1b-2). `parse()` nekter å emittere for et år
ingen skrevet funksjon dekker.

### Utvandringsvinduet er datoer, og finnes i én av fem rapporter

Bare 2020-rapporten oppgir det per produksjonsområde, som datoer med
uketall bare for medianen. Uketallet for start og slutt er VÅR avledning
og er årsavhengig. De øvrige rapportene har det ikke: 2016/17 brukte et
standardisert 40-dagersvindu, 2018 og 2021 sier ingenting, 2022 gir
verbale perioder.

Det bekrefter forbeholdet i notatet fra 26.08: det faste uke 16–24 var
systematisk feil i nord, og det kan bare rettes for ett av årene.

## Revisjonsaksen svarte, og svaret var et tredje alternativ

12 revisjonsrader, alle for 2020, mellom 2020- og 2021-rapporten.
Spørsmålet var om rapportene skiller seg på KATEGORIEN eller bare på de
kontinuerlige estimatene. Svaret er ingen av delene: **de skiller seg på
metodenes egne kategorier og usikkerheter.** Hovedkonklusjonen er uendret
for alle tretten produksjonsområder.

Kontrollen som gjør dette troverdig: 2021-rapporten beskriver selv, i
prosa, nøyaktig hvilke metodevurderinger som ble endret — og hver eneste
av dem ligger i changeloggen, mens ingenting annet gjør det. Rapportens
egen tekst er fasit for maskinuttrekket.

## Hvorfor 13 celler flere ikke er 13 celler flere

Dette er notatets viktigste ledd, og det peker motsatt vei av det man
skulle tro.

| | gammel fasit | ny kilde |
|---|---|---|
| år | 2020–2024 | 2016–2018, 2020–2022 |
| (po, år)-celler | 65 | **78** |
| **ettårsoverganger** | **52** | **52** |
| **kategoriskift** | **11** | **13** |

Cellene økte med 20 %. **Overgangene økte ikke i det hele tatt**, og
skiftene bare fra 11 til 13.

Grunnen er at de nye årene ligger i en EGEN BLOKK, atskilt fra de gamle
av 2019-hullet:

    2016 - 2017 - 2018 |  (2019 mangler)  | 2020 - 2021 - 2022
      \____ 26 ____/                        \____ 26 ____/

To blokker à tre år gir 2 × 13 = 26 overganger hver, altså 52 — nøyaktig
det samme som fem sammenhengende år ga. Et år lagt til inne i en blokk
gir 13 nye overganger; et år lagt til som starten på en ny blokk gir 0.
Vi la til tre år og fikk én ny blokk.

I tillegg finnes 13 toårshopp 2018→2020, hvorav **2 er kategoriskift**.
De må telles for seg: 2018→2020 er ikke et ettårig skifte, og å slå dem
sammen med de 52 ville påstått en persistens over ett år som ikke er
målt.

Og biomasse begrenser videre: serien begynner 2017-10, så full
Stien-proxy kan ikke strekkes til 2016 i det hele tatt, og 2017 er
delvis — utvandringsvinduet (april–juli) ligger før seriens start. Reelt
proxy-dekkede år er 2018, 2020, 2021, 2022.

**Konklusjonen er ubehagelig og skal stå rett ut: å bygge kilden ga
proveniens, etterprøvbarhet og revisjonshistorikk, men det ga
IKKE statistisk styrke.** Måltallet har 13 bevegelser der det før hadde
11. Bindingen fra notatet 26.08 — at 11 skift ikke kan skille +0,64 fra
+0,76 fra myntkast — er ikke løsnet.

## Det kontinuerlige utfallet finnes ikke i disse rapportene

Notatet fra 26.08 pekte på et kontinuerlig dødelighetsestimat som den
store styrkegevinsten: «65 celler med et kontinuerlig utfall er en langt
større styrkegevinst enn noen prediktorforbedring.»

**Det premisset holder ikke.** Målt over hele flaten — hver rapport, hvert
felt, hvert produksjonsområde:

| felt | celler | ettårsoverganger |
|---|---|---|
| **kategori** | **78** | **52** |
| HI smittepress ROC | 22 | 11 |
| VI virtuell smolt | 18 | 8 |
| SINTEF virtuell smolt | 16 | 10 |
| arealandel over terskel | 15 | 2 |
| HI virtuell smolt vektet/uvektet | 4 / 4 | 0 |

Ingen av de fire modellene gir et kontinuerlig utfall med flere brukbare
celler enn kategorien. Det største har under en tredjedel.

Og de kan ikke legges sammen: ingen av dem dekker de samme årene. HI
virtuell smolt — den 26.08-notatet navnga eksplisitt — oppgir årets
vektede og uvektede snitt for 4 av 13 produksjonsområder i ett år. De ni
andre oppgir SERIENS spenn over 2012–2020, som er en annen størrelse om
et annet tidsrom.

## STOPPREGEL

*Skrevet 27.08.2026, FØR utfallet av de to gjenstående trådene er kjent.
Den står her fordi en stoppregel som skrives etter at man har sett
resultatet, ikke er en stoppregel.*

> **Gir verken arealandel/ROC-sammenslåingen eller HIs modellrapporter et
> kontinuerlig utfall med minst 25 ettårsoverganger, er
> prediksjonshypotesen ferdig testet. Den legges da bort som et
> dokumentert nullresultat med angitt grunn: måltallet har for få
> bevegelser, og de offentlige rapportene inneholder ikke et finere.
> Prosjektet svinger til beskrivelse.**

De to trådene, og hvorfor akkurat de:

1. **Er «arealandel over terskel» (2020) og «HI smittepress ROC»
   (2021–2022) samme størrelse under to navn?** Er de det, er det 35
   celler og opptil 22 ettårsoverganger av et kontinuerlig utfall. De er
   lagret som to felt fordi ordlyden er ulik og ingen rapport definerer
   dem mot hverandre (regel 4). Spørsmålet avgjøres ved å lese
   definisjonene i rapportene, ikke navnene.
2. **Tabellerer HIs egen serie «Rapport fra havforskningen» per-PO-
   estimater over 2012–2025?** Den er en ANNEN serie enn ekspertgruppens
   og er ikke undersøkt.

Terskelen på 25 er valgt mot det som allerede er målt, ikke mot et ønske:
kategorien har 52 overganger og 13 skift, og et kontinuerlig utfall med
under halvparten av kategoriens overganger vil ikke kunne bære et
måltall kategorien selv ikke bærer. Den er heller ikke satt så høyt at
bare et perfekt datasett passerer — 25 er under det arealandel+ROC ville
gitt hvis de er samme størrelse.

## Fasiten beholdes, men degraderes

`analyse/fasit/ekspertgruppen-po-kategori.csv` slettes ikke. Den har 2023
og 2024, som kilden ikke har.

De to er nå ULIKE SLAGS PÅSTANDER og skal ikke blandes:

- kilden bærer dokument, sha256, `published_at`, lesemåte per celle
- fasiten bærer et menneskes lesing uten sporbart dokument

Enhver analyse som bruker 2023–2024 må si det i kjøringsloggen, på samme
måte som den må si at en celle er uverifisert.

**2023–2025 er tapt inntil innsynskravet lander.** Rapportene finnes —
2023 er sitert som Vollset mfl. 2023, 2024 ble levert NFD i juni 2025,
2025 i desember 2025 — men bare vedleggene ligger åpent, og
regjeringen.no svarer 403 på både artikkelsider og PDF-er for oss.

2019 er en ANNEN sak og skal ikke slås sammen med dem:
trafikklyssystemet.no har en årstallsoverskrift «2019» med tomt innhold.
Vi vet ikke om rapporten finnes. **Ubesvart spørsmål, ikke bekreftet
fravær.**

## [din vurdering]

Fire spørsmål notatet ikke avgjør:

1. **Er `/CreationDate` god nok proveniens?** Den er lest fra dokumentet,
   ikke gjettet, men den er eksporttidspunktet — ikke en utgivelsesdato
   noen har gått god for. Alternativet er tom `published_at` for alle
   fem, og da kan revisjonsaksen ikke ordne kroppene i det hele tatt.
   Valget som er tatt er å bruke den MED en vakt mot re-eksport; det kan
   overprøves.
2. **Skal fasitens 2023–2024 stå i det hele tatt?** Å beholde dem er å ha
   to fasiter med ulik proveniens side om side, med den risikoen det
   bærer. Å slette dem er å miste to årganger og fire ekstra
   ettårsoverganger til innsynskravet lander.
3. **Skal innsynskrav sendes?** Rapportene er offentlige utredninger
   levert et departement. Et innsynskrav mot NFD ville trolig gi 2023,
   2024 og 2025, og dermed 39 celler til — men de ville ligget i en TREDJE
   blokk atskilt fra 2016–18 og 2020–22, så gevinsten i overganger er
   26, ikke 39.
4. **Skal 2022-rapportens sannsynlighetsfordeling trekkes ut?** Rikere
   enn kategorien, men finnes bare fra 2022 og ville gitt et felt med ett
   års historikk.

## Hva som ville snudd dette

- Et kontinuerlig utfall med minst 25 ettårsoverganger fra en av de to
  trådene i stoppregelen
- 2019-rapporten dukker opp, og de to blokkene blir én — det ville gitt
  26 ekstra ettårsoverganger, ikke 13, fordi hullet lukkes fra begge
  sider
- Innsyn i 2023–2025 kombinert med 2019, som ville gitt én sammenhengende
  serie 2016–2025 med 117 celler og 104 ettårsoverganger

Merk at de tre er svært ulikt sannsynlige, og at bare den første er
gratis.

## Kjøringen posten hviler på

`backfill.py --kilde ekspertgruppen --rapporter`, 27.08.2026. Fem kropper
arkivert i `data/arkiv/ekspertgruppen/` med verifiserte sha256, seks
snapshots, 12 revisjonsrader. Testsuiten grønn på 482.

Dekningsflaten er målt med et engangsskript mot de arkiverte kroppene;
tallene står i `docs/KILDE-EKSPERTGRUPPEN.md` punkt 5 og kan
reproduseres derfra.
