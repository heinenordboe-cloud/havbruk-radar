# Måling: Havbruksfondet

Målt 12.10.2026 mot `havbruk-radar-data` og kropper arkivert samme dag.
Skriptene ligger i `analyse/havbruksfond/` og arkiveringen i
`arkiver_havbruksfond.py`. Dokumentet beskriver hva som er målt. Det
vurderer ikke hva målingen er verdt.

**Merkene:** MÅLT = holdt mot en arkivert kropp med oppgitt sha256.
MÅLBAR = lest i et snapshot, avledet eller regnet ut av målte tall, men
ikke selv holdt mot en kropp. UBELAGT = ingen kropp vi har sier det.

---

## A1. Regelverket

### Funnet: det er en instruks, ikke en forskrift

Fordelingen mellom kommuner og fylkeskommuner står **ikke i en
forskrift**. Den står i Nærings- og fiskeridepartementets instruks til
Fiskeridirektoratet av 27.09.2024. Hvert år kommer et brev fra
departementet («orientering») med beløpet. Ingen kropp vi har lest
viser til en forskrift på Lovdata, og Fiskeridirektoratets side om
fondet viser bare til instruksen. Lovdata er derfor ikke arkivert for
dette punktet. (MÅLT at siden og instruksen ikke viser til en
forskrift. Vi har ikke søkt gjennom hele Lovdata.)

**Fiskeridirektoratets side lenker feil.** Lenketeksten «Instruks for
utbetalinger fra Havbruksfondet (pdf, 95.0 kB)» peker på «Orientering om
utbetalinger fra Havbruksfondet i 2025», som er beløpsbrevet av
10.11.2025. Instruksen svarer 404 på begge adressene den har hatt på
fiskeridir.no. Den ligger i Wayback, i et avtrykk fra 03.11.2024, og er
hentet derfra. Fra og med «Utbetalingene fra Havbruksfondet fordeles
med 80%» har Fiskeridirektoratets side samme ordlyd som instruksen.
MÅLT med tegnvis sammenligning etter at linjeskift er normalisert. Det
som skiller, er brevhodet, hilsenen, ett kolon og to skrivemåter:
instruksen skriver «akvakulturregistreret» og «Akvakulturregisteret»,
siden skriver «akvakulturregisteret» begge steder. Siden er derfor en
gjengivelse av den gjeldende instruksen, ikke av en annen versjon.

### Kroppene

Alle ble arkivert 12.10.2026 av `arkiver_havbruksfond.py` (kode `d47cfdd`)
og ligger i datarepoet med commit `7f16671`. `published_at` er
`X-Archive-Orig-Last-Modified` der Wayback hadde den. Ellers står feltet
tomt. `/CreationDate` er PDF-ens egen påstand og ikke en utgivelsestid.

| kropp | sti (`data/arkiv/…`) | sha256 | dato |
|---|---|---|---|
| Fiskeridirektoratets side om fondet | `havbruksfondet/2026-10-12.bin.gz` | `c1a2f596b3f7bfcf1a0422664dae431a957f6b468c278bccce9557266c4d6951` | hentet 12.10.2026 |
| **Instruks 27.09.2024** (gjeldende), Wayback 03.11.2024 | `havbruksfondet/2026-10-12.12.bin.gz` | `a47f03cf9327614f68c618e84c9399e92bc932725f366f38c25a9de69606b925` | PDF 2024-09-27 |
| Instruks 30.11.2022 (erstattet), Wayback 26.09.2023 | `havbruksfondet/2026-10-12.13.bin.gz` | `fb3ae757c1e585ee80e424da115ac13759496b790fd50ee91783037de7d15232` | PDF 2022-11-30 |
| Supplerende instruks 2023, Wayback 17.07.2024 | `havbruksfondet/2026-10-12.14.bin.gz` | `ef32a8ce9736f4f8653496df21a77c31686955ab22cb84f3d74a30aa0cd44628` | PDF 2023-12-01 |
| Orientering om utbetalinger 2025 | `havbruksfondet/2026-10-12.11.bin.gz` | `f855e14d60349543c693b66034bf331a4a0472785c0988c31a96e8a74fa1af8a` | brevet datert 10.11.2025 |
| Regneark, utbetaling 2025 | `havbruksfondet/2026-10-12.8.bin.gz` | `e26cfffe259153d0f9fd9d84c3f2a89b3d904e290c0f48f5978a667e38308b76` | |
| Regneark, utbetaling 2024 | `havbruksfondet/2026-10-12.7.bin.gz` | `4a56b3c077e3695f55971a95d51f1f9f82d52aa0db29c18220c93db52cb3ba55` | |
| Pressemelding, fastpris 2024 | `regjeringen-pressemeldinger/2024-06-06.bin.gz` | `ced658f6756116387248c7410e7d902cc3b1c2f958658b687943ccb3fe1200b7` | Last-Modified 06.06.2024 |
| Pressemelding, auksjon 2024 | `regjeringen-pressemeldinger/2024-06-25.bin.gz` | `ce7c58a074e794350d850bf64919d52ece1c242403c67594a99bd543e67046aa` | Last-Modified 25.06.2024 |
| Pressemelding, utbetaling 2025 | `regjeringen-pressemeldinger/2025-11-10.bin.gz` | `35b92f454817a8bc6430314b69b2b799a296e84f2feee60d0a1fe6d2396b8a69` | Last-Modified 05.12.2025, se under |

