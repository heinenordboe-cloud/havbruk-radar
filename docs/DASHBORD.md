# Veien til live nettside

Poenget med denne fila: du skal kunne vente fire måneder uten å tape noe.

## Hvorfor ventingen er gratis

Dashbordet er et rent leselag. Det eier ingen data, og innsamlingen vet
ikke at det finnes. Dagen du legger til `dashboard/`, peker du den mot
`data/` og har all historikken som allerede ligger der.

Det er den eneste grunnen til at rekkefølgen «samle først, vise senere»
fungerer. Hadde dashbordet eid dataene, ville ventingen kostet deg fire
måneder med historikk.

## Når du er klar (anslagsvis en kveld)

    npx degit evidence-dev/template dashboard
    cd dashboard && npm install

I `dashboard/evidence.plugins.yaml` peker du DuckDB på parquet-filene i
`../data/`. DuckDB leser dem direkte — ingen import, ingen database.

En side er en markdown-fil med SQL i:

    ---
    title: Endringslogg
    ---

    ```sql siste
    select * from read_parquet('../data/changelog.parquet')
    order by observed_at desc limit 50
    ```

    <DataTable data={siste} />

Deploy: koble repoet til Vercel, sett rotmappe til `dashboard/`. Hver
commit fra den ukentlige kjøringen bygger siden på nytt. Gratis, ingen
server, ingen drift.

## Et mellomsteg som koster ti minutter

Vil du ha noe synlig før den tid, la `run.py` skrive `data/changelog.md`
i tillegg til parquet, og slå på GitHub Pages. Da har du en offentlig
side som oppdateres ukentlig, uten Node, uten Vercel, uten byggesteg.

Stygg, men ekte — og den kan vises fram i et intervju lenge før
Evidence-versjonen står.

## Rekkefølgen på sidene

1. **Endringslogg.** Kronologisk liste over hva som faktisk skjedde.
   Dette er forsiden. Det er den eneste siden som er nyttig fra uke to.
2. **Aktørside.** Ett selskap over tid. Nyttig etter et par måneder.
3. **Bransjebilde.** Kapasitet per region, vekst mot snittet.
   Verdiløs før du har et halvt år med data.

Bygg dem i den rekkefølgen. Nivå tre først er den vanligste feilen, og
den gir deg en tom graf i fire måneder.
