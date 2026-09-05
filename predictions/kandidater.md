# Kandidater — spørsmål som avgjøres av kvotesystemets høringsrunde

Spørsmål, ikke påstander. Ingen av dem er besvart her, og ingen av dem
skal besvares her: en kandidat blir en prediksjon først når den skrives
som en falsifiserbar påstand i en `predictions/<dato>.yml`, med retning,
terskel, vindu, `feil_hvis` og `konfidens`. Det krever en vurdering som
ikke kan utledes av registeret, og derfor står feltene tomme.

---

## Hva jeg IKKE har verifisert

CLAUDE.md regel 4 gjelder her mer enn noe annet sted i repoet:

- **Jeg har ikke lest høringsnotatet.** Det finnes ikke i dette repoet,
  det er ikke hentet av noen kilde i `sources/`, og ingenting i
  `data/arkiv/` inneholder det. Alt jeg vet om innretningen på et
  kvotesystem er annenhånds.
- **Jeg vet ikke høringsfristen, og ikke datoen for et vedtak.** Alle
  vinduer under står som `<frist>` og `<vedtak>`. De må fylles inn fra
  kilden, ikke fra hukommelsen — heller ikke min.
- **Jeg vet ikke om høringen faktisk berører alle mekanismene under.**
  Spørsmålene er formulert ut fra hva REGISTERET ville vist hvis den
  gjorde det, ikke ut fra hva notatet sier.

Det som følger er derfor ikke en analyse av høringen. Det er en liste
over hva dette arkivet er i stand til å se, stilt som spørsmål — og en
notat om hvilke spørsmål det ikke kan se i det hele tatt.

**Før du gjør en kandidat om til et anslag:** sjekk at feltet finnes og
har dekning. `data/feltnormal/` og `data/health.json` sier hvor mange
entiteter som faktisk leverer feltet. Et anslag om et felt med tynn
dekning blir `kan_ikke_avgjores`, og det måler formatet, ikke deg.

---

## A. Selve kvotemekanikken — vises den i registeret?

### A1
Endrer `kapasitet_enhet` seg for noen lokalitet i Akvakulturregisteret
i løpet av vinduet?

*Hvorfor spørsmålet er skarpt:* et kvotesystem målt i noe annet enn
MTB-tonn må uttrykkes i registeret på et tidspunkt. Feltet finnes
allerede, og `rules/signals.yml` behandler enhetsbytte som sin egen regel
nettopp fordi et bytte gjør prosentendringer meningsløse. Skjer det, er
det synlig samme uke.

*Måles i:* `akvakultur.kapasitet_enhet` — 1779 lokaliteter har feltet.
*Type:* `verdi` eller `endring`. Merk at et anslag om at ingenting skjer
er `uendret`, og det er et ekte anslag.

### A2
Dukker det opp en verdi i `tillatelse_type` eller `kapasitet_type` i
eierskapskilden som ikke fantes ved vinduets start?

*Hvorfor spørsmålet er skarpt:* dette er en NY VERDI i et eksisterende
felt, ikke et nytt felt. Skillet er avgjørende og allerede innarbeidet:
`diff.compare()` undertrykker nye FELTER som skjemautvidelse (CLAUDE.md
1b-3), men en ny verdi i et felt som fantes fra før er en ekte hendelse
og går gjennom.

*Måles i:* `eierskap.tillatelse_type`, `eierskap.kapasitet_type` — 2952
tillatelser.
*Åpent:* dagens verdimengde må leses ut FØR anslaget skrives, ellers kan
«ny verdi» ikke avgjøres.

### A3
Endrer `prodomraade_status` seg for noe produksjonsområde i vinduet — og
i så fall: følger endringen trafikklysvedtaket, eller bryter den med det?

*Hvorfor spørsmålet er skarpt:* de tre anslagene fra 18.08.2026 hviler
alle på at registeret henger etter trafikklysvedtaket av 19.06.2026, og
at det må ta igjen. Erstattes trafikklyset av et kvotesystem, kan feltet
i stedet fryse eller forsvinne — og da bommer alle tre av en helt annen
grunn enn dømmekraft.

