# Måling 11.11.2026 — tidsaksens lag: hvor langt bakover, og hvor tett

Økt 7, Kystloggen 1.0. Spørsmålet: for hvert lag tidsaksen skal bære
(én rad per lokalitet og ISO-uke), hvor langt bakover går det, med
hvilken oppløsning, og hva må til for at laget kan stå i en uke uten å
bli fylt fra en annen?

**Bare måling i dette dokumentet.** Ingen kilde endres, ingenting
publiseres, og ingen tjeneste kalles.

## STOPP-regelen

Skrevet før måleskriptet ble kjørt første gang, 11.11.2026. Målingen
stopper for et lag, og rapporterer i stedet for å bygge det inn i
tidsaksen, hvis

1. **Døra:** et snapshot laget hviler på, ikke kan leses gjennom
   lesedøra (`analyse.kjoringslogg` → `snapshot.versjoner()` →
   `snapshot._les()`).
2. **Proveniensen:** en arkivkropp et lag hviler på alene (sykdom,
   trafikklysets ordlyd), har en annen sha256 enn den R5 og
   `docs/KILDE-TRAFIKKLYSVEDTAK.md` oppgir.
3. **Persondata:** et felt som skulle inn i tidsaksen, bærer navn som
   persondatafilteret ikke kan ta (det arbeider på organisasjonsform,
   ikke på fritekst). Feltet holdes ute og telles.
4. **Eierkoblingen:** et snapshot fra før 17.08.2026 bærer en kobling
   lokalitet–tillatelse–innehaver. Da er premisset i beslutningen
   (M25) feil, og det avgjøres ikke her.
5. **Trafikklyset:** 2026-forskriften bærer ikke setningen om at
   tillatelser i øvrige produksjonsområder «kan utnyttes 100 prosent»
   ordrett. Da har de sju cellene ingen ordlyd å vise.

Et hull i en ukentlig serie (en uke uten snapshot mellom første og
siste) stopper ikke: det er nettopp det tidsaksen skal vise som tomt.
Det telles.

**Utfall:** ingen av de fem er utløst. Alle 14 kildene leses gjennom
døra (F1.1). Mattilsynet-kroppen har R5s sha256 (F9.1), og
2026-forskriften har KILDE-TRAFIKKLYSVEDTAKs (F6.2) og bærer setningen
ordrett. Ingen akvakultur- eller eierskapssnapshot er datert før
17.08.2026 (F2.2). Ingen felt som går inn i tidsaksen er fritekst med
navn: lokalitets- og selskapsnavn tas ikke med (F12.2).

## Datagrunnlag

| ledd | verdi |
|---|---|
| kode | `havbruk-radar` `c415868` (origin/main ved start) |
| data | `havbruk-radar-data` `823b8f53510dab69ca7d34db70967172e7364b75` (origin/main etter `git pull` 11.11.2026) |
| skript | `analyse/tidsakse/m1_lag.py`, `HAVBRUK_DATA_DIR=../havbruk-radar-data/data .venv/bin/python analyse/tidsakse/m1_lag.py` |
| utskrift | `analyse/tidsakse/m1_lag.txt`, uendret; kjørt to ganger med samme sha256 `b29fdfaeef1a42bcefa9a93f0db1c21fbc75f3187ea1828f3ad7957486b769d1` |

Snapshotene er lest gjennom `analyse.kjoringslogg` (versjonsvalg
`alle`, og den gjeldende versjonen valgt som `snapshot.gjeldende()`
gjør). Kjøringsloggen skrives til `analyse/ut/`, som ikke committes;
fillistene over står i stedet med sha256 i F1.1. Kroppene i
`data/arkiv/` er lest utpakket, og sha256 er over den utpakkede
kroppen. «sha256 over fillista» er over linjene
`raw/<kilde>/<fil>\t<sha256 av fila>\n`, sortert på filnavn.

**Merkene:** MÅLT = holdt mot en arkivert kropp, sha256 oppgitt. MÅLBAR =
lest i et snapshot gjennom døra, eller regnet ut av målte tall, men ikke
selv holdt mot en kropp. EKSTERN = hviler på noe som ikke er i arkivet.
UBELAGT = ingen kropp sier det. Hvert funn har én linje «Feil hvis».

## De tre sterkeste funnene

**1. Før uke 34/2026 har tidsaksen fire lag, ikke tretten (F2.1, F2.2,
F3.1, F5.2).** Registeret, tillatelsene, eieren, PO, kommune,
reguleringsområdet og trafikklyset finnes bare fra
akvakultursnapshotet 17.08.2026 og eierskapssnapshotet 02.09.2026.
Bakover er det bare lus og sjøtemperatur (fra 2012), sykdom (fra uke
48/2024) og biomasselagets eldre påstander. Det er M25s 99,4 %
look-ahead sett fra den andre siden: en kobling som ikke fantes, kan
ikke stå i en uke den ikke fantes.
*Hvorfor sterkest:* det er fillista og datoene på snapshotene, og
arkivet har ingen eldre kropp for noen av de to kildene.

**2. Parene P4–P6 i R2 kan ikke bli konflikter i tidsaksen (F12.1).**
Lusetall- og sjøtemperatursnapshotene bærer verken koordinater,
kommunenummer eller PO: hvert av de feltene har én eier i snapshotene,
akvakultur. R2 fant dem bare i kroppene, og fant ingen uenighet der
(R2 F4.1). Konfliktene tidsaksen kan føre, er P1, P2 og P3, og
sykdom mot registeret (F9.2).
*Hvorfor sterkt:* det er feltlistene, ikke en tolkning.

