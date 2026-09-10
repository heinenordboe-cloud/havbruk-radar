# Styringsgruppen — formatkartlegging

Kartlegging, ikke kilde. Ingenting er skrevet til `data/`, ingen kilde er
lagt i `sources/`, og `analyse/fasit/ekspertgruppen-po-kategori.csv` er
ikke rørt.

Alt her er MÅLT på kropper hentet 08.09.2026. Kroppene er lagret rått og
uendret FØR noe ble parset, og sha256 under er regnet på de lagrede
bytene. De ligger i sesjonens arbeidsmappe og IKKE i `data/arkiv/` —
oppgaven forbød det, så en framtidig kilde må hente dem på nytt og
arkivere selv. Hashene under er det som gjør den hentingen etterprøvbar.

Styringsgruppen for vurdering av lakseluspåvirkning er leddet mellom
ekspertgruppens kategori (`sources/ekspertgruppen.py`) og departementets
farge (`sources/trafikklysvedtak.py`). Repoet har i dag bare de to
ytterste leddene.

---

## Oversikt

| kropp | år omtalt | PO-tabell | sammenslått råd | prosagjentakelse | verdiformat | vert | `published_at` |
|---|---|---|---|---|---|---|---|
| 2017 mai | — (skann) | — | — | — | — | trafikklyssystemet.no | 2017-05-16T16:57:11+01:00 |
| 2017 sept | — (skann) | — | — | — | — | hi.no | 2017-10-30T13:34:16+01:00 |
| 2018 | 2016, 2017, 2018 | ja (tekst) | **ja** — for 2016–2017 | ja, to former | terskler i tabell, kategorinavn i per-PO-avsnitt | hi.no | 2018-11-27T14:04:21+01:00 |
| 2018-2019 | 2018, 2019 | ja (tekst) | **ja** — for 2018-2019 | ja, punktliste per PO | terskler begge steder | hi.no | 2019-11-17T14:29:53+01:00 |
| 2020 | 2020 | ja (tekst) | nei | ja, punktliste per PO | kategorinavn i tabell, terskler i prosa | regjeringen.no (403 → Wayback) | 2020-11-27T13:32:29+01:00 |
| 2021 | 2021 + oppdatert 2020 | ja (tekst) ×3 | nei | ja, punktliste per PO | kategorinavn i tabell, terskler i prosa | regjeringen.no (403 → Wayback) | 2021-11-11T12:05:19+01:00 |
| 2022 | 2022 | ja (tekst) | nei | ja, punktliste per PO | IPCC-ord + kategorinavn i tabell, terskler i prosa | regjeringen.no (403 → Wayback), også NVA | 2022-12-01T10:36:21+01:00 |
| 2023 | 2023 | ja (tekst) | nei | ja, punktliste per PO | IPCC-ord + kategorinavn i tabell, terskler i prosa | NVA | 2023-11-22T10:39:50+01:00 |
| 2024 | 2024 | ja (tekst) | nei | ja, punktliste per PO | kategorinavn i tabell, terskler i prosa | NVA | 2024-11-29T13:48:06+01:00 |
| 2025 | **2024 og 2025** | ja (tekst) | **nei** — to årskolonner, ingen sammenslåing | **nei** | kategorinavn + midtpunktstall i parentes | NVA | 2025-11-21T10:58:11+01:00 |

---

## Steg 1 — henting og arkivering

### Brage kan IKKE erstatte de tre vertene

Spørsmålet var om NINA Brage har alle årgangene og dermed kan erstatte
trafikklyssystemet.no, hi.no og regjeringen.no. Svaret er nei, av to
grunner, og begge er målt.

**`brage.nina.no` finnes ikke lenger.** Navnet er en CNAME til
`brage.unit.no`, som ikke har noen adresse — `curl` feiler med kode 6,
«could not resolve host». Installasjonen er avviklet, og handlene
videresendes: `hdl.handle.net/11250/3104585` svarer 302 til
`nva.sikt.no/registration/…`. Etterfølgeren er **Nasjonalt vitenarkiv
(NVA)**, som er den samme veien `docs/KILDE-EKSPERTGRUPPEN.md` allerede
går for ekspertgrupperapportene 2023–2025.

**NVA har fire av ti årganger.** Søke-API-et
(`api.nva.unit.no/search/resources`) gir treff på «Styringsgruppens
oppsummering og vurdering av lakseluspåvirkning …» for **2022, 2023,
2024 og 2025** — og bare de. Tre ulike søk («styringsgruppen lakselus»,
«styringsgruppen produksjonsområder», «styringsgruppens evaluering»)
gir samme fire. Årgangene 2017–2021 ligger ikke der.

Følgen for en framtidig kilde: **fire verter, ikke én.**
trafikklyssystemet.no (2017 mai), hi.no (2017 sept, 2018, 2018-2019),
regjeringen.no via Wayback (2020, 2021, 2022) og NVA (2022–2025). NVA er
det eneste stabile leddet for de nyeste, og det er der nye årganger vil
komme.

De tre manglende årgangene som oppgaven ba om å lete opp — 2023, 2024 og
2025 — er altså funnet, i NVA.

### Hva hver henting ga

