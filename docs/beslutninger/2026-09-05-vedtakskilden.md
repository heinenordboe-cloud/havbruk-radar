---
dato: 2026-09-05
tittel: Vedtaket hentes som kilde — og koblingen mellom råd og farge finnes ikke i regelverket
status: gjeldende
commit: [fylles inn]
---

## Hva som ble bestemt

Departementets FARGE per produksjonsområde per tildelingsrunde hentes
som en KILDE med samme kontrakt som ekspertgruppen:
`sources/trafikklysvedtak.py`, fire forskriftskropper fra lovdata.no,
rå-arkiv før parse, `published_at` lest av kroppen, én uttrekksfunksjon
per forskriftsår.

**Og — dette er notatets tyngste punkt — sammenstillingen mot
ekspertgruppens råd STOPPER før treffraten.** Se «Stoppregelen slo inn».

## Hvorfor kilden måtte bygges

`sources/ekspertgruppen.py` har den ene siden av trafikklyssystemet:
hvilken risikokategori ekspertgruppen setter. Den andre siden — hva
departementet faktisk vedtok — fantes ikke i repoet i det hele tatt.
Uten den kan ingen spørre om vedtaket følger rådet.

Kilden er bygget etter samme mønster som ekspertgruppen fordi kilden har
samme form: N kropper som hver dekker M perioder og som uttaler seg om
hverandres perioder. 2024-forskriftens § 4-tabell skriver
«Produksjonsområde 3 (gult lys i 2020, rødt lys i 2022, rødt lys i
2024)» — én rad, tre påstander, om tre ulike runder.

## Stoppregelen slo inn

Oppdraget hadde en uttrykkelig stoppregel: koblingen mellom
ekspertgruppens RISIKONIVÅ og forskriftens FARGE skulle finnes i
regelverket, dokumenteres med kildehenvisning, og hvis den ikke var
entydig definert, skulle det sies og arbeidet stanses.

**Den er ikke definert.** Målt 05.09.2026 på både den opprinnelig
kunngjorte (LTI) og den gjeldende (SF) teksten av
produksjonsområdeforskriften (FOR-2017-01-16-61): ordene «dødelighet»,
«grønn», «rød», «trafikklys», «risiko» og «ekspertgruppe» forekommer
**null ganger**, og forskriften inneholder ingen prosentterskler.

Kjeden er halvt definert:

* **Farge → miljøstatus → konsekvens ER definert.** § 8 annet ledd:
  «Departementet vurderer om miljøpåvirkningen i et produksjonsområde er
  akseptabel, moderat eller uakseptabel», og §§ 9/10/11 knytter
  nedjustering, uendret og vekst til hver av de tre. Fargenavnene står
  ikke i forskriften, men departementet navngir dem selv i
  høringsnotatet 19.06.2026: «Er miljøpåvirkningen akseptabel (grønn) …
  moderat (gul) … uakseptabel (rød) …».

* **Risikonivå → miljøstatus er IKKE definert.** Det nærmeste er
  trafikklysmeldingen (Meld. St. 16 (2014–2015)) kap. 8.3, som
  departementet siterer: «Dersom resultatet er sammenfallende begge årene
  vil utfallet være forutsigbart …». Det er en stortingsmelding, ikke et
  regelverk; den sier «forutsigbart» uten å navngi hvilken farge som
  følger av hvilken kategori; og den gjelder bare når de to
  grunnlagsårene er sammenfallende.

Og systemet sier selv at fargen ikke er en funksjon av rådet alene.
Trafikklyssystemet.no: «I tillegg gjør departementet en samlet vurdering
som også inkluderer samfunnsøkonomiske konsekvenser når Trafikklysets
farger settes.» Departementet, samme høringsnotat: «Styringsgruppen
foretar ingen slik helhetsvurdering når den gir råd til departementet,
den gir kun et faglig råd om miljøtilstanden.»

`analyse/vedtak_mot_rad.py` rapporterer derfor DEKNING og SAMFOREKOMST,
og beregner ingen treffrate og ingen avviksretning. Å oppgi «X av Y
stemmer» ville vært å oppgi et tall om en oversettelse vi selv fant på —
prosjektets egen feilklasse (CLAUDE.md 1b-2), denne gangen med en
tredjepart som gjenstand. Forbeholdene står i
`analyse/FORBEHOLD-vedtak-mot-rad.md`.

## Tre ting som ble målt, ikke antatt

### Runde 2026 har ikke noe vedtak

Trafikklyset er fargelagt i fem runder. Bare fire har en fastsatt
forskrift. Fastslått mot Lovdatas register over Norsk Lovtidend avdeling
I med syv ulike søkeord for 2026, med kontrollsøk som finner alle fire
eldre forskriftene: ingen kapasitetsjusteringsforskrift for 2026 finnes.
Departementet sendte utkastet på høring 19.06.2026 med frist 31.07.2026.

Fargeleggingen for 2026 er kunngjort i en pressemelding. Kilden leser
vedtak, ikke pressemeldinger, og runden står ikke i `FORSKRIFTER`.
Fravær framfor gjetning.

### `published_at` er ikrafttredelsen, fordi HTTP ikke har noe å tilby

Biomasse tar `published_at` fra `Last-Modified`. Ekspertgruppen kan
ikke, fordi headeren der er en CMS-migreringsdato. Her er situasjonen en
tredje: **lovdata.no sender ingen `Last-Modified` i det hele tatt** —
målt med `curl -I` på alle fire dokumentene. Det finnes ikke noe
HTTP-alternativ å ta feil av.

Det som finnes er dokumentets eget `Ikrafttredelse`-felt, og det brukes,
vaktet mot at ikrafttredelsen skiller seg fra fastsettelsesdatoen.
Alle fire passerer; vakten finnes for den femte.

