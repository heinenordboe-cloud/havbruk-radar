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

---

## Etterskrift 08.11.2026: merket per påstand, og hashene i dokumentet

*Teksten over er ikke endret.* Kontrolløren (frø 3777162473) fant 0
påstander å trekke: MÅLT sto bare i overskriftene, og hashene sto i
utskriften, ikke her. Tallene er de samme; under står de med merket og
hele sha256 (over utpakket kropp) på hver rad, regnet på nytt med samme
definisjoner som F1 og F2.

F1, per kropp i `data/arkiv/` (personform = `organisasjonsform.kode` i
ENK, DA, ANS, PRE; kontaktfelt = `epostadresse`, `telefon` eller
`mobil`).

**Radene teller OBJEKTER i kroppen**, ikke ulike enheter: Brreg-svaret
er søkesider, og en enhet som står på to sider, telles to ganger.
Kontrolløren (frø 1911522043) fant 954 objekter og 938 ulike
organisasjonsnumre i `2026-08-17.2`, og 1805 mot 1759 i `2026-11-02`.
Tallene i F1-tabellen over (98 og 820) er ULIKE organisasjonsnumre over
alle kroppene. De 13 første har personform, de seks fra 28.09.2026 ikke:

| kropp | sha256 | enheter | med personform | med kontaktfelt | merke |
|---|---|---|---|---|---|
| `enhetsregisteret/2026-08-17.2.json.gz` | `8f990aa14e7e20c6fdefb46917d92d3703402d291a849faa8b0a576de9633e50` | 954 | 82 | 442 | MÅLT |
| `enhetsregisteret/2026-08-17.3.json.gz` | `8f990aa14e7e20c6fdefb46917d92d3703402d291a849faa8b0a576de9633e50` | 954 | 82 | 442 | MÅLT |
| `enhetsregisteret/2026-08-17.4.json.gz` | `8f990aa14e7e20c6fdefb46917d92d3703402d291a849faa8b0a576de9633e50` | 954 | 82 | 442 | MÅLT |
| `enhetsregisteret/2026-08-17.5.json.gz` | `8f990aa14e7e20c6fdefb46917d92d3703402d291a849faa8b0a576de9633e50` | 954 | 82 | 442 | MÅLT |
| `enhetsregisteret/2026-08-17.json.gz` | `8f990aa14e7e20c6fdefb46917d92d3703402d291a849faa8b0a576de9633e50` | 954 | 82 | 442 | MÅLT |
| `enhetsregisteret/2026-08-24.2.json.gz` | `542d919920afd35a47db0ebeac427144ed86f3273252dd72469ef6caba32c93f` | 1857 | 64 | 829 | MÅLT |
| `enhetsregisteret/2026-08-24.3.json.gz` | `542d919920afd35a47db0ebeac427144ed86f3273252dd72469ef6caba32c93f` | 1857 | 64 | 829 | MÅLT |
| `enhetsregisteret/2026-08-24.4.json.gz` | `542d919920afd35a47db0ebeac427144ed86f3273252dd72469ef6caba32c93f` | 1857 | 64 | 829 | MÅLT |
| `enhetsregisteret/2026-08-24.json.gz` | `88c0dd231d3b7df81ebbd0bc2f462fc559da390f7972119e24e31a1cac47e2c8` | 1857 | 64 | 829 | MÅLT |
| `enhetsregisteret/2026-08-31.json.gz` | `d7f7e92024ae70889bb947deaa3f152ab0632f16bf3ccad3be610485f9caa78a` | 1857 | 64 | 829 | MÅLT |
| `enhetsregisteret/2026-09-07.json.gz` | `a469fb3b7a8f69608cdc28e419d543617346d40e07b44c559ea91243c8393785` | 1855 | 64 | 828 | MÅLT |
| `enhetsregisteret/2026-09-14.json.gz` | `6cb8b2a0afd30dde26fb1618785d3d918165b15a6ca57ba6ad539d00971873dc` | 1854 | 64 | 828 | MÅLT |
| `enhetsregisteret/2026-09-21.json.gz` | `3971492ea8505be0c5f3f29c880e304b165349143d019fc2d106e01ed7894377` | 1857 | 64 | 826 | MÅLT |
| `enhetsregisteret/2026-09-28.json.gz` | `b66aa57e574c5e991465c1710e41ac9373771d83fc6c9e891041e2b9ac215db0` | 1794 | 0 | 784 | MÅLT |
| `enhetsregisteret/2026-10-05.json.gz` | `a11e2d999450daa818f3e6ebf5ac67ca2dc69c9f3901cc979228f9b9532751a5` | 1787 | 0 | 780 | MÅLT |
| `enhetsregisteret/2026-10-12.json.gz` | `cb63dc091cf45d38767fe7183da26e53d26c2ceabccd5b7f98debe7810ddf63f` | 1790 | 0 | 781 | MÅLT |
| `enhetsregisteret/2026-10-19.json.gz` | `f9bddbf6ddf406e67553068d51d8188a0260f1a905ea51717a2f3c8a474c8f14` | 1795 | 0 | 778 | MÅLT |
| `enhetsregisteret/2026-10-26.json.gz` | `6cdcdbb390fade916e10528a2e6168644a3cac580b5315bb1916bec674b80659` | 1806 | 0 | 780 | MÅLT |
| `enhetsregisteret/2026-11-02.json.gz` | `e108a556c90daabb8173eb80d3e4bc616e990c360215cd8c1a5ef1c58c97e247` | 1805 | 0 | 780 | MÅLT |

