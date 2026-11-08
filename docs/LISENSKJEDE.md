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

**Vilkårssidene ligger i arkivet fra 06.10.2026.** Fram til da var
sitatene i denne fila lest, men ikke tatt vare på: ingen kunne etterprøve
hva en side faktisk sa den dagen den ble lest. `arkiver_vilkar.py`
lagrer nå BarentsWatchs, Fiskeridirektoratets, Brregs og Lovdatas side
som kropper med sha256 i `data/arkiv/vilkar-<part>/` i datarepoet, én gang
i måneden (`vilkar.yml`), og bare når kroppen er ny. Loggfila
`data/arkiv/vilkar/<dato>.logg.json` har i tillegg en hash av den synlige
teksten, så en endring i vilkårene kan skilles fra en endring i markupen.
Sitatene under er fortsatt lest for hånd; kroppene er belegget.

---

## Produktene

**Et produkt er salgbart bare når ingen av kildene det bruker er
UBELAGT.** Statusen per kilde er radens i mappetabellen under; der en
mappe er delt, står delen produktet bruker. `tests/test_lisensdekning.py`
feiler når en kilde her mangler rad, og når «salgbart» ikke er det
statusene gir.

| produkt | kilder og status | salgbart |
|---|---|---|
| Ukentlig hendelsesvarsel | `akvakultur` belagt · `biomasse` belagt · `biomasselag` belagt · `romming` belagt · `eierskap` belagt · `eierskap_historikk` belagt · `enhetsregisteret` belagt · `lusetall` belagt · `sjotemperatur` belagt · `trafikklysvedtak` belagt | **ja** |
| Kommuneanalyse: havbruksfondet | `havbruksfondet:utbetalinger` belagt · `havbruksfondet:instrukser` UBELAGT · `havbruksfondet:pressemeldinger` UBELAGT · `akvakultur` belagt · `biomasse` belagt | **nei** — UBELAGT: `havbruksfondet:instrukser`, `havbruksfondet:pressemeldinger` |
| Dokumentert registeruttrekk | `akvakultur` belagt · `eierskap` belagt · `eierskap_historikk` belagt · `eierskap-overforinger` belagt · `enhetsregisteret` belagt · `enhetsregisteret_oppslag` belagt · `biomasse` belagt · `lusetall` belagt | **ja** |
| Analyse på oppdrag | `akvakultur` belagt · `biomasse` belagt · `lusetall` belagt · `eierskap` belagt · `enhetsregisteret` belagt · `trafikklysvedtak` belagt · `reguleringsomraader` belagt · `unntaksvekst` belagt i lov · `mattilsynet-lakselus` belagt · `ekspertgruppen` UBELAGT · `styringsgruppen` UBELAGT · `regjeringen-horing` UBELAGT · `stortingsmeldinger` UBELAGT | **nei** — UBELAGT: `ekspertgruppen`, `styringsgruppen`, `regjeringen-horing`, `stortingsmeldinger` |

*Ingen av de fire produktene finnes ennå* (R4 del 2.3). Kildelistene er
ANTATT, lest 08.11.2026: hendelsesvarselet er kildene ukesendringene på
nettstedet bygger på i dag (`nettsted.ukentlige_kilder()`, uten
`unntaksvekst`, som ikke publiseres); kommuneanalysen er det
`docs/MALING-HAVBRUKSFOND.md` leser — utbetalingene, instruksen som gir
fordelingen, og pressemeldingene som daterer dem; analysen på oppdrag er
det et oppdrag typisk ville trengt utover registrene.

«Salgbart» gjelder lisensen. To ting står utenfor den kolonnen:
**BarentsWatch** (`lusetall`, `sjotemperatur`) ber profesjonelle brukere
oppgi virksomhet og formål, merknad F; og **registeruttrekket** bærer
personopplysninger i rålaget (`eierskap-overforinger`,
`enhetsregisteret` fra før 09.11.2026), se
`docs/BEHANDLINGSGRUNNLAG-UTKAST.md`. Et uttrekk går gjennom lesedøra,
ikke rett fra arkivet.

---

## Tabellen

