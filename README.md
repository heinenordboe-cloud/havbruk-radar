# havbruk-radar

Norsk havbruk er en næring der kapasitet, eierskap og lokaliteter er i
konstant bevegelse. Offentlige registre viser hvordan det ser ut akkurat
nå, men ikke hva som har endret seg underveis. Det er den forskjellen
dette prosjektet samler.

Kildene hentes ukentlig og hvert eneste snapshot tas vare på, slik at
endringer kan leses ut i etterkant. Innsamlingen har gått uavbrutt siden
august 2026. Registerdataene er åpne og kan hentes av hvem som helst i
dag — men historikken fra en gitt uke kan ikke hentes i ettertid, og det
er den som er poenget.

Jeg har hatt en sterk tilknytning til havet og til oppdrett hele
oppveksten, og min første jobb var på et lakseslakteri. Der fikk jeg se
hele veien fra merd til ferdig pakket og lastet i lastebil. Det er
grunnen til at spørsmålene jeg stiller dataene blir andre enn de ville
blitt ellers.

## Hvordan det er bygget

- Rådata arkiveres uendret og hashes før noe parses. Ingenting skrives om
  i ettertid.
- Kilder som reviderer fortiden bæres på to akser: når noe gjaldt, og når
  det ble sagt. Begge påstander beholdes.
- Hver beslutning av betydning er skrevet ned med begrunnelse og med hva
  som ville snudd den, i `docs/beslutninger/`.

`CLAUDE.md` har de harde reglene. `docs/ARKITEKTUR.md` beskriver
oppbygningen, og `docs/KILDE-*.md` dokumenterer hver enkelt kilde med hva
som er verifisert og hva som er antatt.

## Kilder og attribusjon

**Fiskeridirektoratet** — Akvakulturregisteret, tillatelser og eierskap,
biomassestatistikk og rømmingsstatistikk. Tilgjengeliggjort under
[Norsk lisens for offentlige data (NLOD)](https://data.norge.no/nlod/no/).

**Brønnøysundregistrene** — Enhetsregisteret, under
[NLOD 2.0](https://data.norge.no/nlod/no/2.0) (lest 14.09.2026). Bare de
frie, åpne datasettene hentes — ikke det autoriserte API-et med roller
og fødselsnummer. Brreg oppgir ingen egen attribusjonsform, så NLOD 2.0
punkt 5 gjelder:

> Inneholder data under Norsk lisens for offentlige data (NLOD)
> tilgjengeliggjort av Brønnøysundregistrene

**Lovdata** — kapasitetsjusteringsforskriftene.

**BarentsWatch** — ukentlige lusetellinger og sjøtemperatur per
lokalitet, som BarentsWatch henter fra Mattilsynet. Under
[NLOD, etter BarentsWatch' API-vilkår](https://www.barentswatch.no/artikler/api-vilkar)
(sist oppdatert 02.11.2023, lest 12.09.2026). Kommersiell bruk er
uttrykkelig tillatt.

Attribusjonen skal være synlig for **sluttbruker**, ikke bare her. Begge
setningene er ordrette krav:

> Data levert av BarentsWatch

> Opplysninger om lakselus, rensefisk og medikamentbruk er hentet fra
> Mattilsynet.

**Havforskningsinstituttet** — ekspertgruppens vurderinger av
lakselusindusert villfiskdødelighet, og de foreslåtte
reguleringsområdene:

> Sævik, P.N., Holstad, A., Bolstad, G.H., Næsje, T., Diserud, O.,
> Johnsen, I.A., Jensen, M.F., Sandvik, A.D. og Myksvoll, M.S. (2026).
> *Forslag til reguleringsområder for utslipp av lakselus.* Rapport fra
> havforskningen 2026-28. Geodata:
> [doi.org/10.21335/NMDC-1923112433](https://doi.org/10.21335/NMDC-1923112433)

Reguleringsområdene er et **forslag** til Nærings- og
fiskeridepartementet, ikke gjeldende regelverk, og bæres som det i
dataene. Geodatasettet er under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.no),
bekreftet av Pål Næverlid Sævik ved Havforskningsinstituttet
09.09.2026.

Ingen av etatene eller institusjonene har medvirket til, eller innestår
for, bearbeidingen eller tolkningene som er gjort her. Samme attribusjon
følger med overalt hvor data herfra publiseres.

Lisens, hjemmel, ordrett attribusjonskrav og lesedato per kilde står i
[`docs/LISENSKJEDE.md`](docs/LISENSKJEDE.md). Der en lisens ikke er
funnet, står den som UBELAGT — ikke som antatt greit.

## Personvern

Det hentes kun opplysninger om virksomheter og lokaliteter. **Roller,
gateadresser og andre personopplysninger hentes bevisst ikke inn**, slik
at verken dette repoet eller datarepoet er et personregister.

Snapshotene ligger i et eget, privat repo. Koden er MIT-lisensiert.

---

## In English

Norwegian aquaculture is an industry where capacity, ownership and sites
are in constant motion. Public registries show what things look like
right now, but not what has changed along the way. That difference is
what this project collects.

Sources are fetched weekly and every snapshot is kept, so that change
over time can be read out. Collection has run without interruption since
August 2026.

I've had a strong connection to the sea and to fish farming my whole
life, and my first job was at a salmon processing plant. There I saw the
whole chain, from pen to packed and loaded onto the truck. That's why the
questions I ask of the data are different ones.

Raw responses are archived unchanged and hashed before anything is
parsed. Sources that revise the past are carried on two axes — when
something was true, and when it was stated — and both claims are kept.
Every decision of consequence is written down with its reasoning and with
what would reverse it, in `docs/beslutninger/`.

Data comes from the Norwegian Directorate of Fisheries and the
Brønnøysund Register Centre (both under
[NLOD](https://data.norge.no/nlod/en/)), from Lovdata, from BarentsWatch,
and from the Institute of Marine Research — see the Norwegian section
above for full citations. None of the agencies or institutes have
contributed to, or vouch for, the processing or interpretations made
here. Only company- and site-level data is collected; roles, street
addresses and personal data are deliberately excluded. Code is MIT
licensed.
