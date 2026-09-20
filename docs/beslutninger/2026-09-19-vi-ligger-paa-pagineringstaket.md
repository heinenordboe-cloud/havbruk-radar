---
dato: 2026-09-19
tittel: Vi ligger på pub-aquas pagineringstak — og ArcGIS sier «for bredt» med 200 OK
status: besluttet
commit: [fylles inn]
---

# Vi ligger på pagineringstaket, og den farlige varianten var et annet sted

**Bestemt:** `SPENN = 100` beholdes i `akvakultur` og `eierskap`, som er
eksakt pub-aquas tak. Ingen «ett fullt kall ga én rad»-vakt legges i
`eierskap._alt()` — premisset for den reproduserer ikke. Den ekte
varianten av samme fallgruve ligger i ArcGIS-kildene, og den får en
delt vakt: `sources/_arcgis.py`.

**Og en rettelse:** påstanden i `sources/akvakultur.py` om at et for
bredt spenn gir «stille ÉN rad» er ikke sann. Den har stått siden
17.08.2026, merket «verifisert mot levende API».

---

## 1. Målingen som ikke reproduserte

Utgangspunktet var at pub-aqua svarer 200 med én rad for `range=0-100`
og oppover. Målt mot levende API i dag, begge endepunktene vi bruker:

| range | http | svar |
|---|---:|---|
| `0-98` | 200 | 99 rader |
| `0-99` | 200 | **100 rader** |
| `0-100` | **400** | `The range specification is out of bounds. Limit is set to: 100. Range can be specified e.g: 0-99` |
| `0-199` | 400 | samme |
| `0-999` | 400 | samme |

`/sites` og `/licenses` oppfører seg identisk. Kanten er eksakt 100, og
over den feiler tjenesten **høyt**, med taket i klartekst.

### Hvorfor den gamle påstanden sannsynligvis var en målefeil

Feilkroppen er `{"errors": [ … ]}` — en dict med ÉN nøkkel. `len()` av
den er **1**. Et måleskript som skriver `len(json)` uten å se på
statuskoden leser derfor «1 rad» der svaret var en feil.

Jeg gjorde nøyaktig den feilen i dag, før den ble oppdaget: samme
skriptform, samme tall, samme konklusjon. Det er den mest sparsommelige
forklaringen på 17.08-påstanden også.

Det kan ikke bevises i ettertid. Men ett ledd er sikkert: **gjennom
`_http.get()` kunne symptomet aldri oppstått.** Den kaller
`raise_for_status()`, og en 400 kaster før noe kommer tilbake til
pagineringsløkka. Vakten i `akvakultur.fetch()` som skulle fange «én
rad» har altså aldri kunnet nås av den feilen den ble skrevet for.

## 2. Hva som IKKE ble gjort, og hvorfor

**Ingen «1 rad»-vakt i `eierskap._alt()`.** Asymmetrien mot `akvakultur`
ser ut som en glipp, og den ble nesten rettet. En vakt der ville stått
og aldri kunnet fyre, og — verre — den ville festet en måling som ikke
reproduserer, i en fil som hevder at tall er målt. CLAUDE.md 1b-4:
terskler skal måles, ikke gjettes. Det gjelder også terskler man arver.

Begrunnelsen står nå i `_alt()`s docstring med målingen, slik at neste
person ikke retter asymmetrien på det samme premisset. Samme form som
`ENDRINGER_UTELATT` i `nettsted.py`: en tilsiktet utelatelse som ser ut
som en feil, blir rettet av den neste med mindre den er skrevet ned.

**Vakten i `akvakultur.fetch()` beholdes**, men omdokumentert. Den kan
ikke nås av 400-veien, og den koster to sammenligninger i uka. Den fanger
fortsatt enhver ANNEN vei til «hele registeret ble én rad»: en `base_url`
som peker på et enkeltoppslag, en tjeneste som begynner å svare 200 på
noe som ikke er hele laget, et filter vi ikke vet at vi har. Å fjerne den
ville byttet en billig vakt mot ingenting.

## 3. Den ekte varianten: ArcGIS avkorter med 200 OK

Spørsmålet «finnes samme mønster i andre kilder — et svar som er gyldig,
men som betyr *du spurte for bredt*» har ett ja, og det er ikke pub-aqua.

Målt mot Biomasse-laget (1128 rader, `maxRecordCount` = 2000):

    resultRecordCount=1000, offset=0      1000 rader   exceededTransferLimit=True
    resultRecordCount=1000, offset=1000    128 rader   (ikke satt)
    resultRecordCount=2000, offset=0      1128 rader   (ikke satt)
    resultRecordCount=3000, offset=0      1128 rader   (ikke satt)
    resultRecordCount=5000, offset=0      1128 rader   (ikke satt)

Tjenesten avkorter til sitt eget tak **uten å feile**, og sier det i
`exceededTransferLimit`. `biomasselag` og `romming` har identiske
pagineringsløkker med `if len(trekk) < SPENN: break`, og **ingen av dem
leste flagget**.

