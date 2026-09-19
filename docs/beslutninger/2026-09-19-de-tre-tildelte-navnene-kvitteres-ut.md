---
dato: 2026-09-19
tittel: De tildelte navnene beholdes og kvitteres ut — én verdi i ett felt, ikke prøven
status: besluttet
commit: [fylles inn]
---

# De tildelte navnene beholdes, og kvitteringen navngir hver verdi

**Bestemt:** De historiske tildelingsnavnene i `tildelt_navn` beholdes i
publisert output, og de kvitteres ut som ENKELTFUNN i
`data/kvitteringer/2026-09-19.json`. Kvitteringen er en påstand om at
funnet er forstått — ikke en bryter som gjør prøven stille. Dukker en ny
verdi opp i samme felt, har den ingen kvittering, og porten blokkerer.

Dette er kategori 2 fra
[2026-09-18](2026-09-18-changeloggens-persondata-ligger-stille.md), det
siste som sto åpent før publisering.

**Tallet er TRE, ikke fire.** Det er den ene korreksjonen mot slik saken
ble lagt fram, og den er målt — se punkt 2.

---

## 1. Hvorfor de beholdes

Sektorpåstanden om disse verdiene hviler på **siste ord i en
navnestreng**, ikke på en klassifisering fra registeret. Målt 18.09.2026:

| | |
|---|---|
| `tildelt_orgnr` i vårt enhetsregister-snapshot | **0 av 3** (av 1743 entiteter) |
| `organisasjonsform` for dem noe sted i våre data | **ingen** |
| `institusjonell_sektorkode` for dem | **ingen** |
| tildelingsår | 1978, 1983, 1987 |
| eier noe i dag | 0 tillatelser, alle tre |
| raden de står på | `organisasjonsform = AS` |

Navne-endelsen stemmer med registerets `organisasjonsform` i **1669 av
1669** tilfeller der begge finnes. **Men den målingen har ingen
positive:** lesedøra har fjernet hver DA/ANS/PRE fra populasjonen, og 0
entiteter i den heter noe på DA/ANS/PRE. Prøven er altså validert bare
der svaret ikke betyr noe — formen CLAUDE.md 1b-2 advarer mot, og den
samme syntaktiske prøven på et semantisk spørsmål som
`core/persondata.py` er skrevet for å avvise.

**Om de peker på levende mennesker er ikke målbart med dagens kilder.**
Vi vet ikke om foretakene er oppløst, når det eventuelt skjedde, eller om
organisasjonsformen var `ANS` i 1978 — endelsen er navnet, ikke formen.
Av hele kolonnen er **407 av 694** distinkte `(tildelt_orgnr,
tildelt_navn)`-par ukjente for oss.

Verdiene står som historiske tildelingsopplysninger på rader som selv er
AS, og entiteten de navngir er ikke part i raden.

## 2. TRE saker, ikke fire — og hvorfor det er viktig

Saken ble lagt fram som «14 tildelt_navn, fire distinkte navn». Målt over
alle 1782 sider:

    tildelt_navn  #2a539a   12 forekomster paa 12 sider     kvittert
    tildelt_navn  #355ceb    1 forekomst   paa  1 side      kvittert
    tildelt_navn  #5dd7a3    1 forekomst   paa  1 side      kvittert
    tildelt_navn  #28ed65    1 forekomst   paa 11593        IKKE kvittert
    eier_navn     #28ed65    1 forekomst   paa 11593        IKKE kvittert

De 14 som beholdes er **12 + 1 + 1, altså tre distinkte navn**. Det
fjerde distinkte navnet er partrederiets, og det står på 11593 i BEGGE
kolonnene — som dagens eier og som opprinnelig tildelt, fordi
`eier_orgnr == tildelt_orgnr` for den tillatelsen.

