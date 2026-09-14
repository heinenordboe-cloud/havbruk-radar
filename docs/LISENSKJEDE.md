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
| `eierskap` | NLOD | samme + Brreg, se under | «Kilde: Fiskeridirektoratet» og «Brønnøysundregistrene» | **ja** | 25.08. / **ULEST** |
| `enhetsregisteret` | NLOD | **ULEST** — se merknad B | «Brønnøysundregistrene» | **ja** (følger av NLOD) | **ULEST** |
| `lusetall` | NLOD | [barentswatch.no/artikler/api-vilkar](https://www.barentswatch.no/artikler/api-vilkar) | «Data levert av BarentsWatch» **+** «Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra Mattilsynet.» | **ja, uttrykkelig** | 12.09.2026 |
| `sjotemperatur` | NLOD | samme | «Data levert av BarentsWatch» | **ja, uttrykkelig** | 12.09.2026 |
| `trafikklysvedtak` | NLOD 2.0, via unntaket i Lovdatas punkt 2.3 | [lovdata.no/info/brukeravtale](https://lovdata.no/info/brukeravtale) | «hvis du oppgir Lovdata som kilde og ellers følger vilkårene i NLOD 2.0» | **ja**, men se merknad C | 12.09.2026 |
| `reguleringsomraader` | **CC BY 4.0** | [doi.org/10.21335/NMDC-1923112433](https://doi.org/10.21335/NMDC-1923112433) | navngivelse av opphavspersonene, se merknad D | **ja** | 14.09.2026 |
| `ekspertgruppen` | **UBELAGT** | ingen funnet — se merknad E | siteringsformen fra rapporten selv | **ukjent** | 14.09.2026 (søkt, ikke funnet) |

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

## Merknad B — Brønnøysundregistrene er en KJENT LUKE

`docs/KILDE-EIERSKAP.md` linje 6–7 sier «NLOD for begge; attribusjonen
er et vilkår». Det er repoets egen påstand, og den er trolig riktig —
men **ingen har lest Brregs egen lisensside og skrevet ned ordlyden**,
slik det er gjort for Fiskeridirektoratet.

Derfor står hjemmel og lesedato som ULEST, ikke som en URL vi ikke har
åpnet. Lisensen er ikke i tvil; det som mangler er den ordrette
attribusjonssetningen, og den trengs før Enhetsregisteret bærer en
publisert visning. Dette er den ene raden i tabellen som er et
arbeidsstykke og ikke et funn.

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

Kilden henter fire kropper, én gang hver, og arkiverer dem. Det er ikke
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
   lener seg på rapportene.
2. **Brregs ordrette attribusjonssetning er ikke lest.** Merknad B.
3. **De to BarentsWatch-setningene må stå synlig for sluttbruker.** Se
   TODO-en i `docs/VISNING.md`.
4. **Registrering hos BarentsWatch** hvis bruken blir kommersiell.
