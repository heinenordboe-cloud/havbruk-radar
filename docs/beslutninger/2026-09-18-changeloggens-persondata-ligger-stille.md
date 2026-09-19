---
dato: 2026-09-18
tittel: Changeloggens persondata blir liggende — publiseringsveien lukkes i stedet
status: besluttet
commit: [fylles inn]
---

# Changeloggens persondata blir liggende — publiseringsveien lukkes i stedet

**Bestemt:** De 381 changelog-radene som bærer navnet eller nummeret til
en entitet dagens lesedør ville fjernet, blir stående urørt. Ingen
gjenberegning, ingen lesedør i `changelog.les_alt()`, ingen endring i
`core/diff.py` — og ingen endring i `core/` i det hele tatt.

Det som ble gjort i stedet, er å lukke veien ut:

1. **Merkekonvensjonen utvides til felt-verdi-tabellene.**
   `data-felt="<feltnavn>"` på hver verdicelle i endringstabellen og
   registertabellen, og `publiseringsvakt.felt_verdier()` leser merkingen
   mot `NAVNEFELT` og personvernfeltene.
2. **`eierskap_historikk` utelates UTTRYKKELIG fra endringstabellen.**
   Klausulen som navnga kilden var død kode; den er nå en navngitt
   utelukkelse med vilkårene for å oppheve den skrevet ned.

Beslutningen er alternativ 4 av fem som ble lagt fram 18.09, og
begrunnelsen er at 0 personrelaterte rader i dag når publisert output.
Det som gjorde valget utrygt, er at beskyttelsen besto av **tre
tilfeldigheter**, og at ingen måling ville fanget at én av dem ble
rettet. Punkt 1 og 2 gjør to av de tre til noe som er skrevet ned og
målt.

---

## 1. Målingen

Personmengden er bygget av **rå** snapshots (`pl.read_parquet`, altså det
døra skjuler): 106 entiteter — DA 38, ENK 34, ANS 33, PRE 1 — med 101
navn og 98 nisifrede id-er. Changeloggen er 1 012 708 rader i 1756 filer.

| kolonne | rader | distinkte | kilde |
|---|---:|---:|---|
| `entity_id` = et person-orgnr | **379** | 19 entiteter | enhetsregisteret |
| `entity_name` = et personnavn | **379** | 19 navn | enhetsregisteret |
| `old_value`/`new_value` = et personnavn | **18** | 17 navn | 16 enhetsregisteret `navn`, 2 eierskap_historikk `mottaker_navn` |
| `old_value`/`new_value` = et person-orgnr | **0** | 0 | — |

**381 rader i alt.** De 16 navneverdiene ligger inne i de 379; de 2
`mottaker_navn`-radene er de eneste utenfor.

- **ENK: 0 rader i hele loggen.** De 699 radene fra 15.09-notatet finnes
  ikke lenger. Fire commits berører `data/changelog/2026-08-24.parquet`
  (26039 → 26045 → 26045 rader), og ingen committed versjon inneholder én
  ENK-rad. Gjenberegning kan heller ikke gjenskape dem: døra fjerner
  ENK-ene fra 17.08-snapshotet ved lesing, så diffen mot 24.08 har ingen
  «borte»-rad å lage.
- Datoene: 375 rader på 2026-08-24 (da utvalget ble utvidet — alle `ny`),
  1 på 09-07, 3 på 09-14.
- **Bare 4 av de 379 teller som bevegelse.** `diff.bevegelse()`
  undertrykker de 375 som utvalgsutvidelse. De er altså allerede null i
  enhver analyse; det de fortsatt gjør, er å være revisjonsspor for at
  grensa flyttet seg.
- `changelog.les_alt()` er `pl.read_parquet` over alle filene. **Det
  finnes ingen lesedør for changeloggen** — `snapshot._les()` verner
  snapshotene, og changeloggen har ingen tilsvarende.

### Null av dem når publisert output

1052 changelog-rader når endringstabellen i det hele tatt: biomasselag
585, akvakultur 310, eierskap 157. **0 av dem er personrelaterte** — 0
rader om en personentitet, 0 personnavn i verdiene, 0 i `entity_name`.

## 2. De tre vilkårene som skjuler dem, og at ingen handler om persondata

**Vilkår 1 — ID-rommet.** Endringstabellen nøkler på lokalitetsnummer
eller bart tillatelsesnummer. `enhetsregisteret` har ni-sifret orgnr som
`entity_id`, og det kan aldri være lik et 4–5-sifret loknr eller et
`H-FJ-0018`. Derfor er **alle 26 232 enhetsregisteret-rader** usynlige
for sida, de 379 inkludert.

