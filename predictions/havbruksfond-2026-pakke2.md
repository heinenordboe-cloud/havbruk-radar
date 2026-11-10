# Anslag: fordelingen fra Havbruksfondet 2026, pakke 2

Skrevet 09.11.2026 som utkast, før fordelingen er kjent, og forseglet
09.11.2026 av økt L. I 2024 kom fordelingen 21.10, i 2025 10.11.

Pakke 1, `predictions/havbruksfond-2026.md` (commit 66016dd, 12.10.2026),
gjelder uendret. Pakke 2 erstatter den ikke. Den legger til ni påstander
som er skarpere og kan avgjøres hver for seg: to om metoden (P2-1 og P2-2),
fire om lokaliteter der Fiskeridirektoratets praksis avgjør (P2-3 til P2-6)
og tre om andelene (P2-7 til P2-9).

Fila er `.md` og ikke `.yml`, så `forsegl.py` og `core/predictions.py`
hopper over den. Formatet bærer ikke anslaget (MALING-HAVBRUKSFOND.md A5).
Det er committen og stempelet som forankrer det. Fila røres ikke etter at
den er pushet; utfallet skrives i en ny fil.

**Grunnlaget** er MALING-HAVBRUKSFOND-PAKKE2.md og `pakke2.py` i
havbruk-analyse, `revisjon/2026-11-09-havbruksfond-pakke2/`, regnet 09.11.2026
mot havbruk-radar-data 1f82890 med havbruk-radar 8a27524. Tabellene under er
skrevet ut av skriptet.

**«Forventet»** er referansen i påstandene. Den er A2 fra pakke 1
(snapshotet 31.08.2026, samme filter, vekt og deling) med én endring:
Havbruksstasjonen i Tromsøs to lokaliteter, 10768 og 15236 (1 625 t), er med,
fordi Fiskeridirektoratet tok dem med både i 2024 og 2025. Tromsø får da
1,5475 % i stedet for 1,5056 %. Ingen annen kommune flytter seg mer enn 0,0020
prosentpoeng. Samlet MTB er 3 816 629 t.

**Gruppene.** Hver kommune er i én av tre:

- **U**, 89 kommuner: samme lokaliteter med samme MTB som på
  Fiskeridirektoratets liste per 01.09.2025.
- **E**, 26 kommuner: minst én lokalitet er kommet til, borte eller
  endret siden 01.09.2025, og ingen av lokalitetene er et grensetilfelle.
- **G**, 28 kommuner: har minst én lokalitet fra P2-3 til P2-6.

**Konfidens** står per påstand.

## Anslaget

