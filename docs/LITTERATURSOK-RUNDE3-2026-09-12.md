# Litteratursøk runde 3 — 12.09.2026

Søk og én måling i eget arkiv. Ingen kilde bygget. `sources/`,
`data/raw/`, `analyse/` og fasit-CSV-en er urørt.

Runde én (`docs/LITTERATURSOK-2026-09-11.md`) og runde to
(`docs/LITTERATURSOK-RUNDE2-2026-09-12.md`) dekket Cristin, OpenAlex,
Semantic Scholar, NVA, Idunn via Crossref, MarIus 2018–2022,
Nasjonalbiblioteket og masteroppgavene. Det gjentas ikke her.

Denne runden gjør fire ting: retter påstand B mot eget arkiv (Del A),
åpner høringssvarene (Del B), henter Larsen 2025 (Del C) og leser de to
løse trådene fra runde to (Del D).

---

## Del A — påstand B er målt og rettet

**Dette er rundens viktigste resultat, og det er en måling, ikke et
søk.** Beslutningsnotatet er rettet; se
`docs/beslutninger/2026-09-09-styringsgruppens-rad-som-kilde.md`,
nytt avsnitt «Regelen finnes i tre formuleringer, og to av dem har en
betingelse».

### A.1 De tre formuleringene, ordrett

Alle tre er nå lest i original, to av dem i repoets eget arkiv.

**Styringsgruppen, 2018-2019-kroppen (17.11.2019), s. 6–7** —
`data/arkiv/styringsgruppen/2019-11-17.bin.gz`:

> «Der ekspertgruppens vurderinger for kategori av dødelighet for et
> område er forskjellig i 2018 og 2019 har styringsgruppen, **på lik måte
> som for rådet avgitt i 2017**, valgt en konservativ tilnærming for
> samlet vurdering av lakselusindusert dødelighet (Tabell 3).»

Ingen betingelse. Og gruppen sier selv at 2017-runden brukte samme regel.

**NFD, høringsnotat 2017** — Nasjonalbiblioteket, pliktmonografi
000046102:

> «Styringsgruppen har gjort en samlet vurdering for perioden 2016-2017,
> basert på lik vekting av årene. Der vurderingene er forskjellig for et
> område i de to årene **og usikkerheten er middels eller stor**, har
> styringsgruppen valgt en konservativ tilnærming …»

**NFD, pressemelding 30.10.2017** —
`data/arkiv/regjeringen-pressemeldinger/2017-10-30.bin.gz`:

> «Styringsgruppens råd er basert på lik vekting av årene. Der
> vurderingene er forskjellig for et område i de to årene **og
> usikkerheten er middels eller høy**, har styringsgruppen valgt en
> konservativ tilnærming. **Dette innebærer konkret at det er det året
> med høyest risiko for luseindusert dødelighet som har blitt førende
> for rådet.**»

Tre observasjoner:

1. `stor` og `høy` er samme grad i ekspertgruppens skala (liten /
   middels / stor). Avviket er leksikalsk.
2. Skillet går mellom **kilden** og **departementet**, ikke mellom
   2017-runden og 2019-runden. Styringsgruppen oppgir regelen uten
   betingelse i begge de kroppene som har den; departementet legger til
   betingelsen begge gangene det gjengir den.
3. Pressemeldingen er den eneste av de tre som sier hva regelen
   OPERATIVT gjør — «det året med høyest risiko … førende for rådet».
   Det er samme observasjon Monsen 2021 gjør, fire år før ham, fra
   departementets egen penn.

**2018-kroppen sier ingenting.** Den restaterer 2016–2017-rådet i
Tabell 1, men bruker ikke ordet `konservativ` i det hele tatt — null
treff over tolv sider. Regelen for 2016–2017 finnes altså bare hos
departementet og i 2019-kroppens tilbakeblikk.

### A.2 2016–2017, målt av 2018-kroppens Tabell 1

**Tabell 1 har ikke usikkerhet per år.** Den har `Variasjon mellom
metoder` per år og ÉN felles kolonne `2016–2017 usikkerhet Ekspertgr.`
for paret. Spørsmålet «usikkerhetsgrad per år» har derfor ikke noe svar
for denne runden — det er en egenskap ved kilden, ikke ved uttrekket.

De fire sprikende områdene, ordrett:

| PO | 2016 | 2017 | `2016–2017 usikkerhet Ekspertgr.` | `Råd 2017 For 2016–2017` | verste år? |
|---|---|---|---|---|---|
| 2 | `10-30%` | `< 10 %` | **`Stor`** | `10-30%` | ja |
| 4 | `10-30%` | `> 30 %` | **`Middels`** | `> 30 %` | ja |
| 6 | `10-30%` | `< 10 %` | **`Stor`** | `10-30%` | ja |
| 7 | `10-30%` | `< 10 %` | **`Middels`** | `10-30%` | ja |

