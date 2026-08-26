# Forslag: hvordan PERSONFORMER kan lagres slik at et resultat vet
# hvilken filtrering som gjaldt

**Ikke bygget.** Dette er valget presentert med avveininger, til
avgjørelse. Ingenting i `core/persondata.py` er endret.

## Problemet, presist

`core/persondata.PERSONFORMER` er `frozenset({"ENK"})`, og den virker ved
**lesing** — `snapshot._les()` kaller `fjern_personformer()` hver gang et
snapshot åpnes. Det er med vilje: de 34 enkeltpersonforetakene i
snapshotene fra 16.–17.08.2026 ligger fysisk på disk, filene er
append-only, og filteret er det eneste som holder dem ute.

Konsekvensen er at lista **endrer hva et gammelt snapshot inneholder**.
Utvides den til `{"ENK", "DA", "ANS"}` i morgen, leser hver eneste
analyse av 2018 færre entiteter enn den gjorde i går — og ingenting i
changeloggen, i snapshotet eller i filnavnet sier at noe skjedde. Det er
samme klasse som F9 (utvalget), F10 (feltnormalen) og F14
(løpenummeret): en verdi utenfor dataene avgjør hva de betyr.

Regel 1b-3 stiller prøven: *kan et snapshot alene svare på hva denne
verdien var da raden ble skrevet?* Svaret er nei, og CLAUDE.md fører
allerede `persondata.PERSONFORMER` opp som et kjent, villet unntak.

Kjøringsloggen fra 26.08.2026 lukker halve hullet: hver analysekjøring
fører lista slik den var. Et RESULTAT vet nå hvilken filtrering som
gjaldt. Et SNAPSHOT vet det fortsatt ikke, og et resultat fra før loggen
fantes vet det ikke.

## Hva som gjør dette vanskeligere enn `utvalg`

`utvalg` løses av 1b-3 uten videre: stemple verdien på raden ved
skriving, ferdig. Her kolliderer to krav som begge er ekte:

- **Reproduserbarhet** vil at et gammelt snapshot skal lese likt i dag
  som i fjor. Det peker mot å FRYSE filtreringen på skrivetidspunktet.
- **Personvernet** vil det motsatte. Oppdager vi at DA og ANS også er
  fysiske personer, skal de ut av **alle** snapshots ved neste lesing —
  særlig de gamle. En frossen filtrering ville bevart utleveringen.

De to kan ikke begge få fullt gjennomslag. Personvernet vinner; det er
ikke en avveining mellom to like hensyn. Spørsmålet er hva
reproduserbarheten kan få i stedet.

---

## Alternativ A — la lista ligge i kode, og la kjøringsloggen føre den

*Dette er tilstanden i dag, etter 26.08.2026.*

`Kjoringslogg` fører `personformer ENK` uten at analysen ber om det,
fordi lista virker inne i lesedøra loggen eier.

- **For:** null risiko, allerede på plass, og løser det spørsmålet som
  faktisk ble stilt — «hvilken filtrering lå bak *dette resultatet*».
- **Mot:** løser ikke retroaktiviteten. Et snapshot kan fortsatt ikke
  svare for seg selv, og et resultat produsert før loggen fantes — alt
  fra før 26.08.2026 — er fortsatt ikke etterprøvbart.
- **Mot:** en logg er ikke en vakt. Ingenting hindrer at lista utvides
  mellom to kjøringer uten at noen ser det; loggene skiller seg, men
  bare hvis noen sammenligner dem.

## Alternativ B — stemple filtreringen på raden ved skriving

En `personformer`-kolonne i `SCHEMA`, satt av `stempl()` som `utvalg`.

- **For:** ordrett 1b-3, og mekanikken finnes fra før.
- **Mot, og det er avgjørende:** kolonnen ville svart på feil spørsmål.
  Den sier hvilken liste som gjaldt da raden ble SKREVET, mens
  filtreringen skjer når raden LESES. En analyse i 2028 av et snapshot
  fra 2026 ville sett stempelet `ENK` og lest med 2028-lista. Stempelet
  ville vært sant og likevel villedende — den verste formen, og formen
  1b-2 handler om: et felt som *ligner* svaret.
