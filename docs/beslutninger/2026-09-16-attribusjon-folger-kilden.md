---
dato: 2026-09-16
tittel: Attribusjonen flyttes til Source.attribusjon — vilkåret følger kilden
status: besluttet
commit: [fylles inn]
---

# Attribusjonen flyttes til `Source.attribusjon`

**Bestemt:** Attribusjonssetningene lisensgiveren krever, ordrett, ligger
på kilden — `Source.attribusjon` i `core/contract.py` — og ikke i en
tabell hos den som publiserer.

Dette er en **utvidelse av kildekontrakten**, og den er derfor eierens
avgjørelse og ikke en sidevirkning av en oppgave. CLAUDE.md regel 1 sier
det rett ut: later en ny kilde til å kreve en endring i `core/`, skal
man si fra at kontrakten mangler noe og la brukeren avgjøre. Det ble
gjort 16.09.2026, og dette er avgjørelsen.

---

## 1. Hvorfor tabellen ikke kunne bli stående i `nettsted.py`

`KILDEVILKAAR` var en dict fra kildenavn til setninger, plassert i
generatoren. Den virket, og alle elleve kildene sto der.

Feilen er ikke at den var ufullstendig. Feilen er **når** den ville blitt
det.

En ny kilde er én ny fil i `sources/`. Ingen registrering, ingen import
andre steder — det er hele poenget med `registry.discover()`. Kilden blir
med i neste kjøring, skriver snapshots, og alt virker. Den eneste tingen
som ikke følger med, er raden i en tabell i en helt annen fil.

Og den manglende raden gir ingen feil før noen bygger en side som bruker
kilden. Det kan være uker senere, av en annen grunn, og da er symptomet
«siden vil ikke bygge» og ikke «du glemte lisensen».

Det er den samme formen som resten av kontrakten allerede er skrevet for
å unngå. `utvalg`, `published_at`, `domene` og `startdatofelt` ligger alle
på kilden, og begrunnelsen er identisk i alle fire: **verdien settes der
den er kjent, ikke der den brukes.** Et andre sted å slå den opp er et
sted de to kan svare ulikt, og det er F6, F7 og F8 i tre utgaver.

Attribusjonen er ikke et unntak fra det mønsteret. Den er femte utgave.

## 2. Hva som er lagt til i kontrakten

To felter, og det andre er ikke pynt — se punkt 4.

```python
attribusjon: tuple[str, ...] | None = None
skriver_ogsaa: tuple[str, ...] = ()
```

### `attribusjon` har TO tilstander, og den tomme tuppelen er forbudt

    None                 UBELAGT — kilden sier ingenting
    ("setning", ...)     dette kreves, ordrett
    ()                   ugyldig, kaster

`utvalg` har tre tilstander fordi «vi ba om alt» er en meningsfull
påstand noen kan gå god for. Den tredje er ikke sluppet inn her, og det
er et valg av hvilken vei feilen skal peke.

`()` og `None` er begge usanne i Python. Det er nøyaktig fella
`core/utvalg.py` har en egen seksjon om — «de to falske vennene» — og der
ble den løst med `er_ukjent()` og `henter_alt()`. Her er den løst
strengere, fordi konsekvensen er en annen: et utvalg som leses feil gir
en misvisende changelog, mens en attribusjon som leses feil gir en
publisering uten hjemmel.

En kilde som faktisk ikke krever navngivelse — CC0, offentlig eiendom —
finnes ikke i repoet i dag. Den dagen den kommer, er den tredje
tilstanden en kontraktsendring med et eget notat. `()` er **reservert**
for det, ikke ledig.

### Valideringen står i `core/`, politikken hos den som publiserer

`erklaert_attribusjon(kilde)` validerer formen og returnerer `None` for
UBELAGT. Den stopper tre feilformer:

| feilform | hva den ville gitt |
|---|---|
| `()` | publisering uten attribusjon, i stillhet |
| `"Kilde: X"` (naken streng) | ett punktmerke per bokstav i bunnteksten |
| `("", "Kilde: X")` | et tomt punktmerke |

Den andre er den nærliggende skrivefeilen — `("Kilde: X")` uten komma er
en streng, ikke en tuppel — og den ville iterert som enkelttegn.

**Men `core/` avgjør ikke hva UBELAGT betyr.** Det gjør `nettsted.py`.
Grunnen er at grensen går ulikt: `docs/LISENSKJEDE.md` sier at en UBELAGT
kilde kan brukes i **analyse og dokumentasjon**, men ikke bære en
**publisert visning**. Å legge nektelsen i kjernen ville gjort
ekspertgruppen ubrukelig for analysen den faktisk er hentet for.

Kjernen sier hva som er erklært. Publiseringsleddet sier hva det får lov
til å bety.

## 3. Hva som IKKE ble flyttet, og hvorfor det står her

`UTGIVER` og `LISENS_URL` ble stående i `nettsted.py`. De brukes bare til
JSON-LD: organisasjonsnavnet i `provider`, og lisens-URL-en i `license`
for de kildene der lisensVERSJONEN er belagt.

