---
dato: 2026-08-22
tittel: Enkeltpersonforetak filtreres bort i kilden
status: utkast
commit: 
---

# Enkeltpersonforetak filtreres bort i kilden

> **Utkast.** Alt under «Hva som er gjort» og «Hva som ble målt» er skrevet
> fra diffen og fra kjøringer mot levende API. Avsnittene merket
> **[din vurdering]** er ikke fylt ut — de er dine.

**Bestemt:** Enheter med organisasjonsform `ENK` hentes ikke inn. De
filtreres bort i `sources/enhetsregisteret.py` før observasjoner
opprettes og før rådataene arkiveres, og `core/snapshot.py` nekter å
skrive et snapshot som likevel inneholder dem.

---

## Hva som var galt

Et enkeltpersonforetak er ikke et eget rettssubjekt. Foretaket ER
innehaveren: hun hefter personlig med hele sin formue, forretningsadressen
er i praksis hjemmeadressen, og orgnummeret slår opp til ett navngitt
menneske hos Brreg. Da er navn, kommune, postnummer, næringskode,
registreringsår — og særlig `konkurs` og `under_tvangsavvikling` —
opplysninger om en identifiserbar fysisk person.

CLAUDE.md regel 3 sier at ingen persondata skal hentes fra
Enhetsregisteret. Regelen var forstått som «ikke hent rolleendepunktet og
ikke lagre gateadresse», og begge deler var gjort. Det holdt ikke: 34
enkeltpersonforetak lå i hvert eneste snapshot uansett, fordi de kom inn
gjennom det ordinære næringskodesøket som en hvilken som helst bedrift.

**Kontrollen som skulle fanget det, kunne ikke fange det.** Åpningen av
repoet 16.08 ble begrunnet med at snapshotet inneholdt «kun selskapsdata
(954 enheter, ni felter, alle entity_id ni siffer), ingen persondata».
Ni siffer er sant for et ENK akkurat som for et AS — prøven var
syntaktisk der spørsmålet var semantisk. Feltet som faktisk svarer,
`organisasjonsform`, lå i dataene hele tiden.

Det er CLAUDE.md regel 1b i en femte utgave. De fire første handlet om
tid; denne handler ikke om tid, men om samme feilform: et skille som
finnes i kilden, men som ikke ble båret over i kontrollen som skulle
håndheve det.

[2026-08-16-repoet-er-offentlig.md](2026-08-16-repoet-er-offentlig.md) er
merket delvis feil med denne begrunnelsen.

## Hvorfor ENK og ikke DA og ANS

Spørsmålet er ikke om NAVNET ser ut som et personnavn. «Ola Nordmann AS»
er også oppkalt etter en person, og et AS lagres. Spørsmålet er om
foretaket ER personen.

- **ENK** er ikke et eget rettssubjekt. Filtreres.
- **DA og ANS** er ansvarlige selskaper. Deltakerne hefter personlig, men
  selskapet er et eget rettssubjekt med eget organisasjonsnummer, egen
  adresse og partsevne, og deltakerne selv står bare i rolleregisteret
  som pipelinen aldri spør etter. Selskapsdata om en juridisk person er
  ikke personopplysninger (GDPR fortalepunkt 14). Beholdes.

Å filtrere DA og ANS på at navnet inneholder personnavn ville vært
nøyaktig samme feil som ni-siffer-testen: en syntaktisk prøve på et
semantisk spørsmål.

Skillet lar seg etterprøve i `institusjonell_sektorkode`, som allerede
lagres. Målt i snapshotene 22.08.2026:

| form | sektor | betydning |
|------|--------|-----------|
| ENK | 8200 | husholdninger — personen selv |
| DA, ANS, PRE | 2300 | personlige foretak — foretakssektorene |
| AS, ASA, SA | 2100 | private aksjeselskaper |

SSBs sektorgruppering trekker altså samme grense uavhengig av
resonnementet over. Det er ikke et sammentreff: begge følger av at ENK
ikke er et eget rettssubjekt.

**[din vurdering]** — Om grensa likevel skal gå ved sektor 2300 i stedet
for ved formen ENK. Det ville tatt ut 32 DA, 31 ANS og 1 partrederi i
tillegg, og er en linje i `core/persondata.py`.

## Hva som er gjort

**Filteret ligger to steder, med hver sin grunn.**

- `fetch()` tar personformene ut av `_embedded.enheter` FØR sidene
  returneres for arkivering. Rå-arkivet lagrer hele API-svaret, og der lå
  gateadressen — som `FELTER` holder utenfor snapshotet — til alle 34.
  Feltvalget gjelder snapshotet, ikke arkivet. Filtrerer man bare i
  `parse()`, ligger hjemmeadressen i arkivet uansett.
- `parse()` filtrerer også, fordi arkivfilene fra før i dag inneholder
  personformene. En re-parse er nettopp veien de kommer inn igjen på.