| kropp | vert / vei | HTTP | byte | sha256 | `Last-Modified` |
|---|---|---|---|---|---|
| 2017 mai | trafikklyssystemet.no | 200 | 99 187 | `f8dcce580ffc9561802c13919f41a3a90f9bf33b6b66a80d53f91435e8114979` | Mon, 23 May 2022 11:14:38 GMT |
| 2017 sept | hi.no | 200 | 5 173 096 | `048d769d93b9ec412f15a3bc77ce642269b24a12e987d39c4c5f22adde8d59d5` | Wed, 30 Oct 2019 14:53:29 GMT |
| 2018 | hi.no | 200 | 493 443 | `8d1cab45deb3cd450368a1da2348fb442b33b3ae79c2673a3b34c68f50da5143` | Thu, 29 Nov 2018 06:28:41 GMT |
| 2018-2019 | hi.no | 200 | 730 607 | `b849614f9cf1c2ce2e9169e7f4afdb4d9a19421a0f567f666ca64542e9e5cd34` | Tue, 04 Feb 2020 07:37:21 GMT |
| 2020 | regjeringen.no | **403** | 5 925 | — (feilside, ikke PDF) | ingen |
| 2020 | Wayback `20210121010628` | 200 | 776 717 | `51ad591fe3c82902b4f0c613ad14673243e49aa0089292a3ea1a85a26376ed9a` | `X-Archive-Orig`: Fri, 18 Dec 2020 15:13:41 GMT |
| 2021 | regjeringen.no | **403** | 5 979 | — | ingen |
| 2021 | Wayback `20230101212343` | 200 | 1 544 699 | `79b21f55240226dac2a1d8ca9b501cfe197284b9611d148ce385586b49a03d96` | `X-Archive-Orig`: Tue, 16 Nov 2021 19:28:26 GMT |
| 2022 | regjeringen.no | **403** | 5 874 | — | ingen |
| 2022 | Wayback `20230608073728` | 200 | 898 889 | `4200e7e934a712efd70f05c1df9a49a542e1b6c0a3cd665911427ea1b5fb4dee` | `X-Archive-Orig`: Mon, 05 Dec 2022 16:16:04 GMT |
| 2022 | NVA | 200 | 841 071 | `906fea0154aea86cd698f9e5bdacc6fdd7644724424afab177361dd0ea1d5352` | Mon, 15 Sep 2025 09:32:40 GMT |
| 2023 | NVA | 200 | 941 861 | `aed5a118fc81c8ba7f14179aa66fb4286c29c295bc68933467f4ac9dbace3803` | Mon, 15 Sep 2025 09:32:35 GMT |
| 2024 | NVA | 200 | 912 109 | `23ab0291fd1b90350ef0bd50ed3235af0cb24810081066cc65397ddf6657f8ad` | Mon, 15 Sep 2025 09:32:37 GMT |
| 2025 | NVA | 200 | 924 172 | `82a6c4967fadc7d0da289b4c1e9a7fda9dd60b0d78b056696e3ca013e8f8d363` | Mon, 01 Dec 2025 14:52:27 GMT |

**Alle verter sender `Last-Modified`.** Det er ikke som lovdata.no, som
ikke sender den i det hele tatt (se
`docs/beslutninger/2026-09-05-vedtakskilden.md`). Men headeren betyr tre
forskjellige ting her, og bare den ene av dem ligner en utgivelsesdato:

* **NVA-kroppene bærer en migreringsdato.** 2022, 2023 og 2024 har
  `Last-Modified` innenfor **fem sekunder av hverandre** — 15.09.2025
  kl. 09:32:35, :37 og :40. Det er en batch-innlesting, ikke tre
  utgivelser. Samme signatur som hi.no-migreringen i
  `docs/KILDE-EKSPERTGRUPPEN.md` punkt 3.
* **hi.no og trafikklyssystemet.no spriker.** 2017 mai-kroppen er utgitt
  16.05.2017 og har `Last-Modified` 23.05.2022 — fem år etter.
  2018-kroppen har 29.11.2018, to dager etter `/CreationDate`, og er den
  eneste som er nær.
* **regjeringen.no-kroppene ser derimot riktige ut.** 18.12.2020,
  16.11.2021 og 05.12.2022 ligger alle 3–21 dager etter
  `/CreationDate`. Det er *forenlig* med utgivelse, men beviser den
  ikke: verdien er bevart av Wayback fra opphavets svar, og opphavet
  svarer i dag 403, så den kan ikke etterprøves mot en fersk henting.

`published_at` er derfor tatt fra PDF-ens `/CreationDate`, som i
ekspertgruppen. Avviket mellom de to står i tabellene over — begge er
oppgitt, ingen av dem er slått sammen.

### Produsenter, og to av dem er skannere

    2017 mai    Xerox WorkCentre 7530                  D:20170516165711+01'00'
    2017 sept   KONICA MINOLTA bizhub C654             D:20171030133416+01'00'
    2018        Microsoft® Word for Office 365         D:20181127140421+01'00'
    2018-2019   Microsoft® Word for Office 365         D:20191117142953+01'00'
    2020        Microsoft® Word for Office 365         D:20201127133229+01'00'
    2021        Microsoft® Word 2016                   D:20211111120519+01'00'
    2022        Microsoft® Word for Microsoft 365      D:20221201103621+01'00'
    2023        Microsoft® Word for Microsoft 365      D:20231122103950+01'00'
    2024        Adobe PDF Library 24.3.144             D:20241129134806+01'00'
    2025        Microsoft® Word for Microsoft 365      D:20251121105811+01'00'

Alle ti faller i vurderingsårets mai–desember. Vakten i
`ekspertgruppen._utgitt()` — datoen må ligge i `[nyeste vurderingsår, +1]`
— ville passert for alle.

To merknader som ikke skal gjettes bort: 2017 sept-kroppen har
`/CreationDate` i **oktober**, ikke september, selv om URL-en sier
«september-2017». Og 2018-kroppens førsteside er datert «11. november
2018» mens `/CreationDate` er 27. november. Dokumentets egen dato og
eksportdatoen er ikke samme ting.

### Samme rapport, to hasher

2022-kroppen finnes på begge verter. **Teksten er identisk** (30 046 tegn,
tegn for tegn) og `/CreationDate` er den samme, men `/ModDate` skiller
(01.12.2022 mot 06.12.2022) og filene er ulike: 898 889 mot 841 071 byte,
og to forskjellige sha256.

Følgen for en framtidig kilde er konkret: **`raw_hash` kan ikke brukes
til å avgjøre om to verter har samme rapport.** To eksporter av samme
dokument er to kropper. Identiteten må leses av dokumentet — tittel,
`/CreationDate`, årstall — slik `trafikklysvedtak.gjenkjenn()` gjør det
med FOR-nummeret.

### UO-stempelet, målt på alle ti

