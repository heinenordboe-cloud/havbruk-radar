---
dato: 2026-09-21
tittel: Identiteten er hav og papir — og papiret er valgt på verdi, ikke på tone
status: besluttet
commit: [fylles inn]
---

# Hav og papir

**Bestemt:** Nettstedet har en egen palett og en egen serif, og begge
er begrunnet i målinger framfor i smak.

1. **Havet** (`#0b2e38`) er den eneste mettede flaten, og den finnes
   bare på forsiden. En flate som står på hver side er en bakgrunn.
2. **Papiret** er `#e7dbd0` — L\*88, ikke L\*95. Valgt fordi den lyse
   varianten gjorde tabellarkene usynlige (1,11:1), ikke fordi den er
   «varmere».
3. **Aksenten** er rustoransje og holdes fra trafikklyset på to ledd:
   målt avstand OG form. Aksenten er alltid skrift eller strek;
   trafikklyset er alltid fylt firkant.
4. **Newsreader** bærer overskrifter og ordmerke. Brødteksten er
   systemets sans.
5. **Ordmerket er en plassholder.** Logo og navn er ikke bestemt.

Digdirs `tokens.css` blir stående, men bare skjelettet: typeskala,
avstander, linjehøyder, radier. Fargefamiliene er tatt ut.

---

## 1. Hvorfor papiret ikke er den varme cremefargen

Oppgaven ba om en varm papirflate med Financial Times som referanse.
Første utkast var `#f7f1e4`, og det er riktig svar på oppgaven — og
feil flate.

Målt mot seks vanlige varme off-whites (Tailwind stone, Notion,
Solarized, Muji, m.fl.):

    klyngen      hue 86–95 grader i Lab (gul), L*95–97
    #f7f1e4      hue 92, L*95,3          -> dE 1,7 til nærmeste
    FTs #fff1e5  hue 70, L*95,9          -> rosa, en annen ting

Referansen var altså ikke truffet; klyngen var. Utkastet forsvarte seg
med at ALT varmt og lyst ligger der, og at særpreget måtte bæres av
båndet, serifen og merket. Det er sant så lenge man skrur på TONEN.

**Det slutter å være sant når man skrur på VERDIEN.** Cremefamilien er
definert like mye av å være nesten hvit som av å være varm, og L\* er
aksen ingen defaulter på.

Men avstanden fra klyngen er en bivirkning, ikke grunnen.

## 2. Grunnen er lagdelingen, og den er målbar

Nettstedet er bygget som ark på et bord: `main`, `.topp` og `footer` er
hvite ark (`#fffdf8`) på en bunn. Med `#f7f1e4` var forholdet mellom de
to **1,11:1**. Arkene lå ikke på bordet; de var bordet.

    papir/ark   1,11:1  ->  1,34:1
    hode/ark    1,19:1      1,19:1   (uendret, med vilje)
    kant/papir  1,32:1      1,32:1   (uendret, med vilje)

`--stripe`, `--hode` og `--kant-svak` er avledet på nytt på papirets
egen hue (70 grader), og de to siste forholdene er bevart framfor
gjenoppfunnet: det var ikke noe galt med dem, bare med flata de sto på.

## 3. En mørkere bunn drar alt som står på den med seg

Tre par falt under WCAG AA mot den nye flata, og `test_kontrast` felte
dem. Verdiene er senket til den minste endringen som passerer:

    aksent        #b84a12 -> #aa3e04   bunntekstlenke 3,84 -> 4,54
    blekk-dempet  #5b6b70 -> #546469   bunntekst      4,08 -> 4,54
    kant          #9a9384 -> #8c8576   ring i hodet   2,52 -> 3,03

Den siste var ikke forårsaket av papirbyttet. `--kant` lå under 3:1 på
tonet rad (2,83) og i tabellhodet (2,52) også med det gamle papiret.
Det ble ikke oppdaget, fordi kontrastprøven leste feil halvdel av fila
— se punkt 5.

## 4. Mørk modus er en oversettelse, ikke en invertering

Hero-båndet var `#061f27` mot et papir på `#121a1d`: **1,04:1**. Båndet
fantes ikke. Det eneste man så, var at arket under begynte.

Feilen var å gjøre samme tanke om igjen. I lys modus er havet den
MØRKESTE flaten på en lys side, så i mørk modus ble det gjort enda
mørkere. Men en flate leses av at den skiller seg fra det rundt — ikke
av hvilken vei. Båndet er nå `#13343f`, lysere enn papiret, med
nøyaktig samme forhold (1,34:1) som papir/ark har i lys modus.

Samme feilform, en gang til: `.hero h1` var først `var(--ark)`, som er
papirfarget i lys modus og en MØRK flate i mørk. Båndet er mørkt i
begge. `--hav-tittel` er lys i begge.

## 5. Prøven som ikke målte

`test_kontrast._blokker` fant slutten på mediespørringen ved å lete
etter strengen `\n}\n}`. Da `stil.css` fikk et innrykk (`\n  }\n}`),
fant `find` ingenting og returnerte -1:

    lys  = tekst[:i] + tekst[-1:]     alt ETTER blokka forsvant
    mørk = tekst[i:-1]                alt etter blokka ble lest som mørkt

Følgen var stille og gikk begge veier. Den teller klammer nå.

Det er samme form som CLAUDE.md 1b-2 beskriver: en mekanisme som måler
noe som LIGNER det den skal måle, og som er riktig helt til
formateringen endrer seg.

## 6. Setningen som ble fjernet

Avsnitt 2b i `stil.css` lød: «Nøkternt. En etatsside med en fargeflate
og et logomerke ville påstått at noen står bak — bunnteksten sier at
ingen gjør det.»

Den er fjernet, og ikke dempet. Premisset er feil: en flate og et merke
sier hvem som HAR LAGET nettstedet, ikke hvem som står bak DATAENE. De
to er skilt et annet sted, og der er de sagt rett ut — bunnteksten
navngir hver kilde og sier at ingen av etatene går god for
sammenstillingen. Det er en setning, ikke fraværet av en farge.

Det opprinnelige hensynet er reelt og er ivaretatt av regelen som
faktisk treffer det: ingenting her låner et offentlig våpen, emblem
eller navn.

## 7. Hva som ville snudd dette

- **Papiret:** et bevis på at `#e7dbd0` leses som skittent framfor som
  ubleket på vanlige skjermer. Det er en observasjon om lesere, ikke om
  hex-verdier, og den ville slått lagdelingsargumentet.
- **Serifen:** at Newsreader ikke kommer fram hos en målbar andel.
  `font-display: swap` gjør det utfallet ufarlig, men ikke gratis.
- **Aksenten:** at noen finner ett sted der rust og trafikklysrød
  opptrer i samme form. Formregelen er det leddet som bærer, og den er
  brutt i det øyeblikket.
- **Ordmerket:** at en logo velges. Da byttes `maler/merke.html.j2`,
  og ingenting annet skal trenge å røres. Er det ikke sant, er det en
  feil i denne beslutningen.
