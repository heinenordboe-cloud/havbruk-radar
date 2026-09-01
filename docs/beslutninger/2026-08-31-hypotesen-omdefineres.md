---
dato: 2026-08-31
tittel: Hypotesen omdefineres — ROC er ikke en uavhengig fasit, den er en funksjon av prediktorene våre
status: gjeldende
commit: 478e9d7
---

**Dette notatet er skrevet FØR analysen kjøres.** Det er hele poenget med
det, på samme måte som stoppregelen i `74eb87b`: en grense satt etter at
tallet er kjent, er ikke en grense. Tallgrensen i «Forventning» nedenfor
er valgt uten at noen har sett resultatet.

## Hva som ble bestemt

Hypotesen **«offentlige data forutsier ekspertgruppens vurdering»
forkastes — ikke som besvart med nei, men som feilstilt.**

ROC er ikke en uavhengig fasit å måle prediktorene våre mot. Den er en
BEREGNET FUNKSJON av de samme prediktorene, fra de samme to registrene.
En korrelasjon mellom proxyen vår og ROC er derfor ikke en måling av om
offentlige data bærer signal. Den er en måling av hvor mye informasjon
som går tapt i en kjede vi kjenner leddene i.

Erstattes av: **hvor mye av ROC er bestemt allerede i kildeleddet, før
hydrodynamisk transport?**

## Hvorfor — kjeden er lukket, og vi står i det første leddet

HIs lusemodell tar inn de samme tre størrelsene som repoets Stien-proxy,
fra de samme to registrene. Ordrett fra rapportene, om kildeleddet:

> «antall egg som klekkes av lus i oppdrettsanleggene … beregnet basert
> på innrapporterte antall voksne hunnlus per fisk, antall fisk på
> lokaliteten og vanntemperaturen på 3 m dyp (Stien mfl. 2005)»

med lusedata og temperatur fra Mattilsynet via Altinn, og fiskeantall fra
Fiskeridirektoratet. Det er våre to kilder, og vår formel.

Hele kjeden:

    lusetall × fiskeantall × temperatur
        -> Stien 2005                        <- HER STÅR VI
        -> «super» (LADiMs kildefelt)
        -> LADiM + NorKyst800
        -> kopepodittetthet
        -> terskel
        -> ROC
        -> ekspertgruppens vekting
        -> kategori

**Vår proxy regner ut nøyaktig LADiMs super-felt.** Ikke noe som ligner
det, ikke en korrelert størrelse — det samme feltet, av de samme tallene.

Og fasiten er ikke to uavhengige kilder som er enige. Ekspertgruppens ROC
og HIs ROC var **identiske på 23 av 23 overlappende celler**. Det er ett
tall gjengitt to steder, ikke to målinger som bekrefter hverandre.

## Nullresultatet fra 26.08 er informativt, ikke skuffende

Dette er notatets tyngste ledd, og det snur fortegnet på forrige økt.

`2026-08-26-full-stien-proxy-forklarer-ikke-kategoriene.md` leste en svak
sammenheng som «hypotesen er ikke bekreftet». Med kjeden over på plass er
den lesningen feil. Proxyen og kategorien er **kausalt forbundet gjennom
en kjent mekanisme** — vi står i det første leddet av den prosessen som
produserer utfallet. Da måler en svak sammenheng ikke fravær av signal.
Den måler **tap i kjeden**, og den lokaliserer tapet til leddene mellom
oss og utfallet.

Det er et resultat med retning. «Ingen sammenheng funnet» er det ikke.

Tapet må ligge ett av tre steder, og de er testbare hver for seg:

1. **Transport dominerer.** LADiM + NorKyst800 flytter kopepodittene så
   mye at kildeleddets fordeling mellom områder er svakt relatert til
   hvor de ender opp. Da er ROC i hovedsak et hydrodynamisk produkt, og
   ingen forbedring av kildeleddet vil nå den.
2. **Vår PO-aggregering ødelegger det.** Σᵢ(N_fiskᵢ × lusᵢ) ≠
   N_fisk_PO × middel(lus). HI regner per lokalitet og summerer; vi
   ganger et PO-aggregat med et PO-middel. De to er ulike størrelser med
   mindre lus og fisk er ukorrelert innen området, og det er de ikke.
3. **Ekspertgruppens øvrige innspill dominerer kategorien**, ikke
   modellproduktet. Da er ROC riktig forutsagt, men kategorien er ikke
   ROC.

Forklaring 1 og 3 er testbare med det vi har. Forklaring 2 er det ikke —
se «Utelukket kilde» nedenfor.

## Forventning, skrevet før måling