Argumentet for å flytte dem er nøyaktig det samme som over, og det er
verdt å si at jeg ser det. Grunnen til at de ikke fulgte med er at
oppgaven gjaldt attribusjonen — den juridiske plikten — og at en
kontraktsutvidelse ikke skal vokse ut over det som er avklart. To felter
er allerede ett mer enn bestillingen.

**Dette er et åpent punkt, ikke en konklusjon.** Skal de flyttes, er det
samme øvelse en gang til, og da hører `provider` og `license` naturlig
sammen med `attribusjon` som ett vilkårsobjekt framfor tre felter.

## 4. `skriver_ogsaa` — navnerommet var større enn registeret

Dette kom ut av arbeidet og var ikke ventet.

`registry.discover()` finner elleve kilder. `data/raw/` har **tolv**
mapper. Den tolvte er `eierskap_historikk`, som skrives av
`sources/eierskap.py` under et eget navn — en egen serie med helt andre
felter og en helt annen kadens, og med god grunn (`HISTORIKK_KILDE`
forklarer hvorfor de ikke er én kilde).

Følgen er at et oppslag fra kildenavn til kilde **ikke var totalt**. Og
for attribusjon er «fant ingenting» det samme som `None`, altså UBELAGT —
så lokalitetssiden ville nektet å bygge med en feilmelding om en lisens
som er helt i orden. Feil svar, riktig mekanisme, umulig å forstå.

`skriver_ogsaa` gjør oppslaget totalt, og aliasene arver kildens
attribusjon: det er den samme tjenesten som svarer, under samme vilkår.

`test_kildenavn_til_attribusjon_er_et_TOTALT_oppslag` går gjennom
`data/raw/` i drift og krever at hver mappe har en kilde som skriver
under det navnet. I suiten er mappa tom, og testen sjekker da bare
aliaset — det er den samme grensen som gjør at porten ikke kan være en
pytest-test.

## 5. Hva som ble målt

Etter flyttingen, mot ekte data:

    12 kildenavn i indeksen, 11 kilder + 1 alias
    ekspertgruppen -> None (UBELAGT), de 11 andre -> setninger
    /lokalitet/31397/ bygget på nytt: bunnteksten er TEGN FOR TEGN lik
    publiseringsvakten: ingenting å innvende
    814 tester grønne (806 + 8 nye)

At bunnteksten er uendret er poenget: dette er en flytting og ikke en
endring av hva som står på siden.

## 6. Det denne flyttingen IKKE løser

**Attribusjonen ligger fortsatt ikke på RADEN.** Et snapshot kan ikke
svare på hvilket vilkår som gjaldt da raden ble skrevet — det må slås opp
i koden som gjelder nå.

Det er formelt et brudd på CLAUDE.md 1b-3, og det er samme brudd som
`core/persondata.PERSONFORMER` allerede står oppført med: en verdi som
virker ved LESING, der lista kan endre hva et gammelt snapshot betyr.

Hvorfor det ikke rettes nå:

- Et vilkår er en **tredjeparts påstand som kan endres uten at noe i
  dataene beveger seg**. `docs/LISENSKJEDE.md` har en datokolonne nettopp
  derfor. En attribusjon stemplet på raden ville frosset vilkåret slik
  det var den uka, og det er ikke mer sant enn å lese det som gjelder nå
  — bare vanskeligere å oppdatere.
- Det som faktisk trengs den dagen noen spør, er **hvilken lisens som
  gjaldt da vi HENTET**, og den opplysningen finnes allerede: `lest`-datoen
  i lisenskjeden, sammen med `fetched_at` på raden.

Det er en avveining og ikke en forglemmelse, og den skal kunne
overprøves. Prøven er den samme som alltid: kan et snapshot alene svare
på hva verdien var da raden ble skrevet? Nei — og her er svaret at
spørsmålet stilles til `docs/LISENSKJEDE.md` med en dato i stedet.

## Ville snudd det

- **At en kilde trenger ulik attribusjon for ulike deler av det den
  henter.** `eierskap` er nær ved allerede: tillatelsene er
  Fiskeridirektoratets, organisasjonsformene Brregs, og i dag løses det
  ved å kreve begge setningene overalt. Viser det seg at en kilde må
  skille per felt eller per rad, er ett felt på kilden for grovt, og da
  hører vilkåret hjemme nærmere dataene — antakelig på observasjonen.
- **At en lisensgiver krever noe annet enn en setning.** En logo, en
  lenke med bestemt tekst, eller en plassering («øverst på siden»), lar
  seg ikke uttrykke som en streng i en tuppel. Da er `attribusjon` for
  smalt og må bli et objekt.
- **At `registry.discover()` slutter å være veien til kildene.** Hele
  oppslaget hviler på at kilderegisteret er komplett. Kommer det en kilde
  som ikke oppdages — en manuell backfill uten `Source`-klasse — er
  indeksen ufullstendig igjen, og da er `skriver_ogsaa` en plaster på et
  større hull.

**Ville IKKE snudd det:** at tabellen i `nettsted.py` var lettere å lese
samlet. Den var det. En samlet tabell er nettopp formen som blir stående
uendret når en ny kilde kommer til.