Oppgaven visste om 2018-2019. Søk etter «UO», «utsatt offentlighet»,
«offl» og «offentleglova» i hele teksten i alle ti kroppene gir:

| kropp | stempel |
|---|---|
| 2018-2019 | **`UO § 15.3 (UTSATT OFFENTLIGHET )`** |
| **2020** | **`UO § 15.3 (UTSATT OFFENTLIGHET )`** |
| alle øvrige | ingen treff |

**2020-kroppen bærer det samme stempelet**, og det var ikke kjent på
forhånd. De to 2017-kroppene kan ikke svare på spørsmålet — de har ingen
tekst å søke i (se under).

---

## Steg 2 — formatet, én kropp om gangen

### 2017 mai — `Råd fra styringsgruppe til NFD 16mai17.pdf`

**Kroppen har ingen tekst.** Fire sider, 99 187 byte, og pypdf trekker ut
**3 tegn totalt**. Produsenten er `Xerox WorkCentre 7530` — en
kopimaskin. Dokumentet er et skannet papirark uten OCR-lag.

1. **Vurderingsår:** kan ikke besvares fra kroppen. Ingen setning å sitere.
2. **PO-tabell:** kan ikke besvares.
3. **Verdiformat:** kan ikke besvares.
4. **Sammenslått råd:** kan ikke besvares.
5. **Prosagjentakelse:** kan ikke besvares.
6. **Usikkerhet:** kan ikke besvares.
7. **Bare figur/kart?** Kroppen er i sin helhet bilde. Det er ikke det
   samme som «rådet finnes bare som farge i en figur» — det er at hele
   dokumentet, tekst inkludert, ligger som piksler.

Stoppregelen er lest og ikke utløst: den gjelder en kropp der rådet per
PO finnes utelukkende som FARGE i en FIGUR. Her er problemet et annet, og
kartet er ikke forsøkt lest. Årgangen er ikke maskinlesbar uten OCR, og
OCR er ikke gjort.

### 2017 sept — `Raad-fra-styringsgruppa-til-NFD-september-2017-.pdf`

Samme sak. Elleve sider, 5,2 MB, **10 tegn** uttrukket. Produsent
`KONICA MINOLTA bizhub C654`. Alle sju spørsmål er ubesvarlige av samme
grunn, og ingen av dem er gjettet.

Merk størrelsen: 5,2 MB for elleve sider er ~470 kB per side. Det er
sideskann i høy oppløsning, og et OCR-forsøk ville sannsynligvis
lyktes — men det er en annen oppgave, og resultatet ville vært vår
lesing av et bilde, ikke kildens tekst.

**Denne kroppen er den eneste kilden til rådet for 2016–2017 i original
form.** Innholdet er likevel ikke tapt: 2018-kroppens Tabell 1 restaterer
det, i tekst, i kolonnen «Råd 2017 For 2016–2017». Se under.

### 2018 — `Styringsgruppens-oppsummering.pdf`

12 sider. Tittel på førstesiden: `STATUSRAPPORT FRA STYRINGSGRUPPEN FOR
VURDERING AV LAKSELUSPÅVIRKNING.`

1. **Vurderingsår: 2016, 2017 og 2018.**

   > «Styringsgruppens oppsummering av lakselusindusert dødelighet for
   > laks i produksjonsområdene i 2016, 2017 og 2018 (Tabell 1) er basert
   > på ekspertgruppens vurderinger gitt i egne rapporter til
   > styringsgruppen (Nilsen mfl. 2017, 2018) og styringsgruppens egne
   > vurderinger.»

   Og om hva kroppen ER, som forklarer resten av formen:

   > «Mandatet fastsetter at Styringsgruppen skal gi departementet råd
   > knyttet til kapasitetsjusteringer i oppdrettsnæringen i oddetallsår.
   > 2018 som et liketallsår, gir derfor kun en oppsummering.»

2. **PO-tabell: ja, Tabell 1, som TEKST**, 13 rader. Kolonneoverskrifter
   ordrett, over tre linjer i kroppen:

   ```
   Prod.-      2016         2016        2017        2017      2016–2017    Råd     2018        2018        2018
   områder                                                    usikkerhet   2017                            usikkerhet
            Vurdering    Variasjon   Vurdering   Variasjon                 For   Vurdering   Variasjon
            dødelighet    mellom     dødelighet   mellom      Ekspertgr.  2016–  dødelighet   mellom      Ekspertgr.
                          metoder                 metoder                  2017               metoder
   ```

   Kroppens Tabell 2 (metodematrisen) er derimot et **BILDE** — sidas
   tekstlag har bildeteksten og fotnoten, men ingen celler.

3. **Verdiformat: terskler** i Tabell 1 (`< 10 %`, `10-30%`, `> 30 %`) og
   i den kategorigrupperte prosaen. Men **kategorinavn** i per-PO-
   avsnittene: `Konklusjon: Lav risiko for lakselusindusert
   villfiskdødelighet i 2018.` Begge skrivemåter finnes i samme kropp.
   Koblingen er kroppens egen, i bildeteksten til Tabell 2:

   > «Hovedkonklusjonen tolkes som en ekspertvurdering for at det er en
   > sannsynlig risiko for at mindre enn 10% (lav), 10-30% (moderat) og
   > mer enn 30% (høy) av vill laksesmolt i en region har en
   > lakselusindusert dødelighet.»

4. **Sammenslått råd: JA — men for 2016–2017, ikke for 2018.** Kolonnen
   heter ordrett `Råd 2017 For 2016–2017`. Regelen står i bildeteksten:

   > «Råd for 2016–2017 samlet er gjort av styringsgruppen.»

   Bildeteksten sier hvem som slår sammen, men ikke HVORDAN. Selve
   regelen er ikke formulert i denne kroppen; den formuleres først i
   2018-2019-kroppen («konservativ tilnærming», se under). Målt på
   kolonnen: fire områder har ulik kategori i 2016 og 2017 — PO 2, 4, 6
   og 7 — og rådet er den verste av de to i alle fire.