Er kildeleddet en vesentlig determinant av ROC, skal sammenhengen på de
**39 cellene** (13 PO × 2020–2022) være vesentlig sterkere enn det
proxyen oppnådde mot kategori.

De målte referansepunktene fra 26.08, mot kategorirang, fast vindu 16–24:

| prediktor | rho | rho² |
|---|---|---|
| lusetall alene | +0,510 | 0,260 |
| PO-nummer alene (ren geografi) | +0,511 | 0,261 |
| FULL Stien-proxy | +0,703 | 0,494 |
| DELVIS Stien-proxy | +0,761 | 0,579 |

**Grensen, og begge ledd må holde:**

> **1. Samlet R² ≥ 0,70** for kildeleddet mot ROC over de 39 cellene.
>
> **2. Innen-PO R² ≥ 0,25**, regnet etter at PO-middelet er trukket fra
> begge sider (39 − 13 = 26 frihetsgrader).

Holder begge: kildeleddet er en vesentlig determinant, og tapet ligger i
forklaring 3 — eller er lite.

Holder de ikke: **forklaring 1 eller 2 er riktig**, og hypotesen om at
offentlige data alene kan bære et ROC-nowcast er ferdig testet.

### Hvorfor 0,70, og ikke et rundere tall

Fordi det er der 95 %-intervallets NEDRE kant klarerer referansepunktene,
og ikke bare punktestimatet. R² = 0,70 med n = 39 gir r = 0,837, og
Fisher-z-intervallet er r ∈ [0,708, 0,911], altså **R² ∈ [0,50, 0,83]**.
Nedre kant 0,50 ligger over den fulle proxyens 0,494 og godt over 0,260.

Det gjør grensen robust mot hvilket referansepunkt man mener er det
riktige — den klarerer både 0,26 og 0,49. Den klarerer ikke den delvise
proxyens 0,579 på nedre kant, og det står med vilje: den delvise proxyen
utelater N_fisk og er derfor ikke kildeleddet.

En terskel satt på punktestimatet alene ville vært passert av et utfall
hvis intervall dekker referansen. Med n = 39 er intervallene brede nok
til at det er en reell fare.

**Grensen er ikke satt for å være passerbar.** 0,70 er om lag 1,4× den
fulle proxyens rho². Det skal være et tydelig sprang, ikke en marginal
forbedring — for det er nettopp et tydelig sprang påstanden «kildeleddet
bestemmer ROC» krever.

### Hvorfor det andre leddet finnes

Ren geografi — PO-nummeret alene, uten å kjenne lus, temperatur eller
fisk — oppnår |rho| 0,511 mot kategori. Et samlet R² på 0,70 over 39
celler kan derfor i prinsippet være **utelukkende mellom-PO-variasjon**,
altså et kart og ikke en mekanisme.

Skal kildeleddet bestemme ROC, må det også følge ROC innen ett område
over år. Innen-PO-leddet er det som skiller de to, og 0,25 er satt lavt
med vilje: det er |r| = 0,5, som med 26 frihetsgrader har nedre
95 %-kant 0,02. Leddet påstår altså bare at innen-PO-sammenhengen er
**skilt fra null** — ikke at den er sterk. Det er den svakeste påstanden
som fortsatt utelukker «det er bare geografi».

### Ett forbehold om sammenligningen

R² mot en kontinuerlig ROC og Spearman rho mot en tredelt kategorirang er
ikke samme størrelse. Sammenligningen over er veiledende, ikke eksakt.
Derfor skal Spearman rho for kildeleddet mot ROC **rapporteres ved siden
av R²** i samme kjøring, slik at det finnes ett like-for-like-tall i
loggen uansett hvordan grensen faller ut.

## Utelukket kilde til fiskeantall per lokalitet

HIs ukentlige lusestatus (`ftp.imr.no/anneosea/Rapporter/lakselus.pdf`,
arkivert som `data/arkiv/hi-lakselus-ukesstatus/2026-08-26.bin.gz`) er
undersøkt og **utelukket** som kilde til Stien-kildeleddet per lokalitet.
To uavhengige grunner, begge målt:

1. **Figurene er raster.** 53 sider, **0 path-operatorer** i noen
   sidestrøm. 104 Form-XObjects, og alle 104 er 34–37 byte som ikke gjør
   annet enn å plassere ett Image-XObject: `q / cm / Do / Q`. 104
   Image-XObjects, `/DeviceRGB`, `/FlateDecode`. `/Producer =
   pdfTeX-1.40.14`, `/Creator = LaTeX with hyperref package` — LaTeX satte
   teksten, men figurene ble importert ferdig rastrert. Ingen `Tj`/`TJ` i
   formene, så akseticks finnes ikke som tekst og kan ikke kalibrere noe.