*Måles i:* `akvakultur.prodomraade_status` — 970 lokaliteter har feltet
(ikke alle 1779; dekningen er ujevn og det er verdt å vite før du spår).
*Merk:* dette spørsmålet er delvis allerede spådd. Et nytt anslag om
samme felt må tilføre noe de tre ikke sier, ellers måler det bare dem.

---

## B. Adferd i forkant av et vedtak

Dette er den mest interessante gruppen, og den vanskeligste. Den handler
om at aktører gjør noe FORDI de venter en regelendring — og det er
nettopp det som ikke kan leses ut av høringsnotatet.

### B1
Går antallet eierskapsoverføringer i vinduet opp eller ned sammenlignet
med samme periode i tidligere år?

*Hvorfor spørsmålet er skarpt:* to motsatte mekanismer er begge
plausible, og det er derfor det er verdt å spå. Enten selger man før
reglene strammes, eller så fryser markedet mens ingen vet hva en
tillatelse er verdt. Registeret kan skille dem; en kvalifisert gjetning
kan ikke.

*Måles i:* `data/raw/eierskap_historikk/` — 21 årssnapshots tilbake til
2006, 2611 overføringer. Grunnlaget for en sammenligning finnes.
*Åpent:* hva som er riktig sammenligningsgrunnlag — samme kalendermåneder
i tidligere år, eller et glidende snitt. Velg FØR du ser tallet.
*Advarsel:* denne serien er backfillet og revidert én gang alt
(`ecb672b`). Les CLAUDE.md 1b-5 før du bygger et anslag på den.

### B2
Konsentreres eierskapet i vinduet — går antallet distinkte `eier_orgnr`
ned mens summen av kapasitet holder seg?

*Måles i:* `eierskap.eier_orgnr`, `eierskap.kapasitet` — 2952 tillatelser.
*Åpent:* om «konsentrasjon» skal måles som antall eiere, som andelen hos
de fem største, eller som en HHI. De tre kan svare ulikt, og valget må
tas i `grunnlag` før vinduet åpner, ikke etter.
*Formatbegrensning:* prediksjonsformatet spår ETT felt for ÉN entitet.
Et aggregat over alle eiere passer ikke inn slik formatet står i dag —
se «Spørsmål formatet ikke kan bære» nedenfor.

### B3
Skjer det en økning i `tillatelser_trukket` på lokalitetsnivå i vinduet?

*Måles i:* `akvakultur.tillatelser_trukket` — men merk: bare 856 av 1779
lokaliteter har feltet, og tallet har ligget flatt på 856 i både
`felt_referanse` og `felt_sist`. Det er halv dekning, og et anslag her
har forhøyet risiko for `kan_ikke_avgjores`.

### B4
Går noen av de mindre rettighetshaverne konkurs eller under avvikling i
vinduet?

*Måles i:* `enhetsregisteret.konkurs`, `enhetsregisteret.under_avvikling`
— 1810 enheter, full dekning.
*Type:* `verdi` med `verdi: "True"` for en navngitt entitet.
*Advarsel — dette er den kandidaten som er lettest å skrive galt:* et
anslag om at ett navngitt selskap går konkurs er en påstand om et
foretak, ikke om et menneske, så lenge entiteten er et AS. Er den et ENK,
er den et menneske, og da skal anslaget ikke skrives i det hele tatt —
CLAUDE.md regel 3. Sjekk `organisasjonsform` FØR du velger entitet.
ENK filtreres i kilden fra 22.08.2026, så en ENK-entitet vil uansett gi
`kan_ikke_avgjores` — men det er en tilfeldig beskyttelse, ikke en
grunn til å la være å sjekke.

### B5
Endres `kapasitet_midlertidig` for flere lokaliteter i vinduet enn i en
tilsvarende periode uten en varslet regelendring?

*Hvorfor spørsmålet er skarpt:* midlertidig kapasitet er den raskeste
knappen å trykke på når rammene er usikre. Feltet har full dekning
(1779).

---

## C. Andrelinje — det kvotesystemet skal styre

### C1
Endrer forholdet mellom stående biomasse og uttak seg i vinduet, på en
måte som skiller seg fra sesongmønsteret i 2017–2026?

