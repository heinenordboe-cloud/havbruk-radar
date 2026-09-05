# Trafikklysvedtak — verifiseringsnotat og kildespesifikasjon

Kilde: `sources/trafikklysvedtak.py`
Sammenstilling: `analyse/vedtak_mot_rad.py`
Forbehold: `analyse/FORBEHOLD-vedtak-mot-rad.md`
Beslutning: `docs/beslutninger/2026-09-05-vedtakskilden.md`

Alt i dette notatet er MÅLT på nedlastede kropper 05.09.2026, ikke lest
ut av en oppsummering. Der noe er utledet framfor lest, står det.

## 1. Hva dette er

`sources/ekspertgruppen.py` har RÅDET i trafikklyssystemet: hvilken
risikokategori ekspertgruppen setter på hvert produksjonsområde.
Denne kilden har VEDTAKET: hvilken farge Nærings- og
fiskeridepartementet faktisk ga området, lest av
kapasitetsjusteringsforskriftene.

Entitet er produksjonsområde (`entity_type = "produksjonsomraade"`, samme
som ekspertgruppen og biomasse), `observed_at` er siste dag i
tildelingsrunden, og `published_at` er forskriftens ikrafttredelse.

## 2. Inventaret — fire forskrifter, ikke fem

Trafikklyset er fargelagt i rundene 2018, 2020, 2022, 2024 og 2026.

| runde | forskrift | fastsatt | ikrafttredelse | kunngjort |
|---|---|---|---|---|
| 2018 | FOR-2017-12-20-2397 | 20.12.2017 | 20.12.2017 | 03.01.2018 |
| 2020 | FOR-2020-02-04-105 | 04.02.2020 | 04.02.2020 | 05.02.2020 |
| 2022 | FOR-2022-06-07-972 | 07.06.2022 | 07.06.2022 | 07.06.2022 |
| 2024 | FOR-2024-03-22-515 | 22.03.2024 | 22.03.2024 | 26.03.2024 |
| 2026 | **finnes ikke** | — | — | — |

### Hvordan fraværet av 2026 er FASTSLÅTT

Lovdatas søk (`/sok`) svarer 405 for oss. Registeret over Norsk
Lovtidend gjør ikke det, og det søker i tittelfeltet:

    https://lovdata.no/register/lovtidend?avdeling=LTI&year=2026&search=<ord>

Søkeord prøvd: `matfisk`, `kapasitet`, `akvakultur`, `produksjonsomr`,
`regnbue`, `tillatelser`, `kapasitetsjuster`. Ingen av dem gir en
kapasitetsjusteringsforskrift for 2026. Kontrollsøk på `kongekrabbe`
(9 treff) og de samme ordene for 2018–2025 (som finner alle fire
forskriftene over) viser at søket virker.

Departementet sendte utkastet på høring 19.06.2026 med frist
31.07.2026, og kunngjorde fargeleggingen i pressemelding. Vedtaket i
forskrifts form fantes ikke 05.09.2026.

**Runden står derfor ikke i `FORSKRIFTER`.** Fravær framfor gjetning,
samme regel som ekspertgruppens manglende årganger.

## 3. `published_at` — ikrafttredelsen, og HTTP har ingenting å tilby

Biomasse tar `published_at` fra `Last-Modified`. Ekspertgruppen kan
ikke, fordi headeren der er en CMS-migreringsdato. Her er situasjonen en
tredje: **lovdata.no sender ingen `Last-Modified` i det hele tatt.**

Målt 05.09.2026 med `curl -I` på alle fire dokumentene. Svaret har
`date:` (nå) og `cache-control: max-age=7200`, og ingen
`Last-Modified`, ingen `ETag`. Det finnes ikke noe HTTP-alternativ å ta
feil av.

Det som finnes er dokumentets eget metadatafelt `Ikrafttredelse`.
Ikrafttredelsen er valgt framfor kunngjøringsdatoen fordi den er det
tidspunktet vedtaket VIRKER fra.

### Vakten