5. **Prosagjentakelse: ja, i TO former.** Først gruppert per kategori
   (side 4): «Sannsynlig dødelighet < 10 % med liten usikkerhet:
   Områdene 1, 8, 9, 10, 11, og 13.» Deretter ett avsnitt per
   produksjonsområde (sidene 6–8) med `Konklusjon:` og `Usikkerhet:`.

6. **Usikkerhet: egne kolonner med ord.** `Variasjon mellom metoder` i
   tre nivåer med bokstavkode — `Liten (L)`, `Middels (LM)`, `Stor (LMH)`
   — der bokstavene er kategoriene metodene fordeler seg på. I tillegg
   `usikkerhet Ekspertgr.` med `Liten`/`Middels`/`Stor`. I Tabell 2
   (bildet) kodes usikkerhet som **cellefarge**, som ikke finnes i
   tekstlaget i det hele tatt.

7. **Bare figur? Delvis.** Tabell 2 er et bilde, men den bærer
   metodematrisen, ikke rådet. Rådet og konklusjonene finnes i tekst tre
   steder. Stoppregelen er ikke utløst.

### 2018-2019 — `rad-fra-styringsgruppen-til-nfd-2019.pdf`

13 sider. Bærer `UO § 15.3 (UTSATT OFFENTLIGHET )` på førstesiden.

1. **Vurderingsår: 2018 og 2019.**

   > «Vi avgir her styringsgruppens råd og vurderinger til NFD basert på
   > ekspertgruppens vurderinger av lakseluspåvirkning i
   > produksjonsområdene basert på årene 2018 og 2019 (Vedlegg 1).»

2. **PO-tabell: ja, Tabell 3**, 13 rader. Kolonneoverskrifter ordrett:

   ```
   Prod.-      2018         2018         2019          2019           Råd
   områder   Vurdering   Usikkerhet   Vurdering    Usikkerhet     2018-2019
             dødelighet                dødelighet
   ```

   Kroppen har også Tabell 1 og Tabell 2 (per år, med metodekolonner).

3. **Verdiformat: terskler**, både i tabellen og i punktlista:
   `< 10%`, `10-30%`, `> 30%`. Ingen kategorinavn i rådsleddet.

4. **Sammenslått råd: JA.** Kolonnen heter ordrett `Råd 2018-2019`.
   Sammenslåingsregelen står i to setninger:

   > «Grunnet variasjoner mellom år og metoder, samt usikkerhetene i
   > ekspertgruppens vurderinger, er styringsgruppens råd basert på lik
   > vekting av årene 2018 og 2019. Vi har ikke grunnlag for å vekte et
   > av de to årene over det andre.»

   > «Der ekspertgruppens vurderinger for kategori av dødelighet for et
   > område er forskjellig i 2018 og 2019 har styringsgruppen, på lik
   > måte som for rådet avgitt i 2017, valgt en konservativ tilnærming
   > for samlet vurdering av lakselusindusert dødelighet (Tabell 3).»

   Bildeteksten legger til: «Rådet for 2018-2019 samlet er gjort av
   styringsgruppen.»

5. **Prosagjentakelse: ja**, punktliste per PO etter tabellen:
   «Produksjonsområde 2 sannsynlig dødelighet 10-30% / Usikkerheten
   vurderes som middels i 2018-2019 / I 2018 vurdert dødelighet 10-30%
   med usikkerhet mot > 30%».

6. **Usikkerhet: egen kolonne per år**, med ordene `Liten`, `Middels`,
   `Stor`. I prosaen i tillegg en retning: «med usikkerhet mot > 30%».
   Punktlista skiller også år der de to spriker: «Usikkerheten vurderes
   som middels i 2018 og stor i 2019» (PO6, PO9).

7. **Bare figur? Nei.** Alt er tekst.

### 2020 — `styringsgruppen-evaluering-prodomrader-2020.pdf`

13 sider. Bærer `UO § 15.3 (UTSATT OFFENTLIGHET )`.

1. **Vurderingsår: 2020 alene.** Overskriften er `Styringsgruppens
   vurderinger for 2020`, og:

   > «Styringsgruppens vurderinger er basert på Ekspertgruppens rapport
   > til Styringsgruppen (Vedlegg 1) og Styringsgruppens egne
   > vurderinger.»

2. **PO-tabell: ja, Tabell 1**, 13 rader. Over kolonnerekka står en egen
   bannerlinje. Ordrett:

   ```
   Vurderingen 2020 (konklusjonusikkerhet)
    2020    Trål    Ruse/garn    Bur    HI smitte    HI VS    VI VS    SINTEF VS    Hovedk.
   ```

   («konklusjonusikkerhet» er kroppens egen skrivemåte, uten skilletegn.)

3. **Verdiformat: kategorinavn i tabellen** (`Lav`, `Mod`, `Høy`, med
   usikkerheten limt på: `Lavlit`, `Modmid`, `Høystor`), **terskler i
   prosaen** (`< 10%`, `10-30%`, `> 30%`). To skrivemåter i samme kropp.

4. **Sammenslått råd: NEI.** Det finnes ingen kolonne og intet avsnitt
   som slår sammen to vurderingsår. Kroppen har én årskolonne, og
   punktlista er datert til ett år. **Fraværet er funnet:** dette er
   første kropp uten sammenslåing, og bruddet mot 2018-2019 er skarpt —
   der fantes både kolonne, regelsetning og bildetekst om hvem som slo
   sammen.

   Kroppen omtaler flerårighet, men som ekspertgruppens observasjon om
   variasjon, ikke som en rådsregel: «I enkelte POer er det også klare
   tegn til toårige mønster i vurderingene (for eksempel PO4 og PO7).»

5. **Prosagjentakelse: ja**, punktliste per PO: «Produksjonsområde 4
   sannsynlig dødelighet 10-30% / Usikkerheten vurderes som middels med
   usikkerhet mot > 30%».

6. **Usikkerhet: superscript OG piler.** Bildeteksten sier det ordrett:

   > «Kategorien er indikert med usikkerhet i superscript. ↑↓ Piler
   > indikerer om usikkerheten for konklusjonen «moderat» peker mot
   > kategorien over eller under (Tabell 2 i Ekspertgruppens rapport).»

   I prosaen som ord: «Usikkerheten vurderes som stor med usikkerhet mot
   < 10%».

