# Måling 14.09.2026 — kan vi følge en långivers eksponering mot en fargelegging?

Hypotesen: en akvakulturtillatelse er et realregisterobjekt. Den kan
pantsettes og overføres, og tinglysing gir rettsvern etter
A-registerforskriften. Kan vi da følge en långivers eksponering mot en
fargeleggingsbeslutning?

Målt mot data vi allerede har. Ingen ny innsamling.

**Kortsvaret: nei, og gapet er ikke gradvist — det er totalt.** Vi har
null felter om pant, heftelser eller tinglysing. Det som ER mulig er
nabospørsmålet «hvem eide hva når, i hvilket område, med hvilken farge»,
og det er svarbart for **11 % av tillatelsene**.

Ingen vurdering av forretningsverdi her. Bare hva som kan besvares, hva
som ikke kan, og hva som måtte samles inn.

---

## a) Feltene vi faktisk har

### Det som finnes

| kilde | entitet | felter | snapshots |
|---|---|---|---|
| `eierskap` | tillatelse | 19 | **2** (02.09, 14.09.2026) |
| `eierskap_historikk` | overføring | 8 | 42 filer, 2 611 overføringer |
| `akvakultur` | lokalitet | 29 | 5 (17.08–14.09.2026) |
| `trafikklysvedtak` | produksjonsområde | 2 | 4 runder (2018–2024) |

`eierskap`: `eier_navn`, `eier_orgnr`, `eier_type`, `organisasjonsform`,
`tildelt_navn`, `tildelt_orgnr`, `tildelt_tid`, `kapasitet`,
`kapasitet_enhet`, `kapasitet_type`, `lokaliteter`, `lokaliteter_antall`,
`prodomraade_kode`, `prodomraade_navn`, `kommunenummer`,
`portefoljetype`, `produksjonsstadium`, `tillatelse_formal`,
`tillatelse_type`.

`eierskap_historikk`: `tillatelse_nr`, `journal_dato`, `journal_nr`,
`mottaker_navn`, `mottaker_orgnr`, `mottaker_type`, `rekkefolge`,
`dato_forbehold`.

### Det som MANGLER — og det er hele hypotesen

**Null felter om pant, heftelser eller tinglysing. Ikke få — null.**

Målt over alle tolv kilder, 157 felter til sammen, søkt på `pant`,
`hefte`, `tinglys`, `laan`, `kreditt`, `sikkerhet`, `servitutt`, `urad`,
`beslag`, `utlegg`, `garanti`:

    akvakultur            29 felter   INGEN
    biomasse              10          INGEN
    biomasselag            7          INGEN
    eierskap              19          INGEN
    eierskap_historikk     8          INGEN
    ekspertgruppen         6          tre treff — FALSKE VENNER, se under
    enhetsregisteret      32          INGEN
    lusetall              11          INGEN
    reguleringsomraader    8          INGEN
    romming               23          INGEN
    sjotemperatur          2          INGEN
    trafikklysvedtak       2          INGEN

De tre treffene hos `ekspertgruppen` er `kategori__sikkerhet`,
`kategori_ordrett__sikkerhet` og `hi_smittepress_roc_indeks__sikkerhet`.
Det er **usikkerhetsgrad**, ikke sikkerhetsstillelse. Ordet er det
samme, størrelsen er en helt annen.

**Og det ligger ikke i rå-arkivet heller.** En tillatelse fra
`pub-aqua/licenses` har 19 toppnivånøkler, og ingen av dem gjelder
heftelser:

    capacity, connections, grantInformation, legacyLicenseNr,
    legalEntityName, legalEntityNrId, licenseId, licenseNr,
    openLegalEntityNr, originalLicenseNr, placement,
    portfolioMasterLicenseId, portfolioType, productionModel,
    productionRegime, species, type, version, versionId

