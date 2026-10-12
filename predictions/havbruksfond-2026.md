# Anslag: fordelingen fra Havbruksfondet 2026

Skrevet 12.10.2026, før fordelingen er kjent. I 2024 kom den 21.10, i
2025 10.11.

Fila er `.md` og ikke `.yml`, så `forsegl.py` og
`core/predictions.py` hopper over den: formatet bærer ikke anslaget
(MALING-HAVBRUKSFOND.md A5, «Formatet kan ikke bære det»). Det er
committen som forankrer det. Fila røres ikke etter at den er pushet;
utfallet skrives i en ny fil.

**Referansetabellen** er A2 i `docs/MALING-HAVBRUKSFOND.md` slik den står
i commit **a4608a3** («A2 rettet: vekten er max(kapasitet,
kapasitet_midlertidig)»). Tabellene under er skrevet ut av den commiten.
Andelen er prosent med fire desimaler, som i A2, og den er lik for
snapshotene 31.08 og 07.09.2026.

**Konfidens: 75 %.**

## Anslaget

```yaml
prediksjoner:
  - id: "2026-10-12-1"
    entitet: "kommuner"            # FORMATET BÆRER DET IKKE: gjelder alle 143
    kilde: "havbruksfond"          # FINNES IKKE i sources/ (se over)
    felt: "andel"
    type: "intervall"              # FINNES IKKE i core/predictions.TYPER
    verdi_min: "A2-andel − 0,05 prosentpoeng, per kommune"
    verdi_max: "A2-andel + 0,05 prosentpoeng, per kommune"
    vindu:
      fra: "2026-10-12"
      til: "2026-12-31"
    grunnlag: >
      Utbetalingen 2026 er i et partallsår. Etter instruksen av 27.09.2024
      fordeles da hele kommunenes andel etter klarert lokalitets-MTB per
      01.09.2026 kl. 12.00, uten nyklarert-del. A2 har regnet ut denne
      andelen fra registeret 31.08.2026 og 07.09.2026, og de to
      snapshotene er like. Filteret og vekten (max av kapasitet og
      midlertidig kapasitet) er holdt mot Fiskeridirektoratets egen
      lokalitetsliste for 2025. Der stemmer vekten for 954 av 954
      lokaliteter som ikke er endret siden. Andelen per kommune er da
      MTB i kommunen delt på samlet MTB, og den skal treffe
      Fiskeridirektoratets tall med mindre de har brukt en lokalitet vi
      holder ute eller utelatt en vi tar med.
    feil_hvis: >
      Én av disse fire er nok til at påstanden faller.
      (1) Tabellen «Utbetalinger fra Havbruksfondet 2026» har en kolonne
      ANDEL NYKLARERT med beløp over 0 for noen kommune. Da er
      partallsregelen ikke fulgt.
      (2) Kommunesettet er ikke de samme 143 kommunenumrene som i A2.
      (3) For minst én kommune avviker TOTALT / sum TOTALT for kommunene
      mer enn 0,05 prosentpoeng fra A2.
      (4) For minst én fylkeskommune avviker andelen mer enn 0,05
      prosentpoeng fra A2.
      Mekanismen er feil hvis Fiskeridirektoratets lokalitetsliste per
      01.09.2026 tar med eller utelater andre lokaliteter enn filteret
      gjør. To kjente kandidater er Havbruksstasjonen i Tromsø (1 625 t)
      og HØGÅS (780 t).
    konfidens: 75
    utfall: ""
    utfall_dato: ""
    utfall_kilde: ""
    utfall_note: ""
```

**Hvordan anslaget avgjøres for hånd mot 2025-formatet:** ta
regnearket for 2026 (A6 arkiverer det), arket «Utbetalingsoversikt». Del
TOTALT per KOMNR på summen for kommunene, og del BELØP per FYLKESNR i
arket «Fylkeskommuner» på summen for fylkeskommunene. Hold tallene mot
A2-tabellene, kommune for kommune. Pressemeldingen har samme tabell med
kommunenavn i stedet for nummer. A3 viser at de to stemmer overens.

