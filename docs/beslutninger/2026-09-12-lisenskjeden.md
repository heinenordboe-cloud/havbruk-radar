---
dato: 2026-09-12
tittel: Lisens per kilde er et krav før publisering, og udokumentert lisens er UBELAGT
status: utkast
commit: [fylles inn]
---

## Hva som ble bestemt

**Hver kilde i `sources/` skal ha en rad i `docs/LISENSKJEDE.md`** med
seks felter: lisens, hjemmel som URL, attribusjonskravet i ordrett form,
om kommersiell bruk er tillatt, og **datoen vilkåret ble lest**.

**Er lisensen ikke funnet, står den som UBELAGT — ikke som antatt
greit.** UBELAGT er en påstand om at noen har lett og ikke funnet, og
merknaden skal si hva som ble prøvd. Den er ikke det samme som «ingen
lisens», og heller ikke det samme som «fritt».

**En UBELAGT kilde kan brukes i analyse og dokumentasjon, men skal ikke
bære en publisert visning** før luken er lukket. Grensen går ved
publisering, ikke ved innsamling — vi henter offentlig materiale med
vanlig sitatrett uansett.

**Attribusjonen følger tallene ut, ikke dokumentasjonen.** Der et vilkår
krever synlighet for sluttbruker, er det visningen som må bære den. Se
TODO-en i `docs/VISNING.md`.

Per 14.09.2026: elleve kilder, ti belagt, én UBELAGT
(`ekspertgruppen`), og én kjent luke i ordlyden (Brønnøysundregistrene).

## Hvorfor nå

BarentsWatch' API-vilkår ble lest 12.09.2026, og de sa to ting som ikke
sto noe sted i repoet. Det ene var gledelig — kommersiell bruk er
uttrykkelig tillatt. Det andre var en plikt vi ikke hadde: **at
attribusjonen skal være synlig for SLUTTBRUKER**, med en egen
dataeiersetning om Mattilsynet i tillegg til BarentsWatch selv.

Det er en plikt av en type repoet ikke hadde noe sted å legge. `README.md`
hadde en attribusjonsseksjon, men den er en kildeliste, ikke et
vilkårsregister: den sa «se barentswatch.no for kildens egne vilkår» —
altså en henvisning til noe ingen hadde lest, ført opp som om saken var
i orden.

Og da vilkårene faktisk ble lest, viste det seg at seks av elleve kilder
ikke hadde noen lisensomtale i det hele tatt. To av dem —
`trafikklysvedtak` og `ekspertgruppen` — er ikke NLOD-kilder, og den ene
av dem har vilkår som biter.

## Hvorfor UBELAGT og ikke en antakelse

Dette er samme regel som CLAUDE.md punkt 4, anvendt på en tredjeparts
vilkår i stedet for på et endepunktsformat: **har du ikke lest det, si
det.**

Fristelsen er reell og den er spesifikk. Ekspertgrupperapportene er
offentlige utredninger levert et departement, hentbare uten nøkkel,
registrering eller avtale. Alt ved dem sier «dette er fritt». Men
«offentlig tilgjengelig» og «fritt å republisere» er to forskjellige
påstander, og den ene følger ikke av den andre. Å skrive NLOD i den raden
fordi de andre radene sier NLOD, ville vært å utlede en tredjeparts
rettighetsposisjon av vårt eget inntrykk.

Det er samme feilform som 1b-2 beskriver: et felt som «pleier å følge»
det riktige, brukt fordi de faller sammen i de vanlige tilfellene. Norske
etater publiserer stort sett under NLOD. Helt til en av dem ikke gjør
det — og Lovdata er beviset på at formen finnes. Lovdatas hovedregel i
punkt 2.1 er «egne, private, ikke-kommersielle formål». Hadde vi gjettet
NLOD der, hadde gjettet vært **feil for hovedregelen og riktig bare
fordi et unntak i punkt 2.3 tilfeldigvis dekker akkurat det vi henter.**

Den asymmetrien er hele begrunnelsen: en gjettet lisens som er riktig,
koster ingenting og gir ingen beskjed. En gjettet lisens som er gal,
oppdages av motparten.

## Hvorfor datoen står i tabellen

Et lisensvilkår er en påstand fra en tredjepart som kan endres uten at
noe i dataene beveger seg. Det er den samme egenskapen `published_at`
finnes for: **tidspunktet tilhører KILDEN, ikke oss** (1b-7).

En frekvensvakt oppdager at en kilde slutter å svare. Ingen vakt
oppdager at BarentsWatch endrer vilkårene sine — kallet svarer likt,
radene er de samme, og hele endringen er usynlig i alt vi måler. Datoen
er det eneste som gjør et gammelt vilkår synlig som gammelt.

BarentsWatch' vilkår er sist oppdatert 02.11.2023 og lest 12.09.2026.
Lovdatas brukeravtale er sist oppdatert 31.10.2025 og lest 12.09.2026.
Begge datoene står i tabellen fordi de er to forskjellige opplysninger,
og bare den andre er vår.

## Hva som ikke ble bestemt

**Ingen automatisk kontroll.** Det fristet å la `snapshot.write()` nekte
en kilde uten lisensrad, etter mønster av persondatakontrollen i regel 3.
Det ble ikke gjort, og grunnen er at kontrollen ville vært av samme
svake type som 1b-2 advarer mot: den kan bare måle at **en rad finnes**,
ikke at den er sann eller at den er lest nylig. En kilde med en gal
lisensrad ville passert, og vakten ville gitt dekning for nettopp det
den ikke kan se.

Lisensen er et menneskeansvar her, ikke et maskinansvar. Det som er
gjort i stedet, er å gjøre fraværet lesbart: UBELAGT står i tabellen,
ikke i en fotnote.

**Ingen endring i `sources/`.** Dette er dokumentasjon. Ingen kilde
henter annerledes, og ingen rad i noe snapshot endrer seg.

## Hva som ville snudd det

**At en kilde endrer vilkår.** Da er ikke tabellen gal — den er
utdatert, og lesedatoen er det som viser det. Raden skrives om med ny
dato, og den gamle blir stående i git.

**At et vilkår viser seg å utelukke kommersiell bruk.** I dag sier alle
ti belagte radene ja, og `ekspertgruppen` sier ukjent. Snur én av dem,
er det ikke lisenskjeden som må endres, men hva prosjektet kan bli — og
da flyttes spørsmålet til `docs/APNE-SPORSMAL.md`, som er der valget om
hva dette skal bli allerede hører hjemme.

Merk hvilken vei den risikoen peker: Lovdatas hovedregel er allerede
ikke-kommersiell, og vi står i et unntak. Endres unntaket, faller
`trafikklysvedtak` ut av kommersiell bruk uten at noe i dataene beveger
seg.

**At regelen i praksis blir en rad ingen fyller ut.** Blir UBELAGT et
felt som står i årevis fordi ingen sender e-posten, er ikke problemet
regelen — det er at den er skrevet som dokumentasjon og ikke som en
oppgave. Da hører den i `docs/APNE-SPORSMAL.md` med den hygieneregelen
som gjelder der.
