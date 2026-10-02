---
dato: 2026-10-02
tittel: Biomasselag får et reserve-endepunkt, og hvert snapshot sier hvilket som svarte
status: utkast
commit: 7ccfcc0, 26cf656, c572f50, 7082f2f
---

# Biomasselag: reserve-endepunkt

**UTKAST.** Hva som ble bestemt står under, med målingen.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Bestemt

### 1. Primær først, reserve bare ved HTTP-feil eller error-objekt

`sources/biomasselag.py` spør `Yggdrasil/Biomasse/MapServer/0` først.
Feiler den med HTTP-feil (status, tidsavbrudd, tilkobling — etter
`_http`s fire forsøk) eller med et error-objekt i svaret, brukes
`fiskeridirWMS_akva/MapServer/6` med samme `FELTER` og samme
where-uttrykk (`HVOR = "1=1"`).

Fullstendighetsfeil utløser IKKE reserven: `count` ≠ antall rader,
`exceededTransferLimit` på en kort side, null rader. De gjelder for begge
endepunkter. `returnCountOnly`-sjekken er ny; før dette fantes bare
`exceededTransferLimit`.

Feiler begge, feiler kilden som før: `feil_paa_rad` øker, `sist_ok` står,
og `siste_feil` navngir begge grunnene.

Utløsende måling, 02.10.2026 03:52 UTC: primærens `/query` svarte 200 OK
med `{"error":{"code":500,"message":"Error performing query operation"}}`.
Metadata svarte fortsatt.

### 2. Endepunktet er et kontraktsfelt

`Observation.endepunkt` og `Source.endepunkt`: full URL til endepunktet
som faktisk svarte, stemplet av kjernen på hver rad som `published_at`.
Tom streng er «vet ikke». Snapshots fra før 02.10.2026 leses slik og
fylles ikke inn.

Ikke lagt i `utvalg`. `utvalg.er_utvidet()` leser en ny nøkkel som et
bredere søk, og ville merket ukas nye lokaliteter som utvalgsutvidelse.
`utvalg` er derfor likt for begge endepunkter.

Valgt av Heine 02.10.2026 foran `utvalg` og foran et felt per lokalitet.

### 3. Reserven er en advarsel, og health.json bærer den

Brukes reserven, legger kilden advarselen
`biomasselag: reserve fiskeridirWMS_akva/6 (primær: code 500)`. Den står i:

- `health.json`, i `advarsler_sist`, ved siden av `endepunkt`
- jobben, under KREVER TILSYN

Følgen er `tilsyn=true`, og samle.yml merker commiten DELVIS med teksten
om at en vakt ba om tilsyn, selv om dataene er komplette.

`advarsler_sist` gjelder alle kilder, ikke bare biomasselag, og
overskrives hver kjøring.

Valgt av Heine 02.10.2026 foran en health-post uten tilsyn.

### 4. Skjemakontroll per endepunkt

`KJENTE_UTELATTE` for primæren og `KJENTE_UTELATTE_RESERVE` for lag 6
(23 felt, 22 uten `shape`). Begrunnelsen per felt for de sju ekstra står i
`docs/KILDE-BIOMASSELAG.md`.

### 5. Nøkkelen er `(loknr, felt)`, og `objectid` er ikke med

`diff.compare()` sammenligner på `(entity_id, field)` innen kilden
(`core/diff.py:296`, `snapshot.NOKKEL` i `core/snapshot.py:75`).
`entity_id` er `loknr`, artene er samlet i verdien `arter_tilstede`, og
`objectid` emitteres ikke. Det betyr noe fordi `objectid` er tildelt på
nytt for 720 av 1108 lokaliteter mellom endepunktene.

Målt live 02.10.2026: et snapshot fra reserven mot datarepoets
2026-09-22 gir 29 endringer på 15 lokaliteter, og 0 av dem skyldes
`objectid`.

## Hvorfor

## Hva som ville snudd det
