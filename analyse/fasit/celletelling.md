# Celletelling: trafikklysvedtak

Hvilke (runde, produksjonsområde)-celler `sources/trafikklysvedtak.py`
faktisk emitterer, kjørt gjennom `parse()` over de arkiverte
forskriftskroppene. Bare tall — ingen tolkning, ingen prosent.

Generert av `analyse/celletelling.py`.

## Runder

- Forskrifter i `FORSKRIFTER`: **5**
- Distinkte runder de uttaler seg om: **5** — 2018, 2020, 2022, 2024, 2026
- Teoretisk maksimum: 5 runder x 13 PO = **65** celler

## Emittert

- Emisjoner (forskrift, runde, PO): **63**
- Distinkte (runde, PO): **46** av 65
- Celler uten emisjon: **19**

## Hjemmelstype, på distinkte celler

| lesemåte | celler |
| --- | ---: |
| bare `kapittelhjemmel` | 17 |
| bare øvrige (`ordrett`, `kapitteloverskrift`) | 29 |
| både `kapittelhjemmel` og øvrige | 0 |
| **sum** | **46** |

## Per runde

| runde | emittert av 13 | PO uten emisjon |
| --- | ---: | --- |
| 2018 | 8 | PO2, PO3, PO4, PO5, PO6 |
| 2020 | 12 | PO10 |
| 2022 | 11 | PO2, PO7 |
| 2024 | 9 | PO2, PO6, PO7, PO8 |
| 2026 | 6 | PO2, PO6, PO7, PO8, PO9, PO10, PO11 |

## Per runde og lesemåte — hvordan cellen kan leses

`ordrett` og `kapitteloverskrift` betyr at et FARGEORD står i
kroppen; `kapittelhjemmel` at det ikke gjør det og fargen er
utledet av hvilket kapittel området står under. `ingen` er hull.

| runde | ordrett | ordrett+overskrift | bare overskrift | kapittelhjemmel | blandet m/hjemmel | ingen |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 0 | 0 | 0 | 8 | 0 | 5 |
| 2020 | 1 | 2 | 0 | 9 | 0 | 1 |
| 2022 | 11 | 0 | 0 | 0 | 0 | 2 |
| 2024 | 9 | 0 | 0 | 0 | 0 | 4 |
| 2026 | 6 | 0 | 0 | 0 | 0 | 7 |
| **sum** | **27** | **2** | **0** | **17** | **0** | **19** |

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
| FOR-2026-08-20-1764 | 2020 | PO3, PO4, PO5 | 3 |
| FOR-2026-08-20-1764 | 2022 | PO3, PO4, PO5 | 3 |
| FOR-2026-08-20-1764 | 2024 | PO3, PO4, PO5 | 3 |
| FOR-2026-08-20-1764 | 2026 | PO1, PO3, PO4, PO5, PO12, PO13 | 6 |

## Celler med mer enn én lesemåte

| runde | PO | lesemåter, i emisjonsrekkefølge |
| --- | --- | --- |
| 2020 | PO4 | kapitteloverskrift, ordrett, ordrett, ordrett |
| 2020 | PO5 | kapitteloverskrift, ordrett, ordrett, ordrett |

