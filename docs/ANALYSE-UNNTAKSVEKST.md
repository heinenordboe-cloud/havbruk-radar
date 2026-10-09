# Analyse 09.10.2026 — unntaksvekst 2025/2026, fra søknad til drift

For hver lokalitet Mattilsynet godkjente eller avslo for unntaksvekst
2025/2026: (a) fikk tillatelsene på lokaliteten mer kapasitet i
registeret, når og hvor mye, og (b) hvordan har lokaliteten driftet
målt mot vilkårene for unntaksvekst?

Kode: `unntaksanalyse.py` (alle tallene), `arkiver_lovdata.py` og
`arkiver_mattilsynet.py` (hentingen), `nettsted.bygg_unntaksvekst()`
(siden /analyse/unntaksvekst/). Kjør selv:

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data .venv/bin/python unntaksanalyse.py

**Merkene:** MÅLT = holdt mot en arkivkropp, sha256 oppgitt. MÅLBAR =
regnet av arkiverte kropper med en regel vi har valgt (regelen står),
eller regnestykke på målte tall. IKKE MÅLBAR = ingen kilde vi har, sier
noe om det. Hvert funn har én linje «Feil hvis».

**Ingenting i dette notatet sier at en lokalitet har oppfylt eller brutt
et vilkår.** Tall står ved siden av vilkårets tall. Hvert vilkår har
deler ingen kilde vi har, kan måle.

## De to sterkeste funnene

**1. Ingen tillatelse på lokalitetene fikk mer enn 1 % i registeret, og
1 % fikk også en avslått lokalitet (F2.2 — MÅLT).** Mellom eierskaps-
kroppene 02.09 og 05.10.2026 endret kapasiteten seg på tillatelser
knyttet til fire av de 54 sikkert koblede lokalitetene, alle i PO 13 og
alle mellom 28.09 og 05.10: 13691 (Avslag) +80 t, 15957 +55 t, 29416
+58 t og 33777 +58 t (Godkjent). Hver eneste endring er nøyaktig
round(x × 1,01) — kapittel 3 i kapasitetsjusteringsforskriften 2026, som
gjelder alle tillatelser i PO 1, 12 og 13 uansett unntak. Økningen
unntaket gir (kapittel 4, inntil 6 %), har søknadsfrist hos
fylkeskommunen 28.09.2026 og skal deretter beregnes, tilbys og aksepteres
før den føres inn.
*Hvorfor sterkest:* aritmetikken er eksakt på alle åtte tillatelsene som
endret seg (91 t til sammen — samme antall og tonn som F1.1 i
docs/MALING-FUNN-OKTOBER.md fant for PO 13), holdt mot fem kropper med
hash, og prosessen den venter på står ordrett i forskriften.
*Feil hvis:* en økning etter unntaket ble registrert før 02.09.2026 (før
eierskapsserien) eller etter 05.10.2026 (neste kropp er mandag
12.10.2026). Forskriften trådte i kraft 20.08.2026, så vinduet
20.08–02.09 er ikke dekket.

**2. Kontrollen skiller ikke godkjente fra avslåtte (F4.1 — MÅLBAR).** I
kvalifikasjonsperioden (uke 40/2023–39/2025) ligger like stor andel av
de 45 godkjente og de 8 avslåtte innenfor vilkårets tall på hvert tall vi
kan regne. Laveste p-verdi (Fishers eksakte test, tosidig) er 0,15. Bare
11 av 45 godkjente har ingen telling ≥ 0,10 i uke 13–39, og 19 av 45 har
høyst seks ikke-medikamentelle oppføringer.
Tabellen har 46 godkjente lokaliteter og kontrollen 45, fordi ÅPENVIK
(29416) ikke har én telling hos Mattilsynet i kvalifikasjonsperioden og
derfor er holdt utenfor kontrollen.
*Hvorfor sterkest:* det er bestillingens egen kontroll, og svaret er
negativt på alle åtte tall, også de to lesemåtene av annet ledd b.
*Feil hvis:* tallene ikke måler det Mattilsynet vurderte — en
«oppføring» er ikke en «behandling», per-fisk-regnskapet og
egg-alternativet i nr. 1 er ikke regnet, og API-et mangler 53 tellinger
i okt–nov 2023 — eller forskjellen er der, men for liten til å sees med
8 avslag.

Funnet som sto som nummer 3 til 09.10.2026 — de godkjente har flere
medikamentelle oppføringer etter kvalifikasjonsperioden enn i den — er
tatt ut her og av analysesiden. Det står under «Ikke publisert» nederst,
med grunnen.

Svakere, og hvorfor: at annet ledd b bare er innenfor for 10 av 45
godkjente lest over hele perioden, men 42 av 45 lest innen uke 13–39
(F4.2), sier noe om hvordan bokstaven kan leses — ikke hvordan
Mattilsynet leste den. ÅPENVIK (29416) er godkjent uten én rapport i API-et
i kvalifikasjonsperioden (F3.5), men BarentsWatch har fem tellinger der,
så det er et hull i API-et og ikke i driften.

---

## 1. Vilkårene

