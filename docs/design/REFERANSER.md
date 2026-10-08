# Referansene: Our World in Data og SSB

Briefen sier at Kystloggen skal se ut og oppføre seg som en seriøs
datakilde, og peker på to nettsteder som målestokk. Denne fila sier hva
vi har lært av dem, skrevet som regler vi kan holde oss selv til. Hver
regel står med hvordan den brukes her, slik at den kan etterprøves på
nettstedet og ikke bare leses.

## Hva som er sett, og hva som ikke er det

**Ingen av de to nettstedene ble åpnet da fila ble skrevet,
08.10.2026.** Skyøkten designrunden ble gjort i, har en nettverkspolicy
som avviser `ourworldindata.org` og `www.ssb.no` (403 på CONNECT), og
ingen andre veier inn virket heller. Iakttakelsene under er derfor fra
kjennskap til nettstedene slik de har sett ut over tid, ikke fra en
måling i 390 og 1440 denne dagen. CLAUDE.md regel 4: det står her som
antatt, ikke som bekreftet.

Det som er bekreftet samme dag, gjennom søk: OWIDs datasider har en
egen del for gjenbruk med ferdig sitering av både siden og dataene,
hentedato for kildedataene, og en forklaring på hva OWID har gjort med
tallene. Det er det eneste punktet under som er etterprøvd.

Skal reglene verifiseres i nettleser, er det de fem første under
«Nivåer», «Tabeller» og «Grafer og kart» som betyr mest — det er dem
designet hviler tyngst på.

## Hva de to gjør likt

Begge er offentlige referanser som skal kunne siteres, og begge løser
det på samme måte:

- **Siden er hvit eller nær hvit, og innholdet står rett på den.** Ingen
  kort, ingen skygger, svært få rammer. Skillet mellom deler er luft og
  en hårlinje.
- **Én aksentfarge i grensesnittet, og datafargene er en egen palett.**
  OWIDs blåmørke og røde aksent brukes på logo og noen få markeringer;
  SSBs grønne brukes på lenker og knapper. Ingen av dem bruker
  aksentfargen på data, og ingen bruker en datafarge på en knapp.
- **Toppen er lys.** Logo til venstre, få menypunkter, søk. Det mørke
  feltet er bunnteksten.
- **Tallet står først, kilden rett under.** En figur eller tabell har
  tittel over seg og «Kilde: …» under seg, i liten, dempet tekst.
  Kilden er aldri lenger unna enn neste linje.
- **Metoden finnes, men ligger nederst eller bak et klikk.** SSBs «Om
  statistikken» er en rekke lukkede seksjoner nederst på siden; OWIDs
  «About this data» ligger under figuren. Ingen av dem legger
  forbeholdene foran tallet.

## Regler, og hvordan de brukes her

### Nivåer

1. **Én H1, og rett under den en metalinje.** SSB setter «Oppdatert» og
   «Neste oppdatering» rett under tittelen; OWID setter en undertittel i
   grått. Her: type, nummer og hentedato i én linje under H1, i dempet
   sans. *Brukt i `.sidehode`.*
2. **Så én setning som sier hva siden viser nå.** OWIDs undertittel er
   en setning, ikke en etikett. Her: oppsummeringssetningen som allerede
   bygges av data på lokalitets-, selskaps- og ukessiden, satt som
   ingress i Newsreader. *`.ingress`.*
3. **Nøkkeltall er tall og etikett, uten boks.** SSBs nøkkeltall er et
   stort tall, en kort etikett under og perioden. Her: en rad med
   2–5 slike par under ingressen, skilt med luft og en hårlinje over.
   *`.nokkeltall`.*
4. **Tre nivåer under H1, ikke flere.** Seksjon (H2, serif), blokk (H3,
   serif, mindre) og etikett (sans, liten). En fjerde størrelse som
   ligner en av dem, er en feil, ikke en nyanse.
5. **Samme venstrekant for alt.** Tittel, ingress, tabell, figur og
   notat starter på den samme linja. Teksten har et lesemål, men det
   kortes fra høyre, aldri med innrykk fra venstre.

### Rytme