**3. Fire lokaliteter med åpen PD-sak forsvant fra BarentsWatch etter
uke 10/2026 og står ikke i registeret (F9.2).** 24456, 24696, 30437 og
31959 står i lusetallkroppen for 02.03.2026, ikke i den for
09.03.2026, og ikke i akvakulturkroppen for 09.11.2026.
*Hvorfor sterkt:* tre kropper med sha256, og det er cellene
beslutningen sier skal stå som konflikt.

*Svakere, og hvorfor:* biomasselaget er tett i bare tre månedsslutter
(F7.1), unntaksvekst har ingen vedtaksdato (F10.1), og auksjon og
havbruksfond er ikke lag per lokalitet (F11.1, F11.2).

---

## 1. Døra

**F1.1 — Alle 14 kildene leses gjennom døra, og ingen versjon er merket
ufullstendig. MÅLBAR** (utskriften, punkt 1):

```
kilde | filer datoer | første siste | median dager mellom datoer | ufullstendige | entity_type | entiteter i siste | sha256 over fillista
akvakultur | 19 13 | 2026-08-17 2026-11-09 | 7 | 0 | lokalitet | 1785 | 5fcbb3b7c9f1ff20869689c6c292ca347704c274e2b98d97bccfdb9287bc2b30
eierskap | 10 10 | 2026-09-02 2026-11-09 | 7 | 0 | tillatelse | 2953 | c928de7926efb10ad0c40e77a371a82afed37a1f8e4ba2f7cd837255b977299c
eierskap_historikk | 63 21 | 2006-12-31 2026-12-31 | 365 | 0 | overforing | 91 | 3adb3a4522a27da3691d9f610e600748173280e067189a55cbf71db1f748d498
enhetsregisteret | 20 14 | 2026-08-16 2026-11-09 | 7 | 0 | selskap | 1757 | 3e3e1ce2efe632d0706fbc5007e696676f6c2a92fb5944a491676c1579af5715
enhetsregisteret_oppslag | 3 3 | 2026-11-04 2026-11-11 | 6 | 0 | selskap | 411 | cda394e3b379c7d78bd5b81b9ae1cecbee1b825f94e59b9154c08370e0524dfc
biomasselag | 10 10 | 2026-09-10 2026-11-09 | 7 | 0 | lokalitet | 1118 | b2cf637995a354319a1bfb9145205e46a6efafb490c2ba3213b3507598c5feca
biomasse | 190 106 | 2017-10-31 2026-07-31 | 31 | 0 | produksjonsomraade | 14 | 97ee14d32778fca5b3894d47940412321dabd86199c37526261686e985fcff11
lusetall | 772 772 | 2012-01-02 2026-10-12 | 7 | 0 | lokalitet | 1779 | 095a1741b4680cb492b9a0cd5065f35f8cfeeb70c14e2bd9955e193a6c3e9c56
sjotemperatur | 1539 772 | 2012-01-02 2026-10-12 | 7 | 0 | lokalitet | 1060 | 698a05cf47b745348b5331971c85643f1f869e90eb6618ace2fda492db982190
trafikklysvedtak | 7 5 | 2018-12-31 2026-12-31 | 731 | 0 | produksjonsomraade | 6 | 0aac79cf09cf7cd0c2a87c2df4740b6212619992ddcc27625b14c50bd189f8d9
ekspertgruppen | 24 9 | 2016-12-31 2025-12-31 | 365 | 0 | produksjonsomraade | 13 | 4abf68f1cdf9dab9a87cc90a03cb8de22b172015b05191f81721416250465168
reguleringsomraader | 1 1 | 2026-06-29 2026-06-29 | 0 | 0 | reguleringsomraade | 28 | fb1fa1c105b2ec365202f15fa80c91694134f1c13d01afbf6ec61945bea6f71f
unntaksvekst | 5 5 | 2026-10-12 2026-11-09 | 7 | 0 | soknad_lokalitet | 84 | 1608e0f1cb6e7e8ec01b4c0957f1289ee5092dfdf70a376c7e8f54f87f354e58
romming | 21 21 | 2016-12-31 2026-12-31 | 250 | 0 | romming | 57 | 22693e66d681622377ce61dd9dffdd8d13b03999582660b17cf8e1ce88684b0d
```

De ukentlige seriene, og ukene uten snapshot mellom første og siste:

```
akvakultur: uker 13 (2026-W34..2026-W46), med snapshot 13, uten 0: -; uker med flere datoer: -
eierskap: uker 11 (2026-W36..2026-W46), med snapshot 10, uten 1: 2026-W37; uker med flere datoer: -
enhetsregisteret: uker 14 (2026-W33..2026-W46), med snapshot 14, uten 0: -; uker med flere datoer: -
biomasselag: uker 10 (2026-W37..2026-W46), med snapshot 10, uten 0: -; uker med flere datoer: -
lusetall: uker 772 (2012-W01..2026-W42), med snapshot 772, uten 0: -; uker med flere datoer: -
sjotemperatur: uker 772 (2012-W01..2026-W42), med snapshot 772, uten 0: -; uker med flere datoer: -
unntaksvekst: uker 5 (2026-W42..2026-W46), med snapshot 5, uten 0: -; uker med flere datoer: -
```

*Feil hvis:* en av filene i `raw/<kilde>/` ikke kan leses av
`snapshot.versjoner()`, eller `raw/eierskap/` har en fil for uke 37.

## 2. Registerets tilstand: kapasitet, status, arter, koordinater

**F2.1 — Registeret finnes i 13 uker, uke 34–46/2026, uten hull. MÅLBAR.**
Hver uke har 1779–1785 lokaliteter, alle med kapasitet, koordinater og
kommunenummer, og 968–970 med PO (bare lokaliteter med
matfisktillatelse har PO hos Fiskeridirektoratet, R2 F4.3). Alle har
`versjon_status` APPROVED. Utskriften, punkt 2:

```
dato uke | lokaliteter | med kapasitet | med koordinater | med PO | med kommunenummer | med tillatelser | versjon_status (topp)
2026-08-17 2026-W34 | 1779 | 1779 | 1779 | 970 | 1779 | 1777 | [('APPROVED', 1779)]
2026-10-12 2026-W42 | 1780 | 1780 | 1780 | 968 | 1780 | 1778 | [('APPROVED', 1780)]
2026-11-09 2026-W46 | 1785 | 1785 | 1785 | 969 | 1785 | 1783 | [('APPROVED', 1785)]
```

(Tre av 13 linjer; alle står i utskriften.) Ukene før 34 har ingen
registertilstand i tidsaksen. Registerets egne datoer
(`forste_klarering`, `versjon_gyldig_fra`) er påstander om fortiden som
står på raden for uka de ble sett, ikke verdier som kan flyttes bakover.
*Feil hvis:* `raw/akvakultur/` har en fil datert før 2026-08-17.

**F2.2 — Ingen kobling lokalitet–tillatelse–innehaver før 17.08.2026.
MÅLBAR.** Første `akvakultur.tillatelser` er i snapshotet 2026-08-17
(uke 34), første `eierskap.eier_orgnr` i 2026-09-02 (uke 36). Ingen av
de to kildene har et snapshot fra før 17.08, og arkivet har ingen eldre
kropp: første er `akvakultur/2026-08-17.2.json.gz` og
`eierskap/2026-09-02.json.gz`. Innehaveren står altså fra uke 36, og
tillatelsene på lokaliteten fra uke 34.
*Feil hvis:* `arkiv/akvakultur/` eller `arkiv/eierskap/` har en kropp
datert før 2026-08-17.

## 3. Tillatelser, MTB og eier

**F3.1 — Eierskap finnes i 10 uker: 36 og 38–46/2026. Uke 37 mangler.
MÅLBAR.** 2944–2953 tillatelser, 2903–2913 med lokaliteter, 1715–1720
lokaliteter koblet, 478–482 ulike innehavere (utskriften, punkt 3). Uka
uten snapshot er tom for eierleddet, også om uka før og etter har samme
eier.
*Feil hvis:* `raw/eierskap/` har en fil datert 2026-09-07–2026-09-13.

**F3.2 — MTB står i tonn for 2070–2079 av tillatelsene. MÅLBAR.** Resten
har dekar (`DA`, 536–538), stykk, kilo, m², m³ eller liter, og 87–88 er
årsrammer (`SUM/YEAR`), ikke MTK. En sum av tillatelsenes MTB på en
lokalitet er derfor bare meningsfull per enhet, og den er regnet, ikke
oppgitt (`paastand.REGNET`). En tillatelse kan stå på flere
lokaliteter, så summene over lokaliteter er ikke en sum av MTB.
*Feil hvis:* snapshotet 2026-11-09 har et annet antall tillatelser med
`kapasitet_enhet` TN enn 2079.

**F3.3 — Eierskapshistorikken har 2607 overføringer,
journalført 27.02.2006–17.08.2026. MÅLBAR** (21 årsfiler, 63 versjoner).
Den sier når en tillatelse skiftet innehaver, og gir datoen til en
eierskiftehendelse. Den brukes ikke til å fylle eierkoblingen bakover:
det er M25s look-ahead, og beslutningen står.
*Feil hvis:* de gjeldende versjonene av de 21 årsfilene har et annet
antall `journal_dato` enn 2607.

## 4. Selskapsleddet

**F4.1 — Ingen snapshot bærer en overordnet enhet. MÅLBAR.** De 14
datoene i `enhetsregisteret` har til sammen 32 felt, og det eneste som
handler om konsern er `er_i_konsern` (sant/usant). Brreg oppgir
`overordnetEnhet` for underenheter, og kilden henter hovedenheter. Av
480 innehavere i siste eierskapssnapshot står 359 i siste
enhetsregistersnapshot; 121 er utenfor vårt utvalg (som R2 F2.2).
Selskapsleddet i tidsaksen er derfor orgnr, og det Brreg sier om
enheten, uten en overordnet enhet.
*Feil hvis:* en versjon av `raw/enhetsregisteret/` har et felt med
«overordnet» i navnet.

## 5. Reguleringsområde, PO og kommune

**F5.1 — Ett reguleringsdatasett: `regomr_v3`, status «forslag», 28
områder, utgitt 29.06.2026. MÅLBAR.** Punkt i polygon
(`sources.reguleringsomraader.inneholder`) med koordinatene i siste
akvakultursnapshot: 1757 av 1785 lokaliteter ligger i nøyaktig ett
område, 28 i ingen, ingen i to. Medlemskapet er regnet, ikke oppgitt,
og det gjelder `regomr_v3`, som ikke endrer seg; en ny versjon er et nytt
datasett.
*Feil hvis:* en lokalitet i siste akvakultursnapshot ligger i to av de
28 polygonene.

**F5.2 — PO og kommune finnes bare i akvakultur. MÅLBAR.** Feltene i
`lusetall` og `sjotemperatur` (utskriften, punkt 13) har verken PO,
kommunenummer eller koordinater. PO og kommune står derfor fra uke 34,
og trafikklyset, som henger på PO, likeså.
*Feil hvis:* `raw/lusetall/2026-10-12.parquet` har et felt med
kommune eller PO.

## 6. Trafikklys

**F6.1 — Fem runder, og i 2026 har sju av tretten PO ingen farge.
MÅLBAR:**

