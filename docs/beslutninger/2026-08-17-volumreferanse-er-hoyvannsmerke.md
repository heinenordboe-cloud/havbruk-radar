---
dato: 2026-08-17
tittel: Volumreferansen er et høyvannsmerke
status: gjeldende
commit: c93e9c9
---

# Volumreferansen er et høyvannsmerke

**Bestemt:** Referansen i volumvakten stiger på reell vekst, men senkes
aldri av seg selv. `--godta-volum` er eneste vei ned.

**Hvorfor:** Første implementasjon returnerte siste friske verdi som ny
referanse, også når den var lavere. Reprodusert: 8 % fall i uka, ti
uker, ned til 43 % av opprinnelig volum uten ett varsel. Det er
rullende snitt i praksis — nøyaktig det volumvaktbeslutningen fra samme
dag utelukket, og det modulens egen docstring påsto at den ikke gjorde.

**Hvordan den slapp gjennom:** De fire eksisterende testene brukte
enten et stort fall (50 %, 25 %, 0) eller ren økning. Ingen gikk
gjennom 90-99-båndet der driften lever. Hullet var i testdesignet, ikke
bare i koden.

Funnet av ekstern kodegjennomgang, ikke av testene.

**Sideeffekt:** Gjør kvitteringen meningsfull. Med en referanse som
senket seg selv var `--godta-volum` i praksis dekorasjon.

**Ville snudd det:** Ingenting. En vakt som senker sin egen terskel er
ikke en vakt.