**Hvorfor ±0,05 prosentpoeng:** den største kjente usikkerheten er
Havbruksstasjonen i Tromsø. Den gir 0,043 prosentpoeng for Tromsø hvis
Fiskeridirektoratet tar lokalitetene med igjen. Alle andre kjente
forskjeller er mindre. Det er en terskel, ikke et konfidensintervall.

## Fylkeskommunene, 8

| fylkesnr | fylkeskommune | andel |
|---|---|---:|
| 18 | Nordland | 20.7590% |
| 46 | Vestland | 20.6490% |
| 50 | Trøndelag | 18.6954% |
| 55 | Troms | 15.0488% |
| 56 | Finnmark | 10.1321% |
| 15 | Møre og Romsdal | 8.6034% |
| 11 | Rogaland | 5.2553% |
| 42 | Agder | 0.8570% |

## Kommunene, 143

| komnr | kommune | andel |
|---|---|---:|
| 5014 | FRØYA | 4.5836% |
| 5060 | NÆRØYSUND | 3.8478% |
| 5530 | SENJA | 3.4234% |
| 5603 | HAMMERFEST | 3.0430% |
| 5056 | HITRA | 2.6986% |
| 5534 | KARLSØY | 1.9827% |
| 4602 | KINN | 1.9699% |
| 1103 | STAVANGER | 1.9017% |
| 1573 | SMØLA | 1.9014% |
| 5601 | ALTA | 1.8746% |
| 5503 | HARSTAD | 1.6615% |
| 4617 | KVINNHERAD | 1.6003% |
| 5058 | ÅFJORD | 1.5208% |
| 5501 | TROMSØ | 1.5056% |
| 4626 | ØYGARDEN | 1.4917% |
| 1866 | HADSEL | 1.4689% |
| 1836 | RØDØY | 1.4495% |
| 5049 | FLATANGER | 1.4165% |
| 1848 | STEIGEN | 1.3950% |
| 5542 | SKJERVØY | 1.3832% |
| 4625 | AUSTEVOLL | 1.3740% |
| 1834 | LURØY | 1.3361% |
| 5055 | HEIM | 1.2938% |
| 4631 | ALVER | 1.2927% |
| 4613 | BØMLO | 1.2204% |
| 1875 | HAMARØY | 1.2163% |
| 1838 | GILDESKÅL | 1.2029% |
| 5514 | IBESTAD | 1.1840% |
| 4635 | GULEN | 1.1683% |
| 4636 | SOLUND | 1.1497% |
| 5618 | MÅSØY | 1.0897% |
| 4624 | BJØRNAFJORDEN | 1.0404% |
| 1818 | HERØY I NORDLAND | 1.0379% |
| 5614 | LOPPA | 0.9499% |
| 1811 | BINDAL | 0.9274% |
| 1870 | SORTLAND | 0.8971% |
| 5007 | NAMSOS | 0.8928% |
| 4616 | TYSNES | 0.8776% |
| 5052 | LEKA | 0.8744% |
| 5620 | NORDKAPP | 0.8712% |
| 4648 | BREMANGER | 0.8178% |
| 4645 | ASKVOLL | 0.7974% |
| 1827 | DØNNA | 0.7691% |
| 1813 | BRØNNØY | 0.7487% |
| 1580 | HARAM | 0.7337% |
| 1868 | ØKSNES | 0.7192% |
| 5546 | KVÆNANGEN | 0.7077% |
| 1837 | MELØY | 0.6999% |
| 4207 | FLEKKEFJORD | 0.6951% |
| 4637 | HYLLESTAD | 0.6951% |
| 5616 | HASVIK | 0.6939% |
| 1547 | AUKRA | 0.6543% |
| 1845 | SØRFOLD | 0.6527% |
| 1820 | ALSTAHAUG | 0.6505% |
| 1804 | BODØ | 0.6492% |
| 5528 | DYRØY | 0.6442% |
| 1576 | AURE | 0.6134% |
| 1865 | VÅGAN | 0.6110% |
| 5512 | TJELDSUND | 0.6092% |
| 1146 | TYSVÆR | 0.6055% |
| 5624 | LEBESBY | 0.6035% |
| 4638 | HØYANGER | 0.5929% |
| 4622 | KVAM | 0.5850% |
| 5057 | ØRLAND | 0.5725% |
| 1806 | NARVIK | 0.5515% |
| 1851 | LØDINGEN | 0.5355% |
| 1506 | MOLDE | 0.5187% |
| 5059 | ORKLAND | 0.5038% |
| 4615 | FITJAR | 0.4912% |
| 5020 | OSEN | 0.4907% |
| 5516 | GRATANGEN | 0.4750% |
| 4612 | SVEIO | 0.4702% |
| 4630 | OSTERØY | 0.4702% |
| 1505 | KRISTIANSUND | 0.4702% |
| 5510 | KVÆFJORD | 0.4684% |
| 1554 | AVERØY | 0.4611% |
| 1867 | BØ I NORDLAND | 0.4502% |
| 4618 | ULLENSVANG | 0.4498% |
| 5605 | SØR-VARANGER | 0.4262% |
| 1160 | VINDAFJORD | 0.4215% |
| 4649 | STAD | 0.4215% |
| 1520 | ØRSTA | 0.3885% |
| 1535 | VESTNES | 0.3680% |
| 1860 | VESTVÅGØY | 0.3554% |
| 4646 | FJALER | 0.3476% |
| 1133 | HJELMELAND | 0.3444% |
| 1145 | BOKN | 0.3376% |
| 1134 | SULDAL | 0.3298% |
| 1577 | VOLDA | 0.3271% |
| 1816 | VEVELSTAD | 0.3271% |
| 5632 | BÅTSFJORD | 0.3033% |
| 1812 | SØMNA | 0.2987% |
| 4634 | MASFJORDEN | 0.2889% |
| 1511 | VANYLVEN | 0.2862% |
| 5636 | UNJÁRGA - NESSEBY | 0.2768% |
| 1828 | NESNA | 0.2658% |
| 1853 | EVENES | 0.2516% |
| 5522 | SALANGEN | 0.2516% |
| 1106 | HAUGESUND | 0.2501% |
| 1108 | SANDNES | 0.2467% |
| 1579 | HUSTADVIKA | 0.2453% |
| 1840 | SALTDAL | 0.2390% |
| 4611 | ETNE | 0.2362% |
| 5518 | LOABÁK - LAVANGEN | 0.2359% |
| 1841 | FAUSKE | 0.2253% |
| 1149 | KARMØY | 0.2249% |
| 1144 | KVITSØY | 0.2170% |
| 1815 | VEGA | 0.1997% |
| 1560 | TINGVOLL | 0.1971% |
| 1130 | STRAND | 0.1964% |
| 4632 | AUSTRHEIM | 0.1868% |
| 5544 | NORDREISA | 0.1861% |
| 1557 | GJEMNES | 0.1840% |
| 1578 | FJORD | 0.1840% |
| 1508 | ÅLESUND | 0.1761% |
| 1532 | GISKE | 0.1659% |
| 4627 | ASKØY | 0.1636% |
| 1833 | RANA | 0.1636% |
| 1525 | STRANDA | 0.1636% |
| 1514 | SANDE I MØRE OG ROMSDAL | 0.1500% |
| 1151 | UTSIRA | 0.1431% |
| 1539 | RAUMA | 0.1431% |
| 5536 | LYNGEN | 0.1415% |
| 4614 | STORD | 0.1227% |
| 1822 | LEIRFJORD | 0.1227% |
| 1515 | HERØY I MØRE OG ROMSDAL | 0.1079% |
| 4650 | GLOPPEN | 0.1022% |
| 1835 | TRÆNA | 0.0944% |
| 5526 | SØRREISA | 0.0944% |
| 5540 | GÁIVUOTNA - KÅFJORD - KAIVUONO | 0.0944% |
| 1871 | ANDØY | 0.0835% |
| 1859 | FLAKSTAD | 0.0818% |
| 4623 | SAMNANGER | 0.0818% |
| 4633 | FEDJE | 0.0818% |
| 1528 | SYKKYLVEN | 0.0818% |
| 1824 | VEFSN | 0.0818% |
| 1516 | ULSTEIN | 0.0613% |
| 4206 | FARSUND | 0.0613% |
| 4225 | LYNGDAL | 0.0613% |
| 4628 | VAKSDAL | 0.0613% |
| 4215 | LILLESAND | 0.0392% |
| 1122 | GJESDAL | 0.0367% |
| 1566 | SURNADAL | 0.0204% |
