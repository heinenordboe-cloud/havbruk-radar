"""Hvilke organisasjonsformer er en fysisk person forkledd som et foretak.

Dette er en juridisk vurdering, ikke en innstilling. Den ligger i kode og
ikke i `config.yml` av samme grunn som feltvalget gjør det: hvem vi nekter
å lagre data om skal ikke kunne endres ved et uhell i en YAML-fil.

## Skillet

Spørsmålet er ikke om NAVNET ser ut som et personnavn. «Ola Nordmann AS»
er også oppkalt etter en person, og et AS skal vi lagre. Spørsmålet er om
FORETAKET ER personen:

- **ENK** (enkeltpersonforetak) er ikke et eget rettssubjekt. Innehaveren
  hefter personlig med hele sin formue, forretningsadressen er i praksis
  hjemmeadressen, og orgnummeret slås opp hos Brreg til ett navngitt
  menneske. Da er kommune, postnummer, næring, registreringsår — og
  særlig `konkurs` og `under_tvangsavvikling` — opplysninger om en
  identifiserbar fysisk person. GDPR gjelder.

- **DA og ANS** er ansvarlige selskaper. Deltakerne hefter personlig, men
  selskapet er et eget rettssubjekt med eget organisasjonsnummer, egen
  adresse og partsevne. Deltakerne selv står bare i rolleregisteret, som
  denne pipelinen aldri spør etter (CLAUDE.md regel 3). Selskapsdata om
  en juridisk person er ikke personopplysninger — se fortalepunkt 14 i
  GDPR.

  Et navn som «Hansen og Olsen DA» peker riktignok på fysiske personer.
  Men å filtrere PÅ NAVNET er nøyaktig samme feil som ni-siffer-testen
  fra 16.08: en syntaktisk prøve der spørsmålet er semantisk. Enten er
  formen en person eller ikke. DA og ANS er det ikke, og de blir stående.

## Dataene sier det samme

Skillet over er en juridisk vurdering, men det lar seg etterprøve i
feltet `institusjonell_sektorkode`, som allerede lagres. Målt i
snapshotene 22.08.2026:

    ENK          sektor 8200   husholdninger — personen selv
    DA, ANS, PRE sektor 2300   personlige foretak — foretakssektorene
    AS, ASA, SA  sektor 2100   private aksjeselskaper

SSBs sektorgruppering plasserer altså ENK i husholdningssektoren og DA,
ANS og partrederi blant foretakene. Det er en uavhengig kilde til samme
grense, ikke et sammentreff: begge følger av at ENK ikke er et eget
rettssubjekt.

Mener du DA og ANS likevel skal ut, er inngrepet én linje i settet under
— og da forsvinner de i kilden, ikke i en vask etterpå. Vil du i stedet
trekke grensa ved sektor 2300, er det en annen og bredere regel, og den
bør skrives som en sektorprøve her framfor som en liste over former.
"""

# Feltet en kilde oppgir organisasjonsformen i. Vakten i snapshot.write()
# ser bare det den kan lese, og dette er navnet den leter etter.
FORM_FELT = "organisasjonsform"

# Brreg-koder der foretaket ikke er et eget rettssubjekt fra den fysiske
# personen bak det. Vurderingen bak hver enkelt står i docstringen over,
# og en utvidelse skal ha samme dekning.
PERSONFORMER = frozenset({"ENK"})


def er_personform(kode: object) -> bool:
    """Sant hvis organisasjonsformkoden betyr «dette foretaket er et
    menneske». Tåler None og andre typer: en enhet uten oppgitt form er
    ikke en kjent personform, og skal ikke stoppes på det grunnlaget."""
    return isinstance(kode, str) and kode.strip().upper() in PERSONFORMER
