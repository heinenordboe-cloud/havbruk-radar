---
dato: 2026-09-15
tittel: Publiseringsvakten blokkerer, den varsler ikke — og prøven er en hviteliste
status: besluttet 2026-09-16
commit: [fylles inn]
---

## Hva dette er

Grunnlaget ble skrevet 15.09 med avveiningen åpen. **Avgjort 16.09.2026:**

1. **Porten BLOKKERER.** `python publiseringsvakt.py <mappe>` gir exit 1
   ved funn, og publiseringssteget stopper på den. Ikke testsuiten, ikke
   innsamlingen — se punkt 2 for hvorfor den skillelinjen er absolutt.
2. **`--rapport` teller de filtrerte HVER gang.** Ikke bare når noe er
   galt. Argument 3 mot blokkering — at en grønn vakt kan gi falsk
   trygghet — er ikke løst av å velge varsling; det er løst av at
   rapporten alltid sier hvor mange personer som ble holdt ute, og av at
   vakten selv skriver hva den ikke dekker.

Resten av notatet står som det ble skrevet 15.09, med to tillegg merket
**[16.09]**.

## 1. Hva vakten er, og hvorfor filteret ikke holder

`core/persondata.py` beskytter to steder: `fetch()` holder personformene
ute av rå-arkivet, `snapshot._les()` holder dem ute av alt som leses.
Begge virker på DATAENE.

Ingen av dem beskytter en GENERATOR. En funksjon som leser et filtrert
snapshot og skriver HTML kan sette sammen felter på en måte ingen av
filtrene ser — en tabell over største eiere, en tooltip med orgnummer, en
CSV ved siden av sida. Filteret har gjort jobben sin, og persondataene er
der likevel, satt sammen av biter som hver for seg var greie.

`publiseringsvakt.py` gransker derfor UTPUTTET.

### Prøven er en hviteliste, ikke et mønsterforbud

Oppgaven ba om «ingen fil skal inneholde `\b\d{9}\b`». Den prøven er målt
ugjennomførbar 15.09.2026:

| kilde | ni-sifrede tall |
|---|---:|
| `enhetsregisteret` | 1807 `entity_id` som ER orgnumre |
| `eierskap` | 2953 `eier_orgnr` + 2939 `tildelt_orgnr` |
| `eierskap_historikk` | 91 `mottaker_orgnr` |
| `enhetsregisteret` | 32 `aksjekapital` + 26 `antall_aksjer` som har ni siffer og ikke er orgnumre |

En side som viser ett eneste selskap ville feilt. **Et forbud som må slås
av for å publisere, blir slått av.**

Prøven er derfor snudd: hvert ni-sifret tall i utputtet skal finnes igjen
blant orgnumrene i de FILTRERTE snapshotene. Da avgjør proveniensen og
ikke mønsteret, og et orgnummer som kom inn en annen vei enn gjennom
`snapshot._les()` har ingen steder å gjemme seg.

Det er samme inversjon som gjør `test_ingen_leser_snapshots_utenom_les`
mulig: én dør, og alt som ikke kom gjennom den er et funn. Og det er
nøyaktig det ni-siffer-prøven fra 16.08 ikke kunne: den sa «alle
entity_id er ni siffer, altså selskapsdata» — syntaktisk der spørsmålet
var semantisk, og et ENK har ni siffer som et AS.

### Tre prøver, og hva de ikke dekker

| prøve | fanger | dekker IKKE |
|---|---|---|
| `ukjent_orgnr` | ni-sifret tall utenfor hvitelista | orgnr formatert som desimaltall |
| `personform` | `ENK` som organisasjonsform | persondata uten etiketten |
| `ukjent_navn` | navnestreng utenfor hvitelista | navn generatoren ikke MERKER som navn |

Ingen later som de er uttømmende. En vakt som lover mer enn den kan
holde, er verre enn ingen vakt, fordi den blir trodd.

### To ting målingen mot ekte data endret

