---
dato: 2026-09-15
tittel: Taushet er ikke tilbaketrekking — diff kan ikke skille «sa ingenting» fra «fjernet verdien»
status: utkast — INGEN BESLUTNING TATT
commit: [fylles inn]
---

## Hva dette er

**Et beslutningsGRUNNLAG, ikke en beslutning.** Avveiningen legges fram;
valget er ikke tatt, og ingen kode er endret. Filen følger
mappekonvensjonen for øvrig, men har med vilje ingen «Hva som ble
bestemt»-del — den fylles inn når valget er gjort, sammen med
reverseringskriteriet README ber om.

## Problemet

`diff.revisjon()` kan ikke skille «kilden uttaler seg ikke om denne
cellen» fra «kilden har fjernet verdien». Begge blir en `revidert`-rad
med `new_value = null`, og den raden leses som en tilbaketrekking.

For `trafikklysvedtak` er det målt usant i hvert eneste tilfelle.

---

## 1. Hva som faktisk skjer

`diff.revisjon_mellom()` joiner to versjoner av samme `observed_at` på
`(entity_id, field)` og filtrerer bort feltnavn som bare finnes på én
side. Filteret er **entitetsblindt** — `felles_felter` er feltnavnene
som finnes *et sted* i hver ramme, ikke de kilden uttalte seg om for
*denne* entiteten:

```python
felles_felter = (set(eldre["field"].unique().to_list())
                 & set(nyere["field"].unique().to_list()))
```

Står `farge` i den nyere kroppen for PO3, overlever `farge` filteret for
alle tretten områdene. PO9, som den nyere kroppen ikke nevner, får da en
rad som sier `gronn -> null`.

Funksjonens egen docstring sier at dette er tilsiktet:

> Merk at filteret går på FELTNAVN og ikke på entiteter. En entitet som
> dukker opp eller forsvinner mellom to versjoner av samme måned ER en
> revisjon — kilden har flyttet noe inn i eller ut av det tidsrommet.

Det er riktig for biomasse, som er kilden aksen ble bygget for. En
lokalitet som forsvinner fra en måned i biomassefila ER flyttet ut av
den måneden. Antakelsen bak er at **kroppen er uttømmende om
nøkkelrommet**: hver publisering uttaler seg om hver (lokalitet, måned).

`trafikklysvedtak` bryter den antakelsen ved konstruksjon.
2026-forskriftens § 4-tabell har tre rader. Det er ikke et utsagn om de
ti andre områdene — det er fravær av et utsagn.

## 2. Hvor stort det er, målt

Alle `revidert`-rader i changeloggen 15.09.2026:

| kilde | rader | `new=null` | `old=null` | ekte verdiendring |
|---|---:|---:|---:|---:|
| biomasse | 1809 | **0** | 0 | 1809 |
| ekspertgruppen | 26 | **2** | 4 | 20 |
| trafikklysvedtak | 38 | **34** | 2 | 2 |
| **sum** | **1873** | **36** | 6 | 1831 |

Pluss **12 rader som ble holdt tilbake 15.09** — 2026-kroppens
restatement av runde 2024, der PO 1, 9, 10, 11, 12 og 13 ikke er nevnt.
De er ikke skrevet; se commit `564fb85` i datarepoet. Hadde de gått inn,
ville `trafikklysvedtak` hatt 46 og repoet 48.

**Andelen er liten og konsentrasjonen er total.** 1,9 % av alle
revisjonsrader, men 89 % av `trafikklysvedtak` sine.

### De tre kildene oppfører seg ulikt, og det er selve funnet

**biomasse: 0 av 1809.** Fila bærer hele serien i hver publisering, så
hver kropp uttaler seg om hvert nøkkelpar. Taushet forekommer ikke.
Antakelsen holder perfekt her.

**trafikklysvedtak: 34 av 38.** Kroppen uttaler seg om et lite og
krympende utvalg. Den grønne lista gikk åtte → seks → tre, § 4-tabellen
står på tre rader. Jo nyere forskrift, jo mer taushet.

**ekspertgruppen: 2 av 26**, og de er en tredje form. Det er ikke en
entitet som mangler, men ett felt for én entitet:

```
2020-12-31  PO6  metode_hi_virtuell_smolt_retning              opp   -> null
2020-12-31  PO6  metode_hi_virtuell_smolt_retning__sikkerhet   tabell -> null
```

Feltet `metode_hi_virtuell_smolt_retning` finnes i den nyere kroppen —
for PO2, som fikk det samtidig. Derfor overlever det `felles_felter`, og
PO6 får en tilbaketrekking den nyere rapporten aldri uttalte.

Det viser at problemet ikke er «hele entiteten mangler». Det er at
**nøkkelrommet en kropp uttaler seg om, ikke finnes noe sted i dataene.**