`_utgitt()` KREVER at ikrafttredelsen er lik fastsettelsesdatoen i
FOR-nummeret. Alle fire kroppene passerer (tabellen over). Skiller de
seg, er vedtaket utsatt eller gitt tilbakevirkende kraft, og da svarer
ikrafttredelsen på et annet spørsmål enn `published_at` stiller —
feltet settes tomt med en advarsel. Vakten finnes for den femte kroppen.

Klokkeslettet settes til 12:00 UTC. Lovdata oppgir bare dato for
ikrafttredelse; et klokkeslett vi ikke har ville vært oppdiktet presisjon
uansett hvilket vi valgte, og 12:00 er det som ikke flytter datoen i noen
tidssone.

## 4. LTI, ikke SF

Lovdata har hvert dokument i to former:

* **LTI** — teksten slik den ble kunngjort. Endrer seg aldri.
* **SF** — den konsoliderte, som oppdateres når forskriften endres.

2022-forskriften er endret tre ganger etter kunngjøring
(FOR-2022-06-16-1058, FOR-2022-09-28-1671, FOR-2022-10-06-1721).

Kilden leser LTI. Et VEDTAK er en handling på et tidspunkt, og
`published_at` skal peke på det tidspunktet. En konsolidert tekst er en
påstand om hva som gjelder NÅ, og ville gjort hver kropp til en bevegelig
referanse — CLAUDE.md 1b-4.

Bieffekt som er verdt å notere: fordi LTI-kroppene er faste, er dette en
kilde uten revisjon i 1b-5-forstand. Det som ser ut som revisjon i
changeloggen er at en NYERE forskrift uttaler seg om en ELDRE runde.

## 5. Én uttrekksfunksjon per forskriftsår

Kroppene er MÅLT forskjellige dokumenter:

| kropp | fargeord i teksten | § 3-form | § 4-tabell |
|---|---|---|---|
| 2018 | **ingen** | «Kapittel 2 om økt kapasitet … gjelder» | nei |
| 2020 | «røde», bare i kapittel 4s overskrift | tre kapittelledd | nei |
| 2022 | «(grønne)», «X lys i ÅÅÅÅ» | to kapittelledd | ja, 2 runder/rad |
| 2024 | «(grønne)», «X lys i ÅÅÅÅ» | to kapittelledd | ja, 3 runder/rad |

### 2018-kroppen inneholder ikke ett eneste fargeord

Verifisert med regex over hele dokumentet: hverken «grønn», «gul» eller
«rød» i noen bøyning. (Et naivt søk på delstrengen «gul» treffer
«regUL­ering» — det er derfor tellingen er gjort på ordstammer med
kontekst, ikke på delstrenger.)

Det finnes heller ikke noe kapittel om nedjustering. I den første runden
ble ingen kapasitet nedjustert, og et rødt område ser i dokumentet
nøyaktig ut som et gult.

### 2020-kroppen har fargeordet i en KAPITTELOVERSKRIFT

> «Kapittel 4. Nedjustering av tillatelseskapasitet i **røde**
> produksjonsområder»

§ 3 tredje ledd plasserer PO4 og PO5 under kapittel 4. To lesninger,
begge ordrett i samme dokument, men i to setninger — derfor lesemåte
`kapitteloverskrift` og ikke `ordrett`.

### 2022- og 2024-kroppene er IKKE samme dokument

De ligner, og det er nettopp derfor de har hvert sitt uttrekk. Tre
målte forskjeller:

1. den grønne lista er åtte områder i 2022 og seks i 2024,
2. hver tabellrad bærer to runder i 2022 og tre i 2024, og
3. § 4 i 2024 har i tillegg løpende tekst som omtaler
   «produksjonsområde 3 og 4» og «produksjonsområde 5» med **liten**
   forbokstav. Tabellmønsteret krever stor P nettopp for å ikke lese de
   tre prosaomtalene som tabellrader.

Å kalle 2022-uttrekket fra 2024 ville vært riktig i dag og stille feil
den dagen en av de tre forskjellene betydde noe.

