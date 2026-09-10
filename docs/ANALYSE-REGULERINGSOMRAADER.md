# Lokalitetene mot HIs 28 reguleringsområder

Kjørt 09.09.2026:

    .venv/bin/python analyse/reguleringsomraader.py

Punkt-i-polygon for alle **1 779 lokaliteter** i akvakultursnapshotet
2026-08-31, mot de 28 polygonene i reguleringsområdesnapshotet
2026-06-29. Dette er en ANALYSE. Resultatet er utledbart av to snapshots
som allerede ligger i `data/raw/`, og skrives ikke som snapshots.

Geometrien leses av `geometri`-feltet i SNAPSHOTET, ikke av geojson-
kroppen i arkivet. Det er med vilje: da er det den lagrede WKT-en som
prøves, og er den ubrukelig, viser det seg nå og ikke om to år.

---

## 1. Lokaliteter per reguleringsområde

| omr | n | omr | n | omr | n | omr | n |
|---|---:|---|---:|---|---:|---|---:|
| 1A | 34 | 4C | 70 | 7A | 78 | 11A | 38 |
| 1B | 28 | 4D | 37 | 7B | 57 | 11B | 29 |
| 2A | 94 | 5A | 47 | 8A | 105 | 12A | 38 |
| 3A | 155 | 5B | 51 | 8B | 86 | 12B | 31 |
| 3B | 103 | 6A | 52 | 9A | 165 | 12C | 13 |
| 4A | 44 | 6B | 189 | 10A | 75 | 12D | 6 |
| 4B | 88 | | | 10B | 20 | 13A | **0** |
| | | | | | | 13B | 17 |

**Sum: 1 750.** Ingen lokalitet traff mer enn ett område — polygonene
overlapper ikke, målt og ikke antatt.

## 2. Utenfor alle 28: 29 lokaliteter

| | n |
|---|---:|
| utenfor alle 28 polygoner | **29** |
| uten `prodomraade_kode` i registeret | 810 |
| begge deler | **29** |
| utenfor MEN med `prodomraade_kode` | **0** |
| i et område MEN uten kode | 781 |

**Tallet er lavere enn ventet, og det er det riktige svaret.**
Oppgaven ventet at de 29 skulle ligne de ~810 uten produksjonsområde.
Det gjør de ikke, og grunnen er at de to spørsmålene ikke er det samme:

- **De 29 er der de er fordi de ikke ligger ved kysten.** 28 av 29 er
  `Fresh` vanntype, 24 av 29 `Onshore` — settefiskanlegg i innsjøer og
  vassdrag, langt innenfor der HI har tegnet noe. Den ene i saltvann er
  også den ene med plassering `Ocean`.
- **De 781 ligger ved kysten uten å ha en PO-kode.** 526 av dem står i
  saltvann og 405 er `Offshore`. De faller innenfor et polygon fordi de
  fysisk er der; de mangler kode fordi produksjonsområdene gjelder
  matfisk av laks og ørret i sjø, og et settefisk- eller skjellanlegg
  får ingen kode uansett hvor det ligger.

**Den viktige raden er «utenfor MEN med `prodomraade_kode`: 0».** Ikke
én eneste lokalitet som Fiskeridirektoratet har plassert i et
produksjonsområde faller utenfor HIs 28. Reguleringsområdene dekker
altså hele det området produksjonsområdene dekker, uten hull.

## 3. Krysskontrollen: 969 av 969 enige, null avvik

| | n |
|---|---:|
| med `prodomraade_kode` i registeret | 969 |
| av dem tilordnet et reguleringsområde | 969 |
| **ENIGE** | **969** |
| **AVVIK** | **0** |

Hver eneste lokalitet med produksjonsområdekode fra Fiskeridirektoratet
havner i et reguleringsområde hvis tall er det samme. En lokalitet i PO4
havner i 4A, 4B, 4C eller 4D — i alle 969 tilfeller.

**Begge sider er dermed bekreftet på én gang**, som oppgaven forutså:

- HIs polygoner ligger korrekt inni produksjonsområdene.
- Koordinatene i akvakultursnapshotet er riktige, og
  koordinatrekkefølgen (lengde, så bredde) er riktig lest.
