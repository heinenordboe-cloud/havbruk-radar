---
dato: 2026-09-02
tittel: Eierskapskjeden lukkes via /licenses — og personvernfilteret måtte bli et annet enn det bestilte
status: gjeldende
commit: f86b07e
---

## Hva som ble bestemt

En ny kilde, `sources/eierskap.py`, som lukker kjeden

    lokalitet --(akvakultur.tillatelser)--> tillatelse --(NY)--> selskap

Entiteten er **tillatelsen**, ikke lokaliteten. En tillatelse kan henge på
mange lokaliteter og en lokalitet kan bære mange tillatelser; tillatelsen
er det ene leddet der forholdet mot en eier er 1:1. En rad per lokalitet
måtte slått sammen flere eiere til én verdi og mistet hvem som eier hva.

Ukentlig frekvens (`min_dager_mellom = 7`), som systemets kadens.

## Veien: `/licenses`, ikke `/entities`

Begge endepunktene ble kalt mot levende tjeneste før en linje kildekode
ble skrevet. Ingen av dem krever autentisering.

| endepunkt | rader | kall | bærer |
|---|---|---|---|
| `/licenses` | **3036** | 31 | `licenseNr`, `openLegalEntityNr`, `legalEntityName`, `connections[] → siteNr`, `grantInformation` |
| `/entities` | **542** | 6 | `name`, `typeValue`, `openNr`, **`addresses`** — men ingen kobling til lokalitet |
| `/licenses/{nr}` | 1 | 1 | samme som lista, ett oppslag |
| `/licenses/{nr}/transfers` | 0–6 | 1 | `identityNr`, `journalDate`, `journalNr`, `officialName` |
| `/species` | — | — | finnes ikke (404) |

**`/entities` kan ikke være ryggraden, fordi den ikke inneholder leddet vi
mangler.** Den har ingen kobling mellom tillatelse og lokalitet.
`/licenses` bærer hele kjeden i ett endepunkt. Valget er avgjort av det,
ikke av hva som var enklest.

`/entities` hentes likevel, til nøyaktig **én** ting: `typeValue`, som er
det eneste stedet man kan se om eieren er et menneske. Se under.

Merk to ting som ble målt og ikke antatt: spørreparameteren heter
`license-nr` (kebab), ikke `licenseNr` — den feilstavede varianten
ignoreres stilltiende og returnerer hele lista. Og `range` over 100 gir
400 Bad Request.

## Personvernfilteret — og hvorfor det bestilte filteret ikke holdt

Bestillingen forutsatte at `openLegalEntityNr` **kunne være et
fødselsnummer**, og at en ni-siffer-test derfor ville skille selskap fra
person. Begge deler ble målt, og bildet er et annet.

### Fødselsnummer finnes ikke i responsen

Målt over alle 3036 tillatelser, alle 3036 `grantInformation`, alle 542
enheter og 216 overføringer:

| felt | 11 siffer | 9 siffer | tomt |
|---|---|---|---|
| `licenses.openLegalEntityNr` | **0** | 2974 | 62 |
| `grantInformation.openLegalEntityNr` | **0** | 2965 | 71 |
| `entities.openNr` | **0** | 499 | 43 |
| `transfers.identityNr` | **0** | 214 | 2 |

Fiskeridirektoratet publiserer ikke fødselsnummer i det hele tatt. For
fysiske personer er nummeret **tomt** — og navnet står likevel:
«HOELFELDT LUND, PER CHRISTIAN», «LYSEN ANNE», «NØSTBAKKEN JAN HENRIK».

### Ni siffer skiller ikke person fra selskap

Av de 542 enhetene er 8 `SoleProprietorship` — enkeltpersonforetak. Målt:

> **8 av 8 ENK har NI SIFFER og ville passert det bestilte filteret.**

Det er ordrett feilen CLAUDE.md regel 3 er skrevet om: «åpningen 16.08 ble
begrunnet med at alle `entity_id` var ni siffer, og et ENK har ni siffer
akkurat som et AS. Skillet fantes i dataene (`organisasjonsform`), men ble
ikke båret over i kontrollen som skulle håndheve det.»

Et ENK er ikke et eget rettssubjekt — foretaket ER innehaveren.

