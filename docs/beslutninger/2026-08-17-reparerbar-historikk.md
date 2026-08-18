---
dato: 2026-08-17
tittel: Historikken skal kunne repareres og kryssrefereres bakover
status: gjeldende
commit: 
---

# Historikken skal kunne repareres og kryssrefereres bakover

**Bestemt:** Fire endringer som deler samme begrunnelse — de kan ikke
gjøres senere uten at ukene før forblir mangelfulle.

1. **Rå-arkiv.** Kjernen skriver råsvaret fra hver kilde gzippet til
   `data/raw/<kilde>/<dato>.json.gz` før `parse()` kalles. Append-only,
   samme guard som snapshotene.
2. **Proveniensfelt.** `fetched_at`, `source_version` og `raw_hash` på
   hver observasjon, med defaults i `Observation` og stempling i kjernen
   etter parse.
3. **Koblinger og klassifiseringer som observasjoner.** Innehaver-orgnr,
   NACE-kode og segmenttilhørighet skrives som (entity_id, field, value,
   observed_at) ved hver kjøring, ikke utledes ved analyse.
4. **Prediksjonslogg.** `predictions/<dato>.yml` med retning, vindu,
   terskel og grunnlag. Evalueres automatisk mot observasjoner når
   vinduet utløper.

**Hvorfor rå-arkiv:** Uten det er hver feil i `parse()` permanent
datatap. Et feiltolket felt eller en manglende nøkkel oppdages typisk
uker etter at den kom inn, og kildene overskriver seg selv. Med arkivet
er samme feil en re-parse, og rettingen virker bakover til uke 1.
Dette er også forutsetningen for at parseren kan endres mange ganger
over to år uten at hver endring bare gjelder framover.

**Hvorfor proveniens:** Legges feltene til senere, står de tomme
bakover, og spørsmålet "hvilken parserversjon ga dette tallet" kan aldri
besvares for den perioden.

**Hvorfor koblinger:** Kryssreferering mellom segmenter i verdikjeden er
prosjektets analytiske fortrinn. Registrene viser kun gjeldende kobling
— selges en lokalitet, er forrige eier borte fra kilden. Lagres ikke
koblingen løpende, kan historikken aldri fortelle hvem som eide hva når.
Samme for klassifisering: en enhet som omklassifiseres mister sin
historiske segmenttilhørighet. Segmentkartet (NACE → segment)
versjoneres, slik at en senere endring ikke omskriver historikk.

**Hvorfor prediksjoner:** Commit-tidsstempelet gjør anslaget umulig å
rekonstruere i etterkant. Det er hele verdien — en prediksjon skrevet
etter utfallet er verdiløs, og ingen kan i ettertid bevise at den ikke
var det. Etter to år gir dette målt treffrate per segment og horisont
i stedet for en påstand om bransjeforståelse. Sekundært: et
evalueringssett for et senere modell-lag.

**Om kontrakten:** Sømmen fantes allerede — `fetch()` og `parse()` er
separate kall, og `collect()` kollapset dem til ett. Kjernen åpner
kallene og arkiverer imellom. `contract.py` utvides kun med tre
proveniensfelter som har defaults og fylles av kjernen via
`dataclasses.replace()`. Kilder rører dem ikke. Koblinger og
klassifiseringer bruker samme fire kolonner som alt annet. En ny kilde
er fortsatt én ny fil.

**Presisering om hva som arkiveres:** `fetch()` i Enhetsregisteret
returnerte opprinnelig enheter med pagineringskonvolutten strippet og
seks NACE-søk slått sammen til én liste. Da var `totalPages` og hvilket
søk som fant hver enhet tapt før arkivering. `fetch()` returnerer nå
sidene med konvolutt intakt. Arkivet er dermed reparerbart også mot
pagineringsfeil, ikke bare mot felttolkningsfeil. Standarden gjelder
alle framtidige kilder.

**Prisen:** Repovekst fra rå-arkivet og tre nye kolonner på ~8 000
observasjoner per kjøring. Proveniensfeltene er identiske innenfor én
kjøring, og parquet er kolonnelagret, så kompresjonen bør ta det meste
— ikke verifisert på egne data. Måles på første kjøring: rå-arkiv
gzippet, snapshot før og etter proveniens.

**Ville snudd det:** For rå-arkivet: at det vokser fortere enn
snapshotene med en faktor som gjør git upraktisk, over ca. 100 MB i
året. Da arkiveres rå kun for kilder med felt som ennå ikke er stabilt
tolket. For prediksjonene: at de blir så vage at de ikke kan feile — da
er problemet formatet, ikke ideen, og retning/vindu/terskel kreves som
felter. For de to andre: ingenting. Uten dem er reparasjon og
kryssreferering begrenset til data framover fra dagen de bygges.