```yaml
prediksjoner:
  - id: "2026-11-09-1"
    entitet: "kommuner, gruppe U (89)"     # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "mtb"
    type: "intervall"                      # FINNES IKKE i core/predictions.TYPER
    verdi_min: "forventet MTB − 1 t, per kommune"
    verdi_max: "forventet MTB + 1 t, per kommune"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      De 89 kommunene i gruppe U har de samme lokalitetene med samme MTB
      i snapshotet 31.08.2026 som på Fiskeridirektoratets liste per
      01.09.2025, etter filteret og vekten i A2. Forventet MTB er derfor
      også deres MTB i regnearket 2025. Mellom snapshotene 31.08 og
      07.09.2026 kom ingen lokalitet til, ingen falt ut og ingen endret
      MTB. Vekten max(kapasitet, kapasitet_midlertidig) stemmer med
      Fiskeridirektoratets tall for 954 av 954 uendrede lokaliteter i
      2025 og 842 av 842 i 2024.
    feil_hvis: >
      For minst én av de 89 kommunene avviker MTB-kolonnen per kommune i
      arket «Kommuner» i Fiskeridirektoratets regneark for 2026 («KAP
      REG» i 2025, «Kapasitet» i 2024) mer enn 1 t fra forventet MTB i
      tabellen under. Publiseres ikke regnearket innen 31.12.2026, kan
      påstanden ikke avgjøres.
    konfidens: 90
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-2"
    entitet: "kommuner, gruppe E (26)"     # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "mtb"
    type: "intervall"                      # FINNES IKKE i core/predictions.TYPER
    verdi_min: "forventet MTB − 1 t, per kommune"
    verdi_max: "forventet MTB + 1 t, per kommune"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      For de 26 kommunene i gruppe E er forventet MTB snapshotet
      31.08.2026 etter samme filter og vekt. Forskjellen fra 2025 er
      lokaliteter som er kommet til, falt ut eller fått ny kapasitet.
      For dem er vekten ikke prøvd mot Fiskeridirektoratets egne tall,
      og en ny lokalitet kan krysse en kommunegrense uten at det ses:
      kroppen har ett punkt per lokalitet, ikke en flate.
    feil_hvis: >
      For minst én av de 26 kommunene avviker MTB-kolonnen per kommune i
      arket «Kommuner» i Fiskeridirektoratets regneark for 2026 («KAP
      REG» i 2025, «Kapasitet» i 2024) mer enn 1 t fra forventet MTB i
      tabellen under. Publiseres ikke regnearket innen 31.12.2026, kan
      påstanden ikke avgjøres.
    konfidens: 80
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-3"
    entitet: "lokaliteter 10768 og 15236 (Tromsø)" # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "med_i_nokkelen"
    type: "verdi"
    verdi_min: "med, 650 t og 975 t"
    verdi_max: "med, 650 t og 975 t"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      10768 INDRE KÅRVIK I (650 t) og 15236 SKULGAMBUKT (975 t) i Tromsø
      sto på Fiskeridirektoratets lokalitetsliste både per 01.09.2024 og
      per 01.09.2025, med samme MTB som nå. Ingen av tillatelsene deres
      har laks, ørret eller regnbueørret i eierskapskroppene 02.09 og
      02.11.2026, og ingen kropp sier hvorfor de likevel er med.
      Påstanden hviler på praksis to år på rad, ikke på regelen.
    feil_hvis: >
      I lokalitetslista i regnearket 2026 (arket «Lok. per. 01.09.25» i
      2025, «Lok. per 01.09.24» i 2024) mangler 10768 eller 15236, eller
      en av dem har annen MTB enn 650 t og 975 t. Publiseres ikke
      regnearket innen 31.12.2026, kan påstanden ikke avgjøres.
    konfidens: 75
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-4"
    entitet: "lokalitet 38097 HØGÅS (Strand)" # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "med_i_nokkelen"
    type: "verdi"
    verdi_min: "med, 780 t"
    verdi_max: "med, 780 t"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      38097 HØGÅS sto på lista per 01.09.2024 med 780 t. Den manglet per
      01.09.2025, da den var ute av registeret (versjon
      PERM_SITE_RESURRECTED fra 03.10.2025). Per 31.08 og 07.09.2026 er
      den i registeret med 780 t og består filteret. Av lokalitetene som
      består filteret 31.08.2026, sto alle som fantes i registeret
      01.09.2025 på Fiskeridirektoratets liste det året.
    feil_hvis: >
      I lokalitetslista i regnearket 2026 (arket «Lok. per. 01.09.25» i
      2025, «Lok. per 01.09.24» i 2024) mangler 38097, eller den har
      annen MTB enn 780 t. Publiseres ikke regnearket innen 31.12.2026,
      kan påstanden ikke avgjøres.
    konfidens: 85
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-5"
    entitet: "de 9 lokalitetene med bare andre arter" # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "med_i_nokkelen"
    type: "verdi"
    verdi_min: "ute"
    verdi_max: "ute"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      9 lokaliteter består ledd 1, men har bare tillatelser uten laks,
      ørret og regnbueørret (torsk, kveite, røye, alger). Ingen av dem
      sto på lista per 01.09.2024 eller per 01.09.2025. Tillatelsene og
      artskodene er de samme i eierskapskroppene 02.09 og 02.11.2026.
    feil_hvis: >
      Minst én av de 9 (tabellen under) står i lokalitetslista i
      regnearket 2026 (arket «Lok. per. 01.09.25» i 2025, «Lok. per
      01.09.24» i 2024). Publiseres ikke regnearket innen 31.12.2026,
      kan påstanden ikke avgjøres.
    konfidens: 90
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-6"
    entitet: "de 10 delte lokalitetene og 33417 PERSFLUA" # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "deling"
    type: "verdi"
    verdi_min: "2025-brøken ± 0,001; PERSFLUA ikke delt"
    verdi_max: "2025-brøken ± 0,001; PERSFLUA ikke delt"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      10 lokaliteter ble delt mellom to kommuner både i 2024 og 2025,
      med samme brøker (største forskjell 4,3e-9). 33417 PERSFLUA ble
      delt mellom Ørland og Åfjord i 2024, men ikke i 2025, og
      kapasiteten er endret siden (6 240 til 3 120 t, versjon gyldig fra
      2026-04-12T22:00Z). To av de ti byttet registrert kommune mellom
      snapshotene 31.08 og 07.09.2026 (10181 og 19755). Delingen
      avgjøres av Fiskeridirektoratets kartfestede arealbeslag, som
      ingen kropp hos oss har.
    feil_hvis: >
      I lokalitetslista i regnearket 2026 (arket «Lok. per. 01.09.25» i
      2025, «Lok. per 01.09.24» i 2024) er minst én av de 10 ikke delt,
      eller delt med en brøk som avviker mer enn 0,001 fra 2025-brøken i
      tabellen under, eller 33417 PERSFLUA er delt. Publiseres ikke
      regnearket innen 31.12.2026, kan påstanden ikke avgjøres.
    konfidens: 70
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-7"
    entitet: "fylkeskommuner (8)"          # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "andel"
    type: "intervall"                      # FINNES IKKE i core/predictions.TYPER
    verdi_min: "forventet andel − 0,005 prosentpoeng, per fylkeskommune"
    verdi_max: "forventet andel + 0,005 prosentpoeng, per fylkeskommune"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      Fylkeskommunenes andel er MTB i fylket delt på samlet MTB, uten
      nyklarert-del. Forventet er A2 med Havbruksstasjonen. Påstanden
      faller med P2-3 (Troms 0,036 pp), med P2-5 (opptil 0,061 pp hvis
      alle de ni tas med) og med P2-4 (Rogaland 0,019 pp).
    feil_hvis: >
      For minst én fylkeskommune avviker BELØP / sum BELØP for
      fylkeskommunene mer enn 0,005 prosentpoeng fra forventet andel i
      tabellen under. Avgjøres mot regnearket eller pressemeldingen.
    konfidens: 55
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-8"
    entitet: "kommuner (143)"              # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "andel"
    type: "intervall"                      # FINNES IKKE i core/predictions.TYPER
    verdi_min: "forventet andel − 0,005 prosentpoeng, per kommune"
    verdi_max: "forventet andel + 0,005 prosentpoeng, per kommune"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      Andelen er MTB i kommunen delt på samlet MTB, uten nyklarert-del,
      som i pakke 1, men med Havbruksstasjonen og ti ganger smalere
      margin. Den faller hvis en av P2-3 til P2-6 faller, for de berørte
      kommunene: Tromsø 0,042 pp (P2-3), Strand 0,020 pp (P2-4), opptil
      0,081 pp (P2-5) og opptil 0,079 pp (P2-6). 0,005 prosentpoeng
      svarer til om lag 190 t i én kommune.
    feil_hvis: >
      For minst én av de 143 kommunene avviker TOTALT / sum TOTALT for
      kommunene mer enn 0,005 prosentpoeng fra forventet andel i
      tabellen under. Avgjøres mot regnearket eller pressemeldingen.
    konfidens: 35
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
  - id: "2026-11-09-9"
    entitet: "fylkeskommunene samlet"      # FORMATET BÆRER DET IKKE
    kilde: "havbruksfond"                  # FINNES IKKE i sources/
    felt: "andel_av_total"
    type: "intervall"                      # FINNES IKKE i core/predictions.TYPER
    verdi_min: "20 % − 0,001 prosentpoeng"
    verdi_max: "20 % + 0,001 prosentpoeng"
    vindu:
      fra: "2026-11-09"
      til: "2026-12-31"
    grunnlag: >
      Instruksen av 27.09.2024: «Utbetalingene fra Havbruksfondet
      fordeles med 80% til kommuner og 20% til fylkeskommuner, fra og
      med utbetalingsåret 2024.» I 2024 var fylkeskommunenes del
      939 080 537,80 av 4 695 402 689,00 kr (20,0000 %), i
      2025 281 984 600,00 av 1 409 923 000,00 kr (20,0000 %).
    feil_hvis: >
      Sum BELØP for fylkeskommunene delt på summen for kommuner og
      fylkeskommuner avviker mer enn 0,001 prosentpoeng fra 20 %.
      Avgjøres mot regnearket eller pressemeldingen.
    konfidens: 95
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
```