I dag er det trygt, fordi `SPENN = 1000` ligger under taket på 2000: en
kort side er ekte slutt, og flagget står bare på de fulle sidene.
**Senker tjenesten taket under 1000, snur det:** hver side gir færre
rader enn vi ba om, `len(trekk) < SPENN` leser det som siste side, og
kilden samler halve laget med 200 OK og ingen feilmelding. Volumvakten
ville sett fallet i etterkant; fetch selv ville tiet.

### Vakten ligger ETT sted

`sources/_arcgis.py`, kalt fra begge løkkene. Ikke kopiert inn i hver
kilde: de to pagineres likt, prøven er den samme, og to kopier er to
steder å glemme den ene — formen F6 og F7 hadde. Plasseringen følger
`_barentswatch.py`: maskineri to kilder deler, med `_`-prefiks slik at
`registry` hopper over fila. `_http.py` ville vært feil hjem —
`exceededTransferLimit` er ArcGIS' svarkontrakt, ikke HTTP.

Prøven spør om det ENE tilfellet der vår slutt-test og tjenestens eget
svar er uenige:

    kort side  + flagget satt        MOTSIGELSE — kaster
    full side  + flagget satt        normalt, neste side
    kort side  + uten flagg          ekte slutt

Den spør altså ikke «kom det færre rader enn vi ba om» — det er det
normale på siste side, og en vakt på det ville felt hver kjøring. Det er
1b-2: still spørsmålet du faktisk vil ha svar på.

**Plantet og verifisert.** Et konstruert 200-svar med 500 rader og
flagget satt — nøyaktig det tjenesten ville gitt med taket senket til 500:

    med vakten:    romming.fetch() kaster RuntimeError («avkortet»)
    uten vakten:   romming.fetch() returnerer 500 rader og sier ingenting

Det andre leddet er poenget: det var oppførselen fram til i dag.

## 4. De andre parameterfamiliene, målt

| kilde | parameter | oppførsel ved for bredt/ukjent |
|---|---|---|
| `akvakultur`, `eierskap` | `range` | **400** med taket i klartekst. Ukjente parametere (`siteNr`, `vrovl`) ignoreres stille, men vi sender ingen |
| `enhetsregisteret` | `naeringskode`, `size`, `page` | honoreres; ukjent parameter gir **400** som navngir den: «'vrovl' er ikke et støttet parameter» |
| `biomasselag`, `romming` | `resultOffset`, `resultRecordCount` | **200 + `exceededTransferLimit`** — den stille varianten, nå voktet |
| `lusetall`, `sjotemperatur` | `fromweek`/`toweek` m.fl. | krever token, ikke testbart utenfra. Målt fra vårt eget arkiv: **764 av 764 unike `raw_hash`** i begge — ukeparameterne ble honorert ved hver henting |

Pub-aquas slutt-test er målt sunn i tillegg: `range=1700-1799` gir 82
rader, `1800-1899` gir 0, `5000-5099` gir 0.

## Hva som ville snudd det — særlig om kilden flytter kanten

- **Pub-aqua senker taket under 100.** Da feiler hver kjøring med 400 på
  første kall, hver uke, til `SPENN` senkes. Høyt og umiddelbart, og det
  er derfor det er greit å ligge på kanten: feilen peker mot oss, ikke
  mot dataene. Rettelsen er å senke `SPENN` i begge kildene — de deler
  tak, og de deler ikke konstant, så begge må endres.
- **Pub-aqua hever taket.** Ingenting brekker. Å øke `SPENN` ville spart
  kall, men ikke uten en ny måling: feilmeldingen oppgir taket, så den
  målingen er ett kall.
- **Pub-aqua slutter å validere `range` og begynner å avkorte stille.**
  Da blir pub-aqua det ArcGIS er i dag, og `akvakultur`s beholdte vakt
  fanger bare det ekstreme tilfellet (én rad). Vi ville trengt samme
  konstruksjon som `_arcgis.sjekk_avkorting()` — men pub-aqua har ingen
  `exceededTransferLimit`, og da finnes ingen motsigelse å måle. Det er
  det svakeste punktet i hele oppsettet, og det er utenfor vår kontroll.
- **ArcGIS senker `maxRecordCount` under `SPENN`.** Da fyrer den nye
  vakten, og rettelsen står i feilmeldingen: senk `SPENN`.
- **ArcGIS slutter å sette `exceededTransferLimit`.** Da er vakten blind,
  og vi er tilbake til å stole på at taket ligger over `SPENN`. Verdt å
  måle på nytt hvis laget vokser mot 2000 rader — biomasselag var 1127
  den 10.09 og **1128 i dag**.

**Ville IKKE snudd det:** at vakten i `akvakultur.fetch()` ikke kan nås
av 400-veien. En vakt som dekker flere veier enn den ble skrevet for, er
ikke død kode — den er underdokumentert, og det er rettet.