```
   runde 2018 | published_at 2017-12-20T12:00:00+00:00 | PO med farge 8: 1=gronn, 7=gronn, 8=gronn, 9=gronn, 10=gronn, 11=gronn, 12=gronn, 13=gronn
   runde 2020 | published_at 2020-02-04T12:00:00+00:00 | PO med farge 11: 1=gronn, 2=gronn, 4=rod, 5=rod, 6=gronn, 7=gronn, 8=gronn, 9=gronn, 11=gronn, 12=gronn, 13=gronn
   runde 2020 | published_at 2022-06-07T12:00:00+00:00 | PO med farge 3: 3=gul, 4=rod, 5=rod
   runde 2022 | published_at 2022-06-07T12:00:00+00:00 | PO med farge 11: 1=gronn, 3=rod, 4=rod, 5=gul, 6=gronn, 8=gronn, 9=gronn, 10=gronn, 11=gronn, 12=gronn, 13=gronn
   runde 2022 | published_at 2024-03-22T12:00:00+00:00 | PO med farge 3: 3=rod, 4=rod, 5=gul
   runde 2024 | published_at 2024-03-22T12:00:00+00:00 | PO med farge 9: 1=gronn, 3=rod, 4=rod, 5=gul, 9=gronn, 10=gronn, 11=gronn, 12=gronn, 13=gronn
   runde 2026 | published_at 2026-08-20T12:00:00+00:00 | PO med farge 6: 1=gronn, 3=rod, 4=gul, 5=gul, 12=gronn, 13=gronn
```

`published_at` er forskriftens ikrafttredelse. En nyere forskrift
uttaler seg om eldre runder i § 4-tabellen (versjon 2 av 2020 og 2022);
det er ikke en revisjon i 1b-5-forstand (KILDE-TRAFIKKLYSVEDTAK).
*Feil hvis:* snapshotet for 2026-12-31 har `farge` for PO 2, 6, 7, 8, 9,
10 eller 11.

**F6.2 — Ordlyden for de sju står ordrett, én gang, i § 4 av
FOR-2026-08-20-1764. MÅLT** mot `trafikklysvedtak/2026-12-31.bin.gz`
(sha256 `08b6090d993b96444ba54043079382de2a25750f571b7b98414158bc7abc4cd8`,
som KILDE-TRAFIKKLYSVEDTAK oppgir), lest med kildens egne
`_tekst()`, `_forskriftstekst()` og `_paragraf(…, "4", "5")`:

```
   § 4 har setningen ordrett 1 gang(er): Tillatelser hjemmehørende i øvrige produksjonsområder kan utnyttes 100 prosent.
```

Det er kapasitetsjusteringen forskriften gir de sju, og den er det
tidsaksen viser for dem, med forskriften som kilde. Ingen farge.
*Feil hvis:* § 4 i kroppen har setningen et annet antall ganger enn én.

**F6.3 — Registeret oppgir «GUL» for PO 2 og 6–11. MÅLBAR**
(`prodomraade_status` i siste akvakultursnapshot, utskriften punkt 2).
Det er registerets ord, ikke vedtakets, og beslutningen for økta er at
cellene ikke får farge. Tidsaksen tar derfor ikke med
`prodomraade_status`: en farge i en annen kolonne på samme rad er
fortsatt en farge. Heine avgjør om registerets ord skal stå for seg.
*Feil hvis:* en lokalitet med `prodomraade_kode` 2 i siste
akvakultursnapshot har en annen `prodomraade_status` enn GUL.

**F6.4 — Runde 2026 gjelder alle ukene med PO. MÅLBAR.** Forskriften
trådte i kraft torsdag 20.08.2026 (uke 34), og status leses ved
søndagens slutt, som for sykdom (R5 T3). PO finnes fra uke 34 (F5.2).
Trafikklyset står derfor i uke 34–46/2026 og er tomt før.
`observed_at` er rundens etikett (årets siste dag,
`trafikklysvedtak.siste_dag()`); en runde gjelder fra
`published_at` og høyst til den etiketten.
*Feil hvis:* `published_at` for runde 2026 er en annen enn 2026-08-20.

## 7. Biomasselaget

**F7.1 — Tett i tre månedsslutter, spredt bakover til 2005. MÅLBAR.**
Ti snapshots (uke 37–46) gir hver lokalitets SISTE rapport. Over alle
ti er det 2233 påstander (lokalitet, månedsslutt) om 114 månedsslutter,
30.04.2005–31.10.2026; 2210 fra 02.01.2012, 23 før. Bare tre
månedsslutter har minst 100 lokaliteter:

```
   månedsslutter med minst 100 lokaliteter: [('2026-07-31', 408), ('2026-08-31', 684), ('2026-09-30', 694)]
```

En påstand gjelder månedsslutten i `siste_rapport` (`paastand.py`,
periode dag) og står i ISO-uka som inneholder den dagen. Ukene mellom
er tomme: samme rapport sett på nytt er ingen ny observasjon (R2,
«Varig»). De 23 fra før 2012 ligger utenfor aksen. «Nei» er en
absorberende tilstand (KILDE-BIOMASSELAG): en gammel «Nei» betyr «ikke
meldt fisk siden», ikke «tom da».
*Feil hvis:* de ti gjeldende biomasselagsnapshotene har et annet antall
ulike par (lokalitet, `siste_rapport`) enn 2233.

## 8. Lus, brakklegging, behandling og sjøtemperatur