## 3. Hvilke kilder det rammer

Aksen kjøres av fire backfill-strategier: `_arkivkopi` (410),
`_backfill_maaneder` (633), `_backfill_hendelser` (850) og
`_backfill_rapporter` (1209). Fire kilder står på den.

Det avgjørende er ikke om kilden reviderer, men om **kroppen er
uttømmende over nøkkelrommet sitt** — uttaler den seg om hvert par den
kan uttale seg om, eller velger den?

| kilde | strategi | uttømmende kropp? | rammet |
|---|---|---|---|
| biomasse | `hent_alt` | **ja** — hele serien per publisering | nei, målt 0 av 1809 |
| romming | `aar_i` → `_backfill_hendelser` | **ja** — alle hendelser for året | nei, 0 rader i dag |
| ekspertgruppen | `utgivelser` | **nei** — en rapport tabellerer det den vil | ja, 2 rader |
| trafikklysvedtak | `utgivelser` | **nei** — § 4 har tre rader | ja, 34 (+12) |
| lusetall, sjotemperatur | `hent_uke` | — | nei, revideres ikke |
| akvakultur, enhetsregisteret | ukentlig | — | nei, revideres ikke |
| eierskap | `overforinger` | egen strategi, kaller ikke `revisjon()` | nei |
| reguleringsomraader, biomasselag | ingen | — | nei |

**To av elleve rammet i dag, fire på aksen.** For biomasse og romming er
en forsvunnet entitet en EKTE hendelse — lokaliteten ble flyttet ut av
måneden, meldingen ble trukket — og dagens oppførsel er riktig for dem.
Det er derfor problemet ikke kan løses ved å slå av mekanismen.

Kriteriet er ikke kildenavnet, det er formen: *kan én kropp si noe om et
nøkkelpar en annen kropp tier om?* Skillet følger datakilde mot dokument.
En API-dump svarer på alt den blir spurt om; et dokument skrives for å si
det som er nytt. Enhver framtidig `utgivelser`-kilde som leser dokumenter
vil derfor ligge på feil side.

### Samme feil finnes på TIDSAKSEN, og den er ikke filtrert

`diff.compare()` har problemet i speilvendt form. Snapshotet skrevet
15.09 for runde 2026 bærer seks `borte`-rader:

```
PO9   farge  gronn -> null  borte
PO10  farge  gronn -> null  borte
PO11  farge  gronn -> null  borte   (+ de tre lesemåteradene)
```

De sier at PO 9, 10 og 11 mistet det grønne lyset mellom 2024 og 2026.
De står ikke i 2026-forskriften, det er alt.

**Og `borte` filtreres ikke av `diff.bevegelse()`.** `IKKE_BEVEGELSE` er
`utvalgsutvidelse` og `revidert`. En telling av «endringer denne uka»
ser disse seks; den ser ikke de 34. Løsningen må derfor dekke begge
akser, ellers flytter feilen seg fra den filtrerte aksen til den
ufiltrerte.

## 4. Hva det koster i dag å la det stå

Radene er **ikke datatap**. Changeloggen er avledet og kan regnes ut på
nytt fra snapshotene (CLAUDE.md regel 2), begge snapshots står, og
`diff.bevegelse()` holder `revidert` utenfor ukas endringstall.

Kostnaden er tre ting:

1. **Leseregelen må huskes.** `docs/KILDE-TRAFIKKLYSVEDTAK.md` punkt 9
   sier at gjeldende farge er den fra den nyeste kroppen *som uttaler
   seg*. Den regelen finnes bare i prosa. En analyse som leser
   changeloggen rett fram får feil svar uten å få noe varsel.
2. **Det blokkerer skriving.** De 12 radene 15.09 ble holdt tilbake, og
   det betyr at 2026-kroppens bekreftelse av runde 2024 **ikke er
   ført noe sted i dataene**. Enigheten finnes bare i en commit-melding.
   Det er et reelt tap, og det vokser med hver ny forskrift.
3. **Tallet vokser raskere enn kilden.** Hver ny kapasitetsforskrift
   restaterer flere runder mot en krympende områdeliste. 2028-kroppen vil
   gi flere slike rader enn 2026-kroppen ga.

## 5. Løsningene

### A. Kilden oppgir hvilke nøkler kroppen uttaler seg om

Et felt på `Source`, stemplet på raden av kjernen som `utvalg` og
`published_at` — for eksempel `uttaler_seg_om`, satt av `parse()` til de
`entity_id`-ene kroppen faktisk behandlet. `diff` sammenligner da bare
nøkler som finnes i BEGGE kroppers domene.

