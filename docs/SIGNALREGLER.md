# Signalreglene — spesifikasjon for omskriving

Oppdrag til Claude Code. Fem verifiserte feil og én lekkasje, alle
funnet ved lesing av `core/signals.py` og `rules/signals.yml`
18.08.2026, alle bekreftet mot snapshotet fra 17.08.

Ingenting her har forurenset data. `data/changelog/` lagrer rå endringer
uten signal og vekt, så hele scoringen kan kjøres på nytt retroaktivt.
Feilene koster framover, ikke bakover.

**Hastverket:** mandag 24.08 er første kjøring som gir en ekte diff.
Uke én finnes bare én gang.

---

## 0. Lekkasjen — det viktigste

`score()` går rad for rad, legger til raden bare hvis en regel matcher,
og bryter. **Rader ingen regel treffer havner aldri i utdata.** Treffer
ingen regel noe som helst, returnerer funksjonen en tom ramme — selv om
det var fire hundre endringer den uka.

Så lenge det er tilfellet, vet du ikke hva du ikke ser.

**Endring:** `score()` returnerer ALLE rader. Uten treff får raden
`signal: null` og `vekt: 0`.

**Interfacet endres, så `run.py` må følge med.** I dag er
`scoret.height` antall treff. Etter endringen er det totalen. Kall det
noe annet, og la både utskriften og commit-meldingen si begge tall:

    412 endringer, 38 scoret, 374 uklassifiserte

Topplista skal fortsatt bare vise scorede rader. Legg i tillegg de fem
vanligste feltene blant de uklassifiserte i commit-meldingen — det peker
rett på hvilke regler som mangler.

**Verifisering:** scoret + uklassifisert må være nøyaktig lik antall
endringer. Det er den ene summen som ikke kan stemme ved et sammentreff.

---

## 1. Nytt selskap merkes som ny lokalitet

`_matches()` sammenligner bare `felt` og `endringstype`. «Ny lokalitet i
registeret» (`navn`/`ny`, vekt 8) står før «Nytt selskap i bransjen»
(`navn`/`ny`, vekt 7) i fila, og første treff vinner. Hver nyregistrert
virksomhet fra Enhetsregisteret får dermed lokalitetsetiketten.

Raden har allerede `source` og `entity_type` fra `diff.py`. Grammatikken
bruker dem bare ikke.

**Endring:** to nye valgfrie regelnøkler, `kilde` og `entity_type`, som
filtrerer på samme måte som `felt`. Sett dem på de to reglene som
kolliderer.

---

## 2. Boolske felter kan ikke ha retning

`konkurs`, `under_tvangsavvikling`, `er_i_konsern` og
`ansatte_er_registrert` står uten `retning`, altså `begge`. Å gå konkurs
og å komme ut av konkurs scorer identisk på vekt 9.

Verre: retter du det med `retning: "ned"`, treffer koden
`float(row["old_value"])` på verdien `false`, får ValueError, og regelen
slutter å matche i det hele tatt. Stille.

Dette er samme feilmodus som beslutningen fra 16.08 fjernet for tall,
gjenoppstått i en form fiksen ikke dekket.

**Endring:** to nye valgfrie nøkler, `fra` og `til`, som sammenligner
`old_value` og `new_value` som tekst. `til: "True"` på konkursregelen
fanger inngangen; utgangen er en egen regel med egen vekt, eller ingen
regel. Numerisk `retning` og tekstlig `fra`/`til` skal ikke kunne stå på
samme regel — det er en formatfeil og skal si fra.

---

## 3. Kapasitet fra null fanges aldri

`if old == 0: return False`. Nullvernet mot divisjon spiser samtidig den
mest interessante hendelsen en lokalitet har: at det settes ut fisk der
det ikke var noe.

**Målt omfang, som er mindre enn det ser ut:** 77 lokaliteter står med
kapasitet null, men 72 av dem måler i STK og 50 er ferskvann — det er
settefiskanlegg der feltet er tomt, ikke tomme sjølokaliteter. Reelt
berørt er de fem som måler i tonn og de tretten i saltvann.

Fiksen er likevel riktig. Den er bare ikke like akutt som antallet 77
antyder, og det bør stå i beslutningen.

**Endring:** ny valgfri nøkkel `fra_null: true`. Er den satt, matcher
regelen når `old == 0` og `new > 0`, uten prosentregning. Er den ikke
satt, beholdes dagens oppførsel. Ingen implisitt endring av eksisterende
regler.

---

## 4. Kapasitet sammenlignes uten enhet

Kilden lagrer `kapasitet_enhet` med vilje. Regellaget kan strukturelt
ikke lese et felt til.

**Presisering av hva feilen faktisk er:** innenfor én lokalitets diff er
enheten den samme med mindre den *endret seg*. Problemet er altså ikke
at ulike lokaliteter bruker ulike enheter — det er at en lokalitet som
bytter fra tonn til stykk gir en prosentendring på to usammenlignbare
tall, scoret på vekt 10.

Det er ikke hypotetisk: seks enheter er i bruk, og 433 av 1779
lokaliteter oppgir kapasitet i noe annet enn tonn.

**Endring:** ny valgfri nøkkel `krev_uendret: kapasitet_enhet`. Regelen
matcher ikke hvis det navngitte feltet også har en endring for samme
entitet i samme kjøring.

`score()` har hele endringsrammen, så dette krever ingen ny datakilde:
bygg et oppslag over (entity_id, field) som endret seg, og slå opp.
Generisk mekanisme, ikke kapasitetsspesifikk.

Legg til en egen regel for selve enhetsbyttet, med lav vekt. Det er en
reell hendelse som ikke skal forsvinne fordi den er upraktisk.

---

## 5. Rangeringen rangerer ikke

Tolv av atten regler ligger på vekt 7 eller høyere. «Aksjekapital økt»
har terskel 1 % og vekt 8 — den vil fyre nesten hver uke og skyve ekte
hendelser ut av topplista på frekvens alene.

**Dette er Heines vurdering, ikke en kodeoppgave.** Claude Code skal
ikke sette nye tall. Gjør ingenting her utover å påpeke det i utskriften
hvis én regel står for mer enn en tredel av treffene i en kjøring.

---

## Rekkefølge

Punkt 0 først og alene. Den er den eneste som endrer hva du ser, og de
andre er lettere å vurdere når du ser hva som faktisk ikke treffer.

Deretter 1, 2, 3, 4 i den rekkefølgen — økende inngrep i grammatikken.

## Akseptansetest

Regel 6: kjør det og se resultatet, ikke bare diffen.

Kjør `run.py --tving` mot en midlertidig `HAVBRUK_DATA_DIR` med to
snapshots som skiller seg på kjente måter, og bekreft hver fiks i
utdata — ikke i testene alene. Feilen i prediksjonsloggen 18.08 var
grønn på 86 tester og falt først da noen kjørte den.

Testene skal dekke: at et nytt selskap får selskapsetiketten, at en
boolsk overgang scorer ulikt hver vei, at 0 → N fanges når `fra_null`
er satt og ikke ellers, at en kapasitetsendring med samtidig
enhetsendring ikke matcher, og at scoret + uklassifisert er lik totalen.
