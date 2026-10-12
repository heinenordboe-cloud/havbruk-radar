---
name: maling
description: Protokollen for en måling i havbruk-radar (et MALING-dokument i docs/). Bruk når en oppgave ber om å måle, kartlegge eller etterprøve noe mot arkivet, eller når et MALING-dokument skal skrives eller endres.
---

# Måling

En måling svarer på et spørsmål mot kropper vi har arkivert. Den
vurderer ikke hva svaret er verdt, og den retter ingenting før Heine
har sett svaret.

## Merkene

Hver påstand får ett merke. Definisjonene står i
`docs/PROVENIENS-2026-09-11.md` (linje 12–15) og øverst i
`docs/MALING-FUNN-OKTOBER.md`:

- **MÅLT**: holdt mot en arkivert kropp, med sha256 oppgitt.
- **MÅLBAR**: lest i et snapshot, avledet, eller regnet ut av målte tall,
  men ikke selv holdt mot en kropp.
- **EKSTERN**: hviler på en kropp som ikke er i arkivet. Arkiver den
  (`arkiver_*.py` og `raw.arkiver_ny()`) og gjør den til MÅLT, eller la
  merket stå.
- **UBELAGT**: ingen kropp sier det.

## Hver påstand

- **Hashen** er sha256 over den UTPAKKEDE kroppen for `.gz` i
  `data/arkiv/`, over fila for `.parquet`. Oppgi sti og hash, i
  påstanden eller i en tabell over kroppene.
- **«Feil hvis:»** én linje om hva som ville gjort påstanden usann.
  Se F1.1–F1.6 i `docs/MALING-FUNN-OKTOBER.md`.
- **Skriptet** ligger i `analyse/<måling>/` og navngis i dokumentet.
  Tabellene i dokumentet er utskriften, uendret.

## STOPP-regelen

Skriv den FØR resultatet er kjent, i dokumentet: hva som må til for at
målingen stopper og rapporterer i stedet for å gå videre. Mønsteret står
i `docs/beslutninger/2026-08-27-ekspertgruppen-som-kilde.md`
(«STOPPREGEL» og «UTFALL av stoppregelen»). Utløses den, stopp og si
fra. Går du videre forbi et hull, skriv hvorfor, slik «Hva som mangler,
og hvorfor jeg ikke stoppet» i `docs/MALING-HAVBRUKSFOND.md` gjør.

## Formatet

Som `docs/MALING-FUNN-OKTOBER.md`: dato og datagrunnlag øverst, merkene
forklart, «De tre sterkeste funnene» med hvorfor de er sterkest og
hvilke som er svakere, og deretter nummererte funn (F1.1, F1.2 …) med
merke, kilde, kropper og «Feil hvis».

Et dokument som er committet, skrives ikke om. Rettelser kommer som en
datert etterskrift nederst («Etterskrift DD.MM.ÅÅÅÅ: …»), med en linje
om at teksten over ikke er endret.

## Til slutt: kontrolløren

Før push (CLAUDE.md §8) kjøres kontrolløren på dokumentet, og den får
bare stien:

    claude -p --agent kontrollor --add-dir ../havbruk-radar-data \
        "Kontroller docs/MALING-<navn>.md"

Fra en økt som startet etter at `.claude/agents/kontrollor.md` fantes,
kan den også kalles som subagent. Avvik den finner, rettes med en
datert etterskrift.