- Vår punkt-i-polygon-implementasjon virker.

Ingen av de tre kunne vært feil uten at avvikene ble mange. Null av 969
er ikke et resultat man kan få ved uhell.

En fjerde kontroll faller ut av det samme, uavhengig av geometrien:
geojson-fila bærer `prodomr` som eget felt ved siden av navnet, og
kilden nekter å skrive et område der de to er uenige. Alle 28 er enige.

## 4. Områdene HI oppgir med null anlegg

HIs tall er lest av **tabell 1 i rapport 2026-37**, som er arkivert som
`grensetall_2026-37` i
`data/arkiv/reguleringsomraader/2026-06-29.json.gz`. Kolonnen er «antall
anlegg med produksjon i utvandringsperioden per reguleringsområde
(gjennomsnitt siste fire år)», og stjernen betyr at området «ikke fikk
beregnet akseptabelt utslipp av lakselus fordi få eller ingen anlegg var
i drift årene 2022–2025».

| omr | alle registrerte | m/laks | i sjø, ikke landbasert | m/kommersiell aktivitet | HI oppgir |
|---|---:|---:|---:|---:|---:|
| 1A | 34 | 12 | 2 | 2 | 0* |
| 12D | 6 | 6 | 4 | 4 | 0* |
| 13A | **0** | 0 | 0 | 0 | 0* |

### 13A stemmer helt

Null lokaliteter av noe slag faller i 13A. Ikke «nesten tomt» — tomt.
Området er den ytterste delen av Øst-Finnmark, og
akvakulturregisteret har ingenting der.

### 1A og 12D stemmer IKKE, og det er ikke et registreringsartefakt

Registrert er ikke det samme som i drift, så tallene over avgjør
ingenting alene. Men vi har lusetall per lokalitet per uke, og kan spørre
direkte om anleggene sto med fisk i nøyaktig det vinduet HI brukte.
Terskelen er den mest romslige som finnes — **én uke med
`har_laksefisk = True` er nok** — nettopp fordi den bare kan gjøre HIs
null mer sannsynlig:

| omr | HIs utvandringsvindu | 2022 | 2023 | 2024 | 2025 | HI oppgir |
|---|---|---:|---:|---:|---:|---:|
| 1A | 24.04–23.06 | 2 | 2 | 2 | 2 | 0 |
| 12D | 09.06–01.08 | 4 | 4 | 4 | 4 | 0 |
| 13A | 08.06–29.07 | — | — | — | — | 0 |

De samme anleggene, hvert eneste år:

    1A    12832 RISHOLMEN      Lillesand,  585 t MTB, permanent
          14016 AUENES         Lillesand,  910 t MTB, permanent
          (35778 FREDRIKSTAD INNOVASJONSPARK er landbasert og
           midlertidig klarert — holdt utenfor med vilje)

    12D   13143 BONDEJORDA     Lebesby,   4 000 t MTB, permanent
          13337 HOVDENAKKEN    Lebesby,   6 000 t MTB, permanent
          13813 KVITELV        Lebesby,   4 725 t MTB, permanent
          34697 ØYRA           Lebesby,   8 300 t MTB, permanent

12D er ikke et grensetilfelle: fire sjøanlegg med til sammen 23 025 tonn
MTB i Laksefjord, alle med laksefisk rapportert i hver eneste
utvandringsperiode 2022–2025.

**Hva som IKKE er avklart.** Hvorfor HI oppgir null, er ikke fastslått,
og det skal ikke gjettes. Minst tre forklaringer er forenlige med det vi
ser, og repoet kan ikke skille dem:

1. HI bruker et annet anleggsbegrep enn «lokalitet med laksefisk»
   — for eksempel innrapportert biomasse over en terskel.
2. HI tilordner anlegg til område med en annen metode enn geometrisk
   punkt-i-polygon.
3. Tallet er en avrunding under stjernen, som eksplisitt dekker «få
   eller ingen».

Det som ER fastslått: vår tilordning er ikke feil. Alle sju anleggene
har `prodomraade_kode` 1 og 12 fra Fiskeridirektoratet, som er de samme
tallene som 1A og 12D bærer, og de inngår i de 969 som stemte i punkt 3.
