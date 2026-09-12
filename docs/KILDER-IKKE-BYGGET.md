# Kilder som er undersøkt og ikke bygget

Stående vurderinger. Hver post sier hva kilden ville gitt, hva som
holder den tilbake, og — der det er avgjort — at sporet er lukket.

**Regelen:** bygges en av dem, flyttes vurderingen til en egen
`docs/KILDE-*.md` og posten fjernes herfra. Ellers står det to
beskrivelser av samme kilde som kan skille lag, og den utdaterte er den
som blir lest. Samme hygiene som `docs/APNE-SPORSMAL.md`.

Skillet mellom **bekreftet** (endepunkt testet med egne øyne) og
**antatt** (lest om, ikke prøvd) gjelder her som ellers, jf. regel 4 i
`CLAUDE.md`. Ingen av postene under er bekreftet med mindre det står
uttrykkelig.

Flyttet hit fra prosjektmappa 12.09.2026, fra seksjonen «Ikke bygget» i
`03_datalandskapet.md`. Rømming er ikke med lenger — den er bygget, se
`docs/beslutninger/2026-09-03-romming.md`.

---

## Vannmiljø (Miljødirektoratet) — ANTATT TILGJENGELIG

Bunnundersøkelser under og rundt anlegg: **MOM-B og MOM-C etter
NS 9410**. MOM-B er den hyppige tilstandsundersøkelsen rett under
anlegget, MOM-C den grundigere resipientundersøkelsen utover.

**Ville gitt:** miljøtilstand per lokalitet over tid — den ene
dimensjonen ved oppdrett som verken lusetall, biomasse eller eierskap
sier noe om.

**Forbeholdet, og det er avgjørende for hva kilden kan brukes til:**
historikken finnes bare som PDF. Det er de nyere dataene som ligger i
selve basen. En serie herfra vil derfor ha en knekk der formatet
skifter, og knekken er vår, ikke naturens.

**Proveniens:** tipset kom fra Pål Næverlid Sævik ved
Havforskningsinstituttet 09.09.2026. Han opplyste samtidig at han **ikke
har prøvd API-et selv**. Det er derfor ANTATT i streng forstand — ingen
har sett et svar fra endepunktet, hverken vi eller den som tipset.

---

## Stortingets skriftlige spørsmål og svar — ANTATT TILGJENGELIG

Åpne data fra Stortinget: representantenes skriftlige spørsmål og
departementets svar.

**Ville gitt:** et forvarsel om regelverksendringer. Et svar fra
Nærings- og fiskeridepartementet om trafikklyssystemet, kapasitets-
justering eller luseregulering sier ofte hva som er under arbeid før
det kommer på høring.

**Hvorfor den haster mer enn de andre her:** dette er en tilstand som
forsvinner. Registerdata beskriver hva som gjelder nå, og kan i noen
grad hentes igjen. En politisk signalgivning som ikke ble fanget da den
sto der, finnes ikke som serie i ettertid — samme form som regel 5 i
`CLAUDE.md`.

---

## Regnskapsregisteret — ANTATT TILGJENGELIG

Brønnøysund, åpne data, ingen nøkkel.

**Ville gitt:** omsetning, resultat og egenkapital per orgnr. Kobles
mot Enhetsregisteret. Med eierskapskjeden gir det «hvem vokser lønnsomt
og hvem vokser på gjeld». Årlig oppdatering, lav innsamlingsfrekvens.

---

## Havbruksfondet og auksjonspriser — ANTATT, LAV FREKVENS

Utbetalinger per kommune; pris per tonn MTB per produksjonsområde.

Hendelser som skjer annethvert år. Kan legges til når som helst uten
tap — den eneste kilden på denne lista der utsettelse ikke koster
historikk.

---

## Laksepris / NASDAQ Salmon Index — FRARÅDES

Lisensstatus uklar. En betalt kilde bryter modellen om at alt er
reproduserbart fra åpne data.

---

## NAV stillingsannonser — FRARÅDES FORELØPIG

Åpent API, men støyete. Signalet er svakt sammenlignet med kildene
over. Se `docs/beslutninger/2026-08-18-nav-stillingsannonser-forkastet.md`.

---

## Kommunale byggesaksinnsyn — FRARÅDES

Ikke én integrasjon, men én per kommune, med ulikt oppsett og ingen
dokumentasjon. Høy vedlikeholdskostnad, skjør.

---

## Fisketall per lokalitet — STENGT

Ikke «ikke bygget ennå». **Lukket.**

Biomassedatabasen etter **akvakulturdriftsforskriften § 44** — antall
fisk og biomasse per anlegg per måned — er børssensitiv og ikke
offentlig. **Bekreftet av Havforskningsinstituttet 09.09.2026.** Det er
ikke en tilgang som kan forhandles fram med et bedre argument, og
sporet skal ikke undersøkes på nytt uten at rettstilstanden er endret.

Kartleggingen av hva som faktisk finnes åpent står i
`docs/VURDERING-FISKETALL-PER-LOKALITET.md`. Kortversjonen: ingen åpen
fil bærer beholdning per lokalitet. Den eneste åpne serien med `LOKNR`
er utsett av rensefisk.

**Konsekvensen rekker lenger enn til oss.** Kvoteenheten i et framtidig
reguleringssystem — utslipp per lokalitet, målt mot en tildelt kvote —
kan ikke beregnes av noen utenfor forvaltningen så lenge § 44-dataene
er stengt. Det gjelder alle eksterne, ikke bare dette repoet. Enhver
uavhengig etterprøving av et slikt system er avhengig av at
forvaltningen selv publiserer tallet.

Det som ER hentet, er ja/nei: står det fisk på lokaliteten, og hvilken
art. Se `sources/biomasselag.py` og
`docs/beslutninger/2026-09-10-biomasselag.md`. Mengden er stengt;
tilstedeværelsen er det ikke.