**F1.1 — MÅLT.** Vilkårene står i produksjonsområdeforskriften
(FOR-2017-01-16-61) § 12 første ledd bokstav b nr. 1–6 og annet ledd,
med søknad og kvalifikasjonsperiode i § 12a. Ordrett, lest av kroppen
`lovdata-produksjonsomradeforskriften/2026-10-09.bin.gz`
(SF, sist endret FOR-2026-04-26-689),
sha256 `f44406e410705f3dc1529a3dad672ae29a1c10a09aa276512e94382a9eadd3be`:

> Uavhengig av miljøstatus i produksjonsområdet, kan departementet gi
> tilbud om økt kapasitet til innehaver av tillatelse som har lokaliteter
>
> a. der lakseluslarver ikke slippes ut i frie vannmasser, og det er
> dokumentert av en upartisk faginstans at lokaliteten tillatelsen er
> knyttet til er utformet slik at egg og frittsvømmende stadier av
> lakselus ikke slippes ut i frie vannmasser, eller
>
> b. som i vesentlig mindre grad enn andre har bidratt til å påvirke
> smittepresset av lakselus i løpet av en kvalifikasjonsperiode på to år
> ved å oppfylle gitte vilkår. Kvalifikasjonsperioden går fra og med uke
> 40 i et oddetallsår til og med uke 39 i neste oddetallsår. For
> lokaliteten tillatelsen er knyttet til skal følgende vilkår være
> oppfylt:
>
> 1. Det var færre enn 0,1 voksne hunnlus i gjennomsnitt per fisk ved
> alle tellinger fra og med uke 13 til og med uke 39 i
> kvalifikasjonsperioden, eller det ikke er sluppet ut flere egg og
> frittsvømmende stadier av lakselus til miljøet enn det ville vært
> sluppet ut fra et tilsvarende antall fisk med et lusenivå under 0,1
> voksne hunnlus i gjennomsnitt per fisk.
> 2. Grensene i forskrift 5. desember 2012 nr. 1140 om bekjempelse av
> lakselus § 8 har ikke vært brutt fra og med uke 40 til og med uke 12 i
> kvalifikasjonsperioden. Tilsvarende gjelder brudd på særskilte vilkår
> om lus i den enkelte tillatelse.
> 3. Det kan dokumenteres at det har vært gjennomført maksimalt én
> medikamentell behandling mot lakselus i kvalifikasjonsperioden per
> lokalitet eller per fisk fra fisken settes i sjø til den slaktes. En
> medikamentell behandling er bruk av ett preparat forskrevet til
> lokaliteten, brukt i tråd med preparatomtalen eller i tråd med (EU)
> 2019/6 artikkel 114, jf. forskrift om legemidler til dyr § 1-10.
> 4. Det kan dokumenteres at det har vært gjennomført maksimalt seks
> ikke-medikamentelle behandlinger mot lakselus i kvalifikasjonsperioden
> per lokalitet eller per fisk fra fisken settes i sjø til den slaktes.
> En ikke-medikamentell behandling er fjerning av lus med midler eller
> metoder som ikke er legemidler, og som innebærer fysisk håndtering av
> fisken.
> 5. Det har blitt avsluttet et utsett ved å slakte fisken. Dersom fisken
> er flyttet til en annen lokalitet, må vilkårene ha vært oppfylt på alle
> lokaliteter samlet innenfor kvalifikasjonsperioden for den enkelte
> fisk.
> 6. Det er ikke fattet vedtak om midlertidig biomassereduksjon etter
> forskrift 5. desember 2012 nr. 1140 om bekjempelse av lakselus med
> effekt innenfor kvalifikasjonsperioden.
>
> Selv om det observerte lusenivået på en lokalitet overskrider
> lusegrensen angitt i første ledd bokstav b, nr. 1, kan departementet
> likevel gi tilbud til innehaver av tillatelse så fremt lokaliteten
>
> a. ikke har hatt 0,17 eller flere voksne hunnlus per fisk ved
> rapporteringspliktige tellinger mer enn én gang fra og med uke 13 til
> og med uke 39 hvert år i kvalifikasjonsperioden, og
>
> b. ikke har hatt 0,10 eller flere voksne hunnlus per fisk ved fire
> rapporteringspliktige tellinger på rad.

§ 12a, samme kropp:

> Søknad om å få vurdert om en lokalitet oppfyller vilkårene etter § 12
> sendes på fastsatt skjema til Mattilsynet innen 1. september i
> oddetallsår. Nødvendig dokumentasjon for perioden mellom 1. august og
> uke 40 ettersendes innen utgangen av uke 42. Mattilsynet kan be om
> eventuell tilleggsdokumentasjon.

Lakselusforskriften (FOR-2012-12-05-1140) § 8 første og annet ledd,
`lovdata-lakselusforskriften/2026-10-09.bin.gz`,
sha256 `0ae73fa83534c0f4eade75ebf749a86657a423ee2b8a7d8fecc71c577d37fa23`:

> I Nord-Trøndelag og sørover skal det fra og med mandag i uke 16 til og
> med søndag i uke 21 til en hver tid være færre enn 0,2 voksen hunnlus
> av lakselus i gjennomsnitt per fisk i akvakulturanlegget. Fra og med
> mandag i uke 22 til og med søndag i uke 15 skal det til en hver tid
> være færre enn 0,5 voksen hunnlus av lakselus i gjennomsnitt per fisk
> i akvakulturanlegget.
>
> I Nordland, Troms og Finnmark skal det fra og med mandag i uke 21 til
> og med søndag i uke 26 til en hver tid være færre enn 0,2 voksen
> hunnlus […]. Fra og med mandag i uke 27 til og med søndag i uke 20 skal
> det til en hver tid være færre enn 0,5 voksen hunnlus […].