Ingen av de fire har `Liten`. Betingelsen er oppfylt i alle fire.

Til kontroll, de ni områdene som IKKE spriker: PO1, 3, 5, 8, 9, 10, 11,
12, 13. **Sju av dem har `Liten` usikkerhet** — PO1, 3, 8, 9, 11, 12 og
13 — men kategoriene er identiske i alle sju, så betingelsen blir aldri
utløst der. Mest slående er PO3: `> 30 %` begge år med usikkerhet
`Liten`, altså den høyeste dødelighetskategorien med den laveste
usikkerheten, og likevel ingen anledning for regelen til å virke.

### A.3 2018-2019, ordrett framfor «minst ett år»

Tabell 3 har usikkerhet PER ÅR. De seks sprikende områdene:

| PO | 2018 | usikkerhet 2018 | 2019 | usikkerhet 2019 | `Råd 2018-2019` | verste år? |
|---|---|---|---|---|---|---|
| 2 | `10-30%` | `Middels` | `< 10%` | `Middels` | `10-30%` | ja |
| 3 | `> 30%` | `Middels` | `10-30%` | `Middels` | `> 30%` | ja |
| 4 | `10-30%` | `Middels` | `> 30%` | `Middels` | `> 30%` | ja |
| 5 | `10-30%` | `Middels` | `> 30%` | `Middels` | `> 30%` | ja |
| 7 | `10-30%` | `Stor` | `< 10%` | `Stor` | `10-30%` | ja |
| 10 | `< 10%` | **`Liten`** | `10-30%` | `Stor` | `10-30%` | ja |

### A.4 Svaret på spørsmål 2

**Nei.** Det finnes ikke én celle, i noen av de to rundene, der
kategoriene spriker og usikkerheten er `Liten` gjennomgående.
Betingelsen blir derfor aldri motbevist — og aldri prøvd.

**PO10 i 2018-2019 er det nærmeste vi kommer, og den peker mot den
UBETINGEDE lesingen.** Usikkerheten er `Liten` i 2018 og `Stor` i 2019.
Leses departementets betingelse per år, faller PO10 utenfor den, og
rådet er konservativt likevel. Leses den om området samlet, er PO10
dekket, og betingelsen holder.

Kroppen peker selv på nettopp denne cella, i setningen rett foran
regelen:

> «… produksjonsområde 10, hvor sikkerheten varierer over to kategorier
> (fra liten til stor).»

Styringsgruppen så altså den splittede usikkerheten, nevnte den
uttrykkelig, og anvendte den konservative tilnærmingen uansett. Det er
et indisium, ikke et bevis: PO10 skiller de to LESINGENE av
betingelsen, ikke betingelsen fra fraværet av den.

### A.5 Hva påstand B nå sier

Ordrett som rettet i beslutningsnotatet:

> Rådet er det verste av de to årene i alle ti sprikende cellene over
> to runder. Styringsgruppen oppgir regelen uten betingelse;
> departementet oppgir den med en betingelse om at usikkerheten er
> middels eller stor. Ingen celle i materialet skiller de to
> formuleringene fra hverandre.

Påstanden er ikke utvidet. «Ti av ti» står — det var aldri det som
var for bredt. Det som var for bredt, var å gjengi regelen som om det
fantes én formulering av den.

---

## Del B — høringssvarene

Runde to nådde null. Denne runden nådde **elleve dokumenter fra to
avsendere**, og fikk lest fem av dem. Ruten som virket var avsendernes
egne nettsider, slik du antok.

### B.1 Veterinærinstituttet — det beste stedet å lete

VI er ett av de tre instituttene **i** styringsgruppen. Instituttet
publiserer sine egne høringssvar på
`vetinst.no/rapporter-og-publikasjoner/faglige-vurderinger-og-horingssvar`.
Ti dokumenter om kapasitet/produksjonsområder ble lastet ned.

**Fem har tekstlag. Fem var skann uten tekstlag — de er nå OCR-et**
(se B.1b). Alle ti er dermed lest.