**Desimaltall.** Første utkast brukte `\b\d{9}\b` og fant ett funn i
`oversikt.html` — som var falskt. `\b` står mellom siffer og punktum, så
mønsteret traff heltallsdelen av «96697320.109», biomasse i kilo. Tallet
matches nå som token. Hullet det åpner — et orgnummer skrevet
«912345678.0» blir ikke sett — står som en egen test.

**Rapporten var selv en lekkasje.** Verifiseringen mot et ekte ENK viste
at et navn på 15 tegn gikk uavkortet i rapporten. Byggelogger i et
offentlig repo er offentlige, så en vakt som skriver det lekkede navnet
til loggen har FLYTTET lekkasjen — samme feil som changeloggen gjorde da
kildefilteret kom uten lesefilteret, og 699 rader med navn havnet i
`data/changelog/2026-08-24.parquet`. Rapporten gir nå form, lengde og en
kort signatur: nok til å finne navnet i fila, ikke nok til å være det.

## 2. Skal den BLOKKERE? Avveiningen

### For blokkering

**1. Skaden er ikke reversibel.** Et publisert orgnummer er indeksert av
søkemotorer i løpet av timer og ligger i arkiv etterpå. Å ta ned sida
fjerner ikke kopiene. Dette skiller seg fra alt annet i repoet: et
feilberegnet celletall kan rettes, en publisert hjemmeadresse kan ikke.

**2. Repoet har prøvd varsling før, og det holdt ikke.** Åpningen 16.08
hvilte på en kontroll som sa «ingen persondata». 34 ENK lå i hvert
snapshot i fem dager, med gateadresse i arkivet, mens repoet var
offentlig. Kontrollen var ikke fraværende — den var ikke bindende for noe.

**3. En advarsel i en byggelogg leses ikke.** `docs/beslutninger/
2026-08-31-tilsyn-feiler-ikke-jobben.md` slo fast at datakvalitetsvarsler
ikke skal felle den ukentlige jobben, nettopp fordi en status som er rød
av grunner som ikke er denne ukas problem, slutter å bli lest. Den
begrunnelsen peker motsatt vei her: dette varselet ER alltid denne ukas
problem, og det nullstilles ikke av seg selv.

**4. Kostnaden ved en falsk alarm er lav og synkende.** Publisering er
ikke tidskritisk — nettsiden er en visning av data som alt er samlet inn,
og CLAUDE.md regel 5 gjelder INNSAMLING, ikke publisering. En dag uten
oppdatert nettside koster ingenting som ikke kan hentes inn.

### Mot blokkering

**1. En vakt som feiler feil, blir slått av.** Dette er det tyngste
argumentet, og det er ikke hypotetisk: første kjøring mot ekte output ga
ett falskt funn. Hadde den vært blokkerende den dagen, ville første
reaksjon vært å legge inn et unntak — og et unntak lagt inn under press
er sjelden smalt.

**2. Hvitelista kan bli foreldet av noe som ikke er en feil.** Den bygges
av NYESTE snapshot per kilde. En visning som med rette viser et selskap
som forsvant ut av registeret forrige uke, blir et funn. Innstrammingen
er bevisst, men den betyr at vakten vil felle på legitime endringer i
visningen, ikke bare på lekkasjer.

**3. Den dekker ikke det som er verst.** De tre prøvene fanger det som
kom UTENOM døra. De fanger ikke de 46 personeksponerte som kom GJENNOM
den (punkt 3 under). En blokkerende vakt kan gi en falsk trygghet som er
dyrere enn en varslende: «bygget er grønt, altså er det ingen persondata
der» er nøyaktig setningen fra 16.08.

### Vurderingen

Argument 1 mot er reelt, men det taler for at vakten skal være PRESIS —
ikke for at den skal være uforpliktende. Målingen har alt strammet den én
gang, og hullene er skrevet ned som tester framfor oppdaget i drift.