| kropp | sha256 | rader med navn og tomt identityNr | merke |
|---|---|---|---|
| `eierskap-overforinger/%C3%98-HD-0502.json.gz` | `ebb0c56e99fdcd9a8dab7c8bc7b5790f87984e1776315623ec11d28733a0da23` | 1 | MÅLT |
| `eierskap-overforinger/AA-G-0301.json.gz` | `22a0dde33a85eda6bcaac7a23e0a103830299b2c697838bb76bf236a39b7cc44` | 1 | MÅLT |
| `eierskap-overforinger/AA-L-0317.json.gz` | `d893c4f6ffa33d78811709b5c65ca6eafe5930aba5dda89e82d912418a1241c8` | 2 | MÅLT |
| `eierskap-overforinger/N-HS-0003.json.gz` | `561dd29289ad204bd02b97b4d27fa17a86accb4a8e3877ee8386372893a302ad` | 1 | MÅLT |
| `eierskap-overforinger/NT-FS-0314.json.gz` | `a9efdc6361c50cf74c6d118090090166655a340c286d690a162b53924184cb0b` | 1 | MÅLT |
| `eierskap-overforinger/NT-FS-0316.json.gz` | `a9efdc6361c50cf74c6d118090090166655a340c286d690a162b53924184cb0b` | 1 | MÅLT |
| `eierskap-overforinger/NT-N-0302.json.gz` | `a7c5b2f235e7326da82ea38d097f59b52a067efedf1569adb3610f7208e15bc9` | 1 | MÅLT |
| `eierskap-overforinger/NT-N-0315.json.gz` | `a7c5b2f235e7326da82ea38d097f59b52a067efedf1569adb3610f7208e15bc9` | 1 | MÅLT |
| `eierskap-overforinger/OP-NA-0502.json.gz` | `9dba43f2907432d3c489cb2741989040e75eb2eac2497f6b31d7a6dfa489fcc2` | 1 | MÅLT |
| `eierskap-overforinger/OP-NA-0505.json.gz` | `f99e2289dc29e531ec5a51dc1ec3f79e0851baf816a2a82919102e37bf01ec69` | 1 | MÅLT |
| `eierskap-overforinger/OP-SL-0506.json.gz` | `6ce9114e518b97e29f3fb294205b80b0ce1623c9fd6ce1aba14f28feb15035d3` | 1 | MÅLT |
| `eierskap-overforinger/R-BR-0001.json.gz` | `a4375632800ed7aa7da37821a8792c5a202020ea86111b8561d274a353676852` | 1 | MÅLT |
| `eierskap-overforinger/SF-SD-0005.json.gz` | `d2a25f5320c23f6cd88545c6c7bb4605c9eec6ec1659b8f828167335a61b1eb3` | 1 | MÅLT |
| `eierskap-overforinger/ST-AA-0326.json.gz` | `3bfc3d9bf40db6db1e80f205cc89747b39a88d3477a756d92c6cbf1beb81474a` | 1 | MÅLT |
| `eierskap-overforinger/VA-F-0002.json.gz` | `e2ffb5cdddeea9ffbbbfc39ed2be5550e62aa0718ae7ec16e646976cc65ad3b1` | 1 | MÅLT |
| `eierskap-overforinger/VA-S-0303.json.gz` | `882f8dcdfffaa47c670774f2dfcde96be3aaf785c8b3b855ff59344489dbae53` | 1 | MÅLT |
| `eierskap-overforinger/_-HD-0502.json.gz` | `a3d0a93ff99b7da8ae34a6d8ae5a88a112b7a77d96ccf2ae6546ee3ec8c1164d` | 1 | MÅLT |

F3: `eierskap/2026-09-21.json.gz`, sha256
`22142f87518388f0fb84fe2ef4eb191374221320795ef4ecb6fb28ba1885500c`, har
3 ulike `JointLiabilityCompany`, 2 `UnlimitedLiabilityCompany` og 1
`JointlyOwnedShippingCompany` (MÅLT). Samme tre tall i
`eierskap/2026-09-02.json.gz` og `2026-09-14.json.gz`; ingen kropp etter
21.09.2026 har dem.

F6 er MÅLBAR, ikke MÅLT: den er holdt mot et bygg av nettstedet, som
ikke er en arkivert kropp.