**For:** Dette er CLAUDE.md 1b-3 nesten ordrett — en verdi som avgjør
hva dataene BETYR, lagret SAMMEN med dem. Prøven («kan et snapshot alene
svare på hva denne verdien var da raden ble skrevet?») er nei i dag, og
det er hele feilen. Den løser begge akser med én mekanisme, og den er
etterprøvbar: domenet står på raden.

Den er også den eneste løsningen som kan uttrykke **bekreftelse**. «2026
sa det samme om PO3 som 2024 gjorde» er en påstand som krever at man vet
at 2026 uttalte seg om PO3.

**Mot:** Den er dyrest. Et femte proveniensfelt på `Observation`, med
alt det innebærer: `snapshot.write()`, `CHANGE_SCHEMA`, `runner.stempl`,
lesing av gamle snapshots uten feltet. Og kjernen må endres — CLAUDE.md
regel 1 sier at det er brukerens avgjørelse, ikke kildens.

Gamle snapshots har det ikke, og det kan ikke fylles inn retroaktivt
(1b-7 om `published_at`: 103 biomasse-snapshots ville påstått noe ingen
har gått god for). Det gir en overgangsperiode der regelen bare virker
framover, og «ukjent domene» må falle tilbake på dagens oppførsel.

Merk også at domenet ikke alltid er en entitetsliste. For ekspertgruppen
er den tause enheten (PO6, `metode_hi_virtuell_smolt_retning`) — et
`(entity_id, field)`-par. Feltet må bære par, ikke bare id-er, ellers
løser det trafikklys og ikke ekspertgruppen.

### B. En egen `change_type`

Et femte navn ved siden av `ny`, `endret`, `borte`, `revidert` — for
eksempel `ikke_uttalt` — som brukes når `new_value` er null og kilden er
en som kan tie.

**For:** Billig. `diff.py` og `IKKE_BEVEGELSE`, ingen nye felter, ingen
endring i `Observation` eller i snapshotformatet. Fanger begge akser.
Radene beholdes og blir synlige som det de er.

**Mot:** **Den avgjør ikke spørsmålet, den navngir svaret vi gjetter
oss til.** Uten et domene på raden kan `diff` ikke VITE at fraværet er
taushet — den kan bare anta det. Og for biomasse ville antakelsen vært
gal: der ER et fravær en flytting ut av måneden, og en `ikke_uttalt`-rad
ville skjult en ekte revisjon.

Det gjør den til en kildeavhengig regel forkledd som en generell. Skal
den virke, må den likevel hvile på noe som sier hvilke kilder som kan
tie — og da er man tilbake til å lagre den opplysningen et sted.

Dette er formen CLAUDE.md 1b-2 navngir: en mekanisme som måler noe som
LIGNER det den skal måle, og som er riktig i akkurat de tilfellene der
de to faller sammen.

### C. Entitetsskopet skjemafilter

Endre `felles_felter` fra global til per entitet: sammenlign bare
`(entity_id, field)`-par som finnes på begge sider.

**For:** Billigst av alle. Én linje i `revisjon_mellom()` og én i
`compare()`. Fjerner alle 36 + 12 rader umiddelbart, og fikser
ekspertgruppen-tilfellet like godt som trafikklys, fordi den allerede
opererer på par.

**Mot:** **Den kan ikke uttrykke en ekte fjerning.** En lokalitet som
faktisk forsvinner fra en måned i biomassefila ville blitt stille
undertrykt — og det er 1809 rader hos den ene kilden som *skal* kunne
si dette. Den bytter en usann påstand mot en usynlig hendelse, og
CLAUDE.md er gjennomgående strengere mot det andre («en undertrykt rad
er en hendelse ingen får se», 1b-3).

Den ville også være taus om biomasses framtidige fjerninger uten at noe
sa fra — feilen flytter seg fra å være synlig og gal til å være
usynlig.

### D. En erklæring per kilde

Et klassefelt, for eksempel `kropp_er_uttommende: bool`, som `diff`
leser. True for biomasse, False for trafikklysvedtak og ekspertgruppen.

**For:** Billig, og ærlig om at dette ER en kildeegenskap. Løser C sitt
problem: biomasse beholder sine 1809 rader, de to andre slipper sine.
Ingen endring i snapshotformatet.

**Mot:** Bryter 1b-3 der den er skarpest. Verdien avgjør hva radene
BETYR og ligger i kode, ikke på raden — akkurat der næringskodelista lå
før 24.08.2026. Et gammelt snapshot kan da ikke svare på hva regelen var
da raden ble skrevet, og en endring i flagget endrer retroaktivt hva
hele historikken betyr.

Den er dessuten for grovkornet for ekspertgruppen, som er uttømmende om
SINE felter i noen tabeller og ikke i andre. `kategori` står for alle
tretten i hver rapport; `metode_hi_virtuell_smolt_retning` gjør ikke.
Ett flagg per kilde kan ikke uttrykke det.