6. **Avstand bærer strukturen, ikke rammer.** To avstander gjør
   jobben: mellom seksjoner (56–72 px) og inne i en blokk (8–24 px). En
   seksjon begynner med en hårlinje over H2.
7. **En boks er for noe man skal kunne kopiere eller fylle ut.**
   Søkefeltet og siteringsteksten. Et notat er tekst, ikke en boks.

### Tabeller

8. **Tittel over, kilde og merknad under.** `<caption>` er tittelen;
   kilde, utsnitt og forbehold står i en dempet linje under tabellen.
9. **Hårlinjer mellom rader, ingen loddrette linjer, ingen ramme rundt.**
   Tabellhodet er liten, dempet sans over en mørk strek.
10. **Tall står til høyre, i samme sifferbredde.** Tekst til venstre.
    Enheten står i kolonnehodet når den er lik for hele kolonnen.
11. **Navnet i en rad er en lenke uten å rope.** I en liste med hundre
    rader er hver rad en lenke; da er det understrekingen som sier det,
    ikke fargen. Lenka er blekkfarget med en svak strek; under peker får
    den aksentfargen.
12. **Nedlasting står ved tabellen den gjelder.** SSB legger «Last ned»
    ved hver tabell. Her: nedlastingslenkene står i én linje rett under
    tabellen eller i sidens verktøylinje, med format i parentes.

### Grafer og kart

13. **Tittel og undertittel over, kilde under, ingen ramme.** Svake
    vannrette hjelpelinjer, aksetekst i dempet farge.
14. **Peker gir en loddrett linje og et verktøytips med eksakt verdi og
    dato.** Tipset følger pekeren, men skal aldri dekke figurens egen
    tekst (tittel, tegnforklaring, kilde). Her: tipset ligger inne i
    tegneflata og snur når det når kanten.
15. **Alt pekeren kan nå, kan tastaturet nå.** Samme tips ved fokus,
    synlig fokusmarkør. Tabellen med de samme tallene ligger rett under
    figuren for den som ikke vil bruke den.
16. **Kartet er en figur som de andre.** Tegnforklaring og målestokk
    står i kanten eller under, kreditering under kartet, aldri oppå
    punktene. Et punkt under peker eller i fokus framheves og navngis.

### Kilder og sitering

17. **To siteringer, og begge kan kopieres.** OWID gir én for siden og
    én for dataene, med hentedato. Her: «Siter denne siden» med dato og
    sjekksum, og kildenes egen attribusjon i bunnteksten.
18. **Kildens navn står ved tallet, lisensen står i bunnteksten.**
    Attribusjonssetningene er lisensplikter og står ordrett på hver side.

### Navigasjon

19. **Få menypunkter, alltid synlige.** Fem punkter på én linje, som
    ruller vannrett heller enn å bli en meny bak en knapp.
20. **Brødsmula står over H1, liten og dempet.** Den sier hvor i
    hierarkiet siden er; den er ikke en tittel.
21. **Bunnteksten er kart, ikke kolofon.** Spalter med kilder og vilkår,
    lenker inn i arkivet og kontakt, kant til kant.

### Peker og fokus

22. **Peker endrer én ting.** En lenke blir aksentfarget og får tykkere
    strek. En tabellrad får en svak tone, slik at øyet kan følge den
    tvers over. Ingenting hopper eller flytter seg.
23. **Fokus er alltid synlig, og alltid den samme ringen.** 2 px
    aksentfarge med 2 px luft, på alt som kan få fokus.

## Hva vi bevisst ikke tar med

- **OWIDs faner (graf / kart / tabell).** De krever JavaScript for å
  bytte visning. Her står graf og tabell etter hverandre, og tabellen
  ligger bak en `<details>` som virker uten skript.
- **SSBs trekkspill rundt hovedinnholdet.** SSB lukker store deler av
  siden. Vi lukker bare det som er lange lister og metodetekst, og det
  står alltid hva som ligger bak.
- **Hvit bakgrunn.** Papirfargen er identiteten, og den er målt mot hver
  tekstfarge. Rollen er den samme: én rolig flate.