7. **Bare figur? Nei.**

### 2021 — `styringsgruppens-evaluering-av-produksjonsomrader-2021.pdf`

14 sider.

1. **Vurderingsår: 2021, pluss en oppdatert vurdering av 2020.**

   > «Som beskrevet over har modellene har blitt videreutviklet siden
   > vurderingene i 2020, og Ekspertgruppen har derfor oppdatert sine
   > vurderinger for 2020 i årets rapport.»

   (Ordfeilen «har modellene har» er kroppens egen.)

2. **PO-tabell: ja, TRE av dem**, alle som tekst:

   ```
   Tabell 1:  Vurderingen 2021 (konklusjonusikkerhet)
              2021   Trål   Ruse/garn   Bur   HI smitte   HI VS   VI VS   SINTEF VS   Hovedk.

   Tabell 2:  Oppdatert vurdering 2020 (konklusjonusikkerhet)
              2020   Trål   Ruse/garn   Bur   HI smitte   HI VS   VI VS   SINTEF VS   Hovedk.

   Tabell 3:  PO   2016   2017   2018   2019   2020   2021
   ```

   Tabell 3 er en historikktabell over ekspertgruppens hovedkonklusjoner
   for hele serien 2016–2021.

3. **Verdiformat: kategorinavn i tabellene** (`LavLit`, `Mod↓Mid`,
   `HøyMid`), **terskler i prosaen**. Tabell 3 har rene kategorinavn
   uten usikkerhet (`Lav`, `Mod`, `Høy`).

4. **Sammenslått råd: NEI.** Dette er verdt å merke seg: 2021 er et
   ODDETALLSÅR, altså et år der mandatet sier at styringsgruppen skal gi
   råd om kapasitetsjustering, og kroppen HAR begge grunnlagsårene på
   bordet (Tabell 1 for 2021, Tabell 2 for oppdatert 2020). Råstoffet for
   en sammenslåing ligger der. Den gjøres likevel ikke: overskriften er
   `Styringsgruppens vurderinger for 2021`, og punktlista er datert til
   ett år.

5. **Prosagjentakelse: ja**, punktliste per PO.

6. **Usikkerhet: superscript og piler**, som 2020. En pil til er i bruk:
   PO5 i Tabell 1 har `Mod↕Stor` — dobbeltpil. Prosaen bytter ordlyd fra
   2020: «med retning mot < 10%» der 2020 skrev «med usikkerhet mot».

7. **Bare figur? Nei.**

### 2022 — `styringsgruppen-evaluering-2022-1.pdf` / NVA

16 sider. Finnes på begge verter; se «Samme rapport, to hasher».

1. **Vurderingsår: 2022 alene.**

   > «Styringsgruppens vurdering for 2022 er at følgende sannsynligheter
   > for lakselusindusert dødelighet hos utvandrende vill laksesmolt i
   > produksjonsområdene gjelder.»

2. **PO-tabell: ja, Tabell 2**, 13 rader. Formen er helt ny —
   metodekolonnene er borte, erstattet av én kolonne per
   dødelighetsintervall. Kolonneoverskrifter ordrett:

   ```
   Produksjonsområde   Dødelighet    Dødelighet    Dødelighet    Konklusjon uttrykt
                       under 10 %     10‒30 %      over 30 %       som i tidligere
                                                                      rapporter
   ```

   Merk tegnet i `10‒30 %`: det er U+2012 figurstrek, ikke bindestrek.
   Kroppen har også Tabell 3, en historikktabell `PO | 2016 | … | 2022`.

3. **Verdiformat: TRE skrivemåter i samme tabell.** Terskler i
   kolonneoverskriftene, IPCC-sannsynlighetsord i cellene (`Veldig
   sannsynlig`, `Mer sannsynlig enn ikke`, `Svært usannsynlig`), og
   kategorinavn med usikkerhet i siste kolonne (`Moderatstor`,
   `Høymiddels`). Prosaen bruker terskler. Ordskalaen er definert i
   kroppens Tabell 1, «Kobling mellom uttrykksform og
   sannsynlighetsintervall tilpasset etter IPCC».

4. **Sammenslått råd: NEI.** Ingen kolonne, intet avsnitt.

5. **Prosagjentakelse: ja**, punktliste per PO: «Produksjonsområde 6
   sannsynlig dødelighet 10-30 % / Usikkerheten vurderes som stor».
   Merk mellomrommet foran `%`, som ikke fantes i 2020 og 2021.

6. **Usikkerhet: to lag.** Sannsynlighetsfordelingen over de tre
   intervallene er selve usikkerhetsuttrykket; i tillegg står den gamle
   formen som superscript i konklusjonskolonnen. Ingen piler.

7. **Bare figur? Nei.**

### 2023 — NVA

22 sider, den lengste av dem alle.

1. **Vurderingsår: 2023 alene.**

   > «Styringsgruppens vurdering for 2023 er at følgende kategorier for
   > lakselusindusert dødelighet hos utvandrende vill laksesmolt i
   > produksjonsområdene gjelder:»

   Kroppen omtaler også 2022, men som ekspertgruppens
   heterogenitetsanalyse for det året, ikke som en vurdering
   styringsgruppen gir råd om.

2. **PO-tabell: ja, Tabell 2**, 13 rader. Kolonneoverskrifter ordrett:

   ```
   Produksjons     Dødelighet    Dødelighet    Dødelighet    Konklusjon uttrykt
     -område         <10 %        10‒30 %        > 30 %        som i tidligere
                                                                  rapporter
   ```

   Nesten som 2022, men ikke likt: `under 10 %` er blitt `<10 %`, `over
   30 %` er blitt `> 30 %`, og `Produksjonsområde` er delt over to
   linjer som `Produksjons -område`. Kroppen har dessuten Tabell 3 og 4
   (heterogenitet, 2023 og 2022) og Tabell 5 (historikk `PO | 2016 | … |
   2023`).