**F8.1 — 772 uker, 2012-01-02–2026-10-12, uten hull. MÅLT** mot de 772
kroppene i `arkiv/lusetall/` (sha256 over lista «sti<TAB>sha256\n»
`b7c32ebd92b8c10ebf184cc39933e8a1e51ff3fca6af517a672fa179ebcd144d`), og
MÅLBAR i snapshotene: samme 772 uker i `lusetall` og `sjotemperatur`
(1539 filer, re-parse-versjonene). 2711 lokaliteter står i minst én uke.
Uke 43–46/2026 er ikke hentet ennå (fire ukers etterslep, KILDE-LUSETALL).
*Feil hvis:* `arkiv/lusetall/` har et annet antall `.json.gz` enn 772,
eller to av dem gjelder samme ISO-uke.

**F8.2 — Behandling lever 2012-01-02–2023-12-25 (626 uker). MÅLBAR**
med R8s regel (et flagg er dødt i et strekk på over 13 uker uten én
`True` i universet) og `config.yml` `dodt_fra`:

```
   har_mekanisk_fjerning: første True 2012-01-02, siste True 2026-10-12; døde strekk > 13: -; lever etter regelen 772 uker (2012-01-02..2026-10-12); med dodt_fra 772 uker (2012-01-02..2026-10-12)
   har_medikamentell_behandling: første True 2012-01-02, siste True 2024-11-11; døde strekk > 13: [('2024-01-01', '2024-11-04', 45), ('2024-11-18', '2026-10-12', 100)]; lever etter regelen 627 uker (2012-01-02..2024-11-11); med dodt_fra 626 uker (2012-01-02..2023-12-25)
   har_rensefisk: første True 2012-01-02, siste True 2023-04-17; døde strekk > 13: [('2023-04-24', '2026-10-12', 182)]; lever etter regelen 590 uker (2012-01-02..2023-04-17); med dodt_fra 590 uker (2012-01-02..2023-04-17)
```

R8s regel alene gir én uke til, 2024-11-11 (R8 F2.2: én lokalitet med
flagget den uka). `dodt_fra` er repoets egen kvittering for dødsfallet
(«et unntak, ikke liv»), og oppdraget sier det samme: behandling lever
2012–2023 og er tom etter, ikke «nei». Tidsaksen bruker begge.
*Feil hvis:* et lusetallsnapshot etter 2024-11-11 har
`har_medikamentell_behandling` True for en lokalitet i universet.

## 9. Sykdom (R5)

**F9.1 — Én kropp, 214 tilfeller, og hel fra uke 48/2024. MÅLT** mot
`maling-ilapd/2026-11-04.json.gz` (sha256
`890117f9a349175a61885ecd5505350b99fc57ef52b2907ecd5cee9f63a3407a`, lik
R5), hentet 04.11.2026 01:51:23 UTC (loggen `2026-11-04.i2.logg.json`):

```
   tidligste opprettet 2024-11-26T12:44:42.031588Z (2024-W48); lokaliteter med gyldig ILA/PD 157; av dem i noen lusetalluke 157
```

52 gyldige ILA- og 131 gyldige PD-tilfeller. Status per uke regnes etter
R5 tillegg 1.1 fra uke 48/2024 til uke 44/2026, siste hele uke før
hentingen; uke 45 bare «per 04.11.2026» (R5 T4). Ukene før er tomme
(beslutningen). Alle 157 lokalitetene står i minst én lusetalluke.
*Feil hvis:* kroppen har et `opprettet` før 2024-11-26, eller et annet
antall gyldige PD-tilfeller enn 131.

**F9.2 — De fire PD-lokalitetene forsvant fra BarentsWatch etter
02.03.2026. MÅLT:**

```
   lusetall/2026-03-02.json.gz sha256 cfb15ca9c0837c023d0a99cfc02567fdfba4cb94ed2af9306efeb9aea0540d92: lokaliteter 1775; av de fire med åpen PD: ['24456', '24696', '30437', '31959']
   lusetall/2026-03-09.json.gz sha256 af701b24e0ef3b82183aa9b9db781cbd70b0cabac0a17f610d64fce120739ea3: lokaliteter 1771; av de fire med åpen PD: -
   akvakultur/2026-11-09.json.gz sha256 4d3c2335ec3a4030f25b8a275b8cdea9ee4208bf1553a3c95d3cf6de7707de61: lokaliteter 1785; av de fire: -
```

Mattilsynet fører åpne PD-saker på dem (R5 F6.1). Fra uke 11/2026 sier
begge registrene at lokaliteten ikke finnes, mens Mattilsynet sier at
saken er åpen: det er konflikten beslutningen sier skal stå. Før uke
11 er de vanlige lokaliteter med PD.
*Feil hvis:* en av de fire står i `lusetall/2026-03-09.json.gz`.

## 10. Unntaksvekst

**F10.1 — Fem uker, samme tall hver uke, og ingen vedtaksdato. MÅLBAR.**
84 søknadslokaliteter, 81 med lokalitetsnummer (60 ulike); 69 godkjent,
15 avslag; koblingen til lokaliteten er entydig for 70, flertydig for 3
og usikker for 11 (utskriften, punkt 10). Snapshotet har ingen dato for
vedtaket, så laget er «status som sett i uka», uke 42–46/2026, og
koblingen følger med på hver rad.
*Feil hvis:* et av de fem snapshotene har et annet antall rader med
`resultat` Godkjent enn 69.

## 11. Lagene som bare er arkivkropper

**F11.1 — Auksjon: 110 kropper, ingen kilde, ingen lokalitet. MÅLBAR**
(fillista). Sidene for rundene 2018–2024 og indekssiden, hentet daglig
fra 14.09.2026. `arkiver_auksjon.py` sier selv at formatet på
2026-resultatet ikke er sett, og at prisene per PO trekkes ut av en
kilde som ikke er skrevet. Auksjonen er per PO og runde, ikke per
lokalitet, og står ikke i tidsaksen.
*Feil hvis:* `sources/` har en modul som parser auksjonskroppene.