## Hvordan påstandene avgjøres for hånd

Ta Fiskeridirektoratets regneark for 2026 (A6 i MALING-HAVBRUKSFOND.md
arkiverer det). Har det samme form som 2025:

- **P2-1 og P2-2:** arket «Kommuner», kapasiteten per kommune (LOK_KOMNR),
  holdt mot MTB-kolonnen i tabellen «Kommunene» under, for gruppe U og E.
- **P2-3 til P2-6:** arket med lokalitetene per 01.09.2026. En delt lokalitet
  står der på én rad per kommune, med «Andel i %».
- **P2-7:** arket «Fylkeskommuner», BELØP delt på summen.
- **P2-8:** arket «Utbetalingsoversikt», TOTALT per KOMNR delt på summen for
  kommunene. Pressemeldingen har samme tabell med navn i stedet for nummer.
- **P2-9:** summen for fylkeskommunene delt på summen for alle.

Har regnearket en annen form, avgjøres påstanden etter innholdet: hva
Fiskeridirektoratet har brukt som MTB per kommune og per lokalitet.

**Hvorfor 1 t og 0,005 prosentpoeng:** tallene i regnearkene 2024 og 2025 har
ingen avrunding, og vekten treffer eksakt for alle uendrede lokaliteter. 1 t er
rom for flyttall, ikke for et avvik. 0,005 prosentpoeng er om lag 190 t i én
kommune. Det er terskler, ikke konfidensintervaller.

