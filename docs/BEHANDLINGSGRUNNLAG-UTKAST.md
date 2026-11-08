# Behandlingsgrunnlag for personopplysninger i rålaget — UTKAST

**Utkast, ikke lest av advokat.** Skrevet i økt 4e (08.11.2026) som
grunnlag for en advokatvurdering, ikke som en vurdering. Ingenting her
er en juridisk konklusjon, og ingenting her er gjort: ingen kropp er
slettet, og ingen historikk er skrevet om.

Tallene er fra `docs/MALING-PERSONDATA-RAALAG.md` (MÅLT 08.11.2026).

## 1. Hvilke opplysninger, hvor

| hva | hvor | omfang | hvorfor det ligger der |
|---|---|---|---|
| navn, organisasjonsnummer, adresse og næring for enkeltpersonforetak, DA, ANS og partsrederi | `data/arkiv/enhetsregisteret/` | 13 av 19 kropper, 98 enheter, 17.08–21.09.2026 | kroppen ble arkivert slik Brreg sendte den, før personformene ble filtrert i kilden (22.08) og før snapshot-sperren |
| e-post, telefon, mobil (alle organisasjonsformer) | `data/arkiv/enhetsregisteret/` | 19 av 19 kropper, 820 enheter | kontaktfeltene ble ikke fjernet før arkivering før `bcd4221` |
| navn på mottakere uten identitetsnummer | `data/arkiv/eierskap-overforinger/` | 17 kropper, 12 navn | Fiskeridirektoratets overføringshistorikk; antakelig personer |
| navn på DA, ANS og partsrederi som eier tillatelser | `data/arkiv/eierskap/` | 6 enheter | tillatelsesregisteret; `Person` og ENK filtreres før arkivering |
| e-postadresser til pressekontakter, forfattere og redaktører | `regjeringen-pressemeldinger/`, `reguleringsomraader/`, `vilkar-*/`, `maling-lovdata/` | 17 adresser | del av sidene og metadataene slik utgiveren publiserte dem |
| snapshots og changelog med personform-enheter | `data/raw/`, `data/changelog/` | 106 enheter, 381 changelog-rader (R4 F3, 18.09.2026) | skrevet før sperren; lesedøra holder dem ute |

Ingen fødselsnummer: ingen `identityNr` har 11 siffer (R4 F2), og
rolleendepunktet og det autoriserte API-et brukes ikke (CLAUDE.md
regel 3, LISENSKJEDE merknad B).

**Publisert: ingenting.** 0 av 1 784 identifikatorer står i et bygg av
nettstedet (MALING F6). Lesedøra (`core/persondata.py`) holder
personformene ute av alt som leses, og `snapshot.write()` nekter et nytt
snapshot med dem.

## 2. Formålet

Kystloggen samler offentlige registeropplysninger om havbruk — lokaliteter,
tillatelser, eierskap, selskaper — for å vise hvordan næringen endrer seg
over tid, og for å kunne dokumentere hva registrene sa en gitt dag.
Personopplysningene er ikke formålet. De ligger i rålaget fordi
kroppene er tatt vare på slik kilden sendte dem, og fordi dette er
prosjektets bevis for hva som ble mottatt (sha256, OpenTimestamps-stempler).

## 3. Grunnlag som kan være aktuelle (å vurdere, ikke konkludert)

**Berettiget interesse, personvernforordningen art. 6 nr. 1 bokstav f.**
Argumentene for:

- opplysningene er offentlige hos kilden (Enhetsregisteret,
  Fiskeridirektoratets registre) og gjelder næringsvirksomhet;
- de brukes ikke, vises ikke og selges ikke — de ligger i et privat
  arkiv som bevis på hva kilden sendte;
- de nye kroppene skrives uten dem (filter i kilden, sperre ved
  skriving, kontaktfelt fjernet fra 09.11.2026).

Argumentene mot, eller det en advokat må veie:

- arkivet er append-only, speiles til GitLab og er tidsstemplet; en
  registrert som krever sletting, kan ikke få det uten at stemplene
  brytes (CLAUDE.md regel 2, R4 1.10);
- kontaktfeltene (e-post og telefon) til enkeltpersonforetak er mer
  personlige enn navn og adresse;
- en kjøper vil arve arkivet.

**Art. 85 og personopplysningsloven § 3 (journalistiske formål)** er
nevnt for fullstendighetens skyld. Om en registerkrønike som denne er
journalistikk, er nettopp et advokatspørsmål.

## 4. Det advokaten bør svare på

1. Hvilket grunnlag gjelder for opplysningene i tabellen over, hver
   linje for seg?
2. Utløser kontaktfeltene i 19 kropper en sletteplikt, eller kan de
   beholdes som bevis med tilgangsbegrensning?
3. Kan arkivet overdras til et selskap eller en kjøper med opplysningene
   i, og hva må i så fall avtalen si?
4. Var eksponeringen 16.–18.08.2026 (R4 1.10 F4) meldepliktig?
5. Hva må stå i en personvernerklæring på nettstedet, som i dag ikke har
   en (R4 1.5)?

## 5. Det som er gjort, og det som ikke er det

Gjort: filter i kilden (22.08), sperre i `snapshot.write()`, lesedøra,
kontaktfeltene ut av nye kropper (`bcd4221`), denne målingen.

Ikke gjort, med vilje: sletting, omskriving av historikk, flytting av
kropper. Det venter på svaret i punkt 4.