| dokument | dato | tekstkilde | treff på claim-termene |
|---|---|---|---|
| Kapasitetsjusteringer **2024** | 29.02.2024 | tekstlag (928 tegn) | 0 |
| Endring produksjonsområdeforskriften | 13.06.2023 | tekstlag (4328) | 0 |
| Endring i produksjonsområdeforskriften | 05.03.2021 | tekstlag (2422) | 0 |
| Nytt system for kapasitetsjusteringer | 20.09.2016 | tekstlag (14505) | 1 × `samlet vurdering` |
| samme, duplikat | 2016 | tekstlag (14505) | 1 × `samlet vurdering` |
| **Kapasitetsjusteringer 2021/2022** | **21.01.2022** | **OCR** (953) | 0 |
| **Kapasitetsøkning 2019-2020** | **05.12.2019** | **OCR** (5926) | 0 på termene, **men se B.1c** |
| Fleksibilitet i produksjonsområder | 09.01.2017 | OCR (4678) | 0 |
| Havbruk til havs / yttergrenser | — | OCR (10826) | 0 |
| Produksjonskapasitet for akvakultur | — | OCR (681) | 0 |

Termene: `styringsgruppe`, `ekspertgruppe`, `oddetallsår`,
`konservativ`, `sammenslå`, `lik vekting`, `begge år`, `de to årene`,
`samlet vurdering`, `to år`.

**Rundene 2022 og 2024 er begge «ingen kommentarer».** 2024-svaret:

> «Veterinærinstituttet har vurdert utkast til forskrift om
> kapasitetsjusteringer … i 2024. **Vi har ingen kommentarer til
> utkastet.**»

2022-svaret (OCR):

> «Veterinærinstituttet har vurdert forslag til forskrift om
> kapasitetsjusteringer i norsk lakse- og ørretoppdrett i 2021/2022.
> **Veterinærinstituttet har ingen kommentarer.**»

2024-svaret er undertegnet Edgar Brun og **Eirik Biering**. Biering er
medforfatter av Boxaspen, Biering & Næsje (31.08.2022) —
styringsgruppens egen vurdering av Trendgruppens rapport. Instituttet
som leverer en tredjedel av rådet, representert ved en av rådets
forfattere, har ingen merknader til hvordan rådet blir brukt — i de to
første rundene etter at rådskolonnen forsvant.

### B.1b Om OCR-en, og hva et OCR-nulltreff er verdt

De fem skannene er OCR-et med macOS' Vision-rammeverk
(`VNRecognizeTextRequest`, `.accurate`, språk `nb-NO` m.fl., sidene
rendret 3× via PDFKit). Verktøyet er skrevet for anledningen og ligger
i arbeidskatalogen, ikke i repoet.

**Dette er VÅR lesing av et bilde, ikke kildens tekst.** Skillet er det
samme som `docs/KARTLEGGING-STYRINGSGRUPPEN.md` gjør for de to
2017-kroppene, og det gjelder her også — men bruken er en annen: her
skal OCR-en avgjøre om et ord FINNES, ikke levere en verdi til `data/`.
Følgene:

- Et **nulltreff** er svakere enn et nulltreff fra et tekstlag. OCR kan
  tape et ord. Det er mindre alvorlig her enn ellers, fordi termene er
  lange og særpregede (`oddetallsår`, `konservativ`, `lik vekting`) og
  fordi sidene ellers leses rent — signaturene er det eneste som
  smadres (`8hyan bru`, `Kán Norkim`, `Ect Bg`).
- Et **treff** må kontrolleres mot bildet før det siteres. Sitatene
  under er gjengitt fordi de er sammenhengende og lesbare, men de er
  merket OCR, og skal leses i originalen før de brukes som belegg.
- Tellingen av `råd` måtte gjøres med ordgrense: `råd` er delstreng i
  `området`, og ga 12, 22 og 32 falske treff før det ble rettet. Med
  `\bråd\b` står det igjen **ett** ekte treff i alle fem, i vi7.

### B.1c Det ene som ikke er et nulltreff: VI, 05.12.2019

Dette er det nærmeste noe høringssvar kommer påstand D, og det er
**stopp-og-rapporter-verdig**.

Veterinærinstituttets svar av **05.12.2019** — tre uker etter
2018-2019-kroppen (17.11.2019), som bar den siste sammenslåtte
rådskolonnen — har en egen seksjon med overskriften
**«Høringsnotatavsnitt 2.1.1 Innledning og råd»**:

> «Her beskrives det hvordan man skal foreta produksjonsregulering
> dersom et gitt område **endrer kategori i 2-års perioden** som skal
> ligge til grunn for reguleringen. **Man skal da foreta en grundigere
> vurdering, se på enkeltfaktorer som temperatur og salinitet, og
> vurdere trender i datagrunnlaget.** Effekten som lakselus produsert i
> oppdrettsanlegg har på vill laksefisk er avhengig av svært mange
> enkeltfaktorer, og det er derfor en sterk forenkling å gi én eller få
> av faktorene avgjørende betydning.»

