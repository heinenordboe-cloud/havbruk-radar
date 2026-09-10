# Celletelling: trafikklysvedtak

Hvilke (runde, produksjonsområde)-celler `sources/trafikklysvedtak.py`
faktisk emitterer, kjørt gjennom `parse()` over de arkiverte
forskriftskroppene. Bare tall — ingen tolkning, ingen prosent.

Generert av `analyse/celletelling.py`.

## Runder

- Forskrifter i `FORSKRIFTER`: **4**
- Distinkte runder de uttaler seg om: **4** — 2018, 2020, 2022, 2024
- Teoretisk maksimum: 4 runder x 13 PO = **52** celler

## Emittert

- Emisjoner (forskrift, runde, PO): **48**
- Distinkte (runde, PO): **40** av 52
- Celler uten emisjon: **12**

## Hjemmelstype, på distinkte celler

| lesemåte | celler |
| --- | ---: |
| bare `kapittelhjemmel` | 17 |
| bare øvrige (`ordrett`, `kapitteloverskrift`) | 23 |
| både `kapittelhjemmel` og øvrige | 0 |
| **sum** | **40** |

## Per runde

| runde | emittert av 13 | PO uten emisjon |
| --- | ---: | --- |
| 2018 | 8 | PO2, PO3, PO4, PO5, PO6 |
| 2020 | 12 | PO10 |
| 2022 | 11 | PO2, PO7 |
| 2024 | 9 | PO2, PO6, PO7, PO8 |

## Per forskrift (grunnlaget for unionen over)

| forskrift | runde | PO emittert | antall |
| --- | ---: | --- | ---: |
| FOR-2017-12-20-2397 | 2018 | PO1, PO7, PO8, PO9, PO10, PO11, PO12, PO13 | 8 |
| FOR-2020-02-04-105 | 2020 | PO1, PO2, PO4, PO5, PO6, PO7, PO8, PO9, PO11, PO12, PO13 | 11 |
| FOR-2022-06-07-972 | 2020 | PO3, PO4, PO5 | 3 |
| FOR-2022-06-07-972 | 2022 | PO1, PO3, PO4, PO5, PO6, PO8, PO9, PO10, PO11, PO12, PO13 | 11 |
| FOR-2024-03-22-515 | 2020 | PO3, PO4, PO5 | 3 |
| FOR-2024-03-22-515 | 2022 | PO3, PO4, PO5 | 3 |
| FOR-2024-03-22-515 | 2024 | PO1, PO3, PO4, PO5, PO9, PO10, PO11, PO12, PO13 | 9 |

## Celler med mer enn én lesemåte

| runde | PO | lesemåter, i emisjonsrekkefølge |
| --- | --- | --- |
| 2020 | PO4 | kapitteloverskrift, ordrett, ordrett |
| 2020 | PO5 | kapitteloverskrift, ordrett, ordrett |