Søk i hele arkivkroppen ga 0 treff på `pant`, `hefte`, `tinglys`,
`mortgage`, `pledge`, `encumbr`, `collateral` og `security`. De 16
treffene på `lien` er alle inne i artsnavnet «Strandrekefamilien».

**Det er altså ikke et parse-problem som kan lukkes med en re-parse.**
Fiskeridirektoratets åpne API publiserer ikke heftelsene. A-registerets
panteopplysninger er et annet register enn `pub-aqua`.

### Hva vi har i stedet for pant

`eierskap_historikk` gir **overføringer**, ikke heftelser. Forskjellen er
avgjørende for hypotesen:

* En overføring sier at tillatelsen skiftet innehaver.
* En pantsettelse sier at noen har sikkerhet i den **uten** at
  innehaveren skifter.

En långivers eksponering består av det andre. Den er usynlig for oss —
og den er usynlig på en måte som ikke gir noe spor i det hele tatt:
en pantsatt og en ubeheftet tillatelse ser identiske ut i alle våre 19
felter.

Dessuten: `journal_dato` er **journalføringsdato, ikke
overdragelsesdato**, og bæres med `dato_forbehold` på hver eneste rad med
ordlyden «senest da», ikke «akkurat da». Fiskeridirektoratet dokumenterer
den ikke. Tinglysingstidspunktet — det som gir rettsvern — har vi ikke.

---

## b) Tidslinje per tillatelse — hva som faktisk lar seg sette opp

Ja, delvis. Tre reelle tillatelser i PO4, valgt for å vise tre ulike
former.

PO4s fargehistorie, lest av vedtakene:

    2018   (hull — 2018-kroppen nevner PO 2, 3, 4, 5, 6 uten farge)
    2020   rød
    2022   rød
    2024   rød
    2026   gul     ← fra FOR-2026-08-20-1764, ARKIVERT MEN IKKE PARSET

Dekningsflaten er 40 av 65 celler (13 områder × 5 runder), se
`docs/KILDE-TRAFIKKLYSVEDTAK.md` punkt 8. Regner man bare de fire
rundene som HAR en parser, er den 40 av 52 — men 2026 er nettopp runden
dette spørsmålet gjelder, så 65 er den riktige nevneren her.

### SF-FL-0001 — konsernomstrukturering, ikke handel

    tildelt      AQUA FARMS MATFISK AS      1974-09-03
    2006-09-20   AQUA FARMS AS
    2006-12-29   PAN FISH NORWAY AS
    2007-12-27   MOWI NORWAY AS
    2019-12-24   MOWI ASA
    2022-12-23   MOWI SEAWATER NORWAY AS
    eier 14.09   MOWI SEAWATER NORWAY AS
    kapasitet    648,0 TN (02.09)  →  648,0 TN (14.09)
    lokaliteter  11803; 13838

De to siste leddene er 2019 og 2022 — årene beslutningsnotatet allerede
identifiserer som omstruktureringer, ikke oppkjøpsbølger. 38 andre
PO4-tillatelser har identisk kjede. **Et eierskifte i denne serien er
oftest en flytting inne i et konsern.**

### SF-A-0006 — ekte skifte av hender

    tildelt      LANDØY FISKEOPPDRETT AS    1981-07-23
    2019-07-04   LANDØY FISKEOPPDRETT AS
    2025-08-08   LANDØY HAVBRUK AS
    eier 14.09   LANDØY HAVBRUK AS
    kapasitet    648,0 TN  →  648,0 TN
    lokaliteter  11 stykker

### SF-A-0003 — ingen overføring på 53 år

    tildelt      FALK OG MAGNAR VILNES ANS  1973-09-28
    (ingen overføringer registrert)
    eier 14.09   FALK OG MAGNAR VILNES ANS  (UnlimitedLiabilityCompany)
    kapasitet    648,0 TN  →  648,0 TN
    lokaliteter  10317; 11800; 27055

