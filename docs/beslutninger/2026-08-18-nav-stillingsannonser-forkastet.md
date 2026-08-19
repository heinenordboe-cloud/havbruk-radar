---
dato: 2026-08-18
tittel: NAVs stillingsannonser vurdert og forkastet — lisens, slettingsplikt og persondata
status: gjeldende
commit: 
---

# NAVs stillingsannonser vurdert og forkastet

**Bestemt:** Stillingsannonser tas ikke inn som kilde. Vurderingen skrives
ned slik at undersøkelsen ikke gjøres på nytt om noen måneder.

**Kilden er teknisk god.** `GET https://pam-stilling-feed.nav.no/api/v1/feed`
med bearer-auth, og et offentlig testtoken hentes fra `/api/publicToken`
uten registrering — verifisert, det returnerer en gyldig JWT. Paginering
med `If-Modified-Since`, `ETag` og `Last-Modified`. Annonsene har
`employer.orgnr`, som ville koblet rett inn i entity_id-rommet fra
Enhetsregisteret. Det er en sjelden god kobling, og bemanningsbehov leder
registerendringer.

**Tre ting kolliderer med prosjektets egne forpliktelser:**

**Vilkårene krever fjerning.** «Alle annonsar skal straks fjernast frå
resultatlista når annonsen blir inaktiv eller sletta hos Nav.» Systemet er
append-only ved design. Klausulen gjelder framvisning og ikke nødvendigvis
lagring, men den utelukker uansett en endringslogg som viser gamle
annonser.

**Ingen åpen lisens.** Brreg og Fiskeridirektoratet er NLOD, bekreftet.
NAVs stillingsdata har ingen lisens tildelt — bare bruksvilkår. README-ens
lisenshistorie dekker det ikke.

**Persondata.** Annonser inneholder rutinemessig kontaktperson med navn,
telefon og e-post. CLAUDE.md regel 3 og løftet om at ingen av repoene er
et personregister ville krevd hard filtrering, og vilkårene legger i
tillegg en slettingsplikt på meg som behandlingsansvarlig.

**Ikke verifisert:** Selve feeden er ikke kalt. Feltlista, `employer.orgnr`
inkludert, er dokumentasjon og ikke en respons noen har sett.

**Prisen:** Vi mister den beste ledende indikatoren vi har funnet. Et
selskap ansetter før kapasiteten flyttes, og den bevegelsen er nå usynlig.

**Ville snudd det:** At NAV tildeler dataene en åpen lisens, eller at det
lar seg gjøre å lagre kun orgnr, tittel, sted og datoer — uten annonsetekst
og uten kontaktperson — og at det er nok til å telle bemanningsbehov.
Da er persondataproblemet borte, og fjerningsklausulen gjelder framvisning
vi uansett ikke driver med.
