---
dato: 2026-08-17
tittel: Beslutningsloggen flyttes til repoet, én fil per beslutning
status: gjeldende
commit: 
---

# Beslutningsloggen flyttes til repoet, én fil per beslutning

**Bestemt:** `docs/beslutninger/<dato>-<kort-navn>.md`, én fil per
beslutning, i det offentlige koderepoet. Erstatter
`01_beslutningslogg.md` i Claude-prosjektet.

**Hvorfor splitting:** Samme argument som changeloggen 16.08. En fil som
skrives om hver gang lagres som en ny nesten-full kopi i git, og
historikken sier bare «loggen ble oppdatert». Med én fil per beslutning
viser `git log` presist når hver enkelt oppstod og ble revidert. Loggen
vokste fra null til 534 linjer på to dager.

**Hvorfor repoet:** Beslutningen og commiten som implementerte den
havner i samme historikk, og `commit`-feltet i headeren gjør hoppet fra
hvorfor til hva til ett oppslag. Manuell kopiering fra chat bortfaller —
det var den som ga duplikater og feilplasserte blokker 17.08.

**Hvorfor offentlig:** Loggen er et sterkere CV-artefakt enn koden.
Reverseringskriterium på hver beslutning, dokumenterte feilmoduser,
skillet mellom bekreftet og antatt — det er en type tenkning få
utviklere skriver ned. I dag ser ingen den.

**Ikke duplisering av `docs/`:** Regelen om å ikke duplisere repoets
dokumentasjon handler om innhold, ikke plassering. `ARKITEKTUR.md` sier
hvordan systemet virker; beslutningene sier hvorfor det ble sånn.

**Grensen:** Vurderinger om enkeltaktører, bransjekontakter eller
familieforbindelser skrives ikke i offentlige beslutningsfiler. Går en
beslutning inn på det, blir den værende i prosjektmappa.

**Status-feltet:** Hver fil har `status: gjeldende` eller
`status: erstattet-av <fil>`. Erstattede beslutninger slettes ikke —
men de skal ikke kunne leses som gjeldende, slik den første
volumvaktposten kunne 17.08.

**Utkast, ikke ferdig tekst:** En agent kan skrive utkastet fra diffen,
men vurderingen er hele verdien. «Terskelen er en vurdering, ikke et
funn» betyr noe fordi jeg mener det. Skrives loggen av en agent, blir
den dokumentasjon i stedet for tenkning.

**Ville snudd det:** At beslutningene i praksis blir skrevet av agenten
og lest av ingen. Da er problemet at loggen ikke lenger er tankearbeid,
og den hører hjemme utenfor repoet igjen.