og videre:

> «Tolking av trender i datagrunnlaget må derfor være godt begrunnet,
> spesielt når resultatet kan bidra til en endring i kategori i
> trafikklyssystemet. Fra et miljøperspektiv vil en kunne komme i
> konflikt med «føre-var»-prinsippet dersom en positiv «trend» i
> lusesituasjonen over en toårsperiode bidrar til bedring i kategori med
> økt tillatt produksjon.»

**Hva dette gir, og hva det ikke gir.**

Det gir: et høringssvar som identifiserer den SPRIKENDE grenen
uttrykkelig, gjengir departementets metode for den — grundigere
vurdering, enkeltfaktorer, trender — og kritiserer den som en
forenkling og som en føre-var-risiko. Det er første gang i tre runder
at noen utenfor departementet skriver om den grenen i det hele tatt.

Det gir ikke: noen omtale av at styringsgruppen leverte et sammenslått
råd for nettopp den grenen. `styringsgruppe` forekommer **0** ganger i
svaret. VI kommenterer departementets egen metode, ikke rådsleddet.

**Og det skjerper D framfor å svekke den.** Høringsnotatet for runde
2020 beskrev altså allerede da den sprikende grenen som noe MYNDIGHETENE
skulle løse med en grundigere vurdering — samtidig som den sammenslåtte
rådskolonnen fantes og sa hva rådet var. De to eksisterte side om side i
2020, og departementet fravek rådet i tre områder det året (Fauchald
2020, fn. 107). Fra 2022 finnes bare departementets gren. Påstand D sier
nettopp at motparten forsvant, ikke at grenen gjorde det.

### B.2 Sjømat Norge

`sjomatnorge.no/wp-content/uploads/2023/06/230615-Horing-Produksjonsomradeforskriften.pdf`
— 8 sider, høringssvar 15.06.2023. **Null treff** på `styringsgruppe`,
`ekspertgruppe`, `oddetallsår`, `konservativ`, `sammenslå`, `lik
vekting`, `to år`, `begge år`.

### B.3 Miljøorganisasjonene — hypotesen holdt ikke

Du skrev at miljøorganisasjonene var mest sannsynlige, fordi de har
fagfolk som leser rådsdokumentene. De leser dem — men de angriper noe
annet.

**Felles høringsinnspill fra Naturvernforbundet, NJFF, Natur og
Ungdom, Redd Villaksen og Norske Lakseelver** til NOU 2023:23
(`naturvernforbundet.no/content/uploads/2024/01/59-23-…pdf`), 11 sider:

| term | treff |
|---|---:|
| `trafikklys` | **23** |
| `ekspertgruppe` | 3 (alle i litteraturlista, Vollset mfl.) |
| `styringsgruppe` | **0** |
| `oddetallsår`, `konservativ`, `sammenslå`, `lik vekting`, `begge år` | **0** |
| `to år` | 1 («hvordan de kommer til å bli de neste to årene», om unntaksvekst) |

Innholdet er en frontalkritikk av systemet — «Dagens trafikklyssystem
fungerer ikke etter hensikten» — men den retter seg mot
**grenseverdiene** og **indikatoren**, ikke mot rådsformen.

Samme mønster er dokumentert bakover i tid gjennom Nicholls' MarIus 506
(2018), som gjengir WWFs høringssvar (2016) s. 3–4 og Norske Lakseelvers
fagsjef Erik Sterud: begge angriper grenseverdiene og forholdet til
kvalitetsnormen for villaks. Ingen av dem nevner styringsgruppens
rådsform.

**WWFs egen høringssvarside** (gjennomgått i runde to) har ingen
høringssvar om kapasitetsjustering i det hele tatt.

### B.4 Hva som fortsatt ikke er nådd

Wayback ga i denne runden først treff og deretter **full nedetid** —
«Internet Archive services are temporarily offline», ikke rate-limiting.
Før den falt ut rakk jeg å hente den arkiverte høringssida for
2024-runden, og den gir nøyaktig hva som mangler:

- **60 høringsinstanser** er listet for 2024-runden alene, fra Agder
  fylkeskommune til Virke, med Greenpeace, HI, Fiskeridirektoratet,
  Veterinærinstituttet og WWF blant dem.
- Selve svarene ligger bak `?showSvar=true` på høringssida —
  `…/id3023357/?showSvar=true&consterm=&page=1&isFilterOpen=true`. Den
  URL-en har ingen Wayback-kopi (CDX: null treff).

Med fem runder à ~60 instanser er dette i størrelsesorden 300
dokumenter, hvorav jeg har lest fem.

