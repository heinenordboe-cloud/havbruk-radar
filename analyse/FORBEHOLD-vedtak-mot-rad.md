# Forbehold: hva sammenstillingen av råd og vedtak IKKE kan si

Hører til `analyse/vedtak_mot_rad.py` og `sources/trafikklysvedtak.py`.
Skrevet 05.09.2026.

**Disse forbeholdene hører til i brødteksten der tallene brukes, ikke i
en fotnote.** Hvert av dem endrer hva et tall betyr, ikke hvor presist
det er.

---

## 1. Det finnes ingen definert oversettelse mellom råd og vedtak

Dette er hovedforbeholdet, og det er grunnen til at analysen ikke
oppgir en treffrate.

Ekspertgruppen gir et **risikonivå** for lakselusindusert
villfiskdødelighet på utvandrende laksesmolt: lav (< 10 %), moderat
(10–30 %), høy (> 30 %). Forskriften gir en **farge**, som styrer
kapasitet. Det er to skalaer om to forskjellige ting, og
oversettelsen mellom dem står ikke noe sted i regelverket.

### Hva som ER definert

**Farge → miljøstatus → konsekvens.** Produksjonsområdeforskriften
(FOR-2017-01-16-61) § 8 annet ledd: «Departementet vurderer om
miljøpåvirkningen i et produksjonsområde er akseptabel, moderat eller
uakseptabel.» §§ 9, 10 og 11 knytter konsekvens til hver av de tre:
nedjustering, uendret, tilbud om vekst.

Fargenavnene står ikke i forskriften, men departementet navngir dem selv
i høringsnotatet til kapasitetsjusteringsforskriften 2026 (19.06.2026,
kap. 1):

> «Er miljøpåvirkningen akseptabel (grønn) kan næringen tilbys vekst. Er
> miljøpåvirkningen moderat (gul) kan kapasiteten bli stående uendret, og
> er miljøpåvirkningen uakseptabel (rød) kan kapasiteten senkes.»

Samme tredeling står på trafikklyssystemet.no under «Fargekodene».
Dette leddet er entydig.

### Hva som IKKE er definert

**Risikonivå → miljøstatus.** Målt 05.09.2026 på både den opprinnelig
kunngjorte (LTI) og den gjeldende (SF) teksten av
produksjonsområdeforskriften:

| ord | forekomster |
|---|---|
| «dødelighet» | 0 |
| «grønn» | 0 |
| «rød» | 0 |
| «trafikklys» | 0 |
| «risiko» | 0 |
| «ekspertgruppe» | 0 |
| prosentterskler (10 %, 30 %) | 0 |

Kapasitetsjusteringsforskriftene sier heller ingenting om det: de
bruker fargen som en gitt størrelse og knytter kapasitetstall til den.

Det nærmeste som finnes er trafikklysmeldingen — Meld. St. 16
(2014–2015) — kap. 8.3, som departementet siterer ordrett i
høringsnotatet 19.06.2026:

> «Dersom resultatet er sammenfallende begge årene vil utfallet være
> forutsigbart og det legges ikke opp til noen vurdering, men dersom
> overvåkingen viser en endring i påvirkning de to årene vil myndighetene
> måtte gjøre grundigere vurderinger ut ifra den samlede miljøtilstanden.»

Tre grunner til at dette ikke er en definisjon å regne mot:

1. **En stortingsmelding er ikke et regelverk.** Den binder ikke
   forvaltningen slik en forskrift gjør.
2. **Setningen sier «forutsigbart», ikke hvilken farge.** Den navngir
   ingen kobling fra lav/moderat/høy til grønn/gul/rød. En analyse som
   antar lav→grønn, moderat→gul, høy→rød antar noe teksten ikke sier.
3. **Den gjelder bare når begge årene er sammenfallende.** For alle andre
   celler viser meldingen uttrykkelig til en skjønnsmessig vurdering.

**Konsekvens for tallene:** «antall celler der råd og vedtak stemmer» og
«antall avvik, med retning» kan ikke beregnes. Det er ikke en mangel ved
dataene — det er et trekk ved forvaltningsordningen.

---

## 2. Fargen er påvirket av forhold utenfor ekspertgruppens råd

Dette er ikke en mistanke. Det står i systemets egen beskrivelse.

Trafikklyssystemet.no, som drives av styringsgruppen (Veterinærinstituttet,
Havforskningsinstituttet og NINA):

> «Det er Nærings- og fiskeridepartementet som avgjør om de 13
> produksjonsområdene blir klassifisert som grønne, gule eller røde […]
> Fargeleggingen baseres på de naturfaglige vurderingene til
> Styringsgruppen og Ekspertgruppen. **I tillegg gjør departementet en
> samlet vurdering som også inkluderer samfunnsøkonomiske konsekvenser
> når Trafikklysets farger settes.**»

Departementet selv, høringsnotatet 19.06.2026 kap. 2:

> «Det vil her være viktig å ta inn ulike forklaringsvariabler, og
> sannsynlighet for å komme over i en annen kategori […] Her kan for
> eksempel parametere som temperatur og salinitet gjøre seg gjeldende. I
> en helhetsvurdering kan det også ses hen til samfunnsøkonomiske
> konsekvenser av ulike valg. **Styringsgruppen foretar ingen slik
> helhetsvurdering når den gir råd til departementet, den gir kun et
> faglig råd om miljøtilstanden.**»

Minst fire ting kan altså skille råd fra vedtak uten at noen av dem er
en feil:

* styringsgruppens sammenfatning, som ligger MELLOM ekspertgruppen og
  departementet og ikke er den samme uttalelsen som ekspertgruppens,