## Fylkeskommunene, 8

| fylkesnr | fylkeskommune | MTB forventet | andel forventet |
|---|---|---:|---:|
| 18 | Nordland | 791 956 | 20.7501% |
| 46 | Vestland | 787 759 | 20.6402% |
| 50 | Trøndelag | 713 229 | 18.6874% |
| 55 | Troms | 575 737 | 15.0850% |
| 56 | Finnmark | 386 541 | 10.1278% |
| 15 | Møre og Romsdal | 328 222 | 8.5998% |
| 11 | Rogaland | 200 490 | 5.2531% |
| 42 | Agder | 32 695 | 0.8566% |

## Kommunene, 143

| komnr | kommune | gruppe | MTB forventet | andel forventet |
|---|---|---|---:|---:|
| 5014 | FRØYA | E | 174 866 | 4.5817% |
| 5060 | NÆRØYSUND | E | 146 795 | 3.8462% |
| 5530 | SENJA | U | 130 604 | 3.4220% |
| 5603 | HAMMERFEST | E | 116 091 | 3.0417% |
| 5056 | HITRA | E | 102 950 | 2.6974% |
| 5534 | KARLSØY | E | 75 640 | 1.9819% |
| 4602 | KINN | E | 75 150 | 1.9690% |
| 1103 | STAVANGER | G | 72 548.2 | 1.9008% |
| 1573 | SMØLA | U | 72 540 | 1.9006% |
| 5601 | ALTA | U | 71 515 | 1.8738% |
| 5503 | HARSTAD | E | 63 385 | 1.6608% |
| 4617 | KVINNHERAD | U | 61 050 | 1.5996% |
| 5501 | TROMSØ | G | 59 063 | 1.5475% |
| 5058 | ÅFJORD | G | 58 020 | 1.5202% |
| 4626 | ØYGARDEN | U | 56 910 | 1.4911% |
| 1866 | HADSEL | G | 56 036.9 | 1.4682% |
| 1836 | RØDØY | G | 55 297.5 | 1.4489% |
| 5049 | FLATANGER | G | 54 040 | 1.4159% |
| 1848 | STEIGEN | U | 53 220 | 1.3944% |
| 5542 | SKJERVØY | E | 52 770 | 1.3826% |
| 4625 | AUSTEVOLL | E | 52 420 | 1.3735% |
| 1834 | LURØY | G | 50 972.4 | 1.3355% |
| 5055 | HEIM | G | 49 358.3 | 1.2932% |
| 4631 | ALVER | G | 49 315.5 | 1.2921% |
| 4613 | BØMLO | G | 46 560 | 1.2199% |
| 1875 | HAMARØY | U | 46 400 | 1.2157% |
| 1838 | GILDESKÅL | U | 45 891 | 1.2024% |
| 5514 | IBESTAD | U | 45 170 | 1.1835% |
| 4635 | GULEN | G | 44 570 | 1.1678% |
| 4636 | SOLUND | U | 43 860 | 1.1492% |
| 5618 | MÅSØY | U | 41 574 | 1.0893% |
| 4624 | BJØRNAFJORDEN | U | 39 690 | 1.0399% |
| 1818 | HERØY I NORDLAND | G | 39 597.6 | 1.0375% |
| 5614 | LOPPA | U | 36 239 | 0.9495% |
| 1811 | BINDAL | E | 35 380 | 0.9270% |
| 1870 | SORTLAND | G | 34 223.6 | 0.8967% |
| 5007 | NAMSOS | U | 34 060 | 0.8924% |
| 4616 | TYSNES | U | 33 480 | 0.8772% |
| 5052 | LEKA | U | 33 360 | 0.8741% |
| 5620 | NORDKAPP | U | 33 235 | 0.8708% |
| 4648 | BREMANGER | E | 31 200 | 0.8175% |
| 4645 | ASKVOLL | E | 30 420 | 0.7970% |
| 1827 | DØNNA | U | 29 340 | 0.7687% |
| 1813 | BRØNNØY | G | 28 563.9 | 0.7484% |
| 1580 | HARAM | G | 27 990.6 | 0.7334% |
| 1868 | ØKSNES | E | 27 439 | 0.7189% |
| 5546 | KVÆNANGEN | E | 27 000 | 0.7074% |
| 1837 | MELØY | U | 26 700 | 0.6996% |
| 4207 | FLEKKEFJORD | U | 26 520 | 0.6949% |
| 4637 | HYLLESTAD | U | 26 520 | 0.6949% |
| 5616 | HASVIK | U | 26 472 | 0.6936% |
| 1547 | AUKRA | E | 24 960 | 0.6540% |
| 1845 | SØRFOLD | U | 24 900 | 0.6524% |
| 1820 | ALSTAHAUG | G | 24 818.4 | 0.6503% |
| 1804 | BODØ | U | 24 766 | 0.6489% |
| 5528 | DYRØY | U | 24 575 | 0.6439% |
| 1576 | AURE | G | 23 401.7 | 0.6132% |
| 1865 | VÅGAN | G | 23 311.3 | 0.6108% |
| 5512 | TJELDSUND | U | 23 240 | 0.6089% |
| 1146 | TYSVÆR | U | 23 100 | 0.6052% |
| 5624 | LEBESBY | E | 23 025 | 0.6033% |
| 4638 | HØYANGER | U | 22 620 | 0.5927% |
| 4622 | KVAM | U | 22 319 | 0.5848% |
| 5057 | ØRLAND | G | 21 840 | 0.5722% |
| 1806 | NARVIK | U | 21 040 | 0.5513% |
| 1851 | LØDINGEN | U | 20 428 | 0.5352% |
| 1506 | MOLDE | E | 19 790 | 0.5185% |
| 5059 | ORKLAND | U | 19 220 | 0.5036% |
| 4615 | FITJAR | E | 18 740 | 0.4910% |
| 5020 | OSEN | U | 18 720 | 0.4905% |
| 5516 | GRATANGEN | U | 18 120 | 0.4748% |
| 1505 | KRISTIANSUND | U | 17 940 | 0.4700% |
| 4612 | SVEIO | U | 17 940 | 0.4700% |
| 4630 | OSTERØY | U | 17 940 | 0.4700% |
| 5510 | KVÆFJORD | E | 17 870 | 0.4682% |
| 1554 | AVERØY | U | 17 590 | 0.4609% |
| 1867 | BØ I NORDLAND | G | 17 176.4 | 0.4500% |
| 4618 | ULLENSVANG | U | 17 160 | 0.4496% |
| 5605 | SØR-VARANGER | U | 16 260 | 0.4260% |
| 1160 | VINDAFJORD | U | 16 080 | 0.4213% |
| 4649 | STAD | G | 16 080 | 0.4213% |
| 1520 | ØRSTA | E | 14 820 | 0.3883% |
| 1535 | VESTNES | U | 14 040 | 0.3679% |
| 1860 | VESTVÅGØY | U | 13 560 | 0.3553% |
| 4646 | FJALER | E | 13 260 | 0.3474% |
| 1133 | HJELMELAND | U | 13 140 | 0.3443% |
| 1145 | BOKN | E | 12 880 | 0.3375% |
| 1134 | SULDAL | U | 12 580 | 0.3296% |
| 1577 | VOLDA | U | 12 480 | 0.3270% |
| 1816 | VEVELSTAD | U | 12 480 | 0.3270% |
| 5632 | BÅTSFJORD | U | 11 570 | 0.3031% |
| 1812 | SØMNA | G | 11 395.3 | 0.2986% |
| 4634 | MASFJORDEN | U | 11 020 | 0.2887% |
| 1511 | VANYLVEN | U | 10 920 | 0.2861% |
| 5636 | UNJÁRGA - NESSEBY | U | 10 560 | 0.2767% |
| 1828 | NESNA | U | 10 140 | 0.2657% |
| 1853 | EVENES | E | 9 600 | 0.2515% |
| 5522 | SALANGEN | U | 9 600 | 0.2515% |
| 1106 | HAUGESUND | U | 9 540 | 0.2500% |
| 1108 | SANDNES | U | 9 410 | 0.2466% |
| 1579 | HUSTADVIKA | E | 9 360 | 0.2452% |
| 1840 | SALTDAL | U | 9 119 | 0.2389% |
| 4611 | ETNE | U | 9 010 | 0.2361% |
| 5518 | LOABÁK - LAVANGEN | U | 9 000 | 0.2358% |
| 1841 | FAUSKE | U | 8 596 | 0.2252% |
| 1149 | KARMØY | U | 8 580 | 0.2248% |
| 1144 | KVITSØY | U | 8 280 | 0.2169% |
| 1815 | VEGA | U | 7 620 | 0.1997% |
| 1560 | TINGVOLL | U | 7 520 | 0.1970% |
| 1130 | STRAND | G | 7 491.7 | 0.1963% |
| 4632 | AUSTRHEIM | G | 7 124.7 | 0.1867% |
| 5544 | NORDREISA | U | 7 100 | 0.1860% |
| 1557 | GJEMNES | G | 7 020 | 0.1839% |
| 1578 | FJORD | E | 7 020 | 0.1839% |
| 1508 | ÅLESUND | E | 6 720 | 0.1761% |
| 1532 | GISKE | G | 6 329.4 | 0.1658% |
| 1525 | STRANDA | U | 6 240 | 0.1635% |
| 1833 | RANA | U | 6 240 | 0.1635% |
| 4627 | ASKØY | U | 6 240 | 0.1635% |
| 1514 | SANDE I MØRE OG ROMSDAL | G | 5 724.1 | 0.1500% |
| 1151 | UTSIRA | U | 5 460 | 0.1431% |
| 1539 | RAUMA | U | 5 460 | 0.1431% |
| 5536 | LYNGEN | U | 5 400 | 0.1415% |
| 1822 | LEIRFJORD | U | 4 680 | 0.1226% |
| 4614 | STORD | U | 4 680 | 0.1226% |
| 1515 | HERØY I MØRE OG ROMSDAL | G | 4 116 | 0.1078% |
| 4650 | GLOPPEN | U | 3 900 | 0.1022% |
| 1835 | TRÆNA | U | 3 600 | 0.0943% |
| 5526 | SØRREISA | U | 3 600 | 0.0943% |
| 5540 | GÁIVUOTNA - KÅFJORD - KAIVUONO | U | 3 600 | 0.0943% |
| 1871 | ANDØY | U | 3 184 | 0.0834% |
| 1528 | SYKKYLVEN | U | 3 120 | 0.0817% |
| 1824 | VEFSN | U | 3 120 | 0.0817% |
| 1859 | FLAKSTAD | U | 3 120 | 0.0817% |
| 4623 | SAMNANGER | U | 3 120 | 0.0817% |
| 4633 | FEDJE | U | 3 120 | 0.0817% |
| 1516 | ULSTEIN | U | 2 340 | 0.0613% |
| 4206 | FARSUND | U | 2 340 | 0.0613% |
| 4225 | LYNGDAL | U | 2 340 | 0.0613% |
| 4628 | VAKSDAL | U | 2 340 | 0.0613% |
| 4215 | LILLESAND | U | 1 495 | 0.0392% |
| 1122 | GJESDAL | U | 1 400 | 0.0367% |
| 1566 | SURNADAL | U | 780 | 0.0204% |