I uke 40–12, som nr. 2 gjelder, er grensa 0,5 i hele landet.

Kapasitetsjusteringsforskriften 2026 (FOR-2026-08-20-1764) kapittel 4,
`trafikklysvedtak/2026-12-31.bin.gz`,
sha256 `08b6090d993b96444ba54043079382de2a25750f571b7b98414158bc7abc4cd8`,
§ 15:

> Innehaver av tillatelse som har mottatt et positivt vedtak fra
> Mattilsynet om at en eller flere lokaliteter knyttet til tillatelsen
> har oppfylt kriteriene for unntak etter produksjonsområdeforskriften
> § 12, kan søke om […] b. økning i kapasitet på eksisterende tillatelser.

§ 16 setter fristen til 28. september 2026, § 20 regner tilbudet av
vekst «fra 1. oktober 2023–30. september 2025» og sier at tilbudet ikke
kan «overstige 6 prosent per tillatelse, inkludert eventuelle
kapasitetsøkninger tildelt etter kapittel 3».

**F1.2 — MÅLT. Ordlyden gjaldt hele kvalifikasjonsperioden.** § 12 i
SF-teksten er blokk for blokk lik § 12 i endringsforskriften
FOR-2023-09-28-1520 (LTI, ikrafttredelse 28.09.2023),
`lovdata-produksjonsomradeforskriften-endring-2023/2026-10-09.bin.gz`,
sha256 `7a8d1ec5162730087a21b9c3ab3eb69bc9a285b03b5a50be678a462ba3a70079`,
når endringsinstruksen «Ny § 12a skal lyde:» holdes utenfor. Fotnoten
under § 12 nevner ingen senere endring.
Feil hvis: § 12 er endret uten at Lovdata har ført det i fotnoten.

**F1.3 — LEST, ikke valgt. Kvalifikasjonsperioden er uke 40/2023–uke
39/2025.** § 12 b: «fra og med uke 40 i et oddetallsår til og med uke 39
i neste oddetallsår»; § 12a: søknad «innen 1. september i oddetallsår»;
lista heter «2025/2026». Kapasitetsjusteringsforskriften 2026 § 20
regner over «1. oktober 2023–30. september 2025» — samme to år, fra en
annen kropp.
Feil hvis: lista inneholder søknader fra en annen runde.

### Hva som kan måles

| vilkår | merke | hvordan |
|---|---|---|
| bokstav a | IKKE MÅLBAR | ingen kilde sier hvilke lokaliteter som ikke slipper ut larver |
| b nr. 1 | DELVIS | uker med ≥ 0,10 i uke 13–39; egg-alternativet kan ikke regnes |
| b nr. 2 | DELVIS | uker på/over BarentsWatchs tiltaksgrense i uke 40–12; «over» er ikke «brutt», og særskilte vilkår er ikke lest |
| b nr. 3 | DELVIS | oppføringer av medikamentell behandling per lokalitet; ikke per fisk, og en oppføring er ikke nødvendigvis én behandling |
| b nr. 4 | DELVIS | samme for ikke-medikamentell |
| b nr. 5 | DELVIS | produksjonsperioder som endte med en brakkuke hos BarentsWatch; ikke innrapportert slakting |
| b nr. 6 | IKKE MÅLBAR | vedtak om midlertidig biomassereduksjon står ikke i noen kilde vi henter |
| annet ledd a | MÅLBAR | uker med ≥ 0,17 i uke 13–39, per ISO-år |
| annet ledd b | DELVIS | lengste rekke ≥ 0,10, regnet både over hele perioden og innen uke 13–39 |

**Uklart i vilkårene, sagt rett ut:**
* Annet ledd b sier ikke om de fire tellingene på rad gjelder uke 13–39,
  slik bokstav a og nr. 1 sier uttrykkelig. Begge lesemåtene er regnet.
* «Én medikamentell behandling» er definert som «bruk av ett preparat
  forskrevet til lokaliteten». Mattilsynets rapport har én oppføring per
  behandling per ukesrapport, med antall merder. Én behandling over to
  uker kan stå to ganger.
* «Brutt» er en rettslig vurdering. Vi viser tellinger på eller over
  grensa.

---

## 2. Søknad → lokalitet → tillatelser → kapasitet

**F2.1 — MÅLT. Lista har 84 rader; 70 har en sikker kobling til 54
lokaliteter.** Arkivert av kilden `unntaksvekst` via
`arkiver_mattilsynet.py liste` 09.10.2026:
`unntaksvekst/2026-10-09.json.gz`,
sha256 `7e02f7b191ef69137166200f6fbe096f35931393be704bbd96fc71d173ced0fc`.
HTML-kroppen slik den kom: sha256
`1708491c9c17f9c5189220615e99dcf8fe2f8e45cd1fe47f5149713aa3a49428`,
138 165 byte, `x-cache-hit: hit`, `age: 456`.

| kobling | rader | lokaliteter | brukes |
|---|---:|---:|---|
| sikker (`entydig`) | 70 | 54 | i alt |
| usikker (skrivevariant) | 11 | 9 | vises for seg, telles aldri |
| uløst (`flertydig`) | 3 | 0 | vises for seg |