*Måles i:* `biomasse.biomasse_kg`, `biomasse.uttak_antall` — 104 måneder
tilbake til 2017-10, ingen hull.
*Advarsel, og den er alvorlig:* biomassefila REVIDERES bakover. 12,3 % av
felles rader endret seg mellom to publiseringer, og etterslepet er satt
til fire måneder fordi revisjonsandelen først flater ut der (CLAUDE.md
1b-5). Et anslag med et vindu kortere enn fire måneder kan ikke avgjøres
på biomasse i det hele tatt — tallet finnes ikke ennå når vinduet lukker.
*Konsekvens:* `vindu.til` må ligge minst fire måneder etter den siste
måneden anslaget handler om. Regn det ut, ikke anslå det.

### C2
Faller lusepresset i produksjonsområdene der kapasitet eventuelt trekkes
ned, målt over vinduet?

*Måles i:* `lusetall.voksne_hunnlus` — men bare 576 av 1777 lokaliteter
leverer feltet. Det er den tynneste dekningen blant alle kandidatene her.
*Advarsel:* `har_medikamentell_behandling` og `har_rensefisk` er begge i
et nullstrekk (90 og 172 uker). Feltene KOMMER, men sier ingenting. Et
anslag som hviler på dem vil bomme uten at det betyr noe om verden — det
betyr noe om kilden. Se CLAUDE.md 1b-4.

### C3
Endres brakkleggingsmønsteret i vinduet?

*Måles i:* `lusetall.brakklagt` — full dekning (1777), og ingen nullstrekk.
Den beste dekningen blant lusefeltene.

---

## D. Spørsmål formatet ikke kan bære

Disse hører hjemme i listen fordi de er verdt å svare på, og fordi det er
ærligere å si at de ikke passer enn å presse dem inn i et format som
ville gjort dem uavgjørbare.

Prediksjonsformatet spår **ett felt for én entitet**. Det kan ikke
uttrykke:

- **Aggregater.** «Antall distinkte eiere går ned 10 %» (B2) er et tall
  over hele kilden, ikke over én `entity_id`.
- **Forhold mellom to felter.** «Biomasse per tillatelse går opp» (C1)
  krever to serier.
- **Sammenligning mot et historisk grunnlag.** «Flere overføringer enn
  normalt» (B1) krever at «normalt» er definert et sted formatet ikke har.
- **Fravær av en kilde.** «Trafikklysfeltet slutter å oppdateres» er
  `uendret` med terskel 0 — som formatet strengt tatt kan uttrykke, men
  som betyr noe annet enn det ser ut som.

**Dette er en beslutning som ikke er tatt.** Enten skrives disse
spørsmålene om til å handle om én navngitt entitet der bevegelsen ville
vært størst — som er et dårligere spørsmål, men et avgjørbart et — eller
så må `core/predictions.py` få en aggregattype. Det siste er en utvidelse
av en kontrakt, og CLAUDE.md regel 1 sier at et slikt valg er ditt, ikke
mitt.

`[din vurdering]`

---

## Før du skriver det første anslaget

1. **Fyll inn de faktiske datoene.** Høringsfrist og forventet
   vedtaksdato. Alt her står som `<frist>` og `<vedtak>` fordi jeg ikke
   har dem.
2. **Sett `vindu.til` etter kildens etterslep, ikke etter vedtaket.**
   Biomasse har fire måneders etterslep, lusetall og sjøtemperatur fire
   uker. Et vindu som lukker før dataene finnes gir
   `kan_ikke_avgjores` — og det er formatet som svikter, ikke du.
3. **Skriv `feil_hvis` før `grunnlag`.** Er falsifiseringen vanskeligere å
   formulere enn begrunnelsen, er påstanden ikke skarp nok ennå.
4. **Ta med minst ett anslag du tror kan bomme.** En logg der alle
   vinduene var trygge måler ingenting, og en skeptiker ser det umiddelbart.
5. **Ikke gjenta en signalregel.** Et anslag som sier det samme som
   `rules/signals.yml` alt fanger, måler regelen og ikke dømmekraften.