**Derfor filtreres det på TYPE, ikke på sifferlengde.** Sifferprøven er
beholdt som et andre vilkår, ikke som det bærende: den fanger de 43
privatpersonene, som har tomt nummer.

### `/entities` bærer bostedsadresser fra Folkeregisteret

For de 43 `Person`-enhetene inneholder svaret `addresses` med
`type: "ResidentialLocation"` og `officialSourceType: "FREG"` — altså
gateadresser til navngitte privatpersoner, hentet fra Folkeregisteret.
Det er nøyaktig det regel 3 forbyr.

Rå-arkivet ligger i git og er append-only. En bostedsadresse som kommer
inn der, kan ikke fjernes uten å skrive om hele repoet. Derfor er
kroppen som arkiveres den **filtrerte** — `fetch()` reduserer hver enhet
til `{id, openNr, typeValue, name}` og slipper aldri `addresses` videre.

Det bryter hovedregelen om at `fetch()` returnerer råsvaret, og det er et
bevisst brudd med presedens: `enhetsregisteret` gjorde den samme
avveiningen 22.08.2026. Regel 3 vinner over regel 2 når de to peker i
hver sin retning, fordi den ene feilen er reparerbar og den andre ikke er
det.

## De to lagene, og hvorfor de ikke er belte og bukseseler

**Lag 1, `fetch()`:** personer forsvinner før kroppen arkiveres.
**Lag 2, `parse()`:** samme prøve gjentas.

Lag 2 er ikke en gjentakelse for sikkerhets skyld. `parse()` er veien en
**arkivert** kropp kommer inn igjen på. Skulle en kropp fra før filteret —
eller fra en framtidig versjon der `fetch()` er endret — spilles av på
nytt, er lag 2 det eneste som står mellom den og disken. Samme
begrunnelse og samme form som `enhetsregisteret.parse()`.

Begge lagene ble verifisert med konstruerte rader som ikke finnes i den
ekte responsen: et ellevesifret nummer, et ENK med gyldig niifret nummer,
og en privatperson med bostedsadresse. Alle tre stoppes i begge lag, og
testen sjekker også at strengen «Hjemmeveien», «FREG» og
«ResidentialLocation» ikke finnes i den kroppen som ville blitt arkivert.

## Feilen som ble funnet underveis: «vet ikke» betydde «slipp gjennom»

Første utgave av `_tillat()` var

    return not er_person(eier_type) and er_organisasjonsnummer(orgnr)

og `er_person(None)` returnerer **False** — fordi `None` ikke er en kjent
personform. En tillatelse hvis eier ikke fantes i `/entities` hadde ingen
type, og gikk derfor rett gjennom filteret med et gyldig niifret nummer.

Testen `test_ukjent_eier_slipper_ikke_gjennom` fanget det.

Dette er den samme formen som 1b-2: **en kontroll som måler noe som
LIGNER det den skal måle, og som er riktig i akkurat de tilfellene der de
to faller sammen.** `er_person()` svarer på «er dette en kjent
personform», mens filteret trenger svar på «vet vi at dette IKKE er en
person». De to er like helt til typen mangler.

Regelen som følger, og som gjelder ethvert personvernfilter:

> **«Vet ikke» kan aldri bety «slipp gjennom».**

Det er MOTSATT fallback av frekvensvakten, som behandler `None` som
forfalt og kjører. Forskjellen er tilsiktet og skal ikke jevnes ut:
fallbacken skal peke mot den **billigste feilen**, og den er ikke den
samme i de to tilfellene. Hos frekvensvakten er kostnaden ved å ta feil
en ekstra fil med løpenummer; her er den et personregister i en
append-only historikk.

`_tillat()` krever nå at typen er en kjent, ikke-tom streng. Målt koster
vilkåret ingenting: alle 536 distinkte eier-ID-er i `/licenses` finnes i
`/entities`.

## Filteret er testet mot virkeligheten, ikke bare mot konstruerte rader

Et filter som aldri fjerner noe er et filter ingen har prøvd. I det ekte
kallet 02.09.2026 fjernet det **84 tillatelser**:

    62   personform: Person              (43 enheter)
    22   personform: SoleProprietorship  (8 enheter)
    ---
    84   totalt, av 3036

Ingen av dem ble fjernet av sifferprøven. Hadde filteret vært det
bestilte, ville de 22 ENK-tillatelsene kommet inn.

