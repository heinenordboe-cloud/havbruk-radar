---
dato: 2026-09-09
tittel: Departementets PO9-begrunnelse hviler på en udatert ekspertversjon — funnet er om departementet, ikke om datamodellen
status: utkast
commit: [fylles inn]
---

## Hva som ble bestemt

Funnet føres som et FORBEHOLD ved lesing av departementets
fargeleggingsbegrunnelser, ikke som en endring i noen kilde, noe felt
eller `core/`.

Vår side er allerede i orden. `diff.revisjon()` og
CLAUDE.md 1b-5 lagrer begge ekspertversjonene av 2024 som to påstander om
samme tidspunkt, gjort på hver sin dato, og begge er sanne. Det er
nettopp derfor avviket i departementets tekst i det hele tatt lot seg
måle.

Og ett skille skal ikke viskes ut: departementets lister over SPRIKENDE
områder er ikke lister over AVVIK fra rådet. Se «Skillet som bærer
notatet».

## Hva som ble målt

Departementets fargeleggingsmelding 19.06.2026 begrunner PO9 slik,
ordrett fra kroppen (`docs/VERIFISERING-PRESSEMELDINGER.md`):

> «Ved årets fargelegging gjelder dette ett av produksjonsområdene,
> Vestfjorden og Vesterålen (PO9). Ekspertgruppens vurderinger er at
> området var moderat påvirket i 2024, men at det var like sannsynlig at
> påvirkningen var lav som moderat i 2025. Styringsgruppens råd er
> imidlertid at området var moderat påvirket også i 2025.»

`docs/MALING-RAD-MOT-EKSPERTVURDERING.md` holdt de tre påstandene mot
kroppene:

| påstand | kroppene | dom |
|---|---|---|
| «moderat påvirket i 2024» | 2024-rapporten Tabell 6.1: `Lav–Moderat*`. 2025-rapporten Tabell 6.1 (oppdatert 2024): `Moderat` | **sann bare om den reviderte** |
| «like sannsynlig at påvirkningen var lav som moderat i 2025» | 2025-rapporten Tabell 6.3: `Lav–Moderat*`, `Like sannsynlig som ikke` | sann |
| «styringsgruppens råd … moderat også i 2025» | Styringsgruppens Tabell 8: `Moderat (10)*` | sann |

**Den første påstanden er ikke gal — den er UDATERT.** Da ekspertgruppen
leverte for 2024, skrev den `Lav–Moderat*` for PO9, med nøyaktig samme
forbehold som for 2025. Kategorien ble `Moderat` først et år senere, i
2025-rapportens forenklede nye SHELF-vurdering. Rapporten sier det selv:

> «Oppdateringen innebærer at påvirkningen i PO9 i 2024 blir vurdert til
> moderat, mens den i fjorårets rapport ble vurdert til å være helt på
> grensen mellom lav og moderat. Sannsynlighetskategorien for dødelighet
> over 10 % i PO9 endres dermed fra like sannsynlig som ikke til mer
> sannsynlig enn ikke.»

Departementets setning sier ikke hvilken av de to versjonene den
gjengir. Lest som en beskrivelse av 2024-rapporten er den usann. Lest som
en beskrivelse av grunnlaget for fargeleggingen i 2026 — 2025-rapporten,
der begge år er oppdatert — er den sann.

**Og styringsgruppen avgjorde ingenting i 2024.** Der ekspertgruppen
skrev `Lav–Moderat*`, skrev styringsgruppens 2024-kropp `Lav-Moderat` i
tabellen og `<10%/10-30%` i punktlista. Den førte tvetydigheten videre
uendret. Avgjørelsen skjer for første gang i 2025-kroppen — der
styringsgruppen oppgir en regel med hjemmel i Meld. St. 16 tabell 10.1.

Departementets framstilling er altså riktig i sak: for det grunnlaget
fargeleggingen bygger på, ER 2024 moderat og 2025 tvetydig, og
styringsgruppen løste tvetydigheten. Det som mangler er hvilken versjon
2024-tallet kommer fra.

## Funnet er om departementet, ikke om datamodellen

Dette skal notatet være tydelig på, fordi det er lett å lese som et
datamodellfunn og ikke er ett.

Repoet håndterer allerede saken. CLAUDE.md 1b-5 sier at to snapshots som
er uenige om samme år ikke er en feil, men to påstander om samme
tidspunkt gjort på hver sin dato — og at begge er sanne.
`diff.revisjon()` er aksen som uttrykker det, og for ekspertgruppen ble
den utløst: 2025-kroppen skrev 14 revisjonsrader til
`2024-12-31.2.parquet`. Verdien `Lav–Moderat*` fra 2024-rapporten er
IKKE overskrevet. Den ligger der, med sin egen `published_at`.

Målingen kunne bare stilles fordi begge påstandene er bevart. Hadde
repoet fulgt standardantakelsen om at fortiden ligger fast, ville
2024-verdien vært overskrevet av revisjonen, og departementets setning
ville sett riktig ut mot våre data.

**Ingen endring følger av dette i `sources/`, `core/` eller noe felt.**

## Skillet som bærer notatet

Departementet publiserer i hver runde en liste over områder der
ekspertenes vurdering var ULIK i de to grunnlagsårene. Verifisert ordrett
i `docs/VERIFISERING-PRESSEMELDINGER.md`:

| runde | sprikende områder | departementets ord |
|---|---|---|
| 2020 | PO2, PO3, PO4, PO5, PO7, PO10 | «Områder med endring fra 2018 til 2019» |
| 2022 | PO2, PO4, PO5 | «For tre av områdene var ekspertenes vurdering ulik i 2020 og 2021» |
| 2024 | PO4, PO8 | «For to av områdene var ekspertenes vurdering ulik i 2022 og 2023» |
| 2026 | PO9 | «Ved årets fargelegging gjelder dette ett av produksjonsområdene» |

**En slik liste er en liste over områder der skjønn er TILLATT. Den er
ikke en liste over områder der departementet FRAVEK rådet.** De to er
ikke samme sak, og en analyse som teller den ene som den andre ville
telt tillatelse som handling.

Departementet sier selv hva listene betyr, 06.03.2024:

> «Fargeleggingen følger direkte av handlingsregelen i trafikklyssystemet
> i områdene hvor ekspertenes vurdering av miljøpåvirkningen er lik i
> begge år.»

Altså: står området på lista, er handlingsregelen ikke bindende, og
departementet gjør «en samlet vurdering hvor også samfunnsøkonomiske
konsekvenser har spilt inn» (04.02.2020). Det sier ingenting om hvorvidt
utfallet ble et annet enn rådet.

### Bare runde 2018 har et målt avvik fra rådet

Ett tilfelle i hele materialet er et AVVIK, og det er det eldste.
Pressemeldingen 30.10.2017:

> «- Min vurdering er i hovedsak den samme som rådene fra
> styringsgruppen, men etter en helhetlig vurdering har jeg valgt å sette
> produksjonsområde 7 til grønt.»

> «Det er lagt vekt på at de positive samfunnsøkonomiske konsekvensene er
> vurdert til å være betydelig større enn de negative, sier Sandberg»

Etterprøvd mot dataene: styringsgruppens sammenslåtte råd for PO7 for
2016–2017 er `10-30%`, lest av Tabell 1 i styringsgruppens 2018-kropp,
kolonnen `Råd 2017 For 2016–2017`. Moderat gir gult. Departementet satte
grønt.

Det er det eneste målte tilfellet der departementet fraviker rådets
kategori for et navngitt område — og det er også den eneste runden der
det KAN måles, av grunnen i
`docs/beslutninger/2026-09-09-styringsgruppens-rad-som-kilde.md`: fra
2020 finnes det ikke lenger noe sammenslått råd å måle mot.

Merk hvordan de to tingene henger sammen. Departementet oppgir ÉN gang en
avvikende avgjørelse med begrunnelse, i 2017. Fra 2020 oppgir det
sprikende områder og en «samlet vurdering» — uten at det finnes en
sammenslått anbefaling avviket kan måles mot. Det er ikke påstått her at
det ene forårsaket det andre.

## Uttrykkelig IKKE målt

Dette skal stå, og det skal ikke fylles inn med en antakelse:

**Om departementets lister for rundene 2022 og 2024 bygger på
OPPRINNELIGE eller REVIDERTE årsverdier, er ikke målt.**

Spørsmålet er reelt. For runde 2026 vet vi at listen bygger på den
reviderte 2024, fordi teksten gjengir den reviderte verdien. For 2022 og
2024 er det ikke undersøkt om ekspertgruppens senere kropper reviderte
noen av grunnlagsårene, og i så fall om departementets liste ble skrevet
før eller etter.

Det er målbart — 2021-kroppen reviderer 2020, og ekspertgruppens kropper
fra 2023 og senere kan ha revidert 2022 — men det er ikke gjort, og
notatet påstår ingenting om det.

Tilsvarende: **det er ikke målt om departementets lister stemmer med
ekspertgruppens kropper i det hele tatt.** For runde 2020 stemmer
departementets seks områder eksakt med styringsgruppens 2018-2019-kropp,
i begge retninger, på alle seks. For 2022 og 2024 er sammenligningen ikke
gjort.

## Et forbehold ved kroppene selv

Wayback-avtrykkene av 2020- og 2026-meldingene er henholdsvis ett år og
to måneder etter utgivelsen. `Memento-Datetime` er ARKIVETS
hentetidspunkt, ikke departementets utgivelse — CLAUDE.md 1b-7 punkt 2.
Kroppen kan ha vært endret i mellomtiden uten at vi ser det.

For 2022- og 2024-meldingene er avtrykket samme dag som utgivelsen, og
forbeholdet er da lite.

## Hva som ville snudd dette

- **At departementet daterer ekspertversjonen.** Skriver en framtidig
  melding «i ekspertgruppens rapport for 2025, som oppdaterte vurderingen
  for 2024», er funnet borte for den runden — og forbeholdet skal da ikke
  føres videre mekanisk.
- **At en måling viser at 2022- eller 2024-lista bygger på en revidert
  årsverdi uten å si det.** Da er dette ikke et enkelttilfelle i 2026,
  men et mønster, og notatet skal skrives om fra «et forbehold ved
  lesing» til et funn om systematisk udatert gjengivelse.
- **At departementet oppgir et avvik fra rådet etter 2018.** I dag er
  PO7 i 2017 det eneste. Kommer det et til, er «bare runde 2018 har et
  målt avvik» feil.
- **At `diff.revisjon()` viser seg å ikke bevare begge påstandene for en
  kilde.** Hele grunnlaget for at dette er departementets problem og ikke
  vårt, er at vi har begge versjonene. Faller det, er notatet snudd på
  hodet.