---

## Del C — Larsen 2025 er hentet og lest

**Ruten du foreslo virket: NVAs `filelink`-mønster, det samme
`sources/ekspertgruppen.py` allerede bruker.**

    GET /publication/{pubId}/filelink/{fileId}
      -> {"type":"PresignedUriResponse","id":"https://nva-resource-storage-…s3…"}

Det løser problemet runde to ga opp på: Brage-instansene redirigerer til
NVAs SPA, og `/files/{id}` krever auth — men `/filelink/{id}` gjør det
ikke. Verdt å notere for framtidige hentinger.

**Mari Lie Larsen, *Evidence-based policymaking: Exploring the
effectiveness of salmon aquaculture [regulation]*, ph.d., Institutt for
biovitenskap (BIO), UiB, 2025.** 112 sider, hentet 12.09.2026.

| term | treff | | term | treff |
|---|---:|---|---|---:|
| `traffic light` | **261** | | `two years` | **0** |
| `expert group` | **126** | | `both years` | **0** |
| `trafikklys` | 54 | | `conservative` | **0** |
| `advice` | 63 | | `odd-numbered` | **0** |
| `ekspertgruppe` | 36 | | `oddetallsår` | **0** |
| `steering group` | 18 | | `socio-economic` | **0** |
| `mandate` | 18 | | `deviate` (ikke-statistisk) | **0** |

**Dette er det grundigste arbeidet som finnes om trafikklyssystemets
kunnskapsgrunnlag, og det berører ikke toårssammenslåingen med ett ord.**

Avhandlingen er en økologisk effektstudie — virker systemet etter
hensikten for villaksen — ikke en forvaltnings- eller rettsanalyse.
Styringsgruppen omtales i ett ledd:

> «These conclusions are then reviewed **biannually** by a steering group
> of scientists from the same institutions …»

Merk ordet `biannually`. Det er upresist for perioden etter 2020:
styringsgruppen har levert en ÅRLIG vurdering hvert år. Larsen beskriver
altså rådsleddet som toårig i en periode der det nettopp ikke lenger er
det — uten at hun tar opp spørsmålet.

**Og en rettelse til runde to:** de 9 `Fauchald`-treffene er **P.
Fauchald** (Per Fauchald, NINA-økolog), ikke Ole Kristian Fauchald.
Kontrollert: `Ole Kristian` 0, `Miljøprinsipper` 0, `Fauchald, O` 0,
`Fauchald, P` 9. Larsen siterer ikke Fauchald 2020. Siteringslista fra
runde to står uendret på 16 arbeider.

Larsen 2025 er dermed ikke lenger en dokumentert mangel. Den er lest, og
den er et nulltreff.

---

## Del D — de to løse trådene

### D.1 Mona Østvang Ådum, PrivIus 2021 — svakere enn runde to antydet

Hentet i sin helhet via samme `filelink`-rute. 118 sider.

**Mona Østvang Ådum, *Erstatning til fiskerettshavere for skader og
ulemper ved oppdrettsvirksomhet*, PrivIus, Institutt for privatrett,
UiO, 2021.**

| term | treff | | term | treff |
|---|---:|---|---|---:|
| `Fauchald` | 8 | | `konservativ` | **0** |
| `trafikklys` | 8 | | `sammenslå` | **0** |
| `styringsgruppe` | 6 | | `lik vekting` | **0** |
| `nedjuster` | 5 | | `to år` | **0** |
| `ekspertgruppe` | 1 | | `oddetallsår` | **0** |

**Hva hun faktisk bruker kolonnen til.** Henvisningen til
`Styringsgruppen (2019) s. 7` står i **fotnote 267**, og den bærer én
faktaopplysning i et privatrettslig resonnement om tålegrense og
erstatning:

> «267 Etter justeringene i 2020 kan dette gjelde i PO3, der det
> naturfaglige rådet tilsa en nedjustering i produksjonsområde 3 (rød,
> luseindusert dødelighet over 30 %), mens regjeringen tillot at
> produksjonskapasiteten ble opprettholdt (gul). Se Styringsgruppen
> (2019) s. 7 og Nærings- og fiskeridepartementet (2020).»

Det er samme PO3-funn som Fauchalds, fra samme side, hentet uavhengig —
men det er en **fotnote i en fotnote-funksjon**: den illustrerer at
påvirkningen kan være uakseptabel uten at kapasiteten settes ned. Hun
kommenterer ikke rådets form, og hun bruker ikke kolonnen som metode.

Hovedteksten hennes plasserer henne dessuten på Mellbyes side av D:

> «Det er opprettet en styringsgruppe som gir råd til departementet om
> kapasitetsjusteringer basert på dødeligheten innenfor hvert
> produksjonsområde. Rådene baserer seg på analyser … foretatt av en
> naturvitenskapelig ekspertgruppe. **Departementet foretar imidlertid
> selvstendige vurderinger av produksjonskapasiteten, og er ikke
> bu[ndet] …**»

**Følgen for påstand F:** Ådum er et ekte, uavhengig andre bein — samme
side, samme kolonne, uten å ha lest Fauchald for nettopp det punktet.
Men hun bærer mindre vekt enn runde to ga inntrykk av. Riktig
formulering er at kolonnen er brukt som faktagrunnlag i to publiserte
arbeider, tungt hos Fauchald og i en enkelt fotnote hos Ådum — og at
ingen av dem, og ingen av de 16 siterende arbeidene, nevner at den
opphørte.

### D.2 Hanna Nicholls, MarIus 506 (2018) 4.5.7.2 — argumentet i sin helhet

Hentet fra `sjorettsfondet.no/asset/journal/2018/506/Marius-506.pdf`,
150 sider. Seksjonen er kort — under én side — og lyder i sin helhet:

> **4.5.7.2 Er det en handlingsregel?**
>
> Trafikklyssystemet er ment å være en «handlingsregel». Departementet
> gir uttrykk for en viss grad av automatikk og forutsigbarhet i
> vurderingene: «Dersom resultatet er sammenfallende begge årene vil
> utfallet være forutsigbart og det legges ikke opp til noen
> vurdering».[fn 238: Meld. St. 16 (2014–2015) s. 49] Imidlertid vil jeg
> påpeke enkelte ting som kommer i veien for denne «automatikken»:
>
> Som pekt på tidligere, må departementets adgang til fritt å ta
> avgjørelser, tolkes i lys av lovens formålsbestemmelse om bærekraft,
> samt nml. § 7 og Grl. § 112. Og selv i situasjoner hvor man i et
> produksjonsområde går i «grønt», kommunene og fylkeskommunen som tar
> avgjørelsen om lokalitetsklarering. Ved en økt vekst kommer oppdrett
> også i konflikt med andre interesser, for eksempel med kystfiskere.
> Disse interessekonfliktene kan stå i veien for utvidet
> oppdrettsvirksomhet. Avslutningsvis åpner POF § 8 for at også andre
> miljøpåvirkninger kan integreres i handlingsregelen etter hvert, slik
> at oppdretterne etter hvert også må ta hensyn til andre
> miljøpåvirkninger.

**Runde to overdrev dette, og det rettes her.** Selve 4.5.7.2 handler om
det NEDSTRØMS leddet — fra farge til faktisk kapasitet — og ikke om
leddet fra råd til farge. Fire hindre, alle nedstrøms: rettslige rammer,
kommunal lokalitetsklarering, arealkonflikter, framtidige indikatorer.

Det OPPSTRØMS argumentet finnes, men et sted annet, ca. ti sider foran:

> «Dette innebærer at det ikke er en automatisk sammenheng mellom
> resultatet av modellene basert på naturvitenskapelige metoder og
> produksjonskapasiteten i et område. Mangelen på automatikk fremgår
> også av trinn 5, hvor det beskrives at «departementet fatter en
> beslutning»: **det er departementet som gjør en vurdering og bestemmer
> hvilken kategori miljøpåvirkningen i et område anses å være i.**»

Og — dette er det viktigste for D — hun setter opp togrenstrukturen
eksplisitt:

> «Hvis et område f.eks. har fått «grønt lys» to år på rad i årlige
> målinger, er det meningen at det skal være en slags automatikk i at
> det da blir vekst i området. **Hvis området derimot et år får rødt
> lys, for så å få grønt lys året etter, skal departementet foreta en
> vurdering.**»

> «At det ikke er «automatikk» i sammenhengen mellom resultatene av
> miljømålingene og justeringen av produksjonskapasitet vil på den ene
> siden gå ut over forutsigbarheten til oppdretterne, men på den andre
> siden **tillater det departementet å ta hensyn til hvordan utviklingen
> av miljøsituasjonen har vært i løpet av de to årene** …»

**Hva dette betyr for D.** Nicholls BENEKTER ikke togrenstrukturen — hun
bekrefter den, og legger til at heller ikke den mekaniske grenen er helt
mekanisk. Det er en annen posisjon enn Mellbyes (at ekspertvurderingene
aldri binder). Runde to slo de to sammen; de er ikke det samme.

To ting hun ikke gjør:

- Hun siterer bare FØRSTE halvdel av setningen fra Meld. St. 16.
  `overvåkingen viser` gir **0 treff** i hele volumet — hun har ikke
  «men dersom overvåkingen viser en endring i påvirkning de to årene
  vil myndighetene måtte gjøre grundigere vurderinger ut i fra den
  samlede miljøtilstanden».
- Hun nevner ikke at styringsgruppen leverer et sammenslått råd for den
  sprikende grenen. `styringsgruppen` forekommer **én gang** i 150
  sider, og da om modellutvikling: «Det er i dag satt ned en
  styringsgruppe for å videreutvikle arbeidet med overvåkningsmodellene.»

Det siste er et sterkt nulltreff i seg selv: volumet er skrevet i 2018,
bygger systematisk på høringsnotater og høringssvar, og har hele
kapitler om hjemmel og forutsigbarhet — og rådsleddet er usynlig i det.

---

## Søkeloggen

### Egne arkiv (Del A)

| kropp | fil | måling |
|---|---|---|
| 2018 | `arkiv/styringsgruppen/2018-11-27.bin.gz` | 12 sider; Tabell 1 s. 3; `konservativ` **0** |
| 2018-2019 | `arkiv/styringsgruppen/2019-11-17.bin.gz` | 13 sider; Tabell 3 s. 7; `konservativ` 1 |
| pressemelding 30.10.2017 | `arkiv/regjeringen-pressemeldinger/2017-10-30.bin.gz` | `konservativ tilnærming` 1, `lik vekting` 1 |

### Avsendernes nettsider (Del B)

| kilde | streng / handling | resultat |
|---|---|---|
| vetinst.no | `/rapporter-og-publikasjoner/faglige-vurderinger-og-horingssvar`, uttrekk av lenker med `kapasitet\|produksjonsområd` | **10 dokumenter**, 5 med tekstlag |
| de 5 skannene | OCR med macOS Vision (`VNRecognizeTextRequest`, 3× rendring) | 681–10 826 tegn hver; **0 treff på alle claim-termer**; ett ekte `råd` (vi7) |
| sjomatnorge.no | `230615-Horing-Produksjonsomradeforskriften.pdf` | 8 s., 0 treff |
| naturvernforbundet.no | felles innspill NOU 2023:23 | 11 s., 0 på rådsformen |
| wwf.no | høringssvarsida (runde 2) | ingen om kapasitetsjustering |
| lakseelver.no | nettsøk: høringssvar + trafikklys + styringsgruppen | bare nyhetssaker om grenseverdier og sjøørret |
| regjeringen.no | direkte | **403**, som i runde 1 og 2 |
| web.archive.org | CDX på 2024-høringssida | 8 kopier, hentet 20260213 |
| web.archive.org | CDX på `?showSvar=true` | **0 kopier** |
| web.archive.org | videre kall | **«Temporarily Offline»** — tjenesten nede |

### NVA (Del C og D.1)

| handling | resultat |
|---|---|
| `search/resources?query=Evidence-based policymaking salmon aquaculture` | 1 treff, fil `Thesis_Larsen.pdf` |
| `/publication/{id}/filelink/{fileId}` | **presignert S3-URI — virker uten auth** |
| nedlasting Larsen 2025 | 11 975 711 byte, 112 sider |
| `search/resources?query=Erstatning til fiskerettshavere …` | 1 treff, fil `213.pdf` |
| nedlasting Ådum 2021 | 1 068 025 byte, 118 sider |

### Sjørettsfondet (Del D.2)

| handling | resultat |
|---|---|
| `sjorettsfondet.no/asset/journal/2018/506/Marius-506.pdf` | 150 sider, Hanna Nicholls |
| termtelling i volumet | `styringsgruppen` **1**, `overvåkingen viser` **0**, `sammenfallende` 1, `automatikk` 4 |

---

## Hva som fortsatt ikke lot seg nå

| flanke | hindring | hva som skal til |
|---|---|---|
| **~300 høringssvar, fem runder** | svarene ligger bak `?showSvar=true` på regjeringen.no (403 for oss); ingen Wayback-kopi av den URL-en; Internet Archive nede under kjøringen | be noen utenfor 403-en hente `…/id{N}/?showSvar=true` for de fem hørings-ID-ene, eller prøv Wayback igjen når IA er oppe |
| **Ordrett belegg fra de fem OCR-ede VI-svarene** | teksten er vår lesing av et bilde | sitatene i B.1c bør leses i originalen før de brukes som belegg. Be VI om tekstversjon, eller les papirutgaven |
| MarIus 2023–2026 (~45 bind) | ikke i NB; åpne PDF-er på sjorettsfondet.no uten fulltekstindeks | last ned nr. 553–599 og søk lokalt |
| Brynjulfsen 2025, Revheim 2023, Finstad/Levold 2020 | ikke forsøkt | `filelink`-ruten over virker nå — dette er billig |
| Colombo 2024, Rosendal mfl. 2025, Bakke mfl. 2025 | fra runde 1 | institusjonstilgang |

