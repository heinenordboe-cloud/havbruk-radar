---
dato: 2026-08-16
tittel: Repoet er offentlig
status: delvis feil, erstattet-av 2026-08-18-repoene-er-private.md
commit: 
---

# Repoet er offentlig

> **Delvis feil (påvist 22.08.2026).** Påstanden som falt er
> «ingen persondata», og med den betingelsen åpningen hvilte på.
> Kontrollen som skulle bevist den var at alle `entity_id` var ni
> siffer — men et ENK har ni siffer akkurat som et AS, så prøven kunne
> ikke skille dem. `organisasjonsform` lå i dataene hele tiden og
> svarte på spørsmålet; kontrollen så bare ikke der.
>
> Faktum: 34 enkeltpersonforetak lå i snapshotet som ble inspisert, og
> 202 ville kommet inn ved kjøringen 24.08. Et ENK er ikke et eget
> rettssubjekt — foretaket ER innehaveren.
>
> Beslutningen om å åpne er uansett reversert av
> [2026-08-18-repoene-er-private.md](2026-08-18-repoene-er-private.md),
> så feilen har ingen levende konsekvens for tilgangen. Det den har
> konsekvenser for, er hva som ligger i datarepoet — se
> [2026-08-22-enk-filtreres-i-kilden.md](2026-08-22-enk-filtreres-i-kilden.md).
>
> Rotårsaken er CLAUDE.md regel 1b i en femte utgave: en kontroll som
> var syntaktisk der spørsmålet var semantisk.

**Bestemt:** `havbruk-radar` er gjort offentlig. Erstatter beslutningen
lenger ned om å holde det privat.

**Hvorfor:** README var presentabel nok, og verdien av synlig
commit-historikk begynner å løpe fra dag én. Betingelsen fra
privat-beslutningen er verifisert: snapshotet inneholder kun selskapsdata
(954 enheter, ni felter, alle entity_id ni siffer), ingen roller, ingen
persondata — bekreftet ved inspeksjon av både kode og parquet-fil.

> Det er dette avsnittet som er feil. «Alle entity_id ni siffer» beviser
> ikke «ingen persondata»; det beviser bare at alle radene handler om
> registrerte enheter. 34 av dem var enkeltpersonforetak. Se noten øverst.

**Forpliktelser dette utløste:** MIT-lisens på koden og NLOD-attribusjon
for Brreg-data i README, begge på plass. NLOD er bekreftet i Brregs egen
OpenAPI-spesifikasjon, ikke antatt.

**Ville snudd det:** At persondata må inn i pipelinen, eller at
produktretningen blir alvor og endringsloggen er selve varen.
