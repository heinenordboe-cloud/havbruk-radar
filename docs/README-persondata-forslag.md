# Forslag til ny ordlyd i README.md

**Ikke committet.** Dette er et forslag til erstatning for
persondata-avsnittet i `README.md`, til lesing før det settes inn.
Slett denne fila når ordlyden er valgt.

## Påstanden som ikke stemmer i dag

README sier nå, på norsk:

> Det hentes kun opplysninger om virksomheter og lokaliteter. **Roller,
> gateadresser og andre personopplysninger hentes bevisst ikke inn**, slik
> at verken dette repoet eller datarepoet er et personregister.

og på engelsk:

> Only company- and site-level data is collected; roles, street addresses
> and personal data are deliberately excluded.

Første halvdel er sann: rolleendepunktet er aldri kalt, og gateadresse er
aldri lagret i et snapshot. Andre halvdel — konklusjonen om at ingen av
repoene er et personregister — er ikke sann. 34 enkeltpersonforetak ligger
i hvert enhetsregister-snapshot fra 16.–17.08.2026, og et ENK er ikke et
eget rettssubjekt: foretaket er innehaveren.

Fra 22.08.2026 filtreres de bort i kilden, så påstanden blir sann for nye
snapshots. Historikken som allerede er skrevet er en åpen sak, og
ordlyden bør ikke påstå mer enn det som er avgjort der.

---

## Forslag A — presis, og sier hva som gjenstår

Anbefalt hvis historikken blir stående.

> Det hentes kun opplysninger om virksomheter og lokaliteter. Roller,
> gateadresser og andre personopplysninger hentes bevisst ikke inn.
>
> Enkeltpersonforetak er et eget spørsmål: et ENK er ikke et eget
> rettssubjekt, så opplysninger om foretaket er opplysninger om
> innehaveren. Fra 22.08.2026 filtreres de bort i kilden, før noe lagres
> eller arkiveres. Snapshots samlet inn før den datoen inneholder dem, og
> hva som skal gjøres med de filene er ikke avgjort — se
> `docs/beslutninger/2026-08-22-enk-filtreres-i-kilden.md`.

Engelsk:

> Only company- and site-level data is collected; roles, street addresses
> and personal data are deliberately excluded.
>
> Sole proprietorships are a separate matter: a Norwegian *enkeltperson-
> foretak* is not a legal entity distinct from its owner, so data about
> the business is data about a person. Since 22 August 2026 these are
> filtered out at the source, before anything is stored or archived.
> Snapshots collected before that date still contain them, and what to do
> about those files has not been decided.

## Forslag B — kortere, uten den åpne saken

Anbefalt hvis historikken ryddes først, slik at det ikke gjenstår noe å
ta forbehold om.

> Det hentes kun opplysninger om virksomheter og lokaliteter. Roller,
> gateadresser og andre personopplysninger hentes bevisst ikke inn, og
> enkeltpersonforetak — der foretaket rettslig sett er innehaveren —
> filtreres bort i kilden før noe lagres.

Engelsk:

> Only company- and site-level data is collected. Roles, street addresses
> and personal data are deliberately excluded, and sole proprietorships —
> where the business is legally the person — are filtered out at the
> source before anything is stored.

---

## Det som er felles for begge

Setningen «slik at verken dette repoet eller datarepoet er et
personregister» er tatt ut i begge forslag. Den er en konklusjon trukket
på vegne av leseren, og det var nettopp en slik konklusjon — «alle
entity_id er ni siffer, altså ingen persondata» — som bar åpningen av
repoet 16.08 og viste seg å ikke holde. Beskriv hva som hentes og hva som
ikke hentes; la leseren trekke slutningen.