## 6. Vaktene

Alle kaster `Forskriftsfeil`, som stopper uttrekket framfor å levere
delvise farger.

| vakt | spør |
|---|---|
| `_krev_alle_omraader` | nevner § 3-leddet et «Område N:» uten at en farge kom ut? |
| `_krev_alle_tabellrader` | har § 4 en «Produksjonsområde N» uten farge, en parentes uten «X lys i ÅÅÅÅ», eller et årstall i parentesen som ingen celle dekker? |
| `_krev_runder` | er rundene tabellen nevner nøyaktig de `FORSKRIFTER` sier kroppen dekker? |
| `_krev_ordlyd` | står ordlyden vi PÅSTÅR at kroppen har, faktisk der? |
| `_krev_vekst_hjemmel` | er forskriften hjemlet i produksjonsområdeforskriften § 11, og handler kapittelet om økt kapasitet? |
| `_forskriftstekst` | finnes «Hjemmel: Fastsatt av», så brødteksten kan skilles fra innholdsfortegnelsen? |
| `gjenkjenn` | er FOR-nummeret og tittelen enige om hvilken forskrift dette er? |

Ankeret i `_krev_alle_omraader` er «Område N:» med kolon, ikke ordet
«produksjonsområde». Det siste står 20–40 ganger i hver kropp — om
virkeområde, om flytting, om vederlag — og en vakt på det ordet ville
fyrt på hver eneste paragraf. Samme resonnement som
`ekspertgruppen._VINDU_KANDIDAT`.

`_krev_runder` er den vakten som fanger den farligste feilen: et uttrekk
som leser to av tre parenteser gir fortsatt tre tabellrader, riktig form
og en tapt runde.

## 7. Tre lesemåter

Hver farge får `farge__lesemaate`. Ordinale, sterkest først:

| lesemåte | betyr |
|---|---|
| `ordrett` | fargeordet står i samme setning eller tabellrad som områdenummeret |
| `kapitteloverskrift` | § 3 plasserer området i et kapittel, og kapittelets overskrift bærer fargeordet |
| `kapittelhjemmel` | **utledet**: området står under kapittelet som gjennomfører produksjonsområdeforskriften § 11, og kroppen har ingen fargeord |

### Utledningen er etterprøvd

`kapittelhjemmel` er det eneste leddet der vi tar et steg kilden ikke
tar. Den er kontrollert så langt kroppene tillater:

* **Grønn:** den samme strukturelle plassen — § 11-kapittelet for økt
  kapasitet — er merket «(grønne)» ORDRETT i både 2022- og
  2024-kroppen. To av to tilgjengelige kontroller stemmer.
* **Rød:** 2020-kroppens `kapitteloverskrift`-lesning av PO4 og PO5
  bekreftes ordrett av «rødt lys i 2020» i både 2022- og 2024-kroppen.
  To av to.

## 8. Dekningsflaten

40 av 65 mulige celler (13 områder × 5 runder) har en farge.

| runde | celler | grønn | gul | rød | hull |
|---|---|---|---|---|---|
| 2018 | 8 | 8 | 0 | 0 | PO 2, 3, 4, 5, 6 |
| 2020 | 12 | 9 | 1 | 2 | PO 10 |
| 2022 | 11 | 8 | 1 | 2 | PO 2, 7 |
| 2024 | 9 | 6 | 1 | 2 | PO 2, 6, 7, 8 |
| 2026 | 0 | — | — | — | alle 13 |

Lesemåte over de 40: 23 `ordrett`, 17 `kapittelhjemmel`, 0
`kapitteloverskrift` (de to `kapitteloverskrift`-cellene i 2020-kroppen
er senere restatert ORDRETT, og den sist utgitte lesemåten er den som
gjelder ved lesing).

### Hullene er ikke tilfeldige