| kilde | lisens | hjemmel | attribusjon, ordrett | kommersiell | lest |
|---|---|---|---|---|---|
| `akvakultur` | **NLOD 1.0** — lisenssiden lenker dit, se merknad A | [fiskeridir.no](https://www.fiskeridir.no/statistikk-tall-og-analyse/lisens-for-bruk-av-fiskeridirektoratets-data) | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026, versjonen 04.11.2026 |
| `biomasse` | **NLOD 1.0** | samme | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026, versjonen 04.11.2026 |
| `biomasselag` | **NLOD 1.0** | samme | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026, versjonen 04.11.2026 |
| `romming` | **NLOD 1.0** | samme | «Kilde: Fiskeridirektoratet» | **ja** | 25.08.2026, versjonen 04.11.2026 |
| `eierskap` | **NLOD 1.0** (Fiskeridir.) + **NLOD 2.0** (Brreg) | [fiskeridir.no](https://www.fiskeridir.no/statistikk-tall-og-analyse/lisens-for-bruk-av-fiskeridirektoratets-data) + [brreg.no/…/datasett-og-api](https://www.brreg.no/bruke-data-fra-bronnoysundregistrene/datasett-og-api/) | «Kilde: Fiskeridirektoratet» **+** «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av Brønnøysundregistrene» | **ja** | 25.08. / 14.09.2026 |
| `enhetsregisteret_oppslag` (oppslag på enkeltnummer, `backfill.py --oppslag`) | **NLOD 2.0**, som `enhetsregisteret` | samme | som `enhetsregisteret` | **ja** | 04.11.2026 |
| `enhetsregisteret` | **NLOD 2.0** — gjelder det **frie** nivået, se merknad B | [brreg.no/…/datasett-og-api](https://www.brreg.no/bruke-data-fra-bronnoysundregistrene/datasett-og-api/), lisenstekst [data.norge.no/nlod/no/2.0](https://data.norge.no/nlod/no/2.0) | «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av Brønnøysundregistrene» | **ja** | 14.09.2026 |
| `lusetall` | NLOD | [barentswatch.no/artikler/api-vilkar](https://www.barentswatch.no/artikler/api-vilkar) | «Data levert av BarentsWatch» **+** «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet.» | **ja, uttrykkelig** | 12.09.2026 |
| `sjotemperatur` | NLOD | samme | «Data levert av BarentsWatch» | **ja, uttrykkelig** | 12.09.2026 |
| `trafikklysvedtak` | NLOD 2.0, via unntaket i Lovdatas punkt 2.3 | [lovdata.no/info/brukeravtale](https://lovdata.no/info/brukeravtale) | «hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | **ja**, men se merknad C | 12.09.2026 |
| `reguleringsomraader` | **CC BY 4.0** | [doi.org/10.21335/NMDC-1923112433](https://doi.org/10.21335/NMDC-1923112433) | navngivelse av opphavspersonene, se merknad D | **ja** | 14.09.2026 |
| `ekspertgruppen` | **UBELAGT** | ingen funnet — se merknad E | siteringsformen fra rapporten selv | **ukjent** | 14.09.2026 (søkt, ikke funnet) |
| departementets kunngjøringer på regjeringen.no (`beslutning.py`; ikke en kilde i `sources/`) | **UBELAGT** | ingen funnet — se merknad M | — | **ukjent** | 04.11.2026 (søkt i arkivet, ikke funnet) |
| `unntaksvekst` | **belagt i lov 09.10.2026**: uten vern, åndsverkloven § 14 — se merknad K | [lovdata.no/lov/2018-06-15-40/§14](https://lovdata.no/lov/2018-06-15-40/§14), arkivert i `lovdata-andsverkloven/` | ingen krav i loven; som praksis Mattilsynets egen form, «(Kilde: Mattilsynet, nettadressa og datoen du gjenga teksten.)» | **ja** — ingen enerett å begrense den (lesning, merknad K) | 09.10.2026 |
| Mattilsynets åpne API (ikke en kilde; hentet for analysen av unntaksvekst) | **NLOD 2.0** | spesifikasjonen selv, `info.license`, arkivert i `mattilsynet-openapi/` | standardformen i NLOD 2.0: «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av Mattilsynet» | **ja** | 09.10.2026 |
| `akvakultur-flater` (fangst, `arkiver_flater.py`; ikke en kilde) | NLOD | samme som `akvakultur`, arkivert i `vilkar-fiskeridir/`; laget sier selv «Fiskeridirektoratet / Akvakulturregister» | «Kilde: Fiskeridirektoratet» | **ja** | 03.11.2026 |
| `akvakultur-soknader` (fangst, `arkiver_soknader.py`; ikke en kilde) | NLOD | samme som `akvakultur`, arkivert i `vilkar-fiskeridir/` («All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD)»); tjenesten sier selv «Fiskeridirektoratet» i `copyrightText` | «Kilde: Fiskeridirektoratet» | **ja** | 03.11.2026 |
| `lusetall-innkomst-v2` (fangst, `arkiver_luseinnkomst.py --v2`) | NLOD | samme som `lusetall`, arkivert i `vilkar-barentswatch/`; spesifikasjonen har ingen `info.license` | som `lusetall` | **ja, uttrykkelig** | 03.11.2026 |
| `utgivelse-regomr` (vakt, `utgivelsesvakt.py`) | **CC BY 4.0** | NMDCs landingsside, arkivert i `vilkar-nmdc/` fra 03.11.2026 | som `reguleringsomraader`, merknad D | **ja** | 03.11.2026 |
| bransjemedia: Fiskeribladet, Intrafish (ikke fanget) | **fangst krever avtale** | `/vilkar` på hvert nettsted, arkivert i `vilkar-fiskeribladet/` og `vilkar-intrafish/` | — | **nei** uten avtale: «skraping, crawling, indeksering, tekst/datautvinning» krever gyldig avtale | 03.11.2026 |
| bransjemedia: Kyst.no, iLaks (ikke fanget) | **UBELAGT** | Kyst.no: bare Oceanspace Medias abonnementsvilkår, arkivert i `vilkar-kyst/`; iLaks: ingen vilkårsside funnet | — | **ukjent** | 03.11.2026 (søkt) |

---

## Mappetabellen — hver mappe i `data/arkiv/` og hver kilde i `sources/`

Tabellen over har én rad per KILDE. Denne har én rad per MAPPE i
datarepoets arkiv og per kildenavn i `sources/`, fordi det er mappene som
inneholder det vi har tatt vare på — og R4 (04.11.2026) fant 23 mapper med
innhold som ingen rad nevnte, blant dem havbruksfondet, AIS og
styringsgruppen. En mappe kommer til av seg selv når en fangst skriver
sin første kropp; en rad kommer bare til når noen skriver den.

Hver rad bærer **vilkåret ordrett** for kommersiell bruk, videresalg og
attribusjon, **datoen** det ble lest, og **den arkiverte vilkårssiden**
sitatene står i (`mappe/fil` under `data/arkiv/`). Sitatene er holdt mot
kroppen, ikke mot nettsiden: `verktoy/lisensdekning.py` sier fra om et
sitat som ikke står i den arkiverte teksten, og om en mappe eller et
kildenavn uten rad.

**Uklart = UBELAGT**, og grunnen står i vilkårskolonnen. Der en mappe
bærer innhold fra flere utgivere med ulike vilkår, er den delt
(`havbruksfondet:utbetalinger`, `:instrukser`, `:pressemeldinger`); et
produkt som bruker mappa, arver den svakeste delen det faktisk bruker.
`*` er et mønster: `vilkar-*` dekker hver vilkårsmappe.

| mappe | utgiver | vilkår, arkivert | kommersiell bruk | videresalg | attribusjon | lest | status |
|---|---|---|---|---|---|---|---|
| `akvakultur` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `biomasse` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `biomasselag` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `romming` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `eierskap` | Fiskeridirektoratet + Brreg | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` + `vilkar-brreg/2026-11-02.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» + Brreg: «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Brønnøysundregistrene | 08.11.2026 | belagt |
| `eierskap_historikk` | som `eierskap` | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` + `vilkar-brreg/2026-11-02.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» + Brreg: «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Brønnøysundregistrene | 08.11.2026 | belagt |
| `enhetsregisteret` | Brreg, det frie nivået | `vilkar-brreg/2026-11-02.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «Datasettene følger Norsk lisens for åpne data (NLOD)» | NLOD 2.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | siden oppgir ingen; NLOD 2.0 punkt 5 (merknad B): «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Brønnøysundregistrene | 08.11.2026 | belagt |
| `enhetsregisteret_oppslag` | Brreg, det frie nivået | `vilkar-brreg/2026-11-02.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «Datasettene følger Norsk lisens for åpne data (NLOD)» | NLOD 2.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | siden oppgir ingen; NLOD 2.0 punkt 5 (merknad B): «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Brønnøysundregistrene | 08.11.2026 | belagt |
| `lusetall` | BarentsWatch, dataeier Mattilsynet | `vilkar-barentswatch/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet» | 08.11.2026 | belagt |
| `sjotemperatur` | BarentsWatch | `vilkar-barentswatch/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch» | 08.11.2026 | belagt |
| `trafikklysvedtak` | Lovdata (Norsk Lovtidend) | `vilkar-lovdata/2026-11-02.bin.gz` | «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | samme; «Massenedlasting og systematiske uttrekk er ikke tillatt.» | «hvis du oppgir Lovdata som kilde» | 08.11.2026 | belagt |
| `reguleringsomraader` | Havforskningsinstituttet via NMDC | `vilkar-nmdc/2026-11-03.bin.gz` | «Creative Commons Attribution 4.0 International License» | «Use Constraints CC BY 4.0» | navngivelse etter CC BY 4.0, merknad D; siden: «Use Constraints CC BY 4.0» | 08.11.2026 | belagt |
| `ekspertgruppen` | ekspertgruppen (HI, NINA m.fl.) | `vilkar-nva-ekspertgruppen-2023/2026-11-08.bin.gz`, `-2024/`, `-2025/`: hver fil har «https://nva.sikt.no/license/copyright-act/1.0» («Generelle bruksvilkår»), ingen åpen lisens; merknad E | — | — | — | 08.11.2026 | **UBELAGT** |
| `unntaksvekst` | Mattilsynet | `lovdata-andsverkloven/2026-10-09.bin.gz` (§ 14, merknad K) + `vilkar-mattilsynet/2026-11-08.bin.gz` (praksis) | «Lover, forskrifter, rettsavgjørelser og andre vedtak av offentlig myndighet er uten vern etter denne loven.» | samme | ingen krav i loven; praksis: «(Kilde: Mattilsynet, nettadressa og datoen du gjenga teksten.)» | 09.10.2026 | belagt i lov |
| `akvakultur-flater` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `akvakultur-soknader` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `auksjon` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `eierskap-overforinger` | Fiskeridirektoratet | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `eierskap-brreg` | Brreg | `vilkar-brreg/2026-11-02.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «Datasettene følger Norsk lisens for åpne data (NLOD)» | NLOD 2.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | siden oppgir ingen; NLOD 2.0 punkt 5 (merknad B): «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Brønnøysundregistrene | 08.11.2026 | belagt |
| `havbruksfondet:utbetalinger` | Fiskeridirektoratet (regnearkene) | `vilkar-fiskeridir/2026-11-08.bin.gz` + `vilkar-nlod-1.0/2026-11-08.bin.gz` | «All bruk av data fra Fiskeridirektoratet er underlagt Norsk lisens for offentlige data (NLOD).» | «Data som er lisensiert under NLOD kan fritt viderebrukes på vilkårene som er utarbeidet av Difi»; NLOD 1.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | «Kilde: Fiskeridirektoratet»; «Kildehenvisningen skal ikke gi inntrykk av at Fiskeridirektoratet godkjenner eller anbefaler det som presenteres eller den som presenterer.» | 08.11.2026 | belagt |
| `havbruksfondet:instrukser` | Nærings- og fiskeridepartementet, lagt ut av Fiskeridirektoratet | uklart om «data fra Fiskeridirektoratet» dekker departementets instruks; at § 14 dekker den, er en lesning ingen har gjort | — | — | — | 08.11.2026 | **UBELAGT** |
| `havbruksfondet:pressemeldinger` | regjeringen.no via Wayback | `vilkar-regjeringen/2026-11-08.bin.gz` gjelder bare «Bilder og videomateriale på regjeringen.no»; ingen side for tekst. regjeringen.no svarer 403, siden er lest via Wayback | — | — | — | 08.11.2026 | **UBELAGT** |
| `ntb-pressemeldinger` | NFD via NTB (`arkiver_havbruksfond.py`; ingen kropp ennå) | pressemeldingene er departementets; som `regjeringen-pressemeldinger` | — | — | — | 08.11.2026 | **UBELAGT** |
| `lusetall-innkomst` | BarentsWatch, dataeier Mattilsynet | `vilkar-barentswatch/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet» | 08.11.2026 | belagt |
| `lusetall-innkomst-v2` | BarentsWatch, dataeier Mattilsynet | `vilkar-barentswatch/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet» | 08.11.2026 | belagt |
| `lusetall-innkomst-lokalitet` | BarentsWatch, dataeier Mattilsynet | `vilkar-barentswatch/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet» | 08.11.2026 | belagt |
| `ais-bw` | BarentsWatch, dataeier Kystverket | `vilkar-barentswatch/2026-11-08.bin.gz` + `vilkar-kystverket/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene»; «Data er gratis og tilgjengelig for alle, og dataene er regulert under Norsk Lisens for offentlige data – NLOD» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Ekstern bruk av Kystverkets AIS-data må krediteres Kystverket.» | 08.11.2026 | belagt |
| `ais-bw-full-5min` | BarentsWatch, dataeier Kystverket | `vilkar-barentswatch/2026-11-08.bin.gz` + `vilkar-kystverket/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene»; «Data er gratis og tilgjengelig for alle, og dataene er regulert under Norsk Lisens for offentlige data – NLOD» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Ekstern bruk av Kystverkets AIS-data må krediteres Kystverket.» | 08.11.2026 | belagt |
| `ais-bw-get-5min` | BarentsWatch, dataeier Kystverket | `vilkar-barentswatch/2026-11-08.bin.gz` + `vilkar-kystverket/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene»; «Data er gratis og tilgjengelig for alle, og dataene er regulert under Norsk Lisens for offentlige data – NLOD» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Ekstern bruk av Kystverkets AIS-data må krediteres Kystverket.» | 08.11.2026 | belagt |
| `ais-bw-hist` | BarentsWatch, dataeier Kystverket | `vilkar-barentswatch/2026-11-08.bin.gz` + `vilkar-kystverket/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene»; «Data er gratis og tilgjengelig for alle, og dataene er regulert under Norsk Lisens for offentlige data – NLOD» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Ekstern bruk av Kystverkets AIS-data må krediteres Kystverket.» | 08.11.2026 | belagt |
| `ais-bw-hist-5min` | BarentsWatch, dataeier Kystverket | `vilkar-barentswatch/2026-11-08.bin.gz` + `vilkar-kystverket/2026-11-08.bin.gz` | «Du har lov til å bruke data hentet via BarentsWatch i kommersiell sammenheng, så lenge du følger alle retningslinjene»; «Data er gratis og tilgjengelig for alle, og dataene er regulert under Norsk Lisens for offentlige data – NLOD» | «Du har lov til å videredistribuere innholdet dersom du krediterer oss og dataeier»; «Du kan ikke endre på innholdet i data som leveres.» | «Data levert av BarentsWatch»; «Ekstern bruk av Kystverkets AIS-data må krediteres Kystverket.» | 08.11.2026 | belagt |
| `ais-manifest` | oss: sha256-lister over AIS-filene på kystvakt-1 | ingen tredjeparts innhold; AIS-vilkåret står på `ais-bw` | — | — | — | 08.11.2026 | egen |
| `ais-5632` | Kystverket, udokumentert port | porten er ikke dokumentert noe sted (`MALING-AIS.md`); `vilkar-kystverket/2026-11-08.bin.gz` nevner den ikke | — | — | — | 08.11.2026 | **UBELAGT** |
| `mattilsynet` | Mattilsynets åpne API (loggene) | `mattilsynet-openapi/2026-10-09.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «https://data.norge.no/nlod/no/2.0» | NLOD 2.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | spesifikasjonen oppgir ingen; NLOD 2.0 punkt 5: «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Mattilsynet | 08.11.2026 | belagt |
| `mattilsynet-lakselus` | Mattilsynets åpne API | `mattilsynet-openapi/2026-10-09.bin.gz` + `vilkar-nlod-2.0/2026-11-08.bin.gz` | «https://data.norge.no/nlod/no/2.0» | NLOD 2.0: «deriblant å distribuere, overføre, spre, vise, fremføre, selge, låne ut og leie ut» | spesifikasjonen oppgir ingen; NLOD 2.0 punkt 5: «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av» Mattilsynet | 08.11.2026 | belagt |
| `hi-lakselus-ukesstatus` | Havforskningsinstituttet | hi.no har ingen vilkårsside, bare personvernerklæring (lest 08.11.2026); ingen kropp å arkivere | — | — | — | 08.11.2026 | **UBELAGT** |
| `styringsgruppen` | styringsgruppen (HI, NVA, trafikklyssystemet.no) | `vilkar-nva-styringsgruppen-2025/2026-11-08.bin.gz`: «https://nva.sikt.no/license/copyright-act/1.0»; 2017–2022 fra hi.no og trafikklyssystemet.no, der ingen vilkårsside er funnet | — | — | — | 08.11.2026 | **UBELAGT** |
| `styringsgruppen-ovrige` | styringsgruppen (HI, NVA, trafikklyssystemet.no) | `vilkar-nva-styringsgruppen-2025/2026-11-08.bin.gz`: «https://nva.sikt.no/license/copyright-act/1.0»; 2017–2022 fra hi.no og trafikklyssystemet.no, der ingen vilkårsside er funnet | — | — | — | 08.11.2026 | **UBELAGT** |
| `styringsgruppen-mandater` | Nærings- og fiskeridepartementet via Wayback | `vilkar-regjeringen/2026-11-08.bin.gz` gjelder bare «Bilder og videomateriale på regjeringen.no»; ingen side for tekst. regjeringen.no svarer 403, siden er lest via Wayback | — | — | — | 08.11.2026 | **UBELAGT** |
| `regjeringen-horing` | Nærings- og fiskeridepartementet | `vilkar-regjeringen/2026-11-08.bin.gz` gjelder bare «Bilder og videomateriale på regjeringen.no»; ingen side for tekst. regjeringen.no svarer 403, siden er lest via Wayback | — | — | — | 08.11.2026 | **UBELAGT** |
| `regjeringen-pressemeldinger` | Nærings- og fiskeridepartementet | `vilkar-regjeringen/2026-11-08.bin.gz` gjelder bare «Bilder og videomateriale på regjeringen.no»; ingen side for tekst. regjeringen.no svarer 403, siden er lest via Wayback; merknad M | — | — | — | 08.11.2026 | **UBELAGT** |
| `stortingsmeldinger` | Meld. St. 16 (2014–2015), regjeringen.no via Wayback | `vilkar-regjeringen/2026-11-08.bin.gz` gjelder bare «Bilder og videomateriale på regjeringen.no»; ingen side for tekst. regjeringen.no svarer 403, siden er lest via Wayback | — | — | — | 08.11.2026 | **UBELAGT** |
| `lovdata` | Lovdata | `vilkar-lovdata/2026-11-02.bin.gz` | «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | samme; «Massenedlasting og systematiske uttrekk er ikke tillatt.» | «hvis du oppgir Lovdata som kilde» | 08.11.2026 | belagt |
| `lovdata-andsverkloven` | Lovdata | `vilkar-lovdata/2026-11-02.bin.gz` | «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | samme; «Massenedlasting og systematiske uttrekk er ikke tillatt.» | «hvis du oppgir Lovdata som kilde» | 08.11.2026 | belagt |
| `lovdata-lakselusforskriften` | Lovdata | `vilkar-lovdata/2026-11-02.bin.gz` | «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | samme; «Massenedlasting og systematiske uttrekk er ikke tillatt.» | «hvis du oppgir Lovdata som kilde» | 08.11.2026 | belagt |
| `lovdata-produksjonsomradeforskriften` | Lovdata | `vilkar-lovdata/2026-11-02.bin.gz` | «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | samme; «Massenedlasting og systematiske uttrekk er ikke tillatt.» | «hvis du oppgir Lovdata som kilde» | 08.11.2026 | belagt |
| `lovdata-produksjonsomradeforskriften-endring-2023` | Lovdata | `vilkar-lovdata/2026-11-02.bin.gz` | «Du kan, uten begrensningene i punkt 2.1 og 2.2, fritt kopiere, bruke og dele følgende innhold fra tjenestene hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | samme; «Massenedlasting og systematiske uttrekk er ikke tillatt.» | «hvis du oppgir Lovdata som kilde» | 08.11.2026 | belagt |
| `utgivelse-regomr` | Havforskningsinstituttet via NMDC | `vilkar-nmdc/2026-11-03.bin.gz` | «Creative Commons Attribution 4.0 International License» | «Use Constraints CC BY 4.0» | navngivelse etter CC BY 4.0, merknad D; siden: «Use Constraints CC BY 4.0» | 08.11.2026 | belagt |
| `utgivelsesvakt` | Havforskningsinstituttet via NMDC | `vilkar-nmdc/2026-11-03.bin.gz` | «Creative Commons Attribution 4.0 International License» | «Use Constraints CC BY 4.0» | navngivelse etter CC BY 4.0, merknad D; siden: «Use Constraints CC BY 4.0» | 08.11.2026 | belagt |
| `maling-*` | målekropper | selges ikke; innholdet hentes under kildens egen rad | — | — | — | 08.11.2026 | ikke innhold |
| `vilkar` | loggene til vilkårsarkivet | selges ikke; innholdet hentes under kildens egen rad | — | — | — | 08.11.2026 | ikke innhold |
| `vilkar-*` | vilkårssidene selv | selges ikke; innholdet hentes under kildens egen rad | — | — | — | 08.11.2026 | ikke innhold |
| `*-openapi` | API-spesifikasjoner | selges ikke; innholdet hentes under kildens egen rad | — | — | — | 08.11.2026 | ikke innhold |

**Det tabellen ikke sier.** At NLOD 1.0, NLOD 2.0 og CC BY 4.0 tillater
salg av en sammenstilling, er lisensenes ordlyd lest av oss — juridisk
bekreftelse er EKSTERN (advokat), som i R4. Selve lisenstekstene på
data.norge.no er arkivert fra 08.11.2026 (`vilkar-nlod-1.0/`,
`vilkar-nlod-2.0/`). `belagt i lov` hviler på en lesning av
åndsverkloven § 14 (merknad K), ikke på et vilkår fra utgiveren.

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
| Herofotografiet, «skjærgård på Bømlo» | forsidens hero, tre bredder | Unsplash-lisensen | **ingenting** | `/bilde/hero-*.jpg` | `docs/design/HEROFOTO.md`, merknad L |
| Kystkontur, Kartverket N500/N2000 | kystlinja i alle kart | **CC BY 4.0** | **«© Kartverket»** med lenke, der kartet vises | dekkes av krediteringen under hvert kart og i bunnteksten | `docs/design/KARTGEOMETRI.md`, merknad J |
| Kystlinje, Natural Earth 1:10 m | nabolandene i kartene | public domain | **ingenting** | `/naturalearth-LICENSE.md` | `docs/design/KARTGEOMETRI.md` |
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

### Merknad L — herofotografiet, og at raden følger fila

*Het merknad K til 09.10.2026, da bokstaven ble tatt av `unntaksvekst`
også. To merknader med samme bokstav i et dokument som skal siteres,
er en feil; denne fikk neste ledige.*

Raden i tabell 2 har vært ute og inne igjen på fem dager, og det er
verdt å skrive ned hvorfor framfor å la tabellen se stabil ut:

    22.09.2026   inn    foto av skyer over hav, Wolfgang Hasselmann
    26.09.2026   UT     heroen ble et kart; fotografiet ut av `maler/`
    27.09.2026   inn    nytt foto, skjærgård på Bømlo, Endre Stedje

Raden ble FJERNET 26.09 og ikke merket «ute av bruk»: en rad om et lån
vi ikke lenger tar, er en usann opplysning på den ene siden som finnes
for å svare på om man kan stole på dette. Den som kom inn igjen 27.09 er
en NY rad om en annen fil av et annet motiv av en annen fotograf — ikke
den gamle gjenopprettet. **Lisensen er den samme (Unsplash), og det er
nettopp derfor det måtte kontrolleres:** to bilder under samme vilkår er
ikke samme lån, og en rad som bare oppga lisensen ville ikke skilt dem.

Vilkåret er lest på nytt 27.09.2026 på <https://unsplash.com/license> og
ikke gjenbrukt fra 22.09. Innholdet var uendret: fri bruk, også
kommersielt, ingen tillatelse og ingen navngiving nødvendig; ikke lov å
selge bildet uendret eller bygge en konkurrerende bildetjeneste.

**Unsplash+ er et annet lisensnivå** med andre vilkår, og et bilde
derfra kunne ikke ligget her. Kontrollert i Unsplashs eget API-svar for
bildet: `premium: false`, `plus: false`.

`docs/design/HEROFOTO.md` bærer proveniensen for alle tre heroene i
rekkefølge — begge fotografiene og kartet imellom — fordi en arkivert
kopi av forsiden fra en gitt uke ellers ikke kan etterprøves.

### Merknad G — de som ikke krever noe

Unsplash-lisensen og Natural Earths vilkår krever ingen navngiving.
Begge er likevel navngitt — på /om/, i proveniensfilene, og for
fotografiet også i bildeteksten i heroen — og det er ikke en
misforståelse av lisensen: en side som ikke sier hvor et bilde
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

**Versjonen er 1.0, og den er lest i kroppen** (04.11.2026, rødt lag F3).
Lisenssiden sier «Norsk lisens for offentlige data (NLOD)» uten tall, men
lenken «lisensen som våre data er underlagt» går til
`https://data.norge.no/nlod/no/1.0`, og lenken ved «vilkårene som er
utarbeidet av Difi» går til `https://data.norge.no/nlod/no` uten versjon.
Kroppen er `data/arkiv/vilkar-fiskeridir/2026-11-02.bin.gz`, sha256
`021c8692f14104b1986de78ad8f198948ab6ea52b699fec7034feb657ffdb0a3`.
Fram til da oppga JSON-LD `eierskap` med 2.0, som er en versjon
Fiskeridirektoratet ikke har oppgitt, og de fire andre med lisenssiden.
Nå er `license` 1.0 for alle fem, og for `eierskap` og
`eierskap_historikk` i tillegg Brregs 2.0 (`nettsted.LISENS_URL`).

## Merknad B — Brønnøysundregistrene, og HVILKET nivå lisensen gjelder

Luken fra 12.09.2026 er lukket 14.09.2026. Raden sto som ULEST fordi
ingen hadde lest Brregs egen lisensside; det er nå gjort.

### Lisensen, ordrett fra Brregs egen side

Fra `brreg.no/bruk-av-data-fra-bronnoysundregistrene/apne-data/`, lest
14.09.2026. **Den adressen gir 404 fra 06.10.2026** (lest 06.10.2026; svaret er ikke arkivert, så det kan ikke etterprøves — kontrolløren 08.11.2026). Setningen står
ordrett på `brreg.no/bruke-data-fra-bronnoysundregistrene/datasett-og-api/`,
som Brregs gamle `/produkter-og-tjenester/apne-data/` videresender til, og
er arkivert derfra:

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

## Merknad F — BarentsWatch: hva vilkårene krever, og hva Heine må gjøre

Lest på nytt 08.11.2026 i kroppen `vilkar-barentswatch/2026-11-08.bin.gz`
(sha256 `732454d98fe17a505543f8ee20c3d31907d521f5e75fdc0a16123d5af2d0564b`;
synlig tekst lik versjonen fra 02.11.2026). Sidas egen dato: «Sist
oppdatert: 02. november 2023». Sitatene under er ordrett fra kroppen.

### Krever kommersiell bruk egen registrering eller avtale? Nei.

Kommersiell bruk er tillatt på samme vilkår som annen bruk:

> «Du har lov til å bruke data hentet via BarentsWatch i kommersiell
> sammenheng, så lenge du følger alle retningslinjene»

Registreringen gjelder ALLE brukere, ikke bare kommersielle, og den er
allerede gjort — klientene for lusetall, sjøtemperatur og AIS finnes:

> «API er åpent og gratis, med det kreves at du selv gjør registrering (
> https://www.barentswatch.no/om/apnedata/ ) slik at vi kan holde deg
> oppdatert om utvikling og endringer.»

For profesjonell bruk er det en ANBEFALING, ikke et vilkår:

> «Vi ber deg om å fylle ut feltet "Formål (valgfritt)".»

> «Dersom du vil bruke API profesjonelt, og spesielt om du bruker
> dedikert mail for API anbefaler vi at du oppgir: E-post som ikke er
> knyttet til en person (f.eks post@... eller fiskehelse.avd@ )
> Kontaktperson med telefonnummer og epost Virksomhet som ønsker
> tilgangen Formål (Applikasjon eller planlagt bruk)»

**Rettelse.** Fram til 08.11.2026 sto det her at «kommersielle brukere bes
registrere API-klienten med formål, firma og kontaktperson». Det er ikke
vilkårets ord: siden skiller på PROFESJONELL bruk, ikke kommersiell, og
den ANBEFALER opplysningene. R4 regnet det som en uoppfylt plikt; etter
ordlyden er det en anbefaling som ikke er fulgt.

### De andre pliktene, ordrett

1. **Høy trafikk koster, og skal varsles:**

   > «Dersom du tar i bruk data fra BarentsWatch på høytrafikk nettsider
   > (eller på andre måter overbelaster våre servere), må du betale
   > håndteringskostnader til serverdrift eller lignende. Ta kontakt dersom
   > du planlegger å bruke datagrunnlaget vårt på sider som har svært stor
   > trafikk.»

   Nettstedet henter ingenting fra BarentsWatch ved visning; trafikken
   til kystloggen.no når ikke deres servere. Det som kan falle inn under
   «på andre måter», er AIS-strømmen, som har stått oppe døgnet rundt
   fra 28.10.2026 (`ais-bw`). Om én vedvarende tilkobling er
   «overbelastning», sier vilkåret ikke: det kan bare BarentsWatch svare
   på.
2. **Navnet:** «Du kan med andre ord ikke bruke BarentsWatch som en del
   av navnet på tjenesten.» Oppfylt: tjenesten heter Kystloggen.
3. **Innholdet:** «Du kan ikke endre på innholdet i data som leveres.»
   Rå-kroppen lagres uendret og hashet før noe parses; det som avledes
   (`kildeledd`), er merket som avledet.
4. **Attribusjonen** skal være synlig for brukeren: «Data levert av
   BarentsWatch», og for lusetallene dataeierens setning, «Opplysninger
   om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet».
   Oppfylt på nettstedet fra 16.09.2026 (bunnteksten og CSV-hodet). For
   AIS er dataeieren Kystverket: «Ekstern bruk av Kystverkets AIS-data må
   krediteres Kystverket.» (`vilkar-kystverket/2026-11-08.bin.gz`). AIS
   vises ikke på nettstedet i dag.

### Hva Heine må gjøre

Ingenting av dette er gjort av en økt; det krever innlogging på
BarentsWatch «Min side», og det er Heines konto. Om feltene allerede er
fylt ut, er ikke lest (EKSTERN).

1. **For hver API-klient** (lusetall/sjøtemperatur, og AIS): fyll ut
   «Formål», for eksempel «Kystloggen (kystloggen.no): ukentlig
   innsamling av lusetall og sjøtemperatur, og AIS-strøm, til et
   nettsted og datatjenester som kan bli kommersielle».
2. **Bytt e-posten på klientene** til en som ikke er knyttet til en
   person (`kontakt@kystloggen.no`), og oppgi kontaktperson med telefon
   og e-post, og virksomhet. Virksomheten er i dag Heine personlig; når
   selskapet finnes (R4 mangel 3), byttes den, og klientene bør da stå
   på selskapet (R4 mangel 6).
3. **Send én e-post til BarentsWatch om AIS-strømmen** (kontaktskjemaet
   på barentswatch.no): at klienten holder én tilkobling åpen døgnet
   rundt mot `live.ais.barentswatch.no`, hva den brukes til, og spør om
   det er innenfor vanlig bruk. Vilkåret ber om kontakt før svært stor
   trafikk, og bare de kan si om dette er det. Svaret arkiveres som
   belegg.

Ingen av de tre er et vilkår for kommersiell bruk etter ordlyden; punkt
1 og 2 er det vilkåret anbefaler for profesjonell bruk, og punkt 3 er den
eneste plikten som kan være utløst.

---

## Det som må skje før publisering

Rekkefølgen er den samme som alvorlighetsgraden:

1. **`ekspertgruppen` er UBELAGT.** Avklar med HI/NINA før en visning
   lener seg på rapportene.
1b. **Departementets kunngjøringer er UBELAGT** (merknad M, 04.11.2026).
   Visningen er stoppet til lisensen er belagt.
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
3. **BarentsWatch:** kommersiell bruk krever ingen egen registrering eller
   avtale (merknad F, lest på nytt 08.11.2026). Det vilkåret anbefaler for
   profesjonell bruk, og spørsmålet om AIS-strømmen, står der som tre
   punkter Heine gjør.

Lukket 14.09.2026: Brregs ordrette attribusjonssetning, som sto som
ULEST fra 12.09. Se merknad B.

---

## Merknad M — departementets kunngjøringer er UBELAGT

Lest 04.11.2026 (økt 4d, rødt lag F12). Kunngjøringene av
trafikklysrundene — pressemeldingene og nyhetene på regjeringen.no som
`beslutning.py` leser fargen, tegnforklaringen og de særskilte
vurderingene av — har ingen dokumentert lisens:

- **De ni arkiverte kroppene** i `data/arkiv/regjeringen-pressemeldinger/`
  (2017-10-30 til 2026-09-10) oppgir ikke noe vilkår for teksten.
  Bunnteksten lenker til «Bruks- og opphavsrett for bilder og
  videomateriale» (`/no/om-nettstedet/bruk-av-bilder-og-videomateriale/id2715005/`),
  som etter navnet gjelder bilder og video, og til personvernerklæringen.
  Ingen kropp nevner NLOD, Creative Commons eller gjenbruk av tekst.
- **regjeringen.no og Wayback** svarte CONNECT 403 fra øktas nettverk, så
  siden lenken peker til, er ikke lest.

Etter regelen øverst er det UBELAGT, og en UBELAGT kilde skal ikke bære en
publisert visning. Fra 04.11.2026 vises kunngjøringene derfor ikke
(`nettsted.KUNNGJORINGER_VISES = False`): ingen sitater, ingen
tegnforklaring fra dem, ingen «særskilt»-merknader, og de 19 av 65
rundecellene der bare kunngjøringen oppgir fargen, står som «ikke vist».
De leses og rangeres fortsatt, så visningen kommer tilbake med én linje
den dagen lisensen er belagt.

**Det som kan belegge den**, og som Heine må avgjøre: (1) vilkårssiden
for tekst på regjeringen.no, lest og arkivert; eller (2) samme lesning av
åndsverkloven § 14 som for `unntaksvekst` (merknad K) — kunngjøringene er
uttalelser om offentlig myndighetsutøvelse, utgitt av departementet.
Ingen av dem er gjort her.

## Merknad K — `unntaksvekst`: belagt i lov, åndsverkloven § 14

**Belagt i lov 09.10.2026.** Grunnlaget for å gjengi Mattilsynets
oversikt over søknader om unntaksvekst er at den ikke har opphavsrettslig
vern, ikke at Mattilsynet gir lov. Vilkårssiden «Vil du bruke tekstar frå
Mattilsynet?» var grunnlaget fra morgenen 09.10.2026, og den lesningen —
at «tekstar» dekker en tabell — er forlatt. Siden beholdes som PRAKSIS,
se under.

### § 14 — vedtak av offentlig myndighet er uten vern

Åndsverkloven (LOV-2018-06-15-40, sist endret LOV-2024-12-13-76) § 14
første og andre ledd, ordrett. Lest av kroppen
`lovdata-andsverkloven/2026-10-09.bin.gz` i datarepoet, hentet
2026-10-09T15:46:18Z fra lovdata.no/dokument/NL/lov/2018-06-15-40,
sha256 `b60131c4a8bbe6fe3f4d22a39ea386aea97738ef52b0be8bb14add8885237521`
(synlig tekst: `49ba24de8dc65ce57df0298acd6b88f67379d76a400ec49d87b528d00cb9e1fe`):

> Lover, forskrifter, rettsavgjørelser og andre vedtak av offentlig
> myndighet er uten vern etter denne loven. Det samme gjelder forslag,
> utredninger, uttalelser og lignende som gjelder offentlig
> myndighetsutøvelse, og er avgitt av offentlig myndighet, offentlig
> oppnevnt råd eller utvalg, eller utgitt av det offentlige. Tilsvarende
> er offisielle oversettelser av slike tekster uten vern etter denne
> loven.
>
> Åndsverk som ikke er skapt særskilt til bruk i dokumenter som nevnt i
> første ledd, og som det siteres fra eller som gjengis i særskilt
> vedlegg, omfattes ikke av denne bestemmelsen. Første ledd gjelder
> heller ikke lyrikk, musikkverk eller kunstverk.

Søknadslista er Mattilsynets oversikt over søknader og resultatet av
dem: en oversikt over vedtak, utgitt av myndigheten selv. Andre ledds
unntak treffer den ikke — den er verken skapt utenfor myndigheten og
gjengitt i et vedlegg, eller lyrikk, musikk eller kunst.

### Tabellen er fakta uten verkshøyde

Uavhengig av § 14: lista er saksnummer, lokalitet, produksjonsområde og
resultat, satt opp i en tabell. Det er fakta, ordnet slik slike fakta
ordnes, og ikke et åndsverk. Uten verkshøyde er det ingen opphavsrett å
ta stilling til.

### § 24 — databasevern krever en vesentlig investering

Samme kropp, § 24 første ledd, ordrett:

> Den som fremstiller en database, som for eksempel et formular, en
> katalog, en tabell, et program eller lignende arbeid, hvor innsamling,
> kontroll eller presentasjon av innholdet innebærer en vesentlig
> investering, har enerett til å råde over hele eller vesentlige deler
> av databasens innhold ved uttrekk fra eller gjenbruk av databasen.

En oversikt over myndighetens egne vedtak krever ingen vesentlig
investering i INNSAMLING: vedtakene er fattet av den som fører lista, og
oversikten er et biprodukt av saksbehandlingen. Og § 24 femte ledd sier
uansett at «§§ 3 tredje ledd, 4, 8 til 10, 14, 26 til 29 […] gjelder
tilsvarende» — unntaket for vedtak gjelder også databaseretten.

### Det som er en lesning, og det som ikke er det

Lovteksten over er MÅLT: ordrett av en arkivert kropp med hash. At lista
er en oversikt over vedtak i § 14s forstand, at den mangler verkshøyde,
og at den ikke er en vesentlig investering, er LESNINGER av loven, gjort
09.10.2026 etter Heines anvisning. Ingen domstol eller myndighet har sagt
det om denne lista (CLAUDE.md regel 4).

### Vilkårssiden beholdes som praksis

Mattilsynets side (arkivert i `vilkar-mattilsynet/`, lest 09.10.2026)
ber om tre ting, og vi gjør dem selv om loven ikke krever det:

1. **Kilde.** `attribusjon = ("Kilde: Mattilsynet",)`, i bunnteksten på
   hver side som bruker kilden.
2. **Adresse og dato.** Ved tabellen på /analyse/unntaksvekst/.
3. **Ingen misvisende sammenheng.** Siden sier hva lista sier, og
   vurderer ikke søknadene. En lokalitetsside nevner lista bare der
   koblingen er sikker.

### Følgene

Søknadene står i ukesendringene fra den andre ukentlige kjøringen (den
første har ingen forrige å sammenligne med), og kilden står i
lisenstabellen på /om/ med hjemmelen «åndsverkloven § 14». Skulle
grunnlaget falle, settes `attribusjon` tilbake til `None`; da bygges
ikke analysesiden, og byggingen feiler til den er tatt ut.