### E. La det stå, og gjør leseregelen maskinlesbar

Ingen endring i `diff`. I stedet en funksjon — `diff.gjeldende()` eller
lignende — som gir gjeldende verdi per (dato, entitet) ved å gå
versjonene i publiseringsrekkefølge og hoppe over dem som ikke uttaler
seg.

**For:** Ingen endring i skjema, ingen i changeloggen, ingen i
historikken. Flytter regelen fra prosa i punkt 9 til kode som kan testes.

**Mot:** Løser lesingen, ikke skrivingen. De 12 radene fra 15.09 er
fortsatt uskrivbare, changeloggen bærer fortsatt 36 usanne påstander, og
`borte`-radene på tidsaksen telles fortsatt som bevegelse. Og funksjonen
må selv avgjøre «uttaler seg ikke om» — altså trenger den det samme
domenet som A, bare beregnet ved lesing i stedet for lagret ved
skriving.

Det er `core/persondata.PERSONFORMER` om igjen: en regel som virker ved
LESING kan endre hva et gammelt snapshot betyr. CLAUDE.md fører allerede
den som et kjent, åpent avvik.

## 6. Avveiningen, kort

| | kostnad | løser skriving | løser begge akser | etterprøvbar fra raden | dekker ekspertgruppen |
|---|---|---|---|---|---|
| A domene på raden | høy, `core/` + skjema | ja | ja | **ja** | ja, hvis par |
| B egen change_type | lav | delvis | ja | nei | nei uten D |
| C entitetsskopet filter | **lavest** | ja | ja | nei | ja |
| D flagg per kilde | lav | ja | ja | nei | **nei** |
| E lesefunksjon | lav | **nei** | nei | nei | ja |

To spørsmål avgjør, og de er uavhengige:

**Er en usann påstand verre enn en usynlig hendelse?** C og D fjerner
rader. A og B beholder dem og merker dem. Repoet har svart på dette før,
og svart begge veier: skjemautvidelsen SLETTES fordi påstanden er sikker
fra de to snapshotene alene, utvalgsutvidelsen MERKES fordi den hviler
på et felt som kan være tomt (1b-3). **Her er påstanden ikke sikker fra
snapshotene alene** — det er nettopp det som mangler — og analogien
peker da mot merking, altså mot A eller B.

**Er dette verdt en `core/`-endring nå?** Det er 36 rader på disk, 1,9 %
av revisjonsaksen, og leseregelen er dokumentert. Mot det står at
bekreftelsen fra 2026-kroppen ikke lar seg skrive i det hele tatt, og at
tallet vokser med hver forskrift. CLAUDE.md regel 1 sier at når en kilde
later til å kreve en endring i `core/`, skal kontrakten meldes mangelfull
og brukeren avgjøre. **Det er det denne saken er.**

## 7. Hva som IKKE er et alternativ

**Å utlede fargen ved utelukkelse.** «Verken grønn eller rød peker mot
gul» er sant for tre av hullene og usant for 2018-kroppen, som ikke har
noe nedjusteringskapittel i det hele tatt. Kilden er bygget på fravær
framfor gjetning, og det står fast.

**Å skrive de 12 radene og forklare dem i commit-meldingen.** Det er
gjort én gang allerede — de 34 fra 05.09 står på disk med en forklaring
i punkt 9. Å gjenta det er å la mengden usanne rader vokse mot en prosa
ingen leser ved siden av dataene.

## 8. Åpent

- Om A velges: skal domenet bære `entity_id` eller `(entity_id, field)`?
  Ekspertgruppen krever det siste; trafikklysvedtak klarer seg med det
  første. Å velge det billigste løser én kilde og ikke den andre.
- Hva gjør en kropp som uttaler seg om en entitet ved å si «uendret»?
  Ingen av dagens kropper gjør det, men en forskrift som skrev «PO9
  beholder grønt lys» ville vært et utsagn, ikke taushet, og uttrekket
  ville ikke sett forskjellen.
- `borte`-radene på tidsaksen: skal de inn i `IKKE_BEVEGELSE` uavhengig
  av hva som velges her? De seks fra 2026-snapshotet telles som bevegelse
  i dag.

## Kilder til tallene

- Rad-tellingene: `data/changelog/*/*.parquet`, alle `change_type =
  revidert`, lest 15.09.2026.
- De 12 tilbakeholdte: `diff.revisjon()` mot `2024-12-31` med
  2026-kroppen, kjørt uten skriving 15.09.2026.
- De seks `borte`: `data/changelog/trafikklysvedtak/2026-12-31.parquet`,
  skrevet 15.09.2026 (datarepo `564fb85`).
- Tidligere måling av de 34: `docs/KILDE-TRAFIKKLYSVEDTAK.md` punkt 9,
  backfillen 05.09.2026.