---

## Status per påstand etter tre runder

| | status | endret i runde 3? |
|---|---|---|
| **B** | første ledd publisert (Monsen 2021; NFD 2017 ×2), andre ledd ikke funnet | **ja** — regelen har tre formuleringer, betingelsen er målt og utestet, notatet rettet |
| **C** | mandatteksten publisert (Mellbye & Bendiksen red. 2024), endringen ikke funnet | nei |
| **D** | ikke funnet som formulert; premisset publisert, motforestillingen presisert | **ja** — Nicholls' argument er nedstrøms, ikke Mellbyes posisjon; og VIs høringssvar 05.12.2019 er første eksterne omtale av den sprikende grenen (B.1c) |
| **E** | ikke funnet | **ja** — Larsen 2025, det grundigste arbeidet om kunnskapsgrunnlaget, har 0 på `two years`/`both years` |
| **F** | ikke funnet; kolonnen brukt i to arbeider | **ja** — Ådums bidrag er én fotnote, ikke en metode; Larsen siterer ikke Fauchald 2020 |

---

## Den svakeste påstanden nå, og hvorfor

**Det er C.**

Ikke fordi den er usann — mandatene er lest i originalen, `oddetallsår`
og `kapasitetsjuster` forekommer null ganger i 2020-mandatet,
`fargelegging` null ganger i 2018-mandatet, og `/CreationDate` daterer
revisjonen til 18.05.2020 kl. 12:14. Selve målingen er solid.

Den er svakest fordi **halvparten av den allerede er publisert, av den
mest autoritative tenkelige motparten, og den andre halvparten er en
observasjon om et fravær hos nettopp ham.**

Mellbye & Bendiksen (red.), *Akvakulturloven: lovkommentar*
(Universitetsforlaget 2024) siterer 2020-mandatet ordrett, daterer det
korrekt, og oppgir hvor det ble publisert. Det som gjenstår for C er
påstanden om at ingen har sammenlignet 2018- og 2020-mandatet — og
Mellbye er den som var nærmest å gjøre det og ikke gjorde det. Han
beskriver tvert imot systemet som om klausulen fortsatt sto der
(«styringsgruppens oppsummering i oddetallsårene»).

Det gjør C til en påstand om hva en navngitt, levende jurist har
oversett i en lovkommentar utgitt for to år siden. Den formen er
sårbar på tre måter de andre ikke er:

1. **Den kan falsifiseres av én setning** i en senere utgave, en
   artikkel eller et foredrag jeg ikke har sett. Jeg har søkt Idunn på
   tittelnivå, NB på fulltekst og NVA — men lovkommentarer revideres.
2. **«Ingen har sammenlignet» er en sterkere påstand enn «ingen har
   publisert funnet»**, som er formen B, E og F har. C påstår noe om
   fravær av en sammenligning i et dokument som siterer den ene halvdelen.
3. **Den er den eneste av de fem der jeg har lest motparten bare gjennom
   konkordanser**, ikke i fulltekst. Lovkommentaren er en
   pliktmonografi i NB uten nedlastbar kropp; jeg har seks
   konkordansevinduer på `styringsgruppen` og tre på `mandat`, ikke
   kapittelet. **Det er den mest verdifulle enkeltkilden å skaffe før C
   publiseres** — et bibliotekseksemplar eller Juridika-tilgang, og les
   kommentaren til akvakulturloven § 9 i sin helhet.

E er den skarpeste og best belagte: fire eksakte fraser med null treff i
hele Nasjonalbiblioteket, med frasesøkets strenghet kontrollert, og nå
med Larsen 2025 som et 112-siders nulltreff oppå det. F er nest sterkest,
fordi avhengigheten er verifisert mot vårt eget arkiv side for side. B er
sterk etter Del A, og vet nå nøyaktig hvor den er utestet. D er svak i
formen, men det er en kjent svakhet med en kjent årsak: koblingen råd →
farge er ikke definert i regelverket, og det er selve funnet. D fikk
dessuten bedre fotfeste i denne runden: Veterinærinstituttets
høringssvar 05.12.2019 viser at den sprikende grenen var omstridt
allerede da rådskolonnen fantes — og at kritikken den gang gjaldt
departementets metode, ikke rådsleddet, som ingen nevnte.
