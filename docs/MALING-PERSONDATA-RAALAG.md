# Måling: personopplysninger i rålaget, per mappe

Økt 4e punkt 5, 08.11.2026. Spørsmålet fra R4 punkt 7: hvilke
personopplysninger ligger i de arkiverte kroppene i
`havbruk-radar-data/data/arkiv/`, per mappe — og publiseres noen av dem?

Datagrunnlag: datarepoet ved `1053549` (08.11.2026), og nettstedet bygget
av kodrepoet ved `4c1b489` med det datarepoet (`nettsted.py --alle`).
Skriptet er `analyse/persondata_raalag/maal.py`; utskriften står uendret i
`analyse/persondata_raalag/utskrift.txt`.

**Dokumentet gjengir ingen navn, nummer eller adresser**, bare antall og
hasher. Kodrepoet er offentlig.

## Merkene

Som `docs/PROVENIENS-2026-09-11.md`: **MÅLT** er holdt mot en arkivert
kropp med sha256; **MÅLBAR** er regnet ut av målte tall; **EKSTERN**
hviler på noe utenfor arkivet; **UBELAGT**: ingen kropp sier det.

## STOPPREGEL (skrevet før skriptet ble kjørt)

Målingen stopper og rapporterer, i stedet for å skrive utkastet til
behandlingsgrunnlag, hvis **én eneste identifikator** fra rålaget —
organisasjonsnummer eller navn på en enhet med personform, navn uten
identitetsnummer, en eier som ikke er et selskap, en søker uten
organisasjonsnummer, eller en personlig e-postadresse — står i det bygde
nettstedet. I så fall er spørsmålet ikke lenger hvilket grunnlag arkivet har,
men at noe er publisert som ikke skulle vært det.

Treff som viser seg å være et annet objekt med samme navn (et AS og et
DA med likt navn), regnes ikke som brudd, men hvert slikt treff skal
forklares enkeltvis før det avskrives.

Målingen stopper IKKE fordi tallene i arkivet er høye. Arkivet er
append-only (CLAUDE.md regel 2), og oppdraget sier uttrykkelig: ingen
sletting og ingen omskriving av historikk.

**Utfall:** stoppregelen ble ikke utløst. 0 av 1 784 identifikatorer
står i bygget (F6).

## De tre sterkeste funnene

1. **F6 — ingenting av det som ble funnet, står i det bygde nettstedet.**
   Sterkest fordi det er spørsmålet oppdraget stilte, og fordi det er
   holdt mot hver eneste identifikator, ikke mot et utvalg.
2. **F1 — `enhetsregisteret` er den eneste mappa med personformer i
   Brreg-kroppene**: 13 av 19 kropper, 98 ulike enheter. Samme tall som
   R4 (13 av 19), regnet på nytt med et annet skript.
3. **F2 — 12 navn uten identitetsnummer i 17 overføringskropper.**

Svakere: F4 (e-postadresser) er en mønstertelling, og «personlig» er
skriptets skille mot funksjonsadresser, ikke en lesning av hver adresse.
F5 (AIS) er ikke målt.

## Funnene

### F1 — Brreg-kropper: personformer og kontaktfelt — MÅLT

Utskriften, del A:

| mappe | kropper | med personform | med kontaktfelt | enheter med personform | enheter med kontaktfelt |
|---|---|---|---|---|---|
| `enhetsregisteret` | 19 | 13 | 19 | 98 | 820 |
| `enhetsregisteret_oppslag` | 1 | 0 | 0 | 0 | 0 |
| `eierskap-brreg` | 111 | 0 | 0 | 0 | 0 |

Personform er `organisasjonsform.kode` i `core/persondata.PERSONFORMER`
(ENK, DA, ANS, PRE). Kontaktfelt er `epostadresse`, `telefon` eller
`mobil`, uansett form. De 13 kroppene står med sti og sha256 i
utskriften; de fem fra 17.08.2026 har samme hash
(`8f990aa14e7e20c6…`), som i R4. Alle 19 er fra før 09.11.2026; fra den
datoen skrives kroppen uten kontaktfeltene (`bcd4221`), og den første
kjøringen etter det er ikke gjort ennå.

