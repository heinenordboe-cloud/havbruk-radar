---
dato: 2026-08-18
tittel: Kategorien «forsvinnende kilder» er tom, og hastverket den skapte gjelder ikke lenger
status: gjeldende
commit: 
---

# Kategorien «forsvinnende kilder» er tom

**Bestemt:** Kildeklassifiseringen i
[backfill-beslutningen fra 17.08](2026-08-17-backfill-rekkefolge.md) er feil
på to av tre punkter. Prioritering settes fra nå på analytisk verdi og
lisensrenhet, ikke på hvor fort en kilde forvitrer.

**Hva som var feil:** Beslutningen deler kilder i rene arkiver og kilder
som overskriver seg selv, og lister tre i den andre gruppa:
Akvakulturregisterets kapasitet og trafikklys, lusetall, og
stillingsannonser.

- **Lusetall** er et arkiv. BarentsWatch' fiskehelse-API tar år og uke
  som stiparametre — `/v1/geodata/fishhealth/locality/{year}/{week}` — og
  dataene går tilbake til 2012.
- **Stillingsannonser** er et arkiv. NAVs feed inneholder alle annonser
  siden ca. 2019, og inaktive er merket som inaktive, ikke slettet.
  Seks-måneders-regelen gjelder hvor lenge en annonse kan være *aktiv*,
  ikke hvor lenge den er hentbar.
- **Akvakultur** var den ekte, og den er i drift siden 17.08.

**Hvorfor det betyr noe:** Hastverket har vært den styrende kraften i hver
prioritering siden 16.08. CLAUDE.md regel 5 sier at innsamling aldri skal
utsettes til fordel for mer bygging, og det er riktig som prinsipp — men
det binder ingenting akkurat nå, fordi ingen kjent kilde forvitrer.
Fortsatt å prioritere etter forvitring ville bygget bredde uten grunn.

**Og datafortrinnet er tynnere enn prosjektet har antatt.**
Akvakulturregisteret versjonerer seg selv: hver lokalitet bærer
`validFrom`, `validUntil` (`9999-12-30` for gjeldende), `registeredTime`
og `versionCauseType`. Fiskeridirektoratet lagrer altså historikken
internt. Jeg fant ikke et offentlig endepunkt som gir de lukkede
intervallene, men fant det heller ikke bevist fraværende.

Det betyr at premisset ikke er «dataene finnes ikke», men «en etat har
valgt å ikke publisere noe de allerede lagrer». Det er ikke fysikk, det
kan endres, og en konkurrent kan i mellomtiden be om innsyn etter
offentleglova.

**Konsekvensen for strategien:** Vollgrava ligger ikke i snapshotene.
Den ligger i prediksjonsloggen, som er det eneste laget der «kan ikke
rekonstrueres» er bokstavelig sant, og i domenekodede regler som en
generalist ikke skriver.

**Prisen:** Uten forvitring som sorteringsnøkkel er rekkefølgen på nye
kilder et åpent vurderingsspørsmål igjen, og det er tyngre enn en regel.

**Ville snudd det:** At en kilde vi vil ha viser seg å ha kort
oppbevaringstid — da flyttes den opp, og kategorien er ikke tom lenger.
Eller at Fiskeridirektoratet publiserer versjonshistorikken, som ville
gjort den siste resten av datafortrinnet rekonstruerbart og gjort saken
enda tydeligere.