3. **Verdiformat:** som 2022 — terskler i overskrifter, IPCC-ord i
   celler, kategorinavn med superscript i siste kolonne. Prosaen bruker
   terskler.

4. **Sammenslått råd: NEI.**

5. **Prosagjentakelse: ja**, men **listeformen er endret**: `PO1
   sannsynlig dødelighet < 10 %` der alle tidligere kropper skrev
   `Produksjonsområde 1 sannsynlig dødelighet`. Et uttrekk skrevet mot de
   eldre kroppene ville funnet null rader her — og null rader er stille.

6. **Usikkerhet:** som 2022, med et tillegg i bildeteksten: «usikkerhet
   er angitt som hevet liten skrift, og forklart i kapittel 5.3 i
   ekspertgruppens rapport».

7. **Bare figur? Nei.**

### 2024 — NVA

14 sider. Eneste kropp eksportert med `Adobe PDF Library`, og det får
følger — se punkt 7.

1. **Vurderingsår: 2024 alene.** Overskriften er `Styringsgruppens
   vurderinger for 2024`, og:

   > «Rapporten vurderer status for lakselusindusert dødelighet i hvert
   > produksjonsområde i 2024.»

   (Sitert med mellomrom rettet der tekstlaget har mistet dem; kroppen
   skriver «Rapporten vurdererstatus».)

2. **PO-tabell: ja, Tabell 2**, 13 rader. Kolonneoverskrifter ordrett:

   ```
   PO    Konklusjon      Sannsynlighet for        Sannsynlighet for
         påvirkning    dødelighet over 10 %     dødelighet over 30 %
   ```

   Konklusjonen har flyttet fra SISTE til ANDRE kolonne, og de tre
   intervallkolonnene er blitt to terskelkolonner. Kroppen har også
   Tabell 3 (heterogenitet) og Tabell 4 (historikk `2016-2024`).

3. **Verdiformat: kategorinavn i tabellen** (`Lav`, `Moderat`, `Høy`) og
   **terskler i prosaen**. Superscript-usikkerheten er borte fra
   konklusjonskolonnen.

4. **Sammenslått råd: NEI.** Kroppen NEVNER toårsperioden, men som
   begrunnelse for heterogenitetsanalysen, ikke som en rådsregel:

   > «Heterogenitetsanalyser er innført i Trafikklyssystemet for å
   > beskrive konsekvensen av lakselusindusert dødelighet i
   > produksjonsområdene bedre, og som et hjelpemiddel ved fargesetting
   > av produksjonsområder hvor vurderingene varierer innenfor
   > fargesettingsperioden på to år.»

   Toårsperioden tilhører altså DEPARTEMENTETS fargesetting, ikke
   styringsgruppens råd. Styringsgruppen gir fortsatt ett år.

5. **Prosagjentakelse: ja**, punktliste per PO i 2023-formen (`PO1
   sannsynlig dødelighet`).

6. **Usikkerhet: to sannsynlighetskolonner**, med IPCC-ordskalaen
   definert i kroppens Tabell 1. Ingen superscript, ingen piler.

7. **Bare figur? Nei — men tekstlaget er skadet.** Adobe-eksporten har
   mistet ordmellomrom i store deler av dokumentet: punktlista kommer ut
   som `PO1sannsynligdødelighet<10%`, og brødteksten som
   `Styringsgruppens vurderi nger er b asert på resultat er
   oginformasjonsom pr esent er es i`. Tegnene er der, men
   ordgrensene er ikke. Et mønster med `\s+` mellom ordene finner null
   rader i denne ene kroppen.

### 2025 — NVA

18 sider. **Den kroppen som bryter mønsteret mest.**

1. **Vurderingsår: 2024 OG 2025.**

   > «I tillegg til vurderinger for 2025, inneholder årets
   > ekspertgrupperapport oppdaterte vurderinger for 2024 grunnet
   > utvikling av modellene som brukes av Ekspertgruppen og ny kunnskap.»

   > «Styringsgruppens vurdering for 2024 og 2025 er at følgende
   > kategorier for lakselusindusert dødelighet hos utvandrende vill
   > laksesmolt i produksjonsområdene gjelder som beskrevet i Tabell 8.»

2. **PO-tabell: ja, Tabell 8**, 13 rader, med to årskolonner.
   Kolonneoverskrifter ordrett:

   ```
              2024            2025
    PO     Konklusjon      Konklusjon
           påvirkning      påvirkning
   ```

   Kroppen har også Tabell 2 (`PO | Sannsynlighet for dødelighet over
   10 %: 2024, 2025 | Sannsynlighet for dødelighet over 30 %: 2024,
   2025`), Tabell 4 og 6 (heterogenitet per år).

3. **Verdiformat: kategorinavn MED midtpunktstall i parentes** —
   `Lav (0,3)`, `Moderat (14)`, `Høy (39)`. Tallet er nytt i denne
   kroppen. Bildeteksten forklarer det:

   > «Konklusjonene om påvirkningskategoriene lav (under 10 %
   > lakselusindusert dødelighet), moderat (10–30 % dødelighet) og høy
   > (over 30 % dødelighet) er gitt av midtpunktet i
   > sannsynlighetsfordelingene (i parentes).»

4. **Sammenslått råd: NEI — og dette er det viktigste funnet i denne
   kroppen.** Overskriften dekker to år, men tabellen har **én kolonne
   per år og ingen sammenslått kolonne**. Det finnes heller ingen
   regelsetning om hvordan to år veies mot hverandre. Kroppen slipper
   unna spørsmålet ved at det ikke oppstår:

   > «I henhold til Styringsgruppens vurdering endret ingen av
   > produksjonsområdene kategori fra 2024 til 2025 (Tabell 8).»

   Målt på Tabell 8: alle tretten områder har samme kategori i begge år.
   **Sammenslåingsregelen fra 2018-2019 er ikke gjeninnført — den er
   bare ikke satt på prøve.**

   Kroppen formulerer derimot én annen terskelregel, ordrett:

   > «Styringsgruppen forstår definisjonen av miljøpåvirkning i
   > Stortingsmelding 16 (2014-15) tabell 10.1. som at kategorien lav er
   > mindre enn 10 % og at kategori moderat er fra og med 10 % til og med
   > 30 %. Vi mener derfor at en medianverdi lik 10 % bør plasseres i
   > moderat påvirkning.»

   Det er en regel om GRENSEN mellom to kategorier, ikke om
   sammenslåing av to år.