Merk at ANS ikke filtreres bort: et ansvarlig selskap er et eget
rettssubjekt, til forskjell fra et ENK. Se `core/persondata.py`.

### Hva tidslinjen KAN og IKKE KAN

**Kan:** eierrekkefølge tilbake til 2006, dagens produksjonsområde,
fargen per runde 2020–2024, dagens kapasitet og lokaliteter.

**Kan ikke, og det er fire hull:**

1. **Kapasitetsutviklingen finnes ikke.** `eierskap` har **to
   snapshots, tolv dager fra hverandre**. Målt: **0 av 2 944 felles
   tillatelser** endret kapasitet i vinduet. Kolonnen «hvordan
   kapasiteten har endret seg» er tom, ikke fordi den er stabil, men
   fordi vi har tolv dagers historikk. Nedjusteringen etter et rødt lys
   trer dessuten i kraft **seks måneder** etter forskriften (§ 5), så
   selv et helt år med ukentlige snapshots ville fanget bare én
   justering.
2. **Produksjonsområdet er DAGENS, ikke historisk.** Tilknytningen leses
   av dagens `connections`. En tillatelse som lå i et annet PO i 2012
   tilskrives dagens. Å si «den lå i et rødt område da den ble overført i
   2019» er derfor en påstand vi ikke kan belegge.
3. **2026-fargen er ikke i dataene.** Forskriften er arkivert, men
   `FORSKRIFTER` mangler en uttrekksfunksjon for den — § 4-tabellen har
   fire runder per rad mot tre i 2024-kroppen. Fargen over er lest
   manuelt av kroppen, ikke av en parser.
4. **`journal_dato` er «senest da».** Hver rad i tidslinjen bærer sitt
   eget `dato_forbehold`.

---

## c) Eierskifter i røde og gule områder — og dekningen

### Populasjonen, etter siste kjente farge

    rød            114 tillatelser     89 med minst én overføring   78,1 %
    gul            210                163                           77,6 %
    grønn          822                650                           79,1 %
    uten PO      1 807                534                           29,6 %
    SUM          2 953

**114 + 210 = 324 tillatelser i rødt eller gult. 252 av dem har minst én
registrert overføring.**

### Overføringer per år, tillatelser med kjent PO

    2018    47      2022   675   ← omstrukturering
    2019   227      2023    85
    2020    15      2024    25
    2021     1      2025    75
                    2026    35

    1 740 av 2 611 overføringer gjelder en tillatelse med kjent PO (66,6 %)

2019 og 2022 er 52 % av alle overføringene og er begge
omstruktureringer. **Serien heter «journalførte overføringer av
tillatelser», ikke «eierskifter»**, og en analyse som teller rader her
teller konsernflyttinger.

### Eierskifter i VÅR snapshotserie: én

    eierskap-snapshots        02.09 og 14.09.2026 — tolv dager
    felles tillatelser        2 944
    eierskifte i vinduet          1
    kapasitetsendring             0

Det er forskjellen på de to seriene: **overføringshistorikken rekker til
2006, vår egen observasjonsserie er tolv dager.** Bare den andre er
noe vi har sett skje.

---

## d) Dekningen, båret gjennom

Hvert svar over hviler på en kjede, og kjeden er aldri sterkere enn sitt
svakeste ledd. Målt 14.09.2026:

| ledd | dekning | merknad |
|---|---|---|
| lokalitet → selskap | **1 722 av 1 782 = 96,6 %** | 57 permanent utelukket, 3 uten tillatelse |
| lokalitet → produksjonsområde | **969 av 1 782 = 54,4 %** | landbasert og ferskvann har ikke PO |
| tillatelse → produksjonsområde | **1 146 av 2 953 = 38,8 %** | svakeste ledd som finnes |
| produksjonsområde → farge | **40 av 65 celler = 61,5 %** | 13 områder × 5 runder; 2026 bidrar med 0 |
| tillatelse → pant | **0 %** | finnes ikke |

