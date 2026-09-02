---
dato: 2026-09-03
tittel: "diff.compare bygget changeloggen med avkortet skjemautledning — en latent feil siden loggen ble skrevet"
status: gjeldende
commit: e1c89d1
---

## Hva som ble bestemt

`core/diff.py` bygger nå changelog-rammen med `infer_schema_length=None`
i stedet for polars' standard. Endringen gjelder begge stedene rammen
bygges: `compare()` og `revisjon_mellom()`.

**Dette er en endring i `core/`, og den er ført som egen beslutning
nettopp derfor.**

## Feilen

    ComputeError: could not append value: "journalDate er
    JOURNALFØRINGSDATO…" of type: str to the builder

Rammen ble bygget med `pl.DataFrame(changes)`, som utleder skjemaet fra
de **100 første radene**. Er de hundre første «ny», er `old_value` `None`
i hver eneste én, kolonnen utledes som `Null`, og den første raden med en
faktisk streng i `old_value` — en «borte» eller «endret» — feller hele
byggingen.

`.cast(CHANGE_SCHEMA)` på linja under ville gitt riktig type. Rammen rakk
bare aldri å bli bygget.

## Hvorfor den aldri har fyrt før

Fordi hver eksisterende kilde blander «ny», «endret» og «borte» innenfor
de første hundre radene. Enhetsregisteret, akvakultur, lusetall og
sjøtemperatur skriver alle snapshots der de fleste entitetene går igjen
fra forrige gang, så en «endret»- eller «borte»-rad dukker opp tidlig.

`eierskap_historikk` gjør ikke det. Den skriver ett snapshot per år med
én rad per overføring, og **to nabosnapshots deler ingen entiteter i det
hele tatt**. Da er alle «ny» først og alle «borte» sist, og de 100 første
er garantert bare «ny» så snart et år har over hundre observasjoner.

Feilen har altså ligget der siden changeloggen ble skrevet, og ventet på
den første kilden med disjunkte entitetssett.

## Hvorfor dette ikke er «å endre core for en kilde»

CLAUDE.md regel 1 er klar: `core/` endres ikke for å legge til en kilde,
og later en ny kilde til å kreve det, skal man si fra i stedet for å
gjøre unntaket.

Prøven er om KONTRAKTEN mangler noe. Den gjør den ikke her:

- Ingen nytt felt, ingen ny `change_type`, ingen ny parameter.
- `CHANGE_SCHEMA` er uendret. Kolonnene er de samme, typene er de samme.
- Kilden leverer kontraktsriktige data — `old_value` skal være `Utf8`
  eller `None`, og det er nøyaktig det den leverer.

Det som er rettet er en **implementasjonsdetalj som gir krasj for
kontraktsriktige data**. Enhver framtidig kilde med over hundre nye
entiteter før den første forsvunne ville truffet den, uavhengig av hva
den ellers gjør.

Alternativet var å la kilden slutte å skrive `dato_forbehold` for å komme
utenom. Det ville vært å bøye dataene etter en feil i kjernen, feilen
ville ligget der til neste gang, og den neste ville truffet den uten å
vite hvorfor.

## Verifisering

Regresjonstest i `tests/test_revisjon.py`:
`test_over_hundre_nye_rader_for_forste_borte`. Den skriver et snapshot med
150 entiteter, så ett med 150 HELT ANDRE, og krever 300 changelog-rader
med `old_value` som `Utf8`.

Testen er kjørt mot koden **uten** rettelsen og feiler der med
`ComputeError` — den beskriver altså feilen, ikke bare rettelsen.

## Hva som ville snudd det

- **Polars endrer standardoppførselen** slik at heterogene kolonner
  utledes riktig uansett lengde. Da er parameteren overflødig, men den
  gjør ingen skade.
- **`CHANGE_SCHEMA` sendes direkte inn i konstruktøren** i stedet for å
  castes etterpå. Det ville vært strammere — skjemaet ville vært
  påkrevet i stedet for utledet — men det er en større endring i en
  funksjon to andre moduler er avhengige av, og den hører ikke hjemme i
  en hastefiks.
