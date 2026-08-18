---
dato: 2026-08-16
tittel: Avhengigheter pinnes eksakt
status: gjeldende
commit: 40a32ee
---

# Avhengigheter pinnes eksakt

**Bestemt:** `requirements.txt` pinner `httpx==0.28.1`, `polars==1.36.1`,
`PyYAML==6.0.3`. `pyarrow` er fjernet — den ble aldri importert.
Testene kjører i CI på hver push, ikke bare mandag i produksjon.

**Hvorfor:** Med `>=` installerte jobben nyeste versjon hver mandag. To
risikoer: et breaking change i polars gjør jobben rød uten at du rørte
noe, og en kompromittert release kjører automatisk med skrivetilgang til
repoet. For et system som skal gå uten tilsyn i to år er dette den største
enkeltrisikoen etter at en etat endrer API.

**Prisen:** Oppgradering blir en bevisst handling. Det er meningen.

**Merk om metode:** Første forsøk pinnet en polars-versjon som ikke finnes,
hentet fra et miljø i stedet for fra PyPI. Riktig framgangsmåte er å la
pip løse versjonene lokalt og deretter låse det som faktisk ble installert
— da er pinningen sann per definisjon.

**Ville snudd det:** Ingenting. Men versjonene bør bumpes bevisst et par
ganger i året, ellers råtner de.