* høringsinnspill,
* forklaringsvariabler som temperatur og salinitet, og
* samfunnsøkonomiske konsekvenser.

**Konsekvens:** et avvik mellom kategori og farge er ikke i seg selv
bevis for at departementet gikk mot faget. Ordningen er innrettet slik at
det kan skje lovlig og åpent.

---

## 3. Vedtaket hviler på TO vurderingsår, ikke ett

En celle (produksjonsområde, tildelingsrunde) har to råd, ikke ett.

Lest av departementets egne dokumenter:

| runde | grunnlagsår | kilde |
|---|---|---|
| 2026 | 2024 og 2025 | høringsnotat 19.06.2026, kap. 2 |
| 2024 | 2022 og 2023 | høringen til kapasitetsjusteringsforskriften 2024 (regjeringen.no id3023357) |
| 2022 | ikke bekreftet | — |
| 2020 | ikke bekreftet | — |
| 2018 | ikke bekreftet | — |

Mønsteret (runde Y bygger på år Y−2 og Y−1) stemmer med rapportenes egne
årsintervaller, men et mønster som passer er ikke en lest kilde
(CLAUDE.md regel 4). `analyse/vedtak_mot_rad.py` teller derfor bare de
rundene der grunnlagsårene faktisk er lest, og fører resten som
«vedtak uten lest grunnlagsår».

**Konsekvens:** en sammenstilling som parer runde 2024 mot
ekspertgruppens 2024-vurdering ville paret vedtaket med en rapport som
ble utgitt ETTER at vedtaket ble fattet. Rapporten for 2024 kom i 2025;
forskriften ble fastsatt 22.03.2024.

---

## 4. Et sammenfall beviser ikke årsak

Selv der kategori og farge faller sammen, følger det ikke at
ekspertgruppens råd forårsaket fargen.

* Antallet celler er lite. Med 40 vedtakceller i alt, hvorav 9 har lest
  grunnlagsår og et råd, er tilfeldig sammenfall ikke usannsynlig.
* Fordelingen er skjev i begge ender: 31 av 40 vedtakceller er grønne
  (6 røde, 3 gule), og 62 av 116 rådsceller er «lav» (41 moderat, 13
  høy). To skjeve fordelinger vil falle sammen ofte uten at noen av dem
  forklarer den andre.
* Ekspertgruppen og departementet leser samme underliggende virkelighet.
  Sammenfall kan like gjerne skyldes at lusepresset var lavt som at
  rådet ble fulgt.

Dette er samme forbehold som `docs/beslutninger/2026-08-31-hypotesen-
omdefineres.md` slår fast for ROC-leddet: en fasit som er en funksjon av
de samme prediktorene er ikke en uavhengig fasit.

---

## 5. Hvor mange celler hviler på en tolket skala-oversettelse

Med analysen slik den står: **null.** Skriptet beregner ingen treffrate,
så ingen celle bærer en oversettelse.

Skulle noen likevel innføre en, ville den gjelde alle de 9 cellene der
begge sider finnes og grunnlagsårene er lest. Av de 9 har 1 celle
SPRIKENDE råd mellom de to grunnlagsårene (høy det ene året, moderat det
andre) — nettopp tilfellet trafikklysmeldingen sier at utfallet IKKE er
forutsigbart for. Den cellen ville hvilt på både en oppdiktet skala og et
oppdiktet valg mellom to år.

---

## 6. Hvor mange vedtakceller hviler på VÅR utledning

17 av 40 vedtakceller har lesemåte `kapittelhjemmel`: forskriften nevner
ikke farge i det hele tatt, og grønt er utledet av at området står under
kapittelet som gjennomfører produksjonsområdeforskriften § 11
(«Tilbud om kapasitetsøkning (akseptabel miljøpåvirkning)»).

Alle 17 er fra rundene 2018 og 2020. Utledningen er etterprøvd så langt
det lar seg gjøre: den samme strukturelle plassen er merket «(grønne)»
ORDRETT i både 2022- og 2024-forskriften. Men den er en utledning, og
`farge__lesemaate` bærer den på hver rad slik at ingen analyse kan bruke
den uten å se den.

---

## 7. 25 av 65 celler har ikke noe vedtak å lese

Ikke fordi vedtaket mangler i verden — fordi forskriften ikke uttaler seg.

* **13 celler (runde 2026):** ingen fastsatt forskrift. Fargeleggingen er
  kunngjort i pressemelding, utkastet var på høring med frist 31.07.2026,
  og målt 05.09.2026 finnes ingen kapasitetsjusteringsforskrift for 2026 i
  Norsk Lovtidend avdeling I.
* **5 celler (runde 2018):** FOR-2017-12-20-2397 inneholder ikke ett
  eneste fargeord og har intet kapittel om nedjustering. Et rødt område
  ser der nøyaktig ut som et gult.
* **1 celle (runde 2020, PO10):** unevnt i 2020-forskriften og restatert
  av ingen senere forskrift.
* **2 celler (runde 2022) og 4 celler (runde 2024):** områder som verken
  står i den grønne lista eller i § 4-tabellen.

De 7 siste (2022 og 2024) er de eneste der utelukkelse peker et sted:
systemet har tre farger, så «verken grønn eller rød» peker mot gul.
Slutningen krever at forskriften er uttømmende om farge, og
2018-forskriften viser at den ikke trenger å være det. **Hullene er
altså ikke jevnt fordelt, og det er ikke tilfeldig hvilke områder som
mangler:** de gule er nettopp de som ikke utløser noe tiltak, og derfor
de som ikke trenger å nevnes i en forskrift om kapasitetsjustering.

En analyse som bare bruker celler med vedtak, arbeider derfor på et
utvalg som systematisk underrepresenterer gult.
