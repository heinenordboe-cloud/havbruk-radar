---
dato: 2026-08-16
tittel: Alt normaliseres til (entity_id, field, value, observed_at)
status: gjeldende
commit: 
---

# Alt normaliseres til (entity_id, field, value, observed_at)

**Bestemt:** Ett observasjonsformat for alle kilder. Alt lagres som tekst,
typing skjer i analysen.

**Hvorfor:** Alternativet er én tabell per kilde, og da må diff-, signal-
og dashbordlaget kjenne hver enkelt kilde. Med ett format kjenner de null.

**Prisen:** Tap av typeinformasjon ved lagring. Bevisst byttehandel når
kildene er uforutsigbare.
