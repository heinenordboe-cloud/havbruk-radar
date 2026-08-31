---
dato: 2026-08-26
tittel: Full Stien-proxy forklarer ikke ekspertgruppens kategorier
status: gjeldende
commit: [fylles inn]
---

> **Lesningen av nullresultatet er omdefinert 31.08.2026.** Målingene i
> denne posten står uendret, men konklusjonen «hypotesen er ikke
> bekreftet» hvilte på at kategorien var en uavhengig fasit. Den er den
> ikke: ROC er en beregnet funksjon av de samme prediktorene, fra de
> samme registrene. Svak sammenheng måler derfor tap i en kjent kjede,
> ikke fravær av signal. Se
> [2026-08-31-hypotesen-omdefineres.md](2026-08-31-hypotesen-omdefineres.md).

## Hva som ble bestemt

Hypotesen «trafikklysets kategoriskift er forutsigbare fra offentlige
data» er testet med alle tre leddene i Stien-formelen og **ikke
bekreftet**.

Arbeidslinja legges om fra prediksjon til beskrivelse **inntil fasiten
bærer et kontinuerlig dødelighetsestimat**. Bindingen ligger på
MÅLTALLET, ikke på prediktoren, og derfor er neste steg ikke en finere
prediktor.

Lokalitetsnivå med avstandsvekting **utsettes** — ikke fordi det er
uinteressant, men fordi det ville brukt en økt på inngangssiden av en
måling som ikke kan lese resultatet. Se «Hvorfor lokalitetsnivå ikke er
neste steg».

## Hvorfor

Full proxy gir rho +0,703 mot kategorirang, svakere enn den delvise
(+0,761). N_fisk alene gir +0,349 og treffer 3 av 11 kategoriskift.

N_fisk er ikke breddegrad (rho −0,021) men er i stor grad PO-identitet:
variasjon mellom områder er 5,5× variasjonen mellom år innen område
(4,8× på relativ skala). Ren geografi oppnår |rho| 0,511 (PO-nummer)
uten å kjenne lus, temperatur eller fisk.

Innen PO: median +0,707, spenn −0,89 til +0,87 over 7 områder.

**Måltallets styrke er utilstrekkelig.** 52 celler med foregående år gir
11 skift. Eksakt 95 %-intervall (Clopper-Pearson) rundt 7/11 er
**0,31–0,89**; rundt 6/11 er det 0,23–0,83. De overlapper hverandre og
myntkastets 0,5. Enveis binomialtest når p < 0,05 først ved **9 av 11**
— som er nøyaktig reverseringskriteriet nederst, og det er ikke tilfeldig:
det er den minste verdien måltallet i det hele tatt kan uttale seg om.

Intervallet er dessuten for snilt. De 11 skiftene er fordelt på 7
produksjonsområder — PO8 bidrar med 3, PO2 og PO4 med 2 hver — så de er
ikke uavhengige, og effektiv n er lavere enn 11.

## Hvor skjør målingen er — målt, ikke antatt

Etter at utkastet til denne posten var skrevet, ble ekspertgruppens egen
rapport for 2020 lest. Den oppgir **et eget utvandringsvindu per
produksjonsområde**, og vårt faste uke 16–24 er ikke det samme vinduet:

| PO | deres vindu | overlapp med 16–24 |
|---|---|---|
| 1–2 | uke 17–23/24 | 100 % |
| 3–7 | uke 17–25/26 | 80–89 % |
| 8–10 | uke 21–28/30 | 40–50 % |
| 11–12 | uke 23–30/31 | 22–25 % |
| **13** | **uke 26–31** | **0 %** |

For PO13 er vinduet vårt ferdig FØR utvandringen begynner. Overlappen
faller monotont med breddegrad, altså er feilen konfundert med nøyaktig
den variabelen som slår alle prediktorene.

Erstattes det faste vinduet med deres, flytter tallene seg mye — og i
ulike retninger:

| prediktor | rho, fast 16–24 | rho, deres vindu | skift, fast | skift, deres |
|---|---|---|---|---|
| lusetall alene | +0,510 | **+0,716** | 6/11 | **4/11** |
| temperatur | +0,639 | **+0,309** | 6/11 | 7/11 |
| DELVIS proxy | +0,761 | +0,736 | 7/11 | 7/11 |
| FULL Stien-proxy | +0,703 | **+0,637** | 6/11 | 7/11 |
| lusetall, innen PO | median +0,354 | **median +0,000** | | |