Godkjent 46 og avslått 8 av de 54. Ingen lokalitet har ulike resultater
for ulike søkere. Søkeren står med registerets navn og orgnr på 81 av
84 rader, alle AS; de 3 andre er én celle med to foretak, uten treff.
Tabellen er den samme som i målingen 08.10 (alle 84 (lokalitet, PO,
resultat, saksnumre) like), selv om HTML-kroppen har ny hash.
Feil hvis: en entydig navnekobling peker på feil lokalitet — likt navn i
samme PO er ikke en bekreftelse fra Mattilsynet.

**F2.2 — MÅLT. Kapasiteten.** Tillatelser med aktiv tilknytning til
lokaliteten i hver eierskapskropp, `capacity.current`:

| kropp | sha256 |
|---|---|
| `eierskap/2026-09-02.json.gz` | `6b22413510b5fbd59789e842f5f11dfc84df33fb0cdf4faf098e5ccf9bec39c9` |
| `eierskap/2026-09-14.json.gz` | `0c3525cac63342deaa8e0a8250de93af53eb3008a76fe8fe1a51c027de0c9454` |
| `eierskap/2026-09-21.json.gz` | `22142f87518388f0fb84fe2ef4eb191374221320795ef4ecb6fb28ba1885500c` |
| `eierskap/2026-09-28.json.gz` | `6e677a6024ee8665a366ed8f5efc356eb56c1ace2a857034a839162ac4c88b02` |
| `eierskap/2026-10-05.json.gz` | `581bca616e7d0b7706524cf6323e956a9dfbb4c99c9c77b1671f3aab2a171c11` |

| lokalitet | resultat | endring 28.09 → 05.10 | tillatelser endret av tilknyttet | alle round(x × 1,01) |
|---|---|---:|---:|---|
| 13691 | Avslag | +80 t | 7 av 7 | ja |
| 15957 | Godkjent | +55 t | 5 av 7 | ja |
| 29416 ÅPENVIK | Godkjent | +58 t | 5 av 5 | ja |
| 33777 | Godkjent | +58 t | 5 av 7 | ja |

Det er åtte ulike tillatelser — F-N-0006 og F-SV-0004, -0005, -0006,
-0008, -0009, -0010, -0011 — med 91 t til sammen, og flere av dem er
knyttet til to eller tre av de fire lokalitetene samtidig. Ingen andre av
de 60 lokalitetsnumrene (54 sikre og 9 usikre, der 13057, 18217 og
27856 står som begge) har en kapasitetsendring i noen av kroppene. 34117 fikk tillatelsen H-K-0032
tilknyttet mellom 21.09 og 28.09, uten kapasitetsendring.
Feil hvis: tillatelser eid av personer også fikk økningen. De er fjernet
før arkivering (93 i kroppen 05.10) og kan verken telles eller utelukkes.

**F2.3 — MÅLT. Lokalitetskapasiteten (`/sites` `capacity`) er uendret**
for alle 60 lokalitetsnumre i alle 15 akvakulturkropper 17.08–05.10.2026
(`akvakultur/2026-08-17.2.json.gz` … `2026-10-05.json.gz`,
`b415394a…`).

---

## 3. Drift: Mattilsynets rapporter, BarentsWatchs perioder

**Grunnlaget — MÅLT.** `arkiver_mattilsynet.py lakselus` 09.10.2026 på
kode 531249bc6406: 60 lokaliteter (sikre og usikre), 7 187 rapporter,
`mattilsynet-lakselus/<nr>/2026-10-09.json.gz`, sha256 per kropp i
`mattilsynet/2026-10-09.2.logg.json`. Spesifikasjonen
`mattilsynet-openapi/2026-10-09.json.gz`, versjon `ed7f9fe`, sha256
`779bf51d44146e01335d60e70e2b5e20e79110ca6b5d3a53d5daa74ae5e68303`
(lik målingen 09.10, docs/MALING-MATTILSYNET-API.md). Rapportøren er
blanket før arkivering i 305 rapporter på 6 lokaliteter, der nummeret
ikke står i eierskapskroppens `enheter`.

**Periodegrensen er BarentsWatchs vurdering.** En produksjonsperiode er
sammenhengende uker der `lusetall.brakklagt` er `False` — BarentsWatchs
«Trolig uten fisk», en slutning og ikke en innrapportering
(docs/MALING-FUNN-OKTOBER.md F4.2). Delingen er `nettsted.del_i_perioder()`,
den samme som lokalitetssiden bruker. Tiltaksgrensa er BarentsWatchs
«Lusegrense uke» (`sjotemperatur.lusegrense`), til og med uke 37/2026.

**Reglene vi har valgt** (står i `unntaksanalyse`):
* Én verdi per uke: høyeste rapporterte lusetall; en behandling som står
  likt i to rapporter samme uke, telles én gang.
* En rapport for en uke som ligger etter uka den ble levert i, holdes
  utenfor: 11272 har «2025 uke 52» levert 03.01.2025.
* 0,10 og 0,17 sammenlignes uten avrunding; tiltaksgrensa med halv-opp
  til to desimaler, som BarentsWatch.

**F3.1 — MÅLT. Samdrift gir flere rapporter per uke.** 1 135
lokalitetsuker har mer enn én rapport; 99 av dem er ulike.

