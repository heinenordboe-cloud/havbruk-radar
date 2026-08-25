---
dato: 2026-08-25
tittel: Utvalget skiller ukjent fra ingen filtrering
status: vedtatt
commit:
---

# Utvalget skiller ukjent fra ingen filtrering

**Bestemt:** `utvalg` har tre tilstander, ikke to.

    kilde.utvalg      på disk     utvalg.les()   betyr
    ---------------------------------------------------------------
    {"n": [...]}      {"n":[…]}   {"n":[…]}      kjent utvalg
    {}                "{}"        {}             kjent: ingen filtrering
    None              ""          None           ukjent

`Source.utvalg` er `None` som standard. `lusetall` deklarerer `{}` i
`hent_uke()`. Snapshots skrevet før denne endringen har tom streng og
skal leses som **ukjent**, uansett hva kilden faktisk gjorde.

**Skillet:** «vi vet ikke hva vi ba om» er ikke «vi ba om alt».

## Hvorfor det ikke var godt nok

`utvalg` kom inn 24.08.2026 med to tilstander: et utvalg, eller tomt.
Tomt måtte da bære to helt ulike påstander samtidig.

For `lusetall` var sammenblandingen direkte gal.
`/v1/geodata/fishhealth/locality/{år}/{uke}` tar ingen
utvalgsparametre og returnerer alle lokaliteter som rapporterte den
uka. Det er ikke fravær av kunnskap — det er kunnskap om fravær av
filtrering. Et snapshot som sier «vet ikke» om noe vi vet, sier noe
usant om seg selv.

Merk at `serialiser()` allerede HADDE den riktige regelen i
docstringen sin fra 24.08:

> Tom streng og ikke `"{}"`: de to betyr ulike ting. `{}` er «kilden
> sier at den ikke filtrerer», tom streng er «kilden sier ingenting».

Koden gjorde det motsatte — `if not n: return ""` kollapset dem. En
dokumentert intensjon som ikke er implementert er verre enn ingen: den
får neste leser til å tro at skillet finnes.

## Samme skille, en etasje ned

Prosjektet hadde allerede dette riktig ett sted og galt et annet.

`lus_er_rapportert` finnes fordi en lokalitet uten rapportering og en
med null lus ikke er det samme, og fordi 0,0 er en lovlig målt verdi.
`temperatur_er_rapportert` finnes av nøyaktig samme grunn — 0,0 grader
forekommer 675 ganger i historikken. Uten flagget blir «ingen rapport»
til null i enhver analyse.

`{}` mot `None` i utvalget er den samme setningen om et annet felt.

## Representasjonen, og hvorfor ikke noe annet

`{}` og `None` framfor et eget felt eller en sentinelverdi:

- **Ikke en egen kolonne** (`utvalg_er_kjent`). Den ville vært et andre
  felt som kan sprike med det første, og et snapshot med
  `utvalg=""` og `utvalg_er_kjent=True` er en tilstand ingen kan tolke.
  Én kolonne som bærer tre verdier kan ikke motsi seg selv.
- **Ikke en sentinelstreng** (`"alt"`, `"__alle__"`). Da må hver leser
  kjenne magiske ord, og en kilde kunne i prinsippet levert en nøkkel
  med samme navn. `"{}"` er allerede gyldig JSON og allerede det
  `les()` returnerer det riktige for.
- **Standarden er `None`, ikke `{}`.** Dette er det avgjørende valget.
  Sto standarden som `{}`, ville enhver kilde som aldri har tenkt på
  spørsmålet automatisk påstått at den henter alt — en påstand ingen
  har gått god for. `akvakultur` står i dag som ukjent, og det er
  riktig: ingen har undersøkt om endepunktet filtrerer.

Fella er at `{}` og `None` begge er usanne i Python. `if not utvalg:`
behandler dem likt og er nesten alltid feil. Derfor finnes
`utvalg.er_ukjent()` og `utvalg.henter_alt()` — for å gjøre
forskjellen tungvint å overse.

## Konsekvens for utvidelsesregelen

`er_utvidet()` fikk to ytterpunkter den generelle regelen ikke dekket,
fordi den er skrevet for to kriteriesett og leser et tomt sett som
«ingen kriterier» i stedet for «alle entiteter»:

- **Fra ingen filtrering til et filter er ikke en utvidelse.** Bredere
  enn alt finnes ikke. Uten regelen ville en ny nøkkel i `til` blitt
  lest som utvidelse, og radene som FORSVANT blitt merket som noe som
  kom til.
- **Fra et filter til ingen filtrering ER den størst mulige
  utvidelsen.** Den generelle regelen sa usant her, fordi kriteriene i
  `fra` ikke finnes igjen i et tomt `til` — de er ikke fjernet, de er
  blitt overflødige.

Ukjent smitter som før: mangler ett av utvalgene, er svaret usant. En
undertrykt rad er en hendelse ingen får se, og fallbacken skal falle
mot den siden der feilen er synlig.

## De 761 gamle lusetall-snapshotene

**De fylles ikke inn retroaktivt.** Regel 2 står: en fil som er skrevet
røres ikke. De blir stående med tom streng, altså **ukjent**.

Det er ikke en nødløsning, det er det riktige svaret. Vi visste ikke
hva vi ba om da vi skrev dem — ikke fordi endepunktet var uklart, men
fordi feltet ikke fantes og ingen hadde stilt spørsmålet. Å skrive
`{}` inn i dem nå ville vært å datere en kunnskap til før den fantes,
og det er den samme feilen som å lese klokka på nytt et sted til.

Praktisk konsekvens: en sammenligning mellom et snapshot fra før
25.08.2026 og et etter gir `er_utvidet() == False`, fordi det ene er
ukjent. Ingenting undertrykkes over skjøten. Det er riktig retning —
skjøten skal koste støy, ikke stille undertrykkelse.

## Ville snudd det

- **Om `{}` viser seg å måtte bety noe mer enn «alt».** Et endepunkt som
  «henter alt» innenfor en implisitt grense — bare aktive lokaliteter,
  bare siste år — er ikke ufiltrert, det er filtrert av noen andre. Blir
  det vanlig, må den implisitte grensen skrives som et kriterium
  (`{"status": ["aktiv"]}`), og `{}` reserveres for det som faktisk er
  alt. Da er ikke beslutningen snudd, men `{}` blir sjeldnere riktig
  enn den ser ut nå.
- **Om tre tilstander viser seg å være for få.** «Kjent, men ikke
  uttrykkbart i nøkkel-til-liste» er en fjerde som kan komme — et
  fritekstsøk, et geografisk polygon. Da må formatet utvides, ikke
  tilstandene gjenbrukes til noe de ikke betyr.
- **Om `if not utvalg:` dukker opp i en ny leser og gir feil svar.** Det
  ville vist at predikatene ikke er nok, og at tilstandene må bæres av
  en type som ikke har en usann tolkning — en enum eller et objekt. Så
  langt er lesernes antall lite nok (`er_utvidet`, `beskriv`,
  `diff.compare` gjennom `snapshot.utvalg_i`) til at kostnaden ikke
  forsvarer seg.

## Hva som IKKE er avgjort

`akvakultur` og `enhetsregisteret` er ikke gjennomgått for om de burde
deklarere noe. `enhetsregisteret` setter allerede
`{"naeringskoder": [...]}`. `akvakultur` setter ingenting og står som
ukjent til noen har sett på om endepunktet filtrerer.