Kilden sier dessuten fra selv hvis tallet noen gang blir null:
`fetch()` legger da en advarsel om at enten har kilden sluttet å
publisere personeide tillatelser, eller så treffer ikke filteret lenger.

Verifisert på disk etter skriving: `organisasjonsform` er kun
AS/ASA/DA/ANS/SA, `eier_type` inneholder verken `Person` eller
`SoleProprietorship`, alle 5890 organisasjonsnumre er ni siffer, og
arkivkroppen inneholder null ellevesifrede tallstrenger og ingen av
strengene `addresses`, `zipCode`, `FREG` eller `ResidentialLocation`.

## Organisasjonsformkartet er målt, ikke gjettet

pub-aqua bruker sitt eget vokabular. Kartet til Brreg-koder ble verifisert
ved å krysse eiernes organisasjonsnummer mot vårt eget
enhetsregister-snapshot: **367 enheter overlappet, og alle fem parene
stemte 1:1 uten et eneste avvik.**

    LimitedLiabilityCompany    -> AS     361
    PublicLimitedCompany       -> ASA      2
    JointLiabilityCompany      -> DA       2
    UnlimitedLiabilityCompany  -> ANS      1
    CoopCompany                -> SA       1

De to ansvarlige selskapsformene ligger **motsatt av hva navnene
antyder** — `JointLiabilityCompany` er DA og `UnlimitedLiabilityCompany`
er ANS. Det er nettopp derfor kartet er målt.

Formene uten overlapp (Foundation, Municipality, Association,
JointlyOwnedShippingCompany, OrganizationalSection — 108 tillatelser) står
bevisst ikke i kartet: vi har ikke Brregs ord for dem, og en gjettet kode
ville vært en påstand på en tredjeparts vegne. De får `eier_type` ordrett
i stedet. DA og ANS beholdes, samme vurdering som `core/persondata.py`.

## Frekvens: ukentlig

Eierskap endres sjeldnere enn lusetall — overføringene spenner fra 2006
til 2026, med 9–65 i året — men et eierskifte er en **hendelse med høy
verdi**, og changeloggen fanger den bare hvis vi har to snapshots rundt
den.

Kostnaden er 37 kall i uka (31 for tillatelser, 6 for enheter) mot et
endepunkt uten nøkkel og uten rate limit vi har sett. Å hente sjeldnere
ville spart ingenting som er verdt å spare, og gjort hvert eierskifte
upresist datert med opptil en måned.

## `published_at` settes ikke

Verifisert: verken `/licenses` eller `/entities` sender `Last-Modified`
eller `ETag`. Regel 1b-7 er tydelig — standarden er «vet ikke», aldri
hentetidspunktet. Feltet står tomt.

`transfers` har en `ajourDate`, men den var lik dagens dato ved kallet og
er altså arkivets «à jour per», ikke en utgivelsesdato for tillatelsen.
Den brukes ikke.

## `core/` er urørt

Ingen endring i `core/` var nødvendig. Kilden er én ny fil i `sources/`
pluss en post i `config.yml`, og `registry.discover()` fant den uten
videre. Oversettelsen fra pub-aquas vokabular til Brreg-koder ligger i
kilden, der den hører hjemme — `core/persondata.py` eier fortsatt
spørsmålet «hvilke Brreg-former er personer», og kilden svarer på
«hvilken Brreg-form er dette».

## Hva som ville snudd det

- **Fiskeridirektoratet begynner å publisere fødselsnummer.** Da er
  sifferprøven plutselig det bærende vilkåret og ikke det andre, og den
  må flyttes først i `_tillat()`.
- **`/entities` slutter å oppgi `typeValue`.** Da finnes det ingen måte å
  skille ENK fra AS på i denne kilden, og den kan ikke kjøre — et filter
  som ikke kan stille spørsmålet sitt skal stoppe, ikke gjette.
- **Et endepunkt gir tillatelse → lokalitet uten å gå via eieren.** Da
  kan `/entities` droppes helt, og bostedsadressene aldri passere vårt
  minne i det hele tatt.
- **Fiskeridirektoratet publiserer et eget maskinlesbart eierskapsregister
  med historikk.** Da er `transfers`-rekonstruksjonen under overflødig.