## Lokalitetene i P2-3 til P2-6

| påstand | lokalitet | navn | kommune | MTB | forventet |
|---|---|---|---|---:|---|
| P2-3 | 10768 | INDRE KÅRVIK I | 5501 | 650 | med |
| P2-3 | 15236 | SKULGAMBUKT | 5501 | 975 | med |
| P2-4 | 38097 | HØGÅS | 1130 | 780 | med |
| P2-5 | 11411 | LILLEELV | 1866 | 780 | ute |
| P2-5 | 11737 | SKORPA | 4635 | 150 | ute |
| P2-5 | 12233 | STOKKENESET | 4649 | 1 560 | ute |
| P2-5 | 12634 | INNERNESSET | 5049 | 300 | ute |
| P2-5 | 16797 | FOLDERØYHOLMEN | 4613 | 1 560 | ute |
| P2-5 | 18595 | YTTERHAVNA | 1870 | 325 | ute |
| P2-5 | 22296 | GRØNSET | 1557 | 3 120 | ute |
| P2-5 | 26876 | LANGNESET | 1866 | 780 | ute |
| P2-5 | 29417 | YTRE VASSHOLMEN | 1818 | 780 | ute |
| P2-6 | 10181 | OKSEBÅSEN V | 1532 / 1580 | 4 680 | delt: 1532 0.352441, 1580 0.647566 |
| P2-6 | 10229 | FÆTTEN | 1576 / 5055 | 4 680 | delt: 1576 0.000363, 5055 0.999640 |
| P2-6 | 11015 | BRATTHOLMEN | 1818 / 1820 | 4 680 | delt: 1818 0.632599, 1820 0.367389 |
| P2-6 | 11665 | JIBBERSHOLMANE | 4631 / 4632 | 3 620 | delt: 4631 0.971121, 4632 0.028909 |
| P2-6 | 13246 | VOLDNES | 1514 / 1515 | 5 460 | delt: 1514 0.389022, 1515 0.610981 |
| P2-6 | 13527 | FINNKJERKA | 1865 / 1866 | 5 460 | delt: 1865 0.055555, 1866 0.944479 |
| P2-6 | 14679 | HELLFJORDEN | 1867 / 1870 | 3 120 | delt: 1867 0.646285, 1870 0.353718 |
| P2-6 | 19755 | KLUBBEN | 1812 / 1813 | 2 340 | delt: 1812 0.331321, 1813 0.668753 |
| P2-6 | 33797 | HIDLEKJERRINGA | 1103 / 1130 | 3 600 | delt: 1103 0.002278, 1130 0.997689 |
| P2-6 | 45002 | Korsvika | 1834 / 1836 | 5 460 | delt: 1834 0.993121, 1836 0.006875 |
| P2-6 | 33417 | PERSFLUA | 5057 | 3 120 | ikke delt |