De 7 hullene i 2022 og 2024 er områder som verken står i den grønne
lista eller i § 4-tabellen. Systemet har tre farger, så «verken grønn
eller rød» peker mot gul — og det er nettopp poenget: **gule områder er
de som ikke utløser noe tiltak, og derfor de som ikke trenger å nevnes i
en forskrift om kapasitetsjustering.** Utvalget av celler med vedtak
underrepresenterer systematisk gult.

Fargen ved utelukkelse emitteres likevel ikke. Slutningen krever at
forskriften er uttømmende om farge, og 2018-kroppen viser at den ikke
trenger å være det.

## 9. Revisjonsaksen — kjent avvik

`diff.revisjon_mellom()` sier uttrykkelig at skjemafilteret går på
FELTNAVN og ikke på entiteter, fordi «en entitet som dukker opp eller
forsvinner mellom to versjoner av samme måned ER en revisjon». Det er
riktig for biomasse. Det er **feil for denne kilden**: at
2022-forskriften ikke gjentar PO1 for runde 2020, betyr ikke at
departementet trakk tilbake det grønne lyset — det betyr at
§ 4-tabellen bare har tre rader.

Målt på backfillen 05.09.2026, 38 revisjonsrader i alt:

| | rader |
|---|---|
| `new_value` er null — området er bare ikke gjentatt | 34 |
| `old_value` er null — ny påstand (PO3 i 2020) | 2 |
| ekte verdiendring — PO4/PO5 2020, lesemåte oppgradert | 2 |
| **motstrid om FARGE mellom to kropper** | **0** |

De 34 er en usann påstand i changeloggen. De er ikke datatap:
changeloggen er avledet og kan regnes ut på nytt fra snapshotene
(CLAUDE.md regel 2), begge snapshots står, og `diff.bevegelse()`
filtrerer `revidert` bort fra ukas endringstall.

Rettelsen hører hjemme i `core/diff.py` — et valg mellom entitets- og
feltsemantikk som en kilde ikke kan ta selv. CLAUDE.md regel 1 sier at
en kilde IKKE skal be om en endring i `core/` på egen hånd, så avviket
står målt og ikke omgått.

**Leseregelen inntil videre:** gjeldende farge for (runde, PO) er den
sist utgitte raden SOM FINNES for cellen — ikke det siste snapshotet.
Implementert i `analyse.vedtak_mot_rad._sist_utgitt()`.

At tallet i siste rad er **0** er i seg selv et funn: de fire
forskriftene motsier aldri hverandre om en farge.

## 10. Frekvens

`min_dager_mellom = 7` for en toårig kilde. Sju betyr ikke «det kommer
en forskrift hver uke», det betyr «tilby kilden til kjøringen hver uke og
la `finnes_allerede()` avgjøre».

Fastsettelsesmåneden er målt til å variere: desember (2017), februar
(2020), mars (2024) og juni (2022). Et etterslep i dager måtte gjettet
hvilken.

## 11. Lisens og attribusjon

Norsk Lovtidend og Lovdatas gjengivelse av forskrifter er offentlige
rettskilder. Rå-kroppene i `data/arkiv/trafikklysvedtak/` er HTML-sider
fra lovdata.no, arkivert for at en forbedret parser skal kunne kjøre på
nytt uten å hente igjen. Sitater i dokumentasjonen er ordrette og
kildeført til FOR-nummer.

## 12. Det som IKKE er bygget

* **Kapasitetstallene i § 4-tabellen.** «Ned 6 pst.», «94 pst.»,
  «88,36 pst.» er lesbare, men er en annen størrelse enn fargen.
  Kroppen er arkivert; det er en re-parse den dagen noen vil ha dem.
* **Vederlagssatsene.** 120 000 kr/tonn (2018), 156 000 (2020),
  170 000 (2024) står i § 7/§ 10 og er ikke hentet.
* **Fargen for runde 2026.** Den finnes i en pressemelding, ikke i et
  vedtak. Kilden leser vedtak.
* **Styringsgruppens råd.** Leddet mellom ekspertgruppen og
  departementet er en tredje uttalelse som ikke er hentet, og det er en
  reell begrensning på sammenstillingen — se forbehold 2.