**F3.2 — MÅLT. Dekningen mot BarentsWatch**, de 60 lokalitetene, uke
40/2023 til 2026-09-07: 5 625 uker har telling i begge, 57 bare hos
BarentsWatch (53 av dem i oktober–november 2023), 16 bare hos
Mattilsynet. For de sikre: i 13 av 5 135 felles uker skiller verdiene
mer enn 0,005. Alle 13 er uker med to eller tre ulike rapporter, og i
alle 13 er BarentsWatchs verdi lik en av de lavere rapportene; 9 av dem
er 39477, der høyeste og laveste rapport samme uke kan skille 0,29.
Regelen om høyeste verdi gir der et høyere tall enn BarentsWatch viser.
Feil hvis: API-ets hull i høsten 2023 også gjelder behandlinger. Det
berører nr. 2 (uke 40–12) mer enn nr. 1 (uke 13–39).

**F3.3 — MÅLBAR. Per lokalitet** (sikre koblinger; «KV» =
kvalifikasjonsperioden, «E» = fra uke 40/2025; x/y = uker med ≥ 0,10 av
uker med telling i uke 13–39; rekke = lengste rekke ≥ 0,10, hele
perioden/innen uke 13–39). Hele tabellen, også per produksjonsperiode,
står på siden og i nedlastingen.

