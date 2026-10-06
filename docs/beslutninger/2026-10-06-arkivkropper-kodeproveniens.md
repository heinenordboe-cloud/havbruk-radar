---
dato: 2026-10-06
tittel: Arkivkropper uten snapshot får kodeproveniens i kjøringens loggfil, ikke i en sidevogn per kropp
status: utkast
commit: (denne)
---

# Arkivkropper uten snapshot får kodeproveniens i loggfila

**UTKAST.** Hva som ble bestemt står under, med det som ble målt.
«Hvorfor» og «hva som ville snudd det» skrives av Heine.

## Hva som ble bestemt

`arkiver_auksjon.py` og `arkiver_vilkar.py` skriver kropper til
`data/arkiv/` uten at noe snapshot peker på dem. De øvrige arkivkroppene
er knyttet til kode gjennom snapshotet som bærer deres `raw_hash`, og som
`snapshot.write()` stempler med `kode_commit` og `kode_rent`. Disse to
hadde ingen slik kobling (APNE-SPORSMAL, punkt 9 i den andre lista, fra
23.09.2026).

Fra 06.10.2026:

1. **Samme sperre som `run.py`.** Begge skriptene kaller
   `kodeproveniens.krev_sporbar()` før noe hentes. Urent arbeidstre,
   eller HEAD som ikke finnes på origin/main, gir `::error::` og exit 1.
   `--torrkjor` er unntatt, som i `run.py`: den skriver ingen fil.
2. **Stempelet står i loggfila.** Hver post med `sha256` i
   `<dato>.logg.json` får `kode_commit`, `kode_rent` og `fetched_at`.
3. **Ingen ny fil per kropp.** Spørsmålet var «sidevogn eller holder
   `raw_hash`?». Loggfila er allerede en sidevogn: én per kjøring,
   append-only (skrives bare om den ikke finnes), med sha256 per kropp.
   Den bærer nå også koden.

Gamle logger fylles ikke inn i ettertid. De vet ikke hvilken kode som
skrev dem, og en påstand om det nå ville vært oppdiktet (CLAUDE.md regel
2, og 1b-7 om å ikke fylle inn proveniens retroaktivt).

## Hva det dekker av de tre argumentene i APNE-SPORSMAL

| Argument | Dekket? |
|---|---|
| 1. Koden avgjør HVA som ble hentet | Ja for det som ble hentet: loggen sier hvilken kode som valgte adressene. Fraværet av en kropp er synlig som en manglende post i loggen, ikke i en sjekksum. |
| 2. En rar arkivfil kan ikke etterprøves mot koden | Ja, for kropper skrevet fra 06.10.2026: sha256 → loggpost → `kode_commit`. |
| 3. Sperren gjelder ikke | Ja: `krev_sporbar()` før henting. |

Det som IKKE dekkes: en kropp som er byte-lik en eldre, skrives ikke på
nytt (`raw.arkiver_ny()`). Loggposten for dagens kjøring peker da på en
fil skrevet av en tidligere kjøring, muligens med annen kode. Det er en
sann påstand — kroppen er den samme uansett hvem som lastet den ned —
men stempelet sier hvem som fant den i dag, ikke hvem som skrev fila.

## Målt

- Prøvene i `tests/test_arkiver_auksjon.py` og `tests/test_arkiver_vilkar.py`:
  stempelet står på hver kropp, ikke på feil- og advarselsposter, og
  `IkkeSporbar` stopper før første henting uten å skrive noe.
- Mot det ekte arbeidstreet med ucommitede endringer 06.10.2026:
  `::error::Vilkårsarkiveringen startet ikke: arbeidstreet er ikke rent`,
  exit 1, ingen mappe skrevet.