Regnearkene for 2017–2023 er også arkivert (`.2`–`.6`, `.9`, `.10`).
Alle sha256-ene står i `havbruksfondet/2026-10-12.logg.json`.

**Pressemeldingen 2025 er avtrykket fra 05.12.2025.** Skriptet ba om
avtrykket fra 10.11.2025 kl. 13.41, men Wayback svarte med avtrykket fra
05.12.2025. Avtrykket fra 10.11 er hentet for hånd og ligger ikke i
arkivet. Artikkelteksten i de to er tegn for tegn lik (5 990 tegn). Det
som skiller dem, er sidekrom rundt artikkelen. MÅLT.

### Ordrett

Alle sitatene er fra instruksen av 27.09.2024 med mindre noe annet er
oppgitt.

**Fordelingsnøkkelen**

> «Både kommunenes og fylkeskommunenes andel fordeles forholdsmessig
> basert på klarert lokalitets-MTB i den enkelte kommune og
> fylkeskommune, slik det går frem av akvakulturregistreret 1. september
> kl. 12.00 i utbetalingsåret.»

**Måledatoen:** «1. september kl. 12.00 i utbetalingsåret» (samme
setning). For 2026 betyr det 01.09.2026 kl. 12.00, altså 10.00 UTC.

**Arter og lokaliteter**

> «Lokalitets-MTB (maksimal tillatt biomasse) for alminnelige
> matfisktillatelser og tillatelser til særlige formål benyttes for
> fordelingsnøkkel. Kun lokaliteter for laks, ørret og regnbueørret i
> sjøvann inngår i fordelingsnøkkelen.»

**Lokaliteter over en kommunegrense**

> «Dersom det kartfestede arealbeslaget til en lokalitet (i overflaten),
> slik det er registrert i Akvakulturregisteret, krysser en kommunegrense
> (og eventuelt fylkesgrense), så skal utbetalingen denne lokaliteten gir
> opphav til, fordeles mellom angjeldende kommuner (og eventuelt
> fylkeskommuner) i samsvar med lokalitetens kartfestede arealbeslag
> innenfor hver av kommunene.»

**Delingen mellom kommuner og fylkeskommuner**

> «Utbetalingene fra Havbruksfondet fordeles med 80% til kommuner og 20%
> til fylkeskommuner, fra og med utbetalingsåret 2024.»

Instruksen av 2022 hadde «7/8 og 1/8».

**Regelen for ny biomasse**

> «En del av kommunenes andel, tilsvarende 1/8 av midlene som utbetales
> gjennom Havbruksfondet, kommer til fordeling blant kommuner som har
> klarert ny lokalitets-MTB innenfor en toårsperiode. Denne utbetalingen
> er oppad begrenset til 5 millioner kroner per enkeltkommune. Det
> eventuelt overskytende beløpet fordeles på alle kommuner basert på
> andel av lokalitets-MTB.»

