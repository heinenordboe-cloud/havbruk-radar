# Verifisering: departementets pressemeldinger om fargeleggingen

Dokumentasjonsgrunnlag, ikke kilde. Ingenting her blir observasjoner i
`data/`. `sources/trafikklysvedtak.py` leser VEDTAK og ikke
pressemeldinger med vilje, og det valget står — se
`docs/beslutninger/2026-09-05-vedtakskilden.md`.

Materialet kom inn i prosjektet som påstander fra en planleggingssamtale.
Hver enkelt er holdt mot kroppen. Kroppene er hentet 09.09.2026 og lagret
rått før noe ble lest.

## Kroppene

regjeringen.no svarer 403 for oss på alle fem, som for ekspertgruppens
2021- og 2022-kropper. Alle er hentet via Internet Archive med `id_`, som
gir arkivets kopi av det opprinnelige svaret.

| melding | id | Wayback-avtrykk | byte | sha256 |
|---|---|---|---|---|
| 30.10.2017 | `id2577032` | 2019-01-03 01:06:10 | 52 013 | `896b9570c2d91346f06513fddba7bd7c45b1a5235950fb83f0410210b54eadda` |
| 04.02.2020 | `id2688939` | 2021-02-06 09:16:30 | 58 646 | `f02cd9a1494e908b6dc145b0551795c69b8f75425983b44dae1386e275ed9c6b` |
| 07.06.2022 | `id2917698` | 2022-06-07 11:37:21 | 58 792 | `637168e536c51114259825401ff0396425f75944b54f1b95af4b03ab0c5501c9` |
| 06.03.2024 | `id3028522` | 2024-03-06 08:41:13 | 57 118 | `c5681d286a37cf49304349c076b5e58af99ffbfc129ff0db0be261e670ef9c22` |
| 19.06.2026 | `id3167021` | 2026-08-12 11:20:38 | 66 197 | `b804dafd845a9908e14601e9dc855180c2115edaa4771402212496d610bdc194` |

`id2688939` var ikke oppgitt på forhånd. Den ble funnet ved å søke
Waybacks CDX-indeks over `regjeringen.no/no/aktuelt/` for 2020 og lese
datofeltet i kroppen: «Dato: 04.02.2020». Slugen er
`regjeringen-skrur-pa-trafikklyset-i-havbruksnaringen`.

Merk avtrykksdatoene: for 2020- og 2026-meldingene er nærmeste avtrykk
henholdsvis ett år og to måneder etter utgivelsen. Kroppen kan ha blitt
endret i mellomtiden uten at vi ser det. Dette er Waybacks `fetched_at`,
ikke departementets `published_at` — CLAUDE.md 1b-7 punkt 2.

---

## B1 — pressemeldingen 30.10.2017 — **BEKREFTET**, og rikere enn påstått

Alle fire delpåstandene stemmer ordrett.

**Grunnlagsår 2016 og 2017:**

> «I rapporten er det gjort en detaljert analyse av lakseluspåvirkning i
> de ulike produksjonsområdene på basis av all tilgjengelig kunnskap for
> årene 2016 og 2017.»

**Fargene for alle tretten, i én setning:**

> «Regjeringen har besluttet at 8 produksjonsområder settes til grønt
> (produksjonsområdene 1 og 7-13), tre produksjonsområder settes til gult
> (2, 5 og 6) og to produksjonsområder settes til rødt (3 og 4).»

**PO7 satt til grønt mot rådet, med samfunnsøkonomi som oppgitt grunn:**

> «- Min vurdering er i hovedsak den samme som rådene fra
> styringsgruppen, men etter en helhetlig vurdering har jeg valgt å sette
> produksjonsområde 7 til grønt. Jeg mener at lusepåvirkningen i området
> ligger innenfor et akseptabelt risikonivå og at dette kan underbygges
> av gode faglige vurderinger, sier fiskeriminister Sandberg.»

> «-Bildet som tegnes i ekspertgruppens rapport gir meg tro på at den
> gode utviklingen i produksjonsområde 7 er en trend som vil vare. Det er
> lagt vekt på at de positive samfunnsøkonomiske konsekvensene er vurdert
> til å være betydelig større enn de negative, sier Sandberg»

**Avviket er etterprøvd mot dataene.** Styringsgruppens råd for PO7 for
2016–2017 er `10-30%` — moderat, altså gult — lest av Tabell 1 i
styringsgruppens 2018-kropp, kolonnen `Råd 2017 For 2016–2017`.
Departementet satte grønt. Dette er det eneste målte tilfellet i hele
materialet der departementet fraviker rådets kategori for et navngitt
område.