- **Mot:** koster en kolonne på hver rad i all framtid for en opplysning
  som allerede finnes i git.

## Alternativ C — versjonert liste, og lesingen bruker den som gjaldt

`data/personformer/<dato>.json`, append-only som `feltnormal/`.
`snapshot._les()` slår opp hvilken liste som gjaldt da snapshotet ble
hentet, og bruker den.

- **For:** full reproduserbarhet. Et snapshot leser likt for alltid.
- **Mot, og det er diskvalifiserende:** det fryser personvernfilteret på
  den historiske verdien. Oppdager vi at en form er en fysisk person,
  ville nettopp de gamle snapshotene — de som allerede inneholder radene
  — fortsatt utlevert dem. Reproduserbarhet kjøpt for personvern er ikke
  en avveining vi har lov til å gjøre.
- **Mot:** flytter en juridisk vurdering fra kode til en datafil, tvert
  imot begrunnelsen i `core/persondata.py` for at den ikke ligger i
  `config.yml`.

## Alternativ D — lista er et LAVVANNSMERKE, og bare den kan bevege seg

Lista blir ren kode som i dag, men får to ting:

1. **En monotonivakt.** `PERSONFORMER` kan bare VOKSE. En form som er
   fjernet fra lista krever en skrevet kvittering — samme mekanikk som
   `feltnormal.gulv` og `volum_referanse`, og samme begrunnelse: en
   referanse som kan flytte seg begge veier stilltiende, godtar
   degradering i sakte film. Vakten er en test som leser lista i git og
   feller en innsnevring uten kvittering.
2. **Utvidelsen er en HENDELSE.** Når lista vokser, skrives en linje i
   changeloggen — `change_type = "vernutvidelse"`, ved siden av
   `utvalgsutvidelse` og `revidert`. Den er ikke bevegelse i sjøen og
   telles ikke som aktivitet, men den er synlig, og den er datert.

Reproduserbarheten blir da ikke absolutt, men **retningsbestemt og
kjent**: en analyse kjørt på nytt i 2028 kan bare gi FÆRRE entiteter enn
den ga i 2026, aldri flere, og kjøringsloggen sier hvilken liste hver av
dem hvilte på. En forskjell mellom to resultater kan dermed alltid
tilskrives enten data eller en datert vernutvidelse.

- **For:** løser det som kan løses uten å ofre personvernet, og gjør
  retningen til en egenskap noen kan regne med.
- **For:** vakten er den delen som mangler i A. En logg forteller; en
  vakt hindrer.
- **Mot:** koster en ny `change_type` og en ny vakt, og
  monotonivakten er ikke gratis riktig — den må lese git-historikken
  eller en kvitteringsfil, og begge deler er en mekanisme til å
  vedlikeholde.
- **Mot:** løser fortsatt ikke resultater produsert før 26.08.2026.

---

## Anbefaling

**A er allerede der. D er neste steg, og C skal ikke bygges.**

Det avgjørende er å ikke la 1b-3 gjelde mekanisk her. Regelen sier at en
verdi som avgjør hva dataene betyr skal lagres sammen med dem — men den
er skrevet for verdier der det å fryse dem er riktig. Personvernfilteret
er ikke en slik verdi: det skal virke framover OG bakover, og da er det
ikke reproduserbarheten som skal gi etter, men målet om at den skal være
*absolutt*.

## Hva som ville snudd det

- Blir `PERSONFORMER` noen gang **snevret inn** — en form tas ut fordi
  vurderingen var feil — er A alene ikke nok, og D-vakten er ikke en
  formalitet lenger. Da må den bygges før innsnevringen skjer, ikke
  etter.
- Kommer det en kilde der filtreringen må skje ved SKRIVING og ikke ved
  lesing — fordi rådataene ikke kan arkiveres i det hele tatt — er B
  riktig for den kilden, og de to mekanismene må sameksistere.
- Blir de gamle snapshotene fra 16.–17.08.2026 en dag slettet eller
  skrevet om, faller hele grunnen til at filteret ligger i leseveien, og
  hele dette valget skal tas på nytt.
