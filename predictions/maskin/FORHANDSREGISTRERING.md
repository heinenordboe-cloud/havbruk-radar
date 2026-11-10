# Forhåndsregistrering: forseglede maskinanslag per produksjonsområde

Skrevet 10.11.2026 ca. 20:10 UTC, før første anslag er laget. Kode
`havbruk-radar` f8996e3, data `havbruk-radar-data` 8a50e4c. Fila stemples
med OpenTimestamps (`FORHANDSREGISTRERING.md.ots`) og committes før
`anslag.py` finnes og før noe ukeanslag er regnet ut.

Grunnlaget er backtesten R6 fra 09.11.2026 i det private
`havbruk-analyse` (`revisjon/2026-11-09-anslag-backtest/`,
forhåndsregistrert i 85eed2c og målt i 7d258f7). Tallene fra R6 står
under der de brukes. Hvilke typer som forsegles, bestemte Heine
10.11.2026.

Bare PO-nivå: ingen lokaliteter og ingen selskaper i denne mappa.

## To typer, ikke flere

| type | klasse | anslag per PO, utstedt mandag i uke T | mål | referanse a: siste verdi | referanse b: samme periode i fjor |
|---|---|---|---|---|---|
| K2 | hovedtype | antall brakklegginger | uke T … T+3 | antall i uke T−7 … T−4 | antall i uke T−52 … T−49 |
| K6 | PRØVETYPE | snitt voksne hunnlus | uke T+4 | snitt i uke T−4 | snitt i uke T+4−52 |

Ett anslag per produksjonsområde (PO 1–13), per type og uke. Lokaliteter
uten PO anslås ikke.

**K2 er hovedtypen.** I R6 slo den begge referansene: SS 0,272 [0,241;
0,308] mot siste verdi og 0,207 [0,162; 0,258] mot i fjor, i alle 13 PO
og i 87 % av fire-ukers vinduer (P4 0,87). Den var den eneste av sju som
oppfylte hele den registrerte regelen.

**K6 er en prøvetype, og den er merket PRØVETYPE overalt:** i hver
ukefil, i `fasiten.json` og i trefflista. Den forsegles og skåres som K2,
men resultatet er ikke et hovedresultat. I R6 slo K6 begge referansene
over hele testen (SS 0,252 [0,183; 0,340] og 0,190 [0,064; 0,299], 12 av
13 PO), men vant bare 56 % av fire-ukers vinduer (P4 0,56), under den
registrerte grensa på 0,6.

## Hvorfor K1 og K7 ikke er med

**K1, andel lokaliteter over lusegrensa om fire uker per PO, slo ikke den
naive referansen i R6.** Mot siste verdi var MAE 0,0250 for modellen og
0,0252 for referansen: SS 0,007, altså +0,7 %, og 95 %-intervallet
[−0,103; 0,093] krysser null. Mot samme uke i fjor var SS 0,143, men
intervallet [−0,007; 0,248] krysser også null. Modellen slo begge i 5 av
13 PO og i 28 % av fire-ukers vinduer. Som nåvarsel (mål = utstedelsesuka)
tapte den mot siste verdi, med hele intervallet under null: SS −0,061
[−0,138; −0,003]. Utfallet var null i 63 % av PO-ukene. R6s dom etter den
registrerte regelen: «uavklart» fire uker fram, «slår ikke» som nåvarsel.

**K7, antall nye PD-lokaliteter de neste fire ukene per PO, tapte mot
siste verdi under MAE.** MAE var 0,2084 for modellen og 0,1685 for
referansen: SS −0,237 [−0,660; −0,043]. 90 % av PO-vinduene hadde null,
og MAE belønner den som sier null. R6s dom: «slår ikke».

K1 og K7 måles videre internt. De kan registreres senere, i en ny
forhåndsregistrering, hvis de slår referansen. K3 (utsett), K4
(eierskifter) og K5 (sjøtemperatur) er ute: K3 var uavklart mot i fjor
(SS 0,051 [−0,067; 0,127]), og utfallet står i våre data først etter ~17
uker. K4 ble stoppet av S1 (56 % av overføringene siden 2023 uten
PO-kobling). K5 var uavklart mot i fjor (SS 0,111 [−0,006; 0,221]).

## Hva som teller

**Bare forseglede uker teller i trefflista.** En uke er forseglet når
`predictions/maskin/<år>-<uke>.yml` har en `.ots`-fil ved siden av seg,
og summen OpenTimestamps-fila er stemplet for, er sha256 av ukefila.
Ukefila røres aldri etter stempelet. Utfallet skrives i `fasiten.json`,
aldri i ukefila.

**Frist:** anslaget for uke T stemples før uke T er omme (søndag 24:00
UTC). En uke som ikke er stemplet innen fristen, er tapt. Den lages ikke i
ettertid, og den fylles ikke inn med backtest eller med et anslag regnet
ut senere. Beviset for tidspunktet er blokken i det oppgraderte
stempelet; blokktiden er en øvre grense for når fila fantes.

**Backtest står adskilt**, merket BACKTEST, og telles aldri sammen med de
forseglede ukene.

**Ingen type legges til eller fjernes** etter første forsegling uten en
ny forhåndsregistrering, stemplet og committet før den første uka den
gjelder for. Det samme gjelder modellen, referansene, målet og skåren
under.

`fasiten.json` har én rad per forseglet anslag: id, type, PO,
forseglingstidspunkt, sha256 av ukefila, åpningsdato, og utfall og skår
når de er kjent.

## Modellen er R6s, uendret

