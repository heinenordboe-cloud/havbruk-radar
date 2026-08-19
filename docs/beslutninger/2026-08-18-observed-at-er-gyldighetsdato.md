---
dato: 2026-08-18
tittel: observed_at er datoen snapshotet gjelder for, ikke datoen vi hentet det
status: delvis feil
commit: 
---

# observed_at er gyldighetsdato

> **Note 19.08 — én påstand i denne posten falt.** Skillet mellom
> `observed_at` og `fetched_at` står, og var riktig. Det som er galt er
> setningen under om at `dager_siden()` «gjør allerede det riktige»:
> frekvensvakten målte mot filnavnsdatoen, altså mot `observed_at`, og
> ble permanent utløst for enhver kilde med etterslep. Posten er derfor
> **delvis feil**, ikke erstattet — resten gjelder uendret. Se
> [frekvensvakten måler innsamling, ikke
> observasjon](2026-08-19-frekvensvakt-maler-innsamling.md).

**Bestemt:** `observed_at` betyr datoen snapshotet gjelder for.
`fetched_at` betyr når API-et ble kalt. Erstatter punktet om merking i
[backfill-beslutningen fra 17.08](2026-08-17-backfill-rekkefolge.md), som
sier at `observed_at` betyr «da vi så det» og at et nytt felt skal bære
«da det gjaldt».

**Skillet:** `observed_at` handler om verden. `fetched_at` handler om oss.

For ukentlig innsamling faller de sammen, fordi vår eneste kunnskap om
verden er datert av at vi så etter. For backfill spriker de: regnskapstall
for 2022 hentes i 2026.

**Hvorfor omdefineringen er gratis:** Innsamling og gyldighet har vært
samme dato i hver eneste fil som er skrevet til nå. Omdefineringen er
derfor retroaktivt sann for hele historikken. Ingen migrering, ingen
omskriving av append-only-data. Det vinduet lukker i det øyeblikket den
første backfillede fila skrives.

**Hvorfor den andre veien er dyrere:** Filnavnet ER `observed_at`, og all
rekkefølge- og diff-logikk nøkler på dato i filnavn. Betyr `observed_at`
«da vi hentet», lander all backfill i ett snapshot datert i dag, diffen
ser 700 uker som «ny» i samme kjøring, og et helt nytt sammenligningslag
må skrives ved siden av det som finnes.

Med gyldighetsdato skriver backfill av lusetall uke 9 i 2015 fila
`data/raw/lusetall/2015-03-02.parquet`, og `previous()`, `les_mellom()`,
`siste_dato()` og `dager_siden()` gjør allerede det riktige. Maskineriet
arves gratis.

> **Feil, 19.08.** De tre første gjør det riktige. `dager_siden()` gjorde
> det ikke: den var frekvensvaktens eneste kilde, og målte mot
> filnavnsdatoen — som denne posten nettopp omdefinerte til å bety
> gyldighet og ikke henting. For lusetall med fire ukers etterslep leste
> vakten permanent 28 dager. Se noten øverst.

**Merkingen han ville ha finnes allerede.** En backfillet rad er en rad
der `fetched_at` ligger langt etter `observed_at`. Det er utregnbart, det
krever ingen ny kolonne, og det kan ikke komme ut av synk med seg selv.

**Hva som faktisk må endres i kode:**

1. `health.py` må vite at en skriving er historisk. Volumreferansen og
   feltvakten er høyvannsmerker mot forrige kjøring, og backfill av
   hundrevis av uker vil enten fyre konstant eller forgifte
   referansenivået. Et flagg og en tidlig retur, ikke en omskriving.
2. Et backfill-inngangspunkt ved siden av `run.py`, som skriver snapshots
   i datorekkefølge og deretter utleder diff og changelog per uke. Ikke en
   endring i kjernen.
3. Docstringen i `contract.py` sier i dag «ISO-dato for kjøringen». Den
   må si hva feltet nå betyr, ellers arver neste leser den gamle
   forståelsen.

`diff.compare()` trenger ingen endring: `if old is None: continue` gjør
det riktige når backfill prosesseres eldst først.

**Åpent, og bevisst utsatt:** Kilder der ett kall returnerer flere
perioder samtidig — regnskap for flere år for ett selskap — krever at
`parse()` deler på periode og at driveren skriver ett snapshot per
periode. Det er et parse-nivåspørsmål og avgjøres når den første slike
kilden bygges.

**Den ærlige innvendingen:** For rene registerpollinger sier ikke Brreg
når et tall endret seg, bare hva det er nå. Der er «datoen snapshotet
gjelder for» i praksis «datoen vi så etter», og å kalle det gyldighet er
en liten fiksjon. Den er akseptert fordi alternativet — to konkurrerende
tidsakser der den ene styrer filnavn og den andre betydning — er verre.

**Prisen:** En definisjon som er lett å lese feil hvis man kommer til
prosjektet uten denne posten. Derfor står den i `contract.py` også.

**Ville snudd det:** At en kilde viser seg å trenge både hentetidspunkt
og gyldighetsperiode som *intervall* og ikke som dato — en verdi som
gjaldt fra mars til september. Da holder ikke én dato, og skjemaet
trenger et periodefelt. Det er en utvidelse, ikke en reversering.