> «Ved fordeling av midlene som skal fordeles med utgangspunkt i ny
> lokalitets-MTB, skal Fiskeridirektoratet legge til grunn ny
> lokalitets-MTB i en periode fra 1. september kl 12.00 i oddetallsår, og
> to kalenderår tilbake i tid. Det gjøres ikke fratrekk for
> lokalitets-MTB som har bortfalt i perioden.»

> «Generelt legger departementet opp til at utbetalingene til kommuner i
> partallsår fordeles etter klarert lokalitets-MTB, mens kommuner med ny
> klarert lokalitets-MTB tilgodeses for dette i oddetallsår.»

**«1/8 av midlene» betyr 1/8 av to års utbetalinger.** Det er MÅLT
fra regnearkene og orienteringen. Orienteringen for 2025 avsetter
763 165 711 kr til ny lokalitets-MTB. Utbetalingen i 2024 var
3 756 322 151,20 + 939 080 537,80 = 4 695 402 689,00 kr (regnearket
2024). Utbetalingen i 2025 var 1 409 923 000 kr. Summen delt på 8 er
**763 165 711,1 kr**, altså samme beløp ned til kronen. 2026 er et
partallsår, så utbetalingen i 2026 har ingen nyklarert-del, og hele
kommunenes andel fordeles etter stående MTB.

**Andel av kapasitetssalget som går til fondet**

Fastpris 2024 (`regjeringen-pressemeldinger/2024-06-06`):

> «De samlede inntektene fra fastpristildelingen var 476 millioner
> kroner, hvorav 55 prosent går til kommuner og fylkeskommuner gjennom
> Havbruksfondet.»

Auksjon 2024 (`regjeringen-pressemeldinger/2024-06-25`):

> «55 prosent av inntektene fra auksjonen fordeles til kommuner og
> fylkeskommuner med havbruksvirksomhet gjennom Havbruksfondet. Dette
> kommer i tillegg til 55 prosent av inntektene fra
> fastpristildelingen, samt produksjonsavgiften i sin helhet.»

**Produksjonsavgiften.** Faktaboksen i pressemeldingen 10.11.2025:

> «Havbruksfondet tilføres 55 prosent av inntektene for salg av nye
> oppdrettstillatelser, og produksjonsavgiften på fisk i sin helhet.»

### Hva som mangler, og hvorfor jeg ikke stoppet

Nøkkelen (hvem som får hvilken andel) er entydig: måledato, arter,
lokaliteter, deling og nybiomasseregel står ordrett i én instruks. Det
var det A2 trengte. Hullene gjelder hvor mye penger som kommer inn, og
det berører A7. A7 er et gulv av andre grunner også. Derfor gikk jeg
videre. Mener du at hullene under burde ha stoppet arbeidet, gjelder
A2–A7 med forbeholdet.

1. **55 % står bare i pressemeldinger.** Vedtaket bak andelen
   (budsjettvedtaket i Stortinget) er ikke arkivert. Andelen er oppgitt
   for 2024-runden og gjentatt i en faktaboks 10.11.2025. **Ingen kropp
   fra 2026 oppgir den.** UBELAGT for 2026.
2. **Unntaksvekst er ikke nevnt.** Ingen kropp sier hvor stor andel av
   unntaksveksten som går til fondet. Unntaksveksten selges til samme
   pris som fastpris (270 000 kr/t, pressemeldingen 10.09.2026). UBELAGT.
3. **Bokføringsperioden er borte fra instruksen.** Instruksen av 2022
   sa: «Direktoratet utbetaler midler fra salgs- og auksjonsinntekter
   bokført i perioden fra og med 1. september foregående år til og med
   31. august året for utbetalingen.» Instruksen av 2024 har ikke
   setningen. Ble regelen fra 2022 videreført, havner salget etter
   fristen 28.09.2026 i utbetalingen **2027**, ikke 2026. Det er
   UBELAGT hvilken regel som gjelder nå. Beløpet bestemmes uansett av
   den årlige orienteringen, som ifølge instruksen «fordrer
   budsjettfullmakt fra Stortinget».
4. **«Alminnelige matfisktillatelser og tillatelser til særlige
   formål».** Regelverket sier ikke hvordan en lokalitet med bare
   tillatelser for andre arter skal behandles. I 2025 tok
   Fiskeridirektoratet med to slike lokaliteter og holdt ni andre
   utenfor. Se A2.