**F11.2 — Havbruksfondet: én måledato, 01.09.2026. MÅLBAR.**
`havbruksfond.py` regner nøkkelen per kommune av akvakultursnapshotene
31.08 og 07.09, eierskapskroppen 02.09 og Fiskeridirektoratets regneark.
Per lokalitet er det ett svar, for uke 36/2026: med i nøkkelen eller
ikke, og med hvilken vekt. 21 kropper i `havbruksfondet/` er sidene og
regnearkene, ikke lokalitetsdata.
*Feil hvis:* `havbruksfond.MAALEDATO` er en annen enn 2026-09-01.

**F11.3 — Luseinnkomsten er kropper, ikke snapshots. MÅLBAR**
(fangstloggene):

```
   lusetall-innkomst: uker i fangstloggene 6 (2026-10-05..2026-11-09); hentinger 70; første henting 2026-11-02T19:14:46+00:00, siste 2026-11-11T12:12:10+00:00
   lusetall-innkomst-v2: uker i fangstloggene 6 (2026-10-05..2026-11-09); hentinger 55; første henting 2026-11-03T19:44:22+00:00, siste 2026-11-11T12:11:58+00:00
```

Kroppene for uke 37–40/2026 og tre eldre uker er fra målingen 02.11
(MALING-LUSEINNKOMST). Innkomsten viser uke N til N−4 mens
BarentsWatch fortsatt fyller den, og gir fasit for ingen uke før N−4 er
hentet av lusetall. v2 bærer sykdom som Mattilsynets kopi (R5 F4.5).
*Feil hvis:* en fangstlogg har en uke før 2026-10-05.

**F11.4 — De nye kildene fra MALING-NYE-KILDER. MÅLBAR** (fillista):
flatelaget 7 kropper (03.–11.11.2026), søknadslagene 6 (bare måling:
søkers navn uten organisasjonsform, regel 3), og målekroppene fra 03.11
(47). Ingen av dem går bakover: flatelaget kan ikke spørres om fortiden
(MALING-NYE-KILDER F1.2).
*Feil hvis:* `arkiv/akvakultur-flater/` har en kropp datert før
2026-11-03.

## 12. Parene i R2, og navnene

**F12.1 — P1–P3 har begge sider i snapshotene, P4–P6 har det ikke.
MÅLBAR** (utskriften, punkt 13):

```
   lusetall: brakklagt, er_landbasert, er_slaktemerd, har_ila, har_laksefisk, har_medikamentell_behandling, har_mekanisk_fjerning, har_pd, har_rensefisk, lus_er_rapportert, voksne_hunnlus
   sjotemperatur: lusegrense, sjotemperatur, temperatur_er_rapportert
```

Det er med vilje: `sources/sjotemperatur.py` lar akvakultur eie navn,
kommune, koordinater og PO, fordi to kilder med samme felt legger igjen
en permanent falsk forskjell. P4–P6 kan bare prøves mot kroppene, og R2
F4.1 fant 0 uenige der, koblet på samme uke.
*Feil hvis:* et snapshot i `raw/lusetall/` har feltet `kommunenummer`.

**F12.2 — Tidsaksen trenger ingen navn. MÅLBAR.** Lokaliteter står
med nummer, innehavere og selskaper med orgnr, unntaksvekstsøkeren med
orgnr. P1 sammenligner navn (eierskap mot Enhetsregisteret), men bare
mens tidsaksen bygges; resultatet er «navn ulikt» eller «form ulik»,
ikke navnet. Søkernavnet i unntaksvekst og `lokalitetsnavn` hos
Mattilsynet tas ikke med.
*Feil hvis:* et felt tidsaksen tar inn, er fritekst.

## Hva dette betyr for tidsaksen

| lag | kilde | oppløsning | første uke | siste uke | plassert på |
|---|---|---|---|---|---|
| registerets tilstand | akvakultur | uke | 2026-W34 | 2026-W46 | snapshotets uke |
| PO, kommune | akvakultur | uke | 2026-W34 | 2026-W46 | snapshotets uke |
| reguleringsområde | reguleringsomraader + akvakultur | regnet per uke | 2026-W34 | 2026-W46 | koordinatenes uke |
| trafikklys | trafikklysvedtak | runde | 2026-W34 | 2026-W46 | rundens gyldighet, via PO |
| tillatelser, MTB, eier | eierskap | uke | 2026-W36 | 2026-W46 | snapshotets uke (W37 tom) |
| selskap | enhetsregisteret | uke | 2026-W36 | 2026-W46 | via eierens orgnr |
| biomasselaget | biomasselag | måned | 2012 | 2026-W44 | uka med månedsslutten |
| lus, brakk | lusetall | uke | 2012-W01 | 2026-W42 | uka den gjelder |
| behandling | lusetall | uke | 2012-W01 | 2023-W52 | uka den gjelder, tom etter |
| sjøtemperatur, lusegrense | sjotemperatur | uke | 2012-W01 | 2026-W42 | uka den gjelder |
| sykdom | Mattilsynet (kropp) | uke | 2024-W48 | 2026-W45 | status ved søndag; W45 per hentedato |
| unntaksvekst | unntaksvekst | uke | 2026-W42 | 2026-W46 | snapshotets uke |
| havbruksfond | havbruksfond.py | måledato | 2026-W36 | 2026-W36 | uka med 01.09.2026 |
| luseinnkomst | lusetall-innkomst (kropper) | henting | — | — | ikke i tidsaksen, se under |
| auksjon | arkivkropper | runde, PO | — | — | ikke i tidsaksen |