Argument 3 mot er det som fortjener mest vekt, og det løses ikke av å
velge varsling. Det løses av at vaktens egen dokumentasjon sier hva den
ikke dekker, og at `--rapport` skriver de 46 hver gang. En vakt som teller
det den ikke stopper, gir ikke den falske tryggheten.

**Formen som ser ut til å balansere dem:** blokkerende, men bare på
publiseringsjobben — ikke på den vanlige testsuiten og ikke på
innsamlingen.

**Og porten kan ikke være en pytest-test.** Det ble forsøkt og målt
15.09.2026. `tests/conftest.py` setter `HAVBRUK_DATA_DIR` til en
engangsmappe før pytest importerer noen testmodul — sikkerhetsnettet som
gjør det umulig for en test å røre datarepoet. Følgen er at `RAW_DIR` er
TOM inne i suiten. Kjørt mot ekte `oversikt.html` ble hvitelista bygget
av ingenting, og hvert eneste orgnummer i fila meldte seg som
`ukjent_orgnr`. Porten var ikke streng — den var blind, og ville felt
hver publisering.

De to kravene er uforenlige, og begge er riktige:

* suiten skal ALDRI kunne lese eller skrive ekte data
* porten skal ALLTID lese ekte data

Porten er derfor en KOMMANDO med exit-kode, kjørt i publiseringssteget:

    python publiseringsvakt.py <mappe>      # exit 1 ved funn

`test_porten_kan_ikke_vaere_en_pytest_test` står i suiten som en sperre
mot at noen flytter den inn igjen — den måler at hvitelista faktisk er
tom der, framfor å anta det.

Innsamlingen røres ikke. Et feilende publiseringssteg skal aldri kunne
stoppe en ukes datainnsamling — den uka er tapt historikk, publiseringen
er ikke.

**Ikke avgjort:** om et funn skal kunne overstyres, og av hvem. En
`--godta`-vei ville speile `run.py --godta-volum`. Argumentet mot er at
volumkvitteringen gjelder et tall, mens denne ville gjeldt en person.

**[16.09] Valgt: blokkerende, uten overstyringsvei foreløpig.** Formen
over er den som ble valgt — exit 1 på publiseringssteget alene. At det
ikke finnes en `--godta` er ikke et standpunkt om at det aldri skal
finnes en; det er at ingen har hatt bruk for den ennå, og en luke som
lages før den trengs, lages uten å vite hva den skal slippe gjennom.

**[16.09] Argument 1 mot ble prøvd mot virkeligheten samme uke.** Da
grensa flyttet seg til sektor 2300, kom `DA` inn i `PERSONFORMER` — og
`DA` er også dekar, 748 rader `kapasitet_enhet`. Den brede prøven meldte
fire funn på den ene ekte genererte fila, alle falske. Det er nøyaktig
«en vakt som feiler feil, blir slått av», og det ble møtt som forutsatt:
prøven ble STRAMMET (tvetydige koder krever nå at feltnavnet står i
nærheten), ikke slått av. Se
[2026-09-16-grensa-gaar-ved-sektor-2300.md](2026-09-16-grensa-gaar-ved-sektor-2300.md)
punkt 5.

## 3. Målingen: hvem passerer filteret og er likevel en person?

Målt 15.09.2026 mot nyeste snapshot per kilde, lest gjennom
`snapshot._les()`. Aggregater — ingen navn, ingen numre.

### Filteret virker

**0 ENK** i noe snapshot. 2229 orgnumre og 8757 navn i hvitelista.

### Men 46 entiteter er personeksponert

| form | antall | SSB-sektor |
|---|---:|---|
| DA | 27 | 2300 |
| ANS | 18 | 2300 |
| PRE | 1 | 2300 |
| **sum** | **46** | av 64 DA/ANS/PRE totalt |

Alle 64 ligger i sektor 2300, «personlige foretak». 46 av dem har i
tillegg et navn på to eller tre ord uten bedriftsord — formen «Etternavn
og Etternavn DA». Deltakerne hefter personlig, og navnet navngir dem.