| lok | navn | PO | resultat | kapasitet | KV ≥0,10 u13–39 | KV 0,17 maks/år | KV rekke alle/13–39 | KV over 40–12 | KV med | KV ikke-med | KV slutt | E ≥0,10 u13–39 | E over grensa | E med | E ikke-med |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 11513 | ANDAL | 3 | Avslag | uendret | 9/40 | 1 | 3/3 | 0 | 0 | 26 | 1 | – | 0/23 | 1 | 7 |
| 32457 | DALSVÅG NV | 3 | Godkjent | uendret | 6/27 | 0 | 15/2 | 0 | 1 | 4 | 1 | 6/27 | 0/49 | 12 | 16 |
| 12033 | DYSVIK | 3 | Godkjent | uendret | 2/28 | 1 | 5/1 | 0 | 0 | 9 | 1 | 4/27 | 0/50 | 2 | 8 |
| 12036 | HISDALEN | 3 | Godkjent | uendret | 0/47 | 0 | 14/0 | 0 | 0 | 9 | 2 | 3/21 | 0/44 | 0 | 7 |
| 12035 | HONDSKÅR | 3 | Godkjent | uendret | 0/51 | 0 | 6/0 | 0 | 0 | 5 | 1 | 4/27 | 0/50 | 0 | 6 |
| 22095 | HÅGARDSNESET | 3 | Godkjent | uendret | 0/52 | 0 | 6/0 | 0 | 0 | 8 | 1 | 2/25 | 0/42 | 0 | 5 |
| 11575 | KOLØY N | 3 | Godkjent | uendret | 0/39 | 0 | 0/0 | 0 | 0 | 0 | 1 | 0/20 | 0/36 | 0 | 0 |
| 18217 | KVALØY Ø | 3 | Godkjent | uendret | 2/39 | 1 | 5/1 | 0 | 0 | 7 | 1 | 5/24 | 0/22 | 5 | 4 |
| 45066 | LINGAHOLMANE | 3 | Godkjent | uendret | 3/43 | 0 | 5/2 | 0 | 0 | 10 | 1 | 2/7 | 0/32 | 1 | 6 |
| 12022 | LJONESBJØRGENE | 3 | Godkjent | uendret | 4/31 | 1 | 12/3 | 0 | 0 | 13 | 1 | 5/27 | 0/50 | 0 | 13 |
| 33337 | LYNGNES | 3 | Godkjent | uendret | 3/31 | 0 | 8/2 | 0 | 3 | 13 | 1 | 5/27 | 0/26 | 0 | 2 |
| 13020 | NYGÅRD | 3 | Godkjent | uendret | 10/31 | 1 | 14/4 | 0 | 0 | 12 | 1 | – | 0/18 | 1 | 2 |
| 13345 | OTERSTEGDALEN | 3 | Godkjent | uendret | 6/28 | 1 | 4/3 | 0 | 0 | 12 | 2 | 20/27 | 1/48 | 2 | 13 |
| 32137 | SAGEN 2 | 3 | Avslag | uendret | 0/31 | 0 | 0/0 | 0 | 0 | 0 | 4 | 0/13 | 0/26 | 0 | 0 |
| 10328 | SAGVIK | 3 | Godkjent | uendret | 13/47 | 1 | 10/3 | 0 | 0 | 7 | 1 | 8/15 | 1/40 | 2 | 10 |
| 22315 | SKAVHELLA | 3 | Godkjent | uendret | 10/36 | 1 | 5/3 | 0 | 0 | 12 | 1 | 9/16 | 3/41 | 1 | 13 |
| 31117 | SKRUBBO | 3 | Godkjent | uendret | 6/35 | 0 | 4/3 | 0 | 4 | 17 | 1 | 12/27 | 1/26 | 0 | 3 |
| 34117 | SKÅTHOLMEN | 3 | Godkjent | 1 tillatelse inn | 12/44 | 1 | 7/3 | 0 | 0 | 16 | 1 | 6/27 | 0/26 | 0 | 4 |
| 13057 | TEIGLAND I | 3 | Godkjent | uendret | 10/39 | 0 | 6/6 | 0 | 0 | 4 | 1 | 7/27 | 0/50 | 2 | 10 |
| 10029 | TUHOLMANE Ø | 3 | Godkjent | uendret | 5/37 | 0 | 4/1 | 0 | 0 | 7 | 1 | 4/26 | 0/24 | 5 | 2 |
| 30717 | TVEITNES | 3 | Godkjent | uendret | 5/32 | 1 | 5/2 | 0 | 1 | 5 | 1 | 1/27 | 0/28 | 0 | 0 |
| 45072 | BLEKET | 4 | Godkjent | uendret | 21/52 | 0 | 10/3 | 0 | 2 | 17 | 1 | 10/18 | 0/43 | 0 | 15 |
| 12156 | BLOM | 4 | Godkjent | uendret | 1/31 | 1 | 16/1 | 0 | 2 | 36 | 1 | 0/8 | 0/16 | 0 | 1 |
| 21336 | DJUPELEGET | 4 | Godkjent | uendret | 5/27 | 1 | 12/2 | 0 | 0 | 7 | 1 | 7/27 | 0/50 | 0 | 8 |
| 13870 | EIKEBÆRÅNÆ | 4 | Godkjent | uendret | 0/54 | 0 | 7/0 | 0 | 0 | 2 | 1 | 0/27 | 0/38 | 0 | 0 |
| 13874 | FYLLINGSNES S | 4 | Godkjent | uendret | 0/38 | 0 | 5/0 | 0 | 0 | 5 | 2 | – | – | – | – |
| 40297 | GNARNESVIKA | 4 | Godkjent | uendret | 4/34 | 1 | 6/3 | 0 | 0 | 8 | 1 | 2/23 | 0/21 | 3 | 4 |
| 11771 | GRISHOLMSUNDET | 4 | Godkjent | uendret | 9/41 | 1 | 11/2 | 0 | 0 | 0 | 1 | 0/1 | 0/1 | 0 | 0 |
| 24615 | GRUNNSØYA | 4 | Godkjent | uendret | 0/36 | 0 | 2/0 | 0 | 1 | 0 | 1 | 0/11 | 0/36 | 0 | 2 |
| 31577 | HANEHOLMEN | 4 | Godkjent | uendret | 1/45 | 0 | 7/1 | 0 | 0 | 10 | 1 | 0/25 | 0/23 | 2 | 0 |
| 39477 | HUNDVIKA AUST | 4 | Godkjent | uendret | 0/31 | 0 | 11/0 | 0 | 4 | 15 | 1 | 1/27 | 1/50 | 6 | 14 |
| 11665 | JIBBERSHOLMANE | 4 | Godkjent | uendret | 11/37 | 1 | 9/3 | 0 | 0 | 16 | 1 | 0/10 | 1/15 | 0 | 3 |
| 12215 | KLEPPENESET | 4 | Godkjent | uendret | 2/25 | 1 | 5/1 | 0 | 3 | 2 | 1 | – | 0/9 | 0 | 1 |
| 11791 | LANGERÅA | 4 | Godkjent | uendret | 9/29 | 0 | 6/3 | 0 | 2 | 6 | 1 | 0/2 | 0/23 | 0 | 0 |
| 12212 | LINDENESET | 4 | Godkjent | uendret | 1/33 | 0 | 5/1 | 0 | 3 | 10 | 1 | 0/9 | 0/34 | 0 | 6 |
| 13876 | LITLETVEITHOLANE | 4 | Godkjent | uendret | 10/45 | 1 | 21/3 | 0 | 0 | 9 | 1 | 1/12 | 0/37 | 0 | 5 |
| 45206 | LYNGHOLMANE | 4 | Avslag | uendret | 0/27 | 0 | 4/0 | 0 | 3 | 4 | 0 | 0/9 | 0/22 | 0 | 2 |
| 11772 | MOLDØYOSEN | 4 | Godkjent | uendret | 10/40 | 0 | 12/5 | 0 | 0 | 3 | 1 | 0/1 | 0/10 | 0 | 0 |
| 19655 | OSPENESET | 4 | Godkjent | uendret | 0/35 | 0 | 3/0 | 0 | 3 | 8 | 1 | 0/12 | 0/25 | 0 | 2 |
| 13706 | SELJESET | 4 | Godkjent | uendret | 2/27 | 0 | 4/2 | 0 | 1 | 4 | 1 | 9/27 | 0/40 | 1 | 5 |
| 13644 | TEPSTAD | 4 | Avslag | uendret | 8/48 | 1 | 29/3 | 0 | 0 | 30 | 1 | 0/17 | 0/15 | 0 | 0 |
| 14018 | TOSKA S | 4 | Godkjent | uendret | 10/34 | 1 | 10/3 | 0 | 1 | 18 | 1 | 0/7 | 0/15 | 0 | 3 |
| 15455 | DAUMANNSVIKA | 8 | Avslag | uendret | 4/34 | 0 | 8/4 | 0 | 0 | 4 | 1 | 0/27 | 0/50 | 0 | 0 |
| 27856 | HUNDHOLMEN | 8 | Avslag | uendret | 0/12 | 0 | 1/0 | 0 | 1 | 0 | 1 | – | – | – | – |
| 19098 | LEIVSETHAMRAN | 8 | Godkjent | uendret | 1/44 | 0 | 1/1 | 0 | 0 | 0 | 1 | – | 0/9 | 0 | 0 |
| 13125 | STORVIKA | 8 | Avslag | uendret | 9/28 | 7 | 12/4 | 1 | 0 | 9 | 1 | 19/27 | 0/50 | 0 | 13 |
| 35737 | SÆTEROSEN | 8 | Godkjent | uendret | 0/9 | 0 | 0/0 | 0 | 0 | 0 | 2 | 0/3 | 0/1 | 0 | 0 |
| 31077 | TJUKKENESET | 9 | Godkjent | uendret | 1/19 | 0 | 1/1 | 0 | 0 | 0 | 1 | 8/27 | 0/45 | 0 | 3 |
| 10735 | ÅRØYA | 11 | Godkjent | uendret | 3/44 | 0 | 2/2 | 0 | 1 | 7 | 1 | 7/7 | 0/32 | 1 | 3 |
| 15957 | LATVIKA | 13 | Godkjent | +55 t (1 %) | 1/38 | 0 | 1/1 | 0 | 0 | 0 | 1 | – | – | – | – |
| 33777 | LAUSKLUBBEN | 13 | Godkjent | +58 t (1 %) | 0/38 | 0 | 0/0 | 0 | 0 | 0 | 2 | 0/21 | 0/19 | 1 | 0 |
| 13691 | OTERFJORDEN | 13 | Avslag | +80 t (1 %) | 2/43 | 1 | 2/2 | 0 | 0 | 0 | 1 | – | – | – | – |
| 32637 | VEIDNES | 13 | Godkjent | uendret | 1/36 | 0 | 1/1 | 0 | 0 | 0 | 1 | 0/26 | 0/46 | 1 | 0 |
| 29416 | ÅPENVIK | 13 | Godkjent | +58 t (1 %) | – | – | 0/0 | 0 | 0 | 0 | 0 | 0/9 | 0/7 | 1 | 0 |