2. **Verdien er relativ uansett.** «Utslipp per anlegg» er et KART der
   per-lokalitet-verdien er kodet i farge, og HIs egen figurtekst sier at
   «Fargeskalaen er relativ, og viser bare innbyrdes variasjon!». Selv en
   eksakt vektoravlesning ville gitt lat/lon vi allerede har fra
   Akvakulturregisteret, pluss en rangering innad i ett PO for én uke —
   ikke millioner klekte egg per time.

Den eneste kvantitative serien i rapporten (millioner klekte egg per
time) er eksplisitt **summert over alle rapporterende anlegg i PO-et**.
Det er PO-aggregatet vi allerede har.

**Konsekvens: forklaring 2 kan ikke elimineres direkte med offentlig
tilgjengelige data i dag.** PO-aggregeringen står som en dokumentert,
ikke-reduserbar tilnærming inntil fiskeantall per lokalitet publiseres.
Det er en kjent grense for hva denne analysen kan avgjøre, og den skal
oppgis sammen med resultatet — ikke oppdages av den neste som leser det.

Merk hva dette gjør med tolkningen av et negativt utfall: faller
grensen, kan vi **ikke** skille forklaring 1 fra forklaring 2. Vi kan
bare si at kildeleddet slik VI kan regne det ut, ikke bestemmer ROC.

## Grunnlaget er endret 01.09.2026 — grensen må settes på nytt

Notatet forutsetter **39 celler** (13 PO × 2020–2022). Den forutsetningen
holder ikke lenger: ekspertgrupperapportene for 2023, 2024 og 2025 er
funnet i Nasjonalt vitenarkiv og lest inn (`sources/ekspertgruppen.py`).

| | før | nå |
|---|---|---|
| (po, år)-celler med `kategori` | 78 | **116** |
| ettårsoverganger | 52 | **90** |
| herav kategoriskift | 13 | **19** |
| ROC-celler (`hi_smittepress_roc_indeks`) | 33 (2021–2022) | **43** (2021–2025) |
| ROC ettårsoverganger | 11 | **29** |

**Grensen R² ≥ 0,70 er IKKE flyttet, og analysen er ikke kjørt.** Men
tallet 39 i «Forventning» er nå feil, og begrunnelsen for 0,70 hviler på
n = 39 gjennom Fisher-z-intervallet. Med et større n blir intervallet
smalere, og terskelen som klarerer referansepunktene på nedre kant
faller. Regnestykket skal gjøres på nytt **før** analysen kjøres — det er
hele poenget med at grensen ble skrevet først.

To ting må avklares før den nye grensen kan settes:

1. ~~**ROC-dekningen for 2025 er 2 av 13 PO.**~~ **Undersøkt 01.09.2026,
   og det var en bug.** Parseren leser nå **12 av 13 i hvert år
   2021–2025** — 60 celler mot 43 — med PO1 som eneste, ekte fravær.
   Fem setningsformer og én ny avsnittsetikett felte uttrekket; se
   `docs/KILDE-EKSPERTGRUPPEN.md`.

   **MEN: tallet 60 er parserens, ikke diskens.** `backfill.py
   --rapporter` hopper over et år der `published_at` alt finnes, så en
   PARSERretting kan ikke skrives inn gjennom den veien. Snapshotene bærer
   fortsatt 43. Skal 60 inn i et panel, må de re-deriveres bevisst — og
   `diff.revisjon()` kaster `Grunnlagssprik` mellom `source_version` 2 og
   3, som er riktig: en forskjell kan da like gjerne være vår parser som
   kildens revisjon.
2. **PO9 i 2024 og 2025 har ingen `kategori`.** Kilden nekter å velge
   («Lav til moderat»), verdien ligger i `kategori_ordrett`, og cellene
   faller derfor ut av rangbaserte mål. 2024 er senere revidert til
   moderat av 2025-rapporten; 2025 står uavklart.

## Grensen satt på nytt 01.09.2026 — fordi celletallet endret seg

**Dette er ikke en oppmykning etter et resultat. Analysen er fortsatt
ikke kjørt.** Grunnlaget under grensen falt bort da ROC-parserbugen ble
rettet (`600554c`), og en grense begrunnet på et celletall som ikke
stemmer, er ingen grense. De gamle tallene står uendret over; dette er
en tilføyelse, ikke en overskriving.

### Hva som endret seg

    n           39  ->  60      (13 PO x 3 år  ->  12 PO x 5 år)
    grupper     13  ->  12      PO1 oppgir legitimt ingen ROC i noe år
    n per PO     3  ->   5
    frihetsgrader innen PO   39-13 = 26  ->  60-12 = 48

### Nytt samlet ledd: **R² ≥ 0,67**

