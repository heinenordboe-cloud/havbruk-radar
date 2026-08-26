---
dato: 2026-08-26
tittel: published_at, og at løpenummeret sluttet å være kronologi
status: vedtatt
commit:
---

# published_at, og at løpenummeret sluttet å være kronologi

**Bestemt:** `Observation` får et tredje tidspunkt.

    observed_at    VERDEN   hvilket tidspunkt raden handler om
    fetched_at     OSS      når vi spurte
    published_at   KILDEN   når kilden utga dette svaret

Og som følge av det: **rekkefølgen mellom versjoner av samme dato
avgjøres av utgivelsen, ikke av filnavnet.**

## Hvorfor feltet måtte finnes

De to første tidspunktene holdt i ti dagers drift fordi
`fetched_at` og `published_at` faller sammen NESTEN når vi henter
ferskt. Henter du en gang i uka, ligger utgivelsen timer eller dager
fra hentingen, og forskjellen er støy.

En kropp gravd fram fra et arkiv river dem fra hverandre.
Wayback-kopien av `biostat-total-omr.csv` ble hentet av oss 26.08.2026
og utgitt av Fiskeridirektoratet 20.07.2024. To år.

Uten feltet kan en slik kropp ikke skrives inn i det hele tatt. Enten
får den ELDSTE påstanden det NYESTE hentetidspunktet — og
revisjonsaksen leser baklengs — eller så finner vi på en proveniens.
Det er ikke to dårlige valg blant flere; det er de eneste to.

**Standarden er «vet ikke», aldri `fetched_at`.** Sto hentetidspunktet
der, ville hver kilde automatisk PÅSTÅTT en utgivelsesdato ingen har
gått god for, og påstanden ville vært usann i nøyaktig det tilfellet
feltet finnes for. Samme skille som `utvalg` gjør, av samme grunn.

**Den LESES, den utledes ikke.** `sources/biomasse.py` tar den fra
`Last-Modified`, og fra `X-Archive-Orig-Last-Modified` når kroppen
kommer fra Wayback — samme header, bevart av Internet Archive. Å utlede
den av at «fila oppdateres den 20.» ville vært et gjett på en
tredjeparts vegne. Waybacks egen `Memento-Datetime` brukes ikke: den er
da ARKIVET hentet kroppen, deres `fetched_at`. For 2024-kopien ligger
de 18 dager fra hverandre.

## Det som ikke var forutsett: løpenummeret var en stedfortreder

`data/raw/<kilde>/<dato>.parquet` kolliderer med løpenummer — `.2`,
`.3`. Fram til 26.08.2026 var nummeret en pålitelig stedfortreder for
rekkefølge: en høyere `.N` var skrevet senere OG bar en nyere påstand.
Ingen skrev det ned, fordi ingenting kunne bryte det.

Arkivinnsettingen brøt det. For 2017-10-31 er `.2` Wayback-kopien
utgitt 20.07.2024, skrevet ved siden av en `.parquet` utgitt to år
senere. Høyeste nummer, eldste påstand.

Dette er samme form som F4, F6, F7, F8 og F13: et mål som LIGNER det
det skal måle, og som er riktig helt til de to faller fra hverandre.
Ført som **F14**.

`snapshot.versjoner()` og `forrige_versjon()` ble lagt om samme dag
feltet kom inn. `previous()` og `les_mellom()` ble det ikke, og de er
den andre halvdelen av samme feil — de sorterte fortsatt på filnavn.
Rettet 26.08.2026.

### Hva det ville kostet

Målt på de 81 månedene der en arkivkopi nå ligger ved siden av
basefila:

    endringsrader med riktig baseline (2026-påstanden)   9391
    endringsrader med feil baseline (Wayback 2024)       9389
    differanse                                             -2

    changelog-rader som ville fått FEIL old_value         1805

Antallet endringer beveger seg altså nesten ikke — to rader av 9391.
Det er verdt å si rett ut, fordi det er grunnen til at feilen ville
vært vanskelig å oppdage: ingen teller ville slått ut.

Skaden ligger i den andre linja. 1805 changelog-rader ville oppgitt en
to år gammel verdi som «hva som sto her forrige måned». Radene ville
sett riktige ut, hatt riktig form, telt riktig — og løyet om et tall.
Det er den stille varianten, som resten av 1b-lista.

## Fallet tilbake, og hvorfor det er riktig og ikke bare til stede

`snapshot.publisert()` er `published_at` der den finnes, ellers
`fetched_at`, ellers tom.