### Betingelsen i faktaboksen — den står, og den er UTESTET

Faktaboksen gjengir styringsgruppens regel slik:

> «Styringsgruppen har ut i fra ekspertgruppens rapport gjort en samlet
> vurdering av lakselusindusert dødelighet for laks i perioden 2016-2017.
> Styringsgruppens råd er basert på lik vekting av årene. Der vurderingene
> er forskjellig for et område i de to årene **og usikkerheten er middels
> eller høy**, har styringsgruppen valgt en konservativ tilnærming. Dette
> innebærer konkret at det er det året med høyest risiko for luseindusert
> dødelighet som har blitt førende for rådet.»

(Uthevingen er min.)

Styringsgruppens egen ordlyd, i 2018-2019-kroppen, har ingen slik
betingelse:

> «Der ekspertgruppens vurderinger for kategori av dødelighet for et
> område er forskjellig i 2018 og 2019 har styringsgruppen, på lik måte
> som for rådet avgitt i 2017, valgt en konservativ tilnærming for samlet
> vurdering av lakselusindusert dødelighet (Tabell 3).»

**Er departementet mer presis enn kilden? Det kan ikke avgjøres, og det
er selve svaret.**

Tre ting, i rekkefølge:

1. **Kilden departementet beskriver, kan ikke leses.** Faktaboksen handler
   om rådet for 2016–2017, som ble avgitt i styringsgruppens
   september-2017-kropp. Den kroppen er en skann uten tekstlag — 10 tegn
   uttrukket av elleve sider. Se `docs/KARTLEGGING-STYRINGSGRUPPEN.md`.
   Betingelsen kan altså ikke etterprøves mot den teksten den gjengir.

2. **Betingelsen er FORENLIG med dataene, men den skiller ingenting.**
   Målt på Tabell 1 i styringsgruppens 2018-kropp, som restaterer
   2016–2017-rådet i tekst:

   | PO | 2016 | 2017 | usikkerhet 2016–2017 | Råd 2016–2017 |
   |---|---|---|---|---|
   | 2 | `10-30%` | `< 10 %` | Stor | `10-30%` |
   | 4 | `10-30%` | `> 30 %` | Middels | `> 30 %` |
   | 6 | `10-30%` | `< 10 %` | Stor | `10-30%` |
   | 7 | `10-30%` | `< 10 %` | Middels | `10-30%` |

   Fire områder spriker mellom de to årene, og **alle fire har Middels
   eller Stor usikkerhet**. Ingen av de ni øvrige spriker. Det finnes
   altså ikke ett eneste tilfelle i 2016–2017 der de to formuleringene
   ville gitt forskjellig svar: betingelsen er aldri satt på prøve.

3. **Konklusjonen.** Departementet oppgir en strengere regel enn den
   styringsgruppen selv skriver ned. Om det er en mer presis gjengivelse
   av september-2017-kroppen, eller en presisering departementet har lagt
   til, kan ikke avgjøres fra noen kropp vi har. Det som KAN sies er at
   regelen aldri fikk et tilfelle å diskriminere på, og at
   styringsgruppen i den neste kroppen — den vi kan lese — skrev den uten
   betingelsen.

---

## B2 — grunnlagsår per runde — **BEKREFTET**, alle fire

| runde | melding | ordrett |
|---|---|---|
| 2018 | 30.10.2017 | «for årene 2016 og 2017» |
| 2020 | 04.02.2020 | «I områder der påvirkningen av lakselus har vært ulik i 2018 og 2019 …» |
| 2022 | 07.06.2022 | «Fargen er satt basert på naturfaglige vurderinger av lakselusas påvirkning på villaks for årene 2020 og 2021.» |
| 2024 | 06.03.2024 | «Fargene er satt basert på naturfaglige vurderinger av lakselusas påvirkning på villaks for årene 2022 og 2023.» |
| 2026 | 19.06.2026 | «Fargene er satt basert på naturfaglige vurderinger av lakseluspåvirkning på villaks for årene 2024 og 2025.» |

Runde 2018 sto ikke i B2-lista; den er lagt til fordi 30.10.2017-kroppen
oppgir den. Dermed er grunnlagsårene lest av kilden for **alle fem
runder**, ikke bare de fire som var påstått.

Det lukker den ene av tre reverseringstingene i
`docs/beslutninger/2026-09-05-vedtakskilden.md`: «Et departementsdokument
som oppgir grunnlagsårene for rundene 2018, 2020 og 2022. I dag er de
bare lest for 2024 og 2026.» De er nå lest for alle fem.