Samme metode som før: finn den R² hvis 95 %-intervalls NEDRE kant
klarerer den fulle Stien-proxyens rho² = 0,494. Fisher-z, df = n − 3.

| n | eksakt løsning | 95 % CI for R² | avrundet grense |
|---|---|---|---|
| 39 (gammel) | R² = 0,6948 | [0,494, 0,828] | 0,70 |
| 60 (ny) | R² = 0,6592 | [0,494, 0,781] | **0,67** |

Grensen faller fordi intervallet er smalere ved n = 60, ikke fordi
kravet er mildere: nedre kant ligger på samme sted mot samme
referansepunkt. Ved R² = 0,67 og n = 60 er intervallet
[0,508, 0,788] — nedre kant over 0,494 (full proxy) og godt over 0,260
(lusetall alene) og 0,261 (PO-nummer alene).

**0,67 og ikke 0,66,** som den eksakte løsningen ville tillatt: disken
holder i dag 58 ROC-celler, ikke 60. Differansen er PO7 i 2021 og 2022,
som ligger i committede v1-snapshots og bevisst ikke er rørt. Ved
n = 58 gir R² = 0,66 nedre kant 0,4918 — så vidt UNDER referansen —
mens 0,67 gir 0,5047. Grensen skal ikke avhenge av en beslutning som
ikke er tatt, og 0,67 klarerer begge.

### Innen-PO-leddet står på **R² ≥ 0,25**

Samme metode gir samme tall. Metoden var aldri «løs for nedre kant lik
null»; den var «velg |r| = 0,5, og kontroller at den er skilt fra null».

    13 PO à 3 år, df = 26:  R² = 0,25, 95 % CI R² = [0,027, 0,536]
    12 PO à 5 år, df = 48:  R² = 0,25, 95 % CI R² = [0,068, 0,465]

Leddet er fortsatt **den svakeste delen av regelen** — det påstår bare at
innen-PO-sammenhengen er skilt fra null, ikke at den er sterk. Det som
er endret er at **n per gruppe gikk fra 3 til 5**, og med 48
frihetsgrader mot 26 hviler den samme påstanden på mer: nedre kant har
flyttet seg fra 0,027 til 0,068.

Terskelen er IKKE senket selv om de 48 frihetsgradene ville tillatt det
(samme margin som før nås ved R² ≈ 0,12). Å flytte en grense nedover
etter at grunnlaget ble bedre, uten at spørsmålet er endret, er hvordan
en stoppregel mister tennene. Marginen beholdes som margin.

### Hvorfor leddet finnes, uendret

Ren geografi — PO-nummeret alene — når |rho| 0,511 mot kategori uten å
kjenne lus, temperatur eller fisk. Et samlet R² kan i prinsippet være
utelukkende mellom-PO-variasjon, altså et kart og ikke en mekanisme.

## Hva som ville snudd det

- Dokumentasjon på at HI bruker en **annen formel eller andre registre**
  enn rapportene oppgir. Da er kjeden over feil, og ROC er mer uavhengig
  av prediktorene våre enn dette notatet legger til grunn.
- **Fiskeantall per lokalitet blir offentlig**, slik at forklaring 2 kan
  elimineres direkte i stedet for å stå som forbehold.
- En kilde som gir ROC eller kopepodittetthet fra en **annen modellkjede**
  enn LADiM/NorKyst800. Da finnes det igjen en uavhengig fasit, og den
  opprinnelige hypotesen kan stilles på nytt — riktig denne gangen.

## [KREVER BRUKERENS AVGJØRELSE — IKKE FYLT INN]

**Skal prosjektet forfølge nowcasting av ROC som mulig produkt, eller
holdes som ren analyse?**

Valget avgjør to ting som ikke kan avgjøres nedenfra:

- **hvor ofte kildeleddet må beregnes** — et nowcast krever ukentlig
  kjøring i takt med lusetallenes rytme; en analyse trenger bare én
  kjøring per (PO, år)
- **hvor mye av året som må dekkes** — et nowcast trenger hele
  produksjonssyklusen; analysen trenger bare utvandringsvinduet, som
  dessuten er PO-avhengig og fortsatt ikke rettet
  (se 26.08-notatet, «Hvor skjør målingen er»)

Avsnittet fylles inn av brukeren. Det står tomt med vilje: rekkefølgen i
dette notatet er at grensen settes før målingen, og produktvalget tas av
den som eier prosjektets formål — ikke av den som skriver analysen.

## Kjøringen dette notatet går FORAN

Ingen. Analysen er ikke kjørt, og `analyse/` er urørt i denne økten.
Det er tilsiktet: notatet skal ligge i git før tallet finnes, slik at
grensen kan etterprøves mot en commit som er eldre enn resultatet.
