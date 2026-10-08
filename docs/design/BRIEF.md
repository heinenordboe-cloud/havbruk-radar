# Briefen

Kilden for all design på Kystloggen fra 08.10.2026. Står noe her i strid
med en eldre designfil (`STILGUIDE.md`, overleveringen, kommentarer i
`maler/stil.css`), er det denne som gjelder, og den andre skal rettes.

## Én setning

> Registrene viser hvordan ting er nå. Kystloggen viser hva som har
> endret seg, uke for uke, med kilde og sjekksum på hvert tall.

## Formål

Nettstedet har tre jobber, i denne rekkefølgen:

1. **Bevis.** Arkivet finnes, det går hver uke, og det kan etterprøves.
   Hver side skal vise når dataene ble hentet, fra hvem, og hvordan et
   tall kan sjekkes.
2. **Inngang.** Folk lander på én lokalitet eller ett selskap fra et
   søk. Siden svarer «hva har skjedd her» før den forklarer metoden.
3. **Referanse.** En side kan siteres, og den betyr det samme om et år.
   Adresser, ankernavn og tall endrer ikke betydning.

## Lesere

| Hvem | Spørsmålet de kommer med |
|---|---|
| Daglig leder i oppdrett | Hva har naboen gjort? |
| Rådgiver / advokat | Hva er historikken på denne tillatelsen eller lokaliteten? |
| Journalist / forsker | Hva skjedde, og kan jeg sitere det? |
| Analytiker | Kan jeg få dataene? |

## Tone

Arkiv og oppslagsverk. Nøktern, presis, ingen salgsord. Troverdigheten
er merkevaren — en side som overdriver én gang, er en side ingen siterer.

## Innholdsregler

- **Bare målte tall.** Ingen tolkning, ingen vurdering, ingen anslag.
  En oppsummeringssetning settes sammen av fakta som står lenger ned på
  siden; mangler et ledd, utelates leddet — det gjettes ikke.
- **Ingen personnavn.** Se CLAUDE.md regel 3. Et enkeltpersonforetak er
  en person.
- **Forbehold slettes aldri, de legges ett klikk unna.** Et forbehold kan
  flyttes ned eller inn bak en `<details>`, men det skal finnes på siden.
- **Registerverdier vises med menneskelig form først**, og rå verdi ett
  klikk unna (se `visningsord.py`).
- **Alt kan siteres og lastes ned.**
- **Virker uten JavaScript.** JS er bare en forbedring. Paginering,
  lukkede lister og filtre skal fungere med JS slått av.
- **Ingen sporing, ingen eksterne ressurser.** Fonter, bilder og skript
  ligger hos oss.

## Hva vi ikke skriver om

Ingen omtale av rapporter, abonnement eller tjenester før Heine sier
fra. «Kontakt» holder.

## Språk og modus

- **Bare norsk.**
- **Bare lys modus.** Én palett. Det finnes ingen
  `prefers-color-scheme: dark`-blokk i `maler/stil.css`, og både
  stilarket og `<meta name="color-scheme">` sier `light`. En leser med
  mørk modus i systemet får den samme lyse siden. Kontrastprøven
  (`tests/test_kontrast.py`) måler den ene paletten og feller en
  mørkblokk om den kommer tilbake. Mørk modus ble fjernet 08.10.2026:
  hver farge måtte velges, måles og vedlikeholdes to ganger, og feilene
  sto i den modusen ingen så på (h1 på 1,34:1, båndet på 1,04:1).

## Typografi

Newsreader (overskrifter og ordmerket) og IBM Plex Sans / Mono (brødtekst,
tabeller og tall), som i dag. Hostet av oss, se `maler/*.woff2`.

## Forsiden

- Fotografi som viser et **ekte oppdrettsanlegg**. Heines eget bilde fra
  desember; til det finnes, det nåværende bildet eller kartet.
- **Lavere hero**, slik at ukas endringer står over bretten på
  1440×900.

## Loggen

Hver hendelse som er verdt å sitere — konkurs, store eierskifter,
kapasitet som flytter seg — blir en egen post med beskrivende adresse:

    /logg/<dato>-<emne>/

- Systemet kan **foreslå** kandidater. Heine skriver og publiserer selv.
- **Kun AS, ASA og tilsvarende** selskapsformer, aldri ENK eller andre
  personformer.
- Bygges i en **egen pakke**. Designet skal ha en **postmal**: tittel,
  dato, ingress, de målte tallene med kilde og sjekksum, lenker til
  lokalitets- og selskapssidene det gjelder, og siteringsblokk.

## Sider og jobb

| Side | Svarer på | Øverst | Lenger ned |
|---|---|---|---|
| Forside | Hva er dette, hva skjedde nå, kan jeg stole på det? | Én setning om hva vi er, ukas viktigste 3–5 endringer, søk | Arkivtall, kart, følg med |
| Uke | Hva skjedde denne uka? | Sammendrag, vesentlige endringer | Tekniske endringer, selskapsdata, nedlasting, sitering |
| Lokalitet | Tilstand, og hva har skjedd? | Oppsummering, tilstand, kart, siste vesentlige endringer | Lus, tillatelser, registerfelt, kildens historikk |
| Selskap | Hva eier de, hva har endret seg? | Sammendrag, vesentlige endringer | Lokalitetsliste, historikk |
| Område | Hvordan ser området ut, hvem er der? | Farge, kapasitet per selskap, beholdningsgraf | Kilder for fargen, runder |
| Indekser | Finn det jeg leter etter | Søk og filter | Tabell med sider |
| Søk | Finn alt | Søkefelt | — |
| Om | Hvem, hvordan, kan jeg stole på det? | Hva og hvem i tre avsnitt | Metode, kilder, lisens, sitering, kontakt |

## Lengde

Målt på 390 px bredde:

- **Selskapssiden** skal være under 5 000 px.
- **Ingen indeksside** skal være over 10 000 px.

## Referanser for designet

Our World in Data og SSB: tall først, kilde ved hvert tall, nedlasting
ved hver tabell, nøktern typografi.