Gruppe U: 1106, 1108, 1122, 1133, 1134, 1144, 1146, 1149, 1151, 1160, 1505, 1511, 1516, 1525, 1528, 1535, 1539, 1554, 1560, 1566, 1573, 1577, 1804, 1806, 1815, 1816, 1822, 1824, 1827, 1828, 1833, 1835, 1837, 1838, 1840, 1841, 1845, 1848, 1851, 1859, 1860, 1871, 1875, 4206, 4207, 4215, 4225, 4611, 4612, 4614, 4616, 4617, 4618, 4622, 4623, 4624, 4626, 4627, 4628, 4630, 4633, 4634, 4636, 4637, 4638, 4650, 5007, 5020, 5052, 5059, 5512, 5514, 5516, 5518, 5522, 5526, 5528, 5530, 5536, 5540, 5544, 5601, 5605, 5614, 5616, 5618, 5620, 5632, 5636.

Gruppe E: 1145, 1506, 1508, 1520, 1547, 1578, 1579, 1811, 1853, 1868, 4602, 4615, 4625, 4645, 4646, 4648, 5014, 5056, 5060, 5503, 5510, 5534, 5542, 5546, 5603, 5624.

Gruppe G: 1103, 1130, 1514, 1515, 1532, 1557, 1576, 1580, 1812, 1813, 1818, 1820, 1834, 1836, 1865, 1866, 1867, 1870, 4613, 4631, 4632, 4635, 4649, 5049, 5055, 5057, 5058, 5501.