**F3.4 er flyttet** til «Ikke publisert» nederst.

**F3.5 — MÅLT. ÅPENVIK (29416, Godkjent) har ingen rapport i API-et i
kvalifikasjonsperioden.** BarentsWatch har fem tellinger i uke 40–44/2023
og regner lokaliteten som brakklagt i 99 av de 104 ukene. API-ets ti
rapporter er alle etter uke 40/2025. Lokaliteten er holdt utenfor
kontrollen (uten tall er det ingenting å ligge innenfor).

---

## 4. Kontrollen: godkjent mot avslått før søknaden

**F4.1 — MÅLBAR. Ingen forskjell.** 45 godkjente og 8 avslåtte
lokaliteter med tellinger i kvalifikasjonsperioden. Tabellen har 46
godkjente lokaliteter og kontrollen 45, fordi ÅPENVIK (29416) ikke har én
telling hos Mattilsynet i kvalifikasjonsperioden og derfor er holdt
utenfor kontrollen. Andel innenfor vilkårets tall, Fishers eksakte test (tosidig,
`math.comb`, ingen tilfeldighet):

| vilkår | innenfor betyr | godkjent | avslått | p |
|---|---|---:|---:|---:|
| b nr. 1 | ingen telling ≥ 0,10 i uke 13–39 | 11/45 | 3/8 | 0,42 |
| annet ledd a | høyst én ≥ 0,17 i uke 13–39 hvert år | 45/45 | 7/8 | 0,15 |
| annet ledd b | < 4 på rad ≥ 0,10, hele perioden | 10/45 | 4/8 | 0,19 |
| annet ledd b | < 4 på rad ≥ 0,10, innen uke 13–39 | 42/45 | 6/8 | 0,16 |
| b nr. 2 | ingen over tiltaksgrensa i uke 40–12 | 45/45 | 7/8 | 0,15 |
| b nr. 3 | høyst én medikamentell oppføring | 36/45 | 7/8 | 1,00 |
| b nr. 4 | høyst seks ikke-medikamentelle oppføringer | 19/45 | 5/8 | 0,44 |
| b nr. 5 | minst én periode endte med brakk | 45/45 | 7/8 | 0,15 |

Medianer, godkjent mot avslått: tellinger 68 / 66, uker ≥ 0,10 i uke
13–39 3 / 3, høyeste i uke 13–39 0,16 / 0,1675, rekke hele perioden
6 / 3,5, rekke innen uke 13–39 2 / 2,5, medikamentelle 0 / 0,
ikke-medikamentelle 7 / 4.

På tre tall (annet ledd a, nr. 2, nr. 5) er alle godkjente innenfor og
én avslått utenfor — to ulike avslåtte lokaliteter. Det er retningen en
forskjell ville hatt, og den er ikke stor nok til å skilles fra
tilfeldighet med 8 avslag.

*Feil hvis:* se funn 2 øverst.

**F4.2 — MÅLBAR. Lesemåten av annet ledd b.** Lest over hele perioden er
10 av 45 godkjente innenfor; lest innen uke 13–39 er 42 av 45 det. Det
sier at lesemåten betyr mye, ikke hvilken Mattilsynet brukte.

---

## 5. Siden /analyse/unntaksvekst/