5. **Prosagjentakelse: NEI.** Søk etter alle formene fra de tidligere
   kroppene — `Produksjonsområde N sannsynlig dødelighet`, `PON
   sannsynlig dødelighet`, og mellomromsløse varianter — gir **null
   treff**. Rådet per PO finnes bare i Tabell 8. Punktlista, som har
   vært der i hver eneste kropp siden 2018, er borte.

   Det har en direkte konsekvens: **kryssjekken forsvinner.** Alle
   kropper fra 2018 til 2024 sier rådet to ganger, og
   `docs/KILDE-EKSPERTGRUPPEN.md` punkt 4 kaller den doble lesingen «den
   eneste kontrollen som kan felle et uttrekk som er syntaktisk vellykket
   og semantisk feil». For 2025 finnes den kontrollen ikke.

6. **Usikkerhet: midtpunktstallet i parentes**, pluss en egen Tabell 2
   med IPCC-ord per år og per terskel. Bildeteksten til Tabell 2 nevner
   dessuten en visuell koding: «Usikkerhetskategoriene er visualisert med
   gråtoner fra hvit (svært usannsynlig) til mørk grå (veldig
   sannsynlig).» Gråtonen er redundant her — ordet står i cella — men den
   er samme mekanisme som 2018-kroppens cellefarge, der ordet IKKE sto.

7. **Bare figur? Nei.**

   Én ting til, som ikke er et formatfunn men en revisjon: 2024-kroppen
   skriver PO9 som `Lav-Moderat`, mens 2025-kroppen skriver PO9 for 2024
   som `Moderat (11)`. To kropper, samme vurderingsår, ulik verdi. Det er
   formen `diff.revisjon()` finnes for.

---

## Steg 3 — tabell mot prosaliste

For hver kropp som har både PO-tabell og prosaliste er rådet lest fra
begge og talt opp. Ingen uenighet er utlignet, og ingen vinner er valgt.

Sammenligningen krever at kategorinavn og terskler kan holdes opp mot
hverandre. **Koblingen er kildens egen**, ikke vår: «mindre enn 10%
(lav), 10-30% (moderat) og mer enn 30% (høy)» (2018-kroppen), gjentatt i
2023-, 2024- og 2025-kroppene. Verdiene er ikke normalisert i
rapporteringen — de står ordrett i tabellene under.

| kropp | tabellrader | prosarader | **uenigheter** |
|---|---|---|---|
| 2018 (Tabell 1, 2018-kolonnen, mot kategorigruppert prosa) | 13 | 13 | **0** |
| 2018 (Tabell 1, 2018-kolonnen, mot per-PO «Konklusjon:») | 13 | 13 | **0** |
| 2018-2019 (Tabell 3, «Råd 2018-2019», mot punktliste) | 13 | 13 | **0** |
| 2020 (Tabell 1 «Hovedk.» mot punktliste) | 13 | 13 | **0** |
| 2021 (Tabell 1 «Hovedk.» mot punktliste) | 13 | 13 | **0** |
| 2022 (Tabell 2 «Konklusjon …» mot punktliste) | 13 | 13 | **0** |
| 2023 (Tabell 2 «Konklusjon …» mot punktliste) | 13 | 13 | **0** |
| 2024 (Tabell 2 «Konklusjon påvirkning» mot punktliste) | 13 | 13 | **0** |
| 2025 | 13 | **0 — ingen prosaliste** | **kan ikke måles** |
| 2017 mai, 2017 sept | — | — | **kan ikke måles (skann)** |

**Hva de nullene betyr, og ikke betyr.** For 2018-2019 er begge lesingene
styringsgruppens eget råd, og null uenigheter er en ren kryssjekk. For
2020–2024 er tabellen EKSPERTGRUPPENS hovedkonklusjon og prosalista
STYRINGSGRUPPENS vurdering. At de er like i alle 65 cellene betyr at
styringsgruppen i disse fem årgangene ikke har fraveket ekspertgruppen i
noen PO — det er et funn om kilden, ikke bare om uttrekket.

### Kontrollen på 2018-2019 passerer

Fasiten var kjent: seks av tretten områder skal ha forskjellig kategori i
de to årene (PO 2, 3, 4, 5, 7, 10), og rådet skal være den verste av de
to i alle seks.

    PO med ulik kategori mellom 2018 og 2019 : [2, 3, 4, 5, 7, 10]
    råd = verste av de to i alle seks        : ja
    uenigheter tabell vs punktliste          : 0

Målt:

| PO | 2018 | 2019 | Råd 2018-2019 |
|---|---|---|---|
| 2 | `10-30%` | `< 10%` | `10-30%` |
| 3 | `> 30%` | `10-30%` | `> 30%` |
| 4 | `10-30%` | `> 30%` | `> 30%` |
| 5 | `10-30%` | `> 30%` | `> 30%` |
| 7 | `10-30%` | `< 10%` | `10-30%` |
| 10 | `< 10%` | `10-30%` | `10-30%` |

Uttrekket er dermed etterprøvd mot et menneskes lesing av samme kropp.

**Og den samme regelen gjelder ett år tidligere.** 2018-kroppens kolonne
`Råd 2017 For 2016–2017` er lest med samme metode: fire områder har ulik
kategori i 2016 og 2017 — PO 2, 4, 6 og 7 — og rådet er den verste av de
to i alle fire.

