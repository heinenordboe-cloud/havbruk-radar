# Måling 19.09.2026 — hva datoen i filnavnet er, per kilde

`publiseringsvakt.hviteliste()` leser NYESTE snapshot per kilde.
Generatoren leser alle 21 årgangene av `eierskap_historikk`, og 961 av
1030 portfunn kom av det (976 etter escaping-rettingen i e72847b).

Regelen som skal løse det: **hvitelista leser ALLE datoer for en kilde
partisjonert på når noe gjaldt i VERDEN, og NYESTE dato for en kilde
partisjonert på når VI hentet.** Kilden erklærer selv hvilken type den
er — `Source.partisjonering`, samme form som `domene`, `utvalg` og
`attribusjon`.

Denne fila er grunnlaget for den erklæringen. Alt er målt mot
datarepoet 19.09.2026, og hvert tall under er reproduserbart med
skriptene beskrevet nederst.

---

## 1. Klassifiseringen av alle 12 kilder

Prøven er `observed_at` mot `fetched_at`, over HVERT snapshot kilden
har — ikke over de fire som ble sett på først. Avviket er i dager,
negativt der snapshotet gjelder for et tidsrom FØR vi hentet det.

| kilde | datoer | spenn | avvik min..maks | median | type |
|---|---:|---|---:|---:|---|
| `akvakultur` | 5 | 2026-08-17..2026-09-14 | 0 .. 0 | **0** | henting |
| `biomasselag` | 2 | 2026-09-10..2026-09-15 | 0 .. 0 | **0** | henting |
| `eierskap` | 2 | 2026-09-02..2026-09-14 | 0 .. 0 | **0** | henting |
| `enhetsregisteret` | 6 | 2026-08-16..2026-09-14 | 0 .. 0 | **0** | henting |
| `biomasse` | 104 | 2017-10-31..2026-05-31 | −3221 .. −94 | −1821 | verden |
| `eierskap_historikk` | 21 | 2006-12-31..2026-12-31 | −7185 .. **+120** | −3532 | verden |
| `ekspertgruppen` | 9 | 2016-12-31..2025-12-31 | −3532 .. −244 | −1706 | verden |
| `lusetall` | 764 | 2012-01-02..2026-08-17 | −5343 .. −28 | **−2669** | verden |
| `reguleringsomraader` | 1 | 2026-06-29..2026-06-29 | −77 .. −77 | −77 | verden |
| `romming` | 13 | 2016-12-31..2026-12-31 | −3533 .. **+119** | −1342 | verden |
| `sjotemperatur` | 764 | 2012-01-02..2026-08-17 | −5349 .. −28 | −2675 | verden |
| `trafikklysvedtak` | 5 | 2018-12-31..2026-12-31 | −2805 .. **+107** | −1344 | verden |

**8 «verden», 4 «henting».** Skillet er ikke gradvist: de fire
henting-kildene har avvik **0 i hvert enkelt snapshot** — ikke median 0,
men min og maks også — og de åtte andre har median mellom −77 og −3532
dager.

Det gjør erklæringen ETTERPRØVBAR, og det er hele grunnen til at prøven
er skrevet ned her: en «henting»-kilde kan gjenkjennes ved at
`observed_at == date(fetched_at)` overalt. Tre kilder har i tillegg
snapshots datert FRAM I TID (+120, +119, +107 dager): et snapshot som
gjelder for 2026-12-31 og ble hentet i september kan ikke være datert
etter hentingen.

### `lusetall` er «verden», ikke «henting»

Premisset da regelen ble formulert var at «lusetall og de ukentlige» er
henting-typen. **Det holder ikke.** `lusetall` har **764 datoer fra
2012-01-02**, med **median 2669 dager** mellom uka raden gjelder for og
dagen vi hentet den. Datoen i filnavnet er ISO-uka lusetellingen gjelder
for — det er nettopp rettelsen av F6, der `run.py` daterte snapshotet
etter kjøredagen mens kilden stemplet radene med uka de gjaldt for.

Samme for `sjotemperatur`: 764 datoer, median −2675.