**Vilkår 2 — klausulen var DØD KODE.** Filteret tok med
`source in ("eierskap", "eierskap_historikk")`. Men
`eierskap_historikk` har `entity_id` på formen `F-A-0034|2007000034` —
tillatelse|journalnr, fordi én overføring er én entitet og en tillatelse
har mange. **30 104 av 30 104 rader har rørtegnet**, så
`entity_id in tillatelser` kunne treffe 0. Klausulen navnga en kilde den
ikke kunne matche, og de to DA-navnene (`HE-E-0505|2014000149`, datert
2014 og 2015) var skjult av en gren som ikke virket.

**Vilkår 3 — fortsatt-aktuell.** `tillatelser_per_lokalitet` bygges av
NYESTE eierskap-snapshot. En `borte`-rad om den siste tillatelsen på en
lokalitet fjerner sin egen synlighet. Konsekvensen er perverst formet:
**jo mer fullstendig en entitet forsvinner, jo mindre synlig er
forsvinningen** — og en rad om en personentitet er nettopp en rad om noe
som er tatt ut.

Det var H-FJ-0018 som avdekket hele dette: ved neste kjøring forsvinner
raden fra eierskap-snapshotet og skriver 16 `borte`-rader til
changeloggen, hvorav 2 bærer personformnavnet som `old_value`. Den
flyttingen skjer uansett hva som ble bestemt her — se
[2026-09-16-grensa-gaar-ved-sektor-2300.md](2026-09-16-grensa-gaar-ved-sektor-2300.md)
punkt 7.2. Det sida viser, endres ikke av den, fordi vilkår 3 slår inn i
samme øyeblikk.

## 3. Hva som ble bygget

### Merkingen er FELTVOKABULARET, ikke en liste attributtnavn

Konvensjonen fra 15.09 var `data-navn` og `class="navn|eier"`. Den duger
der kolonnen er kjent på forhånd — et eiernavn står alltid i
eierkolonnen. Den duger ikke for en felt-verdi-tabell: samme `<td>` bærer
`siste_rapport` i én rad og `eier_navn` i neste, og en statisk klasse
ville merket alt som navn eller ingenting.

Merkingen er derfor utledet av RADEN, og feltnavnet er det generatoren
allerede har:

    <td data-felt="{{ e.felt }}">{{ e.fra }}</td>

`publiseringsvakt.felt_verdier()` leser merkingen mot `NAVNEFELT`,
`persondata.FORM_FELT` og `persondata.SEKTOR_FELT`. Det er **samme regel
`gransk_csv` har hatt siden 16.09** — kolonneoverskriften er merkingen —
i et annet format. To formater, én regel, og ingen av dem spør om
hvordan en verdi SER UT.

En sideeffekt verdt å nevne, fordi den er den slags kontroll som ellers
blir slått av: prøven trengte ikke tekstvinduet `FORMKONTEKST` for en
feltmerket celle. `<td data-felt="organisasjonsform">DA</td>` felles selv
om `DA` er dekar i 748 rader, fordi merkingen SIER hva feltet er.

**Verifisert ved å plante.** Én konstruert changelog-rad
(`eier_navn`, `old_value = "TESTVIK OG STRAUM DA"`) på en tillatelse som
ligger på en lokalitet, i en kopi av changeloggen med symlink til ekte
snapshots:

    plantede rader som når endringstabellen: 2
    MED merking:   3 funn — ukjent_orgnr x2, ukjent_navn (det plantede navnet)
    UTEN merking:  2 funn — bare de to orgnumrene

Navnet felles av `ukjent_navn` og ikke av `personform`: `DA` er målt
tvetydig, så endelsen i navnet fyrer ikke. Uten merkingen er navnet
usynlig — som er nøyaktig det hullet som ble målt, og andre halvdel av
`test_et_navn_i_endringstabellen_felles_av_porten`.

### Målt på ekte output

    før:   1030 funn — 807 ukjent_navn (75 distinkte), 208 ukjent_orgnr, 15 personform
    etter:  976 funn — 753 ukjent_navn (74 distinkte), 208 ukjent_orgnr, 15 personform
    feltmerkede celler i utputtet: 50 155

Merkingen ga **0 nye funn**: de 24 navneverdiene changeloggen står med i
endringstabellene er alle i hvitelista, og ingen har sektor-2300-endelse.
Prøven er altså ikke skjerpet fordi den fant noe — den er skjerpet fordi
den ikke KUNNE finne noe.

De 54 som forsvant er en rettelse i porten, ikke i dataene:
`ukjent_navn` sammenlignet HTML-escapet celletekst mot en uescapet
hviteliste. Alle 54 var samme navn — `EGIL KRISTOFFERSEN &amp; SØNNER
AS`, et AS som ligger i hvitelista med `&`. Avkodingen skjer per VERDI og
ikke på filkroppen; gjort på kroppen ville den endret inputtet til
`ukjent_orgnr`, som er en tokenisering der ett tegn avgjør.