Ingen celle fylles fra en annen uke. En uke uten laget er tom, ikke
null og ikke forrige ukes verdi.

## Hva som mangler, og hvorfor jeg ikke stoppet

- **Luseinnkomsten** er kropper med egne fangstlogger, ikke snapshots,
  og BarentsWatch overskriver uka til N−4. Den gir hendelsesvarselet
  (økt 10) uke N−1, som lusetall først har fire uker senere. Den står
  ikke i tidsaksen i denne økta; et lag av den er et eget valg om
  hvilken henting av en uke som gjelder.
- **Auksjonen** har ingen kilde å lese den med, og er ikke per
  lokalitet (F11.1).
- **Overordnet enhet** finnes ikke i noen snapshot (F4.1). Ingenting er
  hentet for å skaffe den.
- **P4–P6** kan ikke prøves i snapshotene (F12.1). R2 har prøvd dem i
  kroppene.
- **Hvorfor de fire PD-lokalitetene forsvant**, sier ingen kropp
  (UBELAGT, som i R5).

---

## Etterskrift 11.11.2026: dekningen i den bygde tidsaksen

Teksten over er ikke endret. Tidsaksen er bygget av `tidsakse.py`
(commit `c92b1b4`) mot samme datarepo (`823b8f53…`), og dekningen per
lag og uke er telt i den med `analyse/tidsakse/m2_dekning.py`.
Utskriften står uendret i `m2_dekning.txt` (sha256
`828c8c9f4980beb35aeba429b08e84b0d3c9f4cf3b46fa03a3a08fb2284d8b8d`), og
hele tabellen, én rad per uke og én kolonne per lag, i `m2_dekning.tsv`
(`dbc5339eead08ed4bf675e9e1500ce082f01fad474386124f266f8bdca1dd1dc`).
Begge er kjørt to ganger med samme sha256. Alt i etterskriften er
MÅLBAR: regnet av snapshotene gjennom døra og de to kroppene, ikke selv
holdt mot en kropp. En celle telles når `<lag>__kilde` er satt.

**Filene:**

```
   tidsakse.parquet sha256 29e2131c524c5d2d88d342ac465dde0f6f04f88ee58b9ca9c9122d93b845e7bf byte 2257512
   hendelser.parquet sha256 7b30406553d493a3d5403984bb2ec89d685cca8c7d9f24a743647f80f6f44115 byte 118622
   konflikter.parquet sha256 7550793b7886d6867235bcf77f24d616542936e03d16f86149959e2d617f1a51 byte 6008
   tidsakse.parquet: 2107616 rader = 2716 lokaliteter × 776 uker (2012-W01..2026-W46), 104 kolonner
   hendelser.parquet: 46596 rader; konflikter.parquet: 231 rader
```

**Per lag:**

```
lag | første uke | siste uke | uker med celle | uker uten celle mellom første og siste | celler | median per uke med celle | høyest
register | 2026-W34 | 2026-W46 | 13 | 0 | 23158 | 1782 | 1785
sted | 2026-W34 | 2026-W46 | 13 | 0 | 23158 | 1782 | 1785
regomr | 2026-W34 | 2026-W46 | 13 | 0 | 23158 | 1782 | 1785
trafikklys | 2026-W34 | 2026-W46 | 13 | 0 | 12597 | 969 | 970
eierskap | 2026-W36 | 2026-W46 | 10 | 1: 2026-W37 | 17172 | 1717 | 1720
selskap | 2026-W36 | 2026-W46 | 10 | 1: 2026-W37 | 15504 | 1550 | 1552
biomasselag | 2012-W13 | 2026-W44 | 96 | 666 | 2210 | 2 | 694
lus | 2012-W01 | 2026-W42 | 772 | 0 | 1336229 | 1715 | 1999
sjo | 2012-W01 | 2026-W42 | 772 | 0 | 827876 | 1071 | 1114
stripe | 2012-W01 | 2026-W42 | 772 | 0 | 1342612 | 1720 | 2004
sykdom | 2024-W48 | 2026-W45 | 102 | 0 | 180799 | 1774 | 1788
unntaksvekst | 2026-W42 | 2026-W46 | 5 | 0 | 300 | 60 | 60
havbruksfond | 2026-W36 | 2026-W36 | 1 | 0 | 1065 | 1065 | 1065
```

Hvert lag står i ukene tabellen «Hva dette betyr for tidsaksen» over
sa. Uke 37 er tom for eier og selskap, og biomasselaget står i 96 uker
med en månedsslutt og er tomt i de 666 mellom. Selskapsleddet har færre
celler enn eierleddet fordi 121 innehavere er utenfor vårt utvalg av
Enhetsregisteret (F4.1). Sykdom teller også «ingen aktiv sak», og
står derfor for hver lokalitet et register har i uka.

**Uke for uke fra uke 33/2026**, der de fleste lagene begynner:

```
uke | register | sted | regomr | trafikklys | eierskap | selskap | biomasselag | lus | sjo | stripe | sykdom | unntaksvekst | havbruksfond | konflikt
2026-W33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1777 | 1066 | 1778 | 1781 | 0 | 0 | 4
2026-W34 | 1779 | 1779 | 1779 | 970 | 0 | 0 | 0 | 1777 | 1066 | 1778 | 1783 | 0 | 0 | 4
2026-W35 | 1779 | 1779 | 1779 | 970 | 0 | 0 | 0 | 1777 | 1066 | 1779 | 1783 | 0 | 0 | 4
2026-W36 | 1779 | 1779 | 1779 | 969 | 1715 | 1550 | 684 | 1777 | 1066 | 1779 | 1784 | 0 | 1065 | 31
2026-W37 | 1779 | 1779 | 1779 | 969 | 0 | 0 | 0 | 1776 | 1063 | 1780 | 1783 | 0 | 0 | 4
2026-W38 | 1782 | 1782 | 1782 | 969 | 1717 | 1551 | 0 | 1778 | 1062 | 1781 | 1786 | 0 | 0 | 4
2026-W39 | 1782 | 1782 | 1782 | 969 | 1717 | 1551 | 0 | 1779 | 1062 | 1782 | 1786 | 0 | 0 | 4
2026-W40 | 1783 | 1783 | 1783 | 969 | 1717 | 1552 | 694 | 1780 | 1062 | 1782 | 1787 | 0 | 0 | 20
2026-W41 | 1782 | 1782 | 1782 | 969 | 1717 | 1550 | 0 | 1779 | 1060 | 1782 | 1786 | 0 | 0 | 4
2026-W42 | 1780 | 1780 | 1780 | 968 | 1716 | 1550 | 0 | 1779 | 1060 | 1781 | 1785 | 60 | 0 | 5
2026-W43 | 1781 | 1781 | 1781 | 968 | 1717 | 1550 | 0 | 0 | 0 | 0 | 1785 | 60 | 0 | 24
2026-W44 | 1783 | 1783 | 1783 | 969 | 1719 | 1551 | 17 | 0 | 0 | 0 | 1787 | 60 | 0 | 5
2026-W45 | 1784 | 1784 | 1784 | 969 | 1717 | 1549 | 0 | 0 | 0 | 0 | 1788 | 60 | 0 | 4
2026-W46 | 1785 | 1785 | 1785 | 969 | 1720 | 1550 | 0 | 0 | 0 | 0 | 0 | 60 | 0 | 0
```

Lokalitetsuker per lag og år står i utskriften, punkt 3.

**Konflikter og hendelser:**

```
   P1: 19 celler, 19 lokaliteter, 2026-W43..2026-W43
   P2: 8 celler, 6 lokaliteter, 2026-W36..2026-W44
   P3: 64 celler, 63 lokaliteter, 2012-W26..2026-W40
   sykdom: 140 celler, 4 lokaliteter, 2026-W11..2026-W45
   H1 sykdom: 210, 2024-W48..2026-W43, uten uke (bare intervall) 0
   H2 over_lusegrensa: 10214, 2012-W01..2026-W42, uten uke (bare intervall) 0
   H3 brakklagt: 7379, 2012-W02..2026-W42, uten uke (bare intervall) 0
   H4 brakklegging_slutt: 7610, 2012-W02..2026-W42, uten uke (bare intervall) 0
   H5 mekanisk_lusefjerning: 21149, 2012-W03..2026-W42, uten uke (bare intervall) 0
   H6 ny_lokalitet: 11, 2026-W35..2026-W45, uten uke (bare intervall) 0
   H7 lokalitet_ut_eller_status: 5, 2026-W35..2026-W41, uten uke (bare intervall) 0
   H8 kapasitet_endret: 8, 2026-W36..2026-W41, uten uke (bare intervall) 0
   H9 eierskifte: 10, 2026-W42..2026-W43, uten uke (bare intervall) 1
   stempel på første fil: komplett 46596
   eierleddet: lokalitetsuker med en tillatelse der eieren er en personform (eier ikke ført): 3, tillatelser til sammen 3
```

P1 er én innehaver i uke 43 (navnet hos Fiskeridirektoratet ulikt
Brregs), ført på de 19 lokalitetene den eier tillatelser på; R2 F2.1
fant den samme. Eierskiftet uten uke er det over hullet i uke 37: bare
intervallet 02.09–14.09 står, ingen uke er gjettet.

**Holdt mot R8 og R2**, regnet av tidsaksen: grunnen 2012-01-02–2026-10-05
gir fisk 434 032, brakk 358 103 og utenfor 542 315 (R8 F1.1), lus i
fiskeukene over 17 969, under 393 485 og ikke talt 22 578 (R8 F3.1), og
5 039 aktive sykdomsceller med samme fordeling som R8 F4.1. P3 er 22 og
16, P2 5, 1, 1 og 1, og P1 én innehaver, som R2. Bygget slik vi kjente
aksen 04.11.2026 06:00 UTC, deler 71/26 seg i 42, 13, 13 og 3 som R2
F1.2. Behandling «ja» er 35 131: R8s 35 206 minus de 75 i uka
2024-11-11, som `dodt_fra` tar (F8.2). Prøvene står i
`tests/test_tidsakse.py`.

**Persondata, STOPP-regelen punkt 3.** Byggingen fant F15-tilfellet: et
partrederi (PRE, en personform) som eier av én tillatelse på én
lokalitet i eierskapssnapshotene 02.09, 14.09 og 21.09.2026, med
personformen bare i `eier_type`, der døra ikke ser den (CLAUDE.md § 7,
R2 F6.1). Det er ikke et navn, men et orgnr som peker på en personform,
og det er behandlet slik regelen sier: eieren er holdt ute og telt
(`eierskap__personform_utelatt`, 3 lokalitetsuker). Tillatelsen står.

**Presisering til F8.1:** lista er linjene
`lusetall/<filnavn>\t<sha256 over den utpakkede kroppen>\n` for de 772
kroppene, sortert på filnavn.

**Heine avgjør:** om registerets `prodomraade_status` («GUL» for PO 2
og 6–11, F6.3) skal stå i tidsaksen for seg, og om luseinnkomsten skal
bli et eget lag (F11.3). Ingen av dem er med nå.