Øverst funn 1 og 2 (kapasiteten og kontrollen), så én setning om hva som
er målt og én om hvorfor tabellen teller 46 godkjente og kontrollen 45.
Deretter tabellen per søker og lokalitet (sikre koblinger), så
kapasiteten, perioden per produksjonsperiode (lukket), radene uten sikker
kobling, kontrollen, vilkårene ordrett med det som er målt under hvert,
metode med sti og sha256 for hvert grunnlag, og forbehold. Nedlasting som
Excel og datapakke med alle tallene i F3.3 og mer. Lenke fra forsiden og
fra hver lokalitet med sikker kobling; i sitemap og i søket som sidetype
«Analyse».

Tabellen viser driftstall og vilkårets tall i kolonneoverskriften, men
ingen kolonne, klasse eller farge som kan leses som innenfor eller
utenfor, og den er sortert etter produksjonsområde og navn — ikke etter
avvik. Drift før mot etter (F3.4) står ikke på siden.

Søkernavnet er registerets, bare der kilden har koblet det entydig til et
orgnr med selskapsform, og merket slik at publiseringsvakten prøver det
mot snapshotene. Hasher står i grupper på åtte (en hel sha256 har ni
siffer på rad i 11,7 % av tilfellene, og porten leser dem som orgnr).

**Lisensen.** Siden kunne ikke bygges med `unntaksvekst` UBELAGT. Belagt
i lov 09.10.2026: lista er uten vern etter åndsverkloven § 14, sitert
ordrett med hash i docs/LISENSKJEDE.md merknad K, der følgene for
ukesendringene står. Mattilsynets gjenbruksside (arkivert i
`vilkar-mattilsynet/`) beholdes som praksis: kilden har
`attribusjon = ("Kilde: Mattilsynet",)`, og adressen og datoen står ved
tabellen.
API-dataene står under NLOD 2.0 etter spesifikasjonen selv.

## 6. Lusegrafen

Søylene over tiltaksgrensa er rust (`--rust`), som i overleveringen; de
andre står i `--hav5`. «Over» er samme regel som overalt
(`nettsted._over_grensen`, BarentsWatchs halv-opp).

---

## Hva analysen ikke sier

* Om en lokalitet har oppfylt eller brutt et vilkår.
* Når Mattilsynet fattet vedtakene — lista har ingen dato.
* Om økningen etter kapittel 4 kommer, og hvor stor den blir. Den neste
  eierskapskroppen er 12.10.2026.
* Noe om de 11 usikre og 3 uløste radene. Tallene for de usikre
  kandidatene skrives ut av `unntaksanalyse.py` (linjene merket
  `[usikre]`), men koblingen er ikke bekreftet, og de står verken i
  tabellen, kontrollen eller nedlastingen.

---

## Ikke publisert

Funnet under sto som nummer 3 blant de sterkeste til 09.10.2026. Det er
tatt ut av den listen og av analysesiden, og står her slik det ble målt.
Tallene er riktig talt; det er SAMMENLIGNINGEN som ikke holder.

**F3.4 — MÅLBAR som telling, ikke som sammenligning. Etter, samlet.**

| | godkjente | avslåtte |
|---|---:|---:|
| lokaliteter med tellinger etter uke 40/2025 | 44 av 46 | 6 av 8 |
| minst én telling ≥ 0,10 i uke 13–39 (2026) | 25 | 1 |
| flere enn én ≥ 0,17 i uke 13–39 i 2026 | 10 | 1 |
| minst én telling over tiltaksgrensa | 6 | 0 |
| mer enn én medikamentell oppføring | 10 | 0 |
| mer enn seks ikke-medikamentelle oppføringer | 11 | 2 |
| medikamentelle oppføringer, sum etter (53 uker) | 49 | 1 |
| medikamentelle oppføringer, sum før (104 uker) | 32 | 4 |

Feil hvis: en lokalitet som er godkjent, har byttet drift eller eier;
tallene følger lokalitetsnummeret, ikke søkeren.

Tre grunner til at før og etter ikke kan settes mot hverandre:

* **Periodene er ikke sammenlignbare.** «Etter» er 53 uker (uke 40/2025
  til uke 41/2026), «før» er 104. Ingen av dem er justert for hvor fisken
  er i produksjonssyklusen: lus og behandlinger følger syklusen og
  årstiden, og en lokalitet som hadde utsett i den ene perioden og brakk
  i den andre, gir ulike tall uten at driften er endret.
* **En oppføring er ikke en behandling.** Mattilsynets ukesrapport har én
  oppføring per behandling per rapport. En behandling over to uker kan
  stå to ganger, og forskriften teller behandlinger.
* **Det finnes ingen vedtaksdato.** «Etter» er etter kvalifikasjons-
  perioden, ikke etter Mattilsynets vedtak, så tallet kan ikke leses som
  drift etter en godkjenning.

**Hva som måtte til for å gjøre det sammenlignbart:**

* Samme kalenderuker år mot år — for eksempel uke 13–39 i 2024, 2025 og
  2026 — så sesongen er den samme på begge sider.
* Bare uker med fisk til stede: uker der lokaliteten ikke er brakklagt
  (BarentsWatchs vurdering, se F3), og med en telling, slik at brakk ikke
  trekker tallet ned.
* Behandlinger talt som behandlinger og ikke som oppføringer — det krever
  en regel for når to oppføringer i påfølgende uker er samme behandling,
  og den regelen er ikke skrevet.
* Vedtaksdatoen, om det skal hete «etter godkjenningen». Den står ikke i
  Mattilsynets liste.