---

## B3 — sprikende områder — **tre BEKREFTET, én AVKREFTET**

| runde | påstått | kroppen sier | dom |
|---|---|---|---|
| 2020 | ingen navngitt | **navngir seks** | **AVKREFTET** |
| 2022 | PO2, PO4, PO5 | PO2, PO4, PO5 | BEKREFTET |
| 2024 | PO4, PO8 | PO4, PO8 | BEKREFTET |
| 2026 | PO9 | PO9 | BEKREFTET |

**2022**, ordrett:

> «For tre av områdene var ekspertenes vurdering ulik i 2020 og 2021.
> Dette gjelder Ryfylke (PO2), Nordhordland til Stadt (PO4) og Stadt til
> Hustadvika (PO5).»

**2024**, ordrett:

> «For to av områdene var ekspertenes vurdering ulik i 2022 og 2023. Dette
> gjelder Nordhordland til Stadt (PO4) og Helgeland til Bodø (PO8).»

**2026**, ordrett:

> «For 2024 og 2025 er dette tilfellet for 12 av produksjonsområdene. I
> områder der ekspertgruppens vurderinger er ulik de to årene gjør
> departementet en mer helhetlig vurdering av miljøtilstanden. Ved årets
> fargelegging gjelder dette ett av produksjonsområdene, Vestfjorden og
> Vesterålen (PO9).»

### Hvorfor 2020-påstanden er avkreftet

04.02.2020-meldingen har en egen mellomtittel, **«Områder med endring fra
2018 til 2019»**, og under den navngis seks områder med retningen på
endringen:

> «Ryfylke og Nord-Trøndelag med Bindal får grønt lys. Her har utviklingen
> vært positiv i måleperioden og gått fra moderat til lav påvirkning fra
> lakselus.»

> «Området fra Karmøy til Sotra får gult lys. Også dette området har hatt
> en positiv utvikling fra høy påvirkning fra lakselus i 2018 til moderat
> i 2019.»

> «Området fra Andøy til Senja får også gult lys. Her har det vært en
> negativ utvikling fra lav påvirkning fra lakselus i 2018 til moderat i
> 2019.»

> «Produksjonsområdene fra Nordhordland til Stadt og fra Stadt til
> Hustadvika får rødt lys. Områdene har hatt en negativ utvikling fra
> moderat påvirkning fra lakselus i 2018 til høy påvirkning i 2019.»

Det er **PO2, PO3, PO4, PO5, PO7 og PO10**.

**Og det er nøyaktig de seks som er målt i styringsgruppens
2018-2019-kropp.** `docs/MALING-RAD-MOT-EKSPERTVURDERING.md` og
`docs/KARTLEGGING-STYRINGSGRUPPEN.md` fant PO 2, 3, 4, 5, 7 og 10 som de
eneste med ulik kategori i de to årene, og med retningene:

| PO | 2018 | 2019 | departementets ord |
|---|---|---|---|
| 2 | `10-30%` | `< 10%` | «fra moderat til lav» ✓ |
| 3 | `> 30%` | `10-30%` | «fra høy … i 2018 til moderat i 2019» ✓ |
| 4 | `10-30%` | `> 30%` | «fra moderat … i 2018 til høy … i 2019» ✓ |
| 5 | `10-30%` | `> 30%` | «fra moderat … i 2018 til høy … i 2019» ✓ |
| 7 | `10-30%` | `< 10%` | «fra moderat til lav» ✓ |
| 10 | `< 10%` | `10-30%` | «fra lav … i 2018 til moderat i 2019» ✓ |

Seks av seks, i begge retninger, med samme kategorier. Departementets
melding og styringsgruppens kropp er uavhengige lesninger av det samme,
og de stemmer på hver eneste celle.

Merk hva dette gjør med rådet: styringsgruppens sammenslåtte råd for
2018-2019 valgte det verste året i alle seks. Departementet fargela PO2
og PO7 GRØNT, PO3 og PO10 GULT, PO4 og PO5 RØDT — altså etter 2019-året
alene i fire av seks, ikke etter det sammenslåtte rådet. Dette er ikke
målt videre her, og det står som en åpen tråd i C2.

---

## B4 — «samlet vurdering» i 2020-meldingen — **BEKREFTET**

Ordrett, og i sin helhet:

> «Nærings- og fiskeridepartementet baserer fargeleggingen på naturfaglige
> råd. I områder der påvirkningen av lakselus har vært ulik i 2018 og 2019
> har departementet gjort en samlet vurdering hvor også samfunnsøkonomiske
> konsekvenser har spilt inn. Dette er i tråd med Havbruksmeldingen.»

Formuleringen går igjen, litt endret, i alle de senere meldingene — 2022
utdyper den med «grundigere vurderinger av den samlede miljøtilstanden»,
2026 med «en mer helhetlig vurdering av miljøtilstanden». Den er altså
ikke en engangsformulering, men systemets faste begrunnelse for skjønn i
sprikende områder.

---

## B5 — 2018-2019-kroppens to tabeller — **BEKREFTET**

Verifisert mot den arkiverte kroppen, ikke mot nett. sha256
`b849614f9cf1c2ce2e9169e7f4afdb4d9a19421a0f567f666ca64542e9e5cd34`,
uendret siden kartleggingen.

**Tabell 2 er ekspertgruppens 2019-vurdering i sin helhet**, side 5, 13
rader, med metodekolonner og konklusjon. Bannerlinja er
`Vurdering 2019 (konklusjonusikkerhet)` og kolonneoverskriftene ordrett:

    PO   Trål      Sjøørret   Vaktbur   HI            HI      VI      SINTEF   Konklusjon
         fangst    ruse                 smittepress   Smolt   smolt   smolt

Konklusjonskolonnen for 2019: PO1 `Lavliten`, PO2 `Lavmid`, PO3 `Modmid↑`,
PO4 `Høymid`, PO5 `Høymid`, PO6 `Lavstor`, PO7 `Lavstor`, PO8 `Lavmid`,
PO9 `Lavmid`, PO10 `Modstor↓`, PO11 `Lavliten`, PO12 `Lavmid`, PO13
`Lavliten`.

**Tabell 1 er en revidert 2018-vurdering**, side 4, 13 rader, samme
kolonner. Bildeteksten sier det selv:

> «Tabell 1. Ny vurdering av lakselusindusert dødelighet for 2018 med
> oppdaterte modeller fra HI og VI og nye SINTEF resultater som ikke var
> inkludert i rapporten fra 2018.»

Bannerlinja er `Oppdatert vurdering 2018 (konklusjon usikkerhet)`. Dette
er samme form som 2021-kroppens Tabell 2 og 2025-kroppens kapittel 6.1:
en kropp som reviderer et år en tidligere kropp allerede har uttalt seg
om. `diff.revisjon()` er aksen for det.

Tabellen bærer dessuten et eget merke for revisjonen:

> «Δ Usikkerheten er endret etter revidering av metoder fra 2018 til 2019.»

Merket står på PO3, PO4, PO7 og PO8.

### Verdien er ANNENHÅNDS, og kroppen sier det selv

Dette er styringsgruppens gjengivelse i sitt eget dokument, ikke
ekspertgruppens kropp. Bildetekstene henviser videre:

> «Metodene er beskrevet i detalj i ekspertgruppens rapport (Vedlegg 1).»

**Og Vedlegg 1 er ikke med.** Side 11 har overskriften «Vedlegg 1 —
Ekspertgruppens rapport med 12 vedlegg», og så er det ingenting. Det er
en skilleside. Kroppen på hi.no er de tretten sidene styringsgruppen
skrev; ekspertgruppens rapport var vedlagt den opprinnelige leveransen og
er ikke i denne fila.

### En ting som endrer 2019-linja i KILDE-EKSPERTGRUPPEN.md punkt 9

Punkt 9 fører 2019 som «UBESVART SPØRSMÅL — ikke bekreftet fravær», med
begrunnelsen «Vi vet ikke om rapporten finnes».

**Kroppen siterer den, med full tittel og forfatterrekke:**

> «Vollset, K.W., Nilsen, F., Ellingsen, I., Finstad, B., Helgesen, K.O.,
> Karlsen, Ø., Sandvik, A.D., Sægrov, H., Ugedal, Qviller, L., O., Dalvin,
> S. 2019. Vurdering av lakselusindusert villfiskdødelighet per
> produksjonsområde i 2019. Rapport fra ekspertgruppe for vurdering av
> lusepåvirkning.»

Ekspertgruppens 2019-rapport FINNES altså — den er skrevet, navngitt og
sitert av styringsgruppen. Det vi ikke har, er en kopi.

