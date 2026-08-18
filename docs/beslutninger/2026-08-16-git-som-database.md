---
dato: 2026-08-16
tittel: Git som database, ikke en server
status: gjeldende
commit: 
---

# Git som database, ikke en server

**Bestemt:** Ett parquet-snapshot per kilde per kjøring, committet til
git. Ingen database, ingen VPS.

**Hvorfor:** Git gir versjonering, diff og historikk gratis og permanent.
Null drift, null kostnad. `data/` er bevisst ikke i `.gitignore` —
dataene *er* repoet.

**Ville snudd det:** Kjøretid over seks timer per kjøring, eller kilder
som blokkerer GitHubs IP-adresser. Ikke repostørrelse — 43 KB i uka er
ca. 2 MB i året.