De publiseres med kommune, postnummer, næringskode, registreringsår og
`konkurs` — samme feltsett som gjorde de 34 ENK-ene til persondata.

> **[16.09] Dette avsnittet beskriver tilstanden fram til 16.09.2026.**
> Alle 64 filtreres nå, og målingen under er det grunnlaget beslutningen
> ble tatt på — ikke en beskrivelse av hva som ligger i snapshotene i
> dag.

**Dette er ikke et nytt funn. Det er det åpne spørsmålet i beslutningen
fra 22.08, nå med et tall på.** Den beslutningen har «[din vurdering]» der
det står om grensa skal gå ved formen ENK eller ved sektor 2300, og anslo
kostnaden til «32 DA, 31 ANS og 1 partrederi». Målingen i dag gir 27 + 18
+ 1 = 46 med personformet navn, av 64 totalt.

### Navneprøven alene er verdiløs, og det er målt

En prøve på navneform uten organisasjonsformen treffer **1278 av 1807**
entiteter — hvorav **1196 er AS**. Brreg skriver navn i VERSALER (1795 av
1807), så «NORDLAKS OPPDRETT AS» og «HANSEN OG OLSEN DA» har nøyaktig
samme form.

`core/persondata.py` sa dette på forhånd: «å filtrere PÅ NAVNET er
nøyaktig samme feil som ni-siffer-testen fra 16.08 — en syntaktisk prøve
der spørsmålet er semantisk.» Målingen bekrefter det med et tall, og det
er grunnen til at `personeksponert()` krever BÅDE formen og navnet.

### De andre kildene

| kilde | personeksponert | merknad |
|---|---:|---|
| `akvakultur` | 0 | 1782 lokalitetsnavn, alle stedsnavn |
| `eierskap` | 0 av 8 DA/ANS | ingen med personformet navn |
| `eierskap_historikk` | 0 | 91 mottakere, alle med juridisk suffiks |
| `enhetsregisteret` | 46 | se over |

`eierskap` har 114 entiteter uten `organisasjonsform` — filteret er blindt
for dem. Målt: de er `OrganizationalSection` (75), `Foundation` (26),
`Association` (10), `Municipality` (2) og `JointlyOwnedShippingCompany`
(1). Ingen fysiske personer.

### Svaret på spørsmålet

**Ja.** 46 rader i dagens snapshots passerer personformfilteret og bærer
en identifiserbar fysisk person — ikke fordi navnet ser slik ut, men
fordi organisasjonsformen sier at foretaket er en personlig
sammenslutning og navnet navngir deltakerne.

De felles ikke av vakten, og det er et valg og ikke en forglemmelse: å
felle ville avgjort det åpne spørsmålet fra 22.08 ved en vakt framfor ved
en beslutning. `--rapport` skriver tallet hver gang.

## 4. Åpent

To av fire punkter er avgjort 16.09.2026 og står igjen med svaret sitt,
ikke slettet — en leser som kommer hit fra en lenke skal se hva som ble
spurt om.

- ~~Blokkerende eller varslende~~ — **blokkerende**, på
  publiseringssteget alene. Se toppen av notatet.
- ~~Om grensa skal flyttes fra formen ENK til sektor 2300~~ — **flyttet**.
  Alle 64 filtreres, ikke bare de 46 med personnavn. Se
  [2026-09-16-grensa-gaar-ved-sektor-2300.md](2026-09-16-grensa-gaar-ved-sektor-2300.md).
  Følgen for dette notatet: tallet 46 i punkt 3 er en måling av en
  tilstand som ikke lenger finnes. `--rapport` leser nå 0
  personeksponerte, og et tall over 0 betyr at noe kom inn utenom
  `snapshot._les()`.
- **Fortsatt åpent:** om et funn skal kunne overstyres, og av hvem.
- **Fortsatt åpent:** `ukjent_navn` ser bare det generatoren MERKER som
  navn. Skal nettsidegeneratoren pålegges en merkekonvensjon, må det
  bestemmes før den skrives — etterpå er det en omskriving.
