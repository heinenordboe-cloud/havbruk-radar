# Finnes fisketall per lokalitet?

Målt 09.09.2026 mot repoet, dataregisteret (`data/`) og — for spørsmål 2
og 4 — mot den levende fila hos Fiskeridirektoratet.

**Kort svar: nei.** Ingen kilde i repoet, og ingen åpen fil vi kjenner,
bærer antall fisk eller stående biomasse per lokalitet. LOKNR-serien
bærer ikke beholdning; den bærer utsett av rensefisk.

---

## 1. Hva LOKNR-serien er, i sin helhet

`docs/KILDE-BIOMASSE.md` punkt 9, siste kulepunkt, ordrett og komplett:

> - **`biostat-utsett2c-omr-rensef-lok.csv`** er den eneste åpne fila med
>   `LOKNR` (10 583 rader, 2019–2025, avsluttet 01.01.2026, bare utsett av
>   rensefisk). Den viser at Fiskeridirektoratet *kan* publisere på
>   lokalitetsnivå; de gjør det bare ikke for laksebiomasse.

Setningen er ikke avkortet i kilden. «bare utsett av rensefisk» er hele
forbeholdet, og det er det avgjørende ordet.

Serien er også omtalt indirekte på linje 40 i samme fil: JSON-varianten
av `biostat-total-omr` har feil metadata, fordi `Forklaring`-blokken er
kopiert fra RENSEFISK-fila og beskriver `LOKNR` og `UTSETT_1000STK` —
felter som ikke finnes i totalserien.

## 2. Bærer den antall fisk eller biomasse per lokalitet?

**Nei. Bare utsettshendelser, og bare av rensefisk.**

Hentet og målt 09.09.2026 fra
`register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-OMR/biostat-utsett2c-omr-rensef-lok.csv`
(200, 623 355 byte, `text/csv`, `Last-Modified: Thu, 20 Aug 2026 04:38:18 GMT`).
Åtte kolonner, hele overskriftsrekka:

```
ÅR;MÅNED_KODE;MÅNED;PO_KODE;PO_NAVN;LOKNR;ARTSID;UTSETT_STK
```

`UTSETT_STK` er antall rensefisk SATT UT i måneden. Det finnes ingen
`BEHFISK_STK`, ingen `BIOMASSE_KG`, ingen `UTTAK_STK` — altså verken
beholdning ved månedslutt eller noe å regne beholdning av. `ARTSID` er
Berggylt, Bergnebb, Gressgylt, Grønngylt, Rognkjeks og «Ikke spesifisert».
**Laks og regnbueørret forekommer ikke i fila.**

Selv om man ville rekonstruert en rensefiskbeholdning av utsett alene,
går det ikke: uttak, dødelighet og svinn er ikke i fila, og rensefisk har
høy dødelighet. Og rensefisk er uansett feil art — Stien-formelen og HIs
kvoteenhet handler om laksefisken lusa sitter på.

## 3. Er den i råarkivet?

**Nei. Bare omtalt.** `data/arkiv/biomasse/` inneholder tre kropper
(2024-06-30, 2026-04-30, 2026-05-31), alle med totalseriens
overskriftsrekke (`ÅR;MÅNED_KODE;MÅNED;PO_KODE;PO_NAVN;ARTSID;UTSETTSÅR;
BEHFISK_STK;…`). Ingen fil noe sted under `data/arkiv/` eller `data/raw/`
har `LOKNR` i seg, og ordet forekommer i repoet bare på de tre linjene i
`docs/KILDE-BIOMASSE.md` (40, 530, 531). Kroppen jeg hentet i dag ligger
i /tmp og er ikke skrevet inn i `data/`.

## 4. Kadens, dekning og «avsluttet 01.01.2026»

Den bærer ikke beholdning, så spørsmålet er strengt tatt bortfalt. Målt
likevel, fordi tallene sier noe om hva Fiskeridirektoratet publiserer på
lokalitetsnivå når de først gjør det:

- **Kadens:** månedlig, én rad per (måned, lokalitet, art). 10 582
  datarader (`wc -l` gir 10 583 med overskriftsrekka — det er tallet i
  KILDE-BIOMASSE).
- **Dekning:** 632 unike `LOKNR` over hele serien. 601 av dem finnes i
  akvakulturregisterets 1 779 lokaliteter. Aldri mer enn 474 lokaliteter
  i ett år — altså under 27 % av registeret på sitt beste.