| PO | 2016 | 2017 | Råd 2016–2017 |
|---|---|---|---|
| 2 | `10-30%` | `< 10 %` | `10-30%` |
| 4 | `10-30%` | `> 30 %` | `> 30 %` |
| 6 | `10-30%` | `< 10 %` | `10-30%` |
| 7 | `10-30%` | `< 10 %` | `10-30%` |

Det er en uavhengig bekreftelse av regelen, på en årgang hvis egen kropp
er en uleselig skann. 2018-2019-kroppen sier selv at det er samme regel:
«på lik måte som for rådet avgitt i 2017».

### To feilspor som ble fanget, og hvordan

Begge er verdt å skrive ned, fordi de er nøyaktig den feilformen
oppgaven advarer mot — riktig form, feil tall.

**Ombrukne tabellrader.** Første uttrekk av 2018-kroppens Tabell 1
rapporterte 9 uenigheter mot prosaen. Årsaken var ikke kilden: rader der
en celle er brutt over to linjer (`Stor` / `(LMH)`) forskjøv
kolonnetellingen, så «2018 Vurdering» ble lest fra feil felt. Etter at
radene settes sammen til logiske rader før kolonnene leses: 13 rader, 0
uenigheter. Ni oppdiktede uenigheter ville sett ut som et funn om
kilden.

**`Områdene?` matcher ikke `Område`.** Prosauttrekket fant 11 av 13
områder, og de to som falt ut var PO3 og PO4 — de to eneste som står i
ENTALL («Område 4.») fordi de er alene i sin kategori. Det ga to
«uenigheter» som var to manglende rader. Mønsteret måtte være
`Område(?:ne)?`. Merk hvilke to som falt ut: de eneste i høy- og
stor-usikkerhet-kategoriene. Samme form som orddelingsfeilen i
`docs/KILDE-EKSPERTGRUPPEN.md` punkt 4, der de to som falt ut var
nettopp de to i høy-kategorien.

---

## Når dokumentet endret karakter

Én setning per kropp, om overgangen fra «styringsgruppen slår sammen to
år» til «styringsgruppen vurderer ett år»:

* **2017 mai** — kan ikke svare; kroppen er en skann uten tekstlag.
* **2017 sept** — kan ikke svare; samme grunn, men 2018-kroppen
  restaterer rådet dens som et sammenslått `Råd 2017 For 2016–2017`, så
  årgangen SLO SAMMEN.
* **2018** — slår sammen, i kolonnen `Råd 2017 For 2016–2017`, men gir
  ikke selv noe råd for 2018, fordi «2018 som et liketallsår, gir derfor
  kun en oppsummering».
* **2018-2019** — slår sammen, i kolonnen `Råd 2018-2019`, og er den
  eneste kroppen som skriver ned regelen for hvordan: lik vekting av de
  to årene, og «en konservativ tilnærming» der de spriker.
* **2020** — **her skjer endringen**: overskriften er `Styringsgruppens
  vurderinger for 2020`, tabellen har én årskolonne, og verken kolonne
  eller regelsetning for sammenslåing finnes.
* **2021** — vurderer ett år, og det er den sterkeste bekreftelsen på at
  endringen er reell og ikke en tilfeldighet ved 2020: 2021 er et
  oddetallsår med begge grunnlagsårene i kroppen (Tabell 1 for 2021,
  Tabell 2 for oppdatert 2020), og slår dem likevel ikke sammen.
* **2022** — vurderer ett år.
* **2023** — vurderer ett år.
* **2024** — vurderer ett år, og flytter uttrykkelig toårigheten over til
  departementet: heterogenitetsanalysen er «et hjelpemiddel ved
  fargesetting … innenfor fargesettingsperioden på to år».
* **2025** — dekker to år i overskrift og tabell, men slår dem ikke
  sammen: to årskolonner, ingen rådskolonne, ingen regelsetning, og
  spørsmålet oppstår ikke fordi «ingen av produksjonsområdene endret
  kategori fra 2024 til 2025».

**Endringen finnes, og den skjedde i 2020-kroppen.** Den er ikke reversert
i 2025 — der er toårigheten kommet tilbake i DEKNING, men ikke i
SAMMENSLÅING. Skulle de to årene sprike i en framtidig kropp, finnes det
ingen skrevet regel i noen kropp etter 2019 for hva rådet da blir.

---

## For en framtidig kilde

Kartleggingen svarer ikke på om kilden skal bygges. Den sier hva den i så
fall må tåle, og hvert punkt er målt over:

1. **Fire verter, ikke én.** NVA dekker 2022–2025, hi.no 2017–2019,
   trafikklyssystemet.no 2017 mai, og regjeringen.no svarer 403 så
   2020–2022 må gå via Wayback.
2. **To årganger er ikke maskinlesbare.** 2017 mai og 2017 sept er skann
   uten OCR-lag. 2016–2017-rådet finnes likevel i tekst, restatert i
   2018-kroppens Tabell 1.
3. **Én uttrekksfunksjon per kropp.** Kolonneoverskriftene endrer seg
   hvert eneste år; konklusjonen flytter fra siste til andre kolonne
   mellom 2023 og 2024; `10‒30 %` skifter tegn; `Produksjonsområde N`
   blir `PON` i 2023; punktlista forsvinner helt i 2025.
4. **2024-kroppen mangler ordmellomrom.** Mønstre med `\s+` finner null
   rader der.
5. **Kryssjekken finnes for 2018–2024 og ikke for 2025.** En vakt som
   krever to lesinger vil felle 2025-kroppen; en som ikke krever det,
   mister kontrollen for alle de andre.
6. **`raw_hash` identifiserer ikke en rapport.** 2022 finnes som to
   kropper med samme tekst og to ulike hasher.
7. **`published_at` fra `/CreationDate`.** `Last-Modified` er en
   migreringsdato på NVA (tre kropper innenfor fem sekunder) og på
   trafikklyssystemet.no (fem år på etterskudd). Den ser riktig ut på
   regjeringen.no-kroppene, men kan ikke etterprøves der, siden opphavet
   nå svarer 403.
8. **To kropper er stemplet `UO § 15.3 (UTSATT OFFENTLIGHET)`:**
   2018-2019 og 2020.