Ett valg vi tok uten å måle noe, flytter rho for rått lusetall med
+0,21, halverer temperaturens, senker den fulle proxyens — og sletter
hele årsvariasjonssignalet innen PO. **Dette redder ikke hypotesen; det
viser at målingen ikke tåler vekten den ble bedt om å bære.**

Nullresultatet står, men det er ikke rent: det hviler på et vindu vi nå
vet er systematisk feil i nord.

**Ikke verifisert:** vinduene er lest maskinelt ut av PDF-en for 2020 og
brukt på alle årene 2018–2026. Om ekspertgruppen setter dem på nytt hvert
år, er det en tilnærming. De må leses av et menneske og føres som fasit
med kilde og sikkerhet før de brukes i et resultat.

## Hva som IKKE er vist

At offentlige data mangler signalet. Ekspertgruppen normaliserer ved
hydrodynamisk spredning langs utvandringsrute, ikke per
produksjonsområde. PO-aggregering kan ødelegge et signal som finnes på
lokalitetsnivå. Analysen skiller ikke mellom de to forklaringene.

At nullresultatet er robust. Vindumålingen over viser det motsatte: det
er betinget av minst ett valg som er feil, og som beveger tallene med
±0,2.

## Hvorfor lokalitetsnivå ikke er neste steg

Tre grunner, i rekkefølge:

1. **Bindingen er på utgangssiden.** 11 skift, intervall 0,31–0,89. En
   bedre prediktor endrer ikke at måltallet ikke kan skille +0,64 fra
   +0,76 fra myntkast. Ekspertgruppens rapporter inneholder
   KONTINUERLIGE estimater per PO — «HI virtuell smolt» oppgir vektet og
   uvektet gjennomsnittlig estimert dødelighet, «HI smittekart» oppgir
   arealandel over hver terskel. 65 celler med et kontinuerlig utfall er
   en langt større styrkegevinst enn noen prediktorforbedring.
2. **Avstandsvekting krever noe vi ikke har.** Lus og temperatur finnes
   per lokalitet, men N_fisk gjør det ikke og publiseres ikke
   (KILDE-BIOMASSE punkt 9). Utvandringsruter finnes ikke i noe snapshot.
   Begge måtte antas, og en antatt rute inn i en måling som allerede
   beveger seg ±0,2 på et vindusvalg, gir presisjon ingen kan lese.
3. **Det billige valget er ikke tatt ennå.** Vinduet per PO er 13 rader
   i en fasitfil med proveniens, samme mønster som
   `ekspertgruppen-po-kategori.csv`. Det retter en kjent, målt,
   breddegradskonfundert feil. Det skal gjøres uansett hva man mener om
   hypotesen.

Rekkefølge for neste økt: (1) vindu per PO som fasit, (2) kontinuerlig
dødelighetsestimat som fasit, (3) deretter — og bare hvis 1 og 2 ikke
avgjør saken — lokalitetsnivå.

## Hva som ville snudd det

- Et måltall med flere bevegelser enn 11 over perioden, eller et
  kontinuerlig dødelighetsestimat i stedet for tre kategorier
- Lokalitetsnivå med avstandsvekting som gir rho innen PO med spredning
  som ikke krysser null
- Kategoriskift truffet over 9 av 11 — terskelen der en enveis
  binomialtest først når p < 0,05

## Et forbehold som følger med kontinuerlig fasit

Vinduet og dødelighetsestimatet kommer fra samme ekspertgruppe som
kategorien. Å importere deres modellvalg gjør proxyen mindre uavhengig
av deres konklusjon. Det er ikke sirkulært i skadelig forstand — vinduet
er en antakelse om laksesmoltens biologi, ikke utledet av
dødelighetsestimatet — men det skal stå at vi da måler hvor godt
offentlige data reproduserer deres modell, ikke hvor godt de beskriver
sjøen.

## Kjøringen posten hviler på

`analyse/lusepress_mot_fasit.py`, kjøringslogg
`analyse/ut/lusepress.kjoring.log`. Følsomhet for biomasseversjonen kjørt
som egne kjøringer (`--biomasse-versjon forste` og `2`): rho for full
proxy uendret på +0,703, N_fisk +0,349 → +0,353. Konklusjonen avhenger
ikke av hvilken av Fiskeridirektoratets to påstander om fortiden som
leses.
