---
dato: 2026-08-17
tittel: Feltnivåvakt — volumvakten er for grovkornet til å se ett felt forsvinne
status: gjeldende
commit: d21803c
---

# Feltnivåvakt — volumvakten er for grovkornet til å se ett felt forsvinne

**Bestemt:** `health.py` sporer antall rader per `(kilde, felt)` og
varsler når et felt som fantes i referansen har null rader nå. Samme
høyvannsmerke-semantikk som volumreferansen. Egen kvittering:
`--godta-felt`.

**Hvorfor:** Volumvakten måler totalen per kilde, og det er for grovt.
Målt på akvakultur 17.08.2026: 29 felter, 48236 observasjoner, største
enkeltfelt 1779 rader = 3,7 %. Terskelen er 10 %. **Ingen av de 29
feltene kan utløse volumvakten** — et felt kan slutte å komme hver uke i
det uendelige mens jobben er grønn.

Det er SCHEMA-buggen i mindre skala, og SCHEMA-buggen er grunnen til at
volumvakten finnes. Vakten dekket ikke sitt eget opphav.

**Reprodusert på ekte data før fiksen:** `prodomraade_status` fjernet
fra dagens akvakultur-snapshot gir 48236 → 47266 = 2,0 % fall.
Volumvakten stille, feltvakten fyrer, i samme kjøring. Det er hele
påstanden — uten den er dette bare en vakt som duplikerer en annen.

**Hvorfor så smalt:** Bare null rader varsler. Ingen prosentterskel per
felt, fordi det ikke finnes ukesvarians å kalibrere mot ennå, og felt
varierer legitimt — `prodomraade_*` finnes for 970 av 1779 lokaliteter,
`tillatelser_trukket` for 853. Null er entydig; 15 % er en gjetning.
Terskelen kan komme når det finnes måneders data.

**Hvorfor to kvitteringer og ikke én:** `--godta-volum` svarer «totalen
er legitimt lavere nå». `--godta-felt` svarer «dette feltet finnes
legitimt ikke lenger». De opptrer uavhengig: et register kan
konsolideres uten å miste felter, og en etat kan slutte å publisere ett
felt uten at totalen merkes. Slår man dem sammen, blir den ene en stille
aksept av den andre — registeret krymper legitimt, du kvitterer volumet,
og at et felt samtidig forsvant svelges med i kjøpet. Det er demping,
og demping er den ene tingen kvitteringen ikke skal være.

**Nede kilde nullstiller ikke referansen:** En kilde som er nede
leverer null felter. Uten unntaket ville hele feltsettet blitt meldt
borte samtidig, og verre: et tomt feltsett ville blitt den nye
normalen, slik at vakten var død for den kilden etterpå. Dekket av
test.

**Om kontrakten:** `health.oppdater()` tar nå observasjonsrammen i
tillegg til resultatene. Kjernen teller selv — en kilde trenger ikke
vite at feltvakten finnes, og en ny kilde er fortsatt én fil. Samme
kategori som import-isoleringen 16.08: kjernen får se det den allerede
har i hånda.

**Ikke bygget: vakt per NACE-kode.** Den så ut som samme mekanisme, men
er det ikke. Observasjonenes `naeringskode`-verdier er enhetenes
HOVEDKODE, ikke hvilket søk som fant dem. Verifisert: `10.912` søkes på,
men er aldri hovedkode for noen enhet — en observasjonsbasert kodevakt
ville meldt den tom på en frisk kjøring. Fire koder (`03.110`, `33.120`,
`35.121`, `46.322`) er hovedkode uten å bli søkt på. Per-søk-tall finnes
bare i kilden (`treff_per_kode`), så den vakten trenger en egen kanal
og er en egen beslutning.

**Ville snudd det:** At feltvarsler i praksis er støy — at felt
forsvinner og kommer tilbake av seg selv i registrene. Da er null-regelen
for streng, og den må erstattes av «borte N kjøringer på rad», ikke
fjernes.
