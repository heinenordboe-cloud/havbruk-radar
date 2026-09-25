# Lisenskjeden — én rad per kilde

Hver kilde i `sources/` med lisens, hjemmel, ordrett attribusjonskrav,
om kommersiell bruk er tillatt, og **datoen vilkåret faktisk ble lest**.

Regelen som fila håndhever: **udokumentert lisens er UBELAGT, ikke
antatt greit.** Se `docs/beslutninger/2026-09-12-lisenskjeden.md`.
UBELAGT betyr at vilkåret er lett etter og ikke funnet — ikke at det er
fritt. En UBELAGT kilde kan brukes i analyse og dokumentasjon, men skal
ikke bære en publisert visning uten at noen har spurt utgiveren.

Datokolonnen er ikke pynt. Et vilkår er en tredjeparts påstand som kan
endres uten at noe i dataene beveger seg, og en lisens lest for et år
siden er en antakelse med en dato på. Samme skille som `published_at`:
tidspunktet tilhører KILDEN, ikke oss.

---

## Tabellen

| kilde | lisens | hjemmel | attribusjon, ordrett | kommersiell | lest |
|---|---|---|---|---|---|
| `akvakultur` | NLOD | [fiskeridir.no](https://www.fiskeridir.no/statistikk-tall-og-analyse/lisens-for-bruk-av-fiskeridirektoratets-data) | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026 |
| `biomasse` | NLOD | samme | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026 |
| `biomasselag` | NLOD | samme | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026 |
| `romming` | NLOD | samme | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026 |
| `eierskap` | NLOD (Fiskeridir.) + **NLOD 2.0** (Brreg) | [fiskeridir.no](https://www.fiskeridir.no/statistikk-tall-og-analyse/lisens-for-bruk-av-fiskeridirektoratets-data) + [brreg.no/…/apne-data](https://www.brreg.no/bruk-av-data-fra-bronnoysundregistrene/apne-data/) | «Kilde: Fiskeridirektoratet» **+** «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av Brønnøysundregistrene» | **ja** | 25.08. / 14.09.2026 |
| `enhetsregisteret` | **NLOD 2.0** — gjelder det **frie** nivået, se merknad B | [brreg.no/…/apne-data](https://www.brreg.no/bruk-av-data-fra-bronnoysundregistrene/apne-data/), lisenstekst [data.norge.no/nlod/no/2.0](https://data.norge.no/nlod/no/2.0) | «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av Brønnøysundregistrene» | **ja** | 14.09.2026 |
| `lusetall` | NLOD | [barentswatch.no/artikler/api-vilkar](https://www.barentswatch.no/artikler/api-vilkar) | «Data levert av BarentsWatch» **+** «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet.» | **ja, uttrykkelig** | 12.09.2026 |
| `sjotemperatur` | NLOD | samme | «Data levert av BarentsWatch» | **ja, uttrykkelig** | 12.09.2026 |
| `trafikklysvedtak` | NLOD 2.0, via unntaket i Lovdatas punkt 2.3 | [lovdata.no/info/brukeravtale](https://lovdata.no/info/brukeravtale) | «hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | **ja**, men se merknad C | 12.09.2026 |
| `reguleringsomraader` | **CC BY 4.0** | [doi.org/10.21335/NMDC-1923112433](https://doi.org/10.21335/NMDC-1923112433) | navngivelse av opphavspersonene, se merknad D | **ja** | 14.09.2026 |
| `ekspertgruppen` | **UBELAGT** | ingen funnet — se merknad E | siteringsformen fra rapporten selv | **ukjent** | 14.09.2026 (søkt, ikke funnet) |

---

## Tabell 2 — det NETTSTEDET SELV distribuerer

Tabellen over er KILDENE: data vi henter, sammenstiller og gjengir.
Denne er noe annet — filer vi selv sender ut sammen med sidene, og som
har sine egne vilkår. Fram til 22.09.2026 var det én rad (Newsreader);
designoverleveringen gjorde det til seks.

Skillet er verdt en egen tabell fordi PLIKTEN er en annen. En kilde
krever en attribusjonssetning på siden; en font under OFL krever at
lisensteksten følger FILA, og det er et krav om et filnavn på en
adresse — ikke om en setning. Se `nettsted.VAART_LAAN`, som er raden
som faktisk står på /om/.

| hva | rolle | lisens | krever | ligger på | proveniens |
|---|---|---|---|---|---|
| Newsreader | overskrifter, ordmerke, nøkkeltall | SIL OFL 1.1 | lisensteksten følger fila | `/newsreader-OFL.txt` | `docs/design/NEWSREADER.md` |
| IBM Plex Sans | brødtekst, etiketter, tabeller | SIL OFL 1.1 | lisensteksten følger fila | `/ibmplex-OFL.txt` | `docs/design/IBM-PLEX.md` |
| IBM Plex Mono | tallverdier i tabellkolonner | SIL OFL 1.1 | samme fil som Sans | `/ibmplex-OFL.txt` | `docs/design/IBM-PLEX.md` |
| Herofotografiet | forsidens hero | Unsplash-lisensen | **ingenting** — navngiving er frivillig | — | `docs/design/HEROFOTO.md` |
| Kystlinje, Natural Earth 1:10 m | kartene | public domain | **ingenting** | `/naturalearth-LICENSE.md` | `docs/design/KARTGEOMETRI.md` |
| Produksjonsområdepolygoner | kartene | NLOD (Fiskeridirektoratet) | «Kilde: Fiskeridirektoratet» | dekkes av kildeattribusjonen | `docs/design/KARTGEOMETRI.md` |
| Pagefind 1.4.0 | søket på `/sok/` | MIT | **ingenting** | — | `docs/design/PAGEFIND.md` |

### Merknad I — Pagefind er et VERKTØY, ikke en avhengighet i runtime

Binæren (15,6 MB) ligger ikke i repoet og sendes ikke ut. Den kjøres
ved bygging og legger igjen `pagefind.js`, to WebAssembly-filer og
indeksen. MIT krever at lisenstekst og opphavsrettsmerknad følger med
«substantial portions of the Software»; `pagefind.js` og wasm-filene
bærer sine egne merknader slik CloudCannon la dem. Proveniensen —
utgivelse, sha256 av tarballen og sha256 av hver wasm-fil — står i
`docs/design/PAGEFIND.md` og i `publiseringsvakt.BINAERFILER_VERKTOY`.

### Merknad J — Kartverket, LEST 25.09.2026, IKKE TATT I BRUK

Lest i forkant av en mulig ekte kystlinje i kartene. **Ingen
Kartverket-data ligger i repoet eller i utputtet per 25.09.2026**, og
raden i tabell 2 skrives den dagen den første fila gjør det.

**Lisensen, ordrett fra Kartverkets egen vilkårsside**
([kartverket.no/api-og-data/vilkar-for-bruk](https://www.kartverket.no/api-og-data/vilkar-for-bruk),
lest 25.09.2026, sidas egen «Siste oppdatering» 21.07.26):

> Kartverkets gratisprodukt er lisensierte etter Creative Commons
> Navngivelse 4.0 international (CC BY 4.0).
>
> Dette inneber at Kartverkets namn skal visast i alle samanhengar der
> produkta eller uttrekk av produkta blir brukt, det vere seg
> applikasjonar, webløysingar, trykte produkt, illustrasjonar eller
> anna, på følgjande måte: © Kartverket. Det skal også linkast til
> nettsidene våre der det er mogleg.
>
> Nokre av produkta har opphavsrettsleg vern, nokre har databasevern,
> og nokre har gått ut på dato. Som det står i CC BY, omfattar denne
> berre det som er verna, og kravet til å oppgi kjelde gjeld difor så
> langt produktet er verna eller skal namngis av andre grunnar (god
> forretningsskikk).

Og om ansvar, samme side, ordrett:

> Kartverkets gratisprodukt blir distribuert slik dei er. Kartverket
> tar ikkje noko ansvar for bruk og vidarebruk. Kart frå historisk
> arkiv skal ikkje brukast til navigasjon.
>
> Brukarane må vere merksame på at kart ikkje alltid stemmer med
> terrenget, og bruken må skje på aktsamt vis i høve til utstyr og
> bruksområde.

**Attribusjonsformen er «© Kartverket», med lenke til kartverket.no.**
Det er den ordrette formen siden ber om, og den er kortere enn NLOD-
setningene i tabell 1 — CC BY 4.0 krever i tillegg at lisensen navngis
og lenkes, som er det `/om/`-tabellen gjør for hver rad i tabell 2.

#### Datasettene, med lisensen slik Geonorge oppgir den per datasett

Hvert datasett har sin EGEN lisensangivelse i Geonorges metadata, og
den er lest der og ikke antatt av vilkårssiden. Alle fem sier det
samme. Hentet fra `kartkatalog.geonorge.no/api/getdata/<uuid>`
25.09.2026:

| datasett | uuid | tilgang | lisens | bruksbegrensning, ordrett |
|---|---|---|---|---|
| N50 Kartdata | `ea192681-…-f3ce04c189ac` | Åpne data | CC BY 4.0 | «Ingen begrensninger på bruk er oppgitt» |
| N250 Kartdata | `442cae64-…-545bc1d9ab48` | Åpne data | CC BY 4.0 | «Ingen begrensninger på bruk er oppgitt.» |
| Dybdedata – kurver generaliserte | `871960a1-…-7886a4126d23` | Åpne data | CC BY 4.0 | (tom) |
| Dybdedata – terrengmodeller 50 m | `67a3a191-…-eaaf7c513549` | Åpne data | CC BY 4.0 | «Ingen begrensninger på bruk er oppgitt.» |
| Sjøkart – Dybdedata | `2751aacf-…-3532a51c529a` | Åpne data | CC BY 4.0 | «Dataene er ikke godkjent for navigasjon. De er ikke egnet for nøyaktige masseberegninger.» |

Lisenslenken hvert av dem oppgir er
[creativecommons.org/licenses/by/4.0](https://creativecommons.org/licenses/by/4.0/).

**Den siste raden bærer et vilkår de andre ikke har.** «Ikke godkjent
for navigasjon» er ikke en formalitet på et nettsted som viser
oppdrettsanlegg i sjøen: en dybdekurve tegnet ved siden av en lokalitet
ser ut som et sjøkart, og det er nettopp den lesningen Kartverket
fraskriver seg. Blir dybdedata tatt i bruk, må setningen stå ved
visningen — ikke bare i denne fila.

#### Størrelse, målt på Geonorges nedlastingstre 25.09.2026

Kartdataene finnes som statiske filer under
`nedlasting.geonorge.no/geonorge/Basisdata/`, i EUREF89 UTM 33N
(EPSG:25833) blant andre. Formatene er FGDB, GML, PostGIS og SOSI —
**ingen GeoJSON og ingen GeoPackage.**

    N50   ingen landsdekkende fil og ingen fylkesfil; per KOMMUNE
          Harstad 5503      5,3 MB     Bremanger 4648   16,3 MB
          Nordkapp 5620    11,0 MB     Hammerfest 5603  43,1 MB
    N250  landsdekkende GML-zip       354,4 MB
    N500  landsdekkende GML-zip        68,0 MB
    N1000 landsdekkende GML-zip        22,3 MB
    N2000 landsdekkende GML-zip         4,9 MB
    N5000 landsdekkende GML-zip         1,3 MB

Dybdedataene, målt samme sted og samme dag:

    Dybdedata – kurver generaliserte, landsdekkende
        SOSI-zip   104,7 MB       S57-zip    91,7 MB
        (ingen GML, ingen GeoJSON, ingen GeoPackage)

    Dybdedata (fulle), per kommune/fylke i GML
        427 filer, 18,4 GB til sammen

Kildens egen beskrivelse av de generaliserte kurvene, ordrett:
«Inneholder generaliserte dybdekurver for norske kyst- og havområder.
Dybdekurvene er grove og har varierende kvalitet og nøyaktighet.»

INGENTING ER BYGGET MED DEM. Dette er lisensen og størrelsen, som var
det som ble bedt om.

### Merknad G — de to som ikke krever noe

Unsplash-lisensen og Natural Earths vilkår krever ingen navngiving.
Begge er likevel navngitt, på /om/ og i proveniensfilene, og det er
ikke en misforståelse av lisensen: en side som ikke sier hvor et bilde
eller en kystlinje kommer fra, kan ingen etterprøve. Det er samme
grunn som at datokolonnen i tabellen over finnes.

Natural Earth ber uttrykkelig om at kreditering IKKE er nødvendig, og
oppgir en formulering for dem som vil likevel: «Made with Natural
Earth.» Den står i `docs/design/KARTGEOMETRI.md`.

### Merknad H — polygonene er NLOD, og de er fra en karttjeneste

`produksjonsomrader.geojson` er hentet fra Fiskeridirektoratets egen
ArcGIS-tjeneste, ikke fra en av kildene i `sources/`. Lisensen er
likevel den samme — merknad A gjelder «den som tar i bruk data fra
Fiskeridirektoratet» og skiller ikke på hvilket endepunkt dataene kom
fra. Attribusjonen «Kilde: Fiskeridirektoratet» står allerede i
bunnteksten på hver side som viser kartet, fordi `akvakultur` er en av
sidens kilder.

**Ett felt i den fila brukes IKKE:** `status`, som bærer «grønn», «gul»
og «rød». Se `kart.py` — fargen er et forvaltningsvedtak med en dato og
en hjemmel, og et statusfelt i et karttjenestelag er en gjengivelse av
det uten noen av delene.

---

## Merknad A — Fiskeridirektoratet

Ordlyden er hentet fra `docs/KILDE-BIOMASSE.md` punkt 10, ikke gjengitt
fra hukommelsen. Lisenssiden ble lest 25.08.2026:

> «Den som tar i bruk data fra Fiskeridirektoratet godtar automatisk
> lisensen.»

Ingen registrering, ingen avtale, ingen søknad, ingen nøkkel. Godkjente
attribusjonsformer er «Kilde: Fiskeridirektoratet», «Kilde rådata:
Fiskeridirektoratet» eller «Kilde for rådata som vi har benyttet i vår
sammenstilling: Fiskeridirektoratet». Attribusjonen skal ikke
fremstilles som om Fiskeridirektoratet anbefaler eller går god for vår
sammenstilling.

Gjelder alle fem fiskeridirektoratkildene: `akvakultur`, `biomasse`,
`biomasselag`, `romming` og `eierskap` (`pub-aqua`).

## Merknad B — Brønnøysundregistrene, og HVILKET nivå lisensen gjelder

Luken fra 12.09.2026 er lukket 14.09.2026. Raden sto som ULEST fordi
ingen hadde lest Brregs egen lisensside; det er nå gjort.

### Lisensen, ordrett fra Brregs egen side

Fra `brreg.no/bruk-av-data-fra-bronnoysundregistrene/apne-data/`:

> «Datasettene følger Norsk lisens for åpne data (NLOD). Det er ikke
> nødvendig å registrere seg for å ta datasettet i bruk.»

API-dokumentasjonen på `data.brreg.no` er mer presis om versjonen og
lenker til lisensteksten:

> «License: Norsk lisens for offentlige data (NLOD)» →
> `data.norge.no/nlod/no/2.0`

**NLOD 2.0** er altså versjonen. Ingen registrering, ingen avtale, ingen
nøkkel — samme form som Fiskeridirektoratet.

### Attribusjonssetningen kommer fra NLOD, ikke fra Brreg

Dette er forskjellen fra Fiskeridirektoratet, og den er verdt å skrive
ned i stedet for å pusse bort: **Brreg oppgir ingen egen
attribusjonsform.** Fiskeridirektoratet lister tre godkjente varianter
av «Kilde: Fiskeridirektoratet»; Brreg sier bare at datasettene følger
NLOD.

Det er nettopp tilfellet NLOD 2.0 punkt 5 er skrevet for. Ordrett fra
lisensteksten, lest 14.09.2026:

> «Hvis lisensgiver ikke spesifiserer hvordan navngivelse bør foretas,
> skal lisenstaker normalt oppgi følgende: "Inneholder data under Norsk
> lisens for offentlige data (NLOD) tilgjengeliggjort av [navnet på
> lisensgiver]".»

Med lisensgiver satt inn blir setningen vår:

> **«Inneholder data under Norsk lisens for offentlige data (NLOD)
> tilgjengeliggjort av Brønnøysundregistrene»**

Den er ordrett i den forstand som teller — den er lisensgiverens egen
foreskrevne form, ikke vår omskriving. At den måtte hentes ett ledd
lenger ut enn Fiskeridirektoratets, er en opplysning om kjeden og ikke
en svakhet ved den.

**Kommersiell bruk:** NLOD 2.0 bruker ikke ordet «kommersiell» i det
hele tatt. Retten følger av at lisensen gir rett til å «kopiere, bruke
og tilgjengeliggjøre informasjon» og er «ikke-eksklusiv, vederlagsfri og
uten tidsmessige eller geografiske begrensninger». Ja i tabellen betyr
altså **ingen begrensning**, ikke en uttrykkelig tillatelse — til
forskjell fra BarentsWatch, som sier det rett ut. Skillet er lite og
skal likevel stå.

**Hvor attribusjonen må stå.** NLOD 2.0 er mildere enn BarentsWatch her,
og det er verdt å vite hvilken av dem som setter kravet:

> «det er ikke et krav at navngivelse foregår på samme side som
> informasjonen presenteres på, det er nok at kildehenvisningen blir
> plassert på en "Om"-side eller lignende … Kildehenvisningen må likevel
> ikke være bortgjemt, eller vanskelig å finne.»

En «Om»-side holder for NLOD. Den holder **ikke** for BarentsWatch, som
krever synlighet for sluttbruker. Den strengeste plikten er den som
gjelder i en visning som blander kildene — se TODO-en i
`docs/VISNING.md`.

### Hvilket NIVÅ lisensen gjelder: bare det frie

Enhetsregisteret har to tilgangsnivåer, og **vi bruker utelukkende det
frie**. Det er ikke en detalj: lisensen over gjelder de åpne
datasettene, og ville ikke uten videre dekket det andre nivået.

| nivå | hva | bruker vi? |
|---|---|---|
| `data.brreg.no/enhetsregisteret/api/enheter` — åpne data | grunndata, næringskode, organisasjonsform, ansatte, konkurs- og avviklingsflagg. Ingen nøkkel, ingen avtale | **ja, bare dette** |
| `data.brreg.no/enhetsregisteret/autorisert-api/…` | roller **inklusive fødselsnummer** for personer, oppslag på fødselsnummer. Sikret med Maskinporten, krever scope `brreg:data:enhetsregisteret:roller:person:oppslag:fnr` | **nei** |

Det autoriserte nivået er ikke bare en annen lisens — det er nøyaktig
den grensen **CLAUDE.md regel 3** forbyr oss å krysse. Roller med
fødselsnummer ville gjort repoet til et personregister med
behandlingsansvar. Kilden henter ikke roller i det hele tatt, og det er
en beslutning som står uavhengig av hva lisensen måtte tillate:
**regelen er strengere enn vilkåret, og det er regelen som gjelder.**

En tredje vei finnes også, og den er heller ikke vår: et abonnement på
«full tilgang» med signert avtale og årlig vederlag for private aktører.
Det gir teknisk tilgang, ikke andre data enn nivåene over.

**Én ting i premisset er IKKE bekreftet.** At det autoriserte API-et er
forbeholdt kredittopplysningsforetak og finansforetak, er ikke å finne i
Brregs egen dokumentasjon: API-dokumentasjonen navngir ingen
kvalifiserte grupper, bare Maskinporten-kravet og scopet.
Abonnementssiden skiller på offentlige og private aktører, ikke på
bransje. Hvem som faktisk innvilges scopet er dermed **ULEST** — det
endrer ingenting for oss, siden vi uansett ikke søker, men det skal ikke
stå i denne fila som om det var etterprøvd.

## Merknad C — Lovdata, og grensen som faktisk biter

Lest 12.09.2026. Brukeravtalen er sist oppdatert 31.10.2025.

Hovedregelen i punkt 2.1 er streng:

> «Du kan bruke innholdet på de åpne tjenestene for egne, private,
> ikke-kommersielle formål.»

> «Du har ikke rett til å distribuere, publisere eller mangfoldiggjøre
> innholdet uten skriftlig tillatelse fra Lovdata. Massenedlasting av
> innholdet er ikke tillatt.»

**Men punkt 2.3 gjør unntak, og unntaket dekker nøyaktig det vi
henter:**

> «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke
> og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som
> kilde og ellers følger vilkårene i NLOD 2.0:»

Listen omfatter **«Regelverk i Norsk Lovtidend»**, «Gjeldende formelle
lover» og «Gjeldende sentrale forskrifter».

Det er verdt å merke seg hvorfor dette treffer oss presist.
`docs/KILDE-TRAFIKKLYSVEDTAK.md` punkt 4 fastslår at kilden leser
**LTI-kroppene, ikke SF** — den kunngjorte teksten i Norsk Lovtidend,
ikke den konsoliderte forskriften. Valget ble tatt av en helt annen
grunn (en LTI-kropp er fast, en SF-kropp er en bevegelig referanse, jf.
CLAUDE.md 1b-4), men det plasserer oss i den første kulen i Lovdatas
egen unntaksliste. Kommersiell bruk er dermed tillatt gjennom NLOD 2.0.

**Grensen som gjelder oss:**

> «Massenedlasting og systematiske uttrekk er ikke tillatt. For større
> nedlastinger, bruk våre åpne API-er.»

Kilden henter fem kropper, én gang hver, og arkiverer dem. Det er ikke
massenedlasting. Men skulle `trafikklysvedtak` noen gang utvides til å
tråle Lovdata bredt, er dette vilkåret det som stenger veien, og da er
det API-et som er inngangen — ikke flere HTTP-kall mot nettsidene.

## Merknad D — reguleringsområdene, CC BY 4.0

Lisensen var oppgitt av Pål Næverlid Sævik ved Havforskningsinstituttet
09.09.2026. Den er nå **bekreftet mot hjemmelen selv**, NMDCs
landingsside for datasettet, lest 14.09.2026:

    Creative Commons Attribution 4.0 International License (CC BY 4.0)
    «Smittekontakt (lakselus) mellom oppdrettsanlegg og oppholdsområder
    for villfisk»
    Utgiver: Havforskningsinstituttet

Det er en oppgradering av grunnlaget, ikke en ny opplysning: påstanden
hvilte på en e-post, og hviler nå på utgiverens egen metadatapost. CC BY
4.0 tillater kommersiell bruk og krever navngivelse. Siteringen står i
`README.md` under Havforskningsinstituttet.

**Merk at datasettets tittel hos NMDC ikke er rapportens tittel.**
Rapporten heter *Forslag til reguleringsområder for utslipp av
lakselus*; datasettet heter «Smittekontakt (lakselus) mellom
oppdrettsanlegg og oppholdsområder for villfisk». Det er rapporten
README siterer og datasettet lisensen gjelder.

## Merknad E — ekspertgrupperapportene er UBELAGT

Søkt 14.09.2026, ikke funnet. Dette er en **ikke-funnet lisens**, ikke
en lisens som mangler fordi ingen har lett.

Det som ble prøvd:

- Brage-handlene for 2023, 2024 og 2025
  (`hdl.handle.net/11250/3104585` m.fl.) videresender til
  `nva.sikt.no`, som er en SPA — landingssiden gir ingen tekst til en
  vanlig henting, og dermed heller ingen rettighetserklæring.
- Havforskningsinstituttets egne sider for *Rapport fra havforskningen*
  oppgir ISSN og serieinformasjon, men ingen lisens- eller
  gjenbruksvilkår.

`docs/KILDE-EKSPERTGRUPPEN.md` punkt 11 sier det som ER belagt:
rapportene er offentlige utredninger levert Nærings- og
fiskeridepartementet, uten nøkkel, registrering eller avtale, og
sitering følger rapportenes egen form.

**Hva statusen betyr i praksis.** Å lese, sitere og trekke ut tall for
analyse er dekket av vanlig sitatrett og av at dette er offentlige
utredninger. Det som IKKE er belagt, er retten til å republisere
kroppene eller å bygge en kommersiell tjeneste på dem. Kilden er derfor
trygg der den står i dag — og er den ene som må avklares før en
publisert visning lener seg på den.

**Hvordan luken lukkes:** ett spørsmål til Havforskningsinstituttet
eller NINA om hvilken lisens ekspertgrupperapportene utgis under. Det
er ikke mer kode; det er en e-post. Samme form som det åpne spørsmålet
om `(null)`-kategorien i `docs/KILDE-BIOMASSE.md` punkt 11.

## Merknad F — BarentsWatch, de fire pliktene ved siden av attribusjonen

Vilkårene på `www.barentswatch.no/artikler/api-vilkar` er sist oppdatert
02.11.2023 og lest 12.09.2026. Data fra BarentsWatch-API-ene er under
NLOD med mindre API-dokumentasjonen sier noe annet, og **kommersiell
bruk er uttrykkelig tillatt**.

Attribusjonen skal være synlig for **sluttbruker**, ikke bare i et repo.
Begge setningene, ordrett:

> «Data levert av BarentsWatch»

> «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra
> Mattilsynet.»

Den andre er dataeierattribusjonen og gjelder lusetallene. Den er ikke
valgfri fordi vi henter fra BarentsWatch og ikke fra Mattilsynet — det
er nettopp da den trengs.

Fire plikter til, som ikke er attribusjon og derfor lett faller ut:

1. **Kommersielle brukere bes registrere API-klienten** med formål,
   firma og kontaktperson.
2. **BarentsWatch skal kontaktes før høytrafikkbruk.** Ellers kan de
   fakturere serverkostnader. Dagens kadens er én ukentlig kjøring, og
   backfillen er unnagjort — men en ny backfill over 762 uker er
   nettopp det denne plikten handler om.
3. **«BarentsWatch» kan ikke inngå i tjenestenavnet.**
4. **Datainnholdet skal ikke endres.** Vårt arkivlag oppfyller dette av
   seg selv: rå-kroppen lagres uendret og hashet før noe parses. Det
   som avledes (`kildeledd`) er merket som avledet og er ikke en
   gjengivelse av kildens data.

Punkt 1 og 2 er de eneste stedene i hele lisenskjeden der et vilkår
krever en HANDLING fra oss og ikke bare en setning i en visning. Ingen
av dem er utført per 14.09.2026, og ingen av dem er utløst ennå.

---

## Det som må skje før publisering

Rekkefølgen er den samme som alvorlighetsgraden:

1. **`ekspertgruppen` er UBELAGT.** Avklar med HI/NINA før en visning
   lener seg på rapportene. Eneste gjenstående hull i kjeden.
2. ~~**De to BarentsWatch-setningene må stå synlig for sluttbruker**, og
   Brregs NLOD-setning må med der Enhetsregisteret vises.~~ **Gjort
   16.09.2026** for den publiserte siden: `nettsted.py` bygger
   bunnteksten av kildenes egne `Source.attribusjon` (flyttet dit
   16.09.2026, se beslutningen), per kilde siden faktisk bruker, og
   nekter å rendre en side som lener seg på en UBELAGT kilde. Den
   interne `oversikt.html` har det fortsatt ikke, og kravet er ikke
   utløst der. Se TODO-en i `docs/VISNING.md`.

   **Og det gjelder DATAFILENE, ikke bare sidene.**
   `/lokalitet/<nr>/lusetall.csv` bærer setningene i et kommentarhode i
   FILA — ikke i en sidecar, som ville vært borte i det øyeblikket noen
   laster ned CSV-en alene. Et vilkår som bare er oppfylt så lenge to
   filer holder sammen, svikter stille. CSV-en bærer BARE
   lusetallkildens setninger: den inneholder ingen data fra
   Fiskeridirektoratet eller Brreg, og et hode som sa noe annet ville
   vært en påstand om at de har levert noe her.
3. **Registrering hos BarentsWatch** hvis bruken blir kommersiell.

Lukket 14.09.2026: Brregs ordrette attribusjonssetning, som sto som
ULEST fra 12.09. Se merknad B.