Anslagene regnes ut av R6s skript, importert som modul:
`analyse/anslag/anslag_backtest.py`, sha256
`0b8f7eec13499506604fb628a3a0850d07deed6283ea2d17f99eb633e221d2d7`, lik
byte for byte fila som laget backtesten. `anslag.py` kaller funksjonene
derfra og velger bare hvilken uke de evalueres for. Den regner ikke ut
noe av modellen selv.

Prøvd 10.11.2026 før denne fila ble skrevet: med data 8a50e4c,
PO-koblingen fra 02.11 og R6s siste uke (2026-10-05) gir modulen R6s tall
eksakt. Hasardtabellen er lik, MAE for K2 er 1,3066 / 1,7958 / 1,6475
(modell / a / b), for K6 0,0502 / 0,0670 / 0,0620, og uke 2026-10-05 har
12 brakklegginger (R6 F2.9). Ingen ukes anslag var regnet ut.

- **K2, M-hasard.** For hver lokalitet som er aktiv (`brakklagt` False) i
  uke K = T−4 og har vært det sammenhengende i a uker: h(bøtte) er andelen
  aktive lokalitetsuker i trening (2017-01-02 … 2022-12-26) som fikk en
  brakklegging i K+4 … K+7. Bøttene er 1–26, 27–52, 53–65, 66–78, 79–91,
  92–104, 105+ og ukjent (aktiv siden seriens start 2012-01-02). Én kurve
  for hele landet, og anslaget er summen av h over lokalitetene i PO-en.
  Fra trening: 1–26: 0,0140; 27–52: 0,0291; 53–65: 0,0951; 66–78: 0,2013;
  79–91: 0,3008; 92–104: 0,2298; 105+: 0,1575.
- **K6, M-sesong.** Anslaget er y(T−4) + C(uke T+4) − C(uke T−4), der
  C(PO, ukenummer) er snittet av y over treningsårene for ISO-ukenummeret
  (uke 53 regnes som 52), glattet med et sentrert sirkulært 5-ukers
  snitt. Klippes til minst 0.

## Utstedelse og informasjon

Anslaget for uke T utstedes mandag i uke T (ISO-uke). Det bygger bare på
våre egne snapshots, med produksjonens etterslep:

- `lusetall` og `sjotemperatur` med observert uke til og med T−4
  (`uker_etterslep = 4`). Senere uker leses ikke, selv om de finnes.
  Versjonsvalget er R6s: `lusetall` GJELDENDE; `sjotemperatur` ALLE,
  slått sammen per (dato, lokalitet, felt) på sist utgitte.
- PO for en lokalitet er `akvakultur.prodomraade_kode` i siste snapshot
  til og med utstedelsesmandagen. Samme kobling brukes for utfallet og
  begge referansene. (R6 brukte siste snapshot for hele backtesten.)
- Alt leses gjennom lesedøra (`Kjoringslogg.les()` →
  `snapshot.versjoner()` → `_les()`), som i R6.

`har_laksefisk` brukes ikke. M25 (10.11.2026) fant at feltet betyr at
lokaliteten er en lakselokalitet, ikke at det står fisk: 601 413 uker er
både brakklagt og `har_laksefisk`. Sjekket før denne fila ble skrevet:
R6s skript nevner ikke feltet. K2 regner en lokalitet som aktiv når
`brakklagt` er False, og K6 bruker lokaliteter med `lus_er_rapportert`
True.

## Utfall og skår

Utfallsdefinisjonene er R6s:

- **Brakklegging** (K2) i uke w: lokaliteten finnes i uke w−1 med
  `brakklagt` False og i uke w med `brakklagt` True. Fravær er ikke
  brakklegging. Utfallet er antallet i PO-en i uke T … T+3.
- **Snitt voksne hunnlus** (K6): lokalitetene med `lus_er_rapportert`
  True, `voksne_hunnlus` og `sjotemperatur.lusegrense` i uka, og det
  aritmetiske snittet av `voksne_hunnlus`. En PO-uke med færre enn 5
  slike lokaliteter skåres ikke.

Utfallet leses når alle ukene det bygger på står i våre snapshots (K2:
T−1 … T+3 i `lusetall`; K6: T+4 i `lusetall` og `sjotemperatur`), med
gjeldende versjon den dagen skåreren kjører.

**Skår:** absolutt feil per (PO, uke) for modellen og for hver
referanse. En rad der modellen, en referanse eller utfallet ikke kan
regnes ut, skåres ikke for noen av de tre. Trefflista viser per type MAE
for modellen og for hver referanse over alle forseglede og avgjorte
rader, og SS = 1 − MAE(modell) / MAE(referanse) for a og b hver for seg.

**Åpningsdato:** mandagen da siste måluke etter planen står i våre
snapshots, altså måluka pluss `uker_etterslep` (4) uker. K2: mandag i uke
T+7. K6: mandag i uke T+8.

## Lesemåte

Trefflista er løpende. Den sier ikke at en type «slår referansen» før
minst 12 utstedelsesuker er avgjort for typen, og da etter R6s regel: SS
over null mot både a og b, og nedre 2,5 %-grense i en blokk-bootstrap
(blokker på 8 utstedelsesuker, 2000 trekk, frø 20261109) over null for
begge. SS over null med nedre grense på eller under null heter
«uavklart». SS på eller under null mot en av dem heter «slår ikke».
Grensa på 12 uker er fra R6: der skilte K2 seieren fra flaks (P12sig
0,81), og ingen kortere vindu gjorde det.