Regelen står, men den klassifiserer **8 av 12** kilder som «verden», ikke
2. Det er verdt å skrive ned fordi det er den motsatte feilen av den
farlige: en kilde man tror er «henting» og som egentlig er «verden» gir
en for LITEN hviteliste, altså støyende funn — mens motsatt vei er
stille. Se punkt 4.

## 2. Hva regelen koster, og hva den kjøper

Hvitelista bygget tre ganger per variant, samme kode, bare utvalget av
datoer som varierer:

| regel | navn | orgnr | tid (3 kjøringer) |
|---|---:|---:|---|
| nyeste per kilde (i dag) | 8 682 | 2 163 | 0,07–0,08 s |
| **regelen** (alle datoer for de 8, nyeste for de 4) | **12 244** | **2 214** | **7,17–7,54 s** |
| alle datoer for alt | 12 257 | 2 219 | 7,49–7,52 s |

Regelen legger **3 562 navn og 51 orgnumre** til hvitelista mot i dag.

Og den siste linja er det regelen KJØPER: forskjellen mellom «regelen»
og «alle datoer for alt» er **13 navn og 5 orgnumre**. Det er de eldre
partisjonene til de fire henting-kildene — navn som ikke gjelder lenger,
og som en visning ikke skal hente fra. Ett av dem er en tildelt eier som
falt ut av `eierskap` mellom 02.09 og 14.09. Tallet er lite, men det er
nøyaktig den innstrammingen `hviteliste()` er skrevet for å ha, og en
regel som leste alle datoer for alt ville gitt den bort.

Per kilde under regelen (to kjøringer per kilde, samme bygg som
hvitelista — lesing OG feltiterasjon):

    akvakultur             henting    1 datoer   0,01–0,02 s   1742 navn     0 orgnr
    biomasse               verden   104 datoer   0,20–0,24 s     14 navn     0 orgnr
    biomasselag            henting    1 datoer   0,00–0,01 s   1098 navn     0 orgnr
    eierskap               henting    1 datoer   0,02       s   3738 navn   798 orgnr
    eierskap_historikk     verden    21 datoer   0,05–0,06 s   2940 navn   335 orgnr
    ekspertgruppen         verden     9 datoer   0,02–0,03 s     13 navn     0 orgnr
    enhetsregisteret       henting    1 datoer   0,02       s   1742 navn  1743 orgnr
    lusetall               verden   764 datoer   4,97–5,14 s   2684 navn     0 orgnr
    reguleringsomraader    verden     1 datoer   0,00       s     28 navn     0 orgnr
    romming                verden    13 datoer   0,02       s    388 navn     0 orgnr
    sjotemperatur          verden   764 datoer   1,87–2,07 s   1494 navn     0 orgnr
    trafikklysvedtak       verden     5 datoer   0,01       s     12 navn     0 orgnr
    SUM                                          7,19       s

**`lusetall` er 5 av de 7 sekundene**, og nesten alt er feltiterasjon og
ikke lesing: de 764 snapshotene leses alene i 2,29 s, mens lesing pluss
iterasjon over **13 627 428 rader** koster 4,97–5,14 s. Kilden bidrar med
2 684 navn (lokalitetsnavn via `entity_name`) og 0 orgnumre.

Sju sekunder på en port som kjører ved publisering, mot 20 sekunder for
å bygge de 1782 sidene. Prisen er kjent og akseptert; tallet står her
slik at en framtidig økning kan sammenlignes med noe.

## 3. Lesedøra fjerner 0 rader fra de 21 årgangene

Regelen alene er ikke nok, og dette er grunnen. At hvitelista leser de
eldre partisjonene betyr at `snapshot.versjoner()` kjører
`persondata.fjern_personformer()` på dem — døra kjører. Målt hva den
faktisk fjerner fra `eierskap_historikk`:

    rader rått (pl.read_parquet):   36 360
    rader gjennom lesedøra:         36 360
    døra fjerner:                        0

Årsaken står i kildens felter. Alle 4 545 rader per felt, over de 21
årgangene:

    tillatelse_nr  mottaker_orgnr  mottaker_navn  mottaker_type
    journal_dato   journal_nr      rekkefolge     dato_forbehold

    rader med organisasjonsform:        0
    rader med institusjonell_sektorkode: 0

