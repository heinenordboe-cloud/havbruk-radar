# Trefflista for maskinanslagene

Bare forseglede uker teller. Backtesten står nederst, adskilt og merket
BACKTEST, og telles ikke. Hva som er registrert, står i
`FORHANDSREGISTRERING.md`; hver rad står i `fasiten.json`.

Lusetall til og med uke 2026-W42 (2026-10-12).

## K2, brakklegginger de neste fire ukene — hovedtype

| forseglede uker | avgjorte uker | avgjorte rader | MAE modell | MAE a (siste verdi) | MAE b (i fjor) | SS a | SS b | dom |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | – | – | – | – | – | for tidlig: 0 av 12 uker avgjort |

| uke | forseglet (UTC) | åpningsdato | status | MAE modell | MAE a | MAE b |
|---|---|---|---|---|---|---|
| 2026-W46 | 2026-11-10T20:49:02Z | 2026-12-28 | åpen | – | – | – |

## K6, snitt voksne hunnlus om fire uker — PRØVETYPE

Prøvetype: forseglet og skåret som K2, men ikke et hovedresultat.

| forseglede uker | avgjorte uker | avgjorte rader | MAE modell | MAE a (siste verdi) | MAE b (i fjor) | SS a | SS b | dom |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | – | – | – | – | – | for tidlig: 0 av 12 uker avgjort |

| uke | forseglet (UTC) | åpningsdato | status | MAE modell | MAE a | MAE b |
|---|---|---|---|---|---|---|
| 2026-W46 | 2026-11-10T20:49:02Z | 2027-01-04 | åpen | – | – | – |

## BACKTEST — teller ikke i trefflista

R6, MALING-ANSLAG.md 09.11.2026 (havbruk-analyse 7d258f7, data havbruk-radar-data 1f82890). Hva modellen VILLE gjort i 2023–2026.

| type | utstedelser | rader | MAE modell | MAE a | MAE b | SS a [95 %] | SS b [95 %] | P4 | dom |
|---|---|---|---|---|---|---|---|---|---|
| K2 (hovedtype) | 2023-01-02 … 2026-09-14 (194) | 2522 | 1.3066 | 1.7958 | 1.6475 | 0.272 [0.241, 0.308] | 0.207 [0.162, 0.258] | 0.87 | slår referansen |
| K6 (PRØVETYPE) | 2022-12-05 … 2026-09-07 (197) | 2300 | 0.0502 | 0.0670 | 0.0620 | 0.252 [0.183, 0.340] | 0.190 [0.064, 0.299] | 0.56 | slår referansen |