Det er derfor ikke kvittert. Å kvittere det ville vært å kvittere ut
nøyaktig den saken som løser seg selv ved neste `eierskap`-kjøring, og
kvitteringen ville stått igjen som en levende påstand om et funn som ikke
finnes. Se punkt 5.

## 3. Kvitteringen er en påstand, ikke en bryter

Samme form som `health.godta_volum()`: ikke et flagg, men en verdi
skrevet til en fil som committes. Git-loggen sier når, fila sier hvorfor
og av hvem.

**Den kvitterer ut ETT FUNN, aldri et SLAG.** Nøkkelen er `(felt,
signaturen til den enkelte verdien)`:

    kvittert: personform              hele prøven er død. Et femte navn
                                      passerer i stillhet.
    kvittert: (tildelt_navn, #2a53..) nøyaktig denne verdien i nøyaktig
                                      dette feltet.

Det er samme skille som `godta_felt()` mot `godta_volum()`: to
kvitteringer for to spørsmål, framfor én som svelger begge.

For at et funn skal KUNNE kvitteres slik, måtte prøven attribuere det.
Fram til i dag meldte `personform` bare at «ordet ANS finnes i fila».
Verdicellene i eierskaps- og overføringstabellene bærer nå `data-felt`,
og en kode inne i en feltmerket navneverdi attribueres til `(felt,
verdi)`. Det ga en skjerping på siden av kvitteringen: `DA` som siste ord
i et navnefelt felles nå, der tekstprøven ikke kunne felle den fordi `DA`
er dekar i 748 rader.

### Rapporten bærer signaturen, ikke navnet

`--rapport` teller kvitterte funn **hver kjøring**, og porten skriver dem
alltid — også ved exit 0:

    Kvitterte funn i denne kjøringen: 14   (3 kvitteringer finnes i …)
        12x  tildelt_navn «W W» 10 tegn #2a539a sig=2a539ae1  [2026-09-19 …]
         1x  tildelt_navn «W W» 12 tegn #355ceb sig=355ceb1f  [2026-09-19 …]
         1x  tildelt_navn «W W W» 15 tegn #5dd7a3 sig=5dd7a3c0 [2026-09-19 …]

**«Porten er grønn» kan derfor aldri bety «ingen funn».** Det var det
tyngste argumentet mot en blokkerende vakt 15.09 — at et grønt bygg gir
falsk trygghet — og det er denne tellingen som svarer på det.

### Fila ligger i DATAREPOET

Kvitteringen navngir verdien ordrett, og da kan den ikke ligge i
kodrepoet. `2026-08-18-repoene-er-private.md` sier at kodrepoet kan
åpnes «den dagen det trengs», at commit-historikken følger med, og at
**offentlig ikke kan gjøres ugjort**. En fil med tre
mulige-persondata-navn i kodrepoets historikk ville vært en tikkende
utgave av nettopp det regel 3 forbyr.

Datarepoet er privat fordi det ER historikken, og det er samme rom som
snapshotene navnet alt står i. Porten trenger heller ikke navnet: den
slår opp på signaturen, som den regner ut av det den finner i utputtet.
Navnet står i fila for mennesket som skal etterprøve kvitteringen, og
signaturen kontrolleres mot det — en kvittering som oppgir navn A og
signaturen til navn B ville kvittert ut et funn ingen har lest.

## 4. Verifisert ved å plante

Mot ekte output, med kvitteringen på plass:

    urørt side (den kvitterte saken)      1 funn, 1 kvittert,  0 ukvitterte  exit 0
    PLANTET femte verdi i tildelt_navn    3 funn, 1 kvittert,  2 UKVITTERTE  exit 1
    KONTROLL: kvittert verdi flyttet
    til mottaker_navn                     1 funn, 0 kvitterte, 1 UKVITTERT   exit 1

Den andre linja er kravet: en ny verdi i samme felt feller porten, mens
den kvitterte står. Den tredje viser at kvitteringen er bundet til
FELTET også — `tildelt_navn` er en historisk tildelingsopplysning,
`mottaker_navn` er noe annet, og de to er ikke samme påstand om verden.

En kvittering som ikke traff noe funn rapporteres også, hver kjøring. En
kvittering for noe som ikke finnes lenger er ikke farlig, men den er
røte: den ser ut som en levende påstand og dekker ingenting. Veien ut er
`status: "trukket"` i en ny fil — filene er append-only, og en trukket
kvittering skal kunne leses i ettertid.

## 5. Porten gir IKKE exit 0 i dag, og det er riktig

Målt etter kvitteringen: **14 funn kvittert, 2 ukvitterte, exit 1.** De to
er partrederiet på 11593.

Det var ventet at porten skulle bli grønn her. Den blir det ikke, og
grunnen er at partrederiet fortsatt står i nyeste `eierskap`-snapshot
(14.09), der det opptrer i to kolonner. Filteret som fjerner det er
verifisert å virke — dagens kode dropper `H-FJ-0018` helt når
arkivkroppen fra 14.09 spilles gjennom `parse()` — men **snapshotet er
fra to dager før grensa flyttet seg**, og `min_dager_mellom = 7` gjør at
neste `eierskap`-henting er tidligst 21.09.

Tre veier, og valget er tatt:

1. **Vent på neste kjøring.** Da forsvinner begge funnene av seg selv, og
   porten gir exit 0 uten at noe er kvittert. **Valgt.**
2. Kvitter partrederiet også. Avvist: det ville kvittert ut en sak som
   opphører av seg selv, og etterlatt en kvittering som dekker ingenting.
3. Tvinge en henting nå. Avvist: `min_dager_mellom` er ikke i veien for
   noe som helst her, og en ekstra henting for å gjøre en port grønn er
   å endre dataene for å endre målingen.

At porten står rød i to dager er ikke en kostnad: publisering er ikke
tidskritisk, og CLAUDE.md regel 5 gjelder INNSAMLING, ikke publisering.

## Hva som ville snudd det

- **Et Brreg-oppslag på historiske organisasjonsnumre.** Dette er det
  viktigste, og det er en konkret, målbar vei ut. Brreg beholder oppløste
  enheter, så et oppslag ville gitt `organisasjonsform` og
  `institusjonell_sektorkode` for alle tre — og for de **407** av 694
  distinkte tildelingsparene som i dag er ukjente for oss. Da er
  spørsmålet ikke lenger «hva ser navnet ut som» men «hva sier registeret»,
  og kvitteringen skal trekkes samme dag: viser oppslaget sektor 2300,
  skal verdiene filtreres, ikke forklares. Veien er alt beskrevet i
  `2026-09-02-eierskapshistorikk-backfill.md` og delvis bygget i
  `fa35000` (`brreg_form`) — den brukes på mottakere i historikken, ikke
  på tildelte eiere i den ukentlige serien.
- **At en av de tre viser seg å være et levende ANS med identifiserbare
  deltakere.** Da er det ikke en historisk opplysning, og kvitteringen
  gjelder en påstand som ikke holder.
- **At `tildelt_navn` begynner å bety noe annet enn «hvem fikk
  tillatelsen første gang».** Kvitteringen er bundet til feltet fordi
  feltet bærer betydningen. Endrer kilden hva feltet inneholder, gjelder
  ikke begrunnelsen lenger.
- **At antallet vokser.** Tre verdier er en liste et menneske kan gå god
  for. Blir det tretti, er det ikke lenger enkeltfunn som er forstått —
  det er et mønster, og da skal spørsmålet stilles på nytt som «skal
  `tildelt_navn` vises i det hele tatt», ikke som en lengre kvittering.

**Ville IKKE snudd det:** at et av navnene ser ut som et personnavn. Det
er nettopp prøven som er målt verdiløs alene — 1278 av 1807 entiteter
treffer en navneform-prøve, og 1196 av dem er AS.