**De 57 er ikke et hull som kan tettes.** De er personeide lokaliteter
stoppet av personvernfilteret, og CLAUDE.md regel 3 er strengere enn
både lisensen og API-et. 3,2 % av lokalitetene er systematisk usynlige,
og de er ikke tilfeldig fordelt — de er små, personeide anlegg. En
analyse av «hvem er eksponert» utelater dem per konstruksjon, og
skjevheten peker samme vei hver gang.

### Den sammensatte dekningen

For spørsmålet «eierskifte i et område med kjent farge» må tillatelsen ha
både PO og farge:

    2 953 tillatelser
      ×  38,8 %  har produksjonsområde        →  1 146
      ×  ~100 %  av dem har en kjent farge    →  1 146
      =  324 i rødt eller gult                →  11,0 % av populasjonen

**Spørsmålet i c) er altså besvart for 11 % av tillatelsene**, og de 11 %
er ikke et tilfeldig utvalg: de er sjølokaliteter i de tretten
produksjonsområdene. Landbaserte anlegg, settefiskanlegg og
ferskvannslokaliteter er utenfor, og det er nettopp de som ikke rammes av
en fargelegging.

For pantespørsmålet er regnestykket kortere: **0 % ganger hva som helst
er 0 %.**

---

## Gapet — hva som måtte samles inn

Rangert etter hva som låser opp mest.

### 1. A-registerets heftelser (BLOKKERENDE)

Uten dette er hypotesen ikke delvis besvart — den er ubesvart.
Akvakulturregisteret føres av Fiskeridirektoratet og har en
panteboksdel; `pub-aqua` publiserer den ikke. Det som trengs per
tillatelse: **panthaver, beløp eller ramme, prioritet og
tinglysingsdato.**

Ikke undersøkt her: om opplysningene er tilgjengelige mot vederlag,
mot avtale, eller ikke i det hele tatt. **Det er det første spørsmålet
som må stilles**, og det er en e-post til Fiskeridirektoratet, ikke mer
kode. Merk at `docs/KILDER-IKKE-BYGGET.md` allerede har ett spor som ble
stengt på denne måten: § 44-databasen er børssensitiv.

### 2. Historisk produksjonsområde per tillatelse

I dag tilskrives dagens PO bakover. Uten historikk kan ingen påstand om
«lå i et rødt område den gangen» belegges. Vår akvakulturserie starter
17.08.2026, så dette kan bare bygges framover — CLAUDE.md regel 5.

### 3. Kapasitet over tid

To snapshots tolv dager fra hverandre. Nedjustering trer i kraft seks
måneder etter forskriften, så serien må gå i minst to år før én
fargeleggingssyklus er dekket fra vedtak til virkning. **Dette er den
ene mangelen som lukkes av seg selv, hvis innsamlingen bare får gå.**

### 4. 2026-fargen inn i `FORSKRIFTER`

En uttrekksfunksjon for FOR-2026-08-20-1764. Kroppen er arkivert, så det
er en re-parse uten frist.

### 5. Overdragelsesdato, ikke journalføringsdato

`journal_dato` er «senest da». Fiskeridirektoratet dokumenterer den
ikke — seks spec-adresser svarer 404. Krever et spørsmål til etaten.

---

## Hva målingen faktisk viste

Det som er verdt å ta med videre er ikke at pant mangler — det var
ventet. Det er at **de to nabospørsmålene også er svakere enn de ser
ut:**

* «Hvem eide den når» rekker til 2006, men halvparten av bevegelsen er
  konsernomstrukturering, og datoen er «senest da».
* «Hvilken farge hadde området» er svarbart for 38,8 % av tillatelsene,
  og bare for dagens områdetilknytning.

Et svar som hadde oppgitt «2 611 overføringer siden 2006» uten disse to
forbeholdene ville vært sant og villedende på samme tid.