De 103 biomasse-basefilene har ikke kolonnen. Det har heller ingen av
de fire andre kildene. Fallbacken bærer altså nesten alt vi eier, og
den kan ikke forsvares med at den «finnes».

Den er riktig fordi `fetched_at` er en ØVRE GRENSE for utgivelsen — du
kan ikke hente noe som ikke er utgitt — og fordi den for en kilde uten
feltet stiger monotont med hver skriving. Utgivelsesrekkefølgen blir da
NØYAKTIG løpenummerrekkefølgen. Fallbacken endrer med andre ord
ingenting for noen kilde som ikke har feltet, og det er det som gjør
den trygg.

Rekkefølgen blir bare riktig så lenge en kropp som er utgitt LENGE før
den ble hentet, faktisk oppgir `published_at`. Derfor NEKTER
`backfill.py --arkiv` å skrive en kropp uten den. **Unntaket er stengt,
og det er hele forutsetningen for fallbacken** — åpnes det igjen, faller
begrunnelsen bort.

En detalj som ikke skal glemmes: sammenligningen er leksikografisk på
ISO-8601-strenger. Det holder fordi begge skrivere normaliserer til
UTC med `+00:00` — `_utgitt()` gjennom `astimezone(utc).isoformat()`,
`fetched_at` gjennom `now(timezone.utc)`. En kilde som skriver et annet
offset ville brutt det stille.

## Gamle snapshots fylles ikke inn

De 103 biomasse-snapshotene fra 25.08 leses som ukjent. Å skrive
26.08.2026 inn i dem ville PÅSTÅTT at Fiskeridirektoratet utga tallene
den dagen VI hentet dem. Regel 2 gjelder her som ellers, og det er
samme svar som de 761 lusetall-snapshotene fikk for `utvalg`.

## Ville snudd det

- **Om en kilde viser seg å oppgi en `Last-Modified` som ikke er
  utgivelsen.** En CDN som stempler fila når den ble kopiert til
  kanten, ikke når redaksjonen slapp den, gjør feltet til en tredje
  målestokk for OSS forkledd som KILDEN. Da må feltet leses fra noe
  kilden selv publiserer — en `dataPublished` i nyttelasten — eller
  stå tomt.
- **Om et offset utenfor UTC dukker opp i en `published_at`.** Da må
  sorteringsnøkkelen parses framfor å sammenlignes som tekst. Målt i
  dag: alle skrivere normaliserer, så kostnaden forsvarer seg ikke ennå.
- **Om `--arkiv` må kunne skrive en kropp uten utgivelsestidspunkt.**
  Da er ikke bare den modusen endret — hele begrunnelsen for at
  `publisert()` kan falle tilbake på `fetched_at` faller bort, og
  rekkefølgen må bæres av noe annet enn en øvre grense.
- **Om løpenummeret må kunne bety noe igjen.** Skulle to kropper med
  samme `published_at` bære ulike påstander, er tiebreakeren en
  vilkårlig avgjørelse forkledd som en regel. Så langt har det ikke
  skjedd.

## Hva som IKKE er avgjort

**Om de fire gjenstående Wayback-kopiene skal hentes.** CDX viser én
fangst av `.csv` (07.08.2024, allerede inne) og seks av `.json`, med
seks distinkte digests. Fire av dem er utgivelser vi ikke har. Å hente
dem krever en JSON-gren i parseren, som i dag bare leser CSV.

Spørsmålet er ikke teknisk — det er om revisjonshistorikk fra
2024–2026 er verdt arbeidet, gitt at prosjektets formål er å se
framover. [din vurdering]

**Om kopien fra 17.01.2025 skal håndteres i det hele tatt.** Den bærer
ingen utgivelsesheader, og arkivmodusen nekter den av seg selv. Regelen
fanger den uten skjønn, og det er riktig. Men det betyr at én
revisjonstilstand er permanent utilgjengelig for oss.
[din vurdering] om det er verdt et unntak med håndskrevet
proveniens, eller om et hull er ærligere enn et gjett.

**Om de fire andre kildene skal lese `published_at`.** Ingen av dem er
undersøkt for om endepunktet oppgir noe brukbart. BarentsWatch og
Enhetsregisteret svarer sannsynligvis med en `Date`-header, men `Date`
er da SVARET ble generert — vårt spørsmål, ikke deres utgivelse. Å
lese den ville vært F14 en gang til, med en ny stedfortreder.
[din vurdering] om det er verdt å undersøke nå, eller om feltet skal
få stå som biomasse-spesifikt til en annen kilde faktisk reviderer.