De gjenstående 976 er **ikke** denne beslutningen. De er kategori 1 fra
15.09 — hvitelista leser nyeste snapshot per kilde mens generatoren leser
alle 21 årgangene av `eierskap_historikk` — og den beslutningen står
åpen. Porten gir exit 1, og ingenting publiseres før den er tatt.

### Utelatelsen er navngitt

`nettsted.ENDRINGER_VIA_TILLATELSE` er kildene som kan vises via en
tillatelse; `nettsted.ENDRINGER_UTELATT` er den som uttrykkelig ikke kan.
Begrunnelsen står i koden med målingen, og tre vilkår må være oppfylt før
`eierskap_historikk` kan vises:

1. **En uttrykkelig kobling.** Tillatelsesdelen av den sammensatte id-en
   må splittes ut med vilje — ikke matche ved et sammentreff.
2. **Merkingen.** På plass fra i dag.
3. **En avklaring av de to DA-navnene.** Åpen.

`test_eierskap_historikk_er_uttrykkelig_utelatt` og
`test_utelatt_kilde_naar_ikke_endringstabellen` håndhever begge deler —
konstanten og oppførselen. Den første bærer setningen fra
16.09-notatet: faller den, er valget endret, og da skal beslutningen
endres med den.

## 4. Prisen, sagt rett ut

**381 rader med persondata blir liggende i datarepoet, og leses
ufiltrert av hvert bygg.** For snapshotene er «blir liggende på disk,
døra fjerner ved lesing» den etablerte formen — regel 2. Her er bare
første halvdel sann.

Det som beskytter dem er ikke at de er utilgjengelige, men at ingen
generator i dag spør etter dem. Vilkår 1 og 3 er egenskaper ved
nøkkelrommet og ved hva som er aktuelt — ikke ved personvern — og de kan
endres av en visning ingen tenker på som en personvernendring. En
oversiktsside over «siste endringer på tvers av kilder» ville føre alle
26 232 enhetsregisteret-radene rett til utputtet, og de 379 med dem.

Porten ville sett dem — `entity_name` og `old_value` i en feltmerket
tabell er dekket fra i dag. Den ville sett dem som `ukjent_navn`, altså
som et funn om proveniens, og en leser av rapporten ville måttet vite at
det gjelder en person.

## Hva som ville snudd valget

- **At changeloggen skal vises i sin helhet.** Dette er det tyngste, og
  det er grunnen til at notatet finnes framfor en kommentar i koden. En
  visning uten `entity_id`-filter — en oversiktsside, et søk, en
  «endringer denne uka» på tvers av kilder, eller en CSV av loggen ved
  siden av sidene — fjerner vilkår 1 og 3 samtidig. Da er de 381 radene
  ikke lenger stille, og alternativ 4 er ikke lenger et alternativ:
  spørsmålet blir gjenberegning (alt. 1) eller en lesedør i `les_alt()`
  (alt. 2), og det skal avgjøres FØR visningen skrives, ikke etterpå.
  **Målt for alt. 2, slik at valget ikke må gjøres på nytt:** 16 av de 19
  entitetene er selv-identifiserende fra loggen alene — de er `ny`, så
  `organisasjonsform` og `institusjonell_sektorkode` står der som egne
  rader. En dør på de to feltene fjerner 376 av 379 og **mister 3**
  (enkeltstående `endret`-rader uten klassifiserende felt). Skal alle 19
  tas, må døra krysspeile snapshotene, altså lese alle snapshots for å
  lese changeloggen.
- **At noen retter vilkår 2.** Den er nå en navngitt utelukkelse med
  vilkår og en test, så en retting er en beslutning. Tas den, er de 2
  DA-navnene en åpen sak som må lukkes først.
- **At en ny kilde får lokalitetsnummer som `entity_id` og bærer navn.**
  Da gjelder vilkår 1 ikke lenger for den kilden, og radene dens går rett
  til endringstabellen. Merkingen fanger dem, men hvitelista avgjør om
  det blir et funn — og et navn som er i nyeste snapshot gir ingen funn
  selv om det er en person.
- **At `entity_name` blir vist.** Ingen tabell viser den kolonnen i dag.
  379 av de 381 eksponeringene ligger der, så en visning som tar den med
  er en helt annen risiko enn en som viser `old_value`.

**Ville IKKE snudd det:** at tallet 381 vokser med et par rader i uka
fordi biomasse eller akvakultur skriver `borte`-rader. Mekanismen er
den samme og målingen er gjentakbar; det som ville snudd valget er at
radene begynner å NÅ noen, ikke at de blir flere.