*Feil hvis:* en kropp har enhetene et annet sted enn i objekter med både
`organisasjonsnummer` og `navn` (skriptet går gjennom hele JSON-treet,
så det ville ikke sett en annen struktur).

### F2 — Overføringer: navn uten identitetsnummer — MÅLT

17 kropper i `eierskap-overforinger`, 18 rader, 12 ulike navn
(`officialName` med `identityNr` null eller tom). R4 talte 17 rader i 16
kropper 04.11.2026; én kropp er kommet til siden. At navnene er
personer, er en ANTAKELSE, som i R4 F2: kilden sier det ikke. Ingen andre
mapper har slike rader.

*Feil hvis:* kilden blanker `identityNr` for noe annet enn personer, eller
bruker et annet feltnavn for identiteten enn `identityNr`.

### F3 — Tillatelseseiere og søkere — MÅLT

`eierskap` (tillatelsesregisteret): ingen `Person` og ingen
`SoleProprietorship` i noen kropp — de filtreres før arkivering
(`sources/eierskap.py`, `PERSONTYPER`). Personformene som står der:
3 ulike DA (`JointLiabilityCompany`), 2 ANS (`UnlimitedLiabilityCompany`)
og 1 partsrederi, oversatt som i `sources/eierskap.py` linje 159–166.

`akvakultur-soknader`: 0 søkere med navn og uten organisasjonsnummer.

*Feil hvis:* pub-aqua bruker en `typeValue` for personer som ikke står i
`PERSONTYPER`.

### F4 — E-postadresser i tekstkroppene — MÅLT (mønster)

Ulike adresser der lokaldelen ikke er en funksjonsadresse (post@,
kontakt@ …), per mappe: `enhetsregisteret` 327 (kontaktfeltene i F1),
`regjeringen-pressemeldinger` 6 (pressekontaktene),
`reguleringsomraader` 3 (forfatterne i NMDC-metadataene), `vilkar-*` 7
(redaktører og kontaktpersoner på vilkårssidene) og `maling-lovdata` 1.

*Feil hvis:* en adresse står i et format mønsteret ikke kjenner igjen
(med mellomrom eller «(at)»); i så fall er tallet for lavt.

### F5 — AIS — IKKE MÅLT

AIS-kroppene ligger ikke i git, bare på kystvakt-1 og i Storage Box
(`MALING-AIS.md`), og mappene i arkivet her har én prøvekropp hver.
Meldingene bærer MMSI og skipsnavn. Om det er personopplysninger for små
fartøy, er en vurdering, ikke en telling: UBELAGT.

### F6 — Ingenting av det over er publisert — MÅLT

Hver identifikator fra F1–F4 holdt mot de 6 526 tekstfilene i bygget
(.html som synlig tekst; .xml, .json, .csv, .txt rått): navn som
delstreng, også «Fornavn Etternavn» for «Etternavn, Fornavn»; nummer mot
alle sifferfølger; adresser mot alle adresser i bygget.

| kategori | identifikatorer | funnet i bygget |
|---|---|---|
| A kontaktfelt | 1 221 | 0 |
| A navn med personform | 98 | 0 |
| A orgnr med personform | 98 | 0 |
| B navn uten identitetsnummer | 12 | 0 |
| C eier med personform | 12 | 0 |
| E personlig e-postadresse | 343 | 0 |

Bygget er fra kodrepoet ved `4c1b489`; det publiserte er fra `a909dd4`
(04.11.2026) og er ikke målt her (EKSTERN).

*Feil hvis:* bygget viser en identifikator i en annen form enn de tre
over, for eksempel et nummer med mellomrom inne i (`123 456 789`) i
synlig tekst. Sifferfølger med mellomrom er tatt med, men bare med
mellomrom slik bygget skriver dem.

## Hva målingen ikke sier

Om opplysningene har et behandlingsgrunnlag, om de må slettes, og om en
kjøper kan arve dem, er EKSTERN (advokat). Utkastet til
behandlingsgrunnlag står i `docs/BEHANDLINGSGRUNNLAG-UTKAST.md`. Ingen
kropp er slettet og ingen historikk skrevet om.