Døra spør om de to siste. Kilden skriver ingen av dem — formen ligger i
`mottaker_type`, i pub-aquas vokabular. Uten et tillegg ville regelen
altså **hvitelistet** de personformede mottakerne i stedet for å filtrere
dem: stillhet kjøpt for sikkerhet.

## 4. `mottaker_type` er der, og BEGGE ledd trengs

    overføringsentiteter (dato, id):            2611
    uten mottaker_type i det hele tatt:            0

Feltet finnes altså på **2611 av 2611**. Ingen rad mangler det
klassifiserende feltet — det er en annen situasjon enn de 677
overføringene backfillen måtte stoppe på ukjent type, og den forskjellen
er verdt å merke seg: her VET kilden, den sier det bare i sitt eget
språk.

`sources/eierskap.er_person()` treffer **4** av de 2611:

| `mottaker_type` | n | `FORM_KART` | `er_person()` |
|---|---:|---|---|
| LimitedLiabilityCompany | 1647 | `AS` | False |
| AS | 663 | — | False |
| PublicLimitedCompany | 284 | `ASA` | False |
| FLI | 6 | — | False |
| **DA** | **3** | — | **True** |
| FYLK | 3 | — | False |
| ASA | 2 | — | False |
| Municipality | 2 | — | False |
| **JointLiabilityCompany** | **1** | `DA` | **True** |

De fire:

    2009-12-31   NT-NR-0379|2009000008   DA
    2009-12-31   VA-S-0302|2009000002    DA
    2009-12-31   VA-S-0303|2009000002    DA
    2014-12-31   HE-E-0505|2014000149    JointLiabilityCompany

**`FORM_KART` alene er IKKE nok.** Tre av de fire bærer Brreg-koden `DA`,
og `FORM_KART.get("DA")` er `None` — kartet oversetter FRA pub-aquas
navn, ikke fra Brregs koder. Den fjerde bærer `JointLiabilityCompany`,
som bare kartet kjenner.

`er_person()` er nok, fordi den spør begge:

    t in PERSONTYPER                          pub-aquas egne ord
    persondata.er_personform(t)               Brregs koder        <- fanger de 3
    persondata.er_personform(FORM_KART[t])     oversettelsen       <- fanger den 1

Det er samme to-ledds-konstruksjon som `er_personform`/`er_personsektor`
i `core/persondata.py`, og her er den målt nødvendig: hvert ledd fanger
noe det andre ikke fanger. En implementasjon som bare slo opp i
`FORM_KART` ville tatt 1 av 4 og sett riktig ut.

At kilden bærer to vokabularer i samme felt er ikke en feil — det er
`fa35000`, der historiske mottakere som er oppløst får formen slått opp
hos Brreg fordi de ikke finnes i pub-aquas `/entities`.

## 5. Hva målingen ikke svarer på

- **Om de 3 DA-ene og partrederiet er persondata.** Det er en åpen
  beslutning, ikke en måling. Se
  `docs/beslutninger/2026-09-18-changeloggens-persondata-ligger-stille.md`
  punkt 3 og sektornotatets punkt 7.
- **Om noen av de 8 «verden»-kildene REVIDERER bakover.** Partisjonstypen
  sier hva datoen i filnavnet er, ikke om en gammel dato kan få nye tall.
  `biomasse` gjør det (12,3 % av radene, målt 25.08), og det er et annet
  spørsmål med sitt eget svar i `diff.revisjon()`.
- **Om en kilde erklærer seg riktig.** Prøven i punkt 1 er den
  etterprøvingen, og den er grunnen til at avviket er målt per snapshot
  og ikke bare som median.

## Skriptene

Alle fire i sesjonens scratchpad, og alle leser datarepoet gjennom
`core.snapshot` — ingen `pl.read_parquet` utenom der punkt 3
uttrykkelig måler rått mot lest.

| måling | hva den gjør |
|---|---|
| punkt 1 | `snapshot.datoer()` × `snapshot.versjoner()`, `fetched_at_i()` per snapshot, avvik i dager |
| punkt 2 | hvitelistebygget i tre varianter, 3 kjøringer hver, og per kilde 2 kjøringer |
| punkt 3–4 | `pl.read_parquet` mot `snapshot.versjoner()` for samme dato, feltteller, `er_person()` per `mottaker_type` |
