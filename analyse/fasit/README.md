# Fasit — manuelt innsamlet, ikke innsamlet av en kilde

Alt i `data/` er skrevet av en `Source` og bærer `fetched_at`,
`source_version` og `raw_hash`. Det som ligger her er skrevet av et
menneske som har lest en PDF.

De to må ikke kunne forveksles, og derfor ligger fasiten

- **utenfor `data/`**, så den aldri havner i `les_alt()`, i en diff
  eller i et snapshot,
- **i kodetreet**, så den versjoneres i git sammen med analysen som
  bruker den — den er en forutsetning for et resultat, ikke en
  observasjon om verden,
- **som CSV med kilde- og sikkerhetskolonne**, så hver enkelt celle
  bærer hvor den kommer fra. En fasit uten proveniens er en påstand.

`data/` er append-only fordi historikken ikke kan hentes igjen. Denne
fila er det motsatte: den skal rettes når noen leser rapporten på nytt
og finner at en celle var feil. Rettelsen skjer med ny `kilde` og ny
dato i toppkommentaren.

## ekspertgruppen-po-kategori.csv

Ekspertgruppen for vurdering av lusepåvirkning kategoriserer hvert
produksjonsområde hvert år etter estimert lakselusindusert dødelighet
på utvandrende villakssmolt:

| kategori | dødelighet |
|---|---|
| `lav`     | under 10 % |
| `moderat` | 10–30 % |
| `hoy`     | over 30 %  |

`ukjent` betyr at året ikke er lest ut av en rapport. 2018, 2019, 2025
og 2026 står som `ukjent` med vilje — de er ikke gjettet, og de
utelates av enhver treffprosent.

`sikkerhet=utledet` gjelder 2024, som er avledet og ikke lest som
kategori. Analysen rapporterer treff med og uten disse radene.
