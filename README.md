# havbruk-radar

Longitudinell datainnsamling om norsk havbruk. Hver kjøring skriver et nytt
snapshot og committer det. Historikken bygges opp over tid og kan ikke
rekonstrueres i etterkant — derfor starter innsamlingen før systemet er ferdig.

## Kom i gang

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run.py --torrkjor           # hent og vis, skriv ingenting
python run.py                      # ekte kjøring, skriver snapshot
python -m pytest -q                # røyktest, ingen nett nødvendig
```

Første kjøring gir null endringer — det er riktig. Diffen krever et
forrige snapshot å sammenligne mot. Endringsloggen starter i kjøring to.

## Slik legger du til en kilde

Lag én fil i `sources/`. Ingenting annet skal endres.

```python
from core.contract import Observation, Source

class MinKilde(Source):
    name = "min_kilde"
    entity_type = "selskap"

    def fetch(self):
        return ...                    # rådata, ingen rensing

    def parse(self, raw, observed_at):
        yield Observation(...)        # normaliser hit
```

`core/registry.py` skanner mappa og finner den automatisk. Filer som
starter med `_` hoppes over.

## Reglene som holder strukturen i live

1. **Ingenting overskrives.** Nye filer, aldri redigerte. `data/` er ikke i `.gitignore`.
2. **`core/` kjenner ikke kildene.** Må du endre `core/` for å legge til en kilde, er kontrakten brutt.
3. **Konfigurasjon i `config.yml`, ikke i kode.** URL-er, koder, terskler, feltnavn.
4. **Regler i `rules/signals.yml`.** De skal endres ukentlig uten commit i Python.
5. **Feil isoleres per kilde.** Én kilde som dør skal aldri stoppe de andre.
6. **Én test som beviser punkt 5.** Den ligger i `tests/`.
7. **Feil som isoleres må fortsatt varsles.** En grønn jobb med en død kilde er verre enn en rød jobb.

## Struktur

```
run.py                    inngangspunkt, syv steg
config.yml                alt som kan justeres
core/
  contract.py             ← den viktigste filen. Observation + Source
  config.py               leser config.yml
  registry.py             finner kilder ved å skanne sources/
  runner.py               kjører alle, isolerer feil
  snapshot.py             skriver parquet, leser forrige
  diff.py                 sammenligner mot forrige snapshot
  signals.py              scorer endringer mot rules/signals.yml
  health.py               oppdager kilder som stille slutter å levere
sources/
  enhetsregisteret.py     aktiv — åpent API, ingen nøkkel
  akvakulturregisteret.py deaktivert til endepunkt er bekreftet
rules/signals.yml         signalregler
data/raw/{kilde}/{dato}.parquet
data/changelog.parquet    akkumulert endringslogg
data/health.json          status per kilde
data/siste_kjoring.txt    genereres, brukes som commit-melding
docs/ARKITEKTUR.md        hvorfor det ser slik ut
docs/RUNBOOK.md           drift, sikring og veien til nettside
tests/                    røyktest uten nett
```

## Kilder

| Kilde | Status | Nøkkel |
|---|---|---|
| Enhetsregisteret | aktiv | nei |
| Akvakulturregisteret | mangler endepunkt | nei |
| Regnskapsregisteret | ikke bygget | nei |
| BarentsWatch | ikke bygget | gratis registrering |
| NAV stillinger | ikke bygget | nei |