- **«Avsluttet 01.01.2026»** betyr at januar 2026 er den siste måneden med
  rader, ikke at fila er tatt ned. Den republiseres fortsatt den 20. hver
  måned som resten av biomassestatistikken (`Last-Modified` 20.08.2026),
  men har ikke fått en rad på sju måneder.

  Serien dør ikke brått — den forvitrer. Lokaliteter med rader per år:

  | år | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|---|---|---|
  | lokaliteter | 474 | 464 | 397 | 317 | 284 | 214 | 155 | 3 |
  | rader | 1762 | 2114 | 1978 | 1621 | 1419 | 956 | 728 | 4 |

  **Ikke verifisert:** hvorfor. Om rensefiskbruken faktisk faller, om
  rapporteringsplikten er endret, eller om publiseringen har stoppet, er
  ikke fastslått, og skal ikke gjettes.

## 5. Noen annen kilde med fisketall per lokalitet?

**Nei.** Alle ni kilder i `sources/` er gjennomgått på feltnivå mot siste
snapshot:

| kilde | enhet | bærer den antall fisk? |
|---|---|---|
| `biomasse` | produksjonsområde | JA — `beholdning_antall`, men per PO per måned |
| `akvakultur` | lokalitet | nei |
| `lusetall` | lokalitet | nei |
| `sjotemperatur` | lokalitet | nei |
| `romming` | rømmingshendelse | delvis — se under |
| `eierskap` | tillatelse | nei |
| `enhetsregisteret` | foretak | nei |
| `trafikklysvedtak` | produksjonsområde | nei |
| `ekspertgruppen` | produksjonsområde | nei |

To presiseringer, siden begge ligner på et svar:

- **`akvakultur.kapasitet`** er MTB i tonn — en TILLATELSE, et tak, ikke
  en beholdning. Et anlegg med 2 340 tonn MTB kan stå brakklagt.
  Råsvaret fra registeret er også sjekket direkte
  (`data/arkiv/akvakultur/2026-08-31.json.gz`, 28 nøkler): `capacity`,
  `tempCapacity` og `speciesTypes` er alt som finnes om størrelse. Ingen
  beholdning er filtrert bort av kilden — den er ikke i svaret.
- **`romming.antall_romt_estimert` / `antall_romt_endelig`** er antall
  fisk per lokalitet, men bare de som RØMTE, bare den datoen det skjedde.
  Det er en hendelse, ikke en beholdning.

`data/arkiv/hi-lakselus-ukesstatus/` er kartlagt: én PDF, ingen kilde,
ingen fisketall. `KILDE-BIOMASSE.md` punkt 9 har fra før avvist ArcGIS
`Yggdrasil/Biomasse` (ingen tonnasje, intet antall) og
`Yggdrasil/Produksjonsintensitet` (tonn/km² i toårige glidende snitt).

## 6. Lusetall: per fisk eller totalantall?

**Per fisk. Vi har ikke totalantall.**

`sources/lusetall.py:67` mapper `voksne_hunnlus` fra BarentsWatch-feltet
`avgAdultFemaleLice` — gjennomsnittlig antall voksne hunnlus PER FISK i
lokaliteten den uka, grenseverdi 0,5 i sesong
(`docs/BARENTSWATCH-FUNN.md:103`).

Råsvaret er sjekket, ikke bare feltlista vår: kroppen i
`data/arkiv/lusetall/2026-08-03.json.gz` har 20 nøkler per lokalitet, og
ingen av dem er et fiskeantall:

```
avgAdultFemaleLice, hasCleanerfishDeployed, hasIla, hasMechanicalRemoval,
hasPd, hasReportedLice, hasSalmonoids, hasSubstanceTreatments,
inFilteredSelection, isFallow, isOnLand, isSlaughterHoldingCage, lat,
localityNo, localityWeekId, lon, municipality, municipalityNo, name
```

**Følgen for HIs kvoteenhet.** Enheten er totalt antall voksne hunnlus i
et område, altså Σᵢ (lus_per_fiskᵢ × N_fiskᵢ) over lokalitetene. Vi har
den første faktoren per lokalitet per uke fra 2012. Den andre finnes bare
per produksjonsområde per måned (`biomasse.beholdning_antall`).

**Fisketallet er den ENESTE manglende brikken — men det er én brikke som
mangler helt, ikke én som mangler delvis.** Deles PO 4 i 4A–4D, finnes
det ingen målt verdi å fordele på de fire. Forbeholdet
`KILDE-BIOMASSE.md` allerede bærer for PO-nivået — at
Σᵢ (N_fiskᵢ × lusᵢ) ≠ N_fisk_PO × middel(lus), med ukjent fortegn på
skjevheten — blir strengere på reguleringsområdenivå, ikke mildere: der
PO-produktet i det minste summerer over hele det området fisken faktisk
står i, må en oppdeling først bestemme hvor fisken står.