Kilden leser LTI-versjonen (teksten slik den ble kunngjort), ikke SF (den
konsoliderte). 2022-forskriften er endret tre ganger etter kunngjøring.
Et vedtak er en handling på et tidspunkt, og en konsolidert tekst ville
gjort hver kropp til en bevegelig referanse — CLAUDE.md 1b-4.

### Tre lesemåter, fordi kroppene sier fargen ulikt sterkt

| kropp | fargeord |
|---|---|
| 2018 | **ingen i det hele tatt** |
| 2020 | «røde», bare i overskriften til kapittel 4 |
| 2022, 2024 | «(grønne)» i § 3 og «X lys i ÅÅÅÅ» i § 4-tabellen |

Hver farge bærer `farge__lesemaate`: `ordrett`, `kapitteloverskrift`
eller `kapittelhjemmel`. Den siste er den eneste der VI tar et steg
kilden ikke tar — grønt utledet av at området står under kapittelet som
gjennomfører produksjonsområdeforskriften § 11.

**Utledningen er etterprøvd**, og det er poenget med å skille dem: den
samme strukturelle plassen er merket «(grønne)» ORDRETT i både 2022- og
2024-kroppen, og 2020-kroppens `kapitteloverskrift`-lesning av PO4/PO5
bekreftes ordrett av «rødt lys i 2020» i begge de senere. To av to i
begge retninger.

## Dekningen

40 av 65 mulige celler (13 områder × 5 runder) har en farge: 23
`ordrett`, 17 `kapittelhjemmel`.

| runde | celler | hull |
|---|---|---|
| 2018 | 8 | PO 2, 3, 4, 5, 6 — kroppen har ingen fargeord og intet nedjusteringskapittel |
| 2020 | 12 | PO 10 — unevnt overalt |
| 2022 | 11 | PO 2, 7 |
| 2024 | 9 | PO 2, 6, 7, 8 |
| 2026 | 0 | ingen fastsatt forskrift |

**Hullene er ikke tilfeldige, og det er et funn i seg selv.** De 7
hullene i 2022 og 2024 er områder som verken står i den grønne lista
eller i § 4-tabellen — altså gule. Gule områder er de som ikke utløser
noe tiltak, og derfor de som ikke trenger å nevnes i en forskrift om
kapasitetsjustering. Et utvalg av celler med vedtak underrepresenterer
systematisk gult.

Fargen ved utelukkelse emitteres likevel ikke. Slutningen krever at
forskriften er uttømmende om farge, og 2018-kroppen viser at den ikke
trenger å være det: der er fem områder unevnt, og minst ett av dem var
ikke grønt.

## Revisjonsaksen svarte, og svaret var todelt

38 revisjonsrader ble skrevet av backfillen. **Null av dem er motstrid om
en farge:** de fire forskriftene sier aldri noe ulikt om samme
(område, runde). To rader er en ekte oppgradering av lesemåte for PO4 og
PO5 i 2020, og to er PO3 i 2020, som bare de senere kroppene bærer.

De øvrige 34 er en **usann påstand**, og det er et kjent avvik som ikke
er omgått. `diff.revisjon_mellom()` behandler en entitet som forsvinner
mellom to versjoner som en revisjon — riktig for biomasse, der en
lokalitet faktisk flyttes ut av en måned. Feil her: at 2022-forskriften
ikke gjentar PO1 for runde 2020, betyr ikke at departementet trakk
tilbake det grønne lyset, bare at § 4-tabellen har tre rader.

Rettelsen ville vært et valg mellom entitets- og feltsemantikk i
`core/diff.py`. **CLAUDE.md regel 1 sier at en kilde ikke skal be om en
endring i `core/` på egen hånd**, så avviket står målt i
`docs/KILDE-TRAFIKKLYSVEDTAK.md` punkt 9 og i kildens docstring, og
avgjørelsen er brukerens. Det er ikke datatap: changeloggen er avledet
(regel 2), begge snapshots står, og `diff.bevegelse()` filtrerer
`revidert` bort fra ukas endringstall.

Leseregelen inntil videre: gjeldende farge for (runde, PO) er den sist
utgitte raden SOM FINNES for cellen — ikke det siste snapshotet. Det er
regelen `analyse/ekspertgruppen_celler.les()` allerede følger for
felter, anvendt på entiteter.

## Hva som ville snudd dette

* **En forskrift som definerer koblingen.** Skrives terskelverdiene eller
  en oversettelsestabell inn i produksjonsområdeforskriften, blir
  treffraten beregnelig, og `analyse/vedtak_mot_rad.py` skal da beregne
  den — med skala og hjemmel ført i kjøringsloggen.
* **Et departementsdokument som oppgir grunnlagsårene for rundene 2018,
  2020 og 2022.** I dag er de bare lest for 2024 og 2026, og de tre
  eldste rundene telles derfor ikke som sammenlignbare. Med dem lest
  vokser grunnlaget fra 9 til anslagsvis 34 celler.
* **Styringsgruppens råd som egen kilde.** Leddet mellom ekspertgruppen
  og departementet er en tredje uttalelse, og
  `analyse/fasit/ekspertgruppen-po-kategori.csv` viser at noen celler
  allerede er hentet derfra for hånd. Uten den kan et avvik mellom
  ekspertgruppen og forskriften ikke plasseres: det kan like gjerne ha
  oppstått i styringsgruppen som hos departementet.
* **At 2026-forskriften fastsettes.** Da føyes den til `FORSKRIFTER` med
  sin egen uttrekksfunksjon, og runde 2026 går fra 0 til inntil 13
  celler. Den skal IKKE gjenbruke 2024-uttrekket på antakelse om likt
  format.