Det flytter 2019 fra kategorien «vi vet ikke om det finnes noe å nå» til
kategorien 2023–2025 lå i fram til 01.09.2026: «vi vet at rapporten finnes
og vi når den ikke». Det er den samme kategorien som ble tømt da NVA ble
prøvd.

**Punkt 9 er IKKE rettet på dette grunnlaget.** Beviset ligger i en kropp
som ikke er i repoet — den ligger i sesjonens arbeidsmappe fra
kartleggingen — og revisjonens regel 2 sier at bare påstander med bevis i
repoet rettes. Endringen er din avgjørelse. Se
`docs/REVISJON-2026-09-09.md`.

Og uansett: B5 gjør ikke 2019 dekket. En annenhånds gjengivelse i et
vedlegg er ikke ekspertgruppens egen kropp, og en kilde skal ikke
emittere for et år den ikke har lest en kropp for.

---

## Fargene, samlet, som kroppene oppgir dem

Tatt med fordi de er lest ordrett i denne runden og fordi de gir en
uavhengig kontroll av vedtakskilden.

| runde | grønn | gul | rød |
|---|---|---|---|
| 2018 | 1, 7, 8, 9, 10, 11, 12, 13 | 2, 5, 6 | 3, 4 |
| 2020 | 1, 2, 6, 7, 8, 9, 11, 12, 13 | 3, 10 | 4, 5 |
| 2022 | 1, 6, 8, 9, 10, 11, 12, 13 | 2, 5, 7 | 3, 4 |
| 2024 | 1, 9, 10, 11, 12, 13 | 2, 5, 6, 7, 8 | 3, 4 |
| 2026 | 1, 12, 13 | 2, 4, 5, 6, 7, 8, 9, 10, 11 | 3 |

**Dette er en pressemelding, ikke et vedtak.** Radene skal ikke inn i
`data/`. To kontroller faller likevel ut av tabellen:

- **2026-runden bekrefter aggregatvakten.** Tre grønne (PO1, PO12, PO13),
  ni gule, én rød (PO3) er nøyaktig fordelingen
  `docs/MALING-RAD-MOT-EKSPERTVURDERING.md` brukte som ekstern vakt fra
  høringsnotatet, og som uttrekket traff på første kjøring.
- **2018-runden forklarer et hull i vedtakskilden.**
  `docs/KILDE-TRAFIKKLYSVEDTAK.md` har PO 2, 3, 4, 5 og 6 uten farge for
  runde 2018, fordi forskriften ikke nevner dem. Pressemeldingen sier at
  2, 5 og 6 var gule og 3 og 4 røde. Fargen ved utelukkelse ville altså
  vært riktig her — men den emitteres fortsatt ikke, av samme grunn som
  før: slutningen krever at forskriften er uttømmende, og
  pressemeldingen er ikke vedtaket.

---

## Kontroll: pressemeldingene mot `sources/trafikklysvedtak.py`

De fem meldingene gir farge for alle 13 områder i alle fem runder.
Kilden emitterer 40 celler. Der begge har en verdi:

    celler kilden emitterer     : 40
    enige med pressemeldingen   : 40
    uenige                      : 0

**Null motstrid.** Fire forskriftskropper lest av `parse()`, og fem
pressemeldinger lest av HTML — to uavhengige veier til samme tall, uten
et eneste avvik. Det er den sterkeste eksterne kontrollen vedtakskilden
har fått.

De 12 cellene bare pressemeldingene har, fordeler seg slik:

    gul   10
    rød    2

**Det bekrefter hypotesen i `docs/beslutninger/2026-09-05-vedtakskilden.md`,
og korrigerer den på ett punkt.** Notatet skriver at hullene i 2022 og
2024 «er områder som verken står i den grønne lista eller i § 4-tabellen
— altså gule», og at «et utvalg av celler med vedtak underrepresenterer
systematisk gult». Målt nå: ti av tolv hull er gule. De to siste er PO3
og PO4 i runde 2018, som var RØDE — og notatet forklarer allerede
hvorfor de mangler: 2018-forskriften har intet nedjusteringskapittel,
fordi «kapasiteten i de røde områdene ikke skal reduseres i denne
runden», som pressemeldingen sier ordrett.

Skjevheten er altså reell og retningen er riktig, men den er ikke
utelukkende mot gult: den er mot **alt som ikke utløser et tiltak**. I
2018 gjaldt det også rødt.

Dette endrer ikke at fargen ved utelukkelse fortsatt ikke skal emitteres.
Pressemeldingen er ikke vedtaket, og 2018-runden er nettopp beviset på at
en forskrift ikke trenger å være uttømmende om farge.