Konvolutten røres ikke: `page.totalPages` og hvilket søk sida kom fra står
igjen uendret, så arkivet kan fortsatt avsløre en avkortet paginering ved
re-parse — som var hele grunnen til at konvolutten arkiveres.

**To ting telles fortsatt før filteret, med vilje.** Varselet om tomme
næringskodesøk spør «svarte Brreg med noe på denne koden»; telles det
etter filteret, ser en kode som legitimt bare inneholder ENK ut som en
utgått kode. Og pagineringen styres av svaret fra Brreg — en side der alle
treffene var ENK ville etter filteret vært tom, og løkka hadde brutt ut
midt i et søk og mistet sidene bak.

**Antallet skrives til kjøringsloggen**, per organisasjonsform. Filtrering
er stille av natur — en enhet som aldri blir en observasjon etterlater
seg ingen rad å savne — så uten tallet ville et hopp fra 202 til 900 vært
usynlig. Det telles ORGNUMRE, ikke forekomster: kilden søker på ni
næringskoder og samme foretak kan komme i retur fra flere, og en teller
ville hoppet av at en næringskode ble lagt til framfor av at flere
personer kom inn i utvalget.

**Vakten i `snapshot.write()`** nekter å skrive et snapshot der en filtrert
organisasjonsform likevel finnes i radene. Den ligger i den ene trakta
både `run.py` og `backfill.py` skriver gjennom, samme plassering og samme
begrunnelse som datokontrollen ved siden av. Den fanger en kilde som
glemmer filteret, en re-parse gjennom en vei som ikke filtrerer, eller en
backfill som går utenom `fetch()`.

Hva vakten IKKE dekker, sagt rett ut: den ser bare rader der feltet heter
`organisasjonsform`, og den fyrer etter at rå-arkivet er skrevet. Den
fanger at et kjent filter sviktet — ikke at lista over personformer er
riktig, og ikke persondata på vei inn i arkivet.

**Listen over personformer ligger i `core/persondata.py`**, ikke i
`config.yml`. Samme begrunnelse som feltvalget: hvem vi nekter å lagre
data om skal ikke kunne endres ved et uhell i en YAML-fil.

## Hva som ble målt

Verifisert mot levende Brreg-API 22.08.2026, ikke bare mot testdata.

**Kjøringen som ville skjedd mandag 24.08:**

    202 foretak filtrert bort som fysisk person (ENK 202)
    1810 entiteter i snapshotet, 0 med organisasjonsform ENK
    0 ENK i rå-arkivet, totalPages og næringskode bevart i konvolutten

202, ikke 34. Revisjonens tall stammer fra snapshotet 17.08, og
`config.yml` har fått flere næringskoder siden — `03.300` (tjenester
tilknyttet fiske, fangst og akvakultur) bidrar alene med 133 ENK.
Utvalget har vokst fra 938 til 2012 enheter, og eksponeringen ville altså
vært seks ganger større neste mandag enn den revisjonen fant.

**Re-parse av det ekte arkivet** (`2026-08-17.json.gz`, 954 enheter inn):
904 entiteter ut, 0 ENK.

**Testene:** 161 → 172 grønne, altså 11 nye på dette.

## Historikken som allerede er skrevet

Ikke rørt. Kartlagt:

| sted | omfang |
|------|--------|
| `data/raw/enhetsregisteret/` | 5 filer, 34 ENK i hver |
| `data/arkiv/enhetsregisteret/` | 5 filer, 34 ENK med **gateadresse** i hver |
| `data/changelog/` | 0 — ingen ENK-endring er logget ennå |
| kodrepoets git-historikk | 2 parquet-filer, 34 ENK i hver |

Arkivet er verre enn snapshotene: der ligger hele API-svaret, inkludert
gateadressen som feltvalget holder utenfor snapshotene.

Kodrepoet er den ubehagelige raden. Snapshotene lå der før `91ccee6`
skilte kode og data, og blobene er fortsatt nåbare i historikken — i
perioden 16.–18.08 var det repoet offentlig.

**[din vurdering]** — valget mellom:

- **La historikken stå, filtrer ved lesing og publisering.** Holder
  append-only og «git er databasen» intakt. Prisen er at persondataene
  blir liggende i to repoers historikk, og at hver framtidig lesevei må
  huske filteret — nøyaktig den formen for «noen må huske det» som denne
  saken handler om.
- **Skriv historikken om.** `git filter-repo` på begge repo, force push,
  alle hasher endres. Bryter et arkitekturprinsipp med vilje, gjør
  eksisterende kloner uforenlige, og fjerner ikke det noen allerede har
  kopiert. Til gjengjeld er dataene faktisk borte.
- **Noe imellom** — for eksempel omskriving av kodrepoet, som var
  offentlig, og filtrering ved lesing i datarepoet, som ikke har vært det.

## Prisen

**[din vurdering]**

## Ville snudd det

**[din vurdering]**
